"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, Copy, Plus, Trash2 } from "lucide-react";
import type { ArgumentItem, ArgumentType } from "@/types";
import {
  addArgument,
  deleteArgument,
  duplicateArgument,
  updateArgument,
} from "@/lib/flowEditHelpers";

// ── Type chip config ──────────────────────────────────────────────────────────

const TYPE_META: Record<ArgumentType, { label: string; chip: string }> = {
  offense:  { label: "Offense",  chip: "text-lav    border border-lav/20    bg-lav/10"    },
  defense:  { label: "Defense",  chip: "text-ok     border border-ok/20     bg-ok/10"     },
  weighing: { label: "Weighing", chip: "text-warn   border border-warn/20   bg-warn/10"   },
  response: { label: "Response", chip: "text-ink-subtle border border-hairline bg-surface-3" },
  unclear:  { label: "Unclear",  chip: "text-ink-faint  border border-hairline bg-surface-2" },
};

const ARGUMENT_TYPE_OPTIONS = (
  Object.entries(TYPE_META) as [ArgumentType, { label: string }][]
).map(([value, { label }]) => ({ value, label }));

// ── Shared input style ────────────────────────────────────────────────────────

const FIELD =
  "w-full text-sm text-ink bg-surface-2 border border-hairline rounded-md " +
  "px-3 py-2 placeholder:text-ink-faint outline-none transition-colors " +
  "focus-visible:border-lav/50 focus-visible:ring-2 focus-visible:ring-lav/20";

// ── Helpers ───────────────────────────────────────────────────────────────────

function issuesToText(issues: string[]): string {
  return (issues ?? []).join("\n");
}

function textToIssues(text: string): string[] {
  return text
    .split("\n")
    .map((s) => s.trim())
    .filter(Boolean);
}

// ── Sub-components ────────────────────────────────────────────────────────────

