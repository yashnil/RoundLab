"use client";

import type { CardDraft, SelectedSpan } from "@/types";
import { HighlightedCardText, hostnameOnly } from "./HighlightedCardText";

/**
 * Source verification drawer — collapsed by default.
 * Shows the full original passage with highlights when expanded.
 * Edit mode shows cut controls.
 */
export function SourceVerificationPanel({
  card,
  editingSpans,
  boldSpans,
  onRemoveSpan,
  isEditing,
  onEditStart,
  onEditReset,
}: {
  card: CardDraft;
  editingSpans: SelectedSpan[];
  boldSpans?: SelectedSpan[];
  onRemoveSpan: (index: number) => void;
  isEditing: boolean;
  onEditStart: () => void;
  onEditReset: () => void;
}) {
  return (
    <div className="flex flex-col gap-2 min-w-0">
      {/* Extraction method + snippet warning (compact) */}
      <div className="flex items-center gap-2 flex-wrap text-[9px] text-ink-muted">
        {card.extraction_method && (
          <span className="px-1.5 py-px rounded bg-surface-faint border border-border/40">
            via {card.extraction_method}
          </span>
        )}
        {card.is_snippet_source && (
          <span className="px-1.5 py-px rounded bg-amber-50 border border-amber-200 text-amber-700 font-medium">
            ⚠ Partial source — verify before saving
          </span>
        )}
      </div>

      {/* Full passage */}
      <div className="max-h-72 overflow-y-auto rounded-lg border border-border/40 bg-gray-50/80">
        <HighlightedCardText
          text={card.body_text}
          spans={editingSpans}
          boldSpans={boldSpans}
          mode={isEditing ? "deemphasize" : "full"}
          editable={isEditing}
          onRemoveSpan={onRemoveSpan}
        />
      </div>

      {/* Edit controls */}
      <div className="flex items-center gap-2 flex-wrap">
        {card.url && (
          <a
            href={card.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[10px] text-blue-600 hover:underline truncate max-w-[200px]"
          >
            {hostnameOnly(card.url)} ↗
          </a>
        )}
        <div className="ml-auto flex gap-1.5">
          {!isEditing ? (
            <button
              onClick={onEditStart}
              className="text-[10px] px-2 py-1 rounded-md border border-border text-ink-muted hover:bg-surface-1"
            >
              Edit Cut
            </button>
          ) : (
            <button
              onClick={onEditReset}
              className="text-[10px] px-2 py-1 rounded-md border border-amber-300 text-amber-700 hover:bg-amber-50"
            >
              Reset Cut
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default SourceVerificationPanel;
