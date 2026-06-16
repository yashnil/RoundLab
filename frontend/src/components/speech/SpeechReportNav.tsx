"use client";

import { useActiveSection } from "@/hooks/useActiveSection";
import { availableSections, type ReportSectionFlags } from "@/lib/reportSections";
import { cn } from "@/lib/utils";

interface SpeechReportNavProps {
  flags: ReportSectionFlags;
}

/**
 * Sticky, URL-addressable section nav for the speech report. Uses in-page
 * anchors (extending the page's existing #drills anchor) so browser
 * back/forward and deep links keep working, with scroll-spy for the active tab.
 */
export default function SpeechReportNav({ flags }: SpeechReportNavProps) {
  const sections = availableSections(flags);
  const activeId = useActiveSection(sections.map((s) => s.id));

  if (sections.length < 2) return null;

  return (
    <nav
      aria-label="Report sections"
      className="sticky top-14 z-10 -mx-4 mb-1 border-b border-hairline bg-canvas/90 px-4 backdrop-blur-md sm:-mx-6 sm:px-6"
    >
      <ul className="flex gap-1 overflow-x-auto py-2">
        {sections.map((s) => {
          const active = activeId === s.id;
          return (
            <li key={s.id}>
              <a
                href={`#${s.id}`}
                aria-current={active ? "true" : undefined}
                title={s.hint}
                className={cn(
                  "inline-flex items-center whitespace-nowrap rounded-md px-3 py-1.5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50",
                  active
                    ? "bg-surface-2 text-ink"
                    : "text-ink-subtle hover:bg-surface-1 hover:text-ink",
                )}
              >
                {s.label}
              </a>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
