import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";

const require = createRequire(import.meta.url);
const { chromium } = require("../frontend/node_modules/playwright");

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1")), "..");
const CHROME_EXE = "C:/Users/XGN/AppData/Local/Google/Chrome/Application/chrome.exe";
const FRONTEND_URL = process.env.QLANALYSER_FRONTEND_URL || "http://127.0.0.1:4174/module-lab.html?customer_demo=login&api=http://127.0.0.1:8001/api";
const RAW_PATH = process.env.QLANALYSER_EPILEPSY_LAB_SAMPLE || path.join(ROOT, "work/e2e_epilepsy_std_demo/epilepsy_std_demo_high_amplitude_raw.fif");
const OUT_DIR = process.env.QLANALYSER_EPILEPSY_LAB_EVIDENCE_DIR || path.join(ROOT, "work/e2e_epilepsy_lab_sync_std/ui_e2e");
const EVIDENCE_PATH = path.join(OUT_DIR, "epilepsy_lab_sync_std_e2e.json");

function ensure(condition, message) {
  if (!condition) throw new Error(message);
}

function localArtifactPath(item) {
  if (!item?.path) return "";
  return String(item.path);
}

function readTextIfExists(filePath) {
  return filePath && fs.existsSync(filePath) ? fs.readFileSync(filePath, "utf8") : "";
}

