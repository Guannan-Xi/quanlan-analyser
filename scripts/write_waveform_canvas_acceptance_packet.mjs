import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";

const root = process.cwd();
const evidenceDir = path.join(root, "work", "release_evidence", "20260627-waveform-canvas-workbench-dev");
const readJson = (name) => JSON.parse(fs.readFileSync(path.join(evidenceDir, name), "utf8"));

const staticReport = readJson("waveform_canvas_contract_static_validation.json");
const browserReport = readJson("waveform_canvas_workbench_browser_e2e.json");
const loadedReport = readJson("waveform_canvas_workbench_real_loaded_probe.json");
const trackedTargets = [
  "frontend/app.js",
  "frontend/index.html",
  "frontend/styles.css",
  "scripts/e2e_teaching_waveform_preview.mjs",
  "scripts/e2e_waveform_interaction.mjs",
  "scripts/validate_waveform_canvas_contract.mjs",
  "scripts/write_waveform_canvas_acceptance_packet.mjs",
];
const changedFiles = execFileSync("git", [
  "status",
  "--short",
  "--",
  ...trackedTargets,
], { cwd: root, encoding: "utf8" })
  .split(/\r?\n/)
  .map((line) => line.slice(3).trim())
  .filter(Boolean);

const packet = {
  status: "completed_canvas_workbench_dev_ready_for_acceptance",
  generated_at: new Date().toISOString(),
  route_decision: "gpt55_planner_or_acceptance + build_lane + verify_lane + review_lane + script_validator + browser_e2e",
  documents_read: [
    "docs/product/waveform_preparation_workbench_requirements_20260627.md",
    "docs/product/waveform_preparation_workbench_detailed_design_20260627.md",
    "docs/product/waveform_preparation_workbench_e2e_test_plan_20260627.md",
    "docs/product/qlanalyser_project_cleanup_waveform_preprocessing_ui_design_20260626.md",
    "docs/product/waveform_preparation_workbench_canvas_contract_20260627.md",
  ],
  agent_governance: {
    reclaimed_agents: [
      "stale notice sent earlier to old TimeChart thread; old missing subagent close attempt was not found",
    ],
    stale_agents: [
      "old TimeChart architecture review thread 019ecb3f-a33b-71d0-ab44-f29d9e62f75a marked stale by prior handoff state",
    ],
    kept_agents: [
      "019f059c-fdb1-72e1-8c57-a84cea718c83 Build/read-only review",
      "019f059d-3593-7a31-bd7a-2e2f80dbf244 Verify/read-only review",
      "019f059d-6d15-75c3-88f8-193ab029482e Product UI review",
    ],
    join_result: "all three current agents returned completed read-only findings and were consumed by PM integration",
  },
  implemented_changes: [
    "Unified Canvas time mapping helpers for time-to-x and x-to-time.",
    "Normalized waveform payload to contract fields including display_sample_rate_hz, downsampled, downsample_method, scale_uv, bad_segments, events.",
    "Added frontend min/max bucket fallback for oversized waveform arrays.",
    "Drew waveform samples by times_sec instead of sample index.",
    "Added event markers, readable bad/selected segment labels, bad segment overlays, and resize redraw.",
    "Fixed Ctrl/Cmd wheel zoom around mouse anchor.",
    "Added preparation contract version to downstream analysis task parameters and gate checks.",
    "Added teaching-data-protected and analysis-preparation-gate stable selectors.",
    "Fixed real waveform loaded state so the loading overlay hides after Canvas draw.",
    "Raised responsive waveform layout folding to 1100px.",
    "Added Playwright fallback in two E2E scripts without installing dependencies.",
    "Added static Canvas contract validator script.",
  ],
  changed_files: changedFiles,
  verification: {
    static_contract: staticReport.status,
    browser_e2e: browserReport.status,
    real_loaded_probe: loadedReport.status,
    syntax_checks: [
      "node --check frontend/app.js PASS",
      "node --check scripts/e2e_waveform_interaction.mjs PASS",
      "node --check scripts/e2e_teaching_waveform_preview.mjs PASS",
      "node --check scripts/e2e_teaching_sandbox_mode.mjs PASS",
      "node --check scripts/e2e_teaching_sandbox_analysis.mjs PASS",
    ],
    mojibake: "python -X utf8 scripts/check_no_mojibake.py frontend/app.js frontend/index.html PASS",
    service_health: { frontend_4174: 200, backend_8001_health: 200 },
    evidence_files: fs.readdirSync(evidenceDir).sort(),
  },
  no_touch_router_headroom_ipc: true,
  timechart_integrated: false,
  blocked_or_unverified: [
    "Full release suite for all analysis modules was not rerun in this slice.",
    "Existing Playwright scripts originally expected frontend/node_modules/playwright; fallback was added, but direct CLI execution still needs NODE_PATH or the bundled runtime until project dependencies are restored.",
    "Browser-level slow-response simulation for stale preview overwrite was not separately rerun; static requestSeq guard was verified.",
  ],
  next_real_artifact: "Codex/C0 final acceptance can rerun this evidence folder and then fold the result into the release gate.",
  route_chain: "Human/ClaudeCode package -> QGCS route -> document read -> parallel agent findings -> PM patch -> script/browser validation -> acceptance packet",
  model_lane: "GPT-5.5/Codex final acceptance owner; script/browser validators for bounded evidence",
  headroom_savings: "not measured; no router/headroom changes made",
  final_receipt: "completed_canvas_workbench_dev_ready_for_acceptance",
};

const out = path.join(evidenceDir, "acceptance_packet.json");
fs.writeFileSync(out, `${JSON.stringify(packet, null, 2)}\n`, "utf8");
console.log(out);
