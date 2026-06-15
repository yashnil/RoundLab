"use client";

import * as React from "react";
import { Tooltip } from "radix-ui";
import { cn } from "@/lib/utils";

const TooltipProvider = Tooltip.Provider;
const TooltipRoot = Tooltip.Root;
const TooltipTrigger = Tooltip.Trigger;

const TooltipContent = React.forwardRef<
  React.ElementRef<typeof Tooltip.Content>,
  React.ComponentPropsWithoutRef<typeof Tooltip.Content>
>(({ className, sideOffset = 6, ...props }, ref) => (
  <Tooltip.Portal>
    <Tooltip.Content
      ref={ref}
      sideOffset={sideOffset}
      className={cn(
        "z-50 max-w-xs rounded-md border border-hairline-strong bg-surface-3 px-2.5 py-1.5",
        "text-xs font-medium leading-snug text-ink shadow-lg",
        "data-[state=delayed-open]:animate-in data-[state=closed]:animate-out",
        "data-[state=closed]:fade-out-0 data-[state=delayed-open]:fade-in-0",
        "data-[state=closed]:zoom-out-95 data-[state=delayed-open]:zoom-in-95",
        className,
      )}
      {...props}
    />
  </Tooltip.Portal>
));
TooltipContent.displayName = "TooltipContent";

export { TooltipProvider, TooltipRoot, TooltipTrigger, TooltipContent };
