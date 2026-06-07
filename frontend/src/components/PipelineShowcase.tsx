"use client";

/**
 * PipelineShowcase — Horizontal walkthrough board.
 *
 * Five stages laid out left-to-right:
 *   Audio → Transcript → Flow → Ballot → Drill
 *
 * A connected stage rail at the top (desktop) shows which stage is active.
 * Content cards below fill in progressively.
 * One-shot reveal — no looping, no floating chips.
 */

import { useEffect, useRef, useState } from "react";
import { motion } from "motion/react";
import { BarChart3, Check, FileText, GitBranch, Mic, Zap } from "lucide-react";
import { EASE } from "@/lib/motion";

// ── Waveform ───────────────────────────────────────────────────────────────────

const BARS = [4, 10, 16, 8, 20, 14, 6, 18, 12, 7, 15, 11, 5, 17, 9, 13, 4, 19, 8, 14];

function Waveform({ active }: { active: boolean }) {
  return (
    <div className="flex items-end gap-0.5" style={{ height: 40 }}>
      {BARS.map((h, i) => (
        <motion.div
          key={i}
          className="w-0.5 rounded-full bg-lav"
          animate={
            active
              ? { height: [h * 1.1, h * 0.4, h * 1.1], opacity: [0.65, 1, 0.65] }
              : { height: h * 0.65, opacity: 0.35 }
          }
          transition={{
            duration: 0.9 + (i % 4) * 0.15,
            repeat: active ? Infinity : 0,
            repeatType: "mirror",
            delay: i * 0.03,
            ease: "easeInOut",
          }}
          style={{ minHeight: 2 }}
        />
      ))}
    </div>
  );
}

// ── Score bar ──────────────────────────────────────────────────────────────────

function ScoreBar({
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
          transition={{ duration: 0.65, delay, ease: EASE }}
        />
      </div>
      <span className="w-4 shrink-0 text-right text-[9px] tabular-nums text-ink-faint">{value}</span>
    </div>
  );
}

// ── Stage metadata (icon + label only — no state) ──────────────────────────────

type StageIcon = React.ComponentType<{ size?: number; className?: string }>;

interface StageMeta { icon: StageIcon; label: string; }

const STAGES: StageMeta[] = [
  { icon: Mic,       label: "Audio"      },
  { icon: FileText,  label: "Transcript" },
  { icon: GitBranch, label: "Flow"       },
  { icon: BarChart3, label: "Ballot"     },
  { icon: Zap,       label: "Drill"      },
];

// ── Main component ─────────────────────────────────────────────────────────────

interface PipelineShowcaseProps {
  autoPlay?: boolean;
  stageMs?: number;
  /**
   * When false (default), stages do not advance automatically.
   * Set to true once the section is in view to begin the one-shot reveal.
   * Defaults to true for backward compatibility when used outside page.tsx.
   */
  start?: boolean;
}

