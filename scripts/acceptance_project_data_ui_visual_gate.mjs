import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";

const require = createRequire(import.meta.url);
const { chromium } = require("../frontend/node_modules/playwright");

const FRONTEND_URL = process.env.QLANALYSER_FRONTEND_URL || "http://127.0.0.1:4174/?customer_demo=login&api=http://127.0.0.1:8001/api";
const OUT_DIR = process.env.QLANALYSER_PROJECT_DATA_UI_GATE_DIR || path.resolve("work/release_evidence/ui_interaction_review/project_data_ui_gate");
const EVIDENCE_PATH = path.join(OUT_DIR, "project_data_ui_gate.json");
const CUSTOMER_EMAIL = process.env.QLANALYSER_DEMO_EMAIL || "demo.customer@quanlan.cn";
const CUSTOMER_PASSWORD = process.env.QLANALYSER_DEMO_PASSWORD || "demo123456";

const badVisibleMarkers = [
  "\uFFFD",
  "\u95ab",
  "\u9357",
  "\u7ef0",
  "\u6924",
  "\u6d93",
  "\u5be4",
  "acceptance-label",
  "persistent-label",
  "synthetic fixture dependent",
  "task_id",
];

function ensureDir() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
}

async function screenshot(page, name) {
  const target = path.join(OUT_DIR, `${name}.png`);
  await page.screenshot({ path: target, fullPage: true });
  return target;
}

async function login(page) {
  await page.addInitScript(() => {
    localStorage.removeItem("qlanalyser_auth_session");
    sessionStorage.removeItem("qlanalyser_auth_session");
  });
  await page.goto(FRONTEND_URL, { waitUntil: "domcontentloaded", timeout: 20000 });
  const loginForm = "#customerLoginForm";
  await page.waitForSelector(loginForm, { state: "visible", timeout: 15000 });
  await page.fill("#customerEmail", CUSTOMER_EMAIL);
  await page.fill("#customerPassword", CUSTOMER_PASSWORD);
  await Promise.all([
    page.waitForSelector("#appShell:not([hidden])", { timeout: 20000 }),
    page.locator("#customerLoginBtn").click(),
  ]);
  await page.waitForTimeout(1800);
}

async function collectState(page, name) {
  return page.evaluate(({ name, badVisibleMarkers }) => {
    const bodyText = document.body.innerText || "";
    const styleOf = (selector) => {
      const node = document.querySelector(selector);
      return node ? getComputedStyle(node).display : null;
    };
    const visible = (selector) => {
      const node = document.querySelector(selector);
      if (!node || node.hidden) return false;
      if (node.classList?.contains("visually-hidden-file")) return false;
      const style = getComputedStyle(node);
      const rect = node.getBoundingClientRect();
      return style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0;
    };
    const visibleScopedDataActions = Array.from(document.querySelectorAll('[data-ia-action="rename-data"], [data-ia-action="replace-data"], [data-ia-action="delete-data"]'))
      .filter((node) => {
        if (node.hidden) return false;
        const style = getComputedStyle(node);
        const parentStyle = node.parentElement ? getComputedStyle(node.parentElement) : null;
        return style.display !== "none" && parentStyle?.display !== "none";
      })
      .map((node) => node.innerText.trim());
    return {
      name,
      activeView: document.querySelector(".view.active")?.id || "",
      projectSelectCount: document.querySelector("#workspaceProjectSelect")?.options?.length || 0,
      projectSelectVisible: visible("#workspaceProjectSelect"),
      projectSelectOptions: Array.from(document.querySelector("#workspaceProjectSelect")?.options || []).map((option) => option.textContent.trim()).slice(0, 12),
      selectedProject: document.querySelector("#workspaceProjectSelect")?.value || "",
      projectSearchVisible: visible("#workspaceProjectSearch"),
      projectFilterSummary: document.querySelector("#workspaceProjectFilterSummary")?.innerText || "",
      showReviewProjectsChecked: Boolean(document.querySelector("#workspaceShowReviewProjects")?.checked),
      projectRowsText: document.querySelector("#iaProjectRows")?.innerText || "",
      visibleProjectRowCount: Array.from(document.querySelectorAll("#iaProjectRows [data-project-select]")).filter((node) => {
        const style = getComputedStyle(node);
        const rect = node.getBoundingClientRect();
        return style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0;
      }).length,
      dataPanelText: document.querySelector('[data-testid="project-data-crud-panel"]')?.innerText || "",
      dataRowsHidden: Boolean(document.querySelector("#iaDataRows")?.hidden),
      dataActionsDisplay: styleOf(".ia-data-actions"),
      dataEmptyVisible: visible("#iaDataEmptyState"),
      visibleScopedDataActions,
      badVisibleMarkers: badVisibleMarkers.filter((marker) => bodyText.includes(marker)),
      horizontalOverflow: document.documentElement.scrollWidth > window.innerWidth + 2,
      scrollWidth: document.documentElement.scrollWidth,
      innerWidth: window.innerWidth,
      innerHeight: window.innerHeight,
    };
  }, { name, badVisibleMarkers });
}

function checkNoSelection(state) {
  const issues = [];
  if (state.projectSelectVisible) issues.push("project compatibility select should be hidden; project panel/list must be primary");
  if (state.visibleProjectRowCount < 1) issues.push("project panel should show available project rows before selection");
  if (state.projectRowsText.includes("\u9879\u76ee\u5217\u8868\u5df2\u6536\u8d77")) issues.push("project panel should not be collapsed before project selection");
  if (!state.projectSearchVisible) issues.push("project search should be visible in project management");
  if (state.projectSelectCount > 35) issues.push(`compatibility project select should stay bounded, got ${state.projectSelectCount} options`);
  if (!state.projectFilterSummary.includes("/") || !state.projectFilterSummary.includes("\u9879\u76ee")) issues.push("project filter summary should explain bounded project scope");
  if (!state.dataRowsHidden) issues.push("data table should stay hidden before project selection");
  if (!state.dataEmptyVisible) issues.push("data empty state should be visible before project selection");
  if (state.dataActionsDisplay !== "none") issues.push("data action bar should be hidden before project selection");
  if (state.badVisibleMarkers.length) issues.push(`bad visible markers: ${state.badVisibleMarkers.join(", ")}`);
  if (state.horizontalOverflow) issues.push("horizontal overflow detected");
  return issues;
}

