const MANIFEST_URL = "./assets/research-modules/reproducibility/research_module_manifest.json";
const DEFAULT_API_BASE = ["localhost", "127.0.0.1"].includes(window.location.hostname) ? "http://127.0.0.1:8000/api" : "/api";
const API_BASE = new URLSearchParams(window.location.search).get("api") || DEFAULT_API_BASE;
const MODULE_ORDER = ["qc", "psd", "erp", "tfr", "pac", "connectivity"];
const DEMO_MODULES = new Set(["qc", "psd", "erp"]);
const SECTION_ANCHORS = [
  { id: "inputs", label: "数据输入" },
  { id: "controls", label: "参数与预处理" },
  { id: "mne", label: "MNE 方法" },
  { id: "outputs", label: "指标输出" },
  { id: "figures", label: "绘图" },
  { id: "artifacts", label: "下载" },
  { id: "tests", label: "复核" },
  { id: "risks", label: "边界" },
];

const LAB_STAGES = [
  {
    id: "project",
    icon: "folder-plus",
    title: "项目建立",
    subtitle: "研究问题和范式",
    body: "确认研究目的、被试与条件、事件来源和交付物",
    evidence: ["项目名称", "被试与条件", "交付物范围"],
  },
  {
    id: "import",
    icon: "upload-cloud",
    title: "数据导入",
    subtitle: "Raw 与事件表",
    body: "导入 EEG 原始文件、通道信息、采样率和 events / annotations",
    evidence: ["EDF / BDF / FIF / BrainVision / SET / CNT", "通道与采样率", "事件表或注释"],
  },
  {
    id: "preview",
    icon: "activity",
    title: "预览与预处理",
    subtitle: "QC、滤波、参考、坏道",
    body: "先看波形和质控摘要，再决定滤波、notch、参考和坏道处理",
    evidence: ["Raw 预览", "QC 摘要", "预处理参数"],
  },
  {
    id: "analysis",
    icon: "git-branch",
    title: "项目选择",
    subtitle: "QC / PSD / ERP / TFR / PAC / Connectivity",
    body: "按研究问题选择质控、频谱、事件相关反应或高级预览项目",
    evidence: ["QC / PSD / ERP 已可体验", "TFR / PAC / Connectivity 即将开放", "每个项目保留 MNE 对应方法"],
  },
  {
    id: "statistics",
    icon: "sigma",
    title: "统计",
    subtitle: "指标表与条件对比",
    body: "在被试或条件指标上做统计，避免把单个 trial 或单个通道当最终结论",
    evidence: ["条件对比", "效应量与校正", "统计风险提示"],
  },
  {
    id: "figures",
    icon: "file-chart-column",
    title: "绘图",
    subtitle: "科研级图表",
    body: "输出波形、频谱、topomap、时频图和统计图，图注绑定参数与方法",
    evidence: ["图片", "表格", "方法说明"],
  },
  {
    id: "download",
    icon: "download",
    title: "下载交付",
    subtitle: "图表、CSV、JSON、复现记录",
    body: "将图表、统计表、参数、软件版本、方法段和结果包一起交付",
    evidence: ["report.html", "CSV / JSON", "manifest / log / method"],
  },
];

const REVIEW_ROWS = [
  ["enabled", "先看数据能不能用", "QC 质控", "EEG 文件、通道信息、采样率和需要查看的时间窗", "波形预览、质量摘要、异常提示、质控图和可下载结果包", "正式处理前先做"],
  ["enabled", "看频段功率分布", "PSD 频谱", "静息态或任务态 EEG、频段范围、通道选择和数据时间段", "功率谱图、频段功率表、参数记录和方法说明", "比较组别或条件前先确认"],
  ["enabled", "看事件相关反应", "ERP", "连续 EEG、事件表、刺激编码、基线窗和分段时间窗", "平均波形、条件对比图、峰值指标、drop log 和结果文件", "适合 P300 / N400 等任务"],
  ["preview", "看时频变化", "TFR", "事件分段、频率范围、baseline、decimation 和内存预算", "时频图、功率变化矩阵和参数记录", "先用于方案确认"],
  ["preview", "看跨频耦合", "PAC", "相位频段、振幅频段、时间窗、替代检验和统计阈值", "耦合热图、显著性说明和方法边界", "需要人工复核"],
  ["preview", "看脑区连接关系", "Connectivity", "分区或通道方案、连接指标、频段、参考方式和体积传导控制", "连接矩阵、网络图、指标表和风险提示", "只作预览"],
  ["all", "确认科研交付物", "全部项目", "研究目的、数据类型、参数选择和复核人", "科研级图表、CSV、JSON、方法说明和完整下载包", "下载前核对参数"],
];

