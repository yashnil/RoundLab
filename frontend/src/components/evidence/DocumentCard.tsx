"use client";

import { useState } from "react";
import { FileText, Trash2, AlertCircle, CheckCircle2, BookOpen, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { apiFetch } from "@/lib/api";
import { fileSizeLabel } from "@/lib/evidenceHelpers";
import { CardItem } from "@/components/evidence/EvidenceLibraryCard";
import type {
  EvidenceDocument, EvidenceCard, DocumentWithCards, BlockEntry, ExtractBlocksResponse,
} from "@/types";

const STATUS_CONFIG: Record<
  string,
  { label: string; variant: "default" | "indigo" | "green" | "amber" | "red" }
> = {
  uploaded: { label: "Processing…", variant: "amber" },
  parsed:   { label: "Ready",       variant: "green"  },
  failed:   { label: "Failed",      variant: "red"    },
};

export function DocumentCard({
  doc,
  onDelete,
  onBlocksExtracted,
}: {
  doc: EvidenceDocument;
  onDelete: (id: string) => void;
  onBlocksExtracted?: (entries: BlockEntry[]) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [cards, setCards] = useState<EvidenceCard[]>([]);
  const [loading, setLoading] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [extractResult, setExtractResult] = useState<ExtractBlocksResponse | null>(null);
  const [extractErr, setExtractErr] = useState("");
  const cfg = STATUS_CONFIG[doc.status] ?? STATUS_CONFIG.uploaded;

  async function loadCards() {
    if (expanded || doc.status !== "parsed") return;
    setLoading(true);
    try {
      const data = await apiFetch<DocumentWithCards>(`/documents/${doc.id}?user_id=${doc.user_id}`);
      setCards(data.cards);
      setExpanded(true);
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete() {
    if (!confirm(`Delete "${doc.filename}"? This cannot be undone.`)) return;
    setDeleting(true);
    try {
      await apiFetch(`/documents/${doc.id}?user_id=${doc.user_id}`, { method: "DELETE" });
      onDelete(doc.id);
    } catch {
      setDeleting(false);
    }
  }

  async function extractBlocks() {
    setExtracting(true);
    setExtractErr("");
    try {
      const result = await apiFetch<ExtractBlocksResponse>(
        `/documents/${doc.id}/extract-blocks`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ user_id: doc.user_id }),
        },
      );
      setExtractResult(result);
      onBlocksExtracted?.(result.entries);
    } catch (e: unknown) {
      setExtractErr(e instanceof Error ? e.message : "Extraction failed");
    } finally {
      setExtracting(false);
    }
  }

  return (
    <div className="overflow-hidden rounded-[3px] border border-hairline bg-surface-1">
      {/* File tab header */}
      <div className="flex items-center gap-2 border-b border-hairline bg-surface-2 px-3 py-1.5">
        <span className="file-tab capitalize">{doc.doc_type}</span>
        <Badge variant={cfg.variant} className="text-xs">{cfg.label}</Badge>
        <span className="flex-1" />
        {doc.page_count && (
          <span className="text-[10px] text-ink-faint"
            style={{ fontFamily: "var(--font-jetbrains-mono)" }}>
            {doc.page_count}pp
          </span>
        )}
        {doc.file_size_bytes && (
          <span className="text-[10px] text-ink-faint"
            style={{ fontFamily: "var(--font-jetbrains-mono)" }}>
            {fileSizeLabel(doc.file_size_bytes)}
          </span>
        )}
      </div>

      {/* Body */}
      <div className="p-3.5">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-2.5 min-w-0">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-[3px] border border-hairline bg-surface-2">
              <FileText size={14} className="text-ink-faint" />
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-ink">{doc.filename}</p>
              {doc.error_message && (
                <p className="mt-0.5 text-xs text-danger">{doc.error_message}</p>
              )}
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-1 flex-wrap">
            {doc.status === "parsed" && (
              <>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 px-2 text-xs"
                  onClick={expanded ? () => setExpanded(false) : loadCards}
                  disabled={loading}
                >
                  {loading ? "Loading…" : expanded ? "Hide cards" : "Show cards"}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 px-2 text-xs gap-1 text-lav hover:text-lav"
                  onClick={extractBlocks}
                  disabled={extracting}
                  title="Extract block and frontline entries from this document"
                >
                  {extracting ? (
                    <><Loader2 size={11} className="animate-spin" />Extracting…</>
                  ) : (
                    <><BookOpen size={11} />Extract blocks</>
                  )}
                </Button>
              </>
            )}
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

        {extractErr && (
          <p className="mt-2 text-xs text-danger px-0.5">{extractErr}</p>
        )}

        {extractResult && (
          <div className="mt-2 flex items-center gap-1.5 rounded-lg border border-ok/20 bg-ok/5 px-3 py-1.5">
            <CheckCircle2 size={11} className="text-ok shrink-0" />
            <p className="text-xs text-ok">
              Extracted {extractResult.entries_extracted} entries
              {extractResult.entries_embedded > 0 ? ` (${extractResult.entries_embedded} indexed)` : ""}.
              They appear in the Blockfile Trainer section below.
            </p>
          </div>
        )}

        {expanded && cards.length > 0 && (
          <div className="mt-3 flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <span className="section-stamp">
                Extracted cards
                <span className="rep-badge ml-2">{cards.length}</span>
              </span>
              {cards.filter(c => !c.attribution_complete).length > 0 && (
                <span className="inline-flex items-center gap-1 text-xs text-amber-600">
                  <AlertCircle size={10} />
                  {cards.filter(c => !c.attribution_complete).length} incomplete attribution
                </span>
              )}
            </div>
            {cards.map((card) => (
              <CardItem key={card.id} card={card} />
            ))}
          </div>
        )}
        {expanded && cards.length === 0 && (
          <p className="mt-3 text-xs text-ink-subtle">No evidence cards extracted from this document.</p>
        )}
      </div>
    </div>
  );
}
