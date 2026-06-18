const DEFAULT_API_BASE = ["localhost", "127.0.0.1"].includes(window.location.hostname) ? "http://127.0.0.1:8000/api" : "/api";
const params = new URLSearchParams(window.location.search);
const API_BASE = params.get("api") || DEFAULT_API_BASE;
const state = { project: null, files: [], selectedFile: "", metadata: null, task: null, artifacts: [], activeFigure: "raw_preview_figure", fileMessage: "", fileError: false, runMessage: "", runError: false };

function icon(name){ return `<i data-lucide="${name}" aria-hidden="true"></i>`; }
function h(value){ return String(value ?? "").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#39;"); }
function api(path){ return `${API_BASE}${path}`; }
async function request(path, options = {}){
  const response = await fetch(api(path), options);
  if(!response.ok){
    let detail = await response.text();
    try { detail = JSON.stringify(JSON.parse(detail).detail || JSON.parse(detail), null, 2); } catch {}
    throw new Error(detail || `HTTP ${response.status}`);
  }
  const type = response.headers.get("content-type") || "";
  return type.includes("application/json") ? response.json() : response.text();
}
function artifactUrl(artifact){ return api(`/artifacts/${artifact.id}/download`); }
function byLabel(label){ return state.artifacts.find((item) => item.label === label); }

function render(){
  const root = document.querySelector("#qcLab");
  root.innerHTML = `
    <header class="qc-top"><nav class="qc-nav">
      <a class="brand" href="./qc-lab.html"><span class="brand-mark">QC</span><span><strong>QLanalyser QC 实验室</strong><small>完整输入输出 · 数据预览 · 滤波快照</small></span></a>
      <div class="top-links"><a href="./module-lab.html">${icon("flask-conical")}分析实验室</a><a href="./index.html">${icon("home")}正式入口</a></div>
    </nav></header>
    <section class="qc-wrap">
      <div class="hero">
        <article class="hero-card"><p class="eyebrow">QC service workbench</p><h1>数据质控、原始波形预览和带通/陷波快照</h1><p>这个页面连接真实后端服务。你可以上传 EEG 文件，读取 metadata，选择通道和时间窗，运行 QC 预览任务，并下载原始波形、滤波预览、快照、result、manifest 和 log。</p><div class="message">API：${h(API_BASE)} · 实验室免登录；正式工作台登录/注册保持不变。</div></article>
        <aside class="side-card"><h2>上线测试重点</h2><ul class="status-list"><li><strong>输入</strong><br/>上传或选择 EEG 文件</li><li><strong>处理</strong><br/>metadata + 波形窗口 + 预览滤波</li><li><strong>输出</strong><br/>SVG 快照、JSON、manifest、log</li></ul></aside>
      </div>
      <div class="layout">
        <aside>${renderControls()}</aside>
        <main>${renderResults()}</main>
      </div>
    </section>`;
  bind();
  if(window.lucide) window.lucide.createIcons();
}

function renderControls(){
  return `
    <section class="panel"><h2>1. 文件输入</h2>
      <div class="field"><label>选择已上传 EEG</label><select id="fileSelect"><option value="">请选择文件</option>${state.files.map((file)=>`<option value="${h(file.id)}" ${file.id===state.selectedFile?"selected":""}>${h(file.original_filename)} · ${h(file.detected_format || "unknown")}</option>`).join("")}</select><small>列表来自后端 /api/eeg/files。</small></div>
      <div class="field"><label>上传 EEG 文件</label><input id="uploadFile" type="file" accept=".edf,.bdf,.fif,.vhdr,.set,.cnt" /></div>
      <div class="grid-2"><button class="btn" id="refreshFiles" type="button">${icon("refresh-cw")}刷新文件</button><button class="btn primary" id="uploadBtn" type="button">${icon("upload")}上传</button></div>
      <p id="fileMessage" class="message ${state.fileError ? "error" : ""}" ${state.fileMessage ? "" : "hidden"}>${h(state.fileMessage)}</p>
    </section>
    <section class="panel"><h2>2. 预览参数</h2>
      <div class="grid-2"><div class="field"><label>开始秒</label><input id="startSec" type="number" step="0.1" value="0" /></div><div class="field"><label>窗口秒</label><input id="durationSec" type="number" step="0.1" value="8" /></div></div>
      <div class="field"><label>通道</label><input id="channels" type="text" placeholder="留空自动取前 8 个 EEG；例如 Fz,Cz,Pz,Oz" /></div>
      <div class="grid-2"><div class="field"><label>显示采样率</label><input id="displaySfreq" type="number" step="1" value="200" /></div><div class="field"><label>快照标签</label><input id="snapshotLabel" type="text" value="QC preview snapshot" /></div></div>
      <div class="checks"><label class="check"><input id="filterEnabled" type="checkbox" checked /> 启用滤波预览</label><label class="check"><input id="bandpassEnabled" type="checkbox" checked /> 带通</label><div class="grid-2"><div class="field"><label>低切 Hz</label><input id="lFreq" type="number" step="0.1" value="1" /></div><div class="field"><label>高切 Hz</label><input id="hFreq" type="number" step="0.1" value="40" /></div></div><label class="check"><input id="notchEnabled" type="checkbox" /> 陷波</label><div class="field"><label>陷波频率 Hz</label><input id="notchFreq" type="text" value="50" /></div></div>
      <button class="btn primary" id="runPreview" type="button" ${state.selectedFile?"":"disabled"}>${icon("play")}运行 QC 预览</button>
      <p id="runMessage" class="message ${state.runError ? "error" : ""}" ${state.runMessage ? "" : "hidden"}>${h(state.runMessage)}</p>
    </section>`;
}

function renderResults(){
  return `
    <section class="panel"><h2>Metadata 概览</h2>${renderMetadata()}</section>
    <section class="panel"><h2>波形与滤波预览</h2>${renderViewer()}</section>
    <section class="panel"><h2>输出文件</h2>${renderArtifacts()}</section>`;
}
function renderMetadata(){
  const file = state.files.find((item)=>item.id===state.selectedFile);
  const meta = state.metadata || file?.metadata_json || {};
  if(!file) return `<div class="empty">请选择或上传 EEG 文件。</div>`;
  const rows = [
    ["文件", file.original_filename], ["格式", file.detected_format], ["采样率", file.sampling_rate || meta.sampling_rate], ["时长", file.duration_sec || meta.duration_sec], ["通道数", file.channel_count || meta.channel_count], ["状态", meta.status || file.status], ["事件/注释", meta.annotation_count], ["高/低通", `${meta.highpass ?? "-"} / ${meta.lowpass ?? "-"}`]
  ];
  return `<div class="meta-grid">${rows.map(([k,v])=>`<div class="metric"><span>${h(k)}</span><strong>${h(v ?? "-")}</strong></div>`).join("")}</div>`;
}
function renderViewer(){
  if(!state.artifacts.length) return `<div class="empty">运行 QC 预览后，这里会显示原始波形、滤波预览和快照。</div>`;
  const tabs = [["raw_preview_figure","原始波形"],["filter_preview_figure","滤波预览"],["snapshot_figure","快照"]].filter(([label])=>byLabel(label));
  const active = byLabel(state.activeFigure) || byLabel(tabs[0]?.[0]);
  return `<div class="viewer"><div class="figure-tabs">${tabs.map(([label,text])=>`<button class="btn ${active?.label===label?"primary":""}" type="button" data-figure="${label}">${h(text)}</button>`).join("")}</div><div class="figure-frame">${active?`<img src="${artifactUrl(active)}" alt="${h(active.label)}" />`:`<div class="empty">暂无图像</div>`}</div></div>`;
}
function renderArtifacts(){
  if(!state.artifacts.length) return `<div class="empty">尚未生成输出文件。</div>`;
  return `<div class="artifact-grid">${state.artifacts.map((artifact)=>`<a class="artifact" href="${artifactUrl(artifact)}" target="_blank" rel="noopener"><span>${h(artifact.artifact_type)}</span><strong>${h(artifact.label)}</strong><small>${h(artifact.id)} ? download</small></a>`).join("")}</div>`;
}

function bind(){
  document.querySelector("#refreshFiles")?.addEventListener("click", loadFiles);
  document.querySelector("#uploadBtn")?.addEventListener("click", uploadFile);
  document.querySelector("#fileSelect")?.addEventListener("change", async (event)=>{ state.selectedFile = event.target.value; state.metadata=null; state.task=null; state.artifacts=[]; if(state.selectedFile) await loadMetadata(); render(); });
  document.querySelector("#runPreview")?.addEventListener("click", runPreview);
  document.querySelectorAll("[data-figure]").forEach((button)=>button.addEventListener("click",()=>{ state.activeFigure=button.dataset.figure; render(); }));
}
async function ensureProject(){ if(state.project) return state.project; state.project = await request("/projects", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({name:"QC Lab Test", description:"No-login QC lab upload", research_type:"qc_lab"})}); return state.project; }
async function loadFiles(){ setMessage("fileMessage","正在读取文件列表..."); try{ state.files = await request("/eeg/files"); if(!state.selectedFile && state.files[0]) state.selectedFile=state.files[0].id; if(state.selectedFile) await loadMetadata(); setMessage("fileMessage",`已读取 ${state.files.length} 个文件。`); }catch(error){ setMessage("fileMessage",`读取文件失败：${error.message}`, true); } render(); }
async function loadMetadata(){ if(!state.selectedFile) return; try{ state.metadata = await request(`/eeg/files/${state.selectedFile}/metadata`); }catch(error){ setMessage("fileMessage",`metadata 读取失败：${error.message}`, true); } }
async function uploadFile(){ const input=document.querySelector("#uploadFile"); const file=input?.files?.[0]; if(!file){ setMessage("fileMessage","请选择一个 EEG 文件。", true); return; } try{ setMessage("fileMessage","正在上传..."); const project=await ensureProject(); const form=new FormData(); form.append("file", file); const uploaded=await request(`/eeg/upload?project_id=${encodeURIComponent(project.id)}`, {method:"POST", body:form}); state.selectedFile=uploaded.id; await loadFiles(); setMessage("fileMessage",`上传成功：${uploaded.original_filename}`); }catch(error){ setMessage("fileMessage",`上传失败：${error.message}`, true); } render(); }
function collectParameters(){ const channels=document.querySelector("#channels")?.value.split(",").map((item)=>item.trim()).filter(Boolean) || []; const notchFreqs=(document.querySelector("#notchFreq")?.value || "").split(",").map((item)=>Number(item.trim())).filter((item)=>Number.isFinite(item)); return { preview:{ start_sec:Number(document.querySelector("#startSec")?.value || 0), duration_sec:Number(document.querySelector("#durationSec")?.value || 8), channels, display_sfreq:Number(document.querySelector("#displaySfreq")?.value || 200), show_annotations:true }, filter_preview:{ enabled:document.querySelector("#filterEnabled")?.checked, bandpass:{ enabled:document.querySelector("#bandpassEnabled")?.checked, l_freq:Number(document.querySelector("#lFreq")?.value || 1), h_freq:Number(document.querySelector("#hFreq")?.value || 40) }, notch:{ enabled:document.querySelector("#notchEnabled")?.checked, freqs:notchFreqs } }, snapshot:{ label:document.querySelector("#snapshotLabel")?.value || "QC preview snapshot", include_raw:true, include_filtered_preview:true } }; }
async function runPreview(){ if(!state.selectedFile){ setMessage("runMessage","请先选择文件。", true); return; } try{ setMessage("runMessage","正在运行 QC 预览服务..."); const file=state.files.find((item)=>item.id===state.selectedFile); const task=await request("/tasks", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({ project_id:file.project_id, module_name:"qc", workflow_id:"qc_waveform_preview", input_file_id:file.id, parameters_json:collectParameters() })}); state.task=task; state.artifacts=await request(`/tasks/${task.id}/artifacts`); state.activeFigure=byLabel("filter_preview_figure")?"filter_preview_figure":"raw_preview_figure"; setMessage("runMessage",`任务完成：${task.id}，生成 ${state.artifacts.length} 个输出文件。`); }catch(error){ setMessage("runMessage",`运行失败：${error.message}`, true); } render(); }
function setMessage(id, text, error=false){
  if(id === "fileMessage") { state.fileMessage = text; state.fileError = Boolean(error); }
  if(id === "runMessage") { state.runMessage = text; state.runError = Boolean(error); }
  const el=document.querySelector(`#${id}`);
  if(!el) return;
  el.hidden=false;
  el.textContent=text;
  el.classList.toggle("error", Boolean(error));
}

render();
loadFiles();