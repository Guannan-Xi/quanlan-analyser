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

const expected = [
  { id: "qc", label: "数据准备与质量检查", status: "准备步骤", tone: "dependency" },
  { id: "psd", label: "PSD / Bandpower", status: "可用", tone: "available" },
  { id: "erp", label: "ERP / P300", status: "可用，需事件", tone: "available" },
  { id: "tfr", label: "TFR / ERSP / ITC", status: "预览方法，需复核", tone: "beta" },
  { id: "multitaper_psd", label: "Multitaper PSD", status: "预览方法，需复核", tone: "beta" },
  { id: "multitaper_tfr", label: "Multitaper TFR", status: "预览方法，需复核", tone: "beta" },
  { id: "reference_csd", label: "Reference / CSD", status: "预览方法，需复核", tone: "beta" },
  { id: "pac", label: "PAC / CFC", status: "预览方法，需复核", tone: "beta" },
  { id: "connectivity", label: "Connectivity", status: "预览方法，需复核", tone: "beta" },
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
  /内部测试/,
  /开发验收/,
  /真实\s*\/api/i,
  /方法分支/,
  /分析任务工作台/,
  /9 个模块/,
  /项目 ID/,
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

function parseCards(html) {
  const cards = [];
  const articleRegex = /<article\b[^>]*class="[^"]*\bia-method-card\b[^"]*"[^>]*>[\s\S]*?<\/article>/g;
  let match;
  while ((match = articleRegex.exec(html))) {
    const article = match[0];
    const tag = /<article\b([^>]*)>/.exec(article)?.[1] || "";
    const id = /data-module-id="([^"]+)"/.exec(tag)?.[1] || "";
    const className = /class="([^"]+)"/.exec(tag)?.[1] || "";
    const label = /<strong>([\s\S]*?)<\/strong>/.exec(article)?.[1]?.trim() || "";
    const status = /<b>([\s\S]*?)<\/b>/.exec(article)?.[1]?.trim() || "";
    const text = stripTags(article);
    cards.push({ id, className, label, status, text });
  }
  return cards;
}

function check(condition, name, details = {}) {
  return { name, pass: Boolean(condition), details };
}

function visibleTextForScopePanel(html) {
  const section = /<section\b[^>]*data-testid="analysis-method-scope-panel"[^>]*>[\s\S]*?<\/section>/.exec(html)?.[0] || "";
  return stripTags(section);
}

const html = read("frontend/index.html");
const appJs = read("frontend/app.js");
const cards = parseCards(html);
const panelText = visibleTextForScopePanel(html);
const checks = [];

checks.push(check(cards.length === expected.length, "html_has_9_current_available_module_cards", { actual: cards.length }));

for (const item of expected) {
  const card = cards.find((candidate) => candidate.id === item.id);
  checks.push(check(Boolean(card), `html_card_exists:${item.id}`));
  checks.push(check(card?.label === item.label, `html_card_label:${item.id}`, { expected: item.label, actual: card?.label }));
  checks.push(check(card?.status === item.status, `html_card_status:${item.id}`, { expected: item.status, actual: card?.status }));
  checks.push(check(card?.className.split(/\s+/).includes(item.tone), `html_card_tone:${item.id}`, { expected: item.tone, actual: card?.className }));
  checks.push(check(appJs.includes(`${item.id}: [`), `dynamic_copy_contains:${item.id}`));
  checks.push(check(appJs.includes(item.label), `dynamic_copy_label:${item.id}`, { label: item.label }));
}

for (const term of forbiddenMainCardTerms) {
  checks.push(check(!term.test(panelText), `main_card_forbidden_term_absent:${term}`));
}

checks.push(check(panelText.includes("预览方法可试用"), "panel_explains_preview_methods"));
checks.push(check(panelText.includes("人工复核"), "panel_explains_human_review"));
checks.push(check(html.includes("当前可用：9 项分析能力"), "analysis_badge_uses_user_capability_copy"));
checks.push(check(panelText.includes("不证明信息流或因果方向"), "connectivity_boundary_visible"));
checks.push(check(panelText.includes("不能单独解释为因果关系"), "pac_boundary_visible"));
checks.push(check(panelText.includes("不把结果解释为精确脑源定位"), "reference_csd_boundary_visible"));

const report = {
  script: path.basename(__filename),
  checked_at: new Date().toISOString(),
  requirement_ids: ["R1", "R2", "R7"],
  expected_module_ids: expected.map((item) => item.id),
  actual_module_ids: cards.map((item) => item.id),
  card_count: cards.length,
  checks,
  passed: checks.every((item) => item.pass),
};

fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(evidencePath, `${JSON.stringify(report, null, 2)}\n`, "utf8");
console.log(JSON.stringify(report, null, 2));
if (!report.passed) process.exit(1);
