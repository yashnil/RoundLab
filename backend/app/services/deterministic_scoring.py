"""
Deterministic scoring engine for PF debate speeches.

LLM explains; rubric engine scores.

This module computes numeric scores from transcript/argument analysis
using stable heuristics, not direct LLM output. This prevents score-shopping
via repeated regeneration.
"""

import hashlib
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Scoring version - increment when scoring logic changes materially
# v3 = Recalibrated scoring (2026-06-04): lower baselines, stricter thresholds, score caps
SCORING_VERSION = "pf_rubric_v3_recalibrated_2026_06_04"


def compute_report_fingerprint(
    transcript_text: str,
    speech_type: str,
    argument_map: list[dict],
) -> str:
    """
    Compute deterministic fingerprint for feedback report inputs.

    Same inputs → same fingerprint → skip regeneration.
    """
    # Normalize transcript (lowercase, strip extra whitespace)
    normalized_text = " ".join(transcript_text.lower().split())

    # Create summary of argument_map (claims and warrants, ignoring IDs)
    arg_summary = []
    for arg in argument_map:
        arg_summary.append(f"{arg.get('claim', '')}|{arg.get('warrant', '')}")
    arg_string = "||".join(sorted(arg_summary))

    # Combine inputs
    fingerprint_input = f"{normalized_text}||{speech_type}||{SCORING_VERSION}||{arg_string}"

    # Hash
    return hashlib.sha256(fingerprint_input.encode()).hexdigest()


