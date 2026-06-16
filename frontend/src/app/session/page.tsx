"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "motion/react";
import {
  Mic, GitBranch, FileText, ArrowRight, Target, Zap, RefreshCw, Clock,
} from "lucide-react";
import AppShell from "@/components/shell/AppShell";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { createClient } from "@/lib/supabase";
import { apiFetch } from "@/lib/api";
import { slideInLeft, slideInRight, staggerParent, staggerChild, EASE } from "@/lib/motion";
import {
  getSpeechTypeInfo, getJudgeTypeInfo, formatSpeechTarget, setupCtaLabel,
  readLastJudgeType, rememberJudgeType,
} from "@/lib/practiceSetup";
import type { Speech } from "@/types";

// ── Styles ─────────────────────────────────────────────────────────────────────

const selectCls =
  "h-9 w-full rounded-md border border-hairline bg-surface-2 px-3 py-2 " +
  "text-sm text-ink outline-none transition-colors " +
  "focus-visible:border-lav/50 focus-visible:ring-2 focus-visible:ring-lav/20 " +
  "disabled:opacity-40";

// ── Practice loop timeline data ────────────────────────────────────────────────

const LOOP_STEPS = [
  {
    icon: Mic,
    label: "Record speech",
    hint: "30+ seconds · any PF speech type",
    color: "lav" as const,
  },
  {
    icon: GitBranch,
    label: "Argument flow",
    hint: "Claim → Warrant → Evidence → Impact",
    color: "lav" as const,
  },
  {
    icon: FileText,
    label: "Judge ballot",
    hint: "Clash · Weighing · Drops · Extensions",
    color: "lav" as const,
  },
  {
    icon: Target,
    label: "Targeted drills",
    hint: "3 drills · one per weakness",
    color: "ok" as const,
  },
];

// ── Field label ────────────────────────────────────────────────────────────────

function FieldLabel({ label, hint, required }: { label: string; hint?: string; required?: boolean }) {
  return (
    <div className="flex flex-col gap-0.5">
      <label className="text-xs font-medium text-ink-subtle">
        {label}{required && <span className="ml-0.5 text-ink-faint" aria-hidden>*</span>}
      </label>
      {hint && <p className="text-xs text-ink-faint">{hint}</p>}
    </div>
  );
}

// ── Section divider ────────────────────────────────────────────────────────────

