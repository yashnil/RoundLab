import json
import logging
from typing import Optional

import openai
from pydantic import BaseModel

from app.config import settings
from app.models.feedback_report import FeedbackScores
from app.services.pf_rubrics import get_rubric, get_score_band, SCORE_BANDS

logger = logging.getLogger(__name__)


class FeedbackGenerationError(Exception):
    pass


class ScoreExplanation(BaseModel):
    """Explanation for a single dimension score."""

    dimension_name: str
    score: int
    score_band: str
    evidence_from_speech: str
    why_not_higher: str
    how_to_improve: str


class DebateIssue(BaseModel):
    """Structured coaching issue — explicitly typed and grounded in speech data."""

    issue_type: str
    """One of: missing_warrant | weak_evidence | unclear_impact | no_weighing |
    dropped_argument | weak_extension | no_clash | new_argument | organization | delivery"""

    severity: str
    """low | medium | high"""

    title: str
    """Short title, e.g. 'Missing warrant on economic contention'"""

    explanation: str
    """1-2 sentences explaining what is missing or weak in the speech."""

    why_it_matters: str
    """1 sentence: what this costs the debater in a real round (e.g. 'Flow judges may not evaluate this argument.')"""

    recommendation: str
    """1 concrete next step the debater can take to fix this."""

    affected_argument_labels: list[str]
    """Labels of arguments from the flow that exhibit this issue (may be empty)."""

    recommended_drill_type: str
    """One of: warranting | weighing | drops | extensions | evidence | clash | judge_adaptation | collapse | line_by_line"""


class _FeedbackOutput(BaseModel):
    """Full structured output from the LLM. Stored verbatim in raw_feedback."""

    overall_score: int
    scores: FeedbackScores
    score_explanations: list[ScoreExplanation]
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
    # Structured issues — new field, v2 reports only
    structured_issues: list[DebateIssue] = []


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

IMPORTANT: If a student cites evidence vaguely, critique the attribution and explanation, but do NOT \
invent what the card says. Do NOT fabricate evidence.

Speech context:
- Speech type: {speech_type}
- Side: {side}
- Topic: {topic}
- Judge type: {judge_type}

Speech type guidance:
{speech_type_guidance}

Judge type guidance:
{judge_guidance}

RUBRIC FOR THIS SPEECH TYPE ({speech_type}):
{rubric_details}

SCORING CALIBRATION:
{score_bands}

