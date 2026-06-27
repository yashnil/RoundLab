"use client";
import { useState, useEffect } from "react";
import { apiFetch } from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import {
  CheckCircle, Clock, BookOpen, AlertTriangle, ChevronRight,
} from "lucide-react";
import type { CurriculumLesson } from "@/types/training";

interface LessonProgress {
  lesson_id: string;
  status: "not_started" | "in_progress" | "completed";
  completed_at?: string;
}

interface StudentCurriculumRow {
  student_id: string;
  student_name?: string;
  progress: LessonProgress[];
}

interface Props {
  teamId: string;
  coachId: string;
}

const STATUS_ICON: Record<string, React.ReactNode> = {
  completed: <CheckCircle size={13} className="text-ok" aria-hidden />,
  in_progress: <Clock size={13} className="text-lav" aria-hidden />,
  not_started: <div className="w-3 h-3 rounded-full border border-ink-faint" aria-hidden />,
};

export default function CurriculumPanel({ teamId, coachId }: Props) {
  const [lessons, setLessons] = useState<CurriculumLesson[]>([]);
  const [students, setStudents] = useState<StudentCurriculumRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [validation, setValidation] = useState<{ valid: boolean; errors: string[] } | null>(null);
  const [validLoading, setValidLoading] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [lessonsData, progressData] = await Promise.all([
          apiFetch<CurriculumLesson[]>("/training/curriculum"),
          apiFetch<StudentCurriculumRow[]>(
            `/training/curriculum/team-progress?team_id=${teamId}&coach_id=${coachId}`,
          ).catch(() => []),
        ]);
        setLessons(lessonsData || []);
        setStudents(progressData || []);
      } catch {
        setErr("Could not load curriculum data.");
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [teamId, coachId]);

  async function runValidation() {
    setValidLoading(true);
    try {
      const result = await apiFetch<{ valid: boolean; errors: string[]; warnings: string[] }>(
        "/training/curriculum/validate",
      );
      setValidation({ valid: result.valid, errors: result.errors });
    } catch {
      setValidation({ valid: false, errors: ["Validation request failed"] });
    } finally {
      setValidLoading(false);
    }
  }

  function getLessonProgress(student: StudentCurriculumRow, lessonId: string): LessonProgress {
    return (
      student.progress.find((p) => p.lesson_id === lessonId) ?? {
        lesson_id: lessonId,
        status: "not_started",
      }
    );
  }

  function countCompleted(student: StudentCurriculumRow): number {
    return student.progress.filter((p) => p.status === "completed").length;
  }

  if (loading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-12 rounded-xl" />
        ))}
      </div>
    );
  }

  if (err) {
    return (
      <div className="flex items-start gap-3 rounded-xl border border-danger/25 bg-danger/5 px-4 py-3">
        <AlertTriangle size={16} className="shrink-0 text-danger mt-0.5" aria-hidden />
        <p className="text-[13px] text-danger">{err}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Curriculum overview */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-subtle">
            Curriculum — {lessons.length} lessons
          </p>
          <Button
            variant="secondary"
            className="text-[11px] h-7 px-3"
            onClick={runValidation}
            disabled={validLoading}
          >
            {validLoading ? "Validating…" : "Validate curriculum"}
          </Button>
        </div>

        {validation && (
          <div
            className={`rounded-xl border px-3 py-2 text-[12px] ${
              validation.valid
                ? "border-ok/20 bg-ok/5 text-ok"
                : "border-danger/20 bg-danger/5 text-danger"
            }`}
          >
            {validation.valid
              ? "All 11 lessons pass curriculum validation."
              : `${validation.errors.length} error(s): ${validation.errors.slice(0, 3).join(" · ")}`}
          </div>
        )}

        <div className="divide-y divide-hairline rounded-2xl border border-hairline overflow-hidden">
          {lessons.map((lesson) => (
            <div
              key={lesson.id}
              className="flex items-center gap-3 px-4 py-3 bg-surface-1 hover:bg-surface-2 transition-colors"
            >
              <BookOpen size={13} className="text-ink-faint shrink-0" aria-hidden />
              <div className="flex-1 min-w-0">
                <p className="text-[12px] font-semibold text-ink truncate">{lesson.title}</p>
                <p className="text-[10px] text-ink-subtle">{lesson.estimated_minutes} min · {lesson.difficulty}</p>
              </div>
              <Link
                href={`/lesson?lesson=${lesson.id}`}
                className="text-[11px] text-lav hover:underline flex items-center gap-0.5"
              >
                Preview <ChevronRight size={11} aria-hidden />
              </Link>
            </div>
          ))}
        </div>
      </div>

      {/* Student progress grid */}
      {students.length > 0 && (
        <div className="space-y-3">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-subtle">
            Student progress
          </p>
          <div className="overflow-x-auto rounded-2xl border border-hairline">
            <table className="min-w-full text-[11px]">
              <thead>
                <tr className="border-b border-hairline bg-surface-2">
                  <th className="text-left px-4 py-2.5 text-ink-subtle font-semibold">Student</th>
                  <th className="text-left px-3 py-2.5 text-ink-subtle font-semibold">Done</th>
                  {lessons.slice(0, 8).map((l) => (
                    <th key={l.id} className="px-2 py-2.5 text-ink-subtle font-normal">
                      <span className="block truncate max-w-[60px]" title={l.title}>
                        {l.title.split(" ")[0]}
                      </span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {students.map((s) => (
                  <tr key={s.student_id} className="border-b border-hairline last:border-0 bg-surface-1 hover:bg-surface-2">
                    <td className="px-4 py-2.5 text-ink font-medium">
                      {s.student_name ?? s.student_id.slice(0, 8)}
                    </td>
                    <td className="px-3 py-2.5 text-ink-subtle">
                      {countCompleted(s)}/{lessons.length}
                    </td>
                    {lessons.slice(0, 8).map((l) => {
                      const p = getLessonProgress(s, l.id);
                      return (
                        <td key={l.id} className="px-2 py-2.5 text-center">
                          {STATUS_ICON[p.status]}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
