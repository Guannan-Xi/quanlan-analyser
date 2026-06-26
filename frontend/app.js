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

const demoCustomer = {
  name: "\u5ba2\u6237\u8d26\u6237",
  email: "demo.customer@quanlan.cn",
  org: "Quanlan Neuro Lab",
  password: "demo123456",
  registeredAt: "2026-06-20",
};

const state = {
  balance: 0,
  rechargeAmount: 1000,
  paymentMethod: "alipay",
  wallet: null,
  activeTemplate: "ERP \u4e8b\u4ef6\u76f8\u5173\u7535\u4f4d",
  segmentMode: "time",
  role: null,
  tasks: [],
  apiBase: new URLSearchParams(window.location.search).get("api") || DEFAULT_API_BASE,
  real: {
    project: null,
    eegFile: null,
    plan: null,
    tasks: {},
    artifacts: {},
    report: null,
    epochSet: null,
    latestTaskModule: null,
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
  },
  teaching: {
    active: false,
    guideActive: false,
    stepIndex: 0,
    datasetLoaded: false,
    lockedUntilStep: 0,
    demoProjectId: "proj_demo_learning",
    demoFileId: "eeg_demo_teaching_oddball",
  },
};

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
  start: 0,
  windowSec: 10,
  gain: 2,
  visibleChannels: 8,
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
  const canvas = qs("#eegCanvas");
  const ctx = canvas?.getContext?.("2d");
  if (canvas && ctx) ctx.clearRect(0, 0, canvas.width, canvas.height);
  const meta = qs("#eegMeta");
  if (meta) meta.innerHTML = "";
  const events = qs("#eegEvents");
  if (events) events.innerHTML = "";
  const strip = qs("#previewStrip");
  if (strip) strip.innerHTML = "";
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
    title: "教学模式 1/8",
    body: "这里会载入一份练习用 EEG 数据，帮助你从项目、数据准备、分析到报告完整走一遍。",
    require: () => state.teaching.datasetLoaded,
    blocked: "练习数据正在载入，请稍候。",
  },
  {
    view: "dashboard",
    selector: '[data-testid="project-data-crud-panel"]',
    title: "教学模式 2/8",
    body: "先看当前项目和数据。普通模式不会自动放入这份练习数据。",
    require: () => Boolean(state.real.project?.id && state.real.eegFile?.id),
    blocked: "请等待练习项目和样本数据载入完成。",
  },
  {
    view: "analysis",
    selector: '[data-testid="single-file-preview-panel"]',
    title: "教学模式 3/8",
    body: "单击数据后，波形和基础质量信息会自动预览，无需再点运行按钮。",
    require: () => Boolean(state.real.eegFile?.id),
    blocked: "请先选择教学 EEG 数据。",
    onEnter: () => requestAutoQcPreviewForSelectedFile(state.real.eegFile).catch(() => null),
  },
  {
    view: "analysis",
    selector: ".eeg-toolbar",
    title: "教学模式 4/8",
    body: "在波形附近完成坏道、片段和事件修改，所有修改都可以恢复。",
    require: () => Boolean(state.real.eegFile?.id),
    blocked: "请先载入教学 EEG 数据。",
  },
  {
    view: "analysis",
    selector: "#presetPrepReference",
    title: "教学模式 5/8",
    body: "重参考属于预处理，可选择保留原始参考、平均参考、指定通道或双极参考。",
    require: () => Boolean(state.real.eegFile?.id),
    blocked: "请先载入教学 EEG 数据。",
  },
  {
    view: "analysis",
    selector: '[data-real-action="confirm-plan-inline"]',
    title: "教学模式 6/8",
    body: "确认数据准备后，再进入分析方法选择。",
    require: () => Boolean(state.real.eegFile?.id),
    blocked: "请先载入教学 EEG 数据。",
  },
  {
    view: "workflow",
    selector: '[data-testid="analysis-method-scope-panel"]',
    title: "教学模式 7/8",
    body: "这里只放分析方法；重参考和质量检查留在数据准备里。",
    require: () => Boolean(state.real.eegFile?.id),
    blocked: "请先完成教学数据载入。",
  },
  {
    view: "statistics",
    selector: '[data-testid="result-review-workbench"]',
    title: "教学模式 8/8",
    body: "运行分析后，在结果和报告页查看图表、参数记录和边界说明。",
    require: () => Boolean(state.real.eegFile?.id),
    blocked: "请先完成教学数据载入。",
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
  dashboard: "\u9879\u76ee\u5de5\u4f5c\u53f0",
  journey: "\u6d41\u7a0b\u8bf4\u660e",
  analysis: "\u6570\u636e\u51c6\u5907",
  workflow: "\u5206\u6790\u4efb\u52a1",
  paradigms: "\u8303\u5f0f\u5e93",
  statistics: "\u7ed3\u679c\u67e5\u770b",
  publication: "\u62a5\u544a\u4e0b\u8f7d",
  upload: "\u6570\u636e\u6587\u4ef6",
  storage: "\u6570\u636e\u7ba1\u7406",
  billing: "\u8d39\u7528\u4e0e\u5145\u503c",
  invoice: "\u53d1\u7968\u7533\u8bf7",
  inbox: "\u53d1\u7968\u7bb1",
  userCenter: "\u4e2a\u4eba\u4e2d\u5fc3",
  adminDashboard: "\u8fd0\u8425\u9996\u9875",
  adminOperations: "\u4efb\u52a1\u8fd0\u8425",
  adminFinance: "\u8d22\u52a1\u7ba1\u7406",
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
    view: "analysis",
  },
  {
    title: "第 2 步：上传 EEG 数据",
    body: "把 EDF、SET 或 FIF 数据放入当前项目。",
    action: "系统会读取文件信息，并把数据保存在当前项目下。",
    view: "upload",
  },
  {
    title: "第 3 步：确认费用",
    body: "费用与分析分开显示，便于团队核对支出。",
    action: "如本次分析需要扣费，请先确认费用再提交。",
    view: "billing",
  },
  {
    title: "第 4 步：选择分析方法",
    body: "数据准备确认后，再选择实际要运行的分析方法。",
    action: "平台会根据任务类型和数据情况提示合适的方法。",
    view: "journey",
  },
  {
    title: "第 5 步：确认参数",
    body: "先使用推荐的分段、基线和通道设置作为起点。",
    action: "确认基础流程后，再按研究问题调整高级参数。",
    view: "analysis",
  },
  {
    title: "第 6 步：检查数据准备",
    body: "质量检查属于数据准备，分析前应先复核。",
    action: "继续前请确认坏段、标签和参考设置。",
    view: "statistics",
  },
  {
    title: "第 7 步：查看图表和表格",
    body: "分析完成后，可以查看 ERP、PSD 等结果图表。",
    action: "进入报告交付页下载图表、表格和方法说明。",
    view: "publication",
  },
  {
    title: "第 8 步：下载并交付",
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
        <span>09:03 \u8bb0\u5f55\u4e86\u5145\u503c\uff0c\u4f59\u989d\u5df2\u66f4\u65b0\u3002</span>
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
        <span>也可以先使用教学样本熟悉流程，再切换到自己的项目数据。</span>
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
      const balanceText = String(qs("#balanceSide")?.textContent || "").replace(/[^\d.]/g, "");
      const balance = Number(balanceText || state.balance || 0);
      return `
        <div class="audit-list">
          <span><b>\u8d26\u53f7\u663e\u793a\uff1a</b>${escapeHtml(customer.name || "\u5ba2\u6237\u8d26\u53f7")}</span>
          <span><b>\u90ae\u7bb1\uff1a</b>${escapeHtml(customer.email || "\u672a\u7ed1\u5b9a\u90ae\u7bb1")}</span>
          <span><b>\u673a\u6784\uff1a</b>${escapeHtml(customer.org || "Quanlan Neuro Lab")}</span>
          <span><b>\u5f53\u524d\u4f59\u989d\uff1a</b>${money(balance)}</span>
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


function renderWaveformWorkbenchStatus(message = "") {
  const target = qs("#waveformWorkbenchStatus");
  if (!target) return;
  const selected = normalizeSegmentRange(eegState.selectedSegment?.start_sec, eegState.selectedSegment?.end_sec);
  const start = Number(eegState.start || 0);
  const windowSec = Number(eegState.windowSec || 10);
  const referenceSelect = qs("#presetPrepReference");
  const referenceLabel = referenceSelect?.selectedOptions?.[0]?.textContent?.trim() || "平均参考";
  const filterState = Boolean(eegState.filterEnabled || eegState.showFiltered) ? "滤波预览开启" : "原始波形";
  const pieces = [
    ["当前窗口", `${start.toFixed(1)}-${(start + windowSec).toFixed(1)} s`],
    ["显示", `${Number(eegState.visibleChannels || 8)} 通道 / 增益 ${Number(eegState.gain || 2)}x`],
    ["选段", selected ? `${selected.start_sec.toFixed(2)}-${selected.end_sec.toFixed(2)} s` : "拖拽波形选择片段"],
    ["滤波", filterState],
    ["参考", referenceLabel],
    ["坏道草稿", `${prepEditState.badChannels.length} 条，可恢复 ${prepEditState.restoredBadChannels.length} 条`],
    ["片段草稿", `剔除 ${prepEditState.excludedSegments.length} 段，恢复 ${prepEditState.restoredSegments.length} 段`],
  ];
  target.innerHTML = [
    message ? `<strong>${escapeHtml(cleanRuntimeMessage(message))}</strong>` : "",
    ...pieces.map(([label, value]) => `<span><b>${escapeHtml(label)}</b>${escapeHtml(value)}</span>`),
    `<em>预处理只生成数据准备记录，不改写原始 EEG。</em>`,
  ].filter(Boolean).join("");
}

function hasConfirmedPlan() {
  const plan = state.real.plan;
  return Boolean(plan && !plan.is_default && plan.status === "confirmed" && plan.id && Number.isFinite(Number(plan.revision)));
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

function currentWorkspaceFile() {
  const selectedId = qs("#workspaceFileFocusSelect")?.value || qs("#workspaceFileSelect")?.value || state.workspace.selectedFileId;
  const selected = (state.workspace.files || []).find((item) => item.id === selectedId);
  const file = state.real.eegFile || selected || null;
  if (file?.id) {
    state.real.eegFile = file;
    state.workspace.selectedFileId = file.id;
  }
  return file;
}

function currentWorkspaceProject() {
  const selectedId = state.workspace.selectedProjectId;
  const selected = (state.workspace.projects || []).find((item) => item.id === selectedId);
  const project = state.real.project || selected || null;
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
  const file = (state.workspace.files || []).find((item) => item.id === fileId) || null;
  state.real.eegFile = file;
  state.real.plan = null;
  state.real.epochSet = null;
  clearEegPreviewState();
  await refreshProjectWorkspace();
  if (jumpToAnalysis) setView("analysis");
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
  overlay.setAttribute("aria-modal", "true");
  overlay.setAttribute("aria-live", "polite");
  overlay.innerHTML = `
    <div class="teaching-mask" data-teaching-action="next"></div>
    <div class="teaching-spotlight" aria-hidden="true"></div>
    <section class="teaching-card" data-testid="teaching-step-card">
      <div class="teaching-card-head">
        <span class="teaching-kicker">教学数据</span>
        <button class="icon-btn" type="button" data-teaching-action="close" title="结束教学"><i data-lucide="x"></i></button>
      </div>
      <h2 id="teachingStepTitle">教学模式</h2>
      <p id="teachingStepBody">正在准备教学步骤。</p>
      <div class="teaching-progress" aria-hidden="true"><span></span></div>
      <div class="teaching-actions">
        <button class="ghost-btn" type="button" data-teaching-action="prev"><i data-lucide="chevron-left"></i><span>上一步</span></button>
        <button class="primary-btn" type="button" data-teaching-action="next"><span>下一步</span><i data-lucide="chevron-right"></i></button>
        <button class="ghost-btn" type="button" data-teaching-action="close"><i data-lucide="x"></i><span>结束教学</span></button>
      </div>
      <small class="teaching-boundary">教学数据为合成 EEG，仅用于熟悉流程，不作为科学结论。</small>
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
    button.dataset.teachingAction = state.teaching.active ? "exit" : "start";
    button.classList.toggle("active", Boolean(state.teaching.active));
    button.setAttribute("aria-pressed", state.teaching.active ? "true" : "false");
    const label = button.querySelector("span");
    if (label) label.textContent = state.teaching.active ? "\u8fd4\u56de\u666e\u901a\u6a21\u5f0f" : "\u6559\u5b66\u6a21\u5f0f";
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
    banner.innerHTML = `<strong>\u6559\u5b66\u6a21\u5f0f</strong><span>\u4f60\u6b63\u5728\u4f7f\u7528\u5185\u7f6e\u8111\u7535\u6570\u636e\u8bd5\u8dd1\u6d41\u7a0b\uff0c\u65e0\u9700\u4e0a\u4f20\u6570\u636e\uff1b\u6559\u5b66\u6570\u636e\u4e0d\u53ef\u5220\u9664\uff0c\u7ed3\u679c\u4ec5\u7528\u4e8e\u5b66\u4e60\u64cd\u4f5c\u3002</span><button class="ghost-btn mini" type="button" data-teaching-action="guide"><i data-lucide="route"></i><span>\u91cd\u65b0\u6253\u5f00\u5f15\u5bfc</span></button>`;
    banner.hidden = false;
  } else if (banner) {
    banner.hidden = true;
  }
  if (window.lucide) window.lucide.createIcons();
}

