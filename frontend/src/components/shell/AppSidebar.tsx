"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Mic, PanelLeftClose, PanelLeftOpen, Plus, Search } from "lucide-react";
import { cn } from "@/lib/utils";
import { APP_NAV_GROUPS, isNavItemActive } from "@/lib/navItems";
import { usePersistentToggle } from "@/hooks/usePersistentToggle";
import {
  TooltipRoot,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip";
import { openCommandMenu } from "@/components/shell/CommandMenu";

const LOOP_LABELS = ["Practice", "Analyze", "Drill", "Improve"] as const;

export default function AppSidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = usePersistentToggle(
    "dissio-sidebar-collapsed",
  );

  return (
    <aside
      data-collapsed={collapsed}
      className={cn(
        "sticky top-0 z-30 hidden h-screen shrink-0 flex-col border-r border-sidebar-border bg-sidebar md:flex",
        "transition-[width] duration-200 ease-out",
        collapsed ? "w-16" : "w-60",
      )}
      aria-label="Primary navigation"
    >
      {/* Brand */}
      <div className="flex h-14 shrink-0 items-center gap-2 px-3">
        <Link
          href="/dashboard"
          className="group flex items-center gap-2.5 rounded-md px-1 py-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50"
        >
          <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-lav transition-colors group-hover:bg-lav-hi">
            <Mic size={14} className="text-white" aria-hidden="true" />
          </span>
          {!collapsed && (
            <span className="text-sm font-semibold tracking-tight text-ink">
              Dissio
            </span>
          )}
        </Link>
      </div>

      {/* Primary CTA */}
      <div className="shrink-0 px-3 pb-2">
        <NavCTA collapsed={collapsed} />
      </div>

      {/* Command launcher */}
      <div className="shrink-0 px-3 pb-3">
        <button
          type="button"
          onClick={openCommandMenu}
          className={cn(
            "flex w-full items-center rounded-md border border-hairline bg-surface-1 text-ink-subtle transition-colors",
            "hover:border-hairline-strong hover:text-ink",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50",
            collapsed ? "h-9 justify-center" : "h-9 gap-2 px-2.5",
          )}
          aria-label="Open command menu"
        >
          <Search size={14} aria-hidden="true" />
          {!collapsed && (
            <>
              <span className="text-xs">Search…</span>
              <kbd className="ml-auto rounded border border-hairline px-1.5 py-0.5 font-mono text-xs text-ink-subtle">
                ⌘K
              </kbd>
            </>
          )}
        </button>
      </div>

      {/* Nav groups */}
      <nav className="flex-1 overflow-y-auto px-3" aria-label="App sections">
        {APP_NAV_GROUPS.map((group) => (
          <div key={group.id} className="mb-5 last:mb-0">
            {group.label && !collapsed && (
              <p className="text-eyebrow px-2 pb-1.5 text-ink-subtle">
                {group.label}
              </p>
            )}
            <ul className="flex flex-col gap-0.5" role="list">
              {group.items.map((item) => {
                const active = isNavItemActive(item, pathname);
                const Icon = item.icon;
                const link = (
                  <Link
                    href={item.href}
                    aria-current={active ? "page" : undefined}
                    className={cn(
                      "group flex items-center rounded-md text-sm font-medium transition-colors",
                      "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50",
                      collapsed ? "h-9 w-9 justify-center" : "h-9 gap-2.5 px-2.5",
                      active
                        ? "bg-lav/8 text-ink"
                        : "text-ink-subtle hover:bg-surface-1 hover:text-ink",
                    )}
                  >
                    <span className="relative flex shrink-0 items-center">
                      {active && (
                        <span
                          className="absolute -left-2.5 h-4 w-0.5 rounded-full bg-lav"
                          aria-hidden="true"
                        />
                      )}
                      <Icon size={17} aria-hidden="true" />
                    </span>
                    {!collapsed && (
                      <span className="truncate">{item.label}</span>
                    )}
                  </Link>
                );

                return (
                  <li key={item.href}>
                    {collapsed ? (
                      <TooltipRoot>
                        <TooltipTrigger asChild>{link}</TooltipTrigger>
                        <TooltipContent side="right">
                          {item.label}
                          {item.hint && (
                            <span className="block text-ink-subtle">
                              {item.hint}
                            </span>
                          )}
                        </TooltipContent>
                      </TooltipRoot>
                    ) : (
                      link
                    )}
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      {/* Loop strip — Practice › Analyze › Drill › Improve */}
      <div
        className="shrink-0 border-t border-sidebar-border px-3 py-3"
        aria-hidden="true"
      >
        {collapsed ? (
          <div className="flex flex-col items-center gap-1.5">
            {LOOP_LABELS.map((_, i) => (
              <span key={i} className="h-1 w-1 rounded-full bg-hairline-strong" />
            ))}
          </div>
        ) : (
          <p className="section-stamp text-ink-subtle">{LOOP_LABELS.join(" › ")}</p>
        )}
      </div>

      {/* Collapse toggle */}
      <div className="shrink-0 border-t border-sidebar-border p-3">
        <button
          type="button"
          onClick={() => setCollapsed(!collapsed)}
          className={cn(
            "flex w-full items-center rounded-md text-ink-subtle transition-colors",
            "hover:bg-surface-1 hover:text-ink",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50",
            collapsed ? "h-9 justify-center" : "h-9 gap-2 px-2.5",
          )}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          aria-expanded={!collapsed}
        >
          {collapsed ? (
            <PanelLeftOpen size={17} aria-hidden="true" />
          ) : (
            <PanelLeftClose size={17} aria-hidden="true" />
          )}
          {!collapsed && <span className="text-xs">Collapse</span>}
        </button>
      </div>
    </aside>
  );
}

function NavCTA({ collapsed }: { collapsed: boolean }) {
  const cta = (
    <Link
      href="/session"
      className={cn(
        "flex items-center rounded-md bg-primary text-primary-foreground transition-colors",
        "hover:bg-primary/85",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50",
        collapsed
          ? "h-9 w-9 justify-center"
          : "h-9 gap-2 px-3 text-sm font-medium",
      )}
      aria-label="Start a new practice round"
    >
      <Plus size={16} aria-hidden="true" />
      {!collapsed && <span>New Round</span>}
    </Link>
  );
  if (!collapsed) return cta;
  return (
    <TooltipRoot>
      <TooltipTrigger asChild>{cta}</TooltipTrigger>
      <TooltipContent side="right">Start a new practice round</TooltipContent>
    </TooltipRoot>
  );
}