async function main() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  ensure(fs.existsSync(RAW_PATH), `Missing epilepsy lab sample: ${RAW_PATH}`);

  const evidence = {
    status: "running",
    frontend_url: FRONTEND_URL,
    raw_path: RAW_PATH,
    output_dir: OUT_DIR,
    requests: [],
    responses: [],
    screenshots: {},
    selected_file_id: null,
    task: null,
    artifacts: [],
    checks: {},
  };

  const launchOptions = { headless: true };
  if (fs.existsSync(CHROME_EXE)) launchOptions.executablePath = CHROME_EXE;
  const browser = await chromium.launch(launchOptions);
  const page = await browser.newPage({ viewport: { width: 1440, height: 1400 } });

  page.on("request", (request) => {
    const url = request.url();
    if (url.includes("/api/")) {
      evidence.requests.push({ method: request.method(), url, body: request.postData() || "" });
    }
  });
  page.on("response", (response) => {
    const url = response.url();
    if (url.includes("/api/")) {
      evidence.responses.push({ status: response.status(), url });
    }
  });

  try {
    await page.goto(FRONTEND_URL, { waitUntil: "networkidle", timeout: 60000 });
    await page.waitForSelector("#labEegFile", { timeout: 30000 });

    await page.locator("#method-group-event-screening-research").scrollIntoViewIfNeeded();
    await page.locator('[data-target-method="epilepsy_lab_std"]').click();
    await page.waitForSelector('[data-runner-form="epilepsy_lab_std"]', { timeout: 15000 });
    await page.screenshot({ path: path.join(OUT_DIR, "01_lab_card.png"), fullPage: true });
    evidence.screenshots.lab_card = path.join(OUT_DIR, "01_lab_card.png");

    await page.fill("#labProjectName", "Epilepsy Lab Sync E2E Demo");
    await page.setInputFiles("#labEegFile", RAW_PATH);
    const uploadResponsePromise = page.waitForResponse(
      (response) => response.url().includes("/api/eeg/upload") && response.request().method() === "POST",
      { timeout: 90000 },
    );
    await page.click("#labUploadButton");
    const uploadJson = await (await uploadResponsePromise).json();
    evidence.upload = uploadJson;
    evidence.selected_file_id = uploadJson.id;
    await page.waitForFunction((fileId) => {
      const selects = [...document.querySelectorAll("[data-file-select]")];
      return selects.some((select) => [...select.options].some((option) => option.value === fileId));
    }, uploadJson.id, { timeout: 60000 });

    await page.locator("#method-group-event-screening-research").scrollIntoViewIfNeeded();
    await page.locator('[data-target-method="epilepsy_lab_std"]').click();
    const form = page.locator('[data-runner-form="epilepsy_lab_std"]');
    await form.locator('select[name="dataset"]').selectOption(uploadJson.id);
    await form.locator('input[name="epoch_length_sec"]').fill("5");
    await form.locator('input[name="std_factor"]').fill("2");
    await form.locator('input[name="rms_window_samples"]').fill("15");
    await form.locator('input[name="merge_gap_epoch_num"]').fill("1");
    await form.locator('input[name="min_event_epochs"]').fill("2");
    await form.locator('input[name="event_window_sec"]').fill("1800");
    await page.screenshot({ path: path.join(OUT_DIR, "02_after_upload.png"), fullPage: true });
    evidence.screenshots.after_upload = path.join(OUT_DIR, "02_after_upload.png");

    const taskResponsePromise = page.waitForResponse(
      (response) => response.url().endsWith("/api/tasks") && response.request().method() === "POST",
      { timeout: 120000 },
    );
    const artifactsResponsePromise = page.waitForResponse(
      (response) => response.url().includes("/api/tasks/") && response.url().endsWith("/artifacts"),
      { timeout: 120000 },
    );
    await form.locator('button[type="submit"]').click();

    const taskJson = await (await taskResponsePromise).json();
    evidence.task = taskJson;
    ensure(taskJson.module_name === "epilepsy", "Lab mirror did not submit module_name=epilepsy.");
    ensure(taskJson.workflow_id === "epilepsy_std_threshold", "Lab mirror did not submit epilepsy_std_threshold.");
    ensure(taskJson.status === "completed", `Task did not complete synchronously: ${taskJson.status}`);

    const artifacts = await (await artifactsResponsePromise).json();
    evidence.artifacts = artifacts;
    await page.waitForFunction(() => document.body.innerText.includes("epilepsy_events"), null, { timeout: 60000 });
    await page.screenshot({ path: path.join(OUT_DIR, "03_after_run.png"), fullPage: true });
    evidence.screenshots.after_run = path.join(OUT_DIR, "03_after_run.png");

    const labels = artifacts.map((item) => item.label || item.path || "");
    const summaryArtifact = artifacts.find((item) => String(item.label || "").includes("epilepsy_summary"));
    const eventsArtifact = artifacts.find((item) => String(item.label || "").includes("epilepsy_events"));
    const summaryText = readTextIfExists(localArtifactPath(summaryArtifact));
    const eventsText = readTextIfExists(localArtifactPath(eventsArtifact));
    const summary = summaryText ? JSON.parse(summaryText) : {};
    const eventRows = eventsText.trim() ? Math.max(0, eventsText.trim().split(/\r?\n/).length - 1) : 0;
    const taskRequestBody = evidence.requests.find((item) => item.method === "POST" && item.url.endsWith("/api/tasks"))?.body || "";

    evidence.checks = {
      labCardVisible: await page.locator('text=癫痫样事件筛查 / 实验室同步测试').count() > 0,
      uploadedFileVisible: true,
      selectedFileId: evidence.selected_file_id,
      moduleName: taskJson.module_name,
      workflowId: taskJson.workflow_id,
      taskCompleted: taskJson.status === "completed",
      labModeSubmitted: taskRequestBody.includes('"lab_mode":true'),
      labFixtureSubmitted: taskRequestBody.includes("epilepsy_std_demo_high_amplitude_v1"),
      syncMirrorNoteSubmitted: taskRequestBody.includes("ML high-fidelity migration pending"),
      nonMedicalBoundarySubmitted: taskRequestBody.includes("Research screening/support only"),
      epochScoresArtifact: labels.some((label) => label.includes("epilepsy_epoch_scores")),
      eventsArtifact: labels.some((label) => label.includes("epilepsy_events")),
      summaryArtifact: labels.some((label) => label.includes("epilepsy_summary")),
      eventCountFromSummary: summary.event_count,
      eventRows,
    };
    ensure(evidence.checks.labCardVisible, "Lab sync card was not visible.");
    ensure(evidence.checks.labModeSubmitted, "lab_mode was not submitted.");
    ensure(evidence.checks.labFixtureSubmitted, "lab_fixture_id was not submitted.");
    ensure(evidence.checks.syncMirrorNoteSubmitted, "sync_mirror_note was not submitted.");
    ensure(evidence.checks.nonMedicalBoundarySubmitted, "Non-medical boundary was not submitted.");
    ensure(evidence.checks.epochScoresArtifact, "Missing epilepsy_epoch_scores artifact.");
    ensure(evidence.checks.eventsArtifact, "Missing epilepsy_events artifact.");
    ensure(evidence.checks.summaryArtifact, "Missing epilepsy_summary artifact.");
    ensure(Number(summary.event_count || 0) >= 1 || eventRows >= 1, "Fixture did not produce candidate events.");

    evidence.status = "PASS";
    fs.writeFileSync(EVIDENCE_PATH, `${JSON.stringify(evidence, null, 2)}\n`, "utf8");
    console.log(JSON.stringify({
      status: evidence.status,
      evidence_path: EVIDENCE_PATH,
      task_id: taskJson.id,
      file_id: evidence.selected_file_id,
      artifact_count: artifacts.length,
      event_count: summary.event_count,
      screenshots: evidence.screenshots,
    }, null, 2));
  } catch (error) {
    evidence.status = "FAIL";
    evidence.error = String(error?.stack || error);
    try {
      await page.screenshot({ path: path.join(OUT_DIR, "failure.png"), fullPage: true });
      evidence.screenshots.failure = path.join(OUT_DIR, "failure.png");
    } catch {}
    fs.writeFileSync(EVIDENCE_PATH, `${JSON.stringify(evidence, null, 2)}\n`, "utf8");
    console.error(error);
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

main();
