"use client";

import { motion } from "motion/react";
import { Badge } from "@/components/ui/badge";
import { T } from "@/lib/motion";
import type { ArgumentItem, ArgumentType } from "@/types";

const TYPE_CONFIG: Record<
  ArgumentType,
  { badge: "green" | "blue" | "violet" | "orange" | "default"; border: string }
> = {
  offense:  { badge: "green",   border: "border-l-ok"              },
  defense:  { badge: "blue",    border: "border-l-blue"            },
  weighing: { badge: "violet",  border: "border-l-violet"          },
  response: { badge: "orange",  border: "border-l-orange"          },
  unclear:  { badge: "default", border: "border-l-hairline-strong" },
};

function confBadge(c: number | null) {
  if (c === null) return null;
  if (c >= 0.8) return { label: "High", variant: "green"  as const };
  if (c >= 0.5) return { label: "Med",  variant: "amber"  as const };
  return            { label: "Low",  variant: "red"    as const };
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
    return "Add a 'because' sentence after your claim. Explain the logical link: why is this claim true?";
  }
  if (hasEvidenceIssue) {
    return "After citing your source, add: 'This proves [claim] because [one sentence explanation].'";
  }
  if (hasImpactIssue) {
    return "Describe the real-world consequence. Who is affected? How severe is it? How soon does it happen?";
  }
  if (hasWeighingIssue) {
    return "Add a comparison: 'This outweighs [opponent's impact] because [magnitude/probability/timeframe].'";
  }

  // Generic fallback
  return "Strengthen each part: claim → warrant → evidence → impact. Every link should be crystal clear.";
}

export default function ArgumentCard({ arg, index }: { arg: ArgumentItem; index: number }) {
  const config = TYPE_CONFIG[arg.argument_type] ?? TYPE_CONFIG.unclear;
  const conf   = confBadge(arg.confidence);
  const coachNote = getCoachNote(arg.issues);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.06, ...T.base }}
      whileHover={{
        y: -2,
        boxShadow: "0 4px 16px -4px oklch(0.510 0.156 278 / 0.12)",
        borderColor: "oklch(0.270 0.006 264)",
        transition: T.fast,
      }}
      className={`flex flex-col gap-3 rounded-lg border border-l-4 border-hairline bg-surface-2 p-4 ${config.border} cursor-default`}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-semibold leading-snug text-ink">{arg.label}</p>
        <div className="flex shrink-0 items-center gap-1">
          {conf && <Badge variant={conf.variant}>{conf.label}</Badge>}
          <Badge variant={config.badge} className="capitalize">{arg.argument_type}</Badge>
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
          {/* Show issue tags as secondary info */}
          {arg.issues.length > 0 && (
            <div className="flex flex-wrap gap-1">
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
