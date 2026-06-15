"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  FileText, Upload, Search, Trash2, ChevronDown, ChevronUp,
  AlertCircle, CheckCircle2, X, BookOpen, Loader2, Sparkles,
  Link2, ClipboardPaste, Globe,
} from "lucide-react";
import AppShell from "@/components/shell/AppShell";
import SectionHeader from "@/components/SectionHeader";
import { EmptyEvidenceGlyph } from "@/components/EmptyStateGlyphs";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { createClient } from "@/lib/supabase";
import { apiFetch } from "@/lib/api";
import { blockEntryTypeLabel, coverageStatusBadgeStyle } from "@/lib/blockfileHelpers";
import {
  sourceQualityLabel,
} from "@/lib/researchHelpers";
import CardDraftReview from "@/components/CardDraftReview";
import EvidenceCardDraft, { computeSaveReadiness } from "@/components/EvidenceCardDraft";
import { EvidenceStudioModal } from "@/components/evidence/EvidenceStudioModal";
import { SearchLoadingSteps, shouldShowResultsSummary, shouldShowEmptyState } from "@/components/EvidenceSearchPanel";
import type {
  EvidenceDocument,
  EvidenceCard,
  DocumentWithCards,
  SearchResultItem,
  BlockEntry,
  ExtractBlocksResponse,
  CardDraft,
  ExtractUrlResponse,
  GenerateCardsResponse,
} from "@/types";

// ── Constants ──────────────────────────────────────────────────────────────────

const ALLOWED_EXTS = ["pdf", "docx", "txt", "md"];
const MAX_MB = 20;

const STATUS_CONFIG: Record<
  string,
  { label: string; variant: "default" | "indigo" | "green" | "amber" | "red" }
> = {
  uploaded: { label: "Processing…", variant: "amber" },
  parsed:   { label: "Ready",       variant: "green"  },
  failed:   { label: "Failed",      variant: "red"    },
};

// ── Helpers ────────────────────────────────────────────────────────────────────

