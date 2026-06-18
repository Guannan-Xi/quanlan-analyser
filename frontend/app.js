const qs = (selector) => document.querySelector(selector);
const qsa = (selector) => [...document.querySelectorAll(selector)];
const money = (value) => `￥${Number(value).toFixed(2)}`;
const AUTH_KEY = "qlanalyser_auth_session";
const CUSTOMER_KEY = "qlanalyser_customer_profile";
const ENTRY_PAGE = "expert-entry-demo.html";
const DEFAULT_API_BASE = ["localhost", "127.0.0.1"].includes(window.location.hostname)
  ? "http://127.0.0.1:8000/api"
  : "/api";

const demoCustomer = {
  name: "",
  email: "",
  org: "",
  password: "",
  registeredAt: "",
};

const demoAdmin = {
  email: "ops@quanlan.cn",
  password: "",
};

const state = {
  balance: 0,
  rechargeAmount: 1000,
  activeTemplate: "ERP 事件相关电位",
  segmentMode: "time",
  role: null,
  tasks: [],
  apiBase: new URLSearchParams(window.location.search).get("api") || DEFAULT_API_BASE,
  real: {
    project: null,
    eegFile: null,
    tasks: {},
    report: null,
  },
};

const eegState = {
  data: null,
  events: [],
  sourceName: "",
  autoloaded: false,
  uploaded: false,
  start: 0,
  windowSec: 10,
  gain: 2,
  visibleChannels: 8,
  drag: null,
};

const templates = [
  { name: "数据浏览与分段", desc: "MNE Raw.plot，连续片段、事件叠加和坏段标注", icon: "scan-line", image: "./assets/analysis-raw-segment.png" },
  { name: "静息态功率谱", desc: "MNE Spectrum.plot，Welch PSD，alpha peak 与频段功率", icon: "bar-chart-3", image: "./assets/analysis-psd.png" },
  { name: "ERP 事件相关电位", desc: "MNE Evoked，target-standard，对应 EEGLAB ERP 工作流", icon: "waves", image: "./assets/analysis-erp.png" },
  { name: "ICA 预处理", desc: "MNE ICA components，对应 EEGLAB runica / ICLabel 流程", icon: "sliders-horizontal", image: "./assets/analysis-ica.png" },
  { name: "时频分析", desc: "MNE TFR，Morlet 小波，对应 EEGLAB ERSP / ITC", icon: "audio-waveform", image: "./assets/analysis-timefreq.png" },
  { name: "头皮地形图", desc: "MNE topomap，对应 EEGLAB topoplot", icon: "scan-eye", image: "./assets/analysis-source.png" },
  { name: "机器学习分类", desc: "MNE Epoch 特征 + sklearn 分类与交叉验证", icon: "git-branch", image: "./assets/analysis-ml.png" },
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
  dashboard: "工作台总览",
  journey: "流程引导",
  analysis: "上传与预览",
  workflow: "分析分支",
  paradigms: "范式参考",
  statistics: "统计与结果",
  publication: "图表下载",
  upload: "数据导入",
  storage: "数据资产",
  billing: "计费",
  invoice: "开票",
  adminDashboard: "后台总览",
  adminOperations: "任务运营",
  adminFinance: "订单开票管理",
  adminSystem: "系统状态",
};

