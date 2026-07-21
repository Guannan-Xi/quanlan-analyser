import fs from "node:fs";
import path from "node:path";
import { chromium, chromiumLaunchOptions } from "./lib/playwright_runtime.mjs";


const FRONTEND_URL = process.env.QLANALYSER_FRONTEND_URL
  || "http://127.0.0.1:4174/module-lab.html?api=http://127.0.0.1:8001/api&acceptance=layout-review";
const EVIDENCE_DIR = path.resolve("work/release_evidence/07-mainline-integration");
const EVIDENCE_PATH = process.env.QLANALYSER_MODULE_LAB_LAYOUT_EVIDENCE
  || path.join(EVIDENCE_DIR, "module_lab_layout_review.json");
const SCREENSHOT_DIR = process.env.QLANALYSER_MODULE_LAB_LAYOUT_SCREENSHOTS
  || path.join(EVIDENCE_DIR, "module_lab_layout_review_screenshots");

const VIEWPORTS = [
  { name: "desktop", width: 1440, height: 1000 },
  { name: "mobile", width: 390, height: 844 },
  { name: "narrow", width: 360, height: 800 },
];

const EXPECTED_TEXT = [
  "当前可用分析方法",
  "数据准备与 QC",
  "按科学目的归类的稳定分析",
  "事件筛查 / 癫痫样事件",
];

const CURRENT_EXPECTED_TEXT = [
  "科研分析底座",
  "数据准备与 QC",
  "按科学目的归类的稳定分析",
  "实验室预览分析方法",
];

const ASCII_EXPECTED_TEXT = [
  "\u5206\u6790\u65b9\u6cd5\u5e93",
  "\u6570\u636e\u51c6\u5907\u4e0e QC",
  "\u6309\u79d1\u5b66\u76ee\u7684\u5f52\u7c7b\u7684\u7a33\u5b9a\u5206\u6790",
  "\u5b9e\u9a8c\u5ba4\u9884\u89c8\u5206\u6790\u65b9\u6cd5",
];

const FORBIDDEN_TEXT = [
  "预览方法，需复核",
  "交付前需要复核参数、统计口径和解释边界",
];

const evidence = {
  status: "running",
  frontendUrl: FRONTEND_URL,
  startedAt: new Date().toISOString(),
  viewports: [],
  errors: [],
};

function writeEvidence() {
  fs.mkdirSync(EVIDENCE_DIR, { recursive: true });
  fs.writeFileSync(EVIDENCE_PATH, `${JSON.stringify(evidence, null, 2)}\n`, "utf8");
}

function localBrowserExecutable() {
  const candidates = [
    process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE,
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  ].filter(Boolean);
  return candidates.find((item) => fs.existsSync(item)) || "";
}

async function inspectViewport(browser, viewport) {
  const page = await browser.newPage({ viewport: { width: viewport.width, height: viewport.height } });
  const screenshotPath = path.join(SCREENSHOT_DIR, `${viewport.name}-${viewport.width}x${viewport.height}.png`);
  const result = {
    viewport,
    screenshotPath,
    passed: false,
    issues: [],
  };
  page.on("pageerror", (error) => result.issues.push({ type: "pageerror", message: error.message }));
  page.on("console", (msg) => {
    if (msg.type() === "error" && !msg.text().includes("Failed to load resource")) {
      result.issues.push({ type: "console", message: msg.text() });
    }
  });
  try {
    await page.goto(FRONTEND_URL, { waitUntil: "networkidle", timeout: 60000 });
    await page.waitForSelector("[data-method-group]", { timeout: 20000 });
    fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
    await page.screenshot({ path: screenshotPath, fullPage: true });
    const checks = await page.evaluate(({ expectedText, forbiddenText }) => {
      const bodyText = document.body.innerText || "";
      const groupCount = document.querySelectorAll("[data-method-group]").length;
      const pickerCount = document.querySelectorAll("[data-method-picker]").length;
      const horizontalOverflow = document.documentElement.scrollWidth > window.innerWidth + 2;
      const missingText = expectedText.filter((text) => !bodyText.includes(text));
      const forbiddenHits = forbiddenText.filter((text) => bodyText.includes(text));
      return {
        groupCount,
        pickerCount,
        horizontalOverflow,
        scrollWidth: document.documentElement.scrollWidth,
        innerWidth: window.innerWidth,
        missingText,
        forbiddenHits,
      };
    }, { expectedText: ASCII_EXPECTED_TEXT, forbiddenText: FORBIDDEN_TEXT });
    result.checks = checks;
    if (checks.groupCount !== 10) result.issues.push({ type: "group_count", message: `expected 10 groups, got ${checks.groupCount}` });
    if (checks.pickerCount !== 0) result.issues.push({ type: "method_picker", message: `expected 0 method pickers, got ${checks.pickerCount}` });
    if (checks.horizontalOverflow) result.issues.push({ type: "horizontal_overflow", message: `scrollWidth ${checks.scrollWidth} > innerWidth ${checks.innerWidth}` });
    if (checks.missingText.length) result.issues.push({ type: "missing_boundary_text", message: checks.missingText.join(", ") });
    if (checks.forbiddenHits.length) result.issues.push({ type: "forbidden_preview_copy", message: checks.forbiddenHits.join(", ") });
    result.passed = result.issues.length === 0;
  } catch (error) {
    result.issues.push({ type: "exception", message: error.message || String(error) });
    try {
      fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
      await page.screenshot({ path: screenshotPath, fullPage: true });
    } catch (_) {}
  } finally {
    await page.close();
  }
  return result;
}

async function main() {
  writeEvidence();
  const executablePath = localBrowserExecutable();
  const browser = await chromium.launch(executablePath ? { executablePath } : {});
  try {
    for (const viewport of VIEWPORTS) {
      evidence.viewports.push(await inspectViewport(browser, viewport));
      writeEvidence();
    }
  } finally {
    await browser.close();
  }
  evidence.status = evidence.viewports.every((item) => item.passed) && evidence.errors.length === 0 ? "passed" : "failed";
  evidence.finishedAt = new Date().toISOString();
  writeEvidence();
  console.log(JSON.stringify(evidence, null, 2));
  if (evidence.status !== "passed") process.exit(1);
}

main();
