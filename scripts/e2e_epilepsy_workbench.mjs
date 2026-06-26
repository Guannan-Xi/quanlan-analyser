import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";

const require = createRequire(import.meta.url);
const { chromium } = require("../frontend/node_modules/playwright");

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1")), "..");
const CHROME_EXE = "C:/Users/XGN/AppData/Local/Google/Chrome/Application/chrome.exe";
const FRONTEND_URL = process.env.QLANALYSER_EPILEPSY_WORKBENCH_URL
  || "http://127.0.0.1:4174/epilepsy-workbench.html?api=http://127.0.0.1:8001/api&mode=ml_epoch_classifier";
const OUT_DIR = process.env.QLANALYSER_EPILEPSY_WORKBENCH_EVIDENCE_DIR
  || path.join(ROOT, "work/e2e_epilepsy_workbench/ui_e2e");
const EVIDENCE_PATH = path.join(OUT_DIR, "epilepsy_workbench_e2e.json");

function ensure(condition, message) {
  if (!condition) throw new Error(message);
}

async function main() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const evidence = {
    status: "running",
    frontend_url: FRONTEND_URL,
    requests: [],
    responses: [],
    screenshots: {},
    task: null,
    waveformTask: null,
    checks: {},
  };

  const launchOptions = { headless: true };
  if (fs.existsSync(CHROME_EXE)) launchOptions.executablePath = CHROME_EXE;
  const browser = await chromium.launch(launchOptions);
  const page = await browser.newPage({ viewport: { width: 1440, height: 1200 } });

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
    await page.waitForSelector('[data-testid="epilepsy-file-select"]', { timeout: 30000 });
    await page.click("#selectEpilepsyFixtureBtn");
    await page.screenshot({ path: path.join(OUT_DIR, "01_workbench_loaded.png"), fullPage: true });
    evidence.screenshots.loaded = path.join(OUT_DIR, "01_workbench_loaded.png");

    const epilepsyTaskPromise = page.waitForResponse(
      (response) => response.url().endsWith("/api/tasks")
        && response.request().method() === "POST"
        && (response.request().postData() || "").includes('"module_name":"epilepsy_ml"'),
      { timeout: 120000 },
    );
    await page.click('[data-testid="epilepsy-run"]');
    const epilepsyTask = await (await epilepsyTaskPromise).json();
    evidence.task = epilepsyTask;
    ensure(epilepsyTask.status === "completed", `Epilepsy task not completed: ${epilepsyTask.status}`);
    ensure(epilepsyTask.module_name === "epilepsy_ml", "Workbench did not submit epilepsy_ml module.");
    ensure(epilepsyTask.workflow_id === "epilepsy_ml_xgboost", "Workbench did not submit epilepsy_ml_xgboost.");

    await page.waitForFunction(() => document.body.innerText.includes("工作台分析完成"), null, { timeout: 60000 });
    await page.waitForSelector("#visibleEpochCountSelect", { timeout: 30000 });
    await page.waitForSelector("#applyStageNormalBtn", { timeout: 30000 });
    await page.waitForSelector('[data-testid="epilepsy-event-table"] tbody tr', { timeout: 30000 });
    const eventRows = await page.locator('[data-testid="epilepsy-event-table"] tbody tr').count();
    ensure(eventRows >= 1, "No candidate event rows rendered.");

    await page.click("#markNormalBtn");
    await page.waitForFunction(() => document.body.innerText.includes("0 个候选事件"), null, { timeout: 30000 });
    const correctedState = await page.evaluate(() => {
      const keys = Object.keys(localStorage).filter((key) => key.startsWith("qlanalyser.epilepsy.review.v1."));
      return Object.fromEntries(keys.map((key) => [key, localStorage.getItem(key)]));
    });
    evidence.correctedState = correctedState;
    ensure(Object.values(correctedState).some((text) => String(text).includes('"epochOverrides"')), "Epoch override state was not saved.");
    ensure(Object.values(correctedState).some((text) => String(text).includes('"set_stage"')), "Stage correction action was not recorded.");

    await page.click("#sourceUndoBtn");
    await page.waitForSelector('[data-testid="epilepsy-event-table"] tbody tr', { timeout: 30000 });
    const restoredEventRows = await page.locator('[data-testid="epilepsy-event-table"] tbody tr').count();
    ensure(restoredEventRows >= 1, "Undo did not restore candidate event rows.");

    await page.click("#markSeizureBtn");
    await page.waitForFunction(() => document.body.innerText.includes("Seizure"), null, { timeout: 30000 });
    const reviewState = await page.evaluate(() => {
      const keys = Object.keys(localStorage).filter((key) => key.startsWith("qlanalyser.epilepsy.review.v1."));
      return Object.fromEntries(keys.map((key) => [key, localStorage.getItem(key)]));
    });
    evidence.reviewState = reviewState;

    const waveformTaskPromise = page.waitForResponse(
      (response) => response.url().endsWith("/api/tasks")
        && response.request().method() === "POST"
        && (response.request().postData() || "").includes('"workflow_id":"qc_waveform_preview"'),
      { timeout: 120000 },
    );
    await page.click("#runWaveformBtn");
    const waveformTask = await (await waveformTaskPromise).json();
    evidence.waveformTask = waveformTask;
    ensure(waveformTask.status === "completed", `Waveform task not completed: ${waveformTask.status}`);
    await page.waitForSelector('[data-testid="epilepsy-waveform-frame"] img', { timeout: 60000 });

    await page.screenshot({ path: path.join(OUT_DIR, "02_after_workbench_run.png"), fullPage: true });
    evidence.screenshots.after_run = path.join(OUT_DIR, "02_after_workbench_run.png");

    const bodyText = await page.locator("body").innerText();
    evidence.checks = {
      pageTitleVisible: bodyText.includes("癫痫样事件分析工作台"),
      taskCompleted: epilepsyTask.status === "completed",
      moduleName: epilepsyTask.module_name,
      workflowId: epilepsyTask.workflow_id,
      eventRows,
      correctedEventRowsAfterNormal: 0,
      restoredEventRows,
      reviewSaved: Object.values(reviewState).some((text) => String(text).includes("seizure_candidate")),
      epochCorrectionSaved: Object.values(correctedState).some((text) => String(text).includes('"epochOverrides"')),
      stageActionRecorded: Object.values(correctedState).some((text) => String(text).includes('"set_stage"')),
      waveformCompleted: waveformTask.status === "completed",
      waveformImageVisible: await page.locator('[data-testid="epilepsy-waveform-frame"] img').count() > 0,
      nonMedicalBoundary: bodyText.includes("不用于诊断"),
    };
    ensure(evidence.checks.reviewSaved, "Manual review was not saved to localStorage.");
    ensure(evidence.checks.epochCorrectionSaved, "Epoch-level correction was not saved to localStorage.");
    ensure(evidence.checks.stageActionRecorded, "Epoch-level correction action was not recorded.");
    ensure(evidence.checks.waveformImageVisible, "Waveform preview image is not visible.");
    ensure(evidence.checks.nonMedicalBoundary, "Non-medical boundary not visible.");

    evidence.status = "PASS";
    fs.writeFileSync(EVIDENCE_PATH, `${JSON.stringify(evidence, null, 2)}\n`, "utf8");
    console.log(JSON.stringify({
      status: evidence.status,
      evidence_path: EVIDENCE_PATH,
      task_id: epilepsyTask.id,
      waveform_task_id: waveformTask.id,
      event_rows: eventRows,
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
