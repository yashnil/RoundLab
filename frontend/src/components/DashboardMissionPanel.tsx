"use client";

/**
 * DashboardMissionPanel — The cockpit top section of the dashboard.
 *
 * Replaces the previous stacked: page header + metrics grid + mission card + focus skill.
 * Composes them into a single visual "mission briefing" command view.
 *
 * Left dominant panel:    next mission + 4 metrics + CTA
 * Right support panel:    current focus skill + XP progress
 */

import Link from "next/link";
import { motion } from "motion/react";
import {
  Mic, CheckCircle2, Target, Headphones, Zap, Trophy, ArrowRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { EASE } from "@/lib/motion";
import type { ProgressSummary, Speech, SkillAverages } from "@/types";
import { deriveLowestSkill, derivePracticeNextAction } from "@/lib/debateHelpers";

// ── Compact metric cell ────────────────────────────────────────────────────────

function MetricCell({
  icon: Icon, value, label, accent,
}: { icon: React.ComponentType<{ size?: number; className?: string }>; value: number; label: string; accent: string }) {
  return (
    <div className="flex flex-col items-center gap-0.5 py-3 text-center">
      <Icon size={13} className={accent} />
      <span className="text-xl font-bold tabular-nums tracking-tight text-ink">{value}</span>
      <span className="text-[10px] leading-none text-ink-faint">{label}</span>
    </div>
  );
}

// ── Focus skill bar ────────────────────────────────────────────────────────────

function FocusSkillBar({ value, max = 20 }: { value: number; max?: number }) {
  const pct = (value / max) * 100;
  const color = pct >= 70 ? "bg-lav" : pct >= 50 ? "bg-warn" : "bg-danger";
  return (
    <div className="flex items-center gap-2">
      <div className="h-2 flex-1 overflow-hidden rounded-full bg-hairline">
        <motion.div
          className={`h-full rounded-full ${color}`}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 1.0, ease: EASE, delay: 0.3 }}
        />
      </div>
      <span className="shrink-0 font-mono text-xs font-bold tabular-nums text-ink">
        {value.toFixed(1)}<span className="font-normal text-ink-faint">/{max}</span>
      </span>
    </div>
  );
}

// ── XP bar ────────────────────────────────────────────────────────────────────

function XPBar({ xp, level, xpToNext }: { xp: number; level: number; xpToNext: number }) {
  // XP within current level
  const XP_THRESHOLDS = [0, 100, 250, 500, 900, 1400];
  const levelStart = XP_THRESHOLDS[Math.min(level - 1, XP_THRESHOLDS.length - 1)] ?? 0;
  const xpInLevel = Math.max(0, xp - levelStart);
  const pct = Math.min(100, (xpInLevel / xpToNext) * 100);

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between">
        <span className="text-[10px] text-ink-faint">Level {level} → {level + 1}</span>
        <span className="text-[10px] font-semibold text-ink-subtle">{xp} XP</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-hairline">
        <motion.div
          className="h-full rounded-full bg-lav"
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 1.0, ease: EASE, delay: 0.4 }}
        />
      </div>
      <p className="text-[10px] text-ink-faint">{xpToNext} XP to level up</p>
    </div>
  );
}

// ── Loading skeleton ───────────────────────────────────────────────────────────

export function DashboardMissionPanelSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-3 lg:grid-cols-[1fr_260px]">
      <div className="rounded-2xl border border-hairline bg-surface-1 p-5">
        <Skeleton className="mb-4 h-4 w-32" />
        <Skeleton className="mb-2 h-6 w-3/4" />
        <Skeleton className="mb-5 h-4 w-2/3" />
        <div className="grid grid-cols-4 gap-0 divide-x divide-hairline rounded-xl border border-hairline">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="flex flex-col items-center gap-1 py-3">
              <Skeleton className="h-3 w-3" />
              <Skeleton className="h-5 w-6" />
              <Skeleton className="h-2 w-10" />
            </div>
          ))}
        </div>
        <Skeleton className="mt-4 h-8 w-32 rounded-xl" />
      </div>
      <div className="rounded-2xl border border-hairline bg-surface-1 p-5">
        <Skeleton className="mb-3 h-3 w-24" />
        <Skeleton className="mb-2 h-5 w-20" />
        <Skeleton className="mb-4 h-2 w-full rounded-full" />
        <Skeleton className="mb-3 h-3 w-24" />
        <Skeleton className="mb-2 h-2 w-full rounded-full" />
      </div>
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────