const recommendations = {
  p300: {
    title: "推荐：ERP / P300 分析",
    body: "因为事件标签包含 target 和 standard，研究问题是事件锁定反应差异。系统会计算 target-standard 波形，提取 280-420 ms 的 P300 平均振幅。",
    params: "Epoch -0.2~0.8 s；baseline -0.2~0 s；通道 Pz/P3/P4；统计为配对 t 检验 + FDR + cluster permutation。",
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

const journeyDetails = [
  {
    title: "第 1 步：先建项目",
    body: "给这次分析取一个名字，例如客户 Oddball ERP。你也可以直接使用系统示例名称。",
    action: "点“开始分析”，确认项目名和数据数量。",
    view: "analysis",
  },
  {
    title: "第 2 步：上传脑电",
    body: "把 EDF、SET 或 FIF 文件拖入上传框。系统会自动读取通道、采样率和事件标签。",
    action: "新手建议保留自动识别结果，先不要改高级设置。",
    view: "upload",
  },
  {
    title: "第 3 步：看懂费用",
    body: "按每小时脑电数据 1 元，5 h 扣 5 元。余额从 1000 元变为 995 元，扣费记录可用于开票。",
    action: "确认费用后点击“提交分析”。扣费前会先显示预计金额。",
    view: "billing",
  },
  {
    title: "第 4 步：不会选方法",
    body: "用户只知道范式是 Oddball，不知道 ERP、时频还是机器学习。平台检查事件标签 target/standard，推荐 ERP/P300。",
    action: "选择“target / standard 或 Oddball”，点击推荐分析方法。",
    view: "journey",
  },
  {
    title: "第 5 步：使用默认参数",
    body: "系统给出 epoch -0.2~0.8 s、baseline -0.2~0 s、P300 280-420 ms、Pz/P3/P4、target-standard。",
    action: "先使用默认参数，后续再让专家调整高级参数。",
    view: "analysis",
  },
  {
    title: "第 6 步：查看质控",
    body: "平台输出坏道、坏段、眨眼 ICA、试次数、滤波和参考记录。QC 不合格被试会被标记待复核。",
    action: "看到红色提示时，先下载质控报告，不要急着下结论。",
    view: "statistics",
  },
  {
    title: "第 7 步：生成图和表",
    body: "先导出每位被试的 P300 指标，再做配对 t 检验、FDR 和 cluster permutation，并生成 300 dpi 主图。",
    action: "进入“投稿图”下载主图、统计表和方法说明。",
    view: "publication",
  },
  {
    title: "第 8 步：提交或开票",
    body: "下载结果包后可发给导师、合作者或编辑。费用记录可在线申请发票。",
    action: "图、表、方法和复现记录都在下载包里。",
    view: "publication",
  },
];

const modalContent = {
  knowledge: {
    title: "知识库",
    body: `
      <p>这里会解释脑电分析中的常见概念：事件锁定分析、连续片段选择、每位被试指标、统计校正、图像导出和复现记录。</p>
      <div class="modal-actions">
        <button class="ghost-btn" data-modal-view="workflow"><i data-lucide="route"></i><span>打开新手向导</span></button>
        <button class="ghost-btn" data-modal-view="journey"><i data-lucide="clipboard-check"></i><span>查看流程</span></button>
      </div>
    `,
  },
  audit: {
    title: "项目记录",
    body: `
      <div class="audit-list">
        <span>09:00 注册客户 399467826@qq.com 并创建 Oddball ERP 项目</span>
        <span>09:03 充值 1000 元，本次分析按 5 小时计费</span>
        <span>09:05 生成 5 份 Oddball EEG 与事件表，哈希校验通过</span>
        <span>09:08 推荐 ERP/P300 方法，并记录分析参数</span>
        <span>09:16 导出结果包、统计表、方法说明和图注</span>
        <span>09:20 结果整理完成，等待确认后通知客户</span>
      </div>
    `,
  },
  uploadHelp: {
    title: "上传遇到问题怎么办",
    body: `
      <div class="audit-list">
        <span>文件太大：保持页面打开，平台会自动分段上传。</span>
        <span>网络中断：重新进入项目后继续上传，不需要从头开始。</span>
        <span>不知道事件表：先上传原始脑电，系统会尝试自动识别事件标签。</span>
        <span>第一次使用：可以先用示例数据跑完整流程，再上传真实数据。</span>
      </div>
    `,
  },
};

function setRealStatus(message, kind = "info") {
  const target = qs("#realRuntimeStatus");
  if (!target) return;
  target.classList.remove("status-error", "status-ok");
  if (kind === "error") target.classList.add("status-error");
  if (kind === "ok") target.classList.add("status-ok");
  target.textContent = message;
}

function addReportDownload(report) {
  const target = qs("#realReportDownloads");
  if (!target || !report?.id) return;
  const href = `${state.apiBase}/reports/${report.id}/package`;
  target.innerHTML = `<a href="${href}" target="_blank" rel="noreferrer"><i data-lucide="download"></i><span>报告包 ${report.id}</span></a>`;
  if (window.lucide) lucide.createIcons();
}

async function apiJson(path, options = {}) {
  const response = await fetch(`${state.apiBase}${path}`, {
    headers: { Accept: "application/json", ...(options.headers || {}) },
    ...options,
  });
  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    const detail = typeof data === "string" ? data : data?.detail || JSON.stringify(data);
    throw new Error(detail || `Request failed: ${response.status}`);
  }
  return data;
}

async function ensureRealProject() {
  if (state.real.project) return state.real.project;
  const projectName = qs("#realProjectName")?.value.trim() || "Pilot 真实分析项目";
  const project = await apiJson("/projects", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: projectName,
      description: "Local real-flow pilot project",
      research_type: "resting_state",
      owner_id: "local-user",
    }),
  });
  state.real.project = project;
  setRealStatus(`项目已创建：${project.id}`, "ok");
  return project;
}

async function uploadRealEeg() {
  const file = qs("#real-eeg-file")?.files?.[0];
  if (!file) throw new Error("请选择一个 EEG 文件后再上传");
  const project = await ensureRealProject();
  const form = new FormData();
  form.append("file", file);
  const uploaded = await apiJson(`/eeg/upload?project_id=${encodeURIComponent(project.id)}`, {
    method: "POST",
    body: form,
  });
  state.real.eegFile = uploaded;
  setRealStatus(`文件已上传：${uploaded.id}`, "ok");
  return uploaded;
}

async function runRealTask(moduleName, workflowId) {
  const project = await ensureRealProject();
  const eegFile = state.real.eegFile || await uploadRealEeg();
  setRealStatus(`正在运行 ${moduleName.toUpperCase()}...`, "info");
  const task = await apiJson("/tasks", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      project_id: project.id,
      module_name: moduleName,
      workflow_id: workflowId,
      input_file_id: eegFile.id,
      parameters_json: {},
    }),
  });
  state.real.tasks[moduleName] = task;
  setRealStatus(`${moduleName.toUpperCase()} 已完成：${task.id} / ${task.status}`, "ok");
  return task;
}

async function createRealReport() {
  const task = state.real.tasks.erp || state.real.tasks.psd || state.real.tasks.qc;
  if (!task) throw new Error("请先运行至少一个分析任务");
  const project = await ensureRealProject();
  const title = qs("#realReportTitle")?.value.trim() || "Single-subject EEG report";
  const report = await apiJson("/reports", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: project.id, task_id: task.id, title }),
  });
  state.real.report = report;
  addReportDownload(report);
  setRealStatus(`报告已生成：${report.id}`, "ok");
  return report;
}

function showToast(message) {
  const toast = qs("#toast");
  if (!toast) return;
  toast.textContent = message;
  toast.classList.add("show");
  window.setTimeout(() => toast.classList.remove("show"), 2400);
}

