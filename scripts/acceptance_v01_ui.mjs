import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const { chromium } = require("../frontend/node_modules/playwright");
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const FRONTEND_URL = process.env.QLANALYSER_FRONTEND_URL || "http://127.0.0.1:4174/";
const SAMPLE_FIF = process.env.QLANALYSER_UI_SAMPLE || path.resolve("work/acceptance/ui_with_events_raw.fif");
const API_BASE = process.env.QLANALYSER_API_URL || "http://127.0.0.1:8001/api";
const EVIDENCE_PATH = process.env.QLANALYSER_UI_EVIDENCE_PATH || "";
const CUSTOMER_DENYLIST = [
  "v0.1",
  "demo",
  "Demo",
  "本地演示",
  "local API",
  "后台",
  "管理员",
  "API 服务",
  "费用",
  "开票",
  "发票",
  "Oddball",
  "示例结果",
  "模块中心",
  "体验中心",
  "publication_package.zip",
  "analysis_manifest.json",
  "subject_level_metrics.csv",
  "statistics_summary.csv",
];
const MOJIBAKE_PATTERNS = [
  "瀹㈡埛",
  "椤圭洰",
  "鐮旂┒",
  "鍏ㄦ緶",
  "鏁版嵁",
  "绛夊緟",
  "杩愯",
  "鎶ュ憡",
  "�",
];

function assertCleanText(text) {
  const hits = MOJIBAKE_PATTERNS.filter((item) => text.includes(item));
  if (/\?{3,}/.test(text) || text.includes("\uFFFD") || hits.length) {
    throw new Error(`UI contains mojibake/readiness text (${hits.join(", ")}): ${text.slice(0, 500)}`);
  }
}

function isAllowedCustomerOperationsTerm(item) {
  return item === "\u8d39\u7528" || item === "\u5f00\u7968" || item === "\u53d1\u7968";
}

function assertCustomerCopy(text, scope) {
  assertCleanText(text);
  const hits = CUSTOMER_DENYLIST.filter((item) => text.includes(item) && !isAllowedCustomerOperationsTerm(item));
  if (hits.length) {
    throw new Error(`${scope} exposes internal/customer-hostile copy: ${hits.join(", ")}\n${text.slice(0, 800)}`);
  }
}

async function assertCustomerOpsSurfaces(page) {
  const bodyText = await page.locator("body").innerText();
  for (const required of ["\u8d39\u7528", "\u53d1\u7968\u7533\u8bf7", "\u53d1\u7968\u7bb1"]) {
    if (!bodyText.includes(required)) {
      throw new Error(`customer operations surface missing: ${required}`);
    }
  }
  for (const selector of ['button[data-view="billing"]', 'button[data-view="invoice"]']) {
    const count = await page.locator(selector).count();
    if (count !== 1) {
      throw new Error(`customer operations navigation selector missing or duplicated: ${selector}`);
    }
  }
}

