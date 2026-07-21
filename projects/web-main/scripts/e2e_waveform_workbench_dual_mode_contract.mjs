import fs from "node:fs";
import path from "node:path";
import { chromium, chromiumLaunchOptions } from "./lib/playwright_runtime.mjs";

const repoRoot = process.cwd();
const evidenceDir = process.env.QLANALYSER_WAVEFORM_DUAL_MODE_E2E_DIR
  || path.join(repoRoot, "work", "release_evidence", "20260628-waveform-workbench-dual-mode-contract");
fs.mkdirSync(evidenceDir, { recursive: true });

const api = process.env.QLANALYSER_API_URL || "http://127.0.0.1:8001/api";
const base = process.env.QLANALYSER_FRONTEND_BASE || "http://127.0.0.1:4174";
const url = (workbench, extra = "") => `${base}/waveform-workbench.html?${workbench ? `workbench=${encodeURIComponent(workbench)}&` : ""}${extra ? `${extra}&` : ""}teaching_demo=auto&api=${encodeURIComponent(api)}&v=dual-mode-contract`;

function pass(id, details = {}) {
  return { id, passed: true, ...details };
}

function fail(id, details = {}) {
  return { id, passed: false, ...details };
}

async function waitLoaded(page) {
  await page.goto(page.targetUrl, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForSelector("[data-testid='waveform-workbench-shell']", { timeout: 30000 });
  await page.waitForFunction(() => {
    const shell = document.querySelector("[data-testid='waveform-workbench-shell']");
    return shell?.dataset.loaded === "true" && shell?.dataset.windowCoverage === "ready";
  }, { timeout: 60000 });
}

async function state(page) {
  return page.evaluate(() => {
    const shell = document.querySelector("[data-testid='waveform-workbench-shell']");
    const epochButton = document.querySelector("[data-testid='waveform-mode-epoch-review']");
    const epochControls = document.querySelector("[data-testid='waveform-epoch-controls']");
    const basicSwitch = document.querySelector("[data-testid='waveform-switch-basic']");
    const epochSwitch = document.querySelector("[data-testid='waveform-switch-epoch']");
    const switchWrap = document.querySelector(".ww-workbench-switch");
    const canvasPanel = document.querySelector(".ww-canvas-panel");
    const toolbar = document.querySelector("[data-testid='waveform-governed-toolbar']");
    const context = document.querySelector(".ww-context");
    const sidePanel = document.querySelector(".ww-side-panel");
    const legend = document.querySelector(".ww-legend");
    const draft = document.querySelector("#wwDraftSummary");
    const eventLegend = document.querySelector(".legend-event")?.closest("span");
    const loadTeachingBtn = document.querySelector("#loadTeachingBtn");
    const advancedToggle = document.querySelector("[data-testid='waveform-toolbar-advanced-toggle']");
    const browseGroup = document.querySelector(".ww-browse-group");
    const eventControl = document.querySelector("#wwEventDisplay")?.closest(".ww-control");
    const rangeControls = Array.from(document.querySelectorAll(".ww-range-control"));
    const overviewTrack = document.querySelector("#wwOverviewTrack");
    const isVisible = (el) => !!el && el.getBoundingClientRect().height > 0 && getComputedStyle(el).display !== "none" && !el.hidden;
    const rect = (el) => {
      if (!el) return null;
      const r = el.getBoundingClientRect();
      return { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) };
    };
    return {
      title: document.title,
      heading: document.querySelector(".ww-topbar h1")?.textContent?.trim() || "",
      subtitle: document.querySelector(".ww-topbar p")?.textContent?.trim() || "",
      mode: shell?.dataset.mode || "",
      workbenchMode: shell?.dataset.workbenchMode || "",
      customerMode: shell?.dataset.customerMode || "",
      epochEnabled: shell?.dataset.epochEnabled === "true",
      epochButtonVisible: isVisible(epochButton),
      epochButtonDisabled: !!epochButton?.disabled,
      epochControlsVisible: isVisible(epochControls),
      basicSwitchActive: basicSwitch?.classList.contains("active") || false,
      epochSwitchActive: epochSwitch?.classList.contains("active") || false,
      modeSwitchVisible: shell?.dataset.modeSwitchVisible === "true",
      switchWrapVisible: isVisible(switchWrap),
      locationSearch: window.location.search,
      viewport: { w: window.innerWidth, h: window.innerHeight, scrollWidth: document.documentElement.scrollWidth, clientWidth: document.documentElement.clientWidth },
      canvasPanelRect: rect(canvasPanel),
      toolbarRect: rect(toolbar),
      contextRect: rect(context),
      sidePanelRect: rect(sidePanel),
      legendVisible: isVisible(legend),
      draftVisible: isVisible(draft),
      eventDisplay: shell?.dataset.eventDisplay || "",
      eventLegendVisible: isVisible(eventLegend),
      overviewText: document.querySelector("#wwOverviewCaption")?.textContent || "",
      overviewAriaValueNow: overviewTrack?.getAttribute("aria-valuenow") || "",
      overviewAriaValueText: overviewTrack?.getAttribute("aria-valuetext") || "",
      overviewRepeatsCurrentRange: /当前\s+\d{2}:\d{2}/.test(document.querySelector("#wwOverviewCaption")?.textContent || ""),
      advancedOpen: shell?.dataset.advancedOpen === "true",
      advancedToggleVisible: isVisible(advancedToggle),
      advancedToggleText: advancedToggle?.textContent?.trim() || "",
      browseGroupVisible: isVisible(browseGroup),
      eventControlVisible: isVisible(eventControl),
      rangeControlsVisible: rangeControls.filter(isVisible).length,
      startSec: Number(shell?.dataset.startSec || 0),
      durationSec: Number(shell?.dataset.durationSec || 0),
      fileDurationSec: Number(shell?.dataset.fileDurationSec || 0),
      windowCoverage: shell?.dataset.windowCoverage || "",
      loadTeachingText: loadTeachingBtn?.textContent?.trim() || "",
      loadTeachingPrimary: loadTeachingBtn?.classList.contains("ww-primary") || false,
      actionHintText: document.querySelector("#wwActionHint")?.textContent || "",
      shortcutText: document.querySelector("#wwShortcutHelp")?.textContent || "",
      draftText: document.querySelector("#wwDraftSummary")?.textContent || "",
      hasEpochSelection: shell?.dataset.hasEpochSelection === "true",
      loaded: shell?.dataset.loaded === "true",
    };
  });
}

