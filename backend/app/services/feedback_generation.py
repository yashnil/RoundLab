import json
import logging
from typing import Optional

import openai
from pydantic import BaseModel

from app.config import settings
from app.models.feedback_report import FeedbackScores

logger = logging.getLogger(__name__)


class FeedbackGenerationError(Exception):
    pass


class _FeedbackOutput(BaseModel):
    """Full structured output from the LLM. Stored verbatim in raw_feedback."""

    overall_score: int
    scores: FeedbackScores
    summary: str
    strengths: list[str]
    weaknesses: list[str]
    decision_logic: str
    dropped_or_undercovered_arguments: list[str]
    warranting_diagnostics: list[str]
    weighing_diagnostics: list[str]
    evidence_diagnostics: list[str]
    judge_adaptation_notes: str
    top_3_priorities: list[str]
    recommendations: list[str]


_SPEECH_TYPE_GUIDANCE: dict[str, str] = {
    "constructive": (
        "This is a constructive speech presenting the team's initial case. "
        "Evaluate the completeness of each argument chain (claim → warrant → evidence → impact), "
        "the persuasiveness of the case structure, and how well the debater establishes initial "
        "framing. Note any structural weaknesses that will hurt them in later speeches."
    ),
    "rebuttal": (
        "This is a rebuttal speech. "
        "Evaluate the directness of responses to opponent arguments, whether every contention "
        "was addressed or dropped (and whether intentionally), and whether the speaker "
        "re-established their own case while attacking the opponent's."
    ),
    "summary": (
        "This is a summary speech. "
        "Evaluate what was correctly extended from earlier speeches, how the speaker collapsed "
        "the flow to decisive voting issues, and how impacts were weighed against each other. "
        "Note whether the speaker clearly explained why they are winning."
    ),
    "final_focus": (
        "This is a final focus speech. "
        "Evaluate impact comparison, voting issue clarity, and strategic focus. "
        "The speaker must crystallize the round — evaluate whether they gave the judge a clear "
        "story of why their side wins, with explicit weighing of magnitude, probability, and timeframe."
    ),
    "crossfire": (
        "This is a crossfire exchange. "
        "Evaluate the quality of questions asked, how well the speaker avoided making damaging "
        "concessions, and whether the speaker used the crossfire strategically to set up later "
        "arguments. Note any critical admissions that could be used against the speaker."
    ),
}

_JUDGE_GUIDANCE: dict[str, str] = {
    "lay": (
        "This is a lay judge. They prioritize: real-world impact clarity, persuasion, "
        "simple and accessible explanation, and big-picture storytelling. "
        "They may not track every argument but will vote for the side that tells the clearest story. "
        "Evaluate whether this speech was accessible and persuasive to a non-expert audience."
    ),
    "flow": (
        "This is a flow judge. They prioritize: extensions done correctly, dropped arguments, "
        "line-by-line refutation, and whether the debater cleaned up the flow. "
        "They will vote on drops. Evaluate whether the debater covered the flow completely "
        "and extended arguments through every speech."
    ),
    "tech": (
        "This is a tech judge. They prioritize: argument resolution, conceded offense, "
        "precise weighing, and minimal judge intervention. "
        "They expect explicit interaction between arguments and clear comparative weighing. "
        "Evaluate whether the debater resolved every clash and gave the judge a clear reason to vote."
    ),
    "coach": (
        "This is a coach judge. They prioritize educational feedback and skill development — "
        "identifying what the debater needs to learn, not just what they did wrong. "
        "Evaluate this speech from a teaching perspective: what specific skills should this "
        "debater practice before their next round?"
    ),
}

