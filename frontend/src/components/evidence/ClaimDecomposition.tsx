"use client";

import { useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  ArrowRight,
  BarChart2,
  GitBranch,
  Loader2,
  RotateCcw,
  Shield,
  TrendingUp,
  Zap,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { decomposeClaim, type BranchKey, type ResearchBranch } from "@/lib/claimDecomposition";
import type { EvidenceRole } from "@/types";

// ── Branch icons ──────────────────────────────────────────────────────────────

const BRANCH_ICON: Record<BranchKey, LucideIcon> = {
  causal_warrant: Zap,
  empirical_support: BarChart2,
  impact: TrendingUp,
  counterargument: Shield,
  limitation: AlertCircle,
};

// ── Props ─────────────────────────────────────────────────────────────────────

interface ClaimDecompositionProps {
  claim: string;
  onSearchBranch: (query: string, role: EvidenceRole) => void;
  /** Called when "Run all" is clicked — should aggregate results from all angles. */
  onRunAll?: () => void;
  /** True while any search is in-flight. Used to show/clear loading state. */
  isSearching?: boolean;
  disabled?: boolean;
}

/**
 * Research plan: breaks the claim into angles (causal warrant, empirical
 * support, impact, counterargument, limitation) as compact, fully-clickable
 * rows. Each row carries its own loading indicator. "Run all" in the header
 * triggers an aggregated multi-angle search.
 *
 * Clicking a row immediately routes through the same candidate-search function
 * used by the main workflow — no second confirmation required.
 */
export default function ClaimDecomposition({
  claim,
  onSearchBranch,
  onRunAll,
  isSearching = false,
  disabled,
}: ClaimDecompositionProps) {
  const branches = decomposeClaim(claim);
  const [activeBranchKey, setActiveBranchKey] = useState<BranchKey | null>(null);
  const [runningAll, setRunningAll] = useState(false);
  const prevSearchingRef = useRef(isSearching);

  // Clear internal loading state when the parent finishes searching.
  useEffect(() => {
    if (prevSearchingRef.current && !isSearching) {
      setActiveBranchKey(null);
      setRunningAll(false);
    }
    prevSearchingRef.current = isSearching;
  }, [isSearching]);

  if (branches.length === 0) return null;

  const anyLoading = isSearching && (activeBranchKey !== null || runningAll);
  const globalDisabled = disabled || anyLoading;

  function handleBranchClick(b: ResearchBranch) {
    if (globalDisabled) return;
    setActiveBranchKey(b.key);
    onSearchBranch(b.query, b.role);
  }

  function handleRunAll() {
    if (globalDisabled) return;
    setRunningAll(true);
    onRunAll?.();
  }

  return (
    <div className="rounded-xl border border-hairline bg-surface-1 overflow-hidden">

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between px-3.5 py-2 border-b border-hairline">
        <div className="flex items-center gap-1.5">
          <GitBranch size={12} className="text-lav shrink-0" aria-hidden />
          <span className="text-[12px] font-semibold text-ink">Research plan</span>
        </div>

        {onRunAll && (
          <button
            type="button"
            disabled={disabled || isSearching}
            onClick={handleRunAll}
            aria-label="Run all research angles and merge results"
            className={cn(
              "inline-flex items-center gap-1 rounded px-2 py-0.5",
              "text-[11px] font-medium text-ink-subtle whitespace-nowrap",
              "hover:text-ink hover:bg-surface-2",
              "disabled:opacity-40 disabled:cursor-not-allowed",
              "transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-lav/40",
            )}
          >
            {runningAll && isSearching ? (
              <Loader2 size={10} className="animate-spin shrink-0" aria-hidden />
            ) : (
              <RotateCcw size={10} className="shrink-0" aria-hidden />
            )}
            Run all
          </button>
        )}
      </div>

      {/* ── Angle rows ─────────────────────────────────────────────────────── */}
      <ul role="list" className="divide-y divide-hairline">
        {branches.map((b) => {
          const Icon = BRANCH_ICON[b.key];
          const isActive = activeBranchKey === b.key && isSearching;

          return (
            <li key={b.key}>
              <button
                type="button"
                disabled={globalDisabled}
                onClick={() => handleBranchClick(b)}
                aria-busy={isActive}
                aria-label={`Search ${b.label} angle`}
                className={cn(
                  "w-full flex items-center gap-3 px-3.5 py-2.5 text-left",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-lav/40",
                  "transition-colors",
                  isActive
                    ? "bg-lav/5 cursor-default"
                    : globalDisabled
                    ? "opacity-40 cursor-not-allowed"
                    : "hover:bg-surface-2 cursor-pointer",
                )}
              >
                {/* Icon */}
                <Icon
                  size={13}
                  className={cn("shrink-0", isActive ? "text-lav" : "text-ink-faint")}
                  aria-hidden
                />

                {/* Label + description */}
                <div className="flex-1 min-w-0">
                  <p className={cn(
                    "text-[12px] font-medium leading-tight truncate",
                    isActive ? "text-lav" : "text-ink",
                  )}>
                    {b.label}
                  </p>
                  <p className="text-[11px] text-ink-subtle truncate mt-0.5">
                    {b.description}
                  </p>
                </div>

                {/* Trailing indicator */}
                <span className="shrink-0">
                  {isActive ? (
                    <Loader2 size={12} className="animate-spin text-lav" aria-hidden />
                  ) : (
                    <ArrowRight size={12} className="text-ink-faint" aria-hidden />
                  )}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