SCORING INSTRUCTIONS:
1. For each dimension, you MUST provide:
   - The numeric score (within the dimension's 0-max range)
   - The score band it falls into (e.g., "Excellent 19-20", "Functional 12-15")
   - Evidence from the speech showing what was done well
   - Why the score is not higher (what's missing or weak)
   - How to improve to reach the next band

2. Do NOT assign a 0-3 score unless the dimension is essentially absent or unusable. A readable,
   understandable speech with identifiable arguments should almost never receive 0-3 for Clarity.

3. Use the FULL 0-20 scale. Avoid defaulting to 10 or 12. Consult the score anchors and place the
   performance in the appropriate band based on what is actually present.

4. Score what is present, not what you wish were there. Be honest about weaknesses but recognize strengths.

IMPORTANT: Score consistently using the rubric above. The same transcript should produce similar scores.

LEGACY SCORE MAPPING (for backwards compatibility with 5-dimension schema):
You must output 5 scores (clash, weighing, extensions, drops, judge_adaptation) even though this \
speech type may not use all dimensions. Map the rubric dimensions as follows:
{score_mapping}

DO NOT PENALIZE HEAVILY:
{do_not_penalize}

Output field instructions:
- score_explanations: For EACH rubric dimension (not the legacy 5 fields), provide:
  * dimension_name: exact name from rubric (e.g., "case_structure", "warranting")
  * score: the numeric score you assigned
  * score_band: which band it falls into (e.g., "Functional 12-15")
  * evidence_from_speech: what in the transcript earned this score
  * why_not_higher: what's missing or weak that prevented a higher score
  * how_to_improve: concrete next steps to reach the next band
- summary: 3–5 sentences. Post-round assessment as the judge. Honest, specific, educational.
- strengths: 2–4 items. Specific things done well — quote or closely paraphrase from the transcript. No generic praise.
- weaknesses: 3–5 items. Specific problems — explain WHY each is a problem and WHAT to do to fix it next time.
- decision_logic: 2–4 sentences. If this were a real round, who is winning and on what arguments? What is the decisive issue?
- dropped_or_undercovered_arguments: Arguments the debater should have addressed (or addressed more thoroughly) but did not. Empty list if nothing was dropped.
- warranting_diagnostics: For each main argument, diagnose the warrant: sufficient / thin / absent / 'asserted not impacted' / 'impacted but not weighed.' Include topic-aware examples showing BEFORE (weak) and AFTER (strong) versions using the actual speech's claims and topic. Label examples with 'Model example only—do not copy word-for-word.' Do not fabricate specific citations or evidence. Use general topic context.
- weighing_diagnostics: For each impact claim, diagnose whether weighing was present and how precise. Note missing magnitude, probability, or timeframe analysis. Include topic-aware examples showing how to improve weighing for this specific argument. Use BEFORE/AFTER format with the actual topic and claims. Explain WHY the improved version is stronger.
- evidence_diagnostics: For each cited source, statistic, or study, assess whether it was used correctly and contextualized. Empty list if no evidence was cited. If the student cites vaguely, critique attribution but do NOT invent what the evidence says.
- judge_adaptation_notes: 2–3 sentences. Was this speech appropriate for a {judge_type} judge? What specific changes would better adapt it?
- top_3_priorities: Exactly 3 items. The most important skills to develop before the next round, ordered by priority. Make these {speech_type}-specific (e.g., for constructive: warranting, impact development; for summary: extensions, weighing).
- recommendations: 3–5 specific practice drills, exercises, or techniques that directly address the top weaknesses. Make these {speech_type}-appropriate.
- structured_issues: Generate 2–4 structured issues. For each issue:
  * issue_type: one of missing_warrant | weak_evidence | unclear_impact | no_weighing | dropped_argument | weak_extension | no_clash | new_argument | organization | delivery
  * severity: low | medium | high (based on how much this would cost them in a real round)
  * title: short specific title, e.g. "Missing warrant on Contention 2"
  * explanation: 1-2 sentences — what exactly is wrong, grounded in the speech
  * why_it_matters: 1 sentence — real-round consequence for a {judge_type} judge
  * recommendation: 1 concrete action the debater can take next
  * affected_argument_labels: list of argument labels from the argument map that exhibit this issue (use exact labels from the argument map provided). Empty list if not determinable.
  * recommended_drill_type: one of warranting | weighing | drops | extensions | evidence | clash | judge_adaptation | collapse | line_by_line
  Order issues by severity (high first). Do not repeat the same issue_type twice.\
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

    # Get speech-type-specific rubric
    rubric = get_rubric(speech_type)

    # Build rubric details for prompt
    rubric_details = f"Purpose: {rubric['purpose']}\n\nDimensions to evaluate:\n"
    for dim in rubric["dimensions"]:
        rubric_details += f"- {dim['student_friendly_label']} (0-{dim['max_score']}): {dim['description']}\n"
        rubric_details += f"  Reward: {dim['what_to_reward']}\n"
        rubric_details += f"  Penalize: {dim['what_to_penalize']}\n"
        if "score_anchors" in dim and dim["score_anchors"]:
            rubric_details += "  Score Anchors:\n"
            for anchor in dim["score_anchors"]:
                rubric_details += f"    {anchor['range']}: {anchor['label']} - {anchor['description']}\n"

    # Build score bands
    score_bands = ""
    for band_key, band_data in SCORE_BANDS.items():
        score_bands += f"- {band_data['min']}-{band_data['max']}: {band_data['label']}\n"

    # Build score mapping for legacy 5-dimension schema
    if speech_type == "constructive":
        score_mapping = """
- clash: Map case_structure score (scale to 0-20). Constructive doesn't have clash, so score organization.
- weighing: Map impact_development score (scale to 0-20).
- extensions: Map judge_clarity score (scale to 0-20). No extensions in constructive.
- drops: Map evidence_use score (scale to 0-20).
- judge_adaptation: Map judge_clarity score (scale to 0-20).
NOTE: Total these to get overall_score out of 100."""
    elif speech_type == "rebuttal":
        score_mapping = """
- clash: Map clash_refutation score (scale to 0-20).
- weighing: Map weighing_setup score (scale to 0-20).
- extensions: Map response_quality score (scale to 0-20).
- drops: Map coverage_prioritization score (scale to 0-20).
- judge_adaptation: Map evidence_comparison score (scale to 0-20).
NOTE: Total these to get overall_score out of 100."""
    elif speech_type == "summary":
        score_mapping = """
- clash: Map frontlining score (scale to 0-20).
- weighing: Map weighing score (scale to 0-20).
- extensions: Map extension_quality score (scale to 0-20).
- drops: Map collapse_strategy score (scale to 0-20).
- judge_adaptation: Map judge_clarity score (scale to 0-20).
NOTE: Total these to get overall_score out of 100."""
    elif speech_type == "final_focus":
        score_mapping = """
- clash: Map crystallization score (scale to 0-20).
- weighing: Map comparative_weighing score (scale to 0-20).
- extensions: Map ballot_story score (scale to 0-20).
- drops: Map consistency score (scale to 0-20).
- judge_adaptation: Map judge_adaptation score (scale to 0-20).
NOTE: Total these to get overall_score out of 100."""
    else:
        score_mapping = """
- Map dimensions as appropriate to the 5 legacy fields.
- Overall score should reflect total performance."""

    do_not_penalize = "- " + "\n- ".join(rubric["do_not_penalize_heavily"]) if rubric["do_not_penalize_heavily"] else "None"

    calibration_note = f"\n\nCALIBRATION NOTES:\n{rubric['calibration_notes']}"
    if 0 < word_count < 75:
        calibration_note += (
            f"\n\nThis transcript is short ({word_count} words — typically under 30 seconds). "
            "Score conservatively. Do not infer sophisticated debate performance from limited evidence. "
            "Score only what is actually present. If content is absent, score it as absent."
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
        rubric_details=rubric_details,
        score_bands=score_bands,
        score_mapping=score_mapping,
        do_not_penalize=do_not_penalize,
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
