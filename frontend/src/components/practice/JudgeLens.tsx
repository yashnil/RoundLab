"use client";

import { Eye, ListChecks, FlaskConical, GraduationCap, Check, X } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { JUDGE_TYPE_INFO, JUDGE_TYPE_ORDER } from "@/lib/practiceSetup";
import type { JudgeType } from "@/types";
import { cn } from "@/lib/utils";

const JUDGE_ICON: Record<JudgeType, LucideIcon> = {
  lay: Eye,
  flow: ListChecks,
  tech: FlaskConical,
  coach: GraduationCap,
};

export type JudgeValue = JudgeType | "";

interface JudgeLensSelectorProps {
  value: JudgeValue;
  onChange: (judge: JudgeValue) => void;
  disabled?: boolean;
}

/**
 * Judge-lens selector — distinct cards for lay / flow / tech / coach. Each card
 * states what the judge rewards; the live preview (JudgeLensPreview) shows how
 * the report's emphasis changes. Used in practice setup.
 */
export function JudgeLensSelector({ value, onChange, disabled }: JudgeLensSelectorProps) {
  return (
    <div role="radiogroup" aria-label="Judge lens" className="grid grid-cols-2 gap-2">
      {JUDGE_TYPE_ORDER.map((judge) => {
        const info = JUDGE_TYPE_INFO[judge];
        const Icon = JUDGE_ICON[judge];
        const active = value === judge;
        return (
          <button
            key={judge}
            type="button"
            role="radio"
            aria-checked={active}
            disabled={disabled}
            onClick={() => onChange(active ? "" : judge)}
            className={cn(
              "flex flex-col gap-1.5 rounded-lg border p-3 text-left transition-colors disabled:opacity-40",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50",
              active
                ? "border-lav/50 bg-lav/[0.07]"
                : "border-hairline bg-surface-1 hover:border-hairline-strong",
            )}
          >
            <span className="flex items-center gap-1.5">
              <Icon size={14} className={active ? "text-lav" : "text-ink-faint"} aria-hidden="true" />
              <span className="text-sm font-semibold text-ink">{info.label}</span>
            </span>
            <span className="text-xs leading-relaxed text-ink-subtle">{info.rewards[0]}</span>
          </button>
        );
      })}
    </div>
  );
}

/**
 * Compact "this report will emphasize…" preview for the selected judge lens.
 */
export function JudgeLensPreview({ judge }: { judge: JudgeValue }) {
  if (!judge) {
    return (
      <p className="text-xs leading-relaxed text-ink-faint">
        Pick a judge lens to preview how RoundLab will weight your feedback.
      </p>
    );
  }
  const info = JUDGE_TYPE_INFO[judge];
  return (
    <div className="flex flex-col gap-2">
      <p className="text-eyebrow text-lav">This report will emphasize</p>
      <ul className="flex flex-col gap-1">
        {info.emphasis.map((line) => (
          <li key={line} className="flex items-center gap-1.5 text-xs text-ink">
            <Check size={11} className="shrink-0 text-ok" aria-hidden="true" />
            {line}
          </li>
        ))}
      </ul>
      <div className="flex flex-wrap gap-1.5 border-t border-hairline pt-2">
        {info.punishes.slice(0, 2).map((line) => (
          <span key={line} className="inline-flex items-center gap-1 text-[10px] text-ink-faint">
            <X size={9} className="shrink-0 text-danger" aria-hidden="true" />
            {line}
          </span>
        ))}
      </div>
    </div>
  );
}
