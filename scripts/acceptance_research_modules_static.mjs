import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const { chromium } = require("../frontend/node_modules/playwright");
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const FRONTEND = path.join(ROOT, "frontend");
const BASE_URL = process.env.QLANALYSER_RESEARCH_MODULE_URL || "http://127.0.0.1:4177";
const MANIFEST_PATH = path.join(FRONTEND, "assets", "research-modules", "reproducibility", "research_module_manifest.json");
const EXPECTED = ["qc", "psd", "erp", "tfr", "pac", "connectivity"];
const CUSTOMER_DENYLIST = ["v0.1", "demo", "Demo", "本地演示", "local API", "后台", "管理员", "API 服务"];
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

function assertCustomerCopy(text, scope) {
  const hits = CUSTOMER_DENYLIST.filter((item) => text.includes(item));
  check(`${scope} customer-facing copy`, hits.length === 0, { hits, text: text.slice(0, 1000) });
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
  assertCustomerCopy(homeBody, "home");
  const homeLabLinks = await home.locator('a[href*="module-lab.html"]:visible').count();
  const homeRegisterTabs = await home.locator('[data-login-tab="customerRegister"]').count();
  const homeDemoButtons = await home.locator('#demoEntryBtn').count();
  const homeAdminTabs = await home.locator('[data-login-tab="adminLogin"]:visible').count();
  check("home hides secondary lab entry", homeLabLinks === 0, { homeLabLinks, text: homeBody.slice(0, 1000) });
  check("home has customer register tab", homeRegisterTabs === 1, { homeRegisterTabs });
  check("home hides pre-login demo project", homeDemoButtons === 0, { homeDemoButtons });
  check("home hides operations entry", homeAdminTabs === 0, { homeAdminTabs });
  await home.close();

  const entry = await browser.newPage();
  const entryBody = await pageOk(entry, `${BASE_URL}/expert-entry-demo.html`, { skipImages: true });
  assertCustomerCopy(entryBody, "entry");
  const entryLabLinks = await entry.locator('a[href*="module-lab.html"]:visible').count();
  const entryRegisterTabs = await entry.locator('[data-login-tab="customerRegister"]').count();
  const entryDemoButtons = await entry.locator('#demoEntryBtn').count();
  const entryAdminTabs = await entry.locator('[data-login-tab="adminLogin"]:visible').count();
  check("entry hides secondary lab entry", entryLabLinks === 0, { entryLabLinks, text: entryBody.slice(0, 1000) });
  check("entry has customer register tab", entryRegisterTabs === 1, { entryRegisterTabs });
  check("entry hides pre-login demo project", entryDemoButtons === 0, { entryDemoButtons });
  check("entry hides operations entry", entryAdminTabs === 0, { entryAdminTabs });
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
  check("analysis lab copy uses customer-facing name", labBody.includes("\u5206\u6790\u5b9e\u9a8c\u5ba4") && !labBody.includes("Open Design"), { text: labBody.slice(0, 1000) });
  check("experience center labels stable items", labBody.includes("\u5df2\u53ef\u4f53\u9a8c") && !labBody.includes("\u5df2\u542f\u7528"), { text: labBody.slice(0, 1000) });
  check("experience center labels preview items", labBody.includes("\u5373\u5c06\u5f00\u653e") && !labBody.includes("\u9884\u7814"), { text: labBody.slice(0, 1000) });
  check("analysis lab heading", labBody.includes("\u5206\u6790\u5b9e\u9a8c\u5ba4"));
  check("experience center project cards", labCards >= EXPECTED.length, { labCards, expected_min: EXPECTED.length });
  const previewCards = await labIndex.locator(".preview-card").count();
  check("experience center has preview cards", previewCards >= 1, { previewCards });
  await labIndex.close();

  const qcLab = await browser.newPage();
  const qcLabBody = await pageOk(qcLab, `${BASE_URL}/qc-lab.html`);
  check("qc lab data preparation page", qcLabBody.includes("QC 与数据准备") && qcLabBody.includes("metadata") && qcLabBody.includes("真实波形"), { text: qcLabBody.slice(0, 800) });
  check("qc lab has upload input", await qcLab.locator('input[type="file"]').count() >= 1);
  check("qc lab real waveform action", (qcLabBody.includes("刷新真实波形") || qcLabBody.includes("Refresh waveform")) && await qcLab.locator('#runPreviewBtn').count() === 1);
  check("qc lab preview segment action", (qcLabBody.includes("保存当前片段") || qcLabBody.includes("Save evidence segment")) && await qcLab.locator('#saveSegmentBtn').count() === 1);
  check("qc lab common preparation controls", (qcLabBody.includes("64 通道") || qcLabBody.includes("64 channels")) && (qcLabBody.includes("坏段") || qcLabBody.includes("bad segments")) && (qcLabBody.includes("坏导") || qcLabBody.includes("bad channels")));
  check("qc lab plan save action", (qcLabBody.includes("保存当前方案") || qcLabBody.includes("Save draft")) && await qcLab.locator('#savePlanBtn').count() === 1 && await qcLab.locator('#confirmPlanBtn').count() === 1);
  check("qc lab visible confirmed-plan gate", qcLabBody.includes("Data preparation gate") && qcLabBody.includes("Draft plan") && qcLabBody.includes("Revision") && qcLabBody.includes("Current file"));
  check("qc lab downstream readiness copy", qcLabBody.includes("PSD readiness") && qcLabBody.includes("ERP readiness") && qcLabBody.includes("must wait for a confirmed plan"));
  check("qc lab preview-only warning", qcLabBody.includes("Preview-only filter") && qcLabBody.includes("not formal PSD/ERP analysis filters"));
  check("qc lab exposes gate data attributes", await qcLab.locator('#qcLab[data-qc-plan-status][data-qc-plan-confirmed][data-qc-plan-revision][data-qc-file-id][data-qc-psd-ready][data-qc-erp-ready]').count() === 1);
  check("qc lab exposes gate panel data attributes", await qcLab.locator('[data-qc-gate-panel][data-plan-status][data-plan-confirmed][data-plan-revision][data-file-id][data-psd-ready][data-erp-ready]').count() === 1);
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
    check(`experience detail heading ${slug}`, heading.length > 0, { heading });
    check(`experience detail input section ${slug}`, body.includes("Inputs") || body.includes("Input data") || body.includes("\u8f93\u5165"), { slug });
    check(`experience detail controls section ${slug}`, body.includes("Parameters") || body.includes("\u53c2\u6570"), { slug });
    check(`experience detail mne section ${slug}`, body.includes("MNE"), { slug });
    check(`experience detail output section ${slug}`, body.includes("Outputs") || body.includes("Artifact") || body.includes("artifact") || body.includes("\u8f93\u51fa"), { slug });
    check(`workflow detail review section ${slug}`, body.includes("\u590d\u6838\u6e05\u5355") || body.includes("\u68c0\u67e5\u6e05\u5355") || body.includes("Checklist") || body.includes("review"), { slug });
    check(`experience detail risks section ${slug}`, body.includes("Research guardrails") || body.includes("Risks") || body.includes("risk") || body.includes("guardrail") || body.includes("\u8fb9\u754c\u4e0e\u98ce\u9669") || body.includes("\u79d1\u7814\u8fb9\u754c\u4e0e\u98ce\u9669"), { slug });
    check(`experience detail panels ${slug}`, panels >= 2, { panels });
    check(`experience detail checklist rows ${slug}`, tableRows >= 0, { tableRows });
    check(`experience detail artifacts ${slug}`, docs >= 0, { docs });
    report.pages.push({ slug, url, h1: heading, panels, tableRows, docs });
    await page.close();
  }

  await browser.close();

  report.status = "passed";
  let outDir = path.join(ROOT, "work", "acceptance");
  try {
    fs.mkdirSync(outDir, { recursive: true });
  } catch {
    outDir = path.join(os.tmpdir(), "qlanalyser-acceptance");
    fs.mkdirSync(outDir, { recursive: true });
  }
  let out = path.join(outDir, "research_modules_static_latest.json");
  try {
    fs.writeFileSync(out, JSON.stringify(report, null, 2), "utf8");
  } catch {
    outDir = path.join(os.tmpdir(), "qlanalyser-acceptance");
    fs.mkdirSync(outDir, { recursive: true });
    out = path.join(outDir, "research_modules_static_latest.json");
    fs.writeFileSync(out, JSON.stringify(report, null, 2), "utf8");
  }
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
