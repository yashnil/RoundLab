"use client";

/**
 * TournamentWorkoutPanel — displays a speech's tournament prep workout.
 *
 * States:
 *   A. No workout — CTA to generate
 *   B. Loading
 *   C. Error
 *   D. Workout generated (not_started / in_progress)
 *   E. Completed
 */

import { useState } from "react";
import {
  Dumbbell, CheckCircle2, Circle, Loader2, RefreshCw,
  ChevronDown, ChevronUp, ArrowRight, Mic, AlertCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";
import {
  estimateWorkoutMinutes,
  deriveWorkoutProgress,
  getWorkoutFocusLabel,
  getWorkoutStepCategoryLabel,
  getNextIncompleteStep,
} from "@/lib/workoutHelpers";
import type { Workout, WorkoutStep } from "@/types";

interface TournamentWorkoutPanelProps {
  speechId: string;
  userId: string;
  /** Pre-loaded workout (null = not generated, undefined = still loading from parent) */
  workout: Workout | null | undefined;
  onWorkoutChange: (w: Workout | null) => void;
  onStartReRecord: () => void;
}

const CATEGORY_COLORS: Record<string, string> = {
  argument: "text-lav",
  evidence: "text-warn",
  delivery: "text-cyan",
  rerecord: "text-ok",
};

const CATEGORY_BG: Record<string, string> = {
  argument: "bg-lav/8 border-lav/20",
  evidence: "bg-warn/8 border-warn/20",
  delivery: "bg-cyan/8 border-cyan/20",
  rerecord: "bg-ok/8 border-ok/20",
};

function StepCard({
  step,
  index,
  onToggle,
  toggling,
  onOpenDrill,
}: {
  step: WorkoutStep;
  index: number;
  onToggle: (id: string) => void;
  toggling: boolean;
  onOpenDrill?: (drillId: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const isReRecord = step.category === "rerecord";
  const colorClass = CATEGORY_COLORS[step.category] ?? "text-ink-subtle";
  const bgClass = CATEGORY_BG[step.category] ?? "bg-surface-2 border-hairline";

  return (
    <div
      className={[
        "rounded-xl border transition-all",
        step.completed
          ? "border-hairline bg-surface-2 opacity-60"
          : bgClass,
      ].join(" ")}
    >
      <div className="flex items-start gap-3 px-4 py-3">
        {/* Checkbox / complete indicator */}
        <button
          onClick={() => !step.completed && onToggle(step.id)}
          disabled={toggling || step.completed}
          className="mt-0.5 shrink-0 transition-colors"
          aria-label={step.completed ? "Step completed" : "Mark step complete"}
        >
          {step.completed ? (
            <CheckCircle2 size={16} className="text-ok" />
          ) : (
            <Circle size={16} className="text-ink-faint hover:text-ink-subtle" />
          )}
        </button>

        <div className="flex-1 min-w-0">
          {/* Step header */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`text-[10px] font-semibold uppercase tracking-wide ${colorClass}`}>
              {getWorkoutStepCategoryLabel(step.category)}
            </span>
            <span className="text-[10px] text-ink-faint">·</span>
            <span className="text-[10px] text-ink-faint">
              {step.estimated_minutes} min
            </span>
            {step.completed && (
              <span className="text-[10px] font-medium text-ok">Done</span>
            )}
          </div>

          <p
            className={[
              "mt-0.5 text-sm font-semibold",
              step.completed ? "line-through text-ink-faint" : "text-ink",
            ].join(" ")}
          >
            {index + 1}. {step.title}
          </p>

          {/* Problem statement — always visible */}
          {!step.completed && (
            <p className="mt-1 text-xs text-ink-subtle leading-relaxed">
              {step.problem}
            </p>
          )}

          {/* Expandable instruction + success criteria */}
          {!step.completed && (
            <>
              {expanded && (
                <div className="mt-2 flex flex-col gap-2">
                  <div className="rounded-lg border border-hairline bg-surface-1 px-3 py-2.5">
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-ink-faint mb-1">
                      Action
                    </p>
                    <p className="text-xs text-ink-subtle leading-relaxed">
                      {step.instruction}
                    </p>
                  </div>
                  <div className="rounded-lg border border-hairline bg-surface-1 px-3 py-2.5">
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-ink-faint mb-1">
                      Success criteria
                    </p>
                    <p className="text-xs text-ink-subtle leading-relaxed">
                      {step.success_criteria}
                    </p>
                  </div>
                </div>
              )}

              <div className="mt-2 flex items-center gap-2 flex-wrap">
                <button
                  onClick={() => setExpanded((p) => !p)}
                  className="flex items-center gap-0.5 text-[10px] font-medium text-ink-faint hover:text-ink transition-colors"
                >
                  {expanded ? (
                    <>
                      <ChevronUp size={11} /> Hide steps
                    </>
                  ) : (
                    <>
                      <ChevronDown size={11} /> Show steps
                    </>
                  )}
                </button>

                {step.linked_drill_id && onOpenDrill && (
                  <button
                    onClick={() => onOpenDrill(step.linked_drill_id!)}
                    className="flex items-center gap-0.5 text-[10px] font-medium text-lav hover:underline"
                  >
                    Open drill <ArrowRight size={10} />
                  </button>
                )}

                {isReRecord && (
                  <span className="text-[10px] text-ok font-medium">
                    ↑ Use the Re-record button above
                  </span>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default function TournamentWorkoutPanel({
  speechId,
  userId,
  workout,
  onWorkoutChange,
  onStartReRecord,
}: TournamentWorkoutPanelProps) {
  const [generating, setGenerating] = useState(false);
  const [genErr, setGenErr] = useState("");
  const [togglingId, setTogglingId] = useState<string | null>(null);

  async function generateWorkout(force = false) {
    setGenerating(true);
    setGenErr("");
    try {
      const data = await apiFetch<Workout>(`/speeches/${speechId}/workout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, force_regenerate: force }),
      });
      onWorkoutChange(data);
    } catch (e: unknown) {
      setGenErr(e instanceof Error ? e.message : "Failed to generate workout");
    } finally {
      setGenerating(false);
    }
  }

  async function markStepComplete(stepId: string) {
    if (!workout) return;
    setTogglingId(stepId);
    try {
      const updated = await apiFetch<Workout>(`/workouts/${workout.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, completed_step_ids: [stepId] }),
      });
      onWorkoutChange(updated);
    } catch {
      // Best-effort — don't surface error for step completion
    } finally {
      setTogglingId(null);
    }
  }

  // ── State A: not yet generated ─────────────────────────────────────────
  if (workout === null) {
    return (
      <div className="flex flex-col gap-3">
        <div className="flex items-start gap-3 rounded-xl border border-hairline bg-surface-2 px-4 py-4">
          <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-hairline bg-surface-3">
            <Dumbbell size={14} className="text-lav" />
          </div>
          <div className="flex-1">
            <p className="text-sm font-semibold text-ink">Build tournament prep workout</p>
            <p className="mt-0.5 text-xs text-ink-subtle leading-relaxed">
              Turn this report into a focused 10–20 minute practice plan — specific reps,
              timed steps, and a clear re-record goal.
            </p>
          </div>
        </div>

        {genErr && (
          <div className="flex items-center gap-2 rounded-lg border border-danger/25 bg-danger/5 px-3 py-2">
            <AlertCircle size={13} className="shrink-0 text-danger" />
            <p className="text-xs text-danger">{genErr}</p>
          </div>
        )}

        <Button
          size="sm"
          className="w-fit gap-1.5 text-xs"
          onClick={() => generateWorkout(false)}
          disabled={generating}
        >
          {generating ? (
            <>
              <Loader2 size={11} className="animate-spin" />
              Building workout…
            </>
          ) : (
            <>
              <Dumbbell size={11} />
              Generate workout
            </>
          )}
        </Button>
      </div>
    );
  }

  // ── State B: loading from parent ──────────────────────────────────────
  if (workout === undefined) {
    return (
      <div className="flex items-center gap-2 py-4">
        <Loader2 size={14} className="animate-spin text-ink-faint" />
        <p className="text-xs text-ink-faint">Loading workout…</p>
      </div>
    );
  }

  // ── States D/E: workout exists ────────────────────────────────────────
  const { steps, re_record_goal, coach_note } = workout.workout_json;
  const progress = deriveWorkoutProgress(workout);
  const totalMin = estimateWorkoutMinutes(steps);
  const isComplete = workout.status === "completed";
  const nextStep = getNextIncompleteStep(workout);

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-start gap-3">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-hairline bg-surface-2">
            <Dumbbell size={14} className={isComplete ? "text-ok" : "text-lav"} />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="text-sm font-semibold text-ink">{workout.title}</h3>
              {isComplete ? (
                <span
                  className="text-[10px] font-semibold px-1.5 py-0.5 rounded-full"
                  style={{
                    background: "oklch(0.620 0.170 145 / 0.12)",
                    border: "1px solid oklch(0.620 0.170 145 / 0.30)",
                    color: "var(--color-ok)",
                  }}
                >
                  Completed
                </span>
              ) : workout.status === "in_progress" ? (
                <span
                  className="text-[10px] font-semibold px-1.5 py-0.5 rounded-full"
                  style={{
                    background: "oklch(0.510 0.156 278 / 0.10)",
                    border: "1px solid oklch(0.510 0.156 278 / 0.25)",
                    color: "var(--color-lav)",
                  }}
                >
                  In progress
                </span>
              ) : null}
            </div>
            <div className="flex items-center gap-2 mt-0.5 flex-wrap">
              <span className="text-xs text-ink-faint">
                {totalMin} min · {progress.completed}/{progress.total} steps done
              </span>
              {workout.focus_area && (
                <>
                  <span className="text-xs text-ink-faint">·</span>
                  <span className="text-xs text-lav font-medium">
                    {getWorkoutFocusLabel(workout.focus_area)}
                  </span>
                </>
              )}
            </div>
          </div>
        </div>

        <button
          onClick={() => generateWorkout(true)}
          disabled={generating}
          title="Regenerate workout"
          className="shrink-0 rounded-lg p-1.5 text-ink-faint hover:bg-surface-2 hover:text-ink transition-colors"
        >
          <RefreshCw size={12} className={generating ? "animate-spin" : ""} />
        </button>
      </div>

      {/* Progress bar */}
      {!isComplete && progress.total > 0 && (
        <div className="h-1 w-full rounded-full bg-surface-3 overflow-hidden">
          <div
            className="h-full rounded-full bg-lav transition-all duration-300"
            style={{ width: `${progress.pct}%` }}
          />
        </div>
      )}

      {/* Coach note */}
      {coach_note && (
        <div className="rounded-lg border border-hairline bg-surface-2 px-3.5 py-2.5">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-ink-faint mb-1">
            Coach note
          </p>
          <p className="text-xs text-ink-subtle leading-relaxed">{coach_note}</p>
        </div>
      )}

      {/* Completed state */}
      {isComplete ? (
        <div className="flex flex-col gap-3">
          <div
            className="flex items-center gap-3 rounded-xl px-4 py-3.5"
            style={{
              background: "oklch(0.620 0.170 145 / 0.06)",
              border: "1px solid oklch(0.620 0.170 145 / 0.25)",
            }}
          >
            <CheckCircle2 size={16} className="shrink-0 text-ok" />
            <div>
              <p className="text-sm font-semibold text-ink">Workout completed</p>
              <p className="mt-0.5 text-xs text-ok leading-relaxed">{re_record_goal}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button size="sm" className="gap-1.5 text-xs" onClick={onStartReRecord}>
              <Mic size={11} />
              Re-record speech
            </Button>
            <Button
              size="sm"
              variant="secondary"
              className="gap-1.5 text-xs"
              onClick={() => generateWorkout(true)}
              disabled={generating}
            >
              <RefreshCw size={11} className={generating ? "animate-spin" : ""} />
              New workout
            </Button>
          </div>
        </div>
      ) : (
        <>
          {/* Step list */}
          <div className="flex flex-col gap-2">
            {steps.map((step, i) => (
              <StepCard
                key={step.id}
                step={step}
                index={i}
                onToggle={markStepComplete}
                toggling={togglingId === step.id}
              />
            ))}
          </div>

          {/* Re-record goal */}
          <div className="rounded-lg border border-hairline bg-surface-2 px-3.5 py-2.5">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-ink-faint mb-1">
              Re-record goal
            </p>
            <p className="text-xs text-ink-subtle leading-relaxed">{re_record_goal}</p>
          </div>

          {/* Re-record CTA if last remaining step */}
          {nextStep?.category === "rerecord" &&
            steps.filter((s) => !s.completed && s.category !== "rerecord").length === 0 && (
            <Button size="sm" className="w-fit gap-1.5 text-xs" onClick={onStartReRecord}>
              <Mic size={11} />
              Re-record speech
            </Button>
          )}
        </>
      )}

      {genErr && (
        <p className="text-xs text-danger">{genErr}</p>
      )}
    </div>
  );
}
