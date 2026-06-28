/**
 * swHelpers.js — audio upload-retry helpers for the Dissio service worker.
 *
 * UMD bundle: exports via CommonJS in Node.js/Jest; attaches to the SW
 * global scope when loaded via importScripts().
 *
 * Every function that touches IndexedDB accepts an optional `idbFactory`
 * parameter so unit tests can inject fake-indexeddb instead of relying on
 * the browser global.
 *
 * Backward-compat guarantee:
 *  - Recordings in roundlab_audio are uploaded and then removed from that
 *    store once the server confirms receipt.  This prevents duplicate uploads
 *    across sync events.
 *  - The roundlab_audio database itself is never deleted.
 */

/* eslint-disable no-var */
(function (root, factory) {
  if (typeof module !== "undefined" && typeof module.exports !== "undefined") {
    // Node.js / Jest
    module.exports = factory();
  } else {
    // Service Worker global scope (importScripts)
    var helpers = factory();
    Object.keys(helpers).forEach(function (key) {
      root[key] = helpers[key];
    });
  }
})(typeof self !== "undefined" ? self : typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  var SW_DB_NAME = "dissio_audio";
  var SW_DB_NAME_LEGACY = "roundlab_audio"; // intentional: backward-compat source
  var SW_STORE_NAME = "pending_recordings";
  var SW_UPLOAD_ENDPOINT = "/api/speech/upload";

  // --------------------------------------------------------------------------
  // openAudioDB
  // --------------------------------------------------------------------------

  /**
   * Open an audio IDB database by name.
   *
   * Returns null when:
   *  - The database has never been created (onupgradeneeded fires with
   *    oldVersion === 0 → isNew → we close immediately and return null).
   *  - The open request errors.
   *
   * This prevents the helper from creating a new empty database in the course
   * of checking for one that doesn't exist yet.
   *
   * @param {string} name
   * @param {IDBFactory} [idbFactory] - defaults to global indexedDB
   * @returns {Promise<IDBDatabase|null>}
   */
  function openAudioDB(name, idbFactory) {
    var idb = idbFactory || (typeof indexedDB !== "undefined" ? indexedDB : null);
    if (!idb) return Promise.resolve(null);
    return new Promise(function (resolve) {
      try {
        var isNew = false;
        var req = idb.open(name, 1);
        req.onupgradeneeded = function (e) {
          isNew = e.oldVersion === 0;
        };
        req.onsuccess = function () {
          var db = req.result;
          if (isNew || !db.objectStoreNames.contains(SW_STORE_NAME)) {
            db.close();
            resolve(null);
            return;
          }
          resolve(db);
        };
        req.onerror = function () { resolve(null); };
      } catch (_) {
        resolve(null);
      }
    });
  }

  // --------------------------------------------------------------------------
  // getAllFromDB / getPendingFromDB
  // --------------------------------------------------------------------------

  /**
   * Return ALL records from the store (any status).
   * Used to build an accurate dedup set — records in any state (uploading,
   * uploaded, etc.) in dissio_audio must block re-upload from the legacy DB.
   *
   * @param {IDBDatabase|null} db
   * @returns {Promise<Object[]>}
   */
  function getAllFromDB(db) {
    if (!db) return Promise.resolve([]);
    return new Promise(function (resolve) {
      try {
        var tx = db.transaction(SW_STORE_NAME, "readonly");
        var req = tx.objectStore(SW_STORE_NAME).getAll();
        req.onsuccess = function () { resolve(req.result || []); };
        req.onerror = function () { resolve([]); };
      } catch (_) {
        resolve([]);
      }
    });
  }

  // --------------------------------------------------------------------------
  // deleteRecord / markRecordFailed
  // --------------------------------------------------------------------------

  /**
   * Delete a single record by uploadId from the given database.
   *
   * @param {IDBDatabase} db
   * @param {string} uploadId
   * @returns {Promise<void>}
   */
  function deleteRecord(db, uploadId) {
    return new Promise(function (resolve, reject) {
      try {
        var tx = db.transaction(SW_STORE_NAME, "readwrite");
        var req = tx.objectStore(SW_STORE_NAME).delete(uploadId);
        req.onsuccess = function () { resolve(); };
        req.onerror = function () { reject(req.error); };
      } catch (err) {
        reject(err);
      }
    });
  }

  /**
   * Mark a record as failed and increment its attempt counter.
   *
   * @param {IDBDatabase} db
   * @param {Object} record
   * @returns {Promise<void>}
   */
  function markRecordFailed(db, record) {
    return new Promise(function (resolve, reject) {
      try {
        var updated = Object.assign({}, record, {
          status: "failed",
          attempts: (record.attempts || 0) + 1,
        });
        var tx = db.transaction(SW_STORE_NAME, "readwrite");
        var req = tx.objectStore(SW_STORE_NAME).put(updated);
        req.onsuccess = function () { resolve(); };
        req.onerror = function () { reject(req.error); };
      } catch (err) {
        reject(err);
      }
    });
  }

  // --------------------------------------------------------------------------
  // retryPendingUploads
  // --------------------------------------------------------------------------

  /**
   * Core background-sync logic: upload all pending/failed recordings from
   * both dissio_audio and the legacy roundlab_audio database, then clean up.
   *
   * Deduplication rules:
   *  1. Build a set of ALL uploadIds present in dissio_audio (any status).
   *     A legacy record whose uploadId is already in dissio_audio is skipped —
   *     even if the main-DB record is "uploading" or "uploaded".
   *  2. Per-record, track which store(s) own it (inMain / inLegacy).
   *
   * After a successful upload:
   *  - Delete the record from every store that contains this uploadId.
   *  - This permanently removes it from roundlab_audio so the next sync
   *    event cannot re-upload it.
   *
   * After an HTTP error:
   *  - Preserve the record and mark it "failed" in every relevant store.
   *
   * After a network exception:
   *  - Preserve all records unchanged for a later retry.
   *
   * Neither database is ever deleted.
   *
   * @param {IDBFactory} [idbFactory] - injectable for tests; defaults to global indexedDB
   * @param {function} [fetchFn] - injectable for tests; defaults to global fetch
   * @returns {Promise<void>}
   */
  async function retryPendingUploads(idbFactory, fetchFn) {
    var idb = idbFactory || (typeof indexedDB !== "undefined" ? indexedDB : null);
    var doFetch = fetchFn || (typeof fetch !== "undefined" ? fetch : null);
    if (!idb || !doFetch) return;

    var db = await openAudioDB(SW_DB_NAME, idb);
    var legacyDb = await openAudioDB(SW_DB_NAME_LEGACY, idb);

    // ALL records from dissio_audio — any status — so we can accurately block
    // legacy uploads when the same uploadId is already tracked in the main DB.
    var allMainRecords = await getAllFromDB(db);
    var mainIds = new Set(allMainRecords.map(function (r) { return r.uploadId; }));

    // Only pending/failed from the main DB need uploading.
    var mainPending = allMainRecords.filter(function (r) {
      return r.status === "pending" || r.status === "failed";
    });

    // ALL records from legacy — any status — to build the cross-cleanup set.
    var allLegacyRecords = await getAllFromDB(legacyDb);
    var legacyIds = new Set(allLegacyRecords.map(function (r) { return r.uploadId; }));

    // Only upload legacy records whose uploadId is absent from dissio_audio entirely.
    var legacyPending = allLegacyRecords.filter(function (r) {
      return (r.status === "pending" || r.status === "failed") && !mainIds.has(r.uploadId);
    });

    // Annotate each candidate with which store(s) own it.
    // inLegacy is true for main records too when the legacy DB also has a copy
    // (e.g. migration copied the record to dissio_audio but legacy wasn't cleaned).
    var toUpload = mainPending.map(function (r) {
      return { record: r, inMain: true, inLegacy: legacyIds.has(r.uploadId) };
    }).concat(legacyPending.map(function (r) {
      return { record: r, inMain: false, inLegacy: true };
    }));

    for (var i = 0; i < toUpload.length; i++) {
      var item = toUpload[i];
      var record = item.record;
      var inMain = item.inMain;
      var inLegacy = item.inLegacy;

      try {
        var form = new FormData();
        form.append(
          "file",
          record.blob,
          record.uploadId + "." + (record.mimeType.split("/")[1] || "webm")
        );
        form.append("upload_id", record.uploadId);

        var res = await doFetch(SW_UPLOAD_ENDPOINT, { method: "POST", body: form });

        if (res.ok) {
          // Delete from every store that holds this uploadId.
          // Prevents re-upload on the next background-sync event.
          if (db && inMain) await deleteRecord(db, record.uploadId);
          if (legacyDb && inLegacy) await deleteRecord(legacyDb, record.uploadId);
        } else {
          // HTTP error: preserve and mark failed in every relevant store.
          if (db && inMain) await markRecordFailed(db, record);
          if (legacyDb && inLegacy) await markRecordFailed(legacyDb, record);
        }
      } catch (_) {
        // Network exception — preserve all records for a later retry.
      }
    }

    if (db) db.close();
    if (legacyDb) legacyDb.close();
  }

  return {
    SW_DB_NAME: SW_DB_NAME,
    SW_DB_NAME_LEGACY: SW_DB_NAME_LEGACY,
    SW_STORE_NAME: SW_STORE_NAME,
    SW_UPLOAD_ENDPOINT: SW_UPLOAD_ENDPOINT,
    openAudioDB: openAudioDB,
    getAllFromDB: getAllFromDB,
    deleteRecord: deleteRecord,
    markRecordFailed: markRecordFailed,
    retryPendingUploads: retryPendingUploads,
  };
});
