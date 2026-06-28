"use client";
import { useState, useEffect, useCallback } from "react";

const DRAFT_PREFIX = "dissio_draft:";
/** Legacy prefix written by the RoundLab brand — migrated on first read. */
const DRAFT_PREFIX_LEGACY = "roundlab_draft:";
const MAX_DRAFT_AGE_MS = 7 * 24 * 60 * 60 * 1000; // 7 days

interface DraftEntry<T> {
  data: T;
  savedAt: number;
}

/**
 * Persist a draft to localStorage and recover it after page refresh.
 *
 * Key is namespaced with DRAFT_PREFIX to avoid collisions.
 * Drafts older than 7 days are auto-expired on read.
 * NEVER store sensitive content (transcripts, audio URLs, evidence text).
 */
export function useLocalDraft<T>(key: string, initial: T) {
  const storageKey = `${DRAFT_PREFIX}${key}`;

  const readDraft = useCallback((): T => {
    try {
      // Try new key first; fall back to legacy key and migrate on first hit
      let raw = localStorage.getItem(storageKey);
      if (!raw) {
        const legacyKey = `${DRAFT_PREFIX_LEGACY}${key}`;
        raw = localStorage.getItem(legacyKey);
        if (raw) {
          localStorage.setItem(storageKey, raw);
          localStorage.removeItem(legacyKey);
        }
      }
      if (!raw) return initial;
      const entry: DraftEntry<T> = JSON.parse(raw);
      if (Date.now() - entry.savedAt > MAX_DRAFT_AGE_MS) {
        localStorage.removeItem(storageKey);
        return initial;
      }
      return entry.data;
    } catch {
      return initial;
    }
  }, [storageKey, key, initial]); // eslint-disable-line react-hooks/exhaustive-deps

  const [draft, setDraft] = useState<T>(initial);

  // Hydrate from localStorage on mount
  useEffect(() => {
    setDraft(readDraft());
  }, [readDraft]);

  const saveDraft = useCallback(
    (value: T) => {
      setDraft(value);
      try {
        const entry: DraftEntry<T> = { data: value, savedAt: Date.now() };
        localStorage.setItem(storageKey, JSON.stringify(entry));
      } catch {
        // localStorage full or unavailable — silent fail
      }
    },
    [storageKey],
  );

  const clearDraft = useCallback(() => {
    setDraft(initial);
    try {
      localStorage.removeItem(storageKey);
    } catch {
      // silent fail
    }
  }, [storageKey, initial]); // eslint-disable-line react-hooks/exhaustive-deps

  return { draft, saveDraft, clearDraft };
}
