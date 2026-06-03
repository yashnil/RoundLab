"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion } from "motion/react";
import {
  Mic, CheckCircle2, Target, TrendingUp, Headphones,
  MoreHorizontal, Trash2, ArrowUpRight, ArrowRight,
  BookOpen, Zap,
} from "lucide-react";
import AppNav from "@/components/AppNav";
import MetricCard from "@/components/MetricCard";
import EmptyState from "@/components/EmptyState";
import DeleteDialog from "@/components/DeleteDialog";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  DropdownMenuRoot, DropdownMenuTrigger, DropdownMenuContent,
  DropdownMenuItem, DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import { createClient } from "@/lib/supabase";
import { apiFetch } from "@/lib/api";
import { staggerParent, staggerChild, cardHover } from "@/lib/motion";
import type { Speech, ProgressSummary } from "@/types";

const TYPE_LABEL: Record<string, string> = {
  constructive: "Constructive", rebuttal: "Rebuttal", summary: "Summary",
  final_focus: "Final Focus",  crossfire: "Crossfire",
};
const JUDGE_LABEL: Record<string, string> = {
  lay: "Lay", flow: "Flow", tech: "Tech", coach: "Coach",
};

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

type BV = "default" | "indigo" | "green" | "amber" | "red";

function speechStatus(s: Speech): { label: string; variant: BV } {
  if (s.status === "error")        return { label: "Error",          variant: "red"    };
  if (s.status === "done")         return { label: "Feedback ready", variant: "green"  };
  if (s.status === "analyzing")    return { label: "Analyzing…",     variant: "amber"  };
  if (s.status === "transcribing") return { label: "Transcribing…",  variant: "indigo" };
  if (s.audio_url)                 return { label: "Audio uploaded",  variant: "default"};
  return                                  { label: "Pending",         variant: "default"};
}

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, {
    month: "short", day: "numeric", year: "numeric",
  });
}

function fmtPercent(val: number | null) {
  if (val === null) return "—";
  return `${Math.round(val * 100)}%`;
}

