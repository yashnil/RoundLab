"use client";

/**
 * HeroDebateConsole — Compact 2.5D product graphic for the landing hero.
 *
 * Shows the full product loop at a glance:
 *   Audio → Argument Flow → Judge Ballot → Drill
 *
 * Accessibility: role="img" + aria-label on the outer wrapper; all inner elements
 * are aria-hidden so screen readers see only the accessible label.
 *
 * Motion: entrance animation on the outer wrapper only. Inner elements use plain
 * divs/spans (no motion.*) to avoid partial-opacity states during Axe color-contrast
 * scanning. All text colors meet AA contrast on surface-1 background.
 */

import { motion } from "motion/react";
import { Mic, Zap } from "lucide-react";
import { EASE } from "@/lib/motion";

// ── Static waveform ────────────────────────────────────────────────────────────

const WAVE = [5, 9, 14, 8, 20, 13, 6, 18, 11, 5, 16, 10, 4, 17, 7, 12, 9, 15, 6, 11];

function StaticWaveform() {
  return (
    <div className="flex items-end gap-0.5">
      {WAVE.map((h, i) => (
        <div
          key={i}
          className="w-1 shrink-0 rounded-full bg-lav"
          style={{ height: h * 1.5, opacity: 0.25 + (h / 20) * 0.65, minHeight: 2 }}
        />
      ))}
    </div>
  );
}

// ── Argument chain node ────────────────────────────────────────────────────────

type NodeStatus = "ok" | "warn";

function ChainNode({ label, status }: { label: string; status: NodeStatus }) {
  const cls =
    status === "ok"
      ? "border-ok/25 bg-ok/8 text-ok"
      : "border-warn/25 bg-warn/8 text-warn";
  return (
    <span className={`rounded border px-1.5 py-0.5 ${cls}`}>
      <span className="block text-eyebrow font-bold uppercase leading-none tracking-wide">
        {label}
        {status === "warn" && " ⚠"}
      </span>
    </span>
  );
}

// ── Ballot bar ─────────────────────────────────────────────────────────────────

function BallotBar({
  label, value, max,
}: { label: string; value: number; max: number }) {
  const pct   = Math.round((value / max) * 100);
  const color = value < 12 ? "bg-warn" : "bg-lav";
  return (
    <div className="flex items-center gap-1.5">
      <span className="w-14 shrink-0 text-eyebrow text-ink-subtle">{label}</span>
      <div className="h-0.5 flex-1 overflow-hidden rounded-full bg-hairline">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-4 shrink-0 text-right text-eyebrow tabular-nums text-ink-subtle">{value}</span>
    </div>
  );
}

// ── Stage progress strip ───────────────────────────────────────────────────────

const STAGES = ["Audio", "Flow", "Ballot", "Drill"] as const;

