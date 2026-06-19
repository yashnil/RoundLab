"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  ClipboardCheck, Check, RotateCcw, ChevronLeft, ChevronRight, Plus, GraduationCap,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  fetchAssignmentForSpeech, fetchReviewQueue, reviewAssignment,
  RECIPIENT_STATE_LABEL, RECIPIENT_STATE_TONE,
} from "@/lib/assignments";
import type { AssignmentForSpeech, ReviewQueueItem, RecipientState } from "@/types";
import { cn } from "@/lib/utils";

const TONE_CLS: Record<"ink" | "warn" | "ok" | "danger" | "lav", string> = {
  ink: "border-hairline bg-surface-2 text-ink-subtle",
  warn: "border-warn/30 bg-warn/10 text-warn",
  ok: "border-ok/30 bg-ok/10 text-ok",
  danger: "border-danger/30 bg-danger/10 text-danger",
  lav: "border-lav/30 bg-lav/10 text-lav",
};

function StatusBadge({ status }: { status: RecipientState }) {
  return (
    <span className={cn("rounded-full border px-2 py-0.5 text-[10px] font-semibold", TONE_CLS[RECIPIENT_STATE_TONE[status]])}>
      {RECIPIENT_STATE_LABEL[status]}
    </span>
  );
}

/**
 * Compact coach review rail shown on a team student's report. Reuses the
 * existing for-speech + review endpoints and their permission logic — it never
 * duplicates the report. Coaches get review actions + next/previous; the student
 * owner sees their assignment status and any coach feedback (read-only).
 */
export default function CoachReviewRail({ speechId }: { speechId: string }) {
  const [data, setData] = useState<AssignmentForSpeech | null>(null);
  const [queue, setQueue] = useState<ReviewQueueItem[]>([]);
  const [feedback, setFeedback] = useState("");
  const [status, setStatus] = useState<RecipientState | null>(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetchAssignmentForSpeech(speechId)
      .then((d) => {
        if (cancelled) return;
        setData(d);
        setStatus(d.recipient?.status ?? null);
        setFeedback(d.recipient?.coach_feedback ?? "");
        if (d.viewer_is_coach && d.assignment) {
          fetchReviewQueue(d.assignment.team_id).then((q) => { if (!cancelled) setQueue(q); }).catch(() => {});
        }
      })
      .catch(() => { /* no assignment / not permitted → rail stays hidden */ });
    return () => { cancelled = true; };
  }, [speechId]);

  const { prev, next } = useMemo(() => {
    const idx = queue.findIndex((q) => q.submission_speech_id === speechId);
    return {
      prev: idx > 0 ? queue[idx - 1] : null,
      next: idx >= 0 && idx < queue.length - 1 ? queue[idx + 1] : null,
    };
  }, [queue, speechId]);

  if (!data?.assignment || !data.recipient) return null;
  const { assignment, recipient, viewer_is_coach } = data;

  async function act(action: "reviewed" | "revision_requested") {
    setBusy(true);
    try {
      await reviewAssignment(recipient.id, action, feedback || undefined);
      setStatus(action);
      setDone(true);
    } catch { /* surfaced by disabled state lifting */ }
    finally { setBusy(false); }
  }

  return (
    <section
      aria-label="Assignment review"
      className="rounded-2xl border border-authored-coach/30 bg-authored-coach/[0.05] p-4"
    >
      <div className="mb-3 flex items-center justify-between gap-2">
        <span className="flex items-center gap-1.5 text-eyebrow text-authored-coach">
          <ClipboardCheck size={13} aria-hidden /> {viewer_is_coach ? "Coach review" : "Assignment"}
        </span>
        {status && <StatusBadge status={status} />}
      </div>

      <p className="text-sm font-semibold text-ink">{assignment.title}</p>
      {assignment.goal && <p className="mt-0.5 text-xs text-ink-subtle">Goal: {assignment.goal}</p>}
      {assignment.success_criteria.length > 0 && (
        <ul className="mt-2 flex flex-col gap-1">
          {assignment.success_criteria.map((c, i) => (
            <li key={i} className="flex items-start gap-1.5 text-xs text-ink-subtle">
              <Check size={11} className="mt-0.5 shrink-0 text-ok" aria-hidden /> {c}
            </li>
          ))}
        </ul>
      )}

      {viewer_is_coach ? (
        <div className="mt-3 flex flex-col gap-2 border-t border-authored-coach/15 pt-3">
          <label htmlFor="rail-feedback" className="text-[10px] font-semibold uppercase tracking-wide text-ink-faint">Coach feedback</label>
          <textarea
            id="rail-feedback" value={feedback} onChange={(e) => setFeedback(e.target.value)}
            placeholder="What landed, the one fix, the next rep…"
            className="h-24 w-full resize-none rounded-md border border-hairline bg-surface-2 px-3 py-2 text-sm text-ink outline-none focus-visible:border-lav/50 focus-visible:ring-2 focus-visible:ring-lav/20"
          />
          {done && <p className="text-xs text-ok">Saved. {next ? "Move to the next submission." : "That was the last in the queue."}</p>}
          <div className="flex flex-wrap gap-2">
            <Button onClick={() => act("reviewed")} disabled={busy} size="sm" className="gap-1.5"><Check size={12} /> Mark reviewed</Button>
            <Button onClick={() => act("revision_requested")} disabled={busy} size="sm" variant="secondary" className="gap-1.5"><RotateCcw size={12} /> Request revision</Button>
            <Button asChild size="sm" variant="secondary" className="gap-1.5">
              <Link href={`/team/assign?team=${assignment.team_id}`}><Plus size={12} /> Assign follow-up</Link>
            </Button>
          </div>
          {(prev || next) && (
            <div className="flex items-center justify-between border-t border-authored-coach/15 pt-2">
              {prev?.submission_speech_id
                ? <Link href={`/speech/${prev.submission_speech_id}`} className="flex items-center gap-1 text-xs text-lav hover:underline"><ChevronLeft size={12} /> Previous</Link>
                : <span />}
              <Link href={`/team/review?team=${assignment.team_id}`} className="text-xs text-ink-subtle hover:text-ink">Review queue</Link>
              {next?.submission_speech_id
                ? <Link href={`/speech/${next.submission_speech_id}`} className="flex items-center gap-1 text-xs text-lav hover:underline">Next <ChevronRight size={12} /></Link>
                : <span />}
            </div>
          )}
        </div>
      ) : recipient.coach_feedback ? (
        <div className="mt-3 flex flex-col gap-1 border-t border-authored-coach/15 pt-3">
          <span className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide text-authored-coach"><GraduationCap size={11} aria-hidden /> Coach feedback</span>
          <p className="text-sm text-ink">{recipient.coach_feedback}</p>
        </div>
      ) : null}
    </section>
  );
}
