"use client";

import { useModels } from "@/hooks/useSystem";
import type { ModelInfo } from "@/lib/types";

const lifecycleStyle: Record<string, string> = {
  LOADED:         "text-[#4ade80]",
  AVAILABLE:      "text-[#60a5fa]",
  NOT_CONFIGURED: "text-[#737373]",
  FAILED:         "text-[#f87171]",
};

export default function ModelsPage() {
  const { data, isLoading } = useModels();
  const models = data ?? [];

  return (
    <div className="flex flex-col border border-[#1a1a1a] rounded-lg overflow-hidden animate-fade-in" style={{ height: "calc(100vh - 80px)" }}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 h-10 border-b border-[#1a1a1a] bg-[#0a0a0a] shrink-0">
        <span className="text-[13px] font-medium text-[#d4d4d4]">Model Observatory</span>
        <span className="font-mono-data text-[11px] text-[#333]">
          {models.filter(m => m.status === "LOADED").length} loaded · {models.length} registered
        </span>
      </div>

      {/* Model rows — dense scrollable list */}
      <div className="flex-1 overflow-y-auto divide-y divide-[#1a1a1a]">
        {models.map((model) => (
          <div key={model.name} className="flex items-start gap-4 px-4 py-4 hover:bg-[#0d0d0d] transition-colors">
            {/* Lifecycle indicator */}
            <div className="pt-0.5 shrink-0 w-2 flex justify-center">
              <span className={["status-dot mt-1.5", model.status === "LOADED" ? "status-dot-green" : model.status === "AVAILABLE" ? "status-dot-muted" : "status-dot-red"].join(" ")} />
            </div>

            {/* Main content */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-3">
                <span className="text-[13px] font-medium text-[#e5e5e5]">{model.name}</span>
                <span className={["font-mono-data text-[10px]", lifecycleStyle[model.status] ?? "text-[#333]"].join(" ")}>
                  {model.status}
                </span>
              </div>
              <div className="flex items-center gap-4 mt-0.5">
                <span className="font-mono-data text-[11px] text-[#404040]">{model.task}</span>
                {model.device && (
                  <span className="font-mono-data text-[11px] text-[#2a2a2a]">{model.device}</span>
                )}
              </div>
              {model.description && (
                <p className="text-[11px] text-[#333] mt-1.5 leading-relaxed max-w-2xl">{model.description}</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
