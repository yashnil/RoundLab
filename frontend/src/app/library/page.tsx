"use client";

import { useState, useEffect } from "react";
import { BookOpen, Search, Plus, FileText, Network, X } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { createClient } from "@/lib/supabase";
import type {
  LibrarySearchResult,
  LibrarySearchResponse,
  Resolution,
  Blockfile,
  Side,
} from "@/types/library";
import { SaveToLibraryDialog } from "@/components/library/SaveToLibraryDialog";
import { BlockfileEditor } from "@/components/library/BlockfileEditor";
import { FrontlineBuilder } from "@/components/library/FrontlineBuilder";

// ── Side selector chip ─────────────────────────────────────────────────────

const SIDE_COLORS: Record<Side, string> = {
  pro: "bg-sky-100 text-sky-800 border-sky-200",
  con: "bg-rose-100 text-rose-800 border-rose-200",
  neutral: "bg-surface-muted text-ink-subtle border-border",
};

// ── Library card row ───────────────────────────────────────────────────────

function LibraryCardRow({
  result,
  onSelect,
}: {
  result: LibrarySearchResult;
  onSelect: () => void;
}) {
  const verdictColor =
    result.support_verdict === "supported"
      ? "text-ok"
      : result.support_verdict === "partially_supported"
        ? "text-amber-600"
        : result.support_verdict
          ? "text-danger"
          : "text-ink-subtle";

  return (
    <button
      onClick={onSelect}
      className="w-full text-left rounded-xl border border-border hover:border-lav/30 hover:bg-surface-muted/60 transition-all px-4 py-3 space-y-1.5"
    >
      <div className="flex items-start gap-2">
        <div className="flex-1 min-w-0">
          <p className="text-[13px] font-semibold text-ink truncate">
            {result.tag || "Untitled card"}
          </p>
          <p className="text-[11px] text-ink-subtle truncate">{result.cite}</p>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          {result.side && (
            <span className={`text-[10px] px-1.5 py-0.5 rounded border capitalize ${SIDE_COLORS[result.side as Side] ?? "bg-surface-muted"}`}>
              {result.side}
            </span>
          )}
          {result.support_verdict && (
            <span className={`text-[10px] font-medium ${verdictColor}`}>
              {result.support_verdict.replace("_", " ")}
            </span>
          )}
        </div>
      </div>
      {result.body_preview && (
        <p className="text-[11px] text-ink-subtle line-clamp-2 leading-relaxed">
          {result.body_preview}
        </p>
      )}
      <div className="flex items-center gap-2 flex-wrap">
        {result.argument_title && (
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-lav/10 text-lav border border-lav/20">
            {result.argument_title}
          </span>
        )}
        {result.tags.map((t) => (
          <span key={t} className="text-[10px] px-1.5 py-0.5 rounded bg-surface-muted border border-border text-ink-subtle">
            {t}
          </span>
        ))}
        <span className="text-[10px] text-ink-faint ml-auto">
          {new Date(result.saved_at).toLocaleDateString()}
        </span>
      </div>
    </button>
  );
}

// ── Create blockfile mini-form ─────────────────────────────────────────────

