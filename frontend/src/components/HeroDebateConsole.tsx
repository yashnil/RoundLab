"use client";

/**
 * HeroDebateConsole — Compact 2.5D product graphic for the landing hero.
 *
 * Shows the full product loop at a glance:
 *   Audio → Argument Flow → Judge Ballot → Drill
 *
 * Fits in the first fold. Uses perspective CSS for a 2.5D feel.
 * All animations are one-shot entrances — nothing loops.
 * The "No weighing" issue is embedded as a normal issue row, not a floating chip.
 */

import { Fragment } from "react";
import { motion } from "motion/react";
import { Mic, Zap } from "lucide-react";
import { EASE } from "@/lib/motion";

// ── Static waveform ────────────────────────────────────────────────────────────

const WAVE = [5, 9, 14, 8, 20, 13, 6, 18, 11, 5, 16, 10, 4, 17, 7, 12, 9, 15, 6, 11];

function StaticWaveform() {
  return (
    <div className="flex items-end gap-0.5" aria-hidden>
      {WAVE.map((h, i) => (
        <motion.div
          key={i}
          className="w-1 shrink-0 rounded-full bg-lav"
          initial={{ height: 2, opacity: 0 }}
          animate={{ height: h * 1.5, opacity: 0.25 + (h / 20) * 0.65 }}
          transition={{ duration: 0.35, delay: 0.4 + i * 0.022, ease: EASE }}
          style={{ minHeight: 2 }}
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
      <span className="block text-[8px] font-bold uppercase leading-none tracking-wide">
        {label}
        {status === "warn" && " ⚠"}
      </span>
    </span>
  );
}

// ── Ballot bar ─────────────────────────────────────────────────────────────────

function BallotBar({
  label, value, max, delay,
}: { label: string; value: number; max: number; delay: number }) {
  const pct   = Math.round((value / max) * 100);
  const color = value < 12 ? "bg-warn" : "bg-lav";
  return (
    <div className="flex items-center gap-1.5">
      <span className="w-14 shrink-0 text-[9px] text-ink-faint">{label}</span>
      <div className="h-0.5 flex-1 overflow-hidden rounded-full bg-hairline">
        <motion.div
          className={`h-full rounded-full ${color}`}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.55, delay, ease: EASE }}
        />
      </div>
      <span className="w-4 shrink-0 text-right text-[9px] tabular-nums text-ink-faint">{value}</span>
    </div>
  );
}

// ── Stage progress strip ───────────────────────────────────────────────────────

const STAGES = ["Audio", "Flow", "Ballot", "Drill"] as const;

function StageBar() {
  return (
    <div className="flex items-center justify-between border-b border-hairline px-4 py-2">
      {STAGES.map((s, i) => (
        <Fragment key={s}>
          <motion.span
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.15 + i * 0.10, duration: 0.3 }}
            className="text-[9px] font-bold uppercase tracking-wider text-lav"
          >
            {s}
          </motion.span>
          {i < STAGES.length - 1 && (
            <motion.span
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.20 + i * 0.10, duration: 0.3 }}
              className="text-[10px] text-hairline-strong"
              aria-hidden
            >
              →
            </motion.span>
          )}
        </Fragment>
      ))}
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────