async function screenshot(page, name) {
  const output = path.join(evidenceDir, name);
  await page.screenshot({ path: output, fullPage: true });
  return output;
}

async function dragCanvas(page) {
  const box = await page.locator("#wwCanvas").boundingBox();
  if (!box) throw new Error("Canvas not found");
  const y = box.y + box.height * 0.45;
  await page.mouse.move(box.x + box.width * 0.25, y);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * 0.45, y, { steps: 8 });
  await page.mouse.up();
}

async function dragOverview(page, fromRatio, toRatio) {
  const box = await page.locator("#wwOverviewTrack").boundingBox();
  if (!box) throw new Error("Overview track not found");
  const y = box.y + box.height / 2;
  await page.mouse.move(box.x + box.width * fromRatio, y);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * toRatio, y, { steps: 10 });
  await page.mouse.up();
  await page.waitForTimeout(1000);
}

const checks = [];
const screenshots = {};
const browser = await chromium.launch(chromiumLaunchOptions({ headless: true }));

try {
  const basic = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  basic.targetUrl = url("");
  await waitLoaded(basic);
  screenshots.basicInitial = await screenshot(basic, "01_basic_initial.png");
  const basicInitial = await state(basic);
  checks.push(basicInitial.workbenchMode === "basic" && !basicInitial.epochEnabled
    ? pass("T-DUAL-01-basic-default-disables-epoch", { basicInitial })
    : fail("T-DUAL-01-basic-default-disables-epoch", { basicInitial }));
  checks.push(!basicInitial.epochButtonVisible && basicInitial.epochButtonDisabled && !basicInitial.epochControlsVisible
    ? pass("T-DUAL-02-basic-hides-epoch-ui", { basicInitial })
    : fail("T-DUAL-02-basic-hides-epoch-ui", { basicInitial }));
  checks.push(!/Epoch/i.test(`${basicInitial.heading} ${basicInitial.subtitle} ${basicInitial.actionHintText} ${basicInitial.shortcutText}`)
    ? pass("T-DUAL-03-basic-copy-does-not-mention-epoch", { basicInitial })
    : fail("T-DUAL-03-basic-copy-does-not-mention-epoch", { basicInitial }));
  checks.push(basicInitial.eventDisplay === "hidden" && !basicInitial.eventLegendVisible && basicInitial.overviewText.includes("事件标记已隐藏")
    ? pass("T-DUAL-03B-basic-default-hides-event-markers", { basicInitial })
    : fail("T-DUAL-03B-basic-default-hides-event-markers", { basicInitial }));
  checks.push(basicInitial.loadTeachingText === "重新载入教学数据" && !basicInitial.loadTeachingPrimary
    ? pass("T-DUAL-03C-loaded-teaching-button-is-demoted", { basicInitial })
    : fail("T-DUAL-03C-loaded-teaching-button-is-demoted", { basicInitial }));
  await basic.keyboard.press("e");
  const basicAfterE = await state(basic);
  checks.push(basicAfterE.mode === "browse" && !basicAfterE.hasEpochSelection
    ? pass("T-DUAL-04-basic-key-e-does-not-enter-epoch-review", { basicAfterE })
    : fail("T-DUAL-04-basic-key-e-does-not-enter-epoch-review", { basicAfterE }));
  await basic.locator("[data-testid='waveform-mode-select-segment']").click();
  await dragCanvas(basic);
  screenshots.basicAfterSelect = await screenshot(basic, "02_basic_after_select.png");
  const basicAfterSelect = await state(basic);
  checks.push(!/Epoch/i.test(basicAfterSelect.draftText) && !basicAfterSelect.hasEpochSelection
    ? pass("T-DUAL-05-basic-selection-summary-has-no-epoch", { basicAfterSelect })
    : fail("T-DUAL-05-basic-selection-summary-has-no-epoch", { basicAfterSelect }));
  await basic.locator("[data-testid='waveform-switch-epoch']").click();
  const basicPageAfterEpochSwitch = await state(basic);
  screenshots.basicPageAfterEpochSwitch = await screenshot(basic, "02b_same_page_after_epoch_switch.png");
  checks.push(basicPageAfterEpochSwitch.workbenchMode === "epoch" && basicPageAfterEpochSwitch.epochEnabled && basicPageAfterEpochSwitch.epochButtonVisible && basicPageAfterEpochSwitch.epochSwitchActive && basicPageAfterEpochSwitch.loaded
    ? pass("T-DUAL-06-same-page-switch-basic-to-epoch", { basicPageAfterEpochSwitch })
    : fail("T-DUAL-06-same-page-switch-basic-to-epoch", { basicPageAfterEpochSwitch }));
  checks.push(basicPageAfterEpochSwitch.eventDisplay === "light" && basicPageAfterEpochSwitch.eventLegendVisible
    ? pass("T-DUAL-06B-epoch-switch-restores-light-event-markers", { basicPageAfterEpochSwitch })
    : fail("T-DUAL-06B-epoch-switch-restores-light-event-markers", { basicPageAfterEpochSwitch }));
  await basic.locator("[data-testid='waveform-switch-basic']").click();
  const basicPageAfterBasicSwitch = await state(basic);
  screenshots.basicPageAfterBasicSwitch = await screenshot(basic, "02c_same_page_after_basic_switch.png");
  checks.push(basicPageAfterBasicSwitch.workbenchMode === "basic" && !basicPageAfterBasicSwitch.epochEnabled && !basicPageAfterBasicSwitch.epochButtonVisible && basicPageAfterBasicSwitch.basicSwitchActive && basicPageAfterBasicSwitch.loaded && !basicPageAfterBasicSwitch.locationSearch.includes("workbench=")
    ? pass("T-DUAL-07-same-page-switch-epoch-back-to-basic", { basicPageAfterBasicSwitch })
    : fail("T-DUAL-07-same-page-switch-epoch-back-to-basic", { basicPageAfterBasicSwitch }));
  checks.push(basicPageAfterBasicSwitch.eventDisplay === "hidden" && !basicPageAfterBasicSwitch.eventLegendVisible
    ? pass("T-DUAL-07B-basic-switch-hides-event-markers-again", { basicPageAfterBasicSwitch })
    : fail("T-DUAL-07B-basic-switch-hides-event-markers-again", { basicPageAfterBasicSwitch }));

  const epoch = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  epoch.targetUrl = url("epoch");
  await waitLoaded(epoch);
  screenshots.epochInitial = await screenshot(epoch, "03_epoch_initial.png");
  const epochInitial = await state(epoch);
  checks.push(epochInitial.workbenchMode === "epoch" && epochInitial.epochEnabled
    ? pass("T-DUAL-08-epoch-mode-enables-epoch", { epochInitial })
    : fail("T-DUAL-08-epoch-mode-enables-epoch", { epochInitial }));
  checks.push(epochInitial.epochButtonVisible && !epochInitial.epochButtonDisabled && !epochInitial.epochControlsVisible
    ? pass("T-DUAL-09-epoch-button-visible-controls-contextual", { epochInitial })
    : fail("T-DUAL-09-epoch-button-visible-controls-contextual", { epochInitial }));
  await epoch.keyboard.press("e");
  const epochAfterE = await state(epoch);
  checks.push(epochAfterE.mode === "epochReview" && epochAfterE.epochControlsVisible
    ? pass("T-DUAL-10-epoch-key-e-enters-epoch-review", { epochAfterE })
    : fail("T-DUAL-10-epoch-key-e-enters-epoch-review", { epochAfterE }));
  await dragCanvas(epoch);
  screenshots.epochAfterSelect = await screenshot(epoch, "04_epoch_after_epoch_select.png");
  const epochAfterSelect = await state(epoch);
  checks.push(epochAfterSelect.hasEpochSelection && /Epoch/i.test(epochAfterSelect.draftText)
    ? pass("T-DUAL-11-epoch-selection-summary-has-epoch", { epochAfterSelect })
    : fail("T-DUAL-11-epoch-selection-summary-has-epoch", { epochAfterSelect }));

  const narrow = await browser.newPage({ viewport: { width: 599, height: 1114 } });
  narrow.targetUrl = url("");
  await waitLoaded(narrow);
  screenshots.basicNarrowSignalFirst = await screenshot(narrow, "05_basic_narrow_signal_first.png");
  const narrowInitial = await state(narrow);
  checks.push(narrowInitial.canvasPanelRect && narrowInitial.toolbarRect && narrowInitial.canvasPanelRect.y < narrowInitial.toolbarRect.y && narrowInitial.canvasPanelRect.y < 760
    ? pass("T-DUAL-12-narrow-basic-shows-waveform-before-full-toolbar", { narrowInitial })
    : fail("T-DUAL-12-narrow-basic-shows-waveform-before-full-toolbar", { narrowInitial }));
  checks.push(narrowInitial.contextRect && narrowInitial.contextRect.h < 180 && narrowInitial.viewport.scrollWidth <= narrowInitial.viewport.clientWidth
    ? pass("T-DUAL-13-narrow-context-is-compact-without-horizontal-overflow", { narrowInitial })
    : fail("T-DUAL-13-narrow-context-is-compact-without-horizontal-overflow", { narrowInitial }));
  checks.push(narrowInitial.sidePanelRect && narrowInitial.sidePanelRect.h < 210 && narrowInitial.sidePanelRect.y < narrowInitial.toolbarRect.y
    ? pass("T-DUAL-14-narrow-action-panel-is-compact-before-toolbar", { narrowInitial })
    : fail("T-DUAL-14-narrow-action-panel-is-compact-before-toolbar", { narrowInitial }));
  checks.push(!narrowInitial.draftVisible && !narrowInitial.legendVisible
    ? pass("T-DUAL-14B-narrow-hides-empty-draft-and-legend-clutter", { narrowInitial })
    : fail("T-DUAL-14B-narrow-hides-empty-draft-and-legend-clutter", { narrowInitial }));
  checks.push(narrowInitial.advancedToggleVisible && !narrowInitial.advancedOpen && !narrowInitial.browseGroupVisible && !narrowInitial.eventControlVisible && narrowInitial.rangeControlsVisible === 0
    ? pass("T-DUAL-16-narrow-default-uses-progressive-disclosure", { narrowInitial })
    : fail("T-DUAL-16-narrow-default-uses-progressive-disclosure", { narrowInitial }));
  checks.push(!narrowInitial.overviewRepeatsCurrentRange
    ? pass("T-DUAL-17-overview-does-not-repeat-current-time-range", { narrowInitial })
    : fail("T-DUAL-17-overview-does-not-repeat-current-time-range", { narrowInitial }));
  checks.push(narrowInitial.overviewText.includes("拖动时间轴") && /当前窗口从/.test(narrowInitial.overviewAriaValueText)
    ? pass("T-DUAL-17B-overview-exposes-drag-affordance-and-aria", { overviewText: narrowInitial.overviewText, overviewAriaValueText: narrowInitial.overviewAriaValueText })
    : fail("T-DUAL-17B-overview-exposes-drag-affordance-and-aria", { narrowInitial }));
  await dragOverview(narrow, 0.25, 0.82);
  const narrowAfterOverviewDrag = await state(narrow);
  checks.push(narrowAfterOverviewDrag.startSec > narrowInitial.startSec + 5 && ["ready", "partial", "loading"].includes(narrowAfterOverviewDrag.windowCoverage)
    ? pass("T-DUAL-20-overview-track-drag-seeks-time-window", { before: narrowInitial.startSec, after: narrowAfterOverviewDrag.startSec, windowCoverage: narrowAfterOverviewDrag.windowCoverage })
    : fail("T-DUAL-20-overview-track-drag-seeks-time-window", { before: narrowInitial, after: narrowAfterOverviewDrag }));
  await narrow.locator("#wwOverviewTrack").focus();
  await narrow.keyboard.press("Home");
  await narrow.waitForTimeout(600);
  const narrowAfterOverviewHome = await state(narrow);
  await narrow.keyboard.press("End");
  await narrow.waitForTimeout(600);
  const narrowAfterOverviewEnd = await state(narrow);
  checks.push(narrowAfterOverviewHome.startSec <= 0.05 && narrowAfterOverviewEnd.startSec >= Math.max(0, narrowAfterOverviewEnd.fileDurationSec - narrowAfterOverviewEnd.durationSec) - 0.5
    ? pass("T-DUAL-21-overview-track-keyboard-home-end-seeks", { homeStart: narrowAfterOverviewHome.startSec, endStart: narrowAfterOverviewEnd.startSec })
    : fail("T-DUAL-21-overview-track-keyboard-home-end-seeks", { home: narrowAfterOverviewHome, end: narrowAfterOverviewEnd }));
  await narrow.locator("[data-testid='waveform-toolbar-advanced-toggle']").click();
  const narrowAdvanced = await state(narrow);
  screenshots.basicNarrowAdvancedOpen = await screenshot(narrow, "05b_basic_narrow_advanced_open.png");
  checks.push(narrowAdvanced.advancedOpen && narrowAdvanced.browseGroupVisible && narrowAdvanced.eventControlVisible && narrowAdvanced.rangeControlsVisible >= 1 && /收起/.test(narrowAdvanced.advancedToggleText)
    ? pass("T-DUAL-18-narrow-advanced-controls-expand-on-demand", { narrowAdvanced })
    : fail("T-DUAL-18-narrow-advanced-controls-expand-on-demand", { narrowAdvanced }));

  const customerBasic = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  customerBasic.targetUrl = url("", "mode_switch=hidden");
  await waitLoaded(customerBasic);
  screenshots.customerBasicHiddenSwitch = await screenshot(customerBasic, "06_customer_basic_hidden_switch.png");
  const customerBasicState = await state(customerBasic);
  checks.push(customerBasicState.workbenchMode === "basic" && !customerBasicState.epochEnabled && !customerBasicState.modeSwitchVisible && !customerBasicState.switchWrapVisible
    ? pass("T-DUAL-15-customer-basic-can-hide-mode-switch", { customerBasicState })
    : fail("T-DUAL-15-customer-basic-can-hide-mode-switch", { customerBasicState }));
  checks.push(customerBasicState.canvasPanelRect && customerBasicState.toolbarRect && customerBasicState.canvasPanelRect.y < customerBasicState.toolbarRect.y
    ? pass("T-DUAL-19-customer-desktop-keeps-waveform-before-toolbar", { customerBasicState })
    : fail("T-DUAL-19-customer-desktop-keeps-waveform-before-toolbar", { customerBasicState }));

  const customerClean = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  customerClean.targetUrl = url("", "mode_switch=hidden&customer_mode=clean");
  await waitLoaded(customerClean);
  screenshots.customerCleanDesktop = await screenshot(customerClean, "07_customer_clean_desktop.png");
  const customerCleanState = await state(customerClean);
  checks.push(customerCleanState.customerMode === "clean" && customerCleanState.advancedToggleVisible && !customerCleanState.advancedOpen && !customerCleanState.browseGroupVisible && !customerCleanState.eventControlVisible
    ? pass("T-DUAL-22-customer-clean-desktop-collapses-advanced-controls", { customerCleanState })
    : fail("T-DUAL-22-customer-clean-desktop-collapses-advanced-controls", { customerCleanState }));
} finally {
  await browser.close();
}

const failed = checks.filter((item) => !item.passed);
const result = {
  status: failed.length ? "failed" : "passed",
  checks,
  failed: failed.map((item) => item.id),
  screenshots,
};
const outputPath = path.join(evidenceDir, "waveform_workbench_dual_mode_contract_result.json");
fs.writeFileSync(outputPath, JSON.stringify(result, null, 2), "utf8");
console.log(JSON.stringify({ status: result.status, outputPath, failed: result.failed, screenshots }, null, 2));
if (failed.length) process.exitCode = 1;
