import fs from "node:fs";
import path from "node:path";

const ROOT = process.cwd();
const EVIDENCE_ROOT = "work/release_evidence/07-full-product-e2e-pdca/11_real_dataset_owner_review";
const MANIFEST_PATH = process.env.QLANALYSER_OWNER_DATA_MANIFEST
  || path.join(EVIDENCE_ROOT, "input_manifest.json");
const TEMPLATE_PATH = path.join(EVIDENCE_ROOT, "input_manifest.template.json");
const OUT_DIR = path.resolve(ROOT, "work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-owner-data-manifest");
const OUT_FILE = path.join(OUT_DIR, "owner_data_manifest_contract.json");

const FORMAL_METHODS = new Set([
  "psd",
  "erp",
  "tfr",
  "multitaper_psd",
  "multitaper_tfr",
  "reference_csd",
  "pac",
  "connectivity",
]);
const EVENT_REQUIRED = new Set(["erp", "tfr", "multitaper_tfr", "pac"]);

function readJsonIfExists(relPath) {
  const absPath = path.resolve(ROOT, relPath);
  if (!fs.existsSync(absPath)) return null;
  return JSON.parse(fs.readFileSync(absPath, "utf8").replace(/^\uFEFF/, ""));
}

function boolValue(value) {
  return value === true || value === "true" || value === "yes";
}

function validateDataset(item = {}, index = 0) {
  const datasetId = String(item.dataset_id || `dataset_${index + 1}`);
  const blockers = [];
  const warnings = [];
  const allowedMethods = Array.isArray(item.allowed_methods) ? item.allowed_methods.map(String) : [];
  const unknownMethods = allowedMethods.filter((method) => !FORMAL_METHODS.has(method));
  const eventMethods = allowedMethods.filter((method) => EVENT_REQUIRED.has(method));

  if (!String(item.path || "").trim()) blockers.push("path is required");
  if (String(item.path || "").trim() && !fs.existsSync(path.resolve(ROOT, String(item.path)))) blockers.push("path does not exist");
  if (item.anonymized !== true) blockers.push("anonymized must be true");
  if (item.contains_phi !== false) blockers.push("contains_phi must be false");
  if (!allowedMethods.length) blockers.push("allowed_methods must be a non-empty array");
  if (allowedMethods.includes("qc")) blockers.push("qc must not be listed in allowed_methods; use data_preparation_dependency='qc'");
  if (unknownMethods.length) blockers.push(`unsupported allowed_methods: ${unknownMethods.join(", ")}`);
  if (item.data_preparation_required !== true) blockers.push("data_preparation_required must be true");
  if (item.data_preparation_dependency !== "qc") blockers.push("data_preparation_dependency must be 'qc'");
  if (eventMethods.length && !boolValue(item.event_markers_available)) {
    blockers.push(`event markers are required for methods: ${eventMethods.join(", ")}`);
  }
  if (allowedMethods.includes("reference_csd") && !boolValue(item.channel_location_available)) {
    warnings.push("reference_csd is allowed but channel_location_available is not true; owner should confirm montage/location assumptions");
  }

  return {
    dataset_id: datasetId,
    path_alias: path.basename(String(item.path || "")),
    allowed_methods: allowedMethods,
    event_methods: eventMethods,
    data_preparation_required: item.data_preparation_required,
    data_preparation_dependency: item.data_preparation_dependency,
    event_markers_available: item.event_markers_available,
    channel_location_available: item.channel_location_available,
    blockers,
    warnings,
    status: blockers.length ? "blocked" : "passed",
  };
}

const manifest = readJsonIfExists(MANIFEST_PATH);
const blockers = [];
const warnings = [];
let datasets = [];

if (!manifest) {
  blockers.push("input_manifest.json is missing");
} else {
  if (manifest.owner_confirmed_authorized !== true) blockers.push("owner_confirmed_authorized must be true");
  if (!String(manifest.owner || "").trim()) blockers.push("owner is required");
  if (!String(manifest.authorization_note || "").trim()) blockers.push("authorization_note is required");
  if (!Array.isArray(manifest.datasets) || !manifest.datasets.length) {
    blockers.push("datasets must contain at least one dataset");
  } else {
    datasets = manifest.datasets.map(validateDataset);
    for (const dataset of datasets) {
      blockers.push(...dataset.blockers.map((message) => `${dataset.dataset_id}: ${message}`));
      warnings.push(...dataset.warnings.map((message) => `${dataset.dataset_id}: ${message}`));
    }
  }
}

const result = {
  script: "validate_epilepsy_owner_data_manifest_v0_1.mjs",
  generated_at: new Date().toISOString(),
  status: blockers.length ? "blocked" : "passed",
  manifest_path: MANIFEST_PATH,
  template_path: TEMPLATE_PATH,
  exists: Boolean(manifest),
  contract: {
    allowed_methods: Array.from(FORMAL_METHODS),
    qc_policy: "QC is required as data_preparation_dependency='qc' and must not be listed in allowed_methods.",
    event_required_methods: Array.from(EVENT_REQUIRED),
    non_medical_scope: "research_screening_support_only",
  },
  datasets,
  blockers,
  warnings,
  next_command: blockers.length
    ? "Fill work/release_evidence/07-full-product-e2e-pdca/11_real_dataset_owner_review/input_manifest.json, then rerun this validator."
    : "python -X utf8 scripts/run_real_dataset_regression_from_manifest.py",
};

fs.mkdirSync(OUT_DIR, { recursive: true });
fs.writeFileSync(OUT_FILE, `${JSON.stringify(result, null, 2)}\n`, "utf8");
console.log(JSON.stringify(result, null, 2));
if (process.env.QLANALYSER_REQUIRE_OWNER_MANIFEST === "1" && result.status !== "passed") {
  process.exit(1);
}
