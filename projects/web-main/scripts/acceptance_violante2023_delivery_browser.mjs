import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { chromium, chromiumLaunchOptions } from "./lib/playwright_runtime.mjs";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDir, "..");
const reportDir = path.join(repoRoot, "outputs", "simnibs_ti_violante2023_reproduction_20260729");
const reportPath = path.join(reportDir, "report.html");
const evidenceDir = path.join(reportDir, "quality_control", "browser");
fs.mkdirSync(evidenceDir, { recursive: true });

const diskBytes = fs.readFileSync(reportPath);
const diskHash = crypto.createHash("sha256").update(diskBytes).digest("hex").toUpperCase();
const manifest = JSON.parse(fs.readFileSync(path.join(reportDir, "manifest.json"), "utf8"));
const manifestHash = manifest.files.find((item) => item.path === "report.html")?.sha256;
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
  await page.goto(reportUrl, { waitUntil: "load", timeout: 60_000 });
  await page.evaluate(async () => {
    if (document.fonts?.ready) await document.fonts.ready;
    await Promise.all([...document.images].map((node) => node.complete
      ? Promise.resolve()
      : new Promise((resolve) => node.addEventListener("load", resolve, { once: true }))));
  });

  const metrics = await page.evaluate(() => {
    const images = [...document.images].map((node) => ({
      src: node.getAttribute("src"),
      alt: node.alt,
      complete: node.complete,
      naturalWidth: node.naturalWidth,
      naturalHeight: node.naturalHeight,
    }));
    const navTargets = [...document.querySelectorAll("nav a")].map((node) => node.getAttribute("href"));
    const missingTargets = navTargets.filter((href) => !href?.startsWith("#") || !document.querySelector(href));
    const allText = document.body.innerText;
    const tableWrap = document.querySelector(".table-wrap");
    return {
      documentOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
      viewportWidth: document.documentElement.clientWidth,
      documentWidth: document.documentElement.scrollWidth,
      images,
      figureCount: document.querySelectorAll("figure").length,
      sectionCount: document.querySelectorAll("main > section").length,
      missingTargets,
      tableScrollable: tableWrap ? tableWrap.scrollWidth > tableWrap.clientWidth : false,
      bodyFontSizePx: Number.parseFloat(getComputedStyle(document.body).fontSize),
      reportId: document.querySelector('meta[name="report-id"]')?.content || "",
      hasMojibake: /�|涓.|锛.|鈥.|闁.|绔./.test(allText),
      keyText: {
        atlas: allText.includes("Harvard-Oxford"),
        substitute: allText.includes("10-10 实施替代"),
        notPatient: allText.includes("不是原论文的 MIDA 模型、原始参与者模型或客户 MRI"),
        dtiMissing: allText.includes("其余单元记为缺失，不写成零"),
        sensitivityMissing: allText.includes("未进行网格收敛、电极位置扰动、组织电导率敏感性、DTI 主方向定向不确定性、非线性 MNI 配准不确定性或跨受试者稳健性分析"),
        corticalControls: allText.includes("半径 10 mm 的球形采样区，不是解剖图谱分区"),
        directionalFormula: [...document.querySelectorAll("#field-definition .formula")].some((node) => node.textContent.includes("||a+b| − |a−b||")),
        timaxFormula: [...document.querySelectorAll("#field-definition .formula")].some((node) => node.textContent.includes("2|E2 × (E1−E2)| / |E1−E2|")),
        amplitudeConvention: allText.includes("不是 RMS、单个载波峰值，也不是 |E1|+|E2|"),
        p99VolumeReference: allText.includes("海马占有效方向投影分析域体积的 0.57%") && allText.includes("仅作为空间占比参照"),
        centroidBoundaryMargin: allText.includes("距前/中边界仅 0.97 mm") && allText.includes("不能视为稳健分类"),
        smallTailDisclosure: allText.includes("2.13 mm³（47 个四面体）") && allText.includes("对网格离散敏感，只作量级描述"),
        completeTargetRatios: allText.includes("mean/P95 比值同时由 1.59/1.49 变为 1.28/1.00") && allText.includes("海马与全部靶外灰质的 P95 基本相当"),
        dtiDirectionReliability: allText.includes("只表示方向向量存在且数值有限，不表示方向估计可靠") && allText.includes("未设置 FA 或特征值各向异性阈值"),
        mniTransform: allText.includes("subject2mni_coords") && allText.includes("Conform2MNI_nonl.nii.gz") && allText.includes("最近邻方式采样"),
        figure7TailDisclosure: allText.includes("柱高仅表示海马及三个蒙太奇相关皮层采样区的体积加权中位数") && allText.includes("不能仅凭本图中位数判断表层暴露"),
        paperSourceAnchors: allText.includes("Violante 2023 图 2c 报告 16 名参与者个体 MRI 模型") && allText.includes("复现 Violante 2023 沿 DTI 推导主纤维轴计算包络场的分析口径"),
        rightHippocampusMetrics: allText.includes("right hippocampus (contralateral)") && /右海马[^。]*mean\/median\/P95[^。]*V\/m/.test(allText),
        rightHippocampusSampling: allText.includes("右海马采用与左海马相同的 Harvard-Oxford 图谱、非线性 subject-to-MNI 变换和最近邻采样链"),
        offTargetIncludesRightHippocampus: allText.includes("全部靶外灰质包含右海马、其他深部灰质及皮层采样区") && allText.includes("全局 target/off-target 比值不等同于侧化选择性"),
        niftiCount: allText.includes("16 份场图与 ROI 掩膜"),
      },
    };
  });

  await page.screenshot({ path: path.join(evidenceDir, `${name}_full.png`), fullPage: true });
  for (const section of ["summary", "protocol", "results", "interpretation", "methods"]) {
    await page.locator(`#${section}`).screenshot({ path: path.join(evidenceDir, `${name}_${section}.png`) });
  }
  await context.close();
  return { viewport, errors, ...metrics };
}

