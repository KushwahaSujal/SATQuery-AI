#!/usr/bin/env node
/**
 * End-to-end smoke test for SatQuery AI frontend-v2 ↔ backend.
 *
 * Exercises the full chain WITHOUT the UI:
 *   1. GET /api/health
 *   2. GET /api/models
 *   3. POST /api/upload (one demo image)
 *   4. POST /api/analyze (a simple query)
 *   5. Poll GET /api/jobs/{jobId} until terminal
 *   6. GET /api/results/{jobId} → verify answer/confidence/models_used
 *   7. GET /api/analysis/{jobId}/layers → verify at least one layer
 *   8. GET layer artifact → verify bytes (>= PNG header)
 *
 * Usage:
 *   node scripts/smoke.mjs
 *   API_BASE=http://localhost:8000 node scripts/smoke.mjs
 *
 * Exits 0 on success, 1 on first failure with a clear message.
 */

import { readFileSync, statSync } from "node:fs";
import { resolve } from "node:path";

const API_BASE = process.env.API_BASE ?? "http://localhost:8000";
const DEMO_IMAGE_CANDIDATES = [
  "D:/SATQuery-AI/SATQuery-AI-backend/demo_resources/1_masking/street_houses_trees_cars__P0725_0005.png",
  "../demo_resources/1_masking/street_houses_trees_cars__P0725_0005.png",
  "demo_resources/1_masking/street_houses_trees_cars__P0725_0005.png",
];

function log(step, ok, detail = "") {
  const tag = ok ? "PASS" : "FAIL";
  const color = ok ? "\x1b[32m" : "\x1b[31m";
  console.log(`${color}[${tag}]\x1b[0m ${step}${detail ? " — " + detail : ""}`);
  if (!ok) process.exit(1);
}

function findDemoImage() {
  for (const p of DEMO_IMAGE_CANDIDATES) {
    try {
      statSync(p);
      return p;
    } catch {}
  }
  return null;
}

async function http(path, init = {}) {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, init);
  const text = await res.text();
  let json = null;
  try {
    json = text ? JSON.parse(text) : null;
  } catch {}
  return { ok: res.ok, status: res.status, json, text };
}

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

async function main() {
  console.log(`\nSatQuery AI end-to-end smoke test`);
  console.log(`API_BASE: ${API_BASE}\n`);

  // 1. Health
  const health = await http("/api/health");
  log("GET /api/health", health.ok, `status=${health.status} body=${JSON.stringify(health.json).slice(0, 120)}`);
  if (!health.json?.status || health.json.status !== "ok") {
    log("backend reports non-ok status", false, JSON.stringify(health.json));
  }

  // 2. Models
  const models = await http("/api/models");
  log("GET /api/models", models.ok, `body=${JSON.stringify(models.json).slice(0, 120)}`);
  const modelList = Array.isArray(models.json) ? models.json : (models.json?.models ?? []);
  log("models list non-empty", modelList.length > 0, `${modelList.length} models`);

  // 3. Upload
  const imgPath = findDemoImage();
  if (!imgPath) {
    log("demo image found", false, "missing — checked: " + DEMO_IMAGE_CANDIDATES.join(", "));
  }
  const fileBuf = readFileSync(imgPath);
  const blob = new Blob([fileBuf], { type: "image/png" });
  const fd = new FormData();
  fd.append("files", blob, "demo.png");

  const upload = await http("/api/upload", { method: "POST", body: fd });
  log("POST /api/upload", upload.ok, `request_id=${upload.json?.request_id ?? upload.json?.job_id}`);
  const requestId = upload.json?.request_id ?? upload.json?.job_id;
  if (!requestId) {
    log("upload gave a request_id", false, JSON.stringify(upload.json));
  }

  // 4. Analyze
  const analyzeBody = {
    query: "Describe this scene in detail",
    image_filenames: [upload.json?.metadata?.[0]?.filename ?? "demo.png"],
    parameters: {},
  };
  if (requestId) analyzeBody.request_id = requestId;
  const analyze = await http("/api/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(analyzeBody),
  });
  log("POST /api/analyze", analyze.ok, `status=${analyze.json?.status} task=${analyze.json?.task} workflow=${analyze.json?.workflow}`);
  const jobId = analyze.json?.job_id ?? requestId;

  // If the backend returned synchronously with COMPLETED, skip polling.
  let finalStatus = analyze.json?.status;

  // 5. Poll
  if (finalStatus && !["COMPLETED", "FAILED"].includes(finalStatus)) {
    for (let i = 0; i < 60; i++) {
      await sleep(2000);
      const job = await http(`/api/jobs/${jobId}`);
      finalStatus = job.json?.status;
      process.stdout.write(`  poll ${i + 1}: ${finalStatus ?? "?"}\r`);
      if (["COMPLETED", "FAILED"].includes(finalStatus)) {
        console.log("");
        break;
      }
    }
    console.log("");
  }
  log("job reached terminal state", ["COMPLETED", "FAILED"].includes(finalStatus), `final=${finalStatus}`);

  if (finalStatus === "FAILED") {
    log("job succeeded", false, JSON.stringify(analyze.json));
  }

  // 6. Result
  const result = await http(`/api/results/${jobId}`);
  log("GET /api/results/{jobId}", result.ok, `answer=${typeof result.json?.answer === "string" ? result.json.answer.slice(0, 80) : "MISSING"} confidence=${result.json?.confidence}`);
  log("result has answer", typeof result.json?.answer === "string" && result.json.answer.length > 0);
  log("result has confidence", typeof result.json?.confidence === "number");
  log("result has models_used", Array.isArray(result.json?.models_used));

  // 7. Layers
  const layers = await http(`/api/analysis/${jobId}/layers`);
  const layerList = Array.isArray(layers.json) ? layers.json : (layers.json?.layers ?? []);
  log("GET /api/analysis/{jobId}/layers", layers.ok, `${layerList.length} layers`);
  log("at least one layer", layerList.length > 0);

  if (layerList.length > 0) {
    // 8. Layer artifact
    const firstLayer = layerList[0];
    const layerId = firstLayer.layer_id ?? firstLayer.id;
    const artifactUrl = firstLayer.artifact_url
      ? (firstLayer.artifact_url.startsWith("http") ? firstLayer.artifact_url : `${API_BASE}${firstLayer.artifact_url}`)
      : `${API_BASE}/api/analysis/${jobId}/visualizations/${layerId}`;
    const artifact = await fetch(artifactUrl);
    const buf = Buffer.from(await artifact.arrayBuffer());
    const isPng = buf[0] === 0x89 && buf[1] === 0x50 && buf[2] === 0x4e && buf[3] === 0x47;
    log(`GET layer ${layerId}`, artifact.ok && buf.length > 0 && isPng, `${buf.length} bytes, png=${isPng}`);
  }

  console.log(`\n\x1b[32m✓ ALL CHECKS PASSED\x1b[0m\n`);
}

main().catch((err) => {
  console.error("\n\x1b[31m✗ SMOKE TEST CRASHED\x1b[0m");
  console.error(err);
  process.exit(1);
});