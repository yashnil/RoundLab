"use client";

import { useId, useRef, useState } from "react";
import { PHASE_LABELS, isCrossfire, speechTypeLabel } from "@/lib/roundModel";
import { useRecorder } from "@/hooks/useRecorder";
import { createClient } from "@/lib/supabase";
import * as roundApi from "@/lib/roundApi";
import { ApiError } from "@/lib/api";
import type { RoundPhaseType, RoundSide, RoundSpeech } from "@/types/round";

interface Props {
  roundId: string;
  phase: RoundPhaseType;
  studentSide: RoundSide;
  isStudentTurn: boolean;
  onSpeechSubmitted: (speech: RoundSpeech) => void;
  onOpponentSpeechRequested: () => void;
  onAdvancePhase: () => void;
  isLoading: boolean;
}

type CaptureMode = "record" | "type" | "paste";

async function uploadAudioBlob(blob: Blob, roundId: string, phase: string): Promise<string> {
  const supabase = createClient();
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) throw new Error("Not signed in.");

  const ext = blob.type.includes("mp4") ? "mp4" : blob.type.includes("ogg") ? "ogg" : "webm";
  const path = `${session.user.id}/rounds/${roundId}/${phase}-${Date.now()}.${ext}`;
  const { error } = await supabase.storage
    .from("speech-audio")
    .upload(path, blob, { contentType: blob.type, upsert: false });
  if (error) throw new Error(error.message);

  const { data: signed } = await supabase.storage
    .from("speech-audio")
    .createSignedUrl(path, 60 * 60 * 6);
  if (!signed?.signedUrl) throw new Error("Failed to get upload URL.");
  return signed.signedUrl;
}

