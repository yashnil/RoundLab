"use client";

/**
 * /pilot — Internal pilot readiness dashboard.
 *
 * Shows per-user analytics for a single student going through the pilot loop.
 * No cross-user data is exposed here — all queries are scoped to the current user.
 * This page is dev/internal only; do not surface it in main nav.
 */

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion } from "motion/react";
import {
  ArrowLeft, BarChart2, TrendingUp, TrendingDown, Minus,
  CheckCircle2, Circle, MessageSquare, Zap,
} from "lucide-react";
import AppNav from "@/components/AppNav";
import PilotChecklist from "@/components/PilotChecklist";
import SkillTrendCard from "@/components/SkillTrendCard";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { createClient } from "@/lib/supabase";
import { apiFetch } from "@/lib/api";
import { staggerParent, staggerChild } from "@/lib/motion";
import type { ProgressSummary, PilotSummary, PilotAggregate } from "@/types";

function StatCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="flex flex-col gap-1 rounded-xl border border-hairline bg-surface-1 p-3">
      <p className="text-[10px] font-medium uppercase tracking-wide text-ink-faint">{label}</p>
      <p className="text-xl font-bold tabular-nums text-ink">{value}</p>
      {sub && <p className="text-[10px] text-ink-faint">{sub}</p>}
    </div>
  );
}

function PilotFlag({ label, done }: { label: string; done: boolean }) {
  return (
    <div className="flex items-center gap-2">
      {done
        ? <CheckCircle2 size={13} className="shrink-0 text-ok" />
        : <Circle size={13} className="shrink-0 text-ink-faint" />
      }
      <span className={`text-xs ${done ? "text-ok font-medium" : "text-ink-subtle"}`}>{label}</span>
    </div>
  );
}

function fmtRating(r: number | null) {
  if (r === null) return "—";
  return r >= 0.75 ? "Positive" : r >= 0.4 ? "Mixed" : "Negative";
}

const SKILL_META = [
  { key: "clash",            label: "Clash",            icon: "⚔", max: 20 },
  { key: "weighing",         label: "Impact Weighing",  icon: "⚖", max: 20 },
  { key: "extensions",       label: "Extensions",       icon: "↗", max: 20 },
  { key: "drops",            label: "Drop Prevention",  icon: "🛡", max: 20 },
  { key: "judge_adaptation", label: "Judge Adaptation", icon: "👁", max: 20 },
];

function SkillsSkeleton() {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
      {Array.from({ length: 5 }).map((_, i) => (
        <Skeleton key={i} className="h-24 rounded-xl" />
      ))}
    </div>
  );
}