function StageBar() {
  return (
    <div className="flex items-center justify-between border-b border-hairline px-4 py-2">
      {STAGES.map((s, i) => (
        <span key={s} className="flex items-center gap-2">
          <span className="text-eyebrow font-bold uppercase tracking-wider text-ink-subtle">
            {s}
          </span>
          {i < STAGES.length - 1 && (
            <span className="text-eyebrow text-hairline-strong" aria-hidden="true">→</span>
          )}
        </span>
      ))}
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────

export default function HeroDebateConsole() {
  return (
    <motion.div
      role="img"
      aria-label="RoundLab product preview"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.08, ease: EASE }}
      className="relative w-full"
    >
      {/* Inner panel — aria-hidden; all children are decorative.
          Uses bg-surface-1 (solid) so Axe can compute contrast accurately.
          No inner motion.* to avoid partial-opacity state during Axe scans. */}
      <div
        aria-hidden="true"
        className="beam-top overflow-hidden rounded-2xl border border-hairline bg-surface-1"
        style={{
          boxShadow:
            "0 0 80px -20px oklch(0.510 0.156 278 / 0.25)," +
            "0 0 0 1px oklch(0.510 0.156 278 / 0.08)," +
            "0 28px 56px -12px oklch(0 0 0 / 0.28)",
          transform: "perspective(960px) rotateX(1.5deg) rotateY(-5deg)",
          transformStyle: "preserve-3d",
        }}
      >
        {/* ── Header ────────────────────────────────────────────────── */}
        <div className="flex items-center justify-between border-b border-hairline px-4 py-3">
          <div className="flex items-center gap-2">
            <div className="flex h-5 w-5 items-center justify-center rounded-md bg-lav">
              <Mic size={10} className="text-white" aria-hidden />
            </div>
            <span className="text-xs font-semibold text-ink">1AC · State Championship R4</span>
          </div>
          <span className="rounded-full border border-ok/25 bg-ok/10 px-2 py-0.5 text-eyebrow font-semibold text-ok">
            Analysis complete
          </span>
        </div>

        {/* ── Stage progress ─────────────────────────────────────────── */}
        <StageBar />

        {/* ── Top zone: Audio (left) + Argument chain (right) ───────── */}
        <div className="grid grid-cols-2 divide-x divide-hairline">

          {/* Audio */}
          <div className="flex flex-col gap-2 p-3">
            <p className="text-eyebrow font-semibold uppercase tracking-wider text-ink-subtle">
              Audio input
            </p>
            <StaticWaveform />
            <div className="mt-0.5 flex flex-wrap items-center gap-1">
              {["Pro", "Flow judge", "1:52"].map((chip) => (
                <span
                  key={chip}
                  className="rounded-full border border-hairline px-1.5 py-0.5 text-eyebrow text-ink-subtle"
                >
                  {chip}
                </span>
              ))}
            </div>
          </div>

          {/* Argument chain */}
          <div className="flex flex-col gap-2 p-3">
            <p className="text-eyebrow font-semibold uppercase tracking-wider text-ink-subtle">
              Argument flow
            </p>
            <div className="flex flex-wrap items-center gap-1">
              <ChainNode label="Claim"    status="ok"   />
              <span className="text-eyebrow text-ok/50"   aria-hidden="true">━</span>
              <ChainNode label="Warrant"  status="ok"   />
              <span className="text-eyebrow text-warn/40" aria-hidden="true">╌</span>
              <ChainNode label="Evidence" status="warn" />
              <span className="text-eyebrow text-ok/50"   aria-hidden="true">━</span>
              <ChainNode label="Impact"   status="ok"   />
            </div>
            <p className="text-eyebrow text-ink-subtle">
              C1: Economic Burden Shift · OFFENSE
            </p>
          </div>
        </div>

        {/* ── Issue row ─────────────────────────────────────────────── */}
        <div className="flex items-center gap-2 border-t border-warn/15 bg-warn/5 px-4 py-2">
          <span className="h-1 w-1 shrink-0 rounded-full bg-warn" />
          <span className="text-xs font-medium text-warn">No weighing detected — C1 vs. opponent</span>
          <span className="ml-auto rounded-full border border-warn/20 px-1.5 py-0.5 text-eyebrow text-ink-subtle">
            Judge note
          </span>
        </div>

        {/* ── Bottom zone: Ballot (left) + Drill (right) ─────────────── */}
        <div className="grid grid-cols-2 divide-x divide-hairline border-t border-hairline">

          {/* Judge ballot */}
          <div className="flex flex-col gap-2.5 p-3">
            <p className="text-eyebrow font-semibold uppercase tracking-wider text-ink-subtle">
              Judge ballot
            </p>
            <div className="flex items-center gap-2.5">
              <div className="relative flex h-12 w-12 shrink-0 flex-col items-center justify-center rounded-full border-2 border-lav bg-canvas">
                <span className="text-lg font-bold tabular-nums leading-none text-ink">78</span>
                <span className="text-eyebrow leading-none text-ink-subtle">/100</span>
              </div>
              <div className="flex flex-col gap-0">
                <span className="text-eyebrow font-semibold text-ink">Developing</span>
                <span className="text-eyebrow text-ink-subtle">Flow judge</span>
              </div>
            </div>
            <div className="flex flex-col gap-1">
              <BallotBar label="Clash"    value={14} max={20} />
              <BallotBar label="Weighing" value={9}  max={20} />
              <BallotBar label="Coverage" value={16} max={20} />
            </div>
          </div>

          {/* Drill unlocked */}
          <div className="flex flex-col gap-2.5 p-3">
            <p className="text-eyebrow font-semibold uppercase tracking-wider text-ink-subtle">
              Drill unlocked
            </p>
            <div className="flex items-start gap-2">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-lav">
                <Zap size={13} className="text-white" aria-hidden />
              </div>
              <div className="flex flex-col gap-0.5">
                <p className="text-xs font-semibold leading-snug text-ink">Weighing Sprint</p>
                <p className="text-eyebrow text-ink-subtle">Impact Weighing · 90s</p>
              </div>
            </div>
            <p className="text-xs leading-relaxed text-ink-subtle">
              Compare magnitude, probability, and timeframe against opponent offense.
            </p>
            <div className="mt-auto flex items-center gap-1.5 rounded-md border border-lav/25 bg-lav/8 px-2 py-1.5">
              <Zap size={9} className="text-lav" aria-hidden />
              <span className="text-eyebrow font-semibold text-ink">Start weighing drill</span>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
