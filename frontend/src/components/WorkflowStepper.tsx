"use client";

import { motion, AnimatePresence } from "motion/react";
import { Check } from "lucide-react";
import { T } from "@/lib/motion";

export interface WorkflowStep {
  label: string;
  done: boolean;
  current?: boolean;
  soon?: boolean;
}

/**
 * WorkflowStepper — compact pill-based progress indicator.
 * Done: lavender fill + spring check.
 * Current: lavender outline + subtle CSS ring pulse.
 * Locked/soon: muted.
 */
export default function WorkflowStepper({ steps }: { steps: WorkflowStep[] }) {
  return (
    <div className="flex items-center overflow-x-auto">
      {steps.map((step, i) => {
        const isDone    = step.done;
        const isCurrent = !isDone && steps.slice(0, i).every((s) => s.done) && !step.soon;

        return (
          <div key={step.label} className="flex items-center">
            <div
              className={[
                "relative flex items-center gap-1 whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-medium transition-all",
                isDone
                  ? "bg-lav text-white"
                  : isCurrent
                  ? "border border-lav/50 text-lav step-pulse"
                  : "text-ink-faint",
              ].join(" ")}
            >
              <AnimatePresence mode="wait">
                {isDone ? (
                  <motion.span
                    key="check"
                    initial={{ scale: 0, rotate: -30 }}
                    animate={{ scale: 1, rotate: 0 }}
                    transition={T.snap}
                  >
                    <Check size={10} strokeWidth={2.5} />
                  </motion.span>
                ) : isCurrent ? (
                  <motion.span
                    key="dot"
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={T.snap}
                    className="h-1.5 w-1.5 rounded-full bg-lav"
                  />
                ) : null}
              </AnimatePresence>

              {step.label}
              {step.soon && <span className="text-[9px] opacity-50">(soon)</span>}
            </div>

            {i < steps.length - 1 && (
              <div className={[
                "mx-1.5 h-px w-4 shrink-0 transition-colors duration-500",
                step.done ? "bg-lav/40" : "bg-hairline",
              ].join(" ")} />
            )}
          </div>
        );
      })}
    </div>
  );
}
