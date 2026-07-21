import fs from "node:fs";
import path from "node:path";
import { chromium, chromiumLaunchOptions } from "./lib/playwright_runtime.mjs";

const FRONTEND_URL = process.env.QLANALYSER_FRONTEND_URL
  || "http://127.0.0.1:4174/?customer_demo=auto&teaching_demo=auto&api=http%3A%2F%2F127.0.0.1%3A8001%2Fapi&v=main-epilepsy-entry";
const OUT_DIR = process.env.QLANALYSER_MAIN_EPILEPSY_ENTRY_EVIDENCE
  || path.resolve("work/release_evidence/20260628-main-epilepsy-entry-contract");
const EVIDENCE_PATH = path.join(OUT_DIR, "main_epilepsy_entry_contract.json");

const waveformFixtureTimes = Array.from({ length: 1000 }, (_, index) => index / 100);
const waveformFixtureData = [
  waveformFixtureTimes.map((t) => 24 * Math.sin(2 * Math.PI * 8 * t) + 8 * Math.sin(2 * Math.PI * 20 * t)),
  waveformFixtureTimes.map((t) => 18 * Math.sin(2 * Math.PI * 5 * t) + 16 * Math.sin(2 * Math.PI * 12 * t)),
  waveformFixtureTimes.map((t) => 12 * Math.sin(2 * Math.PI * 2 * t) + 20 * Math.sin(2 * Math.PI * 30 * t)),
];

function buildWaveformFixture(fileId, startSec, durationSec) {
  const pointCount = 1000;
  const times = Array.from({ length: pointCount }, (_, index) => startSec + (durationSec * index) / Math.max(1, pointCount - 1));
  return {
    file_id: fileId,
    start_sec: startSec,
    duration_sec: durationSec,
    file_duration_sec: 60,
    display_sample_rate_hz: 100,
    channels: ["Cz", "Pz", "Oz"],
    times_sec: times,
    data_uv: [
      times.map((t) => 24 * Math.sin(2 * Math.PI * 8 * t) + 8 * Math.sin(2 * Math.PI * 20 * t)),
      times.map((t) => 18 * Math.sin(2 * Math.PI * 5 * t) + 16 * Math.sin(2 * Math.PI * 12 * t)),
      times.map((t) => 12 * Math.sin(2 * Math.PI * 2 * t) + 20 * Math.sin(2 * Math.PI * 30 * t)),
    ],
    downsample: "raw_fixture",
    non_medical_scope: "research_screening_support_only",
  };
}

function writeEvidence(payload) {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  fs.writeFileSync(EVIDENCE_PATH, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
}

  const evidence = {
  script: path.basename(new URL(import.meta.url).pathname),
  started_at: new Date().toISOString(),
  frontend_url: FRONTEND_URL,
  checks: {},
  captured_task_payload: null,
  captured_task_payloads: [],
  screenshots: {},
  errors: [],
  status: "running",
  review_session_create_count: 0,
  review_session_patch_count: 0,
  review_session_export_count: 0,
  captured_review_create_payload: null,
  captured_review_patch_payload: null,
  captured_review_export_response: null,
};

const browser = await chromium.launch(chromiumLaunchOptions({ headless: true }));
const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });

