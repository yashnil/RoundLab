"""Optional LLM card refiner for the Evidence Studio.

When an OpenAI key is configured, this produces a smarter tagline, read-aloud
highlight selection, warrant/impact, and debate-prep coaching than the
deterministic pipeline. It NEVER invents evidence text: the body stays exact
source text, and the LLM may only choose quote substrings from the supplied
passage. Every returned quote is validated against exact offsets and the whole
result is run through validate_read_aloud_card; on any failure the caller falls
back to the deterministic BM25/pysbd pipeline.

Public entry point: refine_card_with_llm(...) -> RefinedCardResult | None
"""

from __future__ import annotations

import logging
from typing import Optional

from pydantic import BaseModel

from app.config import get_openai_api_key, settings
from app.models.research import RefinedCardResult, SelectedSpan

logger = logging.getLogger(__name__)


# ── LLM structured-output schema ───────────────────────────────────────────────

class _RefinerOutput(BaseModel):
    tagline: str = ""
    read_aloud_quotes: list[str] = []
    warrant: str = ""
    impact: str = ""
    what_this_card_proves: str = ""
    strategic_strength: str = ""
    potential_weakness: str = ""
    likely_counterargument: str = ""
    best_response: str = ""
    crossfire_question: str = ""
    crossfire_answer: str = ""
    best_pairing: str = ""
    weighing_angle: str = ""
    best_use: str = "contention"


_VALID_BEST_USE = {
    "contention", "rebuttal", "summary", "final_focus", "crossfire", "weighing",
}


def _system_prompt(strict: bool) -> str:
    base = (
        "You are an elite Public Forum debate coach helping a student cut and use an "
        "evidence card. You will be given a source passage, the claim the student wants "
        "to support, the topic, the side, and the card's role.\n\n"
        "ABSOLUTE RULES:\n"
        "1. The card body is EXACT source text — never rewrite, paraphrase, or invent it.\n"
        "2. read_aloud_quotes MUST be exact substrings copied verbatim from the passage.\n"
        "3. The read_aloud_quotes, read in order, must form ONE coherent argument a "
        "debater can read aloud — complete clauses/sentences, not disconnected shards.\n"
        "4. Do NOT highlight the whole passage; choose the read-aloud core only "
        "(roughly 30-60% of the passage).\n"
        "5. tagline is a punchy DEBATE CLAIM in your own words (<= 18 words), not the "
        "article title and not a copied source fragment; it must start with a capital "
        "and read as a complete claim.\n"
        "6. warrant explains why the source's logic supports the claim; impact explains "
        "why it matters in the round. Both must be specific to THIS card (use the actual "
        "entities/cases), natural, and free of filler like 'if the judge buys this'.\n"
        "7. best_use is one of: contention, rebuttal, summary, final_focus, crossfire, weighing.\n"
    )
    if strict:
        base += (
            "\nSTRICTER PASS: your previous quotes were incoherent or too long. Choose "
            "FEWER, COMPLETE sentences that read cleanly aloud and clearly state the claim.\n"
        )
    return base


def _call_llm(passage: str, claim: str, topic: str, side: str, role: str,
              source_metadata: dict, strict: bool) -> Optional[_RefinerOutput]:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=get_openai_api_key())
        meta_line = ", ".join(
            f"{k}: {v}" for k, v in (source_metadata or {}).items() if v
        ) or "unknown"
        user_msg = (
            f"TOPIC: {topic or 'n/a'}\n"
            f"CLAIM TO SUPPORT: {claim or 'n/a'}\n"
            f"SIDE: {side or 'n/a'}\n"
            f"CARD ROLE: {role or 'direct_support'}\n"
            f"SOURCE: {meta_line}\n\n"
            f"PASSAGE (the card body — exact text):\n\"\"\"\n{passage[:6000]}\n\"\"\"\n"
        )
        resp = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _system_prompt(strict)},
                {"role": "user", "content": user_msg},
            ],
            response_format=_RefinerOutput,
            temperature=0.2,
            max_tokens=900,
        )
        return resp.choices[0].message.parsed
    except Exception as exc:
        logger.debug("LLM refiner call failed: %s", exc)
        return None


