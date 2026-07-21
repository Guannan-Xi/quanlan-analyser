import fs from "node:fs";
import path from "node:path";

const ROOT = process.cwd();
const OUT_DIR = path.resolve(ROOT, "work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-owner-input-packet");
const JSON_OUT = path.join(OUT_DIR, "owner_input_packet.json");
const MD_OUT = path.join(OUT_DIR, "owner_input_packet.md");

const paths = {
  readiness: "work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-readiness/readiness_packet.json",
  release_gate: "work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-release-gate/release_gate_result.json",
  cloud_preflight: "work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-cloud-target-preflight/preflight_result.json",
  owner_manifest_contract: "work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-owner-data-manifest/owner_data_manifest_contract.json",
  owner_manifest_template: "work/release_evidence/07-full-product-e2e-pdca/11_real_dataset_owner_review/input_manifest.template.json",
  owner_input_checklist: "work/release_evidence/07-full-product-e2e-pdca/11_real_dataset_owner_review/01_input_gate/owner_input_checklist.md",
};

function readJson(relPath) {
  const absPath = path.resolve(ROOT, relPath);
  if (!fs.existsSync(absPath)) return null;
  return JSON.parse(fs.readFileSync(absPath, "utf8").replace(/^\uFEFF/, ""));
}

function exists(relPath) {
  return fs.existsSync(path.resolve(ROOT, relPath));
}

const readiness = readJson(paths.readiness);
const releaseGate = readJson(paths.release_gate);
const cloudPreflight = readJson(paths.cloud_preflight);
const ownerManifestContract = readJson(paths.owner_manifest_contract);

const packet = {
  script: "build_epilepsy_cloud_trial_owner_input_packet.mjs",
  generated_at: new Date().toISOString(),
  purpose: "Collect the remaining external inputs needed for QLanalyser epilepsy-like event screening cloud trial v0.1.",
  current_status: {
    internal_local_status: readiness?.internal_local_status || "unknown",
    cloud_trial_rc_status: readiness?.cloud_trial_rc_status || releaseGate?.cloud_trial_rc_verdict || "unknown",
    external_release_status: readiness?.external_release_status || releaseGate?.external_release_verdict || "unknown",
  },
  inputs_needed: [
    {
      owner: "Cloud/deployment owner",
      input: "Non-local cloud or staging frontend URL and API base URL",
      required_fields: ["QLANALYSER_CLOUD_FRONTEND_URL", "QLANALYSER_CLOUD_API_BASE_URL"],
      evidence_after_input: [
        paths.cloud_preflight,
        "work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-cloud-upload-to-export/browser_upload_to_export.json",
        "work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-cloud-acceptance-run/acceptance_run.json",
      ],
      current_blockers: cloudPreflight?.failed || ["cloud target not checked"],
      command_after_input: "node scripts/run_epilepsy_cloud_trial_acceptance.mjs",
    },
    {
      owner: "Owner/data steward",
      input: "Authorized anonymized EEG input_manifest.json",
      required_fields: [
        "owner_confirmed_authorized=true",
        "owner",
        "authorization_note",
        "datasets[].path",
        "datasets[].anonymized=true",
        "datasets[].contains_phi=false",
        "datasets[].data_preparation_required=true",
        "datasets[].data_preparation_dependency='qc'",
        "datasets[].allowed_methods subset of 8 formal methods",
      ],
      allowed_methods: ["psd", "erp", "tfr", "multitaper_psd", "multitaper_tfr", "reference_csd", "pac", "connectivity"],
      forbidden_allowed_methods: ["qc"],
      template_path: paths.owner_manifest_template,
      checklist_path: paths.owner_input_checklist,
      evidence_after_input: [
        paths.owner_manifest_contract,
        "work/release_evidence/07-full-product-e2e-pdca/11_real_dataset_owner_review/02_regression/real_dataset_regression_run.json",
      ],
      current_blockers: ownerManifestContract?.blockers || ["owner manifest not checked"],
      command_after_input: "node scripts/validate_epilepsy_owner_data_manifest_v0_1.mjs && python -X utf8 scripts/run_real_dataset_regression_from_manifest.py",
    },
  ],
  existing_artifacts: Object.fromEntries(Object.entries(paths).map(([key, relPath]) => [key, { path: relPath, exists: exists(relPath) }])),
  next_human_actions: [
    "Cloud/deployment owner provides non-local frontend/API URLs and confirms /api/health is reachable.",
    "Owner/data steward fills input_manifest.json from the template and confirms anonymization/authorization.",
  ],
};

function renderMarkdown(data) {
  const lines = [
    "# QLanalyser Epilepsy-like Event Screening v0.1 - Owner Input Packet",
    "",
    `Generated: ${data.generated_at}`,
    "",
    "## Current Status",
    "",
    `- Internal local status: \`${data.current_status.internal_local_status}\``,
    `- Cloud trial RC status: \`${data.current_status.cloud_trial_rc_status}\``,
    `- External release status: \`${data.current_status.external_release_status}\``,
    "",
    "## Inputs Needed",
    "",
  ];
  for (const item of data.inputs_needed) {
    lines.push(`### ${item.owner}`);
    lines.push("");
    lines.push(`Needed: ${item.input}`);
    lines.push("");
    lines.push("Required fields:");
    for (const field of item.required_fields) lines.push(`- \`${field}\``);
    if (item.allowed_methods) {
      lines.push("");
      lines.push(`Allowed methods: \`${item.allowed_methods.join("`, `")}\``);
      lines.push("QC is required as data-preparation dependency, not as an analysis method.");
    }
    if (item.template_path) {
      lines.push("");
      lines.push(`Template: \`${item.template_path}\``);
      lines.push(`Checklist: \`${item.checklist_path}\``);
    }
    lines.push("");
    lines.push("Current blockers:");
    for (const blocker of item.current_blockers) lines.push(`- ${blocker}`);
    lines.push("");
    lines.push("Command after input:");
    lines.push("");
    lines.push("```powershell");
    lines.push(item.command_after_input);
    lines.push("```");
    lines.push("");
  }
  lines.push("## Boundary");
  lines.push("");
  lines.push("This v0.1 trial remains research-support only. It is not a diagnostic, treatment, or clinical triage product.");
  lines.push("");
  return `${lines.join("\n")}\n`;
}

fs.mkdirSync(OUT_DIR, { recursive: true });
fs.writeFileSync(JSON_OUT, `${JSON.stringify(packet, null, 2)}\n`, "utf8");
fs.writeFileSync(MD_OUT, renderMarkdown(packet), "utf8");
console.log(JSON.stringify({ status: "written", json: path.relative(ROOT, JSON_OUT), markdown: path.relative(ROOT, MD_OUT), inputs_needed: packet.inputs_needed.length }, null, 2));
