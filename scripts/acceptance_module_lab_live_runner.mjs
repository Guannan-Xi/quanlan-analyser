import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { chromium } = require("../frontend/node_modules/playwright");

const FRONTEND_URL = process.env.QLANALYSER_FRONTEND_URL || "http://127.0.0.1:4174/module-lab.html?api=http://127.0.0.1:8001/api&acceptance=customer-file-runner-6";
const SAMPLE_FIF = process.env.QLANALYSER_UI_SAMPLE || path.resolve("work/acceptance/ui_with_events_raw.fif");
const EVIDENCE_PATH = process.env.QLANALYSER_MODULE_LAB_LIVE_EVIDENCE || path.resolve("work/release_evidence/20260620-module-lab-live-runner/module_lab_live_runner.json");
const SCREENSHOT_PATH = process.env.QLANALYSER_MODULE_LAB_LIVE_SCREENSHOT || path.resolve("work/release_evidence/20260620-module-lab-live-runner/module_lab_live_runner_all.png");
const MODULE_SCOPE = process.env.QLANALYSER_MODULE_LAB_SCOPE || "p0";

const ALL_MODULE_RUNS = [
  {
    id: "qc",
    workflow: "metadata_qc",
    fields: ["min_sampling_rate_hz", "min_duration_sec", "bad_channel_limit"],
    setParameters: async (page) => {
      await page.locator('[data-runner-form="qc"] input[name="min_sampling_rate_hz"]').fill("100");
      await page.locator('[data-runner-form="qc"] input[name="min_duration_sec"]').fill("5");
      await page.locator('[data-runner-form="qc"] input[name="bad_channel_limit"]').fill("2");
    },
    expectParameters: ["min_sampling_rate_hz", "min_duration_sec", "bad_channel_limit"],
  },
  {
    id: "psd",
    workflow: "resting_psd",
    responseWaitMs: 120000,
    fields: ["fmin", "fmax", "include_channel_table"],
    setParameters: async (page) => {
      await page.locator('[data-runner-form="psd"] input[name="fmin"]').fill("2");
      await page.locator('[data-runner-form="psd"] input[name="fmax"]').fill("35");
    },
    expectParameters: ['"fmin":2', '"fmax":35'],
  },
  {
    id: "erp",
    workflow: "erp_p300",
    responseWaitMs: 120000,
    fields: ["event_standard", "event_target", "tmin", "tmax", "baseline_start", "baseline_end"],
    setParameters: async (page) => {
      await page.locator('[data-runner-form="erp"] input[name="event_standard"]').fill("1");
      await page.locator('[data-runner-form="erp"] input[name="event_target"]').fill("2");
      await page.locator('[data-runner-form="erp"] input[name="tmin"]').fill("-0.2");
      await page.locator('[data-runner-form="erp"] input[name="tmax"]').fill("0.8");
      await page.locator('[data-runner-form="erp"] input[name="baseline_start"]').fill("-0.2");
      await page.locator('[data-runner-form="erp"] input[name="baseline_end"]').fill("0");
    },
    expectParameters: ['"event_id"', '"target"', '"standard"', '"tmin":-0.2', '"tmax":0.8'],
  },
  {
    id: "tfr",
    workflow: "tfr_ersp_itc",
    fields: ["event_id", "tmin", "tmax", "baseline", "freqs", "n_cycles", "decim", "return_itc"],
    artifactWaitMs: 180000,
    responseWaitMs: 180000,
    setParameters: async (page) => {
      await page.locator('[data-runner-form="tfr"] input[name="event_id"]').fill("");
      await page.locator('[data-runner-form="tfr"] input[name="tmin"]').fill("-0.2");
      await page.locator('[data-runner-form="tfr"] input[name="tmax"]').fill("0.8");
      await page.locator('[data-runner-form="tfr"] input[name="baseline"]').fill("-0.2,0");
      await page.locator('[data-runner-form="tfr"] input[name="freqs"]').fill("8,13,30");
      await page.locator('[data-runner-form="tfr"] input[name="n_cycles"]').fill("3");
      await page.locator('[data-runner-form="tfr"] input[name="decim"]').fill("2");
      await page.locator('[data-runner-form="tfr"] input[name="return_itc"]').check();
    },
    expectParameters: ['"freqs":[8,13,30]', '"n_cycles":3', '"decim":2', '"return_itc":true'],
  },
  {
    id: "pac",
    workflow: "pac_cfc",
    fields: ["channels", "phase_freqs", "amp_freqs", "n_phase_bins", "dynamic_window_sec"],
    setParameters: async (page) => {
      await page.locator('[data-runner-form="pac"] input[name="channels"]').fill("Cz,Pz");
      await page.locator('[data-runner-form="pac"] input[name="phase_freqs"]').fill("4,6,8");
      await page.locator('[data-runner-form="pac"] input[name="phase_band_width"]').fill("2");
      await page.locator('[data-runner-form="pac"] input[name="amp_freqs"]').fill("30,50,70");
      await page.locator('[data-runner-form="pac"] input[name="amp_band_width"]').fill("20");
      await page.locator('[data-runner-form="pac"] input[name="n_phase_bins"]').fill("18");
      await page.locator('[data-runner-form="pac"] input[name="window_start_sec"]').fill("0");
      await page.locator('[data-runner-form="pac"] input[name="window_end_sec"]').fill("8");
      await page.locator('[data-runner-form="pac"] input[name="dynamic_window_sec"]').fill("4");
      await page.locator('[data-runner-form="pac"] input[name="dynamic_step_sec"]').fill("2");
    },
    expectParameters: ['"phase_freqs":[4,6,8]', '"amp_freqs":[30,50,70]', '"n_phase_bins":18', '"dynamic_window_sec":4'],
  },
  {
    id: "reference_csd",
    workflow: "reference_csd",
    fields: ["reference_mode", "preview_channels", "preview_start_sec", "preview_duration_sec", "csd_lambda2"],
    setParameters: async (page) => {
      await page.locator('[data-runner-form="reference_csd"] select[name="reference_mode"]').selectOption("average");
      await page.locator('[data-runner-form="reference_csd"] input[name="preview_channels"]').fill("Fz,Cz,Pz,Oz");
      await page.locator('[data-runner-form="reference_csd"] input[name="preview_start_sec"]').fill("0");
      await page.locator('[data-runner-form="reference_csd"] input[name="preview_duration_sec"]').fill("8");
      await page.locator('[data-runner-form="reference_csd"] input[name="csd_lambda2"]').fill("0.00001");
    },
    expectParameters: ['"reference_mode":"average"', '"preview"', '"duration_sec":8'],
  },
  {
    id: "multitaper_psd_tfr",
    workflow: "multitaper_psd_tfr",
    fields: ["analysis_family", "fmin", "fmax", "freqs", "n_cycles", "time_bandwidth", "decim", "return_itc"],
    artifactWaitMs: 180000,
    responseWaitMs: 180000,
    setParameters: async (page) => {
      await page.locator('[data-runner-form="multitaper_psd_tfr"] select[name="analysis_family"]').selectOption("tfr");
      await page.locator('[data-runner-form="multitaper_psd_tfr"] input[name="fmin"]').fill("1");
      await page.locator('[data-runner-form="multitaper_psd_tfr"] input[name="fmax"]').fill("40");
      await page.locator('[data-runner-form="multitaper_psd_tfr"] input[name="bandwidth"]').fill("4");
      await page.locator('[data-runner-form="multitaper_psd_tfr"] input[name="low_bias"]').check();
      await page.locator('[data-runner-form="multitaper_psd_tfr"] select[name="normalization"]').selectOption("length");
      await page.locator('[data-runner-form="multitaper_psd_tfr"] input[name="event_id"]').fill("");
      await page.locator('[data-runner-form="multitaper_psd_tfr"] input[name="tmin"]').fill("-0.2");
      await page.locator('[data-runner-form="multitaper_psd_tfr"] input[name="tmax"]').fill("0.8");
      await page.locator('[data-runner-form="multitaper_psd_tfr"] input[name="baseline"]').fill("-0.2,0");
      await page.locator('[data-runner-form="multitaper_psd_tfr"] input[name="freqs"]').fill("8,13,30");
      await page.locator('[data-runner-form="multitaper_psd_tfr"] input[name="n_cycles"]').fill("7");
      await page.locator('[data-runner-form="multitaper_psd_tfr"] input[name="time_bandwidth"]').fill("4");
      await page.locator('[data-runner-form="multitaper_psd_tfr"] input[name="decim"]').fill("1");
      await page.locator('[data-runner-form="multitaper_psd_tfr"] input[name="return_itc"]').check();
    },
    expectParameters: ['"analysis_family":"tfr"', '"freqs":[8,13,30]', '"n_cycles":7', '"time_bandwidth":4', '"decim":1', '"return_itc":true'],
  },
  {
    id: "connectivity",
    workflow: "connectivity",
    fields: ["method", "fmin", "fmax", "segment_length_sec", "edge_top_n"],
    setParameters: async (page) => {
      await page.locator('[data-runner-form="connectivity"] select[name="method"]').selectOption("correlation");
      await page.locator('[data-runner-form="connectivity"] input[name="fmin"]').fill("8");
      await page.locator('[data-runner-form="connectivity"] input[name="fmax"]').fill("12");
      await page.locator('[data-runner-form="connectivity"] input[name="segment_length_sec"]').fill("4");
      await page.locator('[data-runner-form="connectivity"] input[name="edge_top_n"]').fill("20");
    },
    expectParameters: ['"method":"correlation"', '"fmin":8', '"fmax":12', '"edge_top_n":20'],
  },
];