def calculate_constructive_scores(
    transcript_text: str,
    argument_map: list[dict],
    word_count: int,
) -> dict[str, int]:
    """
    Calculate deterministic scores for Constructive speeches.

    Returns dict with keys: case_structure, warranting, evidence_use, impact_development, judge_clarity

    Calibration philosophy:
    - 90-100: tournament-ready, strategic, very polished
    - 80-89: strong, mostly complete, clear warrants/evidence/impacts, minor issues only
    - 70-79: solid, understandable and competitive, but some underdeveloped analysis
    - 60-69: developing, complete case but notable weaknesses
    - 50-59: flawed but complete, major reasoning or impact gaps
    - 40-49: needs foundation, basic case exists but thinly supported
    - below 40: incomplete/not scorable
    """
    scores = {}
    transcript_lower = transcript_text.lower()

    # Case Structure (0-20): Organization, signposting, clear advocacy
    case_structure_score = 5  # Lower baseline: needs to earn points
    num_arguments = len(argument_map)

    if num_arguments >= 2:
        case_structure_score += 3  # Has multiple contentions (reduced from +4)
    if num_arguments >= 3:
        case_structure_score += 2  # Well-structured case

    # Check for structural keywords (stricter threshold)
    structure_keywords = ["first", "second", "third", "contention", "next", "thus", "therefore"]
    structure_count = sum(1 for kw in structure_keywords if kw in transcript_lower)
    if structure_count >= 5:  # Raised threshold from 3
        case_structure_score += 3
    elif structure_count >= 3:
        case_structure_score += 1  # Reduced from +2

    # Stricter length requirements
    if word_count < 100:
        case_structure_score -= 4  # Increased penalty from -3
    if word_count < 50:
        case_structure_score -= 3  # Additional penalty for very short
    if num_arguments < 1:
        case_structure_score -= 5
    if num_arguments < 2:  # Single argument case is weaker
        case_structure_score -= 2

    scores["case_structure"] = max(0, min(20, case_structure_score))

    # Warranting (0-25): Claim→warrant→evidence→impact chains
    warranting_score = 6  # Lower baseline: warrants must be earned

    # Check how many arguments have warrants (stricter evaluation)
    arguments_with_warrants = sum(
        1 for arg in argument_map
        if arg.get("warrant") and len(arg.get("warrant", "").strip()) > 15  # Raised from 10
    )
    warrant_ratio = arguments_with_warrants / max(1, num_arguments)

    # Stricter thresholds for warrant bonuses
    if warrant_ratio >= 0.9:  # Nearly all arguments warranted (raised from 0.8)
        warranting_score += 10  # Strong warranting
    elif warrant_ratio >= 0.7:  # Most arguments warranted (raised from 0.6)
        warranting_score += 6  # Good warranting (reduced from +8)
    elif warrant_ratio >= 0.5:  # Half warranted (raised from 0.4)
        warranting_score += 3  # Developing warranting
    else:
        warranting_score -= 3  # Weak warranting (increased penalty from -2)

    # Check for causal language (stricter thresholds)
    causal_keywords = ["because", "since", "leads to", "causes", "results in", "due to", "therefore", "thus"]
    causal_count = sum(1 for kw in causal_keywords if kw in transcript_lower)
    if causal_count >= 5:  # Raised from 3
        warranting_score += 4
    elif causal_count >= 3:  # Raised from 1
        warranting_score += 2
    elif causal_count >= 1:
        warranting_score += 1  # Reduced from +2

    # Stronger penalties for argument issues
    arguments_with_issues = sum(
        1 for arg in argument_map
        if "missing warrant" in str(arg.get("issues", [])).lower()
        or "thin warrant" in str(arg.get("issues", [])).lower()
        or "insufficient warrant" in str(arg.get("issues", [])).lower()
    )
    if arguments_with_issues > 0:
        warranting_score -= arguments_with_issues * 3  # Increased from *2

    # Check for weak warrant indicators in issues
    if num_arguments > 0 and warrant_ratio < 0.3:  # Less than 30% warranted
        warranting_score -= 4  # Additional penalty for very weak warranting

    scores["warranting"] = max(0, min(25, warranting_score))

    # Evidence Use (0-20): Citations, source quality
    evidence_score = 5  # Lower baseline: evidence must be earned

    # Check how many arguments have evidence (stricter evaluation)
    arguments_with_evidence = sum(
        1 for arg in argument_map
        if arg.get("evidence") and len(arg.get("evidence", "").strip()) > 8  # Raised from 5
    )
    evidence_ratio = arguments_with_evidence / max(1, num_arguments)

    # Stricter thresholds for evidence bonuses
    if evidence_ratio >= 0.8:  # Raised from 0.75
        evidence_score += 7  # Increased from +6
    elif evidence_ratio >= 0.6:  # Raised from 0.5
        evidence_score += 4  # Same
    elif evidence_ratio >= 0.4:  # Raised from 0.25
        evidence_score += 2  # Same
    elif evidence_ratio < 0.3:  # Penalty for very little evidence
        evidence_score -= 2

    # Check for citation keywords (stricter thresholds)
    citation_keywords = ["study", "research", "data", "according to", "evidence", "shows", "finds", "statistics"]
    citation_count = sum(1 for kw in citation_keywords if kw in transcript_lower)
    if citation_count >= 4:  # Raised from 3
        evidence_score += 4
    elif citation_count >= 2:  # Raised from 1
        evidence_score += 2
    elif citation_count >= 1:
        evidence_score += 1  # Reduced from +2

    # Stronger penalties for vague citations
    vague_citations = sum(1 for phrase in ["experts say", "studies show", "people say", "some say"] if phrase in transcript_lower)
    if vague_citations > 0:
        evidence_score -= vague_citations * 2  # Increased from -1

    scores["evidence_use"] = max(0, min(20, evidence_score))

    # Impact Development (0-20): Magnitude, probability, timeframe
    impact_score = 5  # Lower baseline: impacts must be earned

    # Check for impact language (stricter evaluation)
    impact_keywords = ["impact", "harm", "benefit", "lives", "death", "deaths", "economic", "environment", "suffering", "crisis"]
    impact_count = sum(1 for kw in impact_keywords if kw in transcript_lower)
    if impact_count >= 6:  # Raised from 4
        impact_score += 5
    elif impact_count >= 3:  # Raised from 2
        impact_score += 3
    elif impact_count >= 1:
        impact_score += 1
    else:
        impact_score -= 2  # Penalty for no impact language

    # Check for quantification (stricter - "many" and "significant" are vague)
    quant_keywords = ["million", "billion", "percent", "trillion", "thousand"]
    quant_count = sum(1 for kw in quant_keywords if kw in transcript_lower)
    if quant_count >= 3:  # Raised from 2
        impact_score += 3
    elif quant_count >= 1:
        impact_score += 1

    # Penalize vague quantification
    if "many" in transcript_lower or "significant" in transcript_lower:
        impact_score -= 1  # These are weak quantifiers

    # Check arguments have impacts (stricter evaluation)
    arguments_with_impacts = sum(
        1 for arg in argument_map
        if arg.get("impact") and len(arg.get("impact", "").strip()) > 15  # Raised from 10
    )
    impact_ratio = arguments_with_impacts / max(1, num_arguments)

    if impact_ratio >= 0.9:  # Nearly all arguments
        impact_score += 5  # Increased from +4
    elif impact_ratio >= 0.6:  # Most arguments
        impact_score += 3
    elif impact_ratio >= 0.3:  # Some arguments
        impact_score += 1  # Reduced from +2
    else:  # Few or no impacts
        impact_score -= 3  # Penalty for weak impact development

    scores["impact_development"] = max(0, min(20, impact_score))

    # Judge Clarity (0-15): Understandable, accessible language
    clarity_score = 5  # Lower baseline: clarity must be earned

    # Stricter length penalties
    if word_count < 50:
        clarity_score -= 5  # Reduced from -6 but still strong penalty
    elif word_count < 100:
        clarity_score -= 3

    # Reward optimal length (not just any length)
    if 300 <= word_count <= 600:  # Narrower optimal range
        clarity_score += 4  # Increased from +3
    elif 200 <= word_count <= 800:  # Acceptable range
        clarity_score += 2  # Reduced from +3
    elif 150 <= word_count < 200:  # Short but acceptable
        clarity_score += 1
    elif word_count > 900:  # Too verbose
        clarity_score -= 1

    # Check for excessive jargon/complexity (stricter evaluation)
    avg_sentence_length = word_count / max(1, transcript_text.count(". ") + transcript_text.count("? ") + 1)
    if avg_sentence_length < 12:  # Very concise
        clarity_score += 3  # Increased from +2
    elif avg_sentence_length < 18:  # Concise
        clarity_score += 1  # Reduced from +2
    elif avg_sentence_length > 35:  # Very complex
        clarity_score -= 3  # Increased from -2
    elif avg_sentence_length > 25:  # Somewhat complex
        clarity_score -= 1

    # Stronger penalties for unclear structure
    if num_arguments == 0:
        clarity_score -= 5  # Increased from -4
    elif num_arguments == 1:
        clarity_score -= 2  # Single argument is less clear

    scores["judge_clarity"] = max(0, min(15, clarity_score))

    # Apply calibration caps to prevent inflated scores
    original_total = sum(scores.values())
    scores = _apply_constructive_score_caps(scores)
    capped_total = sum(scores.values())

    logger.info(
        "deterministic_scoring: constructive | word_count=%d num_args=%d | case_structure=%d warranting=%d evidence=%d impact=%d clarity=%d | total=%d (capped_from=%d)",
        word_count,
        num_arguments,
        scores["case_structure"],
        scores["warranting"],
        scores["evidence_use"],
        scores["impact_development"],
        scores["judge_clarity"],
        capped_total,
        original_total if original_total != capped_total else capped_total,
    )

    return scores


