"use client";

/**
 * Drill Practice Page — /drills/[id]
 *
 * A focused training room for a single drill.
 * Shows the exercise prompt, instructions, success criteria, and recording UI.
 * Loads drill data + past attempts, then lets the student record and submit.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { motion, AnimatePresence } from "motion/react";
import {
  ArrowLeft, Check, CheckSquare, Square,
  Target, BookOpen, Zap, Clock, Headphones,
  ChevronDown, ChevronUp, ThumbsUp, AlertCircle, RefreshCw,
} from "lucide-react";
import AppNav from "@/components/AppNav";
import CoachMarginNote from "@/components/CoachMarginNote";
import RoundLabJourneyRail from "@/components/RoundLabJourneyRail";
import DrillAttemptRecorder from "@/components/DrillAttemptRecorder";
import DrillRating from "@/components/DrillRating";
import ConfusionReport from "@/components/ConfusionReport";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { createClient } from "@/lib/supabase";
import { apiFetch } from "@/lib/api";
import { resolveAudioUrl } from "@/lib/audio";
import { fadeUp, EASE } from "@/lib/motion";
import type { Drill, DrillAttempt, DrillRatingRow, DrillStatus } from "@/types";

// ── Helpers ────────────────────────────────────────────────────────────────────

const SKILL_LABELS: Record<string, { label: string; variant: "indigo" | "blue" | "red" | "green" | "amber" | "violet" | "orange" | "default" }> = {
  weighing:         { label: "Impact Weighing",  variant: "indigo"  },
  warranting:       { label: "Warranting",       variant: "blue"    },
  drops:            { label: "Drop Prevention",  variant: "red"     },
  extensions:       { label: "Extensions",       variant: "green"   },
  evidence:         { label: "Evidence Use",     variant: "amber"   },
  clash:            { label: "Clash",            variant: "violet"  },
  judge_adaptation: { label: "Judge Adaptation", variant: "orange"  },
};

const DIFFICULTY_BADGE: Record<string, { label: string; variant: "green" | "amber" | "red" }> = {
  beginner:     { label: "Beginner",     variant: "green" },
  intermediate: { label: "Intermediate", variant: "amber" },
  advanced:     { label: "Advanced",     variant: "red"   },
};

function formatTimeLimit(seconds: number | null | undefined): string {
  if (!seconds) return "";
  if (seconds < 60) return `${seconds}s`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return s === 0 ? `${m}m` : `${m}m ${s}s`;
}

function fmtDate(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

// ── Loading skeleton ────────────────────────────────────────────────────────────

function PageSkeleton() {
  return (
    <div className="flex flex-col gap-5">
      <Skeleton className="h-4 w-32 rounded" />
      <div className="flex flex-col gap-2">
        <Skeleton className="h-7 w-3/4 rounded" />
        <Skeleton className="h-4 w-1/2 rounded" />
      </div>
      <Skeleton className="h-24 w-full rounded-xl" />
      <Skeleton className="h-32 w-full rounded-xl" />
      <Skeleton className="h-40 w-full rounded-xl" />
    </div>
  );
}

// ── Attempt card ───────────────────────────────────────────────────────────────

function ScoreBadge({ score }: { score: number }) {
  const band =
    score >= 90 ? { label: "Excellent", color: "text-ok bg-ok/10 border-ok/20" }
    : score >= 70 ? { label: "Solid",    color: "text-lav bg-lav/10 border-lav/20" }
    : score >= 50 ? { label: "Developing", color: "text-warn bg-warn/10 border-warn/20" }
    : { label: "Needs work", color: "text-danger bg-danger/10 border-danger/20" };
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-semibold ${band.color}`}>
      {score}/100 · {band.label}
    </span>
  );
}

function AttemptCard({ attempt, index, isLatest = false }: { attempt: DrillAttempt; index: number; isLatest?: boolean }) {
  const [showTranscript, setShowTranscript] = useState(false);
  const [audioSrc, setAudioSrc] = useState<string | null>(null);
  const [audioErr, setAudioErr] = useState(false);

  useEffect(() => {
    if (!attempt.audio_url) return;
    const sb = createClient();
    resolveAudioUrl(attempt.audio_url, sb).then((url) => {
      if (url) setAudioSrc(url);
      else setAudioErr(true);
    });
  }, [attempt.audio_url]);
  const fb = attempt.feedback as Record<string, unknown> | null;
  const feedbackSummary = fb ? String(fb.feedback_summary ?? fb.summary ?? fb.note ?? "") : "";
  const strengths = fb ? (fb.strengths as string[] | undefined) ?? [] : [];
  const improvements = fb ? (fb.improvements as string[] | undefined) ?? [] : [];
  const nextInstruction = fb ? String(fb.next_instruction ?? "") : "";
  const metCriteria = fb ? Boolean(fb.met_success_criteria) : null;
  const shouldRetry = fb ? Boolean(fb.should_retry) : null;
  const hasFullFeedback = feedbackSummary.length > 0;
  const transcriptExcerpt = attempt.response
    ? attempt.response.length > 220
      ? attempt.response.slice(0, 220).trimEnd() + "…"
      : attempt.response
    : null;

  const scoreAttr =
    attempt.score !== null && attempt.score >= 70 ? { "data-score-good": true } :
    attempt.score !== null && attempt.score >= 50 ? { "data-score-warn": true } : {};

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, delay: index * 0.05, ease: EASE }}
      className={isLatest ? "rep-ticket flex flex-col gap-3 p-4" : "flex flex-col gap-3 rounded-lg border border-hairline bg-surface-2 p-4"}
      {...(isLatest ? scoreAttr : {})}
    >
      {/* Header row */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5">
          <Headphones size={12} className="text-lav" />
          <span className="text-xs font-semibold text-ink">
            {isLatest ? "Latest attempt" : `Attempt ${index + 1}`}
          </span>
          {metCriteria !== null && (
            metCriteria
              ? <span className="ml-1 flex items-center gap-0.5 text-[10px] text-ok"><Check size={10} />Criteria met</span>
              : <span className="ml-1 flex items-center gap-0.5 text-[10px] text-ink-faint"><AlertCircle size={10} />Criteria not met</span>
          )}
        </div>
        <span className="text-[10px] text-ink-faint">{fmtDate(attempt.created_at)}</span>
      </div>

      {/* Score badge */}
      {attempt.score !== null && (
        <div className="flex items-center gap-2">
          <ScoreBadge score={attempt.score} />
          {shouldRetry && (
            <span className="text-[10px] text-ink-faint">· retry recommended</span>
          )}
        </div>
      )}

      {/* Audio playback */}
      {attempt.audio_url && (
        audioSrc ? (
          <audio
            src={audioSrc}
            controls
            className="h-8 w-full"
            onError={() => setAudioErr(true)}
            aria-label={`Drill attempt ${index + 1} playback`}
          />
        ) : audioErr ? (
          <p className="text-[10px] text-warn">
            Audio could not be loaded. The attempt was saved, but playback is unavailable.
          </p>
        ) : (
          <div className="h-8 flex items-center">
            <span className="text-[10px] text-ink-faint">Loading audio…</span>
          </div>
        )
      )}

      {/* Full feedback */}
      {hasFullFeedback && (
        <div className="flex flex-col gap-2 rounded-lg border border-lav/20 bg-lav/5 px-3 py-3">
          <p className="text-xs leading-relaxed text-ink">{feedbackSummary}</p>

          {strengths.length > 0 && (
            <div className="flex flex-col gap-1">
              <div className="flex items-center gap-1 text-[10px] font-semibold text-ok">
                <ThumbsUp size={9} />
                Strengths
              </div>
              <ul className="flex flex-col gap-0.5 pl-1">
                {strengths.map((s, i) => (
                  <li key={i} className="text-[11px] leading-snug text-ink-muted">· {s}</li>
                ))}
              </ul>
            </div>
          )}

          {improvements.length > 0 && (
            <div className="flex flex-col gap-1">
              <div className="flex items-center gap-1 text-[10px] font-semibold text-warn">
                <AlertCircle size={9} />
                Improvements
              </div>
              <ul className="flex flex-col gap-0.5 pl-1">
                {improvements.map((s, i) => (
                  <li key={i} className="text-[11px] leading-snug text-ink-muted">· {s}</li>
                ))}
              </ul>
            </div>
          )}

          {nextInstruction && (
            <div className="mt-1 border-t border-lav/10 pt-2">
              <p className="text-[10px] font-semibold text-ink-subtle">Next step</p>
              <p className="text-[11px] leading-snug text-ink-muted">{nextInstruction}</p>
            </div>
          )}
        </div>
      )}

      {/* Transcript excerpt */}
      {transcriptExcerpt && (
        <div className="flex flex-col gap-1">
          <button
            type="button"
            onClick={() => setShowTranscript((v) => !v)}
            className="flex items-center gap-1 text-[10px] text-ink-faint hover:text-ink-subtle"
          >
            {showTranscript ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
            {showTranscript ? "Hide transcript" : "Show transcript"}
          </button>
          {showTranscript && (
            <p className="rounded-md bg-surface-3 px-3 py-2 text-[11px] leading-snug text-ink-muted">
              {attempt.response}
            </p>
          )}
        </div>
      )}

      {/* Fallback when no scoring yet */}
      {attempt.score === null && !hasFullFeedback && (
        <p className="text-[10px] text-ink-faint">
          Attempt saved — practice your speech again to track improvement.
        </p>
      )}
    </motion.div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────────

export default function DrillPage() {
  const { id: drillId } = useParams<{ id: string }>();
  const router = useRouter();

  const [userId,      setUserId]      = useState<string | null>(null);
  const [drill,       setDrill]       = useState<Drill | null>(null);
  const [attempts,    setAttempts]    = useState<DrillAttempt[]>([]);
  const [drillRating, setDrillRating] = useState<DrillRatingRow | null>(null);
  const [loading,     setLoading]     = useState(true);
  const [err,         setErr]         = useState("");
  const [attemptsErr, setAttemptsErr] = useState("");
  const [updatingStatus, setUpdatingStatus] = useState(false);
  const reloadingRef = useRef(false);

  // ── Load data ──────────────────────────────────────────────────────────────

  useEffect(() => {
    createClient().auth.getUser().then(async ({ data }) => {
      if (!data.user) { router.replace("/login"); return; }
      const uid = data.user.id;
      setUserId(uid);

      // Fetch drill — required; failure blocks the page
      let drillData: Drill;
      try {
        drillData = await apiFetch<Drill>(`/drills/${drillId}?user_id=${uid}`);
        setDrill(drillData);
      } catch (e: unknown) {
        setErr(e instanceof Error ? e.message : "Could not load drill.");
        return;
      }

      // Fetch attempts — optional; failure shows inline error instead of blocking page
      try {
        const attemptsData = await apiFetch<DrillAttempt[]>(`/drills/${drillId}/attempts?user_id=${uid}`);
        setAttempts(attemptsData);
      } catch {
        setAttemptsErr("Couldn't load drill attempts. Try refreshing this drill.");
      }

      // Fetch existing drill rating (best-effort)
      try {
        const ratingData = await apiFetch<DrillRatingRow | null>(`/drills/${drillId}/rating?user_id=${uid}`);
        if (ratingData) setDrillRating(ratingData);
      } catch { /* no-op */ }
    }).catch(() => setErr("Auth error. Please refresh."))
      .finally(() => setLoading(false));
  }, [drillId, router]);

  // ── Reload attempts (safe to call from retry button) ───────────────────────

  const reloadAttempts = useCallback(async () => {
    if (!userId || reloadingRef.current) return;
    reloadingRef.current = true;
    setAttemptsErr("");
    try {
      const fresh = await apiFetch<DrillAttempt[]>(`/drills/${drillId}/attempts?user_id=${userId}`);
      setAttempts(fresh);
    } catch (e: unknown) {
      setAttemptsErr("Couldn't load drill attempts. Try refreshing this drill.");
    } finally {
      reloadingRef.current = false;
    }
  }, [userId, drillId]);

  // ── Status update ──────────────────────────────────────────────────────────

  const updateStatus = useCallback(async (status: DrillStatus) => {
    if (!userId || !drill) return;
    setUpdatingStatus(true);
    try {
      const updated = await apiFetch<Drill>(`/drills/${drillId}?user_id=${userId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });
      setDrill(updated);
    } catch { /* silently ignore */ }
    finally { setUpdatingStatus(false); }
  }, [userId, drill, drillId]);

  // ── After attempt saved ────────────────────────────────────────────────────

  const handleAttemptSaved = useCallback(async (savedAttempt: DrillAttempt) => {
    // Immediately show the returned attempt so it appears before the reload
    setAttempts((prev) => [savedAttempt, ...prev]);
    // Reload to get the full authoritative list
    await reloadAttempts();
    // Auto-advance status to attempted if still assigned
    if (drill?.status === "assigned") {
      await updateStatus("attempted");
    }
  }, [reloadAttempts, drill?.status, updateStatus]);

  // ── Render ─────────────────────────────────────────────────────────────────

  const skill = drill ? (SKILL_LABELS[drill.skill_target] ?? { label: drill.skill_target, variant: "default" as const }) : null;
  const diff  = drill ? (DIFFICULTY_BADGE[drill.difficulty] ?? DIFFICULTY_BADGE.beginner) : null;
  const steps = drill?.instructions?.split("\n").filter(Boolean) ?? [];
  const tlLabel = formatTimeLimit(drill?.time_limit_seconds);

  return (
    <>
      <AppNav />
      <main className="min-h-screen bg-canvas">
        <div className="mx-auto flex max-w-3xl flex-col gap-6 px-4 py-8 sm:px-6">

          {/* ── Back link ─────────────────────────────────────────────── */}
          {drill && (
            <Link
              href={`/speech/${drill.speech_id}`}
              className="flex w-fit items-center gap-1.5 text-xs text-ink-faint transition-colors hover:text-ink"
            >
              <ArrowLeft size={12} />
              Back to speech report
            </Link>
          )}

          {/* ── Loading / Error ────────────────────────────────────────── */}
          {loading && <PageSkeleton />}

          {!loading && err && (
            <div className="rounded-xl border border-danger/20 bg-danger/5 px-4 py-6 text-center">
              <p className="text-sm text-danger">{err}</p>
              <Link href="/dashboard" className="mt-3 inline-block text-xs text-ink-faint underline">
                Back to dashboard
              </Link>
            </div>
          )}

          {/* ── Drill content ──────────────────────────────────────────── */}
          {!loading && drill && userId && (
            <AnimatePresence mode="wait">
              <motion.div
                key="content"
                variants={{ hidden: { opacity: 0 }, show: { opacity: 1 } }}
                initial="hidden"
                animate="show"
                className="flex flex-col gap-6"
              >

                {/* Header */}
                <motion.div {...fadeUp(0)} className="flex flex-col gap-3">
                  {/* Status + order */}
                  <div className="flex items-center gap-2">
                    <span className="flex h-6 w-6 items-center justify-center rounded-full bg-lav text-[10px] font-bold text-white">
                      {drill.order}
                    </span>
                    <span className="flex items-center gap-1.5 text-xs text-ink-faint">
                      <span className={`h-1.5 w-1.5 rounded-full ${
                        drill.status === "completed" ? "bg-ok"
                        : drill.status === "attempted" ? "bg-warn"
                        : "bg-ink-faint"
                      }`} />
                      {drill.status === "completed" ? "Completed"
                       : drill.status === "attempted" ? "Attempted"
                       : "Not started"}
                    </span>
                  </div>

                  <h1 className="text-title text-ink">{drill.title}</h1>

                  {/* Badges */}
                  <div className="flex flex-wrap items-center gap-2">
                    {skill && <Badge variant={skill.variant as "indigo"}>{skill.label}</Badge>}
                    {diff  && <Badge variant={diff.variant}>{diff.label}</Badge>}
                    {tlLabel && (
                      <span className="flex items-center gap-1 rounded-full border border-hairline bg-surface-2 px-2.5 py-1 text-[10px] text-ink-subtle">
                        <Clock size={10} />
                        {tlLabel}
                      </span>
                    )}
                  </div>
                </motion.div>

                {/* Why this drill */}
                {drill.source_weakness && (
                  <motion.div {...fadeUp(0.07)}>
                    <CoachMarginNote
                      type="warn"
                      label="Why this drill"
                      note={`Targeting: ${drill.source_weakness}`}
                    />
                  </motion.div>
                )}

                {/* Description */}
                {drill.description && (
                  <motion.div {...fadeUp(0.1)}>
                    <p className="text-sm leading-relaxed text-ink-subtle">{drill.description}</p>
                  </motion.div>
                )}

                {/* Exercise prompt */}
                <motion.div {...fadeUp(0.13)} className="flex flex-col gap-2">
                  <div className="section-stamp">
                    <Target size={11} className="text-lav" />
                    Exercise prompt
                  </div>
                  <div className="rounded-xl border border-lav/20 bg-lav/5 px-5 py-4">
                    <p className="text-sm leading-relaxed text-ink">{drill.prompt}</p>
                  </div>
                </motion.div>

                {/* Instructions */}
                {steps.length > 0 && (
                  <motion.div {...fadeUp(0.16)} className="flex flex-col gap-2">
                    <div className="section-stamp">
                      <BookOpen size={11} className="text-lav" />
                      How to practice
                    </div>
                    <ol className="flex flex-col gap-2">
                      {steps.map((step, i) => (
                        <li key={i} className="flex items-start gap-3 text-sm text-ink-muted">
                          <span
                            className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-[3px] border border-hairline text-[10px] font-bold text-ink-faint"
                            style={{ fontFamily: "var(--font-jetbrains-mono)" }}
                          >
                            {i + 1}
                          </span>
                          {step.replace(/^\d+\.\s*/, "")}
                        </li>
                      ))}
                    </ol>
                  </motion.div>
                )}

                {/* Success criteria */}
                {drill.success_criteria.length > 0 && (
                  <motion.div {...fadeUp(0.19)} className="flex flex-col gap-2">
                    <div className="section-stamp">
                      <Zap size={11} className="text-lav" />
                      Success criteria
                    </div>
                    <ul className="flex flex-col gap-2">
                      {drill.success_criteria.map((criterion, i) => (
                        <li key={i} className="flex items-start gap-2 text-sm text-ink-muted">
                          {drill.status === "completed"
                            ? <CheckSquare size={14} className="mt-0.5 shrink-0 text-ok" />
                            : <Square      size={14} className="mt-0.5 shrink-0 text-ink-faint" />
                          }
                          {criterion}
                        </li>
                      ))}
                    </ul>
                  </motion.div>
                )}

                {/* ── Practice room ────────────────────────────────────── */}
                <motion.div {...fadeUp(0.22)} id="practice-room" className="flex flex-col gap-3">
                  <div className="section-stamp">
                    <span className="h-1.5 w-1.5 rounded-full bg-lav flex-shrink-0" />
                    Practice room
                  </div>

                  {drill.status === "completed" ? (
                    <div className="flex items-center gap-2 rounded-lg border border-ok/20 bg-ok/5 px-4 py-3">
                      <Check size={14} className="shrink-0 text-ok" />
                      <p className="text-sm font-medium text-ok">Drill completed — great work.</p>
                    </div>
                  ) : (
                    <div className="surface-practice">
                      <div className="border-b border-hairline px-4 py-3">
                        <span className="section-stamp">
                          Rep room
                          {tlLabel && (
                            <span className="ml-2 font-normal normal-case tracking-normal text-ink-faint">
                              target: {tlLabel}
                            </span>
                          )}
                        </span>
                        <p className="mt-1 text-[11px] text-ink-faint">
                          Speak your response aloud. Re-record as many times as you need.
                        </p>
                      </div>
                      <div className="p-4">
                        <DrillAttemptRecorder
                          drillId={drill.id}
                          userId={userId}
                          speechId={drill.speech_id}
                          onAttemptSaved={handleAttemptSaved}
                        />
                      </div>
                    </div>
                  )}

                  {/* Status control */}
                  <div className="flex flex-wrap items-center gap-2">
                    {drill.status !== "completed" && (
                      <Button
                        size="sm"
                        variant="secondary"
                        disabled={updatingStatus}
                        onClick={() => updateStatus("completed")}
                        className="gap-1.5"
                      >
                        <Check size={12} />
                        {updatingStatus ? "Saving…" : "Mark completed"}
                      </Button>
                    )}
                    {drill.status === "assigned" && (
                      <Button
                        size="sm"
                        variant="secondary"
                        disabled={updatingStatus}
                        onClick={() => updateStatus("attempted")}
                      >
                        {updatingStatus ? "Saving…" : "Mark attempted"}
                      </Button>
                    )}
                  </div>
                </motion.div>

                {/* ── Attempts error ────────────────────────────────────── */}
                {attemptsErr && (
                  <motion.div {...fadeUp(0.25)}>
                    <div className="flex items-center justify-between gap-2 rounded-lg border border-warn/20 bg-warn/5 px-3 py-2">
                      <p className="text-xs text-warn">{attemptsErr}</p>
                      <button
                        type="button"
                        onClick={reloadAttempts}
                        className="shrink-0 text-xs font-medium text-lav hover:text-lav-hi"
                      >
                        Retry
                      </button>
                    </div>
                  </motion.div>
                )}

                {/* ── Latest Result ─────────────────────────────────────── */}
                {attempts.length > 0 && (
                  <motion.div {...fadeUp(0.26)} className="flex flex-col gap-3">
                    <div className="section-stamp">
                      <span className="h-1.5 w-1.5 rounded-full bg-lav flex-shrink-0" />
                      Latest result
                    </div>
                    <AttemptCard attempt={attempts[0]} index={0} isLatest />
                  </motion.div>
                )}

                {/* ── Drill rating — show after at least one attempt ────── */}
                {attempts.length > 0 && userId && (
                  <motion.div {...fadeUp(0.27)} className="flex flex-col gap-2">
                    <DrillRating
                      drillId={drill.id}
                      userId={userId}
                      drillAttemptId={attempts[0]?.id ?? null}
                      initialRating={drillRating?.rating ?? null}
                      onRated={setDrillRating}
                    />
                    <ConfusionReport
                      targetType="drill_feedback"
                      targetId={drill.id}
                      userId={userId}
                    />
                  </motion.div>
                )}

                {/* ── Past Attempts (collapsed list) ────────────────────── */}
                {attempts.length > 1 && (
                  <motion.div {...fadeUp(0.28)} className="flex flex-col gap-2">
                    <div className="flex items-center gap-2">
                      <div className="section-stamp">
                        <span className="h-1.5 w-1.5 rounded-full bg-ink-subtle flex-shrink-0" />
                        Earlier attempts
                      </div>
                      <span className="rep-badge">{attempts.length - 1}</span>
                    </div>
                    <div className="flex flex-col gap-2">
                      {attempts.slice(1).map((a, i) => (
                        <AttemptCard key={a.id} attempt={a} index={i + 1} />
                      ))}
                    </div>
                  </motion.div>
                )}

                {/* ── Next Move ─────────────────────────────────────────── */}
                {(() => {
                  const latestAttempt = attempts[0] ?? null;
                  const shouldRetry = latestAttempt
                    ? (latestAttempt.feedback as Record<string, unknown> | null)?.should_retry === true
                    : false;
                  const criteriaMet = latestAttempt
                    ? (latestAttempt.feedback as Record<string, unknown> | null)?.met_success_criteria === true
                    : false;

                  let heading: string;
                  let body: string;
                  let primaryLabel: string;
                  let primaryHref: string;
                  let showRetryButton = false;

                  const rerecordHref = `/session?mode=rerecord&source_speech_id=${drill.speech_id}&source_drill_id=${drill.id}`;

                  if (drill.status === "completed" || (!shouldRetry && criteriaMet)) {
                    heading = "Ready to re-record";
                    body = "You've met the criteria. Record the speech again — RoundLab will compare the new report to the original.";
                    primaryLabel = "Start re-record session";
                    primaryHref = rerecordHref;
                  } else if (shouldRetry) {
                    heading = "Try again — you're close";
                    body = latestAttempt?.score !== null
                      ? `Score: ${latestAttempt?.score}/100. Practice the drill again to hit the success criteria.`
                      : "Practice the drill again to hit the success criteria.";
                    primaryLabel = "Back to speech report";
                    primaryHref = `/speech/${drill.speech_id}`;
                    showRetryButton = true;
                  } else if (attempts.length > 0) {
                    heading = "Good rep — keep practicing";
                    body = "Record another attempt, or re-record the full speech to track improvement.";
                    primaryLabel = "Back to speech report";
                    primaryHref = `/speech/${drill.speech_id}`;
                    showRetryButton = true;
                  } else {
                    heading = "Practice this drill first";
                    body = "Record at least one attempt above, then re-record the full speech to track improvement.";
                    primaryLabel = "Back to speech report";
                    primaryHref = `/speech/${drill.speech_id}`;
                  }

                  const railIndex = drill.status === "completed" ? 3 : 2;

                  return (
                    <motion.div
                      {...fadeUp(0.30)}
                      className="mission-brief flex flex-col gap-3 p-5"
                    >
                      <RoundLabJourneyRail
                        activeIndex={railIndex}
                        showLabels
                        className="mb-1"
                      />
                      <p className="text-sm font-semibold text-ink">{heading}</p>
                      <p className="text-xs leading-relaxed text-ink-subtle">{body}</p>
                      <div className="flex flex-wrap items-center gap-2">
                        <Link
                          href={primaryHref}
                          className="flex items-center gap-1.5 rounded-md bg-lav px-4 py-2 text-xs font-semibold text-white transition-colors hover:bg-lav-hi"
                        >
                          {primaryLabel}
                          <ArrowLeft size={11} className="rotate-180" />
                        </Link>
                        {showRetryButton && (
                          <>
                            <button
                              type="button"
                              onClick={() => {
                                const el = document.getElementById("practice-room");
                                el?.scrollIntoView({ behavior: "smooth" });
                              }}
                              className="flex items-center gap-1.5 rounded-md border border-hairline px-4 py-2 text-xs font-medium text-ink-subtle transition-colors hover:border-lav/30 hover:text-ink"
                            >
                              <RefreshCw size={11} />
                              Record another rep
                            </button>
                            <Link
                              href={rerecordHref}
                              className="text-xs text-ink-faint transition-colors hover:text-ink-subtle"
                            >
                              Re-record full speech anyway
                            </Link>
                          </>
                        )}
                      </div>
                    </motion.div>
                  );
                })()}

              </motion.div>
            </AnimatePresence>
          )}
        </div>
      </main>
    </>
  );
}
