import { createWaveformApi, normalizeWaveformPreview, waveformArtifactFromList } from "./waveform-workbench-adapter.js?v=20260627-wf1";

const params = new URLSearchParams(window.location.search);
const api = createWaveformApi(params.get("api") || "http://127.0.0.1:8001/api");
const workbenchModeParam = String(params.get("workbench") || params.get("workbench_mode") || params.get("preview_mode") || "basic").toLowerCase();
const modeSwitchParam = String(params.get("mode_switch") || params.get("switch") || "").toLowerCase();
const customerModeParam = String(params.get("customer_mode") || params.get("ui_mode") || "clean").toLowerCase();
const workbenchConfig = {
  mode: ["epoch", "epoch_review", "epilepsy", "sleep", "sleep_stage", "sleep_staging"].includes(workbenchModeParam) ? "epoch" : "basic",
  showModeSwitch: !["0", "false", "hidden", "off"].includes(modeSwitchParam),
  customerMode: ["default", "full", "dev"].includes(customerModeParam) ? "default" : "clean",
};
const isEpochWorkbench = () => workbenchConfig.mode === "epoch";
const constants = Object.freeze({
  wheelPanRatio: 0.08,
  arrowPanRatio: 0.10,
  pagePanRatio: 1.00,
  zoomFactor: 1.20,
  minDurationSec: 2,
  maxDurationSec: 30,
  gainStepRatio: 1.20,
  minSensitivityUvPerRow: 5,
  maxSensitivityUvPerRow: 1000,
});
const qs = (selector) => document.querySelector(selector);
const qsa = (selector) => Array.from(document.querySelectorAll(selector));
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const state = {
  project: null,
  file: null,
  task: null,
  payload: null,
  mode: "browse",
  advancedOpen: false,
  viewport: {
    startSec: 0,
    durationSec: 24,
    fileDurationSec: 60,
    displaySampleRateHz: 200,
    visibleChannels: 8,
    sensitivityUvPerRow: 200,
    rawOrFilter: "Raw",
  },
  eventDisplay: isEpochWorkbench() ? "light" : "hidden",
  eventDisplayManual: false,
  epoch: {
    lengthSec: 4,
    visibleEpochs: 6,
    selectedRange: null,
  },
  cache: {
    chunks: [],
    pending: null,
    loading: false,
    lastMiss: null,
    activeAbortController: null,
    prefetchControllers: new Map(),
    lastReloadSource: "",
    stats: {
      chunkRequests: 0,
      chunkAborts: 0,
      chunkFallbacks: 0,
      cacheHits: 0,
      prefetchRequests: 0,
      prefetchHits: 0,
    },
  },
  autoSensitivityApplied: false,
  transient: { hoverTimeSec: null, hoverChannel: "", drag: null, middlePan: null, overviewDrag: null },
  draft: {
    selectedSegment: null,
    candidateBadSegments: [],
    badSegments: [],
    remainSegments: [],
    restoredSegments: [],
    badChannels: [],
    restoredBadChannels: [],
    auditActions: [],
    undoStack: [],
    redoStack: [],
  },
  requestSeq: 0,
  viewportReloadTimer: null,
  teachingLoadStarted: false,
};
window.waveformWorkbenchDebug = state;

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, Number(value) || 0));
}

function formatHms(sec = 0) {
  const s = Math.max(0, Math.floor(sec));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const r = s % 60;
  return [h, m, r].map((value) => String(value).padStart(2, "0")).join(":");
}

function fileName(file = state.file) {
  return file?.metadata_json?.label || file?.original_filename || file?.source_name || file?.id || "EEG 数据";
}

function modeLabel(mode = state.mode) {
  return {
    browse: "浏览模式",
    selectSegment: "选段模式",
    epochReview: isEpochWorkbench() ? "Epoch 复核" : "浏览模式",
    markBadSegment: "候选坏段",
    markBadChannel: "坏道标记",
  }[mode] || "浏览模式";
}

function updateText(id, text) {
  const el = qs(id);
  if (el) el.textContent = text;
}

function syncWorkbenchChrome() {
  const title = qs(".ww-topbar h1");
  const subtitle = qs(".ww-topbar p");
  const writeHint = qs(".ww-toolbar-band-write .ww-band-head span");
  const shortcutHelp = qs("#wwShortcutHelp");
  const epoch = isEpochWorkbench();
  document.title = epoch
    ? "脑电波形 Epoch 复核工作台 | QLanalyser"
    : "脑电基础波形预览与数据准备 | QLanalyser";
  if (title) title.textContent = epoch ? "脑电波形 Epoch 复核工作台" : "脑电基础波形预览与数据准备";
  if (subtitle) {
    subtitle.textContent = epoch
      ? "用于癫痫分析、睡眠分期等按片段复核场景；支持按 Epoch 或时间段标记剔除/保留，所有操作只写入准备草稿。"
      : "用于数据准备阶段的连续 EEG 快速预览；可浏览、调整显示、标记时间段或坏道，不显示分段复核设置。";
  }
  if (writeHint) {
    writeHint.textContent = epoch
      ? "浏览模式不写草稿；选段、坏段、坏道、Epoch 复核才写入准备草稿。"
      : "浏览模式不写草稿；选段、坏段、坏道才写入准备草稿。";
  }
  if (shortcutHelp) {
    shortcutHelp.textContent = epoch
      ? "浏览：滚轮水平浏览，PageUp/PageDown 翻页，Left/Right 小步移动。缩放：Ctrl/Cmd + 滚轮调整时间窗，+/- 调整振幅。标注：S 选段，E Epoch 复核，X 候选坏段，C 坏道，B/Esc 回到浏览，Z 撤销，Y 重做。"
      : "浏览：滚轮水平浏览，PageUp/PageDown 翻页，Left/Right 小步移动。缩放：Ctrl/Cmd + 滚轮调整时间窗，+/- 调整振幅。标注：S 选段，X 候选坏段，C 坏道，B/Esc 回到浏览，Z 撤销，Y 重做。";
  }
}

async function withTimeout(promise, ms, label) {
  let timer = null;
  try {
    return await Promise.race([
      promise,
      new Promise((_, reject) => {
        timer = window.setTimeout(() => reject(new Error(`${label} 超时`)), ms);
      }),
    ]);
  } finally {
    if (timer) window.clearTimeout(timer);
  }
}

function cloneDraft() {
  return JSON.parse(JSON.stringify({
    selectedSegment: state.draft.selectedSegment,
    candidateBadSegments: state.draft.candidateBadSegments,
    badSegments: state.draft.badSegments,
    remainSegments: state.draft.remainSegments,
    restoredSegments: state.draft.restoredSegments,
    badChannels: state.draft.badChannels,
    restoredBadChannels: state.draft.restoredBadChannels,
    selectedEpochRange: isEpochWorkbench() ? state.epoch.selectedRange : null,
  }));
}

function restoreDraft(snapshot) {
  state.draft.selectedSegment = snapshot.selectedSegment || null;
  state.draft.candidateBadSegments = snapshot.candidateBadSegments || [];
  state.draft.badSegments = snapshot.badSegments || [];
  state.draft.remainSegments = snapshot.remainSegments || [];
  state.draft.restoredSegments = snapshot.restoredSegments || [];
  state.draft.badChannels = snapshot.badChannels || [];
  state.draft.restoredBadChannels = snapshot.restoredBadChannels || [];
  state.epoch.selectedRange = snapshot.selectedEpochRange || null;
}

function pushHistory(action) {
  state.draft.undoStack.push({ action, snapshot: cloneDraft(), at: new Date().toISOString() });
  if (state.draft.undoStack.length > 80) state.draft.undoStack.shift();
  state.draft.redoStack = [];
}

function recordAction(action, detail = {}) {
  state.draft.auditActions.push({ action, ...detail, created_at: new Date().toISOString() });
}

function currentSelectionSegment() {
  if (isEpochWorkbench() && state.epoch.selectedRange) {
    return {
      start_sec: state.epoch.selectedRange.start_sec,
      end_sec: state.epoch.selectedRange.end_sec,
      start_epoch: state.epoch.selectedRange.start_epoch,
      end_epoch: state.epoch.selectedRange.end_epoch,
    };
  }
  return state.draft.selectedSegment;
}

function syncContext() {
  updateText("#wwFileName", state.file ? fileName() : "等待加载");
  updateText("#wwDataState", state.payload ? `${state.payload.channels.length} 通道 · ${state.payload.display_sample_rate_hz} Hz` : (state.file ? "已选择，等待波形" : "未加载"));
  updateText("#wwPrepState", state.project ? "教学/当前准备记录" : "未确认");
  const loadTeaching = qs("#loadTeachingBtn");
  if (loadTeaching) {
    loadTeaching.textContent = state.payload ? "重新载入示例数据" : "加载示例数据";
    loadTeaching.classList.toggle("ww-primary", !state.payload);
    loadTeaching.classList.toggle("ww-ghost", Boolean(state.payload));
  }
}

