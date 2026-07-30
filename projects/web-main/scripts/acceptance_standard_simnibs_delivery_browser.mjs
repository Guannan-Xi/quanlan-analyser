import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { createRequire } from "node:module";
import { chromiumLaunchOptions } from "./lib/playwright_runtime.mjs";

const root = path.resolve(process.argv[2] || "outputs/simnibs_ti_violante2023_reproduction_20260729");
const reportPath = path.join(root, "report.html");
const payloadPath = path.join(root, "standard_report_data.json");
const evidenceDir = path.join(root, "quality_control", "standard_browser");
fs.mkdirSync(evidenceDir, { recursive: true });

const moduleDir = process.env.QLANALYSER_PLAYWRIGHT_MODULE_DIR;
if (!moduleDir) throw new Error("QLANALYSER_PLAYWRIGHT_MODULE_DIR is required");
const require = createRequire(import.meta.url);
const { chromium } = require(path.join(moduleDir, "index.js"));
const payload = JSON.parse(fs.readFileSync(payloadPath, "utf8"));
const browser = await chromium.launch(chromiumLaunchOptions({ headless: true }));

async function inspect(name, viewport) {
  const context = await browser.newContext({ viewport });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto(pathToFileURL(reportPath).href, { waitUntil: "load" });
  await page.waitForTimeout(250);
  const result = await page.evaluate(() => {
    const text = document.body.innerText;
    const images = [...document.images].map((image) => ({ complete: image.complete, width: image.naturalWidth, height: image.naturalHeight, alt: image.alt }));
    const anchors = [...document.querySelectorAll("nav a")];
    return {
      title: document.querySelector("h1")?.textContent.trim(),
      sections: document.querySelectorAll("main > section").length,
      figures: document.querySelectorAll("figure").length,
      images,
      navTargetsValid: anchors.every((anchor) => document.querySelector(anchor.getAttribute("href"))),
      overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
      tableScrollable: [...document.querySelectorAll(".table-wrap")].every((node) => node.scrollWidth <= node.clientWidth || getComputedStyle(node).overflowX === "auto"),
      hasServiceIdentity: text.includes("SimNIBS 仿真服务"),
      hasFivePartStructure: ["一、主要结论", "二、模型与刺激方案", "三、模拟结果", "四、结果解读", "五、方法、质量控制与交付"].every((value) => text.includes(value)),
      hasPublicationArtifacts: ["Excel 结果表", "图表数据", "NIfTI 数据", "HDF5 数据", "复现说明"].every((value) => text.includes(value)),
      hasQcStatuses: text.includes("载波网格一致性") && text.includes("跨受试者稳健性"),
      hasMojibake: /锟斤拷|鐢靛満|娴烽┈|閿欒|�/.test(text),
    };
  });
  await page.screenshot({ path: path.join(evidenceDir, `${name}_full.png`), fullPage: true });
  await page.locator("#summary").screenshot({ path: path.join(evidenceDir, `${name}_summary.png`) });
  await context.close();
  return { viewport, errors, ...result };
}

try {
  const desktop = await inspect("desktop", { width: 1440, height: 900 });
  const mobile = await inspect("mobile", { width: 390, height: 844 });
  const checks = [desktop, mobile];
  const passed = payload.schema_version === "simnibs.delivery.v2"
    && payload.project.title === desktop.title
    && checks.every((item) => item.errors.length === 0)
    && checks.every((item) => item.sections === 5 && item.figures === payload.figures.length)
    && checks.every((item) => item.images.every((image) => image.complete && image.width > 0 && image.height > 0 && image.alt.trim()))
    && checks.every((item) => item.navTargetsValid && !item.overflow && item.tableScrollable)
    && checks.every((item) => item.hasServiceIdentity && item.hasFivePartStructure && item.hasPublicationArtifacts && item.hasQcStatuses && !item.hasMojibake);
  const audit = { status: passed ? "passed" : "failed", desktop, mobile };
  fs.writeFileSync(path.join(evidenceDir, "browser_audit.json"), JSON.stringify(audit, null, 2), "utf8");
  console.log(JSON.stringify({ status: audit.status, sections: desktop.sections, figures: desktop.figures, desktopOverflow: desktop.overflow, mobileOverflow: mobile.overflow }, null, 2));
  if (!passed) process.exitCode = 1;
} finally {
  await browser.close();
}
