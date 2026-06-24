"use client";

import { useState, useEffect } from "react";
import { Plus, Trash2, Check } from "lucide-react";
import { apiFetch } from "@/lib/api";
import type { Frontline, FrontlineResponse, ResponseType } from "@/types/library";

const RESPONSE_TYPE_LABELS: Record<ResponseType, string> = {
  no_link: "No Link",
  link_defense: "Link Defense",
  impact_defense: "Impact Defense",
  uniqueness_takeout: "Uniqueness Takeout",
  turn: "Turn",
  counterplan: "Counterplan",
  mitigation: "Mitigation",
  non_unique: "Non-Unique",
  weighing: "Weighing",
  evidence_indictment: "Evidence Indictment",
  source_challenge: "Source Challenge",
};

const SPEECH_OPTIONS = ["rebuttal", "summary", "final_focus"];

interface FrontlineBuilderProps {
  frontline: Frontline;
  userId: string;
}

export function FrontlineBuilder({ frontline, userId }: FrontlineBuilderProps) {
  const [responses, setResponses] = useState<FrontlineResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [newType, setNewType] = useState<ResponseType>("no_link");
  const [newClaim, setNewClaim] = useState("");
  const [newExplanation, setNewExplanation] = useState("");
  const [newWording, setNewWording] = useState("");
  const [newPriority, setNewPriority] = useState(1);
  const [newSpeech, setNewSpeech] = useState<string[]>(["rebuttal", "summary", "final_focus"]);
  const [isAnalytical, setIsAnalytical] = useState(false);
  const [saving, setSaving] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const data = await apiFetch(
        `/library/frontlines/${frontline.id}/responses?user_id=${userId}`,
      ) as FrontlineResponse[];
      setResponses(data.sort((a, b) => a.position - b.position));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [frontline.id, userId]);

  async function addResponse() {
    if (!newClaim.trim()) return;
    setSaving(true);
    try {
      await apiFetch(`/library/frontlines/${frontline.id}/responses`, {
        method: "POST",
        body: JSON.stringify({
          frontline_id: frontline.id,
          user_id: userId,
          response_type: newType,
          response_claim: newClaim.trim(),
          explanation: newExplanation || undefined,
          wording_for_speech: newWording || undefined,
          priority: newPriority,
          speech_suitability: newSpeech,
          is_analytical: isAnalytical,
          position: responses.length,
        }),
      });
      setNewClaim("");
      setNewExplanation("");
      setNewWording("");
      setIsAnalytical(false);
      setShowForm(false);
      await load();
    } catch {
      // non-fatal
    } finally {
      setSaving(false);
    }
  }

  async function deleteResponse(id: string) {
    try {
      await apiFetch(`/library/responses/${id}?user_id=${userId}`, { method: "DELETE" });
      setResponses((prev) => prev.filter((r) => r.id !== id));
    } catch {}
  }

  const priorityColor = (p: number) =>
    p === 1 ? "text-ok" : p === 2 ? "text-amber-600" : "text-ink-subtle";

  if (loading) {
    return <div className="text-[12px] text-ink-subtle py-4">Loading frontline…</div>;
  }

  return (
    <div className="space-y-4">
      {/* Opponent claim summary */}
      <div className="rounded-xl border border-border bg-surface-muted px-4 py-3 space-y-1.5">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-subtle">
          Opponent
        </p>
        {frontline.opponent_claim && (
          <p className="text-[13px] font-semibold text-ink">{frontline.opponent_claim}</p>
        )}
        {frontline.opponent_warrant && (
          <p className="text-[12px] text-ink-subtle">{frontline.opponent_warrant}</p>
        )}
        {frontline.opponent_impact && (
          <p className="text-[12px] text-ink-subtle">Impact: {frontline.opponent_impact}</p>
        )}
      </div>

      {/* Responses */}
      <div className="flex items-center justify-between">
        <p className="text-[13px] font-semibold text-ink">
          Responses ({responses.length})
        </p>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-1 text-[12px] text-lav hover:underline"
        >
          <Plus size={13} />
          Add Response
        </button>
      </div>

      {showForm && (
        <div className="rounded-xl border border-border bg-surface-muted p-4 space-y-3">
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-[10px] text-ink-muted mb-1">Type</label>
              <select
                value={newType}
                onChange={(e) => setNewType(e.target.value as ResponseType)}
                className="w-full text-[12px] border border-border rounded-md px-2 py-1.5 bg-surface-1 text-ink"
              >
                {(Object.entries(RESPONSE_TYPE_LABELS) as [ResponseType, string][]).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-[10px] text-ink-muted mb-1">Priority (1=best)</label>
              <input
                type="number"
                value={newPriority}
                min={1}
                onChange={(e) => setNewPriority(parseInt(e.target.value) || 1)}
                className="w-full text-[12px] border border-border rounded-md px-2 py-1.5 bg-surface-1 text-ink"
              />
            </div>
          </div>
          <div>
            <label className="block text-[10px] text-ink-muted mb-1">Response claim *</label>
            <input
              value={newClaim}
              onChange={(e) => setNewClaim(e.target.value)}
              placeholder="Their argument fails because…"
              className="w-full text-[12px] border border-border rounded-md px-2.5 py-1.5 bg-surface-1 text-ink"
            />
          </div>
          <div>
            <label className="block text-[10px] text-ink-muted mb-1">Explanation</label>
            <textarea
              value={newExplanation}
              onChange={(e) => setNewExplanation(e.target.value)}
              placeholder="Why this response works…"
              rows={2}
              className="w-full text-[12px] border border-border rounded-md px-2.5 py-1.5 bg-surface-1 text-ink resize-none"
            />
          </div>
          <div>
            <label className="block text-[10px] text-ink-muted mb-1">Read-aloud wording (optional)</label>
            <input
              value={newWording}
              onChange={(e) => setNewWording(e.target.value)}
              placeholder="Short, read-aloud version for rounds"
              className="w-full text-[12px] border border-border rounded-md px-2.5 py-1.5 bg-surface-1 text-ink"
            />
          </div>
          <div>
            <label className="block text-[10px] text-ink-muted mb-1">Speech suitability</label>
            <div className="flex gap-2">
              {SPEECH_OPTIONS.map((sp) => (
                <label key={sp} className="flex items-center gap-1 text-[11px] text-ink cursor-pointer">
                  <input
                    type="checkbox"
                    checked={newSpeech.includes(sp)}
                    onChange={(e) =>
                      setNewSpeech((prev) =>
                        e.target.checked ? [...prev, sp] : prev.filter((x) => x !== sp),
                      )
                    }
                  />
                  {sp}
                </label>
              ))}
            </div>
          </div>
          <label className="flex items-center gap-2 text-[11px] text-ink cursor-pointer">
            <input
              type="checkbox"
              checked={isAnalytical}
              onChange={(e) => setIsAnalytical(e.target.checked)}
            />
            Analytical response (no evidence card required)
          </label>
          <div className="flex gap-2">
            <button
              onClick={addResponse}
              disabled={saving || !newClaim.trim()}
              className="flex-1 text-[12px] py-1.5 rounded-md bg-ink text-canvas disabled:opacity-40"
            >
              {saving ? "Adding…" : "Add Response"}
            </button>
            <button
              onClick={() => setShowForm(false)}
              className="text-[12px] px-3 py-1.5 rounded-md border border-border text-ink-subtle"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {responses.length === 0 && !showForm && (
        <p className="py-6 text-center text-[12px] text-ink-subtle">
          No responses yet. Add your first response above.
        </p>
      )}

      {responses.map((r) => (
        <div
          key={r.id}
          className="rounded-xl border border-border overflow-hidden"
        >
          <div className="flex items-start gap-3 px-4 py-3">
            <div className="flex-1 min-w-0 space-y-0.5">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface-muted border border-border text-ink-subtle">
                  {RESPONSE_TYPE_LABELS[r.response_type]}
                </span>
                <span className={`text-[10px] font-semibold ${priorityColor(r.priority)}`}>
                  P{r.priority}
                </span>
                {r.is_analytical && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface-muted border border-border text-ink-subtle">
                    Analytical
                  </span>
                )}
                <span className="text-[10px] text-ink-faint ml-auto">
                  {r.speech_suitability.join(", ")}
                </span>
              </div>
              <p className="text-[13px] font-semibold text-ink leading-snug">{r.response_claim}</p>
              {r.explanation && (
                <p className="text-[11px] text-ink-subtle">{r.explanation}</p>
              )}
              {r.wording_for_speech && (
                <p className="text-[11px] text-ink-subtle italic">
                  Read-aloud: &ldquo;{r.wording_for_speech}&rdquo;
                </p>
              )}
            </div>
            <button
              onClick={() => deleteResponse(r.id)}
              className="p-1 rounded text-ink-faint hover:text-danger hover:bg-danger/10 transition-colors shrink-0"
              aria-label="Delete response"
            >
              <Trash2 size={14} />
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
