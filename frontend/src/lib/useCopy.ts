"use client";

import { useState, useCallback } from "react";

/**
 * Provides copy-to-clipboard with inline success state.
 * Returns [copy fn, copied boolean].
 * `copied` resets to false after 2 seconds.
 */
export function useCopy(resetMs = 2000): [(text: string) => Promise<void>, boolean] {
  const [copied, setCopied] = useState(false);

  const copy = useCallback(async (text: string) => {
    if (!navigator?.clipboard) return;
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), resetMs);
    } catch {}
  }, [resetMs]);

  return [copy, copied];
}
