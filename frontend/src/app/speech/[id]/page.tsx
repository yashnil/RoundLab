"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { motion, AnimatePresence } from "motion/react";
import {
  Check, ChevronDown, ChevronUp, FileText,
  Mic, RefreshCw, Trash2, Upload, ThumbsUp, ThumbsDown, Target, Copy,
  ShieldAlert, Sparkles,
} from "lucide-react";
import { useCopy } from "@/lib/useCopy";
import AppNav from "@/components/AppNav";
import WorkflowStepper from "@/components/WorkflowStepper";
import RecordingStudio from "@/components/RecordingStudio";
import UploadDropzone from "@/components/UploadDropzone";
import TranscriptPanel from "@/components/TranscriptPanel";
import JudgeModeSelector, { type JudgeViewMode } from "@/components/JudgeModeSelector";
import ReportVerdictPanel from "@/components/ReportVerdictPanel";
import FlowBoard from "@/components/FlowBoard";
import ScoreBreakdown from "@/components/ScoreBreakdown";
import LoadingCard from "@/components/LoadingCard";
import DeleteDialog from "@/components/DeleteDialog";
import EmptyStateCard from "@/components/EmptyStateCard";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { createClient } from "@/lib/supabase";
import { apiFetch } from "@/lib/api";
import { fadeUp, staggerParent, staggerChild, T, EASE } from "@/lib/motion";
import DrillCard from "@/components/DrillCard";
import FlowTable from "@/components/FlowTable";
import PracticeLoopCTA from "@/components/PracticeLoopCTA";
import ImprovementComparisonCard from "@/components/ImprovementComparisonCard";
import CoachMarginNote from "@/components/CoachMarginNote";
import EvidenceSupportPanel from "@/components/EvidenceSupportPanel";
import FeedbackRating from "@/components/FeedbackRating";
import ConfusionReport from "@/components/ConfusionReport";
import { getCoachNote, deriveFlowCoachNoteType, getPrimaryIssue, deriveEvidenceRiskSummary } from "@/lib/debateHelpers";
import type { ArgumentMap, Drill, DrillStatus, FeedbackReport, Speech, Transcript } from "@/types";
import type { DebateIssue, ClaimEvidenceCheck, EvidenceCheckResult, EvidenceDocument } from "@/types";
import type { RecordState } from "@/components/RecordingStudio";

// ── Constants ──────────────────────────────────────────────────────────────────

const ALLOWED_EXT = ["mp3", "wav", "m4a", "webm", "ogg", "mp4"];
const MAX_BYTES   = 50 * 1024 * 1024;

const TYPE_LABEL: Record<string, string> = {
  constructive: "Constructive", rebuttal: "Rebuttal",
  summary: "Summary", final_focus: "Final Focus", crossfire: "Crossfire",
};

const MSG_TRANSCRIBE = ["Preparing your speech", "Reading your audio", "Processing speech content", "Almost ready"];
const MSG_FLOW       = ["Finding claims and warrants", "Mapping evidence and impacts", "Building your flow", "Analyzing argument structure"];
const MSG_FEEDBACK   = ["Reading your speech", "Mapping arguments", "Evaluating the case", "Building your coaching report"];
const MSG_DRILLS     = ["Reviewing your feedback", "Identifying skill gaps", "Creating practice drills"];
const MSG_UNIFIED_ANALYSIS = ["Reading your speech", "Mapping arguments", "Building your flow", "Evaluating the case", "Creating your coaching report"];

// Current scoring version - should match backend SCORING_VERSION
const CURRENT_SCORING_VERSION = "pf_rubric_v3_recalibrated_2026_06_04";

const STAGE_MESSAGES: Record<"transcript" | "flow" | "feedback", { title: string; messages: string[] }> = {
  transcript: {
    title: "Preparing your speech",
    messages: ["Transcribing audio", "Processing speech text", "Analyzing word choice"],
  },
  flow: {
    title: "Mapping arguments",
    messages: ["Identifying claims", "Extracting warrants and evidence", "Building your flow table"],
  },
  feedback: {
    title: "Applying rubric",
    messages: ["Evaluating structure and warranting", "Scoring each dimension", "Building coaching report"],
  },
};

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
              className="flex h-5 w-5 shrink-0 items-center justify-center rounded-[3px] border border-hairline-strong text-[11px] font-bold text-ink-faint"
              style={{ fontFamily: "var(--font-jetbrains-mono)" }}
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
        <span className="section-stamp">{label}</span>
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

  return (
    <div className="flex flex-col gap-2 rounded-lg border border-hairline bg-surface-2 px-4 py-3">
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm font-semibold text-ink">{label}</p>
        <span className={`text-xs font-medium ${statusColor} capitalize`}>
          {status === "needs-work" ? "Needs Work" : status === "missing" ? "Missing" : "Strong"}
        </span>
      </div>

      {/* Display actual diagnostics from LLM (includes topic-aware examples) */}
      <div className="flex flex-col gap-2">
        {items.map((item, i) => (
          <p key={i} className="text-sm leading-relaxed text-ink-muted whitespace-pre-wrap">{item}</p>
        ))}
      </div>

      {/* Disclaimer for examples */}
      {items.some(item => item.toLowerCase().includes("before:") || item.toLowerCase().includes("after:")) && (
        <div className="flex items-start gap-2 rounded-md border border-amber/20 bg-amber/5 px-3 py-2">
          <p className="text-xs text-amber">⚠ Model example only — adapt to your arguments, don't copy word-for-word</p>
        </div>
      )}
    </div>
  );
}

/** Wraps a workspace section card — animates in when it first appears */
function WorkspaceCard({ children, glow }: { children: React.ReactNode; glow?: boolean }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: EASE }}
    >
      <Card
        className={glow ? "beam-top" : undefined}
        style={glow ? { boxShadow: "0 0 40px -12px oklch(0.510 0.156 278 / 0.18)" } : undefined}
      >
        {children}
      </Card>
    </motion.div>
  );
}



// ── Flow Summary Helper ────────────────────────────────────────────────────────

function FlowSummary({ argMap }: { argMap: ArgumentMap }) {
  const offenseArgs = argMap.arguments.filter(a => a.argument_type === "offense");
  const allIssues = argMap.arguments.flatMap(a => a.issues);
  const warrantIssues = allIssues.filter(i => i.toLowerCase().includes("warrant")).length;
  const impactIssues = allIssues.filter(i => i.toLowerCase().includes("impact")).length;
  const evidenceIssues = allIssues.filter(i => i.toLowerCase().includes("evidence") || i.toLowerCase().includes("unsupported")).length;

  // Find strongest argument (highest confidence, offense type preferred)
  const strongestArg = argMap.arguments.reduce((best, curr) => {
    if (!best) return curr;
    const currScore = (curr.confidence ?? 0) + (curr.argument_type === "offense" ? 0.1 : 0);
    const bestScore = (best.confidence ?? 0) + (best.argument_type === "offense" ? 0.1 : 0);
    return currScore > bestScore ? curr : best;
  }, argMap.arguments[0]);

  // Determine most common weakness
  let commonWeakness = "";
  if (warrantIssues > Math.max(impactIssues, evidenceIssues)) {
    commonWeakness = "Warranting";
  } else if (impactIssues > Math.max(warrantIssues, evidenceIssues)) {
    commonWeakness = "Impact development";
  } else if (evidenceIssues > 0) {
    commonWeakness = "Evidence connection";
  } else if (allIssues.length > 0) {
    commonWeakness = "Argument structure";
  }

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      <div className="flex flex-col gap-1 rounded-lg border border-hairline bg-surface-2 px-4 py-3">
        <p className="text-xs text-ink-faint">Total Arguments</p>
        <p className="text-2xl font-bold text-ink">{argMap.arguments.length}</p>
        <p className="text-xs text-ink-subtle">{offenseArgs.length} offense</p>
      </div>

      {strongestArg && (
        <div className="flex flex-col gap-1 rounded-lg border border-ok/20 bg-ok/5 px-4 py-3">
          <p className="text-xs text-ok">Strongest Argument</p>
          <p className="text-sm font-semibold text-ink line-clamp-2">{strongestArg.label}</p>
        </div>
      )}

      {commonWeakness && (
        <div className="flex flex-col gap-1 rounded-lg border border-amber/20 bg-amber/5 px-4 py-3">
          <p className="text-xs text-amber">Most Common Issue</p>
          <p className="text-sm font-semibold text-ink">{commonWeakness}</p>
          <p className="text-xs text-ink-subtle">{allIssues.length} total issues</p>
        </div>
      )}
    </div>
  );
}

// ── Coach annotation sub-components ───────────────────────────────────────────

/**
 * Renders a CoachMarginNote for the highest-severity structured issue.
 * Shows nothing if no structured issues exist.
 */
