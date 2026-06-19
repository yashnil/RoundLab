"use client";

import { useState } from "react";
import { Trash2, ChevronDown, ChevronUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";
import { blockEntryTypeLabel, coverageStatusBadgeStyle } from "@/lib/blockfileHelpers";
import type { BlockEntry } from "@/types";

export function BlockEntryCard({
  entry,
  userId,
  onDelete,
}: {
  entry: BlockEntry;
  userId: string;
  onDelete: (id: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const badge = coverageStatusBadgeStyle("no_available_block");

  async function handleDelete() {
    if (!confirm("Remove this block entry?")) return;
    setDeleting(true);
    try {
      await apiFetch(`/block-entries/${entry.id}?user_id=${userId}`, { method: "DELETE" });
      onDelete(entry.id);
    } catch {
      setDeleting(false);
    }
  }

  return (
    <div className="rounded-xl border border-hairline bg-surface-1">
      <div className="flex items-start justify-between gap-2 px-3.5 py-3">
        <div className="flex-1 min-w-0 flex flex-col gap-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span
              className="text-[10px] font-semibold rounded-full px-1.5 py-0.5"
              style={badge}
            >
              {blockEntryTypeLabel(entry.entry_type)}
            </span>
            {entry.tag && (
              <span className="text-xs font-semibold text-ink truncate">
                {entry.tag}
              </span>
            )}
          </div>
          {entry.opponent_claim && (
            <p className="text-xs text-ink-subtle leading-relaxed">
              AT: {entry.opponent_claim.length > 120 ? entry.opponent_claim.slice(0, 120) + "…" : entry.opponent_claim}
            </p>
          )}
          <p className={`text-xs text-ink leading-relaxed ${expanded ? "whitespace-pre-wrap" : "line-clamp-3"}`}>
            {entry.response_text}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          <button
            onClick={() => setExpanded((v) => !v)}
            className="text-ink-faint hover:text-ink p-1"
          >
            {expanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
          </button>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 w-7 p-0 text-ink-subtle hover:text-danger"
            onClick={handleDelete}
            disabled={deleting}
          >
            <Trash2 size={13} />
          </Button>
        </div>
      </div>
      {expanded && (
        <div className="border-t border-hairline px-3.5 pb-3 pt-2.5 flex flex-col gap-2">
          {entry.warrant_text && (
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wide text-ink-faint mb-0.5">Warrant</p>
              <p className="text-xs text-ink-subtle leading-relaxed">{entry.warrant_text}</p>
            </div>
          )}
          {entry.evidence_text && (
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wide text-ink-faint mb-0.5">Evidence</p>
              <p className="text-xs text-ink-subtle leading-relaxed">{entry.evidence_text}</p>
            </div>
          )}
          {entry.impact_text && (
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wide text-ink-faint mb-0.5">Impact</p>
              <p className="text-xs text-ink-subtle leading-relaxed">{entry.impact_text}</p>
            </div>
          )}
          {(entry.author || entry.source || entry.date) && (
            <p className="text-[10px] text-ink-faint">
              {[entry.author, entry.source, entry.date].filter(Boolean).join(" · ")}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
