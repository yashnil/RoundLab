/**
 * Service-worker audio recovery tests.
 *
 * Directly exercises the real production functions exported from
 * public/swHelpers.js via CommonJS require().  A bug in the production
 * implementation will cause these tests to fail.
 *
 * Coverage:
 *  1. Legacy-only recording uploads once; not re-uploaded on a later sync
 *  2. Duplicate uploadId in both databases uploads exactly once
 *  3. Successful upload removes the record from both stores
 *  4. Failed HTTP response preserves the record and increments attempts
 *  5. Network exception preserves the record unchanged
 *  6. Missing legacy database is harmless (no crash, no spurious uploads)
 */

import { IDBFactory } from "fake-indexeddb";

// Import the real production helpers directly from swHelpers.js.
// allowJs:true + esModuleInterop:true in tsconfig allow this.
// eslint-disable-next-line @typescript-eslint/no-require-imports
const {
  SW_DB_NAME,
  SW_DB_NAME_LEGACY,
  SW_STORE_NAME,
  retryPendingUploads,
  getAllFromDB,
  openAudioDB,
} = require("../../public/swHelpers.js");

// ── Test fixtures ─────────────────────────────────────────────────────────────

function makeBlob(text = "audio"): Blob {
  return new Blob([text], { type: "audio/webm" });
}

