const MANIFEST_URL = "/assets/research-modules/reproducibility/research_module_manifest.json";
const basePrefix = document.body.dataset.module === "index" ? "./" : "../";
const icon = (name) => `<i data-lucide="${name}" aria-hidden="true"></i>`;

function asset(url) {
  if (!url) return "";
  if (url.startsWith("http")) return url;
  if (url.startsWith("/")) return basePrefix + url.slice(1);
  return basePrefix + url;
}
function h(text) {
  return String(text ?? "").replace(/[&<>"']/g, (m) => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#039;"}[m]));
}
async function getText(url) {
  const res = await fetch(asset(url), {cache:"no-store"});
  if (!res.ok) throw new Error(`${res.status} ${url}`);
  return res.text();
}
async function getJson(url) {
  const text = await getText(url);
  return JSON.parse(text);
}
function parseCsv(text) {
  const rows = [];
  let row = [], cell = "", quote = false;
  for (let i=0;i<text.length;i++) {
    const c = text[i], n = text[i+1];
    if (c === '"' && quote && n === '"') { cell += '"'; i++; continue; }
    if (c === '"') { quote = !quote; continue; }
    if (c === ',' && !quote) { row.push(cell); cell = ""; continue; }
    if ((c === '\n' || c === '\r') && !quote) {
      if (c === '\r' && n === '\n') i++;
      row.push(cell); if (row.some(v => v !== "")) rows.push(row);
      row = []; cell = ""; continue;
    }
    cell += c;
  }
  if (cell || row.length) { row.push(cell); if (row.some(v => v !== "")) rows.push(row); }
  return rows;
}
function statusClass(module) { return module.statusLevel === "enabled" ? "enabled" : "preview"; }

async function loadManifest() {
  return getJson(MANIFEST_URL);
}

function renderIndex(manifest) {
  const grid = document.querySelector("#moduleGrid");
  if (!grid) return;
  grid.innerHTML = Object.values(manifest.modules).map((m) => {
    const firstFig = m.figures?.[0]?.src || "";
    return `<article class="module-card">
      <img src="${asset(firstFig)}" alt="${h(m.title)}" loading="lazy" />
      <div class="body">
        <span class="status-badge ${statusClass(m)}">${m.status}</span>
        <h3>${h(m.title)}</h3>
        <p>${h(m.subtitle)}</p>
        <p>${h(m.scenario)}</p>
        <div class="actions">
          <a class="mini-btn main" href="./research-module/${m.page}">${icon("external-link")}查看详情</a>
          <a class="mini-btn" href="${asset(m.package)}">${icon("download")}结果包</a>
        </div>
      </div>
    </article>`;
  }).join("");
  if (window.lucide) lucide.createIcons();
}

function list(items, className="") {
  return `<ul class="info-list ${className}">${(items||[]).map((x)=>`<li>${h(x)}</li>`).join("")}</ul>`;
}
function pillList(items) {
  return (items||[]).map((x)=>`<span class="tag good">${h(x)}</span>`).join("");
}

