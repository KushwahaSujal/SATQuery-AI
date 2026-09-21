"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import Sidebar from "@/components/layout/Sidebar";
import TopBar from "@/components/layout/TopBar";
import { SpotlightCard } from "@/components/ui/spotlight-card";
import {
  CATEGORY_COUNTS,
  CATALOGUED_FILE_COUNT,
  DEMO_CATEGORIES,
  DEMO_RESOURCES,
  MEASUREMENT_PROVENANCE,
  ROUTING_NOTE,
  demoResourceUrl,
  formatBytes,
  isVideoPath,
  type DemoCategoryId,
  type DemoFile,
  type DemoResource,
} from "@/lib/demoResources";

const stagger = { hidden: {}, show: { transition: { staggerChildren: 0.05, delayChildren: 0.05 } } };
const cardVariant = {
  hidden: { opacity: 0, y: 14, scale: 0.98 },
  show: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { duration: 0.35, ease: [0.22, 1, 0.36, 1] as [number, number, number, number] },
  },
};

const README_URL = demoResourceUrl("README.md");

function categoryLabel(id: DemoCategoryId): string {
  return DEMO_CATEGORIES.find((c) => c.id === id)?.label ?? id;
}

function isKnownWeak(id: DemoCategoryId): boolean {
  return DEMO_CATEGORIES.find((c) => c.id === id)?.knownWeak === true;
}

/** Renders a preview for a demo file: image, video, or an honest "cannot preview" state. */
function Preview({
  path,
  className,
  rounded = "rounded-lg",
}: {
  path?: string;
  className?: string;
  rounded?: string;
}) {
  if (!path) {
    return (
      <div
        className={`${className} ${rounded} flex items-center justify-center bg-[var(--surface-3)] border border-[var(--border)] px-3 text-center`}
      >
        <span className="text-[10px] text-[var(--text-3)]">No previewable file</span>
      </div>
    );
  }

  if (isVideoPath(path)) {
    return (
      <video
        src={demoResourceUrl(path)}
        className={`${className} ${rounded} bg-[var(--surface-3)] border border-[var(--border)] object-cover`}
        controls
        muted
        playsInline
        preload="metadata"
      />
    );
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={demoResourceUrl(path)}
      alt={path}
      loading="lazy"
      className={`${className} ${rounded} bg-[var(--surface-3)] border border-[var(--border)] object-cover`}
    />
  );
}

function KnownWeakBadge() {
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-[var(--amber)]/40 bg-[var(--amber-bg)] px-2 py-0.5 text-[10px] font-semibold text-[var(--amber)]">
      <svg className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
        <path d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      Known weak
    </span>
  );
}

function FileRow({ file }: { file: DemoFile }) {
  return (
    <li className="flex items-start justify-between gap-3 border-b border-[var(--border)] py-2 last:border-b-0">
      <div className="min-w-0">
        <div className="truncate text-[11px] font-medium text-[var(--text)]">{file.label}</div>
        <div className="break-all font-mono text-[10px] text-[var(--text-3)]">{file.path}</div>
        <div className="mt-0.5 flex flex-wrap items-center gap-2 text-[10px] text-[var(--text-3)]">
          <span>{formatBytes(file.bytes)}</span>
          {file.pixels && <span>{file.pixels} px</span>}
          {!file.previewable && (
            <span className="rounded border border-[var(--amber)]/40 bg-[var(--amber-bg)] px-1.5 py-0.5 font-medium text-[var(--amber)]">
              {file.path.toLowerCase().endsWith(".geojson") ? "GeoJSON — not an image" : "GeoTIFF — not previewable in browser"}
            </span>
          )}
        </div>
      </div>
      <a
        href={demoResourceUrl(file.path)}
        download
        className="mt-0.5 shrink-0 rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-2 py-1 text-[10px] font-medium text-[var(--text-2)] transition-colors hover:border-[var(--cyan)] hover:text-[var(--cyan)]"
      >
        Download
      </a>
    </li>
  );
}

