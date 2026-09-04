import { cn } from "@/lib/utils";

const stateConfig = {
  success: "text-[#4ade80]",
  warning: "text-[#fbbf24]",
  error:   "text-[#f87171]",
  neutral: "text-[#737373]",
} as const;

type BadgeState = keyof typeof stateConfig;

interface StatusBadgeProps {
  label: string;
  state?: BadgeState;
  dot?: boolean;
  className?: string;
}

export default function StatusBadge({ label, state = "neutral", dot = true, className }: StatusBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 font-mono-data text-[11px] select-none",
        stateConfig[state],
        className
      )}
    >
      {dot && (
        <span
          className={cn(
            "status-dot",
            state === "success" && "status-dot-green",
            state === "warning" && "status-dot-amber",
            state === "error"   && "status-dot-red",
            state === "neutral" && "status-dot-muted"
          )}
        />
      )}
      {label}
    </span>
  );
}