export default function HeroDebateConsole() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.08, ease: EASE }}
      className="relative w-full"
      aria-label="RoundLab product preview"
    >
      {/* 2.5D outer panel — perspective tilt on lg+ screens */}
      <div
        className="beam-top overflow-hidden rounded-2xl border border-hairline bg-surface-1/95 backdrop-blur-sm"
        style={{
          boxShadow:
            "0 0 80px -20px oklch(0.510 0.156 278 / 0.25)," +
            "0 0 0 1px oklch(0.510 0.156 278 / 0.08)," +
            "0 28px 56px -12px oklch(0 0 0 / 0.28)",
          // Subtle 2.5D tilt — gives depth without Three.js
          // transform applied via CSS so reduced-motion doesn't block it (it's static)
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
          <span className="rounded-full border border-ok/25 bg-ok/10 px-2 py-0.5 text-[10px] font-semibold text-ok">
            Analysis complete
          </span>
        </div>

        {/* ── Stage progress ─────────────────────────────────────────── */}
        <StageBar />

        {/* ── Top zone: Audio (left) + Argument chain (right) ───────── */}
        <div className="grid grid-cols-2 divide-x divide-hairline">

          {/* Audio */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.38, duration: 0.4 }}
            className="flex flex-col gap-2 p-3"
          >
            <p className="text-[9px] font-semibold uppercase tracking-wider text-lav">Audio input</p>
            <StaticWaveform />
            <div className="mt-0.5 flex flex-wrap items-center gap-1">
              {["Pro", "Flow judge", "1:52"].map((chip) => (
                <span
                  key={chip}
                  className="rounded-full border border-hairline px-1.5 py-0.5 text-[8px] text-ink-faint"
                >
                  {chip}
                </span>
              ))}
            </div>
          </motion.div>

          {/* Argument chain */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.50, duration: 0.4 }}
            className="flex flex-col gap-2 p-3"
          >
            <p className="text-[9px] font-semibold uppercase tracking-wider text-lav">Argument flow</p>
            {/* Chain strip: Claim ━ Warrant ━ Evidence⚠ ━ Impact */}
            <div className="flex flex-wrap items-center gap-1">
              <ChainNode label="Claim"    status="ok"   />
              <span className="text-[8px] text-ok/50"    aria-hidden>━</span>
              <ChainNode label="Warrant"  status="ok"   />
              <span className="text-[8px] text-warn/40"  aria-hidden>╌</span>
              <ChainNode label="Evidence" status="warn" />
              <span className="text-[8px] text-ok/50"    aria-hidden>━</span>
              <ChainNode label="Impact"   status="ok"   />
            </div>
            <p className="text-[9px] leading-relaxed text-ink-faint">
              C1: Economic Burden Shift · OFFENSE
            </p>
          </motion.div>
        </div>

        {/* ── Issue row — embedded, not floating ─────────────────────── */}
        <motion.div
          initial={{ opacity: 0, x: -6 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.68, duration: 0.35 }}
          className="flex items-center gap-2 border-t border-warn/15 bg-warn/5 px-4 py-2"
        >
          <span className="h-1 w-1 shrink-0 rounded-full bg-warn" aria-hidden />
          <span className="text-[10px] font-medium text-warn">No weighing detected — C1 vs. opponent</span>
          <span className="ml-auto rounded-full border border-warn/20 px-1.5 py-0.5 text-[9px] text-warn/70">
            Judge note
          </span>
        </motion.div>

        {/* ── Bottom zone: Ballot (left) + Drill (right) ─────────────── */}
        <div className="grid grid-cols-2 divide-x divide-hairline border-t border-hairline">

          {/* Judge ballot */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.58, duration: 0.4 }}
            className="flex flex-col gap-2.5 p-3"
          >
            <p className="text-[9px] font-semibold uppercase tracking-wider text-lav">Judge ballot</p>
            <div className="flex items-center gap-2.5">
              {/* Score ring */}
              <div className="relative flex h-12 w-12 shrink-0 flex-col items-center justify-center rounded-full border-2 border-lav bg-canvas">
                <span className="text-lg font-bold tabular-nums leading-none text-ink">78</span>
                <span className="text-[8px] leading-none text-ink-faint">/100</span>
              </div>
              <div className="flex flex-col gap-0">
                <span className="text-[10px] font-semibold text-lav">Developing</span>
                <span className="text-[9px] text-ink-faint">Flow judge</span>
              </div>
            </div>
            <div className="flex flex-col gap-1">
              <BallotBar label="Clash"    value={14} max={20} delay={0.78} />
              <BallotBar label="Weighing" value={9}  max={20} delay={0.88} />
              <BallotBar label="Coverage" value={16} max={20} delay={0.98} />
            </div>
          </motion.div>

          {/* Drill unlocked */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.72, duration: 0.4 }}
            className="flex flex-col gap-2.5 p-3"
          >
            <p className="text-[9px] font-semibold uppercase tracking-wider text-lav">Drill unlocked</p>
            <div className="flex items-start gap-2">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-lav">
                <Zap size={13} className="text-white" aria-hidden />
              </div>
              <div className="flex flex-col gap-0.5">
                <p className="text-[10px] font-semibold leading-snug text-ink">Weighing Sprint</p>
                <p className="text-[9px] text-ink-faint">Impact Weighing · 90s</p>
              </div>
            </div>
            <p className="text-[10px] leading-relaxed text-ink-muted">
              Compare magnitude, probability, and timeframe against opponent offense.
            </p>
            <div className="mt-auto flex items-center gap-1.5 rounded-md border border-lav/25 bg-lav/8 px-2 py-1.5">
              <Zap size={9} className="text-lav" aria-hidden />
              <span className="text-[9px] font-semibold text-lav">Start weighing drill</span>
            </div>
          </motion.div>
        </div>
      </div>
    </motion.div>
  );
}