function FormSection({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-2">
      <p className="shrink-0 text-eyebrow text-ink-faint">{label}</p>
      <div className="h-px flex-1 bg-hairline" />
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────────

export default function SessionPage() {
  const router = useRouter();
  const [userId,           setUserId]           = useState<string | null>(null);
  const [userLoading,      setUserLoading]      = useState(true);
  const [title,            setTitle]            = useState("");
  const [speechType,       setSpeechType]       = useState("constructive");
  const [side,             setSide]             = useState("");
  const [judgeType,        setJudgeType]        = useState("");
  const [topic,            setTopic]            = useState("");
  const [submitting,       setSubmitting]       = useState(false);
  const [error,            setError]            = useState("");
  // Re-record mode
  const [isRerecordMode,   setIsRerecordMode]   = useState(false);
  const [sourceSpeechId,   setSourceSpeechId]   = useState<string | null>(null);
  const [sourceDrillId,    setSourceDrillId]    = useState<string | null>(null);
  const [contextLoading,   setContextLoading]   = useState(false);
  const [contextError,     setContextError]     = useState("");

  useEffect(() => {
    createClient().auth.getUser().then(({ data }) => {
      if (!data.user) router.replace("/login");
      else setUserId(data.user.id);
    }).finally(() => setUserLoading(false));
  }, [router]);

  // Read URL params client-side (avoids useSearchParams/Suspense requirement)
  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    if (params.get("mode") === "rerecord") {
      setIsRerecordMode(true);
      setSourceSpeechId(params.get("source_speech_id"));
      setSourceDrillId(params.get("source_drill_id"));
    }
    // Quick-start deep link from the dashboard: /session?type=rebuttal
    const presetType = params.get("type");
    const VALID_TYPES = ["constructive", "rebuttal", "summary", "final_focus", "crossfire"];
    if (presetType && VALID_TYPES.includes(presetType)) {
      setSpeechType(presetType);
    }
    // Smart default: prefill the judge type the student last practiced with.
    const lastJudge = readLastJudgeType();
    if (lastJudge) setJudgeType(lastJudge);
  }, []);

  // Prefill form from source speech when in re-record mode
  useEffect(() => {
    if (!userId || !isRerecordMode || !sourceSpeechId) return;
    setContextLoading(true);
    setContextError("");
    apiFetch<Speech>(`/speeches/${sourceSpeechId}?user_id=${userId}`)
      .then((src) => {
        setSpeechType(src.speech_type);
        if (src.side) setSide(src.side);
        if (src.judge_type) setJudgeType(src.judge_type);
        if (src.topic) setTopic(src.topic);
        setTitle(`Re-record: ${src.title}`);
      })
      .catch(() => setContextError("Could not load source session context — form left blank."))
      .finally(() => setContextLoading(false));
  }, [userId, isRerecordMode, sourceSpeechId]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!userId) return;
    setError(""); setSubmitting(true);
    rememberJudgeType(judgeType);
    try {
      const payload: Record<string, unknown> = {
        user_id:     userId,
        title:       title || `${speechType.replace("_", " ")} — Practice Rep`,
        speech_type: speechType,
        side:        side || null,
        judge_type:  judgeType || null,
        topic:       topic || null,
      };
      if (isRerecordMode && sourceSpeechId) payload.parent_speech_id = sourceSpeechId;
      if (isRerecordMode && sourceDrillId)  payload.source_drill_id  = sourceDrillId;

      const s = await apiFetch<Speech>("/speeches", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      router.push(`/speech/${s.id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
      setSubmitting(false);
    }
  }

  return (
    <AppShell maxWidth="full" bare>
        <div className="mx-auto max-w-5xl px-5 py-10 sm:px-6">
          <div className="grid grid-cols-1 gap-10 lg:grid-cols-[2fr_3fr] lg:gap-14">

            {/* ── Left: Practice briefing panel ──────────────────────── */}
            <motion.div {...slideInLeft(0)} className="flex flex-col gap-7">

              {/* Header */}
              <div className="flex flex-col gap-3">
                <span className="inline-block w-fit rounded-full border border-lav/30 bg-lav/10 px-3 py-1 text-eyebrow text-lav">
                  Practice Room
                </span>
                <h1 className="text-title text-ink">Set up your practice rep</h1>
                <p className="text-sm leading-relaxed text-ink-subtle">
                  RoundLab uses your round context to calibrate the judge lens and generate precise ballot-style feedback.
                </p>
              </div>

              {/* Practice loop timeline */}
              <motion.div
                className="flex flex-col"
                variants={staggerParent(0.08, 0.15)}
                initial="hidden"
                animate={userLoading ? "hidden" : "show"}
              >
                <p className="mb-4 text-eyebrow text-ink-faint">Your practice loop</p>

                {userLoading ? (
                  <div className="flex flex-col gap-4">
                    {Array.from({ length: 4 }).map((_, i) => (
                      <div key={i} className="flex gap-3">
                        <Skeleton className="h-8 w-8 shrink-0 rounded-lg" />
                        <div className="flex flex-1 flex-col gap-1.5 pt-1">
                          <Skeleton className="h-3.5 w-28" />
                          <Skeleton className="h-3 w-40" />
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  LOOP_STEPS.map((step, i) => {
                    const Icon = step.icon;
                    const isLast = i === LOOP_STEPS.length - 1;
                    const dotColor  = step.color === "ok" ? "bg-ok"  : "bg-lav";
                    const iconColor = step.color === "ok" ? "text-ok" : "text-lav";
                    const ringColor = step.color === "ok" ? "border-ok/20 bg-ok/8" : "border-lav/20 bg-lav/8";

                    return (
                      <motion.div key={step.label} variants={staggerChild} className="flex gap-3">
                        {/* Vertical spine */}
                        <div className="flex flex-col items-center">
                          <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border ${ringColor}`}>
                            <Icon size={14} className={iconColor} />
                          </div>
                          {!isLast && (
                            <div className="mt-1 flex flex-1 flex-col items-center gap-1 pb-3">
                              <div className="h-full w-px bg-hairline" style={{ minHeight: 20 }} />
                              <span className={`text-[8px] font-bold ${dotColor === "bg-ok" ? "text-ok/50" : "text-lav/40"}`}>↓</span>
                            </div>
                          )}
                        </div>
                        {/* Label */}
                        <div className="flex flex-col gap-0.5 pb-4">
                          <p className="text-sm font-semibold text-ink">{step.label}</p>
                          <p className="text-xs text-ink-faint">{step.hint}</p>
                        </div>
                      </motion.div>
                    );
                  })
                )}
              </motion.div>

              {/* Bottom note */}
              {!userLoading && (
                <div className="hidden items-start gap-2 rounded-lg border border-hairline bg-surface-1 px-3 py-2.5 lg:flex">
                  <Zap size={12} className="mt-0.5 shrink-0 text-lav" />
                  <p className="text-xs leading-relaxed text-ink-faint">
                    Drill attempts earn <span className="font-semibold text-lav">50 XP</span> — the fastest way to level up. After recording, RoundLab handles the rest.
                  </p>
                </div>
              )}
            </motion.div>

            {/* ── Right: Speech setup form ────────────────────────────── */}
            <motion.div {...slideInRight(0.05)}>
              {userLoading ? (
                <Card>
                  <CardContent className="flex flex-col gap-4 px-5 py-5">
                    {Array.from({ length: 6 }).map((_, i) => (
                      <div key={i} className="flex flex-col gap-1.5">
                        <Skeleton className="h-3 w-20" />
                        <Skeleton className="h-9 w-full rounded-md" />
                      </div>
                    ))}
                    <Skeleton className="mt-1 h-9 w-full rounded-md" />
                  </CardContent>
                </Card>
              ) : (
                <Card className="beam-top" style={{ boxShadow: "0 0 48px -16px oklch(0.510 0.156 278 / 0.18)" }}>
                  <CardContent className="px-5 py-5">

                    {/* Card header */}
                    <div className="mb-5 border-b border-hairline pb-4">
                      <p className="text-eyebrow text-lav">Speech Setup</p>
                      <p className="mt-0.5 text-sm font-semibold text-ink">Configure your round</p>
                      <p className="mt-0.5 text-xs text-ink-faint">
                        More context → more precise judge feedback
                      </p>
                    </div>

                    {/* Re-record mode banner */}
                    {isRerecordMode && (
                      <div className="mb-5 flex items-start gap-2 rounded-lg border border-ok/20 bg-ok/5 px-3 py-2.5">
                        <RefreshCw size={12} className="mt-0.5 shrink-0 text-ok" />
                        <div>
                          <p className="text-xs font-semibold text-ok">Re-record mode</p>
                          <p className="mt-0.5 text-xs text-ink-subtle">
                            {contextLoading
                              ? "Loading your original session context…"
                              : contextError
                              ? contextError
                              : "RoundLab will compare this report to the original and show your improvement."}
                          </p>
                        </div>
                      </div>
                    )}

                    <form onSubmit={handleSubmit} className="flex flex-col gap-5">

                      {/* ── Round context ── */}
                      <FormSection label="Round context" />

                      {/* Speech type */}
                      <div className="flex flex-col gap-1.5">
                        <FieldLabel label="Speech type" hint="What part of the round?" required />
                        <select className={selectCls} value={speechType}
                          onChange={(e) => setSpeechType(e.target.value)} disabled={submitting}>
                          <option value="constructive">Constructive</option>
                          <option value="rebuttal">Rebuttal</option>
                          <option value="summary">Summary</option>
                          <option value="final_focus">Final Focus</option>
                          <option value="crossfire">Crossfire</option>
                        </select>
                        {getSpeechTypeInfo(speechType) && (
                          <div className="flex items-start gap-2 rounded-lg border border-hairline bg-surface-2/60 px-3 py-2">
                            <Clock size={12} className="mt-0.5 shrink-0 text-ink-faint" aria-hidden="true" />
                            <p className="text-xs leading-relaxed text-ink-subtle">
                              <span className="font-medium text-ink">
                                {formatSpeechTarget(getSpeechTypeInfo(speechType)!.targetSeconds)} target.
                              </span>{" "}
                              {getSpeechTypeInfo(speechType)!.purpose}
                            </p>
                          </div>
                        )}
                      </div>

                      {/* Side + Judge */}
                      <div className="grid grid-cols-2 gap-3">
                        <div className="flex flex-col gap-1.5">
                          <FieldLabel label="Side" hint="Affects framing" />
                          <select className={selectCls} value={side}
                            onChange={(e) => setSide(e.target.value)} disabled={submitting}>
                            <option value="">— not set —</option>
                            <option value="pro">Pro</option>
                            <option value="con">Con</option>
                          </select>
                        </div>
                        <div className="flex flex-col gap-1.5">
                          <FieldLabel label="Judge type" hint="Adapts tone" />
                          <select className={selectCls} value={judgeType}
                            onChange={(e) => setJudgeType(e.target.value)} disabled={submitting}>
                            <option value="">— not set —</option>
                            <option value="lay">Lay</option>
                            <option value="flow">Flow</option>
                            <option value="tech">Tech</option>
                            <option value="coach">Coach</option>
                          </select>
                        </div>
                      </div>
                      {getJudgeTypeInfo(judgeType) && (
                        <p className="-mt-2 text-xs leading-relaxed text-ink-subtle">
                          <span className="font-medium text-ink">{getJudgeTypeInfo(judgeType)!.label}:</span>{" "}
                          {getJudgeTypeInfo(judgeType)!.description}
                        </p>
                      )}

                      {/* ── Session info ── */}
                      <FormSection label="Session info" />

                      {/* Rep name — optional, auto-fills from type if blank */}
                      <div className="flex flex-col gap-1.5">
                        <FieldLabel label="Rep name" hint='Optional — e.g. "1AC · State Championship R4"' />
                        <Input
                          placeholder={`${speechType.replace("_", " ").replace(/^\w/, c => c.toUpperCase())} — Practice Rep`}
                          value={title} onChange={(e) => setTitle(e.target.value)}
                          disabled={submitting}
                        />
                      </div>

                      {/* Resolution */}
                      <div className="flex flex-col gap-1.5">
                        <FieldLabel label="Resolution" hint='The PF topic — e.g. "Resolved: The USFG should…"' />
                        <Input
                          placeholder="Resolved: …"
                          value={topic} onChange={(e) => setTopic(e.target.value)}
                          disabled={submitting}
                        />
                      </div>

                      {/* Error */}
                      {error && (
                        <motion.p
                          initial={{ opacity: 0, y: 4 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ duration: 0.2, ease: EASE }}
                          className="rounded-lg border border-danger/20 bg-danger/5 px-3 py-2 text-xs text-danger"
                        >
                          {error}
                        </motion.p>
                      )}

                      {/* CTA */}
                      <div className="flex flex-col gap-2 pt-1">
                        <motion.div
                          whileHover={{ scale: 1.01 }}
                          whileTap={{ scale: 0.99 }}
                          transition={{ duration: 0.12 }}
                        >
                          <Button type="submit" disabled={submitting} className="w-full gap-2">
                            {submitting ? "Opening practice room…" : (
                              <><span>{setupCtaLabel(isRerecordMode)}</span><ArrowRight size={13} /></>
                            )}
                          </Button>
                        </motion.div>

                        {/* Keyboard hint below CTA */}
                        <p className="hidden text-center text-[10px] text-ink-faint sm:block">
                          After setup, press{" "}
                          <kbd className="rounded bg-surface-2 px-1 py-0.5 font-mono text-[9px] border border-hairline">Space</kbd>
                          {" "}to start recording
                        </p>
                      </div>

                    </form>
                  </CardContent>
                </Card>
              )}
            </motion.div>

          </div>
        </div>
    </AppShell>
  );
}
