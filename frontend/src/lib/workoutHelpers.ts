import type { Workout, WorkoutStep, WorkoutStatus } from "@/types";

export function estimateWorkoutMinutes(steps: WorkoutStep[]): number {
  return steps.reduce((sum, s) => sum + (s.estimated_minutes || 0), 0);
}

export interface WorkoutProgress {
  completed: number;
  total: number;
  pct: number;
}

export function deriveWorkoutProgress(workout: Workout): WorkoutProgress {
  const steps = workout.workout_json.steps;
  const total = steps.length;
  const completed = steps.filter((s) => s.completed).length;
  return {
    completed,
    total,
    pct: total > 0 ? Math.round((completed / total) * 100) : 0,
  };
}

export function getWorkoutFocusLabel(focus: string): string {
  const labels: Record<string, string> = {
    warranting:  "Warrant Clarity",
    evidence:    "Evidence Alignment",
    weighing:    "Impact Weighing",
    drops:       "Drop Prevention",
    extensions:  "Extension Quality",
    collapse:    "Collapse Discipline",
    delivery:    "Delivery Control",
    clash:       "Direct Clash",
    rerecord:    "Re-record",
  };
  return labels[focus] ?? focus;
}

export function getWorkoutStepCategoryLabel(category: string): string {
  const labels: Record<string, string> = {
    argument:  "Argument",
    evidence:  "Evidence",
    delivery:  "Delivery",
    rerecord:  "Re-record",
  };
  return labels[category] ?? category;
}

export function getNextIncompleteStep(workout: Workout): WorkoutStep | null {
  return workout.workout_json.steps.find((s) => !s.completed) ?? null;
}

export function buildReRecordGoal(workout: Workout): string {
  return workout.workout_json.re_record_goal;
}

export function shouldShowWorkoutCTA(
  speechStatus: string | undefined,
  hasFeedback: boolean,
  hasDrills: boolean,
): boolean {
  return speechStatus === "done" && hasFeedback && hasDrills;
}

export function workoutStatusLabel(status: WorkoutStatus): string {
  const labels: Record<WorkoutStatus, string> = {
    not_started: "Not started",
    in_progress:  "In progress",
    completed:    "Completed",
  };
  return labels[status] ?? status;
}

export function formatWorkoutPlan(workout: Workout): string {
  const lines: string[] = [];
  const { steps, re_record_goal, coach_note } = workout.workout_json;
  const totalMin = estimateWorkoutMinutes(steps);

  lines.push(`RoundLab Tournament Prep Workout`);
  lines.push(`${workout.title}`);
  lines.push(`Estimated time: ${totalMin} minutes`);
  if (workout.focus_area) {
    lines.push(`Focus: ${getWorkoutFocusLabel(workout.focus_area)}`);
  }
  lines.push("");

  if (coach_note) {
    lines.push(`Coach note: ${coach_note}`);
    lines.push("");
  }

  lines.push("Steps:");
  steps.forEach((step, i) => {
    lines.push(`\n${i + 1}. ${step.title} (${step.estimated_minutes} min)`);
    lines.push(`   Fix: ${step.problem}`);
    lines.push(`   Action: ${step.instruction}`);
    lines.push(`   Success: ${step.success_criteria}`);
  });

  lines.push("");
  lines.push(`Re-record goal:`);
  lines.push(`  ${re_record_goal}`);

  return lines.join("\n");
}
