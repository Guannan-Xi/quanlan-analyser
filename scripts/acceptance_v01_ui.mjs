import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const { chromium } = require("../frontend/node_modules/playwright");
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const FRONTEND_URL = process.env.QLANALYSER_FRONTEND_URL || "http://127.0.0.1:4174/";
const SAMPLE_FIF = process.env.QLANALYSER_UI_SAMPLE || path.resolve("work/acceptance/ui_with_events_raw.fif");
const API_BASE = process.env.QLANALYSER_API_URL || "http://127.0.0.1:8000/api";

function assertCleanText(text) {
  if (/\?{3,}/.test(text) || text.includes("\uFFFD")) {
    throw new Error(`UI contains mojibake/readiness text: ${text.slice(0, 500)}`);
  }
}

async function waitForApi(page, label, matcher, trigger, timeout = 30000) {
  console.log(`[ui] waiting: ${label}`);
  const responsePromise = page.waitForResponse(matcher, { timeout });
  await trigger();
  const response = await responsePromise;
  console.log(`[ui] ${label}: ${response.status()} ${response.request().method()} ${response.url()}`);
  return response;
}

async function run() {
  if (!fs.existsSync(SAMPLE_FIF)) {
    throw new Error(`Sample FIF not found: ${SAMPLE_FIF}. Generate it with scripts/acceptance_v01_full.py or the documented MNE snippet.`);
  }

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const pageErrors = [];
  const apiResponses = [];
  const taskPosts = [];

  page.on("pageerror", (err) => pageErrors.push(err.message));
  page.on("response", (response) => {
    if (response.url().includes("/api/")) {
      apiResponses.push({ url: response.url(), status: response.status() });
    }
  });

  await page.goto(FRONTEND_URL, { waitUntil: "domcontentloaded" });
  await page.waitForSelector("#customerLoginForm", { timeout: 10000 });
  assertCleanText(await page.locator("body").innerText());

  await page.click("#demoEntryBtn");
  await page.waitForSelector("#appShell:not([hidden])", { timeout: 10000 });
  await page.waitForSelector(".shell", { timeout: 10000 });
  await page.waitForSelector(".nav-item[data-role=\"customer\"]", { timeout: 10000 });
  await page.waitForFunction(() => document.body.innerText.includes("QLanalyser Online"), null, { timeout: 15000 });
  await page.click('button[data-view="dashboard"]');
  await page.waitForSelector('button[data-real-action="create-project"]', { timeout: 10000 });
  await page.waitForFunction(() => document.body.innerText.includes("\u771f\u5b9e\u5206\u6790\u94fe\u8def"), null, { timeout: 15000 });

  const projectResponse = await waitForApi(
    page,
    "create project",
    (response) => response.url().includes(`${API_BASE}/projects`) && response.request().method() === "POST" && response.status() === 200,
    () => page.click('button[data-real-action="create-project"]')
  );
  const project = await projectResponse.json();
  if (!project.id) throw new Error(`Project response missing id: ${JSON.stringify(project)}`);
  await page.waitForFunction(() => document.body.innerText.includes("\u9879\u76ee\u5df2\u521b\u5efa"), null, { timeout: 10000 });

  const invalid = path.join(os.tmpdir(), `qlanalyser-ui-invalid-${Date.now()}.txt`);
  fs.writeFileSync(invalid, "not eeg");
  await page.setInputFiles("#real-eeg-file", invalid);
  const invalidUploadResponse = await waitForApi(
    page,
    "invalid upload",
    (response) => response.url().includes(`${API_BASE}/eeg/upload`) && response.status() === 422,
    () => page.click('button[data-real-action="upload-eeg"]')
  );
  const invalidPayload = await invalidUploadResponse.json();
  const invalidText = JSON.stringify(invalidPayload);
  if (!/Unsupported EEG file format|Uploaded EEG file is empty/i.test(invalidText)) {
    throw new Error(`Expected unsupported-format API error, got: ${invalidText}`);
  }
  await page.waitForSelector("#realRuntimeStatus.status-error", { timeout: 10000 });

  await page.setInputFiles("#real-eeg-file", SAMPLE_FIF);
  const uploadResponse = await waitForApi(
    page,
    "valid upload",
    (response) => response.url().includes(`${API_BASE}/eeg/upload`) && response.status() === 200,
    () => page.click('button[data-real-action="upload-eeg"]'),
    30000
  );
  const uploaded = await uploadResponse.json();
  if (!uploaded.id) throw new Error(`Upload response missing id: ${JSON.stringify(uploaded)}`);

  for (const moduleName of ["qc", "psd", "erp"]) {
    const taskResponse = await waitForApi(
      page,
      `run ${moduleName}`,
      (response) => response.url().includes(`${API_BASE}/tasks`) && response.request().method() === "POST" && response.status() === 200,
      () => page.click(`button[data-real-action="run-${moduleName}"]`),
      30000
    );
    const task = await taskResponse.json();
    taskPosts.push({ module: moduleName, id: task.id, status: task.status });
    if (!task.id || task.status !== "completed") {
      throw new Error(`Expected completed ${moduleName} task, got: ${JSON.stringify(task)}`);
    }
  }

  const reportResponse = await waitForApi(
    page,
    "create report",
    (response) => response.url().includes(`${API_BASE}/reports`) && response.request().method() === "POST" && response.status() === 200,
    () => page.click('button[data-real-action="create-report"]'),
    30000
  );
  const report = await reportResponse.json();
  if (!report.id) throw new Error(`Report response missing id: ${JSON.stringify(report)}`);
  await page.waitForSelector('#realReportDownloads a[href*="package"]', { timeout: 10000 });

  const bodyText = await page.locator("body").innerText();
  assertCleanText(bodyText);
  if (pageErrors.length) throw new Error(`Page errors: ${pageErrors.join("; ")}`);

  console.log(JSON.stringify({
    status: "passed",
    frontendUrl: FRONTEND_URL,
    apiBase: API_BASE,
    sample: SAMPLE_FIF,
    projectId: project.id,
    uploadedFileId: uploaded.id,
    reportId: report.id,
    taskPosts,
    apiCalls: apiResponses.length
  }, null, 2));

  await browser.close();
}

run().catch((error) => {
  console.error(error);
  process.exit(1);
});
