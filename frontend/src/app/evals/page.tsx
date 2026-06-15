"use client";

/**
 * /evals — Development eval dashboard.
 *
 * Reads from the static SAMPLE_EVAL_RESULTS fixture (mock-mode run).
 * To use real results, replace SAMPLE_EVAL_RESULTS with the output of:
 *   python -m evals.run_evals --mock       (fast, no API cost)
 *   python -m evals.run_evals              (real LLM, costs money)
 *
 * This page is for development and demo quality review.
 * It is NOT shown in the student dashboard or nav.
 */

import { CheckCircle2, XCircle, TrendingUp, AlertCircle, FlaskConical } from "lucide-react";
import AppShell from "@/components/shell/AppShell";
import { SAMPLE_EVAL_RESULTS, type EvalSampleResult } from "@/lib/eval_results_fixture";

// ── Helpers ────────────────────────────────────────────────────────────────────

function pct(n: number) {
  return `${(n * 100).toFixed(1)}%`;
}

function MetricBar({ label, value }: { label: string; value: number }) {
  const color = value >= 0.8 ? "bg-ok" : value >= 0.5 ? "bg-warn" : "bg-danger";
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs text-ink-subtle">{label}</span>
        <span className="font-mono text-xs font-semibold text-ink">{pct(value)}</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-hairline">
        <div className={`h-full rounded-full ${color}`} style={{ width: pct(value) }} />
      </div>
    </div>
  );
}

