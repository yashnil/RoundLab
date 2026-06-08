"use client";

import { motion } from "motion/react";
import { ArrowRight, RefreshCw, Target, Zap, CheckCircle2 } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { EASE } from "@/lib/motion";
import type { Drill } from "@/types";

interface PracticeLoopCTAProps {
  drills: Drill[];
  speechId: string;
  isComplete: boolean;
  hasFeedback: boolean;
  onGenerateDrills?: () => void;
  generatingDrills?: boolean;
  onStartNewAttempt?: () => void;
}

export default function PracticeLoopCTA({
  drills,
  speechId,
  isComplete,
  hasFeedback,
  onGenerateDrills,
  generatingDrills = false,
  onStartNewAttempt,
}: PracticeLoopCTAProps) {
  // Only show when report is complete
  if (!isComplete || !hasFeedback) return null;

  const assignedDrills  = drills.filter((d) => d.status === "assigned");
  const attemptedDrills = drills.filter((d) => d.status === "attempted");
  const completedDrills = drills.filter((d) => d.status === "completed");
  const allDone         = drills.length > 0 && drills.every((d) => d.status !== "assigned");

  // Derive the coaching state
  type LoopState = "no_drills" | "drills_ready" | "drills_in_progress" | "all_done";
  const loopState: LoopState =
    drills.length === 0          ? "no_drills" :
    assignedDrills.length > 0    ? "drills_ready" :
    !allDone                     ? "drills_in_progress" :
                                   "all_done";

  const content = {
    no_drills: {
      icon: Target,
      eyebrow: "Next step",
      title: "Turn feedback into targeted drills",
      body: "Generate 3 practice exercises based on your coaching report. Each targets a specific weakness.",
      primary: null,
      secondary: null,
      accentColor: "lav",
    },
    drills_ready: {
      icon: Zap,
      eyebrow: `${assignedDrills.length} drill${assignedDrills.length > 1 ? "s" : ""} waiting`,
      title: assignedDrills[0]?.title ?? "Start your first drill",
      body: `Targeting: ${assignedDrills[0]?.skill_target?.replace(/_/g, " ") ?? "key weakness"}`,
      accentColor: "lav",
    },
    drills_in_progress: {
      icon: Zap,
      eyebrow: `${attemptedDrills.length + completedDrills.length}/${drills.length} attempted`,
      title: "Keep going — finish your drills",
      body: assignedDrills[0]
        ? `Next up: ${assignedDrills[0].title}`
        : "Re-record to track your improvement.",
      accentColor: "lav",
    },
    all_done: {
      icon: CheckCircle2,
      eyebrow: "All drills complete",
      title: "Ready to re-record and track progress",
      body: "You've practiced all your drills. Start a new session with the same setup to measure improvement.",
      accentColor: "ok",
    },
  }[loopState];

  const IconCmp = content.icon;
  const borderColor = content.accentColor === "ok" ? "border-ok/20" : "border-lav/25";
  const bgGrad      = content.accentColor === "ok"
    ? "from-ok/5 to-ok/8"
    : "from-lav/5 to-lav/10";

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: EASE }}
      className={`rounded-2xl border bg-gradient-to-br ${borderColor} ${bgGrad} p-5`}
      style={{
        boxShadow: content.accentColor === "ok"
          ? "0 0 40px -14px oklch(0.620 0.170 145 / 0.18)"
          : "0 0 40px -14px oklch(0.510 0.156 278 / 0.20)",
      }}
    >
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-3">
          <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${
            content.accentColor === "ok" ? "bg-ok" : "bg-lav"
          }`}>
            <IconCmp size={18} className="text-white" />
          </div>
          <div className="flex flex-col gap-0.5">
            <p className={`text-eyebrow ${content.accentColor === "ok" ? "text-ok" : "text-lav"}`}>
              {content.eyebrow}
            </p>
            <p className="text-sm font-semibold text-ink">{content.title}</p>
            <p className="text-xs text-ink-subtle">{content.body}</p>
          </div>
        </div>

        <div className="flex shrink-0 flex-col gap-2 sm:items-end">
          {loopState === "no_drills" && onGenerateDrills && (
            <Button size="sm" onClick={onGenerateDrills} disabled={generatingDrills} className="gap-1.5">
              {generatingDrills ? "Generating…" : <><Target size={12} /> Generate Drills</>}
            </Button>
          )}

          {loopState === "drills_ready" && (
            <>
              <Link
                href={
                  assignedDrills[0]?.id
                    ? `/drills/${assignedDrills[0].id}`
                    : `/speech/${speechId}#drills`
                }
                className="flex items-center gap-1.5 rounded-md bg-lav px-3.5 py-2 text-xs font-semibold text-white transition-colors hover:bg-lav-hi"
              >
                Open drill workspace <ArrowRight size={12} />
              </Link>
              {onStartNewAttempt && (
                <button
                  type="button"
                  onClick={onStartNewAttempt}
                  className="flex items-center gap-1 text-xs text-ink-subtle transition-colors hover:text-ink"
                >
                  <RefreshCw size={10} /> Re-record instead
                </button>
              )}
            </>
          )}

          {loopState === "drills_in_progress" && assignedDrills.length > 0 && (
            <Link
              href={
                assignedDrills[0]?.id
                  ? `/drills/${assignedDrills[0].id}`
                  : `/speech/${speechId}#drills`
              }
              className="flex items-center gap-1.5 rounded-md bg-lav px-3.5 py-2 text-xs font-semibold text-white transition-colors hover:bg-lav-hi"
            >
              Open drill workspace <ArrowRight size={12} />
            </Link>
          )}

          {loopState === "all_done" && (
            <>
              {onStartNewAttempt && (
                <Button size="sm" onClick={onStartNewAttempt} className="gap-1.5">
                  <RefreshCw size={12} /> New Attempt
                </Button>
              )}
              <Link href="/dashboard" className="flex items-center gap-1 text-xs text-ink-subtle transition-colors hover:text-ink">
                Back to dashboard <ArrowRight size={10} />
              </Link>
            </>
          )}
        </div>
      </div>

      {/* Progress dots for drills_in_progress / drills_ready */}
      {drills.length > 0 && (loopState === "drills_ready" || loopState === "drills_in_progress") && (
        <div className="mt-3 flex items-center gap-1.5 border-t border-lav/10 pt-3">
          <span className="text-eyebrow text-ink-faint">Progress:</span>
          <div className="flex items-center gap-1">
            {drills.map((d, i) => (
              <div
                key={i}
                title={d.title}
                className={`h-1.5 w-6 rounded-full transition-colors ${
                  d.status === "completed" ? "bg-ok" :
                  d.status === "attempted" ? "bg-warn" :
                  "bg-hairline"
                }`}
              />
            ))}
          </div>
          <span className="text-xs text-ink-faint">
            {completedDrills.length + attemptedDrills.length}/{drills.length} done
          </span>
        </div>
      )}
    </motion.div>
  );
}
