import { useEffect, useRef, useState, useSyncExternalStore } from "react";

interface Options {
  /** Fraction of element visible before triggering (0–1). Default 0.2. */
  threshold?: number;
  /** CSS rootMargin string. Default "0px". */
  rootMargin?: string;
}

const REDUCED_MOTION_QUERY = "(prefers-reduced-motion: reduce)";

function subscribeReducedMotion(callback: () => void): () => void {
  if (typeof window === "undefined" || !window.matchMedia) return () => {};
  const mq = window.matchMedia(REDUCED_MOTION_QUERY);
  mq.addEventListener("change", callback);
  return () => mq.removeEventListener("change", callback);
}

function getReducedMotionSnapshot(): boolean {
  if (typeof window === "undefined" || !window.matchMedia) return false;
  return window.matchMedia(REDUCED_MOTION_QUERY).matches;
}

/**
 * Returns [ref, hasEntered].
 *
 * hasEntered becomes true once the element crosses the viewport threshold
 * and stays true — it never resets, even if the element leaves the viewport.
 *
 * Respects prefers-reduced-motion: reduced-motion users get hasEntered=true
 * immediately so consumers skip staggered reveals. The media query is read via
 * useSyncExternalStore (hydration-safe, no setState-in-effect).
 */
export function useInViewOnce<T extends HTMLElement = HTMLDivElement>(
  options: Options = {},
): [React.RefObject<T | null>, boolean] {
  const ref = useRef<T | null>(null);
  const [enteredView, setEnteredView] = useState(false);
  const prefersReducedMotion = useSyncExternalStore(
    subscribeReducedMotion,
    getReducedMotionSnapshot,
    () => false,
  );

  useEffect(() => {
    if (prefersReducedMotion) return; // final state already shown
    const el = ref.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setEnteredView(true);
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
  }, [prefersReducedMotion]);

  return [ref, enteredView || prefersReducedMotion];
}
