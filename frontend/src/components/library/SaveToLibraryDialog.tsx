"use client";

import { useState, useEffect } from "react";
import { X, AlertTriangle, BookmarkPlus } from "lucide-react";
import { apiFetch } from "@/lib/api";
import type { CardDraft } from "@/types";
import type { Resolution, Argument, Side } from "@/types/library";

interface SaveToLibraryDialogProps {
  card: CardDraft;
  userId: string;
  onSaved: (cardId: string) => void;
  onClose: () => void;
}

const SIDE_LABELS: Record<Side, string> = {
  pro: "Pro (Affirmative)",
  con: "Con (Negative)",
  neutral: "Neutral / General",
};

const ROLE_OPTIONS = [
  { value: "direct_support", label: "Direct support" },
  { value: "mechanism_support", label: "Mechanism / link" },
  { value: "impact_support", label: "Impact evidence" },
  { value: "example_support", label: "Example / case study" },
  { value: "definition_support", label: "Definition" },
  { value: "authority_support", label: "Authority / expert opinion" },
  { value: "counter_evidence", label: "Counter-evidence / response" },
];

export function SaveToLibraryDialog({
  card,
  userId,
  onSaved,
  onClose,
}: SaveToLibraryDialogProps) {
  const [resolutions, setResolutions] = useState<Resolution[]>([]);
  const [arguments_, setArguments] = useState<Argument[]>([]);
  const [selectedResolutionId, setSelectedResolutionId] = useState("");
  const [selectedArgumentId, setSelectedArgumentId] = useState("");
  const [newArgumentTitle, setNewArgumentTitle] = useState("");
  const [side, setSide] = useState<Side>("pro");
  const [evidenceRole, setEvidenceRole] = useState("direct_support");
  const [notes, setNotes] = useState("");
  const [tags, setTags] = useState("");
  const [unsupportedOverride, setUnsupportedOverride] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const verdict: string | undefined = card.claim_supported === false ? "unsupported" : undefined;
  const requiresOverride = verdict === "unsupported";

  useEffect(() => {
    apiFetch(`/library/resolutions?user_id=${userId}`)
      .then((data) => setResolutions(data as Resolution[]))
      .catch(() => {});
  }, [userId]);

  useEffect(() => {
    if (!selectedResolutionId) {
      setArguments([]);
      return;
    }
    apiFetch(
      `/library/arguments?user_id=${userId}&resolution_id=${selectedResolutionId}&side=${side}`,
    )
      .then((data) => setArguments(data as Argument[]))
      .catch(() => {});
  }, [userId, selectedResolutionId, side]);

  async function handleSave() {
    if (requiresOverride && !unsupportedOverride) {
      setError(
        "This card has a weak or contradicted support verdict. Check the box to save anyway.",
      );
      return;
    }
    setSaving(true);
    setError(null);
    try {
      let argumentId = selectedArgumentId;

      // Inline argument creation
      if (!argumentId && newArgumentTitle.trim()) {
        const newArg = await apiFetch("/library/arguments", {
          method: "POST",
          body: JSON.stringify({
            user_id: userId,
            resolution_id: selectedResolutionId || undefined,
            side,
            title: newArgumentTitle.trim(),
          }),
        }) as Argument;
        argumentId = newArg.id;
      }

      const tagList = tags
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);

      const payload = {
        user_id: userId,
        card_id: card.saved_card_id || card.id,
        resolution_id: selectedResolutionId || undefined,
        argument_id: argumentId || undefined,
        side,
        evidence_role: evidenceRole,
        user_notes: notes || undefined,
        tags: tagList,
        support_verdict: verdict,
        unsupported_save_override: unsupportedOverride,
        source_url: card.url || undefined,
      };

      const result = await apiFetch("/library/cards/save", {
        method: "POST",
        body: JSON.stringify(payload),
      }) as { card_id: string };

      onSaved(result.card_id);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Save failed. Please try again.";
      setError(msg);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Save card to library"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="w-full max-w-lg bg-surface-1 rounded-xl shadow-xl border border-hairline overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-hairline">
          <div className="flex items-center gap-2">
            <BookmarkPlus size={18} className="text-lav" />
            <h2 className="text-[15px] font-semibold text-ink">Save to Library</h2>
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-1 text-ink-subtle hover:bg-surface-muted transition-colors"
            aria-label="Close"
          >
            <X size={16} />
          </button>
        </div>

        {/* Card preview */}
        <div className="px-5 py-3 border-b border-hairline bg-surface-muted">
          <p className="text-[12px] font-semibold text-ink truncate">
            {card.tag || card.generated_tag ? "(generated tag)" : "Untitled card"}
          </p>
          <p className="text-[11px] text-ink-subtle truncate">
            {card.cite || card.short_cite || card.url || "No source"}
          </p>
        </div>

        {/* Form */}
        <div className="px-5 py-4 space-y-3 max-h-[60vh] overflow-y-auto">
          {requiresOverride && (
            <div className="flex items-start gap-2 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2.5">
              <AlertTriangle size={15} className="text-amber-600 mt-0.5 shrink-0" />
              <div className="text-[11px] text-amber-800">
                <p className="font-semibold">Weak support verdict</p>
                <p>This card is marked {verdict}. Saving it as affirmative support may mislead your case.</p>
              </div>
            </div>
          )}

          {/* Resolution */}
          <div>
            <label className="block text-[11px] font-medium text-ink-muted mb-1">
              Resolution <span className="text-ink-faint">(optional)</span>
            </label>
            <select
              value={selectedResolutionId}
              onChange={(e) => setSelectedResolutionId(e.target.value)}
              className="w-full text-[13px] border border-border rounded-lg px-2.5 py-1.5 bg-surface-1 text-ink focus:outline-none focus:ring-2 focus:ring-lav/40"
            >
              <option value="">No resolution</option>
              {resolutions.map((r) => (
                <option key={r.id} value={r.id}>{r.title}</option>
              ))}
            </select>
          </div>

          {/* Side */}
          <div>
            <label className="block text-[11px] font-medium text-ink-muted mb-1">Side</label>
            <div className="flex gap-2">
              {(["pro", "con", "neutral"] as Side[]).map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => setSide(s)}
                  className={`flex-1 text-[11px] py-1.5 rounded-lg border transition-colors ${
                    side === s
                      ? "bg-lav/10 border-lav/30 text-lav font-medium"
                      : "border-border text-ink-subtle hover:bg-surface-muted"
                  }`}
                >
                  {SIDE_LABELS[s]}
                </button>
              ))}
            </div>
          </div>

          {/* Argument */}
          <div>
            <label className="block text-[11px] font-medium text-ink-muted mb-1">
              Argument <span className="text-ink-faint">(optional)</span>
            </label>
            {arguments_.length > 0 && (
              <select
                value={selectedArgumentId}
                onChange={(e) => setSelectedArgumentId(e.target.value)}
                className="w-full text-[13px] border border-border rounded-lg px-2.5 py-1.5 bg-surface-1 text-ink focus:outline-none focus:ring-2 focus:ring-lav/40 mb-1.5"
              >
                <option value="">Select or create below</option>
                {arguments_.map((a) => (
                  <option key={a.id} value={a.id}>{a.title}</option>
                ))}
              </select>
            )}
            {!selectedArgumentId && (
              <input
                value={newArgumentTitle}
                onChange={(e) => setNewArgumentTitle(e.target.value)}
                placeholder="New argument title (leave blank to skip)"
                className="w-full text-[13px] border border-border rounded-lg px-2.5 py-1.5 bg-surface-1 text-ink placeholder:text-ink-faint focus:outline-none focus:ring-2 focus:ring-lav/40"
              />
            )}
          </div>

          {/* Evidence role */}
          <div>
            <label className="block text-[11px] font-medium text-ink-muted mb-1">Evidence role</label>
            <select
              value={evidenceRole}
              onChange={(e) => setEvidenceRole(e.target.value)}
              className="w-full text-[13px] border border-border rounded-lg px-2.5 py-1.5 bg-surface-1 text-ink focus:outline-none focus:ring-2 focus:ring-lav/40"
            >
              {ROLE_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>

          {/* Tags */}
          <div>
            <label className="block text-[11px] font-medium text-ink-muted mb-1">
              Tags <span className="text-ink-faint">(comma-separated)</span>
            </label>
            <input
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="e.g. uniqueness, economy, link"
              className="w-full text-[13px] border border-border rounded-lg px-2.5 py-1.5 bg-surface-1 text-ink placeholder:text-ink-faint focus:outline-none focus:ring-2 focus:ring-lav/40"
            />
          </div>

          {/* Notes */}
          <div>
            <label className="block text-[11px] font-medium text-ink-muted mb-1">
              Notes <span className="text-ink-faint">(optional)</span>
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Coach notes, context, usage tips..."
              rows={2}
              className="w-full text-[13px] border border-border rounded-lg px-2.5 py-1.5 bg-surface-1 text-ink placeholder:text-ink-faint focus:outline-none focus:ring-2 focus:ring-lav/40 resize-none"
            />
          </div>

          {/* Override checkbox */}
          {requiresOverride && (
            <label className="flex items-center gap-2 text-[11px] text-ink cursor-pointer">
              <input
                type="checkbox"
                checked={unsupportedOverride}
                onChange={(e) => setUnsupportedOverride(e.target.checked)}
                className="rounded border-border"
              />
              I understand this card has weak/contradicted support — save anyway
            </label>
          )}

          {error && (
            <p className="text-[11px] text-danger" role="alert">{error}</p>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 px-5 py-3 border-t border-hairline bg-surface-muted">
          <button
            onClick={onClose}
            className="text-[12px] px-3 py-1.5 rounded-lg border border-border text-ink-subtle hover:bg-surface-hover transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="text-[12px] px-4 py-1.5 rounded-lg bg-ink text-canvas hover:bg-ink/80 transition-colors font-medium disabled:opacity-50"
          >
            {saving ? "Saving…" : "Save to Library"}
          </button>
        </div>
      </div>
    </div>
  );
}
