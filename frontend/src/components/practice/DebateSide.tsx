"use client";

import { Shield, Swords } from "lucide-react";
import { cn } from "@/lib/utils";

export type SideValue = "pro" | "con" | "";

interface DebateSideProps {
  value: SideValue;
  onChange: (side: SideValue) => void;
  disabled?: boolean;
  /** When true, an explicit "not set" option is offered. */
  allowUnset?: boolean;
}

const OPTIONS: { value: "pro" | "con"; label: string; icon: typeof Shield; tone: string; activeTone: string }[] = [
  {
    value: "pro",
    label: "Pro",
    icon: Shield,
    tone: "text-pro",
    activeTone: "border-pro/50 bg-pro/10 text-pro",
  },
  {
    value: "con",
    label: "Con",
    icon: Swords,
    tone: "text-con",
    activeTone: "border-con/50 bg-con/10 text-con",
  },
];

/**
 * Pro/Con segmented selector. Text + icon + semantic tokens (never color alone),
 * keyboard-operable as a radiogroup. Reused by setup and (read-only) report header.
 */
export default function DebateSide({ value, onChange, disabled, allowUnset }: DebateSideProps) {
  return (
    <div
      role="radiogroup"
      aria-label="Side"
      className="inline-flex w-full gap-0.5 rounded-lg border border-hairline bg-surface-2 p-0.5"
    >
      {OPTIONS.map((opt) => {
        const Icon = opt.icon;
        const active = value === opt.value;
        return (
          <button
            key={opt.value}
            type="button"
            role="radio"
            aria-checked={active}
            disabled={disabled}
            onClick={() => onChange(allowUnset && active ? "" : opt.value)}
            className={cn(
              "flex flex-1 items-center justify-center gap-1.5 rounded-md border px-3 py-2 text-sm font-medium transition-colors disabled:opacity-40",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50",
              active
                ? opt.activeTone
                : "border-transparent text-ink-subtle hover:text-ink",
            )}
          >
            <Icon size={14} aria-hidden="true" className={active ? "" : opt.tone} />
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