function openModal(kind) {
  const config = modalContent[kind];
  const backdrop = qs("#modalBackdrop");
  if (!config || !backdrop) return;
  qs("#modalTitle").textContent = config.title;
  qs("#modalBody").innerHTML = config.body;
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

function setLoginMessage(message, type = "info") {
  const target = qs("#loginMessage");
  if (!target) return;
  target.textContent = message;
  target.classList.toggle("error", type === "error");
  target.classList.toggle("success", type === "success");
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
  const customer = getStoredCustomer();
  const safeText = (value, fallback = "-") => value || fallback;
  if (qs("#adminCustomerName")) qs("#adminCustomerName").textContent = safeText(customer.name);
  if (qs("#adminCustomerEmail")) qs("#adminCustomerEmail").textContent = safeText(customer.email);
  if (qs("#adminCustomerOrg")) qs("#adminCustomerOrg").textContent = safeText(customer.org);
  if (qs("#adminCustomerRegisteredAt")) qs("#adminCustomerRegisteredAt").textContent = safeText(customer.registeredAt);
}

function startDemoWorkspace(persist = true) {
  saveCustomer({
    ...demoCustomer,
    name: demoCustomer.name || "Pilot \u6f14\u793a\u7528\u6237",
    email: demoCustomer.email || "demo@qlanalyser.online",
    org: demoCustomer.org || "QLanalyser Online Pilot",
    registeredAt: demoCustomer.registeredAt || "Pilot demo",
  });
  rememberSession("customer", persist);
  loginAs("customer", getStoredCustomer());
  setLoginMessage("\u5df2\u8fdb\u5165 QLanalyser Online Pilot \u6f14\u793a\u5de5\u4f5c\u53f0\u3002", "success");
  showToast("\u5df2\u8fdb\u5165\u6f14\u793a\u9879\u76ee");
}

function loginCustomer(email, password, remember) {
  const customer = getStoredCustomer();
  const matchedDemo = email === demoCustomer.email && password === demoCustomer.password;
  const matchedRegistered = email === customer.email && password === customer.password;
  if (!email || !password) {
    setLoginMessage("请输入邮箱 / 手机号和密码；还没有账户时请先注册。", "error");
    return;
  }
  if (matchedDemo) {
    startDemoWorkspace(remember);
    return;
  }
  if (!matchedRegistered) {
    setLoginMessage("邮箱或密码不正确，请检查后重试；还没有账户时请先注册。", "error");
    return;
  }
  rememberSession("customer", remember);
  loginAs("customer", customer);
  setLoginMessage("");
}

function registerCustomer({ name, email, phone, org, password, code, mode }) {
  if (!name.trim()) {
    setLoginMessage("请填写姓名，后续项目和报告会使用它。", "error");
    return;
  }
  const normalizedMode = mode === "phone" ? "phone" : "email";
  if (normalizedMode === "email") {
    if (!validateEmail(email)) {
      setLoginMessage("请填写有效邮箱，正式账户会通过邮箱验证码确认。", "error");
      return;
    }
    if (!code.trim()) {
      setLoginMessage("请输入邮箱验证码。本地版会模拟发送验证码。", "error");
      return;
    }
    if (password.length < 8) {
      setLoginMessage("正式账户密码至少 8 位。", "error");
      return;
    }
  } else {
    if (!/^1\d{10}$/.test(phone.trim())) {
      setLoginMessage("请输入 11 位手机号，用于沙盒验证码体验。", "error");
      return;
    }
    if (!code.trim()) {
      setLoginMessage("请输入手机沙盒验证码。", "error");
      return;
    }
  }
  const account = normalizedMode === "email" ? email.trim() : phone.trim();
  const profile = {
    name: name.trim(),
    email: normalizedMode === "email" ? account : `${account}@sandbox.quanlan.local`,
    phone: normalizedMode === "phone" ? account : "",
    org: org.trim() || "未填写单位",
    password: normalizedMode === "email" ? password : "",
    accountMode: normalizedMode,
    registeredAt: new Date().toLocaleString("zh-CN", { hour12: false }),
  };
  saveCustomer(profile);
  rememberSession("customer", true);
  renderAdminCustomerProfile();
  loginAs("customer", profile);
  setLoginMessage("注册成功，已进入 QLanalyser 工作台。", "success");
  showToast(normalizedMode === "email" ? "邮箱验证码注册成功" : "手机沙盒账户已创建");
}

function loginAdmin(email, password) {
  const wantsPilotAdmin = (!email && !password) || (email === demoAdmin.email && password === demoAdmin.password);
  if (!wantsPilotAdmin) {
    setLoginMessage("Pilot \u8bd5\u7528\u7248\u7ba1\u7406\u5458\u5165\u53e3\u5f85\u5b8c\u5584\uff1b\u5f53\u524d\u4ec5\u63d0\u4f9b\u672c\u5730\u6f14\u793a\u540e\u53f0\u3002", "error");
    return;
  }
  rememberSession("admin", true);
  loginAs("admin");
  setLoginMessage("\u5df2\u8fdb\u5165 Pilot \u8bd5\u7528\u7248\u7ba1\u7406\u5458\u6f14\u793a\u540e\u53f0\u3002", "success");
  showToast("Pilot \u7ba1\u7406\u5458\u6f14\u793a\u540e\u53f0\u5df2\u6253\u5f00");
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
  qsa("[data-role]").forEach((item) => {
    item.hidden = item.dataset.role !== role;
  });
  if (role === "admin") {
    qs("#roleLabel").textContent = "管理员后台";
    qs("#balanceSide").textContent = "运营";
    qs("#accountHint").textContent = "管理客户项目、任务、订单、开票和系统状态";
    qs("#topEyebrow").textContent = "后台管理 / 今日运营";
    qs("#tutorialBtn").hidden = true;
    renderAdminCustomerProfile();
    setView("adminDashboard");
  } else {
    const customer = profile || getStoredCustomer();
    qs("#roleLabel").textContent = customer.name || "客户账户";
    qs("#balanceSide").textContent = money(state.balance);
    qs("#accountHint").textContent = `${customer.org || "个人课题"} · ${customer.email || "未绑定邮箱"}`;
    qs("#topEyebrow").textContent = "项目：客户 Oddball ERP / 5 份 EEG";
    qs("#tutorialBtn").hidden = false;
    setView("journey");
  }
  if (window.lucide) lucide.createIcons();
}

function logout(clear = true) {
  if (clear) clearSession();
  qs("#appShell").hidden = true;
  qs("#loginScreen").hidden = false;
  qsa(".view").forEach((el) => el.classList.remove("active"));
  qsa(".nav-item").forEach((el) => el.classList.remove("active"));
  switchLoginTab("customerLogin");
  closeModal();
  if (clear && !window.location.pathname.endsWith(ENTRY_PAGE)) {
    history.replaceState(null, "", ENTRY_PAGE);
  }
  if (window.lucide) lucide.createIcons();
}

function setView(view) {
  const targetNav = qs(`[data-view="${view}"]`);
  const targetView = qs(`#${view}`);
  if (!targetView) {
    showToast("Pilot \u8bd5\u7528\u7248\u6682\u672a\u5f00\u653e\u8be5\u9875\u9762\u3002");
    return;
  }
  if (targetNav?.dataset.role && state.role && targetNav.dataset.role !== state.role) {
    showToast("\u5f53\u524d\u8d26\u6237\u65e0\u6743\u8bbf\u95ee\u8be5\u5165\u53e3\u3002");
    return;
  }
  qsa(".view").forEach((el) => el.classList.toggle("active", el.id === view));
  qsa(".nav-item").forEach((el) => el.classList.toggle("active", el.dataset.view === view));
  const title = qs("#viewTitle");
  if (title) title.textContent = titles[view] || titles.dashboard;
  if (view === "analysis") ensureEegLoaded();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function renderJourneyDetail(index = 0) {
  const target = qs("#journeyDetail");
  const detail = journeyDetails[index] || journeyDetails[0];
  if (!target) return;
  target.innerHTML = `
    <strong>${detail.title}</strong>
    <span>${detail.body}</span>
    <b>${detail.action}</b>
    <button class="ghost-btn" data-journey-view="${detail.view}"><i data-lucide="arrow-right"></i><span>进入相关页面</span></button>
  `;
  qsa(".journey-card").forEach((card) => card.classList.toggle("active", Number(card.dataset.journeyStep) === index));
  qs("[data-journey-view]")?.addEventListener("click", () => setView(detail.view));
  if (window.lucide) lucide.createIcons();
}

function renderTasks() {
  const target = qs("#taskList");
  if (!target) return;
  target.innerHTML = state.tasks.map((task) => `
    <div class="task">
      <div><strong>${task.name}</strong><span>${task.detail}</span></div>
      <div><span>${task.progress === 100 ? "已完成" : `${task.progress}%`}</span><div class="task-meter"><i style="width:${task.progress}%"></i></div></div>
    </div>
  `).join("");
}

function renderRealFlowSummary() {
  const target = qs("#realRuntimeStatus");
  if (!target) return;
  if (state.real.report) {
    setRealStatus(`报告已生成：${state.real.report.id}`, "ok");
  } else if (state.real.tasks.erp || state.real.tasks.psd || state.real.tasks.qc) {
    const last = state.real.tasks.erp || state.real.tasks.psd || state.real.tasks.qc;
    setRealStatus(`最近任务：${last.module_name || "analysis"} / ${last.id}`, "ok");
  } else if (state.real.eegFile) {
    setRealStatus(`文件已准备：${state.real.eegFile.id}`, "ok");
  } else if (state.real.project) {
    setRealStatus(`项目已创建：${state.real.project.id}`, "ok");
  } else {
    setRealStatus("等待创建项目。", "info");
  }
}


function activeTemplate() {
  return templates.find((item) => item.name === state.activeTemplate) || templates[0];
}

function renderPreview() {
  const item = activeTemplate();
  const caption = qs("#previewCaption");
  if (caption) caption.textContent = `当前模板：${item.name}。${item.desc}。下方原始波形用于核对通道质量、事件位置、振幅尺度和可分析片段。`;
  qsa(".preview-chip").forEach((button) => button.classList.toggle("active", button.dataset.template === item.name));
}

function textField(decoder, bytes, start, length) {
  return decoder.decode(bytes.slice(start, start + length)).trim();
}

function parseNumber(value, fallback = 0) {
  const parsed = Number(String(value).trim());
  return Number.isFinite(parsed) ? parsed : fallback;
}

function parseEdf(buffer) {
  const bytes = new Uint8Array(buffer);
  const view = new DataView(buffer);
  const decoder = new TextDecoder("ascii");
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
  const usableRecords = Math.max(1, records < 0 ? Math.floor((bytes.length - headerBytes) / (samplesPerRecordTotal * 2)) : records);
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
        const digital = dataOffset + 1 < bytes.length ? view.getInt16(dataOffset, true) : 0;
        if (channelTransforms[ch].isEeg) {
          signals[ch].values[base + i] = ((digital - digitalMin[ch]) * channelTransforms[ch].scale + physicalMin[ch]) * channelTransforms[ch].toMicrovolt;
        }
        dataOffset += 2;
      }
    }
  }

  const eegSignals = signals.filter((signal, index) => channelTransforms[index].isEeg);
  return { labels: eegSignals.map((signal) => signal.label), signals: eegSignals, sampleRate, duration, records: usableRecords, recordDuration, sourceUnit: "uV" };
}

