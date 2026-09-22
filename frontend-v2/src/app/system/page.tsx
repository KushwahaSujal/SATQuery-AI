"use client";

import Link from "next/link";
import { useMemo } from "react";
import { useHealth, useModels } from "@/hooks/useSystem";
import { API_BASE } from "@/lib/endpoints";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui";
import {
  AlertCircle,
  CheckCircle2,
  Cpu,
  Database,
  Loader2,
  RefreshCw,
  Server,
  XCircle,
} from "lucide-react";

type Tone = "ok" | "warn" | "bad" | "idle";

const TONE_TEXT: Record<Tone, string> = {
  ok: "text-[var(--green)]",
  warn: "text-[var(--warning)]",
  bad: "text-[var(--error)]",
  idle: "text-[var(--text-2)]",
};

const TONE_DOT: Record<Tone, string> = {
  ok: "bg-[var(--green)]",
  warn: "bg-[var(--warning)]",
  bad: "bg-[var(--error)]",
  idle: "bg-[var(--text-4)]",
};

function StatTile({
  icon,
  label,
  value,
  detail,
  tone,
  live = false,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  detail?: string;
  tone: Tone;
  live?: boolean;
}) {
  return (
    <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-3.5">
      <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-wider text-[var(--text-3)]">
        <span className="text-[var(--text-3)]">{icon}</span>
        <span className="truncate">{label}</span>
      </div>
      <div className="mt-2 flex items-center gap-2">
        {/* Glow is reserved for a live, healthy signal — never decoration. */}
        <span
          className={`status-dot ${TONE_DOT[tone]} ${live ? "animate-pulse-dot" : ""}`}
          style={live ? { boxShadow: "0 0 8px var(--green)" } : undefined}
        />
        <span className={`text-sm font-semibold ${TONE_TEXT[tone]}`}>{value}</span>
      </div>
      {detail && (
        <p className="mt-1 font-mono-data text-[10px] text-[var(--text-3)] break-words">{detail}</p>
      )}
    </div>
  );
}

function checkedAt(timestamp: number): string {
  if (!timestamp) return "not yet checked";
  try {
    return new Date(timestamp).toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return "not yet checked";
  }
}

