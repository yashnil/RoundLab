"use client";

import * as React from "react";
import { Tabs } from "radix-ui";
import { cn } from "@/lib/utils";

const TabsRoot = Tabs.Root;

const TabsList = React.forwardRef<
  React.ElementRef<typeof Tabs.List>,
  React.ComponentPropsWithoutRef<typeof Tabs.List>
>(({ className, ...props }, ref) => (
  <Tabs.List
    ref={ref}
    className={cn(
      "inline-flex items-center gap-1 rounded-lg border border-hairline bg-surface-1 p-1",
      className,
    )}
    {...props}
  />
));
TabsList.displayName = "TabsList";

const TabsTrigger = React.forwardRef<
  React.ElementRef<typeof Tabs.Trigger>,
  React.ComponentPropsWithoutRef<typeof Tabs.Trigger>
>(({ className, ...props }, ref) => (
  <Tabs.Trigger
    ref={ref}
    className={cn(
      "inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium",
      "text-ink-subtle transition-colors hover:text-ink",
      "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50",
      "data-[state=active]:bg-surface-3 data-[state=active]:text-ink data-[state=active]:shadow-sm",
      "disabled:pointer-events-none disabled:opacity-50",
      className,
    )}
    {...props}
  />
));
TabsTrigger.displayName = "TabsTrigger";

const TabsContent = React.forwardRef<
  React.ElementRef<typeof Tabs.Content>,
  React.ComponentPropsWithoutRef<typeof Tabs.Content>
>(({ className, ...props }, ref) => (
  <Tabs.Content
    ref={ref}
    className={cn(
      "mt-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50",
      className,
    )}
    {...props}
  />
));
TabsContent.displayName = "TabsContent";

export { TabsRoot, TabsList, TabsTrigger, TabsContent };
