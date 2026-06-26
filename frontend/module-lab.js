const DEFAULT_API_BASE = ["localhost", "127.0.0.1"].includes(window.location.hostname) ? "http://127.0.0.1:8001/api" : "/api";
const API_BASE = new URLSearchParams(window.location.search).get("api") || DEFAULT_API_BASE;

const state = {
  project: null,
  files: [],
  demo数据集: null,
  selectedFileId: "",
  uploadInFlight: false,
};

const EPILEPSY_STD_FIELDS = [
  ["eeg_channel", "EEG 通道（可选，空为第一个可用 EEG）", "text", ""],
  ["epoch_length_sec", "Epoch 长度（秒）", "number", "5"],
  ["std_factor", "STD 阈值系数", "number", "2"],
  ["rms_window_samples", "RMS 滑动窗口（样本）", "number", "15"],
  ["merge_gap_epoch_num", "相邻候选合并间隔（epoch）", "number", "1"],
  ["min_event_epochs", "最小事件长度（epoch）", "number", "2"],
  ["event_window_sec", "统计窗口（秒）", "number", "1800"],
  ["bad_channels", "排除通道，用英文逗号分隔（可选）", "text", ""],
];

const MODULES = {
  qc: {
    title: "数据准备 / 质控",
    workflow: "metadata_qc",
    lifecycle: "数据准备",
    description: "在选择分析方法前，检查元数据、事件可用性和记录可分析性。",
    fields: [
      ["min_sampling_rate_hz", "最低采样率（Hz）", "number", "100"],
      ["min_duration_sec", "最低时长（秒）", "number", "5"],
      ["bad_channel_limit", "坏道复核阈值", "number", "2"],
    ],
  },
  psd: {
    title: "PSD / 频段功率",
    workflow: "resting_psd",
    lifecycle: "稳定分析",
    description: "运行 MNE Welch PSD，并导出频段功率与通道级表格。",
    fields: [
      ["fmin", "最低频率（Hz）", "number", "1"],
      ["fmax", "最高频率（Hz）", "number", "40"],
      ["l_freq", "高通滤波（Hz，可选）", "number", ""],
      ["h_freq", "低通滤波（Hz，可选）", "number", ""],
      ["notch_freq", "陷波滤波（Hz，可选）", "number", ""],
      ["n_fft", "Welch 窗口长度 n_fft（样本，可选）", "number", ""],
      ["n_overlap", "Welch 窗口重叠 n_overlap（样本，可选）", "number", ""],
      ["bad_channels", "排除通道，用英文逗号分隔（可选）", "text", ""],
      ["reject_by_annotation", "排除标记为 BAD 的片段", "checkbox", "true"],
      ["include_channel_table", "导出通道级和频段功率表", "checkbox", "true"],
    ],
  },
  band_power: {
    title: "Band Power / 频段功率",
    workflow: "resting_psd",
    backendModule: "psd",
    lifecycle: "稳定分析",
    fixedParameters: {
      display_alias: "Band Power",
      band_power_view: true,
      non_medical_boundary: "Research EEG descriptive band-power analysis only; non-medical research boundary.",
    },
    description: "复用 PSD 后端合同，聚焦连续 EEG 的描述性频段功率结果；仅用于非医疗科研分析，不作为临床结论。",
    fields: [
      ["fmin", "最低频率（Hz）", "number", "1"],
      ["fmax", "最高频率（Hz）", "number", "40"],
      ["l_freq", "高通滤波（Hz，可选）", "number", ""],
      ["h_freq", "低通滤波（Hz，可选）", "number", ""],
      ["notch_freq", "陷波滤波（Hz，可选）", "number", ""],
      ["n_fft", "Welch 窗口长度 n_fft（样本，可选）", "number", ""],
      ["n_overlap", "Welch 窗口重叠 n_overlap（样本，可选）", "number", ""],
      ["bad_channels", "排除通道，用英文逗号分隔（可选）", "text", ""],
      ["reject_by_annotation", "排除标记为 BAD 的片段", "checkbox", "true"],
      ["include_channel_table", "导出通道级和频段功率表", "checkbox", "true"],
    ],
  },
  erp: {
    title: "ERP / P300",
    workflow: "erp_p300",
    lifecycle: "稳定分析",
    description: "按 standard/target 事件分段，做基线校正，并导出 ERP 指标。",
    fields: [
      ["event_standard", "标准刺激事件码", "number", "1"],
      ["event_target", "目标刺激事件码", "number", "2"],
      ["tmin", "分段开始（秒）", "number", "-0.2"],
      ["tmax", "分段结束（秒）", "number", "0.8"],
      ["baseline_start", "基线开始（秒）", "number", "-0.2"],
      ["baseline_end", "基线结束（秒）", "number", "0"],
      ["l_freq", "高通滤波（Hz）", "number", "0.1"],
      ["h_freq", "低通滤波（Hz）", "number", "30"],
      ["reference_mode", "参考方式", "select", "average", ["average", "keep_current"]],
      ["reject_by_annotation", "排除标记为 BAD 的片段", "checkbox", "true"],
      ["reject_eeg_uv", "剔除阈值（µV，可选）", "number", ""],
      ["bad_channels", "排除通道，用英文逗号分隔（可选）", "text", ""],
      ["roi_channels", "ROI 通道，用英文逗号分隔（可选）", "text", "Pz,P3,P4"],
    ],
  },
  epilepsy_std: {
    title: "癫痫样事件筛查 / STD 阈值",
    workflow: "epilepsy_std_threshold",
    backendModule: "epilepsy",
    workbenchPage: "./epilepsy-workbench.html",
    lifecycle: "内部验证",
    fixedParameters: {
      method: "std_threshold",
      non_medical_boundary: "Research screening/support only; no diagnosis, treatment, or clinical decision-making.",
    },
    description: "用滑动 RMS 与 STD 阈值标记候选高幅事件 epoch，输出表格和复现记录；仅作科研筛查辅助。",
    fields: EPILEPSY_STD_FIELDS,
  },
  epilepsy_lab_std: {
    title: "癫痫样事件筛查 / 实验室同步测试",
    workflow: "epilepsy_std_threshold",
    backendModule: "epilepsy",
    workbenchPage: "./epilepsy-workbench.html",
    lifecycle: "实验室同步",
    statusLabel: "同源试跑",
    fixedParameters: {
      method: "std_threshold",
      display_alias: "癫痫样事件筛查 / 实验室同步测试",
      lab_mode: true,
      lab_fixture_id: "epilepsy_std_demo_high_amplitude_v1",
      sync_mirror_note: "STD current runnable lab mirror; ML high-fidelity migration pending.",
      non_medical_boundary: "Research screening/support only; no diagnosis, treatment, or clinical decision-making.",
    },
    boundaryNotes: [
      "实验室入口复用同一 epilepsy_std_threshold 后端工作流，不 fork 第二套算法。",
      "当前可运行底座为 STD 阈值筛查；ML 高保真迁移完成后复用同一入口和复核工作台。",
    ],
    description: "用于在实验室同步试跑癫痫样候选事件筛查、参数记录和产物下载；仅作科研辅助复核。",
    fields: EPILEPSY_STD_FIELDS,
  },
  tfr: {
    title: "事件锁定时频分析",
    workflow: "tfr_ersp_itc",
    description: "运行 TFR；ERSP、ITC 和 ERS-like / ERD-like 都是事件锁定时频分析下的输出或解释层，不作为独立方法入口。",
    boundaryNotes: [
      "TFR = Time-Frequency Representation，用时频图承载事件后功率随时间和频率的变化。",
      "ERS-like / ERD-like 只描述相对 baseline 的功率升降；没有统计检验时不写成正式显著 ERS/ERD。",
      "TRF = Temporal Response Function，属于连续刺激-神经响应建模，后续可单独开放为连续刺激响应分析。",
    ],
    statusLabel: "时频方法",
    lifecycle: "当前可用方法",
    fields: [
      ["event_id", "事件编号（可选）", "text", ""],
      ["tmin", "分段开始（秒）", "number", "-0.2"],
      ["tmax", "分段结束（秒）", "number", "0.8"],
      ["baseline", "基线开始、结束（秒）", "text", "-0.2,0"],
      ["freqs", "频率网格（Hz）", "text", "8,13,30"],
      ["n_cycles", "小波周期数", "number", "3"],
      ["decim", "降采样步长", "number", "2"],
      ["return_itc", "返回 ITC", "checkbox", "true"],
      ["picks", "分析通道，用英文逗号分隔（可选）", "text", ""],
      ["average", "输出平均时频图", "checkbox", "true"],
    ],
  },
  pac: {
    title: "PAC 相位-振幅耦合",
    workflow: "pac_cfc",
    description: "运行单记录相位-振幅耦合分析，导出 MI 表、相位分箱、耦合图和动态曲线；结果不能单独解释为因果机制。",
    statusLabel: "耦合方法",
    lifecycle: "当前可用方法",
    fields: [
      ["channels", "通道，用英文逗号分隔", "text", "Cz,Pz"],
      ["phase_freqs", "相位频率中心（Hz）", "text", "4,6,8"],
      ["phase_band_width", "相位频带宽度（Hz）", "number", "2"],
      ["amp_freqs", "振幅频率中心（Hz）", "text", "30,50,70"],
      ["amp_band_width", "振幅频带宽度（Hz）", "number", "20"],
      ["n_phase_bins", "相位分箱数", "number", "18"],
      ["window_start_sec", "窗口开始（秒）", "number", "0"],
      ["window_end_sec", "窗口结束（秒，可选）", "number", "8"],
      ["dynamic_window_sec", "动态窗口（秒）", "number", "4"],
      ["dynamic_step_sec", "动态步长（秒）", "number", "2"],
      ["n_surrogates", "替代检验次数", "number", "20"],
      ["random_state", "随机种子", "number", "20260621"],
      ["filter_edge_padding_sec", "滤波边缘填充（秒）", "number", "2"],
      ["edge_trim_sec", "边缘裁剪（秒）", "number", "0"],
      ["bad_channels", "坏道，用英文逗号分隔", "text", ""],
    ],
  },
  reference_csd: {
    title: "CSD 电流源密度计算",
    workflow: "reference_csd",
    description: "运行 CSD 传感器空间滤波并导出前后对照结果；重参考设置属于数据准备，不作为分析方法卡片。",
    statusLabel: "需通道位置",
    lifecycle: "当前可用方法",
    fields: [
      ["reference_mode", "空间滤波模式", "select", "csd", ["csd", "average", "keep_original", "specific_channels", "bipolar"]],
      ["ref_channels", "参考通道，用英文逗号分隔", "text", ""],
      ["bad_channels", "排除通道，用英文逗号分隔（可选）", "text", ""],
      ["bipolar_pairs", "双极参考对（anode-cathode，可选）", "text", ""],
      ["preview_channels", "预览通道，用英文逗号分隔", "text", "Fz,Cz,Pz,Oz"],
      ["preview_start_sec", "预览开始（秒）", "number", "0"],
      ["preview_duration_sec", "预览时长（秒）", "number", "8"],
      ["csd_lambda2", "CSD lambda2", "number", "0.00001"],
      ["csd_stiffness", "CSD 刚度", "number", "4"],
      ["csd_n_legendre_terms", "CSD Legendre 项数", "number", "50"],
    ],
  },
  multitaper_psd: {
    title: "多窗 PSD",
    workflow: "multitaper_psd_tfr",
    backendModule: "multitaper_psd_tfr",
    fixedParameters: { analysis_family: "psd" },
    description: "使用多窗谱估计计算连续 EEG 的 PSD；这是频谱功率方法，不与事件锁定 TFR 合并。",
    statusLabel: "多窗谱方法",
    lifecycle: "当前可用方法",
    fields: [
      ["fmin", "最低频率（Hz）", "number", "1"],
      ["fmax", "最高频率（Hz）", "number", "40"],
      ["bandwidth", "带宽（Hz，可选）", "number", ""],
      ["adaptive", "自适应", "checkbox", ""],
      ["low_bias", "低偏差", "checkbox", "true"],
      ["normalization", "归一化", "select", "length", ["length", "full"]],
      ["remove_dc", "移除直流分量", "checkbox", "true"],
      ["bad_channels", "排除通道，用英文逗号分隔（可选）", "text", ""],
      ["picks", "分析通道，用英文逗号分隔（可选）", "text", ""],
    ],
  },
  multitaper_tfr: {
    title: "事件锁定多窗 TFR",
    workflow: "multitaper_psd_tfr",
    backendModule: "multitaper_psd_tfr",
    fixedParameters: { analysis_family: "tfr" },
    description: "使用多窗方法计算事件锁定时频功率和可选 ITC；这是 TFR 方法，不与多窗 PSD 合并。",
    statusLabel: "多窗时频方法",
    lifecycle: "当前可用方法",
    fields: [
      ["event_id", "事件编号（可选）", "text", ""],
      ["tmin", "分段开始（秒）", "number", "-0.2"],
      ["tmax", "分段结束（秒）", "number", "0.8"],
      ["baseline", "基线开始、结束（秒）", "text", "-0.2,0"],
      ["baseline_mode", "基线模式", "select", "logratio", ["mean", "ratio", "logratio", "percent", "zscore", "zlogratio", "none"]],
      ["freqs", "频率网格（Hz）", "text", "8,13,30"],
      ["n_cycles", "小波周期数", "number", "7"],
      ["time_bandwidth", "时间-带宽积", "number", "4"],
      ["decim", "降采样步长", "number", "1"],
      ["return_itc", "返回 ITC", "checkbox", "true"],
      ["use_fft", "使用 FFT", "checkbox", "true"],
      ["zero_mean", "零均值小波", "checkbox", "true"],
      ["bad_channels", "排除通道，用英文逗号分隔（可选）", "text", ""],
      ["picks", "分析通道，用英文逗号分隔（可选）", "text", ""],
    ],
  },
  connectivity: {
    title: "Connectivity 连接性分析",
    workflow: "connectivity",
    description: "运行单记录传感器空间连接性分析，导出矩阵、边排序和图；结果不证明信息流或因果方向。",
    statusLabel: "连接性方法",
    lifecycle: "当前可用方法",
    fields: [
      ["method", "方法", "select", "correlation", ["correlation", "coherence"]],
      ["fmin", "最低频率（Hz）", "number", "8"],
      ["fmax", "最高频率（Hz）", "number", "12"],
      ["segment_length_sec", "分段长度（秒）", "number", "4"],
      ["edge_top_n", "展示边数", "number", "20"],
      ["reference", "参考说明", "select", "current_recording", ["current_recording"]],
      ["bad_channels", "坏道，用英文逗号分隔", "text", ""],
    ],
  },
};