def _validate_quotes(passage: str, quotes: list[str]) -> list[SelectedSpan]:
    """Map each quote to an exact offset in the passage. Quotes that are not exact
    substrings are rejected (never snapped into something the source didn't say).
    Searches monotonically to preserve order."""
    spans: list[SelectedSpan] = []
    search_from = 0
    for q in quotes:
        qt = (q or "").strip()
        if len(qt) < 8:
            continue
        pos = passage.find(qt, search_from)
        if pos == -1:
            pos = passage.find(qt)  # allow out-of-order, but must be exact
        if pos == -1:
            logger.debug("LLM quote not found in passage, rejecting: %r", qt[:50])
            continue
        spans.append(SelectedSpan(
            start=pos, end=pos + len(qt), text=passage[pos:pos + len(qt)],
            sentence_index=len(spans), rationale="llm_highlight",
        ))
        search_from = max(search_from, pos)
    spans.sort(key=lambda s: s.start)
    return spans


def _build_result(passage: str, out: _RefinerOutput, spans, validation) -> RefinedCardResult:
    best_use = out.best_use if out.best_use in _VALID_BEST_USE else "contention"
    return RefinedCardResult(
        tagline=out.tagline.strip(),
        warrant=out.warrant.strip(),
        impact=out.impact.strip(),
        what_this_card_proves=out.what_this_card_proves.strip(),
        strategic_strength=out.strategic_strength.strip(),
        potential_weakness=out.potential_weakness.strip(),
        likely_counterargument=out.likely_counterargument.strip(),
        best_response=out.best_response.strip(),
        crossfire_question=out.crossfire_question.strip(),
        crossfire_answer=out.crossfire_answer.strip(),
        best_pairing=out.best_pairing.strip(),
        weighing_angle=out.weighing_angle.strip(),
        best_use=best_use,
        cut_body=passage,
        read_aloud_spans=spans,
        validation=validation,
    )


def llm_refiner_available() -> bool:
    """True when the refiner can run (key present + feature enabled)."""
    return bool(get_openai_api_key()) and bool(getattr(settings, "research_enable_llm_refiner", True))


def refined_to_intelligence(refined: RefinedCardResult):
    """Convert a RefinedCardResult into a CardIntelligence (LLM-written coaching)."""
    from app.models.research import CardIntelligence
    return CardIntelligence(
        why_this_card=refined.what_this_card_proves or refined.warrant,
        supports_claim_because=[refined.strategic_strength] if refined.strategic_strength else [],
        best_use=refined.best_use,  # type: ignore[arg-type]
        warrant_analysis=refined.warrant,
        impact_analysis=refined.impact,
        potential_weakness=refined.potential_weakness,
        how_to_answer_weakness=refined.best_response,
        opponent_response=refined.likely_counterargument,
        crossfire_question=refined.crossfire_question,
        crossfire_answer=refined.crossfire_answer,
        best_pairing=refined.best_pairing,
        weighing_angle=refined.weighing_angle,
        limitations=[refined.potential_weakness] if refined.potential_weakness else [],
    )


def refine_card_with_llm(
    base_passage: str,
    current_cut: Optional[str] = None,
    topic: str = "",
    claim: str = "",
    side: str = "",
    role: str = "",
    source_metadata: Optional[dict] = None,
    entities: Optional[list] = None,
) -> Optional[RefinedCardResult]:
    """Refine a card with the LLM. Returns None when unavailable or when the
    output cannot be validated (caller then uses the deterministic pipeline)."""
    from app.services.card_cutting import validate_read_aloud_card

    if not llm_refiner_available():
        return None
    passage = (base_passage or "").strip()
    if len(passage) < 60:
        return None

    for strict in (False, True):
        out = _call_llm(passage, claim, topic, side, role, source_metadata or {}, strict)
        if out is None:
            return None
        spans = _validate_quotes(passage, out.read_aloud_quotes)
        if not spans:
            continue
        validation = validate_read_aloud_card(passage, spans)
        if validation.passed:
            return _build_result(passage, out, spans, validation)
        # else: retry once with stricter instructions
    return None
