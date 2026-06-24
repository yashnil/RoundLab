"use client";

import { getDroppedArguments, getSurvivingOffense, winnerLabel } from "@/lib/roundModel";
import type { RoundArgument, RoundDecision } from "@/types/round";

interface Props {
  decision: RoundDecision;
  allArguments: RoundArgument[];
  onRejudge?: (judgeType: string) => Promise<void>;
  isLoading?: boolean;
}

export function RoundBallotView({ decision, allArguments, onRejudge, isLoading }: Props) {
  const proSurviving = getSurvivingOffense(allArguments, "pro");
  const conSurviving = getSurvivingOffense(allArguments, "con");
  const dropped = getDroppedArguments(allArguments);

  return (
    <div className="space-y-6 max-w-2xl">
      {/* Header */}
      <div className="rounded-lg border-2 border-primary/20 bg-primary/5 p-6">
        <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
          Decision
        </div>
        <div className="text-2xl font-semibold">{winnerLabel(decision)} wins</div>
        <div className="text-xs text-muted-foreground mt-1">
          {decision.judge_type} judge · Engine v{decision.engine_version}
        </div>
      </div>

      {/* RFD */}
      <div className="rounded-lg border p-4">
        <h3 className="text-sm font-semibold mb-2">Reason for Decision</h3>
        <p className="text-sm text-muted-foreground leading-relaxed">{decision.reason_for_decision}</p>
      </div>

      {/* Voting issues */}
      {decision.voting_issues.length > 0 && (
        <div className="rounded-lg border p-4">
          <h3 className="text-sm font-semibold mb-2">Voting Issues</h3>
          <ul className="space-y-1">
            {decision.voting_issues.map((v, i) => (
              <li key={i} className="text-sm text-muted-foreground flex items-start gap-2">
                <span className="mt-0.5 text-primary">›</span>
                <span>{v}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Speaker points */}
      <div className="rounded-lg border p-4">
        <h3 className="text-sm font-semibold mb-3">Speaker Points</h3>
        <div className="grid grid-cols-2 gap-4">
          <div className="text-center">
            <div className="text-2xl font-mono font-semibold">{decision.speaker_points["pro"] ?? "—"}</div>
            <div className="text-xs text-muted-foreground mt-1">Pro</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-mono font-semibold">{decision.speaker_points["con"] ?? "—"}</div>
            <div className="text-xs text-muted-foreground mt-1">Con</div>
          </div>
        </div>
      </div>

      {/* Dropped arguments */}
      {dropped.length > 0 && (
        <div className="rounded-lg border border-red-200 dark:border-red-900 p-4">
          <h3 className="text-sm font-semibold text-red-700 dark:text-red-400 mb-2">
            Dropped Arguments ({dropped.length})
          </h3>
          <ul className="space-y-1">
            {dropped.map((a) => (
              <li key={a.id} className="text-sm text-muted-foreground flex items-start gap-2">
                <span className="font-mono text-xs w-8 shrink-0 mt-0.5">{a.label}</span>
                <span className="text-xs">{a.claim}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Evidence issues */}
      {decision.evidence_issues.length > 0 && (
        <div className="rounded-lg border p-4">
          <h3 className="text-sm font-semibold mb-2">Evidence Issues</h3>
          <ul className="space-y-1">
            {decision.evidence_issues.map((v, i) => (
              <li key={i} className="text-xs text-amber-600 dark:text-amber-400">{v}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Weighing */}
      {decision.weighing_comparison && (
        <div className="rounded-lg border p-4">
          <h3 className="text-sm font-semibold mb-2">Weighing</h3>
          <p className="text-sm text-muted-foreground">{decision.weighing_comparison}</p>
        </div>
      )}

      {/* Decision trace */}
      <details className="rounded-lg border p-4">
        <summary className="text-sm font-semibold cursor-pointer">Decision Trace</summary>
        <div className="mt-3 space-y-1">
          {decision.decision_trace.arguments_considered.map((e, i) => (
            <div key={i} className="text-xs flex items-center gap-2">
              <span className={e.included ? "text-emerald-600" : "text-red-600"}>
                {e.included ? "✓" : "✗"}
              </span>
              <span className="font-mono w-8">{e.argument_label}</span>
              <span className="text-muted-foreground">{e.side}</span>
              {e.reason && <span className="text-muted-foreground italic">— {e.reason}</span>}
            </div>
          ))}
        </div>
        {decision.decision_trace.judge_profile_effects.length > 0 && (
          <div className="mt-3 pt-3 border-t">
            <p className="text-xs font-medium mb-1">Judge profile effects:</p>
            {decision.decision_trace.judge_profile_effects.map((e, i) => (
              <p key={i} className="text-xs text-muted-foreground">{e}</p>
            ))}
          </div>
        )}
      </details>
    </div>
  );
}
