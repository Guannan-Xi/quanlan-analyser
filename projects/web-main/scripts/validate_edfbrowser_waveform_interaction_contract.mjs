import fs from "node:fs";
import path from "node:path";

const repoRoot = process.cwd();
const evidenceDir = process.env.QLANALYSER_EDFBROWSER_CONTRACT_DIR
  || path.join(repoRoot, "work", "release_evidence", "20260627-edfbrowser-waveform-interaction-dev");
fs.mkdirSync(evidenceDir, { recursive: true });

const files = {
  app: path.join(repoRoot, "frontend", "app.js"),
  html: path.join(repoRoot, "frontend", "index.html"),
  css: path.join(repoRoot, "frontend", "styles.css"),
};

const docs = [
  "docs/product/waveform_preparation_workbench_edfbrowser_interaction_requirements_20260627.md",
  "docs/product/waveform_preparation_workbench_edfbrowser_interaction_detailed_design_20260627.md",
  "docs/product/waveform_preparation_workbench_edfbrowser_interaction_e2e_test_plan_20260627.md",
  "docs/product/waveform_preparation_workbench_edfbrowser_interaction_dual_review_summary_20260627.md",
  "docs/product/waveform_preparation_workbench_canvas_contract_20260627.md",
];

const text = Object.fromEntries(
  Object.entries(files).map(([key, file]) => [key, fs.readFileSync(file, "utf8")]),
);

const docChecks = docs.map((relativePath) => {
  const abs = path.join(repoRoot, relativePath);
  const body = fs.readFileSync(abs, "utf8");
  return {
    path: relativePath,
    exists: true,
    utf8_read: body.length > 100,
  };
});

function includesAll(source, needles) {
  return needles.every((needle) => source.includes(needle));
}

const checks = [
  {
    id: "T-EDF-01",
    name: "ordinary wheel pans horizontally",
    passed: includesAll(text.app, ["wheelPanRatio: 0.08", "shiftEegWindow(direction, EDF_BROWSER_INTERACTION_CONSTANTS.wheelPanRatio"]),
  },
  {
    id: "T-EDF-02",
    name: "Ctrl/Cmd wheel zooms around cursor anchor",
    passed: includesAll(text.app, ["event.ctrlKey || event.metaKey", "canvasXToTime(event.clientX - rect.left, plot)", "zoomEegWindow(factor, anchorTime)", "maxWindowSec: 300"]),
  },
  {
    id: "T-EDF-02B",
    name: "time-window controls use the 300 s EDFBrowser ceiling",
    passed: includesAll(text.app, ["minWindowSec: 2", "maxWindowSec: 300", "clampEegWindowDuration"])
      && text.html.includes('id="eegWindowInput" type="range" min="2" max="300"'),
  },
  {
    id: "T-EDF-03",
    name: "PageUp/PageDown page by one window",
    passed: includesAll(text.app, ["key === \"PageUp\"", "key === \"PageDown\"", "pagePanRatio: 1.00"]),
  },
  {
    id: "T-EDF-04",
    name: "Left/Right pan by one tenth page",
    passed: includesAll(text.app, ["key === \"ArrowLeft\"", "key === \"ArrowRight\"", "arrowPanRatio: 0.10"]),
  },
  {
    id: "T-EDF-05",
    name: "middle button drag pans horizontally",
    passed: includesAll(text.app, ["event.button === 1", "eegState.middlePan", "deltaSec"]),
  },
  {
    id: "T-EDF-06",
    name: "browse mode left click does not write draft",
    passed: includesAll(text.app, ["eegState.interactionMode === \"browse\"", "左键不会写入草稿"]) && !text.app.includes("if (event.button !== 0) return;\n  const time = eegCanvasTimeFromEvent"),
  },
  {
    id: "T-EDF-07",
    name: "selectSegment mode writes UI draft",
    passed: includesAll(text.html, ["data-testid=\"waveform-mode-select-segment\"", "data-mode-target=\"selectSegment\""])
      && includesAll(text.app, ["setWaveformInteractionMode", "mode: eegState.interactionMode", "updateSelectedSegmentInputs"]),
  },
  {
    id: "T-EDF-08",
    name: "markBadSegment can be restored and audited as draft",
    passed: includesAll(text.html, ["data-testid=\"waveform-mode-mark-bad-segment\"", "data-ia-action=\"restore-segment\""])
      && includesAll(text.app, ["mode === \"markBadSegment\"", "handleIaAction(\"exclude-segment\")", "prepEditState.restoredSegments.push"]),
  },
  {
    id: "T-EDF-09",
    name: "amplitude and time zoom are separated",
    passed: includesAll(text.app, ["adjustEegAmplitudeSensitivity", "uV/row", "Ctrl/Cmd + 滚轮缩放时间窗"]),
  },
  {
    id: "T-EDF-10",
    name: "mode buttons and status bar contract exist",
    passed: includesAll(text.html, [
      "data-testid=\"waveform-mode-browse\"",
      "data-testid=\"waveform-mode-select-segment\"",
      "data-testid=\"waveform-mode-mark-bad-segment\"",
      "data-testid=\"waveform-mode-mark-bad-channel\"",
      "data-testid=\"waveform-status-bar\"",
      "data-mode=\"browse\"",
    ]) && includesAll(text.app, ["模式", "时间窗", "s/page", "ch", "uV/row", "Raw", "Filter"]),
  },
  {
    id: "T-EDF-11",
    name: "analysis preparation gate and payload contract",
    passed: includesAll(text.html + text.app, ["data-testid=\"analysis-preparation-gate\"", "data_preparation_plan_id", "data_preparation_revision", "data_preparation_contract_version", "DATA_PREPARATION_CONTRACT_VERSION"]),
  },
  {
    id: "T-EDF-12",
    name: "non-medical boundary and TimeChart exclusion",
    passed: (text.app.includes("不作为临床诊断依据") || text.app.includes("non_diagnostic"))
      && !text.app.includes("TimeChart")
      && !text.html.includes("TimeChart")
      && !text.css.includes("TimeChart"),
  },
];

const passed = checks.every((check) => check.passed) && docChecks.every((check) => check.exists && check.utf8_read);
const result = {
  status: passed ? "passed" : "failed",
  generated_at: new Date().toISOString(),
  docs: docChecks,
  checks,
  constants: {
    wheelPanRatio: 0.08,
    arrowPanRatio: 0.10,
    pagePanRatio: 1.00,
    zoomFactor: 1.20,
    maxWindowSec: 300,
    contractVersion: "qlanalyser-data-preparation-v0.2",
  },
  no_touch_scope: {
    timechart: true,
    router_headroom_gateway_ipc_model_route: true,
  },
};

const outputPath = path.join(evidenceDir, "edfbrowser_waveform_interaction_contract_validation.json");
fs.writeFileSync(outputPath, `${JSON.stringify(result, null, 2)}\n`, "utf8");
console.log(JSON.stringify({ status: result.status, outputPath, failed: checks.filter((check) => !check.passed).map((check) => check.id) }, null, 2));
if (!passed) process.exit(1);
