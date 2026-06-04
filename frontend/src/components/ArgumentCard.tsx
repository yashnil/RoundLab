"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { ChevronDown } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { T } from "@/lib/motion";
import type { ArgumentItem, ArgumentType } from "@/types";

const TYPE_CONFIG: Record<
  ArgumentType,
  { badge: "green" | "blue" | "violet" | "orange" | "default"; border: string; label: string }
> = {
  offense:  { badge: "green",   border: "border-l-ok",              label: "Offense"  },
  defense:  { badge: "blue",    border: "border-l-blue",            label: "Defense"  },
  weighing: { badge: "violet",  border: "border-l-violet",          label: "Weighing" },
  response: { badge: "orange",  border: "border-l-orange",          label: "Response" },
  unclear:  { badge: "default", border: "border-l-hairline-strong", label: "Unclear"  },
};

function confBadge(c: number | null) {
  if (c === null) return null;
  if (c >= 0.8) return { label: "Strong", variant: "green"  as const };
  if (c >= 0.5) return { label: "Developing",  variant: "amber"  as const };
  return            { label: "Needs Work",  variant: "red"    as const };
}

function Field({ label, text, italic, highlight }: { label: string; text: string; italic?: boolean; highlight?: boolean }) {
  return (
    <div className="flex flex-col gap-1">
      <span className={`text-eyebrow ${highlight ? "text-lav" : "text-ink-faint"}`}>{label}</span>
      <p className={`text-sm leading-relaxed ${highlight ? "font-medium text-ink" : "text-ink-muted"}${italic ? " italic" : ""}`}>{text}</p>
    </div>
  );
}

function getCoachNote(issues: string[]): string | null {
  if (issues.length === 0) return null;

  // Check for specific issue patterns and provide student-friendly coaching
  const hasWarrantIssue = issues.some(i => i.toLowerCase().includes("warrant"));
  const hasEvidenceIssue = issues.some(i => i.toLowerCase().includes("evidence") || i.toLowerCase().includes("unsupported"));
  const hasImpactIssue = issues.some(i => i.toLowerCase().includes("impact"));
  const hasWeighingIssue = issues.some(i => i.toLowerCase().includes("weigh"));

  if (hasWarrantIssue) {
    return "Explain why your claim is true";
  }
  if (hasEvidenceIssue) {
    return "Connect your evidence to the claim";
  }
  if (hasImpactIssue) {
    return "Explain why the harm matters";
  }
  if (hasWeighingIssue) {
    return "Compare your impact against theirs";
  }

  // Generic fallback
  return "Strengthen the argument structure";
}

function getStudentFriendlyFix(issues: string[]): string | null {
  if (issues.length === 0) return null;

  const hasWarrantIssue = issues.some(i => i.toLowerCase().includes("warrant"));
  const hasEvidenceIssue = issues.some(i => i.toLowerCase().includes("evidence") || i.toLowerCase().includes("unsupported"));
  const hasImpactIssue = issues.some(i => i.toLowerCase().includes("impact"));
  const hasWeighingIssue = issues.some(i => i.toLowerCase().includes("weigh"));

  if (hasWarrantIssue) {
    return "Add a 'because' sentence after your claim explaining the logical link.";
  }
  if (hasEvidenceIssue) {
    return "After citing your source, explain: 'This proves [claim] because...'";
  }
  if (hasImpactIssue) {
    return "Describe the real-world consequence: who is affected, how severe, how soon?";
  }
  if (hasWeighingIssue) {
    return "Add: 'This outweighs [their impact] because [magnitude/probability/timeframe].'";
  }

  return "Strengthen each part: claim → warrant → evidence → impact.";
}

