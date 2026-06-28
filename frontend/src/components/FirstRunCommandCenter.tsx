"use client";

import Link from "next/link";
import { ArrowRight, FileText, FlaskConical, Mic } from "lucide-react";
import { motion } from "motion/react";
import { logEvent } from "@/lib/analytics";
import { fadeUp } from "@/lib/motion";

// ── Pipeline loop visualization ───────────────────────────────────────────────

const LOOP_STEPS = [
  { label: "Speech", color: "bg-lav" },
  { label: "Flow",   color: "bg-lav" },
  { label: "Ballot", color: "bg-lav" },
  { label: "Drill",  color: "bg-lav" },
  { label: "Re-record", color: "bg-ok" },
];

function PipelineLoop() {
  return (
    <div className="flex items-center gap-1 flex-wrap">
      {LOOP_STEPS.map((step, i) => (
        <div key={step.label} className="flex items-center gap-1">
          <span className={`inline-flex items-center rounded-full ${step.color}/15 border border-current/20 px-2 py-0.5 text-[10px] font-semibold ${step.color === "bg-ok" ? "text-ok" : "text-lav"}`}>
            {step.label}
          </span>
          {i < LOOP_STEPS.length - 1 && (
            <ArrowRight size={9} className="text-ink-faint shrink-0" />
          )}
        </div>
      ))}
    </div>
  );
}

// ── Action path card ──────────────────────────────────────────────────────────

function PathCard({
  icon: Icon,
  title,
  description,
  ctaLabel,
  href,
  primary,
  onClick,
}: {
  icon: React.ElementType;
  title: string;
  description: string;
  ctaLabel: string;
  href: string;
  primary?: boolean;
  onClick?: () => void;
}) {
  return (
    <Link
      href={href}
      onClick={onClick}
      className={[
        "flex flex-col gap-3 rounded-xl border p-4 transition-colors group",
        primary
          ? "border-lav/30 bg-lav/5 hover:bg-lav/10 hover:border-lav/50"
          : "border-hairline bg-surface-2 hover:border-hairline-strong hover:bg-surface-3",
      ].join(" ")}
    >
      <div className={`flex h-8 w-8 items-center justify-center rounded-lg ${primary ? "bg-lav/15" : "bg-surface-3"}`}>
        <Icon size={15} className={primary ? "text-lav" : "text-ink-subtle"} />
      </div>
      <div className="flex flex-col gap-1 flex-1">
        <p className="text-sm font-semibold text-ink">{title}</p>
        <p className="text-xs text-ink-faint leading-relaxed">{description}</p>
      </div>
      <div className={`flex items-center gap-1 text-xs font-medium ${primary ? "text-lav" : "text-ink-subtle"} group-hover:gap-2 transition-all`}>
        {ctaLabel}
        <ArrowRight size={11} />
      </div>
    </Link>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

interface FirstRunCommandCenterProps {
  userId?: string | null;
}

export default function FirstRunCommandCenter({ userId }: FirstRunCommandCenterProps) {
  return (
    <motion.div {...fadeUp(0)}>
      <div className="rounded-xl border border-lav/20 bg-surface-1 overflow-hidden">

        {/* Header */}
        <div className="border-b border-hairline bg-lav/5 px-5 py-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="section-stamp" style={{ color: "var(--color-lav)" }}>
              First rep
            </span>
          </div>
          <p className="text-base font-semibold text-ink">Start your first Dissio rep</p>
          <p className="mt-1 text-xs text-ink-subtle leading-relaxed">
            Upload or record a PF speech — Dissio builds your flow, generates judge-style feedback, and assigns targeted drills.
          </p>
          <div className="mt-3">
            <PipelineLoop />
          </div>
        </div>

        {/* Three paths */}
        <div className="grid grid-cols-1 gap-3 p-4 sm:grid-cols-3">
          <PathCard
            icon={Mic}
            title="Analyze my own speech"
            description="Record live or upload an audio file. Works with constructive, rebuttal, summary, or final focus."
            ctaLabel="Start first speech"
            href="/session"
            primary
            onClick={() => logEvent("onboarding_start_speech_clicked", userId)}
          />
          <PathCard
            icon={FlaskConical}
            title="Try a demo report"
            description="See what a complete Dissio session looks like — flow, ballot, drills, and re-record comparison."
            ctaLabel="Open demo report"
            href="/demo"
            onClick={() => logEvent("onboarding_demo_clicked", userId)}
          />
          <PathCard
            icon={FileText}
            title="Upload evidence first"
            description="Optional: add your case file so Dissio can check whether your speech evidence actually supports your claims."
            ctaLabel="Add case file"
            href="/evidence"
            onClick={() => logEvent("onboarding_evidence_clicked", userId)}
          />
        </div>

        {/* Footer hint */}
        <div className="border-t border-hairline px-5 py-3">
          <p className="text-[11px] text-ink-faint">
            Not sure where to start?{" "}
            <Link href="/demo" className="text-lav hover:text-lav-hi underline-offset-2 hover:underline" onClick={() => logEvent("onboarding_demo_clicked", userId)}>
              Try the demo report
            </Link>{" "}
            to see exactly what you&apos;ll get.
          </p>
        </div>
      </div>
    </motion.div>
  );
}
