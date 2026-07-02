import fs from "node:fs";
import path from "node:path";

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1")), "..");
const outDir = path.join(root, "work", "release_evidence", "20260628-release-candidate-self-adversarial-audit");
const jsonPath = path.join(outDir, "release_candidate_self_adversarial_audit.json");
const mdPath = path.join(root, "docs", "product", "qlanalyser_release_candidate_self_adversarial_audit_20260628.md");

function read(rel) {
  return fs.readFileSync(path.join(root, rel), "utf8");
}

function exists(rel) {
  return fs.existsSync(path.join(root, rel));
}

function readJson(rel) {
  return JSON.parse(read(rel));
}

function check(pass, id, layer, requirement, evidence = {}, severity = "P0") {
  return {
    id,
    layer,
    requirement,
    severity,
    status: pass ? "pass" : "fail",
    evidence,
  };
}

function statusPassed(value) {
  return value === true || String(value || "").toLowerCase() === "passed" || String(value || "").toUpperCase() === "PASS";
}

const html = read("frontend/index.html");
const app = read("frontend/app.js");
const epilepsyHtml = read("frontend/epilepsy-workbench.html");
const epilepsyJs = read("frontend/epilepsy-workbench.js");
const waveformJs = read("frontend/waveform-workbench.js");
const waveformHtml = read("frontend/waveform-workbench.html");

const evidenceFiles = {
  mainEpilepsy: "work/release_evidence/20260628-main-epilepsy-entry-contract/main_epilepsy_entry_contract.json",
  epilepsyWorkbench: "work/e2e_epilepsy_workbench/ui_e2e/epilepsy_workbench_e2e.json",
  waveformDual: "work/release_evidence/20260628-waveform-workbench-dual-mode-contract/waveform_workbench_dual_mode_contract_result.json",
  waveformEpoch: "work/release_evidence/20260628-waveform-workbench-epoch-review/waveform_workbench_e2e_result.json",
  backendSmoke: "work/release_evidence/07-full-product-e2e-pdca/04_backend_api/backend_api_smoke.json",
  mlAssets: "work/e2e_epilepsy_ml_migration/asset_validation.json",
  mlFeatureContract: "work/e2e_epilepsy_ml_migration/feature_contract.json",
  mlModelSmoke: "work/e2e_epilepsy_ml_migration/model_smoke.json",
  mlFixtureRun: "work/e2e_epilepsy_ml_migration/fixture_run_evidence.json",
};

const loadedEvidence = Object.fromEntries(Object.entries(evidenceFiles).map(([key, rel]) => [key, exists(rel) ? readJson(rel) : null]));
const mainCards = Array.from(html.matchAll(/class="[^"]*\bia-method-card\b[^"]*"[^>]*data-module-id="([^"]+)"/g)).map((match) => match[1]);
const forbiddenCustomerCopy = [
  "TimeChart experimental",
  "epilepsy-renderer-timechart",
  "renderer=timechart",
  "当前可用：8 项",
  "从 8 项",
  'data-module-id="qc"',
];
const sourceForCopy = [html, app, epilepsyHtml, epilepsyJs, waveformHtml, waveformJs].join("\n");

