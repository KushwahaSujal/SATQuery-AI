"use client";

import { motion } from "framer-motion";
import { DURATION, EASE } from "@/lib/motion";

/**
 * Placeholder for the results view while an analysis runs.
 *
 * It mirrors the layout the finished view actually uses -- a layer strip, a large canvas
 * and a metrics row -- so the page does not visibly rearrange when the real content
 * arrives. It deliberately contains no numbers: a skeleton that showed plausible-looking
 * values would be inventing results that do not exist yet.
 */
export function ResultsSkeleton({ layerCount = 4 }: { layerCount?: number }) {
  return (
    <div className="space-y-3" aria-hidden="true">
      {/* Layer strip */}
      <div className="flex gap-2 overflow-hidden">
        {Array.from({ length: layerCount }).map((_, i) => (
          <Shimmer key={i} delay={i * 0.08} className="h-9 flex-1 rounded-lg" style={{ minWidth: 88 }} />
        ))}
      </div>

      {/* Canvas */}
      <Shimmer delay={0.1} className="h-64 w-full rounded-xl sm:h-80" />

      {/* Metrics row */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div
            key={i}
            className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-3"
          >
            <Shimmer delay={0.15 + i * 0.05} className="h-2 w-2/3 rounded" />
            <Shimmer delay={0.2 + i * 0.05} className="mt-2 h-3.5 w-1/2 rounded" />
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * A single shimmering block.
 *
 * The sweep is a background animation rather than a transform so it cannot become the
 * containing block for anything positioned inside it, and `prefers-reduced-motion` is
 * honoured through MotionConfig in components/Providers.tsx.
 */
function Shimmer({
  className = "",
  style,
  delay = 0,
}: {
  className?: string;
  style?: React.CSSProperties;
  delay?: number;
}) {
  return (
    <motion.div
      className={`relative overflow-hidden bg-[var(--surface-2)] ${className}`}
      style={style}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: DURATION.base, ease: EASE, delay }}
    >
      <motion.div
        className="absolute inset-0"
        style={{
          background:
            "linear-gradient(90deg, transparent 0%, var(--surface-3) 50%, transparent 100%)",
        }}
        animate={{ x: ["-100%", "100%"] }}
        transition={{ duration: 1.5, repeat: Infinity, ease: "linear", delay }}
      />
    </motion.div>
  );
}
