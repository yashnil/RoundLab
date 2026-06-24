"""Pass 16 — Speech-stage legality checker.

Deterministic checks for PF speech-stage rules.
Returns precise violations, not generic feedback.
"""

from __future__ import annotations

import re
from typing import List, Optional

from app.models.round_simulation import (
    ArgumentFlowStatus,
    RoundArgument,
    RoundPhaseType,
    RoundSide,
    SpeechLegalityViolation,
    SpeechLegalityViolationType,
)

_WEIGHING_CUES = [
    r'\b(?:magnitude|probability|timeframe|reversibility)\b',
    r'\b(?:outweighs?|comparatively|even if they win|prioritize)\b',
    r'\b(?:more important|bigger impact|faster timeframe|more likely)\b',
]

_NEW_ARG_CUES = [
    r'\bfirst(?:ly)?\s+(?:I want to|we|let me)\s+(?:argue|contend|submit|say|note)\b',
    r'\bnew\s+(?:argument|contention|reason)\b',
    r'\bintroduce\b',
    r'\ban?\s+additional\s+reason\b',
]

_EXTENSION_CUES = [
    r'\bextend\b',
    r'\bstands?\s+uncontested\b',
    r'\bgoes?\s+unanswered\b',
    r'\bacross\s+the\s+(?:flow|board)\b',
]


def _mentions_weighing(text: str) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in _WEIGHING_CUES)


def _appears_to_add_new_argument(text: str) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in _NEW_ARG_CUES)


def _mentions_extension(text: str) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in _EXTENSION_CUES)


def _find_opponent_arguments(
    live_args: List[RoundArgument],
    speaker_side: RoundSide,
) -> List[RoundArgument]:
    opp = RoundSide.CON if speaker_side == RoundSide.PRO else RoundSide.PRO
    return [a for a in live_args if a.side == opp]


def _find_own_arguments(
    live_args: List[RoundArgument],
    speaker_side: RoundSide,
) -> List[RoundArgument]:
    return [a for a in live_args if a.side == speaker_side]


def check_constructive(
    transcript: str,
    speaker_side: RoundSide,
    live_args: List[RoundArgument],
) -> List[SpeechLegalityViolation]:
    """Constructive: must introduce offense and evidence foundations."""
    violations: List[SpeechLegalityViolation] = []
    # Must contain some claim content
    if len(transcript.split()) < 30:
        violations.append(SpeechLegalityViolation(
            type=SpeechLegalityViolationType.DROPPED_OFFENSE,
            description="Constructive is too short — no substantive arguments presented.",
            severity="error",
        ))
    return violations


def check_rebuttal(
    transcript: str,
    speaker_side: RoundSide,
    live_args: List[RoundArgument],
) -> List[SpeechLegalityViolation]:
    """Rebuttal: must have direct clash, response coverage."""
    violations: List[SpeechLegalityViolation] = []
    opponent_args = _find_opponent_arguments(live_args, speaker_side)
    live_opponent = [
        a for a in opponent_args
        if a.status in (ArgumentFlowStatus.INTRODUCED, ArgumentFlowStatus.EXTENDED, ArgumentFlowStatus.LIVE)
    ]
    if live_opponent:
        # Check if any opponent argument is mentioned
        answered = [
            a for a in live_opponent
            if re.search(re.escape(a.label), transcript, re.IGNORECASE)
        ]
        if not answered:
            violations.append(SpeechLegalityViolation(
                type=SpeechLegalityViolationType.MISSING_CLASH,
                description=(
                    f"Rebuttal does not address any opponent arguments "
                    f"({[a.label for a in live_opponent]}). Direct clash required."
                ),
                severity="error",
            ))
    return violations


