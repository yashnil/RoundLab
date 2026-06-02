import * as React from "react"
import { cn } from "@/lib/utils"

/* Input — 8px border radius, surface-2 fill, hairline border.
   Focus: 2px ring at lav/50 opacity. */

function Input({ className, type, ...props }: React.ComponentProps<"input">) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        "h-8 w-full min-w-0 rounded-md border border-hairline bg-surface-2 px-3 py-1.5",
        "text-sm text-ink placeholder:text-ink-faint",
        "transition-colors outline-none",
        "focus-visible:border-lav/50 focus-visible:ring-2 focus-visible:ring-lav/20",
        "disabled:cursor-not-allowed disabled:opacity-40",
        "file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-ink",
        className
      )}
      {...props}
    />
  )
}

export { Input }
