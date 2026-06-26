const DEFAULT_API_BASE = ["localhost", "127.0.0.1"].includes(window.location.hostname) ? "http://127.0.0.1:8001/api" : "/api";
const params = new URLSearchParams(window.location.search);
const API_BASE = params.get("api") || DEFAULT_API_BASE;
const START_TASK_ID = params.get("task") || "";
const START_MODE = params.get("mode") || "ml_epoch_classifier";
const START_RENDERER = params.get("renderer") === "timechart" ? "timechart" : "svg";
const REVIEW_STORE_PREFIX = "qlanalyser.epilepsy.review.v1.";
const TIMECHART_CDN_SOURCES = [
  "https://cdn.jsdelivr.net/npm/timechart@0.5.2/dist/timechart.min.js",
  "https://unpkg.com/timechart@0.5.2/dist/timechart.min.js",
];
const TIMECHART_D3_SOURCES = [
  "https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js",
  "https://unpkg.com/d3@7/dist/d3.min.js",
];
const TIMECHART_SCRIPT_TIMEOUT_MS = 6000;
const WAVEFORM_MIN_DURATION_SEC = 2;
const WAVEFORM_MAX_DURATION_SEC = 60;
const WAVEFORM_DEFAULT_CONTEXT_SEC = 2;
const WAVEFORM_DEBOUNCE_MS = 220;
const WAVEFORM_DRAG_THRESHOLD_PX = 18;
const WAVEFORM_WHEEL_PAN_RATIO = 0.16;
const WAVEFORM_ARROW_PAN_RATIO = 0.1;
const WAVEFORM_GAINS = ["auto", "0.5", "1", "2", "4"];

const state = {
  project: null,
  files: [],
  selectedFileId: "",
  demoFixture: null,
  algorithmMode: START_MODE === "std_threshold" ? "std_threshold" : "ml_epoch_classifier",
  task: null,
  artifacts: [],
  sourceEpochRows: [],
  sourceEventRows: [],
  epochRows: [],
  eventRows: [],
  summary: null,
  parameters: {
    eeg_channel: "",
    epoch_length_sec: 5,
    std_factor: 2,
    rms_window_samples: 15,
    merge_gap_epoch_num: 1,
    min_event_epochs: 2,
    event_window_sec: 1800,
    bad_channels: "",
  },
  selectedEpoch: 0,
  epochSelectionStart: 0,
  epochSelectionEnd: 0,
  visibleEpochCount: "All",
  epochWindowStart: 0,
  selectedEventId: "",
  reviews: {},
  epochOverrides: {},
  reviewActions: [],
  reviewNote: "",
  reviewSession: null,
  reviewSessionError: "",
  history: [],
  future: [],
  waveformTask: null,
  waveformArtifacts: [],
  waveformWindow: null,
  waveformEventId: "",
  waveformError: "",
  waveformRenderer: START_RENDERER,
  waveformViewport: { startSec: null, durationSec: null, lastEventId: "" },
  waveformInteraction: { mode: "browse", gain: "auto" },
  timechartLoadState: "idle",
  timechartLoadError: "",
  timechartInstance: null,
  timechartMetrics: null,
  activeWaveformLabel: "raw_preview_figure",
  message: "请选择或上传 EEG，然后运行工作台分析。",
  error: false,
  uploadInFlight: false,
  runInFlight: false,
  waveformInFlight: false,
};

let waveformPreviewTimer = null;
let waveformDragState = null;

function icon(name) { return `<i data-lucide="${h(name)}" aria-hidden="true"></i>`; }
function h(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}
function api(path) { return `${API_BASE.replace(/\/$/, "")}${path}`; }
function fmt(value, digits = 2) {
  const n = Number(value);
  return Number.isFinite(n) ? n.toFixed(digits) : "-";
}
function boolValue(value) { return String(value).toLowerCase() === "true"; }
function numeric(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}
function clamp(value, min, max) {
  const n = Number(value);
  if (!Number.isFinite(n)) return min;
  return Math.min(max, Math.max(min, n));
}
function selectedFile() { return state.files.find((item) => item.id === state.selectedFileId); }
function artifactByLabel(label, list = state.artifacts) { return list.find((item) => item.label === label); }
function artifactUrl(artifact) { return api(`/artifacts/${artifact.id}/download`); }
function reviewKey() { return `${REVIEW_STORE_PREFIX}${state.task?.id || state.selectedFileId || "draft"}`; }
function resetWaveformPreview() {
  state.waveformTask = null;
  state.waveformArtifacts = [];
  state.waveformWindow = null;
  state.waveformEventId = "";
  state.waveformError = "";
  state.waveformInFlight = false;
  state.activeWaveformLabel = "raw_preview_figure";
  state.waveformViewport = { startSec: null, durationSec: null, lastEventId: "" };
  state.waveformInteraction = { mode: "browse", gain: "auto" };
  state.timechartMetrics = null;
  state.timechartInstance = null;
}
function resetAnalysisOutputs() {
  state.task = null;
  state.artifacts = [];
  state.sourceEpochRows = [];
  state.sourceEventRows = [];
  state.epochRows = [];
  state.eventRows = [];
  state.summary = null;
  state.selectedEventId = "";
  state.selectedEpoch = 0;
  state.epochSelectionStart = 0;
  state.epochSelectionEnd = 0;
  state.epochWindowStart = 0;
  state.reviews = {};
  state.epochOverrides = {};
  state.reviewActions = [];
  state.reviewNote = "";
  state.reviewSession = null;
  state.reviewSessionError = "";
  state.history = [];
  state.future = [];
  resetWaveformPreview();
}
function recordingDurationSec(file = selectedFile()) {
  const candidates = [
    file?.duration_sec,
    file?.metadata_json?.duration_sec,
    state.summary?.duration_sec,
    state.summary?.input_shape?.duration_sec,
  ];
  for (const item of candidates) {
    const value = Number(item);
    if (Number.isFinite(value) && value > 0) return value;
  }
  return 0;
}
function waveformWindowForEvent(event, file = selectedFile()) {
  const recordingDuration = recordingDurationSec(file);
  let start = Math.max(0, numeric(event.start_sec) - WAVEFORM_DEFAULT_CONTEXT_SEC);
  let duration = Math.min(30, Math.max(6, numeric(event.duration_sec) + WAVEFORM_DEFAULT_CONTEXT_SEC * 2));
  if (recordingDuration > 0) {
    if (start >= recordingDuration) {
      start = Math.max(0, recordingDuration - Math.min(6, recordingDuration));
    }
    duration = Math.min(duration, Math.max(0.1, recordingDuration - start));
  }
  return { start, duration };
}
function clampWaveformViewport(startSec, durationSec, file = selectedFile()) {
  const recordingDuration = recordingDurationSec(file);
  let duration = clamp(durationSec, WAVEFORM_MIN_DURATION_SEC, WAVEFORM_MAX_DURATION_SEC);
  if (recordingDuration > 0) duration = Math.min(duration, Math.max(WAVEFORM_MIN_DURATION_SEC, recordingDuration));
  let start = Math.max(0, numeric(startSec));
  if (recordingDuration > 0) start = clamp(start, 0, Math.max(0, recordingDuration - duration));
  return { start, duration };
}
function currentWaveformViewport(event = selectedEvent(), file = selectedFile()) {
  const saved = state.waveformViewport || {};
  const eventId = event ? String(event.event_id || "") : "";
  const savedEventId = String(saved.lastEventId || "");
  if (
    Number.isFinite(Number(saved.startSec))
    && Number.isFinite(Number(saved.durationSec))
    && (!eventId || !savedEventId || savedEventId === eventId)
  ) {
    return clampWaveformViewport(Number(saved.startSec), Number(saved.durationSec), file);
  }
  const base = waveformWindowForEvent(event || {}, file);
  return clampWaveformViewport(base.start, base.duration, file);
}
function setWaveformViewport(startSec, durationSec, options = {}) {
  const viewport = clampWaveformViewport(startSec, durationSec, selectedFile());
  state.waveformViewport = {
    startSec: viewport.start,
    durationSec: viewport.duration,
    lastEventId: options.eventId !== undefined ? String(options.eventId || "") : String(state.waveformViewport?.lastEventId || ""),
  };
  if (options.invalidate !== false && !options.keepPreview) {
    state.waveformWindow = null;
    state.timechartMetrics = null;
  }
  return viewport;
}
function fitWaveformToEvent(event = selectedEvent(), options = {}) {
  if (!event) return null;
  const base = waveformWindowForEvent(event, selectedFile());
  return setWaveformViewport(base.start, base.duration, { eventId: event.event_id, invalidate: options.invalidate !== false });
}
function waveformViewportMatchesPayload(payload) {
  if (!payload) return false;
  const viewport = currentWaveformViewport();
  const start = Number(payload.start_sec || 0);
  const stop = Number(payload.stop_sec ?? (start + Number(payload.duration_sec || 0)));
  return Math.abs(start - viewport.start) < 0.05 && Math.abs((stop - start) - viewport.duration) < 0.08;
}
function waveformChannelsForRequest() {
  const channel = String(state.parameters.eeg_channel || "").trim();
  return channel ? [channel] : [];
}
function waveformFilterProfileId() {
  return state.activeWaveformLabel === "filter_preview_figure" ? "preview_0p5_45_notch50" : "raw";
}
function waveformWindowMatchesActiveView(payload) {
  if (!payload) return false;
  return String(payload.filter_profile_id || "raw") === waveformFilterProfileId() && waveformViewportMatchesPayload(payload);
}
function waveformGainMultiplier() {
  const value = state.waveformInteraction?.gain || "auto";
  if (value === "auto") return 1;
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 1;
}
function correctionModeActive() {
  return state.waveformInteraction?.mode === "correct";
}
function setWaveformMode(mode) {
  state.waveformInteraction.mode = mode === "correct" ? "correct" : "browse";
  render();
}
function setWaveformGain(gain) {
  state.waveformInteraction.gain = WAVEFORM_GAINS.includes(String(gain)) ? String(gain) : "auto";
  state.timechartMetrics = null;
  render();
}
function stepWaveformGain(direction) {
  const current = String(state.waveformInteraction?.gain || "auto");
  const index = Math.max(0, WAVEFORM_GAINS.indexOf(current));
  const next = clamp(index + direction, 0, WAVEFORM_GAINS.length - 1);
  setWaveformGain(WAVEFORM_GAINS[next]);
}
function canRunWaveformPreview() {
  const file = selectedFile();
  const event = selectedEvent();
  return Boolean(file && event && state.task?.input_file_id === file.id && !state.waveformInFlight);
}
function scheduleWaveformPreview(reason = "viewport") {
  clearTimeout(waveformPreviewTimer);
  waveformPreviewTimer = setTimeout(() => {
    waveformPreviewTimer = null;
    if (canRunWaveformPreview()) runWaveformPreview({ reason, automatic: true });
  }, WAVEFORM_DEBOUNCE_MS);
}
function updateWaveformViewportAndSchedule(startSec, durationSec, reason = "viewport") {
  setWaveformViewport(startSec, durationSec, { eventId: selectedEvent()?.event_id, keepPreview: true });
  render();
  scheduleWaveformPreview(reason);
}
function zoomWaveformAtRatio(ratio, factor) {
  const viewport = currentWaveformViewport();
  const anchorRatio = clamp(ratio, 0, 1);
  const anchorTime = viewport.start + viewport.duration * anchorRatio;
  const nextDuration = clamp(viewport.duration * factor, WAVEFORM_MIN_DURATION_SEC, WAVEFORM_MAX_DURATION_SEC);
  const nextStart = anchorTime - anchorRatio * nextDuration;
  updateWaveformViewportAndSchedule(nextStart, nextDuration, "zoom");
}
function panWaveformBy(deltaSec) {
  const viewport = currentWaveformViewport();
  updateWaveformViewportAndSchedule(viewport.start + deltaSec, viewport.duration, "pan");
}
function zoomWaveformToRatioRange(startRatio, endRatio) {
  const viewport = currentWaveformViewport();
  const leftRatio = clamp(Math.min(startRatio, endRatio), 0, 1);
  const rightRatio = clamp(Math.max(startRatio, endRatio), 0, 1);
  if (rightRatio - leftRatio < 0.01) return;
  const nextStart = viewport.start + viewport.duration * leftRatio;
  const nextDuration = viewport.duration * (rightRatio - leftRatio);
  updateWaveformViewportAndSchedule(nextStart, nextDuration, "selection-zoom");
}
function resetWaveformToEvent() {
  const event = selectedEvent();
  const viewport = fitWaveformToEvent(event);
  if (viewport) {
    render();
    scheduleWaveformPreview("fit-event");
  }
}
function toggleWaveformFilter() {
  state.activeWaveformLabel = state.activeWaveformLabel === "raw_preview_figure" ? "filter_preview_figure" : "raw_preview_figure";
  state.timechartMetrics = null;
  render();
  scheduleWaveformPreview("filter-toggle");
}
function renderWaveformMiniMap(event = selectedEvent(), viewport = currentWaveformViewport(event), file = selectedFile()) {
  const duration = recordingDurationSec(file);
  if (!duration) {
    return `<div class="waveform-minimap empty-mini" data-testid="epilepsy-waveform-minimap">No duration metadata</div>`;
  }
  const pct = (value) => clamp((Number(value) / duration) * 100, 0, 100);
  const viewportLeft = pct(viewport.start);
  const viewportWidth = Math.max(1, pct(viewport.duration));
  const eventLeft = event ? pct(numeric(event.start_sec)) : 0;
  const eventWidth = event ? Math.max(0.8, pct(numeric(event.end_sec) - numeric(event.start_sec))) : 0;
  return `<div class="waveform-minimap" data-testid="epilepsy-waveform-minimap" aria-label="waveform window overview">
    <span class="waveform-minimap-track"></span>
    <span class="waveform-minimap-window" style="left:${viewportLeft}%;width:${Math.min(100 - viewportLeft, viewportWidth)}%"></span>
    ${event ? `<span class="waveform-minimap-event" style="left:${eventLeft}%;width:${Math.min(100 - eventLeft, eventWidth)}%"></span>` : ""}
  </div>`;
}
function loadExternalScript(url) {
  return new Promise((resolve, reject) => {
    let settled = false;
    const finish = (callback, value) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      callback(value);
    };
    const timer = setTimeout(() => finish(reject, new Error(`timeout loading ${url}`)), TIMECHART_SCRIPT_TIMEOUT_MS);
    const existing = Array.from(document.scripts).find((script) => script.dataset.dynamicSrc === url);
    if (existing?.dataset.loaded === "true") {
      finish(resolve, url);
      return;
    }
    if (existing) {
      existing.addEventListener("load", () => finish(resolve, url), { once: true });
      existing.addEventListener("error", () => finish(reject, new Error(`failed to load ${url}`)), { once: true });
      return;
    }
    const script = document.createElement("script");
    script.src = url;
    script.async = true;
    script.dataset.dynamicSrc = url;
    script.addEventListener("load", () => {
      script.dataset.loaded = "true";
      finish(resolve, url);
    }, { once: true });
    script.addEventListener("error", () => finish(reject, new Error(`failed to load ${url}`)), { once: true });
    document.head.appendChild(script);
  });
}
async function loadFirstScript(urls, predicate) {
  let lastError = null;
  for (const url of urls) {
    try {
      await loadExternalScript(url);
      if (!predicate || predicate()) return url;
    } catch (error) {
      lastError = error;
    }
  }
  throw lastError || new Error("script unavailable");
}
async function ensureTimeChart() {
  if (window.TimeChart) {
    state.timechartLoadState = "ready";
    return window.TimeChart;
  }
  state.timechartLoadState = "loading";
  state.timechartLoadError = "";
  if (!window.d3) await loadFirstScript(TIMECHART_D3_SOURCES, () => Boolean(window.d3));
  await loadFirstScript(TIMECHART_CDN_SOURCES, () => Boolean(window.TimeChart));
  state.timechartLoadState = "ready";
  return window.TimeChart;
}
function waveformPayloadKey(payload) {
  return [
    payload?.file_id || state.selectedFileId || "",
    payload?.start_sec,
    payload?.stop_sec,
    payload?.filter_profile_id || "raw",
    (payload?.channels || []).map((channel) => channel.name || "").join("|"),
  ].join(":");
}
function timechartPalette(index) {
  return ["#0f766e", "#2563eb", "#7c3aed", "#c2410c", "#15803d", "#be123c", "#475569"][index % 7];
}
function buildTimeChartSeries(payload) {
  const channels = Array.isArray(payload?.channels) ? payload.channels : [];
  const rowSpacing = 120;
  let pointCount = 0;
  const series = channels.map((channel, index) => {
    const times = Array.isArray(channel.times_sec) ? channel.times_sec : [];
    const rawValues = channel.encoding === "minmax"
      ? times.map((_, pointIndex) => (numeric((channel.min_values || [])[pointIndex]) + numeric((channel.max_values || [])[pointIndex])) / 2)
      : (Array.isArray(channel.values) ? channel.values : []);
    const finite = rawValues.map(Number).filter(Number.isFinite);
    const absMax = Math.max(1e-9, ...finite.map((value) => Math.abs(value)));
    const scale = (42 * waveformGainMultiplier()) / absMax;
    const offset = (channels.length - index - 1) * rowSpacing;
    const data = times.map((time, pointIndex) => ({
      x: numeric(time),
      y: offset - numeric(rawValues[pointIndex]) * scale,
    }));
    pointCount += data.length;
    return { name: channel.name || `CH${index + 1}`, data, color: timechartPalette(index) };
  });
  return {
    series,
    pointCount,
    rowSpacing,
    yMin: -rowSpacing * 0.6,
    yMax: Math.max(rowSpacing, channels.length * rowSpacing - rowSpacing * 0.4),
  };
}
function renderTimeChartHost(payload) {
  const channels = Array.isArray(payload?.channels) ? payload.channels : [];
  const start = Number(payload.start_sec || 0);
  const stop = Number(payload.stop_sec ?? (start + Number(payload.duration_sec || 0)));
  const selected = selectedEvent();
  const eventStartPct = selected ? clamp((numeric(selected.start_sec) - start) / Math.max(0.001, stop - start), 0, 1) * 100 : 0;
  const eventEndPct = selected ? clamp((numeric(selected.end_sec) - start) / Math.max(0.001, stop - start), 0, 1) * 100 : 0;
  const labels = channels.map((channel, index) => `<span style="top:${8 + (index + 0.5) * (84 / Math.max(1, channels.length))}%">${h(channel.name || `CH${index + 1}`)}</span>`).join("");
  const meta = `${fmt(start, 2)}-${fmt(stop, 2)}s | ${h(payload.filter_profile?.description || payload.filter_profile_id || "raw")} | ${h(payload.unit || "")}`;
  return `<div class="waveform-window timechart-window" data-timechart-key="${h(waveformPayloadKey(payload))}">
    <div class="waveform-meta">${meta}<span class="timechart-status" id="timechartStatus">TimeChart experimental</span></div>
    <div class="timechart-shell">
      <div class="timechart-host" id="timechartWaveformHost" data-testid="epilepsy-timechart-host"></div>
      ${selected ? `<div class="timechart-event-overlay" style="left:${eventStartPct}%;width:${Math.max(0.5, eventEndPct - eventStartPct)}%"></div>` : ""}
      <div class="timechart-channel-labels">${labels}</div>
    </div>
  </div>`;
}
async function hydrateWaveformRenderer() {
  if (state.waveformRenderer !== "timechart") return;
  const host = document.querySelector("#timechartWaveformHost");
  const status = document.querySelector("#timechartStatus");
  const payload = state.waveformWindow;
  if (!host || !payload || host.dataset.rendered === waveformPayloadKey(payload)) return;
  host.dataset.rendered = waveformPayloadKey(payload);
  const started = performance.now();
  try {
    if (status) status.textContent = "loading TimeChart";
    const TimeChart = await ensureTimeChart();
    const start = Number(payload.start_sec || 0);
    const stop = Number(payload.stop_sec ?? (start + Number(payload.duration_sec || 0)));
    const built = buildTimeChartSeries(payload);
    host.innerHTML = "";
    state.timechartInstance?.dispose?.();
    state.timechartInstance = new TimeChart(host, {
      series: built.series,
      xRange: { min: start, max: stop },
      yRange: { min: built.yMin, max: built.yMax },
      zoom: { x: { autoRange: false }, y: { autoRange: false } },
    });
    state.timechartMetrics = {
      renderer: "timechart",
      fallback: false,
      point_count: built.pointCount,
      channel_count: built.series.length,
      duration_ms: Number((performance.now() - started).toFixed(2)),
      payload_key: waveformPayloadKey(payload),
    };
    window.__QLANALYSER_EPILEPSY_TIMECHART__ = state.timechartMetrics;
    if (status) status.textContent = `TimeChart ${state.timechartMetrics.duration_ms} ms`;
  } catch (error) {
    state.timechartLoadState = "failed";
    state.timechartLoadError = error.message || String(error);
    state.timechartMetrics = {
      renderer: "svg",
      fallback: true,
      error: state.timechartLoadError,
      duration_ms: Number((performance.now() - started).toFixed(2)),
      payload_key: waveformPayloadKey(payload),
    };
    window.__QLANALYSER_EPILEPSY_TIMECHART__ = state.timechartMetrics;
    host.innerHTML = renderWaveformWindow(payload);
    if (status) status.textContent = `SVG fallback: ${state.timechartLoadError}`;
  }
}
function scoreLabel() {
  return state.task?.module_name === "epilepsy_ml" || state.summary?.method === "ml_epoch_classifier" || state.algorithmMode === "ml_epoch_classifier"
    ? "probability"
    : "mean RMS";
}
function syncIcons() { if (window.lucide) window.lucide.createIcons(); }

