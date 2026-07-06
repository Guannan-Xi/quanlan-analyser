/**
 * EDF Reviewer Lab - Phase 3: Dual-Window Interactive Viewer
 * 
 * Native JS implementation for QLanalyser analysis lab.
 * Features: dual-window comparison, per-channel zoom, time range sliders,
 * gain linking, right-click reset, publication SVG export.
 */

// ── State ──────────────────────────────────────────────
let uploadedFile = null;
let edfMetadata = null;
let waveformData = null;

// Per-window state
const winState = {
  a: { gain: 1, startSec: 0, selectedChannel: -1, gainByChannel: {} },
  b: { gain: 1, startSec: 0, selectedChannel: -1, gainByChannel: {} },
};
let gainLinked = false;
let windowSeconds = 20;
let channels = [];
let times = [];
let values = [];

// ── DOM refs ───────────────────────────────────────────
const dom = {};

function $(sel) { return document.querySelector(sel); }
function $$(sel) { return document.querySelectorAll(sel); }

// ── Init ───────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  dom.upload = $('#edfUpload');
  dom.fileInfo = $('#fileInfo');
  dom.controls = $('#controlsSection');
  dom.channelSelect = $('#channelSelect');
  dom.renderBtn = $('#renderBtn');
  dom.viewer = $('#viewerSection');
  dom.waveform = $('#waveformViewer');
  dom.loader = $('#loadingOverlay');
  dom.windowSec = $('#windowSeconds');
  dom.gainLink = $('#gainLinkToggle');

  dom.upload.addEventListener('change', handleUpload);
  dom.renderBtn.addEventListener('click', handleRender);
  dom.gainLink.addEventListener('change', () => { gainLinked = dom.gainLink.checked; });
  dom.windowSec.addEventListener('change', () => {
    windowSeconds = Math.max(1, parseFloat(dom.windowSec.value) || 20);
  });
  windowSeconds = parseFloat(dom.windowSec?.value) || 20;
});

// ── Upload ─────────────────────────────────────────────
async function handleUpload(e) {
  const f = e.target.files[0];
  if (!f) return;
  uploadedFile = f;
  showLoading('读取 EDF...');
  try {
    edfMetadata = await inspectEDF(f);
    displayInfo(edfMetadata);
    renderChannels(edfMetadata.channels);
    dom.controls.style.display = 'block';
    dom.renderBtn.disabled = false;
    hideLoading();
  } catch (err) {
    hideLoading();
    showError('读取失败: ' + err.message);
  }
}

async function inspectEDF(file) {
  const fd = new FormData(); fd.append('file', file);
  const r = await fetch('/api/lab/edf-reviewer/inspect', { method: 'POST', body: fd });
  if (!r.ok) { const e = await r.json().catch(()=>({detail:r.statusText})); throw new Error(e.detail); }
  return r.json();
}

function displayInfo(m) {
  dom.fileInfo.innerHTML = `
    <div class="success-message">已加载: ${esc(uploadedFile.name)}</div>
    <div class="file-info-grid">
      <div class="file-info-item"><div class="file-info-label">采样率</div><div class="file-info-value">${m.sfreq.toFixed(1)} Hz</div></div>
      <div class="file-info-item"><div class="file-info-label">时长</div><div class="file-info-value">${m.duration.toFixed(1)} s</div></div>
      <div class="file-info-item"><div class="file-info-label">通道数</div><div class="file-info-value">${m.channel_count}</div></div>
      <div class="file-info-item"><div class="file-info-label">指纹</div><div class="file-info-value">${m.file_hash?.slice(0,12)||''}</div></div>
    </div>`;
}

function renderChannels(chs) {
  dom.channelSelect.innerHTML = '';
  chs.forEach(ch => {
    const w = document.createElement('div'); w.className = 'channel-checkbox';
    const cb = document.createElement('input'); cb.type = 'checkbox'; cb.id = 'ch_'+ch; cb.value = ch;
    if (ch.toUpperCase().startsWith('EEG')) cb.checked = true;
    const lb = document.createElement('label'); lb.htmlFor = 'ch_'+ch; lb.textContent = ch;
    w.appendChild(cb); w.appendChild(lb); dom.channelSelect.appendChild(w);
  });
}

function getSelectedChannels() {
  return [...dom.channelSelect.querySelectorAll('input:checked')].map(c => c.value);
}