export default function ArgumentCard({
  arg,
  index,
  viewMode = "coach"
}: {
  arg: ArgumentItem;
  index: number;
  viewMode?: "coach" | "technical";
}) {
  const [expanded, setExpanded] = useState(false);
  const config = TYPE_CONFIG[arg.argument_type] ?? TYPE_CONFIG.unclear;
  const conf   = confBadge(arg.confidence);
  const coachNote = getCoachNote(arg.issues);
  const fixSuggestion = getStudentFriendlyFix(arg.issues);
  const hasIssues = arg.issues.length > 0;

  // Coach View: Compact, summary-first
  if (viewMode === "coach") {
    return (
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: index * 0.06, ...T.base }}
        className={`flex flex-col gap-3 rounded-lg border border-l-4 border-hairline bg-surface-2 p-4 ${config.border}`}
      >
        {/* Compact Header */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <Badge variant={config.badge} className="capitalize shrink-0">{config.label}</Badge>
              {conf && <Badge variant={conf.variant} className="shrink-0">{conf.label}</Badge>}
            </div>
            <p className="text-sm font-semibold leading-snug text-ink">{arg.label}</p>
          </div>
        </div>

        {/* Main Issue/Note (always visible in coach view) */}
        {hasIssues ? (
          <div className="flex flex-col gap-2 rounded-md border border-amber/20 bg-amber/5 px-3 py-2">
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-semibold text-amber">⚠ {coachNote}</span>
            </div>
            {fixSuggestion && (
              <p className="text-xs leading-relaxed text-ink-muted">{fixSuggestion}</p>
            )}
          </div>
        ) : (
          <div className="flex items-center gap-2 rounded-md border border-ok/20 bg-ok/5 px-3 py-2">
            <span className="text-xs font-semibold text-ok">✓ Argument structure is solid</span>
          </div>
        )}

        {/* Expandable Details */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center justify-between gap-2 rounded-md border border-hairline px-3 py-2 text-left transition-colors hover:bg-surface-3"
        >
          <span className="text-xs font-medium text-ink-subtle">
            {expanded ? "Hide" : "Show"} full details
          </span>
          <motion.div
            animate={{ rotate: expanded ? 180 : 0 }}
            transition={T.fast}
          >
            <ChevronDown size={14} className="text-ink-faint" />
          </motion.div>
        </button>

        <AnimatePresence>
          {expanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden"
            >
              <div className="flex flex-col gap-3 pt-1">
                <Field label="Claim" text={arg.claim} highlight />
                <div className="ml-2 flex flex-col gap-3 border-l-2 border-hairline pl-3">
                  <Field label="Warrant" text={arg.warrant} />
                  {arg.evidence && <Field label="Evidence" text={arg.evidence} italic />}
                </div>
                <Field label="Impact" text={arg.impact} highlight />

                {arg.issues.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {arg.issues.map((issue, j) => (
                      <span key={j} className="rounded-full bg-amber/10 px-2 py-0.5 text-[10px] font-medium text-amber">
                        {issue}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    );
  }

  // Technical Flow: Full details visible (original view)
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.06, ...T.base }}
      whileHover={{
        y: -2,
        boxShadow: "0 4px 16px -4px oklch(0.510 0.156 278 / 0.12)",
        transition: T.fast,
      }}
      className={`flex flex-col gap-3 rounded-lg border border-l-4 border-hairline bg-surface-2 p-4 ${config.border} cursor-default`}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-semibold leading-snug text-ink">{arg.label}</p>
        <div className="flex shrink-0 items-center gap-1">
          {conf && <Badge variant={conf.variant}>{conf.label}</Badge>}
          <Badge variant={config.badge} className="capitalize">{config.label}</Badge>
        </div>
      </div>

      {/* Structured fields with visual flow */}
      <div className="flex flex-col gap-3">
        <Field label="Claim" text={arg.claim} highlight />
        <div className="ml-2 flex flex-col gap-3 border-l-2 border-hairline pl-3">
          <Field label="Warrant" text={arg.warrant} />
          {arg.evidence && <Field label="Evidence" text={arg.evidence} italic />}
        </div>
        <Field label="Impact" text={arg.impact} highlight />
      </div>

      {/* Coach Note */}
      {coachNote && (
        <div className="flex flex-col gap-2 rounded-lg border border-amber/20 bg-amber/5 px-3 py-2.5">
          <div className="flex items-center gap-1.5">
            <span className="text-xs font-semibold text-amber">Coach Note</span>
          </div>
          <p className="text-xs leading-relaxed text-ink">{coachNote}</p>
          {fixSuggestion && (
            <p className="text-xs leading-relaxed text-ink-subtle">{fixSuggestion}</p>
          )}
          {/* Show issue tags */}
          {arg.issues.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1">
              {arg.issues.map((issue, j) => (
                <span key={j} className="rounded-full bg-amber/10 px-1.5 py-0.5 text-[10px] font-medium text-amber">
                  {issue}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </motion.div>
  );
}