function parseEvents(text) {
  const lines = text.trim().split(/\r?\n/).filter(Boolean);
  if (lines.length < 2) return [];
  const header = lines[0].split(/\t|,/).map((item) => item.trim());
  const onsetIndex = header.indexOf("onset");
  const durationIndex = header.indexOf("duration");
  const typeIndex = header.indexOf("trial_type");
  return lines.slice(1).map((line) => {
    const parts = line.split(/\t|,/);
    return {
      onset: parseNumber(parts[onsetIndex], 0),
      duration: durationIndex >= 0 ? parseNumber(parts[durationIndex], 0) : 0,
      type: typeIndex >= 0 ? parts[typeIndex] : "event",
    };
  }).filter((event) => Number.isFinite(event.onset));
}

function clampEegStart() {
  if (!eegState.data) {
    eegState.start = 0;
    return;
  }
  eegState.start = Math.max(0, Math.min(eegState.start, Math.max(0, eegState.data.duration - eegState.windowSec)));
  if (qs("#eegStartInput")) qs("#eegStartInput").value = eegState.start.toFixed(1);
}

function updateEegControls() {
  if (qs("#eegWindowLabel")) qs("#eegWindowLabel").textContent = `${eegState.windowSec} s`;
  if (qs("#eegGainLabel")) qs("#eegGainLabel").textContent = `${eegState.gain}x`;
  if (qs("#eegChannelLabel")) qs("#eegChannelLabel").textContent = String(eegState.visibleChannels);
  if (qs("#eegWindowInput")) qs("#eegWindowInput").value = String(eegState.windowSec);
  if (qs("#eegGainInput")) qs("#eegGainInput").value = String(eegState.gain);
  if (qs("#eegChannelInput")) qs("#eegChannelInput").value = String(eegState.visibleChannels);
  clampEegStart();
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
  const uvToPx = (spacing / 150) * eegState.gain;

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
    const step = Math.max(1, Math.floor((endSample - startSample) / plotW));
    ctx.strokeStyle = ch % 2 ? "#457b9d" : "#157a77";
    ctx.lineWidth = 1.3;
    ctx.beginPath();
    let moved = false;
    for (let i = startSample; i <= endSample; i += step) {
      const t = i / sr;
      const x = left + (t - eegState.start) * pxPerSecond;
      const y = y0 - Math.max(-spacing * 0.45, Math.min(spacing * 0.45, signal.values[i] * uvToPx));
      if (!moved) {
        ctx.moveTo(x, y);
        moved = true;
      } else {
        ctx.lineTo(x, y);
      }
    }
    ctx.stroke();
  });

  ctx.fillStyle = "#6b7785";
  ctx.fillText(`时间窗 ${eegState.start.toFixed(1)}-${(eegState.start + eegState.windowSec).toFixed(1)} s · 增益 ${eegState.gain}x · 单位 µV`, left, 18);
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
      `时长：${data.duration.toFixed(1)} s`,
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

