import fs from "node:fs";
import path from "node:path";
import { chromium, chromiumLaunchOptions } from "./lib/playwright_runtime.mjs";

const API_BASE = process.env.QLANALYSER_API_BASE_URL || "http://127.0.0.1:8001/api";
const FRONTEND_URL = process.env.QLANALYSER_FRONTEND_URL
  || `http://127.0.0.1:4174/?customer_demo=auto&api=${encodeURIComponent(API_BASE)}&v=epilepsy-deeplink-e2e#epilepsyWorkbenchInline`;
const OUT_DIR = process.env.QLANALYSER_EPILEPSY_DEEPLINK_E2E_DIR
  || path.resolve(FRONTEND_URL.includes("39.97.248.225")
    ? "work/release_evidence/20260630-epilepsy-deeplink-bootstrap-cloud"
    : "work/release_evidence/20260630-epilepsy-deeplink-bootstrap-local");
const EVIDENCE_PATH = path.join(OUT_DIR, "deeplink_bootstrap.json");

function ensureDir() { fs.mkdirSync(OUT_DIR, { recursive: true }); }
function writeEvidence(payload) {
  ensureDir();
  fs.writeFileSync(EVIDENCE_PATH, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
}
async function clickFirstVisibleEnabled(page, selector, label, timeout = 30000) {
  await page.waitForFunction((sel) => Array.from(document.querySelectorAll(sel)).some((el) => {
    const rect = el.getBoundingClientRect();
    const style = window.getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.display !== "none" && style.visibility !== "hidden" && !el.disabled && el.getAttribute("aria-disabled") !== "true";
  }), selector, { timeout });
  const index = await page.evaluate((sel) => Array.from(document.querySelectorAll(sel)).findIndex((el) => {
    const rect = el.getBoundingClientRect();
    const style = window.getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.display !== "none" && style.visibility !== "hidden" && !el.disabled && el.getAttribute("aria-disabled") !== "true";
  }), selector);
  if (index < 0) throw new Error(`${label} not visible/enabled`);
  await page.locator(selector).nth(index).click({ timeout }).catch(async () => {
    await page.evaluate(({ sel, idx }) => document.querySelectorAll(sel)[idx]?.click(), { sel: selector, idx: index });
  });
}
async function waitForTaskCompleted(page, timeoutMs = 240000) {
  await page.waitForFunction(() => {
    const stateTask = window.__QLANALYSER_E2E_STATE__?.real?.tasks?.epilepsy_ml;
    const task = window.__QLANALYSER_EPILEPSY_E2E_TASK__ || window.__QLANALYSER_LAST_EPILEPSY_TASK__;
    return [stateTask, task].filter(Boolean).some((item) => ["completed", "failed", "error"].includes(String(item.status || "").toLowerCase()));
  }, null, { timeout: timeoutMs });
  return page.evaluate(() => window.__QLANALYSER_E2E_STATE__?.real?.tasks?.epilepsy_ml || window.__QLANALYSER_EPILEPSY_E2E_TASK__ || window.__QLANALYSER_LAST_EPILEPSY_TASK__ || null);
}

const evidence = {
  script: path.basename(new URL(import.meta.url).pathname),
  started_at: new Date().toISOString(),
  frontend_url: FRONTEND_URL,
  api_base: API_BASE,
  checks: {},
  screenshots: {},
  errors: [],
  status: "running",
};

const browser = await chromium.launch(chromiumLaunchOptions({ headless: true }));
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
page.on("pageerror", (error) => evidence.errors.push(error.message || String(error)));

try {
  await page.goto(FRONTEND_URL, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForFunction(() => document.body?.dataset?.role === "customer" && document.querySelector("#appShell")?.hidden === false, null, { timeout: 90000 });
  await page.waitForFunction(() => document.querySelector(".view.active")?.id === "epilepsyWorkbenchInline", null, { timeout: 90000 });
  await page.waitForFunction(() => /epilepsy_ml_demo_source_channels\.edf|eeg_demo_epilepsy_high_amplitude/i.test(document.body.innerText || ""), null, { timeout: 90000 });
  await page.waitForFunction(() => window.__QLANALYSER_E2E_STATE__?.real?.eegFile?.id === "eeg_demo_epilepsy_high_amplitude", null, { timeout: 90000 });
  await page.waitForSelector('[data-testid="inline-epilepsy-waveform-canvas"]', { timeout: 30000 });
  await page.waitForFunction(() => document.querySelector('[data-testid="inline-epilepsy-waveform-canvas"]')?.dataset.hasWaveform === "true", null, { timeout: 90000 }).catch(() => {});
  evidence.screenshots.loaded = path.join(OUT_DIR, "01_deeplink_loaded.png");
  await page.screenshot({ path: evidence.screenshots.loaded, fullPage: true });

  const initial = await page.evaluate(() => {
    const overlay = document.querySelector("#teachingOverlay");
    const overlayRect = overlay?.getBoundingClientRect?.() || { width: 0, height: 0 };
    const overlayStyle = overlay ? window.getComputedStyle(overlay) : null;
    const activeView = document.querySelector(".view.active")?.id || "";
    const bodyText = document.body.innerText || "";
    const state = window.__QLANALYSER_E2E_STATE__ || {};
    const file = state.real?.eegFile || {};
    const plan = state.real?.plan || {};
    const startButton = document.querySelector('[data-testid="inline-epilepsy-start-screening"]');
    const canvas = document.querySelector('[data-testid="inline-epilepsy-waveform-canvas"]');
    return {
      urlHash: window.location.hash,
      activeView,
      viewTitle: document.querySelector("#viewTitle")?.textContent?.replace(/\s+/g, " ").trim() || "",
      activeNav: document.querySelector(".nav [data-view].active")?.getAttribute("data-view") || "",
      fileId: file.id || "",
      fileName: file.original_filename || file.filename || "",
      projectId: state.real?.project?.id || "",
      planId: plan.id || "",
      planStatus: plan.status || "",
      startButtonText: startButton?.textContent?.replace(/\s+/g, " ").trim() || "",
      startButtonDisabled: Boolean(startButton?.disabled),
      hasWaveform: canvas?.dataset.hasWaveform || "",
      bodyText,
      teachingOverlayActive: Boolean(overlay && overlay.classList.contains("active") && overlayRect.width > 0 && overlayRect.height > 0 && overlayStyle?.visibility !== "hidden" && overlayStyle?.display !== "none"),
      candidateOverlayBeforeRun: /算法候选|模型候选高亮|已完成初筛/.test(bodyText),
    };
  });
  evidence.initial_state = {
    ...initial,
    bodyText: initial.bodyText.slice(0, 4000),
  };

  const preWheelToast = await page.locator("#toast").textContent().catch(() => "");
  await page.locator('[data-testid="inline-epilepsy-waveform-canvas"]').hover();
  await page.mouse.wheel(240, 0);
  await page.waitForTimeout(350);
  evidence.wheel_state = await page.evaluate((beforeToast) => {
    const toast = document.querySelector("#toast")?.textContent?.replace(/\s+/g, " ").trim() || "";
    const canvas = document.querySelector('[data-testid="inline-epilepsy-waveform-canvas"]');
    return {
      toastBefore: beforeToast || "",
      toastAfter: toast,
      toastUnchanged: toast === (beforeToast || ""),
      readerStart: Number(canvas?.dataset.readerStartSec || 0),
      hasWaveform: canvas?.dataset.hasWaveform || "",
    };
  }, preWheelToast || "");

  await clickFirstVisibleEnabled(page, '[data-testid="inline-epilepsy-start-screening"]', "start epilepsy screening", 60000);
  const task = await waitForTaskCompleted(page);
  await page.waitForFunction(() => window.__QLANALYSER_E2E_STATE__?.epilepsyInline?.resultLoadStatus === "ready", null, { timeout: 90000 });
  const afterRun = await page.evaluate(() => {
    const state = window.__QLANALYSER_E2E_STATE__ || {};
    const stripText = document.querySelector('[data-testid="inline-epilepsy-stage-strip"]')?.textContent?.replace(/\s+/g, " ").trim() || "";
    const eventsText = document.querySelector('[data-testid="inline-epilepsy-events-panel"]')?.textContent?.replace(/\s+/g, " ").trim() || "";
    return {
      task: state.real?.tasks?.epilepsy_ml || window.__QLANALYSER_LAST_EPILEPSY_TASK__ || null,
      resultLoadStatus: state.epilepsyInline?.resultLoadStatus || "",
      eventCount: state.epilepsyInline?.eventRows?.length || 0,
      epochCount: state.epilepsyInline?.epochRows?.length || 0,
      stageText: stripText,
      eventsText,
    };
  });
  evidence.after_screening = afterRun;
  evidence.backend_task = task;
  evidence.screenshots.after_screening = path.join(OUT_DIR, "02_after_screening.png");
  await page.screenshot({ path: evidence.screenshots.after_screening, fullPage: true });

  evidence.checks.final_hash_is_epilepsy_workbench = initial.urlHash === "#epilepsyWorkbenchInline";
  evidence.checks.active_view_is_epilepsy_workbench = initial.activeView === "epilepsyWorkbenchInline";
  evidence.checks.title_is_epilepsy_workbench = /癫痫样事件分析台/.test(`${initial.viewTitle}\n${initial.bodyText}`);
  evidence.checks.current_data_is_epilepsy_edf = initial.fileId === "eeg_demo_epilepsy_high_amplitude"
    && /epilepsy_ml_demo_source_channels\.edf/i.test(initial.fileName);
  evidence.checks.not_dashboard = initial.activeView !== "dashboard";
  evidence.checks.not_oddball_demo = !/teaching_oddball_with_montage_raw\.fif|eeg_demo_teaching_oddball/i.test(initial.bodyText);
  evidence.checks.teaching_overlay_not_blocking = initial.teachingOverlayActive === false;
  evidence.checks.pre_screening_no_algorithm_candidate_semantics = initial.candidateOverlayBeforeRun === false;
  evidence.checks.start_button_available = initial.startButtonDisabled === false && /开始初筛|重新初筛/.test(initial.startButtonText);
  evidence.checks.waveform_canvas_ready = ["true", true].includes(initial.hasWaveform) || ["true", true].includes(evidence.wheel_state.hasWaveform);
  evidence.checks.inline_wheel_no_toast = evidence.wheel_state.toastUnchanged === true;
  evidence.checks.task_completed = String(afterRun.task?.status || task?.status || "").toLowerCase() === "completed";
  evidence.checks.candidate_event_and_stage_visible = afterRun.eventCount >= 1
    && afterRun.epochCount >= 1
    && /候选事件/.test(afterRun.eventsText)
    && /1/.test(afterRun.stageText);
  evidence.checks.no_diagnosis_or_treatment_copy = !/诊断结论|确诊为|确诊：|治疗建议|用于临床分诊|临床分诊建议/.test(`${initial.bodyText}\n${afterRun.eventsText}`);
  evidence.status = Object.values(evidence.checks).every(Boolean) ? "passed" : "failed";
} catch (error) {
  evidence.errors.push(error?.stack || error?.message || String(error));
  evidence.status = "failed";
  evidence.failure_state = await page.evaluate(() => ({
    hash: window.location.hash,
    activeView: document.querySelector(".view.active")?.id || "",
    bodyText: (document.body.innerText || "").slice(0, 3000),
    stateFile: window.__QLANALYSER_E2E_STATE__?.real?.eegFile || null,
    deepLink: window.__QLANALYSER_E2E_STATE__?.deepLink || null,
  })).catch(() => null);
  evidence.screenshots.failure = path.join(OUT_DIR, "failure.png");
  await page.screenshot({ path: evidence.screenshots.failure, fullPage: true }).catch(() => {});
} finally {
  evidence.finished_at = new Date().toISOString();
  writeEvidence(evidence);
  await browser.close().catch(() => {});
}

console.log(JSON.stringify(evidence, null, 2));
if (evidence.status !== "passed") process.exit(1);
