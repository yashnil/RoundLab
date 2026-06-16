"use client";

import { useCallback, useState } from "react";
import { createClient } from "@/lib/supabase";
import { apiFetch } from "@/lib/api";
import type { Speech } from "@/types";

export const ALLOWED_AUDIO_EXT = ["mp3", "wav", "m4a", "webm", "ogg", "mp4"];
export const MAX_AUDIO_BYTES = 50 * 1024 * 1024; // 50 MB

export type UploadStatus =
  | "idle"
  | "ready"
  | "uploading"
  | "uploaded"
  | "error";

export type UploadErrorKind =
  | "unsupported-file"
  | "file-too-large"
  | "empty-file"
  | "network"
  | "authentication"
  | "storage"
  | "unknown";

export interface FileValidation {
  ok: boolean;
  message?: string;
  kind?: UploadErrorKind;
}

/** Pure file validation against real application limits. */
export function validateAudioFile(f: File): FileValidation {
  const ext = f.name.split(".").pop()?.toLowerCase() ?? "";
  if (!ALLOWED_AUDIO_EXT.includes(ext)) {
    return { ok: false, message: `Unsupported ".${ext}". Allowed: ${ALLOWED_AUDIO_EXT.join(", ")}.`, kind: "unsupported-file" };
  }
  if (f.size === 0) {
    return { ok: false, message: "That file is empty — pick a real audio file.", kind: "empty-file" };
  }
  if (f.size > MAX_AUDIO_BYTES) {
    return { ok: false, message: `Too large (${(f.size / 1024 / 1024).toFixed(1)} MB). Max 50 MB.`, kind: "file-too-large" };
  }
  return { ok: true };
}

/** Classify an upload exception into a user-facing message + kind. */
export function classifyUploadError(e: unknown): { message: string; kind: UploadErrorKind } {
  const kind = (e as { kind?: UploadErrorKind })?.kind;
  const raw = e instanceof Error ? e.message : "Upload failed.";
  if (kind) return { message: raw, kind };
  const lower = raw.toLowerCase();
  if (lower.includes("401") || lower.includes("unauthor") || lower.includes("jwt") || lower.includes("expired")) {
    return { message: "Your session expired. Sign in again — your file is still selected.", kind: "authentication" };
  }
  if (lower.includes("network") || lower.includes("failed to fetch")) {
    return { message: "Network problem during upload. Check your connection and retry.", kind: "network" };
  }
  return { message: raw, kind: "unknown" };
}

/** Resolve audio duration (seconds) from a Blob/File via an HTMLAudioElement. */
export async function getAudioDuration(file: Blob): Promise<number | null> {
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
      setTimeout(() => { URL.revokeObjectURL(url); resolve(null); }, 3000);
    } catch {
      resolve(null);
    }
  });
}

interface UseSpeechUploadArgs {
  speechId: string;
  userId: string | null;
}

export interface UseSpeechUpload {
  selectedFile: File | null;
  fileError: string;
  uploadError: string;
  status: UploadStatus;
  errorKind: UploadErrorKind | null;
  uploading: boolean;
  selectFile: (file: File | null) => void;
  clearFile: () => void;
  /** Upload the selected file; returns the persisted Speech or null on failure. */
  uploadSelectedFile: () => Promise<Speech | null>;
  /** Shared persistence used by both file upload and recorded-blob save. */
  persistAudio: (data: Blob, ext: string, durationSeconds: number | null) => Promise<Speech>;
}

export function useSpeechUpload({ speechId, userId }: UseSpeechUploadArgs): UseSpeechUpload {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState("");
  const [uploadError, setUploadError] = useState("");
  const [status, setStatus] = useState<UploadStatus>("idle");
  const [errorKind, setErrorKind] = useState<UploadErrorKind | null>(null);

  const selectFile = useCallback((file: File | null) => {
    setUploadError("");
    setErrorKind(null);
    if (!file) {
      setSelectedFile(null);
      setFileError("");
      setStatus("idle");
      return;
    }
    const v = validateAudioFile(file);
    if (!v.ok) {
      setFileError(v.message ?? "Invalid file.");
      setSelectedFile(null);
      setStatus("error");
      return;
    }
    setFileError("");
    setSelectedFile(file);
    setStatus("ready");
  }, []);

  const clearFile = useCallback(() => {
    setSelectedFile(null);
    setFileError("");
    setStatus("idle");
  }, []);

  const persistAudio = useCallback(
    async (data: Blob, ext: string, durationSeconds: number | null): Promise<Speech> => {
      const path = `${userId}/${speechId}/audio.${ext}`;
      const sb = createClient();
      const { error: se } = await sb.storage.from("audio").upload(path, data, {
        upsert: true,
        contentType: data.type || "audio/webm",
      });
      if (se) throw Object.assign(new Error(`Upload failed: ${se.message}`), { kind: "storage" });
      return apiFetch<Speech>(`/speeches/${speechId}?user_id=${userId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ audio_url: path, duration_seconds: durationSeconds ?? undefined }),
      });
    },
    [speechId, userId],
  );

  const uploadSelectedFile = useCallback(async (): Promise<Speech | null> => {
    if (!selectedFile || !userId || status === "uploading") return null;
    setUploadError("");
    setErrorKind(null);
    setStatus("uploading");
    try {
      const ext = selectedFile.name.split(".").pop()!.toLowerCase();
      const durationSeconds = await getAudioDuration(selectedFile);
      const upd = await persistAudio(selectedFile, ext, durationSeconds);
      setSelectedFile(null);
      setStatus("uploaded");
      return upd;
    } catch (e) {
      const { message, kind } = classifyUploadError(e);
      setUploadError(message);
      setErrorKind(kind);
      setStatus("error");
      return null;
    }
  }, [selectedFile, userId, status, persistAudio]);

  return {
    selectedFile,
    fileError,
    uploadError,
    status,
    errorKind,
    uploading: status === "uploading",
    selectFile,
    clearFile,
    uploadSelectedFile,
    persistAudio,
  };
}