function TopIssueCoachNote({ issues }: { issues?: DebateIssue[] }) {
  const top = getPrimaryIssue(issues);
  if (!top) return null;
  const cfg = getCoachNote(top.issue_type);
  if (!cfg) return null;
  return <CoachMarginNote type={cfg.type} note={cfg.note} />;
}

/**
 * Renders a CoachMarginNote derived from the argument map's most common issue.
 * Only appears when at least one argument has a flagged issue.
 * Provides a flow-level annotation above the FlowTable.
 */
function FlowCoachNote({ args }: { args: Array<{ issues: string[] }> }) {
  const issueType = deriveFlowCoachNoteType(args);
  if (!issueType) return null;
  const cfg = getCoachNote(issueType);
  if (!cfg) return null;
  return <CoachMarginNote type={cfg.type} note={cfg.note} label="Flow note" />;
}

const LENS_NOTE_TEXT: Record<JudgeViewMode, string> = {
  coach: "Coach lens — showing fix actions and drill targets for each argument.",
  lay:   "Lay lens — highlighting impact clarity, persuasion, and judge comprehension.",
  flow:  "Flow lens — highlighting dropped arguments, extensions, and warrant depth.",
  tech:  "Tech lens — highlighting evidence quality, warrant support, and weighing.",
};

