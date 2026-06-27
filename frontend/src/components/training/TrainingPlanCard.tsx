"use client";
import { CheckCircle, Circle, BookOpen, Mic, RefreshCw, Target } from "lucide-react";
import type { TrainingPlan, WeekPlan } from "@/types/training";
import { Button } from "@/components/ui/button";
import Link from "next/link";

interface Props {
  plan: TrainingPlan;
  onNextWeek?: () => void;
  advancing?: boolean;
}

export function TrainingPlanCard({ plan, onNextWeek, advancing }: Props) {
  const week = plan.weeks[plan.current_week - 1] as WeekPlan | undefined;

  if (!week) {
    return (
      <div className="rounded-2xl border border-hairline bg-surface-1 px-5 py-8 text-center">
        <p className="text-[13px] text-ink-subtle">Plan complete — generate a new plan to continue.</p>
      </div>
    );
  }

  const progressPct = ((plan.current_week - 1) / plan.total_weeks) * 100;

  return (
    <div className="rounded-2xl border border-hairline bg-surface-1 overflow-hidden">
      {/* Header */}
      <div className="bg-lav/5 border-b border-hairline px-5 py-3 flex items-center justify-between">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-wide text-lav">
            Week {plan.current_week} of {plan.total_weeks}
          </p>
          <p className="text-[15px] font-bold text-ink mt-0.5">{week.objective}</p>
        </div>
        <div className="text-right">
          <p className="text-[11px] text-ink-subtle">{week.estimated_hours}h this week</p>
          <p className="text-[10px] text-ink-subtle">Target: {week.mastery_target.toFixed(0)}/100</p>
        </div>
      </div>

      {/* Progress bar */}
      <div className="h-1 bg-surface-3">
        <div
          className="h-full bg-lav transition-all"
          style={{ width: `${progressPct}%` }}
        />
      </div>

      {/* Steps */}
      <div className="px-5 py-4 space-y-3">
        {week.lesson_id && (
          <div className="flex items-start gap-3">
            <BookOpen size={15} className="shrink-0 mt-0.5 text-lav" aria-hidden />
            <div className="flex-1">
              <p className="text-[12px] font-semibold text-ink">Learn</p>
              <p className="text-[12px] text-ink-subtle">{week.skill_name} lesson</p>
            </div>
            <Link href={`/learn?lesson=${week.lesson_id}`} className="text-[11px] text-lav hover:underline shrink-0">
              Start →
            </Link>
          </div>
        )}

        <div className="flex items-start gap-3">
          <Target size={15} className="shrink-0 mt-0.5 text-ok" aria-hidden />
          <div className="flex-1">
            <p className="text-[12px] font-semibold text-ink">Drill</p>
            <p className="text-[12px] text-ink-subtle">{week.drill_description}</p>
          </div>
        </div>

        <div className="flex items-start gap-3">
          <Mic size={15} className="shrink-0 mt-0.5 text-warn" aria-hidden />
          <div className="flex-1">
            <p className="text-[12px] font-semibold text-ink">Apply</p>
            <p className="text-[12px] text-ink-subtle">{week.speech_application}</p>
          </div>
          <Link href="/session" className="text-[11px] text-lav hover:underline shrink-0">
            Record →
          </Link>
        </div>

        <div className="flex items-start gap-3">
          <RefreshCw size={15} className="shrink-0 mt-0.5 text-orange-400" aria-hidden />
          <div className="flex-1">
            <p className="text-[12px] font-semibold text-ink">Prove</p>
            <div className="space-y-0.5 mt-0.5">
              {week.completion_criteria.map((c, i) => (
                <p key={i} className="text-[11px] text-ink-subtle flex items-start gap-1">
                  <Circle size={10} className="shrink-0 mt-0.5 text-ink-faint" aria-hidden />
                  {c}
                </p>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Action */}
      {plan.current_week < plan.total_weeks && onNextWeek && (
        <div className="px-5 pb-4">
          <Button
            size="sm"
            variant="secondary"
            onClick={onNextWeek}
            disabled={advancing}
            className="w-full text-[12px]"
          >
            <CheckCircle size={13} className="mr-1.5" aria-hidden />
            {advancing ? "Saving…" : "Mark week complete → next"}
          </Button>
        </div>
      )}
    </div>
  );
}
