"""Pass 15 — Judge Adaptation Orchestrator.

Loads source material from Supabase, runs adaptation pipeline, and returns
a fully structured JudgeAdaptationResult.

Immutability contract:
    - Evidence body is read-only. Never written to output.
    - Support verdict passes through without modification.
    - Citation metadata passes through without modification.
"""

from __future__ import annotations

import logging
from typing import Optional

from app.models.judge_adaptation import (
    AdaptationRisk,
    EvidencePresentationGuide,
    JudgeAdaptationResult,
    JudgeType,
)
from app.services.adaptation_risk_checker import check_all_risks, critical_risks
from app.services.adaptation_rules import get_adaptation_changes
from app.services.frontline_adapter import adapt_frontline_for_judge
from app.services.judge_profiles import get_builtin_profile
from app.services.judge_readiness_scorer import score_judge_readiness
from app.services.speech_plan_adapter import adapt_speech_for_judge
from app.services.supabase_client import get_supabase

logger = logging.getLogger(__name__)

_PURPOSES = {
    "evidence": "Support a specific claim with quoted source material",
    "argument": "Present a complete claim-warrant-evidence-impact structure",
    "frontline": "Respond to the opponent's argument in rebuttal",
    "section": "Present a blockfile section to a judge",
    "summary": "Extend and weigh key arguments in summary",
    "final_focus": "Crystallize voters for the judge in final focus",
    "transcript": "Deliver a prepared speech",
}

_GOALS = {
    "lay": "Tell a clear, jargon-free story that connects to real-world consequences",
    "parent": "Provide context so the judge understands the debate and your fairness claim",
    "flow": "Give the judge every label and extension they need to flow your arguments",
    "technical": "Exploit every concession, state burdens, and separate offense from defense",
    "coach": "Demonstrate strategically sound debate habits and complete argument structure",
}


def _load_card(card_id: str, user_id: str) -> Optional[dict]:
    try:
        sb = get_supabase()
        result = sb.table("evidence_cards").select("*").eq("id", card_id).limit(1).execute()
        if not result.data:
            return None
        card = result.data[0]
        if card.get("user_id") != user_id:
            return None
        return card
    except Exception as exc:
        logger.warning("_load_card: %s", exc)
        return None


def _load_frontline(frontline_id: str, user_id: str) -> tuple[Optional[dict], list[dict]]:
    try:
        sb = get_supabase()
        fl = sb.table("frontlines").select("*").eq("id", frontline_id).limit(1).execute()
        if not fl.data or fl.data[0].get("user_id") != user_id:
            return None, []
        frontline = fl.data[0]
        resp = sb.table("frontline_responses").select("*").eq("frontline_id", frontline_id).order("priority").execute()
        return frontline, resp.data or []
    except Exception as exc:
        logger.warning("_load_frontline: %s", exc)
        return None, []


def _load_argument(argument_id: str, user_id: str) -> Optional[dict]:
    try:
        sb = get_supabase()
        result = sb.table("arguments").select("*").eq("id", argument_id).limit(1).execute()
        if not result.data or result.data[0].get("user_id") != user_id:
            return None
        return result.data[0]
    except Exception as exc:
        logger.warning("_load_argument: %s", exc)
        return None


