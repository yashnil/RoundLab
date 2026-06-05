"""
Public Forum debate rubric profiles.

Each speech type has its own evaluation criteria, dimensions, and calibration.
This makes scoring accurate to what each speech is supposed to accomplish.
"""

from typing import TypedDict


class ScoreAnchor(TypedDict):
    range: str
    label: str
    description: str


class DimensionSpec(TypedDict):
    name: str
    max_score: int
    description: str
    what_to_reward: str
    what_to_penalize: str
    student_friendly_label: str
    score_anchors: list[ScoreAnchor]


class RubricProfile(TypedDict):
    speech_type: str
    purpose: str
    dimensions: list[DimensionSpec]
    do_not_penalize_heavily: list[str]
    calibration_notes: str


CONSTRUCTIVE_RUBRIC: RubricProfile = {
    "speech_type": "constructive",
    "purpose": "Lay the foundation for the team's side of the resolution through a prepared case.",
    "dimensions": [
        {
            "name": "case_structure",
            "max_score": 20,
            "description": "Clear advocacy, organized contentions, logical sequencing, signposting",
            "what_to_reward": "Clear roadmap, organized contentions, logical flow, effective signposting",
            "what_to_penalize": "Disorganized structure, unclear advocacy, poor transitions, confusing order",
            "student_friendly_label": "Case Structure",
            "score_anchors": [
                {"range": "19-20", "label": "Excellent", "description": "Perfect roadmap, clean signposting, professional structure"},
                {"range": "16-18", "label": "Strong", "description": "Clear contentions, good organization, minor flow issues only"},
                {"range": "12-15", "label": "Functional", "description": "Identifiable contentions, some structure, needs better signposting"},
                {"range": "8-11", "label": "Developing", "description": "Basic structure present but confusing, unclear order"},
                {"range": "4-7", "label": "Very Weak", "description": "Minimal structure, hard to follow, no clear roadmap"},
                {"range": "0-3", "label": "Missing/Unusable", "description": "No discernible structure, incoherent organization"},
            ],
        },
        {
            "name": "warranting",
            "max_score": 25,
            "description": "Claims have reasons, causal chains explained, evidence connected to claims",
            "what_to_reward": "Complete claim→warrant→evidence→impact chains, explained causal links",
            "what_to_penalize": "Bare assertions, missing warrants, unexplained jumps in logic, weak internal links",
            "student_friendly_label": "Warranting & Internal Links",
            "score_anchors": [
                {"range": "22-25", "label": "Excellent", "description": "Every claim has clear warrant and evidence, causal chains explained"},
                {"range": "18-21", "label": "Strong", "description": "Most claims warranted, some evidence links could be stronger"},
                {"range": "13-17", "label": "Functional", "description": "Some warrants present, but many assertions lack explanation"},
                {"range": "8-12", "label": "Developing", "description": "Minimal warranting, mostly bare claims, thin causal links"},
                {"range": "4-7", "label": "Very Weak", "description": "Almost no warrants, pure assertion-based"},
                {"range": "0-3", "label": "Missing/Unusable", "description": "No warrants at all, incoherent claims"},
            ],
        },
        {
            "name": "evidence_use",
            "max_score": 20,
            "description": "Sources cited clearly, evidence supports claims, evidence interpreted not name-dropped",
            "what_to_reward": "Clear citations, evidence interpretation, proper source attribution",
            "what_to_penalize": "Vague citations, unsupported claims, fabricated evidence, name-dropping without explanation",
            "student_friendly_label": "Evidence Use",
            "score_anchors": [
                {"range": "19-20", "label": "Excellent", "description": "Every claim backed by clear, well-cited evidence with interpretation"},
                {"range": "16-18", "label": "Strong", "description": "Most claims have evidence, citations clear, good interpretation"},
                {"range": "12-15", "label": "Functional", "description": "Some evidence cited but may be vague or poorly explained"},
                {"range": "8-11", "label": "Developing", "description": "Minimal evidence, mostly name-dropping without explanation"},
                {"range": "4-7", "label": "Very Weak", "description": "Almost no evidence, or fabricated/misattributed sources"},
                {"range": "0-3", "label": "Missing/Unusable", "description": "No evidence cited at all, pure assertion"},
            ],
        },
        {
            "name": "impact_development",
            "max_score": 20,
            "description": "Explains who is harmed/benefited, severity/probability/timeframe, connects to resolution",
            "what_to_reward": "Clear impact story, explains magnitude/probability/timeframe, links to resolution",
            "what_to_penalize": "Vague impacts, no explanation of harm, unclear connection to resolution, missing timeframe",
            "student_friendly_label": "Impact Development",
            "score_anchors": [
                {"range": "19-20", "label": "Excellent", "description": "Clear impact story with magnitude, probability, timeframe, resolution link"},
                {"range": "16-18", "label": "Strong", "description": "Impacts developed with some quantification, clear harm/benefit"},
                {"range": "12-15", "label": "Functional", "description": "Impacts present but vague, missing some timeframe/magnitude detail"},
                {"range": "8-11", "label": "Developing", "description": "Minimal impact development, unclear who is harmed or how"},
                {"range": "4-7", "label": "Very Weak", "description": "Almost no impact explanation, just assertion of harm"},
                {"range": "0-3", "label": "Missing/Unusable", "description": "No impacts developed, no connection to resolution"},
            ],
        },
        {
            "name": "judge_clarity",
            "max_score": 15,
            "description": "Understandable to lay/flow judges, avoids excessive jargon, clear story",
            "what_to_reward": "Accessible language, clear narrative, appropriate for judge type",
            "what_to_penalize": "Excessive jargon, unclear explanation, confusing presentation",
            "student_friendly_label": "Judge Accessibility & Clarity",
            "score_anchors": [
                {"range": "14-15", "label": "Excellent", "description": "Crystal clear, accessible language, perfect judge adaptation"},
                {"range": "12-13", "label": "Strong", "description": "Clear and understandable, appropriate for judge type"},
                {"range": "9-11", "label": "Functional", "description": "Mostly clear with some confusing moments or jargon"},
                {"range": "6-8", "label": "Developing", "description": "Hard to follow, excessive jargon or unclear story"},
                {"range": "3-5", "label": "Very Weak", "description": "Very confusing, poor judge adaptation, unclear narrative"},
                {"range": "0-2", "label": "Missing/Unusable", "description": "Incoherent, unintelligible, impossible for judge to understand"},
            ],
        },
    ],
    "do_not_penalize_heavily": [
        "Lack of clash/refutation",
        "Lack of extensions",
        "Lack of drops coverage",
        "Lack of final voters",
        "Lack of crystallization",
        "No direct opponent engagement",
    ],
    "calibration_notes": (
        "A complete constructive with two contentions, some cited evidence, and understandable "
        "advocacy but weak warrants and limited impact analysis should score 50-60, not 30. "
        "Score 30-39 only if severely underdeveloped, incoherent, missing core components, or impossible to evaluate."
    ),
}

