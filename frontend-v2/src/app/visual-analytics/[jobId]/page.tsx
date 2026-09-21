"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useHistogram, useLayers, usePixelInspector } from "@/hooks/useSystem";
import { api } from "@/lib/api";
import type { ExportFormat, Layer } from "@/lib/types";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui";
import {
  AlertCircle,
  ArrowLeft,
  ChartColumn,
  ChevronRight,
  Crosshair,
  Download,
  ImageOff,
  Layers as LayersIcon,
  Loader2,
} from "lucide-react";

const PROVENANCE_CLASS: Record<string, string> = {
  SOURCE_DATA: "text-[var(--cyan)]",
  DERIVED_INDEX: "text-[var(--green)]",
  MODEL_OUTPUT: "text-[var(--text)]",
  MODEL_PROBABILITY: "text-[var(--warning)]",
};

const EXPORT_FORMATS: ExportFormat[] = ["png", "geotiff", "geojson"];
const EXPORT_EXTENSION: Record<ExportFormat, string> = {
  png: "png",
  geotiff: "tif",
  geojson: "geojson",
};

type ExportState = { format: ExportFormat; status: "working" | "done" | "error"; message?: string };

function num(value: number | undefined | null, digits = 4): string {
  if (value == null || Number.isNaN(value)) return "—";
  return value.toFixed(digits);
}

function FieldRow({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3 py-1">
      <span className="font-mono-data text-[10px] text-[var(--text-3)]">{label}</span>
      <span className={`font-mono-data text-[10px] text-right break-all ${tone ?? "text-[var(--text)]"}`}>
        {value}
      </span>
    </div>
  );
}

