"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { motion, AnimatePresence } from "motion/react";
import {
  Check, FileText,
  Mic, Pencil, RefreshCw, Trash2, Upload, ThumbsUp, ThumbsDown, Target, Copy,
  ShieldAlert, Sparkles, Share2, Printer, ArrowRight, Swords,
} from "lucide-react";
import { useCopy } from "@/lib/useCopy";
import { deriveAnalysisRecoveryState, isJobActive } from "@/lib/jobHelpers";
import AppShell from "@/components/shell/AppShell";
import SpeechReportNav from "@/components/speech/SpeechReportNav";
import {
  StepHeader, Collapsible, InlineAlert, StatusBadge, CoachDiagnosis, WorkspaceCard,
  FlowSummary, TopIssueCoachNote, FlowCoachNote, FlowLensNote, ContextualHelp,
  getVerifiedOverallScore, isReportStale,
} from "@/components/speech/reportPrimitives";
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
import { fadeUp, staggerParent, staggerChild, T } from "@/lib/motion";
import DrillCard from "@/components/DrillCard";
import FlowTable from "@/components/FlowTable";
import PracticeLoopCTA from "@/components/PracticeLoopCTA";
import ImprovementComparisonCard from "@/components/ImprovementComparisonCard";
import CoachMarginNote from "@/components/CoachMarginNote";
import EvidenceSupportPanel from "@/components/EvidenceSupportPanel";
import FeedbackRating from "@/components/FeedbackRating";
import { AnalysisProgressCard } from "@/components/AnalysisProgressCard";
import FlowEditPanel from "@/components/FlowEditPanel";
import ConfusionReport from "@/components/ConfusionReport";
import DeliveryCoachPanel, { DeliveryCoachPanelEmpty } from "@/components/DeliveryCoachPanel";
import ShareReportModal from "@/components/ShareReportModal";
import TournamentWorkoutPanel from "@/components/TournamentWorkoutPanel";
import BlockCoveragePanel from "@/components/BlockCoveragePanel";
import { logEvent } from "@/lib/analytics";
import { deriveNextBestAction } from "@/lib/blockfileHelpers";
import { formatPracticePlan, copyToClipboard } from "@/lib/reportHelpers";
import { deriveEvidenceRiskSummary } from "@/lib/debateHelpers";
import { initEditArgs, isFlowCorrectedAndNeedsRegen } from "@/lib/flowEditHelpers";
import type { AnalysisJob, AnalyzeResponse, ArgumentItem, ArgumentMap, DeliveryMetrics, Drill, DrillStatus, FeedbackReport, Speech, Transcript, Workout, BlockCoverageResponse } from "@/types";
import type { ClaimEvidenceCheck, EvidenceCheckResult, EvidenceDocument } from "@/types";
import type { RecordState } from "@/components/RecordingStudio";
import { useRecorder } from "@/hooks/useRecorder";
import { useSpeechUpload } from "@/hooks/useSpeechUpload";

// ── Constants ──────────────────────────────────────────────────────────────────

const TYPE_LABEL: Record<string, string> = {
  constructive: "Constructive", rebuttal: "Rebuttal",
  summary: "Summary", final_focus: "Final Focus", crossfire: "Crossfire",
};

const MSG_TRANSCRIBE = ["Preparing your speech", "Reading your audio", "Processing speech content", "Almost ready"];
const MSG_FLOW       = ["Finding claims and warrants", "Mapping evidence and impacts", "Building your flow", "Analyzing argument structure"];
const MSG_FEEDBACK   = ["Reading your speech", "Mapping arguments", "Evaluating the case", "Building your coaching report"];
const MSG_DRILLS     = ["Reviewing your feedback", "Identifying skill gaps", "Creating practice drills"];
const MSG_UNIFIED_ANALYSIS = ["Reading your speech", "Mapping arguments", "Building your flow", "Evaluating the case", "Creating your coaching report"];

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



// ── Main ───────────────────────────────────────────────────────────────────────