async function loadEegFromBuffer(buffer, sourceName, eventsText = "") {
  try {
    eegState.data = parseEdf(buffer);
    eegState.events = eventsText ? parseEvents(eventsText) : [];
    eegState.sourceName = sourceName;
    eegState.start = 0;
    eegState.visibleChannels = Math.min(8, eegState.data.signals.length);
    qs("#eegEmpty")?.classList.add("ready");
    renderEeg();
    showToast(`已加载脑电：${sourceName}`);
  } catch (error) {
    qs("#eegEmpty")?.classList.remove("ready");
    qs("#eegEmpty").textContent = error.message || "EDF 解析失败。";
    showToast("EDF 解析失败，请检查文件格式");
  }
}

async function loadEegFromUrls(edfUrl, eventsUrl = "") {
  qs("#eegEmpty")?.classList.remove("ready");
  qs("#eegEmpty").textContent = "正在加载 EDF 数据。";
  const edfResponse = await fetch(edfUrl);
  if (!edfResponse.ok) throw new Error("EDF 文件加载失败。");
  const eventsResponse = eventsUrl ? await fetch(eventsUrl) : null;
  const eventsText = eventsResponse?.ok ? await eventsResponse.text() : "";
  await loadEegFromBuffer(await edfResponse.arrayBuffer(), edfUrl.split("/").pop(), eventsText);
}

function ensureEegLoaded() {
  if (eegState.autoloaded || eegState.data) {
    renderEeg();
    return;
  }
  eegState.autoloaded = true;
  const [edfUrl, eventsUrl] = (qs("#eegSourceSelect")?.value || "").split("|");
  if (edfUrl) loadEegFromUrls(edfUrl, eventsUrl).catch((error) => showToast(error.message || "脑电加载失败"));
}

function renderTemplates() {
  const target = qs("#templateList");
  if (!target) return;
  target.innerHTML = templates.map((item) => `
    <button class="template ${item.name === state.activeTemplate ? "active" : ""}" data-template="${item.name}">
      <i data-lucide="${item.icon}"></i>
      <span><strong>${item.name}</strong><span>${item.desc}</span></span>
      <i data-lucide="chevron-right"></i>
    </button>
  `).join("");
  qsa(".template").forEach((button) => button.addEventListener("click", () => {
    state.activeTemplate = button.dataset.template;
    renderTemplates();
    renderPreview();
    if (window.lucide) lucide.createIcons();
    showToast(`已选择：${state.activeTemplate}`);
  }));
}

function renderPreviewStrip() {
  const target = qs("#previewStrip");
  if (!target) return;
  target.innerHTML = templates.map((item) => `<button class="preview-chip ${item.name === state.activeTemplate ? "active" : ""}" data-template="${item.name}">${item.name}</button>`).join("");
  qsa(".preview-chip").forEach((button) => button.addEventListener("click", () => {
    state.activeTemplate = button.dataset.template;
    renderTemplates();
    renderPreview();
    if (window.lucide) lucide.createIcons();
  }));
}

