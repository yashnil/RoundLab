"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Mic, Square, Trash2, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { T, EASE } from "@/lib/motion";
import RecordingMeter from "@/components/practice/RecordingMeter";

export type RecordState =
  | "idle"
  | "requesting"
  | "countdown"
  | "recording"
  | "recorded"
  | "uploading"
  | "error";

interface RecordingStudioProps {
  recordState: RecordState;
  recordingSeconds: number;
  recordObjectUrl: string | null;
  recordError: string;
  /** Real 0..1 input level from the recorder's analyser (drives the meter). */
  level?: number;
  onStartRecording: () => void;
  onStopRecording: () => void;
  onSaveRecording: () => void;
  onDiscardRecording: () => void;
}

function formatTime(s: number) {
  return `${Math.floor(s / 60).toString().padStart(2, "0")}:${(s % 60).toString().padStart(2, "0")}`;
}

// ── Countdown (3-2-1-Speak) ────────────────────────────────────────────────────

function CountdownView({ count }: { count: number | "go" }) {
  return (
    <div className="flex flex-col items-center gap-5 py-8">
      <div className="relative flex items-center justify-center">
        <motion.div
          className="absolute rounded-full border-2 border-lav/30"
          animate={{ width: [60, 100, 60], height: [60, 100, 60], opacity: [0.6, 0, 0.6] }}
          transition={{ duration: 1, repeat: Infinity, ease: "easeOut" }}
        />
        <AnimatePresence mode="wait">
          <motion.div
            key={count}
            initial={{ scale: 1.6, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.6, opacity: 0 }}
            transition={{ duration: 0.35, ease: EASE }}
            className="relative flex h-20 w-20 items-center justify-center rounded-full border-2 border-lav/50 bg-lav/10"
          >
            {count === "go" ? (
              <Mic size={28} className="text-lav" />
            ) : (
              <span className="text-3xl font-bold tabular-nums text-lav">{count}</span>
            )}
          </motion.div>
        </AnimatePresence>
      </div>
      <div className="flex flex-col items-center gap-1 text-center">
        <p className="text-sm font-semibold text-ink">
          {count === "go" ? "Speak!" : "Get ready…"}
        </p>
        <p className="text-xs text-ink-subtle">Recording starts in a moment</p>
        <p className="text-[10px] text-ink-faint mt-0.5">
          <kbd className="rounded bg-surface-3 px-1 py-0.5 font-mono text-[9px]">Esc</kbd>
          {" "}to cancel
        </p>
      </div>
    </div>
  );
}

// ── Idle / requesting / error ──────────────────────────────────────────────────

