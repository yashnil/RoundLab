"use client";

import { useState, useEffect } from "react";
import { motion, useReducedMotion } from "motion/react";
import { CheckCircle2, AlertTriangle, XCircle, Plus, ChevronRight } from "lucide-react";
import { fadeUpInView, reducedSafe } from "@/lib/motion";

// ── Types ─────────────────────────────────────────────────────────────────────

export type NodeStatus = "strong" | "weak" | "missing";

export interface FlowNode {
  role: string;
  status: NodeStatus;
  excerpt: string;
}

// ── Data — C1: Economic Burden Shift ─────────────────────────────────────────
// Status values mirror SpeechFlowSection and JudgeLensSection for continuity.

export const DECISIVE_MOMENT_NODES: FlowNode[] = [
  { role: "CLAIM",    status: "strong",  excerpt: "Refugee resettlement shifts fiscal burden to municipalities" },
  { role: "EVIDENCE", status: "strong",  excerpt: "Urban Institute 2023 — $21K long-run return, $8K upfront cost" },
  { role: "WARRANT",  status: "weak",    excerpt: "Rural districts bear costs disproportionately (mechanism asserted)" },
  { role: "IMPACT",   status: "strong",  excerpt: "Integration services suppressed — harm to resettled families" },
  { role: "WEIGHING", status: "missing", excerpt: "— not addressed in this speech —" },
];

export const BALLOT_EXCERPT =
  "No weighing on C1 — NC's long-run return argument stands uncontested. I have to resolve this line for the negative.";

export const DRILL_CARD_DATA = {
  step: "Weighing comparison",
  type: "Argument weighing",
  prompt:
    "Compare the $8K short-run municipal burden to NC's $21K five-year return claim. State which timeframe matters more and why year one is the decisive period.",
  target: "Explicit weighing with a named timeframe comparison",
  durationLabel: "90 sec",
};

export const BEFORE_SPEECH = {
  label: "Before drill",
  timestamp: "Summary · 1:12",
  excerpt:
    "Extend our first contention — the evidence shows municipalities bear upfront costs without adequate reimbursement, suppressing integration services for years.",
  added: [] as string[],
};

export const AFTER_SPEECH = {
  label: "After drill",
  timestamp: "Summary (re-record) · 1:15",
  excerpt:
    "Municipalities bear $8K in year-one costs while NC's benefits take five years to materialize — we win the first year, when the integration harm actually hits. That outweighs on timeframe.",
  added: ["Weighing", "Timeframe comparison", "Causal link"],
};

// ── Style helpers ─────────────────────────────────────────────────────────────

const NODE_CONFIG: Record<NodeStatus, {
  Icon: React.ComponentType<{ size?: number; className?: string; "aria-hidden"?: boolean | "true" }>;
  iconClass: string;
  statusWord: string;
  statusClass: string;
}> = {
  strong:  { Icon: CheckCircle2, iconClass: "text-ok",     statusWord: "strong",  statusClass: "text-ok"     },
  weak:    { Icon: AlertTriangle, iconClass: "text-warn",   statusWord: "weak",    statusClass: "text-warn"   },
  missing: { Icon: XCircle,       iconClass: "text-danger", statusWord: "missing", statusClass: "text-danger" },
};

// ── Step number chip ──────────────────────────────────────────────────────────

function StepChip({ n }: { n: string }) {
  return (
    <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-lav/15 text-eyebrow font-bold text-lav">
      {n}
    </span>
  );
}

// ── 01: Decisive Moment ───────────────────────────────────────────────────────

