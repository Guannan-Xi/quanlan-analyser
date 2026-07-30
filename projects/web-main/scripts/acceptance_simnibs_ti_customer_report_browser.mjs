import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { chromium, chromiumLaunchOptions } from "./lib/playwright_runtime.mjs";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const evidenceDir = process.argv[2] ? path.resolve(process.argv[2]) : scriptDir;
const repoRoot = path.resolve(scriptDir, "..");
fs.mkdirSync(evidenceDir, { recursive: true });
const reportDir = path.join(repoRoot, "outputs", "simnibs_customer_ti_demo_ernie_20260728");
const reportPath = path.join(reportDir, "report.html");
const reportData = JSON.parse(fs.readFileSync(path.join(reportDir, "report_data.json"), "utf8"));
const expectedSliceScale = `${Number(reportData.spatial.color_scales.field_primary.vmax_v_per_m).toFixed(3)} V/m`;
const expectedSurfaceScale = `${Number(reportData.spatial.color_scales.field_surface.vmax_v_per_m).toFixed(3)} V/m`;
const manifest = JSON.parse(fs.readFileSync(path.join(reportDir, "manifest.json"), "utf8"));
const manifestHash = manifest.files.find((item) => item.path === "report.html")?.sha256;
const diskBytes = fs.readFileSync(reportPath);
const diskHash = crypto.createHash("sha256").update(diskBytes).digest("hex").toUpperCase();
const reportUrl = `${pathToFileURL(reportPath).href}?qa=${Date.now()}`;

const browser = await chromium.launch(chromiumLaunchOptions({ headless: true }));

async function inspect(name, viewport) {
  const context = await browser.newContext({ viewport });
  const page = await context.newPage();
  const errors = [];
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  page.on("pageerror", (error) => errors.push(error.message));

  const response = await page.goto(reportUrl, { waitUntil: "load", timeout: 60_000 });
  await page.evaluate(async () => {
    if (document.fonts?.ready) await document.fonts.ready;
    await Promise.all([...document.images].map((image) => image.complete
      ? Promise.resolve()
      : new Promise((resolve) => image.addEventListener("load", resolve, { once: true }))));
  });
  const responseHash = response
    ? crypto.createHash("sha256").update(await response.body()).digest("hex").toUpperCase()
    : null;

  const metrics = await page.evaluate(() => {
    const visibleTables = [...document.querySelectorAll(".table-wrap")]
      .filter((wrap) => wrap.getBoundingClientRect().width > 0)
      .map((wrap) => ({
        section: wrap.closest("section")?.id || "unknown",
        clientWidth: wrap.clientWidth,
        scrollWidth: wrap.scrollWidth,
        scrollable: wrap.scrollWidth > wrap.clientWidth,
      }));
    const images = [...document.images].map((image) => ({
      src: image.getAttribute("src"),
      alt: image.getAttribute("alt") || "",
      complete: image.complete,
      naturalWidth: image.naturalWidth,
    }));
    const roiHeaders = [...document.querySelectorAll("#roi thead th")]
      .map((header) => header.innerText.replace(/\s+/g, " ").trim());
    return {
      overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
      images,
      visibleTables,
      roiHeaders,
      roiText: document.querySelector("#roi")?.innerText || "",
      fieldText: document.querySelector("#field")?.innerText || "",
      summaryText: document.querySelector("#summary")?.innerText || "",
      modelText: document.querySelector("#model")?.innerText || "",
      methodsText: document.querySelector("#methods")?.innerText || "",
      buildIdentity: document.querySelector("[data-bind=buildIdentity]")?.textContent || "",
      sectionNumbers: [...document.querySelectorAll(".content>.section:not([hidden]) .section-no")].map((node) => node.textContent.trim()),
    };
  });

  await page.evaluate(() => { window.location.hash = "#roi"; });
  await page.waitForFunction(() => {
    const heading = document.querySelector("#roi h2")?.getBoundingClientRect();
    return Boolean(heading && heading.top >= 0 && heading.top < window.innerHeight);
  }, null, { timeout: 5_000 });
  await page.waitForTimeout(150);
  const anchor = await page.evaluate(() => {
    const toolbar = document.querySelector(".toolbar")?.getBoundingClientRect();
    const heading = document.querySelector("#roi h2")?.getBoundingClientRect();
    return {
      toolbarBottom: toolbar?.bottom ?? 0,
      headingTop: heading?.top ?? -1,
      headingVisible: Boolean(
        toolbar && heading
        && heading.top >= toolbar.bottom
        && heading.bottom <= window.innerHeight
      ),
    };
  });

  await page.screenshot({ path: path.join(evidenceDir, `${name}_roi_anchor.png`) });
  await page.screenshot({ path: path.join(evidenceDir, `${name}_full.png`), fullPage: true });
  await page.addStyleTag({ content: ".toolbar{display:none!important}" });
  for (const section of ["model", "protocol", "field", "roi", "methods", "delivery"]) {
    await page.locator(`#${section}`).screenshot({ path: path.join(evidenceDir, `${name}_${section}.png`) });
  }
  await context.close();

  return {
    viewport,
    responseHash,
    sameFrozenArtifact: responseHash === diskHash && diskHash === manifestHash,
    errors,
    anchor,
    ...metrics,
  };
}