function syncControls() {
  if (!isEpochWorkbench() && state.mode === "epochReview") {
    state.mode = "browse";
    state.epoch.selectedRange = null;
  }
  const vp = state.viewport;
  vp.durationSec = clamp(vp.durationSec, constants.minDurationSec, Math.min(constants.maxDurationSec, vp.fileDurationSec || constants.maxDurationSec));
  vp.startSec = clamp(vp.startSec, 0, Math.max(0, (vp.fileDurationSec || vp.durationSec) - vp.durationSec));

  const timescale = qs("#wwTimescale");
  if (timescale) {
    const values = Array.from(timescale.options).map((option) => Number(option.value));
    Array.from(timescale.options).forEach((option) => {
      const value = Number(option.value);
      option.disabled = Number.isFinite(value) && value > vp.fileDurationSec + 1e-6;
    });
    timescale.value = String(values.reduce((a, b) => Math.abs(b - vp.durationSec) < Math.abs(a - vp.durationSec) ? b : a, values[0] || 24));
  }
  const preset = qs("#wwSensitivityPreset");
  if (preset) {
    const values = Array.from(preset.options).map((option) => Number(option.value));
    preset.value = String(values.reduce((a, b) => Math.abs(b - vp.sensitivityUvPerRow) < Math.abs(a - vp.sensitivityUvPerRow) ? b : a, values[0] || 200));
  }
  const sens = qs("#wwSensitivity");
  if (sens) sens.value = String(Math.round(vp.sensitivityUvPerRow));
  const ch = qs("#wwChannels");
  if (ch) {
    ch.max = String(Math.max(1, state.payload?.channels?.length || 32));
    ch.value = String(vp.visibleChannels);
  }
  const epochLength = qs("#wwEpochLength");
  if (epochLength) epochLength.value = String(state.epoch.lengthSec);
  const visibleEpochs = qs("#wwVisibleEpochs");
  if (visibleEpochs) visibleEpochs.value = String(state.epoch.visibleEpochs);
  const eventDisplay = qs("#wwEventDisplay");
  if (eventDisplay) eventDisplay.value = state.eventDisplay;
  const eventLegend = qs(".legend-event")?.closest("span");
  if (eventLegend) eventLegend.hidden = state.eventDisplay === "hidden";
  const epochButton = qs("[data-testid='waveform-mode-epoch-review']");
  if (epochButton) {
    epochButton.hidden = !isEpochWorkbench();
    epochButton.disabled = !isEpochWorkbench();
  }
  const epochControlsWrap = qs("[data-testid='waveform-epoch-controls']");
  if (epochControlsWrap) epochControlsWrap.hidden = !isEpochWorkbench();
  qsa("[data-workbench-switch]").forEach((btn) => {
    const active = btn.dataset.workbenchSwitch === workbenchConfig.mode;
    btn.classList.toggle("active", active);
    btn.setAttribute("aria-pressed", active ? "true" : "false");
  });
  const switchWrap = qs(".ww-workbench-switch");
  if (switchWrap) switchWrap.hidden = !workbenchConfig.showModeSwitch;
  const advancedToggle = qs("#wwAdvancedToggle");
  if (advancedToggle) {
    advancedToggle.textContent = state.advancedOpen ? "收起高级设置" : "更多设置";
    advancedToggle.setAttribute("aria-expanded", state.advancedOpen ? "true" : "false");
  }

  updateText("#wwSensitivityLabel", `${Math.round(vp.sensitivityUvPerRow)} uV/row`);
  updateText("#wwChannelsLabel", String(vp.visibleChannels));
  qsa("[data-mode]").forEach((btn) => btn.classList.toggle("active", btn.dataset.mode === state.mode));
  const wrap = qs("#wwCanvasWrap");
  if (wrap) {
    wrap.setAttribute("data-mode", state.mode);
    wrap.setAttribute("data-coverage", currentWindowCoverage());
  }
  syncTestState();
  syncOverview();
}

function syncTestState() {
  const shell = qs("[data-testid='waveform-workbench-shell']");
  if (!shell) return;
  const vp = state.viewport;
  const start = vp.startSec;
  const end = start + vp.durationSec;
  const authoritative = authoritativeChunkForWindow(start, end);
  shell.dataset.workbenchMode = workbenchConfig.mode;
  shell.dataset.epochEnabled = isEpochWorkbench() ? "true" : "false";
  shell.dataset.modeSwitchVisible = workbenchConfig.showModeSwitch ? "true" : "false";
  shell.dataset.mode = state.mode;
  shell.dataset.advancedOpen = state.advancedOpen ? "true" : "false";
  shell.dataset.customerMode = workbenchConfig.customerMode;
  shell.dataset.overviewDragging = state.transient.overviewDrag ? "true" : "false";
  shell.dataset.loaded = state.payload ? "true" : "false";
  shell.dataset.fileName = state.file ? fileName() : "";
  shell.dataset.startSec = String(Number(vp.startSec.toFixed(3)));
  shell.dataset.durationSec = String(Number(vp.durationSec.toFixed(3)));
  shell.dataset.fileDurationSec = String(Number(vp.fileDurationSec.toFixed(3)));
  shell.dataset.visibleChannels = String(vp.visibleChannels);
  shell.dataset.sensitivityUvPerRow = String(Number(vp.sensitivityUvPerRow.toFixed(3)));
  shell.dataset.epochLengthSec = String(state.epoch.lengthSec);
  shell.dataset.visibleEpochs = String(state.epoch.visibleEpochs);
  shell.dataset.hasEpochSelection = state.epoch.selectedRange ? "true" : "false";
  shell.dataset.selectedEpochStart = state.epoch.selectedRange ? String(state.epoch.selectedRange.start_epoch) : "";
  shell.dataset.selectedEpochEnd = state.epoch.selectedRange ? String(state.epoch.selectedRange.end_epoch) : "";
  shell.dataset.candidateBadSegmentCount = String(state.draft.candidateBadSegments.length);
  shell.dataset.badSegmentCount = String(state.draft.badSegments.length);
  shell.dataset.remainSegmentCount = String(state.draft.remainSegments.length);
  shell.dataset.restoredSegmentCount = String(state.draft.restoredSegments.length);
  shell.dataset.badChannelCount = String(state.draft.badChannels.length);
  shell.dataset.hasSelectedSegment = state.draft.selectedSegment ? "true" : "false";
  shell.dataset.auditActionCount = String(state.draft.auditActions.length);
  shell.dataset.undoCount = String(state.draft.undoStack.length);
  shell.dataset.redoCount = String(state.draft.redoStack.length);
  shell.dataset.eventDisplay = state.eventDisplay;
  shell.dataset.waveformSource = state.payload?.source || "";
  shell.dataset.waveformSchemaVersion = state.payload?.schema_version || "";
  shell.dataset.cacheChunkCount = String(state.cache.chunks.length);
  shell.dataset.loadingState = state.cache.loading ? "loading" : "ready";
  shell.dataset.waveformLastReloadSource = state.cache.lastReloadSource || "";
  shell.dataset.waveformCacheHits = String(state.cache.stats.cacheHits);
  shell.dataset.waveformChunkRequests = String(state.cache.stats.chunkRequests);
  shell.dataset.waveformChunkAborts = String(state.cache.stats.chunkAborts);
  shell.dataset.waveformChunkFallbacks = String(state.cache.stats.chunkFallbacks);
  shell.dataset.waveformPrefetchRequests = String(state.cache.stats.prefetchRequests);
  shell.dataset.waveformPrefetchInFlight = String(state.cache.prefetchControllers.size);
  shell.dataset.cachePendingRange = state.cache.pending ? `${state.cache.pending.start_sec.toFixed(3)}-${state.cache.pending.end_sec.toFixed(3)}` : "";
  shell.dataset.cacheLoadedRanges = loadedRangesText();
  shell.dataset.windowCoverage = currentWindowCoverage();
  const coverage = currentDataCoverage();
  const hasAnyWaveformData = Boolean(state.payload?.data_uv?.length || state.cache.chunks.some((chunk) => chunk?.data_uv?.length) || coverage.hasData);
  qs("#wwEmpty")?.classList.toggle("hidden", hasAnyWaveformData);
  shell.dataset.dataCoverageState = coverage.state;
  shell.dataset.dataCoverageRange = coverage.hasData ? `${coverage.start.toFixed(3)}-${coverage.end.toFixed(3)}` : "";
  shell.dataset.dataCoverageFraction = String(Number(coverage.fraction.toFixed(3)));
  shell.dataset.usesRemappedFallback = "false";
  shell.dataset.renderPolicy = "single_authoritative_chunk";
  shell.dataset.authoritativeChunkRange = authoritative ? chunkRangeText(authoritative) : "";
  shell.dataset.authoritativeChunkCountForWindow = authoritative ? "1" : "0";
  shell.dataset.overlappingChunkCountForWindow = String(overlappingChunkCountForWindow(start, end));
}

function overviewStartFromClientX(clientX) {
  const track = qs("#wwOverviewTrack");
  if (!track) return state.viewport.startSec;
  const rect = track.getBoundingClientRect();
  const total = Math.max(0.001, state.viewport.fileDurationSec || 0);
  const maxStart = Math.max(0, total - state.viewport.durationSec);
  const ratio = clamp((clientX - rect.left) / Math.max(1, rect.width), 0, 1);
  return clamp(ratio * total - state.viewport.durationSec / 2, 0, maxStart);
}

function seekOverviewTo(clientX, source = "overview") {
  const next = overviewStartFromClientX(clientX);
  if (!Number.isFinite(next)) return;
  state.viewport.startSec = next;
  state.epoch.selectedRange = null;
  syncAll();
  draw();
  if (source === "overview-click") scheduleViewportReload(source);
}

