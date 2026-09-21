"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

interface MarqueeProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  pauseOnHover?: boolean;
  reverse?: boolean;
  speed?: number; // seconds per loop
}

export function Marquee({
  children,
  className,
  pauseOnHover = true,
  reverse = false,
  speed = 30,
  ...props
}: MarqueeProps) {
  return (
    <div
      className={cn(
        "group flex w-full overflow-hidden [--gap:1.5rem] [mask-image:linear-gradient(to_right,transparent,black_8%,black_92%,transparent)]",
        className
      )}
      style={{ "--marquee-duration": `${speed}s` } as React.CSSProperties}
      {...props}
    >
      <div
        className={cn(
          "flex shrink-0 gap-[var(--gap)] pr-[var(--gap)]",
          "animate-marquee",
          reverse && "[animation-direction:reverse]",
          pauseOnHover && "group-hover:[animation-play-state:paused]"
        )}
      >
        {children}
      </div>
      <div
        aria-hidden
        className={cn(
          "flex shrink-0 gap-[var(--gap)] pr-[var(--gap)]",
          "animate-marquee",
          reverse && "[animation-direction:reverse]",
          pauseOnHover && "group-hover:[animation-play-state:paused]"
        )}
      >
        {children}
      </div>
    </div>
  );
}