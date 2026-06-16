"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { motion, AnimatePresence } from "motion/react";
import {
  Check,
  RefreshCw, Trash2, Copy,
  ShieldAlert, Sparkles, Share2, Printer,
} from "lucide-react";
import { useCopy } from "@/lib/useCopy";
import { deriveAnalysisRecoveryState, isJobActive } from "@/lib/jobHelpers";
import AppShell from "@/components/shell/AppShell";
import SpeechReportWorkspace from "@/components/speech/SpeechReportWorkspace";
import SpeechProcessingWorkspace from "@/components/speech/SpeechProcessingWorkspace";
import SpeechCaptureWorkspace from "@/components/speech/SpeechCaptureWorkspace";
import {
  StepHeader, InlineAlert, StatusBadge, CoachDiagnosis, WorkspaceCard,
  FlowSummary, TopIssueCoachNote, FlowCoachNote, FlowLensNote, ContextualHelp,
  getVerifiedOverallScore, isReportStale,
} from "@/components/speech/reportPrimitives";
import WorkflowStepper from "@/components/WorkflowStepper";
import { type JudgeViewMode } from "@/components/JudgeModeSelector";
import ReportVerdictPanel from "@/components/ReportVerdictPanel";
import DeleteDialog from "@/components/DeleteDialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { createClient } from "@/lib/supabase";
import { apiFetch } from "@/lib/api";
import { staggerParent, staggerChild, T } from "@/lib/motion";
import PracticeLoopCTA from "@/components/PracticeLoopCTA";
import ImprovementComparisonCard from "@/components/ImprovementComparisonCard";
import CoachMarginNote from "@/components/CoachMarginNote";
import EvidenceSupportPanel from "@/components/EvidenceSupportPanel";
import ShareReportModal from "@/components/ShareReportModal";
import { logEvent } from "@/lib/analytics";
import { formatPracticePlan, copyToClipboard } from "@/lib/reportHelpers";
import { deriveEvidenceRiskSummary } from "@/lib/debateHelpers";
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
              <SpeechCaptureWorkspace
                speech={speech} resetting={resetting} resetAudio={resetAudio}
                recBusy={recBusy} mode={mode} setMode={setMode}
                recordStudioState={recordStudioState} rec={rec}
                handleStartRec={handleStartRec} saveRec={saveRec} handleDiscardRec={handleDiscardRec}
                upload={upload} onFileChange={onFileChange} uploadFile={uploadFile}
                pastedText={pastedText} setPastedText={setPastedText} pasteErr={pasteErr}
                submitPastedText={submitPastedText} submittingText={submittingText}
              />
            )}

            {/* ── For Complete Sessions: Coaching Report → Practice → Arguments → Input ── */}
            {isComplete ? (
              <SpeechReportWorkspace
                speech={speech} feedback={feedback} argMap={argMap} drills={drills}
                transcript={transcript} userId={userId} speechId={speechId}
                analyzingUnified={analyzingUnified} genFb={genFb} genDrills={genDrills}
                drillErr={drillErr} updatingDrill={updatingDrill} workout={workout}
                freshResults={freshResults} savedChecks={savedChecks}
                blockCoverage={blockCoverage} hasBlockEntries={hasBlockEntries}
                deliveryLoaded={deliveryLoaded} deliveryMetrics={deliveryMetrics}
                judgeViewMode={judgeViewMode} showTableView={showTableView}
                flowEditMode={flowEditMode} editingArgs={editingArgs}
                savingCorrection={savingCorrection} correctionErr={correctionErr}
                regenErr={regenErr} regenerating={regenerating}
                setFeedbackRated={setFeedbackRated} setWorkout={setWorkout}
                setBlockCoverage={setBlockCoverage} setJudgeViewMode={setJudgeViewMode}
                setFlowEditMode={setFlowEditMode} setEditingArgs={setEditingArgs}
                setCorrectionErr={setCorrectionErr} setShowTableView={setShowTableView}
                generateFeedback={generateFeedback} generateDrills={generateDrills}
                updateDrillStatus={updateDrillStatus} saveFlowCorrection={saveFlowCorrection}
                regenerateFromFlow={regenerateFromFlow} startNewAttempt={startNewAttempt}
              />
            ) : (
              <SpeechProcessingWorkspace
                speech={speech} transcript={transcript} analyzingUnified={analyzingUnified}
                activeJob={activeJob} canAnalyze={canAnalyze} startJobAnalysis={startJobAnalysis}
                unifiedAnalysisErr={unifiedAnalysisErr} retryAnalysis={retryAnalysis}
                retryingJob={retryingJob} analysisStage={analysisStage} argMap={argMap}
                genFlow={genFlow} feedback={feedback} genFb={genFb} generateFeedback={generateFeedback}
                judgeViewMode={judgeViewMode} setJudgeViewMode={setJudgeViewMode}
                flowEditMode={flowEditMode} setFlowEditMode={setFlowEditMode} editingArgs={editingArgs}
                setEditingArgs={setEditingArgs} setCorrectionErr={setCorrectionErr}
                saveFlowCorrection={saveFlowCorrection} savingCorrection={savingCorrection}
                correctionErr={correctionErr} showTableView={showTableView} setShowTableView={setShowTableView}
                regenErr={regenErr} regenerating={regenerating} regenerateFromFlow={regenerateFromFlow}
                resetAudio={resetAudio} copyRFD={copyRFD} rfdCopied={rfdCopied} userId={userId}
                speechId={speechId} setFeedbackRated={setFeedbackRated} drills={drills}
                updateDrillStatus={updateDrillStatus} updatingDrill={updatingDrill}
                deliveryLoaded={deliveryLoaded} deliveryMetrics={deliveryMetrics} workout={workout}
                setWorkout={setWorkout} startNewAttempt={startNewAttempt} blockCoverage={blockCoverage}
                setBlockCoverage={setBlockCoverage} hasBlockEntries={hasBlockEntries}
                genDrills={genDrills} drillErr={drillErr} generateDrills={generateDrills}
              />
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