REBUTTAL_RUBRIC: RubricProfile = {
    "speech_type": "rebuttal",
    "purpose": "Answer the opponent's constructive, attack links/warrants/evidence/impacts, preserve your side's offense.",
    "dimensions": [
        {
            "name": "clash_refutation",
            "max_score": 30,
            "description": "Directly responds to opponent claims, attacks key links/warrants, avoids generic responses",
            "what_to_reward": "Specific link/warrant attacks, clear turns/takeouts, strategic targeting",
            "what_to_penalize": "Generic 'they are wrong' responses, missing key offense, shallow refutation",
            "student_friendly_label": "Clash & Direct Refutation",
        },
        {
            "name": "coverage_prioritization",
            "max_score": 20,
            "description": "Covers most important arguments, avoids wasting time on minor claims, strategic choices",
            "what_to_reward": "Strategic argument selection, efficient time use, smart prioritization",
            "what_to_penalize": "Wasting time on minor points, missing key offense, poor time management",
            "student_friendly_label": "Coverage & Prioritization",
        },
        {
            "name": "response_quality",
            "max_score": 20,
            "description": "Clear takeouts/turns, explains why response matters, avoids unsupported assertions",
            "what_to_reward": "Clear turns with explanation, well-supported responses, impact of responses explained",
            "what_to_penalize": "Unsupported assertions, unclear turns, no explanation of why response matters",
            "student_friendly_label": "Response Quality",
        },
        {
            "name": "evidence_comparison",
            "max_score": 15,
            "description": "Compares evidence quality, challenges application, explains not just cites",
            "what_to_reward": "Evidence quality comparison, source credibility analysis, application critique",
            "what_to_penalize": "Card spam without explanation, ignoring opponent evidence, weak evidence comparison",
            "student_friendly_label": "Evidence Comparison",
        },
        {
            "name": "weighing_setup",
            "max_score": 15,
            "description": "Starts comparison where useful, preserves offense for later, gives strategic direction",
            "what_to_reward": "Early weighing framing, offense preservation, strategic ballot direction",
            "what_to_penalize": "No strategic framing, losing all offense, unclear direction for judge",
            "student_friendly_label": "Early Weighing & Strategic Framing",
        },
    ],
    "do_not_penalize_heavily": [
        "Not having full final ballot framing",
        "Not perfectly collapsing the round",
        "Not having complete voters",
    ],
    "calibration_notes": (
        "Rebuttal should be judged on clash quality and coverage. "
        "Missing key opponent offense is a major issue. "
        "Shallow refutation should be penalized more than missing full ballot framing."
    ),
}

