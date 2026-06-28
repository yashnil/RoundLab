/**
 * Shared motion presets for Dissio.
 * Import from here — never hardcode transition values in components.
 *
 * Usage:
 *   import { fadeUp, T, staggerParent, staggerChild, reducedSafe } from "@/lib/motion";
 *
 *   // Always wrap entrance animations with reducedSafe():
 *   <motion.div {...reducedSafe(fadeUp(0.1))} />
 *
 *   <motion.ul variants={staggerParent()} initial="hidden" animate="show">
 *     <motion.li variants={staggerChild} />
 *   </motion.ul>
 */

// ── Easing curves ─────────────────────────────────────────────────────────────
export const EASE      = [0.22, 1, 0.36, 1] as [number, number, number, number];
export const EASE_SOFT = [0.4, 0, 0.2, 1]  as [number, number, number, number];

// ── Transition presets ────────────────────────────────────────────────────────
export const T = {
  fast:   { duration: 0.15, ease: EASE },
  base:   { duration: 0.30, ease: EASE },
  slow:   { duration: 0.50, ease: EASE },
  spring: { type: "spring", stiffness: 360, damping: 30 } as const,
  snap:   { type: "spring", stiffness: 500, damping: 38 } as const,
} as const;

// ── Prop factories (spread onto motion.* elements) ────────────────────────────

export function fadeUp(delay = 0) {
  return {
    suppressHydrationWarning: true,
    initial:    { opacity: 0, y: 16 },
    animate:    { opacity: 1, y: 0  },
    transition: { duration: 0.4, delay, ease: EASE },
  } as const;
}

export function fadeIn(delay = 0) {
  return {
    suppressHydrationWarning: true,
    initial:    { opacity: 0 },
    animate:    { opacity: 1 },
    transition: { duration: 0.3, delay, ease: EASE },
  } as const;
}

export function fadeUpInView(delay = 0) {
  return {
    suppressHydrationWarning: true,
    initial:    { opacity: 0, y: 14 },
    whileInView: { opacity: 1, y: 0 },
    viewport:   { once: true, margin: "-40px" },
    transition: { duration: 0.4, delay, ease: EASE },
  } as const;
}

export function slideInLeft(delay = 0) {
  return {
    suppressHydrationWarning: true,
    initial:    { opacity: 0, x: -16 },
    animate:    { opacity: 1, x: 0   },
    transition: { duration: 0.4, delay, ease: EASE },
  } as const;
}

export function slideInRight(delay = 0) {
  return {
    suppressHydrationWarning: true,
    initial:    { opacity: 0, x: 16 },
    animate:    { opacity: 1, x: 0  },
    transition: { duration: 0.4, delay, ease: EASE },
  } as const;
}

// ── Stagger variants (use with motion parent + children sharing variant names) ─

/** Parent container — sets stagger cadence on children */
export function staggerParent(cadence = 0.07, delay = 0) {
  return {
    hidden: {},
    show: {
      transition: {
        staggerChildren: cadence,
        delayChildren:   delay,
      },
    },
  } as const;
}

/** Child variant — used inside a stagger parent */
export const staggerChild = {
  hidden:  { opacity: 0, y: 12 },
  show:    { opacity: 1, y: 0  },
  transition: { duration: 0.3, ease: EASE },
} as const;

// ── Card hover preset ─────────────────────────────────────────────────────────
export const cardHover = {
  whileHover: { y: -2, transition: { duration: 0.15, ease: EASE } },
  whileTap:   { y:  0, scale: 0.99 },
} as const;

// ── Reduced-motion support ────────────────────────────────────────────────────

/**
 * No-op motion props — instant, no visual movement.
 * Spread onto motion.* as a fallback when reduced motion is preferred.
 */
export const MOTION_NOOP = {
  initial: {},
  animate: {},
  transition: { duration: 0 },
} as const;

/**
 * Wraps any motion prop factory and returns MOTION_NOOP when
 * `prefers-reduced-motion: reduce` is active.
 *
 * Always use on entrance animations (fadeUp, fadeIn, fadeUpInView, stagger, etc.)
 * to respect user accessibility preferences.
 *
 *   <motion.div {...reducedSafe(fadeUp(0.1))} />
 *   <motion.div {...reducedSafe(fadeUpInView(0.2))} />
 */
export function reducedSafe<T extends object>(props: T): T | typeof MOTION_NOOP {
  if (typeof window === "undefined") return props;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches
    ? MOTION_NOOP
    : props;
}
