import { Skeleton } from "@/components/ui/skeleton";

interface PageSkeletonProps {
  /** Number of body card rows to render. */
  rows?: number;
}

/**
 * Lightweight route loading skeleton. Mirrors the common page geometry
 * (title block + stacked content cards) so navigation feels instant.
 */
export default function PageSkeleton({ rows = 3 }: PageSkeletonProps) {
  return (
    <div
      className="mx-auto flex w-full max-w-5xl flex-col gap-5 px-4 py-8 sm:px-6"
      aria-busy="true"
      aria-live="polite"
    >
      <span className="sr-only">Loading…</span>
      <div className="flex flex-col gap-2">
        <Skeleton className="h-7 w-56 rounded-lg" />
        <Skeleton className="h-4 w-72 rounded-lg" />
      </div>
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-28 w-full rounded-xl" />
      ))}
    </div>
  );
}
