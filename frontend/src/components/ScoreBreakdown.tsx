import { Progress } from "@/components/ui/progress";
import type { FeedbackScores } from "@/types";

const DIMS: { key: keyof FeedbackScores; label: string }[] = [
  { key: "clash",            label: "Clash"        },
  { key: "weighing",         label: "Weighing"     },
  { key: "extensions",       label: "Extensions"   },
  { key: "drops",            label: "Drops"        },
  { key: "judge_adaptation", label: "Judge Adapt." },
];

function barColor(pct: number): string {
  if (pct >= 70) return "bg-lav";
  if (pct >= 50) return "bg-warn";
  return "bg-danger";
}

export default function ScoreBreakdown({ scores }: { scores: FeedbackScores }) {
  return (
    <div className="flex flex-col gap-3">
      {DIMS.map(({ key, label }, i) => {
        const value = scores[key];
        const pct   = (value / 20) * 100;
        return (
          <div key={key} className="flex items-center gap-3">
            <span className="w-28 shrink-0 text-sm text-ink-subtle">{label}</span>
            <Progress
              value={value}
              max={20}
              colorClass={barColor(pct)}
              animated
              animationDelay={0.1 + i * 0.08}
              className="h-1"
            />
            <span className="w-10 text-right text-xs font-semibold tabular-nums text-ink-muted">
              {value}/20
            </span>
          </div>
        );
      })}
    </div>
  );
}
