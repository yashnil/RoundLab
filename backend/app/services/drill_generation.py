"""
Drill generation service.

Generates exactly 3 personalized PF debate drills from a feedback report.
Each drill targets a specific weakness identified in the feedback.
"""

import logging
from typing import Optional

import openai
from pydantic import BaseModel

from app.config import settings

logger = logging.getLogger(__name__)


class DrillGenerationError(Exception):
    pass


class _DrillItem(BaseModel):
    """One structured drill from the LLM."""

    title: str
    """Short action-oriented name, e.g. 'Impact Comparison Sprint'."""

    skill_target: str
    """One of: weighing | warranting | drops | extensions | evidence | clash | judge_adaptation | collapse | line_by_line"""

    description: str
    """2-3 sentence summary of what this drill is and why it matters."""

    prompt: str
    """The actual exercise the debater should perform — concrete and specific."""

    instructions: str
    """3-5 step guide. Plain text, newline-separated steps."""

    success_criteria: list[str]
    """3-4 specific, checkable criteria for what 'good' looks like."""

    source_weakness: str
    """The verbatim weakness from the feedback this drill addresses."""

    difficulty: str
    """beginner | intermediate | advanced"""

    time_limit_seconds: int = 90
    """Recommended practice time in seconds. Typical values: 60 (beginner), 90 (intermediate), 120-180 (advanced). Must be between 30 and 300. Defaults to 90 if not specified."""


class _DrillsOutput(BaseModel):
    drills: list[_DrillItem]
    """Exactly 3 drills in order of priority."""


_SYSTEM_PROMPT = """\
You are a PF debate coach generating personalized practice drills for a novice or JV debater.

Rules:
1. Generate EXACTLY 3 drills — no more, no fewer.
2. Each drill must target a DIFFERENT skill area. Do not generate two drills on the same skill.
3. Ground every drill in the specific feedback provided. Reference actual weaknesses, not generic advice.
4. Drills must be PUBLIC FORUM debate-specific. Do not give generic public speaking advice.
5. Each drill should be completable in 5-10 minutes.
6. Use debate-native terminology: warrants, weighing, extensions, drops, voting issues, impact calculus, cross-ex.
7. Order drills by priority: most critical weakness first.
8. difficulty values: 'beginner' for foundational skills, 'intermediate' for tactical improvements, 'advanced' for strategic refinements.
9. time_limit_seconds: Set a realistic practice time. Beginner drills: 45-90s. Intermediate: 90-150s. Advanced: 120-180s. Must be between 30 and 300.

Available skill_target values:
- weighing: comparing impacts by magnitude, probability, timeframe, reversibility
- warranting: strengthening the logical link between claim and evidence
- drops: recovering dropped arguments; avoiding drops in future speeches
- extensions: extending arguments through speeches; keeping contentions alive
- evidence: using and explaining evidence persuasively
- clash: directly engaging with opponent arguments
- judge_adaptation: calibrating language, speed, complexity for judge type
- collapse: choosing which arguments to collapse to in summary/final focus
- line_by_line: systematic response to opponent's speech structure
- pacing_control: reducing speaking rate to ensure warrants land clearly for judges
- filler_reduction: eliminating filler words (um, uh, like, you know) that reduce judge confidence
- clarity_delivery: breaking long sentences into judge-flowable units
- concise_warranting: expressing claim + warrant + impact in fewer, clearer words
- pause_control: using deliberate pauses after claims and before impacts

Each drill's prompt should describe a concrete speech scenario the debater can practice with.
Instructions should be a numbered list of 3-5 clear steps.
Success criteria should be 3-4 specific checkboxes the debater can self-evaluate against.
"""


def generate_drills(
    *,
    weaknesses: list[str],
    top_3_priorities: list[str],
    transcript_text: str,
    arguments: list[dict],
    speech_type: str,
    side: Optional[str],
    topic: Optional[str],
    judge_type: Optional[str],
) -> list[_DrillItem]:
    """
    Generate 3 personalized PF drills from feedback weaknesses.

    Raises DrillGenerationError on failure.
    """
    client = openai.OpenAI(api_key=settings.openai_api_key)

    # Build the coaching context
    priorities_text = "\n".join(f"- {p}" for p in top_3_priorities) if top_3_priorities else ""
    weaknesses_text = "\n".join(f"- {w}" for w in weaknesses[:6]) if weaknesses else ""

    arg_labels = []
    for a in arguments[:6]:
        label = a.get("label") or a.get("claim", "")[:60]
        arg_type = a.get("argument_type", "")
        if label:
            arg_labels.append(f"  [{arg_type}] {label}")
    args_text = "\n".join(arg_labels) if arg_labels else "  (none extracted)"

    topic_line = f"Resolution: {topic}" if topic else ""
    side_line = f"Side: {side.upper()}" if side else ""
    judge_line = f"Judge type: {judge_type}" if judge_type else ""
    speech_line = f"Speech type: {speech_type}"

    user_prompt = f"""\
Generate 3 personalized drills for this debater based on the feedback below.

{speech_line}
{side_line}
{judge_line}
{topic_line}

ARGUMENTS FROM THIS SPEECH:
{args_text}

TOP 3 PRIORITIES FROM FEEDBACK (most important weaknesses to fix):
{priorities_text if priorities_text else weaknesses_text or "General improvement needed"}

FULL WEAKNESS LIST:
{weaknesses_text or "See priorities above"}

EXCERPT FROM TRANSCRIPT (first 600 chars):
{transcript_text[:600]}

Now generate exactly 3 drills. Each must target a different skill area. Ground them in the specific weaknesses above.
"""

    try:
        completion = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt},
            ],
            response_format=_DrillsOutput,
            temperature=0.4,
        )
    except openai.OpenAIError as exc:
        logger.error("drill_generation: OpenAI call failed | exc=%s", exc)
        raise DrillGenerationError("Drill generation failed — OpenAI error") from exc
    except Exception as exc:
        logger.error("drill_generation: unexpected error | exc_type=%s", type(exc).__name__)
        raise DrillGenerationError("Drill generation failed unexpectedly") from exc

    output = completion.choices[0].message.parsed
    if output is None:
        raise DrillGenerationError("Drill generation returned no output")

    drills = output.drills
    if len(drills) != 3:
        logger.warning("drill_generation: expected 3 drills, got %d — trimming/padding", len(drills))
        drills = drills[:3]

    return drills


