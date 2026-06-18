import { Send, Users, ClipboardCheck, TrendingDown, Zap, ArrowRight } from "lucide-react";
import type { LucideIcon } from "lucide-react";

/**
 * Team section visual — the coach loop a program sees before signing up:
 * Assign → students complete → review queue → skill gap surfaces → assign a drill.
 * Distinct topic (Final Focus voter clarity) so it never repeats the hero sample.
 */

interface Stage {
  icon: LucideIcon;
  label: string;
  detail: string;
  emphasis?: "gap";
}

const STAGES: Stage[] = [
  { icon: Send, label: "Assign", detail: "Final Focus · voter clarity · due Fri" },
  { icon: Users, label: "Completed", detail: "3 of 4 submitted" },
  { icon: ClipboardCheck, label: "Review queue", detail: "1 ready · keyboard-fast" },
  { icon: TrendingDown, label: "Skill gap", detail: "Weighing trails the team", emphasis: "gap" },
  { icon: Zap, label: "Assign drill", detail: "Weighing sprint → 2 students" },
];

export default function TeamWorkflowStrip() {
  return (
    <div className="rounded-2xl border border-hairline bg-surface-1 p-5">
      <div className="mb-4 flex flex-col gap-1">
        <p className="text-heading text-ink">A coach&apos;s loop, not a student dashboard</p>
        <p className="mt-0.5 text-xs text-ink-subtle">
          Assign practice, review submissions fast, and turn a team-wide gap into the next drill.
        </p>
      </div>

      <ol className="flex flex-col gap-2 lg:flex-row lg:items-stretch lg:gap-0">
        {STAGES.map((stage, i) => {
          const Icon = stage.icon;
          const isGap = stage.emphasis === "gap";
          return (
            <li key={stage.label} className="flex items-stretch lg:flex-1">
              <div
                className={
                  "flex flex-1 flex-col gap-1.5 rounded-lg border p-3 " +
                  (isGap
                    ? "border-warn/30 bg-warn/[0.07]"
                    : "border-hairline bg-surface-2")
                }
              >
                <div className="flex items-center gap-1.5">
                  <Icon
                    size={13}
                    className={"shrink-0 " + (isGap ? "text-warn" : "text-ink-faint")}
                    aria-hidden
                  />
                  <span
                    className={
                      "text-[10px] font-bold uppercase tracking-wider " +
                      (isGap ? "text-warn" : "text-ink-faint")
                    }
                  >
                    {stage.label}
                  </span>
                </div>
                <p className="text-xs leading-relaxed text-ink-muted">{stage.detail}</p>
              </div>
              {i < STAGES.length - 1 && (
                <div
                  className="hidden items-center px-1 text-hairline-strong lg:flex"
                  aria-hidden
                >
                  <ArrowRight size={14} />
                </div>
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