const P0_MODULE_IDS = ["qc", "psd", "erp"];
const DATA_PREP_MODULE_IDS = ["qc"];
const STABLE_ANALYSIS_MODULE_IDS = ["psd", "band_power", "erp"];
const ADVANCED_MODULE_IDS = ["epilepsy_std", "epilepsy_lab_std", "tfr", "pac", "reference_csd", "multitaper_psd", "multitaper_tfr", "connectivity"];
const METHOD_GROUPS = [
  {
    id: "data-readiness",
    title: "数据准备与 QC",
    lifecycle: "分析前置条件",
    description: "先确认文件结构、事件和记录质量，再进入后续分析。",
    ids: ["qc"],
  },
  {
    id: "stationary-spectral-power",
    title: "连续数据频谱功率",
    lifecycle: "稳定分析",
    description: "PSD / 频段功率用于描述一段连续 EEG 的频率成分和频段能量，不与事件锁定时频图混为一类。",
    ids: ["psd", "band_power"],
  },
  {
    id: "event-locked-time-domain",
    title: "事件锁定时域反应",
    lifecycle: "稳定分析",
    description: "ERP / P300 面向事件标记后的时域波形和峰值指标。",
    ids: ["erp"],
  },
  {
    id: "event-screening-research",
    title: "事件筛查 / 癫痫样事件",
    lifecycle: "内部验证",
    description: "癫痫样事件筛查用于科研辅助复核候选高幅 epoch；不作为诊断、确诊、治疗或临床决策。",
    ids: ["epilepsy_std", "epilepsy_lab_std"],
  },
  {
    id: "event-locked-time-frequency",
    title: "事件锁定时频分析",
    lifecycle: "当前可用方法",
    description: "TFR 是方法入口；ERSP、ITC 与 ERS-like/ERD-like 解释都来自同一时频结果。TRF 是连续刺激响应函数建模，不并入本组。",
    ids: ["tfr"],
  },
  {
    id: "multitaper-spectral-power",
    title: "多窗连续频谱功率",
    lifecycle: "当前可用方法",
    description: "多窗 PSD 是连续频谱功率估计方法，单独评审，不与事件锁定 TFR 合并。",
    ids: ["multitaper_psd"],
  },
  {
    id: "multitaper-time-frequency",
    title: "事件锁定多窗时频分析",
    lifecycle: "当前可用方法",
    description: "多窗 TFR 是事件锁定时频方法，单独评审；ITC 是可选输出指标，baseline 口径需要随结果报告保留。",
    ids: ["multitaper_tfr"],
  },
  {
    id: "csd-spatial-filter",
    title: "CSD 空间滤波",
    lifecycle: "当前可用方法",
    description: "CSD 用于传感器空间的空间滤波；重参考设置归入数据准备，不作为分析方法。",
    ids: ["reference_csd"],
  },
  {
    id: "cross-frequency-coupling",
    title: "跨频耦合",
    lifecycle: "当前可用方法",
    description: "PAC / CFC 描述同一记录中低频相位和高频振幅之间的耦合，不等同于通道间连接性。",
    ids: ["pac"],
  },
  {
    id: "sensor-connectivity",
    title: "传感器连接性",
    lifecycle: "当前可用方法",
    description: "连接性分析描述通道之间的相关或相干结构，不与 PAC/CFC 合并。",
    ids: ["connectivity"],
  },
];

