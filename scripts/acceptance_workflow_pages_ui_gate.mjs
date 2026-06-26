import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";

const require = createRequire(import.meta.url);
const { chromium } = require("../frontend/node_modules/playwright");

const FRONTEND_URL = process.env.QLANALYSER_FRONTEND_URL || "http://127.0.0.1:4174/index.html?customer_demo=auto&api=http%3A%2F%2F127.0.0.1%3A8001%2Fapi";
const OUT_DIR = process.env.QLANALYSER_WORKFLOW_PAGES_UI_GATE_DIR || path.resolve("work/release_evidence/ui_interaction_review/workflow_pages_gate");
const EVIDENCE_PATH = path.join(OUT_DIR, "workflow_pages_ui_gate.json");
const CUSTOMER_EMAIL = process.env.QLANALYSER_DEMO_EMAIL || "demo.customer@quanlan.cn";
const CUSTOMER_PASSWORD = process.env.QLANALYSER_DEMO_PASSWORD || "demo123456";

const forbiddenVisibleMarkers = [
  "\uFFFD",
  "acceptance-label",
  "persistent-label",
  "Persistence Gate",
  "Acceptance project",
  "task_id",
  "Online data management",
  "Raw data, derived files",
  "raw/sub-001.edf",
  "derivatives/erp.csv",
  "figures/main.png",
  "Help and account recovery",
  "Upload help",
  "\u65b9\u6cd5\u5de5\u4f5c\u53f0",
  "\u79d1\u7814\u7ea7\u522b\u6d41\u7a0b",
];

const mojibakeRegex = new RegExp("[\\uFFFD]|(\\u95c1|\\u95bb|\\u95b8|\\u95bf|\\u7019\\u6b4c\\u5c19|\\u7027\\u677f\\u61d0|\\u9435\\u56e7\\u5632|\\u95ba\\u4f7a\\u5897|\\u599e\\u3085\\u6e71|\\u5a34\\u7286)");
const financeTerms = ["\u5145\u503c", "\u53d1\u7968", "\u4f59\u989d"];

const workflowPages = [
  {
    view: "analysis",
    name: "data_preparation",
    selector: "#analysis",
    requiredSelectors: ["#prepDataQueue", "[data-testid='preview-edit-workbench']", "[data-real-action='confirm-plan-inline']", "[data-real-action='save-epoch-set']"],
    requiredActions: ["confirm-plan-inline", "save-epoch-set"],
  },
  {
    view: "workflow",
    name: "analysis_tasks",
    selector: "#workflow",
    requiredSelectors: ["[data-real-action='run-psd']", "[data-real-action='run-erp']", "[data-real-action='run-tfr']", "[data-real-action='run-pac']"],
    requiredActions: ["run-psd", "run-erp", "run-tfr", "run-pac"],
  },
  {
    view: "statistics",
    name: "results_review",
    selector: "#statistics",
    requiredSelectors: ["[data-testid='results-review-workbench']"],
    requiredActions: [],
  },
  {
    view: "publication",
    name: "report_delivery",
    selector: "#publication",
    requiredSelectors: ["[data-real-action='create-report']"],
    requiredActions: ["create-report"],
  },
  {
    view: "userCenter",
    name: "user_center",
    selector: "#userCenter",
    requiredSelectors: ["#invoiceBtn", "#rechargeBtn"],
    requiredActions: [],
    allowFinanceTerms: true,
  },
];

function ensureDir() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
}

async function screenshot(page, name) {
  const target = path.join(OUT_DIR, `${name}.png`);
  await page.screenshot({ path: target, fullPage: true });
  return target;
}

function pushIf(condition, issues, message, details = {}) {
  if (condition) issues.push({ message, details });
}

async function loginIfNeeded(page) {
  await page.addInitScript(() => {
    localStorage.removeItem("qlanalyser_auth_session");
    sessionStorage.removeItem("qlanalyser_auth_session");
  });
  await page.goto(FRONTEND_URL, { waitUntil: "domcontentloaded", timeout: 20000 });
  const appVisible = await page.locator("#appShell:not([hidden])").isVisible().catch(() => false);
  if (appVisible) return;
  await page.waitForSelector("#customerLoginForm", { state: "visible", timeout: 15000 });
  await page.fill("#customerEmail", CUSTOMER_EMAIL);
  await page.fill("#customerPassword", CUSTOMER_PASSWORD);
  await Promise.all([
    page.waitForSelector("#appShell:not([hidden])", { timeout: 20000 }),
    page.locator("#customerLoginBtn").click(),
  ]);
  await page.waitForTimeout(1000);
}

async function selectFirstProject(page) {
  await page.locator('[data-view="dashboard"]').click();
  await page.waitForSelector("#dashboard.view.active", { timeout: 10000 });
  const firstProject = page.locator("#iaProjectRows [data-project-select]").first();
  if (await firstProject.isVisible().catch(() => false)) {
    await firstProject.click();
    await page.waitForTimeout(700);
    return true;
  }
  return false;
}

