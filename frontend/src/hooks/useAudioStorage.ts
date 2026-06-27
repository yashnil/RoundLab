"use client";
/**
 * useAudioStorage — durable pending-recording storage via IndexedDB.
 *
 * Motivation: localStorage cannot hold Blob objects and loses data after
 * the browser unloads. IndexedDB survives refresh and browser restart (where
 * supported), making it safe for "audio pending upload" state.
 *
 * Contract:
 *  - Store audio until the server confirms receipt (status = "uploaded")
 *  - Retry safely after reconnect (idempotent upload ID prevents double-send)
 *  - Auto-expire entries older than MAX_AGE_MS to reclaim storage
 *  - Expose pending/uploading/failed/recovered states to the UI
 *  - Handle QuotaExceededError gracefully (surface error, keep oldest clean)
 *  - Never store transcripts or sensitive metadata unnecessarily
 */

import { useState, useCallback, useRef } from "react";

const DB_NAME = "roundlab_audio";
const STORE_NAME = "pending_recordings";
const DB_VERSION = 1;
const MAX_AGE_MS = 7 * 24 * 60 * 60 * 1000; // 7 days

export type AudioStatus =
  | "pending"
  | "uploading"
  | "uploaded"
  | "failed"
  | "recovered"
  | "quota_error";

export interface PendingRecording {
  /** Stable ID chosen by the caller — used as the dedup key. */
  uploadId: string;
  blob: Blob;
  mimeType: string;
  /** ISO timestamp — used for expiry. */
  createdAt: string;
  status: AudioStatus;
  /** Number of upload attempts so far. */
  attempts: number;
}

// --------------------------------------------------------------------------
// IndexedDB helpers (lazy-open, singleton per tab)
// --------------------------------------------------------------------------

let _db: IDBDatabase | null = null;

function openDB(): Promise<IDBDatabase> {
  if (_db) return Promise.resolve(_db);
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = (e) => {
      const db = (e.target as IDBOpenDBRequest).result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        const store = db.createObjectStore(STORE_NAME, { keyPath: "uploadId" });
        store.createIndex("by_status", "status", { unique: false });
        store.createIndex("by_created", "createdAt", { unique: false });
      }
    };
    req.onsuccess = (e) => {
      _db = (e.target as IDBOpenDBRequest).result;
      resolve(_db);
    };
    req.onerror = () => reject(req.error);
  });
}

function idbPut(db: IDBDatabase, record: PendingRecording): Promise<void> {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readwrite");
    const store = tx.objectStore(STORE_NAME);
    const req = store.put(record);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
  });
}

function idbGet(
  db: IDBDatabase,
  uploadId: string,
): Promise<PendingRecording | undefined> {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readonly");
    const store = tx.objectStore(STORE_NAME);
    const req = store.get(uploadId);
    req.onsuccess = () => resolve(req.result as PendingRecording | undefined);
    req.onerror = () => reject(req.error);
  });
}

function idbDelete(db: IDBDatabase, uploadId: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readwrite");
    const store = tx.objectStore(STORE_NAME);
    const req = store.delete(uploadId);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
  });
}

function idbGetAll(db: IDBDatabase): Promise<PendingRecording[]> {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readonly");
    const store = tx.objectStore(STORE_NAME);
    const req = store.getAll();
    req.onsuccess = () => resolve((req.result as PendingRecording[]) ?? []);
    req.onerror = () => reject(req.error);
  });
}

// --------------------------------------------------------------------------
// Expiry sweep — removes entries older than MAX_AGE_MS
// --------------------------------------------------------------------------

async function sweepExpired(): Promise<void> {
  try {
    const db = await openDB();
    const all = await idbGetAll(db);
    const cutoff = Date.now() - MAX_AGE_MS;
    for (const rec of all) {
      if (new Date(rec.createdAt).getTime() < cutoff) {
        await idbDelete(db, rec.uploadId);
      }
    }
  } catch {
    // Non-fatal — storage sweep failure should not break the UI
  }
}

