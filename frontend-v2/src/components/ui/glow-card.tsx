"use client";

import { cn } from "@/lib/utils";

interface GlowCardProps extends React.HTMLAttributes<HTMLDivElement> {
  glowColor?: string;
  children: React.ReactNode;
}

export function GlowCard({ children, className, glowColor = "var(--accent)", ...props }: GlowCardProps) {
  return (
    <div
      className={cn(
        "group relative rounded-lg border border-[var(--b1)] bg-[var(--s1)] p-4",
        "transition-all duration-300",
        "hover:border-[var(--b3)] hover:shadow-[0_0_20px_rgba(0,0,0,0.3)]",
        "before:absolute before:inset-0 before:rounded-lg before:opacity-0",
        "before:transition-opacity before:duration-300",
        "hover:before:opacity-100",
        className
      )}
      style={{
        "--glow-color": glowColor,
      } as React.CSSProperties}
      {...props}
    >
      <div className="relative z-10">{children}</div>
      <div
        className="absolute inset-0 rounded-lg opacity-0 transition-opacity duration-300 group-hover:opacity-100 pointer-events-none"
        style={{
          background: `radial-gradient(400px circle at var(--mouse-x, 50%) var(--mouse-y, 50%), ${glowColor}10, transparent 40%)`,
        }}
      />
    </div>
  );
}
