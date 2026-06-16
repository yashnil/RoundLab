"use client";

import { useEffect, useState } from "react";

/**
 * Scroll-spy: given anchor element ids (in document order), return the one
 * currently nearest the top of the viewport. Uses IntersectionObserver, so the
 * only setState happens inside the observer callback (not synchronously in the
 * effect body).
 */
export function useActiveSection(ids: string[]): string | null {
  const [active, setActive] = useState<string | null>(ids[0] ?? null);
  const key = ids.join("|");

  useEffect(() => {
    if (typeof window === "undefined" || ids.length === 0) return;

    const visible = new Map<string, number>();
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            visible.set(entry.target.id, entry.intersectionRatio);
          } else {
            visible.delete(entry.target.id);
          }
        }
        // Pick the first id (document order) that is currently visible.
        const current = ids.find((id) => visible.has(id));
        if (current) setActive(current);
      },
      { rootMargin: "-72px 0px -55% 0px", threshold: [0, 0.25, 0.5, 1] },
    );

    const els = ids
      .map((id) => document.getElementById(id))
      .filter((el): el is HTMLElement => el !== null);
    els.forEach((el) => observer.observe(el));

    return () => observer.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  return active;
}
