"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

interface AuroraTextProps extends React.HTMLAttributes<HTMLElement> {
  children: React.ReactNode;
  as?: "span" | "h1" | "h2" | "h3" | "p" | "div";
  colors?: string[];
  speed?: number;
}

export function AuroraText({
  children,
  className,
  as: Tag = "span",
  colors = ["#00d5be", "#168BFF", "#7957FF", "#00C7D9"],
  speed = 6,
  ...props
}: AuroraTextProps) {
  const gradient = `linear-gradient(120deg, ${colors.join(", ")}, ${colors[0]})`;

  return (
    <Tag
      className={cn("relative inline-block", className)}
      style={
        {
          backgroundImage: gradient,
          backgroundSize: "300% 100%",
          WebkitBackgroundClip: "text",
          backgroundClip: "text",
          WebkitTextFillColor: "transparent",
          color: "transparent",
          animation: `aurora-shift ${speed}s linear infinite`,
        } as React.CSSProperties
      }
      {...props}
    >
      {children}
    </Tag>
  );
}