const PREVIEW_ONLY = [
  {
    id: "source_localization",
    title: "源定位 / 逆解",
    reason: "源定位、波束形成和源重建前置条件的预览页。",
    page: "./research-module/source_localization.html",
  },
];

function h(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function icon(name) {
  return `<i data-lucide="${h(name)}" aria-hidden="true"></i>`;
}

function api(path) {
  return `${API_BASE.replace(/\/$/, "")}${path}`;
}

function publicArtifactLabel(item) {
  const raw = item?.label || item?.artifact_type || item?.file_name || item?.path || "output";
  const withoutQuery = String(raw).split(/[?#]/)[0];
  return withoutQuery.split(/[\\/]/).filter(Boolean).pop() || withoutQuery;
}

function moduleTitle(moduleName) {
  const raw = String(moduleName || "");
  const direct = MODULES[raw]?.title;
  if (direct) return direct;
  const byWorkflow = Object.values(MODULES).find((module) => module.workflow === raw || module.backendModule === raw);
  return byWorkflow?.title || raw.toUpperCase() || "分析";
}

function readableErrorDetail(value, fallback) {
  if (!value) return fallback;
  if (typeof value === "string") return value;
  if (typeof value === "object") {
    return value.message || value.error || value.detail || JSON.stringify(value);
  }
  return String(value);
}

async function apiJson(path, options = {}) {
  const response = await fetch(api(path), options);
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const payload = await response.json();
      detail = readableErrorDetail(payload.detail || payload.message, detail);
    } catch (_) {}
    throw new Error(detail);
  }
  return response.json();
}

async function loadFiles() {
  state.files = await apiJson("/eeg/files");
  if (state.selectedFileId) {
    state.files.sort((a, b) => (a.id === state.selectedFileId ? -1 : b.id === state.selectedFileId ? 1 : 0));
  }
  if (!state.selectedFileId && state.files.length) {
    state.selectedFileId = state.files[0].id;
  }
  renderFileOptions();
  renderDataSourceStatus();
  return state.files;
}

async function loadDemo数据集() {
  state.demo数据集 = await apiJson("/lab/demo/dataset");
  renderDemo数据集Summary();
  renderDataSourceStatus();
  return state.demo数据集;
}

async function ensureProject() {
  if (state.project) return state.project;
  const name = document.querySelector("#labProjectName")?.value?.trim() || "分析方法预览项目";
  state.project = await apiJson("/projects", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name,
      description: "分析方法预览项目",
      research_type: "analysis_lab",
      owner_id: "local-user",
      owner_user_id: "local-user",
      created_by: "local-user",
    }),
  });
  renderDataSourceStatus(`项目已创建： ${state.project.id}`, "ok");
  return state.project;
}

