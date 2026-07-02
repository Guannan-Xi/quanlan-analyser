import fs from "node:fs";
import path from "node:path";
import { chromium, chromiumLaunchOptions } from "./lib/playwright_runtime.mjs";

const repoRoot = process.cwd();
const evidenceDir = process.env.QLANALYSER_MAIN_CANVAS_CHUNK_EVIDENCE
  || path.join(repoRoot, "work", "release_evidence", "20260628-main-data-prep-canvas-chunk");
const outputPath = path.join(evidenceDir, "main_data_prep_canvas_chunk_interaction.json");
const screenshotPath = path.join(evidenceDir, "main_data_prep_canvas_chunk_interaction.png");
const frontendUrl = process.env.QLANALYSER_MAIN_CANVAS_CHUNK_URL
  || "http://127.0.0.1:4174/?customer_demo=auto&teaching_demo=auto&api=http%3A%2F%2F127.0.0.1%3A8001%2Fapi&v=main-epilepsy-entry#analysis";
const addCandidateSelector = '.prep-side-action-grid [data-ia-action="add-candidate-bad-segment"]';
const confirmCandidateSelector = '.prep-side-action-grid [data-ia-action="confirm-candidate-bad-segments"]';

fs.mkdirSync(evidenceDir, { recursive: true });

function canvasInkMetricScript() {
  const canvas = document.querySelector("#eegCanvas");
  if (!canvas) return { exists: false, nonWhite: 0, width: 0, height: 0 };
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;
  const sampleWidth = Math.min(width, 900);
  const sampleHeight = Math.min(height, 500);
  const data = ctx.getImageData(0, 0, sampleWidth, sampleHeight).data;
  let nonWhite = 0;
  for (let i = 0; i < data.length; i += 4) {
    const r = data[i];
    const g = data[i + 1];
    const b = data[i + 2];
    const a = data[i + 3];
    if (a > 0 && (r < 245 || g < 245 || b < 245)) nonWhite += 1;
  }
  return { exists: true, nonWhite, width, height };
}

const evidence = {
  status: "running",
  generated_at: new Date().toISOString(),
  frontendUrl,
  network: { chunk: 0, qcTask: 0 },
  checks: {},
  screenshots: { canvas: screenshotPath },
  errors: [],
};

const browser = await chromium.launch(chromiumLaunchOptions({ headless: true }));
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