def _apply_constructive_score_caps(scores: dict[str, int]) -> dict[str, int]:
    """
    Apply calibration caps to constructive scores to prevent inflation.

    Rules:
    - If Warranting <= 10 AND Impact Development <= 10, cap overall at 65
    - If 3+ dimensions are <= 12, cap overall at 70
    - If Case Structure, Warranting, AND Impact Development are all < 14, cap at 72
    - Only allow 80+ if every dimension is >= 14 AND at least two dimensions are >= 16
    """
    case_structure = scores["case_structure"]
    warranting = scores["warranting"]
    evidence_use = scores["evidence_use"]
    impact_development = scores["impact_development"]
    judge_clarity = scores["judge_clarity"]

    total = sum(scores.values())
    dimensions_below_12 = sum(1 for score in scores.values() if score <= 12)
    dimensions_below_14 = sum(1 for score in scores.values() if score < 14)
    dimensions_16_plus = sum(1 for score in scores.values() if score >= 16)

    # Apply caps from strictest to most lenient
    cap = 100  # No cap by default

    # Very weak warranting AND impact → cap at 65
    if warranting <= 10 and impact_development <= 10:
        cap = min(cap, 65)
        logger.info("deterministic_scoring: applying cap=65 (weak warranting AND impact)")

    # Three or more dimensions weak → cap at 70
    if dimensions_below_12 >= 3:
        cap = min(cap, 70)
        logger.info("deterministic_scoring: applying cap=70 (3+ dimensions below 12)")

    # Core dimensions (case, warranting, impact) all weak → cap at 72
    if case_structure < 14 and warranting < 14 and impact_development < 14:
        cap = min(cap, 72)
        logger.info("deterministic_scoring: applying cap=72 (core dimensions weak)")

    # Prevent "Strong" (80+) unless dimensions support it
    if total >= 80:
        if dimensions_below_14 > 0:  # Any dimension below 14
            cap = min(cap, 79)
            logger.info("deterministic_scoring: preventing 80+ (dimension below 14)")
        elif dimensions_16_plus < 2:  # Need at least 2 dimensions at 16+
            cap = min(cap, 79)
            logger.info("deterministic_scoring: preventing 80+ (fewer than 2 dimensions at 16+)")

    # Apply cap if needed
    if total > cap:
        # Proportionally reduce all dimensions to meet cap
        scale_factor = cap / total
        capped_scores = {
            dim: max(0, int(score * scale_factor))
            for dim, score in scores.items()
        }
        # Ensure sum equals cap (handle rounding)
        diff = cap - sum(capped_scores.values())
        if diff > 0:
            # Add remaining points to highest dimension
            max_dim = max(capped_scores.keys(), key=lambda k: capped_scores[k])
            capped_scores[max_dim] += diff
        logger.info("deterministic_scoring: capped %d → %d (scale=%.2f)", total, cap, scale_factor)
        return capped_scores

    return scores


