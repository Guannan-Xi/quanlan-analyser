const MANIFEST_URL = "./assets/research-modules/reproducibility/research_module_manifest.json";
const MODULE_ORDER = ["qc", "psd", "erp", "tfr", "pac", "connectivity"];
const SECTION_ANCHORS = [
  { id: "inputs", label: "输入" },
  { id: "controls", label: "参数" },
  { id: "mne", label: "MNE 方法" },
  { id: "outputs", label: "输出" },
  { id: "figures", label: "图像" },
  { id: "artifacts", label: "文件" },
  { id: "tests", label: "验收" },
  { id: "risks", label: "风险" },
];

const LAB_STAGES = [
  {
    id: "entry",
    icon: "door-open",
    title: "免登录入口",
    subtitle: "实验室和正式工作台分离",
    body: "Open Design 入口直接进入独立模块实验室；正式工作台仍保留登录、注册和管理员入口。",
    evidence: ["module-lab.html 可直接访问", "index.html 只保留跳转链接", "不调用后端鉴权接口"],
  },
  {
    id: "choose",
    icon: "layout-grid",
    title: "选择模块",
    subtitle: "QC / PSD / ERP 已启用，TFR / PAC / Connectivity 为预研",
    body: "模块卡片只读取静态 manifest 和审核资产，适合客户、PI、算法同事在合并前逐项确认。",
    evidence: ["6 个模块入口", "启用/预研状态可见", "每个模块可单独打开"],
  },
  {
    id: "review",
    icon: "clipboard-check",
    title: "UI/交互评审",
    subtitle: "围绕研究者要判断的内容组织界面",
    body: "评审重点覆盖输入、参数、MNE 对齐、输出证据、失败状态、风险边界和响应式表现。",
    evidence: ["评审矩阵可过滤", "模块详情页有验收表", "风险提示不进入正式结论"],
  },
  {
    id: "handoff",
    icon: "package-check",
    title: "证据包交付",
    subtitle: "先审 demo，再合并正式页面",
    body: "每个模块保留图像、CSV、JSON、方法说明和压缩包链接，作为本轮 UI 审核和后续实现交接材料。",
    evidence: ["静态文件存在性检查", "文案无损坏检查", "Playwright 页面验收"],
  },
];

const REVIEW_ROWS = [
  ["all", "入口边界", "实验室免登录可访问，正式工作台仍要求登录/注册", "从首页进入实验室，再返回正式入口；不出现预登录 demo 项目按钮", "必须通过"],
  ["all", "Open Design 首屏", "首屏展示真实模块选择、审核状态和证据包，不做营销页", "切换入口 demo 阶段，检查当前状态是否清晰", "必须通过"],
  ["enabled", "已启用模块", "QC / PSD / ERP 的输入、参数、输出和文件证据可审核", "逐个打开模块详情页，核对图像、表格、方法说明和压缩包", "必须通过"],
  ["preview", "预研模块", "TFR / PAC / Connectivity 明确标记预研边界", "检查预研模块是否避免给出生产可用承诺", "必须通过"],
  ["all", "参数理解", "核心参数与 MNE 对象名称同时出现，研究者能判断方法是否合理", "检查参数、MNE 方法、输出三段是否能互相对应", "建议通过"],
  ["all", "交互状态", "按钮、筛选、详情页导航和下载链接有明确目标", "键盘切换焦点，确认悬停和选中状态稳定", "建议通过"],
  ["all", "风险说明", "科研边界、临床禁用、统计风险和人工复核边界可见", "检查风险段落是否出现在每个模块详情页", "必须通过"],
  ["all", "本地验收", "静态页面、图片、CSV、JSON、文档和实验室入口均可本地验证", "运行 research modules 静态验收脚本", "必须通过"],
];