export function RoundSpeechCapture({
  roundId,
  phase,
  studentSide,
  isStudentTurn,
  onSpeechSubmitted,
  onOpponentSpeechRequested,
  onAdvancePhase,
  isLoading,
}: Props) {
  const [mode, setMode] = useState<CaptureMode>("type");
  const [transcript, setTranscript] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const submittedKeyRef = useRef<string | null>(null);
  const idempotencyKey = `student-${roundId}-${phase}`;

  const recorder = useRecorder();
  const textareaId = useId();

  const phaseLabel = PHASE_LABELS[phase] ?? phase;
  const crossfire = isCrossfire(phase);
  const busy = isLoading || submitting;

  const recState = recorder.state;
  const recStatus = recState.status;

  // ── Submit helpers ──────────────────────────────────────────────────────────

  async function submitWithText(text: string) {
    if (submittedKeyRef.current === idempotencyKey) return;
    if (!text.trim()) { setError("Please enter your speech."); return; }
    setSubmitting(true);
    setError(null);
    try {
      const speech = await roundApi.submitStudentSpeech(roundId, phase, {
        transcriptText: text.trim(),
        idempotencyKey,
      });
      submittedKeyRef.current = idempotencyKey;
      setTranscript("");
      onSpeechSubmitted(speech);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Speech submission failed.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleRecordSubmit() {
    if (!recState.blob) { setError("No recording available."); return; }
    if (submittedKeyRef.current === idempotencyKey) return;
    setSubmitting(true);
    setError(null);
    try {
      const audioUrl = await uploadAudioBlob(recState.blob, roundId, phase);
      const speech = await roundApi.submitStudentSpeech(roundId, phase, {
        audioUrl,
        idempotencyKey,
      });
      submittedKeyRef.current = idempotencyKey;
      recorder.reset();
      onSpeechSubmitted(speech);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Submission failed. Your recording is still saved.");
    } finally {
      setSubmitting(false);
    }
  }

  // ── Opponent turn ───────────────────────────────────────────────────────────

  if (!isStudentTurn && !crossfire) {
    return (
      <div className="space-y-4">
        <div className="rounded-lg border bg-muted/20 p-4">
          <p className="text-sm font-medium">AI Opponent&#39;s Turn</p>
          <p className="text-xs text-muted-foreground mt-1">
            The AI opponent will deliver the {phaseLabel}.
          </p>
        </div>
        <button
          onClick={onOpponentSpeechRequested}
          disabled={busy}
          className="w-full rounded-md bg-secondary px-4 py-2.5 text-sm font-medium transition-opacity disabled:opacity-50"
        >
          {busy ? "Generating opponent speech..." : `Generate ${phaseLabel}`}
        </button>
      </div>
    );
  }

  // ── Crossfire ───────────────────────────────────────────────────────────────

  if (crossfire) {
    return (
      <div className="space-y-4">
        <div className="rounded-lg border bg-sky-50 dark:bg-sky-950/20 p-4">
          <p className="text-sm font-medium">{phaseLabel}</p>
          <p className="text-xs text-muted-foreground mt-1">
            Type your crossfire answers or advance to the next phase.
          </p>
        </div>
        <label htmlFor={textareaId} className="sr-only">Crossfire response</label>
        <textarea
          id={textareaId}
          className="w-full rounded-md border bg-background px-3 py-2 text-sm min-h-[80px] resize-none focus:outline-none focus:ring-2 focus:ring-ring"
          placeholder="Type your crossfire response..."
          value={transcript}
          onChange={(e) => setTranscript(e.target.value)}
        />
        {error && <p className="text-xs text-red-600">{error}</p>}
        <div className="flex gap-2">
          <button
            onClick={() => submitWithText(transcript)}
            disabled={busy || !transcript.trim()}
            className="flex-1 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-50"
          >
            {submitting ? "Submitting..." : "Submit Answer"}
          </button>
          <button
            onClick={onAdvancePhase}
            disabled={busy}
            className="rounded-md border px-4 py-2 text-sm font-medium disabled:opacity-50"
          >
            Advance Phase
          </button>
        </div>
      </div>
    );
  }

  // ── Student speech ──────────────────────────────────────────────────────────

  // Derived from errorKind
  const isPermissionError = recStatus === "error" && recState.errorKind === "permission";
  const isUnsupported = recStatus === "error" && recState.errorKind === "unsupported";
  const isRecording = recStatus === "recording";
  const hasRecording = recStatus === "recorded" || recStatus === "playing";
  const isUploading = recStatus === "uploading";
  // Can click "Enable Microphone" / "Start Recording" when idle or ready
  const canStart = recStatus === "idle" || recStatus === "ready";

  return (
    <div className="space-y-4">
      <div className="rounded-lg border bg-emerald-50 dark:bg-emerald-950/20 p-4">
        <p className="text-sm font-medium">Your Turn — {phaseLabel}</p>
        <p className="text-xs text-muted-foreground mt-1">
          Deliver the {speechTypeLabel(phase)}. Record or type your speech below.
        </p>
      </div>

      {/* Mode tabs */}
      <div className="flex gap-1 rounded-md border w-fit text-xs" role="tablist" aria-label="Input mode">
        {(["record", "type", "paste"] as CaptureMode[]).map((m) => (
          <button
            key={m}
            role="tab"
            aria-selected={mode === m}
            onClick={() => setMode(m)}
            className={`px-3 py-1.5 capitalize transition-colors first:rounded-l-md last:rounded-r-md ${
              mode === m ? "bg-primary text-primary-foreground" : "hover:bg-accent"
            }`}
          >
            {m}
          </button>
        ))}
      </div>

      {/* Record mode */}
      {mode === "record" && (
        <div className="space-y-3" role="tabpanel">
          {isUnsupported && (
            <p className="text-xs text-amber-700 dark:text-amber-400 rounded-md border border-amber-200 bg-amber-50 px-3 py-2">
              {recState.error || "Recording isn&#39;t supported in this browser."}{" "}
              Use the Type or Paste tab instead.
            </p>
          )}
          {isPermissionError && (
            <div className="text-xs text-red-600 rounded-md border border-red-200 bg-red-50 px-3 py-2">
              <span>{recState.error || "Microphone access was denied."}{" "}</span>
              <button onClick={recorder.requestPermission} className="underline font-medium">
                Try again
              </button>
              <span>{" "}or use the Type tab.</span>
            </div>
          )}
          {canStart && !isUnsupported && !isPermissionError && (
            <button
              onClick={recStatus === "idle" ? recorder.requestPermission : recorder.start}
              disabled={busy}
              className="w-full rounded-md bg-red-600 hover:bg-red-700 text-white px-4 py-2.5 text-sm font-medium transition-colors disabled:opacity-50"
            >
              {recStatus === "idle" ? "Enable Microphone" : "Start Recording"}
            </button>
          )}
          {isRecording && (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <span className="inline-block w-2 h-2 rounded-full bg-red-500 animate-pulse" aria-hidden />
                <span className="text-xs font-medium">Recording</span>
                <span className="text-xs text-muted-foreground ml-auto">
                  {Math.floor(recState.durationMs / 1000)}s
                </span>
              </div>
              <div className="w-full h-1.5 rounded-full bg-muted overflow-hidden" aria-hidden>
                <div
                  className="h-full bg-red-500 transition-all duration-75"
                  style={{ width: `${Math.round(recorder.level * 100)}%` }}
                />
              </div>
              <button
                onClick={recorder.stop}
                className="w-full rounded-md border border-red-300 px-4 py-2 text-sm font-medium text-red-700 hover:bg-red-50 transition-colors"
              >
                Stop Recording
              </button>
            </div>
          )}
          {hasRecording && (
            <div className="space-y-3 rounded-md border p-3">
              <div className="flex items-center gap-2 text-xs">
                <span className="text-emerald-600 font-medium">Recording ready</span>
                <span className="text-muted-foreground">
                  {(recState.durationMs / 1000).toFixed(1)}s
                </span>
              </div>
              <div className="flex gap-2">
                {recStatus === "recorded" && (
                  <button
                    onClick={recorder.play}
                    className="rounded-md border px-3 py-1.5 text-xs font-medium hover:bg-accent"
                  >
                    Play back
                  </button>
                )}
                <button
                  onClick={() => recorder.reset()}
                  disabled={busy}
                  className="rounded-md border px-3 py-1.5 text-xs font-medium text-muted-foreground hover:text-red-600 hover:border-red-200 transition-colors disabled:opacity-50"
                >
                  Re-record
                </button>
              </div>
              {error && <p className="text-xs text-red-600">{error}</p>}
              <button
                onClick={handleRecordSubmit}
                disabled={busy}
                className="w-full rounded-md bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground disabled:opacity-50 transition-opacity"
              >
                {submitting ? "Uploading & submitting..." : "Submit Recording"}
              </button>
            </div>
          )}
          {isUploading && (
            <p className="text-xs text-muted-foreground">Uploading...</p>
          )}
        </div>
      )}

      {/* Type / Paste mode */}
      {(mode === "type" || mode === "paste") && (
        <div className="space-y-3" role="tabpanel">
          <label htmlFor={textareaId} className="sr-only">Speech text</label>
          <textarea
            id={textareaId}
            className="w-full rounded-md border bg-background px-3 py-2 text-sm min-h-[140px] resize-none focus:outline-none focus:ring-2 focus:ring-ring"
            placeholder={
              mode === "paste"
                ? "Paste your speech transcript here..."
                : "Type your speech or an outline of your arguments..."
            }
            value={transcript}
            onChange={(e) => setTranscript(e.target.value)}
          />
          {error && <p className="text-xs text-red-600">{error}</p>}
          <div className="flex gap-2">
            <button
              onClick={() => submitWithText(transcript)}
              disabled={busy || !transcript.trim()}
              className="flex-1 rounded-md bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground disabled:opacity-50 transition-opacity"
            >
              {submitting ? "Submitting..." : "Submit Speech"}
            </button>
            <button
              onClick={onAdvancePhase}
              disabled={busy}
              className="rounded-md border px-4 py-2.5 text-sm font-medium disabled:opacity-50 hover:bg-accent transition-colors"
            >
              Skip →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
