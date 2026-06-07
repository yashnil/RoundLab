import { useEffect, useRef, useState } from "react";

interface Options {
  /** Fraction of element visible before triggering (0–1). Default 0.2. */
  threshold?: number;
  /** CSS rootMargin string. Default "0px". */
  rootMargin?: string;
}

/**
 * Returns [ref, hasEntered].
 *
 * hasEntered becomes true once the element crosses the viewport threshold
 * and stays true — it never resets, even if the element leaves the viewport.
 *
 * Respects prefers-reduced-motion: if the user has reduced motion enabled,
 * hasEntered starts as true so consumers skip staggered reveals.
 */
export function useInViewOnce<T extends HTMLElement = HTMLDivElement>(
  options: Options = {},
): [React.RefObject<T | null>, boolean] {
  const ref = useRef<T | null>(null);
  const [hasEntered, setHasEntered] = useState(false);

  useEffect(() => {
    // Respect reduced motion — skip animation, show final state immediately
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setHasEntered(true);
      return;
    }

    const el = ref.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setHasEntered(true);
          observer.unobserve(el);
        }
      },
      {
        threshold: options.threshold ?? 0.2,
        rootMargin: options.rootMargin ?? "0px",
      },
    );

    observer.observe(el);
    return () => observer.disconnect();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return [ref, hasEntered];
}
