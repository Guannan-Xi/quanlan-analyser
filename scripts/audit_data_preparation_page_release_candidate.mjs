import fs from "node:fs";
import path from "node:path";
import { chromium, chromiumLaunchOptions } from "./lib/playwright_runtime.mjs";

const repoRoot = process.cwd();
const evidenceDir = process.env.QLANALYSER_DATA_PREP_RC_AUDIT_DIR
  || path.join(repoRoot, "work", "release_evidence", "20260628-data-preparation-page-rc-audit");
const outputPath = path.join(evidenceDir, "data_preparation_page_rc_audit.json");
const frontendUrl = process.env.QLANALYSER_DATA_PREP_RC_AUDIT_URL
  || "http://127.0.0.1:4174/?customer_demo=auto&teaching_demo=auto&api=http%3A%2F%2F127.0.0.1%3A8001%2Fapi&v=data-prep-rc-audit#analysis";

fs.mkdirSync(evidenceDir, { recursive: true });

const viewports = [
  { id: "desktop_1440", width: 1440, height: 900 },
  { id: "laptop_1280", width: 1280, height: 820 },
  { id: "mobile_390", width: 390, height: 844 },
];

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

async function waitForCanvasReady(page) {
  await page.goto(frontendUrl, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForSelector("#eegCanvas", { timeout: 60000 });
  await page.waitForFunction(() => {
    const debug = window.qlanalyserWaveformDebug || {};
    return debug.lastPreviewSource === "waveform_chunk_api" || debug.lastPreviewStatus === "chunk-ready";
  }, null, { timeout: 60000 });
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
}

async function auditViewport(browser, viewport) {
  const page = await browser.newPage({ viewport: { width: viewport.width, height: viewport.height } });
  const screenshotPath = path.join(evidenceDir, `data_prep_rc_${viewport.id}.png`);
  const network = { chunk: 0, qcTask: 0 };
  page.on("response", (response) => {
    const url = response.url();
    const req = response.request();
    if (url.includes("/api/eeg/files/") && url.includes("/waveform/chunk")) network.chunk += 1;
    if (url.endsWith("/api/tasks") && req.method() === "POST" && (req.postData() || "").includes('"qc_waveform_preview"')) network.qcTask += 1;
  });

  await waitForCanvasReady(page);
  const snapshot = await page.evaluate((viewportId) => {
    const visible = (selector) => {
      const node = document.querySelector(selector);
      if (!node) return false;
      const style = window.getComputedStyle(node);
      const rect = node.getBoundingClientRect();
      return style.visibility !== "hidden" && style.display !== "none" && rect.width > 0 && rect.height > 0;
    };
    const visibleText = (selector) => {
      const node = document.querySelector(selector);
      if (!node) return "";
      const walker = document.createTreeWalker(node, NodeFilter.SHOW_TEXT);
      const chunks = [];
      while (walker.nextNode()) {
        const parent = walker.currentNode.parentElement;
        if (!parent) continue;
        const style = window.getComputedStyle(parent);
        const rect = parent.getBoundingClientRect();
        if (style.visibility === "hidden" || style.display === "none" || rect.width <= 1 || rect.height <= 1) continue;
        const text = walker.currentNode.textContent.trim();
        if (text) chunks.push(text);
      }
      return chunks.join(" ");
    };
    const action = (selector) => {
      const node = document.querySelector(selector);
      return {
        exists: Boolean(node),
        visible: Boolean(node && visible(selector)),
        disabled: Boolean(node?.disabled || node?.getAttribute("aria-disabled") === "true"),
        text: node?.textContent?.trim() || "",
      };
    };
    const rectOf = (selector) => {
      const node = document.querySelector(selector);
      if (!node) return null;
      const r = node.getBoundingClientRect();
      return { x: r.x, y: r.y, width: r.width, height: r.height, bottom: r.bottom };
    };
    return {
      viewportId,
      title: document.querySelector("h1")?.textContent?.trim() || "",
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
      bodyText: document.body.textContent || "",
      analysisText: visibleText("#analysis"),
      stepCards: document.querySelectorAll(".ia-step-card").length,
      dataCardVisible: visible('[data-testid="project-data-crud-panel"], .ia-data-list-card, [data-file-select]'),
      canvasVisible: visible("#eegCanvas"),
      canvasRect: rectOf("#eegCanvas"),
      toolbarVisible: visible(".eeg-toolbar"),
      timeSliderVisible: visible("#eegTimeSlider"),
      timeSliderDisabled: Boolean(document.querySelector("#eegTimeSlider")?.disabled),
      workbenchLinkVisible: visible('[data-testid="open-waveform-workbench-clean"]'),
      rightPanelVisible: visible(".workbench-action-panel"),
      advancedReferenceCollapsed: !Boolean(document.querySelector(".prep-advanced-settings")?.open),
      hiddenOldEditWorkbench: !visible('[data-testid="preview-edit-workbench"]'),
      staticImages: document.querySelectorAll('[data-testid="single-file-preview-panel"] img, .eeg-viewer img').length,
      visibleCurrentWindowCount: (visibleText("#analysis").match(/当前窗口/g) || []).length,
      visibleConfirmedPlanInWaveformStatus: /方案|已确认\s*r/i.test(document.querySelector("#waveformWorkbenchStatus")?.textContent || ""),
      addCandidate: action('.prep-side-action-grid [data-ia-action="add-candidate-bad-segment"]'),
      confirmCandidate: action('.prep-side-action-grid [data-ia-action="confirm-candidate-bad-segments"]'),
      restoreSegment: action('.prep-side-action-grid [data-ia-action="restore-segment"]'),
      markBadChannel: action('.prep-side-action-grid [data-ia-action="mark-bad-channel"]'),
      confirmPlan: action('.prep-confirm-actions [data-real-action="confirm-plan-inline"], [data-real-action="confirm-plan-inline"]'),
      eventPanelVisible: visible('[data-testid="event-epoch-panel"]'),
      nextPanelVisible: visible('[data-testid="data-preparation-submit-last"]'),
    };
  }, viewport.id);
  const ink = await page.evaluate(canvasInkMetricScript);
  await page.screenshot({ path: screenshotPath, fullPage: true });
  await page.close();
  return { viewport, screenshotPath, network, snapshot, ink };
}

async function auditInteraction(browser) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const network = { chunk: 0, qcTask: 0 };
  page.on("response", (response) => {
    const url = response.url();
    const req = response.request();
    if (url.includes("/api/eeg/files/") && url.includes("/waveform/chunk")) network.chunk += 1;
    if (url.endsWith("/api/tasks") && req.method() === "POST" && (req.postData() || "").includes('"qc_waveform_preview"')) network.qcTask += 1;
  });
  await waitForCanvasReady(page);
  const before = await page.evaluate(() => ({
    slider: Number(document.querySelector("#eegTimeSlider")?.value || 0),
    sliderMax: Number(document.querySelector("#eegTimeSlider")?.max || 0),
    addDisabled: Boolean(document.querySelector('.prep-side-action-grid [data-ia-action="add-candidate-bad-segment"]')?.disabled),
    confirmDisabled: Boolean(document.querySelector('.prep-side-action-grid [data-ia-action="confirm-candidate-bad-segments"]')?.disabled),
    status: document.querySelector("#waveformWorkbenchStatus")?.textContent || "",
    hint: document.querySelector("#mainPrepActionHint")?.textContent || "",
  }));
  await page.locator("#eegCanvas").hover();
  await page.mouse.wheel(420, 0);
  await page.waitForTimeout(800);
  const afterWheel = await page.evaluate(() => ({
    slider: Number(document.querySelector("#eegTimeSlider")?.value || 0),
    navigator: document.querySelector("#eegNavigatorLabel")?.textContent || "",
    status: document.querySelector("#waveformWorkbenchStatus")?.textContent || "",
  }));
  await page.locator("#eegTimeSlider").evaluate((node) => {
    node.value = String(Math.min(Number(node.max || 0), Number(node.value || 0) + 5));
    node.dispatchEvent(new Event("input", { bubbles: true }));
    node.dispatchEvent(new Event("change", { bubbles: true }));
  });
  await page.waitForTimeout(1000);
  const afterSlider = await page.evaluate(() => ({
    slider: Number(document.querySelector("#eegTimeSlider")?.value || 0),
    navigator: document.querySelector("#eegNavigatorLabel")?.textContent || "",
  }));
  await page.getByTestId("waveform-mode-select-segment").click();
  const box = await page.locator("#eegCanvas").boundingBox();
  if (!box) throw new Error("Canvas bounding box missing");
  await page.mouse.move(box.x + box.width * 0.35, box.y + box.height * 0.42);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * 0.55, box.y + box.height * 0.42, { steps: 8 });
  await page.mouse.up();
  await page.waitForTimeout(400);
  const afterSelect = await page.evaluate(() => ({
    addDisabled: Boolean(document.querySelector('.prep-side-action-grid [data-ia-action="add-candidate-bad-segment"]')?.disabled),
    confirmDisabled: Boolean(document.querySelector('.prep-side-action-grid [data-ia-action="confirm-candidate-bad-segments"]')?.disabled),
    hint: document.querySelector("#mainPrepActionHint")?.textContent || "",
    status: document.querySelector("#waveformWorkbenchStatus")?.textContent || "",
  }));
  await page.locator('.prep-side-action-grid [data-ia-action="add-candidate-bad-segment"]').click();
  await page.waitForTimeout(300);
  const afterCandidate = await page.evaluate(() => ({
    confirmDisabled: Boolean(document.querySelector('.prep-side-action-grid [data-ia-action="confirm-candidate-bad-segments"]')?.disabled),
    draft: document.querySelector("#mainPrepDraftSummary")?.textContent || "",
    hint: document.querySelector("#mainPrepActionHint")?.textContent || "",
  }));
  await page.locator('.prep-side-action-grid [data-ia-action="confirm-candidate-bad-segments"]').click();
  await page.waitForTimeout(300);
  const afterConfirmCandidate = await page.evaluate(() => ({
    restoreDisabled: Boolean(document.querySelector('.prep-side-action-grid [data-ia-action="restore-segment"]')?.disabled),
    draft: document.querySelector("#mainPrepDraftSummary")?.textContent || "",
    hint: document.querySelector("#mainPrepActionHint")?.textContent || "",
  }));
  const screenshotPath = path.join(evidenceDir, "data_prep_rc_interaction_flow.png");
  await page.screenshot({ path: screenshotPath, fullPage: true });
  await page.close();
  return { network, before, afterWheel, afterSlider, afterSelect, afterCandidate, afterConfirmCandidate, screenshotPath };
}

