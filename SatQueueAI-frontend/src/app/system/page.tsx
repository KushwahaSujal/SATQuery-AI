"use client";

import { useHealth, useModels } from "@/hooks/useSystem";
import TerminalConsole from "@/components/terminal/TerminalConsole";

function Row({ label, value, status }: { label: string; value: string; status?: "ok" | "warn" | "err" }) {
  const valueColor = status === "ok" ? "text-[#4ade80]" : status === "warn" ? "text-[#fbbf24]" : status === "err" ? "text-[#f87171]" : "text-[#737373]";
  return (
    <div className="flex items-center justify-between px-4 py-3 border-b border-[#1a1a1a] last:border-0 hover:bg-[#0d0d0d] transition-colors">
      <span className="font-mono-data text-[11px] text-[#404040]">{label}</span>
      <span className={["font-mono-data text-[11px]", valueColor].join(" ")}>{value}</span>
    </div>
  );
}

export default function SystemPage() {
  const health = useHealth();
  const models = useModels();

  const d = health.data ?? {
    api: health.isLoading ? "connecting..." : "offline",
    database: health.isLoading ? "checking..." : "offline",
    storage: "unknown",
    models_ready: 0,
    models_total: 0,
    active_requests: 0,
    device: "CPU",
    version: "1.0.0",
    environment: "development",
  };
  const modelList = models.data ?? [];

  return (
    <div className="space-y-4 animate-fade-in">
      {/* Interactive CLI Console */}
      <TerminalConsole title={`satquery-cli v${d.version || "1.0.0"}`} subtitle="satquery — active pipeline modules" />

      {/* System Health & Status Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_1fr] gap-4">
        {/* Health table */}
        <div className="border border-[#1a1a1a] rounded-lg overflow-hidden">
          <div className="flex items-center px-4 h-10 border-b border-[#1a1a1a] bg-[#0a0a0a]">
            <span className="text-[13px] font-medium text-[#d4d4d4]">System Health</span>
          </div>

          <Row label="API Gateway" value={d.api} status={d.api === "online" ? "ok" : "err"} />
          <Row label="Database Engine" value={d.database} status={d.database === "connected" ? "ok" : "err"} />
          <Row label="Compute Device" value={d.device || "CPU"} status={d.device ? "ok" : "warn"} />
          <Row
            label="Models Available"
            value={`${d.models_ready ?? 0} / ${d.models_total ?? 0} ready`}
            status={(d.models_ready ?? 0) > 0 ? "ok" : "warn"}
          />
          <Row label="Environment" value={d.environment || "development"} />
        </div>

        {/* Models list */}
        <div className="border border-[#1a1a1a] rounded-lg overflow-hidden flex flex-col">
          <div className="flex items-center px-4 h-10 border-b border-[#1a1a1a] bg-[#0a0a0a]">
            <span className="text-[13px] font-medium text-[#d4d4d4]">Registered Pipeline Models</span>
          </div>

          <div className="p-4 space-y-2.5 font-mono-data text-[11px] overflow-y-auto h-[250px]">
            {modelList.length > 0 ? (
              modelList.map((m) => (
                <div key={m.name} className="flex items-center justify-between border-b border-[#1a1a1a] pb-1.5 last:border-0">
                  <div>
                    <span className="text-[#d4d4d4] font-medium block">{m.name}</span>
                    <span className="text-[#404040] text-[10px]">{m.task}</span>
                  </div>
                  <span className={m.status === "AVAILABLE" || m.loaded ? "text-[#4ade80]" : "text-[#737373]"}>
                    {m.status === "AVAILABLE" || m.loaded ? "AVAILABLE" : "NO CHECKPOINT"}
                  </span>
                </div>
              ))
            ) : (
              <div className="text-center text-[#737373] py-4">
                {models.isLoading ? "Loading backend models..." : "No models registered"}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
