import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const root = path.resolve(__dirname, "..");
const outDir = path.join(root, "work", "release_evidence", "07-mainline-productization", "current_available_modules");
const evidencePath = path.join(outDir, "main_workbench_direct_method_entries_9_methods.json");

const html = fs.readFileSync(path.join(root, "frontend/index.html"), "utf8");
const app = fs.readFileSync(path.join(root, "frontend/app.js"), "utf8");

const discoveryEntries = [
  "qc",
  "psd",
  "erp",
  "tfr",
  "multitaper_psd",
  "multitaper_tfr",
  "reference_csd",
  "pac",
  "connectivity",
];

const directActions = [
  {
    moduleId: "psd",
    action: "run-psd",
    label: "开始 PSD 分析",
    workflow: "resting_psd",
    backendModule: "psd",
    preview: false,
  },
  {
    moduleId: "erp",
    action: "run-erp",
    label: "开始 ERP 分析",
    workflow: "erp_p300",
    backendModule: "erp",
    preview: false,
  },
  {
    moduleId: "tfr",
    action: "run-tfr",
    label: "试用 TFR 时频分析（需复核）",
    workflow: "tfr_ersp_itc",
    backendModule: "tfr",
    preview: true,
  },
  {
    moduleId: "multitaper_psd",
    action: "run-multitaper-psd",
    label: "试用 Multitaper PSD（需复核）",
    workflow: "multitaper_psd_tfr",
    backendModule: "multitaper_psd_tfr",
    preview: true,
  },
  {
    moduleId: "multitaper_tfr",
    action: "run-multitaper-tfr",
    label: "试用 Multitaper TFR（需复核）",
    workflow: "multitaper_psd_tfr",
    backendModule: "multitaper_psd_tfr",
    preview: true,
  },
  {
    moduleId: "reference_csd",
    action: "run-reference-csd",
    label: "试用 Reference / CSD（需复核）",
    workflow: "reference_csd",
    backendModule: "reference_csd",
    preview: true,
  },
  {
    moduleId: "pac",
    action: "run-pac",
    label: "试用 PAC 耦合分析（需复核）",
    workflow: "pac_cfc",
    backendModule: "pac",
    preview: true,
  },
  {
    moduleId: "connectivity",
    action: "run-connectivity",
    label: "试用 Connectivity（需复核）",
    workflow: "connectivity",
    backendModule: "connectivity",
    preview: true,
  },
];

function check(condition, name, details = {}) {
  return { name, pass: Boolean(condition), details };
}

const actionButtonRegex = /data-real-action="([^"]+)"[\s\S]*?<span>([\s\S]*?)<\/span>/g;
const buttons = [];
let match;
while ((match = actionButtonRegex.exec(html))) {
  buttons.push({ action: match[1], label: match[2].replace(/\s+/g, " ").trim() });
}

const checks = [];

for (const id of discoveryEntries) {
  checks.push(check(html.includes(`data-module-id="${id}"`), `current-module-card:${id}`));
}

for (const item of directActions) {
  const button = buttons.find((candidate) => candidate.action === item.action);
  checks.push(check(Boolean(button), `direct-action-button:${item.action}`, { expectedLabel: item.label, actualLabel: button?.label }));
  checks.push(check(button?.label === item.label, `direct-action-label:${item.action}`, { expected: item.label, actual: button?.label }));
  checks.push(check(
    app.includes(`"${item.action}"`) && app.includes(`runRealTask("${item.moduleId}", "${item.workflow}")`),
    `handler-maps-workflow:${item.action}`,
    { moduleId: item.moduleId, workflow: item.workflow },
  ));
  checks.push(check(app.includes(`if (moduleName === "${item.moduleId}")`) || ["psd", "erp", "tfr", "pac"].includes(item.moduleId), `parameters-case:${item.moduleId}`));
  if (item.preview) {
    checks.push(check(item.label.includes("需复核"), `preview-action-review-copy:${item.action}`));
  }
}

checks.push(check(!buttons.some((button) => button.action === "run-qc"), "qc-is-not-duplicated-as-analysis-button"));
checks.push(check(directActions.length === 8, "eight-analysis-actions-defined"));
checks.push(check(app.includes('moduleName === "multitaper_psd" || moduleName === "multitaper_tfr"'), "multitaper-user-actions-share-backend-module"));
checks.push(check(app.includes('return "multitaper_psd_tfr"'), "multitaper-backend-module-preserved"));
checks.push(check(app.includes("8 项分析方法"), "empty-state-does-not-limit-to-four-methods"));
checks.push(check(!app.includes("方法分支中选择 PSD、ERP、TFR 或 PAC"), "old-four-method-copy-removed"));

const report = {
  script: path.basename(__filename),
  checked_at: new Date().toISOString(),
  requirement_ids: ["R12"],
  discovery_entries: discoveryEntries,
  direct_actions: directActions.map(({ moduleId, action, label, workflow, backendModule }) => ({ moduleId, action, label, workflow, backendModule })),
  checks,
  passed: checks.every((item) => item.pass),
  evidence_path: evidencePath,
};

fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(evidencePath, `${JSON.stringify(report, null, 2)}\n`, "utf8");
console.log(JSON.stringify(report, null, 2));
if (!report.passed) process.exit(1);
