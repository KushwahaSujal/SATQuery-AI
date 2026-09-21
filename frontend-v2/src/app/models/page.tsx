"use client";

import { useMemo, useState } from "react";
import { useModels } from "@/hooks/useSystem";
import type { ModelInfo } from "@/lib/types";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui";
import { AlertCircle, Boxes, Cpu, Loader2, Search } from "lucide-react";

/**
 * Lifecycle strings come straight from the registry (`load_state`/`status`) and are rendered
 * verbatim. The backend already emits states outside lib/types' ModelLifecycle union — e.g.
 * PRESENT_NOT_SERVING — so an unknown state must render as itself, never be coerced into a
 * friendlier label the backend did not claim.
 */
const SERVING_STATES = new Set(["AVAILABLE", "LOADED"]);

function statusClasses(status: string): string {
  if (status === "LOADED") return "text-[var(--green)] bg-[var(--green-bg)] border-[var(--green)]/25";
  if (status === "AVAILABLE") return "text-[var(--cyan)] bg-[var(--cyan-glow)] border-[var(--cyan)]/25";
  if (status === "FAILED") return "text-[var(--error)] bg-[var(--error-bg)] border-[var(--error)]/25";
  return "text-[var(--warning)] bg-[var(--warning-bg)] border-[var(--warning)]/25";
}

function validationClasses(status?: string): string {
  if (status === "VERIFIED") return "text-[var(--green)]";
  if (status === "PENDING_VERIFICATION") return "text-[var(--warning)]";
  return "text-[var(--text-3)]";
}

function Tile({ label, value, tone }: { label: string; value: string; tone: string }) {
  return (
    <div className="rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2">
      <p className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-3)]">
        {label}
      </p>
      <p className={`mt-1 font-mono-data text-sm ${tone}`}>{value}</p>
    </div>
  );
}

function ModelRow({ model }: { model: ModelInfo }) {
  const serving = SERVING_STATES.has(model.status);
  return (
    <div className="px-3 py-3 transition-colors hover:bg-[var(--surface-hover)]/40 sm:px-4">
      <div className="flex flex-wrap items-center gap-2">
        <span
          className={`status-dot shrink-0 ${
            serving ? "bg-[var(--green)]" : model.status === "FAILED" ? "bg-[var(--error)]" : "bg-[var(--warning)]"
          }`}
        />
        <span className="text-[13px] font-semibold text-[var(--heading)]">{model.name}</span>
        <span
          className={`rounded border px-1.5 py-0.5 font-mono-data text-[9px] uppercase tracking-wider ${statusClasses(
            model.status,
          )}`}
        >
          {model.status}
        </span>
        {model.device && (
          <span className="inline-flex items-center gap-1 font-mono-data text-[10px] text-[var(--text-3)]">
            <Cpu className="h-3 w-3" />
            {model.device}
          </span>
        )}
        {model.validation_status && (
          <span
            className={`font-mono-data text-[10px] ${validationClasses(model.validation_status)}`}
            title="validation_status as recorded by the registry"
          >
            {model.validation_status.toLowerCase().replace(/_/g, " ")}
          </span>
        )}
      </div>

      {model.description && (
        <p className="mt-1.5 font-mono-data text-[10px] leading-relaxed text-[var(--text-3)]">
          {model.description}
        </p>
      )}

      {model.capabilities && model.capabilities.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {model.capabilities.map((task) => (
            <span
              key={task}
              className="rounded border border-[var(--border)] bg-[var(--surface-2)] px-1.5 py-0.5 font-mono-data text-[9px] text-[var(--text-2)]"
            >
              {task}
            </span>
          ))}
        </div>
      )}

      {!serving && (
        <p className="mt-2 rounded-md border border-[var(--warning)]/25 bg-[var(--warning-bg)] px-2.5 py-1.5 text-[11px] text-[var(--text-2)]">
          Reported as <span className="font-mono-data">{model.status}</span> — the planner will not
          route work to it. The registry records a machine-readable refusal reason for this state,
          which the frontend API layer does not currently expose, so none is shown here rather than
          guessed.
        </p>
      )}

      {model.last_error && (
        <p className="mt-2 flex items-start gap-1.5 rounded-md border border-[var(--error)]/25 bg-[var(--error-bg)] px-2.5 py-1.5 font-mono-data text-[10px] break-words text-[var(--error)]">
          <AlertCircle className="mt-0.5 h-3 w-3 shrink-0" />
          {model.last_error}
        </p>
      )}
    </div>
  );
}

