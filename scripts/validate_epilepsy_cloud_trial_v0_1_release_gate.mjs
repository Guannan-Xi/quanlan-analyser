import fs from "node:fs";
import path from "node:path";

const ROOT = process.cwd();
const LOCAL_E2E = path.resolve(
  ROOT,
  "work/release_evidence/20260629-epilepsy-cloud-trial-v0-1-browser-upload-to-export/browser_upload_to_export.json",
);
const STATIC_CONTRACT = path.resolve(
  ROOT,
  "work/release_evidence/20260629-epilepsy-child-page-p0/static_epilepsy_child_page_contract.json",
);
const COPY_GOVERNANCE = path.resolve(
  ROOT,
  "work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-copy-governance/copy_governance_result.json",
);
const FAILURE_STATES = path.resolve(
  ROOT,
  "work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-failure-states/failure_states_browser.json",
);
const CLOUD_E2E = path.resolve(
  ROOT,
  "work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-cloud-upload-to-export/browser_upload_to_export.json",
);
const OWNER_DATA_MANIFEST_CONTRACT = path.resolve(
  ROOT,
  "work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-owner-data-manifest/owner_data_manifest_contract.json",
);
const OWNER_DATA_REGRESSION = path.resolve(
  ROOT,
  "work/release_evidence/07-full-product-e2e-pdca/11_real_dataset_owner_review/real_dataset_regression_result.json",
);
const OUT_DIR = path.resolve(ROOT, "work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-release-gate");
const OUT_FILE = path.join(OUT_DIR, "release_gate_result.json");
const REQUIRED_UPLOAD_TO_EXPORT_CHECKS = [
  "no_task_before_start",
  "upload_authorization_in_request",
  "upload_authorization_persisted",
  "uploaded_edf_metadata",
  "plan_confirmed_for_uploaded_file",
  "task_payload_contract",
  "task_completed",
  "stage_code_truth",
  "candidate_event_truth",
  "review_correction_saved",
  "review_export_published",
  "results_module_has_review_package",
  "non_medical_scope_export",
  "missing_upload_authorization_rejected",
  "unconfirmed_preparation_rejected",
  "wrong_workflow_rejected",
  "missing_review_session_export_rejected",
  "customer_review_labels_visible",
  "no_old_labels_in_candidate_panel",
  "no_epilepsy_staging_copy",
  "no_diagnosis_or_treatment_copy",
  "no_video_placeholder_copy",
  "customer_copy_no_old_review_labels",
  "inline_entry_waveform_first",
  "inline_no_duplicate_scale_controls",
  "inline_wheel_no_toast",
  "inline_progress_completed",
  "inline_spectrogram_same_window_source",
  "inline_stage_overlay_toggle",
];
const REQUIRED_FAILURE_STATE_CHECKS = [
  "missing_upload_authorization_ui",
  "unconfirmed_preparation_gate_ui",
  "screening_task_failure_ui",
  "artifact_load_failure_ui",
  "review_save_failure_ui",
  "export_failure_ui",
];

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, "utf8").replace(/^\uFEFF/, ""));
}

function readJsonIfExists(file) {
  if (!fs.existsSync(file)) return null;
  return readJson(file);
}

function isLocalUrl(rawUrl = "") {
  try {
    const url = new URL(rawUrl);
    return ["127.0.0.1", "localhost", "::1"].includes(url.hostname);
  } catch {
    return true;
  }
}

function summarizeChecks(checks = {}) {
  const entries = Object.entries(checks);
  return {
    total: entries.length,
    passed: entries.filter(([, value]) => Boolean(value)).length,
    failed: entries.filter(([, value]) => !value).map(([name]) => name),
  };
}

function requiredCheckCoverage(checks = {}) {
  const missing = REQUIRED_UPLOAD_TO_EXPORT_CHECKS.filter((name) => !(name in checks));
  const failed = REQUIRED_UPLOAD_TO_EXPORT_CHECKS.filter((name) => checks[name] !== true);
  return {
    required_total: REQUIRED_UPLOAD_TO_EXPORT_CHECKS.length,
    missing,
    failed,
    passed: missing.length === 0 && failed.length === 0,
  };
}