function DecisiveMomentCard({ animated }: { animated: boolean }) {
  return (
    <motion.div
      {...(animated ? reducedSafe(fadeUpInView(0.06)) : {})}
      className="flex h-full flex-col overflow-hidden rounded-2xl border border-hairline bg-surface-1"
      data-testid="decisive-moment-card"
    >
      <div className="flex items-center gap-2.5 border-b border-hairline px-5 py-3">
        <StepChip n="01" />
        <span className="section-stamp">Decisive moment</span>
      </div>

      <div className="flex flex-1 flex-col gap-3.5 p-5">
        {/* Mini flow sheet — strong nodes compact, weak/missing nodes annotated */}
        <div className="flex flex-col gap-1" role="list" aria-label="C1 argument chain status">
          {DECISIVE_MOMENT_NODES.map((node) => {
            const cfg = NODE_CONFIG[node.status];
            const { Icon } = cfg;
            const isCompact = node.status === "strong"; // strong nodes: role + status only
            return (
              <div
                key={node.role}
                role="listitem"
                className={[
                  "flex items-start gap-2 rounded-md px-3",
                  isCompact ? "py-1.5" : "py-2",
                  node.status === "missing"
                    ? "border border-danger/25 bg-danger/5"
                    : node.status === "weak"
                    ? "border border-warn/20 bg-warn/5"
                    : "border border-hairline bg-surface-2/40",
                ].join(" ")}
              >
                <Icon
                  size={11}
                  className={`mt-[2px] shrink-0 ${cfg.iconClass}`}
                  aria-hidden
                />
                <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                  <div className="flex items-baseline gap-1.5">
                    <span
                      className={[
                        "text-eyebrow font-semibold",
                        node.status === "missing"
                          ? "text-danger"
                          : node.status === "weak"
                          ? "text-warn"
                          : "text-ink",
                      ].join(" ")}
                    >
                      {node.role}
                    </span>
                    <span className={`text-eyebrow ${cfg.statusClass}`}>
                      · {cfg.statusWord}
                    </span>
                  </div>
                  {/* Show note only for weak and missing nodes */}
                  {!isCompact && (
                    <p className="text-xs leading-snug text-ink-subtle">{node.excerpt}</p>
                  )}
                </div>
                {node.status === "missing" && (
                  <span className="shrink-0 text-xs font-bold text-danger">✗</span>
                )}
              </div>
            );
          })}
        </div>

        {/* Ballot excerpt — anchored at bottom with a visible separator */}
        <div className="mt-auto border-t border-hairline/50 pt-3">
        <div
          className="flex flex-col gap-1.5 rounded-lg border border-warn/20 bg-warn/5 px-3 py-3"
          data-testid="ballot-excerpt"
        >
          <p className="section-stamp text-warn">Flow judge · ballot note</p>
          <p className="text-xs italic leading-relaxed text-ink-subtle">
            &ldquo;{BALLOT_EXCERPT}&rdquo;
          </p>
        </div>
        </div>
      </div>
    </motion.div>
  );
}

// ── 02: Drill Bridge ──────────────────────────────────────────────────────────

