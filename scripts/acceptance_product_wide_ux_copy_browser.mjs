import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";

const require = createRequire(import.meta.url);
const { chromium } = require("../frontend/node_modules/playwright");

const TARGET_URL =
  process.env.QLANALYSER_FRONTEND_URL ||
  "http://127.0.0.1:4174/?customer_demo=login&api=http://127.0.0.1:8001/api";
const OUT_DIR =
  process.env.QLANALYSER_PRODUCT_UX_EVIDENCE_DIR ||
  path.resolve("work/release_evidence/20260625-product-wide-ux-copy");
const EVIDENCE_PATH = path.join(OUT_DIR, "product_wide_ux_copy_browser.json");

const checks = [];
const pass = (name, details = {}) => checks.push({ name, pass: true, details });
const fail = (name, details = {}) => checks.push({ name, pass: false, details });

async function bodyText(page) {
  return page.locator("body").innerText({ timeout: 10000 });
}

async function run() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    const consoleErrors = [];
    page.on("console", (message) => {
      if (message.type() === "error") consoleErrors.push(message.text());
    });
    await page.goto(TARGET_URL, { waitUntil: "domcontentloaded", timeout: 30000 });
    await page.locator("#customerLoginBtn").click({ timeout: 15000 });
    await page.locator("#appShell").waitFor({ state: "visible", timeout: 15000 });

    await page.locator('button[data-view="workflow"]:visible').click({ timeout: 15000 });
    const workflowText = await bodyText(page);
    ["开始 PSD 分析", "开始 ERP 分析", "开始 TFR 时频分析", "开始 PAC 耦合分析"].forEach((copy) => {
      workflowText.includes(copy) ? pass(`workflow-copy:${copy}`) : fail(`workflow-copy:${copy}`);
    });
    ["运行 PSD", "运行 ERP", "运行 TFR", "运行 PAC", "validator", "报告 ZIP"].forEach((copy) => {
      workflowText.includes(copy) ? fail(`workflow-banned:${copy}`) : pass(`workflow-banned:${copy}`);
    });
    const workflowScreenshot = path.join(OUT_DIR, "workflow_copy.png");
    await page.screenshot({ path: workflowScreenshot, fullPage: true });

    await page.locator('button[data-view="publication"]:visible').click({ timeout: 15000 });
    const publicationText = await bodyText(page);
    publicationText.includes("生成交付报告")
      ? pass("publication-copy:生成交付报告")
      : fail("publication-copy:生成交付报告");
    ["生成报告 ZIP", "下载报告 ZIP", "ZIP 下载"].forEach((copy) => {
      publicationText.includes(copy) ? fail(`publication-banned:${copy}`) : pass(`publication-banned:${copy}`);
    });
    const publicationScreenshot = path.join(OUT_DIR, "publication_copy.png");
    await page.screenshot({ path: publicationScreenshot, fullPage: true });

    const report = {
      script: path.basename(new URL(import.meta.url).pathname),
      target_url: TARGET_URL,
      checked_at: new Date().toISOString(),
      checks,
      screenshots: { workflow: workflowScreenshot, publication: publicationScreenshot },
      console_errors: consoleErrors,
      passed: checks.every((item) => item.pass) && consoleErrors.length === 0,
    };
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
