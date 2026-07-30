import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

import { chromium, chromiumLaunchOptions } from "./lib/playwright_runtime.mjs";

const root = path.resolve("outputs/simnibs_inverse_ti_discrete_ernie_20260729");
const reportPath = path.join(root, "report.html");
const evidencePath = path.join(root, "visual_acceptance.json");
const requiredFigureStems = [
  "fig00_model_target_registration",
  "fig00_inverse_electrode_montage",
  "fig00_four_electrode_e1_e2_timax",
  "fig00_four_electrode_timax_surface",
  "fig07_four_electrode_timax_slices",
  "fig08_four_electrode_quantitative",
];
const requiredSectionHeadings = [
  "结果摘要",
  "头模型、刺激方案与最终电场",
  "目标区与靶外定量",
  "逆向优化证据",
  "靶外空间分布与敏感性",
  "设备可执行性",
  "数值质量与正式研究前提",
  "论文制图与二次分析",
  "交付文件索引",
  "方法与引用",
];
const reportSha256 = crypto.createHash("sha256").update(fs.readFileSync(reportPath)).digest("hex").toUpperCase();

const browser = await chromium.launch(chromiumLaunchOptions({ headless: true }));
const results = [];

try {
  for (const viewport of [
    { name: "desktop", width: 1440, height: 900 },
    { name: "mobile", width: 390, height: 844 },
  ]) {
    const context = await browser.newContext({ viewport });
    const page = await context.newPage();
    await page.goto(pathToFileURL(reportPath).href, { waitUntil: "load" });
    await page.evaluate(async () => {
      await document.fonts.ready;
      await Promise.all([...document.images].map((img) => img.complete
        ? Promise.resolve()
        : new Promise((resolve) => {
            img.addEventListener("load", resolve, { once: true });
            img.addEventListener("error", resolve, { once: true });
          })));
    });

    const dom = await page.evaluate(() => {
      const images = [...document.images].map((img) => ({
        src: img.getAttribute("src"),
        alt: img.getAttribute("alt") || "",
        complete: img.complete,
        naturalWidth: img.naturalWidth,
        naturalHeight: img.naturalHeight,
      }));
      const visibleElements = [...document.querySelectorAll("h1,h2,h3,p,li,figure,figcaption,table")]
        .filter((element) => {
          const style = getComputedStyle(element);
          const rect = element.getBoundingClientRect();
          return style.visibility !== "hidden" && style.display !== "none" && rect.width > 0 && rect.height > 0;
        })
        .map((element, index) => {
          const rect = element.getBoundingClientRect();
          return { index, tag: element.tagName, top: rect.top, bottom: rect.bottom, left: rect.left, right: rect.right };
        });
      const overlaps = [];
      for (let index = 1; index < visibleElements.length; index += 1) {
        const previous = visibleElements[index - 1];
        const current = visibleElements[index];
        const horizontal = Math.min(previous.right, current.right) - Math.max(previous.left, current.left);
        const vertical = Math.min(previous.bottom, current.bottom) - Math.max(previous.top, current.top);
        if (horizontal > 2 && vertical > 2 && !["FIGURE", "TABLE"].includes(previous.tag) && current.tag !== "FIGCAPTION") {
          overlaps.push({ previous, current, horizontal, vertical });
        }
      }
      return {
        title: document.title,
        h1Count: document.querySelectorAll("h1").length,
        h2Texts: [...document.querySelectorAll("h2")].map((heading) => heading.textContent.trim()),
        imageCount: images.length,
        images,
        horizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
        scrollWidth: document.documentElement.scrollWidth,
        clientWidth: document.documentElement.clientWidth,
        overlaps,
        bodyText: document.body.innerText,
      };
    });

    const missingFigures = requiredFigureStems.filter((stem) => !dom.images.some((img) => img.src?.includes(stem)));
    const brokenImages = dom.images.filter((img) => !img.complete || img.naturalWidth < 2 || img.naturalHeight < 2);
    const missingAlt = dom.images.filter((img) => !img.alt.trim());
    const missingScientificText = ["V/m", "TImax", "E1", "E2", "个体 conform", "ROI"]
      .filter((term) => !dom.bodyText.includes(term));
    const missingSections = requiredSectionHeadings.filter((heading) => !dom.h2Texts.includes(heading));
    const duplicateSections = [...new Set(dom.h2Texts.filter(
      (heading, index, headings) => headings.indexOf(heading) !== index,
    ))];
    const screenshot = path.join(root, `${viewport.name}.png`);
    await page.screenshot({ path: screenshot, fullPage: true });

    results.push({
      viewport,
      ...dom,
      missingFigures,
      brokenImages,
      missingAlt,
      missingScientificText,
      missingSections,
      duplicateSections,
      screenshot,
      passed: !dom.horizontalOverflow && missingFigures.length === 0 && brokenImages.length === 0
        && missingAlt.length === 0 && missingScientificText.length === 0 && dom.overlaps.length === 0
        && dom.h1Count === 1 && missingSections.length === 0 && duplicateSections.length === 0,
    });
    await context.close();
  }
} finally {
  await browser.close();
}

const evidence = {
  generatedAt: new Date().toISOString(),
  reportPath,
  reportBytes: fs.statSync(reportPath).size,
  reportSha256,
  requiredFigureStems,
  status: results.every((result) => result.passed) ? "passed" : "failed",
  results,
};
fs.writeFileSync(evidencePath, `${JSON.stringify(evidence, null, 2)}\n`, "utf8");
console.log(JSON.stringify({ status: evidence.status, evidencePath, reportSha256, results: results.map((r) => ({ viewport: r.viewport.name, passed: r.passed, imageCount: r.imageCount, horizontalOverflow: r.horizontalOverflow, missingFigures: r.missingFigures, brokenImages: r.brokenImages.length, missingAlt: r.missingAlt.length, missingScientificText: r.missingScientificText, overlaps: r.overlaps.length })) }, null, 2));
if (evidence.status !== "passed") process.exitCode = 1;