try {
  page.on("response", (response) => {
    const url = response.url();
    const req = response.request();
    if (url.includes("/api/eeg/files/") && url.includes("/waveform/chunk")) evidence.network.chunk += 1;
    if (url.endsWith("/api/tasks") && req.method() === "POST" && (req.postData() || "").includes('"qc_waveform_preview"')) evidence.network.qcTask += 1;
  });

  await page.goto(frontendUrl, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForSelector("#eegCanvas", { timeout: 60000 });
  await page.waitForFunction(() => window.qlanalyserWaveformDebug?.lastPreviewSource === "waveform_chunk_api" || window.qlanalyserWaveformDebug?.lastPreviewStatus === "chunk-ready", null, { timeout: 60000 });
  await page.waitForFunction(() => {
    const canvas = document.querySelector("#eegCanvas");
    if (!canvas) return false;
    const ctx = canvas.getContext("2d");
    const data = ctx.getImageData(0, 0, Math.min(canvas.width, 500), Math.min(canvas.height, 300)).data;
    for (let i = 0; i < data.length; i += 4) {
      if (data[i + 3] > 0 && (data[i] < 245 || data[i + 1] < 245 || data[i + 2] < 245)) return true;
    }
    return false;
  }, null, { timeout: 60000 });

  const before = await page.evaluate(canvasInkMetricScript);
  const beforeDebug = await page.evaluate(() => window.qlanalyserWaveformDebug || {});
  const beforeUi = await page.evaluate(() => ({
    sliderValue: Number(document.querySelector("#eegTimeSlider")?.value || 0),
    sliderMax: Number(document.querySelector("#eegTimeSlider")?.max || 0),
    addCandidateDisabled: Boolean(document.querySelector('.prep-side-action-grid [data-ia-action="add-candidate-bad-segment"]')?.disabled),
    confirmCandidateDisabled: Boolean(document.querySelector('.prep-side-action-grid [data-ia-action="confirm-candidate-bad-segments"]')?.disabled),
    staticImages: document.querySelectorAll('[data-testid="single-file-preview-panel"] img, .eeg-viewer img').length,
    actionHint: document.querySelector("#mainPrepActionHint")?.textContent || "",
    draftSummary: document.querySelector("#mainPrepDraftSummary")?.textContent || "",
    workbenchLink: document.querySelector('[data-testid="open-waveform-workbench-clean"]')?.getAttribute("href") || "",
  }));
  await page.locator("#eegCanvas").hover();
  await page.mouse.wheel(0, 420);
  const wheelStatusSamples = [];
  for (let i = 0; i < 6; i += 1) {
    wheelStatusSamples.push(await page.evaluate(() => document.querySelector("#waveformWorkbenchStatus")?.textContent || ""));
    await page.waitForTimeout(180);
  }
  await page.waitForTimeout(1200);
  const afterWheel = await page.evaluate(() => ({
    debug: window.qlanalyserWaveformDebug || {},
    start: Number(document.querySelector("#eegStartInput")?.value || 0),
    meta: document.querySelector("#eegMeta")?.textContent || "",
    navigator: document.querySelector("#eegNavigatorLabel")?.textContent || "",
    waveformStatus: document.querySelector("#waveformWorkbenchStatus")?.textContent || "",
  }));
  const slider = page.locator("#eegTimeSlider");
  await slider.evaluate((node) => {
    node.value = String(Math.min(Number(node.max || 0), Number(node.value || 0) + 5));
    node.dispatchEvent(new Event("input", { bubbles: true }));
    node.dispatchEvent(new Event("change", { bubbles: true }));
  });
  await page.waitForTimeout(1500);
  const afterSlider = await page.evaluate(() => ({
    debug: window.qlanalyserWaveformDebug || {},
    start: Number(document.querySelector("#eegStartInput")?.value || 0),
    meta: document.querySelector("#eegMeta")?.textContent || "",
    navigator: document.querySelector("#eegNavigatorLabel")?.textContent || "",
    sliderValue: Number(document.querySelector("#eegTimeSlider")?.value || 0),
    ink: (() => {
      const canvas = document.querySelector("#eegCanvas");
      if (!canvas) return { exists: false, nonWhite: 0, width: 0, height: 0 };
      const ctx = canvas.getContext("2d");
      const width = canvas.width;
      const height = canvas.height;
      const sampleWidth = Math.min(width, 900);
      const sampleHeight = Math.min(height, 500);
      const data = ctx.getImageData(0, 0, sampleWidth, sampleHeight).data;
      let nonWhite = 0;
      for (let i = 0; i < data.length; i += 4) {
        const r = data[i];
        const g = data[i + 1];
        const b = data[i + 2];
        const a = data[i + 3];
        if (a > 0 && (r < 245 || g < 245 || b < 245)) nonWhite += 1;
      }
      return { exists: true, nonWhite, width, height };
    })(),
    imageCount: document.querySelectorAll('[data-testid="single-file-preview-panel"] img, .eeg-viewer img').length,
  }));

  await page.getByTestId("waveform-mode-select-segment").click();
  const box = await page.locator("#eegCanvas").boundingBox();
  if (!box) throw new Error("Canvas bounding box missing");
  await page.mouse.move(box.x + box.width * 0.35, box.y + box.height * 0.40);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * 0.55, box.y + box.height * 0.40, { steps: 8 });
  await page.mouse.up();
  await page.waitForTimeout(500);
  const afterSelect = await page.evaluate(() => ({
    addCandidateDisabled: Boolean(document.querySelector('.prep-side-action-grid [data-ia-action="add-candidate-bad-segment"]')?.disabled),
    confirmCandidateDisabled: Boolean(document.querySelector('.prep-side-action-grid [data-ia-action="confirm-candidate-bad-segments"]')?.disabled),
    actionHint: document.querySelector("#mainPrepActionHint")?.textContent || "",
    draftSummary: document.querySelector("#mainPrepDraftSummary")?.textContent || "",
    status: document.querySelector("#waveformWorkbenchStatus")?.textContent || "",
    selectedStart: Number(document.querySelector("#segmentStart")?.value || 0),
    selectedEnd: Number(document.querySelector("#segmentEnd")?.value || 0),
  }));
  await page.locator(addCandidateSelector).click();
  await page.waitForTimeout(300);
  const afterCandidate = await page.evaluate(() => ({
    addCandidateDisabled: Boolean(document.querySelector('.prep-side-action-grid [data-ia-action="add-candidate-bad-segment"]')?.disabled),
    confirmCandidateDisabled: Boolean(document.querySelector('.prep-side-action-grid [data-ia-action="confirm-candidate-bad-segments"]')?.disabled),
    actionHint: document.querySelector("#mainPrepActionHint")?.textContent || "",
    draftSummary: document.querySelector("#mainPrepDraftSummary")?.textContent || "",
    status: document.querySelector("#waveformWorkbenchStatus")?.textContent || "",
  }));

  await page.screenshot({ path: screenshotPath, fullPage: true });

  evidence.before = { canvas: before, debug: beforeDebug };
  evidence.beforeUi = beforeUi;
  evidence.wheelStatusSamples = wheelStatusSamples;
  evidence.afterWheel = afterWheel;
  evidence.afterSlider = afterSlider;
  evidence.afterSelect = afterSelect;
  evidence.afterCandidate = afterCandidate;
  evidence.checks.chunk_api_used = evidence.network.chunk > 0 || beforeDebug.lastPreviewSource === "waveform_chunk_api" || beforeDebug.lastPreviewStatus === "chunk-ready";
  evidence.checks.no_qc_task_for_initial_canvas = evidence.network.qcTask === 0;
  evidence.checks.canvas_non_blank = before.nonWhite > 1000 && afterSlider.ink.nonWhite > 1000;
  evidence.checks.no_static_image_preview = afterSlider.imageCount === 0;
  evidence.checks.interaction_updates_canvas_state = afterWheel.meta.includes("当前窗口") || afterSlider.meta.includes("当前窗口");
  evidence.checks.slider_drag_changes_position = beforeUi.sliderMax > 0 && afterSlider.sliderValue > beforeUi.sliderValue;
  evidence.checks.wheel_pan_requests_chunk = evidence.network.chunk >= 2 && afterWheel.navigator !== "";
  evidence.checks.wheel_status_not_plan_confirmation = !/方案|已确认\s*r/i.test(afterWheel.waveformStatus || "");
  evidence.checks.wheel_status_has_no_transient_loading_line = wheelStatusSamples.every((text) => !/正在读取|正在恢复|正在更新|Canvas 波形|时间窗|滑块位置|波形预览/.test(text || ""));
  evidence.checks.add_candidate_disabled_until_selection = beforeUi.addCandidateDisabled === true && afterSelect.addCandidateDisabled === false;
  evidence.checks.confirm_candidate_enabled_after_candidate = afterCandidate.confirmCandidateDisabled === false && afterCandidate.draftSummary.includes("候选坏段");
  evidence.checks.right_panel_reflects_canvas_selection = afterSelect.actionHint.includes("当前选区") || afterSelect.status.includes("选区");
  evidence.checks.professional_workbench_entry_present = beforeUi.workbenchLink.includes("waveform-workbench.html");
  evidence.status = Object.values(evidence.checks).every(Boolean) ? "passed" : "failed";
} catch (error) {
  evidence.status = "failed";
  evidence.errors.push(error.stack || String(error));
} finally {
  fs.writeFileSync(outputPath, `${JSON.stringify(evidence, null, 2)}\n`, "utf8");
  await browser.close().catch(() => {});
}

console.log(JSON.stringify({ status: evidence.status, outputPath, screenshotPath, checks: evidence.checks, network: evidence.network }, null, 2));
if (evidence.status !== "passed") process.exit(1);
