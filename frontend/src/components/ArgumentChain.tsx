"use client";

/**
 * ArgumentChain — visualizes the Claim → Warrant → Evidence → Impact
 * structure for a PF debate argument.
 *
 * Modes:
 *   "strip"  Compact horizontal status row (FlowTable, compact surfaces)
 *   "cards"  Full card layout with text (expanded views, report, landing)
 *
 * Status is auto-derived from text presence and issues keywords.
 */

import { motion } from "motion/react";
import { EASE } from "@/lib/motion";
import type { JudgeViewMode } from "@/components/JudgeModeSelector";

// ── Types ──────────────────────────────────────────────────────────────────────

export type ChainNodeStatus = "strong" | "weak" | "missing";

export interface ChainData {
  claim: string;
  warrant: string | null;
  evidence: string | null;
  impact: string;
  issues?: string[];
}

// ── Status inference ───────────────────────────────────────────────────────────

function inferStatus(
  text: string | null,
  issueKeywords: string[],
  issues: string[],
): ChainNodeStatus {
  if (!text || text.trim().length < 6) return "missing";
  const blob = issues.join(" ").toLowerCase();
  if (issueKeywords.some((k) => blob.includes(k))) return "weak";
  return "strong";
}

// ── Visual config per status ───────────────────────────────────────────────────

const S: Record<ChainNodeStatus, {
  dot: string; label: string; border: string; bg: string; badge: string;
}> = {
  strong:  { dot: "bg-ok",     label: "text-ok",     border: "border-ok/25",     bg: "bg-ok/5",    badge: "✓" },
  weak:    { dot: "bg-warn",   label: "text-warn",   border: "border-warn/25",   bg: "bg-warn/5",  badge: "⚠" },
  missing: { dot: "bg-danger", label: "text-danger", border: "border-danger/20", bg: "bg-danger/5",badge: "✗" },
};

// ── Judge-mode field emphasis ──────────────────────────────────────────────────

const JUDGE_EMPHASIS: Record<JudgeViewMode, string[]> = {
  lay:   ["impact"],
  flow:  ["warrant", "impact"],
  tech:  ["evidence", "warrant"],
  coach: [],
};

// ── Strip mode ─────────────────────────────────────────────────────────────────

function StripNode({ label, status, emphasized }: {
  label: string; status: ChainNodeStatus; emphasized: boolean;
}) {
  const s = S[status];
  return (
    <div className="flex shrink-0 items-center gap-1">
      <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${s.dot}`} />
      <span className={`text-[9px] font-semibold uppercase tracking-wider ${
        emphasized ? s.label : "text-ink-faint"
      }`}>{label}</span>
      {status !== "strong" && (
        <span className={`text-[9px] font-bold leading-none ${s.label}`}>{s.badge}</span>
      )}
    </div>
  );
}

function StripConnector({ status }: { status: ChainNodeStatus }) {
  if (status === "missing") {
    return (
      <div className="mx-0.5 flex w-5 shrink-0 items-center">
        <svg className="h-1 w-full overflow-visible" viewBox="0 0 20 2">
          <line
            x1="0" y1="1" x2="20" y2="1"
            stroke="oklch(0.640 0.215 25 / 0.28)"
            strokeWidth="1.5"
            strokeDasharray="3 2"
          />
        </svg>
      </div>
    );
  }
  return (
    <div className={`mx-0.5 h-px w-5 shrink-0 ${
      status === "weak" ? "bg-warn/35" : "bg-ok/40"
    }`} />
  );
}

export function ArgumentChainStrip({ data, judgeMode }: {
  data: ChainData; judgeMode?: JudgeViewMode;
}) {
  const issues  = data.issues ?? [];
  const wStatus = inferStatus(data.warrant,  ["warrant", "missing warrant"], issues);
  const eStatus = inferStatus(data.evidence, ["evidence", "unsupported"],   issues);
  const iStatus = inferStatus(data.impact,   ["impact", "unclear impact"],  issues);
  const em      = JUDGE_EMPHASIS[judgeMode ?? "coach"];

  return (
    <div className="flex flex-wrap items-center gap-0.5">
      <StripNode label="Claim"    status="strong"  emphasized={em.includes("claim")}    />
      <StripConnector status={wStatus} />
      <StripNode label="Warrant"  status={wStatus} emphasized={em.includes("warrant")}  />
      <StripConnector status={eStatus} />
      <StripNode label="Evidence" status={eStatus} emphasized={em.includes("evidence")} />
      <StripConnector status={iStatus} />
      <StripNode label="Impact"   status={iStatus} emphasized={em.includes("impact")}   />
    </div>
  );
}

// ── Cards mode ─────────────────────────────────────────────────────────────────

function ChainCard({ label, text, status, emphasized, delay }: {
  label: string; text: string | null; status: ChainNodeStatus;
  emphasized: boolean; delay: number;
}) {
  const s = S[status];
  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, delay, ease: EASE }}
      className={`flex min-w-0 flex-1 flex-col gap-1.5 rounded-lg border p-2.5 ${s.border} ${s.bg}`}
    >
      <div className="flex items-center gap-1.5">
        <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${s.dot}`} />
        <span className={`text-[9px] font-bold uppercase tracking-wider ${
          emphasized ? s.label : "text-ink-faint"
        }`}>{label}</span>
        {status !== "strong" && (
          <span className={`ml-auto text-[9px] font-bold ${s.label}`}>{s.badge}</span>
        )}
      </div>
      {text ? (
        <p className="line-clamp-4 text-[11px] leading-relaxed text-ink-muted">{text}</p>
      ) : (
        <p className="text-[11px] italic text-danger/60">Not stated in speech</p>
      )}
    </motion.div>
  );
}

