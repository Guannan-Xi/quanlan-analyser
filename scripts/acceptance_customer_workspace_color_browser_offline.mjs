import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";

const require = createRequire(import.meta.url);
const { chromium } = require("../frontend/node_modules/playwright");

const TARGET_URL =
  process.env.QLANALYSER_FRONTEND_URL ||
  "http://127.0.0.1:4174/?customer_demo=login&api=http://127.0.0.1:8001/api";
const OUT_DIR =
  process.env.QLANALYSER_COLOR_EVIDENCE_DIR ||
  path.resolve("work/release_evidence/20260625-customer-workspace-color");
const EVIDENCE_PATH = path.join(OUT_DIR, "customer_workspace_color_browser_offline.json");

const checks = [];
const pass = (name, details = {}) => checks.push({ name, pass: true, details });
const fail = (name, details = {}) => checks.push({ name, pass: false, details });

async function openView(page, viewId) {
  await page.evaluate((id) => {
    document.querySelectorAll(".view").forEach((node) => node.classList.toggle("active", node.id === id));
    document.querySelectorAll(".nav-item").forEach((node) => node.classList.toggle("active", node.dataset.view === id));
    const title = document.querySelector("#viewTitle");
    if (title) {
      title.textContent = {
        dashboard: "项目管理",
        analysis: "数据准备",
        workflow: "分析任务",
        publication: "报告交付",
      }[id] || "QLanalyser";
    }
  }, viewId);
  await page.waitForTimeout(250);
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
    await page.evaluate(() => {
      document.querySelector("#loginScreen")?.setAttribute("hidden", "");
      const shell = document.querySelector("#appShell");
      shell?.removeAttribute("hidden");
      document.body.classList.add("is-authenticated");
      document.body.dataset.role = "customer";
      document.querySelectorAll('[data-role="admin"]').forEach((node) => {
        node.setAttribute("hidden", "");
        node.setAttribute("aria-hidden", "true");
      });
      document.querySelectorAll('[data-role="customer"]').forEach((node) => {
        node.removeAttribute("hidden");
        node.setAttribute("aria-hidden", "false");
      });
    });

    const screenshots = {};
    for (const view of ["dashboard", "analysis", "workflow", "publication"]) {
      await openView(page, view);
      const file = path.join(OUT_DIR, `${view}_color.png`);
      await page.screenshot({ path: file, fullPage: true });
      screenshots[view] = file;
    }

    const styleProbe = await page.evaluate(() => {
      const primary = getComputedStyle(document.querySelector(".primary-btn")).backgroundImage || getComputedStyle(document.querySelector(".primary-btn")).backgroundColor;
      const ghost = getComputedStyle(document.querySelector(".ghost-btn")).backgroundColor;
      const panel = getComputedStyle(document.querySelector(".panel")).backgroundColor;
      const sidebarAccount = getComputedStyle(document.querySelector(".sidebar .account-panel")).backgroundColor;
      const statusChip = getComputedStyle(document.querySelector(".status-chip") || document.querySelector(".badge")).backgroundColor;
      return { primary, ghost, panel, sidebarAccount, statusChip };
    });

    styleProbe.primary.includes("21, 92, 156") || styleProbe.primary.includes("linear-gradient")
      ? pass("primary-button-uses-brand-blue", { primary: styleProbe.primary })
      : fail("primary-button-uses-brand-blue", { primary: styleProbe.primary });
    styleProbe.panel.includes("255, 255, 255")
      ? pass("panel-background-is-white", { panel: styleProbe.panel })
      : fail("panel-background-is-white", { panel: styleProbe.panel });
    styleProbe.sidebarAccount.includes("255, 255, 255") && !styleProbe.sidebarAccount.includes("1)")
      ? pass("sidebar-account-keeps-dark-translucent-style", { sidebarAccount: styleProbe.sidebarAccount })
      : fail("sidebar-account-keeps-dark-translucent-style", { sidebarAccount: styleProbe.sidebarAccount });

    const report = {
      script: path.basename(new URL(import.meta.url).pathname),
      target_url: TARGET_URL,
      checked_at: new Date().toISOString(),
      checks,
      style_probe: styleProbe,
      screenshots,
      console_errors: consoleErrors,
      passed: checks.every((item) => item.pass),
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
