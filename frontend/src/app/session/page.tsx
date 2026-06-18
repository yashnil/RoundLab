"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "motion/react";
import {
  Mic, Upload, FileText, ArrowRight, Target, RefreshCw, Clock, Check,
} from "lucide-react";
import AppShell from "@/components/shell/AppShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { createClient } from "@/lib/supabase";
import { apiFetch } from "@/lib/api";
import { fadeUp } from "@/lib/motion";
import {
  getJudgeTypeInfo, formatSpeechTarget, SPEECH_TYPE_INFO, SPEECH_TYPE_ORDER,
  readLastJudgeType, rememberJudgeType,
} from "@/lib/practiceSetup";
import DebateSide, { type SideValue } from "@/components/practice/DebateSide";
import { JudgeLensSelector, JudgeLensPreview, type JudgeValue } from "@/components/practice/JudgeLens";
import StickyActionDock from "@/components/practice/StickyActionDock";
import type { Speech, SpeechType } from "@/types";

type CaptureMode = "record" | "upload" | "paste";

const INPUT_METHODS: {
  mode: CaptureMode;
  label: string;
  icon: typeof Mic;
  enables: string;
  limit: string;
  cta: string;
}[] = [
  {
    mode: "record",
    label: "Record now",
    icon: Mic,
    enables: "Full argument + delivery feedback",
    limit: "Needs mic access",
    cta: "Open recorder",
  },
  {
    mode: "upload",
    label: "Upload audio",
    icon: Upload,
    enables: "Full argument + delivery from existing audio",
    limit: "Audio file required",
    cta: "Choose audio",
  },
  {
    mode: "paste",
    label: "Paste text",
    icon: FileText,
    enables: "Argument structure analysis",
    limit: "No pacing, filler, or vocal delivery",
    cta: "Paste speech",
  },
];

function StepLabel({ n, title }: { n: number; title: string }) {
  return (
    <div className="flex items-center gap-2.5">
      <span className="flex h-6 w-6 items-center justify-center rounded-full border border-lav/40 bg-lav/10 font-mono text-xs font-bold text-lav">
        {n}
      </span>
      <h2 className="text-heading text-ink">{title}</h2>
    </div>
  );
}

