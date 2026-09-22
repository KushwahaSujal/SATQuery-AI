"use client";

import { motion } from "framer-motion";
import { pageVariant } from "@/lib/motion";

/**
 * Route transition.
 *
 * Next's App Router re-mounts `template.tsx` on every navigation (unlike `layout.tsx`,
 * which persists), so this is the one place a page-level entrance can live without
 * wrapping each route by hand.
 *
 * It is deliberately subtle -- a 0.28s fade. Anything more turns navigation into a
 * slideshow, and the chrome (sidebar, topbar) stays put because it lives in the layout
 * above this.
 *
 * It fades only. `display: contents` would give this wrapper no box at all (so nothing
 * would animate), and a transform would turn it into the containing block for the
 * position:fixed drawer and hero video mid-navigation.
 *
 * Reduced motion is handled by MotionConfig in components/Providers.tsx, which applies
 * the viewer's preference to every framer-motion animation, plus the CSS block in
 * globals.css for non-JS transitions.
 */
export default function Template({ children }: { children: React.ReactNode }) {
  return (
    <motion.div initial="hidden" animate="show" variants={pageVariant} className="h-full">
      {children}
    </motion.div>
  );
}
