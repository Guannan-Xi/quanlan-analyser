import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const { chromium } = require("../frontend/node_modules/playwright");
import fs from "node:fs";
import path from "node:path";

const FRONTEND_URL = process.env.QLANALYSER_FRONTEND_URL || "http://127.0.0.1:4174/?pilot=1&api=http://127.0.0.1:8001/api";
const API_BASE = process.env.QLANALYSER_API_URL || new URL(FRONTEND_URL).searchParams.get("api") || "http://127.0.0.1:8001/api";
const SAMPLE_FIF = process.env.QLANALYSER_UI_SAMPLE || path.resolve("work/acceptance/ui_with_events_raw.fif");
const EVIDENCE_PATH = process.env.QLANALYSER_PRESET_ANALYSIS_EVIDENCE || path.resolve("work/release_evidence/20260620-customer-preset-analysis/customer_preset_analysis.json");
const SCREENSHOT_PATH = process.env.QLANALYSER_PRESET_ANALYSIS_SCREENSHOT || path.resolve("work/release_evidence/20260620-customer-preset-analysis/customer_preset_analysis.png");

function writeEvidence(payload) {
  fs.mkdirSync(path.dirname(EVIDENCE_PATH), { recursive: true });
  fs.mkdirSync(path.dirname(SCREENSHOT_PATH), { recursive: true });
  fs.writeFileSync(EVIDENCE_PATH, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
}

async function waitForApi(page, label, predicate, action, timeout = 30000) {
  const responsePromise = page.waitForResponse(predicate, { timeout });
  await action();
  const response = await responsePromise;
  if (!response.ok()) throw new Error(`${label} failed with HTTP ${response.status()}`);
  return response;
}

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const evidence = {
  status: "failed",
  url: FRONTEND_URL,
  apiBase: API_BASE,
  screenshot: SCREENSHOT_PATH,
  visualStatus: "failed",
  screenshotExists: false,
  screenshotBytes: 0,
  checks: { psd: {}, erp: {} },
  taskPayloads: [],
  errors: [],
  warnings: [],
};

page.on("request", async (request) => {
  if (request.url().includes(`${API_BASE}/tasks`) && request.method() === "POST") {
    evidence.taskPayloads.push(JSON.parse(request.postData() || "{}"));
  }
});
page.on("pageerror", (error) => evidence.errors.push(error.message));
page.on("console", (msg) => {
  if (msg.type() === "error") evidence.errors.push(msg.text());
});

try {
  await page.goto(FRONTEND_URL, { waitUntil: "domcontentloaded" });
  await page.waitForSelector("#appShell:not([hidden])", { timeout: 15000 });
  await page.click('button[data-view="dashboard"]');
  await page.click('[data-real-action="create-project"]');
  await page.waitForTimeout(1000);
  if (!fs.existsSync(SAMPLE_FIF)) throw new Error(`Sample FIF not found: ${SAMPLE_FIF}`);
  await page.setInputFiles("#real-eeg-file", SAMPLE_FIF);
  await page.click('[data-real-action="upload-eeg"]');
  await page.waitForTimeout(1500);
  await page.click('button[data-view="analysis"]');
  await page.waitForSelector("#templateList .method-preset", { timeout: 15000 });
  evidence.checks.hasPresetFields = await page.locator("#presetPsdFmin").count() === 1
    && await page.locator("#presetPsdFmax").count() === 1
    && await page.locator('[data-real-action="run-psd-inline"]').count() === 1;

  await waitForApi(
    page,
    "confirm data-preparation plan",
    (response) => response.url().includes(`${API_BASE}/data-preparation/plans`) && response.request().method() === "POST" && response.status() === 200,
    () => page.click('[data-real-action="confirm-plan-inline"]')
  );
  await page.waitForFunction(() => {
    const text = document.querySelector("#realPlanState")?.innerText || "";
    return text.includes("prep_") || text.includes("revision");
  }, null, { timeout: 15000 });

  await page.locator("#presetPsdFmin").fill("2");
  await page.locator("#presetPsdFmax").fill("35");
  const psdTaskResponse = await waitForApi(
    page,
    "run preset PSD task",
    (response) => response.url().includes(`${API_BASE}/tasks`) && response.request().method() === "POST" && response.status() === 200,
    () => page.click('[data-real-action="run-psd-inline"]')
  );
  const psdTask = await psdTaskResponse.json();
  await page.waitForFunction(() => document.querySelectorAll('#realResultReview a[href*="/artifacts/"]').length > 0, null, { timeout: 15000 });
  evidence.checks.psd.downloadLinks = await page.locator('#realResultReview a[href*="/artifacts/"]').count();
  evidence.checks.psd.taskCompleted = psdTask.status === "completed" && psdTask.module_name === "psd";
  const psdArtifactsResponse = await fetch(`${API_BASE}/tasks/${encodeURIComponent(psdTask.id)}/artifacts`);
  if (!psdArtifactsResponse.ok) throw new Error(`PSD artifact lookup failed with HTTP ${psdArtifactsResponse.status}`);
  const psdArtifacts = await psdArtifactsResponse.json();
  evidence.checks.psd.bandpowerArtifacts = psdArtifacts
    .filter((item) => ["band_power", "channel_band_power"].includes(item.label) || /band_power\.csv$/.test(item.path || ""))
    .map((item) => ({ label: item.label, artifact_type: item.artifact_type, path: item.path }));
  evidence.checks.psd.bandpowerOutputsPresent = evidence.checks.psd.bandpowerArtifacts.some((item) => item.label === "band_power")
    && evidence.checks.psd.bandpowerArtifacts.some((item) => item.label === "channel_band_power");
  const psdPayload = evidence.taskPayloads.find((item) => item.module_name === "psd") || {};
  evidence.checks.psd.parametersSubmitted = psdPayload.parameters_json?.fmin === 2 && psdPayload.parameters_json?.fmax === 35;
  evidence.checks.psd.planLinked = Boolean(psdPayload.parameters_json?.data_preparation_plan_id) && Number.isFinite(Number(psdPayload.parameters_json?.data_preparation_revision));

  await page.locator("#presetErpStandard").fill("1");
  await page.locator("#presetErpTarget").fill("2");
  await page.locator("#presetErpTmin").fill("-0.25");
  await page.locator("#presetErpTmax").fill("0.75");
  await page.locator("#presetErpBaselineStart").fill("-0.25");
  await page.locator("#presetErpBaselineEnd").fill("0");
  const erpTaskResponse = await waitForApi(
    page,
    "run preset ERP task",
    (response) => response.url().includes(`${API_BASE}/tasks`) && response.request().method() === "POST" && response.status() === 200,
    () => page.click('[data-real-action="run-erp-inline"]'),
    45000
  );
  const erpTask = await erpTaskResponse.json();
  await page.waitForFunction(() => {
    const review = document.querySelector("#realResultReview")?.innerText || "";
    return review.includes("ERP") || review.includes("erp_p300");
  }, null, { timeout: 15000 });
  evidence.checks.erp.downloadLinks = await page.locator('#realResultReview a[href*="/artifacts/"]').count();
  evidence.checks.erp.taskCompleted = erpTask.status === "completed" && erpTask.module_name === "erp";
  const erpPayload = evidence.taskPayloads.find((item) => item.module_name === "erp") || {};
  evidence.checks.erp.parametersSubmitted = erpPayload.parameters_json?.event_id?.standard === 1
    && erpPayload.parameters_json?.event_id?.target === 2
    && erpPayload.parameters_json?.tmin === -0.25
    && erpPayload.parameters_json?.tmax === 0.75
    && Array.isArray(erpPayload.parameters_json?.baseline)
    && erpPayload.parameters_json.baseline[0] === -0.25
    && erpPayload.parameters_json.baseline[1] === 0;
  evidence.checks.erp.planLinked = Boolean(erpPayload.parameters_json?.data_preparation_plan_id) && Number.isFinite(Number(erpPayload.parameters_json?.data_preparation_revision));
  try {
    await page.screenshot({ path: SCREENSHOT_PATH, fullPage: true, timeout: 10000 });
  } catch (error) {
    evidence.warnings.push(`full-page screenshot fallback used: ${error.message}`);
    await page.locator("#appShell").screenshot({ path: SCREENSHOT_PATH, timeout: 10000 });
  }
  const screenshotStat = fs.statSync(SCREENSHOT_PATH);
  evidence.screenshotExists = screenshotStat.isFile();
  evidence.screenshotBytes = screenshotStat.size;
  evidence.visualStatus = evidence.screenshotExists && evidence.screenshotBytes > 0 ? "passed" : "failed";
  evidence.status = evidence.checks.hasPresetFields
    && evidence.checks.psd.taskCompleted
    && evidence.checks.psd.parametersSubmitted
    && evidence.checks.psd.planLinked
    && evidence.checks.psd.downloadLinks > 0
    && evidence.checks.psd.bandpowerOutputsPresent
    && evidence.checks.erp.taskCompleted
    && evidence.checks.erp.parametersSubmitted
    && evidence.checks.erp.planLinked
    && evidence.checks.erp.downloadLinks > 0
    && evidence.visualStatus === "passed"
    && evidence.errors.length === 0 ? "passed" : "failed";
} catch (error) {
  evidence.errors.push(error.message);
} finally {
  await browser.close();
  writeEvidence(evidence);
}

console.log(JSON.stringify(evidence, null, 2));
if (evidence.status !== "passed") process.exit(1);
