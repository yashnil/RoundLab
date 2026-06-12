"use client";

/** Color-code a slot chip by its strategic function or label keywords. */
function slotColor(slotLabel: string, slotFunction?: string): string {
  const key = `${slotLabel} ${slotFunction ?? ""}`.toLowerCase();
  if (key.includes("legal") || key.includes("doctrinal"))
    return "bg-blue-50 border-blue-200 text-blue-700";
  if (key.includes("moral") || key.includes("philosoph"))
    return "bg-purple-50 border-purple-200 text-purple-700";
  if (key.includes("example") || key.includes("historical"))
    return "bg-green-50 border-green-200 text-green-700";
  if (key.includes("impact") || key.includes("stakes"))
    return "bg-red-50 border-red-200 text-red-700";
  if (key.includes("threshold") || key.includes("objection") || key.includes("limitation"))
    return "bg-amber-50 border-amber-200 text-amber-700";
  return "bg-slate-50 border-slate-200 text-slate-700";
}

export function EvidenceSlotBadge({
  slotLabel,
  slotFunction,
}: {
  slotLabel?: string | null;
  slotFunction?: string;
}) {
  if (!slotLabel) return null;
  return (
    <span
      className={`text-[10px] px-2 py-0.5 rounded-full border font-medium ${slotColor(
        slotLabel,
        slotFunction,
      )}`}
      title={slotFunction ? `Strategic function: ${slotFunction}` : undefined}
    >
      {slotLabel}
    </span>
  );
}

export default EvidenceSlotBadge;