const moduleTests = {
  qc: [
    ["文件接入", "EDF/BDF/FIF/BrainVision/SET/CNT 可读；空文件、缺失通道和不支持格式给出清晰失败原因。"],
    ["信号质量", "展示采样率、时长、通道类型、平线/极端通道、注释、疑似坏道和质量判断。"],
    ["决策门槛", "说明 PSD/ERP 是否可继续，并标注哪些结论仍需人工复核。"],
  ],
  psd: [
    ["PSD 方法", "Welch 参数、fmin/fmax、窗长、重叠、picks、参考方式和频段定义均可见。"],
    ["交付物", "频段功率 CSV、通道级 CSV、summary JSON、方法文本和发表图均有链接。"],
    ["解释边界", "说明绝对/相对功率、参考敏感性、滤波敏感性和肌电风险。"],
  ],
  erp: [
    ["事件与分段", "event_id 映射、tmin/tmax、baseline、剔除规则、ROI 和成分时间窗必须明确。"],
    ["事件缺失", "事件缺失必须清晰失败；统计不能把 trial 当成独立被试。"],
    ["交付物", "Evoked/差异指标、ERP CSV、summary JSON、地形图/波形图和图注均有链接。"],
  ],
  tfr: [
    ["预览边界", "标记为仅预览；V01 后端执行尚未开放。"],
    ["MNE 方法", "frequencies、n_cycles、baseline 模式、decimation、ROI 和 ITC/power 选择均可见。"],
    ["统计策略", "生产开放前必须复核 cluster/permutation 或多重比较策略。"],
  ],
  pac: [
    ["预览边界", "标记为仅预览；生产使用前必须复核 surrogate/null model。"],
    ["滤波设置", "相位/振幅频段、滤波长度、Hilbert 边界处理、ROI 和 surrogate 次数均可见。"],
    ["假阳性风险", "说明非正弦波形、伪迹、边界效应和多重比较风险。"],
  ],
  connectivity: [
    ["预览边界", "标记为仅预览；指标、参考方式和体积传导控制是前置条件。"],
    ["矩阵契约", "metric、band、窗长、节点 ROI、阈值和 null model 均可见。"],
    ["交付物", "矩阵、网络图、边 CSV、图指标和敏感性说明均有链接。"],
  ],
};

const handoff = {
  qc: "当前可体验：数据接入、质量概览、坏道提示和质量判断",
  psd: "当前可体验：Welch 频谱、频段功率、通道级表格和可下载结果",
  erp: "当前可体验：事件映射、epoch 分段、ERP 波形、地形图和差异指标",
  tfr: "即将开放：先展示时频项目的输入、参数、输出和风险边界",
  pac: "即将开放：先展示相位振幅耦合的输入、参数、输出和风险边界",
  connectivity: "即将开放：先展示连接性矩阵、网络图、图指标和敏感性说明",
};

function icon(name) {
  return `<i data-lucide="${name}" aria-hidden="true"></i>`;
}

