"""
Deterministic block-coverage classifier.

For each argument in a speech:
  1. Build a query from the claim + warrant text.
  2. Search user's block_entries via match_block_entries RPC.
  3. Classify as covered / partially_covered / missing / no_available_block
     based on similarity score and existing argument quality signals.

No LLM is used here — classification is fully deterministic.
"""

from __future__ import annotations
from typing import Any, Optional

from app.models.blockfile import BlockCoverageResult, BlockSearchResult
from app.services.embeddings import embed_text

# Similarity thresholds
_COVERED_THRESHOLD      = 0.60
_PARTIAL_THRESHOLD      = 0.35
_HAS_MATCH_THRESHOLD    = 0.20  # anything below: no_available_block

# These speech types face opponent arguments, so we check block coverage
_OPPOSING_SPEECH_TYPES = frozenset({"rebuttal", "summary", "final_focus"})
# These speech types should have frontlines prepared
_CONSTRUCTIVE_TYPES    = frozenset({"constructive"})


def _build_query(claim: str, warrant: str, evidence: Optional[str]) -> str:
    parts = [claim, warrant or "", evidence or ""]
    return " ".join(p.strip() for p in parts if p.strip())[:2000]


def _classify(
    top_similarity: float,
    issues: list[str],
    evidence_present: bool,
) -> tuple[str, str, Optional[str]]:
    """
    Returns (status, rationale, missing_piece).
    """
    if top_similarity < _HAS_MATCH_THRESHOLD:
        return (
            "no_available_block",
            "No uploaded block or frontline entry matched this claim.",
            "Upload a blockfile that addresses this opponent argument.",
        )

    if top_similarity >= _COVERED_THRESHOLD:
        if not issues:
            return (
                "covered",
                f"Matching block found (similarity {top_similarity:.2f}) and argument quality is strong.",
                None,
            )
        missing = _derive_missing_from_issues(issues)
        return (
            "partially_covered",
            f"Matching block found (similarity {top_similarity:.2f}) but argument has known gaps: {', '.join(issues[:2])}.",
            missing,
        )

    if top_similarity >= _PARTIAL_THRESHOLD:
        missing = _derive_missing_from_issues(issues)
        if not missing and not issues:
            missing = "Warrant or evidence may not match the available block response."
        return (
            "partially_covered",
            f"Partial block match (similarity {top_similarity:.2f}). Response may not fully apply the uploaded block.",
            missing,
        )

    # Between HAS_MATCH and PARTIAL
    return (
        "missing",
        f"Block entry found but similarity is low ({top_similarity:.2f}) — speech likely did not use it.",
        "Use the matched block: include the core response, warrant, and impact comparison.",
    )


def _derive_missing_from_issues(issues: list[str]) -> Optional[str]:
    if not issues:
        return None
    for issue in issues:
        il = issue.lower()
        if "warrant" in il:
            return "Add the core warrant explaining why the opponent's argument fails."
        if "evidence" in il:
            return "Include a cited piece of evidence supporting the response."
        if "impact" in il:
            return "Explain the comparative impact of your response."
        if "weigh" in il:
            return "Weigh your response against the opponent's impact."
    return issues[0][:200]


def _make_drill(
    claim_text: str,
    entry: BlockSearchResult,
    status: str,
    argument_label: Optional[str],
) -> Optional[dict[str, Any]]:
    if status == "no_available_block":
        return None
    tag = entry.tag or entry.opponent_claim or claim_text[:80]
    if status == "missing":
        prompt = (
            f"Use your uploaded block '{tag}' to answer the claim: \"{claim_text[:200]}\". "
            f"You must include the core response, warrant, and impact comparison. Time limit: 45 seconds."
        )
        skill = "block_application"
        title = f"Block application: {tag[:60]}"
    else:
        prompt = (
            f"Strengthen your response to '{tag}'. Your current response is missing key elements "
            f"from the uploaded block. Include: the warrant, evidence citation, and weighing. 45 seconds."
        )
        skill = "response_warranting"
        title = f"Strengthen response: {tag[:60]}"
    return {
        "title": title,
        "skill_target": skill,
        "prompt": prompt,
        "description": f"Practice drill from block coverage analysis ({argument_label or claim_text[:60]})",
        "difficulty": "beginner",
        "time_limit_seconds": 90,
        "instructions": "1. Read your uploaded block entry first.\n"
                        "2. Give your response in 45 seconds without reading directly.\n"
                        "3. Include: core response, warrant, and impact comparison.",
        "success_criteria": [
            "States the core counter-argument clearly",
            "Explains the warrant (mechanism behind the response)",
            "Compares impacts or explains why opponent's impact doesn't flow",
            "Does not make claims beyond what the uploaded block supports",
        ],
    }


