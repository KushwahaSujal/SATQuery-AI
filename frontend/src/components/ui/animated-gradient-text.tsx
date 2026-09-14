"use client";

import { cn } from "@/lib/utils";

interface AnimatedGradientTextProps {
  children: React.ReactNode;
  className?: string;
}

export function AnimatedGradientText({ children, className }: AnimatedGradientTextProps) {
  return (
    <span
      className={cn(
        "inline-block bg-gradient-to-r from-[var(--accent-text)] via-[var(--cyan)] to-[var(--accent-text)] bg-[length:200%_auto] bg-clip-text text-transparent animate-gradient",
        className
      )}
    >
      {children}
    </span>
  );
}