# Delivery skill targets eligible for a deterministic drill (no LLM needed)
_DELIVERY_SKILL_PRIORITY = [
    "pacing_control",
    "filler_reduction",
    "clarity_delivery",
    "concise_warranting",
    "pause_control",
]


def make_delivery_drill(clarity_flags: list[str], wpm: Optional[float], filler_count: int, word_count: int) -> Optional[_DrillItem]:
    """Return one deterministic delivery drill based on the most critical flag.

    Returns None if no delivery issue is significant enough to warrant a drill.
    No LLM call — this is fully deterministic.
    """
    filler_rate = filler_count / max(word_count, 1)

    if "too_fast" in clarity_flags and wpm is not None and wpm > 185:
        return _DrillItem(
            title="Pacing Control — Warrant Slowdown",
            skill_target="pacing_control",
            description=(
                f"You're speaking at approximately {int(wpm)} WPM. "
                "Fast pacing can obscure warrants and make it harder for judges to flow."
            ),
            prompt=(
                "Take the warrant section of your longest contention. "
                "Re-deliver it at 140–160 WPM. Pause for one full second after the claim, "
                "and again before the impact. Record yourself and count your pace."
            ),
            instructions=(
                "1. Identify your longest contention's warrant sentence.\n"
                "2. Mark natural pause points: after the claim, after the warrant, before the impact.\n"
                "3. Practice delivering that section three times with deliberate pauses.\n"
                "4. Record yourself. Aim for 140–160 WPM in that section.\n"
                "5. Check: can you hear each argument landing clearly?"
            ),
            success_criteria=[
                "Warrant section delivered at 140–165 WPM",
                "Clear 1-second pause after claim and before impact",
                "All words fully articulated — no blending",
            ],
            source_weakness="Speaking rate above 185 WPM may obscure warrants for judges",
            difficulty="beginner",
            time_limit_seconds=90,
        )

    if "many_fillers" in clarity_flags and filler_rate > 0.05:
        top_filler = "um"
        return _DrillItem(
            title="Filler Reduction — Clean Delivery Rep",
            skill_target="filler_reduction",
            description=(
                f"Your speech contained a high rate of filler words ({filler_count} detected). "
                "Filler words reduce judge confidence and can interrupt the flow of your argument."
            ),
            prompt=(
                "Give your opening contention again from memory. "
                f"Every time you say 'um,' 'uh,' 'like,' or 'you know,' stop and restart the sentence. "
                "Complete the contention with zero filler words."
            ),
            instructions=(
                "1. Choose one contention (claim + warrant + evidence + impact).\n"
                "2. Practice it once at normal speed — count your filler words.\n"
                "3. Do it again: if you say a filler word, pause and restart the sentence.\n"
                "4. Repeat until you complete the contention with zero fillers.\n"
                "5. Record your clean rep and confirm you're filler-free."
            ),
            success_criteria=[
                "Full contention delivered with zero filler words",
                "Natural pauses used instead of fillers at hesitation points",
                "No restarts needed in the final recorded rep",
            ],
            source_weakness=f"High filler word rate ({filler_count} fillers detected) reduces judge confidence",
            difficulty="beginner",
            time_limit_seconds=90,
        )

    if "long_sentences" in clarity_flags:
        return _DrillItem(
            title="Clarity Drill — Break Long Sentences",
            skill_target="clarity_delivery",
            description=(
                "Several sentences in your speech were very long, making them hard for judges to flow. "
                "Shorter, judge-flowable sentences help arguments land more clearly."
            ),
            prompt=(
                "Find your longest sentence in the speech. "
                "Rewrite it as two or three shorter sentences (under 20 words each). "
                "Each sentence should carry one idea: claim, warrant, or impact."
            ),
            instructions=(
                "1. Identify the longest sentence in your speech transcript.\n"
                "2. Count the words — it is probably over 30 words.\n"
                "3. Split it into 2–3 sentences, each with one idea.\n"
                "4. Say the new version aloud. It should sound natural and flowable.\n"
                "5. Deliver the section with the new sentences in a full run-through."
            ),
            success_criteria=[
                "No sentence longer than 25 words in the rewritten section",
                "Each new sentence expresses exactly one idea",
                "The rewritten section sounds natural and judge-flowable",
            ],
            source_weakness="Long sentences reduce clarity and make arguments hard to flow",
            difficulty="beginner",
            time_limit_seconds=120,
        )

    return None
