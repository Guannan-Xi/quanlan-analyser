import { createRequire } from "module";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const require = createRequire(import.meta.url);
const { chromium } = require("../frontend/node_modules/playwright");
const __dirname = path.dirname(fileURLToPath(import.meta.url));

const ROOT = path.resolve(__dirname, "..");
const OUT = path.join(ROOT, "work", "release_evidence", "20260621-ui-three-round-coverage");
const BASE = "http://127.0.0.1:4174/?api=http://127.0.0.1:8001/api";
const LAB = "http://127.0.0.1:4174/module-lab.html?api=http://127.0.0.1:8001/api";

fs.mkdirSync(OUT, { recursive: true });

const customerViews = [
  "dashboard",
  "upload",
  "analysis",
  "workflow",
  "statistics",
  "publication",
  "storage",
  "billing",
  "invoice",
  "inbox",
];

const adminViews = [
  "adminDashboard",
  "adminOperations",
  "adminFinance",
  "adminSystem",
];

function safeName(value) {
  return String(value).replace(/[^a-zA-Z0-9_-]+/g, "-").replace(/^-|-$/g, "");
}

async function screenshot(page, name) {
  const file = path.join(OUT, `${safeName(name)}.png`);
  await page.screenshot({ path: file, fullPage: true });
  return file;
}

async function pageMetrics(page) {
  return page.evaluate(() => {
    const visibleText = (el) => {
      const text = (el?.innerText || el?.textContent || "").replace(/\s+/g, " ").trim();
      return text.slice(0, 240);
    };
    const boxes = [...document.querySelectorAll("button, a, input, select, textarea")].filter((el) => {
      const r = el.getBoundingClientRect();
      return r.width > 0 && r.height > 0 && getComputedStyle(el).visibility !== "hidden";
    }).map((el) => {
      const r = el.getBoundingClientRect();
      return {
        tag: el.tagName.toLowerCase(),
        text: visibleText(el) || el.getAttribute("aria-label") || el.getAttribute("title") || el.getAttribute("placeholder") || "",
        x: Math.round(r.x),
        y: Math.round(r.y),
        w: Math.round(r.width),
        h: Math.round(r.height),
      };
    });
    const tooSmall = boxes.filter((b) => (b.tag === "button" || b.tag === "a") && (b.w < 32 || b.h < 32));
    const tables = [...document.querySelectorAll(".table-row.head, table thead, [role='table']")].length;
    const statusText = [...document.querySelectorAll(".warn,.ok,.error,.status,.notice,.demo-status,.segment-summary")]
      .map(visibleText)
      .filter(Boolean)
      .slice(0, 12);
    return {
      title: document.querySelector("#viewTitle")?.innerText?.trim() || document.title,
      scrollWidth: document.documentElement.scrollWidth,
      innerWidth: window.innerWidth,
      horizontalOverflow: document.documentElement.scrollWidth > window.innerWidth + 2,
      interactiveCount: boxes.length,
      tooSmall,
      tableLikeCount: tables,
      statusText,
      bodyText: document.body.innerText.replace(/\s+/g, " ").trim().slice(0, 800),
      mojibake: /\?\?\?\?|锟|�/.test(document.body.innerText),
    };
  });
}

async function closeModalIfOpen(page) {
  const close = page.locator("#modalCloseBtn");
  if (await close.isVisible().catch(() => false)) {
    await close.click().catch(() => {});
  }
}

async function tryClick(page, selector, label, result, options = {}) {
  const locator = page.locator(selector).first();
  const count = await locator.count().catch(() => 0);
  if (!count) {
    result.actions.push({ label, selector, status: options.allowMissing ? "expected_missing" : "missing" });
    return;
  }
  if (!(await locator.isVisible().catch(() => false))) {
    result.actions.push({ label, selector, status: options.allowMissing ? "expected_not_visible" : "not_visible" });
    return;
  }
  const disabled = await locator.isDisabled().catch(() => false);
  if (disabled && options.allowDisabled) {
    result.actions.push({ label, selector, status: "expected_disabled" });
    return;
  }
  if (disabled) {
    result.actions.push({ label, selector, status: "disabled" });
    return;
  }
  try {
    await locator.click({ timeout: 3500 });
    await page.waitForTimeout(250);
    result.actions.push({ label, selector, status: "clicked" });
    await closeModalIfOpen(page);
  } catch (error) {
    result.actions.push({ label, selector, status: "click_failed", error: error.message.split("\n")[0] });
  }
}

async function loginCustomer(page) {
  await page.goto(BASE, { waitUntil: "networkidle" });
  await page.fill("#customerEmail", "demo.customer@quanlan.cn");
  await page.fill("#customerPassword", "demo123456");
  await page.click("#customerLoginForm button[type='submit']");
  await page.waitForSelector("#appShell:not([hidden])", { timeout: 10000 });
}

async function loginAdmin(page) {
  await page.goto(BASE, { waitUntil: "networkidle" });
  await page.click(".admin-corner");
  await page.fill("#adminEmail", "ops@quanlan.cn");
  await page.fill("#adminPassword", "ops-demo-2026");
  await page.click("#adminLoginForm button[type='submit']");
  await page.waitForSelector("#appShell:not([hidden])", { timeout: 10000 });
}

