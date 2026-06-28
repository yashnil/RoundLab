"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  FileText, Upload, Search,
  CheckCircle2, X, BookOpen, Loader2, Sparkles,
  Link2, ClipboardPaste, Globe, ChevronRight,
} from "lucide-react";
import SectionHeader from "@/components/SectionHeader";
import { EmptyEvidenceGlyph } from "@/components/EmptyStateGlyphs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { createClient } from "@/lib/supabase";
import { apiFetch } from "@/lib/api";
import { sourceQualityLabel, sourceQualityColor } from "@/lib/researchHelpers";
import CardDraftReview from "@/components/CardDraftReview";
import EvidenceCardDraft, { computeSaveReadiness } from "@/components/EvidenceCardDraft";
import { EvidenceStudioModal } from "@/components/evidence/EvidenceStudioModal";
import { shouldShowResultsSummary, shouldShowEmptyState } from "@/components/EvidenceSearchPanel";
import { EvidenceSearchProgress } from "@/components/evidence/EvidenceSearchProgress";
import ClaimDecomposition from "@/components/evidence/ClaimDecomposition";
import ResearchSummary from "@/components/evidence/ResearchSummary";
import { SearchFailurePanel } from "@/components/evidence/SearchFailurePanel";
import ProvenanceTrail from "@/components/evidence/ProvenanceTrail";
import { DocumentCard } from "@/components/evidence/DocumentCard";
import { BlockEntryCard } from "@/components/evidence/BlockEntryCard";
import { SearchResultCard } from "@/components/evidence/SearchResultCard";
import {
  fileSizeLabel, extFromFilename, ALLOWED_EVIDENCE_EXTS, MAX_EVIDENCE_MB,
} from "@/lib/evidenceHelpers";
import { decomposeClaim, RESEARCH_DEPTH_OPTIONS, type ResearchDepth } from "@/lib/claimDecomposition";
import {
  deriveWorkbenchStage,
  deriveMobileStageFromWorkbench,
  deriveCandidateFilters,
  deriveSkeletonCount,
  MOBILE_STAGE_LABELS,
  type MobileStage,
} from "@/lib/workbenchModel";
import type {
  EvidenceDocument,
  SearchResultItem,
  BlockEntry,
  CardDraft,
  ExtractUrlResponse,
  GenerateCardsResponse,
} from "@/types";

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
  const [cbDepth, setCbDepth] = useState<ResearchDepth>("standard");
  const [cbPastedText, setCbPastedText] = useState("");
  const [cbPasteAuthor, setCbPasteAuthor] = useState("");
  const [cbPastePublication, setCbPastePublication] = useState("");
  const [cbPasteDate, setCbPasteDate] = useState("");
  const [cbLoading, setCbLoading] = useState(false);
  const [cbError, setCbError] = useState("");
  const [cbExtractResult, setCbExtractResult] = useState<ExtractUrlResponse | null>(null);
  const [cbGenerateResult, setCbGenerateResult] = useState<GenerateCardsResponse | null>(null);
  const [drafts, setDrafts] = useState<CardDraft[]>([]);
  const [draftsLoading, setDraftsLoading] = useState(false);
  const [savingDraftId, setSavingDraftId] = useState<string | null>(null);
  const [discardingDraftId, setDiscardingDraftId] = useState<string | null>(null);
  const [cardFilter, setCardFilter] = useState<"all" | "ready" | "review" | "weak" | "counter">("all");
  const [studioCard, setStudioCard] = useState<CardDraft | null>(null);
  const [saveError, setSaveError] = useState("");
  // ID of the most-recently saved card (for the "View in Library" link)
  const [lastSavedCardId, setLastSavedCardId] = useState<string | null>(null);

  // Workbench state — which card is previewed in the right panel
  const [selectedCardId, setSelectedCardId] = useState<string | null>(null);
  // Mobile panel navigation — overrides auto-derived stage routing
  const [mobileStageOverride, setMobileStageOverride] = useState<MobileStage | null>(null);
  // Roving tabindex for candidate keyboard navigation
  const [activeCardIndex, setActiveCardIndex] = useState<number>(0);
  const candidateListRef = useRef<HTMLDivElement>(null);
  // Sequence counter for stale-response protection: only the most-recent
  // search can commit its result to state.
  const searchSeqRef = useRef(0);

  // Block entries state
  const [blockEntries, setBlockEntries] = useState<BlockEntry[]>([]);
  const [blockEntriesLoading, setBlockEntriesLoading] = useState(false);
  const [blockSearchQuery, setBlockSearchQuery] = useState("");
  const [blockSearching, setBlockSearching] = useState(false);
  const [blockSearchResults, setBlockSearchResults] = useState<BlockEntry[] | null>(null);
  const [blockSearchErr, setBlockSearchErr] = useState("");

  // ── Derived workbench state ────────────────────────────────────────────────

  const allCards = cbGenerateResult?.cards ?? [];
  const workbenchStage = deriveWorkbenchStage({
    isLoading: cbLoading,
    hasResults: allCards.length > 0,
    selectedCardId,
    isSaving: savingDraftId !== null,
    savedCount: drafts.filter((d) => d.status === "saved").length,
  });
  const autoMobileStage = deriveMobileStageFromWorkbench(workbenchStage);
  const mobileStage = mobileStageOverride ?? autoMobileStage;

  // The currently selected card (for right panel preview)
  const selectedCard =
    (allCards.find((c) => c.id === selectedCardId) ??
     drafts.find((d) => d.id === selectedCardId)) ?? null;

  // Candidate filters
  const candidateFilterChips = deriveCandidateFilters(
    allCards.map((c) => ({
      readinessLevel: computeSaveReadiness(c).level as "ready" | "review_needed" | "weak",
      isCounter: !!c.is_counter_evidence,
    })),
    cardFilter,
  );

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

  // ── Loaders ────────────────────────────────────────────────────────────────

  async function loadDocuments(uid: string) {
    setDocsLoading(true);
    try {
      const docs = await apiFetch<EvidenceDocument[]>(`/documents?user_id=${uid}`);
      setDocuments(docs);
    } catch { /* non-fatal */ } finally { setDocsLoading(false); }
  }

  async function loadBlockEntries(uid: string) {
    setBlockEntriesLoading(true);
    try {
      const entries = await apiFetch<BlockEntry[]>(`/block-entries?user_id=${uid}`);
      setBlockEntries(entries);
    } catch { /* non-fatal */ } finally { setBlockEntriesLoading(false); }
  }

  async function loadDrafts(uid: string) {
    setDraftsLoading(true);
    try {
      const data = await apiFetch<CardDraft[]>(`/research/card-drafts?user_id=${uid}&status=draft`);
      setDrafts(data);
    } catch { /* non-fatal */ } finally { setDraftsLoading(false); }
  }

  // ── Block search ───────────────────────────────────────────────────────────

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
    } finally { setBlockSearching(false); }
  }

  function handleBlocksExtracted(entries: BlockEntry[]) {
    setBlockEntries((prev) => {
      const existingIds = new Set(prev.map((e) => e.id));
      return [...entries.filter((e) => !existingIds.has(e.id)), ...prev];
    });
  }

  // ── Card Builder ───────────────────────────────────────────────────────────

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
      await generateDraftFromSource(result.research_source_id, null, null);
    } catch (e: unknown) {
      setCbError(e instanceof Error ? e.message : "Extraction failed");
    } finally { setCbLoading(false); }
  }

  async function handlePasteDraft() {
    if (!userId || !cbPastedText.trim()) return;
    setCbLoading(true);
    setCbError("");
    try {
      await generateDraftFromSource(null, null, cbPastedText.trim());
    } catch (e: unknown) {
      setCbError(e instanceof Error ? e.message : "Draft generation failed");
    } finally { setCbLoading(false); }
  }

  async function handleGenerateCards(claimOverride?: string) {
    const override = typeof claimOverride === "string" ? claimOverride.trim() : "";
    const claim = override || cbClaimGoal.trim();
    if (!userId || !claim) return;
    if (override) setCbClaimGoal(override);
    const maxCards = cbDepth === "quick" ? 3 : cbDepth === "deep" ? 8 : 5;
    const seq = ++searchSeqRef.current;
    setCbLoading(true);
    setCbError("");
    setCbGenerateResult(null);
    setSelectedCardId(null);
    setMobileStageOverride(null);
    try {
      const result = await apiFetch<GenerateCardsResponse>("/research/generate-cards", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userId,
          topic: cbTopic.trim() || undefined,
          claim_to_support: claim,
          side: cbSide || undefined,
          max_cards: maxCards,
          include_partial_support: true,
        }),
      });
      // Stale-response guard: discard if a newer request has already started
      if (seq !== searchSeqRef.current) return;
      setCardFilter("all");
      setCbGenerateResult(result);
      if (result.cards.length > 0) setMobileStageOverride("candidates");
    } catch (e: unknown) {
      if (seq !== searchSeqRef.current) return;
      setCbError(e instanceof Error ? e.message : "Search failed");
    } finally {
      if (seq === searchSeqRef.current) setCbLoading(false);
    }
  }

  /**
   * Run all five claim angles in sequence, aggregate and deduplicate the
   * resulting cards, then commit the merged set to state. Each angle uses
   * max_cards=3 so the total stays manageable. Cards are deduplicated by id.
   * A stale-response guard ensures that a concurrent normal search can cancel
   * this loop.
   */
  async function handleRunAllAngles() {
    if (!userId || !cbClaimGoal.trim()) return;
    const branches = decomposeClaim(cbClaimGoal.trim());
    const seq = ++searchSeqRef.current;
    setCbLoading(true);
    setCbError("");
    setCbGenerateResult(null);
    setSelectedCardId(null);
    setMobileStageOverride(null);
    const seenIds = new Set<string>();
    const allCards: GenerateCardsResponse["cards"] = [];
    try {
      for (const branch of branches) {
        if (seq !== searchSeqRef.current) return; // cancelled by newer request
        try {
          const result = await apiFetch<GenerateCardsResponse>("/research/generate-cards", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              user_id: userId,
              topic: cbTopic.trim() || undefined,
              claim_to_support: branch.query,
              side: cbSide || undefined,
              max_cards: 3,
              include_partial_support: true,
            }),
          });
          for (const card of result.cards) {
            if (!seenIds.has(card.id)) {
              seenIds.add(card.id);
              allCards.push(card);
            }
          }
        } catch { /* ignore per-angle failure, continue remaining angles */ }
      }
      if (seq !== searchSeqRef.current) return;
      setCardFilter("all");
      setCbGenerateResult({
        search_configured: true,
        cards: allCards,
        no_card_reason: allCards.length === 0 ? "No cards found across any angle." : null,
        suggestions: [],
      });
      if (allCards.length > 0) setMobileStageOverride("candidates");
    } finally {
      if (seq === searchSeqRef.current) setCbLoading(false);
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
    // Auto-select the newly generated draft in the right panel
    setSelectedCardId(draft.id);
    setMobileStageOverride("card");
  }

  async function handleSaveDraft(draft: CardDraft, confirmed: boolean) {
    if (!userId || !confirmed) return;
    // Prevent duplicate save clicks while a save is in-flight
    if (savingDraftId !== null) return;
    setSavingDraftId(draft.id);
    setSaveError("");
    setLastSavedCardId(null);
    try {
      const m = draft.user_markup_json;
      const hasFullMarkup =
        !!m &&
        ((m.highlight?.length ?? 0) > 0 ||
          (m.underline?.length ?? 0) > 0 ||
          (m.bold?.length ?? 0) > 0 ||
          (m.italic?.length ?? 0) > 0);
      const hasColumnSpans =
        (draft.highlighted_spans_json?.length ?? 0) > 0 ||
        (draft.underline_spans_json?.length ?? 0) > 0;
      if (hasFullMarkup || hasColumnSpans) {
        await apiFetch(`/research/card-drafts/${draft.id}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            user_id: userId,
            highlighted_spans_json: draft.highlighted_spans_json ?? [],
            underline_spans_json: draft.underline_spans_json ?? [],
            ...(hasFullMarkup ? { user_markup_json: m } : {}),
          }),
        });
      }
      const result = await apiFetch<{ card_id: string; draft_id: string; message: string }>(
        `/research/card-drafts/${draft.id}/save`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ user_id: userId, confirmed }),
        },
      );
      setLastSavedCardId(result.card_id);
      setDrafts((prev) =>
        prev.map((d) => d.id === draft.id ? { ...d, status: "saved" as const } : d),
      );
      setCbGenerateResult((prev) =>
        prev
          ? { ...prev, cards: prev.cards.map((c) => c.id === draft.id ? { ...c, status: "saved" as const } : c) }
          : prev,
      );
    } catch (err: unknown) {
      // The API returns structured {stage, message} for 500s; surface the stage
      let msg = "Save failed. Check your account profile and try again.";
      if (err instanceof Error) {
        try {
          const parsed = JSON.parse(err.message) as { stage?: string; message?: string };
          if (parsed.stage) {
            msg = `Save failed at ${parsed.stage}: ${parsed.message ?? "internal error"}`;
          } else {
            msg = err.message;
          }
        } catch {
          msg = err.message;
        }
      }
      setSaveError(msg);
    } finally { setSavingDraftId(null); }
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
      if (selectedCardId === draftId) setSelectedCardId(null);
    } finally { setDiscardingDraftId(null); }
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
    } catch { /* non-fatal */ }
  }

  // ── File handling ──────────────────────────────────────────────────────────

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    setFileError("");
    setUploadError("");
    const file = e.target.files?.[0] ?? null;
    if (!file) return;
    const ext = extFromFilename(file.name);
    if (!ALLOWED_EVIDENCE_EXTS.includes(ext)) {
      setFileError(`Unsupported file type. Allowed: ${ALLOWED_EVIDENCE_EXTS.join(", ")}`);
      return;
    }
    if (file.size > MAX_EVIDENCE_MB * 1024 * 1024) {
      setFileError(`File too large. Maximum size is ${MAX_EVIDENCE_MB} MB.`);
      return;
    }
    setSelectedFile(file);
  }

  async function handleUpload() {
    if (!selectedFile || !userId) {
      if (!userId) setUploadError("Please sign in before uploading evidence.");
      return;
    }
    setUploading(true);
    setUploadError("");
    const sb = createClient();
    const safeName = selectedFile.name.replace(/[^a-zA-Z0-9._-]/g, "_");
    const storagePath = `${userId}/${Date.now()}_${safeName}`;
    try {
      const { error: storageErr } = await sb.storage
        .from("documents")
        .upload(storagePath, selectedFile, { upsert: false });
      if (storageErr) {
        const msg = storageErr.message ?? "";
        if (msg.includes("row-level security") || msg.includes("policy")) {
          setUploadError("Upload blocked by evidence library permissions. Apply the documents storage migration and ensure the bucket exists.");
        } else if (msg.includes("Bucket not found") || msg.includes("bucket")) {
          setUploadError("The 'documents' storage bucket does not exist. Create it in the Supabase dashboard.");
        } else if (msg.includes("already exists") || msg.includes("duplicate")) {
          setUploadError("A file with that name already exists. Rename the file and try again.");
        } else {
          setUploadError("Storage upload failed: " + msg);
        }
        return;
      }
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
        setUploadError(
          parseErr instanceof Error
            ? "File uploaded but parsing failed: " + parseErr.message
            : "File uploaded but the backend could not process it."
        );
        await loadDocuments(userId);
        return;
      }
      setDocuments((prev) => [doc, ...prev]);
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (err: unknown) {
      setUploadError(err instanceof Error ? err.message : "Upload failed.");
    } finally { setUploading(false); }
  }

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
    } finally { setSearching(false); }
  }

  function handleDeleteDoc(id: string) {
    setDocuments((prev) => prev.filter((d) => d.id !== id));
  }

  // ── Select card for right panel ────────────────────────────────────────────

  function handleSelectCard(card: CardDraft, idx?: number) {
    setSelectedCardId(card.id);
    setMobileStageOverride("card");
    if (idx !== undefined) setActiveCardIndex(idx);
  }

  function handleCandidateKeyDown(e: React.KeyboardEvent<HTMLDivElement>) {
    const cards = filteredCards;
    if (cards.length === 0) return;
    let next = activeCardIndex;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      next = Math.min(activeCardIndex + 1, cards.length - 1);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      next = Math.max(activeCardIndex - 1, 0);
    } else if (e.key === "Home") {
      e.preventDefault();
      next = 0;
    } else if (e.key === "End") {
      e.preventDefault();
      next = cards.length - 1;
    } else {
      return;
    }
    setActiveCardIndex(next);
    // Move DOM focus to the newly active card element
    const candidates = candidateListRef.current?.querySelectorAll<HTMLElement>("[data-candidate]");
    candidates?.[next]?.focus();
  }

  // ── Loading state ──────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="h-8 w-8 motion-safe:animate-spin rounded-full border-2 border-hairline border-t-lav" />
      </div>
    );
  }

  if (!userId) return null;

  const parsedCount = documents.filter((d) => d.status === "parsed").length;

  // Sorted cards for the candidate panel
  const readinessOrder = { ready: 0, review_needed: 1, weak: 2 } as const;
  const sortedCards = [...allCards].sort((a, b) => {
    const ra = computeSaveReadiness(a).level;
    const rb = computeSaveReadiness(b).level;
    return (readinessOrder[ra] ?? 1) - (readinessOrder[rb] ?? 1);
  });
  const filteredCards = sortedCards.filter((c) => {
    if (cardFilter === "all") return true;
    if (cardFilter === "counter") return !!c.is_counter_evidence;
    const r = computeSaveReadiness(c).level;
    if (cardFilter === "ready") return r === "ready" && !c.is_counter_evidence;
    if (cardFilter === "review") return r === "review_needed";
    if (cardFilter === "weak") return r === "weak";
    return true;
  });

  return (
    <div className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      {/* Evidence Studio Modal (full-screen card editor) */}
      {studioCard && (
        <EvidenceStudioModal
          card={studioCard}
          claimGoal={cbClaimGoal.trim()}
          onSave={(c) => handleSaveDraft(c, true)}
          onDiscard={handleDiscardDraft}
          onClose={() => setStudioCard(null)}
        />
      )}

      <div className="flex flex-col gap-6">

        {/* Page header */}
        <SectionHeader
          title="Evidence Library"
          description="Upload case files or cut evidence cards from real sources."
        />

        {/* ── Tab bar ────────────────────────────────────────────────────────── */}
        <div
          className="flex items-center gap-0 border-b border-hairline -mb-2"
          role="tablist"
          aria-label="Evidence sections"
        >
          {([
            { key: "library", label: "Library", icon: <FileText size={13} aria-hidden="true" /> },
            { key: "builder", label: "Card Builder", icon: <Sparkles size={13} aria-hidden="true" /> },
          ] as const).map(({ key, label, icon }) => (
            <button
              key={key}
              role="tab"
              aria-selected={activeTab === key}
              onClick={() => setActiveTab(key)}
              className={cn(
                "flex items-center gap-1.5 px-4 py-2.5 text-xs font-semibold border-b-2 -mb-px transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50 rounded-t",
                activeTab === key
                  ? "border-lav text-ink"
                  : "border-transparent text-ink-subtle hover:text-ink hover:border-hairline",
              )}
            >
              {icon}
              {label}
            </button>
          ))}
        </div>

        {/* ── Card Builder tab — 3-column workbench ────────────────────────── */}
        {activeTab === "builder" && (
          <section aria-label="Card Builder workbench">

            {/* Mobile stage nav */}
            <nav
              className="md:hidden flex border-b border-hairline mb-4 -mx-4 px-4"
              aria-label="Workbench sections"
            >
              {(["search", "candidates", "card"] as MobileStage[]).map((stage) => (
                <button
                  key={stage}
                  type="button"
                  onClick={() => setMobileStageOverride(stage)}
                  aria-current={mobileStage === stage ? "step" : undefined}
                  className={cn(
                    "flex-1 py-2 text-xs font-semibold border-b-2 -mb-px transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50",
                    mobileStage === stage
                      ? "border-lav text-ink"
                      : "border-transparent text-ink-subtle hover:text-ink",
                  )}
                >
                  {MOBILE_STAGE_LABELS[stage]}
                </button>
              ))}
            </nav>

            {/* 3-column grid */}
            <div className="grid grid-cols-1 md:grid-cols-[280px_1fr_340px] gap-0 md:border md:border-hairline md:rounded-xl md:overflow-hidden">

              {/* ── Left panel: search controls ────────────────────────────────── */}
              <aside
                className={cn(
                  "flex flex-col gap-4 p-4 md:border-r md:border-hairline md:overflow-y-auto",
                  mobileStage !== "search" ? "hidden md:flex" : "flex",
                )}
                aria-label="Search controls"
              >
                <div>
                  <h2 className="text-eyebrow text-ink-subtle mb-3">Research claim</h2>
                  <div className="flex flex-col gap-2">
                    <div>
                      <label htmlFor="cb-claim" className="text-xs font-medium text-ink-subtle block mb-1">
                        Claim to support <span className="text-danger">*</span>
                      </label>
                      <textarea
                        id="cb-claim"
                        value={cbClaimGoal}
                        onChange={(e) => setCbClaimGoal(e.target.value)}
                        placeholder="e.g. tariffs reduce economic growth"
                        rows={3}
                        className="w-full rounded-lg border border-hairline bg-surface-2 px-3 py-2 text-sm text-ink leading-relaxed resize-none focus:outline-none focus:ring-2 focus:ring-lav/30 focus:border-lav/50"
                      />
                    </div>
                    <div>
                      <label htmlFor="cb-topic" className="text-xs font-medium text-ink-subtle block mb-1">
                        Topic <span className="text-ink-faint font-normal">(optional)</span>
                      </label>
                      <Input
                        id="cb-topic"
                        value={cbTopic}
                        onChange={(e) => setCbTopic(e.target.value)}
                        placeholder="e.g. US-China trade"
                        className="text-sm h-8"
                      />
                    </div>
                    <div>
                      <label htmlFor="cb-side" className="text-xs font-medium text-ink-subtle block mb-1">
                        Side <span className="text-ink-faint font-normal">(optional)</span>
                      </label>
                      <select
                        id="cb-side"
                        value={cbSide}
                        onChange={(e) => setCbSide(e.target.value)}
                        className="h-8 w-full rounded-lg border border-hairline bg-surface-2 px-2.5 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-lav/30"
                      >
                        <option value="">Not specified</option>
                        <option value="Pro">Pro</option>
                        <option value="Con">Con</option>
                      </select>
                    </div>
                  </div>
                </div>

                <div className="border-t border-hairline pt-4">
                  <h2 className="text-eyebrow text-ink-subtle mb-3">Source mode</h2>
                  {/* Mode selector */}
                  <div
                    className="flex flex-col gap-0.5 rounded-lg border border-hairline bg-surface-2 p-0.5"
                    role="radiogroup"
                    aria-label="Evidence source mode"
                  >
                    {([
                      { key: "url",    label: "From URL",        icon: <Link2 size={12} aria-hidden="true" /> },
                      { key: "paste",  label: "Paste text",      icon: <ClipboardPaste size={12} aria-hidden="true" /> },
                      { key: "search", label: "Research search", icon: <Globe size={12} aria-hidden="true" /> },
                    ] as const).map(({ key, label, icon }) => (
                      <button
                        key={key}
                        type="button"
                        role="radio"
                        aria-checked={builderMode === key}
                        onClick={() => { setBuilderMode(key); setCbError(""); setCbGenerateResult(null); setSelectedCardId(null); }}
                        className={cn(
                          "flex items-center gap-2 rounded-md px-3 py-2 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50",
                          builderMode === key
                            ? "bg-surface-1 text-ink shadow-xs"
                            : "text-ink-subtle hover:text-ink",
                        )}
                      >
                        {icon}{label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* URL mode input */}
                {builderMode === "url" && (
                  <div className="flex flex-col gap-3">
                    <div>
                      <label htmlFor="cb-url" className="text-xs font-medium text-ink-subtle block mb-1">
                        Article URL
                      </label>
                      <Input
                        id="cb-url"
                        value={cbUrl}
                        onChange={(e) => setCbUrl(e.target.value)}
                        placeholder="https://…"
                        type="url"
                        className="text-sm h-8 font-mono"
                      />
                    </div>
                    <Button
                      onClick={handleExtractUrl}
                      disabled={cbLoading || !cbUrl.trim()}
                      size="sm"
                      className="w-full"
                    >
                      {cbLoading
                        ? <><Loader2 size={13} className="mr-1.5 motion-safe:animate-spin" aria-hidden="true" />Extracting…</>
                        : <>Extract + Draft<ChevronRight size={13} className="ml-1.5" aria-hidden="true" /></>}
                    </Button>
                    {cbLoading && (
                      <EvidenceSearchProgress active={cbLoading} durationMs={30_000} label="Opening source and cutting evidence" />
                    )}
                    {cbExtractResult && (
                      <div className="flex items-start gap-2 rounded-lg border border-ok/25 bg-ok/5 px-3 py-2 text-xs text-ink-subtle">
                        <CheckCircle2 size={12} className="text-ok mt-0.5 shrink-0" aria-hidden="true" />
                        <span>
                          Extracted from <strong>{cbExtractResult.article.metadata.publication ?? new URL(cbExtractResult.article.url).hostname}</strong>.{" "}
                          <span className={sourceQualityColor(cbExtractResult.quality.source_quality)}>
                            {sourceQualityLabel(cbExtractResult.quality.source_quality)}.
                          </span>
                        </span>
                      </div>
                    )}
                  </div>
                )}

                {/* Paste mode input */}
                {builderMode === "paste" && (
                  <div className="flex flex-col gap-3">
                    <div>
                      <label htmlFor="cb-paste" className="text-xs font-medium text-ink-subtle block mb-1">
                        Source text
                      </label>
                      <textarea
                        id="cb-paste"
                        value={cbPastedText}
                        onChange={(e) => setCbPastedText(e.target.value)}
                        placeholder="Paste the article or passage…"
                        rows={6}
                        className="w-full rounded-lg border border-hairline bg-surface-2 px-3 py-2 text-sm text-ink leading-relaxed resize-y focus:outline-none focus:ring-2 focus:ring-lav/30 focus:border-lav/50"
                      />
                    </div>
                    <div className="grid grid-cols-1 gap-2">
                      {[
                        { id: "cb-paste-author", label: "Author", value: cbPasteAuthor, set: setCbPasteAuthor, placeholder: "Jane Doe" },
                        { id: "cb-paste-pub", label: "Publication", value: cbPastePublication, set: setCbPastePublication, placeholder: "New York Times" },
                        { id: "cb-paste-date", label: "Date", value: cbPasteDate, set: setCbPasteDate, placeholder: "2024-03-15" },
                      ].map(({ id, label, value, set, placeholder }) => (
                        <div key={id}>
                          <label htmlFor={id} className="text-xs font-medium text-ink-subtle block mb-1">
                            {label} <span className="text-ink-faint font-normal">(optional)</span>
                          </label>
                          <Input id={id} value={value} onChange={(e) => set(e.target.value)} placeholder={placeholder} className="text-sm h-8" />
                        </div>
                      ))}
                    </div>
                    <Button
                      onClick={handlePasteDraft}
                      disabled={cbLoading || !cbPastedText.trim()}
                      size="sm"
                      className="w-full"
                    >
                      {cbLoading
                        ? <><Loader2 size={13} className="mr-1.5 motion-safe:animate-spin" aria-hidden="true" />Generating…</>
                        : "Generate Card Draft"}
                    </Button>
                    {cbLoading && (
                      <EvidenceSearchProgress active={cbLoading} durationMs={20_000} label="Cleaning text and cutting evidence" />
                    )}
                  </div>
                )}

                {/* Search mode controls */}
                {builderMode === "search" && (
                  <div className="flex flex-col gap-3">
                    <ClaimDecomposition
                      claim={cbClaimGoal}
                      disabled={cbLoading}
                      isSearching={cbLoading}
                      onSearchBranch={(query) => handleGenerateCards(query)}
                      onRunAll={handleRunAllAngles}
                    />
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium text-ink-subtle">Depth</span>
                      <div
                        className="flex gap-0.5 rounded-lg border border-hairline bg-surface-2 p-0.5"
                        role="radiogroup"
                        aria-label="Research depth"
                      >
                        {RESEARCH_DEPTH_OPTIONS.map((opt) => (
                          <button
                            key={opt.key}
                            type="button"
                            role="radio"
                            aria-checked={cbDepth === opt.key}
                            title={opt.hint}
                            onClick={() => setCbDepth(opt.key)}
                            className={cn(
                              "rounded-md px-2.5 py-1 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50",
                              cbDepth === opt.key ? "bg-surface-1 text-ink shadow-xs" : "text-ink-subtle hover:text-ink",
                            )}
                          >
                            {opt.label}
                          </button>
                        ))}
                      </div>
                    </div>
                    <Button
                      onClick={() => handleGenerateCards()}
                      disabled={cbLoading || !cbClaimGoal.trim()}
                      size="sm"
                      className="w-full"
                    >
                      {cbLoading
                        ? <><Loader2 size={13} className="mr-1.5 motion-safe:animate-spin" aria-hidden="true" />Searching…</>
                        : <><Globe size={13} className="mr-1.5" aria-hidden="true" />Find candidate cards</>}
                    </Button>
                    {cbLoading && <EvidenceSearchProgress active={cbLoading} />}
                  </div>
                )}

                {cbError && (
                  <p className="rounded-lg border border-danger/25 bg-danger/5 px-3 py-2 text-xs text-danger" role="alert">
                    {cbError}
                  </p>
                )}
              </aside>

              {/* ── Center panel: source candidates ────────────────────────────── */}
              <section
                className={cn(
                  "flex flex-col gap-3 p-4 md:border-r md:border-hairline md:max-h-[calc(100vh-220px)] md:overflow-y-auto",
                  mobileStage !== "candidates" ? "hidden md:flex" : "flex",
                )}
                aria-label="Source candidates"
                aria-live="polite"
                aria-busy={cbLoading}
              >
                {/* Loading skeletons — shaped like source cards */}
                {cbLoading && (
                  <>
                    <p className="sr-only">Searching for evidence sources…</p>
                    {Array.from({ length: deriveSkeletonCount(builderMode) }).map((_, i) => (
                      <div key={i} className="rounded-xl border border-hairline bg-surface-1 p-4 flex flex-col gap-3">
                        <div className="flex items-start justify-between gap-2">
                          <Skeleton className="h-4 w-3/4 rounded" />
                          <Skeleton className="h-5 w-14 rounded-full" />
                        </div>
                        <Skeleton className="h-3 w-1/2 rounded" />
                        <Skeleton className="h-3 w-full rounded" />
                        <Skeleton className="h-3 w-5/6 rounded" />
                        <Skeleton className="h-3 w-2/3 rounded" />
                      </div>
                    ))}
                  </>
                )}

                {/* Research not configured */}
                {!cbLoading && cbGenerateResult && !cbGenerateResult.search_configured && (
                  <div className="rounded-xl border border-warn/25 bg-warn/5 px-4 py-4 flex flex-col gap-3">
                    <p className="text-sm font-semibold text-warn-dark">Research Search not configured</p>
                    <p className="text-xs text-ink-subtle leading-relaxed">
                      {cbGenerateResult.no_card_reason ?? "A Tavily API key is required. Set TAVILY_API_KEY in your backend .env file."}
                    </p>
                    {cbGenerateResult.suggestions && cbGenerateResult.suggestions.length > 0 && (
                      <ul className="text-xs text-ink-subtle list-disc list-inside flex flex-col gap-0.5">
                        {cbGenerateResult.suggestions.map((s) => <li key={s}>{s}</li>)}
                      </ul>
                    )}
                    <div className="flex items-center gap-2">
                      <Button size="sm" variant="secondary" className="h-7 px-2 text-xs gap-1"
                        onClick={() => { setBuilderMode("url"); setCbGenerateResult(null); }}>
                        <Link2 size={11} aria-hidden="true" /> From URL
                      </Button>
                      <Button size="sm" variant="secondary" className="h-7 px-2 text-xs gap-1"
                        onClick={() => { setBuilderMode("paste"); setCbGenerateResult(null); }}>
                        <ClipboardPaste size={11} aria-hidden="true" /> Paste text
                      </Button>
                    </div>
                  </div>
                )}

                {/* Research summary (transparent pipeline stages + rejected sources) */}
                {!cbLoading && cbGenerateResult?.search_configured && (
                  <ResearchSummary result={cbGenerateResult} />
                )}

                {/* Indirect support notice */}
                {!cbLoading && cbGenerateResult?.usable_indirect_support_found && !cbGenerateResult?.direct_support_found && (
                  <div className="rounded-lg border border-lav/25 bg-lav/5 px-3 py-2 text-xs text-ink-subtle">
                    No direct evidence found, but mechanism/example cards support your argument&apos;s warrant.
                  </div>
                )}

                {/* Candidate cards */}
                {shouldShowResultsSummary(cbGenerateResult, cbLoading) && cbGenerateResult && (
                  <div className="flex flex-col gap-4">
                    {/* Header + filter chips */}
                    <div className="flex items-center justify-between gap-2 flex-wrap">
                      <div className="flex items-baseline gap-2">
                        <h3 className="text-sm font-semibold text-ink">Evidence packet</h3>
                        <span className="text-xs text-ink-faint">{sortedCards.length} card{sortedCards.length !== 1 ? "s" : ""}</span>
                      </div>
                      {sortedCards.length > 1 && (
                        <div
                          className="flex items-center rounded-lg border border-hairline bg-surface-2 p-0.5"
                          role="group"
                          aria-label="Filter candidates"
                        >
                          {candidateFilterChips.map(({ key, label, count, active }) => (
                            <button
                              key={key}
                              type="button"
                              onClick={() => setCardFilter(key)}
                              aria-pressed={active}
                              className={cn(
                                "px-2.5 py-1 rounded-md text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50",
                                active ? "bg-ink text-canvas" : "text-ink-subtle hover:text-ink",
                              )}
                            >
                              {label} <span className="opacity-60 tabular-nums">{count}</span>
                            </button>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Slot progress bar (when set planner active) */}
                    {cbGenerateResult.evidence_set_plan && (() => {
                      const plan = cbGenerateResult.evidence_set_plan;
                      const slotLabels = plan?.slots?.map((s) => s.slot_label) ?? [];
                      const filledSlots = new Set(sortedCards.map((c) => c.slot_label).filter(Boolean)).size;
                      const total = slotLabels.length;
                      if (total === 0) return null;
                      const pct = Math.round((filledSlots / total) * 100);
                      return (
                        <div className="flex items-center gap-2">
                          <div
                            className="h-1 flex-1 rounded-full bg-hairline overflow-hidden"
                            role="progressbar"
                            aria-valuenow={pct}
                            aria-valuemin={0}
                            aria-valuemax={100}
                            aria-label={`${filledSlots} of ${total} evidence slots filled`}
                          >
                            <div className="h-full rounded-full bg-lav transition-all" style={{ width: `${pct}%` }} />
                          </div>
                          <span className="text-eyebrow text-ink-subtle tabular-nums whitespace-nowrap">
                            {filledSlots}/{total} slots
                          </span>
                        </div>
                      );
                    })()}

                    {/* Card list — roving tabindex for keyboard navigation */}
                    <div
                      ref={candidateListRef}
                      className="flex flex-col gap-3"
                      role="listbox"
                      aria-label="Evidence candidates"
                      onKeyDown={handleCandidateKeyDown}
                    >
                      {filteredCards.map((card, idx) => (
                        // Outer element is a div — never a button — so the inner
                        // Save/Discard/Open Studio buttons remain valid HTML.
                        // Selection fires on click/Enter/Space; inner buttons call
                        // e.stopPropagation() to prevent accidental card selection.
                        <div
                          key={card.id}
                          role="option"
                          aria-selected={selectedCardId === card.id}
                          aria-label={`${card.tag ?? "Untitled card"}. ${computeSaveReadiness(card).level === "ready" ? "Ready to save." : "Needs review."}`}
                          data-candidate="true"
                          tabIndex={activeCardIndex === idx ? 0 : -1}
                          onClick={() => handleSelectCard(card, idx)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter" || e.key === " ") {
                              e.preventDefault();
                              handleSelectCard(card, idx);
                            }
                          }}
                          className={cn(
                            "relative rounded-xl border transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50",
                            selectedCardId === card.id
                              ? "border-lav/40 ring-1 ring-lav/20"
                              : "border-hairline hover:border-hairline-strong",
                          )}
                        >
                          {idx === 0 && computeSaveReadiness(card).level === "ready" && cardFilter === "all" && (
                            <span className="absolute -top-2 left-3 z-10 text-eyebrow font-semibold px-2 py-0.5 rounded-full bg-ink text-canvas">
                              Best match
                            </span>
                          )}
                          <EvidenceCardDraft
                            card={card}
                            claimGoal={cbClaimGoal.trim()}
                            onSave={(c) => handleSaveDraft(c, true)}
                            onDiscard={handleDiscardDraft}
                            onOpenStudio={() => setStudioCard(card)}
                          />
                          <div className="mt-1.5 px-1">
                            <ProvenanceTrail card={card} />
                          </div>
                        </div>
                      ))}
                      {filteredCards.length === 0 && (
                        <p className="text-xs text-ink-subtle text-center py-6">
                          No cards match this filter.
                        </p>
                      )}
                    </div>

                    {/* Unfilled slots — strategic gaps */}
                    {cbGenerateResult.unfilled_slots && cbGenerateResult.unfilled_slots.length > 0 && (
                      <div className="rounded-lg border border-warn/25 bg-warn/5 px-3 py-3 flex flex-col gap-2">
                        <p className="text-xs font-semibold text-warn">
                          Could not fill {cbGenerateResult.unfilled_slots.length} slot{cbGenerateResult.unfilled_slots.length > 1 ? "s" : ""}: {cbGenerateResult.unfilled_slots.join(", ")}
                        </p>
                        <p className="text-xs text-ink-subtle">
                          No strong card was found automatically. Try a specific URL or paste the source.
                        </p>
                        <div className="flex gap-1.5 flex-wrap">
                          <button
                            onClick={() => { setBuilderMode("url"); setCbGenerateResult(null); }}
                            className="text-xs px-2 py-1 rounded border border-hairline bg-surface-1 text-ink-subtle hover:text-ink flex items-center gap-1 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-lav/50"
                          >
                            <Link2 size={10} aria-hidden="true" /> Try source URL
                          </button>
                          <button
                            onClick={() => { setBuilderMode("paste"); setCbGenerateResult(null); }}
                            className="text-xs px-2 py-1 rounded border border-hairline bg-surface-1 text-ink-subtle hover:text-ink flex items-center gap-1 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-lav/50"
                          >
                            <ClipboardPaste size={10} aria-hidden="true" /> Paste source
                          </button>
                          <button
                            onClick={() => handleGenerateCards()}
                            disabled={cbLoading}
                            className="text-xs px-2 py-1 rounded border border-hairline bg-surface-1 text-ink-subtle hover:text-ink focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-lav/50 disabled:opacity-50"
                          >
                            Search again
                          </button>
                        </div>
                      </div>
                    )}

                    {/* Weak leads */}
                    {cbGenerateResult.weak_leads && cbGenerateResult.weak_leads.length > 0 && (
                      <div className="rounded-lg border border-hairline bg-surface-1 px-3 py-3 flex flex-col gap-2">
                        <p className="text-xs font-semibold text-ink-subtle">
                          Source leads — verify manually before cutting
                        </p>
                        <div className="flex flex-col gap-2">
                          {cbGenerateResult.weak_leads.map((lead, i) => (
                            <div key={lead.url ?? i} className="flex items-start gap-2 border-l-2 border-hairline-strong pl-2">
                              <div className="flex-1 min-w-0 flex flex-col gap-0.5">
                                {lead.slot_label && (
                                  <span className="text-eyebrow text-ink-subtle">{lead.slot_label}</span>
                                )}
                                {lead.tag && <p className="text-xs font-medium text-ink leading-snug">{lead.tag}</p>}
                                {lead.short_cite && <p className="text-eyebrow text-ink-subtle">{lead.short_cite}</p>}
                                {lead.reason && <p className="text-eyebrow text-warn">{lead.reason}</p>}
                              </div>
                              {lead.url && (
                                <div className="flex gap-1 shrink-0">
                                  <a
                                    href={lead.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-eyebrow px-1.5 py-px rounded border border-hairline text-ink-subtle hover:text-lav hover:bg-surface-2 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-lav/50"
                                    aria-label={`Open source: ${lead.tag ?? lead.url}`}
                                  >
                                    Open ↗
                                  </a>
                                  <button
                                    onClick={() => { setBuilderMode("url"); setCbUrl(lead.url!); setCbGenerateResult(null); }}
                                    className="text-eyebrow px-1.5 py-px rounded border border-hairline text-ink-subtle hover:text-ink hover:bg-surface-2 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-lav/50"
                                  >
                                    Extract
                                  </button>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* No cards found */}
                {!cbLoading && cbGenerateResult && cbGenerateResult.search_configured && cbGenerateResult.cards.length === 0 && (() => {
                  const diag = cbGenerateResult.diagnostics;
                  const hasCounterEvidence = (diag?.rejected_as_counter_evidence ?? 0) > 0;
                  const hasIndirectSupport = cbGenerateResult.usable_indirect_support_found === true;
                  const leadUrls = diag?.possible_lead_urls ?? [];
                  const trace = cbGenerateResult.search_trace;

                  return (
                    <div className="flex flex-col gap-3">
                      {/* Structured failure panel when trace is available */}
                      {trace ? (
                        <SearchFailurePanel
                          trace={trace}
                          noCardReason={cbGenerateResult.no_card_reason}
                        />
                      ) : (
                        <div className="rounded-xl border border-hairline bg-surface-1 px-4 py-4 flex flex-col gap-3">
                          <p className="text-sm font-semibold text-ink">
                            {hasCounterEvidence
                              ? "Sources found argue against this claim"
                              : hasIndirectSupport
                              ? "Indirect support found — needs a link card"
                              : "No cards found for this claim"}
                          </p>
                          {cbGenerateResult.no_card_reason && (
                            <p className="text-xs text-ink-subtle leading-relaxed">{cbGenerateResult.no_card_reason}</p>
                          )}
                        </div>
                      )}

                      {/* Indirect support tip */}
                      {hasIndirectSupport && cbGenerateResult.indirect_support_explanation && (
                        <div className="rounded-lg border border-lav/25 bg-lav/5 px-3 py-2">
                          <p className="text-xs text-ink-subtle leading-relaxed">
                            <strong>Tip:</strong> {cbGenerateResult.indirect_support_explanation}
                          </p>
                        </div>
                      )}

                      {/* Counter-evidence pre-empt banner */}
                      {hasCounterEvidence && (
                        <div className="rounded-lg border border-warn/25 bg-warn/5 px-3 py-2">
                          <p className="text-xs text-warn leading-relaxed">
                            <strong>Pre-empt opportunity:</strong> Sources argue the other side. Consider cutting these as pre-empt answers.
                          </p>
                        </div>
                      )}

                      {/* Lead URLs for manual review */}
                      {leadUrls.length > 0 && (
                        <div className="flex flex-col gap-1">
                          <p className="text-xs font-medium text-ink-subtle">Worth checking manually:</p>
                          {leadUrls.slice(0, 3).map((u) => (
                            <button
                              key={u}
                              type="button"
                              onClick={() => { setBuilderMode("url"); setCbUrl(u); setCbGenerateResult(null); }}
                              className="text-xs text-ink-subtle underline underline-offset-2 hover:text-ink text-left truncate focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-lav/50 rounded"
                            >
                              {u}
                            </button>
                          ))}
                        </div>
                      )}

                      {/* Revised claim suggestions */}
                      {cbGenerateResult.suggested_revised_claims && cbGenerateResult.suggested_revised_claims.length > 0 && (
                        <div className="flex flex-col gap-1.5">
                          <p className="text-xs font-medium text-ink-subtle">Try a narrower claim:</p>
                          <div className="flex flex-wrap gap-1.5">
                            {cbGenerateResult.suggested_revised_claims.map((claim) => (
                              <button
                                key={claim}
                                type="button"
                                onClick={() => { setCbClaimGoal(claim); setCbGenerateResult(null); }}
                                className="text-xs px-2 py-1 rounded-full border border-hairline text-ink-subtle hover:text-lav hover:border-lav/40 hover:bg-lav/5 transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-lav/50"
                              >
                                {claim}
                              </button>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Mode-switch buttons */}
                      <div className="flex gap-2">
                        <Button size="sm" variant="secondary" className="h-7 px-2 text-xs gap-1"
                          onClick={() => { setBuilderMode("url"); setCbGenerateResult(null); }}>
                          <Link2 size={11} aria-hidden="true" /> Try a URL
                        </Button>
                        <Button size="sm" variant="secondary" className="h-7 px-2 text-xs gap-1"
                          onClick={() => { setBuilderMode("paste"); setCbGenerateResult(null); }}>
                          <ClipboardPaste size={11} aria-hidden="true" /> Paste text
                        </Button>
                      </div>
                    </div>
                  );
                })()}

                {/* Older drafts not in the current search results */}
                {(() => {
                  const searchCardIds = new Set((cbGenerateResult?.cards ?? []).map((c) => c.id));
                  const visibleDrafts = drafts.filter((d) => d.status !== "discarded" && !searchCardIds.has(d.id));
                  const showEmpty = shouldShowEmptyState(cbGenerateResult, drafts, cbLoading);

                  if (draftsLoading) {
                    return (
                      <div className="flex flex-col gap-2">
                        {[1, 2].map((i) => <Skeleton key={i} className="h-28 w-full rounded-xl" />)}
                      </div>
                    );
                  }
                  if (visibleDrafts.length > 0) {
                    return (
                      <div className="flex flex-col gap-2.5">
                        <p className="text-eyebrow text-ink-faint">Previous drafts</p>
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
                  if (showEmpty) {
                    return (
                      <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-hairline px-8 py-10 text-center">
                        <Sparkles size={16} className="text-ink-faint" aria-hidden="true" />
                        <div>
                          <p className="text-sm font-semibold text-ink">No card drafts yet</p>
                          <p className="text-xs text-ink-subtle mt-0.5">
                            Enter a URL, paste text, or run a research search to generate your first card draft.
                          </p>
                        </div>
                      </div>
                    );
                  }
                  return null;
                })()}
              </section>

              {/* ── Right panel: card draft, citation, save state ──────────────── */}
              <aside
                className={cn(
                  "flex flex-col gap-4 p-4 md:max-h-[calc(100vh-220px)] md:overflow-y-auto",
                  mobileStage !== "card" ? "hidden md:flex" : "flex",
                )}
                aria-label="Card draft and save"
              >
                {selectedCard ? (
                  <>
                    {/* Save error */}
                    {saveError && (
                      <div
                        className="rounded-lg border border-danger/25 bg-danger/5 px-3 py-2 text-xs text-danger"
                        role="alert"
                      >
                        <span>{saveError}</span>
                        <button
                          type="button"
                          className="ml-2 underline focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-danger/50 rounded"
                          onClick={() => { setSaveError(""); handleSaveDraft(selectedCard!, true); }}
                        >
                          Retry
                        </button>
                        <button
                          type="button"
                          className="ml-1.5 underline focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-danger/50 rounded"
                          onClick={() => setSaveError("")}
                        >
                          Dismiss
                        </button>
                      </div>
                    )}
                    {/* Save success */}
                    {lastSavedCardId && !saveError && (
                      <div
                        className="rounded-lg border border-ok/25 bg-ok/5 px-3 py-2 text-xs text-ok"
                        role="status"
                      >
                        Card saved to your library.{" "}
                        <button
                          type="button"
                          className="underline focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ok/50 rounded"
                          onClick={() => setActiveTab("library")}
                        >
                          View in Library
                        </button>
                      </div>
                    )}
                    <div className="flex items-center justify-between">
                      <h2 className="text-eyebrow text-ink-faint">Card draft</h2>
                      <button
                        type="button"
                        onClick={() => setStudioCard(selectedCard)}
                        className="text-[11px] text-lav hover:underline focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-lav/50 rounded"
                      >
                        Open in Studio ↗
                      </button>
                    </div>
                    <EvidenceCardDraft
                      card={selectedCard}
                      claimGoal={cbClaimGoal.trim()}
                      onSave={(c) => handleSaveDraft(c, true)}
                      onDiscard={handleDiscardDraft}
                      onOpenStudio={() => setStudioCard(selectedCard)}
                    />
                  </>
                ) : (
                  <div className="flex-1 flex flex-col items-center justify-center gap-3 text-center py-12">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-dashed border-hairline-strong">
                      <FileText size={16} className="text-ink-faint" aria-hidden="true" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-ink-subtle">Select a candidate</p>
                      <p className="text-xs text-ink-faint mt-0.5">Click any card in the center panel to preview and save it</p>
                    </div>
                  </div>
                )}
              </aside>
            </div>
          </section>
        )}

        {/* ── Library tab ───────────────────────────────────────────────────── */}
        {activeTab === "library" && (
          <div className="flex flex-col gap-8">

            {/* Upload panel */}
            <section aria-labelledby="upload-heading">
              <h2 id="upload-heading" className="section-stamp mb-3 block">Upload document</h2>
              <div className="rounded-xl border border-hairline bg-surface-1 p-4 flex flex-col gap-4">
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploading}
                  aria-label={selectedFile ? `Selected: ${selectedFile.name}. Press to change file.` : "Select a file to upload"}
                  className={cn(
                    "flex flex-col items-center gap-3 p-8 text-center rounded-lg border-2 border-dashed transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50",
                    selectedFile ? "border-lav/30 bg-lav/[0.03]" : "border-hairline-strong hover:border-lav/30",
                    uploading && "pointer-events-none opacity-50",
                  )}
                >
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-hairline bg-surface-2">
                    <Upload size={16} className="text-ink-subtle" aria-hidden="true" />
                  </div>
                  {selectedFile ? (
                    <div className="flex flex-col gap-0.5">
                      <span className="text-sm font-medium text-ink">{selectedFile.name}</span>
                      <span className="text-xs text-ink-subtle">{fileSizeLabel(selectedFile.size)}</span>
                    </div>
                  ) : (
                    <div className="flex flex-col gap-0.5">
                      <span className="text-sm font-medium text-ink">Click or press to select a file</span>
                      <span className="text-xs text-ink-subtle">
                        {ALLOWED_EVIDENCE_EXTS.join(", ")} · max {MAX_EVIDENCE_MB} MB
                      </span>
                    </div>
                  )}
                </button>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept={ALLOWED_EVIDENCE_EXTS.map((e) => `.${e}`).join(",")}
                  onChange={handleFileChange}
                  disabled={uploading}
                  className="sr-only"
                  tabIndex={-1}
                />

                {fileError && <p className="text-xs text-danger" role="alert">{fileError}</p>}
                {uploadError && <p className="text-xs text-danger" role="alert">{uploadError}</p>}

                {selectedFile && (
                  <div className="flex flex-wrap items-center gap-3">
                    <select
                      value={docType}
                      onChange={(e) => setDocType(e.target.value)}
                      disabled={uploading}
                      aria-label="Document type"
                      className="h-9 rounded-lg border border-hairline bg-surface-1 px-3 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-lav/30"
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
                      aria-label="Document role"
                      className="h-9 rounded-lg border border-hairline bg-surface-1 px-3 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-lav/30"
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
                      onClick={() => { setSelectedFile(null); if (fileInputRef.current) fileInputRef.current.value = ""; }}
                      className="gap-1"
                    >
                      <X size={12} aria-hidden="true" /> Clear
                    </Button>
                  </div>
                )}
              </div>
              <p className="mt-2 text-xs text-ink-subtle">
                Dissio extracts evidence cards from your file. It never invents citations.
              </p>
            </section>

            {/* Library search */}
            {parsedCount > 0 && (
              <section aria-labelledby="search-heading">
                <h2 id="search-heading" className="section-stamp mb-3 block">Search evidence</h2>
                <div className="mb-2 flex items-center gap-1" role="group" aria-label="Search mode">
                  {(["keyword", "semantic", "hybrid"] as const).map((m) => (
                    <button
                      key={m}
                      type="button"
                      aria-pressed={searchMode === m}
                      onClick={() => setSearchMode(m)}
                      className={cn(
                        "rounded-full border px-3 py-1 text-[10px] font-semibold uppercase tracking-wide transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50",
                        searchMode === m
                          ? "border-lav/40 bg-lav/10 text-lav"
                          : "border-hairline bg-surface-2 text-ink-subtle hover:text-ink",
                      )}
                    >
                      {m}
                    </button>
                  ))}
                </div>
                <p className="mb-2 text-[10px] text-ink-faint">
                  {searchMode === "keyword" && "Matches exact words. Fast and deterministic."}
                  {searchMode === "semantic" && "Finds conceptually related evidence even when wording differs."}
                  {searchMode === "hybrid" && "Semantic results first, then keyword fill. Recommended."}
                </p>
                <form onSubmit={handleSearch} className="flex gap-2">
                  <Input
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="e.g. deterrence fiscal burden alliance credibility"
                    className="flex-1 text-sm"
                    disabled={searching}
                    aria-label="Search your evidence library"
                  />
                  <Button type="submit" size="sm" disabled={searching || !searchQuery.trim()}>
                    <Search size={14} className="mr-1.5" aria-hidden="true" />
                    {searching ? "Searching…" : "Search"}
                  </Button>
                </form>
                {searchError && <p className="mt-2 text-xs text-danger" role="alert">{searchError}</p>}
                {searchResults !== null && (
                  <div className="mt-3 flex flex-col gap-2" aria-live="polite">
                    {searchResults.length === 0 ? (
                      <p className="text-sm text-ink-subtle">
                        No matching evidence found in your library.
                        {searchMode !== "keyword" && (
                          <span className="block mt-1 text-xs text-ink-faint">
                            If documents were uploaded before semantic search was enabled, try re-embedding or switch to Keyword mode.
                          </span>
                        )}
                      </p>
                    ) : (
                      <>
                        <p className="text-xs text-ink-subtle">
                          {searchResults.length} result{searchResults.length !== 1 ? "s" : ""}
                          {searchResults.some((r) => r.retrieval_mode === "semantic" || r.retrieval_mode === "hybrid") && (
                            <span className="ml-2 text-lav font-medium">semantic</span>
                          )}
                        </p>
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
            <section aria-labelledby="docs-heading">
              <div className="mb-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <h2 id="docs-heading" className="section-stamp">Case files</h2>
                  {documents.length > 0 && <span className="rep-badge">{documents.length}</span>}
                </div>
                {parsedCount > 0 && <span className="section-stamp">{parsedCount} ready</span>}
              </div>
              {docsLoading ? (
                <div className="flex flex-col gap-3">
                  {[1, 2].map((i) => <Skeleton key={i} className="h-20 w-full rounded-xl" />)}
                </div>
              ) : documents.length === 0 ? (
                <div className="flex flex-col items-center gap-4 rounded-xl border border-dashed border-hairline px-8 py-10 text-center">
                  <EmptyEvidenceGlyph className="h-10 w-12 text-ink-faint opacity-60" />
                  <div>
                    <p className="text-sm font-semibold text-ink">No case files yet</p>
                    <p className="text-xs text-ink-subtle mt-0.5">
                      Upload a case file or evidence packet above. Dissio will extract evidence cards you can cite.
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

            {/* Blockfile Trainer */}
            <section aria-labelledby="blocks-heading">
              <div className="mb-3 flex items-center gap-2">
                <BookOpen size={14} className="text-ink-faint shrink-0" aria-hidden="true" />
                <h2 id="blocks-heading" className="section-stamp">Blockfile Trainer</h2>
                {blockEntries.length > 0 && <span className="rep-badge">{blockEntries.length}</span>}
              </div>
              <p className="mb-3 text-xs text-ink-subtle leading-relaxed">
                Extract block and frontline entries from uploaded documents using the &ldquo;Extract blocks&rdquo;
                button above. Then search your block library to find prepared responses.
                Only your uploaded files are used — no outside knowledge.
              </p>
              {blockEntries.length > 0 && (
                <form onSubmit={handleBlockSearch} className="mb-4 flex gap-2">
                  <Input
                    value={blockSearchQuery}
                    onChange={(e) => setBlockSearchQuery(e.target.value)}
                    placeholder="Search blocks e.g. deterrence privacy rights"
                    className="flex-1 text-sm"
                    disabled={blockSearching}
                    aria-label="Search block entries"
                  />
                  <Button type="submit" size="sm" disabled={blockSearching || !blockSearchQuery.trim()}>
                    {blockSearching
                      ? <><Loader2 size={13} className="mr-1.5 motion-safe:animate-spin" aria-hidden="true" />Searching…</>
                      : <><Search size={13} className="mr-1.5" aria-hidden="true" />Search blocks</>}
                  </Button>
                  {blockSearchResults !== null && (
                    <Button type="button" variant="secondary" size="sm"
                      onClick={() => { setBlockSearchResults(null); setBlockSearchQuery(""); }}>
                      Clear
                    </Button>
                  )}
                </form>
              )}
              {blockSearchErr && <p className="mb-2 text-xs text-danger" role="alert">{blockSearchErr}</p>}
              {blockEntriesLoading ? (
                <div className="flex flex-col gap-2">
                  {[1, 2, 3].map((i) => <Skeleton key={i} className="h-16 w-full rounded-xl" />)}
                </div>
              ) : (blockSearchResults ?? blockEntries).length === 0 ? (
                <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-hairline px-6 py-8 text-center">
                  <Sparkles size={16} className="text-ink-faint" aria-hidden="true" />
                  <div>
                    <p className="text-sm font-semibold text-ink">No block entries yet</p>
                    <p className="text-xs text-ink-subtle mt-0.5">
                      Upload a blockfile or frontline document above, then click &ldquo;Extract blocks&rdquo; to populate your block library.
                    </p>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col gap-2">
                  {blockSearchResults !== null && (
                    <p className="text-xs text-ink-subtle">
                      {blockSearchResults.length} result{blockSearchResults.length !== 1 ? "s" : ""} for &ldquo;{blockSearchQuery}&rdquo;
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

          </div>
        )}

      </div>
    </div>
  );
}
