"use client";

import { Check, Loader, AlertTriangle, Circle } from "lucide-react";
import {
  deriveProcessingStages,
  processingHeadline,
  ANALYSIS_CATEGORIES,
  type ProcJobStatus,
  type ProcStageStatus,
} from "@/lib/practice/processingStages";
import { cn } from "@/lib/utils";

interface SpeechProcessingTimelineProps {
  jobStatus: ProcJobStatus;
  hasReport: boolean;
  failed: boolean;
}

function StageIcon({ status }: { status: ProcStageStatus }) {
  if (status === "done") return <Check size={13} strokeWidth={2.5} aria-hidden="true" />;
  if (status === "active") return <Loader size={13} className="motion-safe:animate-spin" aria-hidden="true" />;
  if (status === "failed") return <AlertTriangle size={13} aria-hidden="true" />;
  return <Circle size={9} aria-hidden="true" />;
}

const stageStyles: Record<ProcStageStatus, { dot: string; text: string; rail: string }> = {
  done: { dot: "border-ok/40 bg-ok/15 text-ok", text: "text-ink", rail: "bg-ok/40" },
  active: { dot: "border-proc-active/50 bg-proc-active/15 text-proc-active", text: "text-ink", rail: "bg-hairline" },
  failed: { dot: "border-danger/40 bg-danger/15 text-danger", text: "text-ink", rail: "bg-hairline" },
  upcoming: { dot: "border-hairline-strong bg-surface-2 text-ink-faint", text: "text-ink-faint", rail: "bg-hairline" },
};

/**
 * Honest, debate-native processing timeline. Shows four high-level stages
 * (the only ones the backend supports) and lists the analysis categories as an
 * explanatory checklist — never marking them complete from elapsed time, never
 * a fake percentage. Only the active stage animates (reduced-motion safe).
 */
export default function SpeechProcessingTimeline({
  jobStatus,
  hasReport,
  failed,
}: SpeechProcessingTimelineProps) {
  const stages = deriveProcessingStages({ jobStatus, hasReport, failed });
  const headline = processingHeadline(stages);
  const analysisActive = stages.find((s) => s.id === "analysis")?.status === "active";

  return (
    <div className="flex flex-col gap-4">
      <p className="sr-only" role="status" aria-live="polite">
        {headline}
      </p>

      <ol className="flex flex-col gap-0">
        {stages.map((stage, i) => {
          const s = stageStyles[stage.status];
          const last = i === stages.length - 1;
          return (
            <li
              key={stage.id}
              className="relative flex items-start gap-3 pb-4 last:pb-0"
              aria-current={stage.status === "active" ? "step" : undefined}
            >
              {!last && (
                <span className={cn("absolute left-[12px] top-7 h-[calc(100%-1rem)] w-px", s.rail)} aria-hidden="true" />
              )}
              <span className={cn("z-10 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border", s.dot)}>
                <StageIcon status={stage.status} />
              </span>
              <div className="min-w-0 flex-1 pt-0.5">
                <p className={cn("text-sm font-medium", s.text)}>{stage.label}</p>

                {stage.id === "analysis" && (stage.status === "active" || stage.status === "done") && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {ANALYSIS_CATEGORIES.map((cat) => (
                      <span
                        key={cat}
                        className={cn(
                          "inline-flex items-center rounded-md border px-2 py-0.5 text-[0.6875rem] font-medium",
                          stage.status === "done"
                            ? "border-ok/25 bg-ok/5 text-ink-subtle"
                            : "border-proc-active/20 bg-proc-active/5 text-ink-subtle",
                        )}
                      >
                        {cat}
                      </span>
                    ))}
                  </div>
                )}

                {stage.id === "analysis" && analysisActive && (
                  <p className="mt-2 text-xs leading-relaxed text-ink-faint">
                    RoundLab is examining these categories together — they aren’t finished one at a time.
                  </p>
                )}
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