SUMMARY_RUBRIC: RubricProfile = {
    "speech_type": "summary",
    "purpose": "Narrow the round, extend key offense, frontline responses, respond to turns, make the judge's decision easier.",
    "dimensions": [
        {
            "name": "extension_quality",
            "max_score": 25,
            "description": "Extends claim, warrant, evidence, impact—not just 'extend our contention'",
            "what_to_reward": "Complete extensions with all components, carries forward what's needed",
            "what_to_penalize": "Bare extensions ('extend X'), missing warrant/evidence/impact in extension, unclear what's being extended",
            "student_friendly_label": "Extension Quality",
        },
        {
            "name": "collapse_strategy",
            "max_score": 20,
            "description": "Focuses on most important arguments, avoids going for everything, shows strategic awareness",
            "what_to_reward": "Clear strategic focus, efficient collapse, smart argument selection",
            "what_to_penalize": "Going for too many arguments, unclear strategy, kitchen sink approach",
            "student_friendly_label": "Collapse Strategy",
        },
        {
            "name": "frontlining",
            "max_score": 20,
            "description": "Answers key responses against your offense, handles important turns, doesn't leave attacks unanswered",
            "what_to_reward": "Answering key turns, addressing important responses, protecting offense",
            "what_to_penalize": "Ignoring major turns, leaving offense undefended, missing key responses",
            "student_friendly_label": "Frontlining & Responses",
        },
        {
            "name": "weighing",
            "max_score": 25,
            "description": "Compares magnitude/probability/timeframe/reversibility/scope, explains why your offense matters more",
            "what_to_reward": "Explicit comparative weighing, multiple weighing mechanisms, clear explanation",
            "what_to_penalize": "No weighing, generic 'we outweigh', missing comparison, unclear impact analysis",
            "student_friendly_label": "Weighing",
        },
        {
            "name": "judge_clarity",
            "max_score": 10,
            "description": "Clear roadmap, understandable ballot direction, avoids excessive spread/confusion",
            "what_to_reward": "Clear organization, easy-to-follow structure, judge-friendly presentation",
            "what_to_penalize": "Confusing organization, unclear ballot direction, too fast/spread",
            "student_friendly_label": "Judge Clarity",
        },
    ],
    "do_not_penalize_heavily": [
        "Not having full final focus crystallization",
        "Not having perfect voters yet",
    ],
    "calibration_notes": (
        "Summary should collapse and weigh. "
        "Missing extensions or weighing is a major issue. "
        "New arguments should be penalized."
    ),
}

