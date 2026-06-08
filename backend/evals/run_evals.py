#!/usr/bin/env python3
"""
RoundLab evaluation runner.

Loads labeled speech fixtures and runs the analysis pipeline,
comparing outputs against ground-truth labels using deterministic metrics.

Usage (from backend/ directory):
    python -m evals.run_evals                           # run all, real LLM
    python -m evals.run_evals --mock                    # run all, mock LLM (no API cost)
    python -m evals.run_evals --mock --limit 3          # first 3 fixtures, mock
    python -m evals.run_evals --fixture good_constructive  # single fixture

Output:
    evals/results/latest.json   (always overwritten)
    evals/results/<run_id>.json (timestamped archive)
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Resolve the backend root so imports work whether run as a module or script
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from evals.models import (
    EvalRunResult,
    EvalSampleResult,
    EvalSpeechFixture,
)
from evals.metrics import (
    check_required_issues,
    detect_hallucinated_evidence,
    normalize_drill_type,
    normalize_issue_type,
    sample_passes,
    score_argument_coverage,
    score_drill_relevance,
    score_issue_detection,
    summarize_eval_result,
)


def _run_signal_detector(fixture: EvalSpeechFixture) -> tuple[list[str], int]:
    """Run the deterministic DebateSignalDetector on a fixture and return signal types + budget."""
    try:
        from app.services.debate_signal_detection import detect_debate_signals
        report = detect_debate_signals(fixture.transcript, fixture.speech_type, fixture.side, fixture.judge_type)
        signal_types = [s.issue_type for s in report.signals]
        budget = report.quality_gate.recommended_issue_budget
        return signal_types, budget
    except Exception:
        return [], -1

FIXTURES_DIR = Path(__file__).parent / "fixtures"
RESULTS_DIR  = Path(__file__).parent / "results"


# ── Fixture loading ────────────────────────────────────────────────────────────

def load_fixtures(
    limit: Optional[int] = None,
    fixture_id: Optional[str] = None,
) -> list[EvalSpeechFixture]:
    """Load and validate all JSON fixtures from the fixtures directory."""
    paths = sorted(FIXTURES_DIR.glob("*.json"))
    fixtures: list[EvalSpeechFixture] = []
    for path in paths:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            fixtures.append(EvalSpeechFixture(**data))
        except Exception as exc:
            print(f"[WARN] Could not load fixture {path.name}: {exc}", file=sys.stderr)

    if fixture_id:
        fixtures = [f for f in fixtures if f.id == fixture_id]
    if limit:
        fixtures = fixtures[:limit]
    return fixtures


# ── Mock pipeline ──────────────────────────────────────────────────────────────

def run_mock_pipeline(fixture: EvalSpeechFixture) -> dict:
    """Return canned pipeline output based on fixture expected values.

    In mock mode the expected outputs are used as the simulated LLM response,
    so the metrics measure the eval machinery rather than model accuracy.
    """
    # Mock arguments — one per expected component
    mock_arguments = []
    for i, comp in enumerate(fixture.expected_argument_components, start=1):
        mock_arguments.append({
            "id": f"arg_{i}",
            "label": comp.label_hint,
            "claim": comp.example_claim or f"Claim for {comp.label_hint}",
            "warrant": comp.example_warrant or ("Clear warrant explaining mechanism." if comp.has_warrant else ""),
            "evidence": comp.example_evidence,
            "impact": comp.example_impact or f"Impact of {comp.label_hint}",
            "argument_type": "offense",
            "issues": [],
            "confidence": 0.85,
        })

    # Mock issues — use expected issues directly
    mock_issues = [
        {
            "issue_type": exp.issue_type,
            "severity": exp.severity,
            "title": f"Mock: {exp.issue_type.replace('_', ' ').title()}",
            "explanation": f"Mock explanation for {exp.issue_type}.",
            "why_it_matters": "Mock why it matters.",
            "recommendation": "Mock recommendation.",
            "affected_argument_labels": [],
            "recommended_drill_type": exp.expected_drill_type or "warranting",
        }
        for exp in fixture.expected_issues
    ]

    # Mock drills — one per expected drill type
    mock_drills = [
        {
            "skill_target": dt,
            "title": f"Mock {dt.replace('_', ' ').title()} Drill",
            "source_weakness": f"Mock weakness targeting {dt}",
            "difficulty": "beginner",
        }
        for dt in fixture.expected_drill_types
    ]

    return {
        "arguments": mock_arguments,
        "issues": mock_issues,
        "drills": mock_drills,
    }


# ── Real pipeline ──────────────────────────────────────────────────────────────

def run_real_pipeline(fixture: EvalSpeechFixture) -> tuple[dict | None, str | None]:
    """Run the actual LLM pipeline on the fixture transcript.

    Returns (output_dict, error_string). error_string is None on success.
    """
    try:
        from app.services.argument_extraction import (
            ArgumentExtractionError,
            extract_arguments,
        )
        from app.services.feedback_generation import (
            FeedbackGenerationError,
            generate_feedback,
        )
        from app.services.drill_generation import DrillGenerationError, generate_drills
    except ImportError as exc:
        return None, f"Import error: {exc}"

    # Step 1: argument extraction
    try:
        arguments = extract_arguments(
            text=fixture.transcript,
            speech_type=fixture.speech_type,
            side=fixture.side,
            topic=fixture.topic,
            judge_type=fixture.judge_type,
        )
        arg_dicts = [a.model_dump() for a in arguments]
    except ArgumentExtractionError as exc:
        return None, f"Argument extraction failed: {exc}"

    # Step 2: feedback generation
    try:
        feedback = generate_feedback(
            text=fixture.transcript,
            arguments=arg_dicts,
            speech_type=fixture.speech_type,
            side=fixture.side,
            topic=fixture.topic,
            judge_type=fixture.judge_type,
            word_count=len(fixture.transcript.split()),
        )
        issues = [i.model_dump() for i in feedback.structured_issues]
    except FeedbackGenerationError as exc:
        return None, f"Feedback generation failed: {exc}"

    # Step 3: drill generation (best-effort — don't fail eval on drill error)
    drills: list[dict] = []
    try:
        drill_items = generate_drills(
            weaknesses=feedback.weaknesses,
            top_3_priorities=getattr(feedback, "top_3_priorities", []) or [],
            transcript_text=fixture.transcript,
            arguments=arg_dicts,
            speech_type=fixture.speech_type,
            side=fixture.side,
            topic=fixture.topic,
            judge_type=fixture.judge_type,
        )
        drills = [d.model_dump() for d in drill_items]
    except DrillGenerationError:
        pass

    return {"arguments": arg_dicts, "issues": issues, "drills": drills}, None


# ── Diagnostic output ─────────────────────────────────────────────────────────

def _print_sample_diagnostics(fixture: EvalSpeechFixture, result: "EvalSampleResult") -> None:
    """Print per-sample actionable diagnostics when a sample fails or has notable gaps."""
    if result.passed and result.issue_metrics.f1 >= 0.8:
        return  # Only show diagnostics for imperfect results

    expected_types = [normalize_issue_type(e.issue_type) for e in fixture.expected_issues]
    expected_types = [t for t in expected_types if t]

    if expected_types:
        print(f"    Expected issues:   {expected_types}")

    if result.predicted_issue_types:
        print(f"    Predicted issues:  {result.predicted_issue_types}")
    elif not result.mock_mode and result.issue_metrics.false_positives > 0:
        print(f"    Predicted issues:  (not stored — upgrade runner to capture)")

    if result.issue_metrics.false_negatives > 0 or result.issue_metrics.false_positives > 0:
        print(f"    Issue detection:   TP={result.issue_metrics.true_positives} "
              f"FP={result.issue_metrics.false_positives} "
              f"FN={result.issue_metrics.false_negatives}")

    if result.detected_signal_types:
        print(f"    Detector signals:  {result.detected_signal_types}  (budget={result.quality_gate_budget})")
    elif result.quality_gate_budget >= 0:
        print(f"    Detector signals:  (none)  (budget={result.quality_gate_budget})")

    if result.required_issues_missed:
        print(f"    REQUIRED MISSED:   {result.required_issues_missed}")

    if result.drill_relevance < 0.5:
        expected_drills = [normalize_drill_type(d) for d in fixture.expected_drill_types if d]
        print(f"    Expected drills:   {expected_drills}  (coverage={result.drill_relevance:.2f})")

    if result.argument_coverage < 0.5:
        hints = [c.label_hint for c in fixture.expected_argument_components]
        print(f"    Arg label hints:   {hints}  (coverage={result.argument_coverage:.2f})")

    if result.hallucinated_evidence_count > 0:
        print(f"    Hallucinations:    {result.hallucinated_evidence_count}")


# ── Single-sample eval ─────────────────────────────────────────────────────────

def eval_fixture(fixture: EvalSpeechFixture, mock: bool) -> EvalSampleResult:
    timestamp = datetime.now(tz=timezone.utc).isoformat()
    error: str | None = None

    if mock:
        output = run_mock_pipeline(fixture)
    else:
        output, error = run_real_pipeline(fixture)
        if output is None:
            # Pipeline completely failed — return a failed result
            return EvalSampleResult(
                fixture_id=fixture.id,
                fixture_title=fixture.title,
                speech_type=fixture.speech_type,
                mock_mode=mock,
                issue_metrics=score_issue_detection(fixture.expected_issues, []),
                argument_coverage=0.0,
                drill_relevance=0.0,
                hallucinated_evidence_count=0,
                required_issues_missed=[e.issue_type for e in fixture.expected_issues if e.required],
                passed=False,
                error=error,
                timestamp=timestamp,
            )

    actual_issues:    list[dict] = output.get("issues", [])
    actual_arguments: list[dict] = output.get("arguments", [])
    actual_drills:    list[dict] = output.get("drills", [])

    issue_metrics        = score_issue_detection(fixture.expected_issues, actual_issues)
    argument_coverage    = score_argument_coverage(fixture.expected_argument_components, actual_arguments)
    drill_relevance      = score_drill_relevance(fixture.expected_drill_types, actual_drills)
    hallucinated         = detect_hallucinated_evidence(actual_arguments)
    required_issues_missed = check_required_issues(fixture.expected_issues, actual_issues)

    passed = sample_passes(
        issue_metrics=issue_metrics,
        argument_coverage=argument_coverage,
        drill_relevance=drill_relevance,
        required_issues_missed=required_issues_missed,
    )

    predicted_types = []
    for issue in actual_issues:
        t = normalize_issue_type(issue.get("issue_type", ""))
        if t:
            predicted_types.append(t)
        else:
            raw = issue.get("issue_type", "")
            if raw:
                predicted_types.append(f"?{raw}")  # unmapped type — visible in diagnostics

    detected_signals, budget = _run_signal_detector(fixture)

    return EvalSampleResult(
        fixture_id=fixture.id,
        fixture_title=fixture.title,
        speech_type=fixture.speech_type,
        mock_mode=mock,
        issue_metrics=issue_metrics,
        argument_coverage=argument_coverage,
        drill_relevance=drill_relevance,
        hallucinated_evidence_count=len(hallucinated),
        required_issues_missed=required_issues_missed,
        passed=passed,
        predicted_issue_types=predicted_types,
        detected_signal_types=detected_signals,
        quality_gate_budget=budget,
        error=error,
        timestamp=timestamp,
    )


# ── Aggregate results ──────────────────────────────────────────────────────────

def aggregate(samples: list[EvalSampleResult], mock: bool, run_id: str) -> EvalRunResult:
    n = len(samples)
    passed = sum(1 for s in samples if s.passed)

    def avg(vals: list[float]) -> float:
        return round(sum(vals) / len(vals), 4) if vals else 0.0

    return EvalRunResult(
        run_id=run_id,
        timestamp=datetime.now(tz=timezone.utc).isoformat(),
        mock_mode=mock,
        total_fixtures=n,
        passed=passed,
        failed=n - passed,
        avg_issue_precision=avg([s.issue_metrics.precision for s in samples]),
        avg_issue_recall=avg([s.issue_metrics.recall for s in samples]),
        avg_issue_f1=avg([s.issue_metrics.f1 for s in samples]),
        avg_argument_coverage=avg([s.argument_coverage for s in samples]),
        avg_drill_relevance=avg([s.drill_relevance for s in samples]),
        total_hallucinated_evidence=sum(s.hallucinated_evidence_count for s in samples),
        samples=samples,
    )


# ── Save results ───────────────────────────────────────────────────────────────

def save_results(result: EvalRunResult) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    data = result.model_dump()
    latest = RESULTS_DIR / "latest.json"
    latest.write_text(json.dumps(data, indent=2), encoding="utf-8")
    archive = RESULTS_DIR / f"{result.run_id}.json"
    archive.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"\nResults written to {latest}")


# ── CLI entry point ────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="RoundLab eval runner — compare pipeline outputs against labeled fixtures."
    )
    parser.add_argument("--mock",    action="store_true", help="Use mock LLM responses (no API calls)")
    parser.add_argument("--limit",   type=int, default=None, help="Run only the first N fixtures")
    parser.add_argument("--fixture", type=str, default=None, help="Run a single fixture by id")
    args = parser.parse_args()

    run_id = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
    mode_label = "MOCK" if args.mock else "REAL"

    fixtures = load_fixtures(limit=args.limit, fixture_id=args.fixture)
    if not fixtures:
        print("No fixtures found. Check evals/fixtures/ directory.", file=sys.stderr)
        sys.exit(1)

    print(f"RoundLab Eval Runner — {mode_label} mode — {len(fixtures)} fixture(s)")
    print("=" * 60)

    samples: list[EvalSampleResult] = []
    for i, fixture in enumerate(fixtures, start=1):
        print(f"\n[{i}/{len(fixtures)}] {fixture.id} ({fixture.speech_type})")
        result = eval_fixture(fixture, mock=args.mock)
        samples.append(result)
        print(f"  {summarize_eval_result(result)}")
        _print_sample_diagnostics(fixture, result)

    agg = aggregate(samples, mock=args.mock, run_id=run_id)

    print("\n" + "=" * 60)
    print(f"SUMMARY: {agg.passed}/{agg.total_fixtures} passed")
    print(f"  Avg issue F1:          {agg.avg_issue_f1:.3f}")
    print(f"  Avg argument coverage: {agg.avg_argument_coverage:.3f}")
    print(f"  Avg drill relevance:   {agg.avg_drill_relevance:.3f}")
    print(f"  Total hallucinations:  {agg.total_hallucinated_evidence}")

    save_results(agg)


if __name__ == "__main__":
    main()
