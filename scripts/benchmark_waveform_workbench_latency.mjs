import fs from "node:fs";
import path from "node:path";
import { performance } from "node:perf_hooks";
import { chromium, chromiumLaunchOptions } from "./lib/playwright_runtime.mjs";

const repoRoot = process.cwd();
const evidenceDir = process.env.QLANALYSER_WAVEFORM_BENCH_DIR
  || path.join(repoRoot, "work", "release_evidence", "20260628-waveform-chunk-api-benchmark");
const apiBase = (process.env.QLANALYSER_API_BASE || "http://127.0.0.1:8001/api").replace(/\/$/, "");
const frontendUrl = process.env.QLANALYSER_WAVEFORM_WORKBENCH_URL
  || `http://127.0.0.1:4174/waveform-workbench.html?teaching_demo=auto&api=${encodeURIComponent(apiBase)}&v=chunk-api-latency`;
const includeLegacyTaskBench = process.env.QLANALYSER_INCLUDE_LEGACY_TASK_BENCH === "1";

fs.mkdirSync(evidenceDir, { recursive: true });

async function timed(label, fn) {
  const start = performance.now();
  try {
    const value = await fn();
    return { label, ok: true, ms: Math.round((performance.now() - start) * 10) / 10, value };
  } catch (error) {
    return { label, ok: false, ms: Math.round((performance.now() - start) * 10) / 10, error: error.stack || String(error) };
  }
}

async function jsonFetch(url, options) {
  const response = await fetch(url, options);
  const text = await response.text();
  let data = null;
  try { data = JSON.parse(text); } catch { data = text; }
  if (!response.ok) throw new Error(`${response.status} ${text.slice(0, 300)}`);
  return { data, bytes: Buffer.byteLength(text, "utf8"), status: response.status };
}

function waveformArtifactFromList(artifacts = []) {
  return artifacts.find((artifact) => {
    const key = `${artifact.label || ""} ${artifact.artifact_type || ""} ${artifact.object_key || ""} ${artifact.path || ""}`.toLowerCase();
    return key.includes("waveform_preview") && key.includes("json");
  }) || artifacts.find((artifact) => {
    const key = `${artifact.label || ""} ${artifact.artifact_type || ""} ${artifact.object_key || ""} ${artifact.path || ""}`.toLowerCase();
    return key.includes("waveform") && key.includes("json");
  }) || null;
}

async function waitForArtifact(taskId, timeoutMs = 90000) {
  const started = performance.now();
  let polls = 0;
  while (performance.now() - started < timeoutMs) {
    polls += 1;
    const result = await jsonFetch(`${apiBase}/tasks/${encodeURIComponent(taskId)}/artifacts`);
    const artifact = waveformArtifactFromList(result.data);
    if (artifact) return { artifact, polls };
    await new Promise((resolve) => setTimeout(resolve, 700));
  }
  throw new Error(`waveform artifact timeout for ${taskId}`);
}

function summarizePayload(payload, bytes) {
  const channels = Array.isArray(payload.channels) ? payload.channels.length : 0;
  const points = Array.isArray(payload.times_sec) ? payload.times_sec.length : 0;
  const matrixPoints = Array.isArray(payload.data_uv) ? payload.data_uv.reduce((sum, row) => sum + (Array.isArray(row) ? row.length : 0), 0) : 0;
  return {
    bytes,
    channels,
    points,
    matrixPoints,
    start_sec: payload.start_sec ?? payload.window?.start_sec,
    duration_sec: payload.duration_sec ?? payload.window_sec ?? payload.window?.duration_sec,
    file_duration_sec: payload.file_duration_sec ?? payload.duration_total_sec,
    display_sample_rate_hz: payload.display_sample_rate_hz ?? payload.sfreq_display ?? payload.sample_rate_hz,
    approx_bytes_per_matrix_point: matrixPoints ? Math.round((bytes / matrixPoints) * 10) / 10 : null,
  };
}