FINAL_FOCUS_RUBRIC: RubricProfile = {
    "speech_type": "final_focus",
    "purpose": "Crystallize the round and tell the judge exactly why your side wins.",
    "dimensions": [
        {
            "name": "ballot_story",
            "max_score": 30,
            "description": "Gives 1-2 clear reasons to vote, writes the ballot for the judge, explains what to prioritize",
            "what_to_reward": "Clear voters, ballot framing, focused winning narrative",
            "what_to_penalize": "No voters, trying to go for everything, unclear ballot story",
            "student_friendly_label": "Ballot Story & Voters",
        },
        {
            "name": "comparative_weighing",
            "max_score": 25,
            "description": "Makes explicit comparisons, uses magnitude/probability/timeframe/scope/reversibility",
            "what_to_reward": "Explicit comparative weighing, multiple mechanisms, clear superiority explanation",
            "what_to_penalize": "No weighing, generic assertions, missing comparison",
            "student_friendly_label": "Comparative Weighing",
        },
        {
            "name": "crystallization",
            "max_score": 20,
            "description": "Narrows the round efficiently, resolves key clash points, doesn't rehash everything",
            "what_to_reward": "Efficient narrowing, resolves clash, focuses on decisive issues",
            "what_to_penalize": "Rehashing everything, not crystallizing, missing key clash resolution",
            "student_friendly_label": "Crystallization",
        },
        {
            "name": "consistency",
            "max_score": 15,
            "description": "No new arguments, follows summary path, keeps ballot story coherent",
            "what_to_reward": "Consistency with summary, no new arguments, coherent narrative",
            "what_to_penalize": "New arguments, contradicting summary, incoherent ballot story",
            "student_friendly_label": "Consistency with Summary",
        },
        {
            "name": "judge_adaptation",
            "max_score": 10,
            "description": "Clear for lay judge, precise for flow judge, persuasive closing narrative",
            "what_to_reward": "Appropriate judge adaptation, persuasive delivery, clear closing",
            "what_to_penalize": "Inappropriate for judge type, unclear closing, weak persuasion",
            "student_friendly_label": "Judge Adaptation & Clarity",
        },
    ],
    "do_not_penalize_heavily": [],
    "calibration_notes": (
        "Final focus should crystallize and weigh. "
        "No voters or new arguments are major issues. "
        "Going for too many issues should be penalized."
    ),
}

CROSSFIRE_RUBRIC: RubricProfile = {
    "speech_type": "crossfire",
    "purpose": "Ask strategic questions, avoid concessions, set up later arguments.",
    "dimensions": [
        {
            "name": "question_quality",
            "max_score": 30,
            "description": "Strategic questions that set up offense or expose opponent weaknesses",
            "what_to_reward": "Strategic setup questions, questions exposing weaknesses, clear follow-ups",
            "what_to_penalize": "Pointless questions, missing strategic opportunities, unclear questions",
            "student_friendly_label": "Question Quality",
        },
        {
            "name": "defense",
            "max_score": 30,
            "description": "Avoids damaging concessions, defends positions effectively",
            "what_to_reward": "Smart non-concessions, effective defense, protecting key positions",
            "what_to_penalize": "Damaging concessions, weak defense, giving up key ground",
            "student_friendly_label": "Defense & Non-Concessions",
        },
        {
            "name": "strategic_setup",
            "max_score": 25,
            "description": "Uses crossfire to set up later speech arguments",
            "what_to_reward": "Clear setup for later speeches, strategic framing",
            "what_to_penalize": "Missing setup opportunities, no strategic use of crossfire",
            "student_friendly_label": "Strategic Setup",
        },
        {
            "name": "clarity",
            "max_score": 15,
            "description": "Clear exchanges, understandable to judge, appropriate tone",
            "what_to_reward": "Clear communication, appropriate tone, judge-friendly",
            "what_to_penalize": "Confusing exchanges, inappropriate tone, hard to follow",
            "student_friendly_label": "Clarity & Professionalism",
        },
    ],
    "do_not_penalize_heavily": [
        "Not winning every exchange",
        "Not setting up every possible argument",
    ],
    "calibration_notes": (
        "Crossfire is about strategic setup and defense. "
        "Critical concessions should be heavily penalized."
    ),
}

