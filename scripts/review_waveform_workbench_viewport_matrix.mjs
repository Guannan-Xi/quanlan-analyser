import fs from "node:fs";
import path from "node:path";
import { chromium, chromiumLaunchOptions } from "./lib/playwright_runtime.mjs";

const repoRoot = process.cwd();
const evidenceDir = process.env.QLANALYSER_WAVEFORM_VIEWPORT_REVIEW_DIR
  || path.join(repoRoot, "work", "release_evidence", "20260628-waveform-customer-viewport-matrix");
const apiBase = process.env.QLANALYSER_API_BASE || "http://127.0.0.1:8001/api";
const frontendUrl = process.env.QLANALYSER_WAVEFORM_WORKBENCH_URL
  || `http://127.0.0.1:4174/waveform-workbench.html?teaching_demo=auto&api=${encodeURIComponent(apiBase)}&v=viewport-matrix`;

fs.mkdirSync(evidenceDir, { recursive: true });

const viewports = [
  { id: "desktop_1440", width: 1440, height: 900 },
  { id: "laptop_1280", width: 1280, height: 820 },
  { id: "mobile_390", width: 390, height: 844 },
];

function pass(id, details = {}) {
  return { id, passed: true, ...details };
}

function fail(id, details = {}) {
  return { id, passed: false, ...details };
}

async function canvasInk(page) {
  return page.evaluate(() => {
    const canvas = document.querySelector("#wwCanvas");
    if (!canvas) return { checked: 0, ink: 0, ratio: 0 };
    const ctx = canvas.getContext("2d");
    const { width, height } = canvas;
    const data = ctx.getImageData(0, 0, width, height).data;
    let checked = 0;
    let ink = 0;
    const step = Math.max(5, Math.floor(Math.sqrt((width * height) / 18000)));
    for (let y = 0; y < height; y += step) {
      for (let x = 0; x < width; x += step) {
        const idx = (y * width + x) * 4;
        checked += 1;
        if (data[idx + 3] > 0 && (data[idx] < 245 || data[idx + 1] < 245 || data[idx + 2] < 245)) ink += 1;
      }
    }
    return { checked, ink, ratio: checked ? ink / checked : 0 };
  });
}

