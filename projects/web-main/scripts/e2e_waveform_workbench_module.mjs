import fs from "node:fs";
import path from "node:path";
import { chromium, chromiumLaunchOptions } from "./lib/playwright_runtime.mjs";

const repoRoot = process.cwd();
const evidenceDir = process.env.QLANALYSER_WAVEFORM_WORKBENCH_E2E_DIR
  || path.join(repoRoot, "work", "release_evidence", "20260628-waveform-workbench-epoch-review");
fs.mkdirSync(evidenceDir, { recursive: true });

const frontendUrl = process.env.QLANALYSER_WAVEFORM_WORKBENCH_URL
  || "http://127.0.0.1:4174/waveform-workbench.html?workbench=epoch&teaching_demo=auto&api=http%3A%2F%2F127.0.0.1%3A8001%2Fapi&v=e2e";

function pass(id, details = {}) {
  return { id, passed: true, ...details };
}

function fail(id, details = {}) {
  return { id, passed: false, ...details };
}

function approx(actual, expected, tolerance) {
  return Number.isFinite(actual) && Number.isFinite(expected) && Math.abs(actual - expected) <= tolerance;
}

async function state(page) {
  return page.evaluate(() => {
    const shell = document.querySelector("[data-testid='waveform-workbench-shell']");
    const status = document.querySelector("[data-testid='waveform-status-bar']");
    const empty = document.querySelector("#wwEmpty");
    const canvas = document.querySelector("#wwCanvas");
    const draft = document.querySelector("#wwDraftSummary");
    const actionState = document.querySelector("#wwActionState");
    const actionHint = document.querySelector("#wwActionHint");
    const primaryAction = document.querySelector("#wwPrimaryAction");
    const candidateActions = document.querySelector(".ww-candidate-actions");
    const reviewActions = document.querySelector(".ww-review-actions");
    const historyActions = document.querySelector(".ww-history-actions");
    const dangerActions = document.querySelector(".ww-danger-zone");
    const overview = document.querySelector("[data-testid='waveform-overview']");
    const loading = document.querySelector("#wwLoadingOverlay");
    const governedToolbar = document.querySelector("[data-testid='waveform-governed-toolbar']");
    const toolbarBands = Array.from(document.querySelectorAll("[data-toolbar-layer]")).map((item) => ({
      layer: item.getAttribute("data-toolbar-layer"),
      text: item.textContent || "",
      visible: item.getBoundingClientRect().height > 0 && getComputedStyle(item).display !== "none",
    }));
    const epochControls = document.querySelector("[data-testid='waveform-epoch-controls']");
    const rect = canvas?.getBoundingClientRect();
    return {
      loaded: shell?.dataset.loaded === "true",
      mode: shell?.dataset.mode || "",
      workbenchMode: shell?.dataset.workbenchMode || "",
      epochEnabled: shell?.dataset.epochEnabled === "true",
      fileName: shell?.dataset.fileName || "",
      startSec: Number(shell?.dataset.startSec || 0),
      durationSec: Number(shell?.dataset.durationSec || 0),
      fileDurationSec: Number(shell?.dataset.fileDurationSec || 0),
      visibleChannels: Number(shell?.dataset.visibleChannels || 0),
      sensitivityUvPerRow: Number(shell?.dataset.sensitivityUvPerRow || 0),
      epochLengthSec: Number(shell?.dataset.epochLengthSec || 0),
      visibleEpochs: Number(shell?.dataset.visibleEpochs || 0),
      hasEpochSelection: shell?.dataset.hasEpochSelection === "true",
      selectedEpochStart: shell?.dataset.selectedEpochStart || "",
      selectedEpochEnd: shell?.dataset.selectedEpochEnd || "",
      candidateBadSegmentCount: Number(shell?.dataset.candidateBadSegmentCount || 0),
      badSegmentCount: Number(shell?.dataset.badSegmentCount || 0),
      remainSegmentCount: Number(shell?.dataset.remainSegmentCount || 0),
      restoredSegmentCount: Number(shell?.dataset.restoredSegmentCount || 0),
      badChannelCount: Number(shell?.dataset.badChannelCount || 0),
      hasSelectedSegment: shell?.dataset.hasSelectedSegment === "true",
      auditActionCount: Number(shell?.dataset.auditActionCount || 0),
      undoCount: Number(shell?.dataset.undoCount || 0),
      redoCount: Number(shell?.dataset.redoCount || 0),
      eventDisplay: shell?.dataset.eventDisplay || "",
      waveformSource: shell?.dataset.waveformSource || "",
      waveformSchemaVersion: shell?.dataset.waveformSchemaVersion || "",
      cacheChunkCount: Number(shell?.dataset.cacheChunkCount || 0),
      loadingState: shell?.dataset.loadingState || "",
      waveformLastReloadSource: shell?.dataset.waveformLastReloadSource || "",
      waveformCacheHits: Number(shell?.dataset.waveformCacheHits || 0),
      waveformChunkRequests: Number(shell?.dataset.waveformChunkRequests || 0),
      waveformChunkAborts: Number(shell?.dataset.waveformChunkAborts || 0),
      waveformChunkFallbacks: Number(shell?.dataset.waveformChunkFallbacks || 0),
      waveformPrefetchRequests: Number(shell?.dataset.waveformPrefetchRequests || 0),
      waveformPrefetchInFlight: Number(shell?.dataset.waveformPrefetchInFlight || 0),
      cachePendingRange: shell?.dataset.cachePendingRange || "",
      cacheLoadedRanges: shell?.dataset.cacheLoadedRanges || "",
      windowCoverage: shell?.dataset.windowCoverage || "",
      dataCoverageState: shell?.dataset.dataCoverageState || "",
      dataCoverageRange: shell?.dataset.dataCoverageRange || "",
      dataCoverageFraction: Number(shell?.dataset.dataCoverageFraction || 0),
      usesRemappedFallback: shell?.dataset.usesRemappedFallback || "",
      renderPolicy: shell?.dataset.renderPolicy || "",
      authoritativeChunkRange: shell?.dataset.authoritativeChunkRange || "",
      authoritativeChunkCountForWindow: Number(shell?.dataset.authoritativeChunkCountForWindow || 0),
      overlappingChunkCountForWindow: Number(shell?.dataset.overlappingChunkCountForWindow || 0),
      statusText: status?.textContent || "",
      statusHidden: status ? status.hidden : false,
      emptyHidden: empty?.classList.contains("hidden") || false,
      loadingVisible: loading ? !loading.hidden : false,
      loadingText: loading?.textContent || "",
      overviewVisible: !!overview && overview.getBoundingClientRect().height > 0,
      overviewText: document.querySelector("#wwOverviewCaption")?.textContent || "",
      governedToolbarVisible: !!governedToolbar && governedToolbar.getBoundingClientRect().height > 0,
      toolbarBands,
      epochControlsVisible: !!epochControls && epochControls.getBoundingClientRect().height > 0 && getComputedStyle(epochControls).display !== "none",
      draftText: draft?.textContent || "",
      actionStateText: actionState?.textContent || "",
      actionHintText: actionHint?.textContent || "",
      primaryActionText: primaryAction?.textContent || "",
      primaryActionVisible: !!primaryAction && primaryAction.getBoundingClientRect().height > 0 && getComputedStyle(primaryAction).display !== "none",
      candidateActionsHidden: candidateActions?.classList.contains("is-empty") || false,
      reviewActionsHidden: reviewActions?.classList.contains("is-empty") || false,
      historyActionsHidden: historyActions?.classList.contains("is-empty") || false,
      dangerActionsHidden: dangerActions?.classList.contains("is-empty") || false,
      canvasBox: rect ? { x: rect.x, y: rect.y, width: rect.width, height: rect.height } : null,
      scrollY: window.scrollY,
      buttons: {
        rejectDisabled: document.querySelector("#wwRejectBtn")?.disabled || false,
        remainDisabled: document.querySelector("#wwRemainBtn")?.disabled || false,
        undoDisabled: document.querySelector("#wwUndoBtn")?.disabled || false,
        redoDisabled: document.querySelector("#wwRedoBtn")?.disabled || false,
        cancelAllDisabled: document.querySelector("#wwCancelAllBtn")?.disabled || false,
        confirmCandidatesDisabled: document.querySelector("#wwConfirmBadSegmentsBtn")?.disabled || false,
        discardCandidatesDisabled: document.querySelector("#wwDiscardCandidatesBtn")?.disabled || false,
        restoreSegmentDisabled: document.querySelector("#wwRestoreSegmentBtn")?.disabled || false,
        clearDraftDisabled: document.querySelector("#wwClearDraftBtn")?.disabled || false,
      },
    };
  });
}

