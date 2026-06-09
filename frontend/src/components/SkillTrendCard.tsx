"use client";

/**
 * SkillTrendCard — shows a single skill dimension with current score,
 * previous score, delta, and trend label (improving / stable / needs_attention).
 */

import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import type { SkillTrend } from "@/types";

const TREND_CONFIG = {
  improving:        { label: "Improving",       icon: TrendingUp,   color: "text-ok" },
  stable:           { label: "Stable",          icon: Minus,        color: "text-ink-faint" },
  needs_attention:  { label: "Needs attention", icon: TrendingDown, color: "text-danger" },
  no_data:          { label: "No trend yet",    icon: Minus,        color: "text-ink-faint" },
} as const;

interface Props {
  label: string;
  icon: string;
  max: number;
  trend: SkillTrend;
}

export default function SkillTrendCard({ label, icon, max, trend }: Props) {
  const cfg = TREND_CONFIG[trend.trend as keyof typeof TREND_CONFIG] ?? TREND_CONFIG.no_data;
  const TrendIcon = cfg.icon;
  const pct = (trend.current / max) * 100;
  const barColor = pct >= 70 ? "bg-lav" : pct >= 50 ? "bg-warn" : "bg-danger";

  return (
    <div className="flex flex-col gap-2 rounded-lg border border-hairline bg-surface-1 p-3">
      <div className="flex items-center justify-between gap-2">
        <span className="section-stamp">
          <span aria-hidden>{icon}</span>
          {label}
        </span>
        <div className={`flex items-center gap-1 text-[10px] font-medium ${cfg.color}`}>
          <TrendIcon size={10} />
          {cfg.label}
        </div>
      </div>

      <div className="flex items-end gap-2">
        <span
          className="text-lg font-bold tabular-nums text-ink leading-none"
          style={{ fontFamily: "var(--font-jetbrains-mono)" }}
        >
          {trend.current.toFixed(1)}
        </span>
        <span
          className="mb-0.5 text-xs text-ink-faint"
          style={{ fontFamily: "var(--font-jetbrains-mono)" }}
        >/{max}</span>
        {trend.delta !== null && (
          <span className={`mb-0.5 text-[10px] font-semibold ${trend.delta > 0 ? "text-ok" : trend.delta < 0 ? "text-danger" : "text-ink-faint"}`}>
            {trend.delta > 0 ? "+" : ""}{trend.delta.toFixed(1)}
          </span>
        )}
      </div>

      <div className="h-1 overflow-hidden rounded-full bg-hairline">
        <div className={`h-full rounded-full transition-all duration-700 ${barColor}`} style={{ width: `${pct}%` }} />
      </div>

      {trend.previous !== null && (
        <p className="text-[10px] text-ink-faint">
          Previous: {trend.previous.toFixed(1)}/{max}
        </p>
      )}
    </div>
  );
}
