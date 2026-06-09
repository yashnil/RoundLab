"use client";

/**
 * FeedbackRating — unobtrusive 3-option helpfulness rating for speech feedback reports.
 * Shows "Was this feedback useful?" with Helpful / Somewhat / Not useful.
 * Optional short comment. Shows confirmation after submit.
 */

import { useState } from "react";
import { ThumbsUp, Minus, ThumbsDown, CheckCircle2 } from "lucide-react";
import type { FeedbackRating as FeedbackRatingType } from "@/types";

interface Props {
  speechId: string;
  userId: string;
  initialRating?: FeedbackRatingType | null;
  onRated?: (rating: FeedbackRatingType) => void;
}

const OPTIONS: Array<{
  value: FeedbackRatingType;
  label: string;
  icon: React.ElementType;
  activeClass: string;
}> = [
  { value: "helpful",     label: "Helpful",     icon: ThumbsUp,   activeClass: "border-ok/40 bg-ok/10 text-ok" },
  { value: "somewhat",    label: "Somewhat",    icon: Minus,      activeClass: "border-warn/40 bg-warn/10 text-warn" },
  { value: "not_helpful", label: "Not useful",  icon: ThumbsDown, activeClass: "border-danger/40 bg-danger/10 text-danger" },
];

export default function FeedbackRating({ speechId, userId, initialRating, onRated }: Props) {
  const [selected, setSelected] = useState<FeedbackRatingType | null>(initialRating ?? null);
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(!!initialRating);
  const [err, setErr] = useState("");

  async function submit(rating: FeedbackRatingType) {
    if (submitting) return;
    setSelected(rating);
    setSubmitting(true);
    setErr("");
    try {
      const { apiFetch } = await import("@/lib/api");
      await apiFetch(`/speeches/${speechId}/feedback/rating?user_id=${userId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ helpful_rating: rating, helpful_comment: comment || undefined }),
      });
      setSubmitted(true);
      onRated?.(rating);
    } catch {
      setErr("Could not save rating. Try again.");
      setSubmitting(false);
    }
  }

  if (submitted) {
    return (
      <div className="flex items-center gap-2 py-1">
        <CheckCircle2 size={13} className="shrink-0 text-ok" />
        <p className="text-xs text-ink-subtle">Thanks — this helps improve RoundLab.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2.5">
      <span className="section-stamp">Was this feedback useful?</span>
      <div className="flex flex-wrap gap-2">
        {OPTIONS.map(({ value, label, icon: Icon, activeClass }) => (
          <button
            key={value}
            type="button"
            disabled={submitting}
            onClick={() => submit(value)}
            className={[
              "flex items-center gap-1.5 rounded-[3px] border px-3 py-1.5 text-[11px] font-medium transition-all",
              selected === value
                ? activeClass
                : "border-hairline bg-surface-2 text-ink-faint hover:border-lav/30 hover:text-ink",
            ].join(" ")}
          >
            <Icon size={11} />
            {label}
          </button>
        ))}
      </div>

      {selected && !submitted && (
        <div className="flex flex-col gap-1.5">
          <input
            type="text"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="What was confusing or missing? (optional)"
            className="w-full rounded-lg border border-hairline bg-surface-2 px-3 py-2 text-xs text-ink placeholder:text-ink-faint focus:border-lav/40 focus:outline-none"
            onKeyDown={(e) => { if (e.key === "Enter") submit(selected); }}
          />
          <p className="text-[10px] text-ink-faint">Your rating helps improve RoundLab.</p>
        </div>
      )}

      {err && <p className="text-[10px] text-danger">{err}</p>}
    </div>
  );
}
