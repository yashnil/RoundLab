"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { motion, AnimatePresence } from "motion/react";
import {
  Check, ChevronDown, ChevronUp,
  Mic, RefreshCw, Trash2, Upload, ThumbsUp, ThumbsDown,
} from "lucide-react";
import AppNav from "@/components/AppNav";
import WorkflowStepper from "@/components/WorkflowStepper";
import RecordingStudio from "@/components/RecordingStudio";
import UploadDropzone from "@/components/UploadDropzone";
import TranscriptPanel from "@/components/TranscriptPanel";
import ArgumentCard from "@/components/ArgumentCard";
import ScoreCard from "@/components/ScoreCard";
import ScoreBreakdown from "@/components/ScoreBreakdown";
import LoadingCard from "@/components/LoadingCard";
import DeleteDialog from "@/components/DeleteDialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { createClient } from "@/lib/supabase";
import { apiFetch } from "@/lib/api";
import { fadeUp, staggerParent, staggerChild, T, EASE } from "@/lib/motion";
import DrillCard from "@/components/DrillCard";
import type { ArgumentMap, Drill, DrillStatus, FeedbackReport, Speech, Transcript } from "@/types";
import type { RecordState } from "@/components/RecordingStudio";

// ── Constants ──────────────────────────────────────────────────────────────────

const ALLOWED_EXT = ["mp3", "wav", "m4a", "webm", "ogg", "mp4"];
const MAX_BYTES   = 50 * 1024 * 1024;

const TYPE_LABEL: Record<string, string> = {
  constructive: "Constructive", rebuttal: "Rebuttal",
  summary: "Summary", final_focus: "Final Focus", crossfire: "Crossfire",
};

const MSG_TRANSCRIBE = ["Preparing audio…", "Running transcription…", "Processing signal…", "Saving transcript…"];
const MSG_FLOW       = ["Mapping claims…", "Finding warrants…", "Checking evidence…", "Building flow…"];
const MSG_FEEDBACK   = ["Reading the flow…", "Scoring clash…", "Checking judge adaptation…", "Writing judge ballot…"];
const MSG_DRILLS     = ["Reading your ballot…", "Finding skill gaps…", "Building practice drills…"];

// ── Helpers ────────────────────────────────────────────────────────────────────

function validateFile(f: File): string | null {
  const ext = f.name.split(".").pop()?.toLowerCase() ?? "";
  if (!ALLOWED_EXT.includes(ext)) return `Unsupported ".${ext}". Allowed: ${ALLOWED_EXT.join(", ")}.`;
  if (f.size > MAX_BYTES)         return `Too large (${(f.size / 1024 / 1024).toFixed(1)} MB). Max 50 MB.`;
  return null;
}

function getBestMime(): { mimeType: string; ext: string } {
  if (typeof MediaRecorder === "undefined") return { mimeType: "", ext: "webm" };
  for (const c of [
    { mimeType: "audio/webm;codecs=opus", ext: "webm" },
    { mimeType: "audio/webm",             ext: "webm" },
    { mimeType: "audio/ogg;codecs=opus",  ext: "ogg"  },
    { mimeType: "audio/mp4",              ext: "mp4"  },
  ]) { if (MediaRecorder.isTypeSupported(c.mimeType)) return c; }
  return { mimeType: "", ext: "webm" };
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function StepHeader({ n, title, done, aside }: {
  n: number; title: string; done: boolean; aside?: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between gap-3">
      <div className="flex items-center gap-2.5">
        <AnimatePresence mode="wait">
          {done ? (
            <motion.span
              key="done"
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={T.snap}
              className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-lav text-white"
            >
              <Check size={10} strokeWidth={2.5} />
            </motion.span>
          ) : (
            <motion.span
              key="pending"
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={T.snap}
              className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-hairline-strong text-xs font-bold text-ink-faint"
            >
              {n}
            </motion.span>
          )}
        </AnimatePresence>
        <p className="text-heading text-ink">{title}</p>
      </div>
      {aside}
    </div>
  );
}

function Collapsible({ label, children, open: defaultOpen = false }: {
  label: string; children: React.ReactNode; open?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border-t border-hairline">
      <button
        type="button"
        className="flex w-full items-center justify-between py-3 text-left"
        onClick={() => setOpen((v) => !v)}
      >
        <span className="text-eyebrow text-ink-faint">{label}</span>
        <motion.span
          animate={{ rotate: open ? 180 : 0 }}
          transition={T.fast}
        >
          <ChevronDown size={12} className="text-ink-faint" />
        </motion.span>
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: EASE }}
            className="overflow-hidden"
          >
            <div className="pb-4">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function InlineAlert({ variant, children }: { variant: "danger" | "warn"; children: React.ReactNode }) {
  const s = variant === "danger"
    ? "border-danger/20 bg-danger/5 text-danger/90"
    : "border-warn/20 bg-warn/5 text-warn/90";
  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={T.base}
      className={`flex items-start gap-2 rounded-lg border px-4 py-3 text-sm ${s}`}
    >
      <span className="mt-0.5 shrink-0">⚠</span>
      <p>{children}</p>
    </motion.div>
  );
}

function StatusBadge({ status }: { status: string }) {
  type V = "default" | "indigo" | "green" | "amber" | "red";
  const MAP: Record<string, [string, V]> = {
    pending:      ["Pending",      "default"],
    transcribing: ["Transcribing", "indigo" ],
    analyzing:    ["Analyzing",    "amber"  ],
    done:         ["Complete",     "green"  ],
    error:        ["Error",        "red"    ],
  };
  const [label, variant] = MAP[status] ?? [status, "default" as V];
  return <Badge variant={variant} className="shrink-0">{label}</Badge>;
}

