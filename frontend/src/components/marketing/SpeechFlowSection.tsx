"use client";

import { useState, useEffect } from "react";
import { motion } from "motion/react";
import { AlertTriangle } from "lucide-react";
import { fadeUpInView, reducedSafe } from "@/lib/motion";

// ── Data model ────────────────────────────────────────────────────────────────

export type PhraseRole = "claim" | "warrant" | "evidence" | "impact";

export interface TranscriptSegment {
  type: "text" | "phrase";
  content: string;
  phraseId?: string;
  role?: PhraseRole;
}

export interface FlowNode {
  id: string;
  phraseId?: string;
  role: PhraseRole;
  status: "strong" | "weak" | "missing";
  label: string;   // e.g. "CLAIM"
  excerpt: string;
  note?: string;
}

// ── Content — C1: Economic Burden Shift ──────────────────────────────────────
// Same example referenced in HeroDebateConsole for narrative continuity.

export const TRANSCRIPT_SEGMENTS: TranscriptSegment[] = [
  {
    type: "phrase",
    phraseId: "ph-claim",
    role: "claim",
    content:
      "The current refugee resettlement framework imposes concentrated short-run costs on receiving municipalities without adequate federal offset.",
  },
  { type: "text", content: " " },
  {
    type: "phrase",
    phraseId: "ph-evidence",
    role: "evidence",
    content:
      "According to the Urban Institute's 2023 report, the average refugee household achieves net fiscal positivity within five years — generating $21,000 in tax revenue above service consumption.",
  },
  { type: "text", content: " But " },
  {
    type: "phrase",
    phraseId: "ph-warrant",
    role: "warrant",
    content:
      "municipalities in rural districts bear upfront costs of eight thousand dollars per refugee before federal reimbursement arrives.",
  },
  { type: "text", content: " " },
  {
    type: "phrase",
    phraseId: "ph-impact",
    role: "impact",
    content:
      "Without rebalancing this burden, local opposition suppresses integration infrastructure",
  },
  { type: "text", content: " — and that's the decisive link in this round." },
];

export const FLOW_NODES: FlowNode[] = [
  {
    id: "node-claim",
    phraseId: "ph-claim",
    role: "claim",
    status: "strong",
    label: "CLAIM",
    excerpt: "Short-run municipal costs, no federal offset",
  },
  {
    id: "node-evidence",
    phraseId: "ph-evidence",
    role: "evidence",
    status: "strong",
    label: "EVIDENCE",
    excerpt: "Urban Institute 2023 — net fiscal positivity in 5 yrs",
    note: "Urban Institute, 2023",
  },
  {
    id: "node-warrant",
    phraseId: "ph-warrant",
    role: "warrant",
    status: "weak",
    label: "WARRANT",
    excerpt: "$8K upfront cost before federal reimbursement",
    note: "Mechanism asserted — causal link unclear",
  },
  {
    id: "node-impact",
    phraseId: "ph-impact",
    role: "impact",
    status: "strong",
    label: "IMPACT",
    excerpt: "Local opposition suppresses integration programs",
  },
];

// ── Style maps ────────────────────────────────────────────────────────────────

const PHRASE_STYLE: Record<PhraseRole, { base: string; active: string }> = {
  claim:    { base: "border-b border-lav/50",  active: "bg-lav/10 rounded-sm"  },
  evidence: { base: "border-b border-ok/50",   active: "bg-ok/10 rounded-sm"   },
  warrant:  { base: "border-b border-warn/50", active: "bg-warn/10 rounded-sm" },
  impact:   { base: "border-b border-ok/40",   active: "bg-ok/10 rounded-sm"   },
};

const PHRASE_TEXT: Record<PhraseRole, string> = {
  claim:    "text-lav",
  evidence: "text-ok",
  warrant:  "text-warn",
  impact:   "text-ok",
};

const NODE_STYLE: Record<PhraseRole, { border: string; bg: string; badge: string }> = {
  claim:    { border: "border-lav/30",  bg: "bg-lav/6",  badge: "bg-lav/15 text-lav"   },
  evidence: { border: "border-ok/30",   bg: "bg-ok/6",   badge: "bg-ok/15 text-ok"     },
  warrant:  { border: "border-warn/30", bg: "bg-warn/6", badge: "bg-warn/15 text-warn" },
  impact:   { border: "border-ok/30",   bg: "bg-ok/6",   badge: "bg-ok/15 text-ok"     },
};

// ── Activation helpers (pure — also exercised in unit tests) ──────────────────

/** Is this transcript phrase highlighted given the current activeId? */
export function isPhraseActive(phraseId: string, activeId: string | null): boolean {
  if (activeId === phraseId) return true;
  const node = FLOW_NODES.find((n) => n.id === activeId);
  return node?.phraseId === phraseId;
}