function requiredFailureStateCoverage(checks = {}) {
  const missing = REQUIRED_FAILURE_STATE_CHECKS.filter((name) => !(name in checks));
  const failed = REQUIRED_FAILURE_STATE_CHECKS.filter((name) => checks[name] !== true);
  return {
    required_total: REQUIRED_FAILURE_STATE_CHECKS.length,
    missing,
    failed,
    passed: missing.length === 0 && failed.length === 0,
  };
}

function main() {
  const localE2e = readJson(LOCAL_E2E);
  const staticContract = readJson(STATIC_CONTRACT);
  const copyGovernance = readJsonIfExists(COPY_GOVERNANCE);
  const failureStates = readJsonIfExists(FAILURE_STATES);
  const cloudE2e = readJsonIfExists(CLOUD_E2E);
  const ownerDataManifestContract = readJsonIfExists(OWNER_DATA_MANIFEST_CONTRACT);
  const ownerDataRegression = readJsonIfExists(OWNER_DATA_REGRESSION);
  const localSummary = summarizeChecks(localE2e.checks || {});
  const cloudSummary = summarizeChecks(cloudE2e?.checks || {});
  const localRequiredCoverage = requiredCheckCoverage(localE2e.checks || {});
  const cloudRequiredCoverage = requiredCheckCoverage(cloudE2e?.checks || {});
  const failureStateCoverage = requiredFailureStateCoverage(failureStates?.checks || {});
  const cloudFrontendUrl = process.env.QLANALYSER_CLOUD_FRONTEND_URL || process.env.QLANALYSER_FRONTEND_URL || "";
  const cloudApiBaseUrl = process.env.QLANALYSER_CLOUD_API_BASE_URL || process.env.QLANALYSER_API_BASE_URL || "";
  const localEvidenceIsLocalhost = isLocalUrl(localE2e.frontend_url || "");
  const cloudEvidenceIsNonLocal = Boolean(cloudE2e?.frontend_url && !isLocalUrl(cloudE2e.frontend_url));
  const hasCloudTarget = Boolean(cloudFrontendUrl && cloudApiBaseUrl && !isLocalUrl(cloudFrontendUrl) && !isLocalUrl(cloudApiBaseUrl));

  const checks = {
    local_browser_upload_to_export_passed: localE2e.status === "passed" && localSummary.failed.length === 0 && localRequiredCoverage.passed,
    static_inline_child_contract_passed: staticContract.status === "passed" && (staticContract.failed || []).length === 0,
    copy_governance_passed: copyGovernance?.status === "passed" && (copyGovernance.failed || []).length === 0,
    failure_state_browser_e2e_passed: failureStates?.status === "passed" && (failureStates.errors || []).length === 0 && failureStateCoverage.passed,
    local_evidence_not_misclaimed_as_cloud: localEvidenceIsLocalhost,
    cloud_target_env_present_and_non_local: hasCloudTarget,
    cloud_browser_upload_to_export_evidence_present: cloudE2e?.status === "passed" && cloudSummary.failed.length === 0 && cloudRequiredCoverage.passed && cloudEvidenceIsNonLocal,
    owner_data_manifest_contract_passed: ownerDataManifestContract?.status === "passed" && (ownerDataManifestContract.blockers || []).length === 0,
    owner_data_regression_present: Boolean(ownerDataRegression?.status === "passed" || ownerDataRegression?.final_verdict === "passed"),
  };
  const cloudTrialEvidenceReady = checks.local_browser_upload_to_export_passed
    && checks.static_inline_child_contract_passed
    && checks.copy_governance_passed
    && checks.failure_state_browser_e2e_passed
    && checks.cloud_browser_upload_to_export_evidence_present;
  const cloudTrialRcReady = cloudTrialEvidenceReady;
  const externalReleaseReady = cloudTrialRcReady && checks.owner_data_manifest_contract_passed && checks.owner_data_regression_present;

  const result = {
    script: "validate_epilepsy_cloud_trial_v0_1_release_gate.mjs",
    generated_at: new Date().toISOString(),
    local_evidence: {
      path: path.relative(ROOT, LOCAL_E2E),
      status: localE2e.status,
      frontend_url: localE2e.frontend_url,
      summary: localSummary,
      required_check_coverage: localRequiredCoverage,
      view_title: localE2e.inline_initial_state?.viewTitle || "",
      active_nav: localE2e.inline_initial_state?.activeNav || "",
      stage_overlay: localE2e.inline_stage_overlay_toggle || null,
    },
    static_contract: {
      path: path.relative(ROOT, STATIC_CONTRACT),
      status: staticContract.status,
      failed: staticContract.failed || [],
    },
    copy_governance: {
      path: path.relative(ROOT, COPY_GOVERNANCE),
      present: Boolean(copyGovernance),
      status: copyGovernance?.status || "missing",
      failed: copyGovernance?.failed || [],
    },
    failure_states: {
      path: path.relative(ROOT, FAILURE_STATES),
      present: Boolean(failureStates),
      status: failureStates?.status || "missing",
      errors: failureStates?.errors || [],
      required_check_coverage: failureStates ? failureStateCoverage : null,
    },
    cloud_evidence: {
      path: path.relative(ROOT, CLOUD_E2E),
      present: Boolean(cloudE2e),
      status: cloudE2e?.status || "missing",
      frontend_url: cloudE2e?.frontend_url || null,
      summary: cloudE2e ? cloudSummary : null,
      required_check_coverage: cloudE2e ? cloudRequiredCoverage : null,
      non_local: cloudEvidenceIsNonLocal,
    },
    owner_data_regression: {
      path: path.relative(ROOT, OWNER_DATA_REGRESSION),
      present: Boolean(ownerDataRegression),
      status: ownerDataRegression?.status || ownerDataRegression?.final_verdict || "missing",
    },
    owner_data_manifest_contract: {
      path: path.relative(ROOT, OWNER_DATA_MANIFEST_CONTRACT),
      present: Boolean(ownerDataManifestContract),
      status: ownerDataManifestContract?.status || "missing",
      blockers: ownerDataManifestContract?.blockers || [],
      warnings: ownerDataManifestContract?.warnings || [],
    },
    cloud_target: {
      frontend_url: cloudFrontendUrl || null,
      api_base_url: cloudApiBaseUrl || null,
      has_non_local_target: hasCloudTarget,
    },
    checks: {
      ...checks,
      cloud_trial_current_env_present_for_rerun: checks.cloud_target_env_present_and_non_local,
    },
    cloud_trial_rc_verdict: cloudTrialRcReady
      ? "cloud_trial_rc_ready_for_acceptance"
      : "blocked_cloud_trial_e2e_missing",
    external_release_verdict: externalReleaseReady
      ? "external_release_ready_for_acceptance"
      : !checks.owner_data_manifest_contract_passed
        ? "blocked_owner_manifest_missing_or_invalid"
        : checks.owner_data_regression_present
        ? "blocked_cloud_trial_e2e_missing"
        : "blocked_owner_data_regression_missing",
    release_verdict: cloudTrialRcReady
      ? "cloud_release_candidate_ready_for_acceptance"
      : "blocked_cloud_trial_e2e_missing",
    next_required_command: hasCloudTarget
      ? `QLANALYSER_FRONTEND_URL=${cloudFrontendUrl} QLANALYSER_API_BASE_URL=${cloudApiBaseUrl} QLANALYSER_EPILEPSY_UPLOAD_E2E_DIR=work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-cloud-upload-to-export node scripts/e2e_epilepsy_cloud_trial_upload_to_export_browser.mjs`
      : "Set QLANALYSER_CLOUD_FRONTEND_URL and QLANALYSER_CLOUD_API_BASE_URL to the real cloud/staging target, then rerun the browser upload-to-export E2E.",
    non_medical_boundary: "research_screening_support_only",
  };

  fs.mkdirSync(OUT_DIR, { recursive: true });
  fs.writeFileSync(OUT_FILE, `${JSON.stringify(result, null, 2)}\n`, "utf8");
  console.log(JSON.stringify(result, null, 2));

  if (process.env.QLANALYSER_REQUIRE_CLOUD === "1" && result.cloud_trial_rc_verdict !== "cloud_trial_rc_ready_for_acceptance") {
    process.exit(1);
  }
  if (process.env.QLANALYSER_REQUIRE_EXTERNAL_RELEASE === "1" && result.external_release_verdict !== "external_release_ready_for_acceptance") {
    process.exit(1);
  }
}

main();
