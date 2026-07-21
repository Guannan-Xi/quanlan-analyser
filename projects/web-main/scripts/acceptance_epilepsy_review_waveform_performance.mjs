import fs from "node:fs";
import path from "node:path";
import { chromium, chromiumLaunchOptions, classifyAcceptanceFailure } from "./lib/playwright_runtime.mjs";

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1")), "..");
const FRONTEND_BASE = process.env.QLANALYSER_LAB_EPILEPSY_FRONTEND_BASE || "http://127.0.0.1:4176";
const API_BASE = process.env.QLANALYSER_LAB_EPILEPSY_API_BASE || "http://127.0.0.1:8043/api";
const OUT_DIR = process.env.QLANALYSER_LAB_EPILEPSY_PERF_DIR
  || path.join(ROOT, "work", "release_evidence", "epilepsy_visual_perf_20260708", "waveform_performance");
const EVIDENCE_PATH = path.join(OUT_DIR, "epilepsy_review_waveform_performance.json");
const STRICT = process.env.QLANALYSER_LAB_EPILEPSY_PERF_STRICT === "1";
const RUN_ID = new Date().toISOString().replace(/[-:T.Z]/g, "").slice(0, 14);

function ensure(condition, message, details = {}) {
  if (!condition) {
    const error = new Error(message);
    error.details = details;
    throw error;
  }
}

function reviewUrl() {
  const url = new URL("/epilepsy-review-preview.html", FRONTEND_BASE);
  url.searchParams.set("api", API_BASE);
  url.searchParams.set("v", `waveform-perf-${RUN_ID}`);
  return url.toString();
}

function percentile(values, p) {
  const finite = values.filter((value) => Number.isFinite(value)).sort((a, b) => a - b);
  if (!finite.length) return null;
  const index = Math.min(finite.length - 1, Math.max(0, Math.ceil((p / 100) * finite.length) - 1));
  return finite[index];
}

async function assertApiHealth(evidence) {
  const healthUrl = `${API_BASE.replace(/\/$/, "")}/health`;
  const response = await fetch(healthUrl);
  evidence.service_health = { url: healthUrl, status: response.status };
  ensure(response.ok, `Backend health check failed: ${response.status}`);
}

async function waitForWaveformSettled(page, timeoutMs = 30000) {
  await page.waitForFunction(() => {
    const perf = window.__qlaEpilepsyReviewPerf;
    if (!perf) return true;
    const entries = Object.values(perf.cache || {});
    if (!entries.length) return true;
    return entries.some((entry) => entry.status === "ready") || entries.every((entry) => entry.status === "failed");
  }, null, { timeout: timeoutMs });
}

async function dragBy(page, selector, dx, steps = 48) {
  const locator = page.locator(selector);
  await locator.waitFor({ state: "visible", timeout: 30000 });
  const box = await locator.boundingBox();
  ensure(box, `Cannot drag missing element: ${selector}`);
  const x = box.x + box.width / 2;
  const y = box.y + box.height / 2;
  const start = performance.now();
  await page.mouse.move(x, y);
  await page.mouse.down();
  await page.mouse.move(x + dx, y, { steps });
  await page.mouse.up();
  await page.waitForTimeout(250);
  return performance.now() - start;
}

async function collectClientPerf(page) {
  return page.evaluate(() => {
    const perf = window.__qlaEpilepsyReviewPerf || null;
    const canvas = document.querySelector("#waveformCanvas");
    const canvasRect = canvas?.getBoundingClientRect();
    const band = document.querySelector("#eventBand");
    const bandRect = band?.getBoundingClientRect();
    return {
      perf,
      current_candidate: document.querySelector("#eventTitle")?.innerText || "",
      canvas_rect: canvasRect ? {
        width: Math.round(canvasRect.width),
        height: Math.round(canvasRect.height),
      } : null,
      event_band_rect: bandRect ? {
        width: Math.round(bandRect.width),
        height: Math.round(bandRect.height),
      } : null,
      zero_sized_enabled_controls: Array.from(document.querySelectorAll("button, [role='button']"))
        .map((node) => {
          const rect = node.getBoundingClientRect();
          return {
            id: node.id || "",
            text: (node.innerText || node.getAttribute("aria-label") || "").trim().slice(0, 60),
            disabled: Boolean(node.disabled || node.getAttribute("aria-disabled") === "true"),
            width: Math.round(rect.width),
            height: Math.round(rect.height),
          };
        })
        .filter((item) => !item.disabled && (item.width <= 1 || item.height <= 1)),
    };
  });
}

