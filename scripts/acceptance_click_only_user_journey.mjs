import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const { chromium } = require("../frontend/node_modules/playwright");
import fs from "node:fs";
import path from "node:path";

const FRONTEND_URL = process.env.QLANALYSER_CLICK_FRONTEND_URL || "http://39.97.248.225/?api=http://39.97.248.225/api";
const SAMPLE_FIF = process.env.QLANALYSER_UI_SAMPLE || path.resolve("work/acceptance/ui_with_events_raw.fif");
const OUT_DIR = process.env.QLANALYSER_CLICK_EVIDENCE_DIR || path.resolve("work/release_evidence/20260621-click-only-user-journey");
const EVIDENCE_PATH = path.join(OUT_DIR, "click_only_user_journey.json");

const MOJIBAKE_RE = /[\uFFFD]|锟|鏂|绠|鐢|杩|妯|欏|鍙|浠|诲|璐|戜|娉|嗗|叆|涓|彂|犳/;

function ensureDir() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
}

function shotPath(name) {
  return path.join(OUT_DIR, `${name}.png`);
}

async function screenshot(page, name) {
  const target = shotPath(name);
  await page.screenshot({ path: target, fullPage: true, timeout: 10000 }).catch(async () => {
    await page.locator("body").screenshot({ path: target, timeout: 10000 });
  });
  return target;
}

async function visibleText(page) {
  return (await page.locator("body").innerText({ timeout: 10000 })).replace(/\s+/g, " ").trim();
}

async function safeClick(page, selector, label, timeout = 10000) {
  const locator = page.locator(selector).first();
  const visible = await locator.isVisible({ timeout }).catch(() => false);
  if (!visible) throw new Error(`${label} not visible: ${selector}`);
  await locator.click();
}

async function runCustomerJourney(browser, evidence) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, acceptDownloads: true });
  const requests = [];
  page.on("request", (request) => {
    const url = request.url();
    if (url.includes("/api/")) requests.push({ method: request.method(), url });
  });
  const result = {
    status: "failed",
    steps: [],
    requests,
    blockers: [],
    warnings: [],
    screenshots: {},
  };
  evidence.customer = result;
  try {
    await page.goto(FRONTEND_URL, { waitUntil: "domcontentloaded" });
    result.screenshots.login = await screenshot(page, "customer-login");
    let text = await visibleText(page);
    result.initialMojibake = MOJIBAKE_RE.test(text);
    if (result.initialMojibake) result.blockers.push("Visible login/workflow text contains mojibake.");

    await page.locator("#customerEmail").fill("demo.customer@quanlan.cn");
    await page.locator("#customerPassword").fill("demo123456");
    await safeClick(page, "#customerLoginForm button[type='submit']", "customer login submit");
    await page.waitForSelector("#appShell:not([hidden])", { timeout: 15000 });
    result.steps.push("logged_in_by_form_click");
    result.screenshots.dashboard = await screenshot(page, "customer-dashboard");

    await safeClick(page, 'button[data-view="billing"]', "billing nav");
    result.steps.push("opened_billing_by_nav_click");
    result.screenshots.billing = await screenshot(page, "customer-billing");
    await safeClick(page, "#rechargeBtn", "sandbox recharge button");
    result.steps.push("clicked_sandbox_recharge");

    await safeClick(page, 'button[data-view="invoice"]', "invoice nav");
    result.steps.push("opened_invoice_by_nav_click");
    result.screenshots.invoice = await screenshot(page, "customer-invoice");
    await safeClick(page, "#invoiceBtn", "invoice submit button");
    result.steps.push("submitted_invoice_by_click");

    await safeClick(page, 'button[data-view="inbox"]', "inbox nav");
    result.steps.push("opened_inbox_by_nav_click");
    result.screenshots.inbox = await screenshot(page, "customer-inbox");

    await safeClick(page, 'button[data-view="dashboard"]', "dashboard nav");
    await safeClick(page, '[data-real-action="create-project"]', "create project");
    result.steps.push("created_project_by_click");
    if (!fs.existsSync(SAMPLE_FIF)) throw new Error(`Sample FIF missing: ${SAMPLE_FIF}`);
    await page.setInputFiles("#real-eeg-file", SAMPLE_FIF);
    result.steps.push("selected_eeg_file_by_file_input");
    await safeClick(page, '[data-real-action="upload-eeg"]', "upload EEG");
    result.steps.push("uploaded_eeg_by_click");
    await safeClick(page, '[data-real-action="run-qc"]', "run QC", 20000);
    result.steps.push("ran_qc_by_click");
    await safeClick(page, '[data-real-action="run-psd"]', "run PSD", 20000);
    result.steps.push("ran_psd_by_click");
    await page.waitForFunction(() => !document.querySelector('[data-real-action="create-report"]')?.disabled, null, { timeout: 30000 }).catch(() => {});
    await safeClick(page, '[data-real-action="run-erp"]', "run ERP", 20000);
    result.steps.push("ran_erp_by_click");
    await page.waitForFunction(() => !document.querySelector('[data-real-action="create-report"]')?.disabled, null, { timeout: 30000 }).catch(() => {});
    const reportButtonEnabled = await page.locator('[data-real-action="create-report"]').isEnabled().catch(() => false);
    if (reportButtonEnabled) {
      await safeClick(page, '[data-real-action="create-report"]', "create report", 20000);
      result.steps.push("created_report_by_click");
    } else {
      result.blockers.push("Create report button was not enabled after clicked analysis tasks.");
    }
    result.screenshots.afterAnalysis = await screenshot(page, "customer-after-analysis");
    const downloadSelector = 'button[data-report-download], a[href*="/reports/"], a[href*="/artifacts/"], a[download]';
    const reportDownloadButton = page.locator("button[data-report-download]").first();
    await reportDownloadButton.waitFor({ state: "visible", timeout: 15000 }).catch(() => {});
    result.reportDownloadButtonCount = await page.locator("button[data-report-download]").count();
    result.downloadLinks = await page.locator(downloadSelector).count();
    const downloadLink = reportDownloadButton;
    if (result.downloadLinks <= 0) {
      result.blockers.push("No visible report/artifact download links after analysis clicks.");
    } else if (result.reportDownloadButtonCount <= 0) {
      result.blockers.push("No visible primary report package download button after report creation.");
    } else {
      const download = await Promise.all([
        page.waitForEvent("download", { timeout: 15000 }),
        downloadLink.click(),
      ]).then(([download]) => download).catch((error) => {
        result.blockers.push(`Report download click did not produce a browser download: ${error.message}`);
        return null;
      });
      if (download) {
        const fileName = download.suggestedFilename();
        const target = path.join(OUT_DIR, fileName);
        await download.saveAs(target);
        result.downloadedReport = target;
        result.steps.push("downloaded_report_package_by_click");
      }
    }

    text = await visibleText(page);
    result.finalMojibake = MOJIBAKE_RE.test(text);
    if (result.finalMojibake) result.blockers.push("Visible post-login text contains mojibake.");
    result.status = result.blockers.length ? "failed" : "passed";
  } catch (error) {
    result.blockers.push(error.message);
    result.screenshots.error = await screenshot(page, "customer-error").catch(() => "");
  } finally {
    await page.close();
  }
}

