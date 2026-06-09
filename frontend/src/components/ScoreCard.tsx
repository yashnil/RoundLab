"use client";

import { useEffect } from "react";
import { motion, useMotionValue, useTransform, animate } from "motion/react";
import { cn } from "@/lib/utils";

const GRADE_SCALE = [
  { min: 90, grade: "Tournament-Ready",        ring: "border-ok"     },
  { min: 80, grade: "Strong",                  ring: "border-ok"     },
  { min: 70, grade: "Solid",                   ring: "border-lav"    },
  { min: 60, grade: "Developing",              ring: "border-lav-lo" },
  { min: 50, grade: "Flawed but Complete",     ring: "border-warn"   },
  { min: 40, grade: "Needs Foundation",        ring: "border-warn"   },
  { min: 30, grade: "Severely Underdeveloped", ring: "border-danger" },
  { min:  0, grade: "Incomplete",              ring: "border-danger" },
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
      className={cn("flex items-center gap-6", className)}
    >
      {/* Score ring — responsive size */}
      <div className="relative shrink-0">
        <div
          className={cn(
            "absolute inset-0 rounded-full opacity-25 blur-md",
            ring.replace("border-", "bg-"),
          )}
        />
        <div
          className={cn(
            "relative flex h-20 w-20 shrink-0 flex-col items-center justify-center rounded-full border-[3px] bg-canvas sm:h-24 sm:w-24",
            ring,
          )}
        >
          <span
            className="text-3xl font-bold leading-none tabular-nums text-ink sm:text-4xl"
            style={{ fontFamily: "var(--font-jetbrains-mono)" }}
          >
            {score !== null ? <AnimatedNumber target={score} /> : "—"}
          </span>
          <span
            className="mt-0.5 text-[10px] text-ink-faint"
            style={{ fontFamily: "var(--font-jetbrains-mono)" }}
          >
            /100
          </span>
        </div>
      </div>

      {/* Grade + summary */}
      <div className="flex flex-col gap-1.5">
        <p className="text-heading text-ink sm:text-title">{grade}</p>
        {summary && (
          <p className="text-sm leading-relaxed text-ink-subtle">{summary}</p>
        )}
      </div>
    </motion.div>
  );
}
