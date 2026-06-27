"use client";
import { MASTERY_STATE_LABEL, MASTERY_STATE_COLOR, MASTERY_STATE_BG } from "@/types/training";
import type { MasteryScore, MasteryState } from "@/types/training";

interface Props {
  mastery: MasteryScore;
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
}

export function SkillMasteryRing({ mastery, size = "md", showLabel = true }: Props) {
  const r = size === "sm" ? 18 : size === "lg" ? 36 : 26;
  const circumference = 2 * Math.PI * r;
  const offset = circumference - (mastery.mastery_score / 100) * circumference;

  const dim = size === "sm" ? 48 : size === "lg" ? 88 : 64;

  const stateColor = MASTERY_STATE_COLOR[mastery.mastery_state as MasteryState] ?? "text-ink-subtle";
  const stateBg = MASTERY_STATE_BG[mastery.mastery_state as MasteryState] ?? "bg-surface-2";
  const stateLabel = MASTERY_STATE_LABEL[mastery.mastery_state as MasteryState] ?? mastery.mastery_state;

  const strokeColor =
    mastery.mastery_state === "mastered"
      ? "var(--lavender-8)"
      : mastery.mastery_state === "proficient"
      ? "#22c55e"
      : mastery.mastery_state === "needs_refresh"
      ? "#f97316"
      : "#94a3b8";

  return (
    <div className="flex flex-col items-center gap-1">
      <svg
        width={dim}
        height={dim}
        viewBox={`0 0 ${dim} ${dim}`}
        aria-label={`${mastery.skill_id} mastery: ${mastery.mastery_score.toFixed(0)}`}
      >
        <circle
          cx={dim / 2}
          cy={dim / 2}
          r={r}
          fill="none"
          stroke="var(--surface-3)"
          strokeWidth={size === "sm" ? 4 : 6}
        />
        <circle
          cx={dim / 2}
          cy={dim / 2}
          r={r}
          fill="none"
          stroke={strokeColor}
          strokeWidth={size === "sm" ? 4 : 6}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          transform={`rotate(-90 ${dim / 2} ${dim / 2})`}
        />
        <text
          x={dim / 2}
          y={dim / 2 + (size === "sm" ? 4 : 5)}
          textAnchor="middle"
          fontSize={size === "sm" ? 10 : size === "lg" ? 16 : 12}
          fontWeight={600}
          fill="currentColor"
          className="text-ink"
        >
          {mastery.mastery_score.toFixed(0)}
        </text>
      </svg>
      {showLabel && (
        <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full ${stateBg} ${stateColor}`}>
          {stateLabel}
        </span>
      )}
    </div>
  );
}
