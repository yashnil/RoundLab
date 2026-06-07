"use client";

/**
 * JudgeLensComparison — Shows how the same speech looks different
 * under Lay, Flow, Tech, and Coach judging paradigms.
 *
 * Use on landing (illustrative) or report page (contextual).
 * All data is static — no backend fetch.
 */

import { motion } from "motion/react";
import { Eye, GitBranch, BarChart3, BookOpen } from "lucide-react";
import { EASE } from "@/lib/motion";

// ── Lens definitions ───────────────────────────────────────────────────────────

interface LensDef {
  key: string;
  label: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
  colorClass: string;      // text-* class
  borderClass: string;     // border-* class
  bgClass: string;         // bg-* class
  barClass: string;        // bg-* class for mini bars
  focus: string[];
  /** 1–5 emphasis weight per dimension */
  weights: { Clarity: number; Warrants: number; Evidence: number; Weighing: number };
  note: string;
}

const LENSES: LensDef[] = [
  {
    key:         "lay",
    label:       "Lay Judge",
    icon:        Eye,
    colorClass:  "text-ok",
    borderClass: "border-ok/20",
    bgClass:     "bg-ok/5",
    barClass:    "bg-ok",
    focus:       ["Clarity of story", "Real-world impact", "Plain language"],
    weights:     { Clarity: 5, Warrants: 2, Evidence: 2, Weighing: 4 },
    note:        "Persuasion over precision. Impacts must land emotionally.",
  },
  {
    key:         "flow",
    label:       "Flow Judge",
    icon:        GitBranch,
    colorClass:  "text-lav",
    borderClass: "border-lav/20",
    bgClass:     "bg-lav/5",
    barClass:    "bg-lav",
    focus:       ["Extensions", "Dropped arguments", "Weighing"],
    weights:     { Clarity: 2, Warrants: 5, Evidence: 4, Weighing: 5 },
    note:        "Dropped = conceded. Weigh impacts explicitly or lose.",
  },
  {
    key:         "tech",
    label:       "Tech Judge",
    icon:        BarChart3,
    colorClass:  "text-cyan",
    borderClass: "border-cyan/20",
    bgClass:     "bg-cyan/5",
    barClass:    "bg-cyan",
    focus:       ["Concessions", "Evidence quality", "Line-by-line"],
    weights:     { Clarity: 2, Warrants: 4, Evidence: 5, Weighing: 4 },
    note:        "Precision matters. Concessions are permanent on the flow.",
  },
  {
    key:         "coach",
    label:       "Coach",
    icon:        BookOpen,
    colorClass:  "text-warn",
    borderClass: "border-warn/20",
    bgClass:     "bg-warn/5",
    barClass:    "bg-warn",
    focus:       ["Skill gaps", "Next drill target", "Improvement loop"],
    weights:     { Clarity: 3, Warrants: 5, Evidence: 4, Weighing: 5 },
    note:        "Diagnoses weaknesses. Every issue becomes a practice rep.",
  },
];

const DIM_ORDER = ["Clarity", "Warrants", "Evidence", "Weighing"] as const;

// ── Component ─────────────────────────────────────────────────────────────────

interface JudgeLensComparisonProps {
  className?: string;
}

export default function JudgeLensComparison({ className = "" }: JudgeLensComparisonProps) {
  return (
    <div className={`grid grid-cols-2 gap-3 lg:grid-cols-4 ${className}`}>
      {LENSES.map((lens, i) => {
        const Icon = lens.icon;
        return (
          <motion.div
            key={lens.key}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, delay: i * 0.08, ease: EASE }}
            className={`flex flex-col gap-3 rounded-xl border p-4 ${lens.borderClass} ${lens.bgClass}`}
          >
            {/* Header */}
            <div className="flex items-center gap-2">
              <Icon size={14} className={lens.colorClass} aria-hidden />
              <p className={`text-sm font-semibold ${lens.colorClass}`}>{lens.label}</p>
            </div>

            {/* Focus areas */}
            <div className="flex flex-col gap-1">
              {lens.focus.map((f) => (
                <div key={f} className="flex items-center gap-1.5">
                  <span className={`h-1 w-1 shrink-0 rounded-full ${lens.barClass} opacity-70`} aria-hidden />
                  <span className="text-[11px] text-ink-muted">{f}</span>
                </div>
              ))}
            </div>

            {/* Emphasis weight bars */}
            <div className="flex flex-col gap-1.5 border-t border-hairline pt-2">
              {DIM_ORDER.map((dim) => {
                const val = lens.weights[dim];
                return (
                  <div key={dim} className="flex items-center gap-1.5">
                    <span className="w-14 shrink-0 text-[9px] text-ink-faint">{dim}</span>
                    <div className="h-0.5 flex-1 overflow-hidden rounded-full bg-hairline">
                      <div
                        className={`h-full rounded-full ${lens.barClass}`}
                        style={{ width: `${(val / 5) * 100}%`, opacity: 0.65 }}
                        aria-label={`${dim}: ${val}/5`}
                      />
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Coaching note */}
            <p className="text-[10px] leading-relaxed text-ink-faint">{lens.note}</p>
          </motion.div>
        );
      })}
    </div>
  );
}