function SpeechCard({ s, onDelete }: { s: Speech; onDelete: (s: Speech) => void }) {
  const status = speechStatus(s);

  return (
    <motion.div
      variants={staggerChild}
      {...cardHover}
    >
      <Card className="transition-colors duration-150 hover:border-hairline-strong">
        <CardContent className="flex items-center gap-4 px-5 py-4">
          <Link href={`/speech/${s.id}`} className="group flex min-w-0 flex-1 items-center gap-3.5">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-hairline bg-surface-2 transition-colors group-hover:border-lav/30 group-hover:bg-lav/5">
              <Mic size={13} className="text-ink-faint transition-colors group-hover:text-lav" />
            </div>
            <div className="flex min-w-0 flex-col gap-0.5">
              <p className="truncate text-sm font-semibold text-ink transition-colors group-hover:text-lav-hi">
                {s.title}
              </p>
              {s.topic && <p className="truncate text-xs text-ink-faint">{s.topic}</p>}
              <div className="mt-0.5 flex flex-wrap items-center gap-x-2">
                <span className="text-xs text-ink-subtle">
                  {TYPE_LABEL[s.speech_type] ?? s.speech_type}
                </span>
                {s.side       && <span className="text-xs capitalize text-ink-faint">{s.side}</span>}
                {s.judge_type && <span className="text-xs text-ink-faint">{JUDGE_LABEL[s.judge_type]} judge</span>}
                <span className="text-xs text-ink-faint">{fmtDate(s.created_at)}</span>
              </div>
              {/* Compact 5-step workflow progress dots */}
              <div className="mt-1.5 flex items-center gap-1">
                {[
                  { key: "audio",  done: !!s.audio_url,                                     label: "Audio"      },
                  { key: "tx",     done: s.status !== "pending",                             label: "Transcript" },
                  { key: "flow",   done: s.status === "analyzing" || s.status === "done",    label: "Flow"       },
                  { key: "fb",     done: s.status === "done",                                label: "Feedback"   },
                  { key: "drills", done: false /* fetched separately */,                     label: "Drills", possible: s.status === "done" },
                ].map((step, i, arr) => (
                  <div key={step.key} className="flex items-center">
                    <div
                      title={step.label}
                      className={[
                        "h-1 w-4 rounded-full transition-colors",
                        step.done
                          ? "bg-lav"
                          : (step as { possible?: boolean }).possible
                          ? "bg-lav/25"
                          : "bg-hairline",
                      ].join(" ")}
                    />
                    {i < arr.length - 1 && <div className="mx-0.5 h-px w-1 bg-hairline" />}
                  </div>
                ))}
              </div>
            </div>
          </Link>

          <div className="flex shrink-0 items-center gap-2">
            <Badge variant={status.variant}>{status.label}</Badge>
            <DropdownMenuRoot>
              <DropdownMenuTrigger asChild>
                <button
                  type="button"
                  onClick={(e) => e.preventDefault()}
                  className="flex h-6 w-6 items-center justify-center rounded-md text-ink-faint transition-colors hover:bg-surface-2 hover:text-ink-subtle"
                >
                  <MoreHorizontal size={13} />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem asChild>
                  <Link href={`/speech/${s.id}`} className="flex items-center gap-2">
                    <ArrowUpRight size={12} />
                    View session
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem destructive onSelect={() => onDelete(s)}>
                  <Trash2 size={12} />
                  Delete
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenuRoot>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}

function SpeechSkeleton() {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 px-5 py-4">
        <Skeleton className="h-8 w-8 shrink-0 rounded-lg" />
        <div className="flex flex-1 flex-col gap-1.5">
          <Skeleton className="h-3.5 w-2/5" />
          <Skeleton className="h-3 w-1/4" />
        </div>
        <Skeleton className="h-5 w-24 rounded-full" />
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const router = useRouter();
  const [userId,    setUserId]    = useState<string | null>(null);
  const [speeches,  setSpeeches]  = useState<Speech[]>([]);
  const [progress,  setProgress]  = useState<ProgressSummary | null>(null);
  const [loading,   setLoading]   = useState(true);
  const [err,       setErr]       = useState("");
  const [del,       setDel]       = useState<Speech | null>(null);
  const [deleting,  setDeleting]  = useState(false);
  const [deleteErr, setDeleteErr] = useState("");

  useEffect(() => {
    createClient().auth.getUser()
      .then(async ({ data }) => {
        if (!data.user) { router.replace("/login"); return; }
        setUserId(data.user.id);

        // Fetch speeches and progress in parallel
        const [speechesData, progressData] = await Promise.all([
          apiFetch<Speech[]>(`/speeches?user_id=${data.user.id}`),
          apiFetch<ProgressSummary>(`/users/${data.user.id}/progress`),
        ]);

        setSpeeches(speechesData);
        setProgress(progressData);
      })
      .catch(() => setErr("Could not load your data. Please refresh and try again."))
      .finally(() => setLoading(false));
  }, [router]);

  async function handleDelete() {
    if (!del || !userId) return;
    setDeleting(true);
    setDeleteErr("");
    try {
      await apiFetch(`/speeches/${del.id}?user_id=${userId}`, { method: "DELETE" });
      setSpeeches((p) => p.filter((s) => s.id !== del.id));

      // Refresh progress
      const progressData = await apiFetch<ProgressSummary>(`/users/${userId}/progress`);
      setProgress(progressData);
      setDel(null);
    } catch (e: unknown) {
      setDeleteErr(e instanceof Error ? e.message : "Could not delete this session. Please refresh and try again.");
    }
    finally { setDeleting(false); }
  }

  return (
    <>
      <AppNav />
      <main className="min-h-screen bg-canvas">
        <motion.div
          className="mx-auto flex max-w-4xl flex-col gap-7 px-6 py-9"
          variants={staggerParent(0.07, 0.05)}
          initial="hidden"
          animate="show"
        >
          {/* Page header */}
          <motion.div variants={staggerChild} className="flex flex-col gap-1">
            <h1 className="text-title text-ink">Progress Dashboard</h1>
            <p className="text-sm text-ink-subtle">
              Track your practice, improve your skills, and prepare for rounds.
            </p>
          </motion.div>

          {/* Metrics */}
          {loading ? (
            <motion.div variants={staggerChild} className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="flex items-center gap-3 rounded-xl border border-hairline bg-surface-1 px-4 py-4">
                  <Skeleton className="h-8 w-8 shrink-0 rounded-lg" />
                  <div className="flex flex-col gap-1.5">
                    <Skeleton className="h-4 w-8" />
                    <Skeleton className="h-2.5 w-16" />
                  </div>
                </div>
              ))}
            </motion.div>
          ) : !err && progress ? (
            <motion.div
              variants={staggerParent(0.06)}
              className="grid grid-cols-2 gap-3 sm:grid-cols-4"
            >
              {[
                { label: "Speeches",         value: progress.speech_count,          Icon: Mic,          iconBg: "bg-lav/10 border border-lav/20",    iconColor: "text-lav"        },
                { label: "Feedback Ready",   value: progress.feedback_ready_count,  Icon: CheckCircle2, iconBg: "bg-ok/10 border border-ok/20",     iconColor: "text-ok"         },
                { label: "Drills Assigned",  value: progress.drills_assigned_count, Icon: Target,       iconBg: "bg-indigo/10 border border-indigo/20", iconColor: "text-indigo" },
                { label: "Drill Attempts",   value: progress.drill_attempts_count,  Icon: Headphones,   iconBg: "bg-amber/10 border border-amber/20",   iconColor: "text-amber"  },
              ].map((m) => (
                <motion.div key={m.label} variants={staggerChild}>
                  <MetricCard {...m} />
                </motion.div>
              ))}
            </motion.div>
          ) : null}

          {/* Error */}
          {!loading && err && (
            <motion.div variants={staggerChild}>
              <Card><CardContent className="py-8 text-center text-sm text-danger">{err}</CardContent></Card>
            </motion.div>
          )}

          {/* Empty state */}
          {!loading && !err && speeches.length === 0 && (
            <motion.div variants={staggerChild}>
              <EmptyState
                Icon={Mic}
                title="Ready to start practicing?"
                description="Record your first Public Forum speech and get judge-style feedback on your arguments, weighing, extensions, and drops. You'll receive personalized drills to improve your weakest skills."
                action={{ label: "Record Your First Speech", href: "/session" }}
              />
            </motion.div>
          )}

          {/* Recommended Next Practice card */}
          {!loading && !err && progress && progress.incomplete_drills.length > 0 && (
            <motion.div variants={staggerChild}>
              <Card className="border-lav/20 bg-lav/5">
                <CardContent className="flex flex-col gap-4 px-5 py-5">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex flex-col gap-1">
                      <div className="flex items-center gap-2">
                        <Zap size={14} className="text-lav" />
                        <p className="text-eyebrow text-lav">Recommended Next Practice</p>
                      </div>
                      <p className="text-sm font-semibold text-ink">{progress.incomplete_drills[0].title}</p>
                      <div className="mt-1 flex flex-wrap items-center gap-2">
                        <Badge variant={(SKILL_LABELS[progress.incomplete_drills[0].skill_target]?.variant as "indigo") || "default"}>
                          {SKILL_LABELS[progress.incomplete_drills[0].skill_target]?.label || progress.incomplete_drills[0].skill_target}
                        </Badge>
                        <Badge variant="default" className="capitalize">{progress.incomplete_drills[0].difficulty}</Badge>
                        <span className="text-xs text-ink-subtle">From: {progress.incomplete_drills[0].speech_title}</span>
                      </div>
                    </div>
                    <Button asChild size="sm" className="shrink-0 gap-1.5">
                      <Link href={`/speech/${progress.incomplete_drills[0].speech_id}`}>
                        Practice Now
                        <ArrowRight size={11} />
                      </Link>
                    </Button>
                  </div>

                  {progress.incomplete_drills.length > 1 && (
                    <p className="text-xs text-ink-subtle">
                      +{progress.incomplete_drills.length - 1} more drill{progress.incomplete_drills.length - 1 !== 1 ? "s" : ""} to practice
                    </p>
                  )}
                </CardContent>
              </Card>
            </motion.div>
          )}

          {/* Skill breakdown */}
          {!loading && !err && progress && progress.skill_averages && (
            <motion.div variants={staggerChild} className="flex flex-col gap-3">
              <div className="flex items-center gap-2">
                <p className="text-eyebrow text-ink-subtle">Skill Breakdown</p>
                <span className="rounded-full border border-hairline bg-surface-2 px-1.5 py-0.5 text-xs text-ink-faint">
                  Average across {progress.feedback_ready_count} speech{progress.feedback_ready_count !== 1 ? "es" : ""}
                </span>
              </div>
              <Card>
                <CardContent className="grid grid-cols-1 gap-4 px-5 py-5 sm:grid-cols-2">
                  {[
                    { key: "clash", label: "Clash", max: 20 },
                    { key: "weighing", label: "Impact Weighing", max: 20 },
                    { key: "extensions", label: "Extensions", max: 20 },
                    { key: "drops", label: "Drop Prevention", max: 20 },
                    { key: "judge_adaptation", label: "Judge Adaptation", max: 20 },
                  ].map((skill) => {
                    const value = progress.skill_averages![skill.key as keyof typeof progress.skill_averages];
                    const pct = (value / skill.max) * 100;
                    return (
                      <div key={skill.key} className="flex flex-col gap-1.5">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-medium text-ink-subtle">{skill.label}</span>
                          <span className="text-xs font-bold text-ink">{value.toFixed(1)}<span className="text-ink-faint">/{skill.max}</span></span>
                        </div>
                        <div className="h-1.5 overflow-hidden rounded-full bg-hairline">
                          <div
                            className="h-full rounded-full bg-lav transition-all"
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                  {progress.drill_completion_rate !== null && (
                    <div className="flex flex-col gap-1.5 sm:col-span-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-medium text-ink-subtle">Drill Completion Rate</span>
                        <span className="text-xs font-bold text-ink">{fmtPercent(progress.drill_completion_rate)}</span>
                      </div>
                      <div className="h-1.5 overflow-hidden rounded-full bg-hairline">
                        <div
                          className="h-full rounded-full bg-ok transition-all"
                          style={{ width: `${(progress.drill_completion_rate || 0) * 100}%` }}
                        />
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            </motion.div>
          )}

          {/* Help state for drills */}
          {!loading && !err && progress && progress.drills_assigned_count === 0 && progress.feedback_ready_count > 0 && (
            <motion.div variants={staggerChild}>
              <Card className="border-amber/20 bg-amber/5">
                <CardContent className="flex items-start gap-3 px-5 py-4">
                  <BookOpen size={14} className="mt-0.5 shrink-0 text-amber" />
                  <div className="flex flex-1 flex-col gap-1">
                    <p className="text-sm font-semibold text-ink">Generate drills to unlock personalized practice</p>
                    <p className="text-xs text-ink-subtle">
                      You have feedback on {progress.feedback_ready_count} speech{progress.feedback_ready_count !== 1 ? "es" : ""}. Open a session and click "Generate Drills" to get 3 personalized exercises targeting your weakest skills.
                    </p>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )}

          {/* Skeleton list */}
          {loading && (
            <motion.div variants={staggerChild} className="flex flex-col gap-1.5">
              {Array.from({ length: 3 }).map((_, i) => <SpeechSkeleton key={i} />)}
            </motion.div>
          )}

          {/* Speech list */}
          {!loading && !err && speeches.length > 0 && (
            <motion.section variants={staggerChild} className="flex flex-col gap-3">
              <div className="flex items-center gap-2">
                <p className="text-eyebrow text-ink-subtle">Recent Sessions</p>
                <span className="rounded-full border border-hairline bg-surface-2 px-1.5 py-0.5 text-xs text-ink-faint">
                  {speeches.length}
                </span>
              </div>
              <motion.div
                className="flex flex-col gap-1.5"
                variants={staggerParent(0.05)}
                initial="hidden"
                animate="show"
              >
                {speeches.map((s) => (
                  <SpeechCard key={s.id} s={s} onDelete={setDel} />
                ))}
              </motion.div>
            </motion.section>
          )}
        </motion.div>
      </main>

      <DeleteDialog
        open={del !== null}
        onOpenChange={(o) => { if (!o && !deleting) { setDel(null); setDeleteErr(""); } }}
        title="Delete session?"
        description={`"${del?.title}" will be permanently deleted along with its transcript, flow, feedback, and drills.`}
        onConfirm={handleDelete}
        isDeleting={deleting}
        error={deleteErr}
      />
    </>
  );
}
