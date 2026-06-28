/**
 * IndexedDB tests for useAudioStorage (Pass 21.4 + hardening).
 *
 * Uses fake-indexeddb to run IndexedDB operations in Jest (Node.js).
 *
 * Sections 1-7: test the DB layer in isolation using local re-implementations
 * of the IDB helpers (avoids importing the React-hook module for basic
 * schema/CRUD verification).
 *
 * Section 8: LEGACY MIGRATION — imports and directly exercises the real
 * production functions exported from useAudioStorage.ts so that these tests
 * WILL FAIL if the production implementation breaks.
 */

import { IDBFactory, IDBKeyRange } from "fake-indexeddb";

// ── Section 8 imports: real production functions ─────────────────────────────
import {
  DB_NAME,
  DB_NAME_LEGACY,
  STORE_NAME,
  DB_VERSION,
  getLegacyPendingRecordings,
  migrateLegacyRecordings,
  idbPut as prodIdbPut,
  idbGet as prodIdbGet,
  idbGetAll as prodIdbGetAll,
  _resetForTests,
  _setMigrationOverride,
  _openDB,
} from "@/hooks/useAudioStorage";

// ── DB constants (local mirror for sections 1-7) ──────────────────────────────
const LOCAL_DB_NAME = "dissio_audio";
const LOCAL_STORE_NAME = "pending_recordings";
const LOCAL_DB_VERSION = 1;
const MAX_AGE_MS = 7 * 24 * 60 * 60 * 1000; // 7 days

type AudioStatus =
  | "pending"
  | "uploading"
  | "uploaded"
  | "failed"
  | "recovered"
  | "quota_error";

interface PendingRecording {
  uploadId: string;
  blob: Blob;
  mimeType: string;
  createdAt: string;
  status: AudioStatus;
  attempts: number;
}

// ── Local DB helpers (sections 1-7 only) ─────────────────────────────────────

let _idbFactory: IDBFactory;
let _db: IDBDatabase | null = null;

function openDB(): Promise<IDBDatabase> {
  if (_db) return Promise.resolve(_db);
  return new Promise((resolve, reject) => {
    const req = _idbFactory.open(LOCAL_DB_NAME, LOCAL_DB_VERSION);
    req.onupgradeneeded = (e) => {
      const db = (e.target as IDBOpenDBRequest).result;
      if (!db.objectStoreNames.contains(LOCAL_STORE_NAME)) {
        const store = db.createObjectStore(LOCAL_STORE_NAME, { keyPath: "uploadId" });
        store.createIndex("by_status", "status", { unique: false });
        store.createIndex("by_created", "createdAt", { unique: false });
      }
    };
    req.onsuccess = (e) => {
      _db = (e.target as IDBOpenDBRequest).result;
      resolve(_db!);
    };
    req.onerror = () => reject(req.error);
  });
}

function idbPut(db: IDBDatabase, record: PendingRecording): Promise<void> {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(LOCAL_STORE_NAME, "readwrite");
    const store = tx.objectStore(LOCAL_STORE_NAME);
    store.put(record);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

function idbGet(db: IDBDatabase, uploadId: string): Promise<PendingRecording | undefined> {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(LOCAL_STORE_NAME, "readonly");
    const req = tx.objectStore(LOCAL_STORE_NAME).get(uploadId);
    req.onsuccess = () => resolve(req.result as PendingRecording | undefined);
    req.onerror = () => reject(req.error);
  });
}

function idbDelete(db: IDBDatabase, uploadId: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(LOCAL_STORE_NAME, "readwrite");
    tx.objectStore(LOCAL_STORE_NAME).delete(uploadId);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

function idbGetAll(db: IDBDatabase): Promise<PendingRecording[]> {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(LOCAL_STORE_NAME, "readonly");
    const req = tx.objectStore(LOCAL_STORE_NAME).getAll();
    req.onsuccess = () => resolve(req.result as PendingRecording[]);
    req.onerror = () => reject(req.error);
  });
}

