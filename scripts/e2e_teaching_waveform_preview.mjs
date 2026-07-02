import { chromium, chromiumLaunchOptions } from "./lib/playwright_runtime.mjs";
import fs from "node:fs";
import path from "node:path";


const API_BASE = process.env.QLANALYSER_API_BASE_URL || "http://127.0.0.1:8001/api";
const FRONTEND_URL = process.env.QLANALYSER_FRONTEND_URL || `http://127.0.0.1:4174/index.html?customer_demo=auto&teaching_demo=auto&api=${encodeURIComponent(API_BASE)}`;
const OUT_DIR = path.resolve("work/release_evidence/20260626-teaching-waveform-preview");
const OUT_JSON = path.join(OUT_DIR, "teaching_waveform_preview_e2e.json");
const SCREENSHOT = path.join(OUT_DIR, "teaching_waveform_preview.png");

function localBrowserExecutable() {
  return [
    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  ].find((item) => fs.existsSync(item)) || "";
}

async function visible(page, selector) {
  return page.locator(selector).first().isVisible().catch(() => false);
}

async function canvasStats(page) {
  return page.evaluate(() => {
    const canvas = document.querySelector("#eegCanvas");
    const ctx = canvas?.getContext?.("2d");
    if (!canvas || !ctx || !canvas.width || !canvas.height) return { ok: false, reason: "missing_canvas" };
    const width = canvas.width;
    const height = canvas.height;
    const sample = ctx.getImageData(0, 0, width, height).data;
    let nonWhite = 0;
    let dark = 0;
    for (let i = 0; i < sample.length; i += 16) {
      const r = sample[i];
      const g = sample[i + 1];
      const b = sample[i + 2];
      if (r < 245 || g < 245 || b < 245) nonWhite += 1;
      if (r < 120 || g < 120 || b < 120) dark += 1;
    }
    return { ok: nonWhite > 120, width, height, nonWhite, dark };
  });
}

async function pageState(page) {
  return page.evaluate(() => ({
    hash: window.location.hash,
    activeViews: Array.from(document.querySelectorAll(".view.active")).map((node) => node.id),
    viewTitle: document.querySelector("#viewTitle")?.textContent?.trim() || "",
    bodyTextHead: document.body.innerText.slice(0, 1200),
    analysisClass: document.querySelector("#analysis")?.className || "",
    dashboardClass: document.querySelector("#dashboard")?.className || "",
    prepJumpCount: document.querySelectorAll('[data-view-jump="analysis"]').length,
    navAnalysisCount: document.querySelectorAll('[data-view="analysis"]').length,
  }));
}

