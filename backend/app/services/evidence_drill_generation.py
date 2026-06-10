"""
Deterministic evidence drill generation.

Converts ClaimEvidenceCheckRow results into targeted drill rows
without calling the LLM. Phase 1 implementation.

Skill targets introduced here:
  evidence_alignment  — claim doesn't match what the card says
  claim_precision     — claim overstates or misrepresents the card
  evidence_attribution — no matching card found in library
  card_warranting     — card exists but warrant chain is incomplete
"""

from __future__ import annotations

from typing import TypedDict

from app.models.document import ClaimEvidenceCheckRow


class EvidenceDrillRow(TypedDict):
    title: str
    skill_target: str
    description: str
    prompt: str
    instructions: str
    success_criteria: list[str]
    source_weakness: str
    difficulty: str
    time_limit_seconds: int


# ── Templates by support level ────────────────────────────────────────────────

def _best_snippet(check: ClaimEvidenceCheckRow) -> str | None:
    """Extract the highest-similarity snippet from retrieved_snippets_json."""
    snippets = check.retrieved_snippets_json
    if not snippets:
        return None
    best = max(snippets, key=lambda s: s.get("similarity", 0))
    text = best.get("snippet", "").strip()
    return text[:300] if text else None


def _drill_for_unsupported(check: ClaimEvidenceCheckRow) -> EvidenceDrillRow:
    label = check.argument_label or check.claim_text[:60]
    snippet = _best_snippet(check)
    snippet_line = (
        f"\n\nClosest uploaded evidence (similarity {check.top_similarity:.2f} if applicable):\n"
        f'"{snippet}"\n\n'
        "Restate your claim so it uses language and facts from this snippet — "
        "or explain why the snippet does not support the claim and what card you need."
        if snippet else ""
    )
    return EvidenceDrillRow(
        title=f"Precision Restatement — {label}",
        skill_target="claim_precision",
        description=(
            "Your uploaded card does not support the claim as stated. "
            "This drill trains you to restate the claim so it matches "
            "exactly what your evidence can prove."
        ),
        prompt=(
            f"Look at the argument labeled '{label}'. Your cited evidence "
            "does not support the exact claim you made in the speech. "
            "Re-read your card carefully, then restate the claim in 1–2 sentences "
            "that your card can directly prove. Say what the card ACTUALLY shows — "
            f"not what you wish it showed.{snippet_line}"
        ),
        instructions="\n".join([
            "1. Write down the original claim you made in the speech.",
            "2. Read your uploaded card for this argument word-for-word.",
            "3. Identify the single most specific fact the card proves.",
            "4. Rewrite the claim using only language the card supports.",
            "5. Practice saying the revised claim aloud until it sounds natural.",
        ]),
        success_criteria=[
            "The restated claim uses vocabulary present in the card.",
            "No statistic or causal link is stated that the card doesn't establish.",
            "The claim is specific enough that a flow judge could verify it.",
            "You can say the claim in one sentence without hedging.",
        ],
        source_weakness=(
            f"Unsupported claim — uploaded card does not establish: {check.claim_text[:120]}"
        ),
        difficulty="beginner",
        time_limit_seconds=90,
    )


def _drill_for_partially_supported(check: ClaimEvidenceCheckRow) -> EvidenceDrillRow:
    label = check.argument_label or check.claim_text[:60]
    snippet = _best_snippet(check)
    missing = check.missing_link or ""
    snippet_line = (
        f"\n\nBest matching snippet from your library:\n\"{snippet}\"\n\n"
        + (f"Gap to close: {missing}\n\n" if missing else "")
        + "Practice bridging from this snippet to your claim with a clear warrant."
        if snippet else (f"\n\nGap to close: {missing}" if missing else "")
    )
    return EvidenceDrillRow(
        title=f"Evidence Alignment — {label}",
        skill_target="evidence_alignment",
        description=(
            "Your card is relevant but doesn't fully prove the claim as stated. "
            "This drill teaches you to align your in-round claim language "
            "with what your evidence can actually establish."
        ),
        prompt=(
            f"For the argument '{label}': your card provides partial support "
            "but doesn't prove the full claim. "
            "Read your card, identify the gap between what you said and what it shows, "
            "then practice a 30-second block that closes that gap — either by narrowing "
            f"the claim or by explaining the inferential link from the card to the claim.{snippet_line}"
        ),
        instructions="\n".join([
            "1. State the claim you ran in the speech.",
            "2. Summarize the card in one sentence.",
            "3. Identify what the card proves vs. what you claimed — note the gap.",
            "4. Choose: narrow the claim to fit the card, or add a warrant bridging them.",
            "5. Record or write a 30-second version of this argument with the gap closed.",
        ]),
        success_criteria=[
            "The claim and card are explicitly linked by a stated warrant.",
            "You acknowledge what the card specifically shows without overstating it.",
            "A flow judge could draw the same inference from the card you're making.",
            "The block takes no longer than 35 seconds to deliver aloud.",
        ],
        source_weakness=(
            f"Partially supported claim — card is relevant but gap exists: {check.claim_text[:120]}"
        ),
        difficulty="intermediate",
        time_limit_seconds=120,
    )