const moduleTests = {
  qc: [
    ["文件接入", "EDF/BDF/FIF/BrainVision/SET/CNT 可读；空文件、缺失通道和不支持格式给出清晰失败原因。"],
    ["信号质量", "展示采样率、时长、通道类型、平线/极端通道、注释、疑似坏道和可分析性。"],
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
    ["预览边界", "标记为仅预览；V01 后端执行尚未启用。"],
    ["MNE 设计", "frequencies、n_cycles、baseline 模式、decimation、ROI 和 ITC/power 选择均可见。"],
    ["统计策略", "生产启用前必须复核 cluster/permutation 或多重比较策略。"],
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
  qc: "并行开发交接：先连接后端 QC 契约；输出 qc_summary.json、parameters.json、method_description.txt 和可审计日志。",
  psd: "并行开发交接：稳定 Welch 参数、频段定义、通道级表格和被试级统计。",
  erp: "并行开发交接：优先验证事件和 epoch；事件缺失必须给出可读错误。",
  tfr: "并行开发交接：baseline、wavelet 和 cluster statistics 审查完成前，只保留预览 UI/契约。",
  pac: "并行开发交接：surrogate/null model 与滤波边界测试完成前，只保留预览 UI/契约。",
  connectivity: "并行开发交接：参考方式、体积传导和阈值敏感性审查完成前，只保留预览 UI/契约。",
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
  return module.status || (module.statusLevel === "enabled" ? "V01 已启用" : "预研预览");
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
    <a class="brand" href="./module-lab.html" aria-label="QLanalyser 分析实验室">
      <span class="brand-mark">QL</span>
      <span><strong>QLanalyser 分析实验室</strong><small>Open Design 免登录入口 demo</small></span>
    </a>
    <div class="quick">
      <a href="./index.html">${icon("home")}正式入口</a>
      <a href="./research-modules.html">${icon("layout-dashboard")}研究模块总览</a>
      <a class="pill" href="${asset(manifest.shared?.reviewer_checklist)}">${icon("clipboard-check")}评审清单</a>
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
      <p class="eyebrow">Open Design entrance demo</p>
      <h1>独立分析模块实验室</h1>
      <p>先把入口、模块 UI、交互状态和科研边界作为可审核 demo 固定下来；你确认后，再决定哪些内容合并到正式页面。</p>
    </div>
    <div class="demo-workbench">
      <aside class="stage-rail" aria-label="Open Design demo 阶段">
        ${LAB_STAGES.map((stage, index) => `<button class="stage-button ${index === 0 ? "active" : ""}" type="button" data-stage="${stage.id}">
          ${icon(stage.icon)}
          <span><strong>${h(stage.title)}</strong><small>${h(stage.subtitle)}</small></span>
        </button>`).join("")}
      </aside>
      <article class="demo-canvas">
        <div class="canvas-toolbar">
          <span class="status enabled">免登录实验室</span>
          <span>${enabled} 个已启用</span>
          <span>${preview} 个预研</span>
        </div>
        <div class="open-design-panel">
          <div>
            <p class="eyebrow">Current review state</p>
            <h2 id="stageTitle">${h(LAB_STAGES[0].title)}</h2>
            <p id="stageBody">${h(LAB_STAGES[0].body)}</p>
          </div>
          <ul id="stageEvidence" class="evidence-list">
            ${LAB_STAGES[0].evidence.map((item) => `<li>${h(item)}</li>`).join("")}
          </ul>
        </div>
        <div class="module-strip" aria-label="模块快速入口">
          ${allModules.map((module) => `<a href="./module-lab.html?module=${h(module.slug)}" class="module-chip ${statusClass(module)}">
            <strong>${h(module.slug.toUpperCase())}</strong><span>${h(statusLabel(module))}</span>
          </a>`).join("")}
        </div>
        <div class="canvas-actions">
          <a class="btn primary" href="./module-lab.html?module=${h(featured?.slug || "qc")}">${icon("play")}打开 ${h((featured?.slug || "qc").toUpperCase())} demo</a>
          <a class="btn" href="#review-plan">${icon("list-checks")}查看评审方案</a>
        </div>
      </article>
      <aside class="handoff-panel">
        <h2>本轮审核边界</h2>
        <dl>
          <div><dt>不改</dt><dd>正式入口、后端接口、算法执行链路</dd></div>
          <div><dt>保留</dt><dd>实验室免登录，正式工作台登录/注册</dd></div>
          <div><dt>产出</dt><dd>可审核 demo 页面、模块 UI 清单、静态验收报告</dd></div>
        </dl>
      </aside>
    </div>
  </section>`;
}

function renderReviewPlan() {
  return `<section class="review-band" id="review-plan" data-review-matrix>
    <div class="section-head row-head">
      <div>
        <p class="eyebrow">UI / interaction review</p>
        <h2>实验室模块 UI/交互评审方案</h2>
        <p>用同一张矩阵确认入口边界、模块状态、研究证据和风险提示，避免 demo 阶段把预研内容误合并进正式工作台。</p>
      </div>
      <div class="segmented" role="group" aria-label="评审范围过滤">
        <button class="active" type="button" data-review-filter="all">全部</button>
        <button type="button" data-review-filter="enabled">已启用</button>
        <button type="button" data-review-filter="preview">预研</button>
      </div>
    </div>
    <div class="table-wrap">
      <table class="review-table">
        <thead><tr><th>评审项</th><th>通过标准</th><th>操作方式</th><th>结论门槛</th></tr></thead>
        <tbody>
          ${REVIEW_ROWS.map(([scope, item, standard, action, gate]) => `<tr data-review-scope="${scope}"><td><strong>${h(item)}</strong><small>${scope === "all" ? "全模块" : scope === "enabled" ? "QC / PSD / ERP" : "TFR / PAC / Connectivity"}</small></td><td>${h(standard)}</td><td>${h(action)}</td><td><span class="gate">${h(gate)}</span></td></tr>`).join("")}
        </tbody>
      </table>
    </div>
  </section>`;
}

function renderModuleGrid(manifest) {
  return `<section class="module-band">
    <div class="section-head">
      <p class="eyebrow">Module demos</p>
      <h2>模块入口</h2>
      <p>每个入口都是独立静态页面，只读取研究模块 manifest 和本地样例资产，适合先审 UI、交互和交付物。</p>
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
            <a class="btn primary" href="./module-lab.html?module=${h(module.slug)}">${icon("external-link")}打开 demo</a>
            <a class="btn" href="${asset(module.package)}">${icon("archive")}证据包</a>
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
    module.package ? { label: "模块证据包", src: module.package, kind: "ZIP" } : null,
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

function renderSide(manifest, slug) {
  return `<aside class="side">
    <h2>模块导航</h2>
    <nav>
      ${modules(manifest).map((module) => `<a class="${module.slug === slug ? "active" : ""}" href="./module-lab.html?module=${h(module.slug)}"><span>${h(module.title)}</span><strong>${h(module.slug.toUpperCase())}</strong></a>`).join("")}
    </nav>
    <hr />
    ${SECTION_ANCHORS.map((anchor) => `<a href="#${anchor.id}"><span>${h(anchor.label)}</span>${icon("chevron-right")}</a>`).join("")}
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
        <p class="eyebrow">${h(module.slug.toUpperCase())} independent module demo</p>
        <h1>${h(module.title)}</h1>
        <p>${h(module.scenario || module.subtitle)}</p>
        <div class="module-links">
          <a class="btn primary" href="${asset(module.package)}">${icon("archive")}下载证据包</a>
          <a class="btn" href="${asset(manifest.shared?.reviewer_checklist)}">${icon("clipboard-check")}评审清单</a>
          <a class="btn" href="./module-lab.html#review-plan">${icon("arrow-left")}返回实验室</a>
        </div>
      </section>
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
      <section class="panel" id="tests"><h2>模块验收矩阵</h2><div class="table-wrap"><table class="test-matrix"><thead><tr><th>检查项</th><th>验收规则</th></tr></thead><tbody>${testRows(slug)}</tbody></table></div></section>
      <section class="panel callout" id="risks"><h2>科研边界与风险</h2>${list(module.risks, "risk")}<p><strong>并行开发交接：</strong>${h(handoff[slug])}</p><p><strong>共享边界：</strong>${h(manifest.researchGuardrail)}</p></section>
    </div>
  </main>`;
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
    if (window.lucide) window.lucide.createIcons();
  } catch (error) {
    root.innerHTML = `<section class="lab-wrap"><div class="empty">分析实验室加载失败：${h(error.message || error)}</div></section>`;
  }
}

main();