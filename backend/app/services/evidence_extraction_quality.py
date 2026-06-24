"""Deterministic extraction quality checks.

These checks are used to decide whether the primary extractor's output is
sufficient or whether a fallback should be attempted.

All checks are pure-deterministic (no LLM, no network calls).

Quality signals:
  - Minimum usable character count
  - Paragraph count
  - Boilerplate (navigation/cookie/menu) ratio
  - Repeated-line ratio
  - Alphabetic-text ratio
  - Title/body overlap anomaly
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


# ── Tuning constants ──────────────────────────────────────────────────────────

_MIN_CHARS = 200
_MIN_PARAGRAPHS = 2
_MAX_BOILERPLATE_RATIO = 0.40    # fraction of lines that look like navigation
_MAX_REPEATED_LINE_RATIO = 0.35  # fraction of non-blank lines that are duplicated
_MIN_ALPHA_RATIO = 0.55          # fraction of characters that are alphabetic
_MAX_TITLE_BODY_OVERLAP = 0.80   # if body is mostly the title repeated, it's bad

_BOILERPLATE_PATTERNS = re.compile(
    r"^(cookie|accept all|privacy policy|terms of service|all rights reserved"
    r"|skip to content|toggle navigation|sign in|log in|subscribe|newsletter"
    r"|home\s*[|›>]\s*|breadcrumb|menu|navigation|advertisement"
    r"|©\s*\d{4}|copyright \d{4}|\bsearch\b|\bshare\b|\bcomments?\b)",
    re.IGNORECASE,
)


@dataclass
class ExtractionQualityResult:
    passed: bool = True
    char_count: int = 0
    paragraph_count: int = 0
    boilerplate_ratio: float = 0.0
    repeated_line_ratio: float = 0.0
    alpha_ratio: float = 0.0
    warnings: list[str] = field(default_factory=list)
    failure_reason: str = ""      # the first check that failed


def check_extraction_quality(
    text: str,
    *,
    title: str = "",
    min_chars: int = _MIN_CHARS,
    min_paragraphs: int = _MIN_PARAGRAPHS,
) -> ExtractionQualityResult:
    """Return an ExtractionQualityResult for the extracted text.

    `passed=True` means the text is good enough to proceed with card cutting.
    A fallback should be attempted when `passed=False`.
    """
    result = ExtractionQualityResult()
    warnings = result.warnings

    text = text or ""
    result.char_count = len(text)

    # ── 1. Minimum length ─────────────────────────────────────────────────────
    if result.char_count < min_chars:
        result.passed = False
        result.failure_reason = "too_short"
        warnings.append(
            f"Extraction too short: {result.char_count} chars (min {min_chars})."
        )
        return result

    # ── 2. Paragraph count ────────────────────────────────────────────────────
    paragraphs = [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]
    result.paragraph_count = len(paragraphs)
    if result.paragraph_count < min_paragraphs:
        warnings.append(
            f"Only {result.paragraph_count} paragraph(s) found; text may be too dense."
        )

    # ── 3. Boilerplate ratio ──────────────────────────────────────────────────
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if lines:
        boilerplate_lines = sum(1 for l in lines if _BOILERPLATE_PATTERNS.match(l))
        result.boilerplate_ratio = boilerplate_lines / len(lines)
        if result.boilerplate_ratio > _MAX_BOILERPLATE_RATIO:
            result.passed = False
            result.failure_reason = "boilerplate_dominated"
            warnings.append(
                f"Boilerplate ratio {result.boilerplate_ratio:.1%} exceeds threshold "
                f"({_MAX_BOILERPLATE_RATIO:.0%}). Extraction may be navigation/menu text."
            )
            return result

    # ── 4. Repeated-line ratio ────────────────────────────────────────────────
    if lines:
        seen: dict[str, int] = {}
        for l in lines:
            seen[l] = seen.get(l, 0) + 1
        repeated = sum(1 for l, c in seen.items() if c > 1)
        result.repeated_line_ratio = repeated / len(lines)
        if result.repeated_line_ratio > _MAX_REPEATED_LINE_RATIO:
            warnings.append(
                f"Repeated-line ratio {result.repeated_line_ratio:.1%} is high; "
                "source may contain navigation repetition."
            )

    # ── 5. Alphabetic-text ratio ──────────────────────────────────────────────
    alpha_chars = sum(1 for c in text if c.isalpha())
    result.alpha_ratio = alpha_chars / max(1, len(text))
    if result.alpha_ratio < _MIN_ALPHA_RATIO:
        result.passed = False
        result.failure_reason = "low_alpha_ratio"
        warnings.append(
            f"Alphabetic ratio {result.alpha_ratio:.1%} is below threshold "
            f"({_MIN_ALPHA_RATIO:.0%}). Text may be mostly code, tables, or symbols."
        )
        return result

    # ── 6. Title/body overlap anomaly ─────────────────────────────────────────
    if title and len(text) > 0:
        title_words = set(re.findall(r"\w+", title.lower()))
        body_words = re.findall(r"\w+", text.lower())
        if title_words and body_words:
            overlap = sum(1 for w in body_words if w in title_words)
            overlap_ratio = overlap / len(body_words)
            if overlap_ratio > _MAX_TITLE_BODY_OVERLAP:
                warnings.append(
                    "Body text has very high overlap with title; "
                    "may be a metadata-only page."
                )

    return result
