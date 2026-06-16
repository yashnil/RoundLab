"use client";

import Link from "next/link";
import { Mic } from "lucide-react";
import { QUICK_START_OPTIONS, quickStartHref } from "@/lib/dashboardHelpers";

/**
 * Fast entry into a practice by speech type. Deep-links into /session with the
 * type preset so the recorder opens with the right time guidance.
 */
export default function QuickStartRow() {
  return (
    <section aria-label="Quick start a practice" className="flex flex-col gap-2.5">
      <div className="flex items-center gap-2">
        <Mic size={14} className="text-ink-subtle" aria-hidden="true" />
        <h2 className="text-heading text-ink">Quick start</h2>
        <span className="text-xs text-ink-faint">Jump straight into a speech type</span>
      </div>
      <ul className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
        {QUICK_START_OPTIONS.map((opt) => (
          <li key={opt.type}>
            <Link
              href={quickStartHref(opt.type)}
              className="card-interactive flex h-full flex-col gap-1 rounded-lg border border-hairline bg-surface-1 px-3.5 py-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50"
            >
              <span className="text-sm font-medium text-ink">{opt.label}</span>
              <span className="font-mono text-[0.6875rem] tabular-nums text-ink-faint">
                {opt.minutes}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
