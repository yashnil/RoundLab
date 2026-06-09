"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "motion/react";
import {
  ChevronDown, CheckSquare, Square,
  Target, Zap, Headphones, ArrowRight,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { T } from "@/lib/motion";
import { apiFetch } from "@/lib/api";
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
  const [expanded, setExpanded] = useState(false);
  const [attempts, setAttempts] = useState<DrillAttempt[]>([]);
  const [loadingAttempts, setLoadingAttempts] = useState(false);
  const [attemptsFetched, setAttemptsFetched] = useState(false);

  const skill   = SKILL_LABELS[drill.skill_target] ?? { label: drill.skill_target, variant: "default" as const };
  const diff    = DIFFICULTY_BADGE[drill.difficulty] ?? DIFFICULTY_BADGE.beginner;
  const status  = STATUS_CONFIG[drill.status as DrillStatus] ?? STATUS_CONFIG.assigned;
  const isUpdating = updatingId === drill.id;

  const latestScore = attempts[0]?.score ?? null;

  // Fetch attempts when expanded — only once, only when userId is available
  useEffect(() => {
    if (!userId || !expanded || attemptsFetched || loadingAttempts) return;
    setLoadingAttempts(true);
    apiFetch<DrillAttempt[]>(`/drills/${drill.id}/attempts?user_id=${userId}`)
      .then((data) => {
        setAttempts(data);
        setAttemptsFetched(true);
      })
      .catch(() => {})
      .finally(() => setLoadingAttempts(false));
  }, [expanded, drill.id, attemptsFetched, loadingAttempts, userId]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.07, ...T.base }}
      className={[
        "rounded-lg border transition-colors",
        drill.status === "completed"
          ? "border-ok/20 bg-ok/3"
          : drill.status === "attempted"
          ? "border-warn/20 bg-surface-1"
          : "border-hairline bg-surface-1",
      ].join(" ")}
    >
      {/* ── Header row (always visible) ───────────────────────────────── */}
      <button
        type="button"
        className="flex w-full items-center gap-3 px-5 py-4 text-left"
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
      >
        {/* Order number */}
        <div
          className={[
            "flex h-6 w-6 shrink-0 items-center justify-center rounded-[3px] text-[11px] font-bold",
            drill.status !== "assigned" ? "bg-lav text-white" : "border border-hairline-strong text-ink-faint",
          ].join(" ")}
          style={{ fontFamily: "var(--font-jetbrains-mono)" }}
        >
          {drill.order}
        </div>

        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-sm font-semibold text-ink">{drill.title}</span>
            <Badge variant={skill.variant as "indigo"}>{skill.label}</Badge>
            <Badge variant={diff.variant}>{diff.label}</Badge>
            {attemptsFetched && attempts.length > 0 && (
              <Badge variant="default" className="gap-1">
                <Headphones size={10} />
                {attempts.length}
                {latestScore !== null && (
                  <span className="ml-0.5 font-bold text-lav">{latestScore}</span>
                )}
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
          <motion.span animate={{ rotate: expanded ? 180 : 0 }} transition={T.fast}>
            <ChevronDown size={14} className="text-ink-faint" />
          </motion.span>
        </div>
      </button>

      {/* ── Expanded: assignment summary + workspace link ──────────────── */}
      {expanded && (
        <div className="flex flex-col gap-4 border-t border-hairline px-5 pb-5 pt-4">

          {/* Completion banner */}
          {drill.status === "completed" && (
            <div className="flex items-center gap-2 rounded-lg border border-ok/20 bg-ok/5 px-3 py-2">
              <CheckSquare size={13} className="shrink-0 text-ok" />
              <p className="text-xs font-medium text-ok">
                Drill completed — re-record your speech to track the improvement.
              </p>
            </div>
          )}

          {/* Exercise prompt (compact) */}
          <div className="flex flex-col gap-1.5">
            <div className="section-stamp">
              <Target size={10} className="text-lav" />
              Exercise prompt
            </div>
            <p className="line-clamp-3 text-sm leading-relaxed text-ink-muted">{drill.prompt}</p>
          </div>

          {/* Success criteria summary (checkboxes only) */}
          {drill.success_criteria.length > 0 && (
            <div className="flex flex-col gap-1">
              <div className="section-stamp">
                <Zap size={10} className="text-lav" />
                Success criteria
              </div>
              <ul className="flex flex-col gap-1">
                {drill.success_criteria.map((c, i) => (
                  <li key={i} className="flex items-center gap-2 text-xs text-ink-muted">
                    {drill.status === "completed"
                      ? <CheckSquare size={11} className="shrink-0 text-ok" />
                      : <Square      size={11} className="shrink-0 text-ink-faint" />}
                    {c}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Attempts summary */}
          {loadingAttempts && (
            <p className="text-xs text-ink-faint">Loading attempts…</p>
          )}
          {attemptsFetched && attempts.length > 0 && (
            <div className="flex items-center gap-2">
              <Headphones size={12} className="text-ink-faint" />
              <span className="text-xs text-ink-subtle">
                {attempts.length} attempt{attempts.length !== 1 ? "s" : ""} recorded
                {latestScore !== null && (
                  <span className="ml-1 font-semibold text-lav">· latest: {latestScore}/100</span>
                )}
              </span>
            </div>
          )}
          {attemptsFetched && attempts.length === 0 && (
            <p className="text-xs text-ink-faint">No attempts yet.</p>
          )}

          {/* Primary CTA — always link to the dedicated workspace */}
          <div className="flex flex-wrap items-center gap-2 pt-1">
            <Link
              href={`/drills/${drill.id}`}
              className="flex items-center gap-1.5 rounded-md bg-lav px-4 py-2 text-xs font-semibold text-white transition-colors hover:bg-lav-hi"
            >
              Open drill workspace
              <ArrowRight size={12} />
            </Link>
          </div>

          {/* Status control — for coach/manual override */}
          {onStatusChange && (
            <div className="flex items-center gap-3 border-t border-hairline pt-3">
              <label htmlFor={`status-${drill.id}`} className="text-xs text-ink-subtle">
                Status:
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
        </div>
      )}
    </motion.div>
  );
}
