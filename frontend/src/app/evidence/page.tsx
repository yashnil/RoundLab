"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  FileText, Upload, Search, Trash2, ChevronDown, ChevronUp,
  AlertCircle, CheckCircle2, X,
} from "lucide-react";
import PageShell from "@/components/PageShell";
import SectionHeader from "@/components/SectionHeader";
import { EmptyEvidenceGlyph } from "@/components/EmptyStateGlyphs";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { createClient } from "@/lib/supabase";
import { apiFetch } from "@/lib/api";
import type {
  EvidenceDocument,
  EvidenceCard,
  DocumentWithCards,
  SearchResultItem,
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

function DocumentCard({
  doc,
  onDelete,
}: {
  doc: EvidenceDocument;
  onDelete: (id: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [cards, setCards] = useState<EvidenceCard[]>([]);
  const [loading, setLoading] = useState(false);
  const [deleting, setDeleting] = useState(false);
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
          <div className="flex shrink-0 items-center gap-1">
            {doc.status === "parsed" && (
              <Button
                variant="ghost"
                size="sm"
                className="h-7 px-2 text-xs"
                onClick={expanded ? () => setExpanded(false) : loadCards}
                disabled={loading}
              >
                {loading ? "Loading…" : expanded ? "Hide cards" : "Show cards"}
              </Button>
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
  // Show meaningful heading: prefer card tag, then CARD N label, then nothing
  const topCard = item.cards[0];
  const displayTitle = (topCard?.tag && !topCard.tag.match(/^CARD\s+\d+$/i))
    ? topCard.tag
    : item.chunk.heading ?? null;

  return (
    <div className="case-file-card p-3 text-sm">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          {/* Source document */}
          <p className="text-[10px] font-medium uppercase tracking-wide text-ink-muted truncate">
            {item.document_filename}
          </p>
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

  // ── Auth ───────────────────────────────────────────────────────────────────

  useEffect(() => {
    createClient()
      .auth.getUser()
      .then(async ({ data }) => {
        if (!data.user) { router.replace("/login"); return; }
        setUserId(data.user.id);
        await loadDocuments(data.user.id);
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

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!searchQuery.trim() || !userId) return;
    setSearching(true);
    setSearchError("");
    setSearchResults(null);
    try {
      const results = await apiFetch<SearchResultItem[]>("/documents/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, query: searchQuery.trim(), limit: 8 }),
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
    <PageShell maxWidth="7xl">
      <div className="flex flex-col gap-8">

        {/* Header */}
        <SectionHeader
          title="Evidence Library"
          description="Upload your case files. RoundLab checks whether your speech claims are supported by your own evidence."
        />

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
              <div className="flex items-center gap-3">
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
                  <p className="text-sm text-ink-subtle">No matching evidence found in your library.</p>
                ) : (
                  <>
                    <p className="text-xs text-ink-subtle">{searchResults.length} result{searchResults.length !== 1 ? "s" : ""}</p>
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
                <DocumentCard key={doc.id} doc={doc} onDelete={handleDeleteDoc} />
              ))}
            </div>
          )}
        </section>

      </div>
    </PageShell>
  );
}
