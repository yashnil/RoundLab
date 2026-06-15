"use client";

import { useCallback, useSyncExternalStore } from "react";

/**
 * A boolean flag persisted to localStorage, reactive across the tab and other
 * tabs. Hydration-safe (server snapshot = fallback) and avoids
 * setState-in-effect.
 */
export function usePersistentToggle(
  key: string,
  fallback = false,
): readonly [boolean, (next: boolean) => void] {
  const eventName = `roundlab:toggle:${key}`;

  const subscribe = useCallback(
    (cb: () => void) => {
      if (typeof window === "undefined") return () => {};
      window.addEventListener(eventName, cb);
      window.addEventListener("storage", cb);
      return () => {
        window.removeEventListener(eventName, cb);
        window.removeEventListener("storage", cb);
      };
    },
    [eventName],
  );

  const getSnapshot = useCallback(() => {
    if (typeof window === "undefined") return fallback;
    const v = window.localStorage.getItem(key);
    return v === null ? fallback : v === "1";
  }, [key, fallback]);

  const getServerSnapshot = useCallback(() => fallback, [fallback]);

  const value = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  const setValue = useCallback(
    (next: boolean) => {
      if (typeof window === "undefined") return;
      window.localStorage.setItem(key, next ? "1" : "0");
      window.dispatchEvent(new CustomEvent(eventName));
    },
    [key, eventName],
  );

  return [value, setValue] as const;
}
