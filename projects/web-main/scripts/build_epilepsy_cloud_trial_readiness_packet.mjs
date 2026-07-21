import fs from "node:fs";
import path from "node:path";

const ROOT = process.cwd();
const OUT_DIR = path.resolve(ROOT, "work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-readiness");
const OUT_FILE = path.join(OUT_DIR, "readiness_packet.json");

const paths = {
  local_browser_e2e: "work/release_evidence/20260629-epilepsy-cloud-trial-v0-1-browser-upload-to-export/browser_upload_to_export.json",
  static_child_contract: "work/release_evidence/20260629-epilepsy-child-page-p0/static_epilepsy_child_page_contract.json",
  spec_pack: "work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-spec-pack/spec_pack_result.json",
  copy_governance: "work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-copy-governance/copy_governance_result.json",
  failure_states: "work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-failure-states/failure_states_browser.json",
  release_gate: "work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-release-gate/release_gate_result.json",
  cloud_browser_e2e: "work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-cloud-upload-to-export/browser_upload_to_export.json",
  owner_data_manifest_contract: "work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-owner-data-manifest/owner_data_manifest_contract.json",
  owner_data_regression: "work/release_evidence/07-full-product-e2e-pdca/11_real_dataset_owner_review/real_dataset_regression_result.json",
  checkpoint_doc: "docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_checkpoint_20260630.md",
  cutover_runbook: "docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_cloud_cutover_runbook_20260630.md",
};

function readJson(relPath) {
  const absPath = path.resolve(ROOT, relPath);
  if (!fs.existsSync(absPath)) return null;
  return JSON.parse(fs.readFileSync(absPath, "utf8").replace(/^\uFEFF/, ""));
}

function summarizeChecks(checks = {}) {
  const entries = Object.entries(checks);
  return {
    total: entries.length,
    passed: entries.filter(([, value]) => Boolean(value)).length,
    failed: entries.filter(([, value]) => !value).map(([name]) => name),
  };
}

function statusFromEvidence(name, relPath, predicate, details = {}) {
  const evidence = readJson(relPath);
  const passed = Boolean(evidence && predicate(evidence));
  return {
    name,
    status: passed ? "passed" : "missing_or_failed",
    evidence_path: relPath,
    present: Boolean(evidence),
    summary: evidence?.checks ? summarizeChecks(evidence.checks) : null,
    details: details(evidence),
  };
}

const releaseGate = readJson(paths.release_gate);
const cloudFrontendUrl = process.env.QLANALYSER_CLOUD_FRONTEND_URL || process.env.QLANALYSER_FRONTEND_URL || "";
const cloudApiBaseUrl = process.env.QLANALYSER_CLOUD_API_BASE_URL || process.env.QLANALYSER_API_BASE_URL || "";

const gates = [
  statusFromEvidence(
    "local_browser_upload_to_export",
    paths.local_browser_e2e,
    (evidence) => evidence.status === "passed" && summarizeChecks(evidence.checks).failed.length === 0,
    (evidence) => ({
      frontend_url: evidence?.frontend_url || null,
      truth_stage_code: evidence?.inline_stage_overlay_toggle?.stageText || null,
      task_module: evidence?.backend_task?.module_name || null,
      workflow_id: evidence?.backend_task?.workflow_id || null,
    }),
  ),
  statusFromEvidence(
    "static_child_page_contract",
    paths.static_child_contract,
    (evidence) => evidence.status === "passed" && (evidence.failed || []).length === 0,
    (evidence) => ({ failed: evidence?.failed || [] }),
  ),
  statusFromEvidence(
    "spec_pack_coverage",
    paths.spec_pack,
    (evidence) => evidence.status === "passed" && (evidence.failed || []).length === 0,
    (evidence) => ({ failed: evidence?.failed || [], handoff_docs: evidence?.evidence_paths || null }),
  ),
  statusFromEvidence(
    "scoped_copy_governance",
    paths.copy_governance,
    (evidence) => evidence.status === "passed" && (evidence.failed || []).length === 0,
    (evidence) => ({ failed: evidence?.failed || [], forbidden_customer_hits: evidence?.forbidden_customer_hits || [] }),
  ),
  statusFromEvidence(
    "failure_state_browser_e2e",
    paths.failure_states,
    (evidence) => evidence.status === "passed" && (evidence.errors || []).length === 0 && summarizeChecks(evidence.checks).failed.length === 0,
    (evidence) => ({ errors: evidence?.errors || [] }),
  ),
  statusFromEvidence(
    "cloud_browser_upload_to_export",
    paths.cloud_browser_e2e,
    (evidence) => evidence.status === "passed" && summarizeChecks(evidence.checks).failed.length === 0 && !/127\.0\.0\.1|localhost/.test(String(evidence.frontend_url || "")),
    (evidence) => ({ frontend_url: evidence?.frontend_url || null }),
  ),
  statusFromEvidence(
    "owner_data_manifest_contract",
    paths.owner_data_manifest_contract,
    (evidence) => evidence.status === "passed" && (evidence.blockers || []).length === 0,
    (evidence) => ({ blockers: evidence?.blockers || [], warnings: evidence?.warnings || [] }),
  ),
  statusFromEvidence(
    "owner_data_regression",
    paths.owner_data_regression,
    (evidence) => evidence.status === "passed" || evidence.final_verdict === "passed",
    (evidence) => ({ status: evidence?.status || evidence?.final_verdict || null }),
  ),
];