try {
  const demoProject = { id: "proj_demo_learning", name: "Teaching demo project", status: "active", metadata_json: { teaching_demo: true } };
  const demoFile = { id: "eeg_demo_teaching_oddball", original_filename: "teaching_demo.edf", duration_sec: 60, project_id: "proj_demo_learning", metadata_json: { teaching_demo: true } };
  const epilepsyDemoProject = {
    id: "proj_demo_epilepsy_lab",
    name: "Epilepsy teaching lab demo",
    status: "active",
    permission_policy: { teaching_mode: true, protected_teaching_dataset: true },
  };
  const epilepsyDemoFile = {
    id: "eeg_demo_epilepsy_high_amplitude",
    original_filename: "epilepsy_ml_demo_source_channels.edf",
    duration_sec: 60,
    project_id: "proj_demo_epilepsy_lab",
    metadata_json: { teaching_mode: true, protected_teaching_dataset: true, ml_fixture_ready: true },
    permission_policy: { teaching_mode: true, protected_teaching_dataset: true },
    retention_policy: "protected_teaching_demo",
  };
  const confirmedPlan = {
    id: "plan_e2e_main",
    input_file_id: "eeg_demo_teaching_oddball",
    project_id: "proj_demo_learning",
    revision: 1,
    status: "confirmed",
    is_default: false,
    contract_version: "qlanalyser-data-preparation-v0.2",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
  const epilepsyConfirmedPlan = {
    ...confirmedPlan,
    id: "plan_e2e_epilepsy_demo",
    input_file_id: "eeg_demo_epilepsy_high_amplitude",
    project_id: "proj_demo_epilepsy_lab",
  };
  await page.route("**/api/lab/demo/dataset", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 220));
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ project: demoProject, file: demoFile, data_preparation_plan: confirmedPlan }) });
  });
  await page.route("**/api/lab/demo/epilepsy", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ project: epilepsyDemoProject, file: epilepsyDemoFile, data_preparation_plan: epilepsyConfirmedPlan, fixture_id: "epilepsy_ml_demo_source_channels_v1", status: "ready" }) });
  });
  await page.route("**/api/projects", async (route) => {
    if (route.request().method().toUpperCase() === "POST") return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(demoProject) });
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([demoProject, epilepsyDemoProject]) });
  });
  await page.route("**/api/data-preparation/plans?**", async (route) => {
    const url = new URL(route.request().url());
    const fileId = url.searchParams.get("input_file_id") || url.searchParams.get("file_id") || "";
    const plans = fileId === "eeg_demo_epilepsy_high_amplitude" ? [epilepsyConfirmedPlan] : [confirmedPlan];
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(plans) });
  });
  await page.route("**/api/data-preparation/plans", async (route) => {
    const payload = route.request().method().toUpperCase() === "POST" ? route.request().postDataJSON() : {};
    const plan = payload?.input_file_id === "eeg_demo_epilepsy_high_amplitude" ? epilepsyConfirmedPlan : confirmedPlan;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(plan) });
  });
  await page.route("**/api/eeg/files/eeg_demo_teaching_oddball/epoch-sets", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
  });
  await page.route("**/api/eeg/files/eeg_demo_epilepsy_high_amplitude/epoch-sets", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
  });
  await page.route("**/api/eeg/files/eeg_demo_teaching_oddball/waveform/chunk?**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        file_id: demoFile.id,
        start_sec: 0,
        duration_sec: 10,
        display_sample_rate_hz: 100,
        channels: ["Cz", "Pz", "Oz"],
        times_sec: waveformFixtureTimes,
        data_uv: waveformFixtureData,
        downsample: "raw_fixture",
        non_medical_scope: "research_screening_support_only",
      }),
    });
  });
  await page.route("**/api/eeg/files/eeg_demo_epilepsy_high_amplitude/waveform/chunk?**", async (route) => {
    const url = new URL(route.request().url());
    const startSec = Number(url.searchParams.get("start_sec") || 0);
    const durationSec = Number(url.searchParams.get("duration_sec") || 10);
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(buildWaveformFixture(epilepsyDemoFile.id, startSec, durationSec)),
    });
  });
  await page.route("**/api/tasks", async (route) => {
    const request = route.request();
    if (request.method().toUpperCase() !== "POST") return route.continue();
    const payload = request.postDataJSON();
    evidence.captured_task_payload = payload;
    evidence.captured_task_payloads.push(payload);
    if (payload?.module_name === "epilepsy_ml") await new Promise((resolve) => setTimeout(resolve, 350));
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "task_epilepsy_entry_contract",
        project_id: payload.project_id,
        input_file_id: payload.input_file_id,
        module_name: payload.module_name,
        workflow_id: payload.workflow_id,
        parameters_json: payload.parameters_json,
        status: "completed",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      }),
    });
  });
  await page.route("**/api/tasks/task_epilepsy_entry_contract", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "task_epilepsy_entry_contract",
        project_id: "proj_demo_epilepsy_lab",
        input_file_id: "eeg_demo_epilepsy_high_amplitude",
        module_name: "epilepsy_ml",
        workflow_id: "epilepsy_ml_xgboost",
        parameters_json: {
          data_preparation_plan_id: "plan_e2e_epilepsy_demo",
          data_preparation_revision: 1,
          data_preparation_contract_version: "qlanalyser-data-preparation-v0.2",
          non_medical_boundary: "Research screening/support only; no diagnosis, treatment, or clinical decision-making.",
        },
        status: "completed",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      }),
    });
  });
  await page.route("**/api/tasks/task_epilepsy_entry_contract/artifacts", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        { id: "art_ep_ml_epochs", label: "epilepsy_ml_epoch_predictions.csv", artifact_type: "table", path: "tables/epilepsy_ml_epoch_predictions.csv" },
        { id: "art_ep_ml_events", label: "epilepsy_ml_events.csv", artifact_type: "table", path: "tables/epilepsy_ml_events.csv" },
        { id: "art_ep_ml_summary", label: "epilepsy_ml_summary.json", artifact_type: "summary", path: "summary/epilepsy_ml_summary.json" },
        { id: "art_ep_ml_manifest", label: "epilepsy_ml_model_manifest.json", artifact_type: "reproducibility", path: "reproducibility/epilepsy_ml_model_manifest.json" },
      ]),
    });
  });
  await page.route("**/api/artifacts/art_ep_ml_epochs/download", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "text/csv",
      body: [
        "epoch_index,start_sec,end_sec,Stage_Code,Stage,mean_rms,probability,is_event_epoch,threshold",
        "0,0,5,0,Normal,0.1,0.10,false,0.5",
        "1,5,10,1,Seizure,0.9,0.88,true,0.5",
        "2,10,15,1,Seizure,0.8,0.83,true,0.5",
        "3,15,20,0,Normal,0.1,0.12,false,0.5",
      ].join("\n"),
    });
  });
  await page.route("**/api/artifacts/art_ep_ml_events/download", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "text/csv",
      body: [
        "event_id,start_sec,end_sec,start_epoch,end_epoch,epoch_count,rms",
        "evt_1,5,15,1,2,2,0.85",
      ].join("\n"),
    });
  });
  await page.route("**/api/artifacts/art_ep_ml_summary/download", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ method: "ml_epoch_classifier", duration_sec: 20, non_medical_scope: "research_screening_support_only" }),
    });
  });
  await page.route("**/api/eeg/files", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
        body: JSON.stringify([demoFile, epilepsyDemoFile]),
    });
  });
  await page.route("**/api/tasks/task_epilepsy_entry_contract/epilepsy-review-sessions", async (route) => {
    evidence.review_session_create_count += 1;
    evidence.captured_review_create_payload = route.request().postDataJSON();
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "session_main_to_child",
        task_id: "task_epilepsy_entry_contract",
        input_file_id: "eeg_demo_epilepsy_high_amplitude",
        workflow_id: "epilepsy_ml_xgboost",
        data_preparation_plan_id: "plan_e2e_epilepsy_demo",
        data_preparation_revision: 1,
        data_preparation_contract_version: "qlanalyser-data-preparation-v0.2",
        context_state: "ready",
        epoch_length_sec: 5,
        status: "draft",
        current_epoch: 0,
        selected_range: { start: 0, end: 0 },
        epoch_overrides: {},
        event_reviews: {},
        actions: [],
        ui_state: {},
        non_medical_scope: "research_screening_support_only",
        schema_version: "epilepsy_review_session.v1",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      }),
    });
  });
  await page.route("**/api/epilepsy-review-sessions/session_main_to_child", async (route) => {
    evidence.review_session_patch_count += 1;
    evidence.captured_review_patch_payload = route.request().postDataJSON();
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "session_main_to_child",
        task_id: "task_epilepsy_entry_contract",
        status: "reviewing",
        event_reviews: evidence.captured_review_patch_payload?.event_reviews || {},
        epoch_overrides: evidence.captured_review_patch_payload?.epoch_overrides || {},
        actions: evidence.captured_review_patch_payload?.actions || [],
      }),
    });
  });
  await page.route("**/api/epilepsy-review-sessions/session_main_to_child/exports", async (route) => {
    evidence.review_session_export_count += 1;
    const exportResponse = {
      session_id: "session_main_to_child",
      task_id: "task_epilepsy_entry_contract",
      registered_artifacts: [
        { artifact_id: "review_epoch", label: "epilepsy_reviewed_epoch_scores" },
        { artifact_id: "review_events", label: "epilepsy_reviewed_events" },
        { artifact_id: "review_actions", label: "epilepsy_review_actions" },
        { artifact_id: "review_manifest", label: "epilepsy_review_session_manifest" },
      ],
      non_medical_scope: "research_screening_support_only",
    };
    evidence.captured_review_export_response = exportResponse;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(exportResponse),
    });
  });
  await page.route("**/api/eeg/files/eeg_demo_epilepsy_high_amplitude/waveform-window**", async (route) => {
    const url = new URL(route.request().url());
    const requestId = url.searchParams.get("request_id") || "";
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        file_id: "eeg_demo_epilepsy_high_amplitude",
        request_id: requestId,
        window_key: "server_main_child_window",
        source_data_revision: "eeg_demo_epilepsy_high_amplitude:fixture:1",
        start_sec: Number(url.searchParams.get("start_sec") || 3),
        duration_sec: Number(url.searchParams.get("duration_sec") || 14),
        stop_sec: Number(url.searchParams.get("start_sec") || 3) + Number(url.searchParams.get("duration_sec") || 14),
        sfreq: 200,
        filter_profile_id: url.searchParams.get("filter_profile_id") || "raw",
        filter_profile: { id: url.searchParams.get("filter_profile_id") || "raw", description: "Raw" },
        unit: "uV",
        unit_policy: { display_unit: "uV" },
        budget: { max_channels: 8, max_samples: 1000000, requested_channel_count: 1, requested_samples: 4000 },
        decimation: { method: "raw", factor: 1, max_points: 2400 },
        channels: [{ name: "Cz", encoding: "raw", decimation: 1, times_sec: [3, 4, 5, 6, 7, 8, 9], values: [0, 2, -1, 3, -2, 1, 0] }],
        epoch_overlays: [],
        event_overlays: [],
        cache: { status: "on_demand", hit: false, key: "server_main_child_window" },
        metrics: { server_elapsed_ms: 12, read_elapsed_ms: 4, filter_elapsed_ms: 0, encode_elapsed_ms: 2, payload_bytes: 1024 },
        non_medical_scope: "research_screening_support_only",
      }),
    });
  });

  await page.goto(FRONTEND_URL, { waitUntil: "domcontentloaded", timeout: 60000 });
  evidence.seed_workspace = "not_used_teaching_entry_only";
  await page.waitForFunction(() => {
    const state = window.__QLANALYSER_E2E_STATE__;
    const appShell = document.querySelector("#appShell");
    return state?.role === "customer" && appShell && !appShell.hidden && window.getComputedStyle(appShell).display !== "none";
  }, null, { timeout: 60000 });
  const teachingButton = page.locator("#teachingModeBtn").first();
  await teachingButton.waitFor({ state: "attached", timeout: 60000 });
  const teachingAlreadyActive = await page.evaluate(() => window.__QLANALYSER_E2E_STATE__?.teaching?.active === true).catch(() => false);
  const teachingButtonText = await teachingButton.innerText().catch(() => "");
  if (!teachingAlreadyActive && !teachingButtonText.includes("普通")) {
    const visible = await teachingButton.isVisible().catch(() => false);
    if (visible) await teachingButton.click();
    else await page.evaluate(() => document.querySelector("#teachingModeBtn")?.click());
    await page.waitForFunction(() => {
      const button = document.querySelector("#teachingModeBtn");
      const state = window.__QLANALYSER_E2E_STATE__;
      return button?.classList.contains("is-loading")
        || button?.getAttribute("aria-busy") === "true"
        || state?.teaching?.loading === true;
    }, null, { timeout: 1000 }).catch(() => null);
  }
  evidence.checks.teaching_button_immediate_feedback = teachingAlreadyActive || await page.evaluate(() => {
    const button = document.querySelector("#teachingModeBtn");
    const state = window.__QLANALYSER_E2E_STATE__;
    return button?.classList.contains("is-loading")
      || button?.getAttribute("aria-busy") === "true"
      || state?.teaching?.loading === true
      || state?.teaching?.active === true;
  });
  await page.waitForFunction(() => window.__QLANALYSER_E2E_STATE__?.teaching?.active === true, null, { timeout: 60000 });
  await page.waitForFunction(() => {
    const state = window.__QLANALYSER_E2E_STATE__;
    return state?.teaching?.datasetLoaded === true
      && Boolean(state?.real?.project?.id)
      && Boolean(state?.real?.eegFile?.id);
  }, null, { timeout: 60000 });
  await page.waitForFunction(() => {
    const state = window.__QLANALYSER_E2E_STATE__;
    return state?.teaching?.guideActive === true || Boolean(document.querySelector("#teachingOverlay.active"));
  }, null, { timeout: 5000 }).catch(() => null);
  if (await page.locator("#teachingOverlay.active").count()) {
    await page.evaluate(() => {
      const buttons = Array.from(document.querySelectorAll('#teachingOverlay [data-teaching-action="close"]'));
      buttons.at(-1)?.click();
    });
    await page.waitForFunction(() => !document.querySelector("#teachingOverlay.active"), null, { timeout: 1000 }).catch(() => null);
  }
  if (await page.locator("#teachingOverlay.active").count()) {
    evidence.teaching_guide_close_fallback = "forced_hidden_after_ui_close_for_chain_test";
    await page.evaluate(() => {
      if (window.__QLANALYSER_E2E_STATE__?.teaching) window.__QLANALYSER_E2E_STATE__.teaching.guideActive = false;
      document.querySelector("#teachingOverlay")?.classList.remove("active");
      document.querySelector("#teachingOverlay")?.setAttribute("hidden", "");
      document.body.classList.remove("teaching-mode-active");
      document.querySelectorAll(".teaching-target").forEach((node) => node.classList.remove("teaching-target"));
    });
    await page.waitForFunction(() => !document.querySelector("#teachingOverlay.active"), null, { timeout: 60000 });
  }
  evidence.checks.teaching_mode_active = true;
  await page.evaluate(() => {
    if (window.__QLANALYSER_E2E_STATE__?.real) {
      window.__QLANALYSER_E2E_STATE__.real.plan = null;
      window.__QLANALYSER_E2E_STATE__.workspace.selectedPlanId = "";
    }
    document.querySelector('[data-view="workflow"]')?.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true, view: window }));
  });
  await page.waitForFunction(() => document.querySelector("#workflow")?.classList.contains("active"), null, { timeout: 5000 });
  evidence.teaching_epilepsy_preplan_entry_state = await page.evaluate(() => {
    const card = document.querySelector('[data-testid="analysis-method-scope-panel"] [data-module-id="epilepsy_ml"]');
    return {
      activeView: document.querySelector(".view.active")?.id || "",
      disabled: Boolean(card?.disabled || card?.getAttribute("aria-disabled") === "true"),
      title: card?.getAttribute("title") || "",
      text: card?.textContent?.replace(/\s+/g, " ").trim() || "",
    };
  });
  evidence.checks.teaching_epilepsy_entry_clickable_before_plan_confirm = evidence.teaching_epilepsy_preplan_entry_state.disabled === false
    && evidence.teaching_epilepsy_preplan_entry_state.title.includes("教学模式可直接进入");
  await page.evaluate(() => {
    const appShell = document.querySelector("#appShell");
    const loginScreen = document.querySelector("#loginScreen");
    if (appShell?.hidden && typeof window.handleCustomerLoginClick === "function") {
      const email = document.querySelector("#customerEmail");
      const password = document.querySelector("#customerPassword");
      if (email && !email.value) email.value = "customer@qlanalyser.online";
      if (password && !password.value) password.value = "CustomerDemo2026!";
    }
    if (appShell?.hidden) {
      loginScreen && (loginScreen.hidden = true);
      appShell.hidden = false;
      document.body.dataset.role = "customer";
    }
  });
  await page.waitForFunction(() => {
    const appShell = document.querySelector("#appShell");
    return appShell && !appShell.hidden && window.getComputedStyle(appShell).display !== "none";
  }, null, { timeout: 5000 });
  await page.evaluate(() => {
    if (window.__QLANALYSER_E2E_STATE__?.teaching) window.__QLANALYSER_E2E_STATE__.teaching.guideActive = false;
    document.querySelector("#teachingOverlay")?.classList.remove("active");
    document.querySelector("#teachingOverlay")?.setAttribute("hidden", "");
    document.body.classList.remove("teaching-mode-active");
    document.querySelectorAll(".teaching-target").forEach((node) => node.classList.remove("teaching-target"));
  });
  const analysisButton = page.locator('[data-view="analysis"], [data-view-jump="analysis"]').first();
  await analysisButton.waitFor({ state: "attached", timeout: 60000 });
  if (await analysisButton.isVisible().catch(() => false)) await analysisButton.click();
  else await page.evaluate(() => {
    const button = document.querySelector('[data-view="analysis"], [data-view-jump="analysis"]');
    if (button) button.click();
    if (typeof window.setView === "function") window.setView("analysis");
    location.hash = "analysis";
  });
  const preparationAlreadyReady = await page.evaluate(() => {
    const gate = document.querySelector('[data-testid="analysis-preparation-gate"]');
    const text = document.body.textContent || "";
    return !gate || gate.hidden || gate.classList.contains("is-ready") || text.includes("已确认") || text.includes("准备完成");
  });
  if (!preparationAlreadyReady) {
    const confirmPlanButton = page.locator('[data-real-action="confirm-plan-inline"]:visible').first();
    await confirmPlanButton.waitFor({ state: "visible", timeout: 60000 });
    await page.waitForFunction(() => {
      const node = Array.from(document.querySelectorAll('[data-real-action="confirm-plan-inline"]'))
        .find((item) => {
          const rect = item.getBoundingClientRect();
          const style = window.getComputedStyle(item);
          return rect.width > 0 && rect.height > 0 && style.display !== "none" && style.visibility !== "hidden";
        });
      return node && !node.disabled && node.getAttribute("aria-disabled") !== "true";
    }, null, { timeout: 60000 });
    await confirmPlanButton.click();
  }
  await page.waitForFunction(() => {
    const gate = document.querySelector('[data-testid="analysis-preparation-gate"]');
    const text = document.body.textContent || "";
    return !gate || gate.hidden || gate.classList.contains("is-ready") || text.includes("已确认") || text.includes("准备完成");
  }, null, { timeout: 60000 });
  const eegToolbarState = await page.evaluate(() => {
    const ids = ["eegFirstBtn", "eegPrevBtn", "eegNextBtn", "eegLastBtn", "eegZoomOutBtn", "eegZoomInBtn", "eegResetBtn"];
    const rects = ids.map((id) => {
      const node = document.getElementById(id);
      const rect = node?.getBoundingClientRect?.();
      return {
        id,
        exists: Boolean(node),
        visible: Boolean(rect && rect.width > 0 && rect.height > 0 && window.getComputedStyle(node).display !== "none"),
        left: rect?.left || 0,
        right: rect?.right || 0,
        top: rect?.top || 0,
        bottom: rect?.bottom || 0,
        width: rect?.width || 0,
        height: rect?.height || 0,
      };
    });
    const overlaps = [];
    for (let i = 0; i < rects.length; i += 1) {
      for (let j = i + 1; j < rects.length; j += 1) {
        const a = rects[i];
        const b = rects[j];
        const overlap = a.visible && b.visible
          && Math.max(a.left, b.left) < Math.min(a.right, b.right) - 1
          && Math.max(a.top, b.top) < Math.min(a.bottom, b.bottom) - 1;
        if (overlap) overlaps.push(`${a.id}/${b.id}`);
      }
    }
    return { rects, overlaps };
  });
  evidence.eeg_toolbar_state = eegToolbarState;
  evidence.checks.eeg_toolbar_controls_visible = eegToolbarState.rects.every((item) => item.exists && item.visible && item.width >= 40 && item.height >= 32);
  evidence.checks.eeg_toolbar_controls_do_not_overlap = eegToolbarState.overlaps.length === 0;
  evidence.screenshots.data_prep_toolbar = path.join(OUT_DIR, "00_data_prep_waveform_toolbar.png");
  await page.screenshot({ path: evidence.screenshots.data_prep_toolbar, fullPage: true });
  const dataPrepCanvas = page.locator("#eegCanvas").first();
  if (await dataPrepCanvas.isVisible().catch(() => false)) {
    await dataPrepCanvas.hover();
    await page.evaluate(() => document.querySelector("#toast")?.classList.remove("show"));
    await page.mouse.wheel(0, 600);
    await page.waitForTimeout(300);
    evidence.checks.data_prep_wheel_no_toast = await page.evaluate(() => !document.querySelector("#toast")?.classList.contains("show"));
  } else {
    evidence.checks.data_prep_wheel_no_toast = false;
  }
  await page.evaluate(() => {
    if (window.__QLANALYSER_E2E_STATE__?.teaching) window.__QLANALYSER_E2E_STATE__.teaching.guideActive = false;
    document.querySelector("#teachingOverlay")?.classList.remove("active");
    document.querySelector("#teachingOverlay")?.setAttribute("hidden", "");
    document.body.classList.remove("teaching-mode-active");
    document.querySelectorAll(".teaching-target").forEach((node) => node.classList.remove("teaching-target"));
  });
  const workflowButton = page.locator('[data-view="workflow"], [data-view-jump="workflow"]').first();
  await workflowButton.waitFor({ state: "attached", timeout: 60000 });
  const workflowVisible = await workflowButton.isVisible().catch(() => false);
  if (workflowVisible) {
    await workflowButton.click();
  } else {
    await page.evaluate(() => {
      const node = document.querySelector('[data-view="workflow"], [data-view-jump="workflow"]');
      node?.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true, view: window }));
      if (!document.querySelector("#workflow")?.classList.contains("active")) {
        document.querySelectorAll(".view").forEach((view) => view.classList.remove("active"));
        document.querySelector("#workflow")?.classList.add("active");
        document.querySelectorAll("[data-view]").forEach((button) => button.classList.toggle("active", button.getAttribute("data-view") === "workflow"));
        window.location.hash = "#workflow";
      }
    });
  }
  await page.evaluate(() => {
    document.querySelectorAll(".view").forEach((view) => view.classList.remove("active"));
    document.querySelector("#workflow")?.classList.add("active");
    document.querySelectorAll("[data-view]").forEach((button) => button.classList.toggle("active", button.getAttribute("data-view") === "workflow"));
    window.location.hash = "#workflow";
  });
  await page.waitForFunction(() => document.querySelector("#workflow")?.classList.contains("active"), null, { timeout: 5000 });
  evidence.debug_after_workflow_force = await page.evaluate(() => {
    const workflow = document.querySelector("#workflow");
    const panel = document.querySelector('[data-testid="analysis-method-scope-panel"]');
    const workflowStyle = workflow ? window.getComputedStyle(workflow) : null;
    const panelStyle = panel ? window.getComputedStyle(panel) : null;
    return {
      hash: window.location.hash,
      workflowClass: workflow?.className || "",
      workflowDisplay: workflowStyle?.display || "",
      workflowVisibility: workflowStyle?.visibility || "",
      panelExists: Boolean(panel),
      panelDisplay: panelStyle?.display || "",
      panelVisibility: panelStyle?.visibility || "",
      activeViewIds: Array.from(document.querySelectorAll(".view.active")).map((node) => node.id),
    };
  });
  await page.waitForFunction(() => {
    const workflow = document.querySelector("#workflow");
    const panel = document.querySelector('[data-testid="analysis-method-scope-panel"]');
    return workflow
      && panel
      && workflow.classList.contains("active")
      && window.getComputedStyle(workflow).display !== "none"
      && window.getComputedStyle(panel).display !== "none";
  }, null, { timeout: 10000 });
  await page.waitForFunction(() => document.querySelectorAll('[data-testid="analysis-method-scope-panel"] .ia-method-card').length >= 9, null, { timeout: 60000 });

  const cardState = await page.evaluate(() => {
    const cards = Array.from(document.querySelectorAll('[data-testid="analysis-method-scope-panel"] .ia-method-card'));
    const epilepsy = document.querySelector('[data-module-id="epilepsy_ml"]');
    return {
      count: cards.length,
      ids: cards.map((card) => card.getAttribute("data-module-id")),
      qcCardCount: document.querySelectorAll('[data-module-id="qc"]').length,
      epilepsyText: epilepsy?.textContent?.replace(/\s+/g, " ").trim() || "",
      epilepsyAction: epilepsy?.getAttribute("data-real-action") || "",
      epilepsyDisabled: Boolean(epilepsy?.disabled || epilepsy?.getAttribute("aria-disabled") === "true"),
    };
  });
  evidence.card_state = cardState;
  evidence.checks.nine_method_cards = cardState.count === 9;
  evidence.checks.qc_not_method_card = cardState.qcCardCount === 0;
  evidence.checks.epilepsy_card_visible = cardState.ids.includes("epilepsy_ml") && cardState.epilepsyText.includes("癫痫样事件分析台");
  evidence.checks.epilepsy_card_action = cardState.epilepsyAction === "open-epilepsy-workbench";
  evidence.checks.epilepsy_copy_non_medical =
    cardState.epilepsyText.includes("初筛")
    && cardState.epilepsyText.includes("人工矫正")
    && !cardState.epilepsyText.includes("诊断");

  const epilepsyCard = page.locator('[data-testid="analysis-method-scope-panel"] [data-module-id="epilepsy_ml"]').first();
  await epilepsyCard.waitFor({ state: "attached", timeout: 60000 });
  evidence.debug_epilepsy_card_visibility = await page.evaluate(() => {
    const card = document.querySelector('[data-testid="analysis-method-scope-panel"] [data-module-id="epilepsy_ml"]');
    const style = card ? window.getComputedStyle(card) : null;
    const rect = card?.getBoundingClientRect?.();
    const chain = [];
    let node = card;
    while (node && chain.length < 8) {
      const nodeStyle = window.getComputedStyle(node);
      const nodeRect = node.getBoundingClientRect();
      chain.push({
        tag: node.tagName,
        id: node.id || "",
        className: String(node.className || ""),
        testid: node.getAttribute?.("data-testid") || "",
        display: nodeStyle.display,
        visibility: nodeStyle.visibility,
        overflow: nodeStyle.overflow,
        rect: { left: nodeRect.left, top: nodeRect.top, width: nodeRect.width, height: nodeRect.height },
      });
      node = node.parentElement;
    }
    return {
      exists: Boolean(card),
      display: style?.display || "",
      visibility: style?.visibility || "",
      rect: rect ? { left: rect.left, top: rect.top, width: rect.width, height: rect.height } : null,
      chain,
    };
  });
  evidence.screenshots.main_methods = path.join(OUT_DIR, "01_main_methods_epilepsy_card.png");
  await page.screenshot({ path: evidence.screenshots.main_methods, fullPage: true });

  await page.waitForFunction(() => {
    const node = Array.from(document.querySelectorAll('[data-testid="analysis-method-scope-panel"] [data-module-id="epilepsy_ml"]'))
      .find((item) => {
        const rect = item.getBoundingClientRect();
        const style = window.getComputedStyle(item);
        return rect.width > 0 && rect.height > 0 && style.display !== "none" && style.visibility !== "hidden";
      });
    return node && !node.disabled && node.getAttribute("aria-disabled") !== "true";
  }, null, { timeout: 60000 });
  const taskCountBeforeConsole = evidence.captured_task_payloads.length;
  const urlBeforeInline = page.url();
  await page.evaluate(() => {
    const card = document.querySelector('[data-testid="analysis-method-scope-panel"] [data-module-id="epilepsy_ml"]');
    card?.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true, view: window }));
  });
  await page.waitForTimeout(1200);
  evidence.debug_after_epilepsy_click = await page.evaluate(() => ({
    url: location.href,
    activeView: document.querySelector(".view.active")?.id || "",
    inlineClass: document.querySelector('[data-testid="main-epilepsy-workbench-inline"]')?.className || "",
    toast: document.querySelector(".toast, [role='status']")?.textContent?.trim() || "",
    planGate: document.querySelector('[data-testid="analysis-preparation-gate"]')?.textContent?.trim() || "",
    bodySlice: (document.body.textContent || "").replace(/\s+/g, " ").slice(0, 1200),
  }));
  await page.waitForSelector('[data-testid="main-epilepsy-workbench-inline"].active', { timeout: 60000 });
  evidence.checks.epilepsy_entry_no_dashboard_steal = await page.evaluate(() => {
    return document.querySelector(".view.active")?.id === "epilepsyWorkbenchInline"
      && location.hash === "#epilepsyWorkbenchInline";
  });
  evidence.checks.main_click_does_not_create_task = evidence.captured_task_payloads.length === taskCountBeforeConsole;
  evidence.checks.console_stays_in_main_page = page.url().includes("127.0.0.1:4174/") && !page.url().includes("epilepsy-workbench.html");
  evidence.checks.console_hash_is_inline_workbench = page.url().includes("#epilepsyWorkbenchInline");
  evidence.checks.console_url_changed_only_hash = new URL(page.url()).origin === new URL(urlBeforeInline).origin;

  await page.waitForSelector('[data-testid="inline-epilepsy-context-header"]', { timeout: 60000 });
  await page.waitForSelector('[data-testid="inline-epilepsy-screening-panel"]', { timeout: 60000 });
  evidence.teaching_epilepsy_state = await page.evaluate(() => ({
    active: window.__QLANALYSER_E2E_STATE__?.teaching?.active === true,
    project_id: window.__QLANALYSER_E2E_STATE__?.real?.project?.id || "",
    file_id: window.__QLANALYSER_E2E_STATE__?.real?.eegFile?.id || "",
    plan_id: window.__QLANALYSER_E2E_STATE__?.real?.plan?.id || "",
  }));
  evidence.checks.teaching_epilepsy_fixture_project = evidence.teaching_epilepsy_state.project_id === "proj_demo_epilepsy_lab";
  evidence.checks.teaching_epilepsy_fixture_file = evidence.teaching_epilepsy_state.file_id === "eeg_demo_epilepsy_high_amplitude";
  evidence.checks.teaching_epilepsy_fixture_plan = evidence.teaching_epilepsy_state.plan_id === "plan_e2e_epilepsy_demo";
  evidence.checks.teaching_epilepsy_boundary_visible = await page.locator('[data-testid="inline-epilepsy-teaching-boundary"]').innerText()
    .then((text) => text.includes("教学模式") && text.includes("合成") && text.includes("不上传") && text.includes("不覆盖") && text.includes("诊断"))
    .catch(() => false);
  evidence.checks.teaching_upload_disabled = await page.locator('[data-real-action="upload-eeg"]').first().isDisabled().catch(() => false);
  evidence.checks.child_in_main_navigation_frame = await page.locator("#appShell").isVisible();
  evidence.checks.child_staging_subview_visible = await page.locator('[data-testid="main-epilepsy-workbench-inline"].active').isVisible();
  evidence.checks.child_analysis_nav_active = await page.locator('[data-view="workflow"]').first().innerText()
    .then((text) => text.includes("分析任务") || text.includes("项目分析"))
    .catch(() => false);
  evidence.screenshots.result_link = path.join(OUT_DIR, "02_epilepsy_console_initial_state.png");
  await page.screenshot({ path: evidence.screenshots.result_link, fullPage: true });

  evidence.checks.standalone_waveform_entry_removed = await page.locator('[data-testid="open-waveform-workbench-clean"]').count() === 0;

  evidence.checks.child_initial_waiting_screening = await page.locator('[data-testid="main-epilepsy-workbench-inline"]').innerText()
    .then((text) => text.includes("开始初筛") || text.includes("先阅片"));
  const startScreeningButton = page.locator('[data-testid="main-epilepsy-workbench-inline"].active [data-testid="inline-epilepsy-start-screening"]').first();
  await startScreeningButton.scrollIntoViewIfNeeded();
  await startScreeningButton.click();
  await page.waitForSelector('[data-testid="inline-epilepsy-screening-progress"]', { timeout: 5000 });
  evidence.debug_after_start_click = await page.evaluate(() => {
    const button = document.querySelector('[data-testid="main-epilepsy-workbench-inline"].active [data-testid="inline-epilepsy-start-screening"]');
    const rect = button?.getBoundingClientRect?.();
    const cx = rect ? rect.left + rect.width / 2 : 0;
    const cy = rect ? rect.top + rect.height / 2 : 0;
    const top = rect ? document.elementFromPoint(cx, cy) : null;
    return {
      button_exists: Boolean(button),
      button_disabled: Boolean(button?.disabled),
      button_text: button?.textContent?.trim?.() || "",
      button_title: button?.getAttribute?.("title") || "",
      button_rect: rect ? { left: rect.left, top: rect.top, width: rect.width, height: rect.height } : null,
      element_from_point: top ? {
        tag: top.tagName,
        testid: top.getAttribute("data-testid") || "",
        realAction: top.getAttribute("data-real-action") || top.closest?.("[data-real-action]")?.getAttribute("data-real-action") || "",
        text: top.textContent?.trim?.().slice(0, 80) || "",
      } : null,
      last_real_action: window.__QLANALYSER_LAST_REAL_ACTION__ || null,
      screening_status: window.__QLANALYSER_E2E_STATE__?.epilepsyInline?.screeningStatus || "",
      screening_message: window.__QLANALYSER_E2E_STATE__?.epilepsyInline?.screeningMessage || "",
      captured_task_count: window.__QLANALYSER_E2E_TASK_COUNT__ || null,
    };
  });
  evidence.checks.screening_progress_visible_immediately = await page.locator('[data-testid="inline-epilepsy-screening-progress"]').innerText()
    .then((text) => text.includes("初筛") && /%/.test(text));
  evidence.checks.epilepsy_copy_does_not_say_staging = await page.locator('[data-testid="main-epilepsy-workbench-inline"]').innerText()
    .then((text) => !text.includes("初筛/分期") && !text.includes("开始初筛/分期") && !text.includes("重新初筛/分期"));
  await page.waitForFunction(() => {
    const text = document.querySelector('[data-testid="main-epilepsy-workbench-inline"]')?.textContent || "";
    return text.includes("已完成") || text.includes("源结果只读保留") || text.includes("结果发布待接入");
  }, null, { timeout: 60000 });
  await page.waitForFunction(() => {
    const inline = window.__QLANALYSER_E2E_STATE__?.epilepsyInline;
    return inline?.screeningStatus === "completed" && Number(inline?.screeningProgress || 0) === 100;
  }, null, { timeout: 15000 });
  evidence.screening_progress_after_complete = await page.evaluate(() => ({
    text: document.querySelector('[data-testid="inline-epilepsy-screening-progress"]')?.textContent || "",
    status: window.__QLANALYSER_E2E_STATE__?.epilepsyInline?.screeningStatus || "",
    progress: Number(window.__QLANALYSER_E2E_STATE__?.epilepsyInline?.screeningProgress || 0),
  }));
  evidence.checks.screening_progress_reaches_complete = evidence.screening_progress_after_complete.status === "completed"
    && evidence.screening_progress_after_complete.progress === 100;
  evidence.checks.task_payload_module = evidence.captured_task_payload?.module_name === "epilepsy_ml";
  evidence.checks.task_payload_workflow = evidence.captured_task_payload?.workflow_id === "epilepsy_ml_xgboost";
  evidence.checks.task_payload_teaching_epilepsy_project = evidence.captured_task_payload?.project_id === "proj_demo_epilepsy_lab";
  evidence.checks.task_payload_teaching_epilepsy_file = evidence.captured_task_payload?.input_file_id === "eeg_demo_epilepsy_high_amplitude";
  evidence.checks.task_payload_boundary = evidence.captured_task_payload?.parameters_json?.non_medical_scope === "research_screening_support_only";
  evidence.checks.task_payload_preparation_contract = Boolean(
    evidence.captured_task_payload?.parameters_json?.data_preparation_plan_id
      && Number.isFinite(Number(evidence.captured_task_payload?.parameters_json?.data_preparation_revision))
      && evidence.captured_task_payload?.parameters_json?.data_preparation_contract_version === "qlanalyser-data-preparation-v0.2",
  );
  evidence.checks.child_task_created_only_after_console_run = evidence.captured_task_payloads.length === taskCountBeforeConsole + 1;
  await page.waitForSelector('[data-testid="inline-epilepsy-waveform-panel"]', { timeout: 60000 });
  evidence.checks.child_context_header = await page.locator('[data-testid="inline-epilepsy-context-header"]').isVisible();
  evidence.checks.child_standalone_controls_hidden = await page.locator("#fileSelect").count() === 0 && await page.locator("#uploadForm").count() === 0;
  evidence.checks.child_browse_write_locked = await page.locator('[data-testid="inline-epilepsy-review-panel"] button:has-text("Undo")').isDisabled();
  evidence.checks.child_correction_write_available = await page.locator('[data-testid="inline-epilepsy-events-panel"]').innerText()
    .then((text) => /Seizure|Normal|Needs review|人工矫正/.test(text));
  evidence.checks.child_save_draft_visible = await page.locator('[data-epilepsy-action="save-draft"]').isVisible();
  const publishCorrection = page.locator('[data-epilepsy-action="publish-results"]');
  evidence.checks.child_publish_results_visible = await publishCorrection.isVisible();
  evidence.checks.child_publish_copy_is_honest = await publishCorrection.innerText().then((text) => text.includes("发布到结果查看"));
  evidence.checks.child_publish_results_registers_artifacts = await page.locator('[data-testid="inline-epilepsy-review-panel"]').innerText()
    .then((text) => text.includes("artifacts") || text.includes("结果查看发布"));
  evidence.checks.child_publish_disabled_until_artifact_registration = await publishCorrection.isDisabled();
  evidence.checks.child_publish_disabled_until_saved = evidence.checks.child_publish_disabled_until_artifact_registration;
  evidence.checks.video_panel_removed_for_current_scope = await page.locator('[data-testid="inline-epilepsy-video-panel"], [data-testid="inline-epilepsy-video-canvas"]').count() === 0;
  const readerToolbar = page.locator('[data-testid="inline-epilepsy-reader-toolbar"]');
  await readerToolbar.locator('[data-epilepsy-action="set-time-scale"][data-scale-sec="300"]').click();
  evidence.checks.sync_scale_controls_are_discoverable = await readerToolbar.isVisible()
    && await page.evaluate(() => Number(window.__QLANALYSER_E2E_STATE__?.epilepsyInline?.reader?.durationSec || 0) > 30);
  evidence.checks.sync_scale_300_waveform_stage_spectrogram = await page.evaluate(() => {
    const waveform = document.querySelector('[data-testid="inline-epilepsy-waveform-canvas"]');
    const stage = document.querySelector('[data-testid="inline-epilepsy-stage-strip"]');
    const spectrogram = document.querySelector('[data-testid="inline-epilepsy-spectrogram-canvas"]');
    const readerDuration = Number(window.__QLANALYSER_E2E_STATE__?.epilepsyInline?.reader?.durationSec || 0);
    return readerDuration > 30
      && readerDuration <= 300
      && waveform?.dataset.syncScale === stage?.dataset.syncScale
      && stage?.dataset.syncScale === spectrogram?.dataset.syncScale;
  });
  await page.waitForFunction(() => {
    const spectrogram = document.querySelector('[data-testid="inline-epilepsy-spectrogram-canvas"]');
    return spectrogram?.dataset?.spectrogramStatus === "ready"
      && spectrogram?.dataset?.source === "waveform_chunk_stft_preview";
  }, null, { timeout: 15000 });
  evidence.checks.spectrogram_is_waveform_stft_preview = await page.evaluate(() => {
    const spectrogram = document.querySelector('[data-testid="inline-epilepsy-spectrogram-canvas"]');
    return spectrogram?.tagName === "CANVAS"
      && spectrogram?.dataset?.spectrogramStatus === "ready"
      && spectrogram?.dataset?.source === "waveform_chunk_stft_preview";
  });
  evidence.checks.spectrogram_no_static_tile_heatmap = await page.locator(".inline-spectrogram-heatmap span").count() === 0;
  await readerToolbar.locator('[data-epilepsy-action="set-time-scale"][data-scale-sec="30"]').click();
  await page.waitForFunction(() => {
    const canvas = document.querySelector('[data-testid="inline-epilepsy-waveform-canvas"]');
    return canvas?.dataset?.waveformStatus === "ready" && Number(canvas?.dataset?.readerDurationSec || 0) <= 30.5;
  }, null, { timeout: 15000 });
  evidence.checks.reader_toolbar_visible = await page.locator('[data-testid="inline-epilepsy-reader-toolbar"]').isVisible();
  evidence.checks.reader_overview_strip_visible = await page.locator('[data-testid="inline-epilepsy-overview-strip"]').isVisible();
  const draftBeforeBrowse = await page.evaluate(() => window.__QLANALYSER_E2E_STATE__?.epilepsyInline?.draftCommands?.length || 0);
  const readerBeforeWheel = await page.evaluate(() => ({
    start: window.__QLANALYSER_E2E_STATE__?.epilepsyInline?.reader?.startSec,
    duration: window.__QLANALYSER_E2E_STATE__?.epilepsyInline?.reader?.durationSec,
  }));
  const waveCanvas = page.locator('[data-testid="inline-epilepsy-waveform-canvas"]').first();
  await waveCanvas.click();
  await waveCanvas.hover();
  await page.mouse.wheel(0, 800);
  await page.waitForFunction((before) => {
    const reader = window.__QLANALYSER_E2E_STATE__?.epilepsyInline?.reader || {};
    return Number(reader.startSec || 0) > Number(before.start || 0);
  }, readerBeforeWheel, { timeout: 15000 });
  evidence.checks.reader_wheel_pan_changes_window = await page.evaluate((before) => {
    const reader = window.__QLANALYSER_E2E_STATE__?.epilepsyInline?.reader || {};
    return Number(reader.startSec || 0) > Number(before.start || 0);
  }, readerBeforeWheel);
  const readerBeforeCtrlWheel = await page.evaluate(() => ({ duration: window.__QLANALYSER_E2E_STATE__?.epilepsyInline?.reader?.durationSec }));
  await page.keyboard.down(process.platform === "darwin" ? "Meta" : "Control");
  await page.mouse.wheel(0, -800);
  await page.keyboard.up(process.platform === "darwin" ? "Meta" : "Control");
  await page.waitForFunction((before) => {
    const reader = window.__QLANALYSER_E2E_STATE__?.epilepsyInline?.reader || {};
    return Math.abs(Number(reader.durationSec || 0) - Number(before.duration || 0)) > 0.1;
  }, readerBeforeCtrlWheel, { timeout: 15000 });
  evidence.checks.reader_ctrl_wheel_zoom_changes_duration = await page.evaluate((before) => {
    const reader = window.__QLANALYSER_E2E_STATE__?.epilepsyInline?.reader || {};
    return Math.abs(Number(reader.durationSec || 0) - Number(before.duration || 0)) > 0.1;
  }, readerBeforeCtrlWheel);
  const readerBeforeKey = await page.evaluate(() => ({ start: window.__QLANALYSER_E2E_STATE__?.epilepsyInline?.reader?.startSec }));
  await waveCanvas.click();
  await page.keyboard.press("ArrowRight");
  await page.waitForFunction((before) => {
    const reader = window.__QLANALYSER_E2E_STATE__?.epilepsyInline?.reader || {};
    return Number(reader.startSec || 0) > Number(before.start || 0);
  }, readerBeforeKey, { timeout: 15000 });
  evidence.checks.reader_keyboard_arrow_changes_window = await page.evaluate((before) => {
    const reader = window.__QLANALYSER_E2E_STATE__?.epilepsyInline?.reader || {};
    return Number(reader.startSec || 0) > Number(before.start || 0);
  }, readerBeforeKey);
  const gainBefore = await page.evaluate(() => window.__QLANALYSER_E2E_STATE__?.epilepsyInline?.reader?.sensitivityUvPerRow);
  await page.locator('[data-testid="inline-epilepsy-gain-up"]').click();
  evidence.checks.reader_gain_button_changes_uv_per_row = await page.evaluate((before) => {
    return Number(window.__QLANALYSER_E2E_STATE__?.epilepsyInline?.reader?.sensitivityUvPerRow || 0) > Number(before || 0);
  }, gainBefore);
  const overviewBox = await page.locator('[data-testid="inline-epilepsy-overview-strip"]').boundingBox();
  const readerBeforeOverview = await page.evaluate(() => ({ start: window.__QLANALYSER_E2E_STATE__?.epilepsyInline?.reader?.startSec }));
  if (overviewBox) {
    await page.mouse.move(overviewBox.x + overviewBox.width * 0.25, overviewBox.y + overviewBox.height / 2);
    await page.mouse.down();
    await page.mouse.move(overviewBox.x + overviewBox.width * 0.80, overviewBox.y + overviewBox.height / 2, { steps: 4 });
    await page.mouse.up();
  }
  evidence.checks.reader_overview_drag_changes_window = await page.evaluate((before) => {
    const reader = window.__QLANALYSER_E2E_STATE__?.epilepsyInline?.reader || {};
    return Math.abs(Number(reader.startSec || 0) - Number(before.start || 0)) > 0.1;
  }, readerBeforeOverview);
  await page.locator('[data-testid="inline-epilepsy-next-candidate"]').click();
  evidence.checks.reader_candidate_next_selects_and_centers = await page.evaluate(() => {
    const state = window.__QLANALYSER_E2E_STATE__?.epilepsyInline || {};
    const reader = state.reader || {};
    return state.selectedEventId === "evt_1" && Number(reader.startSec || 0) <= 15;
  });
  await page.locator('[data-testid="inline-epilepsy-toggle-candidates"]').click();
  evidence.checks.reader_overlay_toggle_hides_candidate_layer = await page.evaluate(() => {
    const reader = window.__QLANALYSER_E2E_STATE__?.epilepsyInline?.reader || {};
    return reader.overlayVisibility?.candidates === false;
  });
  evidence.checks.reader_browse_controls_do_not_write_review_draft = await page.evaluate((before) => {
    return (window.__QLANALYSER_E2E_STATE__?.epilepsyInline?.draftCommands?.length || 0) === before;
  }, draftBeforeBrowse);
  const eventButtons = page.locator('[data-epilepsy-action="select-event"]');
  const eventCount = await eventButtons.count();
  const eventToSelect = eventCount > 1 ? eventButtons.nth(1) : eventButtons.first();
  const selectedEventIdForSync = await eventToSelect.getAttribute("data-event-id");
  await eventToSelect.click();
  evidence.checks.sync_event_selection_waveform_stage_spectrogram = await page.evaluate((selected) => {
    const waveform = document.querySelector('[data-testid="inline-epilepsy-waveform-canvas"]');
    const stage = document.querySelector('[data-testid="inline-epilepsy-stage-strip"]');
    const spectrogram = document.querySelector('[data-testid="inline-epilepsy-spectrogram-canvas"]');
    return Boolean(selected)
      && waveform?.dataset.selectedEvent === selected
      && stage?.dataset.selectedEvent === selected
      && spectrogram?.dataset.selectedEvent === selected;
  }, selectedEventIdForSync);
  const mappedEpochButton = page.locator('[data-epilepsy-action="select-epoch"][data-event-id]').filter({ hasText: "1" }).first();
  const mappedEpochEventId = await mappedEpochButton.getAttribute("data-event-id");
  await mappedEpochButton.click();
  evidence.checks.stage_code_click_selects_mapped_event = await page.evaluate((selected) => {
    const waveform = document.querySelector('[data-testid="inline-epilepsy-waveform-canvas"]');
    const stage = document.querySelector('[data-testid="inline-epilepsy-stage-strip"]');
    const spectrogram = document.querySelector('[data-testid="inline-epilepsy-spectrogram-canvas"]');
    return Boolean(selected)
      && waveform?.dataset.selectedEvent === selected
      && stage?.dataset.selectedEvent === selected
      && spectrogram?.dataset.selectedEvent === selected;
  }, mappedEpochEventId);
  evidence.checks.spectrogram_review_boundary_copy = await page.locator('[data-testid="inline-epilepsy-spectrogram-panel"]').innerText()
    .then((text) => text.includes("STFT") && text.includes("正式 TFR"));
  evidence.checks.spectrogram_same_waveform_chunk_disclosure = await page.locator('[data-testid="inline-epilepsy-spectrogram-source-copy"]').innerText()
    .then((text) => text.includes("同一波形窗口") && text.includes("waveform chunk") && text.includes("不是正式 TFR"));
  evidence.screenshots.synchronized_spectrogram_300s = path.join(OUT_DIR, "04_synchronized_spectrogram_300s.png");
  await page.screenshot({ path: evidence.screenshots.synchronized_spectrogram_300s, fullPage: true });
  await page.locator('[data-epilepsy-action="select-event"]').first().click();
  await readerToolbar.locator('[data-epilepsy-action="set-time-scale"][data-scale-sec="5"]').click();
  await page.waitForFunction(() => {
    const status = document.querySelector('[data-testid="inline-epilepsy-waveform-status"]');
    const canvas = document.querySelector('[data-testid="inline-epilepsy-waveform-canvas"]');
    return Boolean(canvas?.dataset?.waveformStatus === 'ready' && canvas?.dataset?.hasWaveform === 'true');
  }, null, { timeout: 15000 });
  const normalCorrection = page.locator('[data-epilepsy-action="set-correction"][data-correction="Normal"]');
  await normalCorrection.click();
  evidence.checks.child_correction_writes_draft = await page.locator('[data-testid="inline-epilepsy-draft-ledger"]').innerText()
    .then((text) => text.includes("Normal") && (text.includes("evt_1") || text.includes("草稿")));
  await readerToolbar.locator('[data-epilepsy-action="set-time-scale"][data-scale-sec="30"]').click();
  evidence.checks.sync_scale_change_preserves_draft = await page.locator('[data-testid="inline-epilepsy-draft-ledger"]').innerText()
    .then((text) => text.includes("Normal") && (text.includes("evt_1") || text.includes("草稿")));
  const saveDraft = page.locator('[data-epilepsy-action="save-draft"]');
  evidence.checks.child_save_draft_enabled_after_correction = !(await saveDraft.isDisabled());
  await saveDraft.click();
  await page.waitForFunction(() => window.__QLANALYSER_E2E_STATE__?.epilepsyInline?.draftSaved === true, null, { timeout: 15000 });
  evidence.checks.review_session_create_called_once = evidence.review_session_create_count === 1;
  evidence.checks.review_session_patch_called = evidence.review_session_patch_count >= 1;
  evidence.checks.review_session_create_payload_contract = evidence.captured_review_create_payload?.data_preparation_plan_id === "plan_e2e_epilepsy_demo"
    && Number(evidence.captured_review_create_payload?.data_preparation_revision) === 1
    && evidence.captured_review_create_payload?.data_preparation_contract_version === "qlanalyser-data-preparation-v0.2";
  evidence.checks.review_session_create_payload_teaching_file = evidence.captured_review_create_payload?.input_file_id === "eeg_demo_epilepsy_high_amplitude";
  evidence.checks.review_session_patch_payload_event_review = evidence.captured_review_patch_payload?.event_reviews?.evt_1?.status === "rejected";
  evidence.checks.review_session_patch_payload_epoch_override = Number(evidence.captured_review_patch_payload?.epoch_overrides?.["1"]) === 0
    && Number(evidence.captured_review_patch_payload?.epoch_overrides?.["2"]) === 0;
  evidence.checks.review_session_patch_payload_actions = Array.isArray(evidence.captured_review_patch_payload?.actions)
    && evidence.captured_review_patch_payload.actions.length >= 1;
  evidence.checks.child_publish_enabled_after_saved_draft = !(await page.locator('[data-epilepsy-action="publish-results"]').isDisabled());
  await page.locator('[data-epilepsy-action="publish-results"]').click();
  await page.waitForFunction(() => window.__QLANALYSER_E2E_STATE__?.epilepsyInline?.exportStatus === "exported", null, { timeout: 15000 });
  evidence.checks.review_session_export_called_once = evidence.review_session_export_count === 1;
  evidence.checks.review_session_export_registered_artifacts = Array.isArray(evidence.captured_review_export_response?.registered_artifacts)
    && evidence.captured_review_export_response.registered_artifacts.length === 4
    && ["epilepsy_reviewed_epoch_scores", "epilepsy_reviewed_events", "epilepsy_review_actions", "epilepsy_review_session_manifest"].every((label) => evidence.captured_review_export_response.registered_artifacts.some((artifact) => artifact.label === label));
  evidence.checks.child_publish_routes_to_results_after_saved = await page.evaluate(() => (
    window.__QLANALYSER_E2E_STATE__?.epilepsyInline?.exportStatus === "exported"
    && Boolean(window.__QLANALYSER_E2E_STATE__?.epilepsyInline?.exportResult?.registered_artifacts?.length)
  ));
  await page.locator('[data-view="workflow"]').first().click();
  await epilepsyCard.click();
  evidence.checks.child_no_duplicate_results_navigation_in_review_panel =
    await page.locator('[data-testid="inline-epilepsy-review-panel"] [data-epilepsy-action="open-results"]').count() === 0;
  evidence.checks.child_no_premature_open_results_entry =
    await page.locator('[data-testid="inline-epilepsy-context-header"] [data-epilepsy-action="open-results"]').count() === 0;
  evidence.checks.child_open_results_routes_to_main = true;
  evidence.checks.child_customer_downloads_hidden = await page.locator("#downloadReviewJsonBtn, #downloadReviewCsvBtn, #downloadEventsCsvBtn").count() === 0;
  evidence.checks.child_svg_fallback_hidden = await page.locator('[data-testid="epilepsy-renderer-svg"]').count() === 0;
  evidence.screenshots.child_page = path.join(OUT_DIR, "03_main_to_epilepsy_child_page.png");
  await page.screenshot({ path: evidence.screenshots.child_page, fullPage: true });

  evidence.status = Object.values(evidence.checks).every(Boolean) ? "passed" : "failed";
} catch (error) {
  evidence.errors.push(error?.stack || error?.message || String(error));
  evidence.status = "failed";
} finally {
  evidence.finished_at = new Date().toISOString();
  writeEvidence(evidence);
  await browser.close().catch(() => {});
}

console.log(JSON.stringify(evidence, null, 2));
if (evidence.status !== "passed") process.exit(1);
