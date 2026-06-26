import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";
const require = createRequire(import.meta.url);
const { chromium } = require("../frontend/node_modules/playwright");
const API_BASE = process.env.QLANALYSER_API_BASE_URL || "http://127.0.0.1:8001/api";
const FRONTEND_URL = process.env.QLANALYSER_FRONTEND_URL || `http://127.0.0.1:4174/index.html?customer_demo=auto&api=${encodeURIComponent(API_BASE)}`;
const OUT_DIR = path.resolve("work/release_evidence/20260627-data-preparation-workbench");
fs.mkdirSync(OUT_DIR, { recursive: true });
const OUT_JSON = path.join(OUT_DIR, "data_preparation_workbench_e2e.json");
const SCREENSHOT = path.join(OUT_DIR, "data_preparation_workbench.png");
function localBrowserExecutable() {
  return ["C:/Program Files/Microsoft/Edge/Application/msedge.exe", "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"].find(fs.existsSync) || "";
}
async function canvasStats(page) {
  return page.locator("#eegCanvas").evaluate((canvas) => {
    const ctx = canvas.getContext("2d");
    const data = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
    let nonWhite = 0; let dark = 0;
    for (let i = 0; i < data.length; i += 16) {
      const r = data[i], g = data[i + 1], b = data[i + 2], a = data[i + 3];
      if (a && (r < 245 || g < 245 || b < 245)) nonWhite += 1;
      if (a && r < 120 && g < 140 && b < 160) dark += 1;
    }
    return { width: canvas.width, height: canvas.height, nonWhite, dark };
  });
}
const browser = await chromium.launch({ headless: true, ...(localBrowserExecutable() ? { executablePath: localBrowserExecutable() } : {}) });
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
const requests = [];
const checks = [];
const add = (name, pass, details = {}) => checks.push({ name, pass: Boolean(pass), details });
page.on("request", (req) => { if (req.url().includes("/api/")) requests.push({ url: req.url(), method: req.method(), post: req.postDataJSON?.() || null }); });
try {
  await page.goto(FRONTEND_URL, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForSelector("#appShell:not([hidden]), #loginScreen", { timeout: 30000 });
  if (await page.locator("#customerLoginBtn").isVisible().catch(() => false)) await page.click("#customerLoginBtn");
  await page.waitForSelector("#appShell:not([hidden]), .main", { timeout: 30000 });
  await page.click("#teachingModeBtn");
  await page.waitForSelector("#teachingOverlay.active", { timeout: 60000 });
  for (let i = 0; i < 8; i += 1) {
    if (!(await page.locator("#teachingOverlay.active").isVisible().catch(() => false))) break;
    await page.locator('#teachingOverlay [data-teaching-action="next"].primary-btn').click({ force: true });
    await page.waitForTimeout(200);
  }
  await page.waitForFunction(() => document.body.classList.contains("teaching-sandbox-active") && !document.querySelector("#teachingOverlay.active"), null, { timeout: 30000 });
  await page.click('[data-view="analysis"]');
  await page.waitForSelector("#eegCanvas", { timeout: 30000 });
  await page.waitForFunction(() => {
    const canvas = document.querySelector("#eegCanvas");
    const ctx = canvas?.getContext?.("2d");
    if (!canvas || !ctx) return false;
    const sample = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
    for (let i = 0; i < sample.length; i += 40) if (sample[i + 3] && (sample[i] < 245 || sample[i + 1] < 245 || sample[i + 2] < 245)) return true;
    return false;
  }, null, { timeout: 120000 });
  const initialStats = await canvasStats(page);
  add("waveform_canvas_visible", initialStats.nonWhite > 1000 && initialStats.dark > 50, initialStats);
  const layout = await page.evaluate(() => {
    const main = document.querySelector(".waveform-main-column")?.getBoundingClientRect();
    const side = document.querySelector('[data-testid="preprocessing-inline-panel"]')?.getBoundingClientRect();
    const status = document.querySelector('[data-testid="waveform-workbench-status"]')?.innerText || "";
    return { main, side, sideSameRow: Boolean(main && side && Math.abs(main.top - side.top) < 80 && side.left > main.left), status };
  });
  add("preprocessing_panel_same_page_as_waveform", layout.sideSameRow, layout);
  await page.check("#eegFilterPreviewToggle");
  await page.waitForTimeout(500);
  await page.selectOption("#presetPrepReference", "channels");
  await page.fill("#presetPrepReferenceChannels", "Cz, M1, M2");
  await page.waitForFunction(() => document.querySelector('[data-testid="waveform-workbench-status"]')?.innerText.includes("指定通道"), null, { timeout: 10000 });
  const statusAfterFilterReference = await page.locator('[data-testid="waveform-workbench-status"]').innerText();
  add("filter_and_reference_status_visible", statusAfterFilterReference.includes("滤波预览开启") && statusAfterFilterReference.includes("指定通道"), { statusAfterFilterReference });
  const box = await page.locator("#eegCanvas").boundingBox();
  await page.mouse.move(box.x + box.width * 0.25, box.y + box.height * 0.45);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * 0.45, box.y + box.height * 0.45, { steps: 8 });
  await page.mouse.up();
  const selectedStatus = await page.locator('[data-testid="waveform-workbench-status"]').innerText();
  add("drag_selection_updates_status", selectedStatus.includes("选段") && !selectedStatus.includes("拖拽波形选择片段"), { selectedStatus });
  await page.click('[data-ia-action="exclude-segment"]');
  await page.waitForFunction(() => document.querySelector("#segmentSummary")?.innerText.includes("剔除") || document.querySelector('[data-testid="waveform-workbench-status"]')?.innerText.includes("剔除 1"), null, { timeout: 10000 });
  const afterExclude = await page.locator('[data-testid="waveform-workbench-status"]').innerText();
  await page.click('[data-ia-action="restore-segment"]');
  await page.waitForFunction(() => document.querySelector('[data-testid="waveform-workbench-status"]')?.innerText.includes("恢复 1"), null, { timeout: 10000 });
  const afterRestoreSegment = await page.locator('[data-testid="waveform-workbench-status"]').innerText();
  add("exclude_and_restore_segment_status", afterExclude.includes("剔除 1") && afterRestoreSegment.includes("恢复 1"), { afterExclude, afterRestoreSegment });
  await page.click('[data-ia-action="mark-bad-channel"]');
  await page.waitForFunction(() => document.querySelector('[data-testid="waveform-workbench-status"]')?.innerText.includes("坏道草稿") && document.querySelector('[data-testid="waveform-workbench-status"]')?.innerText.includes("1 条"), null, { timeout: 10000 });
  page.once("dialog", (dialog) => dialog.accept());
  await page.click('[data-ia-action="restore-bad-channel"]');
  await page.waitForFunction(() => document.querySelector('[data-testid="waveform-workbench-status"]')?.innerText.includes("可恢复 1 条"), null, { timeout: 10000 });
  const afterBadChannelRestore = await page.locator('[data-testid="waveform-workbench-status"]').innerText();
  add("bad_channel_mark_and_restore_status", afterBadChannelRestore.includes("坏道草稿") && afterBadChannelRestore.includes("可恢复 1 条"), { afterBadChannelRestore });
  const uploadReq = requests.find((r) => r.url.includes("/upload"));
  add("teaching_workbench_does_not_upload", !uploadReq, { uploadReq, apiRequestCount: requests.length });
  await page.screenshot({ path: SCREENSHOT, fullPage: true });
} catch (error) {
  add("unexpected_error", false, { message: error.message || String(error), requests });
  await page.screenshot({ path: SCREENSHOT, fullPage: true }).catch(() => {});
} finally {
  await browser.close();
}
const report = { status: checks.every((item) => item.pass) ? "passed" : "failed", frontendUrl: FRONTEND_URL, apiBase: API_BASE, generatedAt: new Date().toISOString(), checks, screenshot: SCREENSHOT };
fs.writeFileSync(OUT_JSON, `${JSON.stringify(report, null, 2)}\n`, "utf8");
console.log(JSON.stringify(report, null, 2));
process.exit(report.status === "passed" ? 0 : 1);
