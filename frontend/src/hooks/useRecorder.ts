"use client";

import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import {
  recorderReducer,
  initialRecorderState,
  hasUnsavedRecording,
  type RecorderState,
} from "@/lib/recorder";
import { computeRmsLevel, smoothLevel } from "@/lib/audioLevel";

const PREFERRED_MIME = ["audio/webm", "audio/mp4", "audio/ogg"];

function pickMimeType(): string | undefined {
  if (typeof MediaRecorder === "undefined") return undefined;
  return PREFERRED_MIME.find((t) => MediaRecorder.isTypeSupported?.(t));
}

export interface UseRecorder {
  state: RecorderState;
  /** Smoothed 0..1 input level for a meter (updates each animation frame). */
  level: number;
  requestPermission: () => Promise<void>;
  start: () => void;
  stop: () => void;
  play: () => void;
  stopPlayback: () => void;
  /** Discard the current take and return to idle (caller confirms first). */
  reset: () => void;
  /** Run an uploader for the captured blob, driving upload state transitions. */
  upload: (uploader: (blob: Blob) => Promise<void>) => Promise<boolean>;
  hasUnsaved: boolean;
}

export function useRecorder(): UseRecorder {
  const [state, dispatch] = useReducer(recorderReducer, initialRecorderState);
  const [level, setLevel] = useState(0);

  // Latest state, readable from stable callbacks (e.g. the upload closure).
  const stateRef = useRef(state);
  useEffect(() => {
    stateRef.current = state;
  });

  const streamRef = useRef<MediaStream | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const rafRef = useRef<number | null>(null);
  const tickRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startedAtRef = useRef<number>(0);
  const urlRef = useRef<string | null>(null);
  const audioElRef = useRef<HTMLAudioElement | null>(null);
  const levelRef = useRef(0);

  const stopLevelLoop = useCallback(() => {
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
  }, []);

  const stopTicks = useCallback(() => {
    if (tickRef.current !== null) {
      clearInterval(tickRef.current);
      tickRef.current = null;
    }
  }, []);

  const teardownStream = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    analyserRef.current = null;
    if (audioCtxRef.current && audioCtxRef.current.state !== "closed") {
      audioCtxRef.current.close().catch(() => {});
    }
    audioCtxRef.current = null;
  }, []);

  const revokeUrl = useCallback(() => {
    if (urlRef.current) {
      URL.revokeObjectURL(urlRef.current);
      urlRef.current = null;
    }
  }, []);

  const requestPermission = useCallback(async () => {
    if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
      dispatch({ type: "UNSUPPORTED", message: "Recording isn’t supported in this browser. Try uploading an audio file instead." });
      return;
    }
    dispatch({ type: "REQUEST_PERMISSION" });
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      try {
        const Ctx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
        const ctx = new Ctx();
        const source = ctx.createMediaStreamSource(stream);
        const analyser = ctx.createAnalyser();
        analyser.fftSize = 1024;
        source.connect(analyser);
        audioCtxRef.current = ctx;
        analyserRef.current = analyser;
      } catch {
        // Level metering is optional; recording still works without it.
      }
      dispatch({ type: "PERMISSION_GRANTED" });
    } catch {
      dispatch({ type: "PERMISSION_DENIED", message: "We couldn’t access your microphone. Check your browser’s mic permission and try again." });
    }
  }, []);

  const start = useCallback(() => {
    const stream = streamRef.current;
    if (!stream) return;
    try {
      const mime = pickMimeType();
      const recorder = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined);
      chunksRef.current = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: mime || "audio/webm" });
        revokeUrl();
        const url = URL.createObjectURL(blob);
        urlRef.current = url;
        const durationMs = Date.now() - startedAtRef.current;
        dispatch({ type: "RECORDING_READY", blob, url, durationMs });
      };
      recorderRef.current = recorder;
      recorder.start();
      startedAtRef.current = Date.now();
      dispatch({ type: "START_RECORDING" });

      tickRef.current = setInterval(() => {
        dispatch({ type: "TICK", ms: Date.now() - startedAtRef.current });
      }, 250);

      const analyser = analyserRef.current;
      if (analyser) {
        const buf = new Uint8Array(analyser.fftSize);
        const loop = () => {
          analyser.getByteTimeDomainData(buf);
          const next = smoothLevel(levelRef.current, computeRmsLevel(buf));
          levelRef.current = next;
          setLevel(next);
          rafRef.current = requestAnimationFrame(loop);
        };
        rafRef.current = requestAnimationFrame(loop);
      }
    } catch {
      dispatch({ type: "FAIL", message: "Recording failed to start. Try reloading or uploading a file." });
    }
  }, [revokeUrl]);

  const stop = useCallback(() => {
    dispatch({ type: "STOP_RECORDING" });
    stopTicks();
    stopLevelLoop();
    levelRef.current = 0;
    setLevel(0);
    try {
      recorderRef.current?.stop();
    } catch {
      /* already stopped */
    }
  }, [stopTicks, stopLevelLoop]);

  const play = useCallback(() => {
    if (!urlRef.current) return;
    const el = audioElRef.current ?? new Audio(urlRef.current);
    audioElRef.current = el;
    el.onended = () => dispatch({ type: "STOP_PLAYBACK" });
    el.play().then(
      () => dispatch({ type: "START_PLAYBACK" }),
      () => dispatch({ type: "STOP_PLAYBACK" }),
    );
  }, []);

  const stopPlayback = useCallback(() => {
    audioElRef.current?.pause();
    dispatch({ type: "STOP_PLAYBACK" });
  }, []);

  const reset = useCallback(() => {
    stopTicks();
    stopLevelLoop();
    audioElRef.current?.pause();
    audioElRef.current = null;
    revokeUrl();
    teardownStream();
    recorderRef.current = null;
    chunksRef.current = [];
    levelRef.current = 0;
    setLevel(0);
    dispatch({ type: "RESET" });
  }, [stopTicks, stopLevelLoop, revokeUrl, teardownStream]);

  const upload = useCallback(
    async (uploader: (blob: Blob) => Promise<void>) => {
      const blob = stateRef.current.blob;
      if (!blob) return false;
      dispatch({ type: "START_UPLOAD" });
      try {
        await uploader(blob);
        dispatch({ type: "UPLOAD_SUCCESS" });
        return true;
      } catch (e) {
        dispatch({
          type: "UPLOAD_FAILURE",
          message: e instanceof Error ? e.message : "Upload failed. Your recording is safe — try again.",
        });
        return false;
      }
    },
    [],
  );

  // Cleanup on unmount only.
  useEffect(() => {
    return () => {
      stopTicks();
      stopLevelLoop();
      audioElRef.current?.pause();
      revokeUrl();
      teardownStream();
    };
  }, [stopTicks, stopLevelLoop, revokeUrl, teardownStream]);

  return {
    state,
    level,
    requestPermission,
    start,
    stop,
    play,
    stopPlayback,
    reset,
    upload,
    hasUnsaved: hasUnsavedRecording(state),
  };
}
