/**
 * Assignment API wrappers + pure helpers shared by the coach overview, builder,
 * review queue, student profile, report rail, and the student handoff. Identity
 * is carried by the Supabase token (attached in apiFetch) — no user_id params.
 * The pure helpers (handoff href, status labels, overdue, backlog) are tested.
 */

import { apiFetch } from "@/lib/api";
import type {
  Assignment, RecipientState, ReviewQueueItem, TeamReadiness, CoachStudentProfile,
  AssignmentForSpeech,
} from "@/types";

export interface CreateAssignmentInput {
  team_id: string;
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

export function listAssignments(teamId: string): Promise<Assignment[]> {
  return apiFetch<Assignment[]>(`/teams/${teamId}/assignments`);
}

export function fetchReviewQueue(teamId: string): Promise<ReviewQueueItem[]> {
  return apiFetch<ReviewQueueItem[]>(`/teams/${teamId}/review-queue`);
}

export function fetchReadiness(teamId: string): Promise<TeamReadiness> {
  return apiFetch<TeamReadiness>(`/teams/${teamId}/readiness`);
}

export function fetchStudentProfile(teamId: string, studentId: string): Promise<CoachStudentProfile> {
  return apiFetch<CoachStudentProfile>(`/teams/${teamId}/students/${studentId}`);
}

export function fetchAssignmentForSpeech(speechId: string): Promise<AssignmentForSpeech> {
  return apiFetch<AssignmentForSpeech>(`/assignments/for-speech/${speechId}`);
}

/** Student begins their assignment with a freshly created speech. */
export function startAssignment(recipientId: string, speechId: string): Promise<unknown> {
  return apiFetch(`/assignments/recipients/${recipientId}/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ speech_id: speechId }),
  });
}

export function reviewAssignment(
  recipientId: string, action: "reviewed" | "revision_requested", coachFeedback?: string,
): Promise<unknown> {
  return apiFetch(`/assignments/recipients/${recipientId}/review`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, coach_feedback: coachFeedback ?? null }),
  });
}

// ── Pure helpers ────────────────────────────────────────────────────────────────

export const RECIPIENT_STATE_LABEL: Record<RecipientState, string> = {
  assigned: "Not started",
  started: "In progress",
  processing: "Processing",
  ready_for_review: "Ready for review",
  failed: "Analysis failed",
  reviewed: "Reviewed",
  revision_requested: "Revision requested",
};

export const RECIPIENT_STATE_TONE: Record<RecipientState, "ink" | "warn" | "ok" | "danger" | "lav"> = {
  assigned: "ink",
  started: "lav",
  processing: "lav",
  ready_for_review: "warn",
  failed: "danger",
  reviewed: "ok",
  revision_requested: "danger",
};

/** Statuses that still need someone to act before the loop is closed. */
const OUTSTANDING: RecipientState[] = ["assigned", "started", "processing", "ready_for_review", "failed"];

/** An assignment is overdue if past due and any recipient is still outstanding. */
export function isOverdue(assignment: Assignment, now: Date = new Date()): boolean {
  if (!assignment.due_date) return false;
  const due = new Date(assignment.due_date + "T23:59:59");
  if (now <= due) return false;
  return assignment.recipients.some((r) => OUTSTANDING.includes(r.status));
}

/** Recipients whose analyzed work is waiting on the coach. */
export function reviewBacklog(assignments: Assignment[]): number {
  return assignments.reduce(
    (n, a) => n + a.recipients.filter((r) => r.status === "ready_for_review").length,
    0,
  );
}

/**
 * Deep-link that carries an assignment's context into the student's practice
 * route, tagging the recipient so the practice page can mark it started.
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
