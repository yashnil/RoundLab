"use client";

import type { RoundDrill } from "@/types/round";

interface Props {
  drills: RoundDrill[];
  onGenerateDrills: () => void;
  isLoading: boolean;
}

const SKILL_COLORS: Record<string, string> = {
  drops: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  clash: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
  extensions: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
  evidence: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  weighing: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400",
  judge_adaptation: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  pacing_control: "bg-slate-100 text-slate-700 dark:bg-slate-900/30 dark:text-slate-400",
};

function DrillCard({ drill }: { drill: RoundDrill }) {
  const colorClass = SKILL_COLORS[drill.skill_target] ?? "bg-muted text-muted-foreground";
  const minutes = Math.floor(drill.time_limit_seconds / 60);
  const secs = drill.time_limit_seconds % 60;
  const timeLabel = minutes > 0 ? `${minutes}:${String(secs).padStart(2, "0")}` : `${secs}s`;

  return (
    <div className="rounded-lg border p-4 space-y-3">
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-sm font-semibold leading-tight">{drill.title}</h3>
        <span className={`shrink-0 inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${colorClass}`}>
          {drill.skill_target.replace(/_/g, " ")}
        </span>
      </div>

      <p className="text-xs text-muted-foreground leading-relaxed">{drill.prompt}</p>

      {drill.source.weakness_description && (
        <div className="rounded-md bg-muted/50 px-3 py-2">
          <p className="text-xs text-muted-foreground italic">&ldquo;{drill.source.weakness_description}&rdquo;</p>
        </div>
      )}

      <div className="space-y-1">
        <p className="text-xs font-medium">Success criteria:</p>
        <ul className="space-y-0.5">
          {drill.success_criteria.map((c, i) => (
            <li key={i} className="text-xs text-muted-foreground flex items-start gap-1.5">
              <span className="mt-0.5 text-primary shrink-0">·</span>
              {c}
            </li>
          ))}
        </ul>
      </div>

      <div className="flex items-center justify-between pt-1">
        <span className="text-xs text-muted-foreground">Time limit: {timeLabel}</span>
        <button
          className="rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground"
          disabled
          title="Connect to drill attempt recorder in a future pass"
        >
          Practice
        </button>
      </div>
    </div>
  );
}

export function RoundDrillsView({ drills, onGenerateDrills, isLoading }: Props) {
  if (drills.length === 0) {
    return (
      <div className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Generate targeted drills from this round&#39;s failures and dropped arguments.
        </p>
        <button
          onClick={onGenerateDrills}
          disabled={isLoading}
          className="rounded-md bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground disabled:opacity-50 transition-opacity"
        >
          {isLoading ? "Generating drills..." : "Generate Post-Round Drills"}
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold">Post-Round Drills ({drills.length})</h2>
        <button
          onClick={onGenerateDrills}
          disabled={isLoading}
          className="rounded-md border px-3 py-1.5 text-xs font-medium hover:bg-accent disabled:opacity-50 transition-colors"
        >
          {isLoading ? "Regenerating..." : "Regenerate"}
        </button>
      </div>
      <div className="grid gap-4">
        {drills.map((d) => <DrillCard key={d.id} drill={d} />)}
      </div>
    </div>
  );
}
