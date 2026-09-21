import type { Transition, Variants } from "framer-motion";

/**
 * One motion vocabulary for the whole app.
 *
 * Four pages (history, datasets, reports, documentation) each carried their own copy of
 * `stagger` / `fadeUp` / `rowVariant` / `cardVariant`, and the copies had drifted:
 * staggerChildren was 0.07, 0.07, 0.06 and 0.05, delayChildren 0.1, 0.05, 0.05 and 0.04,
 * and rowVariant was x:-12/0.4s in one place and x:-8/0.35s in another. Extracting them
 * therefore is not a pure refactor -- it picks canonical timings, which is a deliberate
 * choice recorded here rather than four accidents.
 *
 * Canonical values below are the median of what was already in use, so no page changes
 * dramatically.
 */

/** Standard easing: a quick start that settles, used everywhere. */
export const EASE: [number, number, number, number] = [0.22, 1, 0.36, 1];

export const DURATION = {
  /** Hover, press, colour changes. */
  fast: 0.18,
  /** The default for entrances and layout moves. */
  base: 0.4,
  /** Larger surfaces: route changes, panels. */
  slow: 0.55,
} as const;

export const transition = (duration: number = DURATION.base): Transition => ({
  duration,
  ease: EASE,
});

/**
 * Motion is opt-out at the OS level. Reading the media query keeps `prefers-reduced-motion`
 * honoured without every component remembering to check, and it is read lazily so this
 * module stays safe to import during SSR.
 */
export function prefersReducedMotion(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  } catch {
    return false;
  }
}

/** Container that reveals its children one after another. */
export const stagger: Variants = {
  hidden: {},
  show: {
    transition: { staggerChildren: 0.06, delayChildren: 0.05 },
  },
};

/** Faster stagger for dense lists where the full cascade would feel slow. */
export const staggerTight: Variants = {
  hidden: {},
  show: {
    transition: { staggerChildren: 0.035, delayChildren: 0.04 },
  },
};

/** The default entrance: rise and fade. */
export const fadeUp: Variants = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: transition() },
};

/** Plain fade, for things that should not move. */
export const fade: Variants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: transition() },
};

/** Table and list rows, which slide in from the leading edge. */
export const rowVariant: Variants = {
  hidden: { opacity: 0, x: -10 },
  show: { opacity: 1, x: 0, transition: transition(0.38) },
};

/** Cards in a grid, which also scale very slightly. */
export const cardVariant: Variants = {
  hidden: { opacity: 0, y: 16, scale: 0.97 },
  show: { opacity: 1, y: 0, scale: 1, transition: transition() },
};

/** Panels that slide in from the trailing edge, e.g. a detail drawer. */
export const panelVariant: Variants = {
  hidden: { opacity: 0, x: 24 },
  show: { opacity: 1, x: 0, transition: transition(DURATION.slow) },
  exit: { opacity: 0, x: 24, transition: transition(DURATION.fast) },
};

/** Dialogs and the command palette. */
export const overlayVariant: Variants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: transition(DURATION.fast) },
  exit: { opacity: 0, transition: transition(DURATION.fast) },
};

export const modalVariant: Variants = {
  hidden: { opacity: 0, y: -8, scale: 0.98 },
  show: { opacity: 1, y: 0, scale: 1, transition: transition(0.22) },
  exit: { opacity: 0, y: -8, scale: 0.98, transition: transition(DURATION.fast) },
};

/**
 * Whole-route transition. Deliberately subtle: a page should not feel like a slideshow.
 *
 * Opacity only, on purpose. A `transform` on the route wrapper would make it the
 * containing block for every position:fixed descendant while it animated -- the mobile
 * nav drawer and the home hero video both rely on being fixed to the viewport, and they
 * would jump for the duration of every navigation.
 */
export const pageVariant: Variants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: transition(0.28) },
};

/** Shared hover/press feedback for controls that should feel physical. */
export const pressable = {
  whileHover: { scale: 1.02 },
  whileTap: { scale: 0.98 },
  transition: { duration: DURATION.fast, ease: EASE },
} as const;

/** Subtler variant for large targets, where 1.02 reads as a jump. */
export const pressableSubtle = {
  whileHover: { scale: 1.01 },
  whileTap: { scale: 0.995 },
  transition: { duration: DURATION.fast, ease: EASE },
} as const;
