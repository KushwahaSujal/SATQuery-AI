"use client";

import { useRef, useState } from "react";
import { authHeaders, getApiBase, setConnection, useConnection } from "@/lib/connection";

type Check = { state: "idle" | "checking" | "waking" | "ok" | "error"; detail?: string };

const SCHEME = /^https?:\/\//i;

/**
 * Uncontrolled inputs, remounted (via the `key` the caller passes) whenever the stored
 * base/key changes from outside this render — e.g. right after hydration, when the real
 * localStorage values replace the server-rendered defaults, or when another tab saves a
 * different connection. Remounting resets `defaultValue`; it does not touch ConnectionPanel's
 * own `check` state, so an in-flight "Save & test" (which itself triggers this same resync,
 * with the values it just saved) never loses its status mid-flight.
 */
function ConnectionInputs({
  base,
  apiKey,
  baseRef,
  keyRef,
}: {
  base: string;
  apiKey: string;
  baseRef: React.RefObject<HTMLInputElement | null>;
  keyRef: React.RefObject<HTMLInputElement | null>;
}) {
  return (
    <>
      <input
        ref={baseRef}
        className="w-full bg-transparent border border-[#262626] rounded px-2 py-1 font-mono-data text-[11px] text-[#d4d4d4]"
        defaultValue={base}
        placeholder="https://…modal.run or http://localhost:8000"
      />
      <input
        ref={keyRef}
        className="w-full bg-transparent border border-[#262626] rounded px-2 py-1 font-mono-data text-[11px] text-[#d4d4d4]"
        defaultValue={apiKey}
        type="password"
        placeholder="API key (empty for local)"
      />
    </>
  );
}

export default function ConnectionPanel() {
  const { base, key } = useConnection();
  const [check, setCheck] = useState<Check>({ state: "idle" });
  const baseRef = useRef<HTMLInputElement>(null);
  const keyRef = useRef<HTMLInputElement>(null);

  const save = async () => {
    const nextBase = (baseRef.current?.value ?? "").trim();
    const nextKey = (keyRef.current?.value ?? "").trim();

    if (!SCHEME.test(nextBase)) {
      setCheck({ state: "error", detail: "URL must start with http:// or https://" });
      return;
    }

    setConnection(nextBase, nextKey);
    setCheck({ state: "checking" });
    const started = performance.now();
    const waking = setTimeout(() => setCheck({ state: "waking" }), 3000);
    try {
      // /api/health is an open path (no auth required) — a network error or non-2xx here means
      // the backend itself is unreachable, distinct from an API-key problem on the probe below.
      const health = await fetch(`${getApiBase()}/api/health`);
      if (!health.ok) {
        setCheck({ state: "error", detail: `backend unreachable at ${getApiBase()}` });
        return;
      }
      const r = await fetch(`${getApiBase()}/api/results/connection-check`, { headers: authHeaders() });
      const secs = ((performance.now() - started) / 1000).toFixed(1);
      if (r.status === 401) {
        setCheck({ state: "error", detail: "API key rejected" });
      } else if (r.status === 404 || r.status === 400) {
        // The connection-check route itself returns 404/400 for a nonexistent probe id — that's
        // expected and proves auth + routing both work, not a failure.
        setCheck({ state: "ok", detail: `reachable in ${secs}s` });
      } else {
        setCheck({ state: "error", detail: `unexpected status ${r.status}` });
      }
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
      <ConnectionInputs key={`${base}::${key ?? ""}`} base={base} apiKey={key ?? ""} baseRef={baseRef} keyRef={keyRef} />
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
