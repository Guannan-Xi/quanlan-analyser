import fs from "node:fs";
import path from "node:path";
import { chromium, chromiumLaunchOptions } from "./lib/playwright_runtime.mjs";

const repoRoot = process.cwd();
const apiBase = process.env.QLANALYSER_API_BASE_URL || "http://127.0.0.1:8001/api";
const frontendUrl = process.env.QLANALYSER_DATA_PREP_STATE_MATRIX_URL
  || `http://127.0.0.1:4174/?customer_demo=auto&teaching_demo=auto&api=${encodeURIComponent(apiBase)}&v=data-prep-state-matrix#analysis`;
const evidenceDir = process.env.QLANALYSER_DATA_PREP_STATE_MATRIX_DIR
  || path.join(repoRoot, "work", "release_evidence", "20260628-data-preparation-controls-state-matrix");
const outputPath = path.join(evidenceDir, "data_preparation_controls_state_matrix.json");
const screenshotPath = path.join(evidenceDir, "data_preparation_controls_state_matrix.png");

fs.mkdirSync(evidenceDir, { recursive: true });

const checks = [];
function add(name, pass, details = {}) {
  checks.push({ name, pass: Boolean(pass), details });
}

async function appReady(page) {
  await page.goto(frontendUrl, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForFunction(() => {
    const visible = (selector) => {
      const node = document.querySelector(selector);
      if (!node) return false;
      const style = window.getComputedStyle(node);
      const rect = node.getBoundingClientRect();
      return !node.hidden && style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0;
    };
    return visible("#appShell") || visible("#loginScreen");
  }, null, { timeout: 60000 });
  const login = page.locator("#customerLoginBtn");
  if (await login.isVisible().catch(() => false)) await login.click();
  await page.waitForSelector("#appShell:not([hidden])", { timeout: 60000 });
  await page.waitForSelector("#teachingModeBtn", { timeout: 60000 });
}

async function stateSnapshot(page) {
  return page.evaluate(() => {
    const attr = (selector, name) => document.querySelector(selector)?.getAttribute(name) || "";
    const visible = (selector) => {
      const node = document.querySelector(selector);
      if (!node) return false;
      const style = window.getComputedStyle(node);
      const rect = node.getBoundingClientRect();
      return style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0 && !node.hidden;
    };
    const disabledState = (selector) => {
      const node = document.querySelector(selector);
      return node ? {
        disabled: Boolean(node.disabled),
        ariaDisabled: node.getAttribute("aria-disabled"),
        title: node.getAttribute("title") || "",
        text: node.textContent.trim(),
      } : null;
    };
    return {
      url: window.location.href,
      hash: window.location.hash,
      activeViews: [...document.querySelectorAll(".view.active")].map((node) => node.id),
      teachingActive: document.body.classList.contains("teaching-sandbox-active"),
      teachingButton: {
        text: document.querySelector("#teachingModeBtn")?.textContent.trim() || "",
        action: attr("#teachingModeBtn", "data-teaching-action"),
        pressed: attr("#teachingModeBtn", "aria-pressed"),
      },
      teachingBannerVisible: visible("#teachingSandboxBanner"),
      browseMode: disabledState('[data-testid="waveform-mode-browse"]'),
      selectMode: disabledState('[data-testid="waveform-mode-select-segment"]'),
      badSegmentMode: disabledState('[data-testid="waveform-mode-mark-bad-segment"]'),
      badChannelMode: disabledState('[data-testid="waveform-mode-mark-bad-channel"]'),
      firstBtn: disabledState("#eegFirstBtn"),
      slider: disabledState("#eegTimeSlider"),
      windowPreset: disabledState("#eegWindowPreset"),
      addLabel: disabledState('[data-ia-action="add-label"]'),
      confirmPlan: disabledState('[data-real-action="confirm-plan-inline"]'),
      workflowViewActive: document.querySelector("#workflow")?.classList.contains("active") || false,
      analysisViewActive: document.querySelector("#analysis")?.classList.contains("active") || false,
      gateText: document.querySelector('[data-testid="analysis-preparation-gate"]')?.textContent.trim() || "",
      statusText: document.querySelector("#waveformWorkbenchStatus")?.textContent.trim() || "",
      hintText: document.querySelector("#mainPrepActionHint")?.textContent.trim() || "",
      segment: {
        timePressed: attr('[data-segment="time"]', "aria-pressed"),
        eventPressed: attr('[data-segment="event"]', "aria-pressed"),
        timeVisible: visible("#timeSegmentForm"),
        eventVisible: visible("#eventSegmentForm"),
      },
    };
  });
}

const browser = await chromium.launch({ headless: true, ...chromiumLaunchOptions() });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const planPayloads = [];
page.on("request", (request) => {
  if (request.method() === "POST" && request.url().includes("/data-preparation/plans")) {
    try {
      planPayloads.push(JSON.parse(request.postData() || "{}"));
    } catch (_) {}
  }
});

try {
  await appReady(page);
  await page.waitForFunction(() => document.querySelector("#teachingModeBtn")?.dataset.teachingAction === "exit", null, { timeout: 60000 });
  const teachingLoaded = await stateSnapshot(page);
  add("teaching_auto_enters_once_with_exit_button", teachingLoaded.teachingActive && teachingLoaded.teachingButton.action === "exit", teachingLoaded.teachingButton);

  await page.click("#teachingModeBtn");
  await page.waitForFunction(() => !document.body.classList.contains("teaching-sandbox-active"), null, { timeout: 30000 });
  const afterExit = await stateSnapshot(page);
  add("teaching_exit_refreshes_chrome", !afterExit.teachingActive && afterExit.teachingButton.action === "start" && afterExit.teachingButton.pressed === "false" && !afterExit.teachingBannerVisible, afterExit.teachingButton);
  add("teaching_exit_removes_auto_url_param", !new URL(afterExit.url).searchParams.has("teaching_demo"), { url: afterExit.url });

  await page.evaluate(() => {
    const isVisible = (node) => {
      if (!node) return false;
      const style = window.getComputedStyle(node);
      const rect = node.getBoundingClientRect();
      return !node.hidden && style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0;
    };
    const entry = [...document.querySelectorAll('[data-view-jump="analysis"], [data-view="analysis"]')].find(isVisible);
    entry?.click();
  });
  await page.waitForFunction(() => document.querySelector("#analysis")?.classList.contains("active"), null, { timeout: 30000 });
  await page.click('[data-testid="waveform-mode-select-segment"]', { force: true });
  const noDataMode = await stateSnapshot(page);
  add("no_data_write_modes_disabled_with_reason",
    noDataMode.browseMode && noDataMode.browseMode.disabled === false
      && noDataMode.selectMode?.disabled === true
      && noDataMode.selectMode?.ariaDisabled === "true"
      && /请选择|等待波形/.test(noDataMode.selectMode?.title || ""),
    {
      browse: noDataMode.browseMode,
      select: noDataMode.selectMode,
      badSegment: noDataMode.badSegmentMode,
      badChannel: noDataMode.badChannelMode,
    });
  add("no_data_waveform_navigation_disabled",
    noDataMode.firstBtn?.disabled === true
      && noDataMode.slider?.disabled === true
      && noDataMode.windowPreset?.disabled === true,
    { firstBtn: noDataMode.firstBtn, slider: noDataMode.slider, windowPreset: noDataMode.windowPreset });
  add("no_data_label_action_disabled",
    noDataMode.addLabel?.disabled === true
      && noDataMode.addLabel?.ariaDisabled === "true"
      && String(noDataMode.addLabel?.title || "").length > 0,
    { addLabel: noDataMode.addLabel });

  await page.click('[data-view-jump="workflow"]');
  await page.waitForTimeout(300);
  const workflowGate = await stateSnapshot(page);
  add("workflow_jump_uses_preparation_gate",
    workflowGate.analysisViewActive && !workflowGate.workflowViewActive && /确认|准备/.test(`${workflowGate.gateText} ${workflowGate.hintText}`),
    { activeViews: workflowGate.activeViews, gateText: workflowGate.gateText, hintText: workflowGate.hintText });

  await appReady(page);
  await page.waitForFunction(() => document.body.classList.contains("teaching-sandbox-active") && document.querySelector("#analysis")?.classList.contains("active"), null, { timeout: 60000 });
  await page.waitForFunction(() => document.querySelector("#analysis")?.classList.contains("active"), null, { timeout: 30000 });
  const visibleSegmentControls = await page.evaluate(() => {
    const visible = (node) => {
      if (!node) return false;
      const style = window.getComputedStyle(node);
      const rect = node.getBoundingClientRect();
      return !node.hidden && style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0;
    };
    return [...document.querySelectorAll("[data-segment]")].filter(visible).length;
  });
  if (visibleSegmentControls > 0) {
    await page.locator('[data-segment="event"]').filter({ hasText: /./ }).first().click();
    const eventMode = await stateSnapshot(page);
    add("segment_event_button_switches_form",
      eventMode.segment.eventPressed === "true" && eventMode.segment.eventVisible && !eventMode.segment.timeVisible,
      eventMode.segment);
    await page.selectOption("#eventType", "stim/target").catch(() => {});
    await page.fill("#eventPre", "-0.3");
    await page.fill("#eventPost", "1.2");
    await page.click('[data-real-action="confirm-plan-inline"]');
    await page.waitForTimeout(800);
    const lastPlanPayload = planPayloads[planPayloads.length - 1] || {};
    const segmentSettings = lastPlanPayload.qc_json?.segment_settings || lastPlanPayload.preprocessing_json?.segment_settings || {};
    add("confirm_plan_payload_keeps_event_segment_settings",
      segmentSettings.segment_mode === "event"
        && segmentSettings.event_segment?.event_type === "stim/target"
        && Number(segmentSettings.event_segment?.pre_sec) === -0.3
        && Number(segmentSettings.event_segment?.post_sec) === 1.2,
      { segmentSettings, payloadCount: planPayloads.length });
    await page.locator('[data-segment="time"]').filter({ hasText: /./ }).first().click();
    const timeMode = await stateSnapshot(page);
    add("segment_time_button_switches_form",
      timeMode.segment.timePressed === "true" && timeMode.segment.timeVisible && !timeMode.segment.eventVisible,
      timeMode.segment);
  } else {
    add("legacy_segment_controls_hidden_in_customer_ui", true, { visibleSegmentControls });
  }

  const failPage = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await failPage.route("**/api/lab/demo/dataset", async (route) => {
    await route.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ detail: "forced teaching dataset failure" }) });
  });
  await failPage.goto(`http://127.0.0.1:4174/?customer_demo=auto&api=${encodeURIComponent(apiBase)}&v=data-prep-state-matrix-fail#analysis`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await failPage.waitForFunction(() => {
    const visible = (selector) => {
      const node = document.querySelector(selector);
      if (!node) return false;
      const style = window.getComputedStyle(node);
      const rect = node.getBoundingClientRect();
      return !node.hidden && style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0;
    };
    return visible("#appShell") || visible("#loginScreen");
  }, null, { timeout: 60000 });
  if (await failPage.locator("#customerLoginBtn").isVisible().catch(() => false)) await failPage.click("#customerLoginBtn");
  await failPage.waitForSelector("#teachingModeBtn", { timeout: 60000 });
  await failPage.click("#teachingModeBtn");
  await failPage.waitForTimeout(1200);
  const failState = await failPage.evaluate(() => ({
    teachingActive: document.body.classList.contains("teaching-sandbox-active"),
    buttonAction: document.querySelector("#teachingModeBtn")?.dataset.teachingAction || "",
    buttonPressed: document.querySelector("#teachingModeBtn")?.getAttribute("aria-pressed") || "",
    bannerVisible: (() => {
      const node = document.querySelector("#teachingSandboxBanner");
      if (!node) return false;
      const rect = node.getBoundingClientRect();
      return !node.hidden && rect.width > 0 && rect.height > 0;
    })(),
  }));
  add("teaching_start_failure_rolls_back_chrome",
    !failState.teachingActive && failState.buttonAction === "start" && failState.buttonPressed === "false" && !failState.bannerVisible,
    failState);
  await failPage.close().catch(() => {});

  await page.screenshot({ path: screenshotPath, fullPage: true });
} catch (error) {
  add("unexpected_error", false, { message: error.stack || String(error) });
  await page.screenshot({ path: screenshotPath, fullPage: true }).catch(() => {});
} finally {
  await browser.close().catch(() => {});
}

const report = {
  status: checks.every((check) => check.pass) ? "passed" : "failed",
  generatedAt: new Date().toISOString(),
  frontendUrl,
  apiBase,
  checks,
  screenshotPath,
};
fs.writeFileSync(outputPath, `${JSON.stringify(report, null, 2)}\n`, "utf8");
console.log(JSON.stringify({ status: report.status, outputPath, screenshotPath, failed: checks.filter((check) => !check.pass).map((check) => check.name) }, null, 2));
process.exit(report.status === "passed" ? 0 : 1);
