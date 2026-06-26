import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const root = path.resolve(__dirname, "..");
const outDir =
  process.env.QLANALYSER_AUTO_PREVIEW_EVIDENCE_DIR ||
  path.join(root, "work", "release_evidence", "07-mainline-productization", "data_preparation_auto_preview");
const evidencePath = path.join(outDir, "data_preparation_auto_preview.json");

function read(rel) {
  return fs.readFileSync(path.join(root, rel), "utf8");
}

function check(condition, name, details = {}) {
  return { name, pass: Boolean(condition), details };
}

const app = read("frontend/app.js");
const html = read("frontend/index.html");
const workflowGate = read("scripts/acceptance_workflow_pages_ui_gate.mjs");

const checks = [
  check(
    /async function chooseWorkspaceFile\(fileId, options = \{\}\)[\s\S]*requestAutoQcPreviewForSelectedFile\(file\)/.test(app),
    "file_selection_calls_auto_preview"
  ),
  check(
    app.includes('recordUiAction("real:auto-qc-preview", "pass"'),
    "auto_preview_records_user_action"
  ),
  check(
    app.includes('button.hidden = !eegState.autoPreviewError'),
    "reload_preview_hidden_until_error"
  ),
  check(
    html.includes('class="ghost-btn secondary-preview-action"') && html.includes("重新加载预览"),
    "reload_preview_exists_only_as_secondary_recovery_action"
  ),
  check(
    !workflowGate.includes('"run-qc-preview-inline", "confirm-plan-inline"') &&
      !workflowGate.includes("'run-qc-preview-inline', 'confirm-plan-inline'"),
    "workflow_gate_no_longer_requires_preview_button"
  ),
  check(
    !app.includes("运行 QC 预览") && !html.includes("运行质控预览"),
    "visible_copy_does_not_use_run_qc_preview"
  ),
  check(
    app.includes("无需额外点击预览按钮"),
    "selected_file_copy_explains_no_preview_button_needed"
  ),
  check(
    !app.includes("任务 ${escapeHtml(state.real.tasks.qc.id)}"),
    "preview_success_copy_hides_task_id"
  ),
];

const report = {
  script: path.basename(__filename),
  checked_at: new Date().toISOString(),
  requirement_ids: ["R3", "R4", "R9"],
  checks,
  passed: checks.every((item) => item.pass),
};

fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(evidencePath, `${JSON.stringify(report, null, 2)}\n`, "utf8");
console.log(JSON.stringify(report, null, 2));
if (!report.passed) process.exit(1);