export default function SystemPage() {
  const health = useHealth();
  const models = useModels();

  const data = health.data;
  const busy = health.isFetching || models.isFetching;

  const availability = useMemo(
    () => Object.entries(data?.models_available ?? {}),
    [data?.models_available],
  );
  const readyCount = availability.filter(([, ok]) => ok).length;

  const registry = models.data ?? [];
  const notServing = registry.filter(
    (m) => m.status !== "AVAILABLE" && m.status !== "LOADED",
  );

  // Reachability is decided only by what the health probe actually returned.
  const apiTone: Tone = health.isError
    ? "bad"
    : !data
      ? "idle"
      : data.api === "online"
        ? "ok"
        : "warn";
  const apiValue = health.isError
    ? "Unreachable"
    : !data
      ? health.isLoading
        ? "Checking…"
        : "Unknown"
      : data.api === "online"
        ? "Online"
        : "Degraded";

  const dbTone: Tone = !data ? "idle" : data.database_connected ? "ok" : "bad";
  const deviceTone: Tone = !data ? "idle" : data.device ? "ok" : "warn";

  return (
    <div className="h-screen flex flex-col bg-[var(--canvas)] text-[var(--text)] font-sans antialiased overflow-hidden">
      <TopBar showBrand={true} />

      <div className="flex flex-1 overflow-hidden">
        <Sidebar hideBrand={true} activeItem="system" className="h-full" />

        <main className="flex-1 overflow-y-auto bg-[var(--canvas)] p-4 sm:p-6 space-y-5">
          {/* Header */}
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div className="flex items-start gap-3">
              <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-[var(--border)] bg-[var(--surface-2)] text-[var(--cyan)]">
                <Server className="h-4 w-4" />
              </div>
              <div className="min-w-0">
                <h1 className="text-lg font-bold tracking-tight text-[var(--heading)]">
                  System diagnostics
                </h1>
                <p className="mt-0.5 text-xs text-[var(--text-3)]">
                  Live backend, database and checkpoint state, read from{" "}
                  <span className="font-mono-data">/api/health</span> and{" "}
                  <span className="font-mono-data">/api/models</span>. Nothing on this page is cached
                  or synthesised.
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={() => {
                health.refetch();
                models.refetch();
              }}
              disabled={busy}
              className="inline-flex shrink-0 items-center gap-2 rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-3 py-1.5 text-xs font-medium text-[var(--text)] transition hover:border-[var(--border-strong)] hover:bg-[var(--surface-hover)] disabled:opacity-60"
            >
              {busy ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin text-[var(--cyan)]" />
              ) : (
                <RefreshCw className="h-3.5 w-3.5 text-[var(--text-3)]" />
              )}
              Re-check now
            </button>
          </div>

          {/* Connection */}
          <Card>
            <CardHeader className="flex-row items-center justify-between gap-3 space-y-0">
              <CardTitle>Backend connection</CardTitle>
              <span className="font-mono-data text-[10px] text-[var(--text-3)]">
                last checked {checkedAt(health.dataUpdatedAt || health.errorUpdatedAt)}
              </span>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="overflow-x-auto">
                <div className="flex min-w-0 items-center gap-2 rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2">
                  <span className="shrink-0 text-[10px] font-semibold uppercase tracking-wider text-[var(--text-3)]">
                    API base
                  </span>
                  <code className="font-mono-data text-[11px] whitespace-nowrap text-[var(--text)]">
                    {API_BASE}
                  </code>
                </div>
              </div>
              <p className="text-[11px] text-[var(--text-3)]">
                The base URL is fixed at build time by{" "}
                <span className="font-mono-data">NEXT_PUBLIC_API_BASE_URL</span>. This build has no
                runtime connection store, so it cannot be re-pointed or given an API key from the
                browser.
              </p>

              {health.isError && (
                <div className="flex items-start gap-2 rounded-md border border-[var(--error)]/30 bg-[var(--error-bg)] px-3 py-2">
                  <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[var(--error)]" />
                  <div className="min-w-0">
                    <p className="text-xs font-semibold text-[var(--error)]">
                      Health probe failed
                    </p>
                    <p className="mt-0.5 font-mono-data text-[10px] break-words text-[var(--text-2)]">
                      {health.error instanceof Error ? health.error.message : String(health.error)}
                    </p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Health tiles */}
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <StatTile
              icon={<Server className="h-3.5 w-3.5" />}
              label="API gateway"
              value={apiValue}
              detail={data?.version ? `version ${data.version}` : undefined}
              tone={apiTone}
              live={apiTone === "ok"}
            />
            <StatTile
              icon={<Database className="h-3.5 w-3.5" />}
              label="Database"
              value={
                !data ? (health.isLoading ? "Checking…" : "Unknown") : data.database_connected ? "Connected" : "Disconnected"
              }
              detail={data ? `database_connected = ${String(data.database_connected)}` : undefined}
              tone={dbTone}
            />
            <StatTile
              icon={<Cpu className="h-3.5 w-3.5" />}
              label="Compute device"
              value={data?.device ? data.device.toUpperCase() : health.isLoading ? "Checking…" : "Unknown"}
              detail={data?.device ? "reported by the inference runtime" : undefined}
              tone={deviceTone}
            />
            <StatTile
              icon={<CheckCircle2 className="h-3.5 w-3.5" />}
              label="Checkpoints available"
              value={
                availability.length > 0
                  ? `${readyCount} / ${availability.length}`
                  : health.isLoading
                    ? "Checking…"
                    : "None reported"
              }
              detail={data?.environment ? `environment: ${data.environment}` : undefined}
              tone={
                availability.length === 0
                  ? "idle"
                  : readyCount === availability.length
                    ? "ok"
                    : readyCount > 0
                      ? "warn"
                      : "bad"
              }
            />
          </div>

          {/* Checkpoint availability */}
          <Card>
            <CardHeader className="flex-row flex-wrap items-center justify-between gap-2 space-y-0">
              <CardTitle>Checkpoint availability per model</CardTitle>
              <span className="font-mono-data text-[10px] text-[var(--text-3)]">
                health.models_available · {availability.length} entries
              </span>
            </CardHeader>
            <CardContent className="space-y-3">
              {availability.length === 0 ? (
                <p className="text-xs text-[var(--text-3)]">
                  {health.isLoading
                    ? "Loading availability map…"
                    : health.isError
                      ? "Unavailable — the health probe did not answer."
                      : "The backend reported no models_available map."}
                </p>
              ) : (
                <>
                  <div className="overflow-x-auto">
                    <table className="w-full min-w-[420px] border-collapse text-left">
                      <thead>
                        <tr className="border-b border-[var(--border)] text-[10px] font-semibold uppercase tracking-wider text-[var(--text-3)]">
                          <th className="px-2 py-2">model_id</th>
                          <th className="px-2 py-2 text-right">checkpoint</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[var(--border)] text-xs">
                        {availability.map(([modelId, ok]) => (
                          <tr key={modelId} className="hover:bg-[var(--surface-hover)]/40">
                            <td className="px-2 py-1.5 font-mono-data text-[11px] text-[var(--text)]">
                              {modelId}
                            </td>
                            <td className="px-2 py-1.5 text-right">
                              <span
                                className={`inline-flex items-center gap-1.5 font-mono-data text-[10px] ${
                                  ok ? "text-[var(--green)]" : "text-[var(--text-3)]"
                                }`}
                              >
                                {ok ? (
                                  <CheckCircle2 className="h-3 w-3" />
                                ) : (
                                  <XCircle className="h-3 w-3" />
                                )}
                                {ok ? "available" : "unavailable"}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <p className="text-[11px] text-[var(--text-3)]">
                    &quot;Available&quot; here is the health probe&apos;s own flag: the checkpoint is
                    present and loadable. It is not a promise that the model will serve a
                    prediction — the registry tracks serving state separately.
                  </p>
                </>
              )}
            </CardContent>
          </Card>

          {/* Registry cross-check */}
          <Card>
            <CardHeader className="flex-row flex-wrap items-center justify-between gap-2 space-y-0">
              <CardTitle>Registry cross-check</CardTitle>
              <Link
                href="/models"
                className="font-mono-data text-[10px] text-[var(--cyan)] hover:underline"
              >
                open model registry →
              </Link>
            </CardHeader>
            <CardContent>
              {models.isError ? (
                <div className="flex items-start gap-2 text-xs">
                  <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[var(--error)]" />
                  <span className="text-[var(--text-2)]">
                    {models.error instanceof Error ? models.error.message : "Could not load /api/models."}
                  </span>
                </div>
              ) : models.isLoading ? (
                <p className="text-xs text-[var(--text-3)]">Loading registry…</p>
              ) : registry.length === 0 ? (
                <p className="text-xs text-[var(--text-3)]">
                  The registry returned no model records.
                </p>
              ) : (
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                  <div className="rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2">
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-3)]">
                      Registry records
                    </p>
                    <p className="mt-1 font-mono-data text-sm text-[var(--text)]">{registry.length}</p>
                  </div>
                  <div className="rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2">
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-3)]">
                      Health entries
                    </p>
                    <p className="mt-1 font-mono-data text-sm text-[var(--text)]">
                      {availability.length}
                    </p>
                  </div>
                  <div className="rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2">
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-3)]">
                      Not serving
                    </p>
                    <p
                      className={`mt-1 font-mono-data text-sm ${
                        notServing.length > 0 ? "text-[var(--warning)]" : "text-[var(--green)]"
                      }`}
                    >
                      {notServing.length}
                    </p>
                  </div>
                </div>
              )}

              {notServing.length > 0 && (
                <ul className="mt-3 space-y-1">
                  {notServing.map((m) => (
                    <li
                      key={m.name}
                      className="flex flex-wrap items-center gap-2 rounded-md border border-[var(--warning)]/25 bg-[var(--warning-bg)] px-2.5 py-1.5 text-[11px]"
                    >
                      <span className="font-semibold text-[var(--heading)]">{m.name}</span>
                      <span className="font-mono-data text-[10px] text-[var(--warning)]">
                        {m.status}
                      </span>
                      {m.task && (
                        <span className="font-mono-data text-[10px] text-[var(--text-3)]">
                          {m.task}
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </main>
      </div>
    </div>
  );
}