async function uploadLabFile() {
  const input = document.querySelector("#labEegFile");
  const file = input?.files?.[0];
  if (!file) throw new Error("请先选择 EEG 数据文件再上传。");
  const project = await ensureProject();
  const form = new FormData();
  form.append("file", file);
  const uploaded = await apiJson(`/eeg/upload?project_id=${encodeURIComponent(project.id)}`, {
    method: "POST",
    body: form,
  });
  state.selectedFileId = uploaded.id;
  state.files = [uploaded, ...state.files.filter((file) => file.id !== uploaded.id)];
  renderFileOptions();
  renderDataSourceStatus(`已上传并选中： ${uploaded.filename || uploaded.id}`, "ok");
  return uploaded;
}

function selectedCustomerFile() {
  return state.files.find((item) => item.id === state.selectedFileId);
}

function fileOptionText(file) {
  const sizeMb = Number(file.size_bytes || 0) / (1024 * 1024);
  const isTeaching = /synthetic|sample|teaching|demo/i.test(String(file.original_filename || file.filename || file.label || file.id || ""));
  const originalName = file.label || file.original_filename || file.filename || "客户数据";
  const name = isTeaching ? `教学示例数据：${originalName}` : originalName;
  const suffix = sizeMb ? ` - ${sizeMb.toFixed(1)} MB` : "";
  return `${name}${suffix}`;
}

function renderFileOptions() {
  document.querySelectorAll("[data-file-select]").forEach((select) => {
    const currentValue = state.selectedFileId || select.value;
    select.innerHTML = [
      `<option value="">教学示例 Oddball EEG（仅用于方法演示）</option>`,
      ...state.files.map((file) => `<option value="${h(file.id)}">${h(fileOptionText(file))}</option>`),
    ].join("");
    select.value = state.files.some((file) => file.id === currentValue) ? currentValue : state.selectedFileId;
  });
}

function renderDataSourceStatus(message = "", tone = "info") {
  const box = document.querySelector("#labDataSourceStatus");
  if (!box) return;
  const file = selectedCustomerFile();
  const demoFile = state.demo数据集?.file;
  const sourceFile = file || demoFile;
  const eventsCounts = sourceFile?.metadata_json?.events || state.demo数据集?.file?.metadata_json?.events || null;
  const sourceLabel = file
    ? `当前客户数据：${fileOptionText(file)}`
    : "当前使用教学示例 Oddball EEG（仅用于方法演示）。";
  const detailItems = [
    eventsCounts && {
      label: "事件数量",
      value: Object.entries(eventsCounts).map(([key, value]) => `${key}: ${value}`).join(" / "),
    },
    sourceFile?.id && { label: "复现编号", value: sourceFile.id },
  ].filter(Boolean);
  box.className = `demo-status ${tone === "ok" ? "ok" : ""}`;
  box.innerHTML = `
    <strong>${h(message || sourceLabel)}</strong>
    <span>运行完成后显示用户可读的结果摘要；复现编号仅用于审计追踪。</span>
    ${detailItems.length ? `<div class="data-source-details">${detailItems.map((item) => `<div class="data-source-detail"><span>${h(item.label)}</span><code>${h(item.value)}</code></div>`).join("")}</div>` : ""}
  `;
}

function renderDemo数据集Summary() {
  const box = document.querySelector("#labDemo数据集Summary");
  if (!box) return;
  const demoFile = state.demo数据集?.file;
  if (!demoFile) {
    box.innerHTML = `<div class="demo-status"><strong>教学示例数据</strong><span>正在加载 Oddball EEG 示例和事件表信息。</span></div>`;
    return;
  }
  const eventsCounts = demoFile.metadata_json?.events || {};
  box.innerHTML = `
    <div class="demo-status ok">
      <strong>教学示例数据已就绪</strong>
      <span>该数据只用于方法演示和回归测试，不会被当作客户项目结果。</span>
      <div class="data-source-details">
        <div class="data-source-detail"><span>数据类型</span><code>Oddball EEG 示例</code></div>
        ${Object.keys(eventsCounts).length ? `<div class="data-source-detail"><span>事件数量</span><code>${h(Object.entries(eventsCounts).map(([key, value]) => `${key}: ${value}`).join(" / "))}</code></div>` : ""}
        <div class="data-source-detail"><span>复现编号</span><code>${h(demoFile.id || "demo")}</code></div>
      </div>
    </div>
  `;
}

function readNumber(form, name) {
  const raw = form.elements[name]?.value;
  if (raw === undefined || raw === null || raw === "") return undefined;
  const value = Number(raw);
  return Number.isFinite(value) ? value : undefined;
}

function stripUndefined(value) {
  if (Array.isArray(value)) return value.map(stripUndefined);
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.entries(value).filter(([, item]) => item !== undefined).map(([key, item]) => [key, stripUndefined(item)]));
  }
  return value;
}

