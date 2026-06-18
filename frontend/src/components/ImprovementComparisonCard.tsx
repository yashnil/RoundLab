"use client";

import type { SpeechComparisonResult } from "@/types";
import ImprovementReceipt from "@/components/ImprovementReceipt";

interface Props {
  comparison: SpeechComparisonResult;
}

/**
 * Re-record comparison shown in the report. Thin wrapper over ImprovementReceipt
 * so the re-record path and the drill-result path share one improvement view.
 */
export default function ImprovementComparisonCard({ comparison }: Props) {
  if (!comparison.has_parent) return null;

  const hasAnyScore =
    comparison.original_overall_score !== null || comparison.new_overall_score !== null;

  if (!hasAnyScore) {
    return (
      <div className="rounded-2xl border border-hairline bg-surface-1 p-5">
        <p className="text-eyebrow text-lav">Improvement receipt</p>
        <p className="mt-1 text-xs text-ink-faint">
          Your comparison will appear once both reports are fully analyzed.
        </p>
      </div>
    );
  }

  return <ImprovementReceipt comparison={comparison} />;
}
