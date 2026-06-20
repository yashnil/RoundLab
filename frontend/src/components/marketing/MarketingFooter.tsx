import Link from "next/link";
import { Mic } from "lucide-react";
import type { MarketingLink } from "@/lib/marketing";

interface FooterGroup {
  label: string;
  links: MarketingLink[];
}

/**
 * Footer navigation — only real routes and on-page anchors (no privacy/terms stubs
 * that don't exist yet). Guarded by `marketing.test.ts`.
 */
export const MARKETING_FOOTER: FooterGroup[] = [
  {
    label: "Product",
    links: [
      { label: "Practice loop", href: "#practice" },
      { label: "Flow & ballot", href: "#flow" },
      { label: "Improvement", href: "#improve" },
      { label: "Evidence", href: "#evidence" },
      { label: "For coaches", href: "#team" },
    ],
  },
  {
    label: "Get started",
    links: [
      { label: "Sign in", href: "/login" },
      { label: "See a real report", href: "/demo" },
      { label: "Drills & guides", href: "/learn" },
      { label: "Pilot program", href: "/pilot" },
    ],
  },
];

export default function MarketingFooter() {
  return (
    <footer className="border-t border-hairline bg-surface-1/50">
      <div className="mx-auto flex max-w-6xl flex-col gap-10 px-6 py-12 md:flex-row md:justify-between">
        <div className="flex max-w-xs flex-col gap-3">
          <Link href="/" className="flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded-md bg-lav">
              <Mic size={12} className="text-white" aria-hidden />
            </div>
            <span className="text-sm font-semibold tracking-tight text-ink">RoundLab</span>
          </Link>
          <p className="text-xs leading-relaxed text-ink-subtle">
            An AI flow coach for Public Forum debaters. Turn every practice speech into a
            flow, a ballot, and your next adjustment.
          </p>
        </div>

        <nav aria-label="Footer" className="grid grid-cols-2 gap-8 sm:gap-16">
          {MARKETING_FOOTER.map((group) => (
            <div key={group.label} className="flex flex-col gap-3">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-ink-faint">
                {group.label}
              </p>
              <ul className="flex flex-col gap-2">
                {group.links.map((link) => (
                  <li key={link.label}>
                    <Link
                      href={link.href}
                      className="text-sm text-ink-subtle transition-colors hover:text-ink"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </nav>
      </div>

      <div className="border-t border-hairline">
        <p className="mx-auto max-w-6xl px-6 py-5 text-xs text-ink-faint">
          Built for competitive Public Forum. Coaching, not case generation.
        </p>
      </div>
    </footer>
  );
}
