import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const evidenceDir = path.join(root, "work", "release_evidence", "20260628-epilepsy-sleep-staging-child-pages");
fs.mkdirSync(evidenceDir, { recursive: true });

const files = [
  "docs/product/epilepsy_sleep_staging_predev_adversarial_gate_20260628.md",
  "docs/product/epilepsy_sleep_waveform_staging_architecture_design_20260628.md",
  "docs/product/epilepsy_sleep_waveform_staging_requirements_20260628.md",
  "docs/product/epilepsy_sleep_waveform_staging_detailed_design_20260628.md",
  "docs/product/epilepsy_sleep_waveform_staging_e2e_acceptance_plan_20260628.md",
];

const requiredByFile = {
  "docs/product/epilepsy_sleep_staging_predev_adversarial_gate_20260628.md": [
    "G1 - Explicit State Machine",
    "G2 - Browse vs Correction Boundary",
    "G3 - Single Source of Truth",
    "G4 - No Primary Upload Path",
    "main navigation frame",
    "G5 - Demonstrable Waveform Interaction",
    "G6 - Results Backflow Honesty",
    "G7 - Sleep Release Claim Gate",
    "G8 - No Domain Bleed",
    "Current vs Target Reconciliation Gate",
    "control_state_matrix.json",
  ],
  "docs/product/epilepsy_sleep_waveform_staging_architecture_design_20260628.md": [
    "epilepsy_sleep_staging_predev_adversarial_gate_20260628.md",
    "state",
    "control",
    "main navigation frame",
    "Results-flow",
  ],
  "docs/product/epilepsy_sleep_waveform_staging_requirements_20260628.md": [
    "epilepsy_sleep_staging_predev_adversarial_gate_20260628.md",
    "duplicate",
    "visible control",
    "main navigation frame",
    "direct customer URL",
    "waveform interaction",
    "Results",
  ],
  "docs/product/epilepsy_sleep_waveform_staging_detailed_design_20260628.md": [
    "epilepsy_sleep_staging_predev_adversarial_gate_20260628.md",
    "control-state matrix",
    "Direct opening without `embed=1`",
    "main QLanalyser navigation frame",
    "Browse mode is read-only",
    "overview/timeline",
    "Results publish is honest",
    "Current vs Target Reconciliation",
    "hide_in_embed",
  ],
  "docs/product/epilepsy_sleep_waveform_staging_e2e_acceptance_plan_20260628.md": [
    "epilepsy_sleep_staging_predev_adversarial_gate_20260628.md",
    "GATE-01",
    "GATE-11",
    "GATE-12",
    "GATE-13",
    "Browse-mode",
    "Waveform interaction",
    "Domain bleed",
  ],
};

const result = {
  status: "passed",
  checked_at: new Date().toISOString(),
  files: [],
};

for (const rel of files) {
  const abs = path.join(root, rel);
  const entry = { file: rel, exists: fs.existsSync(abs), missing: [] };
  if (!entry.exists) {
    entry.missing = requiredByFile[rel] || [];
    result.status = "failed";
    result.files.push(entry);
    continue;
  }
  const text = fs.readFileSync(abs, "utf8");
  for (const needle of requiredByFile[rel] || []) {
    if (!text.includes(needle)) entry.missing.push(needle);
  }
  if (entry.missing.length) result.status = "failed";
  entry.characters = text.length;
  result.files.push(entry);
}

const outPath = path.join(evidenceDir, "predev_gate_validation.json");
fs.writeFileSync(outPath, JSON.stringify(result, null, 2), "utf8");

if (result.status !== "passed") {
  console.error(JSON.stringify(result, null, 2));
  process.exit(1);
}

console.log(JSON.stringify(result, null, 2));
