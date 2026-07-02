import fs from "node:fs";
import path from "node:path";
import { chromium, chromiumLaunchOptions } from "./lib/playwright_runtime.mjs";

const repoRoot = process.cwd();
const evidenceDir = process.env.QLANALYSER_MAIN_WAVEFORM_VISIBLE_DIR
  || path.join(repoRoot, "work", "release_evidence", "20260627-main-data-prep-waveform-visible");
fs.mkdirSync(evidenceDir, { recursive: true });

const frontendUrl = process.env.QLANALYSER_MAIN_WAVEFORM_URL
  || "http://127.0.0.1:4174/?customer_demo=auto&teaching_demo=auto&api=http%3A%2F%2F127.0.0.1%3A8001%2Fapi&v=main-wave-visible#analysis";

async function run() {
  const browser = await chromium.launch(chromiumLaunchOptions({ headless: true }));
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  try {
    await page.goto(frontendUrl, { waitUntil: "domcontentloaded", timeout: 30000 });
    await page.waitForSelector("#eegCanvas", { state: "visible", timeout: 30000 });
    await page.waitForFunction(() => {
      const empty = document.querySelector("#eegEmpty");
      const canvas = document.querySelector("#eegCanvas");
      const rect = canvas?.getBoundingClientRect();
      return empty?.classList.contains("ready") && rect?.width > 600 && rect?.height > 350 && !document.body.innerText.includes("Failed to fetch");
    }, null, { timeout: 30000 });
    const state = await page.evaluate(() => {
      const canvas = document.querySelector("#eegCanvas");
      const rect = canvas?.getBoundingClientRect();
      const empty = document.querySelector("#eegEmpty");
      const status = document.querySelector("[data-testid='waveform-status-bar']");
      return {
        canvas: rect ? { width: rect.width, height: rect.height, x: rect.x, y: rect.y } : null,
        emptyClass: empty?.className || "",
        emptyHidden: empty?.hidden || getComputedStyle(empty).display === "none",
        emptyText: empty?.textContent || "",
        statusText: status?.textContent || "",
        statusHidden: status ? status.hidden : false,
        hasFailedToFetch: document.body.innerText.includes("Failed to fetch"),
        selectedDataText: document.querySelector("#prepDataQueue")?.textContent || "",
        navigatorText: document.querySelector("#eegNavigatorLabel")?.textContent || "",
        windowControlText: document.querySelector("#eegWindowPreset")?.textContent || "",
      };
    });
    const screenshotPath = path.join(evidenceDir, "main_data_prep_waveform_visible.png");
    await page.screenshot({ path: screenshotPath, fullPage: false });
    const duplicatedStatusTerms = ["s/page", "8 ch", "uV/row", "Raw", "浏览模式"];
    const statusHasDuplicatedControlText = duplicatedStatusTerms.some((term) => state.statusText.includes(term));
    const checks = [
      { id: "teaching-data-selected", passed: /teaching_oddball/i.test(state.selectedDataText) },
      { id: "canvas-visible-wide-enough", passed: state.canvas?.width > 600 && state.canvas?.height > 350, value: state.canvas },
      { id: "empty-overlay-hidden", passed: state.emptyHidden && state.emptyClass.includes("ready"), value: state.emptyClass },
      { id: "no-failed-to-fetch", passed: !state.hasFailedToFetch },
      { id: "status-bar-deduped-by-default", passed: !statusHasDuplicatedControlText, value: { statusText: state.statusText, statusHidden: state.statusHidden, duplicatedStatusTerms } },
      { id: "time-context-owned-by-controls", passed: state.navigatorText.includes("/") && state.windowControlText.includes("s/page"), value: { navigatorText: state.navigatorText, windowControlText: state.windowControlText } },
    ];
    const result = {
      status: checks.every((check) => check.passed) ? "passed" : "failed",
      generated_at: new Date().toISOString(),
      frontendUrl,
      screenshotPath,
      state,
      checks,
    };
    const outputPath = path.join(evidenceDir, "main_data_prep_waveform_visible_e2e.json");
    fs.writeFileSync(outputPath, `${JSON.stringify(result, null, 2)}\n`, "utf8");
    console.log(JSON.stringify({ status: result.status, outputPath, screenshotPath, failed: checks.filter((check) => !check.passed).map((check) => check.id) }, null, 2));
    if (result.status !== "passed") process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

try {
  await run();
} catch (error) {
  const outputPath = path.join(evidenceDir, "main_data_prep_waveform_visible_e2e.json");
  fs.writeFileSync(outputPath, `${JSON.stringify({ status: "failed", error: error.stack || String(error), frontendUrl, generated_at: new Date().toISOString() }, null, 2)}\n`, "utf8");
  console.error(error.stack || String(error));
  process.exit(1);
}