// --------------------------------------------------------------------------
// Hook
// --------------------------------------------------------------------------

interface UseAudioStorageReturn {
  status: AudioStatus | null;
  /** Save a new recording blob to IndexedDB. Returns false on quota error. */
  savePending: (uploadId: string, blob: Blob, mimeType: string) => Promise<boolean>;
  /** Mark a recording as uploading (prevents duplicate sends). */
  markUploading: (uploadId: string) => Promise<void>;
  /** Mark a recording as successfully uploaded; removes local copy. */
  markUploaded: (uploadId: string) => Promise<void>;
  /** Mark a recording as failed (will be retried on next reconnect). */
  markFailed: (uploadId: string) => Promise<void>;
  /** Retrieve a pending recording blob (e.g. to retry upload). */
  getBlob: (uploadId: string) => Promise<Blob | null>;
  /** Return all non-uploaded recordings (for reconnect retry). */
  getPending: () => Promise<PendingRecording[]>;
}

export function useAudioStorage(): UseAudioStorageReturn {
  const [status, setStatus] = useState<AudioStatus | null>(null);
  // Tracks ongoing upload IDs to prevent duplicate in-flight sends
  const inFlight = useRef<Set<string>>(new Set());

  const savePending = useCallback(
    async (uploadId: string, blob: Blob, mimeType: string): Promise<boolean> => {
      try {
        await sweepExpired();
        const db = await openDB();
        const record: PendingRecording = {
          uploadId,
          blob,
          mimeType,
          createdAt: new Date().toISOString(),
          status: "pending",
          attempts: 0,
        };
        await idbPut(db, record);
        setStatus("pending");
        return true;
      } catch (err) {
        const isQuota =
          err instanceof DOMException &&
          (err.name === "QuotaExceededError" ||
            err.name === "NS_ERROR_DOM_QUOTA_REACHED");
        setStatus(isQuota ? "quota_error" : "failed");
        return false;
      }
    },
    [],
  );

  const markUploading = useCallback(async (uploadId: string): Promise<void> => {
    if (inFlight.current.has(uploadId)) return; // already in flight
    try {
      const db = await openDB();
      const existing = await idbGet(db, uploadId);
      if (!existing) return;
      inFlight.current.add(uploadId);
      await idbPut(db, {
        ...existing,
        status: "uploading",
        attempts: existing.attempts + 1,
      });
      setStatus("uploading");
    } catch {
      // Non-fatal
    }
  }, []);

  const markUploaded = useCallback(async (uploadId: string): Promise<void> => {
    try {
      const db = await openDB();
      await idbDelete(db, uploadId);
      inFlight.current.delete(uploadId);
      setStatus("uploaded");
    } catch {
      // Non-fatal
    }
  }, []);

  const markFailed = useCallback(async (uploadId: string): Promise<void> => {
    inFlight.current.delete(uploadId);
    try {
      const db = await openDB();
      const existing = await idbGet(db, uploadId);
      if (!existing) return;
      await idbPut(db, { ...existing, status: "failed" });
      setStatus("failed");
    } catch {
      // Non-fatal
    }
  }, []);

  const getBlob = useCallback(
    async (uploadId: string): Promise<Blob | null> => {
      try {
        const db = await openDB();
        const rec = await idbGet(db, uploadId);
        return rec?.blob ?? null;
      } catch {
        return null;
      }
    },
    [],
  );

  const getPending = useCallback(async (): Promise<PendingRecording[]> => {
    try {
      const db = await openDB();
      const all = await idbGetAll(db);
      return all.filter(
        (r) => r.status === "pending" || r.status === "failed",
      );
    } catch {
      return [];
    }
  }, []);

  return {
    status,
    savePending,
    markUploading,
    markUploaded,
    markFailed,
    getBlob,
    getPending,
  };
}