async function browserBench() {
  const browser = await chromium.launch(chromiumLaunchOptions({ headless: true }));
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  try {
    const nav = await timed("browser.page.goto_domcontentloaded", () => page.goto(frontendUrl, { waitUntil: "domcontentloaded", timeout: 30000 }));
    const loaded = await timed("browser.wait_loaded", () => page.waitForFunction(
      () => document.querySelector("[data-testid='waveform-workbench-shell']")?.dataset.loaded === "true",
      null,
      { timeout: 45000 },
    ));
    const state = await page.evaluate(() => {
      const shell = document.querySelector("[data-testid='waveform-workbench-shell']");
      const canvas = document.querySelector("#wwCanvas");
      const rect = canvas?.getBoundingClientRect();
      return {
        loaded: shell?.dataset.loaded,
        fileName: shell?.dataset.fileName,
        startSec: Number(shell?.dataset.startSec || 0),
        durationSec: Number(shell?.dataset.durationSec || 0),
        windowCoverage: shell?.dataset.windowCoverage,
        waveformSource: shell?.dataset.waveformSource,
        waveformSchemaVersion: shell?.dataset.waveformSchemaVersion,
        waveformLastReloadSource: shell?.dataset.waveformLastReloadSource,
        waveformCacheHits: Number(shell?.dataset.waveformCacheHits || 0),
        waveformChunkRequests: Number(shell?.dataset.waveformChunkRequests || 0),
        waveformChunkAborts: Number(shell?.dataset.waveformChunkAborts || 0),
        waveformChunkFallbacks: Number(shell?.dataset.waveformChunkFallbacks || 0),
        waveformPrefetchRequests: Number(shell?.dataset.waveformPrefetchRequests || 0),
        waveformPrefetchInFlight: Number(shell?.dataset.waveformPrefetchInFlight || 0),
        cacheChunkCount: Number(shell?.dataset.cacheChunkCount || 0),
        cacheLoadedRanges: shell?.dataset.cacheLoadedRanges,
        usesRemappedFallback: shell?.dataset.usesRemappedFallback,
        canvas: rect ? { width: rect.width, height: rect.height } : null,
      };
    });
    const wheel = await timed("browser.wheel_pan_state_update", async () => {
      const box = state.canvas;
      await page.mouse.move(120 + box.width * 0.5, 360 + box.height * 0.45);
      await page.mouse.wheel(0, 600);
      await page.waitForTimeout(120);
      return page.evaluate(() => {
        const shell = document.querySelector("[data-testid='waveform-workbench-shell']");
        return {
          startSec: Number(shell?.dataset.startSec || 0),
          windowCoverage: shell?.dataset.windowCoverage,
          waveformSource: shell?.dataset.waveformSource,
          waveformLastReloadSource: shell?.dataset.waveformLastReloadSource,
          waveformCacheHits: Number(shell?.dataset.waveformCacheHits || 0),
          waveformChunkRequests: Number(shell?.dataset.waveformChunkRequests || 0),
          waveformChunkAborts: Number(shell?.dataset.waveformChunkAborts || 0),
          waveformChunkFallbacks: Number(shell?.dataset.waveformChunkFallbacks || 0),
          waveformPrefetchRequests: Number(shell?.dataset.waveformPrefetchRequests || 0),
          waveformPrefetchInFlight: Number(shell?.dataset.waveformPrefetchInFlight || 0),
          loadingState: shell?.dataset.loadingState,
          pending: shell?.dataset.cachePendingRange,
          usesRemappedFallback: shell?.dataset.usesRemappedFallback,
        };
      });
    });
    return { nav, loaded, state, wheel };
  } finally {
    await browser.close();
  }
}