interface DashboardMissionPanelProps {
  progress: ProgressSummary;
  latestSpeech?: Speech | null;
}

export default function DashboardMissionPanel({ progress, latestSpeech = null }: DashboardMissionPanelProps) {
  // Derive the canonical next action from the shared helper
  const action = derivePracticeNextAction(progress, latestSpeech);

  // XP label is cosmetic only — keep simple local derivation
  const isFirstTime = progress.drill_attempts_count === 0;
  const hasIncompleteDrills = progress.incomplete_drills.length > 0;
  const xpLabel = isFirstTime ? "+50 XP" : hasIncompleteDrills ? "+20 XP" : "+10 XP";

  // Focus skill
  const focusSkill = progress.skill_averages
    ? deriveLowestSkill(progress.skill_averages)
    : null;

  return (
    <div className="grid grid-cols-1 gap-3 lg:grid-cols-[1fr_268px]">

      {/* ── Left: Mission + Metrics ──────────────────────────────────── */}
      <div
        className="beam-top mission-card overflow-hidden rounded-2xl border p-5"
        style={{ boxShadow: "0 0 48px -14px oklch(0.510 0.156 278 / 0.22)" }}
      >
        {/* Mission header */}
        <div className="mb-4 flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-lav">
            <Zap size={18} className="text-white" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="mb-0.5 flex items-center gap-2">
              <p className="text-eyebrow text-lav">Next Mission</p>
              <span className="rounded-full border border-lav/25 bg-lav/10 px-1.5 py-0.5 text-[10px] font-bold text-lav">
                {xpLabel}
              </span>
            </div>
            <p className="text-sm font-semibold leading-snug text-ink">{action.title}</p>
            <p className="mt-0.5 text-xs leading-relaxed text-ink-subtle">{action.description}</p>
          </div>
        </div>

        {/* 4 compact metrics */}
        <div className="mb-4 grid grid-cols-4 divide-x divide-hairline overflow-hidden rounded-xl border border-hairline bg-surface-2">
          <MetricCell icon={Mic}          value={progress.speech_count}          label="Speeches" accent="text-lav"  />
          <MetricCell icon={CheckCircle2} value={progress.feedback_ready_count}  label="Ballots"  accent="text-ok"  />
          <MetricCell icon={Target}       value={progress.drills_assigned_count} label="Drills"   accent="text-lav" />
          <MetricCell icon={Headphones}   value={progress.drill_attempts_count}  label="Attempts" accent="text-warn" />
        </div>

        {/* CTA */}
        <Button asChild size="sm" className="gap-1.5">
          <Link href={action.primaryHref}>
            {action.primaryLabel} <ArrowRight size={12} />
          </Link>
        </Button>
      </div>

      {/* ── Right: Focus Skill + XP ───────────────────────────────────── */}
      <div className="flex flex-col gap-3">

        {/* Focus skill card */}
        <div className="flex-1 rounded-2xl border border-hairline bg-surface-1 p-4">
          <p className="mb-2 text-eyebrow text-ink-faint">Current Focus</p>
          {focusSkill ? (
            <div className="flex flex-col gap-3">
              <div>
                <p className="text-sm font-semibold text-ink">{focusSkill.label}</p>
                <p className="text-xs text-ink-faint">Lowest scoring skill</p>
              </div>
              <FocusSkillBar value={focusSkill.value} />
            </div>
          ) : (
            <p className="text-xs text-ink-faint">Analyze a speech to see your focus skill.</p>
          )}
        </div>

        {/* XP + Level card */}
        <div className="rounded-2xl border border-hairline bg-surface-1 p-4">
          <div className="mb-3 flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg border border-lav/25 bg-lav/10">
              <Trophy size={13} className="text-lav" />
            </div>
            <div>
              <p className="text-xs font-semibold text-ink">Level {progress.level}</p>
              <p className="text-[10px] text-ink-faint">Practice rep</p>
            </div>
          </div>
          <XPBar xp={progress.xp} level={progress.level} xpToNext={progress.xp_to_next_level} />
        </div>

      </div>
    </div>
  );
}
