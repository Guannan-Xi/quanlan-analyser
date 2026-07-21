import fs from "node:fs";
import path from "node:path";
import { chromium, chromiumLaunchOptions } from "./lib/playwright_runtime.mjs";

const API_BASE = process.env.QLANALYSER_API_BASE_URL || "http://127.0.0.1:8001/api";
const FRONTEND_URL = process.env.QLANALYSER_FRONTEND_URL
  || `http://127.0.0.1:4174/?customer_demo=auto&api=${encodeURIComponent(API_BASE)}&v=epilepsy-upload-to-export-interaction#storage`;
const SAMPLE_EDF = process.env.QLANALYSER_EPILEPSY_SAMPLE_EDF
  || path.resolve("work/fixtures/epilepsy_regular_labeled/regular_epilepsy_labeled_60s.edf");

function isLocalUrl(rawUrl = "") {
  try {
    const url = new URL(rawUrl);
    return ["127.0.0.1", "localhost", "::1"].includes(url.hostname);
  } catch {
    return true;
  }
}

const OUT_DIR = process.env.QLANALYSER_EPILEPSY_UPLOAD_E2E_DIR
  || path.resolve(isLocalUrl(FRONTEND_URL)
    ? "work/release_evidence/20260629-epilepsy-cloud-trial-v0-1-browser-upload-to-export"
    : "work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-cloud-upload-to-export");
const EVIDENCE_PATH = path.join(OUT_DIR, "browser_upload_to_export.json");

function ensureDir() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
}

