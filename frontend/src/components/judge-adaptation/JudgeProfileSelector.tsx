"use client";

import { JUDGE_TYPE_DESCRIPTIONS, JUDGE_TYPE_LABELS, JudgeProfile, JudgeType } from "@/types/judgeAdaptation";

interface Props {
  profiles: JudgeProfile[];
  selected: JudgeType | null;
  onSelect: (type: JudgeType) => void;
  className?: string;
}

const JUDGE_ICONS: Record<JudgeType, string> = {
  lay: "🧑‍🤝‍🧑",
  parent: "👨‍👩‍👧",
  flow: "📋",
  technical: "⚖️",
  coach: "🎯",
  custom: "✏️",
};

export function JudgeProfileSelector({ profiles, selected, onSelect, className }: Props) {
  return (
    <div className={className}>
      <p className="text-xs font-medium text-[var(--ink-subtle)] uppercase tracking-wide mb-3">
        Select Judge Type
      </p>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
        {profiles.map((profile) => {
          const isSelected = selected === profile.judge_type;
          return (
            <button
              key={profile.judge_type}
              onClick={() => onSelect(profile.judge_type)}
              aria-pressed={isSelected}
              className={[
                "flex flex-col gap-1 rounded-lg border px-3 py-2 text-left transition-colors",
                isSelected
                  ? "border-[var(--lavender-8)] bg-[var(--lavender-8)]/10 text-[var(--lavender-8)]"
                  : "border-[var(--surface-3)] bg-[var(--surface-2)] text-[var(--ink-primary)] hover:border-[var(--lavender-8)]/50",
              ].join(" ")}
            >
              <span className="text-base">{JUDGE_ICONS[profile.judge_type]}</span>
              <span className="text-sm font-medium leading-tight">
                {JUDGE_TYPE_LABELS[profile.judge_type]}
              </span>
              {isSelected && (
                <span className="text-[10px] text-[var(--lavender-8)] font-medium">Selected</span>
              )}
            </button>
          );
        })}
      </div>
      {selected && (
        <p className="mt-3 text-xs text-[var(--ink-subtle)] leading-relaxed">
          {JUDGE_TYPE_DESCRIPTIONS[selected]}
        </p>
      )}
    </div>
  );
}
