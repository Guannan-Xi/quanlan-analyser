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
  "20260626-teaching-mode-independent-product-design",
  "implementation",
);
const evidencePath = path.join(evidenceDir, "static_acceptance.json");

function read(rel) {
  return fs.readFileSync(path.join(root, rel), "utf8");
}

function exists(rel) {
  return fs.existsSync(path.join(root, rel));
}

function check(pass, name, details = {}) {
  return { name, pass: Boolean(pass), details };
}

function visibleText(html) {
  return html
    .replace(/<script[\s\S]*?<\/script>/gi, " ")
    .replace(/<style[\s\S]*?<\/style>/gi, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

const appJs = read("frontend/app.js");
const indexHtml = read("frontend/index.html");
const labDemoService = read("backend/services/lab_demo_service.py");
const storageService = read("backend/services/storage_service.py");
const protectionScript = read("scripts/acceptance_teaching_mode_protection.py");

const checks = [
  check(indexHtml.includes('id="teachingModeBtn"'), "teaching_mode_switch_button_exists"),
  check(appJs.includes("state.teaching") && appJs.includes("startTeachingMode"), "teaching_mode_state_machine_exists"),
  check(appJs.includes("filteredWorkspaceProjects") && appJs.includes("isTeachingDemoProject"), "normal_mode_can_hide_teaching_projects"),
  check(appJs.includes("proj_demo_learning") && appJs.includes("eeg_demo_teaching_oddball"), "regular_teaching_ids_present"),
  check(appJs.includes("proj_demo_epilepsy_lab") && appJs.includes("eeg_demo_epilepsy_high_amplitude"), "epilepsy_teaching_ids_present"),
  check(appJs.includes("protected_teaching_dataset"), "frontend_reads_protected_teaching_dataset_flag"),
  check(appJs.includes("teachingProtectedMessage"), "frontend_blocks_protected_actions"),
  check(appJs.includes('[data-ia-action="rename-data"]') && appJs.includes("aria-disabled"), "data_rename_action_can_be_disabled"),
  check(labDemoService.includes("protected_teaching_dataset"), "demo_dataset_source_marks_protection"),
  check(labDemoService.includes("protected_teaching_demo"), "demo_dataset_source_marks_retention_policy"),
  check(storageService.includes("TEACHING_DATASET_PROTECTED"), "backend_uses_structured_protection_error"),
  check(storageService.includes("delete_eeg_file") && storageService.includes("_is_protected_teaching_file"), "backend_blocks_protected_file_mutation"),
  check(storageService.includes("archive_project") && storageService.includes("_is_protected_teaching_project"), "backend_blocks_protected_project_mutation"),
  check(
    exists("scripts/acceptance_teaching_mode_protection.py") && protectionScript.includes("TEACHING_DATASET_PROTECTED"),
    "backend_protection_smoke_script_exists",
  ),
  check(exists("docs/product/teaching_mode_independent_requirements_20260626.md"), "requirements_document_exists"),
  check(exists("docs/product/teaching_mode_independent_design_20260626.md"), "design_document_exists"),
  check(exists("docs/product/teaching_mode_independent_test_plan_20260626.md"), "test_plan_document_exists"),
  check(
    exists("work/release_evidence/20260626-teaching-mode-independent-product-design/deepseek_logic_review_packet.md"),
    "deepseek_review_packet_exists_pending_status_only",
  ),
  check(indexHtml.includes("个人中心") || appJs.includes("个人中心"), "personal_center_copy_still_present"),
];

const forbiddenNormalLeakage = [
  "fixture",
  "backend",
  "workflow",
  "runner",
];
const visibleIndexText = visibleText(indexHtml);
for (const term of forbiddenNormalLeakage) {
  checks.push(check(!visibleIndexText.includes(term), `index_customer_copy_avoids_developer_term:${term}`));
}

const report = {
  script: path.basename(__filename),
  generated_at: new Date().toISOString(),
  checks,
  passed: checks.every((item) => item.pass),
};

fs.mkdirSync(evidenceDir, { recursive: true });
fs.writeFileSync(evidencePath, `${JSON.stringify(report, null, 2)}\n`, "utf8");
console.log(JSON.stringify(report, null, 2));
process.exit(report.passed ? 0 : 1);
