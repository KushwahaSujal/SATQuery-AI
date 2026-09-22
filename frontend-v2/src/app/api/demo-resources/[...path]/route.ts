import { createReadStream, existsSync } from "node:fs";
import { stat, realpath } from "node:fs/promises";
import path from "node:path";
import { Readable } from "node:stream";

/**
 * Streams files out of the repository's `demo_resources/` directory.
 *
 * These are the sample assets committed to the repo (35 MB, 54 files). They are
 * deliberately NOT copied into `public/` — the repo has a no-duplicate-data rule —
 * so this route reads them from their single on-disk location.
 */

/** Candidate locations for `demo_resources/`, in priority order. */
function resolveBaseDir(): string | null {
  const candidates = [
    process.env.DEMO_RESOURCES_DIR,
    path.join(process.cwd(), "..", "demo_resources"), // dev server runs in frontend-v2/
    path.join(process.cwd(), "demo_resources"), // server started from the repo root
  ].filter((c): c is string => Boolean(c));

  for (const candidate of candidates) {
    const resolved = path.resolve(candidate);
    if (existsSync(resolved)) return resolved;
  }
  return null;
}

const BASE_DIR = resolveBaseDir();

/** Only the extensions that actually exist under demo_resources/. */
const CONTENT_TYPES: Record<string, string> = {
  ".png": "image/png",
  ".tif": "image/tiff",
  ".tiff": "image/tiff",
  ".mp4": "video/mp4",
  ".geojson": "application/geo+json",
  ".json": "application/json",
  ".md": "text/markdown; charset=utf-8",
};

function deny(status: number, reason: string): Response {
  return new Response(JSON.stringify({ error: reason }), {
    status,
    headers: { "content-type": "application/json" },
  });
}

/**
 * Resolves the requested segments against BASE_DIR, refusing anything that
 * escapes it. Rejects traversal both before resolving (segment shape) and
 * after (prefix check on the normalised path, and again on the real path so a
 * symlink cannot point outside).
 */
function safeJoin(base: string, segments: string[]): string | null {
  const decoded: string[] = [];
  for (const raw of segments) {
    let segment: string;
    try {
      segment = decodeURIComponent(raw);
    } catch {
      return null; // malformed percent-encoding
    }
    if (
      segment.length === 0 ||
      segment === "." ||
      segment === ".." ||
      segment.includes("/") ||
      segment.includes("\\") ||
      segment.includes("\0")
    ) {
      return null;
    }
    decoded.push(segment);
  }
  if (decoded.length === 0) return null;

  const resolved = path.resolve(base, ...decoded);
  const normalisedBase = path.resolve(base) + path.sep;
  if (resolved !== path.resolve(base) && !resolved.startsWith(normalisedBase)) {
    return null;
  }
  return resolved;
}

export async function GET(
  request: Request,
  { params }: { params: Promise<{ path: string[] }> },
): Promise<Response> {
  if (!BASE_DIR) {
    return deny(500, "demo_resources directory not found on this server");
  }

  const { path: segments = [] } = await params;
  const filePath = safeJoin(BASE_DIR, segments);
  if (!filePath) return deny(400, "Invalid path");

  const extension = path.extname(filePath).toLowerCase();
  const contentType = CONTENT_TYPES[extension];
  if (!contentType) return deny(415, `Unsupported file type: ${extension || "(none)"}`);

  let stats;
  try {
    stats = await stat(filePath);
    // Re-check after symlink resolution: a link inside the base dir must not
    // point outside it.
    const real = await realpath(filePath);
    if (real !== BASE_DIR && !real.startsWith(BASE_DIR + path.sep)) {
      return deny(400, "Invalid path");
    }
  } catch {
    return deny(404, "Not found");
  }
  if (!stats.isFile()) return deny(404, "Not found");

  const headers = new Headers({
    "content-type": contentType,
    "cache-control": "public, max-age=3600",
    "accept-ranges": "bytes",
    "x-content-type-options": "nosniff",
  });

  // Minimal single-range support so browsers can seek within the mp4 samples.
  const rangeHeader = request.headers.get("range");
  const match = rangeHeader ? /^bytes=(\d*)-(\d*)$/.exec(rangeHeader.trim()) : null;
  if (match && (match[1] !== "" || match[2] !== "")) {
    let start: number;
    let end: number;
    if (match[1] === "") {
      const suffixLength = Number(match[2]);
      start = Math.max(0, stats.size - suffixLength);
      end = stats.size - 1;
    } else {
      start = Number(match[1]);
      end = match[2] === "" ? stats.size - 1 : Math.min(Number(match[2]), stats.size - 1);
    }
    if (!Number.isFinite(start) || !Number.isFinite(end) || start > end || start >= stats.size) {
      return new Response(null, {
        status: 416,
        headers: { "content-range": `bytes */${stats.size}` },
      });
    }
    headers.set("content-range", `bytes ${start}-${end}/${stats.size}`);
    headers.set("content-length", String(end - start + 1));
    const partial = Readable.toWeb(
      createReadStream(filePath, { start, end }),
    ) as unknown as ReadableStream<Uint8Array>;
    return new Response(partial, { status: 206, headers });
  }

  headers.set("content-length", String(stats.size));
  const body = Readable.toWeb(
    createReadStream(filePath),
  ) as unknown as ReadableStream<Uint8Array>;
  return new Response(body, { status: 200, headers });
}