async function startTeachingMode(options = {}) {
  const { showGuide = true } = options;
  state.teaching.active = true;
  state.teaching.guideActive = Boolean(showGuide);
  state.teaching.stepIndex = 0;
  state.teaching.datasetLoaded = false;
  ensureTeachingOverlay();
  setRealStatus("正在载入教学数据。", "info");
  try {
    const dataset = await apiJson("/lab/demo/dataset");
    const project = dataset?.project || null;
    const file = dataset?.file || null;
    if (project?.id) {
      state.real.project = project;
      state.workspace.selectedProjectId = project.id;
    }
    if (file?.id) {
      state.real.eegFile = { ...file, teaching_demo: true };
      state.workspace.selectedFileId = file.id;
      eegState.selectedFilePreviewId = "";
    }
    state.teaching.datasetLoaded = Boolean(project?.id && file?.id);
    await refreshProjectWorkspace();
    state.real.project = state.workspace.projects.find((item) => item.id === project?.id) || project || state.real.project;
    state.real.eegFile = state.workspace.files.find((item) => item.id === file?.id) || state.real.eegFile || file;
    state.workspace.selectedProjectId = state.real.project?.id || state.workspace.selectedProjectId;
    state.workspace.selectedFileId = state.real.eegFile?.id || state.workspace.selectedFileId;
    setView("dashboard");
    await ensureTeachingSandboxReady({ preview: false });
    recordUiAction("teaching:start", "pass", "教学模式已载入合成 EEG 数据。", {
      project_id: state.real.project?.id,
      file_id: state.real.eegFile?.id,
      demo: true,
    });
  } catch (error) {
    state.teaching.datasetLoaded = false;
    recordUiAction("teaching:start", "blocked", `教学数据载入失败：${error.message || error}`);
  }
  applyTeachingModeChrome();
  if (state.teaching.guideActive) renderTeachingOverlay();
  else hideTeachingGuideOverlay();
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
  recordUiAction("teaching:close", "pass", "教学模式已结束。");
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
  const owner = String(project?.owner_id || project?.owner_user_id || project?.created_by || project?.metadata_json?.owner_id || "").toLowerCase();
  if (owner === "pilot-user" || owner === "pilot_user" || owner === "demo-user") return true;
  if (text.includes("qlanalyser pilot project")) return true;
  if (text.includes("pilot generated") || text.includes("pilot-generated")) return true;
  if (text.includes("我的分析项目") && (owner.includes("pilot") || text.includes("pilot"))) return true;
  return false;
}

function isReviewOrInternalProject(project) {
  const text = projectSearchText(project);
  return [
    "acceptance",
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
    const disabled = archived || protectedTeaching;
    button.disabled = disabled;
    button.setAttribute("aria-disabled", disabled ? "true" : "false");
    button.title = protectedTeaching ? teachingProtectedMessage() : (archived ? "归档项目为只读；如需修改，请先恢复到普通项目。" : "");
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
  return "内置教学数据用于练习，不能删除、归档或改名。";
}

function scopedProjectFiles(project, files = []) {
  const rows = project?.id ? (files || []).filter((item) => item.project_id === project.id) : [];
  if (state.teaching.active && isTeachingDemoProject(project)) {
    return rows.filter((item) => isTeachingDemoFile(item));
  }
  return rows;
}

function isArchivedProject(project) {
  const rawStatus = String(project?.status || "").toLowerCase();
  return ["archived", "archive", "deleted", "delete"].includes(rawStatus);
}

function projectUpdatedTime(project) {
  const value = Date.parse(project?.updated_at || project?.created_at || "");
  return Number.isFinite(value) ? value : 0;
}

function projectFileCount(project, files = []) {
  if (!project?.id) return 0;
  return Number.isFinite(Number(project.data_count))
    ? Number(project.data_count)
    : files.filter((item) => item.project_id === project.id).length;
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
    if (selected?.id) filtered = [selected, ...filtered];
  }
  return filtered;
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
  const planReady = hasConfirmedPlan();
  const planTitle = planReady
    ? "数据准备已确认，可以继续分析"
    : "请先完成数据准备并确认方案";
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
  setRealActionEnabled("run-psd", planReady, planTitle);
  setRealActionEnabled("run-erp", planReady, planReady ? "可运行 ERP；若事件标记缺失，系统会给出具体提示" : planTitle);
  setRealActionEnabled("run-tfr", planReady, planReady ? "可运行时频分析；若事件或分段条件不足，系统会给出具体提示" : planTitle);
  setRealActionEnabled("run-multitaper-psd", planReady, planReady ? "数据准备已确认，可以运行 Multitaper PSD" : "请先完成数据准备并确认方案");
  setRealActionEnabled("run-multitaper-tfr", planReady, planReady ? "可运行 Multitaper TFR；若事件或分段条件不足，系统会给出具体提示" : "请先完成数据准备并确认方案");
  setRealActionEnabled("run-reference-csd", planReady, planReady ? "数据准备已确认，可以运行 CSD 电流源密度计算" : "请先完成数据准备并确认方案");
  setRealActionEnabled("run-pac", planReady, planReady ? "可运行耦合分析；若事件或时间窗条件不足，系统会给出具体提示" : "请先完成数据准备并确认方案");
  setRealActionEnabled("run-connectivity", planReady, planReady ? "数据准备已确认，可以运行连接性分析" : "请先完成数据准备并确认方案");
  const task = latestAnalysisTask();
  setRealActionEnabled("create-report", Boolean(task), task ? "基于最近一次完成的分析生成报告" : "请先完成一个分析任务");
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
    const protectedTeaching = Boolean(state.teaching.active && (isTeachingDemoProject(state.real.project) || isTeachingDemoFile(state.real.eegFile)));
    protectedNote.hidden = !protectedTeaching;
  }
  let nextActions = ["create-project"];
  if (hasProject && (!hasFile || hasPendingUpload)) nextActions = ["upload-eeg"];
  if (hasFile && !planReady) nextActions = ["run-qc-preview-inline", "run-metadata-qc-inline", "confirm-plan-inline"];
  if (planReady && !state.real.epochSet) nextActions = ["save-epoch-set"];
  if (planReady && !state.real.epochSet && !task) nextActions = ["run-psd", "run-multitaper-psd", "run-reference-csd", "run-connectivity"];
  if (planReady && state.real.epochSet && !task) nextActions = ["run-psd", "run-erp", "run-tfr", "run-multitaper-psd", "run-multitaper-tfr", "run-reference-csd", "run-pac", "run-connectivity"];
  if (task && !state.real.report) nextActions = ["create-report"];
  if (state.real.report) nextActions = [];
  markRealNextActions(nextActions);
  renderDisabledReason("confirm-plan-inline", "#prepPrimaryReason");
  renderDisabledReason("run-psd", "#analysisPrimaryReason");
  renderDisabledReason("create-report", "#reportPrimaryReason");
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
  return session.accountId || session.account_id || getStoredCustomer().id || "demo-customer";
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
    empty.innerHTML = `<strong>等待选择 EEG 数据</strong><span>请先在左侧数据队列选择文件，或返回数据管理上传到当前项目。</span>`;
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

function renderWaveformInteractionHint(message = "") {
  const target = qs("#eegEvents");
  if (!target) return;
  const selected = normalizeSegmentRange(eegState.selectedSegment?.start_sec, eegState.selectedSegment?.end_sec);
  const selectedText = selected ? `当前选区 ${selected.start_sec.toFixed(2)}-${selected.end_sec.toFixed(2)} s` : "拖拽波形可选择片段";
  const excludedText = prepEditState.excludedSegments.length ? `已剔除 ${prepEditState.excludedSegments.length} 段` : "尚未剔除片段";
  target.innerHTML = `<span>${escapeHtml(message || selectedText)}</span><span>${escapeHtml(excludedText)}</span><span>滚轮平移，Ctrl + 滚轮缩放</span>`;
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
  const maxStart = Math.max(0, Number(file?.duration_sec || 0) - Number(eegState.windowSec || 10));
  eegState.start = Math.max(0, Math.min(Number(eegState.start || 0), Number.isFinite(maxStart) ? maxStart : Number(eegState.start || 0)));
  eegState.windowSec = Math.max(2, Math.min(30, Number(eegState.windowSec || 10)));
  eegState.visibleChannels = Math.max(1, Math.min(64, Math.round(Number(eegState.visibleChannels || 8))));
  eegState.gain = Math.max(0.5, Math.min(8, Number(eegState.gain || 2)));
  if (startInput) {
    startInput.value = Number(eegState.start || 0).toFixed(1).replace(/\.0$/, "");
    if (file?.duration_sec) startInput.max = String(Math.max(0, Number(file.duration_sec) - Number(eegState.windowSec || 10)));
  }
  if (windowInput) windowInput.value = String(eegState.windowSec);
  if (gainInput) gainInput.value = String(eegState.gain);
  if (channelInput) channelInput.value = String(eegState.visibleChannels);
  if (filterToggle) filterToggle.checked = Boolean(eegState.showFiltered || eegState.filterEnabled);
  setTextIfPresent("#eegWindowLabel", `${eegState.windowSec} s`);
  setTextIfPresent("#eegGainLabel", `${eegState.gain}x`);
  setTextIfPresent("#eegChannelLabel", String(eegState.visibleChannels));
  renderWaveformWorkbenchStatus();
}