async function renderCsvPreview(table) {
  const target = document.querySelector(`[data-table-src="${table.src}"]`);
  if (!target) return;
  try {
    const rows = parseCsv(await getText(table.src)).slice(0, 9);
    if (!rows.length) { target.innerHTML = `<div class="empty">CSV 暂无内容</div>`; return; }
    const head = rows[0];
    const body = rows.slice(1);
    target.innerHTML = `<div class="table-wrap"><table class="data-table"><thead><tr>${head.map(c=>`<th>${h(c)}</th>`).join("")}</tr></thead><tbody>${body.map(r=>`<tr>${head.map((_,i)=>`<td>${h(r[i] ?? "")}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
  } catch (err) {
    target.innerHTML = `<div class="empty">无法预览 CSV：${h(err.message)}</div>`;
  }
}

async function renderDocPreview(doc) {
  const target = document.querySelector(`[data-doc-src="${doc.src}"]`);
  if (!target) return;
  try {
    const text = await getText(doc.src);
    const pretty = doc.type === "json" ? JSON.stringify(JSON.parse(text), null, 2) : text;
    target.innerHTML = `<pre>${h(pretty)}</pre>`;
  } catch (err) {
    target.innerHTML = `<pre>无法预览：${h(err.message)}</pre>`;
  }
}

function renderModule(manifest, slug) {
  const m = manifest.modules[slug];
  const app = document.querySelector("#moduleApp");
  if (!app || !m) return;
  const pages = Object.values(manifest.modules);
  app.innerHTML = `<header class="module-header">
    <nav class="module-nav">
      <a href="../research-modules.html">${icon("arrow-left")} 返回体验中心</a>
      <div>${pages.map((p)=>`<a href="./${p.page}">${h(p.slug.toUpperCase())}</a>`).join("")}</div>
    </nav>
    <section class="module-title">
      <span class="status-badge ${statusClass(m)}">${h(m.status)}</span>
      <h1>${h(m.title)}</h1>
      <p>${h(m.subtitle)}</p>
      <p>${h(m.scenario)}</p>
      <div class="quick-links">
        <a class="primary" href="${asset(m.package)}">${icon("download")}下载结果包</a>
        <a class="secondary" href="${asset(manifest.shared.mne_reference)}">${icon("book-open")}MNE 参考清单</a>
        <a class="secondary" href="${asset(manifest.shared.reviewer_checklist)}">${icon("clipboard-check")}体验清单</a>
      </div>
    </section>
  </header>
  <section class="sample-strip" aria-label="Synthetic input data">
    <strong>${icon("database")}测试输入数据</strong>
    <a href="${asset(manifest.sampleData.source_edf)}">示例 EDF</a>
    <a href="${asset(manifest.sampleData.source_events)}">原始事件 TSV</a>
    <a href="${asset(manifest.sampleData.events_tsv)}">事件 TSV</a>
    <a href="${asset(manifest.sampleData.raw_preview_csv)}">Raw preview CSV</a>
    <a href="${asset(manifest.sampleData.subject_metrics_csv)}">Subject metrics CSV</a>
  </section>
  <div class="module-layout">
    <aside class="side-panel">
      <h3>页面索引</h3>
      <a href="#workflow">输入输出 <span>→</span></a>
      <a href="#figures">图像预览 <span>→</span></a>
      <a href="#tables">表格预览 <span>→</span></a>
      <a href="#docs">参数与方法 <span>→</span></a>
      <a href="#guardrails">科研风险 <span>→</span></a>
      <a href="${asset(m.package)}">下载 ZIP <span>↓</span></a>
    </aside>
    <section class="content-stack">
      <article class="panel" id="workflow">
        <p class="eyebrow">Workflow contract</p>
        <h2>输入、参数控件、输出</h2>
        <div class="grid-2">
          <div><h3>输入</h3>${list(m.inputs)}</div>
          <div><h3>参数控件</h3>${list(m.controls)}</div>
          <div><h3>输出</h3>${list(m.outputs)}</div>
          <div><h3>MNE 对应对象</h3><div>${pillList(m.mneObjects)}</div></div>
        </div>
      </article>
      <article class="panel" id="figures">
        <p class="eyebrow">Publication preview</p>
        <h2>图像预览</h2>
        <div class="figure-grid">${(m.figures||[]).map((f)=>`<figure class="figure-card"><img src="${asset(f.src)}" alt="${h(f.alt||f.label)}" loading="lazy" /><figcaption>${h(f.label)}</figcaption></figure>`).join("")}</div>
      </article>
      <article class="panel" id="tables">
        <p class="eyebrow">Subject-level data</p>
        <h2>CSV 表格预览</h2>
        <div class="content-stack">${(m.tables||[]).map((tbl)=>`<section><h3>${h(tbl.label)}</h3><div data-table-src="${h(tbl.src)}"></div><div class="download-row"><a class="mini-btn" href="${asset(tbl.src)}">${icon("download")}下载 CSV</a></div></section>`).join("")}</div>
      </article>
      <article class="panel" id="docs">
        <p class="eyebrow">Reproducibility</p>
        <h2>参数、方法说明、图注和 summary</h2>
        <div class="doc-grid">${(m.docs||[]).map((doc)=>`<section class="doc-card"><h3>${h(doc.label)}</h3><div data-doc-src="${h(doc.src)}"></div><div class="download-row"><a class="mini-btn" href="${asset(doc.src)}">${icon("download")}下载</a></div></section>`).join("")}</div>
      </article>
      <article class="panel guardrail" id="guardrails">
        <p class="eyebrow">Scientific guardrails</p>
        <h2>科研解释风险</h2>
        ${list(m.risks, "risk-list")}
        <p><strong>统一边界：</strong>${h(manifest.researchGuardrail)}</p>
      </article>
    </section>
  </div>`;
  (m.tables||[]).forEach(renderCsvPreview);
  (m.docs||[]).forEach(renderDocPreview);
  if (window.lucide) lucide.createIcons();
}

(async function boot(){
  try {
    const manifest = await loadManifest();
    const slug = document.body.dataset.module;
    if (slug === "index") renderIndex(manifest);
    else renderModule(manifest, slug);
  } catch (err) {
    const target = document.querySelector("#moduleGrid") || document.querySelector("#moduleApp") || document.body;
    target.innerHTML = `<div class="page-wrap"><div class="panel"><h2>页面加载失败</h2><p>${h(err.message)}</p></div></div>`;
  }
})();
