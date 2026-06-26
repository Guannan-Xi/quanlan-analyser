import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";

const require = createRequire(import.meta.url);
const { chromium } = require("../frontend/node_modules/playwright");

const TARGET_URL =
  process.env.QLANALYSER_FRONTEND_URL ||
  "http://127.0.0.1:4174/?customer_demo=login&api=http://127.0.0.1:8001/api";
const OUT_DIR =
  process.env.QLANALYSER_DATA_PREP_UX_EVIDENCE_DIR ||
  path.resolve("work/release_evidence/20260625-data-prep-ux-repair");
const EVIDENCE_PATH = path.join(OUT_DIR, "data_prep_ux_repair_browser.json");

function pass(name, details = {}) {
  return { name, pass: true, details };
}

function fail(name, details = {}) {
  return { name, pass: false, details };
}

async function visibleText(page) {
  return page.locator("body").innerText({ timeout: 10000 });
}

async function run() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const report = {
    script: path.basename(new URL(import.meta.url).pathname),
    target_url: TARGET_URL,
    checked_at: new Date().toISOString(),
    checks: [],
  };
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    const consoleErrors = [];
    page.on("console", (message) => {
      if (["error", "warning"].includes(message.type())) consoleErrors.push(message.text());
    });
    await page.goto(TARGET_URL, { waitUntil: "domcontentloaded", timeout: 30000 });
    await page.locator("#customerLoginBtn").click({ timeout: 15000 });
    await page.locator("#appShell").waitFor({ state: "visible", timeout: 15000 });
    const analysisNav = page.locator('button[data-view-jump="analysis"]:visible').first();
    if (await analysisNav.count()) {
      await analysisNav.click({ timeout: 15000 });
    } else {
      await page.locator("button").filter({ hasText: /数据准备|上传与预览/ }).first().click({ timeout: 15000 });
    }
    await page.locator('[data-testid="single-file-preview-panel"]').waitFor({ state: "visible", timeout: 15000 });

    const body = await visibleText(page);
    report.checks.push(
      body.includes("运行质控预览")
        ? fail("old-qc-preview-copy-not-visible", { found: "运行质控预览" })
        : pass("old-qc-preview-copy-not-visible"),
    );
    report.checks.push(
      body.includes("重新加载预览") ? pass("reload-preview-copy-visible") : fail("reload-preview-copy-visible"),
    );
    report.checks.push(
      body.includes("恢复坏道修改") ? pass("bad-channel-restore-visible") : fail("bad-channel-restore-visible"),
    );
    report.checks.push(
      body.includes("恢复片段") ? pass("segment-restore-visible") : fail("segment-restore-visible"),
    );

    const previewPanel = page.locator('[data-testid="single-file-preview-panel"]');
    const previewWorkbenchCount = await previewPanel.locator('[data-testid="preview-edit-workbench"]').count();
    report.checks.push(
      previewWorkbenchCount > 0
        ? pass("preview-edit-workbench-is-inside-preview-panel")
        : fail("preview-edit-workbench-is-inside-preview-panel"),
    );

    const screenshotPath = path.join(OUT_DIR, "data_prep_ux_repair_browser.png");
    await page.screenshot({ path: screenshotPath, fullPage: true });
    report.screenshot = screenshotPath;
    report.console_errors = consoleErrors;
    report.passed = report.checks.every((item) => item.pass);
    fs.writeFileSync(EVIDENCE_PATH, `${JSON.stringify(report, null, 2)}\n`, "utf8");
    console.log(JSON.stringify(report, null, 2));
    if (!report.passed) process.exit(1);
  } finally {
    await browser.close();
  }
}

run().catch((error) => {
  console.error(error.stack || error.message);
  process.exit(1);
});
