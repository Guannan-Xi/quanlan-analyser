const qs = (selector) => document.querySelector(selector);
const qsa = (selector) => [...document.querySelectorAll(selector)];
const escapeHtml = (value = "") => String(value)
  .replace(/&/g, "&amp;")
  .replace(/</g, "&lt;")
  .replace(/>/g, "&gt;")
  .replace(/"/g, "&quot;")
  .replace(/'/g, "&#39;");
const money = (value) => `￥${Number(value).toFixed(2)}`;
const today = () => new Date().toLocaleDateString("zh-CN");
const nowTime = () => new Date().toLocaleTimeString("zh-CN", { hour12: false });
const AUTH_KEY = "neurocloud_auth_session";
const CUSTOMER_KEY = "neurocloud_customer_profile";
const PRODUCT_TITLE = "QLanalyser 脑科学数据分析平台";
const STARTER_BALANCE = 100;
const API_BASE = "";
const LOCAL_BDF_SAMPLE_META = "/api/local-sample/nohe-bdf/meta";
const PRODUCT_MODE = (location.pathname.endsWith("/v0.html") || new URLSearchParams(location.search).get("mode") === "v0") ? "v0" : "full";
const isV0Mode = PRODUCT_MODE === "v0";
const architecture = window.QLANALYSER_ARCHITECTURE || {};
const domainFactory = {
  createProject: architecture.createProject || ((input) => input),
  createEegFile: architecture.createEegFile || ((input) => input),
  createAnalysisTask: architecture.createAnalysisTask || ((input) => input),
  createLedgerEntry: architecture.createLedgerEntry || ((input) => input),
  createArtifact: architecture.createArtifact || ((input) => input),
};
const TEACHING_DATASET = {
  id: "system_visual_oddball_p300",
  name: "Visual Oddball P300",
  edfUrl: "./assets/system_teaching_oddball/system_visual_oddball_p300.edf",
  eventsUrl: "./assets/system_teaching_oddball/system_visual_oddball_p300_events.tsv",
  manifestUrl: "./assets/system_teaching_oddball/system_teaching_manifest.json",
  channelCount: 64,
  durationSec: 180,
  eventsCount: 80,
  locked: true,
};
const deliveryPreviewRegistry = new Map();
const TEACHING_DELIVERIES = [
  {
    id: "teaching-events",
    href: TEACHING_DATASET.eventsUrl,
    icon: "table",
    label: "教学事件表",
    detail: "target / standard 事件标记",
    type: "tsv",
    source: "学习模式",
    size: "约 2 KB",
  },
  {
    id: "teaching-edf",
    href: TEACHING_DATASET.edfUrl,
    icon: "database",
    label: "教学 EDF",
    detail: "64 通道 Visual Oddball P300",
    type: "edf",
    source: "系统锁定教学数据",
    size: "约 5.6 MB",
    meta: "64 通道 / 180 秒 / 80 个事件；只用于学习模式。",
  },
  {
    id: "teaching-manifest",
    href: TEACHING_DATASET.manifestUrl,
    icon: "file-json",
    label: "教学 manifest",
    detail: "通道、时长和事件摘要",
    type: "json",
    source: "学习模式",
    size: "约 1 KB",
  },
];

document.title = PRODUCT_TITLE;
document.documentElement.dataset.productMode = PRODUCT_MODE;

function nowDateTime() {
  return new Date().toLocaleString("zh-CN", { hour12: false });
}

const demoCustomer = {
  name: "本地体验客户",
  phone: "13900000000",
  phoneVerifiedAt: "本地演示",
  email: "demo@qlanalyser.local",
  org: "本地演示账号",
  password: "demo123456",
  registeredAt: "本地内置",
};

const state = {
  balance: STARTER_BALANCE,
  rechargeAmount: 1000,
  activeTemplate: "ERP 事件相关电位",
  analysisPage: "home",
  segmentMode: "time",
  role: null,
  selectedPayMethod: "支付宝",
  sms: {
    pendingPhone: "",
    lastBizId: "",
    sandboxCode: "",
    expiresAt: 0,
  },
  payment: {
    activeOrder: null,
    lastError: "",
  },
  platform: null,
  localSample: null,
  teaching: {
    loaded: false,
    eventsConfirmed: false,
    templateSelected: false,
    analysisDone: false,
    result: null,
    resultUrl: "",
  },
  activeDeliveryPreview: null,
  teachingModeActive: false,
  tasks: [],
  adminActiveTaskId: "admin-task-formal-sample",
  adminTasks: [
    {
      id: "admin-task-formal-sample",
      customer: "后台监控样本客户",
      project: "Oddball ERP 正式分析",
      file: "sub-01_task-oddball.edf",
      size: "2.4 GB",
      cost: 420,
      submittedAt: "2026-06-12 16:10",
      currentNodeId: "delivery_review",
      failedNodeIds: [],
      doneNodeIds: ["intake", "profile_check", "cost_freeze", "upload_store", "queue_assign", "format_parse", "preprocess", "quality_check", "method_route", "mne_worker", "stats", "figures", "report_package"],
      history: [
        { time: "16:10:21", nodeId: "intake", status: "完成", note: "客户提交任务" },
        { time: "16:10:28", nodeId: "cost_freeze", status: "完成", note: "冻结 ￥420.00" },
        { time: "16:11:43", nodeId: "preprocess", status: "完成", note: "64 通道 EDF 预处理完成" },
        { time: "16:14:09", nodeId: "mne_worker", status: "完成", note: "ERP、统计表和图表已生成" },
        { time: "16:16:02", nodeId: "delivery_review", status: "当前", note: "等待交付复核" },
      ],
    },
    {
      id: "admin-task-failed-ica",
      customer: "认知神经实验室",
      project: "N-back 工作记忆",
      file: "sub-07_task-nback.edf",
      size: "3.4 GB",
      cost: 580,
      submittedAt: "2026-06-12 15:42",
      currentNodeId: "preprocess",
      failedNodeIds: ["preprocess"],
      doneNodeIds: ["intake", "profile_check", "cost_freeze", "upload_store", "queue_assign", "format_parse"],
      history: [
        { time: "15:42:11", nodeId: "intake", status: "完成", note: "客户提交任务" },
        { time: "15:42:19", nodeId: "upload_store", status: "完成", note: "分片上传合并完成" },
        { time: "15:44:03", nodeId: "format_parse", status: "完成", note: "EDF 头信息读取完成" },
        { time: "15:45:38", nodeId: "preprocess", status: "失败", note: "ICA 阶段检测到异常通道比例过高" },
      ],
    },
    {
      id: "admin-task-queued-teaching",
      customer: "学习模式系统账号",
      project: "Visual Oddball P300 教学数据校验",
      file: "system_visual_oddball_p300.edf",
      size: "5.6 MB",
      cost: 0,
      submittedAt: "2026-06-12 16:30",
      currentNodeId: "queue_assign",
      failedNodeIds: [],
      doneNodeIds: ["intake", "profile_check", "cost_freeze", "upload_store"],
      history: [
        { time: "16:30:02", nodeId: "intake", status: "完成", note: "管理员校验系统教学数据" },
        { time: "16:30:05", nodeId: "format_parse", status: "完成", note: "64 通道 EDF 与事件表可读取" },
        { time: "16:30:09", nodeId: "queue_assign", status: "当前", note: "等待定期回归校验" },
      ],
    },
  ],
  activeProjectId: null,
  projects: [],
  orders: [
    { id: "QL-20260611-RCH", customer: "后台监控样本客户", type: "充值", amount: 1000, status: "已入账", source: "支付回调", createdAt: "2026-06-11 10:12", handler: "系统" },
    { id: "QL-20260612-ERP", customer: "后台监控样本客户", type: "任务扣费", amount: 420, status: "已扣费", source: "任务 admin-task-formal-sample", createdAt: "2026-06-12 16:10", handler: "系统" },
    { id: "QL-20260612-INV", customer: "认知神经实验室", type: "开票", amount: 580, status: "待审核", source: "客户提交发票信息", createdAt: "2026-06-12 15:50", handler: "财务复核" },
  ],
  invoices: [
    { id: "INV-20260612-001", customer: "认知神经实验室", title: "认知神经实验室", taxId: "待核对", amount: 580, email: "lab@example.com", status: "待审核", createdAt: "2026-06-12 15:50" },
  ],
  operationLog: [
    { time: "16:30:09", actor: "系统", action: "教学数据校验排队", target: "Visual Oddball P300", source: "system_teaching_manifest.json" },
    { time: "16:16:02", actor: "管理员", action: "交付复核中", target: "Oddball ERP 正式分析", source: "业务链路 delivery_review" },
    { time: "15:45:38", actor: "worker", action: "预处理失败", target: "N-back 工作记忆", source: "ICA 质控规则" },
  ],
  systemStatus: {
    teachingEnabled: true,
    teachingVersion: "2026.06.12",
    teachingVerifiedAt: "未校验",
    mneOnline: true,
    eeglabMapped: true,
    deliveryOnline: true,
    scaleApproval: false,
    riskChecks: {
      uploadResume: true,
      balanceGuard: true,
      invoiceReview: false,
      archivePolicy: false,
    },
  },
  formalPreviewOpen: false,
};

const eegState = {
  data: null,
  events: [],
  eventSource: "none",
  sourceName: "",
  sourceMode: "",
  autoloaded: false,
  start: 0,
  windowSec: 10,
  gain: 2,
  filter: {
    enabled: true,
    highpassHz: 0.5,
    lowpassHz: 40,
    notchEnabled: false,
    notchHz: 50,
    notchQ: 30,
  },
  originalData: null,
  preprocess: {
    ran: false,
    steps: [],
    badChannels: [],
    badSegments: [],
    icaCandidates: [],
    summary: "请先加载 EEG 数据",
  },
  visibleChannels: 8,
  drag: null,
};

const templates = [
  { name: "静息态功率谱", desc: "计算频段功率、alpha peak 和被试级指标", icon: "bar-chart-3", image: "./assets/analysis-psd.png" },
  { name: "ERP 事件相关电位", desc: "比较 annotation 条件波形并提取时间窗指标", icon: "waves", image: "./assets/analysis-erp.png" },
  { name: "时频分析", desc: "输出事件锁定频段变化和条件差异", icon: "audio-waveform", image: "./assets/analysis-timefreq.png" },
];

const PREPROCESS_HELP = {
  highpass: "高通滤波用于去除慢漂移。ERP 常见设置为 0.1-1 Hz，静息态常见设置为 0.5-1 Hz。",
  lowpass: "低通滤波用于限制高频噪声。ERP 常见设置为 30-40 Hz，时频分析要按目标频段调整。",
  notch: "陷波用于去除工频干扰。中国常用 50 Hz，北美常用 60 Hz。",
  reference: "重参考会改变电位零点。V0 支持平均参考、保留原参考、Cz、双乳突、单侧乳突、指定通道，并预留 REST。",
  referenceChannel: "指定通道参考会把所选通道信号从所有通道中扣除，适合已知硬件参考或特定实验方案。",
  icaMethod: "MNE 常用 fastica、infomax、picard；EEGLAB 常用 runica，对应 infomax 并可启用 extended。",
  icaComponents: "ICA 成分数对应 MNE n_components 或 EEGLAB PCA 维数，通常不超过有效 EEG 通道数。",
  icaMaxIter: "最大迭代对应 MNE max_iter 或 runica 训练停止上限，数据更复杂时可适当提高。",
  icaDecim: "降采样对应 MNE decim，可在拟合 ICA 时加速计算，但需要记录到复现参数中。",
  icaRandomState: "随机种子对应 MNE random_state，用于保证结果可重复。",
  icaThreshold: "ICLabel 阈值用于标记眼动、肌电、心电、工频和通道噪声等非脑源成分候选。",
  icaExtended: "Extended 是 EEGLAB runica 常用开关，更适合同时分离超高斯和亚高斯成分。",
  eventType: "事件类型来自 EEG annotations 或事件表。ERP/RRP 和 TFR 只对选中的事件类别切 epoch。",
  eventPre: "事件前窗口决定 epoch 起点。ERP 常用 -0.2 秒，TFR 可按实验设计延长。",
  eventPost: "事件后窗口决定 epoch 终点。P300 常见到 0.8 秒，复杂任务可延长。",
  erpBaseline: "Baseline 用事件前安静时间段校正电位零点，常用 -0.2 到 0 秒。",
  segmentStart: "PSD 连续窗起点，应避开导入初期漂移、练习段或明显伪迹。",
  segmentEnd: "PSD 连续窗终点，应保证窗口足够长，并和起点共同形成可分析片段。",
  psdWelchWindow: "Welch 窗长影响频率分辨率和稳定性。窗口越长频率分辨率越高，但对非平稳更敏感。",
  psdBands: "频段决定输出指标。常用 Delta、Theta、Alpha、Beta，也可扩展自定义频段。",
  tfrFreqRange: "TFR 频率范围决定时频图覆盖的节律，常见认知任务可从 4-40 Hz 开始。",
  tfrWindow: "TFR 时间窗决定围绕事件计算的时间范围，需要覆盖预期反应和基线。",
  tfrBaseline: "TFR 基线用于计算相对功率变化，常用事件前 -0.3 到 0 秒。",
};

function helpIcon(topic, label) {
  const text = PREPROCESS_HELP[topic] || "该参数会写入任务 manifest，用于复现分析。";
  return `<button class="help-dot" type="button" data-help-topic="${topic}" aria-label="查看${label}说明" title="${escapeHtml(text)}"><i data-lucide="circle-help"></i></button>`;
}

const V0_TEMPLATE_NAMES = new Set(["静息态功率谱", "ERP 事件相关电位", "时频分析"]);
const WORKFLOW_ROUTES = {
  "ERP 事件相关电位": {
    route: "erp",
    title: "当前路径：ERP/RRP",
    detail: "接下来只展示事件锁定分析需要的预处理和参数：事件表、epoch、baseline、条件平均和时间窗指标。",
    segmentMode: "event",
  },
  "静息态功率谱": {
    route: "psd",
    title: "当前路径：频谱 PSD",
    detail: "接下来只展示连续数据分析需要的预处理和参数：坏段、连续窗、Welch、频带功率和频段 topomap。",
    segmentMode: "time",
  },
  "时频分析": {
    route: "tfr",
    title: "当前路径：时频 TFR",
    detail: "接下来只展示时频分析需要的预处理和参数：事件窗、频率范围、基线方式和 ERD/ERS 输出。",
    segmentMode: "event",
  },
};

const ANALYSIS_TARGET_PAGES = {
  "#analysis": "home",
  ".upload-panel": "data",
  ".data-files-panel": "data",
  ".preview-panel": "data",
  ".preprocess-panel": "preprocess",
  ".method-panel": "method",
  ".segment-panel": "method",
  ".submit-panel": "submit",
};
const ANALYSIS_PAGES = new Set(["home", "data", "preprocess", "method", "submit", "result"]);

const BUSINESS_CHAIN = [
  {
    title: "客户入口",
    nodes: [
      { id: "register_verify", label: "注册验证", detail: "手机短信" },
      { id: "intake", label: "提交任务", detail: "项目 / 文件 / 模板" },
      { id: "profile_check", label: "账号校验", detail: "权限 / 配额" },
      { id: "cost_freeze", label: "冻结费用", detail: "余额 / 免费额度" },
    ],
  },
  {
    title: "收费入口",
    nodes: [
      { id: "payment_create", label: "创建订单", detail: "支付宝" },
      { id: "payment_notify", label: "支付回调", detail: "验签 / 入账" },
    ],
  },
  {
    title: "数据入口",
    nodes: [
      { id: "upload_store", label: "上传入库", detail: "分片 / 对象存储" },
      { id: "queue_assign", label: "进入队列", detail: "租户限流" },
      { id: "format_parse", label: "格式解析", detail: "EDF / BDF / SET" },
    ],
  },
  {
    title: "预处理",
    nodes: [
      { id: "preprocess", label: "预处理", detail: "滤波 / ICA / 坏道" },
      { id: "quality_check", label: "质控复核", detail: "伪迹 / 事件 / 通道" },
      { id: "method_route", label: "方法路由", detail: "MNE / EEGLAB" },
    ],
  },
  {
    title: "分析计算",
    nodes: [
      { id: "mne_worker", label: "分析 worker", detail: "ERP / PSD / TFR" },
      { id: "stats", label: "统计计算", detail: "指标 / 组水平" },
      { id: "figures", label: "图表生成", detail: "波形 / 热图 / 地形图" },
    ],
  },
  {
    title: "交付出口",
    nodes: [
      { id: "report_package", label: "结果打包", detail: "表 / 图 / manifest" },
      { id: "delivery_review", label: "交付复核", detail: "人工 / 自动规则" },
      { id: "invoice_ready", label: "订单开票", detail: "扣费 / 发票" },
    ],
  },
];

// Any customer task lifecycle change should update this chain first, so admin monitoring stays truthful.
const chainNodeMap = new Map(BUSINESS_CHAIN.flatMap((group) => group.nodes.map((node) => [node.id, node])));

const titles = {
  dashboard: "我的脑电分析项目",
  analysis: "正式数据分析",
  publication: "结果交付",
  teaching: "学习模式",
  billing: "账户账单",
  adminDashboard: "管理员后台总览",
  adminCustomers: "客户与数据管理",
  adminOrders: "订单与开票审核",
  adminMethods: "方法模板与系统配置",
};

const recommendations = {
  p300: {
    title: "推荐：Oddball ERP",
    body: "适合 target / standard 事件标签。先做事件锁定平均、GFP、通道热图和差异波，再核对事件表。",
    params: "Epoch -0.2~0.8 s；baseline -0.2~0 s；条件 target / standard；输出 ERP、GFP、差异波、事件表和复现记录。",
  },
  n400: {
    title: "推荐：ERP / N400 分析",
    body: "语义一致与不一致通常比较 300-500 ms 的负波差异，适合事件锁定 ERP。",
    params: "Epoch -0.2~0.8 s；中顶区通道；指标为 300-500 ms 平均振幅；统计为被试内配对模型。",
  },
  stroop: {
    title: "推荐：冲突 ERP + theta 时频",
    body: "Stroop 同时适合 N2/P3 ERP 与额中线 theta，两者可以作为主分析和补充分析。",
    params: "ERP 窗口 200-450 ms；theta 4-8 Hz；条件为 incongruent-congruent；报告效应量。",
  },
  motor: {
    title: "推荐：运动想象 ERD / 分类",
    body: "left/right hand 标签适合 C3/C4 的 mu 与 beta ERD，同时可给出交叉验证分类准确率。",
    params: "8-30 Hz；事件后 0.5-3.5 s；CSP + LDA；被试内交叉验证和组水平统计。",
  },
  ssvep: {
    title: "推荐：SSVEP 频率标记分析",
    body: "10 Hz / 15 Hz 闪烁属于频率锁定反应，应在对应刺激频率及谐波处提取 SNR。",
    params: "稳态窗 1-6 s；提取 10/15 Hz 与谐波；后枕区通道；置换检验或线性模型。",
  },
  rest: {
    title: "推荐：静息态 PSD / 连通性",
    body: "eyes open / eyes closed 是连续静息范式，优先做频谱、alpha peak 和频段功率。",
    params: "2 s 或 4 s 分窗；Welch PSD；delta/theta/alpha/beta；可扩展相干和图论指标。",
  },
  sleep: {
    title: "推荐：睡眠事件与阶段分析",
    body: "spindle 和 k-complex 属于睡眠 EEG 事件，需要先做阶段或事件检测，再输出密度、振幅和频率。",
    params: "纺锤 11-16 Hz；事件级检测后聚合到被试；统计按阶段和条件分层。",
  },
};

function showToast(message) {
  const toast = qs("#toast");
  if (!toast) return;
  toast.textContent = message;
  toast.classList.add("show");
  window.setTimeout(() => toast.classList.remove("show"), 2400);
}

function statusClass(status = "") {
  if (/失败|待审核|待确认|不足|停用/.test(status)) return "warn";
  if (/运行|队列|处理中|生成中|当前|待支付/.test(status)) return "run";
  return "ok";
}

async function apiRequest(path, payload = null) {
  const options = payload
    ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }
    : { method: "GET" };
  const response = await fetch(`${API_BASE}${path}`, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.ok === false) throw new Error(data.message || "服务请求失败");
  return data;
}

function validatePhone(phone) {
  return /^1[3-9]\d{9}$/.test(String(phone || "").trim());
}

function recordOperation(actor, action, target, source = "前端状态") {
  state.operationLog.unshift({ time: nowTime(), actor, action, target, source });
  state.operationLog = state.operationLog.slice(0, 12);
  renderAdminOperationLog();
}

function tableEmpty(message, columns = 4) {
  return `<div class="table-row empty-row" style="grid-template-columns:1fr"><span>${message}</span></div>`;
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

function currentCustomerName() {
  const customer = getStoredCustomer();
  return customer.name || customer.phone || customer.email || "客户账户";
}

function customerAvatarText(customer = getStoredCustomer()) {
  const source = customer.name || customer.org || customer.phone || customer.email || "全";
  return String(source).trim().slice(0, 1).toUpperCase() || "全";
}

function syncSidebarAccount(profile = getStoredCustomer()) {
  if (state.role === "admin") {
    if (qs("#roleLabel")) qs("#roleLabel").textContent = "管理员后台";
    if (qs("#balanceSide")) qs("#balanceSide").textContent = "运营控制台";
    if (qs("#accountHint")) qs("#accountHint").textContent = "运营管理";
    if (qs("#accountAvatar")) qs("#accountAvatar").textContent = "管";
    return;
  }
  if (qs("#roleLabel")) qs("#roleLabel").textContent = profile.name || "客户账户";
  if (qs("#balanceSide")) qs("#balanceSide").textContent = money(state.balance);
  if (qs("#accountHint")) {
    qs("#accountHint").textContent = profile.phone
      ? `${profile.org || "个人课题"} · ${profile.phone}`
      : profile.email
        ? `${profile.org || "个人课题"} · ${profile.email}`
        : "查看账号、充值和资料";
  }
  if (qs("#accountAvatar")) qs("#accountAvatar").textContent = customerAvatarText(profile);
}

function currentCustomerOrders() {
  const name = currentCustomerName();
  const customer = getStoredCustomer();
  const keys = [name, customer.name, customer.phone, customer.email].filter(Boolean);
  return state.orders.filter((order) => keys.includes(order.customer));
}

function validateEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function setLoginMessage(message, type = "info") {
  const target = qs("#loginMessage");
  if (!target) return;
  target.textContent = message;
  target.classList.toggle("error", type === "error");
  target.classList.toggle("success", type === "success");
}

function applyProductModeUi() {
  document.documentElement.dataset.learningMode = state.teachingModeActive ? "true" : "false";
  const teachingButton = qs("#sidebarTeachingBtn");
  if (teachingButton) {
    const title = teachingButton.querySelector("strong");
    const sub = teachingButton.querySelector("small");
    if (title) title.textContent = state.teachingModeActive ? "退出教学模式" : "教学模式";
    if (sub) sub.textContent = state.teachingModeActive ? "回到正式项目" : "导入示例项目";
  }
  if (!isV0Mode) return;
  document.title = "QLanalyser V0 研究交付版";
  const loginTitle = qs(".login-card h2");
  if (loginTitle) loginTitle.textContent = "V0 客户入口";
  const subtitle = qs(".product-subtitle");
  if (subtitle) subtitle.textContent = "保留完整平台入口，把主流程收束成一次可复核的 EEG 到 ERP 交付体验。";
  const proof = qs(".product-proof-strip");
  if (proof) proof.innerHTML = "<span>项目</span><span>预览</span><span>ERP</span><span>manifest</span>";
  const loginButton = qs('#customerLoginForm button[type="submit"] span');
  if (loginButton) loginButton.textContent = "进入 V0 工作台";
  const projectButton = qs("#tutorialBtn");
  if (projectButton) {
    projectButton.dataset.projectAction = "load-v0-sample";
    const label = projectButton.querySelector("span");
    if (label) label.textContent = "加载 V0 样例";
  }
  qsa('.nav-item[data-role="admin"]').forEach((item) => {
    item.hidden = true;
    item.style.display = "none";
  });
  qsa('.flow-rail [data-view-jump="billing"]').forEach((item) => {
    item.hidden = true;
    item.style.display = "none";
  });
  if (qs("#topEyebrow")) qs("#topEyebrow").textContent = "V0 研究交付版";
  if (state.role === "customer") {
    syncSidebarAccount();
    if (qs("#accountHint")) qs("#accountHint").textContent = "V0 试用账号 · 查看资料与充值";
  }
  const message = qs("#loginMessage");
  if (message && !message.textContent.trim() && qs("#loginScreen") && !qs("#loginScreen").hidden) {
    setLoginMessage("测试账号：demo@qlanalyser.local / demo123456", "success");
  }
}

function switchLoginTab(tab) {
  qsa("[data-login-tab]").forEach((button) => button.classList.toggle("active", button.dataset.loginTab === tab));
  qsa(".login-form").forEach((form) => form.classList.toggle("active", form.id === `${tab}Form`));
  setLoginMessage("");
}

function rememberSession(role, persist = true) {
  const session = JSON.stringify({ role, savedAt: new Date().toISOString() });
  if (persist) localStorage.setItem(AUTH_KEY, session);
  else sessionStorage.setItem(AUTH_KEY, session);
}

function clearSession() {
  localStorage.removeItem(AUTH_KEY);
  sessionStorage.removeItem(AUTH_KEY);
}

function enhanceControlLabels() {
  qsa(".nav-item, .icon-btn").forEach((button) => {
    const label = button.getAttribute("aria-label") || button.getAttribute("title") || button.textContent.trim();
    if (!label) return;
    button.setAttribute("title", label);
    button.setAttribute("aria-label", label);
  });
}

function renderAdminCustomerProfile() {
  renderAdminCustomers();
}

function storedCustomerDisplay() {
  const customer = getStoredCustomer();
  return {
    id: "customer-local",
    name: customer.name || "未命名客户",
    email: customer.phone || customer.email || "未绑定手机号",
    org: customer.org || "未填写单位",
    registeredAt: customer.registeredAt || "未登记",
    dataSize: state.projects.reduce((sum, project) => sum + (parseFloat(project.size) || 0), 0).toFixed(1) + " GB",
    balance: state.balance,
    status: customer.phoneVerifiedAt ? "正常" : "待验证手机号",
    source: "客户账户资料",
  };
}

function adminCustomerRows() {
  const local = storedCustomerDisplay();
  return [
    local,
    { id: "customer-sample", name: "后台监控样本客户", email: "sample-customer@example.cn", org: "样本课题组", registeredAt: "2026-06-10", dataSize: "2.4 GB", balance: 2480, status: "正常", source: "后台监控样本" },
    { id: "customer-cog", name: "认知神经实验室", email: "cognitive-lab@example.cn", org: "高校实验室", registeredAt: "2026-06-08", dataSize: "3.4 GB", balance: 580, status: "任务失败待处理", source: "后台任务链路" },
  ];
}

function renderAdminCustomers() {
  const table = qs("#adminCustomerTable");
  if (!table) return;
  table.innerHTML = [
    `<div class="table-row head"><span>客户</span><span>单位</span><span>数据</span><span>余额</span><span>状态</span></div>`,
    ...adminCustomerRows().map((customer) => `
      <div class="table-row">
        <span>${customer.name}<small>${customer.email}</small></span>
        <span>${customer.org}<small>来源：${customer.source}</small></span>
        <span>${customer.dataSize}</span>
        <span>${money(customer.balance)}</span>
        <span class="${statusClass(customer.status)}">${customer.status}</span>
      </div>
    `),
  ].join("");
}

function renderAdminMetrics() {
  const target = qs("#adminMetrics");
  if (!target) return;
  const customers = adminCustomerRows();
  const running = state.adminTasks.filter((task) => !task.failedNodeIds.length && task.currentNodeId !== "invoice_ready" && task.currentNodeId !== "delivery_review").length;
  const failed = state.adminTasks.filter((task) => task.failedNodeIds.length).length;
  const taskCost = state.orders.filter((order) => order.type === "任务扣费").reduce((sum, order) => sum + order.amount, 0);
  const delivered = state.adminTasks.filter((task) => ["delivery_review", "invoice_ready"].includes(task.currentNodeId)).length;
  const sla = state.adminTasks.length ? (delivered / state.adminTasks.length) * 100 : 0;
  target.innerHTML = `
    <div class="metric"><span>客户数</span><strong>${customers.length}</strong><small>来自客户资料与后台示例账户</small></div>
    <div class="metric"><span>任务</span><strong>${state.adminTasks.length}</strong><small>${running} 个运行中，${failed} 个失败</small></div>
    <div class="metric"><span>任务收入</span><strong>${money(taskCost)}</strong><small>来自订单流水</small></div>
    <div class="metric"><span>交付占比</span><strong>${sla.toFixed(1)}%</strong><small>来自业务链路节点</small></div>
  `;
}

function renderAdminQueueGrid() {
  const queue = qs("#adminQueueGrid");
  if (queue) {
    const count = (nodeIds) => state.adminTasks.filter((task) => nodeIds.includes(task.currentNodeId)).length;
    queue.innerHTML = `
      <div><strong>预处理队列</strong><span>滤波、重参考、坏道检测、ICA</span><b>${count(["preprocess", "quality_check"])} 个任务</b></div>
      <div><strong>分析队列</strong><span>ERP、PSD、时频、拓扑图、机器学习</span><b>${count(["queue_assign", "format_parse", "method_route", "mne_worker", "stats", "figures"])} 个任务</b></div>
      <div><strong>交付队列</strong><span>结果包、复核、订单开票</span><b>${count(["report_package", "delivery_review", "invoice_ready"])} 个任务</b></div>
    `;
  }
  const priority = qs("#adminPriorityGrid");
  if (priority) {
    const pendingInvoices = state.orders.filter((order) => order.type === "开票" && order.status === "待审核").length;
    const failedTasks = state.adminTasks.filter((task) => task.failedNodeIds.length).length;
    const missingProfiles = adminCustomerRows().filter((customer) => customer.status.includes("待补")).length;
    priority.innerHTML = `
      <div><strong>今日待处理</strong><span>失败任务、发票复核、客户资料。</span><b>${failedTasks + pendingInvoices + missingProfiles} 项</b></div>
      <div><strong>任务失败</strong><span>可在业务链路中定位失败节点。</span><b>${failedTasks} 项</b></div>
      <div><strong>开票审核</strong><span>来自客户开票申请。</span><b>${pendingInvoices} 项</b></div>
    `;
  }
}

function renderChecklists() {
  const risk = qs("#adminRiskChecklist");
  if (risk) {
    const items = [
      ["uploadResume", "大文件上传续传正常"],
      ["balanceGuard", "余额不足任务已拦截"],
      ["invoiceReview", `${state.orders.filter((order) => order.type === "开票" && order.status === "待审核").length} 个发票信息待复核`],
      ["archivePolicy", "数据归档策略待确认"],
    ];
    risk.innerHTML = items.map(([key, label]) => `<label><input type="checkbox" data-system-check="${key}" ${state.systemStatus.riskChecks[key] ? "checked" : ""} /> ${label}</label>`).join("");
  }
  const system = qs("#adminSystemChecklist");
  if (system) {
    const items = [
      ["mneOnline", "MNE 分析服务在线"],
      ["eeglabMapped", "EEGLAB 模板已映射"],
      ["deliveryOnline", "结果包生成服务正常"],
      ["scaleApproval", "计算资源扩容待审批"],
    ];
    system.innerHTML = items.map(([key, label]) => `<label><input type="checkbox" data-system-status="${key}" ${state.systemStatus[key] ? "checked" : ""} /> ${label}</label>`).join("");
  }
  const invoice = qs("#invoiceStatusChecklist");
  if (invoice) {
    const latest = state.invoices.find((item) => item.customer === currentCustomerName());
    const orders = currentCustomerOrders();
    invoice.innerHTML = [
      ["订单已扣费", orders.some((order) => order.type === "任务扣费" && order.status === "已扣费")],
      ["项目和 PI 已匹配", Boolean(getStoredCustomer().name || getStoredCustomer().org)],
      ["发票信息审核", latest?.status === "已审核" || latest?.status === "已发送"],
      ["电子发票发送", latest?.status === "已发送"],
    ].map(([label, checked]) => `<label><input type="checkbox" data-invoice-check disabled ${checked ? "checked" : ""} /> ${label}</label>`).join("");
  }
  bindChecklistHandlers();
}

function bindChecklistHandlers() {
  qsa("[data-system-check]").forEach((input) => input.addEventListener("change", () => {
    state.systemStatus.riskChecks[input.dataset.systemCheck] = input.checked;
    recordOperation("管理员", input.checked ? "确认风控项" : "取消风控项", input.parentElement.textContent.trim(), "风控检查表");
    showToast(input.checked ? "检查项已确认" : "检查项已取消");
  }));
  qsa("[data-system-status]").forEach((input) => input.addEventListener("change", () => {
    state.systemStatus[input.dataset.systemStatus] = input.checked;
    recordOperation("管理员", "更新系统状态", input.parentElement.textContent.trim(), "系统状态表");
    showToast("系统状态已更新");
  }));
}

function renderAdminOrders() {
  const table = qs("#adminOrderTable");
  if (table) {
    table.innerHTML = [
      `<div class="table-row head"><span>订单</span><span>客户</span><span>金额</span><span>状态</span><span>处理</span></div>`,
      ...state.orders.map((order) => {
        const action = order.status === "待审核" ? "审核通过" : order.status === "已冻结" ? "确认扣费" : "记录复核";
        const label = order.status === "待审核" ? "审核" : order.status === "已冻结" ? "扣费" : "复核";
        return `
        <div class="table-row">
          <span>${order.id}<small>${order.type} / ${order.createdAt}</small></span>
          <span>${order.customer}<small>来源：${order.source}</small></span>
          <span>${money(order.amount)}</span>
          <span class="${statusClass(order.status)}">${order.status}</span>
          <span class="row-actions"><button type="button" data-order-action="${action}" data-order-id="${order.id}">${label}</button></span>
        </div>
      `;
      }),
    ].join("");
  }
  const customerTable = qs("#customerOrderTable");
  if (customerTable) {
    const customerOrders = currentCustomerOrders();
    customerTable.innerHTML = [
      `<div class="table-row head"><span>流水</span><span>类型</span><span>金额</span><span>状态</span><span>时间</span></div>`,
      ...(customerOrders.length ? customerOrders.map((order) => `
        <div class="table-row">
          <span>${order.id}<small>${order.source}</small></span>
          <span>${order.type}</span>
          <span>${money(order.amount)}</span>
          <span class="${statusClass(order.status)}">${order.status}</span>
          <span>${order.createdAt}</span>
        </div>
      `) : [tableEmpty("还没有账户流水。充值、提交分析或申请开票后才会显示记录。")]),
    ].join("");
  }
  renderFinanceSummary();
  qsa("[data-order-action]").forEach((button) => button.addEventListener("click", () => handleOrderAction(button.dataset.orderAction, button.dataset.orderId)));
}

function renderFinanceSummary() {
  const admin = qs("#adminFinanceSummary");
  if (admin) {
    const recharge = state.orders.filter((order) => order.type === "充值").reduce((sum, order) => sum + order.amount, 0);
    const charge = state.orders.filter((order) => order.type === "任务扣费").reduce((sum, order) => sum + order.amount, 0);
    const invoice = state.orders.filter((order) => order.type === "开票" && order.status === "待审核").reduce((sum, order) => sum + order.amount, 0);
    admin.innerHTML = `
      <div class="cost-row"><span>充值入账</span><b>${money(recharge)}</b></div>
      <div class="cost-row"><span>任务扣费</span><b>${money(charge)}</b></div>
      <div class="cost-row total"><span>待开发票</span><b>${money(invoice)}</b></div>
    `;
  }
  const customer = qs("#customerBillingSummary");
  if (customer) {
    const charged = currentCustomerOrders().filter((order) => order.type === "任务扣费").reduce((sum, order) => sum + order.amount, 0);
    customer.innerHTML = `
      <div class="cost-row"><span>当前项目</span><b>${activeProject()?.name || "-"}</b></div>
      <div class="cost-row"><span>单价</span><b>￥1 / h</b></div>
      <div class="cost-row total"><span>已扣</span><b>${money(charged)}</b></div>
      <div class="cost-row"><span>当前余额</span><b>${money(state.balance)}</b></div>
    `;
  }
}

function renderAdminMethods() {
  const methods = qs("#adminMethodGrid");
  if (methods) {
    const smsStatus = state.platform?.sms?.productionReady ? "生产短信" : "短信沙箱";
    const paymentStatus = state.platform?.payment?.productionReady ? "支付宝生产" : "支付宝沙箱";
    methods.innerHTML = `
      <div><strong>MNE 模板</strong><span>Raw 预览、Epoch、Evoked、PSD、TFR、Topomap</span><b>${templates.length} 个启用</b></div>
      <div><strong>EEGLAB 对照</strong><span>runica、ERSP、topoplot、事件锁定 ERP</span><b>${state.systemStatus.eeglabMapped ? "已映射" : "待映射"}</b></div>
      <div><strong>计费策略</strong><span>按记录时长、任务类型、加急和存储周期计费</span><b>￥1 / h</b></div>
      <div><strong>注册短信</strong><span>手机号验证码注册，验证码服务端校验。</span><b>${smsStatus}</b></div>
      <div><strong>支付宝</strong><span>服务端创建订单，异步通知后入账。</span><b>${paymentStatus}</b></div>
    `;
  }
  const capacity = qs("#adminCapacityGrid");
  if (capacity) {
    const queued = state.adminTasks.filter((task) => task.currentNodeId === "queue_assign").length;
    capacity.innerHTML = `
      <div><strong>上传入口</strong><span>分片、断点续传、对象存储落盘。</span><b>目标 10,000 并发会话</b></div>
      <div><strong>任务队列</strong><span>预处理、分析、报告生成拆分调度。</span><b>${queued} 个等待调度</b></div>
      <div><strong>计算池</strong><span>按租户额度、任务优先级和资源水位分配。</span><b>${state.systemStatus.scaleApproval ? "扩容审批通过" : "按需扩容待审批"}</b></div>
    `;
  }
  if (qs("#adminTeachingLockStatus")) {
    qs("#adminTeachingLockStatus").textContent = state.systemStatus.teachingEnabled
      ? `系统锁定，客户不可删除 / 版本 ${state.systemStatus.teachingVersion}`
      : "教学入口已停用，原始 EDF 仍锁定保存";
    qs("#adminTeachingLockStatus").className = state.systemStatus.teachingEnabled ? "ok" : "warn";
  }
}

function renderAdminOperationLog() {
  const target = qs("#adminOperationLog");
  if (!target) return;
  target.innerHTML = state.operationLog.map((item) => `
    <div class="operation-row">
      <span>${item.time}</span>
      <strong>${item.actor} · ${item.action}</strong>
      <b>${item.target}</b>
      <em>${item.source}</em>
    </div>
  `).join("");
}

function renderPaymentStatus() {
  const target = qs("#paymentStatus");
  const actions = qs("#paymentActions");
  const gateway = qs("#alipayGatewayLink");
  const mockButton = qs("#mockAlipayNotifyBtn");
  const order = state.payment.activeOrder;
  if (!target) return;
  if (!order) {
    target.innerHTML = `<div class="notice neutral compact-notice"><i data-lucide="wallet-cards"></i><span>选择金额后创建支付宝订单。</span></div>`;
    if (actions) actions.hidden = true;
    return;
  }
  target.innerHTML = `
    <div class="payment-card">
      <span>支付宝订单</span>
      <strong>${order.paymentNo}</strong>
      <b class="${statusClass(order.status)}">${order.status}</b>
      <small>${order.source || order.api} / ${money(order.amount)}</small>
    </div>
  `;
  if (gateway) gateway.href = order.gatewayUrl || "#";
  if (mockButton) mockButton.hidden = !order.sandbox;
  if (actions) actions.hidden = order.status === "已入账";
}

function renderAccountSettings() {
  const customer = getStoredCustomer();
  if (qs("#profileName")) qs("#profileName").value = customer.name || "";
  if (qs("#profilePhone")) qs("#profilePhone").value = customer.phone ? `${customer.phone}（已验证）` : "未绑定";
  if (qs("#profileEmail")) qs("#profileEmail").value = customer.email || "";
  if (qs("#profileOrg")) qs("#profileOrg").value = customer.org || "";
  if (qs("#profilePassword")) qs("#profilePassword").value = "";
  if (qs("#profilePasswordConfirm")) qs("#profilePasswordConfirm").value = "";
  if (qs("#invoiceEmail")) qs("#invoiceEmail").value = customer.email || "";
  if (qs("#invoiceTitle")) qs("#invoiceTitle").value = customer.org && customer.org !== "未填写单位" ? customer.org : "";
  renderFinanceSummary();
  renderAdminOrders();
  renderChecklists();
  renderPaymentStatus();
  if (window.lucide) lucide.createIcons();
}

function renderAllAdmin() {
  renderAdminMetrics();
  renderAdminQueueGrid();
  renderAdminCustomers();
  renderAdminOrders();
  renderAdminMethods();
  renderAdminTaskMonitor();
  renderAdminOperationLog();
  renderChecklists();
}

function handleOrderAction(action, orderId) {
  const order = state.orders.find((item) => item.id === orderId);
  if (!order) return;
  if (action === "审核通过") {
    order.status = "已审核";
    order.handler = "管理员";
    const invoice = state.invoices.find((item) => item.amount === order.amount && item.customer === order.customer);
    if (invoice) invoice.status = "已审核";
    recordOperation("管理员", "审核订单", order.id, order.source);
    showToast(`已审核：${order.id}`);
  } else if (action === "确认扣费") {
    order.status = "已扣费";
    order.handler = "管理员确认";
    const project = state.projects.find((item) => item.id === order.projectId);
    completeProjectForLocalDemo(project, order.source || order.id, order.amount);
    const task = state.adminTasks.find((item) => item.id === order.taskId);
    if (task) {
      task.currentNodeId = "delivery_review";
      task.doneNodeIds = ["intake", "profile_check", "cost_freeze", "upload_store", "queue_assign", "format_parse", "preprocess", "quality_check", "method_route", "mne_worker", "stats", "figures", "report_package"];
      task.history.push(
        { time: nowTime(), nodeId: "mne_worker", status: "完成", note: "本地验收：分析 worker 完成" },
        { time: nowTime(), nodeId: "delivery_review", status: "当前", note: "交付件等待客户查看" },
      );
      state.adminActiveTaskId = task.id;
    }
    recordOperation("管理员", "确认任务扣费", order.id, project?.name || order.source);
    showToast(`已扣费并生成交付：${order.id}`);
  } else {
    recordOperation("管理员", "复核订单", order.id, order.status);
    showToast(`已记录复核：${order.id}`);
  }
  renderAllAdmin();
  renderAccountSettings();
  renderProjects();
  renderPublication();
}

async function handleAdminSystemAction(action) {
  if (action === "校验教学数据") {
    try {
      const response = await fetch(TEACHING_DATASET.manifestUrl);
      const manifest = response.ok ? await response.json() : null;
      const channels = manifest?.channels?.length || TEACHING_DATASET.channelCount;
      state.systemStatus.teachingVerifiedAt = `${today()} ${nowTime()}`;
      renderTeachingDataset(manifest);
      recordOperation("管理员", "校验教学数据", `${channels} 通道`, TEACHING_DATASET.manifestUrl);
      showToast(channels === 64 ? "教学 EDF 已校验：64 通道" : `教学数据通道数异常：${channels}`);
    } catch (error) {
      recordOperation("管理员", "校验教学数据失败", TEACHING_DATASET.name, error.message || "fetch failed");
      showToast("教学数据校验失败");
    }
  }
  if (action === "更新教学版本") {
    state.systemStatus.teachingVersion = today().replace(/\//g, ".");
    recordOperation("管理员", "更新教学版本", TEACHING_DATASET.name, state.systemStatus.teachingVersion);
    showToast(`教学版本已更新：${state.systemStatus.teachingVersion}`);
  }
  if (action === "停用教学入口") {
    state.systemStatus.teachingEnabled = !state.systemStatus.teachingEnabled;
    recordOperation("管理员", state.systemStatus.teachingEnabled ? "启用教学入口" : "停用教学入口", TEACHING_DATASET.name, "系统配置");
    showToast(state.systemStatus.teachingEnabled ? "教学入口已启用" : "教学入口已停用");
  }
  renderAdminMethods();
  renderAdminOperationLog();
}

function saveProfileFromForm() {
  const name = qs("#profileName")?.value.trim() || "";
  const email = qs("#profileEmail")?.value.trim() || "";
  const org = qs("#profileOrg")?.value.trim() || "";
  const password = qs("#profilePassword")?.value || "";
  const passwordConfirm = qs("#profilePasswordConfirm")?.value || "";
  if (!name) {
    showToast("请填写账户名");
    return;
  }
  if (email && !validateEmail(email)) {
    showToast("请填写有效邮箱");
    return;
  }
  if (password || passwordConfirm) {
    if (password.length < 8) {
      showToast("新密码至少 8 位");
      return;
    }
    if (password !== passwordConfirm) {
      showToast("两次输入的新密码不一致");
      return;
    }
  }
  const current = getStoredCustomer();
  const profile = {
    ...current,
    name,
    phone: current.phone || "",
    phoneVerifiedAt: current.phoneVerifiedAt || "",
    email,
    org: org || "未填写单位",
    password: password || current.password,
    registeredAt: current.registeredAt || new Date().toLocaleString("zh-CN", { hour12: false }),
  };
  saveCustomer(profile);
  if (qs("#profileNotice span")) qs("#profileNotice span").textContent = password ? "账户信息和密码已保存。" : "账户信息已保存。";
  syncSidebarAccount(profile);
  recordOperation("客户", "保存账户资料", profile.name, profile.phone || profile.email);
  renderAdminCustomers();
  renderAccountSettings();
  showToast("账户信息已保存");
}

function submitInvoice() {
  const customer = getStoredCustomer();
  const billableOrders = currentCustomerOrders().filter((order) => order.type === "任务扣费" && order.status === "已扣费");
  if (!billableOrders.length) {
    showToast("还没有可开票的已扣费订单");
    return;
  }
  const title = qs("#invoiceTitle")?.value.trim() || customer.org || "";
  const taxId = qs("#invoiceTaxId")?.value.trim() || "";
  const amount = Math.max(0, Number(qs("#invoiceAmount")?.value || 0));
  const email = qs("#invoiceEmail")?.value.trim() || customer.email || "";
  if (!title || !taxId || !amount || !validateEmail(email)) {
    showToast("请补全发票抬头、税号、金额和邮箱");
    return;
  }
  const createdAt = new Date().toLocaleString("zh-CN", { hour12: false });
  const invoiceId = `INV-${Date.now()}`;
  const orderId = `QL-${Date.now()}-INV`;
  const customerName = currentCustomerName();
  state.invoices.unshift({ id: invoiceId, customer: customerName, title, taxId, amount, email, status: "待审核", createdAt });
  state.orders.unshift({ id: orderId, customer: customerName, type: "开票", amount, status: "待审核", source: invoiceId, createdAt, handler: "管理员审核" });
  const notice = qs("#invoiceNotice span");
  if (notice) notice.textContent = `开票申请已提交：${invoiceId}，等待管理员审核。`;
  recordOperation("客户", "提交开票申请", invoiceId, `${title} / ${money(amount)}`);
  renderAccountSettings();
  renderAllAdmin();
  showToast("开票申请已提交");
}

function appendPaymentAdminTask(order, status = "待支付") {
  const existing = state.adminTasks.find((task) => task.paymentNo === order.paymentNo);
  const now = nowTime();
  if (existing) {
    existing.currentNodeId = status === "已入账" ? "payment_notify" : "payment_create";
    existing.doneNodeIds = status === "已入账" ? ["payment_create", "payment_notify"] : ["payment_create"];
    existing.history.push({
      time: now,
      nodeId: existing.currentNodeId,
      status: status === "已入账" ? "完成" : "当前",
      note: status === "已入账" ? `支付宝回调入账 ${money(order.amount)}` : "等待支付宝支付回调",
    });
    state.adminActiveTaskId = existing.id;
    return existing;
  }
  const id = `admin-payment-${Date.now()}`;
  const task = {
    id,
    paymentNo: order.paymentNo,
    customer: order.customer || getStoredCustomer().name || "客户账户",
    project: "账户充值",
    file: order.provider || "支付宝",
    size: "-",
    cost: order.amount,
    submittedAt: order.createdAt || new Date().toLocaleString("zh-CN", { hour12: false }),
    currentNodeId: status === "已入账" ? "payment_notify" : "payment_create",
    failedNodeIds: [],
    doneNodeIds: status === "已入账" ? ["payment_create", "payment_notify"] : ["payment_create"],
    history: [
      { time: now, nodeId: "payment_create", status: "完成", note: `创建支付宝订单 ${order.paymentNo}` },
      { time: now, nodeId: status === "已入账" ? "payment_notify" : "payment_create", status: status === "已入账" ? "完成" : "当前", note: status === "已入账" ? `支付宝回调入账 ${money(order.amount)}` : "等待支付宝支付回调" },
    ],
  };
  state.adminTasks.unshift(task);
  state.adminActiveTaskId = id;
  return task;
}

async function createAlipayRecharge() {
  if (state.selectedPayMethod !== "支付宝") {
    showToast("当前仅接入支付宝");
    return;
  }
  try {
    const customer = getStoredCustomer();
    const data = await apiRequest("/api/payments/alipay/create", {
      amount: state.rechargeAmount,
      customer: customer.name || customer.phone || "客户账户",
    });
    state.payment.activeOrder = data.order;
    appendPaymentAdminTask(data.order, "待支付");
    state.orders.unshift({
      id: data.order.paymentNo,
      customer: data.order.customer,
      type: "充值",
      amount: data.order.amount,
      status: "待支付",
      source: `${data.order.source} / ${data.order.api}`,
      createdAt: data.order.createdAt,
      handler: "支付宝网关",
    });
    recordOperation("客户", "创建支付宝订单", data.order.paymentNo, money(data.order.amount));
    renderAccountSettings();
    renderAllAdmin();
    showToast("支付宝订单已创建，等待支付回调");
  } catch (error) {
    state.payment.lastError = error.message || "创建支付宝订单失败";
    renderPaymentStatus();
    showToast(state.payment.lastError);
  }
}

async function mockAlipayNotify() {
  const order = state.payment.activeOrder;
  if (!order?.paymentNo) {
    showToast("没有待支付订单");
    return;
  }
  try {
    const data = await apiRequest("/api/payments/alipay/mock-notify", { paymentNo: order.paymentNo });
    state.payment.activeOrder = data.order;
    const ledger = state.orders.find((item) => item.id === data.order.paymentNo);
    const alreadySettled = ledger?.status === "已入账";
    if (!alreadySettled) state.balance += data.order.amount;
    if (ledger) {
      ledger.status = "已入账";
      ledger.handler = "支付宝异步通知";
      ledger.source = `${data.order.source} / trade_no ${data.order.tradeNo}`;
      ledger.createdAt = data.order.paidAt || ledger.createdAt;
    }
    appendPaymentAdminTask(data.order, "已入账");
    updateBalance();
    recordOperation("系统", "支付宝入账", data.order.paymentNo, `${data.order.tradeNo} / ${money(data.order.amount)}`);
    renderAccountSettings();
    renderAllAdmin();
    showToast(`支付宝入账成功：${money(data.order.amount)}`);
  } catch (error) {
    showToast(error.message || "支付宝回调失败");
  }
}

function activeProject() {
  return state.projects.find((project) => project.id === state.activeProjectId) || null;
}

function isLearningProject(project = activeProject()) {
  return Boolean(project?.mode === "learning" || project?.learningMode);
}

function ensureProjectFiles(project) {
  if (!project) return [];
  if (!Array.isArray(project.files)) project.files = [];
  return project.files;
}

function primaryProjectFile(project) {
  const files = ensureProjectFiles(project).filter((file) => !(isLearningProject(project) && /事件表|CSV|TSV/.test(file.type)));
  return files.find((file) => /EDF|BDF|SET|FIF/.test(file.type)) || files[0] || null;
}

function inferDeliveryType(item) {
  const value = `${item.type || ""} ${item.href || ""}`.toLowerCase();
  if (value.includes(".png") || value.includes(".jpg") || value.includes(".jpeg") || value.includes(".svg")) return "image";
  if (value.includes(".json")) return "json";
  if (value.includes(".csv")) return "csv";
  if (value.includes(".tsv")) return "tsv";
  if (value.includes(".txt")) return "text";
  if (value.includes(".edf")) return "edf";
  if (value.includes(".bdf")) return "bdf";
  if (value.includes(".zip")) return "zip";
  return item.type || "file";
}

function fileNameFromHref(href = "") {
  return decodeURIComponent(String(href).split("?")[0].split("/").pop() || "delivery-file");
}

function registerDeliveryItems(items = [], scope = "") {
  items.forEach((item, index) => {
    const id = item.id || `${scope || "delivery"}-${index}`;
    deliveryPreviewRegistry.set(id, {
      ...item,
      id,
      type: inferDeliveryType(item),
      fileName: item.fileName || fileNameFromHref(item.href),
    });
  });
}

function deliveryButtonHtml(item, className = "ghost-link") {
  return `
    <button type="button" class="${className}" data-preview-download="${item.id}">
      <i data-lucide="${item.icon || "file"}"></i><strong>${escapeHtml(item.label)}</strong><span>${escapeHtml(item.detail || "点击后先预览")}</span>
    </button>
  `;
}

function deliveryItemGroup(item = {}) {
  if (inferDeliveryType(item) === "image" || item.icon === "image") return "figures";
  if (item.icon === "table" || item.icon === "list-tree" || /\.(csv|tsv)$/i.test(item.href || "")) return "tables";
  if (item.icon === "file-text" || /\.txt$/i.test(item.href || "")) return "methods";
  if (item.icon === "file-json" || /\.json$/i.test(item.href || "")) return "reproduce";
  return "package";
}

function groupedDeliveryHtml(items = []) {
  if (!items.length) {
    return `
      <div class="delivery-group">
        <div class="delivery-group-head"><strong>交付包</strong><span>等待后台写入正式文件</span></div>
        <div class="delivery-grid">
          <div class="ghost-link disabled-link"><i data-lucide="archive"></i><strong>结果包</strong><span>真实后台生成 ZIP 后开放下载</span></div>
          <div class="ghost-link disabled-link"><i data-lucide="table"></i><strong>统计表</strong><span>真实分析 worker 完成后写入</span></div>
          <div class="ghost-link disabled-link"><i data-lucide="file-text"></i><strong>Methods 文本</strong><span>绑定模板、参数和软件版本</span></div>
          <div class="ghost-link disabled-link"><i data-lucide="file-json"></i><strong>复现记录</strong><span>绑定数据哈希、参数和任务链路</span></div>
        </div>
      </div>
    `;
  }
  const groups = [
    { id: "figures", title: "结果图", desc: "下载前可预览图像" },
    { id: "tables", title: "统计表", desc: "指标表和事件表" },
    { id: "methods", title: "Methods", desc: "论文方法描述" },
    { id: "reproduce", title: "复现记录", desc: "manifest 与参数链路" },
    { id: "package", title: "交付包", desc: "完整归档与打包下载" },
  ];
  return groups.map((group) => {
    const groupItems = items.filter((item) => deliveryItemGroup(item) === group.id);
    if (!groupItems.length) return "";
    return `
      <div class="delivery-group">
        <div class="delivery-group-head"><strong>${group.title}</strong><span>${group.desc}</span></div>
        <div class="delivery-grid">
          ${groupItems.map((item) => deliveryButtonHtml(item)).join("")}
        </div>
      </div>
    `;
  }).join("");
}

function bindDeliveryPreviewButtons(root = document) {
  root.querySelectorAll("[data-preview-download]").forEach((button) => {
    button.onclick = () => openDeliveryPreview(button.dataset.previewDownload);
  });
}

function closeDeliveryPreview() {
  state.activeDeliveryPreview = null;
  const modal = qs("#deliveryPreviewModal");
  if (modal) modal.hidden = true;
}

async function previewTextFile(item) {
  const response = await fetch(item.href);
  if (!response.ok) throw new Error("文件预览失败");
  const text = await response.text();
  if (item.type === "json") {
    try {
      return JSON.stringify(JSON.parse(text), null, 2).slice(0, 8000);
    } catch {
      return text.slice(0, 8000);
    }
  }
  return text.split(/\r?\n/).slice(0, 80).join("\n");
}

async function openDeliveryPreview(id) {
  const item = deliveryPreviewRegistry.get(id);
  if (!item) {
    showToast("交付件还没有可预览的来源");
    return;
  }
  state.activeDeliveryPreview = item;
  const modal = qs("#deliveryPreviewModal");
  const title = qs("#deliveryPreviewTitle");
  const meta = qs("#deliveryPreviewMeta");
  const body = qs("#deliveryPreviewBody");
  const downloadBtn = qs("#deliveryDownloadBtn");
  if (!modal || !title || !meta || !body || !downloadBtn) return;
  modal.hidden = false;
  title.textContent = item.label || item.fileName;
  meta.textContent = `${item.fileName} · ${item.source || "当前项目"}${item.size ? ` · ${item.size}` : ""}`;
  body.innerHTML = `<div class="preview-loading">正在生成预览...</div>`;
  downloadBtn.onclick = () => {
    const anchor = document.createElement("a");
    anchor.href = item.href;
    anchor.download = item.fileName || "";
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    recordOperation(state.role === "admin" ? "管理员" : "客户", "确认下载交付件", item.label || item.fileName, item.source || "-");
    showToast(`开始下载：${item.label || item.fileName}`);
  };
  try {
    if (item.type === "image") {
      body.innerHTML = `<figure class="delivery-image-preview"><img src="${item.href}" alt="${escapeHtml(item.label)}" /><figcaption>${escapeHtml(item.detail || item.fileName)}</figcaption></figure>`;
    } else if (["json", "csv", "tsv", "text"].includes(item.type)) {
      const text = await previewTextFile(item);
      body.innerHTML = `<pre>${escapeHtml(text)}</pre>`;
    } else if (item.type === "zip") {
      body.innerHTML = `<div class="delivery-file-summary"><strong>${escapeHtml(item.fileName)}</strong><span>${escapeHtml(item.detail || "结果包")}</span><small>ZIP 包下载前显示来源、文件名和内容摘要；正式版可接入服务端目录清单。</small></div>`;
    } else if (item.type === "edf" || item.type === "bdf") {
      body.innerHTML = `<div class="delivery-file-summary"><strong>${escapeHtml(item.fileName)}</strong><span>${escapeHtml(item.meta || item.detail || "脑电原始数据")}</span><small>脑电原始文件下载前应先在预览器核对通道、时长和事件。</small></div>`;
    } else {
      body.innerHTML = `<div class="delivery-file-summary"><strong>${escapeHtml(item.fileName)}</strong><span>${escapeHtml(item.detail || "交付文件")}</span></div>`;
    }
  } catch (error) {
    body.innerHTML = `<div class="notice warn compact-notice"><i data-lucide="triangle-alert"></i><span>${escapeHtml(error.message || "预览失败")}</span></div>`;
  }
  if (window.lucide) lucide.createIcons();
}

function createFormalProject(name = "") {
  const createdAt = nowDateTime();
  const domainProject = domainFactory.createProject({
    name: name || `正式分析项目 ${state.projects.length + 1}`,
    status: "draft",
    ownerId: currentCustomerName(),
    createdAt,
    updatedAt: createdAt,
  });
  const project = {
    ...domainProject,
    file: "等待上传 EEG 文件",
    stage: "待上传",
    queue: "未提交",
    size: "-",
    createdAt,
    updated: today(),
    analyzedAt: "",
    locked: false,
    owner: getStoredCustomer().name || "客户账户",
    files: [],
    result: { status: "未生成", badge: "未提交", note: "上传数据并提交分析后显示结果状态。" },
  };
  state.projects.unshift(project);
  state.activeProjectId = project.id;
  return project;
}

function linkProjectIds(project, key, ids) {
  if (!project || !key) return;
  if (!Array.isArray(project[key])) project[key] = [];
  ids.filter(Boolean).forEach((id) => {
    if (!project[key].includes(id)) project[key].push(id);
  });
}

function createLearningProjectFromTeaching() {
  const existing = state.projects.find((project) => project.mode === "learning" && project.teachingDatasetId === TEACHING_DATASET.id);
  if (existing) {
    state.activeProjectId = existing.id;
    return existing;
  }
  const project = createFormalProject(`学习体验：${TEACHING_DATASET.name}`);
  project.mode = "learning";
  project.learningMode = true;
  project.teachingDatasetId = TEACHING_DATASET.id;
  project.file = `system/${TEACHING_DATASET.edfUrl.split("/").pop()}`;
  project.stage = "待确认";
  project.queue = "免扣费体验";
  project.size = `${TEACHING_DATASET.channelCount} 通道 / ${TEACHING_DATASET.durationSec} 秒`;
  project.locked = true;
  project.result = { status: "未生成", badge: "学习模式免扣费", note: "使用系统预置数据走正式分析流程，不消耗余额，不生成收费订单。" };
  project.files = [{
    ...domainFactory.createEegFile({
      id: `teaching-edf-${Date.now()}`,
      projectId: project.id,
      filename: project.file,
      format: "EDF",
      sizeBytes: 5914880,
      samplingRateHz: null,
      channelCount: TEACHING_DATASET.channelCount,
      durationSec: TEACHING_DATASET.durationSec,
      eventSummary: { total: TEACHING_DATASET.eventsCount },
      status: "preview_ready",
      source: "system_teaching",
      locked: true,
    }),
    name: project.file,
    type: "EDF",
    status: "已加载，可预览",
    source: "学习模式预置数据",
    locked: true,
    fileUrl: TEACHING_DATASET.edfUrl,
    eventsUrl: TEACHING_DATASET.eventsUrl,
    sizeBytes: 5914880,
  }];
  linkProjectIds(project, "eegFileIds", project.files.filter((file) => /EDF|BDF|SET|FIF/.test(file.type || file.format || "")).map((file) => file.id));
  linkProjectIds(project, "artifactIds", project.files.filter((file) => file.objectType === "Artifact").map((file) => file.id));
  return project;
}

function buildDeliveryTrace(project, taskName) {
  const mainFile = primaryProjectFile(project);
  const isLearning = isLearningProject(project);
  const parameterMap = {
    "ERP 事件相关电位": "Epoch -0.2~0.8 s / baseline -0.2~0 s / event-locked average",
    "静息态功率谱": `${previewFilterLabel()} / Welch-like single-channel PSD / 0-60 Hz`,
    "时频分析": `${previewFilterLabel()} / alpha 8-13 Hz / beta 13-30 Hz / sliding window energy`,
  };
  return {
    input: mainFile?.name || project?.file || "等待上传 EEG 文件",
    events: state.activeTemplate === "静息态功率谱" ? "连续数据，无需事件表" : isLearning ? TEACHING_DATASET.eventsUrl.split("/").pop() : "events_used_for_erp.csv",
    template: state.activeTemplate,
    parameters: parameterMap[state.activeTemplate] || "当前分析参数",
    software: "MNE pipeline / QLanalyser local demo",
    task: taskName,
    archive: `manifest-${String(project?.id || "project").slice(-6)}.json`,
    verified: ["输入数据", "事件表", "分析参数", "结果图", "统计表", "Methods", "manifest"],
  };
}

function learningResultAssets() {
  return {
    figures: [
      { src: "./assets/system_teaching_oddball/system_teaching_p300_summary.svg", caption: "Visual Oddball P300 ERP 概览" },
      { src: "./assets/system_teaching_oddball/system_teaching_p300_heatmap.svg", caption: "Visual Oddball P300 通道热图" },
    ],
    downloads: [
      { href: "./assets/system_teaching_oddball/system_teaching_delivery_manifest.json", icon: "file-json", label: "学习交付 manifest", detail: "学习模式输入、参数和输出绑定记录" },
      { href: "./assets/system_teaching_oddball/system_teaching_erp_metrics.csv", icon: "table", label: "P300 指标表", detail: "target / standard / 差异指标" },
      { href: "./assets/system_teaching_oddball/system_teaching_methods.txt", icon: "file-text", label: "Methods 文本", detail: "Visual Oddball P300 教学分析说明" },
      { href: TEACHING_DATASET.eventsUrl, icon: "list-tree", label: "事件表", detail: "target / standard onset 与标签" },
      { href: TEACHING_DATASET.manifestUrl, icon: "file-json", label: "教学数据 manifest", detail: "通道、时长和事件摘要" },
    ],
  };
}

function localBdfResultAssets() {
  return {
    figures: [
      { src: "./assets/nohe_301_c64rs_0610/nohe_erp_summary.png", caption: "ERP 与 GFP 概览" },
      { src: "./assets/nohe_301_c64rs_0610/nohe_erp_channel_heatmap.png", caption: "通道 ERP 热图" },
    ],
    downloads: [
      { href: "./assets/nohe_301_c64rs_0610/nohe_301_c64rs_erp_package.zip", icon: "archive", label: "结果包", detail: "图、表、Methods、manifest" },
      { href: "./assets/nohe_301_c64rs_0610/erp_condition_metrics.csv", icon: "table", label: "ERP 指标表", detail: "erp_condition_metrics.csv" },
      { href: "./assets/nohe_301_c64rs_0610/nohe_methods.txt", icon: "file-text", label: "Methods 文本", detail: "BDF annotation ERP 分析说明" },
      { href: "./assets/nohe_301_c64rs_0610/events_used_for_erp.csv", icon: "list-tree", label: "事件表", detail: "事件 onset 与标签" },
      { href: "./assets/nohe_301_c64rs_0610/nohe_analysis_manifest.json", icon: "file-json", label: "复现记录", detail: "参数、版本和输入文件" },
    ],
  };
}

function localBdfPublicationAssets() {
  return {
    figures: [
      { src: "./assets/nohe_301_c64rs_0610/nohe_erp_summary.png", label: "GFP 条件图", caption: "Annotation-locked global field power，含 epoch-level 95% bootstrap CI。" },
      { src: "./assets/nohe_301_c64rs_0610/nohe_erp_difference.png", label: "GFP 差异图", caption: "FocusChange 与 SelectedPatchesChange 的 GFP 差异，含 bootstrap CI。" },
      { src: "./assets/nohe_301_c64rs_0610/nohe_erp_heatmap_focuschange.png", label: "FocusChange 热图", caption: "FocusChange 条件的 channel-index ERP 热图，统一色标。" },
      { src: "./assets/nohe_301_c64rs_0610/nohe_erp_heatmap_selectedpatcheschange.png", label: "SelectedPatchesChange 热图", caption: "SelectedPatchesChange 条件的 channel-index ERP 热图，统一色标。" },
      { src: "./assets/nohe_301_c64rs_0610/nohe_event_timeline.png", label: "事件时间线", caption: "进入 ERP 计算的 BDF annotation 事件分布。" },
    ],
    downloads: [
      { href: "./assets/nohe_301_c64rs_0610/nohe_301_c64rs_erp_package.zip", icon: "archive", label: "结果包", detail: "PNG、SVG、指标表、Methods、manifest" },
      { href: "./assets/nohe_301_c64rs_0610/nohe_erp_summary.svg", icon: "image", label: "GFP 条件图 SVG", detail: "可编辑矢量图" },
      { href: "./assets/nohe_301_c64rs_0610/nohe_erp_difference.svg", icon: "image", label: "GFP 差异图 SVG", detail: "可编辑矢量图" },
      { href: "./assets/nohe_301_c64rs_0610/nohe_erp_heatmap_focuschange.svg", icon: "image", label: "FocusChange 热图 SVG", detail: "可编辑矢量图" },
      { href: "./assets/nohe_301_c64rs_0610/nohe_erp_heatmap_selectedpatcheschange.svg", icon: "image", label: "SelectedPatchesChange 热图 SVG", detail: "可编辑矢量图" },
      { href: "./assets/nohe_301_c64rs_0610/nohe_event_timeline.svg", icon: "image", label: "事件时间线 SVG", detail: "可编辑矢量图" },
      { href: "./assets/nohe_301_c64rs_0610/erp_condition_metrics.csv", icon: "table", label: "ERP 指标表", detail: "erp_condition_metrics.csv" },
      { href: "./assets/nohe_301_c64rs_0610/nohe_methods.txt", icon: "file-text", label: "Methods 文本", detail: "BDF annotation ERP 分析说明" },
      { href: "./assets/nohe_301_c64rs_0610/events_used_for_erp.csv", icon: "list-tree", label: "事件表", detail: "事件 onset 与标签" },
      { href: "./assets/nohe_301_c64rs_0610/nohe_analysis_manifest.json", icon: "file-json", label: "复现记录", detail: "参数、版本和输入文件" },
    ],
  };
}

function chartDataUrl(title, series, options = {}) {
  const canvas = document.createElement("canvas");
  canvas.width = 960;
  canvas.height = 540;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "#17202a";
  ctx.font = "700 24px Arial";
  ctx.fillText(title, 44, 48);
  ctx.strokeStyle = "#d9e0e7";
  ctx.lineWidth = 1;
  const left = 72;
  const top = 76;
  const width = 820;
  const height = 360;
  for (let i = 0; i <= 5; i += 1) {
    const y = top + (height * i) / 5;
    ctx.beginPath();
    ctx.moveTo(left, y);
    ctx.lineTo(left + width, y);
    ctx.stroke();
  }
  const values = series.flatMap((item) => item.points.map((point) => point.y)).filter(Number.isFinite);
  const xs = series.flatMap((item) => item.points.map((point) => point.x)).filter(Number.isFinite);
  const minX = options.minX ?? Math.min(...xs, 0);
  const maxX = options.maxX ?? Math.max(...xs, 1);
  const minY = options.minY ?? Math.min(...values, 0);
  const maxY = options.maxY ?? Math.max(...values, 1);
  const scaleX = (x) => left + ((x - minX) / Math.max(1e-9, maxX - minX)) * width;
  const scaleY = (y) => top + height - ((y - minY) / Math.max(1e-9, maxY - minY)) * height;
  const palette = ["#157a77", "#d95f43", "#2f80ed", "#526577"];
  series.forEach((item, index) => {
    ctx.strokeStyle = item.color || palette[index % palette.length];
    ctx.lineWidth = 2.2;
    ctx.beginPath();
    item.points.forEach((point, pointIndex) => {
      const x = scaleX(point.x);
      const y = scaleY(point.y);
      if (pointIndex) ctx.lineTo(x, y);
      else ctx.moveTo(x, y);
    });
    ctx.stroke();
    ctx.fillStyle = ctx.strokeStyle;
    ctx.fillRect(left + index * 190, 462, 18, 4);
    ctx.fillStyle = "#526577";
    ctx.font = "13px Arial";
    ctx.fillText(item.label, left + index * 190 + 26, 468);
  });
  ctx.fillStyle = "#6b7785";
  ctx.font = "12px Arial";
  ctx.fillText(options.xLabel || "Time / Frequency", left, 506);
  ctx.save();
  ctx.translate(18, top + height - 12);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText(options.yLabel || "Amplitude", 0, 0);
  ctx.restore();
  return canvas.toDataURL("image/png");
}

function firstSignalPoints(limit = 1600) {
  const data = eegState.data;
  if (!data?.signals?.length) return [];
  const signal = data.signals[0];
  const step = Math.max(1, Math.floor(signal.values.length / limit));
  const points = [];
  for (let i = 0; i < signal.values.length; i += step) {
    points.push({ x: i / signal.sampleRate, y: signal.values[i] || 0 });
  }
  return points;
}

function computePsdPoints(signal, bins = 96) {
  if (!signal?.values?.length) return [];
  const sampleRate = signal.sampleRate || eegState.data?.sampleRate || 1;
  const n = Math.min(4096, signal.values.length);
  const start = Math.max(0, Math.floor((signal.values.length - n) / 2));
  const values = signal.values.slice(start, start + n);
  const points = [];
  const maxFreq = Math.min(60, sampleRate / 2);
  for (let b = 1; b <= bins; b += 1) {
    const freq = (maxFreq * b) / bins;
    let re = 0;
    let im = 0;
    for (let i = 0; i < n; i += Math.max(1, Math.floor(n / 1024))) {
      const angle = (2 * Math.PI * freq * i) / sampleRate;
      re += values[i] * Math.cos(angle);
      im -= values[i] * Math.sin(angle);
    }
    points.push({ x: freq, y: Math.log10(1 + (re * re + im * im) / n) });
  }
  return points;
}

function tfrEnvelopePoints(signal, bandHz = [8, 13], windows = 120) {
  if (!signal?.values?.length) return [];
  const sampleRate = signal.sampleRate || eegState.data?.sampleRate || 1;
  const windowSize = Math.max(8, Math.floor(sampleRate * 0.5));
  const step = Math.max(1, Math.floor((signal.values.length - windowSize) / windows));
  const points = [];
  for (let start = 0; start + windowSize < signal.values.length; start += step) {
    let energy = 0;
    for (let i = start; i < start + windowSize; i += Math.max(1, Math.floor(sampleRate / 80))) {
      const t = i / sampleRate;
      const carrier = Math.sin(2 * Math.PI * ((bandHz[0] + bandHz[1]) / 2) * t);
      energy += Math.abs((signal.values[i] || 0) * carrier);
    }
    points.push({ x: start / sampleRate, y: energy / windowSize });
    if (points.length >= windows) break;
  }
  return points;
}

function buildLocalAnalysisAssets(project, taskName) {
  if (isLearningProject(project)) return learningResultAssets();
  if (state.activeTemplate === "ERP 事件相关电位" && project?.localSample) return localBdfPublicationAssets();
  const signal = eegState.data?.signals?.[0];
  const baseDownloads = [
    { href: "#", icon: "file-json", label: "分析 manifest", detail: `${state.activeTemplate} / ${taskName}` },
  ];
  if (state.activeTemplate === "静息态功率谱") {
    const psd = computePsdPoints(signal);
    return {
      figures: [
        { src: chartDataUrl("PSD 功率谱", [{ label: signal?.label || "Channel 1", points: psd }], { xLabel: "Frequency (Hz)", yLabel: "log power", minX: 0, maxX: 60 }), label: "PSD 功率谱", caption: "基于当前 EEG 片段计算的单通道功率谱。" },
      ],
      downloads: baseDownloads,
    };
  }
  if (state.activeTemplate === "时频分析") {
    const alpha = tfrEnvelopePoints(signal, [8, 13]);
    const beta = tfrEnvelopePoints(signal, [13, 30]);
    return {
      figures: [
        { src: chartDataUrl("TFR 频带能量随时间变化", [{ label: "Alpha 8-13 Hz", points: alpha }, { label: "Beta 13-30 Hz", points: beta }], { xLabel: "Time (s)", yLabel: "Band energy" }), label: "TFR 时频趋势", caption: "基于当前 EEG 片段估算的 alpha/beta 频带能量时间变化。" },
      ],
      downloads: baseDownloads,
    };
  }
  return {
    figures: [
      { src: chartDataUrl("ERP/RRP 波形预览", [{ label: signal?.label || "Channel 1", points: firstSignalPoints(900) }], { xLabel: "Time (s)", yLabel: "uV" }), label: "波形预览", caption: "基于当前 EEG 数据生成的波形结果预览。" },
    ],
    downloads: baseDownloads,
  };
}

function startLearningMode() {
  const project = createLearningProjectFromTeaching();
  state.teachingModeActive = true;
  state.formalPreviewOpen = true;
  renderProjects();
  setView("dashboard");
  updateCosts();
  const mainFile = primaryProjectFile(project);
  if (mainFile) {
    previewProjectFile(mainFile).catch((error) => showToast(error.message || "教学数据预览失败"));
  }
  renderProjectFiles();
  renderPreprocessPipeline();
  recordOperation("客户", "进入学习模式正式流程", project.name, TEACHING_DATASET.name);
  showToast("已进入学习模式：同正式流程，免扣费");
}

function exitLearningMode() {
  state.teachingModeActive = false;
  const firstFormal = state.projects.find((project) => !isLearningProject(project));
  if (firstFormal) state.activeProjectId = firstFormal.id;
  resetEegPreview();
  applyProductModeUi();
  renderProjects();
  setView("dashboard");
  showToast("已退出教学模式");
}

function completeProjectForLocalDemo(project, taskName, cost) {
  if (!project) return;
  const isLocalBdf = Boolean(project.localSample);
  const isLearning = isLearningProject(project);
  const demoAssets = buildLocalAnalysisAssets(project, taskName);
  project.stage = "结果待查看";
  project.queue = "已完成";
  project.analyzedAt = nowDateTime();
  project.result = {
    status: "已完成",
    badge: `${isLearning ? "学习模式 / " : ""}${project.size} / ${state.activeTemplate}`,
    note: isLearning ? "学习模式已用预置数据完成正式流程体验；本次不消耗余额，不生成收费订单。" : isLocalBdf ? `本地 BDF 已完成 ${state.activeTemplate} 计算，交付件来自当前数据。` : "本地验收：后台已确认扣费并写入交付记录。",
    taskName,
    cost,
    createdAt: new Date().toLocaleString("zh-CN", { hour12: false }),
    trace: buildDeliveryTrace(project, taskName),
    figures: demoAssets.figures,
    downloads: demoAssets.downloads,
  };
  const artifactIds = [
    ...(demoAssets.figures || []).map((item, index) => `${taskName}-figure-${index + 1}`),
    ...(demoAssets.downloads || []).map((item, index) => item.id || `${taskName}-artifact-${index + 1}`),
  ];
  linkProjectIds(project, "artifactIds", artifactIds);
  const taskRecord = state.tasks.find((item) => item.id === taskName || item.name === taskName);
  if (taskRecord) {
    taskRecord.status = "completed";
    taskRecord.finalCost = cost;
    taskRecord.artifactIds = artifactIds;
    taskRecord.manifestId = artifactIds.find((id) => /manifest/i.test(id)) || "";
  }
  project.files = project.files.filter((file) => file.type !== "结果包");
  project.files.push({
    id: `result-${Date.now()}`,
    name: `results/${taskName}_delivery_manifest.json`,
    type: "结果包",
    status: "已生成",
    source: taskName,
    locked: true,
  });
}

function projectWorkflowSummary(project = activeProject()) {
  if (!project) {
    return {
      phase: "未选择项目",
      next: "新建项目、加载测试数据或进入学习模式",
      trace: "Project 0 / EEGFile 0 / Task 0 / Artifact 0",
      done: 0,
      total: 6,
    };
  }
  const items = projectLifecycleItems(project);
  const done = items.filter((item) => item.ok).length;
  const current = items.find((item) => item.active) || items.find((item) => !item.ok) || items[items.length - 1];
  const nextMap = {
    project: "补全项目基本信息",
    file: "上传或加载 EEG 文件",
    preview: "先预览原始信号和事件标签",
    task: "确认参数并创建分析任务",
    artifact: "等待或复核 Worker 输出",
    manifest: "预览结果并确认 manifest",
  };
  const finished = done === items.length;
  return {
    phase: `${current?.label || "Project"} · ${current?.detail || project.stage || ""}`,
    next: finished ? "预览结果并归档下载" : (nextMap[current?.id] || "继续完成当前阶段"),
    trace: `Project 1 / EEGFile ${project.eegFileIds?.length || 0} / Task ${project.taskIds?.length || 0} / Artifact ${project.artifactIds?.length || 0}`,
    done,
    total: items.length,
  };
}

function renderSubmitReadiness() {
  const target = qs("#submitReadiness");
  const button = qs("#createTaskBtn");
  if (!target && !button) return;
  const project = activeProject();
  const files = ensureProjectFiles(project).filter((file) => !/事件表|CSV|TSV/.test(file.type));
  const hasEegFile = files.some((file) => /EDF|BDF|SET|FIF/.test(file.type || file.format || ""));
  const hasPreview = Boolean(project && (eegState.data || isLearningProject(project)));
  const learning = isLearningProject(project);
  const subjects = Math.max(1, Number(qs("#subjectsInput")?.value || 1));
  const hours = Math.max(0.1, Number(qs("#hoursInput")?.value || 0.1));
  const cost = learning ? 0 : subjects * hours;
  const balanceOk = learning || state.balance >= cost;
  const checks = [
    { label: "Project", ok: Boolean(project), detail: project?.name || "先从项目列表或学习模式进入" },
    { label: "EEGFile", ok: hasEegFile, detail: hasEegFile ? (primaryProjectFile(project)?.name || "已绑定 EEG") : "等待 EDF/BDF/SET/FIF" },
    { label: "Preview", ok: hasPreview, detail: hasPreview ? "已核对信号/事件" : "提交前先预览原始数据" },
    { label: "Method", ok: Boolean(state.activeTemplate), detail: state.activeTemplate || "选择分析模板" },
    { label: learning ? "Learning" : "Billing", ok: balanceOk, detail: learning ? "学习模式免扣费" : `余额 ${money(state.balance)} / 预计 ${money(cost)}` },
  ];
  const canSubmit = checks.every((item) => item.ok);
  if (target) {
    target.innerHTML = checks.map((item) => `
      <div class="${item.ok ? "ready" : "blocked"}">
        <b>${item.ok ? "OK" : "!"}</b>
        <span>${item.label}</span>
        <small>${escapeHtml(item.detail)}</small>
      </div>
    `).join("");
  }
  if (button) {
    button.disabled = !canSubmit;
    button.title = canSubmit ? "" : "请先完成项目、EEG 文件、预览、方法和余额检查。";
  }
}

function renderProjects() {
  const project = activeProject();
  const running = state.projects.filter((item) => item.queue !== "已完成").length;
  renderProjectLifecycle("projectLifecycleDashboard", project);
  renderProjectLifecycle("projectLifecycleAnalysis", project);
  if (qs("#projectCount")) {
    qs("#projectCount").textContent = String(state.projects.length);
    qs("#projectCount").nextElementSibling.textContent = state.projects.length
      ? `${running} 个未完成，${state.projects.length - running} 个已完成`
      : "暂无项目";
  }
  if (qs("#currentProjectName")) qs("#currentProjectName").textContent = project?.name || "未选择";
  if (qs("#currentProjectStage")) qs("#currentProjectStage").textContent = project?.stage || "等待新建或上传";
  if (qs("#currentProjectQueue")) qs("#currentProjectQueue").textContent = project?.queue || "未提交";
  if (qs("#dashboardBalance")) qs("#dashboardBalance").textContent = money(state.balance);

  const table = qs("#projectTable");
  if (table) {
    const rows = state.projects.length
      ? state.projects.map((item) => {
        const mainFile = primaryProjectFile(item);
        const analyzed = item.result?.status === "已完成" || item.queue === "已完成";
        const workflow = projectWorkflowSummary(item);
        return `
        <div class="table-row project-row ${item.id === state.activeProjectId ? "active-row" : ""}" data-project-row="${item.id}">
          <span>${item.name}<small>${isLearningProject(item) ? "学习模式" : "正式项目"} · ${item.stage}</small></span>
          <span>${item.createdAt || item.updated || "-"}<small>${item.updated ? `更新：${item.updated}` : ""}</small></span>
          <span>${mainFile?.name || item.file}<small>${item.size || "-"}</small></span>
          <span class="project-stage-cell ${analyzed ? "ok" : "run"}">
            <b>${analyzed ? "已分析" : item.queue || "未提交"}</b>
            <small>${escapeHtml(workflow.phase)}</small>
            <small>${escapeHtml(workflow.next)}</small>
            <em>${escapeHtml(workflow.trace)}</em>
          </span>
          <span class="row-actions">
            <button type="button" data-select-project="${item.id}">分析</button>
            ${analyzed ? `<button type="button" data-open-project-result="${item.id}">结果</button>` : ""}
          </span>
        </div>
      `;
      }).join("")
      : tableEmpty("还没有项目。新建项目、上传 EDF，或进入学习模式试跑一次完整流程。");
    table.innerHTML = `<div class="table-row head project-row"><span>项目</span><span>开始时间</span><span>数据文件</span><span>分析状态</span><span>操作</span></div>${rows}`;
    qsa("[data-select-project]").forEach((button) => button.addEventListener("click", () => {
      state.activeProjectId = button.dataset.selectProject;
      state.formalPreviewOpen = false;
      resetEegPreview();
      renderProjects();
      updateCosts();
      updateFormalPreviewVisibility();
      setView("analysis");
      showToast(`已打开项目：${activeProject().name}`);
    }));
    qsa("[data-open-project-result]").forEach((button) => button.addEventListener("click", () => {
      state.activeProjectId = button.dataset.openProjectResult;
      renderProjects();
      setView("publication");
      showToast(`已打开结果：${activeProject().name}`);
    }));
  }

  const card = qs("#currentProjectCard");
  if (card) {
    if (!project) {
      card.innerHTML = `<div class="empty-card"><strong>暂无项目</strong><span>需要分析自己的数据时，请新建项目或上传 EDF；需要试用完整流程时，进入学习模式。</span></div>`;
    } else {
      const mainFile = primaryProjectFile(project);
      const analyzed = project.result?.status === "已完成" || project.queue === "已完成";
      card.innerHTML = `
        <div class="project-card-main"><span>当前项目</span><strong>${project.name}</strong><small>${isLearningProject(project) ? "学习模式" : "正式项目"} · ${project.stage}</small></div>
        <div><span>开始时间</span><strong>${project.createdAt || project.updated || "-"}</strong></div>
        <div><span>数据文件</span><strong>${mainFile?.name || project.file}</strong></div>
        <div><span>分析状态</span><strong>${analyzed ? "已分析" : project.queue}</strong></div>
        <div><span>分析完成</span><strong>${project.analyzedAt || (analyzed ? project.updated : "未分析")}</strong></div>
      `;
    }
  }
  renderProjectFiles();
  renderSubmitReadiness();
}

function renderProjectFiles() {
  const project = activeProject();
  const target = qs("#projectFileTable");
  if (!target) return;
  if (!project) {
    target.innerHTML = `<div class="table-row head"><span>文件</span><span>类型</span><span>状态</span><span>操作</span></div>${tableEmpty("还没有项目。上传数据或进入学习模式后，这里会显示文件。")}`;
    if (qs("#projectFileNotice span")) qs("#projectFileNotice span").textContent = "项目没有数据文件前，不显示原始脑电预览、队列或结果。";
    renderSubmitReadiness();
    return;
  }
  const files = ensureProjectFiles(project);
  const rows = files.length
    ? files.map((file) => {
      const actions = [];
      if (/EDF|BDF|SET|FIF/.test(file.type)) actions.push("预览", "替换");
      if (/事件表|CSV|TSV/.test(file.type)) actions.push("查看");
      if (project.result?.status === "已完成" || file.type === "结果包") actions.push("结果");
      if (!file.locked && !project.locked) actions.push("删除");
      return `
        <div class="table-row" data-file-id="${file.id}">
          <span>${file.name}<small>来源：${file.source || "客户上传"}</small></span>
          <span>${file.type}</span>
          <span class="${statusClass(file.status)}">${file.status}</span>
          <span class="row-actions">${actions.map((action) => `<button type="button" data-file-action="${action}" data-file-id="${file.id}">${action}</button>`).join("")}</span>
        </div>
      `;
    }).join("")
    : tableEmpty("当前项目还没有数据文件。请上传 EDF / BDF / SET 后再提交任务。");
  target.innerHTML = `<div class="table-row head"><span>文件</span><span>类型</span><span>状态</span><span>操作</span></div>${rows}`;
  bindFileActionButtons();
  if (qs("#projectFileNotice span")) {
    qs("#projectFileNotice span").textContent = isLearningProject(project)
      ? `${project.name}：预置教学数据已进入正式流程，本次免扣费。`
      : `${project.name}：${files.length} 个文件，${project.queue}。`;
  }
  if (window.lucide) lucide.createIcons();
  renderSubmitReadiness();
  const autoPreview = primaryProjectFile(project);
  if (state.teachingModeActive && autoPreview && /EDF|BDF/.test(autoPreview.type) && !eegState.data) {
    previewProjectFile(autoPreview).catch(() => {});
  }
}

function findProjectFile(fileId) {
  const project = activeProject();
  const file = ensureProjectFiles(project).find((item) => item.id === fileId);
  return { project, file };
}

function addUploadedFiles(files) {
  let project = activeProject();
  if (!files.length) return;
  if (!project) project = createFormalProject(`正式项目 ${files[0].name.replace(/\.[^.]+$/, "")}`);
  const addedFileIds = [];
  files.forEach((file) => {
    const extension = file.name.split(".").pop()?.toUpperCase() || "文件";
    const type = ["EDF", "BDF", "SET", "FIF"].includes(extension) ? extension : extension === "CSV" ? "事件表" : extension;
    const fileRecord = {
      ...domainFactory.createEegFile({
        id: `file-${Date.now()}-${Math.random().toString(16).slice(2, 7)}`,
        projectId: project.id,
        filename: `raw/${file.name}`,
        format: type,
        sizeBytes: file.size,
        status: type === "EDF" ? "preview_ready" : "uploaded",
        source: "customer_upload",
      }),
      name: `raw/${file.name}`,
      type,
      status: type === "EDF" ? "已上传，可预览" : "已上传，等待解析",
      source: "客户上传",
      locked: false,
      browserFile: file,
    };
    project.files.push(fileRecord);
    addedFileIds.push(fileRecord.id);
  });
  linkProjectIds(project, "eegFileIds", addedFileIds);
  const mainFile = primaryProjectFile(project);
  project.file = mainFile?.name || project.file;
  project.size = `${(files.reduce((sum, file) => sum + file.size, 0) / 1024 / 1024).toFixed(1)} MB`;
  project.stage = "待确认";
  project.queue = "未提交";
  project.updated = today();
  state.formalPreviewOpen = false;
  resetEegPreview();
  renderProjects();
  recordOperation("客户", "上传项目文件", project.name, `${files.length} 个浏览器文件`);
}

async function loadLocalBdfSample() {
  const button = qs("#loadLocalBdfBtn");
  if (button) button.disabled = true;
  try {
    const meta = await apiRequest(LOCAL_BDF_SAMPLE_META);
    state.localSample = meta;
    state.formalPreviewOpen = false;
    resetEegPreview();
    const project = createFormalProject("本地测试：RSC-64RS ERP");
    project.file = meta.fileName;
    project.stage = "待确认";
    project.queue = "未提交";
    project.size = meta.sizeLabel;
    project.localSample = true;
    const localFileId = `local-bdf-${Date.now()}`;
    project.files = [{
      ...domainFactory.createEegFile({
        id: localFileId,
        projectId: project.id,
        filename: `local/${meta.fileName}`,
        format: "BDF",
        sizeBytes: meta.sizeBytes,
        channelCount: meta.channelCount,
        eventSummary: meta.eventSummary,
        status: "preview_ready",
        source: "local_sample",
        locked: true,
      }),
      name: `local/${meta.fileName}`,
      type: "BDF",
      status: "已加载，可预览",
      source: meta.sourceLabel || "本机测试数据",
      locked: true,
      fileUrl: meta.fileUrl,
      eventsUrl: meta.eventsUrl,
      sizeBytes: meta.sizeBytes,
    }];
    linkProjectIds(project, "eegFileIds", project.files.map((file) => file.id));
    renderProjects();
    setView("analysis");
    recordOperation("客户", "加载本地 BDF 测试数据", project.name, meta.fileName);
    showToast("本地 BDF 测试数据已加入当前项目");
  } catch (error) {
    showToast(error.message || "本地 BDF 测试数据不可用");
  } finally {
    if (button) button.disabled = false;
  }
}

function projectLifecycleItems(project = activeProject()) {
  const files = ensureProjectFiles(project);
  const hasEegFile = files.some((file) => /EDF|BDF|SET|FIF/.test(file.type || file.format || ""));
  const hasPreview = Boolean(eegState.data || isLearningProject(project));
  const hasTask = Boolean(project?.taskIds?.length || state.tasks.some((task) => task.projectId === project?.id));
  const completed = project?.result?.status === "已完成" || project?.queue === "已完成";
  const hasManifest = Boolean(project?.result?.trace?.archive || project?.result?.downloads?.some((item) => /manifest/i.test(item.href || item.label || "")));
  return [
    { id: "project", label: "Project", detail: project ? project.name : "先创建或选择项目", ok: Boolean(project), active: Boolean(project) && !hasEegFile },
    { id: "file", label: "EEGFile", detail: hasEegFile ? (primaryProjectFile(project)?.name || "已绑定数据") : "上传 EDF/BDF/SET/FIF", ok: hasEegFile, active: Boolean(project) && !hasEegFile },
    { id: "preview", label: "Preview", detail: hasPreview ? "已可核对信号/事件" : "打开原始波形预览", ok: hasPreview, active: hasEegFile && !hasPreview },
    { id: "task", label: "AnalysisTask", detail: hasTask ? (project?.queue || "任务已创建") : "配置方法并提交", ok: hasTask, active: hasPreview && !hasTask },
    { id: "artifact", label: "Artifact", detail: completed ? "图表/表格已生成" : "等待 worker 生成", ok: completed, active: hasTask && !completed },
    { id: "manifest", label: "Report", detail: hasManifest ? "manifest 已绑定" : "交付包待复核", ok: hasManifest, active: completed && !hasManifest },
  ];
}

function renderProjectLifecycle(targetId, project = activeProject()) {
  const target = qs(`#${targetId}`);
  if (!target) return;
  const items = projectLifecycleItems(project);
  target.innerHTML = items.map((item, index) => `
    <div class="${item.ok ? "done" : ""} ${item.active ? "active" : ""}">
      <b>${index + 1}</b>
      <span>${item.label}</span>
      <small>${escapeHtml(item.detail)}</small>
    </div>
  `).join("");
}

async function previewProjectFile(file) {
  state.formalPreviewOpen = true;
  updateFormalPreviewVisibility();
  if (file.fileUrl && /EDF|BDF/.test(file.type)) {
    await loadEegFromUrls(file.fileUrl, file.eventsUrl || "", "formal", file.name.split("/").pop());
    file.status = "已预览";
    renderProjectFiles();
    return;
  }
  if (file.browserFile && /EDF|BDF/.test(file.type)) {
    await loadEegFromBuffer(await file.browserFile.arrayBuffer(), file.browserFile.name, "", "formal");
    file.status = "已预览";
    renderProjectFiles();
    return;
  }
  resetEegPreview(/EDF|BDF/.test(file.type)
    ? "该记录来自本地选择，但当前浏览器会话未保留文件句柄。请重新上传后预览。"
    : "该文件不是可直接在网页中预览的 EDF。BDF / SET 将在后台解析后生成预览索引。");
}

function handleFileAction(action, fileId) {
  const { project, file } = findProjectFile(fileId);
  if (!project || !file) return;
  if (action === "预览") {
    previewProjectFile(file).catch((error) => showToast(error.message || "文件预览失败"));
    recordOperation("客户", "打开文件预览", file.name, project.name);
    showToast("已打开预览区域");
    return;
  }
  if (action === "替换") {
    file.status = "等待重新上传";
    project.stage = "待上传替换文件";
    project.queue = "未提交";
    project.updated = today();
    renderProjects();
    recordOperation("客户", "标记文件替换", file.name, project.name);
    showToast("已标记为等待替换，请上传新文件");
    return;
  }
  if (action === "删除") {
    if (file.locked || project.locked) {
      showToast("系统锁定文件不能删除");
      return;
    }
    project.files = project.files.filter((item) => item.id !== file.id);
    const mainFile = primaryProjectFile(project);
    project.file = mainFile?.name || "等待上传 EEG 文件";
    project.stage = project.files.length ? "待确认" : "待上传";
    project.queue = "未提交";
    project.size = project.files.length ? project.size : "-";
    project.updated = today();
    renderProjects();
    recordOperation("客户", "删除项目文件", file.name, project.name);
    showToast(`已从当前项目移除：${file.name}`);
    return;
  }
  if (action === "查看") {
    showToast(`${file.name}：${file.status}`);
    recordOperation("客户", "查看派生文件", file.name, file.source || project.name);
    if (file.name.includes("events_used_for_erp")) setView("publication");
    return;
  }
  if (action === "结果") {
    recordOperation("客户", "打开结果交付", project.name, project.result?.status || "项目状态");
    setView("publication");
  }
}

function bindFileActionButtons() {
  qsa("[data-file-action]").forEach((button) => {
    button.addEventListener("click", () => handleFileAction(button.dataset.fileAction, button.dataset.fileId));
  });
}

function activeAdminTask() {
  return state.adminTasks.find((task) => task.id === state.adminActiveTaskId) || state.adminTasks[0];
}

function chainStatus(task, nodeId) {
  if (task.failedNodeIds.includes(nodeId) && task.currentNodeId === nodeId) return "failed current";
  if (task.failedNodeIds.includes(nodeId)) return "failed";
  if (task.currentNodeId === nodeId) return "current";
  if (task.doneNodeIds.includes(nodeId)) return "done";
  return "pending";
}

function renderAdminTaskMonitor() {
  const task = activeAdminTask();
  if (!task) return;
  const picker = qs("#adminTaskPicker");
  if (picker) {
    picker.innerHTML = state.adminTasks.map((item) => `
      <button type="button" class="${item.id === task.id ? "active" : ""}" data-admin-task="${item.id}">
        <strong>${item.customer}</strong>
        <span>${item.project}</span>
        <b>${chainNodeMap.get(item.currentNodeId)?.label || "未知节点"}</b>
      </button>
    `).join("");
    qsa("[data-admin-task]").forEach((button) => button.addEventListener("click", () => {
      state.adminActiveTaskId = button.dataset.adminTask;
      renderAdminTaskMonitor();
      showToast(`已切换任务：${activeAdminTask().project}`);
    }));
  }

  if (qs("#adminChainTaskTitle")) qs("#adminChainTaskTitle").textContent = `${task.customer} · ${task.project}`;
  if (qs("#adminChainTaskMeta")) qs("#adminChainTaskMeta").textContent = `${task.file} / ${task.size}`;
  if (qs("#adminChainCurrentNode")) qs("#adminChainCurrentNode").textContent = chainNodeMap.get(task.currentNodeId)?.label || task.currentNodeId;
  if (qs("#adminChainFailedNode")) {
    qs("#adminChainFailedNode").textContent = task.failedNodeIds.length
      ? task.failedNodeIds.map((id) => chainNodeMap.get(id)?.label || id).join("、")
      : "无失败节点";
  }

  const chain = qs("#adminBusinessChain");
  if (chain) {
    chain.innerHTML = BUSINESS_CHAIN.map((group) => `
      <div class="chain-stage">
        <h3>${group.title}</h3>
        <div class="chain-stage-nodes">
          ${group.nodes.map((node) => {
            const status = chainStatus(task, node.id);
            return `<button type="button" class="chain-node ${status}" data-chain-node="${node.id}">
              <strong>${node.label}</strong>
              <span>${node.detail}</span>
            </button>`;
          }).join("")}
        </div>
      </div>
    `).join("");
    qsa("[data-chain-node]").forEach((button) => button.addEventListener("click", () => {
      const node = chainNodeMap.get(button.dataset.chainNode);
      const related = task.history.find((item) => item.nodeId === button.dataset.chainNode);
      showToast(`${node?.label || button.dataset.chainNode}：${related?.note || "等待进入该节点"}`);
      recordOperation("管理员", "查看链路节点", node?.label || button.dataset.chainNode, task.project);
    }));
  }

  const history = qs("#adminChainHistory");
  if (history) {
    history.innerHTML = task.history.map((item) => {
      const node = chainNodeMap.get(item.nodeId);
      const status = item.status === "失败" ? "failed" : item.status === "当前" ? "current" : "done";
      return `<div class="history-row ${status}">
        <span>${item.time}</span>
        <strong>${node?.label || item.nodeId}</strong>
        <b>${item.status}</b>
        <em>${item.note}</em>
      </div>`;
    }).join("");
  }
}

function handleProjectAction(action) {
  const current = activeProject();
  if (action === "new") {
    const project = createFormalProject();
    state.formalPreviewOpen = false;
    resetEegPreview();
    recordOperation("客户", "新建正式项目", project.id, "项目总览");
    setView("analysis");
    showToast("已创建新项目");
  } else if (action === "load-v0-sample") {
    loadLocalBdfSample();
  } else if (action === "rename" && current) {
    const nextName = window.prompt("项目名称", current.name);
    if (!nextName || !nextName.trim()) return;
    current.name = nextName.trim();
    current.updated = today();
    showToast("项目名称已更新");
  } else if (action === "duplicate" && current) {
    const id = `ql-copy-${Date.now()}`;
    const createdAt = nowDateTime();
    state.projects.unshift({
      ...current,
      id,
      name: `${current.name} 副本`,
      queue: "未提交",
      stage: "待确认",
      createdAt,
      updated: today(),
      analyzedAt: "",
      locked: false,
      files: ensureProjectFiles(current).map((file) => ({ ...file, id: `${file.id}-copy-${Date.now()}`, locked: Boolean(file.locked) })),
      result: { ...current.result, status: "未生成" },
    });
    state.activeProjectId = id;
    recordOperation("客户", "复制项目", current.name, id);
    setView("analysis");
    showToast("已复制为新项目");
  } else if (action === "delete" && current) {
    if (current.locked) {
      showToast("系统项目不能删除");
      return;
    }
    if (!window.confirm(`删除项目「${current.name}」？`)) return;
    state.projects = state.projects.filter((project) => project.id !== current.id);
    state.activeProjectId = state.projects[0]?.id || null;
    state.formalPreviewOpen = false;
    resetEegPreview();
    recordOperation("客户", "删除项目", current.name, "项目总览");
    showToast("项目已删除");
  } else if (!current && ["rename", "duplicate", "delete"].includes(action)) {
    showToast("还没有项目");
  }
  renderProjects();
  updateFormalPreviewVisibility();
}

function loginCustomer(account, password, remember) {
  const customer = getStoredCustomer();
  const normalized = String(account || "").trim();
  const matchedDemo = normalized === demoCustomer.email && password === demoCustomer.password;
  const matchedRegistered = [customer.email, customer.phone].filter(Boolean).includes(normalized) && password === customer.password;
  if (!matchedDemo && !matchedRegistered) {
    setLoginMessage("账号或密码不正确，请检查后重试。", "error");
    return;
  }
  if (matchedDemo) saveCustomer(demoCustomer);
  rememberSession("customer", remember);
  loginAs("customer", matchedRegistered ? customer : getStoredCustomer());
  setLoginMessage("");
}

async function sendRegisterSmsCode() {
  const phone = qs("#registerPhone")?.value.trim() || "";
  if (!validatePhone(phone)) {
    setLoginMessage("请填写有效手机号。", "error");
    return;
  }
  const button = qs("#sendSmsCodeBtn");
  if (button) button.disabled = true;
  try {
    const data = await apiRequest("/api/auth/sms-code", { phone, purpose: "register" });
    state.sms = {
      pendingPhone: phone,
      lastBizId: data.bizId,
      sandboxCode: data.sandboxCode || "",
      expiresAt: Date.now() + Number(data.expiresInSec || 300) * 1000,
    };
    if (data.sandboxCode && qs("#registerSmsCode")) qs("#registerSmsCode").value = data.sandboxCode;
    setLoginMessage(data.sandboxCode ? `本地沙箱验证码：${data.sandboxCode}` : "验证码已发送。", "success");
    recordOperation("系统", "发送注册短信验证码", phone, data.provider || "短信服务");
  } catch (error) {
    setLoginMessage(error.message || "验证码发送失败。", "error");
  } finally {
    if (button) {
      window.setTimeout(() => {
        button.disabled = false;
      }, 1000);
    }
  }
}

async function registerCustomer({ name, phone, smsCode, email, org, password, passwordConfirm }) {
  if (!name.trim()) {
    setLoginMessage("请填写姓名。", "error");
    return;
  }
  if (!validatePhone(phone)) {
    setLoginMessage("请填写有效手机号。", "error");
    return;
  }
  if (!smsCode.trim()) {
    setLoginMessage("请填写短信验证码。", "error");
    return;
  }
  if (email && !validateEmail(email)) {
    setLoginMessage("请填写有效邮箱。", "error");
    return;
  }
  if (password.length < 8) {
    setLoginMessage("密码至少 8 位。", "error");
    return;
  }
  if (password !== passwordConfirm) {
    setLoginMessage("两次输入的密码不一致。", "error");
    return;
  }
  try {
    const data = await apiRequest("/api/auth/register", {
      name,
      phone,
      code: smsCode,
      email,
      org,
      password,
      passwordConfirm,
    });
    const profile = {
      ...data.customer,
      password,
      email: data.customer.email || email.trim(),
      org: data.customer.org || org.trim() || "未填写单位",
    };
    saveCustomer(profile);
    rememberSession("customer", true);
    state.balance = STARTER_BALANCE;
    state.projects = [];
    state.activeProjectId = null;
    state.tasks = [];
    state.payment.activeOrder = null;
    state.formalPreviewOpen = false;
    resetEegPreview();
    recordOperation("客户", "注册客户账号", profile.name, `${profile.phone} / 手机已验证`);
    renderAllAdmin();
    loginAs("customer", profile);
    showToast("注册成功，已进入项目总览");
  } catch (error) {
    setLoginMessage(error.message || "注册失败。", "error");
  }
}

function restoreSession() {
  const raw = sessionStorage.getItem(AUTH_KEY) || localStorage.getItem(AUTH_KEY);
  if (!raw) {
    logout(false);
    return;
  }
  try {
    const session = JSON.parse(raw);
    if (session.role === "customer") {
      loginAs("customer", getStoredCustomer());
      return;
    }
    if (session.role === "admin") {
      loginAs("admin");
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
  qsa("[data-role]").forEach((item) => {
    item.hidden = item.dataset.role !== role;
  });
  if (role === "admin") {
    syncSidebarAccount();
    qs("#topEyebrow").textContent = "平台管理";
    qs("#tutorialBtn").hidden = true;
    renderAllAdmin();
    setView("adminDashboard");
    if (window.lucide) lucide.createIcons();
    return;
  }
  const customer = profile || getStoredCustomer();
  syncSidebarAccount(customer);
  qs("#topEyebrow").textContent = "当前项目";
  qs("#tutorialBtn").hidden = false;
  renderProjects();
  renderAccountSettings();
  applyProductModeUi();
  setView("dashboard");
  if (window.lucide) lucide.createIcons();
}

function logout(clear = true) {
  state.role = null;
  if (clear) clearSession();
  qs("#appShell").hidden = true;
  qs("#loginScreen").hidden = false;
  qsa(".view").forEach((el) => el.classList.remove("active"));
  qsa(".nav-item").forEach((el) => el.classList.remove("active"));
  switchLoginTab("customerLogin");
  if (window.lucide) lucide.createIcons();
}

function setView(view) {
  const targetNav = qs(`[data-view="${view}"]`);
  if (targetNav?.dataset.role && state.role && targetNav.dataset.role !== state.role) return;
  qsa(".view").forEach((el) => el.classList.toggle("active", el.id === view));
  qsa(".nav-item").forEach((el) => el.classList.toggle("active", el.dataset.view === view));
  qsa(".flow-rail [data-view-jump]").forEach((el) => el.classList.toggle("active", el.dataset.viewJump === view));
  const title = qs("#viewTitle");
  if (title) title.textContent = titles[view] || titles.dashboard;
  if (view === "analysis") {
    setAnalysisPage(state.analysisPage || "home", { scroll: false });
    renderCustomerChecks();
    renderProjectLifecycle("projectLifecycleAnalysis", activeProject());
    updateFormalPreviewVisibility();
  }
  if (view === "dashboard") renderProjects();
  if (view === "publication") renderPublication();
  if (view === "teaching") loadTeachingManifest();
  if (view === "billing") renderAccountSettings();
  if (view.startsWith("admin")) renderAllAdmin();
  applyProductModeUi();
  renderModuleRail(view);
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function renderTasks() {
  const target = qs("#taskList");
  if (!target) return;
  target.innerHTML = state.tasks.length ? state.tasks.map((task) => `
    <div class="task">
      <div><strong>${task.name || task.id}</strong><span>${task.detail || `${task.workflowTemplate || "Analysis"} / ${task.status || ""}`}</span></div>
      <div><span>${task.progress === 100 ? "已完成" : `${task.progress}%`}</span><div class="task-meter"><i style="width:${task.progress}%"></i></div></div>
    </div>
  `).join("") : `<div class="empty-card"><strong>暂无任务</strong><span>正式项目或学习体验提交后会显示任务进度。</span></div>`;
}

function renderPublication() {
  const project = activeProject();
  const casePanel = qs(".customer-case-panel");
  const deliveryPanel = qs(".customer-delivery-panel");
  const statusPanel = qs("#publicationStatus")?.closest(".panel");
  if (!project || project.result?.status !== "已完成") {
    if (casePanel) {
      casePanel.innerHTML = `
        <div class="empty-state result-empty">
          <i data-lucide="file-clock"></i>
          <strong>暂无结果</strong>
          <span>当前项目完成分析后，这里会显示图表、统计表和交付包。想先试跑完整流程，可进入学习模式。</span>
        </div>
      `;
    }
    if (deliveryPanel) deliveryPanel.hidden = true;
    if (statusPanel) statusPanel.hidden = true;
    if (window.lucide) lucide.createIcons();
    return;
  }
  const mainFile = primaryProjectFile(project);
  const learning = isLearningProject(project);
  if (casePanel) {
    const trace = project.result.trace || buildDeliveryTrace(project, project.result.taskName || "-");
    const figures = project.result.figures?.length ? `
      <div class="figure-grid formal-result-figures">
        ${project.result.figures.map((figure) => `<figure><img src="${figure.src}" alt="${figure.caption}" /><figcaption>${figure.caption}</figcaption></figure>`).join("")}
      </div>
    ` : "";
    const tracePanel = `
      <details class="delivery-trace-panel">
        <summary class="delivery-trace-head">
          <strong>复核链路</strong>
          <span>输入数据、事件表、参数和输出文件已绑定到 manifest。</span>
        </summary>
        <div class="delivery-trace-grid">
          <div><span>输入</span><strong>${escapeHtml(trace.input)}</strong></div>
          <div><span>事件表</span><strong>${escapeHtml(trace.events)}</strong></div>
          <div><span>参数</span><strong>${escapeHtml(trace.parameters)}</strong></div>
          <div><span>软件</span><strong>${escapeHtml(trace.software)}</strong></div>
          <div><span>任务</span><strong>${escapeHtml(trace.task)}</strong></div>
          <div><span>归档</span><strong>${escapeHtml(trace.archive)}</strong></div>
        </div>
        <div class="trace-checks">
          ${(trace.verified || []).map((item) => `<span><i data-lucide="check"></i>${escapeHtml(item)}</span>`).join("")}
        </div>
      </details>
    `;
    casePanel.innerHTML = `
      <div class="panel-head">
        <div><h2>${project.name}</h2><p>${learning ? "学习模式使用正式结果页和交付流程。" : "当前正式项目结果。"}</p></div>
        <span class="badge">${learning ? "学习模式免扣费" : project.result.badge || "已完成"}</span>
      </div>
      <div class="case-summary formal-result-summary">
        <div><span>数据文件</span><strong>${mainFile?.name || project.file}</strong></div>
        <div><span>分析模板</span><strong>${state.activeTemplate}</strong></div>
        <div><span>任务编号</span><strong>${project.result.taskName || "-"}</strong></div>
        <div><span>${learning ? "余额消耗" : "扣费"}</span><strong>${learning ? "￥0.00" : money(project.result.cost || 0)}</strong></div>
      </div>
      <div class="notice neutral compact-notice"><i data-lucide="badge-check"></i><span>${project.result.note || "结果已写入当前项目。"}</span></div>
      ${figures}
      ${tracePanel}
    `;
  }
  if (deliveryPanel) {
    const figureItems = (project.result.figures || []).map((figure, index) => ({
      id: `formal-${project.id}-figure-${index}`,
      href: figure.src,
      icon: "image",
      label: figure.label || `结果图 ${index + 1}`,
      detail: figure.caption || "结果图下载前预览",
      source: project.name,
      type: "image",
    }));
    const fileItems = project.result.downloads?.map((item, index) => ({
      ...item,
      id: item.id || `formal-${project.id}-${index}`,
      source: project.name,
    })) || [];
    const deliveryItems = [...figureItems, ...fileItems];
    registerDeliveryItems(deliveryItems, `formal-${project.id}`);
    deliveryPanel.hidden = false;
    deliveryPanel.innerHTML = `
      <div class="panel-head">
        <div><h2>交付件</h2><p>${isLearningProject(project) ? "学习模式复用正式交付流程，下载前同样先预览。" : "由当前正式项目生成，下载前请先预览。"}</p></div>
        <span class="badge">已完成</span>
      </div>
      <div class="delivery-status-strip">
        <span><i data-lucide="package-check"></i> 已生成</span>
        <span><i data-lucide="badge-check"></i> 已绑定 manifest</span>
        <span><i data-lucide="eye"></i> 下载前预览</span>
        <span><i data-lucide="user-check"></i> 待客户确认</span>
      </div>
      ${groupedDeliveryHtml(deliveryItems)}
    `;
  }
  if (deliveryPanel) deliveryPanel.hidden = false;
  if (statusPanel) statusPanel.hidden = false;
  if (qs("#publicationStatus")) qs("#publicationStatus").textContent = `当前输出：${project.result.createdAt || today()}，${project.result.taskName || "正式任务"}。`;
  renderArchitectureChecklist();
  bindDeliveryPreviewButtons(deliveryPanel);
  if (window.lucide) lucide.createIcons();
}

function renderArchitectureChecklist() {
  const status = qs("#publicationStatus");
  if (!status || !architecture.architectureChecklist) return;
  const checks = architecture.architectureChecklist(state);
  const failed = checks.filter((item) => !item.ok);
  status.dataset.architectureStatus = failed.length ? "needs-review" : "aligned";
  status.title = failed.length
    ? `架构待核对：${failed.map((item) => item.label).join(" / ")}`
    : "已对齐项目、数据、任务、账务、交付件和 manifest 的 V1 架构对象。";
}

function activeTemplate() {
  return templates.find((item) => item.name === state.activeTemplate) || templates[0];
}

function availableTemplates() {
  return isV0Mode ? templates.filter((item) => V0_TEMPLATE_NAMES.has(item.name)) : templates;
}

function workflowRouteFor(templateName = state.activeTemplate) {
  return WORKFLOW_ROUTES[templateName] || WORKFLOW_ROUTES["ERP 事件相关电位"];
}

function analysisPageForTarget(targetSelector = "") {
  if (ANALYSIS_TARGET_PAGES[targetSelector]) return ANALYSIS_TARGET_PAGES[targetSelector];
  return qs(targetSelector)?.dataset.analysisPage || state.analysisPage || "home";
}

function renderPreprocessSummary() {
  renderPreprocessPipeline();
}

function cloneEegData(data) {
  if (!data) return null;
  return {
    ...data,
    labels: [...data.labels],
    signals: data.signals.map((signal) => ({
      ...signal,
      values: new Float32Array(signal.values),
    })),
  };
}

function signalStats(values, step = 1) {
  const sampled = [];
  let sum = 0;
  let sumSq = 0;
  let count = 0;
  for (let i = 0; i < values.length; i += step) {
    const value = values[i];
    if (!Number.isFinite(value)) continue;
    sampled.push(value);
    sum += value;
    sumSq += value * value;
    count += 1;
  }
  if (!count) return { mean: 0, rms: 0, p2p: 0 };
  sampled.sort((a, b) => a - b);
  const mean = sum / count;
  const rms = Math.sqrt(Math.max(0, sumSq / count));
  return { mean, rms, p2p: sampled[sampled.length - 1] - sampled[0] };
}

function detectBadChannels(data) {
  if (!data?.signals?.length) return [];
  const stats = data.signals.map((signal) => signalStats(signal.values, Math.max(1, Math.floor(signal.values.length / 5000))));
  const rmsValues = stats.map((item) => item.rms).sort((a, b) => a - b);
  const median = percentileSorted(rmsValues, 0.5) || 1;
  return stats.map((item, index) => ({
    label: data.signals[index].label,
    rms: item.rms,
    p2p: item.p2p,
    reason: item.rms > median * 4 ? "RMS 过高" : item.rms < median * 0.12 ? "近似平线" : "",
  })).filter((item) => item.reason);
}

function detectBadSegments(data, windowSec = 1) {
  if (!data?.signals?.length || !data.sampleRate) return [];
  const sr = data.sampleRate;
  const windowSamples = Math.max(1, Math.floor(windowSec * sr));
  const totalWindows = Math.floor(data.signals[0].values.length / windowSamples);
  const segments = [];
  for (let win = 0; win < totalWindows; win += 1) {
    let peak = 0;
    const start = win * windowSamples;
    const end = start + windowSamples;
    data.signals.forEach((signal) => {
      for (let i = start; i < end && i < signal.values.length; i += Math.max(1, Math.floor(sr / 80))) {
        peak = Math.max(peak, Math.abs(signal.values[i]));
      }
    });
    if (peak > 180) segments.push({ start: start / sr, end: end / sr, peak });
  }
  return segments.slice(0, 24);
}

function detectIcaCandidates(data) {
  if (!data?.signals?.length) return [];
  return data.signals.slice(0, 12).map((signal) => {
    const stats = signalStats(signal.values, Math.max(1, Math.floor(signal.values.length / 4000)));
    const frontal = /^fp|^af|^f/i.test(signal.label);
    const score = Math.min(0.99, (frontal ? 0.35 : 0.08) + Math.min(0.55, stats.p2p / 500));
    return { label: signal.label, score, reason: frontal ? "疑似眼动相关通道" : "高振幅成分候选" };
  }).filter((item) => item.score >= 0.45).sort((a, b) => b.score - a.score).slice(0, 6);
}

function applyAverageReference(data) {
  const length = data.signals[0]?.values.length || 0;
  const output = cloneEegData(data);
  for (let i = 0; i < length; i += 1) {
    let sum = 0;
    output.signals.forEach((signal) => { sum += signal.values[i] || 0; });
    const avg = sum / output.signals.length;
    output.signals.forEach((signal) => { signal.values[i] = (signal.values[i] || 0) - avg; });
  }
  output.reference = "average";
  return output;
}

function applyChannelReference(data, channelLabel) {
  const refSignal = data.signals.find((signal) => signal.label === channelLabel);
  const output = cloneEegData(data);
  if (!refSignal) return output;
  output.signals.forEach((signal) => {
    for (let i = 0; i < signal.values.length; i += 1) signal.values[i] = (signal.values[i] || 0) - (refSignal.values[i] || 0);
  });
  output.reference = channelLabel;
  return output;
}

function preprocessConfigFromUi() {
  const highpass = parseNumber(qs("#preHighpassInput")?.value, eegState.filter.highpassHz);
  const lowpass = parseNumber(qs("#preLowpassInput")?.value, eegState.filter.lowpassHz);
  const notch = qs("#preNotchSelect")?.value || (eegState.filter.notchEnabled ? String(eegState.filter.notchHz) : "off");
  const componentCap = Math.max(2, eegState.data?.signals?.length || 64);
  return {
    filter: {
      enabled: true,
      highpassHz: highpass,
      lowpassHz: lowpass,
      notchEnabled: notch !== "off",
      notchHz: notch === "off" ? eegState.filter.notchHz : Number(notch),
      notchQ: eegState.filter.notchQ,
    },
    reference: qs("#preReferenceSelect")?.value || "average",
    referenceChannel: qs("#preReferenceChannelSelect")?.value || "",
    icaMethod: qs("#preIcaMethod")?.value || "fastica",
    icaComponents: Math.min(componentCap, Math.max(2, parseNumber(qs("#preIcaComponents")?.value, Math.min(20, componentCap)))),
    icaMaxIter: Math.max(100, parseNumber(qs("#preIcaMaxIter")?.value, 800)),
    icaDecim: Math.max(1, parseNumber(qs("#preIcaDecim")?.value, 2)),
    icaRandomState: Math.max(0, parseNumber(qs("#preIcaRandomState")?.value, 97)),
    icaThreshold: Math.max(0, Math.min(1, parseNumber(qs("#preIcaThreshold")?.value, 0.45))),
    icaExtended: (qs("#preIcaExtended")?.value || "true") === "true",
  };
}

function firstMatchingChannel(data, pattern) {
  return data?.signals?.find((signal) => pattern.test(signal.label))?.label || "";
}

function applyMastoidAverageReference(data, leftPattern, rightPattern) {
  const left = firstMatchingChannel(data, leftPattern);
  const right = firstMatchingChannel(data, rightPattern);
  if (left && right) {
    const leftSignal = data.signals.find((signal) => signal.label === left);
    const rightSignal = data.signals.find((signal) => signal.label === right);
    const output = cloneEegData(data);
    output.signals.forEach((signal) => {
      for (let i = 0; i < signal.values.length; i += 1) {
        signal.values[i] = (signal.values[i] || 0) - (((leftSignal.values[i] || 0) + (rightSignal.values[i] || 0)) / 2);
      }
    });
    output.reference = `${left}/${right}`;
    return { data: output, detail: `双乳突平均参考（${left}/${right}）`, ok: true };
  }
  return { data, detail: "未找到成对乳突通道 A1/A2 或 M1/M2", ok: false };
}

function applyPreprocessToData(data) {
  let next = cloneEegData(data);
  const steps = [];
  const config = preprocessConfigFromUi();
  eegState.filter = { ...eegState.filter, ...config.filter };
  next.signals = next.signals.map((signal) => ({
    ...signal,
    values: new Float32Array(filterPreviewSeries(signal.values, signal.sampleRate || next.sampleRate, config.filter)),
  }));
  steps.push({ name: "滤波", status: "已运行", detail: previewFilterLabel() });
  if (config.reference === "average") {
    next = applyAverageReference(next);
    steps.push({ name: "重参考", status: "已运行", detail: "平均参考，已从每个采样点扣除全通道均值" });
  } else if (config.reference === "cz") {
    next = applyChannelReference(next, "Cz");
    steps.push({ name: "重参考", status: "已运行", detail: "Cz 参考" });
  } else if (config.reference === "linked-mastoids") {
    const ref = applyMastoidAverageReference(next, /A1|M1|TP9/i, /A2|M2|TP10/i);
    next = ref.data;
    steps.push({ name: "重参考", status: ref.ok ? "已运行" : "需复核", detail: ref.detail });
  } else if (config.reference === "left-mastoid") {
    const mastoid = firstMatchingChannel(next, /A1|M1|TP9/i);
    next = mastoid ? applyChannelReference(next, mastoid) : next;
    steps.push({ name: "重参考", status: mastoid ? "已运行" : "需复核", detail: mastoid ? `左乳突参考（${mastoid}）` : "未找到 A1/M1/TP9 通道" });
  } else if (config.reference === "right-mastoid") {
    const mastoid = firstMatchingChannel(next, /A2|M2|TP10/i);
    next = mastoid ? applyChannelReference(next, mastoid) : next;
    steps.push({ name: "重参考", status: mastoid ? "已运行" : "需复核", detail: mastoid ? `右乳突参考（${mastoid}）` : "未找到 A2/M2/TP10 通道" });
  } else if (config.reference === "rest") {
    steps.push({ name: "重参考", status: "已记录", detail: "REST 参考需后端头模型支持，V0 记录参数但不改变波形" });
  } else if (config.reference === "channel" && config.referenceChannel) {
    next = applyChannelReference(next, config.referenceChannel);
    steps.push({ name: "重参考", status: "已运行", detail: `${config.referenceChannel} 参考` });
  } else {
    steps.push({ name: "重参考", status: "已跳过", detail: "保持原参考" });
  }
  const badChannels = detectBadChannels(next);
  steps.push({ name: "坏道检测", status: badChannels.length ? "需复核" : "通过", detail: badChannels.length ? `${badChannels.length} 个候选坏道` : "未发现明显坏道" });
  const badSegments = detectBadSegments(next);
  steps.push({ name: "坏段检测", status: badSegments.length ? "需复核" : "通过", detail: badSegments.length ? `${badSegments.length} 个候选坏段` : "未发现明显坏段" });
  const icaCandidates = detectIcaCandidates(next).filter((item) => item.score >= config.icaThreshold).slice(0, config.icaComponents);
  steps.push({ name: "ICA 预检", status: icaCandidates.length ? "有候选" : "通过", detail: `${config.icaMethod} / ${config.icaComponents} 成分 / max_iter ${config.icaMaxIter} / decim ${config.icaDecim} / random_state ${config.icaRandomState}${config.icaExtended ? " / extended" : ""}` });
  return { data: next, steps, badChannels, badSegments, icaCandidates };
}

function runPreprocess() {
  if (!eegState.data) {
    showToast("请先加载 EEG 数据");
    renderPreprocessPipeline();
    return;
  }
  if (!eegState.originalData) eegState.originalData = cloneEegData(eegState.data);
  const result = applyPreprocessToData(eegState.originalData);
  eegState.data = result.data;
  eegState.preprocess = {
    ran: true,
    steps: result.steps,
    badChannels: result.badChannels,
    badSegments: result.badSegments,
    icaCandidates: result.icaCandidates,
    summary: `已完成 ${result.steps.length} 个预处理步骤`,
  };
  renderEeg();
  renderPreprocessPipeline();
  drawPreprocessResults();
  showToast("预处理已运行并应用到当前预览");
}

function resetPreprocess() {
  if (!eegState.originalData) {
    showToast("没有可恢复的原始数据");
    return;
  }
  eegState.data = cloneEegData(eegState.originalData);
  eegState.preprocess = { ran: false, steps: [], badChannels: [], badSegments: [], icaCandidates: [], summary: "已恢复原始数据" };
  renderEeg();
  renderPreprocessPipeline();
  drawPreprocessResults();
  showToast("已恢复原始 EEG 数据");
}

function markCurrentSegmentBad() {
  if (!eegState.data) {
    showToast("请先加载 EEG 数据");
    return;
  }
  const segment = {
    start: eegState.start,
    end: eegState.start + eegState.windowSec,
    peak: 0,
    manual: true,
  };
  eegState.preprocess.badSegments = [
    ...eegState.preprocess.badSegments,
    segment,
  ].sort((a, b) => a.start - b.start);
  eegState.preprocess.ran = true;
  eegState.preprocess.summary = "已人工标记坏段";
  renderPreprocessPipeline();
  drawPreprocessResults();
  showToast("已标记当前时间窗为坏段");
}

function drawBadChannelTopo() {
  const canvas = qs("#badChannelTopoCanvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const w = canvas.width;
  const h = canvas.height;
  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = "#fbfcfd";
  ctx.fillRect(0, 0, w, h);
  const cx = w / 2;
  const cy = h / 2;
  const r = Math.min(w, h) * 0.36;
  ctx.strokeStyle = "#8fb7b4";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.arc(cx, cy, r, 0, Math.PI * 2);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(cx - 20, cy - r - 4);
  ctx.lineTo(cx, cy - r - 24);
  ctx.lineTo(cx + 20, cy - r - 4);
  ctx.stroke();
  const bad = new Set(eegState.preprocess.badChannels.map((item) => item.label));
  const labels = eegState.data?.signals?.slice(0, 32).map((item) => item.label) || [];
  labels.forEach((label, index) => {
    const angle = (Math.PI * 2 * index) / Math.max(1, labels.length) - Math.PI / 2;
    const rr = r * (0.28 + 0.68 * ((index % 4) / 3));
    const x = cx + Math.cos(angle) * rr;
    const y = cy + Math.sin(angle) * rr;
    ctx.fillStyle = bad.has(label) ? "#d95f43" : "#2fb36d";
    ctx.beginPath();
    ctx.arc(x, y, 6, 0, Math.PI * 2);
    ctx.fill();
  });
  ctx.fillStyle = "#526577";
  ctx.font = "13px Arial";
  ctx.fillText(bad.size ? `坏道候选 ${bad.size} 个` : "坏道检测通过：全绿", 18, h - 18);
}

function drawBadSegmentPreview() {
  const canvas = qs("#badSegmentCanvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const w = canvas.width;
  const h = canvas.height;
  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = "#fbfcfd";
  ctx.fillRect(0, 0, w, h);
  const signal = eegState.data?.signals?.[0];
  if (!signal) {
    ctx.fillStyle = "#6b7785";
    ctx.fillText("等待 EEG 数据", 24, 40);
    return;
  }
  const start = Math.floor(eegState.start * signal.sampleRate);
  const end = Math.min(signal.values.length - 1, Math.floor((eegState.start + eegState.windowSec) * signal.sampleRate));
  const values = signal.values.slice(start, end);
  const step = Math.max(1, Math.floor(values.length / Math.max(1, w - 60)));
  const stats = visibleSignalStats({ values }, 0, Math.max(0, values.length - 1), step);
  const left = 40;
  const top = 30;
  const plotW = w - 70;
  const plotH = h - 72;
  eegState.preprocess.badSegments.forEach((seg) => {
    if (seg.end < eegState.start || seg.start > eegState.start + eegState.windowSec) return;
    const x1 = left + ((seg.start - eegState.start) / eegState.windowSec) * plotW;
    const x2 = left + ((seg.end - eegState.start) / eegState.windowSec) * plotW;
    ctx.fillStyle = "rgba(217,95,67,0.18)";
    ctx.fillRect(x1, top, Math.max(2, x2 - x1), plotH);
  });
  ctx.strokeStyle = "#157a77";
  ctx.lineWidth = 1.4;
  ctx.beginPath();
  for (let i = 0; i < values.length; i += step) {
    const x = left + (i / Math.max(1, values.length - 1)) * plotW;
    const y = top + plotH / 2 - ((values[i] - stats.baseline) / Math.max(1, stats.scaleUv)) * (plotH * 0.3);
    if (i) ctx.lineTo(x, y);
    else ctx.moveTo(x, y);
  }
  ctx.stroke();
  ctx.fillStyle = "#526577";
  ctx.font = "13px Arial";
  ctx.fillText(`${signal.label} · 当前窗 ${eegState.start.toFixed(1)}-${(eegState.start + eegState.windowSec).toFixed(1)} s`, 18, h - 18);
}

function renderIcaResults() {
  const target = qs("#icaResultList");
  if (!target) return;
  const candidates = eegState.preprocess.icaCandidates;
  target.innerHTML = candidates.length ? candidates.map((item) => `
    <label class="ica-result-row">
      <input type="checkbox" checked />
      <span><strong>${escapeHtml(item.label)}</strong><small>${escapeHtml(item.reason)} · ${(item.score * 100).toFixed(0)}%</small></span>
    </label>
  `).join("") : `<div class="empty-card"><strong>暂无 ICA 候选</strong><span>运行预处理后显示可复核成分。</span></div>`;
}

function syncPreprocessReferenceOptions() {
  const wrap = qs("#preReferenceChannelLabel");
  const select = qs("#preReferenceChannelSelect");
  if (!wrap || !select) return;
  const show = (qs("#preReferenceSelect")?.value || "average") === "channel";
  wrap.hidden = !show;
  if (show) {
    select.innerHTML = (eegState.data?.signals || [])
      .map((signal) => `<option value="${escapeHtml(signal.label)}">${escapeHtml(signal.label)}</option>`)
      .join("") || `<option value="">等待 EEG 通道</option>`;
  }
}

function syncIcaControlLimits() {
  const input = qs("#preIcaComponents");
  if (!input) return;
  const channelCount = Math.max(2, eegState.data?.signals?.length || 64);
  input.max = String(channelCount);
  if (parseNumber(input.value, 20) > channelCount) input.value = String(channelCount);
}

function bindHelpButtons(root = document) {
  root.querySelectorAll("[data-help-topic]").forEach((button) => {
    button.onclick = () => {
      const message = PREPROCESS_HELP[button.dataset.helpTopic] || "该参数会写入任务 manifest，用于复现分析。";
      showToast(message);
    };
  });
}

function drawPreprocessResults() {
  syncPreprocessReferenceOptions();
  syncIcaControlLimits();
  drawBadChannelTopo();
  drawBadSegmentPreview();
  renderIcaResults();
  const ref = qs("#preReferenceResult");
  if (ref) ref.value = eegState.preprocess.steps.find((item) => item.name === "重参考")?.detail || "尚未运行";
}

function renderPreprocessPipeline() {
  const grid = qs("#preprocessPipelineGrid");
  const summary = qs("#preprocessRunSummary");
  const dataReady = Boolean(eegState.data);
  const steps = eegState.preprocess.ran ? eegState.preprocess.steps : [
    { name: "滤波", status: dataReady ? "待运行" : "等待数据", detail: previewFilterLabel() },
    { name: "重参考", status: dataReady ? "待运行" : "等待数据", detail: "平均参考" },
    { name: "坏道检测", status: dataReady ? "待运行" : "等待数据", detail: "基于 RMS / 平线检测" },
    { name: "坏段检测", status: dataReady ? "待运行" : "等待数据", detail: "1 秒窗峰值阈值 180 µV" },
    { name: "ICA 预检", status: dataReady ? "待运行" : "等待数据", detail: "前额通道与高振幅候选筛查" },
  ];
  if (grid) {
    grid.innerHTML = steps.map((step) => `
      <div class="preprocess-card ${step.status.includes("需") || step.status.includes("候选") ? "warning" : step.status.includes("已") || step.status === "通过" ? "done" : ""}">
        <strong>${escapeHtml(step.name)}</strong>
        <span>${escapeHtml(step.status)}</span>
        <small>${escapeHtml(step.detail)}</small>
      </div>
    `).join("");
  }
  if (summary) {
    const badChannels = eegState.preprocess.badChannels.map((item) => `${item.label}(${item.reason})`).join("、") || "无";
    const badSegments = eegState.preprocess.badSegments.length ? `${eegState.preprocess.badSegments.length} 段` : "无";
    const ica = eegState.preprocess.icaCandidates.map((item) => `${item.label} ${(item.score * 100).toFixed(0)}%`).join("、") || "无";
    summary.textContent = eegState.preprocess.ran
      ? `${eegState.preprocess.summary}。坏道：${badChannels}；坏段：${badSegments}；ICA 候选：${ica}。`
      : dataReady ? "已加载 EEG，可以运行真实前端预处理。" : "请先在“数据导入”页加载 EEG，再运行预处理。";
  }
  syncPreprocessReferenceOptions();
  syncIcaControlLimits();
  drawPreprocessResults();
}

function analysisStepItems() {
  const project = activeProject();
  const files = project ? ensureProjectFiles(project) : [];
  const hasPreview = Boolean(eegState.data) || Boolean(project?.localSample) || isLearningProject(project);
  const task = state.tasks.find((item) => item.projectId === project?.id);
  const resultReady = Boolean(project?.result?.status) || task?.status === "completed";
  return [
    { page: "home", icon: "layout-dashboard", title: "分析首页", detail: "查看流程状态和下一步", status: project ? "已选择项目" : "等待项目" },
    { page: "data", icon: "folder-input", title: "数据导入", detail: "上传文件并完成原始 QC", status: files.length ? "已有数据" : "未导入" },
    { page: "preprocess", icon: "sliders-horizontal", title: "预处理", detail: "滤波、重参考、ICA 和坏段", status: hasPreview ? "可配置" : "先预览" },
    { page: "method", icon: "workflow", title: "分析方法", detail: "选择 ERP/RRP、PSD 或 TFR", status: state.activeTemplate || "未选择" },
    { page: "submit", icon: "rocket", title: "提交任务", detail: "确认参数并创建分析任务", status: task ? task.status || "已提交" : "未提交" },
    { page: "result", icon: "file-chart-column", title: "结果状态", detail: "查看生成进度和交付入口", status: resultReady ? "已有结果" : "等待结果" },
  ];
}

function renderAnalysisHome() {
  const target = qs("#analysisHomeGrid");
  if (!target) return;
  target.innerHTML = analysisStepItems().map((item) => `
    <button type="button" class="analysis-home-card" data-view-jump="analysis" data-analysis-page="${item.page}">
      <i data-lucide="${item.icon}"></i>
      <strong>${escapeHtml(item.title)}</strong>
      <span>${escapeHtml(item.detail)}</span>
      <b>${escapeHtml(item.status)}</b>
    </button>
  `).join("");
  target.querySelectorAll("[data-analysis-page]").forEach((button) => {
    button.addEventListener("click", () => setAnalysisPage(button.dataset.analysisPage, { scroll: true }));
  });
  renderAnalysisResultStatus();
}

function renderAnalysisResultStatus() {
  const target = qs("#analysisResultGrid");
  if (!target) return;
  const project = activeProject();
  const task = state.tasks.find((item) => item.projectId === project?.id);
  const resultReady = Boolean(project?.result?.status) || task?.status === "completed";
  const items = [
    { icon: "folder-kanban", title: "当前项目", detail: project?.name || "尚未选择项目", status: project ? "已绑定" : "待选择" },
    { icon: "activity", title: "分析方法", detail: state.activeTemplate || "尚未选择分析方法", status: state.activeTemplate ? "已选择" : "待选择" },
    { icon: "timer", title: "任务状态", detail: task?.name || "尚未提交任务", status: task?.status || "未提交" },
    { icon: "package-check", title: "交付入口", detail: resultReady ? "结果包可进入交付模块查看" : "任务完成后自动生成交付入口", status: resultReady ? "可查看" : "等待结果" },
  ];
  target.innerHTML = items.map((item) => `
    <div class="analysis-home-card static">
      <i data-lucide="${item.icon}"></i>
      <strong>${escapeHtml(item.title)}</strong>
      <span>${escapeHtml(item.detail)}</span>
      <b>${escapeHtml(item.status)}</b>
    </div>
  `).join("");
}

function renderModuleRail(view = qs(".view.active")?.id || "dashboard") {
  const target = qs("#moduleRail");
  if (!target) return;
  if (view !== "analysis" || state.role !== "customer") {
    target.innerHTML = "";
    target.hidden = true;
    return;
  }
  target.hidden = false;
  const steps = analysisStepItems().filter((item) => item.page !== "home");
  const methodLabels = {
    "ERP 事件相关电位": "ERP/RRP",
    "静息态功率谱": "PSD",
    "时频分析": "TFR",
  };
  const railSteps = steps.map((item) => {
    if (item.page !== "method") return item;
    return {
      ...item,
      children: availableTemplates().map((template) => ({
        icon: template.icon,
        title: methodLabels[template.name] || template.name,
        detail: template.desc,
        templateName: template.name,
      })),
    };
  });
  target.innerHTML = `
    <section class="module-rail-group expanded">
      <div class="module-rail-title">
        <i data-lucide="chevron-down"></i>
        <span><strong>分析流程</strong><small>从数据到结果</small></span>
      </div>
      <div class="module-rail-list">
        ${railSteps.map((item) => `
          <div class="module-rail-node">
            <button type="button" class="module-rail-item ${item.page === state.analysisPage ? "active" : ""}" data-view-jump="analysis" data-analysis-page="${item.page}" data-rail-kind="step">
              <i data-lucide="${item.icon}"></i>
              <span><strong>${escapeHtml(item.title)}</strong><small>${escapeHtml(item.status)}</small></span>
            </button>
            ${item.children ? `
              <div class="module-rail-sublist method-list">
                ${item.children.map((child) => `
                  <button type="button" class="module-rail-item module-rail-subitem ${child.templateName === state.activeTemplate ? "active" : ""}" data-view-jump="analysis" data-analysis-page="method" data-workflow-template="${escapeHtml(child.templateName)}" data-rail-kind="method">
                    <i data-lucide="${child.icon}"></i>
                    <span><strong>${escapeHtml(child.title)}</strong><small>${escapeHtml(child.detail)}</small></span>
                  </button>
                `).join("")}
              </div>
            ` : ""}
          </div>
        `).join("")}
      </div>
    </section>
  `;
  target.querySelectorAll("[data-analysis-page]").forEach((button) => {
    button.addEventListener("click", () => {
      if (button.dataset.workflowTemplate) {
        state.activeTemplate = button.dataset.workflowTemplate;
        setSegmentMode(workflowRouteFor().segmentMode);
        renderTemplates();
        renderMethodParams();
        syncWorkflowRouteUi();
      }
      setAnalysisPage(button.dataset.analysisPage, { scroll: true });
    });
  });
  if (window.lucide) lucide.createIcons();
}

function setAnalysisPage(page = "home", options = {}) {
  const next = ANALYSIS_PAGES.has(page) ? page : "home";
  state.analysisPage = next;
  qsa(".analysis-page").forEach((section) => section.classList.toggle("active", section.dataset.analysisPage === next));
  qsa("#moduleRail [data-analysis-page]").forEach((button) => {
    const active = button.dataset.railKind === "method"
      ? button.dataset.workflowTemplate === state.activeTemplate
      : button.dataset.analysisPage === next;
    button.classList.toggle("active", active);
    button.setAttribute("aria-current", active ? "page" : "false");
  });
  renderPreprocessSummary();
  renderMethodParams();
  renderAnalysisHome();
  renderModuleRail("analysis");
  if (options.scroll) qs(".analysis-shell")?.scrollIntoView({ behavior: "smooth", block: "start" });
  if (window.lucide) lucide.createIcons();
}

function renderMethodParams() {
  const title = qs("#methodParamTitle");
  const hint = qs("#methodParamHint");
  const panel = qs("#methodParamPanel");
  if (!panel) return;
  if (state.activeTemplate === "ERP 事件相关电位") {
    if (title) title.textContent = "ERP/RRP 参数";
    if (hint) hint.textContent = "事件锁定分析只显示事件、epoch 和 baseline 参数。";
    panel.innerHTML = `
      <div class="form-grid">
        <label><span>事件类型 ${helpIcon("eventType", "事件类型")}</span><select id="eventType"><option value="">等待读取事件标签</option></select></label>
        <label><span>事件前 ${helpIcon("eventPre", "事件前")}</span><div class="with-unit"><input id="eventPre" type="number" value="-0.2" step="0.1" /><em>秒</em></div></label>
        <label><span>事件后 ${helpIcon("eventPost", "事件后")}</span><div class="with-unit"><input id="eventPost" type="number" value="0.8" step="0.1" /><em>秒</em></div></label>
        <label><span>Baseline ${helpIcon("erpBaseline", "Baseline")}</span><select id="erpBaseline"><option>-0.2 到 0 秒</option><option>不校正</option></select></label>
      </div>
    `;
    state.segmentMode = "event";
  } else if (state.activeTemplate === "静息态功率谱") {
    if (title) title.textContent = "PSD 参数";
    if (hint) hint.textContent = "频谱分析只显示连续窗、Welch 和频段参数。";
    panel.innerHTML = `
      <div class="form-grid">
        <label><span>开始时间 ${helpIcon("segmentStart", "开始时间")}</span><div class="with-unit"><input id="segmentStart" type="number" value="12" min="0" step="0.1" /><em>秒</em></div></label>
        <label><span>结束时间 ${helpIcon("segmentEnd", "结束时间")}</span><div class="with-unit"><input id="segmentEnd" type="number" value="18" min="0" step="0.1" /><em>秒</em></div></label>
        <label><span>Welch 窗长 ${helpIcon("psdWelchWindow", "Welch 窗长")}</span><select id="psdWelchWindow"><option>2 秒</option><option selected>4 秒</option><option>8 秒</option></select></label>
        <label><span>频段 ${helpIcon("psdBands", "频段")}</span><select id="psdBands"><option selected>Delta/Theta/Alpha/Beta</option><option>Alpha peak</option><option>自定义 1-45 Hz</option></select></label>
      </div>
    `;
    state.segmentMode = "time";
  } else {
    if (title) title.textContent = "TFR 参数";
    if (hint) hint.textContent = "时频分析只显示频率范围、时间窗和基线方式。";
    panel.innerHTML = `
      <div class="form-grid">
        <label><span>事件类型 ${helpIcon("eventType", "事件类型")}</span><select id="eventType"><option value="">等待读取事件标签</option></select></label>
        <label><span>频率范围 ${helpIcon("tfrFreqRange", "频率范围")}</span><select id="tfrFreqRange"><option selected>4-40 Hz</option><option>8-30 Hz</option><option>1-80 Hz</option></select></label>
        <label><span>时间窗 ${helpIcon("tfrWindow", "时间窗")}</span><select id="tfrWindow"><option selected>-0.5 到 1.5 秒</option><option>-1 到 2 秒</option></select></label>
        <label><span>基线 ${helpIcon("tfrBaseline", "基线")}</span><select id="tfrBaseline"><option selected>-0.3 到 0 秒</option><option>不校正</option></select></label>
      </div>
    `;
    state.segmentMode = "event";
  }
  renderEventDrivenControls();
  qsa("#methodParamPanel input, #methodParamPanel select").forEach((item) => item.addEventListener("change", updateSegmentSummary));
  bindHelpButtons(panel);
  updateSegmentSummary();
  if (window.lucide) lucide.createIcons();
}

function syncWorkflowRouteUi() {
  const route = workflowRouteFor();
  if (route.segmentMode) setSegmentMode(route.segmentMode);
  qsa(".workflow-route-picker button").forEach((button) => {
    const active = button.dataset.workflowTemplate === state.activeTemplate;
    button.classList.toggle("active", active);
    button.setAttribute("aria-checked", active ? "true" : "false");
  });
  const summary = qs("#workflowRouteSummary");
  if (!summary) return;
  const title = summary.querySelector("strong");
  const detail = summary.querySelector("span");
  if (title) title.textContent = route.title;
  if (detail) detail.textContent = route.detail;
}

function renderTemplateStatus() {
  const item = activeTemplate();
  const target = qs("#templateSelectionStatus");
  if (!target) return;
  target.innerHTML = `
    <strong>当前模板：${item.name}</strong>
    <span>${item.desc}</span>
    <b>提交后进入异步队列，结果写入当前项目交付件。</b>
  `;
}

function renderCustomerChecks() {
  const learning = isLearningProject(activeProject());
  const formalCopy = {
    subjectMeta: "被试编号、组别和任务范式已填写。",
    channelMeta: "通道表、采样率和参考电极已核对。",
    eventMap: "事件标签已对应到实验条件。",
    dataConsent: "数据授权范围已确认。",
  };
  const learningCopy = {
    subjectMeta: "我已理解正式项目需确认被试编号、组别和任务范式。",
    channelMeta: "我已理解正式项目需核对通道表、采样率和参考电极。",
    eventMap: "我已理解正式项目需把事件标签对应到实验条件。",
    dataConsent: "我已理解正式项目提交前需确认数据授权范围。",
  };
  const copy = learning ? learningCopy : formalCopy;
  qsa("[data-check-copy]").forEach((node) => {
    node.textContent = copy[node.dataset.checkCopy] || node.textContent;
  });
}

function renderPreview() {
  const caption = qs("#previewCaption");
  if (caption) caption.textContent = "原始波形用于核对通道质量、事件位置、振幅尺度和可分析片段。";
}

function updateFormalPreviewVisibility() {
  const hasData = Boolean(eegState.data) && eegState.sourceMode === "formal";
  const open = state.formalPreviewOpen || hasData;
  const empty = qs("#formalPreviewEmpty");
  const toolbar = qs(".eeg-toolbar");
  const viewer = qs(".eeg-viewer");
  const meta = qs("#eegMeta");
  const events = qs("#eegEvents");
  if (empty) empty.hidden = open;
  if (toolbar) toolbar.hidden = !open;
  if (viewer) viewer.hidden = !open;
  if (meta) meta.hidden = !open;
  if (events) events.hidden = !open;
}

function resetEegPreview(message = "正在等待加载 EDF 数据。") {
  eegState.data = null;
  eegState.originalData = null;
  eegState.preprocess = { ran: false, steps: [], badChannels: [], badSegments: [], icaCandidates: [], summary: "请先加载 EEG 数据" };
  eegState.events = [];
  eegState.eventSource = "none";
  eegState.sourceName = "";
  eegState.sourceMode = "";
  eegState.autoloaded = false;
  eegState.start = 0;
  const empty = qs("#eegEmpty");
  if (empty) {
    empty.classList.remove("ready");
    empty.textContent = message;
  }
  if (qs("#eegMeta")) qs("#eegMeta").innerHTML = "";
  if (qs("#eegEvents")) qs("#eegEvents").innerHTML = "";
  renderEventDrivenControls();
  updateFormalPreviewVisibility();
  drawEeg();
  renderPreprocessPipeline();
}

function renderTeachingDataset(manifest = null) {
  const channelCount = manifest?.channels?.length || TEACHING_DATASET.channelCount;
  const duration = manifest?.duration_sec || TEACHING_DATASET.durationSec;
  const events = manifest?.events_count || TEACHING_DATASET.eventsCount;
  if (qs("#teachingChannelCount")) qs("#teachingChannelCount").textContent = `${channelCount} 通道`;
  if (qs("#teachingDuration")) qs("#teachingDuration").textContent = `${duration} 秒`;
  if (qs("#teachingEventCount")) qs("#teachingEventCount").textContent = `${events} 个`;
  if (qs("#adminTeachingDatasetMeta")) qs("#adminTeachingDatasetMeta").textContent = `${channelCount} 通道 / ${duration} 秒 / EDF + events.tsv`;
  registerDeliveryItems(TEACHING_DELIVERIES, "teaching");
  bindDeliveryPreviewButtons(qs("#teaching") || document);
  if (window.lucide) lucide.createIcons();
}

async function loadTeachingManifest() {
  try {
    const response = await fetch(TEACHING_DATASET.manifestUrl);
    if (!response.ok) return;
    renderTeachingDataset(await response.json());
  } catch {
    renderTeachingDataset();
  }
}

function appendAdminTaskFromCustomer(cost) {
  const project = activeProject();
  const learning = isLearningProject(project);
  const id = `admin-task-${Date.now()}`;
  const now = new Date().toLocaleTimeString("zh-CN", { hour12: false });
  const task = {
    id,
    customer: learning ? "学习模式体验客户" : getStoredCustomer().name || "客户账户",
    project: project?.name || "新建分析项目",
    file: project?.file || "等待上传 EEG 文件",
    size: project?.size || "-",
    cost,
    submittedAt: new Date().toLocaleString("zh-CN", { hour12: false }),
    currentNodeId: "queue_assign",
    failedNodeIds: [],
    doneNodeIds: ["intake", "profile_check", "cost_freeze", "upload_store"],
    history: [
      { time: now, nodeId: "intake", status: "完成", note: learning ? "客户提交学习体验任务" : "客户提交分析任务" },
      { time: now, nodeId: "profile_check", status: "完成", note: "账号与项目权限通过" },
      { time: now, nodeId: "cost_freeze", status: "完成", note: learning ? "学习模式免扣费" : `冻结 ${money(cost)}` },
      { time: now, nodeId: "queue_assign", status: "当前", note: "等待 worker 调度" },
    ],
  };
  state.adminTasks.unshift(task);
  state.adminActiveTaskId = id;
  renderAdminTaskMonitor();
  renderAllAdmin();
  return task;
}

function textField(decoder, bytes, start, length) {
  return decoder.decode(bytes.slice(start, start + length)).trim();
}

function parseNumber(value, fallback = 0) {
  const parsed = Number(String(value).trim());
  return Number.isFinite(parsed) ? parsed : fallback;
}

function formatHz(value) {
  const rounded = Math.round(Number(value) * 10) / 10;
  return Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(1);
}

function readSigned24(view, offset) {
  let value = view.getUint8(offset) | (view.getUint8(offset + 1) << 8) | (view.getUint8(offset + 2) << 16);
  if (value & 0x800000) value -= 0x1000000;
  return value;
}

function parseEdf(buffer, sourceName = "") {
  const bytes = new Uint8Array(buffer);
  const view = new DataView(buffer);
  const decoder = new TextDecoder("ascii");
  const version = textField(decoder, bytes, 0, 8);
  const isBdf = version.includes("BIOSEMI") || /\.bdf$/i.test(sourceName);
  const bytesPerSample = isBdf ? 3 : 2;
  const headerBytes = parseNumber(textField(decoder, bytes, 184, 8), 256);
  const records = parseNumber(textField(decoder, bytes, 236, 8), 1);
  const recordDuration = parseNumber(textField(decoder, bytes, 244, 8), 1);
  const signalCount = parseNumber(textField(decoder, bytes, 252, 4), 0);
  if (!signalCount || headerBytes < 256 + signalCount * 256) throw new Error("EDF 文件头不完整，无法读取通道信息。");

  let offset = 256;
  const readArray = (length) => {
    const values = [];
    for (let i = 0; i < signalCount; i += 1) values.push(textField(decoder, bytes, offset + i * length, length));
    offset += length * signalCount;
    return values;
  };
  const labels = readArray(16);
  readArray(80);
  const physicalDims = readArray(8);
  const physicalMin = readArray(8).map((item) => parseNumber(item));
  const physicalMax = readArray(8).map((item) => parseNumber(item));
  const digitalMin = readArray(8).map((item) => parseNumber(item));
  const digitalMax = readArray(8).map((item) => parseNumber(item));
  readArray(80);
  const samplesPerRecord = readArray(8).map((item) => parseNumber(item));
  const samplesPerRecordTotal = samplesPerRecord.reduce((sum, item) => sum + item, 0);
  const usableRecords = Math.max(1, records < 0 ? Math.floor((bytes.length - headerBytes) / (samplesPerRecordTotal * bytesPerSample)) : records);
  const firstEegIndex = labels.findIndex((label, index) => !label.toLowerCase().includes("annotation") && Boolean(physicalDims[index]));
  const sampleRate = samplesPerRecord[Math.max(0, firstEegIndex)] / recordDuration;
  const duration = usableRecords * recordDuration;
  const signals = labels.map((label, ch) => ({
    label: label || `Ch ${ch + 1}`,
    unit: physicalDims[ch] || "uV",
    sampleRate: samplesPerRecord[ch] / recordDuration,
    values: new Float32Array(samplesPerRecord[ch] * usableRecords),
  }));

  const channelTransforms = labels.map((label, ch) => {
    const dim = physicalDims[ch].toLowerCase();
    return {
      isEeg: !label.toLowerCase().includes("annotation") && Boolean(physicalDims[ch]),
      scale: (physicalMax[ch] - physicalMin[ch]) / (digitalMax[ch] - digitalMin[ch] || 1),
      toMicrovolt: dim === "v" ? 1e6 : dim === "mv" ? 1e3 : 1,
    };
  });

  let dataOffset = headerBytes;
  for (let record = 0; record < usableRecords; record += 1) {
    for (let ch = 0; ch < signalCount; ch += 1) {
      const count = samplesPerRecord[ch];
      const base = record * count;
      for (let i = 0; i < count; i += 1) {
        const digital = isBdf
          ? dataOffset + 2 < bytes.length ? readSigned24(view, dataOffset) : 0
          : dataOffset + 1 < bytes.length ? view.getInt16(dataOffset, true) : 0;
        if (channelTransforms[ch].isEeg) {
          signals[ch].values[base + i] = ((digital - digitalMin[ch]) * channelTransforms[ch].scale + physicalMin[ch]) * channelTransforms[ch].toMicrovolt;
        }
        dataOffset += bytesPerSample;
      }
    }
  }

  const eegSignals = signals.filter((signal, index) => channelTransforms[index].isEeg);
  return { labels: eegSignals.map((signal) => signal.label), signals: eegSignals, sampleRate, duration, records: usableRecords, recordDuration, sourceUnit: "uV", format: isBdf ? "BDF" : "EDF" };
}

function parseEvents(text) {
  const lines = text.trim().split(/\r?\n/).filter(Boolean);
  if (lines.length < 2) return [];
  const header = lines[0].split(/\t|,/).map((item) => item.trim());
  const onsetIndex = header.includes("onset") ? header.indexOf("onset") : header.indexOf("onset_sec");
  const durationIndex = header.indexOf("duration");
  const typeIndex = header.includes("trial_type") ? header.indexOf("trial_type") : header.indexOf("event_label");
  if (onsetIndex < 0) return [];
  return lines.slice(1).map((line) => {
    const parts = line.split(/\t|,/);
    return {
      onset: parseNumber(parts[onsetIndex], 0),
      duration: durationIndex >= 0 ? parseNumber(parts[durationIndex], 0) : 0,
      type: typeIndex >= 0 ? parts[typeIndex] : "event",
    };
  }).filter((event) => Number.isFinite(event.onset));
}

function eventTypeCounts(events = []) {
  const counts = new Map();
  events.forEach((event) => {
    const type = String(event.type || "event").trim() || "event";
    counts.set(type, (counts.get(type) || 0) + 1);
  });
  return [...counts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
}

function eventAnalysisState() {
  const counts = eventTypeCounts(eegState.events);
  if (!counts.length) {
    return {
      mode: "none",
      title: "未读到事件标签",
      message: "当前 EEG 没有可用 annotations/events。建议先做连续片段浏览、静息态功率谱或上传事件表；ERP 条件分析不能凭阈值自动假设。",
      params: "可用：连续数据段、PSD、坏段复核。需要 ERP 时，请补充 onset + event_label/trial_type 事件表。",
    };
  }
  if (counts.length === 1) {
    const [label, count] = counts[0];
    return {
      mode: "single",
      title: `读到 1 类事件：${label}`,
      message: `共 ${count} 个事件。可以做单条件 epoch、诱发响应和质控；如果要做条件差异，需要另一类事件或实验日志映射。`,
      params: `建议窗口：-0.2 到 0.8 s；事件类型：${label}。不要把单一事件强行解释为 target/standard 对比。`,
    };
  }
  const top = counts.slice(0, 4).map(([label, count]) => `${label}(${count})`).join(" / ");
  return {
    mode: "multi",
    title: `从数据读到 ${counts.length} 类事件`,
    message: `事件标签：${top}。方法推荐应基于这些真实标签，再由用户确认实验语义。`,
    params: `可做事件锁定 ERP/时频；条件对比需确认标签含义，不能只按名称自动判定范式。`,
  };
}

function renderEventDrivenControls() {
  const counts = eventTypeCounts(eegState.events);
  const eventSelect = qs("#eventType");
  if (eventSelect) {
    eventSelect.innerHTML = counts.length
      ? counts.map(([label, count], index) => `<option value="${escapeHtml(label)}"${index === 0 ? " selected" : ""}>${escapeHtml(label)} (${count})</option>`).join("")
      : `<option value="">未读到事件标签</option>`;
    eventSelect.disabled = !counts.length;
  }
  const methodSelect = qs("#methodSignal");
  if (methodSelect) {
    if (counts.length) {
      methodSelect.innerHTML = [
        `<option value="auto">按 EEG 事件标签推荐</option>`,
        ...counts.map(([label, count]) => `<option value="event:${escapeHtml(label)}">${escapeHtml(label)} (${count})</option>`),
        `<option value="continuous">改做连续数据/静息态</option>`,
      ].join("");
      methodSelect.value = "auto";
    } else {
      methodSelect.innerHTML = [
        `<option value="continuous">无事件：连续数据/静息态</option>`,
        `<option value="auto">等待 EEG 事件标签</option>`,
      ].join("");
      methodSelect.value = "continuous";
    }
  }
  updateSegmentSummary();
  const recommendation = qs("#methodRecommendation");
  if (recommendation) {
    const stateInfo = eventAnalysisState();
    recommendation.classList.add("event-fact");
    recommendation.classList.toggle("warning", stateInfo.mode === "none");
    recommendation.innerHTML = `
      <strong>${escapeHtml(stateInfo.title)}</strong>
      <span>${escapeHtml(stateInfo.message)}</span>
      <b>${escapeHtml(stateInfo.params)}</b>
    `;
  }
}

function clampEegStart() {
  if (!eegState.data) {
    eegState.start = 0;
    return;
  }
  eegState.start = Math.max(0, Math.min(eegState.start, Math.max(0, eegState.data.duration - eegState.windowSec)));
  if (qs("#eegStartInput")) qs("#eegStartInput").value = eegState.start.toFixed(1);
}

function eegNyquistHz() {
  const sampleRate = eegState.data?.sampleRate || 0;
  return sampleRate > 0 ? sampleRate / 2 : 0;
}

function previewFilterMaxHz(sampleRate) {
  const nyquist = sampleRate > 0 ? sampleRate / 2 : eegNyquistHz();
  if (!nyquist) return 0;
  return Math.max(0.1, nyquist - Math.max(0.1, Math.min(1, nyquist * 0.01)));
}

function clampEegFilter() {
  const filter = eegState.filter;
  const maxHz = previewFilterMaxHz(eegState.data?.sampleRate || 0) || 499.5;
  filter.highpassHz = Math.max(0, Math.min(parseNumber(filter.highpassHz, 0.5), Math.max(0, maxHz - 0.1)));
  filter.lowpassHz = Math.max(0.1, Math.min(parseNumber(filter.lowpassHz, 40), maxHz));
  if (filter.highpassHz >= filter.lowpassHz) filter.highpassHz = Math.max(0, filter.lowpassHz - 0.1);
  filter.notchHz = Math.max(1, Math.min(parseNumber(filter.notchHz, 50), maxHz));
  filter.notchQ = Math.max(5, Math.min(parseNumber(filter.notchQ, 30), 100));
}

function previewFilterLabel() {
  const filter = eegState.filter;
  if (!filter.enabled) return "原始";
  const highpass = filter.highpassHz > 0 ? `${formatHz(filter.highpassHz)}-` : "";
  const band = `${highpass}${formatHz(filter.lowpassHz)} Hz`;
  return filter.notchEnabled ? `${band} + 陷波 ${formatHz(filter.notchHz)} Hz` : band;
}

function updateEegControls() {
  clampEegFilter();
  const filter = eegState.filter;
  const nyquist = eegNyquistHz();
  const maxHz = previewFilterMaxHz(eegState.data?.sampleRate || 0) || 499.5;
  if (qs("#eegWindowLabel")) qs("#eegWindowLabel").textContent = `${eegState.windowSec} s`;
  if (qs("#eegGainLabel")) qs("#eegGainLabel").textContent = `${eegState.gain}x`;
  if (qs("#eegFilterLabel")) qs("#eegFilterLabel").textContent = previewFilterLabel();
  if (qs("#eegChannelLabel")) qs("#eegChannelLabel").textContent = String(eegState.visibleChannels);
  if (qs("#eegWindowInput")) qs("#eegWindowInput").value = String(eegState.windowSec);
  if (qs("#eegGainInput")) qs("#eegGainInput").value = String(eegState.gain);
  if (qs("#eegFilterEnable")) qs("#eegFilterEnable").checked = filter.enabled;
  if (qs("#eegHighpassInput")) {
    qs("#eegHighpassInput").max = Math.max(0, filter.lowpassHz - 0.1).toFixed(1);
    qs("#eegHighpassInput").disabled = !filter.enabled;
    qs("#eegHighpassInput").value = formatHz(filter.highpassHz);
  }
  if (qs("#eegLowpassInput")) {
    qs("#eegLowpassInput").max = maxHz.toFixed(1);
    qs("#eegLowpassInput").disabled = !filter.enabled;
    qs("#eegLowpassInput").value = formatHz(filter.lowpassHz);
  }
  if (qs("#eegNotchEnable")) {
    qs("#eegNotchEnable").checked = filter.notchEnabled;
    qs("#eegNotchEnable").disabled = !filter.enabled;
  }
  if (qs("#eegNotchInput")) {
    qs("#eegNotchInput").max = maxHz.toFixed(1);
    qs("#eegNotchInput").disabled = !filter.enabled || !filter.notchEnabled;
    qs("#eegNotchInput").value = formatHz(filter.notchHz);
  }
  if (qs("#eegFilterLimit")) {
    qs("#eegFilterLimit").textContent = nyquist ? `Nyquist ${formatHz(nyquist)} Hz，上限 ${formatHz(maxHz)} Hz` : "等待数据采样率";
  }
  if (qs("#eegChannelInput")) qs("#eegChannelInput").value = String(eegState.visibleChannels);
  clampEegStart();
}

function percentileSorted(values, ratio) {
  if (!values.length) return 0;
  const index = Math.max(0, Math.min(values.length - 1, Math.floor((values.length - 1) * ratio)));
  return values[index];
}

function visibleSignalStats(signal, startSample, endSample, step) {
  const sampled = [];
  for (let i = startSample; i <= endSample; i += step) {
    const value = signal.values[i];
    if (Number.isFinite(value)) sampled.push(value);
  }
  if (!sampled.length) return { baseline: 0, scaleUv: 1, peakUv: 0 };
  const sorted = [...sampled].sort((a, b) => a - b);
  const baseline = percentileSorted(sorted, 0.5);
  const deviations = sampled.map((value) => Math.abs(value - baseline)).sort((a, b) => a - b);
  const scaleUv = Math.max(1, percentileSorted(deviations, 0.98));
  const peakUv = deviations[deviations.length - 1] || scaleUv;
  return { baseline, scaleUv, peakUv };
}

function applyNotchFilter(values, sampleRate, notchHz, q = 30) {
  if (!sampleRate || notchHz <= 0 || notchHz >= sampleRate / 2 || values.length < 4) return values;
  const w0 = (2 * Math.PI * notchHz) / sampleRate;
  const cosW0 = Math.cos(w0);
  const alpha = Math.sin(w0) / (2 * q);
  const a0 = 1 + alpha;
  const b0 = 1 / a0;
  const b1 = (-2 * cosW0) / a0;
  const b2 = 1 / a0;
  const a1 = (-2 * cosW0) / a0;
  const a2 = (1 - alpha) / a0;
  const out = new Float32Array(values.length);
  let x1 = 0;
  let x2 = 0;
  let y1 = 0;
  let y2 = 0;
  for (let i = 0; i < values.length; i += 1) {
    const x0 = values[i];
    const y0 = b0 * x0 + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2;
    out[i] = y0;
    x2 = x1;
    x1 = x0;
    y2 = y1;
    y1 = y0;
  }
  return out;
}

function filterPreviewSeries(values, sampleRate, filterConfig) {
  if (!filterConfig?.enabled || values.length < 4) return values;
  const maxHz = previewFilterMaxHz(sampleRate);
  const lowHz = Math.max(0, Math.min(parseNumber(filterConfig.highpassHz, 0), Math.max(0, maxHz - 0.1)));
  const highHz = Math.max(0.1, Math.min(parseNumber(filterConfig.lowpassHz, sampleRate / 2), maxHz || sampleRate / 2));
  const dt = 1 / sampleRate;
  let out = values;
  if (lowHz > 0) {
    const rc = 1 / (2 * Math.PI * lowHz);
    const alpha = rc / (rc + dt);
    const highPassed = new Float32Array(out.length);
    highPassed[0] = 0;
    for (let i = 1; i < out.length; i += 1) {
      highPassed[i] = alpha * (highPassed[i - 1] + out[i] - out[i - 1]);
    }
    out = highPassed;
  }
  if (filterConfig.notchEnabled) {
    out = applyNotchFilter(out, sampleRate, parseNumber(filterConfig.notchHz, 50), filterConfig.notchQ);
  }
  if (highHz > 0 && highHz < sampleRate / 2) {
    const rc = 1 / (2 * Math.PI * highHz);
    const alpha = dt / (rc + dt);
    const lowPassed = new Float32Array(out.length);
    lowPassed[0] = out[0];
    for (let i = 1; i < out.length; i += 1) {
      lowPassed[i] = lowPassed[i - 1] + alpha * (out[i] - lowPassed[i - 1]);
    }
    out = lowPassed;
  }
  return out;
}

function drawEeg() {
  const canvas = qs("#eegCanvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const rect = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  canvas.width = Math.max(900, Math.floor(rect.width * dpr));
  canvas.height = Math.floor(520 * dpr);
  ctx.scale(dpr, dpr);
  const width = canvas.width / dpr;
  const height = canvas.height / dpr;
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#fbfcfd";
  ctx.fillRect(0, 0, width, height);

  const data = eegState.data;
  if (!data) return;
  const left = 78;
  const right = 18;
  const top = 28;
  const bottom = 34;
  const plotW = width - left - right;
  const plotH = height - top - bottom;
  const channels = data.signals.slice(0, Math.min(eegState.visibleChannels, data.signals.length));
  const spacing = plotH / Math.max(1, channels.length);
  const pxPerSecond = plotW / eegState.windowSec;
  const visualGain = Math.max(0.25, eegState.gain / 2);

  ctx.strokeStyle = "#e8edf2";
  ctx.lineWidth = 1;
  ctx.fillStyle = "#6b7785";
  ctx.font = "12px Arial";
  for (let s = Math.ceil(eegState.start); s <= eegState.start + eegState.windowSec; s += 1) {
    const x = left + (s - eegState.start) * pxPerSecond;
    ctx.beginPath();
    ctx.moveTo(x, top);
    ctx.lineTo(x, top + plotH);
    ctx.stroke();
    if ((s - Math.ceil(eegState.start)) % 2 === 0) ctx.fillText(`${s}s`, x + 3, height - 12);
  }

  eegState.events
    .filter((event) => event.onset >= eegState.start && event.onset <= eegState.start + eegState.windowSec)
    .forEach((event) => {
      const x = left + (event.onset - eegState.start) * pxPerSecond;
      ctx.strokeStyle = event.type.includes("target") ? "#d86b4f" : "#157a77";
      ctx.beginPath();
      ctx.moveTo(x, top);
      ctx.lineTo(x, top + plotH);
      ctx.stroke();
      ctx.fillStyle = ctx.strokeStyle;
      ctx.fillText(event.type.replace("stim/", ""), x + 4, top + 14);
    });

  channels.forEach((signal, ch) => {
    const y0 = top + spacing * (ch + 0.5);
    ctx.strokeStyle = "#d9e0e7";
    ctx.beginPath();
    ctx.moveTo(left, y0);
    ctx.lineTo(left + plotW, y0);
    ctx.stroke();
    ctx.fillStyle = "#17202a";
    ctx.fillText(signal.label, 10, y0 + 4);

    const sr = signal.sampleRate;
    const startSample = Math.max(0, Math.floor(eegState.start * sr));
    const endSample = Math.min(signal.values.length - 1, Math.ceil((eegState.start + eegState.windowSec) * sr));
    const rawSegment = signal.values.slice(startSample, endSample + 1);
    const previewSegment = filterPreviewSeries(rawSegment, sr, eegState.filter);
    const step = Math.max(1, Math.floor(previewSegment.length / plotW));
    const previewSignal = { values: previewSegment };
    const stats = visibleSignalStats(previewSignal, 0, previewSegment.length - 1, step);
    const scaleToPx = (spacing * 0.38 * visualGain) / stats.scaleUv;
    ctx.strokeStyle = ch % 2 ? "#457b9d" : "#157a77";
    ctx.lineWidth = 1.3;
    ctx.beginPath();
    let moved = false;
    for (let i = 0; i < previewSegment.length; i += step) {
      const t = (startSample + i) / sr;
      const x = left + (t - eegState.start) * pxPerSecond;
      const centered = previewSegment[i] - stats.baseline;
      const y = y0 - Math.max(-spacing * 0.48, Math.min(spacing * 0.48, centered * scaleToPx));
      if (!moved) {
        ctx.moveTo(x, y);
        moved = true;
      } else {
        ctx.lineTo(x, y);
      }
    }
    ctx.stroke();
    ctx.fillStyle = "#8a96a3";
    ctx.fillText(`±${stats.scaleUv.toFixed(0)}µV`, left + plotW - 48, y0 - 5);
  });

  ctx.fillStyle = "#6b7785";
  const filterText = `${previewFilterLabel()}${eegState.filter.enabled ? " 预览滤波" : ""}`;
  ctx.fillText(`时间窗 ${eegState.start.toFixed(1)}-${(eegState.start + eegState.windowSec).toFixed(1)} s · ${filterText} · 增益 ${eegState.gain}x · 单位 µV`, left, 18);
}

function renderEegMeta() {
  const data = eegState.data;
  const meta = qs("#eegMeta");
  const events = qs("#eegEvents");
  if (!data) return;
  if (meta) {
    meta.innerHTML = [
      `文件：${eegState.sourceName}`,
      `通道：${data.signals.length}`,
      `采样率：${data.sampleRate.toFixed(0)} Hz`,
      `Nyquist：${formatHz(eegNyquistHz())} Hz`,
      `时长：${data.duration.toFixed(1)} s`,
      `事件：${eventTypeCounts(eegState.events).length ? eventTypeCounts(eegState.events).map(([label, count]) => `${label} ${count}`).join(" / ") : "未读到"}`,
      `当前显示：${Math.min(eegState.visibleChannels, data.signals.length)} 通道`,
    ].map((item) => `<span>${item}</span>`).join("");
  }
  if (events) {
    const visible = eegState.events.filter((event) => event.onset >= eegState.start && event.onset <= eegState.start + eegState.windowSec).slice(0, 8);
    events.innerHTML = visible.length
      ? visible.map((event) => `<span>${event.onset.toFixed(2)}s ${event.type}</span>`).join("")
      : "<span>当前时间窗内暂无事件</span>";
  }
}

function renderEeg() {
  updateEegControls();
  renderEegMeta();
  drawEeg();
}

async function loadEegFromBuffer(buffer, sourceName, eventsText = "", sourceMode = "formal") {
  try {
    eegState.data = parseEdf(buffer, sourceName);
    eegState.originalData = cloneEegData(eegState.data);
    eegState.preprocess = { ran: false, steps: [], badChannels: [], badSegments: [], icaCandidates: [], summary: "已加载原始数据，等待运行预处理" };
    eegState.events = eventsText ? parseEvents(eventsText) : [];
    eegState.eventSource = eegState.events.length ? "events-table" : "none";
    eegState.sourceName = sourceName;
    eegState.sourceMode = sourceMode;
    eegState.start = 0;
    eegState.visibleChannels = Math.min(8, eegState.data.signals.length);
    if (qs("#eegChannelInput")) qs("#eegChannelInput").max = String(Math.max(4, eegState.data.signals.length));
    if (sourceMode === "formal") {
      state.formalPreviewOpen = true;
      qs("#eegEmpty")?.classList.add("ready");
      qs("#eegEmpty").textContent = "预览已加载。";
    }
    updateFormalPreviewVisibility();
    renderEventDrivenControls();
    renderEeg();
    renderPreprocessPipeline();
    showToast(`已加载脑电：${sourceName}`);
  } catch (error) {
    qs("#eegEmpty")?.classList.remove("ready");
    qs("#eegEmpty").textContent = error.message || "EDF 解析失败。";
    showToast("EDF 解析失败，请检查文件格式");
    throw error;
  }
}

async function loadEegFromUrls(edfUrl, eventsUrl = "", sourceMode = "formal", sourceName = "") {
  qs("#eegEmpty")?.classList.remove("ready");
  qs("#eegEmpty").textContent = "正在加载 EEG 数据。";
  const edfResponse = await fetch(edfUrl);
  if (!edfResponse.ok) throw new Error("EDF 文件加载失败。");
  const eventsResponse = eventsUrl ? await fetch(eventsUrl) : null;
  const eventsText = eventsResponse?.ok ? await eventsResponse.text() : "";
  await loadEegFromBuffer(await edfResponse.arrayBuffer(), sourceName || edfUrl.split("/").pop(), eventsText, sourceMode);
}

async function loadTeachingEeg() {
  startLearningMode();
}

function renderTemplates() {
  const target = qs("#templateList");
  if (!target) return;
  target.innerHTML = availableTemplates().map((item) => `
    <button class="template ${item.name === state.activeTemplate ? "active" : ""}" data-template="${item.name}">
      <i data-lucide="${item.icon}"></i>
      <span><strong>${item.name}</strong><span>${item.desc}</span></span>
      <i data-lucide="chevron-right"></i>
    </button>
  `).join("");
  qsa(".template").forEach((button) => button.addEventListener("click", () => {
    state.activeTemplate = button.dataset.template;
    setSegmentMode(workflowRouteFor().segmentMode);
    renderTemplates();
    renderTemplateStatus();
    renderPreview();
    renderMethodParams();
    syncWorkflowRouteUi();
    if (window.lucide) lucide.createIcons();
    showToast(`已选择：${state.activeTemplate}`);
  }));
  renderTemplateStatus();
  syncWorkflowRouteUi();
}

function setSegmentMode(mode) {
  if (!mode) return;
  state.segmentMode = mode;
  qsa("#segmentMode button").forEach((item) => item.classList.toggle("active", item.dataset.segment === mode));
  qs("#timeSegmentForm")?.classList.toggle("active", mode === "time");
  qs("#eventSegmentForm")?.classList.toggle("active", mode === "event");
  updateSegmentSummary();
}

function bindV0WorkflowGuide() {
  qsa("[data-workflow-target], [data-workflow-template]").forEach((button) => {
    button.addEventListener("click", () => {
      const template = button.dataset.workflowTemplate;
      const targetSelector = button.dataset.workflowTarget || "#analysis";
      if (template) {
        state.activeTemplate = template;
      }
      setAnalysisPage(analysisPageForTarget(targetSelector), { scroll: false });
      setSegmentMode(button.dataset.workflowSegment || workflowRouteFor().segmentMode);
      renderTemplates();
      renderTemplateStatus();
      renderPreview();
      renderMethodParams();
      syncWorkflowRouteUi();
      qsa(".workflow-action-row button").forEach((item) => item.classList.toggle("active", item === button));
      const target = qs(targetSelector);
      target?.scrollIntoView({ behavior: "smooth", block: "start" });
      if (template) showToast(`已选择：${template}`);
    });
  });
}

function bindAnalysisSubnav() {
  qsa("button[data-analysis-page]").forEach((button) => {
    if (button.dataset.analysisSubnavBound) return;
    button.dataset.analysisSubnavBound = "true";
    button.addEventListener("click", () => setAnalysisPage(button.dataset.analysisPage, { scroll: true }));
  });
}

function updateSegmentSummary() {
  const target = qs("#segmentSummary");
  if (!target) return;
  if (state.activeTemplate === "静息态功率谱") {
    const start = Number(qs("#segmentStart")?.value || 0);
    const end = Number(qs("#segmentEnd")?.value || 0);
    const welch = qs("#psdWelchWindow")?.value || "4 秒";
    const bands = qs("#psdBands")?.value || "Delta/Theta/Alpha/Beta";
    target.textContent = `PSD 将提取 ${start.toFixed(1)}s - ${end.toFixed(1)}s 连续片段，Welch 窗长 ${welch}，输出频段：${bands}。`;
    return;
  }
  const type = qs("#eventType")?.value || "target";
  if (!type) {
    target.textContent = "未读到事件标签。请先打开含 annotations/events 的 EEG，或上传事件表；当前不能配置事件锁定 ERP。";
    return;
  }
  const pre = Number(qs("#eventPre")?.value || 0);
  const post = Number(qs("#eventPost")?.value || 0);
  if (state.activeTemplate === "时频分析") {
    const range = qs("#tfrFreqRange")?.value || "4-40 Hz";
    const baseline = qs("#tfrBaseline")?.value || "-0.3 到 0 秒";
    target.textContent = `TFR 将围绕事件 ${type} 计算 ${range} 时频能量，基线：${baseline}。`;
    return;
  }
  const baseline = qs("#erpBaseline")?.value || "-0.2 到 0 秒";
  target.textContent = `ERP/RRP 将围绕事件 ${type} 提取 Epoch，窗口为事件前 ${pre.toFixed(1)}s 到事件后 ${post.toFixed(1)}s，Baseline：${baseline}。`;
}

function updateCosts() {
  const subjects = Math.max(1, Number(qs("#subjectsInput")?.value || 1));
  const hours = Math.max(0.1, Number(qs("#hoursInput")?.value || 0.1));
  const total = subjects * hours;
  const project = activeProject();
  const learning = isLearningProject(project);
  if (qs("#totalHours")) qs("#totalHours").textContent = `${total.toFixed(1)} h`;
  if (qs("#analysisCost")) qs("#analysisCost").textContent = learning ? "学习模式免扣费" : money(total);
  if (qs("#totalCost")) qs("#totalCost").textContent = learning ? money(0) : money(total);
  const createTaskLabel = qs("#createTaskBtn span");
  if (createTaskLabel) createTaskLabel.textContent = learning ? "免扣费运行体验任务" : "冻结费用并建任务";
  renderSubmitReadiness();
  return learning ? 0 : total;
}

function updateBalance() {
  if (qs("#balanceMain")) qs("#balanceMain").textContent = state.balance.toFixed(2);
  if (state.role !== "admin") syncSidebarAccount();
}

function enterAdmin() {
  rememberSession("admin", false);
  loginAs("admin");
  showToast("已进入管理员后台");
}

function updateRecommendation() {
  const key = qs("#methodSignal")?.value || "p300";
  const target = qs("#methodRecommendation");
  if (!target) return;
  if (key === "auto" || key.startsWith("event:") || key === "continuous") {
    const stateInfo = eventAnalysisState();
    const selected = key.startsWith("event:") ? key.slice("event:".length) : "";
    target.classList.add("event-fact");
    target.classList.toggle("warning", stateInfo.mode === "none");
    target.innerHTML = `
      <strong>${escapeHtml(selected ? `按事件 ${selected} 分析` : stateInfo.title)}</strong>
      <span>${escapeHtml(stateInfo.message)}</span>
      <b>${escapeHtml(stateInfo.params)}</b>
      <small>事件标签来自当前 EEG 预览读到的 annotations/events；标签语义仍需实验日志确认。</small>
    `;
    showToast(stateInfo.mode === "none" ? "未读到事件标签" : "已按 EEG 事件标签生成建议");
    return;
  }
  const item = recommendations[key] || recommendations.p300;
  target.classList.remove("event-fact", "warning");
  target.innerHTML = `
    <strong>${item.title}</strong>
    <span>${item.body}</span>
    <b>${item.params}</b>
    <small>确认后可提交任务，结果会进入“结果交付”。</small>
  `;
  showToast(`已推荐：${item.title}`);
}

async function loadPlatformConfig() {
  try {
    const data = await apiRequest("/api/platform/config");
    state.platform = data;
    renderAdminMethods();
  } catch (error) {
    state.platform = {
      sms: { provider: "不可用", productionReady: false },
      payment: { provider: "不可用", productionReady: false },
    };
    recordOperation("系统", "平台通道检查失败", "短信 / 支付", error.message || "API 不可用");
  }
}

async function loadLocalSampleConfig() {
  const button = qs("#loadLocalBdfBtn");
  if (!button) return;
  try {
    const meta = await apiRequest(LOCAL_BDF_SAMPLE_META);
    state.localSample = meta;
    button.hidden = false;
    button.querySelector("span").textContent = `加载本地 BDF 测试数据（${meta.sizeLabel}）`;
  } catch {
    button.hidden = true;
  }
}

function boot() {
  applyProductModeUi();
  renderTasks();
  renderTemplates();
  renderPreview();
  renderProjects();
  renderCustomerChecks();
  renderAllAdmin();
  renderTeachingDataset();
  renderPreprocessPipeline();
  setSegmentMode(workflowRouteFor().segmentMode);
  updateSegmentSummary();
  updateCosts();
  updateBalance();
  renderAccountSettings();
  enhanceControlLabels();
  loadPlatformConfig();
  loadLocalSampleConfig();
  applyProductModeUi();

  qsa("[data-view], [data-view-jump]").forEach((button) => button.addEventListener("click", () => setView(button.dataset.view || button.dataset.viewJump)));
  qsa("[data-project-action]").forEach((button) => button.addEventListener("click", () => handleProjectAction(button.dataset.projectAction)));
  qsa("[data-login-tab]").forEach((button) => button.addEventListener("click", () => switchLoginTab(button.dataset.loginTab)));
  qs("#adminEntryBtn")?.addEventListener("click", enterAdmin);
  qs("#customerLoginForm")?.addEventListener("submit", (event) => {
    event.preventDefault();
    loginCustomer(qs("#customerEmail")?.value.trim() || "", qs("#customerPassword")?.value || "", Boolean(qs("#rememberCustomer")?.checked));
  });
  qs("#customerRegisterForm")?.addEventListener("submit", (event) => {
    event.preventDefault();
    registerCustomer({
      name: qs("#registerName")?.value || "",
      phone: qs("#registerPhone")?.value || "",
      smsCode: qs("#registerSmsCode")?.value || "",
      email: qs("#registerEmail")?.value || "",
      org: qs("#registerOrg")?.value || "",
      password: qs("#registerPassword")?.value || "",
      passwordConfirm: qs("#registerPasswordConfirm")?.value || "",
    });
  });
  qs("#sendSmsCodeBtn")?.addEventListener("click", sendRegisterSmsCode);
  qs("#logoutBtn")?.addEventListener("click", logout);

  ["#subjectsInput", "#hoursInput"].forEach((selector) => qs(selector)?.addEventListener("input", updateCosts));
  ["#segmentStart", "#segmentEnd", "#segmentStride", "#eventType", "#eventPre", "#eventPost"].forEach((selector) => {
    qs(selector)?.addEventListener("input", updateSegmentSummary);
    qs(selector)?.addEventListener("change", updateSegmentSummary);
  });

  qsa("#segmentMode button").forEach((button) => button.addEventListener("click", () => setSegmentMode(button.dataset.segment)));

  qs("#fileInput")?.addEventListener("change", (event) => {
    const files = [...event.target.files];
    const count = files.length;
    qs("#fileLabel").textContent = count ? `已选择 ${count} 个文件` : "选择或拖入 EEG 数据";
    if (count) {
      addUploadedFiles(files);
      showToast("文件已加入当前项目数据列表");
    }
  });
  qs("#loadLocalBdfBtn")?.addEventListener("click", loadLocalBdfSample);

  qs("#createTaskBtn")?.addEventListener("click", () => {
    const cost = updateCosts();
    const project = activeProject();
    const learning = isLearningProject(project);
    const localBdf = Boolean(project?.localSample);
    if (!project) {
      showToast("请先新建项目、上传 EEG 数据，或进入学习模式试跑流程");
      setView("analysis");
      return;
    }
    const files = ensureProjectFiles(project);
    if (!files.length) {
      showToast("请先上传 EEG 数据文件");
      return;
    }
    if (!learning && !eegState.data) {
      showToast("请先预览原始 EEG，核对信号和事件标签后再提交任务");
      setView("analysis");
      return;
    }
    if (!learning && state.balance < cost) {
      showToast("余额不足，请先充值");
      setView("billing");
      return;
    }
    if (!learning) state.balance -= cost;
    if (project) {
      project.stage = "已提交分析";
      project.queue = learning ? "学习任务运行中" : "队列第 1 位";
      project.result = { status: "生成中", badge: `${project.size} / 分析中`, note: learning ? "学习模式使用预置数据运行正式流程，本次免扣费。" : "任务完成后生成正式交付件。" };
      project.updated = today();
    }
    const taskName = `${learning ? "learning-task" : "eeg-task"}-${String(Date.now()).slice(-5)}`;
    state.tasks.unshift({
      ...domainFactory.createAnalysisTask({
        id: taskName,
        projectId: project.id,
        workflowTemplate: state.activeTemplate,
        status: learning || localBdf ? "completed" : "balance_frozen",
        estimatedCost: cost,
        frozenAmount: learning || localBdf ? 0 : cost,
        finalCost: learning ? 0 : localBdf ? cost : 0,
        inputFileIds: files.map((file) => file.id),
      }),
      name: taskName,
      detail: `${learning ? "学习模式免扣费；" : ""}${state.activeTemplate}；${qs("#segmentSummary")?.textContent || ""}`,
      progress: learning ? 100 : localBdf ? 100 : 12,
    });
    linkProjectIds(project, "taskIds", [taskName]);
    const task = appendAdminTaskFromCustomer(cost);
    if (learning) {
      task.currentNodeId = "delivery_review";
      task.doneNodeIds = ["intake", "profile_check", "cost_freeze", "upload_store", "queue_assign", "format_parse", "preprocess", "quality_check", "method_route", "mne_worker", "stats", "figures", "report_package"];
      task.history.push(
        { time: nowTime(), nodeId: "mne_worker", status: "完成", note: "学习模式：预置数据完成示例分析" },
        { time: nowTime(), nodeId: "delivery_review", status: "当前", note: "学习交付件等待客户预览" },
      );
      completeProjectForLocalDemo(project, taskName, 0);
    } else if (localBdf) {
      state.orders.unshift({
        ...domainFactory.createLedgerEntry({
          id: `QL-${Date.now()}-TASK`,
          customer: currentCustomerName(),
          type: "analysis_charge",
          amount: cost,
          status: "charged",
          source: taskName,
          projectId: project.id,
          taskId: task.id,
          handler: "system",
        }),
        id: `QL-${Date.now()}-TASK`,
        customer: currentCustomerName(),
        type: "任务扣费",
        amount: cost,
        status: "已扣费",
        source: taskName,
        projectId: project.id,
        taskId: task.id,
        createdAt: new Date().toLocaleString("zh-CN", { hour12: false }),
        handler: "系统",
      });
      task.currentNodeId = "delivery_review";
      task.doneNodeIds = ["intake", "profile_check", "cost_freeze", "upload_store", "queue_assign", "format_parse", "preprocess", "quality_check", "method_route", "mne_worker", "stats", "figures", "report_package"];
      task.history.push(
        { time: nowTime(), nodeId: "format_parse", status: "完成", note: "BDF 头信息、64 个 EEG 通道与 annotations 已复核" },
        { time: nowTime(), nodeId: "mne_worker", status: "完成", note: "本地 MNE 已完成 annotation-locked ERP / GFP / 热图输出" },
        { time: nowTime(), nodeId: "delivery_review", status: "当前", note: "正式交付件已写入客户结果页，等待预览确认" },
      );
      completeProjectForLocalDemo(project, taskName, cost);
    } else {
      state.orders.unshift({
        ...domainFactory.createLedgerEntry({
          id: `QL-${Date.now()}-TASK`,
          customer: currentCustomerName(),
          type: "analysis_charge",
          amount: cost,
          status: "frozen",
          source: taskName,
          projectId: project.id,
          taskId: task.id,
          handler: "system",
        }),
        id: `QL-${Date.now()}-TASK`,
        customer: currentCustomerName(),
        type: "任务扣费",
        amount: cost,
        status: "已冻结",
        source: taskName,
        projectId: project.id,
        taskId: task.id,
        createdAt: new Date().toLocaleString("zh-CN", { hour12: false }),
        handler: "系统",
      });
    }
    updateBalance();
    renderTasks();
    renderProjects();
    renderAccountSettings();
    renderAllAdmin();
    recordOperation("客户", learning ? "提交学习体验任务" : "提交分析任务", project?.name || taskName, `${state.activeTemplate} / ${money(cost)}`);
    showToast(learning ? "学习任务已完成，可预览交付件" : localBdf ? "本地 BDF 正式 ERP 已完成，可预览交付件" : `任务已提交，冻结费用 ${money(cost)}`);
    setView(learning || localBdf ? "publication" : "dashboard");
  });

  qs("#eegPrevBtn")?.addEventListener("click", () => {
    eegState.start -= eegState.windowSec * 0.5;
    renderEeg();
  });
  qs("#eegNextBtn")?.addEventListener("click", () => {
    eegState.start += eegState.windowSec * 0.5;
    renderEeg();
  });
  qs("#eegZoomInBtn")?.addEventListener("click", () => {
    eegState.windowSec = Math.max(2, Math.round(eegState.windowSec * 0.7));
    renderEeg();
  });
  qs("#eegZoomOutBtn")?.addEventListener("click", () => {
    eegState.windowSec = Math.min(30, Math.round(eegState.windowSec * 1.4));
    renderEeg();
  });
  qs("#eegResetBtn")?.addEventListener("click", () => {
    eegState.start = 0;
    eegState.windowSec = 10;
    eegState.gain = 2;
    eegState.filter = {
      enabled: true,
      highpassHz: 0.5,
      lowpassHz: 40,
      notchEnabled: false,
      notchHz: 50,
      notchQ: 30,
    };
    eegState.visibleChannels = Math.min(8, eegState.data?.signals.length || 8);
    renderEeg();
  });
  qs("#eegStartInput")?.addEventListener("change", () => {
    eegState.start = parseNumber(qs("#eegStartInput")?.value, 0);
    renderEeg();
  });
  qs("#eegWindowInput")?.addEventListener("input", () => {
    eegState.windowSec = parseNumber(qs("#eegWindowInput")?.value, 10);
    renderEeg();
  });
  qs("#eegGainInput")?.addEventListener("input", () => {
    eegState.gain = parseNumber(qs("#eegGainInput")?.value, 2);
    renderEeg();
  });
  qs("#eegFilterEnable")?.addEventListener("change", () => {
    eegState.filter.enabled = Boolean(qs("#eegFilterEnable")?.checked);
    renderEeg();
  });
  qs("#eegHighpassInput")?.addEventListener("change", () => {
    eegState.filter.highpassHz = parseNumber(qs("#eegHighpassInput")?.value, 0.5);
    renderEeg();
  });
  qs("#eegLowpassInput")?.addEventListener("change", () => {
    eegState.filter.lowpassHz = parseNumber(qs("#eegLowpassInput")?.value, 40);
    renderEeg();
  });
  qs("#eegNotchEnable")?.addEventListener("change", () => {
    eegState.filter.notchEnabled = Boolean(qs("#eegNotchEnable")?.checked);
    renderEeg();
  });
  qs("#eegNotchInput")?.addEventListener("change", () => {
    eegState.filter.notchHz = parseNumber(qs("#eegNotchInput")?.value, 50);
    renderEeg();
  });
  qs("#eegChannelInput")?.addEventListener("input", () => {
    eegState.visibleChannels = parseNumber(qs("#eegChannelInput")?.value, 8);
    renderEeg();
  });

  const eegCanvas = qs("#eegCanvas");
  eegCanvas?.addEventListener("wheel", (event) => {
    if (!eegState.data) return;
    event.preventDefault();
    const before = eegState.windowSec;
    eegState.windowSec = Math.max(2, Math.min(30, Math.round(eegState.windowSec * (event.deltaY < 0 ? 0.8 : 1.25))));
    const rect = eegCanvas.getBoundingClientRect();
    const ratio = (event.clientX - rect.left - 78) / Math.max(1, rect.width - 96);
    eegState.start += (before - eegState.windowSec) * Math.max(0, Math.min(1, ratio));
    renderEeg();
  }, { passive: false });
  eegCanvas?.addEventListener("pointerdown", (event) => {
    if (!eegState.data) return;
    eegState.drag = { x: event.clientX, start: eegState.start };
    eegCanvas.classList.add("dragging");
  });
  window.addEventListener("pointermove", (event) => {
    if (!eegState.drag || !eegState.data) return;
    const rect = eegCanvas.getBoundingClientRect();
    const secondsPerPx = eegState.windowSec / Math.max(1, rect.width - 96);
    eegState.start = eegState.drag.start - (event.clientX - eegState.drag.x) * secondsPerPx;
    renderEeg();
  });
  window.addEventListener("pointerup", () => {
    eegState.drag = null;
    eegCanvas?.classList.remove("dragging");
  });

  qs("#recommendBtn")?.addEventListener("click", updateRecommendation);
  qs("#runPreprocessBtn")?.addEventListener("click", runPreprocess);
  qs("#resetPreprocessBtn")?.addEventListener("click", resetPreprocess);
  qs("#markCurrentSegmentBtn")?.addEventListener("click", markCurrentSegmentBad);
  qs("#preReferenceSelect")?.addEventListener("change", syncPreprocessReferenceOptions);
  qs("#sidebarAccountBtn")?.addEventListener("click", () => setView("billing"));
  bindHelpButtons();
  bindAnalysisSubnav();
  bindV0WorkflowGuide();
  qs("#methodSignal")?.addEventListener("change", () => {
    const target = qs("#methodRecommendation");
    if (target) target.innerHTML = "";
  });

  bindFileActionButtons();

  qs("#loadTeachingEegBtn")?.addEventListener("click", () => {
    loadTeachingEeg().catch((error) => showToast(error.message || "教学数据加载失败"));
  });
  qs("#sidebarTeachingBtn")?.addEventListener("click", () => {
    if (state.teachingModeActive) {
      exitLearningMode();
      return;
    }
    loadTeachingEeg().catch((error) => showToast(error.message || "教学数据加载失败"));
  });
  qs("#loadTeachingFromProjectBtn")?.addEventListener("click", () => {
    loadTeachingEeg().catch((error) => showToast(error.message || "教学数据加载失败"));
  });
  qs("#deliveryPreviewClose")?.addEventListener("click", closeDeliveryPreview);
  qs("#deliveryPreviewCancel")?.addEventListener("click", closeDeliveryPreview);
  qs("#deliveryDownloadBtn")?.addEventListener("click", () => {
    const item = state.activeDeliveryPreview;
    if (!item) showToast("请先选择交付件");
  });
  bindDeliveryPreviewButtons();
  qsa("[data-admin-system-action]").forEach((button) => button.addEventListener("click", () => handleAdminSystemAction(button.dataset.adminSystemAction)));

  qs("#publishBtn")?.addEventListener("click", () => {
    const status = `当前输出：${qs("#dpiSelect")?.value}、${qs("#paletteSelect")?.value}、${qs("#fontSelect")?.value}，已绑定统计表、图注、方法说明和复现记录。`;
    if (qs("#publicationStatus")) qs("#publicationStatus").textContent = status;
    recordOperation("客户", "应用结果导出参数", activeProject()?.name || "当前项目", status);
    showToast("图像后处理参数已应用到导出包");
  });

  qsa("[data-recharge]").forEach((button) => button.addEventListener("click", () => {
    state.rechargeAmount = Number(button.dataset.recharge);
    qsa("[data-recharge]").forEach((item) => item.classList.toggle("active", item === button));
  }));

  qsa("[data-pay-method]").forEach((button) => button.addEventListener("click", () => {
    qsa("[data-pay-method]").forEach((item) => item.classList.toggle("active", item === button));
    state.selectedPayMethod = button.dataset.payMethod;
    showToast(`${button.dataset.payMethod} 已选中`);
  }));

  qs("#rechargeBtn")?.addEventListener("click", createAlipayRecharge);
  qs("#mockAlipayNotifyBtn")?.addEventListener("click", mockAlipayNotify);

  qs("#saveProfileBtn")?.addEventListener("click", saveProfileFromForm);
  qs("#invoiceBtn")?.addEventListener("click", submitInvoice);

  if (window.lucide) lucide.createIcons();
  restoreSession();
  applyProductModeUi();
}

boot();