async function request(path, options = {}) {
  const response = await fetch(api(path), options);
  if (!response.ok) {
    let detail = await response.text();
    try {
      const parsed = JSON.parse(detail);
      detail = parsed.detail?.message || parsed.detail?.error_code || parsed.detail || parsed.message || JSON.stringify(parsed);
    } catch {}
    throw new Error(String(detail || `HTTP ${response.status}`));
  }
  const type = response.headers.get("content-type") || "";
  return type.includes("application/json") ? response.json() : response.text();
}

function parseCsv(text) {
  const rows = [];
  const source = String(text || "").trim();
  if (!source) return rows;
  const lines = source.split(/\r?\n/);
  const headers = splitCsvLine(lines.shift()).map((item) => item.trim());
  for (const line of lines) {
    if (!line.trim()) continue;
    const values = splitCsvLine(line);
    const row = {};
    headers.forEach((header, index) => { row[header] = values[index] ?? ""; });
    rows.push(row);
  }
  return rows;
}

function splitCsvLine(line) {
  const out = [];
  let current = "";
  let quote = false;
  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i];
    if (ch === '"' && line[i + 1] === '"') {
      current += '"';
      i += 1;
    } else if (ch === '"') {
      quote = !quote;
    } else if (ch === "," && !quote) {
      out.push(current);
      current = "";
    } else {
      current += ch;
    }
  }
  out.push(current);
  return out;
}

function epochLengthSec() {
  const fromSummary = Number(state.summary?.epoch_length_sec || state.summary?.parameters?.epoch_length_sec);
  if (Number.isFinite(fromSummary) && fromSummary > 0) return fromSummary;
  const fromState = Number(state.parameters.epoch_length_sec);
  return Number.isFinite(fromState) && fromState > 0 ? fromState : 5;
}

function epochIndexOf(row, fallback = 0) {
  const raw = row?.epoch_index ?? row?.Epoch ?? row?.epoch ?? fallback;
  const value = Number(raw);
  return Number.isFinite(value) ? value : fallback;
}

function stageCodeOf(row) {
  const raw = row?.Stage_Code ?? row?.stage_code ?? row?.prediction ?? row?.classification;
  if (raw !== undefined && raw !== "") {
    if (String(raw).toLowerCase() === "seizure") return 1;
    return Number(raw) >= 1 ? 1 : 0;
  }
  if (String(row?.Stage || "").toLowerCase() === "seizure") return 1;
  if (boolValue(row?.is_event_epoch) || boolValue(row?.above_threshold)) return 1;
  return 0;
}

function stageName(code) {
  return Number(code) === 1 ? "Seizure" : "Normal";
}

function normalizeEpochRows(rows) {
  const length = epochLengthSec();
  return rows.map((row, fallbackIndex) => {
    const index = epochIndexOf(row, fallbackIndex);
    const code = stageCodeOf(row);
    const startSec = Number.isFinite(Number(row.start_sec)) ? Number(row.start_sec) : index * length;
    const endSec = Number.isFinite(Number(row.end_sec)) ? Number(row.end_sec) : startSec + length;
    const probability = row.probability ?? row.mean_rms ?? row.score ?? "";
    return {
      ...row,
      epoch_index: String(index),
      start_sec: String(startSec),
      end_sec: String(endSec),
      Stage_Code: String(code),
      Stage: stageName(code),
      source_Stage_Code: row.source_Stage_Code ?? String(code),
      source_Stage: row.source_Stage ?? stageName(code),
      probability,
      mean_rms: row.mean_rms ?? probability,
      is_event_epoch: String(boolValue(row.is_event_epoch)),
    };
  });
}

