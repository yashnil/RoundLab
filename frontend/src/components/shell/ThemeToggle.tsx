"use client";

import { Sun, Moon } from "lucide-react";
import { useTheme } from "@/hooks/useTheme";
import {
  TooltipRoot,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip";

interface ThemeToggleProps {
  className?: string;
  /** Show a text label beside the icon (used in expanded sidebar / menus). */
  withLabel?: boolean;
}

export default function ThemeToggle({ className, withLabel }: ThemeToggleProps) {
  const { theme, toggle } = useTheme();
  const isDark = theme === "dark";
  const nextLabel = isDark ? "Switch to light mode" : "Switch to dark mode";
  const Icon = isDark ? Sun : Moon;

  const button = (
    <button
      type="button"
      onClick={toggle}
      aria-label={nextLabel}
      className={
        className ??
        "flex h-8 w-8 items-center justify-center rounded-md text-ink-subtle transition-colors hover:bg-surface-2 hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50"
      }
    >
      <Icon size={16} aria-hidden="true" />
      {withLabel && (
        <span className="ml-2 text-sm">{isDark ? "Light mode" : "Dark mode"}</span>
      )}
    </button>
  );

  if (withLabel) return button;

  return (
    <TooltipRoot>
      <TooltipTrigger asChild>{button}</TooltipTrigger>
      <TooltipContent side="bottom">{nextLabel}</TooltipContent>
    </TooltipRoot>
  );
}
