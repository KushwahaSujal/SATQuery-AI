"use client";

import { cn } from "@/lib/utils";

interface BorderBeamProps {
  className?: string;
  size?: number;
  duration?: number;
  delay?: number;
  colorFrom?: string;
  colorTo?: string;
  borderWidth?: number;
}

export function BorderBeam({
  className,
  size = 200,
  duration = 8,
  delay = 0,
  colorFrom = "#00d5be",
  colorTo = "#00f2fe",
  borderWidth = 1.5,
}: BorderBeamProps) {
  return (
    <div
      style={
        {
          "--size": size,
          "--duration": duration,
          "--delay": `-${delay}s`,
          "--color-from": colorFrom,
          "--color-to": colorTo,
          "--border-width": `${borderWidth}px`,
        } as React.CSSProperties
      }
      className={cn(
        "pointer-events-none absolute inset-0 rounded-[inherit] [border:var(--border-width)_solid_transparent]",
        "[background:linear-gradient(#0a1628,#0a1628)_padding-box,linear-gradient(calc(var(--angle)*1deg),transparent_20%,var(--color-from),var(--color-to),transparent_80%)_border-box]",
        "[animation:border-beam_calc(var(--duration)*1s)_var(--delay)_infinite_linear]",
        className
      )}
    />
  );
}