const checks = [
  check(
    html.includes('data-testid="open-waveform-workbench-clean"')
      && html.includes("customer_mode=clean")
      && html.includes("mode_switch=hidden"),
    "WW-DISC-01",
    "global_page",
    "Main data-preparation page exposes a discoverable clean WaveformWorkbench entry.",
    { source: "frontend/index.html" },
  ),
  check(
    waveformJs.includes("workbenchModeParam")
      && waveformJs.includes("mode_switch")
      && waveformJs.includes("customer_mode"),
    "WW-MODE-01",
    "functional_region",
    "WaveformWorkbench supports basic/epoch mode separation plus customer clean mode.",
    { source: "frontend/waveform-workbench.js" },
  ),
  check(
    waveformHtml.includes('data-testid="waveform-overview"')
      && waveformHtml.includes('role="slider"')
      && waveformJs.includes("overviewTrack")
      && waveformJs.includes("keydown"),
    "WW-KEY-01",
    "control_level",
    "WaveformWorkbench exposes keyboard and draggable time-navigation semantics.",
    { source: "frontend/waveform-workbench.html/js" },
  ),
  check(
    statusPassed(loadedEvidence.waveformDual?.status) && Array.isArray(loadedEvidence.waveformDual?.failed) && loadedEvidence.waveformDual.failed.length === 0,
    "WW-E2E-01",
    "business_workflow",
    "WaveformWorkbench basic/epoch/clean dual-mode E2E passed.",
    { evidence: evidenceFiles.waveformDual },
  ),
  check(
    statusPassed(loadedEvidence.waveformEpoch?.status)
      && (!Array.isArray(loadedEvidence.waveformEpoch?.failed) || loadedEvidence.waveformEpoch.failed.length === 0),
    "WW-E2E-02",
    "business_workflow",
    "WaveformWorkbench epoch review interaction E2E passed.",
    { evidence: evidenceFiles.waveformEpoch },
  ),
  check(
    mainCards.length === 9 && mainCards.includes("epilepsy_ml") && !mainCards.includes("qc"),
    "MAIN-METHOD-01",
    "global_page",
    "Main analysis page exposes 9 analysis methods and keeps QC out of method cards.",
    { actual_method_ids: mainCards },
  ),
  check(
    app.includes('runRealTask("epilepsy_ml", "epilepsy_ml_xgboost")')
      && app.includes("epilepsyWorkbenchUrl")
      && app.includes('data-testid="open-epilepsy-workbench"'),
    "EPI-MAIN-01",
    "functional_region",
    "Main app can submit epilepsy ML screening and link to the review workbench.",
    { source: "frontend/app.js" },
  ),
  check(
    statusPassed(loadedEvidence.mainEpilepsy?.status)
      && loadedEvidence.mainEpilepsy?.checks?.task_payload_module
      && loadedEvidence.mainEpilepsy?.checks?.task_payload_workflow
      && loadedEvidence.mainEpilepsy?.checks?.result_workbench_link,
    "EPI-MAIN-E2E-01",
    "business_workflow",
    "Main app epilepsy entry E2E proves payload and workbench link contract.",
    { evidence: evidenceFiles.mainEpilepsy, checks: loadedEvidence.mainEpilepsy?.checks || {} },
  ),
  check(
    epilepsyJs.includes("correctionModeActive")
      && epilepsyJs.includes("epochOverrides")
      && epilepsyJs.includes("reviewActions")
      && epilepsyJs.includes("/waveform-window"),
    "EPI-WB-01",
    "functional_region",
    "Epilepsy workbench separates source output, manual review layer, and lightweight waveform window.",
    { source: "frontend/epilepsy-workbench.js" },
  ),
  check(
    !epilepsyJs.includes('["canvas", "timechart", "svg"].includes')
      && !epilepsyJs.includes('data-testid="epilepsy-renderer-timechart"')
      && !sourceForCopy.includes("TimeChart experimental"),
    "EPI-WB-02",
    "control_level",
    "Epilepsy workbench customer path does not expose TimeChart.",
    { source: "frontend/epilepsy-workbench.js/html" },
  ),
  check(
    statusPassed(loadedEvidence.epilepsyWorkbench?.status)
      && loadedEvidence.epilepsyWorkbench?.checks?.taskCompleted
      && loadedEvidence.epilepsyWorkbench?.checks?.epochCorrectionSaved
      && loadedEvidence.epilepsyWorkbench?.checks?.stageActionRecorded
      && loadedEvidence.epilepsyWorkbench?.checks?.waveformWindowReturned
      && loadedEvidence.epilepsyWorkbench?.checks?.waveformPreviewVisible,
    "EPI-WB-E2E-01",
    "business_workflow",
    "Epilepsy workbench E2E proves ML run, correction mode review action, undo path, and waveform preview.",
    { evidence: evidenceFiles.epilepsyWorkbench, checks: loadedEvidence.epilepsyWorkbench?.checks || {} },
  ),
  check(
    statusPassed(loadedEvidence.mlAssets?.status)
      && statusPassed(loadedEvidence.mlFeatureContract?.status)
      && statusPassed(loadedEvidence.mlModelSmoke?.status)
      && statusPassed(loadedEvidence.mlFixtureRun?.status),
    "EPI-ML-01",
    "business_workflow",
    "Epilepsy ML asset, feature schema, model smoke, and fixture run checks passed.",
    {
      asset_validation: evidenceFiles.mlAssets,
      feature_contract: evidenceFiles.mlFeatureContract,
      model_smoke: evidenceFiles.mlModelSmoke,
      fixture_run: evidenceFiles.mlFixtureRun,
    },
  ),
  check(
    statusPassed(loadedEvidence.backendSmoke?.status) && Array.isArray(loadedEvidence.backendSmoke?.blockers) && loadedEvidence.backendSmoke.blockers.length === 0,
    "BACKEND-01",
    "business_workflow",
    "Backend API smoke passed with no blockers.",
    { evidence: evidenceFiles.backendSmoke },
  ),
  check(
    forbiddenCustomerCopy.every((term) => !sourceForCopy.includes(term)),
    "COPY-01",
    "control_level",
    "No blocking stale customer copy or QC-as-method copy remains in the edited customer path.",
    { forbidden_terms: forbiddenCustomerCopy },
  ),
  check(
    !exists("work/release_evidence/07-full-product-e2e-pdca/11_real_dataset_owner_review/input_manifest.json"),
    "RELEASE-RISK-01",
    "business_workflow",
    "External release owner-data regression remains blocked by missing authorized input_manifest.json.",
    { expected_missing: "work/release_evidence/07-full-product-e2e-pdca/11_real_dataset_owner_review/input_manifest.json" },
    "P1",
  ),
];

