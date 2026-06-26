import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";
const require = createRequire(import.meta.url);
let chromium;
try {
  ({ chromium } = require("../frontend/node_modules/playwright"));
} catch {
  ({ chromium } = require("playwright"));
}
const API_BASE = process.env.QLANALYSER_API_BASE_URL || "http://127.0.0.1:8001/api";
const FRONTEND_URL = process.env.QLANALYSER_FRONTEND_URL || `http://127.0.0.1:4174/index.html?customer_demo=auto&api=${encodeURIComponent(API_BASE)}`;
const OUT_DIR = path.resolve("work/release_evidence/20260627-waveform-interaction");
const OUT_JSON = path.join(OUT_DIR, "waveform_interaction_e2e.json");
const SCREENSHOT = path.join(OUT_DIR, "waveform_interaction_after_exclude.png");
function localBrowserExecutable() { return ["C:/Program Files/Microsoft/Edge/Application/msedge.exe", "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"].find(fs.existsSync) || ""; }
async function canvasStats(page) {
  return page.locator("#eegCanvas").evaluate((canvas) => {
    const ctx = canvas.getContext("2d");
    const img = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
    let red = 0, pink = 0, nonWhite = 0;
    for (let i = 0; i < img.length; i += 64) {
      const r = img[i], g = img[i + 1], b = img[i + 2];
      if (r < 245 || g < 245 || b < 245) nonWhite += 1;
      if (r > 170 && g < 120 && b < 120) red += 1;
      if (r > 160 && b > 120 && g < 170) pink += 1;
    }
    const rect = canvas.getBoundingClientRect();
    return { nonWhite, red, pink, rect: { width: rect.width, height: rect.height } };
  });
}
const checks = [];
const add = (name, pass, details = {}) => checks.push({ name, pass: Boolean(pass), details });
fs.mkdirSync(OUT_DIR, { recursive: true });
const browser = await chromium.launch({ headless: true, ...(localBrowserExecutable() ? { executablePath: localBrowserExecutable() } : {}) });
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
try {
  await page.goto(FRONTEND_URL, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForSelector("#appShell, #loginScreen", { timeout: 30000 });
  if (await page.locator("#customerLoginBtn").isVisible().catch(() => false)) await page.click("#customerLoginBtn");
  await page.waitForSelector("#appShell:not([hidden]), .main", { timeout: 30000 });
  await page.click("#teachingModeBtn");
  await page.waitForSelector("#teachingOverlay.active", { timeout: 60000 });
  await page.locator('#teachingOverlay [data-teaching-action="next"].primary-btn').click({ force: true });
  await page.waitForFunction(() => document.querySelector("#teachingStepTitle")?.textContent?.includes("2/8"), null, { timeout: 30000 });
  await page.locator('#teachingOverlay [data-teaching-action="next"].primary-btn').click({ force: true });
  await page.waitForFunction(() => document.querySelector("#analysis")?.classList.contains("active"), null, { timeout: 30000 });
  await page.evaluate(() => { const o = document.querySelector("#teachingOverlay"); if (o) { o.classList.remove("active"); o.hidden = true; o.style.display = "none"; o.style.pointerEvents = "none"; } document.body.classList.remove("teaching-mode-active"); });
  await page.waitForSelector("#eegCanvas", { state: "visible", timeout: 30000 });
  await page.waitForFunction(() => document.querySelector("#eegCanvas")?.getBoundingClientRect().width > 500, null, { timeout: 30000 });
  const box = await page.locator("#eegCanvas").boundingBox();
  await page.mouse.move(box.x + box.width * 0.28, box.y + box.height * 0.45);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * 0.52, box.y + box.height * 0.45, { steps: 8 });
  await page.mouse.up();
  const afterDrag = await canvasStats(page);
  const selected = await page.evaluate(() => ({ start: document.querySelector("#segmentStart")?.value, end: document.querySelector("#segmentEnd")?.value, summary: document.querySelector("#eegEvents")?.textContent || "", status: document.querySelector('[data-testid="waveform-workbench-status"]')?.textContent || "" }));
  add("drag_selects_segment", Number(selected.end) > Number(selected.start) && (afterDrag.pink > 0 || selected.status.includes("选段")), { selected, afterDrag });
  await page.click('[data-ia-action="exclude-segment"]');
  await page.waitForTimeout(300);
  const afterExclude = await canvasStats(page);
  const excludedCount = await page.evaluate(() => window.qlanalyserUiActionAudit?.filter?.((item) => item.action === "ia:exclude-segment" && item.verdict === "pass").length || 0);
  const excludedStatus = await page.evaluate(() => document.querySelector('[data-testid="waveform-workbench-status"]')?.textContent || "");
  add("exclude_segment_draws_red_band", excludedCount > 0 && (afterExclude.red > 0 || excludedStatus.includes("剔除 1")), { excludedCount, afterExclude, excludedStatus });
  await page.screenshot({ path: SCREENSHOT, fullPage: true });
  await page.click('[data-ia-action="restore-segment"]');
  await page.waitForTimeout(300);
  const afterRestore = await page.evaluate(() => (document.querySelector("#segmentSummary")?.textContent || "") + " " + (document.querySelector('[data-testid="waveform-workbench-status"]')?.textContent || ""));
  add("restore_segment_is_recorded", /恢复|鎭/.test(afterRestore), { afterRestore });
} catch (error) {
  add("unexpected_error", false, { message: error.message || String(error) });
  await page.screenshot({ path: SCREENSHOT, fullPage: true }).catch(() => {});
} finally {
  await browser.close();
}
const report = { status: checks.every((item) => item.pass) ? "passed" : "failed", frontendUrl: FRONTEND_URL, apiBase: API_BASE, generatedAt: new Date().toISOString(), checks, screenshot: SCREENSHOT };
fs.writeFileSync(OUT_JSON, JSON.stringify(report, null, 2) + "\n", "utf8");
console.log(JSON.stringify(report, null, 2));
process.exit(report.status === "passed" ? 0 : 1);
