"use client";

/**
 * DrillRating — small helpfulness rating shown after a drill attempt is scored.
 * "Did this drill help you understand what to fix?"
 * One rating per drill (upserts on resubmit).
 */

import { useState } from "react";
import { CheckCircle2, ThumbsUp, Minus, ThumbsDown } from "lucide-react";
import type { DrillRating as DrillRatingType, DrillRatingRow } from "@/types";

interface Props {
  drillId: string;
  userId: string;
  drillAttemptId?: string | null;
  initialRating?: DrillRatingType | null;
  onRated?: (row: DrillRatingRow) => void;
}

const OPTIONS: Array<{
  value: DrillRatingType;
  label: string;
  icon: React.ElementType;
  activeClass: string;
}> = [
  { value: "helpful",     label: "Yes",       icon: ThumbsUp,   activeClass: "border-ok/40 bg-ok/10 text-ok" },
  { value: "somewhat",    label: "A little",  icon: Minus,      activeClass: "border-warn/40 bg-warn/10 text-warn" },
  { value: "not_helpful", label: "No",        icon: ThumbsDown, activeClass: "border-danger/40 bg-danger/10 text-danger" },
];

export default function DrillRating({ drillId, userId, drillAttemptId, initialRating, onRated }: Props) {
  const [selected, setSelected] = useState<DrillRatingType | null>(initialRating ?? null);
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(!!initialRating);
  const [err, setErr] = useState("");

  async function submit(rating: DrillRatingType) {
    if (submitting) return;
    setSelected(rating);
    setSubmitting(true);
    setErr("");
    try {
      const { apiFetch } = await import("@/lib/api");
      const row = await apiFetch<DrillRatingRow>(`/drills/${drillId}/rating?user_id=${userId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          rating,
          comment: comment || undefined,
          drill_attempt_id: drillAttemptId ?? undefined,
        }),
      });
      setSubmitted(true);
      onRated?.(row);
    } catch {
      setErr("Could not save rating. Try again.");
      setSubmitting(false);
    }
  }

  if (submitted) {
    return (
      <div className="flex items-center gap-2 py-1">
        <CheckCircle2 size={12} className="shrink-0 text-ok" />
        <p className="text-[11px] text-ink-subtle">Thanks — your feedback helps improve drills.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2 rounded-md border border-hairline bg-surface-2 px-3 py-3">
      <span className="section-stamp">Did this drill help?</span>
      <div className="flex flex-wrap gap-1.5">
        {OPTIONS.map(({ value, label, icon: Icon, activeClass }) => (
          <button
            key={value}
            type="button"
            disabled={submitting}
            onClick={() => submit(value)}
            className={[
              "flex items-center gap-1 rounded-[3px] border px-2.5 py-1 text-[10px] font-medium transition-all",
              selected === value
                ? activeClass
                : "border-hairline bg-surface-1 text-ink-faint hover:border-lav/30 hover:text-ink",
            ].join(" ")}
          >
            <Icon size={10} />
            {label}
          </button>
        ))}
      </div>

      {selected && !submitted && (
        <input
          type="text"
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          placeholder="What would make this drill better? (optional)"
          className="w-full rounded-md border border-hairline bg-surface-1 px-2.5 py-1.5 text-[10px] text-ink placeholder:text-ink-faint focus:border-lav/40 focus:outline-none"
          onKeyDown={(e) => { if (e.key === "Enter") submit(selected); }}
        />
      )}

      {err && <p className="text-[10px] text-danger">{err}</p>}
    </div>
  );
}
