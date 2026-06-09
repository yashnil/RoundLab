"use client";

/**
 * PilotChecklist — 6-step pilot loop checklist.
 * Each item derives completion state from real progress/pilot-summary data.
 * Used on /pilot and optionally embedded in the dashboard.
 */

import { CheckCircle2, Circle } from "lucide-react";
import type { PilotSummary, ProgressSummary } from "@/types";

interface ChecklistItem {
  label: string;
  description: string;
  done: boolean;
}

interface Props {
  progress: ProgressSummary;
  pilot?: PilotSummary | null;
}

export function derivePilotChecklist(progress: ProgressSummary, pilot?: PilotSummary | null): ChecklistItem[] {
  return [
    {
      label: "Record your first speech",
      description: "Record or upload a PF speech to get started.",
      done: progress.speech_count > 0,
    },
    {
      label: "Open your flow report",
      description: "Get judge-style feedback on your speech.",
      done: progress.feedback_ready_count > 0,
    },
    {
      label: "Complete one recommended drill",
      description: "Practice the drill targeting your weakest skill.",
      done: progress.drill_attempts_count > 0,
    },
    {
      label: "Re-record the speech",
      description: "Record the speech again to track improvement.",
      done: pilot ? pilot.rerecord_count > 0 : progress.speech_count >= 2,
    },
    {
      label: "View improvement report",
      description: "Compare your new score to the original.",
      done: pilot ? pilot.comparison_count > 0 : false,
    },
    {
      label: "Rate the feedback",
      description: "Tell us if the feedback was useful.",
      done: pilot ? pilot.feedback_rating_count > 0 : false,
    },
  ];
}

export default function PilotChecklist({ progress, pilot }: Props) {
  const items = derivePilotChecklist(progress, pilot);
  const completed = items.filter((i) => i.done).length;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2">
        <span className="section-stamp">Pilot checklist</span>
        <span
          className="text-[10px] font-medium text-ink-faint tabular-nums"
          style={{ fontFamily: "var(--font-jetbrains-mono)" }}
        >
          {completed}/{items.length}
        </span>
      </div>

      {/* Progress bar — sharper, debate-scorecard style */}
      <div className="h-0.5 overflow-hidden rounded-none bg-hairline">
        <div
          className="h-full bg-lav transition-all duration-700"
          style={{ width: `${(completed / items.length) * 100}%` }}
        />
      </div>

      <ol className="flex flex-col gap-2.5">
        {items.map((item, i) => (
          <li key={i} className="flex items-start gap-2.5">
            {item.done ? (
              <CheckCircle2 size={14} className="mt-0.5 shrink-0 text-ok" />
            ) : (
              <Circle size={14} className="mt-0.5 shrink-0 text-ink-faint" />
            )}
            <div className="flex flex-col gap-0.5">
              <span className={`text-xs font-medium ${item.done ? "text-ink-subtle line-through" : "text-ink"}`}>
                {item.label}
              </span>
              {!item.done && (
                <span className="text-[10px] text-ink-faint">{item.description}</span>
              )}
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