async function runAdminDiscoverability(browser, evidence) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const result = {
    status: "failed",
    steps: [],
    blockers: [],
    screenshots: {},
  };
  evidence.admin = result;
  try {
    await page.goto(FRONTEND_URL, { waitUntil: "domcontentloaded" });
    result.screenshots.login = await screenshot(page, "admin-login-discovery");
    const visibleAdminEntryCount = await page.locator('button:visible, a:visible').evaluateAll((nodes) =>
      nodes.filter((node) => /运营|管理|Admin|admin|ops/i.test(node.innerText || node.getAttribute("aria-label") || "")).length
    );
    result.visibleAdminEntryCount = visibleAdminEntryCount;
    if (visibleAdminEntryCount <= 0) {
      result.blockers.push("No visible admin/ops entry on the default login screen.");
    }
    if (visibleAdminEntryCount > 0) {
      await page.locator('button:visible, a:visible').filter({ hasText: /运营|管理|Admin|admin|ops/i }).first().click();
      result.steps.push("clicked_visible_admin_entry");
      result.screenshots.adminForm = await screenshot(page, "admin-login-form");
    }
    const adminFormVisible = await page.locator("#adminLoginForm").isVisible().catch(() => false);
    result.adminFormVisible = adminFormVisible;
    if (!adminFormVisible) result.blockers.push("Admin login form is not discoverable by visible click path.");
    result.status = result.blockers.length ? "failed" : "passed";
  } catch (error) {
    result.blockers.push(error.message);
  } finally {
    await page.close();
  }
}

async function runRegisterCoverage(browser, evidence) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const result = { status: "failed", steps: [], blockers: [], screenshots: {} };
  evidence.register = result;
  try {
    await page.goto(FRONTEND_URL, { waitUntil: "domcontentloaded" });
    await safeClick(page, '[data-login-tab="customerRegister"]', "customer register tab");
    for (const mode of ["email", "phone", "wechat"]) {
      await page.locator(`input[name="registerMode"][value="${mode}"]`).check();
      await page.locator("#registerName").fill(`Click Tester ${mode}`);
      await page.locator("#registerOrg").fill("QLanalyser Test Lab");
      if (mode === "email") await page.locator("#registerEmail").fill(`click-${Date.now()}@example.com`);
      if (mode === "phone") await page.locator("#registerPhone").fill("13800000000");
      await safeClick(page, "#sendCodeBtn", `${mode} send code`);
      if (await page.locator("#registerCode").isVisible().catch(() => false)) {
        await page.locator("#registerCode").fill("123456");
      }
      if (await page.locator("#registerPassword").isVisible().catch(() => false)) {
        await page.locator("#registerPassword").fill("demo123456");
      }
      result.screenshots[`register-${mode}`] = await screenshot(page, `register-${mode}`);
      result.steps.push(`covered_register_${mode}`);
    }
    result.status = "passed";
  } catch (error) {
    result.blockers.push(error.message);
    result.screenshots.error = await screenshot(page, "register-error").catch(() => "");
  } finally {
    await page.close();
  }
}

