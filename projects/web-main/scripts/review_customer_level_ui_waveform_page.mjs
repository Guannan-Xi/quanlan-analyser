import fs from "node:fs";
import path from "node:path";
import { chromium, chromiumLaunchOptions } from "./lib/playwright_runtime.mjs";

const repoRoot = process.cwd();
const evidenceDir = path.join(repoRoot, "work", "release_evidence", "20260627-customer-level-ui-review");
fs.mkdirSync(evidenceDir, { recursive: true });

const url = "http://127.0.0.1:4174/?customer_demo=auto&teaching_demo=auto&api=http%3A%2F%2F127.0.0.1%3A8001%2Fapi&v=customer-ui-review#analysis";
const viewports = [
  { name: "desktop_1440", width: 1440, height: 900 },
  { name: "laptop_1280", width: 1280, height: 820 },
  { name: "mobile_390", width: 390, height: 844 },
];

async function collect(page, viewportName) {
  return page.evaluate((viewportNameArg) => {
    const box = (selector) => {
      const el = document.querySelector(selector);
      const rect = el?.getBoundingClientRect();
      return rect ? { x: rect.x, y: rect.y, width: rect.width, height: rect.height } : null;
    };
    const style = (selector) => {
      const el = document.querySelector(selector);
      if (!el) return null;
      const cs = getComputedStyle(el);
      return { display: cs.display, visibility: cs.visibility, overflow: cs.overflow, color: cs.color, background: cs.backgroundColor };
    };
    const visibleText = (selector, n = 300) => (document.querySelector(selector)?.textContent || "").trim().slice(0, n);
    return {
      viewport: viewportNameArg,
      url: location.href,
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
      horizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 2,
      activeView: document.querySelector(".view.active")?.id || "",
      bodyHasFailedToFetch: document.body.innerText.includes("Failed to fetch"),
      bodyHasWaitingEeg: document.body.innerText.includes("等待加载 EEG 数据") || document.body.innerText.includes("等待选择 EEG 数据"),
      navText: visibleText(".sidebar", 700),
      pageTitle: visibleText("#analysis .panel-head h2", 100),
      dataQueueText: visibleText(".ia-data-queue", 800),
      waveformStatus: visibleText("[data-testid='waveform-status-bar']", 800),
      preprocessingText: visibleText("[data-testid='preprocessing-inline-panel']", 800),
      canvas: box("#eegCanvas"),
      canvasStyle: style("#eegCanvas"),
      emptyOverlay: {
        box: box("#eegEmpty"),
        style: style("#eegEmpty"),
        className: document.querySelector("#eegEmpty")?.className || "",
        hidden: document.querySelector("#eegEmpty")?.hidden || false,
        text: visibleText("#eegEmpty", 300),
      },
      layout: {
        appShell: box("#appShell"),
        dataPrep: box("[data-testid='data-preparation-workbench']"),
        dataQueue: box(".ia-data-queue"),
        prepMain: box(".ia-prep-main"),
        waveformLayout: box(".waveform-prep-layout"),
        waveformMain: box(".waveform-main-column"),
        preprocessing: box("[data-testid='preprocessing-inline-panel']"),
      },
      buttons: Array.from(document.querySelectorAll("#analysis button, #analysis select, #analysis input"))
        .slice(0, 80)
        .map((el) => ({
          tag: el.tagName,
          text: (el.textContent || el.getAttribute("aria-label") || el.getAttribute("title") || el.id || "").trim().slice(0, 80),
          id: el.id || "",
          disabled: Boolean(el.disabled),
          hidden: Boolean(el.hidden),
          rect: (() => {
            const r = el.getBoundingClientRect();
            return { x: r.x, y: r.y, width: r.width, height: r.height };
          })(),
        })),
    };
  }, viewportName);
}

const browser = await chromium.launch(chromiumLaunchOptions({ headless: true }));
const report = {
  generated_at: new Date().toISOString(),
  url,
  screenshots: {},
  viewports: {},
};

try {
  for (const vp of viewports) {
    const page = await browser.newPage({ viewport: { width: vp.width, height: vp.height } });
    await page.goto(url, { waitUntil: "domcontentloaded", timeout: 30000 });
    await page.waitForSelector("#eegCanvas", { state: "visible", timeout: 30000 });
    await page.waitForTimeout(4000);
    const topPath = path.join(evidenceDir, `${vp.name}_analysis_top.png`);
    const fullPath = path.join(evidenceDir, `${vp.name}_analysis_full.png`);
    await page.screenshot({ path: topPath, fullPage: false });
    await page.screenshot({ path: fullPath, fullPage: true });
    report.screenshots[`${vp.name}_top`] = topPath;
    report.screenshots[`${vp.name}_full`] = fullPath;
    report.viewports[vp.name] = await collect(page, vp.name);
    await page.close();
  }
  const output = path.join(evidenceDir, "customer_level_ui_review_probe.json");
  fs.writeFileSync(output, `${JSON.stringify(report, null, 2)}\n`, "utf8");
  console.log(JSON.stringify({ status: "passed", output, screenshots: report.screenshots }, null, 2));
} finally {
  await browser.close();
}