function CoachDiagnosis({ category, items, label }: { category: string; items: string[]; label: string }) {
  if (!items || items.length === 0) return null;

  // Determine status based on content
  const rawText = items.join(" ").toLowerCase();
  let status: "strong" | "needs-work" | "missing";
  let statusColor: string;
  let explanation: string;
  let fix: string;

  if (rawText.includes("none") || rawText.includes("absent") || rawText.includes("missing") || items.length === 0) {
    status = "missing";
    statusColor = "text-danger";
  } else if (rawText.includes("thin") || rawText.includes("weak") || rawText.includes("unclear")) {
    status = "needs-work";
    statusColor = "text-warn";
  } else {
    status = "strong";
    statusColor = "text-ok";
  }

  // Generate student-friendly explanations
  if (category === "warranting") {
    if (status === "missing") {
      explanation = "You often state what happened, but do not explain why it proves your argument.";
      fix = "Add one sentence after each claim that starts with 'This matters because…' or 'This is true because…'";
    } else if (status === "needs-work") {
      explanation = "Some warrants are present but could be stronger and more explicit.";
      fix = "Make sure every claim has a clear 'because' sentence explaining the logical connection.";
    } else {
      explanation = "Your warranting is solid. You explain why your claims are true.";
      fix = "";
    }
  } else if (category === "weighing") {
    if (status === "missing") {
      explanation = "RoundLab did not detect clear weighing or comparative analysis.";
      fix = "Add comparisons using magnitude (how big), probability (how likely), or timeframe (how soon).";
    } else if (status === "needs-work") {
      explanation = "Some weighing is present but needs to be more explicit.";
      fix = "Directly compare your impacts to your opponent's. Say 'Our impact outweighs because…'";
    } else {
      explanation = "You're weighing impacts against each other effectively.";
      fix = "";
    }
  } else if (category === "evidence") {
    if (status === "missing") {
      explanation = "You mention sources but don't clearly explain what they prove.";
      fix = "After citing evidence, explain exactly what the card proves in one sentence.";
    } else if (status === "needs-work") {
      explanation = "Your sources are mentioned, but some connections to claims are unclear.";
      fix = "After each piece of evidence, add: 'This proves that [claim] because [explanation].'";
    } else {
      explanation = "Your evidence is well-connected to your arguments.";
      fix = "";
    }
  } else {
    // Generic fallback for other categories
    if (status === "missing") {
      explanation = `${label} is not clearly present in your speech.`;
      fix = "Focus on developing this area in your next attempt.";
    } else if (status === "needs-work") {
      explanation = `${label} needs improvement.`;
      fix = "Review the specific feedback items and strengthen this skill.";
    } else {
      explanation = `${label} is working well.`;
      fix = "";
    }
  }

  return (
    <div className="flex flex-col gap-2 rounded-lg border border-hairline bg-surface-2 px-4 py-3">
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm font-semibold text-ink">{label}</p>
        <span className={`text-xs font-medium ${statusColor} capitalize`}>
          {status === "needs-work" ? "Needs Work" : status === "missing" ? "Missing" : "Strong"}
        </span>
      </div>
      <p className="text-sm leading-relaxed text-ink-muted">{explanation}</p>
      {fix && (
        <div className="flex items-start gap-2 rounded-md border border-lav/10 bg-lav/5 px-3 py-2">
          <span className="text-xs font-semibold text-lav">Fix:</span>
          <p className="text-xs leading-relaxed text-ink-subtle">{fix}</p>
        </div>
      )}
    </div>
  );
}

/** Wraps a workspace section card — animates in when it first appears */
function WorkspaceCard({ children }: { children: React.ReactNode }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: EASE }}
    >
      <Card>{children}</Card>
    </motion.div>
  );
}

// ── Main ───────────────────────────────────────────────────────────────────────