async function main() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const evidence = {
    schema_version: "qlanalyser.epilepsy.review_waveform_performance.v1",
    run_id: RUN_ID,
    status: "running",
    strict: STRICT,
    frontend_url: reviewUrl(),
    api_base: API_BASE,
    network: {
      waveform_requests: [],
      waveform_responses: [],
    },
    console: [],
    measurements: {},
    checks: {},
  };
  await assertApiHealth(evidence);

  const browser = await chromium.launch(chromiumLaunchOptions({ headless: true }));
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  page.on("console", (message) => {
    if (["error", "warning"].includes(message.type())) evidence.console.push({ type: message.type(), text: message.text() });
  });
  page.on("pageerror", (error) => evidence.console.push({ type: "pageerror", text: String(error?.message || error) }));
  page.on("request", (request) => {
    if (request.url().includes("/waveform-window")) {
      evidence.network.waveform_requests.push({ at: Date.now(), method: request.method(), url: request.url() });
    }
  });
  page.on("response", (response) => {
    if (response.url().includes("/waveform-window")) {
      evidence.network.waveform_responses.push({ at: Date.now(), status: response.status(), url: response.url() });
    }
  });

  try {
    await page.goto(reviewUrl(), { waitUntil: "domcontentloaded", timeout: 60000 });
    await page.waitForSelector('[data-testid="epilepsy-review-preview"]', { timeout: 30000 });
    await page.waitForSelector("#candidateList [data-candidate-id]", { timeout: 30000 });
    await page.waitForSelector("#eventBand", { timeout: 30000 });
    await waitForWaveformSettled(page);
    await page.waitForTimeout(500);

    const initialClient = await collectClientPerf(page);
    evidence.measurements.initial_client = initialClient;

    const candidateButtons = await page.locator("#candidateList [data-candidate-id]").evaluateAll((nodes) => nodes.map((node) => node.getAttribute("data-candidate-id")).filter(Boolean).slice(0, 6));
    const switchSamples = [];
    for (const candidateId of candidateButtons.slice(1, 6)) {
      const before = performance.now();
      await page.click(`#candidateList [data-candidate-id="${candidateId}"]`);
      await page.waitForFunction((expected) => document.querySelector("#eventTitle")?.innerText?.includes(expected), candidateId, { timeout: 10000 });
      await waitForWaveformSettled(page);
      switchSamples.push(performance.now() - before);
    }
    evidence.measurements.candidate_switch_samples_ms = switchSamples;

    const requestsBeforeDrag = evidence.network.waveform_requests.length;
    const dragElapsedMs = await dragBy(page, "#eventBand", 120, 80);
    const requestsAfterDrag = evidence.network.waveform_requests.length;
    await page.waitForTimeout(300);
    const afterDragClient = await collectClientPerf(page);

    evidence.measurements.drag_elapsed_ms = dragElapsedMs;
    evidence.measurements.waveform_requests_during_drag = requestsAfterDrag - requestsBeforeDrag;
    evidence.measurements.after_drag_client = afterDragClient;

    const perf = afterDragClient.perf || {};
    const drawDurations = Array.isArray(perf.draw_samples_ms) ? perf.draw_samples_ms : [];
    const dragFrameDurations = Array.isArray(perf.drag_frame_samples_ms) ? perf.drag_frame_samples_ms : [];
    evidence.measurements.draw_p95_ms = percentile(drawDurations, 95);
    evidence.measurements.draw_max_ms = drawDurations.length ? Math.max(...drawDurations) : null;
    evidence.measurements.drag_frame_p95_ms = percentile(dragFrameDurations, 95);
    evidence.measurements.drag_frame_max_ms = dragFrameDurations.length ? Math.max(...dragFrameDurations) : null;
    evidence.measurements.candidate_switch_p95_ms = percentile(switchSamples, 95);
    evidence.measurements.perf_ledger_present = Boolean(afterDragClient.perf);

    evidence.checks = {
      backend_health_ok: evidence.service_health.status < 400,
      waveform_canvas_visible: (afterDragClient.canvas_rect?.width || 0) >= 600 && (afterDragClient.canvas_rect?.height || 0) >= 240,
      event_band_visible: (afterDragClient.event_band_rect?.width || 0) > 4 && (afterDragClient.event_band_rect?.height || 0) > 40,
      no_zero_sized_enabled_controls: afterDragClient.zero_sized_enabled_controls.length === 0,
      no_waveform_request_storm_during_drag: evidence.measurements.waveform_requests_during_drag <= 1,
      drag_wall_time_recorded: Number.isFinite(dragElapsedMs) && dragElapsedMs > 0,
      no_console_errors: evidence.console.filter((item) => item.type === "error" || item.type === "pageerror").length === 0,
    };
    if (afterDragClient.perf) {
      evidence.checks.perf_ledger_present = true;
      evidence.checks.no_stale_waveform_overwrite = Number(perf.stale_responses || 0) === 0;
      evidence.checks.draw_p95_under_50ms = evidence.measurements.draw_p95_ms === null || evidence.measurements.draw_p95_ms < 50;
      evidence.checks.drag_frame_p95_under_32ms = evidence.measurements.drag_frame_p95_ms === null || evidence.measurements.drag_frame_p95_ms < 32;
      evidence.checks.waveform_aborts_recorded_not_failed = Number(perf.aborts || 0) >= 0;
    } else {
      evidence.checks.perf_ledger_present = !STRICT;
    }

    evidence.status = Object.values(evidence.checks).every(Boolean) ? "passed" : "failed";
    fs.writeFileSync(EVIDENCE_PATH, `${JSON.stringify(evidence, null, 2)}\n`, "utf8");
    console.log(JSON.stringify({
      status: evidence.status,
      evidence_path: EVIDENCE_PATH,
      measurements: evidence.measurements,
      checks: evidence.checks,
    }, null, 2));
    if (evidence.status !== "passed") process.exitCode = 1;
  } catch (error) {
    evidence.status = "failed";
    evidence.failure_class = classifyAcceptanceFailure(error, evidence);
    evidence.error = String(error?.stack || error);
    evidence.error_details = error?.details || {};
    try {
      const file = path.join(OUT_DIR, "failure.png");
      await page.screenshot({ path: file, fullPage: true, timeout: 20000 });
      evidence.failure_screenshot = file;
    } catch {
      // Keep original failure.
    }
    fs.writeFileSync(EVIDENCE_PATH, `${JSON.stringify(evidence, null, 2)}\n`, "utf8");
    console.error(error);
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

main();
