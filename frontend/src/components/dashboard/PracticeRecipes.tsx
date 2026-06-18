"use client";

import Link from "next/link";
import {
  Mic, Swords, Scale, Flag, Wrench, Gauge, Speech, Quote, ChevronRight,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import {
  PRACTICE_RECIPES,
  recipeHref,
  type PracticeRecipe,
  type RecipeIcon,
} from "@/lib/practiceRecipes";

const ICONS: Record<RecipeIcon, LucideIcon> = {
  Mic, Swords, Scale, Flag, Wrench, Gauge, Speech, Quote,
};

function RecipeCard({ recipe }: { recipe: PracticeRecipe }) {
  const Icon = ICONS[recipe.icon];
  return (
    <Link
      href={recipeHref(recipe)}
      className="card-interactive group flex h-full items-start gap-3 rounded-lg border border-hairline bg-surface-1 px-3.5 py-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50"
    >
      <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-hairline bg-surface-2 transition-colors group-hover:border-lav/30 group-hover:bg-lav/5">
        <Icon size={14} className="text-ink-faint transition-colors group-hover:text-lav" aria-hidden />
      </span>
      <span className="flex min-w-0 flex-1 flex-col gap-0.5">
        <span className="flex items-center gap-1.5">
          <span className="truncate text-sm font-medium text-ink">{recipe.label}</span>
          <span className="ml-auto shrink-0 font-mono text-[0.625rem] tabular-nums text-ink-faint">
            {recipe.minutes}
          </span>
        </span>
        <span className="text-xs leading-relaxed text-ink-subtle">{recipe.blurb}</span>
      </span>
      <ChevronRight
        size={13}
        className="mt-0.5 shrink-0 text-ink-faint opacity-0 transition-opacity group-hover:opacity-100"
        aria-hidden
      />
    </Link>
  );
}

/**
 * Practice recipes — one-click training configurations beyond raw speech type.
 * Each opens the real setup flow primed with type, judge lens, and a practice goal.
 */
export default function PracticeRecipes() {
  const full = PRACTICE_RECIPES.filter((r) => r.group === "full");
  const quick = PRACTICE_RECIPES.filter((r) => r.group === "quick");

  return (
    <section aria-label="Practice recipes" className="flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <h2 className="text-heading text-ink">Practice recipes</h2>
        <span className="text-xs text-ink-faint">One-click reps, primed and ready</span>
      </div>

      <div className="flex flex-col gap-2">
        <p className="text-[0.625rem] font-semibold uppercase tracking-[0.08em] text-ink-faint">
          Full speeches
        </p>
        <ul className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {full.map((r) => (
            <li key={r.id}><RecipeCard recipe={r} /></li>
          ))}
        </ul>
      </div>

      <div className="flex flex-col gap-2">
        <p className="text-[0.625rem] font-semibold uppercase tracking-[0.08em] text-ink-faint">
          Quick reps
        </p>
        <ul className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {quick.map((r) => (
            <li key={r.id}><RecipeCard recipe={r} /></li>
          ))}
        </ul>
      </div>
    </section>
  );
}
