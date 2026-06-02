"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion } from "motion/react";
import {
  Mic, CheckCircle2, Clock, TrendingUp,
  MoreHorizontal, Trash2, ArrowUpRight,
} from "lucide-react";
import AppNav from "@/components/AppNav";
import MetricCard from "@/components/MetricCard";
import EmptyState from "@/components/EmptyState";
import DeleteDialog from "@/components/DeleteDialog";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  DropdownMenuRoot, DropdownMenuTrigger, DropdownMenuContent,
  DropdownMenuItem, DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import { createClient } from "@/lib/supabase";
import { apiFetch } from "@/lib/api";
import { staggerParent, staggerChild, cardHover } from "@/lib/motion";
import type { Speech } from "@/types";

const TYPE_LABEL: Record<string, string> = {
  constructive: "Constructive", rebuttal: "Rebuttal", summary: "Summary",
  final_focus: "Final Focus",  crossfire: "Crossfire",
};
const JUDGE_LABEL: Record<string, string> = {
  lay: "Lay", flow: "Flow", tech: "Tech", coach: "Coach",
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
  const [speeches, setSpeeches] = useState<Speech[]>([]);
  const [loading,  setLoading]  = useState(true);
  const [err,      setErr]      = useState("");
  const [del,      setDel]      = useState<Speech | null>(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    createClient().auth.getUser()
      .then(({ data }) => {
        if (!data.user) { router.replace("/login"); return; }
        return apiFetch<Speech[]>(`/speeches?user_id=${data.user.id}`);
      })
      .then((rows) => { if (rows) setSpeeches(rows); })
      .catch(() => setErr("Could not load speeches. Is the backend running?"))
      .finally(() => setLoading(false));
  }, [router]);

  async function handleDelete() {
    if (!del) return;
    setDeleting(true);
    try {
      await apiFetch(`/speeches/${del.id}`, { method: "DELETE" });
      setSpeeches((p) => p.filter((s) => s.id !== del.id));
      setDel(null);
    } catch { /* keep open */ }
    finally { setDeleting(false); }
  }

  const feedbackReady = speeches.filter((s) => s.status === "done").length;
  const withAudio     = speeches.filter((s) => !!s.audio_url).length;
  const inProgress    = speeches.filter((s) =>
    ["transcribing", "analyzing"].includes(s.status)).length;

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
            <h1 className="text-title text-ink">My Sessions</h1>
            <p className="text-sm text-ink-subtle">
              Record, transcribe, and get judge-style feedback on your rounds.
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
          ) : !err && speeches.length > 0 ? (
            <motion.div
              variants={staggerParent(0.06)}
              className="grid grid-cols-2 gap-3 sm:grid-cols-4"
            >
              {[
                { label: "Sessions",       value: speeches.length, Icon: TrendingUp,  iconBg: "bg-lav/10 border border-lav/20",    iconColor: "text-lav"        },
                { label: "Recorded",       value: withAudio,       Icon: Mic,         iconBg: "bg-surface-2 border border-hairline", iconColor: "text-ink-subtle" },
                { label: "Feedback Ready", value: feedbackReady,   Icon: CheckCircle2, iconBg: "bg-ok/10 border border-ok/20",     iconColor: "text-ok"         },
                { label: "In Progress",    value: inProgress,      Icon: Clock,       iconBg: "bg-warn/10 border border-warn/20",   iconColor: "text-warn"       },
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
                title="No sessions yet"
                description="Record your first speech and get judge-style feedback in minutes."
                action={{ label: "Start Your First Session", href: "/session" }}
              />
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
        onOpenChange={(o) => { if (!o && !deleting) setDel(null); }}
        title="Delete session?"
        description={`"${del?.title}" will be permanently deleted along with its transcript, flow, and feedback.`}
        onConfirm={handleDelete}
        isDeleting={deleting}
      />
    </>
  );
}
