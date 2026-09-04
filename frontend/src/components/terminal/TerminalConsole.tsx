import { useEffect, useRef, useState } from "react";
import { useModels } from "@/hooks/useSystem";
import { api } from "@/lib/api";
import { getLocalJobs } from "@/lib/localJobs";
import { cn } from "@/lib/utils";

export interface TerminalOutputLine {
  id: string;
  type: "input" | "header" | "row" | "info" | "success" | "error" | "muted";
  text?: string;
  columns?: { id: string; name: string; desc: string; status: "active" | "standby" | "loaded" }[];
}

interface TerminalConsoleProps {
  title?: string;
  subtitle?: string;
  className?: string;
  collapsible?: boolean;
}

export default function TerminalConsole({
  title = "satquery-cli v1.0.0",
  subtitle = "satquery — pipeline observatory",
  className,
}: TerminalConsoleProps) {
  const modelsQuery = useModels();
  const [history, setHistory] = useState<TerminalOutputLine[]>([]);
  const [inputVal, setInputVal] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Initialize terminal logs with live models when loaded
  useEffect(() => {
    const models = modelsQuery.data ?? [];
    const activeCount = models.filter((m) => m.status === "AVAILABLE" || m.loaded).length;

    const initialLogs: TerminalOutputLine[] = [
      { id: "c1", type: "input", text: "satquery pipeline status" },
      { id: "c2", type: "header", text: `SatQuery Workstation Pipeline (${activeCount}/${models.length || 9} models ready)` },
    ];

    if (models.length > 0) {
      initialLogs.push({
        id: "c3",
        type: "row",
        columns: models.slice(0, 4).map((m, idx) => ({
          id: `mod_${idx + 1}`,
          name: m.name,
          desc: m.description || m.task,
          status: m.status === "AVAILABLE" || m.loaded ? "active" : "standby",
        })),
      });
      if (models.length > 4) {
        initialLogs.push({
          id: "c4",
          type: "muted",
          text: `... +${models.length - 4} additional registered neural adapters active in memory`,
        });
      }
    } else {
      initialLogs.push({
        id: "c3",
        type: "muted",
        text: "Connecting to SatQuery neural pipeline gateway...",
      });
    }

    setHistory(initialLogs);
  }, [modelsQuery.data]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history]);

  async function handleCommand(e: React.FormEvent) {
    e.preventDefault();
    const cmd = inputVal.trim();
    if (!cmd) return;

    const newLogs: TerminalOutputLine[] = [
      ...history,
      { id: crypto.randomUUID(), type: "input", text: cmd },
    ];

    const lower = cmd.toLowerCase();

    if (lower === "clear") {
      setHistory([]);
      setInputVal("");
      return;
    } else if (lower === "help") {
      newLogs.push(
        { id: crypto.randomUUID(), type: "info", text: "Available commands:" },
        { id: crypto.randomUUID(), type: "muted", text: "  status   — View active pipeline neural adapters" },
        { id: crypto.randomUUID(), type: "muted", text: "  models   — List registered vision & VQA models" },
        { id: crypto.randomUUID(), type: "muted", text: "  jobs     — Fetch live execution job queue" },
        { id: crypto.randomUUID(), type: "muted", text: "  clear    — Clear terminal buffer" }
      );
    } else if (lower === "models" || lower === "status") {
      const models = modelsQuery.data ?? [];
      newLogs.push(
        { id: crypto.randomUUID(), type: "header", text: `Registered Pipeline Models (${models.length} active)` },
        {
          id: crypto.randomUUID(),
          type: "row",
          columns: models.map((m, idx) => ({
            id: `adapter_${idx + 1}`,
            name: m.name,
            desc: m.task,
            status: m.status === "AVAILABLE" || m.loaded ? "active" : "standby",
          })),
        }
      );
    } else if (lower === "jobs") {
      try {
        const live = await api.listJobs();
        const local = getLocalJobs();
        const combined = [...live, ...local];
        if (combined.length === 0) {
          newLogs.push(
            { id: crypto.randomUUID(), type: "info", text: "[JOB QUEUE STATUS]" },
            { id: crypto.randomUUID(), type: "muted", text: "No active analysis jobs found in database or local workspace." }
          );
        } else {
          newLogs.push({ id: crypto.randomUUID(), type: "info", text: `[JOB QUEUE STATUS - ${combined.length} RECORDS]` });
          combined.slice(0, 5).forEach((j) => {
            const id = j.job_id || j.id || "job";
            newLogs.push({
              id: crypto.randomUUID(),
              type: j.status === "COMPLETED" ? "success" : j.status === "FAILED" ? "error" : "info",
              text: `JOB ${id.slice(0, 8)} :: ${j.task || "ANALYSIS"} :: ${j.query || "Geospatial query"} (${j.status || "COMPLETED"})`,
            });
          });
        }
      } catch {
        newLogs.push({
          id: crypto.randomUUID(),
          type: "muted",
          text: "No active analysis jobs found in queue.",
        });
      }
    } else {
      newLogs.push({
        id: crypto.randomUUID(),
        type: "error",
        text: `command not found: ${cmd}. Type 'help' for available commands.`,
      });
    }

    setHistory(newLogs);
    setInputVal("");
  }

  return (
    <div
      className={cn(
        "rounded-lg border border-[#1e232a] bg-[#0c0e12] overflow-hidden font-mono-data shadow-2xl flex flex-col",
        className
      )}
    >
      {/* Terminal Title Bar (macOS style window buttons matching reference screenshot) */}
      <div className="h-9 bg-[#12151c] border-b border-[#1c2028] px-3.5 flex items-center justify-between shrink-0 select-none">
        {/* macOS Traffic Lights */}
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-[#ff5f56] inline-block hover:opacity-80 transition-opacity" />
          <span className="w-3 h-3 rounded-full bg-[#ffbd2e] inline-block hover:opacity-80 transition-opacity" />
          <span className="w-3 h-3 rounded-full bg-[#27c93f] inline-block hover:opacity-80 transition-opacity" />
        </div>

        {/* Subtitle / title */}
        <div className="text-[11px] text-[#525e70] font-medium tracking-tight">
          {subtitle}
        </div>
      </div>

      {/* Terminal Body */}
      <div
        className="p-4 text-[12px] space-y-3 overflow-y-auto max-h-[380px] min-h-[220px]"
        onClick={() => inputRef.current?.focus()}
      >
        {history.map((item) => {
          if (item.type === "input") {
            return (
              <div key={item.id} className="flex items-center gap-2 pt-1">
                <span className="text-[#38bdf8] font-bold select-none">$</span>
                <span className="text-[#fafafa] font-semibold">{item.text}</span>
              </div>
            );
          }

          if (item.type === "header") {
            return (
              <div key={item.id} className="text-[#38bdf8] font-bold pt-1">
                {item.text}
              </div>
            );
          }

          if (item.type === "row" && item.columns) {
            return (
              <div key={item.id} className="space-y-1 py-0.5">
                {item.columns.map((col) => (
                  <div
                    key={col.id}
                    className="grid grid-cols-[80px_140px_1fr_70px] gap-3 items-center text-[12px]"
                  >
                    <span className="text-[#64748b]">{col.id}</span>
                    <span className="text-[#e2e8f0] font-medium">{col.name}</span>
                    <span className="text-[#94a3b8] truncate">{col.desc}</span>
                    <span
                      className={cn(
                        "text-right text-[11px] font-medium",
                        col.status === "active" ? "text-[#4ade80]" : "text-[#38bdf8]"
                      )}
                    >
                      {col.status}
                    </span>
                  </div>
                ))}
              </div>
            );
          }

          if (item.type === "info") {
            return (
              <div key={item.id} className="text-[#38bdf8]">
                {item.text}
              </div>
            );
          }

          if (item.type === "success") {
            return (
              <div key={item.id} className="text-[#4ade80]">
                {item.text}
              </div>
            );
          }

          if (item.type === "error") {
            return (
              <div key={item.id} className="text-[#f87171]">
                {item.text}
              </div>
            );
          }

          return (
            <div key={item.id} className="text-[#64748b] text-[11px]">
              {item.text}
            </div>
          );
        })}

        {/* Input prompt line */}
        <form onSubmit={handleCommand} className="flex items-center gap-2 pt-1">
          <span className="text-[#38bdf8] font-bold select-none">$</span>
          <input
            ref={inputRef}
            type="text"
            value={inputVal}
            onChange={(e) => setInputVal(e.target.value)}
            placeholder="type 'help', 'status', or 'models'..."
            className="flex-1 bg-transparent text-[#fafafa] placeholder:text-[#334155] outline-none font-mono-data text-[12px]"
          />
        </form>
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
