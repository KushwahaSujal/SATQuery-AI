"use client";

import { useState } from "react";
import { authHeaders, getApiBase, getApiKey, setConnection } from "@/lib/connection";

type Check = { state: "idle" | "checking" | "waking" | "ok" | "error"; detail?: string };

export default function ConnectionPanel() {
  const [base, setBase] = useState(() => getApiBase());
  const [key, setKey] = useState(() => getApiKey() ?? "");
  const [check, setCheck] = useState<Check>({ state: "idle" });

  const save = async () => {
    setConnection(base, key);
    setCheck({ state: "checking" });
    const started = performance.now();
    const waking = setTimeout(() => setCheck({ state: "waking" }), 3000);
    try {
      const r = await fetch(`${getApiBase()}/api/results/connection-check`, { headers: authHeaders() });
      const secs = ((performance.now() - started) / 1000).toFixed(1);
      if (r.status === 401) setCheck({ state: "error", detail: "API key rejected" });
      else setCheck({ state: "ok", detail: `reachable in ${secs}s` });
    } catch {
      setCheck({ state: "error", detail: `backend unreachable at ${getApiBase()}` });
    } finally {
      clearTimeout(waking);
    }
  };

  const status =
    check.state === "waking" ? "Waking GPU (~60 s)…"
    : check.state === "checking" ? "Checking…"
    : check.state === "ok" ? `Connected · ${check.detail}`
    : check.state === "error" ? `Not connected · ${check.detail}`
    : "";

  return (
    <div className="border border-[#1a1a1a] rounded p-4 space-y-2" data-testid="connection-panel">
      <p className="font-mono-data text-[11px] text-[#737373] m-0">Backend connection</p>
      <input className="w-full bg-transparent border border-[#262626] rounded px-2 py-1 font-mono-data text-[11px] text-[#d4d4d4]"
             value={base} onChange={(e) => setBase(e.target.value)} placeholder="https://…modal.run or http://localhost:8000" />
      <input className="w-full bg-transparent border border-[#262626] rounded px-2 py-1 font-mono-data text-[11px] text-[#d4d4d4]"
             value={key} onChange={(e) => setKey(e.target.value)} type="password" placeholder="API key (empty for local)" />
      <div className="flex items-center gap-3">
        <button type="button" onClick={save}
                className="font-mono-data text-[11px] border border-[#262626] rounded px-2.5 py-1 text-[#d4d4d4] hover:border-[#404040]">
          Save &amp; test
        </button>
        <span className="font-mono-data text-[11px] text-[#a3a3a3]" data-testid="connection-status">{status}</span>
      </div>
    </div>
  );
}
