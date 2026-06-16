"use client";

import { CheckCircle2, Loader, AlertTriangle, Circle, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { captureStatusView, type CapturePersistenceStatus, type CaptureTone } from "@/lib/practice/captureStatus";
import { cn } from "@/lib/utils";

interface CaptureSaveStatusProps {
  status: CapturePersistenceStatus;
  /** Retry handler, shown when the status is retryable. */
  onRetry?: () => void;
  retryLabel?: string;
  className?: string;
}

const toneStyles: Record<CaptureTone, { wrap: string; icon: string }> = {
  neutral: { wrap: "border-hairline bg-surface-2/60", icon: "text-ink-faint" },
  info: { wrap: "border-lav/25 bg-lav/5", icon: "text-lav" },
  success: { wrap: "border-ok/25 bg-ok/5", icon: "text-ok" },
  warning: { wrap: "border-warn/30 bg-warn/5", icon: "text-warn" },
  error: { wrap: "border-danger/25 bg-danger/5", icon: "text-danger" },
};

function ToneIcon({ tone }: { tone: CaptureTone }) {
  const cls = "shrink-0";
  if (tone === "success") return <CheckCircle2 size={16} className={cls} aria-hidden="true" />;
  if (tone === "info") return <Loader size={16} className={cn(cls, "motion-safe:animate-spin")} aria-hidden="true" />;
  if (tone === "warning" || tone === "error") return <AlertTriangle size={16} className={cls} aria-hidden="true" />;
  return <Circle size={16} className={cls} aria-hidden="true" />;
}

/**
 * One always-visible answer to "is my speech saved and can I leave?". Reads the
 * normalized capture status; never claims saved unless the status proves it.
 */
export default function CaptureSaveStatus({
  status,
  onRetry,
  retryLabel = "Retry analysis",
  className,
}: CaptureSaveStatusProps) {
  const view = captureStatusView(status);
  const styles = toneStyles[view.tone];

  return (
    <div
      className={cn("flex items-start gap-2.5 rounded-lg border px-3.5 py-2.5", styles.wrap, className)}
      role="status"
      aria-live="polite"
    >
      <span className={cn("mt-0.5", styles.icon)}>
        <ToneIcon tone={view.tone} />
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold text-ink">{view.title}</p>
        <p className="mt-0.5 text-xs leading-relaxed text-ink-subtle">{view.description}</p>
      </div>
      {view.retryable && onRetry && (
        <Button size="sm" variant="outline" onClick={onRetry} className="shrink-0 gap-1.5">
          <RotateCcw size={13} aria-hidden="true" />
          {retryLabel}
        </Button>
      )}
    </div>
  );
}