function DrillBridgeCard({ animated }: { animated: boolean }) {
  return (
    <motion.div
      {...(animated ? reducedSafe(fadeUpInView(0.12)) : {})}
      className="flex h-full flex-col overflow-hidden rounded-2xl border border-lav/30 bg-lav/[0.04]"
      data-testid="drill-bridge-card"
    >
      <div className="flex items-center gap-2.5 border-b border-lav/20 px-5 py-3">
        <StepChip n="02" />
        <span className="section-stamp text-lav">Drill assigned</span>
      </div>

      <div className="flex flex-1 flex-col gap-3 p-5">
        {/* Gap-trigger bridge — carries the diagnosis from card 01 */}
        <div
          className="flex items-center gap-1.5 rounded-md border border-warn/25 bg-warn/5 px-2.5 py-1.5"
          data-testid="gap-trigger"
        >
          <AlertTriangle size={10} className="shrink-0 text-warn" aria-hidden />
          <span className="text-eyebrow font-semibold text-warn">WEIGHING</span>
          <span className="text-eyebrow text-ink-subtle">· missing · prescribed from C1</span>
        </div>

        {/* Drill content — separated from the diagnosis trigger by a lav line */}
        <div className="flex flex-1 flex-col gap-3 border-t border-lav/20 pt-3">
          {/* Drill type badge */}
          <div className="flex items-center gap-2">
            <span className="rounded bg-lav/15 px-1.5 py-0.5 text-eyebrow font-semibold text-lav">
              {DRILL_CARD_DATA.type.toUpperCase()}
            </span>
          </div>

          {/* Drill prompt */}
          <p
            className="text-sm font-medium leading-relaxed text-ink"
            data-testid="drill-prompt"
          >
            &ldquo;{DRILL_CARD_DATA.prompt}&rdquo;
          </p>

          {/* Expected outcome + duration */}
          <div className="mt-auto flex flex-col gap-2">
            <p className="section-stamp">Expected outcome</p>
            <p className="text-xs text-ink-subtle">{DRILL_CARD_DATA.target}</p>
            <span className="w-fit rounded-full border border-hairline bg-surface-2 px-2.5 py-1 text-xs font-medium text-ink-subtle">
              {DRILL_CARD_DATA.durationLabel} · speak aloud
            </span>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

// ── 03: Before/After Transformation ──────────────────────────────────────────

function TransformationCard({ animated }: { animated: boolean }) {
  return (
    <motion.div
      {...(animated ? reducedSafe(fadeUpInView(0.18)) : {})}
      className="flex h-full flex-col overflow-hidden rounded-2xl border border-hairline bg-surface-1"
      data-testid="transformation-card"
    >
      <div className="flex items-center gap-2.5 border-b border-hairline px-5 py-3">
        <StepChip n="03" />
        <span className="section-stamp">A round later</span>
      </div>

      <div className="flex flex-1 flex-col gap-3 p-5">
        {/* Before lane — visually recessive: framed but dim to signal the unresolved state */}
        <div className="flex flex-col gap-2 rounded-lg border border-hairline bg-surface-2/60 px-4 py-3">
          <div className="flex items-center justify-between">
            <span className="text-eyebrow font-semibold text-ink-subtle">BEFORE DRILL</span>
            <span className="font-mono text-xs text-ink-faint">{BEFORE_SPEECH.timestamp}</span>
          </div>
          <p className="text-xs italic leading-relaxed text-ink-faint">
            &ldquo;{BEFORE_SPEECH.excerpt}&rdquo;
          </p>
        </div>

        {/* After lane — dominant: left lav accent marks the resolved state */}
        <div
          className="flex flex-1 flex-col gap-2 rounded-lg border-l-2 border-lav bg-lav/[0.06] px-4 py-3"
          data-testid="after-lane"
        >
          <div className="flex items-center justify-between">
            <span className="text-eyebrow font-semibold text-lav">
              {AFTER_SPEECH.label.toUpperCase()}
            </span>
            <span className="font-mono text-xs text-ink-faint">{AFTER_SPEECH.timestamp}</span>
          </div>
          <p className="text-sm leading-relaxed text-ink">
            &ldquo;{AFTER_SPEECH.excerpt}&rdquo;
          </p>
          {/* Added behavior chips */}
          <div className="mt-auto flex flex-wrap gap-1.5 border-t border-lav/15 pt-3">
            {AFTER_SPEECH.added.map((label) => (
              <span
                key={label}
                className="inline-flex items-center gap-1 rounded-full border border-lav/25 bg-lav/10 px-2 py-0.5 text-eyebrow font-semibold text-lav"
              >
                <Plus size={8} aria-hidden /> {label}
              </span>
            ))}
          </div>
        </div>

        {/* Coach observation */}
        <div className="flex items-start gap-2 rounded-lg border border-ok/20 bg-ok/5 px-3 py-2.5">
          <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-ok" aria-hidden />
          <p className="text-xs leading-relaxed text-ink-muted">
            <span className="font-semibold text-ink">What changed:</span>{" "}
            the extension now names the conceded warrant and weighs on timeframe explicitly.
          </p>
        </div>
      </div>
    </motion.div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────

export default function DebateProofSection() {
  const [isMounted, setIsMounted] = useState(false);
  useEffect(() => setIsMounted(true), []);
  const prefersReducedMotion = useReducedMotion();
  const animated = isMounted && prefersReducedMotion === false;

  return (
    <section
      id="product-proof"
      className="scroll-mt-16 border-t border-hairline"
      aria-label="Coaching story: from gap detection to improvement"
    >
      <div className="mx-auto max-w-6xl px-6 py-14">
        {/* Section heading */}
        <motion.div
          {...reducedSafe(fadeUpInView(0))}
          className="mb-8 flex flex-col gap-2"
        >
          <p className="section-stamp">Coaching story · C1 · Economic Burden Shift</p>
          <h2 className="text-headline text-ink max-w-2xl">
            One gap. One drill.{" "}
            <br className="hidden sm:block" />A round later.
          </h2>
          <p className="mt-1 max-w-lg text-sm leading-relaxed text-ink-subtle">
            Same speech. One diagnosed gap. One drill. A stronger next round.
          </p>
        </motion.div>

        {/*
          Three-card causal sequence.
          xl+: 5-column grid — cards in cols 1,3,5 with causal connector columns in 2,4.
          Below xl: single-column stack (connectors hidden).
          lg (1024px) deliberately kept as single-column to avoid cramped three-col layout.
        */}
        <div className="grid grid-cols-1 items-stretch gap-4 xl:gap-0 xl:grid-cols-[1fr_60px_1fr_60px_1fr]">
          <DecisiveMomentCard animated={animated} />

          {/* Connector 01→02: carries the WEIGHING gap signal forward */}
          <div
            className="hidden xl:flex flex-col items-center justify-center gap-1 self-center px-1"
            aria-hidden
          >
            <span className="text-center text-eyebrow font-semibold leading-snug text-warn">
              ✗ WEIGHING
            </span>
            <span className="text-center text-eyebrow leading-snug text-ink-faint">
              detected
            </span>
            <ChevronRight size={13} className="mt-1 text-hairline-strong" />
          </div>

          <DrillBridgeCard animated={animated} />

          {/* Connector 02→03: drill rep completed, outcome follows */}
          <div
            className="hidden xl:flex flex-col items-center justify-center gap-1 self-center px-1"
            aria-hidden
          >
            <span className="text-center text-eyebrow leading-snug text-ink-faint">
              drill
            </span>
            <span className="text-center text-eyebrow leading-snug text-ink-faint">
              complete
            </span>
            <ChevronRight size={13} className="mt-1 text-hairline-strong" />
          </div>

          <TransformationCard animated={animated} />
        </div>
      </div>
    </section>
  );
}
