"use client";

import { useEffect, useState } from "react";
import { motion } from "motion/react";
import {
  ChevronDown, ChevronUp, CheckSquare, Square,
  Target, BookOpen, Zap, Headphones,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { T } from "@/lib/motion";
import { apiFetch } from "@/lib/api";
import DrillAttemptRecorder from "@/components/DrillAttemptRecorder";
import type { Drill, DrillAttempt, DrillStatus } from "@/types";

// ── Skill target → display label + badge variant ──────────────────────────────

const SKILL_LABELS: Record<string, { label: string; variant: "indigo" | "green" | "amber" | "red" | "blue" | "violet" | "orange" | "default" }> = {
  weighing:         { label: "Impact Weighing",    variant: "indigo"  },
  warranting:       { label: "Warranting",         variant: "blue"    },
  drops:            { label: "Drop Prevention",    variant: "red"     },
  extensions:       { label: "Extensions",         variant: "green"   },
  evidence:         { label: "Evidence Use",       variant: "amber"   },
  clash:            { label: "Clash",              variant: "violet"  },
  judge_adaptation: { label: "Judge Adaptation",   variant: "orange"  },
  collapse:         { label: "Collapse Strategy",  variant: "indigo"  },
  line_by_line:     { label: "Line-by-Line",       variant: "blue"    },
};

const DIFFICULTY_BADGE: Record<string, { label: string; variant: "green" | "amber" | "red" }> = {
  beginner:     { label: "Beginner",     variant: "green" },
  intermediate: { label: "Intermediate", variant: "amber" },
  advanced:     { label: "Advanced",     variant: "red"   },
};

const STATUS_CONFIG: Record<DrillStatus, { label: string; dot: string }> = {
  assigned:  { label: "Not started", dot: "bg-ink-faint" },
  attempted: { label: "Attempted",   dot: "bg-warn"      },
  completed: { label: "Completed",   dot: "bg-ok"        },
};

// Derive a recommended time limit from skill_target + difficulty
function drillTimeLimit(skillTarget: string, difficulty: string): string {
  const base: Record<string, number> = {
    weighing: 90, warranting: 60, drops: 120, extensions: 90,
    evidence: 60, clash: 90, judge_adaptation: 60,
    collapse: 90, line_by_line: 90,
  };
  const multiplier = difficulty === "advanced" ? 1.5 : difficulty === "beginner" ? 0.75 : 1;
  const secs = Math.round((base[skillTarget] ?? 90) * multiplier);
  return secs < 60 ? `${secs}s` : `${Math.round(secs / 60)} min`;
}

// ── Drill number indicator ────────────────────────────────────────────────────

function DrillNumber({ n, status }: { n: number; status: DrillStatus }) {
  const isDone = status !== "assigned";
  return (
    <div
      className={[
        "flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold",
        isDone ? "bg-lav text-white" : "border border-hairline-strong text-ink-faint",
      ].join(" ")}
    >
      {n}
    </div>
  );
}

// ── Main DrillCard ────────────────────────────────────────────────────────────

interface DrillCardProps {
  drill: Drill;
  index: number;
  onStatusChange?: (drillId: string, status: DrillStatus) => void;
  updatingId?: string | null;
  userId?: string;
}

export default function DrillCard({
  drill, index, onStatusChange, updatingId, userId,
}: DrillCardProps) {
  const [expanded, setExpanded] = useState(index === 0);
  const [attempts, setAttempts] = useState<DrillAttempt[]>([]);
  const [loadingAttempts, setLoadingAttempts] = useState(false);
  const [attemptsFetched, setAttemptsFetched] = useState(false);

  const skill  = SKILL_LABELS[drill.skill_target] ?? { label: drill.skill_target, variant: "default" as const };
  const diff   = DIFFICULTY_BADGE[drill.difficulty] ?? DIFFICULTY_BADGE.beginner;
  const status = STATUS_CONFIG[drill.status as DrillStatus] ?? STATUS_CONFIG.assigned;

  const steps  = drill.instructions?.split("\n").filter(Boolean) ?? [];
  const isUpdating = updatingId === drill.id;

  // Fetch attempts when expanded (only once)
  useEffect(() => {
    if (expanded && !attemptsFetched && !loadingAttempts) {
      setLoadingAttempts(true);
      apiFetch<DrillAttempt[]>(`/drills/${drill.id}/attempts`)
        .then((data) => {
          setAttempts(data);
          setAttemptsFetched(true);
        })
        .catch(() => {})
        .finally(() => setLoadingAttempts(false));
    }
  }, [expanded, drill.id, attemptsFetched, loadingAttempts]);

  function handleAttemptSaved() {
    // Refresh attempts list without triggering loading state
    apiFetch<DrillAttempt[]>(`/drills/${drill.id}/attempts`)
      .then((data) => {
        setAttempts(data);
        setAttemptsFetched(true);
      })
      .catch(() => {});
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.07, ...T.base }}
      className={[
        "rounded-xl border transition-colors",
        drill.status === "completed"
          ? "border-ok/20 bg-ok/3"
          : drill.status === "attempted"
          ? "border-warn/20 bg-surface-1"
          : "border-hairline bg-surface-1",
      ].join(" ")}
    >
      {/* Header row */}
      <button
        type="button"
        className="flex w-full items-center gap-3 px-5 py-4 text-left"
        onClick={() => setExpanded((v) => !v)}
      >
        <DrillNumber n={drill.order} status={drill.status as DrillStatus} />

        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-sm font-semibold text-ink">{drill.title}</span>
            <Badge variant={skill.variant as "indigo"}>{skill.label}</Badge>
            <Badge variant={diff.variant}>{diff.label}</Badge>
            {attempts.length > 0 && (
              <Badge variant="default" className="gap-1">
                <Headphones size={10} />
                {attempts.length}
              </Badge>
            )}
          </div>
          {drill.source_weakness && (
            <p className="text-xs text-ink-faint">
              <span className="text-ink-subtle">Targets: </span>
              {drill.source_weakness}
            </p>
          )}
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <span className="flex items-center gap-1.5 text-xs text-ink-subtle">
            <span className={`h-1.5 w-1.5 rounded-full ${status.dot}`} />
            {status.label}
          </span>
          <motion.span
            animate={{ rotate: expanded ? 180 : 0 }}
            transition={T.fast}
          >
            <ChevronDown size={14} className="text-ink-faint" />
          </motion.span>
        </div>
      </button>

      {/* Expanded content */}
      {expanded && (
        <div className="overflow-hidden">
            <div className="flex flex-col gap-4 border-t border-hairline px-5 py-4">
              {/* Completion banner */}
              {drill.status === "completed" && (
                <div className="flex items-center gap-2 rounded-lg border border-ok/20 bg-ok/5 px-3 py-2">
                  <CheckSquare size={13} className="shrink-0 text-ok" />
                  <p className="text-xs font-medium text-ok">Drill completed — good work. Re-record to see if it shows in your next speech.</p>
                </div>
              )}

              {/* Time limit + description row */}
              <div className="flex items-start justify-between gap-3">
                {drill.description && (
                  <p className="text-sm leading-relaxed text-ink-muted">{drill.description}</p>
                )}
                <div className="flex shrink-0 flex-col items-end gap-0.5">
                  <span className="text-eyebrow text-ink-faint">Time limit</span>
                  <span className="font-mono text-xs font-semibold text-ink">
                    {drill.time_limit_seconds != null
                      ? drill.time_limit_seconds < 60
                        ? `${drill.time_limit_seconds}s`
                        : `${Math.floor(drill.time_limit_seconds / 60)}m${drill.time_limit_seconds % 60 > 0 ? ` ${drill.time_limit_seconds % 60}s` : ""}`
                      : drillTimeLimit(drill.skill_target, drill.difficulty)}
                  </span>
                </div>
              </div>

              {/* Prompt — the actual exercise */}
              <div className="flex flex-col gap-1.5">
                <div className="flex items-center gap-1.5">
                  <Target size={12} className="text-lav" />
                  <span className="text-eyebrow text-ink-subtle">Exercise prompt</span>
                </div>
                <p className="rounded-xl border border-lav/15 bg-lav/5 px-4 py-3 text-sm leading-relaxed text-ink">
                  {drill.prompt}
                </p>
              </div>

              {/* Instructions */}
              {steps.length > 0 && (
                <div className="flex flex-col gap-2">
                  <div className="flex items-center gap-1.5">
                    <BookOpen size={12} className="text-lav" />
                    <span className="text-eyebrow text-ink-subtle">How to practice</span>
                  </div>
                  <ol className="flex flex-col gap-1.5">
                    {steps.map((step, i) => (
                      <li key={i} className="flex items-start gap-2.5 text-sm text-ink-muted">
                        <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border border-hairline text-[10px] font-bold text-ink-faint">
                          {i + 1}
                        </span>
                        {step.replace(/^\d+\.\s*/, "")}
                      </li>
                    ))}
                  </ol>
                </div>
              )}

              {/* Success criteria */}
              {drill.success_criteria.length > 0 && (
                <div className="flex flex-col gap-2">
                  <div className="flex items-center gap-1.5">
                    <Zap size={12} className="text-lav" />
                    <span className="text-eyebrow text-ink-subtle">Success criteria</span>
                  </div>
                  <ul className="flex flex-col gap-1.5">
                    {drill.success_criteria.map((criterion, i) => {
                      const checked = drill.status === "completed";
                      return (
                        <li key={i} className="flex items-center gap-2 text-sm text-ink-muted">
                          {checked
                            ? <CheckSquare size={13} className="shrink-0 text-ok" />
                            : <Square     size={13} className="shrink-0 text-ink-faint" />}
                          {criterion}
                        </li>
                      );
                    })}
                  </ul>
                </div>
              )}

              {/* Status Control - reversible */}
              {onStatusChange && (
                <div className="flex items-center gap-3 pt-1">
                  <label htmlFor={`status-${drill.id}`} className="text-xs font-medium text-ink-subtle">
                    Mark as:
                  </label>
                  <select
                    id={`status-${drill.id}`}
                    value={drill.status}
                    onChange={(e) => onStatusChange(drill.id, e.target.value as DrillStatus)}
                    disabled={isUpdating}
                    className="rounded-md border border-hairline bg-surface-2 px-2 py-1 text-xs text-ink transition-colors hover:border-hairline-strong focus:border-lav focus:outline-none disabled:opacity-50"
                  >
                    <option value="assigned">Not started</option>
                    <option value="attempted">Attempted</option>
                    <option value="completed">Completed</option>
                  </select>
                  {isUpdating && <span className="text-xs text-ink-faint">Saving…</span>}
                </div>
              )}

              {/* Drill Attempt Recorder */}
              {userId && (
                <div className="flex flex-col gap-2 pt-2">
                  <DrillAttemptRecorder
                    drillId={drill.id}
                    userId={userId}
                    speechId={drill.speech_id}
                    onAttemptSaved={handleAttemptSaved}
                  />
                  {/* Stable container for attempts count to prevent layout shift */}
                  <div className="min-h-[20px]">
                    {loadingAttempts ? (
                      <p className="text-xs text-ink-faint">Loading attempts…</p>
                    ) : attempts.length > 0 ? (
                      <p className="text-xs font-medium text-ink-subtle">
                        {attempts.length} attempt{attempts.length !== 1 ? "s" : ""} recorded
                      </p>
                    ) : null}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
    </motion.div>
  );
}
