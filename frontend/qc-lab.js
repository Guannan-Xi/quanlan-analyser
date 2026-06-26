const DEFAULT_API_BASE = ["localhost", "127.0.0.1"].includes(window.location.hostname) ? "http://127.0.0.1:8001/api" : "/api";
const params = new URLSearchParams(window.location.search);
const API_BASE = params.get("api") || DEFAULT_API_BASE;
const MAX_PREVIEW_CHANNELS = 64;
const MAX_PREVIEW_DURATION_SEC = 30;
const SEGMENT_STORE_KEY = "qlanalyser.qc.previewSegments.v1";
const SEGMENT_TAG_LABELS = {
  artifact_review: "伪迹复核",
  bad_channel_evidence: "坏道依据",
  bad_segment_evidence: "坏段依据",
  filter_check: "滤波检查",
  teaching_example: "教学示例",
  report_evidence: "报告依据",
  other: "其他"
};

const state = {
  project: null,
  files: [],
  selectedFile: "",
  metadata: null,
  task: null,
  plan: null,
  artifacts: [],
  activeFigure: "raw_preview_figure",
  fileMessage: "",
  fileError: false,
  runMessage: "",
  runError: false,
  channelQuery: "",
  selectedChannels: [],
  viewport: { startSec: 0, durationSec: 12, verticalScaleUv: 100, displaySfreq: 250, mode: "overlay" },
  filterPreview: { enabled: true, bandpass: { enabled: true, l_freq: 1, h_freq: 40 }, notch: { enabled: true, freqs: [50] } },
  badChannels: [],
  pendingBadSegment: { startSec: 0, endSec: 2, reason: "eye_blink", note: "" },
  badSegments: [],
  annotationActions: [],
  savedPreviewSegments: [],
  activePreviewSegmentId: null,
  unsavedChanges: false,
  segmentDraft: { name: "当前预览片段", note: "", tags: ["evidence_review"], includeInReport: true },
};

