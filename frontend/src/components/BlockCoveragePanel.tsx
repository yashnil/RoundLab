"use client";

import { useState } from "react";
import {
  Shield, ChevronDown, ChevronUp, Loader2, RefreshCw,
  CheckCircle2, AlertCircle, XCircle, HelpCircle, BookOpen,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";
import {
  coverageStatusLabel,
  coverageStatusBadgeStyle,
} from "@/lib/blockfileHelpers";
import type {
  BlockCoverageResponse, BlockCoverageCheck, BlockCoverageStatus,
} from "@/types";

interface BlockCoveragePanelProps {
  speechId: string;
  userId: string;
  /** Pre-loaded coverage (null = not run yet, undefined = still loading) */
  coverage: BlockCoverageResponse | null | undefined;
  hasBlockEntries: boolean;
  onCoverageChange: (c: BlockCoverageResponse | null) => void;
}

function CoverageStatusIcon({ status }: { status: BlockCoverageStatus }) {
  if (status === "covered")
    return <CheckCircle2 size={14} className="text-ok shrink-0" />;
  if (status === "partially_covered")
    return <AlertCircle size={14} className="text-warn shrink-0" />;
  if (status === "missing")
    return <XCircle size={14} className="text-danger shrink-0" />;
  return <HelpCircle size={14} className="text-ink-faint shrink-0" />;
}

function CoverageCheckRow({ check }: { check: BlockCoverageCheck }) {
  const [expanded, setExpanded] = useState(false);
  const badgeStyle = coverageStatusBadgeStyle(check.status);

  return (
    <div className="rounded-lg border border-hairline bg-surface-2">
      <button
        onClick={() => setExpanded((p) => !p)}
        className="flex w-full items-start gap-3 px-3.5 py-3 text-left"
      >
        <CoverageStatusIcon status={check.status} />
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium text-ink truncate">
            {check.claim_text.length > 120
              ? check.claim_text.slice(0, 120) + "…"
              : check.claim_text}
          </p>
          <span
            className="mt-0.5 inline-block text-[10px] font-semibold rounded-full px-1.5 py-0.5"
            style={badgeStyle}
          >
            {coverageStatusLabel(check.status)}
          </span>
        </div>
        {expanded ? (
          <ChevronUp size={12} className="shrink-0 mt-0.5 text-ink-faint" />
        ) : (
          <ChevronDown size={12} className="shrink-0 mt-0.5 text-ink-faint" />
        )}
      </button>

      {expanded && (
        <div className="border-t border-hairline px-3.5 pb-3 pt-2.5 flex flex-col gap-2">
          {check.rationale && (
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wide text-ink-faint mb-0.5">
                Analysis
              </p>
              <p className="text-xs text-ink-subtle leading-relaxed">{check.rationale}</p>
            </div>
          )}
          {check.missing_piece && check.status !== "covered" && (
            <div
              className="rounded-lg px-3 py-2"
              style={{
                background: "oklch(0.760 0.160 60 / 0.07)",
                border: "1px solid oklch(0.760 0.160 60 / 0.22)",
              }}
            >
              <p className="text-[10px] font-semibold uppercase tracking-wide text-warn mb-0.5">
                Missing piece
              </p>
              <p className="text-xs text-ink-subtle leading-relaxed">{check.missing_piece}</p>
            </div>
          )}
          {check.top_similarity !== null && check.top_similarity !== undefined && (
            <p className="text-[10px] text-ink-faint">
              Best block match: {Math.round(check.top_similarity * 100)}% similarity
            </p>
          )}
        </div>
      )}
    </div>
  );
}

export default function BlockCoveragePanel({
  speechId,
  userId,
  coverage,
  hasBlockEntries,
  onCoverageChange,
}: BlockCoveragePanelProps) {
  const [running, setRunning] = useState(false);
  const [runErr, setRunErr] = useState("");

  async function runCoverage(force = false) {
    setRunning(true);
    setRunErr("");
    try {
      const data = await apiFetch<BlockCoverageResponse>(
        `/speeches/${speechId}/block-coverage`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ user_id: userId, force_rerun: force }),
        },
      );
      onCoverageChange(data);
    } catch (e: unknown) {
      setRunErr(e instanceof Error ? e.message : "Coverage check failed");
    } finally {
      setRunning(false);
    }
  }

  // Loading from parent
  if (coverage === undefined) {
    return (
      <div className="flex items-center gap-2 py-3">
        <Loader2 size={13} className="animate-spin text-ink-faint" />
        <p className="text-xs text-ink-faint">Loading block coverage…</p>
      </div>
    );
  }

  // No blocks uploaded
  if (!hasBlockEntries) {
    return (
      <div className="flex flex-col gap-3">
        <div className="flex items-start gap-3 rounded-xl border border-dashed border-hairline p-4">
          <BookOpen size={14} className="shrink-0 mt-0.5 text-ink-faint" />
          <div>
            <p className="text-sm font-semibold text-ink">No blockfile uploaded</p>
            <p className="mt-0.5 text-xs text-ink-subtle leading-relaxed">
              Upload a blockfile to your Evidence Library to check whether your responses
              use your prepared blocks and frontlines.
            </p>
            <a
              href="/evidence"
              className="mt-1.5 inline-flex items-center gap-1 text-xs text-lav hover:underline underline-offset-2"
            >
              Open Evidence Library →
            </a>
          </div>
        </div>
      </div>
    );
  }

  // Coverage not run yet
  if (coverage === null) {
    return (
      <div className="flex flex-col gap-3">
        <div className="flex items-start gap-3 rounded-xl border border-hairline bg-surface-2 p-4">
          <Shield size={14} className="shrink-0 mt-0.5 text-ink-faint" />
          <div className="flex-1">
            <p className="text-sm font-semibold text-ink">Check block coverage</p>
            <p className="mt-0.5 text-xs text-ink-subtle leading-relaxed">
              See whether your speech used the uploaded blocks and frontlines for each argument.
              Only your uploaded files are used — no outside knowledge.
            </p>
          </div>
        </div>
        {runErr && (
          <p className="text-xs text-danger">{runErr}</p>
        )}
        <Button
          size="sm"
          className="w-fit gap-1.5 text-xs"
          onClick={() => runCoverage(false)}
          disabled={running}
        >
          {running ? (
            <><Loader2 size={11} className="animate-spin" />Checking…</>
          ) : (
            <><Shield size={11} />Check block coverage</>
          )}
        </Button>
      </div>
    );
  }

  // Coverage results
  const { checks, covered_count, partially_covered_count, missing_count,
    no_available_block_count, total_block_entries } = coverage;
  const total = checks.length;

  return (
    <div className="flex flex-col gap-4">
      {/* Summary header */}
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[10px] font-semibold text-ok">
              {covered_count} covered
            </span>
            {partially_covered_count > 0 && (
              <span className="text-[10px] font-semibold text-warn">
                {partially_covered_count} partial
              </span>
            )}
            {missing_count > 0 && (
              <span className="text-[10px] font-semibold text-danger">
                {missing_count} missing
              </span>
            )}
            {no_available_block_count > 0 && (
              <span className="text-[10px] text-ink-faint">
                {no_available_block_count} no block
              </span>
            )}
            <span className="text-[10px] text-ink-faint">
              · {total_block_entries} blocks in library
            </span>
          </div>
        </div>
        <button
          onClick={() => runCoverage(true)}
          disabled={running}
          title="Re-run coverage"
          className="shrink-0 rounded-lg p-1.5 text-ink-faint hover:bg-surface-2 hover:text-ink transition-colors"
        >
          <RefreshCw size={12} className={running ? "animate-spin" : ""} />
        </button>
      </div>

      {/* Progress bar */}
      {total > 0 && (
        <div className="h-1 w-full rounded-full bg-surface-3 overflow-hidden flex">
          {covered_count > 0 && (
            <div
              className="h-full bg-ok transition-all"
              style={{ width: `${(covered_count / total) * 100}%` }}
            />
          )}
          {partially_covered_count > 0 && (
            <div
              className="h-full bg-warn transition-all"
              style={{ width: `${(partially_covered_count / total) * 100}%` }}
            />
          )}
          {missing_count > 0 && (
            <div
              className="h-full bg-danger transition-all"
              style={{ width: `${(missing_count / total) * 100}%` }}
            />
          )}
        </div>
      )}

      {/* Check rows */}
      {checks.length > 0 && (
        <div className="flex flex-col gap-1.5">
          {checks.map((check) => (
            <CoverageCheckRow key={check.id} check={check} />
          ))}
        </div>
      )}

      {total === 0 && (
        <p className="text-xs text-ink-faint">No arguments to check.</p>
      )}

      {runErr && <p className="text-xs text-danger">{runErr}</p>}

      <p className="text-[10px] text-ink-faint leading-relaxed">
        Based only on your uploaded blockfiles — no outside knowledge is used.
      </p>
    </div>
  );
}
