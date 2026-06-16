"use client";

import type { CardIntelligence } from "@/types";

// ── Speech-use labels ──────────────────────────────────────────────────────────

const SPEECH_USE_LABEL: Record<string, string> = {
  contention: "Contention",
  rebuttal: "Rebuttal",
  summary: "Summary",
  final_focus: "Final Focus",
  frontline: "Frontline",
  weighing: "Weighing",
  impact: "Impact / Weighing",
  definition: "Framework",
  crossfire: "Crossfire",
};

/** One labelled coaching mini-card. Renders nothing when the value is empty. */
function PrepCard({
  label,
  value,
  accent = "text-gray-500",
  tint = "border-gray-200 bg-white",
}: {
  label: string;
  value?: string | null;
  accent?: string;
  tint?: string;
}) {
  if (!value || !value.trim()) return null;
  return (
    <div className={`rounded-xl border px-3.5 py-3 ${tint}`}>
      <p className={`text-[9.5px] font-semibold uppercase tracking-[0.06em] ${accent} mb-1`}>{label}</p>
      <p className="text-[12.5px] leading-relaxed text-gray-700">{value}</p>
    </div>
  );
}

/**
 * Structured debate-prep coaching for a card, laid out as a clean two-column
 * grid of mini-cards (single-column on narrow widths). Concrete, card-specific
 * coaching: what it proves, strength/weakness, likely pushback + response,
 * crossfire Q&A, pairing, weighing angle, and which speech to use it in.
 */
export function DebatePrepPanel({
  intelligence,
  className = "",
}: {
  intelligence?: CardIntelligence | null;
  className?: string;
}) {
  if (!intelligence) return null;

  const speechUse = SPEECH_USE_LABEL[intelligence.best_use] ?? "Constructive";

  const hasContent =
    intelligence.why_this_card ||
    intelligence.potential_weakness ||
    intelligence.how_to_answer_weakness ||
    intelligence.opponent_response ||
    intelligence.crossfire_question ||
    intelligence.crossfire_answer ||
    intelligence.best_pairing ||
    intelligence.weighing_angle;

  if (!hasContent) return null;

  return (
    <div className={`flex flex-col gap-3 ${className}`}>
      <div className="flex items-center justify-between">
        <h3 className="text-[13px] font-semibold text-gray-900">Debate prep</h3>
        <span className="text-[10px] font-medium px-2.5 py-0.5 rounded-full bg-gray-900 text-white">
          Best in {speechUse}
        </span>
      </div>

      {/* What this proves — full width, sets up the rest */}
      {intelligence.why_this_card?.trim() && (
        <PrepCard
          label="What this card proves"
          value={intelligence.why_this_card}
          accent="text-gray-500"
          tint="border-gray-200 bg-gray-50/70"
        />
      )}

      {/* Two-column coaching grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
        <PrepCard
          label="Potential weakness"
          value={intelligence.potential_weakness}
          accent="text-amber-700"
          tint="border-amber-200/70 bg-amber-50/40"
        />
        <PrepCard
          label="How to answer it"
          value={intelligence.how_to_answer_weakness}
          accent="text-emerald-700"
          tint="border-emerald-200/70 bg-emerald-50/40"
        />
        <PrepCard
          label="Likely opponent pushback"
          value={intelligence.opponent_response}
          accent="text-rose-700"
          tint="border-rose-200/60 bg-rose-50/40"
        />
        <PrepCard
          label="Weighing angle"
          value={intelligence.weighing_angle}
          accent="text-violet-700"
          tint="border-violet-200/60 bg-violet-50/40"
        />
        <PrepCard
          label="Crossfire question to ask"
          value={intelligence.crossfire_question}
          accent="text-indigo-700"
          tint="border-indigo-200/60 bg-indigo-50/40"
        />
        <PrepCard
          label="Crossfire answer to give"
          value={intelligence.crossfire_answer}
          accent="text-indigo-700"
          tint="border-indigo-200/60 bg-indigo-50/40"
        />
        <PrepCard
          label="Best pairing"
          value={intelligence.best_pairing}
          accent="text-blue-700"
          tint="border-blue-200/60 bg-blue-50/40"
        />
      </div>
    </div>
  );
}

export default DebatePrepPanel;