export default function SpeechPage() {
  const { id: speechId } = useParams<{ id: string }>();
  const router = useRouter();

  const [userId,     setUserId]     = useState<string | null>(null);
  const [speech,     setSpeech]     = useState<Speech | null>(null);
  const [pageLoad,   setPageLoad]   = useState(true);
  const [pageErr,    setPageErr]    = useState("");

  const [mode,       setMode]       = useState<"record" | "upload">("record");
  const [recState,   setRecState]   = useState<RecordState>("idle");
  const [recSecs,    setRecSecs]    = useState(0);
  const [recBlob,    setRecBlob]    = useState<Blob | null>(null);
  const [recUrl,     setRecUrl]     = useState<string | null>(null);
  const [recErr,     setRecErr]     = useState("");
  const [selFile,    setSelFile]    = useState<File | null>(null);
  const [fileErr,    setFileErr]    = useState("");
  const [upErr,      setUpErr]      = useState("");
  const [uploading,  setUploading]  = useState(false);
  const [resetting,  setResetting]  = useState(false);

  const [transcript,   setTranscript]   = useState<Transcript | null>(null);
  const [transcribing, setTranscribing] = useState(false);
  const [txErr,        setTxErr]        = useState("");
  const [argMap,       setArgMap]       = useState<ArgumentMap | null>(null);
  const [genFlow,      setGenFlow]      = useState(false);
  const [flowErr,      setFlowErr]      = useState("");
  const [feedback,     setFeedback]     = useState<FeedbackReport | null>(null);
  const [genFb,        setGenFb]        = useState(false);
  const [fbErr,        setFbErr]        = useState("");

  const [drills,        setDrills]        = useState<Drill[]>([]);
  const [genDrills,     setGenDrills]     = useState(false);
  const [drillErr,      setDrillErr]      = useState("");
  const [updatingDrill, setUpdatingDrill] = useState<string | null>(null);

  const [ratingFeedback, setRatingFeedback] = useState(false);
  const [feedbackRated, setFeedbackRated] = useState(false);

  const [delOpen,  setDelOpen]  = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteErr, setDeleteErr] = useState("");

  const mrRef   = useRef<MediaRecorder | null>(null);
  const chunks  = useRef<Blob[]>([]);
  const stream  = useRef<MediaStream | null>(null);
  const timer   = useRef<ReturnType<typeof setInterval> | null>(null);
  const extRef  = useRef("webm");
  const urlRef  = useRef<string | null>(null);

  useEffect(() => () => {
    if (timer.current) clearInterval(timer.current);
    stream.current?.getTracks().forEach((t) => t.stop());
    if (urlRef.current) URL.revokeObjectURL(urlRef.current);
  }, []);

  useEffect(() => {
    createClient().auth.getUser()
      .then(({ data }) => {
        if (!data.user) { router.replace("/login"); return null; }
        const uid = data.user.id;
        setUserId(uid);
        return apiFetch<Speech>(`/speeches/${speechId}?user_id=${uid}`).then((s) => ({ s, uid }));
      })
      .then(async (result) => {
        if (!result) return;
        const { s, uid } = result;
        setSpeech(s);
        try { setTranscript(await apiFetch<Transcript>(`/speeches/${speechId}/transcript?user_id=${uid}`)); }    catch {}
        try { setArgMap(await apiFetch<ArgumentMap>(`/speeches/${speechId}/argument-map?user_id=${uid}`)); }     catch {}
        try { setFeedback(await apiFetch<FeedbackReport>(`/speeches/${speechId}/feedback?user_id=${uid}`)); }    catch {}
        try { setDrills(await apiFetch<Drill[]>(`/speeches/${speechId}/drills?user_id=${uid}`)); }               catch {}
      })
      .catch(() => setPageErr("Could not load your data. Please refresh and try again."))
      .finally(() => setPageLoad(false));
  }, [speechId, router]);

  // ── Recording ──────────────────────────────────────────────────────────────

  async function startRec() {
    setRecErr(""); setRecState("requesting");
    try {
      const s = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.current = s;
      const { mimeType, ext } = getBestMime();
      extRef.current = ext;
      const mr = new MediaRecorder(s, mimeType ? { mimeType } : {});
      mrRef.current = mr; chunks.current = [];
      mr.ondataavailable = (e) => { if (e.data.size > 0) chunks.current.push(e.data); };
      mr.onstop = () => {
        const blob = new Blob(chunks.current, { type: mimeType || "audio/webm" });
        if (urlRef.current) URL.revokeObjectURL(urlRef.current);
        const u = URL.createObjectURL(blob);
        urlRef.current = u;
        setRecBlob(blob); setRecUrl(u); setRecState("recorded");
        stream.current?.getTracks().forEach((t) => t.stop());
        stream.current = null;
        if (timer.current) { clearInterval(timer.current); timer.current = null; }
      };
      mr.start();
      setRecSecs(0);
      timer.current = setInterval(() => setRecSecs((n) => n + 1), 1000);
      setRecState("recording");
    } catch (err: unknown) {
      setRecState("error");
      setRecErr(err instanceof Error && err.name === "NotAllowedError"
        ? "Microphone permission denied." : "Could not access microphone.");
    }
  }

  function stopRec()    { mrRef.current?.stop(); }

  function discardRec() {
    if (urlRef.current) { URL.revokeObjectURL(urlRef.current); urlRef.current = null; }
    setRecUrl(null); setRecBlob(null); setRecState("idle"); setRecSecs(0); setRecErr("");
  }

  async function saveRec() {
    if (!recBlob || !userId) return;
    setRecState("uploading");
    const path = `${userId}/${speechId}/audio.${extRef.current}`;
    try {
      const sb = createClient();
      const { error: se } = await sb.storage.from("audio").upload(path, recBlob, {
        upsert: true, contentType: recBlob.type || "audio/webm",
      });
      if (se) { setRecState("error"); setRecErr(`Upload failed: ${se.message}`); return; }
      const upd = await apiFetch<Speech>(`/speeches/${speechId}?user_id=${userId}`, {
        method: "PATCH", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ audio_url: path }),
      });
      setSpeech(upd);
      if (urlRef.current) { URL.revokeObjectURL(urlRef.current); urlRef.current = null; }
      setRecUrl(null); setRecBlob(null); setRecState("idle");
    } catch (err: unknown) {
      setRecState("error");
      setRecErr(err instanceof Error ? err.message : "Upload failed.");
    }
  }

  // ── File upload ────────────────────────────────────────────────────────────

  function onFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    setFileErr(""); setUpErr("");
    const f = e.target.files?.[0] ?? null;
    if (!f) return;
    const ve = validateFile(f);
    if (ve) { setFileErr(ve); setSelFile(null); e.target.value = ""; }
    else setSelFile(f);
  }

  async function uploadFile() {
    if (!selFile || !userId) return;
    setUpErr(""); setUploading(true);
    const ext  = selFile.name.split(".").pop()!.toLowerCase();
    const path = `${userId}/${speechId}/audio.${ext}`;
    try {
      const sb = createClient();
      const { error: se } = await sb.storage.from("audio").upload(path, selFile, { upsert: true });
      if (se) { setUpErr(`Upload failed: ${se.message}`); return; }
      const upd = await apiFetch<Speech>(`/speeches/${speechId}?user_id=${userId}`, {
        method: "PATCH", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ audio_url: path }),
      });
      setSpeech(upd); setSelFile(null);
    } catch (err: unknown) {
      setUpErr(err instanceof Error ? err.message : "Upload failed.");
    } finally { setUploading(false); }
  }

  function clearFile() { setSelFile(null); setFileErr(""); }

  // ── Reset audio ────────────────────────────────────────────────────────────

  async function resetAudio() {
    if (!userId) return;
    setResetting(true);
    try {
      const upd = await apiFetch<Speech>(`/speeches/${speechId}/reset-audio?user_id=${userId}`, { method: "POST" });
      setSpeech(upd);
      setTranscript(null); setArgMap(null); setFeedback(null);
      setRecState("idle"); setRecUrl(null); setRecBlob(null); setRecErr("");
    } catch {}
    finally { setResetting(false); }
  }

  // ── AI operations ──────────────────────────────────────────────────────────

  async function transcribe() {
    if (!userId) return;
    setTxErr(""); setTranscribing(true);
    try { setTranscript(await apiFetch<Transcript>(`/speeches/${speechId}/transcribe?user_id=${userId}`, { method: "POST" })); }
    catch (e: unknown) { setTxErr(e instanceof Error ? e.message : "Transcription failed."); }
    finally { setTranscribing(false); }
  }

  async function generateFlow() {
    if (!userId) return;
    setFlowErr(""); setGenFlow(true);
    try { setArgMap(await apiFetch<ArgumentMap>(`/speeches/${speechId}/extract-arguments?user_id=${userId}`, { method: "POST" })); }
    catch (e: unknown) { setFlowErr(e instanceof Error ? e.message : "Flow generation failed."); }
    finally { setGenFlow(false); }
  }

  async function generateFeedback() {
    if (!userId) return;
    setFbErr(""); setGenFb(true);
    try { setFeedback(await apiFetch<FeedbackReport>(`/speeches/${speechId}/generate-feedback?user_id=${userId}`, { method: "POST" })); }
    catch (e: unknown) { setFbErr(e instanceof Error ? e.message : "Feedback generation failed."); }
    finally { setGenFb(false); }
  }

  async function deleteSession() {
    if (!userId) return;
    setDeleting(true);
    setDeleteErr("");
    try {
      await apiFetch(`/speeches/${speechId}?user_id=${userId}`, { method: "DELETE" });
      router.replace("/dashboard");
    }
    catch (e: unknown) {
      setDeleteErr(e instanceof Error ? e.message : "Could not delete this session. Please refresh and try again.");
    }
    finally { setDeleting(false); }
  }

  // ── Drills ─────────────────────────────────────────────────────────────────

  async function generateDrills() {
    if (!userId) return;
    setDrillErr(""); setGenDrills(true);
    try {
      const result = await apiFetch<Drill[]>(`/speeches/${speechId}/generate-drills?user_id=${userId}`, { method: "POST" });
      setDrills(result);
    } catch (e: unknown) {
      setDrillErr(e instanceof Error ? e.message : "Drill generation failed.");
    } finally { setGenDrills(false); }
  }

  async function updateDrillStatus(drillId: string, status: DrillStatus) {
    if (!userId) return;
    setUpdatingDrill(drillId);
    try {
      const updated = await apiFetch<Drill>(`/drills/${drillId}?user_id=${userId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });
      setDrills((prev) => prev.map((d) => d.id === drillId ? updated : d));
    } catch { /* silently ignore */ }
    finally { setUpdatingDrill(null); }
  }

  /** Start a fresh session with the same speech metadata. */
  async function startNewAttempt() {
    if (!speech || !userId) return;
    try {
      const newSpeech = await apiFetch<Speech>("/speeches", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id:     userId,
          title:       `${speech.title} (Attempt 2)`,
          speech_type: speech.speech_type,
          side:        speech.side,
          judge_type:  speech.judge_type,
          topic:       speech.topic,
        }),
      });
      router.push(`/speech/${newSpeech.id}`);
    } catch { /* fallback: just go to new session */ router.push("/session"); }
  }

  async function rateFeedback(rating: "helpful" | "not_helpful") {
    if (!userId || feedbackRated) return;
    setRatingFeedback(true);
    try {
      const updated = await apiFetch<FeedbackReport>(
        `/speeches/${speechId}/feedback/rating?user_id=${userId}`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ helpful_rating: rating }),
        }
      );
      setFeedback(updated);
      setFeedbackRated(true);
    } catch {}
    finally { setRatingFeedback(false); }
  }

  // ── States ─────────────────────────────────────────────────────────────────

  if (pageLoad) {
    return (
      <>
        <AppNav />
        <main className="min-h-screen bg-canvas">
          <div className="mx-auto flex max-w-3xl flex-col gap-5 px-6 py-9">
            <Skeleton className="h-6 w-48 rounded-lg" />
            <Skeleton className="h-4 w-60 rounded-lg" />
            <Skeleton className="h-8 w-full rounded-full" />
            {[1, 2].map((i) => (
              <Card key={i}><CardContent className="py-8"><Skeleton className="h-20 w-full rounded-lg" /></CardContent></Card>
            ))}
          </div>
        </main>
      </>
    );
  }

  if (pageErr || !speech) {
    return (
      <>
        <AppNav />
        <main className="min-h-screen bg-canvas">
          <div className="mx-auto max-w-3xl px-6 py-16">
            <p className="text-sm text-danger">{pageErr || "Speech not found."}</p>
          </div>
        </main>
      </>
    );
  }

  // ── Computed ───────────────────────────────────────────────────────────────

  const wc         = transcript?.word_count ?? null;
  const canAnalyze = wc !== null && wc >= 20;
  const recBusy    = recState === "requesting" || recState === "recording" || recState === "uploading";

  const date = new Date(speech.created_at).toLocaleDateString(undefined, {
    month: "long", day: "numeric", year: "numeric",
  });

  const steps = [
    { label: "Audio",      done: !!speech.audio_url        },
    { label: "Transcript", done: !!transcript              },
    { label: "Flow",       done: !!argMap                  },
    { label: "Feedback",   done: !!feedback                },
    { label: "Drills",     done: drills.length > 0        },
  ];

  const deleteBtn = (
    <button
      type="button"
      onClick={() => setDelOpen(true)}
      className="flex items-center gap-1.5 rounded-md px-2 py-1.5 text-xs font-medium text-ink-faint transition-colors hover:bg-danger/10 hover:text-danger"
    >
      <Trash2 size={12} />
      Delete
    </button>
  );

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <>
      <AppNav rightSlot={deleteBtn} />
      <main className="min-h-screen bg-canvas">
        <motion.div
          className="mx-auto flex max-w-3xl flex-col gap-5 px-6 py-9"
          variants={staggerParent(0.08, 0.05)}
          initial="hidden"
          animate="show"
        >
          {/* Header */}
          <motion.div variants={staggerChild} className="flex flex-col gap-2">
            <div className="flex items-start justify-between gap-3">
              <h1 className="text-title text-ink">{speech.title}</h1>
              <StatusBadge status={speech.status} />
            </div>
            <div className="flex flex-wrap items-center gap-x-2.5 gap-y-0 text-xs text-ink-subtle">
              <span>{TYPE_LABEL[speech.speech_type] ?? speech.speech_type}</span>
              {speech.side       && <span className="capitalize">{speech.side}</span>}
              {speech.judge_type && <span className="capitalize">{speech.judge_type} judge</span>}
              <span className="text-ink-faint">{date}</span>
            </div>
            {speech.topic && <p className="text-xs text-ink-faint">{speech.topic}</p>}
          </motion.div>

          {/* Stepper */}
          <motion.div variants={staggerChild}>
            <WorkflowStepper steps={steps} />
          </motion.div>

          {/* Workspace cards — each animates in when it first appears */}
          <AnimatePresence mode="popLayout">

            {/* ── Step 1: Audio ─────────────────────────────────────────── */}
            <WorkspaceCard key="audio">
              <CardContent className="flex flex-col gap-4 px-5 py-5">
                <StepHeader n={1} title="Audio" done={!!speech.audio_url} />

                {speech.audio_url ? (
                  <div className="flex flex-col gap-3">
                    <div className="flex items-center gap-3 rounded-lg border border-ok/20 bg-ok/5 px-4 py-3">
                      <Mic size={13} className="shrink-0 text-ok" />
                      <div className="min-w-0 flex-1">
                        <p className="text-xs font-medium text-ok">Audio ready</p>
                        <p className="mt-0.5 truncate font-mono text-xs text-ok/50">
                          {speech.audio_url.split("/").pop()}
                        </p>
                      </div>
                    </div>
                    <Button
                      variant="secondary" size="sm" disabled={resetting} onClick={resetAudio}
                      className="w-fit gap-1.5 text-ink-faint hover:border-danger/30 hover:text-danger"
                    >
                      <RefreshCw size={11} className={resetting ? "animate-spin" : ""} />
                      {resetting ? "Resetting…" : "Delete audio & re-record"}
                    </Button>
                  </div>
                ) : (
                  <div className="flex flex-col gap-4">
                    <div className="flex gap-0.5 rounded-lg border border-hairline bg-surface-2 p-0.5">
                      {(["record", "upload"] as const).map((m) => (
                        <button
                          key={m}
                          type="button"
                          disabled={recBusy}
                          onClick={() => setMode(m)}
                          className={[
                            "flex flex-1 items-center justify-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors disabled:opacity-40",
                            mode === m
                              ? "border border-hairline bg-surface-3 text-ink"
                              : "text-ink-subtle hover:text-ink-muted",
                          ].join(" ")}
                        >
                          {m === "record" ? <><Mic size={12} /> Record</> : <><Upload size={12} /> Upload</>}
                        </button>
                      ))}
                    </div>

                    <AnimatePresence mode="wait">
                      {mode === "record" ? (
                        <motion.div key="record"
                          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                          transition={T.fast}
                        >
                          <RecordingStudio
                            recordState={recState} recordingSeconds={recSecs}
                            recordObjectUrl={recUrl} recordError={recErr}
                            onStartRecording={startRec} onStopRecording={stopRec}
                            onSaveRecording={saveRec}  onDiscardRecording={discardRec}
                          />
                        </motion.div>
                      ) : (
                        <motion.div key="upload"
                          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                          transition={T.fast}
                        >
                          <UploadDropzone
                            selectedFile={selFile} fileError={fileErr}
                            uploadError={upErr}    uploading={uploading}
                            onFileChange={onFileChange} onUpload={uploadFile} onClearFile={clearFile}
                          />
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                )}
              </CardContent>
            </WorkspaceCard>

            {/* ── Step 2: Transcript ────────────────────────────────────── */}
            {speech.audio_url && (
              transcribing ? (
                <motion.div key="tx-loading" {...fadeUp(0)}>
                  <LoadingCard title="Transcribing audio" messages={MSG_TRANSCRIBE} />
                </motion.div>
              ) : transcript ? (
                <WorkspaceCard key="tx-done">
                  <CardContent className="flex flex-col gap-4 px-5 py-5">
                    <StepHeader n={2} title="Transcript" done />
                    <TranscriptPanel transcript={transcript} onReRecord={resetAudio} />

                    {/* Next step CTA */}
                    {!argMap && (
                      <div className="flex items-start gap-3 rounded-lg border border-lav/20 bg-lav/5 px-4 py-3">
                        <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-lav text-xs font-bold text-white">
                          3
                        </div>
                        <div className="flex-1">
                          <p className="text-sm font-semibold text-ink">Next: Build your flow</p>
                          <p className="text-xs text-ink-subtle">Extract every claim, warrant, evidence, and impact from your speech.</p>
                        </div>
                      </div>
                    )}
                  </CardContent>
                </WorkspaceCard>
              ) : (
                <WorkspaceCard key="tx-empty">
                  <CardContent className="flex flex-col gap-4 px-5 py-5">
                    <StepHeader n={2} title="Transcript" done={false} />
                    <div className="flex items-start gap-3 rounded-lg border border-lav/20 bg-lav/5 px-4 py-3">
                      <div className="flex-1">
                        <p className="text-sm font-semibold text-ink">Transcribe first</p>
                        <p className="text-xs text-ink-subtle">
                          RoundLab uses AI to transcribe your speech so it can understand what you said. Takes 10–30 seconds.
                        </p>
                      </div>
                    </div>
                    {txErr && <InlineAlert variant="danger">{txErr}</InlineAlert>}
                    <Button onClick={transcribe} disabled={transcribing} size="sm" className="w-full">
                      {transcribing ? "Transcribing…" : "Transcribe My Speech"}
                    </Button>
                  </CardContent>
                </WorkspaceCard>
              )
            )}

            {/* ── Step 3: Flow ──────────────────────────────────────────── */}
            {transcript && (
              genFlow ? (
                <motion.div key="flow-loading" {...fadeUp(0)}>
                  <LoadingCard title="Generating flow" messages={MSG_FLOW} />
                </motion.div>
              ) : argMap ? (
                <WorkspaceCard key="flow-done">
                  <CardContent className="flex flex-col gap-4 px-5 py-5">
                    <StepHeader n={3} title="Flow" done aside={
                      <Badge variant="indigo">
                        {argMap.arguments.length} arg{argMap.arguments.length !== 1 ? "s" : ""}
                      </Badge>
                    } />

                    {/* Flow Explanation */}
                    <div className="flex flex-col gap-3 rounded-lg border border-lav/10 bg-lav/5 px-4 py-3">
                      <p className="text-sm leading-relaxed text-ink">
                        <span className="font-semibold">This is your flow:</span> Each card shows one argument RoundLab heard in your speech. Green arguments are usable offense. Coach notes show what a judge may find missing.
                      </p>
                      {/* Quick Legend */}
                      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs">
                        <span className="text-ink-subtle"><span className="font-semibold text-ink">Claim</span> = what you argue</span>
                        <span className="text-ink-subtle"><span className="font-semibold text-ink">Warrant</span> = why it's true</span>
                        <span className="text-ink-subtle"><span className="font-semibold text-ink">Evidence</span> = support</span>
                        <span className="text-ink-subtle"><span className="font-semibold text-ink">Impact</span> = why it matters</span>
                      </div>
                    </div>

                    {argMap.arguments.length === 0 ? (
                      <p className="text-sm text-ink-faint">No arguments extracted.</p>
                    ) : (
                      <>
                        {/* Common Issues Summary */}
                        {(() => {
                          const allIssues = argMap.arguments.flatMap(a => a.issues);
                          const warrantIssues = allIssues.filter(i => i.toLowerCase().includes("warrant")).length;
                          const impactIssues = allIssues.filter(i => i.toLowerCase().includes("impact")).length;
                          const hasCommonIssue = warrantIssues > argMap.arguments.length / 2 || impactIssues > argMap.arguments.length / 2;

                          return hasCommonIssue ? (
                            <div className="rounded-lg border border-amber/20 bg-amber/5 px-4 py-3">
                              <p className="text-xs font-semibold text-amber">Common Pattern</p>
                              <p className="text-sm text-ink">
                                {warrantIssues > impactIssues
                                  ? "Most of your arguments need stronger warranting. Add 'because' sentences explaining why your claims are true."
                                  : "Most of your arguments need stronger impact explanation. Tell the judge why these impacts matter in the real world."}
                              </p>
                            </div>
                          ) : null;
                        })()}

                        <motion.div
                          className="grid grid-cols-1 gap-3 md:grid-cols-2"
                          variants={staggerParent(0.06)}
                          initial="hidden"
                          animate="show"
                        >
                          {argMap.arguments.map((a, i) => (
                            <ArgumentCard key={i} arg={a} index={i} />
                          ))}
                        </motion.div>
                      </>
                    )}

                    {/* Next step CTA */}
                    {!feedback && (
                      <div className="flex items-start gap-3 rounded-lg border border-lav/20 bg-lav/5 px-4 py-3">
                        <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-lav text-xs font-bold text-white">
                          4
                        </div>
                        <div className="flex-1">
                          <p className="text-sm font-semibold text-ink">Next: Get judge feedback</p>
                          <p className="text-xs text-ink-subtle">See what a judge would notice: clash, weighing, drops, and adaptation.</p>
                        </div>
                      </div>
                    )}
                  </CardContent>
                </WorkspaceCard>
              ) : (
                <WorkspaceCard key="flow-empty">
                  <CardContent className="flex flex-col gap-4 px-5 py-5">
                    <StepHeader n={3} title="Flow" done={false} />
                    {!canAnalyze ? (
                      <InlineAlert variant="danger">Transcript too short. Record at least 30 seconds.</InlineAlert>
                    ) : (
                      <div className="flex items-start gap-3 rounded-lg border border-lav/20 bg-lav/5 px-4 py-3">
                        <div className="flex-1">
                          <p className="text-sm font-semibold text-ink">Build your debate flow</p>
                          <p className="text-xs text-ink-subtle">
                            RoundLab maps out every claim, warrant, evidence, and impact. This is what a judge would flow during your speech.
                          </p>
                        </div>
                      </div>
                    )}
                    {flowErr && <InlineAlert variant="danger">{flowErr}</InlineAlert>}
                    <Button disabled={!canAnalyze || genFlow} onClick={generateFlow} size="sm" className="w-full">
                      {genFlow ? "Building Flow…" : "Build My Flow"}
                    </Button>
                  </CardContent>
                </WorkspaceCard>
              )
            )}

            {/* ── Step 4: Feedback ──────────────────────────────────────── */}
            {argMap && (
              genFb ? (
                <motion.div key="fb-loading" {...fadeUp(0)}>
                  <LoadingCard title="Generating feedback" messages={MSG_FEEDBACK} />
                </motion.div>
              ) : feedback ? (
                <WorkspaceCard key="fb-done">
                  <CardContent className="flex flex-col gap-4 px-5 py-5">
                    <StepHeader n={4} title="Feedback" done />

                    <ScoreCard score={feedback.overall_score} summary={feedback.summary} />

                    <Collapsible label="Score Breakdown" open>
                      <ScoreBreakdown scores={feedback.scores} />
                    </Collapsible>

                    {(feedback.strengths.length > 0 || feedback.weaknesses.length > 0) && (
                      <Collapsible label="Strengths & Weaknesses" open>
                        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                          {feedback.strengths.length > 0 && (
                            <div className="flex flex-col gap-2">
                              <p className="text-eyebrow text-ok">Strengths</p>
                              <ul className="flex flex-col gap-1.5">
                                {feedback.strengths.map((s, i) => (
                                  <li key={i} className="flex gap-2 text-sm text-ink-muted">
                                    <span className="shrink-0 text-ok">✓</span>{s}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                          {feedback.weaknesses.length > 0 && (
                            <div className="flex flex-col gap-2">
                              <p className="text-eyebrow text-danger">Weaknesses</p>
                              <ul className="flex flex-col gap-1.5">
                                {feedback.weaknesses.map((w, i) => (
                                  <li key={i} className="flex gap-2 text-sm text-ink-muted">
                                    <span className="shrink-0 text-danger">✕</span>{w}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                      </Collapsible>
                    )}

                    {feedback.raw_feedback?.top_3_priorities?.length ? (
                      <Collapsible label="Top 3 Priorities" open>
                        <ol className="flex flex-col gap-2">
                          {feedback.raw_feedback.top_3_priorities.map((p, i) => (
                            <li key={i} className="flex items-start gap-2.5 text-sm text-ink-muted">
                              <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-lav text-xs font-bold text-white">
                                {i + 1}
                              </span>
                              {p}
                            </li>
                          ))}
                        </ol>
                      </Collapsible>
                    ) : null}

                    {feedback.raw_feedback?.decision_logic && (
                      <Collapsible label="Decision Logic (RFD)">
                        <p className="text-sm leading-relaxed text-ink-muted">
                          {feedback.raw_feedback.decision_logic}
                        </p>
                      </Collapsible>
                    )}

                    {(feedback.raw_feedback?.dropped_or_undercovered_arguments?.length ||
                      feedback.raw_feedback?.warranting_diagnostics?.length ||
                      feedback.raw_feedback?.weighing_diagnostics?.length ||
                      feedback.raw_feedback?.evidence_diagnostics?.length) ? (
                      <Collapsible label="Coach Diagnosis" open>
                        <div className="flex flex-col gap-3">
                          {/* Dropped arguments - show as warning */}
                          {feedback.raw_feedback?.dropped_or_undercovered_arguments && feedback.raw_feedback.dropped_or_undercovered_arguments.length > 0 && (
                            <div className="flex flex-col gap-2 rounded-lg border border-danger/20 bg-danger/5 px-4 py-3">
                              <p className="text-sm font-semibold text-danger">Dropped / Undercovered</p>
                              <ul className="flex flex-col gap-1">
                                {feedback.raw_feedback.dropped_or_undercovered_arguments.map((item, i) => (
                                  <li key={i} className="text-sm text-ink-muted">· {item}</li>
                                ))}
                              </ul>
                            </div>
                          )}

                          <CoachDiagnosis
                            category="warranting"
                            label="Warranting"
                            items={feedback.raw_feedback?.warranting_diagnostics ?? []}
                          />
                          <CoachDiagnosis
                            category="weighing"
                            label="Impact Weighing"
                            items={feedback.raw_feedback?.weighing_diagnostics ?? []}
                          />
                          <CoachDiagnosis
                            category="evidence"
                            label="Evidence Use"
                            items={feedback.raw_feedback?.evidence_diagnostics ?? []}
                          />
                        </div>
                      </Collapsible>
                    ) : null}

                    {feedback.raw_feedback?.judge_adaptation_notes && (
                      <Collapsible label="Judge Adaptation">
                        <p className="text-sm leading-relaxed text-ink-muted">
                          {feedback.raw_feedback.judge_adaptation_notes}
                        </p>
                      </Collapsible>
                    )}

                    {feedback.raw_feedback?.recommendations?.length ? (
                      <Collapsible label="Recommendations">
                        <ul className="flex flex-col gap-1.5">
                          {feedback.raw_feedback.recommendations.map((r, i) => (
                            <li key={i} className="flex gap-2 text-sm text-ink-muted">
                              <span className="shrink-0 text-ink-faint">→</span>{r}
                            </li>
                          ))}
                        </ul>
                      </Collapsible>
                    ) : null}

                    {/* Feedback Rating */}
                    {!feedback.helpful_rating && !feedbackRated ? (
                      <div className="flex flex-col gap-2 rounded-lg border border-hairline bg-surface-2 px-4 py-3">
                        <p className="text-xs font-medium text-ink-subtle">Was this feedback useful?</p>
                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => rateFeedback("helpful")}
                            disabled={ratingFeedback}
                            className="flex items-center gap-1.5 rounded-md border border-hairline bg-surface-1 px-3 py-1.5 text-xs text-ink-subtle transition-colors hover:border-ok/40 hover:bg-ok/5 hover:text-ok disabled:opacity-50"
                          >
                            <ThumbsUp size={12} />
                            Helpful
                          </button>
                          <button
                            type="button"
                            onClick={() => rateFeedback("not_helpful")}
                            disabled={ratingFeedback}
                            className="flex items-center gap-1.5 rounded-md border border-hairline bg-surface-1 px-3 py-1.5 text-xs text-ink-subtle transition-colors hover:border-danger/40 hover:bg-danger/5 hover:text-danger disabled:opacity-50"
                          >
                            <ThumbsDown size={12} />
                            Not helpful
                          </button>
                        </div>
                        <p className="text-xs text-ink-faint">Your rating helps improve RoundLab for students.</p>
                      </div>
                    ) : (feedback.helpful_rating || feedbackRated) && (
                      <div className="flex items-center gap-2 rounded-lg border border-ok/20 bg-ok/5 px-4 py-2">
                        <Check size={12} className="text-ok" />
                        <p className="text-xs text-ok">Thanks for the feedback!</p>
                      </div>
                    )}

                    {/* Next step CTA - Generate Drills */}
                    {drills.length === 0 && (
                      <div className="flex items-start gap-3 rounded-lg border border-lav/20 bg-lav/5 px-4 py-3">
                        <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-lav text-xs font-bold text-white">
                          5
                        </div>
                        <div className="flex-1">
                          <p className="text-sm font-semibold text-ink">Next: Generate practice drills</p>
                          <p className="text-xs text-ink-subtle">Get 3 personalized drills targeting your weakest skills. Practice them before re-recording.</p>
                        </div>
                      </div>
                    )}
                  </CardContent>
                </WorkspaceCard>
              ) : (
                <WorkspaceCard key="fb-empty">
                  <CardContent className="flex flex-col gap-4 px-5 py-5">
                    <StepHeader n={4} title="Feedback" done={false} />
                    {!canAnalyze ? (
                      <InlineAlert variant="danger">Transcript too short for meaningful feedback.</InlineAlert>
                    ) : (
                      <div className="flex items-start gap-3 rounded-lg border border-lav/20 bg-lav/5 px-4 py-3">
                        <div className="flex-1">
                          <p className="text-sm font-semibold text-ink">Get judge-style feedback</p>
                          <p className="text-xs text-ink-subtle">
                            RoundLab scores your speech like a debate judge: clash, weighing, extensions, drops, and judge adaptation.
                          </p>
                        </div>
                      </div>
                    )}
                    {fbErr && <InlineAlert variant="danger">{fbErr}</InlineAlert>}
                    <Button disabled={!canAnalyze || genFb} onClick={generateFeedback} size="sm" className="w-full">
                      {genFb ? "Generating Feedback…" : "Get Judge Feedback"}
                    </Button>
                  </CardContent>
                </WorkspaceCard>
              )
            )}

            {/* ── Step 5: Drills ────────────────────────────────────────── */}
            {feedback && (
              genDrills ? (
                <motion.div key="drills-loading" {...fadeUp(0)}>
                  <LoadingCard title="Generating drills" messages={MSG_DRILLS} />
                </motion.div>
              ) : drills.length > 0 ? (
                <WorkspaceCard key="drills-done">
                  <CardContent className="flex flex-col gap-4 px-5 py-5">
                    <StepHeader
                      n={5}
                      title="Practice Drills"
                      done
                      aside={
                        <Badge variant="indigo">
                          {drills.filter((d) => d.status !== "assigned").length}/{drills.length} attempted
                        </Badge>
                      }
                    />
                    <div className="flex items-start gap-3 rounded-lg border border-lav/20 bg-lav/5 px-4 py-3">
                      <div className="flex-1">
                        <p className="text-sm font-semibold text-ink">Practice these drills</p>
                        <p className="text-xs text-ink-subtle">
                          Each drill targets a specific weakness from your feedback. Record yourself doing the exercise, then re-record your speech to see improvement.
                        </p>
                      </div>
                    </div>
                    <div className="flex flex-col gap-2">
                      {drills.map((drill, i) => (
                        <DrillCard
                          key={drill.id}
                          drill={drill}
                          index={i}
                          onStatusChange={updateDrillStatus}
                          updatingId={updatingDrill}
                          userId={userId ?? undefined}
                        />
                      ))}
                    </div>

                    {/* Re-record CTA after drills */}
                    <div className="flex items-center gap-3 rounded-lg border border-hairline bg-surface-2 px-4 py-3">
                      <div className="flex-1">
                        <p className="text-sm font-semibold text-ink">Ready to re-record?</p>
                        <p className="text-xs text-ink-subtle">Practice a few drills above, then start a fresh attempt to track your progress.</p>
                      </div>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={startNewAttempt}
                        className="shrink-0 gap-1.5 text-lav hover:border-lav/40"
                      >
                        <RefreshCw size={11} />
                        New Attempt
                      </Button>
                    </div>
                  </CardContent>
                </WorkspaceCard>
              ) : (
                <WorkspaceCard key="drills-empty">
                  <CardContent className="flex flex-col gap-4 px-5 py-5">
                    <StepHeader n={5} title="Practice Drills" done={false} />
                    <div className="flex items-start gap-3 rounded-lg border border-lav/20 bg-lav/5 px-4 py-3">
                      <div className="flex-1">
                        <p className="text-sm font-semibold text-ink">Create personalized drills</p>
                        <p className="text-xs text-ink-subtle">
                          RoundLab analyzes your feedback to generate 3 targeted practice exercises. Each drill helps you improve a specific skill.
                        </p>
                      </div>
                    </div>
                    {drillErr && <InlineAlert variant="danger">{drillErr}</InlineAlert>}
                    <Button onClick={generateDrills} disabled={genDrills} size="sm" className="w-full">
                      {genDrills ? "Creating Drills…" : "Create My Practice Drills"}
                    </Button>
                  </CardContent>
                </WorkspaceCard>
              )
            )}

          </AnimatePresence>
        </motion.div>
      </main>

      <DeleteDialog
        open={delOpen}
        onOpenChange={(v) => { if (!v && !deleting) { setDelOpen(false); setDeleteErr(""); } }}
        title="Delete this session?"
        description={`"${speech.title}" will be permanently deleted along with its transcript, flow, and feedback.`}
        onConfirm={deleteSession}
        isDeleting={deleting}
        error={deleteErr}
      />
    </>
  );
}
