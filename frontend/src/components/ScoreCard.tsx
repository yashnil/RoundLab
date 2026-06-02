"use client";

import { useEffect } from "react";
import { motion, useMotionValue, useTransform, animate } from "motion/react";
import { cn } from "@/lib/utils";

const GRADE_SCALE = [
  { min: 88, grade: "Excellent",   ring: "border-ok"     },
  { min: 75, grade: "Strong",      ring: "border-lav"    },
  { min: 62, grade: "Developing",  ring: "border-lav-lo" },
  { min: 50, grade: "Needs Work",  ring: "border-warn"   },
  { min:  0, grade: "Beginning",   ring: "border-danger" },
] as const;

function resolve(score: number | null) {
  if (score === null) return { grade: "Not scored", ring: "border-hairline-strong" };
  return GRADE_SCALE.find((s) => score >= s.min) ?? GRADE_SCALE[GRADE_SCALE.length - 1];
}

/** Animates a number from 0 to target over ~1.4s */
function AnimatedNumber({ target }: { target: number }) {
  const mv = useMotionValue(0);
  const display = useTransform(mv, (v) => Math.round(v).toString());

  useEffect(() => {
    const ctrl = animate(mv, target, {
      duration: 1.4,
      delay: 0.15,
      ease: [0.22, 1, 0.36, 1],
    });
    return ctrl.stop;
  }, [mv, target]);

  return <motion.span>{display}</motion.span>;
}

interface ScoreCardProps {
  score: number | null;
  summary?: string | null;
  className?: string;
}

export default function ScoreCard({ score, summary, className }: ScoreCardProps) {
  const { grade, ring } = resolve(score);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
      className={cn("flex items-start gap-5", className)}
    >
      {/* Score ring */}
      <div
        className={cn(
          "relative flex h-20 w-20 shrink-0 flex-col items-center justify-center rounded-full border-[3px]",
          ring,
        )}
      >
        <span className="text-3xl font-bold leading-none tracking-tight text-ink">
          {score !== null ? <AnimatedNumber target={score} /> : "—"}
        </span>
        <span className="mt-0.5 text-xs text-ink-faint">/100</span>
      </div>

      {/* Grade + summary */}
      <div className="flex flex-col gap-1.5 pt-1">
        <p className="text-heading text-ink">{grade}</p>
        {summary && (
          <p className="text-sm leading-relaxed text-ink-subtle">{summary}</p>
        )}
      </div>
    </motion.div>
  );
}
