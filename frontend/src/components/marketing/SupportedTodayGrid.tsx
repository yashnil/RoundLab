import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { SUPPORTED_TODAY, CURRENTLY_EXPLORING } from "@/lib/marketing";

/**
 * Replaces the old "Roadmap (coming soon)" section, which mislabeled shipped features
 * as future work. Every card links to the live surface that delivers it.
 */
export default function SupportedTodayGrid() {
  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {SUPPORTED_TODAY.map((cap) => (
          <Link
            key={cap.title}
            href={cap.href}
            className="group flex flex-col gap-1.5 rounded-xl border border-hairline bg-surface-1 p-4 transition-colors hover:border-hairline-strong"
          >
            <div className="flex items-center justify-between">
              <p className="text-sm font-semibold text-ink">{cap.title}</p>
              <ArrowUpRight
                size={14}
                className="shrink-0 text-ink-faint transition-colors group-hover:text-lav"
                aria-hidden
              />
            </div>
            <p className="text-xs leading-relaxed text-ink-subtle">{cap.body}</p>
          </Link>
        ))}
      </div>
      <p className="text-xs text-ink-faint">
        <span className="font-medium text-ink-subtle">In progress:</span> {CURRENTLY_EXPLORING}
      </p>
    </div>
  );
}