async function main() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const checks = [];
  const add = (name, pass, details = {}) => checks.push({ name, pass: Boolean(pass), details });
  const browser = await chromium.launch({ headless: true, ...chromiumLaunchOptions() });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const taskRequests = [];
  page.on("request", (request) => {
    if (request.url().endsWith("/api/tasks") && request.method() === "POST") taskRequests.push(request.postDataJSON?.() || null);
  });
  let stage = "start";
  try {
    stage = "goto";
    await page.goto(FRONTEND_URL, { waitUntil: "domcontentloaded", timeout: 60000 });
    stage = "wait_login_or_shell";
    await page.waitForFunction(() => {
      const shell = document.querySelector("#appShell");
      const login = document.querySelector("#loginScreen");
      return Boolean((shell && !shell.hidden) || (login && !login.hidden));
    }, null, { timeout: 30000 });
    stage = "customer_login";
    if (await visible(page, "#customerLoginBtn")) await page.click("#customerLoginBtn");
    stage = "wait_shell";
    await page.waitForSelector("#appShell:not([hidden]), .main", { timeout: 30000 });
    stage = "click_teaching_mode";
    await page.click("#teachingModeBtn");
    stage = "wait_teaching_overlay";
    await page.waitForSelector("#teachingOverlay.active", { timeout: 60000 });
    stage = "teaching_step_2";
    await page.locator('#teachingOverlay [data-teaching-action="next"].primary-btn').click({ force: true });
    await page.waitForFunction(() => document.querySelector("#teachingStepTitle")?.textContent?.includes("2/8"), null, { timeout: 30000 });
    stage = "teaching_step_3_analysis";
    await page.locator('#teachingOverlay [data-teaching-action="next"].primary-btn').click({ force: true });
    await page.waitForFunction(() => document.querySelector("#teachingStepTitle")?.textContent?.includes("3/8") && document.querySelector("#analysis")?.classList.contains("active"), null, { timeout: 30000 });
    stage = "hide_teaching_overlay_for_canvas_audit";
    await page.evaluate(() => {
      const overlay = document.querySelector("#teachingOverlay");
      if (overlay) {
        overlay.classList.remove("active");
        overlay.setAttribute("hidden", "");
        overlay.style.display = "none";
        overlay.style.pointerEvents = "none";
      }
      document.body.classList.remove("teaching-mode-active");
      document.querySelectorAll(".teaching-target").forEach((node) => node.classList.remove("teaching-target"));
    });
    await page.waitForFunction(() => document.querySelector("#analysis")?.classList.contains("active"), null, { timeout: 30000 }).catch(async (error) => {
      throw new Error(`${error.message || error}; pageState=${JSON.stringify(await pageState(page))}`);
    });
    stage = "wait_eeg_canvas_visible";
    await page.waitForSelector("#eegCanvas", { state: "visible", timeout: 30000 });
    stage = "wait_eeg_canvas_size";
    await page.waitForFunction(() => {
      const canvas = document.querySelector("#eegCanvas");
      const rect = canvas?.getBoundingClientRect?.();
      return Boolean(rect && rect.width > 400 && rect.height > 240);
    }, null, { timeout: 30000 });
    const earlyStats = await canvasStats(page);
    add("canvas_not_blank_during_loading", earlyStats.ok, earlyStats);
    stage = "wait_waveform_ready";
    await page.waitForFunction(() => document.querySelector("#eegEmpty")?.classList.contains("ready"), null, { timeout: 120000 });
    const finalStats = await canvasStats(page);
    add("canvas_has_waveform_after_auto_preview", finalStats.ok && finalStats.dark > 40, finalStats);
    const currentPrepControls = await page.evaluate(() => {
      const text = document.querySelector("#analysis")?.textContent || "";
      return {
        filter: Boolean(document.querySelector("#eegFilterPreviewToggle") || /滤波/.test(text)),
        segment: Boolean(document.querySelector('[data-preview-jump="segment"], [data-mode-target="selectSegment"], [data-ia-action="add-candidate-bad-segment"]') || /选段|片段/.test(text)),
        badChannel: Boolean(document.querySelector('[data-preview-jump="bad-channel"], [data-mode-target="markBadChannel"], [data-ia-action="mark-bad-channel"]') || /坏道|通道/.test(text)),
        reference: Boolean(document.querySelector('[data-preview-jump="reference"], #presetPrepReference') || /参考/.test(text)),
        previewPolicy: /min_max_bucket|显示采样|预览|不改写原始/.test(text),
      };
    });
    add("filter_shortcut_visible", currentPrepControls.filter, currentPrepControls);
    add("segment_shortcut_visible", currentPrepControls.segment, currentPrepControls);
    add("bad_channel_shortcut_visible", currentPrepControls.badChannel, currentPrepControls);
    add("reference_shortcut_visible", currentPrepControls.reference, currentPrepControls);
    const qcRequest = taskRequests.find((item) => item?.module_name === "qc" && item?.workflow_id === "qc_waveform_preview");
    add("auto_preview_uses_fast_ui_preview", Boolean(qcRequest?.parameters_json?.fast_ui_preview) || currentPrepControls.previewPolicy, { qcRequest, currentPrepControls });
    await page.screenshot({ path: SCREENSHOT, fullPage: true });
  } catch (error) {
    add("unexpected_error", false, { stage, message: error.message || String(error), pageState: await pageState(page).catch((stateError) => ({ error: stateError.message || String(stateError) })) });
    await page.screenshot({ path: SCREENSHOT, fullPage: true }).catch(() => {});
  } finally {
    await browser.close();
  }
  const report = {
    status: checks.every((item) => item.pass) ? "passed" : "failed",
    frontendUrl: FRONTEND_URL,
    apiBase: API_BASE,
    generatedAt: new Date().toISOString(),
    checks,
    screenshot: SCREENSHOT,
  };
  fs.writeFileSync(OUT_JSON, `${JSON.stringify(report, null, 2)}\n`, "utf8");
  console.log(JSON.stringify(report, null, 2));
  process.exit(report.status === "passed" ? 0 : 1);
}

main();
