import fs from "node:fs";
import path from "node:path";
import { chromium, chromiumLaunchOptions, classifyAcceptanceFailure } from "./lib/playwright_runtime.mjs";

const API_BASE = process.env.QLANALYSER_API_BASE_URL || "http://127.0.0.1:8001/api";
const FRONTEND_URL =
  process.env.QLANALYSER_FRONTEND_URL ||
  `http://127.0.0.1:4174/?customer_demo=auto&e2e=teaching-quickstart&api=${encodeURIComponent(API_BASE)}`;
const CUSTOMER_EMAIL = process.env.QLANALYSER_DEMO_EMAIL || "demo.customer@quanlan.cn";
const CUSTOMER_PASSWORD = process.env.QLANALYSER_DEMO_PASSWORD || "demo123456";
const OUT_DIR =
  process.env.QLANALYSER_TEACHING_QUICKSTART_E2E_DIR ||
  path.resolve("work/release_evidence/07-full-product-e2e-pdca/16_teaching_quickstart_state");
const EVIDENCE_PATH = path.join(OUT_DIR, "teaching_quickstart_state_e2e.json");
const SCREENSHOT_PATH = path.join(OUT_DIR, "teaching_quickstart_analysis.png");

function check(name, pass, details = {}) {
  return { name, pass: Boolean(pass), details };
}

async function visible(page, selector) {
  return page.locator(selector).first().isVisible().catch(() => false);
}

async function loginAsCustomer(page) {
  await page.addInitScript(() => {
    localStorage.removeItem("qlanalyser_auth_session");
    localStorage.removeItem("qlanalyser_customer_profile");
    sessionStorage.removeItem("qlanalyser_auth_session");
  });
  await page.goto(FRONTEND_URL, { waitUntil: "domcontentloaded", timeout: 60000 });
  if (await visible(page, "#appShell:not([hidden])")) return;
  await page.waitForSelector("#customerLoginForm", { state: "visible", timeout: 30000 });
  await page.fill("#customerEmail", CUSTOMER_EMAIL);
  await page.fill("#customerPassword", CUSTOMER_PASSWORD);
  await Promise.all([
    page.waitForSelector("#appShell:not([hidden])", { timeout: 30000 }),
    page.locator("#customerLoginBtn").click(),
  ]);
}

async function collectQuickstartState(page) {
  return page.evaluate(() => {
    const e2e = window.__QLANALYSER_E2E_STATE__ || {};
    const route = window.__QLANALYSER_ROUTE_STATE__ || {};
    const projectSelect = document.querySelector("#workspaceProjectSelect");
    const fileSelect = document.querySelector("#workspaceFileSelect");
    const isVisible = (node) => {
      if (!node) return false;
      const rect = node.getBoundingClientRect();
      const style = getComputedStyle(node);
      return rect.width > 0 && rect.height > 0 && style.visibility !== "hidden" && style.display !== "none";
    };
    const visibleConfirmButtons = Array.from(document.querySelectorAll('[data-real-action="confirm-plan-inline"]')).filter(isVisible);
    const visibleText = document.querySelector("#appShell")?.innerText || document.body.innerText || "";
    return {
      activeView: document.querySelector(".view.active")?.id || "",
      routeActiveView: route.activeView || "",
      teachingActive: Boolean(route.teachingActive || e2e.teaching?.active),
      teachingLoaded: Boolean(e2e.teaching?.datasetLoaded),
      bodyHasProject: document.body.dataset.hasProject || "",
      bodyHasFile: document.body.dataset.hasFile || "",
      bodyAnalysisReady: document.body.dataset.analysisReady || "",
      projectId: e2e.real?.project?.id || "",
      fileId: e2e.real?.eegFile?.id || "",
      planId: e2e.real?.plan?.id || "",
      selectedProjectId: e2e.workspace?.selectedProjectId || "",
      selectedFileId: e2e.workspace?.selectedFileId || "",
      projectSelectValue: projectSelect?.value || "",
      fileSelectValue: fileSelect?.value || "",
      projectOptions: Array.from(projectSelect?.options || []).map((option) => option.value),
      fileOptions: Array.from(fileSelect?.options || []).map((option) => option.value),
      visibleTextSample: visibleText.slice(0, 1200),
      visibleHasDemoFile: visibleText.includes("teaching_oddball_with_montage_raw.fif"),
      visibleHasNextPrepare: visibleText.includes("确认准备并进入分析"),
      visibleConfirmCount: visibleConfirmButtons.length,
      confirmPlanDisabled: visibleConfirmButtons.some((button) => button.disabled),
    };
  });
}