def _build_evidence_guide(
    card: dict,
    judge_type: JudgeType,
    risks: list[AdaptationRisk],
) -> EvidencePresentationGuide:
    """Build evidence presentation guidance WITHOUT including card body."""
    tag = card.get("tag") or card.get("generated_tag_text") or ""
    source_domain = card.get("source_domain") or ""
    publication = card.get("publication") or ""
    author = card.get("author") or ""
    pub_date = card.get("published_date") or ""
    source_name = publication or source_domain or "the source"
    author_str = f"{author} ({pub_date[:4]})" if author and pub_date else (author or pub_date[:4] if pub_date else "")

    guide = EvidencePresentationGuide(
        card_id=card.get("id", ""),
        card_tag=tag[:200],
        judge_type=judge_type,
        risks=[r for r in risks if r.source_ref == card.get("id")],
    )

    if judge_type in ("lay", "parent"):
        guide.who_is_source = f"{author_str} from {source_name}" if author_str else source_name
        guide.what_source_found = f"Found: {tag[:100]}" if tag else "See evidence"
        guide.why_it_matters = "Because this directly affects [explain real-world consequence]"
        guide.one_sentence_causal = "This matters because [mechanism] leads to [outcome] for [group]."
        guide.can_be_paraphrased = True
        guide.estimated_read_time_seconds = 10

    elif judge_type == "flow":
        guide.short_citation = f"{author.split(',')[0].strip() if author else source_name}, {pub_date[:4] if pub_date else 'nd'}"
        guide.flow_warrant = "The mechanism is [warrant from evidence]"
        guide.flow_impact = tag[:80] if tag else "[impact label]"
        guide.role_on_flow = "Offense: supports [contention label]"
        guide.can_be_paraphrased = False
        guide.estimated_read_time_seconds = 20

    elif judge_type == "technical":
        verdict = card.get("support_verdict") or "unknown"
        guide.support_limit = f"Support verdict: {verdict}"
        guide.relevant_qualifier = "Note any qualifiers in the source"
        guide.concession_interaction = "Cross-reference with opponent's conceded claims"
        guide.card_role = "offense"
        guide.can_be_paraphrased = False
        guide.estimated_read_time_seconds = 25

    elif judge_type == "coach":
        guide.best_practice_note = "Introduce source credentials briefly before reading"
        guide.methodological_limitation = "Acknowledge scope if relevant to the argument"
        guide.can_be_paraphrased = False
        guide.estimated_read_time_seconds = 20

    return guide


