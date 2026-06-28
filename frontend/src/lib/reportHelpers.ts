import type {
  SharedReportPayload,
  SpeechType,
  JudgeType,
  Workout,
} from "@/types";
import { estimateWorkoutMinutes, getWorkoutFocusLabel } from "@/lib/workoutHelpers";

// ── Speech type labels ─────────────────────────────────────────────────────────

const SPEECH_TYPE_LABELS: Record<SpeechType, string> = {
  constructive: "Constructive",
  rebuttal: "Rebuttal",
  summary: "Summary",
  final_focus: "Final Focus",
  crossfire: "Crossfire",
};

const JUDGE_TYPE_LABELS: Record<JudgeType, string> = {
  lay: "Lay judge",
  flow: "Flow judge",
  tech: "Tech judge",
  coach: "Coach",
};

export function speechTypeLabel(type: SpeechType | string): string {
  return SPEECH_TYPE_LABELS[type as SpeechType] ?? type;
}

export function judgeTypeLabel(type: JudgeType | string | null | undefined): string {
  if (!type) return "";
  return JUDGE_TYPE_LABELS[type as JudgeType] ?? type;
}

// ── Score display ──────────────────────────────────────────────────────────────

export function scoreColor(score: number | null | undefined): string {
  if (score === null || score === undefined) return "text-ink-subtle";
  if (score >= 80) return "text-ok";
  if (score >= 60) return "text-warn";
  return "text-danger";
}

export function deltaBadgeClass(delta: number | null | undefined): string {
  if (delta === null || delta === undefined) return "text-ink-faint";
  if (delta > 0) return "text-ok";
  if (delta < 0) return "text-danger";
  return "text-ink-subtle";
}

export function formatDelta(delta: number | null | undefined, unit = ""): string {
  if (delta === null || delta === undefined) return "—";
  const sign = delta > 0 ? "+" : "";
  return `${sign}${delta}${unit}`;
}

// ── Practice plan text formatter ───────────────────────────────────────────────

export function formatPracticePlan(data: SharedReportPayload, workout?: Workout | null): string {
  const lines: string[] = [];

  lines.push("Dissio Practice Plan");
  lines.push("=".repeat(30));
  lines.push("");

  const typeLabel = speechTypeLabel(data.speech_type);
  const date = new Date(data.created_at).toLocaleDateString(undefined, {
    month: "long", day: "numeric", year: "numeric",
  });
  lines.push(`Speech: ${typeLabel}${data.side ? ` (${data.side})` : ""}`);
  if (data.judge_type) lines.push(`Judge: ${judgeTypeLabel(data.judge_type)}`);
  if (data.topic) lines.push(`Resolution: ${data.topic}`);
  lines.push(`Date: ${date}`);
  lines.push("");

  if (data.feedback) {
    if (data.feedback.overall_score !== null && data.feedback.overall_score !== undefined) {
      lines.push(`Overall score: ${data.feedback.overall_score}/100`);
      lines.push("");
    }

    const priorities = data.feedback.top_3_priorities;
    if (priorities && priorities.length > 0) {
      lines.push("Top priorities:");
      priorities.forEach((p, i) => lines.push(`  ${i + 1}. ${p}`));
      lines.push("");
    }

    if (data.feedback.weaknesses && data.feedback.weaknesses.length > 0) {
      lines.push("Main issue:");
      lines.push(`  ${data.feedback.weaknesses[0]}`);
      lines.push("");
    }
  }

  if (data.delivery) {
    const parts: string[] = [];
    if (data.delivery.words_per_minute !== null && data.delivery.words_per_minute !== undefined) {
      parts.push(`${Math.round(data.delivery.words_per_minute)} WPM`);
    }
    if (data.delivery.filler_word_count !== null && data.delivery.filler_word_count !== undefined) {
      parts.push(`${data.delivery.filler_word_count} filler word${data.delivery.filler_word_count !== 1 ? "s" : ""}`);
    }
    if (data.delivery.pacing_band && data.delivery.pacing_band !== "unknown") {
      parts.push(data.delivery.pacing_band.replace("_", " "));
    }
    if (parts.length > 0) {
      lines.push(`Delivery: ${parts.join(" · ")}`);
      lines.push("");
    }
  }

  if (data.drills && data.drills.length > 0) {
    lines.push("Practice drills:");
    data.drills.forEach((drill, i) => {
      lines.push(`  ${i + 1}. ${drill.title} [${drill.skill_target}]`);
      if (drill.description) lines.push(`     ${drill.description}`);
      if (drill.success_criteria.length > 0) {
        lines.push(`     Success: ${drill.success_criteria[0]}`);
      }
    });
    lines.push("");
  }

  // ── Workout steps (if workout is provided) ──────────────────────────────
  if (workout) {
    const wSteps = workout.workout_json.steps;
    const totalMin = estimateWorkoutMinutes(wSteps);
    lines.push(`Tournament Prep Workout — ${workout.title}`);
    lines.push(`Estimated time: ${totalMin} minutes`);
    if (workout.focus_area) {
      lines.push(`Focus: ${getWorkoutFocusLabel(workout.focus_area)}`);
    }
    if (workout.workout_json.coach_note) {
      lines.push(`Coach note: ${workout.workout_json.coach_note}`);
    }
    lines.push("");
    lines.push("Workout steps:");
    wSteps.forEach((step, i) => {
      lines.push(`  ${i + 1}. ${step.title} (${step.estimated_minutes} min)`);
      lines.push(`     Fix: ${step.problem}`);
      lines.push(`     Action: ${step.instruction}`);
      lines.push(`     Success: ${step.success_criteria}`);
    });
    lines.push("");
    lines.push("Re-record goal:");
    lines.push(`  ${workout.workout_json.re_record_goal}`);
  } else {
    lines.push("Next re-record goal:");
    if (data.feedback?.top_3_priorities?.length) {
      lines.push(`  Address: ${data.feedback.top_3_priorities[0]}`);
    } else if (data.drills?.length) {
      lines.push(`  Complete drill: ${data.drills[0].title}`);
    } else {
      lines.push("  Complete at least one drill, then re-record this speech.");
    }
  }

  lines.push("");
  lines.push("Generated by Dissio — dissio.app");

  return lines.join("\n");
}

// ── Clipboard helper ───────────────────────────────────────────────────────────

export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    if (navigator?.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
    // Legacy fallback
    const el = document.createElement("textarea");
    el.value = text;
    el.style.position = "fixed";
    el.style.opacity = "0";
    document.body.appendChild(el);
    el.focus();
    el.select();
    const ok = document.execCommand("copy");
    document.body.removeChild(el);
    return ok;
  } catch {
    return false;
  }
}

// ── Share URL builder ──────────────────────────────────────────────────────────

export function buildShareUrl(token: string): string {
  if (typeof window === "undefined") return `/share/${token}`;
  return `${window.location.origin}/share/${token}`;
}