def _drill_for_unverifiable(check: ClaimEvidenceCheckRow) -> EvidenceDrillRow:
    label = check.argument_label or check.claim_text[:60]
    missing = check.missing_link or ""
    suggestion_line = f"\n\nWhat would make this verifiable: {missing}" if missing else ""
    return EvidenceDrillRow(
        title=f"Evidence Attribution — {label}",
        skill_target="evidence_attribution",
        description=(
            "No uploaded card matched this claim. "
            "This drill builds the habit of always having an uploaded card "
            "for every claim you run, and citing it with author, year, and warrant."
        ),
        prompt=(
            f"The argument '{label}' had no matching card in your evidence library. "
            "Find or write a card for this claim. Then practice citing it in round: "
            "say the author, year, what the card finds, and the warrant connecting it to your claim. "
            f"Repeat until the attribution is automatic.{suggestion_line}"
        ),
        instructions="\n".join([
            "1. Write the claim you made in the speech.",
            "2. Find a source (article, study, report) that supports this claim.",
            "3. Upload it to your evidence library as a case file.",
            "4. Practice citing it aloud: 'According to [Author], [Year], [finding].'",
            "5. Add a one-sentence warrant connecting the finding to the claim.",
        ]),
        success_criteria=[
            "You can name the author and year of the card without looking.",
            "The citation includes what the source specifically found, not a paraphrase.",
            "You can state the warrant linking the card to the claim in one sentence.",
            "The full citation + warrant takes less than 20 seconds to deliver.",
        ],
        source_weakness=(
            f"No matching card found for claim: {check.claim_text[:120]}"
        ),
        difficulty="beginner",
        time_limit_seconds=90,
    )


# ── Priority ranking ──────────────────────────────────────────────────────────

_RISK_ORDER = {"unsupported": 0, "partially_supported": 1, "unverifiable": 2, "supported": 3}


def _risk_priority(check: ClaimEvidenceCheckRow) -> int:
    return _RISK_ORDER.get(check.support_level or "supported", 99)


# ── Public API ────────────────────────────────────────────────────────────────

def generate_evidence_drills(
    checks: list[ClaimEvidenceCheckRow],
    existing_source_weaknesses: set[str] | None = None,
    max_drills: int = 3,
) -> list[EvidenceDrillRow]:
    """
    Generate up to max_drills evidence-specific drills from evidence check results.

    Only generates drills for unsupported/partially_supported/unverifiable checks.
    Skips supported checks and deduplicates against existing_source_weaknesses.

    Returns a list of drill dicts ready for DB insertion (without speech_id/user_id/order).
    """
    if existing_source_weaknesses is None:
        existing_source_weaknesses = set()

    actionable = [
        c for c in checks
        if (c.support_level or "supported") != "supported"
    ]
    actionable.sort(key=_risk_priority)

    drills: list[EvidenceDrillRow] = []
    for check in actionable:
        if len(drills) >= max_drills:
            break

        level = check.support_level or "unverifiable"
        if level == "unsupported":
            candidate = _drill_for_unsupported(check)
        elif level == "partially_supported":
            candidate = _drill_for_partially_supported(check)
        else:
            candidate = _drill_for_unverifiable(check)

        # Dedup: skip if same source_weakness already exists
        sw = candidate["source_weakness"]
        if sw in existing_source_weaknesses:
            continue

        existing_source_weaknesses.add(sw)
        drills.append(candidate)

    return drills