function makeRecord(uploadId: string, overrides: Record<string, unknown> = {}): Record<string, unknown> {
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

/**
 * Create a DB with the pending_recordings store and seed it with records.
 * Returns the db name for reference.
 */
async function seedDB(
  factory: IDBFactory,
  dbName: string,
  records: Record<string, unknown>[],
): Promise<void> {
  await new Promise<void>((resolve, reject) => {
    const req = factory.open(dbName, 1);
    req.onupgradeneeded = (e) => {
      const db = (e.target as IDBOpenDBRequest).result;
      if (!db.objectStoreNames.contains(SW_STORE_NAME)) {
        const store = db.createObjectStore(SW_STORE_NAME, { keyPath: "uploadId" });
        store.createIndex("by_status", "status", { unique: false });
        store.createIndex("by_created", "createdAt", { unique: false });
      }
    };
    req.onsuccess = async (e) => {
      const db = (e.target as IDBOpenDBRequest).result;
      for (const record of records) {
        await new Promise<void>((res, rej) => {
          const tx = db.transaction(SW_STORE_NAME, "readwrite");
          const r = tx.objectStore(SW_STORE_NAME).put(record);
          r.onsuccess = () => res();
          r.onerror = () => rej(r.error);
        });
      }
      db.close();
      resolve();
    };
    req.onerror = () => reject(req.error);
  });
}

/**
 * Read all records from a DB (returns [] if the DB does not exist).
 */
async function readAll(factory: IDBFactory, dbName: string): Promise<Record<string, unknown>[]> {
  const db: IDBDatabase | null = await openAudioDB(dbName, factory);
  if (!db) return [];
  const records = await getAllFromDB(db);
  db.close();
  return records as Record<string, unknown>[];
}

/** A mock fetch that always returns HTTP 200 OK. */
function okFetch(): Promise<{ ok: boolean; status: number }> {
  return Promise.resolve({ ok: true, status: 200 });
}

/** A mock fetch that always returns HTTP 500. */
function errFetch(): Promise<{ ok: boolean; status: number }> {
  return Promise.resolve({ ok: false, status: 500 });
}

/** A mock fetch that always throws (network offline). */
function netFetch(): Promise<never> {
  return Promise.reject(new TypeError("Failed to fetch"));
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("SW audio recovery — production swHelpers.js", () => {
  let factory: IDBFactory;

  beforeEach(() => {
    factory = new IDBFactory();
  });

  // ── 1. Legacy-only upload: not retried on next sync ────────────────────────

  it("1. legacy-only: record uploads once and disappears from roundlab_audio on the next sync", async () => {
    await seedDB(factory, SW_DB_NAME_LEGACY, [makeRecord("leg-001")]);

    const calls: string[] = [];
    const trackingFetch = (url: string, opts: RequestInit) => {
      calls.push((opts?.body as FormData)?.get?.("upload_id") as string ?? "unknown");
      return Promise.resolve({ ok: true, status: 200 });
    };

    // First sync: should upload and delete from legacy.
    await retryPendingUploads(factory, trackingFetch);
    expect(calls).toEqual(["leg-001"]);

    // Second sync: legacy DB now empty — nothing to upload.
    calls.length = 0;
    await retryPendingUploads(factory, trackingFetch);
    expect(calls).toHaveLength(0);

    // Confirm the record is gone from legacy.
    const legacyRecords = await readAll(factory, SW_DB_NAME_LEGACY);
    expect(legacyRecords.map((r) => r.uploadId)).not.toContain("leg-001");
  });

  // ── 2. Duplicate uploadId in both DBs: uploaded exactly once ──────────────

  it("2. dedup: uploadId present in both DBs is uploaded exactly once", async () => {
    // Same uploadId in both databases (e.g. migration ran but legacy not cleaned).
    await seedDB(factory, SW_DB_NAME, [makeRecord("dup-001")]);
    await seedDB(factory, SW_DB_NAME_LEGACY, [makeRecord("dup-001")]);

    const calls: string[] = [];
    const trackingFetch = (_url: string, opts: RequestInit) => {
      calls.push((opts?.body as FormData)?.get?.("upload_id") as string ?? "unknown");
      return Promise.resolve({ ok: true, status: 200 });
    };

    await retryPendingUploads(factory, trackingFetch);

    // Must have been called exactly once.
    expect(calls).toHaveLength(1);
    expect(calls[0]).toBe("dup-001");
  });

  // ── 3. Successful upload removes record from both stores ───────────────────

  it("3. cleanup: successful upload removes the record from dissio_audio AND roundlab_audio", async () => {
    // Simulate a migrated record: in both main DB and legacy.
    await seedDB(factory, SW_DB_NAME, [makeRecord("both-001")]);
    await seedDB(factory, SW_DB_NAME_LEGACY, [makeRecord("both-001")]);

    await retryPendingUploads(factory, okFetch);

    const mainRecords = await readAll(factory, SW_DB_NAME);
    const legacyRecords = await readAll(factory, SW_DB_NAME_LEGACY);

    expect(mainRecords.map((r) => r.uploadId)).not.toContain("both-001");
    expect(legacyRecords.map((r) => r.uploadId)).not.toContain("both-001");
  });

  // ── 4. Failed HTTP response: preserves record, increments attempts ─────────

  it("4. http-error: preserves the record and increments attempts in the relevant store", async () => {
    await seedDB(factory, SW_DB_NAME, [makeRecord("fail-001", { attempts: 1 })]);

    await retryPendingUploads(factory, errFetch);

    const mainRecords = await readAll(factory, SW_DB_NAME);
    const r = mainRecords.find((x) => x.uploadId === "fail-001");
    expect(r).toBeDefined();
    expect(r!.status).toBe("failed");
    expect(r!.attempts).toBe(2); // incremented
  });

  // ── 4b. Failed HTTP response for legacy-only record ───────────────────────

  it("4b. http-error: legacy-only record is preserved and marked failed", async () => {
    await seedDB(factory, SW_DB_NAME_LEGACY, [makeRecord("fail-leg-001", { attempts: 0 })]);

    await retryPendingUploads(factory, errFetch);

    const legacyRecords = await readAll(factory, SW_DB_NAME_LEGACY);
    const r = legacyRecords.find((x) => x.uploadId === "fail-leg-001");
    expect(r).toBeDefined();
    expect(r!.status).toBe("failed");
    expect(r!.attempts).toBe(1);
  });

  // ── 5. Network exception: preserves all records ───────────────────────────

  it("5. network-error: network exception leaves all records unchanged", async () => {
    await seedDB(factory, SW_DB_NAME, [makeRecord("net-001", { status: "pending", attempts: 0 })]);
    await seedDB(factory, SW_DB_NAME_LEGACY, [makeRecord("net-leg-001", { status: "pending", attempts: 0 })]);

    // Should not throw even though fetch rejects.
    await expect(retryPendingUploads(factory, netFetch)).resolves.toBeUndefined();

    const mainRecords = await readAll(factory, SW_DB_NAME);
    const legacyRecords = await readAll(factory, SW_DB_NAME_LEGACY);

    const m = mainRecords.find((r) => r.uploadId === "net-001");
    expect(m!.status).toBe("pending");
    expect(m!.attempts).toBe(0);

    const l = legacyRecords.find((r) => r.uploadId === "net-leg-001");
    expect(l!.status).toBe("pending");
    expect(l!.attempts).toBe(0);
  });

  // ── 6. Missing legacy database ────────────────────────────────────────────

  it("6. missing legacy: retryPendingUploads() is harmless when roundlab_audio does not exist", async () => {
    // Only the main DB exists.
    await seedDB(factory, SW_DB_NAME, [makeRecord("main-001")]);
    // Do NOT seed roundlab_audio — it has never been created in this factory.

    const calls: string[] = [];
    const trackingFetch = (_url: string, opts: RequestInit) => {
      calls.push((opts?.body as FormData)?.get?.("upload_id") as string ?? "unknown");
      return Promise.resolve({ ok: true, status: 200 });
    };

    // Must not throw.
    await expect(retryPendingUploads(factory, trackingFetch)).resolves.toBeUndefined();

    // Main record was still uploaded.
    expect(calls).toEqual(["main-001"]);

    // Main DB cleaned up.
    const mainRecords = await readAll(factory, SW_DB_NAME);
    expect(mainRecords.map((r) => r.uploadId)).not.toContain("main-001");
  });
});
