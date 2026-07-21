import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const root = path.resolve(__dirname, "..");
const app = fs.readFileSync(path.join(root, "frontend", "app.js"), "utf8");

function check(pass, name, details = {}) {
  return { name, pass: Boolean(pass), details };
}

function sectionBetween(source, startNeedle, endNeedle) {
  const start = source.indexOf(startNeedle);
  if (start < 0) return "";
  const end = source.indexOf(endNeedle, start + startNeedle.length);
  return end < 0 ? source.slice(start) : source.slice(start, end);
}

const createReport = sectionBetween(app, "async function createRealReport()", "function artifactDownloadUrl");
const reportGate = sectionBetween(app, "function reportReleaseGateSnapshot()", "async function ensureReportReleaseReady()");
const ensureReportGate = sectionBetween(app, "async function ensureReportReleaseReady()", "function currentWorkspaceFile()");
const updateGate = sectionBetween(app, "function updateRealActionGate()", "function getAuthSession()");
const delivery = sectionBetween(app, "function renderRealDelivery()", "function applyCustomerDemoMode()");
const iaAction = sectionBetween(app, "async function handleIaAction(action)", "function handleSubmitAnalysisClick()");
const excludeBranch = sectionBetween(iaAction, 'action === "exclude-segment"', 'action === "restore-segment"');
const addLabelBranch = sectionBetween(iaAction, 'action === "add-label"', 'action === "edit-label"');

const checks = [];

checks.push(check(
  reportGate.includes("isCompletedAnalysisTask(task)")
    && reportGate.includes("state.real.resultsViewed")
    && reportGate.includes("hasDownloadableResultArtifact(artifacts)"),
  "report_gate_requires_completed_reviewed_and_artifact",
));
checks.push(check(
  ensureReportGate.includes("await fetchTaskArtifacts(gate.task.id)")
    && ensureReportGate.includes("缺少可下载结果文件")
    && ensureReportGate.includes("throw new Error"),
  "report_generation_refetches_and_blocks_missing_artifacts",
));
checks.push(check(
  createReport.includes("await ensureReportReleaseReady()")
    && createReport.indexOf("await ensureReportReleaseReady()") < createReport.indexOf('apiJson("/reports"'),
  "create_real_report_hard_gate_before_reports_api",
));
checks.push(check(
  updateGate.includes("const reportGate = reportReleaseGateSnapshot()")
    && updateGate.includes('setRealActionEnabled("create-report", reportGate.ready, reportGate.reason)')
    && !updateGate.includes("const canCreateReport = Boolean(task && state.real.resultsViewed)"),
  "create_report_button_uses_shared_gate_not_results_viewed_only",
));
checks.push(check(
  delivery.includes("const reportGate = reportReleaseGateSnapshot()")
    && delivery.includes("reportGate.ready")
    && delivery.includes("reportGate.reason"),
  "report_delivery_empty_state_uses_shared_gate",
));

checks.push(check(
  app.includes("function manualSegmentRangeFromInputs()")
    && app.includes("manualSegmentEdited")
    && app.includes("end <= start"),
  "manual_segment_window_requires_explicit_valid_user_input",
));
checks.push(check(
  app.includes('document.addEventListener("input"')
    && app.includes("markSegmentInputEdited(event.target)"),
  "segment_time_inputs_mark_user_edits",
));
checks.push(check(
  iaAction.includes('const requiresSegmentDraft = action === "exclude-segment" || action === "add-label"')
    && iaAction.includes("requiresSegmentDraft && !file?.id")
    && iaAction.includes("requiresSegmentDraft && !selectedSegment")
    && iaAction.includes('persistence: "not_mutated"'),
  "segment_and_label_drafts_block_without_file_or_range",
));
checks.push(check(
  excludeBranch.includes("file_id: file.id")
    && excludeBranch.includes("start_sec: start")
    && excludeBranch.includes("end_sec: end")
    && !/(\?\?\s*30|:\s*30\b|:\s*35\b|start\s*\+\s*5|12|18)/.test(excludeBranch),
  "exclude_segment_has_no_default_time_fallback",
));
checks.push(check(
  addLabelBranch.includes("file_id: file.id")
    && addLabelBranch.includes("target: `${start.toFixed(1)} s`")
    && !/(\?\?\s*30|30\.0|12|18)/.test(addLabelBranch),
  "add_label_has_no_default_time_fallback",
));

const report = {
  script: path.basename(__filename),
  checks,
  passed: checks.every((item) => item.pass),
};

console.log(JSON.stringify(report, null, 2));
process.exit(report.passed ? 0 : 1);
