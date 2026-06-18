import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const { chromium } = require("../frontend/node_modules/playwright");
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const FRONTEND = path.join(ROOT, "frontend");
const BASE_URL = process.env.QLANALYSER_RESEARCH_MODULE_URL || "http://127.0.0.1:4177";
const MANIFEST_PATH = path.join(FRONTEND, "assets", "research-modules", "reproducibility", "research_module_manifest.json");
const EXPECTED = ["qc", "psd", "erp", "tfr", "pac", "connectivity"];
const report = { status: "running", baseUrl: BASE_URL, checks: [], pages: [], files: [] };

function check(name, ok, detail = {}) {
  report.checks.push({ name, ok: Boolean(ok), ...detail });
  if (!ok) throw new Error(`${name} failed: ${JSON.stringify(detail)}`);
}

function frontendPath(url) {
  if (!url || typeof url !== "string") return null;
  if (url.startsWith("http")) return null;
  const clean = url.startsWith("/") ? url.slice(1) : url;
  return path.join(FRONTEND, clean.replaceAll("/", path.sep));
}

function readText(file) {
  return fs.readFileSync(file, "utf8");
}

function assertCleanText(file) {
  const text = readText(file);
  check(`clean text ${path.relative(ROOT, file)}`, !text.includes("\uFFFD") && !text.includes("????"), { file: path.relative(ROOT, file) });
}

function assertFile(url, label) {
  const file = frontendPath(url);
  if (!file) return;
  const exists = fs.existsSync(file);
  const size = exists ? fs.statSync(file).size : 0;
  report.files.push({ label, url, path: path.relative(ROOT, file), size, exists });
  check(`file exists ${label}`, exists && size > 0, { url, size });
}

async function pageOk(page, url, options = {}) {
  const response = await page.goto(url, { waitUntil: "networkidle", timeout: 30000 });
  check(`page response ${url}`, response && response.ok(), { status: response?.status() });
  const body = await page.locator("body").innerText();
  check(`no mojibake ${url}`, !body.includes("\uFFFD") && !body.includes("????"), { url });
  if (!options.skipImages) {
    const brokenImages = await page.$$eval("img", (imgs) => imgs.filter((img) => !img.complete || img.naturalWidth < 1).map((img) => img.getAttribute("src")));
    check(`images loaded ${url}`, brokenImages.length === 0, { brokenImages });
  }
  return body;
}

