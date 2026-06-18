const MANIFEST_URL = "./assets/research-modules/reproducibility/research_module_manifest.json";
const MODULE_ORDER = ["qc", "psd", "erp", "tfr", "pac", "connectivity"];
const SECTION_ANCHORS = [
  { id: "inputs", label: "Inputs" },
  { id: "controls", label: "Parameters" },
  { id: "mne", label: "MNE methods" },
  { id: "outputs", label: "Outputs" },
  { id: "figures", label: "Figures" },
  { id: "artifacts", label: "Files" },
  { id: "tests", label: "Acceptance" },
  { id: "risks", label: "Risks" },
];

const moduleTests = {
  qc: [
    ["File intake", "EDF/BDF/FIF/BrainVision/SET/CNT can be read; empty files, missing channels, and unsupported formats fail clearly."],
    ["Signal quality", "Show sampling rate, duration, channel types, flat/extreme channels, annotations, bad-channel candidates, and analyzability."],
    ["Decision gate", "Expose whether PSD/ERP may proceed and why manual review is still required."],
  ],
  psd: [
    ["PSD method", "Welch parameters, fmin/fmax, window, overlap, picks, reference, and band definitions are visible."],
    ["Deliverables", "Band-power CSV, channel-level CSV, summary JSON, method text, and publication figure are linked."],
    ["Interpretation guard", "State absolute vs relative power, reference sensitivity, filtering sensitivity, and EMG risk."],
  ],
  erp: [
    ["Events and epochs", "event_id mapping, tmin/tmax, baseline, rejection, ROI, and component windows are explicit."],
    ["Missing events", "Missing events must fail clearly; statistics must not treat trials as independent subjects."],
    ["Deliverables", "Evoked/difference metrics, ERP CSV, summary JSON, topomap/waveform figures, and captions are linked."],
  ],
  tfr: [
    ["Preview boundary", "Marked preview-only; V01 backend execution is not enabled."],
    ["MNE design", "frequencies, n_cycles, baseline mode, decimation, ROI, and ITC/power selection are visible."],
    ["Statistics", "Cluster/permutation or multiple-comparison strategy must be reviewed before production enablement."],
  ],
  pac: [
    ["Preview boundary", "Marked preview-only; production use requires surrogate/null model review."],
    ["Filtering", "phase/amplitude bands, filter length, Hilbert edge handling, ROI, and surrogate count are visible."],
    ["False-positive risks", "Non-sinusoidal waveforms, artifacts, boundary effects, and multiple comparisons are stated."],
  ],
  connectivity: [
    ["Preview boundary", "Marked preview-only; metric, reference, and volume-conduction controls are prerequisites."],
    ["Matrix contract", "metric, band, window length, nodes/ROIs, threshold, and null model are visible."],
    ["Deliverables", "Matrix, network graph, edge CSV, graph metrics, and sensitivity notes are linked."],
  ],
};

