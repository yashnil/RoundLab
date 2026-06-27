"use client";
import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import type { MasteryScore, MasteryState } from "@/types/training";
import { MASTERY_STATE_LABEL, MASTERY_STATE_COLOR } from "@/types/training";

interface Props {
  mastery: MasteryScore;
  skillName: string;
}

export function MasteryExplanation({ mastery, skillName }: Props) {
  const [expanded, setExpanded] = useState(false);

  const stateColor = MASTERY_STATE_COLOR[mastery.mastery_state as MasteryState] ?? "text-ink-subtle";
  const stateLabel = MASTERY_STATE_LABEL[mastery.mastery_state as MasteryState] ?? mastery.mastery_state;

  return (
    <div className="rounded-xl border border-hairline bg-surface-1 px-4 py-3 space-y-2">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-[13px] font-semibold text-ink">{skillName}</p>
          <p className="text-[11px] text-ink-subtle">
            Score: <span className="font-semibold text-ink">{mastery.mastery_score.toFixed(0)}</span>
            {" · "}
            <span className={stateColor}>{stateLabel}</span>
            {" · "}
            {mastery.evidence_count} evidence item{mastery.evidence_count !== 1 ? "s" : ""}
          </p>
        </div>
        <button
          onClick={() => setExpanded((e) => !e)}
          className="flex items-center gap-1 text-[11px] text-ink-subtle hover:text-ink"
          aria-expanded={expanded}
        >
          {expanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
          {expanded ? "Less" : "Details"}
        </button>
      </div>

      {expanded && (
        <div className="space-y-2 pt-1 border-t border-hairline">
          {mastery.coach_override_score !== null && (
            <div className="rounded-lg bg-lav/10 px-3 py-2 text-[12px]">
              <span className="font-semibold text-lav">Coach override:</span>{" "}
              {mastery.coach_override_score.toFixed(0)}
              {mastery.coach_override_note && (
                <p className="text-ink-subtle mt-0.5">{mastery.coach_override_note}</p>
              )}
            </div>
          )}

          {mastery.explanation ? (
            <pre className="text-[11px] text-ink-subtle whitespace-pre-wrap font-sans">
              {mastery.explanation}
            </pre>
          ) : (
            <p className="text-[11px] text-ink-subtle">
              Based on {mastery.evidence_count} analyzed speech{mastery.evidence_count !== 1 ? "es" : ""},
              drill{mastery.evidence_count !== 1 ? "s" : ""}, and re-recordings.
              {mastery.last_demonstrated_at && (
                <> Last demonstrated {new Date(mastery.last_demonstrated_at).toLocaleDateString()}.</>
              )}
            </p>
          )}

          {mastery.recurring_weakness > 0 && (
            <p className="text-[11px] text-orange-600">
              ⚠ Recurring weakness flagged {mastery.recurring_weakness} time{mastery.recurring_weakness !== 1 ? "s" : ""}
            </p>
          )}

          <div className="flex items-center gap-2 text-[10px] text-ink-subtle">
            <span>Confidence: {(mastery.confidence * 100).toFixed(0)}%</span>
          </div>
        </div>
      )}
    </div>
  );
}
