"use client";

import Link from "next/link";
import {
  RotateCcw,
  Loader,
  Target,
  Repeat,
  Mic,
  TrendingUp,
  ArrowRight,
  type LucideIcon,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import type { NextAction, NextActionIcon } from "@/lib/dashboardHelpers";

const ICONS: Record<NextActionIcon, LucideIcon> = {
  RotateCcw,
  Loader,
  Target,
  Repeat,
  Mic,
  TrendingUp,
};

/**
 * The single most prominent thing on the dashboard: one context-aware next
 * action chosen from the student's real data. Outweighs the metric cards.
 */
export default function NextActionPanel({ action }: { action: NextAction }) {
  const Icon = ICONS[action.icon];
  const spin = action.icon === "Loader";

  return (
    <section
      aria-label="Your next step"
      className="surface-mission beam-top relative overflow-hidden rounded-xl p-5 sm:p-6"
    >
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex min-w-0 items-start gap-4">
          <span className="mt-0.5 flex h-11 w-11 shrink-0 items-center justify-center rounded-lg border border-lav/30 bg-lav/10 text-lav-hi">
            <Icon size={20} className={spin ? "animate-spin" : undefined} aria-hidden="true" />
          </span>
          <div className="min-w-0">
            <p className="text-[0.6875rem] font-semibold uppercase tracking-[0.08em] text-lav-hi">
              {action.eyebrow}
            </p>
            <h2 className="mt-0.5 text-title font-semibold text-ink">{action.title}</h2>
            <p className="mt-1.5 max-w-xl text-sm leading-relaxed text-ink-subtle">
              {action.description}
            </p>
          </div>
        </div>
        <div className="flex shrink-0 flex-col gap-2 sm:items-end">
          <Button asChild size="lg" className="glow-lav">
            <Link href={action.href}>
              {action.ctaLabel}
              <ArrowRight size={16} aria-hidden="true" />
            </Link>
          </Button>
          {action.secondary && (
            <Button asChild variant="ghost" size="sm">
              <Link href={action.secondary.href}>{action.secondary.label}</Link>
            </Button>
          )}
        </div>
      </div>
    </section>
  );
}