export default function PilotPage() {
  const router = useRouter();
  const [userId, setUserId] = useState<string | null>(null);
  const [progress, setProgress] = useState<ProgressSummary | null>(null);
  const [pilotSummary, setPilotSummary] = useState<PilotSummary | null>(null);
  const [pilotAggregate, setPilotAggregate] = useState<PilotAggregate | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    createClient().auth.getUser().then(async ({ data }) => {
      if (!data.user) { router.replace("/login"); return; }
      const uid = data.user.id;
      setUserId(uid);

      try {
        const [prog, summary, agg] = await Promise.all([
          apiFetch<ProgressSummary>(`/users/${uid}/progress`),
          apiFetch<PilotSummary>(`/users/${uid}/pilot-summary`),
          apiFetch<PilotAggregate>(`/pilot?user_id=${uid}`),
        ]);
        setProgress(prog);
        setPilotSummary(summary);
        setPilotAggregate(agg);
      } catch (e: unknown) {
        setErr(e instanceof Error ? e.message : "Could not load pilot data.");
      }
    }).catch(() => setErr("Auth error. Please refresh."))
      .finally(() => setLoading(false));
  }, [router]);

  return (
    <>
      <AppNav />
      <main className="min-h-screen bg-canvas">
        <motion.div
          className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-8 sm:px-6"
          variants={staggerParent(0.07, 0.05)}
          initial="hidden"
          animate="show"
        >
          {/* Header */}
          <motion.div variants={staggerChild}>
            <Link href="/dashboard" className="flex w-fit items-center gap-1.5 text-xs text-ink-faint hover:text-ink mb-4">
              <ArrowLeft size={12} />
              Back to dashboard
            </Link>
            <div className="flex items-center gap-2.5">
              <BarChart2 size={18} className="text-lav" />
              <h1 className="text-2xl font-bold text-ink">Pilot Dashboard</h1>
              <span className="rounded-full border border-lav/20 bg-lav/5 px-2 py-0.5 text-[10px] font-medium text-lav">
                Dev only
              </span>
            </div>
            <p className="mt-1 text-sm text-ink-subtle">
              Your personal pilot metrics — practice loop health and skill progress.
            </p>
          </motion.div>

          {loading && (
            <motion.div variants={staggerChild} className="flex flex-col gap-4">
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} className="h-20 rounded-xl" />)}
              </div>
              <SkillsSkeleton />
            </motion.div>
          )}

          {!loading && err && (
            <motion.div variants={staggerChild}>
              <Card><CardContent className="py-8 text-center text-sm text-danger">{err}</CardContent></Card>
            </motion.div>
          )}

          {/* Activity stats */}
          {!loading && pilotAggregate && (
            <motion.div variants={staggerChild}>
              <span className="section-stamp mb-3 block">Activity</span>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <StatCard label="Speeches" value={pilotAggregate.speeches_uploaded} sub={`${pilotAggregate.analyzed_speeches} analyzed`} />
                <StatCard label="Drills assigned" value={pilotAggregate.drills_assigned} sub={`${pilotAggregate.drill_attempts} attempts`} />
                <StatCard label="Re-records" value={pilotAggregate.rerecords} />
                <StatCard label="Feedback ratings" value={pilotAggregate.feedback_ratings} sub={pilotAggregate.average_feedback_usefulness !== null ? `Avg: ${fmtRating(pilotAggregate.average_feedback_usefulness)}` : "None yet"} />
              </div>
            </motion.div>
          )}

          {/* Pilot flags */}
          {!loading && pilotSummary && (
            <motion.div variants={staggerChild}>
              <span className="section-stamp mb-3 block">Pilot loop flags</span>
              <Card>
                <CardContent className="grid grid-cols-1 gap-2 px-5 py-4 sm:grid-cols-2">
                  <PilotFlag label="Returned for second speech" done={pilotSummary.return_for_second_speech} />
                  <PilotFlag label="Completed at least one drill" done={pilotSummary.completed_one_drill} />
                  <PilotFlag label="Rated feedback" done={pilotSummary.feedback_rating_count > 0} />
                  <PilotFlag label="Rated a drill" done={pilotSummary.drill_rating_count > 0} />
                  <PilotFlag label="Viewed improvement report" done={pilotSummary.comparison_count > 0} />
                </CardContent>
              </Card>
            </motion.div>
          )}

          {/* Pilot checklist */}
          {!loading && progress && (
            <motion.div variants={staggerChild}>
              <span className="section-stamp mb-3 block">Full loop checklist</span>
              <Card>
                <CardContent className="px-5 py-5">
                  <PilotChecklist progress={progress} pilot={pilotSummary} />
                </CardContent>
              </Card>
            </motion.div>
          )}

          {/* Skill trends */}
          {!loading && pilotSummary?.skill_trends && (
            <motion.div variants={staggerChild}>
              <span className="section-stamp mb-3 block">Skill trends</span>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                {SKILL_META.map(({ key, label, icon, max }) => {
                  const trend = pilotSummary.skill_trends![key as keyof typeof pilotSummary.skill_trends];
                  return <SkillTrendCard key={key} label={label} icon={icon} max={max} trend={trend} />;
                })}
              </div>
            </motion.div>
          )}

          {/* Common issues */}
          {!loading && pilotSummary && pilotSummary.common_issues.length > 0 && (
            <motion.div variants={staggerChild}>
              <span className="section-stamp mb-3 block">Common issues (from feedback)</span>
              <Card>
                <CardContent className="flex flex-col gap-2 px-5 py-4">
                  {pilotSummary.common_issues.map((issue, i) => (
                    <div key={i} className="flex items-start gap-2">
                      <Zap size={11} className="mt-0.5 shrink-0 text-lav" />
                      <p className="text-xs text-ink-subtle">{issue}</p>
                    </div>
                  ))}
                </CardContent>
              </Card>
            </motion.div>
          )}

          {/* Drop-off insight */}
          {!loading && pilotAggregate && (
            <motion.div variants={staggerChild}>
              <span className="section-stamp mb-3 block">Drop-off point</span>
              <Card>
                <CardContent className="px-5 py-4">
                  <div className="flex items-center gap-2">
                    <MessageSquare size={13} className="text-lav" />
                    <p className="text-xs font-medium text-ink">
                      {pilotAggregate.common_drop_off === "no_speech_yet" && "No speech recorded yet — loop hasn't started."}
                      {pilotAggregate.common_drop_off === "uploaded_not_analyzed" && "Speech uploaded but not analyzed — stuck at transcription/analysis."}
                      {pilotAggregate.common_drop_off === "assigned_drills_not_attempted" && "Drills assigned but none attempted — stuck before first drill rep."}
                      {pilotAggregate.common_drop_off === "practicing_drills_no_rerecord" && "Practicing drills but haven't re-recorded — encourage a re-record."}
                      {pilotAggregate.common_drop_off === "active" && "Fully active through the practice loop."}
                    </p>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )}

          {/* Pilot protocol reminder */}
          <motion.div variants={staggerChild}>
            <Card className="border-lav/10 bg-lav/5">
              <CardContent className="px-5 py-4">
                <p className="mb-2 text-xs font-semibold text-lav">Recommended pilot protocol</p>
                <ol className="flex flex-col gap-1.5 pl-1">
                  {[
                    "Record one PF speech (any type).",
                    "Open your flow report and review feedback.",
                    "Complete one recommended drill.",
                    "Re-record the speech.",
                    "View your improvement report.",
                    "Rate the feedback usefulness.",
                  ].map((step, i) => (
                    <li key={i} className="flex items-start gap-2 text-xs text-ink-subtle">
                      <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border border-lav/20 text-[9px] font-bold text-lav">{i + 1}</span>
                      {step}
                    </li>
                  ))}
                </ol>
              </CardContent>
            </Card>
          </motion.div>

        </motion.div>
      </main>
    </>
  );
}