export default function VisualAnalyticsPage() {
  const params = useParams<{ jobId: string }>();
  const jobId = params.jobId;

  const layersQuery = useLayers(jobId);
  const layers: Layer[] = layersQuery.data?.layers ?? [];

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const activeLayer = useMemo(
    () => layers.find((l) => l.id === selectedId) ?? layers[0],
    [layers, selectedId],
  );
  const activeId = activeLayer?.id;

  const [opacity, setOpacity] = useState(100);
  const [imageFailed, setImageFailed] = useState(false);
  const [imageSize, setImageSize] = useState<{ width: number; height: number } | null>(null);
  const [marker, setMarker] = useState<{ xPct: number; yPct: number } | null>(null);
  const [showHistogram, setShowHistogram] = useState(false);
  const [exportState, setExportState] = useState<ExportState | null>(null);

  const imgRef = useRef<HTMLImageElement>(null);
  const pixelInspector = usePixelInspector(jobId);
  const histogram = useHistogram(jobId, activeId, showHistogram && Boolean(activeId));

  // Everything below the layer selection is per-layer state; switching layers must not carry
  // over a previous layer's render failure, marker, pixel read-out or export result.
  useEffect(() => {
    setImageFailed(false);
    setImageSize(null);
    setMarker(null);
    setExportState(null);
    pixelInspector.reset();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeId]);

  const handleCanvasClick = useCallback(
    (event: React.MouseEvent<HTMLImageElement>) => {
      const img = imgRef.current;
      if (!img || !img.naturalWidth || !img.naturalHeight) return;

      // The PNG the backend renders has exactly the raster's pixel grid, so the click maps to
      // (col, row) through the image's own natural size — not through an assumed raster size.
      const rect = img.getBoundingClientRect();
      const scale = Math.min(rect.width / img.naturalWidth, rect.height / img.naturalHeight);
      const drawnWidth = img.naturalWidth * scale;
      const drawnHeight = img.naturalHeight * scale;
      const offsetX = (rect.width - drawnWidth) / 2;
      const offsetY = (rect.height - drawnHeight) / 2;

      const localX = event.clientX - rect.left - offsetX;
      const localY = event.clientY - rect.top - offsetY;
      if (localX < 0 || localY < 0 || localX > drawnWidth || localY > drawnHeight) return;

      const col = Math.min(img.naturalWidth - 1, Math.floor(localX / scale));
      const row = Math.min(img.naturalHeight - 1, Math.floor(localY / scale));

      setMarker({
        xPct: ((offsetX + localX) / rect.width) * 100,
        yPct: ((offsetY + localY) / rect.height) * 100,
      });
      pixelInspector.mutate({ col, row });
    },
    [pixelInspector],
  );

  const runExport = useCallback(
    async (format: ExportFormat) => {
      if (!activeId) return;
      setExportState({ format, status: "working" });
      try {
        const response = await fetch(api.exportUrl(jobId, activeId, format));
        if (!response.ok) {
          const body = await response.text();
          let message = `Backend returned ${response.status}`;
          try {
            const parsed = JSON.parse(body);
            message = parsed?.error?.message || parsed?.detail || message;
          } catch {
            /* keep the status-code message */
          }
          setExportState({ format, status: "error", message });
          return;
        }
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = `${jobId}_${activeId}.${EXPORT_EXTENSION[format]}`;
        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();
        URL.revokeObjectURL(url);
        setExportState({ format, status: "done" });
      } catch (error) {
        setExportState({
          format,
          status: "error",
          message: error instanceof Error ? error.message : "Network error",
        });
      }
    },
    [activeId, jobId],
  );

  const pixel = pixelInspector.data;
  const bins = histogram.data?.bins ?? [];
  const maxBinCount = bins.reduce((peak, bin) => Math.max(peak, bin.count), 0);

  return (
    <div className="h-screen flex flex-col bg-[var(--canvas)] text-[var(--text)] font-sans antialiased overflow-hidden">
      <TopBar showBrand={true} />

      <div className="flex flex-1 overflow-hidden">
        <Sidebar hideBrand={true} activeItem="visual-analytics" className="h-full" />

        <main className="flex-1 overflow-y-auto bg-[var(--canvas)]">
          {/* Sub-header */}
          <div className="flex flex-wrap items-center gap-3 border-b border-[var(--border)] bg-[var(--surface)] px-4 py-3 sm:px-6">
            <Link
              href={`/analysis/${jobId}`}
              className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-[var(--border)] bg-[var(--surface-2)] text-[var(--text-2)] transition hover:border-[var(--border-strong)] hover:text-[var(--heading)]"
              aria-label="Back to the analysis workspace"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
            </Link>
            <div className="min-w-0">
              <div className="flex items-center gap-1.5 font-mono-data text-[10px] text-[var(--text-3)]">
                <span>visual-analytics</span>
                <ChevronRight className="h-3 w-3" />
                <span className="truncate text-[var(--text-2)]">{jobId}</span>
              </div>
              <h1 className="mt-0.5 flex items-center gap-2 text-sm font-semibold text-[var(--heading)]">
                <LayersIcon className="h-3.5 w-3.5 text-[var(--cyan)]" />
                Layer inspector
              </h1>
            </div>
            <span className="ml-auto font-mono-data text-[10px] text-[var(--text-3)]">
              {layersQuery.isLoading
                ? "loading layers…"
                : `${layers.length} layer${layers.length === 1 ? "" : "s"}`}
            </span>
          </div>

          <div className="p-4 sm:p-6">
            {layersQuery.isLoading ? (
              <Card>
                <CardContent className="flex items-center gap-2 pt-4 text-xs text-[var(--text-3)]">
                  <Loader2 className="h-4 w-4 animate-spin text-[var(--cyan)]" />
                  Discovering visualization layers for this job…
                </CardContent>
              </Card>
            ) : layersQuery.isError ? (
              <Card>
                <CardContent className="flex items-start gap-2 pt-4 text-xs">
                  <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-[var(--error)]" />
                  <div className="min-w-0">
                    <p className="font-semibold text-[var(--heading)]">Could not load layers</p>
                    <p className="mt-0.5 font-mono-data text-[10px] break-words text-[var(--text-2)]">
                      {layersQuery.error instanceof Error
                        ? layersQuery.error.message
                        : String(layersQuery.error)}
                    </p>
                  </div>
                </CardContent>
              </Card>
            ) : layers.length === 0 || !activeLayer ? (
              <Card>
                <CardContent className="pt-4">
                  <p className="text-sm font-semibold text-[var(--heading)]">
                    This job has no visualization layers
                  </p>
                  <p className="mt-1 max-w-xl text-xs leading-relaxed text-[var(--text-2)]">
                    <span className="font-mono-data">/api/analysis/{jobId}/layers</span> returned an
                    empty list. Layers are discovered from the job&apos;s source imagery on disk, so
                    a completed job whose input rasters have since been cleaned up reports none —
                    and pixel inspection, histograms and exports are unavailable with it.
                  </p>
                  <Link
                    href={`/analysis/${jobId}`}
                    className="mt-3 inline-flex items-center gap-1.5 rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-3 py-1.5 text-xs font-medium text-[var(--text)] transition hover:border-[var(--border-strong)]"
                  >
                    <ArrowLeft className="h-3.5 w-3.5" />
                    Back to the analysis workspace
                  </Link>
                </CardContent>
              </Card>
            ) : (
              <div className="grid grid-cols-1 gap-4 lg:grid-cols-[236px_minmax(0,1fr)] xl:grid-cols-[236px_minmax(0,1fr)_320px]">
                {/* ── Layer list ── */}
                <Card className="overflow-hidden self-start">
                  <CardHeader className="border-b border-[var(--border)] bg-[var(--surface-2)]/40 py-2.5">
                    <CardTitle className="font-mono-data text-[10px] uppercase tracking-wider text-[var(--text-2)]">
                      Layers
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="max-h-72 overflow-y-auto p-0 lg:max-h-[62vh]">
                    {layers.map((layer) => {
                      const active = layer.id === activeLayer.id;
                      return (
                        <button
                          key={layer.id}
                          type="button"
                          onClick={() => setSelectedId(layer.id)}
                          className={`flex w-full flex-col gap-0.5 border-b border-[var(--border)] px-3 py-2.5 text-left transition last:border-0 ${
                            active
                              ? "bg-[var(--cyan)]/10 text-[var(--heading)]"
                              : "text-[var(--text-2)] hover:bg-[var(--surface-hover)]/50 hover:text-[var(--heading)]"
                          }`}
                        >
                          <span className="text-[11px] leading-snug">{layer.name}</span>
                          <span
                            className={`font-mono-data text-[9px] uppercase tracking-wider ${
                              PROVENANCE_CLASS[layer.provenance] ?? "text-[var(--text-3)]"
                            }`}
                          >
                            {layer.provenance}
                          </span>
                        </button>
                      );
                    })}
                  </CardContent>
                </Card>

                {/* ── Canvas ── */}
                <div className="min-w-0 space-y-4">
                  <Card className="overflow-hidden">
                    <CardHeader className="flex-row flex-wrap items-center justify-between gap-2 space-y-0 border-b border-[var(--border)] bg-[var(--surface-2)]/40 py-2.5">
                      <div className="min-w-0">
                        <CardTitle className="truncate text-[12px]">{activeLayer.name}</CardTitle>
                        <span
                          className={`font-mono-data text-[9px] uppercase tracking-wider ${
                            PROVENANCE_CLASS[activeLayer.provenance] ?? "text-[var(--text-3)]"
                          }`}
                        >
                          {activeLayer.provenance}
                          {activeLayer.category ? ` · ${activeLayer.category}` : ""}
                        </span>
                      </div>
                      <span className="flex items-center gap-1.5 font-mono-data text-[10px] text-[var(--text-3)]">
                        <Crosshair className="h-3 w-3" />
                        click to inspect a pixel
                      </span>
                    </CardHeader>

                    <CardContent className="p-0">
                      <div className="relative h-[52vh] min-h-[280px] w-full overflow-hidden bg-[var(--canvas)]">
                        {imageFailed ? (
                          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 px-6 text-center">
                            <ImageOff className="h-5 w-5 text-[var(--text-3)]" />
                            <p className="text-xs font-semibold text-[var(--heading)]">
                              The backend did not return an image for this layer
                            </p>
                            <p className="max-w-sm font-mono-data text-[10px] break-all text-[var(--text-3)]">
                              {activeLayer.artifact_url}
                            </p>
                            <button
                              type="button"
                              onClick={() => setImageFailed(false)}
                              className="mt-1 rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-2.5 py-1 text-[11px] text-[var(--text)] transition hover:border-[var(--border-strong)]"
                            >
                              Retry render
                            </button>
                          </div>
                        ) : (
                          <>
                            {/* eslint-disable-next-line @next/next/no-img-element */}
                            <img
                              ref={imgRef}
                              key={activeLayer.id}
                              src={activeLayer.artifact_url}
                              alt={activeLayer.name}
                              onClick={handleCanvasClick}
                              onLoad={(e) =>
                                setImageSize({
                                  width: e.currentTarget.naturalWidth,
                                  height: e.currentTarget.naturalHeight,
                                })
                              }
                              onError={() => setImageFailed(true)}
                              style={{ opacity: opacity / 100 }}
                              className="absolute inset-0 h-full w-full cursor-crosshair object-contain"
                            />
                            {marker && (
                              <span
                                className="pointer-events-none absolute h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full border border-[var(--cyan)] bg-[var(--cyan)]/30"
                                style={{ left: `${marker.xPct}%`, top: `${marker.yPct}%` }}
                              />
                            )}
                            {pixelInspector.isPending && (
                              <span className="absolute right-2 top-2 flex items-center gap-1.5 rounded-md border border-[var(--border)] bg-[var(--surface)]/90 px-2 py-1 font-mono-data text-[10px] text-[var(--text-2)]">
                                <Loader2 className="h-3 w-3 animate-spin text-[var(--cyan)]" />
                                reading pixel
                              </span>
                            )}
                          </>
                        )}
                      </div>

                      {/* Opacity + geometry */}
                      <div className="flex flex-wrap items-center gap-3 border-t border-[var(--border)] bg-[var(--surface-2)]/40 px-3 py-2">
                        <span className="font-mono-data text-[10px] uppercase tracking-wider text-[var(--text-3)]">
                          Opacity
                        </span>
                        <input
                          type="range"
                          min={10}
                          max={100}
                          value={opacity}
                          onChange={(e) => setOpacity(Number(e.target.value))}
                          aria-label="Layer opacity"
                          className="h-1 min-w-[120px] flex-1 cursor-pointer accent-[var(--cyan)]"
                        />
                        <span className="font-mono-data text-[10px] text-[var(--text-2)]">
                          {opacity}%
                        </span>
                        <span className="font-mono-data text-[10px] text-[var(--text-3)]">
                          {imageSize ? `${imageSize.width} × ${imageSize.height} px` : "size unknown"}
                        </span>
                      </div>
                    </CardContent>
                  </Card>

                  {/* Layer metadata + legend */}
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                    <Card>
                      <CardHeader className="py-3">
                        <CardTitle className="text-[12px]">Layer metadata</CardTitle>
                      </CardHeader>
                      <CardContent className="pt-0">
                        <FieldRow label="layer_id" value={activeLayer.id} />
                        <FieldRow label="layer_type" value={activeLayer.category || "—"} />
                        <FieldRow
                          label="provenance"
                          value={activeLayer.provenance}
                          tone={PROVENANCE_CLASS[activeLayer.provenance] ?? "text-[var(--text)]"}
                        />
                        {activeLayer.description && (
                          <FieldRow label="units" value={activeLayer.description} />
                        )}
                      </CardContent>
                    </Card>

                    <Card>
                      <CardHeader className="py-3">
                        <CardTitle className="text-[12px]">Legend</CardTitle>
                      </CardHeader>
                      <CardContent className="pt-0">
                        {activeLayer.legend_url ? (
                          <div className="overflow-x-auto rounded-md border border-[var(--border)] bg-[var(--surface-2)] p-2">
                            {/* eslint-disable-next-line @next/next/no-img-element */}
                            <img
                              src={activeLayer.legend_url}
                              alt={`Legend for ${activeLayer.name}`}
                              className="max-w-full"
                            />
                          </div>
                        ) : (
                          <p className="text-[11px] leading-relaxed text-[var(--text-3)]">
                            The backend publishes no legend for this layer. Legends exist only for
                            single-band, spectral-index, SAR-polarisation and probability layers.
                          </p>
                        )}
                      </CardContent>
                    </Card>
                  </div>
                </div>

                {/* ── Inspector / histogram / export ── */}
                <div className="min-w-0 space-y-4 lg:col-span-2 xl:col-span-1">
                  {/* Pixel inspector */}
                  <Card>
                    <CardHeader className="py-3">
                      <CardTitle className="flex items-center gap-1.5 text-[12px]">
                        <Crosshair className="h-3.5 w-3.5 text-[var(--cyan)]" />
                        Pixel inspector
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="pt-0">
                      {pixelInspector.isError ? (
                        <div className="flex items-start gap-1.5 text-[11px]">
                          <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[var(--error)]" />
                          <span className="break-words text-[var(--text-2)]">
                            {pixelInspector.error instanceof Error
                              ? pixelInspector.error.message
                              : "Pixel inspection failed."}
                          </span>
                        </div>
                      ) : !pixel ? (
                        <p className="text-[11px] text-[var(--text-3)]">
                          Click anywhere on the image to read that pixel.
                        </p>
                      ) : (
                        <div className="divide-y divide-[var(--border)]">
                          <div className="pb-1">
                            <FieldRow label="col, row" value={`${pixel.col}, ${pixel.row}`} />
                          </div>

                          {pixel.geographic_coordinates && (
                            <div className="py-1">
                              <FieldRow
                                label={`x, y (${
                                  pixel.geographic_coordinates.crs ?? pixel.crs ?? "crs unknown"
                                })`}
                                value={`${num(pixel.geographic_coordinates.x_coord, 2)}, ${num(
                                  pixel.geographic_coordinates.y_coord,
                                  2,
                                )}`}
                              />
                            </div>
                          )}

                          {pixel.band_values && Object.keys(pixel.band_values).length > 0 && (
                            <div className="py-1">
                              <p className="mb-0.5 font-mono-data text-[9px] uppercase tracking-wider text-[var(--text-3)]">
                                band values
                              </p>
                              {Object.entries(pixel.band_values).map(([band, value]) => (
                                <FieldRow key={band} label={band} value={num(value, 2)} />
                              ))}
                            </div>
                          )}

                          {pixel.derived_indices && Object.keys(pixel.derived_indices).length > 0 && (
                            <div className="py-1">
                              <p className="mb-0.5 font-mono-data text-[9px] uppercase tracking-wider text-[var(--text-3)]">
                                derived indices
                              </p>
                              {Object.entries(pixel.derived_indices).map(([index, value]) => (
                                <FieldRow
                                  key={index}
                                  label={index}
                                  value={num(value)}
                                  tone="text-[var(--green)]"
                                />
                              ))}
                            </div>
                          )}

                          {(pixel.probability != null || pixel.model_prediction) && (
                            <div className="py-1">
                              <p className="mb-0.5 font-mono-data text-[9px] uppercase tracking-wider text-[var(--text-3)]">
                                model prediction
                              </p>
                              {pixel.probability != null && (
                                <FieldRow
                                  label="probability"
                                  value={`${(pixel.probability * 100).toFixed(2)}%`}
                                  tone="text-[var(--warning)]"
                                />
                              )}
                              {pixel.model_prediction?.status && (
                                <FieldRow label="status" value={pixel.model_prediction.status} />
                              )}
                            </div>
                          )}
                        </div>
                      )}

                      <p className="mt-2.5 border-t border-[var(--border)] pt-2 text-[10px] leading-relaxed text-[var(--text-3)]">
                        The inspector reads the job&apos;s source raster and change masks, not the
                        rendered layer above, so its values are identical whichever layer is
                        selected.
                      </p>
                    </CardContent>
                  </Card>

                  {/* Histogram */}
                  <Card>
                    <CardHeader className="py-3">
                      <button
                        type="button"
                        onClick={() => setShowHistogram((open) => !open)}
                        className="flex w-full items-center justify-between gap-2"
                      >
                        <CardTitle className="flex items-center gap-1.5 text-[12px]">
                          <ChartColumn className="h-3.5 w-3.5 text-[var(--cyan)]" />
                          Distribution
                        </CardTitle>
                        <span className="font-mono-data text-[10px] text-[var(--text-3)]">
                          {showHistogram ? "hide" : "show"}
                        </span>
                      </button>
                    </CardHeader>

                    {showHistogram && (
                      <CardContent className="pt-0">
                        {histogram.isLoading ? (
                          <p className="flex items-center gap-1.5 text-[11px] text-[var(--text-3)]">
                            <Loader2 className="h-3.5 w-3.5 animate-spin text-[var(--cyan)]" />
                            Computing histogram…
                          </p>
                        ) : histogram.isError ? (
                          <div className="flex items-start gap-1.5 text-[11px]">
                            <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[var(--error)]" />
                            <span className="break-words text-[var(--text-2)]">
                              {histogram.error instanceof Error
                                ? histogram.error.message
                                : "Histogram unavailable."}
                            </span>
                          </div>
                        ) : !histogram.data ? (
                          <p className="text-[11px] text-[var(--text-3)]">No histogram returned.</p>
                        ) : (
                          <>
                            {bins.length === 0 ? (
                              <p className="text-[11px] text-[var(--text-3)]">
                                The backend returned statistics but no bins for this layer.
                              </p>
                            ) : (
                              <div className="overflow-x-auto">
                                <div className="flex h-24 min-w-[240px] items-end gap-px">
                                  {bins.map((bin, index) => (
                                    <div
                                      key={`${bin.range_start}-${index}`}
                                      title={`[${bin.range_start}, ${bin.range_end}) — ${bin.count.toLocaleString()} px`}
                                      className="flex-1 bg-[var(--cyan)]/60"
                                      style={{
                                        height: `${
                                          maxBinCount > 0 ? Math.max((bin.count / maxBinCount) * 100, 1) : 1
                                        }%`,
                                      }}
                                    />
                                  ))}
                                </div>
                                <div className="mt-1 flex justify-between font-mono-data text-[9px] text-[var(--text-3)]">
                                  <span>{num(histogram.data.min, 2)}</span>
                                  <span>{histogram.data.units}</span>
                                  <span>{num(histogram.data.max, 2)}</span>
                                </div>
                              </div>
                            )}

                            <div className="mt-2 border-t border-[var(--border)] pt-1.5">
                              <FieldRow label="min" value={num(histogram.data.min, 3)} />
                              <FieldRow label="max" value={num(histogram.data.max, 3)} />
                              <FieldRow label="mean" value={num(histogram.data.mean, 3)} />
                              <FieldRow label="median" value={num(histogram.data.median, 3)} />
                              <FieldRow label="std" value={num(histogram.data.std, 3)} />
                              {histogram.data.total_pixels != null && (
                                <FieldRow
                                  label="pixels"
                                  value={histogram.data.total_pixels.toLocaleString()}
                                />
                              )}
                            </div>
                          </>
                        )}
                      </CardContent>
                    )}
                  </Card>

                  {/* Export */}
                  <Card>
                    <CardHeader className="py-3">
                      <CardTitle className="flex items-center gap-1.5 text-[12px]">
                        <Download className="h-3.5 w-3.5 text-[var(--cyan)]" />
                        Export layer
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-1.5 pt-0">
                      {EXPORT_FORMATS.map((format) => {
                        const state = exportState?.format === format ? exportState : null;
                        return (
                          <div key={format}>
                            <button
                              type="button"
                              onClick={() => runExport(format)}
                              disabled={state?.status === "working"}
                              className="flex w-full items-center justify-between rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-2.5 py-1.5 font-mono-data text-[10px] uppercase tracking-wider text-[var(--text-2)] transition hover:border-[var(--border-strong)] hover:text-[var(--heading)] disabled:opacity-60"
                            >
                              <span>{format}</span>
                              {state?.status === "working" ? (
                                <Loader2 className="h-3 w-3 animate-spin text-[var(--cyan)]" />
                              ) : (
                                <Download className="h-3 w-3" />
                              )}
                            </button>
                            {state?.status === "error" && (
                              <p className="mt-1 break-words rounded-md border border-[var(--error)]/25 bg-[var(--error-bg)] px-2 py-1 font-mono-data text-[9px] text-[var(--error)]">
                                {state.message}
                              </p>
                            )}
                            {state?.status === "done" && (
                              <p className="mt-1 font-mono-data text-[9px] text-[var(--green)]">
                                downloaded
                              </p>
                            )}
                          </div>
                        );
                      })}
                      <p className="pt-1 text-[10px] leading-relaxed text-[var(--text-3)]">
                        Each button calls the export endpoint for real; if the backend cannot
                        produce that format for this layer, its error is shown here instead of a
                        silent failure.
                      </p>
                    </CardContent>
                  </Card>
                </div>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