export default function DatasetsPage() {
  const [selectedCategory, setSelectedCategory] = useState<DemoCategoryId | "all">("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [selectedId, setSelectedId] = useState<string>(DEMO_RESOURCES[0].id);
  const [preview, setPreview] = useState<{ entryId: string; path: string; caption: string } | null>(null);

  const query = searchQuery.trim().toLowerCase();

  const filtered = useMemo(() => {
    return DEMO_RESOURCES.filter((entry) => {
      const matchesCategory = selectedCategory === "all" || entry.category === selectedCategory;
      if (!matchesCategory) return false;
      if (!query) return true;
      const haystack = [
        entry.name,
        entry.folder,
        entry.provenance,
        entry.description ?? "",
        entry.failure ?? "",
        categoryLabel(entry.category),
        ...entry.runs.map((r) => `${r.prompt} ${r.result} ${r.note ?? ""}`),
        ...entry.files.map((f) => f.path),
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(query);
    });
  }, [selectedCategory, query]);

  const selected: DemoResource | undefined =
    filtered.find((e) => e.id === selectedId) ?? filtered[0] ?? DEMO_RESOURCES.find((e) => e.id === selectedId);

  const shownFileCount = filtered.reduce((total, entry) => total + entry.files.length, 0);

  const activePreview =
    selected && preview && preview.entryId === selected.id
      ? preview
      : selected
        ? { entryId: selected.id, path: selected.thumbnail ?? "", caption: selected.thumbnailCaption ?? "Input file" }
        : null;

  const pills: Array<{ id: DemoCategoryId | "all"; label: string; count: number; weak?: boolean }> = [
    { id: "all", label: "All", count: DEMO_RESOURCES.length },
    ...DEMO_CATEGORIES.map((c) => ({
      id: c.id as DemoCategoryId | "all",
      label: c.label,
      count: CATEGORY_COUNTS[c.id],
      weak: c.knownWeak,
    })),
  ];

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.35 }}
      className="flex h-screen flex-col overflow-hidden bg-[var(--canvas)] font-sans text-[var(--text)] antialiased selection:bg-[var(--cyan-glow)] selection:text-[var(--cyan)]"
    >
      <TopBar
        showBrand={true}
        searchPlaceholder="Search demo resources by name, prompt or file..."
        onSearch={(q) => setSearchQuery(q)}
      />

      <div className="flex flex-1 overflow-hidden">
        <Sidebar hideBrand={true} activeItem="datasets" className="h-full" />

        <div className="flex min-w-0 flex-1 flex-col overflow-y-auto lg:flex-row lg:overflow-hidden">
          <main className="min-w-0 flex-1 px-4 py-5 sm:px-6 lg:overflow-y-auto" data-purpose="demo-resources-workspace">
            {/* Header */}
            <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div className="min-w-0">
                <h1 className="mb-1 text-2xl font-bold tracking-tight text-[var(--heading)]">Demo resources</h1>
                <p className="max-w-2xl text-xs text-[var(--text-3)]">
                  The sample imagery, image pairs and videos committed to this repository under{" "}
                  <span className="font-mono text-[var(--text-2)]">demo_resources/</span> —{" "}
                  {DEMO_RESOURCES.length} entries over {CATALOGUED_FILE_COUNT} files (35 MB on disk). This is the repo&apos;s own
                  demo data, served straight from the working tree. It is not a live catalog and there is no dataset API
                  behind it.
                </p>
              </div>
              <Link
                href="/analysis"
                className="inline-flex shrink-0 items-center justify-center gap-2 rounded-lg bg-[var(--cyan)] px-4 py-2 text-xs font-semibold text-[var(--canvas)] shadow-[0_0_15px_var(--cyan-glow)] transition hover:opacity-90"
              >
                <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                  <path d="M12 4v16m8-8H4" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                <span>Run an analysis</span>
              </Link>
            </div>

            {/* Provenance */}
            <div className="mb-4 rounded-xl border border-[var(--border)] bg-[var(--surface)] p-3.5 text-[11px] leading-relaxed text-[var(--text-2)]">
              <p>{MEASUREMENT_PROVENANCE}</p>
              <p className="mt-1.5 text-[var(--text-3)]">{ROUTING_NOTE}</p>
              <p className="mt-1.5">
                Prompts, results and caveats on this page are quoted from{" "}
                <a
                  href={README_URL}
                  target="_blank"
                  rel="noreferrer"
                  className="font-mono text-[var(--cyan)] underline decoration-dotted underline-offset-2"
                >
                  demo_resources/README.md
                </a>
                . Fields the README does not state — acquisition dates for the VRSBench scenes, ground resolution, sensor,
                cloud cover, licence, accuracy — are left out rather than guessed.
              </p>
            </div>

            {/* Category filters — counts are computed from the catalog itself */}
            <div className="mb-3 flex items-center gap-2 overflow-x-auto pb-1" data-purpose="category-filters">
              {pills.map((pill) => {
                const active = selectedCategory === pill.id;
                return (
                  <button
                    key={pill.id}
                    onClick={() => setSelectedCategory(pill.id)}
                    className={`flex shrink-0 cursor-pointer items-center gap-2 rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                      active
                        ? "border border-[var(--cyan)]/50 bg-[var(--cyan-glow)] text-[var(--cyan)]"
                        : "border border-[var(--border)] bg-[var(--surface-2)] text-[var(--text-2)] hover:border-[var(--border-strong)]"
                    }`}
                  >
                    <span className={pill.weak && !active ? "text-[var(--amber)]" : undefined}>{pill.label}</span>
                    <span
                      className={`rounded-full px-1.5 text-[10px] ${
                        active ? "bg-[var(--cyan-glow)] text-[var(--cyan)]" : "bg-[var(--surface-3)] text-[var(--text-3)]"
                      }`}
                    >
                      {pill.count}
                    </span>
                  </button>
                );
              })}
            </div>

            {/* Search + view switcher */}
            <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
              <div className="relative min-w-[200px] max-w-xs flex-1">
                <svg
                  className="absolute left-3 top-2.5 h-3.5 w-3.5 text-[var(--text-3)]"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <circle cx="11" cy="11" r="8" />
                  <line x1="21" x2="16.65" y1="21" y2="16.65" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                <input
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full rounded-lg border border-[var(--border)] bg-[var(--surface-2)] py-1.5 pl-9 pr-3 text-xs text-[var(--text)] placeholder-[var(--text-3)] focus:border-[var(--cyan)] focus:outline-none"
                  placeholder="Search name, prompt, file path..."
                  type="text"
                />
              </div>

              <div className="flex items-center rounded-lg border border-[var(--border)] bg-[var(--surface-2)] p-0.5">
                <button
                  onClick={() => setViewMode("grid")}
                  className={`rounded p-1 transition ${viewMode === "grid" ? "bg-[var(--surface-3)] text-[var(--cyan)]" : "text-[var(--text-3)] hover:text-[var(--text)]"}`}
                  title="Grid view"
                  aria-pressed={viewMode === "grid"}
                >
                  <svg className="h-3.5 w-3.5" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M5 3a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2V5a2 2 0 00-2-2H5zM5 11a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2v-2a2 2 0 00-2-2H5zM11 5a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V5zM11 13a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
                  </svg>
                </button>
                <button
                  onClick={() => setViewMode("list")}
                  className={`rounded p-1 transition ${viewMode === "list" ? "bg-[var(--surface-3)] text-[var(--cyan)]" : "text-[var(--text-3)] hover:text-[var(--text)]"}`}
                  title="List view"
                  aria-pressed={viewMode === "list"}
                >
                  <svg className="h-3.5 w-3.5" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M3 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM3 10a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM3 16a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" />
                  </svg>
                </button>
              </div>
            </div>

            {/* Entries */}
            {filtered.length === 0 ? (
              <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-8 text-center">
                <p className="text-sm font-medium text-[var(--heading)]">No entry matches this filter</p>
                <p className="mt-1 text-xs text-[var(--text-3)]">
                  {DEMO_RESOURCES.length} entries exist in demo_resources/. Clear the search to see them all.
                </p>
              </div>
            ) : (
              <motion.div
                variants={stagger}
                initial="hidden"
                animate="show"
                className={
                  viewMode === "grid"
                    ? "grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3"
                    : "flex flex-col gap-2"
                }
              >
                {filtered.map((entry) => {
                  const weak = isKnownWeak(entry.category);
                  const active = selected?.id === entry.id;
                  const promptCount = entry.runs.length;

                  if (viewMode === "list") {
                    return (
                      <motion.button
                        key={entry.id}
                        variants={cardVariant}
                        onClick={() => setSelectedId(entry.id)}
                        className={`flex w-full items-center gap-3 rounded-xl border px-3 py-2.5 text-left transition ${
                          active
                            ? "border-[var(--cyan)]/50 bg-[var(--cyan-glow)]"
                            : "border-[var(--border)] bg-[var(--surface)] hover:border-[var(--border-strong)]"
                        }`}
                      >
                        <Preview path={entry.thumbnail} className="h-12 w-12 shrink-0" rounded="rounded-md" />
                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="truncate text-xs font-semibold text-[var(--heading)]">{entry.name}</span>
                            {weak && <KnownWeakBadge />}
                          </div>
                          <div className="truncate font-mono text-[10px] text-[var(--text-3)]">{entry.folder}</div>
                        </div>
                        <div className="shrink-0 text-right text-[10px] text-[var(--text-3)]">
                          <div>{entry.files.length} files</div>
                          <div>{promptCount === 0 ? "no measured run" : `${promptCount} prompt${promptCount === 1 ? "" : "s"}`}</div>
                        </div>
                      </motion.button>
                    );
                  }

                  return (
                    <motion.div key={entry.id} variants={cardVariant}>
                      <SpotlightCard
                        className={`h-full cursor-pointer rounded-xl border transition ${
                          active
                            ? "border-[var(--cyan)]/50 bg-[var(--surface-2)]"
                            : "border-[var(--border)] bg-[var(--surface)] hover:border-[var(--border-strong)]"
                        }`}
                        onClick={() => setSelectedId(entry.id)}
                      >
                        <div className="relative">
                          <Preview path={entry.thumbnail} className="h-36 w-full" rounded="rounded-t-xl" />
                          <div className="absolute left-2 top-2 flex flex-wrap gap-1.5">
                            <span className="rounded-full border border-[var(--border)] bg-[var(--scrim)] px-2 py-0.5 text-[10px] font-medium text-[var(--heading)] backdrop-blur">
                              {categoryLabel(entry.category)}
                            </span>
                            {weak && <KnownWeakBadge />}
                          </div>
                        </div>
                        <div className="p-3">
                          <h3 className="truncate text-xs font-semibold text-[var(--heading)]">{entry.name}</h3>
                          <p className="mt-0.5 break-all font-mono text-[10px] text-[var(--text-3)]">{entry.folder}</p>
                          {entry.failure && (
                            <p className="mt-2 text-[10px] leading-relaxed text-[var(--amber)]">{entry.failure}</p>
                          )}
                          {!entry.failure && entry.description && (
                            <p className="mt-2 line-clamp-2 text-[10px] leading-relaxed text-[var(--text-2)]">
                              {entry.description}
                            </p>
                          )}
                          <div className="mt-2.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[10px] text-[var(--text-3)]">
                            <span>{entry.files.length} files</span>
                            <span>
                              {entry.runs.length === 0
                                ? "no measured run"
                                : `${entry.runs.length} prompt${entry.runs.length === 1 ? "" : "s"} recorded`}
                            </span>
                            {entry.duration && <span>{entry.duration}</span>}
                          </div>
                        </div>
                      </SpotlightCard>
                    </motion.div>
                  );
                })}
              </motion.div>
            )}

            <div className="pt-4 text-xs text-[var(--text-3)]">
              Showing <span className="font-medium text-[var(--text)]">{filtered.length}</span> of{" "}
              <span className="font-medium text-[var(--text)]">{DEMO_RESOURCES.length}</span> entries ·{" "}
              <span className="font-medium text-[var(--text)]">{shownFileCount}</span> of{" "}
              <span className="font-medium text-[var(--text)]">{CATALOGUED_FILE_COUNT}</span> files
            </div>
          </main>

          {/* Details panel */}
          <aside className="w-full shrink-0 space-y-4 border-t border-[var(--border)] bg-[var(--surface)] p-5 lg:w-[26rem] lg:border-l lg:border-t-0 lg:overflow-y-auto">
            {!selected ? (
              <p className="text-xs text-[var(--text-3)]">Select an entry to see its files and recorded runs.</p>
            ) : (
              <>
                <div>
                  <div className="mb-1.5 flex flex-wrap items-center gap-2">
                    <span className="rounded-full border border-[var(--border)] bg-[var(--surface-3)] px-2 py-0.5 text-[10px] font-medium text-[var(--text-2)]">
                      {categoryLabel(selected.category)}
                    </span>
                    {isKnownWeak(selected.category) && <KnownWeakBadge />}
                    {selected.duration && (
                      <span className="text-[10px] text-[var(--text-3)]">{selected.duration}</span>
                    )}
                  </div>
                  <h2 className="text-base font-bold tracking-tight text-[var(--heading)]">{selected.name}</h2>
                  <p className="mt-0.5 break-all font-mono text-[10px] text-[var(--text-3)]">
                    demo_resources/{selected.folder}
                  </p>
                </div>

                {isKnownWeak(selected.category) && (
                  <div className="rounded-lg border border-[var(--amber)]/40 bg-[var(--amber-bg)] p-3 text-[11px] leading-relaxed text-[var(--amber)]">
                    <span className="font-semibold">Known weak — do not demo this.</span> It is kept in{" "}
                    <span className="font-mono">5_known_weak/</span>, and listed here, so nobody picks it by accident.
                    {selected.failure && <> What goes wrong: {selected.failure}</>}
                  </div>
                )}

                {activePreview && (
                  <div>
                    <Preview path={activePreview.path || undefined} className="h-56 w-full" rounded="rounded-xl" />
                    {activePreview.path && (
                      <p className="mt-1.5 text-[10px] leading-relaxed text-[var(--text-3)]">
                        {activePreview.caption} · <span className="font-mono">{activePreview.path}</span>
                      </p>
                    )}
                  </div>
                )}

                {selected.description && !isKnownWeak(selected.category) && (
                  <p className="text-[11px] leading-relaxed text-[var(--text-2)]">{selected.description}</p>
                )}

                <div className="text-[11px] leading-relaxed text-[var(--text-3)]">
                  <span className="font-medium text-[var(--text-2)]">Provenance:</span> {selected.provenance}
                </div>

                {selected.caveat && (
                  <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] p-3 text-[11px] leading-relaxed text-[var(--text-2)]">
                    <span className="font-semibold text-[var(--heading)]">Caveat: </span>
                    {selected.caveat}
                  </div>
                )}

                {selected.meta && (
                  <div>
                    <h3 className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-[var(--text-3)]">
                      Documented metadata
                    </h3>
                    <dl className="space-y-1.5">
                      {selected.meta.map((field) => (
                        <div key={field.label} className="flex gap-2 text-[11px]">
                          <dt className="w-28 shrink-0 text-[var(--text-3)]">{field.label}</dt>
                          <dd className="min-w-0 break-words text-[var(--text-2)]">{field.value}</dd>
                        </div>
                      ))}
                    </dl>
                    {selected.metaSource && (
                      <p className="mt-1.5 text-[10px] text-[var(--text-3)]">{selected.metaSource}</p>
                    )}
                  </div>
                )}

                <div>
                  <h3 className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-[var(--text-3)]">
                    Recorded runs
                  </h3>
                  {selected.runs.length === 0 ? (
                    <p className="text-[11px] leading-relaxed text-[var(--text-2)]">
                      No run recorded in the README for this entry, so no result is shown.
                    </p>
                  ) : (
                    <ul className="space-y-2">
                      {selected.runs.map((run) => (
                        <li
                          key={run.prompt}
                          className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] p-2.5"
                        >
                          <div className="font-mono text-[11px] text-[var(--cyan)]">{run.prompt}</div>
                          <div className="mt-1 text-[11px] font-medium text-[var(--text)]">{run.result}</div>
                          {run.note && (
                            <div className="mt-0.5 text-[10px] leading-relaxed text-[var(--text-3)]">{run.note}</div>
                          )}
                          {run.overlay && (
                            <button
                              onClick={() =>
                                setPreview({
                                  entryId: selected.id,
                                  path: run.overlay as string,
                                  caption: `Backend overlay for “${run.prompt}”`,
                                })
                              }
                              className="mt-1.5 text-[10px] font-medium text-[var(--cyan)] underline decoration-dotted underline-offset-2"
                            >
                              Show this overlay
                            </button>
                          )}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>

                <div>
                  <h3 className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-[var(--text-3)]">
                    Files ({selected.files.length})
                  </h3>
                  <ul>
                    {selected.files.map((file) => (
                      <FileRow key={file.path} file={file} />
                    ))}
                  </ul>
                </div>
              </>
            )}
          </aside>
        </div>
      </div>
    </motion.div>
  );
}