def check_summary(
    transcript: str,
    speaker_side: RoundSide,
    live_args: List[RoundArgument],
    previous_speech_transcript: Optional[str] = None,
) -> List[SpeechLegalityViolation]:
    """Summary: no new independent arguments; must extend offense; include weighing."""
    violations: List[SpeechLegalityViolation] = []

    if _appears_to_add_new_argument(transcript):
        violations.append(SpeechLegalityViolation(
            type=SpeechLegalityViolationType.NEW_ARGUMENT_IN_SUMMARY,
            description="Summary appears to introduce a new independent argument. "
                        "Only responses and extensions from prior speeches are permitted.",
            severity="error",
        ))

    own_args = _find_own_arguments(live_args, speaker_side)
    live_own = [
        a for a in own_args
        if a.status in (ArgumentFlowStatus.INTRODUCED, ArgumentFlowStatus.EXTENDED, ArgumentFlowStatus.LIVE)
    ]
    if live_own and not _mentions_extension(transcript):
        violations.append(SpeechLegalityViolation(
            type=SpeechLegalityViolationType.DROPPED_OFFENSE,
            description=(
                f"Summary does not appear to extend any offense "
                f"({[a.label for a in live_own]}). Offense must be carried through summary."
            ),
            severity="warning",
        ))

    if not _mentions_weighing(transcript):
        violations.append(SpeechLegalityViolation(
            type=SpeechLegalityViolationType.MISSING_WEIGHING,
            description="Summary lacks weighing comparison (magnitude, probability, timeframe, reversibility).",
            severity="warning",
        ))

    return violations


def check_final_focus(
    transcript: str,
    speaker_side: RoundSide,
    live_args: List[RoundArgument],
    summary_transcript: Optional[str] = None,
) -> List[SpeechLegalityViolation]:
    """Final focus: no new arguments; must match summary; comparative weighing."""
    violations: List[SpeechLegalityViolation] = []

    if _appears_to_add_new_argument(transcript):
        violations.append(SpeechLegalityViolation(
            type=SpeechLegalityViolationType.NEW_ARGUMENT_IN_FINAL_FOCUS,
            description="Final focus introduces a new argument. "
                        "Only arguments from summary may be extended here.",
            severity="error",
        ))

    if not _mentions_weighing(transcript):
        violations.append(SpeechLegalityViolation(
            type=SpeechLegalityViolationType.MISSING_WEIGHING,
            description="Final focus must include comparative weighing to win the ballot.",
            severity="error",
        ))

    # Check consistency with summary (very heuristic)
    if summary_transcript:
        # Extract key labels from summary; check at least one appears in final focus
        summary_labels = re.findall(r'\b(?:AC|NC|C)\s*\d+\b', summary_transcript, re.IGNORECASE)
        if summary_labels:
            carried = [
                l for l in summary_labels
                if re.search(re.escape(l), transcript, re.IGNORECASE)
            ]
            if not carried:
                violations.append(SpeechLegalityViolation(
                    type=SpeechLegalityViolationType.INCONSISTENT_WITH_SUMMARY,
                    description=(
                        "Final focus does not appear consistent with summary. "
                        "Arguments from the summary must be extended here."
                    ),
                    severity="warning",
                ))

    return violations


def check_crossfire(
    exchange_text: str,
    new_card_ids_introduced: List[str],
) -> List[SpeechLegalityViolation]:
    """Crossfire: no new evidence introduction."""
    violations: List[SpeechLegalityViolation] = []
    if new_card_ids_introduced:
        violations.append(SpeechLegalityViolation(
            type=SpeechLegalityViolationType.NEW_EVIDENCE_IN_CROSSFIRE,
            description=f"Crossfire introduced {len(new_card_ids_introduced)} new evidence card(s). "
                        "Evidence may not be introduced during crossfire.",
            severity="error",
        ))
    return violations


def check_speech_legality(
    phase: RoundPhaseType,
    transcript: str,
    speaker_side: RoundSide,
    live_args: List[RoundArgument],
    summary_transcript: Optional[str] = None,
    new_card_ids: Optional[List[str]] = None,
) -> List[SpeechLegalityViolation]:
    """Top-level dispatcher for speech-stage legality checks."""
    from app.models.round_simulation import RoundPhaseType as RPT
    if phase in (RPT.FIRST_CONSTRUCTIVE, RPT.SECOND_CONSTRUCTIVE):
        return check_constructive(transcript, speaker_side, live_args)
    if phase in (RPT.FIRST_REBUTTAL, RPT.SECOND_REBUTTAL):
        return check_rebuttal(transcript, speaker_side, live_args)
    if phase in (RPT.FIRST_SUMMARY, RPT.SECOND_SUMMARY):
        return check_summary(transcript, speaker_side, live_args, summary_transcript)
    if phase in (RPT.FIRST_FINAL_FOCUS, RPT.SECOND_FINAL_FOCUS):
        return check_final_focus(transcript, speaker_side, live_args, summary_transcript)
    if phase in (RPT.FIRST_CROSSFIRE, RPT.GRAND_CROSSFIRE, RPT.FINAL_CROSSFIRE):
        return check_crossfire(transcript, new_card_ids or [])
    return []