function selectedEpochRange() {
  const max = Math.max(0, state.epochRows.length - 1);
  const start = clamp(state.epochSelectionStart, 0, max);
  const end = clamp(state.epochSelectionEnd, 0, max);
  return start <= end ? { start, end } : { start: end, end: start };
}

function setEpochSelection(start, end = start) {
  const max = Math.max(0, state.epochRows.length - 1);
  state.epochSelectionStart = clamp(start, 0, max);
  state.epochSelectionEnd = clamp(end, 0, max);
  state.selectedEpoch = state.epochSelectionStart;
}

function visibleEpochRows() {
  const rows = state.epochRows;
  if (!rows.length || state.visibleEpochCount === "All") return rows;
  const count = Math.max(1, Number(state.visibleEpochCount) || rows.length);
  const maxStart = Math.max(0, rows.length - count);
  const start = clamp(state.epochWindowStart, 0, maxStart);
  state.epochWindowStart = start;
  return rows.slice(start, start + count);
}

function buildEventsFromEpochRows(rows) {
  const events = [];
  const eventMask = new Set();
  const minEpochs = 2;
  let runStart = null;
  const closeRun = (endPosition) => {
    if (runStart === null) return;
    const span = endPosition - runStart + 1;
    if (span >= minEpochs) {
      const eventIndex = events.length + 1;
      const first = rows[runStart];
      const last = rows[endPosition];
      for (let i = runStart; i <= endPosition; i += 1) eventMask.add(epochIndexOf(rows[i], i));
      const values = rows.slice(runStart, endPosition + 1).map((row) => numeric(row.probability ?? row.mean_rms));
      const maxValue = Math.max(...values, 0);
      events.push({
        event_id: String(eventIndex),
        start_sec: String(numeric(first.start_sec)),
        end_sec: String(numeric(last.end_sec)),
        duration_sec: String(Math.max(0, numeric(last.end_sec) - numeric(first.start_sec))),
        start_epoch: String(epochIndexOf(first, runStart)),
        end_epoch: String(epochIndexOf(last, endPosition)),
        source_start_epoch_1based: String(epochIndexOf(first, runStart) + 1),
        source_end_epoch_1based: String(epochIndexOf(last, endPosition) + 1),
        epoch_count: String(span),
        rms: String(maxValue),
        max_probability: String(maxValue),
        source: "local_manual_stage_recompute",
      });
    }
    runStart = null;
  };

  rows.forEach((row, index) => {
    if (stageCodeOf(row) === 1) {
      if (runStart === null) runStart = index;
    } else {
      closeRun(index - 1);
    }
  });
  closeRun(rows.length - 1);

  return { events, eventMask };
}

function applyEpochOverrides() {
  const rows = state.sourceEpochRows.map((row, fallbackIndex) => {
    const index = epochIndexOf(row, fallbackIndex);
    const sourceCode = stageCodeOf(row);
    const override = state.epochOverrides[index];
    const code = override === undefined ? sourceCode : Number(override);
    return {
      ...row,
      Stage_Code: String(code),
      Stage: stageName(code),
      manually_corrected: String(override !== undefined),
    };
  });
  const { events, eventMask } = buildEventsFromEpochRows(rows);
  state.epochRows = rows.map((row, fallbackIndex) => ({
    ...row,
    is_event_epoch: String(eventMask.has(epochIndexOf(row, fallbackIndex))),
  }));
  state.eventRows = events.length || state.sourceEpochRows.length ? events : state.sourceEventRows;

  if (!state.eventRows.length) {
    state.selectedEventId = "";
  } else if (!state.eventRows.some((event) => String(event.event_id) === String(state.selectedEventId))) {
    const containing = state.eventRows.find((event) => {
      const epoch = Number(state.selectedEpoch);
      return epoch >= Number(event.start_epoch) && epoch <= Number(event.end_epoch);
    });
    state.selectedEventId = String((containing || state.eventRows[0]).event_id);
  }
}

function readParametersFromForm() {
  const form = document.querySelector("#parameterForm");
  if (!form) return;
  for (const key of Object.keys(state.parameters)) {
    const element = form.elements[key];
    if (!element) continue;
    state.parameters[key] = element.value;
  }
}

