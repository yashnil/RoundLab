"use client";

import { useState, useEffect } from "react";
import { Link2, Plus, Trash2, Check, X } from "lucide-react";
import { apiFetch } from "@/lib/api";
import type { CardRelationship, RelationshipType } from "@/types/library";

const RELATIONSHIP_LABELS: Record<RelationshipType, string> = {
  supports: "Supports",
  contradicts: "Contradicts",
  updates: "Updates / replaces",
  qualifies: "Qualifies",
  same_finding: "Same finding",
  stronger_source: "Stronger source",
  primary_source_for: "Primary source for",
  responds_to: "Responds to",
  turns: "Turns",
  mitigates: "Mitigates",
  outweighs: "Outweighs",
};

interface CardRelationshipPanelProps {
  cardId: string;
  userId: string;
}

export function CardRelationshipPanel({ cardId, userId }: CardRelationshipPanelProps) {
  const [relationships, setRelationships] = useState<CardRelationship[]>([]);
  const [suggestions, setSuggestions] = useState<unknown[]>([]);
  const [loading, setLoading] = useState(true);
  const [toCardId, setToCardId] = useState("");
  const [relType, setRelType] = useState<RelationshipType>("supports");
  const [explanation, setExplanation] = useState("");
  const [adding, setAdding] = useState(false);
  const [showForm, setShowForm] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const [rels, suggs] = await Promise.all([
        apiFetch(`/library/cards/${cardId}/relationships?user_id=${userId}`),
        apiFetch(`/library/cards/${cardId}/suggest-relationships?user_id=${userId}`),
      ]);
      setRelationships(rels as CardRelationship[]);
      setSuggestions(suggs as unknown[]);
    } catch {
      // non-fatal
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [cardId, userId]);

  async function addRelationship() {
    if (!toCardId.trim()) return;
    setAdding(true);
    try {
      await apiFetch(`/library/cards/${cardId}/relationships`, {
        method: "POST",
        body: JSON.stringify({
          user_id: userId,
          from_card_id: cardId,
          to_card_id: toCardId.trim(),
          relationship_type: relType,
          confidence: "manual",
          explanation: explanation || undefined,
          confirmed: true,
        }),
      });
      setToCardId("");
      setExplanation("");
      setShowForm(false);
      await load();
    } catch {
      // non-fatal
    } finally {
      setAdding(false);
    }
  }

  async function confirmSuggestion(suggestion: Record<string, unknown>) {
    try {
      await apiFetch(`/library/cards/${cardId}/relationships`, {
        method: "POST",
        body: JSON.stringify({
          user_id: userId,
          from_card_id: suggestion.from_card_id,
          to_card_id: suggestion.to_card_id,
          relationship_type: suggestion.relationship_type,
          confidence: "manual",
          explanation: suggestion.explanation,
          confirmed: true,
        }),
      });
      await load();
    } catch {}
  }

  async function deleteRelationship(id: string) {
    try {
      await apiFetch(`/library/relationships/${id}?user_id=${userId}`, {
        method: "DELETE",
      });
      setRelationships((prev) => prev.filter((r) => r.id !== id));
    } catch {}
  }

  if (loading) {
    return <div className="text-[11px] text-ink-subtle py-2">Loading relationships…</div>;
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <Link2 size={14} className="text-ink-subtle" />
          <span className="text-[12px] font-semibold text-ink">Card Relationships</span>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-1 text-[11px] text-lav hover:underline"
        >
          <Plus size={12} />
          Add
        </button>
      </div>

      {showForm && (
        <div className="rounded-lg border border-border bg-surface-muted p-3 space-y-2">
          <input
            value={toCardId}
            onChange={(e) => setToCardId(e.target.value)}
            placeholder="Target card ID"
            className="w-full text-[12px] border border-border rounded-md px-2 py-1 bg-surface-1 text-ink"
          />
          <select
            value={relType}
            onChange={(e) => setRelType(e.target.value as RelationshipType)}
            className="w-full text-[12px] border border-border rounded-md px-2 py-1 bg-surface-1 text-ink"
          >
            {(Object.entries(RELATIONSHIP_LABELS) as [RelationshipType, string][]).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </select>
          <input
            value={explanation}
            onChange={(e) => setExplanation(e.target.value)}
            placeholder="Why? (optional)"
            className="w-full text-[12px] border border-border rounded-md px-2 py-1 bg-surface-1 text-ink"
          />
          <div className="flex gap-2">
            <button
              onClick={addRelationship}
              disabled={adding || !toCardId.trim()}
              className="flex-1 text-[11px] py-1 rounded-md bg-ink text-canvas disabled:opacity-40"
            >
              {adding ? "Adding…" : "Add"}
            </button>
            <button
              onClick={() => setShowForm(false)}
              className="text-[11px] px-2 py-1 rounded-md border border-border text-ink-subtle"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Suggestions */}
      {suggestions.length > 0 && (
        <div>
          <p className="text-[10px] text-ink-muted font-medium uppercase tracking-wide mb-1.5">
            Suggested ({suggestions.length})
          </p>
          {(suggestions as Record<string, unknown>[]).map((s, i) => (
            <div key={i} className="flex items-start gap-2 py-1.5 border-b border-hairline last:border-0">
              <div className="flex-1 min-w-0">
                <p className="text-[11px] text-ink truncate">
                  {String(s.to_card_id).slice(0, 12)}… — {RELATIONSHIP_LABELS[s.relationship_type as RelationshipType]}
                </p>
                <p className="text-[10px] text-ink-subtle">{String(s.explanation)}</p>
              </div>
              <div className="flex gap-1 shrink-0">
                <button
                  onClick={() => confirmSuggestion(s)}
                  className="p-1 rounded text-ok hover:bg-ok/10"
                  aria-label="Confirm suggestion"
                >
                  <Check size={12} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Confirmed relationships */}
      {relationships.length === 0 && suggestions.length === 0 && (
        <p className="text-[11px] text-ink-subtle italic">No relationships yet.</p>
      )}
      {relationships.map((r) => (
        <div key={r.id} className="flex items-start gap-2 py-1.5 border-b border-hairline last:border-0">
          <div className="flex-1 min-w-0">
            <p className="text-[11px] text-ink">
              <span className="font-medium">{RELATIONSHIP_LABELS[r.relationship_type]}</span>
              {" "}→ {r.to_card_id === cardId ? r.from_card_id : r.to_card_id}
            </p>
            {r.explanation && (
              <p className="text-[10px] text-ink-subtle">{r.explanation}</p>
            )}
            <p className="text-[10px] text-ink-faint">
              {r.confidence} · {r.confirmed ? "confirmed" : "unconfirmed"}
            </p>
          </div>
          <button
            onClick={() => deleteRelationship(r.id)}
            className="p-1 rounded text-ink-subtle hover:text-danger hover:bg-danger/10 transition-colors"
            aria-label="Remove relationship"
          >
            <Trash2 size={12} />
          </button>
        </div>
      ))}
    </div>
  );
}
