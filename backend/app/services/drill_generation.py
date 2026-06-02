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