export default function ModelsPage() {
  const models = useModels();
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const registry = models.data ?? [];

  const statuses = useMemo(() => {
    const seen = new Map<string, number>();
    for (const m of registry) seen.set(m.status, (seen.get(m.status) ?? 0) + 1);
    return [...seen.entries()].sort((a, b) => b[1] - a[1]);
  }, [registry]);

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return registry.filter((m) => {
      if (statusFilter !== "all" && m.status !== statusFilter) return false;
      if (!needle) return true;
      const haystack = [m.name, m.task, m.device, m.description, ...(m.capabilities ?? [])]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return haystack.includes(needle);
    });
  }, [registry, query, statusFilter]);

  const grouped = useMemo(() => {
    const byTask = new Map<string, ModelInfo[]>();
    for (const m of filtered) {
      const key = m.task || "unspecified";
      const list = byTask.get(key);
      if (list) list.push(m);
      else byTask.set(key, [m]);
    }
    return [...byTask.entries()].sort((a, b) => a[0].localeCompare(b[0]));
  }, [filtered]);

  const serving = registry.filter((m) => SERVING_STATES.has(m.status));
  const verified = registry.filter((m) => m.validation_status === "VERIFIED");

  return (
    <div className="h-screen flex flex-col bg-[var(--canvas)] text-[var(--text)] font-sans antialiased overflow-hidden">
      <TopBar showBrand={true} />

      <div className="flex flex-1 overflow-hidden">
        <Sidebar hideBrand={true} activeItem="models" className="h-full" />

        <main className="flex-1 overflow-y-auto bg-[var(--canvas)] p-4 sm:p-6 space-y-5">
          {/* Header */}
          <div className="flex items-start gap-3">
            <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-[var(--border)] bg-[var(--surface-2)] text-[var(--cyan)]">
              <Boxes className="h-4 w-4" />
            </div>
            <div className="min-w-0">
              <h1 className="text-lg font-bold tracking-tight text-[var(--heading)]">
                Model registry
              </h1>
              <p className="mt-0.5 text-xs text-[var(--text-3)]">
                Every model record the backend exposes at{" "}
                <span className="font-mono-data">/api/models</span>, with the lifecycle and
                validation state it reports. No scores or benchmarks are shown because the registry
                does not publish any.
              </p>
            </div>
          </div>

          {/* Summary */}
          {registry.length > 0 && (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <Tile label="Records" value={String(registry.length)} tone="text-[var(--text)]" />
              <Tile
                label="Serving"
                value={`${serving.length} / ${registry.length}`}
                tone={serving.length === registry.length ? "text-[var(--green)]" : "text-[var(--warning)]"}
              />
              <Tile
                label="Not serving"
                value={String(registry.length - serving.length)}
                tone={registry.length - serving.length > 0 ? "text-[var(--warning)]" : "text-[var(--green)]"}
              />
              <Tile
                label="Verified"
                value={`${verified.length} / ${registry.length}`}
                tone={verified.length > 0 ? "text-[var(--text)]" : "text-[var(--text-3)]"}
              />
            </div>
          )}

          {/* Controls */}
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
            <div className="relative flex-1 min-w-0">
              <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-[var(--text-3)]" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Filter by name, task, capability or device…"
                className="w-full rounded-lg border border-[var(--border)] bg-[var(--surface)] py-1.5 pl-9 pr-3 text-xs text-[var(--text)] placeholder-[var(--text-3)] focus:border-[var(--cyan)]/40 focus:outline-none"
              />
            </div>

            <div className="-mx-1 flex items-center gap-1.5 overflow-x-auto px-1 pb-1 lg:pb-0">
              <button
                type="button"
                onClick={() => setStatusFilter("all")}
                className={`shrink-0 rounded-lg px-2.5 py-1.5 text-[11px] font-semibold transition ${
                  statusFilter === "all"
                    ? "border border-[var(--cyan)]/40 bg-[var(--cyan-glow)] text-[var(--cyan)]"
                    : "border border-transparent text-[var(--text-3)] hover:bg-[var(--surface-hover)] hover:text-[var(--text)]"
                }`}
              >
                All {registry.length > 0 ? `· ${registry.length}` : ""}
              </button>
              {statuses.map(([status, count]) => (
                <button
                  key={status}
                  type="button"
                  onClick={() => setStatusFilter(status)}
                  className={`shrink-0 rounded-lg px-2.5 py-1.5 font-mono-data text-[10px] uppercase tracking-wider transition ${
                    statusFilter === status
                      ? "border border-[var(--cyan)]/40 bg-[var(--cyan-glow)] text-[var(--cyan)]"
                      : "border border-transparent text-[var(--text-3)] hover:bg-[var(--surface-hover)] hover:text-[var(--text)]"
                  }`}
                >
                  {status} · {count}
                </button>
              ))}
            </div>
          </div>

          {/* List */}
          {models.isError ? (
            <Card>
              <CardContent className="flex items-start gap-2 pt-4 text-xs">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-[var(--error)]" />
                <div>
                  <p className="font-semibold text-[var(--heading)]">Could not load the registry</p>
                  <p className="mt-0.5 font-mono-data text-[10px] break-words text-[var(--text-2)]">
                    {models.error instanceof Error ? models.error.message : String(models.error)}
                  </p>
                </div>
              </CardContent>
            </Card>
          ) : models.isLoading ? (
            <Card>
              <CardContent className="flex items-center gap-2 pt-4 text-xs text-[var(--text-3)]">
                <Loader2 className="h-4 w-4 animate-spin text-[var(--cyan)]" />
                Loading model registry…
              </CardContent>
            </Card>
          ) : registry.length === 0 ? (
            <Card>
              <CardContent className="pt-4 text-xs text-[var(--text-3)]">
                The backend returned no model records.
              </CardContent>
            </Card>
          ) : filtered.length === 0 ? (
            <Card>
              <CardContent className="pt-4 text-xs text-[var(--text-3)]">
                No model matches this filter.
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-4">
              {grouped.map(([task, group]) => (
                <Card key={task} className="overflow-hidden">
                  <CardHeader className="flex-row items-center justify-between gap-2 space-y-0 border-b border-[var(--border)] bg-[var(--surface-2)]/40">
                    <CardTitle className="font-mono-data text-[11px] uppercase tracking-wider text-[var(--text-2)]">
                      {task}
                    </CardTitle>
                    <span className="font-mono-data text-[10px] text-[var(--text-3)]">
                      {group.length} model{group.length === 1 ? "" : "s"}
                    </span>
                  </CardHeader>
                  <CardContent className="divide-y divide-[var(--border)] p-0">
                    {group.map((model) => (
                      <ModelRow key={model.name} model={model} />
                    ))}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          {/* Honest scope note */}
          {registry.length > 0 && (
            <p className="text-[11px] leading-relaxed text-[var(--text-3)]">
              Scope: this page shows the fields the frontend API layer keeps when it maps{" "}
              <span className="font-mono-data">/api/models</span> into{" "}
              <span className="font-mono-data">ModelInfo</span>. The backend also returns{" "}
              <span className="font-mono-data">model_id</span>,{" "}
              <span className="font-mono-data">family</span>,{" "}
              <span className="font-mono-data">version</span>,{" "}
              <span className="font-mono-data">adapter</span>,{" "}
              <span className="font-mono-data">checkpoint</span>,{" "}
              <span className="font-mono-data">license</span>,{" "}
              <span className="font-mono-data">precision</span>,{" "}
              <span className="font-mono-data">input_requirements</span>,{" "}
              <span className="font-mono-data">output_schema</span>,{" "}
              <span className="font-mono-data">device_requirements</span> and{" "}
              <span className="font-mono-data">refusal_reason</span> per model; those are dropped
              before they reach this page and are therefore not displayed.
            </p>
          )}
        </main>
      </div>
    </div>
  );
}
