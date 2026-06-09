"use client";

import { AlertCircle, Loader2, RefreshCw } from "lucide-react";
import type { AnalysisJob } from "@/types";
import { getJobFailureMessage, getJobStepLabel } from "@/lib/jobHelpers";

interface Props {
  job: AnalysisJob;
  onRetry?: () => void;
  retrying?: boolean;
}

export function AnalysisProgressCard({ job, onRetry, retrying }: Props) {
  const progress = job.progress ?? 0;
  const isFailed = job.status === "failed";
  const isRunning = job.status === "running" || job.status === "queued";

  if (isFailed) {
    return (
      <div className="rounded-xl border border-red-500/30 bg-red-950/20 p-5 space-y-3">
        <div className="flex items-start gap-3">
          <AlertCircle className="mt-0.5 shrink-0 text-red-400" size={18} />
          <div className="space-y-1">
            <p className="text-sm font-medium text-red-300">Analysis failed</p>
            <p className="text-sm text-red-400/80">
              {getJobFailureMessage(job)}
            </p>
            {job.attempt_count > 1 && (
              <p className="text-xs text-zinc-500">
                Attempt {job.attempt_count}
              </p>
            )}
          </div>
        </div>
        {onRetry && (
          <button
            onClick={onRetry}
            disabled={retrying}
            className="flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-500 disabled:opacity-50 transition-colors"
          >
            {retrying ? (
              <Loader2 className="animate-spin" size={14} />
            ) : (
              <RefreshCw size={14} />
            )}
            {retrying ? "Retrying…" : "Retry analysis"}
          </button>
        )}
      </div>
    );
  }

  if (isRunning) {
    return (
      <div className="rounded-xl border border-white/10 bg-white/5 p-5 space-y-4">
        <div className="flex items-center gap-3">
          <Loader2 className="animate-spin text-blue-400 shrink-0" size={18} />
          <p className="text-sm font-medium text-zinc-200">
            {getJobStepLabel(job)}
          </p>
        </div>
        <div className="space-y-1">
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/10">
            <div
              className="h-full rounded-full bg-blue-500 transition-all duration-700"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="text-xs text-zinc-500">{progress}%</p>
        </div>
      </div>
    );
  }

  return null;
}
