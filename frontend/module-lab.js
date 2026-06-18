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

const moduleTests = {
  qc: [
    ["文件接入", "EDF/BDF/FIF/BrainVision/SET/CNT 可读取；空文件、缺失通道和不支持格式要给出清晰失败原因。"],
    ["信号质量", "展示采样率、时长、通道类型、平线/极端通道、注释、疑似坏道和可分析性。"],
    ["决策门槛", "明确 PSD/ERP 是否可继续，并说明为什么仍需要人工复核。"],
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
    ["矩阵契约", "metric、band、窗长、节点/ROI、阈值和 null model 均可见。"],
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
  return String(value ?? "").replace(/[&<>'"]/g, (ch) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "'": "&#39;",
    '"': "&quot;",
  }[ch]));
}

function statusClass(module) {
  return module.statusLevel === "enabled" ? "enabled" : "preview";
}

function asset(url) {
  if (!url) return "#";
  if (url.startsWith("http") || url.startsWith("./") || url.startsWith("../")) return url;
  return url.startsWith("/") ? `.${url}` : `./${url}`;
}

function currentSlug() {
  const params = new URLSearchParams(location.search);
  const fromQuery = params.get("module");
  if (fromQuery) return fromQuery;
  const hash = location.hash.replace(/^#/, "");
  return hash || "";
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

function moduleFigure(module) {
  return module.figures?.[0]?.src || "./assets/qlanalyser-neuron-firing-bg.png";
}

function renderHero(manifest) {
  const allModules = modules(manifest);
  const enabled = allModules.filter((module) => module.statusLevel === "enabled").length;
  const preview = allModules.length - enabled;
  return `<header class="lab-hero">
    <nav class="lab-nav">
      <a class="brand" href="./module-lab.html" aria-label="QLanalyser 分析实验室">
        <span class="brand-mark">QL</span>
        <span><strong>QLanalyser 分析实验室</strong><small>免登录独立模块试用</small></span>
      </a>
      <div class="quick">
        <a href="./index.html">${icon("home")}产品入口</a>
        <a href="./research-modules.html">${icon("layout-dashboard")}研究模块总览</a>
        <a class="pill" href="${asset(manifest.shared?.reviewer_checklist)}">${icon("clipboard-check")}评审清单</a>
      </div>
    </nav>
    <section class="lab-hero-grid">
      <div>
        <p class="eyebrow">参考 MNE 规范 | EEG 独立模块实验室</p>
        <h1>独立分析模块实验室</h1>
        <p>QC、PSD、ERP、TFR、PAC 和 Connectivity 已拆成稳定的免登录模块页面。每个页面都展示科研用户需要检查的输入、参数、MNE 对象、输出、图像、文件、风险和并行开发交接点。</p>
      </div>
      <aside class="hero-card">
        <strong>${allModules.length} 个模块入口</strong>
        <span>${enabled} 个 V01 已启用模块 | ${preview} 个预览模块</span>
        <ul>
          <li>客户试用单个分析模块无需登录。</li>
          <li>每个模块都有稳定 URL，便于并行开发和评审。</li>
          <li>合成数据仅用于科研流程测试，不用于临床诊断。</li>
        </ul>
      </aside>
    </section>
  </header>`;
}

function renderIndex(manifest) {
  return `${renderHero(manifest)}<section class="lab-wrap">
    <div class="lab-section-head">
      <h2>选择一个分析模块</h2>
      <p>这些 URL 可用于下午并行开发，也可用于让客户单独试用某个模块。</p>
    </div>
    <div class="module-grid">
      ${modules(manifest).map((module) => `<article class="module-card">
        <img src="${asset(moduleFigure(module))}" alt="${h(module.title)} 预览图" />
        <div class="body">
          <span class="status ${statusClass(module)}">${h(module.status)}</span>
          <h2>${h(module.title)}</h2>
          <p>${h(module.subtitle)}</p>
          <p>${h(module.scenario)}</p>
          <div class="actions">
            <a class="btn primary" href="./module-lab.html?module=${h(module.slug)}">${icon("external-link")}打开模块实验室</a>
            <a class="btn" href="./research-module/${h(module.page)}">${icon("package-open")}静态交付页面</a>
          </div>
        </div>
      </article>`).join("")}
    </div>
  </section>`;
}

function list(items, cls = "") {
  const content = (items || []).map((item) => `<li>${h(item)}</li>`).join("") || `<li>待补充</li>`;
  return `<ul class="list ${cls}">${content}</ul>`;
}

function artifactCards(module) {
  const cards = [];
  for (const table of module.tables || []) cards.push({ label: table.label, src: table.src, type: "CSV 表格" });
  for (const doc of module.docs || []) cards.push({ label: doc.label, src: doc.src, type: doc.type || "文档" });
  if (module.package) cards.push({ label: "模块测试包", src: module.package, type: "ZIP 包" });
  return cards.map((card) => `<a class="artifact" href="${asset(card.src)}" data-doc-preview="${h(card.type)}">
    <strong>${h(card.label)}</strong>
    <span>${h(card.type)}</span><br />
    <small>${h(card.src)}</small>
  </a>`).join("");
}

function testRows(slug) {
  return (moduleTests[slug] || []).map(([name, detail]) => `<tr><td>${h(name)}</td><td>${h(detail)}</td></tr>`).join("");
}

function renderSide(manifest, slug) {
  const moduleLinks = modules(manifest).map((module) => `<a class="${module.slug === slug ? "active" : ""}" href="./module-lab.html?module=${h(module.slug)}"><span>${h(module.slug.toUpperCase())}</span><small>${module.statusLevel === "enabled" ? "V01" : "预览"}</small></a>`).join("");
  const sectionLinks = SECTION_ANCHORS.map((section) => `<a href="#${h(section.id)}"><span>${h(section.label)}</span><small>#${h(section.id)}</small></a>`).join("");
  return `<aside class="side"><h2>模块导航</h2>${moduleLinks}<h2>页面结构</h2>${sectionLinks}</aside>`;
}

function renderDetail(manifest, slug) {
  const module = manifest.modules?.[slug];
  if (!module) {
    return `${renderHero(manifest)}<section class="lab-wrap"><div class="empty">未找到模块：${h(slug)}。请返回实验室总览。</div></section>`;
  }
  return `${renderHero(manifest)}<section class="lab-wrap detail-shell">
    ${renderSide(manifest, slug)}
    <div class="content">
      <section class="module-hero">
        <span class="status ${statusClass(module)}">${h(module.status)}</span>
        <h1>${h(module.title)}</h1>
        <p>${h(module.subtitle)}</p>
        <p>${h(module.scenario)}</p>
        <div class="module-links">
          <a class="btn primary" href="./module-lab.html?module=${h(module.slug)}">${icon("link")}当前独立 URL</a>
          <a class="btn" href="./module-lab.html">${icon("grid-3x3")}返回实验室总览</a>
          <a class="btn" href="./research-module/${h(module.page)}">${icon("package-open")}静态交付页面</a>
        </div>
      </section>
      <section class="panel grid-2">
        <div id="inputs"><h2>输入</h2>${list(module.inputs)}</div>
        <div id="controls"><h2>参数 / 控件</h2>${list(module.controls)}</div>
      </section>
      <section class="panel grid-2">
        <div id="mne"><h2>MNE 对象 / 方法</h2>${list(module.mneObjects)}</div>
        <div id="outputs"><h2>输出</h2>${list(module.outputs)}</div>
      </section>
      <section class="panel" id="figures"><h2>图像输出</h2><div class="figure-grid">${(module.figures || []).map((fig) => `<figure class="figure"><img src="${asset(fig.src)}" alt="${h(fig.alt || fig.label)}" /><figcaption>${h(fig.label)}</figcaption></figure>`).join("")}</div></section>
      <section class="panel" id="artifacts"><h2>文件与交付物</h2><div class="artifact-grid">${artifactCards(module)}</div></section>
      <section class="panel" id="tests"><h2>模块验收矩阵</h2><table class="test-matrix"><thead><tr><th>检查项</th><th>验收规则</th></tr></thead><tbody>${testRows(slug)}</tbody></table></section>
      <section class="panel callout" id="risks"><h2>科研边界与风险</h2>${list(module.risks, "risk")}<p><strong>并行开发交接：</strong>${h(handoff[slug])}</p><p><strong>共享边界：</strong>${h(manifest.researchGuardrail)}</p></section>
    </div>
  </section>`;
}

async function main() {
  const root = document.querySelector("#moduleLab");
  try {
    const manifest = await loadManifest();
    const slug = currentSlug();
    root.innerHTML = slug ? renderDetail(manifest, slug) : renderIndex(manifest);
    if (window.lucide) window.lucide.createIcons();
  } catch (error) {
    root.innerHTML = `<section class="lab-wrap"><div class="empty">分析实验室加载失败：${h(error.message || error)}</div></section>`;
  }
}

main();
