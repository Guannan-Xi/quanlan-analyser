(() => {
const qs = (selector) => document.querySelector(selector);
const qsa = (selector) => [...document.querySelectorAll(selector)];
const money = (value) => `\u00a5${Number(value).toFixed(2)}`;
const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
  "&": "&amp;",
  "<": "&lt;",
  ">": "&gt;",
  '"': "&quot;",
  "'": "&#39;",
}[char]));
const maskEmail = (value) => {
  const email = String(value || "");
  const [name, domain] = email.split("@");
  if (!name || !domain) return email || "-";
  const head = name.slice(0, Math.min(2, name.length));
  return `${head}${"*".repeat(Math.max(2, name.length - head.length))}@${domain}`;
};
const AUTH_KEY = "qlanalyser_auth_session";
const CUSTOMER_KEY = "qlanalyser_customer_profile";
const ENTRY_PAGE = "expert-entry-demo.html";
const DEFAULT_API_BASE = ["localhost", "127.0.0.1"].includes(window.location.hostname)
  ? "http://127.0.0.1:8001/api"
  : "/api";
const isLocalHost = () => ["localhost", "127.0.0.1"].includes(window.location.hostname);
function initialApiBase() {
  const requested = new URLSearchParams(window.location.search).get("api");
  if (!requested) return DEFAULT_API_BASE;
  try {
    const parsed = new URL(requested, window.location.href);
    const allowedLocal = isLocalHost() && ["localhost", "127.0.0.1"].includes(parsed.hostname);
    const allowedSameOrigin = parsed.origin === window.location.origin && parsed.pathname.startsWith("/api");
    if (allowedLocal || allowedSameOrigin) return requested;
  } catch {}
  return DEFAULT_API_BASE;
}
const isE2EAutomationContext = () => {
  if (isLocalHost()) return true;
  const params = new URLSearchParams(window.location.search);
  const marker = `${params.get("v") || ""} ${params.get("acceptance") || ""} ${params.get("e2e") || ""}`.toLowerCase();
  return /(^|[^a-z0-9])(e2e[a-z0-9-]*|acceptance|aliyun-epilepsy-v0-1|epilepsy-upload-to-export|deeplink)([^a-z0-9]|$)/.test(marker);
};
const initialDeepLinkHash = (() => {
  try { return decodeURIComponent(String(window.location.hash || "").replace(/^#/, "")); }
  catch { return String(window.location.hash || "").replace(/^#/, ""); }
})();
function currentHashViewName() {
  try { return decodeURIComponent(String(window.location.hash || "").replace(/^#/, "")); }
  catch { return String(window.location.hash || "").replace(/^#/, ""); }
}
function isEpilepsyWorkbenchDeepLinkIntent() {
  const params = new URLSearchParams(window.location.search);
  const workbench = String(params.get("workbench") || params.get("module") || "").toLowerCase();
  const target = currentHashViewName() || initialDeepLinkHash;
  return target === "epilepsyWorkbenchInline" || workbench === "epilepsy" || workbench === "epilepsy_ml";
}

const demoCustomer = {
  name: "\u5ba2\u6237\u8d26\u6237",
  email: "demo.customer@quanlan.cn",
  org: "Quanlan Neuro Lab",
  password: "demo123456",
  registeredAt: "2026-06-20",
};

const state = {
  balance: 0,
  wallet: null,
  activeTemplate: "ERP \u4e8b\u4ef6\u76f8\u5173\u7535\u4f4d",
  segmentMode: "time",
  role: null,
  tasks: [],
  apiBase: initialApiBase(),
  real: {
    project: null,
    eegFile: null,
    plan: null,
    tasks: {},
    artifacts: {},
    report: null,
    epochSet: null,
    latestTaskModule: null,
    resultsViewed: false,
  },
  workspace: {
    projects: [],
    files: [],
    plans: [],
    epochSets: [],
    selectedProjectId: null,
    selectedFileId: null,
    selectedPlanId: null,
    projectSearch: "",
    showReviewProjects: false,
    sessionProjectIds: new Set(),
  },
  teaching: {
    active: false,
    loading: false,
    guideActive: false,
    stepIndex: 0,
    datasetLoaded: false,
    lockedUntilStep: 0,
    demoProjectId: "proj_demo_learning",
    demoFileId: "eeg_demo_teaching_oddball",
  },
  deepLink: {
    initialHash: initialDeepLinkHash,
    epilepsyBootstrapInFlight: false,
    epilepsyBootstrapStatus: "idle",
    epilepsyBootstrapError: "",
  },
  epilepsyInline: {
    selectedEventId: "",
    timeScaleSec: 30,
    reader: {
      startSec: 0,
      durationSec: 30,
      sensitivityUvPerRow: 50,
      visibleChannelCount: 8,
      overlayVisibility: {
        candidates: true,
        stageCode: true,
        reviewEdits: true,
      },
      middlePan: null,
    },
    resultTaskId: "",
    epochRows: [],
    eventRows: [],
    resultLoadStatus: "idle",
    resultLoadError: "",
    spectrogramPayload: null,
    spectrogramLoadStatus: "idle",
    spectrogramLoadError: "",
    screeningStatus: "idle",
    screeningProgress: 0,
    screeningMessage: "",
    waveformStatus: "idle",
    waveformFetchStatus: "idle",
    waveformError: "",
    waveformPayload: null,
    waveformRequestKey: "",
    waveformPayloadKey: "",
    waveformActiveRequestKey: "",
    waveformAbortController: null,
    waveformDebounceTimer: null,
    waveformCache: new Map(),
    reviewSession: null,
    reviewSaveStatus: "idle",
    reviewSaveError: "",
    exportResult: null,
    exportStatus: "idle",
    exportError: "",
    draftCommands: [],
    redoCommands: [],
    draftSaved: false,
    published: false,
  },
};

function publishE2EState() {
  const activeView = qs(".view.active")?.id || "";
  document.body.dataset.activeView = activeView;
  document.body.dataset.currentRole = state.role || "logged-out";
  document.body.dataset.teachingGuide = state.teaching.guideActive ? "active" : "inactive";
  document.body.dataset.analysisReady = isAnalysisReady() ? "true" : "false";
  document.body.dataset.hasProject = state.real.project?.id ? "true" : "false";
  document.body.dataset.hasFile = state.real.eegFile?.id ? "true" : "false";
  window.__QLANALYSER_ROUTE_STATE__ = {
    role: state.role || null,
    activeView,
    requestedView: document.body.dataset.requestedView || activeView,
    teachingActive: Boolean(state.teaching.active),
    teachingGuideActive: Boolean(state.teaching.guideActive),
  };
  if (!isE2EAutomationContext()) return;
  window.__QLANALYSER_E2E_STATE__ = state;
}

function refreshLabLinks() {
  qsa("[data-lab-link]").forEach((link) => {
    const baseHref = link.dataset.labBaseHref || link.getAttribute("href");
    if (!baseHref) return;
    link.dataset.labBaseHref = baseHref;
    const url = new URL(baseHref, window.location.href);
    if (state.apiBase) url.searchParams.set("api", state.apiBase);
    link.href = url.toString();
  });
}

const EDF_BROWSER_INTERACTION_CONSTANTS = Object.freeze({
  wheelPanRatio: 0.08,
  arrowPanRatio: 0.10,
  pagePanRatio: 1.00,
  zoomFactor: 1.20,
  minWindowSec: 2,
  maxWindowSec: 300,
  gainStepRatio: 1.20,
  minSensitivityUvPerRow: 5,
  maxSensitivityUvPerRow: 500,
});
const INLINE_EPILEPSY_WAVEFORM_CACHE_LIMIT = 16;
const INLINE_EPILEPSY_WAVEFORM_FETCH_DEBOUNCE_MS = 120;
const authenticatedArtifactImageUrls = new Map();

function clearAuthenticatedArtifactObjectUrls() {
  authenticatedArtifactImageUrls.forEach((url) => URL.revokeObjectURL(url));
  authenticatedArtifactImageUrls.clear();
}

const DATA_PREPARATION_CONTRACT_VERSION = "qlanalyser-data-preparation-v0.2";

const eegState = {
  data: null,
  filteredData: null,
  events: [],
  sourceName: "",
  taskId: "",
  autoloaded: false,
  uploaded: false,
      selectedFilePreviewId: "",
      autoPreviewInFlight: false,
      autoPreviewError: "",
      overviewPayload: null,
      overviewLoading: false,
      start: 0,
      windowSec: 10,
  gain: 2,
  sensitivityUvPerRow: 50,
  visibleChannels: 8,
  interactionMode: "browse",
  middlePan: null,
  hoverTimeSec: null,
  hoverChannelName: "",
  showFiltered: false,
  filterEnabled: false,
  filterLfreq: 1,
  filterHfreq: 40,
  filterNotchEnabled: true,
  filterNotch: 50,
  lastPreviewParameters: null,
  previewRequestSeq: 0,
  drag: null,
  selectedSegment: null,
  lastPlot: null,
};

function clearEegPreviewState() {
  eegState.data = null;
  eegState.filteredData = null;
  eegState.events = [];
  eegState.sourceName = "";
  eegState.taskId = "";
  eegState.selectedFilePreviewId = "";
  eegState.autoPreviewError = "";
  eegState.showFiltered = false;
  eegState.filterEnabled = false;
  eegState.lastPreviewParameters = null;
  eegState.interactionMode = "browse";
  eegState.middlePan = null;
  eegState.hoverTimeSec = null;
  eegState.hoverChannelName = "";
  eegState.selectedSegment = null;
  const canvas = qs("#eegCanvas");
  const ctx = canvas?.getContext?.("2d");
  if (canvas && ctx) ctx.clearRect(0, 0, canvas.width, canvas.height);
  const meta = qs("#eegMeta");
  if (meta) meta.innerHTML = "";
  const events = qs("#eegEvents");
  if (events) events.innerHTML = "";
  const strip = qs("#previewStrip");
  if (strip) strip.innerHTML = "";
  qsa("#segmentStart, #segmentEnd").forEach((input) => {
    delete input.dataset.manualSegmentEdited;
  });
}

const prepEditState = {
  excludedSegments: [],
  restoredSegments: [],
  labels: [],
  restoredLabels: [],
  badChannels: [],
  restoredBadChannels: [],
  badChannelHistory: [],
};

function recordBadChannelHistory(action, change, extra = {}) {
  const item = {
    id: `bad_channel_history_${Date.now()}_${prepEditState.badChannelHistory.length + 1}`,
    action,
    file_id: change?.file_id || currentWorkspaceFile()?.id || "",
    channel: String(change?.channel || ""),
    previous_status: change?.previous_status || "",
    new_status: change?.new_status || "",
    reason: change?.reason || "",
    status: change?.status || "draft",
    timestamp: new Date().toISOString(),
    ...extra,
  };
  prepEditState.badChannelHistory.push(item);
  return item;
}

const teachingSteps = [
  {
    view: "dashboard",
    selector: "#teachingModeBtn",
    title: "示例模式 1/6：项目",
    body: "先建立项目，并载入一份练习用 EEG 数据。",
    require: () => state.teaching.datasetLoaded,
    blocked: "练习数据正在载入，请稍候。",
  },
  {
    view: "storage",
    selector: '[data-testid="selected-file-summary"]',
    title: "示例模式 2/6：数据",
    body: "确认当前项目里的 EEG 文件。自己的数据也会从这里上传或选择。",
    require: () => Boolean(state.real.project?.id && state.real.eegFile?.id),
    blocked: "请等待练习项目和样本数据载入完成。",
  },
  {
    view: "analysis",
    selector: '[data-testid="single-file-preview-panel"]',
    title: "示例模式 3/6：准备",
    body: "预览波形、质量信息、坏道和参考设置；确认后再进入分析。",
    require: () => Boolean(state.real.eegFile?.id),
    blocked: "请先选择示例 EEG 数据。",
    onEnter: () => requestAutoQcPreviewForSelectedFile(state.real.eegFile).catch(() => null),
  },
  {
    view: "workflow",
    selector: '[data-testid="analysis-method-scope-panel"]',
    title: "示例模式 4/6：分析",
    body: "选择当前数据真正可以运行的方法。推荐先从 PSD 开始。",
    require: () => Boolean(state.real.eegFile?.id),
    blocked: "请先完成示例数据载入。",
  },
  {
    view: "statistics",
    selector: '[data-testid="result-review-workbench"]',
    title: "示例模式 5/6：结果",
    body: "查看图表、表格、参数和边界说明，确认结果可复核。",
    require: () => Boolean(state.real.eegFile?.id),
    blocked: "请先完成示例数据载入。",
  },
  {
    view: "publication",
    selector: '[data-testid="report-delivery-workbench"]',
    title: "示例模式 6/6：报告",
    body: "查看结果后再生成复核记录，下载图表、表格和复现记录。",
    require: () => Boolean(state.real.eegFile?.id),
    blocked: "请先完成示例数据载入。",
  },
];

const templates = [
  { name: "Raw browsing and segmentation", desc: "MNE Raw.plot, continuous segments, 标签s, and bad-span review", icon: "scan-line", image: "./assets/analysis-raw-segment.png" },
  { name: "PSD spectrum", desc: "MNE Spectrum.plot, Welch PSD, alpha peak, and band-power review", icon: "bar-chart-3", image: "./assets/analysis-psd.png" },
  { name: "ERP / evoked", desc: "MNE Evoked, target-standard comparison, and ERP workflow", icon: "waves", image: "./assets/analysis-erp.png" },
  { name: "ICA review", desc: "MNE ICA components, runica / ICLabel style review flow", icon: "sliders-horizontal", image: "./assets/analysis-ica.png" },
  { name: "Time-frequency", desc: "MNE TFR, Morlet wavelets, ERSP / ITC workflow", icon: "audio-waveform", image: "./assets/analysis-timefreq.png" },
  { name: "Topography", desc: "MNE topomap and EEGLAB topoplot-style presentation", icon: "scan-eye", image: "./assets/analysis-source.png" },
  { name: "Machine learning", desc: "MNE epoch features plus sklearn classification and cross-validation", icon: "git-branch", image: "./assets/analysis-ml.png" },
];

const paradigms = [
  ["Visual oddball P300", "ERP", "适合新手"],
  ["Auditory oddball MMN", "ERP", "适合新手"],
  ["Stroop conflict", "ERP / theta", "常用"],
  ["Go / No-Go inhibition", "N2 / P3", "常用"],
  ["Flanker task", "ERN / theta", "常用"],
  ["Semantic N400", "ERP", "常用"],
  ["Face N170", "ERP", "常用"],
  ["Visual search N2pc", "Lateralized ERP", "进阶"],
  ["Motor imagery L/R", "ERD / ML", "进阶"],
  ["Motor execution MRP", "Readiness potential", "常用"],
  ["SSVEP tagging", "Frequency response", "常用"],
  ["ASSR 40 Hz", "Time-frequency", "常用"],
  ["Rest eyes open/closed", "PSD", "适合新手"],
  ["Meditation alpha theta", "Bandpower", "常用"],
  ["Sleep spindle K-complex", "Sleep EEG", "进阶"],
  ["Somatosensory SEP", "ERP", "常用"],
  ["Error monitoring ERN", "ERP", "进阶"],
  ["Reward positivity", "ERP", "进阶"],
  ["Working memory CDA", "Lateralized ERP", "进阶"],
  ["Attention cue CNV", "Slow potential", "进阶"],
];

const titles = {
  dashboard: "第 1 步：创建或打开项目",
  journey: "交付质检",
  analysis: "检查 EEG 数据",
  workflow: "选择分析方法",
  epilepsyWorkbenchInline: "癫痫样候选事件复核预览",
  paradigms: "\u8303\u5f0f\u5e93",
  statistics: "查看分析结果",
  publication: "生成和下载复核记录",
  upload: "\u6570\u636e\u6587\u4ef6",
  storage: "上传或选择 EEG 数据",
  billing: "服务记录",
  invoice: "\u53d1\u7968\u7533\u8bf7",
  inbox: "\u53d1\u7968\u7bb1",
  userCenter: "\u4e2a\u4eba\u4e2d\u5fc3",
  adminDashboard: "后台总览",
  adminOperations: "任务队列",
  adminFinance: "结算记录",
  adminSystem: "\u7cfb\u7edf\u72b6\u6001",
};

const recommendations = {
  p300: {
    title: "ERP / P300 analysis",
    body: "If the data includes target and standard labels, the system will show a target-standard waveform and the 280-420 ms mean amplitude. The result is for research workflow only, not medical advice.",
    params: "Epoch -0.2 to 0.8 s; baseline -0.2 to 0 s; channels Pz/P3/P4; single-record ERP descriptors only; research-use descriptive output.",
  },
  n400: {
    title: "ERP / N400 analysis",
    body: "Congruent and incongruent conditions usually differ around 300-500 ms, which can be used for event-locked ERP analysis.",
    params: "Epoch -0.2 to 0.8 s; midline channels; 300-500 ms mean amplitude; within-subject paired model.",
  },
  stroop: {
    title: "Conflict ERP + theta",
    body: "Stroop tasks are well suited for N2/P3 ERP plus frontal midline theta. The two outputs can serve as the main and supplementary analyses.",
    params: "ERP: N2/P3 windows; theta: frontal midline; report both as research outputs only.",
  },
  motor: {
    title: "Motor imagery / motor execution",
    body: "Motor imagery and motor execution are well matched to mu/beta suppression and readiness-potential style analysis.",
    params: "Epoch around cue/onset; sensorimotor channels; ERD/ERS and readiness potential features.",
  },
};
const journeyDetails = [
  {
    title: "第 1 步：创建项目",
    body: "先为这次分析建立一个项目名称。",
    action: "创建项目后，再选择或上传项目内数据。",
    view: "dashboard",
  },
  {
    title: "第 2 步：选择数据",
    body: "把 EDF、SET 或 FIF 数据放入当前项目，或选择已有文件。",
    action: "系统会读取文件信息，并保存到当前项目下。",
    view: "storage",
  },
  {
    title: "第 3 步：准备数据",
    body: "检查波形、通道信息和数据质量，并确认准备方案。",
    action: "准备确认后，再进入分析方法选择。",
    view: "analysis",
  },
  {
    title: "第 4 步：运行分析",
    body: "数据准备确认后，再选择实际要运行的分析方法。",
    action: "推荐先运行 PSD；不满足条件的方法保持锁定。",
    view: "workflow",
  },
  {
    title: "第 5 步：查看结果",
    body: "分析完成后，查看图表、表格、参数和质量提示。",
    action: "确认结果后，再进入报告页整理交付材料。",
    view: "statistics",
  },
  {
    title: "第 6 步：生成复核记录",
    body: "下载结果材料，用于复核、共享或归档。",
    action: "图表、表格和复现记录会一起保存在下载材料中。",
    view: "publication",
  },
];

const modalContent = {
  knowledge: {
    title: "\u77e5\u8bc6\u5e93",
    body: `
      <p>\u8fd9\u91cc\u4f1a\u89e3\u91ca EEG \u5de5\u4f5c\u6d41\u4e2d\u7684\u5e38\u89c1\u6982\u5ff5\uff0c\u5305\u62ec\u4e8b\u4ef6\u9501\u5b9a\u5206\u6790\u3001\u8fde\u7eed\u7247\u6bb5\u9009\u62e9\u3001\u6bcf\u4f4d\u88ab\u8bd5\u6307\u6807\u3001QC\u3001\u5bfc\u51fa\u548c\u53ef\u590d\u73b0\u8bb0\u5f55\u3002</p>
      <div class="modal-actions">
        <button class="ghost-btn" data-modal-view="workflow"><i data-lucide="route"></i><span>\u6253\u5f00\u5de5\u4f5c\u6d41\u7a0b\u6307\u5f15</span></button>
      </div>
    `,
  },
  audit: {
    title: "\u64cd\u4f5c\u8bb0\u5f55",
    body: `
      <div class="audit-list">
        <span>09:00 \u521b\u5efa\u4e86\u5ba2\u6237\u8d26\u6237\u5e76\u542f\u52a8\u4e86\u9879\u76ee\u3002</span>
        <span>09:03 \u670d\u52a1\u72b6\u6001\u5df2\u8bb0\u5f55\uff0c\u7ebf\u4e0b\u786e\u8ba4\u540e\u66f4\u65b0\u3002</span>
        <span>09:05 EEG \u6587\u4ef6\u548c\u4e8b\u4ef6\u8868\u5df2\u751f\u6210\u5e76\u9a8c\u8bc1\u3002</span>
        <span>09:08 ERP/P300 \u5df2\u88ab\u63a8\u8350\uff0c\u65b9\u6cd5\u53c2\u6570\u5df2\u4fdd\u5b58\u3002</span>
        <span>09:16 \u56fe\u8868\u3001\u8868\u683c\u548c\u65b9\u6cd5\u6587\u6848\u5df2\u5bfc\u51fa\u5f85\u5ba1\u67e5\u3002</span>
        <span>09:20 \u7ed3\u679c\u5305\u5df2\u5b8c\u6210\uff0c\u5df2\u961f\u5217\u7b49\u5f85\u7528\u6237\u901a\u77e5\u3002</span>
      </div>
    `,
  },
  uploadHelp: {
    title: "\u4e0a\u4f20\u5e2e\u52a9",
    body: `
      <div class="audit-list">
        <span>大文件会分段上传，请保持页面打开。</span>
        <span>网络中断后，可以回到同一个项目继续处理。</span>
        <span>如果事件表缺失，请先上传原始 EEG 数据，再补充或生成事件信息。</span>
        <span>也可以先使用示例样本熟悉流程，再切换到自己的项目数据。</span>
      </div>
    `,
  },
  loginHelp: {
    title: "\u8d26\u53f7\u5e2e\u52a9\u4e0e\u627e\u56de",
    body: `
      <div class="audit-list">
        <span>\u5df2\u6709\u8d26\u53f7\uff1a\u4f7f\u7528\u6ce8\u518c\u90ae\u7bb1\u6216\u624b\u673a\u53f7\u767b\u5f55\u3002</span>
        <span>\u5fd8\u8bb0\u5bc6\u7801\uff1a\u8054\u7cfb\u9879\u76ee\u7ba1\u7406\u5458\u6216\u8fd0\u8425\u4eba\u5458\u91cd\u7f6e\u3002</span>
        <span>\u8bd5\u7528\u56e2\u961f\uff1a\u5148\u521b\u5efa\u8d26\u53f7\uff0c\u518d\u8d70\u4e00\u904d\u793a\u4f8b\u6d41\u7a0b\u3002</span>
        <span>\u65b9\u6cd5\u5e93\uff1a\u7528\u4e8e\u67e5\u770b\u9002\u7528\u6761\u4ef6\u3001\u8f93\u5165\u8f93\u51fa\u548c\u590d\u6838\u8fb9\u754c\u3002</span>
      </div>
    `,
  },
  account: {
    title: "\u8d26\u6237\u4fe1\u606f",
    body: () => {
      const customer = getStoredCustomer();
      return `
        <div class="audit-list">
          <span><b>\u8d26\u53f7\u663e\u793a\uff1a</b>${escapeHtml(customer.name || "\u5ba2\u6237\u8d26\u53f7")}</span>
          <span><b>\u90ae\u7bb1\uff1a</b>${escapeHtml(customer.email || "\u672a\u7ed1\u5b9a\u90ae\u7bb1")}</span>
          <span><b>\u673a\u6784\uff1a</b>${escapeHtml(customer.org || "Quanlan Neuro Lab")}</span>
          <span><b>服务记录：</b>试用服务状态由运营线下确认</span>
          <span><b>\u8d26\u53f7\u6743\u9650\uff1a</b>\u9879\u76ee\u67e5\u770b\u4e0e\u5206\u6790\u64cd\u4f5c</span>
        </div>
      `;
    },
  },
  security: {
    title: "\u5b89\u5168\u8bbe\u7f6e",
    body: `
      <div class="audit-list">
        <span>\u6d4b\u8bd5\u8d26\u53f7\u662f\u672c\u5730\u5ba1\u9605\u7528\u6237\uff0c\u53ea\u8bbf\u95ee\u6f14\u793a\u73af\u5883\u3002</span>
        <span>\u5bc6\u7801\u53ef\u8f6c\u6362\u4e14\u53ef\u91cd\u7f6e\uff0c\u4e0d\u5305\u542b\u4efb\u4f55\u751f\u4ea7\u79d8\u94a5\u3002</span>
        <span>\u6743\u9650\u8303\u56f4\uff1a\u53ea\u6709\u9879\u76ee\u67e5\u770b\u3001\u6570\u636e\u5904\u7406\u548c\u62a5\u544a\u9a8c\u8bc1\u3002</span>
        <span>\u5efa\u8bae\uff1a\u5982\u9700\u66f4\u65b0\u767b\u5f55\u65b9\u5f0f\uff0c\u4ece\u9879\u76ee\u7ba1\u7406\u5458\u5904\u7406\u3002</span>
      </div>
    `,
  },
  usage: {
    title: "\u4f7f\u7528\u8bb0\u5f55",
    body: () => {
      const project = state.real.project;
      const file = state.real.eegFile;
      const projectName = project ? (projectDisplayName(project) || project.name || project.id) : "\u5c1a\u672a\u9009\u62e9\u9879\u76ee";
      const fileName = file ? (eegFileDisplayName(file) || file.id) : "\u5c1a\u672a\u9009\u62e9\u6570\u636e";
      return `
        <div class="audit-list">
          <span><b>\u5f53\u524d\u9879\u76ee\uff1a</b>${escapeHtml(projectName)}</span>
          <span><b>\u5f53\u524d\u6570\u636e\uff1a</b>${escapeHtml(fileName)}</span>
          <span><b>\u8fd1\u671f\u52a8\u4f5c\uff1a</b>\u767b\u5f55 / \u9009\u9879\u76ee / \u5ba1\u6838 / \u5904\u7406\u3002</span>
          <span><b>\u5efa\u8bae\uff1a</b>\u5b8c\u6210\u6570\u636e\u51c6\u5907\u540e\u518d\u8fdb\u5165\u5206\u6790\u4efb\u52a1\u3002</span>
        </div>
      `;
    },
  },
};
function setRealStatus(message, kind = "info") {
  const target = qs("#realRuntimeStatus");
  if (!target) return;
  target.classList.remove("status-error", "status-ok");
  if (kind === "error") target.classList.add("status-error");
  if (kind === "ok") target.classList.add("status-ok");
  target.textContent = cleanRuntimeMessage(message);
}

const uiActionAudit = [];

function recordUiAction(action, verdict, message, extra = {}) {
  const safeMessage = cleanRuntimeMessage(message, action);
  const item = {
    action,
    verdict,
    message: safeMessage,
    at: new Date().toISOString(),
    view: qs(".view.active")?.id || "",
    ...extra,
  };
  uiActionAudit.push(item);
  window.qlanalyserUiActionAudit = uiActionAudit;
  const target = qs("#segmentSummary");
  if (target && action && action.startsWith("ia:")) {
    target.textContent = safeMessage;
  }
  setRealStatus(safeMessage, verdict === "blocked" || verdict === "error" ? "error" : verdict === "pass" ? "ok" : "info");
  return item;
}

function renderPreparationEditSummary(message = "") {
  const target = qs("#segmentSummary");
  if (!target) return;
  const excluded = prepEditState.excludedSegments.length;
  const restored = prepEditState.restoredSegments.length;
  const labels = prepEditState.labels.length;
  const restoredLabels = prepEditState.restoredLabels.length;
  const badChannels = prepEditState.badChannels.length;
  const restoredBadChannels = prepEditState.restoredBadChannels.length;
  const badHistory = prepEditState.badChannelHistory.length;
  const parts = [
    `已剔除片段 ${excluded} 个`,
    `已恢复片段 ${restored} 个`,
    `标签 ${labels} 条`,
    `标签恢复 ${restoredLabels} 条`,
    `坏道修改 ${badChannels} 条`,
    `坏道恢复 ${restoredBadChannels} 条`,
    `坏道历史 ${badHistory} 条`,
  ];
  target.innerHTML = `<strong>${escapeHtml(message || "当前修改可继续调整，保存前不会破坏原始数据。")}</strong><span>${escapeHtml(parts.join(" · "))}</span>`;
  renderWaveformWorkbenchStatus(message);
}


function formatWaveformHms(seconds = 0) {
  const total = Math.max(0, Math.floor(Number(seconds || 0)));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const secs = total % 60;
  return [hours, minutes, secs].map((part) => String(part).padStart(2, "0")).join(":");
}

function waveformModeLabel(mode = eegState.interactionMode) {
  const labels = {
    browse: "浏览模式",
    selectSegment: "选段模式",
    markBadSegment: "坏段模式",
    markBadChannel: "坏道模式",
  };
  return labels[mode] || labels.browse;
}

function isWaveformWriteMode(mode = eegState.interactionMode) {
  return mode === "selectSegment" || mode === "markBadSegment" || mode === "markBadChannel";
}

function preparationPlanStatusLabel() {
  const plan = state.real.plan;
  if (hasConfirmedPlan()) return `准备方案：已确认 r${Number(plan.revision)}`;
  if (plan?.id && !plan.is_default) return "准备方案：草稿未确认";
  return "准备方案：未确认";
}

function waveformDisplaySampleRate() {
  const payload = currentWaveformPayload();
  const value = Number(payload?.display_sample_rate_hz || payload?.sample_rate_hz || payload?.sfreq_display || 0);
  return Number.isFinite(value) && value > 0 ? value : 200;
}

function waveformAnchorDriftToleranceSec() {
  return Math.max(0.05, 2 / Math.max(1, waveformDisplaySampleRate()));
}

function waveformSensitivityUvPerRow() {
  const payload = currentWaveformPayload();
  const baseUv = Number(payload?.scale_uv || 100);
  const gain = Math.max(0.1, Number(eegState.gain || 2));
  const sensitivity = clampNumber(baseUv / gain, EDF_BROWSER_INTERACTION_CONSTANTS.minSensitivityUvPerRow, EDF_BROWSER_INTERACTION_CONSTANTS.maxSensitivityUvPerRow);
  eegState.sensitivityUvPerRow = sensitivity;
  return sensitivity;
}

function syncWaveformModeUi() {
  const mode = eegState.interactionMode || "browse";
  qsa("[data-mode-target]").forEach((button) => {
    const active = button.dataset.modeTarget === mode;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", active ? "true" : "false");
  });
  qsa('[data-testid="preview-edit-workbench"]').forEach((node) => {
    node.dataset.mode = mode;
  });
  const canvas = qs("#eegCanvas");
  if (canvas) {
    canvas.dataset.mode = mode;
    canvas.classList.toggle("waveform-write-mode", isWaveformWriteMode(mode));
    canvas.classList.toggle("waveform-browse-mode", mode === "browse");
  }
}

function setWaveformInteractionMode(mode = "browse", options = {}) {
  const allowed = new Set(["browse", "selectSegment", "markBadSegment", "markBadChannel"]);
  eegState.interactionMode = allowed.has(mode) ? mode : "browse";
  eegState.drag = null;
  eegState.middlePan = null;
  syncWaveformModeUi();
  if (!options.silent) {
    const hint = isWaveformWriteMode()
      ? `${waveformModeLabel()}：只写入准备草稿，不修改原始 EEG。`
      : "浏览模式：滚轮水平浏览，Ctrl/Cmd + 滚轮缩放时间窗。";
    renderWaveformInteractionHint(hint);
  }
  renderWaveformWorkbenchStatus();
}

function renderWaveformWorkbenchStatus(message = "") {
  const target = qs("#waveformWorkbenchStatus");
  if (!target) return;
  const selected = normalizeSegmentRange(eegState.selectedSegment?.start_sec, eegState.selectedSegment?.end_sec);
  const start = Number(eegState.start || 0);
  const windowSec = Number(eegState.windowSec || 10);
  const referenceSelect = qs("#presetPrepReference");
  const referenceLabel = referenceSelect?.selectedOptions?.[0]?.textContent?.trim() || "平均参考";
  const filterState = Boolean(eegState.filterEnabled || eegState.showFiltered) ? "Filter" : "Raw";
  const sensitivity = waveformSensitivityUvPerRow();
  const mode = eegState.interactionMode || "browse";
  const writeHint = isWaveformWriteMode(mode) ? "只写入准备草稿，不修改原始 EEG。" : "默认浏览不会写入选段、坏段或坏道。";
  const pieces = [
    ["模式", waveformModeLabel(mode)],
    ["时间窗", `${formatWaveformHms(start)}-${formatWaveformHms(start + windowSec)}`],
    ["窗口", `${Number(windowSec.toFixed(1))} s/page`],
    ["通道", `${Number(eegState.visibleChannels || 8)} ch`],
    ["灵敏度", `${Number(sensitivity.toFixed(1))} uV/row`],
    ["显示", filterState],
    ["准备", preparationPlanStatusLabel()],
    ["选段", selected ? `${selected.start_sec.toFixed(2)}-${selected.end_sec.toFixed(2)} s` : "未选择"],
    ["参考", referenceLabel],
    ["坏道草稿", `${prepEditState.badChannels.length} 条，可恢复 ${prepEditState.restoredBadChannels.length} 条`],
    ["片段草稿", `剔除 ${prepEditState.excludedSegments.length} 段，恢复 ${prepEditState.restoredSegments.length} 段`],
  ];
  target.classList.toggle("is-write-mode", isWaveformWriteMode(mode));
  target.innerHTML = [
    message ? `<strong>${escapeHtml(cleanRuntimeMessage(message))}</strong>` : "",
    ...pieces.map(([label, value]) => `<span><b>${escapeHtml(label)}</b>${escapeHtml(value)}</span>`),
    `<em>${escapeHtml(writeHint)}</em>`,
  ].filter(Boolean).join("");
  syncWaveformModeUi();
}

function hasConfirmedPlan() {
  const plan = state.real.plan;
  return Boolean(plan && !plan.is_default && plan.status === "confirmed" && plan.id && Number.isFinite(Number(plan.revision)));
}

function dataPreparationContractVersion(plan) {
  return plan?.schema_version
    || plan?.data_preparation_contract_version
    || plan?.contract_version
    || DATA_PREPARATION_CONTRACT_VERSION;
}

function isAnalysisReady(plan = state.real.plan) {
  return Boolean(
    plan
      && !plan.is_default
      && plan.status === "confirmed"
      && plan.id
      && Number.isFinite(Number(plan.revision))
      && dataPreparationContractVersion(plan) === DATA_PREPARATION_CONTRACT_VERSION
  );
}

function latestAnalysisTask() {
  const latestKey = state.real.latestTaskModule;
  if (latestKey && state.real.tasks[latestKey]) return state.real.tasks[latestKey];
  return state.real.tasks.connectivity
    || state.real.tasks.pac
    || state.real.tasks.reference_csd
    || state.real.tasks.multitaper_tfr
    || state.real.tasks.multitaper_psd
    || state.real.tasks.tfr
    || state.real.tasks.erp
    || state.real.tasks.psd
    || null;
}

function latestAnalysisTaskModule() {
  const latestKey = state.real.latestTaskModule;
  if (latestKey && state.real.tasks[latestKey]) return latestKey;
  return [
    "connectivity",
    "pac",
    "reference_csd",
    "multitaper_tfr",
    "multitaper_psd",
    "tfr",
    "erp",
    "psd",
  ].find((moduleName) => state.real.tasks?.[moduleName]) || "";
}

function isCompletedAnalysisTask(task) {
  const status = String(task?.status || "").toLowerCase();
  const queueStatus = String(task?.queue_status || task?.queueStatus || "").toLowerCase();
  return Boolean(task?.id && status === "completed" && (!queueStatus || queueStatus === "completed"));
}

function currentTaskArtifacts(moduleName, task) {
  if (moduleName && Array.isArray(state.real.artifacts?.[moduleName])) return state.real.artifacts[moduleName];
  if (!task?.id) return [];
  return Object.values(state.real.artifacts || {})
    .flat()
    .filter((artifact) => (artifact?.task_id || artifact?.taskId) === task.id);
}

function hasDownloadableResultArtifact(artifacts = []) {
  return artifactDetailItems(artifacts).length > 0;
}

function reportReleaseGateSnapshot() {
  const moduleName = latestAnalysisTaskModule();
  const task = moduleName ? state.real.tasks[moduleName] : latestAnalysisTask();
  const completed = isCompletedAnalysisTask(task);
  const reviewed = Boolean(task?.id && state.real.resultsViewed);
  const artifacts = currentTaskArtifacts(moduleName, task);
  const hasArtifacts = hasDownloadableResultArtifact(artifacts);
  let reason = "可以基于已完成且有结果文件的分析任务生成复核记录。";
  if (!task?.id) reason = "请先完成一个分析任务，再生成复核记录。";
  else if (!completed) reason = "当前分析任务尚未完成，不能生成复核记录。";
  else if (!reviewed) reason = "请先查看分析结果，再生成复核记录。";
  else if (!hasArtifacts) reason = "缺少可下载结果文件，不能生成复核记录；请刷新结果或重新运行分析。";
  return {
    ready: Boolean(task?.id && completed && reviewed && hasArtifacts),
    task,
    moduleName,
    artifacts,
    completed,
    reviewed,
    hasArtifacts,
    reason,
  };
}

async function ensureReportReleaseReady() {
  let gate = reportReleaseGateSnapshot();
  if (!gate.task?.id) throw new Error("请先完成至少一个分析任务，再生成复核记录。");
  if (!gate.completed) throw new Error("当前分析任务尚未完成，不能生成复核记录。");
  if (!gate.reviewed) throw new Error("请先查看分析结果，再生成复核记录。");
  if (!gate.hasArtifacts) {
    const artifacts = await fetchTaskArtifacts(gate.task.id);
    if (gate.moduleName) state.real.artifacts[gate.moduleName] = artifacts;
    gate = reportReleaseGateSnapshot();
  }
  if (!gate.hasArtifacts) {
    throw new Error("缺少可下载结果文件，不能生成复核记录；请刷新结果或重新运行分析。");
  }
  return gate;
}

function currentWorkspaceFile() {
  const selectedId = qs("#workspaceFileFocusSelect")?.value || qs("#workspaceFileSelect")?.value || state.workspace.selectedFileId;
  const selected = activeWorkspaceFiles(state.workspace.files || []).find((item) => item.id === selectedId);
  const file = state.real.eegFile && !isDeletedEegFile(state.real.eegFile) ? state.real.eegFile : selected || null;
  if (file?.id) {
    state.real.eegFile = file;
    state.workspace.selectedFileId = file.id;
  } else {
    state.real.eegFile = null;
    state.workspace.selectedFileId = null;
  }
  return file;
}

function currentWorkspaceProject() {
  const selectedId = state.workspace.selectedProjectId;
  const selected = (state.workspace.projects || []).find((item) => item.id === selectedId);
  const project = state.real.project && !isArchivedProject(state.real.project) ? state.real.project : selected || null;
  if (project?.id) {
    state.real.project = project;
    state.workspace.selectedProjectId = project.id;
  }
  return project;
}

async function chooseWorkspaceProject(projectId) {
  const nextProjectId = projectId || null;
  if (nextProjectId && nextProjectId === state.workspace.selectedProjectId && state.real.project?.id === nextProjectId) {
    renderProjectDataManagement();
    return;
  }
  state.workspace.selectedProjectId = nextProjectId;
  state.workspace.selectedFileId = null;
  state.workspace.selectedPlanId = null;
  clearEegPreviewState();
  if (!nextProjectId) {
    state.real.project = null;
    state.real.eegFile = null;
    state.real.plan = null;
    state.real.epochSet = null;
    await refreshProjectWorkspace();
    return;
  }
  const project = (state.workspace.projects || []).find((item) => item.id === nextProjectId) || null;
  state.real.project = project;
  if (project?.id) state.workspace.sessionProjectIds?.add?.(project.id);
  state.real.eegFile = null;
  state.real.plan = null;
  state.real.epochSet = null;
  await refreshProjectWorkspace();
}

async function chooseWorkspaceFile(fileId, options = {}) {
  const { jumpToAnalysis = false, autoPreview = true } = options;
  state.workspace.selectedFileId = fileId || null;
  state.workspace.selectedPlanId = null;
  if (!fileId) {
    state.real.eegFile = null;
    state.real.plan = null;
    state.real.epochSet = null;
    clearEegPreviewState();
    await refreshProjectWorkspace();
    return;
  }
  const file = activeWorkspaceFiles(state.workspace.files || []).find((item) => item.id === fileId) || null;
  state.real.eegFile = file;
  state.real.plan = null;
  state.real.epochSet = null;
  clearEegPreviewState();
  await refreshProjectWorkspace();
  if (jumpToAnalysis) {
    setView("analysis");
    revealWaveformPreview({ delayMs: 350 });
  }
  if (autoPreview && file?.id) {
    requestAutoQcPreviewForSelectedFile(file).catch((error) => {
      eegState.autoPreviewError = error.message || String(error);
      renderEegPreviewEmptyState();
      showToast(`自动预览未完成：${eegState.autoPreviewError}`);
    });
  }
}

function ensureTeachingOverlay() {
  let overlay = qs("#teachingOverlay");
  if (overlay) return overlay;
  overlay = document.createElement("div");
  overlay.id = "teachingOverlay";
  overlay.className = "teaching-overlay";
  overlay.setAttribute("role", "dialog");
  overlay.setAttribute("aria-modal", "false");
  overlay.setAttribute("aria-live", "polite");
  overlay.innerHTML = `
    <div class="teaching-mask" data-teaching-action="next"></div>
    <div class="teaching-spotlight" aria-hidden="true"></div>
    <section class="teaching-card" data-testid="teaching-step-card">
      <div class="teaching-card-head">
        <span class="teaching-kicker">示例数据</span>
        <button class="icon-btn" type="button" data-teaching-action="close" title="结束引导"><i data-lucide="x"></i></button>
      </div>
      <h2 id="teachingStepTitle">示例模式</h2>
      <p id="teachingStepBody">正在准备示例引导。</p>
      <div class="teaching-progress" aria-hidden="true"><span></span></div>
      <div class="teaching-actions">
        <button class="ghost-btn" type="button" data-teaching-action="prev"><i data-lucide="chevron-left"></i><span>上一步</span></button>
        <button class="primary-btn" type="button" data-teaching-action="next"><span>下一步</span><i data-lucide="chevron-right"></i></button>
        <button class="ghost-btn" type="button" data-teaching-action="close"><i data-lucide="x"></i><span>结束引导</span></button>
      </div>
      <small class="teaching-boundary">示例数据为合成 EEG，仅用于熟悉流程，不作为科学结论。</small>
    </section>
  `;
  document.body.append(overlay);
  if (window.lucide) window.lucide.createIcons();
  return overlay;
}

function clearTeachingTarget() {
  qsa(".teaching-target").forEach((node) => node.classList.remove("teaching-target"));
}

function setTeachingOverlayPosition(target, overlay) {
  const spotlight = overlay.querySelector(".teaching-spotlight");
  const card = overlay.querySelector(".teaching-card");
  const rect = target?.getBoundingClientRect?.();
  if (!rect || rect.width < 1 || rect.height < 1) {
    spotlight.hidden = true;
    card.style.left = "";
    card.style.right = "24px";
    card.style.top = "96px";
    return;
  }
  const pad = 8;
  spotlight.hidden = false;
  spotlight.style.left = `${Math.max(12, rect.left - pad)}px`;
  spotlight.style.top = `${Math.max(12, rect.top - pad)}px`;
  spotlight.style.width = `${Math.min(window.innerWidth - 24, rect.width + pad * 2)}px`;
  spotlight.style.height = `${Math.min(window.innerHeight - 24, rect.height + pad * 2)}px`;

  const cardWidth = Math.min(420, window.innerWidth - 32);
  card.style.width = `${cardWidth}px`;
  const leftCandidate = rect.right + 18;
  const fitsRight = leftCandidate + cardWidth < window.innerWidth - 16;
  const left = fitsRight ? leftCandidate : Math.max(16, Math.min(window.innerWidth - cardWidth - 16, rect.left));
  const cardHeight = Math.min(card.offsetHeight || 280, Math.max(180, window.innerHeight - 32));
  const belowTop = rect.bottom + 14;
  const aboveTop = rect.top - cardHeight - 14;
  const preferredTop = belowTop + cardHeight <= window.innerHeight - 16 ? belowTop : aboveTop;
  const top = Math.max(16, Math.min(window.innerHeight - cardHeight - 16, preferredTop));
  card.style.left = `${left}px`;
  card.style.right = "auto";
  card.style.top = `${top}px`;
}

function renderTeachingOverlay() {
  if (!state.teaching.active || !state.teaching.guideActive) return;
  const overlay = ensureTeachingOverlay();
  const step = teachingSteps[state.teaching.stepIndex] || teachingSteps[0];
  if (step.view && qs(".view.active")?.id !== step.view) setView(step.view);
  clearTeachingTarget();
  const target = qs(step.selector) || qs(".main") || document.body;
  target.classList.add("teaching-target");
  const title = overlay.querySelector("#teachingStepTitle");
  const body = overlay.querySelector("#teachingStepBody");
  const progress = overlay.querySelector(".teaching-progress span");
  const previous = overlay.querySelector('[data-teaching-action="prev"]');
  const next = overlay.querySelector('[data-teaching-action="next"].primary-btn');
  if (title) title.textContent = step.title;
  if (body) body.textContent = step.body;
  if (progress) progress.style.width = `${((state.teaching.stepIndex + 1) / teachingSteps.length) * 100}%`;
  if (previous) previous.disabled = state.teaching.stepIndex === 0;
  if (next) next.querySelector("span").textContent = state.teaching.stepIndex === teachingSteps.length - 1 ? "完成" : "下一步";
  overlay.classList.add("active");
  document.body.classList.add("teaching-mode-active");
  step.onEnter?.();
  window.requestAnimationFrame(() => setTeachingOverlayPosition(target, overlay));
}


function applyTeachingModeChrome() {
  document.body.classList.toggle("teaching-sandbox-active", Boolean(state.teaching.active));
  const button = qs("#teachingModeBtn");
  if (button) {
    const loading = Boolean(state.teaching.loading);
    button.dataset.teachingAction = state.teaching.active ? "exit" : "start";
    button.classList.toggle("active", Boolean(state.teaching.active));
    button.classList.toggle("is-loading", loading);
    button.disabled = loading;
    button.setAttribute("aria-pressed", state.teaching.active ? "true" : "false");
    button.setAttribute("aria-busy", loading ? "true" : "false");
    const label = button.querySelector("span");
    if (label) label.textContent = loading ? "载入示例数据" : state.teaching.active ? "\u8fd4\u56de\u666e\u901a\u6a21\u5f0f" : "\u793a\u4f8b\u6a21\u5f0f";
    button.title = state.teaching.active ? "\u9000\u51fa\u6559\u5b66\u6c99\u76d2\uff0c\u8fd4\u56de\u4f60\u7684\u6b63\u5f0f\u9879\u76ee" : "\u4f7f\u7528\u5185\u7f6e\u8111\u7535\u6570\u636e\u4f53\u9a8c\u5b8c\u6574\u6d41\u7a0b";
  }
  let banner = qs("#teachingSandboxBanner");
  if (state.teaching.active) {
    if (!banner) {
      banner = document.createElement("div");
      banner.id = "teachingSandboxBanner";
      banner.className = "teaching-sandbox-banner";
      const topbar = qs(".topbar");
      topbar?.insertAdjacentElement("afterend", banner);
    }
    banner.innerHTML = `<strong>\u793a\u4f8b\u6a21\u5f0f</strong><span>\u4f60\u6b63\u5728\u4f7f\u7528\u5185\u7f6e\u8111\u7535\u6570\u636e\u8bd5\u8dd1\u6d41\u7a0b\uff0c\u65e0\u9700\u4e0a\u4f20\u6570\u636e\uff1b\u793a\u4f8b\u6570\u636e\u4e0d\u53ef\u5220\u9664\uff0c\u7ed3\u679c\u4ec5\u7528\u4e8e\u5b66\u4e60\u64cd\u4f5c\u3002</span><button class="ghost-btn mini" type="button" data-teaching-action="guide"><i data-lucide="route"></i><span>\u91cd\u65b0\u6253\u5f00\u5f15\u5bfc</span></button>`;
    banner.hidden = false;
  } else if (banner) {
    banner.hidden = true;
  }
  if (window.lucide) window.lucide.createIcons();
}

function applyTeachingDataset(dataset, options = {}) {
  const project = dataset?.project || null;
  const file = dataset?.file || null;
  const plan = dataset?.data_preparation_plan || dataset?.plan || null;
  if (project?.id) {
    state.real.project = project;
    state.workspace.selectedProjectId = project.id;
    if (!state.workspace.projects.some((item) => item.id === project.id)) state.workspace.projects.unshift(project);
  }
  if (file?.id) {
    state.real.eegFile = { ...file, teaching_demo: true };
    state.workspace.selectedFileId = file.id;
    eegState.selectedFilePreviewId = "";
    if (!state.workspace.files.some((item) => item.id === file.id)) state.workspace.files.unshift(state.real.eegFile);
  }
  if (plan?.id) {
    state.real.plan = { ...plan, schema_version: dataPreparationContractVersion(plan) };
    state.workspace.selectedPlanId = plan.id;
    if (!state.workspace.plans.some((item) => item.id === plan.id)) state.workspace.plans.unshift(state.real.plan);
  } else if (options.clearPlan !== false) {
    state.real.plan = null;
    state.workspace.selectedPlanId = "";
  }
  state.teaching.datasetLoaded = Boolean(project?.id && file?.id);
  return { project, file, plan };
}

function preserveTeachingWorkspaceSelection() {
  if (!state.teaching.active) return;
  const project = state.real.project;
  const file = state.real.eegFile;
  const plan = state.real.plan;
  if (project?.id && isTeachingDemoProject(project) && !state.workspace.projects.some((item) => item.id === project.id)) {
    state.workspace.projects.unshift(project);
  }
  if (file?.id && isTeachingDemoFile(file) && !state.workspace.files.some((item) => item.id === file.id)) {
    state.workspace.files.unshift(file);
  }
  if (plan?.id && !state.workspace.plans.some((item) => item.id === plan.id)) {
    state.workspace.plans.unshift(plan);
  }
  if (project?.id && isTeachingDemoProject(project)) state.workspace.selectedProjectId = project.id;
  if (file?.id && isTeachingDemoFile(file)) state.workspace.selectedFileId = file.id;
  if (plan?.id) state.workspace.selectedPlanId = plan.id;
}

async function loadTeachingDatasetForModule(moduleName = "") {
  const endpoint = moduleName === "epilepsy_ml" ? "/lab/demo/epilepsy" : "/lab/demo/dataset";
  const dataset = await apiJson(endpoint);
  const applied = applyTeachingDataset(dataset);
  await refreshProjectWorkspace();
  state.real.project = state.workspace.projects.find((item) => item.id === applied.project?.id) || applied.project || state.real.project;
  state.real.eegFile = state.workspace.files.find((item) => item.id === applied.file?.id) || state.real.eegFile || applied.file;
  state.real.plan = state.workspace.plans.find((item) => item.id === applied.plan?.id) || state.real.plan || applied.plan || null;
  state.workspace.selectedProjectId = state.real.project?.id || state.workspace.selectedProjectId;
  state.workspace.selectedFileId = state.real.eegFile?.id || state.workspace.selectedFileId;
  if (state.real.plan?.id) state.workspace.selectedPlanId = state.real.plan.id;
  return { ...dataset, project: state.real.project, file: state.real.eegFile, plan: state.real.plan };
}

async function startTeachingMode(options = {}) {
  if (state.teaching.loading) return;
  const { showGuide = true } = options;
  const quickStartTarget = options.quickStart ? (options.targetView || "analysis") : "";
  const intendedModuleName = options.moduleName || options.module || (isEpilepsyWorkbenchDeepLinkIntent() ? "epilepsy_ml" : "");
  const isEpilepsyIntent = intendedModuleName === "epilepsy_ml";
  const viewAtStart = qs(".view.active")?.id || "";
  state.teaching.loading = true;
  state.teaching.active = true;
  state.teaching.guideActive = Boolean(showGuide && !isEpilepsyIntent);
  state.teaching.stepIndex = 0;
  state.teaching.datasetLoaded = false;
  ensureTeachingOverlay();
  applyTeachingModeChrome();
  setRealStatus(isEpilepsyIntent ? "正在载入癫痫样事件示例 EDF 数据。" : "正在载入示例数据。", "info");
  try {
    await loadTeachingDatasetForModule(intendedModuleName);
    const currentView = qs(".view.active")?.id || "";
    const userMovedToAnotherView = Boolean(currentView && viewAtStart && currentView !== viewAtStart);
    if (currentView === "epilepsyWorkbenchInline" || isEpilepsyIntent) {
      state.teaching.guideActive = false;
      if (isEpilepsyIntent) setView("epilepsyWorkbenchInline");
      await ensureTeachingSandboxReady({ preview: false, moduleName: "epilepsy_ml" });
    } else {
      if (quickStartTarget) {
        setView(quickStartTarget);
      } else if (!userMovedToAnotherView && !options.preserveView) {
        // FIX: 如果用户从数据准备页进入，返回数据准备页以触发波形预览
        const returnView = (viewAtStart === "analysis") ? "analysis" : "dashboard";
        setView(returnView);
      }
      await ensureTeachingSandboxReady({ preview: false });
    }
    recordUiAction("teaching:start", "pass", "示例模式已载入合成 EEG 数据。", {
      project_id: state.real.project?.id,
      file_id: state.real.eegFile?.id,
      demo: true,
    });
  } catch (error) {
    state.teaching.datasetLoaded = false;
    recordUiAction("teaching:start", "blocked", `示例数据载入失败：${error.message || error}`);
  }
  state.teaching.loading = false;
  applyTeachingModeChrome();
  // FIX: 如果用户从数据准备页进入教学模式，不要弹引导覆盖层（引导会强制切到 dashboard），
  // 而是直接留在 analysis 页并触发波形预览
  if (viewAtStart === "analysis" && state.teaching.guideActive && !isEpilepsyIntent) {
    state.teaching.guideActive = false;
    hideTeachingGuideOverlay();
    setView("analysis");
    // 触发波形自动预览（setView 内部会调用，这里双重保障）
    const file = currentWorkspaceFile();
    if (file?.id) requestAutoQcPreviewForSelectedFile(file).catch(() => null);
  } else if (state.teaching.guideActive) {
    renderTeachingOverlay();
  } else {
    hideTeachingGuideOverlay();
  }
  publishE2EState();
}

function hideTeachingGuideOverlay() {
  const overlay = qs("#teachingOverlay");
  overlay?.classList.remove("active");
  overlay?.setAttribute("hidden", "");
  document.body.classList.remove("teaching-mode-active");
  clearTeachingTarget();
}

function finishTeachingGuide() {
  state.teaching.guideActive = false;
  hideTeachingGuideOverlay();
  applyTeachingModeChrome();
  setView("analysis");
  ensureTeachingSandboxReady({ preview: true }).catch((error) => {
    recordUiAction("teaching:auto-ready", "blocked", error?.message || String(error));
  });
  recordUiAction("teaching:guide-finished", "pass", "\u6559\u5b66\u5f15\u5bfc\u5df2\u5b8c\u6210\uff0c\u7ee7\u7eed\u505c\u7559\u5728\u6559\u5b66\u6a21\u5f0f\uff0c\u53ef\u7528\u5185\u7f6e\u6570\u636e\u8bd5\u8dd1\u5b8c\u6574\u6d41\u7a0b\u3002", {
    project_id: state.real.project?.id,
    file_id: state.real.eegFile?.id,
    sandbox: true,
  });
  showToast("\u6559\u5b66\u5f15\u5bfc\u5df2\u5b8c\u6210\u3002\u4f60\u4ecd\u5728\u6559\u5b66\u6a21\u5f0f\uff0c\u53ef\u76f4\u63a5\u7528\u5185\u7f6e\u6570\u636e\u8bd5\u8dd1\u5206\u6790\u3002");
}

function closeTeachingMode() {
  const wasTeachingDemo = isTeachingDemoProject(state.real.project) || isTeachingDemoFile(state.real.eegFile);
  state.teaching.active = false;
  state.teaching.guideActive = false;
  state.teaching.datasetLoaded = false;
  const overlay = qs("#teachingOverlay");
  hideTeachingGuideOverlay();
  if (wasTeachingDemo) {
    state.real.project = null;
    state.real.eegFile = null;
    state.real.plan = null;
    state.real.epochSet = null;
    state.workspace.selectedProjectId = null;
    state.workspace.selectedFileId = null;
    state.workspace.selectedPlanId = null;
    clearEegPreviewState();
    refreshProjectWorkspace().catch(() => renderProjectDataManagement());
  }
  recordUiAction("teaching:close", "pass", "示例模式已结束。");
}

function goTeachingStep(delta) {
  if (!state.teaching.active) return;
  const current = teachingSteps[state.teaching.stepIndex];
  if (delta > 0 && current?.require && !current.require()) {
    const message = current.blocked || "请先完成当前步骤，再继续。";
    recordUiAction("teaching:step-blocked", "blocked", message, { step: state.teaching.stepIndex + 1 });
    showToast(message);
    renderTeachingOverlay();
    return;
  }
  const nextIndex = state.teaching.stepIndex + delta;
  if (nextIndex >= teachingSteps.length) {
    finishTeachingGuide();
    return;
  }
  state.teaching.stepIndex = Math.max(0, Math.min(teachingSteps.length - 1, nextIndex));
  renderTeachingOverlay();
}

async function chooseWorkspacePlan(planId) {
  state.workspace.selectedPlanId = planId || null;
  if (!planId) {
    state.real.plan = null;
    await refreshProjectWorkspace();
    return;
  }
  const plan = (state.workspace.plans || []).find((item) => item.id === planId) || null;
  state.real.plan = plan;
  await refreshProjectWorkspace();
}

function eegFileDisplayName(item) {
  if (!item) return "";
  const label = String(item.metadata_json?.label || item.label || "").trim();
  const normalized = label.toLowerCase();
  const isInternalReviewLabel = /^(acceptance|persistent|fixture|demo|test)[-_ ]?label/.test(normalized)
    || normalized.includes("审核备注");
  if (label && !isInternalReviewLabel) return label;
  return item.original_filename || item.source_name || item.id || "EEG 数据文件";
}

function projectDisplayName(project) {
  if (!project) return "";
  const rawName = String(project.name || project.title || "").trim();
  const normalized = rawName.toLowerCase();
  if (!rawName) return project.id || "\u672a\u547d\u540d\u9879\u76ee";
  if (normalized.includes("persistence gate")) return "\u6301\u4e45\u5316\u9a8c\u8bc1\u9879\u76ee";
  if (normalized.includes("acceptance project")) return "\u529f\u80fd\u9a8c\u6536\u9879\u76ee";
  if (normalized.includes("crud persistence")) return "\u9879\u76ee\u7ba1\u7406\u9a8c\u8bc1\u9879\u76ee";
  if (normalized.includes("v01 smoke")) return "V01 \u6d41\u7a0b\u9a8c\u8bc1\u9879\u76ee";
  return rawName;
}

function projectSearchText(project) {
  return [
    project?.id,
    project?.name,
    project?.title,
    project?.description,
    project?.research_type,
    project?.owner_id,
    project?.owner_user_id,
    project?.created_by,
    project?.source,
    project?.metadata_json?.source,
    project?.metadata_json?.owner_id,
    projectDisplayName(project),
  ].filter(Boolean).join(" ").toLowerCase();
}

function isAutoGeneratedPilotProject(project) {
  const text = projectSearchText(project);
  const rawName = String(project?.name || project?.title || "").trim();
  const owner = String(project?.owner_id || project?.owner_user_id || project?.created_by || project?.metadata_json?.owner_id || "").toLowerCase();
  if (owner === "pilot-user" || owner === "pilot_user" || owner === "demo-user") return true;
  if (rawName === "我的研究项目") return true;
  if (text.includes("qlanalyser pilot project")) return true;
  if (text.includes("pilot generated") || text.includes("pilot-generated")) return true;
  if (text.includes("我的分析项目") && (owner.includes("pilot") || text.includes("pilot"))) return true;
  return false;
}

function isReviewOrInternalProject(project) {
  const text = projectSearchText(project);
  return [
    "acceptance",
    "cloud trial",
    "mismatch",
    "persistence",
    "smoke",
    "fixture",
    "demo",
    "teaching",
    "grouped methods",
    "grouped-methods",
    "grouped_methods",
    "e2e",
    "qc preview",
    "browser qc",
    "qc lab",
    "qc_lab",
    "parameter exposure review",
    "analysis_lab",
    "analysis lab",
    "local edf",
    "pilot 真实分析项目",
    "v01 科研验证项目",
    "科研验证项目",
    "test",
    "gate",
    "review",
    "validator",
    "dev",
  ].some((marker) => text.includes(marker));
}

function isHiddenFromCustomerProjectList(project) {
  if (isTeachingDemoProject(project)) return !state.teaching.active;
  return isArchivedProject(project) || isReviewOrInternalProject(project) || isAutoGeneratedPilotProject(project);
}

function projectVisibilityReason(project) {
  if (isTeachingDemoProject(project) && !state.teaching.active) return "教学样例";
  if (isArchivedProject(project)) return "已归档";
  if (isAutoGeneratedPilotProject(project)) return "自动生成记录";
  if (isReviewOrInternalProject(project)) return "内部/验收记录";
  return "客户项目";
}

function hiddenProjectCount(projects = state.workspace.projects || []) {
  return (projects || []).filter((item) => isHiddenFromCustomerProjectList(item)).length;
}

function updateProjectVisibilityToggleLabel(projects = state.workspace.projects || []) {
  const span = qs('label[for="workspaceShowReviewProjects"] span');
  if (!span) return;
  if (state.role !== "admin") {
    span.textContent = "显示更多项目";
    return;
  }
  const count = hiddenProjectCount(projects);
  span.textContent = count > 0 ? `显示内部/归档项目（${count}）` : "显示内部/归档项目";
}

function updateProjectRowActionState(project) {
  const rowActions = qs('[data-testid="project-crud-panel"] .ia-row-actions');
  if (!rowActions) return;
  rowActions.hidden = !project?.id;
  const archived = Boolean(project?.id && isArchivedProject(project));
  const protectedTeaching = Boolean(project?.id && isTeachingDemoProject(project));
  qsa('[data-ia-action="edit-project"], [data-ia-action="archive-project"], [data-ia-action="delete-project"]').forEach((button) => {
    if (!rowActions.contains(button)) return;
    const action = button.dataset.iaAction;
    const disabled = protectedTeaching || (archived && action !== "delete-project");
    button.disabled = disabled;
    button.setAttribute("aria-disabled", disabled ? "true" : "false");
    button.title = protectedTeaching
      ? teachingProtectedMessage()
      : (archived && action !== "delete-project" ? "归档项目为只读；可继续删除该项目记录。" : "");
  });
}

function isTeachingDemoProject(project) {
  const policy = project?.permission_policy || {};
  return Boolean(
    project?.id &&
      (project.id === state.teaching.demoProjectId ||
        project.id === "proj_demo_epilepsy_lab" ||
        policy.protected_teaching_dataset ||
        policy.teaching_mode)
  );
}

function isTeachingDemoFile(file) {
  const metadata = file?.metadata_json || {};
  const policy = file?.permission_policy || {};
  return Boolean(
    file?.id &&
      (file.id === state.teaching.demoFileId ||
        file.id === "eeg_demo_epilepsy_high_amplitude" ||
        metadata.protected_teaching_dataset ||
        policy.protected_teaching_dataset ||
        metadata.teaching_mode ||
        policy.teaching_mode ||
        file.retention_policy === "protected_teaching_demo")
  );
}

function teachingProtectedMessage() {
  return "内置示例数据用于练习，不能删除、归档或改名。";
}

function scopedProjectFiles(project, files = []) {
  const rows = project?.id ? (files || []).filter((item) => item.project_id === project.id && !isDeletedEegFile(item)) : [];
  if (state.teaching.active && isTeachingDemoProject(project)) {
    return rows.filter((item) => isTeachingDemoFile(item));
  }
  return rows;
}

function isArchivedProject(project) {
  const rawStatus = String(project?.status || "").toLowerCase();
  return ["archived", "archive", "deleted", "delete"].includes(rawStatus);
}

function isDeletedEegFile(file) {
  const rawStatus = String(file?.status || file?.upload_status || file?.data_status || "").toLowerCase();
  return ["deleted", "delete", "archived", "archive"].includes(rawStatus);
}

function activeWorkspaceFiles(files = state.workspace.files || []) {
  return (files || []).filter((item) => !isDeletedEegFile(item));
}

function projectUpdatedTime(project) {
  const value = Date.parse(project?.updated_at || project?.created_at || "");
  return Number.isFinite(value) ? value : 0;
}

function projectFileCount(project, files = []) {
  if (!project?.id) return 0;
  return activeWorkspaceFiles(files).filter((item) => item.project_id === project.id).length;
}

function projectOptionScopeLabel(project, files = []) {
  if (isArchivedProject(project)) return "\u5df2\u5f52\u6863";
  if (isReviewOrInternalProject(project) || isAutoGeneratedPilotProject(project)) return "内部/验收记录";
  const count = projectFileCount(project, files);
  return count > 0 ? `${count} \u4efd\u6570\u636e` : "\u5f85\u4e0a\u4f20\u6570\u636e";
}

function compareProjectsStable(a, b, files = []) {
  const aTime = projectUpdatedTime(a);
  const bTime = projectUpdatedTime(b);
  if (bTime !== aTime) return bTime - aTime;
  const aCount = projectFileCount(a, files);
  const bCount = projectFileCount(b, files);
  if (bCount !== aCount) return bCount - aCount;
  const aName = projectDisplayName(a) || a?.id || "";
  const bName = projectDisplayName(b) || b?.id || "";
  const nameCompare = aName.localeCompare(bName, "zh-Hans-CN", { numeric: true, sensitivity: "base" });
  if (nameCompare !== 0) return nameCompare;
  return String(a?.id || "").localeCompare(String(b?.id || ""));
}

function filteredWorkspaceProjects(projects, files = []) {
  const query = String(state.workspace.projectSearch || "").trim().toLowerCase();
  const showReview = Boolean(state.workspace.showReviewProjects);
  const selectedId = state.workspace.selectedProjectId || state.real.project?.id || "";
  const seenIds = new Set();
  const list = [...(projects || [])]
    .sort((a, b) => compareProjectsStable(a, b, files))
    .filter((project) => {
      if (!project?.id) return false;
      if (seenIds.has(project.id)) return false;
      seenIds.add(project.id);
      return true;
  });
  let filtered = list.filter((project) => {
    if (isCustomerTrialP0Mode() && !state.teaching.active && !showReview && !query) {
      return shouldShowProjectInCustomerTrial(project, files);
    }
    if (isTeachingDemoProject(project) && !state.teaching.active) return false;
    if (query) return projectSearchText(project).includes(query);
    if (!showReview && isHiddenFromCustomerProjectList(project)) return false;
    if (project.id === selectedId) return true;
    if (showReview && isArchivedProject(project)) return true;
    return !isArchivedProject(project);
  });
  if (!query && !showReview) {
    const withData = filtered.filter((project) => projectFileCount(project, files) > 0);
    filtered = (withData.length ? withData : filtered).slice(0, 24);
  } else if (query) {
    filtered = filtered.slice(0, 80);
  } else {
    filtered = filtered.slice(0, 80);
  }
  if (selectedId && !filtered.some((project) => project.id === selectedId)) {
    const selected = list.find((project) => project.id === selectedId) || state.real.project;
    const allowSelected = !isCustomerTrialP0Mode()
      || state.teaching.active
      || state.workspace.showReviewProjects
      || state.workspace.sessionProjectIds?.has?.(selected.id);
    if (selected?.id && allowSelected) filtered = [selected, ...filtered];
  }
  return filtered;
}

function isCustomerTrialP0Mode() {
  const params = new URLSearchParams(window.location.search || "");
  return ["auto", "demo", "login"].includes(String(params.get("customer_demo") || "").toLowerCase());
}

function hasExplicitCustomerDemoMode() {
  const params = new URLSearchParams(window.location.search || "");
  return ["auto", "demo", "login"].includes(String(params.get("customer_demo") || "").toLowerCase());
}

function isEpilepsyResultReviewV3() {
  const params = new URLSearchParams(window.location.search || "");
  return params.get("epilepsy_result_review_v3") === "1";
}

/* ===== epilepsy result review v3 panel (feature-gated) ===== */
const EPILEPSY_V3 = {
  events: [
    {id:"E-001",index:1,start:"00:10:42.3",duration:"14.8 s",channel:"T3-T5",feature:"节律性尖波样候选活动增强",score:"0.86",statusShort:"保留候选",statusFilter:"keep",statusClass:"ok",focus:["T3-T5","T4-T6","F7-T3","F8-T4","C3-T3","C4-T4"],event_start_sec:642.3,event_end_sec:657.1,event_duration_sec:14.8},
    {id:"E-002",index:2,start:"00:18:11.0",duration:"22.4 s",channel:"Fp2-F4",feature:"低频伪迹混入，形态不稳定",score:"0.74",statusShort:"不纳入",statusFilter:"exclude",statusClass:"bad",focus:["Fp1-F3","Fp2-F4","F3-C3","F4-C4","F7-T3","F8-T4"],event_start_sec:1091.0,event_end_sec:1113.4,event_duration_sec:22.4},
    {id:"E-007",index:3,start:"00:42:08.6",duration:"19.6 s",channel:"T3/T4",feature:"双侧颞区同步样尖波成分，频率演变",score:"0.91",statusShort:"保留候选",statusFilter:"keep",statusClass:"ok",focus:["T3-T5","T4-T6","F7-T3","F8-T4","C3-T3","C4-T4"],event_start_sec:2528.6,event_end_sec:2548.2,event_duration_sec:19.6},
    {id:"E-009",index:4,start:"00:47:36.2",duration:"31.2 s",channel:"T4-C4",feature:"短时节律活动边界不清",score:"0.79",statusShort:"待复核",statusFilter:"pending",statusClass:"warn",focus:["F8-T4","T4-T6","C4-T4","F4-C4","C4-P4","P4-O2"],event_start_sec:2856.2,event_end_sec:2887.4,event_duration_sec:31.2},
    {id:"E-013",index:5,start:"00:53:22.9",duration:"18.1 s",channel:"T3-T5",feature:"尖波样成分伴随背景活动改变",score:"0.88",statusShort:"保留候选",statusFilter:"keep",statusClass:"ok",focus:["F7-T3","T3-T5","C3-T3","F3-C3","C3-P3","P3-O1"],event_start_sec:3202.9,event_end_sec:3221.0,event_duration_sec:18.1},
    {id:"E-018",index:6,start:"01:08:44.1",duration:"11.7 s",channel:"F7-T3",feature:"前额伪迹活动，缺少明确演变",score:"0.62",statusShort:"不纳入",statusFilter:"exclude",statusClass:"bad",focus:["Fp1-F3","F7-T3","F3-C3","T3-T5","C3-P3","P3-O1"],event_start_sec:4124.1,event_end_sec:4135.8,event_duration_sec:11.7},
    {id:"E-026",index:7,start:"01:39:02.4",duration:"25.3 s",channel:"T4-T6",feature:"右侧颞后区候选节律成分",score:"0.84",statusShort:"保留候选",statusFilter:"keep",statusClass:"ok",focus:["F8-T4","T4-T6","C4-T4","F4-C4","C4-P4","P4-O2"],event_start_sec:5942.4,event_end_sec:5967.7,event_duration_sec:25.3},
    {id:"E-034",index:8,start:"02:01:15.8",duration:"16.5 s",channel:"C3-T3",feature:"疑似节律活动，需排除伪迹",score:"0.77",statusShort:"待复核",statusFilter:"pending",statusClass:"warn",focus:["F7-T3","C3-T3","T3-T5","F3-C3","C3-P3","P3-O1"],event_start_sec:7275.8,event_end_sec:7292.3,event_duration_sec:16.5},
  ],
  summary: {auto_candidates:38,visible_events:8,kept_candidates:21,pending_review:5,candidate_density_per_hour:"9.3/h",candidate_rate_per_hour:"9.3/h"},
  views: {
    focus:{label:"核心通道",suffix:"focus_channels_1_35hz",description:"默认复核视图：显示算法提示相关的核心导联，适合快速核对事件形态。"},
    overview:{label:"全通道概览",suffix:"all_channels_overview_1_35hz",description:"显示所有可视化导联。"},
    temporal:{label:"颞区导联组",suffix:"temporal_channels_1_35hz",description:"颞区导联分组，用于核对左右颞区同步性和局灶性形态差异。"},
    frontal:{label:"额区导联组",suffix:"frontal_channels_1_35hz",description:"额区导联分组，用于核对前额伪迹与前部活动。"},
    central_parietal_occipital:{label:"中央-顶枕导联组",suffix:"central_parietal_occipital_channels_1_35hz",description:"中央、顶区和枕区导联分组，用于判断事件是否跨区扩展。"},
  },
  /* static asset base path for P0 prototype; P1 will use real task artifact API */
  assetBase: "",
};
let epilepsyV3SelectedId = "E-001";
let epilepsyV3SelectedView = "focus";
let epilepsyV3ReviewState = {};

function epilepsyV3EventFromHash() {
  const m = (window.location.hash || "").match(/E-\d{3}/);
  return m && EPILEPSY_V3.events.some(e => e.id === m[0]) ? m[0] : null;
}
function epilepsyV3CurrentEvent() {
  return EPILEPSY_V3.events.find(e => e.id === epilepsyV3SelectedId) || EPILEPSY_V3.events[0];
}
function epilepsyV3CurrentMeta() {
  return EPILEPSY_V3.views[epilepsyV3SelectedView] || EPILEPSY_V3.views.focus;
}

/**
 * P1: fetch real epilepsy_ml task events from backend.
 * Calls GET /api/epilepsy-workbench/{task_id}/events and updates EPILEPSY_V3
 * events/summary. Falls back to prototype data if the call fails or returns
 * no events. Idempotent — subsequent calls reuse cached _liveTaskId.
 */
async function fetchEpilepsyV3LiveEvents(taskId) {
  if (!taskId) throw new Error("missing task id");
  const resp = await fetch(`${state.apiBase}/epilepsy-workbench/${encodeURIComponent(taskId)}/events`, { headers: withAuthHeaders({ "Accept": "application/json" }) });
  if (!resp.ok) throw new Error(`events endpoint ${resp.status}`);
  const dto = await resp.json();
  const events = Array.isArray(dto?.events) ? dto.events : [];
  if (!events.length) {
    // No real events discovered yet — reset summary if backend didn't provide one (GLM-03).
    EPILEPSY_V3.summary = dto?.summary || {auto_candidates:0, visible_events:0, kept_candidates:0, pending_review:0, candidate_density_per_hour:"0.0/h", candidate_rate_per_hour:"0.0/h"};
    EPILEPSY_V3._liveEmpty = true;
    return;
  }
  EPILEPSY_V3.events = events.map(ev => {
    try {
      const id = String(ev.event_id || ev.id || "");
      const startSec = Number(ev.event_start_sec ?? ev.start_sec ?? 0);
      const durSec = Number(ev.event_duration_sec ?? ev.duration_sec ?? 0);
      // Prefer backend computed score over recalculating from raw rms (GLM-02).
      const scoreRaw = ev.score ? parseFloat(ev.score) : Number(ev.rms ?? ev.max_abs_amplitude ?? 0);
      const reviewStatusRaw = String(ev.statusFilter || ev.review_status || "pending");
      const reviewStatus = ["keep", "exclude", "pending"].includes(reviewStatusRaw) ? reviewStatusRaw : "pending";
      const statusClass = reviewStatus === "keep" ? "ok" : reviewStatus === "exclude" ? "bad" : "warn";
      const statusShort = reviewStatus === "keep" ? "保留" : reviewStatus === "exclude" ? "不纳入" : "待复核";
      return {
        id,
        start: ev.time_label || _formatEpilepsySec(startSec),
        duration: `${durSec.toFixed(1)} s`,
        channel: ev.channel || "多通道",
        score: scoreRaw ? scoreRaw.toFixed(2) : "—",
        feature: ev.feature || "1-35 Hz 带通",
        statusFilter: reviewStatus,
        statusClass,
        statusShort,
      };
    } catch (_err) {
      // GLM-01: skip malformed events rather than crashing the whole list
      return null;
    }
  }).filter(Boolean);
  if (dto?.summary) {
    const sIn = dto.summary;
    EPILEPSY_V3.summary = {
      auto_candidates: sIn.auto_candidates ?? EPILEPSY_V3.events.length,
      kept_candidates: sIn.kept_candidates ?? 0,
      pending_review: sIn.pending_review ?? EPILEPSY_V3.events.length,
      candidate_density_per_hour: sIn.candidate_density_per_hour || sIn.candidate_rate_per_hour || EPILEPSY_V3.summary.candidate_density_per_hour || EPILEPSY_V3.summary.candidate_rate_per_hour,
      candidate_rate_per_hour: sIn.candidate_rate_per_hour || sIn.candidate_density_per_hour || EPILEPSY_V3.summary.candidate_rate_per_hour,
      visible_events: sIn.visible_events ?? EPILEPSY_V3.events.length,
    };
  }
  if (!EPILEPSY_V3.events.some(e => e.id === epilepsyV3SelectedId)) {
    epilepsyV3SelectedId = EPILEPSY_V3.events[0].id;
  }
}

function _formatEpilepsySec(sec) {
  const total = Math.max(0, Number(sec) || 0);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = Math.floor(total % 60);
  const pad = (n) => String(n).padStart(2, "0");
  return h > 0 ? `${pad(h)}:${pad(m)}:${pad(s)}` : `${pad(m)}:${pad(s)}`;
}

function renderEpilepsyResultReviewV3Panel() {
  const container = qs("#epilepsyResultReviewV3");
  if (!container) return;
  if (!isEpilepsyResultReviewV3()) { container.innerHTML = ""; return; }
  /* P1: if a real epilepsy_ml task exists, fetch its events from the backend.
     P0 fallback: use the static EPILEPSY_V3 prototype data. */
  const epilepsyTask = state.real.tasks?.epilepsy_ml || Object.values(state.real.tasks || {}).find(t => t?.module_name === "epilepsy_ml");
  if (epilepsyTask?.id && !EPILEPSY_V3._liveLoaded) {
    EPILEPSY_V3._liveLoaded = true;
    EPILEPSY_V3._liveTaskId = epilepsyTask.id;
    EPILEPSY_V3._loading = true;
    container.innerHTML = '<p style="padding:14px;color:var(--steel)">正在加载候选事件数据…</p>';
    fetchEpilepsyV3LiveEvents(epilepsyTask.id).then(() => {
      EPILEPSY_V3._loading = false;
      renderEpilepsyResultReviewV3Panel();
    }).catch(err => {
      EPILEPSY_V3._loading = false;
      EPILEPSY_V3._liveError = err.message || String(err);
      renderEpilepsyResultReviewV3Panel();
    });
    return;
  }

  const ev = epilepsyV3CurrentEvent();
  if (!ev) {
    container.innerHTML = `<p class="epilepsy-v3-loading-msg">${EPILEPSY_V3._liveError ? "实时数据加载失败，原型数据不可用：" + escapeHtml(EPILEPSY_V3._liveError) : "无候选事件数据。"}</p>`;
    return;
  }
  const meta = epilepsyV3CurrentMeta();
  const st = epilepsyV3ReviewState[ev.id] || {status: ev.statusFilter, note: ""};
  const s = EPILEPSY_V3.summary || {};
  const safeSummary = {
    auto_candidates: Number(s.auto_candidates || 0),
    visible_events: Number(s.visible_events || 0),
    kept_candidates: Number(s.kept_candidates || 0),
    pending_review: Number(s.pending_review || 0),
    candidate_density_per_hour: String(s.candidate_density_per_hour || s.candidate_rate_per_hour || "0.0/h"),
    candidate_rate_per_hour: String(s.candidate_rate_per_hour || s.candidate_density_per_hour || "0.0/h"),
  };
  const isLive = !!EPILEPSY_V3._liveTaskId;
  const evidenceBase = isLive ? `${state.apiBase}/epilepsy-workbench/${encodeURIComponent(EPILEPSY_V3._liveTaskId)}/events` : EPILEPSY_V3.assetBase;
  const taskArtifacts = state.real.artifacts?.epilepsy_ml || [];
  const allEventZipArtifact = taskArtifacts.find((a) => {
    const metadata = a.quota_usage_json || a.metadata_json || {};
    return (a.label || "").includes("all_events_evidence_package")
      && metadata.evidence_class === "real_waveform_window_package";
  });

  container.innerHTML = `
    <section class="panel epilepsy-v3-workspace" data-testid="epilepsy-v3-review-workspace">
      <div class="panel-head">
        <div>
          <h2>候选事件复核工作区</h2>
          <p>选择候选事件 → 查看 1-35 Hz 合成示意预览 → 记录复核结论。正式证据包需接入真实 EDF 波形窗；科研筛查辅助工具，仅供研究参考。</p>
        </div>
        <div class="epilepsy-v3-summary-pills">
              <span class="epilepsy-v3-pill info">自动候选 ${safeSummary.auto_candidates}</span>
              <span class="epilepsy-v3-pill ok">保留候选 ${safeSummary.kept_candidates}</span>
              <span class="epilepsy-v3-pill warn">待复核 ${safeSummary.pending_review}</span>
              <span class="epilepsy-v3-pill soft">候选密度 ${escapeHtml(safeSummary.candidate_density_per_hour)}，不是发作频率或疾病负担</span>
        </div>
      </div>
      <div class="epilepsy-v3-layout">
        <aside class="epilepsy-v3-event-index" data-testid="v3-event-index">
          <div class="epilepsy-v3-filter-bar">
            <button class="epilepsy-v3-filter-btn active" data-v3-filter="all">全部 (${safeSummary.visible_events})</button>
            <button class="epilepsy-v3-filter-btn" data-v3-filter="keep">保留</button>
            <button class="epilepsy-v3-filter-btn" data-v3-filter="pending">待复核</button>
            <button class="epilepsy-v3-filter-btn" data-v3-filter="exclude">不纳入</button>
          </div>
          <div class="epilepsy-v3-event-list">
            ${EPILEPSY_V3.events.map(e => `
              <div class="epilepsy-v3-event-item ${e.id === ev.id ? "selected" : ""}" data-v3-event="${escapeHtml(e.id)}" data-v3-status="${escapeHtml(e.statusFilter)}">
                <span class="epilepsy-v3-event-thumb"><img ${isLive ? `data-auth-image-url="${escapeHtml(`${evidenceBase}/${encodeURIComponent(e.id)}/evidence`)}"` : `src="${EPILEPSY_V3.assetBase}event_previews/${e.id}.png"`} alt="${escapeHtml(e.id)}" loading="lazy" onerror="this.style.display='none'"></span>
                <div class="epilepsy-v3-event-info">
                  <strong>${escapeHtml(e.id)}</strong>
                  <span class="epilepsy-v3-event-time">${escapeHtml(e.start)}</span>
                  <span class="epilepsy-v3-event-meta">${escapeHtml(e.channel)} · ${escapeHtml(e.duration)}</span>
                  <span class="epilepsy-v3-pill ${e.statusClass}">${escapeHtml(e.statusShort)}</span>
                </div>
              </div>
            `).join("")}
          </div>
        </aside>
        <section class="epilepsy-v3-viewer" id="epilepsyV3Viewer" data-testid="v3-evidence-viewer">
          <div class="epilepsy-v3-viewer-toolbar">
            <div class="epilepsy-v3-view-selector">
              ${Object.entries(EPILEPSY_V3.views).map(([key, v]) =>
                `<button class="epilepsy-v3-view-btn ${key === epilepsyV3SelectedView ? "active" : ""}" data-v3-view="${key}">${v.label}</button>`
              ).join("")}
            </div>
          </div>
          <div class="epilepsy-v3-viewer-header">
            <h3 id="epilepsyV3ViewerTitle">${escapeHtml(ev.id)} — ${escapeHtml(meta.label)}</h3>
            <p id="epilepsyV3ViewerSubtitle" class="epilepsy-v3-viewer-sub">${isLive ? "合成示意预览（非原始 EDF 波形证据）" : "静态示例预览（非临床证据）"} — ${escapeHtml(ev.start)} — ${escapeHtml(ev.channel)} — ${escapeHtml(ev.feature)}</p>
            <p id="epilepsyV3ViewerHint" class="epilepsy-v3-viewer-hint">${escapeHtml(meta.description)}</p>
          </div>
          <div class="epilepsy-v3-detail-grid">
            <div><small>开始时间</small><strong>${escapeHtml(ev.start)}</strong></div>
            <div><small>持续时间</small><strong>${escapeHtml(ev.duration)}</strong></div>
            <div><small>通道</small><strong>${escapeHtml(ev.channel)}</strong></div>
            <div><small>筛查分数</small><strong>${escapeHtml(ev.score)}</strong></div>
          </div>
          <div class="epilepsy-v3-image-frame" id="epilepsyV3ImageFrame">
            <img id="epilepsyV3MainImage" ${isLive ? `data-auth-image-url="${escapeHtml(`${evidenceBase}/${encodeURIComponent(ev.id)}/evidence`)}"` : `src="${EPILEPSY_V3.assetBase}event_previews/${ev.id}_${meta.suffix}.png"`} alt="${escapeHtml(ev.id)} ${escapeHtml(meta.label)}" onerror="this.alt='证据图加载中…'">
          </div>
          <div class="epilepsy-v3-download-row">
            ${isLive
              ? `<button id="epilepsyV3DlPng" type="button" class="epilepsy-v3-dl-btn" data-auth-download-url="${escapeHtml(`${evidenceBase}/${encodeURIComponent(ev.id)}/evidence`)}" data-auth-download-filename="${escapeHtml(`${ev.id}_${epilepsyV3SelectedView}_synthetic_preview.png`)}">下载合成示意 PNG</button>`
              : `<a id="epilepsyV3DlPng" class="epilepsy-v3-dl-btn" href="${EPILEPSY_V3.assetBase}event_previews/${ev.id}_${meta.suffix}.png" download="${ev.id}_${epilepsyV3SelectedView}_synthetic_preview.png">导出当前视图 PNG</a>`}
            ${isLive
              ? ""
              : `<a id="epilepsyV3DlSvg" class="epilepsy-v3-dl-btn" href="${EPILEPSY_V3.assetBase}event_previews/${ev.id}_${meta.suffix}.svg" download="${ev.id}_${epilepsyV3SelectedView}_1_35hz.svg">导出当前视图 SVG</a>`}
          </div>
        </section>
        <aside class="epilepsy-v3-review-panel" data-testid="v3-review-panel">
          <div class="epilepsy-v3-review-current">
            <h4>当前事件</h4>
            <strong id="epilepsyV3ReviewEventId">${escapeHtml(ev.id)} · ${escapeHtml(ev.channel)}</strong>
            <p id="epilepsyV3ReviewMeta">${escapeHtml(ev.start)} · ${escapeHtml(ev.duration)} · 筛查分数 ${escapeHtml(ev.score)}</p>
            <span id="epilepsyV3ReviewStatusPill" class="epilepsy-v3-pill ${st.status === "keep" ? "ok" : st.status === "exclude" ? "bad" : "warn"}">${st.status === "keep" ? "保留候选" : st.status === "exclude" ? "不纳入" : "待复核"}</span>
          </div>
          <div class="epilepsy-v3-review-actions">
            <h4>复核结论</h4>
            <button class="epilepsy-v3-review-btn keep ${st.status === "keep" ? "active" : ""}" data-v3-review="keep">保留候选</button>
            <button class="epilepsy-v3-review-btn pending ${st.status === "pending" ? "active" : ""}" data-v3-review="pending">待复核</button>
            <button class="epilepsy-v3-review-btn exclude ${st.status === "exclude" ? "active" : ""}" data-v3-review="exclude">不纳入</button>
          </div>
          <div class="epilepsy-v3-review-note">
            <h4>复核备注</h4>
            <textarea id="epilepsyV3ReviewNote" rows="3" placeholder="输入科研复核备注（可选）">${escapeHtml(st.note || "")}</textarea>
          </div>
          <div class="epilepsy-v3-current-zip">
            ${isLive
              ? `<button id="epilepsyV3CurrentZip" type="button" class="epilepsy-v3-dl-btn primary" data-auth-download-url="${escapeHtml(`${evidenceBase}/${encodeURIComponent(ev.id)}/evidence`)}" data-auth-download-filename="${escapeHtml(`${ev.id}_synthetic_preview.png`)}">下载 ${escapeHtml(ev.id)} 合成示意 PNG</button>`
              : `<button id="epilepsyV3CurrentZip" type="button" class="epilepsy-v3-dl-btn primary" disabled title="静态演示素材不提供正式证据包。">${escapeHtml(ev.id)} 演示预览 ZIP 暂不可用</button>`}
          </div>
        </aside>
      </div>
      <section class="epilepsy-v3-delivery-center" data-testid="v3-delivery-center">
        <div class="panel-head compact"><h3>交付中心</h3><p>${isLive ? "正式全量证据包需真实 EDF 波形窗；当前 live 任务只提供合成示意预览。" : "静态演示素材仅用于界面预览，不作为正式证据包。"}</p></div>
        ${isLive
          ? (allEventZipArtifact
            ? `<button id="epilepsyV3AllZip" type="button" class="epilepsy-v3-dl-btn" data-artifact-download="${escapeHtml(allEventZipArtifact.id)}">下载真实波形证据包 ZIP</button>`
            : `<button id="epilepsyV3AllZip" type="button" class="epilepsy-v3-dl-btn" disabled title="正式证据包需要接入真实 EDF 波形窗后生成。">正式全量证据包暂不可用</button>`)
          : `<button id="epilepsyV3AllZip" type="button" class="epilepsy-v3-dl-btn" disabled title="静态演示素材不提供正式证据包。">演示预览 ZIP 暂不可用</button>`}
        <p class="epilepsy-v3-delivery-note">${isLive ? "当前合成示意 PNG 不包含原始 EDF 波形窗、校验清单或正式交付 manifest，不能作为来源证据。" : `演示包可展示 ${safeSummary.visible_events} 个候选事件的预览结构；正式交付需由后端真实证据包生成。`}</p>
      </section>
    </section>
  `;

  initEpilepsyResultReviewV3Interactions();
  loadAuthenticatedUrlImages();
}

function initEpilepsyResultReviewV3Interactions() {
  const workspace = qs(".epilepsy-v3-workspace");
  if (!workspace || workspace.dataset.v3Init === "true") return;
  workspace.dataset.v3Init = "true";

  /* event selection */
  workspace.addEventListener("click", (ev) => {
    const authDownload = ev.target.closest("[data-auth-download-url]");
    if (authDownload) {
      const url = authDownload.dataset.authDownloadUrl || "";
      const filename = authDownload.dataset.authDownloadFilename || "download";
      downloadAuthorizedUrl(url, filename, "image/png,application/octet-stream").catch((error) => showToast(`下载失败: ${error.message || error}`));
      return;
    }
    const artifactDownload = ev.target.closest("[data-artifact-download]");
    if (artifactDownload) {
      downloadArtifactAs(artifactDownload.dataset.artifactDownload || "", "");
      return;
    }
    const eventItem = ev.target.closest("[data-v3-event]");
    if (eventItem) {
      epilepsyV3SelectedId = eventItem.dataset.v3Event;
      renderEpilepsyResultReviewV3Panel();
      return;
    }
    const viewBtn = ev.target.closest("[data-v3-view]");
    if (viewBtn) {
      epilepsyV3SelectedView = viewBtn.dataset.v3View;
      renderEpilepsyResultReviewV3Panel();
      return;
    }
    const filterBtn = ev.target.closest("[data-v3-filter]");
    if (filterBtn) {
      const filter = filterBtn.dataset.v3Filter;
      workspace.querySelectorAll("[data-v3-filter]").forEach(b => b.classList.remove("active"));
      filterBtn.classList.add("active");
      workspace.querySelectorAll("[data-v3-event]").forEach(item => {
        item.hidden = filter !== "all" && item.dataset.v3Status !== filter;
      });
      /* if selected event is hidden, pick first visible */
      const selected = workspace.querySelector("[data-v3-event].selected");
      if (selected && selected.hidden) {
        const first = workspace.querySelector("[data-v3-event]:not([hidden])");
        if (first) { epilepsyV3SelectedId = first.dataset.v3Event; renderEpilepsyResultReviewV3Panel(); }
      }
      return;
    }
    const reviewBtn = ev.target.closest("[data-v3-review]");
    if (reviewBtn) {
      const status = reviewBtn.dataset.v3Review;
      const ev2 = epilepsyV3CurrentEvent();
      epilepsyV3ReviewState[ev2.id] = {
        ...(epilepsyV3ReviewState[ev2.id] || {}),
        status,
        note: (qs("#epilepsyV3ReviewNote")?.value) || "",
      };
      try { localStorage.setItem("qlanalyser_v3_review_" + ev2.id, JSON.stringify(epilepsyV3ReviewState[ev2.id])); } catch(e) {}
      renderEpilepsyResultReviewV3Panel();
      return;
    }
  });

  /* review note persistence */
  const noteEl = qs("#epilepsyV3ReviewNote");
  if (noteEl) {
    noteEl.addEventListener("input", () => {
      const ev2 = epilepsyV3CurrentEvent();
      if (!epilepsyV3ReviewState[ev2.id]) epilepsyV3ReviewState[ev2.id] = {status: ev2.statusFilter, note: ""};
      epilepsyV3ReviewState[ev2.id].note = noteEl.value;
      try { localStorage.setItem("qlanalyser_v3_review_" + ev2.id, JSON.stringify(epilepsyV3ReviewState[ev2.id])); } catch(e) {}
    });
  }

  /* restore review state from localStorage */
  EPILEPSY_V3.events.forEach(e => {
    try {
      const saved = localStorage.getItem("qlanalyser_v3_review_" + e.id);
      if (saved) epilepsyV3ReviewState[e.id] = JSON.parse(saved);
    } catch(err) {}
  });

  /* hash-driven event selection */
  const hashEvent = epilepsyV3EventFromHash();
  if (hashEvent) epilepsyV3SelectedId = hashEvent;
}
/* ===== end epilepsy result review v3 ===== */

function isCurrentSessionProject(project) {
  if (!project?.id) return false;
  if (state.real.project?.id && project.id === state.real.project.id) return true;
  if (state.workspace.sessionProjectIds?.has?.(project.id)) return true;
  const account = typeof currentAccountId === "function" ? currentAccountId() : "";
  const ownerFields = [
    project.account_id,
    project.owner_id,
    project.created_by,
    project.user_id,
    project.customer_id,
  ].filter(Boolean).map((item) => String(item));
  return Boolean(account && ownerFields.includes(String(account)));
}

function shouldShowProjectInCustomerTrial(project, files = state.workspace.files || []) {
  if (!isCustomerTrialP0Mode()) return true;
  if (state.teaching.active) return isTeachingDemoProject(project);
  if (isTeachingDemoProject(project) || isHiddenFromCustomerProjectList(project)) return false;
  return Boolean(
    state.workspace.sessionProjectIds?.has?.(project.id)
    || (state.real.project?.id && project.id === state.real.project.id && state.workspace.sessionProjectIds?.has?.(project.id))
  );
}

function applyCustomerTrialProjectSurfaceCleanup() {
  const hideSurface = isCustomerTrialP0Mode() && !state.teaching.active;
  const teachingSurface = isCustomerTrialP0Mode() && state.teaching.active;
  const hideInternalProjectTools = hideSurface || teachingSurface;
  const search = qs("#workspaceProjectSearch");
  const reviewToggle = qs("#workspaceShowReviewProjects");
  const filterSummary = qs("#workspaceProjectFilterSummary");
  const searchField = search?.closest?.(".project-search-field");
  const searchLabel = search?.closest?.("label");
  const reviewToggleLabel = reviewToggle?.closest?.("label");
  const filterSummaryField = filterSummary?.closest?.(".project-filter-field");
  const projectSelect = qs("#workspaceProjectSelect");
  const projectRows = qs("#iaProjectRows");
  const projectRowActions = qs('[data-testid="project-crud-panel"] .ia-row-actions');
  const projectLedger = qs(".ia-project-ledger");
  const projectDataMaster = qs(".project-data-master-detail");
  const dataLedger = qs(".ia-data-ledger");
  const dataRows = qs("#iaDataRows");
  const prepQueue = qs("#prepDataQueue");
  const dataActions = qs(".ia-data-actions");
  const uploadRow = qs(".ia-data-upload-row");
  [search, searchLabel, reviewToggle, reviewToggleLabel, filterSummary, filterSummaryField, projectSelect, projectRows, projectRowActions, projectLedger, dataLedger, dataRows, prepQueue].forEach((node) => {
    if (node) node.hidden = hideInternalProjectTools;
  });
  [projectDataMaster].forEach((node) => {
    if (node) node.hidden = hideSurface;
  });
  if (searchField) searchField.classList.toggle("customer-project-surface", hideInternalProjectTools);
  if (dataActions) dataActions.hidden = hideInternalProjectTools;
  if (uploadRow) uploadRow.hidden = hideInternalProjectTools || !state.real.project?.id;
  if (teachingSurface) {
    qsa('[data-real-action="create-project"], [data-ia-action="edit-project"], [data-ia-action="archive-project"], [data-ia-action="delete-project"], [data-ia-action="rename-data"], [data-ia-action="delete-data"]').forEach((button) => {
      button.hidden = true;
      button.setAttribute("aria-hidden", "true");
    });
  }
  if (hideSurface && filterSummary) {
    filterSummary.textContent = "历史项目默认收起，只保留当前会话项目。";
  }
  if (hideSurface) {
    const projectSummary = qs("#prepContextSummary");
    const revisionState = qs("#prepRevisionState");
    const project = currentWorkspaceProject();
    const file = currentWorkspaceFile();
    if (projectSummary) {
      projectSummary.textContent = project?.id
        ? `当前项目：${projectDisplayName(project) || project.id}${file?.id ? `；当前数据：${eegFileDisplayName(file) || file.id}` : "；尚未选择数据"}`
        : "先创建项目，再上传 EEG 数据。";
    }
    if (revisionState) {
      revisionState.textContent = project?.id
        ? (file?.id ? "当前数据可继续预处理" : "当前项目等待上传数据")
        : "先创建项目。";
    }
  }
}

function setSurfaceHiddenForCustomer(selector, hidden) {
  qsa(selector).forEach((node) => {
    node.hidden = hidden;
    node.setAttribute("aria-hidden", hidden ? "true" : "false");
  });
}

function compactWaveformWorkbenchStatusForCustomer() {
  const target = qs("#waveformWorkbenchStatus");
  if (!target || !isCustomerTrialP0Mode()) return;
  const hasFile = Boolean(currentWorkspaceFile()?.id || state.real.eegFile?.id);
  const start = Number(eegState.start || 0);
  const windowSec = Number(eegState.windowSec || 10);
  const channels = Number(eegState.visibleChannels || 8);
  const sensitivity = waveformSensitivityUvPerRow();
  target.classList.remove("is-write-mode");
  target.innerHTML = hasFile
    ? [
        `<span><b>时间窗</b>${escapeHtml(formatWaveformHms(start))}-${escapeHtml(formatWaveformHms(start + windowSec))}</span>`,
        `<span><b>通道</b>${escapeHtml(String(channels))} ch</span>`,
        `<span><b>增益</b>${escapeHtml(Number(sensitivity.toFixed(1)))} uV/row</span>`,
      ].join("")
    : `<span><b>波形预览</b>选择或上传 EEG 数据后显示</span>`;
}

function applyCustomerTrialAnalysisSurfaceCleanup() {
  const enabled = isCustomerTrialP0Mode();
  const teachingSurface = enabled && state.teaching.active;
  const { project, projectFiles, file } = currentWorkspaceContext();
  const hasProject = Boolean(project?.id);
  const hasFile = Boolean(file?.id || state.real.eegFile?.id);
  const layout = qs('[data-testid="data-preparation-workbench"]');
  if (layout) {
    layout.classList.toggle("customer-analysis-surface", enabled);
    layout.classList.toggle("has-current-file", enabled && hasFile);
    layout.classList.toggle("no-current-project", enabled && !hasProject);
    layout.classList.toggle("no-current-file", enabled && !hasFile);
    layout.classList.toggle("teaching-customer-analysis-surface", teachingSurface);
  }

  const protectedNote = qs('[data-testid="teaching-data-protected"]');
  if (protectedNote) {
    protectedNote.hidden = !(teachingSurface && hasFile);
    protectedNote.setAttribute("aria-hidden", protectedNote.hidden ? "true" : "false");
  }
  setSurfaceHiddenForCustomer('[data-testid="preprocessing-readiness-panel"]', enabled);
  setSurfaceHiddenForCustomer('[data-testid="event-epoch-panel"]', enabled);
  setSurfaceHiddenForCustomer('[data-testid="data-preparation-submit-last"]', enabled && !hasFile);
  setSurfaceHiddenForCustomer('[data-real-action="save-bad-channel-audit"]', enabled);
  setSurfaceHiddenForCustomer('[data-real-action="discard-bad-channel-audit"]', enabled);
  setSurfaceHiddenForCustomer('[data-real-action="save-epoch-set"]', enabled);
  setSurfaceHiddenForCustomer('[data-real-action="download-epoch-record"]', enabled);
  setSurfaceHiddenForCustomer('[data-real-action="download-plan-json"]', enabled);
  setSurfaceHiddenForCustomer('[data-preview-jump="segment"], [data-preview-jump="bad-channel"], [data-preview-jump="reference"]', enabled);
  setSurfaceHiddenForCustomer("#eegPrevBtn, #eegNextBtn, #eegZoomOutBtn, #eegZoomInBtn, #eegResetBtn", enabled && !hasFile);
  setSurfaceHiddenForCustomer("#loadEegBtn", enabled && !hasFile);

  const queuePanel = qs("#prepDataQueue")?.closest?.(".ia-data-queue");
  if (queuePanel) {
    queuePanel.hidden = false;
    queuePanel.setAttribute("aria-hidden", "false");
    queuePanel.classList.toggle("customer-context-card", enabled);
    if (enabled) {
      const title = queuePanel.querySelector(".ia-section-title strong");
      const subtitle = queuePanel.querySelector(".ia-section-title span");
      if (title) title.textContent = "当前上下文";
      if (subtitle) subtitle.textContent = hasFile ? "当前数据已选择，可继续预览与确认" : "先选择或上传 EEG 数据";
      const boundary = queuePanel.querySelector('[data-testid="prep-no-upload-boundary"] span');
      if (boundary) boundary.textContent = hasProject
        ? "当前项目已就绪。请到数据页上传或选择 EEG 数据。"
        : "请先创建或打开项目，再上传 EEG 数据。";
      const dashboardButton = queuePanel.querySelector('[data-view-jump="dashboard"]');
      const storageButton = queuePanel.querySelector('[data-view-jump="storage"]');
      if (dashboardButton) {
        dashboardButton.hidden = hasProject;
        dashboardButton.setAttribute("aria-hidden", hasProject ? "true" : "false");
        const label = dashboardButton.querySelector("span");
        if (label) label.textContent = "创建或打开项目";
      }
      if (storageButton) {
        storageButton.hidden = !hasProject;
        storageButton.setAttribute("aria-hidden", hasProject ? "false" : "true");
        const label = storageButton.querySelector("span");
        if (label) label.textContent = "上传或选择 EEG 数据";
      }
    }
  }

  qsa(".ia-prep-steps .ia-step-card").forEach((card, index) => {
    if (!enabled) return;
    card.hidden = index > 2;
    card.setAttribute("aria-hidden", index > 2 ? "true" : "false");
    const copy = [
      ["选择数据", hasProject ? "确认当前项目内的 EEG 文件" : "先创建或打开项目"],
      ["预览波形", hasFile ? "查看波形、通道和显示范围" : "上传或选择数据后自动显示"],
      ["确认准备", hasFile ? "确认后进入分析任务" : "选择数据后可继续"],
    ][index];
    if (copy) {
      const strong = card.querySelector("strong");
      const span = card.querySelector("span");
      if (strong) strong.textContent = copy[0];
      if (span) span.textContent = copy[1];
    }
  });

  const previewPanel = qs('[data-testid="single-file-preview-panel"]');
  if (previewPanel) {
    previewPanel.classList.toggle("analysis-empty-state-panel", enabled && !hasFile);
    setTextIfPresent('[data-testid="single-file-preview-panel"] h2', "波形预览与准备方案");
    setTextIfPresent("#previewCaption", hasFile
      ? "先确认波形和数据概况，再进入分析任务。高级片段、坏道和事件记录已收起。"
      : "选择 EEG 数据后，这里会显示波形预览、通道信息和必要检查。");
  }

  const editWorkbench = qs('[data-testid="preview-edit-workbench"]');
  if (editWorkbench) {
    editWorkbench.hidden = enabled && !hasFile;
    editWorkbench.setAttribute("aria-hidden", editWorkbench.hidden ? "true" : "false");
  }

  const preprocessingPanel = qs('[data-testid="preprocessing-inline-panel"]');
  if (preprocessingPanel) {
    preprocessingPanel.classList.toggle("customer-compact-panel", enabled);
    setTextIfPresent('[data-testid="preprocessing-inline-panel"] h2', "准备设置");
    setTextIfPresent('[data-testid="preprocessing-inline-panel"] .panel-head p', hasFile
      ? "保留默认科研预览设置；需要精细调整时再进入高级模式。"
      : "选择数据后可查看概况并确认准备。");
  }

  const confirmButtons = qsa('[data-real-action="confirm-plan-inline"]');
  confirmButtons.forEach((button, index) => {
    const hideButton = enabled && (!hasFile || index > 0);
    button.hidden = hideButton;
    button.setAttribute("aria-hidden", hideButton ? "true" : "false");
  });

  const prepContextSummary = qs("#prepContextSummary");
  if (prepContextSummary && enabled) {
    prepContextSummary.textContent = hasProject
      ? `当前项目：${projectDisplayName(project) || project.id}；${hasFile ? `当前数据：${eegFileDisplayName(file || state.real.eegFile) || "已选择 EEG 数据"}` : `数据文件：${projectFiles.length} 个，等待选择或上传`}`
      : "先创建或打开项目，再上传 EEG 数据。";
  }
  const prepRevisionState = qs("#prepRevisionState");
  if (prepRevisionState && enabled) {
    prepRevisionState.textContent = hasFile
      ? "下一步：检查波形与数据概况，然后确认数据准备。"
      : "下一步：上传或选择 EEG 数据。";
  }

  if (teachingSurface) {
    const teachingQueue = qs("#prepDataQueue")?.closest?.(".ia-data-queue");
    const title = teachingQueue?.querySelector?.(".ia-section-title strong");
    const subtitle = teachingQueue?.querySelector?.(".ia-section-title span");
    const boundary = teachingQueue?.querySelector?.('[data-testid="prep-no-upload-boundary"] span');
    const storageButton = teachingQueue?.querySelector?.('[data-view-jump="storage"]');
    if (title) title.textContent = "\u5f53\u524d\u793a\u4f8b\u6570\u636e";
    if (subtitle) subtitle.textContent = "\u793a\u4f8b\u6570\u636e\u5df2\u8f7d\u5165\uff0c\u53ef\u76f4\u63a5\u9884\u89c8\u6ce2\u5f62\u5e76\u8fdb\u5165\u5206\u6790\u4efb\u52a1\u3002";
    if (boundary) boundary.textContent = "\u793a\u4f8b\u9879\u76ee\u5df2\u5c31\u7eea\uff0c\u65e0\u9700\u4e0a\u4f20\u6570\u636e\u3002";
    if (storageButton) {
      const label = storageButton.querySelector("span");
      if (label) label.textContent = "\u67e5\u770b\u793a\u4f8b\u6570\u636e";
      storageButton.title = "\u67e5\u770b\u5f53\u524d\u793a\u4f8b EEG \u6570\u636e";
    }
    if (prepContextSummary) {
      prepContextSummary.textContent = hasFile
        ? "\u5f53\u524d\u793a\u4f8b\u6570\u636e\u5df2\u9009\u62e9\uff0c\u53ef\u7ee7\u7eed\u9884\u89c8\u4e0e\u786e\u8ba4\u3002"
        : "\u793a\u4f8b\u9879\u76ee\u5df2\u6253\u5f00\uff0c\u6b63\u5728\u7b49\u5f85\u793a\u4f8b\u6570\u636e\u3002";
    }
    if (prepRevisionState) {
      prepRevisionState.textContent = hasFile
        ? "\u4e0b\u4e00\u6b65\uff1a\u786e\u8ba4\u6ce2\u5f62\u548c\u6570\u636e\u6982\u51b5\uff0c\u7136\u540e\u8fdb\u5165\u5206\u6790\u4efb\u52a1\u3002"
        : "\u4e0b\u4e00\u6b65\uff1a\u7b49\u5f85\u793a\u4f8b\u6570\u636e\u8f7d\u5165\u3002";
    }
    qsa(".ia-prep-steps .ia-step-card").forEach((card, index) => {
      const copy = [
        ["\u786e\u8ba4\u793a\u4f8b\u6570\u636e", "\u5df2\u8f7d\u5165\u53d7\u4fdd\u62a4\u7684 EEG \u793a\u4f8b\u6587\u4ef6"],
        ["\u9884\u89c8\u6ce2\u5f62", "\u68c0\u67e5\u6ce2\u5f62\u3001\u901a\u9053\u548c\u663e\u793a\u8303\u56f4"],
        ["\u8fdb\u5165\u5206\u6790", "\u786e\u8ba4\u51c6\u5907\u540e\u8fdb\u5165\u5206\u6790\u4efb\u52a1"],
      ][index];
      if (!copy) return;
      const strong = card.querySelector("strong");
      const span = card.querySelector("span");
      if (strong) strong.textContent = copy[0];
      if (span) span.textContent = copy[1];
    });
  }

  compactWaveformWorkbenchStatusForCustomer();
}

function applyCustomerTrialP0Fixes() {
  applyFinalVisibleCopyGate();
  const selectedProject = currentWorkspaceProject();
  qsa('[data-ia-action="delete-project"]').forEach((button) => {
    const protectedProject = Boolean(selectedProject?.id && isTeachingDemoProject(selectedProject));
    const disabled = !selectedProject?.id || protectedProject;
    button.disabled = disabled;
    button.setAttribute("aria-disabled", disabled ? "true" : "false");
    button.title = !selectedProject?.id
      ? "请先选择一个普通项目。"
      : protectedProject
        ? "教学示例用于练习，不能删除。"
        : "删除当前普通项目记录。";
  });
}

function projectStatusLabel(project, files = []) {
  if (!project?.id) return "未选择项目";
  const rawStatus = String(project.status || "").toLowerCase();
  if (["archived", "archive"].includes(rawStatus)) return "已归档";
  if (["deleted", "delete"].includes(rawStatus)) return "已删除";
  if (["blocked", "disabled"].includes(rawStatus)) return "暂不可用";
  const count = Number.isFinite(Number(project.data_count))
    ? Number(project.data_count)
    : files.filter((item) => item.project_id === project.id).length;
  if (count > 0) return `${count} 份数据可用`;
  return "待上传数据";
}

function fileStatusLabel(file) {
  if (!file?.id) return "未选择数据";
  const rawStatus = String(file.status || file.data_status || "").toLowerCase();
  const map = {
    uploaded: "已上传",
    previewed: "已预览",
    prepared: "已准备",
    needs_attention: "需处理",
    invalid: "不可用",
    archived: "已归档",
    deleted: "已删除",
    blocked: "暂不可用",
  };
  return map[rawStatus] || "等待预览";
}

function fileDetailLabel(file) {
  if (!file?.id) return "请选择项目后查看文件";
  const pieces = [
    file.detected_format || file.format || "EEG",
    file.channel_count ?? file.ch_count ? `${file.channel_count ?? file.ch_count} ch` : null,
    file.sampling_rate ?? file.sample_rate ? `${file.sampling_rate ?? file.sample_rate} Hz` : null,
  ].filter(Boolean);
  return pieces.join(" · ");
}

function preparationStatusLabel(file, plan, epochSet) {
  if (!file?.id) return "先选项目，再选择数据";
  if (epochSet?.id) {
    const 修订版本 = epochSet.revision ?? epochSet.data_preparation_revision ?? plan?.revision ?? 1;
    return `已确认 · 修订版本 ${修订版本}`;
  }
  if (plan?.id) {
    const 修订版本 = plan.revision ?? plan.data_preparation_revision ?? 1;
    return `待确认 · 修订版本 ${修订版本}`;
  }
  return "尚未确认准备方案";
}

function selectedStateLabel(project, file, plan, epochSet) {
  if (!project?.id) return "请先选择项目，再展开当前项目的数据。";
  if (!file?.id) {
    return `当前项目：${projectDisplayName(project) || project.id}；暂无选中数据，先从该项目的数据列表中选择一份文件。`;
  }
  const prepLabel = preparationStatusLabel(file, plan, epochSet);
  return `当前项目：${projectDisplayName(project) || project.id}；当前数据：${eegFileDisplayName(file)}；${prepLabel}。`;
}

function projectStatusLabelReadable(project, files = []) {
  if (!project?.id) return "未选择项目";
  const rawStatus = String(project.status || "").toLowerCase();
  if (["archived", "archive"].includes(rawStatus)) return "已归档";
  if (["deleted", "delete"].includes(rawStatus)) return "已删除";
  if (["blocked", "disabled"].includes(rawStatus)) return "暂不可用";
  const count = Number.isFinite(Number(project.data_count))
    ? Number(project.data_count)
    : files.filter((item) => item.project_id === project.id).length;
  return count > 0 ? `${count} 份数据可用` : "等待上传数据";
}

function fileStatusLabelReadable(file) {
  if (!file?.id) return "未选择数据";
  const rawStatus = String(file.status || file.data_status || "").toLowerCase();
  const map = {
    uploaded: "已上传，等待预览",
    previewed: "已预览",
    prepared: "已完成数据准备",
    needs_attention: "需要处理",
    invalid: "不可用",
    archived: "已归档",
    deleted: "已删除",
    blocked: "暂不可用",
  };
  return map[rawStatus] || "等待预览";
}

function fileDetailLabelReadable(file) {
  if (!file?.id) return "选择项目后查看文件";
  const pieces = [
    file.detected_format || file.format || "EEG",
    file.channel_count ?? file.ch_count ? `${file.channel_count ?? file.ch_count} ch` : null,
    file.sampling_rate ?? file.sample_rate ? `${file.sampling_rate ?? file.sample_rate} Hz` : null,
  ].filter(Boolean);
  return pieces.join(" · ") || "EEG 数据文件";
}

function preparationStatusLabelReadable(file, plan, epochSet) {
  if (!file?.id) return "先选择项目，再选择数据";
  if (epochSet?.id) {
    const 修订版本 = epochSet.revision ?? epochSet.data_preparation_revision ?? plan?.revision ?? 1;
    return `已确认 · 修订版本 ${修订版本}`;
  }
  if (plan?.id) {
    const 修订版本 = plan.revision ?? plan.data_preparation_revision ?? 1;
    return `待确认 · 修订版本 ${修订版本}`;
  }
  return "尚未确认准备方案";
}

function selectedStateLabelReadable(project, file, plan, epochSet) {
  if (!project?.id) return "请先选择项目，再展开当前项目的数据。";
  if (!file?.id) {
    return `当前项目：${projectDisplayName(project) || project.id}；暂未选中数据，请先从项目数据列表中选择一份文件。`;
  }
  const prepLabel = preparationStatusLabelReadable(file, plan, epochSet);
  return `当前项目：${projectDisplayName(project) || project.id}；当前数据：${eegFileDisplayName(file)}；${prepLabel}。`;
}

function setRealActionEnabled(action, enabled, title) {
  const buttons = qsa(`[data-real-action="${action}"]`);
  if (!buttons.length) return;
  buttons.forEach((button) => {
    button.disabled = !enabled;
    button.setAttribute("aria-disabled", enabled ? "false" : "true");
    if (title) {
      button.title = title;
      button.dataset.disabledReason = enabled ? "" : title;
      button.setAttribute("aria-label", title);
    }
  });
}

function currentFileChannelCount(file = currentWorkspaceFile()) {
  return Number(file?.channel_count ?? file?.ch_count ?? file?.n_channels ?? 0);
}

function currentFileHasChannelLocations(file = currentWorkspaceFile()) {
  if (!file) return false;
  if (file.has_montage || file.has_channel_locations || file.montage) return true;
  if (Array.isArray(file.channel_locations) && file.channel_locations.length) return true;
  if (Array.isArray(file.dig) && file.dig.length) return true;
  return Boolean(state.teaching.active && isTeachingDemoFile(file));
}

function hasSavedEpochSetForCurrentFile() {
  const file = currentWorkspaceFile();
  if (!file?.id || !state.real.epochSet?.id) return false;
  return !state.real.epochSet.input_file_id || state.real.epochSet.input_file_id === file.id;
}

function moduleAvailability(moduleName) {
  const customerVisibleModules = new Set(["psd", "erp"]);
  if (state.role !== "admin" && !customerVisibleModules.has(moduleName)) {
    return { enabled: false, reason: "该方法属于进阶/内部流程，客户工作区暂不开放。" };
  }
  const planReady = isAnalysisReady();
  const hasEpochSet = hasSavedEpochSetForCurrentFile();
  const channelCount = currentFileChannelCount();
  const hasChannelLocations = currentFileHasChannelLocations();
  const locked = (reason) => ({ enabled: false, reason });
  if (!planReady) return locked("请先完成数据准备并确认方案");
  if (["erp", "tfr", "multitaper_tfr", "pac"].includes(moduleName) && !hasEpochSet) {
    return locked("请先保存事件与片段，再运行事件相关或耦合分析");
  }
  if (moduleName === "reference_csd" && !hasChannelLocations) {
    return locked("CSD 需要通道位置信息；当前数据还不能运行");
  }
  if (moduleName === "connectivity" && channelCount < 4) {
    return locked("Connectivity 至少需要 4 个可用 EEG 通道");
  }
  const copy = {
    psd: "数据准备已确认，可以运行 PSD",
    multitaper_psd: "数据准备已确认，可以运行 Multitaper PSD",
    erp: "事件与片段已保存，可以运行 ERP",
    tfr: "事件与片段已保存，可以运行 TFR",
    multitaper_tfr: "事件与片段已保存，可以运行 Multitaper TFR",
    pac: "事件与片段已保存，可以运行 PAC",
    reference_csd: "通道位置信息已确认，可以运行 CSD",
    connectivity: "数据准备已确认，可以运行传感器空间 Connectivity",
    epilepsy_ml: "数据准备已确认，可以进入候选事件复核台",
  };
  return { enabled: true, reason: copy[moduleName] || "当前方法可以运行" };
}

function renderDisabledReason(action, selector) {
  const target = qs(selector);
  const button = qs(`[data-real-action="${action}"]`);
  if (!target || !button) return;
  const reason = button.disabled ? (button.dataset.disabledReason || button.title || "当前步骤暂不可用") : (button.title || "可以继续执行当前主操作");
  target.textContent = reason;
  target.classList.toggle("is-ready", !button.disabled);
}

function markRealNextActions(actions = []) {
  const nextSet = new Set(actions);
  qsa("[data-real-action]").forEach((button) => {
    const isNext = nextSet.has(button.dataset.realAction);
    button.classList.toggle("next-action", isNext);
    button.classList.toggle("locked-action", !isNext && button.disabled);
  });
}

function updateRealActionGate() {
  const plan = state.real.plan;
  const hasProject = Boolean(state.real.project?.id);
  const hasFile = Boolean(state.real.eegFile?.id);
  const hasPendingUpload = Boolean(qs("#real-eeg-file")?.files?.[0]);
  const protectedTeaching = Boolean(state.teaching.active && (isTeachingDemoProject(state.real.project) || isTeachingDemoFile(state.real.eegFile)));
  const planReady = isAnalysisReady();
  const teachingEpilepsyWorkbenchReady = Boolean(state.teaching.active && (hasFile || protectedTeaching));
  const planTitle = planReady
    ? "数据准备已确认，可以继续分析"
    : "请先完成数据准备并确认方案";
  const epilepsyWorkbenchTitle = planReady
    ? "进入癫痫样候选事件复核预览，先初筛再人工复核标注"
    : teachingEpilepsyWorkbenchReady
      ? "示例模式可直接进入癫痫样候选事件复核预览；系统会自动载入癫痫示例数据和准备方案"
      : planTitle;
  setRealActionEnabled("create-project", !hasProject, hasProject ? "当前已有项目，可继续选择或编辑" : "创建当前项目");
  setRealActionEnabled("upload-eeg", hasProject && hasPendingUpload, hasProject ? (hasPendingUpload ? "上传所选 EEG 文件到当前项目" : "请先选择 EEG 文件") : "请先选择或创建项目");
  setRealActionEnabled("run-qc-preview-inline", hasFile, hasFile ? "自动预览失败或数据已更新时，可重新加载预览" : "请先选择并上传 EEG 文件");
  setRealActionEnabled("run-metadata-qc-inline", hasFile, hasFile ? "查看当前 EEG 文件的基础信息" : "请先选择并上传 EEG 文件");
  setRealActionEnabled("save-bad-channel-audit", hasFile, hasFile ? "保存当前坏道草稿；确认数据准备后会写入处理记录" : "请先选择 EEG 数据");
  setRealActionEnabled("discard-bad-channel-audit", hasFile, hasFile ? "恢复坏道草稿并留下操作记录" : "请先选择 EEG 数据");
  setRealActionEnabled("save-epoch-set", hasFile && planReady, planReady ? "保存事件与片段设置" : "请先确认数据准备方案");
  setRealActionEnabled("download-epoch-record", hasFile, hasFile ? "下载当前 数据准备记录" : "请先上传 EEG 文件");
  setRealActionEnabled("confirm-plan-inline", hasFile, hasFile ? "确认当前数据准备方案" : "请先上传 EEG 文件");
  setRealActionEnabled("download-plan-json", Boolean(plan), plan ? "下载当前数据准备记录" : "请先确认或载入准备方案");
  const psdAvailability = moduleAvailability("psd");
  const erpAvailability = moduleAvailability("erp");
  setRealActionEnabled("run-psd", psdAvailability.enabled, psdAvailability.reason || planTitle);
  setRealActionEnabled("open-epilepsy-workbench", false, "癫痫样候选事件复核属于内部/专项流程，客户工作区暂不开放。");
  setRealActionEnabled("run-epilepsy-ml", false, "癫痫样候选事件复核属于内部/专项流程，客户工作区暂不开放。");
  setRealActionEnabled("run-erp", erpAvailability.enabled, erpAvailability.reason);
  ["run-tfr", "run-multitaper-psd", "run-multitaper-tfr", "run-reference-csd", "run-pac", "run-connectivity"].forEach((action) => {
    setRealActionEnabled(action, false, "该方法属于进阶/内部流程，客户工作区暂不开放。");
  });
  const task = latestAnalysisTask();
  const reportGate = reportReleaseGateSnapshot();
  setRealActionEnabled("create-report", reportGate.ready, reportGate.reason);
  const gate = qs('[data-testid="analysis-preparation-gate"]');
  if (gate) {
    gate.hidden = planReady;
    gate.classList.toggle("is-ready", planReady);
    gate.textContent = planReady
      ? "数据准备已确认，可以开始分析。"
      : "请先在数据准备页确认当前 EEG 的准备方案。";
  }
  const protectedNote = qs('[data-testid="teaching-data-protected"]');
  if (protectedNote) {
    protectedNote.hidden = !protectedTeaching;
  }
  if (protectedTeaching) setRealActionEnabled("upload-eeg", false, teachingProtectedMessage());
  let nextActions = ["create-project"];
  if (hasProject && (!hasFile || hasPendingUpload)) nextActions = ["upload-eeg"];
  if (hasFile && !planReady) nextActions = ["run-qc-preview-inline", "run-metadata-qc-inline", "confirm-plan-inline"];
  if (planReady && !state.real.epochSet) nextActions = ["save-epoch-set"];
  if (planReady && !task) nextActions = ["run-psd"];
  if (task && !state.real.resultsViewed) nextActions = [];
  if (task && state.real.resultsViewed && !state.real.report) nextActions = reportGate.ready ? ["create-report"] : [];
  if (state.real.report) nextActions = [];
  markRealNextActions(nextActions);
  renderDisabledReason("confirm-plan-inline", "#prepPrimaryReason");
  renderDisabledReason("run-psd", "#analysisPrimaryReason");
  renderDisabledReason("create-report", "#reportPrimaryReason");
  applyCustomerTrialAnalysisSurfaceCleanup();
  if ((qs(".view.active")?.id || "") === "analysis") applyAnalysisPageStateGate();
}
function getAuthSession() {
  try {
    return JSON.parse(localStorage.getItem(AUTH_KEY) || sessionStorage.getItem(AUTH_KEY) || "{}");
  } catch {
    return {};
  }
}

function currentAuthToken() {
  const session = getAuthSession();
  return session.token || getStoredCustomer().token || "";
}

function currentAccountId() {
  const session = getAuthSession();
  const customer = getStoredCustomer();
  return session.accountId || session.account_id || customer.accountId || customer.account_id || customer.id || "demo-customer";
}

function withAuthHeaders(headers = {}) {
  const next = { ...headers };
  const token = currentAuthToken();
  if (token && !next.Authorization) next.Authorization = `Bearer ${token}`;
  return next;
}

async function apiJson(path, options = {}) {
  const response = await fetch(`${state.apiBase}${path}`, {
    ...options,
    headers: withAuthHeaders({ Accept: "application/json", ...(options.headers || {}) }),
  });
  
  // SEC-FIX: Auto-logout on 401 Unauthorized
  if (response.status === 401 && state.role) {
    console.warn("API 返回 401，token 已失效，自动登出");
    clearSession();
    logout(false);
    showToast("登录已过期，请重新登录", "warning");
    throw new Error("Unauthorized: Session expired");
  }
  
  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    const rawDetail = typeof data === "string" ? data : data?.detail || data;
    const detail = typeof rawDetail === "string"
      ? rawDetail
      : (rawDetail?.message || rawDetail?.error || rawDetail?.error_code || JSON.stringify(rawDetail));
    throw new Error(detail || `Request failed: ${response.status}`);
  }
  return data;
}

async function downloadAuthorizedFile(path, filename = "") {
  const response = await fetch(`${state.apiBase}${path}`, {
    method: "GET",
    headers: withAuthHeaders({ Accept: "application/octet-stream" }),
    cache: "no-store",
  });
  if (!response.ok) throw new Error(`Download failed: ${response.status}`);
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename || "download";
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
window.downloadAuthorizedFile = downloadAuthorizedFile;

function downloadJsonPayload(payload, filename) {
  const blob = new Blob([`${JSON.stringify(payload, null, 2)}\n`], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
window.downloadJsonPayload = downloadJsonPayload;

function renderRealPlanState() {
  const target = qs("#realPlanState");
  if (!target) return;
  const plan = state.real.plan;
  const epochSet = state.real.epochSet;
  if (plan?.id && epochSet?.id) {
    target.textContent = "数据准备和事件分段已确认，可以进入分析。";
  } else if (plan?.id) {
    target.textContent = "数据准备已确认；如需事件相关分析，请继续保存事件分段。";
  } else {
    target.textContent = "请先完成数据准备确认，再提交 PSD/ERP 分析任务。";
  }
}

function renderEegPreviewEmptyState() {
  const empty = qs("#eegEmpty");
  if (!empty) return;
  const file = currentWorkspaceFile();
  const loaded = Boolean(eegState.data);
  qsa(".secondary-preview-action").forEach((button) => {
    button.hidden = !eegState.autoPreviewError;
    button.setAttribute("aria-hidden", eegState.autoPreviewError ? "false" : "true");
  });
  empty.classList.toggle("ready", loaded);
  if (loaded) return;
  if (file?.id) {
    const fileName = escapeHtml(eegFileDisplayName(file) || file.original_filename || file.id);
    if (eegState.autoPreviewInFlight) {
      empty.innerHTML = `<strong>正在预览：${fileName}</strong><span>已自动读取当前数据并生成基础质量预览，请稍候。</span>`;
    } else if (eegState.autoPreviewError) {
      empty.innerHTML = `<strong>预览未完成：${fileName}</strong><span>${escapeHtml(eegState.autoPreviewError)}。可使用“重新加载预览”再试一次。</span>`;
    } else if (eegState.selectedFilePreviewId === file.id && state.real.tasks.qc?.id) {
      empty.innerHTML = `<strong>预览记录已生成：${fileName}</strong><span>可以继续剔除/恢复片段、标记坏道，或进入数据准备确认。</span>`;
    } else {
      empty.innerHTML = `<strong>已选择当前数据：${fileName}</strong><span>系统会自动生成波形和基础质量预览；无需额外点击预览按钮。</span>`;
    }
  } else {
      empty.innerHTML = `<strong>第 2 步还没完成：上传或选择 EEG 数据</strong><span>请到数据页上传或选择当前项目的 EEG 数据。</span><button class="primary-btn mini" type="button" data-view-jump="storage">上传或选择数据</button>`;
  }
}

function waveformArtifactFromList(artifacts = []) {
  return artifacts.find((artifact) => {
    const key = `${artifact.label || ""} ${artifact.artifact_type || ""} ${artifact.object_key || ""} ${artifact.path || ""}`.toLowerCase();
    return key.includes("waveform_preview") && key.includes("json");
  }) || artifacts.find((artifact) => {
    const key = `${artifact.label || ""} ${artifact.object_key || ""} ${artifact.path || ""}`.toLowerCase();
    return key.includes("waveform") && key.endsWith(".json");
  }) || null;
}

function filterPreviewArtifactFromList(artifacts = []) {
  return artifacts.find((artifact) => {
    const key = `${artifact.label || ""} ${artifact.artifact_type || ""} ${artifact.object_key || ""} ${artifact.path || ""}`.toLowerCase();
    return key.includes("filter_preview") && key.includes("json");
  }) || null;
}

async function fetchArtifactJson(artifact) {
  const url = artifactDownloadUrl(artifact);
  if (!url) throw new Error("没有找到可读取的波形预览文件。");
  const response = await fetch(url, {
    method: "GET",
    headers: withAuthHeaders({ Accept: "application/json" }),
    cache: "no-store",
  });
  if (!response.ok) throw new Error(`波形预览文件读取失败：${response.status}`);
  return response.json();
}

function delay(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

async function fetchPreviewArtifactsWhenReady(taskId, { needFilter = false } = {}) {
  let artifacts = [];
  for (let attempt = 0; attempt < 70; attempt += 1) {
    artifacts = await fetchTaskArtifacts(taskId);
    const hasWaveform = Boolean(waveformArtifactFromList(artifacts));
    const hasFilter = Boolean(filterPreviewArtifactFromList(artifacts));
    if (hasWaveform && (!needFilter || hasFilter)) return artifacts;
    await delay(1500);
  }
  return artifacts;
}

function waveformMaxPointsPerChannel() {
  const canvas = qs("#eegCanvas");
  const rect = canvas?.getBoundingClientRect?.();
  const plotWidth = Math.max(450, Number(rect?.width || canvas?.clientWidth || 1280) - 110);
  return Math.min(2500, Math.max(900, Math.round(plotWidth * 2)));
}

function minMaxBucketWaveform(times, matrix, maxPoints) {
  const sampleCount = times.length;
  if (sampleCount <= maxPoints) return { times, matrix, downsampled: false };
  const targetBuckets = Math.max(1, Math.floor(maxPoints / 2));
  const bucketSize = Math.max(1, Math.ceil(sampleCount / targetBuckets));
  const keep = new Set([0, sampleCount - 1]);
  for (let start = 0; start < sampleCount; start += bucketSize) {
    const end = Math.min(sampleCount, start + bucketSize);
    let minIndex = start;
    let maxIndex = start;
    let minValue = Infinity;
    let maxValue = -Infinity;
    for (let index = start; index < end; index += 1) {
      const values = matrix.map((row) => Number(row[index])).filter((value) => Number.isFinite(value));
      if (!values.length) continue;
      const localMin = Math.min(...values);
      const localMax = Math.max(...values);
      if (localMin < minValue) {
        minValue = localMin;
        minIndex = index;
      }
      if (localMax > maxValue) {
        maxValue = localMax;
        maxIndex = index;
      }
    }
    keep.add(minIndex);
    keep.add(maxIndex);
  }
  const indices = Array.from(keep).sort((a, b) => a - b);
  return {
    times: indices.map((index) => times[index]),
    matrix: matrix.map((row) => indices.map((index) => row[index])),
    downsampled: true,
  };
}

function normalizeWaveformPreview(payload = {}) {
  const windowSpec = payload.window || payload.input_window || {};
  const rawChannels = Array.isArray(payload.channels)
    ? payload.channels
    : (Array.isArray(windowSpec.channels) ? windowSpec.channels : []);
  const channelInfo = rawChannels.map((item, index) => {
    if (item && typeof item === "object") {
      return {
        name: String(item.name || item.channel || item.label || `CH${index + 1}`),
        index: Number.isFinite(Number(item.index)) ? Number(item.index) : index,
        status: item.status || "good",
        type: item.type || "eeg",
        scale_uv: Number.isFinite(Number(item.scale_uv)) ? Number(item.scale_uv) : undefined,
      };
    }
    return { name: String(item || `CH${index + 1}`), index, status: "good", type: "eeg" };
  });
  const channels = channelInfo.map((item) => item.name);
  let times = Array.isArray(payload.times_sec) ? payload.times_sec.map(Number).filter((value) => Number.isFinite(value)) : [];
  let matrix = Array.isArray(payload.data_uv) ? payload.data_uv : [];
  let data = matrix.map((row) => Array.isArray(row) ? row.map(Number) : []);
  const pointCount = Math.min(times.length, ...data.map((row) => row.length).filter((length) => Number.isFinite(length)));
  times = times.slice(0, pointCount);
  data = data.map((row) => row.slice(0, pointCount).map((value) => (Number.isFinite(value) ? value : 0)));
  if (!channels.length || !times.length || !data.length || !data.some((row) => row.length > 1)) {
    throw new Error("波形预览文件缺少可绘制的通道或采样点。");
  }
  for (let index = 1; index < times.length; index += 1) {
    if (times[index] < times[index - 1]) {
      throw new Error("波形预览时间轴不是单调递增，无法可靠绘制。");
    }
  }
  const maxPoints = waveformMaxPointsPerChannel();
  const bucketed = minMaxBucketWaveform(times, data, maxPoints);
  times = bucketed.times;
  data = bucketed.matrix;
  const startSec = Number(payload.start_sec ?? windowSpec.start_sec ?? times[0] ?? 0);
  const durationSec = Number(payload.duration_sec ?? windowSpec.duration_sec ?? payload.duration ?? ((times[times.length - 1] || startSec) - startSec));
  const endSec = Number(windowSpec.end_sec ?? payload.end_sec ?? (startSec + Math.max(0, durationSec)));
  const displaySampleRate = Number(payload.display_sample_rate_hz ?? payload.sfreq_display ?? payload.display_sfreq ?? payload.sfreq ?? 0);
  const sampleRate = Number(payload.sample_rate_hz ?? payload.sfreq_original ?? payload.sfreq ?? displaySampleRate);
  return {
    ...payload,
    schema_version: payload.schema_version || "qlanalyser-waveform-preview-v0.1",
    input_file_id: payload.input_file_id || currentWorkspaceFile()?.id || "",
    source_task_id: payload.source_task_id || payload.task_id || eegState.taskId || null,
    window: {
      start_sec: startSec,
      duration_sec: durationSec,
      end_sec: Number.isFinite(endSec) ? endSec : startSec + Math.max(0, durationSec),
    },
    channels,
    channelInfo,
    channelNames: channels,
    times_sec: times,
    data_uv: data,
    unit: payload.unit || "uV",
    start_sec: startSec,
    duration_sec: durationSec,
    end_sec: Number.isFinite(endSec) ? endSec : startSec + Math.max(0, durationSec),
    sample_rate_hz: sampleRate,
    display_sample_rate_hz: displaySampleRate || (times.length > 1 ? Number((1 / Math.max(0.001, times[1] - times[0])).toFixed(3)) : 0),
    sfreq_display: displaySampleRate || payload.sfreq_display || payload.sfreq || 0,
    downsampled: Boolean(payload.downsampled || bucketed.downsampled),
    downsample_method: payload.downsample_method || (bucketed.downsampled ? "min_max_bucket" : "none"),
    scale_uv: Number(payload.scale_uv || 100),
    bad_channels: Array.isArray(payload.bad_channels) ? payload.bad_channels : [],
    bad_segments: Array.isArray(payload.bad_segments) ? payload.bad_segments : [],
    events: Array.isArray(payload.events) ? payload.events : [],
    annotations: Array.isArray(payload.annotations) ? payload.annotations : [],
    metadata: {
      ...(payload.metadata || {}),
      preview_only_filtering: Boolean(payload.metadata?.preview_only_filtering ?? payload.filter_preview_only ?? true),
      reference_preview_only: Boolean(payload.metadata?.reference_preview_only ?? true),
      non_diagnostic: true,
    },
  };
}

function currentWaveformPayload() {
  if (eegState.showFiltered && eegState.filteredData?.data_uv?.length) return eegState.filteredData;
  return eegState.data;
}


/* ── EEG Overview Bar (minimap) ─────────────────────────────────── */
async function loadEegOverview(file = currentWorkspaceFile()) {
  if (!file?.id || eegState.overviewLoading) return;
  const fileId = file.id;
  const fileDuration = Number(file.duration_sec || 0);
  if (fileDuration <= 0) return;
  // 只在文件变化时重新请求
  if (eegState.overviewPayload?._fileId === fileId) return;
  eegState.overviewLoading = true;
  eegState.overviewPayload = null;
  try {
    const maxOverviewDur = Math.min(fileDuration, 3600);
    const params = new URLSearchParams({
      start_sec: "0",
      duration_sec: String(maxOverviewDur),
      max_points: "400",
      mode: "minmax",
    });
    const data = await apiJson(`/eeg/files/${encodeURIComponent(fileId)}/waveform-window?${params}`);
    eegState.overviewPayload = { ...data, _fileId: fileId, _fileDuration: fileDuration };
    drawEegOverviewBar();
  } catch (e) {
    console.warn("[overview] load failed:", e?.message || e);
  } finally {
    eegState.overviewLoading = false;
  }
}

function overviewWaveformRows(payload) {
  const direct = payload?.data_uv || payload?.data;
  if (Array.isArray(direct) && direct.length) return direct;
  const channelPayloads = Array.isArray(payload?.channels) ? payload.channels : [];
  return channelPayloads.map((channel) => {
    if (Array.isArray(channel?.values) && channel.values.length) return channel.values.map(Number);
    const mins = Array.isArray(channel?.min_values) ? channel.min_values : [];
    const maxs = Array.isArray(channel?.max_values) ? channel.max_values : [];
    const row = [];
    for (let index = 0; index < Math.min(mins.length, maxs.length); index += 1) {
      row.push(Number(mins[index] || 0), Number(maxs[index] || 0));
    }
    return row;
  }).filter((row) => row.length);
}

function overviewChannelNames(payload) {
  const channels = payload?.channels || payload?.channel_names || [];
  if (!Array.isArray(channels)) return [];
  return channels.map((channel, index) => typeof channel === "string" ? channel : (channel?.name || `Ch${index + 1}`));
}

function drawEegOverviewBar() {
  const canvas = qs("#eegOverviewBar");
  const wrap = qs(".eeg-overview-bar-wrap");
  if (!canvas || !wrap) return;
  const payload = eegState.overviewPayload;
  const file = currentWorkspaceFile();
  const fileDuration = Number(file?.duration_sec || payload?._fileDuration || 0);
  if (!payload || fileDuration <= 0) {
    wrap.hidden = true;
    return;
  }
  wrap.hidden = false;

  const dpr = window.devicePixelRatio || 1;
  const cssW = canvas.clientWidth || canvas.width;
  const cssH = canvas.clientHeight || canvas.height;
  canvas.width = cssW * dpr;
  canvas.height = cssH * dpr;
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, cssW, cssH);

  const epochRows = (state.epilepsyInline && state.epilepsyInline.epochRows) || [];
  const hasStageCode = Array.isArray(epochRows) && epochRows.length > 0;
  const left = 8, right = 8, top = 4, bottom = 8 + (hasStageCode ? 9 : 0);
  const plotW = cssW - left - right;
  const plotH = cssH - top - bottom;
  const channels = overviewChannelNames(payload);
  const data = overviewWaveformRows(payload);
  if (!data.length) { ctx.fillStyle = "#999"; ctx.font = "11px sans-serif"; ctx.fillText("加载中...", left, cssH/2); return; }

  // 计算全局幅度范围（所有通道）
  let globalMax = 0;
  for (let ch = 0; ch < data.length; ch++) {
    const row = data[ch];
    if (!Array.isArray(row)) continue;
    for (let i = 0; i < row.length; i++) {
      const v = Math.abs(row[i]);
      if (v > globalMax) globalMax = v;
    }
  }
  if (globalMax <= 0) globalMax = 1;
  const midY = top + plotH / 2;
  const yScale = (plotH / 2) * 0.7 / globalMax;

  // 画多通道波形（中心叠加）
  const nCh = Math.min(data.length, 4); // 概览条只画前 4 通道避免太密
  for (let ch = 0; ch < nCh; ch++) {
    const row = data[ch];
    if (!Array.isArray(row) || !row.length) continue;
    ctx.beginPath();
    ctx.strokeStyle = "rgba(30, 110, 200, 0.55)";
    ctx.lineWidth = 0.6;
    for (let i = 0; i < row.length; i++) {
      const x = left + (i / (row.length - 1)) * plotW;
      const y = midY - row[i] * yScale;
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
    ctx.stroke();
  }

  // 当前窗口高亮框
  const startSec = Number(eegState.start || 0);
  const windowSec = Number(eegState.windowSec || 10);
  const x1 = left + (startSec / fileDuration) * plotW;
  const x2 = left + (Math.min(startSec + windowSec, fileDuration) / fileDuration) * plotW;
  ctx.fillStyle = "rgba(30, 120, 230, 0.18)";
  ctx.fillRect(x1, top, Math.max(2, x2 - x1), plotH);
  ctx.strokeStyle = "rgba(30, 120, 230, 0.9)";
  ctx.lineWidth = 1.5;
  ctx.strokeRect(x1, top, Math.max(2, x2 - x1), plotH);

  // Stage_Code 色带（百痫初筛结果）
  if (hasStageCode) {
    var bandBottom = cssH - bottom + 6;
    var bandY = bandBottom - 6;
    var epochDurationSec = Number(epochRows[0] && (epochRows[0].duration_sec || epochRows[0].duration) || 4);
    epochRows.forEach(function(row, idx) {
      var code = Number(row.Stage_Code || row.stage_code || row.prediction || 0);
      var epochStart = idx * epochDurationSec;
      var epochEnd = (idx + 1) * epochDurationSec;
      var bx = left + (epochStart / fileDuration) * plotW;
      var bw = Math.max(1, (epochEnd - epochStart) / fileDuration * plotW);
      ctx.fillStyle = code === 1 ? "rgba(220, 38, 38, 0.55)" : "rgba(148, 163, 184, 0.22)";
      ctx.fillRect(bx, bandY, bw + 0.5, 6);
    });
    ctx.strokeStyle = "rgba(148,163,184,0.35)";
    ctx.lineWidth = 0.5;
    ctx.strokeRect(left, bandY, plotW, 6);
  }
  // 时长标签
  var labelY = hasStageCode ? (cssH - bottom + 7) : (cssH - 1);
  ctx.fillStyle = "#666"; ctx.font = "10px sans-serif";
  ctx.fillText("0s", left, labelY);
  var durLabel = fileDuration >= 60 ? ((fileDuration / 60).toFixed(1) + "min") : (fileDuration.toFixed(0) + "s");
  ctx.textAlign = "right";
  ctx.fillText(durLabel, cssW - right, labelY);
  ctx.textAlign = "left";
}function handleEegOverviewClick(event) {
  const canvas = qs("#eegOverviewBar");
  const file = currentWorkspaceFile();
  const fileDuration = Number(file?.duration_sec || eegState.overviewPayload?._fileDuration || 0);
  if (!canvas || fileDuration <= 0) return;
  const rect = canvas.getBoundingClientRect();
  const left = 8, right = 8;
  const plotW = rect.width - left - right;
  const ratio = Math.max(0, Math.min(1, (event.clientX - rect.left - left) / plotW));
  const targetStart = Math.max(0, Math.min(fileDuration - Number(eegState.windowSec || 10), ratio * fileDuration));
  eegState.start = Math.round(targetStart * 10) / 10;
  syncEegControlsFromState();
  reloadWaveformPreview().catch((e) => showToast(e.message || "波形预览更新失败。"));
}
window.handleEegOverviewClick = handleEegOverviewClick;


function normalizeSegmentRange(start, end) {
  const a = Number(start);
  const b = Number(end);
  if (!Number.isFinite(a) || !Number.isFinite(b)) return null;
  const startSec = Math.max(0, Math.min(a, b));
  const displaySampleRate = Number(currentWaveformPayload()?.display_sample_rate_hz || currentWaveformPayload()?.sfreq_display || 0);
  const minDuration = Math.max(0.05, displaySampleRate > 0 ? 2 / displaySampleRate : 0.05);
  const endSec = Math.max(startSec + minDuration, Math.max(a, b));
  return { start_sec: startSec, end_sec: endSec };
}

function markSegmentInputEdited(input) {
  if (input?.matches?.("#segmentStart, #segmentEnd")) input.dataset.manualSegmentEdited = "true";
}

function manualSegmentRangeFromInputs() {
  const startInput = qs("#segmentStart");
  const endInput = qs("#segmentEnd");
  const startEdited = startInput?.dataset.manualSegmentEdited === "true";
  const endEdited = endInput?.dataset.manualSegmentEdited === "true";
  if (!startEdited || !endEdited) return null;
  const startRaw = String(startInput?.value || "").trim();
  const endRaw = String(endInput?.value || "").trim();
  if (!startRaw || !endRaw) return null;
  const start = Number(startRaw);
  const end = Number(endRaw);
  if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start) return null;
  return normalizeSegmentRange(start, end);
}

function selectedOrManualPrepSegmentRange() {
  return normalizeSegmentRange(eegState.selectedSegment?.start_sec, eegState.selectedSegment?.end_sec)
    || manualSegmentRangeFromInputs();
}

function clampNumber(value, min, max) {
  const n = Number(value);
  if (!Number.isFinite(n)) return min;
  return Math.max(min, Math.min(max, n));
}

function canvasPlotWindow(plot) {
  const start = Number(plot?.timeStart ?? 0);
  const end = Number(plot?.timeEnd ?? start + 1);
  return { start, end, duration: Math.max(0.001, end - start) };
}

function timeToCanvasX(timeSec, plot) {
  const { start, end, duration } = canvasPlotWindow(plot);
  const t = clampNumber(timeSec, start, end);
  return Number(plot.left || 0) + ((t - start) / duration) * Math.max(1, Number(plot.plotWidth || 1));
}

function canvasXToTime(x, plot) {
  const { start, end, duration } = canvasPlotWindow(plot);
  const left = Number(plot.left || 0);
  const plotWidth = Math.max(1, Number(plot.plotWidth || 1));
  const ratio = clampNumber((Number(x) - left) / plotWidth, 0, 1);
  return clampNumber(start + ratio * duration, start, end);
}

function updateSelectedSegmentInputs(segment = eegState.selectedSegment) {
  const normalized = normalizeSegmentRange(segment?.start_sec, segment?.end_sec);
  if (!normalized) return;
  const startInput = qs("#segmentStart");
  const endInput = qs("#segmentEnd");
  if (startInput) startInput.value = normalized.start_sec.toFixed(2).replace(/0$/, "").replace(/\.0$/, "");
  if (endInput) endInput.value = normalized.end_sec.toFixed(2).replace(/0$/, "").replace(/\.0$/, "");
}

function eegCanvasTimeFromEvent(event) {
  const canvas = qs("#eegCanvas");
  const plot = eegState.lastPlot;
  if (!canvas || !plot) return null;
  const rect = canvas.getBoundingClientRect();
  return canvasXToTime(event.clientX - rect.left, plot);
}

function redrawCurrentWaveform() {
  const payload = currentWaveformPayload();
  if (payload?.data_uv?.length) drawEegWaveformPreview(payload);
  else drawEegPreviewSkeleton(currentWorkspaceFile());
}

function revealWaveformPreview(options = {}) {
  const { delayMs = 0 } = options;
  const run = () => {
    const target = qs("#eegCanvas")?.closest?.(".waveform-main-column") || qs("#eegCanvas");
    if (!target || qs(".view.active")?.id !== "analysis") return;
    target.scrollIntoView?.({ behavior: delayMs ? "smooth" : "auto", block: "center", inline: "nearest" });
    qs("#eegCanvas")?.focus?.({ preventScroll: true });
  };
  if (delayMs) window.setTimeout(run, delayMs);
  else window.requestAnimationFrame(run);
}

function renderWaveformInteractionHint(message = "") {
  const target = qs("#eegEvents");
  if (!target) return;
  const selected = normalizeSegmentRange(eegState.selectedSegment?.start_sec, eegState.selectedSegment?.end_sec);
  const selectedText = selected ? `当前选区 ${selected.start_sec.toFixed(2)}-${selected.end_sec.toFixed(2)} s` : "当前预览窗未发现事件标记";
  const excludedText = prepEditState.excludedSegments.length ? `已剔除 ${prepEditState.excludedSegments.length} 段` : "尚未剔除片段";
  const pieces = [message || selectedText];
  if (selected || prepEditState.excludedSegments.length) pieces.push(excludedText);
  target.innerHTML = pieces.map((item) => `<span>${escapeHtml(item)}</span>`).join("");
}

function formatPreviewFilterSummary() {
  const enabled = Boolean(eegState.filterEnabled || eegState.showFiltered);
  const band = [];
  if (Number(eegState.filterLfreq) > 0) band.push(`${Number(eegState.filterLfreq)} Hz 以上`);
  if (Number(eegState.filterHfreq) > 0) band.push(`${Number(eegState.filterHfreq)} Hz 以下`);
  const bandText = band.length ? band.join(" / ") : "未设置带通";
  const notchText = Number(eegState.filterNotch) > 0 ? `陷波 ${Number(eegState.filterNotch)} Hz` : "未启用陷波";
  return enabled ? `滤波参数 ${bandText} / ${notchText} / 仅预览` : "滤波参数 未启用 / 仅预览";
}

function syncEegControlsFromState() {
  const startInput = qs("#eegStartInput");
  const windowInput = qs("#eegWindowInput");
  const gainInput = qs("#eegGainInput");
  const channelInput = qs("#eegChannelInput");
  const filterToggle = qs("#eegFilterPreviewToggle");
  const file = currentWorkspaceFile();
  eegState.windowSec = clampEegWindowDuration(eegState.windowSec || 10);
  const maxStart = Math.max(0, Number(file?.duration_sec || 0) - Number(eegState.windowSec || 10));
  eegState.start = Math.max(0, Math.min(Number(eegState.start || 0), Number.isFinite(maxStart) ? maxStart : Number(eegState.start || 0)));
  eegState.visibleChannels = Math.max(1, Math.min(64, Math.round(Number(eegState.visibleChannels || 8))));
  eegState.gain = Math.max(0.5, Math.min(8, Number(eegState.gain || 2)));
  if (startInput) {
    startInput.value = Number(eegState.start || 0).toFixed(1).replace(/\.0$/, "");
    if (file?.duration_sec) startInput.max = String(Math.max(0, Number(file.duration_sec) - Number(eegState.windowSec || 10)));
  }
  if (windowInput) {
    windowInput.max = String(maxEegWindowDuration());
    windowInput.value = String(Number(eegState.windowSec.toFixed(1)));
  }
  if (gainInput) gainInput.value = String(eegState.gain);
  if (channelInput) channelInput.value = String(eegState.visibleChannels);
  if (filterToggle) filterToggle.checked = Boolean(eegState.showFiltered || eegState.filterEnabled);
  setTextIfPresent("#eegWindowLabel", `${eegState.windowSec} s`);
  setTextIfPresent("#eegGainLabel", `${Number(waveformSensitivityUvPerRow().toFixed(1))} uV/row`);
  setTextIfPresent("#eegChannelLabel", String(eegState.visibleChannels));
  // 显示文件总时长提示，帮助用户知道数据范围
  const durationHint = qs("#eegDurationHint");
  if (durationHint) {
    const totalSec = Number(file?.duration_sec || 0);
    if (totalSec > 0) {
      durationHint.textContent = `/ ${totalSec >= 60 ? `${(totalSec / 60).toFixed(1)} min` : `${totalSec.toFixed(0)} s`}`;
      durationHint.hidden = false;
    } else {
      durationHint.hidden = true;
    }
  }
  syncWaveformModeUi();
  renderWaveformWorkbenchStatus();
}

function buildQcPreviewParametersFromUi(options = {}) {
  const file = currentWorkspaceFile();
  eegState.start = Math.max(0, Number(numberFromInput("#eegStartInput", eegState.start || 0)) || 0);
  eegState.windowSec = clampEegWindowDuration(Number(numberFromInput("#eegWindowInput", eegState.windowSec || 10)) || 10);
  eegState.visibleChannels = Math.max(1, Math.min(64, Math.round(Number(numberFromInput("#eegChannelInput", eegState.visibleChannels || 8)) || 8)));
  eegState.gain = Math.max(0.5, Math.min(8, Number(numberFromInput("#eegGainInput", eegState.gain || 2)) || 2));
  eegState.filterEnabled = Boolean(qs("#eegFilterPreviewToggle")?.checked);
  eegState.showFiltered = eegState.filterEnabled;
  eegState.filterLfreq = Math.max(0, Number(numberFromInput("#presetPrepLfreq", eegState.filterLfreq || 1)) || 0);
  eegState.filterHfreq = Math.max(0, Number(numberFromInput("#presetPrepHfreq", eegState.filterHfreq || 40)) || 40);
  eegState.filterNotch = Math.max(0, Number(numberFromInput("#presetPrepNotch", eegState.filterNotch || 50)) || 0);
  const sfreq = Number(file?.sampling_rate || file?.sfreq || eegState.data?.sfreq_original || eegState.data?.sfreq_display || 0);
  const nyquist = sfreq > 0 ? sfreq / 2 : 0;
  if (nyquist > 0) {
    const maxCutoff = Math.max(0, nyquist - 1);
    if (eegState.filterHfreq >= nyquist) eegState.filterHfreq = maxCutoff > eegState.filterLfreq ? Number(maxCutoff.toFixed(1)) : 0;
    if (eegState.filterNotch >= nyquist) eegState.filterNotch = 0;
    if (eegState.filterLfreq > 0 && eegState.filterHfreq > 0 && eegState.filterLfreq >= eegState.filterHfreq) {
      eegState.filterLfreq = Math.max(0, Number((eegState.filterHfreq / 2).toFixed(1)));
    }
  }
  const lfreqInput = qs("#presetPrepLfreq");
  const hfreqInput = qs("#presetPrepHfreq");
  const notchInput = qs("#presetPrepNotch");
  if (lfreqInput) lfreqInput.value = String(eegState.filterLfreq);
  if (hfreqInput) hfreqInput.value = String(eegState.filterHfreq);
  if (notchInput) notchInput.value = String(eegState.filterNotch);
  eegState.filterNotchEnabled = eegState.filterEnabled && eegState.filterNotch > 0;
  syncEegControlsFromState();
  const parameters = {
    fast_ui_preview: Boolean(options.fastUiPreview),
    preview: {
      start_sec: Number(eegState.start || 0),
      duration_sec: Number(eegState.windowSec || 10),
      channel_limit: Number(eegState.visibleChannels || 8),
      display_sfreq: 200,
    },
    filter_preview: {
      enabled: Boolean(eegState.filterEnabled),
      bandpass: {
        enabled: Boolean(eegState.filterEnabled && (eegState.filterLfreq > 0 || eegState.filterHfreq > 0)),
        l_freq: eegState.filterLfreq > 0 ? Number(eegState.filterLfreq) : null,
        h_freq: eegState.filterHfreq > 0 ? Number(eegState.filterHfreq) : null,
        method: "fir",
      },
      notch: {
        enabled: Boolean(eegState.filterNotchEnabled),
        freqs: eegState.filterNotchEnabled ? [Number(eegState.filterNotch)] : [],
        method: "fir",
      },
      compare_mode: "stacked",
      apply_to: "preview_window_only",
    },
    gain: Number(eegState.gain || 2),
    boundary: "仅用于科研数据准备预览，不作为临床诊断依据；预览滤波不改写原始 EEG。",
  };
  eegState.lastPreviewParameters = parameters;
  return parameters;
}

async function reloadWaveformPreview() {
  const file = currentWorkspaceFile();
  if (!file?.id) {
    showToast("请先选择 EEG 数据。");
    return null;
  }
  return runQcPreviewFromUi();
}

function eegFileDurationSec() {
  const file = currentWorkspaceFile();
  const payload = currentWaveformPayload();
  const candidates = [
    file?.duration_sec,
    payload?.file_duration_sec,
    payload?.metadata?.duration_sec,
    payload?.window?.file_duration_sec,
  ].map(Number).filter((value) => Number.isFinite(value) && value > 0);
  return candidates[0] || Math.max(30, Number(eegState.start || 0) + Number(eegState.windowSec || 10));
}

function clampEegWindowStart(start = eegState.start, duration = eegState.windowSec) {
  const fileDuration = eegFileDurationSec();
  const windowSec = clampEegWindowDuration(duration || eegState.windowSec || 10);
  const maxStart = Math.max(0, fileDuration - windowSec);
  return clampNumber(Number(start || 0), 0, maxStart);
}

function maxEegWindowDuration() {
  return Math.min(
    EDF_BROWSER_INTERACTION_CONSTANTS.maxWindowSec,
    Math.max(EDF_BROWSER_INTERACTION_CONSTANTS.minWindowSec, eegFileDurationSec()),
  );
}

function clampEegWindowDuration(duration = eegState.windowSec) {
  return clampNumber(
    Number(duration || 10),
    EDF_BROWSER_INTERACTION_CONSTANTS.minWindowSec,
    maxEegWindowDuration(),
  );
}

async function reloadWaveformAfterViewportChange(options = {}) {
  syncEegControlsFromState();
  qs("#eegCanvas")?.focus?.({ preventScroll: true });
  if (!options.silent) return reloadWaveformPreview();
  const file = currentWorkspaceFile();
  if (!file?.id) {
    renderWaveformInteractionHint("请先选择 EEG 数据。");
    return null;
  }
  try {
    return await reloadWaveformPreview();
  } catch (error) {
    renderWaveformInteractionHint(error.message || "波形预览更新失败。");
    return null;
  }
}

function shiftEegWindow(direction = 1, ratio = 0.5, options = {}) {
  const windowSec = clampEegWindowDuration(eegState.windowSec || 10);
  const step = Math.max(0.05, windowSec * Number(ratio || 0.5));
  eegState.start = clampEegWindowStart(Number(eegState.start || 0) + step * direction, windowSec);
  return reloadWaveformAfterViewportChange(options);
}

function zoomEegWindow(factor = 1, anchorTime = null, options = {}) {
  const oldStart = Number(eegState.start || 0);
  const oldDuration = clampEegWindowDuration(eegState.windowSec || 10);
  const scale = Number(factor || 1);
  const newDuration = clampEegWindowDuration(oldDuration * scale);
  const anchor = Number.isFinite(Number(anchorTime)) ? Number(anchorTime) : oldStart + oldDuration / 2;
  const anchorRatio = clampNumber((anchor - oldStart) / oldDuration, 0, 1);
  eegState.windowSec = newDuration;
  eegState.start = clampEegWindowStart(anchor - anchorRatio * newDuration, newDuration);
  return reloadWaveformAfterViewportChange(options);
}

function adjustEegAmplitudeSensitivity(direction = 1) {
  const factor = EDF_BROWSER_INTERACTION_CONSTANTS.gainStepRatio;
  eegState.gain = direction > 0
    ? Math.min(8, Number(eegState.gain || 2) * factor)
    : Math.max(0.5, Number(eegState.gain || 2) / factor);
  syncEegControlsFromState();
  redrawCurrentWaveform();
  qs("#eegCanvas")?.focus?.({ preventScroll: true });
  return Promise.resolve();
}

function resetEegPreviewControls() {
  eegState.start = 0;
  eegState.windowSec = 10;
  eegState.gain = 2;
  eegState.visibleChannels = 8;
  eegState.showFiltered = false;
  eegState.filterEnabled = false;
  setWaveformInteractionMode("browse", { silent: true });
  return reloadWaveformAfterViewportChange();
}

function drawEegWaveformPreview(payload = currentWaveformPayload()) {
  const canvas = qs("#eegCanvas");
  const ctx = canvas?.getContext?.("2d");
  if (!canvas || !ctx || !payload?.data_uv?.length) return false;
  const emptyOverlay = qs("#eegEmpty");
  if (emptyOverlay) {
    emptyOverlay.classList.add("ready");
    emptyOverlay.innerHTML = "";
  }

  const rect = canvas.getBoundingClientRect();
  const dpr = Math.max(1, window.devicePixelRatio || 1);
  const cssWidth = Math.max(720, Math.round(rect.width || canvas.clientWidth || 1280));
  const cssHeight = Math.max(360, Math.round(rect.height || canvas.clientHeight || 520));
  if (canvas.width !== Math.round(cssWidth * dpr) || canvas.height !== Math.round(cssHeight * dpr)) {
    canvas.width = Math.round(cssWidth * dpr);
    canvas.height = Math.round(cssHeight * dpr);
  }
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, cssWidth, cssHeight);
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, cssWidth, cssHeight);

  const left = 86;
  const right = 24;
  const top = 42;
  const bottom = 46;
  const plotWidth = Math.max(240, cssWidth - left - right);
  const plotHeight = Math.max(220, cssHeight - top - bottom);
  const visibleCount = Math.max(1, Math.min(Number(qs("#eegChannelInput")?.value || eegState.visibleChannels || 8), payload.data_uv.length));
  const rows = payload.data_uv.slice(0, visibleCount);
  const channels = (payload.channels || payload.channelNames || []).slice(0, visibleCount);
  const times = payload.times_sec || [];
  const timeStart = Number(payload.window?.start_sec ?? payload.start_sec ?? times[0] ?? 0);
  const timeEnd = Number(payload.window?.end_sec ?? payload.end_sec ?? times[times.length - 1] ?? (timeStart + Number(payload.duration_sec || eegState.windowSec || 10)));
  const rowHeight = plotHeight / visibleCount;
  const palette = ["#155c9c", "#157a77", "#7c4dff", "#c2410c", "#0f766e", "#9333ea", "#b45309", "#0369a1"];
  eegState.lastPlot = { left, right, top, bottom, plotWidth, plotHeight, timeStart, timeEnd };

  const drawTimeBand = (segment, fillStyle, strokeStyle, label) => {
    const normalized = normalizeSegmentRange(segment?.start_sec, segment?.end_sec);
    if (!normalized || normalized.end_sec < timeStart || normalized.start_sec > timeEnd) return;
    const x = timeToCanvasX(normalized.start_sec, eegState.lastPlot);
    const w = Math.max(2, timeToCanvasX(normalized.end_sec, eegState.lastPlot) - x);
    ctx.fillStyle = fillStyle;
    ctx.fillRect(x, top, w, plotHeight);
    ctx.strokeStyle = strokeStyle;
    ctx.lineWidth = 1;
    ctx.strokeRect(x, top, w, plotHeight);
    if (label) {
      ctx.fillStyle = strokeStyle;
      ctx.font = "700 11px system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif";
      ctx.fillText(label, x + 6, top + 16);
    }
  };
  prepEditState.excludedSegments.forEach((segment, index) => drawTimeBand(segment, "rgba(239, 68, 68, 0.16)", "rgba(220, 38, 38, 0.75)", index === 0 ? "坏段" : ""));
  const payloadBadSegments = Array.isArray(payload.bad_segments) ? payload.bad_segments : [];
  payloadBadSegments.forEach((segment, index) => drawTimeBand(segment, "rgba(239, 68, 68, 0.10)", "rgba(185, 28, 28, 0.55)", index === 0 && !prepEditState.excludedSegments.length ? "坏段" : ""));
  if (eegState.selectedSegment) drawTimeBand(eegState.selectedSegment, "rgba(236, 72, 153, 0.14)", "rgba(219, 39, 119, 0.8)", "选段");

  ctx.strokeStyle = "#e5edf1";
  ctx.lineWidth = 1;
  ctx.font = "12px system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif";
  for (let i = 0; i <= 5; i += 1) {
    const x = left + (plotWidth * i) / 5;
    ctx.beginPath();
    ctx.moveTo(x, top);
    ctx.lineTo(x, top + plotHeight);
    ctx.stroke();
    const label = `${(timeStart + ((timeEnd - timeStart) * i) / 5).toFixed(1)} s`;
    ctx.fillStyle = "#64748b";
    ctx.fillText(label, x - 16, top + plotHeight + 24);
  }

  rows.forEach((samples, rowIndex) => {
    const centerY = top + rowHeight * rowIndex + rowHeight / 2;
    const finite = samples.filter((value) => Number.isFinite(value));
    const maxAbs = Math.max(1, ...finite.map((value) => Math.abs(value)));
    const scale = (rowHeight * 0.34 * Number(qs("#eegGainInput")?.value || eegState.gain || 2)) / maxAbs;
    ctx.strokeStyle = "#edf2f6";
    ctx.beginPath();
    ctx.moveTo(left, centerY);
    ctx.lineTo(left + plotWidth, centerY);
    ctx.stroke();

    const channelName = channels[rowIndex] || `CH${rowIndex + 1}`;
    const isBadDraft = prepEditState.badChannels.some((item) => String(item.channel || "").toLowerCase() === String(channelName).toLowerCase());
    ctx.fillStyle = isBadDraft ? "#dc2626" : "#334155";
    ctx.font = isBadDraft ? "700 12px system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" : "12px system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif";
    ctx.fillText(isBadDraft ? `${channelName} *` : channelName, 18, centerY + 4);
    ctx.strokeStyle = isBadDraft ? "#dc2626" : palette[rowIndex % palette.length];
    ctx.lineWidth = 1.35;
    ctx.beginPath();
    samples.forEach((value, index) => {
      const sampleTime = Number(times[index] ?? (timeStart + ((timeEnd - timeStart) * index) / Math.max(1, samples.length - 1)));
      const x = timeToCanvasX(sampleTime, eegState.lastPlot);
      const y = centerY - Math.max(-rowHeight * 0.42, Math.min(rowHeight * 0.42, value * scale));
      if (index === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
  });

  const eventItems = [
    ...(Array.isArray(payload.events) ? payload.events : []),
    ...(Array.isArray(payload.annotations) ? payload.annotations : []).map((item) => ({
      time_sec: item.time_sec ?? item.onset,
      label: item.label || item.description || item.type || "事件",
      code: item.code || item.type || "",
    })),
  ].filter((item) => Number.isFinite(Number(item.time_sec ?? item.onset)));
  eventItems.slice(0, 80).forEach((item, index) => {
    const timeSec = Number(item.time_sec ?? item.onset);
    if (timeSec < timeStart || timeSec > timeEnd) return;
    const x = timeToCanvasX(timeSec, eegState.lastPlot);
    ctx.strokeStyle = "rgba(20, 184, 166, 0.72)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(x, top);
    ctx.lineTo(x, top + plotHeight);
    ctx.stroke();
    if (index < 10) {
      ctx.fillStyle = "#0f766e";
      ctx.font = "700 10px system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif";
      ctx.fillText(String(item.label || item.code || "事件").slice(0, 12), x + 4, top + 12 + (index % 4) * 13);
    }
  });

  ctx.fillStyle = "#0f172a";
  ctx.font = "700 14px system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif";
  const isFiltered = Boolean(payload.filter_preview_only);
  const title = isFiltered ? "预览滤波波形" : "EEG 波形预览";
  ctx.fillText(title, left, 24);
  ctx.fillStyle = "#64748b";
  ctx.font = "12px system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif";
  const sampleText = payload.display_sample_rate_hz || payload.sfreq_display ? `${payload.display_sample_rate_hz || payload.sfreq_display} Hz 显示采样` : "预览采样";
  const downsampleText = payload.downsampled ? ` · 已按 ${payload.downsample_method || "min/max"} 降采样显示` : "";
  ctx.fillText(`${visibleCount} 通道 · ${payload.unit || "uV"} · ${sampleText}${downsampleText} · ${isFiltered ? "滤波仅预览，不改写原始 EEG" : "原始波形，科研数据准备检查"}`, left + 120, 24);
  renderWaveformWorkbenchStatus();
  // 同步更新概览条上的当前窗口高亮框
  drawEegOverviewBar();
  return true;
}

function drawEegPreviewSkeleton(file = currentWorkspaceFile()) {
  const canvas = qs("#eegCanvas");
  const ctx = canvas?.getContext?.("2d");
  if (!canvas || !ctx) return false;
  qs("#eegEmpty")?.classList.remove("ready");
  const rect = canvas.getBoundingClientRect();
  const dpr = Math.max(1, window.devicePixelRatio || 1);
  const cssWidth = Math.max(720, Math.round(rect.width || canvas.clientWidth || 1280));
  const cssHeight = Math.max(360, Math.round(rect.height || canvas.clientHeight || 520));
  if (canvas.width !== Math.round(cssWidth * dpr) || canvas.height !== Math.round(cssHeight * dpr)) {
    canvas.width = Math.round(cssWidth * dpr);
    canvas.height = Math.round(cssHeight * dpr);
  }
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, cssWidth, cssHeight);
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, cssWidth, cssHeight);
  const left = 86;
  const right = 24;
  const top = 42;
  const bottom = 46;
  const plotWidth = Math.max(240, cssWidth - left - right);
  const plotHeight = Math.max(220, cssHeight - top - bottom);
  const channelCount = Math.max(1, Math.min(Number(eegState.visibleChannels || 8), Number(file?.channel_count || 8)));
  const rowHeight = plotHeight / channelCount;
  const timeStart = Number(eegState.start || 0);
  const timeEnd = timeStart + Number(eegState.windowSec || 10);
  eegState.lastPlot = { left, right, top, bottom, plotWidth, plotHeight, timeStart, timeEnd };
  const drawSkeletonBand = (segment, fillStyle, strokeStyle, label) => {
    const normalized = normalizeSegmentRange(segment?.start_sec, segment?.end_sec);
    if (!normalized || normalized.end_sec < timeStart || normalized.start_sec > timeEnd) return;
    const x = timeToCanvasX(normalized.start_sec, eegState.lastPlot);
    const w = Math.max(2, timeToCanvasX(normalized.end_sec, eegState.lastPlot) - x);
    ctx.fillStyle = fillStyle;
    ctx.fillRect(x, top, w, plotHeight);
    ctx.strokeStyle = strokeStyle;
    ctx.strokeRect(x, top, w, plotHeight);
    if (label) {
      ctx.fillStyle = strokeStyle;
      ctx.font = "700 11px system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif";
      ctx.fillText(label, x + 6, top + 16);
    }
  };
  prepEditState.excludedSegments.forEach((segment, index) => drawSkeletonBand(segment, "rgba(239, 68, 68, 0.16)", "rgba(220, 38, 38, 0.75)", index === 0 ? "坏段" : ""));
  if (eegState.selectedSegment) drawSkeletonBand(eegState.selectedSegment, "rgba(236, 72, 153, 0.14)", "rgba(219, 39, 119, 0.8)", "选段");
  ctx.strokeStyle = "#e5edf1";
  ctx.lineWidth = 1;
  ctx.font = "12px system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif";
  for (let i = 0; i <= 5; i += 1) {
    const x = left + (plotWidth * i) / 5;
    ctx.beginPath();
    ctx.moveTo(x, top);
    ctx.lineTo(x, top + plotHeight);
    ctx.stroke();
    ctx.fillStyle = "#64748b";
    ctx.fillText(`${(Number(eegState.start || 0) + (Number(eegState.windowSec || 10) * i) / 5).toFixed(1)} s`, x - 16, top + plotHeight + 24);
  }
  for (let row = 0; row < channelCount; row += 1) {
    const centerY = top + rowHeight * row + rowHeight / 2;
    ctx.strokeStyle = "#edf2f6";
    ctx.beginPath();
    ctx.moveTo(left, centerY);
    ctx.lineTo(left + plotWidth, centerY);
    ctx.stroke();
    ctx.fillStyle = "#94a3b8";
    ctx.fillText(`CH${row + 1}`, 18, centerY + 4);
  }
  ctx.fillStyle = "#0f172a";
  ctx.font = "700 14px system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif";
  ctx.fillText("正在准备 EEG 波形", left, 24);
  ctx.fillStyle = "#64748b";
  ctx.font = "12px system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif";
  ctx.fillText(`${eegFileDisplayName(file) || file?.original_filename || "当前数据"} · ${channelCount} 通道 · ${eegState.windowSec || 10} s 窗口`, left + 140, 24);
  renderWaveformWorkbenchStatus();
  renderWaveformInteractionHint();
  return true;
}

function renderEegPreviewMetadata(payload = currentWaveformPayload(), artifacts = []) {
  const meta = qs("#eegMeta");
  const isFiltered = Boolean(payload?.filter_preview_only);
  const start = Number(payload?.start_sec ?? eegState.start ?? 0);
  const duration = Number(payload?.duration_sec || eegState.windowSec || 10);
  const end = start + duration;
  const visibleCount = Math.min(Number(eegState.visibleChannels || 8), Number(payload?.channels?.length || 0));
  const filterSummary = formatPreviewFilterSummary();
  if (meta) {
    const items = [
      `当前窗口 ${start.toFixed(1)}-${end.toFixed(1)} s`,
      payload?.channels?.length ? `${visibleCount || payload.channels.length} / ${payload.channels.length} 个通道` : null,
      payload?.sfreq_display ? `${payload.sfreq_display} Hz 显示采样` : null,
      payload?.unit ? `单位 ${payload.unit}` : "单位 uV",
      isFiltered ? "预览滤波" : "原始波形",
      filterSummary,
      "不改写原始 EEG",
    ].filter(Boolean);
    meta.innerHTML = items.map((item) => `<span>${escapeHtml(item)}</span>`).join("");
  }
  const events = qs("#eegEvents");
  if (events) {
    const annotations = Array.isArray(payload?.annotations) ? payload.annotations : [];
    events.innerHTML = annotations.length
      ? annotations.slice(0, 8).map((item) => `<span>${escapeHtml(item.description || item.label || "annotation")} · ${Number(item.onset || 0).toFixed(2)} s</span>`).join("")
      : "<span>当前预览窗未发现事件标记</span>";
  }
  const strip = qs("#previewStrip");
  if (strip) {
    const chips = [
      ["当前窗口", `${start.toFixed(1)}-${end.toFixed(1)} s`],
      ["显示", `${visibleCount || payload?.channels?.length || 0} 通道 / ${payload?.sfreq_display || "预览"} Hz / ${payload?.unit || "uV"}`],
      ["波形", isFiltered ? "预览滤波" : "原始波形"],
      ["滤波参数", filterSummary.replace(/^滤波参数\s*/, "")],
      ["边界", "预览不改写原始 EEG"],
    ];
    strip.innerHTML = chips.map(([label, value], index) => `<button class="preview-chip${index === 0 ? " active" : ""}" type="button"><strong>${escapeHtml(label)}</strong><span>${escapeHtml(value)}</span></button>`).join("");
  }
}

async function loadWaveformPreviewFromTask(task, file = currentWorkspaceFile(), options = {}) {
  const requestSeq = Number(options.requestSeq || eegState.previewRequestSeq || 0);
  const artifacts = await fetchPreviewArtifactsWhenReady(task?.id, { needFilter: Boolean(eegState.showFiltered || eegState.filterEnabled) });
  if (requestSeq && requestSeq !== eegState.previewRequestSeq) {
    return currentWaveformPayload();
  }
  state.real.artifacts.qc = artifacts;
  const waveformArtifact = waveformArtifactFromList(artifacts);
  if (!waveformArtifact) throw new Error("后端已生成 QC 任务，但没有返回波形预览文件。");
  const payload = normalizeWaveformPreview(await fetchArtifactJson(waveformArtifact));
  const filterArtifact = filterPreviewArtifactFromList(artifacts);
  let filterPayload = null;
  if (filterArtifact) {
    const rawFilterPayload = await fetchArtifactJson(filterArtifact);
    if (Array.isArray(rawFilterPayload?.data_uv) && rawFilterPayload.data_uv.length) {
      filterPayload = normalizeWaveformPreview(rawFilterPayload);
    }
  }
  eegState.data = payload;
  eegState.filteredData = filterPayload;
  if (eegState.showFiltered && !filterPayload) eegState.showFiltered = false;
  eegState.events = Array.isArray(payload.annotations) ? payload.annotations : [];
  eegState.sourceName = eegFileDisplayName(file) || file?.original_filename || file?.id || "EEG 数据";
  eegState.taskId = task?.id || "";
  eegState.selectedFilePreviewId = file?.id || "";
  eegState.autoPreviewError = "";
  syncEegControlsFromState();
  const currentPayload = currentWaveformPayload();
  drawEegWaveformPreview(currentPayload);
  renderEegPreviewMetadata(currentPayload, artifacts);
  renderEegPreviewEmptyState();
  // 加载全时程概览条数据（异步，不阻塞波形渲染）
  loadEegOverview(file).catch(() => null);
  return currentPayload;
}

function renderRealFlowSummary() {
  const file = currentWorkspaceFile();
  const target = qs("#prepContextSummary");
  if (target?.closest?.("#dashboard")) return;
  if (target) {
    const projectName = state.real.project?.name || state.real.project?.title || "未选择项目";
    const fileName = file?.original_filename || file?.source_name || "未选择数据";
    const prepState = state.real.epochSet?.id
      ? `事件分段已保存，修订版本 ${state.real.epochSet.revision || 1}`
      : state.real.plan?.id
        ? `准备方案已确认，修订版本 ${state.real.plan.revision || 1}`
        : "准备方案尚未确认";
    target.textContent = `当前项目：${projectName}；当前数据：${fileName}；${prepState}。`;
  }
}

async function runQcPreviewFromUi(options = {}) {
  const eegFile = currentWorkspaceFile();
  if (!eegFile?.id) {
    throw new Error("请先在项目中选择并上传 EEG 数据，再生成基础质量预览。");
  }
  const project = state.real.project || await ensureRealProject();
  const requestSeq = eegState.previewRequestSeq + 1;
  eegState.previewRequestSeq = requestSeq;
  const parameters = buildQcPreviewParametersFromUi(options);
  setRealStatus("正在更新当前波形预览。", "info");
  drawEegPreviewSkeleton(eegFile);
  const task = await apiJson("/tasks", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      project_id: project.id,
      input_file_id: eegFile.id,
      module_name: "qc",
      workflow_id: "qc_waveform_preview",
      parameters_json: parameters,
      owner_user_id: currentAccountId(),
      created_by: currentAccountId(),
    }),
  });
  if (requestSeq !== eegState.previewRequestSeq) return task;
  state.real.tasks.qc = task;
  await loadWaveformPreviewFromTask(task, eegFile, { requestSeq });
  if (requestSeq !== eegState.previewRequestSeq) return task;
  setRealStatus("波形预览已更新，可以看着波形修订片段、标签、坏道和预处理参数。", "ok");
  revealWaveformPreview({ delayMs: 120 });
  return task;
}

async function requestAutoQcPreviewForSelectedFile(file = currentWorkspaceFile()) {
  if (!file?.id || eegState.autoPreviewInFlight) return null;
  if (eegState.selectedFilePreviewId === file.id && state.real.tasks.qc?.id) return state.real.tasks.qc;
  eegState.autoPreviewInFlight = true;
  eegState.autoPreviewError = "";
  renderEegPreviewEmptyState();
  try {
    const task = await runQcPreviewFromUi({ fastUiPreview: true });
    eegState.selectedFilePreviewId = file.id;
    renderEegPreviewEmptyState();
    recordUiAction("real:auto-qc-preview", "pass", `已自动为 ${eegFileDisplayName(file) || file.id} 生成预览证据。`, {
      file_id: file.id,
      task_id: task?.id,
      trigger: "select_file",
    });
    return task;
  } catch (error) {
    eegState.autoPreviewError = error.message || String(error);
    recordUiAction("real:auto-qc-preview", "blocked", `自动预览未完成：${eegState.autoPreviewError}`, {
      file_id: file.id,
      trigger: "select_file",
    });
    throw error;
  } finally {
    eegState.autoPreviewInFlight = false;
    renderEegPreviewEmptyState();
  }
}

async function runMetadataQcFromUi() {
  const eegFile = currentWorkspaceFile();
  if (!eegFile?.id) {
    throw new Error("请先在项目中选择并上传 EEG 数据，再检查数据基础信息。");
  }
  const project = state.real.project || await ensureRealProject();
  setRealStatus("正在检查数据基础信息。", "info");
  const task = await apiJson("/tasks", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      project_id: project.id,
      input_file_id: eegFile.id,
      module_name: "qc",
      workflow_id: "metadata_qc",
      parameters_json: {
        boundary: "research preprocessing metadata check only; non-diagnostic",
      },
      owner_user_id: currentAccountId(),
      created_by: currentAccountId(),
    }),
  });
  state.real.tasks.qc_metadata = task;
  setRealStatus(`数据概况已更新：${task.id}`, "ok");
  return task;
}

function buildEpochSetManifestDraft() {
  const parameters = collectPresetParameters("erp");
  const events = Array.isArray(eegState.events) ? eegState.events : [];
  const standardCount = events.filter((event) => String(event.type) === String(parameters.event_id?.standard)).length;
  const targetCount = events.filter((event) => String(event.type) === String(parameters.event_id?.target)).length;
  const totalMappedEvents = standardCount + targetCount;
  const duration = parameters.tmax - parameters.tmin;
  const estimatedEpochCount = totalMappedEvents;
  return {
    schema_version: "qlanalyser-epoch-set-manifest-draft-v0.1",
    epoch_set_id: `epoch_ui_${Date.now()}`,
    source: "main_workbench_event_epoch_panel",
    analysis_scope: "event",
    event_id: parameters.event_id,
    event_mapping: [
      { condition: "standard", event_code: parameters.event_id?.standard, event_count: standardCount },
      { condition: "target", event_code: parameters.event_id?.target, event_count: targetCount },
    ],
    event_count: totalMappedEvents,
    estimated_epoch_count: estimatedEpochCount,
    tmin: parameters.tmin,
    tmax: parameters.tmax,
    baseline: parameters.baseline,
    l_freq: parameters.l_freq,
    h_freq: parameters.h_freq,
    epoch_window_seconds: Number.isFinite(duration) ? duration : null,
    drop_log_preview: [
      {
        reason: "ui_preview_only",
        count: 0,
        note: "Full exclusion summary is produced by the ERP task result files after analysis processing.",
      },
    ],
    manifest_preview_ui: true,
    boundary: "Single-record sensor-space research workflow manifest draft; not for clinical diagnosis, source localization, or causal inference.",
  };
}

function refreshEpochSetPreview() {
  const manifest = buildEpochSetManifestDraft();
  const setId = qs('[data-testid="epoch-set-id"]');
  if (setId) setId.textContent = `事件分段：待保存；事件 ${manifest.event_count} 个；窗口 ${manifest.tmin} 到 ${manifest.tmax} s；baseline ${manifest.baseline?.[0]} 到 ${manifest.baseline?.[1]} s。`;
  const standardCode = qs('[data-epoch-preview="standard-code"]');
  const targetCode = qs('[data-epoch-preview="target-code"]');
  const standardCount = qs('[data-epoch-preview="standard-count"]');
  const targetCount = qs('[data-epoch-preview="target-count"]');
  if (standardCode) standardCode.textContent = String(manifest.event_id?.standard ?? "");
  if (targetCode) targetCode.textContent = String(manifest.event_id?.target ?? "");
  if (standardCount) standardCount.textContent = `${manifest.event_mapping?.[0]?.event_count ?? 0} 个事件`;
  if (targetCount) targetCount.textContent = `${manifest.event_mapping?.[1]?.event_count ?? 0} 个事件`;
  const dropLog = qs('[data-testid="epoch-preview-drop-log"]');
  if (dropLog) {
    dropLog.textContent = `剔除记录预览：预计 epoch ${manifest.estimated_epoch_count} 个；完整剔除记录会在 ERP 任务产物中生成。`;
  }
  const preview = qs('[data-testid="epoch-set-manifest-preview"]');
  if (preview) {
    preview.textContent = `事件 ${manifest.event_count} 个；预计分段 ${manifest.estimated_epoch_count} 个；窗口 ${manifest.tmin} 到 ${manifest.tmax} s；baseline ${manifest.baseline?.[0]} 到 ${manifest.baseline?.[1]} s。完整处理记录可通过下载按钮获取。`;
  }
  return manifest;
}

function epochSetToManifest(epochSet) {
  if (!epochSet) return refreshEpochSetPreview();
  return {
    ...epochSet,
    epoch_set_id: epochSet.id,
    source: "persistent epoch_set registry via visible UI",
    persisted: true,
  };
}

function renderPersistedEpochSet(epochSet) {
  state.real.epochSet = epochSet;
  const manifest = epochSetToManifest(epochSet);
  const setId = qs('[data-testid="epoch-set-id"]');
  if (setId) setId.textContent = `事件分段已保存：修订版本 ${manifest.revision || 1}；事件映射和来源记录已记录。`;
  const preview = qs('[data-testid="epoch-set-manifest-preview"]');
  if (preview) {
    preview.textContent = `事件分段已保存；修订版本 ${manifest.revision || 1}；事件 ${manifest.event_count || 0} 个；预计分段 ${manifest.estimated_epoch_count || 0} 个。完整处理记录可通过下载按钮获取。`;
  }
  const dropLog = qs('[data-testid="epoch-preview-drop-log"]');
  if (dropLog) {
    dropLog.textContent = `剔除记录预览：已保存 ${manifest.drop_log_preview?.length || 0} 条摘要；修订版本 ${manifest.revision || 1}。`;
  }
  return manifest;
}

async function saveEpochSetFromUi() {
  const eegFile = currentWorkspaceFile();
  if (!eegFile?.id || !state.real.project?.id) {
    throw new Error("请先选择或上传 EEG 数据，再保存事件与片段。");
  }
  const plan = state.real.plan || await getCurrentDataPreparationPlan(eegFile);
  if (!plan?.id || plan.is_default || plan.status !== "confirmed") {
    throw new Error("请先确认数据准备方案，再保存事件与片段。");
  }
  const draft = refreshEpochSetPreview();
  if (!Number.isFinite(Number(draft.event_count)) || Number(draft.event_count) <= 0) {
    throw new Error("当前数据没有可用事件，ERP 暂不能运行。请先确认事件标记。");
  }
  const payload = {
    organization_id: eegFile.organization_id || "local-org",
    project_id: state.real.project.id,
    input_file_id: eegFile.id,
    owner_user_id: currentAccountId(),
    created_by: currentAccountId(),
    status: "confirmed",
    schema_version: "qlanalyser-epoch-set-manifest-v0.1",
    title: "ERP/P300 epoch set",
    data_preparation_plan_id: plan.id,
    data_preparation_revision: plan.revision,
    event_id: draft.event_id,
    event_mapping: draft.event_mapping,
    event_count: draft.event_count,
    estimated_epoch_count: draft.estimated_epoch_count,
    tmin: draft.tmin,
    tmax: draft.tmax,
    baseline: draft.baseline,
    l_freq: draft.l_freq,
    h_freq: draft.h_freq,
    drop_log_preview: draft.drop_log_preview,
    boundary: "Single-record sensor-space research workflow; not for clinical diagnosis, source localization, or causal inference.",
    lineage_json: {
      ui_surface: "event-epoch-panel",
      data_preparation_plan_id: plan.id,
      data_preparation_revision: plan.revision,
      source_file_id: eegFile.id,
      manifest_preview_schema: draft.schema_version,
    },
    artifact_contract_json: {
      required_fields: ["epoch_set_id", "修订版本", "event_mapping", "baseline", "drop_log_preview", "boundary", "lineage_json"],
    },
  };
  const epochSet = await apiJson(`/eeg/files/${encodeURIComponent(eegFile.id)}/epoch-sets`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  renderPersistedEpochSet(epochSet);
  setRealStatus("事件分段已保存，可以继续选择分析方法。", "ok");
  await refreshProjectWorkspace();
  return epochSet;
}

async function saveBadChannelAuditFromUi(decision = "save") {
  const eegFile = currentWorkspaceFile();
  if (!eegFile?.id || !state.real.project?.id) {
    throw new Error("请先选择或上传 EEG 数据，再保存坏道修改。");
  }
  const plan = state.real.plan || await getCurrentDataPreparationPlan(eegFile);
  if (!plan?.id || plan.is_default || plan.status !== "confirmed") {
    throw new Error("请先确认数据准备方案，再保存或恢复坏道修改。");
  }
  const firstChannel =
    currentWaveformPayload()?.channels?.[0] ||
    eegState.data?.channelNames?.[0] ||
    eegFile.channel_names?.[0] ||
    "EEG001";
  const pending = decision === "save"
    ? prepEditState.badChannels
    : prepEditState.restoredBadChannels;
  if (!pending.length) {
    throw new Error(decision === "save" ? "请先在波形旁标记坏道，再保存修改。" : "当前没有待保存的坏道恢复记录。");
  }
  const changedChannels = pending.map((item) => ({
    channel: String(item.channel || firstChannel),
    previous_status: item.previous_status || (decision === "save" ? "good" : "bad"),
    new_status: decision === "save" ? "bad" : "good",
    reason: item.reason || (decision === "save" ? "看波形后标记为待复核坏道" : "恢复坏道临时修改"),
    note: "Research data-preparation audit only; not a clinical judgment.",
  }));
  if (decision === "save") {
    renderPreparationEditSummary(`坏道修改已准备保存：${changedChannels.map((item) => item.channel).join(", ")}。`);
  } else {
    renderPreparationEditSummary(`坏道恢复记录已准备保存：${changedChannels.map((item) => item.channel).join(", ")}。`);
  }
  const audit = await apiJson(`/eeg/files/${encodeURIComponent(eegFile.id)}/bad-channel-audit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      organization_id: eegFile.organization_id || "local-org",
      project_id: state.real.project.id,
      input_file_id: eegFile.id,
      plan_id: plan.id,
      plan_revision: plan.revision,
      actor_user_id: currentAccountId(),
      session_id: currentAuthToken() ? "authenticated-ui-session" : "local-ui-session",
      decision,
      changed_channels: changedChannels,
      reason: "Visible waveform-based bad-channel review",
      note: "Records save/discard decision, channel status before/after, actor/session, and provenance. Not diagnostic.",
      provenance_json: {
        ui_surface: "preprocessing-inline-panel",
        data_preparation_plan_id: plan.id,
        data_preparation_revision: plan.revision,
        source_file_id: eegFile.id,
        bad_channel_history: prepEditState.badChannelHistory,
      },
    }),
  });
  state.real.badChannelAudit = audit;
  setRealStatus(decision === "save" ? "坏道修改已保存，可在当前修改记录中恢复。" : "坏道修改已恢复。", "ok");
  return audit;
}

async function apiUpload(path, formData) {
  const response = await fetch(`${state.apiBase}${path}`, {
    method: "POST",
    headers: withAuthHeaders(),
    body: formData,
  });
  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    const message = typeof data === "string" ? data : data.detail || data.message || "Upload failed";
    throw new Error(message);
  }
  return data;
}

async function refreshProjectWorkspace() {
  const [projects, files] = await Promise.all([
    apiJson("/projects"),
    apiJson("/data/files"),
  ]);
  state.workspace.projects = Array.isArray(projects) ? projects : [];
  state.workspace.files = Array.isArray(files) ? files : [];
  preserveTeachingWorkspaceSelection();
  const selectedProjectId = state.workspace.selectedProjectId || null;
  let project = selectedProjectId
    ? state.workspace.projects.find((item) => item.id === selectedProjectId) || (state.real.project?.id === selectedProjectId ? state.real.project : null)
    : null;
  if (
    project?.id
    && isCustomerTrialP0Mode()
    && !state.teaching.active
    && !state.workspace.showReviewProjects
    && !state.workspace.sessionProjectIds?.has?.(project.id)
  ) {
    project = null;
    state.real.project = null;
    state.workspace.selectedProjectId = null;
    state.workspace.selectedFileId = null;
    state.workspace.selectedPlanId = null;
  }
  if (project?.id && !state.workspace.showReviewProjects && isHiddenFromCustomerProjectList(project)) {
    project = null;
    state.workspace.selectedProjectId = null;
    state.workspace.selectedFileId = null;
    state.workspace.selectedPlanId = null;
  }
  const projectFiles = scopedProjectFiles(project, state.workspace.files);
  const selectedFileId = project?.id ? state.workspace.selectedFileId || null : null;
  const file = project?.id
    ? (selectedFileId ? projectFiles.find((item) => item.id === selectedFileId) : null)
      || (state.real.eegFile?.project_id === project.id ? state.real.eegFile : null)
    : null;
  state.real.project = project;
  state.real.eegFile = file;
  if (file?.id) {
    let plans = [];
    let epochSets = [];
    try {
      [plans, epochSets] = await Promise.all([
        apiJson(`/data-preparation/plans?input_file_id=${encodeURIComponent(file.id)}`),
        apiJson(`/eeg/files/${encodeURIComponent(file.id)}/epoch-sets`),
      ]);
    } catch (error) {
      if (!isTeachingDemoFile(file)) throw error;
      plans = state.real.plan?.input_file_id === file.id ? [state.real.plan] : [];
      epochSets = state.real.epochSet?.input_file_id === file.id ? [state.real.epochSet] : [];
    }
    state.workspace.plans = Array.isArray(plans) ? plans : [];
    state.workspace.epochSets = Array.isArray(epochSets) ? epochSets : [];
    preserveTeachingWorkspaceSelection();
    const selectedPlanId = state.workspace.selectedPlanId || state.real.plan?.id || null;
    const plan = selectedPlanId
      ? state.workspace.plans.find((item) => item.id === selectedPlanId) || (state.real.plan?.id === selectedPlanId ? state.real.plan : null)
      : state.real.plan?.id && state.real.plan.input_file_id === file.id
        ? state.real.plan
        : null;
    const epochSet = state.real.epochSet?.input_file_id === file.id ? state.real.epochSet : null;
    state.real.plan = plan;
    state.real.epochSet = epochSet;
  } else {
    state.workspace.plans = [];
    state.workspace.epochSets = [];
    state.real.plan = null;
    state.real.epochSet = null;
  }
  state.workspace.selectedProjectId = project?.id || null;
  state.workspace.selectedFileId = file?.id || null;
  state.workspace.selectedPlanId = state.real.plan?.id || null;
  preserveTeachingWorkspaceSelection();
  renderProjectDataManagement();
  renderRealPlanState();
  renderRealFlowSummary();
  updateRealActionGate();
  publishE2EState();
  return { projects: state.workspace.projects, files: state.workspace.files, plans: state.workspace.plans, epochSets: state.workspace.epochSets };
}

function workspaceProjectOptions(projects, files = []) {
  return projects.map((project) => {
    const label = projectDisplayName(project) || project.id;
    const scope = projectOptionScopeLabel(project, files);
    const status = projectStatusLabelReadable(project, files);
    const shortId = String(project.id || "").slice(-6);
    const suffix = [status, shortId ? `#${shortId}` : ""].filter(Boolean).join(" · ");
    return `<option value="${escapeHtml(project.id)}">${escapeHtml(label)} · ${escapeHtml(scope)}${suffix ? ` · ${escapeHtml(suffix)}` : ""}</option>`;
  }).join("");
}

function workspaceFileOptions(files) {
  return activeWorkspaceFiles(files).map((item) => {
    const status = fileStatusLabelReadable(item);
    const shortId = String(item.id || "").slice(-6);
    const suffix = [status, shortId ? `#${shortId}` : ""].filter(Boolean).join(" · ");
    return `<option value="${escapeHtml(item.id)}">${escapeHtml(eegFileDisplayName(item))}${suffix ? ` · ${escapeHtml(suffix)}` : ""}</option>`;
  }).join("");
}

async function ensureRealProject() {
  if (state.real.project) return state.real.project;
  const now = new Date();
  const stamp = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")} ${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
  const projectName = qs("#realProjectName")?.value.trim() || `未命名 EEG 项目 ${stamp}`;
  const project = await apiJson("/projects", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: projectName,
      description: "用户创建的 EEG 研究项目",
      research_type: "research_eeg",
      owner_id: currentAccountId(),
      created_by: currentAccountId(),
    }),
  });
  state.real.project = project;
  state.workspace.sessionProjectIds?.add?.(project.id);
  state.real.eegFile = null;
  state.real.plan = null;
  state.real.epochSet = null;
  state.workspace.selectedProjectId = project.id;
  state.workspace.selectedFileId = null;
  setRealStatus(`\u9879\u76ee\u5df2\u521b\u5efa\uff1a${project.id}`, "ok");
  await refreshProjectWorkspace();
  return project;
}

async function uploadRealEeg() {
  const file = qs("#real-eeg-file")?.files?.[0];
  if (!file) throw new Error("\u8bf7\u5148\u9009\u62e9 EEG \u6570\u636e\u6587\u4ef6\uff0c\u518d\u4e0a\u4f20\u5230\u5f53\u524d\u9879\u76ee\u3002");
  const project = await ensureRealProject();
  const form = new FormData();
  form.append("file", file);
  const uploadAuthorizationText = "Uploader confirms authorization to upload this EEG file for QLanalyser cloud trial research analysis and candidate event screening.";
  const uploadUrl = `/eeg/upload?project_id=${encodeURIComponent(project.id)}&upload_authorization_confirmed=true&upload_authorization_text=${encodeURIComponent(uploadAuthorizationText)}`;
  const uploaded = await apiJson(uploadUrl, {
    method: "POST",
    body: form,
  });
  state.real.eegFile = uploaded;
  state.workspace.selectedProjectId = project.id;
  state.workspace.selectedFileId = uploaded.id;
  refreshEpochSetPreview();
  setRealStatus(`\u6587\u4ef6\u5df2\u4e0a\u4f20\uff1a${uploaded.id}`, "ok");
  await refreshProjectWorkspace();
  state.real.eegFile = uploaded;
  state.workspace.selectedProjectId = project.id;
  state.workspace.selectedFileId = uploaded.id;
  renderProjectDataManagement();
  setView("analysis");
  updateRealActionGate();
  return uploaded;
}

async function getCurrentDataPreparationPlan(eegFile) {
  if (!eegFile?.id) return null;
  try {
    const plans = await apiJson(`/data-preparation/plans?input_file_id=${encodeURIComponent(eegFile.id)}`);
    if (!Array.isArray(plans) || !plans.length) return null;
    return plans
      .filter((plan) => !plan.is_default)
      .sort((a, b) => {
        const bTime = Date.parse(b.updated_at || b.created_at || "") || 0;
        const aTime = Date.parse(a.updated_at || a.created_at || "") || 0;
        if (bTime !== aTime) return bTime - aTime;
        return Number(b.revision || 0) - Number(a.revision || 0);
      })[0] || plans[0];
  } catch (error) {
    return null;
  }
}

async function confirmRealDataPreparationPlan(options = {}) {
  const project = await ensureRealProject();
  const eegFile = currentWorkspaceFile() || (options.allowUpload === false ? null : await uploadRealEeg());
  if (!eegFile?.id) throw new Error("\u8bf7\u5148\u9009\u62e9 EEG \u6570\u636e\u3002");
  const current = await getCurrentDataPreparationPlan(eegFile);
  const baseRevision = Number.isInteger(current?.revision) ? current.revision : 0;
  const plan = await apiJson("/data-preparation/plans", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      project_id: project.id,
      input_file_id: eegFile.id,
      base_revision: baseRevision,
      status: "confirmed",
      module_scope: ["qc", "psd", "erp"],
      source_file: {
        file_id: eegFile.id,
        original_filename: eegFile.original_filename,
        detected_format: eegFile.detected_format,
        size_bytes: eegFile.size_bytes,
        sha256: eegFile.sha256,
      },
      metadata_review: {
        sampling_rate: eegFile.sampling_rate,
        channel_count: eegFile.channel_count,
        duration_sec: eegFile.duration_sec,
      },
      qc_json: {
        confirmed_from: "production_workflow",
        qc_task_id: state.real.tasks.qc?.id || null,
        pending_edits: {
          excluded_segments: prepEditState.excludedSegments,
          restored_segments: prepEditState.restoredSegments,
          labels: prepEditState.labels,
          restored_labels: prepEditState.restoredLabels,
          bad_channels: prepEditState.badChannels,
          restored_bad_channels: prepEditState.restoredBadChannels,
          bad_channel_history: prepEditState.badChannelHistory,
        },
      },
      preprocessing_json: {
        reference: qs("#presetPrepReference")?.value || "average",
        reference_mode: qs("#presetPrepReference")?.value || "average",
        reference_channels: splitListFromInput("#presetPrepReferenceChannels"),
        bipolar_pairs: splitListFromInput("#presetPrepBipolarPairs", ";").map((pair) => pair.split("-").map((item) => item.trim()).filter(Boolean)),
        notch_freq: numberFromInput("#presetPrepNotch", 50),
        l_freq: numberFromInput("#presetPrepLfreq", 0.5),
        h_freq: numberFromInput("#presetPrepHfreq", 40),
        filter_preview_only: true,
        preview_parameters: eegState.lastPreviewParameters || buildQcPreviewParametersFromUi(),
      },
      artifact_contract_json: {
        ui_surface: "preprocessing-inline-panel",
        required_followups: ["event_epoch_standalone_management", "drop_log_preview", "epoch_set_manifest"],
        boundary: "single-record research workflow; preview operations do not modify the uploaded EEG file and are not for clinical diagnosis",
      },
      next_step_recommendation: {
        psd: { status: "allowed", reasons: [] },
        erp: { status: "allowed_after_event_review", reasons: [] },
      },
    }),
  });
  state.real.plan = plan;
  renderRealPlanState();
    await refreshProjectWorkspace();
return plan;
}

async function bootstrapEpilepsyDeepLinkWorkbench(reason = "deeplink") {
  if (!isEpilepsyWorkbenchDeepLinkIntent()) return false;
  if (state.deepLink.epilepsyBootstrapInFlight) return true;
  state.deepLink.epilepsyBootstrapInFlight = true;
  state.deepLink.epilepsyBootstrapStatus = "running";
  state.deepLink.epilepsyBootstrapError = "";
  state.teaching.active = true;
  state.teaching.guideActive = false;
  hideTeachingGuideOverlay();
  applyTeachingModeChrome();
  setView("epilepsyWorkbenchInline");
  renderInlineEpilepsyWorkbench();
  setRealStatus("正在进入癫痫样候选事件复核预览：自动准备示例 EDF 数据。", "info");
  try {
    await loadTeachingDatasetForModule("epilepsy_ml");
    await ensureTeachingSandboxReady({ preview: false, moduleName: "epilepsy_ml" });
    setView("epilepsyWorkbenchInline");
    renderInlineEpilepsyWorkbench();
    state.deepLink.epilepsyBootstrapStatus = "ready";
    recordUiAction("epilepsy:deeplink-bootstrap", "pass", "已进入癫痫样候选事件复核预览，并加载示例 EDF 数据。", {
      reason,
      project_id: state.real.project?.id || "",
      file_id: state.real.eegFile?.id || "",
      plan_id: state.real.plan?.id || "",
    });
    return true;
  } catch (error) {
    state.deepLink.epilepsyBootstrapStatus = "failed";
    state.deepLink.epilepsyBootstrapError = error?.message || String(error);
    setView("epilepsyWorkbenchInline");
    renderInlineEpilepsyWorkbench();
    recordUiAction("epilepsy:deeplink-bootstrap", "blocked", state.deepLink.epilepsyBootstrapError);
    showToast(`进入癫痫样候选事件复核预览未完成：${state.deepLink.epilepsyBootstrapError}`);
    return false;
  } finally {
    state.deepLink.epilepsyBootstrapInFlight = false;
    hideTeachingGuideOverlay();
    applyTeachingModeChrome();
    publishE2EState();
  }
}

async function ensureTeachingSandboxReady(options = {}) {
  if (!state.teaching.active) return null;
  const moduleName = options.moduleName || options.module || "";
  if (moduleName === "epilepsy_ml" && (!state.real.eegFile?.id || state.real.eegFile.id !== "eeg_demo_epilepsy_high_amplitude")) {
    await loadTeachingDatasetForModule("epilepsy_ml");
  }
  if (!state.real.project?.id || !state.real.eegFile?.id || !state.teaching.datasetLoaded) {
    await startTeachingMode({ showGuide: false });
  }
  const eegFile = currentWorkspaceFile();
  if (!eegFile?.id) throw new Error("\u6559\u5b66\u6a21\u5f0f\u672a\u80fd\u52a0\u8f7d\u5185\u7f6e\u8111\u7535\u6570\u636e\uff0c\u8bf7\u91cd\u65b0\u8fdb\u5165\u6559\u5b66\u6a21\u5f0f\u3002");
  if (moduleName === "epilepsy_ml" && state.real.plan?.input_file_id && state.real.plan.input_file_id !== eegFile.id) {
    state.real.plan = null;
    state.workspace.selectedPlanId = "";
  }
  let plan = state.real.plan || await getCurrentDataPreparationPlan(eegFile);
  if (!plan || plan.is_default || plan.status !== "confirmed") {
    plan = await confirmRealDataPreparationPlan({ allowUpload: false });
    recordUiAction("teaching:auto-confirm-plan", "pass", "\u6559\u5b66\u6a21\u5f0f\u5df2\u81ea\u52a8\u51c6\u5907\u5185\u7f6e\u6570\u636e\uff0c\u53ef\u76f4\u63a5\u8bd5\u8dd1\u5206\u6790\u65b9\u6cd5\u3002", {
      project_id: state.real.project?.id,
      file_id: eegFile.id,
      plan_id: plan?.id,
    });
  }
  state.real.plan = plan;
  if (options.preview !== false) requestAutoQcPreviewForSelectedFile(eegFile).catch(() => null);
  updateRealActionGate();
  return plan;
}

function numberFromInput(selector, fallback = undefined) {
  const raw = qs(selector)?.value;
  if (raw === undefined || raw === null || raw === "") return fallback;
  const value = Number(raw);
  return Number.isFinite(value) ? value : fallback;
}

function splitListFromInput(selector, separator = ",") {
  const raw = String(qs(selector)?.value || "").trim();
  if (!raw) return [];
  const pieces = separator === ";" ? raw.split(/[;\n]+/) : raw.split(/[,，;\n]+/);
  return pieces.map((item) => item.trim()).filter(Boolean);
}

function stripUndefined(value) {
  if (Array.isArray(value)) return value.map(stripUndefined);
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.entries(value).filter(([, item]) => item !== undefined).map(([key, item]) => [key, stripUndefined(item)]));
  }
  return value;
}

function collectPresetParameters(moduleName) {
  if (moduleName === "psd") {
    return stripUndefined({
      fmin: numberFromInput("#presetPsdFmin", 1),
      fmax: numberFromInput("#presetPsdFmax", 40),
      l_freq: numberFromInput("#presetPsdLfreq"),
      h_freq: numberFromInput("#presetPsdHfreq"),
      notch_freq: numberFromInput("#presetPsdNotch"),
      include_channel_table: Boolean(qs("#presetPsdChannelTable")?.checked),
    });
  }
  if (moduleName === "erp") {
    return stripUndefined({
      event_id: {
        standard: numberFromInput("#presetErpStandard", 1),
        target: numberFromInput("#presetErpTarget", 2),
      },
      event_id_confirmed: true,
      tmin: numberFromInput("#presetErpTmin", -0.2),
      tmax: numberFromInput("#presetErpTmax", 0.8),
      baseline: [numberFromInput("#presetErpBaselineStart", -0.2), numberFromInput("#presetErpBaselineEnd", 0)],
      l_freq: numberFromInput("#presetErpLfreq", 0.1),
      h_freq: numberFromInput("#presetErpHfreq", 30),
      reference: "average",
    });
  }
  if (moduleName === "tfr") {
    return stripUndefined({
      event_id: "",
      tmin: -0.2,
      tmax: 0.8,
      baseline: [-0.2, 0],
      freqs: [8, 13, 30],
      n_cycles: 3,
      decim: 2,
      return_itc: true,
    });
  }
  if (moduleName === "multitaper_psd") {
    return stripUndefined({
      analysis_family: "psd",
      fmin: 1,
      fmax: 40,
      bandwidth: 4,
      low_bias: true,
      normalization: "length",
      remove_dc: true,
    });
  }
  if (moduleName === "multitaper_tfr") {
    return stripUndefined({
      analysis_family: "tfr",
      event_id: "",
      tmin: -0.2,
      tmax: 0.8,
      baseline: [-0.2, 0],
      baseline_mode: "logratio",
      freqs: [8, 13, 30],
      n_cycles: 7,
      time_bandwidth: 4,
      decim: 1,
      return_itc: true,
      use_fft: true,
      zero_mean: true,
    });
  }
  if (moduleName === "reference_csd") {
    return stripUndefined({
      reference_mode: "csd",
      bipolar_pairs: [],
      preview: {
        start_sec: 0,
        duration_sec: 8,
        channels: [],
      },
      csd: {
        sphere: "auto",
        lambda2: 0.00001,
        stiffness: 4,
        n_legendre_terms: 50,
      },
    });
  }
  if (moduleName === "pac") {
    return stripUndefined({
      phase_freqs: [4, 6, 8],
      phase_band_width: 2,
      amp_freqs: [70, 90, 110],
      amp_band_width: 20,
      n_phase_bins: 18,
      time_window: { start_sec: 0, end_sec: 20 },
      dynamic_window_sec: 8,
      dynamic_step_sec: 4,
    });
  }
  if (moduleName === "connectivity") {
    return stripUndefined({
      method: "correlation",
      fmin: 8,
      fmax: 12,
      segment_length_sec: 4,
      edge_top_n: 20,
      reference: "current_recording",
    });
  }
  return {};
}

function backendTaskModuleName(moduleName) {
  if (moduleName === "multitaper_psd" || moduleName === "multitaper_tfr") return "multitaper_psd_tfr";
  return moduleName;
}

function buildTaskParameters(moduleName, plan) {
  const parameters = { non_medical_scope: "research_screening_support_only" };
  Object.assign(parameters, collectPresetParameters(moduleName));
  if (plan && !plan.is_default && plan.id && Number.isFinite(Number(plan.revision))) {
    parameters.data_preparation_plan_id = plan.id;
    parameters.data_preparation_revision = Number(plan.revision);
    parameters.data_preparation_contract_version = dataPreparationContractVersion(plan);
  }
  // TFR 跟随波形窗口：注入当前阅片窗的起点和时间窗给后端裁剪
  if (moduleName === "tfr") {
    const file = currentWorkspaceFile();
    const fileDur = Number(file?.duration_sec || 0);
    if (fileDur > 0) {
      const startSec = Number(eegState.start || 0);
      const windowSec = Number(eegState.windowSec || 10);
      parameters.analysis_window = {
        start_sec: Math.max(0, Math.min(startSec, fileDur - windowSec)),
        duration_sec: Math.min(windowSec, fileDur),
      };
    }
  }
  return parameters;
}

function estimateEpilepsyScreeningSeconds(eegFile = {}) {
  const sizeBytes = Number(eegFile.size_bytes || eegFile.file_size_bytes || eegFile.size || 0);
  const durationSec = Number(eegFile.duration_sec || eegFile.duration_seconds || 0);
  if (sizeBytes >= 1_000_000_000 || durationSec >= 60 * 60 * 12) return 300;
  if (sizeBytes >= 250_000_000 || durationSec >= 60 * 60 * 2) return 120;
  if (durationSec >= 20 * 60 || sizeBytes >= 25_000_000) return 45;
  return 15;
}

function startInlineEpilepsyProgressHeartbeat(eegFile = {}) {
  const estimatedSec = estimateEpilepsyScreeningSeconds(eegFile);
  const startedAt = Date.now();
  window.clearInterval(state.epilepsyInline.progressTimer);
  state.epilepsyInline.progressTimer = window.setInterval(() => {
    const elapsedSec = Math.max(0, (Date.now() - startedAt) / 1000);
    const ratio = Math.min(0.88, elapsedSec / Math.max(10, estimatedSec));
    const progress = Math.max(28, Math.min(68, Math.round(28 + ratio * 40)));
    const longHint = estimatedSec >= 120
      ? "长记录正在本地分块提取特征，页面没有卡死；请保持本页打开。"
      : "正在分块提取特征并生成候选事件。";
    setInlineEpilepsyScreeningProgress("running", progress, longHint);
  }, 2500);
  return () => {
    window.clearInterval(state.epilepsyInline.progressTimer);
    state.epilepsyInline.progressTimer = null;
  };
}

async function runRealTask(moduleName, workflowId) {
  const isInlineEpilepsy = moduleName === "epilepsy_ml";
  if (isInlineEpilepsy) setInlineEpilepsyScreeningProgress("submitting", 8, "已收到操作，正在提交癫痫样候选事件初筛任务。");
  if (state.teaching.active) await ensureTeachingSandboxReady({ preview: false, moduleName });
  const project = await ensureRealProject();
  const eegFile = currentWorkspaceFile() || (state.teaching.active ? null : await uploadRealEeg());
  if (!eegFile?.id) throw new Error(state.teaching.active ? "\u6559\u5b66\u6a21\u5f0f\u672a\u52a0\u8f7d\u5185\u7f6e\u8111\u7535\u6570\u636e\uff0c\u8bf7\u91cd\u65b0\u8fdb\u5165\u6559\u5b66\u6a21\u5f0f\u3002" : "\u8bf7\u5148\u4e0a\u4f20\u6216\u9009\u62e9 EEG \u6570\u636e\u3002");
  const requiresPlan = ["psd", "erp", "tfr", "multitaper_psd", "multitaper_tfr", "reference_csd", "pac", "connectivity", "epilepsy_ml"].includes(moduleName);
  const requiresEpochSet = ["erp", "tfr", "multitaper_tfr", "pac"].includes(moduleName);
  const plan = state.real.plan || await getCurrentDataPreparationPlan(eegFile);
  const planContract = dataPreparationContractVersion(plan);
  if (requiresPlan && (!plan || plan.is_default || plan.status !== "confirmed" || !plan.id || !Number.isFinite(Number(plan.revision)) || planContract !== DATA_PREPARATION_CONTRACT_VERSION)) {
    throw new Error("请先确认数据准备方案，再开始分析。");
  }
  if (requiresEpochSet && !state.real.epochSet?.id) {
    throw new Error("请先保存事件与片段，再开始事件相关分析或 PAC 分析。");
  }
  state.real.plan = plan && !plan.is_default ? plan : state.real.plan;
  const parametersJson = buildTaskParameters(moduleName, plan);
  const backendModule = backendTaskModuleName(moduleName);
  const planText = state.real.plan?.id ? `，数据准备记录第 ${state.real.plan.revision} 版` : "";
  setRealStatus(`正在运行 ${moduleDisplayName(moduleName)}${planText}`, "info");
  let stopEpilepsyProgress = null;
  if (isInlineEpilepsy) {
    setInlineEpilepsyScreeningProgress("running", 28, "已提交任务，正在进行癫痫样候选事件初筛。");
    state.real.tasks[moduleName] = {
      id: `pending_${Date.now()}`,
      status: "running",
      queue_status: "running",
      progress: 28,
      module_name: backendModule,
      workflow_id: workflowId,
      input_file_id: eegFile.id,
      parameters_json: parametersJson,
    };
    state.real.latestTaskModule = moduleName;
    if (isE2EAutomationContext()) {
      window.__QLANALYSER_LAST_REAL_ACTION__ = { action: "run-epilepsy-ml", status: "submitted_to_backend", taskId: "" };
      window.__QLANALYSER_EPILEPSY_E2E_TASK__ = state.real.tasks[moduleName];
    }
    renderInlineEpilepsyWorkbench();
    stopEpilepsyProgress = startInlineEpilepsyProgressHeartbeat(eegFile);
  }
  let task;
  try {
    task = await apiJson("/tasks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        project_id: project.id,
        input_file_id: eegFile.id,
        module_name: backendModule,
        workflow_id: workflowId,
        parameters_json: parametersJson,
        owner_user_id: currentAccountId(),
        created_by: currentAccountId(),
      }),
    });
  } catch (error) {
    if (isInlineEpilepsy) {
      if (stopEpilepsyProgress) stopEpilepsyProgress();
      setInlineEpilepsyScreeningProgress("failed", 100, `初筛未完成：${error.message || error}`);
      if (isE2EAutomationContext()) {
        window.__QLANALYSER_LAST_REAL_ACTION__ = { action: "run-epilepsy-ml", status: "failed", error: error.message || String(error) };
      }
      renderInlineEpilepsyWorkbench();
    }
    throw error;
  } finally {
    if (stopEpilepsyProgress) stopEpilepsyProgress();
  }
  if (isInlineEpilepsy && isE2EAutomationContext()) {
    window.__QLANALYSER_LAST_REAL_ACTION__ = { action: "run-epilepsy-ml", status: "task_created", taskId: task?.id || "" };
  }
  state.real.tasks[moduleName] = task;
  state.real.latestTaskModule = moduleName;
  state.real.resultsViewed = false;
  state.real.report = null;
  if (isInlineEpilepsy) setInlineEpilepsyScreeningProgress("loading_results", 72, "初筛任务已返回，正在读取候选标记预览与候选事件结果。");
  if (moduleName === "epilepsy_ml" && isE2EAutomationContext()) {
    window.__QLANALYSER_LAST_EPILEPSY_TASK__ = task;
    window.__QLANALYSER_EPILEPSY_E2E_TASK__ = task;
    window.__QLANALYSER_E2E_STATE__ = state;
  }
  const artifacts = await fetchTaskArtifacts(task.id);
  state.real.artifacts[moduleName] = artifacts;
  if (moduleName === "epilepsy_ml") {
    await loadInlineEpilepsyResultData(task, artifacts);
    setInlineEpilepsyScreeningProgress("completed", 100, "\u766b\u75eb\u6837\u4e8b\u4ef6\u521d\u7b5b\u5b8c\u6210\uff0c\u53ef\u7ee7\u7eed\u9605\u7247\u548c\u4eba\u5de5\u77eb\u6b63\u3002");
    if (isE2EAutomationContext()) {
      window.__QLANALYSER_LAST_REAL_ACTION__ = { action: "run-epilepsy-ml", status: "completed", taskId: task?.id || "" };
    }
    renderInlineEpilepsyWorkbench();
  }
  setRealStatus(`${moduleDisplayName(moduleName)} 已完成，结果已更新。`, "ok");
  renderRealResultReview();
  renderRealDelivery();
  return task;
}
async function createRealReport() {
  const { task } = await ensureReportReleaseReady();
  const project = await ensureRealProject();
  const title = qs("#realReportTitle")?.value.trim() || "Single-record EEG analysis report";
  const report = await apiJson("/reports", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: project.id, task_id: task.id, title }),
  });
  state.real.report = report;
  addReportDownload(report);
  renderRealDelivery();
  setView("publication");
  setRealStatus("复核记录已生成，可在报告页下载。", "ok");
  return report;
}

function artifactDownloadUrl(artifact) {
  return artifact?.id ? `${state.apiBase}/artifacts/${encodeURIComponent(artifact.id)}/download` : "";
}

function moduleDisplayName(moduleName) {
  const map = {
    qc: "基础质量预览",
    qc_metadata: "数据概况",
    psd: "PSD / Bandpower",
    erp: "ERP / P300",
    tfr: "TFR / ERSP / ITC",
    multitaper_psd: "Multitaper PSD",
    multitaper_tfr: "Multitaper TFR",
    epilepsy_ml: "癫痫样候选事件初筛",
    reference_csd: "CSD 电流源密度计算",
    pac: "PAC 相位-振幅耦合",
    connectivity: "Connectivity 连接性分析",
  };
  return map[moduleName] || String(moduleName || "").toUpperCase();
}

function taskStatusLabelReadable(task) {
  const raw = String(task?.status || "").toLowerCase();
  if (raw === "completed") return "已完成";
  if (raw === "failed" || raw === "error") return "失败";
  if (raw === "queued" || raw === "pending") return "排队中";
  if (raw === "running") return "运行中";
  if (raw === "blocked") return "已阻塞";
  return raw ? `状态：${raw}` : "运行中";
}

function applyResultSurfaceCopy() {
  qsa("#realResultReview [data-result-module]").forEach((item) => {
    const moduleName = String(item.dataset.resultModule || "");
    const task = state.real.tasks?.[moduleName] || null;
    const strong = item.querySelector("strong");
    if (strong && moduleName) {
      strong.textContent = `${moduleDisplayName(moduleName)} - ${taskStatusLabelReadable(task)}`;
    }
    const summary = item.querySelector("span");
    if (summary && moduleName) {
      const artifacts = state.real.artifacts?.[moduleName] || [];
      summary.textContent = artifactSummaryLabel(artifacts);
    }
    const details = item.querySelector("summary");
    if (details) details.textContent = "查看结果文件明细";
  });

  const review = qs("#realResultReview");
  if (review && !review.querySelector("[data-result-module]") && !state.real.tasks?.psd && !state.real.tasks?.erp && !state.real.tasks?.tfr && !state.real.tasks?.pac) {
    const action = getRecoveryActionForAnalysisFlow();
    review.innerHTML = `
      <article class="result-item result-empty-state" data-result-state="empty" data-testid="customer-empty-results">
        <strong>第 4 步还没完成：先运行 PSD 分析</strong>
        <span>完成一次分析任务后，这里会显示图表、表格、参数和可复核记录。</span>
        <div class="real-actions compact-actions">
          <button class="primary-btn" type="button" data-view-jump="${escapeHtml(action.view)}"><i data-lucide="${escapeHtml(action.icon)}"></i><span>${escapeHtml(action.label)}</span></button>
        </div>
      </article>
    `;
  }

  const delivery = qs("#realDeliveryLinks");
  if (delivery && !delivery.querySelector("[data-report-id]")) {
    const task = latestAnalysisTask();
    const reportGate = reportReleaseGateSnapshot();
    const action = task?.id ? null : getRecoveryActionForAnalysisFlow();
    delivery.innerHTML = `
      <article class="result-item result-empty-state" data-report-state="empty" data-testid="customer-empty-reports">
        <strong>${reportGate.ready ? "生成复核记录" : task?.id ? "复核记录暂不可生成" : "请先完成分析并查看结果"}</strong>
        <span>${reportGate.ready ? "已查看分析结果，且已有可下载结果文件，可以整理图表、表格、方法记录和复现信息。" : task?.id ? reportGate.reason : "完成一次分析任务后，先到结果页查看结果。"}</span>
        <div class="real-actions compact-actions">
          ${reportGate.ready
            ? `<button class="primary-btn" type="button" data-real-action="create-report"><i data-lucide="file-output"></i><span>生成复核记录</span></button>`
            : task?.id
              ? `<button class="primary-btn" type="button" data-view-jump="statistics"><i data-lucide="chart-line"></i><span>查看分析结果</span></button>`
            : `<button class="primary-btn" type="button" data-view-jump="${escapeHtml(action.view)}"><i data-lucide="${escapeHtml(action.icon)}"></i><span>${escapeHtml(action.label)}</span></button>`}
        </div>
      </article>
    `;
  }
  if (window.lucide) window.lucide.createIcons();
}

async function markLatestResultsReviewed() {
  const task = latestAnalysisTask();
  if (!task?.id || !isCompletedAnalysisTask(task)) return null;
  if (task.result_reviewed_at || task.resultReviewRecorded) {
    state.real.resultsViewed = true;
    return task;
  }
  try {
    const audit = await apiJson(`/tasks/${encodeURIComponent(task.id)}/result-review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    task.result_reviewed_at = audit.created_at || new Date().toISOString();
    task.resultReviewRecorded = true;
    state.real.resultsViewed = true;
    recordUiAction("result:reviewed", "pass", "分析结果已查看，报告生成门控已记录。", {
      task_id: task.id,
      audit_id: audit.id || "",
    });
    updateRealActionGate();
    renderRealDelivery();
    return task;
  } catch (error) {
    recordUiAction("result:reviewed", "blocked", `结果查看记录未保存：${error.message || error}`, { task_id: task.id });
    updateRealActionGate();
    return null;
  }
}

function artifactSummaryLabel(artifacts = []) {
  if (!artifacts.length) return "结果文件生成中或暂无可下载文件。";
  const downloadable = artifacts.filter((artifact) => artifactDownloadUrl(artifact)).length;
  const groups = artifactGroupSummary(artifacts);
  const groupText = groups.length ? `包括${groups.join("、")}。` : "";
  return `已生成 ${artifacts.length} 个结果文件，其中 ${downloadable} 个可下载。${groupText}`;
}

function artifactReadableKey(artifact = {}) {
  return String(artifact.label || artifact.artifact_type || artifact.id || "")
    .replace(/\.[a-z0-9]+$/i, "")
    .replace(/[-\s]+/g, "_")
    .toLowerCase();
}

function readableArtifactLabel(artifact = {}) {
  const key = artifactReadableKey(artifact);
  const labelMap = [
    [/channel_band_power|band_power_by_channel/, "通道频段功率表"],
    [/band_power|psd_band_power/, "频段功率表"],
    [/psd_mean_spectrum|power_spectrum|spectrum_long|powerspectrum/, "PSD 频谱图"],
    [/erp_metrics|erp_metric|p300/, "ERP 指标表"],
    [/drop_log_summary|epoch_drop|reject/, "Epoch 剔除记录"],
    [/epilepsy_ml_event_timeline_figure|event_timeline/, "癫痫样候选事件初筛时间轴"],
    [/epilepsy_ml_spectrogram_figure|spectrogram_preview/, "癫痫样候选事件初筛时频证据图"],
    [/epilepsy_ml_spectrogram/, "癫痫样候选事件初筛时频数据"],
    [/epilepsy.*epoch|epoch_predictions|epoch_scores/, "癫痫样事件 epoch 预测表"],
    [/epilepsy.*event|candidate_events|reviewed_events|final_review_events/, "癫痫样候选事件表"],
    [/manual_corrections|review_actions|event_review/, "人工复核标注记录"],
    [/review_revision|review_session/, "复核版本记录"],
    [/model_manifest|epilepsy_ml_model_manifest/, "模型记录"],
    [/tfr_power_long|ersp|itc|time_frequency/, "时频功率明细表"],
    [/pac_dynamic_curve|pac_curve|cfc/, "PAC 动态曲线"],
    [/parameters|parameter_schema|threshold_validation/, "参数记录"],
    [/workflow|plan|preparation/, "处理流程记录"],
    [/software_versions|version/, "软件版本记录"],
    [/manifest|log/, "文件清单"],
    [/metadata|dictionary|source/, "数据说明"],
    [/contract|scope/, "结果范围说明"],
  ];
  const match = labelMap.find(([pattern]) => pattern.test(key));
  if (match) return match[1];
  return "结果文件";
}

function artifactGroupSummary(artifacts = []) {
  const groups = new Set();
  artifacts.forEach((artifact) => {
    const key = artifactReadableKey(artifact);
    if (/png|figure|plot|spectrum|power|curve|ersp|itc/.test(key)) groups.add("图表");
    else if (/csv|table|metrics|band|metadata|dictionary/.test(key)) groups.add("表格");
    else if (/workflow|parameters|plan|method/.test(key)) groups.add("方法记录");
    else if (/version|manifest|log|contract|scope|source/.test(key)) groups.add("复现信息");
    else if (/qc|drop|reject|threshold/.test(key)) groups.add("质量记录");
  });
  return Array.from(groups);
}

function artifactDetailItems(artifacts = []) {
  return (artifacts || [])
    .map((artifact) => ({
      label: readableArtifactLabel(artifact),
      href: artifactDownloadUrl(artifact),
      id: artifact.id || "",
      count: 1,
    }))
    .filter((item) => item.href && item.id);
}

function artifactImageItems(artifacts = []) {
  return (artifacts || [])
    .filter((artifact) => safeArtifactPreviewMime(artifact))
    .map((artifact) => ({
      artifact,
      id: artifact.id || "",
      label: readableArtifactLabel(artifact),
      href: artifactDownloadUrl(artifact),
      mime: artifact.mime_type || artifact.mimeType || "image",
    }))
    .filter((item) => item.href && item.id);
}

function safeArtifactPreviewMime(artifact) {
  const mime = String(artifact?.mime_type || artifact?.mimeType || "").toLowerCase();
  const path = String(artifact?.path || artifact?.object_key || artifact?.filename || artifact?.label || "").toLowerCase();
  if (mime === "image/png" || mime === "image/jpeg" || mime === "image/webp") return true;
  return /\.(png|jpg|jpeg|webp)$/.test(path);
}

function safeBlobPreviewMime(blob) {
  const mime = String(blob?.type || "").toLowerCase();
  return mime === "image/png" || mime === "image/jpeg" || mime === "image/webp";
}

function artifactDownloadTitle(artifact) {
  const mime = String(artifact?.mime_type || artifact?.mimeType || "").toLowerCase();
  const path = String(artifact?.path || artifact?.object_key || artifact?.filename || artifact?.label || "").toLowerCase();
  if (mime.startsWith("image/") || /\.(svg|png|jpg|jpeg|webp)$/.test(path)) return "下载图片";
  if (mime.includes("csv") || path.endsWith(".csv")) return "下载 CSV";
  if (mime.includes("json") || path.endsWith(".json")) return "下载 JSON";
  if (mime.includes("zip") || path.endsWith(".zip")) return "下载 ZIP";
  if (mime.startsWith("text/") || /\.(txt|md|log)$/.test(path)) return "下载文本";
  return "下载文件";
}

function renderAuthenticatedArtifactImage(artifact, label) {
  const id = artifact?.id || "";
  if (!id) return `<div class="artifact-card-icon"><i data-lucide="image-off"></i></div>`;
  return `<img data-auth-artifact-image="${escapeHtml(id)}" alt="${escapeHtml(label)}" loading="lazy" />`;
}

function renderResultImagePreview(artifacts = []) {
  const images = artifactImageItems(artifacts);
  if (!images.length) return "";
  return `
    <div class="result-image-preview-grid" data-testid="result-image-preview-grid">
      ${images.map((item) => `
        <figure class="result-image-preview-card">
          ${safeArtifactPreviewMime(item.artifact)
            ? `<button type="button" data-artifact-open="${escapeHtml(item.id)}" title="新窗口打开 ${escapeHtml(item.label)}">${renderAuthenticatedArtifactImage(item.artifact, item.label)}</button>`
            : `<div class="result-image-static-preview">${renderAuthenticatedArtifactImage(item.artifact, item.label)}</div>`}
          <figcaption><strong>${escapeHtml(item.label)}</strong><span>${escapeHtml(item.mime)}</span></figcaption>
        </figure>
      `).join("")}
    </div>
  `;
}

function renderArtifactDetailLinks(artifacts = []) {
  const items = artifactDetailItems(artifacts);
  if (!items.length) return "<span>结果文件生成中或暂无可下载文件。</span>";
  return items.map((item) => `
    <button class="artifact-link-chip" type="button" data-artifact-download="${escapeHtml(item.id)}">
      <span>${escapeHtml(item.label)}</span>
      <small>${item.count > 1 ? `含 ${item.count} 个文件` : "1 个文件"}</small>
    </button>
  `).join("");
}

function resultEvidenceState(moduleName, task, artifacts = []) {
  const hasLinks = artifactDetailItems(artifacts).length > 0;
  if (!task?.id) return { label: "未运行", note: "先回到分析任务运行该分支", tone: "blocked" };
  if (task.status && task.status !== "completed") return { label: taskStatusLabelReadable(task), note: "任务未完成，返回分析任务页刷新或重试", tone: "warning" };
  if (!hasLinks) return { label: "缺少可下载证据", note: "刷新结果；仍缺失时重新运行该分析分支", tone: "warning" };
  return { label: "证据链完整", note: "图表、表格或方法记录已可查看", tone: "ready" };
}

function renderEvidenceBadges(moduleName, task, artifacts = []) {
  const stateItem = resultEvidenceState(moduleName, task, artifacts);
  const groups = artifactGroupSummary(artifacts);
  const chips = [stateItem.label, task?.id ? `任务 ${task.id}` : "无任务", groups.length ? groups.join(" / ") : "无文件分组"];
  return `<div class="evidence-chain ${escapeHtml(stateItem.tone)}">${chips.map((chip) => `<b>${escapeHtml(chip)}</b>`).join("")}<small>${escapeHtml(stateItem.note)}</small></div>`;
}

function getResultViewMode() {
  return state.resultViewMode || "grid";
}

function setResultViewMode(mode) {
  state.resultViewMode = mode;
  try {
    localStorage.setItem("qlanalyser_result_view_mode", mode);
  } catch (e) {}
  renderRealResultReview();
}

function initResultViewMode() {
  if (!state.resultViewMode) {
    try {
      state.resultViewMode = localStorage.getItem("qlanalyser_result_view_mode") || "grid";
    } catch (e) {
      state.resultViewMode = "grid";
    }
  }
}

function renderResultToolbar() {
  const mode = getResultViewMode();
  return `
    <div class="result-toolbar" data-testid="result-toolbar">
      <div class="result-view-switcher">
        <button type="button" class="view-mode-btn ${mode === "grid" ? "active" : ""}" data-view-mode="grid" title="网格视图">
          <i data-lucide="grid-2x2"></i><span>网格</span>
        </button>
        <button type="button" class="view-mode-btn ${mode === "list" ? "active" : ""}" data-view-mode="list" title="列表视图">
          <i data-lucide="list"></i><span>列表</span>
        </button>
        <button type="button" class="view-mode-btn ${mode === "classic" ? "active" : ""}" data-view-mode="classic" title="经典视图">
          <i data-lucide="layout-list"></i><span>经典</span>
        </button>
      </div>
    </div>
  `;
}

function renderArtifactCard(artifact) {
  const label = readableArtifactLabel(artifact);
  const downloadUrl = artifactDownloadUrl(artifact);
  const mime = String(artifact.mime_type || artifact.mimeType || "").toLowerCase();
  const path = String(artifact.path || artifact.object_key || artifact.filename || "").toLowerCase();
  const isImage = mime.startsWith("image/") || /\.(svg|png|jpg|jpeg|webp)$/.test(path);
  const isSvg = mime === "image/svg+xml" || path.endsWith(".svg");
  const isPng = mime === "image/png" || path.endsWith(".png");
  
  if (!downloadUrl) return "";
  
  return `
    <div class="artifact-card" data-artifact-id="${escapeHtml(artifact.id || '')}" data-artifact-type="${isImage ? "image" : "file"}">
      <div class="artifact-card-preview">
        ${isImage 
          ? renderAuthenticatedArtifactImage(artifact, label)
          : `<div class="artifact-card-icon"><i data-lucide="file-text"></i></div>`}
      </div>
      <div class="artifact-card-content">
        <h4 class="artifact-card-title">${escapeHtml(label)}</h4>
        <p class="artifact-card-meta">${escapeHtml(artifact.mime_type || "file")}</p>
      </div>
      <div class="artifact-card-actions">
        <button class="artifact-action-btn" type="button" data-artifact-download="${escapeHtml(artifact.id || '')}" title="${escapeHtml(artifactDownloadTitle(artifact))}">
          <i data-lucide="download"></i>
        </button>
        ${isSvg ? `<button type="button" class="artifact-action-btn" data-artifact-svg-download="${escapeHtml(artifact.id || '')}" title="下载 SVG">
          <i data-lucide="file-code"></i>
        </button>` : ""}
        ${isPng ? `<button type="button" class="artifact-action-btn" data-artifact-png-download="${escapeHtml(artifact.id || '')}" title="下载 PNG">
          <i data-lucide="image"></i>
        </button>` : ""}
        ${safeArtifactPreviewMime(artifact) ? `<button class="artifact-action-btn" type="button" data-artifact-open="${escapeHtml(artifact.id || '')}" title="新窗口打开">
          <i data-lucide="external-link"></i>
        </button>` : ""}
      </div>
    </div>
  `;
}

function renderArtifactsGrid(artifacts = []) {
  if (!artifacts.length) return "<p class='artifact-empty-state'>暂无结果文件</p>";
  return `
    <div class="artifacts-grid" data-testid="artifacts-grid">
      ${artifacts.map(artifact => renderArtifactCard(artifact)).join("")}
    </div>
  `;
}

function renderArtifactsList(artifacts = []) {
  if (!artifacts.length) return "<p class='artifact-empty-state'>暂无结果文件</p>";
  return `
    <div class="artifacts-list" data-testid="artifacts-list">
      ${artifacts.map(artifact => {
        const label = readableArtifactLabel(artifact);
        const downloadUrl = artifactDownloadUrl(artifact);
        const mime = artifact.mime_type || artifact.mimeType || "file";
        if (!downloadUrl) return "";
        return `
          <div class="artifact-list-item">
            <div class="artifact-list-icon"><i data-lucide="file"></i></div>
            <div class="artifact-list-content">
              <strong>${escapeHtml(label)}</strong>
              <span>${escapeHtml(mime)}</span>
            </div>
            <div class="artifact-list-actions">
              <button class="ghost-btn compact-btn" type="button" data-artifact-download="${escapeHtml(artifact.id || '')}">
                <i data-lucide="download"></i><span>${escapeHtml(artifactDownloadTitle(artifact))}</span>
              </button>
            </div>
          </div>
        `;
      }).join("")}
    </div>
  `;
}

function renderModuleBatchActions(moduleName, artifacts = []) {
  if (!artifacts.length) return "";
  const task = state.real.tasks?.[moduleName];
  if (!task?.id) return "";
  
  return `
    <div class="module-batch-actions">
      <button type="button" class="ghost-btn compact-btn" data-module-batch-download="${escapeHtml(moduleName)}" title="批量下载本模块所有文件为 ZIP">
        <i data-lucide="download"></i><span>批量下载 (ZIP)</span>
      </button>
    </div>
  `;
}

function renderRealResultReview() {
  initResultViewMode();
  const target = qs("#realResultReview");
  if (!target) return;
  const modules = Object.entries(state.real.tasks || {}).filter(([, task]) => task?.id);
  if (!modules.length) {
    const action = getRecoveryActionForAnalysisFlow();
    target.innerHTML = `
      <article class="result-item result-empty-state" data-result-state="empty" data-testid="customer-empty-results">
        <strong>还没有分析结果</strong>
        <span>完成一次分析任务后，这里会显示图表、表格、参数和可复核记录。</span>
        <div class="real-actions compact-actions">
          <button class="primary-btn" type="button" data-view-jump="${escapeHtml(action.view)}"><i data-lucide="${escapeHtml(action.icon)}"></i><span>${escapeHtml(action.label)}</span></button>
        </div>
      </article>
    `;
    renderEpilepsyResultReviewV3Panel();
    if (window.lucide) window.lucide.createIcons();
    return;
  }
  
  const viewMode = getResultViewMode();
  const toolbar = renderResultToolbar();
  
  const resultItems = modules.map(([moduleName, task]) => {
    const artifacts = state.real.artifacts?.[moduleName] || [];
    const links = renderArtifactDetailLinks(artifacts);
    
    let contentHtml = "";
    if (viewMode === "grid") {
      contentHtml = `
        ${renderModuleBatchActions(moduleName, artifacts)}
        ${renderArtifactsGrid(artifacts)}
      `;
    } else if (viewMode === "list") {
      contentHtml = `
        ${renderModuleBatchActions(moduleName, artifacts)}
        ${renderArtifactsList(artifacts)}
      `;
    } else {
      contentHtml = `
        ${renderEvidenceBadges(moduleName, task, artifacts)}
        ${renderResultImagePreview(artifacts)}
        <details class="technical-details artifact-details">
          <summary>查看结果文件明细</summary>
          <div class="artifact-link-grid">${links}</div>
        </details>
      `;
    }
    
    return `
      <article class="result-item" data-result-module="${escapeHtml(moduleName)}" data-view-mode="${escapeHtml(viewMode)}">
        <div class="result-item-header">
          <strong>${escapeHtml(moduleDisplayName(moduleName))} - ${escapeHtml(taskStatusLabelReadable(task))}</strong>
          <span>${escapeHtml(artifactSummaryLabel(artifacts))}</span>
        </div>
        <div class="result-item-content">
          ${contentHtml}
        </div>
      </article>
    `;
  }).join("");
  
  const task = latestAnalysisTask();
  const reportGate = reportReleaseGateSnapshot();
  const reportAction = task && !state.real.report
    ? `
      <article class="result-item" data-result-action="report">
        <strong>${reportGate.ready ? "下一步：生成复核记录" : "复核记录暂不可生成"}</strong>
        <span>${reportGate.ready ? "确认结果图表、表格和参数记录后，再生成科研交付材料。" : escapeHtml(reportGate.reason)}</span>
        <div class="real-actions compact-actions">
          ${reportGate.ready
            ? `<button class="primary-btn" type="button" data-real-action="create-report"><i data-lucide="file-output"></i><span>生成复核记录</span></button>`
            : `<button class="ghost-btn" type="button" disabled title="${escapeHtml(reportGate.reason)}"><i data-lucide="file-output"></i><span>生成复核记录</span></button>`}
        </div>
      </article>
    `
    : "";
  
  target.innerHTML = `${toolbar}${resultItems}${reportAction}`;
  attachResultViewEventListeners();
  loadAuthenticatedArtifactImages();
  if (window.lucide) window.lucide.createIcons();
  renderEpilepsyResultReviewV3Panel();
}

function artifactById(artifactId) {
  return Object.values(state.real.artifacts || {}).flat().find((artifact) => artifact?.id === artifactId) || null;
}

function artifactFilename(artifact, fallbackExt = "") {
  const rawPath = String(artifact?.filename || artifact?.path || artifact?.object_key || "");
  const pathName = rawPath.split(/[\\/]/).filter(Boolean).pop() || "";
  const label = String(artifact?.label || artifact?.id || "artifact").replace(/[^\w\-.\u4e00-\u9fa5]+/g, "_");
  const base = pathName || label || "artifact";
  if (!fallbackExt || base.toLowerCase().endsWith(`.${fallbackExt.toLowerCase()}`)) return base;
  return `${base}.${fallbackExt}`;
}

async function fetchAuthorizedBlobUrl(url, accept = "application/octet-stream") {
  if (!url) throw new Error("文件下载链接无效");
  const response = await fetch(url, {
    method: "GET",
    headers: withAuthHeaders({ Accept: accept || "application/octet-stream" }),
    cache: "no-store",
  });
  if (!response.ok) throw new Error(`下载失败: ${response.status}`);
  return response.blob();
}

async function fetchArtifactBlob(artifact, accept = "application/octet-stream") {
  return fetchAuthorizedBlobUrl(artifactDownloadUrl(artifact), accept);
}

function isAllowedAuthenticatedDownloadUrl(url) {
  try {
    const parsed = new URL(url, window.location.href);
    const apiBase = new URL(state.apiBase, window.location.href);
    const basePath = apiBase.pathname.replace(/\/$/, "");
    return parsed.origin === apiBase.origin && (parsed.pathname === basePath || parsed.pathname.startsWith(`${basePath}/`));
  } catch {
    return false;
  }
}

async function downloadAuthorizedUrl(url, filename, accept = "application/octet-stream") {
  if (!isAllowedAuthenticatedDownloadUrl(url)) throw new Error("下载地址不在当前 API 范围内");
  const blob = await fetchAuthorizedBlobUrl(url, accept);
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = filename || "download";
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
}

async function loadAuthenticatedUrlImages() {
  const images = Array.from(document.querySelectorAll("img[data-auth-image-url]"));
  await Promise.all(images.map(async (img) => {
    const url = img.dataset.authImageUrl || "";
    if (!url || img.dataset.authImageStatus === "ready") return;
    if (!isAllowedAuthenticatedDownloadUrl(url)) {
      img.dataset.authImageStatus = "failed";
      img.alt = `${img.alt || "图片"}（加载失败：下载地址不在当前 API 范围内）`;
      return;
    }
    img.dataset.authImageStatus = "loading";
    try {
      const blob = await fetchAuthorizedBlobUrl(url, "image/png,image/jpeg,image/webp");
      if (!safeBlobPreviewMime(blob)) throw new Error("证据图类型不允许预览");
      const objectUrl = URL.createObjectURL(blob);
      img.src = objectUrl;
      img.dataset.authImageStatus = "ready";
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000);
    } catch (error) {
      img.dataset.authImageStatus = "failed";
      img.alt = `${img.alt || "图片"}（加载失败：${error.message || error}）`;
    }
  }));
}

async function loadAuthenticatedArtifactImages() {
  const images = Array.from(document.querySelectorAll("img[data-auth-artifact-image]"));
  await Promise.all(images.map(async (img) => {
    const artifactId = img.dataset.authArtifactImage || "";
    if (!artifactId || img.dataset.authImageStatus === "ready") return;
    const cachedUrl = authenticatedArtifactImageUrls.get(artifactId);
    if (cachedUrl) {
      img.src = cachedUrl;
      img.dataset.authImageStatus = "ready";
      return;
    }
    const artifact = artifactById(artifactId);
    if (!artifact) return;
    img.dataset.authImageStatus = "loading";
    try {
      if (!safeArtifactPreviewMime(artifact)) throw new Error("该文件类型不允许图片预览");
      const blob = await fetchArtifactBlob(artifact, "image/png,image/jpeg,image/webp");
      if (!safeBlobPreviewMime(blob)) throw new Error("该文件类型不允许图片预览");
      const objectUrl = URL.createObjectURL(blob);
      authenticatedArtifactImageUrls.set(artifactId, objectUrl);
      img.src = objectUrl;
      img.dataset.authImageStatus = "ready";
    } catch (error) {
      img.dataset.authImageStatus = "failed";
      img.alt = `${img.alt || "图片"}（加载失败：${error.message || error}）`;
    }
  }));
}

function attachResultViewEventListeners() {
  document.querySelectorAll(".view-mode-btn").forEach(btn => {
    btn.addEventListener("click", (e) => {
      const mode = e.currentTarget.dataset.viewMode;
      if (mode) setResultViewMode(mode);
    });
  });
  
  document.querySelectorAll("[data-artifact-download]").forEach(btn => {
    btn.addEventListener("click", async (e) => {
      const artifactId = e.currentTarget.dataset.artifactDownload;
      await downloadArtifactAs(artifactId, "");
    });
  });

  document.querySelectorAll("[data-artifact-open]").forEach(btn => {
    btn.addEventListener("click", async (e) => {
      const artifactId = e.currentTarget.dataset.artifactOpen;
      await openArtifactInNewWindow(artifactId);
    });
  });

  document.querySelectorAll("[data-artifact-svg-download]").forEach(btn => {
    btn.addEventListener("click", async (e) => {
      const artifactId = e.currentTarget.dataset.artifactSvgDownload;
      await downloadArtifactAs(artifactId, "svg");
    });
  });
  
  document.querySelectorAll("[data-artifact-png-download]").forEach(btn => {
    btn.addEventListener("click", async (e) => {
      const artifactId = e.currentTarget.dataset.artifactPngDownload;
      await downloadArtifactAs(artifactId, "png");
    });
  });
  
  document.querySelectorAll("[data-module-batch-download]").forEach(btn => {
    btn.addEventListener("click", async (e) => {
      const moduleName = e.currentTarget.dataset.moduleBatchDownload;
      await batchDownloadModuleArtifacts(moduleName);
    });
  });
}

async function downloadArtifactAs(artifactId, format = "") {
  try {
    const artifact = artifactById(artifactId);
    if (!artifact) throw new Error("找不到指定的文件");
    const blob = await fetchArtifactBlob(artifact, "application/octet-stream,*/*");
    const filename = artifactFilename(artifact, format || "");
    const link = document.createElement("a");
    const objectUrl = URL.createObjectURL(blob);
    link.href = objectUrl;
    link.download = filename;
    document.body.append(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
    showToast(`已下载 ${filename}`);
  } catch (error) {
    showToast(`下载失败: ${error.message}`);
  }
}

async function openArtifactInNewWindow(artifactId) {
  const targetWindow = window.open("about:blank", "_blank");
  if (targetWindow) targetWindow.opener = null;
  try {
    const artifact = artifactById(artifactId);
    if (!artifact) throw new Error("找不到指定的文件");
    if (!safeArtifactPreviewMime(artifact)) {
      if (targetWindow && !targetWindow.closed) targetWindow.close();
      await downloadArtifactAs(artifactId, "");
      return;
    }
    const blob = await fetchArtifactBlob(artifact, "image/png,image/jpeg,image/webp");
    if (!safeBlobPreviewMime(blob)) {
      if (targetWindow && !targetWindow.closed) targetWindow.close();
      await downloadArtifactAs(artifactId, "");
      return;
    }
    const objectUrl = URL.createObjectURL(blob);
    if (targetWindow) {
      targetWindow.location.href = objectUrl;
    } else {
      const link = document.createElement("a");
      link.href = objectUrl;
      link.target = "_blank";
      link.rel = "noreferrer";
      link.click();
    }
    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000);
  } catch (error) {
    if (targetWindow && !targetWindow.closed) targetWindow.close();
    showToast(`打开失败: ${error.message}`);
  }
}

async function batchDownloadModuleArtifacts(moduleName) {
  try {
    const task = state.real.tasks?.[moduleName];
    if (!task?.id) throw new Error("任务不存在");
    
    const projectId = state.real.project?.id;
    if (!projectId) throw new Error("项目不存在");
    
    showToast("正在准备批量下载...");
    
    const url = `${state.apiBase}/projects/${encodeURIComponent(projectId)}/tasks/${encodeURIComponent(task.id)}/artifacts/batch`;
    const response = await fetch(url, {
      method: "POST",
      headers: withAuthHeaders({ "Content-Type": "application/json" })
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`批量下载失败: ${response.statusText} - ${errorText}`);
    }
    
    const blob = await response.blob();
    const filename = `${moduleName}_artifacts_${task.id.substring(0, 8)}.zip`;
    const objectUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = objectUrl;
    link.download = filename;
    document.body.append(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
    
    showToast(`已下载 ${filename}`);
  } catch (error) {
    showToast(`批量下载失败: ${error.message}`);
  }
}

function addReportDownload(report) {
  const target = qs("#realDeliveryLinks") || qs("#realDelivery");
  if (!target || !report?.id) return;
  qsa('[data-testid="report-package-contract"]').forEach((node) => { node.hidden = false; });
  qsa('[data-testid="report-delivery-workbench"] [data-real-action="create-report"]').forEach((node) => { node.hidden = true; });
  target.innerHTML = `
    <article class="result-item" data-report-id="${escapeHtml(report.id)}">
      <strong>复核记录已生成</strong>
      <span>下载完整交付材料，包含图表、表格、方法记录和复现信息。</span>
      <div class="real-actions compact-actions">
        <button class="primary-btn" type="button" data-report-download="package" data-report-id="${escapeHtml(report.id)}">下载复核记录包</button>
        <button class="ghost-btn" type="button" data-report-download="html" data-report-id="${escapeHtml(report.id)}">在线预览</button>
      </div>
    </article>
  `;
  target.querySelectorAll("[data-report-download]").forEach((button) => {
    button.addEventListener("click", async (event) => {
      const node = event.currentTarget;
      await downloadReportFile(node.dataset.reportId || report.id, node.dataset.reportDownload || "package");
    });
  });
}

async function downloadReportFile(reportId, kind = "package") {
  try {
    if (!reportId) throw new Error("报告不存在");
    const safeKind = kind === "html" ? "html" : "package";
    const url = `${state.apiBase}/reports/${encodeURIComponent(reportId)}/${safeKind}`;
    if (safeKind === "html") {
      if (!isAllowedAuthenticatedDownloadUrl(url)) throw new Error("下载地址不在当前 API 范围内");
      const blob = await fetchAuthorizedBlobUrl(url, "text/html");
      const objectUrl = URL.createObjectURL(blob);
      const preview = window.open(objectUrl, "_blank", "noopener,noreferrer");
      if (!preview) {
        const link = document.createElement("a");
        link.href = objectUrl;
        link.target = "_blank";
        link.rel = "noreferrer";
        link.click();
      }
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000);
      return;
    }
    await downloadAuthorizedUrl(url, `${reportId}.zip`, "application/zip,application/octet-stream");
    showToast("复核记录包已下载");
  } catch (error) {
    showToast(`报告下载失败: ${error.message || error}`);
  }
}

function renderRealDelivery() {
  const target = qs("#realDeliveryLinks") || qs("#realDelivery");
  if (!target) return;
  if (state.real.report) {
    addReportDownload(state.real.report);
    return;
  }
  const task = latestAnalysisTask();
  const reportGate = reportReleaseGateSnapshot();
  qsa('[data-testid="report-delivery-workbench"] [data-real-action="create-report"]').forEach((node) => { node.hidden = true; });
  qsa('[data-testid="report-package-contract"]').forEach((node) => { node.hidden = !task?.id; });
  if (isCustomerTrialP0Mode()) {
    const action = task?.id ? null : getRecoveryActionForAnalysisFlow();
    target.innerHTML = `
      <article class="result-item result-empty-state" data-report-state="empty" data-testid="customer-empty-reports">
        <strong>${reportGate.ready ? "生成复核记录" : task?.id ? "复核记录暂不可生成" : "请先完成分析并查看结果"}</strong>
        <span>${reportGate.ready
          ? "已查看分析结果，且已有可下载结果文件，可以整理图表、表格、方法记录和复现信息。"
          : task?.id
            ? reportGate.reason
            : "完成一次分析任务后，先到结果页查看结果。"}
        </span>
        <div class="real-actions compact-actions">
          ${reportGate.ready
            ? `<button class="primary-btn" type="button" data-real-action="create-report"><i data-lucide="file-output"></i><span>生成复核记录</span></button>`
            : task?.id
              ? `<button class="primary-btn" type="button" data-view-jump="statistics"><i data-lucide="chart-line"></i><span>查看分析结果</span></button>`
            : `<button class="primary-btn" type="button" data-view-jump="${escapeHtml(action.view)}"><i data-lucide="${escapeHtml(action.icon)}"></i><span>${escapeHtml(action.label)}</span></button>`}
        </div>
      </article>
    `;
    if (window.lucide) window.lucide.createIcons();
    return;
  }
  target.innerHTML = `
    <article class="result-item" data-report-state="empty">
      <strong>\u6682\u65e0\u53ef\u4e0b\u8f7d\u62a5\u544a</strong>
      <span>${task?.id
        ? reportGate.reason
        : "请先确认数据准备并运行推荐分析，然后查看结果。"}</span>
      <div class="real-actions compact-actions">
        <button class="${task?.id ? "primary-btn" : "ghost-btn"}" type="button" ${task?.id ? 'data-view-jump="statistics"' : 'data-view-jump="analysis"'}>
          <i data-lucide="${task?.id ? "chart-line" : "sliders-horizontal"}"></i>
          <span>${task?.id ? "查看分析结果" : "\u53bb\u6570\u636e\u51c6\u5907"}</span>
        </button>
      </div>
    </article>
  `;
  if (window.lucide) window.lucide.createIcons();
}

function applyCustomerDemoMode() {
  const mode = new URLSearchParams(window.location.search).get("customer_demo");
  if (!mode) return;
  const hashView = window.location.hash.slice(1);
  const existingSession = getAuthSession();
  if (state.role === "admin" || existingSession.role === "admin" || /^admin[A-Z]/.test(hashView) || hashView === "journey") {
    return;
  }
  const normalizedMode = String(mode).toLowerCase();
  if (["login", "auto", "demo"].includes(normalizedMode)) {
    fillDemoCustomerCredentials();
    setLoginMessage("已填入本地测试账号，可直接登录。", "info");
  }
  if (normalizedMode === "auto") {
    loginCustomer(demoCustomer.email, demoCustomer.password, true).catch((error) => {
      setLoginMessage(error?.message || "自动登录失败，请点击登录重试。", "error");
    });
  }
}

async function handleRealAction(action) {
  if (!action) return null;
  const actionNames = {
    "create-project": "\u521b\u5efa\u9879\u76ee",
    "upload-eeg": "\u4e0a\u4f20 EEG \u6570\u636e",
    "run-qc-preview-inline": "更新波形",
    "run-metadata-qc-inline": "检查数据基础信息",
    "save-bad-channel-audit": "保存坏道修改",
    "discard-bad-channel-audit": "恢复坏道修改",
    "save-epoch-set": "保存事件分段",
    "download-epoch-record": "\u4e0b\u8f7d 数据准备记录",
    "confirm-plan-inline": "\u786e\u8ba4\u6570\u636e\u51c6\u5907",
    "download-plan-json": "下载处理记录",
    "create-report": "生成复核记录",
    "run-psd": "PSD 分析",
    "run-erp": "ERP 分析",
    "run-tfr": "TFR 时频分析",
    "run-multitaper-psd": "Multitaper PSD",
    "run-multitaper-tfr": "Multitaper TFR",
    "run-reference-csd": "CSD 电流源密度计算",
    "run-pac": "PAC 相位-振幅耦合",
    "run-connectivity": "Connectivity 连接性分析",
  };
  try {
    let result = null;
    if (action === "create-project") result = await ensureRealProject();
    else if (action === "upload-eeg") result = await uploadRealEeg();
    else if (action === "run-qc-preview-inline") result = await runQcPreviewFromUi();
    else if (action === "run-metadata-qc-inline") result = await runMetadataQcFromUi();
    else if (action === "save-bad-channel-audit") result = await saveBadChannelAuditFromUi("save");
    else if (action === "discard-bad-channel-audit") result = await saveBadChannelAuditFromUi("discard");
    else if (action === "save-epoch-set") result = await saveEpochSetFromUi();
    else if (action === "download-epoch-record") {
      const manifest = epochSetToManifest(state.real.epochSet);
      downloadJsonPayload(manifest, `${manifest.epoch_set_id || "epoch_manifest"}.json`);
      result = manifest;
    } else if (action === "confirm-plan-inline") result = await confirmRealDataPreparationPlan();
    else if (action === "download-plan-json") {
      const plan = state.real.plan || await getCurrentDataPreparationPlan(state.real.eegFile);
      if (!plan) throw new Error("请先确认或载入数据准备记录，再下载处理记录。");
      downloadJsonPayload(plan, `${plan.id || "data_preparation_plan"}.json`);
      result = plan;
    } else if (action === "open-epilepsy-workbench") result = await openEpilepsyWorkbenchFromPlan();
    else if (action === "run-epilepsy-ml") result = await runRealTask("epilepsy_ml", "epilepsy_ml_xgboost");
    else if (action === "create-report") result = await createRealReport();
    else if (action === "run-psd") result = await runRealTask("psd", "resting_psd");
    else if (action === "run-erp") result = await runRealTask("erp", "erp_p300");
    else if (action === "run-tfr") result = await runRealTask("tfr", "tfr_ersp_itc");
    else if (action === "run-multitaper-psd") result = await runRealTask("multitaper_psd", "multitaper_psd_tfr");
    else if (action === "run-multitaper-tfr") result = await runRealTask("multitaper_tfr", "multitaper_psd_tfr");
    else if (action === "run-reference-csd") result = await runRealTask("reference_csd", "reference_csd");
    else if (action === "run-pac") result = await runRealTask("pac", "pac_cfc");
    else if (action === "run-connectivity") result = await runRealTask("connectivity", "connectivity");
    else throw new Error(`\u6682\u4e0d\u652f\u6301\u7684\u52a8\u4f5c\uff1a${action}`);
    recordUiAction(`real:${action}`, "pass", `${actionNames[action] || action}\u5df2\u5b8c\u6210\u3002`, { resultId: result?.id || result?.audit_id || result?.epoch_set_id || null });
    renderRealResultReview();
    renderRealDelivery();
    updateRealActionGate();
    return result;
  } catch (error) {
    if (action === "run-epilepsy-ml") {
      if (["localhost", "127.0.0.1"].includes(window.location.hostname)) {
        window.__QLANALYSER_LAST_REAL_ACTION__ = { action, status: "failed", error: String(error.message || error) };
      }
      setInlineEpilepsyScreeningProgress("failed", 100, `癫痫样候选事件初筛失败：${error.message || error}`);
    }
    const message = `${actionNames[action] || action}\u672a\u5b8c\u6210\uff1a${error.message || error}`;
    recordUiAction(`real:${action}`, "blocked", message);
    showToast(message);
    return null;
  }
}

function handleSubmitAnalysisClick() {
  const planReady = isAnalysisReady();
  if (!planReady) {
    const message = "请先完成数据准备确认和事件分段，再提交分析任务。";
    recordUiAction("real:submit-analysis", "blocked", message);
    showToast(message);
    setView("analysis");
    return;
  }
  recordUiAction("real:submit-analysis", "pass", "分析入口已就绪，请优先运行推荐分析。");
  setView("workflow");
}

function handlePendingEegFileSelection() {
  const input = qs("#real-eeg-file");
  const file = input?.files?.[0];
  const nameTarget = qs("#realEegFileName");
  if (nameTarget) {
    nameTarget.textContent = file ? file.name : "\u5c1a\u672a\u9009\u62e9\u6587\u4ef6";
  }
  if (file) {
    state.real.eegFile = null;
    state.real.plan = null;
    state.real.epochSet = null;
    recordUiAction("real:select-eeg-file", "pass", `\u5df2\u9009\u62e9\u5f85\u4e0a\u4f20 EEG \u6570\u636e\uff1a${file.name}`);
  }
  updateRealActionGate();
}

async function handleIaAction(action) {
  const project = currentWorkspaceProject();
  const file = currentWorkspaceFile();
  const currentFileName = eegFileDisplayName(file) || "current file";
  const noProjectMessage = "\u8bf7\u5148\u521b\u5efa\u6216\u9009\u62e9\u9879\u76ee\u3002";
  const noFileMessage = "\u8bf7\u5148\u5728\u5f53\u524d\u9879\u76ee\u4e0a\u4f20\u6216\u9009\u62e9 EEG \u6570\u636e\u3002";

  if (action === "edit-project") {
    if (!project?.id) {
      recordUiAction(`ia:${action}`, "blocked", noProjectMessage);
      showToast(noProjectMessage);
      return;
    }
    if (isArchivedProject(project)) {
      const message = "归档项目为只读；如需修改，请先恢复到普通项目。";
      recordUiAction(`ia:${action}`, "blocked", message, { project_id: project.id, status: project.status, persistence: "not_mutated" });
      showToast(message);
      return;
    }
    if (isTeachingDemoProject(project)) {
      const message = teachingProtectedMessage();
      recordUiAction(`ia:${action}`, "blocked", message, { project_id: project.id, persistence: "protected_teaching_dataset" });
      showToast(message);
      return;
    }
    const currentName = projectDisplayName(project) || project.name || "\u672a\u547d\u540d\u9879\u76ee";
    const nextName = qs("#realProjectName")?.value.trim();
    if (!nextName || nextName === currentName) {
      const message = nextName === currentName ? "\u9879\u76ee\u540d\u79f0\u672a\u53d8\u66f4\u3002" : "\u8bf7\u5148\u8f93\u5165\u9879\u76ee\u540d\u79f0\u3002";
      recordUiAction(`ia:${action}`, "blocked", message, { project_id: project.id, persistence: "not_mutated" });
      showToast(message);
      return;
    }
    const updated = await apiJson(`/projects/${encodeURIComponent(project.id)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: nextName,
        updated_by: currentAccountId(),
      }),
    });
    state.real.project = updated;
    state.workspace.selectedProjectId = updated.id;
    await refreshProjectWorkspace();
    const message = `\u9879\u76ee\u540d\u79f0\u5df2\u4fdd\u5b58\uff1a${updated.name || nextName}\u3002`;
    recordUiAction(`ia:${action}`, "pass", message, { project_id: updated.id, name: updated.name || nextName, persistence: "backend_patch" });
    showToast(message);
    return;
  }

  if (action === "archive-project") {
    if (!project?.id) {
      recordUiAction(`ia:${action}`, "blocked", noProjectMessage);
      showToast(noProjectMessage);
      return;
    }
    if (isArchivedProject(project)) {
      const message = "该项目已经归档，当前为只读状态。";
      recordUiAction(`ia:${action}`, "blocked", message, { project_id: project.id, status: project.status, persistence: "not_mutated" });
      showToast(message);
      return;
    }
    if (isTeachingDemoProject(project)) {
      const message = teachingProtectedMessage();
      recordUiAction(`ia:${action}`, "blocked", message, { project_id: project.id, persistence: "protected_teaching_dataset" });
      showToast(message);
      return;
    }
    const archived = await apiJson(`/projects/${encodeURIComponent(project.id)}/archive`, { method: "POST" });
    state.real.project = archived;
    state.workspace.selectedProjectId = archived.id;
    await refreshProjectWorkspace();
    const message = `\u9879\u76ee\u5df2\u5f52\u6863\uff1a${archived.name || archived.id}\u3002`;
    recordUiAction(`ia:${action}`, "pass", message, { project_id: archived.id, status: archived.status, persistence: "backend_archive" });
    showToast(message);
    return;
  }

  if (action === "delete-project") {
    if (!project?.id) {
      recordUiAction(`ia:${action}`, "blocked", noProjectMessage);
      showToast(noProjectMessage);
      return;
    }
    if (project?.id && isTeachingDemoProject(project)) {
      const message = teachingProtectedMessage();
      recordUiAction(`ia:${action}`, "blocked", message, { project_id: project.id, persistence: "protected_teaching_dataset" });
      showToast(message);
      return;
    }
    const confirmed = window.confirm(`删除项目「${projectDisplayName(project) || project.id}」？\n\n这会从普通项目列表移除该项目记录；系统保留审计记录，不会删除内置示例数据。`);
    if (!confirmed) {
      const message = "已取消删除项目。";
      recordUiAction(`ia:${action}`, "blocked", message, { project_id: project.id, persistence: "not_mutated" });
      return;
    }
    const deleted = await apiJson(`/projects/${encodeURIComponent(project.id)}`, { method: "DELETE" });
    state.real.project = null;
    state.real.eegFile = null;
    state.real.plan = null;
    state.real.epochSet = null;
    state.workspace.selectedProjectId = null;
    state.workspace.selectedFileId = null;
    state.workspace.selectedPlanId = null;
    clearEegPreviewState();
    await refreshProjectWorkspace();
    const message = `项目已删除：${deleted.name || projectDisplayName(project) || project.id}。`;
    recordUiAction(`ia:${action}`, "pass", message, { project_id: deleted.id || project.id, status: deleted.status || "deleted", persistence: "backend_soft_delete" });
    showToast(message);
    return;
  }

  if (action === "rename-data") {
    if (!file?.id) {
      recordUiAction(`ia:${action}`, "blocked", noFileMessage);
      showToast(noFileMessage);
      return;
    }
    if (isTeachingDemoFile(file) || isTeachingDemoProject(project)) {
      const message = teachingProtectedMessage();
      recordUiAction(`ia:${action}`, "blocked", message, { file_id: file.id, persistence: "protected_teaching_dataset" });
      showToast(message);
      return;
    }
    const baseName = eegFileDisplayName(file) || file.id;
    const nextLabel = baseName.includes("\u5ba1\u6838\u5907\u6ce8") ? baseName : `${baseName} \u00b7 \u5ba1\u6838\u5907\u6ce8`;
    const result = await apiJson(`/data/files/${encodeURIComponent(file.id)}?label=${encodeURIComponent(nextLabel)}`, {
      method: "PATCH",
    });
    const updatedFile = { ...file, metadata_json: { ...(file.metadata_json || {}), label: result.label || nextLabel } };
    state.real.eegFile = updatedFile;
    state.workspace.files = (state.workspace.files || []).map((item) => (item.id === file.id ? updatedFile : item));
    await refreshProjectWorkspace();
    const message = `\u6570\u636e\u6587\u4ef6\u5907\u6ce8\u5df2\u4fdd\u5b58\uff1a${result.label || nextLabel}\u3002`;
    recordUiAction(`ia:${action}`, "pass", message, { file_id: file.id, label: result.label || nextLabel, persistence: "backend_patch" });
    showToast(message);
    return;
  }

  if (action === "mark-bad-channel" || action === "restore-bad-channel") {
    if (!file?.id) {
      recordUiAction(`ia:${action}`, "blocked", noFileMessage);
      showToast(noFileMessage);
      return;
    }
    if (isTeachingDemoFile(file) && !state.teaching.active) {
      const message = teachingProtectedMessage();
      recordUiAction(`ia:${action}`, "blocked", message, { file_id: file.id, persistence: "protected_teaching_dataset" });
      showToast(message);
      return;
    }
    const payload = currentWaveformPayload();
    const firstChannel =
      eegState.hoverChannelName ||
      payload?.channels?.[0]?.name ||
      payload?.channels?.[0] ||
      eegState.data?.channels?.[0] ||
      file.channel_names?.[0] ||
      "EEG001";
    if (action === "mark-bad-channel") {
      const change = {
        id: `bad_channel_${Date.now()}`,
        file_id: file.id,
        channel: String(firstChannel),
        previous_status: "good",
        new_status: "bad",
        reason: "看波形后标记为待复核坏道",
        status: "draft",
        reversible: true,
      };
      prepEditState.badChannels.push(change);
      recordBadChannelHistory("mark", change);
      const message = `已标记坏道：${change.channel}，保存前可恢复。`;
      recordUiAction(`ia:${action}`, "pass", message, { currentFileName, persistence: "ui_draft", prepEditState });
      renderPreparationEditSummary(message);
      redrawCurrentWaveform();
      showToast(message);
      return;
    }
    const restored = prepEditState.badChannels[prepEditState.badChannels.length - 1];
    if (!restored) {
      const message = "当前没有待恢复的坏道修改。";
      recordUiAction(`ia:${action}`, "blocked", message, { currentFileName, persistence: "ui_draft" });
      renderPreparationEditSummary(message);
      showToast(message);
      return;
    }
    const confirmed = window.confirm(`确认恢复最近一次坏道修改：${restored.channel || firstChannel}？恢复后会记录到坏道历史，保存前仍可继续调整。`);
    if (!confirmed) {
      const message = "已取消恢复坏道修改，当前待保存修改保持不变。";
      recordUiAction(`ia:${action}`, "blocked", message, { currentFileName, persistence: "ui_draft", channel: restored.channel || firstChannel });
      renderPreparationEditSummary(message);
      showToast(message);
      return;
    }
    prepEditState.badChannels.pop();
    const restoredChange = { ...restored, previous_status: restored.new_status || "bad", new_status: "good", status: "restored" };
    prepEditState.restoredBadChannels.push(restoredChange);
    recordBadChannelHistory("restore", restoredChange, { confirmed_by_user: true });
    const message = `已恢复坏道修改：${restored.channel || firstChannel}。`;
    recordUiAction(`ia:${action}`, "pass", message, { currentFileName, persistence: "ui_draft", prepEditState });
    renderPreparationEditSummary(message);
    showToast(message);
    return;
  }

  let message = "\u9875\u9762\u52a8\u4f5c\u5df2\u8bb0\u5f55\u3002";
  const selectedSegment = selectedOrManualPrepSegmentRange();
  const requiresSegmentDraft = action === "exclude-segment" || action === "add-label";
  if (requiresSegmentDraft && !file?.id) {
    message = noFileMessage;
    recordUiAction(`ia:${action}`, "blocked", message, { persistence: "not_mutated" });
    renderPreparationEditSummary(message);
    showToast(message);
    return;
  }
  if (requiresSegmentDraft && !selectedSegment) {
    message = "请先在波形上框选片段，或手动输入有效开始/结束时间后再生成片段或标签草稿。";
    recordUiAction(`ia:${action}`, "blocked", message, { currentFileName, persistence: "not_mutated" });
    renderPreparationEditSummary(message);
    showToast(message);
    return;
  }
  const start = Number(selectedSegment?.start_sec);
  const end = Number(selectedSegment?.end_sec);
  if (action === "select-prep-data") {
    message = `已选择 ${currentFileName}，预览会自动刷新。`;
  } else if (action === "exclude-segment") {
    const segment = {
      id: `segment_${Date.now()}`,
      file_id: file.id,
      start_sec: start,
      end_sec: end,
      reason: "人工标记为伪迹或需剔除片段",
      status: "excluded",
    };
    prepEditState.excludedSegments.push(segment);
    message = `已剔除 ${segment.start_sec.toFixed(1)}-${segment.end_sec.toFixed(1)} s，可随时恢复。`;
  } else if (action === "restore-segment") {
    const segment = prepEditState.excludedSegments.pop();
    if (!segment) {
      message = "当前没有待恢复的剔除片段。";
      recordUiAction(`ia:${action}`, "blocked", message, { currentFileName, persistence: "ui_draft" });
      renderPreparationEditSummary(message);
      showToast(message);
      return;
    }
    segment.status = "restored";
    prepEditState.restoredSegments.push(segment);
    message = `已恢复 ${segment.start_sec.toFixed(1)}-${segment.end_sec.toFixed(1)} s 片段。`;
  } else if (action === "add-label") {
    const label = {
      id: `label_${Date.now()}`,
      file_id: file.id,
      previous_text: null,
      text: "运动伪迹 / 需要复核",
      target: `${start.toFixed(1)} s`,
      status: "active",
      reversible: true,
    };
    prepEditState.labels.push(label);
    message = `已添加标签：${label.text}。`;
  } else if (action === "edit-label") {
    const label = prepEditState.labels[prepEditState.labels.length - 1];
    if (label) {
      label.previous_text = label.text;
      label.text = "运动伪迹 / 已复核";
      label.status = "edited";
      label.reversible = true;
      message = `已更新标签：${label.previous_text} → ${label.text}，可恢复。`;
    } else {
      message = "当前没有可编辑的标签，请先选择片段并添加标签。";
      recordUiAction(`ia:${action}`, "blocked", message, { currentFileName, persistence: "not_mutated" });
      renderPreparationEditSummary(message);
      showToast(message);
      return;
    }
  } else if (action === "restore-label") {
    const label = prepEditState.labels[prepEditState.labels.length - 1];
    if (!label) {
      message = "当前没有可恢复的标签修改。";
      recordUiAction(`ia:${action}`, "blocked", message, { currentFileName, persistence: "ui_draft" });
      renderPreparationEditSummary(message);
      showToast(message);
      return;
    }
    const beforeText = label.text;
    const restoredText = label.previous_text;
    if (restoredText) {
      label.text = restoredText;
      label.status = "restored";
      prepEditState.restoredLabels.push({ ...label, before_text: beforeText, after_text: restoredText, action: "restore" });
      message = `已恢复标签：${beforeText} → ${restoredText}。`;
    } else {
      const removed = prepEditState.labels.pop();
      prepEditState.restoredLabels.push({ ...removed, before_text: beforeText, after_text: null, action: "restore" });
      message = `已恢复新增标签：${beforeText}。`;
    }
  }
  renderPreparationEditSummary(message);
  redrawCurrentWaveform();
  recordUiAction(`ia:${action}`, "pass", message, { currentFileName, persistence: "ui_draft", prepEditState });
  showToast(message);
}

function parseCsvText(text) {
  const lines = String(text || "").trim().split(/\r?\n/).filter(Boolean);
  if (!lines.length) return [];
  const parseLine = (line) => {
    const cells = [];
    let current = "";
    let quoted = false;
    for (let i = 0; i < line.length; i += 1) {
      const char = line[i];
      if (char === '"' && line[i + 1] === '"') {
        current += '"';
        i += 1;
      } else if (char === '"') {
        quoted = !quoted;
      } else if (char === "," && !quoted) {
        cells.push(current);
        current = "";
      } else {
        current += char;
      }
    }
    cells.push(current);
    return cells;
  };
  const headers = parseLine(lines[0]).map((item) => item.trim());
  return lines.slice(1).map((line) => {
    const values = parseLine(line);
    return Object.fromEntries(headers.map((header, index) => [header, values[index] ?? ""]));
  });
}

function artifactByLabel(artifacts, labels = []) {
  const wanted = labels.map((item) => String(item).toLowerCase());
  return (artifacts || []).find((artifact) => {
    const label = String(artifact?.label || artifact?.artifact_label || artifact?.name || "").toLowerCase();
    const path = String(artifact?.path || artifact?.relative_path || artifact?.filename || "").toLowerCase();
    return wanted.some((item) => label === item || label.includes(item) || path.includes(item));
  }) || null;
}

function artifactSearchText(artifact = {}) {
  return [
    artifact?.label,
    artifact?.artifact_label,
    artifact?.name,
    artifact?.path,
    artifact?.relative_path,
    artifact?.object_key,
    artifact?.filename,
  ].map((item) => String(item || "").toLowerCase()).join(" ");
}

function artifactBelongsToTask(artifact, taskId) {
  const text = artifactSearchText(artifact);
  const normalizedTaskId = String(taskId || "").toLowerCase();
  return Boolean(normalizedTaskId && text.includes(`/${normalizedTaskId}/`)) || Boolean(normalizedTaskId && text.includes(`\${normalizedTaskId}\\`));
}

function findInlineEpilepsyTaskArtifact(artifacts, taskId, candidates = []) {
  const scopedArtifacts = (artifacts || []).filter((artifact) => {
    const text = artifactSearchText(artifact);
    if (text.includes("/data_preparation/") || text.includes("\\data_preparation\\")) return false;
    return artifactBelongsToTask(artifact, taskId);
  });
  const rankedCandidates = candidates.map((candidate, index) => ({
    index,
    label: String(candidate.label || "").toLowerCase(),
    path: String(candidate.path || "").toLowerCase(),
  }));
  const exactLabelMatch = scopedArtifacts.find((artifact) => {
    const label = String(artifact?.label || artifact?.artifact_label || artifact?.name || "").toLowerCase();
    return rankedCandidates.some((candidate) => candidate.label && label === candidate.label);
  });
  if (exactLabelMatch) return exactLabelMatch;
  return scopedArtifacts.find((artifact) => {
    const text = artifactSearchText(artifact);
    return rankedCandidates.some((candidate) => candidate.path && text.includes(candidate.path));
  }) || null;
}

async function fetchArtifactText(artifact) {
  if (!artifact?.id) return "";
  const response = await fetch(`${state.apiBase}/artifacts/${encodeURIComponent(artifact.id)}/download`, {
    method: "GET",
    headers: withAuthHeaders({ Accept: "text/plain,application/json,text/csv,*/*" }),
    cache: "no-store",
  });
  if (!response.ok) throw new Error(`Artifact download failed: ${response.status}`);
  return response.text();
}

async function loadInlineEpilepsyResultData(task, artifacts) {
  const epochArtifact = findInlineEpilepsyTaskArtifact(artifacts, task?.id, [
    { label: "epilepsy_epoch_scores" },
    { label: "epilepsy_ml_epoch_predictions" },
    { path: "tables/epilepsy_ml_epoch_predictions.csv" },
    { path: "tables/epilepsy_epoch_scores.csv" },
  ]);
  const eventArtifact = findInlineEpilepsyTaskArtifact(artifacts, task?.id, [
    { label: "epilepsy_events" },
    { label: "epilepsy_ml_events" },
    { path: "tables/epilepsy_ml_events.csv" },
    { path: "tables/epilepsy_events.csv" },
  ]);
  const spectrogramArtifact = findInlineEpilepsyTaskArtifact(artifacts, task?.id, [
    { label: "epilepsy_ml_spectrogram" },
    { path: "data/epilepsy_ml_spectrogram.json" },
  ]);
  if (!task?.id || !epochArtifact) {
    state.epilepsyInline.resultTaskId = task?.id || "";
    state.epilepsyInline.epochRows = [];
    state.epilepsyInline.eventRows = [];
    state.epilepsyInline.resultLoadStatus = "missing_artifacts";
    state.epilepsyInline.resultLoadError = "";
    state.epilepsyInline.spectrogramPayload = null;
    state.epilepsyInline.spectrogramLoadStatus = spectrogramArtifact ? "idle" : "missing_artifact";
    state.epilepsyInline.spectrogramLoadError = "";
    return;
  }
  state.epilepsyInline.resultLoadStatus = "loading";
  state.epilepsyInline.resultLoadError = "";
  state.epilepsyInline.spectrogramLoadStatus = spectrogramArtifact ? "loading" : "missing_artifact";
  state.epilepsyInline.spectrogramLoadError = "";
  try {
    const [epochText, eventText, spectrogramText] = await Promise.all([
      fetchArtifactText(epochArtifact),
      eventArtifact ? fetchArtifactText(eventArtifact) : Promise.resolve(""),
      spectrogramArtifact ? fetchArtifactText(spectrogramArtifact) : Promise.resolve(""),
    ]);
    state.epilepsyInline.resultTaskId = task.id;
    state.epilepsyInline.epochRows = parseCsvText(epochText);
    state.epilepsyInline.eventRows = parseCsvText(eventText);
    if (spectrogramText) {
      state.epilepsyInline.spectrogramPayload = JSON.parse(spectrogramText);
      state.epilepsyInline.spectrogramLoadStatus = "ready";
    } else {
      state.epilepsyInline.spectrogramPayload = null;
      state.epilepsyInline.spectrogramLoadStatus = "missing_artifact";
    }
    state.epilepsyInline.resultLoadStatus = "ready";
  } catch (error) {
    state.epilepsyInline.resultTaskId = task.id;
    state.epilepsyInline.epochRows = [];
    state.epilepsyInline.eventRows = [];
    state.epilepsyInline.resultLoadStatus = "failed";
    state.epilepsyInline.resultLoadError = error.message || String(error);
    state.epilepsyInline.spectrogramPayload = null;
    state.epilepsyInline.spectrogramLoadStatus = "failed";
    state.epilepsyInline.spectrogramLoadError = error.message || String(error);
  }
}

function inlineEpilepsyTask() {
  return state.real.tasks?.epilepsy_ml || null;
}

function inlineEpilepsyArtifacts() {
  return state.real.artifacts?.epilepsy_ml || [];
}

function inlineEpilepsyCandidateEvents() {
  var eventRows = state.epilepsyInline.eventRows || [];
  if (eventRows.length === 0) {
    // Fallback: synthesize candidate events from epochRows with Stage_Code=1
    // when the backend screening pipeline did not register an events CSV artifact.
    var epochRows = state.epilepsyInline.epochRows || [];
    var epochDur = Number((epochRows[0] && (epochRows[0].duration_sec || epochRows[0].duration)) || 5);
    var idx = 0;
    return epochRows
      .map(function (row, index) {
        var code = Number(row.Stage_Code ?? row.stage_code ?? row.prediction ?? 0);
        if (code !== 1) return null;
        idx += 1;
        var startSec = Number(row.start_sec ?? row.start ?? index * epochDur);
        var endSec = Number(row.end_sec ?? row.end ?? (startSec + epochDur));
        return {
          id: "E-" + String(idx).padStart(3, "0"),
          label: "候选事件 " + idx + "（来自 Stage_Code）",
          start: Number.isFinite(startSec) ? startSec : index * epochDur,
          end: Number.isFinite(endSec) && endSec > startSec ? endSec : startSec + epochDur,
          startEpoch: row.epoch_index ?? index,
          endEpoch: row.epoch_index ?? index,
          source: row,
        };
      })
      .filter(Boolean);
  }
  return eventRows.map((row, index) => {
    const start = Number(row.start_sec ?? row.start ?? row.onset_sec ?? 0);
    const end = Number(row.end_sec ?? row.end ?? (start + Number(row.duration_sec || 0)));
    const label = row.event_id || row.id || `evt-${index + 1}`;
    return {
      id: String(label),
      label: `候选事件 ${index + 1}`,
      start,
      end: Number.isFinite(end) && end > start ? end : start,
      startEpoch: row.start_epoch ?? row.start_epoch_index ?? "",
      endEpoch: row.end_epoch ?? row.end_epoch_index ?? "",
      source: row,
    };
  });
}

function inlineEpilepsySelectedEvent(events = inlineEpilepsyCandidateEvents()) {
  return events.find((event) => event.id === state.epilepsyInline.selectedEventId) || events[0] || null;
}

function inlineEpilepsyReaderState() {
  if (!state.epilepsyInline.reader) state.epilepsyInline.reader = {};
  const reader = state.epilepsyInline.reader;
  reader.startSec = Math.max(0, Number(reader.startSec || 0));
  reader.durationSec = Math.max(
    EDF_BROWSER_INTERACTION_CONSTANTS.minWindowSec,
    Math.min(EDF_BROWSER_INTERACTION_CONSTANTS.maxWindowSec, Number(reader.durationSec || state.epilepsyInline.timeScaleSec || 30)),
  );
  reader.sensitivityUvPerRow = Math.max(
    EDF_BROWSER_INTERACTION_CONSTANTS.minSensitivityUvPerRow,
    Math.min(EDF_BROWSER_INTERACTION_CONSTANTS.maxSensitivityUvPerRow, Number(reader.sensitivityUvPerRow || 50)),
  );
  reader.visibleChannelCount = Math.max(1, Math.min(64, Number(reader.visibleChannelCount || 8)));
  reader.overlayVisibility = {
    candidates: reader.overlayVisibility?.candidates !== false,
    stageCode: reader.overlayVisibility?.stageCode !== false,
    reviewEdits: reader.overlayVisibility?.reviewEdits !== false,
  };
  return reader;
}

function inlineEpilepsyFileDuration(file = currentWorkspaceFile() || state.real.eegFile || {}) {
  const payload = state.epilepsyInline.waveformPayload || {};
  return Number(file?.duration_sec || file?.metadata_json?.duration_sec || file?.metadata_json?.duration || payload.file_duration_sec || 60) || 60;
}

function clampInlineEpilepsyReader(file = currentWorkspaceFile() || state.real.eegFile || {}) {
  const reader = inlineEpilepsyReaderState();
  const durationTotal = Math.max(EDF_BROWSER_INTERACTION_CONSTANTS.minWindowSec, inlineEpilepsyFileDuration(file));
  reader.durationSec = Math.max(
    EDF_BROWSER_INTERACTION_CONSTANTS.minWindowSec,
    Math.min(EDF_BROWSER_INTERACTION_CONSTANTS.maxWindowSec, durationTotal, Number(reader.durationSec || 30)),
  );
  reader.startSec = Math.max(0, Math.min(Math.max(0, durationTotal - reader.durationSec), Number(reader.startSec || 0)));
  state.epilepsyInline.timeScaleSec = reader.durationSec;
  return { reader, durationTotal };
}

function setInlineEpilepsyViewport({ file = currentWorkspaceFile() || state.real.eegFile || {}, startSec, durationSec, anchorRatio = 0.5 } = {}) {
  const reader = inlineEpilepsyReaderState();
  const previousStart = Number(reader.startSec || 0);
  const previousDuration = Number(reader.durationSec || 30);
  const durationTotal = Math.max(EDF_BROWSER_INTERACTION_CONSTANTS.minWindowSec, inlineEpilepsyFileDuration(file));
  const nextDuration = Math.max(
    EDF_BROWSER_INTERACTION_CONSTANTS.minWindowSec,
    Math.min(EDF_BROWSER_INTERACTION_CONSTANTS.maxWindowSec, durationTotal, Number(durationSec ?? previousDuration)),
  );
  const anchor = Math.max(0, Math.min(1, Number(anchorRatio)));
  const anchoredTime = previousStart + previousDuration * anchor;
  const proposedStart = Number.isFinite(Number(startSec))
    ? Number(startSec)
    : anchoredTime - nextDuration * anchor;
  reader.durationSec = nextDuration;
  reader.startSec = Math.max(0, Math.min(Math.max(0, durationTotal - nextDuration), proposedStart));
  state.epilepsyInline.timeScaleSec = reader.durationSec;
  return { start_sec: reader.startSec, duration_sec: reader.durationSec, duration_total_sec: durationTotal };
}

function panInlineEpilepsyViewport(ratio, file = currentWorkspaceFile() || state.real.eegFile || {}) {
  const reader = inlineEpilepsyReaderState();
  return setInlineEpilepsyViewport({ file, startSec: reader.startSec + reader.durationSec * Number(ratio || 0) });
}

function zoomInlineEpilepsyViewport(factor, anchorRatio = 0.5, file = currentWorkspaceFile() || state.real.eegFile || {}) {
  const reader = inlineEpilepsyReaderState();
  return setInlineEpilepsyViewport({ file, durationSec: reader.durationSec * Number(factor || 1), anchorRatio });
}

function centerInlineEpilepsyEvent(event, file = currentWorkspaceFile() || state.real.eegFile || {}) {
  if (!event) return inlineEpilepsyWaveformWindow(file);
  const reader = inlineEpilepsyReaderState();
  const center = (Number(event.start || 0) + Number(event.end || event.start || 0)) / 2;
  return setInlineEpilepsyViewport({ file, startSec: center - reader.durationSec / 2 });
}

function selectInlineEpilepsyEvent(eventId, { center = false, file = currentWorkspaceFile() || state.real.eegFile || {} } = {}) {
  const events = inlineEpilepsyCandidateEvents();
  const event = events.find((item) => item.id === eventId) || null;
  if (!event) return null;
  state.epilepsyInline.selectedEventId = event.id;
  if (center) centerInlineEpilepsyEvent(event, file);
  return event;
}

function selectInlineEpilepsyRelativeCandidate(delta, { file = currentWorkspaceFile() || state.real.eegFile || {} } = {}) {
  const events = inlineEpilepsyCandidateEvents();
  if (!events.length) return null;
  const currentIndex = Math.max(0, events.findIndex((event) => event.id === state.epilepsyInline.selectedEventId));
  const nextIndex = Math.max(0, Math.min(events.length - 1, currentIndex + Number(delta || 0)));
  return selectInlineEpilepsyEvent(events[nextIndex].id, { center: true, file });
}

function inlineEpilepsyLatestCorrection(eventId) {
  return [...(state.epilepsyInline.draftCommands || [])].reverse().find((item) => item.eventId === eventId) || null;
}

function inlineEpilepsyEventForEpoch(epochIndex, events = inlineEpilepsyCandidateEvents()) {
  const idx = Number(epochIndex);
  if (!Number.isFinite(idx)) return null;
  return events.find((event) => idx >= Number(event.startEpoch || 0) && idx <= Number(event.endEpoch || event.startEpoch || 0)) || null;
}

function inlineEpilepsySummaryCounts(events) {
  const epochs = state.epilepsyInline.epochRows || [];
  const seizureEpochs = epochs.filter((row) => Number(row.Stage_Code ?? row.stage_code ?? row.prediction ?? 0) === 1).length;
  return { epochCount: epochs.length, eventCount: events.length, seizureEpochs };
}

function inlineReviewStatusFromLabel(label) {
  const value = String(label || "").toLowerCase();
  if (value.includes("伪迹") || value.includes("artifact")) return "rejected";
  if (value.includes("排除") || value.includes("exclude") || value.includes("reject")) return "rejected";
  if (value.includes("保留") || value.includes("keep") || value.includes("candidate")) return "confirmed";
  if (value.includes("复核") || value.includes("review")) return "needs_review";
  if (value.includes("normal")) return "rejected";
  if (value.includes("needs")) return "needs_review";
  if (value.includes("seizure")) return "confirmed";
  return "unreviewed";
}

function inlineEpilepsyDraftReviewPayload() {
  const epochOverrides = {};
  const eventReviews = {};
  const actions = [];
  const events = inlineEpilepsyCandidateEvents();
  (state.epilepsyInline.draftCommands || []).forEach((command, index) => {
    const event = events.find((item) => item.id === command.eventId) || {};
    const status = inlineReviewStatusFromLabel(command.label);
    if ((status === "confirmed" || status === "rejected") && command.actionType !== "adjust_event_interval") {
      const stageCode = status === "confirmed" ? 1 : 0;
      const startEpoch = Number(event.startEpoch ?? 0);
      const endEpoch = Number(event.endEpoch ?? startEpoch);
      for (let epoch = startEpoch; epoch <= endEpoch; epoch += 1) epochOverrides[String(epoch)] = stageCode;
    }
    eventReviews[command.eventId] = {
      event_id: command.eventId,
      status,
      note: `Manual review: ${command.displayLabel || command.label}`,
      reviewer: currentAccountId(),
      reviewed_at: command.at || new Date().toISOString(),
    };
    actions.push({
      type: command.actionType || "event_review",
      target_range: {
        start: Number(event.startEpoch ?? 0),
        end: Number(event.endEpoch ?? event.startEpoch ?? 0),
      },
      before: {
        source_event_id: command.eventId,
        start_sec: Number(event.start || 0),
        end_sec: Number(event.end || event.start || 0),
      },
      after: {
        label: command.label,
        display_label: command.displayLabel || command.label,
        status,
        adjusted_start_sec: command.adjustedStartSec,
        adjusted_end_sec: command.adjustedEndSec,
      },
      note: `Inline epilepsy workbench correction #${index + 1}`,
      source: "main-inline-epilepsy-workbench",
      created_at: command.at || new Date().toISOString(),
    });
  });
  return { epoch_overrides: epochOverrides, event_reviews: eventReviews, actions };
}

async function ensureInlineEpilepsyReviewSession() {
  const existing = state.epilepsyInline.reviewSession;
  if (existing?.id) return existing;
  const task = inlineEpilepsyTask();
  const file = currentWorkspaceFile() || state.real.eegFile || {};
  const plan = state.real.plan || {};
  if (!task?.id) throw new Error("请先运行癫痫样候选事件初筛，再保存人工复核标注。");
  const session = await apiJson(`/tasks/${encodeURIComponent(task.id)}/epilepsy-review-sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      input_file_id: file.id || task.input_file_id || "",
      workflow_id: task.workflow_id || "epilepsy_ml_xgboost",
      epoch_length_sec: 5,
      current_epoch: 0,
      selected_range: { start: 0, end: 0 },
      ui_state: {
        source: "main-inline-epilepsy-workbench",
        time_scale_sec: Number(state.epilepsyInline.timeScaleSec || 30),
        selected_event_id: state.epilepsyInline.selectedEventId || "",
      },
      data_preparation_plan_id: plan.id || task.parameters_json?.data_preparation_plan_id || null,
      data_preparation_revision: Number(plan.revision || task.parameters_json?.data_preparation_revision || 0) || null,
      data_preparation_contract_version: dataPreparationContractVersion(plan) || task.parameters_json?.data_preparation_contract_version || DATA_PREPARATION_CONTRACT_VERSION,
    }),
  });
  state.epilepsyInline.reviewSession = session;
  return session;
}

async function saveInlineEpilepsyReviewDraft() {
  if (!state.epilepsyInline.draftCommands.length) throw new Error("暂无人工复核标注草稿可保存。");
  state.epilepsyInline.reviewSaveStatus = "saving";
  state.epilepsyInline.reviewSaveError = "";
  renderInlineEpilepsyWorkbench();
  try {
    const session = await ensureInlineEpilepsyReviewSession();
    const patch = inlineEpilepsyDraftReviewPayload();
    const saved = await apiJson(`/epilepsy-review-sessions/${encodeURIComponent(session.id)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        status: "reviewing",
        ...patch,
        ui_state: {
          source: "main-inline-epilepsy-workbench",
          time_scale_sec: Number(state.epilepsyInline.timeScaleSec || 30),
          selected_event_id: state.epilepsyInline.selectedEventId || "",
          draft_count: state.epilepsyInline.draftCommands.length,
        },
      }),
    });
    state.epilepsyInline.reviewSession = saved;
    state.epilepsyInline.reviewSaveStatus = "saved";
    state.epilepsyInline.reviewSaveError = "";
    state.epilepsyInline.draftSaved = true;
    state.epilepsyInline.published = false;
    showToast("人工复核标注草稿已保存到复核记录。");
  } catch (error) {
    state.epilepsyInline.reviewSaveStatus = "failed";
    state.epilepsyInline.reviewSaveError = error.message || String(error);
    state.epilepsyInline.draftSaved = false;
    showToast(`保存复核草稿失败：${state.epilepsyInline.reviewSaveError}`);
  } finally {
    renderInlineEpilepsyWorkbench();
  }
}

async function exportInlineEpilepsyReviewResults() {
  if (!state.epilepsyInline.draftSaved || !state.epilepsyInline.reviewSession?.id) throw new Error("请先保存人工复核标注草稿。");
  state.epilepsyInline.exportStatus = "exporting";
  state.epilepsyInline.exportError = "";
  renderInlineEpilepsyWorkbench();
  try {
    const exported = await apiJson(`/epilepsy-review-sessions/${encodeURIComponent(state.epilepsyInline.reviewSession.id)}/exports`, { method: "POST" });
    state.epilepsyInline.exportResult = exported;
    state.epilepsyInline.exportStatus = "exported";
    state.epilepsyInline.exportError = "";
    state.epilepsyInline.published = true;
    const artifacts = await fetchTaskArtifacts(exported.task_id || inlineEpilepsyTask()?.id).catch(() => []);
    if (artifacts?.length) state.real.artifacts.epilepsy_ml = artifacts;
    renderRealResultReview();
    renderRealDelivery();
    publishE2EState();
    showToast("人工复核标注结果已生成，可进入结果页查看。");
  } catch (error) {
    state.epilepsyInline.exportStatus = "failed";
    state.epilepsyInline.exportError = error.message || String(error);
    state.epilepsyInline.published = false;
    showToast(`发布复核结果失败：${state.epilepsyInline.exportError}`);
  } finally {
    renderInlineEpilepsyWorkbench();
    publishE2EState();
  }
}

function normalizeInlineWaveformPayload(payload = {}) {
  const channels = Array.isArray(payload.channels) ? payload.channels : [];
  const data_uv = (Array.isArray(payload.data_uv) ? payload.data_uv : []).map((row) => Array.isArray(row) ? row.map((value) => Number(value) || 0) : []);
  let times = (Array.isArray(payload.times_sec) ? payload.times_sec : []).map(Number).filter(Number.isFinite);
  if (!times.length && data_uv[0]?.length) {
    const start = Number(payload.start_sec || 0);
    const duration = Number(payload.duration_sec || 0) || Math.max(1, data_uv[0].length / Number(payload.display_sample_rate_hz || 200));
    const step = duration / Math.max(1, data_uv[0].length - 1);
    times = Array.from({ length: data_uv[0].length }, (_, index) => start + index * step);
  }
  return {
    ...payload,
    channels,
    data_uv,
    times_sec: times,
    start_sec: Number(payload.start_sec || (times[0] ?? 0)),
    duration_sec: Number(payload.duration_sec || Math.max(0, (times.at(-1) ?? 0) - (times[0] ?? 0))),
    file_duration_sec: Number(payload.file_duration_sec || payload.duration_total_sec || 0),
    display_sample_rate_hz: Number(payload.display_sample_rate_hz || payload.sfreq_display || 200),
  };
}

function inlineEpilepsyWaveformWindow(file) {
  const { reader, durationTotal } = clampInlineEpilepsyReader(file);
  return { start_sec: reader.startSec, duration_sec: reader.durationSec, duration_total_sec: durationTotal };
}

function inlineEpilepsyWaveformRequestKey(file) {
  if (!file?.id) return "";
  const win = inlineEpilepsyWaveformWindow(file);
  const reader = inlineEpilepsyReaderState();
  return `${file.id}|${win.start_sec.toFixed(3)}|${win.duration_sec.toFixed(3)}|${reader.visibleChannelCount}|minmax`;
}

function inlineEpilepsyWaveformHasRenderablePayload() {
  return Boolean(state.epilepsyInline.waveformPayload?.data_uv?.length);
}

function inlineEpilepsyDisplayedReaderWindow(file = currentWorkspaceFile() || state.real.eegFile || {}) {
  const { reader, durationTotal } = clampInlineEpilepsyReader(file);
  const payload = state.epilepsyInline.waveformPayload || {};
  const payloadReady = inlineEpilepsyWaveformHasRenderablePayload();
  const payloadStart = Number(payload.start_sec);
  const payloadDuration = Number(payload.duration_sec);
  const displayStart = payloadReady && Number.isFinite(payloadStart) ? payloadStart : reader.startSec;
  const displayDuration = payloadReady && Number.isFinite(payloadDuration) && payloadDuration > 0 ? payloadDuration : reader.durationSec;
  return {
    displayStartSec: Math.max(0, Math.min(Math.max(0, durationTotal - displayDuration), displayStart)),
    displayDurationSec: Math.max(EDF_BROWSER_INTERACTION_CONSTANTS.minWindowSec, Math.min(durationTotal, displayDuration)),
    durationTotal,
  };
}

function inlineEpilepsyWaveformCache() {
  if (!(state.epilepsyInline.waveformCache instanceof Map)) state.epilepsyInline.waveformCache = new Map();
  return state.epilepsyInline.waveformCache;
}

function rememberInlineEpilepsyWaveformPayload(requestKey, payload) {
  const cache = inlineEpilepsyWaveformCache();
  cache.delete(requestKey);
  cache.set(requestKey, payload);
  while (cache.size > INLINE_EPILEPSY_WAVEFORM_CACHE_LIMIT) {
    const oldest = cache.keys().next().value;
    cache.delete(oldest);
  }
}

function syncInlineEpilepsyWaveformDom() {
  const shell = qs(".inline-wave-canvas");
  const status = qs('[data-testid="inline-epilepsy-waveform-status"]');
  const canvas = qs('[data-testid="inline-epilepsy-waveform-canvas"]');
  const payload = state.epilepsyInline.waveformPayload;
  const ready = inlineEpilepsyWaveformHasRenderablePayload();
  const fetchStatus = state.epilepsyInline.waveformFetchStatus || state.epilepsyInline.waveformStatus || "idle";
  if (shell) {
    shell.classList.toggle("ready", ready);
    shell.classList.toggle("blocked", !ready);
    shell.dataset.waveformStatus = state.epilepsyInline.waveformStatus || "idle";
    shell.dataset.waveformFetchStatus = fetchStatus;
    if (ready) shell.querySelector(".inline-wave-message")?.remove();
  }
  if (status) {
    status.classList.toggle("ready", ready);
    status.classList.toggle("blocked", !ready);
    status.textContent = ready
      ? `已加载波形 · ${(payload.channels || []).slice(0, 8).length} 通道`
      : "等待波形窗口";
  }
  if (canvas) {
    canvas.dataset.waveformStatus = state.epilepsyInline.waveformStatus || "idle";
    canvas.dataset.waveformFetchStatus = fetchStatus;
    canvas.dataset.hasWaveform = ready ? "true" : "false";
  }
}

function ensureInlineEpilepsyWaveform(file) {
  if (!file?.id) {
    state.epilepsyInline.waveformStatus = "missing_file";
    state.epilepsyInline.waveformFetchStatus = "idle";
    state.epilepsyInline.waveformError = "请先选择 EEG 数据。";
    state.epilepsyInline.waveformPayload = null;
    state.epilepsyInline.waveformRequestKey = "";
    state.epilepsyInline.waveformPayloadKey = "";
    state.epilepsyInline.waveformActiveRequestKey = "";
    if (state.epilepsyInline.waveformAbortController) state.epilepsyInline.waveformAbortController.abort();
    if (state.epilepsyInline.waveformDebounceTimer) window.clearTimeout(state.epilepsyInline.waveformDebounceTimer);
    return;
  }
  const reader = inlineEpilepsyReaderState();
  const requestKey = inlineEpilepsyWaveformRequestKey(file);
  if (!requestKey) return;
  if (state.epilepsyInline.waveformPayloadKey === requestKey && inlineEpilepsyWaveformHasRenderablePayload()) {
    state.epilepsyInline.waveformRequestKey = requestKey;
    state.epilepsyInline.waveformStatus = "ready";
    state.epilepsyInline.waveformFetchStatus = "ready";
    return;
  }
  const cached = inlineEpilepsyWaveformCache().get(requestKey);
  if (cached?.data_uv?.length) {
    state.epilepsyInline.waveformRequestKey = requestKey;
    state.epilepsyInline.waveformPayloadKey = requestKey;
    state.epilepsyInline.waveformPayload = cached;
    state.epilepsyInline.waveformStatus = "ready";
    state.epilepsyInline.waveformFetchStatus = "ready";
    state.epilepsyInline.waveformError = "";
    syncInlineEpilepsyWaveformDom();
    window.requestAnimationFrame(() => drawInlineEpilepsyWaveform());
    return;
  }
  if (state.epilepsyInline.waveformActiveRequestKey === requestKey && state.epilepsyInline.waveformFetchStatus === "loading") return;
  const win = inlineEpilepsyWaveformWindow(file);
  state.epilepsyInline.waveformRequestKey = requestKey;
  state.epilepsyInline.waveformStatus = inlineEpilepsyWaveformHasRenderablePayload() ? "ready" : "loading";
  state.epilepsyInline.waveformFetchStatus = "loading";
  state.epilepsyInline.waveformError = "";
  if (state.epilepsyInline.waveformDebounceTimer) window.clearTimeout(state.epilepsyInline.waveformDebounceTimer);
  const query = new URLSearchParams({
    start_sec: String(Number(win.start_sec.toFixed(3))),
    duration_sec: String(Number(win.duration_sec.toFixed(3))),
    channel_limit: String(reader.visibleChannelCount),
    display_sfreq: "200",
    mode: "minmax",
    width_px: "1440",
  });
  state.epilepsyInline.waveformDebounceTimer = window.setTimeout(() => {
    if (state.epilepsyInline.waveformRequestKey !== requestKey) return;
    if (state.epilepsyInline.waveformAbortController) state.epilepsyInline.waveformAbortController.abort();
    const controller = new AbortController();
    state.epilepsyInline.waveformAbortController = controller;
    state.epilepsyInline.waveformActiveRequestKey = requestKey;
    apiJson(`/eeg/files/${encodeURIComponent(file.id)}/waveform/chunk?${query.toString()}`, { signal: controller.signal })
      .then((payload) => {
        if (state.epilepsyInline.waveformRequestKey !== requestKey) return;
        const normalized = normalizeInlineWaveformPayload(payload);
        state.epilepsyInline.waveformPayload = normalized;
        state.epilepsyInline.waveformPayloadKey = requestKey;
        state.epilepsyInline.waveformStatus = "ready";
        state.epilepsyInline.waveformFetchStatus = "ready";
        state.epilepsyInline.waveformError = "";
        rememberInlineEpilepsyWaveformPayload(requestKey, normalized);
        renderInlineEpilepsyWorkbench();
        syncInlineEpilepsyWaveformDom();
        window.requestAnimationFrame(() => drawInlineEpilepsyWaveform());
      })
      .catch((error) => {
        if (error?.name === "AbortError" || state.epilepsyInline.waveformRequestKey !== requestKey) return;
        state.epilepsyInline.waveformFetchStatus = "failed";
        if (!inlineEpilepsyWaveformHasRenderablePayload()) {
          state.epilepsyInline.waveformPayload = null;
          state.epilepsyInline.waveformPayloadKey = "";
          state.epilepsyInline.waveformStatus = "failed";
        }
        state.epilepsyInline.waveformError = error.message || String(error);
        syncInlineEpilepsyWaveformDom();
      })
      .finally(() => {
        if (state.epilepsyInline.waveformActiveRequestKey === requestKey) state.epilepsyInline.waveformActiveRequestKey = "";
        if (state.epilepsyInline.waveformAbortController === controller) state.epilepsyInline.waveformAbortController = null;
      });
  }, INLINE_EPILEPSY_WAVEFORM_FETCH_DEBOUNCE_MS);
}

function drawInlineEpilepsyWaveform() {
  const canvas = qs('[data-testid="inline-epilepsy-waveform-canvas"]');
  const payload = state.epilepsyInline.waveformPayload;
  if (!canvas?.getContext || !payload?.data_uv?.length) return;
  const ctx = canvas.getContext("2d");
  const rect = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  const width = Math.max(720, Math.floor(rect.width || 900));
  const height = Math.max(280, Math.floor(rect.height || 360));
  canvas.width = Math.floor(width * dpr);
  canvas.height = Math.floor(height * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, width, height);
  const left = 72;
  const right = 18;
  const top = 26;
  const bottom = 32;
  const plotW = width - left - right;
  const plotH = height - top - bottom;
  const times = payload.times_sec || [];
  const start = Number(payload.start_sec || times[0] || 0);
  const end = start + Number(payload.duration_sec || Math.max(1, (times.at(-1) || start + 1) - start));
  const reader = inlineEpilepsyReaderState();
  canvas.dataset.stageOverlay = reader.overlayVisibility.stageCode ? "visible" : "hidden";
  const channels = payload.channels || [];
  const rows = payload.data_uv || [];
  const visible = Math.min(reader.visibleChannelCount, channels.length || rows.length, rows.length);
  const rowH = plotH / Math.max(1, visible);
  ctx.strokeStyle = "rgba(42,79,120,.12)";
  ctx.lineWidth = 1;
  for (let i = 0; i <= 6; i += 1) {
    const x = left + (plotW * i / 6);
    ctx.beginPath();
    ctx.moveTo(x, top);
    ctx.lineTo(x, top + plotH);
    ctx.stroke();
    ctx.fillStyle = "#789";
    ctx.font = "11px Segoe UI";
    ctx.fillText(`${(start + (end - start) * i / 6).toFixed(1)}s`, x - 10, height - 10);
  }
  for (let c = 0; c < visible; c += 1) {
    const y0 = top + rowH * (c + 0.5);
    ctx.strokeStyle = "rgba(148,163,184,.22)";
    ctx.beginPath();
    ctx.moveTo(left, y0);
    ctx.lineTo(left + plotW, y0);
    ctx.stroke();
    ctx.fillStyle = "#4b5c6b";
    ctx.font = "12px Segoe UI";
    ctx.fillText(channels[c] || `Ch${c + 1}`, 12, y0 + 4);
    const row = rows[c] || [];
    if (!row.length) continue;
    const scale = (rowH * 0.42) / Math.max(1, Number(reader.sensitivityUvPerRow || 50));
    ctx.strokeStyle = ["#155c9c", "#157a77", "#7c3aed", "#c2410c", "#0f766e", "#9333ea", "#b45309", "#0369a1"][c % 8];
    ctx.lineWidth = 1.12;
    ctx.beginPath();
    for (let i = 0; i < row.length; i += 1) {
      const t = Number(times[i]);
      if (!Number.isFinite(t)) continue;
      const x = left + ((t - start) / Math.max(0.001, end - start)) * plotW;
      const y = y0 - Number(row[i] || 0) * scale;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();
  }
  if (reader.overlayVisibility.stageCode && (state.epilepsyInline.epochRows || []).length) {
    const epochRows = state.epilepsyInline.epochRows || [];
    const bandY = top + 2;
    const bandH = 10;
    epochRows.forEach((row, index) => {
      const code = Number(row.Stage_Code ?? row.stage_code ?? row.prediction ?? 0);
      const rowStart = Number(row.start_sec ?? row.start ?? (index * 5));
      const rowEnd = Number(row.end_sec ?? row.end ?? (rowStart + Number(row.duration_sec || 5)));
      if (!Number.isFinite(rowStart) || !Number.isFinite(rowEnd) || rowEnd <= start || rowStart >= end) return;
      const x1 = left + ((Math.max(start, rowStart) - start) / Math.max(0.001, end - start)) * plotW;
      const x2 = left + ((Math.min(end, rowEnd) - start) / Math.max(0.001, end - start)) * plotW;
      ctx.fillStyle = code === 1 ? "rgba(220, 38, 38, .22)" : "rgba(148, 163, 184, .16)";
      ctx.fillRect(x1, bandY, Math.max(1, x2 - x1), bandH);
      if (code === 1) {
        ctx.strokeStyle = "rgba(185, 28, 28, .72)";
        ctx.strokeRect(x1, bandY, Math.max(1, x2 - x1), bandH);
      }
    });
    ctx.fillStyle = "#475569";
    ctx.font = "10px Segoe UI";
    ctx.fillText("候选标记", left + 4, bandY + bandH + 12);
  }
  const selectedEvent = inlineEpilepsySelectedEvent();
  if (reader.overlayVisibility.candidates && selectedEvent) {
    const x1 = left + ((selectedEvent.start - start) / Math.max(0.001, end - start)) * plotW;
    const x2 = left + ((selectedEvent.end - start) / Math.max(0.001, end - start)) * plotW;
    const x = Math.max(left, Math.min(left + plotW, x1));
    const w = Math.max(1, Math.min(left + plotW, x2) - x);
    ctx.fillStyle = "rgba(245, 158, 11, .14)";
    ctx.fillRect(x, top, w, plotH);
    ctx.strokeStyle = "rgba(180, 83, 9, .72)";
    ctx.strokeRect(x, top, w, plotH);
    ctx.fillStyle = "#92400e";
    ctx.font = "700 12px Segoe UI";
    ctx.fillText("候选事件", x + 6, top + 16);
    // onset 竖线（金色虚线穿透波形面板，与频谱图同步）
    if (x1 >= left && x1 <= left + plotW) {
      ctx.strokeStyle = "rgba(251, 191, 36, .70)";
      ctx.lineWidth = 1.5;
      ctx.setLineDash([5, 4]);
      ctx.beginPath(); ctx.moveTo(x1, top); ctx.lineTo(x1, top + plotH); ctx.stroke();
      ctx.setLineDash([]);
    }
  }
  ctx.fillStyle = "#64748b";
  ctx.font = "11px Segoe UI";
  ctx.fillText(`${payload.downsample || "display"} · ${Number(payload.display_sample_rate_hz || 0).toFixed(0)} Hz display · preview only`, left, 15);
}

function inlineSpectrogramColor(value) {
  const v = Math.max(0, Math.min(1, Number(value) || 0));
  const stops = [
    [0.00, [12, 35, 64]],
    [0.25, [37, 99, 143]],
    [0.50, [102, 171, 170]],
    [0.75, [244, 181, 94]],
    [1.00, [179, 58, 48]],
  ];
  for (let i = 1; i < stops.length; i += 1) {
    const [p1, c1] = stops[i];
    const [p0, c0] = stops[i - 1];
    if (v <= p1) {
      const k = (v - p0) / Math.max(0.0001, p1 - p0);
      const rgb = c0.map((part, index) => Math.round(part + (c1[index] - part) * k));
      return `rgb(${rgb[0]}, ${rgb[1]}, ${rgb[2]})`;
    }
  }
  return "rgb(179, 58, 48)";
}

function inlineComputeSpectrogramPreview(payload) {
  const rows = payload?.data_uv || [];
  if (!rows.length) return null;
  const sfreq = Math.max(1, Number(payload.display_sample_rate_hz || 200));
  const source = rows[0] || [];
  const values = source.map(Number).filter(Number.isFinite);
  if (values.length < 64) return null;
  const windowSize = Math.max(64, Math.min(256, Math.floor(sfreq * 1.0)));
  const hop = Math.max(16, Math.floor(windowSize / 4));
  const bins = [0.5, 2, 4, 8, 12, 20, 30, 50].filter((freq) => freq < sfreq / 2);
  const times = [];
  const matrix = bins.map(() => []);
  for (let start = 0; start + windowSize <= values.length; start += hop) {
    const center = Number(payload.start_sec || 0) + (start + windowSize / 2) / sfreq;
    times.push(center);
    for (let b = 0; b < bins.length; b += 1) {
      const freq = bins[b];
      let re = 0;
      let im = 0;
      for (let n = 0; n < windowSize; n += 1) {
        const hann = 0.5 - 0.5 * Math.cos((2 * Math.PI * n) / Math.max(1, windowSize - 1));
        const angle = (2 * Math.PI * freq * n) / sfreq;
        const sample = values[start + n] * hann;
        re += sample * Math.cos(angle);
        im -= sample * Math.sin(angle);
      }
      const power = 10 * Math.log10((re * re + im * im) / windowSize + 1e-9);
      matrix[b].push(power);
    }
  }
  const flat = matrix.flat().filter(Number.isFinite).sort((a, b) => a - b);
  if (!flat.length || !times.length) return null;
  const percentile = (p) => flat[Math.max(0, Math.min(flat.length - 1, Math.floor((flat.length - 1) * p)))];
  const vmin = percentile(0.10);
  const vmax = percentile(0.99);
  return { frequencies: bins, times, matrix, vmin, vmax, channel: payload.channels?.[0] || "Ch1" };
}

function drawInlineEpilepsySpectrogram() {
  const canvas = qs("[data-testid=\"inline-epilepsy-spectrogram-canvas\"]");
  const payload = state.epilepsyInline.waveformPayload;
  const spectrogramPayload = state.epilepsyInline.spectrogramPayload;
  if (!canvas?.getContext) return;
  const ctx = canvas.getContext("2d");
  const rect = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  const width = Math.max(720, Math.floor(rect.width || 900));
  const height = Math.max(220, Math.floor(rect.height || 260));
  canvas.width = Math.floor(width * dpr);
  canvas.height = Math.floor(height * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, width, height);
  const reader = inlineEpilepsyReaderState();
  const windowStart = Number(reader.startSec || payload?.start_sec || 0);
  const windowEnd = windowStart + Number(reader.durationSec || payload?.duration_sec || 30);
  const allTimes = (spectrogramPayload?.times_sec || []).map(Number);
  const allFreqs = (spectrogramPayload?.frequencies_hz || []).map(Number);
  const allPower = spectrogramPayload?.power_db || [];
  const selectedColumns = allTimes
    .map((time, index) => ({ time, index }))
    .filter((item) => Number.isFinite(item.time) && item.time >= windowStart && item.time <= windowEnd);
  const fallbackColumns = allTimes.map((time, index) => ({ time, index })).slice(0, 1);
  const columns = selectedColumns.length ? selectedColumns : fallbackColumns;
  const spec = spectrogramPayload && allFreqs.length && columns.length && allPower.length ? {
    frequencies: allFreqs,
    times: columns.map((item) => item.time),
    matrix: allPower.map((row) => columns.map((item) => Number(row?.[item.index]))),
    vmin: Number(spectrogramPayload.vmin),
    vmax: Number(spectrogramPayload.vmax),
    channel: spectrogramPayload.channel || payload?.channels?.[0] || "Ch1",
    source: spectrogramPayload.source_compatibility || "epilepsy_ml_spectrogram",
    parameters: spectrogramPayload.parameters || {},
  } : null;
  canvas.dataset.spectrogramStatus = spec ? "ready" : (state.epilepsyInline.spectrogramLoadStatus || "waiting");
  canvas.dataset.source = spec ? "epilepsy_ml_spectrogram_artifact_pc_stft" : "waiting_epilepsy_ml_spectrogram";
  if (!spec) {
    ctx.fillStyle = "#64748b";
    ctx.font = "13px Segoe UI";
    ctx.fillText("\u8fd0\u884c\u521d\u7b5b\u540e\u663e\u793a PC \u53c2\u6570\u540c\u6e90 STFT \u65f6\u9891\u56fe\u3002", 28, 42);
    ctx.fillText("\u7b49\u5f85\u4ea7\u7269\uff1adata/epilepsy_ml_spectrogram.json", 28, 64);
    return;
  }
  const left = 58;
  const right = 16;
  var top = 20;
  const bottom = 34;
  // Stage_Code band for epoch rows
  var scEpochRows = (state.epilepsyInline && state.epilepsyInline.epochRows) || [];
  var hasScBand = scEpochRows.length > 0;
  var scBandH = hasScBand ? 10 : 0;
  if (hasScBand) {
    var scEpochDur = Number(scEpochRows[0]?.duration_sec || scEpochRows[0]?.duration || 4);
    scEpochRows.forEach(function(scRow, scIdx) {
      var scCode = Number(scRow.Stage_Code ?? scRow.stage_code ?? scRow.prediction ?? 0);
      var scStart = scIdx * scEpochDur;
      var scEnd = (scIdx + 1) * scEpochDur;
      if (scEnd <= windowStart || scStart >= windowEnd) return;
      var scX1 = left + ((Math.max(windowStart, scStart) - windowStart) / Math.max(0.001, windowEnd - windowStart)) * (width - left - right);
      var scX2 = left + ((Math.min(windowEnd, scEnd) - windowStart) / Math.max(0.001, windowEnd - windowStart)) * (width - left - right);
      ctx.fillStyle = scCode === 1 ? "rgba(220, 38, 38, 0.45)" : "rgba(148, 163, 184, 0.18)";
      ctx.fillRect(scX1, top, Math.max(1, scX2 - scX1), scBandH);
    });
    ctx.strokeStyle = "rgba(148,163,184,0.25)";
    ctx.lineWidth = 0.5;
    ctx.strokeRect(left, top, width - left - right, scBandH);
    ctx.fillStyle = "#64748b";
    ctx.font = "9px Segoe UI";
    ctx.fillText("候选标记", left + 3, top + scBandH - 2);
    top = top + scBandH + 3;
  }
  const plotW = width - left - right;
  const plotH = height - top - bottom;
  const cols = spec.times.length;
  const rows = spec.frequencies.length;
  const cellW = plotW / Math.max(1, cols);
  const cellH = plotH / Math.max(1, rows);
  for (let r = 0; r < rows; r += 1) {
    const freqIndex = rows - 1 - r;
    for (let c = 0; c < cols; c += 1) {
      const value = spec.matrix[freqIndex]?.[c];
      const norm = (Number(value) - spec.vmin) / Math.max(0.0001, spec.vmax - spec.vmin);
      ctx.fillStyle = inlineSpectrogramColor(norm);
      ctx.fillRect(left + c * cellW, top + r * cellH, Math.ceil(cellW) + 0.5, Math.ceil(cellH) + 0.5);
    }
  }
  ctx.strokeStyle = "rgba(42,79,120,.18)";
  ctx.lineWidth = 1;
  ctx.strokeRect(left, top, plotW, plotH);
  ctx.fillStyle = "#475569";
  ctx.font = "11px Segoe UI";
  const labelFreqs = [50, 30, 20, 12, 8, 4, 0.5].filter((freq) => freq <= spec.frequencies.at(-1));
  labelFreqs.forEach((freq) => {
    const idx = spec.frequencies.reduce((best, current, index) => Math.abs(current - freq) < Math.abs(spec.frequencies[best] - freq) ? index : best, 0);
    const y = top + plotH - (idx / Math.max(1, rows - 1)) * plotH;
    ctx.fillText(String(freq) + "Hz", 8, y + 4);
    ctx.strokeStyle = "rgba(255,255,255,.28)";
    ctx.beginPath();
    ctx.moveTo(left, y);
    ctx.lineTo(left + plotW, y);
    ctx.stroke();
  });
  const start = windowStart;
  const end = windowEnd;
  for (let i = 0; i <= 4; i += 1) {
    const x = left + (plotW * i / 4);
    ctx.fillStyle = "#64748b";
    ctx.fillText((start + (end - start) * i / 4).toFixed(1) + "s", x - 10, height - 10);
  }
  const selectedEvent = inlineEpilepsySelectedEvent();
  if (selectedEvent) {
    const x1 = left + ((selectedEvent.start - start) / Math.max(0.001, end - start)) * plotW;
    const x2 = left + ((selectedEvent.end - start) / Math.max(0.001, end - start)) * plotW;
    const x = Math.max(left, Math.min(left + plotW, x1));
    const w = Math.max(1, Math.min(left + plotW, x2) - x);
    ctx.fillStyle = "rgba(255, 255, 255, .20)";
    ctx.fillRect(x, top, w, plotH);
    ctx.strokeStyle = "rgba(251, 191, 36, .92)";
    ctx.lineWidth = 2;
    ctx.strokeRect(x, top, w, plotH);
  }
  ctx.fillStyle = "#334155";
  ctx.font = "12px Segoe UI";
  const win = Number(spec.parameters?.window_sec || 4).toFixed(0);
  const overlap = Math.round(Number(spec.parameters?.overlap_ratio || 0.9) * 100);
  ctx.fillText("PC STFT artifact · " + spec.channel + " · " + win + "s window · " + overlap + "% overlap · 0.5-50Hz · 10/99 percentile", left, 14);
}

function renderInlineEpilepsyWorkbench() {
  // P0-UI-LOGIC-04 FIX: 在 inline 入口渲染工作台状态占位
  try {
    const statusContainer = qs('#epilepsyWorkbenchStatus');
    if (statusContainer) {
      const file = currentWorkspaceFile() || state.real.eegFile || {};
      const plan = state.real.plan || {};
      const hasFile = Boolean(file.id);
      const planReady = isAnalysisReady();
      if (!hasFile) {
        const context = qs('[data-testid="inline-epilepsy-context-header"]');
        if (context) {
          context.innerHTML = `
            <div class="inline-staging-title">
              <div>
                <p class="eyebrow">分析任务 / 癫痫样候选事件复核</p>
                <h2>癫痫样候选事件复核预览</h2>
                <p>用于候选事件初筛和人工复核。请先选择 EDF/EEG 数据，本页不提供诊断、确诊、治疗或临床分诊结论。</p>
              </div>
            </div>
          `;
        }
        statusContainer.hidden = false;
        statusContainer.classList.add("single-empty-action");
        statusContainer.innerHTML = `
          <div class="status-title">请先完成数据选择和准备确认</div>
          <div class="status-message">上传或选择已准备的 EEG 数据后，这里会显示波形、候选标记预览和人工复核工具。</div>
          <div class="status-actions">
            <button class="primary-btn" type="button" data-workbench-goto="storage"><span>上传或选择 EEG 数据</span></button>
          </div>`;
        statusContainer.querySelectorAll('[data-workbench-goto]').forEach(function(btn) {
          btn.addEventListener('click', function() {
            setView(btn.dataset.workbenchGoto);
          });
        });
        return; // 有状态占位时不渲染详细面板
      }
      statusContainer.hidden = true;
      statusContainer.classList.remove("single-empty-action");
    }
  } catch (e) { console.warn('epilepsyWorkbenchStatus render error:', e); }

  const file = currentWorkspaceFile() || state.real.eegFile || {};
  const plan = state.real.plan || {};
  const task = inlineEpilepsyTask();
  const artifacts = inlineEpilepsyArtifacts();
  const status = String(task?.status || "not_started").toLowerCase();
  const running = status === "running" || status === "queued" || String(task?.id || "").startsWith("pending_");
  const completed = status === "completed";
  const planReady = isAnalysisReady();
  const resultReady = completed && state.epilepsyInline.resultLoadStatus === "ready";
  const events = resultReady ? inlineEpilepsyCandidateEvents() : [];
  const selectedEvent = inlineEpilepsySelectedEvent(events);
  const selectedEventId = selectedEvent?.id || "";
  const { reader, durationTotal } = clampInlineEpilepsyReader(file);
  ensureInlineEpilepsyWaveform(file);
  const waveformStatus = state.epilepsyInline.waveformStatus || "idle";
  const waveformFetchStatus = state.epilepsyInline.waveformFetchStatus || waveformStatus;
  const waveformReady = inlineEpilepsyWaveformHasRenderablePayload();
  const wavePayload = state.epilepsyInline.waveformPayload;
  const displayedWindow = inlineEpilepsyDisplayedReaderWindow(file);
  const displayStartSec = displayedWindow.displayStartSec;
  const displayDurationSec = displayedWindow.displayDurationSec;
  const displayEndSec = Math.min(durationTotal, displayStartSec + displayDurationSec);
  const waveWindowText = waveformReady
    ? `${displayStartSec.toFixed(1)}-${displayEndSec.toFixed(1)}s`
    : "等待波形";
  const syncScale = String(state.epilepsyInline.timeScaleSec || 30);
  if (selectedEventId && !state.epilepsyInline.selectedEventId) state.epilepsyInline.selectedEventId = selectedEventId;
  const correction = selectedEventId ? inlineEpilepsyLatestCorrection(selectedEventId) : null;
  const draftCount = state.epilepsyInline.draftCommands.length;
  const canCorrect = resultReady && Boolean(selectedEvent);
  const savingReview = state.epilepsyInline.reviewSaveStatus === "saving";
  const exportingReview = state.epilepsyInline.exportStatus === "exporting";
  const canSave = draftCount > 0 && !state.epilepsyInline.draftSaved && !savingReview;
  const canPublish = state.epilepsyInline.draftSaved && Boolean(state.epilepsyInline.reviewSession?.id) && !exportingReview && state.epilepsyInline.exportStatus !== "exported";
  const correctionDisabledReason = resultReady ? "请选择一个候选事件后再进行人工复核标注。" : "请先完成癫痫样候选事件初筛并载入候选事件。";
  const saveDisabledReason = savingReview ? "正在保存复核草稿。" : draftCount ? "当前草稿已保存或正在等待后端返回。" : "请先选择候选事件并添加人工复核标注草稿。";
  const publishDisabledReason = state.epilepsyInline.exportStatus === "exported" ? "复核结果已发布到结果页。" : "请先保存复核记录，再发布到结果页。";
  const reviewSessionLabel = state.epilepsyInline.reviewSession?.id || "尚未保存";
  const exportLabel = state.epilepsyInline.exportStatus === "exported" ? "已生成复核结果" : state.epilepsyInline.exportStatus === "exporting" ? "正在生成复核结果" : "等待保存草稿";
  const counts = inlineEpilepsySummaryCounts(events);
  const teachingInline = Boolean(state.teaching.active && (isTeachingDemoProject(state.real.project) || isTeachingDemoFile(file)));
  const deepLinkPreparing = state.deepLink.epilepsyBootstrapStatus === "running" || state.deepLink.epilepsyBootstrapInFlight;
  const deepLinkFailed = state.deepLink.epilepsyBootstrapStatus === "failed";
  const teachingBoundaryText = "\u6559\u5b66\u6a21\u5f0f\uff1a\u6b63\u5728\u4f7f\u7528\u5185\u7f6e\u5408\u6210\u766b\u75eb\u6837 EEG \u6570\u636e\uff0c\u53ef\u5b8c\u6574\u8bd5\u8dd1\u521d\u7b5b\u3001\u4eba\u5de5\u590d\u6838\u6807\u6ce8\u548c\u590d\u6838\u7ed3\u679c\u751f\u6210\uff1b\u4e0d\u4e0a\u4f20\u3001\u4e0d\u5220\u9664\u3001\u4e0d\u8986\u76d6\u4f60\u7684\u6b63\u5f0f\u6570\u636e\uff0c\u4e0d\u4f5c\u4e3a\u8bca\u65ad\u6216\u79d1\u5b66\u7ed3\u8bba\u3002";
  const context = qs('[data-testid="inline-epilepsy-context-header"]');
  if (context) {
    context.innerHTML = `
      <div class="inline-staging-title">
        <div>
          <p class="eyebrow">分析任务 / 主系统子页面</p>
          <h2>癫痫样候选事件复核预览</h2>
          <p>继承已确认的数据准备方案，进入后先查看波形；再运行候选事件初筛，结合候选标记预览、事件表、时频证据与人工复核标注形成复核草稿。科研支持用途，不用于诊断、确诊、治疗或临床分诊。</p>
        </div>
        <div class="real-actions compact-actions">
          <button class="ghost-btn" type="button" data-view-jump="workflow"><span>分析任务</span></button>
          <button class="ghost-btn" type="button" data-view-jump="statistics"><span>查看结果</span></button>
        </div>
      </div>
      <div class="inline-staging-context-grid">
        <span><b>数据</b>${escapeHtml(file.original_filename || file.filename || file.id || "未选择")}</span>
        <span><b>准备方案</b>${escapeHtml(plan.id ? `${plan.id} / r${plan.revision || "-"}` : "未确认")}</span>
        <span><b>分析状态</b>${escapeHtml(completed ? "已完成初筛" : running ? "正在运行" : "等待开始")}</span>
        <span><b>准备记录</b>${escapeHtml(dataPreparationContractVersion(plan))}</span>
      </div>
      ${teachingInline ? `<div class="segment-summary teaching-protected-note" data-testid="inline-epilepsy-teaching-boundary">${escapeHtml(teachingBoundaryText)}</div>` : ""}
      ${deepLinkPreparing ? `<div class="segment-summary teaching-protected-note" data-testid="inline-epilepsy-deeplink-status">正在准备癫痫示例 EDF 数据...</div>` : ""}
      ${deepLinkFailed ? `<div class="segment-summary danger-text" data-testid="inline-epilepsy-deeplink-status">示例 EDF 自动载入未完成：${escapeHtml(state.deepLink.epilepsyBootstrapError || "请重新载入示例数据")} <button class="ghost-btn mini" type="button" data-epilepsy-action="retry-deeplink-bootstrap" data-testid="inline-epilepsy-retry-bootstrap">重新载入示例 EDF</button></div>` : ""}
    `;
  }
  const startPanel = qs('[data-testid="inline-epilepsy-screening-panel"]');
  if (startPanel) {
    const gateReason = planReady ? "准备方案已确认，可以运行后端初筛。" : "尚未确认数据准备方案：可以先查看波形，但不能运行初筛。";
    const screeningStatus = state.epilepsyInline.screeningStatus || (running ? "running" : completed ? "completed" : "idle");
    const screeningProgress = Math.max(0, Math.min(100, Number(state.epilepsyInline.screeningProgress || (running ? 35 : completed ? 100 : 0))));
    const screeningMessage = state.epilepsyInline.screeningMessage || (running ? "\u7cfb\u7edf\u6b63\u5728\u8fdb\u884c\u766b\u75eb\u6837\u5019\u9009\u4e8b\u4ef6\u521d\u7b5b\u3002" : completed ? "\u766b\u75eb\u6837\u5019\u9009\u4e8b\u4ef6\u521d\u7b5b\u5b8c\u6210\uff0c\u53ef\u7ee7\u7eed\u4eba\u5de5\u590d\u6838\u6807\u6ce8\u3002" : "\u70b9\u51fb\u5f00\u59cb\u521d\u7b5b\u540e\uff0c\u7cfb\u7edf\u4f1a\u8bfb\u53d6\u5019\u9009\u4e8b\u4ef6\u548c\u5019\u9009\u6807\u8bb0\u9884\u89c8\u3002");
    startPanel.innerHTML = `
      <div class="inline-staging-callout inline-workbench-toolbar">
        <div>
          <p class="eyebrow">操作台工具栏</p>
          <h2>${completed ? "算法结果已载入，继续人工复核标注" : "先阅片，再按需初筛"}</h2>
          <p data-testid="inline-epilepsy-gate-reason">${escapeHtml(gateReason)} 波形、候选标记、时频证据与候选事件保持同一时间尺度。</p>
        </div>
        <div class="real-actions compact-actions">
          <button class="primary-btn" type="button" data-testid="inline-epilepsy-start-screening" data-real-action="run-epilepsy-ml" title="${escapeHtml(gateReason)}" ${(!planReady || running) ? "disabled" : ""}><span>${running ? "运行中" : completed ? "重新初筛" : "开始初筛"}</span></button>
          <button class="ghost-btn" type="button" data-view-jump="analysis"><span>确认数据准备</span></button>
        </div>
      </div>
      <div class="inline-screening-progress" data-testid="inline-epilepsy-screening-progress" data-status="${escapeHtml(screeningStatus)}" aria-live="polite">
        <div class="inline-progress-head"><strong>${escapeHtml(screeningMessage)}</strong><span>${screeningProgress.toFixed(0)}%</span></div>
        <div class="inline-progress-track" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${screeningProgress.toFixed(0)}"><span style="width:${screeningProgress.toFixed(0)}%"></span></div>
      </div>
    `;
  }
  const summary = qs('[data-testid="inline-epilepsy-summary-panel"]');
  if (summary) {
    summary.innerHTML = `
      <div class="panel-head compact"><h2>结果概览</h2><span class="badge ${resultReady ? "" : "warn"}">${resultReady ? "真实结果已载入" : state.epilepsyInline.resultLoadStatus}</span></div>
      <div class="metric-grid compact-metrics">
        <article class="metric"><span>候选事件</span><strong>${counts.eventCount}</strong><small>来自本次结果文件</small></article>
        <article class="metric"><span>Epoch</span><strong>${counts.epochCount}</strong><small>来自模型分段结果</small></article>
        <article class="metric"><span>候选命中</span><strong>${counts.seizureEpochs}</strong><small>候选标记预览</small></article>
        <article class="metric"><span>人工复核标注</span><strong>${draftCount}</strong><small>${state.epilepsyInline.draftSaved ? "已保存复核记录" : "本地草稿"}</small></article>
      </div>
      <div class="segment-summary">源结果来自本次初筛任务；人工复核标注只写复核版本，不覆盖原始算法输出。</div>
      ${state.epilepsyInline.resultLoadError ? `<p class="small-muted danger-text" data-testid="inline-epilepsy-result-load-error">结果读取错误：${escapeHtml(state.epilepsyInline.resultLoadError)}</p>` : ""}
    `;
  }
  const epoch = qs('[data-testid="inline-epilepsy-epoch-panel"]');
  if (epoch) {
    const cells = resultReady
      ? (state.epilepsyInline.epochRows || []).map((row, index) => {
          const code = Number(row.Stage_Code ?? row.stage_code ?? 0);
          const epochIndex = row.epoch_index ?? index;
          const epochDurationSec = Number(row.duration_sec || row.duration || 4);
          const mappedEvent = inlineEpilepsyEventForEpoch(epochIndex, events);
          const active = mappedEvent?.id && mappedEvent.id === selectedEventId ? " selected" : "";
          const inWindow = (epochIndex * epochDurationSec < displayEndSec && (epochIndex + 1) * epochDurationSec > displayStartSec) ? " in-window" : "";
          return `<button type="button" class="${code === 1 ? "candidate" : ""}${active}${inWindow}" data-epilepsy-action="select-epoch" data-epoch-index="${escapeHtml(epochIndex)}" data-event-id="${escapeHtml(mappedEvent?.id || "")}" title="${mappedEvent ? "选择对应候选事件" : "该 epoch 暂无候选事件"}">${escapeHtml(String(code))}</button>`;
        }).join("")
      : `<em>运行初筛后显示每个 epoch 的候选标记预览。</em>`;
    var epochDur = Number((state.epilepsyInline.epochRows[0] && state.epilepsyInline.epochRows[0].duration_sec) || (state.epilepsyInline.epochRows[0] && state.epilepsyInline.epochRows[0].duration) || 4);
    var totalEpochs = (state.epilepsyInline.epochRows || []).length;
    var totalDur = totalEpochs * epochDur;
    var timeLabels = "";
    // 时间刻度：0s, 60s, 120s(2min), 180s(3min)... 精确覆盖所有 epoch
    for (var ts = 0; ts <= totalDur; ts += 60) {
      var labelText = ts >= 120 ? (ts / 60).toFixed(0) + "min" : ts + "s";
      var labelPos = totalDur > 0 ? (ts / totalDur) * 100 : 0;
      timeLabels += '<span style="position:absolute;left:' + labelPos.toFixed(1) + '%;top:0;font-size:10px;color:#64748b;transform:translateX(-50%);white-space:nowrap">' + labelText + '</span>';
    }
    // 发作起点：扫描 epoch 按钮 DOM 中第一个显示 "1" 的位置
    var onsetMarkerHtml = "";
    if (resultReady && cells.indexOf('>1<') > 0) {
      var onsetSec = 0;
      for (var fi = 0; fi < totalEpochs; fi++) {
        var scRow = state.epilepsyInline.epochRows[fi];
        var sc = Number((scRow && (scRow.Stage_Code !== undefined ? scRow.Stage_Code : scRow.stage_code)) || 0);
        if (sc === 1) { onsetSec = fi * epochDur; break; }
      }
      if (onsetSec === 0) {
        // fallback: direct DOM scan
        var btns = document.querySelectorAll(".inline-epoch-strip button");
        for (var bi = 0; bi < btns.length; bi++) {
          if (btns[bi].textContent.trim() === "1") { onsetSec = bi * epochDur; break; }
        }
      }
      if (onsetSec > 0) {
        var onsetPct = totalDur > 0 ? (onsetSec / totalDur) * 100 : 0;
        onsetMarkerHtml = '<div class="epoch-onset-marker" data-testid="inline-epilepsy-onset-marker" style="left:' + onsetPct.toFixed(1) + '%" title="\u53d1\u4f5c\u8d77\u70b9 ~' + onsetSec.toFixed(0) + 's"></div>';
      }
    }
    // 窗口高亮条
    var winLeftPct = totalDur > 0 ? (displayStartSec / totalDur) * 100 : 0;
    var winWidthPct = totalDur > 0 ? (Math.min(displayDurationSec, totalDur - displayStartSec) / totalDur) * 100 : 0;
    epoch.innerHTML = `
      <div class="panel-head compact"><h2>候选标记时间轴</h2><span class="badge">${resultReady ? "结果已载入" : "等待结果"}</span></div>
      <div class="epoch-strip-outer" data-testid="inline-epilepsy-epoch-outer">
        ${resultReady ? '<div class="epoch-time-scale" data-testid="inline-epilepsy-time-scale">' + timeLabels + '</div>' : ""}
        <div class="inline-epoch-strip" data-testid="inline-epilepsy-stage-strip" data-source-task="${escapeHtml(task?.id || "")}" data-sync-scale="${escapeHtml(syncScale)}" data-selected-event="${escapeHtml(selectedEventId)}">${cells}</div>
        ${resultReady ? '<div class="epoch-window-overlay" data-testid="inline-epilepsy-window-overlay" style="left:' + winLeftPct.toFixed(1) + '%;width:' + Math.max(1, winWidthPct).toFixed(1) + '%" title="' + displayStartSec.toFixed(1) + '-' + displayEndSec.toFixed(1) + 's"></div>' : ""}
        ${resultReady ? onsetMarkerHtml : ""}
      </div>
    `;
  }
  const eventsPanel = qs('[data-testid="inline-epilepsy-events-panel"]');
  if (eventsPanel) {
    var eventStatusMap = {};
    (state.epilepsyInline.draftCommands || []).slice().reverse().forEach(function(cmd) {
      if (cmd.eventId && !eventStatusMap[cmd.eventId]) {
        var lbl = String(cmd.label || "").toLowerCase();
        if (/seizure|保留|keep/.test(lbl)) eventStatusMap[cmd.eventId] = "confirmed";
        else if (/artifact|排除|reject|normal/.test(lbl)) eventStatusMap[cmd.eventId] = "rejected";
        else if (/review|复核|needs/.test(lbl)) eventStatusMap[cmd.eventId] = "needs_review";
      }
    });
    var statusCounts = { confirmed: 0, rejected: 0, needs_review: 0, unreviewed: 0 };
    var dotColors = { confirmed: "#16a34a", rejected: "#dc2626", needs_review: "#f59e0b", unreviewed: "#94a3b8" };
    var dotTitles = { confirmed: "保留候选", rejected: "排除/伪迹", needs_review: "需复核", unreviewed: "待矫正" };
    const rows = events.map((event) => {
      const active = event.id === selectedEventId ? "selected" : "";
      const eventTimeText = `${event.start.toFixed(1)}-${event.end.toFixed(1)}s`;
      const eventEpochText = `epoch ${event.startEpoch}-${event.endEpoch}`;
      const ariaLabel = `${event.label}, ${eventTimeText}, ${eventEpochText}`;
      var st = eventStatusMap[event.id] || "unreviewed";
      statusCounts[st] = (statusCounts[st] || 0) + 1;
      return `<button type="button" class="inline-event-row ${active}" data-epilepsy-action="select-event" data-event-id="${escapeHtml(event.id)}" aria-label="${escapeHtml(ariaLabel)}"><span class="event-status-dot" style="background:${dotColors[st]}" title="${dotTitles[st]}"></span><span><strong>${escapeHtml(event.label)}</strong><small> - ${escapeHtml(eventTimeText)} / ${escapeHtml(eventEpochText)}</small></span></button>`;
    }).join("");
    var summaryBadge = "已判 " + (statusCounts.confirmed + statusCounts.rejected) + "/" + events.length;
    eventsPanel.innerHTML = `
      <div class="panel-head compact"><h2>候选事件与人工复核标注</h2><span class="badge warn">${events.length} 个候选 ･ ${summaryBadge}</span></div>
      <div class="segment-summary">选择候选事件后，可在人工复核区标记为“保留候选 / 排除候选 / 需复核”；<span class="status-legend"><i style="color:#16a34a">●</i>保留 <i style="color:#dc2626">●</i>排除 <i style="color:#f59e0b">●</i>复核 <i style="color:#94a3b8">●</i>待判</span></div>
      <div class="inline-event-list">${rows || `<div class="empty-object-state"><strong>暂无候选事件</strong><span>请先运行初筛，或检查本次结果文件。</span></div>`}</div>
    `;
  }
  const waveform = qs('[data-testid="inline-epilepsy-waveform-panel"]');
  if (waveform) {
    const canPrevPage = reader.startSec > 0.001;
    const canNextPage = reader.startSec + reader.durationSec < durationTotal - 0.001;
    const canGainDown = reader.sensitivityUvPerRow > EDF_BROWSER_INTERACTION_CONSTANTS.minSensitivityUvPerRow + 0.001;
    const canGainUp = reader.sensitivityUvPerRow < EDF_BROWSER_INTERACTION_CONSTANTS.maxSensitivityUvPerRow - 0.001;
    const overviewEvents = events.map((event) => {
      const left = Math.max(0, Math.min(100, (Number(event.start || 0) / Math.max(1, durationTotal)) * 100));
      const width = Math.max(0.4, Math.min(100 - left, ((Number(event.end || event.start || 0) - Number(event.start || 0)) / Math.max(1, durationTotal)) * 100));
      const active = event.id === selectedEventId ? " active" : "";
      return `<span class="inline-overview-event${active}" style="left:${left.toFixed(3)}%;width:${width.toFixed(3)}%" data-event-id="${escapeHtml(event.id)}"></span>`;
    }).join("");
    const overviewReviews = (state.epilepsyInline.draftCommands || []).map((command) => {
      const event = events.find((item) => item.id === command.eventId);
      if (!event) return "";
      const left = Math.max(0, Math.min(100, (Number(event.start || 0) / Math.max(1, durationTotal)) * 100));
      return `<span class="inline-overview-review" style="left:${left.toFixed(3)}%" title="${escapeHtml(`${command.eventId}: ${command.label}`)}"></span>`;
    }).join("");
    const overviewLeft = Math.max(0, Math.min(100, (displayStartSec / Math.max(1, durationTotal)) * 100));
    const overviewWidth = Math.max(1, Math.min(100 - overviewLeft, ((displayEndSec - displayStartSec) / Math.max(1, durationTotal)) * 100));
    waveform.innerHTML = `
      <div class="panel-head compact"><div><h2>原始波形阅片窗</h2><p>进入操作台先看波形；算法初筛结果只作为同步叠加层。</p></div><span class="badge ${waveformReady ? "" : "warn"}">${escapeHtml(waveWindowText)}</span></div>
      <div class="inline-wave-toolbar">
        <span class="inline-mode-pill ${waveformReady ? "ready" : "blocked"}" data-testid="inline-epilepsy-waveform-status">${waveformReady ? `已加载波形 · ${(wavePayload.channels || []).slice(0, 8).length} 通道` : "等待波形窗口"}</span>
        <span class="inline-mode-pill">${escapeHtml(syncScale)}s 同步尺度</span>
        <span class="inline-mode-pill ${resultReady ? "ready" : "blocked"}">${resultReady ? "候选标记已载入" : "尚未运行初筛"}</span>
      </div>
      <div class="inline-reader-toolbar" data-testid="inline-epilepsy-reader-toolbar">
        <div class="inline-reader-group" aria-label="waveform browse controls">
          <button type="button" data-epilepsy-action="reader-prev-page" data-testid="inline-epilepsy-prev-page" ${canPrevPage ? "" : "disabled"}>上一页</button>
          <button type="button" data-epilepsy-action="reader-next-page" data-testid="inline-epilepsy-next-page" ${canNextPage ? "" : "disabled"}>下一页</button>
          <button type="button" data-epilepsy-action="reader-center-event" data-testid="inline-epilepsy-center-candidate" ${selectedEvent ? "" : "disabled"}>居中候选</button>
        </div>
        <div class="inline-reader-group" aria-label="candidate navigation">
          <button type="button" data-epilepsy-action="reader-prev-candidate" data-testid="inline-epilepsy-prev-candidate" ${events.length ? "" : "disabled"}>上一个候选</button>
          <button type="button" data-epilepsy-action="reader-next-candidate" data-testid="inline-epilepsy-next-candidate" ${events.length ? "" : "disabled"}>下一个候选</button>
        </div>
        <div class="inline-reader-group" aria-label="display controls">
          <button type="button" data-epilepsy-action="set-time-scale" data-scale-sec="5" class="${syncScale === "5" ? "active" : ""}" aria-pressed="${syncScale === "5" ? "true" : "false"}">5s</button>
          <button type="button" data-epilepsy-action="set-time-scale" data-scale-sec="30" class="${syncScale === "30" ? "active" : ""}" aria-pressed="${syncScale === "30" ? "true" : "false"}">30s</button>
          <button type="button" data-epilepsy-action="set-time-scale" data-scale-sec="300" class="${Number(syncScale) > 30 ? "active" : ""}" aria-pressed="${Number(syncScale) > 30 ? "true" : "false"}">300s</button>
          <button type="button" data-epilepsy-action="reader-gain-down" data-testid="inline-epilepsy-gain-down" ${canGainDown ? "" : "disabled"}>- uV/row</button>
          <span data-testid="inline-epilepsy-uv-row">${Number(reader.sensitivityUvPerRow).toFixed(0)} uV/row</span>
          <button type="button" data-epilepsy-action="reader-gain-up" data-testid="inline-epilepsy-gain-up" ${canGainUp ? "" : "disabled"}>+ uV/row</button>
        </div>
        <div class="inline-reader-group inline-reader-toggles" aria-label="overlay controls">
          <button type="button" data-epilepsy-action="reader-toggle-overlay" data-overlay="candidates" aria-pressed="${reader.overlayVisibility.candidates ? "true" : "false"}" data-testid="inline-epilepsy-toggle-candidates">候选</button>
          <button type="button" data-epilepsy-action="reader-toggle-overlay" data-overlay="stageCode" aria-pressed="${reader.overlayVisibility.stageCode ? "true" : "false"}" data-testid="inline-epilepsy-toggle-stage">候选标记</button>
          <button type="button" data-epilepsy-action="reader-toggle-overlay" data-overlay="reviewEdits" aria-pressed="${reader.overlayVisibility.reviewEdits ? "true" : "false"}" data-testid="inline-epilepsy-toggle-review">人工复核标注</button>
        </div>
      </div>
      <div class="inline-wave-canvas ${waveformReady ? "ready" : "blocked"}" data-source-task="${escapeHtml(task?.id || "")}" data-sync-scale="${escapeHtml(syncScale)}" data-selected-event="${escapeHtml(selectedEventId)}" data-waveform-status="${escapeHtml(waveformStatus)}" data-waveform-fetch-status="${escapeHtml(waveformFetchStatus)}" data-displayed-start-sec="${displayStartSec.toFixed(3)}" data-displayed-duration-sec="${displayDurationSec.toFixed(3)}">
        <canvas data-testid="inline-epilepsy-waveform-canvas" data-sync-scale="${escapeHtml(syncScale)}" data-selected-event="${escapeHtml(selectedEventId)}" data-waveform-status="${escapeHtml(waveformStatus)}" data-waveform-fetch-status="${escapeHtml(waveformFetchStatus)}" aria-label="癫痫样候选事件复核预览原始 EEG 波形"></canvas>
      </div>
    `;
    const inlineCanvas = waveform.querySelector('[data-testid="inline-epilepsy-waveform-canvas"]');
    if (inlineCanvas) {
      inlineCanvas.tabIndex = 0;
      inlineCanvas.dataset.readerStartSec = reader.startSec.toFixed(3);
      inlineCanvas.dataset.readerDurationSec = reader.durationSec.toFixed(3);
    }
    waveform.insertAdjacentHTML("beforeend", `
      <div class="inline-overview-strip" data-testid="inline-epilepsy-overview-strip" data-duration-sec="${durationTotal.toFixed(3)}" data-start-sec="${displayStartSec.toFixed(3)}" data-window-sec="${displayDurationSec.toFixed(3)}" role="slider" aria-label="全程概览与当前阅片窗口" aria-valuemin="0" aria-valuemax="${durationTotal.toFixed(1)}" aria-valuenow="${displayStartSec.toFixed(1)}">
        ${reader.overlayVisibility.candidates ? overviewEvents : ""}
        ${reader.overlayVisibility.reviewEdits ? overviewReviews : ""}
        <span class="inline-overview-current-window" style="left:${overviewLeft.toFixed(3)}%;width:${overviewWidth.toFixed(3)}%"></span>
      </div>
      <p class="small-muted inline-reader-help">滚轮水平阅片，Ctrl/Cmd+滚轮缩放时间窗，方向键小步移动，PageUp/PageDown 翻页，+/- 调整 uV/row；浏览不会写入人工复核标注草稿。</p>
    `);
  }
  const spectrogram = qs('[data-testid="inline-epilepsy-spectrogram-panel"]');
  if (spectrogram) {
    spectrogram.innerHTML = `
      <div class="panel-head compact"><div><h2>时频证据层</h2><p>基于当前同一波形窗口即时计算 STFT 预览，与波形同轴联动；它不是正式 TFR、PSD 或 Band Power 分析结果。</p></div><div class="inline-scale-control-group" data-testid="inline-epilepsy-sync-scale-readout"><span>跟随阅片窗</span><strong>${escapeHtml(syncScale)}s</strong></div></div>
      <div class="inline-spectrogram-shell" data-sync-scale="${escapeHtml(syncScale)}" data-selected-event="${escapeHtml(selectedEventId)}" data-source-task="${escapeHtml(task?.id || "")}">
        <canvas data-testid="inline-epilepsy-spectrogram-canvas" data-sync-scale="${escapeHtml(syncScale)}" data-selected-event="${escapeHtml(selectedEventId)}" data-source-task="${escapeHtml(task?.id || "")}" data-spectrogram-status="${waveformReady ? "ready" : "waiting"}" aria-label="癫痫样候选事件复核预览 STFT 预览"></canvas>
        <div class="inline-spectrogram-event"><span>${waveformReady ? escapeHtml(waveWindowText) : "等待波形窗口"}</span><strong>${selectedEvent ? "候选事件同步高亮" : "运行后同步候选事件"}</strong></div>
      </div>
      <p class="small-muted" data-testid="inline-epilepsy-spectrogram-source-copy">当前图只由同一波形窗口的 waveform chunk 即时派生 STFT 预览，用于同步阅片参考；它不是正式 TFR、PSD 或 Band Power 分析结果，也不会写入结果产物。</p>
    `;
  }
  const source = qs('[data-testid="inline-epilepsy-source-panel"]');
  if (source) {
    source.innerHTML = `<div class="panel-head compact"><h2>源结果记录</h2></div><div class="empty-object-state"><strong>${resultReady ? "源结果只读保留" : "等待源结果"}</strong><span>候选标记预览、候选事件、阈值和结果文件来自本次任务；人工复核标注另存为草稿，不覆盖原始模型输出。</span></div>`;
  }
  const review = qs('[data-testid="inline-epilepsy-review-panel"]');
  if (review) {
    review.innerHTML = `
      <div class="panel-head compact"><h2>人工复核标注与草稿</h2></div>
      <label class="real-field"><span>当前任务</span><input value="${escapeHtml(task?.id || "未运行")}" readonly /></label>
      <label class="real-field"><span>复核会话</span><input value="${escapeHtml(reviewSessionLabel)}" readonly /></label>
      <div class="inline-review-status"><strong>${selectedEvent ? escapeHtml(selectedEvent.label) : "请选择候选事件"}</strong><span>${correction ? escapeHtml(correction.displayLabel || correction.label) : "人工复核标注只写入复核草稿：保留候选会保留该候选，排除候选会把对应 epoch 改为 0，需复核只写复核状态。"}</span></div>
      <div class="inline-correction-actions">
        <button class="ghost-btn danger-soft" type="button" data-epilepsy-action="set-correction" data-correction="keep_candidate" data-correction-label="保留候选" data-event-id="${escapeHtml(selectedEventId)}" title="${escapeHtml(canCorrect ? "把当前候选保留在复核版本中。" : correctionDisabledReason)}" data-disabled-reason="${escapeHtml(canCorrect ? "" : correctionDisabledReason)}" ${canCorrect ? "" : "disabled"}>保留候选</button>
        <button class="ghost-btn" type="button" data-epilepsy-action="set-correction" data-correction="exclude_candidate" data-correction-label="排除候选" data-event-id="${escapeHtml(selectedEventId)}" title="${escapeHtml(canCorrect ? "把当前候选排除，并把对应 epoch 写为 0。" : correctionDisabledReason)}" data-disabled-reason="${escapeHtml(canCorrect ? "" : correctionDisabledReason)}" ${canCorrect ? "" : "disabled"}>排除候选</button>
        <button class="ghost-btn" type="button" data-epilepsy-action="set-correction" data-correction="Artifact" data-correction-label="标为伪迹" data-event-id="${escapeHtml(selectedEventId)}" title="${escapeHtml(canCorrect ? "把当前候选标为伪迹，复核导出中保留审计原因。" : correctionDisabledReason)}" data-disabled-reason="${escapeHtml(canCorrect ? "" : correctionDisabledReason)}" ${canCorrect ? "" : "disabled"}>标为伪迹</button>
        <button class="ghost-btn" type="button" data-epilepsy-action="set-correction" data-correction="Needs review" data-correction-label="需复核" data-event-id="${escapeHtml(selectedEventId)}" title="${escapeHtml(canCorrect ? "把当前候选标记为需要后续复核。" : correctionDisabledReason)}" data-disabled-reason="${escapeHtml(canCorrect ? "" : correctionDisabledReason)}" ${canCorrect ? "" : "disabled"}>需复核</button>
      </div>
      <div class="inline-correction-actions">
        <button class="ghost-btn" type="button" data-epilepsy-action="adjust-interval" data-adjust-edge="start" data-adjust-delta-sec="-1" data-event-id="${escapeHtml(selectedEventId)}" title="${escapeHtml(canCorrect ? "把候选起点向前微调 1 秒。" : correctionDisabledReason)}" data-disabled-reason="${escapeHtml(canCorrect ? "" : correctionDisabledReason)}" ${canCorrect ? "" : "disabled"}>起点 -1s</button>
        <button class="ghost-btn" type="button" data-epilepsy-action="adjust-interval" data-adjust-edge="start" data-adjust-delta-sec="1" data-event-id="${escapeHtml(selectedEventId)}" title="${escapeHtml(canCorrect ? "把候选起点向后微调 1 秒。" : correctionDisabledReason)}" data-disabled-reason="${escapeHtml(canCorrect ? "" : correctionDisabledReason)}" ${canCorrect ? "" : "disabled"}>起点 +1s</button>
        <button class="ghost-btn" type="button" data-epilepsy-action="adjust-interval" data-adjust-edge="end" data-adjust-delta-sec="-1" data-event-id="${escapeHtml(selectedEventId)}" title="${escapeHtml(canCorrect ? "把候选终点向前微调 1 秒。" : correctionDisabledReason)}" data-disabled-reason="${escapeHtml(canCorrect ? "" : correctionDisabledReason)}" ${canCorrect ? "" : "disabled"}>终点 -1s</button>
        <button class="ghost-btn" type="button" data-epilepsy-action="adjust-interval" data-adjust-edge="end" data-adjust-delta-sec="1" data-event-id="${escapeHtml(selectedEventId)}" title="${escapeHtml(canCorrect ? "把候选终点向后微调 1 秒。" : correctionDisabledReason)}" data-disabled-reason="${escapeHtml(canCorrect ? "" : correctionDisabledReason)}" ${canCorrect ? "" : "disabled"}>终点 +1s</button>
      </div>
      <div class="real-actions compact-actions">
        <button class="ghost-btn" type="button" data-epilepsy-action="undo" title="${draftCount ? "撤销最近一条人工复核标注。" : "暂无可撤销的人工复核标注。"}" data-disabled-reason="${draftCount ? "" : "暂无可撤销的人工复核标注。"}" ${draftCount ? "" : "disabled"}>撤销</button>
        <button class="ghost-btn" type="button" data-epilepsy-action="redo" title="${state.epilepsyInline.redoCommands.length ? "重做最近撤销的人工复核标注。" : "暂无可重做的人工复核标注。"}" data-disabled-reason="${state.epilepsyInline.redoCommands.length ? "" : "暂无可重做的人工复核标注。"}" ${state.epilepsyInline.redoCommands.length ? "" : "disabled"}>重做</button>
        <button class="ghost-btn danger-soft" type="button" data-epilepsy-action="reset" title="${draftCount ? "清空当前本地复核草稿。" : "暂无可清空的人工复核标注草稿。"}" data-disabled-reason="${draftCount ? "" : "暂无可清空的人工复核标注草稿。"}" ${draftCount ? "" : "disabled"}>清空</button>
        <button class="ghost-btn" type="button" data-epilepsy-action="save-draft" title="${escapeHtml(canSave ? "保存人工复核标注草稿到复核记录。" : saveDisabledReason)}" data-disabled-reason="${escapeHtml(canSave ? "" : saveDisabledReason)}" ${canSave ? "" : "disabled"}>${savingReview ? "正在保存" : state.epilepsyInline.draftSaved ? "已保存复核记录" : "保存复核草稿"}</button>
        <button class="ghost-btn" type="button" data-epilepsy-action="publish-results" ${canPublish ? "" : "disabled"} title="${escapeHtml(canPublish ? "生成复核结果并进入结果页。" : publishDisabledReason)}" data-disabled-reason="${escapeHtml(canPublish ? "" : publishDisabledReason)}">${exportingReview ? "正在发布" : state.epilepsyInline.exportStatus === "exported" ? "已发布到结果页" : "发布到结果页"}</button>
        ${state.epilepsyInline.exportStatus === "exported" ? `<button class="ghost-btn" type="button" data-testid="inline-epilepsy-view-results" data-view-jump="statistics">查看复核结果</button>` : ""}
      </div>
      <div class="inline-draft-ledger" data-testid="inline-epilepsy-draft-ledger"><b>复核草稿 ${draftCount} 条${state.epilepsyInline.draftSaved ? " / 已保存" : " / 本地待保存"}</b><span>${state.epilepsyInline.draftCommands.map((item) => escapeHtml(`${item.eventId}: ${item.displayLabel || item.label}`)).join(" / ") || "暂无人工复核标注草稿。"}</span></div>
      <p class="small-muted">保存会写入复核记录；发布会生成复核结果文件，不覆盖原始模型输出。状态：${escapeHtml(exportLabel)}。</p>
      ${state.epilepsyInline.reviewSaveError ? `<p class="small-muted danger-text" data-testid="inline-epilepsy-review-save-error">保存错误：${escapeHtml(state.epilepsyInline.reviewSaveError)}</p>` : ""}
      ${state.epilepsyInline.exportError ? `<p class="small-muted danger-text" data-testid="inline-epilepsy-export-error">发布错误：${escapeHtml(state.epilepsyInline.exportError)}</p>` : ""}
      <p class="small-muted">科研支持用途，不用于诊断、确诊、治疗或临床分诊。</p>
    `;
  }
  window.__QLANALYSER_E2E_STATE__ = isE2EAutomationContext() ? state : undefined;
  window.requestAnimationFrame(() => {
    drawInlineEpilepsyWaveform();
    drawInlineEpilepsySpectrogram();
  });
}

async function openEpilepsyWorkbenchFromPlan() {
  setView("epilepsyWorkbenchInline");
  renderInlineEpilepsyWorkbench();
  if (state.teaching.active) {
    await ensureTeachingSandboxReady({ preview: false, moduleName: "epilepsy_ml" }).catch(() => null);
    renderInlineEpilepsyWorkbench();
  }
  return { id: "epilepsy_workbench_inline", plan_id: state.real.plan?.id || null, gated: !isAnalysisReady() };
}

async function seedWorkspaceForLocalE2E(seed = null) {
  if (!["localhost", "127.0.0.1"].includes(window.location.hostname)) return null;
  const payload = seed || await apiJson("/lab/demo/dataset");
  const project = payload.project || payload.demo_project || null;
  const file = payload.file || payload.eeg_file || null;
  const plan = payload.data_preparation_plan || payload.plan || null;
  if (project) {
    state.real.project = project;
    state.workspace.selectedProjectId = project.id || state.workspace.selectedProjectId;
    if (!state.workspace.projects.some((item) => item.id === project.id)) state.workspace.projects.unshift(project);
  }
  if (file) {
    state.real.eegFile = file;
    state.workspace.selectedFileId = file.id || state.workspace.selectedFileId;
    if (!state.workspace.files.some((item) => item.id === file.id)) state.workspace.files.unshift(file);
  }
  if (plan) {
    state.real.plan = { ...plan, schema_version: dataPreparationContractVersion(plan) };
    state.workspace.selectedPlanId = plan.id || state.workspace.selectedPlanId;
    if (!state.workspace.plans.some((item) => item.id === plan.id)) state.workspace.plans.unshift(state.real.plan);
  }
  await refreshProjectWorkspace().catch(() => null);
  updateRealActionGate();
  renderInlineEpilepsyWorkbench();
  window.__QLANALYSER_E2E_STATE__ = state;
  return {
    project_id: state.real.project?.id || null,
    file_id: state.real.eegFile?.id || null,
    plan_id: state.real.plan?.id || null,
    plan_revision: state.real.plan?.revision || null,
  };
}

if (["localhost", "127.0.0.1"].includes(window.location.hostname)) {
  window.__qlanalyserE2ESeedWorkspace = seedWorkspaceForLocalE2E;
  window.__QLANALYSER_E2E_STATE__ = state;
}
publishE2EState();

function inlineEpilepsyReaderEventTarget(target) {
  return target?.closest?.('[data-testid="inline-epilepsy-waveform-panel"], [data-testid="inline-epilepsy-waveform-canvas"], [data-testid="inline-epilepsy-overview-strip"]') || null;
}

function rerenderInlineEpilepsyReaderAfterInteraction() {
  const requestKey = inlineEpilepsyWaveformRequestKey(currentWorkspaceFile() || state.real.eegFile || {});
  const hasDisplayedTarget = Boolean(requestKey && state.epilepsyInline.waveformPayloadKey === requestKey && inlineEpilepsyWaveformHasRenderablePayload());
  const hasCachedTarget = Boolean(requestKey && inlineEpilepsyWaveformCache().get(requestKey)?.data_uv?.length);
  if (!hasDisplayedTarget && !hasCachedTarget && inlineEpilepsyWaveformHasRenderablePayload()) {
    ensureInlineEpilepsyWaveform(currentWorkspaceFile() || state.real.eegFile || {});
    return;
  }
  renderInlineEpilepsyWorkbench();
  window.requestAnimationFrame(() => {
    drawInlineEpilepsyWaveform();
    drawInlineEpilepsySpectrogram();
  });
}

function setInlineEpilepsyScreeningProgress(status = "idle", progress = 0, message = "") {
  state.epilepsyInline.screeningStatus = status;
  state.epilepsyInline.screeningProgress = Math.max(0, Math.min(100, Number(progress || 0)));
  state.epilepsyInline.screeningMessage = message;
  if (qs("#epilepsyWorkbenchInline")?.classList.contains("active")) {
    renderInlineEpilepsyWorkbench();
  }
}

async function handleInlineEpilepsyAction(action, button) {
  const file = currentWorkspaceFile() || state.real.eegFile || {};
  if (action === "select-event") {
    selectInlineEpilepsyEvent(button.dataset.eventId || "", { center: true, file });
  } else if (action === "select-epoch") {
    const mappedEvent = button.dataset.eventId || inlineEpilepsyEventForEpoch(button.dataset.epochIndex)?.id || "";
    if (mappedEvent) selectInlineEpilepsyEvent(mappedEvent, { center: true, file });
  } else if (action === "set-time-scale") {
    setInlineEpilepsyViewport({ file, durationSec: Number(button.dataset.scaleSec || 30), anchorRatio: 0.5 });
  } else if (action === "reader-prev-page") {
    panInlineEpilepsyViewport(-EDF_BROWSER_INTERACTION_CONSTANTS.pagePanRatio, file);
  } else if (action === "reader-next-page") {
    panInlineEpilepsyViewport(EDF_BROWSER_INTERACTION_CONSTANTS.pagePanRatio, file);
  } else if (action === "reader-center-event") {
    centerInlineEpilepsyEvent(inlineEpilepsySelectedEvent(), file);
  } else if (action === "reader-prev-candidate") {
    selectInlineEpilepsyRelativeCandidate(-1, { file });
  } else if (action === "reader-next-candidate") {
    selectInlineEpilepsyRelativeCandidate(1, { file });
  } else if (action === "reader-gain-down") {
    const reader = inlineEpilepsyReaderState();
    reader.sensitivityUvPerRow = Math.max(EDF_BROWSER_INTERACTION_CONSTANTS.minSensitivityUvPerRow, reader.sensitivityUvPerRow / EDF_BROWSER_INTERACTION_CONSTANTS.gainStepRatio);
  } else if (action === "reader-gain-up") {
    const reader = inlineEpilepsyReaderState();
    reader.sensitivityUvPerRow = Math.min(EDF_BROWSER_INTERACTION_CONSTANTS.maxSensitivityUvPerRow, reader.sensitivityUvPerRow * EDF_BROWSER_INTERACTION_CONSTANTS.gainStepRatio);
  } else if (action === "reader-toggle-overlay") {
    const reader = inlineEpilepsyReaderState();
    const overlay = button.dataset.overlay;
    if (overlay && Object.prototype.hasOwnProperty.call(reader.overlayVisibility, overlay)) {
      reader.overlayVisibility[overlay] = !reader.overlayVisibility[overlay];
    }
  } else if (action === "retry-deeplink-bootstrap") {
    await bootstrapEpilepsyDeepLinkWorkbench("manual_retry");
    return;
  } else if (action === "set-correction") {
    const eventId = button.dataset.eventId || state.epilepsyInline.selectedEventId;
    const label = button.dataset.correction || "";
    const displayLabel = button.dataset.correctionLabel || button.textContent?.trim() || label;
    if (eventId && label) {
      state.epilepsyInline.draftCommands.push({ eventId, label, displayLabel, at: new Date().toISOString() });
      state.epilepsyInline.redoCommands = [];
      state.epilepsyInline.draftSaved = false;
      state.epilepsyInline.published = false;
    }
  } else if (action === "adjust-interval") {
    const eventId = button.dataset.eventId || state.epilepsyInline.selectedEventId;
    const event = inlineEpilepsyCandidateEvents().find((item) => item.id === eventId);
    const edge = button.dataset.adjustEdge || "";
    const delta = Number(button.dataset.adjustDeltaSec || 0);
    if (event && edge && Number.isFinite(delta)) {
      const originalStart = Number(event.start || 0);
      const originalEnd = Number(event.end || originalStart);
      let adjustedStart = originalStart;
      let adjustedEnd = originalEnd;
      if (edge === "start") adjustedStart = Math.max(0, Math.min(originalEnd - 0.1, originalStart + delta));
      if (edge === "end") adjustedEnd = Math.max(adjustedStart + 0.1, originalEnd + delta);
      const sign = delta > 0 ? "+" : "";
      const displayLabel = `${edge === "start" ? "起点" : "终点"} ${sign}${delta}s`;
      state.epilepsyInline.draftCommands.push({
        eventId,
        label: "Needs review",
        displayLabel,
        actionType: "adjust_event_interval",
        adjustedStartSec: Number(adjustedStart.toFixed(3)),
        adjustedEndSec: Number(adjustedEnd.toFixed(3)),
        at: new Date().toISOString(),
      });
      state.epilepsyInline.redoCommands = [];
      state.epilepsyInline.draftSaved = false;
      state.epilepsyInline.published = false;
    }
  } else if (action === "undo") {
    const item = state.epilepsyInline.draftCommands.pop();
    if (item) state.epilepsyInline.redoCommands.push(item);
    state.epilepsyInline.draftSaved = false;
    state.epilepsyInline.published = false;
  } else if (action === "redo") {
    const item = state.epilepsyInline.redoCommands.pop();
    if (item) state.epilepsyInline.draftCommands.push(item);
    state.epilepsyInline.draftSaved = false;
    state.epilepsyInline.published = false;
  } else if (action === "reset") {
    state.epilepsyInline.redoCommands = state.epilepsyInline.draftCommands.splice(0).reverse();
    state.epilepsyInline.draftSaved = false;
    state.epilepsyInline.published = false;
  } else if (action === "save-draft") {
    await saveInlineEpilepsyReviewDraft();
    return;
  } else if (action === "publish-results") {
    await exportInlineEpilepsyReviewResults();
    return;
  }
  renderInlineEpilepsyWorkbench();
}

async function fetchTaskArtifacts(taskId) {
  if (!taskId) return [];
  try {
    return await apiJson(`/tasks/${encodeURIComponent(taskId)}/artifacts`);
  } catch (error) {
    return [];
  }
}

function showGlobalLoading(message = "处理中...") {
  let overlay = qs("#globalLoadingOverlay");
  if (!overlay) {
    overlay = document.createElement("div");
    overlay.id = "globalLoadingOverlay";
    overlay.className = "global-loading-overlay";
    overlay.setAttribute("role", "status");
    overlay.setAttribute("aria-live", "polite");
    overlay.innerHTML = `
      <div class="global-loading-card">
        <div class="global-loading-spinner" aria-hidden="true"></div>
        <span class="global-loading-message"></span>
      </div>
    `;
    document.body.appendChild(overlay);
  }
  const text = overlay.querySelector(".global-loading-message");
  if (text) text.textContent = cleanRuntimeMessage(message);
  overlay.hidden = false;
  overlay.classList.add("show");
}

function hideGlobalLoading() {
  const overlay = qs("#globalLoadingOverlay");
  if (!overlay) return;
  overlay.classList.remove("show");
  window.setTimeout(() => {
    if (!overlay.classList.contains("show")) overlay.hidden = true;
  }, 180);
}

function friendlyRuntimeMessage(message) {
  const text = cleanRuntimeMessage(message || "");
  const lower = text.toLowerCase();
  if (lower.includes("failed to fetch") || lower.includes("network")) return "网络连接失败，请检查网络后重试。";
  if (lower.includes("413") || lower.includes("too large")) return "文件过大，请确认文件大小符合上传限制。";
  if (lower.includes("401") || lower.includes("unauthorized")) return "登录状态已过期，请重新登录。";
  if (lower.includes("403") || lower.includes("permission")) return "当前账号没有权限执行此操作。";
  if (lower.includes("404") || lower.includes("not found")) return "未找到对应资源，请刷新页面后重试。";
  if (lower.includes("timeout")) return "操作超时，请稍后重试或缩小数据范围。";
  return text || "操作失败，请重试。";
}

function showToast(message, tone = "info") {
  const toast = qs("#toast");
  if (!toast) return;
  toast.textContent = friendlyRuntimeMessage(message);
  toast.dataset.tone = tone;
  toast.classList.add("show");
  window.setTimeout(() => toast.classList.remove("show"), tone === "error" ? 4200 : 2400);
}

function openModal(kind) {
  const config = modalContent[kind];
  const backdrop = qs("#modalBackdrop");
  if (!config || !backdrop) return;
  qs("#modalTitle").textContent = config.title;
  qs("#modalBody").innerHTML = typeof config.body === "function" ? config.body() : config.body;
  backdrop.hidden = false;
  qsa("[data-modal-view]").forEach((button) => button.addEventListener("click", () => {
    closeModal();
    setView(button.dataset.modalView);
  }));
  if (window.lucide) lucide.createIcons();
}

function closeModal() {
  const backdrop = qs("#modalBackdrop");
  if (backdrop) backdrop.hidden = true;
}

function getStoredCustomer() {
  try {
    const stored = JSON.parse(localStorage.getItem(CUSTOMER_KEY)) || demoCustomer;
    // One-time migration: purge any plaintext password left from earlier versions.
    if (stored.password !== undefined) {
      delete stored.password;
      try { localStorage.setItem(CUSTOMER_KEY, JSON.stringify(stored)); } catch(e) {}
    }
    return stored;
  } catch {
    return demoCustomer;
  }
}

function saveCustomer(profile) {
  const cleaned = { ...profile };
  delete cleaned.password; // never persist password to localStorage
  localStorage.setItem(CUSTOMER_KEY, JSON.stringify({ ...getStoredCustomer(), ...cleaned }));
}

function validateEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function userFacingAuthMessage(message) {
  const text = String(message || "");
  const lower = text.toLowerCase();
  if (!text.trim()) return "";
  if (lower.includes("verification code") && (lower.includes("invalid") || lower.includes("expired"))) {
    return "\u9a8c\u8bc1\u7801\u65e0\u6548\u6216\u5df2\u8fc7\u671f\uff0c\u8bf7\u91cd\u65b0\u83b7\u53d6\u540e\u518d\u8bd5\u3002";
  }
  if (lower.includes("invalid credentials") || lower.includes("unauthorized")) {
    return "\u8d26\u53f7\u6216\u5bc6\u7801\u4e0d\u6b63\u786e\uff0c\u8bf7\u68c0\u67e5\u540e\u91cd\u8bd5\u3002";
  }
  if (lower.includes("already exists") || lower.includes("duplicate")) {
    return "\u8be5\u8d26\u53f7\u5df2\u5b58\u5728\uff0c\u8bf7\u76f4\u63a5\u767b\u5f55\u6216\u66f4\u6362\u6ce8\u518c\u4fe1\u606f\u3002";
  }
  if (/^[\x00-\x7F]+$/.test(text) && /[A-Za-z]/.test(text)) {
    return "\u64cd\u4f5c\u672a\u5b8c\u6210\uff0c\u8bf7\u68c0\u67e5\u4fe1\u606f\u540e\u91cd\u8bd5\u3002";
  }
  return text;
}

function setLoginFieldValidity(valid) {
  qsa("#customerEmail, #customerPassword").forEach((input) => {
    if (!input) return;
    if (valid) input.removeAttribute("aria-invalid");
    else input.setAttribute("aria-invalid", "true");
  });
}

function setLoginMessage(message, type = "info") {
  const target = qs("#loginMessage");
  if (!target) return;
  target.textContent = userFacingAuthMessage(message);
  target.classList.toggle("error", type === "error");
  target.classList.toggle("success", type === "success");
  target.toggleAttribute("hidden", !target.textContent.trim());
}

function setAuthenticatedShellVisible(isAuthenticated) {
  const loginScreen = qs("#loginScreen");
  const appShell = qs("#appShell");
  document.body.classList.toggle("login-active", !isAuthenticated);
  document.body.classList.toggle("workspace-active", Boolean(isAuthenticated));
  document.body.dataset.shellMode = isAuthenticated ? "workspace" : "login";
  if (loginScreen) {
    loginScreen.hidden = Boolean(isAuthenticated);
    loginScreen.inert = Boolean(isAuthenticated);
    loginScreen.setAttribute("aria-hidden", isAuthenticated ? "true" : "false");
  }
  if (appShell) {
    appShell.hidden = !isAuthenticated;
    appShell.inert = !isAuthenticated;
    appShell.setAttribute("aria-hidden", isAuthenticated ? "false" : "true");
  }
  publishE2EState();
}

function switchLoginTab(tab) {
  if (tab === "customerRegister") {
    setLoginFieldValidity(true);
    qsa("[data-login-tab]").forEach((button) => button.classList.toggle("active", button.dataset.loginTab === tab));
    qsa(".login-form").forEach((form) => form.classList.toggle("active", form.id === `${tab}Form`));
    setLoginMessage("试点阶段由运营人员开通账号。", "info");
    return;
  }
  qsa("[data-login-tab]").forEach((button) => button.classList.toggle("active", button.dataset.loginTab === tab));
  qsa(".login-form").forEach((form) => form.classList.toggle("active", form.id === `${tab}Form`));
  setLoginFieldValidity(true);
  setLoginMessage("");
}

function rememberSession(role, persist = true, extra = {}) {
  const session = JSON.stringify({ role, savedAt: new Date().toISOString(), ...extra });
  if (persist) localStorage.setItem(AUTH_KEY, session);
  else sessionStorage.setItem(AUTH_KEY, session);
}

function clearSession() {
  clearAuthenticatedArtifactObjectUrls();
  localStorage.removeItem(AUTH_KEY);
  sessionStorage.removeItem(AUTH_KEY);
}

function showLoginScreen(message = "", type = "info") {
  state.role = null;
  delete document.body.dataset.role;
  document.body.dataset.currentRole = "logged-out";
  setAuthenticatedShellVisible(false);
  if (window.location.hash) {
    history.replaceState(null, "", `${window.location.pathname}${window.location.search}`);
  }
  switchLoginTab("customerLogin");
  setLoginMessage(message || "", type);
  applyCleanVisibleCopy();
  if (window.lucide) lucide.createIcons();
}

function logout(showMessage = true) {
  clearSession();
  showLoginScreen(showMessage ? "\u5df2\u9000\u51fa\uff0c\u8bf7\u91cd\u65b0\u767b\u5f55\u3002" : "");
}

window.logout = logout;

function enhanceControlLabels() {
  qsa(".nav-item, .icon-btn").forEach((button) => {
    const label = button.getAttribute("aria-label") || button.getAttribute("title") || button.textContent.trim();
    if (!label) return;
    button.setAttribute("title", label);
    button.setAttribute("aria-label", label);
  });
}

function ensureRealEegFileInput() {
  if (qs("#real-eeg-file")) return qs("#real-eeg-file");
  const input = document.createElement("input");
  input.id = "real-eeg-file";
  input.className = "visually-hidden-file";
  input.type = "file";
  input.accept = ".edf,.bdf,.set,.vhdr,.cnt,.fif";
  input.setAttribute("aria-hidden", "true");
  document.body.appendChild(input);
  recordUiAction("upload:input-self-heal", "pass", "EEG 文件上传控件已自动恢复。");
  return input;
}

function applyRoleNavigationState(role = state.role || "customer") {
  document.body.dataset.role = role;
  qsa("[data-role]").forEach((item) => {
    const isVisibleRole = item.dataset.role === role;
    const hiddenBySecondary = role === "customer" && item.dataset.secondaryFlow === "true";
    item.hidden = !isVisibleRole || hiddenBySecondary;
    item.setAttribute("aria-hidden", item.hidden ? "true" : "false");
  });
}

async function refreshWallet() {
  try {
    const wallet = await apiJson("/billing/wallet");
    state.wallet = wallet;
    if (qs("#balanceMain")) qs("#balanceMain").textContent = "试用中";
    if (qs("#balanceSide")) qs("#balanceSide").textContent = "个人中心";
    if (qs("#walletBalance")) qs("#walletBalance").textContent = Number(wallet.balance_credits ?? wallet.balance ?? 0).toFixed(2);
  } catch (error) {
    state.wallet = null;
    if (qs("#walletBalance")) qs("#walletBalance").textContent = "100.00";
  }
}

async function refreshAdminConsole() {
  return Promise.resolve();
}

async function handleSandboxRecharge() {
  const message = "已记录线下确认提醒；正式额度和服务状态由运营后台更新。";
  setTextIfPresent("#rechargeNotice span", message);
  if (qs("#balanceMain")) qs("#balanceMain").textContent = "试用中";
  recordUiAction("service:offline-confirmation-requested", "pass", message, {
    persistence: "ui_service_record",
    account_id: currentAccountId(),
  });
  showToast(message);
  return { status: "recorded", mode: "offline_service_record" };
}

async function refreshInbox() {
  const table = qs("#inboxTable");
  try {
    const items = await apiJson("/inbox");
    if (table) {
      const rows = (items || []).map((item) => `
        <div class="table-row">
          <span>${escapeHtml(item.subject || item.id)}</span>
          <span>${escapeHtml(item.status || "unread")}</span>
          <span>${escapeHtml(String(item.created_at || "-").slice(0, 19))}</span>
          <span>${item.attachment_name ? escapeHtml(item.attachment_name) : "-"}</span>
        </div>
      `).join("");
      table.innerHTML = `
        <div class="table-row head"><span>标题</span><span>状态</span><span>时间</span><span>附件</span></div>
        ${rows || `<div class="table-row"><span>暂无服务消息。</span><span>-</span><span>-</span><span>-</span></div>`}
      `;
    }
    const message = (items || []).length ? `发票箱已刷新：${items.length} 条记录。` : "发票箱已刷新：暂无记录。";
    recordUiAction("inbox:refresh", "pass", message, { count: (items || []).length, persistence: "backend_inbox_list" });
    showToast(message);
    return items;
  } catch (error) {
    const message = `发票箱刷新未完成：${error.message || error}`;
    recordUiAction("inbox:refresh", "blocked", message);
    showToast(message);
    return [];
  }
}

/* ── Workspace progress bar (P0-1) ─────────────────────────────────── */
const PROGRESS_STEPS = [
  { id: 'project', label: '创建项目', view: 'dashboard' },
  { id: 'data', label: '上传数据', view: 'storage' },
  { id: 'preparation', label: '数据准备', view: 'analysis' },
  { id: 'analysis', label: '运行分析', view: 'workflow' },
  { id: 'results', label: '查看结果', view: 'statistics' },
  { id: 'report', label: '生成复核记录', view: 'publication' },
];

const PAGE_ROUTE_CONTRACT = {
  dashboard: { view: "dashboard", roles: ["customer"], workflow: "project" },
  storage: { view: "storage", roles: ["customer"], workflow: "data" },
  analysis: { view: "analysis", roles: ["customer"], workflow: "preparation" },
  workflow: { view: "workflow", roles: ["customer"], workflow: "analysis" },
  epilepsyWorkbenchInline: { view: "epilepsyWorkbenchInline", roles: ["customer"], workflow: "analysis", parent: "workflow" },
  statistics: { view: "statistics", roles: ["customer"], workflow: "results" },
  publication: { view: "publication", roles: ["customer"], workflow: "report" },
  userCenter: { view: "userCenter", roles: ["customer"], workflow: null },
  upload: { aliasOf: "storage" },
  paradigms: { redirectTo: "dashboard" },
  journey: { view: "journey", roles: ["admin"], workflow: null },
  adminDashboard: { view: "adminDashboard", roles: ["admin"], workflow: null },
  adminOperations: { view: "adminOperations", roles: ["admin"], workflow: null },
  adminFinance: { view: "adminFinance", roles: ["admin"], workflow: null },
  adminSystem: { view: "adminSystem", roles: ["admin"], workflow: null },
};

function routeFallbackForRole(role = state.role) {
  return role === "admin" ? "adminDashboard" : "dashboard";
}

function resolvePageRoute(viewName, role = state.role) {
  const requestedView = String(viewName || routeFallbackForRole(role));
  let route = PAGE_ROUTE_CONTRACT[requestedView] || { view: requestedView };
  let targetView = route.aliasOf || route.redirectTo || route.view || requestedView;
  let contract = PAGE_ROUTE_CONTRACT[targetView] || { view: targetView };

  if (!role && !new Set(["login", "register"]).has(targetView)) {
    return { requestedView, targetView, blocked: true, reason: "login-required" };
  }
  if (contract.roles && role && !contract.roles.includes(role)) {
    targetView = routeFallbackForRole(role);
    contract = PAGE_ROUTE_CONTRACT[targetView] || { view: targetView };
  }
  if (!document.getElementById(targetView)) {
    targetView = routeFallbackForRole(role);
    contract = PAGE_ROUTE_CONTRACT[targetView] || { view: targetView };
  }
  return {
    requestedView,
    targetView,
    navView: contract.parent || targetView,
    aliasOf: route.aliasOf || "",
    redirectedFrom: route.redirectTo ? requestedView : "",
    contract,
  };
}

function getWorkspaceProgressState() {
  const hasCompletedTask = isCompletedAnalysisTask(latestAnalysisTask());
  return {
    hasProject: Boolean(state.real.project?.id),
    hasFile: Boolean(state.real.eegFile?.id),
    hasPreparationPlan: isAnalysisReady(),
    hasCompletedTask,
    hasViewedResults: Boolean(hasCompletedTask && state.real.resultsViewed),
    hasReport: Boolean(state.real.report?.id),
  };
}

function getCurrentProgressStep(progress) {
  if (!progress.hasProject) return 'project';
  if (!progress.hasFile) return 'data';
  if (!progress.hasPreparationPlan) return 'preparation';
  if (!progress.hasCompletedTask) return 'analysis';
  if (!progress.hasViewedResults) return 'results';
  if (!progress.hasReport) return 'report';
  return 'report';
}

function getStepState(stepId, progress) {
  const completed = {
    project: progress.hasProject,
    data: progress.hasFile,
    preparation: progress.hasPreparationPlan,
    analysis: progress.hasCompletedTask,
    results: progress.hasViewedResults,
    report: progress.hasReport,
  };
  return completed[stepId] ? 'completed' : 'pending';
}

function getWorkspaceNextRecommendation(progress = getWorkspaceProgressState()) {
  if (!progress.hasProject) return { label: "创建或打开项目", view: "dashboard" };
  if (!progress.hasFile) return { label: "上传或选择 EEG 数据", view: "storage" };
  if (!progress.hasPreparationPlan) return { label: "确认准备并进入分析", view: "analysis" };
  if (!progress.hasCompletedTask) return { label: "运行 PSD 分析", view: "workflow" };
  if (!progress.hasViewedResults) return { label: "查看分析结果", view: "statistics" };
  if (!progress.hasReport) return { label: "生成复核记录", view: "publication" };
  return { label: "下载复核记录包", view: "publication" };
}

function getRecoveryActionForAnalysisFlow() {
  const progress = getWorkspaceProgressState();
  const next = getWorkspaceNextRecommendation(progress);
  const icon = {
    dashboard: "folder-kanban",
    storage: "database",
    analysis: "sliders-horizontal",
    workflow: "activity",
    publication: "file-output",
  }[next.view] || "arrow-right";
  return { ...next, icon };
}

function renderWorkspaceProgressBar() {
  try {
    const bar = qs('#workspaceProgressBar');
    if (!bar) return;

    if (state.role !== 'customer') {
      bar.hidden = true;
      return;
    }
    // 个人中心/账号页不属于工作流，隐藏流程条
    const currentViewId = document.querySelector('.view.active')?.id;
    const nonWorkflowViews = new Set(['dashboard', 'userCenter', 'login', 'register']);
    if (nonWorkflowViews.has(currentViewId)) {
      bar.hidden = true;
      return;
    }
    bar.hidden = false;

    const progress = getWorkspaceProgressState();
    const currentStep = getCurrentProgressStep(progress);
    const currentView = currentViewId;
    const next = getWorkspaceNextRecommendation(progress);

    const stepHtml = PROGRESS_STEPS.map((step, i) => {
      const stepState = getStepState(step.id, progress);
      const isActive = step.view === currentView;
      const isRecommended = step.id === currentStep && !isActive;
      return `<button type="button" class="progress-step ${isActive ? 'active' : ''} ${isRecommended ? 'recommended' : ''} ${stepState === 'completed' ? 'completed' : ''}" data-progress-view="${step.view}">
        <span class="step-num">${stepState === 'completed' ? '✓' : i + 1}</span>
        <span>${step.label}</span>
      </button>${i < PROGRESS_STEPS.length - 1 ? '<span class="progress-step-divider">→</span>' : ''}`;
    }).join('');
    bar.innerHTML = `
      <div class="progress-step-list">${stepHtml}</div>
      <button type="button" class="workflow-next-hint" data-progress-view="${next.view}">
        <span>下一步</span><strong>${escapeHtml(next.label)}</strong>
      </button>
    `;

    bar.querySelectorAll('[data-progress-view]').forEach(btn => {
      btn.addEventListener('click', () => setView(btn.dataset.progressView));
    });
  } catch (e) {
    console.warn('[progress-bar] render failed:', e);
  }
}

function renderDashboardStarter(progress = getWorkspaceProgressState()) {
  const panel = qs('[data-testid="project-crud-panel"]');
  if (!panel || state.role !== "customer") return;
  let starter = panel.querySelector('[data-testid="dashboard-starter"]');
  if (!starter) {
    starter = document.createElement("div");
    starter.className = "dashboard-starter";
    starter.dataset.testid = "dashboard-starter";
    const head = panel.querySelector(".panel-head");
    if (head?.nextSibling) head.after(starter);
    else panel.prepend(starter);
  }
  const next = getWorkspaceNextRecommendation(progress);
  const currentStep = getCurrentProgressStep(progress);
  const stepHtml = PROGRESS_STEPS.map((step, index) => {
    const stepState = getStepState(step.id, progress);
    return `<button type="button" class="starter-step ${step.id === currentStep ? "active" : ""} ${stepState === "completed" ? "completed" : ""}" data-progress-view="${step.view}" aria-current="${step.id === currentStep ? "step" : "false"}">
      <span>${stepState === "completed" ? "✓" : index + 1}</span><strong>${escapeHtml(step.label)}</strong>
    </button>`;
  }).join("");
  starter.innerHTML = `
    <div class="starter-steps">${stepHtml}</div>
    <div class="starter-actions">
      <button type="button" class="ghost-btn mini starter-next" data-progress-view="${escapeHtml(next.view)}" ${currentStep === "project" ? "hidden aria-hidden=\"true\"" : ""}><span>${escapeHtml(next.label)}</span></button>
      <button type="button" class="ghost-btn mini starter-demo" data-teaching-action="quickstart" title="载入合成 EEG 数据并进入数据准备"><i data-lucide="graduation-cap"></i><span>使用示例 EEG 走一遍</span></button>
    </div>
  `;
  starter.querySelectorAll("[data-progress-view]").forEach((button) => {
    button.addEventListener("click", () => setView(button.dataset.progressView));
  });
}

function setView(viewName) {
  const aliases = {
    billing: "userCenter",
    invoice: "userCenter",
  };
  const requestedView = aliases[String(viewName || "")] || String(viewName || routeFallbackForRole());
  const resolved = resolvePageRoute(requestedView);
  if (resolved.blocked) {
    console.warn(`尝试访问 ${requestedView} 但未登录，重定向到登录页`);
    logout(false);
    return;
  }
  const targetView = resolved.targetView;
  if (targetView === "statistics" && latestAnalysisTask()?.id) {
    state.real.resultsViewed = true;
    markLatestResultsReviewed().catch(() => null);
  }
  document.body.dataset.requestedView = resolved.requestedView;
  document.body.dataset.routeAliasOf = resolved.aliasOf || "";
  document.body.dataset.routeRedirectedFrom = resolved.redirectedFrom || "";
  qsa(".view").forEach((section) => {
    section.classList.toggle("active", section.id === targetView);
  });
  qsa("[data-view]").forEach((button) => {
    button.classList.toggle("active", button.dataset.view === resolved.navView);
  });
  const viewTitle = qs("#viewTitle");
  if (viewTitle) {
    const activeButton = qsa(`[data-view="${resolved.navView}"]`).find((button) => button.closest?.(".nav"));
    viewTitle.textContent = titles[targetView] || activeButton?.textContent?.trim() || targetView;
  }
  if (window.location.hash !== `#${targetView}`) {
    window.location.hash = `#${targetView}`;
  }
  requestAnimationFrame(() => window.scrollTo({ top: 0, left: 0, behavior: "auto" }));
  ensureRealEegFileInput();
  renderStorageManagement();
  renderRealResultReview();
  renderRealDelivery();
  updateRealActionGate();
  applyCleanVisibleCopy();
  publishE2EState();
  if (targetView === "analysis") {
    const file = currentWorkspaceFile();
    if (file?.id && eegState.selectedFilePreviewId !== file.id && !eegState.autoPreviewInFlight) {
      requestAutoQcPreviewForSelectedFile(file).catch((error) => {
        recordUiAction("real:auto-qc-preview-on-view", "blocked", error?.message || String(error), { file_id: file.id });
      });
    }
  }
  renderWorkspaceProgressBar();
  if (targetView === 'analysis') applyAnalysisPageStateGate();
  if (targetView === 'workflow') setTimeout(regroupAnalysisMethods, 100);
  if (targetView === 'epilepsyWorkbenchInline') renderInlineEpilepsyWorkbench();
}

function renderAdminCustomerProfile() {
  const customer = getStoredCustomer();
  const safeText = (value, fallback = "-") => value || fallback;
  if (qs("#adminCustomerName")) qs("#adminCustomerName").textContent = safeText(customer.name);
  if (qs("#adminCustomerEmail")) qs("#adminCustomerEmail").textContent = maskEmail(customer.email);
  if (qs("#adminCustomerOrg")) qs("#adminCustomerOrg").textContent = safeText(customer.org);
  if (qs("#adminCustomerRegisteredAt")) qs("#adminCustomerRegisteredAt").textContent = safeText(customer.registeredAt);
}

function startDemoWorkspace(persist = true) {
  saveCustomer({
    ...demoCustomer,
    name: demoCustomer.name || "客户账户",
    email: demoCustomer.email || "customer@qlanalyser.online",
    org: demoCustomer.org || "QLanalyser Online",
    registeredAt: demoCustomer.registeredAt || "未记录",
  });
  rememberSession("customer", persist);
  loginAs("customer", getStoredCustomer());
  setLoginMessage("已进入 QLanalyser Online。", "success");
  showToast("已进入 QLanalyser Online。");
}

function fillDemoCustomerCredentials() {
  const emailInput = qs("#customerEmail");
  const passwordInput = qs("#customerPassword");
  const rememberInput = qs("#rememberCustomer");
  if (emailInput) emailInput.value = demoCustomer.email;
  if (passwordInput) passwordInput.value = demoCustomer.password;
  if (rememberInput) rememberInput.checked = true;
  switchLoginTab("customerLogin");
}

window.handleCustomerLoginClick = async function handleCustomerLoginClick(event) {
  event?.preventDefault?.();
  const emailInput = qs("#customerEmail");
  const passwordInput = qs("#customerPassword");
  const email = emailInput?.value.trim() || "";
  const password = passwordInput?.value || "";
  const remember = Boolean(qs("#rememberCustomer")?.checked);
  if (!email || !password) {
    const message = "\u8bf7\u5148\u8f93\u5165\u90ae\u7bb1/\u624b\u673a\u53f7\u548c\u5bc6\u7801\uff0c\u518d\u70b9\u51fb\u767b\u5f55\u3002";
    setLoginFieldValidity(false);
    setLoginMessage(message, "error");
    showToast(message);
    (email ? passwordInput : emailInput)?.focus();
    return false;
  }
  setLoginFieldValidity(true);
  await loginCustomer(email, password, remember);
  return false;
};

async function loginCustomer(email, password, remember) {
  if (!email || !password) {
    const message = "\u8bf7\u5148\u8f93\u5165\u90ae\u7bb1/\u624b\u673a\u53f7\u548c\u5bc6\u7801\uff0c\u518d\u70b9\u51fb\u767b\u5f55\u3002";
    setLoginFieldValidity(false);
    setLoginMessage(message, "error");
    showToast(message);
    return;
  }
  try {
    const session = await apiJson("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    const account = session.account || {};
    saveCustomer({
      accountId: account.id,
      name: account.name || email,
      email: account.email || email,
      org: account.organization_name || "QLanalyser Online",
      phone: account.phone || "",
      registeredAt: account.created_at || new Date().toISOString().slice(0, 10),
      token: session.token,
    });
    rememberSession("customer", remember, { token: session.token, accountId: account.id });
    loginAs("customer", getStoredCustomer());
    await refreshWallet();
    setLoginFieldValidity(true);
    setLoginMessage("已进入 QLanalyser Online。", "success");
  } catch (error) {
    if (email === demoCustomer.email && password === demoCustomer.password && (isLocalHost() || hasExplicitCustomerDemoMode())) {
      console.warn("Demo login backend unavailable; entering local demo workspace.", error);
      startDemoWorkspace(remember);
      return;
    }
    setLoginMessage(error.message || "\u767b\u5f55\u5931\u8d25\uff0c\u8bf7\u68c0\u67e5\u8d26\u53f7\u548c\u5bc6\u7801\u3002", "error");
  }
}

async function registerCustomer({ name, email, phone, org, password, code, mode }) {
  if (!name.trim()) {
    setLoginMessage("\u8bf7\u5148\u8f93\u5165\u59d3\u540d\u548c\u5bc6\u7801\u3002", "error");
    return;
  }
  const normalizedMode = mode === "phone" ? "phone" : mode === "wechat" ? "wechat" : "email";
  if (normalizedMode === "email" && !validateEmail(email.trim())) {
    setLoginMessage("\u8bf7\u8f93\u5165\u90ae\u7bb1\u5730\u5740\u3002", "error");
    return;
  }
  if (normalizedMode === "phone" && !phone.trim()) {
    setLoginMessage("\u8bf7\u8f93\u5165\u624b\u673a\u53f7\u3002", "error");
    return;
  }
  if (normalizedMode !== "wechat" && code.trim().length < 4) {
    setLoginMessage("\u8bf7\u8f93\u5165\u9a8c\u8bc1\u7801\u3002", "error");
    return;
  }
  if (normalizedMode !== "wechat" && password.length < 8) {
    setLoginMessage("\u5bc6\u7801\u81f3\u5c11\u9700\u8981 8 \u4e2a\u5b57\u7b26\u3002", "error");
    return;
  }
  try {
    const session = await apiJson("/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        register_method: normalizedMode,
        email: email.trim(),
        phone: phone.trim(),
        password,
        name: name.trim(),
        organization_name: org.trim() || "研究团队",
        verification_code: code.trim(),
        wechat_openid: normalizedMode === "wechat" ? `wx_web_${Date.now()}` : "",
        wechat_nickname: normalizedMode === "wechat" ? name.trim() : "",
      }),
    });
    const account = session.account || {};
    const profile = {
      accountId: account.id,
      name: account.name || name.trim(),
      email: account.email || email.trim(),
      phone: account.phone || phone.trim(),
      org: account.organization_name || org.trim() || "研究团队",
      password,
      registeredAt: account.created_at || new Date().toISOString().slice(0, 10),
      token: session.token,
    };
    saveCustomer(profile);
    rememberSession("customer", true, { token: session.token, accountId: account.id });
    loginAs("customer", profile);
    await refreshWallet();
    setLoginMessage("QLanalyser \u8d26\u53f7\u5df2\u521b\u5efa\u3002", "success");
    showToast(normalizedMode === "email" ? "\u90ae\u7bb1\u6ce8\u518c\u5df2\u5b8c\u6210\u3002" : normalizedMode === "phone" ? "\u624b\u673a\u53f7\u6ce8\u518c\u5df2\u5b8c\u6210\u3002" : "\u5fae\u4fe1\u6ce8\u518c\u5df2\u5b8c\u6210\u3002");
  } catch (error) {
    setLoginMessage(error.message || "\u6ce8\u518c\u5931\u8d25\uff0c\u8bf7\u68c0\u67e5\u4fe1\u606f\u540e\u91cd\u8bd5\u3002", "error");
  }
}

async function loginAdmin(email, password) {
  if (!email || !password) {
    setLoginMessage("\u8bf7\u8f93\u5165\u7ba1\u7406\u5458\u90ae\u7bb1\u548c\u5bc6\u7801\u3002", "error");
    return;
  }
  let session;
  try {
    session = await apiJson("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
  } catch (error) {
    setLoginMessage(error.message || "\u7ba1\u7406\u5458\u767b\u5f55\u5931\u8d25\uff0c\u8bf7\u68c0\u67e5\u8d26\u53f7\u3002", "error");
    return;
  }
  rememberSession("admin", true, { token: session.token, accountId: session.account?.id });
  loginAs("admin");
  await refreshAdminConsole();
  setLoginMessage("已进入 QLanalyser 内部后台。", "success");
  showToast("已进入 QLanalyser 内部后台。");
}

function sendSandboxVerificationCode() {
  const mode = qs('input[name="registerMode"]:checked')?.value || "email";
  const target = mode === "phone" ? qs("#registerPhone")?.value.trim() : qs("#registerEmail")?.value.trim();
  if (mode !== "wechat" && !target) {
    const message = mode === "phone" ? "请先输入手机号，再发送沙盒验证码。" : "请先输入邮箱，再发送沙盒验证码。";
    setLoginMessage(message, "error");
    showToast(message);
    return;
  }
  const code = "1234";
  if (qs("#registerCode")) qs("#registerCode").value = code;
  const message = mode === "wechat"
    ? "微信授权为沙盒模式：已生成本地验证凭据。"
    : `沙盒验证码已生成：${code}。`;
  setLoginMessage(message, "success");
  recordUiAction("auth:send-verification-code", "pass", message, { mode, provider_mode: "sandbox" });
  showToast(message);
}

function handleRegisterModeChange() {
  const mode = qs('input[name="registerMode"]:checked')?.value || "email";
  qsa(".register-email-field").forEach((node) => { node.hidden = mode !== "email"; });
  qsa(".register-phone-field").forEach((node) => { node.hidden = mode !== "phone"; });
  qsa(".register-password-field").forEach((node) => { node.hidden = mode === "wechat"; });
  const hint = qs("#registerModeHint");
  if (hint) {
    hint.textContent = mode === "wechat"
      ? "当前为微信授权沙盒流程，不连接真实微信账号。"
      : "当前验证码为沙盒验证，不发送真实短信或邮件。";
  }
}

function collectRegisterPayload() {
  return {
    name: qs("#registerName")?.value || "",
    email: qs("#registerEmail")?.value || "",
    phone: qs("#registerPhone")?.value || "",
    org: qs("#registerOrg")?.value || "",
    password: qs("#registerPassword")?.value || "",
    code: qs("#registerCode")?.value || "",
    mode: qs('input[name="registerMode"]:checked')?.value || "email",
  };
}

async function restoreSession() {
  const raw = localStorage.getItem(AUTH_KEY) || sessionStorage.getItem(AUTH_KEY);
  if (!raw) {
    logout(false);
    return;
  }
  try {
    const session = JSON.parse(raw);
    if (session.role === "admin" || session.role === "customer") {
      // SEC-FIX: Verify token with backend before restoring UI
      try {
        const resp = await fetch(`${state.apiBase}/accounts`, {
          headers: { "Authorization": `Bearer ${session.token}` }
        });
        
        if (resp.status === 401 || resp.status === 403) {
          // Token invalid or expired
          console.warn("Session token验证失败，清除本地session");
          clearSession();
          logout(false);
          return;
        }
        
        if (!resp.ok) {
          // Other errors, still allow login but log warning
          console.warn("Token验证请求失败，允许登录但可能需要重新认证");
        }
        
        // Token valid, proceed with login
        loginAs(session.role, session.role === "customer" ? getStoredCustomer() : null);
        return;
      } catch (error) {
        if (session.role === "admin") {
          console.warn("管理员 token 无法验证，清除本地 session:", error);
          clearSession();
          logout(false);
          return;
        }
        // Customer demo can continue offline in local development.
        console.warn("无法验证客户 token（网络错误），允许本地客户访问:", error);
        loginAs(session.role, session.role === "customer" ? getStoredCustomer() : null);
        return;
      }
    }
  } catch {
    clearSession();
  }
  logout(false);
}

function loginAs(role, profile = null) {
  clearAuthenticatedArtifactObjectUrls();
  state.role = role;
  setAuthenticatedShellVisible(true);
  applyRoleNavigationState(role);
  ensureRealEegFileInput();
  if (role === "admin") {
    state.teaching.active = false;
    state.teaching.guideActive = false;
    state.teaching.datasetLoaded = false;
    hideTeachingGuideOverlay();
    qs("#roleLabel").textContent = "内部账号";
    qs("#balanceSide").textContent = "后台";
    qs("#accountHint").textContent = "查看任务、客户与系统状态";
    const accountMeta = qs("#accountMeta");
    if (accountMeta) accountMeta.textContent = "admin / 管理权限";
    qs("#topEyebrow").textContent = "QLanalyser Online · 内部后台";
    renderAdminCustomerProfile();
    setView("adminDashboard");
  } else {
    const customer = profile || getStoredCustomer();
    const isDemoCustomer = customer.email === demoCustomer.email;
    qs("#roleLabel").textContent = customer.name || "客户账号";
    qs("#balanceSide").textContent = "个人中心";
    qs("#accountHint").textContent = visibleCustomerShellHint(customer);
    const accountMeta = qs("#accountMeta");
    if (accountMeta) {
      accountMeta.textContent = `${maskEmail(customer.email || demoCustomer.email)} / 客户账号`;
    }
    qs("#topEyebrow").textContent = "QLanalyser Online · EEG 科研数据到复核记录";
    const hashView = window.location.hash.slice(1);
    const targetView = isEpilepsyWorkbenchDeepLinkIntent() 
      ? "epilepsyWorkbenchInline" 
      : (hashView || "dashboard");
    setView(targetView);
    updateRealActionGate();
    refreshProjectWorkspace().then(() => {
      if (isEpilepsyWorkbenchDeepLinkIntent()) bootstrapEpilepsyDeepLinkWorkbench("login_restore").catch((error) => {
        recordUiAction("epilepsy:deeplink-bootstrap", "blocked", error?.message || String(error));
      });
    }).catch((error) => {
      recordUiAction("workspace:refresh", "blocked", error.message || "项目刷新失败");
      if (isEpilepsyWorkbenchDeepLinkIntent()) bootstrapEpilepsyDeepLinkWorkbench("login_restore_after_refresh_error").catch(() => null);
    });
  }
  applyShellCopyFixesAscii(role, profile);
  applyCleanVisibleCopy();
  if (window.lucide) lucide.createIcons();
  window.scrollTo({ top: 0, left: 0, behavior: "auto" });
}

function applyShellCopyFixes(role, profile = null) {
  return applyShellCopyFixesAscii(role, profile);
}

function applyShellCopyFixesAsciiLegacy(role, profile = null) {
  if (role === "admin") {
    qs("#roleLabel").textContent = "内部账号";
    qs("#balanceSide").textContent = "后台";
    qs("#accountHint").textContent = "管理客户、项目、任务、发票和系统状态";
    qs("#topEyebrow").textContent = "QLanalyser Online · 内部后台";
    return;
  }
  const customer = profile || getStoredCustomer();
  qs("#roleLabel").textContent = customer.name || "客户账户";
  qs("#balanceSide").textContent = "账户概览";
  qs("#accountHint").textContent = visibleCustomerShellHint(customer);
  qs("#topEyebrow").textContent = "QLanalyser Online · EEG 科研数据到复核记录";
}

function applyShellCopyFixesAscii(role, profile = null) {
  if (role === "admin") {
    qs("#roleLabel").textContent = "内部账号";
    qs("#balanceSide").textContent = "后台";
    qs("#accountHint").textContent = "查看账号、任务、交付与系统状态";
    qs("#topEyebrow").textContent = "QLanalyser Online · 内部后台";
    return;
  }
  const customer = profile || getStoredCustomer();
  qs("#roleLabel").textContent = customer.name || "客户账号";
  qs("#balanceSide").textContent = "个人中心";
  qs("#accountHint").textContent = visibleCustomerShellHint(customer);
  qs("#topEyebrow").textContent = "QLanalyser Online · EEG 科研数据到复核记录";
}

function renderProjectDataManagement() {
  const projects = state.workspace.projects || [];
  const files = state.workspace.files || [];
  const plans = state.workspace.plans || [];
  const epochSets = state.workspace.epochSets || [];
  const selectedProjectId = state.workspace.selectedProjectId || null;
  const selectedProjectCandidate = selectedProjectId
    ? projects.find((item) => item.id === selectedProjectId) || (state.real.project?.id === selectedProjectId ? state.real.project : null)
    : null;
  const project = selectedProjectCandidate && (state.workspace.showReviewProjects || !isHiddenFromCustomerProjectList(selectedProjectCandidate))
    ? selectedProjectCandidate
    : null;
  const projectFiles = scopedProjectFiles(project, files);
  const selectedFileId = project?.id ? state.workspace.selectedFileId || null : null;
  const file = project?.id
    ? (selectedFileId ? projectFiles.find((item) => item.id === selectedFileId) : null)
      || (state.real.eegFile?.project_id === project.id ? state.real.eegFile : null)
    : null;
  const filePlans = file ? plans.filter((item) => item.input_file_id === file.id) : [];
  const selectedPlanId = state.workspace.selectedPlanId || state.real.plan?.id || null;
  const plan = file
    ? (selectedPlanId ? filePlans.find((item) => item.id === selectedPlanId) : null)
      || (state.real.plan?.id && state.real.plan.input_file_id === file.id ? state.real.plan : null)
    : null;
  const epochSet = file
    ? state.real.epochSet?.input_file_id === file.id
      ? state.real.epochSet
      : epochSets.find((item) => item.input_file_id === file.id) || null
    : null;
  const projectRows = qs("#iaProjectRows");
  const projectRowActions = qs('[data-testid="project-crud-panel"] .ia-row-actions');
  const dataRows = qs("#iaDataRows");
  const prepQueue = qs("#prepDataQueue");
  const prepContextSummary = qs("#prepContextSummary");
  const prepRevisionState = qs("#prepRevisionState");
  const fileSelect = qs("#workspaceFileSelect");
  const fileFocusSelect = qs("#workspaceFileFocusSelect");
  const planSelect = qs("#workspacePlanSelect");
  const projectSearch = qs("#workspaceProjectSearch");
  const showReviewProjects = qs("#workspaceShowReviewProjects");
  const projectFilterSummary = qs("#workspaceProjectFilterSummary");
  const visibleProjects = filteredWorkspaceProjects(projects, files);

  if (projectSearch) {
    projectSearch.value = state.workspace.projectSearch || "";
  }
  if (showReviewProjects) {
    showReviewProjects.checked = Boolean(state.workspace.showReviewProjects);
  }
  updateProjectVisibilityToggleLabel(projects);
  updateProjectRowActionState(project);
  if (projectFilterSummary) {
    const hiddenDefaultCount = projects.filter((item) => isHiddenFromCustomerProjectList(item)).length;
    const hiddenCount = Math.max(0, projects.length - visibleProjects.length);
    if (state.workspace.projectSearch) {
      projectFilterSummary.textContent = `搜索结果：${visibleProjects.length} / ${projects.length} 个项目。`;
    } else if (state.workspace.showReviewProjects) {
      projectFilterSummary.textContent = `已显示内部/归档项目：${visibleProjects.length} / ${projects.length} 个项目。`;
    } else {
      projectFilterSummary.textContent = `默认显示 ${visibleProjects.length} / ${projects.length} 个项目；已隐藏 ${hiddenDefaultCount || hiddenCount} 个内部验收、归档或自动生成项目。`;
    }
  }
  if (fileSelect) {
    fileSelect.innerHTML = project?.id
      ? `<option value="">选择数据文件</option>${workspaceFileOptions(projectFiles)}`
      : `<option value="">先选择项目</option>`;
    fileSelect.value = file?.id || "";
    fileSelect.disabled = !project?.id;
  }
  if (fileFocusSelect) {
    fileFocusSelect.innerHTML = project?.id
      ? `<option value="">选择数据文件</option>${workspaceFileOptions(projectFiles)}`
      : `<option value="">先选择项目</option>`;
    fileFocusSelect.value = file?.id || "";
    fileFocusSelect.disabled = !project?.id;
  }
  if (planSelect) {
    planSelect.innerHTML = file
      ? `<option value="">选择准备方案</option>${filePlans.map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.id)}${item.is_default ? "（默认）" : ""}</option>`).join("")}`
      : `<option value="">先选择数据</option>`;
    planSelect.value = plan?.id || "";
    planSelect.disabled = !file?.id;
  }

  if (qs("#iaProjectCount")) qs("#iaProjectCount").textContent = String(projects.length || 0);
  if (qs("#iaDataCount")) qs("#iaDataCount").textContent = String(project?.id ? projectFiles.length : 0);
  if (qs("#iaPreparedCount")) qs("#iaPreparedCount").textContent = plan?.id || epochSet?.id ? "1" : "0";
  if (prepContextSummary) {
    prepContextSummary.textContent = selectedStateLabel(project, file, plan, epochSet);
  }
  if (prepRevisionState) {
    prepRevisionState.textContent = `准备状态：${preparationStatusLabel(file, plan, epochSet)}；范围：${project?.name || project?.id || "当前项目"}.`;
  }

  if (projectRows) {
    const rows = (visibleProjects.length ? visibleProjects : []).slice(0, 12).map((item) => {
      const count = item.data_count ?? files.filter((row) => row.project_id === item.id).length;
      const isSelected = item.id === project?.id;
      return `
        <div class="table-row${isSelected ? " selected" : ""}">
          <span>${escapeHtml(projectDisplayName(item) || "未命名项目")}${isSelected ? `<small>当前项目</small>` : ""}</span>
          <span>${escapeHtml(String(count || 0))} 份数据</span>
          <span>${escapeHtml(projectStatusLabel(item, files))}</span>
          <button class="ghost-btn mini" type="button" data-project-select="${escapeHtml(item.id)}">${isSelected ? "已选中" : "打开项目"}</button>
        </div>
      `;
    }).join("");
    projectRows.innerHTML = `
      <div class="table-row head"><span>项目</span><span>数据</span><span>状态</span><span>入口</span></div>
      ${rows || `<div class="table-row empty-row"><span>暂无项目</span><span>-</span><span>先创建项目</span><button class="ghost-btn mini" type="button" data-real-action="create-project">创建项目</button></div>`}
    `;
  }

  if (dataRows) {
    dataRows.hidden = !project?.id;
    const rows = project?.id ? projectFiles.slice(0, 8).map((item) => {
      const rowPrep = epochSets.find((epoch) => epoch.input_file_id === item.id) || plans.find((candidate) => candidate.input_file_id === item.id) || null;
      const isSelected = item.id === file?.id;
      return `
        <div class="table-row${isSelected ? " selected" : ""}">
          <span>${escapeHtml(eegFileDisplayName(item) || "EEG 文件")}${isSelected ? `<small>当前数据</small>` : ""}</span>
          <span>${escapeHtml(fileDetailLabel(item))}</span>
          <span>${escapeHtml(rowPrep ? `已准备 修订版本 ${rowPrep.revision ?? rowPrep.data_preparation_revision ?? 1}` : "未准备")}</span>
          <button class="ghost-btn mini" type="button" data-file-select="${escapeHtml(item.id)}" data-jump-to-analysis="1" data-ia-action="select-prep-data" title="${escapeHtml(eegFileDisplayName(item) || item.original_filename || item.id || "EEG 文件")}">${isSelected ? "当前数据" : "预览 / 预处理"}</button>
        </div>
      `;
    }).join("") : "";
    dataRows.innerHTML = `
      <div class="table-row head"><span>文件</span><span>格式</span><span>准备</span><span>操作</span></div>
      ${rows || `<div class="table-row empty-row"><span>${project?.id ? "当前项目暂无数据文件" : "请先选择项目"}</span><span>-</span><span>-</span><button class="ghost-btn mini" type="button" disabled>${project?.id ? "暂无数据" : "请先选项目"}</button></div>`}
    `;
  }

  if (prepQueue) {
    prepQueue.hidden = !project?.id;
    const rows = project?.id ? projectFiles.slice(0, 8).map((item) => {
      const rowPrep = epochSets.find((epoch) => epoch.input_file_id === item.id) || plans.find((candidate) => candidate.input_file_id === item.id) || null;
      const isSelected = item.id === file?.id;
      return `
        <div class="table-row${isSelected ? " selected" : ""}">
          <span>${escapeHtml(eegFileDisplayName(item) || "EEG file")}</span>
          <span>${escapeHtml(rowPrep ? `已准备 修订版本 ${rowPrep.revision ?? rowPrep.data_preparation_revision ?? 1}` : "等待预览")}</span>
          <button class="ghost-btn mini" type="button" data-file-select="${escapeHtml(item.id)}" data-jump-to-analysis="1" data-ia-action="select-prep-data" title="${escapeHtml(eegFileDisplayName(item) || item.original_filename || item.id || "EEG 文件")}">${isSelected ? "继续预处理" : "选择 / 预览"}</button>
        </div>
      `;
    }).join("") : "";
    prepQueue.innerHTML = `
      <div class="table-row head"><span>文件</span><span>版本</span><span>操作</span></div>
      ${rows || `<div class="table-row empty-row"><span>${project?.id ? "当前项目暂无可预处理数据" : "请先选择项目"}</span><span>-</span><button class="ghost-btn mini" type="button" disabled>${project?.id ? "暂无数据" : "请先选项目"}</button></div>`}
    `;
  }
  const fileTrigger = qs('[data-file-trigger="real-eeg-file"]');
  if (fileTrigger) {
    fileTrigger.disabled = !project?.id;
    fileTrigger.title = project?.id ? "选择当前项目的 EEG 文件" : "请先选择或创建项目";
  }
  if (qs("#real-eeg-file")) {
    qs("#real-eeg-file").disabled = !project?.id;
  }
  applyProjectDataUxCleanup({ project, file, plan, epochSet, projectFiles, files, plans, epochSets });
  applyCleanVisibleCopy();
  renderEegPreviewEmptyState();
}

function applyProjectDataUxCleanup({ project, file, plan, epochSet, projectFiles = [], files = [], plans = [], epochSets = [] }) {
  const projectRows = qs("#iaProjectRows");
  const dataRows = qs("#iaDataRows");
  const dataPanel = qs('[data-testid="project-data-crud-panel"]');
  const dataEmptyState = qs("#iaDataEmptyState");
  const dataActions = qs(".ia-data-actions");
  const prepQueue = qs("#prepDataQueue");
  const prepContextSummary = qs("#prepContextSummary");
  const prepRevisionState = qs("#prepRevisionState");
  const hasProject = Boolean(project?.id);
  const hasFile = Boolean(file?.id);

  if (qs("#iaProjectCount")) qs("#iaProjectCount").textContent = project?.id ? (projectDisplayName(project) || project.id) : "未选择项目";
  if (qs("#iaDataCount")) qs("#iaDataCount").textContent = file?.id ? (eegFileDisplayName(file) || file.id) : (hasProject ? "暂无数据文件" : "未选择数据");
  if (qs("#iaPreparedCount")) qs("#iaPreparedCount").textContent = preparationStatusLabelReadable(file, plan, epochSet);
  const projectNameInput = qs("#realProjectName");
  if (projectNameInput && document.activeElement !== projectNameInput) {
    projectNameInput.value = project?.id ? (projectDisplayName(project) || project.name || "") : "";
    projectNameInput.disabled = !hasProject || isTeachingDemoProject(project);
    projectNameInput.title = isTeachingDemoProject(project) ? teachingProtectedMessage() : "";
  }
  if (prepContextSummary) {
    prepContextSummary.textContent = hasProject
      ? `当前项目：${projectDisplayName(project) || project.id}；数据文件：${projectFiles.length} 个；下一步：${projectFiles.length ? "选择数据进入预处理" : "上传 EEG 数据"}。`
      : "请先在左侧项目列表打开一个项目。";
  }
  if (prepRevisionState) {
    prepRevisionState.textContent = hasProject
      ? `数据状态：${projectFiles.length ? `${projectFiles.length} 个数据文件` : "等待上传"}。`
      : "数据状态：请先选择项目。";
  }
  updateDashboardSummaryCards({ project, file, plan, epochSet, projectFiles, files });
  if (dataPanel) dataPanel.classList.toggle("has-project", hasProject);
  if (dataEmptyState) {
    dataEmptyState.hidden = hasProject && projectFiles.length > 0;
    dataEmptyState.querySelector("strong").textContent = hasProject ? "当前项目暂无数据" : "请先选择项目";
    dataEmptyState.querySelector("span").textContent = hasProject
      ? "请先上传 EEG 数据。上传后这里会显示文件、格式、状态和进入预处理的入口。"
      : "从左侧项目列表打开一个项目后，这里才显示项目内数据。";
  }
  if (dataActions) dataActions.hidden = !hasProject;
  qsa('[data-ia-action="rename-data"]').forEach((button) => {
    button.hidden = !hasFile;
    const protectedTeachingFile = Boolean(hasFile && isTeachingDemoFile(file));
    button.disabled = protectedTeachingFile;
    button.setAttribute("aria-disabled", protectedTeachingFile ? "true" : "false");
    button.title = protectedTeachingFile ? teachingProtectedMessage() : "";
  });
  qsa('[data-ia-action="replace-data"], [data-ia-action="delete-data"]').forEach((button) => {
    button.hidden = true;
  });

  if (projectRows) {
    const visibleProjects = filteredWorkspaceProjects(state.workspace.projects || [], files);
    const rows = visibleProjects.slice(0, 12).map((item) => {
      const count = item.data_count ?? files.filter((row) => row.project_id === item.id).length;
      const selected = item.id === project?.id;
      return `
        <div class="table-row${selected ? " selected" : ""}">
          <span>${escapeHtml(projectDisplayName(item) || "未命名项目")}${selected ? `<small>当前项目</small>` : ""}</span>
          <span>${escapeHtml(String(count || 0))} 份数据</span>
          <span>${escapeHtml(projectStatusLabelReadable(item, files))}</span>
          <button class="ghost-btn mini" type="button" data-project-select="${escapeHtml(item.id)}">${selected ? "已选中" : "打开"}</button>
        </div>
      `;
    }).join("");
    projectRows.innerHTML = `
      <div class="table-row head"><span>项目</span><span>数据</span><span>状态</span><span>入口</span></div>
      ${rows || `<div class="table-row empty-row"><span>暂无项目</span><span>-</span><span>先创建项目</span><button class="ghost-btn mini" type="button" data-real-action="create-project">创建项目</button></div>`}
    `;
  }

  if (dataRows) {
    dataRows.hidden = !hasProject || projectFiles.length === 0;
    const rows = hasProject ? projectFiles.slice(0, 8).map((item) => {
      const rowPrep = epochSets.find((epoch) => epoch.input_file_id === item.id)
        || plans.find((candidate) => candidate.input_file_id === item.id)
        || null;
      const isSelected = item.id === file?.id;
      return `
        <div class="table-row${isSelected ? " selected" : ""}">
          <span>${escapeHtml(eegFileDisplayName(item) || "EEG 文件")}${isSelected ? `<small>当前数据</small>` : ""}</span>
          <span>${escapeHtml(fileDetailLabelReadable(item))}</span>
          <span>${escapeHtml(rowPrep ? `已准备 · 修订版本 ${rowPrep.revision ?? rowPrep.data_preparation_revision ?? 1}` : fileStatusLabelReadable(item))}</span>
          <button class="ghost-btn mini" type="button" data-file-select="${escapeHtml(item.id)}" data-jump-to-analysis="1" data-ia-action="select-prep-data" title="${escapeHtml(eegFileDisplayName(item) || item.original_filename || item.id || "EEG 文件")}">${isSelected ? "当前数据" : "预览 / 预处理"}</button>
        </div>
      `;
    }).join("") : "";
    dataRows.innerHTML = `
      <div class="table-row head"><span>文件</span><span>格式</span><span>状态</span><span>操作</span></div>
      ${rows}
    `;
  }

  if (prepQueue) {
    prepQueue.hidden = !hasProject;
    const rows = hasProject ? projectFiles.slice(0, 8).map((item) => {
      const rowPrep = epochSets.find((epoch) => epoch.input_file_id === item.id)
        || plans.find((candidate) => candidate.input_file_id === item.id)
        || null;
      const isSelected = item.id === file?.id;
      return `
        <div class="table-row${isSelected ? " selected" : ""}">
          <span>${escapeHtml(eegFileDisplayName(item) || "EEG 文件")}</span>
          <span>${escapeHtml(rowPrep ? `已准备 · 修订版本 ${rowPrep.revision ?? rowPrep.data_preparation_revision ?? 1}` : "等待预览")}</span>
          <button class="ghost-btn mini" type="button" data-file-select="${escapeHtml(item.id)}" data-jump-to-analysis="1" data-ia-action="select-prep-data" title="${escapeHtml(eegFileDisplayName(item) || item.original_filename || item.id || "EEG 文件")}">${isSelected ? "继续预处理" : "选择 / 预览"}</button>
        </div>
      `;
    }).join("") : "";
    prepQueue.innerHTML = `
      <div class="table-row head"><span>文件</span><span>版本</span><span>操作</span></div>
      ${rows || `<div class="table-row empty-row"><span>当前项目暂无可预处理数据</span><span>-</span><button class="ghost-btn mini" type="button" disabled>暂无数据</button></div>`}
    `;
  }
}



function updateDashboardSummaryCards({ project, file, plan, epochSet, projectFiles = [], files = [] }) {
  const projectCardValue = qs("#iaProjectCount");
  const projectCardNote = qs("#dashboard .metric-grid .metric:nth-child(1) small");
  const dataCardValue = qs("#iaDataCount");
  const dataCardNote = qs("#dashboard .metric-grid .metric:nth-child(2) small");
  const prepCardValue = qs("#iaPreparedCount");
  const prepCardNote = qs("#dashboard .metric-grid .metric:nth-child(3) small");
  const nextCardValue = qs("#dashboard .metric-grid .metric:nth-child(4) strong");
  const nextCardNote = qs("#dashboard .metric-grid .metric:nth-child(4) small");

  const projectName = project?.id ? (projectDisplayName(project) || project.id) : "未选择项目";
  const projectStatus = project?.id ? projectStatusLabelReadable(project, files) : "先从项目列表选择一个项目";
  const fileName = file?.id ? (eegFileDisplayName(file) || file.id) : (project?.id ? "暂无数据文件" : "未选择数据");
  const fileStatus = file?.id
    ? `${fileStatusLabelReadable(file)} · ${fileDetailLabelReadable(file)}`
    : (project?.id ? `${projectFiles.length} 份 EEG 文件` : "选择项目后显示 EEG 数据");
  const prepLabel = preparationStatusLabelReadable(file, plan, epochSet);
  const prepSummary = file?.id
    ? prepLabel
    : (project?.id ? "先选数据，再建立准备方案" : "等待选择项目");
  const nextAction = project?.id
    ? (file?.id ? "进入数据预处理" : "先选数据")
    : "先选项目";
  const nextHint = project?.id
    ? "数据页会在选中项目后展开当前项目的数据。"
    : "先选项目，再展开数据列表。";

  if (projectCardValue) projectCardValue.textContent = projectName;
  if (projectCardNote) projectCardNote.textContent = projectStatus;
  if (dataCardValue) dataCardValue.textContent = fileName;
  if (dataCardNote) dataCardNote.textContent = fileStatus;
  if (prepCardValue) prepCardValue.textContent = prepSummary;
  if (prepCardNote) prepCardNote.textContent = file?.id ? "确认后再进入分析任务" : "选择项目后继续";
  if (nextCardValue) nextCardValue.textContent = nextAction;
  if (nextCardNote) nextCardNote.textContent = nextHint;
}
function setTextIfPresent(selector, text) {
  const node = qs(selector);
  if (node) node.textContent = text;
}

function setBrandKickerMarkup() {
  const node = qs(".entry-kicker");
  if (!node) return;
  node.innerHTML = "全澜脑科学<sup>®</sup> | QuanLan BrainScience<sup>®</sup>";
}

function setAllTextIfPresent(selector, text) {
  qsa(selector).forEach((node) => {
    node.textContent = text;
  });
}

function setValueIfPresent(selector, value) {
  const node = qs(selector);
  if (node) node.value = value;
}

function setButtonTone(button, tone = "ghost") {
  if (!button) return;
  button.classList.toggle("primary-btn", tone === "primary");
  button.classList.toggle("ghost-btn", tone !== "primary");
}

function setNodeHidden(node, hidden) {
  if (!node) return;
  node.hidden = Boolean(hidden);
  node.setAttribute("aria-hidden", hidden ? "true" : "false");
}

function visibleCustomerShellHint(customer = getStoredCustomer()) {
  const org = String(customer?.org || "").trim();
  const email = String(customer?.email || "").trim();
  if (org && email) return `${org} · ${maskEmail(email)}`;
  if (org) return org;
  if (email) return maskEmail(email);
  return "客户账号";
}

function applySinglePrimaryActionGate() {
  if (state.role !== "customer") return;
  const progress = getWorkspaceProgressState();
  const dashboard = qs("#dashboard");
  if (dashboard) {
    const createButton = dashboard.querySelector('[data-real-action="create-project"]');
    const chooseDataButton = dashboard.querySelector('[data-view-jump="storage"]');
    if (createButton) {
      setButtonTone(createButton, progress.hasProject ? "ghost" : "primary");
      const label = createButton.querySelector("span");
      if (label) label.textContent = progress.hasProject ? "新建项目" : "创建或打开项目";
    }
    if (chooseDataButton) {
      setNodeHidden(chooseDataButton, !progress.hasProject);
      setButtonTone(chooseDataButton, progress.hasProject && !progress.hasFile ? "primary" : "ghost");
      const label = chooseDataButton.querySelector("span");
      if (label) label.textContent = progress.hasFile ? "查看数据" : "上传或选择数据";
    }
  }

  const storage = qs("#storage");
  if (storage) {
    const chooseFile = storage.querySelector('[data-file-trigger="real-eeg-file-storage"]');
    const upload = storage.querySelector('[data-real-action="upload-eeg"]');
    const pending = Boolean(qs("#real-eeg-file")?.files?.[0]);
    setButtonTone(chooseFile, progress.hasProject && !pending ? "primary" : "ghost");
    setButtonTone(upload, progress.hasProject && pending ? "primary" : "ghost");
  }

  qsa('[data-real-action="confirm-plan-inline"]').forEach((button) => {
    setNodeHidden(button, Boolean(button.closest('[data-testid="preprocessing-inline-panel"]')));
  });
  qsa('[data-real-action="save-epoch-set"]').forEach((button) => setButtonTone(button, "ghost"));
}

function applyCustomerAccountCopy() {
  if (state.role !== "customer") return;
  const customer = getStoredCustomer();
  const displayName = customer?.name || "客户账号";
  setTextIfPresent("#roleLabel", displayName);
  setTextIfPresent("#balanceSide", "个人中心");
  setTextIfPresent("#accountHint", visibleCustomerShellHint(customer));
  setTextIfPresent("#userCenterName", displayName);
  setTextIfPresent("#userCenterEmail", customer?.email || demoCustomer.email);
  setTextIfPresent("#userCenterOrg", customer?.org || "全澜脑科学");
  setTextIfPresent("#userCenterRole", "客户账号");
}

function applyAdminToneDownCopy() {
  if (state.role !== "admin") return;
  setTextIfPresent("#topEyebrow", "QLanalyser Online · 内部后台");
  setTextIfPresent("#roleLabel", "内部账号");
  setTextIfPresent("#balanceSide", "后台");
  setTextIfPresent("#accountHint", "账号、任务、交付与系统状态");
  const nav = qs(".nav");
  if (nav) nav.setAttribute("aria-label", "QLanalyser 后台导航");
  setTextIfPresent('[data-view="adminOperations"] span', "任务队列");
  setTextIfPresent('[data-view="adminFinance"] span', "结算记录");
  setTextIfPresent('[data-view="journey"] span', "质检");
  setTextIfPresent("#adminDashboard .metric:nth-child(1) span", "项目记录");
  setTextIfPresent("#adminDashboard .metric:nth-child(1) small", "最近项目变更");
  setTextIfPresent("#adminDashboard .panel.span-2 h2", "后台概览");
  setTextIfPresent("#adminDashboard .panel.span-2 .panel-head p", "查看账号、任务、交付与系统状态。");
  setTextIfPresent("#adminDashboard .checklist label:last-child", "交付提醒等待确认。");
  setTextIfPresent("#adminDashboard .work-grid .panel:last-child h2", "最近账号变更");
  setTextIfPresent("#adminOperations h2", "任务队列");
  setTextIfPresent("#adminOperations .panel-head p", "查看上传、预处理、分析、出图和导出任务状态。");
  setTextIfPresent("#adminOperations .table-row.head span:nth-child(2)", "所属账号");
  setTextIfPresent("#adminOperations .table-row.head span:nth-child(4)", "处理");
  setTextIfPresent("#adminFinance h2", "服务记录与开票状态");
  setTextIfPresent("#adminFinance .panel-head p", "查看服务记录、额度变更和开票状态。");
  setTextIfPresent("#adminFinance .table-row.head span:nth-child(1)", "记录");
  setTextIfPresent("#adminFinance .table-row.head span:nth-child(2)", "额度");
  setTextIfPresent("#adminFinance .panel:not(.span-2) h2", "结算摘要");
  setTextIfPresent("#adminSystem .queue-grid div:nth-child(2) span", "队列容量");
  setTextIfPresent("#adminSystem .queue-grid div:nth-child(2) b", "正常");
  setTextIfPresent("#adminSystem .queue-grid div:nth-child(3) strong", "稳定");
  setTextIfPresent("#adminSystem .queue-grid div:nth-child(3) span", "上传服务");
  setTextIfPresent("#adminSystem .queue-grid div:nth-child(3) b", "正常");
}

function applyFinalVisibleCopyGate() {
  const nav = qs(".nav");
  if (nav) nav.setAttribute("aria-label", state.role === "admin" ? "QLanalyser 后台导航" : "QLanalyser 客户业务导航");
  const adminCorner = qs(".admin-corner");
  if (adminCorner) {
    adminCorner.title = "内部入口";
    adminCorner.setAttribute("aria-label", "内部入口");
    const label = adminCorner.querySelector("span");
    if (label) label.textContent = "内部";
  }
  applySinglePrimaryActionGate();
  applyCustomerAccountCopy();
  applyAdminToneDownCopy();
}

const BAD_VISIBLE_COPY_RE = /[?]{2,}|\uFFFD|\u5f85\u5b8c\u5584|\u951f|\u5bc0\u544a|\u5be4\u544a|\u93ba|\u942d|\u6fc2|\u7f01|\u95c1|\u5a34|\u95b8|\u6d94|\u7039|\u9357|\u93c2|\u5bee|\u5bb8|\u8d94|\u7ed4|\u6fa7|\u9a9e|\u5ddf|\u93c9/;

function hasBadVisibleCopy(value) {
  return BAD_VISIBLE_COPY_RE.test(String(value || ""));
}

function cleanRuntimeMessage(message, action = "") {
  const text = String(message || "");
  if (!hasBadVisibleCopy(text)) return text;
  const actionName = String(action || "");
  if (actionName.startsWith("auth:")) return "账号操作已记录，页面已更新。";
  if (actionName.startsWith("billing:")) return "试用服务记录已更新。";
  if (actionName.startsWith("invoice:") || actionName.startsWith("inbox:")) return "开票或交付状态已更新。";
  if (actionName.startsWith("audit:")) return "操作记录已打开。";
  if (actionName.startsWith("help:") || actionName.startsWith("upload:")) return "帮助说明已打开。";
  if (actionName.startsWith("ia:")) return "当前项目或数据操作已记录。";
  return "操作已完成，页面已更新。";
}

function cleanTextNodeFallback(textNode) {
  const parent = textNode.parentElement;
  if (!parent) return "已配置";
  const button = parent.closest("button");
  if (button?.dataset?.view || button?.dataset?.viewJump) return "打开";
  if (button?.dataset?.realAction || button?.dataset?.iaAction) return "执行";
  if (parent.closest(".table-row.head")) return "字段";
  if (parent.closest(".table-row")) return "待系统刷新";
  if (parent.closest(".metric")) return "已配置";
  if (parent.closest(".ia-step-card")) return "步骤";
  if (parent.closest(".segment-summary")) return "当前准备状态已记录。";
  if (["H1", "H2", "H3", "STRONG"].includes(parent.tagName)) return "工作项";
  if (parent.tagName === "SMALL") return "当前状态已记录";
  return "已配置";
}

function sanitizeVisibleCopyTree(root = qs("#appShell") || document.body) {
  if (!root) return;
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode(node) {
      const parent = node.parentElement;
      if (!parent || ["SCRIPT", "STYLE", "TEMPLATE"].includes(parent.tagName)) return NodeFilter.FILTER_REJECT;
      if (!String(node.nodeValue || "").trim()) return NodeFilter.FILTER_REJECT;
      return NodeFilter.FILTER_ACCEPT;
    },
  });
  const badNodes = [];
  while (walker.nextNode()) {
    if (hasBadVisibleCopy(walker.currentNode.nodeValue)) badNodes.push(walker.currentNode);
  }
  badNodes.forEach((node) => {
    node.nodeValue = cleanTextNodeFallback(node);
  });
  qsa("input").forEach((input) => {
    if (hasBadVisibleCopy(input.value)) input.value = input.id === "realProjectName" ? "EEG review project" : "";
    if (hasBadVisibleCopy(input.placeholder)) input.placeholder = "";
  });
  qsa("[title]").forEach((node) => {
    if (hasBadVisibleCopy(node.getAttribute("title"))) node.setAttribute("title", "操作说明");
  });
}

function applyLegacyVisibleCopyCleanup() {
  const navLabels = {
    dashboard: "项目",
    storage: "数据",
    analysis: "准备",
    workflow: "分析",
    statistics: "结果",
    publication: "报告",
    journey: "质检",
    userCenter: "个人中心",
    adminDashboard: "后台总览",
    adminOperations: "任务队列",
    adminFinance: "结算记录",
    adminSystem: "系统状态",
  };
  Object.entries(navLabels).forEach(([view, label]) => setTextIfPresent(`[data-view="${view}"] span`, label));
  const activeView = qs(".view.active")?.id || "dashboard";
  setTextIfPresent("#viewTitle", PRODUCT_VIEW_TITLES[activeView] || titles[activeView] || "QLanalyser Online");
  setTextIfPresent("#logoutBtn span", "退出");
  setTextIfPresent("#roleLabel", state.role === "admin" ? "内部账号" : "个人中心");
  setTextIfPresent("#balanceSide", state.role === "admin" ? "后台" : "个人中心");
  setTextIfPresent("#accountHint", state.role === "admin" ? "账号、任务、交付与系统状态" : visibleCustomerShellHint(getStoredCustomer()));
  setTextIfPresent("#realRuntimeStatus", qs("#realRuntimeStatus")?.textContent?.trim() || "等待创建或选择项目。");
  setTextIfPresent("#realEegFileName", qs("#realEegFileName")?.textContent?.includes("待完善") ? "尚未选择文件" : qs("#realEegFileName")?.textContent || "尚未选择文件");
  setTextIfPresent("#dashboard .metric-grid .metric:nth-child(1) span", "当前项目");
  setTextIfPresent("#dashboard .metric-grid .metric:nth-child(1) small", "选择后显示项目名称与状态");
  setTextIfPresent("#dashboard .metric-grid .metric:nth-child(2) span", "当前数据");
  setTextIfPresent("#dashboard .metric-grid .metric:nth-child(2) small", "选择后显示 EEG 文件与格式");
  setTextIfPresent("#dashboard .metric-grid .metric:nth-child(3) span", "准备状态");
  setTextIfPresent("#dashboard .metric-grid .metric:nth-child(3) small", "确认后进入分析任务");
  setTextIfPresent("#dashboard .metric-grid .metric:nth-child(4) span", "下一步");
  setTextIfPresent("#dashboard .metric-grid .metric:nth-child(4) strong", "先选项目");
  setTextIfPresent("#dashboard .metric-grid .metric:nth-child(4) small", "先选项目，再展开数据列表");
  setTextIfPresent("#topEyebrow", state.role === "admin" ? "QLanalyser Online · 内部后台" : "QLanalyser Online · EEG 科研数据到复核记录");
  const customer = getStoredCustomer();
  setTextIfPresent("#userCenterName", customer.name || "客户账号");
  setTextIfPresent("#userCenterEmail", customer.email || "demo.customer@quanlan.cn");
  setTextIfPresent("#userCenterOrg", customer.org || "全澜脑科学");
  setTextIfPresent("#userCenterBalance", "试用中");
  const textPairs = [
    ['[data-testid="project-crud-panel"] h2', "第 1 步：创建或打开项目"],
    ['[data-testid="project-crud-panel"] .panel-head p', "项目会保存本次分析的数据、准备记录、任务、结果和报告。"],
    ['[data-testid="project-data-crud-panel"] h2', "\u9879\u76ee\u5185\u6570\u636e"],
    ['[data-testid="project-data-crud-panel"] .panel-head p', "\u6253\u5f00\u9879\u76ee\u540e\uff0c\u5728\u8fd9\u91cc\u67e5\u770b\u6570\u636e\u6982\u51b5\u548c\u4e0b\u4e00\u6b65\u5165\u53e3\uff1b\u4e0a\u4f20\u548c\u6587\u4ef6\u6574\u7406\u8bf7\u8fdb\u5165\u201c\u6570\u636e\u201d\u3002"],
    ['[data-testid="ia-page-boundary-note"] h2', "\u9875\u9762\u8fb9\u754c"],
    ['[data-testid="ia-page-boundary-note"] .panel-head p', "项目页只负责打开项目；数据、准备、分析和报告按主流程推进。"],
    ['[data-testid="data-preparation-workbench"] h2', "检查 EEG 数据"],
    ['[data-testid="data-preparation-workbench"] .panel-head p', "先看波形和基础质量，再确认准备方案。"],
    ['[data-testid="single-file-preview-panel"] h2', "\u5355\u6587\u4ef6\u9884\u89c8\u4e0e\u4fee\u8ba2"],
    ['[data-testid="segment-tag-editor-panel"] h2', "\u5f53\u524d\u4fee\u6539\u8bb0\u5f55"],
    ['[data-testid="segment-tag-editor-panel"] .panel-head p', "\u7247\u6bb5\u5254\u9664\u3001\u6062\u590d\u3001\u6807\u7b7e\u548c\u574f\u9053\u4fee\u6539\u4f1a\u5148\u8bb0\u5728\u8fd9\u91cc\uff0c\u4fdd\u5b58\u524d\u4e0d\u7834\u574f\u539f\u59cb\u6570\u636e\u3002"],
    ['[data-testid="preprocessing-readiness-panel"] h2', "\u6570\u636e\u51c6\u5907\u68c0\u67e5"],
    ['[data-testid="preprocessing-readiness-panel"] .panel-head p', "\u67e5\u770b\u6570\u636e\u6982\u51b5\u3001\u786e\u8ba4\u51c6\u5907\u65b9\u6848\uff0c\u5e76\u4fdd\u5b58\u6216\u6062\u590d\u574f\u9053\u4fee\u6539\u3002"],
    ['[data-testid="event-epoch-panel"] h2', "\u4e8b\u4ef6\u4e0e\u7247\u6bb5\u4fdd\u5b58"],
    ['[data-testid="event-epoch-panel"] .panel-head p', "\u4fdd\u5b58 ERP/P300 \u4e8b\u4ef6\u6620\u5c04\u3001\u5206\u6bb5\u7a97\u53e3\u3001\u57fa\u7ebf\u548c\u5254\u9664\u8bb0\u5f55\u3002"],
    ['[data-testid="data-preparation-submit-last"] h2', "\u786e\u8ba4\u6570\u636e\u51c6\u5907\u540e\u518d\u63d0\u4ea4"],
    ['[data-testid="data-preparation-submit-last"] .panel-head p', "确认数据准备方案、事件分段和质控记录后，再进入分析任务。"],
    ['[data-testid="analysis-task-workbench"] h2', "选择分析方法"],
    ['[data-testid="analysis-task-workbench"] .panel-head p', "根据当前数据和准备状态，选择可以运行的分析任务。"],
    ['[data-testid="analysis-task-submit-and-report"] h2', "运行分析"],
  ];
  textPairs.forEach(([selector, text]) => setTextIfPresent(selector, text));
  const labels = [
    ['label:has(#workspaceProjectSelect) span', "\u9009\u62e9\u9879\u76ee"],
    ['label:has(#workspaceFileSelect) span', "\u9009\u62e9\u6570\u636e"],
    ['label:has(#workspaceFileFocusSelect) span', "\u5f53\u524d\u6570\u636e"],
    ['label:has(#workspacePlanSelect) span', "\u51c6\u5907\u65b9\u6848"],
    ['label:has(#eegWindowInput) span', "\u7a97\u53e3\u957f\u5ea6 s"],
    ['label:has(#eegChannelInput) span', "\u663e\u793a\u901a\u9053"],
    ['label:has(#eegGainInput) span', "\u589e\u76ca"],
    ['label:has(#presetPrepReference) span', "\u53c2\u8003\u65b9\u5f0f"],
    ['label:has(#presetPrepNotch) span', "\u9677\u6ce2 Hz"],
    ['label:has(#presetPrepLfreq) span', "\u4f4e\u5207 Hz"],
    ['label:has(#presetPrepHfreq) span', "\u9ad8\u5207 Hz"],
    ['label:has(#subjectsInput) span', "\u88ab\u8bd5\u6570"],
    ['label:has(#hoursInput) span', "\u8bb0\u5f55\u65f6\u957f"],
    ['label:has(#realReportTitle) span', "\u62a5\u544a\u6807\u9898"],
  ];
  labels.forEach(([selector, text]) => setTextIfPresent(selector, text));
  const buttons = [
    ['[data-real-action="create-project"] span', "\u521b\u5efa\u9879\u76ee"],
    ['[data-ia-action="edit-project"] span', "\u7f16\u8f91"],
    ['[data-ia-action="archive-project"] span', "\u5f52\u6863"],
    ['[data-ia-action="delete-project"] span', "\u5220\u9664"],
    ['[data-real-action="upload-eeg"] span', "\u4e0a\u4f20\u5230\u5f53\u524d\u9879\u76ee"],
    ['[data-ia-action="rename-data"] span', "\u91cd\u547d\u540d / \u5907\u6ce8"],
    ['[data-real-action="run-qc-preview-inline"] span', "更新波形"],
    ['[data-real-action="run-metadata-qc-inline"] span', "\u67e5\u770b\u6570\u636e\u6982\u51b5"],
    ['[data-real-action="save-bad-channel-audit"] span', "\u4fdd\u5b58\u574f\u9053\u4fee\u6539"],
    ['[data-real-action="discard-bad-channel-audit"] span', "\u6062\u590d\u574f\u9053\u4fee\u6539"],
    ['[data-real-action="save-epoch-set"] span', "\u4fdd\u5b58\u4e8b\u4ef6\u4e0e\u7247\u6bb5"],
    ['[data-real-action="download-epoch-record"] span', "\u4e0b\u8f7d\u6570\u636e\u51c6\u5907\u8bb0\u5f55"],
    ['[data-real-action="confirm-plan-inline"] span', "\u786e\u8ba4\u6570\u636e\u51c6\u5907"],
    ['[data-real-action="download-plan-json"] span', "\u4e0b\u8f7d\u5904\u7406\u8bb0\u5f55"],
    ['[data-real-action="create-report"] span', "生成复核记录"],
    ['[data-real-action="run-psd"] span', "开始 PSD 分析"],
    ['[data-real-action="run-erp"] span', "开始 ERP 分析"],
    ['[data-real-action="run-tfr"] span', "开始 TFR 时频分析"],
    ['[data-real-action="run-multitaper-psd"] span', "开始 Multitaper PSD"],
    ['[data-real-action="run-multitaper-tfr"] span', "开始 Multitaper TFR"],
    ['[data-real-action="run-reference-csd"] span', "开始 CSD 电流源密度计算"],
    ['[data-real-action="run-pac"] span', "开始 PAC 耦合分析"],
    ['[data-real-action="run-connectivity"] span', "开始 Connectivity 连接性分析"],
    ['[data-ia-action="select-prep-data"] span', "\u9009\u62e9\u5e76\u9884\u89c8"],
    ['[data-view-jump="statistics"] span', "查看结果"],
    ['[data-view-jump="publication"] span', "下载报告"],
    ["#submitBtn span", "\u63d0\u4ea4\u5206\u6790"],
  ];
  buttons.forEach(([selector, text]) => setTextIfPresent(selector, text));
  setTextIfPresent('[data-real-action="run-metadata-qc-inline"] span', "检查数据基础信息");
  setAllTextIfPresent('[data-view-jump="statistics"] span', "\u67e5\u770b\u7ed3\u679c");
  setAllTextIfPresent('[data-view-jump="publication"] span', "\u4e0b\u8f7d\u62a5\u544a");
  setTextIfPresent('[data-testid="prep-no-upload-boundary"] span', "\u672a\u9009\u62e9\u9879\u76ee\u6216\u6570\u636e\u65f6\uff0c\u53ea\u663e\u793a\u9879\u76ee\u7ea7\u4fe1\u606f\u3002");
  setValueIfPresent("#realReportTitle", "\u5355\u8bb0\u5f55 EEG \u5206\u6790\u62a5\u544a");
  setTextIfPresent("label:has(#hoursInput) em", "h");
  setTextIfPresent('[data-testid="analysis-task-submit-and-report"] .cost-card span', "\u8bb0\u5f55\u65f6\u957f\u9884\u4f30");
  setTextIfPresent("#totalHours + small", "\u7528\u4e8e\u4f30\u7b97\u6c99\u76d2\u8d39\u7528\uff0c\u4e0d\u4ea7\u751f\u771f\u5b9e\u8d44\u91d1\u53d8\u52a8\u3002");
  setTextIfPresent("#analysisCost", "-");
  setTextIfPresent("#totalCost", "-");
  const analysisCostRow = qs("#analysisCost")?.closest?.(".cost-row");
  const totalCostRow = qs("#totalCost")?.closest?.(".cost-row");
  if (analysisCostRow?.querySelector("span")) analysisCostRow.querySelector("span").textContent = "\u6c99\u76d2\u9884\u4f30\u8d39\u7528";
  if (totalCostRow?.querySelector("span")) totalCostRow.querySelector("span").textContent = "\u62a5\u544a\u5305\u72b6\u6001";
  const prepSteps = [
    ["\u9009\u62e9\u6570\u636e", "\u786e\u8ba4\u5f53\u524d\u9879\u76ee\u4e0b\u7684 EEG \u6587\u4ef6"],
    ["\u9884\u89c8\u6ce2\u5f62", "\u67e5\u770b\u7a97\u53e3\u3001\u901a\u9053\u548c\u589e\u76ca"],
    ["\u7f16\u8f91\u7247\u6bb5", "\u5220\u9664\u6216\u6062\u590d\u6570\u636e\u6bb5\u5e76\u8bb0\u5f55\u6807\u7b7e"],
    ["\u6570\u636e\u8d28\u91cf\u68c0\u67e5", "\u68c0\u67e5\u574f\u9053\u3001\u6ee4\u6ce2\u548c\u63d0\u9192"],
    ["\u786e\u8ba4\u4fee\u8ba2", "\u751f\u6210\u4fee\u8ba2\u7248\u672c\u3001\u6765\u6e90\u8bb0\u5f55\u548c\u5904\u7406\u8bb0\u5f55"],
  ];
  qsa(".ia-step-card").forEach((card, index) => {
    const copy = prepSteps[index] || ["\u6b65\u9aa4", "\u5df2\u8bb0\u5f55"];
    const strong = card.querySelector("strong");
    const span = card.querySelector("span");
    if (strong) strong.textContent = copy[0];
    if (span) span.textContent = copy[1];
  });
  const timeLabels = qsa("#timeSegmentFields label span");
  ["\u8d77\u59cb s", "\u7ed3\u675f s", "\u6b65\u957f s"].forEach((text, index) => {
    if (timeLabels[index]) timeLabels[index].textContent = text;
  });
  const eventLabels = qsa("#eventSegmentFields label span");
  ["\u4e8b\u4ef6\u7c7b\u578b", "\u4e8b\u524d s", "\u4e8b\u540e s", "\u4e8b\u4ef6\u6570"].forEach((text, index) => {
    if (eventLabels[index]) eventLabels[index].textContent = text;
  });
  const editCards = [
    ["\u5220\u9664\u7247\u6bb5", "\u6392\u9664\u5f53\u524d\u9009\u4e2d\u7684\u6570\u636e\u6bb5", "\u5220\u9664"],
    ["\u6062\u590d\u7247\u6bb5", "\u6062\u590d\u4e0a\u4e00\u6b21\u6392\u9664\u7684\u6570\u636e\u6bb5", "\u6062\u590d"],
    ["\u6dfb\u52a0\u6807\u7b7e", "\u6807\u7b7e\uff1a\u8fd0\u52a8\u4f2a\u8ff9 / \u9700\u8981\u590d\u6838", "\u6dfb\u52a0"],
    ["\u7f16\u8f91\u6807\u7b7e", "\u8bb0\u5f55 before/after \u4fee\u8ba2", "\u7f16\u8f91"],
    ["恢复标签", "恢复最近一次标签修改", "恢复"],
  ];
  qsa(".ia-edit-card").forEach((card, index) => {
    const copy = editCards[index] || ["\u7f16\u8f91", "\u5df2\u8bb0\u5f55", "\u6267\u884c"];
    const strong = card.querySelector("strong");
    const span = card.querySelector("span");
    const button = card.querySelector("button");
    if (strong) strong.textContent = copy[0];
    if (span) span.textContent = copy[1];
    if (button) button.textContent = copy[2];
  });
  setTextIfPresent("#segmentSummary", hasBadVisibleCopy(qs("#segmentSummary")?.textContent) ? "\u5f53\u524d\u6570\u636e\u6bb5\u548c\u6807\u7b7e\u4fee\u8ba2\u5df2\u8bb0\u5f55\u3002" : qs("#segmentSummary")?.textContent || "\u5f53\u524d\u6570\u636e\u6bb5\u548c\u6807\u7b7e\u4fee\u8ba2\u5df2\u8bb0\u5f55\u3002");
  const methodCopy = {
    qc: ["准备与数据质量", "在分析前查看数据概况、基础质量提示、预览和准备记录。"],
    preprocessing_readiness: ["准备与数据质量", "在分析前查看数据概况、基础质量提示、预览和准备记录。"],
    psd: ["PSD 频谱与频段功率", "输出频谱、频段功率和通道级表格，适合查看主要频段分布。"],
    psd_bandpower: ["PSD 频谱与频段功率", "输出频谱、频段功率和通道级表格，适合查看主要频段分布。"],
    erp: ["ERP 事件相关电位", "基于事件分段输出波形、指标和剔除记录，适合事件相关分析。"],
    erp_p300: ["ERP 事件相关电位", "基于事件分段输出波形、指标和剔除记录，适合事件相关分析。"],
    tfr: ["TFR 时频分析", "查看事件前后的时频功率和相位一致性，并记录频率范围与基线设置。"],
    pac: ["PAC 相位-振幅耦合", "查看相位-振幅耦合的描述性图表和表格，不能单独解释为因果机制。"],
    pac_cfc: ["PAC 相位-振幅耦合", "查看相位-振幅耦合的描述性图表和表格，不能单独解释为因果机制。"],
    multitaper_psd: ["Multitaper PSD", "使用多窗谱估计查看频谱功率，适合对频谱结果做参数化比较。"],
    multitaper_tfr: ["Multitaper TFR", "查看事件锁定的多窗时频结果，并记录事件、基线和窗参数。"],
    reference_csd: ["CSD 电流源密度计算", "基于通道位置信息计算头皮电位空间分布变化；这是传感器空间滤波，不是源定位或诊断。"],
    connectivity: ["Connectivity 连接性分析", "查看连接性矩阵和边表，结果用于研究参考，不证明信息流或因果方向。"],
    source_localization_boundary: ["Source boundary", "边界检查：无 source model / inverse evidence 不得写精确脑区定位。"],
  };
  qsa(".ia-method-card").forEach((card) => {
    const copy = methodCopy[card.dataset.moduleId];
    if (!copy) return;
    const strong = card.querySelector("strong");
    const span = card.querySelector("span");
    if (strong) strong.textContent = copy[0];
    if (span) span.textContent = copy[1];
  });
  setAllTextIfPresent(".ia-section-title strong", "\u6570\u636e\u961f\u5217");
  setAllTextIfPresent(".ia-section-title span", "\u9010\u4e2a\u6570\u636e\u8fdb\u884c\u9884\u89c8\u548c\u9884\u5904\u7406");
  const loginCopy = [
    [".admin-corner span", "\u5185\u90e8"],
    [".login-brand .cover-copy h1", "\u7814\u7a76\u7ea7\u8111\u7535\u5206\u6790\u5e73\u53f0"],
    [".login-brand .cover-copy p", "\u6e05\u6670\u3001\u53ef\u590d\u73b0\u7684\u8111\u7535\u5206\u6790\u5de5\u4f5c\u533a\u3002"],
    [".account-title span", "QLanalyser Online"],
    [".account-title strong", "\u767b\u5f55"],
    [".account-title small", ""],
    ['[data-login-tab="customerLogin"]', "\u767b\u5f55"],
    ['[data-login-tab="customerRegister"]', "\u8d26\u53f7\u5f00\u901a"],
    ['label:has(#customerEmail) span', "\u90ae\u7bb1 / \u624b\u673a\u53f7"],
    ['label:has(#customerPassword) span', "\u5bc6\u7801"],
    ["#customerLoginBtn span", "\u767b\u5f55\u5e76\u8fdb\u5165\u9879\u76ee"],
    ['[data-lab-link="module-lab"] span', "\u67e5\u770b\u65b9\u6cd5\u5e93"],
    ["#forgotPasswordBtn", "\u627e\u56de\u8d26\u53f7"],
    ["#rememberCustomer", ""],
  ];
  loginCopy.forEach(([selector, text]) => {
    if (selector === "#rememberCustomer") {
      const label = qs(selector)?.closest("label");
      if (label) {
        const input = label.querySelector("input");
        label.textContent = "";
        if (input) label.append(input);
        label.append(" \u8bb0\u4f4f\u767b\u5f55\u72b6\u6001");
      }
      return;
    }
    setTextIfPresent(selector, text);
  });
  const emailInput = qs("#customerEmail");
  const passwordInput = qs("#customerPassword");
  if (emailInput) emailInput.placeholder = "\u8f93\u5165\u5df2\u6ce8\u518c\u90ae\u7bb1\u6216\u4f53\u9a8c\u624b\u673a\u53f7";
  if (passwordInput) passwordInput.placeholder = "\u8bf7\u8f93\u5165\u8d26\u6237\u5bc6\u7801";
  qsa("#realResultReview [data-result-module]").forEach((item) => {
    const moduleName = String(item.dataset.resultModule || "");
    const task = state.real.tasks?.[moduleName] || null;
    const strong = item.querySelector("strong");
    if (strong && moduleName) {
      strong.textContent = `${moduleDisplayName(moduleName)}：${task?.status === "completed" ? "已完成" : task?.status || "运行中"}`;
    }
    const actions = item.querySelector(".real-actions");
    if (actions && !actions.querySelector("a,button")) actions.textContent = "\u7ed3\u679c\u6587\u4ef6\u751f\u6210\u4e2d\u6216\u6682\u65e0\u53ef\u4e0b\u8f7d\u5ba1\u8ba1\u4ea7\u7269\u3002";
  });
  applyResultSurfaceCopy();
  renderEegPreviewEmptyState();
  sanitizeVisibleCopyTree();
}

const PRODUCT_NAV_LABELS = {
  dashboard: "项目",
  storage: "数据",
  analysis: "准备",
  workflow: "分析",
  statistics: "结果",
  publication: "报告",
  journey: "质检",
  billing: "服务记录",
  invoice: "发票申请",
  inbox: "发票箱",
  userCenter: "个人中心",
  adminDashboard: "后台总览",
  adminOperations: "任务队列",
  adminFinance: "结算记录",
  adminSystem: "系统状态",
};

const PRODUCT_VIEW_TITLES = {
  dashboard: "第 1 步：创建或打开项目",
  storage: "上传或选择 EEG 数据",
  analysis: "检查 EEG 数据",
  workflow: "选择分析方法",
  epilepsyWorkbenchInline: "癫痫样候选事件复核预览",
  statistics: "查看分析结果",
  publication: "生成和下载复核记录",
  journey: "交付质检",
  billing: "服务记录",
  invoice: "发票申请",
  inbox: "发票箱",
  userCenter: "个人中心",
  adminDashboard: "后台总览",
  adminOperations: "任务队列",
  adminFinance: "结算记录",
  adminSystem: "系统状态",
};

function productStatusText(value, fallback = "进行中") {
  const raw = String(value || "").toLowerCase();
  const map = {
    active: "进行中",
    created: "未开始",
    ready: "可分析",
    processing: "处理中",
    completed: "已完成",
    提醒: "有提醒",
    error: "需处理",
    failed: "需处理",
    blocked: "暂不可用",
    disabled: "暂不可用",
    archived: "已归档",
    archive: "已归档",
    deleted: "已删除",
    delete: "已删除",
  };
  return map[raw] || fallback;
}

function formatProjectUpdated(project) {
  const raw = project?.updated_at || project?.created_at || "";
  const date = raw ? new Date(raw) : null;
  if (!date || Number.isNaN(date.getTime())) return "暂无记录";
  const yyyy = date.getFullYear();
  const mm = String(date.getMonth() + 1).padStart(2, "0");
  const dd = String(date.getDate()).padStart(2, "0");
  const hh = String(date.getHours()).padStart(2, "0");
  const mi = String(date.getMinutes()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd} ${hh}:${mi}`;
}

function projectStatusLabel(project, files = []) {
  if (!project?.id) return "未选择项目";
  const count = projectFileCount(project, files);
  const base = productStatusText(project.status, count > 0 ? "可分析" : "待上传数据");
  return count > 0 && base === "进行中" ? "已有数据" : base;
}

function fileStatusLabel(file) {
  if (!file?.id) return "未选择数据";
  const raw = String(file.status || file.data_status || "").toLowerCase();
  const map = {
    uploaded: "已上传",
    previewed: "已预览",
    prepared: "已准备",
    needs_attention: "需处理",
    invalid: "不可用",
    archived: "已归档",
    deleted: "已删除",
    blocked: "暂不可用",
  };
  return map[raw] || "等待预览";
}

function fileDetailLabel(file) {
  if (!file?.id) return "请选择数据";
  const pieces = [
    file.detected_format || file.format || "EEG",
    file.channel_count ?? file.ch_count ? `${file.channel_count ?? file.ch_count} 通道` : null,
    file.sampling_rate ?? file.sample_rate ? `${file.sampling_rate ?? file.sample_rate} Hz` : null,
  ].filter(Boolean);
  return pieces.join(" · ") || "EEG 数据文件";
}

function preparationStatusLabel(file, plan, epochSet) {
  if (!file?.id) return "请先选择数据";
  if (epochSet?.id) {
    const 修订版本 = epochSet.revision ?? epochSet.data_preparation_revision ?? plan?.revision ?? 1;
    return `已确认 · 修订版本 ${修订版本}`;
  }
  if (plan?.id) {
    const 修订版本 = plan.revision ?? plan.data_preparation_revision ?? 1;
    return `待确认 · 修订版本 ${修订版本}`;
  }
  return "尚未确认准备方案";
}

function projectStatusLabelReadable(project, files = []) {
  return projectStatusLabel(project, files);
}

function fileStatusLabelReadable(file) {
  return fileStatusLabel(file);
}

function fileDetailLabelReadable(file) {
  return fileDetailLabel(file);
}

function preparationStatusLabelReadable(file, plan, epochSet) {
  return preparationStatusLabel(file, plan, epochSet);
}

function selectedStateLabel(project, file, plan, epochSet) {
  if (!project?.id) return "请先从左侧项目列表打开一个项目。";
  if (!file?.id) return `当前项目：${projectDisplayName(project) || project.id}；请上传或选择一个 EEG 数据文件。`;
  return `当前项目：${projectDisplayName(project) || project.id}；当前数据：${eegFileDisplayName(file)}；${preparationStatusLabel(file, plan, epochSet)}。`;
}

function selectedStateLabelReadable(project, file, plan, epochSet) {
  return selectedStateLabel(project, file, plan, epochSet);
}

function currentWorkspaceContext() {
  const projects = state.workspace.projects || [];
  const files = state.workspace.files || [];
  const plans = state.workspace.plans || [];
  const epochSets = state.workspace.epochSets || [];
  const selectedProjectId = state.workspace.selectedProjectId || null;
  const selectedProjectCandidate = selectedProjectId
    ? projects.find((item) => item.id === selectedProjectId) || (state.real.project?.id === selectedProjectId ? state.real.project : null)
    : null;
  const project = selectedProjectCandidate && (state.workspace.showReviewProjects || !isHiddenFromCustomerProjectList(selectedProjectCandidate))
    ? selectedProjectCandidate
    : null;
  const projectFiles = scopedProjectFiles(project, files);
  const selectedFileId = project?.id ? state.workspace.selectedFileId || null : null;
  const file = project?.id
    ? (selectedFileId ? projectFiles.find((item) => item.id === selectedFileId) : null)
      || (state.real.eegFile?.project_id === project.id ? state.real.eegFile : null)
    : null;
  const plan = file
    ? plans.find((item) => item.input_file_id === file.id) || (state.real.plan?.input_file_id === file.id ? state.real.plan : null)
    : null;
  const epochSet = file
    ? epochSets.find((item) => item.input_file_id === file.id) || (state.real.epochSet?.input_file_id === file.id ? state.real.epochSet : null)
    : null;
  return { projects, files, plans, epochSets, project, projectFiles, file, plan, epochSet };
}

function preparationRecordLabel(plan, epochSet) {
  const record = epochSet || plan;
  if (!record?.id) return "待生成数据准备记录";
  const revision = record.revision ?? record.data_preparation_revision ?? 1;
  return `准备记录第 ${revision} 版`;
}

function renderStorageManagement() {
  const storage = qs("#storage");
  if (!storage) return;
  const { project, projectFiles, file, plans, epochSets, plan, epochSet } = currentWorkspaceContext();
  const contextBar = qs("#storageContextBar");
  const projectHint = qs("#storageProjectHint");
  const fileRows = qs("#storageFileRows");
  const fileDetail = qs("#storageFileDetail");
  const uploadButtons = qsa('[data-file-trigger="real-eeg-file-storage"], #storage [data-real-action="upload-eeg"]');
  const hasProject = Boolean(project?.id);
  const hasFile = Boolean(file?.id);
  const projectName = hasProject ? (projectDisplayName(project) || project.id) : "未打开项目";
  const selectedPrep = preparationRecordLabel(plan, epochSet);
  storage.classList.toggle("storage-no-project", !hasProject);
  storage.classList.toggle("storage-no-data", hasProject && !projectFiles.length);
  storage.classList.toggle("storage-has-data", hasProject && Boolean(projectFiles.length));

  if (contextBar) {
    contextBar.innerHTML = `
      <div><span>当前项目</span><strong>${escapeHtml(projectName)}</strong></div>
      <div><span>数据文件</span><strong>${hasProject ? `${projectFiles.length} 个` : "待选择项目"}</strong></div>
      <div><span>当前数据</span><strong>${hasFile ? escapeHtml(eegFileDisplayName(file) || file.id) : "未选择数据"}</strong></div>
      <div><span>下一步</span><strong>${hasProject ? (projectFiles.length ? "选择数据并进入准备" : "上传 EEG 数据") : "打开项目"}</strong></div>
    `;
  }
  if (projectHint) {
    projectHint.textContent = hasProject
      ? `当前项目：${projectName}。数据文件随项目留痕。`
      : "请先到项目页打开一个项目，再选择 EEG 数据。";
  }
  uploadButtons.forEach((button) => {
    button.disabled = !hasProject;
    button.title = hasProject ? "上传到当前项目" : "请先打开项目";
    button.hidden = !hasProject;
    button.setAttribute("aria-hidden", hasProject ? "false" : "true");
  });

  if (fileRows) {
    if (!hasProject) {
      fileRows.innerHTML = `
        <div class="storage-empty-state">
          <strong>第 1 步还没完成：请先创建或打开项目</strong>
          <span>项目会保存本次 EEG 分析的数据、准备方案、任务、结果和报告。</span>
          <button class="primary-btn mini" type="button" data-view-jump="dashboard">创建或打开项目</button>
        </div>
      `;
    } else if (!projectFiles.length) {
      fileRows.innerHTML = `
        <div class="storage-empty-state">
          <strong>当前项目还没有数据</strong>
          <span>上传 EDF、BDF、SET、VHDR、CNT 或 FIF 文件后，可继续预览和预处理。</span>
          <button class="primary-btn mini" type="button" data-file-trigger="real-eeg-file-storage-empty" onclick="document.getElementById('real-eeg-file').click()">选择 EEG 文件</button>
        </div>
      `;
    } else {
      const rows = projectFiles.slice(0, 24).map((item) => {
        const rowPrep = epochSets.find((epoch) => epoch.input_file_id === item.id)
          || plans.find((candidate) => candidate.input_file_id === item.id)
          || null;
        const selected = item.id === file?.id;
        const actionLabel = selected ? "当前数据" : "选择数据";
        const displayName = eegFileDisplayName(item) || "EEG 数据文件";
        const originalName = String(item.original_filename || item.id || "").trim();
        const secondaryName = originalName && originalName !== displayName ? originalName : "";
        return `
          <button class="table-row storage-file-row${selected ? " selected" : ""}" type="button" data-file-select="${escapeHtml(item.id)}" data-jump-to-analysis="1" data-ia-action="select-prep-data" aria-current="${selected ? "true" : "false"}" title="${escapeHtml(displayName)}">
            <span><strong>${escapeHtml(displayName)}</strong>${secondaryName ? `<small>${escapeHtml(secondaryName)}</small>` : ""}</span>
            <span>${escapeHtml(fileDetailLabel(item))}</span>
            <span><mark class="status-chip">${escapeHtml(rowPrep ? preparationRecordLabel(rowPrep, rowPrep) : fileStatusLabel(item))}</mark></span>
            <span class="row-action">${actionLabel}</span>
          </button>
        `;
      }).join("");
      fileRows.innerHTML = `
        <div class="table-row head storage-file-row-head"><span>数据文件</span><span>文件信息</span><span>当前状态</span><span>下一步</span></div>
        ${rows}
      `;
    }
  }

  if (fileDetail) {
    if (!hasProject) {
      fileDetail.hidden = true;
      fileDetail.setAttribute("aria-hidden", "true");
    } else if (!hasFile) {
      fileDetail.hidden = false;
      fileDetail.setAttribute("aria-hidden", "false");
      fileDetail.innerHTML = `
        <strong>${escapeHtml(projectName)}</strong>
        <p>${projectFiles.length ? "请从左侧选择一份数据文件。" : "当前项目还没有数据文件。"}</p>
        <div class="storage-detail-list">
          <span><b>数据文件：</b>${projectFiles.length} 个</span>
          <span><b>下一步：</b>${projectFiles.length ? "选择数据并预览" : "上传 EEG 数据"}</span>
        </div>
      `;
    } else {
      fileDetail.hidden = false;
      fileDetail.setAttribute("aria-hidden", "false");
      fileDetail.innerHTML = `
        <strong>${escapeHtml(eegFileDisplayName(file) || file.id)}</strong>
        <p>${escapeHtml(fileDetailLabel(file))}</p>
        <div class="storage-detail-list">
          <span><b>所属项目：</b>${escapeHtml(projectName)}</span>
          <span><b>文件状态：</b>${escapeHtml(fileStatusLabel(file))}</span>
          <span><b>准备记录：</b>${escapeHtml(selectedPrep)}</span>
        </div>
        <div class="real-actions compact-actions">
          <button class="primary-btn" type="button" data-view-jump="analysis"><i data-lucide="sliders-horizontal"></i><span>检查 EEG 数据</span></button>
          <button class="ghost-btn" type="button" data-ia-action="rename-data"><i data-lucide="tag"></i><span>编辑名称 / 备注</span></button>
        </div>
      `;
    }
  }
  if (window.lucide) lucide.createIcons();
  applyCustomerTrialStorageSurfaceCleanup();
}

function applyCustomerTrialStorageSurfaceCleanup() {
  const customerSurface = isCustomerTrialP0Mode();
  const teachingSurface = customerSurface && state.teaching.active;
  const storage = qs("#storage");
  if (storage) {
    storage.classList.toggle("customer-storage-surface", customerSurface);
    storage.classList.toggle("teaching-customer-storage-surface", teachingSurface);
  }
  if (!customerSurface) return;

  const { project, file } = currentWorkspaceContext();
  const hasProject = Boolean(project?.id);
  const hasFile = Boolean(file?.id || state.real.eegFile?.id);
  const hideInTeaching = [
    "#storage .storage-toolbar-actions",
    "#storage .storage-upload-authorization",
    "#storage [data-file-trigger=\"real-eeg-file-storage\"]",
    "#storage [data-file-trigger=\"real-eeg-file-storage-empty\"]",
    "#storage [data-real-action=\"upload-eeg\"]",
    "#storage [data-ia-action=\"rename-data\"]",
    "#storage [data-ia-action=\"replace-data\"]",
    "#storage [data-ia-action=\"delete-data\"]",
    "#storage [data-ia-action=\"archive-data\"]",
  ].join(", ");
  setSurfaceHiddenForCustomer(hideInTeaching, teachingSurface);

  const projectHint = qs("#storageProjectHint");
  if (projectHint && teachingSurface) {
    projectHint.textContent = hasFile
      ? "\u793a\u4f8b\u6570\u636e\u5df2\u8f7d\u5165\uff0c\u53ef\u76f4\u63a5\u8fdb\u5165\u6570\u636e\u51c6\u5907\u3002"
      : "\u793a\u4f8b\u9879\u76ee\u5df2\u6253\u5f00\uff0c\u6b63\u5728\u7b49\u5f85\u793a\u4f8b\u6570\u636e\u3002";
  }

  const detail = qs("#storageFileDetail");
  if (detail && teachingSurface && hasFile && !detail.querySelector("[data-testid='teaching-storage-next-step']")) {
    const next = document.createElement("div");
    next.className = "real-actions compact-actions";
    next.dataset.testid = "teaching-storage-next-step";
    next.innerHTML = `
      <button class="primary-btn" type="button" data-view-jump="analysis"><i data-lucide="sliders-horizontal"></i><span>\u8fdb\u5165\u6570\u636e\u51c6\u5907</span></button>
      <span class="customer-note">\u793a\u4f8b\u6570\u636e\u53ea\u8bfb\uff0c\u4e0a\u4f20\u548c\u7f16\u8f91\u5df2\u6536\u8d77\u3002</span>
    `;
    detail.appendChild(next);
  }
  if (detail && teachingSurface && !hasFile && hasProject) {
    detail.innerHTML = `
      <strong>\u793a\u4f8b\u6570\u636e</strong>
      <p>\u793a\u4f8b\u9879\u76ee\u5df2\u6253\u5f00\uff0c\u7cfb\u7edf\u6b63\u5728\u8f7d\u5165\u53ef\u4f53\u9a8c\u7684 EEG \u6570\u636e\u3002</p>
    `;
  }
  if (window.lucide) lucide.createIcons();
}

function renderProjectDataManagement() {
  const projects = state.workspace.projects || [];
  const files = state.workspace.files || [];
  const plans = state.workspace.plans || [];
  const epochSets = state.workspace.epochSets || [];
  const selectedProjectId = state.workspace.selectedProjectId || null;
  const project = selectedProjectId
    ? projects.find((item) => item.id === selectedProjectId) || (state.real.project?.id === selectedProjectId ? state.real.project : null)
    : null;
  const projectFiles = scopedProjectFiles(project, files);
  const selectedFileId = project?.id ? state.workspace.selectedFileId || null : null;
  const file = project?.id
    ? (selectedFileId ? projectFiles.find((item) => item.id === selectedFileId) : null)
      || (state.real.eegFile?.project_id === project.id ? state.real.eegFile : null)
    : null;
  const plan = file
    ? plans.find((item) => item.input_file_id === file.id) || (state.real.plan?.input_file_id === file.id ? state.real.plan : null)
    : null;
  const epochSet = file
    ? epochSets.find((item) => item.input_file_id === file.id) || (state.real.epochSet?.input_file_id === file.id ? state.real.epochSet : null)
    : null;
  const visibleProjects = filteredWorkspaceProjects(projects, files);
  const projectSearch = qs("#workspaceProjectSearch");
  const projectSelect = qs("#workspaceProjectSelect");
  const showReviewProjects = qs("#workspaceShowReviewProjects");
  const projectFilterSummary = qs("#workspaceProjectFilterSummary");
  const projectRows = qs("#iaProjectRows");
  const projectRowActions = qs('[data-testid="project-crud-panel"] .ia-row-actions');
  const dataRows = qs("#iaDataRows");
  const dataPanel = qs('[data-testid="project-data-crud-panel"]');
  const dataEmptyState = qs("#iaDataEmptyState");
  const dataActions = qs(".ia-data-actions");
  const prepContextSummary = qs("#prepContextSummary");
  const prepRevisionState = qs("#prepRevisionState");
  const prepQueue = qs("#prepDataQueue");
  const uploadRow = qs(".ia-data-upload-row");

  if (projectSearch) projectSearch.value = state.workspace.projectSearch || "";
  if (showReviewProjects) showReviewProjects.checked = Boolean(state.workspace.showReviewProjects);
  updateProjectVisibilityToggleLabel(projects);
  updateProjectRowActionState(project);
  if (projectFilterSummary) {
    const hiddenDefaultCount = projects.filter((item) => isHiddenFromCustomerProjectList(item)).length;
    const hiddenCount = Math.max(0, projects.length - visibleProjects.length);
    if (state.workspace.projectSearch) {
      projectFilterSummary.textContent = `搜索结果：${visibleProjects.length} / ${projects.length} 个项目。`;
    } else if (state.workspace.showReviewProjects) {
      projectFilterSummary.textContent = `已显示内部/归档项目：${visibleProjects.length} / ${projects.length} 个项目。`;
    } else {
      projectFilterSummary.textContent = `默认显示 ${visibleProjects.length} / ${projects.length} 个项目；已隐藏 ${hiddenDefaultCount || hiddenCount} 个内部验收、归档或自动生成项目。`;
    }
  }
  if (projectSelect) {
    const boundedProjects = visibleProjects.slice(0, 80);
    projectSelect.innerHTML = `<option value="">选择项目</option>${boundedProjects.map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(projectDisplayName(item) || item.id)}</option>`).join("")}`;
    projectSelect.value = project?.id || "";
  }

  if (projectRows) {
    const shouldShowProjectRows = true;
    const rows = shouldShowProjectRows ? visibleProjects.slice(0, 24).map((item) => {
      const selected = item.id === project?.id;
      const count = projectFileCount(item, files);
      const updatedLabel = formatProjectUpdated(item);
      const stableName = projectDisplayName(item) || "未命名项目";
      return `
        <button class="table-row project-row${selected ? " selected" : ""}" type="button" data-project-select="${escapeHtml(item.id)}" data-selected="${selected ? "true" : "false"}" aria-current="${selected ? "true" : "false"}">
          <span class="project-title-cell"><strong>${escapeHtml(stableName)}</strong><small>${escapeHtml(item.id || "")}</small></span>
          <span class="project-count-cell">${escapeHtml(String(count))}</span>
          <span><mark class="status-chip">${escapeHtml(projectStatusLabel(item, files))}</mark>${state.workspace.showReviewProjects && projectVisibilityReason(item) !== "客户项目" ? `<small>${escapeHtml(projectVisibilityReason(item))}</small>` : ""}</span>
          <span class="project-updated-cell">${escapeHtml(updatedLabel)}</span>
          <span class="row-action">${selected ? "当前" : "打开"}</span>
        </button>
      `;
    }).join("") : "";
    projectRows.innerHTML = `
      <div class="table-row head project-row-head"><span>项目名称</span><span>数据</span><span>状态</span><span>最近更新</span><span>操作</span></div>
      ${rows || (shouldShowProjectRows
        ? `<div class="empty-object-state"><strong>暂无项目</strong><span>先创建项目，再上传或选择 EEG 数据。</span><button class="ghost-btn mini" type="button" data-real-action="create-project">创建项目</button></div>`
        : `<div class="empty-object-state"><strong>项目列表已收起</strong><span>请先搜索项目或创建新项目；选中项目后再展开项目内数据。</span><button class="ghost-btn mini" type="button" data-real-action="create-project">创建项目</button></div>`)}
    `;
  }

  if (dataPanel) dataPanel.classList.toggle("has-project", Boolean(project?.id));
  if (prepContextSummary) {
    prepContextSummary.textContent = project?.id
      ? `当前项目：${projectDisplayName(project) || project.id}；数据文件：${projectFiles.length} 个。`
      : "请先在左侧打开一个项目。";
  }
  if (prepRevisionState) {
    prepRevisionState.textContent = project?.id
      ? (file?.id ? `当前数据：${eegFileDisplayName(file)}；${preparationStatusLabel(file, plan, epochSet)}。` : "当前数据：未选择。")
      : "当前数据：未选择。";
  }
  if (dataEmptyState) {
    dataEmptyState.hidden = Boolean(project?.id && projectFiles.length > 0);
    const title = dataEmptyState.querySelector("strong");
    const body = dataEmptyState.querySelector("span");
    if (title) title.textContent = project?.id ? "当前项目暂无数据" : "请先选择项目";
    if (body) body.textContent = project?.id
      ? "当前项目还没有数据。"
      : "选中项目后显示数据数量和下一步。";
  }
  if (uploadRow) uploadRow.hidden = true;
  if (dataActions) dataActions.hidden = true;

  const fileTrigger = qs('[data-file-trigger="real-eeg-file"]');
  if (fileTrigger) {
    fileTrigger.disabled = !project?.id;
    fileTrigger.title = project?.id ? "选择当前项目的 EEG 数据" : "请先选择项目";
  }
  const eegInput = qs("#real-eeg-file");
  if (eegInput) eegInput.disabled = !project?.id;

  if (dataRows) {
    dataRows.hidden = !project?.id;
    dataRows.innerHTML = project?.id
      ? `
        <div class="project-detail-summary compact-project-data-summary">
          <span><b>数据文件：</b>${projectFiles.length} 个</span>
          <span><b>下一步：</b>${projectFiles.length ? "去数据页选择文件" : "去数据页上传数据"}</span>
          <button class="ghost-btn mini" type="button" data-view-jump="storage">去选择数据</button>
        </div>
      `
      : "";
  }

  if (prepQueue) {
    const rows = project?.id ? projectFiles.slice(0, 12).map((item) => {
      const rowPrep = epochSets.find((epoch) => epoch.input_file_id === item.id)
        || plans.find((candidate) => candidate.input_file_id === item.id)
        || null;
      const selected = item.id === file?.id;
      return `
        <button class="table-row prep-row${selected ? " selected" : ""}" type="button" data-file-select="${escapeHtml(item.id)}" data-jump-to-analysis="1" data-ia-action="select-prep-data" title="${escapeHtml(eegFileDisplayName(item) || item.original_filename || item.id || "EEG 数据文件")}">
          <span><strong>${escapeHtml(eegFileDisplayName(item) || "\u0045\u0045\u0047 \u6570\u636e\u6587\u4ef6")}</strong><small>${escapeHtml(fileDetailLabel(item))}</small></span>
          <span><mark class="status-chip">${escapeHtml(rowPrep ? preparationStatusLabel(item, rowPrep, rowPrep) : "\u53ef\u5f00\u59cb\u51c6\u5907")}</mark></span>
          <span class="row-action">${selected ? "\u5f53\u524d\u6570\u636e" : "\u9009\u62e9 / \u9884\u89c8"}</span>
        </button>
      `;
    }).join("") : "";
    prepQueue.innerHTML = `
      <div class="table-row head prep-row-head"><span>\u6570\u636e\u6587\u4ef6</span><span>\u51c6\u5907\u72b6\u6001</span><span>\u64cd\u4f5c</span></div>
      ${rows || `<div class="empty-object-state"><strong>${project?.id ? "\u5f53\u524d\u9879\u76ee\u6682\u65e0\u6570\u636e" : "\u8bf7\u5148\u9009\u62e9\u9879\u76ee"}</strong><span>${project?.id ? "\u8bf7\u56de\u5230\u6570\u636e\u9875\u4e0a\u4f20 EEG \u6570\u636e\u3002" : "\u5148\u5728\u9879\u76ee\u9875\u6253\u5f00\u9879\u76ee\uff0c\u518d\u9009\u62e9\u9879\u76ee\u5185\u6570\u636e\u3002"}</span><button class="ghost-btn mini" type="button" data-view-jump="${project?.id ? "storage" : "dashboard"}">${project?.id ? "\u8fdb\u5165\u6570\u636e\u9875" : "\u8fd4\u56de\u9879\u76ee"}</button></div>`}
    `;
  }

  applyCustomerTrialProjectSurfaceCleanup();
  updateDashboardSummaryCards({ project, file, plan, epochSet, projectFiles, files });
  renderStorageManagement();
  applyCleanVisibleCopy();
  applyCustomerTrialAnalysisSurfaceCleanup();
  applyProjectDashboardEmptyState();
}

function updateDashboardSummaryCards({ project, file, plan, epochSet, projectFiles = [], files = [] }) {
  const projectName = project?.id ? (projectDisplayName(project) || project.id) : "未选择项目";
  const projectNote = project?.id ? projectStatusLabel(project, files) : "先从项目列表选择一个项目";
  const fileName = file?.id ? (eegFileDisplayName(file) || file.id) : (project?.id ? "未选择数据" : "未选择数据");
  const fileNote = file?.id ? `${fileStatusLabel(file)} · ${fileDetailLabel(file)}` : (project?.id ? `${projectFiles.length} 个数据文件` : "选择项目后显示数据文件");
  const prepText = file?.id ? preparationStatusLabel(file, plan, epochSet) : "未开始";
  const progress = getWorkspaceProgressState();
  const next = getWorkspaceNextRecommendation(progress);
  const nextText = next.label;
  const nextNote = project?.id
    ? "按数据、准备、分析、结果、报告继续推进。"
    : "先创建或打开项目。";

  setTextIfPresent("#dashboard .metric-grid .metric:nth-child(1) span", "当前项目");
  setTextIfPresent("#dashboard .metric-grid .metric:nth-child(1) strong", projectName);
  setTextIfPresent("#dashboard .metric-grid .metric:nth-child(1) small", projectNote);
  setTextIfPresent("#dashboard .metric-grid .metric:nth-child(2) span", "当前数据");
  setTextIfPresent("#dashboard .metric-grid .metric:nth-child(2) strong", fileName);
  setTextIfPresent("#dashboard .metric-grid .metric:nth-child(2) small", fileNote);
  setTextIfPresent("#dashboard .metric-grid .metric:nth-child(3) span", "准备状态");
  setTextIfPresent("#dashboard .metric-grid .metric:nth-child(3) strong", prepText);
  setTextIfPresent("#dashboard .metric-grid .metric:nth-child(3) small", file?.id ? "确认后进入分析任务" : "选择数据后开始预处理");
  setTextIfPresent("#dashboard .metric-grid .metric:nth-child(4) span", "下一步");
  setTextIfPresent("#dashboard .metric-grid .metric:nth-child(4) strong", nextText);
  setTextIfPresent("#dashboard .metric-grid .metric:nth-child(4) small", nextNote);
}

/* ── Dashboard empty-state consolidation (P0-2) ─────────────────── */
function applyProjectDashboardEmptyState() {
  try {
    const hasProject = Boolean(state.real.project?.id || (state.workspace.projects || []).length > 0);
    renderDashboardStarter();
    // When no project exists and none is selected, hide secondary panels
    // to avoid repeating "you haven't started" across 6+ sections.
    const targets = [
      '#dashboard [data-testid="project-data-crud-panel"]',
      '#dashboard #prepContextSummary',
      '#dashboard #prepRevisionState',
      '#dashboard #prepDataQueue',
      '#dashboard .ia-data-upload-row',
      '#dashboard .ia-data-actions',
      '#dashboard #iaDataRows',
      '#dashboard #iaDataEmptyState',
    ];
    targets.forEach((sel) => {
      const el = qs(sel);
      if (el) el.style.display = hasProject ? '' : 'none';
    });

    // Simplify metric-grid: only show project metric when no projects
    const metricGrid = qs('#dashboard .metric-grid');
    if (metricGrid) {
      const metrics = metricGrid.querySelectorAll('.metric');
      metrics.forEach((m, idx) => {
        if (idx > 0 && !hasProject) {
          // Hide "当前数据", "准备状态" metrics; keep "下一步" as guidance
          if (idx < 3) m.style.display = 'none';
        } else {
          m.style.display = '';
        }
      });
    }

    // Hide upload authorization row in storage when no project
    const uploadAuth = qs('.storage-upload-authorization');
    if (uploadAuth) uploadAuth.style.display = hasProject ? '' : 'none';
  } catch (e) {
    console.warn('[empty-state] dashboard consolidation failed:', e);
  }
}

/* ── Analysis page state gate (P0-3) ────────────────────────────── */
function applyAnalysisPageStateGate() {
  try {
    const hasProject = Boolean(state.real.project?.id || state.workspace.selectedProjectId);
    const hasFile = Boolean(state.real.eegFile?.id || currentWorkspaceFile()?.id);
    const analysisView = qs('#analysis');
    if (!analysisView) return;
    analysisView.classList.toggle('analysis-no-project', !hasProject);
    analysisView.classList.toggle('analysis-no-file', !hasFile);

    const waveformControls = qs('#analysis .eeg-toolbar');
    const prepSettings = qs('[data-testid="preprocessing-inline-panel"]') || qs('.preprocessing-side-panel');
    const editWorkbench = qs('[data-testid="preview-edit-workbench"]');
    const previewPanel = qs('[data-testid="single-file-preview-panel"]');
    const waveformLayout = qs('#analysis .waveform-prep-layout');

    // Determine where to render the placeholder
    let placeholder = qs('#analysisEmptyPlaceholder');
    const placeholderParent = previewPanel || analysisView;

    if (!hasFile) {
      if (waveformControls) waveformControls.style.display = 'none';
      if (prepSettings) prepSettings.style.display = 'none';
      if (editWorkbench) editWorkbench.style.display = 'none';
      if (waveformLayout) waveformLayout.style.display = 'none';

      if (!placeholder && placeholderParent) {
        placeholder = document.createElement('div');
        placeholder.id = 'analysisEmptyPlaceholder';
        placeholder.className = 'analysis-empty-placeholder';
        placeholderParent.prepend(placeholder);
      }
      if (placeholder) {
        placeholder.innerHTML = hasProject
          ? '<strong>还没有选择 EEG 数据</strong><span>请先在数据页选择或上传文件。之后这里会显示波形预览、通道信息和基础检查。</span><button class="primary-btn mini" type="button" data-view-jump="storage">选择 EEG 数据</button>'
          : '<strong>请先创建或打开项目</strong><span>项目确定后，再上传或选择 EEG 数据进入检查。</span><button class="primary-btn mini" type="button" data-view-jump="dashboard">创建或打开项目</button>';
      }
      if (placeholder) placeholder.style.display = '';
    } else {
      if (waveformControls) waveformControls.style.display = '';
      if (prepSettings) prepSettings.style.display = '';
      if (editWorkbench) editWorkbench.style.display = '';
      if (waveformLayout) waveformLayout.style.display = '';
      if (placeholder) placeholder.style.display = 'none';
    }
  } catch (e) {
    console.warn('[analysis-gate] apply failed:', e);
  }
}

/* ── Workflow analysis methods grouping (P0-4) ──────────────────── */
function groupAnalysisMethods() {
  const methods = [
    { id: 'psd', label: 'PSD 频谱与频段功率', group: 'recommended' },
    { id: 'erp', label: 'ERP 事件相关电位', group: 'conditional', condition: '需要事件标记' },
    { id: 'tfr', label: 'TFR 时频分析', group: 'advanced', condition: '需要事件标记' },
    { id: 'multitaper_psd', label: 'Multitaper PSD', group: 'advanced' },
    { id: 'multitaper_tfr', label: 'Multitaper TFR', group: 'advanced' },
    { id: 'pac', label: 'PAC 相位-振幅耦合', group: 'advanced' },
    { id: 'connectivity', label: 'Connectivity 连接性分析', group: 'advanced' },
    { id: 'reference_csd', label: 'CSD 电流源密度', group: 'advanced', condition: '需要通道位置' },
    { id: 'epilepsy_ml', label: '癫痫样候选事件复核预览', group: 'special' },
  ];

  const groups = {
    recommended: { title: '推荐先运行', methods: [] },
    conditional: { title: '条件方法', methods: [] },
    advanced: { title: '进阶分析', methods: [] },
    special: { title: '专项工作台', methods: [] },
  };

  methods.forEach(m => groups[m.group].methods.push(m));
  return groups;
}

function regroupAnalysisMethods() {
  try {
    const container = qs('#analysisMethodsGrouped');
    if (!container) return;

    // Find existing method cards in the scope panel
    const scopePanel = qs('[data-testid="analysis-method-scope-panel"]');
    const existingCards = scopePanel ? qsa('.ia-method-contract-grid .ia-method-card, .ia-method-contract-grid button[data-module-id]') : [];

    if (!existingCards.length) return;

    const groups = groupAnalysisMethods();
    const groupOrder = ['recommended', 'conditional', 'advanced', 'special'];

    container.innerHTML = groupOrder.map(key => {
      const g = groups[key];
      if (!g.methods.length) return '';
      if (key === "advanced") {
        return `
          <details class="method-group method-group-collapsible" data-method-group="${key}">
            <summary class="method-group-title">${g.title}<span class="method-group-count">${g.methods.length} 项</span></summary>
            <p class="method-group-note">这些方法需要事件、统计设计、通道位置或额外复核，当前不建议作为第一次分析。</p>
            <div class="method-group-grid"></div>
          </details>
        `;
      }
      return `
        <div class="method-group" data-method-group="${key}">
          <h3 class="method-group-title">${g.title}<span class="method-group-count">${g.methods.length} 项</span></h3>
          <div class="method-group-grid"></div>
        </div>
      `;
    }).join('');

    // Map module IDs to their group
    const moduleToGroup = {};
    groups.recommended.methods.forEach(m => moduleToGroup[m.id] = 'recommended');
    groups.conditional.methods.forEach(m => moduleToGroup[m.id] = 'conditional');
    groups.advanced.methods.forEach(m => moduleToGroup[m.id] = 'advanced');
    groups.special.methods.forEach(m => moduleToGroup[m.id] = 'special');

    // Move existing cards into the grouped container
    const cardByModule = {};
    existingCards.forEach(card => {
      const moduleId = card.dataset.moduleId;
      if (moduleId) cardByModule[moduleId] = card;
    });

    Object.entries(cardByModule).forEach(([moduleId, card]) => {
      const groupKey = moduleToGroup[moduleId];
      if (!groupKey) return;
      const grid = container.querySelector(`[data-method-group="${groupKey}"] .method-group-grid`);
      if (grid) {
        grid.appendChild(card);
      }
    });

    // Hide the original flat grid if it is now empty
    const flatGrid = scopePanel?.querySelector('.ia-method-contract-grid');
    if (flatGrid && !flatGrid.children.length) {
      flatGrid.style.display = 'none';
    }
  } catch (e) {
    console.warn('[method-group] regroup failed:', e);
  }
}

function applyProductPageStructureCleanup() {
  const statistics = qs("#statistics");
  if (statistics && statistics.dataset.productClean !== "true") {
    statistics.dataset.productClean = "true";
    statistics.innerHTML = `
      <section class="panel span-2" data-testid="results-review-workbench">
        <div class="panel-head">
          <div><h2>查看分析结果</h2><p>查看已完成任务的图表、表格、参数、质量提醒和解释边界。</p></div>
        </div>
        <div id="realResultReview" class="result-review"></div>
      </section>
      <div id="epilepsyResultReviewV3"></div>
      <section class="panel" data-testid="result-boundary-panel">
        <div class="panel-head compact"><h2>结果说明</h2></div>
        <p class="customer-note">当前结果用于科研分析参考。若需要组水平统计，请先完成对应的数据汇总和统计流程。</p>
      </section>
    `;  }

  const publication = qs("#publication");
  if (publication && publication.dataset.productClean !== "true") {
    publication.dataset.productClean = "true";
    publication.innerHTML = `
      <section class="panel span-2" data-testid="report-delivery-workbench">
        <div class="panel-head">
          <div><h2>生成和下载复核记录</h2><p>把结果、图表、参数、方法和复现记录打包为科研交付材料。</p></div>
          <button class="primary-btn" type="button" data-real-action="create-report" hidden><i data-lucide="file-output"></i><span>生成复核记录</span></button>
        </div>
        <div class="delivery-grid" id="realDeliveryLinks"></div>
      </section>
      <section class="panel" data-testid="report-package-contract" hidden>
        <div class="panel-head compact"><h2>复核记录包内容</h2></div>
        <div class="storage-table compact-table">
          <div class="table-row head"><span>\u5185\u5bb9</span><span>\u7528\u9014</span><span>\u72b6\u6001</span></div>
          <div class="table-row"><span>\u56fe\u8868</span><span>\u7ed3\u679c\u67e5\u770b\u548c\u6c47\u62a5</span><span class="run">\u968f\u590d\u6838\u8bb0\u5f55\u751f\u6210</span></div>
          <div class="table-row"><span>\u8868\u683c</span><span>\u6307\u6807\u548c\u5bfc\u51fa\u6570\u636e</span><span class="run">\u968f\u590d\u6838\u8bb0\u5f55\u751f\u6210</span></div>
          <div class="table-row"><span>\u65b9\u6cd5\u8bb0\u5f55</span><span>\u53c2\u6570\u3001\u8f6f\u4ef6\u7248\u672c\u548c\u8fb9\u754c</span><span class="run">\u968f\u590d\u6838\u8bb0\u5f55\u751f\u6210</span></div>
        </div>
      </section>
    `;
    renderRealDelivery();
  }

  const journey = qs("#journey");
  if (journey && journey.dataset.productClean !== "true") {
    journey.dataset.productClean = "true";
    journey.innerHTML = `
      <section class="panel span-2" data-testid="review-validation-workbench">
        <div class="panel-head">
          <div><h2>交付质检</h2><p>后台检查数据、准备记录、结果文件和复核记录包是否具备交付条件；不评估临床诊断结论。</p></div>
        </div>
        <div class="review-gate-grid">
          <article class="review-gate-card"><strong>任务产物</strong><span>核对分析任务、图表、表格和结果文件是否齐全。</span><b>待复核</b></article>
          <article class="review-gate-card"><strong>准备记录</strong><span>确认输入数据、准备方案、参数和修订记录可追溯。</span><b>待复核</b></article>
          <article class="review-gate-card"><strong>复核记录包</strong><span>检查方法说明、结果摘要和下载入口是否完整。</span><b>待复核</b></article>
          <article class="review-gate-card"><strong>边界说明</strong><span>确认结果保持科研分析支持边界，避免诊断化表述。</span><b>待复核</b></article>
        </div>
      </section>
      <section class="panel" data-testid="review-action-panel">
        <div class="panel-head compact"><h2>后台处理</h2></div>
        <div class="real-actions compact-actions">
          <button class="ghost-btn" type="button" data-view-jump="adminOperations"><i data-lucide="list-checks"></i><span>查看任务队列</span></button>
          <button class="ghost-btn" type="button" data-view-jump="adminDashboard"><i data-lucide="monitor-dot"></i><span>回到后台总览</span></button>
          <button class="ghost-btn" type="button" data-view-jump="adminSystem"><i data-lucide="server-cog"></i><span>查看系统状态</span></button>
        </div>
      </section>
    `;
  }

  const userCenter = qs("#userCenter");
  if (userCenter && userCenter.dataset.productClean !== "true") {
    userCenter.dataset.productClean = "true";
    userCenter.innerHTML = `
      <div class="user-center-product-grid" data-testid="user-center-product-grid">
        <section class="panel user-center-column" data-testid="user-account-column">
          <div class="panel-head">
            <div><h2>个人中心</h2><p>管理账号、权限、安全和常用偏好。</p></div>
          </div>
          <div class="profile-card clean-profile">
            <div><span>\u59d3\u540d</span><strong id="userCenterName">客户账号</strong></div>
            <div><span>\u767b\u5f55\u8d26\u53f7</span><strong id="userCenterEmail">demo.customer@quanlan.cn</strong></div>
            <div><span>\u6240\u5c5e\u5355\u4f4d</span><strong id="userCenterOrg">全澜脑科学</strong></div>
            <div><span>\u8d26\u53f7\u72b6\u6001</span><strong id="userCenterRole">客户账号</strong></div>
          </div>
          <div class="user-center-section">
            <h3>\u6743\u9650\u8303\u56f4</h3>
            <div class="audit-list">
              <span><b>\u9879\u76ee\u6743\u9650\uff1a</b>可查看和管理授权项目</span>
              <span><b>\u6570\u636e\u6743\u9650\uff1a</b>可上传、选择和准备项目内 EEG 数据</span>
              <span><b>\u7ed3\u679c\u6743\u9650\uff1a</b>可查看结果并生成复核记录包</span>
            </div>
          </div>
          <div class="user-center-section">
            <h3>\u5b89\u5168\u4e0e\u767b\u51fa</h3>
            <div class="settings-list">
              <button class="ghost-btn" type="button" data-modal="security"><i data-lucide="shield-check"></i><span>\u67e5\u770b\u8d26\u53f7\u5b89\u5168\u8bf4\u660e</span></button>
              <button class="ghost-btn" id="logoutBtnUserCenter" type="button"><i data-lucide="log-out"></i><span>\u9000\u51fa\u767b\u5f55</span></button>
            </div>
          </div>
        </section>

        <section class="panel user-center-column subdued-service-column" data-testid="user-finance-column">
          <div class="panel-head compact">
            <div><h2>试用服务记录</h2><p>客户侧只显示服务状态和交付入口。</p></div>
          </div>
          <div class="service-record-list">
            <div><span>服务状态</span><strong id="userCenterBalance">试用中</strong></div>
            <div><span>记录状态</span><strong>线下确认后更新</strong></div>
            <div><span>交付记录</span><strong>报告页下载</strong></div>
          </div>
          <button class="ghost-btn" id="rechargeBtn" type="button"><i data-lucide="clipboard-check"></i><span>提醒运营确认</span></button>
          <div class="notice" id="rechargeNotice"><i data-lucide="badge-check"></i><span>等待线下确认。</span></div>
          <div class="user-center-section">
            <h3>\u901a\u77e5</h3>
            <div class="checklist compact-checklist">
              <label><input type="checkbox" checked /> \u5206\u6790\u5b8c\u6210\u63d0\u9192</label>
              <label><input type="checkbox" checked /> \u62a5\u544a\u751f\u6210\u63d0\u9192</label>
              <label><input type="checkbox" checked /> 登录后进入最近项目</label>
              <label><input type="checkbox" checked /> \u4e0b\u8f7d\u524d\u663e\u793a\u6821\u9a8c\u72b6\u6001</label>
            </div>
          </div>
        </section>
      </div>
    `;
  }
}


function applyLoginAndAdminCleanCopy() {
  const loginPairs = [
    [".boss-home", "返回首页"],
    [".entry-brand-lockup small", "清晰数据管理 · 流程化分析 · 规范结果交付"],
    [".account-title span", "QLanalyser Online"],
    [".account-title strong", "登录"],
    [".account-title small", ""],
    ['[data-login-tab="customerLogin"]', "登录"],
    ['[data-login-tab="customerRegister"]', "账号开通"],
    ['label:has(#customerEmail) span', "邮箱 / 手机号"],
    ['label:has(#customerPassword) span', "密码"],
    ['label:has(#adminEmail) span', "管理员邮箱"],
    ['label:has(#adminPassword) span', "管理员密码"],
    [".admin-note", "后台用于内部人员查看任务、账号和系统状态。"],
    ["#customerLoginBtn span", "登录"],
    ["#forgotPasswordBtn", "找回账号"],
    ['#adminLoginForm button[type="submit"] span', "进入后台"],
  ];
  loginPairs.forEach(([selector, text]) => setTextIfPresent(selector, text));
  setBrandKickerMarkup();
  const emailInput = qs("#customerEmail");
  const passwordInput = qs("#customerPassword");
  const adminEmail = qs("#adminEmail");
  const adminPassword = qs("#adminPassword");
  if (emailInput) emailInput.placeholder = "输入已注册邮箱或体验手机号";
  if (passwordInput) passwordInput.placeholder = "请输入账户密码";
  if (emailInput && !emailInput.value) emailInput.value = demoCustomer.email;
  if (passwordInput && !passwordInput.value) passwordInput.value = demoCustomer.password;
  if (adminEmail) adminEmail.placeholder = "内部后台账号";
  if (adminPassword) adminPassword.placeholder = "请输入后台密码";
  const loginBrand = qs(".login-brand");
  if (loginBrand) loginBrand.setAttribute("aria-label", "QLanalyser 脑电分析平台封面");
  const valueCards = qsa(".entry-value-grid article");
  [["清晰数据管理", "原始数据、事件表、参数与结果统一留痕。"], ["流程化分析", "从质量预览、数据准备到结果导出，按科研分析流程推进。"], ["规范结果交付", "图表、表格、方法说明和操作记录可一起交付。"]].forEach(([title, body], index) => {
    const card = valueCards[index];
    if (!card) return;
    const strong = card.querySelector("strong");
    const span = card.querySelector("span");
    if (strong) strong.textContent = title;
    if (span) span.textContent = body;
  });
  Object.entries(PRODUCT_NAV_LABELS).forEach(([view, label]) => setTextIfPresent(`[data-view="${view}"] span`, label));
  qsa('[data-view="journey"]').forEach((button) => {
    button.hidden = state.role !== "admin";
    button.setAttribute("aria-hidden", state.role !== "admin" ? "true" : "false");
  });
  const activeView = qs(".view.active")?.id || "dashboard";
  setTextIfPresent("#viewTitle", PRODUCT_VIEW_TITLES[activeView] || "QLanalyser Online");
  setTextIfPresent("#topEyebrow", state.role === "admin" ? "QLanalyser Online · 内部后台" : "QLanalyser Online · EEG 科研数据到复核记录");
  applyTeachingModeChrome();
  setTextIfPresent("#logoutBtn span", "退出");
  setTextIfPresent("#roleLabel", state.role === "admin" ? "内部账号" : "个人中心");
}


function renderWorkflowPrimaryAction() {
  const panel = qs('[data-testid="analysis-task-workbench"]');
  if (!panel) return;
  let target = panel.querySelector('[data-testid="workflow-primary-action"]');
  if (!target) {
    target = document.createElement("div");
    target.className = "workflow-primary-action";
    target.dataset.testid = "workflow-primary-action";
    panel.appendChild(target);
  }
  const progress = getWorkspaceProgressState();
  if (!progress.hasProject) {
    target.innerHTML = `
      <strong>第 1 步还没完成：创建或打开项目</strong>
      <span>项目会保存本次分析的数据、准备记录、任务、结果和报告。</span>
      <button class="primary-btn" type="button" data-view-jump="dashboard"><i data-lucide="folder-kanban"></i><span>创建或打开项目</span></button>
    `;
  } else if (!progress.hasFile) {
    target.innerHTML = `
      <strong>第 2 步还没完成：上传或选择 EEG 数据</strong>
      <span>当前项目还没有可分析的数据文件。</span>
      <button class="primary-btn" type="button" data-view-jump="storage"><i data-lucide="database"></i><span>上传或选择数据</span></button>
    `;
  } else if (!progress.hasPreparationPlan) {
    target.innerHTML = `
      <strong>第 3 步还没完成：确认数据准备</strong>
      <span>请先检查 EEG 数据并确认准备方案。</span>
      <button class="primary-btn" type="button" data-view-jump="analysis"><i data-lucide="sliders-horizontal"></i><span>确认准备并进入分析</span></button>
    `;
  } else {
    target.innerHTML = `
      <strong>推荐先运行 PSD</strong>
      <span>查看不同频段的能量分布。结果仅作科研分析参考，不作为诊断结论。</span>
      <button class="primary-btn" type="button" data-real-action="run-psd"><i data-lucide="activity"></i><span>运行 PSD 分析</span></button>
    `;
  }
  if (window.lucide) window.lucide.createIcons();
}

function applyCustomerAnalysisTaskCopy() {
  const planReady = isAnalysisReady();
  const scopePanel = qs('[data-testid="analysis-method-scope-panel"]');
  const groupedMethods = qs("#analysisMethodsGrouped");
  setTextIfPresent('[data-testid="analysis-task-workbench"] h2', "选择分析方法");
  setTextIfPresent('[data-testid="analysis-task-workbench"] .panel-head p', "根据当前数据和准备状态，选择可以运行的分析任务。");
  setTextIfPresent('[data-testid="analysis-task-workbench"] .badge', planReady ? "推荐先运行 PSD" : "等待数据准备");
  setTextIfPresent(".analysis-context-strip span", planReady ? "数据准备已确认，可以提交推荐分析。" : "前置要求：已选择项目、已选择数据，并确认数据准备方案。");
  setTextIfPresent('[data-testid="analysis-method-scope-panel"] h2', "分析方法");
  setTextIfPresent('[data-testid="analysis-method-scope-panel"] .panel-head p', "第一次分析先运行 PSD；ERP 仅在事件标记有效时开放。");
  renderWorkflowPrimaryAction();
  if (scopePanel) {
    scopePanel.hidden = !planReady;
    scopePanel.setAttribute("aria-hidden", planReady ? "false" : "true");
    scopePanel.classList.toggle("workflow-methods-locked", !planReady);
  }
  if (groupedMethods && !planReady) groupedMethods.innerHTML = "";
  const methodCards = qsa('[data-testid="analysis-method-scope-panel"] .ia-method-card');
  const moduleOrder = ["psd", "erp", "tfr", "multitaper_psd", "multitaper_tfr", "pac", "connectivity", "reference_csd", "epilepsy_ml"];
  const customerVisibleModules = new Set(["psd", "erp"]);
  const customerMethodCopy = {
    psd: ["PSD 频谱分析", "第一次分析建议先运行 PSD，先看主要频段能量分布。", "推荐首步", "recommended", "run-psd"],
    erp: ["ERP 事件相关电位", "适合已有事件标记的数据；运行前先确认事件语义。", "需事件", "conditional", "run-erp"],
    tfr: ["TFR 时频分析", "需要事件、时间窗和基线设置，适合进阶研究。", "进阶", "advanced", "run-tfr"],
    multitaper_psd: ["Multitaper PSD", "用于对频谱结果做参数化比较，不作为第一次分析首选。", "进阶", "advanced", "run-multitaper-psd"],
    multitaper_tfr: ["Multitaper TFR", "需要事件锁定和窗参数，适合进阶时频分析。", "进阶", "advanced", "run-multitaper-tfr"],
    pac: ["PAC 相位-振幅耦合", "描述相位与振幅的统计耦合，不能单独解释为因果机制。", "进阶", "advanced", "run-pac"],
    connectivity: ["Connectivity 连接性分析", "描述通道间统计关联，不证明信息流或因果方向。", "进阶", "advanced", "run-connectivity"],
    reference_csd: ["CSD 电流源密度计算", "需要通道位置信息；这是传感器空间滤波，不是源定位或诊断。", "进阶", "advanced", "run-reference-csd"],
    epilepsy_ml: ["癫痫样候选事件复核预览", "候选事件初筛和人工复核标注入口；科研辅助用途，不作为诊断或临床结论。", "专项", "conditional", "open-epilepsy-workbench"],
  };
  methodCards.forEach((card, index) => {
    const moduleId = card.dataset.moduleId || moduleOrder[index];
    const visibleToCustomer = state.role === "admin" || customerVisibleModules.has(moduleId);
    card.hidden = !visibleToCustomer;
    card.setAttribute("aria-hidden", visibleToCustomer ? "false" : "true");
    if (!visibleToCustomer) {
      card.disabled = true;
      card.setAttribute("aria-disabled", "true");
      card.dataset.disabledReason = "该方法属于进阶/内部流程，客户工作区暂不开放。";
      return;
    }
    const copy = customerMethodCopy[moduleId];
    if (!copy) return;
    const [title, body, status, tone, action] = copy;
    card.dataset.moduleId = moduleId;
    card.dataset.realAction = action;
    card.setAttribute("type", "button");
    const availability = moduleAvailability(moduleId);
    card.disabled = !availability.enabled;
    card.setAttribute("aria-disabled", availability.enabled ? "false" : "true");
    card.dataset.disabledReason = availability.enabled ? "" : availability.reason;
    card.setAttribute("title", availability.reason || `${title}：点击后按当前数据条件运行或提示前置步骤。`);
    card.classList.remove("beta", "draft", "dependency", "available", "recommended", "conditional", "advanced");
    if (tone) card.classList.add(tone);
    const strong = card.querySelector("strong");
    const span = card.querySelector("span");
    const badge = card.querySelector("b");
    if (strong) strong.textContent = title;
    if (span) span.textContent = body;
    if (badge) badge.textContent = status;
  });
  qsa('[data-testid="analysis-method-scope-panel"] .method-group').forEach((group) => {
    const hasVisibleCard = qsa(".ia-method-card", group).some((card) => !card.hidden && card.getAttribute("aria-hidden") !== "true");
    group.hidden = !hasVisibleCard;
    group.setAttribute("aria-hidden", hasVisibleCard ? "false" : "true");
  });
}

function applyCleanVisibleCopy() {
  applyProductPageStructureCleanup();
  Object.entries(PRODUCT_NAV_LABELS).forEach(([view, label]) => setTextIfPresent(`[data-view="${view}"] span`, label));
  qsa('[data-view="journey"]').forEach((button) => {
    button.hidden = state.role !== "admin";
    button.setAttribute("aria-hidden", state.role !== "admin" ? "true" : "false");
  });
  applyCustomerTrialAnalysisSurfaceCleanup();
  applyCustomerTrialStorageSurfaceCleanup();
  const activeView = qs(".view.active")?.id || "dashboard";
  setTextIfPresent("#viewTitle", PRODUCT_VIEW_TITLES[activeView] || "QLanalyser Online");
  setTextIfPresent("#logoutBtn span", "退出");
  const teachingButton = qs("#teachingModeBtn");
  if (teachingButton) {
    teachingButton.hidden = state.role === "admin";
    teachingButton.setAttribute("aria-hidden", state.role === "admin" ? "true" : "false");
  }
  if (state.role === "admin") {
    setTextIfPresent("#topEyebrow", "QLanalyser Online · 内部后台");
    setTextIfPresent("#roleLabel", "内部账号");
    setTextIfPresent("#balanceSide", "后台");
    setTextIfPresent("#accountHint", "账号、任务、交付与系统状态");
  } else {
    setTextIfPresent("#topEyebrow", "QLanalyser Online · EEG 科研数据到复核记录");
    setTextIfPresent("#roleLabel", getStoredCustomer()?.name || "客户账号");
    setTextIfPresent("#balanceSide", "个人中心");
    setTextIfPresent("#accountHint", visibleCustomerShellHint(getStoredCustomer()));
  }
  setTextIfPresent('[data-testid="project-crud-panel"] h2', "第 1 步：创建或打开项目");
  setTextIfPresent('[data-testid="project-crud-panel"] .panel-head p', "项目会保存本次分析的数据、准备记录、任务、结果和报告。");
  setTextIfPresent("#workspaceProjectSearch + span", "项目搜索");
  setTextIfPresent('label:has(#workspaceProjectSearch) span', "搜索项目");
  const projectSearch = qs("#workspaceProjectSearch");
  if (projectSearch) projectSearch.placeholder = "按项目名或项目编号搜索";
  setTextIfPresent('label[for="workspaceShowReviewProjects"] span', state.role === "admin" ? "显示内部/归档项目" : "显示更多项目");
  updateProjectVisibilityToggleLabel();
  setTextIfPresent('[data-testid="project-data-crud-panel"] h2', "项目内数据");
  setTextIfPresent('[data-testid="project-data-crud-panel"] .panel-head p', "打开项目后，在这里查看项目内数据概况和下一步入口；上传和文件整理请进入“数据”。");
  setTextIfPresent('[data-file-trigger="real-eeg-file"] span', "选择 EEG 数据");
  setTextIfPresent('[data-real-action="upload-eeg"] span', "上传到当前项目");
  setTextIfPresent("#realEegFileName", qs("#realEegFileName")?.textContent || "尚未选择文件");
  setTextIfPresent('[data-ia-action="edit-project"] span', "编辑");
  setTextIfPresent('[data-ia-action="archive-project"] span', "归档");
  setTextIfPresent('[data-ia-action="delete-project"] span', "删除");
  setTextIfPresent('[data-ia-action="rename-data"] span', "编辑名称 / 备注");
  setTextIfPresent(".next-action-hint", "先从项目开始，再选择项目内数据并准备分析。");
  setTextIfPresent('[data-real-action="create-project"] span', "创建项目");
  renderEegPreviewEmptyState();
  applyLoginAndAdminCleanCopy();
  applyCustomerAnalysisTaskCopy();
  sanitizeVisibleCopyTree();
  updateRealActionGate();
  applyCustomerTrialP0Fixes();
  applyFinalVisibleCopyGate();
}


function eegCanvasChannelFromEvent(event) {
  const canvas = qs("#eegCanvas");
  const plot = eegState.lastPlot;
  const payload = currentWaveformPayload();
  if (!canvas || !plot || !payload?.channels?.length) return "";
  const rect = canvas.getBoundingClientRect();
  const y = Number(event.clientY - rect.top);
  const top = Number(plot.top || 0);
  const plotHeight = Math.max(1, Number(plot.plotHeight || 1));
  const visibleCount = Math.min(payload.channels.length, Number(eegState.visibleChannels || payload.channels.length));
  const index = Math.max(0, Math.min(visibleCount - 1, Math.floor(((y - top) / plotHeight) * visibleCount)));
  const channel = payload.channels[index];
  return typeof channel === "string" ? channel : (channel?.name || "");
}

function handleEegCanvasPointerDown(event) {
  if (event.button !== 0 && event.button !== 1) return;
  const time = eegCanvasTimeFromEvent(event);
  if (!Number.isFinite(time)) return;
  event.preventDefault();
  const canvas = qs("#eegCanvas");
  canvas?.focus?.({ preventScroll: true });
  eegState.hoverTimeSec = time;
  eegState.hoverChannelName = eegCanvasChannelFromEvent(event);
  if ((event.button === 1 || event.buttons === 4) && eegState.interactionMode === "browse") {
    eegState.middlePan = { startX: event.clientX, startSec: Number(eegState.start || 0) };
    canvas?.classList.add("dragging");
    renderWaveformInteractionHint("中键拖动：水平浏览当前 EEG。");
    return;
  }
  if (eegState.interactionMode === "browse") {
    renderWaveformInteractionHint(`浏览 ${time.toFixed(2)} s${eegState.hoverChannelName ? ` / ${eegState.hoverChannelName}` : ""}；左键不会写入草稿。`);
    renderWaveformWorkbenchStatus();
    return;
  }
  if (eegState.interactionMode === "markBadChannel") {
    handleIaAction("mark-bad-channel").catch((error) => showToast(error.message || "坏道标记失败。"));
    return;
  }
  canvas?.classList.add("dragging");
  eegState.drag = { mode: eegState.interactionMode, startTime: time, currentTime: time, moved: false };
  if (eegState.interactionMode === "selectSegment") {
    eegState.selectedSegment = { start_sec: time, end_sec: time + waveformAnchorDriftToleranceSec() };
    updateSelectedSegmentInputs(eegState.selectedSegment);
  }
  redrawCurrentWaveform();
}

function handleEegCanvasPointerMove(event) {
  if (eegState.middlePan) {
    const plot = eegState.lastPlot;
    const dx = Number(event.clientX - eegState.middlePan.startX);
    const plotWidth = Math.max(1, Number(plot?.plotWidth || 1));
    const deltaSec = -(dx / plotWidth) * Math.max(2, Number(eegState.windowSec || 10));
    eegState.start = clampEegWindowStart(eegState.middlePan.startSec + deltaSec, eegState.windowSec);
    syncEegControlsFromState();
    redrawCurrentWaveform();
    event.preventDefault();
    return;
  }
  if (!eegState.drag) return;
  const time = eegCanvasTimeFromEvent(event);
  if (!Number.isFinite(time)) return;
  event.preventDefault();
  eegState.drag.currentTime = time;
  eegState.drag.moved = Math.abs(time - eegState.drag.startTime) > waveformAnchorDriftToleranceSec();
  const normalized = normalizeSegmentRange(eegState.drag.startTime, time);
  if (normalized) {
    eegState.selectedSegment = normalized;
    updateSelectedSegmentInputs(normalized);
    redrawCurrentWaveform();
  }
}

function handleEegCanvasPointerUp(event) {
  if (eegState.middlePan) {
    event.preventDefault();
    eegState.middlePan = null;
    qs("#eegCanvas")?.classList.remove("dragging");
    reloadWaveformAfterViewportChange({ silent: true });
    return;
  }
  if (!eegState.drag) return;
  event.preventDefault();
  const mode = eegState.drag.mode;
  const normalized = normalizeSegmentRange(eegState.drag.startTime, eegState.drag.currentTime);
  eegState.drag = null;
  qs("#eegCanvas")?.classList.remove("dragging");
  if (normalized) {
    eegState.selectedSegment = normalized;
    updateSelectedSegmentInputs(normalized);
    if (mode === "markBadSegment") {
      handleIaAction("exclude-segment").catch((error) => showToast(error.message || "坏段标记失败。"));
      renderWaveformInteractionHint(`已标记坏段 ${normalized.start_sec.toFixed(2)}-${normalized.end_sec.toFixed(2)} s，可恢复。`);
    } else {
      renderWaveformInteractionHint(`已选择 ${normalized.start_sec.toFixed(2)}-${normalized.end_sec.toFixed(2)} s，可剔除或添加标签`);
    }
    redrawCurrentWaveform();
  }
}

function handleEegCanvasWheel(event) {
  const canvas = qs("#eegCanvas");
  if (!canvas || event.target !== canvas) return;
  event.preventDefault();
  if (event.ctrlKey || event.metaKey) {
    const plot = eegState.lastPlot;
    const rect = canvas.getBoundingClientRect();
    const oldStart = Number(eegState.start || plot?.timeStart || 0);
    const oldDuration = Math.max(2, Number(eegState.windowSec || 10));
    const anchorTime = plot ? canvasXToTime(event.clientX - rect.left, plot) : oldStart + oldDuration / 2;
    const factor = event.deltaY > 0 ? EDF_BROWSER_INTERACTION_CONSTANTS.zoomFactor : 1 / EDF_BROWSER_INTERACTION_CONSTANTS.zoomFactor;
    zoomEegWindow(factor, anchorTime, { silent: true });
  } else {
    const direction = event.deltaY > 0 ? 1 : -1;
    shiftEegWindow(direction, EDF_BROWSER_INTERACTION_CONSTANTS.wheelPanRatio, { silent: true });
  }
}

function shouldHandleWaveformKeydown(event) {
  const target = event.target;
  const tagName = String(target?.tagName || "").toLowerCase();
  if (tagName === "input" || tagName === "textarea" || tagName === "select" || target?.isContentEditable) return false;
  const workbench = target?.closest?.('[data-testid="preview-edit-workbench"], .eeg-viewer, .eeg-toolbar');
  return Boolean(workbench || currentWaveformPayload()?.data_uv?.length);
}

function runWaveformKeyboardAction(action) {
  Promise.resolve(action).catch((error) => showToast(error.message || "波形预览更新失败。"));
  qs("#eegCanvas")?.focus?.({ preventScroll: true });
}

function handleWaveformKeydown(event) {
  if (!shouldHandleWaveformKeydown(event)) return false;
  const key = event.key;
  if (key === "PageUp") {
    event.preventDefault();
    runWaveformKeyboardAction(shiftEegWindow(-1, EDF_BROWSER_INTERACTION_CONSTANTS.pagePanRatio));
    return true;
  }
  if (key === "PageDown") {
    event.preventDefault();
    runWaveformKeyboardAction(shiftEegWindow(1, EDF_BROWSER_INTERACTION_CONSTANTS.pagePanRatio));
    return true;
  }
  if (key === "ArrowLeft") {
    event.preventDefault();
    runWaveformKeyboardAction(shiftEegWindow(-1, EDF_BROWSER_INTERACTION_CONSTANTS.arrowPanRatio));
    return true;
  }
  if (key === "ArrowRight") {
    event.preventDefault();
    runWaveformKeyboardAction(shiftEegWindow(1, EDF_BROWSER_INTERACTION_CONSTANTS.arrowPanRatio));
    return true;
  }
  if ((key === "+" || key === "=") && (event.ctrlKey || event.metaKey)) {
    event.preventDefault();
    runWaveformKeyboardAction(zoomEegWindow(1 / EDF_BROWSER_INTERACTION_CONSTANTS.zoomFactor));
    return true;
  }
  if ((key === "-" || key === "_") && (event.ctrlKey || event.metaKey)) {
    event.preventDefault();
    runWaveformKeyboardAction(zoomEegWindow(EDF_BROWSER_INTERACTION_CONSTANTS.zoomFactor));
    return true;
  }
  if (key === "+" || key === "=") {
    event.preventDefault();
    runWaveformKeyboardAction(adjustEegAmplitudeSensitivity(1));
    return true;
  }
  if (key === "-" || key === "_") {
    event.preventDefault();
    runWaveformKeyboardAction(adjustEegAmplitudeSensitivity(-1));
    return true;
  }
  if (key === "Escape" || key.toLowerCase() === "b") {
    event.preventDefault();
    setWaveformInteractionMode("browse");
    return true;
  }
  if (!event.ctrlKey && !event.metaKey && key.toLowerCase() === "s") {
    event.preventDefault();
    setWaveformInteractionMode("selectSegment");
    return true;
  }
  if (!event.ctrlKey && !event.metaKey && key.toLowerCase() === "x") {
    event.preventDefault();
    setWaveformInteractionMode("markBadSegment");
    return true;
  }
  if (!event.ctrlKey && !event.metaKey && key.toLowerCase() === "c") {
    event.preventDefault();
    setWaveformInteractionMode("markBadChannel");
    return true;
  }
  if (!event.ctrlKey && !event.metaKey && key.toLowerCase() === "r") {
    event.preventDefault();
    runWaveformKeyboardAction(resetEegPreviewControls());
    return true;
  }
  if (!event.ctrlKey && !event.metaKey && key.toLowerCase() === "f") {
    event.preventDefault();
    const toggle = qs("#eegFilterPreviewToggle");
    if (toggle) {
      toggle.checked = !toggle.checked;
      eegState.filterEnabled = Boolean(toggle.checked);
      eegState.showFiltered = Boolean(toggle.checked);
      runWaveformKeyboardAction(reloadWaveformPreview());
    }
    return true;
  }
  if (key === "?") {
    event.preventDefault();
    renderWaveformInteractionHint("快捷键：滚轮浏览，Ctrl/Cmd+滚轮缩放，PageUp/PageDown 翻页，Left/Right 小步，+/- 调振幅，S/X/C/B 切换模式。");
    return true;
  }
  return false;
}

function handleInlineEpilepsyReaderWheel(event) {
  const target = inlineEpilepsyReaderEventTarget(event.target);
  if (!target) return;
  event.preventDefault();
  const file = currentWorkspaceFile() || state.real.eegFile || {};
  const rect = target.getBoundingClientRect();
  const anchorRatio = rect.width ? Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width)) : 0.5;
  if (event.ctrlKey || event.metaKey) {
    const factor = event.deltaY > 0 ? EDF_BROWSER_INTERACTION_CONSTANTS.zoomFactor : 1 / EDF_BROWSER_INTERACTION_CONSTANTS.zoomFactor;
    zoomInlineEpilepsyViewport(factor, anchorRatio, file);
  } else {
    panInlineEpilepsyViewport(Math.sign(event.deltaY || event.deltaX || 1) * EDF_BROWSER_INTERACTION_CONSTANTS.wheelPanRatio, file);
  }
  rerenderInlineEpilepsyReaderAfterInteraction();
}

function handleInlineEpilepsyReaderKeydown(event) {
  const target = inlineEpilepsyReaderEventTarget(document.activeElement) || inlineEpilepsyReaderEventTarget(event.target);
  if (!target) return false;
  if (["INPUT", "TEXTAREA", "SELECT"].includes(event.target?.tagName)) return false;
  const file = currentWorkspaceFile() || state.real.eegFile || {};
  const key = event.key;
  if (key === "ArrowLeft") {
    event.preventDefault();
    if (event.ctrlKey || event.metaKey) {
      panInlineEpilepsyViewport(-EDF_BROWSER_INTERACTION_CONSTANTS.arrowPanRatio, file);
    } else {
      selectInlineEpilepsyRelativeCandidate(-1, { file: file });
    }
  } else if (key === "ArrowRight") {
    event.preventDefault();
    if (event.ctrlKey || event.metaKey) {
      panInlineEpilepsyViewport(EDF_BROWSER_INTERACTION_CONSTANTS.arrowPanRatio, file);
    } else {
      selectInlineEpilepsyRelativeCandidate(1, { file: file });
    }
  } else if (key === "PageUp") {
    event.preventDefault();
    panInlineEpilepsyViewport(-EDF_BROWSER_INTERACTION_CONSTANTS.pagePanRatio, file);
  } else if (key === "PageDown") {
    event.preventDefault();
    panInlineEpilepsyViewport(EDF_BROWSER_INTERACTION_CONSTANTS.pagePanRatio, file);
  } else if (key === "+" || key === "=") {
    event.preventDefault();
    if (event.ctrlKey || event.metaKey) zoomInlineEpilepsyViewport(1 / EDF_BROWSER_INTERACTION_CONSTANTS.zoomFactor, 0.5, file);
    else {
      const reader = inlineEpilepsyReaderState();
      reader.sensitivityUvPerRow = Math.min(EDF_BROWSER_INTERACTION_CONSTANTS.maxSensitivityUvPerRow, reader.sensitivityUvPerRow * EDF_BROWSER_INTERACTION_CONSTANTS.gainStepRatio);
    }
  } else if (key === "-" || key === "_") {
    event.preventDefault();
    if (event.ctrlKey || event.metaKey) zoomInlineEpilepsyViewport(EDF_BROWSER_INTERACTION_CONSTANTS.zoomFactor, 0.5, file);
    else {
      const reader = inlineEpilepsyReaderState();
      reader.sensitivityUvPerRow = Math.max(EDF_BROWSER_INTERACTION_CONSTANTS.minSensitivityUvPerRow, reader.sensitivityUvPerRow / EDF_BROWSER_INTERACTION_CONSTANTS.gainStepRatio);
    }
  } else if (key === "k" || key === "K") {
    event.preventDefault();
    var selId = state.epilepsyInline && state.epilepsyInline.selectedEventId;
    if (selId) {
      state.epilepsyInline.draftCommands.push({ eventId: selId, label: "keep_candidate", displayLabel: "保留候选", at: new Date().toISOString() });
      state.epilepsyInline.redoCommands = [];
      state.epilepsyInline.draftSaved = false;
      showToast("候选事件 " + selId + " → 保留候选");
      renderInlineEpilepsyWorkbench();
      return true;
    }
  } else if (key === "r" || key === "R") {
    event.preventDefault();
    var selId2 = state.epilepsyInline && state.epilepsyInline.selectedEventId;
    if (selId2) {
      state.epilepsyInline.draftCommands.push({ eventId: selId2, label: "Artifact", displayLabel: "排除候选", at: new Date().toISOString() });
      state.epilepsyInline.redoCommands = [];
      state.epilepsyInline.draftSaved = false;
      showToast("候选事件 " + selId2 + " → 排除/伪迹");
      renderInlineEpilepsyWorkbench();
      setTimeout(function() { selectInlineEpilepsyRelativeCandidate(1, { file: file }); }, 200);
      return true;
    }
  } else if (key === "m" || key === "M") {
    event.preventDefault();
    var selId3 = state.epilepsyInline && state.epilepsyInline.selectedEventId;
    if (selId3) {
      state.epilepsyInline.draftCommands.push({ eventId: selId3, label: "Needs review", displayLabel: "需复核", at: new Date().toISOString() });
      state.epilepsyInline.redoCommands = [];
      state.epilepsyInline.draftSaved = false;
      showToast("候选事件 " + selId3 + " → 需复核");
      renderInlineEpilepsyWorkbench();
      return true;
    }
  } else if (key === "Escape") {
    event.preventDefault();
    state.epilepsyInline.selectedEventId = "";
    renderInlineEpilepsyWorkbench();
    showToast("已取消选中，返回自由浏览");
    return true;
  } else {
    return false;
  }
  rerenderInlineEpilepsyReaderAfterInteraction();
  return true;
}

function setInlineEpilepsyOverviewFromPointer(event, overview) {
  const rect = overview.getBoundingClientRect();
  const durationTotal = Number(overview.dataset.durationSec || inlineEpilepsyFileDuration());
  const reader = inlineEpilepsyReaderState();
  const ratio = rect.width ? Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width)) : 0;
  setInlineEpilepsyViewport({
    startSec: ratio * durationTotal - reader.durationSec / 2,
    file: currentWorkspaceFile() || state.real.eegFile || {},
  });
  syncInlineEpilepsyOverviewTargetDom(overview);
}

function syncInlineEpilepsyOverviewTargetDom(overview = qs('[data-testid="inline-epilepsy-overview-strip"]')) {
  if (!overview) return;
  const reader = inlineEpilepsyReaderState();
  const durationTotal = Math.max(1, Number(overview.dataset.durationSec || inlineEpilepsyFileDuration()));
  const current = overview.querySelector(".inline-overview-current-window");
  const left = Math.max(0, Math.min(100, (Number(reader.startSec || 0) / durationTotal) * 100));
  const width = Math.max(1, Math.min(100 - left, (Number(reader.durationSec || 0) / durationTotal) * 100));
  overview.dataset.startSec = Number(reader.startSec || 0).toFixed(3);
  overview.dataset.windowSec = Number(reader.durationSec || 0).toFixed(3);
  overview.setAttribute("aria-valuenow", Number(reader.startSec || 0).toFixed(1));
  if (current) {
    current.style.left = `${left.toFixed(3)}%`;
    current.style.width = `${width.toFixed(3)}%`;
  }
}

document.addEventListener("mousedown", (event) => {
  if (event.target?.matches?.("#eegCanvas")) handleEegCanvasPointerDown(event);
  const overview = event.target?.closest?.('[data-testid="inline-epilepsy-overview-strip"]');
  if (overview) {
    event.preventDefault();
    inlineEpilepsyReaderState().overviewDrag = true;
    setInlineEpilepsyOverviewFromPointer(event, overview);
    return;
  }
  if (event.button === 1 && inlineEpilepsyReaderEventTarget(event.target)) {
    event.preventDefault();
    const reader = inlineEpilepsyReaderState();
    reader.middlePan = { clientX: event.clientX, startSec: reader.startSec };
  }
});
document.addEventListener("auxclick", (event) => {
  if (event.target?.matches?.("#eegCanvas")) event.preventDefault();
});
document.addEventListener("mousemove", (event) => {
  handleEegCanvasPointerMove(event);
  const reader = inlineEpilepsyReaderState();
  const overview = qs('[data-testid="inline-epilepsy-overview-strip"]');
  if (reader.overviewDrag && overview) {
    setInlineEpilepsyOverviewFromPointer(event, overview);
    return;
  }
  if (reader.middlePan) {
    const panel = qs('[data-testid="inline-epilepsy-waveform-panel"]');
    const width = Math.max(1, panel?.getBoundingClientRect?.().width || 900);
    const dx = event.clientX - reader.middlePan.clientX;
    setInlineEpilepsyViewport({
      startSec: reader.middlePan.startSec - (dx / width) * reader.durationSec,
      file: currentWorkspaceFile() || state.real.eegFile || {},
    });
    rerenderInlineEpilepsyReaderAfterInteraction();
  }
});
document.addEventListener("mouseup", (event) => {
  handleEegCanvasPointerUp(event);
  const reader = inlineEpilepsyReaderState();
  const wasOverviewDrag = Boolean(reader.overviewDrag);
  reader.overviewDrag = false;
  reader.middlePan = null;
  if (wasOverviewDrag) rerenderInlineEpilepsyReaderAfterInteraction();
});
document.addEventListener("wheel", handleEegCanvasWheel, { passive: false });
document.addEventListener("wheel", handleInlineEpilepsyReaderWheel, { passive: false });

document.addEventListener("click", (event) => {
  const modalCloseButton = event.target?.closest?.("#modalCloseBtn");
  if (modalCloseButton) {
    event.preventDefault?.();
    closeModal();
    return;
  }
  const knowledgeButton = event.target?.closest?.("#knowledgeBtn");
  if (knowledgeButton) {
    event.preventDefault?.();
    openModal("knowledge");
    recordUiAction("help:knowledge", "pass", "知识库说明已打开。");
    return;
  }
  const accountModalButton = event.target?.closest?.("[data-account-modal]");
  if (accountModalButton) {
    event.preventDefault?.();
    openModal(accountModalButton.dataset.accountModal || "account");
    recordUiAction(`account:${accountModalButton.dataset.accountModal || "account"}`, "pass", "个人中心弹窗已打开。");
    return;
  }
  const auditButton = event.target?.closest?.("#auditBtn");
  if (auditButton) {
    event.preventDefault?.();
    openModal("audit");
    recordUiAction("audit:open", "pass", "操作记录已打开。");
    return;
  }
  const forgotPasswordButton = event.target?.closest?.("#forgotPasswordBtn");
  if (forgotPasswordButton) {
    event.preventDefault?.();
    openModal("loginHelp");
    recordUiAction("auth:help", "pass", "账号帮助已打开。");
    return;
  }
  const loginTabButton = event.target?.closest?.("[data-login-tab]");
  if (loginTabButton) {
    event.preventDefault?.();
    switchLoginTab(loginTabButton.dataset.loginTab);
  const message = loginTabButton.dataset.loginTab === "customerRegister"
      ? "试点阶段由运营人员开通账号。"
      : (loginTabButton.dataset.loginTab === "adminLogin" ? "已切换到内部后台。" : "已切换到登录。");
    recordUiAction("auth:switch-tab", "pass", message, { tab: loginTabButton.dataset.loginTab });
    return;
  }
  const uploadHelpButton = event.target?.closest?.("#uploadHelpBtn");
  if (uploadHelpButton) {
    event.preventDefault?.();
    openModal("uploadHelp");
    recordUiAction("upload:help", "pass", "上传帮助已打开。");
    return;
  }
  const teachingButton = event.target?.closest?.("[data-teaching-action]");
  if (teachingButton) {
    event.preventDefault?.();
    const action = teachingButton.dataset.teachingAction;
    if (action === "start") startTeachingMode({ showGuide: true });
    else if (action === "quickstart") startTeachingMode({ showGuide: false, quickStart: true, targetView: "analysis" });
    else if (action === "exit") closeTeachingMode();
    else if (action === "guide") {
      state.teaching.guideActive = true;
      state.teaching.stepIndex = 0;
      renderTeachingOverlay();
    } else if (action === "next") goTeachingStep(1);
    else if (action === "prev") goTeachingStep(-1);
    else if (action === "close") finishTeachingGuide();
    return;
  }
  const sendCodeButton = event.target?.closest?.("#sendCodeBtn");
  if (sendCodeButton) {
    event.preventDefault?.();
    sendSandboxVerificationCode();
    return;
  }
  const registerSubmitButton = event.target?.closest?.("#customerRegisterForm button[type='submit']");
  if (registerSubmitButton) {
    event.preventDefault?.();
    registerCustomer(collectRegisterPayload());
    return;
  }
  const adminSubmitButton = event.target?.closest?.("#adminLoginForm button[type='submit']");
  if (adminSubmitButton) {
    event.preventDefault?.();
    loginAdmin(qs("#adminEmail")?.value.trim() || "", qs("#adminPassword")?.value || "");
    return;
  }
  const rechargeButton = event.target?.closest?.("#rechargeBtn");
  if (rechargeButton) {
    event.preventDefault?.();
    handleSandboxRecharge();
    return;
  }
  const inboxButton = event.target?.closest?.("#refreshInboxBtn");
  if (inboxButton) {
    event.preventDefault?.();
    refreshInbox();
    return;
  }
  const projectSelectButton = event.target?.closest?.("[data-project-select]");
  if (projectSelectButton) {
    event.preventDefault?.();
    chooseWorkspaceProject(projectSelectButton.dataset.projectSelect || null).catch((error) => {
      showToast(error.message || "项目选择失败。");
    });
    return;
  }
  const fileSelectButton = event.target?.closest?.("[data-file-select]");
  if (fileSelectButton) {
    event.preventDefault?.();
    chooseWorkspaceFile(fileSelectButton.dataset.fileSelect || null, { jumpToAnalysis: Boolean(fileSelectButton.dataset.jumpToAnalysis) }).catch((error) => {
      showToast(error.message || "数据选择失败。");
    });
    return;
  }
  const waveformModeButton = event.target?.closest?.("[data-mode-target]");
  if (waveformModeButton) {
    event.preventDefault?.();
    setWaveformInteractionMode(waveformModeButton.dataset.modeTarget || "browse");
    qs("#eegCanvas")?.focus?.({ preventScroll: true });
    return;
  }
  const waveformControl = event.target?.closest?.("#eegPrevBtn, #eegNextBtn, #eegZoomOutBtn, #eegZoomInBtn, #eegResetBtn");
  if (waveformControl) {
    event.preventDefault?.();
    const run = waveformControl.id === "eegPrevBtn"
      ? shiftEegWindow(-1, EDF_BROWSER_INTERACTION_CONSTANTS.pagePanRatio)
      : waveformControl.id === "eegNextBtn"
        ? shiftEegWindow(1, EDF_BROWSER_INTERACTION_CONSTANTS.pagePanRatio)
        : waveformControl.id === "eegZoomInBtn"
          ? zoomEegWindow(1 / EDF_BROWSER_INTERACTION_CONSTANTS.zoomFactor)
          : waveformControl.id === "eegZoomOutBtn"
            ? zoomEegWindow(EDF_BROWSER_INTERACTION_CONSTANTS.zoomFactor)
            : resetEegPreviewControls();
    Promise.resolve(run).catch((error) => {
      const message = error.message || "波形预览更新失败。";
      eegState.autoPreviewError = message;
      renderEegPreviewEmptyState();
      showToast(message);
    });
    return;
  }
  const previewJump = event.target?.closest?.("[data-preview-jump]");
  if (previewJump) {
    event.preventDefault?.();
    const target = previewJump.dataset.previewJump;
    const selector = target === "reference"
      ? "#presetPrepReference"
      : target === "bad-channel"
        ? '[data-ia-action="mark-bad-channel"]'
        : "#segmentStart";
    const node = qs(selector);
    node?.scrollIntoView?.({ behavior: "smooth", block: "center" });
    window.setTimeout(() => node?.focus?.(), 250);
    recordUiAction(`preview-jump:${target}`, "pass", "已定位到对应预处理控件。");
    return;
  }
  const genericModalButton = event.target?.closest?.("[data-modal]");
  if (genericModalButton) {
    event.preventDefault?.();
    const modalKind = genericModalButton.dataset.modal || "account";
    openModal(modalKind);
    recordUiAction(`modal:${modalKind}`, "pass", "\u8bf4\u660e\u5df2\u6253\u5f00\u3002");
    return;
  }
  const logoutButton = event.target?.closest?.("#logoutBtn, #logoutBtnUserCenter");
  if (logoutButton) {
    event.preventDefault?.();
    logout(true);
    return;
  }
  const viewButton = event.target?.closest?.("[data-view], [data-view-jump]");
  if (viewButton) {
    const targetView = viewButton.dataset.view || viewButton.dataset.viewJump;
    if (targetView) {
      event.preventDefault?.();
      setView(targetView);
      return;
    }
  }
  const submitButton = event.target?.closest?.("#submitBtn");
  if (submitButton) {
    event.preventDefault?.();
    handleSubmitAnalysisClick();
    return;
  }
  const epilepsyActionButton = event.target?.closest?.("[data-epilepsy-action]");
  if (epilepsyActionButton) {
    event.preventDefault?.();
    if (epilepsyActionButton.disabled || epilepsyActionButton.getAttribute("aria-disabled") === "true") {
      const message = epilepsyActionButton.dataset.disabledReason || epilepsyActionButton.title || "该操作当前不可用，请先完成前置步骤。";
      recordUiAction(`epilepsy:${epilepsyActionButton.dataset.epilepsyAction}`, "blocked", message);
      showToast(message);
      return;
    }
    handleInlineEpilepsyAction(epilepsyActionButton.dataset.epilepsyAction, epilepsyActionButton);
    return;
  }
  const realActionButton = event.target?.closest?.("[data-real-action]");
  if (realActionButton) {
    event.preventDefault?.();
    if (realActionButton.disabled || realActionButton.getAttribute("aria-disabled") === "true") {
      const message = realActionButton.title || "\u8be5\u64cd\u4f5c\u5f53\u524d\u4e0d\u53ef\u7528\uff0c\u8bf7\u5148\u5b8c\u6210\u524d\u7f6e\u6b65\u9aa4\u3002";
      recordUiAction(`real:${realActionButton.dataset.realAction}`, "blocked", message);
      showToast(message);
      return;
    }
    if (realActionButton.dataset.busy === "true") return; // double-click guard
    realActionButton.dataset.busy = "true";
    const release = () => { realActionButton.dataset.busy = "false"; };
    Promise.resolve(handleRealAction(realActionButton.dataset.realAction))
      .catch((error) => {
        const message = `${realActionButton.dataset.realAction}未完成：${error?.message || error}`;
        recordUiAction(`real:${realActionButton.dataset.realAction}`, "blocked", message);
        showToast(message);
      })
      .finally(release);
    return;
  }
  const actionButton = event.target?.closest?.("[data-ia-action]");
  if (!actionButton) return;
  const action = actionButton.dataset.iaAction;
  handleIaAction(action).catch((error) => {
    const message = `${action}\u672a\u5b8c\u6210\uff1a${error.message || error}`;
    recordUiAction(`ia:${action}`, "blocked", message);
    showToast(message);
  });
});

document.addEventListener("input", (event) => {
  if (event.target?.matches?.("#segmentStart, #segmentEnd")) {
    markSegmentInputEdited(event.target);
  }
});

document.addEventListener("change", (event) => {
  if (event.target?.matches?.("#segmentStart, #segmentEnd")) {
    markSegmentInputEdited(event.target);
  }
  if (event.target?.matches?.("#real-eeg-file")) {
    handlePendingEegFileSelection();
  }
  if (event.target?.matches?.("#workspaceProjectSelect")) {
    chooseWorkspaceProject(event.target.value || null).catch((error) => {
      showToast(error.message || "项目选择更新失败。");
    });
  }
  if (event.target?.matches?.("#workspaceShowReviewProjects")) {
    state.workspace.showReviewProjects = Boolean(event.target.checked);
    renderProjectDataManagement();
  }
  if (event.target?.matches?.("#workspaceFileSelect, #workspaceFileFocusSelect")) {
    chooseWorkspaceFile(event.target.value || null).catch((error) => {
      showToast(error.message || "数据选择更新失败。");
    });
  }
  if (event.target?.matches?.("#workspacePlanSelect")) {
    chooseWorkspacePlan(event.target.value || null).catch((error) => {
      showToast(error.message || "准备方案选择更新失败。");
    });
  }
  if (event.target?.matches?.("#eegStartInput, #eegWindowInput")) {
    eegState.start = numberFromInput("#eegStartInput", eegState.start);
    eegState.windowSec = numberFromInput("#eegWindowInput", eegState.windowSec);
    syncEegControlsFromState();
    reloadWaveformPreview().catch((error) => showToast(error.message || "波形预览更新失败。"));
  }
  if (event.target?.matches?.("#eegFilterPreviewToggle")) {
    eegState.filterEnabled = Boolean(event.target.checked);
    eegState.showFiltered = Boolean(event.target.checked);
    syncEegControlsFromState();
    if (eegState.showFiltered && !eegState.filteredData) {
      reloadWaveformPreview().catch((error) => showToast(error.message || "滤波预览生成失败。"));
    } else {
      const payload = currentWaveformPayload();
      drawEegWaveformPreview(payload);
      renderEegPreviewMetadata(payload, state.real.artifacts.qc || []);
    }
  }
  if (event.target?.matches?.("#presetPrepLfreq, #presetPrepHfreq, #presetPrepNotch")) {
    eegState.filterLfreq = numberFromInput("#presetPrepLfreq", eegState.filterLfreq);
    eegState.filterHfreq = numberFromInput("#presetPrepHfreq", eegState.filterHfreq);
    eegState.filterNotch = numberFromInput("#presetPrepNotch", eegState.filterNotch);
    renderWaveformWorkbenchStatus();
    if (qs("#eegFilterPreviewToggle")?.checked) {
      reloadWaveformPreview().catch((error) => showToast(error.message || "滤波预览生成失败。"));
    }
  }
  if (event.target?.matches?.("#presetPrepReference, #presetPrepReferenceChannels, #presetPrepBipolarPairs")) {
    renderWaveformWorkbenchStatus();
  }
  if (event.target?.matches?.('input[name="registerMode"]')) {
    handleRegisterModeChange();
  }
});

document.addEventListener("input", (event) => {
  if (event.target?.matches?.("#workspaceProjectSearch")) {
    state.workspace.projectSearch = event.target.value || "";
    renderProjectDataManagement();
  }
  if (event.target?.matches?.("#eegGainInput, #eegChannelInput")) {
    eegState.gain = numberFromInput("#eegGainInput", eegState.gain);
    eegState.visibleChannels = numberFromInput("#eegChannelInput", eegState.visibleChannels);
    setTextIfPresent("#eegGainLabel", `${Number(waveformSensitivityUvPerRow().toFixed(1))} uV/row`);
    setTextIfPresent("#eegChannelLabel", String(eegState.visibleChannels));
    if (eegState.data) {
      const payload = currentWaveformPayload();
      drawEegWaveformPreview(payload);
      renderEegPreviewMetadata(payload, state.real.artifacts.qc || []);
    }
  }
  if (event.target?.matches?.("#eegWindowInput")) {
    eegState.windowSec = numberFromInput("#eegWindowInput", eegState.windowSec);
    setTextIfPresent("#eegWindowLabel", `${eegState.windowSec} s`);
  }
  if (event.target?.matches?.("#eegStartInput")) {
    eegState.start = numberFromInput("#eegStartInput", eegState.start);
    // FIX: 输入起点后自动 debounce 触发波形重载（不再需要失焦/回车）
    if (window.__eegStartReloadTimer) clearTimeout(window.__eegStartReloadTimer);
    window.__eegStartReloadTimer = setTimeout(() => {
      window.__eegStartReloadTimer = null;
      syncEegControlsFromState();
      drawEegOverviewBar();
      reloadWaveformPreview().catch((error) => showToast(error.message || "波形预览更新失败。"));
    }, 400);
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && state.teaching.guideActive) {
    event.preventDefault();
    finishTeachingGuide();
    return;
  }
  if (handleInlineEpilepsyReaderKeydown(event)) return;
  handleWaveformKeydown(event);
});

window.addEventListener("resize", () => {
  if (state.teaching.active && state.teaching.guideActive) renderTeachingOverlay();
  window.clearTimeout(eegState.resizeTimer);
  eegState.resizeTimer = window.setTimeout(() => {
    if (currentWaveformPayload()?.data_uv?.length) redrawCurrentWaveform();
    else drawEegPreviewSkeleton(currentWorkspaceFile());
  }, 120);
});

window.addEventListener("wheel", (event) => {
  if (event.ctrlKey || event.metaKey) event.preventDefault();
}, { passive: false, capture: true });

window.addEventListener("keydown", (event) => {
  if (!(event.ctrlKey || event.metaKey)) return;
  if (["+", "-", "=", "0"].includes(event.key)) event.preventDefault();
}, { capture: true });

if (window.ResizeObserver) {
  const eegResizeObserver = new ResizeObserver(() => {
    window.clearTimeout(eegState.resizeTimer);
    eegState.resizeTimer = window.setTimeout(() => {
      if (currentWaveformPayload()?.data_uv?.length) redrawCurrentWaveform();
      else if (currentWorkspaceFile()?.id) drawEegPreviewSkeleton(currentWorkspaceFile());
    }, 120);
  });
  const observeEegCanvas = () => {
    const target = qs("#eegCanvas")?.parentElement || qs("#eegCanvas");
    if (target) eegResizeObserver.observe(target);
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", observeEegCanvas, { once: true });
  else observeEegCanvas();
}

window.addEventListener("hashchange", () => {
  const hash = window.location.hash.slice(1);
  if (hash && state.role) {
    setView(hash);
  }
});

document.addEventListener("click", (event) => {
  if (event.target?.id === "eegOverviewBar" || event.target?.closest?.("#eegOverviewBar")) {
    handleEegOverviewClick(event);
  }
});

document.addEventListener("submit", (event) => {
  if (event.target?.matches?.("#customerLoginForm")) {
    event.preventDefault();
    window.handleCustomerLoginClick(event);
    return;
  }
  if (event.target?.matches?.("#customerRegisterForm")) {
    event.preventDefault();
    registerCustomer(collectRegisterPayload());
    return;
  }
  if (event.target?.matches?.("#adminLoginForm")) {
    event.preventDefault();
    loginAdmin(qs("#adminEmail")?.value.trim() || "", qs("#adminPassword")?.value || "");
  }
});

const logoutButton = qs("#logoutBtn");
if (logoutButton) {
  logoutButton.addEventListener("click", (event) => {
    event.preventDefault();
    logout(true);
  });
}

async function bootstrapApplication() {
  await restoreSession();
  applyCustomerDemoMode();
  applyCleanVisibleCopy();
}

bootstrapApplication().catch((error) => {
  console.warn("QLanalyser bootstrap failed:", error);
  applyCleanVisibleCopy();
});
})();
