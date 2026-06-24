"use client";

import { useState } from "react";
import { JudgeWorkoutCreate, JudgeWorkoutRow, JUDGE_TYPE_LABELS } from "@/types/judgeAdaptation";

interface Props {
  workout: JudgeWorkoutCreate | JudgeWorkoutRow;
  onComplete?: (id: string, notes: string) => void;
  disabled?: boolean;
}

const WORKOUT_TYPE_LABELS: Record<string, string> = {
  lay_explanation: "Lay Explanation",
  parent_context: "Parent Context",
  flow_extension: "Flow Extension",
  technical_concession: "Technical Concession",
  judge_switch: "Judge Switch",
  evidence_adaptation: "Evidence Adaptation",
  final_focus_voter: "Final Focus Voter",
};

export function JudgeWorkoutCard({ workout, onComplete, disabled }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [notes, setNotes] = useState("");
  const isRow = "id" in workout;
  const isCompleted = isRow && (workout as JudgeWorkoutRow).status === "completed";

  const formatTime = (s: number) => {
    if (s < 60) return `${s}s`;
    return `${Math.floor(s / 60)}m ${s % 60 > 0 ? `${s % 60}s` : ""}`.trim();
  };

  return (
    <div
      className={[
        "rounded-lg border",
        isCompleted
          ? "border-emerald-200 bg-emerald-50/30"
          : "border-[var(--surface-3)] bg-[var(--surface-2)]",
      ].join(" ")}
    >
      <button
        className="w-full flex items-start justify-between gap-3 p-4 text-left"
        onClick={() => setExpanded((e) => !e)}
        aria-expanded={expanded}
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className="text-[10px] font-semibold uppercase tracking-wide text-[var(--lavender-8)]">
              {WORKOUT_TYPE_LABELS[workout.workout_type] || workout.workout_type}
            </span>
            <span className="text-[10px] text-[var(--ink-subtle)] border border-[var(--surface-3)] rounded px-1">
              {JUDGE_TYPE_LABELS[workout.judge_type]}
            </span>
            {workout.comparison_judge_type && (
              <span className="text-[10px] text-[var(--ink-subtle)] border border-[var(--surface-3)] rounded px-1">
                → {JUDGE_TYPE_LABELS[workout.comparison_judge_type]}
              </span>
            )}
            <span className="text-[10px] text-[var(--ink-subtle)] ml-auto">
              {formatTime(workout.time_limit_seconds)}
            </span>
          </div>
          <p className="text-sm font-medium text-[var(--ink-primary)] truncate">{workout.title}</p>
          {workout.description && (
            <p className="text-xs text-[var(--ink-subtle)] mt-0.5 line-clamp-1">
              {workout.description}
            </p>
          )}
        </div>
        <span className="text-[var(--ink-subtle)] text-xs mt-1 shrink-0">
          {expanded ? "▲" : "▼"}
        </span>
      </button>

      {expanded && (
        <div className="px-4 pb-4 border-t border-[var(--surface-3)] pt-3 space-y-4">
          <div>
            <p className="text-[11px] font-medium text-[var(--ink-subtle)] uppercase tracking-wide mb-2">
              Drill Prompt
            </p>
            <p className="text-xs text-[var(--ink-primary)] whitespace-pre-line">{workout.prompt}</p>
          </div>

          {workout.instructions && (
            <div>
              <p className="text-[11px] font-medium text-[var(--ink-subtle)] uppercase tracking-wide mb-1">
                How to Practice
              </p>
              <p className="text-xs text-[var(--ink-primary)]">{workout.instructions}</p>
            </div>
          )}

          {workout.success_criteria.length > 0 && (
            <div>
              <p className="text-[11px] font-medium text-[var(--ink-subtle)] uppercase tracking-wide mb-2">
                Success Criteria
              </p>
              <ul className="space-y-1">
                {workout.success_criteria.map((c, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-[var(--ink-primary)]">
                    <span className="text-[var(--lavender-8)] shrink-0 mt-0.5">□</span>
                    {c}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {isRow && !isCompleted && onComplete && (
            <div className="space-y-2">
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Notes (optional)..."
                className="w-full text-xs border border-[var(--surface-3)] rounded-md p-2 bg-[var(--surface-1)] resize-none h-16 focus:outline-none focus:ring-1 focus:ring-[var(--lavender-8)]"
              />
              <button
                onClick={() => onComplete((workout as JudgeWorkoutRow).id, notes)}
                disabled={disabled}
                className="px-3 py-1.5 text-xs font-medium rounded-md bg-[var(--lavender-8)] text-white hover:opacity-90 disabled:opacity-50 transition-opacity"
              >
                Mark Complete
              </button>
            </div>
          )}

          {isCompleted && (
            <p className="text-xs text-emerald-600 font-medium">✓ Completed</p>
          )}
        </div>
      )}
    </div>
  );
}
