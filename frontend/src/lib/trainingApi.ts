import { apiFetch } from "@/lib/api";
import type {
  MasteryProfile, MasteryScore, TrainingPlan,
  CurriculumLesson, CurriculumProgress, DiagnosticData,
  PracticeAgendaItem, Skill,
} from "@/types/training";

export async function fetchMasteryProfile(): Promise<MasteryProfile> {
  return apiFetch<MasteryProfile>("/training/mastery");
}

export async function addMasteryEvidence(payload: {
  skill_id: string;
  raw_score: number;
  source_type: string;
  source_id?: string;
  change_reason?: string;
  input_scale?: string;
}): Promise<MasteryScore> {
  return apiFetch<MasteryScore>("/training/mastery/evidence", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function fetchActivePlan(): Promise<TrainingPlan | null> {
  try {
    return await apiFetch<TrainingPlan>("/training/plans");
  } catch {
    return null;
  }
}

export async function generatePlan(payload: {
  plan_type: string;
  tournament_date?: string;
  coach_priority_skills?: string[];
}): Promise<TrainingPlan> {
  return apiFetch<TrainingPlan>("/training/plans/generate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function fetchCurriculum(): Promise<CurriculumLesson[]> {
  return apiFetch<CurriculumLesson[]>("/training/curriculum");
}

export async function fetchLesson(lessonId: string): Promise<CurriculumLesson> {
  return apiFetch<CurriculumLesson>(`/training/curriculum/lesson/${lessonId}`);
}

export async function markLessonComplete(lessonId: string, score?: number): Promise<CurriculumProgress> {
  return apiFetch<CurriculumProgress>("/training/progress/lesson", {
    method: "POST",
    body: JSON.stringify({ lesson_id: lessonId, status: "completed", score }),
  });
}

export async function fetchProgress(): Promise<CurriculumProgress[]> {
  return apiFetch<CurriculumProgress[]>("/training/progress");
}

export async function fetchDiagnostic(): Promise<DiagnosticData | null> {
  try {
    return await apiFetch<DiagnosticData>("/training/diagnostic");
  } catch {
    return null;
  }
}

export async function startDiagnostic(payload: {
  experience_level: string;
  intake_data: Record<string, unknown>;
}): Promise<{ diagnostic_id: string; status: string }> {
  return apiFetch("/training/diagnostic/start", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function completeDiagnostic(payload: {
  diagnostic_id: string;
  speech_scores?: Record<string, number>;
}): Promise<{ mastery_profile: MasteryProfile; strengths: string[]; priorities: string[]; first_plan: TrainingPlan }> {
  return apiFetch("/training/diagnostic/complete", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function fetchSkills(): Promise<Skill[]> {
  return apiFetch<Skill[]>("/training/skills");
}

export async function fetchPracticeAgenda(teamId: string, durationMinutes: number = 60): Promise<PracticeAgendaItem[]> {
  return apiFetch<PracticeAgendaItem[]>("/training/practice-agenda", {
    method: "POST",
    body: JSON.stringify({ team_id: teamId, duration_minutes: durationMinutes }),
  });
}
