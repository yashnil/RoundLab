"use client";

import { levelToBars } from "@/lib/audioLevel";
import { cn } from "@/lib/utils";

interface RecordingMeterProps {
  /** 0..1 input level. */
  level: number;
  bars?: number;
  className?: string;
}

/**
 * Input-level meter. Decorative (aria-hidden) — it confirms the mic is picking
 * up sound visually; the textual "Recording" status carries the a11y meaning.
 */
export default function RecordingMeter({ level, bars = 14, className }: RecordingMeterProps) {
  const lit = levelToBars(level, bars);
  return (
    <div
      className={cn("flex items-end gap-0.5", className)}
      aria-hidden="true"
      role="presentation"
    >
      {Array.from({ length: bars }).map((_, i) => {
        const on = i < lit;
        const height = 6 + (i / bars) * 18;
        return (
          <span
            key={i}
            className={cn(
              "w-1 rounded-full transition-colors",
              on
                ? i > bars * 0.85
                  ? "bg-danger"
                  : i > bars * 0.6
                    ? "bg-warn"
                    : "bg-ok"
                : "bg-hairline-strong",
            )}
            style={{ height }}
          />
        );
      })}
    </div>
  );
}