async function main() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const evidence = {
    script: path.basename(new URL(import.meta.url).pathname),
    frontendUrl: FRONTEND_URL,
    apiBase: API_BASE,
    generatedAt: new Date().toISOString(),
    checks: [],
    pageErrors: [],
    consoleErrors: [],
    screenshot: SCREENSHOT_PATH,
    status: "running",
  };
  const browser = await chromium.launch(chromiumLaunchOptions({ headless: true }));
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  page.setDefaultTimeout(45000);
  page.on("pageerror", (error) => evidence.pageErrors.push(error.message || String(error)));
  page.on("console", (msg) => {
    if (msg.type() === "error") evidence.consoleErrors.push(msg.text());
  });

  try {
    await loginAsCustomer(page);
    await page.waitForSelector('[data-teaching-action="quickstart"]:visible', { timeout: 30000 });

    await page.locator('[data-teaching-action="quickstart"]:visible').first().click();
    await page.waitForFunction(
      () => {
        const e2e = window.__QLANALYSER_E2E_STATE__ || {};
        return (
          document.querySelector(".view.active")?.id === "analysis" &&
          e2e.real?.project?.id &&
          e2e.real?.eegFile?.id
        );
      },
      null,
      { timeout: 45000 },
    );
    await page.waitForTimeout(500);

    const state = await collectQuickstartState(page);
    evidence.state = state;
    evidence.checks.push(check("quickstart_lands_on_analysis", state.activeView === "analysis", state));
    evidence.checks.push(check("teaching_mode_active", state.teachingActive && state.teachingLoaded, state));
    evidence.checks.push(check("demo_project_selected", state.projectId === "proj_demo_learning" && state.selectedProjectId === state.projectId, state));
    evidence.checks.push(check("demo_file_selected", state.fileId === "eeg_demo_teaching_oddball" && state.selectedFileId === state.fileId, state));
    evidence.checks.push(check("project_selector_keeps_demo_value", state.projectSelectValue === state.projectId, state));
    evidence.checks.push(check("visible_demo_file_loaded", state.visibleHasDemoFile, state));
    evidence.checks.push(check("visible_next_step_is_prepare", state.visibleHasNextPrepare, state));
    evidence.checks.push(check("visible_confirm_not_disabled_when_present", !state.confirmPlanDisabled, state));
    evidence.checks.push(check("no_page_errors", evidence.pageErrors.length === 0, { pageErrors: evidence.pageErrors }));
    await page.screenshot({ path: SCREENSHOT_PATH, fullPage: true });
  } catch (error) {
    evidence.error = error.message || String(error);
    evidence.failureClass = classifyAcceptanceFailure(error, evidence);
    evidence.checks.push(check("unexpected_error", false, { message: evidence.error, failureClass: evidence.failureClass }));
  } finally {
    await browser.close();
  }

  evidence.status = evidence.checks.every((item) => item.pass) ? "passed" : "failed";
  fs.writeFileSync(EVIDENCE_PATH, `${JSON.stringify(evidence, null, 2)}\n`, "utf8");
  console.log(JSON.stringify(evidence, null, 2));
  process.exit(evidence.status === "passed" ? 0 : 1);
}

main();