_SYSTEM_PROMPT_TEMPLATE = """\
You are an elite Public Forum debate judge and coach. Evaluate this speech as if writing a serious \
post-round ballot for a novice/JV debater. Be specific, technical, and educational. Do not give \
generic AI feedback. Do not praise vaguely. Tie every major critique to something in the transcript \
or argument map. Distinguish between 'argument was absent,' 'argument was present but underwarranted,' \
'argument was asserted but not impacted,' and 'argument was impacted but not weighed.' Your goal is \
to help the student know exactly what to fix in the next recording.

Speech context:
- Speech type: {speech_type}
- Side: {side}
- Topic: {topic}
- Judge type: {judge_type}

Speech type guidance:
{speech_type_guidance}

Judge type guidance:
{judge_guidance}

Scoring instructions (be accurate, consistent, and honest — do not inflate scores):

SCORING CALIBRATION:
- 90–100: Tournament-ready. Clear warranting on all arguments, explicit weighing with magnitude/probability/timeframe, clean extensions through the speech, strong judge adaptation. Minimal weaknesses.
- 75–89: Strong performance but missing some strategic depth. Most arguments warranted, some weighing present, extensions mostly done, adapted to judge type.
- 60–74: Understandable but with notable debate weaknesses. Some warranting present, limited weighing, inconsistent extensions, or generic judge approach.
- 40–59: Major missing components. Thin warranting, no weighing, dropped arguments, or inappropriate for judge type.
- Below 40: Incomplete, very unclear, or too short to evaluate fairly.

IMPORTANT: Score consistently. The same transcript should produce similar scores. Use the rubric anchors above.

- overall_score: Integer 1–100. Derived from the sum of the 5 category scores below (max 100).
- scores.clash (0–20): Direct engagement with opponent arguments. 0 = none, 20 = thorough line-by-line.
- scores.weighing (0–20): Impact comparison and magnitude/probability/timeframe analysis. 0 = none, 20 = precise.
- scores.extensions (0–20): Whether own arguments were clearly extended. 0 = dropped, 20 = fully extended.
- scores.drops (0–20): Whether the speaker addressed everything they needed to. 20 = nothing important dropped.
- scores.judge_adaptation (0–20): How well the speech was tailored to this judge type.

Output field instructions:
- summary: 3–5 sentences. Post-round assessment as the judge. Honest, specific, educational.
- strengths: 2–4 items. Specific things done well — quote or closely paraphrase from the transcript. No generic praise.
- weaknesses: 3–5 items. Specific problems — explain WHY each is a problem and WHAT to do to fix it next time.
- decision_logic: 2–4 sentences. If this were a real round, who is winning and on what arguments? What is the decisive issue?
- dropped_or_undercovered_arguments: Arguments the debater should have addressed (or addressed more thoroughly) but did not. Empty list if nothing was dropped.
- warranting_diagnostics: For each main argument, diagnose the warrant: sufficient / thin / absent / 'asserted not impacted' / 'impacted but not weighed.' Be specific to the argument.
- weighing_diagnostics: For each impact claim, diagnose whether weighing was present and how precise. Note missing magnitude, probability, or timeframe analysis.
- evidence_diagnostics: For each cited source, statistic, or study, assess whether it was used correctly and contextualized. Empty list if no evidence was cited.
- judge_adaptation_notes: 2–3 sentences. Was this speech appropriate for a {judge_type} judge? What specific changes would better adapt it?
- top_3_priorities: Exactly 3 items. The most important skills to develop before the next round, ordered by priority.
- recommendations: 3–5 specific practice drills, exercises, or techniques that directly address the top weaknesses.\
"""


def generate_feedback(
    text: str,
    arguments: list[dict],
    speech_type: str,
    side: Optional[str],
    topic: Optional[str],
    judge_type: Optional[str],
    word_count: int = 0,
) -> _FeedbackOutput:
    """Generate a PF-native ballot-style feedback report using GPT-4o-mini.

    Returns a _FeedbackOutput with all structured fields.
    Raises FeedbackGenerationError with a user-safe message on failure.
    """
    logger.info(
        "feedback_generation: starting | speech_type=%s side=%s judge_type=%s openai_key_present=%s",
        speech_type,
        side,
        judge_type,
        bool(settings.openai_api_key),
    )

    calibration_note = ""
    if 0 < word_count < 75:
        calibration_note = (
            f"\n\nSCORING CALIBRATION: This transcript is short ({word_count} words — typically under 30 seconds). "
            "Score conservatively. Do not infer sophisticated debate performance from limited evidence. "
            "Score only what is actually present. If content is absent, score it as absent. "
            "A short sample cannot demonstrate clash, drops, or extensions — score those at 0–5 unless explicitly shown."
        )

    judge_key = judge_type or ""
    system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(
        speech_type=speech_type,
        side=side or "unknown",
        topic=topic or "not specified",
        judge_type=judge_type or "not specified",
        speech_type_guidance=_SPEECH_TYPE_GUIDANCE.get(
            speech_type, "Evaluate this speech on standard PF criteria."
        ),
        judge_guidance=_JUDGE_GUIDANCE.get(
            judge_key, "Evaluate on general debate quality."
        ),
    )
    system_prompt += calibration_note

    arguments_summary = (
        json.dumps(arguments, indent=2) if arguments else "No argument map available."
    )
    user_message = f"Transcript:\n\n{text}\n\nArgument map:\n\n{arguments_summary}"

    try:
        client = openai.OpenAI(api_key=settings.openai_api_key)
        response = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            response_format=_FeedbackOutput,
            temperature=0.0,
        )
    except openai.AuthenticationError as exc:
        logger.error("feedback_generation: openai_auth_error | exc_type=%s", type(exc).__name__)
        raise FeedbackGenerationError(
            "Feedback generation failed. Check OpenAI API key, billing, or quota."
        ) from exc
    except openai.RateLimitError as exc:
        logger.error("feedback_generation: openai_rate_limit | exc_type=%s", type(exc).__name__)
        raise FeedbackGenerationError(
            "Feedback generation failed. Check OpenAI API key, billing, or quota."
        ) from exc
    except Exception as exc:
        logger.error(
            "feedback_generation: openai call failed | exc_type=%s",
            type(exc).__name__,
        )
        raise FeedbackGenerationError(
            "Feedback generation failed. Check backend logs."
        ) from exc

    parsed = response.choices[0].message.parsed
    if parsed is None:
        logger.error("feedback_generation: structured output returned None")
        raise FeedbackGenerationError("Feedback generation returned no data.")

    logger.info(
        "feedback_generation: success | overall_score=%d speech_id_context=%s",
        parsed.overall_score,
        speech_type,
    )
    return parsed
