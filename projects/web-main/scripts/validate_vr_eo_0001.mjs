import fs from "node:fs";
import path from "node:path";

const evidencePath = process.argv[2];
if (!evidencePath) {
  console.error("Usage: node scripts/validate_vr_eo_0001.mjs <vr-itc-0001-runner-evidence.json>");
  process.exit(2);
}

const runner = JSON.parse(fs.readFileSync(evidencePath, "utf8"));
const inspect = runner.artifact_inspect || {};
const reportDownload = (runner.downloads || []).find((item) => item?.requirement === "report bundle");
const professionalChineseGatePath = path.resolve(
  path.dirname(evidencePath),
  "..",
  "professional_chinese_gate",
  "professional_chinese_gate.json",
);

function readProfessionalChineseGate() {
  if (!fs.existsSync(professionalChineseGatePath)) {
    return {
      status: "pending_next_copy_review",
      evidence: {
        gate: "QLANALYSER_PROFESSIONAL_CHINESE_READY",
        path: professionalChineseGatePath,
        detail: "Executable professional Chinese gate has not run for the current checkpoint.",
      },
    };
  }
  const payload = JSON.parse(fs.readFileSync(professionalChineseGatePath, "utf8"));
  return {
    status: payload.status === "passed" ? "pass" : "block",
    evidence: {
      gate: payload.gate || "QLANALYSER_PROFESSIONAL_CHINESE_READY",
      path: professionalChineseGatePath,
      status: payload.status,
      blockers: payload.blockers || [],
      generated_at: payload.generated_at,
    },
  };
}

const checks = {
  pdf_contains_method_summary: {
    status:
      inspect.report_pdf_present &&
      inspect.pdf_checks?.pdf_header &&
      inspect.pdf_checks?.text_extractable &&
      inspect.pdf_checks?.method_summary
        ? "pass"
        : "revise",
    evidence: inspect.pdf_checks || runner.gaps?.find((gap) => gap.includes("report.pdf")) || {},
  },
  json_contains_schema_version_parameters_processing_steps_warnings_timestamp: {
    status:
      inspect.json_checks?.schema_version &&
      inspect.json_checks?.parameters &&
      inspect.json_checks?.processing_steps &&
      inspect.json_checks?.software_or_workflow_reference &&
      inspect.json_checks?.timestamp &&
      (inspect.json_checks?.warnings_field || inspect.json_checks?.warnings_or_boundary)
        ? "pass"
        : "revise",
    evidence: inspect.json_checks || {},
  },
  csv_contains_units_and_channel_or_frequency_labels: {
    status:
      inspect.csv_checks?.table_dictionary_present &&
      inspect.csv_checks?.units_present &&
      inspect.csv_checks?.channel_or_frequency_labels &&
      ((inspect.csv_checks?.band_power_csv && inspect.csv_checks?.channel_band_power_csv) ||
        inspect.csv_checks?.erp_csv)
        ? "pass"
        : "revise",
    evidence: inspect.csv_checks || {},
  },
  all_artifacts_link_to_provenance_or_source_data: {
    status: inspect.json_checks?.source_metadata && inspect.json_checks?.workflow_json !== false ? "pass" : "revise",
    evidence: inspect.json_checks || {},
  },
  non_diagnostic_boundary_visible: {
    status: inspect.boundary_checks?.non_diagnostic_boundary ? "pass" : "revise",
    evidence: inspect.boundary_checks || {},
  },
  psd_topomap_scientific_boundary: {
    status:
      inspect.boundary_checks?.psd_sensor_space_boundary &&
      inspect.boundary_checks?.no_source_claim
        ? "pass"
        : "revise",
    evidence: inspect.boundary_checks || {},
  },
  chinese_editorial_gate: readProfessionalChineseGate(),
};

const blockers = [];
const warnings = [];
for (const [name, check] of Object.entries(checks)) {
  if (String(check.status).startsWith("not_applicable_missing_artifact")) warnings.push(name);
  else if (check.status !== "pass" && check.status !== "pending_next_copy_review") blockers.push(name);
}

const output = {
  protocol: "QLANALYSER_EXECUTABLE_VIRTUAL_REVIEWER_READY",
  requirement_id: "VR-EO-0001",
  source_runner_evidence: path.resolve(evidencePath),
  report_bundle: reportDownload?.path || runner.downloads?.[0]?.path || null,
  generated_at: new Date().toISOString(),
  checks,
  missing_expected_artifacts: runner.gaps || [],
  decision: blockers.length ? "block" : warnings.length ? "revise" : "pass",
  blockers,
  warnings,
  notes: [
    "Current product exports report.html plus ZIP with result.json, report.json, manifest JSON, CSV, SVG and reproducibility JSON.",
    "PDF presence, text extraction, method summary, JSON, CSV, and scientific boundary fields are checked against VR-EO-0001.",
    "No real participant data was used; fixture is synthetic software-test FIF.",
  ],
};

const outputPath = path.join(path.dirname(evidencePath), "vr-eo-0001-artifact-validator.json");
fs.writeFileSync(outputPath, `${JSON.stringify(output, null, 2)}\n`, "utf8");
console.log(JSON.stringify(output, null, 2));
