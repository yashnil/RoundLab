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
 *
 * Backward compatibility (roundlab_audio → dissio_audio):
 *  - openDB() awaits migration before resolving — no race between first
 *    getPending() call and legacy records being copied.
 *  - Concurrent callers share one in-flight migration promise (no duplicates).
 *  - On migration failure _readyPromise is cleared so the next caller retries.
 *  - Records already present by uploadId are never copied twice (idempotent).
 *  - roundlab_audio is never deleted automatically.
 */

import { useState, useCallback, useRef } from "react";

export const DB_NAME = "dissio_audio";
/** Legacy database written by the RoundLab brand — source for one-time migration. */
export const DB_NAME_LEGACY = "roundlab_audio";
export const STORE_NAME = "pending_recordings";
export const DB_VERSION = 1;
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
// Module-level singletons
// --------------------------------------------------------------------------

let _db: IDBDatabase | null = null;

/** Caches the raw IDB open promise (schema creation only, no migration). */
let _dbOpenPromise: Promise<IDBDatabase> | null = null;

/**
 * Shared promise that resolves only after the DB is open AND migration from
 * the legacy roundlab_audio database has completed.  Cleared on failure so
 * the next caller retries the migration.
 */
let _readyPromise: Promise<IDBDatabase> | null = null;

// Test-injection slots (null in production builds)
let _testMainFactory: IDBFactory | null = null;
let _testLegacyFactory: IDBFactory | null = null;
type MigrationFn = (db: IDBDatabase, factory?: IDBFactory) => Promise<number>;
let _migrationOverride: MigrationFn | null = null;

// --------------------------------------------------------------------------
// Test-only exports
// --------------------------------------------------------------------------

/**
 * Reset all module singletons and inject custom IDB factories.
 * Call this in beforeEach to get clean, isolated state per test.
 * @internal
 */
export function _resetForTests(
  mainFactory: IDBFactory,
  legacyFactory?: IDBFactory,
): void {
  _db = null;
  _dbOpenPromise = null;
  _readyPromise = null;
  _testMainFactory = mainFactory;
  _testLegacyFactory = legacyFactory ?? null;
  _migrationOverride = null;
}

/**
 * Override the migration function called inside openDB().
 * Pass null to restore the real migrateLegacyRecordings().
 * @internal
 */
export function _setMigrationOverride(fn: MigrationFn | null): void {
  _migrationOverride = fn;
}

// --------------------------------------------------------------------------
// IndexedDB helpers (lazy-open, singleton per tab)
// --------------------------------------------------------------------------

function _getMainFactory(): IDBFactory {
  if (_testMainFactory) return _testMainFactory;
  if (typeof indexedDB !== "undefined") return indexedDB;
  throw new Error("IndexedDB is not available in this environment");
}

/** Opens the raw IDB connection and creates the schema. Cached after first open. */
function _openRawDB(): Promise<IDBDatabase> {
  if (_dbOpenPromise) return _dbOpenPromise;
  _dbOpenPromise = new Promise<IDBDatabase>((resolve, reject) => {
    const req = _getMainFactory().open(DB_NAME, DB_VERSION);
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
  return _dbOpenPromise;
}

/**
 * Open dissio_audio and await migration from roundlab_audio before resolving.
 *
 * Guarantees:
 *  - The first getPending()/getBlob()/savePending() call sees migrated records.
 *  - Concurrent callers share one migration attempt (no duplicate migrations).
 *  - On migration failure _readyPromise is cleared so the next caller retries.
 *  - Migration failure is non-fatal — the raw DB is always returned.
 */
function openDB(): Promise<IDBDatabase> {
  if (_readyPromise) return _readyPromise;
  _readyPromise = (async () => {
    const db = await _openRawDB();
    const migrate = _migrationOverride ?? migrateLegacyRecordings;
    try {
      await migrate(db, _testLegacyFactory ?? undefined);
    } catch {
      // Non-fatal: clear so the next openDB() call can retry the migration.
      _readyPromise = null;
    }
    return db;
  })();
  return _readyPromise;
}

/** Exposed for testing: the internal openDB() with migration gate. @internal */
export const _openDB = openDB;

export function idbPut(db: IDBDatabase, record: PendingRecording): Promise<void> {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readwrite");
    const store = tx.objectStore(STORE_NAME);
    const req = store.put(record);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
  });
}