function sweepExpired(db: IDBDatabase): Promise<number> {
  const cutoff = new Date(Date.now() - MAX_AGE_MS).toISOString();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(LOCAL_STORE_NAME, "readwrite");
    const store = tx.objectStore(LOCAL_STORE_NAME);
    const idx = store.index("by_created");
    const range = IDBKeyRange.upperBound(cutoff);
    let deleted = 0;
    const req = idx.openCursor(range);
    req.onsuccess = () => {
      const cursor = req.result as IDBCursorWithValue | null;
      if (cursor) {
        cursor.delete();
        deleted++;
        cursor.continue();
      }
    };
    tx.oncomplete = () => resolve(deleted);
    tx.onerror = () => reject(tx.error);
  });
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function makeBlob(text = "audio data"): Blob {
  return new Blob([text], { type: "audio/webm" });
}

function makeRecord(uploadId: string, overrides?: Partial<PendingRecording>): PendingRecording {
  return {
    uploadId,
    blob: makeBlob(),
    mimeType: "audio/webm",
    createdAt: new Date().toISOString(),
    status: "pending",
    attempts: 0,
    ...overrides,
  };
}

// Each test (sections 1-7) gets a fresh IDBFactory.
beforeEach(() => {
  _idbFactory = new IDBFactory();
  _db = null;
});

// ═══════════════════════════════════════════════════════════════════════════
// 1. Database initialization
// ═══════════════════════════════════════════════════════════════════════════

