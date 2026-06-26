import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";

const require = createRequire(import.meta.url);
const { chromium } = require("../frontend/node_modules/playwright");

const FRONTEND_URL = process.env.QLANALYSER_FRONTEND_URL || "http://127.0.0.1:4174/?customer_demo=login&api=http://127.0.0.1:8001/api";
const SAMPLE_EDF = process.env.QLANALYSER_UI_SAMPLE_EDF || path.resolve("frontend/assets/teaching_oddball.edf");
const OUT_DIR = process.env.QLANALYSER_MAIN_WORKBENCH_CLICK_E2E_DIR
  || path.resolve("work/release_evidence/07-mainline-productization/main_workbench_clickthrough_e2e");
const EVIDENCE_PATH = path.join(OUT_DIR, "main_workbench_direct_method_clickthrough_e2e.json");

const ACTIONS = [
  { action: "run-psd", uiModule: "psd", backendModule: "psd", workflow: "resting_psd" },
  { action: "run-erp", uiModule: "erp", backendModule: "erp", workflow: "erp_p300" },
  { action: "run-tfr", uiModule: "tfr", backendModule: "tfr", workflow: "tfr_ersp_itc" },
  { action: "run-multitaper-psd", uiModule: "multitaper_psd", backendModule: "multitaper_psd_tfr", workflow: "multitaper_psd_tfr" },
  { action: "run-multitaper-tfr", uiModule: "multitaper_tfr", backendModule: "multitaper_psd_tfr", workflow: "multitaper_psd_tfr" },
  { action: "run-reference-csd", uiModule: "reference_csd", backendModule: "reference_csd", workflow: "reference_csd" },
  { action: "run-pac", uiModule: "pac", backendModule: "pac", workflow: "pac_cfc" },
  { action: "run-connectivity", uiModule: "connectivity", backendModule: "connectivity", workflow: "connectivity" },
];