function FieldArea({
  label,
  hint,
  value,
  placeholder,
  onChange,
  rows = 3,
  mono = false,
}: {
  label: string;
  hint?: string;
  value: string;
  placeholder: string;
  onChange: (v: string) => void;
  rows?: number;
  mono?: boolean;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-baseline gap-2">
        <span className="text-xs font-semibold text-ink-subtle">{label}</span>
        {hint && <span className="text-[11px] text-ink-faint">{hint}</span>}
      </div>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        rows={rows}
        className={`${FIELD} resize-y${mono ? " font-mono text-xs" : ""}`}
      />
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

interface FlowEditPanelProps {
  initialArgs: ArgumentItem[];
  onSave: (args: ArgumentItem[], notes?: string) => void;
  onCancel: () => void;
  saving?: boolean;
  saveError?: string | null;
}

export default function FlowEditPanel({
  initialArgs,
  onSave,
  onCancel,
  saving = false,
  saveError = null,
}: FlowEditPanelProps) {
  const [args, setArgs] = useState<ArgumentItem[]>(initialArgs);
  const [expandedIndex, setExpandedIndex] = useState<number | null>(
    initialArgs.length === 1 ? 0 : null,
  );
  const [correctionNotes, setCorrectionNotes] = useState("");

  function toggleExpand(index: number) {
    setExpandedIndex((prev) => (prev === index ? null : index));
  }

  function handleUpdate(index: number, changes: Partial<ArgumentItem>) {
    setArgs((prev) => updateArgument(prev, index, changes));
  }

  function handleAdd() {
    setArgs((prev) => {
      const next = addArgument(prev);
      setExpandedIndex(next.length - 1);
      return next;
    });
  }

  function handleDelete(index: number) {
    if (args.length <= 1) return;
    setArgs((prev) => {
      const next = deleteArgument(prev, index);
      if (expandedIndex !== null) {
        if (expandedIndex === index) setExpandedIndex(null);
        else if (expandedIndex > index) setExpandedIndex(expandedIndex - 1);
      }
      return next;
    });
  }

  function handleDuplicate(index: number) {
    setArgs((prev) => {
      const next = duplicateArgument(prev, index);
      setExpandedIndex(index + 1);
      return next;
    });
  }

  function handleSave() {
    onSave(args, correctionNotes.trim() || undefined);
  }

  return (
    <div className="flex flex-col rounded-xl border border-hairline-strong bg-surface-1 overflow-hidden">

      {/* ── Top bar ──────────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between gap-3 border-b border-hairline bg-surface-2 px-4 py-3">
        <div className="flex items-center gap-2.5 min-w-0">
          <p className="text-sm font-semibold text-ink">Editing flow</p>
          <span className="rep-badge shrink-0">
            {args.length} arg{args.length !== 1 ? "s" : ""}
          </span>
          <span className="section-stamp hidden sm:inline-flex">AI draft correction</span>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button
            type="button"
            onClick={onCancel}
            disabled={saving}
            className="rounded-md border border-hairline px-2.5 py-1 text-xs font-medium text-ink-subtle hover:text-ink hover:border-hairline-strong transition-colors disabled:opacity-40"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={saving}
            className="rounded-md bg-lav px-3 py-1 text-xs font-semibold text-white hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {saving ? "Saving…" : "Save corrections"}
          </button>
        </div>
      </div>

      {/* ── Helper note ───────────────────────────────────────────────────────── */}
      <div className="border-b border-hairline px-4 py-2.5">
        <p className="text-xs text-ink-faint leading-relaxed">
          Edit only if Dissio missed or mislabeled something. Corrections will be used when you regenerate coaching.
        </p>
      </div>

      {/* ── Argument rows ─────────────────────────────────────────────────────── */}
      <div className="flex flex-col divide-y divide-hairline">
        {args.map((arg, index) => {
          const isExpanded = expandedIndex === index;
          const meta = TYPE_META[arg.argument_type] ?? TYPE_META.unclear;
          const issueCount = arg.issues?.length ?? 0;
          const claimPreview = arg.claim
            ? arg.claim.length > 90
              ? arg.claim.slice(0, 90) + "…"
              : arg.claim
            : null;

          return (
            <div key={index} className={isExpanded ? "bg-surface-2" : undefined}>

              {/* Collapsed header row */}
              <button
                type="button"
                aria-expanded={isExpanded}
                onClick={() => toggleExpand(index)}
                className={[
                  "w-full flex items-start gap-3 px-4 py-3 text-left transition-colors",
                  !isExpanded && "hover:bg-surface-2/60",
                ].filter(Boolean).join(" ")}
              >
                {/* Step index */}
                <span className="flow-step mt-0.5 shrink-0">
                  {String(index + 1).padStart(2, "0")}
                </span>

                {/* Argument info */}
                <div className="flex flex-col gap-1 flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-medium text-ink leading-snug">
                      {arg.label || (
                        <span className="italic text-ink-faint">Untitled argument</span>
                      )}
                    </span>
                    <span
                      className={`inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-semibold leading-none ${meta.chip}`}
                    >
                      {meta.label}
                    </span>
                    {issueCount > 0 ? (
                      <span className="inline-flex items-center rounded border border-warn/20 bg-warn/10 px-1.5 py-0.5 text-[10px] font-medium text-warn leading-none">
                        {issueCount} issue{issueCount !== 1 ? "s" : ""}
                      </span>
                    ) : (
                      <span className="inline-flex items-center rounded border border-ok/20 bg-ok/10 px-1.5 py-0.5 text-[10px] font-medium text-ok leading-none">
                        Clean
                      </span>
                    )}
                  </div>
                  {claimPreview ? (
                    <p className="text-xs text-ink-faint leading-relaxed truncate">
                      {claimPreview}
                    </p>
                  ) : (
                    <p className="text-xs italic text-ink-faint">No claim written yet</p>
                  )}
                </div>

                {/* Chevron */}
                <span className="mt-0.5 shrink-0 text-ink-faint" aria-hidden="true">
                  {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                </span>
              </button>

              {/* Expanded edit form */}
              {isExpanded && (
                <div className="border-t border-hairline px-4 py-4 flex flex-col gap-4">

                  {/* Label + Type */}
                  <div className="grid grid-cols-2 gap-3">
                    <div className="flex flex-col gap-1.5">
                      <span className="text-xs font-semibold text-ink-subtle">Label / Title</span>
                      <input
                        type="text"
                        value={arg.label}
                        onChange={(e) => handleUpdate(index, { label: e.target.value })}
                        placeholder="e.g. Contention 1 — Economy"
                        className={FIELD}
                      />
                    </div>
                    <div className="flex flex-col gap-1.5">
                      <span className="text-xs font-semibold text-ink-subtle">Argument Type</span>
                      <select
                        value={arg.argument_type}
                        onChange={(e) =>
                          handleUpdate(index, { argument_type: e.target.value as ArgumentType })
                        }
                        className={`${FIELD} cursor-pointer`}
                      >
                        {ARGUMENT_TYPE_OPTIONS.map((t) => (
                          <option key={t.value} value={t.value}>
                            {t.label}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  {/* Claim + Warrant */}
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                    <FieldArea
                      label="Claim"
                      hint="What you're asserting"
                      value={arg.claim}
                      placeholder="e.g. Economic sanctions harm developing nations"
                      onChange={(v) => handleUpdate(index, { claim: v })}
                    />
                    <FieldArea
                      label="Warrant"
                      hint="Why the claim is true"
                      value={arg.warrant}
                      placeholder="e.g. Sanctions restrict essential imports and GDP growth"
                      onChange={(v) => handleUpdate(index, { warrant: v })}
                    />
                  </div>

                  {/* Evidence + Impact */}
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                    <FieldArea
                      label="Evidence"
                      hint="optional — source, card, or data"
                      value={arg.evidence ?? ""}
                      placeholder="e.g. Smith 2023 — 'Nations under sanctions see…'"
                      onChange={(v) => handleUpdate(index, { evidence: v || null })}
                    />
                    <FieldArea
                      label="Impact"
                      hint="Why it matters in this round"
                      value={arg.impact}
                      placeholder="e.g. Food insecurity and political destabilization"
                      onChange={(v) => handleUpdate(index, { impact: v })}
                    />
                  </div>

                  {/* AI-flagged issues */}
                  <FieldArea
                    label="AI-flagged issues"
                    hint="one per line — clear to remove"
                    value={issuesToText(arg.issues ?? [])}
                    placeholder={"missing_warrant\nweak_evidence"}
                    onChange={(v) => handleUpdate(index, { issues: textToIssues(v) })}
                    rows={2}
                    mono
                  />

                  {/* Row actions */}
                  <div className="flex items-center gap-2 pt-1 border-t border-hairline">
                    <button
                      type="button"
                      onClick={() => handleDuplicate(index)}
                      className="flex items-center gap-1.5 rounded-md border border-hairline px-2.5 py-1.5 text-xs font-medium text-ink-subtle hover:text-ink hover:border-hairline-strong transition-colors"
                    >
                      <Copy size={11} aria-hidden="true" />
                      Duplicate
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDelete(index)}
                      disabled={args.length <= 1}
                      aria-label={`Delete argument ${index + 1}`}
                      className="flex items-center gap-1.5 rounded-md border border-danger/20 px-2.5 py-1.5 text-xs font-medium text-danger/80 hover:text-danger hover:border-danger/40 hover:bg-danger/5 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                    >
                      <Trash2 size={11} aria-hidden="true" />
                      Delete argument
                    </button>
                    {args.length <= 1 && (
                      <span className="text-[11px] text-ink-faint ml-auto">
                        Need at least 1 argument
                      </span>
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* ── Add argument ──────────────────────────────────────────────────────── */}
      <div className="border-t border-hairline p-3">
        <button
          type="button"
          onClick={handleAdd}
          className="file-tray w-full flex items-center justify-center gap-2 py-2.5 text-sm font-medium text-ink-subtle hover:text-ink transition-colors"
        >
          <Plus size={14} aria-hidden="true" />
          Add argument
        </button>
      </div>

      {/* ── Correction notes ──────────────────────────────────────────────────── */}
      <div className="border-t border-hairline px-4 py-4 flex flex-col gap-2">
        <div className="flex flex-col gap-0.5">
          <p className="section-stamp">Correction notes</p>
          <p className="text-xs text-ink-faint mt-1">
            Optional: explain what you changed before regenerating coaching.
          </p>
        </div>
        <textarea
          value={correctionNotes}
          onChange={(e) => setCorrectionNotes(e.target.value)}
          placeholder="e.g. AI missed the weighing argument; added it manually. C2 claim was mislabeled."
          rows={2}
          className={`${FIELD} resize-none`}
        />
      </div>

      {/* ── Footer save bar ───────────────────────────────────────────────────── */}
      <div className="border-t border-hairline bg-surface-2 px-4 py-4 flex flex-col gap-3">
        {saveError && (
          <div className="rounded-lg border border-danger/20 bg-danger/5 px-3 py-2 text-xs text-danger">
            {saveError}
          </div>
        )}
        <p className="text-xs text-ink-faint">
          Save these corrections before regenerating coaching.
        </p>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleSave}
            disabled={saving}
            className="flex-1 rounded-lg bg-lav py-2 text-sm font-semibold text-white hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? "Saving corrections…" : "Save corrections"}
          </button>
          <button
            type="button"
            onClick={onCancel}
            disabled={saving}
            className="rounded-lg border border-hairline px-4 py-2 text-sm font-medium text-ink-subtle hover:text-ink hover:border-hairline-strong transition-colors disabled:opacity-40"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
