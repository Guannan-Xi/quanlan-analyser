import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium, chromiumLaunchOptions, classifyAcceptanceFailure } from "./lib/playwright_runtime.mjs";

const __filename = fileURLToPath(import.meta.url);
const ROOT = path.resolve(path.dirname(__filename), "..");
const DEFAULT_API = "http://127.0.0.1:8001/api";
const DEFAULT_FRONTEND = "http://127.0.0.1:4174";
const CUSTOMER_EMAIL = process.env.QLANALYSER_DEMO_EMAIL || "demo.customer@quanlan.cn";
const CUSTOMER_PASSWORD = process.env.QLANALYSER_DEMO_PASSWORD || "demo123456";
const ADMIN_EMAIL = process.env.QLANALYSER_ADMIN_EMAIL || "ops@quanlan.cn";
const ADMIN_PASSWORD = process.env.QLANALYSER_ADMIN_PASSWORD || "ops-demo-2026";
const TIMEOUT_MS = Number(process.env.QLANALYSER_UI_TIMEOUT_MS || 30000);

function argValue(name, fallback = "") {
  const idx = process.argv.indexOf(name);
  if (idx >= 0 && process.argv[idx + 1]) return process.argv[idx + 1];
  return fallback;
}

function timestamp() {
  const now = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}_${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
}

const apiBase = (argValue("--api") || process.env.QLANALYSER_API_URL || process.env.QLANALYSER_API_BASE_URL || DEFAULT_API).replace(/\/$/, "");
const frontendBase = (argValue("--frontend") || process.env.QLANALYSER_TARGET_URL || process.env.QLANALYSER_FRONTEND_URL || DEFAULT_FRONTEND).replace(/\/$/, "");
const outDir = path.resolve(argValue("--out") || process.env.QLANALYSER_E2E_ADVERSARIAL_OUT || path.join(ROOT, "work", "release_evidence", `user_level_e2e_adversarial_${timestamp()}`));
const screenshotDir = path.join(outDir, "screenshots");
const frontendUrl = (() => {
  const url = new URL(frontendBase);
  url.searchParams.set("api", apiBase);
  return url.toString();
})();

fs.mkdirSync(screenshotDir, { recursive: true });

const result = {
  standard: "qlanalyser_user_level_e2e_adversarial_review_standard_20260702",
  script: "scripts/e2e_user_level_adversarial_acceptance.mjs",
  started_at: new Date().toISOString(),
  finished_at: null,
  status: "running",
  verdict: "running",
  classification: "running",
  frontend_url: frontendUrl,
  api_base: apiBase,
  evidence_dir: outDir,
  steps: [],
  screenshots: [],
  findings: [],
  remaining_risks: [],
};

function addStep(name, ok, detail = {}, severity = ok ? "pass" : "P1") {
  const entry = { name, ok: Boolean(ok), severity, detail };
  result.steps.push(entry);
  if (!ok && severity !== "warn") {
    result.findings.push({ id: `E2E-${String(result.findings.length + 1).padStart(3, "0")}`, severity, name, detail });
  }
  return entry;
}

function pCounts() {
  const counts = { P0: 0, P1: 0, P2: 0, P3: 0 };
  for (const finding of result.findings) {
    if (counts[finding.severity] !== undefined) counts[finding.severity] += 1;
  }
  return counts;
}

