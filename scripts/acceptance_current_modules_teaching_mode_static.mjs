import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const root = path.resolve(__dirname, "..");
const evidenceDir = path.join(
  root,
  "work",
  "release_evidence",
  "07-full-product-e2e-pdca",
  "12_current_modules_teaching_mode",
  "03_static_checks",
);
const evidencePath = path.join(evidenceDir, "current_modules_teaching_mode_static.json");

function read(rel) {
  return fs.readFileSync(path.join(root, rel), "utf8");
}

function stripTags(html) {
  return html
    .replace(/<script[\s\S]*?<\/script>/gi, "")
    .replace(/<style[\s\S]*?<\/style>/gi, "")
    .replace(/<[^>]+>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function parseCards(html) {
  const section = /<section\b[^>]*data-testid="analysis-method-scope-panel"[^>]*>[\s\S]*?<\/section>/i.exec(html)?.[0] || "";
  const cards = [];
  const articleRegex = /<article\b[^>]*class="[^"]*\bia-method-card\b[^"]*"[^>]*>[\s\S]*?<\/article>/gi;
  let match;
  while ((match = articleRegex.exec(section))) {
    const article = match[0];
    const tag = /<article\b([^>]*)>/i.exec(article)?.[1] || "";
    cards.push({
      id: /data-module-id="([^"]+)"/i.exec(tag)?.[1] || "",
      className: /class="([^"]+)"/i.exec(tag)?.[1] || "",
      label: /<strong>([\s\S]*?)<\/strong>/i.exec(article)?.[1]?.trim() || "",
      status: /<b>([\s\S]*?)<\/b>/i.exec(article)?.[1]?.trim() || "",
      text: stripTags(article),
    });
  }
  return { sectionText: stripTags(section), cards };
}

function check(pass, name, details = {}) {
  return { name, pass: Boolean(pass), details };
}

const html = read("frontend/index.html");
const appJs = read("frontend/app.js");
const styles = read("frontend/styles.css");
const taskService = read("backend/services/task_service.py");
const labDemoService = read("backend/services/lab_demo_service.py");
const referenceCsd = read("eeg_core/analysis/reference_csd.py");

const { sectionText, cards } = parseCards(html);
const expected = [
  { id: "psd", label: "PSD 频谱与频段功率" },
  { id: "erp", label: "ERP 事件相关电位" },
  { id: "tfr", label: "TFR 时频分析" },
  { id: "multitaper_psd", label: "Multitaper PSD" },
  { id: "multitaper_tfr", label: "Multitaper TFR" },
  { id: "pac", label: "PAC 相位-振幅耦合" },
  { id: "connectivity", label: "Connectivity 连接性分析" },
  { id: "reference_csd", label: "CSD 电流源密度计算" },
];
const forbiddenVisible = [
  "预览方法",
  "可试用",
  "需复核",
  "Reference / CSD",
  "参考方案与 CSD",
];
const checks = [];

checks.push(check(cards.length === expected.length, "current_analysis_method_card_count_is_8", { actual: cards.length }));
for (const item of expected) {
  const card = cards.find((candidate) => candidate.id === item.id);
  checks.push(check(Boolean(card), `method_card_exists:${item.id}`));
  checks.push(check(card?.label === item.label, `method_card_label:${item.id}`, { expected: item.label, actual: card?.label }));
}
checks.push(check(!cards.some((card) => card.id === "qc"), "qc_not_in_current_analysis_methods", { ids: cards.map((card) => card.id) }));
checks.push(check(sectionText.includes("当前可用分析方法"), "section_renamed_current_available_analysis_methods"));
checks.push(check(sectionText.includes("传感器空间滤波") && sectionText.includes("不是源定位或诊断"), "csd_boundary_visible"));
checks.push(check(sectionText.includes("不能单独解释为因果机制"), "pac_boundary_visible"));
checks.push(check(sectionText.includes("不证明信息流或因果方向"), "connectivity_boundary_visible"));

const customerVisibleSource = [html, appJs].join("\n");
for (const term of forbiddenVisible) {
  checks.push(check(!customerVisibleSource.includes(term), `forbidden_customer_term_absent:${term}`));
}
checks.push(check(html.includes('id="teachingModeBtn"') && html.includes("教学模式"), "topbar_teaching_mode_button_present"));
checks.push(check(appJs.includes("const teachingSteps") && appJs.includes("teaching-overlay"), "teaching_overlay_state_machine_present"));
checks.push(check(styles.includes(".teaching-overlay") && styles.includes(".teaching-spotlight"), "teaching_overlay_styles_present"));
checks.push(check(appJs.includes('reference_mode: "csd"'), "frontend_csd_action_uses_csd_mode"));
checks.push(check(appJs.includes("csd: {") && appJs.includes("n_legendre_terms"), "frontend_csd_parameters_nested_for_backend"));
checks.push(check(taskService.includes('"name": "CSD 电流源密度计算"'), "backend_template_display_name_csd"));
checks.push(check(labDemoService.includes('"reference_mode": "csd"'), "demo_reference_csd_defaults_to_csd"));
checks.push(check(referenceCsd.includes("sensor-space derivatives only"), "csd_method_text_sensor_space_boundary"));

const report = {
  script: path.basename(__filename),
  generated_at: new Date().toISOString(),
  requirements: [
    "R-IA-01",
    "R-IA-03",
    "R-COPY-01",
    "R-CSD-01",
    "R-CSD-02",
    "R-NAV-02",
    "R-TEACH-02",
  ],
  expected_method_ids: expected.map((item) => item.id),
  actual_method_ids: cards.map((item) => item.id),
  checks,
  passed: checks.every((item) => item.pass),
};

fs.mkdirSync(evidenceDir, { recursive: true });
fs.writeFileSync(evidencePath, `${JSON.stringify(report, null, 2)}\n`, "utf8");
console.log(JSON.stringify(report, null, 2));
process.exit(report.passed ? 0 : 1);
