import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";

const require = createRequire(import.meta.url);
const { chromium } = require("../frontend/node_modules/playwright");

const API_BASE = process.env.QLANALYSER_API_BASE_URL || "http://127.0.0.1:8001/api";
const TARGET_URL =
  process.env.QLANALYSER_FRONTEND_URL ||
  `http://127.0.0.1:4174/?customer_demo=login&api=${encodeURIComponent(API_BASE)}`;
const OUT_DIR =
  process.env.QLANALYSER_PROJECT_WAVEFORM_E2E_DIR ||
  path.resolve("work/release_evidence/07-full-product-e2e-pdca/14_waveform_preprocessing_project_cleanup/03_browser_e2e");
const EVIDENCE_PATH = path.join(OUT_DIR, "project_cleanup_waveform_preprocessing_e2e.json");

function check(name, pass, details = {}) {
  return { name, pass: Boolean(pass), details };
}

function localBrowserExecutable() {
  const candidates = [
    process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE,
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  ].filter(Boolean);
  return candidates.find((item) => fs.existsSync(item)) || "";
}

async function ensureLoggedIn(page) {
  await page.goto(TARGET_URL, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForTimeout(700);
  const loginButton = page.locator("#customerLoginBtn");
  if (await loginButton.isVisible().catch(() => false)) {
    await loginButton.click();
  }
  await page.locator("#appShell, .shell").first().waitFor({ state: "visible", timeout: 30000 });
}

async function viewportNoHorizontalOverflow(page) {
  return page.evaluate(() => {
    const root = document.documentElement;
    const body = document.body;
    const scrollWidth = Math.max(root.scrollWidth, body.scrollWidth);
    return { ok: scrollWidth <= root.clientWidth + 2, scrollWidth, clientWidth: root.clientWidth };
  });
}

async function textOf(page, selector) {
  return (await page.locator(selector).first().textContent().catch(() => ""))?.trim() || "";
}

async function waitForTeachingStep(page, marker) {
  await page.waitForFunction(
    (text) => document.querySelector("#teachingStepTitle")?.textContent.includes(text),
    marker,
    { timeout: 30000 },
  );
}

async function advanceTeachingTo(page, marker) {
  const nextButton = page.locator('#teachingOverlay [data-teaching-action="next"].primary-btn');
  for (let attempt = 0; attempt < 8; attempt += 1) {
    const currentTitle = await textOf(page, "#teachingStepTitle");
    if (currentTitle.includes(marker)) return;
    await nextButton.click();
    await page.waitForTimeout(800);
  }
  await waitForTeachingStep(page, marker);
}

async function hideTeachingOverlayForValidation(page) {
  await page.evaluate(() => {
    let style = document.querySelector("#e2eHideTeachingOverlayStyle");
    if (!style) {
      style = document.createElement("style");
      style.id = "e2eHideTeachingOverlayStyle";
      style.textContent = `
        #teachingOverlay,
        #teachingOverlay.active,
        .teaching-overlay,
        .teaching-overlay.active,
        .teaching-spotlight {
          display: none !important;
          visibility: hidden !important;
          opacity: 0 !important;
          pointer-events: none !important;
        }
      `;
      document.head.appendChild(style);
    }
    const overlay = document.querySelector("#teachingOverlay");
    overlay?.classList.remove("active");
    if (overlay) {
      overlay.hidden = true;
      overlay.setAttribute("aria-hidden", "true");
    }
    document.body.classList.remove("teaching-mode-active");
  });
  await page.waitForFunction(() => {
    const overlay = document.querySelector("#teachingOverlay");
    if (!overlay) return true;
    const style = getComputedStyle(overlay);
    return !overlay.classList.contains("active") && (overlay.hidden || style.display === "none" || style.visibility === "hidden" || Number(style.opacity) === 0);
  }, null, { timeout: 15000 });
}

async function canvasStats(page) {
  return page.locator("#eegCanvas").evaluate((canvas) => {
    const ctx = canvas.getContext("2d", { willReadFrequently: true });
    const width = canvas.width;
    const height = canvas.height;
    if (!ctx || !width || !height) return { ok: false, width, height, nonWhite: 0, sampled: 0 };
    const image = ctx.getImageData(0, 0, width, height).data;
    let sampled = 0;
    let nonWhite = 0;
    const step = Math.max(4, Math.floor(Math.sqrt((width * height) / 18000)));
    for (let y = 0; y < height; y += step) {
      for (let x = 0; x < width; x += step) {
        const i = (y * width + x) * 4;
        sampled += 1;
        const r = image[i];
        const g = image[i + 1];
        const b = image[i + 2];
        const a = image[i + 3];
        if (a > 0 && (r < 245 || g < 245 || b < 245)) nonWhite += 1;
      }
    }
    return { ok: nonWhite > 80, width, height, nonWhite, sampled };
  });
}

async function waitForWaveform(page) {
  await page.waitForFunction(() => {
    const activeView = document.querySelector(".view.active");
    const empty = document.querySelector("#eegEmpty");
    const canvas = document.querySelector("#eegCanvas");
    const canvasRect = canvas?.getBoundingClientRect?.();
    return Boolean(
      activeView?.id === "analysis" &&
      canvas &&
      empty &&
      canvasRect?.width > 0 &&
      canvasRect?.height > 0 &&
      getComputedStyle(canvas).visibility !== "hidden" &&
      getComputedStyle(empty).display === "none",
    );
  }, null, { timeout: 120000 });
  return canvasStats(page);
}

async function clickAndWaitForWaveform(page, selector) {
  await page.locator(selector).first().click();
  await page.waitForTimeout(500);
  return waitForWaveform(page);
}

async function waitForJsonResponse(page, predicate, timeout = 120000) {
  const response = await page.waitForResponse(predicate, { timeout });
  let body = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }
  return { ok: response.ok(), status: response.status(), body };
}

