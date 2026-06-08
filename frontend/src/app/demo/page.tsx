"use client";

/**
 * /demo — Static demo report page.
 *
 * Shows a complete polished RoundLab example using SAMPLE_SPEECH_V2 fixtures.
 * No API calls, no auth. Use this to demonstrate the app to coaches and students.
 * Clearly labeled as a demo — data is not mixed into real user dashboards.
 */

import Link from "next/link";
import { motion } from "motion/react";
import {
  FlaskConical, Target, CheckSquare, Square, Zap, ArrowRight,
  TrendingUp, AlertCircle, ThumbsUp,
} from "lucide-react";
import AppNav from "@/components/AppNav";
import { fadeUp, EASE } from "@/lib/motion";
import {
  SAMPLE_SPEECH_V2,
  SAMPLE_FEEDBACK_V2,
  SAMPLE_DRILLS_V2,
  SAMPLE_TRANSCRIPT_V1 as SAMPLE_TRANSCRIPT,
} from "@/lib/fixtures";

const SKILL_LABEL: Record<string, string> = {
  weighing: "Impact Weighing", warranting: "Warranting", drops: "Drop Prevention",
  extensions: "Extensions", evidence: "Evidence Use", clash: "Clash",
  judge_adaptation: "Judge Adaptation",
};

const ISSUE_SEVERITY_COLOR: Record<string, string> = {
  high: "text-danger border-danger/20 bg-danger/5",
  medium: "text-warn border-warn/20 bg-warn/5",
  low: "text-ok border-ok/20 bg-ok/5",
};

export default function DemoPage() {
  const speech   = SAMPLE_SPEECH_V2;
  const feedback = SAMPLE_FEEDBACK_V2;
  const drills   = SAMPLE_DRILLS_V2;
  const issues   = (feedback.raw_feedback?.structured_issues as Array<{
    issue_type: string; severity: string; title: string;
    explanation: string; recommendation: string; recommended_drill_type: string;
  }> | undefined) ?? [];

  return (
    <>
      <AppNav />
      <main className="min-h-screen bg-canvas">
        <div className="mx-auto flex max-w-3xl flex-col gap-6 px-4 py-8 sm:px-6">

          {/* Demo banner */}
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, ease: EASE }}
            className="flex items-center gap-2 rounded-lg border border-lav/20 bg-lav/5 px-4 py-2.5"
          >
            <FlaskConical size={14} className="shrink-0 text-lav" />
            <p className="text-xs text-ink-subtle">
              <span className="font-semibold text-ink">Demo report.</span>{" "}
              This is static sample data, not a real speech session. No audio was recorded.
              <Link href="/session" className="ml-1.5 font-medium text-lav hover:text-lav-hi">
                Start a real session →
              </Link>
            </p>
          </motion.div>

          {/* Speech header */}
          <motion.div {...fadeUp(0)} className="flex flex-col gap-2">
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

          {/* Scores */}
          <motion.div {...fadeUp(0.06)} className="grid grid-cols-3 gap-3 sm:grid-cols-5">
            {[
              { label: "Overall", value: feedback.overall_score ?? 0, max: 100 },
              { label: "Clash",   value: feedback.scores.clash, max: 20 },
              { label: "Weighing", value: feedback.scores.weighing, max: 20 },
              { label: "Drops",   value: feedback.scores.drops, max: 20 },
              { label: "Judge",   value: feedback.scores.judge_adaptation, max: 20 },
            ].map((s) => {
              const pct = (s.value / s.max) * 100;
              const color = pct >= 70 ? "text-ok" : pct >= 50 ? "text-warn" : "text-danger";
              return (
                <div key={s.label} className="flex flex-col items-center gap-0.5 rounded-xl border border-hairline bg-surface-1 py-3">
                  <span className={`text-lg font-bold tabular-nums ${color}`}>{s.value}</span>
                  <span className="text-[9px] font-normal text-ink-faint">/{s.max}</span>
                  <span className="text-[10px] text-ink-subtle">{s.label}</span>
                </div>
              );
            })}
          </motion.div>

          {/* Coach summary */}
          {feedback.summary && (
            <motion.div {...fadeUp(0.10)} className="rounded-xl border border-lav/20 bg-lav/5 px-5 py-4">
              <p className="mb-1 text-eyebrow text-lav">Coach ballot</p>
              <p className="text-sm leading-relaxed text-ink">{feedback.summary}</p>
            </motion.div>
          )}

          {/* Transcript excerpt */}
          <motion.div {...fadeUp(0.13)} className="flex flex-col gap-2">
            <p className="text-eyebrow text-ink-subtle">Transcript excerpt</p>
            <p className="line-clamp-4 rounded-xl border border-hairline bg-surface-1 px-4 py-3 text-sm leading-relaxed text-ink-muted">
              {SAMPLE_TRANSCRIPT.text}
            </p>
          </motion.div>

          {/* Structured issues */}
          {issues.length > 0 && (
            <motion.div {...fadeUp(0.16)} className="flex flex-col gap-3">
              <p className="text-eyebrow text-ink-subtle">Coaching issues</p>
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

          {/* Drills */}
          <motion.div {...fadeUp(0.20)} className="flex flex-col gap-3">
            <p className="text-eyebrow text-ink-subtle">Assigned drills</p>
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
                        <Square size={10} className="shrink-0 text-ink-faint" />
                        {c}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </motion.div>

          {/* Mock improvement comparison */}
          <motion.div
            {...fadeUp(0.24)}
            className="rounded-2xl border border-ok/20 bg-ok/5 p-5"
            style={{ boxShadow: "0 0 32px -12px oklch(0.620 0.170 145 / 0.12)" }}
          >
            <div className="mb-4 flex items-center gap-2.5">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-ok/15">
                <TrendingUp size={15} className="text-ok" />
              </div>
              <div>
                <p className="text-eyebrow text-ok">Drill improvement</p>
                <p className="text-sm font-semibold text-ink">Re-record comparison (sample)</p>
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
            <div className="mt-3 rounded-lg border border-ok/15 bg-ok/8 px-3 py-2">
              <p className="text-xs text-ink">
                Strong improvement — overall score up 8 points after the drill. Your weighing score also improved by 4.
              </p>
            </div>
          </motion.div>

          {/* CTA */}
          <motion.div {...fadeUp(0.28)} className="flex flex-wrap gap-3">
            <Link
              href="/session"
              className="flex items-center gap-1.5 rounded-md bg-lav px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-lav-hi"
            >
              Start your first real session
              <ArrowRight size={13} />
            </Link>
            <Link
              href="/evals"
              className="flex items-center gap-1.5 rounded-md border border-hairline px-5 py-2.5 text-sm font-medium text-ink-subtle transition-colors hover:border-lav/30 hover:text-ink"
            >
              View eval quality dashboard
            </Link>
          </motion.div>

        </div>
      </main>
    </>
  );
}
