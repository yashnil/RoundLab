/**
 * Theme helpers — single source of truth for Dissio's light/dark theme.
 *
 * The theme class (`dark` | `light`) lives on <html>. It is first applied by an
 * inline script in app/layout.tsx (pre-hydration, prevents flash), then managed
 * here. Persisted under localStorage key `dissio-theme`.
 */

export type Theme = "dark" | "light";

export const THEME_STORAGE_KEY = "dissio-theme";
/** Legacy key written by the RoundLab brand — migrated on first read. */
const THEME_STORAGE_KEY_LEGACY = "roundlab-theme";

export function getStoredTheme(): Theme {
  if (typeof window === "undefined") return "dark";
  const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
  if (stored !== null) return stored === "light" ? "light" : "dark";
  // One-time migration from the old key
  const legacy = window.localStorage.getItem(THEME_STORAGE_KEY_LEGACY);
  if (legacy !== null) {
    window.localStorage.setItem(THEME_STORAGE_KEY, legacy);
    window.localStorage.removeItem(THEME_STORAGE_KEY_LEGACY);
    return legacy === "light" ? "light" : "dark";
  }
  return "dark";
}

export function applyTheme(theme: Theme): void {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  root.classList.remove("dark", "light");
  root.classList.add(theme);
}

const THEME_EVENT = "dissio:theme-change";

export function setTheme(theme: Theme): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  applyTheme(theme);
  window.dispatchEvent(new CustomEvent(THEME_EVENT));
}

export function toggleTheme(current: Theme): Theme {
  const next: Theme = current === "dark" ? "light" : "dark";
  setTheme(next);
  return next;
}

// ── useSyncExternalStore adapters (hydration-safe, no setState-in-effect) ────

/** Subscribe to theme changes (this tab + other tabs). */
export function subscribeTheme(callback: () => void): () => void {
  if (typeof window === "undefined") return () => {};
  window.addEventListener(THEME_EVENT, callback);
  window.addEventListener("storage", callback);
  return () => {
    window.removeEventListener(THEME_EVENT, callback);
    window.removeEventListener("storage", callback);
  };
}

/** Snapshot on the client. */
export function getThemeSnapshot(): Theme {
  return getStoredTheme();
}

/** Snapshot during SSR / first paint — matches the inline boot script default. */
export function getThemeServerSnapshot(): Theme {
  return "dark";
}