function collect参数(moduleId, form) {
  if (moduleId === "qc") {
    return stripUndefined({
      min_sampling_rate_hz: readNumber(form, "min_sampling_rate_hz"),
      min_duration_sec: readNumber(form, "min_duration_sec"),
      bad_channel_limit: readNumber(form, "bad_channel_limit"),
    });
  }
  if (moduleId === "psd" || moduleId === "band_power") {
    const splitList = (name) => String(form.elements[name]?.value || "").split(",").map((item) => item.trim()).filter(Boolean);
    return stripUndefined({
      ...MODULES[moduleId].fixedParameters,
      fmin: readNumber(form, "fmin"),
      fmax: readNumber(form, "fmax"),
      l_freq: readNumber(form, "l_freq"),
      h_freq: readNumber(form, "h_freq"),
      notch_freq: readNumber(form, "notch_freq"),
      n_fft: readNumber(form, "n_fft"),
      n_overlap: readNumber(form, "n_overlap"),
      bad_channels: splitList("bad_channels"),
      reject_by_annotation: Boolean(form.elements.reject_by_annotation?.checked),
      include_channel_table: Boolean(form.elements.include_channel_table?.checked),
    });
  }
  if (moduleId === "erp") {
    const splitList = (name) => String(form.elements[name]?.value || "").split(",").map((item) => item.trim()).filter(Boolean);
    const referenceMode = form.elements.reference_mode?.value || "average";
    return stripUndefined({
      event_id: {
        standard: readNumber(form, "event_standard") || 1,
        target: readNumber(form, "event_target") || 2,
      },
      event_id_confirmed: true,
      tmin: readNumber(form, "tmin"),
      tmax: readNumber(form, "tmax"),
      baseline: [readNumber(form, "baseline_start"), readNumber(form, "baseline_end")],
      l_freq: readNumber(form, "l_freq"),
      h_freq: readNumber(form, "h_freq"),
      reference: referenceMode === "keep_current" ? null : referenceMode,
      reject_by_annotation: Boolean(form.elements.reject_by_annotation?.checked),
      reject_eeg_uv: readNumber(form, "reject_eeg_uv"),
      bad_channels: splitList("bad_channels"),
      roi_channels: splitList("roi_channels"),
    });
  }
  if (moduleId === "epilepsy_std" || moduleId === "epilepsy_lab_std") {
    const splitList = (name) => String(form.elements[name]?.value || "").split(",").map((item) => item.trim()).filter(Boolean);
    const eegChannel = String(form.elements.eeg_channel?.value || "").trim();
    return stripUndefined({
      ...MODULES[moduleId].fixedParameters,
      eeg_channel: eegChannel || undefined,
      epoch_length_sec: readNumber(form, "epoch_length_sec"),
      std_factor: readNumber(form, "std_factor"),
      rms_window_samples: readNumber(form, "rms_window_samples"),
      merge_gap_epoch_num: readNumber(form, "merge_gap_epoch_num"),
      min_event_epochs: readNumber(form, "min_event_epochs"),
      event_window_sec: readNumber(form, "event_window_sec"),
      bad_channels: splitList("bad_channels"),
    });
  }
  if (moduleId === "tfr") {
    const splitList = (name) => String(form.elements[name]?.value || "").split(",").map((item) => item.trim()).filter(Boolean);
    const splitNumbers = (name) => splitList(name).map((item) => Number(item)).filter((item) => Number.isFinite(item));
    const baselineValues = splitNumbers("baseline");
    return stripUndefined({
      event_id: form.elements.event_id?.value || "",
      tmin: readNumber(form, "tmin"),
      tmax: readNumber(form, "tmax"),
      baseline: baselineValues.length >= 2 ? baselineValues.slice(0, 2) : baselineValues,
      freqs: splitNumbers("freqs"),
      n_cycles: readNumber(form, "n_cycles"),
      decim: readNumber(form, "decim"),
      return_itc: Boolean(form.elements.return_itc?.checked),
      average: Boolean(form.elements.average?.checked),
      picks: splitList("picks"),
    });
  }
  if (moduleId === "reference_csd") {
    const splitList = (name) => String(form.elements[name]?.value || "").split(",").map((item) => item.trim()).filter(Boolean);
    const bipolarPairs = splitList("bipolar_pairs").map((item) => {
      const [anode, cathode] = item.split("-").map((part) => part.trim());
      return anode && cathode ? { anode, cathode, ch_name: `${anode}-${cathode}` } : null;
    }).filter(Boolean);
    return stripUndefined({
      reference_mode: form.elements.reference_mode?.value || "average",
      ref_channels: splitList("ref_channels"),
      bad_channels: splitList("bad_channels"),
      bipolar_pairs: bipolarPairs,
      preview: {
        start_sec: readNumber(form, "preview_start_sec"),
        duration_sec: readNumber(form, "preview_duration_sec"),
        channels: splitList("preview_channels"),
      },
      csd: {
        lambda2: readNumber(form, "csd_lambda2"),
        stiffness: readNumber(form, "csd_stiffness"),
        n_legendre_terms: readNumber(form, "csd_n_legendre_terms"),
      },
    });
  }
  if (moduleId === "multitaper_psd" || moduleId === "multitaper_tfr") {
    const splitList = (name) => String(form.elements[name]?.value || "").split(",").map((item) => item.trim()).filter(Boolean);
    const splitNumbers = (name) => splitList(name).map((item) => Number(item)).filter((item) => Number.isFinite(item));
    const baselineValues = splitNumbers("baseline");
    const isMultitaperPsd = moduleId === "multitaper_psd";
    return stripUndefined({
      analysis_family: MODULES[moduleId].fixedParameters?.analysis_family || "tfr",
      event_id: form.elements.event_id?.value || "",
      fmin: readNumber(form, "fmin"),
      fmax: readNumber(form, "fmax"),
      bandwidth: readNumber(form, "bandwidth"),
      adaptive: Boolean(form.elements.adaptive?.checked),
      low_bias: Boolean(form.elements.low_bias?.checked),
      normalization: form.elements.normalization?.value || "length",
      remove_dc: Boolean(form.elements.remove_dc?.checked),
      bad_channels: splitList("bad_channels"),
      picks: splitList("picks"),
      freqs: isMultitaperPsd ? [8, 13, 30] : splitNumbers("freqs"),
      n_cycles: isMultitaperPsd ? 7 : readNumber(form, "n_cycles"),
      time_bandwidth: isMultitaperPsd ? 4 : readNumber(form, "time_bandwidth"),
      decim: isMultitaperPsd ? 1 : readNumber(form, "decim"),
      return_itc: Boolean(form.elements.return_itc?.checked),
      tmin: readNumber(form, "tmin"),
      tmax: readNumber(form, "tmax"),
      baseline: isMultitaperPsd ? [-0.2, 0] : (baselineValues.length >= 2 ? baselineValues.slice(0, 2) : baselineValues),
      baseline_mode: form.elements.baseline_mode?.value || "logratio",
      use_fft: Boolean(form.elements.use_fft?.checked),
      zero_mean: Boolean(form.elements.zero_mean?.checked),
      n_jobs: 1,
    });
  }
  if (moduleId === "pac") {
    const splitList = (name) => String(form.elements[name]?.value || "").split(",").map((item) => item.trim()).filter(Boolean);
    const splitNumbers = (name) => splitList(name).map((item) => Number(item)).filter((item) => Number.isFinite(item));
    return stripUndefined({
      channels: splitList("channels"),
      phase_freqs: splitNumbers("phase_freqs"),
      phase_band_width: readNumber(form, "phase_band_width"),
      amp_freqs: splitNumbers("amp_freqs"),
      amp_band_width: readNumber(form, "amp_band_width"),
      n_phase_bins: readNumber(form, "n_phase_bins"),
      time_window: {
        start_sec: readNumber(form, "window_start_sec"),
        end_sec: readNumber(form, "window_end_sec"),
      },
      dynamic_window_sec: readNumber(form, "dynamic_window_sec"),
      dynamic_step_sec: readNumber(form, "dynamic_step_sec"),
      n_surrogates: readNumber(form, "n_surrogates"),
      random_state: readNumber(form, "random_state"),
      filter_edge_padding_sec: readNumber(form, "filter_edge_padding_sec"),
      edge_trim_sec: readNumber(form, "edge_trim_sec"),
      bad_channels: splitList("bad_channels"),
    });
  }
  if (moduleId === "connectivity") {
    const splitList = (name) => String(form.elements[name]?.value || "").split(",").map((item) => item.trim()).filter(Boolean);
    return stripUndefined({
      method: form.elements.method?.value || "correlation",
      fmin: readNumber(form, "fmin"),
      fmax: readNumber(form, "fmax"),
      segment_length_sec: readNumber(form, "segment_length_sec"),
      edge_top_n: readNumber(form, "edge_top_n"),
      bad_channels: splitList("bad_channels"),
      reference: form.elements.reference?.value || "current_recording",
    });
  }
  return {};
}

