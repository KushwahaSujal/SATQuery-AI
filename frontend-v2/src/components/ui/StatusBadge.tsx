import { cn } from "@/lib/utils";

interface StatusBadgeProps {
  status: "completed" | "processing" | "failed" | "queued";
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const config = {
    completed: { bg: "bg-emerald-950/60", text: "text-emerald-400", border: "border-emerald-800/40", dot: "bg-emerald-400", label: "Completed" },
    processing: { bg: "bg-amber-950/60", text: "text-amber-400", border: "border-amber-800/40", dot: "bg-amber-400 animate-pulse", label: "Processing" },
    failed: { bg: "bg-rose-950/60", text: "text-rose-400", border: "border-rose-800/40", dot: "bg-rose-500", label: "Failed" },
    queued: { bg: "bg-slate-800/60", text: "text-slate-400", border: "border-slate-700/40", dot: "bg-slate-400", label: "Queued" },
  };

  const c = config[status];

  return (
    <span className={cn(`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-medium ${c.bg} ${c.text} border ${c.border}`, className)}>
      <span className={`w-1.5 h-1.5 rounded-full ${c.dot}`} />
      {c.label}
    </span>
  );
}