// ── Render waveform ────────────────────────────────────
async function handleRender() {
  channels = getSelectedChannels();
  if (!channels.length) { showError('请至少选择一个通道'); return; }
  const hp = parseFloat($('#highpass').value) || 0;
  const lp = parseFloat($('#lowpass').value) || 0;
  const notch = parseFloat($('#notch').value) || 0;
  const mp = parseInt($('#maxPoints').value) || 20000;
  if (hp>0 && lp>0 && hp>=lp) { showError('高通<低通'); return; }

  showLoading('处理波形...');
  try {
    waveformData = await processWaveform(uploadedFile, channels, hp, lp, notch, mp);
    times = waveformData.times;
    values = waveformData.values;
    initWindowState();
    buildDualViewer();
    dom.viewer.style.display = 'block';
    dom.viewer.scrollIntoView({behavior:'smooth',block:'start'});
    hideLoading();
  } catch(err) {
    hideLoading(); showError('波形失败: '+err.message);
  }
}

async function processWaveform(file, chs, hp, lp, notch, mp) {
  const fd = new FormData(); fd.append('file', file);
  fd.append('channels', JSON.stringify(chs));
  fd.append('highpass', hp); fd.append('lowpass', lp);
  fd.append('notch', notch); fd.append('max_points', mp);
  const r = await fetch('/api/lab/edf-reviewer/waveform', { method: 'POST', body: fd });
  if (!r.ok) { const e = await r.json().catch(()=>({detail:r.statusText})); throw new Error(e.detail); }
  return r.json();
}

function initWindowState() {
  const totalDur = times[times.length-1] - times[0];
  const halfLen = Math.min(windowSeconds, totalDur/2);
  winState.a = { gain: 1, startSec: times[0], selectedChannel: -1, gainByChannel: {} };
  winState.b = { gain: 1, startSec: times[0] + totalDur/2 - halfLen/2, selectedChannel: -1, gainByChannel: {} };
  channels.forEach((_,i) => { winState.a.gainByChannel[i]=1; winState.b.gainByChannel[i]=1; });
}

// ── Build dual-window HTML ────────────────────────────
function buildDualViewer() {
  const info = waveformData || {};
  dom.waveform.innerHTML = `
    <div class="dual-header">
      <h2>双窗口波形审阅</h2>
      <p>${info.filter_summary||''} | ${info.unit_label||''} | ${channels.length} 通道</p>
      ${info.acc_rms_derived ? `<p class="acc-rms-note">✓ 已追加体动 RMS 轨道</p>` : ''}
    </div>
    <div class="dual-panels">
      ${buildPanel('a', '窗口 A')}
      ${buildPanel('b', '窗口 B')}
    </div>
  `;
  renderBoth();
}

function buildPanel(win, label) {
  return `<div class="viewer-panel" id="panel-${win}">
    <div class="panel-toolbar">
      <strong>${label}</strong>
      <button class="btn-sm" onclick="resetGain('${win}')">重置幅值</button>
      <button class="btn-sm primary" onclick="exportSVG('${win}')">保存 SVG 快照</button>
      <span id="status-${win}" class="panel-status"></span>
    </div>
    <div class="svg-box" id="svgBox-${win}"></div>
    <div class="timebar-row">
      <span>时间</span>
      <input type="range" id="range-${win}" min="0" max="1000" value="0" step="0.5" aria-label="时间窗口起点" />
      <span id="timeLabel-${win}"></span>
    </div>
    <div class="hint">单击通道选中 | 滚轮缩放 | 右键重置 | 拖动时间条</div>
  </div>`;
}

// ── SVG Rendering ──────────────────────────────────────
function renderBoth() {
  renderWindow('a');
  renderWindow('b');
}