function optionLabel(value) {
  const labels = {
    average: "平均参考",
    keep_original: "保留原参考",
    specific_channels: "指定参考通道",
    bipolar: "双极参考",
    csd: "CSD 电流源密度",
    psd: "PSD 频谱",
    tfr: "TFR 时频",
    length: "按长度归一化",
    full: "完整归一化",
    correlation: "相关系数",
    coherence: "相干性",
    single_record_descriptive_beta: "单记录描述性预览",
  };
  return labels[value] || value;
}

function renderField([name, label, type, value]) {
  if (type === "checkbox") {
    return `<label class="check-field"><input name="${h(name)}" type="checkbox" ${value === "true" ? "checked" : ""} /> ${h(label)}</label>`;
  }
  if (type === "select") {
    const options = arguments[0][4] || [];
    return `<label>${h(label)}<select name="${h(name)}">${options.map((item) => `<option value="${h(item)}" ${item === value ? "selected" : ""}>${h(optionLabel(item))}</option>`).join("")}</select></label>`;
  }
  return `<label>${h(label)}<input name="${h(name)}" type="${h(type)}" step="any" value="${h(value)}" /></label>`;
}

function renderParameterFields(fields, visibleCount = 8) {
  const primaryFields = fields.slice(0, visibleCount);
  const advancedFields = fields.slice(visibleCount);
  const primary = `<div class="runner-fields">${primaryFields.map(renderField).join("")}</div>`;
  if (!advancedFields.length) return primary;
  return `${primary}
    <details class="advanced-params" open>
      <summary>高级参数（${advancedFields.length} 项）</summary>
      <div class="runner-fields advanced">${advancedFields.map(renderField).join("")}</div>
    </details>`;
}

function renderPacModulePanel(id, module, hidden = false) {
  return `<section class="method-panel" id="module-${h(id)}" data-method-panel="${h(id)}" ${hidden ? "hidden" : ""} data-testid="pac-beta-page">
    <div class="method-panel-head"><strong>${h(module.title)}</strong><span>${h(module.statusLabel || module.lifecycle || "可运行")}</span></div>
    <p>${h(module.description)}</p>
    <form class="runner-form" data-runner-form="${h(id)}">
      <fieldset>
        <legend>输入数据</legend>
        <label>数据集<select name="dataset" data-file-select data-testid="pac-dataset-select"><option value="">内置 Oddball 教学 EEG</option></select></label>
        <label>预处理方案<select name="preparation_plan" data-testid="preparation-plan-select"><option value="">当前预处理方案</option><option value="prep_demo">演示预处理方案</option></select></label>
        <small>选择已上传客户文件会直接开始分析；不选择则使用内置教学数据。</small>
      </fieldset>
      <fieldset>
        <legend>常用参数</legend>
        ${renderParameterFields(module.fields, 6)}
      </fieldset>
      <details class="advanced-params pac-extra" data-testid="pac-analysis-scope">
        <summary>PAC 范围与频率网格</summary>
        <fieldset>
          <legend>范围</legend>
          <label>分析范围<select name="analysis_scope"><option value="single_record_descriptive_beta">单记录描述性预览</option></select></label>
          <label>通道选择<input name="channel_select" type="text" value="Cz,Pz" data-testid="pac-channel-select" /></label>
        </fieldset>
        <fieldset>
          <legend>频率网格</legend>
          <label>相位网格<input name="phase_grid" type="text" value="4,6,8" data-testid="pac-phase-grid" /></label>
          <label>相位频带宽度<input name="phase_band_width_visible" type="number" value="2" data-testid="pac-phase-band-width" /></label>
          <label>振幅网格<input name="amp_grid" type="text" value="30,50,70" data-testid="pac-amp-grid" /></label>
          <label>振幅频带宽度<input name="amp_band_width_visible" type="number" value="20" data-testid="pac-amp-band-width" /></label>
        </fieldset>
        <label>可选 PAC 输入上传<input type="file" data-testid="pac-file-upload" /></label>
      </details>
      <button class="btn primary" type="submit" data-testid="pac-run">${icon("play")}运行 ${h(module.title)}</button>
    </form>
    <div class="demo-result" data-result="${h(id)}" data-testid="method-summary"><div class="empty-run-state"><strong>等待运行</strong><span>提交后会创建分析任务，并在这里显示进度、参数记录和可下载结果。</span></div></div>
    <div class="artifact-grid compact" data-testid="artifact-download-list"><div class="empty">暂无输出文件。</div></div>
    <div data-testid="pac-comodulogram" class="demo-status">运行后这里会显示 PAC 耦合图预览。</div>
    <div data-testid="pac-phase-bins" class="demo-status">运行后这里会显示 PAC 相位分箱预览。</div>
    <div data-testid="pac-dynamic-curve" class="demo-status">运行后这里会显示 PAC 动态曲线预览。</div>
  </section>`;
}

function renderModulePanel(id, module, hidden = false) {
  if (id === "pac") return renderPacModulePanel(id, module, hidden);
  const boundaryNotes = module.boundaryNotes?.length ? `<div class="method-boundary-notes" aria-label="${h(module.title)}科学边界">
      ${module.boundaryNotes.map((note) => `<span>${h(note)}</span>`).join("")}
    </div>` : "";
  const workbenchLink = module.workbenchPage ? `<div class="module-workbench-link"><a class="btn primary" href="${h(module.workbenchPage)}?api=${encodeURIComponent(API_BASE)}">${icon("monitor-cog")}打开癫痫分析工作台</a><small>进入参数、候选事件、epoch 时间轴和人工复核界面。</small></div>` : "";
  return `<section class="method-panel" id="module-${h(id)}" data-method-panel="${h(id)}" ${hidden ? "hidden" : ""}>
    <div class="method-panel-head"><strong>${h(module.title)}</strong><span>${h(module.statusLabel || module.lifecycle || "可运行")}</span></div>
    <p>${h(module.description)}</p>
    ${boundaryNotes}
    ${workbenchLink}
    <form class="runner-form" data-runner-form="${h(id)}">
      <fieldset>
        <legend>输入数据</legend>
        <label>数据集<select name="dataset" data-file-select><option value="">内置 Oddball 教学 EEG</option></select></label>
        <small>选择已上传客户文件会直接开始分析；不选择则使用内置教学数据。</small>
      </fieldset>
      <fieldset>
        <legend>参数</legend>
        ${renderParameterFields(module.fields, id === "tfr" ? module.fields.length : 8)}
      </fieldset>
      <button class="btn primary" type="submit">${icon("play")}运行 ${h(module.title)}</button>
    </form>
    <div class="demo-result" data-result="${h(id)}"><div class="empty-run-state"><strong>等待运行</strong><span>提交后会创建分析任务，并在这里显示进度、参数记录和可下载结果。</span></div></div>
  </section>`;
}