function icon(name){ return `<i data-lucide="${name}" aria-hidden="true"></i>`; }
function h(value){ return String(value ?? "").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#39;"); }
function api(path){ return `${API_BASE}${path}`; }
function fmt(value, digits = 2){ const n = Number(value); return Number.isFinite(n) ? n.toFixed(digits) : "-"; }
function uid(prefix){ return `${prefix}_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`; }
function selectedFile(){ return state.files.find((item)=>item.id===state.selectedFile); }
function metadataChannels(){ return state.metadata?.channel_names || []; }
function channelTypeMap(){ const names = state.metadata?.channel_names || []; const types = state.metadata?.channel_types || []; return Object.fromEntries(names.map((name, index)=>[name, types[index] || "unknown"])); }
function byLabel(label){ return state.artifacts.find((item) => item.label === label); }
function artifactUrl(artifact){ return api(`/artifacts/${artifact.id}/download`); }
function currentPlanReference(){
  if(!state.plan?.id || state.plan.is_default || !Number.isFinite(Number(state.plan.revision))) return {};
  return {
    data_preparation_plan_id: state.plan.id,
    data_preparation_revision: Number(state.plan.revision),
    data_preparation_contract_version: "qlanalyser-data-preparation-v0.2",
  };
}
function planStateLabel(){
  if(!state.plan) return "未保存";
  if(state.plan.is_default) return "默认草稿";
  return `${state.plan.status || "draft"} 第 ${state.plan.revision} 版`;
}
function planGateState(){
  const file = selectedFile();
  const reference = currentPlanReference();
  const confirmed = state.plan?.status === "confirmed" && !state.plan?.is_default;
  const psdBlocked = state.badChannels.length > Math.max(6, metadataChannels().length * 0.25);
  const erpHasEvents = Boolean(state.metadata?.annotation_count || state.metadata?.event_count);
  return {
    confirmed,
    status: state.plan?.is_default ? "default_draft" : (state.plan?.status || "draft"),
    revision: Number.isFinite(Number(state.plan?.revision)) ? Number(state.plan.revision) : 0,
    planId: reference.data_preparation_plan_id || "",
    fileId: state.selectedFile || file?.id || "",
    psdReady: confirmed && !psdBlocked,
    erpReady: confirmed && erpHasEvents,
    erpHasEvents,
  };
}

async function request(path, options = {}){
  const response = await fetch(api(path), options);
  if(!response.ok){
    let detail = await response.text();
    try {
      const parsed = JSON.parse(detail);
      detail = parsed.detail?.message || parsed.detail?.error_code || parsed.detail || parsed.message || JSON.stringify(parsed, null, 2);
      if(typeof detail !== "string") detail = JSON.stringify(detail, null, 2);
    } catch {}
    throw new Error(detail || `HTTP ${response.status}`);
  }
  const type = response.headers.get("content-type") || "";
  return type.includes("application/json") ? response.json() : response.text();
}

function loadLocalSegments(){
  try {
    const all = JSON.parse(localStorage.getItem(SEGMENT_STORE_KEY) || "{}");
    state.savedPreviewSegments = state.selectedFile ? (all[state.selectedFile] || []) : [];
  } catch { state.savedPreviewSegments = []; }
}
function persistLocalSegments(){
  const all = JSON.parse(localStorage.getItem(SEGMENT_STORE_KEY) || "{}");
  if(state.selectedFile) all[state.selectedFile] = state.savedPreviewSegments;
  localStorage.setItem(SEGMENT_STORE_KEY, JSON.stringify(all));
}
function markDirty(){ state.unsavedChanges = true; }
function syncIcons(){ if(window.lucide) window.lucide.createIcons(); }

function render(){
  const root = document.querySelector("#qcLab");
  const gate = planGateState();
  root.dataset.qcPlanStatus = gate.status;
  root.dataset.qcPlanConfirmed = gate.confirmed ? "true" : "false";
  root.dataset.qcPlanRevision = String(gate.revision);
  root.dataset.qcPlanId = gate.planId;
  root.dataset.qcFileId = gate.fileId;
  root.dataset.qcPsdReady = gate.psdReady ? "true" : "false";
  root.dataset.qcErpReady = gate.erpReady ? "true" : "false";
  root.innerHTML = `
    <header class="qc-top"><nav class="qc-nav">
      <a class="brand" href="./qc-lab.html"><span class="brand-mark">QC</span><span><strong>QC 与数据准备</strong><small>元数据 / 波形 / 片段记录</small></span></a>
      <div class="top-links"><a href="./module-lab.html">${icon("layout-dashboard")}体验中心</a><a href="./">${icon("lock")}工作台</a></div>
    </nav></header>
    <section class="qc-wrap">
      <section class="hero">
        <div class="hero-card"><p class="eyebrow">数据准备</p><h1>分析前先检查信号质量</h1><p>开始 PSD 或 ERP 前，先检查元数据、通道、单位、坏导、坏段、事件标记、预览滤波和片段证据。原始 EEG 文件不会被修改。</p><div class="hero-actions"><button class="btn primary" id="runPreviewBtn">${icon("activity")}刷新波形</button><button class="btn" id="saveSegmentTopBtn">${icon("bookmark-plus")}保存片段证据</button><button class="btn" id="savePlanBtn">${icon("save")}保存草稿</button><button class="btn primary" id="confirmPlanBtn">${icon("badge-check")}确认方案</button><button class="btn" id="downloadPlanBtn">${icon("download")}下载方案</button></div></div>
        <aside class="side-card"><h2>当前状态</h2><ul class="status-list"><li><strong>最多 64 个通道</strong><span>每次波形预览最多显示 64 个通道。</span></li><li><strong>仅用于预览的滤波</strong><span>带通/陷波只影响当前预览窗口，不会修改源 EEG。</span></li><li><strong>数据准备方案</strong><span>${h(planStateLabel())}</span></li></ul></aside>
      </section>
      <div class="layout">
        <aside>
          ${renderFilePanel()}
          ${renderChannelPanel()}
          ${renderPrepPanel()}
        </aside>
        <main>
          ${renderPlanGatePanel()}
          ${renderMetadataPanel()}
          ${renderWaveformPanel()}
          ${renderSegmentsPanel()}
          ${renderQualityPanel()}
        </main>
      </div>
    </section>`;
  bindEvents();
  syncIcons();
}

function renderFilePanel(){
  const optionRows = state.files.map((file)=>{
    const rawName = String(file.original_filename || file.filename || file.label || file.id || "");
    const isExample = /synthetic|sample|teaching|demo/i.test(rawName);
    const label = isExample ? "Teaching EEG example" : (file.label || file.original_filename || "Customer EEG file");
    return `<option value="${h(file.id)}" ${file.id===state.selectedFile?"selected":""}>${h(label)}</option>`;
  }).join("");
  return `<section class="panel"><h2>${icon("folder-open")}文件与元数据</h2><div class="field"><label>选择 EEG 文件</label><select id="fileSelect"><option value="">请选择文件</option>${optionRows}</select></div><div class="grid-2"><button class="btn" id="refreshFilesBtn">${icon("refresh-cw")}刷新文件</button><button class="btn" id="refreshMetadataBtn" ${!state.selectedFile?"disabled":""}>${icon("file-search")}刷新元数据</button></div><form class="upload-box" id="uploadForm"><div class="field"><label>上传 EEG</label><input type="file" id="uploadInput" accept=".edf,.bdf,.fif,.fif.gz,.vhdr,.set,.cnt" /></div><button class="btn primary" type="submit">${icon("upload")}上传并选中</button></form><p class="message ${state.fileError?"error":""}" id="fileMessage" ${state.fileMessage?"":"hidden"}>${h(state.fileMessage)}</p></section>`;
}

function renderMetadataPanel(){
  const m = state.metadata || {};
  return `<section class="panel"><div class="panel-head"><h2>${icon("database")}元数据概览</h2><span class="badge">${h(m.status || "未加载")}</span></div><div class="meta-grid"><div class="metric"><span>采样率</span><strong>${fmt(m.sampling_rate,1)} Hz</strong></div><div class="metric"><span>时长</span><strong>${fmt(m.duration_sec,1)} s</strong></div><div class="metric"><span>通道数</span><strong>${m.channel_count ?? "-"}</strong></div><div class="metric"><span>事件 / 注释</span><strong>${m.annotation_count ?? 0}</strong></div><div class="metric"><span>EEG 通道</span><strong>${m.eeg_channel_count ?? "-"}</strong></div><div class="metric"><span>高通 / 低通</span><strong>${fmt(m.highpass,1)} / ${fmt(m.lowpass,1)}</strong></div><div class="metric"><span>读取方式</span><strong>${h(m.reader || "-")}</strong></div><div class="metric"><span>MNE 版本</span><strong>${h(m.mne_version || "-")}</strong></div></div>${renderAnnotationSummary()}</section>`;
}

function renderAnnotationSummary(){
  const anns = state.metadata?.annotations_preview || [];
  if(!anns.length) return `<div class="empty">No annotation preview yet. ERP event meaning should be confirmed in the downstream analysis step.</div>`;
  return `<div class="annotation-list"><h3>Annotation review</h3>${anns.slice(0,12).map((ann, index)=>renderAnnotationRow(ann, index)).join("")}</div>`;
}
function annotationKey(ann, index){ return `ann_${index}_${Number(ann.onset || 0).toFixed(3)}_${String(ann.description || "").replace(/\W+/g,"_")}`; }
function renderAnnotationRow(ann, index){
  const key = annotationKey(ann, index);
  const current = state.annotationActions.find((item)=>item.annotation_key===key)?.action || "keep";
  return `<div class="annotation-row"><span>${fmt(ann.onset,2)}s / ${fmt(ann.duration,2)}s / ${h(ann.description)}</span><select class="annotation-action" data-key="${h(key)}" data-onset="${h(ann.onset)}" data-duration="${h(ann.duration)}" data-description="${h(ann.description)}"><option value="keep" ${current==="keep"?"selected":""}>保留</option><option value="ignore" ${current==="ignore"?"selected":""}>忽略</option><option value="bad_segment" ${current==="bad_segment"?"selected":""}>标记为坏段</option></select></div>`;
}

function renderChannelPanel(){
  const channels = metadataChannels();
  const q = state.channelQuery.trim().toLowerCase();
  const typeMap = channelTypeMap();
  const filtered = channels.filter((ch)=>!q || ch.toLowerCase().includes(q)).slice(0,128);
  const selectedCount = state.selectedChannels.length;
  return `<section class="panel"><h2>${icon("list-checks")}通道选择</h2><div class="field"><label>搜索通道</label><input id="channelQuery" value="${h(state.channelQuery)}" placeholder="Fp1 / Cz / EEG" /></div><div class="grid-2"><button class="btn" id="selectFirst64Btn">选择前 64 个</button><button class="btn" id="clearChannelsBtn">清空选择</button></div><p class="hint">已选择 ${selectedCount}/${MAX_PREVIEW_CHANNELS} 个通道。通道类型来自 MNE 元数据，并会保存到数据准备记录。</p><div class="channel-list">${filtered.map((ch)=>`<label class="channel-pill ${state.badChannels.some((b)=>b.channel===ch)?"bad":""}"><input type="checkbox" class="channel-check" value="${h(ch)}" ${state.selectedChannels.includes(ch)?"checked":""} /> <span>${h(ch)}</span><small>${h(typeMap[ch] || "-")}</small></label>`).join("") || `<div class="empty">请先选择文件并读取元数据。</div>`}</div><div class="field"><label>坏道原因</label><select id="badChannelReason"><option value="noisy">噪声大</option><option value="flat">平坦信号</option><option value="high_amplitude">高振幅</option><option value="intermittent">间歇异常</option><option value="other">其他</option></select></div><button class="btn warn" id="markBadChannelsBtn" ${!selectedCount?"disabled":""}>${icon("shield-alert")}标记为坏道</button>${renderBadChannelList()}</section>`;
}
function renderBadChannelList(){
  if(!state.badChannels.length) return `<div class="empty small">暂无坏导。坏导只写入方案，不删除原始通道。</div>`;
  return `<div class="tag-list">${state.badChannels.map((item)=>`<span class="tag bad">${h(item.channel)} / ${h(item.reason)} <button class="remove-bad-channel" data-channel="${h(item.channel)}">移除</button></span>`).join("")}</div>`;
}

function renderPrepPanel(){
  return `<section class="panel"><h2>${icon("sliders-horizontal")}公共准备</h2><div class="field"><label>显示方式</label><select id="displayMode"><option value="raw" ${state.viewport.mode==="raw"?"selected":""}>原始</option><option value="filtered" ${state.viewport.mode==="filtered"?"selected":""}>滤波后</option><option value="overlay" ${state.viewport.mode==="overlay"?"selected":""}>叠加</option><option value="stacked" ${state.viewport.mode==="stacked"?"selected":""}>上下对比</option></select></div><div class="checks"><label class="check"><input type="checkbox" id="filterEnabled" ${state.filterPreview.enabled?"checked":""}/> 启用滤波预览</label><label class="check"><input type="checkbox" id="bandpassEnabled" ${state.filterPreview.bandpass.enabled?"checked":""}/> 带通</label><label class="check"><input type="checkbox" id="notchEnabled" ${state.filterPreview.notch.enabled?"checked":""}/> 陷波</label></div><div class="grid-2"><div class="field"><label>低切 Hz</label><input type="number" step="0.1" id="lFreq" value="${h(state.filterPreview.bandpass.l_freq)}" /></div><div class="field"><label>高切 Hz</label><input type="number" step="0.1" id="hFreq" value="${h(state.filterPreview.bandpass.h_freq)}" /></div><div class="field"><label>陷波 Hz</label><select id="notchFreq"><option value="50" ${notchFreq()===50?"selected":""}>50</option><option value="60" ${notchFreq()===60?"selected":""}>60</option></select></div><div class="field"><label>纵向缩放 uV</label><input type="number" step="10" id="verticalScale" value="${h(state.viewport.verticalScaleUv)}" /></div></div><p class="notice">滤波只用于当前窗口预览，不修改原始文件，也不会自动成为 PSD/ERP 的正式滤波参数。</p></section>`;
}
function notchFreq(){ return Number(state.filterPreview.notch.freqs?.[0] || 50); }

function renderWaveformPanel(){
  return `<section class="panel waveform-panel"><div class="panel-head"><h2>${icon("waves")}波形操作窗口</h2><span class="badge">${state.selectedChannels.length || Math.min(8, metadataChannels().length)} / ${MAX_PREVIEW_CHANNELS} 通道</span></div><div class="toolbar"><button class="btn" id="prevWindowBtn">${icon("chevron-left")}上一段</button><button class="btn" id="nextWindowBtn">下一段${icon("chevron-right")}</button><button class="btn" id="zoomInBtn">${icon("zoom-in")}缩短窗口</button><button class="btn" id="zoomOutBtn">${icon("zoom-out")}拉长窗口</button><button class="btn primary" id="runPreviewBtn2">${icon("activity")}刷新真实波形</button></div><div class="grid-4"><div class="field"><label>开始秒</label><input type="number" step="0.5" id="startSec" value="${h(state.viewport.startSec)}" /></div><div class="field"><label>窗口秒</label><input type="number" step="1" max="${MAX_PREVIEW_DURATION_SEC}" id="durationSec" value="${h(state.viewport.durationSec)}" /></div><div class="field"><label>显示采样率</label><input type="number" step="10" id="displaySfreq" value="${h(state.viewport.displaySfreq)}" /></div><div class="field"><label>坏段结束秒</label><input type="number" step="0.1" id="badSegmentEnd" value="${h(state.pendingBadSegment.endSec)}" /></div></div><p class="message ${state.runError?"error":""}" id="runMessage" ${state.runMessage?"":"hidden"}>${h(state.runMessage)}</p>${renderFigureTabs()}${renderBadSegmentTools()}</section>`;
}
function renderFigureTabs(){
  const fig = byLabel(state.activeFigure) || byLabel("filter_preview_figure") || byLabel("raw_preview_figure");
  if(!state.artifacts.length) return `<div class="figure-frame empty">点击刷新后，将从真实 EEG 数据生成当前窗口波形。</div>`;
  return `<div class="figure-tabs"><button class="btn ${state.activeFigure==="raw_preview_figure"?"primary":""}" data-figure="raw_preview_figure">Raw waveform</button><button class="btn ${state.activeFigure==="filter_preview_figure"?"primary":""}" data-figure="filter_preview_figure">Filter preview</button><button class="btn ${state.activeFigure==="snapshot_figure"?"primary":""}" data-figure="snapshot_figure">Segment figure</button></div><div class="figure-frame">${fig ? `<img src="${h(artifactUrl(fig))}" alt="QC waveform preview" />` : `<div class="empty">This task did not generate that figure.</div>`}</div>${renderArtifactGrid()}`;
}
function renderArtifactGrid(){
  return `<div class="artifact-grid">${state.artifacts.map((item, index)=>`<a class="artifact" href="${h(artifactUrl(item))}" target="_blank" rel="noreferrer"><span>复核文件</span><strong>${h(item.label || `结果 ${index + 1}`)}</strong><small>打开记录</small></a>`).join("")}</div>`;
}
function renderBadSegmentTools(){
  const reasonOptions = [["eye_blink","Eye blink"],["movement","Movement"],["muscle_artifact","Muscle noise"],["electrode_pop","Electrode pop"],["saturation","Saturation"],["external_noise","External noise"],["discontinuity","Discontinuity"],["other","Other"]].map(([value,label])=>`<option value="${value}" ${state.pendingBadSegment.reason===value?"selected":""}>${label}</option>`).join("");
  return `<div class="bad-segment-box"><h3>坏段标记</h3><p>输入当前窗口内的起止时间。保存只写入数据准备记录，不会裁剪原始 EEG。</p><div class="grid-4"><div class="field"><label>开始</label><input type="number" step="0.1" id="badSegmentStart" value="${h(state.pendingBadSegment.startSec)}" /></div><div class="field"><label>结束</label><input type="number" step="0.1" id="badSegmentEnd2" value="${h(state.pendingBadSegment.endSec)}" /></div><div class="field"><label>原因</label><select id="badSegmentReason">${reasonOptions}</select></div><div class="field"><label>备注</label><input id="badSegmentNote" value="${h(state.pendingBadSegment.note)}" /></div></div><button class="btn warn" id="addBadSegmentBtn">${icon("square-dashed-mouse-pointer")}标记坏段</button>${renderBadSegmentList()}</div>`;
}
function renderBadSegmentList(){
  if(!state.badSegments.length) return `<div class="empty small">No bad segment yet. Bad segments are saved to the plan and never cut the source EEG.</div>`;
  return `<div class="segment-list small-list">${state.badSegments.map((seg)=>`<div class="segment-row"><span>${fmt(seg.start_sec,2)}s - ${fmt(seg.end_sec,2)}s / ${h(seg.reason)}</span><button class="btn remove-bad-segment" data-id="${h(seg.id)}">Remove</button></div>`).join("")}</div>`;
}

function renderSegmentsPanel(){
  const tagOptions = Object.entries(SEGMENT_TAG_LABELS).map(([value,label]) => `<option value="${h(value)}" ${state.segmentDraft.tag===value?"selected":""}>${h(label)}</option>`).join("");
  return `<section class="panel"><div class="panel-head"><h2>${icon("bookmark")}预览片段</h2><button class="btn primary" id="saveSegmentBtn">${icon("bookmark-plus")}保存当前片段</button></div><div class="segment-form"><div class="grid-2"><div class="field"><label>片段名称</label><input id="segmentName" value="${h(state.segmentDraft.name)}" /></div><div class="field"><label>标签</label><select id="segmentTag">${tagOptions}</select></div></div><div class="field"><label>备注</label><input id="segmentNote" value="${h(state.segmentDraft.note)}" placeholder="例如：Fp1 噪声复核，保存当前窗口作为依据。" /></div><label class="check"><input type="checkbox" id="segmentIncludeReport" ${state.segmentDraft.includeInReport?"checked":""}/> 纳入结果依据</label></div>${state.savedPreviewSegments.length ? `<div class="segment-list">${state.savedPreviewSegments.map(renderSavedSegment).join("")}</div>` : `<div class="empty">还没有保存片段。保存后可以恢复窗口并下载复现文件。</div>`}</section>`;
}
function renderSavedSegment(seg){
  return `<article class="segment-card ${state.activePreviewSegmentId===seg.id?"active":""}"><div><strong>${h(seg.name)}</strong><p>${fmt(seg.preview.startSec,2)}s / ${fmt(seg.preview.durationSec,2)}s / ${seg.preview.channels.length} channels / ${h(seg.preview.mode)}</p><small>${h(seg.note || "")}</small></div><div class="segment-actions"><button class="btn restore-segment" data-id="${h(seg.id)}">Restore window</button><button class="btn download-segment" data-id="${h(seg.id)}">Download JSON</button><button class="btn download-segment-svg" data-id="${h(seg.id)}">Download SVG</button><button class="btn warn delete-segment" data-id="${h(seg.id)}">Delete</button></div></article>`;
}

function renderPlanGatePanel(){
  const gate = planGateState();
  const planText = gate.confirmed ? "已确认方案" : "草稿方案";
  const revisionText = gate.revision ? `第 ${gate.revision} 版` : "未生成版本";
  const fileText = gate.fileId || "No file selected";
  const psdText = gate.psdReady ? "PSD can use this plan." : "PSD must wait for a confirmed plan and bad-channel review.";
  const erpText = gate.erpReady ? "ERP can use this plan after ERP event meaning review." : "ERP must wait for a confirmed plan and usable events/annotations.";
  return `<section class="panel plan-gate" data-qc-gate-panel data-plan-status="${h(gate.status)}" data-plan-confirmed="${gate.confirmed ? "true" : "false"}" data-plan-revision="${h(gate.revision)}" data-file-id="${h(gate.fileId)}" data-psd-ready="${gate.psdReady ? "true" : "false"}" data-erp-ready="${gate.erpReady ? "true" : "false"}"><div class="panel-head"><h2>${icon(gate.confirmed ? "badge-check" : "file-clock")}数据准备状态</h2><span class="badge ${gate.confirmed ? "ok" : "warn"}">${h(planText)}</span></div><div class="gate-grid"><div class="metric"><span>当前文件</span><strong>${h(fileText)}</strong></div><div class="metric"><span>准备状态</span><strong>${h(planText)}</strong></div><div class="metric"><span>记录版本</span><strong>${h(revisionText)}</strong></div><div class="metric"><span>记录状态</span><strong>${h(gate.planId ? "已保存" : "未保存")}</strong></div></div><div class="quality-grid"><div class="quality-card ${gate.psdReady ? "ok" : "warn"}"><strong>PSD 准备</strong><span>${h(psdText)}</span></div><div class="quality-card ${gate.erpReady ? "ok" : "warn"}"><strong>ERP 准备</strong><span>${h(erpText)}</span></div><div class="quality-card warn"><strong>滤波预览</strong><span>带通和陷波只影响当前预览窗口，不会自动成为 PSD/ERP 的正式分析参数。</span></div><div class="quality-card warn"><strong>片段记录</strong><span>保存的片段会写入数据准备记录，原始 EEG 不会被裁剪。</span></div></div></section>`;
}

function renderLegacyQualityPanel(){
  const psdBlocked = state.badChannels.length > Math.max(6, metadataChannels().length * 0.25);
  return `<section class="panel"><h2>${icon("check-circle-2")}质量与下一步</h2><div class="quality-grid"><div class="quality-card ${psdBlocked?"warn":"ok"}"><strong>PSD</strong><span>${psdBlocked?"请先复核坏导数量":"可继续；PSD 专属频谱参数在 PSD 页面确认"}</span></div><div class="quality-card ${(state.metadata?.annotation_count||0)?"ok":"warn"}"><strong>ERP</strong><span>${(state.metadata?.annotation_count||0)?"已有 annotations；事件含义仍在 ERP 页面确认":"缺少 events/annotations，ERP 需要事件确认"}</span></div><div class="quality-card warn"><strong>TFR / PAC / Connectivity</strong><span>预览 / 即将开放；当前页不承诺正式执行。</span></div></div><pre class="plan-preview">${h(JSON.stringify(buildPreparationPlan(), null, 2))}</pre></section>`;
}

function renderQualityPanel(){
  const psdBlocked = state.badChannels.length > Math.max(6, metadataChannels().length * 0.25);
  const planConfirmed = state.plan?.status === "confirmed" && !state.plan?.is_default;
  return `<section class="panel"><h2>${icon("check-circle-2")}质量检查</h2><div class="quality-grid"><div class="quality-card ${planConfirmed?"ok":"warn"}"><strong>数据准备</strong><span>${planConfirmed ? `已确认第 ${h(state.plan.revision)} 版` : "请先保存并确认数据准备方案，再进入正式分析。"}</span></div><div class="quality-card ${psdBlocked?"warn":"ok"}"><strong>PSD</strong><span>${psdBlocked?"请先查看坏道数量。":"数据准备确认后可继续；PSD 频谱参数在 PSD 分析中确认。"}</span></div><div class="quality-card ${(state.metadata?.annotation_count||0)?"ok":"warn"}"><strong>ERP</strong><span>${(state.metadata?.annotation_count||0)?"已有事件或注释；事件含义仍需在 ERP 分析中确认。":"缺少事件或注释，ERP 需要先确认事件。"} </span></div><div class="quality-card warn"><strong>TFR / PAC / Connectivity</strong><span>这些高级方法需要事件、频段和解释边界记录；请先完成数据准备。</span></div></div><pre class="plan-preview">${h(JSON.stringify(buildPreparationPlan(), null, 2))}</pre></section>`;
}

function bindEvents(){
  document.querySelector("#refreshFilesBtn")?.addEventListener("click", loadFiles);
  document.querySelector("#refreshMetadataBtn")?.addEventListener("click", ()=>loadMetadata(state.selectedFile));
  document.querySelector("#fileSelect")?.addEventListener("change", (event)=>selectFile(event.target.value));
  document.querySelector("#uploadForm")?.addEventListener("submit", uploadFile);
  document.querySelectorAll("#runPreviewBtn,#runPreviewBtn2").forEach((btn)=>btn.addEventListener("click", runPreview));
  document.querySelectorAll("#saveSegmentBtn,#saveSegmentTopBtn").forEach((btn)=>btn.addEventListener("click", savePreviewSegment));
  document.querySelector("#savePlanBtn")?.addEventListener("click", ()=>savePreparationPlan("draft"));
  document.querySelector("#confirmPlanBtn")?.addEventListener("click", ()=>savePreparationPlan("confirmed"));
  document.querySelector("#downloadPlanBtn")?.addEventListener("click", downloadPlan);
  document.querySelector("#channelQuery")?.addEventListener("input", (event)=>{ state.channelQuery=event.target.value; render(); });
  document.querySelector("#selectFirst64Btn")?.addEventListener("click", ()=>{ state.selectedChannels = metadataChannels().slice(0, MAX_PREVIEW_CHANNELS); markDirty(); render(); });
  document.querySelector("#clearChannelsBtn")?.addEventListener("click", ()=>{ state.selectedChannels = []; markDirty(); render(); });
  document.querySelectorAll(".channel-check").forEach((input)=>input.addEventListener("change", onChannelToggle));
  document.querySelector("#markBadChannelsBtn")?.addEventListener("click", markSelectedBadChannels);
  document.querySelectorAll(".remove-bad-channel").forEach((btn)=>btn.addEventListener("click", ()=>{ state.badChannels = state.badChannels.filter((item)=>item.channel!==btn.dataset.channel); markDirty(); render(); }));
  document.querySelectorAll(".figure-tabs .btn").forEach((btn)=>btn.addEventListener("click", ()=>{ state.activeFigure=btn.dataset.figure; render(); }));
  bindViewportControls();
  bindPrepControls();
  bindSegmentControls();
  bindAnnotationControls();
}

function bindViewportControls(){
  const setViewport = (key, value)=>{ state.viewport[key] = Number(value); markDirty(); };
  document.querySelector("#startSec")?.addEventListener("change", (e)=>{ setViewport("startSec", Math.max(0, e.target.value)); render(); });
  document.querySelector("#durationSec")?.addEventListener("change", (e)=>{ setViewport("durationSec", Math.min(MAX_PREVIEW_DURATION_SEC, Math.max(1, Number(e.target.value)))); render(); });
  document.querySelector("#displaySfreq")?.addEventListener("change", (e)=>{ setViewport("displaySfreq", Math.max(1, e.target.value)); render(); });
  document.querySelector("#verticalScale")?.addEventListener("change", (e)=>{ setViewport("verticalScaleUv", Math.max(1, e.target.value)); render(); });
  document.querySelector("#displayMode")?.addEventListener("change", (e)=>{ state.viewport.mode=e.target.value; markDirty(); render(); });
  document.querySelector("#prevWindowBtn")?.addEventListener("click", ()=>{ state.viewport.startSec = Math.max(0, Number(state.viewport.startSec)-Number(state.viewport.durationSec)); markDirty(); render(); });
  document.querySelector("#nextWindowBtn")?.addEventListener("click", ()=>{ state.viewport.startSec = Math.min(Math.max(0,(state.metadata?.duration_sec||9999)-state.viewport.durationSec), Number(state.viewport.startSec)+Number(state.viewport.durationSec)); markDirty(); render(); });
  document.querySelector("#zoomInBtn")?.addEventListener("click", ()=>{ state.viewport.durationSec = Math.max(1, Number(state.viewport.durationSec)/2); markDirty(); render(); });
  document.querySelector("#zoomOutBtn")?.addEventListener("click", ()=>{ state.viewport.durationSec = Math.min(MAX_PREVIEW_DURATION_SEC, Number(state.viewport.durationSec)*2); markDirty(); render(); });
  ["badSegmentStart","badSegmentEnd","badSegmentEnd2","badSegmentReason","badSegmentNote"].forEach((id)=>document.querySelector(`#${id}`)?.addEventListener("change", updatePendingBadSegment));
  document.querySelector("#addBadSegmentBtn")?.addEventListener("click", addBadSegment);
  document.querySelectorAll(".remove-bad-segment").forEach((btn)=>btn.addEventListener("click", ()=>{ state.badSegments = state.badSegments.filter((item)=>item.id!==btn.dataset.id); markDirty(); render(); }));
}
function bindPrepControls(){
  document.querySelector("#filterEnabled")?.addEventListener("change", (e)=>{ state.filterPreview.enabled=e.target.checked; markDirty(); render(); });
  document.querySelector("#bandpassEnabled")?.addEventListener("change", (e)=>{ state.filterPreview.bandpass.enabled=e.target.checked; markDirty(); render(); });
  document.querySelector("#notchEnabled")?.addEventListener("change", (e)=>{ state.filterPreview.notch.enabled=e.target.checked; markDirty(); render(); });
  document.querySelector("#lFreq")?.addEventListener("change", (e)=>{ state.filterPreview.bandpass.l_freq=Number(e.target.value); markDirty(); });
  document.querySelector("#hFreq")?.addEventListener("change", (e)=>{ state.filterPreview.bandpass.h_freq=Number(e.target.value); markDirty(); });
  document.querySelector("#notchFreq")?.addEventListener("change", (e)=>{ state.filterPreview.notch.freqs=[Number(e.target.value)]; markDirty(); });
}
function bindSegmentControls(){
  document.querySelector("#segmentName")?.addEventListener("input", (e)=>{ state.segmentDraft.name=e.target.value; });
  document.querySelector("#segmentNote")?.addEventListener("input", (e)=>{ state.segmentDraft.note=e.target.value; });
  document.querySelector("#segmentTag")?.addEventListener("change", (e)=>{ state.segmentDraft.tags=[e.target.value]; });
  document.querySelector("#segmentIncludeReport")?.addEventListener("change", (e)=>{ state.segmentDraft.includeInReport=e.target.checked; });
  document.querySelectorAll(".restore-segment").forEach((btn)=>btn.addEventListener("click", ()=>restoreSegment(btn.dataset.id)));
  document.querySelectorAll(".download-segment").forEach((btn)=>btn.addEventListener("click", ()=>downloadSegment(btn.dataset.id, "json")));
  document.querySelectorAll(".download-segment-svg").forEach((btn)=>btn.addEventListener("click", ()=>downloadSegment(btn.dataset.id, "svg")));
  document.querySelectorAll(".delete-segment").forEach((btn)=>btn.addEventListener("click", ()=>deleteSegment(btn.dataset.id)));
}
function bindAnnotationControls(){
  document.querySelectorAll(".annotation-action").forEach((select)=>select.addEventListener("change", ()=>{
    const item = { annotation_key: select.dataset.key, onset_sec: Number(select.dataset.onset), duration_sec: Number(select.dataset.duration), description: select.dataset.description, action: select.value };
    state.annotationActions = state.annotationActions.filter((row)=>row.annotation_key!==item.annotation_key);
    state.annotationActions.push(item);
    if(item.action === "bad_segment"){
      state.badSegments.push({ id: uid("badseg"), start_sec: item.onset_sec, end_sec: item.onset_sec + item.duration_sec, reason: "annotation", note: item.description });
    }
    markDirty(); render();
  }));
}

async function loadFiles(){
  try{
    state.files = await request("/eeg/files");
    if(!state.selectedFile && state.files.length) state.selectedFile = state.files[0].id;
    loadLocalSegments();
    if(state.selectedFile) await loadMetadata(state.selectedFile, false);
    setMessage("fileMessage", `Loaded ${state.files.length} EEG files.`);
  }catch(error){ setMessage("fileMessage", `Failed to load files: ${error.message}`, true); }
  render();
}
async function selectFile(fileId){
  state.selectedFile = fileId;
  state.metadata = null; state.task = null; state.artifacts = []; state.selectedChannels = []; state.badChannels = []; state.badSegments = []; state.annotationActions = []; state.unsavedChanges=false;
  loadLocalSegments();
  if(fileId) await loadMetadata(fileId);
  render();
}
async function loadMetadata(fileId = state.selectedFile, doRender = true){
  if(!fileId) return;
  try{
    state.metadata = await request(`/eeg/files/${fileId}/metadata`);
    if(!state.selectedChannels.length) state.selectedChannels = (state.metadata.channel_names || []).slice(0, Math.min(8, MAX_PREVIEW_CHANNELS));
    state.pendingBadSegment.startSec = Number(state.viewport.startSec) || 0;
    state.pendingBadSegment.endSec = Math.min((state.metadata.duration_sec || 2), state.pendingBadSegment.startSec + 2);
    setMessage("fileMessage", "Metadata refreshed.");
    await loadPreparationPlan(fileId);
  }catch(error){ setMessage("fileMessage", `Metadata load failed: ${error.message}`, true); }
  if(doRender) render();
}
async function uploadFile(event){
  event.preventDefault();
  const input = document.querySelector("#uploadInput");
  const file = input?.files?.[0];
  if(!file){ setMessage("fileMessage", "Please choose an EEG file.", true); return; }
  try{
    setMessage("fileMessage", "Uploading file...");
    const project = state.project || await ensureProject();
    const form = new FormData(); form.append("file", file);
    const uploaded = await request(`/eeg/upload?project_id=${encodeURIComponent(project.id)}`, { method:"POST", body: form });
    state.files.unshift(uploaded); state.selectedFile = uploaded.id; state.metadata = null; state.selectedChannels = [];
    loadLocalSegments();
    await loadMetadata(uploaded.id, false);
    setMessage("fileMessage", `Uploaded and selected: ${uploaded.original_filename}`);
  }catch(error){ setMessage("fileMessage", `Upload failed: ${error.message}`, true); }
  render();
}
async function ensureProject(){
  if(state.project) return state.project;
  state.project = await request("/projects", { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({ name:"QC data preparation experience", description:"QC common data preparation workspace" }) });
  return state.project;
}

function collectParameters(){
  const channels = state.selectedChannels.slice(0, MAX_PREVIEW_CHANNELS);
  return {
    ...currentPlanReference(),
    preview: { start_sec:Number(state.viewport.startSec), duration_sec:Number(state.viewport.durationSec), channels, channel_limit:MAX_PREVIEW_CHANNELS, display_sfreq:Number(state.viewport.displaySfreq), vertical_scale_uv:Number(state.viewport.verticalScaleUv), show_annotations:true, show_events:true, display_mode:state.viewport.mode },
    filter_preview: { enabled:state.filterPreview.enabled, bandpass:{...state.filterPreview.bandpass, method:"fir"}, notch:{...state.filterPreview.notch, method:"fir"}, compare_mode:state.viewport.mode, apply_to:"preview_window_only", edge_policy:{ pad_before_sec:2, pad_after_sec:2, trim_to_requested_window:true } },
    snapshot: { enabled:true, label:state.segmentDraft.name || "QC preview segment", format:"svg", include_raw:true, include_filtered_preview:true, include_annotations:true, include_parameter_badge:true },
    bad_channels: state.badChannels,
    bad_segments: state.badSegments,
    annotation_actions: state.annotationActions,
  };
}
async function runPreview(){
  if(!state.selectedFile){ setMessage("runMessage","Please select a file first.", true); return; }
  try{
    setMessage("runMessage","Requesting real EEG window from the backend...");
    const file = selectedFile();
    const projectId = file.project_id || (await ensureProject()).id;
    const task = await request("/tasks", { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({ project_id:projectId, module_name:"qc", workflow_id:"qc_waveform_preview", input_file_id:file.id, parameters_json:collectParameters() }) });
    state.task = task;
    state.artifacts = await request(`/tasks/${task.id}/artifacts`);
    state.activeFigure = byLabel("filter_preview_figure") ? "filter_preview_figure" : "raw_preview_figure";
    setMessage("runMessage", `后端预览已完成：已生成 ${state.artifacts.length} 个复核文件，技术编号已放入复现详情。`);
  }catch(error){ setMessage("runMessage", `预览失败：${error.message}`, true); }
  render();
}

async function loadPreparationPlan(fileId = state.selectedFile){
  const file = state.files.find((item)=>item.id===fileId);
  if(!file?.project_id) return;
  try{
    state.plan = await request(`/eeg/files/${encodeURIComponent(file.id)}/data-preparation-plan`);
    if(Array.isArray(state.plan?.saved_preview_segments) && state.plan.saved_preview_segments.length){
      state.savedPreviewSegments = state.plan.saved_preview_segments.map((item)=>({
        ...item,
        id: item.id || item.segment_id || uid("seg"),
        preview: item.preview || {
          startSec: item.start_sec || state.viewport.startSec,
          durationSec: item.duration_sec || state.viewport.durationSec,
          channels: item.channels || [],
          verticalScaleUv: state.viewport.verticalScaleUv,
          displaySfreq: item.display_sfreq || state.viewport.displaySfreq,
          mode: item.display_mode || state.viewport.mode,
        },
      }));
    }
  }catch(error){
    state.plan = null;
  }
}

function buildPlanApiPayload(status = "draft"){
  const plan = buildPreparationPlan();
  return {
    project_id: plan.project_id,
    module_scope: ["qc", "psd", "erp"],
    title: "QC common data preparation",
    description: "Shared QC decisions for downstream analysis.",
    status,
    preprocessing_json: plan.filter_preview || {},
    qc_json: {
      schema_version: plan.schema_version,
      metadata_review: plan.metadata_review,
      viewport: plan.viewport,
      selected_channels: plan.selected_channels,
      bad_channels: plan.bad_channels,
      bad_segments: plan.bad_segments,
      annotation_actions: plan.annotation_actions,
      saved_preview_segments: plan.saved_preview_segments,
      next_step_recommendation: plan.next_step_recommendation,
      confirmed_at: status === "confirmed" ? new Date().toISOString() : null,
    },
    psd_json: {},
    artifact_contract_json: {
      source: "qc_common_data_preparation",
      preview_only_filtering: true,
      max_preview_channels: MAX_PREVIEW_CHANNELS,
    },
  };
}

async function savePreparationPlan(status = "draft"){
  if(!state.selectedFile){ setMessage("runMessage", "Please select a file first.", true); return; }
  const file = selectedFile();
  if(!file?.project_id){ setMessage("runMessage", "This file is missing a project id. Please upload or select a project file first.", true); return; }
  try{
    setMessage("runMessage", status === "confirmed" ? "正在确认当前数据准备方案……" : "正在保存数据准备草稿……");
    const payload = buildPlanApiPayload(status);
    const baseRevision = Number.isFinite(Number(state.plan?.revision)) ? Number(state.plan.revision) : 0;
    state.plan = await request(`/eeg/files/${encodeURIComponent(file.id)}/data-preparation-plan`, {
      method: "POST",
      headers:{"Content-Type":"application/json"},
      body: JSON.stringify({ ...payload, base_revision: baseRevision }),
    });
    state.unsavedChanges = false;
    setMessage("runMessage", "数据准备方案已保存。");
  }catch(error){
    setMessage("runMessage", `Plan save failed: ${error.message}. You can still download JSON for review.`, true);
  }
  render();
}

function onChannelToggle(event){
  const ch = event.target.value;
  if(event.target.checked){
    if(state.selectedChannels.length >= MAX_PREVIEW_CHANNELS){ event.target.checked = false; setMessage("runMessage", `No more than ${MAX_PREVIEW_CHANNELS} channels are allowed.`, true); return; }
    if(!state.selectedChannels.includes(ch)) state.selectedChannels.push(ch);
  } else {
    state.selectedChannels = state.selectedChannels.filter((item)=>item!==ch);
  }
  markDirty(); render();
}
function markSelectedBadChannels(){
  const reason = document.querySelector("#badChannelReason")?.value || "other";
  const now = new Date().toISOString();
  const existing = new Set(state.badChannels.map((item)=>item.channel));
  state.selectedChannels.forEach((channel)=>{ if(!existing.has(channel)) state.badChannels.push({ channel, reason, created_at: now, source:"manual" }); });
  markDirty(); render();
}
function updatePendingBadSegment(){
  const start = Number(document.querySelector("#badSegmentStart")?.value ?? state.pendingBadSegment.startSec);
  const end = Number(document.querySelector("#badSegmentEnd2")?.value ?? document.querySelector("#badSegmentEnd")?.value ?? state.pendingBadSegment.endSec);
  state.pendingBadSegment = { startSec:start, endSec:end, reason:document.querySelector("#badSegmentReason")?.value || state.pendingBadSegment.reason, note:document.querySelector("#badSegmentNote")?.value || "" };
}
function addBadSegment(){
  updatePendingBadSegment();
  const { startSec, endSec, reason, note } = state.pendingBadSegment;
  if(!(endSec > startSec)){ setMessage("runMessage", "Bad segment end must be greater than start.", true); return; }
  state.badSegments.push({ id:uid("badseg"), start_sec:startSec, end_sec:endSec, reason, note, source:"manual" });
  markDirty(); render();
}

function buildPreparationPlan(){
  const file = selectedFile();
  const persistedReference = currentPlanReference();
  return {
    schema_version:"qlanalyser-data-preparation-v0.2",
    plan_save_status: state.plan?.is_default ? "default_draft" : (state.plan ? "saved" : "local_edit"),
    plan_id: persistedReference.data_preparation_plan_id || null,
    revision: Number.isFinite(Number(state.plan?.revision)) ? Number(state.plan.revision) : 0,
    input_file_id:state.selectedFile,
    project_id:file?.project_id || "",
    scope:"common_qc_preparation",
    status:state.plan?.status || "draft",
    source_file:{ file_id:state.selectedFile, filename:file?.original_filename, format:state.metadata?.format, reader:state.metadata?.reader, mne_version:state.metadata?.mne_version },
    metadata_review:{ sfreq:state.metadata?.sampling_rate, duration_sec:state.metadata?.duration_sec, n_channels:state.metadata?.channel_count, n_eeg_channels:state.metadata?.eeg_channel_count, annotations_count:state.metadata?.annotation_count, highpass:state.metadata?.highpass, lowpass:state.metadata?.lowpass, channel_types_confirmed:false },
    viewport:state.viewport,
    selected_channels:state.selectedChannels,
    channel_types:{ detected:channelTypeMap(), confirmed:false },
    channel_renames:{ items:{}, confirmed:false },
    unit_review:{ status:"needs_review", note:"This draft only reminds the user to review amplitude and unit; it does not auto-convert units." },
    filter_preview:{ ...state.filterPreview, preview_only:true, edge_policy:{ pad_before_sec:2, pad_after_sec:2, trim_to_requested_window:true } },
    bad_channels:state.badChannels,
    bad_segments:state.badSegments,
    annotation_actions:state.annotationActions,
    saved_preview_segments:state.savedPreviewSegments.map(({svg, ...item})=>item),
    next_step_recommendation:{ psd:{status:state.badChannels.length>Math.max(6, metadataChannels().length*0.25)?"needs_review":"allowed", reasons:[]}, erp:{status:(state.metadata?.annotation_count||0)?"needs_event_confirmation":"needs_events", reasons:(state.metadata?.annotation_count||0)?["events_must_be_confirmed_in_erp"]:["events_not_confirmed"]}, tfr:{status:"planned", reasons:["module_not_enabled_in_v0.1"]} },
    warnings:["Filtering is preview-only for the current window. It never modifies the source file or becomes the formal PSD/ERP filter automatically.", "片段证据会随数据准备方案保存；后续接入共享后端片段 API 后可跨设备复用。"],
    updated_at:new Date().toISOString(),
  };
}
function savePreviewSegment(){
  if(!state.selectedFile){ setMessage("runMessage", "Please select a file first.", true); return; }
  const planReference = currentPlanReference();
  const segment = {
    id:uid("seg"), name:state.segmentDraft.name || "当前预览片段", note:state.segmentDraft.note || "", tags:state.segmentDraft.tags, include_in_report:state.segmentDraft.includeInReport, created_at:new Date().toISOString(),
    source_task_reference:state.task?.id || null,
    evidence_type:"current_preview_segment",
    persistence_status:"local_until_backend_preview_segments_api",
    plan_id:planReference.data_preparation_plan_id || null,
    plan_revision:planReference.data_preparation_revision || null,
    preview:{ startSec:Number(state.viewport.startSec), durationSec:Number(state.viewport.durationSec), channels:[...state.selectedChannels], verticalScaleUv:Number(state.viewport.verticalScaleUv), displaySfreq:Number(state.viewport.displaySfreq), mode:state.viewport.mode },
    filter_preview:JSON.parse(JSON.stringify(state.filterPreview)), bad_channels:JSON.parse(JSON.stringify(state.badChannels)), bad_segments:JSON.parse(JSON.stringify(state.badSegments)), annotation_actions:JSON.parse(JSON.stringify(state.annotationActions)), artifacts:state.artifacts.map((a)=>({ id:a.id, label:a.label, artifact_type:a.artifact_type })), plan_save_status:state.plan?.is_default ? "default_draft" : (state.plan ? "saved" : "local_edit"),
  };
  segment.svg = buildSegmentSvg(segment);
  state.savedPreviewSegments.unshift(segment);
  state.activePreviewSegmentId = segment.id;
  state.unsavedChanges = true;
  persistLocalSegments();
  setMessage("runMessage", "当前预览片段已保存，并会纳入下一次数据准备方案。");
  render();
}
function restoreSegment(id){
  const seg = state.savedPreviewSegments.find((item)=>item.id===id); if(!seg) return;
  state.viewport = { ...state.viewport, startSec:seg.preview.startSec, durationSec:seg.preview.durationSec, verticalScaleUv:seg.preview.verticalScaleUv, displaySfreq:seg.preview.displaySfreq, mode:seg.preview.mode };
  state.selectedChannels = seg.preview.channels.slice(0, MAX_PREVIEW_CHANNELS);
  state.badChannels = JSON.parse(JSON.stringify(seg.bad_channels || [])); state.badSegments = JSON.parse(JSON.stringify(seg.bad_segments || [])); state.annotationActions = JSON.parse(JSON.stringify(seg.annotation_actions || [])); state.filterPreview = JSON.parse(JSON.stringify(seg.filter_preview || state.filterPreview)); state.activePreviewSegmentId = id; render();
}
function deleteSegment(id){ state.savedPreviewSegments = state.savedPreviewSegments.filter((item)=>item.id!==id); persistLocalSegments(); markDirty(); render(); }
function downloadSegment(id, type){ const seg=state.savedPreviewSegments.find((item)=>item.id===id); if(!seg) return; if(type==="svg") downloadBlob(`${seg.id}.svg`, seg.svg || buildSegmentSvg(seg), "image/svg+xml"); else downloadBlob(`${seg.id}.json`, JSON.stringify(seg, null, 2), "application/json"); }
function downloadPlan(){ downloadBlob("data_preparation_plan.json", JSON.stringify(buildPreparationPlan(), null, 2), "application/json"); }
function downloadBlob(filename, content, type){ const blob=new Blob([content],{type}); const url=URL.createObjectURL(blob); const a=document.createElement("a"); a.href=url; a.download=filename; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url); }
function buildSegmentSvg(seg){
  const width=980, height=260; const channels=seg.preview.channels.slice(0,12); const rowH=Math.max(14, Math.floor((height-92)/Math.max(1,channels.length)));
  const rows=channels.map((ch,i)=>`<text x="24" y="${84+i*rowH}" class="label">${h(ch)}</text><line x1="130" y1="${80+i*rowH}" x2="940" y2="${80+i*rowH}" class="baseline"/>`).join("");
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}"><style>.title{font:700 20px system-ui;fill:#10242c}.label,.note{font:600 12px system-ui;fill:#5d6e78}.baseline{stroke:#dbe7ea}.flag{fill:#147d78}</style><rect width="100%" height="100%" fill="#fff"/><text x="24" y="34" class="title">${h(seg.name)}</text><text x="24" y="56" class="note">${fmt(seg.preview.startSec,2)}s - ${fmt(seg.preview.startSec+seg.preview.durationSec,2)}s / ${seg.preview.channels.length} channels / 仅预览滤波</text>${rows}<rect x="130" y="${height-34}" width="220" height="8" class="flag"/><text x="360" y="${height-26}" class="note">预览片段证据图；正式波形来自后端生成的 SVG。</text></svg>`;
}

function setMessage(id, text, error=false){
  if(id === "fileMessage") { state.fileMessage = text; state.fileError = Boolean(error); }
  if(id === "runMessage") { state.runMessage = text; state.runError = Boolean(error); }
  const el=document.querySelector(`#${id}`);
  if(!el) return;
  el.hidden=false; el.textContent=text; el.classList.toggle("error", Boolean(error));
}

render();
loadFiles();