export default function PipelineShowcase({
  autoPlay = true,
  stageMs  = 2200,
  start    = true,
}: PipelineShowcaseProps) {
  const [activeStage, setActiveStage] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!autoPlay || !start) return;

    intervalRef.current = setInterval(() => {
      setActiveStage((prev) => {
        const next = Math.min(prev + 1, 4);
        // Stop advancing once we reach the final stage
        if (next === 4 && intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
        return next;
      });
    }, stageMs);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [autoPlay, stageMs, start]);

  // ── Stage content (defined inside component so it can reference activeStage) ─

  const stageContent: React.ReactNode[] = [

    /* 0 · Audio */
    <div key="audio" className="flex flex-col gap-2">
      <Waveform active={activeStage === 0} />
      <div className="flex flex-wrap items-center gap-1 pt-1">
        {["1AC", "Pro", "Flow judge", "1:52"].map((chip) => (
          <span key={chip} className="rounded-full border border-hairline px-1.5 py-0.5 text-[8px] text-ink-faint">
            {chip}
          </span>
        ))}
      </div>
    </div>,

    /* 1 · Transcript */
    <div key="tx" className="flex flex-col gap-1.5">
      {[
        "Status quo tariffs impose $4.2T in costs on developing nations.",
        "IMF confirms barrier reduction lifts GDP by 1.2% globally.",
        "Our second contention is poverty…",
      ].map((line, i) => (
        <div key={i} className="flex gap-1.5">
          <span className="mt-0.5 shrink-0 font-mono text-[8px] text-ink-faint">
            {String(i + 1).padStart(2, "0")}
          </span>
          <p className="text-[9px] leading-relaxed text-ink-muted">{line}</p>
        </div>
      ))}
    </div>,

    /* 2 · Flow */
    <div key="flow" className="flex flex-col gap-1.5">
      <div className="flex items-center gap-1.5">
        <span className="rounded bg-ok/15 px-1 py-0.5 text-[7px] font-bold text-ok">OFFENSE</span>
        <span className="text-[9px] font-semibold text-ink">C1: Burden Shift</span>
      </div>
      {([
        { l: "Claim",    ok: true,  t: "Tariffs impose $4.2T cost." },
        { l: "Warrant",  ok: true,  t: "Barriers reduce GDP." },
        { l: "Evidence", ok: false, t: "IMF (2023): 1.2% reduction." },
        { l: "Impact",   ok: true,  t: "Less funding for healthcare." },
      ] as const).map(({ l, ok, t }) => (
        <div key={l} className="flex items-start gap-1.5">
          <span className={`shrink-0 rounded px-1 py-0.5 text-[7px] font-bold uppercase leading-none ${
            ok ? "bg-surface-3 text-ink-faint" : "bg-warn/15 text-warn"
          }`}>
            {l}{!ok && " ⚠"}
          </span>
          <p className="text-[9px] leading-relaxed text-ink-muted line-clamp-2">{t}</p>
        </div>
      ))}
      <div className="flex items-center gap-1 rounded border border-warn/20 bg-warn/5 px-1.5 py-1">
        <span className="text-[8px] font-medium text-warn">No weighing — judge note</span>
      </div>
    </div>,

    /* 3 · Ballot */
    <div key="ballot" className="flex flex-col gap-2">
      <div className="flex items-center justify-between gap-2">
        <div>
          <p className="text-[8px] text-ink-faint">Overall</p>
          <p className="text-2xl font-bold tabular-nums leading-none text-ink">78</p>
        </div>
        <div className="flex flex-col items-end gap-0.5">
          <span className="rounded-full border border-lav/25 bg-lav/10 px-1.5 py-0.5 text-[8px] font-semibold text-lav">
            Developing
          </span>
          <span className="text-[8px] text-ink-faint">Flow judge</span>
        </div>
      </div>
      <div className="flex flex-col gap-1">
        {[
          { label: "Clash",    value: 14, max: 20 },
          { label: "Weighing", value:  9, max: 20 },
          { label: "Coverage", value: 16, max: 20 },
        ].map((s, i) => (
          <ScoreBar key={s.label} {...s} delay={activeStage >= 3 ? 0.15 + i * 0.12 : 0} />
        ))}
      </div>
    </div>,

    /* 4 · Drill */
    <div key="drill" className="flex flex-col gap-2">
      <div className="flex items-start gap-2">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-lav">
          <Zap size={13} className="text-white" />
        </div>
        <div>
          <p className="text-[10px] font-semibold leading-snug text-ink">Weighing Sprint</p>
          <p className="text-[9px] text-ink-faint">Impact Weighing · 90s</p>
        </div>
      </div>
      <p className="text-[9px] leading-relaxed text-ink-muted">
        Compare magnitude, probability, and timeframe against opponent offense.
      </p>
      <div className="flex items-center gap-1.5 rounded-md border border-lav/25 bg-lav/8 px-2 py-1.5">
        <Zap size={9} className="text-lav" />
        <span className="text-[9px] font-semibold text-lav">Start drill → 50 XP</span>
      </div>
    </div>,

  ];

  return (
    <div className="flex flex-col gap-5">

      {/* ── Stage rail (desktop only) ─────────────────────────────────── */}
      <div className="relative hidden lg:block">
        {/* Static track */}
        <div className="absolute left-[10%] right-[10%] top-[10px] h-px bg-hairline" />
        {/* Animated progress fill */}
        <motion.div
          className="absolute left-[10%] top-[10px] h-px bg-lav/50"
          animate={{ width: `${activeStage * 20}%` }}
          transition={{ duration: 0.55, ease: EASE }}
        />
        {/* Dots + labels row */}
        <div className="grid grid-cols-5">
          {STAGES.map(({ icon: Icon, label }, i) => {
            const isDone   = activeStage > i;
            const isActive = activeStage === i;
            return (
              <div key={i} className="flex flex-col items-center gap-1.5">
                <div className={`relative z-10 flex h-5 w-5 items-center justify-center rounded-full border bg-canvas transition-colors duration-500 ${
                  isDone   ? "border-lav bg-lav"
                  : isActive ? "border-lav/60 bg-lav/10"
                  :            "border-hairline"
                }`}>
                  {isDone
                    ? <Check size={8} strokeWidth={2.5} className="text-white" />
                    : <Icon  size={8} className={isActive ? "text-lav" : "text-ink-faint"} />
                  }
                </div>
                <span className={`text-[9px] font-semibold uppercase tracking-wider ${
                  isActive ? "text-lav" : isDone ? "text-ink-subtle" : "text-ink-faint"
                }`}>
                  {String(i + 1).padStart(2, "0")} · {label}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Content grid ────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {STAGES.map(({ icon: Icon, label }, i) => {
          const isDone   = activeStage > i;
          const isActive = activeStage === i;
          const visible  = isDone || isActive;
          return (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: visible ? 1 : 0.22, y: 0 }}
              transition={{ duration: 0.4, delay: i * 0.06, ease: EASE }}
              className={`flex flex-col gap-2.5 rounded-xl border p-3 transition-colors duration-500 ${
                isActive ? "border-lav/25 bg-lav/5"
                : isDone  ? "border-hairline bg-surface-2"
                :           "border-hairline/40 bg-surface-1"
              }`}
            >
              {/* Mobile stage header (hidden on lg — rail shows it there) */}
              <div className="flex items-center gap-1.5 lg:hidden">
                <div className={`flex h-4 w-4 shrink-0 items-center justify-center rounded-full border transition-colors duration-300 ${
                  isDone   ? "border-lav bg-lav"
                  : isActive ? "border-lav/50 bg-lav/8"
                  :            "border-hairline"
                }`}>
                  {isDone
                    ? <Check size={7} strokeWidth={2.5} className="text-white" />
                    : <Icon  size={7} className={isActive ? "text-lav" : "text-ink-faint"} />
                  }
                </div>
                <span className={`text-[9px] font-semibold uppercase tracking-wide ${
                  isActive ? "text-lav" : isDone ? "text-ink-subtle" : "text-ink-faint"
                }`}>
                  {String(i + 1).padStart(2, "0")} · {label}
                </span>
              </div>

              {/* Stage content */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: visible ? 1 : 0 }}
                transition={{ duration: 0.35, delay: i * 0.06 + 0.1, ease: EASE }}
              >
                {stageContent[i]}
              </motion.div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