def generate_adaptation(
    user_id: str,
    judge_type: JudgeType,
    source_type: str,
    source_id: str,
    workspace_id: Optional[str] = None,
) -> JudgeAdaptationResult:
    """
    Main orchestrator for judge adaptation.

    Args:
        user_id: requesting user
        judge_type: target judge type
        source_type: "evidence", "argument", "frontline", "summary", "final_focus", etc.
        source_id: ID of the source material
        workspace_id: optional prep workspace

    Returns:
        JudgeAdaptationResult (no evidence body text included)
    """
    profile = get_builtin_profile(judge_type)
    original_purpose = _PURPOSES.get(source_type, "Present prepared material")
    judge_goal = _GOALS.get(judge_type, "Adapt effectively for the judge")

    risks: list[AdaptationRisk] = []
    changes: list = []
    evidence_guide = None
    frontline_adaptation = None
    speech_plan = None

    # ── Evidence ──────────────────────────────────────────────────────────────
    if source_type == "evidence":
        card = _load_card(source_id, user_id)
        if card:
            tag = card.get("tag") or ""
            body = card.get("body_text") or ""
            verdict = card.get("support_verdict")
            freshness = None  # would be loaded from Pass 14 if available

            risks = check_all_risks(
                judge_type,
                card_id=source_id,
                tag=tag,
                original_body=body,
                support_verdict=verdict,
                freshness_state=freshness,
                has_warrant="because" in body.lower() or "mechanism" in body.lower(),
                has_real_world_link=bool(card.get("source_domain")),
                evidence_count=1,
                has_analysis=True,
            )

            changes = get_adaptation_changes(
                judge_type,
                tag=tag,
                body_excerpt=body[:300],
                has_evidence=True,
            )

            evidence_guide = _build_evidence_guide(card, judge_type, risks)

            readiness = score_judge_readiness(
                judge_type, source_type, source_id, user_id,
                risks=risks,
                has_changes=bool(changes),
                change_count=len(changes),
                evidence_count=1,
            )

            what_emphasize = {
                "lay": ["Real-world consequences", "Clear causal chain", "Why it matters to ordinary people"],
                "parent": ["Who the source is", "What they found", "Why it's fair evidence"],
                "flow": ["Short citation", "Claim and warrant label", "Impact label"],
                "technical": ["Support verdict", "Qualifier", "Concession interaction"],
                "coach": ["Source credentials", "Exact claim limit", "Best-practice delivery"],
            }.get(judge_type, [])

            what_simplify = {
                "lay": ["Technical qualifiers", "Methodology details", "Citation format"],
                "parent": ["Debate jargon", "Policy background assumed knowledge"],
                "flow": ["Narrative framing", "Real-world analogies"],
                "technical": ["Narrative substitution", "Rhetorical framing"],
                "coach": [],
            }.get(judge_type, [])

            return JudgeAdaptationResult(
                user_id=user_id,
                judge_type=judge_type,
                source_type="evidence",  # type: ignore[arg-type]
                source_id=source_id,
                original_purpose=original_purpose,
                judge_goal=judge_goal,
                changes=changes,
                risks=risks,
                critical_risks=critical_risks(risks),
                evidence_guide=evidence_guide,
                what_to_emphasize=what_emphasize,
                what_to_simplify=what_simplify,
                what_must_remain_explicit=["Evidence body text", "Source citation", "Support verdict"],
                what_can_be_shortened=["Methodology", "Background context"] if judge_type in ("flow", "technical") else [],
                preserved_source_refs=[source_id],
                estimated_seconds=evidence_guide.estimated_read_time_seconds or 20 if evidence_guide else 20,
            )

    # ── Frontline ─────────────────────────────────────────────────────────────
    if source_type == "frontline":
        frontline, responses = _load_frontline(source_id, user_id)
        if frontline:
            risks = check_all_risks(
                judge_type,
                has_warrant=True,
                has_real_world_link=False,
                response_count=len(responses) if responses else 0,
            )
            frontline_adaptation = adapt_frontline_for_judge(
                frontline, responses or [], judge_type=judge_type
            )
            changes = frontline_adaptation.changes
            risks = frontline_adaptation.risks

    # ── Summary / Final Focus ─────────────────────────────────────────────────
    if source_type in ("summary", "final_focus"):
        stage = "summary" if source_type == "summary" else "final_focus"
        speech_plan = adapt_speech_for_judge(
            stage,  # type: ignore[arg-type]
            judge_type,
            argument_count=2,
            has_extensions=True,
            has_weighing=True,
        )
        risks = speech_plan.risks
        changes = speech_plan.changes

    # ── Argument ──────────────────────────────────────────────────────────────
    if source_type == "argument":
        argument = _load_argument(source_id, user_id)
        tag = argument.get("claim") if argument else ""
        changes = get_adaptation_changes(
            judge_type, tag=tag,
            has_evidence=True,
            has_explicit_labels=False,
        )
        risks = check_all_risks(
            judge_type,
            tag=tag,
            has_warrant=True,
            has_real_world_link=False,
        )

    # ── Generic fallback ──────────────────────────────────────────────────────
    if not changes and not risks:
        changes = get_adaptation_changes(judge_type)
        risks = []

    return JudgeAdaptationResult(
        user_id=user_id,
        judge_type=judge_type,
        source_type=source_type,  # type: ignore[arg-type]
        source_id=source_id,
        original_purpose=original_purpose,
        judge_goal=judge_goal,
        changes=changes,
        risks=risks,
        critical_risks=critical_risks(risks),
        evidence_guide=evidence_guide,
        frontline_adaptation=frontline_adaptation,
        speech_plan=speech_plan,
        what_to_emphasize=[],
        what_to_simplify=[],
        what_must_remain_explicit=["Evidence body text", "Source citation", "Support verdict"],
        what_can_be_shortened=[],
        preserved_source_refs=[source_id],
        estimated_seconds=120,
    )