async function assertLabLink(page, selector, scope) {
  const locator = page.locator(selector).first();
  await locator.waitFor({ state: "attached", timeout: 10000 });
  const href = await locator.evaluate((node) => node.href);
  const url = new URL(href);
  if (url.searchParams.get("api") !== API_BASE) {
    throw new Error(`${scope} does not preserve current API base: ${href}`);
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
  const pageFailures = [];
  const taskPosts = [];

  page.on("pageerror", (err) => pageErrors.push(err.message));
  page.on("response", (response) => {
    if (response.url().includes("/api/")) {
      apiResponses.push({ url: response.url(), status: response.status() });
    }
    const status = response.status();
    const url = response.url();
    if (status >= 400 && !url.includes("/api/") && !url.endsWith("/favicon.ico")) {
      pageFailures.push({ url, status });
    }
  });

  const pilotUrl = new URL(FRONTEND_URL);
  pilotUrl.searchParams.set("pilot", "1");

  await page.goto(FRONTEND_URL, { waitUntil: "domcontentloaded" });
  await page.waitForSelector("#customerLoginForm", { timeout: 10000 });
  assertCustomerCopy(await page.locator("body").innerText(), "login page");
  await assertLabLink(page, 'a.lab-entry-btn[data-lab-link="module-lab"]', "login research workbench link");
  if (await page.locator('[data-login-tab="adminLogin"]:visible').count()) {
    throw new Error("Login page exposes a visible operations entry");
  }

  await page.goto(pilotUrl.toString(), { waitUntil: "domcontentloaded" });
  await page.waitForSelector("#appShell:not([hidden])", { timeout: 10000 });
  await page.waitForSelector(".shell", { timeout: 10000 });
  await page.waitForSelector(".nav-item[data-role=\"customer\"]", { timeout: 10000 });
  await page.waitForFunction(() => document.body.innerText.includes("QLanalyser Online"), null, { timeout: 15000 });
  await page.click('button[data-view="dashboard"]');
  await page.waitForSelector('button[data-real-action="create-project"]', { timeout: 10000 });
  await page.waitForFunction(() => document.body.innerText.includes("\u5f00\u59cb\u672c\u6b21\u5206\u6790"), null, { timeout: 15000 });
  assertCustomerCopy(await page.locator("body").innerText(), "customer dashboard");
  await assertCustomerOpsSurfaces(page);
  if (await page.locator('[data-role="admin"]:visible').count()) {
    throw new Error("Customer dashboard exposes visible operations navigation");
  }
  if (await page.locator('[data-secondary-flow="true"]:visible').count()) {
    throw new Error("Customer dashboard exposes secondary/account navigation in the primary path");
  }
  await assertLabLink(page, 'a.workbench-link[data-lab-link="module-lab"]', "top research workbench link");
  await page.waitForSelector(".research-workbench-panel", { timeout: 10000 });
  if ((await page.locator(".research-workbench-panel .research-card").count()) !== 3) {
    throw new Error("Research workbench should expose three bounded lab entries");
  }
  for (const selector of [
    'a.research-card[data-lab-link="qc-lab"]',
    'a.research-card[data-lab-link="module-lab"]',
    'a.research-card[data-lab-link="research-modules"]',
  ]) {
    await assertLabLink(page, selector, `dashboard lab link ${selector}`);
  }
  for (const action of ["run-psd", "run-erp", "create-report"]) {
    if (!(await page.locator(`button[data-real-action="${action}"]`).isDisabled())) {
      throw new Error(`${action} should be gated before a confirmed plan or completed analysis task`);
    }
  }

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
    await page.waitForSelector(`button[data-real-action="run-${moduleName}"]:not([disabled])`, { timeout: 15000 });
    const taskResponse = await waitForApi(
      page,
      `run ${moduleName}`,
      (response) => response.url().includes(`${API_BASE}/tasks`) && response.request().method() === "POST" && response.status() === 200,
      () => page.click(`button[data-real-action="run-${moduleName}"]`),
      30000
    );
    const task = await taskResponse.json();
    const payload = taskResponse.request().postDataJSON();
    taskPosts.push({ module: moduleName, id: task.id, status: task.status, payload });
    if (!task.id || task.status !== "completed") {
      throw new Error(`Expected completed ${moduleName} task, got: ${JSON.stringify(task)}`);
    }
    if (moduleName === "qc") {
      await page.waitForFunction(() => {
        const text = document.querySelector("#realPlanState")?.innerText || "";
        return /(?:prep|plan)_[a-zA-Z0-9]/.test(text) && /第\s*\d+\s*版/.test(text);
      }, null, { timeout: 10000 });
      for (const action of ["run-psd", "run-erp"]) {
        if (await page.locator(`button[data-real-action="${action}"]`).isDisabled()) {
          throw new Error(`${action} should be enabled after a confirmed data preparation plan`);
        }
      }
    }
    if (["psd", "erp"].includes(moduleName)) {
      const params = payload?.parameters_json || {};
      if (!params.data_preparation_plan_id || !Number.isFinite(Number(params.data_preparation_revision))) {
        throw new Error(`${moduleName} task payload is missing data_preparation_plan_id/revision: ${JSON.stringify(payload)}`);
      }
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
  const reportPackage = page.locator('#realReportDownloads a[href*="/reports/"][href*="/package"]').first();
  await reportPackage.waitFor({ timeout: 10000 });
  const reportPackageHref = await reportPackage.getAttribute("href");
  if (!reportPackageHref?.includes(`${API_BASE}/reports/${report.id}/package`)) {
    throw new Error(`Report package link is not bound to the real report endpoint: ${reportPackageHref}`);
  }
  await page.click('[data-view-jump="publication"]');
  const deliveryPackageHref = await page.locator('#realDeliveryLinks a[href*="/reports/"][href*="/package"]').first().getAttribute("href");
  if (!deliveryPackageHref?.includes(`${API_BASE}/reports/${report.id}/package`)) {
    throw new Error(`Delivery package link is not bound to the real report endpoint: ${deliveryPackageHref}`);
  }
  const packageResponse = await page.request.get(`${API_BASE}/reports/${report.id}/package`);
  if (packageResponse.status() !== 200) {
    throw new Error(`Report package download failed: ${packageResponse.status()} ${await packageResponse.text()}`);
  }
  const packageBody = await packageResponse.body();
  const packageContentType = packageResponse.headers()["content-type"] || "";
  const zipHeader = packageBody.subarray(0, 2).toString("utf8");
  if (zipHeader !== "PK") {
    throw new Error(`Report package response is not a ZIP file: header=${JSON.stringify(zipHeader)} content-type=${packageContentType}`);
  }
  const staticAssetLinks = await page.$$eval(
    'a[href*="publication_package.zip"], a[href*="analysis_manifest.json"], a[href*="subject_level_metrics.csv"], a[href*="statistics_summary.csv"]',
    (anchors) => anchors.map((anchor) => anchor.href)
  );
  if (staticAssetLinks.length) {
    throw new Error(`Customer flow exposes static report/result assets: ${staticAssetLinks.join(", ")}`);
  }

  const bodyText = await page.locator("body").innerText();
  assertCleanText(bodyText);
  if (pageErrors.length) throw new Error(`Page errors: ${pageErrors.join("; ")}`);
  if (pageFailures.length) throw new Error(`Page asset/navigation failures: ${JSON.stringify(pageFailures.slice(0, 10))}`);

  const result = {
    status: "passed",
    frontendUrl: FRONTEND_URL,
    apiBase: API_BASE,
    sample: SAMPLE_FIF,
    projectId: project.id,
    uploadedFileId: uploaded.id,
    reportId: report.id,
    reportPackageHref,
    deliveryPackageHref,
    packageDownload: {
      status: packageResponse.status(),
      contentType: packageContentType,
      bytes: packageBody.length,
      zipHeader,
    },
    taskPosts,
    apiCalls: apiResponses.length
  };
  if (EVIDENCE_PATH) {
    fs.mkdirSync(path.dirname(EVIDENCE_PATH), { recursive: true });
    fs.writeFileSync(EVIDENCE_PATH, `${JSON.stringify(result, null, 2)}\n`, "utf8");
  }
  console.log(JSON.stringify(result, null, 2));

  await browser.close();
}

run().catch((error) => {
  console.error(error);
  process.exit(1);
});