async function collectPageState(page, config, screenshotPrefix = "") {
  await page.locator(`[data-view="${config.view}"]`).click();
  await page.waitForSelector(`${config.selector}.view.active`, { timeout: 12000 });
  await page.waitForTimeout(500);
  const screenshotPath = await screenshot(page, `${screenshotPrefix}${config.name}`);
  const state = await page.evaluate(({ config, forbiddenVisibleMarkers, financeTerms }) => {
    const root = document.querySelector(config.selector);
    const text = root?.innerText || "";
    const visible = (node) => {
      if (!node || node.hidden) return false;
      const style = getComputedStyle(node);
      const rect = node.getBoundingClientRect();
      return style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0;
    };
    const actionStates = config.requiredActions.map((action) => {
      const nodes = Array.from(root?.querySelectorAll(`[data-real-action="${action}"]`) || []);
      return {
        action,
        count: nodes.length,
        visibleCount: nodes.filter(visible).length,
        disabledCount: nodes.filter((node) => node.disabled || node.getAttribute("aria-disabled") === "true").length,
        disabledReasons: nodes
          .filter((node) => node.disabled || node.getAttribute("aria-disabled") === "true")
          .map((node) => node.getAttribute("title") || node.getAttribute("aria-label") || node.innerText || "")
          .filter(Boolean),
      };
    });
    const selectorStates = config.requiredSelectors.map((selector) => {
      const nodes = Array.from(root?.querySelectorAll(selector) || []);
      return { selector, count: nodes.length, visibleCount: nodes.filter(visible).length };
    });
    const rootRect = root?.getBoundingClientRect();
    const visiblePanelCount = Array.from(root?.querySelectorAll(".panel") || []).filter(visible).length;
    const visibleButtonCount = Array.from(root?.querySelectorAll("button") || []).filter(visible).length;
    const financeHits = financeTerms.filter((term) => text.includes(term));
    return {
      view: config.view,
      name: config.name,
      textLength: text.length,
      selectorStates,
      forbiddenHits: forbiddenVisibleMarkers.filter((term) => text.includes(term)),
      mojibakeHit: new RegExp("[\\uFFFD]|(\\u95c1|\\u95bb|\\u95b8|\\u95bf|\\u7019\\u6b4c\\u5c19|\\u7027\\u677f\\u61d0|\\u9435\\u56e7\\u5632|\\u95ba\\u4f7a\\u5897|\\u599e\\u3085\\u6e71|\\u5a34\\u7286)").test(text),
      financeHits,
      actionStates,
      visiblePanelCount,
      visibleButtonCount,
      rootRect: rootRect ? { width: Math.round(rootRect.width), height: Math.round(rootRect.height) } : null,
      horizontalOverflow: document.documentElement.scrollWidth > window.innerWidth + 2,
      viewport: { width: window.innerWidth, height: window.innerHeight, scrollWidth: document.documentElement.scrollWidth },
    };
  }, { config, forbiddenVisibleMarkers, financeTerms });

  state.screenshot = screenshotPath;
  state.issues = [];
  const missingSelectors = state.selectorStates.filter((selector) => selector.visibleCount < 1);
  pushIf(missingSelectors.length > 0, state.issues, "required product selector not visible", { missingSelectors });
  pushIf(state.forbiddenHits.length > 0, state.issues, "forbidden stale/internal visible marker", { forbiddenHits: state.forbiddenHits });
  pushIf(state.mojibakeHit, state.issues, "visible mojibake radar hit", {});
  pushIf(state.horizontalOverflow, state.issues, "page has horizontal overflow", state.viewport);
  pushIf(state.visiblePanelCount < 1, state.issues, "page has no visible product panel", { visiblePanelCount: state.visiblePanelCount });
  pushIf(state.textLength < 30, state.issues, "page appears blank or under-informative", { textLength: state.textLength });
  pushIf(!config.allowFinanceTerms && state.financeHits.length > 0, state.issues, "workflow page exposes finance terms outside user center", { financeHits: state.financeHits });
  for (const action of state.actionStates) {
    pushIf(action.visibleCount < 1, state.issues, "required action not visible", { action: action.action });
    pushIf(action.disabledCount > 0 && action.disabledReasons.length < action.disabledCount, state.issues, "disabled action lacks a user-facing reason", action);
  }
  return state;
}

async function run() {
  ensureDir();
  const report = {
    requirement_id: "QLANALYSER_WORKFLOW_PAGES_UI_GATE",
    review_owner_model: "GPT-5.5/Codex",
    why_not_mini: "Workflow UX verdict and product-scope acceptance require GPT-5.5/Codex; script only collects deterministic UI evidence.",
    frontendUrl: FRONTEND_URL,
    evidence_path: EVIDENCE_PATH,
    defaultTestAccount: {
      account: CUSTOMER_EMAIL,
      passwordOrLogin: CUSTOMER_PASSWORD,
      scope: "demo customer, low privilege, local review only",
      credential_safety: "demo_only / low_privilege / rotatable / no_production_secret",
    },
    generatedAt: new Date().toISOString(),
    states: [],
    screenshots: [],
  };

  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 920 } });
    await loginIfNeeded(page);
    report.projectSelected = await selectFirstProject(page);

    for (const config of workflowPages) {
      const state = await collectPageState(page, config);
      report.states.push(state);
      report.screenshots.push(state.screenshot);
    }

    const narrow = await browser.newPage({ viewport: { width: 390, height: 844 } });
    await loginIfNeeded(narrow);
    await selectFirstProject(narrow);
    const narrowState = await collectPageState(narrow, workflowPages[0], "narrow_");
    narrowState.name = "narrow_data_preparation";
    report.states.push(narrowState);
    report.screenshots.push(narrowState.screenshot);
  } finally {
    await browser.close();
  }

  report.issues = report.states.flatMap((state) => state.issues.map((issue) => ({ state: state.name, ...issue })));
  report.status = report.issues.length ? "failed" : "passed";
  fs.writeFileSync(EVIDENCE_PATH, `${JSON.stringify(report, null, 2)}\n`, "utf8");
  console.log(JSON.stringify(report, null, 2));
  if (report.status !== "passed") process.exit(1);
}

run().catch((error) => {
  ensureDir();
  const report = { status: "failed", error: error.message, stack: error.stack, evidence_path: EVIDENCE_PATH };
  fs.writeFileSync(EVIDENCE_PATH, `${JSON.stringify(report, null, 2)}\n`, "utf8");
  console.error(JSON.stringify(report, null, 2));
  process.exit(1);
});