function FlowLensNote({ judgeMode }: { judgeMode: JudgeViewMode }) {
  const isDetailLens = judgeMode === "flow" || judgeMode === "tech";
  return (
    <div className="flex flex-col gap-2 rounded-lg border border-lav/10 bg-lav/5 px-4 py-3 text-xs">
      <p className="text-ink-subtle">{LENS_NOTE_TEXT[judgeMode]}</p>
      <div className="flex flex-col gap-1 border-t border-lav/10 pt-2">
        <div className="flex flex-wrap gap-x-4 gap-y-0.5">
          <span className="text-ink-faint"><span className="font-semibold text-ink-subtle">Offense</span> = winning argument</span>
          <span className="text-ink-faint"><span className="font-semibold text-ink-subtle">Defense</span> = answers opponent</span>
          <span className="text-ink-faint"><span className="font-semibold text-ink-subtle">Weighing</span> = impact comparison</span>
        </div>
        {isDetailLens && (
          <div className="flex flex-wrap gap-x-4 gap-y-0.5 pt-0.5">
            <span className="text-ink-faint"><span className="font-semibold text-ink-subtle">Claim</span> = what you argue</span>
            <span className="text-ink-faint"><span className="font-semibold text-ink-subtle">Warrant</span> = why it&apos;s true</span>
            <span className="text-ink-faint"><span className="font-semibold text-ink-subtle">Evidence</span> = support</span>
            <span className="text-ink-faint"><span className="font-semibold text-ink-subtle">Impact</span> = why it matters</span>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Helpers ────────────────────────────────────────────────────────────────────

/**
 * Defensively recompute overall score from visible dimension scores.
 * This ensures the displayed overall score always matches the sum of dimension bars.
 */
function getVerifiedOverallScore(feedback: FeedbackReport | null): number | null {
  if (!feedback?.scores) return feedback?.overall_score ?? null;

  const sum =
    feedback.scores.clash +
    feedback.scores.weighing +
    feedback.scores.extensions +
    feedback.scores.drops +
    feedback.scores.judge_adaptation;

  // If stored overall_score doesn't match, use recomputed sum
  if (feedback.overall_score !== null && feedback.overall_score !== sum) {
    console.warn(
      `[Score Verification] Stored overall_score (${feedback.overall_score}) doesn't match dimension sum (${sum}). Using sum.`
    );
  }

  return sum;
}

/**
 * Check if a feedback report is stale and needs regeneration.
 * Returns true if the report uses an older scoring version.
 */
function isReportStale(feedback: FeedbackReport | null): boolean {
  if (!feedback) return false;

  // If raw_feedback contains scoring_version, check if it matches current
  const reportVersion = feedback.raw_feedback?.scoring_version;
  if (reportVersion && reportVersion !== CURRENT_SCORING_VERSION) {
    return true;
  }

  // If scoring_version is missing (old reports), consider stale
  if (!reportVersion) {
    return true;
  }

  return false;
}

// ── Main ───────────────────────────────────────────────────────────────────────

export default function SpeechPage() {
  const { id: speechId } = useParams<{ id: string }>();
  const router = useRouter();

  const [userId,     setUserId]     = useState<string | null>(null);
  const [speech,     setSpeech]     = useState<Speech | null>(null);
  const [pageLoad,   setPageLoad]   = useState(true);
  const [pageErr,    setPageErr]    = useState("");

  const [mode,       setMode]       = useState<"record" | "upload" | "paste">("record");
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

  const [pastedText,   setPastedText]   = useState("");
  const [submittingText, setSubmittingText] = useState(false);
  const [pasteErr,     setPasteErr]     = useState("");

  const [transcript,   setTranscript]   = useState<Transcript | null>(null);
  const [transcribing, setTranscribing] = useState(false);
  const [txErr,        setTxErr]        = useState("");
  const [argMap,       setArgMap]       = useState<ArgumentMap | null>(null);
  const [genFlow,      setGenFlow]      = useState(false);
  const [flowErr,      setFlowErr]      = useState("");
  const [feedback,     setFeedback]     = useState<FeedbackReport | null>(null);
  const [genFb,        setGenFb]        = useState(false);
  const [fbErr,        setFbErr]        = useState("");

  // Unified analysis workflow state
  const [analyzingUnified, setAnalyzingUnified] = useState(false);
  const [unifiedAnalysisErr, setUnifiedAnalysisErr] = useState("");
  const [analysisStage, setAnalysisStage] = useState<"transcript" | "flow" | "feedback" | null>(null);

  const [drills,        setDrills]        = useState<Drill[]>([]);
  const [genDrills,     setGenDrills]     = useState(false);
  const [drillErr,      setDrillErr]      = useState("");
  const [updatingDrill, setUpdatingDrill] = useState<string | null>(null);

  const [ratingFeedback, setRatingFeedback] = useState(false);
  const [feedbackRated, setFeedbackRated] = useState(false);
  const [copyRFD, rfdCopied] = useCopy();

  const [showTableView, setShowTableView] = useState(false);
  const [judgeViewMode, setJudgeViewMode] = useState<JudgeViewMode>("coach");

  const [delOpen,  setDelOpen]  = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteErr, setDeleteErr] = useState("");

  // Re-record comparison (fetched best-effort when speech has parent_speech_id)
  const [comparison, setComparison] = useState<import("@/types").SpeechComparisonResult | null>(null);

  // Evidence-Aware Coach (Phase 2)
  // hasLibrary: null = loading, false = no parsed docs, true = at least one parsed doc
  const [hasLibrary, setHasLibrary] = useState<boolean | null>(null);
  const [savedChecks, setSavedChecks] = useState<ClaimEvidenceCheck[]>([]);
  const [freshResults, setFreshResults] = useState<EvidenceCheckResult[]>([]);
  const [checkingEvidence, setCheckingEvidence] = useState(false);
  const [checkingIndex, setCheckingIndex] = useState<number>(-1);
  const [evidenceCheckErr, setEvidenceCheckErr] = useState("");
  const [genEvidenceDrills, setGenEvidenceDrills] = useState(false);
  const [evidenceDrillErr, setEvidenceDrillErr] = useState("");
  const [evidenceDrillsDone, setEvidenceDrillsDone] = useState(false);

  const mrRef   = useRef<MediaRecorder | null>(null);
  const chunks  = useRef<Blob[]>([]);
  const stream  = useRef<MediaStream | null>(null);
  const timer   = useRef<ReturnType<typeof setInterval> | null>(null);
  const extRef  = useRef("webm");
  const urlRef  = useRef<string | null>(null);
  const autoAnalysisStartedRef = useRef(false);

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
        // Fetch improvement comparison if this is a re-record (best-effort, non-blocking)
        if (s.parent_speech_id) {
          apiFetch<import("@/types").SpeechComparisonResult>(
            `/speeches/${speechId}/comparison?user_id=${uid}`
          ).then(setComparison).catch(() => {});
        }
        // Load all related data in parallel for faster initial page load
        const [txData, argData, fbData, drillData] = await Promise.allSettled([
          apiFetch<Transcript>(`/speeches/${speechId}/transcript?user_id=${uid}`),
          apiFetch<ArgumentMap>(`/speeches/${speechId}/argument-map?user_id=${uid}`),
          apiFetch<FeedbackReport>(`/speeches/${speechId}/feedback?user_id=${uid}`),
          apiFetch<Drill[]>(`/speeches/${speechId}/drills?user_id=${uid}`),
        ]);
        if (txData.status === "fulfilled") setTranscript(txData.value);
        if (argData.status === "fulfilled") setArgMap(argData.value);
        if (fbData.status === "fulfilled") setFeedback(fbData.value);
        if (drillData.status === "fulfilled") setDrills(drillData.value);

        // Evidence library + saved checks — best-effort, non-blocking
        Promise.all([
          apiFetch<EvidenceDocument[]>(`/documents?user_id=${uid}`).catch(() => [] as EvidenceDocument[]),
          apiFetch<ClaimEvidenceCheck[]>(`/speeches/${speechId}/evidence-checks?user_id=${uid}`).catch(() => [] as ClaimEvidenceCheck[]),
        ]).then(([docs, checks]) => {
          setHasLibrary((docs as EvidenceDocument[]).some((d) => d.status === "parsed"));
          if ((checks as ClaimEvidenceCheck[]).length > 0) setSavedChecks(checks as ClaimEvidenceCheck[]);
        });
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
      // Use recSecs (the live timer) as duration_seconds for recordings
      const upd = await apiFetch<Speech>(`/speeches/${speechId}?user_id=${userId}`, {
        method: "PATCH", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ audio_url: path, duration_seconds: recSecs > 0 ? recSecs : undefined }),
      });
      setSpeech(upd);
      if (urlRef.current) { URL.revokeObjectURL(urlRef.current); urlRef.current = null; }
      setRecUrl(null); setRecBlob(null); setRecState("idle");

      // Auto-start analysis after recording upload completes
      // Pass the fresh upd object to avoid stale state race conditions
      await maybeStartAutoAnalysis(upd);
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

  /** Resolve audio duration in seconds from a File by loading it into an HTMLAudioElement. */
  async function getFileDuration(file: File): Promise<number | null> {
    return new Promise((resolve) => {
      try {
        const url = URL.createObjectURL(file);
        const audio = new Audio(url);
        audio.onloadedmetadata = () => {
          URL.revokeObjectURL(url);
          const dur = audio.duration;
          resolve(Number.isFinite(dur) && dur > 0 ? Math.round(dur) : null);
        };
        audio.onerror = () => { URL.revokeObjectURL(url); resolve(null); };
        // Safety timeout — don't block upload on slow metadata load
        setTimeout(() => { URL.revokeObjectURL(url); resolve(null); }, 3000);
      } catch { resolve(null); }
    });
  }

  async function uploadFile() {
    if (!selFile || !userId) return;
    setUpErr(""); setUploading(true);
    const ext  = selFile.name.split(".").pop()!.toLowerCase();
    const path = `${userId}/${speechId}/audio.${ext}`;
    try {
      // Resolve duration before uploading (non-blocking — uses 3s timeout)
      const durationSeconds = await getFileDuration(selFile);

      const sb = createClient();
      const { error: se } = await sb.storage.from("audio").upload(path, selFile, { upsert: true });
      if (se) { setUpErr(`Upload failed: ${se.message}`); return; }
      const upd = await apiFetch<Speech>(`/speeches/${speechId}?user_id=${userId}`, {
        method: "PATCH", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ audio_url: path, duration_seconds: durationSeconds ?? undefined }),
      });
      setSpeech(upd); setSelFile(null);

      // Auto-start analysis after file upload completes
      // Pass the fresh upd object to avoid stale state race conditions
      await maybeStartAutoAnalysis(upd);
    } catch (err: unknown) {
      setUpErr(err instanceof Error ? err.message : "Upload failed.");
    } finally { setUploading(false); }
  }

  function clearFile() { setSelFile(null); setFileErr(""); }

  async function submitPastedText() {
    if (!pastedText.trim() || !userId) return;
    setPasteErr(""); setSubmittingText(true);
    try {
      const txResult = await apiFetch<Transcript>(`/speeches/${speechId}/transcript?user_id=${userId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: pastedText.trim() }),
      });
      setTranscript(txResult);
      // Update speech status
      const updatedSpeech = await apiFetch<Speech>(`/speeches/${speechId}?user_id=${userId}`);
      setSpeech(updatedSpeech);
      setPastedText("");
    } catch (err: unknown) {
      setPasteErr(err instanceof Error ? err.message : "Failed to save transcript.");
    } finally { setSubmittingText(false); }
  }

  // ── Reset audio ────────────────────────────────────────────────────────────

  async function resetAudio() {
    if (!userId) return;
    setResetting(true);
    try {
      const upd = await apiFetch<Speech>(`/speeches/${speechId}/reset-audio?user_id=${userId}`, { method: "POST" });
      setSpeech(upd);
      setTranscript(null); setArgMap(null); setFeedback(null);
      setRecState("idle"); setRecUrl(null); setRecBlob(null); setRecErr("");
      autoAnalysisStartedRef.current = false; // Reset auto-analysis flag for new upload
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

  // ── Unified Analysis Workflow ──────────────────────────────────────────────

  async function analyzeMySpeech(options?: {
    speechOverride?: Speech;
    transcriptOverride?: Transcript | null;
    autoStartedFromUpload?: boolean;
  }) {
    // Use fresh data if provided, otherwise fall back to React state
    const activeSpeech = options?.speechOverride ?? speech;
    if (!userId || !activeSpeech) return;
    if (analyzingUnified) return; // Prevent double-clicks

    const autoStarted = options?.autoStartedFromUpload ?? false;
    console.log(`[Analyze] ${autoStarted ? 'Auto-started after upload' : 'Manual trigger'}, audio_url=${activeSpeech.audio_url ? 'exists' : 'missing'}`);

    setUnifiedAnalysisErr("");
    setAnalyzingUnified(true);
    setAnalysisStage("transcript");

    try {
      // Track current state with local variables to avoid stale state bugs
      let currentTranscript = options?.transcriptOverride ?? transcript;
      let currentArgMap = argMap;
      let currentFeedback = feedback;

      // Step 1: Ensure transcript/text exists
      if (!currentTranscript) {
        if (activeSpeech.audio_url) {
          setTxErr("");
          console.log("[Analyze] Step 1: Generating transcript from audio_url=" + activeSpeech.audio_url);
          try {
            const txResult = await apiFetch<Transcript>(`/speeches/${speechId}/transcribe?user_id=${userId}`, { method: "POST" });
            if (!txResult || !txResult.text) {
              // If POST didn't return data, try GET
              const fetchedTx = await apiFetch<Transcript>(`/speeches/${speechId}/transcript?user_id=${userId}`);
              currentTranscript = fetchedTx;
              setTranscript(fetchedTx);
            } else {
              currentTranscript = txResult;
              setTranscript(txResult);
            }
            console.log("[Analyze] Step 1: Transcript ready, word_count=" + currentTranscript?.word_count);
          } catch (e: unknown) {
            const msg = e instanceof Error ? e.message : "Transcription failed.";
            console.error("[Analyze] Step 1 failed:", msg);
            setTxErr(msg);
            throw new Error(msg);
          }
        } else {
          throw new Error("Add speech text or upload audio first.");
        }
      }

      // Verify we have transcript before continuing
      if (!currentTranscript || !currentTranscript.text) {
        throw new Error("Could not prepare speech text. Please try again.");
      }

      // Step 2: Generate flow if missing
      if (!currentArgMap) {
        setAnalysisStage("flow");
        setFlowErr("");
        console.log("[Analyze] Step 2: Generating argument map...");
        try {
          const flowResult = await apiFetch<ArgumentMap>(`/speeches/${speechId}/extract-arguments?user_id=${userId}`, { method: "POST" });
          if (!flowResult || !flowResult.arguments) {
            // If POST didn't return data, try GET
            const fetchedFlow = await apiFetch<ArgumentMap>(`/speeches/${speechId}/argument-map?user_id=${userId}`);
            currentArgMap = fetchedFlow;
            setArgMap(fetchedFlow);
          } else {
            currentArgMap = flowResult;
            setArgMap(flowResult);
          }
          console.log("[Analyze] Step 2: Flow ready, arguments=" + currentArgMap?.arguments?.length);
        } catch (e: unknown) {
          const msg = e instanceof Error ? e.message : "Flow generation failed.";
          console.error("[Analyze] Step 2 failed:", msg);
          setFlowErr(msg);
          throw new Error(msg);
        }
      }

      // Verify we have argument map before continuing
      if (!currentArgMap) {
        throw new Error("Could not generate argument flow. Please try again.");
      }

      // Step 3: Generate feedback if missing
      if (!currentFeedback) {
        setAnalysisStage("feedback");
        setFbErr("");
        console.log("[Analyze] Step 3: Generating feedback...");
        try {
          const fbResult = await apiFetch<FeedbackReport>(`/speeches/${speechId}/generate-feedback?user_id=${userId}`, { method: "POST" });
          if (!fbResult || typeof fbResult.overall_score !== 'number') {
            // If POST didn't return data, try GET
            const fetchedFb = await apiFetch<FeedbackReport>(`/speeches/${speechId}/feedback?user_id=${userId}`);
            currentFeedback = fetchedFb;
            setFeedback(fetchedFb);
          } else {
            currentFeedback = fbResult;
            setFeedback(fbResult);
          }
          console.log("[Analyze] Step 3: Feedback ready, score=" + currentFeedback?.overall_score);
        } catch (e: unknown) {
          const msg = e instanceof Error ? e.message : "Feedback generation failed.";
          console.error("[Analyze] Step 3 failed:", msg);
          setFbErr(msg);
          throw new Error(msg);
        }
      }

      // Verify we have feedback
      if (!currentFeedback) {
        throw new Error("Could not generate coaching report. Please try again.");
      }

      // Success - all steps completed
      console.log("[Analyze] ✓ All steps completed successfully");
      setAnalysisStage(null);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Analysis failed. Please try again.";
      console.error("[Analyze] Pipeline failed:", msg);
      setUnifiedAnalysisErr(msg);
    } finally {
      setAnalyzingUnified(false);
      setAnalysisStage(null);
    }
  }

  /** Auto-start analysis after audio upload (called once per audio upload event) */
  async function maybeStartAutoAnalysis(uploadedSpeech: Speech) {
    // Guard against duplicate auto-analysis
    if (autoAnalysisStartedRef.current) {
      console.log("[AutoAnalyze] Already started, skipping");
      return;
    }

    // Don't auto-analyze if already analyzing
    if (analyzingUnified) {
      console.log("[AutoAnalyze] Analysis already in progress, skipping");
      return;
    }

    // Don't auto-analyze if feedback already exists
    if (feedback) {
      console.log("[AutoAnalyze] Feedback already exists, skipping");
      return;
    }

    // Verify the uploaded speech actually has audio
    if (!uploadedSpeech.audio_url) {
      console.warn("[AutoAnalyze] Uploaded speech has no audio_url, skipping auto-analysis");
      return;
    }

    // Mark as started to prevent duplicates
    autoAnalysisStartedRef.current = true;
    console.log("[AutoAnalyze] Starting automatic analysis with fresh speech object, audio_url=" + uploadedSpeech.audio_url);

    // Start the analysis pipeline with the fresh uploaded speech object
    await analyzeMySpeech({
      speechOverride: uploadedSpeech,
      autoStartedFromUpload: true,
    });
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

  // ── Evidence support check ─────────────────────────────────────────────────

  async function runAllEvidenceChecks() {
    if (!userId || !argMap || argMap.arguments.length === 0) return;
    setCheckingEvidence(true);
    setEvidenceCheckErr("");
    setFreshResults([]);

    const results: EvidenceCheckResult[] = [];
    for (let i = 0; i < argMap.arguments.length; i++) {
      const arg = argMap.arguments[i];
      setCheckingIndex(i);
      try {
        const result = await apiFetch<EvidenceCheckResult>(
          `/speeches/${speechId}/evidence-check`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              user_id: userId,
              argument_label: arg.label,
              claim_text: arg.claim,
              evidence_text_from_speech: arg.evidence ?? undefined,
            }),
          },
        );
        results.push(result);
      } catch {
        results.push({
          argument_label: arg.label,
          claim_text: arg.claim,
          evidence_text_from_speech: arg.evidence ?? null,
          matched_card: null,
          support_level: "unverifiable",
          explanation: "Check failed — please try again.",
        });
      }
    }

    setFreshResults(results);
    setCheckingIndex(-1);
    setCheckingEvidence(false);
  }

  async function generateEvidenceDrills() {
    if (!userId) return;
    setGenEvidenceDrills(true);
    setEvidenceDrillErr("");
    setEvidenceDrillsDone(false);
    try {
      const newDrills = await apiFetch<Drill[]>(
        `/speeches/${speechId}/evidence-drills?user_id=${encodeURIComponent(userId)}`,
        { method: "POST" },
      );
      if (newDrills.length > 0) {
        setDrills((prev) => {
          const existingIds = new Set(prev.map((d) => d.id));
          return [...prev, ...newDrills.filter((d) => !existingIds.has(d.id))];
        });
      }
      setEvidenceDrillsDone(true);
    } catch (err: unknown) {
      const raw = err instanceof Error ? err.message : "";
      console.error("generateEvidenceDrills:", raw);
      const isConstraintErr =
        raw.toLowerCase().includes("constraint") ||
        raw.toLowerCase().includes("violates") ||
        raw.toLowerCase().includes("order");
      setEvidenceDrillErr(
        isConstraintErr
          ? "Evidence drill could not be saved — drill order was invalid. Refresh and try again."
          : raw
          ? `Evidence drill could not be saved: ${raw}`
          : "Evidence drill could not be saved. Please try again.",
      );
    } finally {
      setGenEvidenceDrills(false);
    }
  }

  // ── States ─────────────────────────────────────────────────────────────────

  if (pageLoad) {
    return (
      <>
        <AppNav />
        <main className="min-h-screen bg-canvas">
          <div className="mx-auto flex max-w-5xl flex-col gap-5 px-6 py-9">
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
          <div className="mx-auto max-w-5xl px-6 py-16">
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
    { label: "Input",           done: !!speech.audio_url || !!transcript },
    { label: "Arguments",       done: !!argMap                           },
    { label: "Coaching Report", done: !!feedback                         },
    { label: "Practice",        done: drills.length > 0                  },
  ];

  const isComplete = speech.status === "done";

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
          className="mx-auto flex max-w-5xl flex-col gap-5 px-4 py-7 sm:px-6 sm:py-9"
          variants={staggerParent(0.08, 0.05)}
          initial="hidden"
          animate="show"
        >
          {/* Header — metadata strip */}
          <motion.div variants={staggerChild} className="flex flex-col gap-3">
            <div className="flex items-start justify-between gap-3">
              <h1 className="text-title text-ink">{speech.title}</h1>
              <StatusBadge status={speech.status} />
            </div>
            {/* Metadata chips */}
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full border border-hairline bg-surface-2 px-2.5 py-1 text-xs font-medium text-ink-subtle">
                {TYPE_LABEL[speech.speech_type] ?? speech.speech_type}
              </span>
              {speech.side && (
                <span className="rounded-full border border-hairline bg-surface-2 px-2.5 py-1 text-xs font-medium capitalize text-ink-subtle">
                  {speech.side}
                </span>
              )}
              {speech.judge_type && (
                <span className="rounded-full border border-hairline bg-surface-2 px-2.5 py-1 text-xs font-medium capitalize text-ink-subtle">
                  {speech.judge_type} judge
                </span>
              )}
              {speech.duration_seconds && speech.duration_seconds > 0 && (
                <span className="rounded-full border border-hairline bg-surface-2 px-2.5 py-1 text-xs font-medium text-ink-faint">
                  {Math.floor(speech.duration_seconds / 60)}:{String(speech.duration_seconds % 60).padStart(2, "0")}
                </span>
              )}
              <span className="text-xs text-ink-faint">{date}</span>
            </div>
            {speech.topic && (
              <p className="text-xs leading-relaxed text-ink-faint">
                <span className="font-medium text-ink-subtle">Resolution:</span> {speech.topic}
              </p>
            )}
          </motion.div>

          {/* Improvement comparison — shown when this is a re-recorded speech */}
          {comparison?.has_parent && (
            <motion.div variants={staggerChild}>
              <ImprovementComparisonCard comparison={comparison} />
            </motion.div>
          )}

          {/* Stepper — only show for incomplete sessions */}
          {!isComplete && (
            <motion.div variants={staggerChild}>
              <WorkflowStepper steps={steps} />
            </motion.div>
          )}

          {/* Verdict Panel — replaces stepper + "What to do next" for complete sessions */}
          {isComplete && feedback && (
            <motion.div variants={staggerChild}>
              <ReportVerdictPanel
                speech={speech}
                feedback={feedback}
                drills={drills}
                judgeViewMode={judgeViewMode}
                onJudgeModeChange={setJudgeViewMode}
                onStartNewAttempt={startNewAttempt}
                overallScore={getVerifiedOverallScore(feedback)}
              />
            </motion.div>
          )}

          {/* Workspace cards — order changes based on completion status */}
          <AnimatePresence mode="popLayout">

            {/* ── Audio Input (Only for Incomplete Sessions) ────────────── */}
            {!isComplete && (
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
                      {(["record", "upload", "paste"] as const).map((m) => (
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
                          {m === "record" ? <><Mic size={12} /> Record</> : m === "upload" ? <><Upload size={12} /> Upload</> : <><FileText size={12} /> Paste</>}
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
                      ) : mode === "upload" ? (
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
                      ) : (
                        <motion.div key="paste"
                          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                          transition={T.fast}
                          className="flex flex-col gap-3"
                        >
                          <div className="flex flex-col gap-2">
                            <label className="text-xs font-medium text-ink-subtle">Paste your speech text</label>
                            <textarea
                              value={pastedText}
                              onChange={(e) => setPastedText(e.target.value)}
                              placeholder="Paste or type your speech here... (minimum 30 seconds / ~75 words)"
                              className="h-48 w-full rounded-md border border-hairline bg-surface-2 px-3 py-2 text-sm text-ink outline-none transition-colors focus-visible:border-lav/50 focus-visible:ring-2 focus-visible:ring-lav/20 resize-none"
                            />
                            {pastedText.trim() && (
                              <p className="text-xs text-ink-faint">
                                {pastedText.trim().split(/\s+/).length} words
                              </p>
                            )}
                          </div>
                          {pasteErr && <InlineAlert variant="danger">{pasteErr}</InlineAlert>}
                          <Button
                            onClick={submitPastedText}
                            disabled={!pastedText.trim() || submittingText}
                            size="sm"
                            className="w-full"
                          >
                            {submittingText ? "Saving..." : "Save Text & Continue"}
                          </Button>
                          <p className="text-xs text-ink-faint leading-relaxed">
                            Paste a speech you've already prepared. RoundLab will analyze the text and generate flow and feedback.
                          </p>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                )}
                </CardContent>
              </WorkspaceCard>
            )}

            {/* ── For Complete Sessions: Coaching Report → Practice → Arguments → Input ── */}
            {isComplete ? (
              <>
                {/* Feedback (Coaching Report) */}
                {feedback && (
                  <WorkspaceCard key="fb-done" glow>
                    <CardContent className="flex flex-col gap-5 px-5 py-5">
                      <StepHeader n={4} title="Coaching Report" done />

                      {/* Regenerate Banner - only show if report is stale */}
                      {isReportStale(feedback) && (
                        <div className="rounded-lg border border-lav/20 bg-lav/5 px-4 py-3 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                          <div className="flex flex-col gap-1">
                            <p className="text-sm font-medium text-lav">Update Available</p>
                            <p className="text-xs text-ink-muted leading-relaxed">
                              This report uses an older rubric. Regenerate to apply the latest recalibrated scoring.
                            </p>
                          </div>
                          <Button
                            size="sm"
                            variant="default"
                            onClick={generateFeedback}
                            disabled={genFb}
                            className="shrink-0"
                          >
                            {genFb ? "Regenerating..." : "Regenerate Report"}
                          </Button>
                        </div>
                      )}

                      {/* Coach annotation — below the top structured issue */}
                      <TopIssueCoachNote issues={feedback.raw_feedback?.structured_issues} />

                      {/* Priority Cards - Top 3 Issues */}
                      {feedback.raw_feedback?.top_3_priorities?.length ? (
                        <div className="flex flex-col gap-3">
                          <div className="section-stamp" style={{ color: "oklch(0.640 0.215 25 / 0.8)" }}>
                            <span className="h-1.5 w-1.5 rounded-full bg-danger flex-shrink-0" />
                            Round-Losing Issues
                          </div>
                          <div className="grid grid-cols-1 gap-2">
                            {feedback.raw_feedback.top_3_priorities.map((p, i) => (
                              <div key={i} className="flex items-start gap-3 rounded-xl border border-danger/25 bg-danger/6 px-4 py-3">
                                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-danger text-[10px] font-bold text-white mt-0.5">
                                  {i + 1}
                                </span>
                                <p className="text-sm leading-relaxed text-ink">{p}</p>
                              </div>
                            ))}
                          </div>
                        </div>
                      ) : null}

                      {/* Strengths & Weaknesses as Cards */}
                      {(feedback.strengths.length > 0 || feedback.weaknesses.length > 0) && (
                        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                          {feedback.strengths.length > 0 && (
                            <div className="flex flex-col gap-2 rounded-xl border border-ok/20 bg-ok/5 p-4">
                              <p className="text-sm font-semibold text-ok">✓ What Landed</p>
                              <ul className="flex flex-col gap-1.5">
                                {feedback.strengths.map((s, i) => (
                                  <li key={i} className="flex items-start gap-2 text-sm leading-relaxed text-ink-muted">
                                    <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-ok" />
                                    {s}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                          {feedback.weaknesses.length > 0 && (
                            <div className="flex flex-col gap-2 rounded-xl border border-warn/25 bg-warn/5 p-4">
                              <p className="text-sm font-semibold text-warn">⚠ Fix Before Next Round</p>
                              <ul className="flex flex-col gap-1.5">
                                {feedback.weaknesses.map((w, i) => (
                                  <li key={i} className="flex items-start gap-2 text-sm leading-relaxed text-ink-muted">
                                    <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-warn" />
                                    {w}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                      )}

                      {/* Judge Ballot */}
                      <div className="flex flex-col gap-3">
                        <div className="section-stamp" style={{ color: "oklch(0.510 0.156 278 / 0.8)" }}>
                          <span className="h-1.5 w-1.5 rounded-full bg-lav flex-shrink-0" />
                          Judge Ballot
                        </div>
                        <div className="rounded-xl border border-hairline bg-surface-2 p-4">
                          <ScoreBreakdown
                            scores={feedback.scores}
                            speechType={speech?.speech_type}
                            scoreExplanations={feedback.raw_feedback?.score_explanations}
                          />
                        </div>
                      </div>

                      {/* Coach Diagnosis Cards */}
                      {(feedback.raw_feedback?.dropped_or_undercovered_arguments?.length ||
                        feedback.raw_feedback?.warranting_diagnostics?.length ||
                        feedback.raw_feedback?.weighing_diagnostics?.length ||
                        feedback.raw_feedback?.evidence_diagnostics?.length) ? (
                        <div className="flex flex-col gap-3">
                          <div className="section-stamp">
                            <span className="h-1.5 w-1.5 rounded-full bg-ink-subtle flex-shrink-0" />
                            Coach Diagnosis
                          </div>

                          {/* Dropped arguments */}
                          {feedback.raw_feedback?.dropped_or_undercovered_arguments && feedback.raw_feedback.dropped_or_undercovered_arguments.length > 0 && (
                            <div className="flex flex-col gap-2 rounded-xl border border-danger/20 bg-danger/5 px-4 py-3">
                              <p className="text-sm font-semibold text-danger">Drops / Undercovered</p>
                              <ul className="flex flex-col gap-1.5">
                                {feedback.raw_feedback.dropped_or_undercovered_arguments.map((item, i) => (
                                  <li key={i} className="flex items-start gap-2 text-sm leading-relaxed text-ink-muted">
                                    <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-danger/60" />
                                    {item}
                                  </li>
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
                      ) : null}

                      {/* Decision Logic (RFD) */}
                      {feedback.raw_feedback?.decision_logic && (
                        <div className="flex flex-col gap-2 rounded-xl border border-lav/20 bg-lav/5 px-4 py-3">
                          <div className="section-stamp" style={{ color: "oklch(0.660 0.130 278)" }}>
                            <span className="h-1.5 w-1.5 rounded-full bg-lav flex-shrink-0" />
                            Reason For Decision (RFD)
                          </div>
                          <p className="text-sm leading-relaxed text-ink-muted">
                            {feedback.raw_feedback.decision_logic}
                          </p>
                        </div>
                      )}

                      {/* Judge Adaptation Notes */}
                      {feedback.raw_feedback?.judge_adaptation_notes && (
                        <div className="flex flex-col gap-2 rounded-xl border border-hairline bg-surface-2 px-4 py-3">
                          <p className="text-sm font-semibold text-ink">Judge Adaptation</p>
                          <p className="text-sm leading-relaxed text-ink-muted">
                            {feedback.raw_feedback.judge_adaptation_notes}
                          </p>
                        </div>
                      )}

                      {/* Action Checklist */}
                      {feedback.raw_feedback?.recommendations?.length ? (
                        <div className="flex flex-col gap-3 rounded-xl border border-lav/20 bg-lav/5 p-4">
                          <p className="text-sm font-semibold text-lav">Before You Re-Record</p>
                          <ul className="flex flex-col gap-2">
                            {feedback.raw_feedback.recommendations.map((r, i) => (
                              <li key={i} className="flex items-start gap-2 text-sm leading-relaxed text-ink">
                                <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded border border-lav/30 bg-surface-1 text-[8px] font-bold text-lav/50">
                                  {i + 1}
                                </span>
                                {r}
                              </li>
                            ))}
                          </ul>
                        </div>
                      ) : null}

                      {/* Feedback Rating + Confusion Report */}
                      {userId && (
                        <div className="flex flex-col gap-3 rounded-xl border border-hairline bg-surface-2 px-4 py-3">
                          <FeedbackRating
                            speechId={speechId}
                            userId={userId}
                            initialRating={(feedback.helpful_rating as "helpful" | "somewhat" | "not_helpful" | null) ?? null}
                            onRated={() => setFeedbackRated(true)}
                          />
                          <ConfusionReport
                            targetType="speech_report"
                            targetId={feedback.id}
                            userId={userId}
                          />
                        </div>
                      )}
                    </CardContent>
                  </WorkspaceCard>
                )}

                {/* Recommended Practice / Drills */}
                {drills.length > 0 ? (
                  <WorkspaceCard key="drills-done">
                    {/* id="drills" is the anchor target for ReportVerdictPanel and PracticeLoopCTA #drills hrefs */}
                    <CardContent id="drills" className="flex flex-col gap-4 px-5 py-5 scroll-mt-20">
                      <StepHeader
                        n={5}
                        title="Recommended Practice"
                        done
                        aside={
                          <Badge variant="indigo">
                            {drills.filter((d) => d.status !== "assigned").length}/{drills.length} attempted
                          </Badge>
                        }
                      />
                      <div className="flex items-start gap-3 rounded-lg border border-lav/20 bg-lav/5 px-4 py-3">
                        <div className="flex-1">
                          <p className="text-sm font-semibold text-ink">Complete drills to turn feedback into improvement</p>
                          <p className="text-xs text-ink-subtle">
                            Each drill targets a specific weakness from your feedback. Practice the exercise, then re-record your speech to track progress.
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
                ) : feedback && (
                  <WorkspaceCard key="drills-empty">
                    <CardContent className="flex flex-col gap-4 px-5 py-5">
                      <StepHeader n={5} title="Recommended Practice" done={false} />
                      <EmptyStateCard
                        icon={Target}
                        title="No practice drills yet"
                        description="Generate personalized drills based on your feedback to target your weaknesses and improve faster."
                        actionLabel="Generate Practice Drills"
                        onAction={generateDrills}
                      />
                      {genDrills && <p className="text-xs text-center text-ink-faint">Generating drills...</p>}
                      {drillErr && <InlineAlert variant="danger">{drillErr}</InlineAlert>}
                    </CardContent>
                  </WorkspaceCard>
                )}

                {/* Flow */}
                {argMap && (
                  <WorkspaceCard key="flow-done">
                    <CardContent className="flex flex-col gap-4 px-5 py-5">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <StepHeader n={3} title="Flow" done aside={
                          <Badge variant="indigo">
                            {argMap.arguments.length} arg{argMap.arguments.length !== 1 ? "s" : ""}
                          </Badge>
                        } />
                        <JudgeModeSelector value={judgeViewMode} onChange={setJudgeViewMode} />
                      </div>

                      {/* Flow Summary */}
                      <FlowSummary argMap={argMap} />

                      {/* Lens note */}
                      <FlowLensNote judgeMode={judgeViewMode} />

                      {argMap.arguments.length === 0 ? (
                        <p className="text-sm text-ink-faint">No arguments extracted.</p>
                      ) : showTableView ? (
                        <FlowTable args={argMap.arguments} judgeMode={judgeViewMode} />
                      ) : (
                        <FlowBoard args={argMap.arguments} judgeMode={judgeViewMode} />
                      )}

                      {/* View toggle — demoted, secondary */}
                      <button
                        type="button"
                        onClick={() => setShowTableView((v) => !v)}
                        className="self-start text-[10px] text-ink-faint underline-offset-2 hover:text-ink-subtle hover:underline"
                      >
                        {showTableView ? "Switch to flow board" : "Switch to table view"}
                      </button>
                    </CardContent>
                  </WorkspaceCard>
                )}

                {/* View Speech Text - Collapsed (completed session)
                    TODO: Future feature - Annotated Speech Text
                    - Highlight claims, warrants, evidence, impacts inline
                    - Underline weak warrants
                    - Flag unsupported evidence
                    - Show strong/weak segments with color coding
                    - Useful for students who want to see exactly where their speech succeeded/failed
                */}
                {transcript && (
                  <WorkspaceCard key="input-details">
                    <CardContent className="flex flex-col gap-3 px-5 py-5">
                      <div className="flex items-center gap-3">
                        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-surface-2">
                          <FileText size={14} className="text-ink-subtle" />
                        </div>
                        <div className="flex-1">
                          <p className="text-sm font-semibold text-ink">View Speech Text</p>
                          <p className="text-xs text-ink-faint">{transcript.word_count} words</p>
                        </div>
                      </div>
                      <Collapsible label="Show full transcript">
                        <div className="rounded-lg border border-hairline bg-surface-2 p-4">
                          <p className="text-sm leading-relaxed text-ink whitespace-pre-wrap">{transcript.text}</p>
                        </div>
                      </Collapsible>
                    </CardContent>
                  </WorkspaceCard>
                )}
              </>
            ) : (
              <>
                {/* ── For Incomplete Sessions: Input → Analysis → Coaching → Practice ── */}

                {/* Input Status - Compact */}
                {speech.audio_url && transcript && !analyzingUnified && (
                  <WorkspaceCard key="input-ready">
                    <CardContent className="flex flex-col gap-3 px-5 py-5">
                      <div className="flex items-center gap-3">
                        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-ok/10">
                          <Check size={14} className="text-ok" />
                        </div>
                        <div className="flex-1">
                          <p className="text-sm font-semibold text-ink">Speech input ready</p>
                          <p className="text-xs text-ink-faint">{transcript.word_count} words • {speech.speech_type.replace('_', ' ')}</p>
                        </div>
                      </div>
                      {/* Optional: View speech text - Future TODO: annotated speech text can highlight claims, warrants, evidence, impacts, weak links, and strong moments. */}
                      <TranscriptPanel transcript={transcript} onReRecord={resetAudio} />
                    </CardContent>
                  </WorkspaceCard>
                )}

                {/* Unified Analysis Workflow */}
                {transcript && !feedback && !analyzingUnified && (
                  <WorkspaceCard key="unified-analysis">
                    <CardContent className="flex flex-col gap-4 px-5 py-5">
                      <StepHeader n={3} title="Analysis" done={false} />
                      {!canAnalyze ? (
                        <InlineAlert variant="danger">Speech text too short. Need at least 75 words for meaningful analysis.</InlineAlert>
                      ) : (
                        <div className="flex items-start gap-3 rounded-lg border border-lav/20 bg-lav/5 px-4 py-3">
                          <div className="flex-1">
                            <p className="text-sm font-semibold text-ink">Get your coaching report</p>
                            <p className="text-xs text-ink-subtle">
                              RoundLab will build your flow, analyze your arguments, and generate judge-style feedback with personalized drills.
                            </p>
                          </div>
                        </div>
                      )}
                      {unifiedAnalysisErr && <InlineAlert variant="danger">{unifiedAnalysisErr}</InlineAlert>}
                      <Button disabled={!canAnalyze || analyzingUnified} onClick={() => analyzeMySpeech()} size="sm" className="w-full">
                        {analyzingUnified ? "Analyzing..." : "Analyze My Speech"}
                      </Button>
                    </CardContent>
                  </WorkspaceCard>
                )}

                {/* Unified Analysis Loading */}
                {analyzingUnified && (
                  <motion.div key="unified-loading" {...fadeUp(0)}>
                    <LoadingCard
                      title={analysisStage ? STAGE_MESSAGES[analysisStage].title : "Analyzing your speech"}
                      subtitle="This can take 30–90 seconds"
                      messages={analysisStage ? STAGE_MESSAGES[analysisStage].messages : MSG_UNIFIED_ANALYSIS}
                    />
                  </motion.div>
                )}

                {/* Step 3: Flow */}
                {argMap && !analyzingUnified && (
                  genFlow ? (
                    <motion.div key="flow-loading" {...fadeUp(0)}>
                      <LoadingCard title="Building your flow" messages={MSG_FLOW} />
                    </motion.div>
                  ) : (
                    <WorkspaceCard key="flow-done">
                      <CardContent className="flex flex-col gap-4 px-5 py-5">
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <StepHeader n={3} title="Flow" done aside={
                            <Badge variant="indigo">
                              {argMap.arguments.length} arg{argMap.arguments.length !== 1 ? "s" : ""}
                            </Badge>
                          } />
                          <JudgeModeSelector value={judgeViewMode} onChange={setJudgeViewMode} />
                        </div>

                        {/* Flow Summary */}
                        <FlowSummary argMap={argMap} />

                        {/* Lens note */}
                        <FlowLensNote judgeMode={judgeViewMode} />

                        {argMap.arguments.length === 0 ? (
                          <p className="py-4 text-center text-sm text-ink-faint">No arguments extracted.</p>
                        ) : showTableView ? (
                          <>
                            <FlowCoachNote args={argMap.arguments} />
                            <FlowTable args={argMap.arguments} judgeMode={judgeViewMode} />
                          </>
                        ) : (
                          <FlowBoard args={argMap.arguments} judgeMode={judgeViewMode} />
                        )}

                        {/* View toggle — demoted, secondary */}
                        <button
                          type="button"
                          onClick={() => setShowTableView((v) => !v)}
                          className="self-start text-[10px] text-ink-faint underline-offset-2 hover:text-ink-subtle hover:underline"
                        >
                          {showTableView ? "Switch to flow board" : "Switch to table view"}
                        </button>

                        {/* Optional: View speech text */}
                        {transcript && (
                          <div className="flex flex-col gap-2">
                            <p className="text-xs text-ink-faint">Input details:</p>
                            <TranscriptPanel transcript={transcript} />
                          </div>
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
                  )
                )}

                {/* Step 4: Feedback */}
                {feedback && !analyzingUnified && (
                  genFb ? (
                    <motion.div key="fb-loading" {...fadeUp(0)}>
                      <LoadingCard title="Analyzing your speech" messages={MSG_FEEDBACK} />
                    </motion.div>
                  ) : (
                    <WorkspaceCard key="fb-done" glow>
                      <CardContent className="flex flex-col gap-5 px-5 py-5">
                        <StepHeader n={4} title="Coaching Report" done />

                        {/* Regenerate Banner - only show if report is stale */}
                        {isReportStale(feedback) && (
                          <div className="rounded-lg border border-lav/20 bg-lav/5 px-4 py-3 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                            <div className="flex flex-col gap-1">
                              <p className="text-sm font-medium text-lav">Update Available</p>
                              <p className="text-xs text-ink-muted leading-relaxed">
                                This report uses an older rubric. Regenerate to apply the latest recalibrated scoring.
                              </p>
                            </div>
                            <Button
                              size="sm"
                              variant="default"
                              onClick={generateFeedback}
                              disabled={genFb}
                              className="shrink-0"
                            >
                              {genFb ? "Regenerating..." : "Regenerate Report"}
                            </Button>
                          </div>
                        )}

                        {/* Priority Cards - Top 3 Issues */}
                        {feedback.raw_feedback?.top_3_priorities?.length ? (
                          <div className="flex flex-col gap-3">
                            <div className="section-stamp" style={{ color: "oklch(0.640 0.215 25 / 0.8)" }}>
                              <span className="h-1.5 w-1.5 rounded-full bg-danger flex-shrink-0" />
                              Round-Losing Issues
                            </div>
                            <div className="grid grid-cols-1 gap-2">
                              {feedback.raw_feedback.top_3_priorities.map((p, i) => (
                                <div key={i} className="flex items-start gap-3 rounded-xl border border-danger/25 bg-danger/6 px-4 py-3">
                                  <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-danger text-[10px] font-bold text-white mt-0.5">
                                    {i + 1}
                                  </span>
                                  <p className="text-sm leading-relaxed text-ink">{p}</p>
                                </div>
                              ))}
                            </div>
                          </div>
                        ) : null}

                        {/* Coach annotation — below the top structured issue */}
                        <TopIssueCoachNote issues={feedback.raw_feedback?.structured_issues} />

                        {/* Strengths & Weaknesses as Cards */}
                        {(feedback.strengths.length > 0 || feedback.weaknesses.length > 0) && (
                          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                            {feedback.strengths.length > 0 && (
                              <div className="flex flex-col gap-2 rounded-xl border border-ok/20 bg-ok/5 p-4">
                                <p className="text-sm font-semibold text-ok">✓ What Landed</p>
                                <ul className="flex flex-col gap-1.5">
                                  {feedback.strengths.map((s, i) => (
                                    <li key={i} className="flex items-start gap-2 text-sm leading-relaxed text-ink-muted">
                                      <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-ok" />
                                      {s}
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}
                            {feedback.weaknesses.length > 0 && (
                              <div className="flex flex-col gap-2 rounded-xl border border-warn/25 bg-warn/5 p-4">
                                <p className="text-sm font-semibold text-warn">⚠ Fix Before Next Round</p>
                                <ul className="flex flex-col gap-1.5">
                                  {feedback.weaknesses.map((w, i) => (
                                    <li key={i} className="flex items-start gap-2 text-sm leading-relaxed text-ink-muted">
                                      <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-warn" />
                                      {w}
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </div>
                        )}

                        {/* Judge Ballot */}
                        <div className="flex flex-col gap-3">
                          <div className="flex items-center gap-2">
                            <span className="h-1.5 w-1.5 rounded-full bg-lav" />
                            <p className="text-eyebrow text-ink-subtle">Judge Ballot</p>
                          </div>
                          <div className="rounded-xl border border-hairline bg-surface-2 p-4">
                            <ScoreBreakdown
                              scores={feedback.scores}
                              speechType={speech?.speech_type}
                              scoreExplanations={feedback.raw_feedback?.score_explanations}
                            />
                          </div>
                        </div>

                        {/* Coach Diagnosis Cards */}
                        {(feedback.raw_feedback?.dropped_or_undercovered_arguments?.length ||
                          feedback.raw_feedback?.warranting_diagnostics?.length ||
                          feedback.raw_feedback?.weighing_diagnostics?.length ||
                          feedback.raw_feedback?.evidence_diagnostics?.length) ? (
                          <div className="flex flex-col gap-3">
                            <div className="flex items-center gap-2">
                              <span className="h-1.5 w-1.5 rounded-full bg-ink-subtle" />
                              <p className="text-eyebrow text-ink-subtle">Coach Diagnosis</p>
                            </div>

                            {feedback.raw_feedback?.dropped_or_undercovered_arguments && feedback.raw_feedback.dropped_or_undercovered_arguments.length > 0 && (
                              <div className="flex flex-col gap-2 rounded-xl border border-danger/20 bg-danger/5 px-4 py-3">
                                <p className="text-sm font-semibold text-danger">Drops / Undercovered</p>
                                <ul className="flex flex-col gap-1.5">
                                  {feedback.raw_feedback.dropped_or_undercovered_arguments.map((item, i) => (
                                    <li key={i} className="flex items-start gap-2 text-sm leading-relaxed text-ink-muted">
                                      <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-danger/60" />
                                      {item}
                                    </li>
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
                        ) : null}

                        {/* Decision Logic (RFD) */}
                        {feedback.raw_feedback?.decision_logic && (
                          <div className="flex flex-col gap-2 rounded-xl border border-lav/20 bg-lav/5 px-4 py-3">
                            <div className="flex items-center justify-between gap-2">
                              <div className="flex items-center gap-2">
                                <span className="h-1.5 w-1.5 rounded-full bg-lav" />
                                <p className="text-eyebrow text-lav">Reason For Decision (RFD)</p>
                              </div>
                              <button
                                type="button"
                                onClick={() => copyRFD(feedback.raw_feedback?.decision_logic ?? "")}
                                className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-ink-faint transition-colors hover:bg-lav/10 hover:text-lav"
                                title="Copy RFD"
                              >
                                {rfdCopied ? <Check size={10} className="text-ok" /> : <Copy size={10} />}
                                {rfdCopied ? "Copied" : "Copy"}
                              </button>
                            </div>
                            <p className="text-sm leading-relaxed text-ink-muted">
                              {feedback.raw_feedback.decision_logic}
                            </p>
                          </div>
                        )}

                        {/* Judge Adaptation Notes */}
                        {feedback.raw_feedback?.judge_adaptation_notes && (
                          <div className="flex flex-col gap-2 rounded-xl border border-hairline bg-surface-2 px-4 py-3">
                            <p className="text-sm font-semibold text-ink">Judge Adaptation</p>
                            <p className="text-sm leading-relaxed text-ink-muted">
                              {feedback.raw_feedback.judge_adaptation_notes}
                            </p>
                          </div>
                        )}

                        {/* Action Checklist */}
                        {feedback.raw_feedback?.recommendations?.length ? (
                          <div className="flex flex-col gap-3 rounded-xl border border-lav/20 bg-lav/5 p-4">
                            <p className="text-sm font-semibold text-lav">Before You Re-Record</p>
                            <ul className="flex flex-col gap-2">
                              {feedback.raw_feedback.recommendations.map((r, i) => (
                                <li key={i} className="flex items-start gap-2 text-sm leading-relaxed text-ink">
                                  <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded border border-lav/30 bg-surface-1 text-[8px] font-bold text-lav/50">
                                    {i + 1}
                                  </span>
                                  {r}
                                </li>
                              ))}
                            </ul>
                          </div>
                        ) : null}

                        {/* Feedback Rating + Confusion Report */}
                        {userId && (
                          <div className="flex flex-col gap-3 rounded-xl border border-hairline bg-surface-2 px-4 py-3">
                            <FeedbackRating
                              speechId={speechId}
                              userId={userId}
                              initialRating={(feedback.helpful_rating as "helpful" | "somewhat" | "not_helpful" | null) ?? null}
                              onRated={() => setFeedbackRated(true)}
                            />
                            <ConfusionReport
                              targetType="speech_report"
                              targetId={feedback.id}
                              userId={userId}
                            />
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
                  )
                )}

                {/* Step 5: Drills */}
                {feedback && (
                  genDrills ? (
                    <motion.div key="drills-loading" {...fadeUp(0)}>
                      <LoadingCard title="Creating practice drills" messages={MSG_DRILLS} />
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
              </>
            )}

            {/* ── Evidence Support — shown after feedback exists and argMap is available ── */}
            {feedback && argMap && argMap.arguments.length > 0 && (
              <WorkspaceCard key="evidence-support">
                <CardContent className="flex flex-col gap-4 px-5 py-5">
                  {/* Section header */}
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2.5">
                      <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-hairline-strong text-xs font-bold text-ink-faint">
                        E
                      </span>
                      <p className="text-heading text-ink">Evidence Support</p>
                    </div>
                    {hasLibrary && !checkingEvidence && (
                      <Button
                        size="sm"
                        variant="secondary"
                        className="h-7 text-xs shrink-0"
                        onClick={runAllEvidenceChecks}
                        disabled={checkingEvidence}
                      >
                        {freshResults.length > 0 || savedChecks.length > 0
                          ? "Re-check all"
                          : "Check all claims"}
                      </Button>
                    )}
                  </div>

                  {/* Purpose copy */}
                  <p className="text-xs text-ink-subtle leading-relaxed">
                    Check whether your uploaded case files support the claims and evidence used in this speech.
                    Results are based only on your library — not outside knowledge.
                  </p>

                  {/* State A: no library */}
                  {hasLibrary === false && (
                    <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-hairline p-6 text-center">
                      <p className="text-sm font-medium text-ink">Upload a case file to verify evidence</p>
                      <p className="text-xs text-ink-subtle leading-relaxed max-w-sm">
                        Go to your Evidence Library and upload a case file.
                        RoundLab will check whether your speech claims are supported by your own uploaded evidence.
                      </p>
                      <a
                        href="/evidence"
                        className="mt-1 inline-flex items-center gap-1 text-xs text-lav underline-offset-2 hover:underline"
                      >
                        Open Evidence Library →
                      </a>
                    </div>
                  )}

                  {/* State B: has library, no checks yet */}
                  {hasLibrary === true && !checkingEvidence && freshResults.length === 0 && savedChecks.length === 0 && (
                    <div className="flex flex-col gap-3 rounded-xl border border-lav/20 bg-lav/5 px-4 py-4">
                      <p className="text-sm font-semibold text-ink">
                        Check claims against your evidence library
                      </p>
                      <p className="text-xs text-ink-subtle leading-relaxed">
                        RoundLab will compare each argument in this speech to your uploaded case files
                        and tell you whether your cited evidence actually supports the claim you made.
                      </p>
                      <Button
                        size="sm"
                        onClick={runAllEvidenceChecks}
                        disabled={checkingEvidence}
                        className="w-full"
                      >
                        Check claims against my evidence library
                      </Button>
                    </div>
                  )}

                  {/* State C: checking */}
                  {checkingEvidence && (
                    <div className="flex flex-col gap-2 rounded-xl border border-hairline bg-surface-2 px-4 py-4">
                      <div className="flex items-center gap-2 text-xs text-ink-subtle">
                        <span className="h-1.5 w-1.5 rounded-full bg-lav analysis-step-active" />
                        {checkingIndex >= 0 && checkingIndex < argMap.arguments.length
                          ? `Checking argument ${checkingIndex + 1} of ${argMap.arguments.length}: ${argMap.arguments[checkingIndex].label}`
                          : "Matching claims to uploaded cards…"}
                      </div>
                      <div className="h-1 w-full overflow-hidden rounded-full bg-surface-1">
                        <div
                          className="h-full rounded-full bg-lav transition-all duration-500"
                          style={{
                            width: checkingIndex >= 0
                              ? `${Math.round((checkingIndex / argMap.arguments.length) * 100)}%`
                              : "0%",
                          }}
                        />
                      </div>
                    </div>
                  )}

                  {evidenceCheckErr && (
                    <p className="text-xs text-danger">{evidenceCheckErr}</p>
                  )}

                  {/* State D/E: results (fresh or saved) */}
                  {(freshResults.length > 0 || savedChecks.length > 0) && !checkingEvidence && (
                    <>
                      {/* Coach margin note based on overall results */}
                      {freshResults.length > 0 && (() => {
                        const hasProblems = freshResults.some(
                          (r) => r.support_level === "unsupported" || r.support_level === "unverifiable",
                        );
                        const allGood = freshResults.every((r) => r.support_level === "supported");
                        if (allGood) {
                          return (
                            <CoachMarginNote
                              type="strong"
                              label="Evidence check"
                              note="Your uploaded evidence supports the main claims checked in this report."
                            />
                          );
                        }
                        if (hasProblems) {
                          return (
                            <CoachMarginNote
                              type="warn"
                              label="Evidence check"
                              note="Evidence check found claims that may need clearer citation or stronger card support."
                            />
                          );
                        }
                        return null;
                      })()}

                      {/* Evidence Risk Summary + drill CTA */}
                      {(() => {
                        const checksForSummary = freshResults.length > 0
                          ? freshResults.map((r) => ({
                              id: "",
                              speech_id: speechId,
                              user_id: userId ?? "",
                              argument_label: r.argument_label,
                              claim_text: r.claim_text,
                              evidence_text_from_speech: r.evidence_text_from_speech,
                              matched_card_id: r.matched_card?.id ?? null,
                              support_level: r.support_level,
                              explanation: r.explanation,
                              created_at: new Date().toISOString(),
                            }))
                          : savedChecks;
                        if (checksForSummary.length === 0) return null;
                        const risk = deriveEvidenceRiskSummary(checksForSummary);
                        const hasProblems = risk.unsupported_count + risk.partial_count + risk.unverifiable_count > 0;
                        if (!hasProblems) return null;
                        return (
                          <div className="rounded-xl border border-warn/20 bg-warn/5 px-4 py-4 flex flex-col gap-3">
                            <div className="flex items-start gap-2.5">
                              <ShieldAlert size={14} className="mt-0.5 shrink-0 text-warn" />
                              <div className="flex flex-col gap-1 min-w-0">
                                <p className="text-sm font-semibold text-ink">Evidence Risk Summary</p>
                                <p className="text-xs text-ink-subtle leading-relaxed">{risk.summary}</p>
                                <p className="text-xs text-ink-muted leading-relaxed">{risk.recommended_action}</p>
                              </div>
                            </div>
                            {evidenceDrillErr && (
                              <p className="text-xs text-danger">{evidenceDrillErr}</p>
                            )}
                            {evidenceDrillsDone ? (
                              <p className="text-xs text-ok flex items-center gap-1.5">
                                <Check size={11} />
                                Evidence drills added to your drill queue below.
                              </p>
                            ) : (
                              <Button
                                size="sm"
                                variant="secondary"
                                className="self-start h-7 text-xs gap-1.5"
                                onClick={generateEvidenceDrills}
                                disabled={genEvidenceDrills}
                              >
                                {genEvidenceDrills ? (
                                  <><RefreshCw size={11} className="animate-spin" />Generating…</>
                                ) : (
                                  <><Sparkles size={11} />Generate evidence drill</>
                                )}
                              </Button>
                            )}
                          </div>
                        );
                      })()}

                      <EvidenceSupportPanel
                        speechId={speechId}
                        userId={userId ?? ""}
                        arguments={argMap.arguments}
                        hasLibrary={hasLibrary ?? true}
                        savedChecks={savedChecks}
                        freshResults={freshResults}
                      />
                    </>
                  )}
                </CardContent>
              </WorkspaceCard>
            )}

          </AnimatePresence>

          {/* Practice Loop CTA — always visible after report is complete */}
          <PracticeLoopCTA
            drills={drills}
            speechId={speechId}
            isComplete={isComplete}
            hasFeedback={!!feedback}
            onGenerateDrills={generateDrills}
            generatingDrills={genDrills}
            onStartNewAttempt={startNewAttempt}
          />

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
