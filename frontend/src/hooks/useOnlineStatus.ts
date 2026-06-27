"use client";

import { useEffect, useState } from "react";

/**
 * Returns the browser's current online/offline status.
 *
 * The initial value is always true so the server render and first client
 * render match. The real browser status is read after hydration.
 */
export function useOnlineStatus(): boolean {
  const [online, setOnline] = useState(true);

  useEffect(() => {
    if (typeof navigator === "undefined") return;

    const updateStatus = () => {
      setOnline(navigator.onLine);
    };

    updateStatus();

    window.addEventListener("online", updateStatus);
    window.addEventListener("offline", updateStatus);

    return () => {
      window.removeEventListener("online", updateStatus);
      window.removeEventListener("offline", updateStatus);
    };
  }, []);

  return online;
}