function buildQcPreviewParametersFromUi(options = {}) {
  const file = currentWorkspaceFile();
  eegState.start = Math.max(0, Number(numberFromInput("#eegStartInput", eegState.start || 0)) || 0);
  eegState.windowSec = Math.max(2, Math.min(30, Number(numberFromInput("#eegWindowInput", eegState.windowSec || 10)) || 10));
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

function shiftEegWindow(direction = 1) {
  const step = Math.max(1, Number(eegState.windowSec || 10) / 2);
  eegState.start = Math.max(0, Number(eegState.start || 0) + step * direction);
  syncEegControlsFromState();
  return reloadWaveformPreview();
}

function zoomEegWindow(factor = 1) {
  const nextWindow = Math.max(2, Math.min(30, Math.round(Number(eegState.windowSec || 10) * factor)));
  eegState.windowSec = nextWindow;
  syncEegControlsFromState();
  return reloadWaveformPreview();
}

function resetEegPreviewControls() {
  eegState.start = 0;
  eegState.windowSec = 10;
  eegState.gain = 2;
  eegState.visibleChannels = 8;
  eegState.showFiltered = false;
  eegState.filterEnabled = false;
  syncEegControlsFromState();
  return reloadWaveformPreview();
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
  const selectedProjectId = state.workspace.selectedProjectId || null;
  const project = selectedProjectId
    ? state.workspace.projects.find((item) => item.id === selectedProjectId) || (state.real.project?.id === selectedProjectId ? state.real.project : null)
    : null;
  const projectFiles = scopedProjectFiles(project, state.workspace.files);
  const selectedFileId = project?.id ? state.workspace.selectedFileId || null : null;
  const file = project?.id
    ? (selectedFileId ? projectFiles.find((item) => item.id === selectedFileId) : null)
      || (state.real.eegFile?.project_id === project.id ? state.real.eegFile : null)
    : null;
  state.real.project = project;
  state.real.eegFile = file;
  if (file?.id) {
    const [plans, epochSets] = await Promise.all([
      apiJson(`/data-preparation/plans?input_file_id=${encodeURIComponent(file.id)}`),
      apiJson(`/eeg/files/${encodeURIComponent(file.id)}/epoch-sets`),
    ]);
    state.workspace.plans = Array.isArray(plans) ? plans : [];
    state.workspace.epochSets = Array.isArray(epochSets) ? epochSets : [];
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
  renderProjectDataManagement();
  renderRealPlanState();
  renderRealFlowSummary();
  updateRealActionGate();
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
  return files.map((item) => {
    const status = fileStatusLabelReadable(item);
    const shortId = String(item.id || "").slice(-6);
    const suffix = [status, shortId ? `#${shortId}` : ""].filter(Boolean).join(" · ");
    return `<option value="${escapeHtml(item.id)}">${escapeHtml(eegFileDisplayName(item))}${suffix ? ` · ${escapeHtml(suffix)}` : ""}</option>`;
  }).join("");
}

async function ensureRealProject() {
  if (state.real.project) return state.real.project;
  const projectName = qs("#realProjectName")?.value.trim() || "我的研究项目";
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
  const uploaded = await apiJson(`/eeg/upload?project_id=${encodeURIComponent(project.id)}`, {
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
      module_scope: ["qc", "psd", "erp", "tfr", "pac", "reference_csd"],
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
        tfr: { status: "allowed_after_epoch_review", reasons: [] },
        pac: { status: "allowed_after_epoch_review", reasons: [] },
      },
    }),
  });
  state.real.plan = plan;
  renderRealPlanState();
    await refreshProjectWorkspace();
return plan;
}

async function ensureTeachingSandboxReady(options = {}) {
  if (!state.teaching.active) return null;
  if (!state.real.project?.id || !state.real.eegFile?.id || !state.teaching.datasetLoaded) {
    await startTeachingMode({ showGuide: false });
  }
  const eegFile = currentWorkspaceFile();
  if (!eegFile?.id) throw new Error("\u6559\u5b66\u6a21\u5f0f\u672a\u80fd\u52a0\u8f7d\u5185\u7f6e\u8111\u7535\u6570\u636e\uff0c\u8bf7\u91cd\u65b0\u8fdb\u5165\u6559\u5b66\u6a21\u5f0f\u3002");
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
  const parameters = {};
  Object.assign(parameters, collectPresetParameters(moduleName));
  if (plan && !plan.is_default && plan.id && Number.isFinite(Number(plan.revision))) {
    parameters.data_preparation_plan_id = plan.id;
    parameters.data_preparation_revision = Number(plan.revision);
    parameters.data_preparation_contract_version = plan.schema_version || "qlanalyser-data-preparation-v0.2";
  }
  return parameters;
}