try {
  const desktop = await inspect("desktop", { width: 1440, height: 900 });
  const mobile = await inspect("mobile", { width: 390, height: 844 });
  const allImages = [...desktop.images, ...mobile.images];
  const keyTextPassed = Object.values(desktop.keyText).every(Boolean) && Object.values(mobile.keyText).every(Boolean);
  const passed = (
    diskHash === manifestHash
    && desktop.errors.length === 0
    && mobile.errors.length === 0
    && !desktop.documentOverflow
    && !mobile.documentOverflow
    && desktop.figureCount === 10
    && mobile.figureCount === 10
    && desktop.sectionCount === 5
    && mobile.sectionCount === 5
    && desktop.missingTargets.length === 0
    && mobile.missingTargets.length === 0
    && allImages.length === 20
    && allImages.every((item) => item.complete && item.naturalWidth > 0 && item.naturalHeight > 0 && item.alt.trim())
    && !desktop.hasMojibake
    && !mobile.hasMojibake
    && keyTextPassed
    && mobile.tableScrollable
    && desktop.reportId === mobile.reportId
    && desktop.reportId.length > 20
  );
  const audit = { status: passed ? "passed" : "failed", diskHash, manifestHash, desktop, mobile };
  fs.writeFileSync(path.join(evidenceDir, "browser_audit.json"), JSON.stringify(audit, null, 2), "utf8");
  console.log(JSON.stringify({
    status: audit.status,
    sameFrozenArtifact: diskHash === manifestHash,
    desktop: { overflow: desktop.documentOverflow, errors: desktop.errors, figures: desktop.figureCount, images: desktop.images.length, mojibake: desktop.hasMojibake },
    mobile: { overflow: mobile.documentOverflow, errors: mobile.errors, figures: mobile.figureCount, images: mobile.images.length, tableScrollable: mobile.tableScrollable, mojibake: mobile.hasMojibake },
    keyText: desktop.keyText,
  }, null, 2));
  if (!passed) process.exitCode = 1;
} finally {
  await browser.close();
}