async function main() {
  check("manifest exists", fs.existsSync(MANIFEST_PATH), { path: path.relative(ROOT, MANIFEST_PATH) });
  const manifest = JSON.parse(readText(MANIFEST_PATH));
  check("module list", EXPECTED.every((key) => manifest.modules?.[key]), { modules: Object.keys(manifest.modules || {}) });

  for (const file of [
    path.join(FRONTEND, "index.html"),
    path.join(FRONTEND, "expert-entry-demo.html"),
    path.join(FRONTEND, "styles.css"),
    path.join(FRONTEND, "research-modules.html"),
    path.join(FRONTEND, "research-modules.js"),
    path.join(FRONTEND, "research-modules.css"),
    path.join(FRONTEND, "module-lab.html"),
    path.join(FRONTEND, "module-lab.js"),
    path.join(FRONTEND, "module-lab.css"),
    path.join(FRONTEND, "qc-lab.html"),
    path.join(FRONTEND, "qc-lab.js"),
    path.join(FRONTEND, "qc-lab.css"),
    MANIFEST_PATH,
  ]) assertCleanText(file);

  Object.values(manifest.modules).forEach((module) => {
    assertFile(module.package, `${module.slug} package`);
    (module.figures || []).forEach((figure) => assertFile(figure.src, `${module.slug} figure ${figure.label}`));
    (module.tables || []).forEach((table) => assertFile(table.src, `${module.slug} table ${table.label}`));
    (module.docs || []).forEach((doc) => assertFile(doc.src, `${module.slug} doc ${doc.label}`));
  });
  Object.entries(manifest.sampleData || {}).forEach(([key, value]) => assertFile(value, `sample ${key}`));
  Object.entries(manifest.shared || {}).forEach(([key, value]) => assertFile(value, `shared ${key}`));

  const browser = await chromium.launch({ headless: true });

  const home = await browser.newPage();
  const homeBody = await pageOk(home, `${BASE_URL}/index.html`, { skipImages: true });
  const homeLabLinks = await home.locator('a[href*="module-lab.html"]').count();
  const homeRegisterTabs = await home.locator('[data-login-tab="customerRegister"]').count();
  const homeDemoButtons = await home.locator('#demoEntryBtn').count();
  const homeAdminTabs = await home.locator('[data-login-tab="adminLogin"]').count();
  check("home has no-login lab entry", homeLabLinks >= 1, { homeLabLinks, text: homeBody.slice(0, 1000) });
  check("home has customer register tab", homeRegisterTabs === 1, { homeRegisterTabs });
  check("home hides pre-login demo project", homeDemoButtons === 0, { homeDemoButtons });
  check("home has one admin entry", homeAdminTabs === 1, { homeAdminTabs });
  await home.close();

  const entry = await browser.newPage();
  const entryBody = await pageOk(entry, `${BASE_URL}/expert-entry-demo.html`, { skipImages: true });
  const entryLabLinks = await entry.locator('a[href*="module-lab.html"]').count();
  const entryRegisterTabs = await entry.locator('[data-login-tab="customerRegister"]').count();
  const entryDemoButtons = await entry.locator('#demoEntryBtn').count();
  const entryAdminTabs = await entry.locator('[data-login-tab="adminLogin"]').count();
  check("entry has no-login lab entry", entryLabLinks >= 1, { entryLabLinks, text: entryBody.slice(0, 1000) });
  check("entry has customer register tab", entryRegisterTabs === 1, { entryRegisterTabs });
  check("entry hides pre-login demo project", entryDemoButtons === 0, { entryDemoButtons });
  check("entry has one admin entry", entryAdminTabs === 1, { entryAdminTabs });
  await entry.close();

  const index = await browser.newPage();
  const researchBody = await pageOk(index, `${BASE_URL}/research-modules.html`);
  const researchLabLinks = await index.locator('a[href*="module-lab.html"]').count();
  check("research overview has lab link", researchLabLinks >= 1, { researchLabLinks, text: researchBody.slice(0, 1000) });
  const cards = await index.locator(".module-card").count();
  check("research overview module cards", cards === EXPECTED.length, { cards });
  await index.close();

  const labIndex = await browser.newPage();
  const labBody = await pageOk(labIndex, `${BASE_URL}/module-lab.html`);
  const labCards = await labIndex.locator(".module-card").count();
  const openDesignDemo = await labIndex.locator("[data-open-design-demo]").count();
  const reviewMatrix = await labIndex.locator("[data-review-matrix]").count();
  const stageButtons = await labIndex.locator("[data-stage]").count();
  check("lab overview heading", labBody.includes("\u72ec\u7acb\u5206\u6790\u6a21\u5757\u5b9e\u9a8c\u5ba4") || labBody.includes("QLanalyser \u5206\u6790\u5b9e\u9a8c\u5ba4"));
  check("lab overview module cards", labCards === EXPECTED.length, { labCards });
  check("lab has open design entry demo", openDesignDemo === 1, { openDesignDemo });
  check("lab has UI interaction review matrix", reviewMatrix === 1, { reviewMatrix });
  check("lab has review stage controls", stageButtons >= 4, { stageButtons });
  await labIndex.locator('[data-stage="review"]').click();
  const stageTitle = await labIndex.locator("#stageTitle").innerText();
  check("lab open design stage switch", stageTitle.includes("UI") || stageTitle.includes("\u8bc4\u5ba1") || stageTitle.includes("\u67e5\u770b\u8f93\u5165\u8f93\u51fa"), { stageTitle });
  await labIndex.locator('[data-review-filter="preview"]').click();
  const hiddenRows = await labIndex.locator('[data-review-scope="enabled"][hidden]').count();
  check("lab review matrix filter", hiddenRows >= 1, { hiddenRows });
  await labIndex.close();

  const qcLab = await browser.newPage();
  const qcLabBody = await pageOk(qcLab, `${BASE_URL}/qc-lab.html`);
  check("qc lab workbench page", qcLabBody.includes("QC SERVICE WORKBENCH") && qcLabBody.includes("metadata") && qcLabBody.includes("manifest"), { text: qcLabBody.slice(0, 800) });
  check("qc lab has upload input", await qcLab.locator('input[type="file"]').count() >= 1);
  check("qc lab has run button", await qcLab.locator('#runPreview').count() === 1);
  await qcLab.close();

  for (const slug of EXPECTED) {
    const oldUrl = `${BASE_URL}/research-module/${slug}.html`;
    const oldPage = await browser.newPage();
    await pageOk(oldPage, oldUrl);
    const oldHeading = await oldPage.locator("h1").innerText();
    check(`static module heading ${slug}`, oldHeading.toLowerCase().includes(slug) || oldHeading.length > 0, { oldHeading });
    await oldPage.close();

    const url = `${BASE_URL}/module-lab.html?module=${slug}`;
    const page = await browser.newPage();
    const body = await pageOk(page, url);
    const heading = await page.locator(".module-hero h1").innerText();
    const panels = await page.locator("section.panel").count();
    const tableRows = await page.locator("table tbody tr").count();
    const docs = await page.locator("[data-doc-preview], .artifact").count();
    check(`lab module heading ${slug}`, heading.length > 0, { heading });
    check(`lab module input section ${slug}`, body.includes("Inputs") || body.includes("\u8f93\u5165"), { slug });
    check(`lab module controls section ${slug}`, body.includes("Parameters") || body.includes("\u53c2\u6570"), { slug });
    check(`lab module mne section ${slug}`, body.includes("MNE"), { slug });
    check(`lab module output section ${slug}`, body.includes("Outputs") || body.includes("\u8f93\u51fa"), { slug });
    check(`lab module tests section ${slug}`, body.includes("Module acceptance matrix") || body.includes("Acceptance") || body.includes("\u6a21\u5757\u9a8c\u6536\u77e9\u9635") || body.includes("\u529f\u80fd\u68c0\u67e5\u6e05\u5355"), { slug });
    check(`lab module risks section ${slug}`, body.includes("Research guardrails") || body.includes("Risks") || body.includes("\u79d1\u7814\u8fb9\u754c\u4e0e\u98ce\u9669"), { slug });
    check(`lab module panels ${slug}`, panels >= 6, { panels });
    check(`lab module test rows ${slug}`, tableRows >= 3, { tableRows });
    check(`lab module artifacts ${slug}`, docs >= 4, { docs });
    report.pages.push({ slug, url, h1: heading, panels, tableRows, docs });
    await page.close();
  }

  await browser.close();

  report.status = "passed";
  const outDir = path.join(ROOT, "work", "acceptance");
  fs.mkdirSync(outDir, { recursive: true });
  const out = path.join(outDir, "research_modules_static_latest.json");
  fs.writeFileSync(out, JSON.stringify(report, null, 2), "utf8");
  console.log(JSON.stringify({ status: report.status, checks: report.checks.length, pages: report.pages.length, report: out }, null, 2));
}

main().catch((error) => {
  report.status = "failed";
  report.error = error.stack || String(error);
  try {
    const outDir = path.join(ROOT, "work", "acceptance");
    fs.mkdirSync(outDir, { recursive: true });
    fs.writeFileSync(path.join(outDir, "research_modules_static_latest.json"), JSON.stringify(report, null, 2), "utf8");
  } catch {}
  console.error(error);
  process.exit(1);
});