async function canvasInk(page) {
  return page.evaluate(() => {
    const canvas = document.querySelector("#wwCanvas");
    if (!canvas) return { checked: 0, ink: 0, ratio: 0 };
    const ctx = canvas.getContext("2d");
    const width = canvas.width;
    const height = canvas.height;
    const image = ctx.getImageData(0, 0, width, height).data;
    let checked = 0;
    let ink = 0;
    const step = Math.max(4, Math.floor(Math.sqrt((width * height) / 24000)));
    for (let y = 0; y < height; y += step) {
      for (let x = 0; x < width; x += step) {
        const idx = (y * width + x) * 4;
        const r = image[idx];
        const g = image[idx + 1];
        const b = image[idx + 2];
        const a = image[idx + 3];
        checked += 1;
        if (a > 0 && (r < 245 || g < 245 || b < 245)) ink += 1;
      }
    }
    return { checked, ink, ratio: checked ? ink / checked : 0 };
  });
}

async function screenshot(page, name) {
  const output = path.join(evidenceDir, name);
  await page.screenshot({ path: output, fullPage: false });
  return output;
}

async function waitForViewportReload(page) {
  await page.waitForTimeout(900);
}

async function wheel(page, box, deltaY, modifiers = []) {
  await page.mouse.move(box.x + box.width * 0.52, box.y + box.height * 0.45);
  for (const modifier of modifiers) await page.keyboard.down(modifier);
  await page.mouse.wheel(0, deltaY);
  for (const modifier of modifiers.reverse()) await page.keyboard.up(modifier);
  await waitForViewportReload(page);
}

