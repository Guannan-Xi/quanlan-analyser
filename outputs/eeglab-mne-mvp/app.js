const qs = (selector) => document.querySelector(selector);
const qsa = (selector) => [...document.querySelectorAll(selector)];
const money = (value) => `￥${Number(value).toFixed(2)}`;

const state = {
  balance: 1000,
  rechargeAmount: 1000,
  activeTemplate: "ERP 事件相关电位",
  segmentMode: "time",
  role: null,
  tasks: [
    { name: "数据上传与识别", detail: "10 份 EEG 已读取，事件标签和通道信息已识别", progress: 100 },
    { name: "P300 分析与统计", detail: "已生成 P300 指标、统计摘要和主图", progress: 100 },
    { name: "结果包整理", detail: "图、表、方法说明和复现记录正在整理", progress: 92 },
  ],
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
  dashboard: "我的脑电分析项目",
  journey: "新手教程：一步一步完成脑电分析",
  analysis: "开始脑电分析",
  workflow: "新手交互式分析向导",
  paradigms: "20 个常见脑电范式",
  statistics: "科研统计与待统计数据",
  publication: "发表级图像后处理",
  upload: "上传脑电数据",
  storage: "我的线上数据",
  billing: "支付与计时计费",
  invoice: "在线申请开票",
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
    body: "给这次分析取一个名字，例如 P300 oddball pilot。你也可以直接使用系统示例名称。",
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
    body: "按每小时脑电数据 1 元，15 h 扣 15 元。余额从 1000 元变为 985 元，扣费记录可用于开票。",
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
    action: "小白用户先用默认参数即可，后续再让专家调整高级参数。",
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
        <button class="ghost-btn" data-modal-view="journey"><i data-lucide="clipboard-check"></i><span>查看新手教程</span></button>
      </div>
    `,
  },
  audit: {
    title: "项目记录",
    body: `
      <div class="audit-list">
        <span>09:00 创建项目 P300 oddball pilot</span>
        <span>09:05 上传 10 份 EEG，哈希校验通过</span>
        <span>09:08 推荐 ERP/P300 方法，参数写入 manifest</span>
        <span>09:16 导出 publication_package.zip</span>
        <span>09:20 开票申请已提交</span>
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

function loginAs(role) {
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
    setView("adminDashboard");
  } else {
    qs("#roleLabel").textContent = "客户账户";
    qs("#balanceSide").textContent = money(state.balance);
    qs("#accountHint").textContent = "按脑电记录时长计费，费用透明可开票";
    qs("#topEyebrow").textContent = "项目：P300 oddball pilot / 10 份 EEG";
    qs("#tutorialBtn").hidden = false;
    setView("journey");
  }
  if (window.lucide) lucide.createIcons();
}

function logout() {
  state.role = null;
  qs("#appShell").hidden = true;
  qs("#loginScreen").hidden = false;
  qsa(".view").forEach((el) => el.classList.remove("active"));
  qsa(".nav-item").forEach((el) => el.classList.remove("active"));
  closeModal();
  if (window.lucide) lucide.createIcons();
}

function setView(view) {
  const targetNav = qs(`[data-view="${view}"]`);
  if (targetNav?.dataset.role && state.role && targetNav.dataset.role !== state.role) return;
  qsa(".view").forEach((el) => el.classList.toggle("active", el.id === view));
  qsa(".nav-item").forEach((el) => el.classList.toggle("active", el.dataset.view === view));
  const title = qs("#viewTitle");
  if (title) title.textContent = titles[view] || titles.dashboard;
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

function activeTemplate() {
  return templates.find((item) => item.name === state.activeTemplate) || templates[0];
}

function renderPreview() {
  const item = activeTemplate();
  const image = qs("#analysisPreview");
  const caption = qs("#previewCaption");
  if (image) {
    image.src = item.image;
    image.alt = `${item.name} 示例图`;
  }
  if (caption) caption.textContent = item.desc;
  qsa(".preview-chip").forEach((button) => button.classList.toggle("active", button.dataset.template === item.name));
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
    <small>平台下一步会自动生成 subject-level CSV、统计摘要、300 dpi 图、methods、caption 和 manifest，供编辑复核。</small>
  `;
  showToast(`已推荐：${item.title}`);
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
  logout();

  qsa("[data-view], [data-view-jump]").forEach((button) => button.addEventListener("click", () => setView(button.dataset.view || button.dataset.viewJump)));
  qsa("[data-login-role]").forEach((button) => button.addEventListener("click", () => loginAs(button.dataset.loginRole)));
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
    const count = event.target.files.length;
    qs("#fileLabel").textContent = count ? `已选择 ${count} 个文件` : "选择或拖入 EEG 数据";
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

  qs("#cyclePreviewBtn")?.addEventListener("click", () => {
    const index = templates.findIndex((item) => item.name === state.activeTemplate);
    state.activeTemplate = templates[(index + 1) % templates.length].name;
    renderTemplates();
    renderPreview();
    if (window.lucide) lucide.createIcons();
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
    const status = `当前输出：${qs("#dpiSelect")?.value}、${qs("#paletteSelect")?.value}、${qs("#fontSelect")?.value}，已绑定统计 CSV、caption、methods 和 manifest。`;
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

  if (window.lucide) lucide.createIcons();
}

boot();