function CardConnector({ nextStatus }: { nextStatus: ChainNodeStatus }) {
  const color =
    nextStatus === "missing" ? "text-danger/30"
    : nextStatus === "weak"  ? "text-warn/45"
    : "text-ok/50";
  return (
    <div className={`hidden shrink-0 items-center justify-center sm:flex sm:w-5 ${color}`}>
      <svg width="16" height="10" viewBox="0 0 16 10" fill="none">
        <path
          d="M0 5H12M8 1L14 5L8 9"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeDasharray={nextStatus === "missing" ? "3 2" : undefined}
        />
      </svg>
    </div>
  );
}

export function ArgumentChainCards({ data, judgeMode }: {
  data: ChainData; judgeMode?: JudgeViewMode;
}) {
  const issues  = data.issues ?? [];
  const wStatus = inferStatus(data.warrant,  ["warrant", "missing warrant"], issues);
  const eStatus = inferStatus(data.evidence, ["evidence", "unsupported"],   issues);
  const iStatus = inferStatus(data.impact,   ["impact", "unclear impact"],  issues);
  const em      = JUDGE_EMPHASIS[judgeMode ?? "coach"];

  return (
    <div className="flex flex-col gap-2">
      <p className="text-[10px] font-semibold uppercase tracking-wider text-ink-faint">
        Argument Structure
      </p>
      <div className="flex flex-col gap-1.5 sm:flex-row sm:items-stretch">
        <ChainCard label="Claim"    text={data.claim}    status="strong"  emphasized={em.includes("claim")}    delay={0.00} />
        <CardConnector nextStatus={wStatus} />
        <ChainCard label="Warrant"  text={data.warrant}  status={wStatus} emphasized={em.includes("warrant")}  delay={0.07} />
        <CardConnector nextStatus={eStatus} />
        <ChainCard label="Evidence" text={data.evidence} status={eStatus} emphasized={em.includes("evidence")} delay={0.14} />
        <CardConnector nextStatus={iStatus} />
        <ChainCard label="Impact"   text={data.impact}   status={iStatus} emphasized={em.includes("impact")}   delay={0.21} />
      </div>
    </div>
  );
}

// ── Default export ─────────────────────────────────────────────────────────────

interface ArgumentChainProps {
  data: ChainData;
  mode?: "strip" | "cards";
  judgeMode?: JudgeViewMode;
}

export default function ArgumentChain({ data, mode = "cards", judgeMode }: ArgumentChainProps) {
  if (mode === "strip") return <ArgumentChainStrip data={data} judgeMode={judgeMode} />;
  return <ArgumentChainCards data={data} judgeMode={judgeMode} />;
}