function writeEvidence(payload) {
  ensureDir();
  fs.writeFileSync(EVIDENCE_PATH, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
}

async function visibleEnabled(page, selector) {
  return page.evaluate((sel) => {
    return Array.from(document.querySelectorAll(sel)).map((el, index) => {
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

async function clickFirstVisibleEnabled(page, selector, label, timeout = 20000) {
  await page.waitForFunction((sel) => {
    return Array.from(document.querySelectorAll(sel)).some((el) => {
      const rect = el.getBoundingClientRect();
      const style = window.getComputedStyle(el);
      return rect.width > 0
        && rect.height > 0
        && style.display !== "none"
        && style.visibility !== "hidden"
        && !el.disabled
        && el.getAttribute("aria-disabled") !== "true";
    });
  }, selector, { timeout });
  const states = await visibleEnabled(page, selector);
  const target = states.find((item) => item.visible && !item.disabled && item.ariaDisabled !== "true");
  if (!target) throw new Error(`${label} is not visible/enabled: ${JSON.stringify(states)}`);
  try {
    await page.locator(selector).nth(target.index).click({ timeout });
  } catch (error) {
    await page.evaluate(({ sel, index }) => {
      const el = document.querySelectorAll(sel)[index];
      if (!el || el.disabled || el.getAttribute("aria-disabled") === "true") {
        throw new Error("fallback target is not enabled");
      }
      el.click();
    }, { sel: selector, index: target.index });
  }
  return target;
}

async function waitForResponseAfter(page, label, predicate, action, timeout = 90000) {
  const responsePromise = page.waitForResponse(predicate, { timeout });
  await action();
  const response = await responsePromise;
  if (!response.ok()) {
    const body = await response.text().catch(() => "");
    throw new Error(`${label} returned ${response.status()}: ${body.slice(0, 500)}`);
  }
  return response;
}

function taskRequestHasModule(response, moduleName) {
  if (!response.url().endsWith("/api/tasks") || response.request().method() !== "POST") return false;
  try {
    const payload = response.request().postDataJSON();
    return payload?.module_name === moduleName;
  } catch {
    return false;
  }
}

async function checkFirstVisible(page, selector, label, timeout = 20000) {
  await page.waitForFunction((sel) => {
    return Array.from(document.querySelectorAll(sel)).some((el) => {
      const rect = el.getBoundingClientRect();
      const style = window.getComputedStyle(el);
      return rect.width > 0 && rect.height > 0 && style.display !== "none" && style.visibility !== "hidden";
    });
  }, selector, { timeout });
  const checked = await page.evaluate((sel) => {
    const target = Array.from(document.querySelectorAll(sel)).find((el) => {
      const rect = el.getBoundingClientRect();
      const style = window.getComputedStyle(el);
      return rect.width > 0 && rect.height > 0 && style.display !== "none" && style.visibility !== "hidden";
    });
    if (!target) return false;
    target.checked = true;
    target.dispatchEvent(new Event("input", { bubbles: true }));
    target.dispatchEvent(new Event("change", { bubbles: true }));
    return Boolean(target.checked);
  }, selector);
  if (!checked) throw new Error(`${label} could not be checked`);
}

async function waitForTaskCompleted(page, timeoutMs = 240000) {
  await page.waitForFunction(() => {
    const task = window.__QLANALYSER_EPILEPSY_E2E_TASK__ || window.__QLANALYSER_LAST_EPILEPSY_TASK__;
    const stateTask = window.__QLANALYSER_E2E_STATE__?.real?.tasks?.epilepsy_ml;
    const candidates = [stateTask, task].filter((item) => item?.module_name === "epilepsy_ml");
    return candidates.some((item) => ["completed", "failed", "error"].includes(String(item?.status || "").toLowerCase()));
  }, null, { timeout: timeoutMs });
  return page.evaluate(() => {
    const stateTask = window.__QLANALYSER_E2E_STATE__?.real?.tasks?.epilepsy_ml;
    const task = window.__QLANALYSER_EPILEPSY_E2E_TASK__ || window.__QLANALYSER_LAST_EPILEPSY_TASK__;
    const candidates = [stateTask, task].filter((item) => item?.module_name === "epilepsy_ml");
    return candidates.find((item) => ["completed", "failed", "error"].includes(String(item?.status || "").toLowerCase()))
      || candidates[0]
      || null;
  });
}

async function authenticatedRequestOptions(page, options = {}) {
  const token = await page.evaluate(() => {
    const key = "qlanalyser_auth_session";
    try {
      const session = JSON.parse(localStorage.getItem(key) || sessionStorage.getItem(key) || "{}");
      return session.token || "";
    } catch {
      return "";
    }
  });
  if (!token) throw new Error("Authenticated browser session token is unavailable");
  return { ...options, headers: { ...(options.headers || {}), Authorization: `Bearer ${token}` } };
}

async function readArtifactText(page, artifacts, labelPattern) {
  const artifact = artifacts.find((item) => labelPattern.test(String(item.label || "")));
  if (!artifact) return { artifact: null, text: "" };
  if (artifact.path && fs.existsSync(artifact.path)) return { artifact, text: fs.readFileSync(artifact.path, "utf8") };
  const artifactId = artifact.artifact_id || artifact.id;
  if (!artifactId) return { artifact, text: "" };
  const response = await page.request.get(
    `${API_BASE}/artifacts/${encodeURIComponent(artifactId)}/download`,
    await authenticatedRequestOptions(page, { timeout: 60000 }),
  );
  if (!response.ok()) return { artifact, text: "" };
  return { artifact, text: await response.text() };
}

const evidence = {
  script: path.basename(new URL(import.meta.url).pathname),
  started_at: new Date().toISOString(),
  frontend_url: FRONTEND_URL,
  api_base: API_BASE,
  sample_edf: SAMPLE_EDF,
  checks: {},
  steps: [],
  screenshots: {},
  requests: {
    uploads: [],
    plans: [],
    tasks: [],
    review_creates: [],
    review_patches: [],
    review_exports: [],
  },
  errors: [],
  status: "running",
};

function textHasAny(text, patterns) {
  return patterns.some((pattern) => pattern.test(String(text || "")));
}

if (!fs.existsSync(SAMPLE_EDF)) {
  evidence.status = "failed";
  evidence.errors.push(`Missing sample EDF: ${SAMPLE_EDF}`);
  writeEvidence(evidence);
  throw new Error(evidence.errors[0]);
}

const browser = await chromium.launch(chromiumLaunchOptions({ headless: true }));
const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });
let taskRequestPhase = "pre_start";

page.on("request", (request) => {
  const url = request.url();
  if (/\/api\/eeg\/upload/.test(url) && request.method() === "POST") evidence.requests.uploads.push({ url });
  if (/\/api\/data-preparation\/plans$/.test(url) && request.method() === "POST") evidence.requests.plans.push(request.postDataJSON?.() || {});
  if (url.endsWith("/api/tasks") && request.method() === "POST") evidence.requests.tasks.push({ phase: taskRequestPhase, ...(request.postDataJSON?.() || {}) });
  if (/\/api\/tasks\/[^/]+\/epilepsy-review-sessions$/.test(url) && request.method() === "POST") evidence.requests.review_creates.push(request.postDataJSON?.() || {});
  if (/\/api\/epilepsy-review-sessions\/[^/]+$/.test(url) && request.method() === "PATCH") evidence.requests.review_patches.push(request.postDataJSON?.() || {});
  if (/\/api\/epilepsy-review-sessions\/[^/]+\/exports$/.test(url) && request.method() === "POST") evidence.requests.review_exports.push(request.postDataJSON?.() || {});
});

page.on("pageerror", (error) => {
  evidence.errors.push(error.message || String(error));
});

try {
  await page.goto(FRONTEND_URL, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForFunction(() => document.body?.dataset?.role === "customer" && document.querySelector("#appShell")?.hidden === false, null, { timeout: 90000 });
  evidence.screenshots.opened = path.join(OUT_DIR, "01_opened.png");
  await page.screenshot({ path: evidence.screenshots.opened, fullPage: true });

  let projectId = await page.evaluate(() => window.__QLANALYSER_E2E_STATE__?.real?.project?.id
    || document.querySelector('[data-project-select][data-selected="true"]')?.getAttribute("data-project-select")
    || document.querySelector('.project-row.selected[data-project-select]')?.getAttribute("data-project-select")
    || "");
  if (!projectId) {
    const firstProjectId = await page.evaluate(() => document.querySelector('[data-project-select]')?.getAttribute("data-project-select") || "");
    if (firstProjectId) {
      await clickFirstVisibleEnabled(page, `[data-project-select="${firstProjectId}"]`, "open existing project");
      await page.waitForTimeout(500);
      projectId = firstProjectId;
      evidence.steps.push({ action: "open existing project", status: "passed", project_id: projectId });
    }
  }
  if (!projectId) {
    const createResponse = await waitForResponseAfter(
      page,
      "create project",
      (response) => /\/api\/projects$/.test(response.url()) && response.request().method() === "POST",
      () => clickFirstVisibleEnabled(page, '[data-real-action="create-project"]', "create project"),
      30000,
    );
    const createdProject = await createResponse.json();
    if (!createdProject?.id) throw new Error(`create project response missing id: ${JSON.stringify(createdProject).slice(0, 300)}`);
    projectId = createdProject.id;
    evidence.steps.push({ action: "create project through UI", status: "passed", project_id: projectId });
    await page.waitForFunction((id) => {
      const current = document.querySelector(`[data-project-select="${id}"]`);
      return Boolean(current?.closest(".table-row")?.classList.contains("selected"))
        || window.__QLANALYSER_E2E_STATE__?.workspace?.selectedProjectId === id;
    }, projectId, { timeout: 30000 });
  } else {
    evidence.steps.push({ action: "reuse current project", status: "passed", project_id: projectId });
  }
  const unauthUploadResponse = await page.request.post(`${API_BASE}/eeg/upload?project_id=${encodeURIComponent(projectId)}`, {
    ...await authenticatedRequestOptions(page),
    multipart: { file: fs.createReadStream(SAMPLE_EDF) },
    timeout: 30000,
  });
  const unauthUploadBody = await unauthUploadResponse.json().catch(() => ({}));
  evidence.failure_checks = {
    missing_upload_authorization_status: unauthUploadResponse.status(),
    missing_upload_authorization_body: unauthUploadBody,
  };

  await clickFirstVisibleEnabled(page, '[data-view="storage"], [data-view-jump="storage"]', "open storage");
  await page.waitForFunction(() => document.querySelector(".view.active")?.id === "storage", null, { timeout: 30000 });
  await page.setInputFiles("#real-eeg-file", SAMPLE_EDF);
  await checkFirstVisible(page, '[data-upload-authorization="eeg"]', "upload authorization");
  evidence.steps.push({ action: "select EDF and confirm upload authorization", status: "passed" });

  const uploadResponsePromise = page.waitForResponse(
    (response) => /\/api\/eeg\/upload/.test(response.url()) && response.request().method() === "POST",
    { timeout: 90000 },
  );
  await clickFirstVisibleEnabled(page, '#storage [data-real-action="upload-eeg"], [data-real-action="upload-eeg"]', "upload EEG");
  const uploaded = await uploadResponsePromise.then((response) => response.json());
  await page.waitForFunction((uploadedFile) => {
    const file = window.__QLANALYSER_E2E_STATE__?.real?.eegFile;
    if (file?.id === uploadedFile.id) return true;
    const bodyText = document.body?.innerText || "";
    return bodyText.includes(uploadedFile.id) || bodyText.includes(uploadedFile.original_filename || uploadedFile.filename || "");
  }, uploaded, { timeout: 30000 });
  const uploadedReadback = await page.request.get(
    `${API_BASE}/eeg/files/${encodeURIComponent(uploaded.id)}`,
    await authenticatedRequestOptions(page, { timeout: 30000 }),
  ).then((res) => res.json());
  evidence.uploaded_file = {
    id: uploaded.id,
    project_id: uploaded.project_id,
    original_filename: uploaded.original_filename,
    detected_format: uploaded.detected_format,
    sampling_rate: uploaded.sampling_rate,
    channel_count: uploaded.channel_count,
    duration_sec: uploaded.duration_sec,
    upload_authorization_confirmed: uploaded.upload_authorization_confirmed,
    metadata_upload_authorization_confirmed: uploaded.metadata_json?.upload_authorization_confirmed,
  };
  evidence.uploaded_file_readback = {
    id: uploadedReadback.id,
    upload_authorization_confirmed: uploadedReadback.upload_authorization_confirmed,
    metadata_upload_authorization_confirmed: uploadedReadback.metadata_json?.upload_authorization_confirmed,
    upload_authorization_confirmed_at: uploadedReadback.upload_authorization_confirmed_at || uploadedReadback.metadata_json?.upload_authorization_confirmed_at,
  };
  taskRequestPhase = "negative_unconfirmed_preparation";
  const unpreparedTaskResponse = await page.request.post(`${API_BASE}/tasks`, {
    ...await authenticatedRequestOptions(page),
    data: {
      project_id: uploaded.project_id,
      input_file_id: uploaded.id,
      module_name: "epilepsy_ml",
      workflow_id: "epilepsy_ml_xgboost",
      parameters_json: {
        non_medical_scope: "research_screening_support_only",
      },
    },
    timeout: 30000,
  });
  const unpreparedTaskBody = await unpreparedTaskResponse.json().catch(() => ({}));
  taskRequestPhase = "pre_start";
  evidence.failure_checks.unconfirmed_preparation_task_status = unpreparedTaskResponse.status();
  evidence.failure_checks.unconfirmed_preparation_task_body = unpreparedTaskBody;
  taskRequestPhase = "negative_wrong_workflow";
  const wrongWorkflowResponse = await page.request.post(`${API_BASE}/tasks`, {
    ...await authenticatedRequestOptions(page),
    data: {
      project_id: uploaded.project_id,
      input_file_id: uploaded.id,
      module_name: "epilepsy_ml",
      workflow_id: "epilepsy_wrong_workflow",
      parameters_json: {
        non_medical_scope: "research_screening_support_only",
      },
    },
    timeout: 30000,
  });
  const wrongWorkflowBody = await wrongWorkflowResponse.json().catch(() => ({}));
  taskRequestPhase = "pre_start";
  evidence.failure_checks.wrong_workflow_status = wrongWorkflowResponse.status();
  evidence.failure_checks.wrong_workflow_body = wrongWorkflowBody;
  const missingExportResponse = await page.request.post(`${API_BASE}/epilepsy-review-sessions/eprev_missing_v01_export/exports`, {
    ...await authenticatedRequestOptions(page),
    timeout: 30000,
  });
  const missingExportBody = await missingExportResponse.json().catch(() => ({}));
  evidence.failure_checks.missing_review_session_export_status = missingExportResponse.status();
  evidence.failure_checks.missing_review_session_export_body = missingExportBody;
  await page.waitForFunction(() => document.querySelector(".view.active")?.id === "analysis", null, { timeout: 30000 });
  evidence.screenshots.after_upload = path.join(OUT_DIR, "02_after_upload.png");
  await page.screenshot({ path: evidence.screenshots.after_upload, fullPage: true });

  const planResponse = await waitForResponseAfter(
    page,
    "confirm data preparation plan",
    (response) => /\/api\/data-preparation\/plans$/.test(response.url()) && response.request().method() === "POST",
    () => clickFirstVisibleEnabled(page, '[data-real-action="confirm-plan-inline"]', "confirm data preparation"),
    90000,
  );
  const plan = await planResponse.json();
  evidence.plan = {
    id: plan.id,
    revision: plan.revision,
    status: plan.status,
    input_file_id: plan.input_file_id,
    schema_version: plan.schema_version,
    module_scope: plan.module_scope,
  };
  evidence.steps.push({ action: "confirm data preparation", status: "passed", plan_id: plan.id });

  await clickFirstVisibleEnabled(page, '[data-view="workflow"], [data-view-jump="workflow"]', "open analysis tasks");
  await page.waitForFunction(() => document.querySelector(".view.active")?.id === "workflow", null, { timeout: 30000 });
  await clickFirstVisibleEnabled(page, '[data-testid="analysis-method-scope-panel"] [data-module-id="epilepsy_ml"]', "open epilepsy workbench");
  await page.waitForSelector('[data-testid="main-epilepsy-workbench-inline"].active', { timeout: 30000 });
  evidence.checks.no_task_before_start = evidence.requests.tasks.filter((item) => item.phase === "user_start_screening").length === 0;
  evidence.screenshots.inline_initial = path.join(OUT_DIR, "03_inline_initial.png");
  await page.screenshot({ path: evidence.screenshots.inline_initial, fullPage: true });
  evidence.inline_initial_state = await page.evaluate(() => {
    const activeView = document.querySelector(".view.active")?.id || "";
    const sections = Array.from(document.querySelectorAll("#epilepsyWorkbenchInline [data-testid]")).map((el) => el.getAttribute("data-testid"));
    const wavePanel = document.querySelector('[data-testid="inline-epilepsy-waveform-panel"]');
    const startPanel = document.querySelector('[data-testid="inline-epilepsy-screening-panel"]');
    const waveRect = wavePanel?.getBoundingClientRect?.() || { top: 0 };
    const startRect = startPanel?.getBoundingClientRect?.() || { top: 0 };
    const scaleButtons = document.querySelectorAll('#epilepsyWorkbenchInline [data-epilepsy-action="set-time-scale"]').length;
    const spectrogramScaleButtons = document.querySelectorAll('[data-testid="inline-epilepsy-spectrogram-panel"] [data-epilepsy-action="set-time-scale"]').length;
    const syncReadoutText = document.querySelector('[data-testid="inline-epilepsy-sync-scale-readout"]')?.textContent?.replace(/\s+/g, " ").trim() || "";
    return {
      activeView,
      sections,
      activeNav: document.querySelector(".nav [data-view].active")?.getAttribute("data-view") || "",
      viewTitle: document.querySelector("#viewTitle")?.textContent?.replace(/\s+/g, " ").trim() || "",
      waveformBeforeScreeningPanel: waveRect.top <= startRect.top,
      scaleButtons,
      spectrogramScaleButtons,
      syncReadoutText,
      startButtonText: document.querySelector('[data-testid="inline-epilepsy-start-screening"]')?.textContent?.replace(/\s+/g, " ").trim() || "",
    };
  });
  const preWheelToast = await page.locator("#toast").textContent().catch(() => "");
  await page.locator('[data-testid="inline-epilepsy-waveform-canvas"]').hover();
  await page.mouse.wheel(240, 0);
  await page.waitForTimeout(350);
  evidence.inline_wheel_state = await page.evaluate((beforeToast) => {
    const toast = document.querySelector("#toast")?.textContent?.replace(/\s+/g, " ").trim() || "";
    const readerStart = Number(document.querySelector('[data-testid="inline-epilepsy-waveform-canvas"]')?.dataset.readerStartSec || 0);
    return {
      toastBefore: beforeToast || "",
      toastAfter: toast,
      toastUnchanged: toast === (beforeToast || ""),
      readerStart,
    };
  }, preWheelToast || "");

  taskRequestPhase = "user_start_screening";
  const taskResponse = await waitForResponseAfter(
    page,
    "start epilepsy screening",
    (response) => taskRequestHasModule(response, "epilepsy_ml"),
    () => clickFirstVisibleEnabled(page, '[data-testid="inline-epilepsy-start-screening"]', "start screening"),
    240000,
  );
  taskRequestPhase = "after_user_start";
  const taskResponseJson = await taskResponse.json();
  evidence.task_response = taskResponseJson;
  const backendTask = await waitForTaskCompleted(page, 240000).catch(async (error) => {
    evidence.task_wait_error = error?.message || String(error);
    if (taskResponseJson?.id) {
      const readback = await page.request.get(
        `${API_BASE}/tasks/${encodeURIComponent(taskResponseJson.id)}`,
        await authenticatedRequestOptions(page, { timeout: 60000 }),
      ).then((res) => res.json()).catch((readError) => ({ readback_error: readError?.message || String(readError) }));
      evidence.task_readback_after_wait_timeout = readback;
      if (String(readback?.status || "").toLowerCase() === "completed") return readback;
    }
    throw error;
  });
  await page.waitForFunction(() => {
    const inline = window.__QLANALYSER_E2E_STATE__?.epilepsyInline;
    const eventText = document.querySelector('[data-testid="inline-epilepsy-events-panel"]')?.textContent || "";
    const stageText = document.querySelector('[data-testid="inline-epilepsy-stage-strip"]')?.textContent || "";
    const summaryText = document.querySelector('[data-testid="inline-epilepsy-summary-panel"]')?.textContent || "";
    const spectrogramCanvas = document.querySelector('[data-testid="inline-epilepsy-spectrogram-canvas"]');
    const hasInternalRows = Array.isArray(inline?.epochRows)
      && inline.epochRows.length > 0
      && Array.isArray(inline?.eventRows)
      && inline.eventRows.length > 0;
    const hasVisibleRows = /候选事件|25\.0|35\.0|epoch/i.test(eventText)
      && /Stage_Code|0|1/.test(stageText)
      && /真实结果已载入|候选事件|Stage_Code/i.test(summaryText);
    return (inline?.resultLoadStatus === "ready" || hasVisibleRows)
      && (inline?.spectrogramLoadStatus === "ready" || Boolean(spectrogramCanvas))
      && (hasInternalRows || hasVisibleRows)
      && /25\.0|35\.0|epoch/.test(eventText)
      && /0|1/.test(stageText);
  }, null, { timeout: 60000 });
  evidence.inline_completed_state = await page.evaluate(() => {
    const progress = document.querySelector('[data-testid="inline-epilepsy-screening-progress"]');
    const bar = progress?.querySelector('[role="progressbar"]');
    const spectrogramCanvas = document.querySelector('[data-testid="inline-epilepsy-spectrogram-canvas"]');
    const waveformCanvas = document.querySelector('[data-testid="inline-epilepsy-waveform-canvas"]');
    return {
      screeningStatus: progress?.getAttribute("data-status") || "",
      progressNow: bar?.getAttribute("aria-valuenow") || "",
      spectrogramStatus: spectrogramCanvas?.dataset.spectrogramStatus || "",
      spectrogramSource: spectrogramCanvas?.dataset.source || "",
      waveformStageOverlay: waveformCanvas?.dataset.stageOverlay || "",
    };
  });
  await clickFirstVisibleEnabled(page, '[data-testid="inline-epilepsy-toggle-stage"]', "toggle stage overlay off");
  await page.waitForFunction(() => document.querySelector('[data-testid="inline-epilepsy-waveform-canvas"]')?.dataset.stageOverlay === "hidden", null, { timeout: 10000 });
  await clickFirstVisibleEnabled(page, '[data-testid="inline-epilepsy-toggle-stage"]', "toggle stage overlay on");
  await page.waitForFunction(() => document.querySelector('[data-testid="inline-epilepsy-waveform-canvas"]')?.dataset.stageOverlay === "visible", null, { timeout: 10000 });
  evidence.inline_stage_overlay_toggle = await page.evaluate(() => ({
    finalOverlay: document.querySelector('[data-testid="inline-epilepsy-waveform-canvas"]')?.dataset.stageOverlay || "",
    togglePressed: document.querySelector('[data-testid="inline-epilepsy-toggle-stage"]')?.getAttribute("aria-pressed") || "",
    stageText: document.querySelector('[data-testid="inline-epilepsy-stage-strip"]')?.textContent?.replace(/\s+/g, " ").trim() || "",
  }));

  const backendArtifacts = await page.request.get(
    `${API_BASE}/tasks/${encodeURIComponent(backendTask.id)}/artifacts`,
    await authenticatedRequestOptions(page, { timeout: 60000 }),
  ).then((res) => res.json());
  evidence.backend_task = {
    id: backendTask.id,
    status: backendTask.status,
    module_name: backendTask.module_name,
    workflow_id: backendTask.workflow_id,
    data_preparation_plan_id: backendTask.data_preparation_plan_id,
    data_preparation_revision: backendTask.data_preparation_revision,
  };
  evidence.backend_artifact_labels = backendArtifacts.map((item) => item.label);
  const epochRead = await readArtifactText(page, backendArtifacts, /epilepsy_ml_epoch_predictions|epilepsy_epoch_scores/);
  const eventRead = await readArtifactText(page, backendArtifacts, /epilepsy_ml_events|epilepsy_events/);
  const spectrogramRead = await readArtifactText(page, backendArtifacts, /epilepsy_ml_spectrogram|spectrogram/);
  const eventTimelineFigureRead = await readArtifactText(page, backendArtifacts, /epilepsy_ml_event_timeline_figure/);
  const spectrogramFigureRead = await readArtifactText(page, backendArtifacts, /epilepsy_ml_spectrogram_figure/);
  const spectrogramJson = spectrogramRead.text ? JSON.parse(spectrogramRead.text) : null;
  evidence.algorithm_result_snapshot = {
    epoch_header: epochRead.text.trim().split(/\r?\n/)[0] || "",
    epoch_line_count: epochRead.text.trim().split(/\r?\n/).filter(Boolean).length,
    event_line_count: eventRead.text.trim().split(/\r?\n/).filter(Boolean).length,
    first_event: eventRead.text.trim().split(/\r?\n/)[1] || "",
    stage_code_hits: (epochRead.text.match(/,1,/g) || []).length,
  };
  evidence.spectrogram_artifact_snapshot = {
    label: spectrogramRead.artifact?.label || "",
    schema_version: spectrogramJson?.schema_version || "",
    source_compatibility: spectrogramJson?.source_compatibility || "",
    method: spectrogramJson?.method || "",
    parameters: spectrogramJson?.parameters || {},
    frequency_bins: spectrogramJson?.frequencies_hz?.length || 0,
    time_bins: spectrogramJson?.times_sec?.length || 0,
    power_rows: spectrogramJson?.power_db?.length || 0,
  };
  evidence.result_figure_artifact_snapshot = {
    event_timeline_label: eventTimelineFigureRead.artifact?.label || "",
    event_timeline_svg: eventTimelineFigureRead.text.trim().startsWith("<svg"),
    event_timeline_title: /癫痫样候选事件初筛时间轴/.test(eventTimelineFigureRead.text),
    event_timeline_boundary: /科研初筛支持/.test(eventTimelineFigureRead.text) && /诊断/.test(eventTimelineFigureRead.text),
    spectrogram_label: spectrogramFigureRead.artifact?.label || "",
    spectrogram_svg: spectrogramFigureRead.text.trim().startsWith("<svg"),
    spectrogram_title: /癫痫样事件初筛时频证据图/.test(spectrogramFigureRead.text),
    spectrogram_boundary: /科研初筛支持/.test(spectrogramFigureRead.text) && /诊断/.test(spectrogramFigureRead.text),
  };

  await clickFirstVisibleEnabled(page, '[data-epilepsy-action="select-event"]', "select candidate event");
  await clickFirstVisibleEnabled(page, '[data-epilepsy-action="set-correction"][data-correction="Seizure"]', "temporary keep candidate");
  await page.waitForFunction(() => /保留候选|复核草稿\s*1/.test(document.querySelector('[data-testid="inline-epilepsy-draft-ledger"]')?.textContent || ""), null, { timeout: 10000 });
  await clickFirstVisibleEnabled(page, '[data-epilepsy-action="undo"]', "undo temporary correction");
  await page.waitForFunction(() => /复核草稿\s*0/.test(document.querySelector('[data-testid="inline-epilepsy-draft-ledger"]')?.textContent || ""), null, { timeout: 10000 });
  await clickFirstVisibleEnabled(page, '[data-epilepsy-action="redo"]', "redo temporary correction");
  await page.waitForFunction(() => /保留候选|复核草稿\s*1/.test(document.querySelector('[data-testid="inline-epilepsy-draft-ledger"]')?.textContent || ""), null, { timeout: 10000 });
  await clickFirstVisibleEnabled(page, '[data-epilepsy-action="reset"]', "clear temporary correction draft");
  await page.waitForFunction(() => /复核草稿\s*0/.test(document.querySelector('[data-testid="inline-epilepsy-draft-ledger"]')?.textContent || ""), null, { timeout: 10000 });
  evidence.correction_matrix_interaction = {
    undo_redo_reset_exercised: true,
  };

  await clickFirstVisibleEnabled(page, '[data-epilepsy-action="set-correction"][data-correction="Seizure"]', "keep candidate");
  await clickFirstVisibleEnabled(page, '[data-epilepsy-action="set-correction"][data-correction="Artifact"]', "mark candidate as artifact");
  await clickFirstVisibleEnabled(page, '[data-epilepsy-action="set-correction"][data-correction="Needs review"]', "mark candidate as needs review");
  await clickFirstVisibleEnabled(page, '[data-epilepsy-action="adjust-interval"][data-adjust-edge="start"][data-adjust-delta-sec="-1"]', "adjust candidate start");
  await clickFirstVisibleEnabled(page, '[data-epilepsy-action="adjust-interval"][data-adjust-edge="end"][data-adjust-delta-sec="1"]', "adjust candidate end");
  await clickFirstVisibleEnabled(page, '[data-epilepsy-action="set-correction"][data-correction="Normal"]', "exclude candidate");
  await page.waitForFunction(() => /保留候选|标为伪迹|需复核|起点 -1s|终点 \+1s|排除候选/.test(document.querySelector('[data-testid="inline-epilepsy-draft-ledger"]')?.textContent || "") && /复核草稿\s*6/.test(document.querySelector('[data-testid="inline-epilepsy-draft-ledger"]')?.textContent || ""), null, { timeout: 10000 });
  evidence.correction_panel_before_publish = await page.evaluate(() => ({
    eventText: document.querySelector('[data-testid="inline-epilepsy-events-panel"]')?.textContent?.replace(/\s+/g, " ").trim() || "",
    reviewText: document.querySelector('[data-testid="inline-epilepsy-review-panel"]')?.textContent?.replace(/\s+/g, " ").trim() || "",
    draftLedgerText: document.querySelector('[data-testid="inline-epilepsy-draft-ledger"]')?.textContent?.replace(/\s+/g, " ").trim() || "",
  }));

  const reviewCreatePromise = page.waitForResponse((response) => /\/api\/tasks\/[^/]+\/epilepsy-review-sessions$/.test(response.url()) && response.request().method() === "POST", { timeout: 60000 });
  const reviewPatchPromise = page.waitForResponse((response) => /\/api\/epilepsy-review-sessions\/[^/]+$/.test(response.url()) && response.request().method() === "PATCH", { timeout: 60000 });
  await clickFirstVisibleEnabled(page, '[data-epilepsy-action="save-draft"]', "save review draft");
  const [reviewCreateResponse, reviewPatchResponse] = await Promise.all([reviewCreatePromise, reviewPatchPromise]);
  const reviewCreateJson = await reviewCreateResponse.json();
  const reviewPatchJson = await reviewPatchResponse.json();

  const reviewExportPromise = page.waitForResponse((response) => /\/api\/epilepsy-review-sessions\/[^/]+\/exports$/.test(response.url()) && response.request().method() === "POST", { timeout: 60000 });
  await clickFirstVisibleEnabled(page, '[data-epilepsy-action="publish-results"]', "publish review results");
  const reviewExportJson = await (await reviewExportPromise).json();
  await page.waitForFunction(() => window.__QLANALYSER_E2E_STATE__?.epilepsyInline?.exportStatus === "exported", null, { timeout: 15000 });
  await clickFirstVisibleEnabled(page, '[data-testid="inline-epilepsy-view-results"], [data-view="statistics"]', "open results");
  await page.waitForFunction(() => document.querySelector(".view.active")?.id === "statistics", null, { timeout: 15000 });
  await page.waitForFunction(() => /癫痫样|人工矫正|复核|候选事件|epoch/.test(document.querySelector('[data-result-module="epilepsy_ml"]')?.textContent || ""), null, { timeout: 15000 });
  await page.waitForFunction(() => Array.from(document.querySelectorAll('[data-result-module="epilepsy_ml"] img')).some((img) => img.complete && img.naturalWidth > 0), null, { timeout: 30000 });
  evidence.screenshots.results = path.join(OUT_DIR, "04_results_review_package.png");
  await page.screenshot({ path: evidence.screenshots.results, fullPage: true });

  const finalState = await page.evaluate(() => {
    const task = window.__QLANALYSER_EPILEPSY_E2E_TASK__ || window.__QLANALYSER_LAST_EPILEPSY_TASK__ || window.__QLANALYSER_E2E_STATE__?.real?.tasks?.epilepsy_ml || null;
    const inline = window.__QLANALYSER_E2E_STATE__?.epilepsyInline || {};
    const resultText = document.querySelector('[data-result-module="epilepsy_ml"]')?.textContent?.replace(/\s+/g, " ").trim() || "";
    const resultImageGrid = document.querySelector('[data-testid="result-image-preview-grid"]');
    const resultImages = Array.from(document.querySelectorAll('[data-result-module="epilepsy_ml"] img')).map((img) => ({
      src: img.getAttribute("src") || "",
      alt: img.getAttribute("alt") || "",
      loaded: img.complete && img.naturalWidth > 0,
    }));
    const eventText = document.querySelector('[data-testid="inline-epilepsy-events-panel"]')?.textContent?.replace(/\s+/g, " ").trim() || "";
    const stageText = document.querySelector('[data-testid="inline-epilepsy-stage-strip"]')?.textContent?.replace(/\s+/g, " ").trim() || "";
    return {
      activeView: document.querySelector(".view.active")?.id || "",
      task,
      resultText,
      resultImageGridVisible: Boolean(resultImageGrid) || resultImages.some((img) => img.loaded),
      resultImages,
      eventText,
      stageText,
      reviewSession: inline.reviewSession || null,
      draftSaved: Boolean(inline.draftSaved),
      exportStatus: inline.exportStatus || "",
      exportResult: inline.exportResult || null,
    };
  });
  evidence.final_state = finalState;
  evidence.review_flow = {
    create_request: evidence.requests.review_creates[0] || null,
    patch_request: evidence.requests.review_patches[0] || null,
    export_request: evidence.requests.review_exports[0] || null,
    create_response_id: reviewCreateJson.id || "",
    patch_response_status: reviewPatchJson.status || "",
    export_response: reviewExportJson,
  };
  const reportResponse = await page.request.post(`${API_BASE}/reports`, {
    ...await authenticatedRequestOptions(page),
    data: {
      project_id: backendTask.project_id || evidence.uploaded_file.project_id,
      task_id: backendTask.id,
      title: "癫痫样事件初筛试用报告",
    },
    timeout: 60000,
  });
  const reportJson = await reportResponse.json().catch(() => ({}));
  const packageResponse = reportJson?.id
    ? await page.request.get(
      `${API_BASE}/reports/${encodeURIComponent(reportJson.id)}/package`,
      await authenticatedRequestOptions(page, { timeout: 60000 }),
    )
    : null;
  const packageBuffer = packageResponse?.ok()
    ? Buffer.from(await packageResponse.body())
    : Buffer.alloc(0);
  const packageIndexText = packageBuffer.toString("latin1");
  evidence.report_package = {
    status: reportResponse.status(),
    id: reportJson?.id || "",
    package_status: packageResponse?.status?.() || 0,
    package_bytes: packageBuffer.length,
    has_event_timeline_svg: packageIndexText.includes("figures/epilepsy_ml_event_timeline.svg"),
    has_spectrogram_svg: packageIndexText.includes("figures/epilepsy_ml_spectrogram_preview.svg"),
  };

  const taskPayload = evidence.requests.tasks.find((item) => item.module_name === "epilepsy_ml") || {};
  const uploadUrl = evidence.requests.uploads[0]?.url || "";
  evidence.checks.upload_authorization_in_request = /upload_authorization_confirmed=true/.test(uploadUrl);
  evidence.checks.upload_authorization_persisted = evidence.uploaded_file.upload_authorization_confirmed === true
    || evidence.uploaded_file.metadata_upload_authorization_confirmed === true
    || evidence.uploaded_file_readback.upload_authorization_confirmed === true
    || evidence.uploaded_file_readback.metadata_upload_authorization_confirmed === true;
  evidence.checks.uploaded_edf_metadata = evidence.uploaded_file.detected_format === "edf"
    && Number(evidence.uploaded_file.duration_sec) >= 50
    && Number(evidence.uploaded_file.channel_count) >= 1;
  evidence.checks.plan_confirmed_for_uploaded_file = evidence.plan.status === "confirmed"
    && evidence.plan.input_file_id === evidence.uploaded_file.id
    && Array.isArray(evidence.plan.module_scope)
    && evidence.plan.module_scope.includes("epilepsy_ml");
  evidence.checks.task_payload_contract = taskPayload.module_name === "epilepsy_ml"
    && taskPayload.workflow_id === "epilepsy_ml_xgboost"
    && taskPayload.input_file_id === evidence.uploaded_file.id
    && taskPayload.parameters_json?.data_preparation_plan_id === evidence.plan.id
    && Number(taskPayload.parameters_json?.data_preparation_revision) === Number(evidence.plan.revision)
    && taskPayload.parameters_json?.data_preparation_contract_version === "qlanalyser-data-preparation-v0.2";
  evidence.checks.task_completed = backendTask.status === "completed";
  evidence.checks.stage_code_truth = /Stage_Code/.test(evidence.algorithm_result_snapshot.epoch_header)
    && evidence.algorithm_result_snapshot.stage_code_hits >= 1;
  evidence.checks.candidate_event_truth = /25\.0,35\.0|25\.0.*35\.0/.test(evidence.algorithm_result_snapshot.first_event);
  evidence.checks.review_correction_saved = Boolean(finalState.draftSaved)
    && Boolean(finalState.reviewSession?.id)
    && Object.keys(evidence.review_flow.patch_request?.event_reviews || {}).length > 0
    && Object.keys(evidence.review_flow.patch_request?.epoch_overrides || {}).length > 0;
  evidence.checks.correction_matrix_actions_saved = evidence.correction_matrix_interaction?.undo_redo_reset_exercised === true
    && Array.isArray(evidence.review_flow.patch_request?.actions)
    && evidence.review_flow.patch_request.actions.length >= 6
    && evidence.review_flow.patch_request.actions.some((item) => item?.after?.display_label === "保留候选")
    && evidence.review_flow.patch_request.actions.some((item) => item?.after?.display_label === "标为伪迹")
    && evidence.review_flow.patch_request.actions.some((item) => item?.after?.display_label === "需复核")
    && evidence.review_flow.patch_request.actions.some((item) => item?.type === "adjust_event_interval" && Number.isFinite(Number(item?.after?.adjusted_start_sec)))
    && evidence.review_flow.patch_request.actions.some((item) => item?.type === "adjust_event_interval" && Number.isFinite(Number(item?.after?.adjusted_end_sec)))
    && evidence.review_flow.patch_request.actions.some((item) => item?.after?.display_label === "排除候选");
  evidence.checks.review_export_published = finalState.exportStatus === "exported"
    && Boolean(evidence.review_flow.export_response?.registered_artifacts?.length || evidence.review_flow.export_response?.manifest?.registered_artifacts?.length);
  evidence.checks.results_module_has_review_package = finalState.activeView === "statistics"
    && /癫痫样|人工矫正|复核|候选事件|epoch/.test(finalState.resultText);
  evidence.checks.non_medical_scope_export = JSON.stringify(evidence.review_flow.export_response).includes("research_screening_support_only");
  evidence.checks.missing_upload_authorization_rejected = evidence.failure_checks?.missing_upload_authorization_status === 422
    && JSON.stringify(evidence.failure_checks?.missing_upload_authorization_body || {}).includes("UPLOAD_AUTHORIZATION_REQUIRED");
  evidence.checks.unconfirmed_preparation_rejected = evidence.failure_checks?.unconfirmed_preparation_task_status === 422
    && JSON.stringify(evidence.failure_checks?.unconfirmed_preparation_task_body || {}).includes("DATA_PREPARATION_REQUIRED");
  evidence.checks.wrong_workflow_rejected = evidence.failure_checks?.wrong_workflow_status === 422
    && JSON.stringify(evidence.failure_checks?.wrong_workflow_body || {}).includes("WORKFLOW_CONTRACT_MISMATCH");
  evidence.checks.missing_review_session_export_rejected = evidence.failure_checks?.missing_review_session_export_status === 404
    && JSON.stringify(evidence.failure_checks?.missing_review_session_export_body || {}).includes("Epilepsy review session not found");
  const customerReviewVisibleText = [
    evidence.correction_panel_before_publish?.eventText || "",
    evidence.correction_panel_before_publish?.reviewText || "",
    evidence.correction_panel_before_publish?.draftLedgerText || "",
    finalState.eventText || "",
    finalState.resultText || "",
  ].join("\n");
  evidence.checks.customer_review_labels_visible = /保留候选/.test(customerReviewVisibleText)
    && /排除候选/.test(customerReviewVisibleText)
    && /标为伪迹/.test(customerReviewVisibleText)
    && /需复核/.test(customerReviewVisibleText)
    && evidence.review_flow.patch_request?.event_reviews?.["1"]?.note === "Manual review: 排除候选"
    && evidence.review_flow.patch_request?.actions?.some((item) => item?.after?.display_label === "排除候选");
  evidence.checks.no_old_labels_in_candidate_panel = !textHasAny(customerReviewVisibleText, [
    /Seizure\s*\/\s*Normal\s*\/\s*Needs review/i,
  ]);
  evidence.checks.no_epilepsy_staging_copy = !textHasAny(`${customerReviewVisibleText}\n${finalState.resultText}`, [
    /癫痫分期/,
    /开始分期/,
    /初筛\/分期/,
  ]);
  evidence.checks.no_diagnosis_or_treatment_copy = !textHasAny(`${customerReviewVisibleText}\n${finalState.resultText}`, [
    /诊断结论/,
    /确诊为/,
    /确诊：/,
    /治疗建议/,
    /用于临床分诊/,
    /临床分诊建议/,
  ]);
  evidence.checks.no_video_placeholder_copy = !textHasAny(`${customerReviewVisibleText}\n${finalState.resultText}`, [
    /Video unavailable/i,
    /当前数据无视频/,
    /视频占位/,
  ]);
  evidence.checks.customer_copy_no_old_review_labels = evidence.checks.no_old_labels_in_candidate_panel
    && evidence.checks.no_epilepsy_staging_copy
    && evidence.checks.no_diagnosis_or_treatment_copy
    && evidence.checks.no_video_placeholder_copy;
  evidence.checks.inline_entry_waveform_first = evidence.inline_initial_state?.activeView === "epilepsyWorkbenchInline"
    && evidence.inline_initial_state?.activeNav === "workflow"
    && /癫痫样事件分析台/.test(evidence.inline_initial_state?.viewTitle || "")
    && evidence.inline_initial_state?.sections?.includes("inline-epilepsy-waveform-panel")
    && evidence.inline_initial_state?.sections?.includes("inline-epilepsy-screening-panel")
    && evidence.inline_initial_state?.waveformBeforeScreeningPanel === true;
  evidence.checks.inline_no_duplicate_scale_controls = evidence.inline_initial_state?.scaleButtons === 3
    && evidence.inline_initial_state?.spectrogramScaleButtons === 0
    && /跟随阅片窗/.test(evidence.inline_initial_state?.syncReadoutText || "");
  evidence.checks.inline_wheel_no_toast = evidence.inline_wheel_state?.toastUnchanged === true;
  evidence.checks.inline_progress_completed = evidence.inline_completed_state?.screeningStatus === "completed"
    && evidence.inline_completed_state?.progressNow === "100";
  evidence.checks.inline_spectrogram_same_window_source = evidence.inline_completed_state?.spectrogramSource === "epilepsy_ml_spectrogram_artifact_pc_stft";
  evidence.checks.epilepsy_pc_stft_artifact_contract = evidence.spectrogram_artifact_snapshot?.schema_version === "qlanalyser-epilepsy-ml-spectrogram-v0.1"
    && /EpilepsyAnalysis2\.py::calculate_spectrogram/.test(evidence.spectrogram_artifact_snapshot?.source_compatibility || "")
    && evidence.spectrogram_artifact_snapshot?.method === "scipy.signal.stft"
    && Number(evidence.spectrogram_artifact_snapshot?.parameters?.window_sec) === 4
    && Number(evidence.spectrogram_artifact_snapshot?.parameters?.overlap_ratio) === 0.9
    && Number(evidence.spectrogram_artifact_snapshot?.parameters?.freq_min_hz) === 0.5
    && Number(evidence.spectrogram_artifact_snapshot?.parameters?.freq_max_hz) === 50
    && evidence.spectrogram_artifact_snapshot?.parameters?.power_transform === "10*log10(abs(Zxx)+1e-10)"
    && evidence.spectrogram_artifact_snapshot?.frequency_bins > 0
    && evidence.spectrogram_artifact_snapshot?.time_bins > 0
    && evidence.spectrogram_artifact_snapshot?.power_rows > 0;
  evidence.checks.epilepsy_result_image_artifacts = evidence.backend_artifact_labels.includes("epilepsy_ml_event_timeline_figure")
    && evidence.backend_artifact_labels.includes("epilepsy_ml_spectrogram_figure")
    && evidence.result_figure_artifact_snapshot?.event_timeline_svg === true
    && evidence.result_figure_artifact_snapshot?.event_timeline_title === true
    && evidence.result_figure_artifact_snapshot?.event_timeline_boundary === true
    && evidence.result_figure_artifact_snapshot?.spectrogram_svg === true
    && evidence.result_figure_artifact_snapshot?.spectrogram_title === true
    && evidence.result_figure_artifact_snapshot?.spectrogram_boundary === true;
  evidence.checks.results_module_shows_result_images = finalState.resultImageGridVisible === true
    && Array.isArray(finalState.resultImages)
    && finalState.resultImages.length >= 2
    && finalState.resultImages.some((item) => /epilepsy_ml_event_timeline|event_timeline|timeline|候选事件初筛时间轴/i.test(`${item.src} ${item.alt}`))
    && finalState.resultImages.some((item) => /epilepsy_ml_spectrogram|spectrogram|时频证据图/i.test(`${item.src} ${item.alt}`));
  evidence.checks.report_package_includes_result_images = evidence.report_package?.status === 200
    && evidence.report_package?.package_status === 200
    && evidence.report_package?.package_bytes > 1024
    && evidence.report_package?.has_event_timeline_svg === true
    && evidence.report_package?.has_spectrogram_svg === true;
  evidence.checks.inline_stage_overlay_toggle = evidence.inline_completed_state?.waveformStageOverlay === "visible"
    && evidence.inline_stage_overlay_toggle?.finalOverlay === "visible"
    && evidence.inline_stage_overlay_toggle?.togglePressed === "true"
    && /1/.test(evidence.inline_stage_overlay_toggle?.stageText || "");
  evidence.status = Object.values(evidence.checks).every(Boolean) ? "passed" : "failed";
} catch (error) {
  evidence.errors.push(error?.stack || error?.message || String(error));
  evidence.status = "failed";
  evidence.failure_state = await page.evaluate(() => ({
    activeView: document.querySelector(".view.active")?.id || "",
    toast: document.querySelector("#toast")?.textContent?.replace(/\s+/g, " ").trim() || "",
    latestAction: window.__QLANALYSER_LAST_REAL_ACTION__ || null,
    task: window.__QLANALYSER_EPILEPSY_E2E_TASK__ || window.__QLANALYSER_LAST_EPILEPSY_TASK__ || null,
  })).catch(() => null);
  evidence.screenshots.failure = path.join(OUT_DIR, "failure.png");
  await page.screenshot({ path: evidence.screenshots.failure, fullPage: true }).catch(() => {});
} finally {
  evidence.finished_at = new Date().toISOString();
  writeEvidence(evidence);
  await browser.close().catch(() => {});
}

console.log(JSON.stringify(evidence, null, 2));
if (evidence.status !== "passed") process.exit(1);
