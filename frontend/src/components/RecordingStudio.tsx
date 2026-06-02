"use client";

import { motion, AnimatePresence } from "motion/react";
import { Mic, Square, Trash2, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { T, EASE } from "@/lib/motion";

export type RecordState =
  | "idle"
  | "requesting"
  | "recording"
  | "recorded"
  | "uploading"
  | "error";

interface RecordingStudioProps {
  recordState: RecordState;
  recordingSeconds: number;
  recordObjectUrl: string | null;
  recordError: string;
  onStartRecording: () => void;
  onStopRecording: () => void;
  onSaveRecording: () => void;
  onDiscardRecording: () => void;
}

function formatTime(s: number) {
  return `${Math.floor(s / 60).toString().padStart(2, "0")}:${(s % 60).toString().padStart(2, "0")}`;
}

// ── Idle / requesting / error ──────────────────────────────────────────────────
function IdleView({
  state, error, onStart,
}: { state: RecordState; error: string; onStart: () => void }) {
  return (
    <div className="flex flex-col items-center gap-5 py-8">
      {/* Mic button — gentle breathing animation when idle */}
      <div className="relative flex items-center justify-center">
        {state === "idle" && (
          <motion.div
            className="absolute h-20 w-20 rounded-full bg-lav/10"
            animate={{ scale: [1, 1.12, 1], opacity: [0.4, 0.7, 0.4] }}
            transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
          />
        )}
        <motion.button
          type="button"
          onClick={onStart}
          disabled={state === "requesting"}
          whileHover={{ scale: 1.06 }}
          whileTap={{ scale: 0.94 }}
          transition={T.fast}
          className="relative z-10 flex h-16 w-16 cursor-pointer items-center justify-center rounded-full bg-lav disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50"
        >
          <Mic size={26} className="text-white" />
        </motion.button>
      </div>

      <div className="flex flex-col items-center gap-1 text-center">
        <p className="text-sm font-medium text-ink">
          {state === "requesting" ? "Requesting microphone…" : "Tap to record"}
        </p>
        <p className="text-xs text-ink-subtle">Aim for at least 30 seconds</p>
      </div>

      {state === "error" && error && (
        <motion.p
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          className="max-w-xs text-center text-sm text-danger"
        >
          {error}
        </motion.p>
      )}
    </div>
  );
}

// ── Recording ──────────────────────────────────────────────────────────────────
function RecordingView({ seconds, onStop }: { seconds: number; onStop: () => void }) {
  return (
    <div className="flex flex-col items-center gap-6 py-8">
      {/* Pulsing rings + stop button */}
      <div className="relative flex items-center justify-center">
        {[0, 1, 2].map((i) => (
          <motion.div
            key={i}
            className="absolute rounded-full border border-danger/20"
            style={{ width: 72 + i * 28, height: 72 + i * 28 }}
            animate={{ scale: [1, 1.15, 1], opacity: [0.5, 0, 0.5] }}
            transition={{
              duration: 2,
              repeat: Infinity,
              delay: i * 0.4,
              ease: "easeOut",
            }}
          />
        ))}
        <motion.button
          type="button"
          onClick={onStop}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          transition={T.fast}
          className="relative z-10 flex h-16 w-16 cursor-pointer items-center justify-center rounded-full bg-danger focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-danger/50"
        >
          <Square size={18} className="fill-white text-white" />
        </motion.button>
      </div>

      {/* Timer */}
      <div className="flex flex-col items-center gap-1">
        <div className="flex items-center gap-2">
          <motion.span
            className="h-1.5 w-1.5 rounded-full bg-danger"
            animate={{ opacity: [1, 0.3, 1] }}
            transition={{ duration: 1, repeat: Infinity }}
          />
          <AnimatePresence mode="popLayout">
            <motion.span
              key={seconds}
              initial={{ opacity: 0.5, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.12, ease: EASE }}
              className="font-mono text-4xl font-semibold tabular-nums tracking-tight text-ink"
            >
              {formatTime(seconds)}
            </motion.span>
          </AnimatePresence>
        </div>
        <p className="text-xs text-ink-subtle">Recording — tap square to stop</p>
      </div>
    </div>
  );
}

// ── Recorded — playback + save/discard ────────────────────────────────────────
function RecordedView({
  url, seconds, onSave, onDiscard,
}: { url: string; seconds: number; onSave: () => void; onDiscard: () => void }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: EASE }}
      className="flex flex-col gap-4 py-4"
    >
      <div className="rounded-lg border border-hairline bg-surface-2 p-3">
        <div className="mb-2 flex items-center justify-between">
          <span className="text-xs font-medium text-ink-subtle">Preview</span>
          <span className="font-mono text-xs text-ink-faint">{formatTime(seconds)}</span>
        </div>
        <audio src={url} controls className="h-8 w-full" />
      </div>
      <div className="flex gap-2">
        <motion.div className="flex-1" whileHover={{ scale: 1.01 }} whileTap={{ scale: 0.99 }}>
          <Button onClick={onSave} size="sm" className="w-full gap-1.5">
            Save &amp; Continue
          </Button>
        </motion.div>
        <Button
          variant="secondary" size="sm" onClick={onDiscard}
          className="gap-1.5 text-ink-subtle hover:border-danger/30 hover:text-danger"
        >
          <Trash2 size={12} />
          Discard
        </Button>
      </div>
    </motion.div>
  );
}

// ── Uploading ─────────────────────────────────────────────────────────────────
function UploadingView() {
  return (
    <div className="flex flex-col items-center gap-3 py-8">
      <motion.div
        className="flex h-7 w-7 items-center justify-center rounded-lg bg-lav"
        animate={{ rotate: 360 }}
        transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
      >
        <RotateCcw size={14} className="text-white" />
      </motion.div>
      <p className="text-sm text-ink-subtle">Saving recording…</p>
    </div>
  );
}

// ── Main ───────────────────────────────────────────────────────────────────────
export default function RecordingStudio({
  recordState,
  recordingSeconds,
  recordObjectUrl,
  recordError,
  onStartRecording,
  onStopRecording,
  onSaveRecording,
  onDiscardRecording,
}: RecordingStudioProps) {
  return (
    <AnimatePresence mode="wait">
      {recordState === "recording" ? (
        <motion.div key="recording" {...{ initial: { opacity: 0 }, animate: { opacity: 1 }, exit: { opacity: 0 }, transition: T.fast }}>
          <RecordingView seconds={recordingSeconds} onStop={onStopRecording} />
        </motion.div>
      ) : recordState === "recorded" && recordObjectUrl ? (
        <motion.div key="recorded" {...{ initial: { opacity: 0 }, animate: { opacity: 1 }, exit: { opacity: 0 }, transition: T.fast }}>
          <RecordedView url={recordObjectUrl} seconds={recordingSeconds} onSave={onSaveRecording} onDiscard={onDiscardRecording} />
        </motion.div>
      ) : recordState === "uploading" ? (
        <motion.div key="uploading" {...{ initial: { opacity: 0 }, animate: { opacity: 1 }, exit: { opacity: 0 }, transition: T.fast }}>
          <UploadingView />
        </motion.div>
      ) : (
        <motion.div key="idle" {...{ initial: { opacity: 0 }, animate: { opacity: 1 }, exit: { opacity: 0 }, transition: T.fast }}>
          <IdleView state={recordState} error={recordError} onStart={onStartRecording} />
        </motion.div>
      )}
    </AnimatePresence>
  );
}