async function wheelNoWait(page, box, deltaY, modifiers = []) {
  await page.mouse.move(box.x + box.width * 0.52, box.y + box.height * 0.45);
  for (const modifier of modifiers) await page.keyboard.down(modifier);
  await page.mouse.wheel(0, deltaY);
  for (const modifier of modifiers.reverse()) await page.keyboard.up(modifier);
  await page.waitForTimeout(80);
}

async function drag(page, box, x1Ratio, x2Ratio, yRatio = 0.45) {
  const y = box.y + box.height * yRatio;
  await page.mouse.move(box.x + box.width * x1Ratio, y);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * x2Ratio, y, { steps: 8 });
  await page.mouse.up();
  await page.waitForTimeout(180);
}

async function freshCanvasBox(page) {
  const canvas = page.locator("#wwCanvas");
  await canvas.scrollIntoViewIfNeeded();
  const box = await canvas.boundingBox();
  if (!box) throw new Error("Canvas bounding box not available");
  return box;
}

async function run() {
  const browser = await chromium.launch(chromiumLaunchOptions({ headless: true }));
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const checks = [];
  const screenshots = {};

  try {
    await page.goto(frontendUrl, { waitUntil: "domcontentloaded", timeout: 30000 });
    await page.waitForFunction(() => document.querySelector("[data-testid='waveform-workbench-shell']")?.dataset.loaded === "true", null, { timeout: 30000 });
    await page.locator("#wwCanvas").waitFor({ state: "visible", timeout: 10000 });
    await page.waitForFunction(() => {
      const canvas = document.querySelector("#wwCanvas");
      if (!canvas) return false;
      const ctx = canvas.getContext("2d");
      const { width, height } = canvas;
      const data = ctx.getImageData(0, 0, width, height).data;
      let checked = 0;
      let ink = 0;
      const step = Math.max(4, Math.floor(Math.sqrt((width * height) / 24000)));
      for (let y = 0; y < height; y += step) {
        for (let x = 0; x < width; x += step) {
          const idx = (y * width + x) * 4;
          checked += 1;
          if (data[idx + 3] > 0 && (data[idx] < 245 || data[idx + 1] < 245 || data[idx + 2] < 245)) ink += 1;
        }
      }
      return checked > 0 && ink / checked > 0.01;
    }, null, { timeout: 10000 });
    const initial = await state(page);
    const initialInk = await canvasInk(page);
    const box = initial.canvasBox;
    screenshots.initial = await screenshot(page, "01_initial_loaded.png");

    checks.push(initial.loaded && initial.emptyHidden && /teaching|oddball/i.test(initial.fileName)
      ? pass("T-WF-01-teaching-data-auto-loaded", { initial })
      : fail("T-WF-01-teaching-data-auto-loaded", { initial }));
    checks.push(initial.statusHidden && !initial.statusText.includes("8 ch") && !initial.statusText.includes("s/page") && !initial.statusText.includes("草稿无")
      ? pass("T-WF-12-status-bar-deduped-by-default", { statusText: initial.statusText, statusHidden: initial.statusHidden })
      : fail("T-WF-12-status-bar-complete", { statusText: initial.statusText }));
    checks.push(initial.cacheChunkCount >= 1 && initial.windowCoverage === "ready" && initial.usesRemappedFallback === "false"
      ? pass("T-CONT-01-initial-window-uses-real-cache", { cacheLoadedRanges: initial.cacheLoadedRanges })
      : fail("T-CONT-01-initial-window-uses-real-cache", { initial }));
    checks.push(initial.waveformSource === "waveform_chunk_api" && initial.waveformSchemaVersion === "qlanalyser-waveform-chunk-v0.1"
      ? pass("T-PERF-01-initial-waveform-uses-lightweight-chunk-api", {
        waveformSource: initial.waveformSource,
        waveformSchemaVersion: initial.waveformSchemaVersion,
      })
      : fail("T-PERF-01-initial-waveform-uses-lightweight-chunk-api", { initial }));
    checks.push(initialInk.ratio > 0.01
      ? pass("T-VIS-01-initial-canvas-has-visible-waveform-ink", initialInk)
      : fail("T-VIS-01-initial-canvas-has-visible-waveform-ink", { initialInk, initial }));
    checks.push(initial.renderPolicy === "single_authoritative_chunk" && initial.authoritativeChunkCountForWindow === 1 && initial.authoritativeChunkRange
      ? pass("T-CONT-04-single-authoritative-chunk-render-policy", {
        authoritativeChunkRange: initial.authoritativeChunkRange,
        overlappingChunkCountForWindow: initial.overlappingChunkCountForWindow,
      })
      : fail("T-CONT-04-single-authoritative-chunk-render-policy", { initial }));
    checks.push(initial.dataCoverageState === "ready" && initial.dataCoverageFraction >= 0.98 && initial.dataCoverageRange
      ? pass("T-LOGIC-01-initial-canvas-matches-real-data-coverage", {
        dataCoverageState: initial.dataCoverageState,
        dataCoverageFraction: initial.dataCoverageFraction,
        dataCoverageRange: initial.dataCoverageRange,
      })
      : fail("T-LOGIC-01-initial-canvas-matches-real-data-coverage", { initial }));
    checks.push(initial.buttons.rejectDisabled && initial.buttons.remainDisabled && initial.buttons.confirmCandidatesDisabled && initial.buttons.restoreSegmentDisabled
      ? pass("T-WF-14-write-actions-disabled-without-selection", { buttons: initial.buttons })
      : fail("T-WF-14-write-actions-disabled-without-selection", { buttons: initial.buttons }));
    checks.push(initial.candidateActionsHidden && initial.reviewActionsHidden && initial.historyActionsHidden && initial.dangerActionsHidden && initial.actionStateText.includes("等待") && initial.primaryActionText.includes("选择")
      ? pass("T-UI-01-empty-state-does-not-promote-disabled-write-actions", {
        actionStateText: initial.actionStateText,
        primaryActionText: initial.primaryActionText,
        candidateActionsHidden: initial.candidateActionsHidden,
        reviewActionsHidden: initial.reviewActionsHidden,
        historyActionsHidden: initial.historyActionsHidden,
        dangerActionsHidden: initial.dangerActionsHidden,
      })
      : fail("T-UI-01-empty-state-does-not-promote-disabled-write-actions", { initial }));
    checks.push(!initial.primaryActionVisible && initial.draftText.trim() === "暂无草稿。"
      ? pass("T-UI-07-empty-state-deduplicates-right-panel-prompts", { primaryActionVisible: initial.primaryActionVisible, draftText: initial.draftText })
      : fail("T-UI-07-empty-state-deduplicates-right-panel-prompts", { initial }));
    checks.push(initial.overviewVisible && initial.overviewText.includes("全程") && initial.overviewText.includes("非断点") && !/\\d+\\.\\d-\\d+\\.\\ds,\\s*\\d+\\.\\d-\\d+\\.\\ds,\\s*\\d+\\.\\d-\\d+\\.\\ds/.test(initial.overviewText)
      ? pass("T-CONT-05-overview-visible-without-cache-log-noise", { overviewText: initial.overviewText })
      : fail("T-CONT-05-overview-visible", { initial }));
    checks.push(initial.governedToolbarVisible && ["browse", "display", "write"].every((layer) => initial.toolbarBands.some((item) => item.layer === layer && item.visible))
      ? pass("T-UI-04-toolbar-has-governed-task-layers", { toolbarBands: initial.toolbarBands })
      : fail("T-UI-04-toolbar-has-governed-task-layers", { initial }));
    checks.push(initial.mode === "browse" && !initial.epochControlsVisible
      ? pass("T-UI-05-epoch-controls-hidden-in-browse-mode", { mode: initial.mode, epochControlsVisible: initial.epochControlsVisible })
      : fail("T-UI-05-epoch-controls-hidden-in-browse-mode", { initial }));

    await wheelNoWait(page, box, 600);
    const duringPan = await state(page);
    checks.push(duringPan.usesRemappedFallback === "false" && ["partial", "loading", "missing", "ready"].includes(duringPan.windowCoverage)
      ? pass("T-CONT-02-no-old-payload-remap-while-panning", { duringPan })
      : fail("T-CONT-02-no-old-payload-remap-while-panning", { duringPan }));
    checks.push(duringPan.renderPolicy === "single_authoritative_chunk" && duringPan.authoritativeChunkCountForWindow <= 1
      ? pass("T-CONT-07-overlap-does-not-merge-grid", {
        authoritativeChunkRange: duringPan.authoritativeChunkRange,
        overlappingChunkCountForWindow: duringPan.overlappingChunkCountForWindow,
      })
      : fail("T-CONT-07-overlap-does-not-merge-grid", { duringPan }));
    checks.push(["ready", "partial", "loading", "missing"].includes(duringPan.dataCoverageState) && duringPan.dataCoverageFraction >= 0
      ? pass("T-LOGIC-02-pan-exposes-data-coverage-state", {
        dataCoverageState: duringPan.dataCoverageState,
        dataCoverageFraction: duringPan.dataCoverageFraction,
      })
      : fail("T-LOGIC-02-pan-exposes-data-coverage-state", { duringPan }));

    await waitForViewportReload(page);
    const afterWheel = await state(page);
    screenshots.afterWheel = await screenshot(page, "02_after_wheel_pan.png");
    checks.push(afterWheel.startSec > initial.startSec && approx(afterWheel.startSec - initial.startSec, initial.durationSec * 0.08, 0.55) && approx(afterWheel.durationSec, initial.durationSec, 0.01)
      ? pass("T-WF-03-wheel-pans-not-zooms", { before: initial.startSec, after: afterWheel.startSec, duration: afterWheel.durationSec })
      : fail("T-WF-03-wheel-pans-not-zooms", { before: initial, after: afterWheel }));
    checks.push(afterWheel.waveformLastReloadSource === "cache_hit" && afterWheel.waveformCacheHits >= 1 && afterWheel.waveformChunkFallbacks === 0
      ? pass("T-PERF-02-wheel-pan-uses-cache-hit-not-legacy-task", {
        waveformLastReloadSource: afterWheel.waveformLastReloadSource,
        waveformCacheHits: afterWheel.waveformCacheHits,
        waveformChunkRequests: afterWheel.waveformChunkRequests,
        waveformChunkFallbacks: afterWheel.waveformChunkFallbacks,
      })
      : fail("T-PERF-02-wheel-pan-uses-cache-hit-not-legacy-task", { afterWheel }));

    await wheel(page, box, -600, ["Control"]);
    const afterCtrlWheel = await state(page);
    screenshots.afterCtrlZoom = await screenshot(page, "03_after_ctrl_zoom.png");
    checks.push(afterCtrlWheel.durationSec < afterWheel.durationSec && approx(afterCtrlWheel.durationSec, afterWheel.durationSec / 1.2, 0.55)
      ? pass("T-WF-04-ctrl-wheel-zooms-time-window", { before: afterWheel.durationSec, after: afterCtrlWheel.durationSec })
      : fail("T-WF-04-ctrl-wheel-zooms-time-window", { before: afterWheel, after: afterCtrlWheel }));

    await page.locator("#wwCanvas").click();
    await page.keyboard.press("PageDown");
    await waitForViewportReload(page);
    const afterPageDown = await state(page);
    checks.push(afterPageDown.startSec > afterCtrlWheel.startSec
      ? pass("T-WF-05-page-down-pans-one-page", { before: afterCtrlWheel.startSec, after: afterPageDown.startSec })
      : fail("T-WF-05-page-down-pans-one-page", { before: afterCtrlWheel, after: afterPageDown }));

    await page.keyboard.press("ArrowRight");
    await waitForViewportReload(page);
    const afterArrow = await state(page);
    checks.push(afterArrow.startSec > afterPageDown.startSec && approx(afterArrow.startSec - afterPageDown.startSec, afterArrow.durationSec * 0.10, 0.55)
      ? pass("T-WF-06-arrow-right-small-pan", { before: afterPageDown.startSec, after: afterArrow.startSec })
      : fail("T-WF-06-arrow-right-small-pan", { before: afterPageDown, after: afterArrow }));

    checks.push(afterArrow.cacheChunkCount >= 1 && afterArrow.usesRemappedFallback === "false" && (afterArrow.windowCoverage === "ready" || afterArrow.loadingVisible)
      ? pass("T-CONT-03-pan-window-real-cache-or-explicit-loading", { cacheLoadedRanges: afterArrow.cacheLoadedRanges, windowCoverage: afterArrow.windowCoverage, loadingText: afterArrow.loadingText })
      : fail("T-CONT-03-pan-window-loads-real-cache", { afterArrow }));

    await page.locator("#wwEventDisplay").selectOption("hidden");
    const afterHideEvents = await state(page);
    await page.locator("#wwEventDisplay").selectOption("light");
    const afterLightEvents = await state(page);
    checks.push(afterHideEvents.eventDisplay === "hidden" && afterLightEvents.eventDisplay === "light"
      ? pass("T-CONT-06-event-display-toggle")
      : fail("T-CONT-06-event-display-toggle", { afterHideEvents, afterLightEvents }));

    await page.keyboard.press("+");
    const afterGain = await state(page);
    checks.push(afterGain.sensitivityUvPerRow < afterArrow.sensitivityUvPerRow && approx(afterGain.durationSec, afterArrow.durationSec, 0.01)
      ? pass("T-WF-07-plus-changes-amplitude-only", { before: afterArrow.sensitivityUvPerRow, after: afterGain.sensitivityUvPerRow })
      : fail("T-WF-07-plus-changes-amplitude-only", { before: afterArrow, after: afterGain }));

    await drag(page, box, 0.25, 0.45);
    const afterBrowseDrag = await state(page);
    checks.push(!afterBrowseDrag.hasSelectedSegment && afterBrowseDrag.badSegmentCount === 0 && afterBrowseDrag.badChannelCount === 0
      ? pass("T-WF-08-browse-drag-does-not-write-draft")
      : fail("T-WF-08-browse-drag-does-not-write-draft", { afterBrowseDrag }));

    await page.locator("[data-testid='waveform-mode-select-segment']").click();
    await drag(page, await freshCanvasBox(page), 0.28, 0.52);
    const afterSelect = await state(page);
    screenshots.afterDraft = await screenshot(page, "04_after_write_mode_draft.png");
    checks.push(afterSelect.mode === "selectSegment" && afterSelect.hasSelectedSegment && afterSelect.auditActionCount >= 1
      ? pass("T-WF-09-select-mode-writes-selected-segment", { afterSelect })
      : fail("T-WF-09-select-mode-writes-selected-segment", { afterSelect }));
    checks.push(!afterSelect.buttons.rejectDisabled && !afterSelect.buttons.remainDisabled && !afterSelect.buttons.cancelAllDisabled && !afterSelect.buttons.clearDraftDisabled
      ? pass("T-WF-15-write-actions-enable-after-selection", { buttons: afterSelect.buttons })
      : fail("T-WF-15-write-actions-enable-after-selection", { buttons: afterSelect.buttons }));
    checks.push(afterSelect.actionStateText.includes("已选中") && afterSelect.primaryActionText.includes("剔除") && afterSelect.primaryActionText.includes("保留") && afterSelect.candidateActionsHidden && !afterSelect.reviewActionsHidden
      ? pass("T-UI-02-selection-promotes-review-actions", {
        actionStateText: afterSelect.actionStateText,
        primaryActionText: afterSelect.primaryActionText,
        reviewActionsHidden: afterSelect.reviewActionsHidden,
      })
      : fail("T-UI-02-selection-promotes-review-actions", { afterSelect }));
    checks.push(afterSelect.primaryActionVisible
      ? pass("T-UI-08-selection-shows-primary-action-card", { primaryActionVisible: afterSelect.primaryActionVisible, primaryActionText: afterSelect.primaryActionText })
      : fail("T-UI-08-selection-shows-primary-action-card", { afterSelect }));

    await page.locator("[data-testid='waveform-mode-epoch-review']").click();
    await drag(page, await freshCanvasBox(page), 0.22, 0.45);
    const afterEpochSelect = await state(page);
    screenshots.afterEpochSelect = await screenshot(page, "04b_after_epoch_selection.png");
    checks.push(afterEpochSelect.mode === "epochReview" && afterEpochSelect.hasEpochSelection && afterEpochSelect.hasSelectedSegment && afterEpochSelect.epochLengthSec === 4 && afterEpochSelect.visibleEpochs === 6
      ? pass("T-WF-09B-epoch-review-snaps-selection", { afterEpochSelect })
      : fail("T-WF-09B-epoch-review-snaps-selection", { afterEpochSelect }));
    checks.push(afterEpochSelect.epochControlsVisible
      ? pass("T-UI-06-epoch-controls-visible-in-epoch-review-mode", { mode: afterEpochSelect.mode, epochControlsVisible: afterEpochSelect.epochControlsVisible })
      : fail("T-UI-06-epoch-controls-visible-in-epoch-review-mode", { afterEpochSelect }));

    await page.locator("[data-testid='waveform-reject-selected']").click();
    const afterReject = await state(page);
    checks.push(afterReject.badSegmentCount >= 1 && afterReject.undoCount >= 1
      ? pass("T-WF-09C-reject-selected-epoch", { afterReject })
      : fail("T-WF-09C-reject-selected-epoch", { afterReject }));

    await page.locator("[data-testid='waveform-undo']").click();
    const afterUndo = await state(page);
    checks.push(afterUndo.badSegmentCount < afterReject.badSegmentCount && afterUndo.redoCount >= 1
      ? pass("T-WF-09D-undo-reject", { afterUndo })
      : fail("T-WF-09D-undo-reject", { before: afterReject, afterUndo }));
    checks.push(!afterUndo.buttons.redoDisabled
      ? pass("T-WF-16-redo-enabled-after-undo", { buttons: afterUndo.buttons })
      : fail("T-WF-16-redo-enabled-after-undo", { buttons: afterUndo.buttons }));

    await page.locator("[data-testid='waveform-redo']").click();
    const afterRedo = await state(page);
    checks.push(afterRedo.badSegmentCount >= afterReject.badSegmentCount
      ? pass("T-WF-09E-redo-reject", { afterRedo })
      : fail("T-WF-09E-redo-reject", { before: afterUndo, afterRedo }));

    await page.locator("[data-testid='waveform-remain-selected']").click();
    const afterRemain = await state(page);
    checks.push(afterRemain.remainSegmentCount >= 1 && afterRemain.badSegmentCount < afterRedo.badSegmentCount
      ? pass("T-WF-09F-remain-overrides-reject", { afterRemain })
      : fail("T-WF-09F-remain-overrides-reject", { before: afterRedo, afterRemain }));

    await page.locator("[data-testid='waveform-mode-mark-bad-segment']").click();
    await drag(page, await freshCanvasBox(page), 0.35, 0.58);
    const afterBadSegment = await state(page);
    checks.push(afterBadSegment.mode === "markBadSegment" && afterBadSegment.candidateBadSegmentCount >= 1 && afterBadSegment.auditActionCount >= 2
      ? pass("T-WF-10-bad-segment-mode-writes-candidate-not-exclusion", { afterBadSegment })
      : fail("T-WF-10-bad-segment-mode-writes-candidate-not-exclusion", { afterBadSegment }));
    checks.push(!afterBadSegment.buttons.confirmCandidatesDisabled && !afterBadSegment.buttons.discardCandidatesDisabled
      ? pass("T-WF-17-candidate-actions-enabled-when-candidates-exist", { buttons: afterBadSegment.buttons })
      : fail("T-WF-17-candidate-actions-enabled-when-candidates-exist", { buttons: afterBadSegment.buttons }));
    checks.push(!afterBadSegment.candidateActionsHidden && afterBadSegment.actionStateText.includes("候选") && afterBadSegment.primaryActionText.includes("确认")
      ? pass("T-UI-03-candidate-actions-appear-only-with-candidates", {
        actionStateText: afterBadSegment.actionStateText,
        primaryActionText: afterBadSegment.primaryActionText,
      })
      : fail("T-UI-03-candidate-actions-appear-only-with-candidates", { afterBadSegment }));

    await page.locator("[data-testid='waveform-shortcut-help']").click();
    const shortcutVisible = await page.locator("#wwShortcutHelp").isVisible();
    checks.push(shortcutVisible
      ? pass("T-WF-10B-shortcut-help-visible")
      : fail("T-WF-10B-shortcut-help-visible"));

    await page.locator("[data-testid='waveform-confirm-candidate-bad-segments']").click();
    const afterConfirmBadSegment = await state(page);
    checks.push(afterConfirmBadSegment.candidateBadSegmentCount === 0 && afterConfirmBadSegment.badSegmentCount >= 1
      ? pass("T-WF-10C-confirm-candidate-writes-exclusion-draft", { afterConfirmBadSegment })
      : fail("T-WF-10C-confirm-candidate-writes-exclusion-draft", { afterConfirmBadSegment }));

    await page.locator("[data-testid='waveform-restore-bad-segment']").click();
    const afterRestoreBadSegment = await state(page);
    checks.push(afterRestoreBadSegment.restoredSegmentCount >= 1
      ? pass("T-WF-10D-restore-confirmed-exclusion", { afterRestoreBadSegment })
      : fail("T-WF-10D-restore-confirmed-exclusion", { afterRestoreBadSegment }));

    await page.locator("[data-testid='waveform-mode-mark-bad-channel']").click();
    const badChannelBox = await freshCanvasBox(page);
    await page.mouse.click(badChannelBox.x + 35, badChannelBox.y + badChannelBox.height * 0.18);
    const afterBadChannel = await state(page);
    checks.push(afterBadChannel.mode === "markBadChannel" && afterBadChannel.badChannelCount >= 1
      ? pass("T-WF-11-bad-channel-mode-click-writes-draft", { afterBadChannel })
      : fail("T-WF-11-bad-channel-mode-click-writes-draft", { afterBadChannel }));

    let clearDialogText = "";
    page.once("dialog", async (dialog) => {
      clearDialogText = dialog.message();
      await dialog.dismiss();
    });
    await page.locator("[data-testid='waveform-clear-all-draft']").click();
    await page.waitForTimeout(120);
    const afterClearDismiss = await state(page);
    checks.push(clearDialogText.includes("草稿") && afterClearDismiss.badChannelCount === afterBadChannel.badChannelCount
      ? pass("T-WF-18-clear-draft-requires-confirmation", { clearDialogText })
      : fail("T-WF-18-clear-draft-requires-confirmation", { clearDialogText, before: afterBadChannel, afterClearDismiss }));

    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForTimeout(150);
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(150);
    const afterScroll = await state(page);
    screenshots.afterScroll = await screenshot(page, "05_after_scroll_persistence.png");
    checks.push(afterScroll.loaded && afterScroll.emptyHidden && afterScroll.visibleChannels > 0 && afterScroll.sensitivityUvPerRow > 0 && afterScroll.mode
      ? pass("T-WF-13-page-scroll-keeps-waveform-state", { afterScroll })
      : fail("T-WF-13-page-scroll-keeps-waveform-state", { afterScroll }));

    const shortPage = await browser.newPage({ viewport: { width: 1280, height: 820 } });
    const shortUrl = frontendUrl
      .replace("teaching_demo=auto", "short_demo=auto")
      .replace("v=e2e", "v=short-coverage-e2e");
    await shortPage.goto(shortUrl, { waitUntil: "domcontentloaded", timeout: 30000 });
    await shortPage.waitForFunction(() => document.querySelector("[data-testid='waveform-workbench-shell']")?.dataset.loaded === "true", null, { timeout: 10000 });
    const shortState = await state(shortPage);
    screenshots.shortData = await screenshot(shortPage, "06_short_data_full_file.png");
    checks.push(shortState.fileDurationSec === 10 && shortState.durationSec === 10 && shortState.startSec === 0 && shortState.dataCoverageState === "ready" && shortState.dataCoverageFraction >= 0.98
      ? pass("T-LOGIC-03-short-file-uses-full-file-window", { shortState })
      : fail("T-LOGIC-03-short-file-uses-full-file-window", { shortState }));
    await shortPage.close();

    const result = {
      status: checks.every((check) => check.passed) ? "passed" : "failed",
      generated_at: new Date().toISOString(),
      frontendUrl,
      screenshots,
      checks,
      finalState: await state(page),
    };
    const outputPath = path.join(evidenceDir, "waveform_workbench_e2e_result.json");
    fs.writeFileSync(outputPath, `${JSON.stringify(result, null, 2)}\n`, "utf8");
    console.log(JSON.stringify({
      status: result.status,
      outputPath,
      failed: checks.filter((check) => !check.passed).map((check) => check.id),
      screenshots,
    }, null, 2));
    if (result.status !== "passed") process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

try {
  await run();
} catch (error) {
  const outputPath = path.join(evidenceDir, "waveform_workbench_e2e_result.json");
  fs.writeFileSync(outputPath, `${JSON.stringify({ status: "failed", error: error.stack || String(error), generated_at: new Date().toISOString(), frontendUrl }, null, 2)}\n`, "utf8");
  console.error(error.stack || String(error));
  process.exit(1);
}
