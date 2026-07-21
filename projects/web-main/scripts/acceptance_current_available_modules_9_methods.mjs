import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const root = path.resolve(__dirname, "..");
const outDir =
  process.env.QLANALYSER_CURRENT_MODULES_EVIDENCE_DIR ||
  path.join(root, "work", "release_evidence", "07-mainline-productization", "current_available_modules");
const evidencePath = path.join(outDir, "current_available_modules_9_methods.json");

const expectedAnalysisMethods = [
  { id: "psd", action: "run-psd", tone: "available" },
  { id: "erp", action: "run-erp", tone: "available" },
  { id: "tfr", action: "run-tfr", tone: "available" },
  { id: "multitaper_psd", action: "run-multitaper-psd", tone: "available" },
  { id: "multitaper_tfr", action: "run-multitaper-tfr", tone: "available" },
  { id: "pac", action: "run-pac", tone: "available" },
  { id: "connectivity", action: "run-connectivity", tone: "available" },
  { id: "reference_csd", action: "run-reference-csd", tone: "available" },
  { id: "epilepsy_ml", action: "run-epilepsy-ml", tone: "available" },
];

const forbiddenMainCardTerms = [
  /runner/i,
  /workflow\s*id/i,
  /module\s*id/i,
  /\/api\/tasks/i,
  /manifest/i,
  /acceptance/i,
  /\bgate\b/i,
  /debug/i,
  /fake/i,
  /mock/i,
  /demo-only/i,
  /preview methods can be tried/i,
  /Reference\s*\/\s*CSD/i,
  /data-module-id="qc"/i,
  /data-real-action="run-qc/i,
];

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

function attr(tag, name) {
  return new RegExp(`${name}="([^"]*)"`, "i").exec(tag)?.[1] || "";
}

function parseCards(html) {
  const cards = [];
  const cardRegex = /<(article|button)\b[^>]*class="[^"]*\bia-method-card\b[^"]*"[^>]*>[\s\S]*?<\/\1>/gi;
  let match;
  while ((match = cardRegex.exec(html))) {
    const cardHtml = match[0];
    const tag = /^<\w+\b([^>]*)>/i.exec(cardHtml)?.[1] || "";
    cards.push({
      tagName: match[1].toLowerCase(),
      id: attr(tag, "data-module-id"),
      action: attr(tag, "data-real-action"),
      className: attr(tag, "class"),
      label: stripTags(/<strong>([\s\S]*?)<\/strong>/i.exec(cardHtml)?.[1] || ""),
      status: stripTags(/<b>([\s\S]*?)<\/b>/i.exec(cardHtml)?.[1] || ""),
      text: stripTags(cardHtml),
    });
  }
  return cards;
}

function check(condition, name, details = {}) {
  return { name, pass: Boolean(condition), details };
}

function visibleTextForScopePanel(html) {
  const start = html.indexOf('data-testid="analysis-method-scope-panel"');
  if (start < 0) return "";
  const nextSection = html.indexOf("<section", start + 20);
  const panel = html.slice(start, nextSection > start ? nextSection : undefined);
  return stripTags(panel);
}

const html = read("frontend/index.html");
const appJs = read("frontend/app.js");
const cards = parseCards(html);
const panelText = visibleTextForScopePanel(html);
const checks = [];

checks.push(check(cards.length === expectedAnalysisMethods.length, "html_has_9_current_analysis_method_cards", { actual: cards.length }));
checks.push(check(!cards.some((card) => card.id === "qc"), "qc_is_not_an_analysis_method_card", { actual_module_ids: cards.map((card) => card.id) }));
checks.push(check(html.includes('data-testid="single-file-preview-panel"'), "data_preparation_panel_exists"));
checks.push(check(html.includes('data-real-action="run-qc-preview-inline"'), "qc_preview_exists_as_data_preparation_dependency"));

for (const item of expectedAnalysisMethods) {
  const card = cards.find((candidate) => candidate.id === item.id);
  checks.push(check(Boolean(card), `html_card_exists:${item.id}`));
  checks.push(check(card?.tagName === "button" || card?.tagName === "article", `html_card_tag_supported:${item.id}`, { actual: card?.tagName }));
  checks.push(check(card?.action === item.action, `html_card_action:${item.id}`, { expected: item.action, actual: card?.action }));
  checks.push(check(card?.className.split(/\s+/).includes(item.tone), `html_card_tone:${item.id}`, { expected: item.tone, actual: card?.className }));
  checks.push(check(appJs.includes(`${item.id}: [`), `dynamic_copy_contains:${item.id}`));
  checks.push(check(appJs.includes(item.action), `dynamic_copy_action:${item.id}`));
}

for (const term of forbiddenMainCardTerms) {
  checks.push(check(!term.test(panelText), `main_card_forbidden_term_absent:${term}`));
}

checks.push(check(/9\s*.{0,8}(method|analysis|分析)/i.test(panelText) || html.includes("9 项分析方法"), "analysis_badge_uses_9_method_scope"));
checks.push(check(panelText.length > 100, "analysis_scope_panel_has_customer_copy", { length: panelText.length }));

const report = {
  script: path.basename(__filename),
  checked_at: new Date().toISOString(),
  requirement_ids: ["P0-4", "QC-as-data-preparation-dependency", "current-available-methods"],
  expected_analysis_method_ids: expectedAnalysisMethods.map((item) => item.id),
  actual_module_ids: cards.map((item) => item.id),
  qc_dependency_policy: "QC/data preparation is required before analysis but is not counted as an analysis method card.",
  card_count: cards.length,
  checks,
  passed: checks.every((item) => item.pass),
};

fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(evidencePath, `${JSON.stringify(report, null, 2)}\n`, "utf8");
console.log(JSON.stringify(report, null, 2));
if (!report.passed) process.exit(1);