const handoff = {
  qc: "Parallel handoff: connect the backend QC contract first; output qc_summary.json, parameters.json, method_description.txt, and auditable logs.",
  psd: "Parallel handoff: stabilize Welch parameters, band definitions, channel-level tables, and subject-level statistics.",
  erp: "Parallel handoff: prioritize event and epoch validation; missing events must fail with a readable error.",
  tfr: "Parallel handoff: keep preview UI/contract only until baseline, wavelet, and cluster-statistics review is complete.",
  pac: "Parallel handoff: keep preview UI/contract only until surrogate/null model and filtering-edge tests are complete.",
  connectivity: "Parallel handoff: keep preview UI/contract only until reference, volume conduction, and threshold-sensitivity reviews are complete.",
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
      <a class="brand" href="./module-lab.html" aria-label="QLanalyser Analysis Lab">
        <span class="brand-mark">QL</span>
        <span><strong>QLanalyser Analysis Lab</strong><small>No-login standalone module trials</small></span>
      </a>
      <div class="quick">
        <a href="./index.html">${icon("home")}Product entry</a>
        <a href="./research-modules.html">${icon("layout-dashboard")}Research overview</a>
        <a class="pill" href="${asset(manifest.shared?.reviewer_checklist)}">${icon("clipboard-check")}Review checklist</a>
      </div>
    </nav>
    <section class="lab-hero-grid">
      <div>
        <p class="eyebrow">MNE-informed - standalone EEG module lab</p>
        <h1>Standalone analysis module lab</h1>
        <p>QC, PSD, ERP, TFR, PAC, and Connectivity are split into stable no-login module pages. Each page exposes the inputs, parameters, MNE objects, outputs, figures, files, risks, and parallel-development handoff points that scientific users need to inspect.</p>
      </div>
      <aside class="hero-card">
        <strong>${allModules.length} module entries</strong>
        <span>${enabled} V01-enabled modules - ${preview} preview modules</span>
        <ul>
          <li>No login required for customer module trials.</li>
          <li>Each module has a stable URL for parallel development.</li>
          <li>Synthetic data are for research workflow testing only.</li>
        </ul>
      </aside>
    </section>
  </header>`;
}

function renderIndex(manifest) {
  return `${renderHero(manifest)}<section class="lab-wrap">
    <div class="lab-section-head">
      <h2>Choose an analysis module</h2>
      <p>Use these URLs for afternoon parallel development or for exposing a single module to a customer trial.</p>
    </div>
    <div class="module-grid">
      ${modules(manifest).map((module) => `<article class="module-card">
        <img src="${asset(moduleFigure(module))}" alt="${h(module.title)} preview" />
        <div class="body">
          <span class="status ${statusClass(module)}">${h(module.status)}</span>
          <h2>${h(module.title)}</h2>
          <p>${h(module.subtitle)}</p>
          <p>${h(module.scenario)}</p>
          <div class="actions">
            <a class="btn primary" href="./module-lab.html?module=${h(module.slug)}">${icon("external-link")}Open module lab</a>
            <a class="btn" href="./research-module/${h(module.page)}">${icon("package-open")}Static deliverable page</a>
          </div>
        </div>
      </article>`).join("")}
    </div>
  </section>`;
}

function list(items, cls = "") {
  const content = (items || []).map((item) => `<li>${h(item)}</li>`).join("") || `<li>To be completed</li>`;
  return `<ul class="list ${cls}">${content}</ul>`;
}

function artifactCards(module) {
  const cards = [];
  for (const table of module.tables || []) cards.push({ label: table.label, src: table.src, type: "CSV table" });
  for (const doc of module.docs || []) cards.push({ label: doc.label, src: doc.src, type: doc.type || "document" });
  if (module.package) cards.push({ label: "Module test package", src: module.package, type: "ZIP package" });
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
  const moduleLinks = modules(manifest).map((module) => `<a class="${module.slug === slug ? "active" : ""}" href="./module-lab.html?module=${h(module.slug)}"><span>${h(module.slug.toUpperCase())}</span><small>${module.statusLevel === "enabled" ? "V01" : "Preview"}</small></a>`).join("");
  const sectionLinks = SECTION_ANCHORS.map((section) => `<a href="#${h(section.id)}"><span>${h(section.label)}</span><small>#${h(section.id)}</small></a>`).join("");
  return `<aside class="side"><h2>Module navigation</h2>${moduleLinks}<h2>Page structure</h2>${sectionLinks}</aside>`;
}

function renderDetail(manifest, slug) {
  const module = manifest.modules?.[slug];
  if (!module) {
    return `${renderHero(manifest)}<section class="lab-wrap"><div class="empty">Module not found: ${h(slug)}. Please return to the lab overview.</div></section>`;
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
          <a class="btn primary" href="./module-lab.html?module=${h(module.slug)}">${icon("link")}Current standalone URL</a>
          <a class="btn" href="./module-lab.html">${icon("grid-3x3")}Back to lab overview</a>
          <a class="btn" href="./research-module/${h(module.page)}">${icon("package-open")}Static deliverable page</a>
        </div>
      </section>
      <section class="panel grid-2">
        <div id="inputs"><h2>Inputs</h2>${list(module.inputs)}</div>
        <div id="controls"><h2>Parameters / controls</h2>${list(module.controls)}</div>
      </section>
      <section class="panel grid-2">
        <div id="mne"><h2>MNE objects / methods</h2>${list(module.mneObjects)}</div>
        <div id="outputs"><h2>Outputs</h2>${list(module.outputs)}</div>
      </section>
      <section class="panel" id="figures"><h2>Visual outputs</h2><div class="figure-grid">${(module.figures || []).map((fig) => `<figure class="figure"><img src="${asset(fig.src)}" alt="${h(fig.alt || fig.label)}" /><figcaption>${h(fig.label)}</figcaption></figure>`).join("")}</div></section>
      <section class="panel" id="artifacts"><h2>Files and deliverables</h2><div class="artifact-grid">${artifactCards(module)}</div></section>
      <section class="panel" id="tests"><h2>Module acceptance matrix</h2><table class="test-matrix"><thead><tr><th>Check</th><th>Acceptance rule</th></tr></thead><tbody>${testRows(slug)}</tbody></table></section>
      <section class="panel callout" id="risks"><h2>Research guardrails and risks</h2>${list(module.risks, "risk")}<p><strong>Parallel-development handoff: </strong>${h(handoff[slug])}</p><p><strong>Shared guardrail: </strong>${h(manifest.researchGuardrail)}</p></section>
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
    root.innerHTML = `<section class="lab-wrap"><div class="empty">Module Lab failed: ${h(error.message || error)}</div></section>`;
  }
}

main();
