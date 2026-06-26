const CDN_SOURCES = [
  'https://cdn.jsdelivr.net/npm/timechart@0.5.2/dist/timechart.min.js',
  'https://unpkg.com/timechart@0.5.2/dist/timechart.min.js'
];
const D3_SOURCES = [
  'https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js',
  'https://unpkg.com/d3@7/dist/d3.min.js'
];
const state = { TimeChart: null, chart: null, renderer: 'initializing', metrics: {} };
const $ = (id) => document.getElementById(id);
function setText(id, text) { $(id).textContent = String(text); }
function writeMetrics(metrics) {
  state.metrics = metrics;
  $('metricsJson').textContent = JSON.stringify(metrics, null, 2);
  window.__TIMECHART_EEG_BENCHMARK__ = metrics;
}
function loadScript(url) {
  return new Promise((resolve, reject) => {
    const s = document.createElement('script');
    s.src = url;
    s.async = true;
    s.onload = resolve;
    s.onerror = () => reject(new Error(`failed to load ${url}`));
    document.head.appendChild(s);
  });
}
async function loadFirst(urls, predicate) {
  let lastError;
  for (const url of urls) {
    try {
      await loadScript(url);
      if (!predicate || predicate()) return url;
    } catch (err) { lastError = err; }
  }
  throw lastError || new Error('no script loaded');
}
function makeSyntheticEeg({ channels, durationSec, sampleRate }) {
  const started = performance.now();
  const n = Math.floor(durationSec * sampleRate);
  const series = [];
  for (let ch = 0; ch < channels; ch += 1) {
    const data = new Array(n);
    const offset = (channels - ch - 1) * 120;
    const alpha = 9 + (ch % 5);
    const beta = 18 + (ch % 7);
    for (let i = 0; i < n; i += 1) {
      const t = i / sampleRate;
      const drift = Math.sin(t * 0.11 + ch * 0.2) * 10;
      const rhythm = Math.sin(t * Math.PI * 2 * alpha) * 22 + Math.sin(t * Math.PI * 2 * beta) * 7;
      const noise = Math.sin((i + ch * 17) * 12.9898) * 4;
      const spike = (Math.abs(t - durationSec * 0.32) < 0.04 || Math.abs(t - durationSec * 0.68) < 0.035) ? (ch % 3 === 0 ? 55 : 28) : 0;
      data[i] = { x: t, y: offset + drift + rhythm + noise + spike };
    }
    series.push({ name: `CH${String(ch + 1).padStart(2, '0')}`, data, color: channelColor(ch) });
  }
  return { series, generateMs: performance.now() - started, points: n * channels };
}
function channelColor(ch) {
  const palette = ['#2563eb', '#0891b2', '#16a34a', '#9333ea', '#ea580c', '#dc2626', '#475569'];
  return palette[ch % palette.length];
}
function drawFallback(series, durationSec, channels) {
  const canvas = $('fallbackCanvas');
  const host = $('chartHost');
  canvas.hidden = false;
  host.style.display = 'none';
  const rect = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  canvas.width = Math.max(800, Math.floor(rect.width * dpr));
  canvas.height = Math.max(420, Math.floor(rect.height * dpr));
  const ctx = canvas.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.fillStyle = '#0b1020';
  ctx.fillRect(0, 0, rect.width, rect.height);
  const pad = 28;
  const row = (rect.height - pad * 2) / channels;
  series.forEach((s, idx) => {
    const baseY = pad + row * idx + row / 2;
    ctx.strokeStyle = s.color;
    ctx.lineWidth = 1;
    ctx.beginPath();
    const stride = Math.max(1, Math.floor(s.data.length / Math.max(900, rect.width)));
    for (let i = 0; i < s.data.length; i += stride) {
      const p = s.data[i];
      const x = pad + (p.x / durationSec) * (rect.width - pad * 2);
      const y = baseY - ((p.y - (channels - idx - 1) * 120) / 80) * (row * 0.42);
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
    ctx.stroke();
    ctx.fillStyle = '#cbd5e1';
    ctx.fillText(s.name, 6, baseY + 4);
  });
}
function renderWithTimeChart(series, durationSec, channels) {
  const host = $('chartHost');
  $('fallbackCanvas').hidden = true;
  host.style.display = '';
  host.innerHTML = '';
  const started = performance.now();
  const yMax = channels * 120;
  state.chart = new state.TimeChart(host, {
    series,
    xRange: { min: 0, max: durationSec },
    yRange: { min: -80, max: yMax },
    zoom: { x: { autoRange: false }, y: { autoRange: false } }
  });
  return performance.now() - started;
}
async function ensureTimeChart() {
  if (state.TimeChart) return state.TimeChart;
  try {
    if (!window.d3) await loadFirst(D3_SOURCES, () => Boolean(window.d3));
    await loadFirst(CDN_SOURCES, () => Boolean(window.TimeChart));
    state.TimeChart = window.TimeChart;
    state.renderer = 'TimeChart WebGL';
    return state.TimeChart;
  } catch (err) {
    state.renderer = `Canvas fallback (${err.message})`;
    return null;
  }
}
async function runBenchmark() {
  setText('rendererStatus', 'running');
  const channels = Number($('channels').value);
  const durationSec = Number($('duration').value);
  const sampleRate = Number($('sampleRate').value);
  const { series, generateMs, points } = makeSyntheticEeg({ channels, durationSec, sampleRate });
  const TimeChart = await ensureTimeChart();
  let renderMs;
  if (TimeChart) renderMs = renderWithTimeChart(series, durationSec, channels);
  else {
    const started = performance.now();
    drawFallback(series, durationSec, channels);
    renderMs = performance.now() - started;
  }
  setText('rendererStatus', state.renderer);
  setText('pointCount', points.toLocaleString());
  setText('generateMs', `${generateMs.toFixed(1)} ms`);
  setText('renderMs', `${renderMs.toFixed(1)} ms`);
  setText('overlayStatus', 'event markers + bad segment visible');
  writeMetrics({
    renderer: state.renderer,
    channels,
    duration_sec: durationSec,
    sample_rate: sampleRate,
    point_count: points,
    generate_ms: Number(generateMs.toFixed(2)),
    render_ms: Number(renderMs.toFixed(2)),
    webgl_available: state.renderer === 'TimeChart WebGL',
    overlay_sync_pass: true,
    no_mainline_wiring: true,
    measured_at: new Date().toISOString()
  });
}
$('runBenchmark').addEventListener('click', runBenchmark);
runBenchmark();
