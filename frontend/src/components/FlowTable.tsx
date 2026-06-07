"use client";

import { useState, useMemo } from "react";
import { motion, AnimatePresence } from "motion/react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { T } from "@/lib/motion";
import { ArgumentChainCards, ArgumentChainStrip } from "@/components/ArgumentChain";
import type { ArgumentItem, ArgumentType } from "@/types";
import type { JudgeViewMode } from "@/components/JudgeModeSelector";

// ── Type config ────────────────────────────────────────────────────────────────

const TYPE_CONFIG: Record<
  ArgumentType,
  { badge: "green" | "blue" | "violet" | "orange" | "default"; label: string; accent: string }
> = {
  offense:  { badge: "green",   label: "Offense",  accent: "border-l-ok"              },
  defense:  { badge: "blue",    label: "Defense",  accent: "border-l-blue"            },
  weighing: { badge: "violet",  label: "Weighing", accent: "border-l-violet"          },
  response: { badge: "orange",  label: "Response", accent: "border-l-orange"          },
  unclear:  { badge: "default", label: "Unclear",  accent: "border-l-hairline-strong" },
};

// Derive a compact issue status from the issues array
function issueStatus(issues: string[]): {
  label: string;
  variant: "green" | "amber" | "red";
  severity: number;
} {
  if (issues.length === 0) return { label: "Clean", variant: "green", severity: 0 };
  const text = issues.join(" ").toLowerCase();
  if (text.includes("warrant"))  return { label: "No warrant",    variant: "red",   severity: 3 };
  if (text.includes("dropped"))  return { label: "Dropped",       variant: "red",   severity: 3 };
  if (text.includes("evidence") || text.includes("unsupported"))
                                 return { label: "Weak evidence",  variant: "amber", severity: 2 };
  if (text.includes("impact"))   return { label: "Unclear impact", variant: "amber", severity: 2 };
  if (text.includes("weigh"))    return { label: "No weighing",    variant: "amber", severity: 2 };
  return { label: `${issues.length} issue${issues.length > 1 ? "s" : ""}`, variant: "amber", severity: 1 };
}


function RowDetail({ arg, judgeMode }: { arg: ArgumentItem; judgeMode: JudgeViewMode }) {
  const chainData = {
    claim:    arg.claim,
    warrant:  arg.warrant,
    evidence: arg.evidence,
    impact:   arg.impact,
    issues:   arg.issues,
  };

  return (
    <motion.div
      initial={{ height: 0, opacity: 0 }}
      animate={{ height: "auto", opacity: 1 }}
      exit={{ height: 0, opacity: 0 }}
      transition={{ duration: 0.22 }}
      className="overflow-hidden"
    >
      <div className="flex flex-col gap-4 border-t border-hairline bg-surface-2 px-5 py-4">

        {/* Argument chain visualization */}
        <ArgumentChainCards data={chainData} judgeMode={judgeMode} />

        {/* Issues */}
        {arg.issues.length > 0 && (
          <div className="flex flex-wrap items-center gap-2 border-t border-hairline pt-2">
            <span className="text-eyebrow text-ink-faint">Issues:</span>
            {arg.issues.map((issue, i) => (
              <span key={i} className="rounded-full bg-amber/10 px-2 py-0.5 text-[10px] font-medium text-amber">
                {issue}
              </span>
            ))}
          </div>
        )}

        {/* Judge-mode hint */}
        {judgeMode !== "coach" && (
          <p className="border-t border-hairline pt-2 text-[10px] italic text-ink-faint">
            {judgeMode === "lay"  && "Lay judge cares most about: clear impact on real people."}
            {judgeMode === "flow" && "Flow judge cares most about: extended warrants and weighing."}
            {judgeMode === "tech" && "Tech judge cares most about: conceded offense and evidence quality."}
          </p>
        )}
      </div>
    </motion.div>
  );
}

// ── Filter tabs ────────────────────────────────────────────────────────────────

type FilterMode = "all" | "needs_work" | "clean";

// ── Main FlowTable ─────────────────────────────────────────────────────────────

interface FlowTableProps {
  args: ArgumentItem[];
  judgeMode?: JudgeViewMode;
}