export default function SessionPage() {
  const router = useRouter();
  const [userId, setUserId] = useState<string | null>(null);
  const [userLoading, setUserLoading] = useState(true);
  const [title, setTitle] = useState("");
  const [speechType, setSpeechType] = useState<SpeechType>("constructive");
  const [side, setSide] = useState<SideValue>("");
  const [judgeType, setJudgeType] = useState<JudgeValue>("");
  const [topic, setTopic] = useState("");
  const [inputMethod, setInputMethod] = useState<CaptureMode>("record");
  const [presetGoal, setPresetGoal] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  // Re-record mode
  const [isRerecordMode, setIsRerecordMode] = useState(false);
  const [sourceSpeechId, setSourceSpeechId] = useState<string | null>(null);
  const [sourceDrillId, setSourceDrillId] = useState<string | null>(null);
  const [contextLoading, setContextLoading] = useState(false);
  const [contextError, setContextError] = useState("");

  useEffect(() => {
    createClient().auth.getUser().then(({ data }) => {
      if (!data.user) router.replace("/login");
      else setUserId(data.user.id);
    }).finally(() => setUserLoading(false));
  }, [router]);

  /* eslint-disable react-hooks/set-state-in-effect --
     One-time, hydration-safe initialization from window.location and the source
     speech. A lazy useState initializer would cause a server/client mismatch on
     window.location. */
  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    if (params.get("mode") === "rerecord") {
      setIsRerecordMode(true);
      setSourceSpeechId(params.get("source_speech_id"));
      setSourceDrillId(params.get("source_drill_id"));
    }
    const presetType = params.get("type");
    if (presetType && presetType in SPEECH_TYPE_INFO) setSpeechType(presetType as SpeechType);
    const presetSide = params.get("side");
    if (presetSide === "pro" || presetSide === "con") setSide(presetSide);
    const presetGoalParam = params.get("goal");
    if (presetGoalParam) setPresetGoal(presetGoalParam);
    const presetInput = params.get("capture");
    if (presetInput === "record" || presetInput === "upload" || presetInput === "paste") {
      setInputMethod(presetInput);
    }
    const presetJudge = params.get("judge");
    if (presetJudge && getJudgeTypeInfo(presetJudge)) {
      setJudgeType(presetJudge as JudgeValue);
    } else {
      const lastJudge = readLastJudgeType();
      if (lastJudge) setJudgeType(lastJudge as JudgeValue);
    }
  }, []);

  useEffect(() => {
    if (!userId || !isRerecordMode || !sourceSpeechId) return;
    setContextLoading(true);
    setContextError("");
    apiFetch<Speech>(`/speeches/${sourceSpeechId}?user_id=${userId}`)
      .then((src) => {
        setSpeechType(src.speech_type as SpeechType);
        if (src.side === "pro" || src.side === "con") setSide(src.side);
        if (src.judge_type && getJudgeTypeInfo(src.judge_type)) setJudgeType(src.judge_type as JudgeValue);
        if (src.topic) setTopic(src.topic);
        setTitle(`Re-record: ${src.title}`);
      })
      .catch(() => setContextError("Could not load source session context — form left blank."))
      .finally(() => setContextLoading(false));
  }, [userId, isRerecordMode, sourceSpeechId]);
  /* eslint-enable react-hooks/set-state-in-effect */

  const typeInfo = SPEECH_TYPE_INFO[speechType];
  const selectedInput = INPUT_METHODS.find((m) => m.mode === inputMethod)!;

  async function handleSubmit() {
    if (!userId) return;
    setError(""); setSubmitting(true);
    if (judgeType) rememberJudgeType(judgeType);
    try {
      const payload: Record<string, unknown> = {
        user_id: userId,
        title: title || `${SPEECH_TYPE_INFO[speechType].label} — Practice Rep`,
        speech_type: speechType,
        side: side || null,
        judge_type: judgeType || null,
        topic: topic || null,
      };
      if (isRerecordMode && sourceSpeechId) payload.parent_speech_id = sourceSpeechId;
      if (isRerecordMode && sourceDrillId) payload.source_drill_id = sourceDrillId;

      const s = await apiFetch<Speech>("/speeches", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      // Carry the chosen capture mode into the practice room.
      router.push(`/speech/${s.id}?capture=${inputMethod}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Could not create your practice. Please try again.");
      setSubmitting(false);
    }
  }

  if (userLoading) {
    return (
      <AppShell maxWidth="full" bare>
        <div className="mx-auto flex max-w-5xl flex-col gap-6 px-4 py-8 sm:px-6">
          <Skeleton className="h-8 w-64" />
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-40 w-full rounded-xl" />
          ))}
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell maxWidth="full" bare>
      <motion.div {...fadeUp(0)} className="mx-auto flex max-w-5xl flex-col gap-8 px-4 py-8 sm:px-6">
        {/* Header */}
        <div className="flex flex-col gap-2">
          <span className="section-stamp">Practice room</span>
          <h1 className="text-title text-ink">
            {isRerecordMode ? "Set up your re-record" : "Build your practice"}
          </h1>
          <p className="max-w-xl text-sm leading-relaxed text-ink-subtle">
            Pick the speech and round context — RoundLab calibrates the judge lens and builds a
            flow, ballot, and drills from what you record.
          </p>
        </div>

        {isRerecordMode && (
          <div className="flex items-start gap-2 rounded-lg border border-ok/25 bg-ok/5 px-3 py-2.5">
            <RefreshCw size={13} className="mt-0.5 shrink-0 text-ok" aria-hidden="true" />
            <p className="text-xs leading-relaxed text-ink-subtle">
              {contextLoading
                ? "Loading your original session context…"
                : contextError
                  ? contextError
                  : "Re-recording to improve — RoundLab will compare this to the original and show your progress."}
            </p>
          </div>
        )}

        {presetGoal && (
          <div className="flex items-start gap-2 rounded-lg border border-lav/25 bg-lav/5 px-3 py-2.5">
            <Target size={13} className="mt-0.5 shrink-0 text-lav" aria-hidden="true" />
            <div>
              <p className="text-eyebrow text-lav">Today&apos;s goal</p>
              <p className="text-xs leading-relaxed text-ink-subtle">{presetGoal}</p>
            </div>
          </div>
        )}

        {/* Step 1 — Choose the speech */}
        <section className="flex flex-col gap-3">
          <StepLabel n={1} title="Choose the speech" />
          <div role="radiogroup" aria-label="Speech type" className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {SPEECH_TYPE_ORDER.map((t) => {
              const info = SPEECH_TYPE_INFO[t];
              const active = speechType === t;
              return (
                <button
                  key={t}
                  type="button"
                  role="radio"
                  aria-checked={active}
                  onClick={() => setSpeechType(t)}
                  className={[
                    "flex flex-col gap-1.5 rounded-xl border p-4 text-left transition-colors",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50",
                    active ? "border-lav/50 bg-lav/[0.07]" : "border-hairline bg-surface-1 hover:border-hairline-strong",
                  ].join(" ")}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-semibold text-ink">{info.label}</span>
                    <span className="flex items-center gap-1 font-mono text-[0.625rem] tabular-nums text-ink-faint">
                      <Clock size={10} aria-hidden="true" />
                      {formatSpeechTarget(info.targetSeconds)}
                    </span>
                  </div>
                  <p className="text-xs leading-relaxed text-ink-subtle">{info.purpose}</p>
                  <p className="mt-auto text-[11px] italic text-ink-faint">{info.strategicGoal}</p>
                </button>
              );
            })}
          </div>
        </section>

        {/* Step 2 — Round context */}
        <section className="flex flex-col gap-4">
          <StepLabel n={2} title="Set the round context" />
          <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
            <div className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-medium text-ink-subtle">Side</label>
                <DebateSide value={side} onChange={setSide} allowUnset />
              </div>
              <div className="flex flex-col gap-1.5">
                <label htmlFor="resolution" className="text-xs font-medium text-ink-subtle">Resolution</label>
                <Input
                  id="resolution"
                  placeholder="Resolved: …"
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label htmlFor="rep-name" className="text-xs font-medium text-ink-subtle">
                  Rep name <span className="text-ink-faint">· optional</span>
                </label>
                <Input
                  id="rep-name"
                  placeholder={`${typeInfo.label} — Practice Rep`}
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                />
              </div>
            </div>
            <div className="flex flex-col gap-3">
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-medium text-ink-subtle">Judge lens</label>
                <JudgeLensSelector value={judgeType} onChange={setJudgeType} />
              </div>
              <div className="rounded-lg border border-hairline bg-surface-2/50 p-3">
                <JudgeLensPreview judge={judgeType} />
              </div>
            </div>
          </div>
        </section>

        {/* Step 3 — How to practice */}
        <section className="flex flex-col gap-3">
          <StepLabel n={3} title="Choose how to practice" />
          <div role="radiogroup" aria-label="Input method" className="grid grid-cols-1 gap-2 sm:grid-cols-3">
            {INPUT_METHODS.map((m) => {
              const Icon = m.icon;
              const active = inputMethod === m.mode;
              return (
                <button
                  key={m.mode}
                  type="button"
                  role="radio"
                  aria-checked={active}
                  onClick={() => setInputMethod(m.mode)}
                  className={[
                    "flex flex-col gap-2 rounded-xl border p-4 text-left transition-colors",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50",
                    active ? "border-lav/50 bg-lav/[0.07]" : "border-hairline bg-surface-1 hover:border-hairline-strong",
                  ].join(" ")}
                >
                  <span className="flex items-center gap-1.5">
                    <Icon size={15} className={active ? "text-lav" : "text-ink-faint"} aria-hidden="true" />
                    <span className="text-sm font-semibold text-ink">{m.label}</span>
                  </span>
                  <span className="flex items-center gap-1 text-xs text-ink-subtle">
                    <Check size={11} className="shrink-0 text-ok" aria-hidden="true" />
                    {m.enables}
                  </span>
                  <span className="text-[11px] text-ink-faint">{m.limit}</span>
                </button>
              );
            })}
          </div>
        </section>

        {error && (
          <p className="rounded-lg border border-danger/20 bg-danger/5 px-3 py-2 text-xs text-danger">{error}</p>
        )}

        {/* Step 4 — Review & begin (sticky dock) */}
        <StickyActionDock
          summary={
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-ink-subtle">
              <span className="font-semibold text-ink">{typeInfo.label}</span>
              <span className="text-ink-faint">· {formatSpeechTarget(typeInfo.targetSeconds)}</span>
              {side && <span className="capitalize text-ink-faint">· {side}</span>}
              {judgeType && <span className="text-ink-faint">· {getJudgeTypeInfo(judgeType)!.label}</span>}
              <span className="text-ink-faint">· {selectedInput.label}</span>
            </div>
          }
        >
          <Button onClick={handleSubmit} disabled={submitting} className="gap-2">
            {submitting ? "Opening practice room…" : (<>{selectedInput.cta}<ArrowRight size={14} /></>)}
          </Button>
        </StickyActionDock>
      </motion.div>
    </AppShell>
  );
}