function buildTaskParameters() {
  const badChannels = String(state.parameters.bad_channels || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  const eegChannel = String(state.parameters.eeg_channel || "").trim();
  if (state.algorithmMode === "ml_epoch_classifier") {
    return {
      method: "ml_epoch_classifier",
      display_alias: "Epilepsy ML source-compatible workbench",
      lab_mode: true,
      lab_fixture_id: "epilepsy_ml_demo_source_channels_v1",
      sync_mirror_note: "Workbench uses the source-compatible epilepsy_ml_xgboost backend workflow.",
      non_medical_boundary: "Research screening/support only; no diagnosis, treatment, or clinical decision-making.",
      eeg_channel: eegChannel || undefined,
      epoch_length_sec: Number(state.parameters.epoch_length_sec || 5),
      probability_threshold: 0.5,
      unit_mode: "source_compatible",
      bad_channels: badChannels,
    };
  }
  return {
    method: "std_threshold",
    display_alias: "癫痫样事件分析工作台",
    lab_mode: true,
    lab_fixture_id: "epilepsy_workbench_lab_v1",
    sync_mirror_note: "Workbench uses the same epilepsy_std_threshold backend workflow; ML high-fidelity migration will plug into this workbench.",
    non_medical_boundary: "Research screening/support only; no diagnosis, treatment, or clinical decision-making.",
    eeg_channel: eegChannel || undefined,
    epoch_length_sec: Number(state.parameters.epoch_length_sec || 5),
    std_factor: Number(state.parameters.std_factor || 2),
    rms_window_samples: Number(state.parameters.rms_window_samples || 15),
    merge_gap_epoch_num: Number(state.parameters.merge_gap_epoch_num || 1),
    min_event_epochs: Number(state.parameters.min_event_epochs || 2),
    event_window_sec: Number(state.parameters.event_window_sec || 1800),
    bad_channels: badChannels,
  };
}

function loadReviews() {
  try {
    const parsed = JSON.parse(localStorage.getItem(reviewKey()) || "{}");
    if (parsed && parsed.__epilepsy_workbench_review_state === 2) {
      state.reviews = parsed.reviews || {};
      state.epochOverrides = parsed.epochOverrides || {};
      state.reviewActions = parsed.reviewActions || [];
    } else {
      state.reviews = parsed || {};
      state.epochOverrides = {};
      state.reviewActions = [];
    }
  } catch {
    state.reviews = {};
    state.epochOverrides = {};
    state.reviewActions = [];
  }
  applyEpochOverrides();
}

function persistReviews() {
  localStorage.setItem(reviewKey(), JSON.stringify({
    __epilepsy_workbench_review_state: 2,
    reviews: state.reviews,
    epochOverrides: state.epochOverrides,
    reviewActions: state.reviewActions,
    updated_at: new Date().toISOString(),
  }, null, 2));
}

function setMessage(message, error = false) {
  state.message = message;
  state.error = error;
}

function render() {
  const root = document.querySelector("#epilepsyWorkbench");
  root.innerHTML = `
    <header class="ep-top">
      <nav class="ep-nav">
        <a class="brand" href="./epilepsy-workbench.html?api=${encodeURIComponent(API_BASE)}">
          <span class="brand-mark">EP</span>
          <span><strong>癫痫样事件分析工作台</strong><small>参数 / 候选事件 / 波形预览 / 人工复核</small></span>
        </a>
        <div class="top-links">
          <a href="./module-lab.html?customer_demo=login&api=${encodeURIComponent(API_BASE)}">${icon("layout-dashboard")}返回方法库</a>
          <a href="./qc-lab.html?api=${encodeURIComponent(API_BASE)}">${icon("waves")}QC 波形页</a>
        </div>
      </nav>
    </header>
    <section class="ep-wrap">
      ${renderHero()}
      <div class="layout">
        <aside>
          ${renderFilePanel()}
          ${renderParameterPanel()}
          ${renderReviewExportPanel()}
        </aside>
        <main>
          ${renderRunSummary()}
          ${renderSourceReplicaToolbar()}
          ${renderTimelinePanel()}
          ${renderEventsPanel()}
          ${renderWaveformPanel()}
          ${renderArtifactsPanel()}
        </main>
      </div>
    </section>
  `;
  bindEvents();
  syncIcons();
  hydrateWaveformRenderer();
}

function renderHero() {
  return `<section class="hero">
    <div class="hero-card">
      <p class="eyebrow">Epileptiform research screening</p>
      <h1>进入癫痫样候选事件工作台</h1>
      <p>这里不是诊断工具。它把源模型 ML 筛查结果变成可复核工作台：参数可改、epoch 可点、候选事件可看、波形可回看、复核结果可导出。</p>
      <div class="hero-actions">
        <button class="btn primary" id="runTaskTopBtn">${icon("play")}运行筛查</button>
        <button class="btn" id="loadLatestEpilepsyFileBtn">${icon("database")}选中实验室数据</button>
        <button class="btn" id="refreshFilesTopBtn">${icon("refresh-cw")}刷新文件</button>
      </div>
    </div>
    <aside class="side-card">
      <h2>边界</h2>
      <ul class="status-list">
        <li><strong>同源工作流</strong><span>默认提交 module_name=epilepsy_ml / workflow_id=epilepsy_ml_xgboost；STD 可作为基线切换。</span></li>
        <li><strong>人工复核</strong><span>复核层保存在浏览器本地，可导出 JSON/CSV；不会改原始 EEG。</span></li>
        <li><strong>非医疗</strong><span>仅用于科研筛查和候选事件复核，不用于诊断、确诊、治疗或临床决策。</span></li>
      </ul>
    </aside>
  </section>`;
}

function renderFilePanel() {
  const options = state.files.map((file) => {
    const rawName = String(file.original_filename || file.filename || file.label || file.id || "");
    const label = /epilepsy|high_amplitude/i.test(rawName)
      ? `癫痫实验室数据：${rawName}`
      : (/demo|sample|teaching|synthetic/i.test(rawName) ? `教学示例：${rawName}` : rawName || file.id);
    return `<option value="${h(file.id)}" ${file.id === state.selectedFileId ? "selected" : ""}>${h(label)}</option>`;
  }).join("");
  return `<section class="panel">
    <h2>${icon("folder-open")}数据文件</h2>
    <div class="field">
      <label>选择 EEG 文件</label>
      <select id="fileSelect" data-testid="epilepsy-file-select"><option value="">请选择文件</option>${options}</select>
    </div>
    <div class="inline-actions">
      <button class="btn" id="refreshFilesBtn">${icon("refresh-cw")}刷新</button>
      <button class="btn" id="selectEpilepsyFixtureBtn">${icon("target")}选实验室数据</button>
    </div>
    <form class="upload-box" id="uploadForm">
      <div class="field">
        <label>上传 EEG</label>
        <input type="file" id="uploadInput" accept=".edf,.bdf,.fif,.fif.gz,.vhdr,.set,.cnt" />
      </div>
      <button class="btn primary" type="submit" ${state.uploadInFlight ? "disabled" : ""}>${icon("upload")}上传并选中</button>
    </form>
    <p class="message ${state.error ? "error" : ""}" data-testid="epilepsy-message">${h(state.message)}</p>
  </section>`;
}

function renderParameterPanel() {
  const p = state.parameters;
  const isMl = state.algorithmMode === "ml_epoch_classifier";
  const runLabel = isMl ? "运行 ML 高保真筛查" : "运行 STD 阈值筛查";
  const notice = isMl
    ? "当前算法底座为源项目 XGBoost ML：模型文件 hash 校验、19 个特征顺序、0.5 阈值、完整 epoch 截断和连续 2 个 epoch 事件规则均按源代码迁移。"
    : "当前算法底座为 STD 阈值筛查；可随时切换到 ML 高保真模式。";
  return `<section class="panel">
    <h2>${icon("sliders-horizontal")}参数设置</h2>
    <div class="field">
      <label>算法</label>
      <select id="algorithmModeSelect">
        <option value="ml_epoch_classifier" ${isMl ? "selected" : ""}>ML 高保真源模型</option>
        <option value="std_threshold" ${!isMl ? "selected" : ""}>STD 阈值基线</option>
      </select>
    </div>
    <form id="parameterForm">
      <div class="field"><label>EEG 通道</label><input name="eeg_channel" value="${h(p.eeg_channel)}" placeholder="空 = 第一个可用 EEG" /></div>
      <div class="grid-2">
        <div class="field"><label>Epoch 长度（秒）</label><input name="epoch_length_sec" type="number" step="0.5" value="${h(p.epoch_length_sec)}" /></div>
        <div class="field"><label>STD 阈值系数</label><input name="std_factor" type="number" step="0.1" value="${h(p.std_factor)}" /></div>
        <div class="field"><label>RMS 窗口（样本）</label><input name="rms_window_samples" type="number" step="1" value="${h(p.rms_window_samples)}" /></div>
        <div class="field"><label>合并间隔（epoch）</label><input name="merge_gap_epoch_num" type="number" step="1" value="${h(p.merge_gap_epoch_num)}" /></div>
        <div class="field"><label>最小事件（epoch）</label><input name="min_event_epochs" type="number" step="1" value="${h(p.min_event_epochs)}" /></div>
        <div class="field"><label>统计窗口（秒）</label><input name="event_window_sec" type="number" step="60" value="${h(p.event_window_sec)}" /></div>
      </div>
      <div class="field"><label>排除通道</label><input name="bad_channels" value="${h(p.bad_channels)}" placeholder="英文逗号分隔" /></div>
    </form>
    <button class="btn primary" id="runTaskBtn" data-testid="epilepsy-run" ${state.runInFlight ? "disabled" : ""}>${icon("play")}${runLabel}</button>
    <p class="notice">${h(notice)}</p>
  </section>`;
}

function renderReviewExportPanel() {
  const taskId = state.task?.id || "未运行";
  const correctedCount = Object.keys(state.epochOverrides).length;
  return `<section class="panel">
    <h2>${icon("clipboard-check")}复核导出</h2>
    <div class="field">
      <label>当前任务</label>
      <input value="${h(taskId)}" readonly />
    </div>
    <div class="inline-actions">
      <button class="btn" id="undoReviewBtn" ${state.history.length ? "" : "disabled"}>${icon("undo-2")}Undo</button>
      <button class="btn" id="redoReviewBtn" ${state.future.length ? "" : "disabled"}>${icon("redo-2")}Redo</button>
      <button class="btn warn" id="resetReviewsBtn" ${(Object.keys(state.reviews).length || correctedCount) ? "" : "disabled"}>${icon("rotate-ccw")}Reset</button>
    </div>
    <div class="inline-actions">
      <button class="btn" id="downloadReviewJsonBtn" ${state.task ? "" : "disabled"}>${icon("download")}导出 JSON</button>
      <button class="btn" id="downloadReviewCsvBtn" ${state.task ? "" : "disabled"}>${icon("table")}导出矫正 Epoch CSV</button>
      <button class="btn" id="downloadEventsCsvBtn" ${state.task ? "" : "disabled"}>${icon("list-checks")}导出事件 CSV</button>
    </div>
    <p class="kbd-hint">快捷键：Shift+2 将当前 epoch 范围标为 Seizure；Shift+1 标为 Normal。已矫正 epoch：${correctedCount}，动作记录：${state.reviewActions.length}</p>
  </section>`;
}

function renderRunSummary() {
  const summary = state.summary || {};
  const reviewed = Object.keys(state.reviews).length + Object.keys(state.epochOverrides).length;
  return `<section class="panel">
    <div class="panel-head">
      <h2>${icon("activity")}工作台概览</h2>
      <span class="badge ${state.task?.status === "completed" ? "" : "warn"}">${h(state.task?.status || "等待运行")}</span>
    </div>
    <div class="metric-grid">
      <div class="metric"><span>候选事件</span><strong>${summary.event_count ?? (state.eventRows.length || "-")}</strong></div>
      <div class="metric"><span>Epoch</span><strong>${summary.epoch_count ?? (state.epochRows.length || "-")}</strong></div>
      <div class="metric"><span>阈值</span><strong>${summary.threshold ? fmt(summary.threshold, 7) : "-"}</strong></div>
      <div class="metric"><span>人工修改</span><strong>${reviewed}</strong></div>
    </div>
    <pre class="param-preview">${h(JSON.stringify({
      task_id: state.task?.id,
      workflow_id: state.task?.workflow_id,
      input_file_id: state.task?.input_file_id,
      parameters: state.task?.parameters_json || buildTaskParameters(),
    }, null, 2))}</pre>
  </section>`;
}

function renderSourceReplicaToolbar() {
  const total = state.epochRows.length;
  if (!total) {
    return `<section class="panel source-replica">
      <h2>${icon("panel-top")}ML Epilepsy Analysis 源交互区</h2>
      <div class="empty">运行分析后，这里会显示源代码式 epoch 导航、Seizure/Normal 人工矫正、Undo/Redo/Reset 和幅度控制。</div>
    </section>`;
  }
  const range = selectedEpochRange();
  const currentPage = state.visibleEpochCount === "All"
    ? 1
    : Math.floor(state.epochWindowStart / Math.max(1, Number(state.visibleEpochCount))) + 1;
  const totalPages = state.visibleEpochCount === "All"
    ? 1
    : Math.max(1, Math.ceil(total / Math.max(1, Number(state.visibleEpochCount))));
  const countOptions = ["All", "100", "50", "30", "20", "10", "5", "3"].map((value) =>
    `<option value="${value}" ${String(state.visibleEpochCount) === value ? "selected" : ""}>${value}</option>`
  ).join("");
  const stageEditDisabled = correctionModeActive() ? "" : "disabled";
  return `<section class="panel source-replica">
    <div class="panel-head">
      <h2>${icon("panel-top")}ML Epilepsy Analysis 源交互区</h2>
      <span class="badge">Page ${currentPage} of ${totalPages}</span>
    </div>
    <div class="source-toolbar">
      <div class="field compact">
        <label>Number of Epochs to display</label>
        <select id="visibleEpochCountSelect">${countOptions}</select>
      </div>
      <div class="source-nav" aria-label="epoch navigation">
        <button class="btn icon-only" data-nav-epoch="first" title="First">${icon("skip-back")}</button>
        <button class="btn icon-only" data-nav-epoch="previous" title="Previous">${icon("chevron-left")}</button>
        <input id="gotoEpochInput" type="number" min="1" max="${total}" value="${state.selectedEpoch + 1}" aria-label="Goto epoch" />
        <button class="btn icon-only" data-nav-epoch="next" title="Next">${icon("chevron-right")}</button>
        <button class="btn icon-only" data-nav-epoch="last" title="Last">${icon("skip-forward")}</button>
      </div>
      <div class="field compact">
        <label>Start Epoch</label>
        <input id="epochRangeStartInput" type="number" min="1" max="${total}" value="${range.start + 1}" />
      </div>
      <div class="field compact">
        <label>End Epoch</label>
        <input id="epochRangeEndInput" type="number" min="1" max="${total}" value="${range.end + 1}" />
      </div>
    </div>
    <div class="source-toolbar source-editbar">
      <button class="btn danger" id="applyStageSeizureBtn" ${stageEditDisabled}>${icon("badge-alert")}Seizure</button>
      <button class="btn primary" id="applyStageNormalBtn" ${stageEditDisabled}>${icon("check")}Normal</button>
      <button class="btn" id="sourceUndoBtn" ${state.history.length ? "" : "disabled"}>${icon("undo-2")}Undo</button>
      <button class="btn" id="sourceRedoBtn" ${state.future.length ? "" : "disabled"}>${icon("redo-2")}Redo</button>
      <button class="btn warn" id="sourceResetBtn" ${(Object.keys(state.reviews).length || Object.keys(state.epochOverrides).length) ? "" : "disabled"}>${icon("rotate-ccw")}Reset</button>
      <div class="field compact">
        <label>EEG amplitude</label>
        <select id="eegAmplitudeSelect" aria-label="EEG amplitude">
          <option>Auto</option><option>±100</option><option>±200</option><option>±500</option><option>±1000</option><option>±2000</option>
        </select>
      </div>
      <div class="field compact">
        <label>EMG amplitude</label>
        <select aria-label="EMG amplitude">
          <option>Auto</option><option>±50</option><option>±100</option><option>±200</option><option>±500</option>
        </select>
      </div>
      <div class="field compact">
        <label>ACC amplitude</label>
        <select aria-label="ACC amplitude">
          <option>Auto</option><option>±500</option><option>±1000</option><option>±2000</option><option>±4000</option>
        </select>
      </div>
    </div>
    <p class="kbd-hint">当前选择：epoch ${range.start + 1} - ${range.end + 1}。Seizure/Normal 只有在 Correction mode 中才会修改选中 epoch 的 Stage_Code，并触发本地事件重算。</p>
  </section>`;
}

function renderTimelinePanel() {
  const label = scoreLabel();
  if (!state.epochRows.length) {
    return `<section class="panel"><h2>${icon("bar-chart-3")}Epoch 时间轴</h2><div class="empty">运行分析后会显示每个 epoch 的阈值命中、事件归属和 ${h(label)} 曲线。</div></section>`;
  }
  const range = selectedEpochRange();
  const cells = visibleEpochRows().map((row) => {
    const index = Number(row.epoch_index);
    const stageCode = stageCodeOf(row);
    const event = boolValue(row.is_event_epoch);
    const above = boolValue(row.above_threshold);
    const reviewed = eventReviewForEpoch(index);
    const inRange = index >= range.start && index <= range.end;
    const classes = ["epoch-cell", stageCode ? "seizure" : "normal", above ? "above" : "", event ? "event" : "", index === state.selectedEpoch ? "selected" : "", inRange ? "range" : "", reviewed ? "reviewed" : ""].filter(Boolean).join(" ");
    return `<button class="${classes}" data-epoch="${index}" title="${fmt(row.start_sec,1)}-${fmt(row.end_sec,1)}s">${index + 1}<small>${stageName(stageCode)}</small></button>`;
  }).join("");
  return `<section class="panel">
    <div class="panel-head">
      <h2>${icon("bar-chart-3")}Epoch 时间轴与 ${h(label)}</h2>
      <span class="badge">点击 epoch 选择；按钮改 Stage_Code</span>
    </div>
    <div class="timeline-card">
      <div class="timeline-head">
        <strong>红色 = Seizure；蓝色 = Normal；绿色边框 = 已聚合候选事件</strong>
        <span>当前 epoch：${state.selectedEpoch + 1}</span>
      </div>
      <div class="stage-axis"><span>Seizure</span><span>Normal</span></div>
      <div class="epoch-strip source-strip" style="--epoch-count:${visibleEpochRows().length}">${cells}</div>
      ${renderRmsChart()}
    </div>
  </section>`;
}

function renderRmsChart() {
  const label = scoreLabel();
  const rows = state.epochRows;
  const width = 980;
  const height = 260;
  const pad = { left: 54, right: 22, top: 22, bottom: 38 };
  const values = rows.map((row) => numeric(row.mean_rms));
  const threshold = numeric(rows[0]?.threshold);
  const maxValue = Math.max(threshold, ...values, 1e-12);
  const x = (index) => pad.left + (rows.length <= 1 ? 0 : index * (width - pad.left - pad.right) / (rows.length - 1));
  const y = (value) => pad.top + (height - pad.top - pad.bottom) * (1 - value / maxValue);
  const points = rows.map((row, index) => `${x(index)},${y(numeric(row.mean_rms))}`).join(" ");
  const eventBands = state.eventRows.map((event) => {
    const start = Math.max(0, Number(event.start_epoch || 0));
    const end = Math.min(rows.length - 1, Number(event.end_epoch || start));
    const x1 = x(start) - 8;
    const x2 = x(end) + 8;
    return `<rect class="event-band" x="${x1}" y="${pad.top}" width="${Math.max(4, x2 - x1)}" height="${height - pad.top - pad.bottom}" />`;
  }).join("");
  const circles = rows.map((row, index) => `<circle class="point ${index === state.selectedEpoch ? "selected" : ""}" cx="${x(index)}" cy="${y(numeric(row.mean_rms))}" r="${index === state.selectedEpoch ? 5 : 3}" />`).join("");
  return `<svg class="rms-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="Epoch ${h(label)} curve">
    <line class="axis" x1="${pad.left}" y1="${height - pad.bottom}" x2="${width - pad.right}" y2="${height - pad.bottom}" />
    <line class="axis" x1="${pad.left}" y1="${pad.top}" x2="${pad.left}" y2="${height - pad.bottom}" />
    ${eventBands}
    <polyline class="line" points="${points}" />
    <line class="threshold" x1="${pad.left}" x2="${width - pad.right}" y1="${y(threshold)}" y2="${y(threshold)}" />
    ${circles}
    <text x="${pad.left}" y="${height - 12}">epoch</text>
    <text x="${pad.left + 10}" y="${Math.max(14, y(threshold) - 7)}">threshold</text>
    <text x="14" y="22">${h(label)}</text>
  </svg>`;
}

function renderWaveformWindow(payload) {
  const channels = Array.isArray(payload?.channels) ? payload.channels : [];
  if (!channels.length) return `<div class="empty">当前窗口没有可显示的通道数据。</div>`;
  const width = 960;
  const channelHeight = 92;
  const pad = { left: 76, right: 24, top: 28, bottom: 34 };
  const height = pad.top + pad.bottom + channels.length * channelHeight;
  const start = Number(payload.start_sec || 0);
  const stop = Number(payload.stop_sec ?? (start + Number(payload.duration_sec || 0)));
  const xOf = (time) => pad.left + (width - pad.left - pad.right) * ((Number(time) - start) / Math.max(0.001, stop - start));
  const meta = `${fmt(start, 2)}-${fmt(stop, 2)}s · ${h(payload.filter_profile?.description || payload.filter_profile_id || "raw")} · ${h(payload.unit || "")}`;
  const traces = channels.map((channel, index) => {
    const yMid = pad.top + index * channelHeight + channelHeight / 2;
    const values = channel.encoding === "minmax" ? [...(channel.min_values || []), ...(channel.max_values || [])] : (channel.values || []);
    const finite = values.map(Number).filter(Number.isFinite);
    const absMax = Math.max(1e-9, ...finite.map((value) => Math.abs(value)));
    const scale = ((channelHeight * 0.38) * waveformGainMultiplier()) / absMax;
    const yOf = (value) => yMid - Number(value) * scale;
    const times = channel.times_sec || [];
    const shape = channel.encoding === "minmax"
      ? times.map((time, pointIndex) => {
        const x = xOf(time);
        return `<line class="waveform-envelope" x1="${x}" x2="${x}" y1="${yOf((channel.min_values || [])[pointIndex] || 0)}" y2="${yOf((channel.max_values || [])[pointIndex] || 0)}" />`;
      }).join("")
      : `<polyline class="waveform-line" points="${times.map((time, pointIndex) => `${xOf(time)},${yOf((channel.values || [])[pointIndex] || 0)}`).join(" ")}" />`;
    return `<g class="waveform-channel">
      <line class="waveform-zero" x1="${pad.left}" x2="${width - pad.right}" y1="${yMid}" y2="${yMid}" />
      <text class="waveform-channel-label" x="14" y="${yMid + 4}">${h(channel.name || `CH${index + 1}`)}</text>
      ${shape}
    </g>`;
  }).join("");
  const selected = selectedEvent();
  const eventBand = selected
    ? `<rect class="waveform-event-band" x="${xOf(numeric(selected.start_sec))}" y="${pad.top - 6}" width="${Math.max(2, xOf(numeric(selected.end_sec)) - xOf(numeric(selected.start_sec)))}" height="${height - pad.top - pad.bottom + 12}" />`
    : "";
  return `<div class="waveform-window">
    <div class="waveform-meta">${meta}</div>
    <svg class="waveform-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="EDF waveform window">
      <line class="axis" x1="${pad.left}" x2="${width - pad.right}" y1="${height - pad.bottom}" y2="${height - pad.bottom}" />
      ${eventBand}
      ${traces}
      <text x="${pad.left}" y="${height - 10}">${fmt(start, 1)}s</text>
      <text x="${width - pad.right - 52}" y="${height - 10}">${fmt(stop, 1)}s</text>
    </svg>
  </div>`;
}

function renderEventsPanel() {
  if (!state.eventRows.length) {
    return `<section class="panel"><div class="panel-head"><h2>${icon("list-checks")}候选事件与人工矫正</h2><span class="badge warn" data-testid="epilepsy-event-count">0 个候选事件</span></div><div class="empty">当前矫正后的 Stage_Code 没有形成连续 >=2 个 Seizure epoch，因此没有候选事件。可以 Undo 或把 epoch 范围重新标为 Seizure。</div></section>`;
  }
  const rows = state.eventRows.map((event) => {
    const id = String(event.event_id);
    const review = state.reviews[id] || {};
    const active = id === state.selectedEventId;
    return `<tr class="${active ? "active" : ""}">
      <td><button data-select-event="${h(id)}">#${h(id)}</button></td>
      <td>${fmt(event.start_sec, 1)} - ${fmt(event.end_sec, 1)} s</td>
      <td>${h(event.start_epoch)} - ${h(event.end_epoch)}</td>
      <td>${h(event.epoch_count)}</td>
      <td>${fmt(event.rms, 7)}</td>
      <td><span class="badge ${review.status ? "" : "warn"}">${h(reviewLabel(review.status))}</span></td>
    </tr>`;
  }).join("");
  const selected = selectedEvent();
  const selectedReview = selected ? (state.reviews[String(selected.event_id)] || {}) : {};
  const correctionReady = correctionModeActive();
  const stageButtonState = selected && correctionReady ? "" : "disabled";
  return `<section class="panel">
    <div class="panel-head">
      <h2>${icon("list-checks")}候选事件与人工矫正</h2>
      <span class="badge" data-testid="epilepsy-event-count">${state.eventRows.length} 个候选事件</span>
    </div>
    <div class="review-card">
      <div>
        <div class="table-wrap">
          <table class="data-table" data-testid="epilepsy-event-table">
            <thead><tr><th>事件</th><th>时间</th><th>Epoch</th><th>长度</th><th>RMS</th><th>复核</th></tr></thead>
            <tbody>${rows}</tbody>
          </table>
        </div>
      </div>
      <aside class="review-item active">
        <div class="review-status">
          <strong>当前事件 ${selected ? `#${h(selected.event_id)}` : "-"}</strong>
          <small>${selected ? `${fmt(selected.start_sec,1)}-${fmt(selected.end_sec,1)}s` : "未选择"}</small>
        </div>
        <div class="field">
          <label>复核备注</label>
          <textarea id="reviewNote" placeholder="例如：高幅连续 3 个 epoch，需回看原始波形。">${h(state.reviewNote || selectedReview.note || "")}</textarea>
        </div>
        <div class="review-actions">
          <button class="btn danger" id="markSeizureBtn" ${stageButtonState}>${icon("badge-alert")}Seizure</button>
          <button class="btn primary" id="markNormalBtn" ${stageButtonState}>${icon("check")}Normal</button>
          <button class="btn" id="markNeedsReviewBtn" ${selected ? "" : "disabled"}>${icon("eye")}待复核</button>
        </div>
        <p class="kbd-hint">${correctionReady ? "矫正模式已开启：Seizure/Normal 会修改当前事件 epoch 范围的工作台 Stage_Code。" : "浏览模式：Seizure/Normal 已锁定，进入 Correction mode 后才可修改 Stage_Code。"} 算法原始产物不会被覆盖。</p>
      </aside>
    </div>
  </section>`;
}

function renderWaveformPanel() {
  const selected = selectedEvent();
  const selectedId = selected ? String(selected.event_id) : "";
  const file = selectedFile();
  const viewport = currentWaveformViewport(selected, file);
  const viewportStop = viewport.start + viewport.duration;
  const mode = correctionModeActive() ? "correct" : "browse";
  const gain = String(state.waveformInteraction?.gain || "auto");
  const filterLabel = waveformFilterProfileId() === "raw" ? "Raw" : "Filter preview";
  const fileLabel = file?.original_filename || file?.filename || file?.id || "未选择 EDF";
  window.__QLANALYSER_EPILEPSY_WAVEFORM_STATE__ = {
    mode,
    gain,
    renderer: state.waveformRenderer,
    filter_profile_id: waveformFilterProfileId(),
    start_sec: viewport.start,
    duration_sec: viewport.duration,
    stop_sec: viewportStop,
    selected_event_id: selectedId,
  };
  const previewMatchesSelection = selectedId && state.waveformEventId === selectedId;
  const analysisMatchesFile = Boolean(state.task?.input_file_id && state.task.input_file_id === state.selectedFileId);
  const directWindow = previewMatchesSelection && waveformWindowMatchesActiveView(state.waveformWindow) ? state.waveformWindow : null;
  const staleWindow = previewMatchesSelection && state.waveformWindow && !directWindow ? state.waveformWindow : null;
  const figure = previewMatchesSelection
    ? (artifactByLabel(state.activeWaveformLabel, state.waveformArtifacts)
      || artifactByLabel("filter_preview_figure", state.waveformArtifacts)
      || artifactByLabel("raw_preview_figure", state.waveformArtifacts))
    : null;
  const status = state.waveformInFlight
    ? "生成中"
    : (previewMatchesSelection ? state.waveformTask?.status : "") || "未生成";
  const canRunWaveform = Boolean(selected && state.selectedFileId && analysisMatchesFile && !state.waveformInFlight);
  const gainOptions = WAVEFORM_GAINS.map((item) => `<option value="${h(item)}" ${gain === item ? "selected" : ""}>${item === "auto" ? "Auto" : `${item}x`}</option>`).join("");
  const frameBody = directWindow || staleWindow
    ? `${staleWindow ? '<div class="waveform-stale-banner">正在读取新窗口，暂显示上一帧波形。</div>' : ""}${state.waveformRenderer === "timechart" ? renderTimeChartHost(directWindow || staleWindow) : renderWaveformWindow(directWindow || staleWindow)}`
    : figure
    ? `<img src="${h(artifactUrl(figure))}" alt="癫痫候选事件波形预览" />`
    : previewMatchesSelection && state.waveformError
      ? `<div class="empty error">波形预览失败：${h(state.waveformError)}</div>`
      : state.waveformInFlight
      ? `<div class="empty">正在读取 EDF 并生成 Raw / Filter preview，请稍等。</div>`
      : selected && !analysisMatchesFile
        ? `<div class="empty">当前候选事件不是当前文件生成的，请先运行当前文件的筛查。</div>`
        : previewMatchesSelection && state.waveformTask?.status === "completed"
          ? `<div class="empty">后端任务已完成，但没有返回 Raw / Filter preview 图像产物。</div>`
      : `<div class="empty">选择候选事件后点击“刷新当前候选波形”。</div>`;
  return `<section class="panel">
    <div class="panel-head">
      <h2>${icon("waves")}候选波形预览</h2>
      <span class="badge ${status === "completed" ? "" : "warn"}">${h(status)}</span>
    </div>
    <div class="waveform-statusbar" data-testid="epilepsy-waveform-statusbar" data-mode="${h(mode)}" data-gain="${h(gain)}" data-start-sec="${viewport.start}" data-duration-sec="${viewport.duration}">
      <span><strong>File</strong>${h(fileLabel)}</span>
      <span><strong>Event</strong>${selected ? `#${h(selected.event_id)}` : "-"}</span>
      <span><strong>Window</strong>${fmt(viewport.start, 2)}-${fmt(viewportStop, 2)}s</span>
      <span><strong>Filter</strong>${h(filterLabel)}</span>
      <span><strong>Gain</strong>${gain === "auto" ? "Auto" : `${h(gain)}x`}</span>
      <span><strong>Mode</strong>${mode === "correct" ? "Correction" : "Browse"}</span>
    </div>
    ${renderWaveformMiniMap(selected, viewport, file)}
    <div class="toolbar">
      <button class="btn primary" id="runWaveformBtn" ${canRunWaveform ? "" : "disabled"}>${icon("activity")}${state.waveformInFlight ? "正在生成波形" : "刷新当前候选波形"}</button>
      <button class="btn ${state.activeWaveformLabel === "raw_preview_figure" ? "primary" : ""}" data-waveform-label="raw_preview_figure">Raw</button>
      <button class="btn ${state.activeWaveformLabel === "filter_preview_figure" ? "primary" : ""}" data-waveform-label="filter_preview_figure">Filter preview</button>
      <button class="btn" data-waveform-reset="event">${icon("locate-fixed")}Fit event</button>
      <button class="btn ${mode === "browse" ? "primary" : ""}" data-waveform-mode="browse" data-testid="epilepsy-waveform-mode-browse">${icon("hand")}Browse</button>
      <button class="btn ${mode === "correct" ? "primary" : ""}" data-waveform-mode="correct" data-testid="epilepsy-waveform-mode-correct">${icon("pencil")}Correction</button>
      <label class="waveform-gain-control">Gain
        <select data-waveform-gain data-testid="epilepsy-waveform-gain">${gainOptions}</select>
      </label>
      <span class="toolbar-spacer"></span>
      <button class="btn ${state.waveformRenderer === "svg" ? "primary" : ""}" data-waveform-renderer="svg" data-testid="epilepsy-renderer-svg">SVG current</button>
      <button class="btn ${state.waveformRenderer === "timechart" ? "primary" : ""}" data-waveform-renderer="timechart" data-testid="epilepsy-renderer-timechart">TimeChart experimental</button>
    </div>
    <p class="notice">波形预览按当前候选事件窗口生成，保留 Raw / Filter preview 两种视图，供人工复核时回看原始波形。</p>
    <div class="figure-frame waveform-frame ${mode === "correct" ? "correct-mode" : "browse-mode"}" tabindex="0" data-waveform-interactive="true" data-testid="epilepsy-waveform-frame">
      ${frameBody}
      <div class="waveform-selection-overlay" data-testid="epilepsy-waveform-selection" hidden></div>
    </div>
  </section>`;
}

function renderArtifactsPanel() {
  if (!state.artifacts.length) {
    return `<section class="panel"><h2>${icon("download")}结果文件</h2><div class="empty">运行后会列出 epoch 表、事件表、summary、参数和复现记录。</div></section>`;
  }
  const links = state.artifacts.map((item) => `<a class="artifact" href="${h(artifactUrl(item))}" target="_blank" rel="noopener">
    <span>${h(item.artifact_type)}</span>
    <strong>${h(item.label || item.path || "output")}</strong>
    <small>${h(item.mime_type || "可下载产物")}</small>
  </a>`).join("");
  return `<section class="panel">
    <div class="panel-head"><h2>${icon("download")}结果文件</h2><span class="badge">${state.artifacts.length} 个产物</span></div>
    <div class="artifact-grid">${links}</div>
  </section>`;
}

function eventReviewForEpoch(epochIndex) {
  if (state.epochOverrides[epochIndex] !== undefined) return "manual_stage";
  const event = state.eventRows.find((item) => epochIndex >= Number(item.start_epoch) && epochIndex <= Number(item.end_epoch));
  return event ? state.reviews[String(event.event_id)]?.status : "";
}

function selectedEvent() {
  if (!state.selectedEventId && state.eventRows.length) state.selectedEventId = String(state.eventRows[0].event_id);
  return state.eventRows.find((item) => String(item.event_id) === String(state.selectedEventId));
}

function reviewLabel(status) {
  return {
    seizure_candidate: "Seizure",
    normal: "Normal",
    needs_review: "待复核",
    manual_stage: "已矫正",
  }[status] || "未复核";
}

function bindEvents() {
  document.querySelector("#refreshFilesBtn")?.addEventListener("click", loadFiles);
  document.querySelector("#refreshFilesTopBtn")?.addEventListener("click", loadFiles);
  document.querySelector("#loadLatestEpilepsyFileBtn")?.addEventListener("click", selectLatestEpilepsyFixture);
  document.querySelector("#selectEpilepsyFixtureBtn")?.addEventListener("click", selectLatestEpilepsyFixture);
  document.querySelector("#algorithmModeSelect")?.addEventListener("change", (event) => {
    state.algorithmMode = event.target.value === "std_threshold" ? "std_threshold" : "ml_epoch_classifier";
    resetAnalysisOutputs();
    render();
  });
  document.querySelector("#fileSelect")?.addEventListener("change", (event) => {
    const nextFileId = event.target.value;
    if (nextFileId !== state.selectedFileId) {
      state.selectedFileId = nextFileId;
      resetAnalysisOutputs();
      if (nextFileId) setMessage("已切换数据文件，请重新运行筛查后再刷新候选波形。", false);
    } else {
      state.selectedFileId = nextFileId;
    }
    render();
  });
  document.querySelector("#uploadForm")?.addEventListener("submit", uploadFile);
  document.querySelector("#runTaskBtn")?.addEventListener("click", runEpilepsyTask);
  document.querySelector("#runTaskTopBtn")?.addEventListener("click", runEpilepsyTask);
  document.querySelector("#parameterForm")?.addEventListener("input", readParametersFromForm);
  document.querySelector("#visibleEpochCountSelect")?.addEventListener("change", (event) => setVisibleEpochCount(event.target.value));
  document.querySelector("#gotoEpochInput")?.addEventListener("change", (event) => gotoEpoch(Number(event.target.value) - 1));
  document.querySelector("#epochRangeStartInput")?.addEventListener("change", updateEpochRangeFromInputs);
  document.querySelector("#epochRangeEndInput")?.addEventListener("change", updateEpochRangeFromInputs);
  document.querySelectorAll("[data-nav-epoch]").forEach((button) => button.addEventListener("click", () => navigateEpoch(button.dataset.navEpoch)));
  document.querySelector("#applyStageSeizureBtn")?.addEventListener("click", () => applyStageToSelection(1));
  document.querySelector("#applyStageNormalBtn")?.addEventListener("click", () => applyStageToSelection(0));
  document.querySelector("#sourceUndoBtn")?.addEventListener("click", undoReview);
  document.querySelector("#sourceRedoBtn")?.addEventListener("click", redoReview);
  document.querySelector("#sourceResetBtn")?.addEventListener("click", resetReviews);
  document.querySelectorAll("[data-epoch]").forEach((button) => button.addEventListener("click", (event) => selectEpoch(Number(button.dataset.epoch), event.shiftKey)));
  document.querySelectorAll("[data-select-event]").forEach((button) => button.addEventListener("click", () => selectEvent(button.dataset.selectEvent)));
  document.querySelector("#reviewNote")?.addEventListener("input", (event) => { state.reviewNote = event.target.value; });
  document.querySelector("#markSeizureBtn")?.addEventListener("click", () => markSelectedEvent("seizure_candidate"));
  document.querySelector("#markNormalBtn")?.addEventListener("click", () => markSelectedEvent("normal"));
  document.querySelector("#markNeedsReviewBtn")?.addEventListener("click", () => markSelectedEvent("needs_review"));
  document.querySelector("#undoReviewBtn")?.addEventListener("click", undoReview);
  document.querySelector("#redoReviewBtn")?.addEventListener("click", redoReview);
  document.querySelector("#resetReviewsBtn")?.addEventListener("click", resetReviews);
  document.querySelector("#downloadReviewJsonBtn")?.addEventListener("click", () => downloadReview("json"));
  document.querySelector("#downloadReviewCsvBtn")?.addEventListener("click", () => downloadReview("csv"));
  document.querySelector("#downloadEventsCsvBtn")?.addEventListener("click", () => downloadReview("events_csv"));
  document.querySelector("#runWaveformBtn")?.addEventListener("click", runWaveformPreview);
  document.querySelectorAll("[data-waveform-label]").forEach((button) => button.addEventListener("click", () => {
    state.activeWaveformLabel = button.dataset.waveformLabel;
    render();
    if (state.waveformEventId && selectedEvent() && !waveformWindowMatchesActiveView(state.waveformWindow) && !state.waveformInFlight) {
      runWaveformPreview();
    }
  }));
  document.querySelectorAll("[data-waveform-renderer]").forEach((button) => button.addEventListener("click", () => {
    state.waveformRenderer = button.dataset.waveformRenderer === "timechart" ? "timechart" : "svg";
    state.timechartMetrics = null;
    render();
  }));
  document.querySelectorAll("[data-waveform-mode]").forEach((button) => button.addEventListener("click", () => setWaveformMode(button.dataset.waveformMode)));
  document.querySelector("[data-waveform-gain]")?.addEventListener("change", (event) => setWaveformGain(event.target.value));
  document.querySelector("[data-waveform-reset]")?.addEventListener("click", resetWaveformToEvent);
  bindWaveformInteractions();
}

function editableKeyTarget(target) {
  return Boolean(target?.closest?.("input, textarea, select, [contenteditable='true']"));
}

function refocusWaveformFrame() {
  requestAnimationFrame(() => {
    document.querySelector("[data-waveform-interactive='true']")?.focus({ preventScroll: true });
  });
}

function bindWaveformInteractions() {
  const frame = document.querySelector("[data-waveform-interactive='true']");
  if (!frame) return;
  const selectionOverlay = frame.querySelector("[data-testid='epilepsy-waveform-selection']");
  const hideSelectionOverlay = () => {
    if (!selectionOverlay) return;
    selectionOverlay.hidden = true;
    selectionOverlay.style.left = "0";
    selectionOverlay.style.width = "0";
  };
  const updateSelectionOverlay = (startX, currentX, width) => {
    if (!selectionOverlay) return;
    const left = clamp(Math.min(startX, currentX), 0, width);
    const right = clamp(Math.max(startX, currentX), 0, width);
    selectionOverlay.hidden = false;
    selectionOverlay.style.left = `${left}px`;
    selectionOverlay.style.width = `${Math.max(1, right - left)}px`;
  };
  frame.addEventListener("wheel", (event) => {
    if (!selectedEvent()) return;
    event.preventDefault();
    frame.focus({ preventScroll: true });
    const viewport = currentWaveformViewport();
    if (event.ctrlKey || event.metaKey) {
      const rect = frame.getBoundingClientRect();
      const ratio = rect.width ? (event.clientX - rect.left) / rect.width : 0.5;
      zoomWaveformAtRatio(ratio, event.deltaY > 0 ? 1.2 : 0.82);
      return;
    }
    const dominantDelta = Math.abs(event.deltaX) > Math.abs(event.deltaY) ? event.deltaX : event.deltaY;
    const direction = dominantDelta > 0 ? 1 : -1;
    const stepRatio = event.shiftKey ? 0.5 : WAVEFORM_WHEEL_PAN_RATIO;
    panWaveformBy(direction * viewport.duration * stepRatio);
  }, { passive: false });
  frame.addEventListener("dblclick", (event) => {
    event.preventDefault();
    resetWaveformToEvent();
  });
  frame.addEventListener("pointerdown", (event) => {
    if (![0, 1].includes(event.button) || editableKeyTarget(event.target) || !selectedEvent()) return;
    event.preventDefault();
    frame.focus({ preventScroll: true });
    const viewport = currentWaveformViewport();
    const rect = frame.getBoundingClientRect();
    waveformDragState = {
      pointerId: event.pointerId,
      mode: event.button === 1 ? "pan" : "select",
      startX: event.clientX,
      startOffsetX: event.clientX - rect.left,
      startSec: viewport.start,
      durationSec: viewport.duration,
      width: Math.max(1, rect.width),
    };
    frame.classList.add("dragging", event.button === 1 ? "pan-dragging" : "select-dragging");
    hideSelectionOverlay();
    frame.setPointerCapture?.(event.pointerId);
  });
  frame.addEventListener("pointermove", (event) => {
    if (!waveformDragState || waveformDragState.pointerId !== event.pointerId) return;
    event.preventDefault();
    const deltaX = event.clientX - waveformDragState.startX;
    if (Math.abs(deltaX) > WAVEFORM_DRAG_THRESHOLD_PX) {
      frame.classList.add("drag-active");
      if (waveformDragState.mode === "select") {
        const currentOffsetX = waveformDragState.startOffsetX + deltaX;
        updateSelectionOverlay(waveformDragState.startOffsetX, currentOffsetX, waveformDragState.width);
      }
    }
  });
  const finishDrag = (event) => {
    if (!waveformDragState || waveformDragState.pointerId !== event.pointerId) return;
    event.preventDefault();
    const drag = waveformDragState;
    waveformDragState = null;
    frame.classList.remove("dragging", "drag-active", "select-dragging", "pan-dragging");
    frame.releasePointerCapture?.(event.pointerId);
    const deltaX = event.clientX - drag.startX;
    hideSelectionOverlay();
    if (Math.abs(deltaX) < WAVEFORM_DRAG_THRESHOLD_PX) return;
    if (drag.mode === "pan") {
      const deltaSec = -(deltaX / drag.width) * drag.durationSec;
      updateWaveformViewportAndSchedule(drag.startSec + deltaSec, drag.durationSec, "middle-drag-pan");
    } else {
      const endOffsetX = drag.startOffsetX + deltaX;
      zoomWaveformToRatioRange(drag.startOffsetX / drag.width, endOffsetX / drag.width);
    }
  };
  frame.addEventListener("pointerup", finishDrag);
  frame.addEventListener("pointercancel", (event) => {
    if (waveformDragState?.pointerId === event.pointerId) waveformDragState = null;
    frame.classList.remove("dragging", "drag-active", "select-dragging", "pan-dragging");
    hideSelectionOverlay();
  });
  frame.addEventListener("auxclick", (event) => {
    if (event.button === 1) event.preventDefault();
  });
  frame.addEventListener("keydown", (event) => {
    if (editableKeyTarget(event.target) || !selectedEvent()) return;
    const viewport = currentWaveformViewport();
    const key = event.key.toLowerCase();
    if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
      event.preventDefault();
      const direction = event.key === "ArrowRight" ? 1 : -1;
      panWaveformBy(direction * viewport.duration * (event.shiftKey ? 0.5 : WAVEFORM_ARROW_PAN_RATIO));
      refocusWaveformFrame();
    } else if (event.key === "PageUp" || event.key === "PageDown") {
      event.preventDefault();
      const direction = event.key === "PageDown" ? 1 : -1;
      panWaveformBy(direction * viewport.duration);
      refocusWaveformFrame();
    } else if (event.key === "+" || event.key === "=" || event.code === "NumpadAdd") {
      event.preventDefault();
      stepWaveformGain(1);
      refocusWaveformFrame();
    } else if (event.key === "-" || event.key === "_" || event.code === "NumpadSubtract") {
      event.preventDefault();
      stepWaveformGain(-1);
      refocusWaveformFrame();
    } else if (key === "r") {
      event.preventDefault();
      resetWaveformToEvent();
      refocusWaveformFrame();
    } else if (key === "f") {
      event.preventDefault();
      toggleWaveformFilter();
      refocusWaveformFrame();
    } else if (key === "e") {
      event.preventDefault();
      setWaveformMode(correctionModeActive() ? "browse" : "correct");
      refocusWaveformFrame();
    }
  });
}

async function loadFiles() {
  try {
    let files = await request("/eeg/files");
    state.files = Array.isArray(files) ? files : [];
    const existingFixture = findEpilepsyFixture(state.files);
    if (existingFixture) {
      state.demoFixture = {
        fixture_id: existingFixture.metadata_json?.fixture_id || "epilepsy_ml_demo_source_channels_v1",
        status: "ready",
        file: existingFixture,
      };
    } else {
      await ensureEpilepsyDemoFixture();
      files = await request("/eeg/files");
      state.files = Array.isArray(files) ? files : [];
    }
    state.files.sort((a, b) => fixtureRank(b) - fixtureRank(a));
    if (!state.selectedFileId && state.files.length) {
      const fixedFixtureId = state.demoFixture?.file?.id || "";
      const fixture = state.files.find((file) => file.id === fixedFixtureId) || findEpilepsyFixture(state.files) || state.files.find((file) => fixtureRank(file) > 0);
      state.selectedFileId = fixture?.id || state.files[0].id;
    }
    setMessage(`文件列表已加载：${state.files.length} 个文件，已预置癫痫实验室数据。`, false);
  } catch (error) {
    setMessage(`文件列表加载失败：${error.message || error}`, true);
  }
  render();
}

async function ensureEpilepsyDemoFixture() {
  try {
    state.demoFixture = await request("/lab/demo/epilepsy");
  } catch (error) {
    state.demoFixture = null;
    console.warn("Epilepsy demo fixture registration failed", error);
  }
}

function fixtureRank(file) {
  const name = String(file.original_filename || file.filename || file.label || file.id || "").toLowerCase();
  if (file.id === "eeg_demo_epilepsy_high_amplitude") return 4;
  if (name.includes("epilepsy_std_demo_high_amplitude")) return 3;
  if (name.includes("epilepsy") || name.includes("high_amplitude")) return 2;
  if (name.includes("demo") || name.includes("teaching")) return 1;
  return 0;
}

function findEpilepsyFixture(files) {
  return (files || []).find((file) =>
    file.id === "eeg_demo_epilepsy_high_amplitude"
    || file.metadata_json?.fixture_id === "epilepsy_ml_demo_source_channels_v1"
    || String(file.original_filename || file.filename || "").toLowerCase() === "epilepsy_ml_demo_source_channels.edf"
  );
}

function selectLatestEpilepsyFixture() {
  const fixedFixtureId = state.demoFixture?.file?.id || "eeg_demo_epilepsy_high_amplitude";
  const fixture = state.files.find((file) => file.id === fixedFixtureId) || findEpilepsyFixture(state.files) || state.files.find((file) => fixtureRank(file) >= 2);
  if (!fixture) {
    setMessage("没有找到癫痫实验室 EDF 数据，请刷新或上传 epilepsy_ml_demo_source_channels.edf。", true);
  } else {
    if (fixture.id !== state.selectedFileId) resetAnalysisOutputs();
    state.selectedFileId = fixture.id;
    setMessage(`已选中实验室数据：${fixture.original_filename || fixture.id}`, false);
  }
  render();
}

async function ensureProject() {
  if (state.project) return state.project;
  state.project = await request("/projects", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: "Epilepsy Workbench Demo",
      description: "癫痫样事件工作台实验室试用项目",
      research_type: "epilepsy_research_screening_lab",
      owner_id: "local-user",
      owner_user_id: "local-user",
      created_by: "local-user",
    }),
  });
  return state.project;
}

async function uploadFile(event) {
  event.preventDefault();
  const input = document.querySelector("#uploadInput");
  const file = input?.files?.[0];
  if (!file) {
    setMessage("请先选择 EEG 文件。", true);
    render();
    return;
  }
  state.uploadInFlight = true;
  setMessage("正在上传 EEG 文件……", false);
  render();
  try {
    const project = await ensureProject();
    const body = new FormData();
    body.append("file", file);
    const uploaded = await request(`/eeg/upload?project_id=${encodeURIComponent(project.id)}`, { method: "POST", body });
    resetAnalysisOutputs();
    state.selectedFileId = uploaded.id;
    state.files = [uploaded, ...state.files.filter((item) => item.id !== uploaded.id)];
    setMessage(`已上传并选中：${uploaded.original_filename || uploaded.id}`, false);
  } catch (error) {
    setMessage(`上传失败：${error.message || error}`, true);
  } finally {
    state.uploadInFlight = false;
    render();
  }
}

async function runEpilepsyTask() {
  readParametersFromForm();
  const file = selectedFile();
  if (!file) {
    setMessage("请先选择或上传 EEG 文件。", true);
    render();
    return;
  }
  resetAnalysisOutputs();
  state.runInFlight = true;
  const isMl = state.algorithmMode === "ml_epoch_classifier";
  setMessage(isMl ? "正在运行 ML 高保真癫痫样筛查，后端会校验源模型 hash 并写出 epoch/event/feature 产物……" : "正在运行癫痫样事件 STD 筛查，后端会读取 EEG 并写出 epoch/event 产物……", false);
  render();
  try {
    const payload = {
      project_id: file.project_id,
      module_name: isMl ? "epilepsy_ml" : "epilepsy",
      workflow_id: isMl ? "epilepsy_ml_xgboost" : "epilepsy_std_threshold",
      input_file_id: file.id,
      parameters_json: buildTaskParameters(),
      owner_user_id: "local-user",
      created_by: "local-user",
    };
    state.task = await request("/tasks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    state.artifacts = await request(`/tasks/${encodeURIComponent(state.task.id)}/artifacts`);
    await loadEpilepsyOutputs();
    loadReviews();
    state.selectedEventId = state.eventRows[0] ? String(state.eventRows[0].event_id) : "";
    if (state.selectedEventId) selectEvent(state.selectedEventId, false);
    setMessage(`工作台分析完成：${state.task.id}，候选事件 ${state.eventRows.length} 个。`, false);
  } catch (error) {
    setMessage(`运行失败：${error.message || error}`, true);
  } finally {
    state.runInFlight = false;
    render();
  }
}

async function loadTask(taskId) {
  if (!taskId) return;
  try {
    resetAnalysisOutputs();
    state.task = await request(`/tasks/${encodeURIComponent(taskId)}`);
    state.algorithmMode = state.task.module_name === "epilepsy_ml" || state.task.workflow_id === "epilepsy_ml_xgboost"
      ? "ml_epoch_classifier"
      : "std_threshold";
    state.selectedFileId = state.task.input_file_id || state.selectedFileId;
    state.artifacts = await request(`/tasks/${encodeURIComponent(taskId)}/artifacts`);
    await loadEpilepsyOutputs();
    loadReviews();
    await ensureReviewSession();
    state.selectedEventId = state.eventRows[0] ? String(state.eventRows[0].event_id) : "";
    if (state.selectedEventId) selectEvent(state.selectedEventId, false);
    setMessage(`已载入任务：${taskId}`, false);
  } catch (error) {
    setMessage(`任务载入失败：${error.message || error}`, true);
  }
}

async function loadEpilepsyOutputs() {
  const epochArtifact = artifactByLabel("epilepsy_epoch_scores");
  const eventsArtifact = artifactByLabel("epilepsy_events");
  const summaryArtifact = artifactByLabel("epilepsy_summary");
  state.sourceEpochRows = epochArtifact ? normalizeEpochRows(parseCsv(await fetch(artifactUrl(epochArtifact)).then((r) => r.text()))) : [];
  state.sourceEventRows = eventsArtifact ? parseCsv(await fetch(artifactUrl(eventsArtifact)).then((r) => r.text())) : [];
  state.epochRows = state.sourceEpochRows;
  state.eventRows = state.sourceEventRows;
  if (summaryArtifact) state.summary = await fetch(artifactUrl(summaryArtifact)).then((r) => r.json());
  state.epochWindowStart = 0;
  setEpochSelection(0, 0);
  applyEpochOverrides();
}

async function ensureReviewSession() {
  if (!state.task?.id || state.reviewSession?.task_id === state.task.id) return state.reviewSession;
  state.reviewSessionError = "";
  try {
    state.reviewSession = await request(`/tasks/${encodeURIComponent(state.task.id)}/epilepsy-review-sessions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        input_file_id: state.task.input_file_id,
        workflow_id: state.task.workflow_id,
        epoch_length_sec: epochLengthSec(),
        current_epoch: state.selectedEpoch,
        selected_range: { start: state.epochSelectionStart, end: state.epochSelectionEnd },
        ui_state: {
          visible_epoch_count: state.visibleEpochCount,
          epoch_window_start: state.epochWindowStart,
          algorithm_mode: state.algorithmMode,
        },
      }),
    });
    return state.reviewSession;
  } catch (error) {
    state.reviewSession = null;
    state.reviewSessionError = error.message || String(error);
    return null;
  }
}

