"use client";

import { useState } from "react";
import { Play, CheckCircle, Clock, BookOpen } from "lucide-react";
import { apiFetch } from "@/lib/api";
import type { PrepWorkout, WorkoutType } from "@/types/prep";

const WORKOUT_TYPE_LABELS: Record<WorkoutType, string> = {
  evidence_explanation: "Explain the Warrant",
  card_comparison: "Card Comparison",
  frontline_speed: "Frontline Speed Drill",
  summary_extension: "Summary Extension",
  evidence_indictment: "Evidence Indictment",
  stale_evidence: "Defend Older Evidence",
  lay_judge_evidence: "Lay-Judge Explanation",
};

const WORKOUT_TYPE_COLORS: Record<WorkoutType, string> = {
  evidence_explanation: "bg-lav/10 text-lav border-lav/20",
  card_comparison: "bg-sky-50 text-sky-700 border-sky-200",
  frontline_speed: "bg-rose-50 text-rose-700 border-rose-200",
  summary_extension: "bg-amber-50 text-amber-700 border-amber-200",
  evidence_indictment: "bg-danger/10 text-danger border-danger/20",
  stale_evidence: "bg-surface-muted text-ink-subtle border-border",
  lay_judge_evidence: "bg-ok/10 text-ok border-ok/20",
};

function WorkoutCard({
  workout,
  onComplete,
}: {
  workout: PrepWorkout;
  onComplete: (id: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [completing, setCompleting] = useState(false);
  const isDone = workout.status === "completed";

  async function handleComplete() {
    setCompleting(true);
    try {
      await apiFetch(`/prep/workouts/${workout.id}/complete?user_id=${workout.user_id}`, {
        method: "PATCH",
      });
      onComplete(workout.id);
    } catch {
      // non-fatal
    } finally {
      setCompleting(false);
    }
  }

  const minutes = Math.ceil(workout.time_limit_seconds / 60);

  return (
    <div
      className={`rounded-xl border overflow-hidden ${isDone ? "border-border opacity-60" : "border-border hover:border-lav/30"} transition-colors`}
    >
      <div className="px-4 py-3 space-y-2">
        <div className="flex items-start gap-2">
          <div className="flex-1 min-w-0 space-y-1">
            <div className="flex items-center gap-2 flex-wrap">
              <span
                className={`text-[10px] px-1.5 py-0.5 rounded border ${WORKOUT_TYPE_COLORS[workout.workout_type]}`}
              >
                {WORKOUT_TYPE_LABELS[workout.workout_type]}
              </span>
              <span className="text-[10px] text-ink-faint flex items-center gap-0.5">
                <Clock size={9} />
                {workout.time_limit_seconds}s limit
              </span>
            </div>
            <p className={`text-[13px] font-semibold ${isDone ? "line-through text-ink-subtle" : "text-ink"}`}>
              {workout.title}
            </p>
            {workout.description && (
              <p className="text-[11px] text-ink-subtle">{workout.description}</p>
            )}
          </div>
          {isDone ? (
            <CheckCircle size={16} className="text-ok shrink-0 mt-0.5" />
          ) : (
            <button
              onClick={() => setExpanded((e) => !e)}
              className="flex items-center gap-1 text-[11px] text-lav hover:underline shrink-0"
            >
              <Play size={11} />
              {expanded ? "Hide" : "Start"}
            </button>
          )}
        </div>

        {expanded && !isDone && (
          <div className="space-y-3 pt-1 border-t border-hairline">
            {workout.source_card_body && (
              <div className="rounded-lg bg-surface-muted border border-border px-3 py-2">
                <p className="text-[10px] font-semibold text-ink-subtle mb-1 flex items-center gap-1">
                  <BookOpen size={10} />
                  Evidence Card
                </p>
                {workout.source_card_tag && (
                  <p className="text-[11px] font-semibold text-ink mb-1">
                    {workout.source_card_tag}
                  </p>
                )}
                <p className="text-[11px] text-ink-subtle leading-relaxed line-clamp-4">
                  {workout.source_card_body}
                </p>
              </div>
            )}

            <div>
              <p className="text-[11px] font-semibold text-ink mb-1">Your task:</p>
              <p className="text-[12px] text-ink leading-relaxed whitespace-pre-wrap">
                {workout.prompt}
              </p>
            </div>

            {workout.instructions && (
              <div>
                <p className="text-[11px] font-semibold text-ink-subtle mb-1">Steps:</p>
                <p className="text-[11px] text-ink-subtle leading-relaxed whitespace-pre-wrap">
                  {workout.instructions}
                </p>
              </div>
            )}

            {workout.success_criteria.length > 0 && (
              <div>
                <p className="text-[11px] font-semibold text-ink-subtle mb-1">
                  Success criteria:
                </p>
                <ul className="space-y-0.5">
                  {workout.success_criteria.map((c, i) => (
                    <li key={i} className="text-[11px] text-ink-subtle flex items-start gap-1.5">
                      <span className="text-lav mt-0.5 shrink-0">·</span>
                      {c}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div className="flex items-center justify-between pt-2 border-t border-hairline">
              <p className="text-[10px] text-ink-faint">
                Complete this out loud, then mark done.
              </p>
              <button
                onClick={handleComplete}
                disabled={completing}
                className="text-[12px] px-3 py-1.5 rounded-md bg-ok text-white disabled:opacity-50 hover:bg-ok/80 transition-colors"
              >
                {completing ? "Saving…" : "Mark Complete"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

interface PrepWorkoutPanelProps {
  workouts: PrepWorkout[];
  onWorkoutComplete: (id: string) => void;
}

export function PrepWorkoutPanel({ workouts, onWorkoutComplete }: PrepWorkoutPanelProps) {
  const active = workouts.filter((w) => w.status !== "completed" && w.status !== "skipped");
  const done = workouts.filter((w) => w.status === "completed");

  if (workouts.length === 0) {
    return (
      <p className="py-8 text-center text-[12px] text-ink-subtle">
        No workouts generated yet. Generate a prep plan first.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      <p className="text-[12px] text-ink-subtle">
        {active.length} workout{active.length !== 1 ? "s" : ""} remaining ·{" "}
        {done.length} completed
      </p>
      <div className="space-y-2">
        {active.map((wo) => (
          <WorkoutCard key={wo.id} workout={wo} onComplete={onWorkoutComplete} />
        ))}
      </div>
      {done.length > 0 && (
        <details className="space-y-2">
          <summary className="text-[11px] text-ink-subtle cursor-pointer hover:text-ink">
            Show {done.length} completed
          </summary>
          <div className="space-y-2 pt-2">
            {done.map((wo) => (
              <WorkoutCard key={wo.id} workout={wo} onComplete={() => {}} />
            ))}
          </div>
        </details>
      )}
    </div>
  );
}