# Map speech types to rubrics
RUBRIC_MAP: dict[str, RubricProfile] = {
    "constructive": CONSTRUCTIVE_RUBRIC,
    "rebuttal": REBUTTAL_RUBRIC,
    "summary": SUMMARY_RUBRIC,
    "final_focus": FINAL_FOCUS_RUBRIC,
    "crossfire": CROSSFIRE_RUBRIC,
}


def get_rubric(speech_type: str) -> RubricProfile:
    """Get the appropriate rubric for a speech type."""
    return RUBRIC_MAP.get(speech_type, CONSTRUCTIVE_RUBRIC)


# Score band definitions
SCORE_BANDS = {
    "tournament_ready": {"min": 90, "max": 100, "label": "Tournament-Ready"},
    "strong": {"min": 80, "max": 89, "label": "Strong"},
    "solid": {"min": 70, "max": 79, "label": "Solid"},
    "developing": {"min": 60, "max": 69, "label": "Developing with Clear Strengths"},
    "flawed": {"min": 50, "max": 59, "label": "Flawed but Complete"},
    "major_issues": {"min": 40, "max": 49, "label": "Major Issues but Partially Functional"},
    "underdeveloped": {"min": 30, "max": 39, "label": "Severely Underdeveloped"},
    "incomplete": {"min": 0, "max": 29, "label": "Incomplete or Incoherent"},
}


def get_score_band(score: int) -> str:
    """Get the score band label for a given score."""
    for band in SCORE_BANDS.values():
        if band["min"] <= score <= band["max"]:
            return band["label"]
    return "Incomplete or Incoherent"


def calibrate_scores(
    raw_scores: dict[str, int],
    speech_type: str,
    transcript_text: str,
    argument_map: list[dict],
) -> tuple[dict[str, int], list[str]]:
    """Calibrate scores to prevent impossible values and apply speech-type constraints.

    Returns (calibrated_scores, warnings) where warnings contains human-readable
    explanations of any adjustments made.
    """
    calibrated = {}
    warnings = []

    # Get rubric for validation
    rubric = get_rubric(speech_type)

    # Build dimension name to max_score mapping
    dim_max = {dim["name"]: dim["max_score"] for dim in rubric["dimensions"]}

    # Basic stats about the speech
    word_count = len(transcript_text.split())
    has_substantial_content = word_count >= 100
    has_multiple_claims = len(argument_map) >= 2

    # Clamp each dimension to its valid range
    for dim_name, max_score in dim_max.items():
        raw_val = raw_scores.get(dim_name, 0)
        clamped = max(0, min(raw_val, max_score))

        # Apply speech-type-specific constraints
        if speech_type == "constructive":
            # Constructive-specific rules
            if dim_name == "judge_clarity":
                # Clarity should not be 0-2 if the transcript is readable and has multiple claims
                if clamped <= 2 and has_substantial_content and has_multiple_claims:
                    old_val = clamped
                    clamped = max(6, clamped)
                    warnings.append(
                        f"Adjusted {dim_name} from {old_val} to {clamped}: "
                        f"Transcript is {word_count} words with {len(argument_map)} claims, "
                        "so it cannot be unintelligible."
                    )

        if clamped != raw_val:
            if not any(w.startswith(f"Adjusted {dim_name}") for w in warnings):
                warnings.append(f"Clamped {dim_name} from {raw_val} to {clamped} (max: {max_score})")

        calibrated[dim_name] = clamped

    # Detect dimensions that don't belong to this speech type
    for score_key in raw_scores.keys():
        if score_key not in dim_max:
            warnings.append(
                f"Removed {score_key}: not a valid dimension for {speech_type} speeches"
            )

    return calibrated, warnings