try {
  const desktop = await inspect("desktop", { width: 1440, height: 900 });
  const mobile = await inspect("mobile", { width: 390, height: 844 });
  const allImages = [...desktop.images, ...mobile.images];
  const status = (
    desktop.sameFrozenArtifact
    && mobile.sameFrozenArtifact
    && !desktop.overflow
    && !mobile.overflow
    && desktop.errors.length === 0
    && mobile.errors.length === 0
    && allImages.length === 20
    && allImages.every((image) => image.complete && image.naturalWidth > 0 && image.alt.trim())
    && desktop.anchor.headingVisible
    && mobile.anchor.headingVisible
    && desktop.sectionNumbers.join(",") === "01,02,03,04,05,06,07,08,09"
    && mobile.sectionNumbers.join(",") === "01,02,03,04,05,06,07,08,09"
    && desktop.roiHeaders.length === 13
    && desktop.roiHeaders.some((header) => header.includes("超阈四面体数"))
    && desktop.roiHeaders.some((header) => header.includes("本区域体积分母"))
    && desktop.roiHeaders.some((header) => header.includes("全灰质高值尾部分配"))
    && desktop.roiText.includes("mm³")
    && desktop.summaryText.includes("不构成峰值位置稳定性检验")
    && desktop.modelText.includes("ROI 配准复核")
    && desktop.modelText.includes("往返误差")
    && desktop.modelText.includes("MNI 定义")
    && desktop.modelText.includes("未独立判定")
    && desktop.methodsText.includes("全灰质覆盖率约 0.1%")
    && desktop.methodsText.includes("全灰质高值尾部")
    && desktop.methodsText.includes("体积加权分位数")
    && desktop.methodsText.includes("searchsorted")
    && desktop.fieldText.includes(expectedSliceScale)
    && desktop.fieldText.includes(expectedSurfaceScale)
    && desktop.fieldText.includes("\u989c\u8272\u4e0d\u53ef\u8de8\u7ec4\u76f4\u63a5\u6bd4\u8f83")
    && desktop.methodsText.includes("不进行线性插值")
    && desktop.methodsText.includes("峰值位置与 ROI 位移")
    && desktop.methodsText.includes("复用同一次 FEM 场解")
    && desktop.methodsText.includes("MNI2Conform_nonl.nii.gz")
    && desktop.methodsText.includes("Conform2MNI_nonl.nii.gz")
    && desktop.methodsText.includes("不能直接解释为解剖位移")
    && desktop.methodsText.includes("体积加权 P99.9")
    && desktop.methodsText.includes("GM/CSF 界面判断")
    && mobile.visibleTables.every((table) => table.scrollable)
  ) ? "passed" : "failed";
  const audit = { status, diskHash, manifestHash, desktop, mobile };
  fs.writeFileSync(path.join(evidenceDir, "browser_audit.json"), JSON.stringify(audit, null, 2), "utf8");
  console.log(JSON.stringify({
    status,
    sameFrozenArtifact: desktop.sameFrozenArtifact && mobile.sameFrozenArtifact,
    desktop: {
      overflow: desktop.overflow,
      errors: desktop.errors,
      anchor: desktop.anchor,
      roiHeaders: desktop.roiHeaders,
      imageCount: desktop.images.length,
    },
    mobile: {
      overflow: mobile.overflow,
      errors: mobile.errors,
      anchor: mobile.anchor,
      scrollableTables: mobile.visibleTables,
      imageCount: mobile.images.length,
    },
  }, null, 2));
  if (status !== "passed") process.exitCode = 1;
} finally {
  await browser.close();
}