function renderWindow(win) {
  const ws = winState[win];
  const totalStart = times[0] || 0;
  const totalEnd = times[times.length-1] || 0;
  const maxStart = Math.max(totalStart, totalEnd - windowSeconds);

  // Sync range slider
  const range = document.getElementById('range-'+win);
  if (range) {
    range.min = String(totalStart);
    range.max = String(maxStart);
    range.value = String(Math.min(Math.max(ws.startSec, totalStart), maxStart));
  }

  ws.startSec = Number(document.getElementById('range-'+win)?.value) || ws.startSec;
  const stopSec = Math.min(totalEnd, ws.startSec + windowSeconds);

  // Find visible indices
  let si=0; while(si<times.length && times[si]<ws.startSec) si++;
  let ei=si; while(ei<times.length && times[ei]<=stopSec) ei++;
  si=Math.max(0,si-1); ei=Math.max(si+2,ei);

  // Downsample
  const count = ei-si;
  const step = Math.max(1, Math.ceil(count/2800));
  const idxs = [];
  for(let i=si; i<ei; i+=step) idxs.push(i);
  if(idxs[idxs.length-1] !== ei-1) idxs.push(ei-1);

  // Per-channel visible max
  const visMax = values.map(row => {
    let m=1e-9; for(const i of idxs) { const a=Math.abs(row[i]); if(isFinite(a)&&a>m) m=a; } return m;
  });

  // Layout
  const W=1600, left=132, right=36, top=70, bottom=104;
  const plotH = 500 - top - bottom;
  const rowH = plotH / Math.max(1, channels.length);
  const halfTrack = rowH * 0.46;
  const x0=left, x1=W-right;
  const rangeSec = Math.max(0.001, stopSec-ws.startSec);
  const yCenters = channels.map((_,ci) => top + rowH*(ci+0.5));

  const scalePx = visMax.map((m,i) => {
    const chGain = ws.gainByChannel[i] || 1;
    const ampPx = 38 * ws.gain * chGain;
    return Math.min(ampPx, (halfTrack*0.92)/(m||1e-9));
  });

  function xFor(t) { return x0+((t-ws.startSec)/rangeSec)*(x1-x0); }
  function yFor(ch, v) { return yCenters[ch] - v*scalePx[ch]; }

  // Build SVG
  let svg = `<svg xmlns="http://www.w3.org/2000/svg" width="100%" viewBox="0 0 ${W} ${500}" style="display:block;touch-action:none;user-select:none;background:#fff;">`;

  // Grid + time ticks
  for(let k=0; k<=8; k++) {
    const t = ws.startSec + (rangeSec*k/8);
    const x = xFor(t);
    svg += `<line x1="${x.toFixed(1)}" y1="${top}" x2="${x.toFixed(1)}" y2="${top+plotH}" stroke="#f1f5f9" stroke-width="1"/>`;
    svg += `<line x1="${x.toFixed(1)}" y1="${top+plotH}" x2="${x.toFixed(1)}" y2="${top+plotH+6}" stroke="#475569" stroke-width="1"/>`;
    svg += `<text x="${x.toFixed(1)}" y="${top+plotH+30}" text-anchor="middle" font-size="20" fill="#334155">${t.toFixed(1)}s</text>`;
  }

  // Channels
  channels.forEach((name, ci) => {
    const yBase = yCenters[ci];
    const isSelected = ws.selectedChannel === ci;
    const color = name.toUpperCase().startsWith('ACC') ? '#10b981' : '#6366f1';
    const strokeW = isSelected ? 2.5 : 1.5;

    // Label
    svg += `<text x="16" y="${(yBase+7).toFixed(1)}" font-size="22" font-weight="${isSelected?'700':'400'}" fill="${isSelected?'#1e40af':'#334155'}" style="cursor:pointer" onclick="selectChannel('${win}',${ci})">${esc(name)}</text>`;
    // Baseline
    svg += `<line x1="${x0}" y1="${yBase.toFixed(1)}" x2="${x1}" y2="${yBase.toFixed(1)}" stroke="${isSelected?'#c7d2fe':'#f1f5f9'}" stroke-width="1"/>`;

    // Waveform
    const pts = idxs.map(i => `${xFor(times[i]).toFixed(1)},${yFor(ci,values[ci][i]).toFixed(1)}`).join(' ');
    svg += `<polyline points="${pts}" fill="none" stroke="${color}" stroke-width="${strokeW}" stroke-linejoin="round" stroke-linecap="round" style="cursor:pointer" onclick="selectChannel('${win}',${ci})"/>`;
  });

  // Bottom axis line
  svg += `<line x1="${x0}" y1="${top+plotH}" x2="${x1}" y2="${top+plotH}" stroke="#1e293b" stroke-width="1.5"/>`;

  // Amplitude scale bar (left side, per last channel as reference)
  const refCh = channels.length-1;
  const ampH = scalePx[refCh];
  const barX = left - 24;
  const barY = top + 10;
  const barLen = 40;
  if (isFinite(ampH) && ampH > 0) {
    const uv = barLen / ampH;
    svg += `<line x1="${barX}" y1="${barY}" x2="${barX}" y2="${barY+barLen}" stroke="#94a3b8" stroke-width="1"/>`;
    svg += `<line x1="${barX-4}" y1="${barY}" x2="${barX}" y2="${barY}" stroke="#94a3b8" stroke-width="1"/>`;
    svg += `<line x1="${barX-4}" y1="${barY+barLen}" x2="${barX}" y2="${barY+barLen}" stroke="#94a3b8" stroke-width="1"/>`;
    svg += `<text x="${barX-8}" y="${barY+barLen/2+5}" text-anchor="end" font-size="14" fill="#64748b">${uv.toFixed(1)}</text>`;
  }

  svg += `</svg>`;

  const box = document.getElementById('svgBox-'+win);
  if (box) box.innerHTML = svg;

  // Update time label
  const tl = document.getElementById('timeLabel-'+win);
  if (tl) tl.textContent = `${ws.startSec.toFixed(1)}s – ${stopSec.toFixed(1)}s`;

  // Update status
  const st = document.getElementById('status-'+win);
  if (st) {
    const sel = ws.selectedChannel >=0 ? channels[ws.selectedChannel] : '全部';
    st.textContent = `选中: ${sel} | 增益: ${ws.gain.toFixed(1)}x`;
  }
}