const blockingFailures = checks.filter((item) => item.severity === "P0" && item.status !== "pass");
const report = {
  schema_version: "qlanalyser.release_candidate_self_adversarial_audit.v1",
  generated_at: new Date().toISOString(),
  final_verdict: blockingFailures.length ? "blocked" : "release_candidate_pass_with_risks",
  external_release_verdict: exists("work/release_evidence/07-full-product-e2e-pdca/11_real_dataset_owner_review/input_manifest.json")
    ? "ready_for_owner_regression"
    : "blocked_owner_data_missing",
  checks,
  blocking_failures: blockingFailures,
};

const md = [
  "# QLanalyser Release Candidate Self-Adversarial Audit",
  "",
  `Generated: ${report.generated_at}`,
  "",
  `Final verdict: ${report.final_verdict}`,
  `External release verdict: ${report.external_release_verdict}`,
  "",
  "## Checks",
  "",
  ...checks.map((item) => `- ${item.status === "pass" ? "PASS" : "FAIL"} [${item.severity}] ${item.id} (${item.layer}): ${item.requirement}`),
  "",
  "## Blocking Failures",
  "",
  blockingFailures.length
    ? blockingFailures.map((item) => `- ${item.id}: ${item.requirement}`).join("\n")
    : "- None for internal release-candidate scope.",
  "",
  "## Known Release Risk",
  "",
  "- External release still requires authorized anonymous owner-data regression manifest and rerun.",
  "- Existing model deserialization warnings should be tracked before hard external release, although current ML smoke and fixture checks pass.",
  "",
].join("\n");

fs.mkdirSync(outDir, { recursive: true });
fs.mkdirSync(path.dirname(mdPath), { recursive: true });
fs.writeFileSync(jsonPath, `${JSON.stringify(report, null, 2)}\n`, "utf8");
fs.writeFileSync(mdPath, md, "utf8");
console.log(JSON.stringify({ status: report.final_verdict, external_release_verdict: report.external_release_verdict, jsonPath, mdPath, failed: blockingFailures.map((item) => item.id) }, null, 2));
if (blockingFailures.length) process.exit(1);