export default function SpeechPage() {
  const { id: speechId } = useParams<{ id: string }>();
  const router = useRouter();

  const [userId,     setUserId]     = useState<string | null>(null);
  const [speech,     setSpeech]     = useState<Speech | null>(null);
  const [pageLoad,   setPageLoad]   = useState(true);
  const [pageErr,    setPageErr]    = useState("");

  const [mode,       setMode]       = useState<"record" | "upload" | "paste">("record");
  const rec = useRecorder();
  const upload = useSpeechUpload({ speechId, userId });
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

  // Job-based analysis state
  const [activeJob, setActiveJob] = useState<AnalysisJob | null>(null);
  const [retryingJob, setRetryingJob] = useState(false);

  // Flow edit state
  const [flowEditMode, setFlowEditMode] = useState(false);
  const [editingArgs, setEditingArgs] = useState<ArgumentItem[]>([]);
  const [savingCorrection, setSavingCorrection] = useState(false);
  const [correctionErr, setCorrectionErr] = useState("");
  const [regenerating, setRegenerating] = useState(false);
  const [regenErr, setRegenErr] = useState("");

  // Delivery metrics
  const [deliveryMetrics, setDeliveryMetrics] = useState<DeliveryMetrics | null>(null);
  const [deliveryLoaded, setDeliveryLoaded] = useState(false);

  // Share report modal + practice plan
  const [showShareModal, setShowShareModal] = useState(false);
  const [practicePlanCopied, setPracticePlanCopied] = useState(false);

  // Tournament prep workout (null = not generated yet, undefined = loading)
  const [workout, setWorkout] = useState<Workout | null | undefined>(undefined);

  // Block coverage (null = not run yet, undefined = loading)
  const [blockCoverage, setBlockCoverage] = useState<BlockCoverageResponse | null | undefined>(undefined);
  const [hasBlockEntries, setHasBlockEntries] = useState(false);

  const autoAnalysisStartedRef = useRef(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => () => {
    if (pollRef.current) clearInterval(pollRef.current);
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

        // Delivery metrics — best-effort, non-blocking
        apiFetch<DeliveryMetrics>(`/speeches/${speechId}/delivery-metrics?user_id=${uid}`)
          .then((dm) => { setDeliveryMetrics(dm); setDeliveryLoaded(true); })
          .catch(() => { setDeliveryLoaded(true); });

        // Workout — best-effort, non-blocking; null = not generated yet
        apiFetch<Workout>(`/speeches/${speechId}/workout?user_id=${uid}`)
          .then((w) => setWorkout(w))
          .catch(() => setWorkout(null));

        // Block coverage — best-effort; null = not run yet
        apiFetch<BlockCoverageResponse>(`/speeches/${speechId}/block-coverage?user_id=${uid}`)
          .then((c) => setBlockCoverage(c))
          .catch(() => setBlockCoverage(null));

        // Block entries — just need to know if any exist for this user
        apiFetch<Array<unknown>>(`/block-entries?user_id=${uid}`)
          .then((entries) => setHasBlockEntries(entries.length > 0))
          .catch(() => {});

        // Recovery: check for in-progress or recently-failed analysis jobs
        apiFetch<AnalysisJob[]>(`/speeches/${speechId}/jobs?user_id=${uid}`)
          .then((jobs) => {
            const state = deriveAnalysisRecoveryState(jobs, s.status);
            if (state.type === "in_progress") {
              setActiveJob(state.job);
              startPollWithUid(state.job.id, uid);
            } else if (state.type === "failed") {
              setActiveJob(state.job);
            }
          })
          .catch(() => {});
      })
      .catch(() => setPageErr("Could not load your data. Please refresh and try again."))
      .finally(() => setPageLoad(false));
  }, [speechId, router]);

  // ── Recording ──────────────────────────────────────────────────────────────

  /** Map the useRecorder status onto the presentational RecordingStudio states. */
  function recordStudioState(): RecordState {
    switch (rec.state.status) {
      case "idle": return "idle";
      case "requesting-permission":
      case "ready": return "requesting";
      case "recording":
      case "stopping": return "recording";
      case "recorded":
      case "playing": return "recorded";
      case "uploading":
      case "uploaded": return "uploading";
      case "error": return "error";
      default: return "idle";
    }
  }

  async function handleStartRec() {
    if (rec.state.status === "idle" || rec.state.status === "error") {
      await rec.requestPermission();
    }
    rec.start();
  }

  function handleDiscardRec() {
    if (rec.state.blob && !window.confirm("Discard this recording? You haven't saved it yet.")) return;
    rec.reset();
  }

  async function saveRec() {
    if (!rec.state.blob || !userId) return;
    const t = rec.state.blob.type;
    const ext = t.includes("mp4") ? "mp4" : t.includes("ogg") ? "ogg" : "webm";
    const durationSeconds = Math.round(rec.state.durationMs / 1000);
    let upd: Speech | null = null;
    const ok = await rec.upload(async (blob) => {
      // Shared persistence path with the file-upload flow.
      upd = await upload.persistAudio(blob, ext, durationSeconds > 0 ? durationSeconds : null);
      setSpeech(upd);
    });
    if (ok && upd) {
      rec.reset();
      // Auto-start analysis after recording upload completes (fresh upd avoids stale state)
      await maybeStartAutoAnalysis(upd);
    }
  }

  // ── File upload ────────────────────────────────────────────────────────────

  function onFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0] ?? null;
    upload.selectFile(f);
    if (!f) return;
    // Reset the input so re-selecting the same file still fires change.
    e.target.value = "";
  }

  async function uploadFile() {
    const upd = await upload.uploadSelectedFile();
    if (upd) {
      setSpeech(upd);
      // Auto-start analysis after file upload completes (fresh upd avoids stale state)
      await maybeStartAutoAnalysis(upd);
    }
  }

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
      rec.reset();
      autoAnalysisStartedRef.current = false; // Reset auto-analysis flag for new upload
    } catch {}
    finally { setResetting(false); }
  }

  // ── Job-based analysis ─────────────────────────────────────────────────────

  function startPollWithUid(jobId: string, uid: string) {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const job = await apiFetch<AnalysisJob>(`/jobs/${jobId}?user_id=${uid}`);
        setActiveJob(job);
        if (!isJobActive(job.status)) {
          clearInterval(pollRef.current!);
          pollRef.current = null;
          if (job.status === "succeeded") {
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
            const updatedSpeech = await apiFetch<Speech>(`/speeches/${speechId}?user_id=${uid}`).catch(() => null);
            if (updatedSpeech) setSpeech(updatedSpeech);
            setActiveJob(null);
          }
        }
      } catch {}
    }, 2000);
  }

  async function startJobAnalysis() {
    if (!userId) return;
    setUnifiedAnalysisErr("");
    try {
      const resp = await apiFetch<AnalyzeResponse>(
        `/speeches/${speechId}/analyze?user_id=${userId}`,
        { method: "POST" },
      );
      const job = await apiFetch<AnalysisJob>(`/jobs/${resp.job_id}?user_id=${userId}`);
      setActiveJob(job);
      if (isJobActive(job.status)) startPollWithUid(job.id, userId);
    } catch (e: unknown) {
      setUnifiedAnalysisErr(e instanceof Error ? e.message : "Analysis failed. Please try again.");
    }
  }

  async function retryAnalysis() {
    if (!activeJob || !userId) return;
    setRetryingJob(true);
    setUnifiedAnalysisErr("");
    try {
      const job = await apiFetch<AnalysisJob>(
        `/jobs/${activeJob.id}/retry?user_id=${userId}`,
        { method: "POST" },
      );
      setActiveJob(job);
      if (isJobActive(job.status)) startPollWithUid(job.id, userId);
    } catch (e: unknown) {
      setUnifiedAnalysisErr(e instanceof Error ? e.message : "Retry failed. Please try again.");
    } finally {
      setRetryingJob(false);
    }
  }

  // ── Flow correction ────────────────────────────────────────────────────────

  async function saveFlowCorrection(args: ArgumentItem[], notes?: string) {
    if (!userId) return;
    setSavingCorrection(true);
    setCorrectionErr("");
    try {
      const updated = await apiFetch<ArgumentMap>(
        `/speeches/${speechId}/argument-map?user_id=${userId}`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ arguments: args, correction_notes: notes }),
        }
      );
      setArgMap(updated);
      setFlowEditMode(false);
    } catch (e: unknown) {
      setCorrectionErr(e instanceof Error ? e.message : "Could not save corrections.");
    } finally {
      setSavingCorrection(false);
    }
  }

  async function regenerateFromFlow() {
    if (!userId) return;
    setRegenerating(true);
    setRegenErr("");
    try {
      const result = await apiFetch<{ feedback: FeedbackReport; drills: Drill[] }>(
        `/speeches/${speechId}/regenerate-from-flow?user_id=${userId}`,
        { method: "POST" }
      );
      setFeedback(result.feedback);
      setDrills(result.drills);
    } catch (e: unknown) {
      setRegenErr(e instanceof Error ? e.message : "Regeneration failed. Please try again.");
    } finally {
      setRegenerating(false);
    }
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
    console.log("[AutoAnalyze] Starting job-based analysis, audio_url=" + uploadedSpeech.audio_url);

    // Start the job-based analysis pipeline
    await startJobAnalysis();
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
      <AppShell maxWidth="full" bare>
          <div className="mx-auto flex max-w-5xl flex-col gap-5 px-6 py-9">
            <Skeleton className="h-6 w-48 rounded-lg" />
            <Skeleton className="h-4 w-60 rounded-lg" />
            <Skeleton className="h-8 w-full rounded-full" />
            {[1, 2].map((i) => (
              <Card key={i}><CardContent className="py-8"><Skeleton className="h-20 w-full rounded-lg" /></CardContent></Card>
            ))}
          </div>
      </AppShell>
    );
  }

  if (pageErr || !speech) {
    return (
      <AppShell maxWidth="full" bare>
          <div className="mx-auto max-w-5xl px-6 py-16">
            <p className="text-sm text-danger">{pageErr || "Speech not found."}</p>
          </div>
      </AppShell>
    );
  }

  // ── Computed ───────────────────────────────────────────────────────────────

  const wc         = transcript?.word_count ?? null;
  const canAnalyze = wc !== null && wc >= 20;
  const recBusy    = rec.state.status === "requesting-permission" || rec.state.status === "recording" || rec.state.status === "stopping" || rec.state.status === "uploading";

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

  const reportActions = isComplete && feedback ? (
    <div className="flex items-center gap-1">
      <button
        type="button"
        onClick={() => {
          logEvent("share_report_modal_opened", userId, { speech_id: speechId });
          setShowShareModal(true);
        }}
        className="no-print flex items-center gap-1.5 rounded-md border border-hairline bg-surface px-2.5 py-1.5 text-xs font-medium text-ink-subtle transition-colors hover:bg-surface-2 hover:text-ink"
      >
        <Share2 size={12} />
        Share
      </button>
      <button
        type="button"
        onClick={() => {
          logEvent("report_print_clicked", userId, { speech_id: speechId });
          window.print();
        }}
        className="no-print flex items-center gap-1.5 rounded-md border border-hairline bg-surface px-2.5 py-1.5 text-xs font-medium text-ink-subtle transition-colors hover:bg-surface-2 hover:text-ink"
      >
        <Printer size={12} />
        Print
      </button>
      {deleteBtn}
    </div>
  ) : deleteBtn;

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <AppShell maxWidth="full" bare headerRight={reportActions}>
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
                            recordState={recordStudioState()} recordingSeconds={Math.round(rec.state.durationMs / 1000)}
                            recordObjectUrl={rec.state.url} recordError={rec.state.error ?? ""}
                            onStartRecording={handleStartRec} onStopRecording={rec.stop}
                            onSaveRecording={saveRec}  onDiscardRecording={handleDiscardRec}
                          />
                        </motion.div>
                      ) : mode === "upload" ? (
                        <motion.div key="upload"
                          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                          transition={T.fast}
                        >
                          <UploadDropzone
                            selectedFile={upload.selectedFile} fileError={upload.fileError}
                            uploadError={upload.uploadError}    uploading={upload.uploading}
                            onFileChange={onFileChange} onUpload={uploadFile} onClearFile={upload.clearFile}
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
                <SpeechReportNav
                  flags={{
                    hasFeedback: !!feedback,
                    hasFlow: !!argMap,
                    hasDrills: drills.length > 0,
                    hasTranscript: !!transcript,
                  }}
                />
                {/* Feedback (Coaching Report) */}
                {feedback && (
                  <WorkspaceCard key="fb-done" glow>
                    <CardContent id="overview" className="flex flex-col gap-5 px-5 py-5 scroll-mt-20">
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

                      {/* Contextual help — warranting */}
                      <ContextualHelp question="Why does warranting matter so much?">
                        A warrant is the logical mechanism that connects your claim to your evidence. Without it, a judge can simply say "so what?" and ignore your argument even if the evidence is strong. Flow judges in particular will drop unwarranted arguments — a claim needs a clear "because" before the evidence or it doesn&apos;t count.
                      </ContextualHelp>

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

                {/* ── Practice Hub — groups Delivery Coach, Workout, Block Coverage, Drills ── */}
                {feedback && !analyzingUnified && (
                  <div className="flex items-center gap-2 px-1 pt-1">
                    <Swords size={13} className="shrink-0 text-ink-faint" />
                    <p className="text-[10px] font-semibold uppercase tracking-widest text-ink-faint">
                      Practice Hub
                    </p>
                  </div>
                )}

                {/* Next best action */}
                {feedback && !analyzingUnified && userId && (
                  (() => {
                    const action = deriveNextBestAction({
                      workout: workout ?? null,
                      drillsIncomplete: drills.filter(d => d.status === "assigned").length,
                      hasEvidenceRisk:
                        freshResults.some(r => r.support_level === "unsupported") ||
                        savedChecks.some(c => c.support_level === "unsupported"),
                      hasMissingBlocks: (blockCoverage?.missing_count ?? 0) > 0,
                      hasBlockEntries,
                      hasFeedback: true,
                      speechStatus: speech?.status,
                      speechId,
                    });
                    return (
                      <WorkspaceCard key="next-best-action">
                        <CardContent className="px-5 py-3">
                          <div className="flex items-center justify-between gap-3">
                            <div className="flex flex-col gap-0.5">
                              <p className="text-[10px] font-semibold uppercase tracking-wide text-ink-faint">
                                Next best action
                              </p>
                              <p className="text-sm font-semibold text-ink">{action.label}</p>
                              <p className="text-xs text-ink-subtle">{action.description}</p>
                            </div>
                            {action.href && (
                              <a
                                href={action.href}
                                className="shrink-0 flex items-center gap-1 rounded-lg border border-hairline bg-surface-2 px-3 py-1.5 text-xs font-medium text-ink hover:bg-surface-3 transition-colors"
                              >
                                Go <ArrowRight size={11} />
                              </a>
                            )}
                          </div>
                        </CardContent>
                      </WorkspaceCard>
                    );
                  })()
                )}

                {/* Delivery Coach Panel — visible after coaching report is done */}
                {feedback && !analyzingUnified && deliveryLoaded && (
                  <WorkspaceCard key="delivery-coach">
                    <CardContent className="flex flex-col gap-4 px-5 py-5">
                      <StepHeader title="Delivery Coach" done={!!deliveryMetrics} aside={
                        deliveryMetrics?.delivery_score !== null && deliveryMetrics?.delivery_score !== undefined ? (
                          <Badge variant="indigo">{deliveryMetrics.delivery_score}/100 delivery</Badge>
                        ) : undefined
                      } />
                      {deliveryMetrics ? (
                        <DeliveryCoachPanel metrics={deliveryMetrics} />
                      ) : (
                        <DeliveryCoachPanelEmpty />
                      )}
                    </CardContent>
                  </WorkspaceCard>
                )}

                {/* Tournament Prep Workout */}
                {feedback && !analyzingUnified && userId && (
                  <WorkspaceCard key="workout">
                    <CardContent className="flex flex-col gap-4 px-5 py-5">
                      <StepHeader title="Tournament Prep Workout" done={workout?.status === "completed"} />
                      <TournamentWorkoutPanel
                        speechId={speechId}
                        userId={userId}
                        workout={workout}
                        onWorkoutChange={setWorkout}
                        onStartReRecord={startNewAttempt}
                      />
                    </CardContent>
                  </WorkspaceCard>
                )}

                {/* Block Coverage */}
                {feedback && !analyzingUnified && userId && (
                  <WorkspaceCard key="block-coverage">
                    <CardContent id="block-coverage" className="flex flex-col gap-4 px-5 py-5 scroll-mt-20">
                      <StepHeader title="Block Coverage" done={!!blockCoverage && blockCoverage.covered_count === blockCoverage.checks.length && blockCoverage.checks.length > 0} />
                      <BlockCoveragePanel
                        speechId={speechId}
                        userId={userId}
                        coverage={blockCoverage}
                        hasBlockEntries={hasBlockEntries}
                        onCoverageChange={setBlockCoverage}
                      />
                    </CardContent>
                  </WorkspaceCard>
                )}

                {/* Recommended Practice / Drills */}
                {drills.length > 0 ? (
                  <WorkspaceCard key="drills-done">
                    {/* id="drills" is the anchor target for ReportVerdictPanel and PracticeLoopCTA #drills hrefs */}
                    <CardContent id="drills" className="flex flex-col gap-4 px-5 py-5 scroll-mt-20">
                      <StepHeader
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
                      <StepHeader title="Recommended Practice" done={false} />
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
                    <CardContent id="flow" className="flex flex-col gap-4 px-5 py-5 scroll-mt-20">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <StepHeader n={3} title="Flow" done aside={
                          <div className="flex items-center gap-2">
                            {argMap.source_type === "user_corrected" && (
                              <Badge variant="indigo">Flow corrected</Badge>
                            )}
                            <Badge variant="indigo">
                              {argMap.arguments.length} arg{argMap.arguments.length !== 1 ? "s" : ""}
                            </Badge>
                          </div>
                        } />
                        <div className="flex items-center gap-2">
                          <JudgeModeSelector value={judgeViewMode} onChange={setJudgeViewMode} />
                          <button
                            type="button"
                            onClick={() => { setFlowEditMode(true); setEditingArgs(initEditArgs(argMap.arguments)); setCorrectionErr(""); }}
                            className="flex items-center gap-1 rounded-md border border-hairline px-2 py-1 text-xs text-ink-faint hover:text-ink-subtle hover:border-hairline-strong transition-colors"
                          >
                            <Pencil size={10} />
                            Edit
                          </button>
                        </div>
                      </div>

                      {flowEditMode ? (
                        <FlowEditPanel
                          initialArgs={editingArgs}
                          onSave={saveFlowCorrection}
                          onCancel={() => setFlowEditMode(false)}
                          saving={savingCorrection}
                          saveError={correctionErr}
                        />
                      ) : (
                        <>
                          {/* Flow Summary */}
                          <FlowSummary argMap={argMap} />

                          {/* Lens note */}
                          <FlowLensNote judgeMode={judgeViewMode} />

                          {/* Contextual help */}
                          <div className="flex flex-col gap-1.5">
                            <ContextualHelp question="What is a flow?">
                              A flow is a structured map of every argument in your speech. Debate judges — especially flow judges — track claim, warrant, evidence, and impact for each contention. If your flow is clean and extended correctly, you can win even on a thin evidence base.
                            </ContextualHelp>
                            <ContextualHelp question="What does the judge lens change?">
                              Lay judges care about persuasion, clarity, and which side sounds more confident. Flow judges track every argument and drop. Switching the lens shows you the most important weaknesses for each judge type — helping you prioritize your prep.
                            </ContextualHelp>
                          </div>

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
                        </>
                      )}

                      {/* Regenerate coaching CTA */}
                      {isFlowCorrectedAndNeedsRegen(argMap, feedback) && !flowEditMode && (
                        <div className="rounded-lg border border-lav/20 bg-lav/5 px-4 py-3 flex flex-col gap-3">
                          <div className="flex flex-col gap-1">
                            <p className="text-sm font-semibold text-lav">Flow corrected — regenerate coaching</p>
                            <p className="text-xs text-ink-subtle leading-relaxed">
                              Your flow was edited. Regenerate to get updated feedback and drills based on the corrected arguments.
                            </p>
                          </div>
                          {regenErr && <p className="text-xs text-danger">{regenErr}</p>}
                          <Button
                            size="sm"
                            onClick={regenerateFromFlow}
                            disabled={regenerating}
                            className="w-fit"
                          >
                            {regenerating ? "Regenerating…" : "Regenerate coaching from corrected flow"}
                          </Button>
                        </div>
                      )}
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
                    <CardContent id="transcript" className="flex flex-col gap-3 px-5 py-5 scroll-mt-20">
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
                {transcript && !feedback && !analyzingUnified && !activeJob && (
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
                      <Button disabled={!canAnalyze} onClick={startJobAnalysis} size="sm" className="w-full">
                        Analyze My Speech
                      </Button>
                    </CardContent>
                  </WorkspaceCard>
                )}

                {/* Job-based analysis progress */}
                {activeJob && (
                  <motion.div key="job-progress" {...fadeUp(0)}>
                    <AnalysisProgressCard
                      job={activeJob}
                      onRetry={activeJob.status === "failed" ? retryAnalysis : undefined}
                      retrying={retryingJob}
                    />
                    {unifiedAnalysisErr && (
                      <div className="mt-2">
                        <InlineAlert variant="danger">{unifiedAnalysisErr}</InlineAlert>
                      </div>
                    )}
                  </motion.div>
                )}

                {/* Legacy unified analysis loading (manual step-through) */}
                {analyzingUnified && !activeJob && (
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
                        <div className="flex flex-wrap items-center justify-between gap-3">
                          <StepHeader n={3} title="Flow" done aside={
                            <div className="flex items-center gap-2">
                              {argMap.source_type === "user_corrected" && (
                                <Badge variant="indigo">Flow corrected</Badge>
                              )}
                              <Badge variant="indigo">
                                {argMap.arguments.length} arg{argMap.arguments.length !== 1 ? "s" : ""}
                              </Badge>
                            </div>
                          } />
                          <div className="flex items-center gap-2">
                            <JudgeModeSelector value={judgeViewMode} onChange={setJudgeViewMode} />
                            <button
                              type="button"
                              onClick={() => { setFlowEditMode(true); setEditingArgs(initEditArgs(argMap.arguments)); setCorrectionErr(""); }}
                              className="flex items-center gap-1 rounded-md border border-hairline px-2 py-1 text-xs text-ink-faint hover:text-ink-subtle hover:border-hairline-strong transition-colors"
                            >
                              <Pencil size={10} />
                              Edit
                            </button>
                          </div>
                        </div>

                        {flowEditMode ? (
                          <FlowEditPanel
                            initialArgs={editingArgs}
                            onSave={saveFlowCorrection}
                            onCancel={() => setFlowEditMode(false)}
                            saving={savingCorrection}
                            saveError={correctionErr}
                          />
                        ) : (
                          <>
                            {/* Flow Summary */}
                            <FlowSummary argMap={argMap} />

                            {/* Lens note */}
                            <FlowLensNote judgeMode={judgeViewMode} />

                            {/* Contextual help */}
                            <div className="flex flex-col gap-1.5">
                              <ContextualHelp question="What is a flow?">
                                A flow is a structured map of every argument in your speech. Debate judges — especially flow judges — track claim, warrant, evidence, and impact for each contention. If your flow is clean and extended correctly, you can win even on a thin evidence base.
                              </ContextualHelp>
                              <ContextualHelp question="What does the judge lens change?">
                                Lay judges care about persuasion, clarity, and which side sounds more confident. Flow judges track every argument and drop. Switching the lens shows you the most important weaknesses for each judge type — helping you prioritize your prep.
                              </ContextualHelp>
                            </div>

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
                          </>
                        )}

                        {/* Regenerate coaching CTA */}
                        {isFlowCorrectedAndNeedsRegen(argMap, feedback) && !flowEditMode && (
                          <div className="rounded-lg border border-lav/20 bg-lav/5 px-4 py-3 flex flex-col gap-3">
                            <div className="flex flex-col gap-1">
                              <p className="text-sm font-semibold text-lav">Flow corrected — regenerate coaching</p>
                              <p className="text-xs text-ink-subtle leading-relaxed">
                                Your flow was edited. Regenerate to get updated feedback and drills based on the corrected arguments.
                              </p>
                            </div>
                            {regenErr && <p className="text-xs text-danger">{regenErr}</p>}
                            <Button
                              size="sm"
                              onClick={regenerateFromFlow}
                              disabled={regenerating}
                              className="w-fit"
                            >
                              {regenerating ? "Regenerating…" : "Regenerate coaching from corrected flow"}
                            </Button>
                          </div>
                        )}

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

                        {/* Contextual help — warranting */}
                        <ContextualHelp question="Why does warranting matter so much?">
                          A warrant is the logical mechanism that connects your claim to your evidence. Without it, a judge can simply say "so what?" and ignore your argument even if the evidence is strong. Flow judges in particular will drop unwarranted arguments — a claim needs a clear "because" before the evidence or it doesn&apos;t count.
                        </ContextualHelp>

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

                {/* ── Practice Hub header (second render path) ── */}
                {feedback && !analyzingUnified && (
                  <div className="flex items-center gap-2 px-1 pt-1">
                    <Swords size={13} className="shrink-0 text-ink-faint" />
                    <p className="text-[10px] font-semibold uppercase tracking-widest text-ink-faint">
                      Practice Hub
                    </p>
                  </div>
                )}

                {/* Delivery Coach Panel (second render path) */}
                {feedback && !analyzingUnified && deliveryLoaded && (
                  <WorkspaceCard key="delivery-coach-2">
                    <CardContent className="flex flex-col gap-4 px-5 py-5">
                      <StepHeader title="Delivery Coach" done={!!deliveryMetrics} aside={
                        deliveryMetrics?.delivery_score !== null && deliveryMetrics?.delivery_score !== undefined ? (
                          <Badge variant="indigo">{deliveryMetrics.delivery_score}/100 delivery</Badge>
                        ) : undefined
                      } />
                      {deliveryMetrics ? (
                        <DeliveryCoachPanel metrics={deliveryMetrics} />
                      ) : (
                        <DeliveryCoachPanelEmpty />
                      )}
                    </CardContent>
                  </WorkspaceCard>
                )}

                {/* Tournament Prep Workout (second render path) */}
                {feedback && !analyzingUnified && userId && (
                  <WorkspaceCard key="workout-2">
                    <CardContent className="flex flex-col gap-4 px-5 py-5">
                      <StepHeader title="Tournament Prep Workout" done={workout?.status === "completed"} />
                      <TournamentWorkoutPanel
                        speechId={speechId}
                        userId={userId}
                        workout={workout}
                        onWorkoutChange={setWorkout}
                        onStartReRecord={startNewAttempt}
                      />
                    </CardContent>
                  </WorkspaceCard>
                )}

                {/* Block Coverage (second render path) */}
                {feedback && !analyzingUnified && userId && (
                  <WorkspaceCard key="block-coverage-2">
                    <CardContent id="block-coverage-2" className="flex flex-col gap-4 px-5 py-5 scroll-mt-20">
                      <StepHeader title="Block Coverage" done={!!blockCoverage && blockCoverage.covered_count === blockCoverage.checks.length && blockCoverage.checks.length > 0} />
                      <BlockCoveragePanel
                        speechId={speechId}
                        userId={userId}
                        coverage={blockCoverage}
                        hasBlockEntries={hasBlockEntries}
                        onCoverageChange={setBlockCoverage}
                      />
                    </CardContent>
                  </WorkspaceCard>
                )}

                {/* Drills */}
                {feedback && (
                  genDrills ? (
                    <motion.div key="drills-loading" {...fadeUp(0)}>
                      <LoadingCard title="Creating practice drills" messages={MSG_DRILLS} />
                    </motion.div>
                  ) : drills.length > 0 ? (
                    <WorkspaceCard key="drills-done">
                      <CardContent className="flex flex-col gap-4 px-5 py-5">
                        <StepHeader
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
                        <StepHeader title="Practice Drills" done={false} />
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
                    <p className="text-heading text-ink">Evidence Support</p>
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

          {/* Copy Practice Plan — visible only when report is complete */}
          {isComplete && feedback && (
            <motion.div variants={staggerChild} className="no-print">
              <button
                type="button"
                onClick={async () => {
                  if (!feedback || !argMap) return;
                  const payload = {
                    token: "",
                    speech_type: speech.speech_type,
                    side: speech.side,
                    judge_type: speech.judge_type,
                    topic: speech.topic,
                    created_at: speech.created_at,
                    feedback: feedback ? {
                      overall_score: feedback.overall_score,
                      scores: feedback.scores,
                      summary: feedback.summary,
                      strengths: feedback.strengths,
                      weaknesses: feedback.weaknesses,
                      top_3_priorities: feedback.raw_feedback?.top_3_priorities ?? null,
                      structured_issues: null,
                    } : null,
                    arguments: null,
                    drills: drills.map(d => ({
                      title: d.title,
                      description: d.description,
                      skill_target: d.skill_target,
                      prompt: d.prompt,
                      success_criteria: d.success_criteria,
                      difficulty: d.difficulty,
                    })),
                    delivery: deliveryMetrics ? {
                      words_per_minute: deliveryMetrics.words_per_minute,
                      filler_word_count: deliveryMetrics.filler_word_count,
                      delivery_score: deliveryMetrics.delivery_score,
                      pacing_band: deliveryMetrics.pacing_band,
                      repeated_phrases_json: deliveryMetrics.repeated_phrases_json,
                    } : null,
                    transcript_text: null,
                    evidence_summary: null,
                    comparison: null,
                    include_flags: {
                      transcript: false, flow: false, feedback: true,
                      drills: true, delivery: true, evidence_summary: false, improvement: false,
                    },
                  };
                  const text = formatPracticePlan(payload, workout ?? null);
                  const ok = await copyToClipboard(text);
                  if (ok) {
                    setPracticePlanCopied(true);
                    setTimeout(() => setPracticePlanCopied(false), 2500);
                    logEvent("practice_plan_copied", userId, { speech_id: speechId });
                  }
                }}
                className="flex items-center gap-1.5 rounded-md border border-hairline bg-surface px-3 py-2 text-xs font-medium text-ink-subtle transition-colors hover:bg-surface-2 hover:text-ink"
              >
                {practicePlanCopied ? (
                  <><Check size={12} className="text-ok" />Practice plan copied!</>
                ) : (
                  <><Copy size={12} />Copy practice plan</>
                )}
              </button>
            </motion.div>
          )}

        </motion.div>

      {showShareModal && userId && (
        <ShareReportModal
          speechId={speechId}
          userId={userId}
          hasImprovement={!!comparison?.has_parent}
          onClose={() => setShowShareModal(false)}
          onPrint={() => {
            logEvent("report_print_clicked", userId, { speech_id: speechId });
            window.print();
          }}
        />
      )}

      <DeleteDialog
        open={delOpen}
        onOpenChange={(v) => { if (!v && !deleting) { setDelOpen(false); setDeleteErr(""); } }}
        title="Delete this session?"
        description={`"${speech.title}" will be permanently deleted along with its transcript, flow, and feedback.`}
        onConfirm={deleteSession}
        isDeleting={deleting}
        error={deleteErr}
      />
    </AppShell>
  );
}
