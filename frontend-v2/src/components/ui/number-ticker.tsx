"use client";

import { useEffect, useRef, useState } from "react";

interface NumberTickerProps {
  value: number;
  suffix?: string;
  prefix?: string;
  decimalPlaces?: number;
  duration?: number; // ms
  className?: string;
}

export function NumberTicker({
  value,
  suffix = "",
  prefix = "",
  decimalPlaces = 0,
  duration = 1800,
  className,
}: NumberTickerProps) {
  const [current, setCurrent] = useState(0);
  const ref = useRef<HTMLSpanElement>(null);
  const started = useRef(false);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !started.current) {
          started.current = true;
          const startTime = performance.now();
          const animate = (now: number) => {
            const elapsed = now - startTime;
            const progress = Math.min(elapsed / duration, 1);
            // ease-out-expo
            const eased = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);
            setCurrent(eased * value);
            if (progress < 1) requestAnimationFrame(animate);
          };
          requestAnimationFrame(animate);
        }
      },
      { threshold: 0.2 }
    );
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, [value, duration]);

  return (
    <span ref={ref} className={className}>
      {prefix}
      {current.toFixed(decimalPlaces)}
      {suffix}
    </span>
  );
}
