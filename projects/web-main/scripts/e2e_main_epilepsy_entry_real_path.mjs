import fs from "node:fs";
import path from "node:path";
import { chromium, chromiumLaunchOptions } from "./lib/playwright_runtime.mjs";

const API_BASE = process.env.QLANALYSER_API_BASE_URL || "http://127.0.0.1:8001/api";
const FRONTEND_URL = process.env.QLANALYSER_FRONTEND_URL
  || `http://127.0.0.1:4174/?customer_demo=auto&api=${encodeURIComponent(API_BASE)}&v=epilepsy-release-real-path#analysis`;
const OUT_DIR = process.env.QLANALYSER_EPILEPSY_REAL_PATH_EVIDENCE
  || path.resolve("work/release_evidence/20260629-epilepsy-release-e2e");
const EVIDENCE_PATH = path.join(OUT_DIR, "main_epilepsy_entry_real_path.json");

function writeEvidence(payload) {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  fs.writeFileSync(EVIDENCE_PATH, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
}

async function visibleEnabled(page, selector) {
  return page.evaluate((sel) => {
    const nodes = Array.from(document.querySelectorAll(sel));
    return nodes.map((el, index) => {
      const rect = el.getBoundingClientRect();
      const style = window.getComputedStyle(el);
      return {
        index,
        text: el.textContent?.replace(/\s+/g, " ").trim() || "",
        disabled: Boolean(el.disabled),
        ariaDisabled: el.getAttribute("aria-disabled"),
        visible: rect.width > 0 && rect.height > 0 && style.display !== "none" && style.visibility !== "hidden",
      };
    });
  }, selector);
}

async function clickFirstVisibleEnabled(page, selector, label) {
  const states = await visibleEnabled(page, selector);
  const target = states.find((item) => item.visible && !item.disabled && item.ariaDisabled !== "true");
  if (!target) throw new Error(`${label} is not visible/enabled: ${JSON.stringify(states)}`);
  await page.locator(selector).nth(target.index).click({ timeout: 15000 });
  return target;
}

async function waitForTaskCompleted(page, timeoutMs = 180000) {
  await page.waitForFunction(() => {
    const task = window.__QLANALYSER_EPILEPSY_E2E_TASK__ || window.__QLANALYSER_LAST_EPILEPSY_TASK__;
    const stateTask = window.__QLANALYSER_E2E_STATE__?.real?.tasks?.epilepsy_ml;
    return ["completed", "failed", "error"].includes(String(task?.status || "").toLowerCase())
      || ["completed", "failed", "error"].includes(String(stateTask?.status || "").toLowerCase());
  }, null, { timeout: timeoutMs });
}

function readArtifactText(artifacts, labelPattern) {
  const artifact = artifacts.find((item) => labelPattern.test(String(item.label || "")));
  if (!artifact?.path || !fs.existsSync(artifact.path)) return { artifact, text: "" };
  return { artifact, text: fs.readFileSync(artifact.path, "utf8") };
}

const evidence = {
  script: path.basename(new URL(import.meta.url).pathname),
  started_at: new Date().toISOString(),
  frontend_url: FRONTEND_URL,
  api_base: API_BASE,
  checks: {},
  steps: [],
  screenshots: {},
  errors: [],
  status: "running",
};

const browser = await chromium.launch(chromiumLaunchOptions({ headless: true }));
const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });
const taskRequests = [];
const reviewCreateRequests = [];
const reviewPatchRequests = [];
const reviewExportRequests = [];

page.on("request", (request) => {
  if (request.url().endsWith("/api/tasks") && request.method() === "POST") {
    taskRequests.push(request.postDataJSON?.() || {});
  }
  if (/\/api\/tasks\/[^/]+\/epilepsy-review-sessions$/.test(request.url()) && request.method() === "POST") {
    reviewCreateRequests.push(request.postDataJSON?.() || {});
  }
  if (/\/api\/epilepsy-review-sessions\/[^/]+$/.test(request.url()) && request.method() === "PATCH") {
    reviewPatchRequests.push(request.postDataJSON?.() || {});
  }
  if (/\/api\/epilepsy-review-sessions\/[^/]+\/exports$/.test(request.url()) && request.method() === "POST") {
    reviewExportRequests.push(request.postDataJSON?.() || {});
  }
});

