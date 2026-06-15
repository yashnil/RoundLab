"use client";

/**
 * /demo — Isolated product showcase using fixture data only.
 *
 * Shows the full RoundLab loop:
 *   speech metadata → transcript → flow board → judge ballot →
 *   structured issues → assigned drills → re-record comparison
 *
 * No API calls. No auth required. Data is NEVER saved to any user account.
 * Clearly labeled as demo throughout.
 */

import { useState } from "react";
import Link from "next/link";
import { motion } from "motion/react";
import {
  AlertCircle, ArrowRight, CheckSquare, ChevronDown, ChevronUp,
  FileText, FlaskConical, Target, ThumbsUp, TrendingUp,
} from "lucide-react";
import AppShell from "@/components/shell/AppShell";
import FlowBoard from "@/components/FlowBoard";
import { fadeUp, EASE } from "@/lib/motion";
import {
  SAMPLE_SPEECH_V2,
  SAMPLE_FEEDBACK_V2,
  SAMPLE_DRILLS_V2,
  SAMPLE_TRANSCRIPT_V1 as SAMPLE_TRANSCRIPT,
  SAMPLE_ARGUMENT_MAP_V1,
} from "@/lib/fixtures";
import { logEvent } from "@/lib/analytics";

// ── Constants ─────────────────────────────────────────────────────────────────

const SKILL_LABEL: Record<string, string> = {
  weighing: "Impact Weighing", warranting: "Warranting",
  drops: "Drop Prevention", extensions: "Extensions",
  evidence: "Evidence Use", clash: "Clash",
  judge_adaptation: "Judge Adaptation",
};

const ISSUE_SEVERITY_COLOR: Record<string, string> = {
  high:   "text-danger border-danger/20 bg-danger/5",
  medium: "text-warn   border-warn/20   bg-warn/5",
  low:    "text-ok     border-ok/20     bg-ok/5",
};

// ── Small helpers ─────────────────────────────────────────────────────────────

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <span className="section-stamp">{children}</span>
    </div>
  );
}