async function inspectViewport(page, vp) {
  await page.setViewportSize({ width: vp.width, height: vp.height });
  await page.goto(frontendUrl, { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.waitForFunction(() => document.querySelector("[data-testid='waveform-workbench-shell']")?.dataset.loaded === "true", null, { timeout: 30000 });
  await page.waitForFunction(() => {
    const canvas = document.querySelector("#wwCanvas");
    if (!canvas) return false;
    const ctx = canvas.getContext("2d");
    const { width, height } = canvas;
    const data = ctx.getImageData(0, 0, width, height).data;
    let checked = 0;
    let ink = 0;
    const step = Math.max(5, Math.floor(Math.sqrt((width * height) / 18000)));
    for (let y = 0; y < height; y += step) {
      for (let x = 0; x < width; x += step) {
        const idx = (y * width + x) * 4;
        checked += 1;
        if (data[idx + 3] > 0 && (data[idx] < 245 || data[idx + 1] < 245 || data[idx + 2] < 245)) ink += 1;
      }
    }
    return checked > 0 && ink / checked > 0.01;
  }, null, { timeout: 10000 });

  const topPath = path.join(evidenceDir, `${vp.id}_top.png`);
  await page.screenshot({ path: topPath, fullPage: false });

  await page.evaluate(() => window.scrollTo(0, Math.floor(document.body.scrollHeight * 0.45)));
  await page.waitForTimeout(200);
  const middlePath = path.join(evidenceDir, `${vp.id}_middle.png`);
  await page.screenshot({ path: middlePath, fullPage: false });

  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await page.waitForTimeout(200);
  const bottomPath = path.join(evidenceDir, `${vp.id}_bottom.png`);
  await page.screenshot({ path: bottomPath, fullPage: false });

  const dom = await page.evaluate(() => {
    const shell = document.querySelector("[data-testid='waveform-workbench-shell']");
    const toolbar = document.querySelector(".ww-toolbar");
    const canvas = document.querySelector("#wwCanvas");
    const sidePanel = document.querySelector(".ww-side-panel");
    const overview = document.querySelector("#wwOverviewCaption");
    const status = document.querySelector("#wwStatus");
    const reviewActions = document.querySelector(".ww-review-actions");
    const rect = (el) => {
      const r = el?.getBoundingClientRect();
      return r ? { x: r.x, y: r.y, width: r.width, height: r.height, bottom: r.bottom } : null;
    };
    return {
      viewport: { width: window.innerWidth, height: window.innerHeight },
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
      bodyHeight: document.body.scrollHeight,
      shellLoaded: shell?.dataset.loaded === "true",
      waveformSource: shell?.dataset.waveformSource || "",
      toolbar: rect(toolbar),
      canvas: rect(canvas),
      sidePanel: rect(sidePanel),
      overviewText: overview?.textContent || "",
      statusText: status?.textContent || "",
      reviewActionsHidden: reviewActions?.classList.contains("is-empty") || false,
    };
  });
  const ink = await canvasInk(page);
  return { viewport: vp, screenshots: { top: topPath, middle: middlePath, bottom: bottomPath }, dom, ink };
}

async function main() {
  const browser = await chromium.launch(chromiumLaunchOptions({ headless: true }));
  const page = await browser.newPage();
  try {
    const results = [];
    for (const vp of viewports) {
      results.push(await inspectViewport(page, vp));
    }
    const checks = [];
    for (const result of results) {
      const { id, width } = result.viewport;
      checks.push(result.dom.shellLoaded && result.dom.waveformSource === "waveform_chunk_api"
        ? pass(`${id}:loaded_chunk_api`, { waveformSource: result.dom.waveformSource })
        : fail(`${id}:loaded_chunk_api`, result.dom));
      checks.push(result.ink.ratio > 0.01
        ? pass(`${id}:canvas_visible`, result.ink)
        : fail(`${id}:canvas_visible`, result.ink));
      checks.push(result.dom.scrollWidth <= result.dom.clientWidth + 2
        ? pass(`${id}:no_horizontal_overflow`, { scrollWidth: result.dom.scrollWidth, clientWidth: result.dom.clientWidth })
        : fail(`${id}:no_horizontal_overflow`, { scrollWidth: result.dom.scrollWidth, clientWidth: result.dom.clientWidth }));
      checks.push(!/\d+\.\d-\d+\.\ds,\s*\d+\.\d-\d+\.\ds,\s*\d+\.\d-\d+\.\ds/.test(result.dom.overviewText)
        ? pass(`${id}:no_cache_log_noise`, { overviewText: result.dom.overviewText })
        : fail(`${id}:no_cache_log_noise`, { overviewText: result.dom.overviewText }));
      if (width >= 760) {
        checks.push(result.dom.toolbar?.height <= 280
          ? pass(`${id}:toolbar_height_reasonable`, { toolbar: result.dom.toolbar })
          : fail(`${id}:toolbar_height_reasonable`, { toolbar: result.dom.toolbar }));
      } else {
        checks.push(result.dom.toolbar?.height <= 760
          ? pass(`${id}:mobile_toolbar_not_unbounded`, { toolbar: result.dom.toolbar })
          : fail(`${id}:mobile_toolbar_not_unbounded`, { toolbar: result.dom.toolbar }));
      }
    }
    const output = {
      status: checks.every((check) => check.passed) ? "passed" : "failed",
      generated_at: new Date().toISOString(),
      frontendUrl,
      evidenceDir,
      results,
      checks,
    };
    const outputPath = path.join(evidenceDir, "viewport_matrix_result.json");
    fs.writeFileSync(outputPath, `${JSON.stringify(output, null, 2)}\n`, "utf8");
    console.log(JSON.stringify({
      status: output.status,
      outputPath,
      failed: checks.filter((check) => !check.passed).map((check) => check.id),
      screenshots: Object.fromEntries(results.map((result) => [result.viewport.id, result.screenshots])),
    }, null, 2));
    if (output.status !== "passed") process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

await main().catch((error) => {
  const outputPath = path.join(evidenceDir, "viewport_matrix_result.json");
  fs.writeFileSync(outputPath, `${JSON.stringify({ status: "failed", error: error.stack || String(error), generated_at: new Date().toISOString(), frontendUrl }, null, 2)}\n`, "utf8");
  console.error(error.stack || String(error));
  process.exit(1);
});