try {
  const demo = await page.request.get(`${API_BASE}/lab/demo/epilepsy`, { timeout: 30000 }).then((res) => res.json());
  evidence.demo_fixture = {
    fixture_id: demo.fixture_id,
    project_id: demo.project?.id,
    file_id: demo.file?.id,
    filename: demo.file?.original_filename || demo.file?.filename,
    format: demo.file?.detected_format || demo.file?.format,
  };
  evidence.checks.epilepsy_edf_fixture_ready = demo.file?.id === "eeg_demo_epilepsy_high_amplitude";

  const plan = await page.request.post(`${API_BASE}/data-preparation/plans`, {
    data: {
      project_id: demo.project.id,
      input_file_id: demo.file.id,
      status: "confirmed",
      schema_version: "qlanalyser-data-preparation-v0.2",
      module_scope: ["qc", "psd", "erp", "epilepsy", "epilepsy_ml", "tfr", "pac", "reference_csd", "multitaper_psd_tfr", "connectivity"],
      title: "E2E epilepsy release candidate preparation plan",
      description: "Created by release E2E for synthetic epilepsy EDF fixture.",
      source_file: {
        file_id: demo.file.id,
        original_filename: demo.file.original_filename || demo.file.filename,
        detected_format: demo.file.detected_format || demo.file.format,
        sha256: demo.file.sha256,
      },
      metadata_review: {
        sampling_rate: demo.file.sampling_rate,
        channel_count: demo.file.channel_count,
        duration_sec: demo.file.duration_sec,
      },
      qc_json: {
        confirmed_from: "epilepsy_release_e2e",
        non_medical_boundary: "Synthetic research/demo data only; not for diagnosis.",
      },
      artifact_contract_json: {
        contract_version: "qlanalyser-data-preparation-v0.2",
        source_artifacts_readonly: true,
      },
    },
    timeout: 30000,
  }).then(async (res) => {
    if (!res.ok()) throw new Error(`Create data preparation plan failed: ${res.status()} ${await res.text()}`);
    return res.json();
  });
  evidence.backend_plan = { id: plan.id, revision: plan.revision, status: plan.status, schema_version: plan.schema_version };

  await page.goto(FRONTEND_URL, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForFunction(() => document.querySelector("#appShell") && !document.querySelector("#appShell").hidden, null, { timeout: 60000 });
  await page.waitForFunction(() => typeof window.__qlanalyserE2ESeedWorkspace === "function", null, { timeout: 60000 });
  await page.waitForTimeout(1500);
  evidence.seed_workspace = await page.evaluate(({ project, file, plan }) => {
    const seeded = window.__qlanalyserE2ESeedWorkspace({ project, file, plan });
    window.__QLANALYSER_E2E_STATE__ = window.__QLANALYSER_E2E_STATE__ || {};
    return seeded;
  }, { project: demo.project, file: demo.file, plan });
  await page.waitForTimeout(300);
  evidence.seed_state = await page.evaluate(() => ({
    activeView: document.querySelector(".view.active")?.id || "",
    plan: window.__QLANALYSER_E2E_STATE__?.real?.plan || null,
    file: window.__QLANALYSER_E2E_STATE__?.real?.eegFile || null,
    gate: document.querySelector('[data-testid="analysis-preparation-gate"]')?.textContent?.replace(/\s+/g, " ").trim() || "",
  }));

  await clickFirstVisibleEnabled(page, '[data-view-jump="workflow"], [data-view="workflow"]', "analysis tasks navigation");
  await page.waitForFunction(() => document.querySelector(".view.active")?.id === "workflow", null, { timeout: 60000 });
  evidence.checks.workflow_visible = true;

  evidence.screenshots.workflow = path.join(OUT_DIR, "01_workflow_epilepsy_card.png");
  await page.screenshot({ path: evidence.screenshots.workflow, fullPage: true });

  await clickFirstVisibleEnabled(page, '[data-testid="analysis-method-scope-panel"] [data-module-id="epilepsy_ml"]', "epilepsy analysis console");
  await page.waitForSelector('[data-testid="main-epilepsy-workbench-inline"].active', { timeout: 60000 });
  evidence.checks.inline_console_opened = true;
  evidence.checks.no_task_before_start = taskRequests.length === 0;

  evidence.screenshots.console_initial = path.join(OUT_DIR, "02_inline_console_initial.png");
  await page.screenshot({ path: evidence.screenshots.console_initial, fullPage: true });

  const taskResponsePromise = page.waitForResponse((response) => (
    response.url().endsWith("/api/tasks")
    && response.request().method() === "POST"
  ), { timeout: 240000 });
  await clickFirstVisibleEnabled(page, '[data-testid="inline-epilepsy-start-screening"]', "start epilepsy screening");
  await page.waitForTimeout(1000);
  evidence.after_start_click = await page.evaluate(() => {
    const button = document.querySelector('[data-testid="inline-epilepsy-start-screening"]');
    return {
      buttonText: button?.textContent?.replace(/\s+/g, " ").trim() || "",
      buttonDisabled: Boolean(button?.disabled),
      toast: document.querySelector("#toast")?.textContent?.replace(/\s+/g, " ").trim() || "",
      latestTask: window.__QLANALYSER_LAST_EPILEPSY_TASK__ || null,
      stateTask: window.__QLANALYSER_E2E_STATE__?.real?.tasks?.epilepsy_ml || null,
      activeView: document.querySelector(".view.active")?.id || "",
    };
  });
  await page.waitForFunction(() => {
    const task = window.__QLANALYSER_EPILEPSY_E2E_TASK__ || window.__QLANALYSER_LAST_EPILEPSY_TASK__;
    const stateTask = window.__QLANALYSER_E2E_STATE__?.real?.tasks?.epilepsy_ml;
    return Boolean(task?.id || stateTask?.id);
  }, null, { timeout: 5000 }).catch(() => {});
  if (!taskRequests.length && !evidence.after_start_click.latestTask?.id && !evidence.after_start_click.stateTask?.id) {
    throw new Error(`Start screening did not create a task: ${JSON.stringify(evidence.after_start_click)}`);
  }
  const taskResponse = await taskResponsePromise;
  let backendTask = null;
  try {
    backendTask = await taskResponse.json();
  } catch (error) {
    evidence.backend_task_response_json_fallback = error.message || String(error);
    backendTask = await page.evaluate(() => (
      window.__QLANALYSER_EPILEPSY_E2E_TASK__
      || window.__QLANALYSER_LAST_EPILEPSY_TASK__
      || window.__QLANALYSER_E2E_STATE__?.real?.tasks?.epilepsy_ml
      || null
    ));
  }
  if (!backendTask?.id) throw new Error(`Cannot resolve epilepsy task id after start: ${JSON.stringify(evidence.after_start_click)}`);
  evidence.backend_task_response = {
    id: backendTask.id,
    status: backendTask.status,
    queue_status: backendTask.queue_status,
    module_name: backendTask.module_name,
    workflow_id: backendTask.workflow_id,
    data_preparation_plan_id: backendTask.data_preparation_plan_id,
    data_preparation_revision: backendTask.data_preparation_revision,
    error_message: backendTask.error_message || null,
  };
  await waitForTaskCompleted(page, 10000).catch(() => {});

  const artifactResponse = await page.request.get(`${API_BASE}/tasks/${encodeURIComponent(backendTask.id)}/artifacts`, { timeout: 30000 });
  if (!artifactResponse.ok()) throw new Error(`Fetch artifacts failed: ${artifactResponse.status()} ${await artifactResponse.text()}`);
  const backendArtifacts = await artifactResponse.json();
  evidence.backend_artifacts = backendArtifacts.map((item) => ({
    id: item.id,
    label: item.label,
    path: item.path,
    size_bytes: item.size_bytes,
    sha256: item.sha256,
  }));
  const summaryRead = readArtifactText(backendArtifacts, /epilepsy_ml_summary|epilepsy_summary/);
  const epochRead = readArtifactText(backendArtifacts, /epilepsy_ml_epoch_predictions|epilepsy_epoch_scores/);
  const eventRead = readArtifactText(backendArtifacts, /epilepsy_ml_events|epilepsy_events/);
  const summaryJson = summaryRead.text ? JSON.parse(summaryRead.text) : {};
  const epochLines = epochRead.text.trim().split(/\r?\n/).filter(Boolean);
  const eventLines = eventRead.text.trim().split(/\r?\n/).filter(Boolean);
  evidence.algorithm_result_snapshot = {
    summary_artifact: summaryRead.artifact?.label || "",
    epoch_artifact: epochRead.artifact?.label || "",
    event_artifact: eventRead.artifact?.label || "",
    summary_keys: Object.keys(summaryJson).sort(),
    epoch_line_count: epochLines.length,
    event_line_count: eventLines.length,
    epoch_header: epochLines[0] || "",
    first_event: eventLines[1] || "",
    stage_code_hits: (epochRead.text.match(/,1,/g) || []).length,
  };

  await page.waitForFunction(() => {
    const inline = window.__QLANALYSER_E2E_STATE__?.epilepsyInline;
    const stageText = document.querySelector('[data-testid="inline-epilepsy-stage-strip"]')?.textContent || "";
    const eventText = document.querySelector('[data-testid="inline-epilepsy-events-panel"]')?.textContent || "";
    return inline?.resultLoadStatus === "ready"
      && Array.isArray(inline.epochRows)
      && inline.epochRows.length > 0
      && Array.isArray(inline.eventRows)
      && inline.eventRows.length > 0
      && !/运行初筛|等待/.test(stageText)
      && /候选事件 1|25\\.0|35\\.0|epoch/.test(eventText);
  }, null, { timeout: 30000 });

  await clickFirstVisibleEnabled(page, '[data-epilepsy-action="select-event"]', "select candidate event");
  await clickFirstVisibleEnabled(page, '[data-epilepsy-action="set-correction"][data-correction="Normal"]', "exclude candidate event");
  await page.waitForFunction(() => {
    const ledger = document.querySelector('[data-testid="inline-epilepsy-draft-ledger"]')?.textContent || "";
    return /排除候选|复核草稿\\s*1/.test(ledger);
  }, null, { timeout: 10000 });

  const reviewCreatePromise = page.waitForResponse((response) => (
    /\/api\/tasks\/[^/]+\/epilepsy-review-sessions$/.test(response.url())
    && response.request().method() === "POST"
  ), { timeout: 60000 });
  const reviewPatchPromise = page.waitForResponse((response) => (
    /\/api\/epilepsy-review-sessions\/[^/]+$/.test(response.url())
    && response.request().method() === "PATCH"
  ), { timeout: 60000 });
  await clickFirstVisibleEnabled(page, '[data-epilepsy-action="save-draft"]', "save review draft");
  const [reviewCreateResponse, reviewPatchResponse] = await Promise.all([reviewCreatePromise, reviewPatchPromise]);
  const reviewCreateJson = await reviewCreateResponse.json().catch(() => ({}));
  const reviewPatchJson = await reviewPatchResponse.json().catch(() => ({}));
  await page.waitForFunction(() => {
    const inline = window.__QLANALYSER_E2E_STATE__?.epilepsyInline;
    return inline?.draftSaved === true && inline?.reviewSession?.id;
  }, null, { timeout: 10000 });

  const reviewExportPromise = page.waitForResponse((response) => (
    /\/api\/epilepsy-review-sessions\/[^/]+\/exports$/.test(response.url())
    && response.request().method() === "POST"
  ), { timeout: 60000 });
  await clickFirstVisibleEnabled(page, '[data-epilepsy-action="publish-results"]', "publish review results");
  const reviewExportResponse = await reviewExportPromise;
  const reviewExportJson = await reviewExportResponse.json().catch(() => ({}));
  await page.waitForFunction(() => {
    const inline = window.__QLANALYSER_E2E_STATE__?.epilepsyInline;
    return inline?.exportStatus === "exported" && document.querySelector('[data-testid="inline-epilepsy-view-results"]');
  }, null, { timeout: 15000 });

  await clickFirstVisibleEnabled(page, '[data-testid="inline-epilepsy-view-results"]', "view review results");
  await page.waitForFunction(() => document.querySelector(".view.active")?.id === "statistics", null, { timeout: 15000 });
  await page.waitForFunction(() => {
    const result = document.querySelector('[data-result-module="epilepsy_ml"]');
    return Boolean(result) && /癫痫样|人工矫正|复核|候选事件|epoch/.test(result.textContent || "");
  }, null, { timeout: 15000 });

  const finalState = await page.evaluate(() => {
    const task = window.__QLANALYSER_EPILEPSY_E2E_TASK__ || window.__QLANALYSER_LAST_EPILEPSY_TASK__ || window.__QLANALYSER_E2E_STATE__?.real?.tasks?.epilepsy_ml || null;
    const artifacts = window.__QLANALYSER_E2E_STATE__?.real?.artifacts?.epilepsy_ml || [];
    const stageText = document.querySelector('[data-testid="inline-epilepsy-stage-strip"]')?.textContent?.replace(/\s+/g, " ").trim() || "";
    const eventText = document.querySelector('[data-testid="inline-epilepsy-events-panel"]')?.textContent?.replace(/\s+/g, " ").trim() || "";
    return {
      activeView: document.querySelector(".view.active")?.id || "",
      url: location.href,
      task,
      artifactLabels: artifacts.map((item) => item.label),
      resultLoadStatus: window.__QLANALYSER_E2E_STATE__?.epilepsyInline?.resultLoadStatus || "",
      epochRows: window.__QLANALYSER_E2E_STATE__?.epilepsyInline?.epochRows?.length || 0,
      eventRows: window.__QLANALYSER_E2E_STATE__?.epilepsyInline?.eventRows?.length || 0,
      stageText,
      eventText,
      waveformVisible: Boolean(document.querySelector('[data-testid="inline-epilepsy-waveform-canvas"]')),
      videoPanelCount: document.querySelectorAll('[data-testid="inline-epilepsy-video-panel"], [data-testid="inline-epilepsy-video-canvas"]').length,
      spectrogramVisible: Boolean(document.querySelector('[data-testid="inline-epilepsy-spectrogram-canvas"]')),
      reviewSession: window.__QLANALYSER_E2E_STATE__?.epilepsyInline?.reviewSession || null,
      draftSaved: Boolean(window.__QLANALYSER_E2E_STATE__?.epilepsyInline?.draftSaved),
      exportStatus: window.__QLANALYSER_E2E_STATE__?.epilepsyInline?.exportStatus || "",
      exportResult: window.__QLANALYSER_E2E_STATE__?.epilepsyInline?.exportResult || null,
      resultModuleText: document.querySelector('[data-result-module="epilepsy_ml"]')?.textContent?.replace(/\s+/g, " ").trim() || "",
    };
  });
  evidence.final_state = finalState;
  evidence.review_flow = {
    create_request: reviewCreateRequests[0] || null,
    patch_request: reviewPatchRequests[0] || null,
    export_request: reviewExportRequests[0] || null,
    create_response_id: reviewCreateJson.id || "",
    patch_response_status: reviewPatchJson.status || "",
    export_response: reviewExportJson,
  };

  const payload = taskRequests.find((item) => item.module_name === "epilepsy_ml") || {};
  evidence.captured_task_payload = payload;
  evidence.checks.task_payload_module = payload.module_name === "epilepsy_ml";
  evidence.checks.task_payload_workflow = payload.workflow_id === "epilepsy_ml_xgboost";
  evidence.checks.task_payload_preparation_contract =
    payload.parameters_json?.data_preparation_plan_id === plan.id
    && Number(payload.parameters_json?.data_preparation_revision) === Number(plan.revision)
    && payload.parameters_json?.data_preparation_contract_version === "qlanalyser-data-preparation-v0.2";
  evidence.checks.task_completed = backendTask.status === "completed";
  evidence.checks.ui_task_state_synced = finalState.task?.status === "completed";
  evidence.checks.algorithm_summary_valid = Boolean(summaryRead.text) && /epilepsy_ml|ml_epoch_classifier|computed|threshold/i.test(summaryRead.text);
  evidence.checks.epoch_predictions_have_stage_code = /Stage_Code/.test(evidence.algorithm_result_snapshot.epoch_header)
    && evidence.algorithm_result_snapshot.epoch_line_count > 1
    && evidence.algorithm_result_snapshot.stage_code_hits > 0;
  evidence.checks.events_csv_has_candidate = evidence.algorithm_result_snapshot.event_line_count > 1;
  evidence.checks.stage_code_visible = /0|1/.test(finalState.stageText) && !/运行初筛|等待/.test(finalState.stageText) && !/118|119|120|121|122|123|124|125|126|127|128|129/.test(finalState.stageText);
  evidence.checks.event_candidates_visible = /候选事件 1|25\\.0|35\\.0|epoch/.test(finalState.eventText) && !/0 个候选/.test(finalState.eventText);
  evidence.checks.waveform_stage_spectrogram_visible = finalState.waveformVisible && finalState.videoPanelCount === 0 && finalState.spectrogramVisible;
  evidence.checks.artifacts_registered = backendArtifacts.some((item) => /epilepsy.*(epoch|prediction)/.test(item.label))
    && backendArtifacts.some((item) => /epilepsy.*events/.test(item.label));
  evidence.checks.review_correction_saved = Boolean(finalState.draftSaved)
    && Boolean(finalState.reviewSession?.id)
    && Object.keys(evidence.review_flow.patch_request?.event_reviews || {}).length > 0
    && Object.keys(evidence.review_flow.patch_request?.epoch_overrides || {}).length > 0;
  evidence.checks.review_export_published = finalState.exportStatus === "exported"
    && Boolean(evidence.review_flow.export_response?.artifacts?.length || evidence.review_flow.export_response?.artifact_ids?.length || finalState.exportResult);
  evidence.checks.results_module_has_review_package = finalState.activeView === "statistics"
    && /癫痫样|人工矫正|复核|候选事件|epoch/.test(finalState.resultModuleText);

  evidence.screenshots.completed = path.join(OUT_DIR, "03_inline_console_completed.png");
  await page.screenshot({ path: evidence.screenshots.completed, fullPage: true });

  evidence.status = Object.values(evidence.checks).every(Boolean) ? "passed" : "failed";
} catch (error) {
  evidence.errors.push(error?.stack || error?.message || String(error));
  evidence.task_requests = taskRequests;
  evidence.failure_state = await page.evaluate(() => {
    const button = document.querySelector('[data-testid="inline-epilepsy-start-screening"]');
    return {
      buttonText: button?.textContent?.replace(/\s+/g, " ").trim() || "",
      buttonDisabled: Boolean(button?.disabled),
      toast: document.querySelector("#toast")?.textContent?.replace(/\s+/g, " ").trim() || "",
      latestTask: window.__QLANALYSER_LAST_EPILEPSY_TASK__ || null,
      stateTask: window.__QLANALYSER_E2E_STATE__?.real?.tasks?.epilepsy_ml || null,
      activeView: document.querySelector(".view.active")?.id || "",
    };
  }).catch(() => null);
  evidence.status = "failed";
  evidence.screenshots.failure = path.join(OUT_DIR, "failure.png");
  await page.screenshot({ path: evidence.screenshots.failure, fullPage: true }).catch(() => {});
} finally {
  evidence.finished_at = new Date().toISOString();
  writeEvidence(evidence);
  await browser.close().catch(() => {});
}

console.log(JSON.stringify(evidence, null, 2));
if (evidence.status !== "passed") process.exit(1);