def calculate_rubric_scores(
    speech_type: str,
    transcript_text: str,
    argument_map: list[dict],
    word_count: int,
) -> dict[str, int]:
    """
    Calculate deterministic rubric scores for any speech type.

    Returns dict mapping rubric dimension names to scores (0-max for that dimension).
    """
    if speech_type == "constructive":
        return calculate_constructive_scores(transcript_text, argument_map, word_count)

    # For other speech types, use simpler baseline for now
    # TODO: Add rebuttal, summary, final_focus deterministic scoring
    logger.warning(
        "deterministic_scoring: %s not fully implemented, using baseline scores",
        speech_type,
    )

    # Return reasonable baseline scores based on speech type
    # These will be mapped to legacy 5-dimension schema by _map_rubric_to_legacy_scores
    num_arguments = len(argument_map)
    baseline_score = 12  # Middle-range score per dimension

    if speech_type == "rebuttal":
        return {
            "clash_refutation": baseline_score,
            "weighing_setup": baseline_score,
            "response_quality": baseline_score,
            "coverage_prioritization": baseline_score,
            "evidence_comparison": baseline_score,
        }
    elif speech_type == "summary":
        return {
            "frontlining": baseline_score,
            "weighing": baseline_score,
            "extension_quality": baseline_score,
            "collapse_strategy": baseline_score,
            "judge_clarity": baseline_score,
        }
    elif speech_type == "final_focus":
        return {
            "crystallization": baseline_score,
            "comparative_weighing": baseline_score,
            "ballot_story": baseline_score,
            "consistency": baseline_score,
            "judge_adaptation": baseline_score,
        }
    else:
        # Unknown speech type - return zeros
        logger.error("deterministic_scoring: unknown speech_type=%s", speech_type)
        return {
            "unknown_dimension": 0,
        }