async function visitView(page, view, round, role) {
  const result = { round, role, surface: view, actions: [] };
  await page.click(`[data-view="${view}"]`);
  await page.waitForTimeout(500);
  result.metrics = await pageMetrics(page);
  result.screenshot = await screenshot(page, `${role}-r${round}-${view}`);
  return result;
}

async function coverCustomer(page, round) {
  await loginCustomer(page);
  const results = [];
  for (const view of customerViews) {
    const result = await visitView(page, view, round, "customer");
    if (view === "dashboard") {
      await tryClick(page, '[data-real-action="create-project"]', "create project", result);
      await tryClick(page, '[data-real-action="run-qc"]', "run qc disabled or gated", result, { allowDisabled: true });
      await tryClick(page, '[data-view-jump="workflow"]', "jump workflow", result);
    }
    if (view === "upload") {
      await tryClick(page, "#uploadHelpBtn", "upload help", result);
    }
    if (view === "analysis") {
      await tryClick(page, '[data-real-action="confirm-plan-inline"], #confirmPlanBtn', "confirm plan if present", result, { allowMissing: true });
    }
    if (view === "workflow") {
      await tryClick(page, '[data-real-action="run-psd"], [data-real-action="run-psd-inline"]', "run psd if available", result, { allowMissing: true, allowDisabled: true });
      await tryClick(page, '[data-real-action="run-erp"], [data-real-action="run-erp-inline"]', "run erp if available", result, { allowMissing: true, allowDisabled: true });
    }
    if (view === "billing") {
      await tryClick(page, "#rechargeBtn", "sandbox recharge", result);
    }
    if (view === "invoice") {
      await tryClick(page, "#invoiceBtn", "submit invoice", result);
    }
    if (view === "inbox") {
      await tryClick(page, "#refreshInboxBtn", "refresh inbox", result);
    }
    results.push(result);
  }
  return results;
}

async function coverAdmin(page, round) {
  await loginAdmin(page);
  const results = [];
  for (const view of adminViews) {
    const result = await visitView(page, view, round, "admin");
    if (view === "adminFinance") {
      await tryClick(page, "[data-admin-issue-invoice]", "issue invoice if present", result, { allowMissing: true });
    }
    results.push(result);
  }
  return results;
}

async function coverLab(page, round) {
  await page.goto(LAB, { waitUntil: "networkidle" });
  const surfaces = [];
  const initial = { round, role: "lab", surface: "module-lab", actions: [] };
  initial.metrics = await pageMetrics(page);
  initial.screenshot = await screenshot(page, `lab-r${round}-overview`);
  await tryClick(page, "#labRefreshFiles", "refresh files", initial);
  await tryClick(page, "#labUploadButton", "upload selected file if provided", initial);
  surfaces.push(initial);

  const moduleIds = await page.$$eval("[data-module-card]", (nodes) => nodes.map((n) => n.getAttribute("data-module-card")));
  for (const id of moduleIds) {
    const result = { round, role: "lab", surface: `module-${id}`, actions: [] };
    await tryClick(page, `[data-module-card="${id}"] button`, `run or inspect ${id}`, result);
    result.metrics = await pageMetrics(page);
    result.screenshot = await screenshot(page, `lab-r${round}-module-${id}`);
    surfaces.push(result);
  }
  return surfaces;
}

(async () => {
  const browser = await chromium.launch();
  const all = [];
  for (let round = 1; round <= 3; round += 1) {
    const desktop = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
    all.push(...await coverCustomer(desktop, round));
    await desktop.close();

    const admin = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
    all.push(...await coverAdmin(admin, round));
    await admin.close();

    const lab = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
    all.push(...await coverLab(lab, round));
    await lab.close();
  }
  const acceptedActionStatuses = new Set(["clicked", "expected_disabled", "expected_missing", "expected_not_visible"]);
  const failedActions = all.flatMap((item) => item.actions.map((action) => ({ surface: item.surface, round: item.round, role: item.role, ...action }))).filter((a) => !acceptedActionStatuses.has(a.status));
  const visualRisks = all.filter((item) => item.metrics.horizontalOverflow || item.metrics.mojibake || item.metrics.tooSmall.length);
  const summary = {
    generatedAt: new Date().toISOString(),
    rounds: 3,
    surfaceCount: all.length,
    uniqueSurfaces: [...new Set(all.map((item) => `${item.role}:${item.surface}`))],
    failedActions,
    visualRisks: visualRisks.map((item) => ({
      round: item.round,
      role: item.role,
      surface: item.surface,
      horizontalOverflow: item.metrics.horizontalOverflow,
      mojibake: item.metrics.mojibake,
      tooSmall: item.metrics.tooSmall,
      screenshot: item.screenshot,
    })),
    pass: failedActions.length === 0 && visualRisks.length === 0,
    results: all,
  };
  fs.writeFileSync(path.join(OUT, "three_round_coverage.json"), JSON.stringify(summary, null, 2), "utf8");
  await browser.close();
  if (!summary.pass) process.exit(1);
})();