function fileSizeLabel(bytes: number | null): string {
  if (!bytes) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function extFromFilename(name: string): string {
  return name.split(".").pop()?.toLowerCase() ?? "";
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function AttributionRow({ card }: { card: EvidenceCard }) {
  const parts: string[] = [];
  if (card.author) parts.push(card.author);
  if (card.source) parts.push(card.source);
  if (card.year) parts.push(String(card.year));

  return (
    <div className="flex items-center gap-1.5 flex-wrap">
      {parts.length > 0 ? (
        <span className="text-xs text-ink-subtle">{parts.join(" · ")}</span>
      ) : null}
      {card.attribution_complete ? (
        <span className="inline-flex items-center gap-0.5 rounded-full bg-emerald-500/10 px-1.5 py-0.5 text-[10px] font-medium text-emerald-600">
          <CheckCircle2 size={9} /> Attribution complete
        </span>
      ) : (
        <span className="inline-flex items-center gap-0.5 rounded-full bg-amber-500/10 px-1.5 py-0.5 text-[10px] font-medium text-amber-600">
          <AlertCircle size={9} />
          {!card.author && !card.year ? "Missing author & date" :
           !card.author ? "Missing author" :
           !card.year ? "Missing date" : "Incomplete"}
        </span>
      )}
    </div>
  );
}

function CardItem({ card }: { card: EvidenceCard }) {
  const [open, setOpen] = useState(false);

  // Use tag as title; fall back to claim_summary truncated, then generic label
  const title = card.tag && !card.tag.match(/^CARD\s+\d+$/i)
    ? card.tag
    : card.claim_summary
      ? card.claim_summary.slice(0, 80) + (card.claim_summary.length > 80 ? "…" : "")
      : "Evidence card";

  return (
    <div className="case-file-card text-sm">
      {/* Compact header — always visible */}
      <div className="flex items-start justify-between gap-3 px-3 py-2.5">
        <div className="flex flex-col gap-1 min-w-0 flex-1">
          <p className="text-xs font-semibold text-ink leading-snug">{title}</p>
          <AttributionRow card={card} />
          {card.claim_summary && (
            <p className="text-xs text-ink-subtle leading-relaxed line-clamp-2">
              {card.claim_summary}
            </p>
          )}
          {/* Card body excerpt — always visible, clamped to 4 lines */}
          {card.card_text && (
            <p className={`mt-1 text-xs leading-relaxed text-ink-muted ${open ? "whitespace-pre-wrap" : "line-clamp-4"}`}>
              {card.card_text}
            </p>
          )}
        </div>
        <button
          onClick={() => setOpen((v) => !v)}
          className="shrink-0 mt-0.5 text-ink-muted hover:text-ink"
          aria-label={open ? "Collapse" : "Expand"}
        >
          {open
            ? <ChevronUp size={13} />
            : <ChevronDown size={13} />}
        </button>
      </div>

      {/* Expanded: source note */}
      {open && card.source && (
        <div className="border-t border-hairline px-3 py-1.5">
          <p className="text-xs text-ink-subtle">Source: {card.source}</p>
        </div>
      )}
    </div>
  );
}

function BlockEntryCard({
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

function DocumentCard({
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

function SearchResultCard({ item }: { item: SearchResultItem }) {
  const [open, setOpen] = useState(false);
  const topCard = item.cards[0];
  const displayTitle = (topCard?.tag && !topCard.tag.match(/^CARD\s+\d+$/i))
    ? topCard.tag
    : item.chunk.heading ?? null;

  const sim = item.similarity;
  const simLabel = sim !== null && sim !== undefined
    ? (sim >= 0.70 ? "Strong match" : sim >= 0.45 ? "Possible match" : "Weak match")
    : null;
  const simColor = sim !== null && sim !== undefined
    ? (sim >= 0.70 ? "text-ok" : sim >= 0.45 ? "text-warn" : "text-danger")
    : "";

  return (
    <div className="case-file-card p-3 text-sm">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          {/* Source document + similarity */}
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-[10px] font-medium uppercase tracking-wide text-ink-muted truncate">
              {item.document_filename}
            </p>
            {simLabel && (
              <span className={`text-[10px] font-semibold ${simColor}`}>
                {simLabel} ({Math.round((sim ?? 0) * 100)}%)
              </span>
            )}
          </div>
          {/* Card tag or chunk heading */}
          {displayTitle && (
            <p className="text-xs font-semibold text-ink mt-0.5 leading-snug">{displayTitle}</p>
          )}
          {/* Attribution metadata from matched card */}
          {topCard && (
            <div className="flex flex-wrap gap-1 mt-0.5">
              {topCard.author && <span className="text-xs text-ink-subtle">{topCard.author}</span>}
              {topCard.source && <span className="text-xs text-ink-subtle">· {topCard.source}</span>}
              {topCard.year && <span className="text-xs text-ink-subtle">· {topCard.year}</span>}
            </div>
          )}
        </div>
        <button onClick={() => setOpen((v) => !v)} className="shrink-0 text-ink-muted hover:text-ink mt-0.5">
          {open ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
        </button>
      </div>
      {/* Text excerpt */}
      <p className={`mt-2 text-xs leading-relaxed text-ink-muted ${open ? "whitespace-pre-wrap" : "line-clamp-4"}`}>
        {topCard?.card_text ?? item.chunk.chunk_text}
      </p>
      {/* Claim summary when collapsed */}
      {!open && topCard?.claim_summary && (
        <p className="mt-1.5 text-xs text-ink-subtle italic line-clamp-1">
          Supports: {topCard.claim_summary}
        </p>
      )}
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────────

export default function EvidencePage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [userId, setUserId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [documents, setDocuments] = useState<EvidenceDocument[]>([]);
  const [docsLoading, setDocsLoading] = useState(false);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [docType, setDocType] = useState<string>("case");
  const [fileError, setFileError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");

  const [searchQuery, setSearchQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<SearchResultItem[] | null>(null);
  const [searchError, setSearchError] = useState("");
  const [searchMode, setSearchMode] = useState<"keyword" | "semantic" | "hybrid">("hybrid");

  // Page tab
  const [activeTab, setActiveTab] = useState<"library" | "builder">("library");

  // Document role for upload form
  const [documentRole, setDocumentRole] = useState<string>("evidence");

  // Card Builder state
  type BuilderMode = "url" | "paste" | "search";
  const [builderMode, setBuilderMode] = useState<BuilderMode>("url");
  const [cbUrl, setCbUrl] = useState("");
  const [cbTopic, setCbTopic] = useState("");
  const [cbClaimGoal, setCbClaimGoal] = useState("");
  const [cbSide, setCbSide] = useState("");
  const [cbPastedText, setCbPastedText] = useState("");
  const [cbPasteAuthor, setCbPasteAuthor] = useState("");
  const [cbPastePublication, setCbPastePublication] = useState("");
  const [cbPasteDate, setCbPasteDate] = useState("");
  const [cbLoading, setCbLoading] = useState(false);
  const [cbError, setCbError] = useState("");
  const [cbExtractResult, setCbExtractResult] = useState<ExtractUrlResponse | null>(null);
  const [cbGenerateResult, setCbGenerateResult] = useState<GenerateCardsResponse | null>(null);
  const [showSearchDiagnostics, setShowSearchDiagnostics] = useState(false);
  const [drafts, setDrafts] = useState<CardDraft[]>([]);
  const [draftsLoading, setDraftsLoading] = useState(false);
  const [savingDraftId, setSavingDraftId] = useState<string | null>(null);
  const [discardingDraftId, setDiscardingDraftId] = useState<string | null>(null);
  const [cardFilter, setCardFilter] = useState<"all" | "ready" | "review" | "weak" | "counter">("all");
  const [studioCard, setStudioCard] = useState<CardDraft | null>(null); // card open in modal
  const [saveError, setSaveError] = useState(""); // inline save error (replaces runtime crash)

  // Block entries state
  const [blockEntries, setBlockEntries] = useState<BlockEntry[]>([]);
  const [blockEntriesLoading, setBlockEntriesLoading] = useState(false);
  const [blockSearchQuery, setBlockSearchQuery] = useState("");
  const [blockSearching, setBlockSearching] = useState(false);
  const [blockSearchResults, setBlockSearchResults] = useState<BlockEntry[] | null>(null);
  const [blockSearchErr, setBlockSearchErr] = useState("");

  // ── Auth ───────────────────────────────────────────────────────────────────

  useEffect(() => {
    createClient()
      .auth.getUser()
      .then(async ({ data }) => {
        if (!data.user) { router.replace("/login"); return; }
        setUserId(data.user.id);
        await Promise.all([
          loadDocuments(data.user.id),
          loadBlockEntries(data.user.id),
          loadDrafts(data.user.id),
        ]);
      })
      .catch(() => router.replace("/login"))
      .finally(() => setLoading(false));
  }, [router]);

  // ── Load documents ─────────────────────────────────────────────────────────

  async function loadDocuments(uid: string) {
    setDocsLoading(true);
    try {
      const docs = await apiFetch<EvidenceDocument[]>(`/documents?user_id=${uid}`);
      setDocuments(docs);
    } catch {
      // non-fatal
    } finally {
      setDocsLoading(false);
    }
  }

  // ── Load block entries ─────────────────────────────────────────────────────

  async function loadBlockEntries(uid: string) {
    setBlockEntriesLoading(true);
    try {
      const entries = await apiFetch<BlockEntry[]>(`/block-entries?user_id=${uid}`);
      setBlockEntries(entries);
    } catch {
      // non-fatal
    } finally {
      setBlockEntriesLoading(false);
    }
  }

  async function handleBlockSearch(e: React.SyntheticEvent) {
    e.preventDefault();
    if (!blockSearchQuery.trim() || !userId) return;
    setBlockSearching(true);
    setBlockSearchErr("");
    setBlockSearchResults(null);
    try {
      const results = await apiFetch<BlockEntry[]>(
        `/block-entries?user_id=${userId}&query=${encodeURIComponent(blockSearchQuery.trim())}&search_mode=hybrid&limit=20`,
      );
      setBlockSearchResults(results);
    } catch (e: unknown) {
      setBlockSearchErr(e instanceof Error ? e.message : "Search failed");
    } finally {
      setBlockSearching(false);
    }
  }

  function handleBlocksExtracted(entries: BlockEntry[]) {
    setBlockEntries((prev) => {
      const existingIds = new Set(prev.map((e) => e.id));
      const newEntries = entries.filter((e) => !existingIds.has(e.id));
      return [...newEntries, ...prev];
    });
  }

  // ── Card Builder functions ─────────────────────────────────────────────────

  async function loadDrafts(uid: string) {
    setDraftsLoading(true);
    try {
      const data = await apiFetch<CardDraft[]>(`/research/card-drafts?user_id=${uid}&status=draft`);
      setDrafts(data);
    } catch {
      // non-fatal
    } finally {
      setDraftsLoading(false);
    }
  }

  async function handleExtractUrl() {
    if (!userId || !cbUrl.trim()) return;
    setCbLoading(true);
    setCbError("");
    setCbExtractResult(null);
    try {
      const result = await apiFetch<ExtractUrlResponse>("/research/extract-url", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userId,
          url: cbUrl.trim(),
          topic: cbTopic.trim() || undefined,
          claim_goal: cbClaimGoal.trim() || undefined,
        }),
      });
      setCbExtractResult(result);
      // Now generate draft
      await generateDraftFromSource(result.research_source_id, null, null);
    } catch (e: unknown) {
      setCbError(e instanceof Error ? e.message : "Extraction failed");
    } finally {
      setCbLoading(false);
    }
  }

  async function handlePasteDraft() {
    if (!userId || !cbPastedText.trim()) return;
    setCbLoading(true);
    setCbError("");
    try {
      await generateDraftFromSource(null, null, cbPastedText.trim());
    } catch (e: unknown) {
      setCbError(e instanceof Error ? e.message : "Draft generation failed");
    } finally {
      setCbLoading(false);
    }
  }

  async function handleGenerateCards() {
    if (!userId || !cbClaimGoal.trim()) return;
    setCbLoading(true);
    setCbError("");
    setCbGenerateResult(null);
    setShowSearchDiagnostics(false);
    try {
      const result = await apiFetch<GenerateCardsResponse>("/research/generate-cards", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userId,
          topic: cbTopic.trim() || undefined,
          claim_to_support: cbClaimGoal.trim(),
          side: cbSide || undefined,
          max_cards: 5,
          include_partial_support: true,
        }),
      });
      setCardFilter("all"); // reset filter when new results arrive
      setCbGenerateResult(result);
    } catch (e: unknown) {
      setCbError(e instanceof Error ? e.message : "Search failed");
    } finally {
      setCbLoading(false);
    }
  }

  async function generateDraftFromSource(
    researchSourceId: string | null,
    url: string | null,
    pastedText: string | null,
  ) {
    if (!userId) return;
    const body: Record<string, unknown> = {
      user_id: userId,
      topic: cbTopic.trim() || "Debate topic",
      claim_goal: cbClaimGoal.trim() || "Support my argument",
      side: cbSide || undefined,
    };
    if (researchSourceId) body.research_source_id = researchSourceId;
    else if (url) body.url = url;
    else if (pastedText) body.pasted_text = pastedText;

    const draft = await apiFetch<CardDraft>("/research/card-draft", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    setDrafts((prev) => [draft, ...prev]);
  }

  async function handleSaveDraft(draft: CardDraft, confirmed: boolean) {
    if (!userId || !confirmed) return;
    setSavingDraftId(draft.id);
    setSaveError("");
    try {
      // Patch the draft with any user-modified spans before saving, so the
      // saved evidence card preserves the user's markup edits.
      const hasMarkupChanges =
        (draft.highlighted_spans_json?.length ?? 0) > 0 ||
        (draft.underline_spans_json?.length ?? 0) > 0;
      if (hasMarkupChanges) {
        await apiFetch(`/research/card-drafts/${draft.id}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            user_id: userId,
            highlighted_spans_json: draft.highlighted_spans_json ?? [],
            underline_spans_json: draft.underline_spans_json ?? [],
          }),
        });
      }
      await apiFetch(`/research/card-drafts/${draft.id}/save`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, confirmed }),
      });
      setDrafts((prev) =>
        prev.map((d) => d.id === draft.id ? { ...d, status: "saved" as const } : d),
      );
      setCbGenerateResult((prev) =>
        prev
          ? { ...prev, cards: prev.cards.map((c) => c.id === draft.id ? { ...c, status: "saved" as const } : c) }
          : prev,
      );
    } catch (err: unknown) {
      const msg = err instanceof Error
        ? err.message
        : "Save failed. Check that your account profile is set up and try again.";
      setSaveError(msg);
    } finally {
      setSavingDraftId(null);
    }
  }

  async function handleDiscardDraft(draftId: string) {
    if (!userId) return;
    setDiscardingDraftId(draftId);
    try {
      await apiFetch(`/research/card-drafts/${draftId}?user_id=${userId}`, { method: "DELETE" });
      setDrafts((prev) => prev.filter((d) => d.id !== draftId));
      setCbGenerateResult((prev) =>
        prev ? { ...prev, cards: prev.cards.filter((c) => c.id !== draftId) } : prev,
      );
    } finally {
      setDiscardingDraftId(null);
    }
  }

  async function handlePatchDraft(draftId: string, updates: Partial<CardDraft>) {
    if (!userId) return;
    try {
      const updated = await apiFetch<CardDraft>(`/research/card-drafts/${draftId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, ...updates }),
      });
      setDrafts((prev) => prev.map((d) => d.id === draftId ? updated : d));
    } catch {
      // non-fatal patch
    }
  }

  // ── File selection ─────────────────────────────────────────────────────────

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    setFileError("");
    setUploadError("");
    const file = e.target.files?.[0] ?? null;
    if (!file) return;

    const ext = extFromFilename(file.name);
    if (!ALLOWED_EXTS.includes(ext)) {
      setFileError(`Unsupported file type. Allowed: ${ALLOWED_EXTS.join(", ")}`);
      return;
    }
    if (file.size > MAX_MB * 1024 * 1024) {
      setFileError(`File too large. Maximum size is ${MAX_MB} MB.`);
      return;
    }
    setSelectedFile(file);
  }

  // ── Upload ─────────────────────────────────────────────────────────────────

  async function handleUpload() {
    if (!selectedFile) return;
    if (!userId) {
      setUploadError("Please sign in before uploading evidence.");
      return;
    }
    setUploading(true);
    setUploadError("");

    const sb = createClient();
    // Sanitize filename: remove characters that can break storage paths
    const safeName = selectedFile.name.replace(/[^a-zA-Z0-9._-]/g, "_");
    const storagePath = `${userId}/${Date.now()}_${safeName}`;

    try {
      // Step 1: upload file to Supabase Storage "documents" bucket
      const { error: storageErr } = await sb.storage
        .from("documents")
        .upload(storagePath, selectedFile, { upsert: false });

      if (storageErr) {
        const msg = storageErr.message ?? "";
        if (msg.includes("row-level security") || msg.includes("policy")) {
          setUploadError(
            "Upload blocked by evidence library permissions. " +
            "Apply migration 20260608110000_fix_document_storage_policies.sql " +
            "and ensure the 'documents' storage bucket exists."
          );
        } else if (msg.includes("Bucket not found") || msg.includes("bucket")) {
          setUploadError(
            "The 'documents' storage bucket does not exist. " +
            "Create it in the Supabase dashboard (Storage → New bucket → 'documents', private)."
          );
        } else if (msg.includes("already exists") || msg.includes("duplicate")) {
          setUploadError("A file with that name already exists. Rename the file and try again.");
        } else {
          setUploadError("Storage upload failed: " + msg);
        }
        return;
      }

      // Step 2: register document with backend (triggers parsing)
      let doc: EvidenceDocument;
      try {
        doc = await apiFetch<EvidenceDocument>("/documents", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            user_id: userId,
            filename: selectedFile.name,
            storage_path: storagePath,
            doc_type: docType,
            document_role: documentRole,
            file_size_bytes: selectedFile.size,
          }),
        });
      } catch (parseErr: unknown) {
        // File is stored but parsing failed — show document status from backend if available
        setUploadError(
          parseErr instanceof Error
            ? "File uploaded but parsing failed: " + parseErr.message
            : "File uploaded but the backend could not process it."
        );
        // Still reload the list so the user can see the failed document
        await loadDocuments(userId);
        return;
      }

      setDocuments((prev) => [doc, ...prev]);
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (err: unknown) {
      setUploadError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
  }

  // ── Search ─────────────────────────────────────────────────────────────────

  async function handleSearch(e: React.SyntheticEvent) {
    e.preventDefault();
    if (!searchQuery.trim() || !userId) return;
    setSearching(true);
    setSearchError("");
    setSearchResults(null);
    try {
      const results = await apiFetch<SearchResultItem[]>("/documents/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, query: searchQuery.trim(), limit: 8, mode: searchMode }),
      });
      setSearchResults(results);
    } catch (err: unknown) {
      setSearchError(err instanceof Error ? err.message : "Search failed.");
    } finally {
      setSearching(false);
    }
  }

  function handleDeleteDoc(id: string) {
    setDocuments((prev) => prev.filter((d) => d.id !== id));
  }

  // ── Loading state ──────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-canvas">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-hairline border-t-lav" />
      </div>
    );
  }

  if (!userId) return null;

  const parsedCount = documents.filter((d) => d.status === "parsed").length;

  return (
    <AppShell maxWidth="7xl">
      {/* ── Evidence Studio Modal ─────────────────────────────────────────────── */}
      {studioCard && (
        <EvidenceStudioModal
          card={studioCard}
          claimGoal={cbClaimGoal.trim()}
          onSave={(c) => handleSaveDraft(c, true)}
          onDiscard={handleDiscardDraft}
          onClose={() => setStudioCard(null)}
        />
      )}

      <div className="flex flex-col gap-8">

        {/* Header */}
        <SectionHeader
          title="Evidence Library"
          description="Upload your case files. RoundLab checks whether your speech claims are supported by your own evidence."
        />

        {/* Tab bar */}
        <div className="flex items-center gap-0 border-b border-border -mb-2">
          {([
            { key: "library", label: "Library", icon: <FileText size={13} /> },
            { key: "builder", label: "Card Builder", icon: <Sparkles size={13} /> },
          ] as const).map(({ key, label, icon }) => (
            <button
              key={key}
              onClick={() => setActiveTab(key)}
              className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-semibold border-b-2 -mb-px transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav focus-visible:ring-offset-1 rounded-sm ${
                activeTab === key
                  ? "border-lav text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
              }`}
            >
              {icon}
              {label}
            </button>
          ))}
        </div>

        {/* ── Card Builder tab ───────────────────────────────────────────────── */}
        {activeTab === "builder" && (
          <section className="flex flex-col gap-6">
            <div>
              <p className="text-sm text-ink-muted leading-relaxed mb-4">
                Cut debate evidence cards from real sources. RoundLab extracts the passage — you review and confirm before saving. Body text is always exact source text.
              </p>

              {/* Mode selector */}
              <div className="flex items-center gap-1.5 mb-5 flex-wrap">
                {([
                  { key: "url",    label: "From URL",        icon: <Link2 size={12} /> },
                  { key: "paste",  label: "Paste Text",      icon: <ClipboardPaste size={12} /> },
                  { key: "search", label: "Research Search", icon: <Globe size={12} /> },
                ] as const).map(({ key, label, icon }) => (
                  <button
                    key={key}
                    onClick={() => { setBuilderMode(key); setCbError(""); setCbGenerateResult(null); }}
                    className={`flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-[11px] font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav focus-visible:ring-offset-1 ${
                      builderMode === key
                        ? "bg-foreground text-background border-foreground"
                        : "bg-muted text-muted-foreground border-border hover:text-foreground hover:border-foreground/30"
                    }`}
                  >
                    {icon}{label}
                  </button>
                ))}
              </div>

              {/* Shared fields: topic + claim goal + side */}
              <div className="rounded-xl border border-border bg-surface-1 p-4 mb-4 flex flex-col gap-3">
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="text-xs font-medium text-ink-muted block mb-1">Topic (optional)</label>
                  <Input
                    value={cbTopic}
                    onChange={(e) => setCbTopic(e.target.value)}
                    placeholder="e.g. US-China trade relations"
                    className="text-sm"
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-ink-muted block mb-1">
                    Claim to support
                    {builderMode === "search" ? <span className="text-danger ml-1">*</span> : <span className="text-ink-muted/70 ml-1 font-normal">(optional)</span>}
                  </label>
                  <Input
                    value={cbClaimGoal}
                    onChange={(e) => setCbClaimGoal(e.target.value)}
                    placeholder="e.g. tariffs hurt economic growth"
                    className="text-sm"
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-ink-muted block mb-1">Side (optional)</label>
                  <select
                    value={cbSide}
                    onChange={(e) => setCbSide(e.target.value)}
                    className="h-9 w-full rounded-lg border border-border bg-surface px-3 text-sm text-ink focus:outline-none focus:ring-1 focus:ring-accent/30"
                  >
                    <option value="">Not specified</option>
                    <option value="Pro">Pro</option>
                    <option value="Con">Con</option>
                  </select>
                  </div>
                </div>
                <p className="text-[11px] text-ink-muted">
                  RoundLab searches credible sources, cuts exact evidence, and drafts debate-ready cards.
                </p>
              </div>

              {/* URL mode */}
              {builderMode === "url" && (
                <div className="flex flex-col gap-3">
                  <div>
                    <label className="text-xs font-medium text-ink-muted block mb-1">Article URL</label>
                    <div className="flex gap-2">
                      <Input
                        value={cbUrl}
                        onChange={(e) => setCbUrl(e.target.value)}
                        placeholder="https://..."
                        className="flex-1 text-sm font-mono"
                        type="url"
                      />
                      <Button
                        onClick={handleExtractUrl}
                        disabled={cbLoading || !cbUrl.trim()}
                        size="sm"
                        className="shrink-0"
                      >
                        {cbLoading ? <><Loader2 size={13} className="mr-1.5 animate-spin" />Extracting…</> : "Extract + Draft"}
                      </Button>
                    </div>
                  </div>
                  {cbExtractResult && (
                    <div className="flex items-center gap-2 text-xs text-ink-muted rounded border border-border bg-surface-faint px-3 py-2">
                      <CheckCircle2 size={12} className="text-ok shrink-0" />
                      <span>
                        Extracted from <strong>{cbExtractResult.article.metadata.publication ?? new URL(cbExtractResult.article.url).hostname}</strong>.
                        {" "}
                        <span className={`font-medium ${cbExtractResult.quality.source_quality === "high" ? "text-green-700" : cbExtractResult.quality.source_quality === "medium" ? "text-amber-600" : "text-ink-muted"}`}>
                          {sourceQualityLabel(cbExtractResult.quality.source_quality)}.
                        </span>
                      </span>
                    </div>
                  )}
                </div>
              )}

              {/* Paste mode */}
              {builderMode === "paste" && (
                <div className="flex flex-col gap-3">
                  <div>
                    <label className="text-xs font-medium text-ink-muted block mb-1">Paste source text</label>
                    <textarea
                      value={cbPastedText}
                      onChange={(e) => setCbPastedText(e.target.value)}
                      placeholder="Paste the article or passage you want to cut a card from…"
                      className="w-full min-h-36 rounded-lg border border-border bg-surface-faint px-3 py-2.5 text-sm text-ink leading-relaxed resize-y focus:border-accent focus:outline-none"
                    />
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    {[
                      { label: "Author", value: cbPasteAuthor, set: setCbPasteAuthor, placeholder: "Jane Doe" },
                      { label: "Publication", value: cbPastePublication, set: setCbPastePublication, placeholder: "New York Times" },
                      { label: "Date", value: cbPasteDate, set: setCbPasteDate, placeholder: "2024-03-15" },
                    ].map(({ label, value, set, placeholder }) => (
                      <div key={label}>
                        <label className="text-xs font-medium text-ink-muted block mb-1">{label} (optional)</label>
                        <Input value={value} onChange={(e) => set(e.target.value)} placeholder={placeholder} className="text-sm" />
                      </div>
                    ))}
                  </div>
                  <Button
                    onClick={handlePasteDraft}
                    disabled={cbLoading || !cbPastedText.trim()}
                    size="sm"
                    className="self-start"
                  >
                    {cbLoading ? <><Loader2 size={13} className="mr-1.5 animate-spin" />Generating…</> : "Generate Card Draft"}
                  </Button>
                </div>
              )}

              {/* Research Search mode */}
              {builderMode === "search" && (
                <div className="flex flex-col gap-3">
                  <Button
                    onClick={handleGenerateCards}
                    disabled={cbLoading || !cbClaimGoal.trim()}
                    size="sm"
                    className="self-start bg-blue-600 text-white hover:bg-blue-700"
                  >
                    {cbLoading
                      ? <><Loader2 size={13} className="mr-1.5 animate-spin" />Searching sources and drafting candidate cards…</>
                      : <><Globe size={13} className="mr-1.5" />Find candidate cards</>
                    }
                  </Button>

                  {/* Not configured */}
                  {cbGenerateResult && !cbGenerateResult.search_configured && (
                    <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 flex flex-col gap-2.5">
                      <p className="text-xs font-semibold text-amber-900">Research Search not configured</p>
                      <p className="text-xs text-amber-800 leading-relaxed">
                        {cbGenerateResult.no_card_reason ?? "A Tavily API key is required for Research Search. Set TAVILY_API_KEY in your backend .env file."}
                      </p>
                      {cbGenerateResult.suggestions && cbGenerateResult.suggestions.length > 0 && (
                        <ul className="text-xs text-amber-800 list-disc list-inside flex flex-col gap-0.5">
                          {cbGenerateResult.suggestions.map((s) => <li key={s}>{s}</li>)}
                        </ul>
                      )}
                      <div className="flex items-center gap-2 mt-1">
                        <Button size="sm" variant="secondary" className="h-7 px-2 text-xs gap-1"
                          onClick={() => { setBuilderMode("url"); setCbGenerateResult(null); }}>
                          <Link2 size={11} /> From URL instead
                        </Button>
                        <Button size="sm" variant="secondary" className="h-7 px-2 text-xs gap-1"
                          onClick={() => { setBuilderMode("paste"); setCbGenerateResult(null); }}>
                          <ClipboardPaste size={11} /> Paste Text instead
                        </Button>
                      </div>
                    </div>
                  )}

                  {/* Loading steps + skeletons */}
                  {cbLoading && <SearchLoadingSteps active={cbLoading} />}

                  {/* Cards found — summary bar + filters + card list */}
                  {shouldShowResultsSummary(cbGenerateResult, cbLoading) && cbGenerateResult && (() => {
                    // Sort cards: ready first, then review_needed, then weak
                    const readinessOrder = { ready: 0, review_needed: 1, weak: 2 };
                    const sorted = [...cbGenerateResult.cards].sort((a, b) => {
                      const ra = computeSaveReadiness(a).level;
                      const rb = computeSaveReadiness(b).level;
                      return (readinessOrder[ra] ?? 1) - (readinessOrder[rb] ?? 1);
                    });

                    // Filter
                    const filtered = sorted.filter((c) => {
                      if (cardFilter === "all") return true;
                      if (cardFilter === "counter") return !!c.is_counter_evidence;
                      const r = computeSaveReadiness(c).level;
                      if (cardFilter === "ready") return r === "ready" && !c.is_counter_evidence;
                      if (cardFilter === "review") return r === "review_needed";
                      if (cardFilter === "weak") return r === "weak";
                      return true;
                    });

                    // Count by level
                    const readyCt = sorted.filter((c) => computeSaveReadiness(c).level === "ready" && !c.is_counter_evidence).length;
                    const reviewCt = sorted.filter((c) => computeSaveReadiness(c).level === "review_needed").length;
                    const weakCt = sorted.filter((c) => computeSaveReadiness(c).level === "weak").length;
                    const counterCt = sorted.filter((c) => !!c.is_counter_evidence).length;

                    const plan = cbGenerateResult.evidence_set_plan;

                    // Map slot_label → best readiness of cards filling that slot
                    const slotReadiness = new Map<string, "ready" | "review_needed" | "weak">();
                    for (const c of sorted) {
                      if (!c.slot_label) continue;
                      const r = computeSaveReadiness(c).level;
                      const existing = slotReadiness.get(c.slot_label);
                      const order = { ready: 0, review_needed: 1, weak: 2 } as const;
                      if (!existing || order[r] < order[existing]) {
                        slotReadiness.set(c.slot_label, r);
                      }
                    }

                    // Weak leads slot labels
                    const weakLeadSlots = new Set(
                      (cbGenerateResult.weak_leads ?? []).map((l) => l.slot_label).filter(Boolean) as string[],
                    );

                    return (
                      <div className="flex flex-col gap-3">
                        {/* Compact evidence set progress — minimal chips only */}
                        {plan && plan.slots && plan.slots.length > 0 && (
                          <div className="flex items-center gap-1.5 flex-wrap">
                            <span className="text-[9px] text-ink-muted font-medium">
                              {slotReadiness.size}/{plan.slots.length} slots filled
                            </span>
                            {plan.slots.map((s) => {
                              const slotState = slotReadiness.get(s.slot_label);
                              const chipClass = slotState === "ready"
                                ? "bg-green-50 border-green-300 text-green-700"
                                : slotState === "review_needed"
                                  ? "bg-amber-50 border-amber-300 text-amber-700"
                                  : slotState === "weak"
                                    ? "bg-orange-50 border-orange-300 text-orange-700"
                                    : "bg-gray-50 border-gray-200 text-gray-400";
                              return (
                                <span
                                  key={s.slot_id}
                                  title={s.search_intent}
                                  className={`text-[9px] px-1.5 py-px rounded border ${chipClass}`}
                                >
                                  {s.slot_label}
                                </span>
                              );
                            })}
                          </div>
                        )}
                        {cbGenerateResult.usable_indirect_support_found &&
                          !cbGenerateResult.direct_support_found && (
                            <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-1.5 text-[11px] text-amber-800">
                              No direct evidence found, but mechanism/example cards support your argument&apos;s warrant.
                            </div>
                          )}
                        {/* Filter chips */}
                        <div className="flex gap-1.5 flex-wrap items-center">
                          <span className="text-[9px] text-ink-muted uppercase tracking-wide">Filter:</span>
                          {(
                            [
                              { key: "all" as const, label: `All (${sorted.length})`, extra: "" },
                              { key: "ready" as const, label: `Ready (${readyCt})`, extra: "text-green-700 border-green-300" },
                              { key: "review" as const, label: `Review (${reviewCt})`, extra: "text-amber-700 border-amber-300" },
                              { key: "weak" as const, label: `Verify (${weakCt})`, extra: "text-red-600 border-red-300" },
                              ...(counterCt > 0 ? [{ key: "counter" as const, label: `Counter (${counterCt})`, extra: "text-orange-700 border-orange-300" }] : []),
                            ]
                          ).map(({ key, label, extra }) => (
                            <button
                              key={key}
                              onClick={() => setCardFilter(key)}
                              className={`text-[9px] px-2 py-0.5 rounded border transition-colors ${
                                cardFilter === key
                                  ? "bg-blue-100 border-blue-400 text-blue-700 font-medium"
                                  : `border-border text-ink-muted hover:bg-surface-faint ${extra}`
                              }`}
                            >
                              {label}
                            </button>
                          ))}
                        </div>
                        <div className="flex flex-col gap-2.5">
                          {filtered.map((card, idx) => (
                            <div key={card.id} className="relative">
                              {idx === 0 && readyCt > 0 && cardFilter === "all" && (
                                <span className="absolute -top-2 right-2 z-10 text-[9px] font-bold px-2 py-0.5 rounded-full bg-blue-600 text-white shadow-sm">
                                  Best
                                </span>
                              )}
                              <EvidenceCardDraft
                                card={card}
                                claimGoal={cbClaimGoal.trim()}
                                onSave={(c) => handleSaveDraft(c, true)}
                                onDiscard={handleDiscardDraft}
                                onOpenStudio={() => setStudioCard(card)}
                              />
                            </div>
                          ))}
                          {filtered.length === 0 && (
                            <p className="text-[11px] text-ink-muted text-center py-4">
                              No cards match this filter.
                            </p>
                          )}
                        </div>

                        {/* Unfilled slots — strategic gaps with helpful CTAs */}
                        {cbGenerateResult.unfilled_slots &&
                          cbGenerateResult.unfilled_slots.length > 0 && (
                            <div className="rounded-md border border-amber-200 bg-amber-50/60 px-3 py-2.5 flex flex-col gap-2">
                              <div className="flex items-center gap-2">
                                <span className="text-[10px] font-semibold text-amber-800">
                                  Could not fill {cbGenerateResult.unfilled_slots.length} slot{cbGenerateResult.unfilled_slots.length > 1 ? "s" : ""}
                                </span>
                                <div className="flex flex-wrap gap-1">
                                  {cbGenerateResult.unfilled_slots.map((label) => (
                                    <span
                                      key={label}
                                      className="text-[9px] px-1.5 py-px rounded border border-amber-300 bg-white text-amber-700"
                                    >
                                      {label}
                                    </span>
                                  ))}
                                </div>
                              </div>
                              <p className="text-[10px] text-amber-700/80">
                                No strong card was found automatically. Cut one manually:
                              </p>
                              <div className="flex gap-1.5 flex-wrap">
                                <button
                                  onClick={() => { setBuilderMode("url"); setCbGenerateResult(null); }}
                                  className="text-[10px] px-2 py-1 rounded border border-amber-300 bg-white text-amber-800 hover:bg-amber-100 flex items-center gap-1"
                                >
                                  <Link2 size={10} /> Try source URL
                                </button>
                                <button
                                  onClick={() => { setBuilderMode("paste"); setCbGenerateResult(null); }}
                                  className="text-[10px] px-2 py-1 rounded border border-amber-300 bg-white text-amber-800 hover:bg-amber-100 flex items-center gap-1"
                                >
                                  <ClipboardPaste size={10} /> Paste source text
                                </button>
                                <button
                                  onClick={handleGenerateCards}
                                  disabled={cbLoading}
                                  className="text-[10px] px-2 py-1 rounded border border-amber-300 bg-white text-amber-800 hover:bg-amber-100"
                                >
                                  Search again
                                </button>
                              </div>
                            </div>
                          )}

                        {/* Weak leads — separate from main cards, styled as leads not cards */}
                        {cbGenerateResult.weak_leads &&
                          cbGenerateResult.weak_leads.length > 0 && (
                            <div className="rounded-md border border-border/50 bg-surface-faint/20 px-3 py-2.5 flex flex-col gap-2">
                              <p className="text-[10px] font-semibold text-ink-muted">
                                Source leads — verify manually before cutting
                              </p>
                              <div className="flex flex-col gap-2">
                                {cbGenerateResult.weak_leads.map((lead, i) => (
                                  <div
                                    key={lead.url ?? i}
                                    className="flex items-start gap-2 border-l-2 border-amber-200 pl-2"
                                  >
                                    <div className="flex-1 min-w-0 flex flex-col gap-0.5">
                                      {lead.slot_label && (
                                        <span className="text-[8px] uppercase tracking-wide text-ink-muted font-semibold">
                                          {lead.slot_label}
                                        </span>
                                      )}
                                      {lead.tag && (
                                        <p className="text-[10px] font-medium text-ink leading-snug">{lead.tag}</p>
                                      )}
                                      {lead.short_cite && (
                                        <p className="text-[9px] text-ink-muted">{lead.short_cite}</p>
                                      )}
                                      {lead.reason && (
                                        <p className="text-[9px] text-amber-700">{lead.reason}</p>
                                      )}
                                    </div>
                                    <div className="flex gap-1 shrink-0 flex-wrap">
                                      {lead.url && (
                                        <>
                                          <a
                                            href={lead.url}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="text-[9px] px-1.5 py-px rounded border border-border text-blue-600 hover:bg-surface-faint"
                                          >
                                            Open ↗
                                          </a>
                                          <button
                                            onClick={() => { setBuilderMode("url"); setCbUrl(lead.url!); setCbGenerateResult(null); }}
                                            className="text-[9px] px-1.5 py-px rounded border border-border text-ink-muted hover:bg-surface-faint"
                                          >
                                            Extract
                                          </button>
                                        </>
                                      )}
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                      </div>
                    );
                  })()}

                  {/* No cards found — clean minimal state */}
                  {!cbLoading && cbGenerateResult && cbGenerateResult.search_configured && cbGenerateResult.cards.length === 0 && (() => {
                    const diag = cbGenerateResult.diagnostics;
                    const hasCounterEvidence = (diag?.rejected_as_counter_evidence ?? 0) > 0;
                    const hasIndirectSupport = cbGenerateResult.usable_indirect_support_found === true;
                    const leadUrls = diag?.possible_lead_urls ?? [];

                    return (
                      <div className="rounded-lg border border-gray-200 px-4 py-3 flex flex-col gap-2.5 bg-gray-50">
                        <p className="text-sm font-semibold text-gray-700">
                          {hasCounterEvidence
                            ? "Sources found argue against this claim"
                            : hasIndirectSupport
                            ? "Indirect support found — needs a link card"
                            : "No cards found for this claim"}
                        </p>

                        {cbGenerateResult.no_card_reason && (
                          <p className="text-xs text-gray-500 leading-relaxed">{cbGenerateResult.no_card_reason}</p>
                        )}

                        {hasIndirectSupport && cbGenerateResult.indirect_support_explanation && (
                          <div className="rounded bg-blue-50 border border-blue-200 px-3 py-2">
                            <p className="text-[11px] text-blue-800 leading-relaxed">
                              <strong>Tip:</strong> {cbGenerateResult.indirect_support_explanation}
                            </p>
                          </div>
                        )}

                        {/* Counter-evidence hint */}
                        {hasCounterEvidence && (
                          <div className="rounded bg-amber-50 border border-amber-200 px-3 py-2">
                            <p className="text-[11px] text-amber-800 leading-relaxed">
                              <strong>Pre-empt opportunity:</strong> The sources found argue the other side. Consider cutting these as answers to prepare your pre-empts.
                            </p>
                          </div>
                        )}

                        {/* Possible lead URLs */}
                        {leadUrls.length > 0 && (
                          <div className="flex flex-col gap-1">
                            <p className="text-[11px] font-medium text-ink-muted">Worth checking manually ({leadUrls.length}):</p>
                            <div className="flex flex-col gap-0.5">
                              {leadUrls.slice(0, 3).map((u) => (
                                <button
                                  key={u}
                                  type="button"
                                  onClick={() => { setBuilderMode("url"); setCbUrl(u); setCbGenerateResult(null); }}
                                  className="text-[11px] text-accent hover:underline text-left truncate"
                                >
                                  {u}
                                </button>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Normalized claim info */}
                        {cbGenerateResult.normalized_claim && cbGenerateResult.normalized_claim !== cbClaimGoal.trim() && (
                          <p className="text-[11px] text-ink-muted">Searched for: <em>{cbGenerateResult.normalized_claim}</em></p>
                        )}
                        {cbGenerateResult.corrections_applied && cbGenerateResult.corrections_applied.length > 0 && (
                          <p className="text-[11px] text-amber-700">Fixed: {cbGenerateResult.corrections_applied.join("; ")}</p>
                        )}

                        {/* Candidates by role info */}
                        {cbGenerateResult.candidates_by_role && Object.keys(cbGenerateResult.candidates_by_role).length > 0 && (() => {
                          const roleEntries = Object.entries(cbGenerateResult.candidates_by_role).filter(([, v]) => v > 0);
                          if (roleEntries.length === 0) return null;
                          const summary = roleEntries.map(([role, count]) => `${count} ${role.replace(/_/g, " ")}`).join(", ");
                          return (
                            <p className="text-[11px] text-ink-muted">Found passage(s) scored as: {summary} — but below usefulness threshold.</p>
                          );
                        })()}

                        {/* Suggested revised claims — clickable chips */}
                        {cbGenerateResult.suggested_revised_claims && cbGenerateResult.suggested_revised_claims.length > 0 && (
                          <div className="flex flex-col gap-1.5">
                            <p className="text-[11px] font-medium text-ink-muted">Try a narrower claim instead:</p>
                            <div className="flex flex-wrap gap-1.5">
                              {cbGenerateResult.suggested_revised_claims.map((claim) => (
                                <button
                                  key={claim}
                                  type="button"
                                  onClick={() => { setCbClaimGoal(claim); setCbGenerateResult(null); }}
                                  className="text-[11px] px-2 py-1 rounded-full border border-accent text-accent bg-transparent hover:bg-accent/10 transition-colors"
                                >
                                  {claim}
                                </button>
                              ))}
                            </div>
                          </div>
                        )}

                        {cbGenerateResult.suggestions && cbGenerateResult.suggestions.length > 0 && (
                          <ul className="text-xs text-ink-muted list-disc list-inside flex flex-col gap-0.5">
                            {cbGenerateResult.suggestions.map((s) => <li key={s}>{s}</li>)}
                          </ul>
                        )}

                        <div className="flex items-center gap-2 mt-1">
                          <Button size="sm" variant="secondary" className="h-7 px-2 text-xs gap-1"
                            onClick={() => { setBuilderMode("url"); setCbGenerateResult(null); }}>
                            <Link2 size={11} /> Try a specific URL
                          </Button>
                          <Button size="sm" variant="secondary" className="h-7 px-2 text-xs gap-1"
                            onClick={() => { setBuilderMode("paste"); setCbGenerateResult(null); }}>
                            <ClipboardPaste size={11} /> Paste source text
                          </Button>
                        </div>
                      </div>
                    );
                  })()}
                </div>
              )}

              {saveError && (
                <p className="mt-2 rounded border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
                  ⚠ Save failed: {saveError}
                </p>
              )}
              {cbError && (
                <p className="mt-2 text-xs text-danger">{cbError}</p>
              )}
            </div>

            {/* Draft list — saved/other drafts NOT already shown in the search results above */}
            {(() => {
              const searchCardIds = new Set(
                (cbGenerateResult?.cards ?? []).map((c) => c.id),
              );
              const visibleDrafts = drafts.filter(
                (d) => d.status !== "discarded" && !searchCardIds.has(d.id),
              );
              // Empty state ONLY when there are no search results and no saved drafts.
              const showEmptyState = shouldShowEmptyState(cbGenerateResult, drafts, cbLoading);

              if (draftsLoading) {
                return (
                  <div className="flex flex-col gap-3">
                    {[1, 2].map((i) => <Skeleton key={i} className="h-32 w-full rounded-lg" />)}
                  </div>
                );
              }

              if (visibleDrafts.length > 0) {
                return (
                  <div className="flex flex-col gap-2.5">
                    {visibleDrafts.map((draft) => (
                      <CardDraftReview
                        key={draft.id}
                        draft={draft}
                        onSave={handleSaveDraft}
                        onDiscard={handleDiscardDraft}
                        onPatch={handlePatchDraft}
                        saving={savingDraftId === draft.id}
                        discarding={discardingDraftId === draft.id}
                      />
                    ))}
                  </div>
                );
              }

              if (showEmptyState) {
                return (
                  <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-border px-8 py-10 text-center">
                    <Sparkles size={16} className="text-ink-muted" />
                    <div>
                      <p className="text-sm font-semibold text-ink">No card drafts yet</p>
                      <p className="text-xs text-ink-muted mt-0.5">
                        Enter a URL, paste text, or run a research search above to generate your first card draft.
                      </p>
                    </div>
                  </div>
                );
              }

              return null;
            })()}
          </section>
        )}

        {/* ── Library tab content ────────────────────────────────────────────── */}
        {activeTab === "library" && <>

        {/* Upload panel */}
        <section>
          <span className="section-stamp mb-3 block">Upload document</span>
          <div className="rounded-[3px] border border-hairline bg-surface-1 p-4 flex flex-col gap-4">
            {/* Drop zone */}
            <label className="file-tray flex cursor-pointer flex-col items-center gap-3 p-8 text-center">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-hairline bg-surface-2">
                <Upload size={16} className="text-ink-subtle" />
              </div>
              {selectedFile ? (
                <div className="flex flex-col gap-0.5">
                  <span className="text-sm font-medium text-ink">{selectedFile.name}</span>
                  <span className="text-xs text-ink-subtle">{fileSizeLabel(selectedFile.size)}</span>
                </div>
              ) : (
                <div className="flex flex-col gap-0.5">
                  <span className="text-sm font-medium text-ink">Click to select a file</span>
                  <span className="text-xs text-ink-subtle">
                    {ALLOWED_EXTS.join(", ")} · max {MAX_MB} MB
                  </span>
                </div>
              )}
              <input
                ref={fileInputRef}
                type="file"
                accept={ALLOWED_EXTS.map((e) => `.${e}`).join(",")}
                onChange={handleFileChange}
                disabled={uploading}
                className="sr-only"
              />
            </label>

            {fileError && <p className="text-xs text-danger">{fileError}</p>}
            {uploadError && <p className="text-xs text-danger">{uploadError}</p>}

            {selectedFile && (
              <div className="flex flex-wrap items-center gap-3">
                <select
                  value={docType}
                  onChange={(e) => setDocType(e.target.value)}
                  disabled={uploading}
                  className="h-9 rounded-lg border border-hairline bg-surface px-3 text-sm text-ink focus:outline-none focus:ring-1 focus:ring-lav/40"
                >
                  <option value="case">Case file</option>
                  <option value="evidence">Evidence packet</option>
                  <option value="brief">Brief</option>
                  <option value="other">Other</option>
                </select>

                <select
                  value={documentRole}
                  onChange={(e) => setDocumentRole(e.target.value)}
                  disabled={uploading}
                  className="h-9 rounded-lg border border-hairline bg-surface px-3 text-sm text-ink focus:outline-none focus:ring-1 focus:ring-lav/40"
                >
                  <option value="evidence">Evidence</option>
                  <option value="case">Case file</option>
                  <option value="blockfile">Blockfile</option>
                  <option value="frontline">Frontline</option>
                  <option value="mixed">Mixed</option>
                </select>

                <Button onClick={handleUpload} disabled={uploading} size="sm" className="flex-1">
                  {uploading ? "Uploading and parsing…" : "Upload"}
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={uploading}
                  onClick={() => {
                    setSelectedFile(null);
                    if (fileInputRef.current) fileInputRef.current.value = "";
                  }}
                  className="gap-1"
                >
                  <X size={12} /> Clear
                </Button>
              </div>
            )}
          </div>
          <p className="mt-2 text-xs text-ink-muted">
            RoundLab extracts evidence cards from your file. It never invents citations.
          </p>
        </section>

        {/* Search */}
        {parsedCount > 0 && (
          <section>
            <span className="section-stamp mb-3 block">Search evidence</span>

            {/* Search mode toggle */}
            <div className="mb-2 flex items-center gap-1">
              {(["keyword", "semantic", "hybrid"] as const).map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => setSearchMode(m)}
                  className={`rounded-full border px-3 py-1 text-[10px] font-semibold uppercase tracking-wide transition-colors ${
                    searchMode === m
                      ? "border-lav/40 bg-lav/10 text-lav"
                      : "border-hairline bg-surface-2 text-ink-muted hover:text-ink"
                  }`}
                >
                  {m}
                </button>
              ))}
            </div>
            <p className="mb-2 text-[10px] text-ink-faint">
              {searchMode === "keyword" && "Matches exact words. Fast and deterministic."}
              {searchMode === "semantic" && "Finds conceptually related evidence even when the wording differs. Uses AI embeddings."}
              {searchMode === "hybrid" && "Semantic results first, then keyword results to fill any gaps. Recommended."}
            </p>

            <form onSubmit={handleSearch} className="flex gap-2">
              <Input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="e.g. deterrence fiscal burden alliance credibility"
                className="flex-1 text-sm"
                disabled={searching}
              />
              <Button type="submit" size="sm" disabled={searching || !searchQuery.trim()}>
                <Search size={14} className="mr-1.5" />
                {searching ? "Searching…" : "Search"}
              </Button>
            </form>

            {searchError && <p className="mt-2 text-xs text-danger">{searchError}</p>}

            {searchResults !== null && (
              <div className="mt-3 flex flex-col gap-2">
                {searchResults.length === 0 ? (
                  <div className="text-sm text-ink-subtle">
                    <p>No matching evidence found in your library.</p>
                    {searchMode !== "keyword" && (
                      <p className="mt-1 text-xs text-ink-faint">
                        If documents were uploaded before semantic search was enabled, try re-embedding them or switch to Keyword mode.
                      </p>
                    )}
                  </div>
                ) : (
                  <>
                    <div className="flex items-center gap-2">
                      <p className="text-xs text-ink-subtle">
                        {searchResults.length} result{searchResults.length !== 1 ? "s" : ""}
                      </p>
                      {searchResults.some((r) => r.retrieval_mode === "semantic" || r.retrieval_mode === "hybrid") && (
                        <span className="text-[10px] text-lav font-medium">semantic</span>
                      )}
                    </div>
                    {searchResults.map((item, i) => (
                      <SearchResultCard key={item.chunk.id ?? i} item={item} />
                    ))}
                  </>
                )}
              </div>
            )}
          </section>
        )}

        {/* Documents list */}
        <section>
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="section-stamp">Case files</span>
              {documents.length > 0 && (
                <span className="rep-badge">{documents.length}</span>
              )}
            </div>
            {parsedCount > 0 && (
              <span className="section-stamp">{parsedCount} ready</span>
            )}
          </div>

          {docsLoading ? (
            <div className="flex flex-col gap-3">
              {[1, 2].map((i) => <Skeleton key={i} className="h-20 w-full rounded-xl" />)}
            </div>
          ) : documents.length === 0 ? (
            <div className="flex flex-col items-center gap-4 rounded-[3px] border border-dashed border-hairline px-8 py-10 text-center">
              <EmptyEvidenceGlyph className="h-10 w-12 text-ink-faint opacity-60" />
              <div>
                <p className="text-sm font-semibold text-ink">No case files yet</p>
                <p className="text-xs text-ink-subtle mt-0.5">
                  Upload a case file or evidence packet above. RoundLab will extract evidence cards you can cite.
                </p>
              </div>
            </div>
          ) : (
            <div className="flex flex-col gap-3">
              {documents.map((doc) => (
                <DocumentCard
                  key={doc.id}
                  doc={doc}
                  onDelete={handleDeleteDoc}
                  onBlocksExtracted={handleBlocksExtracted}
                />
              ))}
            </div>
          )}
        </section>

        {/* ── Blockfile Trainer ────────────────────────────────────────────── */}
        <section>
          <div className="mb-3 flex items-center gap-2">
            <BookOpen size={14} className="text-ink-faint shrink-0" />
            <span className="section-stamp">Blockfile Trainer</span>
            {blockEntries.length > 0 && (
              <span className="rep-badge">{blockEntries.length}</span>
            )}
          </div>
          <p className="mb-3 text-xs text-ink-subtle leading-relaxed">
            Extract block and frontline entries from uploaded documents using the "Extract blocks"
            button above. Then search your block library to find prepared responses.
            Only your uploaded files are used — no outside knowledge.
          </p>

          {/* Block entry search */}
          {blockEntries.length > 0 && (
            <form onSubmit={handleBlockSearch} className="mb-4 flex gap-2">
              <Input
                value={blockSearchQuery}
                onChange={(e) => setBlockSearchQuery(e.target.value)}
                placeholder="Search blocks e.g. deterrence privacy rights"
                className="flex-1 text-sm"
                disabled={blockSearching}
              />
              <Button
                type="submit"
                size="sm"
                disabled={blockSearching || !blockSearchQuery.trim()}
              >
                {blockSearching ? (
                  <><Loader2 size={13} className="mr-1.5 animate-spin" />Searching…</>
                ) : (
                  <><Search size={13} className="mr-1.5" />Search blocks</>
                )}
              </Button>
              {blockSearchResults !== null && (
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => { setBlockSearchResults(null); setBlockSearchQuery(""); }}
                >
                  Clear
                </Button>
              )}
            </form>
          )}

          {blockSearchErr && <p className="mb-2 text-xs text-danger">{blockSearchErr}</p>}

          {/* Block entries list */}
          {blockEntriesLoading ? (
            <div className="flex flex-col gap-2">
              {[1, 2, 3].map((i) => <Skeleton key={i} className="h-16 w-full rounded-xl" />)}
            </div>
          ) : (blockSearchResults ?? blockEntries).length === 0 ? (
            <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-hairline px-6 py-8 text-center">
              <Sparkles size={16} className="text-ink-faint" />
              <div>
                <p className="text-sm font-semibold text-ink">No block entries yet</p>
                <p className="text-xs text-ink-subtle mt-0.5">
                  Upload a blockfile or frontline document above, then click "Extract blocks"
                  on a parsed document to populate your block library.
                </p>
              </div>
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              {blockSearchResults !== null && (
                <p className="text-xs text-ink-subtle">
                  {blockSearchResults.length} result{blockSearchResults.length !== 1 ? "s" : ""}
                  {" "}for "{blockSearchQuery}"
                </p>
              )}
              {(blockSearchResults ?? blockEntries).map((entry) => (
                <BlockEntryCard
                  key={entry.id}
                  entry={entry}
                  userId={userId}
                  onDelete={(id) => {
                    setBlockEntries((prev) => prev.filter((e) => e.id !== id));
                    if (blockSearchResults) {
                      setBlockSearchResults((prev) => prev?.filter((e) => e.id !== id) ?? null);
                    }
                  }}
                />
              ))}
            </div>
          )}
        </section>

        </> /* end library tab */}

      </div>
    </AppShell>
  );
}

