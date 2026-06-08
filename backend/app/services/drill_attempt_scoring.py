"""Drill attempt scoring service.

Evaluates a student's recorded drill attempt transcript against the drill's
success criteria and skill target using an LLM judge.

Score: 1–100 (matches the drill_attempts.score column type).
"""

import json
import logging
from typing import Optional

import openai
from pydantic import BaseModel

from app.config import settings

logger = logging.getLogger(__name__)


# ── Output schema ──────────────────────────────────────────────────────────────

class DrillAttemptFeedback(BaseModel):
    """Structured coaching feedback for one drill attempt."""

    score: int
    """1–100. 90+ = excellent, 70–89 = solid, 50–69 = developing, 30–49 = needs work, <30 = insufficient."""

    met_success_criteria: bool
    """True if the attempt satisfied the drill's stated success criteria."""

    feedback_summary: str
    """2–3 sentence coaching verdict grounded in what the transcript actually said."""

    strengths: list[str]
    """1–3 specific things the attempt did well, debate-native."""

    improvements: list[str]
    """1–3 specific things to fix, each with guidance on how."""

    next_instruction: str
    """One concrete next action the student should take before their next rep."""

    should_retry: bool
    """True if the student should redo the drill before moving on (score < 70 or criteria not met)."""


class DrillScoringError(Exception):
    pass


# ── Skill-specific rubrics ─────────────────────────────────────────────────────

_SKILL_GUIDANCE: dict[str, str] = {
    "weighing": (
        "Evaluate whether the debater explicitly compared impacts using magnitude (how severe?), "
        "probability (how likely?), and timeframe (how soon?). A strong attempt names both sides' "
        "impacts, applies at least two weighing criteria, and ends with a clear voting reason. "
        "A weak attempt only restates its own impact without comparing it to the opponent's."
    ),
    "warranting": (
        "Evaluate the causal chain: Claim → Warrant → Evidence → Impact. The warrant must explain "
        "WHY the claim is true — a mechanism, not a restatement of the claim. A strong attempt has "
        "a clear 'because' sentence linking claim to evidence to impact. "
        "A weak attempt asserts the claim without a causal mechanism."
    ),
    "drops": (
        "Evaluate whether the debater responded to every opponent argument without dropping any. "
        "A strong attempt names each opponent argument and provides a substantive response to each. "
        "A weak attempt addresses some arguments but skips others entirely."
    ),
    "extensions": (
        "Evaluate whether the debater extended claim + warrant + impact together, not just a label. "
        "'Extend our contention' alone is insufficient. A strong attempt re-states the claim, "
        "explains the warrant, and carries the impact forward explicitly."
    ),
    "evidence": (
        "Evaluate citation quality: source name, what it specifically proves, and how it connects "
        "to the claim. A strong attempt explains what the evidence proves, not just names the source. "
        "'Smith 2023 proves our point' without the mechanism is insufficient."
    ),
    "clash": (
        "Evaluate whether the debater directly engaged opponent arguments before building offense. "
        "A strong attempt explicitly names and refutes opponent claims before making its own. "
        "A weak attempt ignores opponent arguments and just repeats its own case."
    ),
    "judge_adaptation": (
        "Evaluate adaptation to the judge type. For lay judges: plain language, real-world examples, "
        "no debate jargon. For flow judges: explicit extensions, acknowledged drops, clear weighing. "
        "For tech judges: precise argument resolution and concession tracking. "
        "A strong attempt removes jargon and explains impacts in accessible terms."
    ),
    "collapse": (
        "Evaluate whether the debater narrowed the round to 1-2 decisive voting issues and "
        "explicitly compared them. A strong attempt names the voting issues, explains why they win "
        "those issues, and weighs them against opponent voting issues."
    ),
    "line_by_line": (
        "Evaluate systematic coverage: does the attempt address every opponent argument in order? "
        "A strong attempt flows through the opponent's case point by point, leaves no gaps, and "
        "uses signposting ('on their first argument...', 'on their second contention...')."
    ),
}

_DEFAULT_SKILL_GUIDANCE = (
    "Evaluate whether the debater's response demonstrates the targeted skill clearly and "
    "specifically. Score based on how well the attempt addresses the drill's prompt and "
    "satisfies the stated success criteria."
)