const blockers = [];
for (const gate of gates) {
  if (gate.status !== "passed") blockers.push(gate.name);
}

const packet = {
  script: "build_epilepsy_cloud_trial_readiness_packet.mjs",
  generated_at: new Date().toISOString(),
  objective: "QLanalyser epilepsy-like event screening cloud trial v0.1 readiness",
  status: blockers.length ? "not_ready" : "ready",
  internal_local_status: gates.slice(0, 5).every((gate) => gate.status === "passed") ? "passed" : "incomplete",
  cloud_trial_rc_status: blockers.includes("cloud_browser_upload_to_export") ? "blocked_cloud_e2e_missing" : "ready_for_acceptance",
  external_release_status: blockers.includes("owner_data_manifest_contract")
    ? "blocked_owner_manifest_missing_or_invalid"
    : blockers.includes("owner_data_regression")
      ? "blocked_owner_data_regression_missing"
      : "ready_for_acceptance",
  cloud_target_env: {
    frontend_url: cloudFrontendUrl || null,
    api_base_url: cloudApiBaseUrl || null,
  },
  handoff_documents: {
    checkpoint_doc: {
      path: paths.checkpoint_doc,
      present: fs.existsSync(path.resolve(ROOT, paths.checkpoint_doc)),
    },
    cutover_runbook: {
      path: paths.cutover_runbook,
      present: fs.existsSync(path.resolve(ROOT, paths.cutover_runbook)),
    },
  },
  gates,
  blockers,
  release_gate_snapshot: releaseGate
    ? {
      path: paths.release_gate,
      cloud_trial_rc_verdict: releaseGate.cloud_trial_rc_verdict,
      external_release_verdict: releaseGate.external_release_verdict,
      checks: releaseGate.checks,
    }
    : null,
  next_commands: {
    cloud_browser_e2e: cloudFrontendUrl && cloudApiBaseUrl
      ? `QLANALYSER_FRONTEND_URL=${cloudFrontendUrl} QLANALYSER_API_BASE_URL=${cloudApiBaseUrl} QLANALYSER_EPILEPSY_UPLOAD_E2E_DIR=work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-cloud-upload-to-export node scripts/e2e_epilepsy_cloud_trial_upload_to_export_browser.mjs`
      : "Set QLANALYSER_CLOUD_FRONTEND_URL and QLANALYSER_CLOUD_API_BASE_URL, then run scripts/e2e_epilepsy_cloud_trial_upload_to_export_browser.mjs.",
    release_gate: "node scripts/validate_epilepsy_cloud_trial_v0_1_release_gate.mjs",
    strict_cloud_gate: "QLANALYSER_REQUIRE_CLOUD=1 node scripts/validate_epilepsy_cloud_trial_v0_1_release_gate.mjs",
    owner_manifest_template: "work/release_evidence/07-full-product-e2e-pdca/11_real_dataset_owner_review/input_manifest.template.json",
    owner_manifest_checklist: "work/release_evidence/07-full-product-e2e-pdca/11_real_dataset_owner_review/01_input_gate/owner_input_checklist.md",
    owner_manifest_validator: "node scripts/validate_epilepsy_owner_data_manifest_v0_1.mjs",
    owner_input_gate_packet: "python -X utf8 scripts/build_real_dataset_owner_review_packet.py",
    owner_data_regression: "python -X utf8 scripts/run_real_dataset_regression_from_manifest.py",
    owner_input_packet: "node scripts/build_epilepsy_cloud_trial_owner_input_packet.mjs",
    checkpoint_doc: paths.checkpoint_doc,
    cutover_runbook: paths.cutover_runbook,
  },
};

fs.mkdirSync(OUT_DIR, { recursive: true });
fs.writeFileSync(OUT_FILE, `${JSON.stringify(packet, null, 2)}\n`, "utf8");
console.log(JSON.stringify(packet, null, 2));
if (process.env.QLANALYSER_REQUIRE_READY === "1" && packet.status !== "ready") {
  process.exit(1);
}