function IdleView({
  state, error, onStart,
}: { state: RecordState; error: string; onStart: () => void }) {
  return (
    <div className="flex flex-col items-center gap-5 py-6">
      {/* Eyebrow */}
      <p className="text-eyebrow text-ink-subtle">Practice Rep</p>

      {/* Mic button — breathing animation when idle */}
      <div className="relative flex items-center justify-center">
        {state === "idle" && (
          <>
            <motion.div
              className="absolute h-28 w-28 rounded-full bg-lav/5"
              animate={{ scale: [1, 1.18, 1], opacity: [0.3, 0.7, 0.3] }}
              transition={{ duration: 3.5, repeat: Infinity, ease: "easeInOut" }}
            />
            <motion.div
              className="absolute h-20 w-20 rounded-full bg-lav/8"
              animate={{ scale: [1, 1.12, 1], opacity: [0.5, 0.9, 0.5] }}
              transition={{ duration: 3.5, repeat: Infinity, ease: "easeInOut", delay: 0.3 }}
            />
          </>
        )}
        <motion.button
          type="button"
          onClick={onStart}
          disabled={state === "requesting"}
          whileHover={{ scale: 1.08 }}
          whileTap={{ scale: 0.92 }}
          transition={T.fast}
          className="relative z-10 flex h-16 w-16 cursor-pointer items-center justify-center rounded-full bg-lav disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50"
          style={{ boxShadow: "0 0 32px -6px oklch(0.510 0.156 278 / 0.60)" }}
          aria-label="Start recording"
        >
          <Mic size={26} className="text-white" />
        </motion.button>
      </div>

      <div className="flex flex-col items-center gap-2 text-center">
        <p className="text-sm font-semibold text-ink">
          {state === "requesting" ? "Requesting microphone…" : "Ready when you are"}
        </p>
        <p className="text-xs text-ink-subtle">3-second countdown · speak for 30+ seconds</p>

        {/* Keyboard shortcut hints — hidden on touch-primary devices */}
        {state === "idle" && (
          <div className="mt-0.5 hidden items-center gap-2 rounded-full border border-hairline bg-surface-2 px-3 py-1.5 sm:flex">
            <kbd className="rounded bg-surface-3 px-1.5 py-0.5 font-mono text-[10px] text-ink-faint">Space</kbd>
            <span className="text-[10px] text-ink-faint">to begin</span>
            <span className="text-[10px] text-ink-faint/50">·</span>
            <kbd className="rounded bg-surface-3 px-1.5 py-0.5 font-mono text-[10px] text-ink-faint">Esc</kbd>
            <span className="text-[10px] text-ink-faint">to cancel</span>
          </div>
        )}
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

function RecordingView({ seconds, level, onStop }: { seconds: number; level: number; onStop: () => void }) {
  return (
    <div className="flex flex-col items-center gap-5 py-5">

      {/* LIVE REC badge */}
      <div className="flex items-center gap-2 rounded-full border border-danger/25 bg-danger/8 px-3 py-1.5">
        <motion.span
          className="h-1.5 w-1.5 rounded-full bg-danger"
          animate={{ opacity: [1, 0.25, 1] }}
          transition={{ duration: 1, repeat: Infinity }}
        />
        <span className="text-[10px] font-bold uppercase tracking-wider text-danger">Recording</span>
      </div>

      {/* Timer — dominant focal object */}
      <AnimatePresence mode="popLayout">
        <motion.span
          key={seconds}
          initial={{ opacity: 0.5, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.12, ease: EASE }}
          className="font-mono text-5xl font-bold tabular-nums tracking-tight text-ink"
        >
          {formatTime(seconds)}
        </motion.span>
      </AnimatePresence>

      {/* Real input-level meter — reflects the live mic, not a decorative loop */}
      <RecordingMeter level={level} bars={18} className="h-16" />

      {/* Stop button with pulsing rings */}
      <div className="relative flex items-center justify-center">
        {[0, 1, 2].map((i) => (
          <motion.div
            key={i}
            className="absolute rounded-full border border-danger/15"
            style={{ width: 72 + i * 28, height: 72 + i * 28 }}
            animate={{ scale: [1, 1.15, 1], opacity: [0.5, 0, 0.5] }}
            transition={{ duration: 2.2, repeat: Infinity, delay: i * 0.45, ease: "easeOut" }}
          />
        ))}
        <motion.button
          type="button"
          onClick={onStop}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          transition={T.fast}
          className="relative z-10 flex h-16 w-16 cursor-pointer items-center justify-center rounded-full bg-danger focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-danger/50"
          aria-label="Stop recording"
        >
          <Square size={20} className="fill-white text-white" />
        </motion.button>
      </div>

      {/* Status text */}
      <div className="flex flex-col items-center gap-1 text-center">
        {seconds >= 30 ? (
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-xs font-medium text-ok">
            ✓ Good length — stop anytime or keep going
          </motion.p>
        ) : (
          <p className="text-xs text-ink-subtle">
            Keep speaking · <span className="tabular-nums">{Math.max(0, 30 - seconds)}s</span> to minimum
          </p>
        )}
        <p className="hidden text-[10px] text-ink-faint sm:block">
          <kbd className="rounded bg-surface-3 px-1 py-0.5 font-mono text-[9px]">Space</kbd>
          {" "}to stop
        </p>
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
      <div className="rounded-xl border border-ok/20 bg-ok/5 px-4 py-3">
        <div className="mb-2 flex items-center justify-between">
          <span className="text-xs font-semibold text-ok">✓ Rep complete</span>
          <span className="font-mono text-xs text-ink-faint">{formatTime(seconds)}</span>
        </div>
        <audio src={url} controls className="h-8 w-full" />
      </div>

      <div className="flex gap-2">
        <motion.div className="flex-1" whileHover={{ scale: 1.01 }} whileTap={{ scale: 0.99 }}>
          <Button onClick={onSave} size="sm" className="w-full gap-1.5">
            Analyze Speech →
          </Button>
        </motion.div>
        <Button
          variant="secondary" size="sm" onClick={onDiscard}
          className="gap-1.5 text-ink-subtle hover:border-danger/30 hover:text-danger"
        >
          <Trash2 size={12} />
          Redo
        </Button>
      </div>

      <p className="hidden text-center text-[10px] text-ink-faint sm:block">
        <kbd className="rounded bg-surface-3 px-1 py-0.5 font-mono text-[9px]">Esc</kbd>
        {" "}to discard and redo
      </p>
    </motion.div>
  );
}

// ── Uploading ─────────────────────────────────────────────────────────────────

function UploadingView() {
  return (
    <div className="flex flex-col items-center gap-4 py-8">
      <motion.div
        className="flex h-9 w-9 items-center justify-center rounded-full bg-lav"
        animate={{ rotate: 360 }}
        transition={{ duration: 1.2, repeat: Infinity, ease: "linear" }}
      >
        <RotateCcw size={15} className="text-white" />
      </motion.div>
      <div className="flex flex-col items-center gap-1 text-center">
        <p className="text-sm font-semibold text-ink">Saving your rep…</p>
        <p className="text-xs text-ink-subtle">Analysis starts right after upload</p>
      </div>
    </div>
  );
}

// ── Main ───────────────────────────────────────────────────────────────────────

export default function RecordingStudio({
  recordState,
  recordingSeconds,
  recordObjectUrl,
  recordError,
  level = 0,
  onStartRecording,
  onStopRecording,
  onSaveRecording,
  onDiscardRecording,
}: RecordingStudioProps) {
  const [countdown, setCountdown] = useState<number | null>(null);
  const timerRefs = useRef<ReturnType<typeof setTimeout>[]>([]);
  const onStartRef = useRef(onStartRecording);
  useEffect(() => { onStartRef.current = onStartRecording; });

  const isCountingDown = countdown !== null;

  // Clear pending countdowns on unmount
  useEffect(() => {
    return () => { timerRefs.current.forEach(clearTimeout); };
  }, []);

  const handleStartWithCountdown = useCallback(() => {
    if (recordState !== "idle" && recordState !== "error") return;
    setCountdown(3);
    const t1 = setTimeout(() => setCountdown(2), 1000);
    const t2 = setTimeout(() => setCountdown(1), 2000);
    const t3 = setTimeout(() => {
      setCountdown(null);
      onStartRef.current();
    }, 3000);
    timerRefs.current = [t1, t2, t3];
  }, [recordState]);

  // Keep a ref so keyboard handler always calls the latest version
  const handleStartRef = useRef(handleStartWithCountdown);
  useEffect(() => { handleStartRef.current = handleStartWithCountdown; });

  // Cancel countdown helper
  function cancelCountdown() {
    timerRefs.current.forEach(clearTimeout);
    timerRefs.current = [];
    setCountdown(null);
  }

  // Keyboard shortcuts: Space (start/stop), Esc (cancel/discard)
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      const el = e.target as HTMLElement;
      const tag = el?.tagName?.toUpperCase();
      // Never intercept when user is typing or a button is focused
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || tag === "BUTTON") return;

      if (e.code === "Space") {
        e.preventDefault();
        if (!isCountingDown && (recordState === "idle" || recordState === "error")) {
          handleStartRef.current();
        } else if (recordState === "recording") {
          onStopRecording();
        }
      }

      if (e.code === "Escape") {
        if (isCountingDown) {
          cancelCountdown();
        } else if (recordState === "recorded") {
          onDiscardRecording();
        }
      }
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [isCountingDown, recordState, onStopRecording, onDiscardRecording]);

  return (
    <AnimatePresence mode="wait">
      {isCountingDown ? (
        <motion.div key="countdown" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={T.fast}>
          <CountdownView count={countdown!} />
        </motion.div>
      ) : recordState === "recording" ? (
        <motion.div key="recording" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={T.fast}>
          <RecordingView seconds={recordingSeconds} level={level} onStop={onStopRecording} />
        </motion.div>
      ) : recordState === "recorded" && recordObjectUrl ? (
        <motion.div key="recorded" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={T.fast}>
          <RecordedView url={recordObjectUrl} seconds={recordingSeconds} onSave={onSaveRecording} onDiscard={onDiscardRecording} />
        </motion.div>
      ) : recordState === "uploading" ? (
        <motion.div key="uploading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={T.fast}>
          <UploadingView />
        </motion.div>
      ) : (
        <motion.div key="idle" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={T.fast}>
          <IdleView state={recordState} error={recordError} onStart={handleStartWithCountdown} />
        </motion.div>
      )}
    </AnimatePresence>
  );
}
