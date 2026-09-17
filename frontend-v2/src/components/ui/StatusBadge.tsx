import { cn } from "@/lib/utils";

interface StatusBadgeProps {
  status: "completed" | "processing" | "failed" | "queued";
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const config = {
    completed: { bg: "var(--status-completed-bg)", text: "var(--status-completed-text)", dot: "var(--status-completed-dot)", label: "Completed" },
    processing: { bg: "var(--status-processing-bg)", text: "var(--status-processing-text)", dot: "var(--status-processing-dot)", label: "Processing" },
    failed: { bg: "var(--status-failed-bg)", text: "var(--status-failed-text)", dot: "var(--status-failed-dot)", label: "Failed" },
    queued: { bg: "var(--surface-3)", text: "var(--text-2)", dot: "var(--text-3)", label: "Queued" },
  };

  const c = config[status];

  return (
    <span
      className={cn("inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-medium border border-transparent", className)}
      style={{ background: c.bg, color: c.text }}
    >
      <span className="w-1.5 h-1.5 rounded-full" style={{ background: c.dot }} />
      {c.label}
    </span>
  );
}