function HelpNote({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <button
      type="button"
      onClick={() => setOpen((v) => !v)}
      className="flex items-start gap-1.5 text-left w-full group"
    >
      <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border border-lav/30 text-[9px] font-bold text-lav">?</span>
      <span className={`text-[11px] text-ink-faint leading-relaxed ${open ? "" : "line-clamp-1"} group-hover:text-ink-subtle transition-colors`}>
        {children}
      </span>
      <span className="shrink-0 mt-0.5 text-ink-faint">
        {open ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
      </span>
    </button>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function DemoPage() {
  const speech   = SAMPLE_SPEECH_V2;
  const feedback = SAMPLE_FEEDBACK_V2;
  const drills   = SAMPLE_DRILLS_V2;
  const argMap   = SAMPLE_ARGUMENT_MAP_V1;
  const issues   = (feedback.raw_feedback?.structured_issues as Array<{
    issue_type: string; severity: string; title: string;
    explanation: string; recommendation: string; recommended_drill_type: string;
  }> | undefined) ?? [];

  return (
    <AppShell maxWidth="full" bare>
        <div className="mx-auto flex max-w-3xl flex-col gap-7 px-4 py-8 sm:px-6">

          {/* ── Demo banner ──────────────────────────────────────────────── */}
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, ease: EASE }}
            className="flex items-start gap-3 rounded-lg border border-lav/20 bg-lav/5 px-4 py-3"
          >
            <FlaskConical size={14} className="shrink-0 text-lav mt-0.5" />
            <div className="flex flex-col gap-1 flex-1">
              <p className="text-xs font-semibold text-ink">Demo mode — sample data only</p>
              <p className="text-xs text-ink-subtle leading-relaxed">
                This is a static example of what RoundLab generates. No audio was recorded and no data is saved to any account.
              </p>
            </div>
            <Link
              href="/session"
              onClick={() => logEvent("demo_start_own_speech_clicked")}
              className="shrink-0 flex items-center gap-1 rounded-md bg-lav px-2.5 py-1 text-xs font-semibold text-white hover:opacity-90 transition-opacity"
            >
              Try real
              <ArrowRight size={10} />
            </Link>
          </motion.div>

          {/* ── Speech header ─────────────────────────────────────────────── */}
          <motion.div {...fadeUp(0)} className="flex flex-col gap-2">
            <p className="section-stamp">Step 1 — Speech</p>
            <h1 className="text-title text-ink">{speech.title}</h1>
            <div className="flex flex-wrap items-center gap-2">
              {[speech.speech_type, speech.side, speech.judge_type && `${speech.judge_type} judge`]
                .filter(Boolean)
                .map((chip) => (
                  <span key={chip as string} className="rounded-full border border-hairline bg-surface-2 px-2.5 py-1 text-xs font-medium capitalize text-ink-subtle">
                    {chip}
                  </span>
                ))}
            </div>
            {speech.topic && (
              <p className="text-xs text-ink-faint">
                <span className="font-medium text-ink-subtle">Resolution: </span>{speech.topic}
              </p>
            )}
          </motion.div>

          {/* ── Transcript excerpt ─────────────────────────────────────────── */}
          <motion.div {...fadeUp(0.04)} className="flex flex-col gap-2">
            <SectionLabel>Step 2 — Transcript</SectionLabel>
            <div className="rounded-xl border border-hairline bg-surface-1 px-4 py-3">
              <p className="line-clamp-4 text-sm leading-relaxed text-ink-muted">
                {SAMPLE_TRANSCRIPT.text}
              </p>
            </div>
            <p className="text-[11px] text-ink-faint">{SAMPLE_TRANSCRIPT.word_count} words · transcribed via Whisper</p>
          </motion.div>

          {/* ── Flow board ────────────────────────────────────────────────── */}
          <motion.div {...fadeUp(0.07)} className="flex flex-col gap-3">
            <SectionLabel>Step 3 — Argument Flow</SectionLabel>
            <HelpNote>
              The flow maps each argument into claim → warrant → evidence → impact. A flow judge reads this to decide who won each contention. Debate coaches call this the "flow sheet."
            </HelpNote>
            <div className="rounded-xl border border-hairline bg-surface-1 overflow-hidden">
              <div className="px-4 py-3 border-b border-hairline bg-surface-2">
                <p className="text-xs font-medium text-ink-subtle">
                  {argMap.arguments.length} arguments extracted
                </p>
              </div>
              <div className="p-3">
                <FlowBoard args={argMap.arguments} judgeMode="flow" />
              </div>
            </div>
          </motion.div>

          {/* ── Judge ballot / scores ──────────────────────────────────────── */}
          <motion.div {...fadeUp(0.10)} className="flex flex-col gap-3">
            <SectionLabel>Step 4 — Judge Ballot</SectionLabel>
            <HelpNote>
              The ballot scores five debate dimensions on a /20 scale. A flow judge focuses on clash, weighing, and drops. A lay judge cares most about judge adaptation and impact clarity.
            </HelpNote>
            <div className="grid grid-cols-3 gap-2.5 sm:grid-cols-5">
              {[
                { label: "Overall",  value: feedback.overall_score ?? 0, max: 100 },
                { label: "Clash",    value: feedback.scores.clash,            max: 20 },
                { label: "Weighing", value: feedback.scores.weighing,         max: 20 },
                { label: "Drops",    value: feedback.scores.drops,            max: 20 },
                { label: "Judge",    value: feedback.scores.judge_adaptation, max: 20 },
              ].map((s) => {
                const pct = (s.value / s.max) * 100;
                const color = pct >= 70 ? "text-ok" : pct >= 50 ? "text-warn" : "text-danger";
                return (
                  <div key={s.label} className="flex flex-col items-center gap-0.5 rounded-xl border border-hairline bg-surface-1 py-3">
                    <span className={`text-xl font-bold tabular-nums ${color}`}>{s.value}</span>
                    <span className="text-[9px] text-ink-faint">/{s.max}</span>
                    <span className="text-[10px] text-ink-subtle">{s.label}</span>
                  </div>
                );
              })}
            </div>

            {/* Coach ballot summary */}
            {feedback.summary && (
              <div className="rounded-xl border border-lav/20 bg-lav/5 px-5 py-4">
                <p className="mb-1 text-eyebrow text-lav">Coach ballot</p>
                <p className="text-sm leading-relaxed text-ink">{feedback.summary}</p>
              </div>
            )}
          </motion.div>

          {/* ── Structured coaching issues ─────────────────────────────────── */}
          {issues.length > 0 && (
            <motion.div {...fadeUp(0.13)} className="flex flex-col gap-3">
              <SectionLabel>Round-losing issues</SectionLabel>
              <HelpNote>
                These are the specific debate problems that would cost you the round in front of this judge type. Each issue has a severity, explanation, and a recommended drill.
              </HelpNote>
              {issues.map((issue, i) => (
                <div
                  key={i}
                  className={`flex flex-col gap-2 rounded-xl border p-4 ${ISSUE_SEVERITY_COLOR[issue.severity] ?? "border-hairline bg-surface-1"}`}
                >
                  <div className="flex items-start gap-2">
                    <AlertCircle size={13} className="mt-0.5 shrink-0" />
                    <div>
                      <p className="text-xs font-semibold text-ink">{issue.title}</p>
                      <p className="mt-0.5 text-xs text-ink-subtle">{issue.explanation}</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-2 pl-5">
                    <ThumbsUp size={11} className="mt-0.5 shrink-0 text-ok" />
                    <p className="text-xs text-ink-muted">{issue.recommendation}</p>
                  </div>
                </div>
              ))}
            </motion.div>
          )}

          {/* ── Assigned drills ────────────────────────────────────────────── */}
          <motion.div {...fadeUp(0.16)} className="flex flex-col gap-3">
            <SectionLabel>Step 5 — Assigned Drills</SectionLabel>
            <HelpNote>
              Drills are short practice exercises targeting one specific weakness identified in your speech. Each drill has a prompt, success criteria, and a time limit. You record yourself doing the exercise.
            </HelpNote>
            {drills.slice(0, 2).map((drill, i) => (
              <div key={drill.id} className="flex flex-col gap-2 rounded-xl border border-hairline bg-surface-1 p-4">
                <div className="flex items-center gap-2">
                  <span className="flex h-5 w-5 items-center justify-center rounded-full bg-lav text-[10px] font-bold text-white">
                    {i + 1}
                  </span>
                  <p className="text-sm font-semibold text-ink">{drill.title}</p>
                  <span className="ml-auto rounded-full border border-hairline bg-surface-2 px-2 py-0.5 text-[10px] text-ink-faint">
                    {SKILL_LABEL[drill.skill_target] ?? drill.skill_target}
                  </span>
                </div>
                <div className="rounded-lg border border-lav/15 bg-lav/5 px-3 py-2">
                  <div className="mb-1 flex items-center gap-1">
                    <Target size={10} className="text-lav" />
                    <span className="text-[10px] font-semibold text-lav">Exercise prompt</span>
                  </div>
                  <p className="text-xs leading-relaxed text-ink">{drill.prompt}</p>
                </div>
                {drill.success_criteria.length > 0 && (
                  <ul className="flex flex-col gap-1">
                    {drill.success_criteria.slice(0, 2).map((c, j) => (
                      <li key={j} className="flex items-center gap-2 text-xs text-ink-muted">
                        <CheckSquare size={10} className="shrink-0 text-ink-faint" />
                        {c}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </motion.div>

          {/* ── Evidence support example ───────────────────────────────────── */}
          <motion.div {...fadeUp(0.19)} className="flex flex-col gap-3">
            <SectionLabel>Evidence support (optional feature)</SectionLabel>
            <HelpNote>
              If you upload a case file, RoundLab checks whether your speech evidence actually appears in your uploaded cards. This is only compared to your own files — not outside knowledge.
            </HelpNote>
            <div className="rounded-xl border border-hairline bg-surface-1 p-4 flex flex-col gap-3">
              {[
                { label: "C1: Economic Growth", level: "supported",           color: "text-ok    border-ok/20    bg-ok/5"   },
                { label: "C2: Poverty Reduction", level: "partially_supported", color: "text-warn  border-warn/20  bg-warn/5" },
              ].map((row) => (
                <div key={row.label} className={`flex items-center justify-between gap-3 rounded-lg border px-3 py-2 ${row.color}`}>
                  <div className="flex items-center gap-2">
                    <FileText size={11} className="shrink-0" />
                    <span className="text-xs font-medium text-ink">{row.label}</span>
                  </div>
                  <span className="text-[10px] font-semibold capitalize">{row.level.replace("_", " ")}</span>
                </div>
              ))}
              <p className="text-[11px] text-ink-faint">
                Evidence checks only use your uploaded files. Upload a case file from{" "}
                <Link href="/evidence" className="text-lav hover:underline">Evidence Library →</Link>
              </p>
            </div>
          </motion.div>

          {/* ── Re-record comparison ───────────────────────────────────────── */}
          <motion.div
            {...fadeUp(0.22)}
            className="rounded-2xl border border-ok/20 bg-ok/5 p-5"
            style={{ boxShadow: "0 0 32px -12px oklch(0.620 0.170 145 / 0.12)" }}
          >
            <SectionLabel>Step 6 — Re-record Comparison</SectionLabel>
            <div className="flex items-center gap-2.5 mb-4">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-ok/15">
                <TrendingUp size={15} className="text-ok" />
              </div>
              <div>
                <p className="text-sm font-semibold text-ink">After drill practice — score comparison</p>
                <p className="text-xs text-ink-faint">Sample data showing what the comparison looks like</p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-1">
                <p className="text-[10px] font-medium uppercase tracking-wide text-ink-faint">Overall score</p>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-ink-subtle">62/100</span>
                  <ArrowRight size={12} className="text-ink-faint" />
                  <span className="text-sm font-bold text-ink">70/100</span>
                  <span className="inline-flex items-center gap-0.5 rounded-full border border-ok/20 bg-ok/10 px-2 py-0.5 text-[11px] font-semibold text-ok">
                    <TrendingUp size={9} />+8
                  </span>
                </div>
              </div>
              <div className="flex flex-col gap-1">
                <p className="text-[10px] font-medium uppercase tracking-wide text-ink-faint">Targeted: Weighing</p>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-ink-subtle">9/20</span>
                  <ArrowRight size={12} className="text-ink-faint" />
                  <span className="text-sm font-bold text-ink">13/20</span>
                  <span className="inline-flex items-center gap-0.5 rounded-full border border-ok/20 bg-ok/10 px-2 py-0.5 text-[11px] font-semibold text-ok">
                    <TrendingUp size={9} />+4
                  </span>
                </div>
              </div>
            </div>
            <div className="mt-3 rounded-lg border border-ok/15 bg-ok/10 px-3 py-2">
              <p className="text-xs text-ink">
                Strong improvement — overall score up 8 points. Weighing score also improved by 4 points. This is what completing one drill cycle looks like.
              </p>
            </div>
          </motion.div>

          {/* ── Sample speech types ────────────────────────────────────────── */}
          <motion.div {...fadeUp(0.25)} className="flex flex-col gap-3">
            <SectionLabel>Sample speech starters</SectionLabel>
            <p className="text-xs text-ink-faint -mt-1">Not sure what to record? These are common PF openings to practice with.</p>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
              {[
                { label: "Constructive (1AC)",  hint: "Your opening 4-minute case — claim + warrant + evidence + impact for 2 contentions." },
                { label: "Rebuttal (2NC/1NR)",  hint: "3 minutes attacking the other team's arguments and defending your case." },
                { label: "Summary (2nd summary)", hint: "2 minutes crystallizing your winning arguments and extending key impacts." },
              ].map((t) => (
                <Link
                  key={t.label}
                  href="/session"
                  onClick={() => logEvent("demo_start_own_speech_clicked")}
                  className="flex flex-col gap-1.5 rounded-xl border border-hairline bg-surface-1 p-3 hover:border-lav/30 hover:bg-lav/5 transition-colors group"
                >
                  <p className="text-xs font-semibold text-ink group-hover:text-lav transition-colors">{t.label}</p>
                  <p className="text-[11px] text-ink-faint leading-relaxed">{t.hint}</p>
                  <span className="text-[10px] text-lav font-medium mt-auto">Practice this →</span>
                </Link>
              ))}
            </div>
          </motion.div>

          {/* ── CTAs ──────────────────────────────────────────────────────── */}
          <motion.div {...fadeUp(0.28)} className="flex flex-wrap gap-3">
            <Link
              href="/session"
              onClick={() => logEvent("demo_start_own_speech_clicked")}
              className="flex items-center gap-1.5 rounded-md bg-lav px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:opacity-90"
            >
              Start your own speech
              <ArrowRight size={13} />
            </Link>
            <Link
              href="/evidence"
              className="flex items-center gap-1.5 rounded-md border border-hairline px-5 py-2.5 text-sm font-medium text-ink-subtle transition-colors hover:border-lav/30 hover:text-ink"
            >
              Upload evidence
            </Link>
            <Link
              href="/dashboard"
              className="flex items-center gap-1.5 rounded-md border border-hairline px-5 py-2.5 text-sm font-medium text-ink-subtle transition-colors hover:border-hairline-strong hover:text-ink"
            >
              Back to dashboard
            </Link>
          </motion.div>

        </div>
    </AppShell>
  );
}
