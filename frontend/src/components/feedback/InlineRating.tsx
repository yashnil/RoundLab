"use client";

import { useState } from "react";
import { ThumbsUp, ThumbsDown, Minus } from "lucide-react";
import { logEvent } from "@/lib/analytics";

type Rating = "yes" | "no" | "unsure";

interface InlineRatingProps {
  /** Short question shown to the user */
  question: string;
  /** Feature/context identifier for analytics */
  feature: string;
  /** Optional: link to a resource (evidence card, drill, flow, etc.) */
  resourceId?: string;
  /** User ID for attribution */
  userId?: string;
  /** Called after a rating is submitted */
  onRated?: (rating: Rating, comment?: string) => void;
  /** Show optional comment field */
  allowComment?: boolean;
  /** Compact single-line layout */
  compact?: boolean;
}

export default function InlineRating({
  question,
  feature,
  resourceId,
  userId,
  onRated,
  allowComment = false,
  compact = false,
}: InlineRatingProps) {
  const [rating, setRating] = useState<Rating | null>(null);
  const [comment, setComment] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [showComment, setShowComment] = useState(false);

  const submit = (r: Rating) => {
    setRating(r);
    logEvent(`feedback_${feature}_rated`, userId ?? "", {
      rating: r,
      resource_id: resourceId,
    });
    if (allowComment && r === "no") {
      setShowComment(true);
    } else {
      setSubmitted(true);
      onRated?.(r);
    }
  };

  const submitWithComment = () => {
    setSubmitted(true);
    onRated?.(rating!, comment.trim() || undefined);
    logEvent(`feedback_${feature}_comment`, userId ?? "", {
      comment_length: comment.trim().length,
    });
  };

  if (submitted) {
    return (
      <p className="text-xs text-[var(--ink-subtle)] py-1" aria-live="polite">
        Thanks for your feedback.
      </p>
    );
  }

  const buttons: { value: Rating; label: string; icon: React.ReactNode }[] = [
    { value: "yes", label: "Yes", icon: <ThumbsUp className="w-3.5 h-3.5" /> },
    { value: "no", label: "No", icon: <ThumbsDown className="w-3.5 h-3.5" /> },
    { value: "unsure", label: "Not sure", icon: <Minus className="w-3.5 h-3.5" /> },
  ];

  return (
    <div
      className={compact ? "flex items-center gap-2" : "flex flex-col gap-2"}
      role="group"
      aria-label={question}
    >
      <span className="text-xs text-[var(--ink-subtle)]">{question}</span>

      <div className="flex items-center gap-1.5">
        {buttons.map(({ value, label, icon }) => (
          <button
            key={value}
            onClick={() => submit(value)}
            className={[
              "flex items-center gap-1 px-2 py-1 rounded text-xs border transition-colors focus-ring",
              rating === value
                ? "bg-[var(--lavender-light)] border-[var(--lavender)] text-[var(--lavender)]"
                : "border-[var(--border-subtle)] text-[var(--ink-subtle)] hover:border-[var(--lavender)] hover:text-[var(--lavender)]",
            ].join(" ")}
            aria-pressed={rating === value}
          >
            {icon}
            {label}
          </button>
        ))}
      </div>

      {showComment && (
        <div className="flex flex-col gap-1.5 mt-1">
          <label className="text-xs text-[var(--ink-subtle)]" htmlFor="inline-comment">
            What went wrong? (optional)
          </label>
          <input
            id="inline-comment"
            type="text"
            maxLength={200}
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Short note…"
            className="text-xs border border-[var(--border-subtle)] rounded px-2 py-1 bg-transparent focus:outline-none focus:border-[var(--lavender)]"
          />
          <button
            onClick={submitWithComment}
            className="self-start text-xs px-2 py-1 rounded bg-[var(--lavender)] text-white focus-ring"
          >
            Submit
          </button>
        </div>
      )}
    </div>
  );
}