function NewBlockfileForm({
  userId,
  resolutions,
  onCreated,
  onCancel,
}: {
  userId: string;
  resolutions: Resolution[];
  onCreated: (bf: Blockfile) => void;
  onCancel: () => void;
}) {
  const [title, setTitle] = useState("");
  const [resolutionId, setResolutionId] = useState("");
  const [side, setSide] = useState<Side>("pro");
  const [saving, setSaving] = useState(false);

  async function create() {
    if (!title.trim()) return;
    setSaving(true);
    try {
      const bf = await apiFetch("/library/blockfiles", {
        method: "POST",
        body: JSON.stringify({
          user_id: userId,
          title: title.trim(),
          resolution_id: resolutionId || undefined,
          side,
        }),
      }) as Blockfile;
      onCreated(bf);
    } catch {
      setSaving(false);
    }
  }

  return (
    <div className="rounded-xl border border-border bg-surface-muted p-4 space-y-2">
      <input
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Blockfile name (e.g., Neg frontlines on Economy)"
        className="w-full text-[13px] border border-border rounded-md px-2.5 py-1.5 bg-surface-1 text-ink"
        autoFocus
      />
      <div className="flex gap-2">
        <select
          value={resolutionId}
          onChange={(e) => setResolutionId(e.target.value)}
          className="flex-1 text-[12px] border border-border rounded-md px-2 py-1.5 bg-surface-1 text-ink"
        >
          <option value="">No resolution</option>
          {resolutions.map((r) => (
            <option key={r.id} value={r.id}>{r.title}</option>
          ))}
        </select>
        <select
          value={side}
          onChange={(e) => setSide(e.target.value as Side)}
          className="text-[12px] border border-border rounded-md px-2 py-1.5 bg-surface-1 text-ink"
        >
          <option value="pro">Pro</option>
          <option value="con">Con</option>
          <option value="neutral">Neutral</option>
        </select>
      </div>
      <div className="flex gap-2">
        <button
          onClick={create}
          disabled={saving || !title.trim()}
          className="flex-1 text-[12px] py-1.5 rounded-md bg-ink text-canvas disabled:opacity-40"
        >
          {saving ? "Creating…" : "Create"}
        </button>
        <button
          onClick={onCancel}
          className="text-[12px] px-3 py-1.5 rounded-md border border-border text-ink-subtle"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────

type Tab = "cards" | "blockfiles" | "frontlines";

export default function LibraryPage() {
  const [userId, setUserId] = useState<string>("");

  useEffect(() => {
    createClient()
      .auth.getUser()
      .then(({ data }) => setUserId(data.user?.id ?? ""));
  }, []);

  const [tab, setTab] = useState<Tab>("cards");
  const [query, setQuery] = useState("");
  const [resolutionId, setResolutionId] = useState("");
  const [sideFilter, setSideFilter] = useState<Side | "">("");
  const [verdictFilter, setVerdictFilter] = useState("");

  const [resolutions, setResolutions] = useState<Resolution[]>([]);
  const [blockfiles, setBlockfiles] = useState<Blockfile[]>([]);
  const [selectedBlockfile, setSelectedBlockfile] = useState<Blockfile | null>(null);
  const [showNewBlockfile, setShowNewBlockfile] = useState(false);

  const [results, setResults] = useState<LibrarySearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [selectedCard, setSelectedCard] = useState<LibrarySearchResult | null>(null);

  async function loadResolutions() {
    if (!userId) return;
    const data = await apiFetch(`/library/resolutions?user_id=${userId}&active_only=true`);
    setResolutions(data as Resolution[]);
  }

  async function loadBlockfiles() {
    if (!userId) return;
    const data = await apiFetch(
      `/library/blockfiles?user_id=${userId}${resolutionId ? `&resolution_id=${resolutionId}` : ""}`,
    );
    setBlockfiles(data as Blockfile[]);
  }

  async function search() {
    if (!userId) return;
    setSearching(true);
    try {
      const data = await apiFetch("/library/search", {
        method: "POST",
        body: JSON.stringify({
          user_id: userId,
          query: query || undefined,
          resolution_id: resolutionId || undefined,
          side: sideFilter || undefined,
          support_verdict: verdictFilter || undefined,
          limit: 40,
        }),
      }) as LibrarySearchResponse;
      setResults(data.results);
    } catch {
      setResults([]);
    } finally {
      setSearching(false);
    }
  }

  useEffect(() => {
    loadResolutions();
  }, [userId]);

  useEffect(() => {
    if (tab === "cards") search();
    if (tab === "blockfiles") loadBlockfiles();
  }, [tab, userId, resolutionId, sideFilter, verdictFilter]);

  useEffect(() => {
    const t = setTimeout(() => {
      if (tab === "cards") search();
    }, 400);
    return () => clearTimeout(t);
  }, [query]);

  if (!userId) {
    return (
      <div className="flex items-center justify-center h-64 text-ink-subtle text-[13px]">
        Sign in to access your evidence library.
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <BookOpen size={22} className="text-lav" />
          <div>
            <h1 className="text-[20px] font-bold text-ink">Evidence Library</h1>
            <p className="text-[12px] text-ink-subtle">Organized, reusable research by argument</p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-hairline">
        {(["cards", "blockfiles", "frontlines"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-[13px] font-medium transition-colors border-b-2 -mb-px capitalize ${
              tab === t
                ? "border-lav text-lav"
                : "border-transparent text-ink-subtle hover:text-ink"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {/* ── Cards tab ──────────────────────────────────────────────────── */}
      {tab === "cards" && (
        <div className="space-y-4">
          {/* Filters */}
          <div className="flex items-center gap-2 flex-wrap">
            <div className="relative flex-1 min-w-[200px]">
              <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-ink-subtle" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search cards by tag, source, notes…"
                className="w-full pl-8 pr-3 py-1.5 text-[13px] border border-border rounded-lg bg-surface-1 text-ink focus:outline-none focus:ring-2 focus:ring-lav/40"
              />
              {query && (
                <button
                  onClick={() => setQuery("")}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-ink-subtle hover:text-ink"
                >
                  <X size={13} />
                </button>
              )}
            </div>
            <select
              value={resolutionId}
              onChange={(e) => setResolutionId(e.target.value)}
              className="text-[12px] border border-border rounded-lg px-2 py-1.5 bg-surface-1 text-ink"
            >
              <option value="">All resolutions</option>
              {resolutions.map((r) => (
                <option key={r.id} value={r.id}>{r.title}</option>
              ))}
            </select>
            <select
              value={sideFilter}
              onChange={(e) => setSideFilter(e.target.value as Side | "")}
              className="text-[12px] border border-border rounded-lg px-2 py-1.5 bg-surface-1 text-ink"
            >
              <option value="">All sides</option>
              <option value="pro">Pro</option>
              <option value="con">Con</option>
              <option value="neutral">Neutral</option>
            </select>
            <select
              value={verdictFilter}
              onChange={(e) => setVerdictFilter(e.target.value)}
              className="text-[12px] border border-border rounded-lg px-2 py-1.5 bg-surface-1 text-ink"
            >
              <option value="">Any verdict</option>
              <option value="supported">Supported</option>
              <option value="partially_supported">Partially supported</option>
              <option value="unsupported">Unsupported</option>
              <option value="contradicted">Contradicted</option>
            </select>
          </div>

          {searching && (
            <p className="text-[12px] text-ink-subtle">Searching…</p>
          )}

          {!searching && results.length === 0 && (
            <div className="py-12 text-center">
              <BookOpen size={28} className="mx-auto mb-3 text-ink-faint" />
              <p className="text-[13px] text-ink-subtle">
                No cards saved yet. Save evidence cards from the Evidence Studio.
              </p>
            </div>
          )}

          <div className="space-y-2">
            {results.map((r) => (
              <LibraryCardRow
                key={r.card_id}
                result={r}
                onSelect={() => setSelectedCard(r)}
              />
            ))}
          </div>
        </div>
      )}

      {/* ── Blockfiles tab ────────────────────────────────────────────── */}
      {tab === "blockfiles" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-[13px] text-ink-subtle">
              {blockfiles.length} blockfile{blockfiles.length !== 1 ? "s" : ""}
            </p>
            <button
              onClick={() => setShowNewBlockfile(true)}
              className="flex items-center gap-1.5 text-[12px] px-3 py-1.5 rounded-lg border border-border text-ink hover:bg-surface-muted transition-colors"
            >
              <Plus size={13} />
              New Blockfile
            </button>
          </div>

          {showNewBlockfile && (
            <NewBlockfileForm
              userId={userId}
              resolutions={resolutions}
              onCreated={(bf) => {
                setBlockfiles((prev) => [bf, ...prev]);
                setSelectedBlockfile(bf);
                setShowNewBlockfile(false);
              }}
              onCancel={() => setShowNewBlockfile(false)}
            />
          )}

          {selectedBlockfile ? (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setSelectedBlockfile(null)}
                  className="text-[11px] text-ink-subtle hover:text-ink"
                >
                  ← All blockfiles
                </button>
              </div>
              <BlockfileEditor blockfile={selectedBlockfile} userId={userId} />
            </div>
          ) : (
            <div className="space-y-2">
              {blockfiles.length === 0 && !showNewBlockfile && (
                <div className="py-12 text-center">
                  <FileText size={28} className="mx-auto mb-3 text-ink-faint" />
                  <p className="text-[13px] text-ink-subtle">
                    No blockfiles yet. Create one to organize your evidence.
                  </p>
                </div>
              )}
              {blockfiles.map((bf) => (
                <button
                  key={bf.id}
                  onClick={() => setSelectedBlockfile(bf)}
                  className="w-full text-left rounded-xl border border-border hover:border-lav/30 hover:bg-surface-muted/60 transition-all px-4 py-3"
                >
                  <div className="flex items-center gap-2">
                    <FileText size={15} className="text-ink-subtle shrink-0" />
                    <p className="text-[13px] font-semibold text-ink">{bf.title}</p>
                    {bf.side && (
                      <span className={`text-[10px] px-1.5 py-0.5 rounded border capitalize ${SIDE_COLORS[bf.side as Side] ?? ""}`}>
                        {bf.side}
                      </span>
                    )}
                  </div>
                  {bf.description && (
                    <p className="text-[11px] text-ink-subtle mt-1 ml-6">{bf.description}</p>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Frontlines tab (placeholder) ──────────────────────────────── */}
      {tab === "frontlines" && (
        <div className="py-12 text-center">
          <Network size={28} className="mx-auto mb-3 text-ink-faint" />
          <p className="text-[13px] text-ink-subtle">
            Frontlines are associated with blockfile sections. Open a blockfile to add frontlines.
          </p>
        </div>
      )}
    </div>
  );
}