function renderParadigms() {
  const target = qs("#paradigmGrid");
  if (!target) return;
  target.innerHTML = paradigms.map(([name, method, status]) => `
    <div><strong>${name}</strong><span>${method}</span><b>${status}</b></div>
  `).join("");
}

function updateSegmentSummary() {
  const target = qs("#segmentSummary");
  if (!target) return;
  if (state.segmentMode === "time") {
    const start = Number(qs("#segmentStart")?.value || 0);
    const end = Number(qs("#segmentEnd")?.value || 0);
    const stride = qs("#segmentStride")?.value || "不重复";
    target.textContent = `将提取 ${start.toFixed(1)}s - ${end.toFixed(1)}s 的连续数据段，重复窗口：${stride}。适合静息态、睡眠、伪迹复核和原始片段浏览。`;
    return;
  }
  const type = qs("#eventType")?.value || "stim/target";
  const pre = Number(qs("#eventPre")?.value || 0);
  const post = Number(qs("#eventPost")?.value || 0);
  target.textContent = `将围绕事件 ${type} 提取 Epoch，窗口为事件前 ${pre.toFixed(1)}s 到事件后 ${post.toFixed(1)}s。适合 ERP、ERSP、N2/P3、N400 和行为事件锁定分析。`;
}

function updateCosts() {
  const subjects = Math.max(1, Number(qs("#subjectsInput")?.value || 1));
  const hours = Math.max(0.1, Number(qs("#hoursInput")?.value || 0.1));
  const total = subjects * hours;
  if (qs("#totalHours")) qs("#totalHours").textContent = `${total.toFixed(1)} h`;
  if (qs("#analysisCost")) qs("#analysisCost").textContent = money(total);
  if (qs("#totalCost")) qs("#totalCost").textContent = money(total);
  return total;
}

function updateBalance() {
  if (qs("#balanceMain")) qs("#balanceMain").textContent = state.balance.toFixed(2);
  if (qs("#balanceSide") && state.role !== "admin") qs("#balanceSide").textContent = money(state.balance);
}

function updateUploadEstimate() {
  const sizeGb = Math.max(0.1, Number(qs("#uploadSizeGb")?.value || 0.1));
  const mbps = Math.max(1, Number(qs("#uploadMbps")?.value || 1));
  const chunkMb = Math.max(16, Number(qs("#chunkMb")?.value || 16));
  const concurrency = Math.max(1, Number(qs("#uploadConcurrency")?.value || 1));
  const efficiency = Math.min(0.92, 0.58 + concurrency * 0.055 + Math.min(chunkMb, 128) / 900);
  const effectiveMbps = mbps * efficiency;
  const etaMinutes = (sizeGb * 8192) / effectiveMbps / 60;
  const chunks = Math.ceil((sizeGb * 1024) / chunkMb);
  if (qs("#uploadEta")) qs("#uploadEta").textContent = `${etaMinutes.toFixed(1)} 分钟`;
  if (qs("#uploadChunks")) qs("#uploadChunks").textContent = String(chunks);
  if (qs("#effectiveMbps")) qs("#effectiveMbps").textContent = `${effectiveMbps.toFixed(0)} Mbps`;
  let advice = "建议：保持默认上传设置即可。大文件会自动分段上传，网络中断后可以继续。";
  if (mbps < 30) advice = "建议：网络较慢时先不要关闭浏览器；如果中断，重新进入项目后继续上传。";
  if (chunks > 2500) advice = "建议：数据量很大，上传会需要更长时间。你可以先上传部分被试试跑分析流程。";
  if (qs("#uploadAdvice")) qs("#uploadAdvice").textContent = advice;
}

function updateRecommendation() {
  const key = qs("#methodSignal")?.value || "p300";
  const item = recommendations[key] || recommendations.p300;
  const target = qs("#methodRecommendation");
  if (!target) return;
  target.innerHTML = `
    <strong>${item.title}</strong>
    <span>${item.body}</span>
    <b>${item.params}</b>
    <small>平台下一步会自动生成被试级指标表、统计摘要、300 dpi 图、方法说明、图注和复现记录，供编辑复核。</small>
  `;
  showToast(`已推荐：${item.title}`);
}


function updateRegisterMode() {
  const mode = qs('input[name="registerMode"]:checked')?.value || "email";
  const emailField = qs(".register-email-field");
  const phoneField = qs(".register-phone-field");
  const passwordField = qs(".register-password-field");
  const hint = qs("#registerModeHint");
  if (emailField) emailField.hidden = mode !== "email";
  if (phoneField) phoneField.hidden = mode !== "phone";
  if (passwordField) passwordField.hidden = mode !== "email";
  if (hint) hint.textContent = mode === "email" ? "邮箱验证码用于正式账户；当前本地版会模拟发送验证码。" : "手机验证码用于沙盒体验，不会触发真实短信。";
}

function handleImageFallback(image) {
  const figure = image.closest("figure");
  image.hidden = true;
  if (figure && !figure.querySelector(".asset-missing")) {
    const note = document.createElement("div");
    note.className = "asset-missing";
    note.textContent = "Pilot \u8bd5\u7528\u7248\u793a\u4f8b\u56fe\u5f85\u751f\u6210\u3002";
    figure.prepend(note);
  }
}

function sendRegisterCode() {
  const mode = qs('input[name="registerMode"]:checked')?.value || "email";
  const target = mode === "email" ? (qs("#registerEmail")?.value || "邮箱") : (qs("#registerPhone")?.value || "手机号");
  const code = mode === "email" ? "246810" : "123456";
  if (qs("#registerCode")) qs("#registerCode").value = code;
  setLoginMessage(`${mode === "email" ? "邮箱" : "手机沙盒"}验证码已生成：${code}（本地演示）`, "success");
  showToast(`验证码已发送到 ${target}`);
}

