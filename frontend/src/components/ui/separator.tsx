"use client";

import * as React from "react";
import { Separator } from "radix-ui";
import { cn } from "@/lib/utils";

const SeparatorRoot = React.forwardRef<
  React.ElementRef<typeof Separator.Root>,
  React.ComponentPropsWithoutRef<typeof Separator.Root>
>(({ className, orientation = "horizontal", decorative = true, ...props }, ref) => (
  <Separator.Root
    ref={ref}
    decorative={decorative}
    orientation={orientation}
    className={cn(
      "shrink-0 bg-hairline",
      orientation === "horizontal" ? "h-px w-full" : "h-full w-px",
      className,
    )}
    {...props}
  />
));
SeparatorRoot.displayName = "SeparatorRoot";

export { SeparatorRoot };
