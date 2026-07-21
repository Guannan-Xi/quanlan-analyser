import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const root = path.resolve(__dirname, "..");
const outDir = path.join(root, "work", "release_evidence", "07-mainline-productization", "current_available_modules");
const evidencePath = path.join(outDir, "main_workbench_direct_method_entries_9_methods_qc_dependency.json");

const html = fs.readFileSync(path.join(root, "frontend/index.html"), "utf8");
const app = fs.readFileSync(path.join(root, "frontend/app.js"), "utf8");

const preparationDependencies = [
  { id: "qc_data_preparation", action: "run-qc-preview-inline" },
  { id: "metadata_overview", action: "run-metadata-qc-inline" },
];

const directActions = [
  { moduleId: "psd", action: "run-psd", workflow: "resting_psd", backendModule: "psd" },
  { moduleId: "erp", action: "run-erp", workflow: "erp_p300", backendModule: "erp" },
  { moduleId: "tfr", action: "run-tfr", workflow: "tfr_ersp_itc", backendModule: "tfr" },
  { moduleId: "multitaper_psd", action: "run-multitaper-psd", workflow: "multitaper_psd_tfr", backendModule: "multitaper_psd_tfr" },
  { moduleId: "multitaper_tfr", action: "run-multitaper-tfr", workflow: "multitaper_psd_tfr", backendModule: "multitaper_psd_tfr" },
  { moduleId: "pac", action: "run-pac", workflow: "pac_cfc", backendModule: "pac" },
  { moduleId: "connectivity", action: "run-connectivity", workflow: "connectivity", backendModule: "connectivity" },
  { moduleId: "reference_csd", action: "run-reference-csd", workflow: "reference_csd", backendModule: "reference_csd" },
  { moduleId: "epilepsy_ml", action: "run-epilepsy-ml", workflow: "epilepsy_ml_xgboost", backendModule: "epilepsy_ml" },
];

function check(condition, name, details = {}) {
  return { name, pass: Boolean(condition), details };
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
      html: cardHtml,
      id: attr(tag, "data-module-id"),
      action: attr(tag, "data-real-action"),
    });
  }
  return cards;
}

const checks = [];
const methodCards = parseMethodCards(html);

for (const item of preparationDependencies) {
  checks.push(check(html.includes(`data-real-action="${item.action}"`), `preparation-dependency:${item.id}`, item));
}
checks.push(check(!html.includes('data-module-id="qc"'), "qc-is-not-analysis-method-card"));
checks.push(check(directActions.length === 9, "nine-analysis-actions-defined"));

for (const item of directActions) {
  const card = methodCards.find((candidate) => candidate.id === item.moduleId);
  const cardText = card?.html || "";
  checks.push(check(Boolean(card), `method-card:${item.moduleId}`));
  checks.push(check(card?.action === item.action, `method-card-action:${item.action}`));
  checks.push(check(!/试用|预览方法|需复核|Reference \/ CSD/i.test(cardText), `method-card-formal-copy:${item.moduleId}`));
  checks.push(check(
    app.includes(`"${item.action}"`) && app.includes(`runRealTask("${item.moduleId}", "${item.workflow}")`),
    `handler-maps-workflow:${item.action}`,
    { moduleId: item.moduleId, workflow: item.workflow },
  ));
}

checks.push(check(app.includes('moduleName === "multitaper_psd" || moduleName === "multitaper_tfr"'), "multitaper-user-actions-share-backend-module"));
checks.push(check(app.includes('return "multitaper_psd_tfr"'), "multitaper-backend-module-preserved"));
checks.push(check(app.includes("当前可用：9 项分析方法") || html.includes("当前可用：9 项分析方法"), "analysis-badge-uses-9-method-copy"));
checks.push(check(!app.includes("试用 Reference / CSD") && !html.includes("试用 Reference / CSD"), "old-reference-csd-preview-copy-removed"));

const report = {
  script: path.basename(__filename),
  checked_at: new Date().toISOString(),
  requirement_ids: ["current-contract-9-formal-methods-qc-dependency"],
  preparation_dependencies: preparationDependencies,
  direct_actions: directActions,
  checks,
  passed: checks.every((item) => item.pass),
  evidence_path: evidencePath,
};

fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(evidencePath, `${JSON.stringify(report, null, 2)}\n`, "utf8");
console.log(JSON.stringify(report, null, 2));
if (!report.passed) process.exit(1);