function requestJson(request) {
  try {
    return request.postDataJSON();
  } catch {
    try {
      return JSON.parse(request.postData() || "{}");
    } catch {
      return {};
    }
  }
}

async function run() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const evidence = {
    script: path.basename(new URL(import.meta.url).pathname),
    target_url: TARGET_URL,
    api_base: API_BASE,
    generated_at: new Date().toISOString(),
    checks: [],
    screenshots: [],
    errors: [],
    status: "running",
  };
  const executablePath = localBrowserExecutable();
  const browser = await chromium.launch({ headless: true, ...(executablePath ? { executablePath } : {}) });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  page.setDefaultTimeout(60000);

  try {
    await ensureLoggedIn(page);
    await page.locator('[data-testid="project-crud-panel"]').waitFor({ state: "visible", timeout: 30000 });
    await page.waitForFunction(
      () => {
        const summary = document.querySelector("#workspaceProjectFilterSummary")?.textContent || "";
        return summary.includes("/") && summary.includes("个项目");
      },
      null,
      { timeout: 60000 },
    );

    const projectRowsText = await page.locator("#iaProjectRows").innerText().catch(() => "");
    const forbiddenProjects = ["Acceptance", "Persistence", "Smoke", "Grouped methods E2E", "QC preview", "QC Lab", "proj_demo_learning", "pilot-user", "Pilot 真实分析项目", "V01 科研验证项目"];
    evidence.checks.push(check("project_rows_hide_internal_records_by_default", forbiddenProjects.every((term) => !projectRowsText.includes(term)), { forbiddenProjects, sample: projectRowsText.slice(0, 600) }));
    const filterSummary = await textOf(page, "#workspaceProjectFilterSummary");
    evidence.checks.push(check("project_filter_summary_explains_hidden_internal_records", filterSummary.includes("已隐藏") && filterSummary.includes("内部验收"), { filterSummary }));
    const projectToggleLabel = await textOf(page, 'label[for="workspaceShowReviewProjects"] span');
    evidence.checks.push(check("project_filter_label_is_internal_archive", projectToggleLabel.includes("内部/归档"), { projectToggleLabel }));
    evidence.checks.push(check("project_filter_label_includes_hidden_count", /（\d+）/.test(projectToggleLabel), { projectToggleLabel }));
    evidence.checks.push(check(
      "project_edit_actions_hidden_without_project",
      !(await page.locator('[data-testid="project-crud-panel"] .ia-row-actions').isVisible().catch(() => false)),
    ));
    evidence.checks.push(check("desktop_no_horizontal_overflow_project_page", (await viewportNoHorizontalOverflow(page)).ok, await viewportNoHorizontalOverflow(page)));

    await page.locator("#workspaceShowReviewProjects").check();
    await page.waitForTimeout(300);
    const expandedSummary = await textOf(page, "#workspaceProjectFilterSummary");
    evidence.checks.push(check("internal_archive_switch_changes_scope", expandedSummary.includes("内部/归档") || expandedSummary.includes("已显示"), { expandedSummary }));
    await page.locator("#workspaceShowReviewProjects").uncheck();
    await page.waitForTimeout(300);

    const projectScreenshot = path.join(OUT_DIR, "project_management_default_scope.png");
    await page.screenshot({ path: projectScreenshot, fullPage: true });
    evidence.screenshots.push(projectScreenshot);

    await page.locator("#teachingModeBtn").click();
    await page.locator(".teaching-overlay.active").waitFor({ state: "visible", timeout: 30000 });
    await waitForTeachingStep(page, "1/8");
    await advanceTeachingTo(page, "3/8");
    await page.waitForFunction(() => document.querySelector(".view.active")?.id === "analysis", null, { timeout: 30000 });
    await hideTeachingOverlayForValidation(page);
    await page.locator('[data-testid="single-file-preview-panel"]').waitFor({ state: "visible", timeout: 30000 });
    await page.locator('[data-testid="preprocessing-inline-panel"]').waitFor({ state: "visible", timeout: 30000 });

    const fileRows = page.locator('[data-file-select]:visible');
    await fileRows.first().waitFor({ state: "visible", timeout: 30000 });
    const teachingFileCount = await fileRows.count();
    const teachingQueueText = await page.locator("#prepDataQueue").innerText().catch(() => "");
    evidence.checks.push(check(
      "teaching_mode_shows_one_demo_file",
      teachingFileCount === 1 && teachingQueueText.includes("teaching_oddball_with_montage_raw.fif") && !teachingQueueText.includes("ui_with_events_raw.fif"),
      { teachingFileCount, teachingQueueText: teachingQueueText.slice(0, 600) },
    ));
    await fileRows.first().click();
    const rawWaveform = await waitForWaveform(page);
    evidence.checks.push(check("selected_data_draws_nonblank_waveform_canvas", rawWaveform.ok, rawWaveform));

    const sameViewport = await page.evaluate(() => {
      const canvas = document.querySelector("#eegCanvas")?.getBoundingClientRect();
      const panel = document.querySelector('[data-testid="preprocessing-inline-panel"]')?.getBoundingClientRect();
      if (!canvas || !panel) return { ok: false };
      const verticalOverlap = Math.max(0, Math.min(canvas.bottom, panel.bottom) - Math.max(canvas.top, panel.top));
      return { ok: verticalOverlap > 80, canvas, panel, verticalOverlap };
    });
    evidence.checks.push(check("preprocessing_panel_visible_with_waveform", sameViewport.ok, sameViewport));

    const beforeWindow = await textOf(page, "#eegWindowLabel");
    await clickAndWaitForWaveform(page, "#eegZoomInBtn");
    const afterZoomIn = await textOf(page, "#eegWindowLabel");
    evidence.checks.push(check("zoom_in_changes_window_label", beforeWindow !== afterZoomIn, { beforeWindow, afterZoomIn }));

    const beforeStart = await page.locator("#eegStartInput").inputValue();
    await clickAndWaitForWaveform(page, "#eegNextBtn");
    const afterNextStart = await page.locator("#eegStartInput").inputValue();
    evidence.checks.push(check("next_window_changes_start", beforeStart !== afterNextStart, { beforeStart, afterNextStart }));

    const beforeCanvas = await canvasStats(page);
    await page.locator("#eegGainInput").fill("4");
    await page.waitForTimeout(300);
    const gainCanvas = await canvasStats(page);
    evidence.checks.push(check("gain_control_keeps_canvas_nonblank", gainCanvas.ok && beforeCanvas.nonWhite !== gainCanvas.nonWhite, { beforeCanvas, gainCanvas }));

    const filterTaskPromise = waitForJsonResponse(page, (response) => {
      const request = response.request();
      const body = requestJson(request);
      return response.url().endsWith("/api/tasks") &&
        request.method() === "POST" &&
        body?.workflow_id === "qc_waveform_preview" &&
        body?.parameters_json?.filter_preview?.enabled === true;
    }, 240000).catch((error) => ({ ok: false, status: 0, body: null, error: error.message || String(error) }));
    await page.locator("#eegFilterPreviewToggle").check();
    const filterTask = await filterTaskPromise;
    evidence.checks.push(check("filter_preview_task_accepted", filterTask.ok && filterTask.body?.id && filterTask.body?.workflow_id === "qc_waveform_preview", {
      status: filterTask.status,
      task_id: filterTask.body?.id,
      task_status: filterTask.body?.status,
      error: filterTask.error,
    }));
    await page.waitForFunction(
      () => document.querySelector("#eegMeta")?.textContent.includes("预览滤波"),
      null,
      { timeout: 90000 },
    );
    await waitForWaveform(page);
    const metaAfterFilter = await page.locator("#eegMeta").innerText();
    evidence.checks.push(check("filter_preview_mode_visible", metaAfterFilter.includes("预览滤波") && metaAfterFilter.includes("不改写原始 EEG"), { metaAfterFilter }));
    evidence.checks.push(check("filter_parameter_summary_visible", metaAfterFilter.includes("滤波参数") && metaAfterFilter.includes("仅预览"), { metaAfterFilter }));

    await page.locator('[data-ia-action="mark-bad-channel"]').click();
    await page.waitForTimeout(200);
    const afterMark = await textOf(page, "#segmentSummary");
    evidence.checks.push(check("bad_channel_mark_draft_visible", afterMark.includes("已标记坏道") || afterMark.includes("坏道修改 1"), { afterMark }));

    const planPromise = waitForJsonResponse(page, (response) => response.url().includes("/api/data-preparation/plans") && response.request().method() === "POST", 120000)
      .catch((error) => ({ ok: false, status: 0, body: null, error: error.message || String(error) }));
    await page.locator('[data-real-action="confirm-plan-inline"]').first().click();
    const planResponse = await planPromise;
    evidence.checks.push(check("data_preparation_plan_confirmed_before_bad_channel_audit", planResponse.ok && planResponse.body?.status === "confirmed", {
      status: planResponse.status,
      plan_id: planResponse.body?.id,
      plan_status: planResponse.body?.status,
      error: planResponse.error,
    }));
    await page.waitForFunction(() => {
      const button = document.querySelector('[data-real-action="save-bad-channel-audit"]');
      return Boolean(button && !button.disabled && button.getAttribute("aria-disabled") !== "true");
    }, null, { timeout: 30000 });

    const saveAuditPromise = waitForJsonResponse(page, (response) => response.url().includes("/api/eeg/files/") && response.url().includes("/bad-channel-audit") && response.request().method() === "POST", 120000)
      .catch((error) => ({ ok: false, status: 0, body: null, error: error.message || String(error) }));
    await page.locator('[data-real-action="save-bad-channel-audit"]').first().click();
    const saveAudit = await saveAuditPromise;
    evidence.checks.push(check("bad_channel_save_audit_persisted", saveAudit.ok && saveAudit.body?.decision === "save", {
      status: saveAudit.status,
      audit_id: saveAudit.body?.id,
      decision: saveAudit.body?.decision,
      error: saveAudit.error,
    }));

    page.once("dialog", async (dialog) => {
      evidence.checks.push(check("bad_channel_restore_confirmation_dialog", dialog.message().includes("确认恢复最近一次坏道修改"), { message: dialog.message() }));
      await dialog.accept();
    });
    await page.locator('[data-ia-action="restore-bad-channel"]').click();
    await page.waitForTimeout(200);
    const afterRestore = await textOf(page, "#segmentSummary");
    evidence.checks.push(check("bad_channel_restore_draft_visible", (afterRestore.includes("已恢复坏道") || afterRestore.includes("坏道恢复 1")) && afterRestore.includes("坏道历史"), { afterRestore }));

    const restoreAuditPromise = waitForJsonResponse(page, (response) => response.url().includes("/api/eeg/files/") && response.url().includes("/bad-channel-audit") && response.request().method() === "POST", 120000)
      .catch((error) => ({ ok: false, status: 0, body: null, error: error.message || String(error) }));
    await page.locator('[data-real-action="discard-bad-channel-audit"]').first().click();
    const restoreAudit = await restoreAuditPromise;
    evidence.checks.push(check("bad_channel_restore_audit_persisted", restoreAudit.ok && restoreAudit.body?.decision === "discard", {
      status: restoreAudit.status,
      audit_id: restoreAudit.body?.id,
      decision: restoreAudit.body?.decision,
      error: restoreAudit.error,
    }));

    await hideTeachingOverlayForValidation(page);
    const workflowScreenshot = path.join(OUT_DIR, "waveform_preprocessing_workbench.png");
    await page.screenshot({ path: workflowScreenshot, fullPage: true });
    evidence.screenshots.push(workflowScreenshot);

    await page.setViewportSize({ width: 390, height: 844 });
    await page.waitForTimeout(500);
    await hideTeachingOverlayForValidation(page);
    evidence.checks.push(check("mobile_no_horizontal_overflow_waveform_page", (await viewportNoHorizontalOverflow(page)).ok, await viewportNoHorizontalOverflow(page)));
    const mobileScreenshot = path.join(OUT_DIR, "waveform_preprocessing_mobile.png");
    await page.screenshot({ path: mobileScreenshot, fullPage: true });
    evidence.screenshots.push(mobileScreenshot);
  } catch (error) {
    evidence.errors.push(error.stack || error.message || String(error));
  } finally {
    evidence.status = evidence.errors.length === 0 && evidence.checks.every((item) => item.pass) ? "passed" : "failed";
    fs.writeFileSync(EVIDENCE_PATH, `${JSON.stringify(evidence, null, 2)}\n`, "utf8");
    await browser.close();
  }
  console.log(JSON.stringify(evidence, null, 2));
  if (evidence.status !== "passed") process.exit(1);
}

run().catch((error) => {
  console.error(error.stack || error.message || String(error));
  process.exit(1);
});
