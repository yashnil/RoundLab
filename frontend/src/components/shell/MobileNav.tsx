"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Mic, BookMarked, Menu, Search } from "lucide-react";
import { cn } from "@/lib/utils";
import { APP_NAV_GROUPS, isNavItemActive } from "@/lib/navItems";
import {
  SheetRoot,
  SheetTrigger,
  SheetContent,
  SheetTitle,
  SheetClose,
} from "@/components/ui/sheet";
import { SeparatorRoot } from "@/components/ui/separator";
import ThemeToggle from "@/components/shell/ThemeToggle";
import { openCommandMenu } from "@/components/shell/CommandMenu";

const PRIMARY = [
  { href: "/dashboard", label: "Home", icon: LayoutDashboard, match: ["/dashboard"] },
  { href: "/session", label: "Practice", icon: Mic, match: ["/session", "/speech"] },
  { href: "/evidence", label: "Evidence", icon: BookMarked, match: ["/evidence"] },
];

export default function MobileNav() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-30 flex h-[calc(3.5rem+env(safe-area-inset-bottom))] items-stretch border-t border-sidebar-border bg-sidebar/95 pb-[env(safe-area-inset-bottom)] backdrop-blur-md md:hidden"
      aria-label="Primary"
    >
      {PRIMARY.map((item) => {
        const active = isNavItemActive(item, pathname);
        const Icon = item.icon;
        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={active ? "page" : undefined}
            className={cn(
              "flex flex-1 flex-col items-center justify-center gap-0.5 text-[0.625rem] font-medium transition-colors",
              active ? "text-lav-hi" : "text-ink-subtle hover:text-ink",
            )}
          >
            <Icon size={20} aria-hidden="true" />
            <span>{item.label}</span>
          </Link>
        );
      })}

      <SheetRoot open={open} onOpenChange={setOpen}>
        <SheetTrigger asChild>
          <button
            type="button"
            className="flex flex-1 flex-col items-center justify-center gap-0.5 text-[0.625rem] font-medium text-ink-subtle transition-colors hover:text-ink"
            aria-label="More navigation"
          >
            <Menu size={20} aria-hidden="true" />
            <span>More</span>
          </button>
        </SheetTrigger>
        <SheetContent side="right" className="w-72">
          <div className="flex h-14 items-center px-4">
            <SheetTitle>Navigate</SheetTitle>
          </div>
          <SeparatorRoot />
          <div className="flex-1 overflow-y-auto px-3 py-3">
            <button
              type="button"
              onClick={() => {
                setOpen(false);
                openCommandMenu();
              }}
              className="mb-3 flex w-full items-center gap-2 rounded-md border border-hairline bg-surface-1 px-3 py-2 text-sm text-ink-subtle"
            >
              <Search size={15} aria-hidden="true" />
              Search actions…
            </button>
            {APP_NAV_GROUPS.map((group) => (
              <div key={group.id} className="mb-4 last:mb-0">
                {group.label && (
                  <p className="px-2 pb-1.5 text-[0.625rem] font-semibold uppercase tracking-[0.08em] text-ink-faint">
                    {group.label}
                  </p>
                )}
                <ul className="flex flex-col gap-0.5">
                  {group.items.map((item) => {
                    const active = isNavItemActive(item, pathname);
                    const Icon = item.icon;
                    return (
                      <li key={item.href}>
                        <SheetClose asChild>
                          <Link
                            href={item.href}
                            aria-current={active ? "page" : undefined}
                            className={cn(
                              "flex items-center gap-2.5 rounded-md px-2.5 py-2.5 text-sm font-medium transition-colors",
                              active
                                ? "bg-surface-2 text-ink"
                                : "text-ink-subtle hover:bg-surface-1 hover:text-ink",
                            )}
                          >
                            <Icon size={18} aria-hidden="true" />
                            {item.label}
                          </Link>
                        </SheetClose>
                      </li>
                    );
                  })}
                </ul>
              </div>
            ))}
          </div>
          <SeparatorRoot />
          <div className="flex items-center justify-between px-4 py-3">
            <span className="text-xs text-ink-subtle">Appearance</span>
            <ThemeToggle />
          </div>
        </SheetContent>
      </SheetRoot>
    </nav>
  );
}