const MODULE_RUNS = MODULE_SCOPE === "all"
  ? ALL_MODULE_RUNS
  : ALL_MODULE_RUNS.filter((moduleSpec) => ["qc", "psd", "erp"].includes(moduleSpec.id));

function writeEvidence(payload) {
  fs.mkdirSync(path.dirname(EVIDENCE_PATH), { recursive: true });
  fs.mkdirSync(path.dirname(SCREENSHOT_PATH), { recursive: true });
  fs.writeFileSync(EVIDENCE_PATH, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
}

async function runModule(page, moduleSpec, selectedFileId) {
  const form = page.locator(`[data-runner-form="${moduleSpec.id}"]`);
  await form.waitFor({ timeout: 15000 });
  const checks = {
    hasForm: true,
    hasInputs: true,
    selectedFileId,
  };
  for (const field of moduleSpec.fields) {
    checks.hasInputs = checks.hasInputs && await form.locator(`[name="${field}"]`).count() === 1;
  }
  await form.locator('select[name="dataset"]').selectOption(selectedFileId);
  checks.customerFileSelected = await form.locator('select[name="dataset"]').inputValue() === selectedFileId;
  await moduleSpec.setParameters(page);
  const taskResponsePromise = page.waitForResponse((response) => response.url().endsWith("/api/tasks") && response.request().method() === "POST", { timeout: moduleSpec.responseWaitMs || 120000 });
  await form.locator('button[type="submit"]').click();
  const taskPayload = await (await taskResponsePromise).json();
  checks.createdTaskId = taskPayload.id;
  checks.taskUsesSelectedFile = taskPayload.input_file_id === selectedFileId;
  checks.workflow = taskPayload.workflow_id;
  checks.workflowMatches = taskPayload.workflow_id === moduleSpec.workflow;
  await page.waitForSelector(`[data-result="${moduleSpec.id}"] .artifact[href*="/artifacts/"]`, { timeout: moduleSpec.artifactWaitMs || 30000 });
  const resultText = await page.locator(`[data-result="${moduleSpec.id}"]`).innerText();
  checks.completed = resultText.includes("Task completed") && resultText.includes(moduleSpec.workflow);
  checks.parametersVisible = moduleSpec.expectParameters.every((needle) => resultText.includes(needle));
  checks.downloadLinks = await page.locator(`[data-result="${moduleSpec.id}"] .artifact[href*="/artifacts/"]`).count();
  checks.passed = checks.hasInputs
    && checks.customerFileSelected
    && checks.taskUsesSelectedFile
    && checks.workflowMatches
    && checks.completed
    && checks.parametersVisible
    && checks.downloadLinks > 0;
  return checks;
}

const evidence = {
  status: "failed",
  url: FRONTEND_URL,
  sampleFile: SAMPLE_FIF,
  moduleScope: MODULE_SCOPE,
  scopeBoundary: MODULE_SCOPE === "p0"
    ? "P0 production-goal matrix scope: QC/preprocessing, PSD/bandpower, and ERP/P300 only. Advanced beta module live runs remain covered by dedicated beta gates."
    : "All module-lab live runner scope, including beta/advanced modules.",
  screenshot: SCREENSHOT_PATH,
  checks: {},
  moduleChecks: {},
  requests: [],
  errors: [],
};

async function run() {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  page.on("request", (request) => {
    const url = request.url();
    if (url.includes("/api/lab/demo/run/") || url.includes("/api/eeg/upload") || url.includes("/api/tasks") || url.includes("/api/artifacts/")) {
      evidence.requests.push({ method: request.method(), url });
    }
  });
  page.on("pageerror", (error) => evidence.errors.push(error.message));
  page.on("console", (msg) => {
    if (msg.type() === "error" && !msg.text().includes("Failed to load resource")) evidence.errors.push(msg.text());
  });

  try {
    if (!fs.existsSync(SAMPLE_FIF)) throw new Error(`Missing sample EEG file: ${SAMPLE_FIF}`);
    await page.goto(FRONTEND_URL, { waitUntil: "networkidle" });
    await page.waitForSelector("#labEegFile", { timeout: 15000 });
    evidence.checks.dataPreparationSectionVisible = await page.locator(".data-preparation-workflow").count() === 1;
    evidence.checks.stableAnalysisSectionVisible = await page.locator(".p0-workflow").count() === 1;
    evidence.checks.betaSectionVisible = await page.locator(".beta-workflow").count() === 1;
    evidence.checks.qcSeparatedFromStableAnalysis = await page.locator(".data-preparation-workflow [data-runner-form='qc']").count() === 1
      && await page.locator(".p0-workflow [data-runner-form='qc']").count() === 0;
    evidence.checks.stableAnalysisContainsPsdErp = await page.locator(".p0-workflow [data-runner-form='psd']").count() === 1
      && await page.locator(".p0-workflow [data-runner-form='erp']").count() === 1;
    evidence.checks.betaLabSeparated = await page.locator(".beta-workflow [data-runner-form='pac']").count() === 1
      && await page.locator(".beta-workflow [data-runner-form='connectivity']").count() === 1;
    await page.locator("#labEegFile").setInputFiles(SAMPLE_FIF);
    const uploadResponse = page.waitForResponse((response) => response.url().includes("/api/eeg/upload") && response.request().method() === "POST", { timeout: 30000 });
    await page.locator("#labUploadButton").click();
    const uploaded = await (await uploadResponse).json();
    evidence.checks.uploadedFileId = uploaded.id;
    await page.waitForFunction(() => !document.querySelector("#labUploadButton")?.disabled, null, { timeout: 10000 });
    await page.waitForFunction(() => Boolean(document.querySelector('[data-runner-form="psd"] select[name="dataset"]')?.value), null, { timeout: 10000 });
    const selectedFileId = await page.locator('[data-runner-form="psd"] select[name="dataset"]').inputValue();
    evidence.checks.selectedFileId = selectedFileId;
    evidence.checks.customerFileSelected = Boolean(selectedFileId);
    evidence.checks.uploadedFileSelected = selectedFileId === uploaded.id;

    for (const moduleSpec of MODULE_RUNS) {
      evidence.moduleChecks[moduleSpec.id] = await runModule(page, moduleSpec, selectedFileId);
    }

    await page.screenshot({ path: SCREENSHOT_PATH, fullPage: true });
    const postUploadCount = evidence.requests.filter((item) => item.method === "POST" && item.url.includes("/api/eeg/upload")).length;
    const postTaskCount = evidence.requests.filter((item) => item.method === "POST" && item.url.endsWith("/api/tasks")).length;
    evidence.checks.singleUpload = postUploadCount === 1;
    evidence.checks.taskPostCount = postTaskCount;
    evidence.status = evidence.checks.uploadedFileId
      && evidence.checks.customerFileSelected
      && evidence.checks.uploadedFileSelected
      && evidence.checks.singleUpload
      && evidence.checks.dataPreparationSectionVisible
      && evidence.checks.stableAnalysisSectionVisible
      && evidence.checks.betaSectionVisible
      && evidence.checks.qcSeparatedFromStableAnalysis
      && evidence.checks.stableAnalysisContainsPsdErp
      && evidence.checks.betaLabSeparated
      && postTaskCount === MODULE_RUNS.length
      && MODULE_RUNS.every((moduleSpec) => evidence.moduleChecks[moduleSpec.id]?.passed)
      && evidence.errors.length === 0 ? "passed" : "failed";
  } catch (error) {
    evidence.errors.push(error.message);
    try {
      await page.screenshot({ path: SCREENSHOT_PATH, fullPage: true });
    } catch (_) {}
  } finally {
    await browser.close();
    writeEvidence(evidence);
  }

  console.log(JSON.stringify(evidence, null, 2));
  if (evidence.status !== "passed") process.exit(1);
}

run();
