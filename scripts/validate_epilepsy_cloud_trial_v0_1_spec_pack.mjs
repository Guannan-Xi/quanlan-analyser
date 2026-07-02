import fs from "node:fs";
import path from "node:path";

const ROOT = process.cwd();
const OUT_DIR = path.resolve(ROOT, "work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-spec-pack");
const OUT_FILE = path.join(OUT_DIR, "spec_pack_result.json");

const docs = {
  goal: "docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_goal_20260629.md",
  requirements: "docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_requirements_20260629.md",
  architecture: "docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_architecture_20260629.md",
  detailed_design: "docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_detailed_design_20260629.md",
  data_api_contract: "docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_data_api_contract_20260629.md",
  e2e_test_plan: "docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_e2e_test_plan_20260629.md",
  release_plan: "docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_release_plan_20260629.md",
  checkpoint: "docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_checkpoint_20260630.md",
  cutover_runbook: "docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_cloud_cutover_runbook_20260630.md",
};

function read(relPath) {
  const absPath = path.resolve(ROOT, relPath);
  if (!fs.existsSync(absPath)) return null;
  return fs.readFileSync(absPath, "utf8");
}

function hasAny(text, terms) {
  return terms.some((term) => text.includes(term));
}

const texts = {};
const files = {};
for (const [name, relPath] of Object.entries(docs)) {
  const text = read(relPath);
  texts[name] = text || "";
  files[name] = {
    path: relPath,
    present: Boolean(text),
    bytes: text ? Buffer.byteLength(text, "utf8") : 0,
  };
}

const allText = Object.values(texts).join("\n");

const checks = {
  goal_doc_present: files.goal.present,
  six_pack_present: [
    "requirements",
    "architecture",
    "detailed_design",
    "data_api_contract",
    "e2e_test_plan",
    "release_plan",
  ].every((name) => files[name].present),
  checkpoint_present: files.checkpoint.present,
  cutover_runbook_present: files.cutover_runbook.present,
  epilepsy_screening_not_staging: hasAny(allText, ["epilepsy-like event screening", "癫痫样事件初筛", "event screening, not staging"]),
  upload_to_export_scope_present: hasAny(allText, ["upload-to-export", "browser upload", "from zero browser upload"]),
  waveform_stft_stage_candidate_scope_present: ["waveform", "STFT", "Stage_Code", "candidate"].every((term) => allText.includes(term)),
  manual_review_and_export_scope_present: ["manual", "review", "export"].every((term) => allText.toLowerCase().includes(term)),
  non_medical_boundary_present: hasAny(allText, ["non-medical", "research-support", "research_screening_support_only", "\u4e0d\u7528\u4e8e\u8bca\u65ad"]),
  sleep_video_out_of_p0_present: hasAny(allText, ["sleep staging", "video analysis"]) && hasAny(allText, ["Out of scope", "future interfaces", "future interface", "\u4e0d\u8fdb\u5165 v0.1 P0"]),
  synthetic_truth_e2e_present: ["regular_epilepsy_labeled_60s.edf", "000001100000", "25.0-35.0s"].every((term) => allText.includes(term)),
  local_vs_cloud_boundary_present: hasAny(allText, ["Local evidence must not be used as a substitute for cloud evidence", "localhost-only evidence", "cloud trial RC remains blocked"]),
  cloud_blocker_present: hasAny(allText, ["blocked_cloud_trial_e2e_missing", "cloud_browser_upload_to_export", "QLANALYSER_CLOUD_FRONTEND_URL"]),
  owner_manifest_blocker_present: hasAny(allText, ["input_manifest.json", "owner_data_manifest_contract", "owner/data steward"]),
  owner_regression_blocker_present: hasAny(allText, ["real_dataset_regression_result.json", "run_real_dataset_regression_from_manifest.py"]),
  readiness_packet_present: fs.existsSync(path.resolve(ROOT, "work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-readiness/readiness_packet.json")),
};

const failed = Object.entries(checks)
  .filter(([, passed]) => !passed)
  .map(([name]) => name);

const result = {
  script: "validate_epilepsy_cloud_trial_v0_1_spec_pack.mjs",
  generated_at: new Date().toISOString(),
  status: failed.length ? "failed" : "passed",
  files,
  checks,
  failed,
  evidence_paths: {
    readiness_packet: "work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-readiness/readiness_packet.json",
    checkpoint_doc: docs.checkpoint,
    cutover_runbook: docs.cutover_runbook,
  },
};

fs.mkdirSync(OUT_DIR, { recursive: true });
fs.writeFileSync(OUT_FILE, `${JSON.stringify(result, null, 2)}\n`, "utf8");
console.log(JSON.stringify(result, null, 2));
if (failed.length) process.exit(1);