describe("IndexedDB initialization", () => {
  it("opens and creates the correct object store", async () => {
    const db = await openDB();
    expect(db.objectStoreNames.contains(LOCAL_STORE_NAME)).toBe(true);
    db.close();
  });

  it("creates by_status index", async () => {
    const db = await openDB();
    const tx = db.transaction(LOCAL_STORE_NAME, "readonly");
    const store = tx.objectStore(LOCAL_STORE_NAME);
    expect(store.indexNames.contains("by_status")).toBe(true);
    db.close();
  });

  it("creates by_created index", async () => {
    const db = await openDB();
    const tx = db.transaction(LOCAL_STORE_NAME, "readonly");
    const store = tx.objectStore(LOCAL_STORE_NAME);
    expect(store.indexNames.contains("by_created")).toBe(true);
    db.close();
  });

  it("uses uploadId as keyPath", async () => {
    const db = await openDB();
    const tx = db.transaction(LOCAL_STORE_NAME, "readonly");
    expect(tx.objectStore(LOCAL_STORE_NAME).keyPath).toBe("uploadId");
    db.close();
  });

  it("returns the same DB instance on second open (singleton)", async () => {
    const db1 = await openDB();
    const db2 = await openDB();
    expect(db1).toBe(db2);
    db1.close();
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 2. savePending / getBlob
// ═══════════════════════════════════════════════════════════════════════════

describe("savePending — stores and retrieves Blob", () => {
  it("stores a record and retrieves it by uploadId", async () => {
    const db = await openDB();
    const record = makeRecord("upload-001");
    await idbPut(db, record);

    const stored = await idbGet(db, "upload-001");
    expect(stored).toBeDefined();
    expect(stored!.uploadId).toBe("upload-001");
    expect(stored!.status).toBe("pending");
    db.close();
  });

  it("retrieves the Blob content that was stored", async () => {
    const db = await openDB();
    const blob = makeBlob("speech-content-abc");
    const record = makeRecord("upload-002", { blob });
    await idbPut(db, record);

    const stored = await idbGet(db, "upload-002");
    // fake-indexeddb may serialize/deserialize Blobs; check size and type
    expect(stored!.blob.size).toBe(blob.size);
    expect(stored!.blob.type).toBe(blob.type);
    db.close();
  });

  it("returns undefined for unknown uploadId", async () => {
    const db = await openDB();
    const result = await idbGet(db, "non-existent-id");
    expect(result).toBeUndefined();
    db.close();
  });

  it("stores mimeType field correctly", async () => {
    const db = await openDB();
    const record = makeRecord("upload-003", { mimeType: "audio/ogg" });
    await idbPut(db, record);

    const stored = await idbGet(db, "upload-003");
    expect(stored!.mimeType).toBe("audio/ogg");
    db.close();
  });

  it("PUT is idempotent — second save overwrites, does not duplicate", async () => {
    const db = await openDB();
    await idbPut(db, makeRecord("upload-004", { status: "pending" }));
    await idbPut(db, makeRecord("upload-004", { status: "uploading", attempts: 1 }));

    const all = await idbGetAll(db);
    const matching = all.filter((r) => r.uploadId === "upload-004");
    expect(matching).toHaveLength(1);
    expect(matching[0].status).toBe("uploading");
    db.close();
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 3. Status transitions
// ═══════════════════════════════════════════════════════════════════════════

describe("Status transitions", () => {
  it("markUploading: sets status to uploading and increments attempts", async () => {
    const db = await openDB();
    await idbPut(db, makeRecord("upl-001", { status: "pending", attempts: 0 }));

    const existing = await idbGet(db, "upl-001");
    await idbPut(db, { ...existing!, status: "uploading", attempts: existing!.attempts + 1 });

    const updated = await idbGet(db, "upl-001");
    expect(updated!.status).toBe("uploading");
    expect(updated!.attempts).toBe(1);
    db.close();
  });

  it("markFailed: sets status to failed without removing the record", async () => {
    const db = await openDB();
    await idbPut(db, makeRecord("upl-002", { status: "uploading" }));

    const existing = await idbGet(db, "upl-002");
    await idbPut(db, { ...existing!, status: "failed" });

    const updated = await idbGet(db, "upl-002");
    expect(updated!.status).toBe("failed");
    db.close();
  });

  it("markUploaded: removes the record from IDB (clean-up on success)", async () => {
    const db = await openDB();
    await idbPut(db, makeRecord("upl-003", { status: "uploading" }));
    await idbDelete(db, "upl-003");

    const stored = await idbGet(db, "upl-003");
    expect(stored).toBeUndefined();
    db.close();
  });

  it("multiple retries increment attempts correctly", async () => {
    const db = await openDB();
    const record = makeRecord("upl-004", { status: "pending", attempts: 0 });
    await idbPut(db, record);

    for (let i = 1; i <= 3; i++) {
      const existing = (await idbGet(db, "upl-004"))!;
      await idbPut(db, { ...existing, status: "uploading", attempts: existing.attempts + 1 });
      const fail = (await idbGet(db, "upl-004"))!;
      await idbPut(db, { ...fail, status: "failed" });
    }

    const final = await idbGet(db, "upl-004");
    expect(final!.attempts).toBe(3);
    expect(final!.status).toBe("failed");
    db.close();
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 4. getPending — only pending/failed
// ═══════════════════════════════════════════════════════════════════════════

describe("getPending — filters by recoverable status", () => {
  it("returns only pending and failed rows (not uploading/uploaded)", async () => {
    const db = await openDB();
    await idbPut(db, makeRecord("r-pending",   { status: "pending" }));
    await idbPut(db, makeRecord("r-uploading", { status: "uploading" }));
    await idbPut(db, makeRecord("r-failed",    { status: "failed" }));
    await idbPut(db, makeRecord("r-uploaded",  { status: "uploaded" }));

    const all = await idbGetAll(db);
    const recoverable = all.filter((r) => r.status === "pending" || r.status === "failed");

    expect(recoverable.map((r) => r.uploadId).sort()).toEqual(["r-failed", "r-pending"]);
    db.close();
  });

  it("returns empty array when nothing is pending or failed", async () => {
    const db = await openDB();
    await idbPut(db, makeRecord("u-uploaded", { status: "uploaded" }));

    const all = await idbGetAll(db);
    const recoverable = all.filter((r) => r.status === "pending" || r.status === "failed");
    expect(recoverable).toHaveLength(0);
    db.close();
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 5. sweepExpired — 7-day TTL
// ═══════════════════════════════════════════════════════════════════════════

describe("sweepExpired — removes records older than MAX_AGE_MS", () => {
  it("does not remove records created recently", async () => {
    const db = await openDB();
    await idbPut(db, makeRecord("fresh-001", { createdAt: new Date().toISOString() }));

    const deleted = await sweepExpired(db);
    expect(deleted).toBe(0);

    const still = await idbGet(db, "fresh-001");
    expect(still).toBeDefined();
    db.close();
  });

  it("removes records older than 7 days", async () => {
    const db = await openDB();
    const oldDate = new Date(Date.now() - MAX_AGE_MS - 1000).toISOString();
    await idbPut(db, makeRecord("old-001", { createdAt: oldDate }));

    const deleted = await sweepExpired(db);
    expect(deleted).toBe(1);

    const gone = await idbGet(db, "old-001");
    expect(gone).toBeUndefined();
    db.close();
  });

  it("removes expired records while keeping recent ones", async () => {
    const db = await openDB();
    const oldDate = new Date(Date.now() - MAX_AGE_MS - 1000).toISOString();
    await idbPut(db, makeRecord("keep-001", { createdAt: new Date().toISOString() }));
    await idbPut(db, makeRecord("expire-001", { createdAt: oldDate }));
    await idbPut(db, makeRecord("expire-002", { createdAt: oldDate }));

    const deleted = await sweepExpired(db);
    expect(deleted).toBe(2);

    expect(await idbGet(db, "keep-001")).toBeDefined();
    expect(await idbGet(db, "expire-001")).toBeUndefined();
    expect(await idbGet(db, "expire-002")).toBeUndefined();
    db.close();
  });

  it("boundary: records exactly at MAX_AGE_MS are removed", async () => {
    const db = await openDB();
    const boundary = new Date(Date.now() - MAX_AGE_MS).toISOString();
    await idbPut(db, makeRecord("boundary-001", { createdAt: boundary }));

    const deleted = await sweepExpired(db);
    expect(deleted).toBe(1);
    db.close();
  });

  it("MAX_AGE_MS equals exactly 7 days in milliseconds", () => {
    expect(MAX_AGE_MS).toBe(604800000); // 7 * 24 * 60 * 60 * 1000
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 6. Multiple records
// ═══════════════════════════════════════════════════════════════════════════

describe("Multiple concurrent records", () => {
  it("stores and retrieves multiple distinct uploadIds", async () => {
    const db = await openDB();
    const ids = ["multi-001", "multi-002", "multi-003"];
    await Promise.all(ids.map((id) => idbPut(db, makeRecord(id))));

    const all = await idbGetAll(db);
    const storedIds = all.map((r) => r.uploadId);
    for (const id of ids) {
      expect(storedIds).toContain(id);
    }
    db.close();
  });

  it("deleting one record does not affect others", async () => {
    const db = await openDB();
    await idbPut(db, makeRecord("keep-a"));
    await idbPut(db, makeRecord("delete-b"));
    await idbPut(db, makeRecord("keep-c"));

    await idbDelete(db, "delete-b");

    expect(await idbGet(db, "keep-a")).toBeDefined();
    expect(await idbGet(db, "delete-b")).toBeUndefined();
    expect(await idbGet(db, "keep-c")).toBeDefined();
    db.close();
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 7. AudioStatus type coverage
// ═══════════════════════════════════════════════════════════════════════════

describe("AudioStatus type", () => {
  const ALL_STATUSES: AudioStatus[] = [
    "pending",
    "uploading",
    "uploaded",
    "failed",
    "recovered",
    "quota_error",
  ];

  it("has exactly 6 valid states", () => {
    expect(ALL_STATUSES).toHaveLength(6);
  });

  it("can store and retrieve each status", async () => {
    const db = await openDB();
    for (const status of ALL_STATUSES) {
      const id = `status-${status}`;
      await idbPut(db, makeRecord(id, { status }));
      const stored = await idbGet(db, id);
      expect(stored!.status).toBe(status);
    }
    db.close();
  });

  it("pending and failed are the 'recoverable' states", () => {
    const recoverable = ALL_STATUSES.filter((s) => s === "pending" || s === "failed");
    expect(recoverable).toEqual(["pending", "failed"]);
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 8. Legacy migration — roundlab_audio → dissio_audio
//
// These tests import and directly exercise the REAL production functions from
// useAudioStorage.ts.  A bug in the production code will cause these tests to
// fail — unlike local reimplementations, which would pass regardless.
//
// Seven scenarios:
//  1. Normal new recordings go into dissio_audio
//  2. Pending/failed records in roundlab_audio are detected
//  3. Legacy records are migrated into dissio_audio
//  4. Running migration twice does not duplicate records
//  5. Migration succeeds (returns []) when the legacy DB does not exist
//  6. openDB() / _openDB() awaits migration before returning the DB
//  7. Migration is retried after a simulated failure
// ═══════════════════════════════════════════════════════════════════════════

describe("Legacy migration — roundlab_audio → dissio_audio (production functions)", () => {
  // Each test in this describe gets fresh module singletons + a fresh main factory.
  // Tests that need a legacy factory create one inline.
  beforeEach(() => {
    _resetForTests(new IDBFactory());
  });

  // ── Local seeding helpers ─────────────────────────────────────────────────
  // These helpers open a DB in an explicit factory and seed it.
  // They do NOT duplicate production code — they are test fixtures.

  function openDBInFactory(name: string, factory: IDBFactory): Promise<IDBDatabase> {
    return new Promise((resolve, reject) => {
      const req = factory.open(name, DB_VERSION);
      req.onupgradeneeded = (e) => {
        const db = (e.target as IDBOpenDBRequest).result;
        if (!db.objectStoreNames.contains(STORE_NAME)) {
          const store = db.createObjectStore(STORE_NAME, { keyPath: "uploadId" });
          store.createIndex("by_status", "status", { unique: false });
          store.createIndex("by_created", "createdAt", { unique: false });
        }
      };
      req.onsuccess = (e) => resolve((e.target as IDBOpenDBRequest).result);
      req.onerror = () => reject(req.error);
    });
  }

  // Seed the legacy roundlab_audio DB inside the given factory.
  async function seedLegacyDB(
    factory: IDBFactory,
    records: PendingRecording[],
  ): Promise<void> {
    const db = await openDBInFactory(DB_NAME_LEGACY, factory);
    for (const r of records) await prodIdbPut(db, r);
    db.close();
  }

  // Open the main dissio_audio DB inside the given factory (no migration).
  function openMainDB(factory: IDBFactory): Promise<IDBDatabase> {
    return openDBInFactory(DB_NAME, factory);
  }

  // ── 1. Normal use of dissio_audio ─────────────────────────────────────────

  it("1. normal: DB_NAME constant is dissio_audio and records land there", async () => {
    expect(DB_NAME).toBe("dissio_audio");
    expect(DB_NAME_LEGACY).toBe("roundlab_audio");

    const mainFactory = new IDBFactory();
    const db = await openMainDB(mainFactory);
    await prodIdbPut(db, makeRecord("normal-001"));
    const stored = await prodIdbGet(db, "normal-001");
    expect(stored?.uploadId).toBe("normal-001");
    db.close();
  });

  // ── 2. Detection of legacy records ────────────────────────────────────────

  it("2. detection: getLegacyPendingRecordings() finds pending/failed, excludes uploaded", async () => {
    const legacyFactory = new IDBFactory();
    await seedLegacyDB(legacyFactory, [
      makeRecord("leg-001", { status: "pending" }),
      makeRecord("leg-002", { status: "failed" }),
      makeRecord("leg-003", { status: "uploaded" }), // must be excluded
    ]);

    // Call the REAL production function with an injected factory.
    const found = await getLegacyPendingRecordings(legacyFactory);
    const ids = found.map((r) => r.uploadId).sort();
    expect(ids).toEqual(["leg-001", "leg-002"]);
    expect(ids).not.toContain("leg-003");
  });

  // ── 3. Migration into the current database ────────────────────────────────

  it("3. migration: migrateLegacyRecordings() copies records into dissio_audio", async () => {
    const mainFactory = new IDBFactory();
    const legacyFactory = new IDBFactory();

    await seedLegacyDB(legacyFactory, [
      makeRecord("mig-001", { status: "pending" }),
      makeRecord("mig-002", { status: "failed" }),
    ]);

    const targetDb = await openMainDB(mainFactory);

    // Call the REAL production function.
    const count = await migrateLegacyRecordings(targetDb, legacyFactory);
    expect(count).toBe(2);

    // Verify via the REAL idbGet.
    const r1 = await prodIdbGet(targetDb, "mig-001");
    const r2 = await prodIdbGet(targetDb, "mig-002");
    expect(r1).toBeDefined();
    expect(r1!.status).toBe("pending");
    expect(r2).toBeDefined();
    expect(r2!.status).toBe("failed");

    targetDb.close();
  });

  // ── 4. Duplicate prevention ────────────────────────────────────────────────

  it("4. dedup: running migrateLegacyRecordings() twice does not duplicate records", async () => {
    const mainFactory = new IDBFactory();
    const legacyFactory = new IDBFactory();

    await seedLegacyDB(legacyFactory, [
      makeRecord("dup-001", { status: "pending" }),
    ]);

    const targetDb = await openMainDB(mainFactory);

    const firstRun = await migrateLegacyRecordings(targetDb, legacyFactory);
    const secondRun = await migrateLegacyRecordings(targetDb, legacyFactory);

    expect(firstRun).toBe(1);
    expect(secondRun).toBe(0); // skipped — uploadId already present

    const all = await prodIdbGetAll(targetDb);
    expect(all.filter((r) => r.uploadId === "dup-001")).toHaveLength(1);
    targetDb.close();
  });

  // ── 5. Missing legacy database ────────────────────────────────────────────

  it("5. resilience: getLegacyPendingRecordings() returns [] when legacy DB does not exist", async () => {
    // Fresh factory with no databases → onupgradeneeded fires with oldVersion=0 → isNew=true → []
    const emptyFactory = new IDBFactory();
    const found = await getLegacyPendingRecordings(emptyFactory);
    expect(found).toEqual([]);
  });

  it("5b. resilience: migrateLegacyRecordings() returns 0 when legacy DB does not exist", async () => {
    const mainFactory = new IDBFactory();
    const emptyFactory = new IDBFactory();

    const targetDb = await openMainDB(mainFactory);
    const count = await migrateLegacyRecordings(targetDb, emptyFactory);
    expect(count).toBe(0);

    const all = await prodIdbGetAll(targetDb);
    expect(all).toHaveLength(0);
    targetDb.close();
  });

  // ── 6. Migration completes before first recovery read ─────────────────────

  it("6. timing: _openDB() resolves only after migration; records visible on first read", async () => {
    const mainFactory = new IDBFactory();
    const legacyFactory = new IDBFactory();

    await seedLegacyDB(legacyFactory, [
      makeRecord("timing-001", { status: "pending" }),
      makeRecord("timing-002", { status: "failed" }),
    ]);

    // Inject both factories so openDB() uses them internally.
    _resetForTests(mainFactory, legacyFactory);

    // _openDB() awaits migration before resolving.
    const db = await _openDB();

    // The migrated records must already be present — no second await needed.
    const all = await prodIdbGetAll(db);
    const ids = all.map((r) => r.uploadId).sort();
    expect(ids).toContain("timing-001");
    expect(ids).toContain("timing-002");
    db.close();
  });

  // ── 7. Retry behavior after simulated migration failure ────────────────────

  it("7. retry: _openDB() retries migration on the next call after a failure", async () => {
    const mainFactory = new IDBFactory();
    const legacyFactory = new IDBFactory();

    await seedLegacyDB(legacyFactory, [
      makeRecord("retry-001", { status: "pending" }),
    ]);

    _resetForTests(mainFactory, legacyFactory);

    // First call: override causes migration to throw.
    _setMigrationOverride(async () => {
      throw new Error("Simulated migration failure");
    });

    const db1 = await _openDB();

    // DB is returned (non-fatal path) but records were NOT migrated.
    const afterFail = await prodIdbGetAll(db1);
    expect(afterFail.map((r) => r.uploadId)).not.toContain("retry-001");

    // Restore real migration.
    _setMigrationOverride(null);

    // Second call: _readyPromise was cleared on failure → retry.
    const db2 = await _openDB();
    expect(db2).toBe(db1); // same underlying IDB connection

    const afterRetry = await prodIdbGetAll(db2);
    expect(afterRetry.map((r) => r.uploadId)).toContain("retry-001");
    db2.close();
  });
});
