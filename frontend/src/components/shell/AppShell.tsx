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
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-3 focus:z-50 focus:rounded-md focus:bg-primary focus:px-3 focus:py-2 focus:text-sm focus:text-primary-foreground"
      >
        Skip to content
      </a>
      <div className="flex min-h-screen bg-canvas">
        <AppSidebar />
        <div className="flex min-w-0 flex-1 flex-col">
          <ProductHeader leftSlot={headerLeft} rightSlot={headerRight} />
          <main
            id="main-content"
            className={cn(
              "mx-auto w-full flex-1 pb-[calc(4rem+env(safe-area-inset-bottom))] md:pb-0",
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
