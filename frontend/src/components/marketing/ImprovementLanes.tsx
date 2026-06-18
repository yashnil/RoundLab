import { Plus } from "lucide-react";

/**
 * Improvement section visual — two parallel lanes (Original vs Re-record) on the SAME
 * speech, annotating exactly what new debate behavior the re-record added. Distinct from
 * the hero sample on purpose: this is a Summary speech, contention C2.
 *
 * "Coaching, not cheating": improvement is shown as added behavior, not a higher number.
 */

const ADDED = ["Warrant", "Weighing", "Extension"];

function Lane({
  kind,
  label,
  speaker,
  quote,
}: {
  kind: "before" | "after";
  label: string;
  speaker: string;
  quote: string;
}) {
  const isAfter = kind === "after";
  return (
    <div
      className={
        "flex flex-1 flex-col gap-3 rounded-lg border p-4 " +
        (isAfter
          ? "border-lav/30 bg-lav/[0.06]"
          : "border-hairline bg-surface-2")
      }
    >
      <div className="flex items-center justify-between">
        <span
          className={
            "text-[11px] font-semibold uppercase tracking-wider " +
            (isAfter ? "text-lav" : "text-ink-faint")
          }
        >
          {label}
        </span>
        <span className="font-mono text-[10px] text-ink-faint">{speaker}</span>
      </div>
      <p
        className={
          "text-sm leading-relaxed " + (isAfter ? "text-ink" : "text-ink-subtle")
        }
      >
        &ldquo;{quote}&rdquo;
      </p>
      {isAfter && (
        <div className="mt-auto flex flex-wrap gap-1.5 border-t border-lav/15 pt-3">
          {ADDED.map((a) => (
            <span
              key={a}
              className="inline-flex items-center gap-1 rounded-full border border-lav/25 bg-lav/10 px-2 py-0.5 text-[10px] font-medium text-lav"
            >
              <Plus size={9} aria-hidden /> {a}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

export default function ImprovementLanes() {
  return (
    <div className="rounded-2xl border border-hairline bg-surface-1 p-5">
      <div className="mb-4 flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-heading text-ink">Same speech, second attempt</p>
          <p className="mt-0.5 text-xs text-ink-subtle">
            Summary · C2 link — what the re-record actually added.
          </p>
        </div>
        <span className="hidden text-[10px] text-ink-faint sm:block">
          Original ↔ Re-record
        </span>
      </div>

      <div className="flex flex-col gap-3 md:flex-row md:items-stretch">
        <Lane
          kind="before"
          label="Original"
          speaker="Summary · 0:48"
          quote="Extend our second contention — the economic argument still stands going into Final Focus."
        />
        <Lane
          kind="after"
          label="Re-record"
          speaker="Summary · 0:51"
          quote="Extend C2: they conceded the supply-chain warrant in crossfire, so the jobs impact is uncontested — and it outweighs on timeframe because it hits before their long-term harm."
        />
      </div>

      <div className="mt-4 flex items-start gap-2 rounded-lg border border-ok/20 bg-ok/5 px-3 py-2.5">
        <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-ok" aria-hidden />
        <p className="text-xs leading-relaxed text-ink-muted">
          <span className="font-semibold text-ink">What changed:</span> the extension now names
          the conceded warrant and weighs on timeframe. Still missing a magnitude comparison —
          that&apos;s the next drill.
        </p>
      </div>
    </div>
  );
}