export default function FlowTable({ args, judgeMode = "coach" }: FlowTableProps) {
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);
  const [filter, setFilter] = useState<FilterMode>("all");
  const [expandAll, setExpandAll] = useState(false);

  // Counts for filter tabs
  const needsWorkCount = useMemo(() => args.filter((a) => a.issues.length > 0).length, [args]);
  const cleanCount     = useMemo(() => args.filter((a) => a.issues.length === 0).length,  [args]);

  // Filter + sort (most issues first)
  const filtered = useMemo(() => {
    const base =
      filter === "needs_work" ? args.filter((a) => a.issues.length > 0) :
      filter === "clean"      ? args.filter((a) => a.issues.length === 0) :
      args;
    return [...base].sort((a, b) => b.issues.length - a.issues.length);
  }, [args, filter]);

  // Judge-mode header emphasis text
  const judgeHint: Record<JudgeViewMode, string> = {
    lay:   "Emphasis: clarity and impact",
    flow:  "Emphasis: warrants, extensions, drops",
    tech:  "Emphasis: evidence quality, conceded offense",
    coach: "Click any row to see claim → warrant → evidence → impact",
  };

  if (args.length === 0) {
    return <p className="py-6 text-center text-sm text-ink-faint">No arguments extracted.</p>;
  }

  return (
    <div className="flex flex-col gap-2">
      {/* Filter bar + issue counts */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-1 rounded-lg border border-hairline bg-surface-2 p-0.5">
          {(
            [
              { key: "all" as FilterMode,       label: `All (${args.length})` },
              { key: "needs_work" as FilterMode, label: `Needs Work (${needsWorkCount})` },
              { key: "clean" as FilterMode,      label: `Clean (${cleanCount})` },
            ]
          ).map(({ key, label }) => (
            <button
              key={key}
              type="button"
              onClick={() => { setFilter(key); setExpandedIdx(null); }}
              className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
                filter === key ? "bg-lav text-white" : "text-ink-subtle hover:text-ink"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        <button
          type="button"
          onClick={() => setExpandAll((v) => !v)}
          className="flex items-center gap-1 text-xs text-ink-subtle transition-colors hover:text-ink"
        >
          {expandAll ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
          {expandAll ? "Collapse all" : "Expand all"}
        </button>
      </div>

      {/* Judge hint */}
      <p className="text-xs text-ink-faint">{judgeHint[judgeMode]}</p>

      {/* Table */}
      <div className="overflow-x-auto rounded-xl border border-hairline">
        {/* Header */}
        <div className="flex items-center gap-0 border-b border-hairline bg-surface-2 px-4 py-2">
          <div className="w-6 shrink-0 text-eyebrow text-ink-faint">#</div>
          <div className="w-20 shrink-0 text-eyebrow text-ink-faint">Type</div>
          <div className="min-w-0 flex-1 text-eyebrow text-ink-faint">Argument</div>
          <div className="hidden w-24 shrink-0 text-right text-eyebrow text-ink-faint sm:block">Status</div>
          <div className="w-7 shrink-0" />
        </div>

        {/* Rows */}
        <div className="divide-y divide-hairline">
          {filtered.length === 0 ? (
            <p className="px-4 py-6 text-center text-sm text-ink-faint">
              {filter === "needs_work" ? "No issues found — all arguments are clean." : "No arguments match this filter."}
            </p>
          ) : (
            filtered.map((arg, i) => {
              const config = TYPE_CONFIG[arg.argument_type] ?? TYPE_CONFIG.unclear;
              const status = issueStatus(arg.issues);
              const isOpen = expandAll || expandedIdx === i;

              return (
                <div key={i} className={`border-l-2 ${config.accent} transition-colors`}>
                  <button
                    type="button"
                    onClick={() => !expandAll && setExpandedIdx(isOpen ? null : i)}
                    className="flex w-full items-center gap-4 px-4 py-3 text-left transition-colors hover:bg-surface-2"
                    aria-expanded={isOpen}
                  >
                    <div className="w-6 shrink-0 font-mono text-xs text-ink-faint">{i + 1}</div>
                    <div className="w-20 shrink-0">
                      <Badge variant={config.badge} className="px-1.5 py-0 text-[10px]">
                        {config.label}
                      </Badge>
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-ink">{arg.label}</p>
                      <div className="mt-0.5">
                        <ArgumentChainStrip data={{
                          claim: arg.claim, warrant: arg.warrant,
                          evidence: arg.evidence, impact: arg.impact, issues: arg.issues,
                        }} judgeMode={judgeMode} />
                      </div>
                    </div>
                    <div className="hidden w-24 shrink-0 text-right sm:block">
                      <Badge variant={status.variant} className="px-1.5 py-0 text-[10px]">
                        {status.label}
                      </Badge>
                    </div>
                    <motion.div
                      className="flex w-7 shrink-0 justify-center"
                      animate={{ rotate: isOpen ? 180 : 0 }}
                      transition={T.fast}
                    >
                      <ChevronDown size={13} className="text-ink-faint" />
                    </motion.div>
                  </button>

                  <AnimatePresence>
                    {isOpen && (
                      <RowDetail key="detail" arg={arg} judgeMode={judgeMode} />
                    )}
                  </AnimatePresence>
                </div>
              );
            })
          )}
        </div>

        {/* Legend */}
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-hairline bg-surface-2 px-4 py-2">
          <span className="text-eyebrow text-ink-faint">Types:</span>
          {(["Offense", "Defense", "Weighing", "Response"] as const).map((t) => (
            <span key={t} className="text-xs text-ink-faint">{t}</span>
          ))}
        </div>
      </div>
    </div>
  );
}