function writeEvidence(payload) {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  fs.writeFileSync(EVIDENCE_PATH, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
}

async function clickEnabled(page, selector, label, timeout = 30000) {
  const target = page.locator(`${selector}:visible`).first();
  await target.waitFor({ state: "visible", timeout });
  await page.waitForFunction((targetSelector) => {
    const node = Array.from(document.querySelectorAll(targetSelector)).find((item) => {
      const style = window.getComputedStyle(item);
      const rect = item.getBoundingClientRect();
      return style.visibility !== "hidden" && style.display !== "none" && rect.width > 0 && rect.height > 0;
    });
    return Boolean(node && !node.disabled && node.getAttribute("aria-disabled") !== "true");
  }, selector, { timeout });
  await target.scrollIntoViewIfNeeded();
  await target.click({ trial: true, timeout });
  await target.click({ timeout });
}

async function waitForResponseAfter(page, label, predicate, action, timeout = 60000) {
  const responsePromise = page.waitForResponse(predicate, { timeout }).catch((error) => error);
  try {
    await action();
  } catch (error) {
    await responsePromise.catch(() => null);
    throw new Error(`${label} click/action failed: ${error.message}`);
  }
  const response = await responsePromise;
  if (response instanceof Error) throw new Error(`${label} response was not observed: ${response.message}`);
  if (!response.ok()) throw new Error(`${label} failed with HTTP ${response.status()}`);
  return response;
}

async function login(page) {
  await page.addInitScript(() => {
    localStorage.removeItem("qlanalyser_auth_session");
    localStorage.removeItem("qlanalyser_customer_profile");
    sessionStorage.removeItem("qlanalyser_auth_session");
  });
  await page.goto(FRONTEND_URL, { waitUntil: "domcontentloaded", timeout: 20000 });
  await page.waitForSelector("#customerLoginForm", { state: "visible", timeout: 15000 });
  await page.fill("#customerEmail", process.env.QLANALYSER_DEMO_EMAIL || "demo.customer@quanlan.cn");
  await page.fill("#customerPassword", process.env.QLANALYSER_DEMO_PASSWORD || "demo123456");
  await Promise.all([
    page.waitForSelector("#appShell:not([hidden])", { timeout: 20000 }),
    page.locator("#customerLoginBtn").click(),
  ]);
}

async function openStorageForUpload(page) {
  const jumpedFromDashboard = await page.locator('[data-view-jump="storage"]:visible').first().isVisible().catch(() => false);
  if (jumpedFromDashboard) {
    await clickEnabled(page, '[data-view-jump="storage"]', "open storage from project detail");
  } else {
    await clickEnabled(page, '[data-view="storage"]', "open storage");
  }
  await page.waitForSelector('#storage.active, .view#storage.active', { timeout: 15000 });
}

async function prepareRunnableWorkbench(page, evidence) {
  const projectResponse = await waitForResponseAfter(
    page,
    "create project",
    (response) => response.url().includes("/api/projects") && response.request().method() === "POST",
    () => clickEnabled(page, '[data-real-action="create-project"]', "create project"),
  );
  const project = await projectResponse.json();
  evidence.projectId = project.id;

  await openStorageForUpload(page);
  await page.setInputFiles("#real-eeg-file", SAMPLE_EDF);
  const uploadResponse = await waitForResponseAfter(
    page,
    "upload EDF",
    (response) => response.url().includes("/api/eeg/upload") && response.request().method() === "POST" && response.status() === 200,
    () => clickEnabled(page, '#storage [data-real-action="upload-eeg"]', "upload EEG"),
    45000,
  );
  const uploaded = await uploadResponse.json();
  evidence.fileId = uploaded.id;

  await clickEnabled(page, '[data-view="analysis"]', "open data preparation");
  const metadataQcResponse = await waitForResponseAfter(
    page,
    "metadata QC",
    (response) => response.url().includes("/api/tasks") && response.request().method() === "POST" && response.status() === 200,
    () => clickEnabled(page, '[data-real-action="run-metadata-qc-inline"]', "run metadata QC"),
    60000,
  );
  evidence.metadataQcTask = (await metadataQcResponse.json()).id;

  const planResponse = await waitForResponseAfter(
    page,
    "confirm data preparation",
    (response) => response.url().includes("/api/data-preparation/plans") && response.request().method() === "POST",
    () => clickEnabled(page, '[data-real-action="confirm-plan-inline"]', "confirm preparation"),
    45000,
  );
  const plan = await planResponse.json();
  evidence.plan = { id: plan.id, revision: plan.revision, status: plan.status };

  const epochResponse = await waitForResponseAfter(
    page,
    "save epoch set",
    (response) => response.url().includes("/api/eeg/files/") && response.url().includes("/epoch-sets") && response.request().method() === "POST",
    () => clickEnabled(page, '[data-real-action="save-epoch-set"]', "save epoch set"),
    45000,
  );
  const epochSet = await epochResponse.json();
  evidence.epochSet = { id: epochSet.id, revision: epochSet.revision, status: epochSet.status };
  await clickEnabled(page, '[data-view="workflow"]', "open analysis workbench");
}

async function runAction(page, item) {
  const response = await waitForResponseAfter(
    page,
    item.action,
    (candidate) => candidate.url().includes("/api/tasks")
      && candidate.request().method() === "POST"
      && candidate.status() === 200,
    () => clickEnabled(page, `[data-real-action="${item.action}"]`, item.action),
    120000,
  );
  const requestPayload = JSON.parse(response.request().postData() || "{}");
  const task = await response.json();
  await page.waitForFunction((action) => {
    const audit = window.qlanalyserUiActionAudit || [];
    return audit.some((entry) => entry.action === `real:${action}` && entry.verdict === "pass");
  }, item.action, { timeout: 30000 });
  return {
    ...item,
    requestPayload,
    task: {
      id: task.id,
      module_name: task.module_name,
      workflow_id: task.workflow_id,
      status: task.status,
    },
    checks: {
      backendModule: requestPayload.module_name === item.backendModule,
      workflow: requestPayload.workflow_id === item.workflow,
      taskCompleted: task.status === "completed",
      planLinked: Boolean(requestPayload.parameters_json?.data_preparation_plan_id),
    },
  };
}

const evidence = {
  status: "failed",
  generatedAt: new Date().toISOString(),
  frontendUrl: FRONTEND_URL,
  sampleEdf: SAMPLE_EDF,
  actionsExpected: ACTIONS,
  actionResults: [],
  screenshots: [],
  errors: [],
};

if (!fs.existsSync(SAMPLE_EDF)) {
  evidence.errors.push(`Sample EDF not found: ${SAMPLE_EDF}`);
  writeEvidence(evidence);
  console.log(JSON.stringify(evidence, null, 2));
  process.exit(1);
}

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
page.on("pageerror", (error) => evidence.errors.push(error.message));
page.on("console", (msg) => {
  if (msg.type() === "error") evidence.errors.push(msg.text());
});

try {
  await login(page);
  await prepareRunnableWorkbench(page, evidence);
  for (const item of ACTIONS) {
    const result = await runAction(page, item);
    evidence.actionResults.push(result);
  }
  const screenshotPath = path.join(OUT_DIR, "main_workbench_direct_method_clickthrough_e2e.png");
  await page.screenshot({ path: screenshotPath, fullPage: true, timeout: 15000 });
  evidence.screenshots.push(screenshotPath);
  evidence.status = evidence.actionResults.length === ACTIONS.length
    && evidence.actionResults.every((result) => Object.values(result.checks).every(Boolean))
    && evidence.errors.length === 0
    ? "passed"
    : "failed";
} catch (error) {
  evidence.errors.push(error.message);
} finally {
  writeEvidence(evidence);
  await browser.close().catch((error) => {
    evidence.errors.push(`browser close failed: ${error.message}`);
    writeEvidence(evidence);
  });
}

console.log(JSON.stringify(evidence, null, 2));
if (evidence.status !== "passed") process.exit(1);
