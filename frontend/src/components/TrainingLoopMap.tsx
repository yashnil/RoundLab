"use client";

/**
 * TrainingLoopMap — Connected node path showing the Dissio practice loop.
 *
 * Speech Rep → Flow Report → Targeted Drill → Re-record → Improvement
 *
 * Each node has a status: complete | current | next | waiting.
 * The "current" node pulses once on mount (one-shot, not infinite).
 */

import { motion } from "motion/react";
import { Mic, GitBranch, Target, RefreshCw, TrendingUp, ChevronRight } from "lucide-react";
import { EASE } from "@/lib/motion";

// ── Types ──────────────────────────────────────────────────────────────────────

export type LoopNodeStatus = "complete" | "current" | "next" | "waiting";

export interface LoopNodeDef {
  label: string;
  sub: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
  status: LoopNodeStatus;
}

// ── Default nodes (demo / first-time user) ─────────────────────────────────────

export const DEFAULT_LOOP_NODES: LoopNodeDef[] = [
  { label: "Speech Rep",    sub: "Record 30+ seconds",  icon: Mic,       status: "current"  },
  { label: "Flow Report",   sub: "Argument analysis",   icon: GitBranch, status: "next"     },
  { label: "Targeted Drill",sub: "Practice weak skill", icon: Target,    status: "waiting"  },
  { label: "Re-record",     sub: "Apply the fix",       icon: RefreshCw, status: "waiting"  },
  { label: "Improvement",   sub: "Score delta",         icon: TrendingUp,status: "waiting"  },
];

// ── Visual config ──────────────────────────────────────────────────────────────

const STATUS_STYLE: Record<LoopNodeStatus, {
  ring: string; bg: string; icon: string; label: string; labelColor: string;
}> = {
  complete: { ring: "border-lav",      bg: "bg-lav",      icon: "text-white",      label: "Done",   labelColor: "text-lav"      },
  current:  { ring: "border-ok",       bg: "bg-ok",       icon: "text-white",      label: "Now",    labelColor: "text-ok"       },
  next:     { ring: "border-lav/50",   bg: "bg-lav/8",    icon: "text-lav",        label: "Next",   labelColor: "text-lav/80"   },
  waiting:  { ring: "border-hairline", bg: "bg-surface-2",icon: "text-ink-faint",  label: "",       labelColor: ""              },
};

// ── Component ─────────────────────────────────────────────────────────────────

interface TrainingLoopMapProps {
  nodes?: LoopNodeDef[];
  className?: string;
}

export default function TrainingLoopMap({
  nodes = DEFAULT_LOOP_NODES,
  className = "",
}: TrainingLoopMapProps) {
  return (
    <div
      className={`flex items-start justify-between gap-1 overflow-x-auto pb-1 ${className}`}
      role="list"
      aria-label="Training loop"
    >
      {nodes.map((node, i) => {
        const Icon    = node.icon;
        const s       = STATUS_STYLE[node.status];
        const isCurr  = node.status === "current";
        const isDone  = node.status === "complete";
        const isLast  = i === nodes.length - 1;

        return (
          <div
            key={i}
            className="flex shrink-0 items-start"
            role="listitem"
          >
            {/* Node column */}
            <div className="flex w-20 flex-col items-center gap-2 sm:w-24">
              {/* Icon circle */}
              <div className="relative">
                {/* One-shot pulse on the current node */}
                {isCurr && (
                  <motion.div
                    className="absolute inset-0 rounded-full border-2 border-ok/40"
                    initial={{ scale: 1, opacity: 0.5 }}
                    animate={{ scale: 1.6, opacity: 0 }}
                    transition={{ duration: 1.4, delay: 0.5, ease: "easeOut" }}
                  />
                )}
                <motion.div
                  initial={{ opacity: 0, scale: 0.7 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.35, delay: i * 0.07, ease: EASE }}
                  className={`relative flex h-10 w-10 items-center justify-center rounded-full border-2 ${s.ring} ${s.bg}`}
                >
                  <Icon size={16} className={s.icon} aria-hidden />
                </motion.div>
              </div>

              {/* Labels */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.3, delay: i * 0.07 + 0.1 }}
                className="flex flex-col items-center gap-0.5 text-center"
              >
                <p className={`text-[10px] font-semibold leading-snug ${
                  isDone || isCurr ? "text-ink" : "text-ink-faint"
                }`}>
                  {node.label}
                </p>
                <p className="text-[9px] leading-none text-ink-faint">{node.sub}</p>
                {s.label && (
                  <span className={`mt-0.5 rounded-full px-1.5 py-0.5 text-[8px] font-semibold ${
                    isCurr
                      ? "bg-ok/10 text-ok"
                      : node.status === "next"
                      ? "bg-lav/10 text-lav/80"
                      : "bg-lav/10 text-lav"
                  }`}>
                    {s.label}
                  </span>
                )}
              </motion.div>
            </div>

            {/* Connector arrow */}
            {!isLast && (
              <div className="flex shrink-0 items-start pt-5">
                <ChevronRight
                  size={14}
                  className={`transition-colors ${
                    isDone || isCurr
                      ? "text-lav/50"
                      : "text-hairline-strong"
                  }`}
                  aria-hidden
                />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
