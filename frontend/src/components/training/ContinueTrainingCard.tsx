"use client";
import Link from "next/link";
import { ArrowRight, BookOpen, Target, RefreshCw, Zap } from "lucide-react";

interface NextAction {
  skill_id: string;
  lesson_id?: string | null;
  source: string;
  context: string;
  active_plan?: {
    id: string;
    current_week: number;
    total_weeks: number;
  };
  plan_step?: {
    objective: string;
    estimated_hours: number;
    drill_description: string;
  };
}

const SOURCE_ICON: Record<string, React.ReactNode> = {
  training_plan: <BookOpen size={14} className="text-lav" aria-hidden />,
  mastery_gap: <Target size={14} className="text-warn" aria-hidden />,
  needs_refresh: <RefreshCw size={14} className="text-orange-400" aria-hidden />,
  coach_assignment: <Zap size={14} className="text-ok" aria-hidden />,
  coach_priority: <Zap size={14} className="text-ok" aria-hidden />,
};

const SOURCE_LABEL: Record<string, string> = {
  training_plan: "Training plan",
  mastery_gap: "Skills gap",
  needs_refresh: "Refresh needed",
  coach_assignment: "Coach assigned",
  coach_priority: "Coach priority",
  fallback: "Suggested",
};

interface Props {
  nextAction: NextAction | null;
  loading?: boolean;
}

export function ContinueTrainingCard({ nextAction, loading }: Props) {
  if (loading) {
    return (
      <div className="rounded-2xl border border-hairline bg-surface-1 px-5 py-4 animate-pulse h-24" />
    );
  }

  if (!nextAction) {
    return (
      <Link
        href="/training"
        className="block rounded-2xl border border-lav/20 bg-lav/5 px-5 py-4 hover:bg-lav/10 transition-colors"
      >
        <div className="flex items-center justify-between">
          <div>
            <p className="text-[12px] font-semibold uppercase tracking-wide text-lav">
              Training
            </p>
            <p className="text-[14px] font-bold text-ink mt-0.5">
              Start your training plan
            </p>
          </div>
          <ArrowRight size={16} className="text-lav shrink-0" aria-hidden />
        </div>
      </Link>
    );
  }

  const icon = SOURCE_ICON[nextAction.source] ?? <Target size={14} className="text-lav" aria-hidden />;
  const label = SOURCE_LABEL[nextAction.source] ?? "Next";
  const href = nextAction.lesson_id
    ? `/lesson?lesson=${nextAction.lesson_id}`
    : "/training";

  return (
    <Link
      href={href}
      className="block rounded-2xl border border-hairline bg-surface-1 hover:bg-surface-2 transition-colors px-5 py-4"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 mb-1">
            {icon}
            <p className="text-[10px] font-semibold uppercase tracking-wide text-ink-subtle">
              {label}
            </p>
          </div>
          <p className="text-[14px] font-bold text-ink leading-snug">
            {nextAction.plan_step?.objective ?? nextAction.context}
          </p>
          {nextAction.active_plan && (
            <p className="text-[11px] text-ink-subtle mt-1">
              Week {nextAction.active_plan.current_week} of{" "}
              {nextAction.active_plan.total_weeks}
              {nextAction.plan_step?.estimated_hours
                ? ` · ${nextAction.plan_step.estimated_hours}h this week`
                : ""}
            </p>
          )}
        </div>
        <ArrowRight size={16} className="text-ink-subtle shrink-0 mt-1" aria-hidden />
      </div>
    </Link>
  );
}