function SampleRow({ sample }: { sample: EvalSampleResult }) {
  return (
    <tr className="border-b border-hairline last:border-0">
      <td className="py-3 pr-4">
        <div className="flex items-center gap-2">
          {sample.passed
            ? <CheckCircle2 size={13} className="shrink-0 text-ok" />
            : <XCircle     size={13} className="shrink-0 text-danger" />}
          <span className="text-xs font-mono text-ink-subtle">{sample.fixture_id}</span>
        </div>
        <p className="mt-0.5 pl-5 text-[10px] text-ink-faint">{sample.fixture_title}</p>
      </td>
      <td className="py-3 pr-4">
        <span className="rounded-full border border-hairline bg-surface-2 px-2 py-0.5 text-[10px] text-ink-faint capitalize">
          {sample.speech_type}
        </span>
      </td>
      <td className="py-3 pr-4 font-mono text-xs text-ink">{pct(sample.issue_metrics.f1)}</td>
      <td className="py-3 pr-4 font-mono text-xs text-ink">{pct(sample.argument_coverage)}</td>
      <td className="py-3 pr-4 font-mono text-xs text-ink">{pct(sample.drill_relevance)}</td>
      <td className="py-3 pr-4">
        {sample.hallucinated_evidence_count > 0
          ? <span className="text-xs font-semibold text-warn">{sample.hallucinated_evidence_count}</span>
          : <span className="text-[10px] text-ink-faint">—</span>}
      </td>
      <td className="py-3">
        {sample.required_issues_missed.length > 0
          ? <span className="text-[10px] text-danger">{sample.required_issues_missed.join(", ")}</span>
          : <span className="text-[10px] text-ok">none</span>}
      </td>
    </tr>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function EvalsPage() {
  const r = SAMPLE_EVAL_RESULTS;
  const passRate = r.total_fixtures > 0 ? r.passed / r.total_fixtures : 0;

  return (
    <AppShell maxWidth="full" bare>
        <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">

          {/* Dev banner */}
          <div className="mb-6 flex items-center gap-2 rounded-lg border border-lav/20 bg-lav/5 px-4 py-2.5">
            <FlaskConical size={14} className="shrink-0 text-lav" />
            <p className="text-xs text-ink-subtle">
              <span className="font-semibold text-ink">Development dashboard.</span>{" "}
              Displays static fixture results from mock-mode eval run. Run{" "}
              <code className="rounded bg-surface-2 px-1 py-0.5 font-mono text-[10px]">
                python -m evals.run_evals --mock
              </code>{" "}
              to regenerate.
            </p>
          </div>

          {/* Header */}
          <div className="mb-6 flex flex-col gap-1">
            <h1 className="text-xl font-bold text-ink">AI Pipeline Eval Dashboard</h1>
            <p className="text-xs text-ink-faint">
              Run ID: <span className="font-mono">{r.run_id}</span>{" "}
              · {r.total_fixtures} fixtures{" "}
              · {r.mock_mode ? "Mock mode" : "Real LLM"}
            </p>
          </div>

          {/* Summary cards */}
          <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              { label: "Pass rate", value: `${r.passed}/${r.total_fixtures}`, sub: pct(passRate), ok: passRate >= 0.8 },
              { label: "Avg Issue F1", value: pct(r.avg_issue_f1), sub: "precision/recall", ok: r.avg_issue_f1 >= 0.7 },
              { label: "Arg coverage", value: pct(r.avg_argument_coverage), sub: "components found", ok: r.avg_argument_coverage >= 0.7 },
              { label: "Drill relevance", value: pct(r.avg_drill_relevance), sub: "target types covered", ok: r.avg_drill_relevance >= 0.7 },
            ].map((card) => (
              <div
                key={card.label}
                className={`rounded-xl border p-4 ${
                  card.ok
                    ? "border-ok/20 bg-ok/5"
                    : "border-warn/20 bg-warn/5"
                }`}
              >
                <p className="text-[10px] text-ink-faint">{card.label}</p>
                <p className="mt-0.5 text-xl font-bold tabular-nums text-ink">{card.value}</p>
                <p className="text-[10px] text-ink-subtle">{card.sub}</p>
              </div>
            ))}
          </div>

          {/* Metric bars */}
          <div className="mb-6 flex flex-col gap-3 rounded-xl border border-hairline bg-surface-1 p-5">
            <p className="text-xs font-semibold text-ink-subtle">Aggregate metrics</p>
            <MetricBar label="Issue detection precision" value={r.avg_issue_precision} />
            <MetricBar label="Issue detection recall"    value={r.avg_issue_recall}    />
            <MetricBar label="Issue detection F1"        value={r.avg_issue_f1}        />
            <MetricBar label="Argument component coverage" value={r.avg_argument_coverage} />
            <MetricBar label="Drill type relevance"      value={r.avg_drill_relevance} />
            {r.total_hallucinated_evidence > 0 && (
              <div className="flex items-center gap-2 rounded-md border border-warn/20 bg-warn/5 px-3 py-2">
                <AlertCircle size={12} className="text-warn" />
                <p className="text-xs text-warn">
                  {r.total_hallucinated_evidence} hallucinated evidence claim{r.total_hallucinated_evidence !== 1 ? "s" : ""} detected across all samples.
                </p>
              </div>
            )}
          </div>

          {/* Sample table */}
          <div className="overflow-hidden rounded-xl border border-hairline bg-surface-1">
            <div className="border-b border-hairline px-5 py-3">
              <p className="text-xs font-semibold text-ink-subtle">
                Sample results
                <span className="ml-2 rounded-full border border-hairline bg-surface-2 px-1.5 py-0.5 text-[10px] text-ink-faint">
                  {r.samples.length}
                </span>
              </p>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-hairline text-left">
                    {["Fixture", "Type", "Issue F1", "Arg cov.", "Drill rel.", "Halluc.", "Missed required"].map((h) => (
                      <th key={h} className="px-0 py-2 pr-4 pl-5 text-[10px] font-semibold uppercase tracking-wide text-ink-faint first:pl-5">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="px-5">
                  {r.samples.map((s) => (
                    <SampleRow key={s.fixture_id} sample={s} />
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Run instructions */}
          <div className="mt-6 rounded-xl border border-hairline bg-surface-1 p-5">
            <p className="mb-3 text-xs font-semibold text-ink-subtle">How to run evals</p>
            <div className="flex flex-col gap-2">
              {[
                { cmd: "python -m evals.run_evals --mock",           label: "Mock mode — fast, no API cost, tests eval machinery" },
                { cmd: "python -m evals.run_evals --mock --limit 3", label: "Mock mode — run 3 fixtures only" },
                { cmd: "python -m evals.run_evals",                  label: "Real LLM — accurate, uses OpenAI API" },
                { cmd: "python -m evals.run_evals --fixture good_constructive", label: "Single fixture by ID" },
              ].map(({ cmd, label }) => (
                <div key={cmd} className="flex items-start gap-3">
                  <code className="shrink-0 rounded bg-surface-2 px-2 py-1 font-mono text-[10px] text-lav">
                    {cmd}
                  </code>
                  <span className="text-[10px] text-ink-faint">{label}</span>
                </div>
              ))}
            </div>
            <p className="mt-3 text-[10px] text-ink-faint">
              Results are written to <code className="font-mono">backend/evals/results/latest.json</code>.
              Copy the JSON into <code className="font-mono">src/lib/eval_results_fixture.ts</code> to update this dashboard.
            </p>
          </div>

        </div>
    </AppShell>
  );
}
