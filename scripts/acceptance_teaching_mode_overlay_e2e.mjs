import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";

const require = createRequire(import.meta.url);
const { chromium } = require("../frontend/node_modules/playwright");

const API_BASE = process.env.QLANALYSER_API_BASE_URL || "http://127.0.0.1:8001/api";
const FRONTEND_URL =
  process.env.QLANALYSER_FRONTEND_URL ||
  `http://127.0.0.1:4174/?customer_demo=auto&api=${encodeURIComponent(API_BASE)}`;
const EVIDENCE_ROOT =
  process.env.QLANALYSER_TEACHING_MODE_EVIDENCE_ROOT ||
  path.resolve("work/release_evidence/07-full-product-e2e-pdca/12_current_modules_teaching_mode/07_ui_browser");
const SCREENSHOT_DIR = path.join(EVIDENCE_ROOT, "screenshots");
const EVIDENCE_PATH = path.join(EVIDENCE_ROOT, "teaching_mode_overlay_e2e.json");

function ensureDirs() {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

function localBrowserExecutable() {
  const candidates = [
    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  ];
  return candidates.find((candidate) => fs.existsSync(candidate)) || null;
}

async function textOf(page, selector) {
  return (await page.locator(selector).first().textContent().catch(() => ""))?.trim() || "";
}

async function visible(page, selector) {
  return page.locator(selector).first().isVisible().catch(() => false);
}

async function main() {
  ensureDirs();
  const executablePath = localBrowserExecutable();
  const browser = await chromium.launch({ headless: true, ...(executablePath ? { executablePath } : {}) });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const checks = [];
  const screenshots = [];
  const add = (name, pass, details = {}) => checks.push({ name, pass: Boolean(pass), details });
  try {
    await page.goto(FRONTEND_URL, { waitUntil: "domcontentloaded", timeout: 60000 });
    await page.waitForSelector("#appShell, #loginScreen", { timeout: 30000 });
    if (await visible(page, "#customerLoginBtn")) {
      await page.click("#customerLoginBtn");
    }
    await page.waitForSelector("#appShell:not([hidden]), .main", { timeout: 30000 });
    await page.waitForSelector("#teachingModeBtn", { timeout: 30000 });

    add("teaching_button_visible", await visible(page, "#teachingModeBtn"));
    add("personal_center_nav_visible", await visible(page, '[data-view="userCenter"]'));

    const initialShot = path.join(SCREENSHOT_DIR, "teaching-00-project-management.png");
    await page.screenshot({ path: initialShot, fullPage: true });
    screenshots.push(initialShot);

    await page.click("#teachingModeBtn");
    await page.waitForSelector("#teachingOverlay.active", { timeout: 30000 });
    await page.waitForSelector(".teaching-spotlight", { timeout: 30000 });
    add("overlay_visible", await visible(page, "#teachingOverlay.active"));
    add("spotlight_visible", await visible(page, ".teaching-spotlight"));
    add("teaching_boundary_visible", (await textOf(page, ".teaching-boundary")).includes("合成 EEG"));
    add("first_step_title", (await textOf(page, "#teachingStepTitle")).includes("1/8"));

    const step1Shot = path.join(SCREENSHOT_DIR, "teaching-01-overlay-start.png");
    await page.screenshot({ path: step1Shot, fullPage: true });
    screenshots.push(step1Shot);

    const stepTitles = [];
    for (let i = 0; i < 7; i += 1) {
      const title = await textOf(page, "#teachingStepTitle");
      stepTitles.push(title);
      await page.click('[data-teaching-action="next"].primary-btn');
      await page.waitForTimeout(500);
    }
    stepTitles.push(await textOf(page, "#teachingStepTitle"));
    add("step_count_reaches_8", stepTitles.some((title) => title.includes("8/8")), { stepTitles });
    add("analysis_methods_step_seen", stepTitles.some((title) => title.includes("7/8")), { stepTitles });

    const finalShot = path.join(SCREENSHOT_DIR, "teaching-08-result-step.png");
    await page.screenshot({ path: finalShot, fullPage: true });
    screenshots.push(finalShot);

    await page.click('[data-teaching-action="close"]');
    await page.waitForTimeout(300);
    add("overlay_closes", !(await visible(page, "#teachingOverlay.active")));
    await page.click('[data-view="userCenter"]');
    await page.waitForSelector("#userCenter.active, #userCenter .panel", { timeout: 10000 });
    add("personal_center_reachable_after_teaching", await visible(page, "#userCenter"));

    const bodyText = await page.locator("body").innerText();
    for (const forbidden of ["预览方法", "可试用", "需复核", "Reference / CSD"]) {
      add(`forbidden_text_absent:${forbidden}`, !bodyText.includes(forbidden));
    }
  } catch (error) {
    add("unexpected_error", false, { message: error.message || String(error) });
  } finally {
    await browser.close();
  }

  const report = {
    script: path.basename(new URL(import.meta.url).pathname),
    frontend_url: FRONTEND_URL,
    api_base: API_BASE,
    generated_at: new Date().toISOString(),
    requirements: ["R-NAV-01", "R-NAV-02", "R-TEACH-01", "R-TEACH-02", "R-TEACH-03", "R-TEACH-04"],
    checks,
    screenshots,
    passed: checks.every((item) => item.pass),
  };
  fs.writeFileSync(EVIDENCE_PATH, `${JSON.stringify(report, null, 2)}\n`, "utf8");
  console.log(JSON.stringify(report, null, 2));
  process.exit(report.passed ? 0 : 1);
}

main();
