"use client";

import { Target, ArrowRight } from "lucide-react";
import type { FeedbackReport } from "@/types";
import { deriveSkills, SKILL_GROUP_LABELS, type SkillInsight, type SkillBand } from "@/lib/reportModel";
import { cn } from "@/lib/utils";

interface SkillsWorkspaceProps {
  feedback: FeedbackReport;
  deliveryScore?: number | null;
  drillsHref?: string;
}

const BAND_META: Record<SkillBand, { label: string; bar: string; text: string }> = {
  strong: { label: "Strong", bar: "bg-ok", text: "text-ok" },
  developing: { label: "Developing", bar: "bg-warn", text: "text-warn" },
  weak: { label: "Needs work", bar: "bg-danger", text: "text-danger" },
};

function Meter({ insight }: { insight: SkillInsight }) {
  const pct = Math.round((insight.score / insight.max) * 100);
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-hairline">
      <div className={cn("h-full rounded-full", BAND_META[insight.band].bar)} style={{ width: `${pct}%` }} />
    </div>
  );
}

export default function SkillsWorkspace({ feedback, deliveryScore, drillsHref = "#drills" }: SkillsWorkspaceProps) {
  const { priority, insights } = deriveSkills(feedback, deliveryScore);
  const secondary = insights.filter((i) => i.key !== priority?.key);

  // Group the secondary skills.
  const groups = secondary.reduce<Record<string, SkillInsight[]>>((acc, i) => {
    (acc[i.group] ??= []).push(i);
    return acc;
  }, {});

  return (
    <section id="skills" className="flex flex-col gap-4 scroll-mt-20" aria-label="Skills">
      <h3 className="text-heading text-ink">Skills</h3>

      {/* Priority skill — expanded */}
      {priority && (
        <div className="rounded-xl border border-lav/30 bg-lav/[0.05] p-4">
          <div className="mb-2 flex items-center justify-between gap-2">
            <span className="flex items-center gap-1.5 text-eyebrow text-lav">
              <Target size={13} aria-hidden /> Focus skill
            </span>
            <span className={cn("text-xs font-semibold tabular-nums", BAND_META[priority.band].text)}>
              {priority.score}/{priority.max} · {BAND_META[priority.band].label}
            </span>
          </div>
          <p className="mb-2 text-sm font-semibold text-ink">{priority.label}</p>
          <Meter insight={priority} />
          {priority.diagnostics.length > 0 && (
            <ul className="mt-3 flex flex-col gap-1">
              {priority.diagnostics.slice(0, 3).map((d, i) => (
                <li key={i} className="flex items-start gap-2 text-xs leading-relaxed text-ink-subtle">
                  <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-lav/60" />
                  {d}
                </li>
              ))}
            </ul>
          )}
          <a href={drillsHref} className="mt-3 inline-flex items-center gap-1 text-[11px] font-medium text-lav hover:underline">
            Drill {priority.label.toLowerCase()} <ArrowRight size={11} aria-hidden />
          </a>
        </div>
      )}

      {/* Secondary skills — compact matrix, grouped */}
      <div className="flex flex-col gap-3">
        {Object.entries(groups).map(([group, items]) => (
          <div key={group} className="flex flex-col gap-2">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-ink-faint">
              {SKILL_GROUP_LABELS[group as keyof typeof SKILL_GROUP_LABELS]}
            </p>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {items.map((i) => (
                <div key={i.key} className="flex flex-col gap-1.5 rounded-lg border border-hairline bg-surface-1 px-3 py-2.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-ink">{i.label}</span>
                    <span className={cn("text-[11px] font-semibold tabular-nums", BAND_META[i.band].text)}>
                      {i.score}/{i.max}
                    </span>
                  </div>
                  <Meter insight={i} />
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
