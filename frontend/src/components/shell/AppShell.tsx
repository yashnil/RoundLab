"use client";

import { type ReactNode } from "react";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Toaster } from "@/components/ui/sonner";
import AppSidebar from "@/components/shell/AppSidebar";
import MobileNav from "@/components/shell/MobileNav";
import ProductHeader from "@/components/shell/ProductHeader";
import CommandMenu from "@/components/shell/CommandMenu";
import { cn } from "@/lib/utils";

type MaxWidth = "full" | "7xl" | "5xl" | "3xl";

const maxWidthClasses: Record<MaxWidth, string> = {
  full: "max-w-full",
  "7xl": "max-w-7xl",
  "5xl": "max-w-5xl",
  "3xl": "max-w-3xl",
};

interface AppShellProps {
  children: ReactNode;
  maxWidth?: MaxWidth;
  /** Header left context (breadcrumbs / page label). */
  headerLeft?: ReactNode;
  /** Header right controls. */
  headerRight?: ReactNode;
  /** Remove the default page padding (for full-bleed surfaces). */
  bare?: boolean;
}

/**
 * AppShell — the single authenticated product shell: collapsible sidebar,
 * sticky header, mobile bottom-nav, and global command menu (Cmd/Ctrl-K).
 */
export default function AppShell({
  children,
  maxWidth = "7xl",
  headerLeft,
  headerRight,
  bare = false,
}: AppShellProps) {
  return (
    <TooltipProvider delayDuration={250}>
      {/*
        Skip link — off-canvas at all times via absolute -left-[9999px].
        Never reserves layout space, never flashes on hydration or route changes.
        Pointer interactions cannot trigger it (only keyboard Tab focus).
        focus:left-4 brings it into view; the main target has tabIndex={-1} so
        Enter/activate moves focus to main content correctly.
      */}
      <a
        href="#main-content"
        className="absolute -left-[9999px] top-3 z-[100] rounded-md bg-lav px-3 py-2 text-sm font-medium text-white focus:left-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/50"
      >
        Skip to content
      </a>
      <div className="flex min-h-screen bg-canvas">
        <AppSidebar />
        <div className="flex min-w-0 flex-1 flex-col">
          <ProductHeader leftSlot={headerLeft} rightSlot={headerRight} />
          <main
            id="main-content"
            tabIndex={-1}
            className={cn(
              "mx-auto w-full flex-1 pb-[calc(4rem+env(safe-area-inset-bottom))] md:pb-0",
              "focus-visible:outline-none",
              maxWidthClasses[maxWidth],
              !bare && "px-4 py-6 sm:px-6 lg:px-8",
            )}
          >
            {children}
          </main>
        </div>
      </div>
      <MobileNav />
      <CommandMenu />
      <Toaster />
    </TooltipProvider>
  );
}
