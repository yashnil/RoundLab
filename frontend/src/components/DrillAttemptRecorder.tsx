"use client";

import { Mic, Square, Trash2, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import RecordingTimer from "@/components/practice/RecordingTimer";
import RecordingMeter from "@/components/practice/RecordingMeter";
import { useRecorder } from "@/hooks/useRecorder";
import type { DrillAttempt } from "@/types";

interface DrillAttemptRecorderProps {
  drillId: string;
  userId: string;
  speechId: string;
  onAttemptSaved: (attempt: DrillAttempt) => void;
}

function extFromMime(mime: string | undefined): string {
  if (!mime) return "webm";
  if (mime.includes("mp4")) return "mp4";
  if (mime.includes("ogg")) return "ogg";
  return "webm";
}

function statusMessage(status: string, error: string | null): string {
  switch (status) {
    case "requesting-permission":
      return "Requesting microphone access";
    case "recording":
      return "Recording in progress";
    case "stopping":
      return "Finishing your recording";
    case "recorded":
      return "Recording ready to review";
    case "uploading":
      return "Saving your attempt";
    case "error":
      return error ?? "Something went wrong";
    default:
      return "";
  }
}

/**
 * Drill attempt recorder, driven by the shared useRecorder state machine.
 * Upload (Supabase storage + attempt API) is passed to the recorder so a
 * failure preserves the local take for retry.
 */
export default function DrillAttemptRecorder({
  drillId,
  userId,
  speechId,
  onAttemptSaved,
}: DrillAttemptRecorderProps) {
  const rec = useRecorder();
  const { status } = rec.state;

  async function handleStart() {
    if (status === "idle" || status === "error") {
      await rec.requestPermission();
    }
    rec.start();
  }

  async function handleSave() {
    const ext = extFromMime(rec.state.blob?.type);
    let saved: DrillAttempt | null = null;
    const ok = await rec.upload(async (blob) => {
      if (blob.size === 0) {
        throw new Error("Recording was empty — please record again.");
      }
      const path = `${userId}/${speechId}/drills/${drillId}/attempt-${Date.now()}.${ext}`;
      const { createClient } = await import("@/lib/supabase");
      const sb = createClient();
      const { error: uploadErr } = await sb.storage.from("audio").upload(path, blob, {
        upsert: false,
        contentType: blob.type || "audio/webm",
      });
      if (uploadErr) throw new Error(`Upload failed: ${uploadErr.message}`);
      const { apiFetch } = await import("@/lib/api");
      saved = await apiFetch<DrillAttempt>(
        `/drills/${drillId}/attempts?user_id=${encodeURIComponent(userId)}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ audio_url: path }),
        },
      );
    });
    if (ok && saved) {
      onAttemptSaved(saved);
      rec.reset();
    }
  }

  const isIdle = status === "idle" || status === "requesting-permission" || status === "error";

  return (
    <div className="rounded-lg border border-hairline bg-surface-2 p-4">
      <div className="mb-2 flex items-center gap-1.5">
        <Mic size={12} className="text-lav" aria-hidden="true" />
        <span className="text-eyebrow text-ink-subtle">Record attempt</span>
      </div>

      {/* Live status for assistive tech (status text, not per-second timer) */}
      <p className="sr-only" role="status" aria-live="polite">
        {statusMessage(status, rec.state.error)}
      </p>

      <div className="min-h-[120px]">
        {isIdle ? (
          <div className="flex flex-col items-center gap-3 py-4">
            <button
              type="button"
              onClick={handleStart}
              disabled={status === "requesting-permission"}
              aria-label="Start recording your attempt"
              className="flex h-12 w-12 items-center justify-center rounded-full bg-lav transition-opacity hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50 disabled:opacity-50"
            >
              <Mic size={20} className="text-white" aria-hidden="true" />
            </button>
            <p className="text-xs text-ink-subtle">
              {status === "requesting-permission" ? "Requesting mic…" : "Tap to record"}
            </p>
            {status === "error" && rec.state.error && (
              <p className="max-w-xs text-center text-xs text-danger">{rec.state.error}</p>
            )}
          </div>
        ) : status === "recording" || status === "stopping" ? (
          <div className="flex flex-col items-center gap-3 py-4">
            <button
              type="button"
              onClick={rec.stop}
              disabled={status === "stopping"}
              aria-label="Stop recording"
              className="flex h-12 w-12 items-center justify-center rounded-full bg-danger transition-opacity hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-danger/50 disabled:opacity-60"
            >
              <Square size={14} className="fill-white text-white" aria-hidden="true" />
            </button>
            <RecordingTimer ms={rec.state.durationMs} active={status === "recording"} />
            <RecordingMeter level={rec.level} />
            <p className="text-xs text-ink-subtle">
              {status === "stopping" ? "Finishing…" : "Recording…"}
            </p>
          </div>
        ) : status === "recorded" && rec.state.url ? (
          <div className="flex flex-col gap-3">
            <div className="rounded-md border border-hairline bg-surface-3 p-2">
              <div className="mb-1 flex items-center justify-between">
                <span className="text-xs font-medium text-ink-subtle">Preview</span>
                <span className="font-mono text-xs tabular-nums text-ink-faint">
                  {Math.round(rec.state.durationMs / 1000)}s
                </span>
              </div>
              <audio src={rec.state.url} controls className="h-8 w-full" aria-label="Attempt preview" />
            </div>
            {rec.state.errorKind === "upload" && rec.state.error && (
              <p className="text-xs text-danger">{rec.state.error}</p>
            )}
            <div className="flex gap-2">
              <Button onClick={handleSave} size="sm" className="flex-1 gap-1.5">
                <Upload size={12} aria-hidden="true" />
                Save attempt
              </Button>
              <Button
                variant="secondary"
                size="sm"
                onClick={rec.reset}
                className="gap-1.5 text-ink-subtle hover:border-danger/30 hover:text-danger"
              >
                <Trash2 size={12} aria-hidden="true" />
                Discard
              </Button>
            </div>
          </div>
        ) : status === "uploading" ? (
          <div className="flex flex-col items-center gap-2 py-4">
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-lav border-t-transparent" aria-hidden="true" />
            <p className="text-xs text-ink-subtle">Saving &amp; analyzing attempt…</p>
            <p className="text-[10px] text-ink-faint">This may take 15–20 seconds</p>
          </div>
        ) : null}
      </div>
    </div>
  );
}
