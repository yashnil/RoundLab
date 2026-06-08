"""Post-LLM structured issue calibration.

Pure functions — no LLM calls, no network.

Responsibilities:
1. Normalize issue_type synonyms (via evals.metrics mapping).
2. Deduplicate issue_types — keep highest-severity instance per type.
3. Add missing HIGH/MEDIUM confidence signals that the LLM missed.
4. Suppress unsupported quality FPs when the quality gate budget is low.
5. Re-sort by severity (high → medium → low).

Works with plain dicts to avoid circular imports with feedback_generation.
The calling code converts DebateIssue ↔ dict as needed.
"""

from __future__ import annotations

import logging

from app.services.debate_signal_detection import DebateSignal, DebateSignalReport

logger = logging.getLogger(__name__)

# Issue types that are about argument quality (subject to quality gate suppression)
_QUALITY_ISSUE_TYPES: frozenset[str] = frozenset({
    "weak_evidence",
    "missing_warrant",
    "unclear_impact",
})

# Issue types that represent debate strategy / rules violations (harder to suppress)
_STRUCTURAL_ISSUE_TYPES: frozenset[str] = frozenset({
    "no_clash",
    "dropped_argument",
    "new_argument",
    "no_weighing",
    "weak_extension",
    "organization",
    "delivery",
})

_SEVERITY_RANK: dict[str, int] = {"high": 3, "medium": 2, "low": 1}

_SIGNAL_TO_DRILL: dict[str, str] = {
    "new_argument": "extensions",
    "no_clash": "clash",
    "weak_evidence": "evidence",
    "missing_warrant": "warranting",
    "dropped_argument": "drops",
    "no_weighing": "weighing",
    "unclear_impact": "warranting",
    "weak_extension": "extensions",
    "organization": "line_by_line",
    "delivery": "judge_adaptation",
}

_SIGNAL_TITLES: dict[str, str] = {
    "new_argument": "New evidence introduced in late speech",
    "no_clash": "Rebuttal lacks direct engagement with opponent",
    "weak_evidence": "Evidence cited without verifiable attribution",
    "missing_warrant": "Claim made without causal mechanism",
    "dropped_argument": "Opponent argument left unanswered",
    "no_weighing": "Impacts extended but never compared",
    "unclear_impact": "Impact too abstract to evaluate",
    "weak_extension": "Argument extended without re-establishing warrant",
}


def _rank(severity: str) -> int:
    return _SEVERITY_RANK.get(severity, 0)


def _normalize(raw: str) -> str:
    """Normalize issue_type via synonym map — same logic as evals/metrics.py."""
    try:
        from evals.metrics import normalize_issue_type
        return normalize_issue_type(raw) or raw.strip().lower().replace("-", "_").replace(" ", "_")
    except ImportError:
        return raw.strip().lower().replace("-", "_").replace(" ", "_")


def _signal_to_issue_dict(signal: DebateSignal) -> dict:
    """Convert a DebateSignal into a DebateIssue-compatible dict."""
    severity = "high" if signal.confidence == "high" else "medium"
    drill = _SIGNAL_TO_DRILL.get(signal.issue_type, "warranting")
    title = _SIGNAL_TITLES.get(signal.issue_type, signal.issue_type.replace("_", " ").title())
    return {
        "issue_type": signal.issue_type,
        "severity": severity,
        "title": title,
        "explanation": signal.reason,
        "why_it_matters": f"Debate signal: {signal.reason}",
        "recommendation": f"Review {drill} drills to address this.",
        "affected_argument_labels": [],
        "recommended_drill_type": drill,
        "_from_detector": True,  # internal flag, stripped before returning
    }


def calibrate_structured_issues(
    issue_dicts: list[dict],
    signals: DebateSignalReport,
    speech_type: str,
) -> list[dict]:
    """Calibrate LLM-generated structured issues using detector signals.

    Args:
        issue_dicts: list of DebateIssue dicts from the LLM
        signals: DebateSignalReport from detect_debate_signals()
        speech_type: e.g. 'constructive', 'rebuttal', etc.

    Returns:
        Calibrated list of issue dicts, sorted by severity.
    """
    if not issue_dicts and not signals.signals:
        return []

    # ── Step 1: Normalize issue_types ─────────────────────────────────────────
    normalized: list[dict] = []
    for d in issue_dicts:
        raw = d.get("issue_type", "")
        norm = _normalize(raw)
        if norm:
            item = dict(d)
            item["issue_type"] = norm
            normalized.append(item)
        else:
            logger.debug("calibrate: dropping issue with unrecognized type %r", raw)

    # ── Step 2: Deduplicate — keep highest severity per issue_type ─────────────
    seen: dict[str, dict] = {}
    for item in normalized:
        t = item["issue_type"]
        if t not in seen or _rank(item.get("severity", "low")) > _rank(seen[t].get("severity", "low")):
            seen[t] = item
    deduped: list[dict] = list(seen.values())

    present_types: set[str] = {i["issue_type"] for i in deduped}

    # ── Step 3: Add missing signal-backed issues ───────────────────────────────
    for sig in signals.signals:
        if sig.issue_type in present_types:
            continue
        if sig.confidence in ("high", "medium"):
            new_issue = _signal_to_issue_dict(sig)
            deduped.append(new_issue)
            present_types.add(sig.issue_type)
            logger.debug(
                "calibrate: added %s (%s confidence) from detector signal",
                sig.issue_type,
                sig.confidence,
            )

    # ── Step 4: Quality gate — suppress unsupported quality FPs ───────────────
    budget = signals.quality_gate.recommended_issue_budget
    signal_types: set[str] = {s.issue_type for s in signals.signals}

    if budget <= 1:
        structural = [i for i in deduped if i["issue_type"] in _STRUCTURAL_ISSUE_TYPES]
        quality = [i for i in deduped if i["issue_type"] in _QUALITY_ISSUE_TYPES]

        if budget == 0:
            # Strong speech: only keep quality issues that came from the detector
            quality_keep = [q for q in quality if q.get("_from_detector") or q["issue_type"] in signal_types]
            logger.debug(
                "calibrate: budget=0 → suppressed %d unsupported quality FPs",
                len(quality) - len(quality_keep),
            )
        else:
            # budget == 1: keep at most 1 quality issue; prefer detector-backed
            signal_quality = [q for q in quality if q.get("_from_detector") or q["issue_type"] in signal_types]
            unsupported = [q for q in quality if q not in signal_quality]
            quality_keep = signal_quality if signal_quality else unsupported[:1]

        deduped = structural + quality_keep

    # ── Step 5: Clean internal flags and sort by severity ─────────────────────
    result = []
    for item in deduped:
        clean = {k: v for k, v in item.items() if k != "_from_detector"}
        result.append(clean)

    result.sort(key=lambda i: _rank(i.get("severity", "low")), reverse=True)
    return result