/** Is this flow node highlighted given the current activeId? */
export function isNodeActive(node: FlowNode, activeId: string | null): boolean {
  if (activeId === node.id) return true;
  return activeId === node.phraseId;
}

// ── Role legend (shared between transcript panel and aria description) ─────────

const LEGEND_ROLES: PhraseRole[] = ["claim", "evidence", "warrant", "impact"];

// ── Component ─────────────────────────────────────────────────────────────────

export default function SpeechFlowSection() {
  const [activeId, setActiveId] = useState<string | null>(null);
  // Polite live region for screen-reader announcement of selections.
  // Only updated on interaction — never announced on page load.
  const [liveMsg, setLiveMsg] = useState("");

  function toggle(id: string) {
    setActiveId((prev) => (prev === id ? null : id));
  }

  useEffect(() => {
    if (!activeId) {
      setLiveMsg("");
      return;
    }
    const seg = TRANSCRIPT_SEGMENTS.find((s) => s.phraseId === activeId);
    const node = FLOW_NODES.find((n) => n.id === activeId || n.phraseId === activeId);
    const roleLabel = (seg?.role ?? node?.role ?? "item") as string;
    const cap = roleLabel.charAt(0).toUpperCase() + roleLabel.slice(1);
    setLiveMsg(`${cap} phrase selected — flow chain node highlighted`);
  }, [activeId]);

  return (
    <section
      id="speech-to-flow"
      className="scroll-mt-16 border-t border-hairline"
      aria-label="Interactive speech-to-flow demonstration"
    >
      {/* Polite announcement for screen readers — never visible on screen */}
      <div role="status" aria-live="polite" className="sr-only">
        {liveMsg}
      </div>

      <div className="mx-auto max-w-6xl px-6 py-14">
        {/* Section heading */}
        <motion.div {...reducedSafe(fadeUpInView(0))} className="mb-7 flex flex-col gap-2">
          <p className="section-stamp">Speech understanding</p>
          <h2 className="text-headline text-ink max-w-xl">
            RoundLab doesn&apos;t just transcribe.{" "}
            <br className="hidden sm:block" />
            It understands the round.
          </h2>
          <p className="mt-1 max-w-lg text-sm leading-relaxed text-ink-subtle">
            Watch a single PF argument become a structured flow — every phrase identified,
            linked, and graded before a flow judge finds the gaps.
          </p>
        </motion.div>

        {/* Two-panel grid: transcript (wider) + flow chain — equal height at lg+ */}
        <motion.div
          {...reducedSafe(fadeUpInView(0.08))}
          className="grid grid-cols-1 gap-4 lg:grid-cols-[1fr_388px] lg:gap-5 xl:grid-cols-[1fr_408px]"
        >
          {/* ── Left: Transcript ──────────────────────────────────────────── */}
          <div className="flex flex-col overflow-hidden rounded-2xl border border-hairline bg-surface-1">
            {/* Panel header — clean single line */}
            <div className="flex items-center gap-2 border-b border-hairline px-5 py-3">
              <span className="section-stamp">Transcript</span>
              <span className="select-none text-ink-faint" aria-hidden>·</span>
              <span className="text-xs text-ink-subtle">C1 · Economic Burden Shift</span>
            </div>

            {/* Transcript body */}
            <div className="flex-1 px-5 py-5">
              {/* Annotated prose. Each phrase segment is a button that can be toggled. */}
              <p
                id="stf-transcript-body"
                className="text-sm leading-[1.75] text-ink-subtle"
              >
                {TRANSCRIPT_SEGMENTS.map((seg, i) => {
                  if (seg.type === "text") {
                    return <span key={i}>{seg.content}</span>;
                  }

                  const role = seg.role!;
                  const phraseId = seg.phraseId!;
                  const active = isPhraseActive(phraseId, activeId);
                  const ps = PHRASE_STYLE[role];

                  return (
                    <button
                      key={i}
                      type="button"
                      onClick={() => toggle(phraseId)}
                      aria-pressed={active}
                      aria-label={`${role}: ${seg.content.slice(0, 72)}…`}
                      className={[
                        "inline cursor-pointer px-0.5 text-left text-sm leading-[1.9]",
                        "transition-colors duration-150",
                        "focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-lav/60 focus-visible:rounded-sm",
                        ps.base,
                        PHRASE_TEXT[role],
                        active ? ps.active : "",
                      ].join(" ")}
                    >
                      {seg.content}
                    </button>
                  );
                })}
              </p>

              {/* Role legend — below prose to avoid header wrapping */}
              <div
                className="mt-4 flex flex-wrap items-center gap-1.5"
                aria-hidden
              >
                {LEGEND_ROLES.map((role) => (
                  <span
                    key={role}
                    className={`rounded px-1.5 py-0.5 text-eyebrow font-semibold ${NODE_STYLE[role].badge}`}
                  >
                    {role}
                  </span>
                ))}
                <span className="ml-1 text-xs text-ink-subtle">
                  · tap to connect
                </span>
              </div>
            </div>
          </div>

          {/* ── Right: Flow chain ─────────────────────────────────────────── */}
          <div className="flex flex-col overflow-hidden rounded-2xl border border-hairline bg-surface-1">
            {/* Panel header */}
            <div className="flex items-center justify-between border-b border-hairline px-5 py-3">
              <span className="section-stamp">Argument flow</span>
              <span className="text-xs text-ink-subtle">C1 chain</span>
            </div>

            {/* Coaching gap summary — always visible at top of panel */}
            <div
              className="flex items-center gap-2 border-b border-warn/20 bg-warn/5 px-4 py-2"
              data-testid="coaching-gap-summary"
            >
              <AlertTriangle size={11} className="shrink-0 text-warn" aria-hidden />
              <span className="text-eyebrow font-semibold text-warn">
                1 gap detected
              </span>
              <span className="text-xs text-warn/80">· no weighing in this speech</span>
            </div>

            {/* Chain nodes */}
            <div
              className="flex flex-1 flex-col px-5 py-4"
              role="list"
              aria-label="Extracted argument chain"
            >
              {FLOW_NODES.map((node, i) => {
                const active = isNodeActive(node, activeId);
                const ns = NODE_STYLE[node.role];
                const isWeak = node.status === "weak";

                return (
                  <div key={node.id} role="listitem">
                    {/* Connector line above (except first) */}
                    {i > 0 && (
                      <div
                        className="ml-4 h-3 w-px border-l border-hairline-strong"
                        aria-hidden
                      />
                    )}

                    {/* Node */}
                    <button
                      type="button"
                      onClick={() => (node.phraseId ? toggle(node.phraseId) : undefined)}
                      aria-pressed={active}
                      aria-label={`${node.label}: ${node.excerpt}`}
                      className={[
                        "group w-full rounded-xl border px-3 py-2 text-left",
                        "transition-all duration-150",
                        ns.border,
                        active
                          ? `${ns.bg} shadow-sm ring-1 ring-inset ${ns.border}`
                          : "bg-transparent",
                        "cursor-pointer hover:bg-surface-2/60",
                        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50",
                      ].join(" ")}
                    >
                      <div className="flex items-start gap-2">
                        {/* Status dot */}
                        <span
                          className={[
                            "mt-[5px] h-1.5 w-1.5 shrink-0 rounded-full",
                            node.status === "strong"
                              ? "bg-ok"
                              : node.status === "weak"
                              ? "bg-warn"
                              : "bg-danger",
                          ].join(" ")}
                          aria-hidden
                        />
                        <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                          <div className="flex items-center gap-1.5">
                            <span
                              className={`rounded px-1.5 py-0.5 text-eyebrow font-semibold ${ns.badge}`}
                            >
                              {node.label}
                            </span>
                            {isWeak && (
                              <span className="text-xs text-warn" aria-label="weak">
                                ⚠
                              </span>
                            )}
                          </div>
                          <p className="text-xs font-medium leading-snug text-ink">
                            {node.excerpt}
                          </p>
                          {node.note && (
                            <p className="mt-0.5 text-xs leading-snug text-ink-subtle">
                              {node.note}
                            </p>
                          )}
                        </div>
                      </div>
                    </button>
                  </div>
                );
              })}

              {/* Dashed connector to missing node */}
              <div
                className="ml-4 h-3 w-px border-l border-dashed border-warn/40"
                aria-hidden
              />

              {/* Missing weighing — detailed explanation */}
              <div className="rounded-xl border border-dashed border-warn/40 bg-warn/5 px-3 py-2.5">
                <div className="flex items-start gap-2">
                  <AlertTriangle
                    size={11}
                    className="mt-[3px] shrink-0 text-warn"
                    aria-hidden
                  />
                  <div className="flex flex-col gap-0.5">
                    <span className="text-eyebrow font-semibold text-warn">
                      WEIGHING · Missing
                    </span>
                    <p className="text-xs font-medium text-warn">
                      No comparison against NC impact
                    </p>
                    <p className="mt-0.5 text-xs text-ink-subtle">
                      Flow judge flagged: impact magnitude unweighed.
                    </p>
                  </div>
                </div>
              </div>

              {/* NC response — compact inline row */}
              <div className="ml-6 mt-2 flex items-baseline gap-2 border-l-2 border-hairline pl-3">
                <span className="shrink-0 text-eyebrow font-semibold text-ink-subtle">
                  NC
                </span>
                <p className="text-xs text-ink-subtle">
                  &ldquo;Long-run benefit conceded — weigh short-run vs. 5-yr return.&rdquo;
                  <span className="ml-1.5 text-xs font-medium text-danger">Dropped</span>
                </p>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