async function api(pathname, options = {}) {
  const response = await fetch(`${apiBase}${pathname}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.token ? { Authorization: `Bearer ${options.token}` } : {}),
      ...(options.headers || {}),
    },
    body: options.body && typeof options.body !== "string" ? JSON.stringify(options.body) : options.body,
  });
  let body = null;
  const text = await response.text();
  try { body = text ? JSON.parse(text) : null; } catch { body = text; }
  return { status: response.status, ok: response.ok, body };
}

async function probe(label, url) {
  try {
    const response = await fetch(url, { cache: "no-store" });
    addStep(`preflight:${label}`, response.ok, { status: response.status, url }, response.ok ? "pass" : "P0");
    return response.ok;
  } catch (error) {
    addStep(`preflight:${label}`, false, { url, error: error.message }, "P0");
    return false;
  }
}

async function screenshot(page, name, selector = "body") {
  const file = path.join(screenshotDir, `${name}.png`);
  const locator = page.locator(selector).first();
  try {
    const hasTarget = (await locator.count()) > 0;
    const targetVisible = hasTarget ? await locator.isVisible().catch(() => false) : false;
    if (hasTarget && targetVisible) await locator.screenshot({ path: file, timeout: TIMEOUT_MS });
    else await page.screenshot({ path: file, fullPage: true, timeout: TIMEOUT_MS });
    result.screenshots.push({ name, path: file, selector, targetVisible });
    addStep(`screenshot:${name}`, true, { path: file, selector, targetVisible });
    return { ok: true, path: file, selector, targetVisible };
  } catch (error) {
    addStep(`screenshot:${name}`, false, { selector, error: error.message }, "P1");
    return { ok: false, selector, error: error.message, targetVisible: false };
  }
}

async function clickIfVisible(page, selector, label, severity = "P1") {
  const locator = page.locator(selector).first();
  const count = await locator.count();
  if (!count) {
    addStep(`click:${label}`, false, { selector, reason: "missing" }, severity);
    return false;
  }
  const visible = await locator.isVisible().catch(() => false);
  const enabled = await locator.isEnabled().catch(() => false);
  if (!visible || !enabled) {
    const title = await locator.getAttribute("title").catch(() => "");
    const disabledReason = await locator.getAttribute("data-disabled-reason").catch(() => "");
    addStep(`click:${label}`, false, { selector, visible, enabled, title, disabledReason }, severity);
    return false;
  }
  await locator.click({ timeout: TIMEOUT_MS });
  addStep(`click:${label}`, true, { selector });
  return true;
}

async function setView(page, hash, screenshotName, selector = "#appShell") {
  const viewName = String(hash || "").replace(/^#/, "");
  const nav = page.locator(`nav [data-view="${viewName}"]`).first();
  const anyNav = page.locator(`[data-view="${viewName}"]`).first();
  const jump = page.locator(`[data-view-jump="${viewName}"]`).first();
  if (await nav.count()) await nav.click({ timeout: TIMEOUT_MS });
  else if (await anyNav.count()) await anyNav.click({ timeout: TIMEOUT_MS });
  else if (await jump.count()) await jump.click({ timeout: TIMEOUT_MS });
  else await page.evaluate((targetView) => { window.location.hash = `#${targetView}`; }, viewName);
  await page.waitForSelector(selector, { state: "visible", timeout: TIMEOUT_MS }).catch(() => null);
  await page.waitForTimeout(500);
  const shot = await screenshot(page, screenshotName, selector);
  const activeView = await page.locator(`#${viewName}.active`).count().catch(() => 0);
  const visibleView = Boolean(shot?.targetVisible) || await page.locator(selector).first().isVisible().catch(() => false);
  addStep(`navigate:#${viewName}`, activeView > 0 || visibleView, { activeView, visibleView }, activeView > 0 || visibleView ? "pass" : "P1");
  return { activeView, visibleView, ok: activeView > 0 || visibleView };
}

async function activateTeachingDemo(page) {
  const teachingButton = page.locator("#teachingModeBtn").first();
  const hasButton = (await teachingButton.count()) > 0;
  if (!hasButton) {
    addStep("customer:teaching-demo-entry-visible", false, { selector: "#teachingModeBtn" }, "P1");
    return false;
  }
  await teachingButton.click({ timeout: TIMEOUT_MS });
  await page.waitForFunction(() => document.querySelectorAll("[data-project-select]").length > 0, null, { timeout: TIMEOUT_MS }).catch(() => null);
  const projectCount = await page.locator("[data-project-select]").count().catch(() => 0);
  addStep("customer:teaching-demo-loaded", projectCount > 0, { projectCount }, projectCount > 0 ? "pass" : "P1");
  const closeTeachingGuide = page.locator('[data-testid="teaching-step-card"] [data-teaching-action="close"]').last();
  if (await closeTeachingGuide.isVisible().catch(() => false)) {
    await closeTeachingGuide.click({ timeout: TIMEOUT_MS }).catch(() => {});
    await page.waitForTimeout(500);
  }
  return projectCount > 0;
}

async function openEpilepsyWorkbenchViaUserPath(page) {
  const entry = page.locator('[data-real-action="open-epilepsy-workbench"]').first();
  const hasEntry = (await entry.count()) > 0;
  if (!hasEntry) {
    addStep("customer:epilepsy-workbench-entry-visible", false, { selector: '[data-real-action="open-epilepsy-workbench"]' }, "P1");
    return false;
  }
  const enabled = await entry.isEnabled().catch(() => false);
  addStep("customer:epilepsy-workbench-entry-enabled", enabled, { selector: '[data-real-action="open-epilepsy-workbench"]' }, enabled ? "pass" : "P1");
  if (!enabled) return false;
  await entry.click({ timeout: TIMEOUT_MS });
  await page.waitForSelector('[data-testid="main-epilepsy-workbench-inline"]', { state: "visible", timeout: TIMEOUT_MS }).catch(() => null);
  const shot = await screenshot(page, "06-epilepsy", "#epilepsyWorkbenchInline");
  const visibleView = Boolean(shot?.targetVisible) || await page.locator('[data-testid="main-epilepsy-workbench-inline"]').first().isVisible().catch(() => false);
  const activeView = await page.locator("#epilepsyWorkbenchInline.active").count().catch(() => 0);
  addStep("navigate:#epilepsyWorkbenchInline", activeView > 0 || visibleView, { activeView, visibleView, via: "open-epilepsy-workbench" }, activeView > 0 || visibleView ? "pass" : "P1");
  return activeView > 0 || visibleView;
}

async function loginCustomer(page) {
  await page.addInitScript(() => {
    localStorage.removeItem("qlanalyser_auth_session");
    localStorage.removeItem("qlanalyser_customer_profile");
    sessionStorage.removeItem("qlanalyser_auth_session");
  });
  await page.goto(frontendUrl, { waitUntil: "domcontentloaded", timeout: TIMEOUT_MS });
  await screenshot(page, "01-login", "#loginScreen");
  await page.waitForSelector("#customerLoginForm", { state: "visible", timeout: TIMEOUT_MS });
  await page.fill("#customerEmail", CUSTOMER_EMAIL);
  await page.fill("#customerPassword", CUSTOMER_PASSWORD);
  await Promise.all([
    page.waitForSelector("#appShell:not([hidden])", { timeout: TIMEOUT_MS }),
    page.click("#customerLoginBtn"),
  ]);
  const visible = await page.locator("#appShell:not([hidden])").isVisible();
  addStep("customer:login-ui", visible, { email: CUSTOMER_EMAIL }, visible ? "pass" : "P0");
}

async function loginAdmin(page) {
  await page.goto(frontendUrl, { waitUntil: "domcontentloaded", timeout: TIMEOUT_MS });
  await page.waitForSelector("#customerLoginForm", { state: "visible", timeout: TIMEOUT_MS });
  await page.click('[data-login-tab="adminLogin"]');
  await page.fill("#adminEmail", ADMIN_EMAIL);
  await page.fill("#adminPassword", ADMIN_PASSWORD);
  await Promise.all([
    page.waitForSelector("#appShell:not([hidden])", { timeout: TIMEOUT_MS }),
    page.locator('#adminLoginForm button[type="submit"]').click(),
  ]);
  const visible = await page.locator("#appShell:not([hidden])").isVisible();
  addStep("admin:login-ui", visible, { email: ADMIN_EMAIL }, visible ? "pass" : "P1");
}

async function runApiBoundaryChecks(customerToken) {
  const badPassword = await api("/auth/login", { method: "POST", body: { email: CUSTOMER_EMAIL, password: "ab" } });
  addStep("api:short-password-returns-401", badPassword.status === 401, { status: badPassword.status }, badPassword.status === 401 ? "pass" : "P1");

  const missingProject = await api("/projects/not_found_project", { token: customerToken });
  addStep("api:missing-project-404", missingProject.status === 404, { status: missingProject.status }, missingProject.status === 404 ? "pass" : "P1");

  const emptyProject = await api("/projects", { method: "POST", token: customerToken, body: { name: "" } });
  addStep("api:empty-project-name-422", emptyProject.status === 422, { status: emptyProject.status }, emptyProject.status === 422 ? "pass" : "P1");

  const unauth = await api("/projects");
  addStep("api:unauthenticated-projects-blocked", [401, 403].includes(unauth.status), { status: unauth.status }, [401, 403].includes(unauth.status) ? "pass" : "P0");
}

async function run() {
  const frontendOk = await probe("frontend", frontendBase);
  const apiOk = await probe("api-health", `${apiBase}/health`);
  if (!frontendOk || !apiOk) throw new Error("service_unreachable");

  const customerLogin = await api("/auth/login", { method: "POST", body: { email: CUSTOMER_EMAIL, password: CUSTOMER_PASSWORD } });
  addStep("api:customer-login", customerLogin.ok, { status: customerLogin.status }, customerLogin.ok ? "pass" : "P0");
  const customerToken = customerLogin.body?.token;
  if (!customerToken) throw new Error("customer token missing");
  await runApiBoundaryChecks(customerToken);

  const browser = await chromium.launch(chromiumLaunchOptions({ headless: true }));
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const pageErrors = [];
  const consoleErrors = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("console", (message) => { if (message.type() === "error") consoleErrors.push(message.text()); });

  try {
    await loginCustomer(page);
    await screenshot(page, "02-dashboard", "#dashboard");
    await activateTeachingDemo(page);
    await screenshot(page, "02-dashboard-demo", "#dashboard");

    const projectCount = await page.locator("[data-project-select]").count().catch(() => 0);
    addStep("customer:project-list-visible", projectCount > 0, { projectCount }, projectCount > 0 ? "pass" : "P1");
    if (projectCount > 0) {
      await page.locator("[data-project-select]").first().click({ timeout: TIMEOUT_MS }).catch(() => {});
      await page.waitForTimeout(500);
      addStep("customer:select-first-project", true, { projectCount });
    }

    const createdProject = await api("/projects", {
      method: "POST",
      token: customerToken,
      body: { name: `E2E 用户验收项目 ${Date.now()}`, description: "Created by user-level E2E adversarial acceptance." },
    });
    addStep("customer:create-project-api-backed", createdProject.ok, { status: createdProject.status, id: createdProject.body?.id }, createdProject.ok ? "pass" : "P1");
    await page.waitForTimeout(500);

    await setView(page, "#storage", "03-storage", "#storage");
    const fileRows = await page.locator("[data-file-select]").count().catch(() => 0);
    addStep("customer:eeg-file-list-visible", fileRows > 0, { fileRows }, fileRows > 0 ? "pass" : "P1");

    const analysisNavigation = await setView(page, "#analysis", "04-analysis", "#analysis");
    const prepVisible = Boolean(analysisNavigation?.visibleView);
    addStep("customer:data-prep-panel-visible", prepVisible, { selector: "#analysis", visibleView: analysisNavigation?.visibleView }, prepVisible ? "pass" : "P1");

    await setView(page, "#workflow", "05-workflow", "#workflow");
    const methods = await page.locator("[data-module-id]").count().catch(() => 0);
    addStep("customer:analysis-methods-visible", methods >= 5, { methods }, methods >= 5 ? "pass" : "P1");

    const epilepsyOpened = await openEpilepsyWorkbenchViaUserPath(page);
    addStep("customer:epilepsy-workbench-visible", epilepsyOpened, { selector: "#epilepsyWorkbenchInline" }, epilepsyOpened ? "pass" : "P1");

    await setView(page, "#statistics", "07-results", "#statistics");
    const resultsVisible = await page.locator('[data-testid="results-review-workbench"], #realResultReview').first().isVisible().catch(() => false);
    addStep("customer:results-visible", resultsVisible, {}, resultsVisible ? "pass" : "P1");

    await setView(page, "#publication", "08-publication", "#publication");
    const deliveryVisible = await page.locator('[data-testid="report-delivery-workbench"], #realDeliveryLinks').first().isVisible().catch(() => false);
    addStep("customer:publication-visible", deliveryVisible, {}, deliveryVisible ? "pass" : "P1");

    await setView(page, "#userCenter", "09-user-center", "#userCenter");
    const balanceText = await page.locator("#walletBalance, #balanceMain").first().innerText().catch(() => "");
    addStep("customer:wallet-visible", /\d/.test(balanceText), { balanceText }, /\d/.test(balanceText) ? "pass" : "P1");

    const visibleText = await page.locator("body").innerText().catch(() => "");
    const diagnosticHits = ["确诊", "治愈", "疗效"].filter((term) => visibleText.includes(term));
    addStep("compliance:no-affirmative-medical-claims", diagnosticHits.length === 0, { diagnosticHits }, diagnosticHits.length === 0 ? "pass" : "P0");
    addStep("runtime:no-page-errors", pageErrors.length === 0, { pageErrors }, pageErrors.length === 0 ? "pass" : "P0");
    addStep("runtime:no-console-errors", consoleErrors.length === 0, { consoleErrors: consoleErrors.slice(0, 10) }, consoleErrors.length === 0 ? "pass" : "P2");
  } finally {
    await page.close().catch(() => {});
  }

  const adminPage = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  try {
    await loginAdmin(adminPage);
    await screenshot(adminPage, "10-admin-dashboard", "#adminDashboard");
    const adminText = await adminPage.locator("#adminDashboard, #appShell").first().innerText().catch(() => "");
    addStep("admin:dashboard-visible", adminText.length > 20, { sample: adminText.slice(0, 120) }, adminText.length > 20 ? "pass" : "P1");
  } finally {
    await adminPage.close().catch(() => {});
    await browser.close().catch(() => {});
  }
}

function writeOutputs() {
  const counts = pCounts();
  result.finished_at = new Date().toISOString();
  result.p0_count = counts.P0;
  result.p1_count = counts.P1;
  result.p2_count = counts.P2;
  result.p3_count = counts.P3;
  result.passed_steps = result.steps.filter((step) => step.ok).length;
  result.failed_steps = result.steps.filter((step) => !step.ok).length;
  if (result.classification === "running") {
    if (counts.P0 > 0) result.classification = "product_failed";
    else if (counts.P1 > 0 || counts.P2 > 0) result.classification = "conditional_pass";
    else result.classification = "passed";
  }
  result.status = result.classification;
  result.verdict = result.classification;
  const jsonPath = path.join(outDir, "user_level_e2e_adversarial_result.json");
  fs.writeFileSync(jsonPath, JSON.stringify(result, null, 2), "utf-8");

  const receipt = [
    "# QLanalyser User-Level E2E Adversarial Receipt",
    "",
    `- standard: ${result.standard}`,
    `- status: ${result.status}`,
    `- verdict: ${result.verdict}`,
    `- frontend_url: ${result.frontend_url}`,
    `- api_base: ${result.api_base}`,
    `- evidence_dir: ${result.evidence_dir}`,
    `- screenshots: ${result.screenshots.length}`,
    `- passed_steps: ${result.passed_steps}`,
    `- failed_steps: ${result.failed_steps}`,
    `- p0: ${result.p0_count}`,
    `- p1: ${result.p1_count}`,
    `- p2: ${result.p2_count}`,
    `- p3: ${result.p3_count}`,
    "",
    "## Findings",
    "",
    ...(result.findings.length ? result.findings.map((finding) => `- ${finding.severity} ${finding.name}: ${JSON.stringify(finding.detail)}`) : ["- none"]),
    "",
    "## Screenshots",
    "",
    ...result.screenshots.map((shot) => `- ${shot.name}: ${shot.path}`),
    "",
  ].join("\n");
  fs.writeFileSync(path.join(outDir, "user_level_e2e_adversarial_receipt.md"), receipt, "utf-8");
  return jsonPath;
}

try {
  await run();
} catch (error) {
  result.classification = classifyAcceptanceFailure(error, result);
  result.status = result.classification;
  result.verdict = result.classification;
  result.findings.push({ id: "E2E-FATAL", severity: result.classification === "product_failed" ? "P0" : "P1", name: "fatal", detail: { error: error.message, stack: error.stack } });
} finally {
  const jsonPath = writeOutputs();
  console.log(JSON.stringify({ status: result.status, verdict: result.verdict, evidence: jsonPath, p0: result.p0_count, p1: result.p1_count, p2: result.p2_count, screenshots: result.screenshots.length }, null, 2));
  if (result.status === "product_failed") process.exit(1);
  if (result.status === "environment_blocked" || result.status === "service_unreachable") process.exit(2);
}
