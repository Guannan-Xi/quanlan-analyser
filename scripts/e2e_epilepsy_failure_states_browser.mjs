import fs from "node:fs";
import path from "node:path";
import { chromium, chromiumLaunchOptions } from "./lib/playwright_runtime.mjs";

const API_BASE = process.env.QLANALYSER_API_BASE_URL || "http://127.0.0.1:8001/api";
const FRONTEND_URL = process.env.QLANALYSER_FRONTEND_URL
  || `http://127.0.0.1:4174/?customer_demo=auto&api=${encodeURIComponent(API_BASE)}&v=epilepsy-failure-states#storage`;
const SAMPLE_EDF = process.env.QLANALYSER_EPILEPSY_SAMPLE_EDF
  || path.resolve("work/fixtures/epilepsy_regular_labeled/regular_epilepsy_labeled_60s.edf");
const OUT_DIR = process.env.QLANALYSER_EPILEPSY_FAILURE_E2E_DIR
  || path.resolve("work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-failure-states");
const OUT_FILE = path.join(OUT_DIR, "failure_states_browser.json");

function ensureDir() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
}

function writeEvidence(payload) {
  ensureDir();
  fs.writeFileSync(OUT_FILE, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
}

async function clickFirstVisibleEnabled(page, selector, label, timeout = 30000) {
  await page.waitForFunction((sel) => {
    return Array.from(document.querySelectorAll(sel)).some((el) => {
      const rect = el.getBoundingClientRect();
      const style = window.getComputedStyle(el);
      return rect.width > 0
        && rect.height > 0
        && style.display !== "none"
        && style.visibility !== "hidden"
        && !el.disabled
        && el.getAttribute("aria-disabled") !== "true";
    });
  }, selector, { timeout });
  const index = await page.evaluate((sel) => {
    return Array.from(document.querySelectorAll(sel)).findIndex((el) => {
      const rect = el.getBoundingClientRect();
      const style = window.getComputedStyle(el);
      return rect.width > 0
        && rect.height > 0
        && style.display !== "none"
        && style.visibility !== "hidden"
        && !el.disabled
        && el.getAttribute("aria-disabled") !== "true";
    });
  }, selector);
  if (index < 0) throw new Error(`${label} is not enabled: ${selector}`);
  await page.locator(selector).nth(index).click({ timeout });
}

async function waitForResponseAfter(page, label, predicate, action, timeout = 90000) {
  const responsePromise = page.waitForResponse(predicate, { timeout });
  await action();
  const response = await responsePromise;
  if (!response) throw new Error(`${label} did not produce response`);
  return response;
}

async function checkFirstVisible(page, selector, label) {
  await page.waitForFunction((sel) => {
    return Array.from(document.querySelectorAll(sel)).some((el) => {
      const rect = el.getBoundingClientRect();
      const style = window.getComputedStyle(el);
      return rect.width > 0 && rect.height > 0 && style.display !== "none" && style.visibility !== "hidden";
    });
  }, selector, { timeout: 30000 });
  const checked = await page.evaluate((sel) => {
    const target = Array.from(document.querySelectorAll(sel)).find((el) => {
      const rect = el.getBoundingClientRect();
      const style = window.getComputedStyle(el);
      return rect.width > 0 && rect.height > 0 && style.display !== "none" && style.visibility !== "hidden";
    });
    if (!target) return false;
    target.checked = true;
    target.dispatchEvent(new Event("change", { bubbles: true }));
    return Boolean(target.checked);
  }, selector);
  if (!checked) throw new Error(`${label} did not become checked`);
}

async function bootstrapUploadedFile(page, evidence) {
  await page.goto(FRONTEND_URL, { waitUntil: "domcontentloaded", timeout: 60000 });
  await clickFirstVisibleEnabled(page, '[data-real-action="create-project"]', "create project");
  await page.waitForFunction(() => Boolean(window.__QLANALYSER_E2E_STATE__?.real?.project?.id), null, { timeout: 30000 });

  await clickFirstVisibleEnabled(page, '[data-view="storage"], [data-view-jump="storage"]', "open storage");
  await page.setInputFiles("#real-eeg-file", SAMPLE_EDF);
  await checkFirstVisible(page, '[data-upload-authorization="eeg"]', "upload authorization");
  const uploadResponse = await waitForResponseAfter(
    page,
    "upload EDF",
    (response) => /\/api\/eeg\/upload/.test(response.url()) && response.request().method() === "POST",
    () => clickFirstVisibleEnabled(page, '#storage [data-real-action="upload-eeg"], [data-real-action="upload-eeg"]', "upload EEG"),
    90000,
  );
  const uploaded = await uploadResponse.json();
  evidence.uploaded_file_id = uploaded.id;
  return uploaded;
}

async function confirmPlanAndOpenWorkbench(page, evidence) {
  await page.waitForFunction(() => document.querySelector(".view.active")?.id === "analysis", null, { timeout: 30000 }).catch(() => {});
  const planResponse = await waitForResponseAfter(
    page,
    "confirm data preparation plan",
    (response) => /\/api\/data-preparation\/plans$/.test(response.url()) && response.request().method() === "POST",
    () => clickFirstVisibleEnabled(page, '[data-real-action="confirm-plan-inline"]', "confirm data preparation"),
    90000,
  );
  const plan = await planResponse.json();
  evidence.plan_id = plan.id;
  await clickFirstVisibleEnabled(page, '[data-view="workflow"], [data-view-jump="workflow"]', "open analysis tasks");
  await clickFirstVisibleEnabled(page, '[data-testid="analysis-method-scope-panel"] [data-module-id="epilepsy_ml"]', "open epilepsy workbench");
  await page.waitForSelector('[data-testid="main-epilepsy-workbench-inline"].active', { timeout: 30000 });
}

async function runScreening(page) {
  const responsePromise = page.waitForResponse((response) => response.url().endsWith("/api/tasks") && response.request().method() === "POST", { timeout: 90000 });
  await clickFirstVisibleEnabled(page, '[data-testid="inline-epilepsy-start-screening"]', "start screening");
  return responsePromise;
}

async function waitForResultReady(page) {
  await page.waitForFunction(() => {
    const inline = window.__QLANALYSER_E2E_STATE__?.epilepsyInline || {};
    return inline.resultLoadStatus === "ready" && Array.isArray(inline.eventRows) && inline.eventRows.length > 0;
  }, null, { timeout: 120000 });
}

async function addCorrection(page) {
  await clickFirstVisibleEnabled(page, '[data-epilepsy-action="select-event"]', "select candidate event");
  await clickFirstVisibleEnabled(page, '[data-epilepsy-action="set-correction"][data-correction="Normal"]', "exclude candidate");
  await page.waitForFunction(() => (window.__QLANALYSER_E2E_STATE__?.epilepsyInline?.draftCommands || []).length > 0, null, { timeout: 15000 });
}

async function newPage(browser) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });
  page.on("pageerror", (error) => {
    throw error;
  });
  return page;
}