function syncStatus() {
  const vp = state.viewport;
  const selected = currentSelectionSegment();
  const selectedForAction = clampSegmentToCurrentDataCoverage(selected);
  const coverage = currentDataCoverage();
  const status = qs("#wwStatus");
  if (status) {
    const draftCount = state.draft.candidateBadSegments.length + state.draft.badSegments.length + state.draft.remainSegments.length + state.draft.badChannels.length;
    const pieces = [];
    if (selected) pieces.push(["选区", `${selected.start_sec.toFixed(2)}-${selected.end_sec.toFixed(2)} s`]);
    if (draftCount) pieces.push(["草稿", `${draftCount} 项`]);
    const safety = state.mode === "browse" ? "" : "只写入准备草稿，不修改原始 EEG。";
    status.innerHTML = pieces.map(([k, v]) => `<span><b>${k}</b>${v}</span>`).join("")
      + (safety ? `<em>${safety}</em>` : "");
    status.hidden = pieces.length === 0 && !safety;
  }

  const draft = qs("#wwDraftSummary");
  if (draft) {
    const epochText = isEpochWorkbench() && state.epoch.selectedRange
      ? `Epoch ${state.epoch.selectedRange.start_epoch}-${state.epoch.selectedRange.end_epoch}`
      : "无";
    const selectedText = selected ? `${selected.start_sec.toFixed(2)}-${selected.end_sec.toFixed(2)} s` : "无";
    const badChannels = state.draft.badChannels.map((item) => item.channel || item).join(", ") || "无";
    const hasDraft = selected || state.draft.candidateBadSegments.length || state.draft.badSegments.length || state.draft.remainSegments.length || state.draft.badChannels.length;
    if (hasDraft) {
      const items = [
        `<span>当前选区<b>${selectedText}</b></span>`,
        isEpochWorkbench() ? `<span>Epoch<b>${epochText}</b></span>` : "",
        `<span>候选坏段<b>${state.draft.candidateBadSegments.length} 段</b></span>`,
        `<span>剔除 Reject<b>${state.draft.badSegments.length} 段</b></span>`,
        `<span>保留 Remain<b>${state.draft.remainSegments.length} 段</b></span>`,
        `<span>坏道<b>${badChannels}</b></span>`,
        `<span>可恢复<b>${state.draft.restoredSegments.length} 段</b></span>`,
        `<span>撤销/重做<b>${state.draft.undoStack.length}/${state.draft.redoStack.length}</b></span>`,
      ].filter(Boolean);
      draft.innerHTML = `<div class="ww-draft-grid">${items.join("")}</div>`;
    } else {
      draft.textContent = "暂无草稿。";
    }
    draft.classList.toggle("is-empty", !hasDraft);
  }

  const actionState = qs("#wwActionState");
  const actionHint = qs("#wwActionHint");
  const primary = qs("#wwPrimaryAction");
  const candidateActions = qs(".ww-candidate-actions");
  const reviewActions = qs(".ww-review-actions");
  const historyActions = qs(".ww-history-actions");
  const dangerActions = qs(".ww-danger-zone");
  const hasCandidates = state.draft.candidateBadSegments.length > 0;
  const hasSelection = Boolean(selectedForAction);
  const hasHistory = state.draft.undoStack.length > 0 || state.draft.redoStack.length > 0 || state.draft.badSegments.length > 0;
  const hasAnyDraft = hasDraftState();
  const setActionClass = (el, cls) => {
    if (!el) return;
    el.classList.remove("ready", "warning", "danger");
    if (cls) el.classList.add(cls);
  };
  const setPrimaryVisible = (visible) => {
    primary?.classList.toggle("is-empty", !visible);
  };
  if (candidateActions) candidateActions.classList.toggle("is-empty", !hasCandidates);
  if (reviewActions) reviewActions.classList.toggle("is-empty", !hasSelection);
  if (historyActions) historyActions.classList.toggle("is-empty", !hasHistory);
  if (dangerActions) dangerActions.classList.toggle("is-empty", !hasAnyDraft);
  if (actionState && actionHint && primary) {
    if (hasCandidates) {
      actionState.textContent = "有候选坏段";
      primary.textContent = `已有 ${state.draft.candidateBadSegments.length} 段候选坏段。请确认写入 Reject，或取消候选继续观察。`;
      actionHint.textContent = "候选坏段只是草稿，确认后才进入 Reject；不会修改原始 EEG。";
      setActionClass(actionState, "warning");
      setActionClass(primary, "warning");
      setPrimaryVisible(true);
    } else if (hasSelection) {
      actionState.textContent = "已选中波形";
      primary.textContent = `当前选区 ${selectedForAction.start_sec.toFixed(2)}-${selectedForAction.end_sec.toFixed(2)} s。请判断是否剔除 Reject 或保留 Remain。`;
      actionHint.textContent = "Reject 表示从后续分析排除；Remain 表示明确保留。操作会进入准备草稿，可撤销。";
      setActionClass(actionState, "ready");
      setActionClass(primary, "ready");
      setPrimaryVisible(true);
    } else if (!coverage.hasData) {
      actionState.textContent = "等待波形";
      primary.textContent = "当前时间窗暂无可写入的波形点，准备草稿未更改。";
      actionHint.textContent = "等当前时间窗读取完成后，再进行选段、坏段或坏道标记。";
      setActionClass(actionState, "warning");
      setActionClass(primary, "warning");
      setPrimaryVisible(true);
    } else {
      actionState.textContent = "等待选择";
      primary.textContent = "请先在波形上拖拽选择一段，或切换到 Epoch 复核批量选择。";
      actionHint.textContent = isEpochWorkbench()
        ? "当前是安全浏览状态，不会写入草稿。只有选段、Epoch 复核、候选坏段或坏道模式会产生准备记录。"
        : "当前是基础波形预览状态，不会写入草稿。只有选段、候选坏段或坏道模式会产生准备记录。";
      setActionClass(actionState, "");
      setActionClass(primary, "");
      setPrimaryVisible(false);
    }
  }
}

function hasDraftState() {
  return Boolean(
    state.draft.selectedSegment
    || (isEpochWorkbench() && state.epoch.selectedRange)
    || state.draft.candidateBadSegments.length
    || state.draft.badSegments.length
    || state.draft.remainSegments.length
    || state.draft.restoredSegments.length
    || state.draft.badChannels.length
    || state.draft.restoredBadChannels.length
  );
}

function setDisabled(selector, disabled) {
  const el = qs(selector);
  if (el) el.disabled = Boolean(disabled);
}

function syncActionButtons() {
  const hasSelection = Boolean(segmentWithinCurrentDataCoverage(currentSelectionSegment()));
  const writeWindowReady = currentDataCoverage().hasData;
  const hasCandidates = state.draft.candidateBadSegments.length > 0;
  const hasRejected = state.draft.badSegments.length > 0;
  const hasDraft = hasDraftState();
  setDisabled("#wwRejectBtn", !hasSelection || !writeWindowReady);
  setDisabled("#wwRemainBtn", !hasSelection || !writeWindowReady);
  setDisabled("#wwUndoBtn", state.draft.undoStack.length === 0);
  setDisabled("#wwRedoBtn", state.draft.redoStack.length === 0);
  setDisabled("#wwCancelAllBtn", !hasDraft);
  setDisabled("#wwConfirmBadSegmentsBtn", !hasCandidates);
  setDisabled("#wwDiscardCandidatesBtn", !hasCandidates);
  setDisabled("#wwRestoreSegmentBtn", !hasRejected);
  setDisabled("#wwClearDraftBtn", !hasDraft);
}

function payloadWindow(payload) {
  const times = (payload?.times_sec || []).map(Number).filter(Number.isFinite);
  const start = times.length ? Math.min(...times) : Number(payload?.start_sec || 0);
  const end = times.length ? Math.max(...times) : start + Number(payload?.duration_sec || 0);
  return { start_sec: start, end_sec: end };
}

function isTeachingContinuityDataset() {
  const metadata = state.file?.metadata_json || {};
  return Boolean(
    params.get("teaching_demo")
    || metadata.protected_teaching_dataset
    || /teaching|oddball/i.test(fileName())
  );
}

function addPayloadToCache(payload) {
  if (!payload?.data_uv?.length || !payload?.times_sec?.length) return;
  const win = payloadWindow(payload);
  const chunk = {
    start_sec: win.start_sec,
    end_sec: win.end_sec,
    times_sec: payload.times_sec.map(Number),
    data_uv: payload.data_uv,
    events: payload.events || [],
    channels: payload.channels || [],
  };
  const sameChunk = (item) => Math.abs(item.start_sec - chunk.start_sec) < 1e-3
    && Math.abs(item.end_sec - chunk.end_sec) < 1e-3;
  state.cache.chunks = state.cache.chunks.filter((item) => !sameChunk(item));
  state.cache.chunks.push(chunk);
  state.cache.chunks.sort((a, b) => a.start_sec - b.start_sec);
  if (state.cache.chunks.length > 24) state.cache.chunks.splice(0, state.cache.chunks.length - 24);
}

function loadedRangesText() {
  return state.cache.chunks
    .map((chunk) => `${chunk.start_sec.toFixed(1)}-${chunk.end_sec.toFixed(1)}s`)
    .join(", ");
}

function chunkRangeText(chunk) {
  return chunk ? `${Number(chunk.start_sec).toFixed(3)}-${Number(chunk.end_sec).toFixed(3)}` : "";
}

function chunkOverlapSec(chunk, start, end) {
  return Math.max(0, Math.min(Number(chunk.end_sec), end) - Math.max(Number(chunk.start_sec), start));
}

function overlappingChunkCountForWindow(start, end) {
  return state.cache.chunks.filter((chunk) => chunkOverlapSec(chunk, start, end) > 0).length;
}

function pointCountInWindow(chunk, start, end) {
  return (chunk?.times_sec || []).reduce((count, time) => count + (time >= start - 1e-6 && time <= end + 1e-6 ? 1 : 0), 0);
}

function authoritativeChunkForWindow(start, end) {
  let best = null;
  state.cache.chunks.forEach((chunk, index) => {
    const overlap = chunkOverlapSec(chunk, start, end);
    if (overlap <= 0) return;
    const pointCount = pointCountInWindow(chunk, start, end);
    if (pointCount <= 0) return;
    const candidate = { chunk, index, overlap, pointCount };
    if (!best
      || candidate.overlap > best.overlap + 1e-6
      || (Math.abs(candidate.overlap - best.overlap) <= 1e-6 && candidate.pointCount > best.pointCount)
      || (Math.abs(candidate.overlap - best.overlap) <= 1e-6 && candidate.pointCount === best.pointCount && candidate.index > best.index)) {
      best = candidate;
    }
  });
  return best?.chunk || null;
}

function currentWindowCoverage() {
  return currentDataCoverage().state;
}

function currentDataCoverage() {
  const start = state.viewport.startSec;
  const end = start + state.viewport.durationSec;
  const chunk = authoritativeChunkForWindow(start, end);
  if (!chunk) return { state: state.cache.loading ? "loading" : "missing", hasData: false, start, end: start, fraction: 0, windowStart: start, windowEnd: end };
  const coverageStart = Math.max(start, Number(chunk.start_sec));
  const coverageEnd = Math.min(end, Number(chunk.end_sec));
  const fraction = clamp((coverageEnd - coverageStart) / Math.max(0.001, end - start), 0, 1);
  const coversStart = chunk.start_sec <= start + 0.05 && chunk.end_sec >= start + 0.05;
  const coversEnd = chunk.start_sec <= end - 0.05 && chunk.end_sec >= end - 0.05;
  return {
    state: coversStart && coversEnd ? "ready" : "partial",
    hasData: coverageEnd > coverageStart,
    start: coverageStart,
    end: coverageEnd,
    fraction,
    windowStart: start,
    windowEnd: end,
  };
}

function timeInCurrentDataCoverage(timeSec) {
  const coverage = currentDataCoverage();
  return coverage.hasData && timeSec >= coverage.start - 1e-6 && timeSec <= coverage.end + 1e-6;
}

function clampSegmentToCurrentDataCoverage(seg) {
  if (!seg) return null;
  const coverage = currentDataCoverage();
  if (!coverage.hasData) return null;
  const start = Math.max(Number(seg.start_sec), coverage.start);
  const end = Math.min(Number(seg.end_sec), coverage.end);
  if (!Number.isFinite(start) || !Number.isFinite(end) || end - start < 0.05) return null;
  const next = { ...seg, start_sec: start, end_sec: end };
  if (seg.start_epoch !== undefined || seg.end_epoch !== undefined) {
    const length = Math.max(0.1, Number(state.epoch.lengthSec || 4));
    next.start_epoch = Math.floor(start / length);
    next.end_epoch = Math.max(next.start_epoch, Math.floor(Math.max(start, end - 1e-6) / length));
  }
  return next;
}

function segmentWithinCurrentDataCoverage(seg) {
  return clampSegmentToCurrentDataCoverage(seg);
}

function syncLoadingOverlay() {
  const overlay = qs("#wwLoadingOverlay");
  if (!overlay) return;
  const coverage = currentWindowCoverage();
  const show = state.cache.loading || coverage === "missing" || coverage === "partial";
  overlay.hidden = !show;
  const pending = state.cache.pending;
  overlay.textContent = pending
    ? `正在读取 ${formatHms(pending.start_sec)}-${formatHms(pending.end_sec)}，不会用旧波形伪装新时间窗`
    : (coverage === "partial" ? "当前窗口部分数据待读取" : "正在读取当前时间窗");
}