// ── Interactions ───────────────────────────────────────
function selectChannel(win, ci) {
  const ws = winState[win];
  ws.selectedChannel = (ws.selectedChannel === ci) ? -1 : ci;
  renderWindow(win);
}

function resetGain(win) {
  const ws = winState[win];
  ws.gain = 1;
  channels.forEach((_,i) => { ws.gainByChannel[i] = 1; });
  ws.selectedChannel = -1;
  renderWindow(win);
  if (gainLinked) syncGainFrom(win);
}

function syncGainFrom(src) {
  const other = src === 'a' ? 'b' : 'a';
  winState[other].gain = winState[src].gain;
  winState[other].gainByChannel = {...winState[src].gainByChannel};
  winState[other].selectedChannel = winState[src].selectedChannel;
  renderWindow(other);
}

function exportSVG(win) {
  const box = document.getElementById('svgBox-'+win);
  const svg = box?.querySelector('svg');
  if (!svg) { alert('未找到波形图'); return; }
  const clone = svg.cloneNode(true);
  // Remove onclick attributes for clean export
  clone.querySelectorAll('[onclick]').forEach(el => el.removeAttribute('onclick'));
  const ser = new XMLSerializer();
  const blob = new Blob([ser.serializeToString(clone)], {type:'image/svg+xml;charset=utf-8'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a'); a.href=url; a.download=`qlanalyser_waveform_${win}.svg`;
  document.body.appendChild(a); a.click(); document.body.removeChild(a); URL.revokeObjectURL(url);
}

// ── Mouse wheel zoom ───────────────────────────────────
document.addEventListener('wheel', e => {
  const panel = e.target.closest('.svg-box');
  if (!panel) return;
  const win = panel.id.replace('svgBox-','');
  const ws = winState[win];
  if (!ws) return;
  e.preventDefault();
  const delta = e.deltaY < 0 ? 1.15 : 1/1.15;
  if (ws.selectedChannel >= 0) {
    const cur = ws.gainByChannel[ws.selectedChannel] || 1;
    ws.gainByChannel[ws.selectedChannel] = Math.max(0.1, Math.min(20, cur * delta));
  } else {
    ws.gain = Math.max(0.1, Math.min(20, ws.gain * delta));
  }
  renderWindow(win);
  if (gainLinked) syncGainFrom(win);
}, {passive:false});

// ── Right-click reset ──────────────────────────────────
document.addEventListener('contextmenu', e => {
  const panel = e.target.closest('.svg-box');
  if (!panel) return;
  e.preventDefault();
  const win = panel.id.replace('svgBox-','');
  const ws = winState[win];
  if (ws.selectedChannel >= 0) {
    ws.gainByChannel[ws.selectedChannel] = 1;
    ws.selectedChannel = -1;
  } else {
    ws.gain = 1;
    channels.forEach((_,i)=>{ws.gainByChannel[i]=1;});
  }
  renderWindow(win);
  if (gainLinked) syncGainFrom(win);
});

// ── Range slider change ────────────────────────────────
document.addEventListener('input', e => {
  if (!e.target.matches('[id^="range-"]')) return;
  const win = e.target.id.replace('range-','');
  winState[win].startSec = parseFloat(e.target.value);
  renderWindow(win);
});

// ── Helpers ────────────────────────────────────────────
function showLoading(msg) { const d=dom.loader; if(d){d.querySelector('.loading-text').textContent=msg;d.style.display='flex';} }
function hideLoading() { const d=dom.loader; if(d) d.style.display='none'; }
function showError(msg) { if(dom.fileInfo) dom.fileInfo.innerHTML=`<div class="error-message">${esc(msg)}</div>`; }
function esc(s) { return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

console.log('EDF Reviewer Lab Phase 3 – Dual-window viewer initialized');