async function runPageCoverage(browser, evidence) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const result = { status: "failed", customerPages: [], adminPages: [], externalPages: [], blockers: [], screenshots: {} };
  evidence.pageCoverage = result;
  let adminContext;
  let adminPage;
  try {
    await page.goto(FRONTEND_URL, { waitUntil: "domcontentloaded" });
    await page.locator("#customerEmail").fill("demo.customer@quanlan.cn");
    await page.locator("#customerPassword").fill("demo123456");
    await safeClick(page, "#customerLoginForm button[type='submit']", "customer login submit");
    await page.waitForSelector("#appShell:not([hidden])", { timeout: 15000 });
    for (const view of ["dashboard", "upload", "analysis", "workflow", "statistics", "publication", "billing", "invoice", "inbox", "storage"]) {
      await safeClick(page, `button[data-view="${view}"]`, `customer ${view} nav`);
      await page.waitForTimeout(300);
      result.screenshots[`customer-${view}`] = await screenshot(page, `coverage-customer-${view}`);
      result.customerPages.push(view);
    }

    adminContext = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    adminPage = await adminContext.newPage();
    await adminPage.goto(FRONTEND_URL, { waitUntil: "domcontentloaded" });
    await safeClick(adminPage, 'button[data-login-tab="adminLogin"]', "admin entry");
    await adminPage.locator("#adminEmail").fill("ops@quanlan.cn");
    await adminPage.locator("#adminPassword").fill("ops-demo-2026");
    await safeClick(adminPage, "#adminLoginForm button[type='submit']", "admin login submit");
    await adminPage.waitForSelector("#appShell:not([hidden])", { timeout: 15000 });
    for (const view of ["adminDashboard", "adminOperations", "adminFinance", "adminSystem"]) {
      await safeClick(adminPage, `button[data-view="${view}"]`, `admin ${view} nav`);
      await adminPage.waitForTimeout(500);
      result.screenshots[`admin-${view}`] = await screenshot(adminPage, `coverage-admin-${view}`);
      result.adminPages.push(view);
    }

    const base = new URL(FRONTEND_URL);
    for (const [name, pathname] of [["module-lab", "module-lab.html"], ["preset-analysis", "research-modules.html"]]) {
      const url = new URL(pathname, base);
      url.searchParams.set("api", base.searchParams.get("api") || "http://127.0.0.1:8001/api");
      await page.goto(url.toString(), { waitUntil: "domcontentloaded" });
      await page.waitForTimeout(1000);
      result.screenshots[name] = await screenshot(page, `coverage-${name}`);
      result.externalPages.push(name);
    }
    result.status = "passed";
  } catch (error) {
    result.blockers.push(error.message);
    result.screenshots.error = await screenshot(adminPage || page, "coverage-error").catch(() => "");
  } finally {
    if (adminContext) await adminContext.close().catch(() => {});
    await page.close();
  }
}

async function main() {
  ensureDir();
  const browser = await chromium.launch();
  const evidence = {
    status: "failed",
    policy: "Click-only user test: no direct backend API calls; browser clicks, inputs, uploads, and visible download links only.",
    frontendUrl: FRONTEND_URL,
    generatedAt: new Date().toISOString(),
  };
  try {
    await runCustomerJourney(browser, evidence);
    await runAdminDiscoverability(browser, evidence);
    await runRegisterCoverage(browser, evidence);
    await runPageCoverage(browser, evidence);
    evidence.status = [
      evidence.customer?.status,
      evidence.admin?.status,
      evidence.register?.status,
      evidence.pageCoverage?.status,
    ].every((status) => status === "passed") ? "passed" : "failed";
  } finally {
    await browser.close();
    fs.writeFileSync(EVIDENCE_PATH, `${JSON.stringify(evidence, null, 2)}\n`, "utf8");
  }
  console.log(JSON.stringify(evidence, null, 2));
  if (evidence.status !== "passed") process.exit(1);
}

main().catch((error) => {
  ensureDir();
  fs.writeFileSync(EVIDENCE_PATH, `${JSON.stringify({ status: "failed", error: error.message }, null, 2)}\n`, "utf8");
  console.error(error);
  process.exit(1);
});