_SYSTEM_PROMPT = """\
You are a PF debate coach evaluating a student's drill attempt.

Rules:
- Be debate-native. Use correct PF terminology. Do not give generic public speaking feedback unless delivery is the drill target.
- Ground every observation in what the transcript actually says. Do not invent content.
- Be honest but encouraging. Do not inflate scores.
- Score on a 1-100 scale:
  90–100 = excellent (met all criteria clearly and with precision)
  70–89  = solid (met most criteria, minor gaps)
  50–69  = developing (met some criteria, significant gaps remain)
  30–49  = needs work (attempted but missed key criteria)
  1–29   = insufficient (did not meaningfully attempt the drill)\
"""


# ── Main function ──────────────────────────────────────────────────────────────

def score_drill_attempt(
    *,
    drill_title: str,
    skill_target: str,
    instructions: Optional[str],
    success_criteria: list[str],
    source_weakness: Optional[str],
    time_limit_seconds: Optional[int],
    difficulty: str,
    transcript: str,
) -> DrillAttemptFeedback:
    """Score a drill attempt transcript against the drill's success criteria.

    Returns a DrillAttemptFeedback on success.
    Raises DrillScoringError on LLM failure or unparseable response.
    """
    client = openai.OpenAI(api_key=settings.openai_api_key)
    skill_guidance = _SKILL_GUIDANCE.get(skill_target, _DEFAULT_SKILL_GUIDANCE)

    criteria_block = (
        "\n".join(f"- {c}" for c in success_criteria)
        if success_criteria
        else "No explicit criteria — use the drill prompt as the standard."
    )

    instructions_block = instructions.strip() if instructions else "No step-by-step instructions provided."
    time_line = f"Time limit: {time_limit_seconds}s." if time_limit_seconds else ""
    weakness_line = f"Original weakness this drill targets: {source_weakness}" if source_weakness else ""

    user_prompt = f"""\
Drill: {drill_title}
Skill target: {skill_target} | Difficulty: {difficulty}
{time_line}
{weakness_line}

Instructions:
{instructions_block}

Success criteria:
{criteria_block}

Skill-specific rubric:
{skill_guidance}

--- ATTEMPT TRANSCRIPT ---
{transcript.strip()}
--- END TRANSCRIPT ---

Respond with a JSON object matching this exact schema:
{{
  "score": <integer 1-100>,
  "met_success_criteria": <boolean>,
  "feedback_summary": "<2-3 sentence coaching verdict — must reference something specific from the transcript>",
  "strengths": ["<1-3 specific debate-native strengths>"],
  "improvements": ["<1-3 specific things to fix, each with how to fix>"],
  "next_instruction": "<one concrete next action the student should take>"
}}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=600,
        )
    except Exception as exc:
        logger.error(
            "score_drill_attempt: openai call failed | skill=%s | exc_type=%s",
            skill_target, type(exc).__name__,
        )
        raise DrillScoringError(f"Scoring LLM call failed: {type(exc).__name__}") from exc

    raw = response.choices[0].message.content or "{}"

    try:
        data = json.loads(raw)
        score_val = max(1, min(100, int(data.get("score", 50))))
        met = bool(data.get("met_success_criteria", False))
        feedback = DrillAttemptFeedback(
            score=score_val,
            met_success_criteria=met,
            feedback_summary=str(data.get("feedback_summary", "")),
            strengths=[str(s) for s in (data.get("strengths") or [])[:3]],
            improvements=[str(s) for s in (data.get("improvements") or [])[:3]],
            next_instruction=str(data.get("next_instruction", "")),
            should_retry=(score_val < 70 or not met),
        )
    except Exception as exc:
        logger.error(
            "score_drill_attempt: parse failed | raw=%.200r | exc=%s", raw, exc
        )
        raise DrillScoringError("Failed to parse scoring response") from exc

    logger.info(
        "score_drill_attempt: scored | score=%d | met_criteria=%s | skill=%s",
        feedback.score, feedback.met_success_criteria, skill_target,
    )
    return feedback
