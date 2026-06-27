"use client";
import { useEffect, useState, useCallback, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { createClient } from "@/lib/supabase";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import Link from "next/link";
import {
  CheckCircle, ChevronRight, ChevronLeft, BookOpen, Mic, Target, RefreshCw,
} from "lucide-react";
import { logLessonStarted, logLessonCompleted } from "@/lib/analytics";
import type { CurriculumLesson } from "@/types/training";

type SessionStep = "lesson" | "recognition" | "drill" | "speech" | "compare" | "complete";

const STEP_ORDER: SessionStep[] = ["lesson", "recognition", "drill", "speech", "compare", "complete"];

const STEP_LABEL: Record<SessionStep, string> = {
  lesson: "Learn",
  recognition: "Check",
  drill: "Drill",
  speech: "Apply",
  compare: "Compare",
  complete: "Done",
};

function StepIndicator({
  current,
  completed,
}: {
  current: SessionStep;
  completed: SessionStep[];
}) {
  const displaySteps = STEP_ORDER.filter((s) => s !== "complete");
  return (
    <div className="flex items-center gap-1.5" role="navigation" aria-label="Session progress">
      {displaySteps.map((step, i) => {
        const isDone = completed.includes(step);
        const isCurrent = step === current;
        return (
          <div key={step} className="flex items-center gap-1.5">
            <div
              className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold transition-colors ${
                isDone ? "bg-ok text-white" : isCurrent ? "bg-lav text-white" : "bg-surface-3 text-ink-faint"
              }`}
              aria-current={isCurrent ? "step" : undefined}
              aria-label={STEP_LABEL[step]}
            >
              {isDone ? <CheckCircle size={12} aria-hidden /> : i + 1}
            </div>
            {i < displaySteps.length - 1 && (
              <div className={`w-4 h-px ${isDone ? "bg-ok" : "bg-hairline"}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}

function LearnStepView({ lesson, onNext }: { lesson: CurriculumLesson; onNext: () => void }) {
  return (
    <div className="space-y-5">
      <div className="flex items-start gap-3">
        <div className="w-8 h-8 rounded-lg bg-lav/10 flex items-center justify-center shrink-0">
          <BookOpen size={15} className="text-lav" aria-hidden />
        </div>
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-lav">What is it?</p>
          <p className="text-[13px] text-ink mt-1 leading-relaxed">{lesson.what_is_it}</p>
        </div>
      </div>
      <div className="rounded-xl border border-hairline bg-surface-1 px-4 py-3 space-y-1">
        <p className="text-[10px] font-semibold uppercase tracking-wide text-ink-subtle">Why judges care</p>
        <p className="text-[12px] text-ink-subtle leading-relaxed">{lesson.why_judges_care}</p>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-xl border border-danger/20 bg-danger/5 px-3 py-2.5">
          <p className="text-[10px] font-semibold text-danger mb-1">Weak</p>
          <p className="text-[12px] text-ink italic leading-relaxed">&ldquo;{lesson.weak_example}&rdquo;</p>
        </div>
        <div className="rounded-xl border border-ok/20 bg-ok/5 px-3 py-2.5">
          <p className="text-[10px] font-semibold text-ok mb-1">Strong</p>
          <p className="text-[12px] text-ink leading-relaxed">&ldquo;{lesson.strong_example}&rdquo;</p>
        </div>
      </div>
      <div className="rounded-xl border border-lav/20 bg-lav/5 px-3 py-2.5">
        <p className="text-[10px] font-semibold uppercase tracking-wide text-lav mb-1">What changed</p>
        <p className="text-[12px] text-ink-subtle leading-relaxed">{lesson.what_changed}</p>
      </div>
      <Button onClick={onNext} className="w-full">
        I understand — check recognition <ChevronRight size={13} className="ml-1" />
      </Button>
    </div>
  );
}

function RecognitionStepView({
  lesson, onNext, onBack,
}: { lesson: CurriculumLesson; onNext: () => void; onBack: () => void }) {
  const [answered, setAnswered] = useState(false);
  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-hairline bg-surface-1 px-4 py-4">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-lav mb-2">Recognition check</p>
        <p className="text-[13px] text-ink leading-relaxed">{lesson.recognition_check}</p>
      </div>
      {!answered ? (
        <Button onClick={() => setAnswered(true)} className="w-full">I can answer this</Button>
      ) : (
        <div className="space-y-3">
          <div className="rounded-xl border border-ok/20 bg-ok/5 px-3 py-2.5">
            <p className="text-[12px] text-ok">Good — apply this in your drill.</p>
          </div>
          <div className="flex gap-3">
            <Button variant="secondary" onClick={onBack} className="flex-1">
              <ChevronLeft size={13} className="mr-1" /> Back
            </Button>
            <Button onClick={onNext} className="flex-1">Go to drill <ChevronRight size={13} className="ml-1" /></Button>
          </div>
        </div>
      )}
    </div>
  );
}

function DrillStepView({
  lesson, onNext, onBack,
}: { lesson: CurriculumLesson; onNext: () => void; onBack: () => void }) {
  const [done, setDone] = useState(false);
  return (
    <div className="space-y-4">
      <div className="flex items-start gap-3">
        <div className="w-8 h-8 rounded-lg bg-warn/10 flex items-center justify-center shrink-0">
          <Target size={15} className="text-warn" aria-hidden />
        </div>
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-warn">Micro drill</p>
          <p className="text-[13px] text-ink mt-1 leading-relaxed">{lesson.micro_drill}</p>
        </div>
      </div>
      <div className="rounded-xl border border-hairline bg-surface-1 px-4 py-3 space-y-2">
        <p className="text-[10px] font-semibold uppercase tracking-wide text-ink-subtle">Success criteria</p>
        {(lesson.success_checklist as string[]).map((c, i) => (
          <p key={i} className="text-[12px] text-ink flex items-start gap-1.5">
            <CheckCircle size={11} className="shrink-0 mt-0.5 text-ink-faint" aria-hidden />
            {c}
          </p>
        ))}
      </div>
      {!done ? (
        <div className="flex gap-3">
          <Button variant="secondary" onClick={onBack} className="flex-1"><ChevronLeft size={13} className="mr-1" /> Back</Button>
          <Button onClick={() => setDone(true)} className="flex-1">I completed the drill</Button>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="rounded-xl border border-ok/20 bg-ok/5 px-3 py-2.5">
            <p className="text-[12px] text-ok">Drill complete — apply it in a speech.</p>
          </div>
          <Button onClick={onNext} className="w-full">Record speech <ChevronRight size={13} className="ml-1" /></Button>
        </div>
      )}
    </div>
  );
}

function SpeechStepView({
  lesson, lessonId, onNext, onBack,
}: { lesson: CurriculumLesson; lessonId: string; onNext: () => void; onBack: () => void }) {
  return (
    <div className="space-y-4">
      <div className="flex items-start gap-3">
        <div className="w-8 h-8 rounded-lg bg-lav/10 flex items-center justify-center shrink-0">
          <Mic size={15} className="text-lav" aria-hidden />
        </div>
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-lav">Apply in a speech</p>
          <p className="text-[13px] text-ink mt-1 leading-relaxed">{lesson.speech_application}</p>
        </div>
      </div>
      <div className="rounded-2xl border border-lav/20 bg-lav/5 px-5 py-6 text-center space-y-3">
        <Mic size={28} className="mx-auto text-lav" aria-hidden />
        <p className="text-[13px] font-semibold text-ink">Record a practice speech</p>
        <p className="text-[12px] text-ink-subtle">
          RoundLab will analyze it and update your {lesson.title} mastery score.
        </p>
        <Link href={`/session?lesson=${lessonId}`}>
          <Button className="px-6">Go to Recording Studio</Button>
        </Link>
      </div>
      <div className="flex gap-3">
        <Button variant="secondary" onClick={onBack} className="flex-1"><ChevronLeft size={13} className="mr-1" /> Back</Button>
        <Button variant="secondary" onClick={onNext} className="flex-1">Skip to compare</Button>
      </div>
    </div>
  );
}

function CompareStepView({ onComplete }: { onComplete: () => void }) {
  return (
    <div className="space-y-4">
      <div className="flex items-start gap-3">
        <div className="w-8 h-8 rounded-lg bg-ok/10 flex items-center justify-center shrink-0">
          <RefreshCw size={15} className="text-ok" aria-hidden />
        </div>
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-ok">Before vs After</p>
          <p className="text-[13px] text-ink mt-1">
            After submitting a speech and re-recording, your improvement and mastery update appear here.
          </p>
        </div>
      </div>
      <div className="rounded-2xl border border-hairline bg-surface-1 px-5 py-6 text-center space-y-3">
        <p className="text-[13px] text-ink-subtle">
          Submit a speech, receive analysis, then re-record to see the comparison.
        </p>
        <Link href="/session">
          <Button variant="secondary" className="px-6">Record re-submission</Button>
        </Link>
      </div>
      <Button onClick={onComplete} className="w-full">
        <CheckCircle size={13} className="mr-1.5" aria-hidden />
        Mark lesson complete
      </Button>
    </div>
  );
}

function LessonPlayerInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const lessonId = searchParams.get("lesson") ?? "";

  const [authLoading, setAuthLoading] = useState(true);
  const [userId, setUserId] = useState<string | null>(null);
  const [lesson, setLesson] = useState<CurriculumLesson | null>(null);
  const [loading, setLoading] = useState(true);
  const [step, setStep] = useState<SessionStep>("lesson");
  const [completed, setCompleted] = useState<SessionStep[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    createClient().auth.getUser()
      .then(({ data }) => {
        if (!data.user) { router.replace("/login?next=/training"); return; }
        setUserId(data.user.id);
      })
      .catch(() => router.replace("/login?next=/training"))
      .finally(() => setAuthLoading(false));
  }, [router]);

  useEffect(() => {
    if (!lessonId || authLoading || !userId) return;
    apiFetch<CurriculumLesson>(`/training/curriculum/lesson/${lessonId}`)
      .then(async (l) => {
        setLesson(l);
        logLessonStarted(userId, lessonId, l.skill_id ?? "");
        try {
          const session = await apiFetch<{ id?: string; current_step?: string; steps_completed?: string[] }>(
            "/training/sessions",
            { method: "POST", body: JSON.stringify({ lesson_id: lessonId }) },
          );
          if (session?.id) {
            setSessionId(session.id);
            // Resume from where we left off
            if (session.current_step) setStep(session.current_step as SessionStep);
            if (session.steps_completed?.length) setCompleted(session.steps_completed as SessionStep[]);
          }
        } catch { /* session creation non-fatal */ }
      })
      .catch(() => setErr("Could not load lesson."))
      .finally(() => setLoading(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lessonId, authLoading, userId]);

  const advanceStep = useCallback((from: SessionStep) => {
    const idx = STEP_ORDER.indexOf(from);
    const next = STEP_ORDER[idx + 1] ?? "complete";
    setCompleted((c) => [...c.filter((s) => s !== from), from]);
    setStep(next);
    if (sessionId) {
      apiFetch(`/training/sessions/${sessionId}`, {
        method: "PATCH",
        body: JSON.stringify({ current_step: next, steps_completed: [...completed, from] }),
      }).catch(() => {});
    }
  }, [sessionId, completed]);

  const backStep = useCallback((from: SessionStep) => {
    const idx = STEP_ORDER.indexOf(from);
    setStep(STEP_ORDER[Math.max(0, idx - 1)]);
  }, []);

  async function handleComplete() {
    if (!lessonId || !userId) return;
    try {
      await apiFetch("/training/progress/lesson", {
        method: "POST",
        body: JSON.stringify({ lesson_id: lessonId, status: "completed" }),
      });
      if (sessionId) {
        await apiFetch(`/training/sessions/${sessionId}`, {
          method: "PATCH",
          body: JSON.stringify({ status: "completed" }),
        });
      }
      logLessonCompleted(userId, lessonId, lesson?.skill_id ?? "");
      setDone(true);
    } catch {
      setErr("Could not save completion. Try again.");
    }
  }

  if (authLoading || loading) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-8 space-y-4">
        {[1, 2, 3].map((i) => <Skeleton key={i} className="h-16 rounded-xl" />)}
      </div>
    );
  }

  if (!lessonId) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-8">
        <p className="text-[13px] text-ink-subtle">No lesson specified.</p>
        <Link href="/training" className="text-[12px] text-lav underline mt-2 block">Back to Training</Link>
      </div>
    );
  }

  if (err) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-8">
        <p className="text-[13px] text-danger">{err}</p>
        <Link href="/training" className="text-[12px] text-lav underline mt-2 block">Back to Training</Link>
      </div>
    );
  }

  if (done || step === "complete") {
    return (
      <div className="max-w-2xl mx-auto px-4 py-8 text-center space-y-4">
        <div className="w-14 h-14 rounded-full bg-ok/10 flex items-center justify-center mx-auto">
          <CheckCircle size={28} className="text-ok" aria-hidden />
        </div>
        <h1 className="text-xl font-bold text-ink">{lesson?.title} — complete</h1>
        <p className="text-[13px] text-ink-subtle">
          Your mastery score updated. Keep practicing to advance.
        </p>
        <div className="flex gap-3 justify-center">
          <Link href="/training"><Button variant="secondary">Back to Training</Button></Link>
          {lesson?.recommended_next && (
            <Link href={`/lesson?lesson=${lesson.recommended_next}`}>
              <Button>Next Lesson →</Button>
            </Link>
          )}
        </div>
      </div>
    );
  }

  if (!lesson) return null;

  return (
    <div className="max-w-2xl mx-auto px-4 py-8 space-y-6">
      <div className="space-y-3">
        <Link href="/training" className="text-[11px] text-ink-subtle hover:text-ink flex items-center gap-1">
          <ChevronLeft size={11} aria-hidden /> Training
        </Link>
        <h1 className="text-xl font-bold text-ink">{lesson.title}</h1>
        <div className="flex items-center justify-between">
          <StepIndicator current={step} completed={completed} />
          <p className="text-[11px] text-ink-subtle">{lesson.estimated_minutes} min</p>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <span className="text-[11px] font-semibold uppercase tracking-wide text-lav">
          {STEP_LABEL[step]}
        </span>
        <span className="text-[11px] text-ink-faint">
          step {STEP_ORDER.indexOf(step) + 1} of {STEP_ORDER.length - 1}
        </span>
      </div>

      {step === "lesson" && <LearnStepView lesson={lesson} onNext={() => advanceStep("lesson")} />}
      {step === "recognition" && (
        <RecognitionStepView lesson={lesson} onNext={() => advanceStep("recognition")} onBack={() => backStep("recognition")} />
      )}
      {step === "drill" && (
        <DrillStepView lesson={lesson} onNext={() => advanceStep("drill")} onBack={() => backStep("drill")} />
      )}
      {step === "speech" && (
        <SpeechStepView lesson={lesson} lessonId={lessonId} onNext={() => advanceStep("speech")} onBack={() => backStep("speech")} />
      )}
      {step === "compare" && <CompareStepView onComplete={handleComplete} />}
    </div>
  );
}

export default function LessonPage() {
  return (
    <Suspense fallback={
      <div className="max-w-2xl mx-auto px-4 py-8 space-y-4">
        {[1, 2, 3].map((i) => <div key={i} className="h-16 rounded-xl bg-surface-2 animate-pulse" />)}
      </div>
    }>
      <LessonPlayerInner />
    </Suspense>
  );
}