function renderMethodGroupCard(group) {
  const firstId = group.ids[0];
  return `<article class="module-card live-card method-group-card" id="method-group-${h(group.id)}" data-method-group="${h(group.id)}">
    <div class="module-card-top"><span>${h(group.lifecycle)}</span><strong>${h(group.ids.length)} 个入口</strong></div>
    <h2>${h(group.title)}</h2>
    <p>${h(group.description)}</p>
    <div class="method-contract"><span>真实分析</span><span>参数记录</span><span>结果文件</span></div>
    ${group.ids.length > 1 ? `<div class="method-switcher" role="tablist" aria-label="${h(group.title)}">
      ${group.ids.map((id, index) => `<button class="method-switch${index === 0 ? " active" : ""}" type="button" role="tab" aria-selected="${index === 0 ? "true" : "false"}" data-method-switch="${h(group.id)}" data-target-method="${h(id)}">
        <strong>${h(MODULES[id].title)}</strong><span>${h(MODULES[id].statusLabel || MODULES[id].lifecycle || "当前方法")}</span>
      </button>`).join("")}
    </div>` : ""}
    <div class="method-stack">
      ${group.ids.map((id) => renderModulePanel(id, MODULES[id], id !== firstId)).join("")}
    </div>
  </article>`;
}

function renderArtifacts(task, artifacts, parameters) {
  const displayTitle = parameters?.display_alias || moduleTitle(task.module_name || "");
  const links = artifacts.map((item) => `<a class="artifact" href="${api(`/artifacts/${item.id}/download`)}" target="_blank" rel="noopener">
    <span>${h(item.artifact_type)}</span>
    <strong>${h(publicArtifactLabel(item))}</strong>
    <small>${h(item.mime_type || "可下载产物")}</small>
  </a>`).join("");
  return `<div class="demo-status ok" data-testid="method-summary">
    <strong>分析完成：${h(displayTitle)}</strong>
    <span>结果文件已生成，可在下方下载；参数和解释边界已随结果记录保存。</span>
    <details class="param-echo"><summary>本次设置与技术记录</summary><code>${h(JSON.stringify({ status: task.status, task_id: task.id, workflow_id: task.workflow_id, parameters }, null, 2))}</code></details>
  </div>
  <div class="artifact-grid compact" data-testid="artifact-download-list">${links || `<div class="empty">暂无输出文件。</div>`}</div>`;
}

async function runModule(moduleId, form, resultBox) {
  const backendModuleId = MODULES[moduleId].backendModule || moduleId;
  const parameters = collect参数(moduleId, form);
  resultBox.innerHTML = `<div class="demo-status">正在运行 ${h(moduleId.toUpperCase())}。后端正在读取 EEG、执行分析并写入结果文件……</div>`;
  const selectedFileId = form.elements.dataset?.value || "";
  let task;
  if (selectedFileId) {
    const file = state.files.find((item) => item.id === selectedFileId);
    if (!file) throw new Error("当前选择的 EEG 文件不可用，请刷新文件列表后重试。");
    state.selectedFileId = selectedFileId;
    task = await apiJson("/tasks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        project_id: file.project_id,
        module_name: backendModuleId,
        workflow_id: MODULES[moduleId].workflow,
        input_file_id: file.id,
        parameters_json: parameters,
        owner_user_id: "local-user",
        created_by: "local-user",
      }),
    });
  } else {
    task = await apiJson(`/lab/demo/run/${encodeURIComponent(backendModuleId)}/configured`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ parameters_json: parameters }),
    });
  }
  const refreshedTask = await apiJson(`/tasks/${encodeURIComponent(task.id)}`);
  const artifacts = await apiJson(`/tasks/${encodeURIComponent(task.id)}/artifacts`);
  resultBox.innerHTML = renderArtifacts(refreshedTask, artifacts, parameters);
  if (window.lucide) window.lucide.createIcons();
}

function bindRunners() {
  document.querySelectorAll("[data-method-switch]").forEach((switchButton) => {
    if (switchButton.dataset.boundMethodSwitch) return;
    switchButton.addEventListener("click", () => {
      const group = switchButton.closest("[data-method-group]");
      if (!group) return;
      const targetMethod = switchButton.dataset.targetMethod;
      group.querySelectorAll("[data-method-panel]").forEach((panel) => {
        panel.hidden = panel.getAttribute("data-method-panel") !== targetMethod;
      });
      group.querySelectorAll("[data-method-switch]").forEach((button) => {
        const active = button.dataset.targetMethod === targetMethod;
        button.classList.toggle("active", active);
        button.setAttribute("aria-selected", active ? "true" : "false");
      });
      const target = group.querySelector(`[data-method-panel="${CSS.escape(targetMethod)}"]`);
      const resultBox = target?.querySelector(`[data-result="${CSS.escape(targetMethod)}"]`);
      if (resultBox) resultBox.scrollIntoView({ block: "nearest", behavior: "smooth" });
    });
    switchButton.dataset.boundMethodSwitch = "true";
  });
  document.querySelectorAll("[data-runner-form]").forEach((form) => {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const moduleId = form.getAttribute("data-runner-form");
      const button = form.querySelector("button[type='submit']");
      const resultBox = document.querySelector(`[data-result="${moduleId}"]`);
      button.disabled = true;
      try {
        await runModule(moduleId, form, resultBox);
      } catch (error) {
        resultBox.innerHTML = `<div class="demo-status error">运行失败：${h(error.message || error)}</div>`;
      } finally {
        button.disabled = false;
      }
    });
  });
  const uploadButton = document.querySelector("#labUploadButton");
  if (uploadButton && !uploadButton.dataset.boundUpload) uploadButton.addEventListener("click", async (event) => {
    event.preventDefault();
    event.stopImmediatePropagation();
    if (state.uploadInFlight || window.__qlModuleLabUploadInFlight) return;
    state.uploadInFlight = true;
    window.__qlModuleLabUploadInFlight = true;
    const button = uploadButton;
    button.disabled = true;
    renderDataSourceStatus("正在上传 EEG 文件……", "info");
    try {
      await uploadLabFile();
    } catch (error) {
      const box = document.querySelector("#labDataSourceStatus");
      if (box) box.innerHTML = `<div class="demo-status error"><strong>上传失败</strong><span>${h(error.message || error)}</span><span>请检查服务连接，然后重试上传或刷新文件列表。</span></div>`;
    } finally {
      state.uploadInFlight = false;
      window.__qlModuleLabUploadInFlight = false;
      button.disabled = false;
    }
  });
  if (uploadButton) uploadButton.dataset.boundUpload = "true";
  const refreshButton = document.querySelector("#labRefreshFiles");
  if (refreshButton && !refreshButton.dataset.boundRefresh) refreshButton.addEventListener("click", async () => {
    await loadFiles();
  });
  if (refreshButton) refreshButton.dataset.boundRefresh = "true";
  if (!document.body.dataset.boundModuleLabFileSelect) {
    document.addEventListener("change", (event) => {
      if (!event.target.matches("[data-file-select]")) return;
      state.selectedFileId = event.target.value;
      renderFileOptions();
      renderDataSourceStatus();
    });
    document.body.dataset.boundModuleLabFileSelect = "true";
  }
}

