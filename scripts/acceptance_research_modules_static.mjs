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
  check(`clean text ${path.relative(ROOT, file)}`, !text.includes("\uFFFD") && !text.includes("????"));
}
function assertFile(url, label) {
  const file = frontendPath(url);
  if (!file) return;
  const exists = fs.existsSync(file);
  const size = exists ? fs.statSync(file).size : 0;
  report.files.push({ label, url, path: path.relative(ROOT, file), size, exists });
  check(`file exists ${label}`, exists && size > 0, { url, size });
}
async function pageOk(page, url) {
  const response = await page.goto(url, { waitUntil: "networkidle", timeout: 30000 });
  check(`page response ${url}`, response && response.ok(), { status: response?.status() });
  const body = await page.locator("body").innerText();
  check(`no mojibake ${url}`, !body.includes("\uFFFD") && !body.includes("????"));
  const brokenImages = await page.$$eval("img", imgs => imgs.filter(img => !img.complete || img.naturalWidth < 1).map(img => img.getAttribute("src")));
  check(`images loaded ${url}`, brokenImages.length === 0, { brokenImages });
}

async function main() {
  check("manifest exists", fs.existsSync(MANIFEST_PATH), { path: path.relative(ROOT, MANIFEST_PATH) });
  const manifest = JSON.parse(readText(MANIFEST_PATH));
  check("module list", EXPECTED.every(key => manifest.modules?.[key]), { modules: Object.keys(manifest.modules || {}) });

  for (const file of [
    path.join(FRONTEND, "research-modules.html"),
    path.join(FRONTEND, "research-modules.js"),
    path.join(FRONTEND, "research-modules.css"),
    MANIFEST_PATH,
  ]) assertCleanText(file);

  for (const key of Object.keys(manifest.sampleData || {})) assertFile(manifest.sampleData[key], `sampleData.${key}`);
  for (const key of Object.keys(manifest.shared || {})) assertFile(manifest.shared[key], `shared.${key}`);
  for (const slug of EXPECTED) {
    const module = manifest.modules[slug];
    const pagePath = path.join(FRONTEND, "research-module", module.page);
    check(`module page file ${slug}`, fs.existsSync(pagePath), { page: module.page });
    assertCleanText(pagePath);
    for (const fig of module.figures || []) assertFile(fig.src, `${slug}.figure.${fig.label}`);
    for (const table of module.tables || []) assertFile(table.src, `${slug}.table.${table.label}`);
    for (const doc of module.docs || []) assertFile(doc.src, `${slug}.doc.${doc.label}`);
    assertFile(module.package, `${slug}.package`);
  }

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });
  await pageOk(page, `${BASE_URL}/research-modules.html`);
  const indexH1 = await page.locator("h1").first().innerText();
  const moduleCards = await page.locator(".module-card").count();
  check("index h1", indexH1.includes("独立测试台"), { indexH1 });
  check("index module cards", moduleCards === 6, { moduleCards });

  for (const slug of EXPECTED) {
    const module = manifest.modules[slug];
    const url = `${BASE_URL}/research-module/${module.page}`;
    await pageOk(page, url);
    const h1 = await page.locator("h1").first().innerText();
    const sampleText = await page.locator(".sample-strip").innerText();
    const panels = await page.locator(".panel").count();
    const tableRows = await page.locator(".data-table tbody tr").count();
    const docs = await page.locator(".doc-card pre").count();
    check(`module h1 ${slug}`, h1 === module.title, { h1, expected: module.title });
    check(`sample strip ${slug}`, sampleText.includes("测试输入数据") && sampleText.includes("Subject metrics CSV"), { sampleText });
    check(`module panels ${slug}`, panels >= 5, { panels });
    check(`module table rows ${slug}`, tableRows >= 3, { tableRows });
    check(`module docs ${slug}`, docs >= 4, { docs });
    report.pages.push({ slug, url, h1, panels, tableRows, docs });
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
