"use client";

import { useSyncExternalStore } from "react";
import {
  subscribeTheme,
  getThemeSnapshot,
  getThemeServerSnapshot,
  toggleTheme as runToggle,
  type Theme,
} from "@/lib/theme";

/**
 * Reactive theme hook. Hydration-safe via useSyncExternalStore — no
 * setState-in-effect, and stays in sync across tabs.
 */
export function useTheme(): { theme: Theme; toggle: () => void } {
  const theme = useSyncExternalStore(
    subscribeTheme,
    getThemeSnapshot,
    getThemeServerSnapshot,
  );
  return { theme, toggle: () => runToggle(theme) };
}