function evaluateEvidence(evidence) {
  const checks = {};
  const desktop = evidence.viewports.find((item) => item.viewport.id === "desktop_1440");
  const laptop = evidence.viewports.find((item) => item.viewport.id === "laptop_1280");
  const mobile = evidence.viewports.find((item) => item.viewport.id === "mobile_390");
  const allViewports = evidence.viewports;
  checks.global_title_data_preparation = allViewports.every((item) => item.snapshot.title.includes("数据准备"));
  checks.global_no_horizontal_overflow = allViewports.every((item) => item.snapshot.scrollWidth <= item.snapshot.clientWidth + 2);
  checks.global_no_static_image_preview = allViewports.every((item) => item.snapshot.staticImages === 0);
  checks.global_canvas_visible_and_nonblank = allViewports.every((item) => item.snapshot.canvasVisible && item.ink.nonWhite > 1000);
  checks.global_no_qc_task_for_initial_canvas = allViewports.every((item) => item.network.qcTask === 0);
  checks.global_chunk_api_used = allViewports.every((item) => item.network.chunk > 0);
  checks.section_step_cards_present = allViewports.every((item) => item.snapshot.stepCards >= 5);
  checks.section_waveform_toolbar_slider_present = allViewports.every((item) => item.snapshot.toolbarVisible && item.snapshot.timeSliderVisible);
  checks.section_right_action_panel_present = Boolean(desktop?.snapshot.rightPanelVisible && laptop?.snapshot.rightPanelVisible);
  checks.section_old_duplicate_edit_workbench_hidden = allViewports.every((item) => item.snapshot.hiddenOldEditWorkbench);
  checks.section_advanced_reference_collapsed = Boolean(desktop?.snapshot.advancedReferenceCollapsed);
  checks.section_secondary_record_panels_present = Boolean(desktop?.snapshot.eventPanelVisible && desktop?.snapshot.nextPanelVisible);
  checks.function_preconditions_disable_write_actions = evidence.interaction.before.addDisabled && evidence.interaction.before.confirmDisabled;
  checks.function_wheel_pan_safe_status = evidence.interaction.network.chunk >= 2 && !/方案|已确认\s*r/i.test(evidence.interaction.afterWheel.status || "");
  checks.function_slider_drag_changes_position = evidence.interaction.before.sliderMax > 0 && evidence.interaction.afterSlider.slider > evidence.interaction.before.slider;
  checks.function_canvas_selection_enables_candidate = evidence.interaction.afterSelect.addDisabled === false && /当前选区|选区/.test(`${evidence.interaction.afterSelect.hint} ${evidence.interaction.afterSelect.status}`);
  checks.function_candidate_enables_confirm = evidence.interaction.afterCandidate.confirmDisabled === false && evidence.interaction.afterCandidate.draft.includes("候选坏段");
  checks.function_confirm_candidate_enables_restore = evidence.interaction.afterConfirmCandidate.restoreDisabled === false && evidence.interaction.afterConfirmCandidate.draft.includes("已确认剔除");
  checks.business_flow_primary_path_complete = [
    checks.function_preconditions_disable_write_actions,
    checks.function_wheel_pan_safe_status,
    checks.function_slider_drag_changes_position,
    checks.function_canvas_selection_enables_candidate,
    checks.function_candidate_enables_confirm,
    checks.function_confirm_candidate_enables_restore,
  ].every(Boolean);
  checks.business_flow_analysis_entry_preserved = Boolean(desktop?.snapshot.nextPanelVisible);
  checks.mobile_canvas_reachable = Boolean(mobile?.snapshot.canvasVisible && mobile.snapshot.canvasRect?.y < 1400);
  evidence.checks = checks;
  evidence.failed = Object.entries(checks).filter(([, value]) => !value).map(([key]) => key);
  evidence.status = evidence.failed.length ? "failed" : "passed";
}

