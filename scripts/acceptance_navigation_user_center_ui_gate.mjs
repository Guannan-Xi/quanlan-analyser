import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";

const require = createRequire(import.meta.url);
const { chromium } = require("../frontend/node_modules/playwright");

const FRONTEND_URL = process.env.QLANALYSER_FRONTEND_URL || "http://127.0.0.1:4174/index.html?customer_demo=auto&api=http%3A%2F%2F127.0.0.1%3A8001%2Fapi";
const OUT_DIR = process.env.QLANALYSER_NAV_USER_CENTER_GATE_DIR || path.resolve("work/release_evidence/ui_interaction_review/navigation_user_center_gate");
const EVIDENCE_PATH = path.join(OUT_DIR, "navigation_user_center_gate.json");
const CUSTOMER_EMAIL = process.env.QLANALYSER_DEMO_EMAIL || "demo.customer@quanlan.cn";
const CUSTOMER_PASSWORD = process.env.QLANALYSER_DEMO_PASSWORD || "demo123456";

const expectedCustomerNav = [
  "项目管理",
  "数据管理",
  "数据准备",
  "分析任务",
  "结果查看",
  "报告交付",
  "评审验证",
  "个人中心",
];

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
  "方法工作台",
  "科研级别流程",
];

const financeTerms = ["充值", "发票", "余额"];
const userCenterRequiredTerms = ["账户", "余额", "充值", "发票", "安全", "通知", "设置"];

function ensureDir() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
}

async function screenshot(page, name) {
  const target = path.join(OUT_DIR, `${name}.png`);
  await page.screenshot({ path: target, fullPage: true });
  return target;
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
}

async function visibleText(page, selector) {
  return page.locator(selector).evaluateAll((nodes) =>
    nodes
      .filter((node) => {
        const style = window.getComputedStyle(node);
        const rect = node.getBoundingClientRect();
        return style.visibility !== "hidden" && style.display !== "none" && rect.width > 0 && rect.height > 0;
      })
      .map((node) => node.innerText || node.textContent || "")
      .join("\n")
  );
}

function pushIf(condition, issues, message, details = {}) {
  if (condition) issues.push({ message, details });
}

async function collectState(page, name, selector = "body") {
  const text = await visibleText(page, selector);
  const issues = [];
  const markerHits = forbiddenVisibleMarkers.filter((marker) => text.includes(marker));
  pushIf(markerHits.length > 0, issues, "visible stale/internal/corrupt marker found", { markerHits });
  return { name, textLength: text.length, markerHits, issues };
}

async function run() {
  ensureDir();
  const report = {
    status: "running",
    url: FRONTEND_URL,
    evidence_path: EVIDENCE_PATH,
    screenshots: [],
    states: [],
    checks: {},
    issues: [],
  };

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 980 } });

  try {
    await loginIfNeeded(page);
    await page.waitForSelector(".sidebar .nav-item[data-role='customer']", { timeout: 15000 });

    const navLabels = await page.locator(".sidebar .nav-item[data-role='customer']").evaluateAll((nodes) =>
      nodes
        .filter((node) => {
          const style = window.getComputedStyle(node);
          const rect = node.getBoundingClientRect();
          return style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0;
        })
        .map((node) => node.innerText.trim().replace(/\s+/g, " "))
    );
    report.checks.navLabels = navLabels;
    pushIf(JSON.stringify(navLabels) !== JSON.stringify(expectedCustomerNav), report.issues, "customer nav order/labels mismatch", {
      expected: expectedCustomerNav,
      actual: navLabels,
    });

    const navText = await visibleText(page, ".sidebar .nav");
    const navFinanceHits = financeTerms.filter((term) => navText.includes(term));
    pushIf(navFinanceHits.length > 0, report.issues, "customer main nav exposes finance terms", { navFinanceHits });

    const accountPanelText = await visibleText(page, ".account-panel");
    report.checks.accountPanelText = accountPanelText;
    pushIf(!accountPanelText.includes("个人中心"), report.issues, "sidebar account panel is not clearly a user-center entry");

    report.screenshots.push(await screenshot(page, "default_workspace"));
    report.states.push(await collectState(page, "default_workspace", "#appShell"));

    await page.locator('[data-view="storage"]').click();
    await page.waitForSelector("#storage.view.active", { timeout: 10000 });
    report.screenshots.push(await screenshot(page, "storage_data_management"));
    const storageState = await collectState(page, "storage_data_management", "#storage");
    const storageText = await visibleText(page, "#storage");
    const storageFinanceHits = financeTerms.filter((term) => storageText.includes(term));
    pushIf(storageFinanceHits.length > 0, storageState.issues, "storage/data management page exposes finance terms", { storageFinanceHits });
    report.states.push(storageState);

    await page.locator('[data-view="userCenter"]').click();
    await page.waitForSelector("#userCenter.view.active", { timeout: 10000 });
    report.screenshots.push(await screenshot(page, "user_center"));
    const userCenterState = await collectState(page, "user_center", "#userCenter");
    const userCenterText = await visibleText(page, "#userCenter");
    const missingUserCenterTerms = userCenterRequiredTerms.filter((term) => !userCenterText.includes(term));
    pushIf(missingUserCenterTerms.length > 0, userCenterState.issues, "user center is missing required account/finance/settings surfaces", {
      missingUserCenterTerms,
    });
    report.states.push(userCenterState);

    const workflowSelectors = ["#dashboard", "#storage", "#analysis", "#workflow", "#statistics", "#publication", "#journey"];
    for (const selector of workflowSelectors) {
      const text = await page.locator(selector).evaluate((node) => node.innerText || node.textContent || "");
      const financeHits = selector === "#storage" ? [] : financeTerms.filter((term) => text.includes(term));
      if (financeHits.length && selector !== "#userCenter") {
        report.issues.push({ message: "customer workflow page exposes finance terms outside user center", details: { selector, financeHits } });
      }
    }

    report.issues.push(...report.states.flatMap((state) => state.issues.map((issue) => ({ state: state.name, ...issue }))));
    report.status = report.issues.length ? "failed" : "passed";
  } finally {
    await browser.close();
  }

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
