import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";

const require = createRequire(import.meta.url);
const { chromium } = require("../frontend/node_modules/playwright");

const API_BASE = process.env.QLANALYSER_API_BASE_URL || "http://127.0.0.1:8001/api";
const FRONTEND_URL =
  process.env.QLANALYSER_FRONTEND_URL ||
  `http://127.0.0.1:4174/index.html?customer_demo=auto&api=${encodeURIComponent(API_BASE)}`;
const EVIDENCE_ROOT =
  process.env.QLANALYSER_TEACHING_INDEPENDENCE_EVIDENCE_ROOT ||
  path.resolve("work/release_evidence/20260626-teaching-mode-independent-product-design/implementation/browser_independence");
const SCREENSHOT_DIR = path.join(EVIDENCE_ROOT, "screenshots");
const EVIDENCE_PATH = path.join(EVIDENCE_ROOT, "browser_e2e.json");

function ensureDirs() {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

function localBrowserExecutable() {
  const candidates = [
    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  ];
  return candidates.find((candidate) => fs.existsSync(candidate)) || null;
}

async function visible(page, selector) {
  return page.locator(selector).first().isVisible().catch(() => false);
}

async function jsonResponse(response) {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

async function main() {
  ensureDirs();
  const checks = [];
  const screenshots = [];
  const add = (name, pass, details = {}) => checks.push({ name, pass: Boolean(pass), details });
  const executablePath = localBrowserExecutable();
  const browser = await chromium.launch({ headless: true, ...(executablePath ? { executablePath } : {}) });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });

  try {
    await page.goto(FRONTEND_URL, { waitUntil: "domcontentloaded", timeout: 60000 });
    await page.waitForSelector("#appShell, #loginScreen", { timeout: 30000 });
    if (await visible(page, "#customerLoginBtn")) {
      await page.click("#customerLoginBtn");
    }
    await page.waitForSelector("#appShell:not([hidden]), .main", { timeout: 30000 });
    const normalText = await page.locator("body").innerText();
    add("normal_mode_hides_regular_teaching_project", !normalText.includes("proj_demo_learning") && !normalText.includes("teaching_oddball"));
    add("normal_mode_hides_epilepsy_teaching_project", !normalText.includes("proj_demo_epilepsy_lab") && !normalText.includes("epilepsy_ml_demo_source_channels"));
    add("personal_center_visible_before_teaching", await visible(page, '[data-view="userCenter"]'));

    const normalShot = path.join(SCREENSHOT_DIR, "01_normal_mode.png");
    await page.screenshot({ path: normalShot, fullPage: true });
    screenshots.push(normalShot);

    await page.click("#teachingModeBtn");
    await page.waitForSelector("#teachingOverlay.active", { timeout: 30000 });
    await page.waitForTimeout(1200);
    await page.request.get(`${API_BASE}/lab/demo/epilepsy`);
    const teachingText = await page.locator("body").innerText();
    add("teaching_mode_loads_teaching_dataset", teachingText.includes("体验中心") || teachingText.includes("teaching_oddball") || teachingText.includes("合成 EEG"));
    add("archive_button_disabled_for_teaching_project", await page.locator('[data-ia-action="archive-project"]').first().isDisabled().catch(() => false));
    add("edit_button_disabled_for_teaching_project", await page.locator('[data-ia-action="edit-project"]').first().isDisabled().catch(() => false));
    const renameButton = page.locator('[data-ia-action="rename-data"]').first();
    const renameVisible = await renameButton.isVisible().catch(() => false);
    const renameDisabled = await renameButton.isDisabled().catch(() => false);
    add("rename_data_button_not_operable_for_teaching_file", !renameVisible || renameDisabled, { visible: renameVisible, disabled: renameDisabled });

    const teachingShot = path.join(SCREENSHOT_DIR, "02_teaching_mode_protected.png");
    await page.screenshot({ path: teachingShot, fullPage: true });
    screenshots.push(teachingShot);

    const archiveResponse = await page.request.post(`${API_BASE}/projects/proj_demo_learning/archive`);
    const archiveJson = await jsonResponse(archiveResponse);
    add("api_blocks_regular_teaching_project_archive", archiveResponse.status() === 409 && archiveJson?.detail?.code === "TEACHING_DATASET_PROTECTED", { status: archiveResponse.status(), body: archiveJson });

    const deleteResponse = await page.request.delete(`${API_BASE}/data/files/eeg_demo_teaching_oddball`);
    const deleteJson = await jsonResponse(deleteResponse);
    add("api_blocks_regular_teaching_file_delete", deleteResponse.status() === 409 && deleteJson?.detail?.code === "TEACHING_DATASET_PROTECTED", { status: deleteResponse.status(), body: deleteJson });

    const epilepsyDeleteResponse = await page.request.delete(`${API_BASE}/data/files/eeg_demo_epilepsy_high_amplitude`);
    const epilepsyDeleteJson = await jsonResponse(epilepsyDeleteResponse);
    add("api_blocks_epilepsy_teaching_file_delete", epilepsyDeleteResponse.status() === 409 && epilepsyDeleteJson?.detail?.code === "TEACHING_DATASET_PROTECTED", { status: epilepsyDeleteResponse.status(), body: epilepsyDeleteJson });

    const filesResponse = await page.request.get(`${API_BASE}/data/files`);
    const filesJson = await jsonResponse(filesResponse);
    const files = Array.isArray(filesJson) ? filesJson : [];
    const regularFile = files.find((item) => item.id === "eeg_demo_teaching_oddball");
    const epilepsyFile = files.find((item) => item.id === "eeg_demo_epilepsy_high_amplitude");
    add("regular_teaching_file_still_available", Boolean(regularFile && regularFile.status !== "deleted" && regularFile.upload_status !== "deleted"), { file: regularFile });
    add("epilepsy_teaching_file_still_available", Boolean(epilepsyFile && epilepsyFile.status !== "deleted" && epilepsyFile.upload_status !== "deleted"), { file: epilepsyFile });
  } catch (error) {
    add("unexpected_error", false, { message: error.message || String(error) });
  } finally {
    await browser.close();
  }

  const report = {
    script: path.basename(new URL(import.meta.url).pathname),
    frontend_url: FRONTEND_URL,
    api_base: API_BASE,
    generated_at: new Date().toISOString(),
    checks,
    screenshots,
    passed: checks.every((item) => item.pass),
  };
  fs.writeFileSync(EVIDENCE_PATH, `${JSON.stringify(report, null, 2)}\n`, "utf8");
  console.log(JSON.stringify(report, null, 2));
  process.exit(report.passed ? 0 : 1);
}

main();