def classify_block_coverage(
    arguments: list[dict[str, Any]],
    speech_type: str,
    user_id: str,
    speech_id: str,
    supabase_client: Any,
    user_has_blocks: bool,
) -> list[BlockCoverageResult]:
    """
    Main entry point. Returns one BlockCoverageResult per relevant argument.

    Args:
        arguments: List of argument dicts (claim, warrant, evidence, impact, issues, label, id).
        speech_type: e.g. "rebuttal", "constructive".
        user_id: Owner's user_id.
        speech_id: Parent speech id.
        supabase_client: Initialized Supabase client.
        user_has_blocks: Whether user has any block_entries.
    """
    if not user_has_blocks:
        # No blocks uploaded — everything is no_available_block
        return [
            BlockCoverageResult(
                argument_id=arg.get("id"),
                claim_text=arg.get("claim", "")[:500],
                check_type="block" if speech_type in _OPPOSING_SPEECH_TYPES else "frontline",
                status="no_available_block",
                matched_entries=[],
                top_similarity=None,
                rationale="No block entries uploaded.",
                missing_piece="Upload a blockfile to your Evidence Library.",
            )
            for arg in arguments
            if arg.get("claim", "").strip()
        ]

    check_type = "block" if speech_type in _OPPOSING_SPEECH_TYPES else "frontline"
    results: list[BlockCoverageResult] = []

    for arg in arguments:
        claim   = arg.get("claim", "").strip()
        warrant = arg.get("warrant", "") or ""
        evidence = arg.get("evidence") or ""
        issues  = arg.get("issues") or []
        label   = arg.get("label") or ""
        arg_id  = arg.get("id")

        if not claim:
            continue

        query_text = _build_query(claim, warrant, evidence)

        try:
            query_embedding = embed_text(query_text)
        except Exception:
            results.append(BlockCoverageResult(
                argument_id=arg_id,
                claim_text=claim[:500],
                check_type=check_type,
                status="no_available_block",
                matched_entries=[],
                top_similarity=None,
                rationale="Embedding failed; cannot check coverage.",
                missing_piece=None,
            ))
            continue

        try:
            # Convert embedding list to pg string format
            pg_vec = "[" + ",".join(str(f) for f in query_embedding) + "]"
            rpc_result = supabase_client.rpc(
                "match_block_entries",
                {
                    "query_embedding": pg_vec,
                    "match_user_id": user_id,
                    "match_count": 5,
                    "similarity_threshold": _HAS_MATCH_THRESHOLD,
                },
            ).execute()
            raw_matches: list[dict[str, Any]] = rpc_result.data or []
        except Exception:
            raw_matches = []

        if not raw_matches:
            top_similarity = 0.0
        else:
            top_similarity = float(raw_matches[0].get("similarity") or 0.0)

        status, rationale, missing_piece = _classify(top_similarity, issues, bool(evidence))

        matched_entries: list[BlockSearchResult] = []
        best_entry: Optional[BlockSearchResult] = None
        for row in raw_matches[:3]:
            entry = BlockSearchResult(
                id=row["id"],
                document_id=row.get("document_id"),
                entry_type=row.get("entry_type", "unknown"),
                side=row.get("side"),
                tag=row.get("tag"),
                opponent_claim=row.get("opponent_claim"),
                response_text=row.get("response_text", ""),
                warrant_text=row.get("warrant_text"),
                evidence_text=row.get("evidence_text"),
                impact_text=row.get("impact_text"),
                weighing_text=row.get("weighing_text"),
                source=row.get("source"),
                author=row.get("author"),
                date=row.get("date"),
                similarity=row.get("similarity"),
            )
            matched_entries.append(entry)
            if best_entry is None:
                best_entry = entry

        suggested_drill = None
        if best_entry and status in ("missing", "partially_covered"):
            suggested_drill = _make_drill(claim, best_entry, status, label)

        results.append(BlockCoverageResult(
            argument_id=arg_id,
            claim_text=claim[:500],
            check_type=check_type,
            status=status,
            matched_entries=matched_entries,
            top_similarity=top_similarity if top_similarity > 0 else None,
            rationale=rationale,
            missing_piece=missing_piece,
            suggested_drill_json=suggested_drill,
        ))

    return results