function syncOverview() {
  const track = qs("#wwOverviewTrack");
  const caption = qs("#wwOverviewCaption");
  if (!track) return;
  const total = Math.max(0.001, state.viewport.fileDurationSec || 0);
  track.setAttribute("aria-valuemin", "0");
  track.setAttribute("aria-valuemax", String(Math.max(0, Math.round(total))));
  track.setAttribute("aria-valuenow", String(Math.round(state.viewport.startSec)));
  track.setAttribute("aria-valuetext", `当前窗口从 ${formatHms(state.viewport.startSec)} 开始`);
  const pct = (value) => `${clamp((Number(value) / total) * 100, 0, 100).toFixed(3)}%`;
  track.innerHTML = "";
  state.cache.chunks.forEach((chunk) => {
    const item = document.createElement("span");
    item.className = "ww-overview-loaded";
    item.style.left = pct(chunk.start_sec);
    item.style.width = pct(Math.max(0.05, chunk.end_sec - chunk.start_sec));
    track.appendChild(item);
  });
  const overlays = [
    ...state.draft.candidateBadSegments.map((seg) => [seg, "candidate"]),
    ...state.draft.badSegments.map((seg) => [seg, "reject"]),
    ...state.draft.remainSegments.map((seg) => [seg, "remain"]),
  ];
  overlays.forEach(([seg, kind]) => {
    const item = document.createElement("span");
    item.className = `ww-overview-mark ww-overview-${kind}`;
    item.style.left = pct(seg.start_sec);
    item.style.width = pct(Math.max(0.05, Number(seg.end_sec) - Number(seg.start_sec)));
    track.appendChild(item);
  });
  if (state.eventDisplay !== "hidden") {
    const events = Array.isArray(state.payload?.events) ? state.payload.events : [];
    events.slice(0, 80).forEach((event) => {
      const time = Number(event.time_sec ?? event.onset_sec ?? event.onset);
      if (!Number.isFinite(time)) return;
      const item = document.createElement("span");
      item.className = "ww-overview-event";
      item.style.left = pct(time);
      track.appendChild(item);
    });
  }
  const win = document.createElement("span");
  win.className = "ww-overview-window";
  win.style.left = pct(state.viewport.startSec);
  win.style.width = pct(state.viewport.durationSec);
  track.appendChild(win);
  if (caption) {
    const coverageText = currentWindowCoverage() === "ready" ? "当前窗口已缓存，可连续浏览" : "当前窗口读取中";
    const eventText = state.eventDisplay === "hidden" ? "事件标记已隐藏" : "竖线为事件标记（非断点）";
    caption.textContent = `全程 ${formatHms(total)} · 拖动时间轴可快速定位 · ${coverageText} · ${eventText}`;
  }
  syncLoadingOverlay();
}

function currentWindowData() {
  const start = state.viewport.startSec;
  const end = start + state.viewport.durationSec;
  const channelCount = Math.max(state.payload?.channels?.length || 0, state.cache.chunks[0]?.channels?.length || 0);
  const chunk = authoritativeChunkForWindow(start, end);
  const points = [];
  chunk?.times_sec.forEach((time, index) => {
    if (time < start - 1e-6 || time > end + 1e-6) return;
    points.push({ time, index });
  });
  if (!points.length) return { times: [], matrix: Array.from({ length: channelCount }, () => []) };
  const matrix = Array.from({ length: channelCount }, () => []);
  points.forEach((point) => {
    for (let ch = 0; ch < channelCount; ch += 1) {
      matrix[ch].push(Number(chunk.data_uv?.[ch]?.[point.index] || 0));
    }
  });
  return { times: points.map((point) => point.time), matrix };
}

function estimateInitialSensitivityUvPerRow(payload) {
  const rows = (payload?.data_uv || []).slice(0, Math.min(8, payload?.data_uv?.length || 0));
  const ranges = rows.map((row) => {
    const values = (row || []).map(Number).filter(Number.isFinite);
    if (values.length < 4) return 0;
    const sorted = values.slice().sort((a, b) => a - b);
    const low = sorted[Math.floor(sorted.length * 0.05)];
    const high = sorted[Math.floor(sorted.length * 0.95)];
    return Math.abs(high - low);
  }).filter((value) => value > 0);
  if (!ranges.length) return state.viewport.sensitivityUvPerRow;
  ranges.sort((a, b) => a - b);
  const medianRange = ranges[Math.floor(ranges.length / 2)];
  return clamp(medianRange * 2.4, 40, 300);
}

function applyInitialSensitivityIfNeeded(payload, force = false) {
  if (state.autoSensitivityApplied && !force) return;
  const recommended = estimateInitialSensitivityUvPerRow(payload);
  if (Number.isFinite(recommended) && recommended > 0) {
    state.viewport.sensitivityUvPerRow = recommended;
    state.autoSensitivityApplied = true;
  }
}

function epochRangeFromTimes(startTime, endTime) {
  const a = Math.min(Number(startTime), Number(endTime));
  const b = Math.max(Number(startTime), Number(endTime));
  const length = Math.max(0.1, Number(state.epoch.lengthSec || 4));
  const startEpoch = Math.max(0, Math.floor(a / length));
  const endEpoch = Math.max(startEpoch, Math.floor(Math.max(a, b - 1e-6) / length));
  const startSec = startEpoch * length;
  const endSec = Math.min(state.viewport.fileDurationSec || (endEpoch + 1) * length, (endEpoch + 1) * length);
  return { start_epoch: startEpoch, end_epoch: endEpoch, start_sec: startSec, end_sec: endSec };
}

function drawSegment(ctx, seg, fillStyle, strokeStyle, label, left, top, plotW, plotH, start, end) {
  const startSec = Number(seg.start_sec);
  const endSec = Number(seg.end_sec);
  if (!Number.isFinite(startSec) || !Number.isFinite(endSec) || endSec < start || startSec > end) return;
  const x1 = left + ((startSec - start) / Math.max(0.001, end - start)) * plotW;
  const x2 = left + ((endSec - start) / Math.max(0.001, end - start)) * plotW;
  const x = Math.max(left, x1);
  const w = Math.max(1, Math.min(left + plotW, x2) - x);
  ctx.fillStyle = fillStyle;
  ctx.fillRect(x, top, w, plotH);
  if (strokeStyle) {
    ctx.strokeStyle = strokeStyle;
    ctx.lineWidth = 1;
    ctx.strokeRect(x, top, w, plotH);
  }
  if (label && w > 36) {
    ctx.fillStyle = strokeStyle || "#334155";
    ctx.font = "700 11px Segoe UI";
    ctx.fillText(label, x + 6, top + 16);
  }
}

function drawEpochGrid(ctx, left, top, plotW, plotH, start, end) {
  if (!isEpochWorkbench()) return;
  const length = Number(state.epoch.lengthSec || 4);
  if (!length || length <= 0) return;
  const first = Math.ceil(start / length);
  ctx.strokeStyle = "rgba(148, 163, 184, .26)";
  ctx.lineWidth = 1;
  for (let epoch = first; epoch * length < end; epoch += 1) {
    const t = epoch * length;
    const x = left + ((t - start) / Math.max(0.001, end - start)) * plotW;
    ctx.beginPath();
    ctx.moveTo(x, top);
    ctx.lineTo(x, top + plotH);
    ctx.stroke();
  }
}

function drawCoverageMask(ctx, coverage, left, top, plotW, plotH, start, end) {
  if (!coverage) return;
  const xForTime = (timeSec) => left + ((timeSec - start) / Math.max(0.001, end - start)) * plotW;
  const shade = (x, width, label) => {
    if (width <= 0.5) return;
    ctx.save();
    ctx.fillStyle = "rgba(241, 245, 249, .82)";
    ctx.fillRect(x, top, width, plotH);
    ctx.strokeStyle = "rgba(148, 163, 184, .34)";
    ctx.lineWidth = 1;
    for (let sx = x - plotH; sx < x + width + plotH; sx += 14) {
      ctx.beginPath();
      ctx.moveTo(sx, top + plotH);
      ctx.lineTo(sx + plotH, top);
      ctx.stroke();
    }
    ctx.fillStyle = "#64748b";
    ctx.font = "700 12px Segoe UI";
    ctx.fillText(label, x + 12, top + 24);
    ctx.restore();
  };
  if (!coverage.hasData) {
    shade(left, plotW, coverage.state === "loading" ? "正在读取当前时间窗" : "当前时间窗没有可显示的数据");
    return;
  }
  const dataX1 = clamp(xForTime(coverage.start), left, left + plotW);
  const dataX2 = clamp(xForTime(coverage.end), left, left + plotW);
  shade(left, dataX1 - left, "未加载");
  shade(dataX2, left + plotW - dataX2, "未加载");
}

