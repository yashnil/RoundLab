"use client";

/**
 * CoachMarginNote — A human-authored annotation component.
 *
 * Used alongside analysis sections to add coach-voice commentary.
 * Visually distinct from AI output: looks like a margin annotation
 * rather than a generated block.
 *
 * Usage:
 *   <CoachMarginNote note="Good impact — but the warrant disappears." />
 *   <CoachMarginNote type="warn" note="A flow judge tracks warrant, not claim." />
 */

import { motion } from "motion/react";
import { EASE } from "@/lib/motion";

type NoteType = "info" | "warn" | "strong";

interface CoachMarginNoteProps {
  note: string;
  type?: NoteType;
  label?: string;
}

const NOTE_STYLE: Record<NoteType, {
  bar: string; bg: string; border: string; labelColor: string;
}> = {
  info:   { bar: "oklch(0.510 0.156 278 / 0.50)", bg: "bg-lav/5",  border: "border-lav/20",  labelColor: "text-lav"  },
  warn:   { bar: "oklch(0.750 0.155 74 / 0.50)",  bg: "bg-warn/5", border: "border-warn/20", labelColor: "text-warn" },
  strong: { bar: "oklch(0.620 0.170 145 / 0.50)", bg: "bg-ok/5",   border: "border-ok/20",   labelColor: "text-ok"   },
};

export default function CoachMarginNote({
  note,
  type = "info",
  label = "Coach note",
}: CoachMarginNoteProps) {
  const s = NOTE_STYLE[type];
  return (
    <motion.div
      initial={{ opacity: 0, x: -4 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.3, ease: EASE }}
      className={`rounded-r-lg border-l-2 pl-3 pr-3 py-2.5 ${s.bg} ${s.border}`}
      style={{ borderLeftColor: s.bar }}
    >
      <p className={`mb-0.5 text-[9px] font-bold uppercase tracking-wider ${s.labelColor}`}>
        {label}
      </p>
      <p className="text-xs leading-relaxed text-ink-muted">{note}</p>
    </motion.div>
  );
}