function checkSelectedProject(state) {
  const issues = [];
  if (!state.selectedProject) issues.push("project should be selected");
  if (!state.projectRowsText.includes("当前项目")) issues.push("selected project summary should be visible");
  if (state.dataRowsHidden) issues.push("data rows should expand after project selection");
  if (state.dataEmptyVisible) issues.push("data empty prompt should hide after project selection");
  if (!state.dataPanelText.includes("当前项目")) issues.push("data panel should explain the selected project's data scope");
  if (state.visibleScopedDataActions.length) issues.push(`file-scoped actions should stay hidden until file selection: ${state.visibleScopedDataActions.join(", ")}`);
  if (state.badVisibleMarkers.length) issues.push(`bad visible markers: ${state.badVisibleMarkers.join(", ")}`);
  if (state.horizontalOverflow) issues.push("horizontal overflow detected");
  return issues;
}

async function run() {
  ensureDir();
  const browser = await chromium.launch();
  const report = {
    requirement_id: "QLANALYSER_PROJECT_DATA_UI_CODE_VISUAL_GATE",
    review_owner_model: "GPT-5.5/Codex",
    why_not_mini: "UI product experience verdict requires code-level and visual judgment; this script only collects deterministic evidence.",
    frontendUrl: FRONTEND_URL,
    defaultTestAccount: {
      account: CUSTOMER_EMAIL,
      passwordOrLogin: CUSTOMER_PASSWORD,
      scope: "demo customer, low privilege, local review only",
      credential_safety: "demo_only / low_privilege / rotatable / no_production_secret",
    },
    generatedAt: new Date().toISOString(),
    status: "running",
    states: [],
    screenshots: [],
    issues: [],
  };
  try {
    const desktop = await browser.newPage({ viewport: { width: 1366, height: 900 }, deviceScaleFactor: 1 });
    await login(desktop);
    const desktopNoSelection = await collectState(desktop, "desktop_no_project_selected");
    desktopNoSelection.screenshot = await screenshot(desktop, "desktop-no-project-selected");
    desktopNoSelection.issues = checkNoSelection(desktopNoSelection);
    report.states.push(desktopNoSelection);
    report.screenshots.push(desktopNoSelection.screenshot);

    if (desktopNoSelection.projectSearchVisible) {
      await desktop.fill("#workspaceProjectSearch", "Persistence");
      await desktop.waitForTimeout(600);
      const desktopSearch = await collectState(desktop, "desktop_project_search");
      desktopSearch.screenshot = await screenshot(desktop, "desktop-project-search");
      desktopSearch.issues = [];
      if (desktopSearch.projectSelectCount < 2) desktopSearch.issues.push("project search should reveal matching historical projects");
      if (!desktopSearch.projectFilterSummary.includes("搜索")) desktopSearch.issues.push("project search summary should indicate search mode");
      if (desktopSearch.projectSelectCount > 81) desktopSearch.issues.push(`project search result should stay bounded, got ${desktopSearch.projectSelectCount} options`);
      report.states.push(desktopSearch);
      report.screenshots.push(desktopSearch.screenshot);
      await desktop.fill("#workspaceProjectSearch", "");
      await desktop.waitForTimeout(600);
    }

    const firstProject = await desktop.evaluate(() => document.querySelector("#iaProjectRows [data-project-select]")?.getAttribute("data-project-select") || "");
    if (!firstProject) {
      desktopNoSelection.issues.push("no selectable project row returned by UI");
    } else {
      await desktop.locator(`#iaProjectRows [data-project-select="${firstProject}"]`).click({ timeout: 10000 });
      await desktop.waitForTimeout(1500);
      const desktopSelected = await collectState(desktop, "desktop_project_selected");
      desktopSelected.screenshot = await screenshot(desktop, "desktop-project-selected");
      desktopSelected.issues = checkSelectedProject(desktopSelected);
      report.states.push(desktopSelected);
      report.screenshots.push(desktopSelected.screenshot);
    }
    await desktop.close();

    const narrow = await browser.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
    await login(narrow);
    const narrowNoSelection = await collectState(narrow, "narrow_no_project_selected");
    narrowNoSelection.screenshot = await screenshot(narrow, "narrow-no-project-selected");
    narrowNoSelection.issues = checkNoSelection(narrowNoSelection);
    report.states.push(narrowNoSelection);
    report.screenshots.push(narrowNoSelection.screenshot);
    await narrow.close();
  } finally {
    await browser.close();
  }

  report.issues = report.states.flatMap((state) => state.issues.map((issue) => ({ state: state.name, issue })));
  report.status = report.issues.length ? "failed" : "passed";
  fs.writeFileSync(EVIDENCE_PATH, `${JSON.stringify(report, null, 2)}\n`, "utf8");
  console.log(JSON.stringify(report, null, 2));
  if (report.status !== "passed") process.exit(1);
}

run().catch((error) => {
  ensureDir();
  const report = { status: "failed", error: error.message, stack: error.stack };
  fs.writeFileSync(EVIDENCE_PATH, `${JSON.stringify(report, null, 2)}\n`, "utf8");
  console.error(JSON.stringify(report, null, 2));
  process.exit(1);
});