async function main() {
  const evidence = {
    status: "running",
    generated_at: new Date().toISOString(),
    frontendUrl,
    viewports: [],
    interaction: null,
    checks: {},
    failed: [],
    errors: [],
  };
  const browser = await chromium.launch(chromiumLaunchOptions({ headless: true }));
  try {
    for (const viewport of viewports) {
      evidence.viewports.push(await auditViewport(browser, viewport));
    }
    evidence.interaction = await auditInteraction(browser);
    evaluateEvidence(evidence);
  } catch (error) {
    evidence.status = "failed";
    evidence.errors.push(error.stack || String(error));
  } finally {
    fs.writeFileSync(outputPath, `${JSON.stringify(evidence, null, 2)}\n`, "utf8");
    await browser.close().catch(() => {});
  }
  console.log(JSON.stringify({
    status: evidence.status,
    outputPath,
    failed: evidence.failed,
    screenshots: [
      ...evidence.viewports.map((item) => item.screenshotPath),
      evidence.interaction?.screenshotPath,
    ].filter(Boolean),
  }, null, 2));
  if (evidence.status !== "passed") process.exit(1);
}

main().catch((error) => {
  fs.writeFileSync(outputPath, `${JSON.stringify({ status: "failed", error: error.stack || String(error), frontendUrl }, null, 2)}\n`, "utf8");
  console.error(error.stack || String(error));
  process.exit(1);
});