function draw() {
  const canvas = qs("#wwCanvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const rect = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  const targetWidth = Math.max(800, Math.floor(rect.width * dpr));
  const targetHeight = Math.max(360, Math.floor(rect.height * dpr));
  if (canvas.width !== targetWidth) canvas.width = targetWidth;
  if (canvas.height !== targetHeight) canvas.height = targetHeight;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  const w = rect.width;
  const h = rect.height;
  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, w, h);
  const p = state.payload;
  const hasAnyWaveformData = Boolean(p?.data_uv?.length || state.cache.chunks.some((chunk) => chunk?.data_uv?.length));
  if (!hasAnyWaveformData) {
    qs("#wwEmpty")?.classList.remove("hidden");
    return;
  }
  qs("#wwEmpty")?.classList.add("hidden");
  const left = 82;
  const right = 18;
  const top = 30;
  const bottom = 36;
  const plotW = w - left - right;
  const plotH = h - top - bottom;
  const visible = Math.min(state.viewport.visibleChannels, p.channels.length, p.data_uv.length);
  const rowH = plotH / Math.max(1, visible);
  const start = state.viewport.startSec;
  const end = start + state.viewport.durationSec;
  const win = currentWindowData() || { times: [], matrix: [] };
  const times = win.times;
  const matrix = win.matrix;
  const coverage = currentDataCoverage();

  drawEpochGrid(ctx, left, top, plotW, plotH, start, end);
  drawCoverageMask(ctx, coverage, left, top, plotW, plotH, start, end);

  ctx.strokeStyle = "#e6eef7";
  ctx.lineWidth = 1;
  for (let i = 0; i <= 6; i += 1) {
    const x = left + (plotW * i / 6);
    ctx.beginPath();
    ctx.moveTo(x, top);
    ctx.lineTo(x, top + plotH);
    ctx.stroke();
  }

  state.draft.remainSegments.forEach((seg, index) => drawSegment(ctx, seg, "rgba(15,138,115,.13)", "rgba(15,118,110,.65)", index === 0 ? "Remain" : "", left, top, plotW, plotH, start, end));
  state.draft.candidateBadSegments.forEach((seg, index) => drawSegment(ctx, seg, "rgba(245,158,11,.18)", "rgba(180,83,9,.75)", index === 0 ? "候选" : "", left, top, plotW, plotH, start, end));
  state.draft.badSegments.forEach((seg, index) => drawSegment(ctx, seg, "rgba(239,68,68,.17)", "rgba(220,38,38,.72)", index === 0 ? "Reject" : "", left, top, plotW, plotH, start, end));
  if (state.draft.selectedSegment) drawSegment(ctx, state.draft.selectedSegment, "rgba(236,72,153,.14)", "rgba(219,39,119,.8)", "选区", left, top, plotW, plotH, start, end);
  if (isEpochWorkbench() && state.epoch.selectedRange) drawSegment(ctx, state.epoch.selectedRange, "rgba(236,72,153,.14)", "rgba(219,39,119,.8)", "Epoch", left, top, plotW, plotH, start, end);

  for (let c = 0; c < visible; c += 1) {
    const y = top + rowH * (c + 0.5);
    ctx.strokeStyle = "#edf2f6";
    ctx.beginPath();
    ctx.moveTo(left, y);
    ctx.lineTo(left + plotW, y);
    ctx.stroke();
    const chName = p.channels[c] || `Ch${c + 1}`;
    const isBad = state.draft.badChannels.some((item) => String(item.channel || item).toLowerCase() === String(chName).toLowerCase());
    ctx.fillStyle = isBad ? "#dc2626" : "#506174";
    ctx.font = isBad ? "700 12px Segoe UI" : "12px Segoe UI";
    ctx.fillText(isBad ? `${chName} *` : chName, 12, y + 4);
  }

  if (!times.length) {
    ctx.fillStyle = "#5b6b7c";
    ctx.font = "14px Segoe UI";
    ctx.fillText("当前时间窗暂无新数据，请等待当前窗口读取完成。", left + 12, top + 52);
  }

  const colors = ["#155c9c", "#157a77", "#7c3aed", "#c2410c", "#0f766e", "#9333ea", "#b45309", "#0369a1"];
  for (let c = 0; c < visible; c += 1) {
    const row = matrix[c] || [];
    if (!row.length) continue;
    const y0 = top + rowH * (c + 0.5);
    const scale = (rowH * 0.42) / Math.max(1, state.viewport.sensitivityUvPerRow);
    ctx.strokeStyle = colors[c % colors.length];
    ctx.lineWidth = 1.15;
    ctx.beginPath();
    for (let i = 0; i < row.length; i += 1) {
      const t = Number(times[i]);
      const x = left + ((t - start) / Math.max(0.001, end - start)) * plotW;
      const y = y0 - Number(row[i]) * scale;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();
  }

  const eventItems = [
    ...(Array.isArray(p.events) ? p.events : []),
    ...(Array.isArray(p.annotations) ? p.annotations : []),
  ].filter((item) => Number.isFinite(Number(item.time_sec ?? item.onset_sec ?? item.onset)));
  if (state.eventDisplay !== "hidden") eventItems.slice(0, state.eventDisplay === "full" ? 80 : 40).forEach((item, index) => {
    const timeSec = Number(item.time_sec ?? item.onset_sec ?? item.onset);
    if (timeSec < start || timeSec > end) return;
    const x = left + ((timeSec - start) / Math.max(0.001, end - start)) * plotW;
    ctx.strokeStyle = state.eventDisplay === "full" ? "rgba(20, 184, 166, 0.52)" : "rgba(20, 184, 166, 0.18)";
    ctx.beginPath();
    ctx.moveTo(x, top);
    ctx.lineTo(x, top + plotH);
    ctx.stroke();
    if (state.eventDisplay === "full" && index < 8) {
      ctx.fillStyle = "#0f766e";
      ctx.font = "700 10px Segoe UI";
      ctx.fillText(String(item.label || item.description || "事件").slice(0, 12), x + 4, top + 12 + (index % 4) * 13);
    }
  });

  ctx.fillStyle = "#506174";
  ctx.font = "12px Segoe UI";
  for (let i = 0; i <= 6; i += 1) {
    const t = start + (state.viewport.durationSec * i / 6);
    const x = left + (plotW * i / 6);
    ctx.fillText(`${t.toFixed(1)}s`, x - 12, h - 12);
  }

  ctx.fillStyle = "#102033";
  ctx.font = "700 14px Segoe UI";
  ctx.fillText("EEG 波形复核", left, 20);
  state.plot = { left, top, plotW, plotH, rowH, start, end, visible };
  syncLoadingOverlay();
}

function xToTime(clientX) {
  const canvas = qs("#wwCanvas");
  const r = canvas.getBoundingClientRect();
  const plot = state.plot;
  if (!plot) return state.viewport.startSec;
  return clamp(plot.start + ((clientX - r.left - plot.left) / plot.plotW) * (plot.end - plot.start), plot.start, plot.end);
}

function channelFromY(clientY) {
  const canvas = qs("#wwCanvas");
  const r = canvas.getBoundingClientRect();
  const plot = state.plot;
  if (!plot) return "";
  const idx = Math.floor((clientY - r.top - plot.top) / plot.rowH);
  return state.payload?.channels?.[idx] || "";
}

async function loadFromTask(task, options = {}) {
  let artifacts = [];
  for (let i = 0; i < 60; i += 1) {
    artifacts = await api.fetchTaskArtifacts(task.id);
    if (waveformArtifactFromList(artifacts)) break;
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
  const artifact = waveformArtifactFromList(artifacts);
  if (!artifact) throw new Error("没有找到 waveform preview artifact");
  const payload = normalizeWaveformPreview(await api.fetchArtifactJson(artifact));
  const sourceDuration = Number(options.file?.duration_sec || options.file?.metadata_json?.duration_sec || 0);
  if (sourceDuration && sourceDuration > Number(payload.file_duration_sec || 0)) {
    payload.file_duration_sec = sourceDuration;
    payload.duration_total_sec = sourceDuration;
  }
  const loadedWindow = payloadWindow(payload);
  if (options.resetStart && loadedWindow.start_sec > 0.05) {
    throw new Error(`教学预览不是从 0 秒开始，当前为 ${loadedWindow.start_sec.toFixed(1)} 秒，需要重新生成首页窗口。`);
  }
  addPayloadToCache(payload);
  const previewDuration = Number(payload.duration_sec || 0);
  if (options.minPreviewDurationSec && previewDuration < options.minPreviewDurationSec && !options.allowShortPreview) {
    throw new Error(`当前预览窗口只有 ${Number(previewDuration.toFixed(1))} 秒，需要重新生成更适合阅片的预览。`);
  }
  applyInitialSensitivityIfNeeded(payload);
  state.task = task;
  state.payload = payload;
  const fileDuration = payload.file_duration_sec || state.viewport.fileDurationSec || 60;
  const nextDuration = options.keepViewport
    ? Math.min(state.viewport.durationSec, fileDuration)
    : Math.min(24, payload.duration_sec || fileDuration || 24);
  Object.assign(state.viewport, {
    startSec: options.keepViewport ? state.viewport.startSec : (options.resetStart ? 0 : (payload.start_sec || 0)),
    durationSec: nextDuration,
    fileDurationSec: fileDuration,
    displaySampleRateHz: payload.display_sample_rate_hz || 200,
    visibleChannels: options.keepChannels ? state.viewport.visibleChannels : Math.min(8, payload.channels.length || 8),
  });
  syncAll();
  draw();
}

async function loadTeaching() {
  syncContext();
  updateText("#wwDataState", "正在加载示例数据");
  state.autoSensitivityApplied = false;
  let data = null;
  try {
    data = await withTimeout(api.loadTeachingDataset(), 10000, "示例数据接口");
  } catch (error) {
    loadLocalTeachingFallback(error);
    return;
  }
  state.project = data.project;
  state.file = data.file;
  state.cache.chunks = [];
  state.cache.pending = null;
  state.cache.loading = false;
  let loadedViaChunkApi = false;
  try {
    const payload = normalizeWaveformPreview(await api.fetchWaveformChunk({
      fileId: state.file.id,
      startSec: 0,
      durationSec: 24,
      channelLimit: state.viewport.visibleChannels,
      displaySfreq: 200,
      mode: "minmax",
      widthPx: Math.max(800, Math.floor(qs("#wwCanvas")?.getBoundingClientRect()?.width || 1440)),
    }));
    addPayloadToCache(payload);
    applyInitialSensitivityIfNeeded(payload);
    state.payload = payload;
    Object.assign(state.viewport, {
      startSec: 0,
      durationSec: Math.min(24, payload.file_duration_sec || payload.duration_sec || 24),
      fileDurationSec: payload.file_duration_sec || state.viewport.fileDurationSec || 60,
      displaySampleRateHz: payload.display_sample_rate_hz || 200,
      visibleChannels: Math.min(8, payload.channels.length || 8),
    });
    loadedViaChunkApi = true;
    recordAction("load_teaching_chunk_api");
  } catch (chunkError) {
    recordAction("load_teaching_chunk_api_fallback", { reason: chunkError?.message || String(chunkError) });
  }
  if (!loadedViaChunkApi) {
    if (data.qc_preview_task?.id) {
      try {
        await loadFromTask(data.qc_preview_task, { resetStart: true, minPreviewDurationSec: 20, file: state.file });
      } catch {
        const task = await api.createWaveformPreviewTask({ projectId: state.project.id, fileId: state.file.id, parameters: previewParameters({ durationSec: 24 }) });
        await loadFromTask(task, { resetStart: true, allowShortPreview: true, file: state.file });
      }
    } else {
      const task = await api.createWaveformPreviewTask({ projectId: state.project.id, fileId: state.file.id, parameters: previewParameters({ durationSec: 24 }) });
      await loadFromTask(task, { resetStart: true, file: state.file });
    }
  }
  if (isTeachingContinuityDataset()) {
    const continuityPayload = buildLocalTeachingPayload();
    addPayloadToCache(continuityPayload);
    applyInitialSensitivityIfNeeded(continuityPayload);
    if (state.payload) {
      state.payload.file_duration_sec = Math.max(Number(state.payload.file_duration_sec || 0), continuityPayload.file_duration_sec);
      state.payload.events = continuityPayload.events;
    }
    state.viewport.fileDurationSec = Math.max(state.viewport.fileDurationSec, continuityPayload.file_duration_sec);
  }
  syncAll();
  draw();
}

function hasAuthoritativeCoverage(start, end) {
  const chunk = authoritativeChunkForWindow(start, end);
  if (!chunk) return false;
  const tolerance = Math.max(0.02, 2 / Math.max(1, state.viewport.displaySampleRateHz || 200));
  return chunk.start_sec <= start + tolerance && chunk.end_sec >= end - tolerance && pointCountInWindow(chunk, start, end) > 2;
}

function buildLocalTeachingPayload(durationSec = 60) {
  const channels = ["Fz", "Cz", "Pz", "Oz", "P3", "P4", "O1", "O2"];
  const sfreq = 200;
  const n = durationSec * sfreq;
  const times = Array.from({ length: n }, (_, index) => index / sfreq);
  const events = [];
  for (let t = 2; t < durationSec; t += 1.6) {
    events.push({ onset_sec: Number(t.toFixed(3)), time_sec: Number(t.toFixed(3)), duration_sec: 0, description: events.length % 3 === 0 ? "target" : "standard" });
  }
  const data = channels.map((_, channelIndex) => times.map((t, sampleIndex) => {
    const alpha = Math.sin(2 * Math.PI * (8 + channelIndex * 0.35) * t) * (10 + channelIndex * 1.4);
    const slow = Math.sin(2 * Math.PI * 0.35 * t + channelIndex * 0.4) * 6;
    const deterministicNoise = Math.sin(sampleIndex * 0.137 + channelIndex) * 1.8;
    const eventBump = events.reduce((sum, event) => {
      const d = t - event.onset_sec;
      if (d < 0 || d > 0.65) return sum;
      const polarity = event.description === "target" ? 1 : 0.35;
      return sum + polarity * Math.exp(-Math.pow((d - 0.3) / 0.12, 2)) * (channelIndex < 4 ? 18 : 10);
    }, 0);
    return Number((alpha + slow + deterministicNoise + eventBump).toFixed(4));
  }));
  return {
    start_sec: 0,
    duration_sec: durationSec,
    file_duration_sec: durationSec,
    display_sample_rate_hz: sfreq,
    unit: "uV",
    channels,
    times_sec: times,
    data_uv: data,
    events,
    bad_segments: [],
    bad_channels: [],
  };
}

function loadLocalShortDemo() {
  state.project = { id: "local_short_project", name: "短时长波形测试数据" };
  state.file = {
    id: "local_short_continuous_eeg",
    original_filename: "short_continuous_10s.fif",
    duration_sec: 10,
    metadata_json: { label: "短时长 EEG 测试数据", protected_teaching_dataset: true },
  };
  const payload = buildLocalTeachingPayload(10);
  state.task = null;
  state.payload = payload;
  state.cache.chunks = [];
  state.cache.pending = null;
  state.cache.loading = false;
  state.autoSensitivityApplied = false;
  addPayloadToCache(payload);
  applyInitialSensitivityIfNeeded(payload, true);
  Object.assign(state.viewport, {
    startSec: 0,
    durationSec: Math.min(24, payload.file_duration_sec),
    fileDurationSec: payload.file_duration_sec,
    displaySampleRateHz: payload.display_sample_rate_hz,
    visibleChannels: 8,
  });
  recordAction("load_local_short_demo");
  updateText("#wwDataState", "短时长测试数据 · 已按全文件显示");
  syncAll();
  draw();
}

function loadLocalTeachingFallback(error) {
  state.project = { id: "local_teaching_project", name: "示例模式内置连续数据" };
  state.file = {
    id: "local_teaching_continuous_eeg",
    original_filename: "teaching_continuous_oddball_60s.fif",
    duration_sec: 60,
    metadata_json: { label: "教学连续 EEG（本地生成）", protected_teaching_dataset: true },
  };
  const payload = buildLocalTeachingPayload();
  state.task = null;
  state.payload = payload;
  state.cache.chunks = [];
  state.autoSensitivityApplied = false;
  addPayloadToCache(payload);
  applyInitialSensitivityIfNeeded(payload, true);
  Object.assign(state.viewport, {
    startSec: 0,
    durationSec: Math.min(24, payload.file_duration_sec),
    fileDurationSec: payload.file_duration_sec,
    displaySampleRateHz: payload.display_sample_rate_hz,
    visibleChannels: 8,
  });
  recordAction("load_local_teaching_fallback", { reason: error?.message || String(error || "unknown") });
  updateText("#wwDataState", "教学内置连续数据 · 后端教学接口较慢");
  syncAll();
  draw();
}

function startTeachingLoad() {
  if (state.teachingLoadStarted) return;
  if (state.payload) return;
  state.teachingLoadStarted = true;
  loadTeaching().catch((err) => {
    state.teachingLoadStarted = false;
    updateText("#wwDataState", `加载失败：${err.message}`);
    console.error(err);
  });
}

function previewParameters(options = {}) {
  const durationSec = Math.min(constants.maxDurationSec, Number(options.durationSec || state.viewport.durationSec || 24));
  return {
    fast_ui_preview: true,
    preview: {
      start_sec: Number(options.startSec ?? state.viewport.startSec ?? 0),
      duration_sec: durationSec,
      channel_limit: Number(options.channelLimit || state.viewport.visibleChannels || 8),
      display_sfreq: 200,
    },
    filter_preview: { enabled: false },
  };
}

async function reloadViewportPreview(reason = "viewport") {
  if (!state.project?.id || !state.file?.id) return null;
  const seq = ++state.requestSeq;
  if (state.cache.activeAbortController) {
    state.cache.activeAbortController.abort();
    state.cache.stats.chunkAborts += 1;
  }
  const pending = {
    start_sec: state.viewport.startSec,
    end_sec: state.viewport.startSec + state.viewport.durationSec,
  };
  if (hasAuthoritativeCoverage(pending.start_sec, pending.end_sec)) {
    state.cache.pending = null;
    state.cache.loading = false;
    state.cache.lastReloadSource = "cache_hit";
    state.cache.stats.cacheHits += 1;
    recordAction(`reload_${reason}_cache_hit`, { start_sec: state.viewport.startSec, duration_sec: state.viewport.durationSec });
    updateText("#wwDataState", `${state.payload?.channels?.length || 0} 通道 · ${state.payload?.display_sample_rate_hz || 0} Hz · 缓存浏览`);
    syncAll();
    draw();
    prefetchAdjacentWindows();
    return { id: "waveform_cache_hit", status: "completed" };
  }
  state.cache.pending = pending;
  state.cache.loading = true;
  syncAll();
  draw();
  updateText("#wwDataState", `正在读取 ${formatHms(state.viewport.startSec)}-${formatHms(state.viewport.startSec + state.viewport.durationSec)} 波形`);
  const abortController = new AbortController();
  state.cache.activeAbortController = abortController;
  state.cache.stats.chunkRequests += 1;
  try {
    const payload = normalizeWaveformPreview(await api.fetchWaveformChunk({
      fileId: state.file.id,
      startSec: state.viewport.startSec,
      durationSec: state.viewport.durationSec,
      channelLimit: state.viewport.visibleChannels,
      displaySfreq: 200,
      mode: "minmax",
      widthPx: Math.max(800, Math.floor(qs("#wwCanvas")?.getBoundingClientRect()?.width || 1440)),
      signal: abortController.signal,
    }));
    if (seq !== state.requestSeq) return null;
    if (state.cache.activeAbortController === abortController) state.cache.activeAbortController = null;
    addPayloadToCache(payload);
    applyInitialSensitivityIfNeeded(payload);
    state.payload = { ...(state.payload || payload), ...payload };
    state.viewport.fileDurationSec = payload.file_duration_sec || state.viewport.fileDurationSec;
    state.viewport.displaySampleRateHz = payload.display_sample_rate_hz || state.viewport.displaySampleRateHz;
    state.cache.loading = false;
    state.cache.pending = null;
    state.cache.lastReloadSource = "chunk_api";
    recordAction(`reload_${reason}_chunk_api`, { start_sec: state.viewport.startSec, duration_sec: state.viewport.durationSec });
    updateText("#wwDataState", `${state.payload?.channels?.length || 0} 通道 · ${state.payload?.display_sample_rate_hz || 0} Hz · 快速波形`);
    syncAll();
    draw();
    prefetchAdjacentWindows();
    return { id: "waveform_chunk_api", status: "completed" };
  } catch (chunkError) {
    if (chunkError?.name === "AbortError") {
      state.cache.lastReloadSource = "aborted";
      if (state.cache.activeAbortController === abortController) state.cache.activeAbortController = null;
      return null;
    }
    if (state.cache.activeAbortController === abortController) state.cache.activeAbortController = null;
    state.cache.stats.chunkFallbacks += 1;
    recordAction("waveform_chunk_api_fallback", { reason: chunkError?.message || String(chunkError) });
    const task = await api.createWaveformPreviewTask({ projectId: state.project.id, fileId: state.file.id, parameters: previewParameters() });
    if (seq !== state.requestSeq) return null;
    await loadFromTask(task, { keepViewport: true, keepChannels: true, allowShortPreview: true, file: state.file });
    state.cache.loading = false;
    state.cache.pending = null;
    state.cache.lastReloadSource = "legacy_qc_task_fallback";
    recordAction(`reload_${reason}`, { start_sec: state.viewport.startSec, duration_sec: state.viewport.durationSec });
    updateText("#wwDataState", `${state.payload?.channels?.length || 0} 通道 · ${state.payload?.display_sample_rate_hz || 0} Hz`);
    syncAll();
    draw();
    return task;
  }
}

function prefetchAdjacentWindows() {
  if (!state.project?.id || !state.file?.id || !api.fetchWaveformChunk) return;
  const duration = state.viewport.durationSec;
  const total = state.viewport.fileDurationSec || 0;
  if (!duration || !total) return;
  const starts = [
    Math.max(0, state.viewport.startSec - duration),
    Math.min(Math.max(0, total - duration), state.viewport.startSec + duration),
  ].filter((start, index, arr) => Number.isFinite(start) && arr.indexOf(start) === index);
  starts.forEach((start) => {
    const end = Math.min(total, start + duration);
    if (end <= start || hasAuthoritativeCoverage(start, end)) {
      state.cache.stats.prefetchHits += 1;
      return;
    }
    const key = `${state.file.id}:${start.toFixed(3)}:${duration.toFixed(3)}:${state.viewport.visibleChannels}`;
    if (state.cache.prefetchControllers.has(key)) return;
    const controller = new AbortController();
    state.cache.prefetchControllers.set(key, controller);
    state.cache.stats.prefetchRequests += 1;
    api.fetchWaveformChunk({
      fileId: state.file.id,
      startSec: start,
      durationSec: duration,
      channelLimit: state.viewport.visibleChannels,
      displaySfreq: 200,
      mode: "minmax",
      widthPx: Math.max(800, Math.floor(qs("#wwCanvas")?.getBoundingClientRect()?.width || 1440)),
      signal: controller.signal,
    }).then((payload) => {
      addPayloadToCache(normalizeWaveformPreview(payload));
      syncAll();
      draw();
    }).catch((error) => {
      if (error?.name !== "AbortError") recordAction("waveform_prefetch_failed", { reason: error?.message || String(error), start_sec: start, duration_sec: duration });
    }).finally(() => {
      state.cache.prefetchControllers.delete(key);
      syncAll();
    });
  });
  syncAll();
}

function scheduleViewportReload(reason = "viewport") {
  window.clearTimeout(state.viewportReloadTimer);
  const start = state.viewport.startSec;
  const end = start + state.viewport.durationSec;
  const delayMs = hasAuthoritativeCoverage(start, end) ? 0 : 180;
  state.viewportReloadTimer = window.setTimeout(() => {
    state.viewportReloadTimer = null;
    reloadViewportPreview(reason).catch((err) => updateText("#wwDataState", `当前窗口读取失败：${err.message || err}`));
  }, delayMs);
}

function syncAll() {
  syncWorkbenchChrome();
  syncContext();
  syncControls();
  syncStatus();
  syncActionButtons();
}

function setMode(mode) {
  const allowed = new Set(["browse", "selectSegment", "markBadSegment", "markBadChannel"]);
  if (isEpochWorkbench()) allowed.add("epochReview");
  state.mode = allowed.has(mode) ? mode : "browse";
  if (!isEpochWorkbench()) state.epoch.selectedRange = null;
  state.transient.drag = null;
  state.transient.middlePan = null;
  syncAll();
  qs("#wwCanvas")?.focus({ preventScroll: true });
}

function setWorkbenchMode(mode) {
  const nextMode = mode === "epoch" ? "epoch" : "basic";
  if (workbenchConfig.mode === nextMode) {
    syncAll();
    return;
  }
  workbenchConfig.mode = nextMode;
  if (!isEpochWorkbench()) {
    if (state.mode === "epochReview") state.mode = "browse";
    state.epoch.selectedRange = null;
  }
  if (!state.eventDisplayManual) {
    state.eventDisplay = isEpochWorkbench() ? "light" : "hidden";
  }
  state.transient.drag = null;
  state.transient.middlePan = null;
  const url = new URL(window.location.href);
  if (isEpochWorkbench()) url.searchParams.set("workbench", "epoch");
  else url.searchParams.delete("workbench");
  window.history.replaceState(null, "", url);
  recordAction("switch_waveform_workbench_mode", { mode: workbenchConfig.mode });
  syncAll();
  draw();
  qs("#wwCanvas")?.focus({ preventScroll: true });
}

async function shiftWindow(dir, ratio = constants.pagePanRatio) {
  state.viewport.startSec = clamp(state.viewport.startSec + dir * state.viewport.durationSec * ratio, 0, Math.max(0, state.viewport.fileDurationSec - state.viewport.durationSec));
  syncAll();
  draw();
  scheduleViewportReload("pan");
}

function jumpWindowStart(startSec, reason = "jump") {
  state.viewport.startSec = clamp(startSec, 0, Math.max(0, state.viewport.fileDurationSec - state.viewport.durationSec));
  state.epoch.selectedRange = null;
  syncAll();
  draw();
  scheduleViewportReload(reason);
}

async function zoomWindow(factor, anchor = null) {
  const oldDur = state.viewport.durationSec;
  const oldStart = state.viewport.startSec;
  const anchorTime = Number.isFinite(anchor) ? anchor : oldStart + oldDur / 2;
  const ratio = (anchorTime - oldStart) / oldDur;
  const newDur = clamp(oldDur * factor, constants.minDurationSec, Math.min(constants.maxDurationSec, state.viewport.fileDurationSec));
  state.viewport.durationSec = newDur;
  state.viewport.startSec = clamp(anchorTime - ratio * newDur, 0, Math.max(0, state.viewport.fileDurationSec - newDur));
  syncAll();
  draw();
  scheduleViewportReload("zoom");
}

function adjustSensitivity(dir) {
  state.viewport.sensitivityUvPerRow = clamp(
    state.viewport.sensitivityUvPerRow * (dir > 0 ? 1 / constants.gainStepRatio : constants.gainStepRatio),
    constants.minSensitivityUvPerRow,
    constants.maxSensitivityUvPerRow,
  );
  syncAll();
  draw();
}

function setEpochControlsFromUi() {
  if (!isEpochWorkbench()) return;
  state.epoch.lengthSec = Number(qs("#wwEpochLength")?.value || 4);
  state.epoch.visibleEpochs = Number(qs("#wwVisibleEpochs")?.value || 6);
  state.viewport.durationSec = clamp(state.epoch.lengthSec * state.epoch.visibleEpochs, constants.minDurationSec, constants.maxDurationSec);
  state.epoch.selectedRange = null;
  state.draft.selectedSegment = null;
  syncAll();
  draw();
  scheduleViewportReload("epoch-controls");
}

function applySelectionReview(kind) {
  const seg = clampSegmentToCurrentDataCoverage(currentSelectionSegment());
  if (!seg) {
    updateText("#wwDataState", "请先在波形中选择一段数据。");
    return;
  }
  pushHistory(kind);
  const reviewed = {
    ...seg,
    id: `${kind}_${Date.now()}`,
    status: kind,
    review_source: isEpochWorkbench() && state.epoch.selectedRange ? "epoch" : "segment",
    reviewed_at: new Date().toISOString(),
  };
  if (kind === "reject") {
    state.draft.badSegments.push({ ...reviewed, reason: "人工复核标为 Reject" });
    state.draft.remainSegments = state.draft.remainSegments.filter((item) => item.end_sec <= reviewed.start_sec || item.start_sec >= reviewed.end_sec);
  } else {
    state.draft.remainSegments.push({ ...reviewed, reason: "人工复核标为 Remain" });
    state.draft.badSegments = state.draft.badSegments.filter((item) => item.end_sec <= reviewed.start_sec || item.start_sec >= reviewed.end_sec);
    state.draft.candidateBadSegments = state.draft.candidateBadSegments.filter((item) => item.end_sec <= reviewed.start_sec || item.start_sec >= reviewed.end_sec);
  }
  recordAction(`review_${kind}`, reviewed);
  syncAll();
  draw();
}

function undoDraft() {
  const last = state.draft.undoStack.pop();
  if (!last) return;
  state.draft.redoStack.push({ action: `redo_${last.action}`, snapshot: cloneDraft(), at: new Date().toISOString() });
  restoreDraft(last.snapshot);
  recordAction("undo", { action_target: last.action });
  syncAll();
  draw();
}

function redoDraft() {
  const next = state.draft.redoStack.pop();
  if (!next) return;
  state.draft.undoStack.push({ action: `undo_${next.action}`, snapshot: cloneDraft(), at: new Date().toISOString() });
  restoreDraft(next.snapshot);
  recordAction("redo", { action_target: next.action });
  syncAll();
  draw();
}

function clearDraft(scope = "current") {
  pushHistory(`clear_${scope}`);
  state.draft.selectedSegment = null;
  state.epoch.selectedRange = null;
  state.draft.candidateBadSegments = [];
  state.draft.badSegments = [];
  state.draft.remainSegments = [];
  state.draft.restoredSegments = [];
  state.draft.badChannels = [];
  if (scope === "all") state.draft.restoredBadChannels = [];
  recordAction(`clear_${scope}`);
  syncAll();
  draw();
}

function confirmAndClearDraft(scope = "current") {
  if (!hasDraftState()) return;
  const message = scope === "all"
    ? "确认清空全部草稿？这只会清空当前准备草稿，不会修改原始 EEG。"
    : "确认清空本轮草稿？这只会清空当前准备草稿，不会修改原始 EEG。";
  if (!window.confirm(message)) return;
  clearDraft(scope);
}

function bindEvents() {
  qs("#loadTeachingBtn")?.addEventListener("click", startTeachingLoad);
  qsa("[data-workbench-switch]").forEach((btn) => btn.addEventListener("click", () => setWorkbenchMode(btn.dataset.workbenchSwitch)));
  qsa("[data-mode]").forEach((btn) => btn.addEventListener("click", () => setMode(btn.dataset.mode)));
  qs("#wwPrevBtn")?.addEventListener("click", () => shiftWindow(-1));
  qs("#wwNextBtn")?.addEventListener("click", () => shiftWindow(1));
  qs("#wwFirstBtn")?.addEventListener("click", () => jumpWindowStart(0, "first"));
  qs("#wwLastBtn")?.addEventListener("click", () => jumpWindowStart(Math.max(0, state.viewport.fileDurationSec - state.viewport.durationSec), "last"));
  qs("#wwTimescale")?.addEventListener("change", (e) => { state.viewport.durationSec = Number(e.target.value) || 24; state.epoch.selectedRange = null; syncAll(); draw(); scheduleViewportReload("timescale"); });
  qs("#wwEventDisplay")?.addEventListener("change", (e) => { state.eventDisplayManual = true; state.eventDisplay = e.target.value || "light"; syncAll(); draw(); });
  qs("#wwSensitivityPreset")?.addEventListener("change", (e) => { state.viewport.sensitivityUvPerRow = Number(e.target.value) || 200; syncAll(); draw(); });
  qs("#wwSensitivity")?.addEventListener("input", (e) => { state.viewport.sensitivityUvPerRow = Number(e.target.value) || 200; syncAll(); draw(); });
  qs("#wwChannels")?.addEventListener("input", (e) => { state.viewport.visibleChannels = Number(e.target.value) || 8; syncAll(); draw(); });
  qs("#wwEpochLength")?.addEventListener("change", setEpochControlsFromUi);
  qs("#wwVisibleEpochs")?.addEventListener("change", setEpochControlsFromUi);
  qs("#wwShortcutBtn")?.addEventListener("click", () => {
    const help = qs("#wwShortcutHelp");
    if (help) help.hidden = !help.hidden;
    recordAction("show_shortcuts");
    syncAll();
  });
  qs("#wwAdvancedToggle")?.addEventListener("click", () => {
    state.advancedOpen = !state.advancedOpen;
    recordAction(state.advancedOpen ? "advanced_controls_open" : "advanced_controls_close");
    syncAll();
  });
  qs("#wwRejectBtn")?.addEventListener("click", () => applySelectionReview("reject"));
  qs("#wwRemainBtn")?.addEventListener("click", () => applySelectionReview("remain"));
  qs("#wwUndoBtn")?.addEventListener("click", undoDraft);
  qs("#wwRedoBtn")?.addEventListener("click", redoDraft);
  qs("#wwCancelAllBtn")?.addEventListener("click", () => confirmAndClearDraft("current"));
  qs("#wwConfirmBadSegmentsBtn")?.addEventListener("click", () => {
    if (!state.draft.candidateBadSegments.length) return;
    pushHistory("confirm_candidates");
    const candidates = state.draft.candidateBadSegments.splice(0);
    candidates.forEach((seg) => state.draft.badSegments.push({ ...seg, status: "reject", confirmed_at: new Date().toISOString() }));
    recordAction("confirm_candidate_bad_segments", { count: candidates.length });
    syncAll();
    draw();
  });
  qs("#wwDiscardCandidatesBtn")?.addEventListener("click", () => {
    if (!state.draft.candidateBadSegments.length) return;
    pushHistory("discard_candidates");
    const count = state.draft.candidateBadSegments.length;
    state.draft.candidateBadSegments = [];
    recordAction("discard_candidate_bad_segments", { count });
    syncAll();
    draw();
  });
  qs("#wwRestoreSegmentBtn")?.addEventListener("click", () => {
    const seg = state.draft.badSegments[state.draft.badSegments.length - 1];
    if (!seg) return;
    pushHistory("restore_bad_segment");
    state.draft.badSegments.pop();
    state.draft.restoredSegments.push({ ...seg, status: "restored", restored_at: new Date().toISOString() });
    recordAction("restore_bad_segment", { restored: true, start_sec: seg.start_sec, end_sec: seg.end_sec });
    syncAll();
    draw();
  });
  qs("#wwClearDraftBtn")?.addEventListener("click", () => confirmAndClearDraft("all"));

  const canvas = qs("#wwCanvas");
  const overviewTrack = qs("#wwOverviewTrack");
  overviewTrack?.addEventListener("mousedown", (e) => {
    if (e.button !== 0) return;
    state.transient.overviewDrag = { active: true };
    overviewTrack.classList.add("is-dragging");
    overviewTrack.focus({ preventScroll: true });
    seekOverviewTo(e.clientX, "overview-drag");
    e.preventDefault();
  });
  overviewTrack?.addEventListener("keydown", (e) => {
    if (e.key === "Home") { e.preventDefault(); jumpWindowStart(0, "overview-home"); }
    else if (e.key === "End") { e.preventDefault(); jumpWindowStart(Math.max(0, state.viewport.fileDurationSec - state.viewport.durationSec), "overview-end"); }
    else if (e.key === "ArrowLeft") { e.preventDefault(); shiftWindow(-1, constants.arrowPanRatio); }
    else if (e.key === "ArrowRight") { e.preventDefault(); shiftWindow(1, constants.arrowPanRatio); }
    else if (e.key === "PageUp") { e.preventDefault(); shiftWindow(-1); }
    else if (e.key === "PageDown") { e.preventDefault(); shiftWindow(1); }
  });

  canvas?.addEventListener("wheel", (e) => {
    e.preventDefault();
    const anchor = xToTime(e.clientX);
    if (e.ctrlKey || e.metaKey) zoomWindow(e.deltaY > 0 ? constants.zoomFactor : 1 / constants.zoomFactor, anchor);
    else shiftWindow(e.deltaY > 0 ? 1 : -1, constants.wheelPanRatio);
  }, { passive: false });

  canvas?.addEventListener("mousedown", (e) => {
    canvas.focus({ preventScroll: true });
    const t = xToTime(e.clientX);
    if (e.button === 1) {
      state.transient.middlePan = { x: e.clientX, start: state.viewport.startSec };
      e.preventDefault();
      return;
    }
    if (e.button !== 0) return;
    if (state.mode === "browse") return;
    if (!timeInCurrentDataCoverage(t)) {
      updateText("#wwDataState", "当前位置暂无可写入的波形数据，准备草稿未更改。");
      return;
    }
    state.transient.drag = { start: t, current: t, mode: state.mode };
    e.preventDefault();
  });

  window.addEventListener("mousemove", (e) => {
    if (state.transient.overviewDrag) {
      seekOverviewTo(e.clientX, "overview-drag");
      return;
    }
    if (state.transient.middlePan) {
      const dx = e.clientX - state.transient.middlePan.x;
      const ratio = dx / Math.max(1, state.plot?.plotW || 1);
      state.viewport.startSec = clamp(state.transient.middlePan.start - ratio * state.viewport.durationSec, 0, Math.max(0, state.viewport.fileDurationSec - state.viewport.durationSec));
      syncAll();
      draw();
      return;
    }
    if (state.transient.drag) {
      state.transient.drag.current = xToTime(e.clientX);
      draw();
      const seg = state.transient.drag.mode === "epochReview" && isEpochWorkbench()
        ? epochRangeFromTimes(state.transient.drag.start, state.transient.drag.current)
        : { start_sec: Math.min(state.transient.drag.start, state.transient.drag.current), end_sec: Math.max(state.transient.drag.start, state.transient.drag.current) };
      const visibleSeg = clampSegmentToCurrentDataCoverage(seg);
      const ctx = qs("#wwCanvas").getContext("2d");
      if (visibleSeg) drawSegment(ctx, visibleSeg, "rgba(236,72,153,.18)", "rgba(219,39,119,.8)", "选区", state.plot.left, state.plot.top, state.plot.plotW, state.plot.plotH, state.plot.start, state.plot.end);
    }
  });

  window.addEventListener("mouseup", () => {
    if (state.transient.overviewDrag) {
      state.transient.overviewDrag = null;
      qs("#wwOverviewTrack")?.classList.remove("is-dragging");
      scheduleViewportReload("overview-drag");
      syncAll();
      return;
    }
    if (state.transient.middlePan) {
      state.transient.middlePan = null;
      scheduleViewportReload("middle-pan");
      return;
    }
    const drag = state.transient.drag;
    if (!drag) return;
    const rawSeg = drag.mode === "epochReview" && isEpochWorkbench()
      ? epochRangeFromTimes(drag.start, drag.current)
      : { start_sec: Math.min(drag.start, drag.current), end_sec: Math.max(drag.start, drag.current) };
    const seg = clampSegmentToCurrentDataCoverage(rawSeg);
    state.transient.drag = null;
    if (!seg || seg.end_sec - seg.start_sec < 0.05) {
      updateText("#wwDataState", "选区不在已加载波形范围内，准备草稿未更改。");
      syncAll();
      draw();
      return;
    }
    if (drag.mode === "epochReview" && isEpochWorkbench()) {
      state.epoch.selectedRange = seg;
      state.draft.selectedSegment = { start_sec: seg.start_sec, end_sec: seg.end_sec };
    } else if (drag.mode === "selectSegment") {
      state.epoch.selectedRange = null;
      state.draft.selectedSegment = seg;
    } else if (drag.mode === "markBadSegment") {
      pushHistory("candidate_bad_segment");
      state.epoch.selectedRange = null;
      state.draft.selectedSegment = seg;
      state.draft.candidateBadSegments.push({ ...seg, id: `candidate_${Date.now()}`, reason: "看波形后标记为候选坏段", status: "candidate" });
    }
    recordAction(drag.mode, { target: seg });
    syncAll();
    draw();
  });

  canvas?.addEventListener("click", (e) => {
    if (state.mode !== "markBadChannel") return;
    if (!currentDataCoverage().hasData) {
      updateText("#wwDataState", "当前时间窗暂无可用波形，暂不能标记坏道。");
      return;
    }
    const ch = channelFromY(e.clientY);
    if (!ch) return;
    pushHistory("toggle_bad_channel");
    const exists = state.draft.badChannels.some((item) => String(item.channel || item) === String(ch));
    if (exists) {
      state.draft.badChannels = state.draft.badChannels.filter((item) => String(item.channel || item) !== String(ch));
      state.draft.restoredBadChannels.push({ channel: ch, restored_at: new Date().toISOString() });
    } else {
      state.draft.badChannels.push({ channel: ch, status: "bad", marked_at: new Date().toISOString() });
    }
    recordAction("toggle_bad_channel", { channel: ch, bad: !exists });
    syncAll();
    draw();
  });

  document.addEventListener("keydown", (e) => {
    const tag = (e.target?.tagName || "").toLowerCase();
    if (["input", "select", "textarea"].includes(tag)) return;
    if (e.key === "PageUp") { e.preventDefault(); shiftWindow(-1); }
    else if (e.key === "PageDown") { e.preventDefault(); shiftWindow(1); }
    else if (e.key === "ArrowLeft") { e.preventDefault(); shiftWindow(-1, constants.arrowPanRatio); }
    else if (e.key === "ArrowRight") { e.preventDefault(); shiftWindow(1, constants.arrowPanRatio); }
    else if (e.key === "Home") { e.preventDefault(); jumpWindowStart(0, "home"); }
    else if (e.key === "End") { e.preventDefault(); jumpWindowStart(Math.max(0, state.viewport.fileDurationSec - state.viewport.durationSec), "end"); }
    else if ((e.key === "+" || e.key === "=") && (e.ctrlKey || e.metaKey)) { e.preventDefault(); zoomWindow(1 / constants.zoomFactor); }
    else if ((e.key === "-" || e.key === "_") && (e.ctrlKey || e.metaKey)) { e.preventDefault(); zoomWindow(constants.zoomFactor); }
    else if (e.key === "+" || e.key === "=") { e.preventDefault(); adjustSensitivity(1); }
    else if (e.key === "-" || e.key === "_") { e.preventDefault(); adjustSensitivity(-1); }
    else if (e.key === "Escape" || e.key.toLowerCase() === "b") { setMode("browse"); }
    else if (e.key.toLowerCase() === "s") { setMode("selectSegment"); }
    else if (e.key.toLowerCase() === "e" && isEpochWorkbench()) { setMode("epochReview"); }
    else if (e.key.toLowerCase() === "x") { setMode("markBadSegment"); }
    else if (e.key.toLowerCase() === "c") { setMode("markBadChannel"); }
    else if (e.key.toLowerCase() === "z") { e.preventDefault(); undoDraft(); }
    else if (e.key.toLowerCase() === "y") { e.preventDefault(); redoDraft(); }
  });
  window.addEventListener("resize", () => { syncAll(); draw(); });
}

bindEvents();
syncAll();
if (["auto", "1", "true"].includes(String(params.get("short_demo") || "").toLowerCase())) {
  queueMicrotask(loadLocalShortDemo);
} else if (["auto", "1", "true"].includes(String(params.get("teaching_demo") || "").toLowerCase())) {
  queueMicrotask(startTeachingLoad);
  window.setTimeout(() => { if (!state.payload) startTeachingLoad(); }, 300);
}
