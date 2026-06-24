"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { AdaptationChangesPanel } from "@/components/judge-adaptation/AdaptationChangesPanel";
import { JudgeComparisonPanel } from "@/components/judge-adaptation/JudgeComparisonPanel";
import { JudgeProfileSelector } from "@/components/judge-adaptation/JudgeProfileSelector";
import { JudgeReadinessCard } from "@/components/judge-adaptation/JudgeReadinessCard";
import { JudgeWorkoutCard } from "@/components/judge-adaptation/JudgeWorkoutCard";
import type {
  JudgeAdaptationResult,
  JudgeComparisonResult,
  JudgeProfile,
  JudgeReadinessReport,
  JudgeType,
  JudgeWorkoutRow,
} from "@/types/judgeAdaptation";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Tab = "adapt" | "compare" | "workouts" | "readiness";

const TABS: { id: Tab; label: string }[] = [
  { id: "adapt", label: "Adapt" },
  { id: "compare", label: "Compare Judges" },
  { id: "workouts", label: "Workouts" },
  { id: "readiness", label: "Readiness" },
];

function JudgeAdaptationContent() {
  const searchParams = useSearchParams();
  const userId = searchParams.get("user_id") ?? "demo-user";

  const [tab, setTab] = useState<Tab>("adapt");
  const [profiles, setProfiles] = useState<JudgeProfile[]>([]);
  const [selectedJudge, setSelectedJudge] = useState<JudgeType | null>("lay");
  const [compareJudge, setCompareJudge] = useState<JudgeType | null>("flow");

  const [sourceType, setSourceType] = useState<string>("evidence");
  const [sourceId, setSourceId] = useState<string>("");

  const [adaptResult, setAdaptResult] = useState<JudgeAdaptationResult | null>(null);
  const [compareResult, setCompareResult] = useState<JudgeComparisonResult | null>(null);
  const [readinessReport, setReadinessReport] = useState<JudgeReadinessReport | null>(null);
  const [workouts, setWorkouts] = useState<JudgeWorkoutRow[]>([]);

  const [isAdapting, setIsAdapting] = useState(false);
  const [isComparing, setIsComparing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load profiles on mount
  useEffect(() => {
    fetch(`${API}/judge-adaptation/profiles?user_id=${userId}`)
      .then((r) => r.json())
      .then(setProfiles)
      .catch(() => {});
  }, [userId]);

  // Load workouts
  useEffect(() => {
    if (tab !== "workouts") return;
    fetch(`${API}/judge-adaptation/workouts?user_id=${userId}`)
      .then((r) => r.json())
      .then((data) => setWorkouts(Array.isArray(data) ? data : []))
      .catch(() => {});
  }, [tab, userId]);

  async function runAdaptation() {
    if (!selectedJudge || !sourceId.trim()) {
      setError("Enter a source ID and select a judge type.");
      return;
    }
    setError(null);
    setIsAdapting(true);
    try {
      const r = await fetch(`${API}/judge-adaptation/adapt`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userId,
          judge_type: selectedJudge,
          source_type: sourceType,
          source_id: sourceId,
        }),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      setAdaptResult(await r.json());
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Adaptation failed.");
    } finally {
      setIsAdapting(false);
    }
  }

  async function runComparison() {
    if (!selectedJudge || !compareJudge || !sourceId.trim()) {
      setError("Enter a source ID and select two judge types.");
      return;
    }
    setError(null);
    setIsComparing(true);
    try {
      const r = await fetch(`${API}/judge-adaptation/compare`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userId,
          judge_types: [selectedJudge, compareJudge],
          source_type: sourceType,
          source_id: sourceId,
        }),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      setCompareResult(await r.json());
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Comparison failed.");
    } finally {
      setIsComparing(false);
    }
  }

  async function loadReadiness() {
    if (!selectedJudge || !sourceId.trim()) return;
    try {
      const r = await fetch(`${API}/judge-adaptation/readiness-score`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userId,
          judge_type: selectedJudge,
          source_type: sourceType,
          source_id: sourceId,
        }),
      });
      if (!r.ok) return;
      setReadinessReport(await r.json());
    } catch {}
  }

  async function generateWorkout() {
    if (!selectedJudge || !sourceId.trim()) return;
    try {
      const params = new URLSearchParams({
        user_id: userId,
        judge_type: selectedJudge,
        source_type: sourceType,
        source_id: sourceId,
      });
      const r = await fetch(`${API}/judge-adaptation/workouts/generate?${params}`, {
        method: "POST",
      });
      if (!r.ok) return;
      const workout = await r.json();
      setWorkouts((prev) => [{ ...workout, id: Date.now().toString(), status: "not_started", created_at: new Date().toISOString(), updated_at: new Date().toISOString() }, ...prev]);
    } catch {}
  }

  async function completeWorkout(id: string, notes: string) {
    try {
      const params = new URLSearchParams({ user_id: userId });
      if (notes) params.set("student_notes", notes);
      await fetch(`${API}/judge-adaptation/workouts/${id}/complete?${params}`, {
        method: "PATCH",
      });
      setWorkouts((prev) =>
        prev.map((w) => (w.id === id ? { ...w, status: "completed" as const } : w))
      );
    } catch {}
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-[var(--ink-primary)]">Judge Adaptation</h1>
        <p className="text-sm text-[var(--ink-subtle)] mt-1">
          Adapt your arguments, evidence, and frontlines for different judge types without changing
          what the evidence says.
        </p>
      </div>

      {/* Source input */}
      <div className="rounded-lg border border-[var(--surface-3)] bg-[var(--surface-2)] p-4 space-y-3">
        <p className="text-xs font-medium text-[var(--ink-subtle)] uppercase tracking-wide">
          Source Material
        </p>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[var(--ink-subtle)] mb-1 block">Source Type</label>
            <select
              value={sourceType}
              onChange={(e) => setSourceType(e.target.value)}
              className="w-full text-sm border border-[var(--surface-3)] rounded-md px-3 py-2 bg-[var(--surface-1)] focus:outline-none focus:ring-1 focus:ring-[var(--lavender-8)]"
            >
              {["evidence", "argument", "frontline", "section", "summary", "final_focus"].map(
                (t) => (
                  <option key={t} value={t}>
                    {t.replace(/_/g, " ")}
                  </option>
                )
              )}
            </select>
          </div>
          <div>
            <label className="text-xs text-[var(--ink-subtle)] mb-1 block">Source ID</label>
            <input
              type="text"
              value={sourceId}
              onChange={(e) => setSourceId(e.target.value)}
              placeholder="card ID, argument ID, etc."
              className="w-full text-sm border border-[var(--surface-3)] rounded-md px-3 py-2 bg-[var(--surface-1)] focus:outline-none focus:ring-1 focus:ring-[var(--lavender-8)]"
            />
          </div>
        </div>
      </div>

      {/* Judge selector */}
      <div className="rounded-lg border border-[var(--surface-3)] bg-[var(--surface-2)] p-4">
        <JudgeProfileSelector
          profiles={profiles}
          selected={selectedJudge}
          onSelect={setSelectedJudge}
        />
      </div>

      {error && (
        <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2">
          <p className="text-xs text-red-700">{error}</p>
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-[var(--surface-3)]">
        <div className="flex gap-1">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={[
                "px-4 py-2 text-sm font-medium border-b-2 transition-colors",
                tab === t.id
                  ? "border-[var(--lavender-8)] text-[var(--lavender-8)]"
                  : "border-transparent text-[var(--ink-subtle)] hover:text-[var(--ink-primary)]",
              ].join(" ")}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab content */}
      {tab === "adapt" && (
        <div className="space-y-4">
          <button
            onClick={runAdaptation}
            disabled={isAdapting || !selectedJudge}
            className="px-4 py-2 text-sm font-medium rounded-lg bg-[var(--lavender-8)] text-white hover:opacity-90 disabled:opacity-50 transition-opacity"
          >
            {isAdapting ? "Generating..." : "Generate Adaptation"}
          </button>

          {adaptResult && (
            <div className="space-y-4">
              <div className="rounded-lg border border-[var(--surface-3)] bg-[var(--surface-2)] p-4">
                <p className="text-xs font-medium text-[var(--ink-subtle)] mb-1">Judge Goal</p>
                <p className="text-sm text-[var(--ink-primary)]">{adaptResult.judge_goal}</p>
              </div>

              {adaptResult.what_to_emphasize.length > 0 && (
                <div className="rounded-lg border border-emerald-200 bg-emerald-50/30 p-4">
                  <p className="text-xs font-medium text-emerald-700 mb-2 uppercase tracking-wide">
                    Emphasize
                  </p>
                  <ul className="space-y-1">
                    {adaptResult.what_to_emphasize.map((e, i) => (
                      <li key={i} className="text-xs text-emerald-800 flex items-start gap-2">
                        <span className="shrink-0">↑</span> {e}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {adaptResult.what_to_simplify.length > 0 && (
                <div className="rounded-lg border border-yellow-200 bg-yellow-50/30 p-4">
                  <p className="text-xs font-medium text-yellow-700 mb-2 uppercase tracking-wide">
                    Simplify
                  </p>
                  <ul className="space-y-1">
                    {adaptResult.what_to_simplify.map((e, i) => (
                      <li key={i} className="text-xs text-yellow-800 flex items-start gap-2">
                        <span className="shrink-0">↓</span> {e}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {adaptResult.what_must_remain_explicit.length > 0 && (
                <div className="rounded-lg border border-slate-200 bg-slate-50/30 p-4">
                  <p className="text-xs font-medium text-slate-700 mb-2 uppercase tracking-wide">
                    Never Change
                  </p>
                  <ul className="space-y-1">
                    {adaptResult.what_must_remain_explicit.map((e, i) => (
                      <li key={i} className="text-xs text-slate-700 flex items-start gap-2">
                        <span className="shrink-0 text-red-500">✕</span> {e}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <AdaptationChangesPanel
                changes={adaptResult.changes}
                risks={adaptResult.risks}
              />
            </div>
          )}
        </div>
      )}

      {tab === "compare" && (
        <div className="space-y-4">
          <div className="rounded-lg border border-[var(--surface-3)] bg-[var(--surface-2)] p-4">
            <p className="text-xs font-medium text-[var(--ink-subtle)] uppercase tracking-wide mb-3">
              Compare Against
            </p>
            <JudgeProfileSelector
              profiles={profiles}
              selected={compareJudge}
              onSelect={setCompareJudge}
            />
          </div>

          <button
            onClick={runComparison}
            disabled={isComparing || !selectedJudge || !compareJudge}
            className="px-4 py-2 text-sm font-medium rounded-lg bg-[var(--lavender-8)] text-white hover:opacity-90 disabled:opacity-50 transition-opacity"
          >
            {isComparing ? "Comparing..." : "Compare Judges"}
          </button>

          <JudgeComparisonPanel result={compareResult} isLoading={isComparing} />
        </div>
      )}

      {tab === "workouts" && (
        <div className="space-y-4">
          <button
            onClick={generateWorkout}
            disabled={!selectedJudge || !sourceId.trim()}
            className="px-4 py-2 text-sm font-medium rounded-lg bg-[var(--lavender-8)] text-white hover:opacity-90 disabled:opacity-50 transition-opacity"
          >
            Generate Workout
          </button>

          {workouts.length === 0 ? (
            <div className="text-center py-8 text-[var(--ink-subtle)]">
              <p className="text-sm">No workouts yet. Generate one above or check back after a coach assigns one.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {workouts.map((w) => (
                <JudgeWorkoutCard key={w.id} workout={w} onComplete={completeWorkout} />
              ))}
            </div>
          )}
        </div>
      )}

      {tab === "readiness" && (
        <div className="space-y-4">
          <button
            onClick={loadReadiness}
            disabled={!selectedJudge || !sourceId.trim()}
            className="px-4 py-2 text-sm font-medium rounded-lg bg-[var(--lavender-8)] text-white hover:opacity-90 disabled:opacity-50 transition-opacity"
          >
            Compute Readiness
          </button>

          {readinessReport ? (
            <JudgeReadinessCard report={readinessReport} />
          ) : (
            <div className="text-center py-8 text-[var(--ink-subtle)]">
              <p className="text-sm">
                Judge readiness is a separate score from evidence quality and freshness.
                Select a judge type and source, then click Compute Readiness.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function JudgeAdaptationPage() {
  return (
    <Suspense fallback={<div className="max-w-5xl mx-auto px-4 py-8 text-sm text-[var(--ink-subtle)]">Loading…</div>}>
      <JudgeAdaptationContent />
    </Suspense>
  );
}