async function syncReviewSession() {
  if (!state.reviewSession?.id) return;
  try {
    const eventReviews = Object.fromEntries(Object.entries(state.reviews || {}).map(([eventId, item]) => {
      const status = item.status === "seizure_candidate"
        ? "confirmed"
        : item.status === "normal"
          ? "rejected"
          : item.status === "needs_review"
            ? "needs_review"
            : "unreviewed";
      return [eventId, {
        event_id: eventId,
        status,
        note: item.note || "",
        reviewer: item.reviewer || "local-user",
        reviewed_at: item.reviewed_at || null,
      }];
    }));
    state.reviewSession = await request(`/epilepsy-review-sessions/${encodeURIComponent(state.reviewSession.id)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        status: "reviewing",
        current_epoch: state.selectedEpoch,
        selected_range: { start: state.epochSelectionStart, end: state.epochSelectionEnd },
        epoch_overrides: state.epochOverrides,
        event_reviews: eventReviews,
        actions: state.reviewActions.map((item) => ({
          type: item.action || item.type || "set_stage",
          target_range: item.range
            ? { start: Number(item.range.start || 0), end: Number(item.range.end || item.range.start || 0) }
            : { start: state.epochSelectionStart, end: state.epochSelectionEnd },
          after: item,
          note: item.note || "",
          source: item.source || "epilepsy-workbench",
        })),
        ui_state: {
          visible_epoch_count: state.visibleEpochCount,
          epoch_window_start: state.epochWindowStart,
          selected_event_id: state.selectedEventId,
          active_waveform_label: state.activeWaveformLabel,
        },
      }),
    });
    state.reviewSessionError = "";
  } catch (error) {
    state.reviewSessionError = error.message || String(error);
  }
}

function queueReviewSessionSync() {
  if (!state.task?.id) return;
  Promise.resolve()
    .then(() => ensureReviewSession())
    .then(() => syncReviewSession())
    .catch((error) => {
      state.reviewSessionError = error.message || String(error);
    });
}

function selectEpoch(epochIndex, extend = false) {
  if (extend) {
    state.epochSelectionEnd = clamp(epochIndex, 0, Math.max(0, state.epochRows.length - 1));
    state.selectedEpoch = state.epochSelectionEnd;
  } else {
    setEpochSelection(epochIndex, epochIndex);
  }
  ensureEpochVisible(state.selectedEpoch);
  const event = state.eventRows.find((item) => epochIndex >= Number(item.start_epoch) && epochIndex <= Number(item.end_epoch));
  if (event) selectEvent(String(event.event_id), false);
  render();
}

function selectEvent(eventId, rerender = true) {
  state.selectedEventId = String(eventId || "");
  const event = selectedEvent();
  if (event) {
    setEpochSelection(Number(event.start_epoch || 0), Number(event.end_epoch || event.start_epoch || 0));
    ensureEpochVisible(state.selectedEpoch);
    state.reviewNote = state.reviews[String(event.event_id)]?.note || "";
    if (String(state.waveformViewport?.lastEventId || "") !== String(event.event_id)) {
      fitWaveformToEvent(event);
      if (canRunWaveformPreview()) scheduleWaveformPreview("select-event");
    }
  }
  if (rerender) render();
}

function markSelectedEvent(status) {
  const event = selectedEvent();
  if (!event) return;
  if (status === "seizure_candidate" || status === "normal") {
    if (!correctionModeActive()) {
      setMessage("当前是浏览模式。请先进入 Correction mode，再修改 Stage_Code。", true);
      render();
      return;
    }
    setEpochSelection(Number(event.start_epoch || 0), Number(event.end_epoch || event.start_epoch || 0));
    applyStageToSelection(status === "seizure_candidate" ? 1 : 0, { event, status });
    return;
  }
  const id = String(event.event_id);
  const previous = snapshotReviewState();
  const next = {
    event_id: id,
    status,
    label: reviewLabel(status),
    note: state.reviewNote || "",
    reviewed_at: new Date().toISOString(),
    reviewer: "local-user",
    source: "epilepsy-workbench-local-review",
    event: {
      start_sec: numeric(event.start_sec),
      end_sec: numeric(event.end_sec),
      start_epoch: Number(event.start_epoch),
      end_epoch: Number(event.end_epoch),
    },
  };
  state.reviews[id] = next;
  state.reviewActions.push({
    action: "set_event_review",
    status,
    event_id: id,
    start_epoch: Number(event.start_epoch),
    end_epoch: Number(event.end_epoch),
    source: "source-ui-replica",
    created_at: new Date().toISOString(),
  });
  pushHistory(previous, snapshotReviewState(), "event_review");
  state.future = [];
  persistReviews();
  queueReviewSessionSync();
  render();
}

function snapshotReviewState() {
  return {
    reviews: JSON.parse(JSON.stringify(state.reviews || {})),
    epochOverrides: JSON.parse(JSON.stringify(state.epochOverrides || {})),
    reviewActions: JSON.parse(JSON.stringify(state.reviewActions || [])),
  };
}

function restoreReviewState(snapshot) {
  state.reviews = JSON.parse(JSON.stringify(snapshot?.reviews || {}));
  state.epochOverrides = JSON.parse(JSON.stringify(snapshot?.epochOverrides || {}));
  state.reviewActions = JSON.parse(JSON.stringify(snapshot?.reviewActions || []));
  applyEpochOverrides();
}

function pushHistory(previous, next, label) {
  state.history.push({ previous, next, label });
  state.future = [];
}

function applyStageToSelection(stageCode, context = {}) {
  if (!state.sourceEpochRows.length) return;
  if (!context.force && !correctionModeActive()) {
    setMessage("当前是浏览模式。Stage_Code 修改已被拦截；进入 Correction mode 后再执行 Seizure/Normal。", true);
    render();
    return;
  }
  const range = selectedEpochRange();
  const previous = snapshotReviewState();
  for (let index = range.start; index <= range.end; index += 1) {
    const source = state.sourceEpochRows.find((row, fallback) => epochIndexOf(row, fallback) === index);
    const sourceCode = source ? stageCodeOf(source) : 0;
    if (Number(stageCode) === sourceCode) delete state.epochOverrides[index];
    else state.epochOverrides[index] = Number(stageCode);
  }
  state.reviewActions.push({
    action: "set_stage",
    stage_code: Number(stageCode),
    stage: stageName(stageCode),
    start_epoch: range.start,
    end_epoch: range.end,
    start_epoch_1based: range.start + 1,
    end_epoch_1based: range.end + 1,
    event_id: context.event ? String(context.event.event_id) : "",
    source: "source-ui-replica",
    created_at: new Date().toISOString(),
  });
  if (context.event && context.status) {
    const event = context.event;
    const id = String(event.event_id);
    state.reviews[id] = {
      event_id: id,
      status: context.status,
      label: reviewLabel(context.status),
      note: state.reviewNote || "",
      reviewed_at: new Date().toISOString(),
      reviewer: "local-user",
      source: "epilepsy-workbench-stage-code-correction",
      event: {
        start_sec: numeric(event.start_sec),
        end_sec: numeric(event.end_sec),
        start_epoch: Number(event.start_epoch),
        end_epoch: Number(event.end_epoch),
      },
    };
  }
  applyEpochOverrides();
  pushHistory(previous, snapshotReviewState(), "epoch_stage");
  persistReviews();
  queueReviewSessionSync();
  setMessage(`已将 epoch ${range.start + 1}-${range.end + 1} 标为 ${stageName(stageCode)}，候选事件已按源规则重算。`, false);
  render();
}

function undoReview() {
  const item = state.history.pop();
  if (!item) return;
  state.future.push(item);
  restoreReviewState(item.previous);
  persistReviews();
  queueReviewSessionSync();
  render();
}

function redoReview() {
  const item = state.future.pop();
  if (!item) return;
  state.history.push(item);
  restoreReviewState(item.next);
  persistReviews();
  queueReviewSessionSync();
  render();
}

function resetReviews() {
  const previous = snapshotReviewState();
  state.reviews = {};
  state.epochOverrides = {};
  state.reviewActions.push({
    action: "reset",
    source: "source-ui-replica",
    created_at: new Date().toISOString(),
  });
  applyEpochOverrides();
  pushHistory(previous, snapshotReviewState(), "reset");
  persistReviews();
  queueReviewSessionSync();
  render();
}

function setVisibleEpochCount(value) {
  state.visibleEpochCount = value || "All";
  ensureEpochVisible(state.selectedEpoch);
  render();
}

function ensureEpochVisible(epochIndex) {
  if (state.visibleEpochCount === "All") {
    state.epochWindowStart = 0;
    return;
  }
  const count = Math.max(1, Number(state.visibleEpochCount) || state.epochRows.length || 1);
  const maxStart = Math.max(0, state.epochRows.length - count);
  if (epochIndex < state.epochWindowStart || epochIndex >= state.epochWindowStart + count) {
    state.epochWindowStart = clamp(Math.floor(epochIndex / count) * count, 0, maxStart);
  }
}

function gotoEpoch(epochIndex) {
  setEpochSelection(epochIndex, epochIndex);
  ensureEpochVisible(state.selectedEpoch);
  const event = state.eventRows.find((item) => state.selectedEpoch >= Number(item.start_epoch) && state.selectedEpoch <= Number(item.end_epoch));
  state.selectedEventId = event ? String(event.event_id) : "";
  render();
}

function navigateEpoch(action) {
  const total = state.epochRows.length;
  if (!total) return;
  const count = state.visibleEpochCount === "All" ? 1 : Math.max(1, Number(state.visibleEpochCount) || 1);
  if (action === "first") gotoEpoch(0);
  else if (action === "last") gotoEpoch(total - 1);
  else if (action === "previous") gotoEpoch(Math.max(0, state.selectedEpoch - count));
  else if (action === "next") gotoEpoch(Math.min(total - 1, state.selectedEpoch + count));
}

function updateEpochRangeFromInputs() {
  const start = Number(document.querySelector("#epochRangeStartInput")?.value || 1) - 1;
  const end = Number(document.querySelector("#epochRangeEndInput")?.value || start + 1) - 1;
  setEpochSelection(start, end);
  ensureEpochVisible(state.selectedEpoch);
  render();
}

async function runWaveformPreview() {
  const file = selectedFile();
  const event = selectedEvent();
  if (!file || !event) return;
  if (!state.task || state.task.input_file_id !== file.id) {
    resetWaveformPreview();
    setMessage("请先对当前数据文件运行筛查，再刷新候选波形。", true);
    render();
    return;
  }
  state.waveformInFlight = true;
  state.waveformTask = { status: "running" };
  state.waveformArtifacts = [];
  state.waveformEventId = String(event.event_id);
  state.waveformError = "";
  setMessage("正在读取当前候选事件 EDF 波形窗口……", false);
  render();
  try {
    const viewport = currentWaveformViewport(event, file);
    setWaveformViewport(viewport.start, viewport.duration, { eventId: event.event_id, invalidate: false });
    const query = new URLSearchParams({
      start_sec: String(viewport.start),
      duration_sec: String(viewport.duration),
      channels: waveformChannelsForRequest().join(","),
      max_points: "2400",
      filter_profile_id: waveformFilterProfileId(),
      include_events: "true",
    });
    state.waveformWindow = await request(`/eeg/files/${encodeURIComponent(file.id)}/waveform-window?${query.toString()}`);
    state.waveformTask = { status: "completed", mode: "waveform-window", id: `${file.id}:${event.event_id}:${state.waveformWindow.filter_profile_id}` };
    setMessage(`波形窗口已读取：${fmt(state.waveformWindow.start_sec, 2)}-${fmt(state.waveformWindow.stop_sec, 2)}s。`, false);
  } catch (error) {
    state.waveformTask = { status: "failed" };
    state.waveformError = error.message || String(error);
    setMessage(`波形预览失败：${error.message || error}`, true);
  } finally {
    state.waveformInFlight = false;
    render();
  }
}

function reviewPayload() {
  return {
    status: "reviewed_locally",
    task_id: state.task?.id || "",
    input_file_id: state.task?.input_file_id || state.selectedFileId || "",
    workflow_id: state.task?.workflow_id || (state.algorithmMode === "ml_epoch_classifier" ? "epilepsy_ml_xgboost" : "epilepsy_std_threshold"),
    non_medical_boundary: "Research screening/support only; no diagnosis, treatment, or clinical decision-making.",
    exported_at: new Date().toISOString(),
    review_count: Object.keys(state.reviews).length,
    corrected_epoch_count: Object.keys(state.epochOverrides).length,
    event_count_after_review: state.eventRows.length,
    source_event_count: state.sourceEventRows.length,
    epoch_length_sec: epochLengthSec(),
    source_contract: {
      stage_code_map: { 0: "Normal", 1: "Seizure" },
      min_consecutive_seizure_epochs_for_event: 2,
      shortcut_normal: "Shift+1",
      shortcut_seizure: "Shift+2",
    },
    reviews: Object.values(state.reviews),
    epoch_overrides: state.epochOverrides,
    review_actions: state.reviewActions,
    reviewed_events: state.eventRows,
    reviewed_epoch_scores: reviewedEpochRows(),
  };
}

function downloadReview(format) {
  const payload = reviewPayload();
  if (format === "csv") {
    saveBlob(csvFromObjects(reviewedEpochRows()), "reviewed_epoch_scores.csv", "text/csv;charset=utf-8");
  } else if (format === "events_csv") {
    saveBlob(csvFromObjects(state.eventRows), "reviewed_events.csv", "text/csv;charset=utf-8");
  } else {
    saveBlob(JSON.stringify(payload, null, 2), "review_session_manifest.json", "application/json;charset=utf-8");
  }
}

function reviewedEpochRows() {
  return state.epochRows.map((row, fallbackIndex) => {
    const index = epochIndexOf(row, fallbackIndex);
    return {
      epoch_index: index,
      source_epoch_1based: index + 1,
      start_sec: numeric(row.start_sec),
      end_sec: numeric(row.end_sec),
      source_Stage_Code: row.source_Stage_Code ?? stageCodeOf(state.sourceEpochRows[fallbackIndex] || row),
      source_Stage: row.source_Stage ?? stageName(stageCodeOf(state.sourceEpochRows[fallbackIndex] || row)),
      Stage_Code: stageCodeOf(row),
      Stage: stageName(stageCodeOf(row)),
      manually_corrected: state.epochOverrides[index] !== undefined,
      probability: row.probability ?? "",
      mean_rms: row.mean_rms ?? "",
      is_event_epoch: boolValue(row.is_event_epoch),
    };
  });
}

function csvFromObjects(rows) {
  if (!rows.length) return "";
  const headers = Array.from(rows.reduce((set, row) => {
    Object.keys(row).forEach((key) => set.add(key));
    return set;
  }, new Set()));
  return [
    headers,
    ...rows.map((row) => headers.map((header) => row[header] ?? "")),
  ].map((row) => row.map(csvEscape).join(",")).join("\n");
}

function csvEscape(value) {
  const raw = String(value ?? "");
  return /[",\n\r]/.test(raw) ? `"${raw.replaceAll('"', '""')}"` : raw;
}

function saveBlob(text, filename, type) {
  const blob = new Blob([text], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

document.addEventListener("keydown", (event) => {
  if (editableKeyTarget(event.target)) return;
  if (!event.shiftKey) return;
  if (event.key === "2" || event.code === "Digit2") {
    event.preventDefault();
    if (!correctionModeActive()) {
      setMessage("浏览模式下 Shift+2 不会修改 Stage_Code；按 E 或点击 Correction mode 后再执行。", true);
      render();
      return;
    }
    applyStageToSelection(1);
  }
  if (event.key === "1" || event.code === "Digit1") {
    event.preventDefault();
    if (!correctionModeActive()) {
      setMessage("浏览模式下 Shift+1 不会修改 Stage_Code；按 E 或点击 Correction mode 后再执行。", true);
      render();
      return;
    }
    applyStageToSelection(0);
  }
});

async function main() {
  render();
  if (START_TASK_ID) {
    setMessage(`正在载入任务：${START_TASK_ID}……`, false);
    render();
    await Promise.all([loadFiles(), loadTask(START_TASK_ID)]);
    render();
    return;
  }
  await loadFiles();
}

main();