if (!fs.existsSync(SAMPLE_EDF)) {
  throw new Error(`Missing sample EDF: ${SAMPLE_EDF}`);
}

const evidence = {
  script: path.basename(new URL(import.meta.url).pathname),
  started_at: new Date().toISOString(),
  frontend_url: FRONTEND_URL,
  api_base: API_BASE,
  sample_edf: SAMPLE_EDF,
  checks: {},
  cases: {},
  screenshots: {},
  errors: [],
  status: "running",
};

const browser = await chromium.launch(chromiumLaunchOptions({ headless: true }));

try {
  {
    const page = await newPage(browser);
    await page.goto(FRONTEND_URL, { waitUntil: "domcontentloaded", timeout: 60000 });
    await clickFirstVisibleEnabled(page, '[data-real-action="create-project"]', "create project");
    await clickFirstVisibleEnabled(page, '[data-view="storage"], [data-view-jump="storage"]', "open storage");
    await page.setInputFiles("#real-eeg-file", SAMPLE_EDF);
    let uploadRequests = 0;
    page.on("request", (request) => {
      if (/\/api\/eeg\/upload/.test(request.url()) && request.method() === "POST") uploadRequests += 1;
    });
    await clickFirstVisibleEnabled(page, '#storage [data-real-action="upload-eeg"], [data-real-action="upload-eeg"]', "try upload without authorization");
    await page.waitForTimeout(500);
    const toast = await page.locator("#toast").textContent().catch(() => "");
    evidence.cases.missing_upload_authorization_ui = { toast, uploadRequests };
    evidence.checks.missing_upload_authorization_ui = /确认|授权|有权|同意/.test(toast || "") && uploadRequests === 0;
    await page.close();
  }

  {
    const page = await newPage(browser);
    const local = {};
    await bootstrapUploadedFile(page, local);
    await clickFirstVisibleEnabled(page, '[data-view="workflow"], [data-view-jump="workflow"]', "open analysis tasks before prep");
    const gate = await page.evaluate(() => {
      const button = document.querySelector('[data-module-id="epilepsy_ml"][data-real-action="open-epilepsy-workbench"]');
      return {
        disabled: Boolean(button?.disabled),
        title: button?.getAttribute("title") || "",
      };
    });
    evidence.cases.unconfirmed_preparation_gate_ui = gate;
    evidence.checks.unconfirmed_preparation_gate_ui = gate.disabled === true && /准备方案|确认/.test(gate.title);
    await page.close();
  }

  {
    const page = await newPage(browser);
    await bootstrapUploadedFile(page, {});
    await confirmPlanAndOpenWorkbench(page, {});
    await page.route("**/api/tasks", async (route) => {
      if (route.request().method() === "POST") {
        await route.fulfill({
          status: 422,
          contentType: "application/json",
          body: JSON.stringify({ detail: { code: "FORCED_SCREENING_FAILURE", message: "forced screening failure" } }),
        });
      } else {
        await route.continue();
      }
    });
    await clickFirstVisibleEnabled(page, '[data-testid="inline-epilepsy-start-screening"]', "start screening with forced failure");
    await page.waitForFunction(() => document.querySelector('[data-testid="inline-epilepsy-screening-progress"]')?.getAttribute("data-status") === "failed", null, { timeout: 15000 });
    const failureUi = await page.evaluate(() => ({
      status: document.querySelector('[data-testid="inline-epilepsy-screening-progress"]')?.getAttribute("data-status") || "",
      progress: document.querySelector('[data-testid="inline-epilepsy-screening-progress"] [role="progressbar"]')?.getAttribute("aria-valuenow") || "",
      text: document.querySelector('[data-testid="inline-epilepsy-screening-progress"]')?.textContent?.replace(/\s+/g, " ").trim() || "",
      toast: document.querySelector("#toast")?.textContent?.replace(/\s+/g, " ").trim() || "",
    }));
    evidence.cases.screening_task_failure_ui = failureUi;
    evidence.checks.screening_task_failure_ui = failureUi.status === "failed" && /失败|failure|FORCED/.test(`${failureUi.text} ${failureUi.toast}`);
    await page.close();
  }

  {
    const page = await newPage(browser);
    await bootstrapUploadedFile(page, {});
    await confirmPlanAndOpenWorkbench(page, {});
    await page.route("**/api/artifacts/*/download", async (route) => {
      await route.fulfill({ status: 410, contentType: "application/json", body: JSON.stringify({ detail: "forced artifact missing" }) });
    });
    await runScreening(page);
    await page.waitForSelector('[data-testid="inline-epilepsy-result-load-error"]', { timeout: 120000 });
    const artifactError = await page.locator('[data-testid="inline-epilepsy-result-load-error"]').textContent();
    evidence.cases.artifact_load_failure_ui = { artifactError };
    evidence.checks.artifact_load_failure_ui = /结果读取错误|Artifact download failed|410/.test(artifactError || "");
    await page.close();
  }

  {
    const page = await newPage(browser);
    await bootstrapUploadedFile(page, {});
    await confirmPlanAndOpenWorkbench(page, {});
    await runScreening(page);
    await waitForResultReady(page);
    await addCorrection(page);
    await page.route("**/api/epilepsy-review-sessions/*", async (route) => {
      if (route.request().method() === "PATCH") {
        await route.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ detail: "forced save failure" }) });
      } else {
        await route.continue();
      }
    });
    await clickFirstVisibleEnabled(page, '[data-epilepsy-action="save-draft"]', "save draft with forced failure");
    await page.waitForSelector('[data-testid="inline-epilepsy-review-save-error"]', { timeout: 30000 });
    const saveError = await page.locator('[data-testid="inline-epilepsy-review-save-error"]').textContent();
    evidence.cases.review_save_failure_ui = { saveError };
    evidence.checks.review_save_failure_ui = /保存错误|forced save failure|500/.test(saveError || "");
    await page.close();
  }

  {
    const page = await newPage(browser);
    await bootstrapUploadedFile(page, {});
    await confirmPlanAndOpenWorkbench(page, {});
    await runScreening(page);
    await waitForResultReady(page);
    await addCorrection(page);
    await clickFirstVisibleEnabled(page, '[data-epilepsy-action="save-draft"]', "save draft");
    await page.waitForFunction(() => window.__QLANALYSER_E2E_STATE__?.epilepsyInline?.draftSaved === true, null, { timeout: 30000 });
    await page.route("**/api/epilepsy-review-sessions/*/exports", async (route) => {
      if (route.request().method() === "POST") {
        await route.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ detail: "forced export failure" }) });
      } else {
        await route.continue();
      }
    });
    await clickFirstVisibleEnabled(page, '[data-epilepsy-action="publish-results"]', "publish with forced failure");
    await page.waitForSelector('[data-testid="inline-epilepsy-export-error"]', { timeout: 30000 });
    const exportError = await page.locator('[data-testid="inline-epilepsy-export-error"]').textContent();
    evidence.cases.export_failure_ui = { exportError };
    evidence.checks.export_failure_ui = /发布错误|forced export failure|500/.test(exportError || "");
    await page.close();
  }

  evidence.status = Object.values(evidence.checks).every(Boolean) ? "passed" : "failed";
} catch (error) {
  evidence.status = "failed";
  evidence.errors.push(error?.stack || error?.message || String(error));
} finally {
  evidence.finished_at = new Date().toISOString();
  writeEvidence(evidence);
  await browser.close().catch(() => {});
}

console.log(JSON.stringify(evidence, null, 2));
if (evidence.status !== "passed") process.exit(1);
