"use client";

import { cn } from "@/lib/utils";

interface ShimmerButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  shimmerColor?: string;
  shimmerSize?: string;
  shimmerDuration?: string;
  borderRadius?: string;
}

export function ShimmerButton({
  children,
  className,
  shimmerColor = "rgba(255, 255, 255, 0.1)",
  shimmerSize = "200px",
  shimmerDuration = "2s",
  borderRadius = "0.375rem",
  ...props
}: ShimmerButtonProps) {
  return (
    <button
      className={cn(
        "relative overflow-hidden transition-all",
        className
      )}
      style={{ borderRadius }}
      {...props}
    >
      <span className="absolute inset-0 overflow-hidden rounded-[inherit]">
        <span
          className="absolute inset-0 -translate-x-full animate-shimmer"
          style={{
            background: `linear-gradient(90deg, transparent, ${shimmerColor}, transparent)`,
            width: shimmerSize,
          }}
        />
      </span>
      <span className="relative z-10">{children}</span>
    </button>
  );
}
