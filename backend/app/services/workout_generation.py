"""
Deterministic Tournament Prep Workout Generation — v1.

No LLM calls. Uses existing feedback/drill/delivery/evidence data to build
a 3–5 step workout that tells the student exactly what to practice next.

Priority order:
  1. Highest-severity structured issues from feedback
  2. Incomplete drills (as supplemental steps)
  3. Evidence risk (unsupported / partially_supported checks)
  4. Severe delivery issue (pacing or filler)
  5. Speech-type specific final technique step
  6. Full re-record (always appended last)
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

# ── Issue → step templates ──────────────────────────────────────────────────

_ISSUE_TEMPLATES: dict[str, dict] = {
    "missing_warrant": {
        "title": "Warrant Clarity Rep",
        "category": "argument",
        "focus": "warranting",
        "problem_prefix": "Your claim lacks a clear causal mechanism.",
        "instruction": (
            "Take the weakest argument in your speech. Deliver it aloud as three beats: "
            "(1) the claim, (2) WHY the mechanism works — the warrant, (3) what world that produces — the impact. "
            "Practice until you can do this in under 45 seconds without stopping."
        ),
        "success_criteria": "You can articulate the causal chain in one breath without pausing.",
        "estimated_minutes": 4,
    },
    "weak_evidence": {
        "title": "Evidence Alignment Rep",
        "category": "evidence",
        "focus": "evidence",
        "problem_prefix": "Your evidence does not clearly support your claim.",
        "instruction": (
            "Read your card aloud. Restate your claim using ONLY language from the card. "
            "If your claim goes beyond what the card says, narrow it. "
            "Write a tag line that is a direct inference from card language — not an extrapolation."
        ),
        "success_criteria": "Tag line and claim match the card language exactly with no overreach.",
        "estimated_minutes": 3,
    },
    "unclear_impact": {
        "title": "Impact Development Rep",
        "category": "argument",
        "focus": "weighing",
        "problem_prefix": "Your impact is vague or unquantified.",
        "instruction": (
            "Re-state your strongest impact with three additions: (1) magnitude — how many people affected, "
            "(2) timeframe — when this happens, (3) probability — how likely. "
            "Practice stating all three in under 30 seconds without notes."
        ),
        "success_criteria": "Impact has magnitude, timeframe, and probability stated explicitly.",
        "estimated_minutes": 3,
    },
    "no_weighing": {
        "title": "Weighing Compression Rep",
        "category": "argument",
        "focus": "weighing",
        "problem_prefix": "You are not comparing why your impacts outweigh theirs.",
        "instruction": (
            "Write a 60-second weighing block: (1) name their best impact, "
            "(2) name your best impact, (3) explain why yours outweighs using one mechanism "
            "(magnitude, timeframe, probability, or reversibility). Deliver it under 60 seconds."
        ),
        "success_criteria": "Weighing block names both sides and uses at least one explicit mechanism.",
        "estimated_minutes": 4,
    },
    "dropped_argument": {
        "title": "Coverage Sweep Rep",
        "category": "argument",
        "focus": "drops",
        "problem_prefix": "You left an opponent argument without a direct response.",
        "instruction": (
            "List every opponent argument from memory. For each one: "
            "(a) recite the response you gave in your speech, or "
            "(b) practice a one-sentence fallback response right now. "
            "No argument should be without at least a fallback."
        ),
        "success_criteria": "Every opponent argument has at least one sentence of direct response.",
        "estimated_minutes": 3,
    },
    "weak_extension": {
        "title": "Extension Quality Rep",
        "category": "argument",
        "focus": "extensions",
        "problem_prefix": "Your extensions are losing warrant context.",
        "instruction": (
            "Re-extend your top argument in 45 seconds: "
            "(1) name the argument, (2) explain why their response doesn't take out the warrant, "
            "(3) re-state the impact. Time yourself and stop at 45 seconds."
        ),
        "success_criteria": "Extension names the argument, addresses the rebuttal, re-establishes impact — under 45 sec.",
        "estimated_minutes": 3,
    },
    "no_clash": {
        "title": "Direct Clash Rep",
        "category": "argument",
        "focus": "clash",
        "problem_prefix": "Your speech restates your case without engaging their arguments directly.",
        "instruction": (
            "Take their strongest argument. Write a response that: "
            "(1) grants something small if true, (2) turns it or gives a straight no-link, "
            "(3) explains why your world still wins even if true. "
            "The response must directly name their argument — not generic rebuttal."
        ),
        "success_criteria": "Response directly names the opponent argument and explains why it fails.",
        "estimated_minutes": 3,
    },
    "new_argument": {
        "title": "Speech Discipline Rep",
        "category": "argument",
        "focus": "drops",
        "problem_prefix": "You introduced new arguments at the wrong speech position.",
        "instruction": (
            "Re-read your speech rules. Practice your speech again without adding any claim "
            "that was not introduced in the constructive. "
            "If you catch yourself adding new material, pause and redirect to extending existing arguments."
        ),
        "success_criteria": "No new claims — only extensions and weighing on arguments already in round.",
        "estimated_minutes": 3,
    },
    "organization": {
        "title": "Signposting Rep",
        "category": "argument",
        "focus": "warranting",
        "problem_prefix": "Your speech lacked clear structure, making it difficult to follow.",
        "instruction": (
            "Re-read your transcript. Identify each argument. Re-deliver with explicit signposts: "
            "'First, off their C1…', 'Second, our C2…', 'Extend our second advantage…'. "
            "Use a number and label before every argument block."
        ),
        "success_criteria": "Every argument is introduced with a number and label before the content.",
        "estimated_minutes": 4,
    },
    "delivery": {
        "title": "Delivery Pacing Rep",
        "category": "delivery",
        "focus": "delivery",
        "problem_prefix": "Delivery issues are reducing argument clarity.",
        "instruction": (
            "Re-read your transcript aloud at a comfortable pace. Every time you catch a filler word, "
            "stop, take a breath, and restart that sentence without it. "
            "Target: one full pass with fewer than half your previous filler count."
        ),
        "success_criteria": "Full pass at a clear pace with filler word count reduced by 50%.",
        "estimated_minutes": 3,
    },
}

# ── Speech-type specific technique step ────────────────────────────────────

_TYPE_TECHNIQUE_STEP: dict[str, dict] = {
    "constructive": {
        "title": "Signpost and Impact Check",
        "category": "argument",
        "focus": "warranting",
        "problem": "Your constructive needs clear structure and complete impacts before re-recording.",
        "instruction": (
            "Run through your speech one more time. After each claim, check: "
            "does the warrant explain WHY? Does the impact tell the judge what world is at stake? "
            "Fix any that are missing before you re-record."
        ),
        "success_criteria": "Every argument has claim → warrant → impact in order.",
        "estimated_minutes": 3,
    },
    "rebuttal": {
        "title": "Line-by-Line Coverage Check",
        "category": "argument",
        "focus": "drops",
        "problem": "Run a final coverage sweep before re-recording your rebuttal.",
        "instruction": (
            "List all opponent arguments from memory. For each one, confirm: "
            "did you directly address it? If not, practice a one-sentence fallback response. "
            "You must have something — even a short response — for every argument."
        ),
        "success_criteria": "No opponent argument left unaddressed.",
        "estimated_minutes": 3,
    },
    "summary": {
        "title": "Collapse Decision Check",
        "category": "argument",
        "focus": "collapse",
        "problem": "Pick your one strongest voting issue before re-recording your summary.",
        "instruction": (
            "From your arguments, identify the one with: "
            "(1) you're winning the warrant, (2) big impact, (3) their weakest response. "
            "Extend ONLY that argument in your re-record with full impact and weighing comparison."
        ),
        "success_criteria": "Speech collapses to one voting issue with a clear weighing comparison.",
        "estimated_minutes": 3,
    },
    "final_focus": {
        "title": "Ballot Story Check",
        "category": "argument",
        "focus": "collapse",
        "problem": "Your final focus must open with one voting issue and a ballot instruction.",
        "instruction": (
            "Write one sentence: 'Vote [side] because [voting issue] — "
            "here is why we win it: [warrant]. Here is why it outweighs: [weighing].' "
            "Deliver that sentence FIRST in your re-record. Nothing else matters if the judge "
            "doesn't know your voting issue."
        ),
        "success_criteria": "Speech opens with a clear voting issue and ballot instruction.",
        "estimated_minutes": 2,
    },
}


# ── Focus / skill mapping helpers ───────────────────────────────────────────

def _skill_to_focus(skill: str) -> str:
    mapping: dict[str, str] = {
        "warranting": "warranting",
        "evidence_alignment": "evidence",
        "claim_precision": "evidence",
        "evidence_attribution": "evidence",
        "card_warranting": "evidence",
        "weighing": "weighing",
        "impact_development": "weighing",
        "drops": "drops",
        "line_by_line": "drops",
        "extensions": "extensions",
        "collapse": "collapse",
        "delivery": "delivery",
        "pacing_control": "delivery",
        "filler_reduction": "delivery",
        "clarity_delivery": "delivery",
        "clash": "clash",
    }
    return mapping.get(skill, skill)


def _focus_to_issue_key(focus: str) -> str:
    mapping: dict[str, str] = {
        "warranting": "missing_warrant",
        "evidence": "weak_evidence",
        "weighing": "no_weighing",
        "drops": "dropped_argument",
        "extensions": "weak_extension",
        "collapse": "no_weighing",
        "delivery": "delivery",
        "clash": "no_clash",
    }
    return mapping.get(focus, "missing_warrant")


# ── Public entry point ──────────────────────────────────────────────────────

def generate_tournament_workout(
    speech: dict,
    feedback_report: dict,
    argument_map: Optional[dict],
    drills: list[dict],
    delivery_metrics: Optional[dict] = None,
    evidence_checks: Optional[list[dict]] = None,
) -> dict[str, Any]:
    """
    Build a 3–5 step tournament prep workout from existing report data.
    Returns a dict with keys: steps, re_record_goal, coach_note,
    estimated_minutes, focus_area, generated_from.
    """
    speech_type = speech.get("speech_type") or "constructive"
    raw = feedback_report.get("raw_feedback") or {}
    overall_score: Optional[int] = feedback_report.get("overall_score")
    structured_issues: list[dict] = raw.get("structured_issues") or []
    top_3: list[str] = raw.get("top_3_priorities") or []

    steps: list[dict] = []
    used_focuses: set[str] = set()

    def add_step(
        *,
        title: str,
        category: str,
        focus: str,
        problem: str,
        instruction: str,
        success_criteria: str,
        estimated_minutes: int,
        source: str,
        linked_drill_id: Optional[str] = None,
    ) -> bool:
        if focus in used_focuses or len(steps) >= 5:
            return False
        used_focuses.add(focus)
        steps.append({
            "id": f"step_{uuid.uuid4().hex[:8]}",
            "title": title,
            "category": category,
            "focus": focus,
            "estimated_minutes": estimated_minutes,
            "source": source,
            "problem": problem,
            "instruction": instruction,
            "success_criteria": success_criteria,
            "linked_drill_id": linked_drill_id,
            "completed": False,
        })
        return True

    # ── 1. Highest-severity structured issues ─────────────────────────────
    sorted_issues = sorted(
        structured_issues,
        key=lambda i: {"high": 0, "medium": 1, "low": 2}.get(i.get("severity", "low"), 2),
    )
    for issue in sorted_issues:
        if len(steps) >= 3:
            break
        issue_type = issue.get("issue_type", "")
        tmpl = _ISSUE_TEMPLATES.get(issue_type)
        if not tmpl:
            continue
        explanation = issue.get("explanation") or tmpl["problem_prefix"]
        add_step(
            title=tmpl["title"],
            category=tmpl["category"],
            focus=tmpl["focus"],
            problem=explanation[:200],
            instruction=tmpl["instruction"],
            success_criteria=tmpl["success_criteria"],
            estimated_minutes=tmpl["estimated_minutes"],
            source="feedback",
        )

    # ── 2. Incomplete drills ──────────────────────────────────────────────
    incomplete = sorted(
        [d for d in drills if d.get("status") != "completed"],
        key=lambda d: d.get("order", 99),
    )
    for drill in incomplete:
        if len(steps) >= 3:
            break
        skill = drill.get("skill_target") or ""
        focus = _skill_to_focus(skill)
        if focus in used_focuses:
            continue
        tmpl = _ISSUE_TEMPLATES.get(_focus_to_issue_key(focus))
        if not tmpl:
            continue
        sc_list = drill.get("success_criteria") or []
        sc = sc_list[0] if isinstance(sc_list, list) and sc_list else tmpl["success_criteria"]
        add_step(
            title=f"Drill Prep — {drill.get('title', 'Practice Rep')}",
            category="argument",
            focus=focus,
            problem=drill.get("source_weakness") or f"Skill gap detected: {skill}.",
            instruction=drill.get("prompt") or tmpl["instruction"],
            success_criteria=sc if isinstance(sc, str) else tmpl["success_criteria"],
            estimated_minutes=max(2, (drill.get("time_limit_seconds") or 180) // 60),
            source="drill",
            linked_drill_id=drill.get("id"),
        )

    # ── 3. Evidence risk ──────────────────────────────────────────────────
    if evidence_checks and "evidence" not in used_focuses and len(steps) < 4:
        risky = [
            c for c in evidence_checks
            if c.get("support_level") in ("unsupported", "partially_supported")
        ]
        if risky:
            worst = sorted(
                risky,
                key=lambda c: 0 if c.get("support_level") == "unsupported" else 1,
            )[0]
            level = worst.get("support_level", "unsupported")
            label = worst.get("argument_label") or (worst.get("claim_text") or "")[:60]
            if level == "unsupported":
                problem = f"No uploaded card directly supports your argument: \"{label}\"."
                instruction = (
                    "Re-read the card you cited. If it doesn't support the claim, "
                    "narrow the claim to match what the card actually says. "
                    "Tag line must be a direct inference from card language — not an extrapolation."
                )
                success = "Tag line uses language from the card; claim stays within what the card proves."
            else:
                problem = f"Your card only partially supports: \"{label}\"."
                instruction = (
                    "Find the sentence in your card that comes closest to your claim. "
                    "Restate the claim using only that sentence's facts and scope. "
                    "Practice the re-tagged version until the match is exact."
                )
                success = "Card and claim language match precisely; no overreach."
            add_step(
                title="Evidence Card Alignment Rep",
                category="evidence",
                focus="evidence",
                problem=problem,
                instruction=instruction,
                success_criteria=success,
                estimated_minutes=3,
                source="evidence",
            )

    # ── 4. Severe delivery issue ──────────────────────────────────────────
    if delivery_metrics and "delivery" not in used_focuses and len(steps) < 4:
        wpm = delivery_metrics.get("words_per_minute") or 0
        fillers = delivery_metrics.get("filler_word_count") or 0
        pacing = delivery_metrics.get("pacing_band") or "steady"
        score = delivery_metrics.get("delivery_score")

        severe = (
            pacing in ("too_fast", "too_slow")
            or fillers >= 8
            or (score is not None and score < 60)
        )
        if severe:
            if pacing == "too_fast":
                problem = f"You spoke at {round(wpm)} WPM — too fast for judges to follow your arguments."
                instruction = (
                    "Re-read the first 30 seconds of your transcript at 150–165 WPM. "
                    "Count deliberate pauses after each claim. Practice until the warrant section "
                    "is fully intelligible at tournament pace."
                )
                success = "Key warrant section delivered at 150–165 WPM with pauses after each claim."
            elif pacing == "too_slow":
                problem = f"You spoke at {round(wpm)} WPM — at risk of losing time on key arguments."
                instruction = (
                    "Re-read your speech targeting 165–175 WPM. Use a timer. "
                    "Eliminate unnecessary filler phrases that slow you down between arguments."
                )
                success = "Full speech fits 165–175 WPM range without cutting argument content."
            else:
                problem = f"High filler word count ({fillers}) reduces clarity and judge confidence."
                instruction = (
                    "Re-read a 60-second section. Every time you say a filler word, stop, "
                    "take a breath, and restart that sentence cleanly. "
                    "Complete two reps targeting half your original filler count."
                )
                success = "60-second section completed twice with filler count reduced by at least half."
            add_step(
                title="Delivery Control Rep",
                category="delivery",
                focus="delivery",
                problem=problem,
                instruction=instruction,
                success_criteria=success,
                estimated_minutes=3,
                source="delivery",
            )

    # ── 5. Speech-type technique step ────────────────────────────────────
    type_step = _TYPE_TECHNIQUE_STEP.get(speech_type)
    if type_step and len(steps) < 4:
        focus = type_step["focus"]
        if focus not in used_focuses:
            add_step(
                title=type_step["title"],
                category=type_step["category"],
                focus=focus,
                problem=type_step["problem"],
                instruction=type_step["instruction"],
                success_criteria=type_step["success_criteria"],
                estimated_minutes=type_step["estimated_minutes"],
                source="feedback",
            )

    # ── 6. Final re-record step ───────────────────────────────────────────
    re_record_goal = _build_rerecord_goal(overall_score, steps, top_3)
    steps.append({
        "id": f"step_{uuid.uuid4().hex[:8]}",
        "title": "Full Re-record",
        "category": "rerecord",
        "focus": "rerecord",
        "estimated_minutes": 2,
        "source": "feedback",
        "problem": "Apply every fix from the workout above in one continuous speech.",
        "instruction": (
            "Record a full new speech without stopping to correct yourself during delivery. "
            "Finish the speech, then open the new report and compare your score and delivery metrics."
        ),
        "success_criteria": re_record_goal,
        "linked_drill_id": None,
        "completed": False,
    })

    total_minutes = sum(s["estimated_minutes"] for s in steps)
    primary_focus = next(
        (s["focus"] for s in steps if s.get("category") != "rerecord"),
        "warranting",
    )

    return {
        "steps": steps,
        "re_record_goal": re_record_goal,
        "coach_note": _build_coach_note(speech_type, overall_score, steps),
        "estimated_minutes": total_minutes,
        "focus_area": primary_focus,
        "generated_from": {
            "feedback_report_id": feedback_report.get("id"),
            "argument_map_id": argument_map.get("id") if argument_map else None,
            "delivery_metrics_id": delivery_metrics.get("id") if delivery_metrics else None,
        },
    }


def _build_rerecord_goal(
    overall_score: Optional[int],
    steps: list[dict],
    top_3: list[str],
) -> str:
    target = min(overall_score + 10, 100) if overall_score is not None else None
    focus_labels: dict[str, str] = {
        "warranting": "clearer warrants",
        "evidence": "tighter evidence alignment",
        "weighing": "explicit weighing",
        "drops": "full coverage",
        "extensions": "stronger extensions",
        "collapse": "collapse discipline",
        "delivery": "cleaner delivery",
        "clash": "direct clash",
    }
    focuses = [s["focus"] for s in steps if s.get("category") not in ("rerecord",)]
    phrases = [focus_labels[f] for f in focuses[:2] if f in focus_labels]
    if phrases and target:
        return f"Score {target}/100 or higher with {' and '.join(phrases)}."
    elif phrases:
        return f"Demonstrate {' and '.join(phrases)} in the new recording."
    elif target:
        return f"Score {target}/100 or higher in the new report."
    elif top_3:
        return f"Address this in your re-record: {top_3[0]}"
    return "Demonstrate measurable improvement on your top feedback priority."


def _build_coach_note(
    speech_type: str,
    overall_score: Optional[int],
    steps: list[dict],
) -> str:
    type_notes: dict[str, str] = {
        "constructive": "Focus on making every argument structurally complete before the round.",
        "rebuttal": "Coverage and clash win rebuttals. No dropped arguments.",
        "summary": "Collapse to your best argument and weigh — judges vote on the last comparison they hear.",
        "final_focus": "The judge is voting on one voting issue. Make sure they know yours.",
    }
    note = type_notes.get(speech_type, "Work through each step before re-recording.")
    if overall_score is not None and overall_score < 65:
        note += " This speech needs structural repair — address the argument steps before delivery."
    non_rerecord = [s for s in steps if s.get("category") != "rerecord"]
    if len(non_rerecord) >= 4:
        note += " Complete all steps in order — each one builds on the previous."
    return note