function renderPreviewOnly() {
  return PREVIEW_ONLY.map(({ id, title, reason, page }) => `<article class="module-card preview-card" id="module-${h(id)}" data-testid="module-preview-${h(id)}" aria-label="${h(title)}，仅预览">
    <div class="module-card-top"><span>仅预览</span><strong>${h(title)}</strong></div>
    <h2>${h(title)}</h2>
    <p>${h(reason)}</p>
    ${page ? `<a class="btn" href="${h(page)}">${icon("external-link")}打开预览页</a>` : `<button class="btn" type="button" disabled>${icon("lock")}暂未开放运行</button>`}
  </article>`).join("");
}

function renderModuleSection({ title, eyebrow, description, groups, className }) {
  return `<section class="workflow-section ${h(className)}" aria-labelledby="${h(className)}-title">
    <div class="section-intro">
      <p class="eyebrow">${h(eyebrow)}</p>
      <h2 id="${h(className)}-title">${h(title)}</h2>
      <p>${h(description)}</p>
    </div>
    <div class="module-grid live-grid">
      ${groups.map(renderMethodGroupCard).join("")}
    </div>
  </section>`;
}

function renderPage() {
  return `<header class="lab-hero detail-top">
    <nav class="lab-nav compact">
      <a class="brand" href="./index.html?customer_demo=login&api=${encodeURIComponent(API_BASE)}"><span class="brand-mark">QL</span><span><strong>QLanalyser</strong><small>分析方法库</small></span></a>
      <a class="pill" href="./index.html?customer_demo=login&api=${encodeURIComponent(API_BASE)}">${icon("arrow-left")}返回项目分析</a>
    </nav>
  </header>
  <main class="lab-wrap">
    <section class="module-hero">
      <div class="hero-kicker"><span class="status enabled">真实分析流程</span><span class="status glass">可用教学数据</span><span class="status glass">9 项分析能力 + 同步测试入口</span></div>
      <p class="eyebrow">分析方法库</p>
      <h1>上传一份 EEG，查看并试用当前分析方法</h1>
      <p>这里帮助科研用户先确认数据可分析性，再分别查看 PSD、ERP、TFR、多窗、参考变换、PAC 和连接性。每个方法都会保留参数记录、结果文件和解释边界。</p>
      <div class="hero-proof-grid" aria-label="分析方法能力概览">
        <div><strong>01</strong><span>数据准备与 QC 保留</span></div>
        <div><strong>02</strong><span>按科学目的拆分方法</span></div>
        <div><strong>03</strong><span>本地 EDF 可端到端测试</span></div>
      </div>
      <p class="boundary-note">科研分析方法库：结果用于数据质量复核、方法复现和研究报告，仅作为非医疗科研分析参考，不作为临床结论。</p>
    </section>
    <section class="module-index panel" aria-label="分析方法索引">
      <div>
        <span>1 数据准备</span>
        <a href="#method-group-data-readiness">QC 可分析性</a>
      </div>
      <div>
        <span>2 稳定分析</span>
        <a href="#method-group-stationary-spectral-power">连续频谱功率</a>
        <a href="#method-group-event-locked-time-domain">事件锁定时域</a>
      </div>
      <div>
        <span>当前可用方法</span>
        <a href="#method-group-event-screening-research">事件筛查 / 癫痫样事件</a>
        <a href="#method-group-event-locked-time-frequency">事件锁定时频</a>
        <a href="#method-group-multitaper-spectral-power">多窗 PSD</a>
        <a href="#method-group-multitaper-time-frequency">多窗 TFR</a>
        <a href="#method-group-csd-spatial-filter">CSD 空间滤波</a>
        <a href="#method-group-cross-frequency-coupling">跨频耦合</a>
        <a href="#method-group-sensor-connectivity">传感器连接性</a>
      </div>
    </section>
    <section class="panel lab-source-panel">
      <div class="source-copy">
        <p class="eyebrow">数据来源</p>
        <h2>上传或选择分析数据集</h2>
        <p>无需先建立正式项目。你可以上传本地 EDF/FIF，也可以使用内置教学数据；每个方法都会按真实分析流程运行。</p>
      </div>
      <form class="runner-form source-form" onsubmit="return false;">
        <label>项目名称<input id="labProjectName" type="text" value="分析方法预览项目" /></label>
        <label>EEG 文件<input id="labEegFile" type="file" /></label>
        <div class="source-actions">
          <button id="labUploadButton" class="btn primary" type="button">${icon("upload")}上传并选中</button>
          <button id="labRefreshFiles" class="btn" type="button">${icon("refresh-cw")}刷新文件列表</button>
        </div>
      </form>
      <div id="labDataSourceStatus" class="demo-status"></div>
      <div id="labDemo数据集Summary"></div>
    </section>
    ${renderModuleSection({
      title: "1. 数据准备与 QC 可分析性",
      eyebrow: "分析前置条件",
      description: "选择分析方法前，确认上传的 EEG 文件具备足够的元数据、事件可用性和质量证据。",
      groups: METHOD_GROUPS.filter((group) => group.ids.some((id) => DATA_PREP_MODULE_IDS.includes(id))),
      className: "data-preparation-workflow",
    })}
    ${renderModuleSection({
      title: "2. 按科学目的归类的稳定分析",
      eyebrow: "当前稳定可用",
      description: "PSD 和 ERP 分属不同分析目的：一个看连续频谱功率，一个看事件锁定时域反应。",
      groups: METHOD_GROUPS.filter((group) => group.ids.some((id) => STABLE_ANALYSIS_MODULE_IDS.includes(id))),
      className: "p0-workflow",
    })}
    ${renderModuleSection({
      title: "当前可用分析方法",
      eyebrow: "按科研问题归类",
      description: "方法按科学问题拆开：时频动态、多窗估计、CSD 空间滤波、跨频耦合和通道间连接性分别查看；参数、统计口径和解释边界随结果记录保存。",
      groups: METHOD_GROUPS.filter((group) => group.ids.some((id) => ADVANCED_MODULE_IDS.includes(id)) && !group.ids.some((id) => STABLE_ANALYSIS_MODULE_IDS.includes(id))),
      className: "advanced-workflow",
    })}
    <section class="workflow-section preview-workflow" aria-labelledby="preview-workflow-title">
      <div class="section-intro">
        <p class="eyebrow">边界预览</p>
        <h2 id="preview-workflow-title">边界说明方法</h2>
        <p>这些页面用于说明前置条件和科学边界，暂不创建可执行客户任务。</p>
      </div>
      <div class="module-grid live-grid">
      ${renderPreviewOnly()}
      </div>
    </section>
  </main>`;
}

async function main() {
  const root = document.querySelector("#moduleLab");
  try {
    root.innerHTML = renderPage();
    bindRunners();
    await Promise.all([loadFiles(), loadDemo数据集()]);
    if (window.lucide) window.lucide.createIcons();
  } catch (error) {
    root.innerHTML = `<section class="lab-wrap"><div class="empty"><strong>分析方法库加载失败。</strong><span>${h(error.message || error)}</span><span>请确认 QLanalyser 服务连接正常，然后刷新页面。</span></div></section>`;
  }
}

main();
