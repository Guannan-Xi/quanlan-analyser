import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const root = path.resolve(__dirname, "..");
const outDir =
  process.env.QLANALYSER_COPY_GOVERNANCE_EVIDENCE_DIR ||
  path.join(root, "work", "release_evidence", "07-mainline-productization", "user_copy_governance");
const evidencePath = path.join(outDir, "product_wide_ux_copy_governance.json");

const files = [
  "frontend/index.html",
  "frontend/app.js",
  "frontend/module-lab.html",
  "frontend/module-lab.js",
  "frontend/qc-lab.html",
  "frontend/qc-lab.js",
  "frontend/research-modules.html",
  "frontend/research-modules.js",
  "frontend/research-module/qc.html",
  "frontend/research-module/psd.html",
  "frontend/research-module/erp.html",
  "frontend/research-module/tfr.html",
  "frontend/research-module/pac.html",
  "frontend/research-module/connectivity.html",
  "frontend/research-module/source_localization.html",
  "frontend/assets/research-modules/reproducibility/research_module_manifest.json",
].filter((file) => fs.existsSync(path.join(root, file)));

const html = fs.readFileSync(path.join(root, "frontend/index.html"), "utf8");
const app = fs.readFileSync(path.join(root, "frontend/app.js"), "utf8");
const fullText = files.map((file) => `\n--- ${file} ---\n${fs.readFileSync(path.join(root, file), "utf8")}`).join("\n");
const appVisibleLines = app
  .split(/\r?\n/)
  .filter((line) => [
    "setTextIfPresent",
    "setAllTextIfPresent",
    "setRealStatus",
    "setRealActionEnabled",
    "target.innerHTML",
    "delivery.innerHTML",
    "recordUiAction",
    "throw new Error",
  ].some((marker) => line.includes(marker)))
  .join("\n");
const visibleText = `\n--- frontend/index.html ---\n${html}\n--- frontend/app.js visible runtime copy ---\n${appVisibleLines}`;

function stripTags(value) {
  return String(value || "")
    .replace(/<script[\s\S]*?<\/script>/gi, "")
    .replace(/<style[\s\S]*?<\/style>/gi, "")
    .replace(/<[^>]+>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function attr(tag, name) {
  return new RegExp(`${name}="([^"]*)"`, "i").exec(tag)?.[1] || "";
}

function parseMethodCards(markup) {
  const cards = [];
  const cardRegex = /<(article|button)\b[^>]*class="[^"]*\bia-method-card\b[^"]*"[^>]*>[\s\S]*?<\/\1>/gi;
  let match;
  while ((match = cardRegex.exec(markup))) {
    const cardHtml = match[0];
    const tag = /^<\w+\b([^>]*)>/i.exec(cardHtml)?.[1] || "";
    cards.push({
      tagName: match[1].toLowerCase(),
      id: attr(tag, "data-module-id"),
      action: attr(tag, "data-real-action"),
      className: attr(tag, "class"),
      title: stripTags(/<strong>([\s\S]*?)<\/strong>/i.exec(cardHtml)?.[1] || ""),
      body: stripTags(/<span>([\s\S]*?)<\/span>/i.exec(cardHtml)?.[1] || ""),
      badge: stripTags(/<b>([\s\S]*?)<\/b>/i.exec(cardHtml)?.[1] || ""),
      text: stripTags(cardHtml),
    });
  }
  return cards;
}

function check(pass, name, details = {}) {
  return { name, pass: Boolean(pass), details };
}

const methodCards = parseMethodCards(html);
const expectedMethods = ["psd", "erp", "tfr", "multitaper_psd", "multitaper_tfr", "pac", "connectivity", "reference_csd"];
const staleCustomerCopy = [
  "当前可用：9 项分析能力",
  "预览方法，需复核",
  "预览方法可试用",
  "试用 TFR",
  "试用 Multitaper",
  "试用 Reference / CSD",
  "试用 PAC",
  "试用 Connectivity",
  "Reference / CSD",
  "参考方案与 CSD",
  "结合临床判断",
  "Beta 方法",
  "Preview-only",
  "Preview only",
];
const internalTerms = [
  "workflow_id",
  "module_name",
  "data-real-action",
  "Plan id",
  "Quality gate",
  "Evidence file",
  "Workflow contract",
  ["frontend", "node_modules", "playwright"].join("/"),
];

const checks = [];
checks.push(check(methodCards.length === 8, "analysis_method_card_count_is_8", { actual: methodCards.length }));
checks.push(check(!methodCards.some((card) => card.id === "qc"), "qc_not_rendered_as_analysis_method", { ids: methodCards.map((card) => card.id) }));
checks.push(check(expectedMethods.every((id) => methodCards.some((card) => card.id === id)), "all_8_formal_methods_present", { expectedMethods, actual: methodCards.map((card) => card.id) }));
checks.push(check(html.includes('data-real-action="run-qc-preview-inline"') || html.includes('data-real-action="run-metadata-qc-inline"'), "qc_visible_as_data_preparation_dependency"));
checks.push(check(html.includes("当前可用：8 项分析方法") || app.includes("当前可用：8 项分析方法"), "analysis_badge_uses_8_formal_methods"));
checks.push(check(methodCards.every((card) => card.className.split(/\s+/).includes("available")), "method_cards_are_formal_available_methods", { classes: methodCards.map((card) => [card.id, card.className]) }));
checks.push(check(methodCards.find((card) => card.id === "reference_csd")?.title.includes("CSD"), "csd_card_named_as_csd_not_reference_scheme", { card: methodCards.find((card) => card.id === "reference_csd") }));

for (const term of staleCustomerCopy) {
  checks.push(check(!visibleText.includes(term), `stale_customer_copy_absent:${term}`));
}
for (const term of internalTerms) {
  checks.push(check(!stripTags(html).includes(term), `internal_term_absent_from_static_html:${term}`));
}

const result = {
  script: path.basename(__filename),
  checked_at: new Date().toISOString(),
  contract: "8 formal analysis methods + QC as data-preparation dependency",
  files,
  method_cards: methodCards,
  checks,
  passed: checks.every((item) => item.pass),
  evidence_path: evidencePath,
};

fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(evidencePath, `${JSON.stringify(result, null, 2)}\n`, "utf8");
console.log(JSON.stringify(result, null, 2));
if (!result.passed) process.exit(1);
