"use client";

import { type ReactNode } from "react";
import Link from "next/link";
import { Mic, Search } from "lucide-react";
import ThemeToggle from "@/components/shell/ThemeToggle";
import UserMenu from "@/components/shell/UserMenu";
import { openCommandMenu } from "@/components/shell/CommandMenu";

interface ProductHeaderProps {
  /** Optional left-side context (breadcrumbs, page label). */
  leftSlot?: ReactNode;
  /** Optional extra controls before the utility cluster. */
  rightSlot?: ReactNode;
}

export default function ProductHeader({ leftSlot, rightSlot }: ProductHeaderProps) {
  return (
    <header className="sticky top-0 z-20 flex h-14 items-center justify-between gap-3 border-b border-hairline bg-canvas/90 px-4 backdrop-blur-md sm:px-6">
      <div className="flex min-w-0 items-center gap-2">
        {/* Mobile brand (sidebar is hidden on mobile) */}
        <Link
          href="/dashboard"
          className="flex items-center gap-2 md:hidden"
          aria-label="Dissio home"
        >
          <span className="flex h-7 w-7 items-center justify-center rounded-md bg-lav">
            <Mic size={14} className="text-white" />
          </span>
          <span className="text-sm font-semibold tracking-tight text-ink">Dissio</span>
        </Link>
        <div className="hidden min-w-0 md:block">{leftSlot}</div>
      </div>

      <div className="flex items-center gap-1.5">
        {rightSlot}
        <button
          type="button"
          onClick={openCommandMenu}
          className="hidden h-8 items-center gap-2 rounded-md border border-hairline bg-surface-1 px-2.5 text-ink-subtle transition-colors hover:text-ink hover:border-hairline-strong focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50 lg:flex"
          aria-label="Open command menu"
        >
          <Search size={14} aria-hidden="true" />
          <span className="text-xs">Search</span>
          <kbd className="rounded border border-hairline px-1.5 py-0.5 font-mono text-xs text-ink-subtle">
            ⌘K
          </kbd>
        </button>
        <ThemeToggle />
        <UserMenu />
      </div>
    </header>
  );
}
