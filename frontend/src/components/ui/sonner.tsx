"use client";

import * as React from "react";
import { Toaster as SonnerToaster, toast } from "sonner";
import { useTheme } from "@/hooks/useTheme";

/**
 * App-wide toast host. Mounted once in the authenticated shell.
 * Reads the persisted RoundLab theme so toasts match light/dark.
 */
function Toaster(props: React.ComponentProps<typeof SonnerToaster>) {
  const { theme } = useTheme();

  return (
    <SonnerToaster
      theme={theme}
      position="bottom-right"
      toastOptions={{
        classNames: {
          toast:
            "!bg-surface-2 !border !border-hairline-strong !text-ink !rounded-lg !shadow-xl",
          description: "!text-ink-subtle",
          actionButton: "!bg-lav !text-white",
          cancelButton: "!bg-surface-3 !text-ink-subtle",
        },
      }}
      {...props}
    />
  );
}

export { Toaster, toast };