function boot() {
  renderTasks();
  renderTemplates();
  renderPreviewStrip();
  renderPreview();
  renderParadigms();
  updateSegmentSummary();
  updateCosts();
  updateBalance();
  updateUploadEstimate();
  updateRecommendation();
  renderJourneyDetail(0);
  renderAdminCustomerProfile();
  renderRealFlowSummary();
  enhanceControlLabels();

  qsa("[data-view], [data-view-jump]").forEach((button) => button.addEventListener("click", () => setView(button.dataset.view || button.dataset.viewJump)));
  qsa("[data-login-tab]").forEach((button) => button.addEventListener("click", () => switchLoginTab(button.dataset.loginTab)));
  qs("#demoEntryBtn")?.addEventListener("click", () => startDemoWorkspace(true));
  qs("#forgotPasswordBtn")?.addEventListener("click", () => {
    setLoginMessage("Pilot \u8bd5\u7528\u7248\u8bf7\u8054\u7cfb\u7ba1\u7406\u5458\u91cd\u7f6e\u5bc6\u7801\u3002", "error");
    showToast("Pilot \u8bd5\u7528\u7248\u8bf7\u8054\u7cfb\u7ba1\u7406\u5458\u91cd\u7f6e\u5bc6\u7801");
  });
  qs("#customerLoginForm")?.addEventListener("submit", (event) => {
    event.preventDefault();
    loginCustomer(qs("#customerEmail")?.value.trim() || "", qs("#customerPassword")?.value || "", Boolean(qs("#rememberCustomer")?.checked));
  });
  qsa('input[name="registerMode"]').forEach((input) => input.addEventListener("change", updateRegisterMode));
  qs("#sendCodeBtn")?.addEventListener("click", sendRegisterCode);
  updateRegisterMode();
  qs("#customerRegisterForm")?.addEventListener("submit", (event) => {
    event.preventDefault();
    registerCustomer({
      name: qs("#registerName")?.value || "",
      email: qs("#registerEmail")?.value || "",
      phone: qs("#registerPhone")?.value || "",
      org: qs("#registerOrg")?.value || "",
      password: qs("#registerPassword")?.value || "",
      code: qs("#registerCode")?.value || "",
      mode: qs('input[name="registerMode"]:checked')?.value || "email",
    });
  });
  qs("#adminLoginForm")?.addEventListener("submit", (event) => {
    event.preventDefault();
    loginAdmin(qs("#adminEmail")?.value.trim() || "", qs("#adminPassword")?.value || "");
  });
  qs("#logoutBtn")?.addEventListener("click", logout);

  ["#subjectsInput", "#hoursInput"].forEach((selector) => qs(selector)?.addEventListener("input", updateCosts));
  ["#uploadSizeGb", "#uploadMbps", "#chunkMb", "#uploadConcurrency"].forEach((selector) => qs(selector)?.addEventListener("input", updateUploadEstimate));
  ["#segmentStart", "#segmentEnd", "#segmentStride", "#eventType", "#eventPre", "#eventPost"].forEach((selector) => {
    qs(selector)?.addEventListener("input", updateSegmentSummary);
    qs(selector)?.addEventListener("change", updateSegmentSummary);
  });

  qsa("#segmentMode button").forEach((button) => button.addEventListener("click", () => {
    state.segmentMode = button.dataset.segment;
    qsa("#segmentMode button").forEach((item) => item.classList.toggle("active", item === button));
    qs("#timeSegmentForm")?.classList.toggle("active", state.segmentMode === "time");
    qs("#eventSegmentForm")?.classList.toggle("active", state.segmentMode === "event");
    updateSegmentSummary();
  }));

  qs("#fileInput")?.addEventListener("change", (event) => {
    const files = [...event.target.files];
    const count = files.length;
    qs("#fileLabel").textContent = count ? `已选择 ${count} 个文件` : "选择或拖入 EEG 数据";
    const edf = files.find((file) => file.name.toLowerCase().endsWith(".edf"));
    if (edf) {
      edf.arrayBuffer().then((buffer) => loadEegFromBuffer(buffer, edf.name));
      showToast("正在预览上传的 EDF 数据");
      return;
    }
    if (count) showToast("数据已进入 BIDS 标准化队列");
  });

  qs("#createTaskBtn")?.addEventListener("click", () => {
    const cost = updateCosts();
    if (state.balance < cost) {
      showToast("余额不足，请先充值");
      setView("billing");
      return;
    }
    state.balance -= cost;
    state.tasks.unshift({ name: `eeg-task-${String(Date.now()).slice(-5)}`, detail: `${state.activeTemplate}；${qs("#segmentSummary")?.textContent || ""}`, progress: 12 });
    updateBalance();
    renderTasks();
    showToast(`任务已提交，冻结费用 ${money(cost)}`);
    setView("dashboard");
  });

  qs("#loadEegBtn")?.addEventListener("click", () => {
    const [edfUrl, eventsUrl] = (qs("#eegSourceSelect")?.value || "").split("|");
    if (edfUrl) loadEegFromUrls(edfUrl, eventsUrl).catch((error) => showToast(error.message || "脑电加载失败"));
  });

  qs("#eegSourceSelect")?.addEventListener("change", () => qs("#loadEegBtn")?.click());
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
  qs("#methodSignal")?.addEventListener("change", updateRecommendation);
  qs("#uploadHelpBtn")?.addEventListener("click", () => openModal("uploadHelp"));

  qs("#knowledgeBtn")?.addEventListener("click", () => openModal("knowledge"));
  qs("#auditBtn")?.addEventListener("click", () => openModal("audit"));
  qs("#modalCloseBtn")?.addEventListener("click", closeModal);
  qs("#modalBackdrop")?.addEventListener("click", (event) => {
    if (event.target === qs("#modalBackdrop")) closeModal();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeModal();
  });

  qsa(".journey-card").forEach((card) => {
    const activate = () => {
      const index = Number(card.dataset.journeyStep || 0);
      renderJourneyDetail(index);
      showToast(`已查看：${journeyDetails[index]?.title || "演练步骤"}`);
    };
    card.addEventListener("click", activate);
    card.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        activate();
      }
    });
  });

  qs("#publishBtn")?.addEventListener("click", () => {
    const status = `当前输出：${qs("#dpiSelect")?.value}、${qs("#paletteSelect")?.value}、${qs("#fontSelect")?.value}，已绑定统计表、图注、方法说明和复现记录。`;
    if (qs("#publicationStatus")) qs("#publicationStatus").textContent = status;
    showToast("图像后处理参数已应用到导出包");
  });

  qsa("[data-recharge]").forEach((button) => button.addEventListener("click", () => {
    state.rechargeAmount = Number(button.dataset.recharge);
    qsa("[data-recharge]").forEach((item) => item.classList.toggle("active", item === button));
  }));

  qsa("[data-pay-method]").forEach((button) => button.addEventListener("click", () => {
    qsa("[data-pay-method]").forEach((item) => item.classList.toggle("active", item === button));
    showToast(`${button.dataset.payMethod} 已选中`);
  }));

  qsa(".checklist input").forEach((input) => input.addEventListener("change", () => {
    showToast(input.checked ? "检查项已确认" : "检查项已取消");
  }));

  qsa("img").forEach((image) =>
    image.addEventListener("error", () => handleImageFallback(image), { once: true })
  );

  qsa("a[download]").forEach((link) => link.addEventListener("click", async (event) => {
    event.preventDefault();
    event.stopImmediatePropagation();
    const label = link.textContent.trim() || "\u6587\u4ef6";
    try {
      const response = await fetch(link.href, { method: "HEAD", cache: "no-store" });
      if (!response.ok) {
        showToast(`\u6587\u4ef6\u6682\u4e0d\u53ef\u7528\uff1a${label}`);
        return;
      }
      showToast(`\u5f00\u59cb\u4e0b\u8f7d\uff1a${label}`);
      const download = document.createElement("a");
      download.href = link.href;
      download.download = link.getAttribute("download") || "";
      document.body.append(download);
      download.click();
      download.remove();
    } catch (error) {
      showToast(`\u6587\u4ef6\u6682\u4e0d\u53ef\u7528\uff1a${label}`);
    }
  }, { capture: true }));

  qsa("a[download]").forEach((link) => link.addEventListener("click", () => {
    showToast(`开始下载：${link.textContent.trim() || "文件"}`);
  }));

  qs("#rechargeBtn")?.addEventListener("click", () => {
    state.balance += state.rechargeAmount;
    updateBalance();
    showToast(`充值成功：${money(state.rechargeAmount)}`);
  });

  qs("#invoiceBtn")?.addEventListener("click", () => {
    const notice = qs("#invoiceNotice span");
    if (notice) notice.textContent = "开票申请已提交，平台会在审核后发送电子发票。";
    showToast("开票申请已提交");
  });

  qs('[data-real-action="create-project"]')?.addEventListener("click", async () => {
    try {
      await ensureRealProject();
      renderRealFlowSummary();
      showToast("项目已创建");
    } catch (error) {
      setRealStatus(error.message || "项目创建失败", "error");
      showToast(error.message || "项目创建失败");
    }
  });
  qs('[data-real-action="upload-eeg"]')?.addEventListener("click", async () => {
    try {
      await uploadRealEeg();
      renderRealFlowSummary();
      showToast("文件已上传");
    } catch (error) {
      setRealStatus(error.message || "上传失败", "error");
      showToast(error.message || "上传失败");
    }
  });
  qs('[data-real-action="run-qc"]')?.addEventListener("click", async () => {
    try {
      await runRealTask("qc", "metadata_qc");
      renderRealFlowSummary();
      showToast("QC 已完成");
    } catch (error) {
      setRealStatus(error.message || "QC 失败", "error");
      showToast(error.message || "QC 失败");
    }
  });
  qs('[data-real-action="run-psd"]')?.addEventListener("click", async () => {
    try {
      await runRealTask("psd", "resting_psd");
      renderRealFlowSummary();
      showToast("PSD 已完成");
    } catch (error) {
      setRealStatus(error.message || "PSD 失败", "error");
      showToast(error.message || "PSD 失败");
    }
  });
  qs('[data-real-action="run-erp"]')?.addEventListener("click", async () => {
    try {
      await runRealTask("erp", "erp_p300");
      renderRealFlowSummary();
      showToast("ERP 已完成");
    } catch (error) {
      setRealStatus(error.message || "ERP 失败", "error");
      showToast(error.message || "ERP 失败");
    }
  });
  qs('[data-real-action="create-report"]')?.addEventListener("click", async () => {
    try {
      await createRealReport();
      renderRealFlowSummary();
      showToast("报告已生成");
    } catch (error) {
      setRealStatus(error.message || "报告生成失败", "error");
      showToast(error.message || "报告生成失败");
    }
  });

  if (window.lucide) lucide.createIcons();
  const params = new URLSearchParams(window.location.search);
  if (params.get("demo") === "1") {
    startDemoWorkspace(true);
  } else if (params.get("admin") === "1") {
    loginAdmin(demoAdmin.email, demoAdmin.password);
  } else {
    restoreSession();
  }
}

boot();
