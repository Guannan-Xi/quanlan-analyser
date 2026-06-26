import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { chromium } = require("../frontend/node_modules/playwright");

const FRONTEND_URL = process.env.QLANALYSER_FRONTEND_URL || "http://127.0.0.1:4174/module-lab.html?api=http://127.0.0.1:8001/api&acceptance=grouped-methods-e2e";
const SAMPLE_EDF = process.env.QLANALYSER_GROUPED_METHODS_EDF || path.resolve("work/release_evidence/20260625-module-lab-grouped-methods-e2e/module_lab_grouped_methods_local.edf");
const EVIDENCE_DIR = path.resolve("work/release_evidence/20260625-module-lab-grouped-methods-e2e");
const EVIDENCE_PATH = process.env.QLANALYSER_GROUPED_METHODS_EVIDENCE || path.join(EVIDENCE_DIR, "module_lab_grouped_methods_e2e.json");
const SCREENSHOT_PATH = process.env.QLANALYSER_GROUPED_METHODS_SCREENSHOT || path.join(EVIDENCE_DIR, "module_lab_grouped_methods_e2e.png");

const MODULE_RUNS = [
  {
    id: "psd",
    group: "stationary-spectral-power",
    workflow: "resting_psd",
    taskModuleName: "psd",
    fields: ["fmin", "fmax", "n_fft", "n_overlap", "bad_channels", "reject_by_annotation", "include_channel_table"],
    setParameters: async (page) => {
      await page.locator('[data-runner-form="psd"] input[name="fmin"]').fill("2");
      await page.locator('[data-runner-form="psd"] input[name="fmax"]').fill("35");
      await page.locator('[data-runner-form="psd"] input[name="n_fft"]').fill("256");
      await page.locator('[data-runner-form="psd"] input[name="n_overlap"]').fill("64");
      await page.locator('[data-runner-form="psd"] input[name="bad_channels"]').fill("Oz");
      await page.locator('[data-runner-form="psd"] input[name="reject_by_annotation"]').check();
    },
    expectParameters: ['"fmin":2', '"fmax":35', '"n_fft":256', '"n_overlap":64', '"bad_channels":["Oz"]', '"reject_by_annotation":true'],
  },
  {
    id: "band_power",
    group: "stationary-spectral-power",
    workflow: "resting_psd",
    taskModuleName: "psd",
    fields: ["fmin", "fmax", "bad_channels", "reject_by_annotation", "include_channel_table"],
    setParameters: async (page) => {
      await page.locator('[data-runner-form="band_power"] input[name="fmin"]').fill("1");
      await page.locator('[data-runner-form="band_power"] input[name="fmax"]').fill("40");
      await page.locator('[data-runner-form="band_power"] input[name="bad_channels"]').fill("Oz");
      await page.locator('[data-runner-form="band_power"] input[name="reject_by_annotation"]').check();
      await page.locator('[data-runner-form="band_power"] input[name="include_channel_table"]').check();
    },
    expectParameters: ['"display_alias":"Band Power"', '"band_power_view":true', '"fmin":1', '"fmax":40', '"bad_channels":["Oz"]', '"include_channel_table":true'],
  },
  {
    id: "tfr",
    group: "event-locked-time-frequency",
    workflow: "tfr_ersp_itc",
    taskModuleName: "tfr",
    fields: ["event_id", "tmin", "tmax", "baseline", "freqs", "n_cycles", "decim", "return_itc", "picks", "average"],
    responseWaitMs: 180000,
    artifactWaitMs: 180000,
    setParameters: async (page) => {
      await page.locator('[data-runner-form="tfr"] input[name="event_id"]').fill("");
      await page.locator('[data-runner-form="tfr"] input[name="tmin"]').fill("-0.2");
      await page.locator('[data-runner-form="tfr"] input[name="tmax"]').fill("0.8");
      await page.locator('[data-runner-form="tfr"] input[name="baseline"]').fill("-0.2,0");
      await page.locator('[data-runner-form="tfr"] input[name="freqs"]').fill("8,13,30");
      await page.locator('[data-runner-form="tfr"] input[name="n_cycles"]').fill("3");
      await page.locator('[data-runner-form="tfr"] input[name="decim"]').fill("2");
      await page.locator('[data-runner-form="tfr"] input[name="return_itc"]').check();
      await page.locator('[data-runner-form="tfr"] input[name="picks"]').fill("Cz,Pz");
      await page.locator('[data-runner-form="tfr"] input[name="average"]').check();
    },
    expectParameters: ['"freqs":[8,13,30]', '"n_cycles":3', '"decim":2', '"return_itc":true', '"picks":["Cz","Pz"]', '"average":true'],
  },
  {
    id: "multitaper_psd",
    group: "multitaper-spectral-power",
    workflow: "multitaper_psd_tfr",
    taskModuleName: "multitaper_psd_tfr",
    fields: ["fmin", "fmax", "bandwidth", "low_bias", "normalization", "remove_dc", "bad_channels", "picks"],
    responseWaitMs: 180000,
    artifactWaitMs: 180000,
    setParameters: async (page) => {
      await page.locator('[data-runner-form="multitaper_psd"] input[name="fmin"]').fill("1");
      await page.locator('[data-runner-form="multitaper_psd"] input[name="fmax"]').fill("40");
      await page.locator('[data-runner-form="multitaper_psd"] input[name="bandwidth"]').fill("4");
      await page.locator('[data-runner-form="multitaper_psd"] input[name="low_bias"]').check();
      await page.locator('[data-runner-form="multitaper_psd"] select[name="normalization"]').selectOption("length");
      await page.locator('[data-runner-form="multitaper_psd"] input[name="remove_dc"]').check();
      await page.locator('[data-runner-form="multitaper_psd"] input[name="bad_channels"]').fill("Oz");
      await page.locator('[data-runner-form="multitaper_psd"] input[name="picks"]').fill("Cz,Pz");
    },
    expectParameters: ['"analysis_family":"psd"', '"fmin":1', '"fmax":40', '"bandwidth":4', '"remove_dc":true', '"bad_channels":["Oz"]', '"picks":["Cz","Pz"]'],
  },
  {
    id: "multitaper_tfr",
    group: "multitaper-time-frequency",
    workflow: "multitaper_psd_tfr",
    taskModuleName: "multitaper_psd_tfr",
    fields: ["event_id", "freqs", "n_cycles", "time_bandwidth", "decim", "return_itc", "bad_channels", "picks", "baseline_mode", "use_fft", "zero_mean"],
    responseWaitMs: 180000,
    artifactWaitMs: 180000,
    setParameters: async (page) => {
      await page.locator('[data-runner-form="multitaper_tfr"] input[name="event_id"]').fill("");
      await page.locator('[data-runner-form="multitaper_tfr"] input[name="tmin"]').fill("-0.2");
      await page.locator('[data-runner-form="multitaper_tfr"] input[name="tmax"]').fill("0.8");
      await page.locator('[data-runner-form="multitaper_tfr"] input[name="baseline"]').fill("-0.2,0");
      await page.locator('[data-runner-form="multitaper_tfr"] select[name="baseline_mode"]').selectOption("logratio");
      await page.locator('[data-runner-form="multitaper_tfr"] input[name="freqs"]').fill("8,13,30");
      await page.locator('[data-runner-form="multitaper_tfr"] input[name="n_cycles"]').fill("7");
      await page.locator('[data-runner-form="multitaper_tfr"] input[name="time_bandwidth"]').fill("4");
      await page.locator('[data-runner-form="multitaper_tfr"] input[name="decim"]').fill("1");
      await page.locator('[data-runner-form="multitaper_tfr"] input[name="return_itc"]').check();
      await page.locator('[data-runner-form="multitaper_tfr"] input[name="use_fft"]').check();
      await page.locator('[data-runner-form="multitaper_tfr"] input[name="zero_mean"]').check();
      await page.locator('[data-runner-form="multitaper_tfr"] input[name="bad_channels"]').fill("Oz");
      await page.locator('[data-runner-form="multitaper_tfr"] input[name="picks"]').fill("Cz,Pz");
    },
    expectParameters: ['"analysis_family":"tfr"', '"freqs":[8,13,30]', '"n_cycles":7', '"time_bandwidth":4', '"bad_channels":["Oz"]', '"picks":["Cz","Pz"]', '"baseline_mode":"logratio"', '"use_fft":true', '"zero_mean":true'],
  },
  {
    id: "erp",
    group: "event-locked-time-domain",
    workflow: "erp_p300",
    taskModuleName: "erp",
    fields: ["event_standard", "event_target", "tmin", "tmax", "baseline_start", "baseline_end", "reference_mode", "reject_by_annotation", "reject_eeg_uv", "bad_channels", "roi_channels"],
    responseWaitMs: 120000,
    setParameters: async (page) => {
      await page.locator('[data-runner-form="erp"] input[name="event_standard"]').fill("1");
      await page.locator('[data-runner-form="erp"] input[name="event_target"]').fill("2");
      await page.locator('[data-runner-form="erp"] input[name="tmin"]').fill("-0.2");
      await page.locator('[data-runner-form="erp"] input[name="tmax"]').fill("0.8");
      await page.locator('[data-runner-form="erp"] input[name="baseline_start"]').fill("-0.2");
      await page.locator('[data-runner-form="erp"] input[name="baseline_end"]').fill("0");
      await page.locator('[data-runner-form="erp"] select[name="reference_mode"]').selectOption("average");
      await page.locator('[data-runner-form="erp"] input[name="reject_by_annotation"]').check();
      await page.locator('[data-runner-form="erp"] input[name="reject_eeg_uv"]').fill("150");
      await page.locator('[data-runner-form="erp"] input[name="bad_channels"]').fill("Oz");
      await page.locator('[data-runner-form="erp"] input[name="roi_channels"]').fill("Pz,P3,P4");
    },
    expectParameters: ['"event_id"', '"target"', '"standard"', '"tmin":-0.2', '"tmax":0.8', '"reference":"average"', '"reject_by_annotation":true', '"reject_eeg_uv":150', '"bad_channels":["Oz"]', '"roi_channels":["Pz","P3","P4"]'],
  },
  {
    id: "epilepsy_std",
    group: "event-screening-research",
    workflow: "epilepsy_std_threshold",
    taskModuleName: "epilepsy",
    fields: ["eeg_channel", "epoch_length_sec", "std_factor", "rms_window_samples", "merge_gap_epoch_num", "min_event_epochs", "event_window_sec", "bad_channels"],
    responseWaitMs: 180000,
    artifactWaitMs: 180000,
    setParameters: async (page) => {
      await page.locator('[data-runner-form="epilepsy_std"] input[name="eeg_channel"]').fill("Fz");
      await page.locator('[data-runner-form="epilepsy_std"] input[name="epoch_length_sec"]').fill("5");
      await page.locator('[data-runner-form="epilepsy_std"] input[name="std_factor"]').fill("2");
      await page.locator('[data-runner-form="epilepsy_std"] input[name="rms_window_samples"]').fill("15");
      await page.locator('[data-runner-form="epilepsy_std"] input[name="merge_gap_epoch_num"]').fill("1");
      await page.locator('[data-runner-form="epilepsy_std"] input[name="min_event_epochs"]').fill("2");
      await page.locator('[data-runner-form="epilepsy_std"] input[name="event_window_sec"]').fill("1800");
      await page.locator('[data-runner-form="epilepsy_std"] input[name="bad_channels"]').fill("Oz");
    },
    expectParameters: ['"method":"std_threshold"', '"std_factor":2', '"min_event_epochs":2', '"bad_channels":["Oz"]', '"non_medical_boundary"'],
  },
  {
    id: "reference_csd",
    group: "csd-spatial-filter",
    workflow: "reference_csd",
    taskModuleName: "reference_csd",
    fields: ["reference_mode", "bad_channels", "bipolar_pairs", "preview_channels", "preview_start_sec", "preview_duration_sec", "csd_lambda2"],
    setParameters: async (page) => {
      await page.locator('[data-runner-form="reference_csd"] select[name="reference_mode"]').selectOption("average");
      await page.locator('[data-runner-form="reference_csd"] input[name="bad_channels"]').fill("O2");
      await page.locator('[data-runner-form="reference_csd"] input[name="bipolar_pairs"]').fill("Fz-Cz");
      await page.locator('[data-runner-form="reference_csd"] input[name="preview_channels"]').fill("Fz,Cz,Pz,Oz");
      await page.locator('[data-runner-form="reference_csd"] input[name="preview_start_sec"]').fill("0");
      await page.locator('[data-runner-form="reference_csd"] input[name="preview_duration_sec"]').fill("8");
      await page.locator('[data-runner-form="reference_csd"] input[name="csd_lambda2"]').fill("0.00001");
    },
    expectParameters: ['"reference_mode":"average"', '"bad_channels":["O2"]', '"bipolar_pairs":[{"anode":"Fz","cathode":"Cz","ch_name":"Fz-Cz"}]', '"preview"', '"duration_sec":8'],
  },
  {
    id: "pac",
    group: "cross-frequency-coupling",
    workflow: "pac_cfc",
    taskModuleName: "pac",
    fields: ["channels", "phase_freqs", "amp_freqs", "n_phase_bins", "dynamic_window_sec", "n_surrogates", "random_state", "filter_edge_padding_sec", "edge_trim_sec"],
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
      await page.locator('[data-runner-form="pac"] input[name="n_surrogates"]').fill("8");
      await page.locator('[data-runner-form="pac"] input[name="random_state"]').fill("12345");
      await page.locator('[data-runner-form="pac"] input[name="filter_edge_padding_sec"]').fill("2");
      await page.locator('[data-runner-form="pac"] input[name="edge_trim_sec"]').fill("0");
    },
    expectParameters: ['"phase_freqs":[4,6,8]', '"amp_freqs":[30,50,70]', '"n_phase_bins":18', '"n_surrogates":8', '"random_state":12345', '"filter_edge_padding_sec":2', '"edge_trim_sec":0'],
  },
  {
    id: "connectivity",
    group: "sensor-connectivity",
    workflow: "connectivity",
    taskModuleName: "connectivity",
    fields: ["method", "fmin", "fmax", "segment_length_sec", "edge_top_n", "reference"],
    setParameters: async (page) => {
      await page.locator('[data-runner-form="connectivity"] select[name="method"]').selectOption("correlation");
      await page.locator('[data-runner-form="connectivity"] input[name="fmin"]').fill("8");
      await page.locator('[data-runner-form="connectivity"] input[name="fmax"]').fill("12");
      await page.locator('[data-runner-form="connectivity"] input[name="segment_length_sec"]').fill("4");
      await page.locator('[data-runner-form="connectivity"] input[name="edge_top_n"]').fill("20");
      await page.locator('[data-runner-form="connectivity"] select[name="reference"]').selectOption("current_recording");
    },
    expectParameters: ['"method":"correlation"', '"fmin":8', '"fmax":12', '"edge_top_n":20', '"reference":"current_recording"'],
  },
];