export function idbGet(
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

export function idbDelete(db: IDBDatabase, uploadId: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readwrite");
    const store = tx.objectStore(STORE_NAME);
    const req = store.delete(uploadId);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
  });
}

export function idbGetAll(db: IDBDatabase): Promise<PendingRecording[]> {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readonly");
    const store = tx.objectStore(STORE_NAME);
    const req = store.getAll();
    req.onsuccess = () => resolve((req.result as PendingRecording[]) ?? []);
    req.onerror = () => reject(req.error);
  });
}

// --------------------------------------------------------------------------
// Legacy migration helpers (exported for unit-test injection)
// --------------------------------------------------------------------------

/**
 * Read pending/failed recordings from the legacy roundlab_audio IndexedDB.
 * Returns [] when the database does not exist or cannot be read — never throws.
 *
 * Detection: if onupgradeneeded fires with oldVersion === 0, the DB was
 * just created (didn't exist before) — we treat it as empty and return [].
 *
 * @param factory  Explicit IDBFactory override (used by tests and the SW).
 *                 Falls back to _testLegacyFactory, then the global indexedDB.
 */
export async function getLegacyPendingRecordings(
  factory?: IDBFactory,
): Promise<PendingRecording[]> {
  const idb =
    factory ??
    _testLegacyFactory ??
    (typeof indexedDB !== "undefined" ? indexedDB : null);
  if (!idb) return [];
  return new Promise((resolve) => {
    try {
      let isNew = false;
      const req = idb.open(DB_NAME_LEGACY, DB_VERSION);
      req.onupgradeneeded = (e) => {
        // oldVersion === 0 → DB did not exist before this open call.
        isNew = (e as IDBVersionChangeEvent).oldVersion === 0;
      };
      req.onsuccess = (e) => {
        const db = (e.target as IDBOpenDBRequest).result;
        if (isNew || !db.objectStoreNames.contains(STORE_NAME)) {
          db.close();
          resolve([]);
          return;
        }
        const tx = db.transaction(STORE_NAME, "readonly");
        const getReq = tx.objectStore(STORE_NAME).getAll();
        getReq.onsuccess = () => {
          const all = (getReq.result as PendingRecording[]) ?? [];
          db.close();
          resolve(all.filter((r) => r.status === "pending" || r.status === "failed"));
        };
        getReq.onerror = () => {
          db.close();
          resolve([]);
        };
      };
      req.onerror = () => resolve([]);
    } catch {
      resolve([]);
    }
  });
}

/**
 * Copy pending/failed recordings from roundlab_audio into targetDb.
 *
 * - Records already present by uploadId are skipped (idempotent).
 * - Preserves original status and record data.
 * - roundlab_audio is never modified or deleted.
 * - Returns the number of records newly copied.
 *
 * @param targetDb      The already-open dissio_audio IDBDatabase.
 * @param legacyFactory Explicit IDBFactory override (used by tests and the SW).
 */
export async function migrateLegacyRecordings(
  targetDb: IDBDatabase,
  legacyFactory?: IDBFactory,
): Promise<number> {
  const legacy = await getLegacyPendingRecordings(legacyFactory);
  if (legacy.length === 0) return 0;
  let migrated = 0;
  for (const record of legacy) {
    const existing = await idbGet(targetDb, record.uploadId);
    if (!existing) {
      await idbPut(targetDb, record);
      migrated++;
    }
  }
  return migrated;
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
