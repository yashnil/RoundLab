/**
 * Assignment API wrappers + pure helpers shared by the coach overview, builder,
 * review queue, student profile, and the student handoff. Network calls go
 * through apiFetch; the pure helpers (handoff href, status labels, overdue) are
 * unit-tested.
 */

import { apiFetch } from "@/lib/api";
import type {
  Assignment, RecipientState, ReviewQueueItem, TeamReadiness, CoachStudentProfile,
} from "@/types";

export interface CreateAssignmentInput {
  team_id: string;
  created_by: string;
  title: string;
  kind: "speech" | "rerecord" | "drill";
  speech_type?: string | null;
  side?: string | null;
  judge_type?: string | null;
  topic?: string | null;
  goal?: string | null;
  success_criteria: string[];
  due_date?: string | null;
  recipient_user_ids: string[];
}

export function createAssignment(input: CreateAssignmentInput): Promise<Assignment> {
  return apiFetch<Assignment>("/assignments", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}

export function listAssignments(teamId: string, userId: string): Promise<Assignment[]> {
  return apiFetch<Assignment[]>(`/teams/${teamId}/assignments?user_id=${userId}`);
}

export function fetchReviewQueue(teamId: string, userId: string): Promise<ReviewQueueItem[]> {
  return apiFetch<ReviewQueueItem[]>(`/teams/${teamId}/review-queue?user_id=${userId}`);
}

export function fetchReadiness(teamId: string, userId: string): Promise<TeamReadiness> {
  return apiFetch<TeamReadiness>(`/teams/${teamId}/readiness?user_id=${userId}`);
}

export function fetchStudentProfile(teamId: string, studentId: string, userId: string): Promise<CoachStudentProfile> {
  return apiFetch<CoachStudentProfile>(`/teams/${teamId}/students/${studentId}?user_id=${userId}`);
}

export function submitAssignment(recipientId: string, userId: string, speechId: string): Promise<unknown> {
  return apiFetch(`/assignments/recipients/${recipientId}/submit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, speech_id: speechId }),
  });
}

export function reviewAssignment(
  recipientId: string, userId: string, action: "reviewed" | "revision_requested", coachFeedback?: string,
): Promise<unknown> {
  return apiFetch(`/assignments/recipients/${recipientId}/review`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, action, coach_feedback: coachFeedback ?? null }),
  });
}

// ── Pure helpers ────────────────────────────────────────────────────────────────

export const RECIPIENT_STATE_LABEL: Record<RecipientState, string> = {
  assigned: "Not started",
  submitted: "Ready for review",
  reviewed: "Reviewed",
  revision_requested: "Revision requested",
};

export const RECIPIENT_STATE_TONE: Record<RecipientState, "ink" | "warn" | "ok" | "danger"> = {
  assigned: "ink",
  submitted: "warn",
  reviewed: "ok",
  revision_requested: "danger",
};

/** An assignment is overdue if its due date has passed and not everyone is done. */
export function isOverdue(assignment: Assignment, now: Date = new Date()): boolean {
  if (!assignment.due_date) return false;
  const due = new Date(assignment.due_date + "T23:59:59");
  if (now <= due) return false;
  return assignment.recipients.some((r) => r.status === "assigned" || r.status === "submitted");
}

/** How many recipients still need the coach's attention (submitted, awaiting review). */
export function reviewBacklog(assignments: Assignment[]): number {
  return assignments.reduce(
    (n, a) => n + a.recipients.filter((r) => r.status === "submitted").length,
    0,
  );
}

/**
 * Deep-link that carries an assignment's context into the student's practice
 * route, tagging the recipient so the student can submit against it afterward.
 */
export function assignmentHandoffHref(a: Assignment, recipientId: string): string {
  const params = new URLSearchParams();
  if (a.speech_type) params.set("type", a.speech_type);
  if (a.judge_type) params.set("judge", a.judge_type);
  if (a.side) params.set("side", a.side);
  if (a.goal) params.set("goal", a.goal);
  params.set("assignment", recipientId);
  return `/session?${params.toString()}`;
}
