import fs from "node:fs";
import path from "node:path";
import { chromium, chromiumLaunchOptions } from "./lib/playwright_runtime.mjs";

const repoRoot = process.cwd();
const evidenceDir = process.env.QLANALYSER_MAIN_DESIGN_CLEANUP_DIR
  || path.join(repoRoot, "work", "release_evidence", "20260628-main-workbench-design-cleanup");
const frontendUrl = process.env.QLANALYSER_MAIN_DESIGN_CLEANUP_URL
  || "http://127.0.0.1:4174/?customer_demo=auto&teaching_demo=auto&api=http%3A%2F%2F127.0.0.1%3A8001%2Fapi&v=main-design-cleanup#analysis";

fs.mkdirSync(evidenceDir, { recursive: true });

const viewports = [
  { id: "desktop_1440", width: 1440, height: 900 },
  { id: "laptop_1280", width: 1280, height: 820 },
  { id: "mobile_390", width: 390, height: 844 },
];

async function captureViewport(browser, viewport) {
  const page = await browser.newPage({ viewport: { width: viewport.width, height: viewport.height } });
  try {
    await page.goto(frontendUrl, { waitUntil: "domcontentloaded", timeout: 30000 });
    await page.waitForSelector("#eegCanvas", { state: "visible", timeout: 30000 });
    await page.waitForFunction(() => {
      const empty = document.querySelector("#eegEmpty");
      const canvas = document.querySelector("#eegCanvas");
      const rect = canvas?.getBoundingClientRect();
      return empty?.classList.contains("ready") && rect?.width > 100 && rect?.height > 200;
    }, null, { timeout: 30000 });
    const screenshotPath = path.join(evidenceDir, `${viewport.id}_analysis_top.png`);
    await page.screenshot({ path: screenshotPath, fullPage: false });
    const metrics = await page.evaluate(() => {
      const status = document.querySelector("[data-testid='waveform-status-bar']");
      const controls = Array.from(document.querySelectorAll("#analysis button, #analysis input, #analysis select"))
        .filter((item) => {
          const style = getComputedStyle(item);
          const rect = item.getBoundingClientRect();
          return style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0;
        });
      const secondaryPanels = Array.from(document.querySelectorAll(".design-secondary-record-panel"))
        .map((panel) => {
          const rect = panel.getBoundingClientRect();
          return { testid: panel.getAttribute("data-testid"), y: rect.y, height: rect.height };
        });
      return {
        scrollWidth: document.documentElement.scrollWidth,
        clientWidth: document.documentElement.clientWidth,
        horizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 2,
        statusText: status?.textContent?.trim() || "",
        visibleControlCount: controls.length,
        secondaryPanels,
        bodyTextForbiddenDebugTerms: ["manifest", "runner", "dispatch", "schema", "artifact", "cache range"]
          .filter((term) => document.body.innerText.toLowerCase().includes(term)),
      };
    });
    return { ...viewport, screenshotPath, metrics, passed: !metrics.horizontalOverflow && metrics.bodyTextForbiddenDebugTerms.length === 0 };
  } finally {
    await page.close();
  }
}

async function run() {
  const browser = await chromium.launch(chromiumLaunchOptions({ headless: true }));
  try {
    const results = [];
    for (const viewport of viewports) {
      results.push(await captureViewport(browser, viewport));
    }
    const output = {
      status: results.every((item) => item.passed) ? "passed" : "failed",
      generated_at: new Date().toISOString(),
      frontendUrl,
      results,
    };
    const outputPath = path.join(evidenceDir, "main_workbench_design_cleanup_viewports.json");
    fs.writeFileSync(outputPath, `${JSON.stringify(output, null, 2)}\n`, "utf8");
    console.log(JSON.stringify({ status: output.status, outputPath, failed: results.filter((item) => !item.passed).map((item) => item.id) }, null, 2));
    if (output.status !== "passed") process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

try {
  await run();
} catch (error) {
  const outputPath = path.join(evidenceDir, "main_workbench_design_cleanup_viewports.json");
  fs.writeFileSync(outputPath, `${JSON.stringify({ status: "failed", error: error.stack || String(error), frontendUrl, generated_at: new Date().toISOString() }, null, 2)}\n`, "utf8");
  console.error(error.stack || String(error));
  process.exit(1);
}
