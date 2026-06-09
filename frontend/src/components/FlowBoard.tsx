"use client";

/**
 * FlowBoard — horizontal-scroll, fixed-column flow view.
 * Each argument is a 208px column side-by-side, like a real debate flow sheet.
 * Judge lens (judgeMode) highlights the relevant CWEIM field without resizing cards.
 */

import { useState } from "react";
import type { ArgumentItem } from "@/types";
import type { JudgeViewMode } from "@/components/JudgeModeSelector";
import { deriveArgumentDisplayLabel } from "@/lib/debateHelpers";

// Per-lens field emphasis — which CWEIM fields are visually accented
const LENS_EMPHASIS: Record<JudgeViewMode, string[]> = {
  coach:   [],
  lay:     ["impact"],
  flow:    ["warrant"],
  tech:    ["warrant", "evidence"],
};

// Argument type badge colors
const TYPE_BADGE: Record<string, string> = {
  offense:  "border-ok/25 bg-ok/5 text-ok",
  defense:  "border-lav/25 bg-lav/5 text-lav",
  weighing: "border-warn/25 bg-warn/5 text-warn",
  response: "border-hairline-strong bg-surface-2 text-ink-subtle",
  unclear:  "border-hairline bg-surface-2 text-ink-faint",
};

// ── Field row ─────────────────────────────────────────────────────────────────

function Field({
  label,
  value,
  isEmphasized,
}: {
  label: string;
  value: string | null | undefined;
  isEmphasized: boolean;
}) {
  return (
    <div
      className={`min-h-[60px] px-3 py-2 transition-colors ${isEmphasized ? "bg-lav/5" : ""}`}
      style={isEmphasized ? { boxShadow: "inset 2px 0 0 oklch(0.510 0.156 278 / 0.35)" } : undefined}
    >
      <p
        className={`mb-1 font-mono text-[8px] font-semibold uppercase tracking-widest leading-none ${
          isEmphasized ? "text-lav" : "text-ink-faint"
        }`}
      >
        {label}
      </p>
      {value ? (
        <p className="text-[10px] leading-[1.5] text-ink-subtle">{value}</p>
      ) : (
        <p className="text-[10px] italic text-ink-faint opacity-50">—</p>
      )}
    </div>
  );
}

// ── Single argument column ────────────────────────────────────────────────────

function FlowColumn({
  arg,
  index,
  allArgs,
  judgeMode,
}: {
  arg: ArgumentItem;
  index: number;
  allArgs: ArgumentItem[];
  judgeMode: JudgeViewMode;
}) {
  const [expanded, setExpanded] = useState(false);
  const emphasis = LENS_EMPHASIS[judgeMode];
  const { prefix, ordinal, title } = deriveArgumentDisplayLabel(arg, index, allArgs);

  return (
    <div className="w-52 shrink-0 flex flex-col overflow-hidden rounded-[3px] border border-hairline bg-surface-1">
      {/* Column header */}
      <div className="border-b border-hairline bg-surface-2 px-3 pb-2.5 pt-2">
        <div className="mb-1.5 flex items-center gap-1.5">
          <span
            className={`rounded border px-1.5 py-0.5 text-[8px] font-semibold uppercase tracking-wider ${
              TYPE_BADGE[arg.argument_type] ?? TYPE_BADGE.unclear
            }`}
          >
            {arg.argument_type}
          </span>
          {arg.confidence !== null && arg.confidence !== undefined && (
            <span className="ml-auto font-mono text-[8px] tabular-nums text-ink-faint">
              {arg.confidence}%
            </span>
          )}
        </div>
        <p className="font-mono text-[8px] font-semibold uppercase tracking-widest text-ink-faint">
          {prefix} · Arg {ordinal}
        </p>
        <p className="mt-0.5 line-clamp-2 text-[11px] font-semibold leading-snug text-ink">{title}</p>
      </div>

      {/* CWEIM fields */}
      <div className="flex flex-col flex-1 divide-y divide-hairline">
        <Field label="Claim"    value={arg.claim}             isEmphasized={emphasis.includes("claim")} />
        <Field label="Warrant"  value={arg.warrant}           isEmphasized={emphasis.includes("warrant")} />
        <Field label="Evidence" value={arg.evidence ?? null}  isEmphasized={emphasis.includes("evidence")} />
        <Field label="Impact"   value={arg.impact}            isEmphasized={emphasis.includes("impact")} />
      </div>

      {/* Issues footer */}
      {arg.issues.length > 0 && (
        <div className="border-t border-warn/15 bg-warn/5 px-3 py-2">
          <p className="mb-1 font-mono text-[8px] font-semibold uppercase tracking-wider text-warn">
            Issues
          </p>
          {arg.issues.slice(0, expanded ? undefined : 1).map((issue, i) => (
            <div key={i} className="flex items-start gap-1.5">
              <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-warn" />
              <p className="text-[10px] leading-relaxed text-warn/80">{issue}</p>
            </div>
          ))}
          {arg.issues.length > 1 && (
            <button
              type="button"
              onClick={() => setExpanded((v) => !v)}
              className="mt-1 text-[9px] text-ink-faint underline underline-offset-2 hover:text-ink-subtle"
            >
              {expanded ? "less" : `+${arg.issues.length - 1} more`}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

// ── Main export ───────────────────────────────────────────────────────────────

interface FlowBoardProps {
  args: ArgumentItem[];
  judgeMode: JudgeViewMode;
  className?: string;
}

export default function FlowBoard({ args, judgeMode, className = "" }: FlowBoardProps) {
  if (args.length === 0) return null;
  return (
    <div className={`overflow-x-auto rounded-lg border border-hairline flow-sheet-bg ${className}`}>
      <div className="flex min-w-max gap-2 p-3">
        {args.map((arg, i) => (
          <FlowColumn key={arg.id ?? i} arg={arg} index={i} allArgs={args} judgeMode={judgeMode} />
        ))}
      </div>
    </div>
  );
}
