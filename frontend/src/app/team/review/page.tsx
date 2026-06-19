"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, ArrowRight, ChevronLeft, ChevronRight, Check, RotateCcw, ExternalLink, Inbox } from "lucide-react";
import AppShell from "@/components/shell/AppShell";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { createClient } from "@/lib/supabase";
import { fetchReviewQueue, reviewAssignment } from "@/lib/assignments";
import type { ReviewQueueItem } from "@/types";

export default function ReviewQueuePage() {
  const router = useRouter();
  const [userId, setUserId] = useState<string | null>(null);
  const [queue, setQueue] = useState<ReviewQueueItem[]>([]);
  const [active, setActive] = useState(0);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [feedback, setFeedback] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const tid = typeof window !== "undefined" ? new URLSearchParams(window.location.search).get("team") : null;
    createClient().auth.getUser()
      .then(async ({ data }) => {
        if (!data.user) { router.replace("/login"); return; }
        setUserId(data.user.id);
        if (!tid) { setErr("No team selected."); return; }
        setQueue(await fetchReviewQueue(tid));
      })
      .catch(() => setErr("Could not load the review queue. You may not have coach access."))
      .finally(() => setLoading(false));
  }, [router]);

  const item = queue[active];

  async function act(action: "reviewed" | "revision_requested") {
    if (!item || !userId) return;
    setBusy(true);
    try {
      await reviewAssignment(item.recipient_id, action, feedback || undefined);
      // Remove the reviewed item from the queue and advance.
      setQueue((q) => q.filter((_, i) => i !== active));
      setActive((a) => Math.min(a, queue.length - 2 < 0 ? 0 : queue.length - 2));
      setFeedback("");
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Could not save your review.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell maxWidth="full" bare>
      <div className="mx-auto flex max-w-3xl flex-col gap-5 px-4 py-8 sm:px-6">
        <div className="flex flex-col gap-1">
          <Link href="/team" className="flex w-fit items-center gap-1 text-xs text-ink-subtle transition-colors hover:text-ink">
            <ArrowLeft size={12} aria-hidden /> Back to team
          </Link>
          <h1 className="text-title text-ink">Review queue</h1>
          <p className="text-sm text-ink-subtle">Submitted work waiting on you — review fast, then move to the next.</p>
        </div>

        {loading ? (
          <Skeleton className="h-48 w-full rounded-xl" />
        ) : err ? (
          <p className="rounded-lg border border-danger/20 bg-danger/5 px-4 py-3 text-sm text-danger">{err}</p>
        ) : queue.length === 0 ? (
          <div className="flex flex-col items-center gap-3 rounded-xl border border-hairline bg-surface-1 px-6 py-12 text-center">
            <Inbox size={28} className="text-ink-faint" aria-hidden />
            <p className="text-sm font-semibold text-ink">Queue is clear</p>
            <p className="max-w-xs text-xs text-ink-subtle">No submissions are waiting for review. New submissions land here automatically.</p>
          </div>
        ) : item ? (
          <div className="flex flex-col gap-4 rounded-2xl border border-hairline bg-surface-1 p-5">
            {/* Position + nav */}
            <div className="flex items-center justify-between">
              <span className="text-xs text-ink-faint tabular-nums">{active + 1} of {queue.length} to review</span>
              <div className="flex gap-1">
                <button type="button" onClick={() => setActive((a) => Math.max(0, a - 1))} disabled={active === 0}
                  className="flex h-7 w-7 items-center justify-center rounded-md border border-hairline text-ink-subtle transition-colors hover:text-ink disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50" aria-label="Previous submission">
                  <ChevronLeft size={14} />
                </button>
                <button type="button" onClick={() => setActive((a) => Math.min(queue.length - 1, a + 1))} disabled={active >= queue.length - 1}
                  className="flex h-7 w-7 items-center justify-center rounded-md border border-hairline text-ink-subtle transition-colors hover:text-ink disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50" aria-label="Next submission">
                  <ChevronRight size={14} />
                </button>
              </div>
            </div>

            <div className="flex flex-col gap-1">
              <p className="text-lg font-semibold text-ink">{item.student_name || `Student ${item.student_id.slice(0, 6)}`}</p>
              <p className="text-sm text-ink-subtle">{item.assignment_title}</p>
              {item.submitted_at && <p className="text-xs text-ink-faint">Submitted {new Date(item.submitted_at).toLocaleDateString()}</p>}
            </div>

            {item.submission_speech_id && (
              <Link href={`/speech/${item.submission_speech_id}`} className="flex w-fit items-center gap-1.5 rounded-lg border border-hairline bg-surface-2 px-3 py-2 text-xs font-medium text-ink transition-colors hover:bg-surface-3">
                <ExternalLink size={12} aria-hidden /> Open their report
              </Link>
            )}

            <div className="flex flex-col gap-1.5">
              <label htmlFor="coach-fb" className="text-xs font-medium text-ink-subtle">Coach feedback</label>
              <textarea id="coach-fb" value={feedback} onChange={(e) => setFeedback(e.target.value)}
                placeholder="What landed, the one thing to fix, and the next rep…"
                className="h-28 w-full resize-none rounded-md border border-hairline bg-surface-2 px-3 py-2 text-sm text-ink outline-none focus-visible:border-lav/50 focus-visible:ring-2 focus-visible:ring-lav/20" />
            </div>

            <div className="flex flex-wrap gap-2">
              <Button onClick={() => act("reviewed")} disabled={busy} className="gap-1.5">
                <Check size={13} /> Mark reviewed
              </Button>
              <Button onClick={() => act("revision_requested")} disabled={busy} variant="secondary" className="gap-1.5">
                <RotateCcw size={13} /> Request revision
              </Button>
              {active < queue.length - 1 && (
                <Button onClick={() => setActive((a) => a + 1)} variant="secondary" className="ml-auto gap-1.5 text-ink-subtle">
                  Skip <ArrowRight size={13} />
                </Button>
              )}
            </div>
          </div>
        ) : null}
      </div>
    </AppShell>
  );
}