async function main() {
  const result = {
    generated_at: new Date().toISOString(),
    apiBase,
    frontendUrl,
    includeLegacyTaskBench,
    timings: [],
    summaries: {},
    recommendations_basis: [],
  };

  const health = await timed("api.health", () => jsonFetch(`${apiBase}/health`));
  result.timings.push({ label: health.label, ok: health.ok, ms: health.ms, error: health.error });

  const demo = await timed("api.lab_demo_dataset", () => jsonFetch(`${apiBase}/lab/demo/dataset`));
  result.timings.push({ label: demo.label, ok: demo.ok, ms: demo.ms, error: demo.error });
  if (!demo.ok) throw new Error(demo.error);
  const demoData = demo.value.data;
  result.summaries.demo = {
    bytes: demo.value.bytes,
    project_id: demoData.project?.id,
    file_id: demoData.file?.id,
    file_duration_sec: demoData.file?.duration_sec,
    qc_preview_task_id: demoData.qc_preview_task?.id,
    qc_preview_task_status: demoData.qc_preview_task?.status,
    qc_preview_task_created_at: demoData.qc_preview_task?.created_at,
  };

  const chunkUrl = `${apiBase}/eeg/files/${encodeURIComponent(demoData.file.id)}/waveform/chunk?start_sec=0&duration_sec=24&channel_limit=8&display_sfreq=200&mode=minmax&width_px=1440`;
  const chunkFirst = await timed("api.waveform_chunk_0_24_first", () => jsonFetch(chunkUrl));
  result.timings.push({ label: chunkFirst.label, ok: chunkFirst.ok, ms: chunkFirst.ms, error: chunkFirst.error });
  if (chunkFirst.ok) result.summaries.waveform_chunk_first = summarizePayload(chunkFirst.value.data, chunkFirst.value.bytes);

  const chunkWarm = await timed("api.waveform_chunk_0_24_warm", () => jsonFetch(chunkUrl));
  result.timings.push({ label: chunkWarm.label, ok: chunkWarm.ok, ms: chunkWarm.ms, error: chunkWarm.error });
  if (chunkWarm.ok) result.summaries.waveform_chunk_warm = summarizePayload(chunkWarm.value.data, chunkWarm.value.bytes);

  if (includeLegacyTaskBench) {
    const taskParams = {
      project_id: demoData.project.id,
      input_file_id: demoData.file.id,
      module_name: "qc",
      workflow_id: "qc_waveform_preview",
      parameters_json: {
        fast_ui_preview: true,
        preview: { start_sec: 0, duration_sec: 24, channel_limit: 8, display_sfreq: 200 },
        filter_preview: { enabled: false },
      },
      owner_user_id: "local-user",
      created_by: "local-user",
    };
    const task = await timed("api.create_qc_preview_task_0_24_legacy", () => jsonFetch(`${apiBase}/tasks`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(taskParams),
    }));
    result.timings.push({ label: task.label, ok: task.ok, ms: task.ms, error: task.error });
    if (task.ok) {
      result.summaries.created_task = { id: task.value.data.id, status: task.value.data.status };
      const artifactWait = await timed("api.wait_waveform_artifact_legacy", () => waitForArtifact(task.value.data.id));
      result.timings.push({ label: artifactWait.label, ok: artifactWait.ok, ms: artifactWait.ms, error: artifactWait.error, polls: artifactWait.value?.polls });
      if (artifactWait.ok) {
        const download = await timed("api.download_waveform_json_legacy", () => jsonFetch(`${apiBase}/artifacts/${encodeURIComponent(artifactWait.value.artifact.id)}/download`));
        result.timings.push({ label: download.label, ok: download.ok, ms: download.ms, error: download.error });
        if (download.ok) result.summaries.waveform_payload_legacy = summarizePayload(download.value.data, download.value.bytes);
      }
    }
  } else {
    result.summaries.legacy_task_benchmark = {
      skipped: true,
      reason: "Set QLANALYSER_INCLUDE_LEGACY_TASK_BENCH=1 to re-run the old QC task path. Default benchmark avoids the known 95s task wait.",
    };
  }

  const browser = await timed("browser.workbench", browserBench);
  result.timings.push({ label: browser.label, ok: browser.ok, ms: browser.ms, error: browser.error });
  if (browser.ok) result.summaries.browser = browser.value;

  result.recommendations_basis = result.timings.map((item) => `${item.label}: ${item.ok ? `${item.ms}ms` : `FAILED ${item.error?.slice(0, 160)}`}`);

  const outputPath = path.join(evidenceDir, "waveform_latency_benchmark.json");
  fs.writeFileSync(outputPath, `${JSON.stringify(result, null, 2)}\n`, "utf8");
  console.log(JSON.stringify({ status: "completed", outputPath, timings: result.timings, summaries: result.summaries }, null, 2));
}

await main().catch((error) => {
  const outputPath = path.join(evidenceDir, "waveform_latency_benchmark.json");
  fs.writeFileSync(outputPath, `${JSON.stringify({ status: "failed", error: error.stack || String(error), generated_at: new Date().toISOString() }, null, 2)}\n`, "utf8");
  console.error(error.stack || String(error));
  process.exit(1);
});
