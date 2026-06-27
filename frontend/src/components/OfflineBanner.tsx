"use client";
import { useOnlineStatus } from "@/hooks/useOnlineStatus";
import { WifiOff } from "lucide-react";

/**
 * Shows a sticky banner when the browser goes offline.
 * Hides automatically when connectivity is restored.
 * Must be rendered inside a client component.
 */
export function OfflineBanner() {
  const online = useOnlineStatus();

  if (online) return null;

  return (
    <div
      role="status"
      aria-live="assertive"
      className="fixed top-0 inset-x-0 z-50 flex items-center justify-center gap-2 bg-warn/90 px-4 py-2 text-[12px] font-semibold text-white backdrop-blur-sm"
    >
      <WifiOff size={13} aria-hidden />
      You&apos;re offline — drafts are saved locally and will sync when you reconnect.
    </div>
  );
}
