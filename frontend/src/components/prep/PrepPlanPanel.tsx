"use client";

import { useState } from "react";
import { Check, Clock, ChevronDown, ChevronUp, AlertTriangle } from "lucide-react";
import { apiFetch } from "@/lib/api";
import type { PrepTask, TaskStatus, TaskType } from "@/types/prep";

const TASK_TYPE_LABELS: Record<TaskType, string> = {
  research_evidence: "Research Evidence",
  replace_stale_card: "Replace Stale Card",
  verify_citation: "Verify Citation",
  strengthen_warrant: "Strengthen Warrant",
  add_impact_evidence: "Add Impact Evidence",
  find_counterevidence: "Find Counter-Evidence",
  build_frontline: "Build Frontline",
  add_weighing: "Add Weighing",
  write_summary_extension: "Write Summary Extension",
  write_final_focus_extension: "Write Final Focus Extension",
  complete_a_drill: "Complete a Drill",
  review_unsafe_card: "Review Unsafe Card",
};

const PRIORITY_COLORS: Record<number, string> = {
  1: "text-danger",
  2: "text-amber-600",
  3: "text-ink-subtle",
};

function TaskRow({
  task,
  onComplete,
}: {
  task: PrepTask;
  onComplete: (id: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [completing, setCompleting] = useState(false);

  async function handleComplete() {
    setCompleting(true);
    try {
      await apiFetch(`/prep/tasks/${task.id}`, {
        method: "PATCH",
        body: JSON.stringify({ user_id: task.user_id, status: "completed" }),
      });
      onComplete(task.id);
    } catch {
      // non-fatal
    } finally {
      setCompleting(false);
    }
  }

  const isDone = task.status === "completed" || task.status === "skipped";

  return (
    <div
      className={`rounded-xl border ${isDone ? "border-border opacity-60" : "border-border"} overflow-hidden`}
    >
      <div className="flex items-start gap-3 px-4 py-3">
        <button
          onClick={handleComplete}
          disabled={isDone || completing}
          aria-label={isDone ? "Completed" : "Mark complete"}
          className={`mt-0.5 w-4 h-4 rounded-full border flex items-center justify-center shrink-0 transition-colors ${
            isDone
              ? "bg-ok/20 border-ok/40"
              : "border-border hover:border-lav hover:bg-lav/10"
          }`}
        >
          {isDone && <Check size={10} className="text-ok" />}
        </button>
        <div className="flex-1 min-w-0 space-y-0.5">
          <div className="flex items-center gap-2 flex-wrap">
            <span
              className={`text-[10px] font-bold ${PRIORITY_COLORS[task.priority] || "text-ink-subtle"}`}
            >
              P{task.priority}
            </span>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface-muted border border-border text-ink-subtle">
              {TASK_TYPE_LABELS[task.task_type]}
            </span>
            {task.estimated_minutes && (
              <span className="text-[10px] text-ink-faint flex items-center gap-0.5">
                <Clock size={9} />
                {task.estimated_minutes}m
              </span>
            )}
            {task.is_auto_generated && (
              <span className="text-[9px] text-ink-faint">auto</span>
            )}
          </div>
          <p
            className={`text-[13px] font-semibold ${isDone ? "line-through text-ink-subtle" : "text-ink"}`}
          >
            {task.title}
          </p>
          {task.reason && (
            <button
              onClick={() => setExpanded((e) => !e)}
              className="flex items-center gap-1 text-[10px] text-lav hover:underline"
            >
              {expanded ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
              {expanded ? "Less" : "Why?"}
            </button>
          )}
          {expanded && task.reason && (
            <p className="text-[11px] text-ink-subtle leading-relaxed pt-1">
              {task.reason}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

interface PrepPlanPanelProps {
  tasks: PrepTask[];
  onTaskComplete: (id: string) => void;
}

export function PrepPlanPanel({ tasks, onTaskComplete }: PrepPlanPanelProps) {
  const pending = tasks.filter((t) => t.status === "pending");
  const done = tasks.filter((t) => t.status === "completed" || t.status === "skipped");

  const totalMinutes = pending.reduce((s, t) => s + (t.estimated_minutes || 0), 0);

  if (tasks.length === 0) {
    return (
      <p className="py-8 text-center text-[12px] text-ink-subtle">
        No prep tasks yet. Generate a readiness report to get a plan.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-[12px] text-ink-subtle">
          {pending.length} task{pending.length !== 1 ? "s" : ""} remaining ·{" "}
          {totalMinutes > 0 ? `~${totalMinutes}m total` : ""}
        </p>
        {done.length > 0 && (
          <span className="text-[11px] text-ok">{done.length} completed</span>
        )}
      </div>

      <div className="space-y-2">
        {pending.map((task) => (
          <TaskRow key={task.id} task={task} onComplete={onTaskComplete} />
        ))}
        {pending.length === 0 && (
          <div className="py-6 text-center rounded-xl border border-ok/20 bg-ok/5">
            <Check size={20} className="mx-auto mb-2 text-ok" />
            <p className="text-[12px] text-ok">All tasks complete!</p>
          </div>
        )}
      </div>

      {done.length > 0 && (
        <details className="space-y-2">
          <summary className="text-[11px] text-ink-subtle cursor-pointer hover:text-ink">
            Show {done.length} completed
          </summary>
          <div className="space-y-2 pt-2">
            {done.map((task) => (
              <TaskRow key={task.id} task={task} onComplete={() => {}} />
            ))}
          </div>
        </details>
      )}
    </div>
  );
}