function h(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function api(path) {
  return `${API_BASE}${path}`;
}

async function apiJson(path, options = {}) {
  const response = await fetch(api(path), options);
  if (!response.ok) {
    let detail = await response.text();
    try { detail = JSON.parse(detail).detail || detail; } catch {}
    throw new Error(detail || `HTTP ${response.status}`);
  }
  return response.json();
}

function asset(url) {
  if (!url) return "";
  if (url.startsWith("http")) return url;
  if (url.startsWith("/")) return `.${url}`;
  return `./${url.replace(/^\.\//, "")}`;
}

function currentSlug() {
  const params = new URLSearchParams(window.location.search);
  const requested = params.get("module") || window.location.hash.replace("#", "");
  return MODULE_ORDER.includes(requested) ? requested : "";
}

async function loadManifest() {
  const response = await fetch(MANIFEST_URL, { cache: "no-store" });
  if (!response.ok) throw new Error(`manifest HTTP ${response.status}`);
  return response.json();
}

function modules(manifest) {
  const source = manifest.modules || {};
  return MODULE_ORDER.map((key) => source[key]).filter(Boolean);
}

function statusLabel(module) {
  return module.status || (module.statusLevel === "enabled" ? "已可体验" : "即将开放");
}

function statusClass(module) {
  return module.statusLevel === "enabled" ? "enabled" : "preview";
}

function moduleFigure(module) {
  return module.figures?.[0]?.src || "/assets/research-modules/figures/overview-main-figure.png";
}

function firstEnabledModule(manifest) {
  return modules(manifest).find((module) => module.statusLevel === "enabled") || modules(manifest)[0];
}

function renderTopbar(manifest, compact = false) {
  return `<nav class="lab-nav ${compact ? "compact" : ""}">
    <a class="brand" href="./module-lab.html" aria-label="分析实验室">
      <span class="brand-mark">QL</span>
      <span><strong>分析实验室</strong><small>免登录查看流程</small></span>
    </a>
    <div class="quick">
      <a href="./index.html">${icon("home")}正式工作台</a>
      <a href="./research-modules.html">${icon("layout-dashboard")}项目总览</a>
      <a class="pill" href="${asset(manifest.shared?.reviewer_checklist)}">${icon("clipboard-check")}复核清单</a>
    </div>
  </nav>`;
}

function renderOpenDesignDemo(manifest) {
  const allModules = modules(manifest);
  const enabled = allModules.filter((module) => module.statusLevel === "enabled").length;
  const preview = allModules.length - enabled;
  const featured = firstEnabledModule(manifest);
  return `<section class="demo-band" data-open-design-demo>
    <div class="section-head">
      <p class="eyebrow">免登录体验</p>
      <h1>分析实验室</h1>
      <p>按 EEG 主流程查看项目建立、数据导入、预览、分析、统计和下载</p>
    </div>
    <div class="demo-workbench">
      <aside class="stage-rail" aria-label="项目体验步骤">
        ${LAB_STAGES.map((stage, index) => `<button class="stage-button ${index === 0 ? "active" : ""}" type="button" data-stage="${stage.id}">
          ${icon(stage.icon)}
          <span><strong>${h(stage.title)}</strong><small>${h(stage.subtitle)}</small></span>
        </button>`).join("")}
      </aside>
      <article class="demo-canvas">
        <div class="canvas-toolbar">
          <span class="status enabled">免登录</span>
          <span>${enabled} 个已可体验</span>
          <span>${preview} 个即将开放</span>
        </div>
        <div class="open-design-panel">
          <div>
            <p class="eyebrow">体验状态</p>
            <h2 id="stageTitle">${h(LAB_STAGES[0].title)}</h2>
            <p id="stageBody">${h(LAB_STAGES[0].body)}</p>
          </div>
          <ul id="stageEvidence" class="evidence-list">
            ${LAB_STAGES[0].evidence.map((item) => `<li>${h(item)}</li>`).join("")}
          </ul>
        </div>
        <div class="module-strip" aria-label="项目快速选择">
          ${allModules.map((module) => `<a href="./module-lab.html?module=${h(module.slug)}" class="module-chip ${statusClass(module)}">
            <strong>${h(module.slug.toUpperCase())}</strong><span>${h(statusLabel(module))}</span>
          </a>`).join("")}
        </div>
        <div class="canvas-actions">
          <a class="btn primary" href="./module-lab.html?module=${h(featured?.slug || "qc")}">${icon("play")}体验 ${h((featured?.slug || "qc").toUpperCase())}</a>
          <a class="btn" href="#review-plan">${icon("list-checks")}查看使用边界</a>
        </div>
      </article>
      <aside class="handoff-panel">
        <h2>使用边界</h2>
        <dl>
          <div><dt>正式项目</dt><dd>登录后管理真实项目数据</dd></div>
          <div><dt>免登录</dt><dd>可先看流程、输入、参数和下载文件</dd></div>
          <div><dt>可查看</dt><dd>输入、参数、结果图表和下载文件</dd></div>
        </dl>
      </aside>
    </div>
  </section>`;
}

function renderReviewPlan() {
  return `<section class="review-band" id="review-plan" data-review-matrix>
    <div class="section-head row-head">
      <div>
        <p class="eyebrow">流程顺序</p>
        <h2>按什么顺序看</h2>
        <p>先确认数据、参数、输出和边界，再决定是否进入正式流程</p>
      </div>
      <div class="segmented" role="group" aria-label="体验范围过滤">
        <button class="active" type="button" data-review-filter="all">全部</button>
        <button type="button" data-review-filter="enabled">已可体验</button>
        <button type="button" data-review-filter="preview">即将开放</button>
      </div>
    </div>
    <div class="table-wrap">
      <table class="review-table">
        <thead><tr><th>研究问题</th><th>推荐项目</th><th>需要准备</th><th>可获得结果</th><th>建议</th></tr></thead>
        <tbody>
          ${REVIEW_ROWS.map(([scope, question, moduleName, inputs, outputs, gate]) => `<tr data-review-scope="${scope}"><td><strong>${h(question)}</strong><small>${scope === "all" ? "全部项目" : scope === "enabled" ? "已可体验" : "即将开放"}</small></td><td>${h(moduleName)}</td><td>${h(inputs)}</td><td>${h(outputs)}</td><td><span class="gate">${h(gate)}</span></td></tr>`).join("")}
        </tbody>
      </table>
    </div>
  </section>`;
}

function renderModuleGrid(manifest) {
  return `<section class="module-band">
    <div class="section-head">
      <p class="eyebrow">可体验项目</p>
      <h2>已开放的项目</h2>
      <p>先看 QC、PSD、ERP；其余项目保持预览状态</p>
    </div>
    <div class="module-grid">
      ${modules(manifest).map((module) => `<article class="module-card">
        <img src="${asset(moduleFigure(module))}" alt="${h(module.title)}" />
        <div class="body">
          <div class="module-card-top">
            <span class="status ${statusClass(module)}">${h(statusLabel(module))}</span>
            <span>${h(module.slug.toUpperCase())}</span>
          </div>
          <h2>${h(module.title)}</h2>
          <p>${h(module.subtitle || module.scenario)}</p>
          <div class="actions">
            <a class="btn primary" href="./module-lab.html?module=${h(module.slug)}">${icon("external-link")}开始体验</a>
            <a class="btn" href="${asset(module.package)}">${icon("archive")}结果包</a>
          </div>
        </div>
      </article>`).join("")}
    </div>
  </section>`;
}

function renderIndex(manifest) {
  return `<header class="lab-hero">${renderTopbar(manifest)}</header>
    <main class="lab-wrap">
      ${renderOpenDesignDemo(manifest)}
      ${renderReviewPlan()}
      ${renderModuleGrid(manifest)}
    </main>`;
}

function list(items, cls = "") {
  if (!items?.length) return `<div class="empty">暂无内容</div>`;
  return `<ul class="list ${cls}">${items.map((item) => `<li>${h(item)}</li>`).join("")}</ul>`;
}

function artifactCards(module) {
  const rows = [
    ...(module.tables || []).map((item) => ({ ...item, kind: "表格" })),
    ...(module.docs || []).map((item) => ({ ...item, kind: item.type === "json" ? "JSON" : "文档" })),
    module.package ? { label: "结果包", src: module.package, kind: "ZIP" } : null,
  ].filter(Boolean);
  if (!rows.length) return `<div class="empty">暂无文件</div>`;
  return rows.map((item) => `<a class="artifact" data-doc-preview href="${asset(item.src)}">
    <span>${h(item.kind)}</span>
    <strong>${h(item.label)}</strong>
    <small>${h(item.src)}</small>
  </a>`).join("");
}

function testRows(slug) {
  return (moduleTests[slug] || []).map(([name, rule]) => `<tr><td><strong>${h(name)}</strong></td><td>${h(rule)}</td></tr>`).join("");
}

function renderBackendDemo(module) {
  if (!DEMO_MODULES.has(module.slug)) {
    return `<section class="panel demo-runner"><h2>后端服务</h2><p>该项目目前是方法预览，后端执行开放前会先完成统计、参数和风险评审。</p></section>`;
  }
  return `<section class="panel demo-runner" id="backend-demo" data-demo-module="${h(module.slug)}">
    <div class="runner-head">
      <div>
        <p class="eyebrow">后端示例</p>
        <h2>运行内置教学数据</h2>
        <p>使用合成 oddball EDF 跑 ${h(module.slug.toUpperCase())}，返回任务状态、结果文件和复现材料。</p>
      </div>
      <button class="btn primary" type="button" data-demo-run="${h(module.slug)}">${icon("play")}运行示例</button>
    </div>
    <div class="demo-result" data-demo-result>还没有运行。点击按钮后会调用后端服务。</div>
  </section>`;
}

function renderDemoResult(task, artifacts) {
  const links = artifacts.slice(0, 8).map((item) => `<a class="artifact" href="${api(`/artifacts/${item.id}/download`)}" target="_blank" rel="noopener">
    <span>${h(item.artifact_type)}</span><strong>${h(item.label)}</strong><small>${h(item.path)}</small>
  </a>`).join("");
  return `<div class="demo-status ok">
    <strong>任务完成：${h(task.module_name.toUpperCase())}</strong>
    <span>task_id：${h(task.id)} · workflow：${h(task.workflow_id)} · status：${h(task.status)}</span>
  </div>
  <div class="artifact-grid compact">${links || `<div class="empty">暂无产物</div>`}</div>`;
}

function renderSide(manifest, slug) {
  return `<aside class="side">
    <h2>流程导航</h2>
    <nav>
      ${SECTION_ANCHORS.map((anchor) => `<a href="#${anchor.id}"><span>${h(anchor.label)}</span>${icon("chevron-right")}</a>`).join("")}
    </nav>
    <hr />
    <h2>项目</h2>
    <nav>
      ${modules(manifest).map((module) => `<a class="${module.slug === slug ? "active" : ""}" href="./module-lab.html?module=${h(module.slug)}"><span>${h(module.title)}</span><strong>${h(module.slug.toUpperCase())}</strong></a>`).join("")}
    </nav>
  </aside>`;
}

function renderDetail(manifest, slug) {
  const module = manifest.modules?.[slug];
  if (!module) return renderIndex(manifest);
  return `<header class="lab-hero detail-top">${renderTopbar(manifest, true)}</header>
  <main class="lab-wrap detail-shell">
    ${renderSide(manifest, slug)}
    <div class="content">
      <section class="module-hero">
        <span class="status ${statusClass(module)}">${h(statusLabel(module))}</span>
        <p class="eyebrow">${h(module.slug.toUpperCase())} 详情</p>
        <h1>${h(module.title)}</h1>
        <p>${h(module.scenario || module.subtitle)}</p>
        <div class="module-links">
          ${slug === "qc" ? `<a class="btn primary" href="./qc-lab.html">${icon("activity")}体验 QC 预览</a>` : ""}
          <a class="btn primary" href="${asset(module.package)}">${icon("archive")}下载结果包</a>
          <a class="btn" href="${asset(manifest.shared?.reviewer_checklist)}">${icon("clipboard-check")}复核清单</a>
          <a class="btn" href="./module-lab.html#review-plan">${icon("arrow-left")}返回分析实验室</a>
        </div>
      </section>
      ${renderBackendDemo(module)}
      <section class="panel grid-2" id="inputs">
        <div><h2>输入</h2>${list(module.inputs)}</div>
        <div id="controls"><h2>参数</h2>${list(module.controls)}</div>
      </section>
      <section class="panel grid-2" id="mne">
        <div><h2>MNE 方法</h2>${list(module.mneObjects)}</div>
        <div id="outputs"><h2>输出</h2>${list(module.outputs)}</div>
      </section>
      <section class="panel" id="figures"><h2>图像输出</h2><div class="figure-grid">${(module.figures || []).map((fig) => `<figure class="figure"><img src="${asset(fig.src)}" alt="${h(fig.alt || fig.label)}" /><figcaption>${h(fig.label)}</figcaption></figure>`).join("")}</div></section>
      <section class="panel" id="artifacts"><h2>文件与交付物</h2><div class="artifact-grid">${artifactCards(module)}</div></section>
      <section class="panel" id="tests"><h2>检查清单</h2><div class="table-wrap"><table class="test-matrix"><thead><tr><th>检查项</th><th>验收规则</th></tr></thead><tbody>${testRows(slug)}</tbody></table></div></section>
      <section class="panel callout" id="risks"><h2>科研边界与风险</h2>${list(module.risks, "risk")}<p><strong>当前状态：</strong>${h(handoff[slug])}</p><p><strong>共享边界：</strong>${h(manifest.researchGuardrail)}</p></section>
    </div>
  </main>`;
}

function bindDemoRunner() {
  document.querySelectorAll("[data-demo-run]").forEach((button) => {
    button.addEventListener("click", async () => {
      const module = button.dataset.demoRun;
      const box = document.querySelector("[data-demo-result]");
      button.disabled = true;
      if (box) box.innerHTML = `<div class="demo-status">正在运行 ${h(module.toUpperCase())} 示例，请稍候...</div>`;
      try {
        const task = await apiJson(`/lab/demo/run/${encodeURIComponent(module)}`, { method: "POST" });
        const artifacts = await apiJson(`/tasks/${encodeURIComponent(task.id)}/artifacts`);
        if (box) box.innerHTML = renderDemoResult(task, artifacts);
      } catch (error) {
        if (box) box.innerHTML = `<div class="demo-status error">运行失败：${h(error.message || error)}</div>`;
      } finally {
        button.disabled = false;
        if (window.lucide) window.lucide.createIcons();
      }
    });
  });
}

function bindIndexInteractions() {
  const stageButtons = [...document.querySelectorAll("[data-stage]")];
  const title = document.querySelector("#stageTitle");
  const body = document.querySelector("#stageBody");
  const evidence = document.querySelector("#stageEvidence");
  stageButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const stage = LAB_STAGES.find((item) => item.id === button.dataset.stage);
      if (!stage) return;
      stageButtons.forEach((item) => item.classList.toggle("active", item === button));
      title.textContent = stage.title;
      body.textContent = stage.body;
      evidence.innerHTML = stage.evidence.map((item) => `<li>${h(item)}</li>`).join("");
      if (window.lucide) window.lucide.createIcons();
    });
  });

  const filterButtons = [...document.querySelectorAll("[data-review-filter]")];
  const rows = [...document.querySelectorAll("[data-review-scope]")];
  filterButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const filter = button.dataset.reviewFilter;
      filterButtons.forEach((item) => item.classList.toggle("active", item === button));
      rows.forEach((row) => {
        const visible = filter === "all" || row.dataset.reviewScope === "all" || row.dataset.reviewScope === filter;
        row.hidden = !visible;
      });
    });
  });
}

async function main() {
  const root = document.querySelector("#moduleLab");
  try {
    const manifest = await loadManifest();
    const slug = currentSlug();
    root.innerHTML = slug ? renderDetail(manifest, slug) : renderIndex(manifest);
    if (!slug) bindIndexInteractions();
    if (slug) bindDemoRunner();
    if (window.lucide) window.lucide.createIcons();
  } catch (error) {
    root.innerHTML = `<section class="lab-wrap"><div class="empty">分析实验室加载失败：${h(error.message || error)}</div></section>`;
  }
}

main();