async function runRealTask(moduleName, workflowId) {
  if (state.teaching.active) await ensureTeachingSandboxReady({ preview: false });
  const project = await ensureRealProject();
  const eegFile = currentWorkspaceFile() || (state.teaching.active ? null : await uploadRealEeg());
  if (!eegFile?.id) throw new Error(state.teaching.active ? "\u6559\u5b66\u6a21\u5f0f\u672a\u52a0\u8f7d\u5185\u7f6e\u8111\u7535\u6570\u636e\uff0c\u8bf7\u91cd\u65b0\u8fdb\u5165\u6559\u5b66\u6a21\u5f0f\u3002" : "\u8bf7\u5148\u4e0a\u4f20\u6216\u9009\u62e9 EEG \u6570\u636e\u3002");
  const requiresPlan = ["psd", "erp", "tfr", "multitaper_psd", "multitaper_tfr", "reference_csd", "pac", "connectivity"].includes(moduleName);
  const requiresEpochSet = ["erp", "tfr", "multitaper_tfr", "pac"].includes(moduleName);
  const plan = state.real.plan || await getCurrentDataPreparationPlan(eegFile);
  const planContract = plan?.schema_version || plan?.data_preparation_contract_version || "qlanalyser-data-preparation-v0.2";
  if (requiresPlan && (!plan || plan.is_default || plan.status !== "confirmed" || !plan.id || !Number.isFinite(Number(plan.revision)) || planContract !== "qlanalyser-data-preparation-v0.2")) {
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
  const task = await apiJson("/tasks", {
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
  state.real.tasks[moduleName] = task;
  state.real.latestTaskModule = moduleName;
  const artifacts = await fetchTaskArtifacts(task.id);
  state.real.artifacts[moduleName] = artifacts;
  setRealStatus(`${moduleDisplayName(moduleName)} 已完成，结果已更新。`, "ok");
  renderRealResultReview();
  renderRealDelivery();
  return task;
}
async function createRealReport() {
  const task = latestAnalysisTask();
  if (!task) throw new Error("请先完成至少一个分析任务，再生成交付报告。");
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
  setRealStatus("交付报告已生成，可在报告交付页下载。", "ok");
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
    review.innerHTML = `
      <article class="result-item result-empty-state">
        <strong>还没有分析结果</strong>
        <span>先完成数据准备，再从 8 项分析方法中选择一种开始。结果会在这里按模块显示。</span>
      </article>
    `;
  }

  const delivery = qs("#realDeliveryLinks");
  if (delivery && !delivery.querySelector("[data-report-id]")) {
    delivery.innerHTML = `
      <article class="result-item result-empty-state" data-report-state="empty">
        <strong>还没有可下载的报告</strong>
        <span>先完成分析并生成交付报告，下载入口才会出现在这里。</span>
      </article>
    `;
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
  const grouped = new Map();
  artifacts.forEach((artifact) => {
    const href = artifactDownloadUrl(artifact);
    if (!href) return;
    const label = readableArtifactLabel(artifact);
    const item = grouped.get(label) || { label, href, count: 0 };
    item.count += 1;
    grouped.set(label, item);
  });
  return Array.from(grouped.values());
}

function renderArtifactDetailLinks(artifacts = []) {
  const items = artifactDetailItems(artifacts);
  if (!items.length) return "<span>结果文件生成中或暂无可下载文件。</span>";
  return items.map((item) => `
    <a class="artifact-link-chip" href="${escapeHtml(item.href)}" target="_blank" rel="noreferrer">
      <span>${escapeHtml(item.label)}</span>
      <small>${item.count > 1 ? `含 ${item.count} 个文件` : "1 个文件"}</small>
    </a>
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

function renderRealResultReview() {
  const target = qs("#realResultReview");
  if (!target) return;
  const modules = Object.entries(state.real.tasks || {}).filter(([, task]) => task?.id);
  if (!modules.length) {
    target.innerHTML = "<p>尚未生成分析结果。请先完成数据准备，再开始 PSD 或 ERP 分析。</p>";
    return;
  }
  const resultItems = modules.map(([moduleName, task]) => {
    const artifacts = state.real.artifacts?.[moduleName] || [];
    const links = renderArtifactDetailLinks(artifacts);
    return `
      <article class="result-item" data-result-module="${escapeHtml(moduleName)}">
        <strong>${escapeHtml(moduleDisplayName(moduleName))} - ${escapeHtml(taskStatusLabelReadable(task))}</strong>
        <span>${escapeHtml(artifactSummaryLabel(artifacts))}</span>
        ${renderEvidenceBadges(moduleName, task, artifacts)}
        <details class="technical-details artifact-details">
          <summary>查看结果文件明细</summary>
          <div class="artifact-link-grid">${links}</div>
        </details>
      </article>
    `;
  }).join("");
  const task = latestAnalysisTask();
  const reportAction = task && !state.real.report
    ? `
      <article class="result-item" data-result-action="report">
        <strong>下一步：生成交付报告</strong>
        <span>基于当前完成的分析任务，整理图表、表格、方法记录和复现信息。</span>
        <div class="real-actions compact-actions">
          <button class="primary-btn" type="button" data-real-action="create-report"><i data-lucide="file-output"></i><span>生成交付报告</span></button>
        </div>
      </article>
    `
    : "";
  target.innerHTML = `${resultItems}${reportAction}`;
  if (window.lucide) window.lucide.createIcons();
}

function addReportDownload(report) {
  const target = qs("#realDeliveryLinks") || qs("#realDelivery");
  if (!target || !report?.id) return;
  const packageUrl = `${state.apiBase}/reports/${encodeURIComponent(report.id)}/package`;
  const htmlUrl = `${state.apiBase}/reports/${encodeURIComponent(report.id)}/html`;
  target.innerHTML = `
    <article class="result-item" data-report-id="${escapeHtml(report.id)}">
      <strong>报告已生成</strong>
      <span>下载完整交付材料，包含图表、表格、方法记录和复现信息。</span>
      <div class="real-actions compact-actions">
        <a class="primary-btn" data-report-download="package" data-report-id="${escapeHtml(report.id)}" href="${escapeHtml(packageUrl)}">下载完整报告</a>
        <a class="ghost-btn" data-report-download="html" data-report-id="${escapeHtml(report.id)}" href="${escapeHtml(htmlUrl)}">在线预览</a>
      </div>
    </article>
  `;
}

function renderRealDelivery() {
  const target = qs("#realDeliveryLinks") || qs("#realDelivery");
  if (!target) return;
  if (state.real.report) {
    addReportDownload(state.real.report);
    return;
  }
  const task = latestAnalysisTask();
  target.innerHTML = `
    <article class="result-item" data-report-state="empty">
      <strong>\u6682\u65e0\u53ef\u4e0b\u8f7d\u62a5\u544a</strong>
      <span>${task?.id
        ? "已有完成的分析任务，请先在分析任务页点击“生成交付报告”。"
        : "请先完成数据准备并开始至少一个分析任务，然后生成交付报告。"}</span>
      <div class="real-actions compact-actions">
        <button class="ghost-btn" type="button" data-view-jump="${task?.id ? "workflow" : "analysis"}">
          <i data-lucide="${task?.id ? "file-output" : "sliders-horizontal"}"></i>
          <span>${task?.id ? "\u53bb\u751f\u6210\u62a5\u544a" : "\u53bb\u6570\u636e\u51c6\u5907"}</span>
        </button>
      </div>
    </article>
  `;
  if (window.lucide) window.lucide.createIcons();
}

function applyCustomerDemoMode() {
  const mode = new URLSearchParams(window.location.search).get("customer_demo");
  if (!mode) return;
  const normalizedMode = String(mode).toLowerCase();
  if (["login", "auto", "demo"].includes(normalizedMode)) {
    fillDemoCustomerCredentials();
    setLoginMessage("已填入本地审核测试账号，可直接点击登录进入工作台。", "info");
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
    "create-report": "生成交付报告",
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
    } else if (action === "create-report") result = await createRealReport();
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
    const message = `${actionNames[action] || action}\u672a\u5b8c\u6210\uff1a${error.message || error}`;
    recordUiAction(`real:${action}`, "blocked", message);
    showToast(message);
    return null;
  }
}

function handleSubmitAnalysisClick() {
  const planReady = hasConfirmedPlan();
  if (!planReady) {
    const message = "请先完成数据准备确认和事件分段，再提交分析任务。";
    recordUiAction("real:submit-analysis", "blocked", message);
    showToast(message);
    setView("analysis");
    return;
  }
  recordUiAction("real:submit-analysis", "pass", "分析入口已就绪，请在当前可用方法中选择要运行的分析。");
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
    if (project?.id && isTeachingDemoProject(project)) {
      const message = teachingProtectedMessage();
      recordUiAction(`ia:${action}`, "blocked", message, { project_id: project.id, persistence: "protected_teaching_dataset" });
      showToast(message);
      return;
    }
    if (project?.id && isArchivedProject(project)) {
      const message = "归档项目为只读，不能直接删除。";
      recordUiAction(`ia:${action}`, "blocked", message, { project_id: project.id, status: project.status, persistence: "not_mutated" });
      showToast(message);
      return;
    }
    const message = "\u9879\u76ee\u5220\u9664\u662f\u9ad8\u98ce\u9669\u64cd\u4f5c\uff0c\u9700\u8981\u786e\u8ba4\u5bf9\u8bdd\u6846\u4e0e\u5ba1\u8ba1\u8bb0\u5f55\uff0c\u5f53\u524d\u672a\u5220\u9664\u9879\u76ee\u3002";
    recordUiAction(`ia:${action}`, "blocked", project?.id ? message : noProjectMessage, { project_id: project?.id || null, persistence: "not_mutated" });
    showToast(project?.id ? message : noProjectMessage);
    return;
  }

  if (action === "rename-data") {
    if (!file?.id) {
      recordUiAction(`ia:${action}`, "blocked", noFileMessage);
      showToast(noFileMessage);
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
  const selectedSegment = normalizeSegmentRange(eegState.selectedSegment?.start_sec, eegState.selectedSegment?.end_sec);
  const start = Number(selectedSegment?.start_sec ?? qs("#segmentStart")?.value ?? 30);
  const end = Number(selectedSegment?.end_sec ?? qs("#segmentEnd")?.value ?? 35);
  if (action === "select-prep-data") {
    message = `已选择 ${currentFileName}，预览会自动刷新。`;
  } else if (action === "exclude-segment") {
    const segment = {
      id: `segment_${Date.now()}`,
      file_id: file?.id || "",
      start_sec: Number.isFinite(start) ? start : 30,
      end_sec: Number.isFinite(end) && end > start ? end : (Number.isFinite(start) ? start + 5 : 35),
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
      file_id: file?.id || "",
      previous_text: null,
      text: "运动伪迹 / 需要复核",
      target: `${Number.isFinite(start) ? start.toFixed(1) : "30.0"} s`,
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
      message = "当前没有可编辑的标签，已先记录一条复核标签。";
      prepEditState.labels.push({
        id: `label_${Date.now()}`,
        file_id: file?.id || "",
        previous_text: null,
        text: "需要复核",
        target: `${Number.isFinite(start) ? start.toFixed(1) : "30.0"} s`,
        status: "active",
        reversible: true,
      });
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

async function fetchTaskArtifacts(taskId) {
  if (!taskId) return [];
  try {
    return await apiJson(`/tasks/${encodeURIComponent(taskId)}/artifacts`);
  } catch (error) {
    return [];
  }
}

function showToast(message) {
  const toast = qs("#toast");
  if (!toast) return;
  toast.textContent = cleanRuntimeMessage(message);
  toast.classList.add("show");
  window.setTimeout(() => toast.classList.remove("show"), 2400);
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
    return JSON.parse(localStorage.getItem(CUSTOMER_KEY)) || demoCustomer;
  } catch {
    return demoCustomer;
  }
}

function saveCustomer(profile) {
  localStorage.setItem(CUSTOMER_KEY, JSON.stringify({ ...getStoredCustomer(), ...profile }));
}

function validateEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function userFacingAuthMessage(message) {
  const text = String(message || "");
  const lower = text.toLowerCase();
  if (!text.trim()) return "\u64cd\u4f5c\u672a\u5b8c\u6210\uff0c\u8bf7\u68c0\u67e5\u4fe1\u606f\u540e\u91cd\u8bd5\u3002";
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
}

function switchLoginTab(tab) {
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
  localStorage.removeItem(AUTH_KEY);
  sessionStorage.removeItem(AUTH_KEY);
}

function showLoginScreen(message = "", type = "info") {
  state.role = null;
  const loginScreen = qs("#loginScreen");
  const appShell = qs("#appShell");
  if (loginScreen) loginScreen.hidden = false;
  if (appShell) appShell.hidden = true;
  if (window.location.hash) {
    history.replaceState(null, "", `${window.location.pathname}${window.location.search}`);
  }
  switchLoginTab("customerLogin");
  if (message) setLoginMessage(message, type);
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
    if (qs("#balanceMain")) qs("#balanceMain").textContent = Number(wallet.balance_credits ?? wallet.balance ?? 0).toFixed(2);
    if (qs("#balanceSide")) qs("#balanceSide").textContent = `\u4f59\u989d ${Number(wallet.balance_credits ?? wallet.balance ?? 0).toFixed(2)}`;
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
  const amount = Number(state.rechargeAmount || 1000);
  const method = state.paymentMethod || "alipay";
  try {
    const order = await apiJson("/billing/recharge", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        account_id: currentAccountId(),
        amount_credits: amount,
        payment_method: method,
        note: "Local review sandbox recharge; no real payment.",
      }),
    });
    const confirmed = await apiJson(`/billing/recharge/${encodeURIComponent(order.id)}/confirm`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        provider_trade_no: `sandbox_${Date.now()}`,
        status: "paid",
        operator_note: "Confirmed by visible UI sandbox button.",
      }),
    });
    await refreshWallet();
    const message = `沙盒充值已完成：${money(confirmed.amount_credits || amount)}，不涉及真实资金。`;
    setTextIfPresent("#rechargeNotice span", message);
    recordUiAction("billing:recharge", "pass", message, { order_id: confirmed.id, amount, method, persistence: "backend_billing" });
    showToast(message);
    return confirmed;
  } catch (error) {
    const message = `沙盒充值未完成：${error.message || error}`;
    setTextIfPresent("#rechargeNotice span", message);
    recordUiAction("billing:recharge", "blocked", message);
    showToast(message);
    return null;
  }
}

async function handleInvoiceSubmit() {
  const title = qs("#invoiceTitleInput")?.value.trim() || "QLanalyser 沙盒发票";
  const taxNumber = qs("#invoiceTaxInput")?.value.trim() || "";
  const amount = Number(qs("#invoiceAmountInput")?.value || 0);
  const email = qs("#invoiceEmailInput")?.value.trim() || getStoredCustomer().email || demoCustomer.email;
  if (!title || !email || amount <= 0) {
    const message = "请填写发票抬头、接收邮箱和有效金额后再提交。";
    setTextIfPresent("#invoiceNotice span", message);
    recordUiAction("invoice:submit", "blocked", message);
    showToast(message);
    return null;
  }
  try {
    const invoice = await apiJson("/invoices", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        account_id: currentAccountId(),
        invoice_title: title,
        tax_number: taxNumber,
        amount_credits: amount,
        recipient_email: email,
        note: "Local review sandbox invoice request.",
      }),
    });
    const message = `沙盒发票申请已提交：${invoice.id}。`;
    setTextIfPresent("#invoiceNotice span", message);
    recordUiAction("invoice:submit", "pass", message, { invoice_id: invoice.id, persistence: "backend_invoice_request" });
    showToast(message);
    return invoice;
  } catch (error) {
    const message = `沙盒发票申请未完成：${error.message || error}`;
    setTextIfPresent("#invoiceNotice span", message);
    recordUiAction("invoice:submit", "blocked", message);
    showToast(message);
    return null;
  }
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
        ${rows || `<div class="table-row"><span>暂无沙盒发票记录。</span><span>-</span><span>-</span><span>-</span></div>`}
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

function setView(viewName) {
  const aliases = {
    billing: "userCenter",
    invoice: "userCenter",
    upload: "storage",
    paradigms: "journey",
  };
  const customerHiddenViews = new Set(["journey"]);
  const requestedView = String(viewName || "dashboard");
  let targetView = aliases[requestedView] || requestedView;
  if (state.role !== "admin" && customerHiddenViews.has(targetView)) {
    targetView = "dashboard";
  }
  qsa(".view").forEach((section) => {
    section.classList.toggle("active", section.id === targetView);
  });
  qsa("[data-view]").forEach((button) => {
    button.classList.toggle("active", button.dataset.view === targetView);
  });
  const viewTitle = qs("#viewTitle");
  if (viewTitle) {
    const activeButton = qsa(`[data-view="${targetView}"]`).find((button) => button.closest?.(".nav"));
    viewTitle.textContent = activeButton?.textContent?.trim() || titles[targetView] || targetView;
  }
  window.location.hash = `#${targetView}`;
  requestAnimationFrame(() => window.scrollTo({ top: 0, left: 0, behavior: "auto" }));
  renderStorageManagement();
  renderRealDelivery();
  updateRealActionGate();
  applyCleanVisibleCopy();
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
  setLoginMessage("\u5df2\u8fdb\u5165 QLanalyser \u9879\u76ee\u5de5\u4f5c\u53f0\u3002", "success");
  showToast("\u5df2\u8fdb\u5165\u9879\u76ee\u5de5\u4f5c\u53f0\u3002");
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
      password,
      registeredAt: account.created_at || new Date().toISOString().slice(0, 10),
      token: session.token,
    });
    rememberSession("customer", remember, { token: session.token, accountId: account.id });
    loginAs("customer", getStoredCustomer());
    await refreshWallet();
    setLoginFieldValidity(true);
    setLoginMessage("\u5df2\u8fdb\u5165 QLanalyser \u9879\u76ee\u5de5\u4f5c\u53f0\u3002", "success");
  } catch (error) {
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
  setLoginMessage("\u5df2\u8fdb\u5165 QLanalyser \u8fd0\u8425\u5de5\u4f5c\u53f0\u3002", "success");
  showToast("\u5df2\u8fdb\u5165\u8fd0\u8425\u5de5\u4f5c\u53f0\u3002");
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

function restoreSession() {
  const raw = localStorage.getItem(AUTH_KEY) || sessionStorage.getItem(AUTH_KEY);
  if (!raw) {
    logout(false);
    return;
  }
  try {
    const session = JSON.parse(raw);
    if (session.role === "admin" || session.role === "customer") {
      loginAs(session.role, session.role === "customer" ? getStoredCustomer() : null);
      return;
    }
  } catch {
    clearSession();
  }
  logout(false);
}

function loginAs(role, profile = null) {
  state.role = role;
  qs("#loginScreen").hidden = true;
  qs("#appShell").hidden = false;
  applyRoleNavigationState(role);
  if (role === "admin") {
    qs("#roleLabel").textContent = "运营账号";
    qs("#balanceSide").textContent = "管理后台";
    qs("#accountHint").textContent = "查看任务、客户与系统状态";
    const accountMeta = qs("#accountMeta");
    if (accountMeta) accountMeta.textContent = "admin / 管理权限";
    qs("#topEyebrow").textContent = "运营后台";
    renderAdminCustomerProfile();
    setView("adminDashboard");
  } else {
    const customer = profile || getStoredCustomer();
    const isDemoCustomer = customer.email === demoCustomer.email;
    qs("#roleLabel").textContent = customer.name || "客户账号";
    qs("#balanceSide").textContent = "个人中心";
    qs("#accountHint").textContent = isDemoCustomer
      ? `${customer.org || "QuanLan Online"} / 本地审核账号`
      : `${customer.org || "未设置机构"} / ${customer.email || "未设置邮箱"}`;
    const accountMeta = qs("#accountMeta");
    if (accountMeta) {
      accountMeta.textContent = `${maskEmail(customer.email || demoCustomer.email)} / ${isDemoCustomer ? "审核账号" : "客户账号"}`;
    }
    qs("#topEyebrow").textContent = "项目工作台";
    setView("dashboard");
    updateRealActionGate();
    refreshProjectWorkspace().catch((error) => {
      recordUiAction("workspace:refresh", "blocked", error.message || "项目工作台刷新失败");
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
    qs("#roleLabel").textContent = "运营账户";
    qs("#balanceSide").textContent = "运营概览";
    qs("#accountHint").textContent = "管理客户、项目、任务、发票和系统状态";
    qs("#topEyebrow").textContent = "运营后台";
    return;
  }
  const customer = profile || getStoredCustomer();
  const isDemoCustomer = customer.email === demoCustomer.email;
  qs("#roleLabel").textContent = customer.name || "客户账户";
  qs("#balanceSide").textContent = "账户概览";
  qs("#accountHint").textContent = isDemoCustomer
    ? `${customer.org || "Quanlan Neuro Lab"} · 当前项目工作区`
    : `${customer.org || "个人账户"} · ${customer.email || "未绑定邮箱"}`;
  qs("#topEyebrow").textContent = "QLanalyser Online · EEG 数据到报告";
}

function applyShellCopyFixesAscii(role, profile = null) {
  if (role === "admin") {
    qs("#roleLabel").textContent = "\u8fd0\u8425\u8d26\u6237";
    qs("#balanceSide").textContent = "\u8fd0\u8425";
    qs("#accountHint").textContent = "\u7ba1\u7406\u5ba2\u6237\u9879\u76ee\u3001\u4efb\u52a1\u3001\u8ba2\u5355\u3001\u5f00\u7968\u548c\u7cfb\u7edf\u72b6\u6001";
    qs("#topEyebrow").textContent = "\u8fd0\u8425 / \u4eca\u65e5\u9879\u76ee";
    return;
  }
  const customer = profile || getStoredCustomer();
  const isDemoCustomer = customer.email === demoCustomer.email;
  qs("#roleLabel").textContent = isDemoCustomer ? "\u5ba2\u6237\u8d26\u6237" : (customer.name || "\u5ba2\u6237\u8d26\u6237");
  qs("#balanceSide").textContent = "\u8d26\u6237\u6982\u89c8";
  qs("#accountHint").textContent = isDemoCustomer
    ? `\u5168\u6f9c\u8111\u79d1\u5b66 \u00b7 \u5f53\u524d\u9879\u76ee\u5de5\u4f5c\u533a`
    : `${customer.org || "\u4e2a\u4eba\u8d26\u6237"} \u00b7 ${customer.email || "\u672a\u7ed1\u5b9a\u90ae\u7bb1"}`;
  qs("#topEyebrow").textContent = "\u5f53\u524d\u9879\u76ee";
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
          <button class="ghost-btn mini" type="button" data-project-select="${escapeHtml(item.id)}">${isSelected ? "已选中" : "进入项目"}</button>
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
    ? "数据管理页会在选中项目后展开当前项目的数据。"
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

function setAllTextIfPresent(selector, text) {
  qsa(selector).forEach((node) => {
    node.textContent = text;
  });
}

function setValueIfPresent(selector, value) {
  const node = qs(selector);
  if (node) node.value = value;
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
  if (actionName.startsWith("billing:")) return "沙盒计费操作已记录。";
  if (actionName.startsWith("invoice:") || actionName.startsWith("inbox:")) return "沙盒交付状态已更新。";
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
    dashboard: "项目管理",
    storage: "数据管理",
    analysis: "数据准备",
    workflow: "分析任务",
    statistics: "结果查看",
    publication: "报告交付",
    journey: "质量检查",
    userCenter: "个人中心",
    adminDashboard: "运营首页",
    adminOperations: "任务运营",
    adminFinance: "财务管理",
    adminSystem: "系统状态",
  };
  Object.entries(navLabels).forEach(([view, label]) => setTextIfPresent(`[data-view="${view}"] span`, label));
  const activeView = qs(".view.active")?.id || "dashboard";
  setTextIfPresent("#viewTitle", titles[activeView] || "项目分析");
  setTextIfPresent("#logoutBtn span", "退出");
  setTextIfPresent("#roleLabel", "个人中心");
  setTextIfPresent("#balanceSide", "账户与财务");
  setTextIfPresent("#accountHint", "余额、充值、发票、权限和设置");
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
  setTextIfPresent("#topEyebrow", "QLanalyser Online · EEG 数据到报告");
  const customer = getStoredCustomer();
  setTextIfPresent("#userCenterName", customer.name || "演示用户");
  setTextIfPresent("#userCenterEmail", customer.email || "demo.customer@quanlan.cn");
  setTextIfPresent("#userCenterOrg", customer.org || "QuanLan Review Sandbox");
  const sideBalanceText = String(qs("#balanceMain")?.textContent || "1000.00").replace(/[^\d.]/g, "");
  setTextIfPresent("#userCenterBalance", `￥${Number(sideBalanceText || 1000).toFixed(2)}`);
  const textPairs = [
    ['[data-testid="project-crud-panel"] h2', "\u9879\u76ee\u7ba1\u7406"],
    ['[data-testid="project-crud-panel"] .panel-head p', "\u53ea\u505a\u9879\u76ee\u7684\u521b\u5efa\u3001\u7f16\u8f91\u3001\u5f52\u6863\u548c\u5220\u9664\uff1b\u8fdb\u5165\u9879\u76ee\u540e\u518d\u5904\u7406\u9879\u76ee\u5185\u6570\u636e\u3002"],
    ['[data-testid="project-data-crud-panel"] h2', "\u6570\u636e\u7ba1\u7406"],
    ['[data-testid="project-data-crud-panel"] .panel-head p', "\u53ea\u505a\u5f53\u524d\u9879\u76ee\u5185\u6570\u636e\u6587\u4ef6\u7684\u67e5\u770b\u3001\u5907\u6ce8\u3001\u4e0a\u4f20\u65b0\u7248\u672c\u548c\u5220\u9664\u3002"],
    ['[data-testid="ia-page-boundary-note"] h2', "\u9875\u9762\u8fb9\u754c"],
    ['[data-testid="ia-page-boundary-note"] .panel-head p', "\u9879\u76ee\u7ba1\u7406\u9875\u53ea\u8d1f\u8d23\u9879\u76ee\u4e0e\u6570\u636e\u7ba1\u7406\uff1b\u5206\u6790\u548c\u9884\u5904\u7406\u4ece\u9879\u76ee\u5165\u53e3\u8fdb\u5165\u3002"],
    ['[data-testid="data-preparation-workbench"] h2', "\u6570\u636e\u51c6\u5907\u5de5\u4f5c\u53f0"],
    ['[data-testid="data-preparation-workbench"] .panel-head p', "\u5bf9\u540c\u4e00\u9879\u76ee\u4e0b\u6bcf\u4e2a\u6570\u636e\u6587\u4ef6\u9010\u4e00\u9884\u89c8\u3001\u9884\u5904\u7406\u3001\u7f16\u8f91\u6570\u636e\u6bb5\u548c\u6807\u7b7e\uff0c\u6700\u540e\u518d\u63d0\u4ea4\u4efb\u52a1\u3002"],
    ['[data-testid="single-file-preview-panel"] h2', "\u5355\u6587\u4ef6\u9884\u89c8\u4e0e\u4fee\u8ba2"],
    ['[data-testid="segment-tag-editor-panel"] h2', "\u5f53\u524d\u4fee\u6539\u8bb0\u5f55"],
    ['[data-testid="segment-tag-editor-panel"] .panel-head p', "\u7247\u6bb5\u5254\u9664\u3001\u6062\u590d\u3001\u6807\u7b7e\u548c\u574f\u9053\u4fee\u6539\u4f1a\u5148\u8bb0\u5728\u8fd9\u91cc\uff0c\u4fdd\u5b58\u524d\u4e0d\u7834\u574f\u539f\u59cb\u6570\u636e\u3002"],
    ['[data-testid="preprocessing-readiness-panel"] h2', "\u6570\u636e\u51c6\u5907\u68c0\u67e5"],
    ['[data-testid="preprocessing-readiness-panel"] .panel-head p', "\u67e5\u770b\u6570\u636e\u6982\u51b5\u3001\u786e\u8ba4\u51c6\u5907\u65b9\u6848\uff0c\u5e76\u4fdd\u5b58\u6216\u6062\u590d\u574f\u9053\u4fee\u6539\u3002"],
    ['[data-testid="event-epoch-panel"] h2', "\u4e8b\u4ef6\u4e0e\u7247\u6bb5\u4fdd\u5b58"],
    ['[data-testid="event-epoch-panel"] .panel-head p', "\u4fdd\u5b58 ERP/P300 \u4e8b\u4ef6\u6620\u5c04\u3001\u5206\u6bb5\u7a97\u53e3\u3001\u57fa\u7ebf\u548c\u5254\u9664\u8bb0\u5f55\u3002"],
    ['[data-testid="data-preparation-submit-last"] h2', "\u786e\u8ba4\u6570\u636e\u51c6\u5907\u540e\u518d\u63d0\u4ea4"],
    ['[data-testid="data-preparation-submit-last"] .panel-head p', "确认数据准备方案、事件分段和质控记录后，再进入分析任务。"],
    ['[data-testid="analysis-task-workbench"] h2', "分析任务"],
    ['[data-testid="analysis-task-workbench"] .panel-head p', "选择已准备好的 EEG 数据后，可开始当前可用的分析方法。"],
    ['[data-testid="analysis-task-submit-and-report"] h2', "\u63d0\u4ea4\u5206\u6790\u4e0e\u751f\u6210\u62a5\u544a"],
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
    ['[data-real-action="create-report"] span', "生成交付报告"],
    ['[data-real-action="run-psd"] span', "开始 PSD 分析"],
    ['[data-real-action="run-erp"] span', "开始 ERP 分析"],
    ['[data-real-action="run-tfr"] span', "开始 TFR 时频分析"],
    ['[data-real-action="run-multitaper-psd"] span', "开始 Multitaper PSD"],
    ['[data-real-action="run-multitaper-tfr"] span', "开始 Multitaper TFR"],
    ['[data-real-action="run-reference-csd"] span', "开始 CSD 电流源密度计算"],
    ['[data-real-action="run-pac"] span', "开始 PAC 耦合分析"],
    ['[data-real-action="run-connectivity"] span', "开始 Connectivity 连接性分析"],
    ['[data-ia-action="select-prep-data"] span', "\u9009\u62e9\u5e76\u9884\u89c8"],
    ['[data-view-jump="statistics"] span', "\u67e5\u770b\u7ed3\u679c"],
    ['[data-view-jump="publication"] span', "\u4e0b\u8f7d\u62a5\u544a"],
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
    ["\u5220\u9664\u7247\u6bb5", "\u6392\u9664 30.0-35.0 s \u6570\u636e\u6bb5", "\u5220\u9664"],
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
    qc: ["数据准备与质量检查", "在分析前查看数据概况、基础质量提示、预览和准备记录。"],
    preprocessing_readiness: ["数据准备与质量检查", "在分析前查看数据概况、基础质量提示、预览和准备记录。"],
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
    [".admin-corner span", "\u7ba1\u7406"],
    [".login-brand .cover-copy h1", "\u7814\u7a76\u7ea7\u8111\u7535\u5206\u6790\u5e73\u53f0"],
    [".login-brand .cover-copy p", "\u6e05\u6670\u3001\u53ef\u590d\u73b0\u7684\u8111\u7535\u5206\u6790\u5de5\u4f5c\u533a\u3002"],
    [".account-title span", "\u7814\u7a76\u5de5\u4f5c\u533a"],
    [".account-title strong", "\u8fdb\u5165\u5206\u6790\u5de5\u4f5c\u53f0"],
    [".account-title small", "\u4e0a\u4f20\u6570\u636e\u3001\u8fd0\u884c\u6d41\u7a0b\u3001\u4e0b\u8f7d\u7ed3\u679c\u5305\u3002"],
    ['[data-login-tab="customerLogin"]', "\u767b\u5f55"],
    ['[data-login-tab="customerRegister"]', "\u6ce8\u518c\u8d26\u53f7"],
    ['label:has(#customerEmail) span', "\u90ae\u7bb1 / \u624b\u673a\u53f7"],
    ['label:has(#customerPassword) span', "\u5bc6\u7801"],
    ["#customerLoginBtn span", "\u767b\u5f55\u5e76\u8fdb\u5165\u5de5\u4f5c\u53f0"],
    ['[data-lab-link="module-lab"] span', "\u67e5\u770b\u65b9\u6cd5\u5e93"],
    ["#forgotPasswordBtn", "\u5e2e\u52a9\u4e0e\u8d26\u53f7\u627e\u56de"],
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
  if (qs("#realResultReview") && !qs("#realResultReview [data-result-module]") && !latestAnalysisTask()) {
    qs("#realResultReview").innerHTML = "<p>尚未生成分析结果。请先完成数据准备，再从 8 项分析方法中选择一种开始。</p>";
  }
  applyResultSurfaceCopy();
  renderEegPreviewEmptyState();
  sanitizeVisibleCopyTree();
}

const PRODUCT_NAV_LABELS = {
  dashboard: "项目管理",
  storage: "数据管理",
  analysis: "数据准备",
  workflow: "分析任务",
  statistics: "结果查看",
  publication: "报告交付",
  journey: "质量检查",
  billing: "费用与充值",
  invoice: "发票申请",
  inbox: "发票箱",
  userCenter: "个人中心",
  adminDashboard: "后台总览",
  adminOperations: "任务运营",
  adminFinance: "财务管理",
  adminSystem: "系统状态",
};

const PRODUCT_VIEW_TITLES = {
  dashboard: "项目管理",
  storage: "数据管理",
  analysis: "数据准备",
  workflow: "分析任务",
  statistics: "结果查看",
  publication: "报告交付",
  journey: "质量检查",
  billing: "费用与充值",
  invoice: "发票申请",
  inbox: "发票箱",
  userCenter: "个人中心",
  adminDashboard: "后台总览",
  adminOperations: "任务运营",
  adminFinance: "财务管理",
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
      ? `当前项目：${projectName}。数据文件按项目管理。`
      : "数据文件按项目管理，请先到项目管理打开一个项目。";
  }
  uploadButtons.forEach((button) => {
    button.disabled = !hasProject;
    button.title = hasProject ? "上传到当前项目" : "请先打开项目";
  });

  if (fileRows) {
    if (!hasProject) {
      fileRows.innerHTML = `
        <div class="storage-empty-state">
          <strong>请先打开项目</strong>
          <span>数据文件按项目管理，打开项目后再上传或选择数据。</span>
          <button class="primary-btn mini" type="button" data-view-jump="dashboard">去项目管理</button>
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
        const actionLabel = selected ? "当前数据" : "预览并准备";
        return `
          <button class="table-row storage-file-row${selected ? " selected" : ""}" type="button" data-file-select="${escapeHtml(item.id)}" data-jump-to-analysis="1" data-ia-action="select-prep-data" aria-current="${selected ? "true" : "false"}" title="${escapeHtml(eegFileDisplayName(item) || item.original_filename || item.id || "EEG 数据文件")}">
            <span><strong>${escapeHtml(eegFileDisplayName(item) || "EEG 数据文件")}</strong><small>${escapeHtml(item.original_filename || item.id || "")}</small></span>
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
      fileDetail.innerHTML = `
        <strong>数据文件详情</strong>
        <p>请先打开一个项目。这里会显示当前项目内的数据文件、备注和进入数据准备的入口。</p>
      `;
    } else if (!hasFile) {
      fileDetail.innerHTML = `
        <strong>${escapeHtml(projectName)}</strong>
        <p>${projectFiles.length ? "请从左侧选择一份数据文件。" : "当前项目还没有数据文件。"}</p>
        <div class="storage-detail-list">
          <span><b>数据文件：</b>${projectFiles.length} 个</span>
          <span><b>下一步：</b>${projectFiles.length ? "选择数据并预览" : "上传 EEG 数据"}</span>
        </div>
      `;
    } else {
      fileDetail.innerHTML = `
        <strong>${escapeHtml(eegFileDisplayName(file) || file.id)}</strong>
        <p>${escapeHtml(fileDetailLabel(file))}</p>
        <div class="storage-detail-list">
          <span><b>所属项目：</b>${escapeHtml(projectName)}</span>
          <span><b>文件状态：</b>${escapeHtml(fileStatusLabel(file))}</span>
          <span><b>准备记录：</b>${escapeHtml(selectedPrep)}</span>
        </div>
        <div class="real-actions compact-actions">
          <button class="primary-btn" type="button" data-view-jump="analysis"><i data-lucide="sliders-horizontal"></i><span>进入数据准备</span></button>
          <button class="ghost-btn" type="button" data-ia-action="rename-data"><i data-lucide="tag"></i><span>编辑名称 / 备注</span></button>
        </div>
      `;
    }
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
        ? `<div class="empty-object-state"><strong>暂无项目</strong><span>先创建项目，再上传或管理 EEG 数据。</span><button class="primary-btn mini" type="button" data-real-action="create-project">创建项目</button></div>`
        : `<div class="empty-object-state"><strong>项目列表已收起</strong><span>请先搜索项目或创建新项目；选中项目后再展开项目内数据。</span><button class="primary-btn mini" type="button" data-real-action="create-project">创建项目</button></div>`)}
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
      ? (file?.id ? `当前数据：${eegFileDisplayName(file)}；${preparationStatusLabel(file, plan, epochSet)}。` : "数据状态：等待上传或选择数据。")
      : "数据状态：未选择项目。";
  }
  if (dataEmptyState) {
    dataEmptyState.hidden = Boolean(project?.id && projectFiles.length > 0);
    const title = dataEmptyState.querySelector("strong");
    const body = dataEmptyState.querySelector("span");
    if (title) title.textContent = project?.id ? "当前项目暂无数据" : "请先选择项目";
    if (body) body.textContent = project?.id
      ? "选择 EEG 数据并上传到当前项目，上传后这里会显示数据列表、预览入口和下一步入口。"
      : "选中项目后才显示项目内数据，避免在项目管理页展开无关列表。";
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
        <div class="project-detail-summary">
          <span><b>数据文件：</b>${projectFiles.length} 个</span>
          <span><b>项目状态：</b>${escapeHtml(projectStatusLabel(project, files))}</span>
          <span><b>下一步：</b>${projectFiles.length ? "进入数据管理选择文件" : "进入数据管理上传 EEG 数据"}</span>
          <button class="primary-btn mini" type="button" data-view-jump="storage">进入数据管理</button>
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
      ${rows || `<div class="empty-object-state"><strong>${project?.id ? "\u5f53\u524d\u9879\u76ee\u6682\u65e0\u6570\u636e" : "\u8bf7\u5148\u9009\u62e9\u9879\u76ee"}</strong><span>${project?.id ? "\u8bf7\u56de\u5230\u6570\u636e\u7ba1\u7406\u4e0a\u4f20 EEG \u6570\u636e\u3002" : "\u5148\u5728\u9879\u76ee\u7ba1\u7406\u4e2d\u6253\u5f00\u9879\u76ee\uff0c\u518d\u9010\u4e2a\u9884\u5904\u7406\u9879\u76ee\u5185\u6570\u636e\u3002"}</span><button class="ghost-btn mini" type="button" data-view-jump="${project?.id ? "storage" : "dashboard"}">${project?.id ? "\u8fdb\u5165\u6570\u636e\u7ba1\u7406" : "\u8fd4\u56de\u9879\u76ee\u7ba1\u7406"}</button></div>`}
    `;
  }

  updateDashboardSummaryCards({ project, file, plan, epochSet, projectFiles, files });
  renderStorageManagement();
  applyCleanVisibleCopy();
}

function updateDashboardSummaryCards({ project, file, plan, epochSet, projectFiles = [], files = [] }) {
  const projectName = project?.id ? (projectDisplayName(project) || project.id) : "未选择项目";
  const projectNote = project?.id ? projectStatusLabel(project, files) : "先从项目列表选择一个项目";
  const fileName = file?.id ? (eegFileDisplayName(file) || file.id) : (project?.id ? "未选择数据" : "未选择数据");
  const fileNote = file?.id ? `${fileStatusLabel(file)} · ${fileDetailLabel(file)}` : (project?.id ? `${projectFiles.length} 个数据文件` : "选择项目后显示数据文件");
  const prepText = file?.id ? preparationStatusLabel(file, plan, epochSet) : "未开始";
  const nextText = project?.id ? (file?.id ? "进入数据准备" : "上传或选择数据") : "先选项目";
  const nextNote = project?.id
    ? "数据管理只展开当前项目内的数据和操作。"
    : "先选择项目，再展开数据管理。";

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

function applyProductPageStructureCleanup() {
  const statistics = qs("#statistics");
  if (statistics && statistics.dataset.productClean !== "true") {
    statistics.dataset.productClean = "true";
    statistics.innerHTML = `
      <section class="panel span-2" data-testid="results-review-workbench">
        <div class="panel-head">
          <div><h2>结果查看</h2><p>本页展示已完成分析的图表、表格和参数记录。需要下载完整文件时，请到“报告交付”。</p></div>
        </div>
        <div id="realResultReview" class="result-review"></div>
      </section>
      <section class="panel" data-testid="result-boundary-panel">
        <div class="panel-head compact"><h2>结果说明</h2></div>
        <p class="customer-note">当前结果用于科研分析参考。若需要组水平统计，请先完成对应的数据汇总和统计流程。</p>
      </section>
    `;
  }

  const publication = qs("#publication");
  if (publication && publication.dataset.productClean !== "true") {
    publication.dataset.productClean = "true";
    publication.innerHTML = `
      <section class="panel span-2" data-testid="report-delivery-workbench">
        <div class="panel-head">
          <div><h2>报告交付</h2><p>管理已生成的交付报告、在线预览、完整下载和交付清单。</p></div>
          <button class="primary-btn" type="button" data-real-action="create-report"><i data-lucide="file-output"></i><span>生成交付报告</span></button>
        </div>
        <div class="delivery-grid" id="realDeliveryLinks"></div>
      </section>
      <section class="panel" data-testid="report-package-contract">
        <div class="panel-head compact"><h2>\u4ea4\u4ed8\u5305\u5185\u5bb9</h2></div>
        <div class="storage-table compact-table">
          <div class="table-row head"><span>\u5185\u5bb9</span><span>\u7528\u9014</span><span>\u72b6\u6001</span></div>
          <div class="table-row"><span>\u56fe\u8868</span><span>\u7ed3\u679c\u67e5\u770b\u548c\u6c47\u62a5</span><span class="run">\u968f\u62a5\u544a\u751f\u6210</span></div>
          <div class="table-row"><span>\u8868\u683c</span><span>\u6307\u6807\u548c\u5bfc\u51fa\u6570\u636e</span><span class="run">\u968f\u62a5\u544a\u751f\u6210</span></div>
          <div class="table-row"><span>\u65b9\u6cd5\u8bb0\u5f55</span><span>\u53c2\u6570\u3001\u8f6f\u4ef6\u7248\u672c\u548c\u8fb9\u754c</span><span class="run">\u968f\u62a5\u544a\u751f\u6210</span></div>
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
          <div><h2>\u8bc4\u5ba1\u9a8c\u8bc1</h2><p>\u8fd9\u91cc\u53ea\u653e\u4ea7\u54c1\u9a8c\u8bc1\u548c\u8bc4\u5ba1\u95e8\uff1b\u4e0d\u518d\u91cd\u590d\u9879\u76ee\u3001\u6570\u636e\u3001\u5206\u6790\u6d41\u7a0b\u6559\u5b66\u3002</p></div>
        </div>
        <div class="review-gate-grid">
          <article class="review-gate-card"><strong>页面可操作检查</strong><span>按用户路径检查按钮、页面跳转和等待状态是否清楚。</span><b>已纳入</b></article>
          <article class="review-gate-card"><strong>结果完整性检查</strong><span>核对图、表、方法记录、提醒和下载入口是否齐全。</span><b>已纳入</b></article>
          <article class="review-gate-card"><strong>科学边界检查</strong><span>避免把描述性结果写成诊断、因果或群组统计结论。</span><b>已纳入</b></article>
          <article class="review-gate-card"><strong>中文与界面检查</strong><span>检查页面无乱码、无内部词、无重复入口、无无效按钮。</span><b>已纳入</b></article>
        </div>
      </section>
      <section class="panel" data-testid="review-action-panel">
        <div class="panel-head compact"><h2>\u4e0b\u4e00\u6b65\u9a8c\u8bc1</h2></div>
        <div class="real-actions compact-actions">
          <button class="ghost-btn" type="button" data-view-jump="dashboard"><i data-lucide="folder-kanban"></i><span>\u56de\u5230\u9879\u76ee\u7ba1\u7406</span></button>
          <button class="ghost-btn" type="button" data-view-jump="statistics"><i data-lucide="chart-no-axes-combined"></i><span>\u68c0\u67e5\u7ed3\u679c</span></button>
          <button class="ghost-btn" type="button" data-view-jump="publication"><i data-lucide="file-down"></i><span>\u68c0\u67e5\u62a5\u544a</span></button>
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
            <div><h2>\u8d26\u6237\u4e2d\u5fc3</h2><p>\u7ba1\u7406\u767b\u5f55\u8eab\u4efd\u3001\u6743\u9650\u3001\u5b89\u5168\u548c\u5e38\u7528\u504f\u597d\u3002</p></div>
          </div>
          <div class="profile-card clean-profile">
            <div><span>\u59d3\u540d</span><strong id="userCenterName">\u6f14\u793a\u7528\u6237</strong></div>
            <div><span>\u767b\u5f55\u8d26\u53f7</span><strong id="userCenterEmail">demo.customer@quanlan.cn</strong></div>
            <div><span>\u6240\u5c5e\u5355\u4f4d</span><strong id="userCenterOrg">QuanLan Review Sandbox</strong></div>
            <div><span>\u8d26\u53f7\u72b6\u6001</span><strong>\u672c\u5730\u5ba1\u6838\u8d26\u53f7</strong></div>
          </div>
          <div class="user-center-section">
            <h3>\u6743\u9650\u8303\u56f4</h3>
            <div class="audit-list">
              <span><b>\u9879\u76ee\u6743\u9650\uff1a</b>\u53ef\u67e5\u770b\u548c\u7ba1\u7406\u6f14\u793a\u9879\u76ee</span>
              <span><b>\u6570\u636e\u6743\u9650\uff1a</b>\u4ec5\u9650\u672c\u5730\u6d4b\u8bd5\u6570\u636e</span>
              <span><b>\u8bc4\u5ba1\u6743\u9650\uff1a</b>\u53ef\u6267\u884c\u4ea7\u54c1\u5ba1\u6838\u548c\u9a8c\u8bc1</span>
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

        <section class="panel user-center-column" data-testid="user-finance-column">
          <div class="panel-head">
            <div><h2>\u8d22\u52a1\u4e0e\u670d\u52a1</h2><p>\u5145\u503c\u3001\u4f59\u989d\u3001\u8ba2\u5355\u3001\u53d1\u7968\u3001\u901a\u77e5\u548c\u5e2e\u52a9\u90fd\u5728\u8fd9\u91cc\u7edf\u4e00\u7ba1\u7406\u3002</p></div>
          </div>
          <div class="finance-summary">
            <div><span>\u5f53\u524d\u4f59\u989d</span><strong id="userCenterBalance">\uffe51000.00</strong></div>
            <div><span>\u8d26\u53f7\u5b89\u5168</span><strong>\u672c\u5730\u5ba1\u6838\u4e13\u7528\u4f4e\u6743\u9650\u8d26\u53f7</strong></div>
          </div>
          <div class="user-center-section">
            <h3>\u5145\u503c</h3>
            <div class="balance">\uffe5<span id="balanceMain">1000.00</span></div>
            <div class="recharge compact-recharge">
              <button data-recharge="100">\uffe5100</button>
              <button data-recharge="500">\uffe5500</button>
              <button class="active" data-recharge="1000">\uffe51000</button>
              <button data-recharge="5000">\uffe55000</button>
            </div>
            <button class="primary-btn" id="rechargeBtn" type="button"><i data-lucide="wallet-cards"></i><span>\u5145\u503c</span></button>
          </div>
          <div class="user-center-section">
            <h3>\u8ba2\u5355\u4e0e\u53d1\u7968</h3>
            <div class="invoice-form compact-invoice-form">
              <label><span>\u53d1\u7968\u62ac\u5934</span><input id="invoiceTitleInput" value="\u67d0\u67d0\u5927\u5b66\u8ba4\u77e5\u795e\u7ecf\u79d1\u5b66\u5b9e\u9a8c\u5ba4" /></label>
              <label><span>\u5f00\u7968\u91d1\u989d</span><div class="with-unit"><input id="invoiceAmountInput" value="5.00" /><em>\u5143</em></div></label>
              <label><span>\u63a5\u6536\u90ae\u7bb1</span><input id="invoiceEmailInput" value="demo.customer@quanlan.cn" /></label>
            </div>
            <button class="primary-btn" id="invoiceBtn" type="button"><i data-lucide="send"></i><span>\u63d0\u4ea4\u5f00\u7968\u7533\u8bf7</span></button>
            <div class="notice" id="invoiceNotice"><i data-lucide="badge-check"></i><span>\u7b49\u5f85\u63d0\u4ea4\u3002</span></div>
          </div>
          <div class="user-center-section two-col-section">
            <div>
              <h3>\u901a\u77e5</h3>
              <div class="checklist compact-checklist">
                <label><input type="checkbox" checked /> \u5206\u6790\u5b8c\u6210\u63d0\u9192</label>
                <label><input type="checkbox" checked /> \u62a5\u544a\u751f\u6210\u63d0\u9192</label>
                <label><input type="checkbox" /> \u53d1\u7968\u5ba1\u6838\u63d0\u9192</label>
              </div>
            </div>
            <div>
              <h3>\u8bbe\u7f6e\u4e0e\u504f\u597d</h3>
              <div class="checklist compact-checklist">
                <label><input type="checkbox" checked /> \u767b\u5f55\u540e\u8fdb\u5165\u9879\u76ee\u7ba1\u7406</label>
                <label><input type="checkbox" checked /> \u4e0b\u8f7d\u524d\u663e\u793a\u6821\u9a8c\u72b6\u6001</label>
                <label><input type="checkbox" /> \u4f7f\u7528\u7d27\u51d1\u5217\u8868</label>
              </div>
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
    [".entry-kicker", "全澜脑科学 | QuanLan BrainScience"],
    [".entry-brand-lockup small", "面向科研团队的 EEG 数据管理、分析交付与复现记录平台。"],
    [".cover-copy p", "让脑电数据管理更清晰，让分析流程更简单，让研究结果更容易交付。"],
    [".account-title span", "研究工作区"],
    [".account-title strong", "进入分析项目"],
    [".account-title small", "上传数据、选择方法、下载结果材料。"],
    ['[data-login-tab="customerLogin"]', "登录"],
    ['[data-login-tab="customerRegister"]', "注册账号"],
    ['[data-login-tab="adminLogin"]', "运营后台"],
    ['label:has(#customerEmail) span', "邮箱 / 手机号"],
    ['label:has(#customerPassword) span', "密码"],
    ['label:has(#adminEmail) span', "管理员邮箱"],
    ['label:has(#adminPassword) span', "管理员密码"],
    [".admin-note", "后台仅用于运营人员管理客户、订单、任务和系统状态。"],
    ["#customerLoginBtn span", "登录并进入项目"],
    ["#forgotPasswordBtn", "帮助与账号找回"],
    ['#adminLoginForm button[type="submit"] span', "进入后台"],
  ];
  loginPairs.forEach(([selector, text]) => setTextIfPresent(selector, text));
  const emailInput = qs("#customerEmail");
  const passwordInput = qs("#customerPassword");
  const adminEmail = qs("#adminEmail");
  const adminPassword = qs("#adminPassword");
  if (emailInput) emailInput.placeholder = "输入已注册邮箱或体验手机号";
  if (passwordInput) passwordInput.placeholder = "请输入账户密码";
  if (adminEmail) adminEmail.placeholder = "运营后台账号";
  if (adminPassword) adminPassword.placeholder = "请输入后台密码";
  const loginBrand = qs(".login-brand");
  if (loginBrand) loginBrand.setAttribute("aria-label", "QLanalyser 脑电分析平台封面");
  const valueCards = qsa(".entry-value-grid article");
  [["数据归档", "原始数据、事件表、参数与结果统一留痕。"], ["分析流程", "从基础质量预览、数据准备到结果导出，按科研分析流程推进。"], ["交付复核", "图表、表格、方法说明和操作记录可一起交付。"]].forEach(([title, body], index) => {
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
  setTextIfPresent("#viewTitle", PRODUCT_VIEW_TITLES[activeView] || "项目分析");
  setTextIfPresent("#topEyebrow", "QLanalyser Online · EEG 数据到报告");
  applyTeachingModeChrome();
  setTextIfPresent("#logoutBtn span", "退出");
  setTextIfPresent("#roleLabel", state.role === "admin" ? "运营后台" : "个人中心");
}


function applyCustomerAnalysisTaskCopy() {
  setTextIfPresent('[data-testid="analysis-task-workbench"] h2', "分析任务");
  setTextIfPresent('[data-testid="analysis-task-workbench"] .panel-head p', "选择已准备好的 EEG 数据后，可开始当前可用的分析方法。");
  setTextIfPresent('[data-testid="analysis-task-workbench"] .badge', "当前可用：8 项分析方法");
  setTextIfPresent(".analysis-context-strip span", "前置要求：已选择项目、已选择数据，并已完成或确认数据准备。");
  setTextIfPresent('[data-testid="analysis-method-scope-panel"] h2', "当前可用分析方法");
  setTextIfPresent('[data-testid="analysis-method-scope-panel"] .panel-head p', "选择一个分析目标，系统会根据当前数据条件提示可运行的方法。");
  const methodCards = qsa('[data-testid="analysis-method-scope-panel"] .ia-method-card');
  const moduleOrder = ["psd", "erp", "tfr", "multitaper_psd", "multitaper_tfr", "pac", "connectivity", "reference_csd"];
  const customerMethodCopy = {
    psd: ["PSD 频谱与频段功率", "输出频谱、频段功率和通道级表格，适合查看主要频段分布。", "频谱", "available", "run-psd"],
    erp: ["ERP 事件相关电位", "基于事件分段输出波形、指标和剔除记录，适合事件相关分析。", "需事件", "available", "run-erp"],
    tfr: ["TFR 时频分析", "查看事件前后的时频功率和相位一致性，并记录频率范围与基线设置。", "时频", "available", "run-tfr"],
    multitaper_psd: ["Multitaper PSD", "使用多窗谱估计查看频谱功率，适合对频谱结果做参数化比较。", "多窗谱", "available", "run-multitaper-psd"],
    multitaper_tfr: ["Multitaper TFR", "查看事件锁定的多窗时频结果，并记录事件、基线和窗参数。", "多窗时频", "available", "run-multitaper-tfr"],
    pac: ["PAC 相位-振幅耦合", "查看相位-振幅耦合的描述性图表和表格，不能单独解释为因果机制。", "耦合", "available", "run-pac"],
    connectivity: ["Connectivity 连接性分析", "查看连接性矩阵和边表，结果用于研究参考，不证明信息流或因果方向。", "连接", "available", "run-connectivity"],
    reference_csd: ["CSD 电流源密度计算", "基于通道位置信息计算头皮电位空间分布变化；这是传感器空间滤波，不是源定位或诊断。", "需通道位置", "available", "run-reference-csd"],
  };
  methodCards.forEach((card, index) => {
    const moduleId = card.dataset.moduleId || moduleOrder[index];
    const copy = customerMethodCopy[moduleId];
    if (!copy) return;
    const [title, body, status, tone, action] = copy;
    card.dataset.moduleId = moduleId;
    card.dataset.realAction = action;
    card.setAttribute("type", "button");
    card.setAttribute("title", `${title}：点击后按当前数据条件运行或提示前置步骤。`);
    card.classList.remove("beta", "draft", "dependency", "available");
    if (tone) card.classList.add(tone);
    const strong = card.querySelector("strong");
    const span = card.querySelector("span");
    const badge = card.querySelector("b");
    if (strong) strong.textContent = title;
    if (span) span.textContent = body;
    if (badge) badge.textContent = status;
  });
}

function applyCleanVisibleCopy() {
  applyProductPageStructureCleanup();
  Object.entries(PRODUCT_NAV_LABELS).forEach(([view, label]) => setTextIfPresent(`[data-view="${view}"] span`, label));
  qsa('[data-view="journey"]').forEach((button) => {
    button.hidden = state.role !== "admin";
    button.setAttribute("aria-hidden", state.role !== "admin" ? "true" : "false");
  });
  const activeView = qs(".view.active")?.id || "dashboard";
  setTextIfPresent("#viewTitle", PRODUCT_VIEW_TITLES[activeView] || "项目分析");
  setTextIfPresent("#topEyebrow", "QLanalyser Online · EEG 数据到报告");
  setTextIfPresent("#logoutBtn span", "退出");
  setTextIfPresent("#roleLabel", "个人中心");
  setTextIfPresent("#balanceSide", "账户与财务");
  setTextIfPresent("#accountHint", "余额、充值、发票、权限和设置");
  setTextIfPresent('[data-testid="project-crud-panel"] h2', "项目管理");
  setTextIfPresent('[data-testid="project-crud-panel"] .panel-head p', "先建立或打开一个研究项目，再选择项目内数据。");
  setTextIfPresent("#workspaceProjectSearch + span", "项目搜索");
  setTextIfPresent('label:has(#workspaceProjectSearch) span', "搜索项目");
  const projectSearch = qs("#workspaceProjectSearch");
  if (projectSearch) projectSearch.placeholder = "按项目名或项目编号搜索";
  setTextIfPresent('label[for="workspaceShowReviewProjects"] span', "显示内部/归档项目");
  updateProjectVisibilityToggleLabel();
  setTextIfPresent('[data-testid="project-data-crud-panel"] h2', "项目内数据");
  setTextIfPresent('[data-testid="project-data-crud-panel"] .panel-head p', "打开项目后，在这里查看项目内数据概况和下一步入口；上传和文件整理请进入“数据管理”。");
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
}


function handleEegCanvasPointerDown(event) {
  if (event.button !== 0) return;
  const time = eegCanvasTimeFromEvent(event);
  if (!Number.isFinite(time)) return;
  event.preventDefault();
  const canvas = qs("#eegCanvas");
  canvas?.classList.add("dragging");
  eegState.drag = { startTime: time, currentTime: time, moved: false };
  eegState.selectedSegment = { start_sec: time, end_sec: time + 0.05 };
  updateSelectedSegmentInputs(eegState.selectedSegment);
  redrawCurrentWaveform();
}

function handleEegCanvasPointerMove(event) {
  if (!eegState.drag) return;
  const time = eegCanvasTimeFromEvent(event);
  if (!Number.isFinite(time)) return;
  event.preventDefault();
  eegState.drag.currentTime = time;
  eegState.drag.moved = Math.abs(time - eegState.drag.startTime) > 0.05;
  const normalized = normalizeSegmentRange(eegState.drag.startTime, time);
  if (normalized) {
    eegState.selectedSegment = normalized;
    updateSelectedSegmentInputs(normalized);
    redrawCurrentWaveform();
  }
}

function handleEegCanvasPointerUp(event) {
  if (!eegState.drag) return;
  event.preventDefault();
  const normalized = normalizeSegmentRange(eegState.drag.startTime, eegState.drag.currentTime);
  eegState.drag = null;
  qs("#eegCanvas")?.classList.remove("dragging");
  if (normalized) {
    eegState.selectedSegment = normalized;
    updateSelectedSegmentInputs(normalized);
    renderWaveformInteractionHint(`已选择 ${normalized.start_sec.toFixed(2)}-${normalized.end_sec.toFixed(2)} s，可剔除或添加标签`);
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
    const anchorRatio = clampNumber((anchorTime - oldStart) / oldDuration, 0, 1);
    const factor = event.deltaY > 0 ? 1.2 : 0.8;
    const newDuration = Math.max(2, Math.min(30, oldDuration * factor));
    eegState.windowSec = newDuration;
    eegState.start = Math.max(0, anchorTime - anchorRatio * newDuration);
  } else {
    const step = Math.max(0.2, Number(eegState.windowSec || 10) * 0.08);
    eegState.start = Math.max(0, Number(eegState.start || 0) + (event.deltaY > 0 ? step : -step));
  }
  syncEegControlsFromState();
  reloadWaveformPreview().catch((error) => showToast(error.message || "波形预览更新失败。"));
}

document.addEventListener("mousedown", (event) => {
  if (event.target?.matches?.("#eegCanvas")) handleEegCanvasPointerDown(event);
});
document.addEventListener("mousemove", handleEegCanvasPointerMove);
document.addEventListener("mouseup", handleEegCanvasPointerUp);
document.addEventListener("wheel", handleEegCanvasWheel, { passive: false });

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
      ? "已切换到注册账号。"
      : (loginTabButton.dataset.loginTab === "adminLogin" ? "已切换到运营后台。" : "已切换到登录。");
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
  const payMethodButton = event.target?.closest?.("[data-pay-method]");
  if (payMethodButton) {
    event.preventDefault?.();
    state.paymentMethod = payMethodButton.dataset.payMethod || "alipay";
    qsa("[data-pay-method]").forEach((button) => button.classList.toggle("active", button === payMethodButton));
    const message = `已选择沙盒支付方式：${state.paymentMethod === "wechat_pay" ? "微信" : "支付宝"}。`;
    recordUiAction("billing:select-payment-method", "pass", message, { payment_method: state.paymentMethod });
    showToast(message);
    return;
  }
  const rechargeAmountButton = event.target?.closest?.("[data-recharge]");
  if (rechargeAmountButton) {
    event.preventDefault?.();
    state.rechargeAmount = Number(rechargeAmountButton.dataset.recharge || 1000);
    qsa("[data-recharge]").forEach((button) => button.classList.toggle("active", button === rechargeAmountButton));
    const message = `已选择沙盒充值金额：${money(state.rechargeAmount)}。`;
    recordUiAction("billing:select-recharge-amount", "pass", message, { amount: state.rechargeAmount });
    showToast(message);
    return;
  }
  const rechargeButton = event.target?.closest?.("#rechargeBtn");
  if (rechargeButton) {
    event.preventDefault?.();
    handleSandboxRecharge();
    return;
  }
  const invoiceButton = event.target?.closest?.("#invoiceBtn");
  if (invoiceButton) {
    event.preventDefault?.();
    handleInvoiceSubmit();
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
  const waveformControl = event.target?.closest?.("#eegPrevBtn, #eegNextBtn, #eegZoomOutBtn, #eegZoomInBtn, #eegResetBtn");
  if (waveformControl) {
    event.preventDefault?.();
    const run = waveformControl.id === "eegPrevBtn"
      ? shiftEegWindow(-1)
      : waveformControl.id === "eegNextBtn"
        ? shiftEegWindow(1)
        : waveformControl.id === "eegZoomInBtn"
          ? zoomEegWindow(0.5)
          : waveformControl.id === "eegZoomOutBtn"
            ? zoomEegWindow(1.5)
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
  const realActionButton = event.target?.closest?.("[data-real-action]");
  if (realActionButton) {
    event.preventDefault?.();
    if (realActionButton.disabled || realActionButton.getAttribute("aria-disabled") === "true") {
      const message = realActionButton.title || "\u8be5\u64cd\u4f5c\u5f53\u524d\u4e0d\u53ef\u7528\uff0c\u8bf7\u5148\u5b8c\u6210\u524d\u7f6e\u6b65\u9aa4\u3002";
      recordUiAction(`real:${realActionButton.dataset.realAction}`, "blocked", message);
      showToast(message);
      return;
    }
    handleRealAction(realActionButton.dataset.realAction);
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

document.addEventListener("change", (event) => {
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
    setTextIfPresent("#eegGainLabel", `${eegState.gain}x`);
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
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && state.teaching.guideActive) {
    event.preventDefault();
    finishTeachingGuide();
  }
});

window.addEventListener("resize", () => {
  if (state.teaching.active && state.teaching.guideActive) renderTeachingOverlay();
  window.clearTimeout(eegState.resizeTimer);
  eegState.resizeTimer = window.setTimeout(() => {
    if (currentWaveformPayload()?.data_uv?.length) redrawCurrentWaveform();
    else drawEegPreviewSkeleton(currentWorkspaceFile());
  }, 120);
});

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

restoreSession();
applyCustomerDemoMode();
applyCleanVisibleCopy();
})();