const evidence = {
  status: "running",
  frontendUrl: FRONTEND_URL,
  sampleEdf: SAMPLE_EDF,
  startedAt: new Date().toISOString(),
  steps: [],
  requests: [],
  modules: {},
  errors: [],
};

function writeEvidence(payload) {
  fs.mkdirSync(EVIDENCE_DIR, { recursive: true });
  fs.writeFileSync(EVIDENCE_PATH, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
}

function localBrowserExecutable() {
  const candidates = [
    process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE,
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  ].filter(Boolean);
  return candidates.find((item) => fs.existsSync(item)) || "";
}

async function selectMethod(page, moduleSpec) {
  const switchButton = page.locator(`[data-method-switch="${moduleSpec.group}"][data-target-method="${moduleSpec.id}"]`);
  if (await switchButton.count()) {
    await switchButton.first().click();
  }
  const picker = page.locator(`[data-method-picker="${moduleSpec.group}"]`);
  if (await picker.count()) {
    await picker.waitFor({ timeout: 15000 });
    await picker.selectOption(moduleSpec.id);
  }
  await page.locator(`[data-method-panel="${moduleSpec.id}"]`).waitFor({ state: "visible", timeout: 15000 });
}

async function runModule(page, moduleSpec, selectedFileId) {
  evidence.steps.push({ action: "start-grouped-method", module: moduleSpec.id, group: moduleSpec.group, status: "running", startedAt: new Date().toISOString() });
  writeEvidence(evidence);
  await selectMethod(page, moduleSpec);
  const form = page.locator(`[data-runner-form="${moduleSpec.id}"]`);
  await form.waitFor({ state: "visible", timeout: 15000 });
  const checks = { selectedFileId, group: moduleSpec.group, hasForm: await form.count() === 1, formVisible: await form.isVisible(), hasInputs: true };
  for (const field of moduleSpec.fields) {
    checks.hasInputs = checks.hasInputs && await form.locator(`[name="${field}"]`).count() === 1;
  }
  await form.locator('select[name="dataset"]').selectOption(selectedFileId);
  checks.customerFileSelected = await form.locator('select[name="dataset"]').inputValue() === selectedFileId;
  await moduleSpec.setParameters(page);
  const taskResponsePromise = page.waitForResponse(
    (response) => response.url().endsWith("/api/tasks") && response.request().method() === "POST",
    { timeout: moduleSpec.responseWaitMs || 120000 },
  );
  await form.locator('button[type="submit"]').click();
  const taskPayload = await (await taskResponsePromise).json();
  checks.createdTaskId = taskPayload.id;
  checks.taskModuleName = taskPayload.module_name;
  checks.taskModuleNameMatches = taskPayload.module_name === moduleSpec.taskModuleName;
  checks.taskUsesSelectedFile = taskPayload.input_file_id === selectedFileId;
  checks.workflow = taskPayload.workflow_id;
  checks.workflowMatches = taskPayload.workflow_id === moduleSpec.workflow;
  await page.waitForSelector(`[data-result="${moduleSpec.id}"] .artifact[href*="/artifacts/"]`, { timeout: moduleSpec.artifactWaitMs || 45000 });
  await page.locator(`[data-result="${moduleSpec.id}"] details.param-echo`).evaluateAll((items) => {
    for (const item of items) item.open = true;
  });
  const resultText = await page.locator(`[data-result="${moduleSpec.id}"]`).evaluate((node) => node.textContent || "");
  const normalizedResultText = resultText.replace(/\s+/g, "");
  checks.completed = resultText.includes("分析完成") && resultText.includes(moduleSpec.workflow);
  checks.parametersVisible = moduleSpec.expectParameters.every((needle) => normalizedResultText.includes(needle.replace(/\s+/g, "")));
  checks.downloadLinks = await page.locator(`[data-result="${moduleSpec.id}"] .artifact[href*="/artifacts/"]`).count();
  checks.passed = checks.hasInputs
    && checks.customerFileSelected
    && checks.taskModuleNameMatches
    && checks.taskUsesSelectedFile
    && checks.workflowMatches
    && checks.completed
    && checks.parametersVisible
    && checks.downloadLinks > 0;
  evidence.modules[moduleSpec.id] = checks;
  evidence.steps.push({ action: "run-grouped-method", module: moduleSpec.id, group: moduleSpec.group, status: checks.passed ? "passed" : "failed", taskId: taskPayload.id, finishedAt: new Date().toISOString() });
  writeEvidence(evidence);
  if (!checks.passed) throw new Error(`Grouped method E2E failed for ${moduleSpec.id}: ${JSON.stringify(checks)}`);
}

async function run() {
  if (!fs.existsSync(SAMPLE_EDF)) throw new Error(`Missing generated EDF: ${SAMPLE_EDF}`);
  const executablePath = localBrowserExecutable();
  const browser = await chromium.launch(executablePath ? { executablePath } : {});
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  page.on("request", (request) => {
    const url = request.url();
    if (url.includes("/api/eeg/upload") || url.includes("/api/tasks") || url.includes("/api/artifacts/")) {
      evidence.requests.push({ method: request.method(), url });
    }
  });
  page.on("pageerror", (error) => evidence.errors.push(error.message));
  page.on("console", (msg) => {
    if (msg.type() === "error" && !msg.text().includes("Failed to load resource")) evidence.errors.push(msg.text());
  });

  try {
    await page.goto(FRONTEND_URL, { waitUntil: "networkidle", timeout: 60000 });
    await page.waitForSelector("[data-method-group]", { timeout: 20000 });
    const groupCount = await page.locator("[data-method-group]").count();
    const pickerCount = await page.locator("[data-method-picker]").count();
    const groupIds = await page.locator("[data-method-group]").evaluateAll((items) => items.map((item) => item.getAttribute("data-method-group")));
    const dataReadinessGroupVisible = groupIds.includes("data-readiness");
    evidence.steps.push({
      action: "load-grouped-ui",
      status: "passed",
      groupCount,
      pickerCount,
      groupIds,
      analysisMethodRunCount: MODULE_RUNS.length,
      dataReadinessGroupVisible,
      note: "Data readiness / QC is preparation UI and is not submitted as an analysis method in this E2E.",
    });
    writeEvidence(evidence);
    const expectedGroups = ["data-readiness", "stationary-spectral-power", "event-locked-time-domain", "event-screening-research", "event-locked-time-frequency", "multitaper-spectral-power", "multitaper-time-frequency", "csd-spatial-filter", "cross-frequency-coupling", "sensor-connectivity"];
    const missingGroups = expectedGroups.filter((id) => !groupIds.includes(id));
    if (groupCount !== expectedGroups.length || missingGroups.length) throw new Error(`Method taxonomy mismatch: ${JSON.stringify({ groupCount, groupIds, missingGroups })}`);
    if (!dataReadinessGroupVisible) throw new Error("Data readiness / QC preparation group should remain visible.");

    await page.locator("#labProjectName").fill("Grouped methods E2E local EDF");
    await page.setInputFiles("#labEegFile", SAMPLE_EDF);
    const uploadPromise = page.waitForResponse((response) => response.url().includes("/api/eeg/upload") && response.request().method() === "POST", { timeout: 120000 });
    await page.locator("#labUploadButton").click();
    const uploaded = await (await uploadPromise).json();
    const selectedFileId = uploaded.id;
    await page.waitForFunction((fileId) => Array.from(document.querySelectorAll("[data-file-select]")).every((select) => select.value === fileId), selectedFileId, { timeout: 30000 });
    evidence.uploadedFile = {
      id: selectedFileId,
      original_filename: uploaded.original_filename,
      detected_format: uploaded.detected_format,
      sampling_rate: uploaded.sampling_rate,
      channel_count: uploaded.channel_count,
      duration_sec: uploaded.duration_sec,
    };
    evidence.steps.push({ action: "upload-generated-edf", status: "passed", selectedFileId });
    writeEvidence(evidence);

    for (const moduleSpec of MODULE_RUNS) {
      await runModule(page, moduleSpec, selectedFileId);
    }

    await page.screenshot({ path: SCREENSHOT_PATH, fullPage: true });
    evidence.status = evidence.errors.length ? "failed" : "passed";
  } catch (error) {
    evidence.status = "failed";
    evidence.errors.push(error.message || String(error));
    try {
      await page.screenshot({ path: SCREENSHOT_PATH, fullPage: true });
    } catch (_) {}
  } finally {
    evidence.finishedAt = new Date().toISOString();
    await browser.close();
    writeEvidence(evidence);
  }

  console.log(JSON.stringify(evidence, null, 2));
  if (evidence.status !== "passed") process.exit(1);
}

run();
