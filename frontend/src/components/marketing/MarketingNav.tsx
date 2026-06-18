"use client";

import { useState } from "react";
import Link from "next/link";
import { Mic, Sun, Moon, Menu } from "lucide-react";
import { APP_NAV_ITEMS } from "@/lib/navItems";
import { MARKETING_NAV_LINKS } from "@/lib/marketing";
import {
  SheetRoot,
  SheetTrigger,
  SheetContent,
  SheetTitle,
  SheetClose,
} from "@/components/ui/sheet";

interface MarketingNavProps {
  isLoggedIn: boolean;
  theme: "dark" | "light";
  onThemeToggle: () => void;
  onSignOut: () => void;
}

export default function MarketingNav({
  isLoggedIn,
  theme,
  onThemeToggle,
  onSignOut,
}: MarketingNavProps) {
  const [open, setOpen] = useState(false);

  return (
    <nav className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-hairline bg-canvas/95 px-5 backdrop-blur-md">
      <Link href="/" className="group flex items-center gap-2">
        <div className="flex h-6 w-6 items-center justify-center rounded-md bg-lav transition-colors group-hover:bg-lav-hi">
          <Mic size={12} className="text-white" aria-hidden />
        </div>
        <span className="text-sm font-semibold tracking-tight text-ink">RoundLab</span>
      </Link>

      {/* Desktop links */}
      {!isLoggedIn ? (
        <div className="hidden items-center gap-5 md:flex">
          {MARKETING_NAV_LINKS.map((item) => (
            <a
              key={item.href}
              href={item.href}
              className="text-sm text-ink-subtle transition-colors hover:text-ink"
            >
              {item.label}
            </a>
          ))}
        </div>
      ) : (
        <div className="hidden items-center gap-4 md:flex">
          {APP_NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="text-sm text-ink-subtle transition-colors hover:text-ink"
            >
              {item.label}
            </Link>
          ))}
        </div>
      )}

      <div className="flex items-center gap-2">
        <button
          onClick={onThemeToggle}
          className="flex h-8 w-8 items-center justify-center rounded-md text-ink-subtle transition-colors hover:bg-surface-2 hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50"
          aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
        >
          {theme === "dark" ? <Sun size={15} /> : <Moon size={15} />}
        </button>

        {/* Desktop CTAs */}
        {!isLoggedIn ? (
          <div className="hidden items-center gap-2 sm:flex">
            <Link
              href="/login"
              className="rounded-md border border-hairline bg-surface-1 px-3 py-1.5 text-sm font-medium text-ink-muted transition-colors hover:border-hairline-strong hover:text-ink"
            >
              Sign in
            </Link>
            <Link
              href="/login"
              className="rounded-md bg-lav px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-lav-hi"
            >
              Start practicing
            </Link>
          </div>
        ) : (
          <div className="hidden items-center gap-2 sm:flex">
            <Link
              href="/session"
              className="rounded-md bg-lav px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-lav-hi"
            >
              New speech
            </Link>
            <button
              onClick={onSignOut}
              className="rounded-md border border-hairline bg-surface-1 px-3 py-1.5 text-sm font-medium text-ink-muted transition-colors hover:border-hairline-strong hover:text-ink"
            >
              Sign out
            </button>
          </div>
        )}

        {/* Mobile menu */}
        <SheetRoot open={open} onOpenChange={setOpen}>
          <SheetTrigger asChild>
            <button
              className="flex h-8 w-8 items-center justify-center rounded-md text-ink-subtle transition-colors hover:bg-surface-2 hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50 md:hidden"
              aria-label="Open menu"
            >
              <Menu size={18} />
            </button>
          </SheetTrigger>
          <SheetContent side="right" className="w-72 px-5 py-5">
            <SheetTitle className="mb-4">Menu</SheetTitle>

            <div className="flex flex-col gap-1">
              {(isLoggedIn ? APP_NAV_ITEMS : MARKETING_NAV_LINKS).map((item) => (
                <SheetClose asChild key={item.href}>
                  {isLoggedIn ? (
                    <Link
                      href={item.href}
                      className="rounded-md px-2 py-2.5 text-sm text-ink-muted transition-colors hover:bg-surface-2 hover:text-ink"
                    >
                      {item.label}
                    </Link>
                  ) : (
                    <a
                      href={item.href}
                      className="rounded-md px-2 py-2.5 text-sm text-ink-muted transition-colors hover:bg-surface-2 hover:text-ink"
                    >
                      {item.label}
                    </a>
                  )}
                </SheetClose>
              ))}
            </div>

            <div className="mt-5 flex flex-col gap-2 border-t border-hairline pt-5">
              {!isLoggedIn ? (
                <>
                  <SheetClose asChild>
                    <Link
                      href="/login"
                      className="rounded-md bg-lav px-3 py-2.5 text-center text-sm font-medium text-white transition-colors hover:bg-lav-hi"
                    >
                      Start practicing
                    </Link>
                  </SheetClose>
                  <SheetClose asChild>
                    <Link
                      href="/login"
                      className="rounded-md border border-hairline px-3 py-2.5 text-center text-sm font-medium text-ink-muted transition-colors hover:text-ink"
                    >
                      Sign in
                    </Link>
                  </SheetClose>
                </>
              ) : (
                <>
                  <SheetClose asChild>
                    <Link
                      href="/session"
                      className="rounded-md bg-lav px-3 py-2.5 text-center text-sm font-medium text-white transition-colors hover:bg-lav-hi"
                    >
                      New speech
                    </Link>
                  </SheetClose>
                  <SheetClose asChild>
                    <button
                      onClick={onSignOut}
                      className="rounded-md border border-hairline px-3 py-2.5 text-center text-sm font-medium text-ink-muted transition-colors hover:text-ink"
                    >
                      Sign out
                    </button>
                  </SheetClose>
                </>
              )}
            </div>
          </SheetContent>
        </SheetRoot>
      </div>
    </nav>
  );
}
