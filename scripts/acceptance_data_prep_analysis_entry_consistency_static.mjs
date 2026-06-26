import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const ROOT = path.resolve(path.dirname(__filename), "..");
const OUT_DIR = path.join(
  ROOT,
  "work",
  "release_evidence",
  "07-full-product-e2e-pdca",
  "13_data_prep_analysis_entry_consistency",
  "04_static_checks",
);
const OUT_PATH = path.join(OUT_DIR, "data_prep_analysis_entry_consistency_static.json");

function read(relPath) {
  return fs.readFileSync(path.join(ROOT, relPath), "utf8");
}

function stripTags(value) {
  return String(value || "")
    .replace(/<script[\s\S]*?<\/script>/gi, "")
    .replace(/<style[\s\S]*?<\/style>/gi, "")
    .replace(/<[^>]+>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function sectionByTestId(html, testId) {
  const match = new RegExp(`<section\\b[^>]*data-testid="${testId}"[^>]*>[\\s\\S]*?<\\/section>`, "i").exec(html);
  return match?.[0] || "";
}

function parseMethodCards(html) {
  const section = sectionByTestId(html, "analysis-method-scope-panel");
  const cardRegex = /<button\b([^>]*)class="[^"]*\bia-method-card\b[^"]*"([^>]*)>([\s\S]*?)<\/button>/gi;
  const cards = [];
  let match;
  while ((match = cardRegex.exec(section))) {
    const attrs = `${match[1] || ""} ${match[2] || ""}`;
    const body = match[3] || "";
    cards.push({
      id: /data-module-id="([^"]+)"/i.exec(attrs)?.[1] || "",
      action: /data-real-action="([^"]+)"/i.exec(attrs)?.[1] || "",
      type: /type="([^"]+)"/i.exec(attrs)?.[1] || "",
      title: /<strong>([\s\S]*?)<\/strong>/i.exec(body)?.[1]?.trim() || "",
      badge: /<b>([\s\S]*?)<\/b>/i.exec(body)?.[1]?.trim() || "",
      text: stripTags(body),
    });
  }
  return cards;
}

function check(name, pass, details = {}) {
  return { name, pass: Boolean(pass), details };
}

const html = read("frontend/index.html");
const app = read("frontend/app.js");
const css = read("frontend/styles.css");
const visibleHtml = stripTags(html);
const cards = parseMethodCards(html);
const expected = [
  ["psd", "run-psd"],
  ["erp", "run-erp"],
  ["tfr", "run-tfr"],
  ["multitaper_psd", "run-multitaper-psd"],
  ["multitaper_tfr", "run-multitaper-tfr"],
  ["pac", "run-pac"],
  ["connectivity", "run-connectivity"],
  ["reference_csd", "run-reference-csd"],
];

const checks = [];

checks.push(check("old_analysis_method_run_panel_removed_from_html", !html.includes('data-testid="analysis-method-run-panel"')));
checks.push(check("old_analysis_method_run_panel_removed_from_runtime_copy", !app.includes("analysis-method-run-panel")));
checks.push(check("method_cards_count_is_8", cards.length === 8, { actual: cards.length }));
for (const [moduleId, action] of expected) {
  const card = cards.find((item) => item.id === moduleId);
  checks.push(check(`method_card_exists:${moduleId}`, Boolean(card), { cards }));
  checks.push(check(`method_card_has_real_action:${moduleId}`, card?.action === action, { actual: card?.action, expected: action }));
  checks.push(check(`method_card_is_button:${moduleId}`, card?.type === "button", { actual: card?.type }));
}

checks.push(check("waveform_preview_json_loader_present", app.includes("waveformArtifactFromList") && app.includes("waveform_preview")));
checks.push(check("waveform_canvas_drawer_present", app.includes("function drawEegWaveformPreview") && app.includes("#eegCanvas")));
checks.push(check("qc_preview_loads_waveform_before_success", app.includes("await loadWaveformPreviewFromTask(task, eegFile);")));
checks.push(check("file_switch_clears_old_preview", app.includes("function clearEegPreviewState") && app.includes("ctx.clearRect")));
checks.push(check("teaching_close_clears_demo_selection", app.includes("const wasTeachingDemo") && app.includes("state.workspace.selectedProjectId = null")));
checks.push(check("teaching_demo_hidden_outside_teaching_mode", app.includes("isTeachingDemoProject(project) && !state.teaching.active")));
checks.push(check("teaching_card_position_uses_real_height", app.includes("const cardHeight = Math.min(card.offsetHeight")));
checks.push(check("method_card_focus_hover_style_present", css.includes(".ia-method-card:hover") && css.includes(".ia-method-card:focus-visible")));
checks.push(check("teaching_card_viewport_bounded", css.includes("max-height: calc(100vh - 32px)") && css.includes("overflow: auto")));

const forbiddenCustomerTerms = [
  "预览方法可试用",
  "可开始准备",
  "待建立准备方案",
  "待预处理",
  "结合临床判断",
  "Reference / CSD",
  "参考方案与 CSD",
];
for (const term of forbiddenCustomerTerms) {
  checks.push(check(`forbidden_visible_copy_absent:${term}`, !visibleHtml.includes(term) && !app.includes(term)));
}
checks.push(check("csd_copy_does_not_mix_reference_method", cards.find((item) => item.id === "reference_csd")?.title === "CSD 电流源密度计算"));
checks.push(check("customer_copy_marks_research_boundary", app.includes("科研预览，不是诊断结论") || app.includes("仅用于数据准备检查")));

const report = {
  script: path.basename(__filename),
  generated_at: new Date().toISOString(),
  status: checks.every((item) => item.pass) ? "passed" : "failed",
  cards,
  checks,
};

fs.mkdirSync(OUT_DIR, { recursive: true });
fs.writeFileSync(OUT_PATH, `${JSON.stringify(report, null, 2)}\n`, "utf8");
console.log(JSON.stringify(report, null, 2));
if (report.status !== "passed") process.exit(1);
