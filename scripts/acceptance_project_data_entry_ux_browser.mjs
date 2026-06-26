import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";

const require = createRequire(import.meta.url);
const { chromium } = require("../frontend/node_modules/playwright");

const TARGET_URL =
  process.env.QLANALYSER_FRONTEND_URL ||
  "http://127.0.0.1:4174/?customer_demo=login&api=http://127.0.0.1:8001/api";
const OUT_DIR =
  process.env.QLANALYSER_PROJECT_DATA_UX_EVIDENCE_DIR ||
  path.resolve("work/release_evidence/20260625-project-data-entry-ux");
const EVIDENCE_PATH = path.join(OUT_DIR, "project_data_entry_ux_browser.json");

const checks = [];
const pass = (name, details = {}) => checks.push({ name, pass: true, details });
const fail = (name, details = {}) => checks.push({ name, pass: false, details });

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
    await page.locator('button[data-view="dashboard"]:visible').click({ timeout: 15000 });
    await page.locator('[data-testid="project-crud-panel"]').waitFor({ state: "visible", timeout: 15000 });

    const body = await page.locator("body").innerText({ timeout: 10000 });
    ["项目内数据", "显示归档项目"].forEach((copy) => {
      body.includes(copy) ? pass(`visible:${copy}`) : fail(`visible:${copy}`);
    });
    ["显示验收/归档项目", "评审验证", "评审门", "预处理入口", "已显示验收与归档记录"].forEach((copy) => {
      body.includes(copy) ? fail(`banned-visible:${copy}`) : pass(`banned-visible:${copy}`);
    });

    const screenshotPath = path.join(OUT_DIR, "project_data_entry_ux.png");
    await page.screenshot({ path: screenshotPath, fullPage: true });
    const report = {
      script: path.basename(new URL(import.meta.url).pathname),
      target_url: TARGET_URL,
      checked_at: new Date().toISOString(),
      checks,
      screenshot: screenshotPath,
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
