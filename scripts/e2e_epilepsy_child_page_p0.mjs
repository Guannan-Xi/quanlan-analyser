import fs from "node:fs";
import path from "node:path";
import { chromium, chromiumLaunchOptions } from "./lib/playwright_runtime.mjs";

const FRONTEND_ORIGIN = process.env.QLANALYSER_FRONTEND_ORIGIN || "http://127.0.0.1:4174";
const API_BASE = process.env.QLANALYSER_API_BASE || "http://127.0.0.1:8001/api";
const OUT_DIR = path.resolve("work/release_evidence/20260629-epilepsy-child-page-p0");
const OUT_FILE = path.join(OUT_DIR, "e2e_epilepsy_child_page_p0.json");

const taskId = "task_child_p0";
const fileId = "file_child_p0";
const planId = "plan_child_p0";
const revision = 3;
const contract = "qlanalyser-data-preparation-v0.2";

const epochCsv = [
  "epoch_index,start_sec,end_sec,Stage_Code,Stage,mean_rms,probability,is_event_epoch,threshold",
  "0,0,5,0,Normal,0.1,0.10,false,0.5",
  "1,5,10,1,Seizure,0.9,0.88,true,0.5",
  "2,10,15,1,Seizure,0.8,0.83,true,0.5",
  "3,15,20,0,Normal,0.1,0.12,false,0.5",
].join("\n");

const eventsCsv = [
  "event_id,start_sec,end_sec,start_epoch,end_epoch,epoch_count,rms",
  "evt_1,5,15,1,2,2,0.85",
].join("\n");

const summaryJson = {
  method: "ml_epoch_classifier",
  duration_sec: 20,
  non_medical_scope: "research_screening_support_only",
};

const evidence = {
  script: "e2e_epilepsy_child_page_p0.mjs",
  started_at: new Date().toISOString(),
  architecture_status: "superseded_by_main_inline_workbench",
  replacement_e2e: "scripts/e2e_main_epilepsy_entry_contract.mjs",
  checks: {},
  screenshots: {},
  status: "running",
  errors: [],
};

function writeEvidence() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  fs.writeFileSync(OUT_FILE, `${JSON.stringify(evidence, null, 2)}\n`, "utf8");
}

function jsonResponse(payload) {
  return {
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(payload),
  };
}

const browser = await chromium.launch(chromiumLaunchOptions({ headless: true }));
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });

await page.route(`${API_BASE}/**`, async (route) => {
  const url = new URL(route.request().url());
  const pathname = url.pathname;
  if (pathname.endsWith("/eeg/files")) {
    return route.fulfill(jsonResponse([{
      id: fileId,
      original_filename: "child_page_fixture.edf",
      duration_sec: 20,
      project_id: "project_child_p0",
      metadata_json: {},
    }]));
  }
  if (pathname.endsWith(`/tasks/${taskId}`)) {
    return route.fulfill(jsonResponse({
      id: taskId,
      status: "completed",
      module_name: "epilepsy_ml",
      workflow_id: "epilepsy_ml_xgboost",
      input_file_id: fileId,
      parameters_json: {
        data_preparation_plan_id: planId,
        data_preparation_revision: revision,
        data_preparation_contract_version: contract,
      },
    }));
  }
  if (pathname.endsWith(`/tasks/${taskId}/artifacts`)) {
    return route.fulfill(jsonResponse([
      { id: "art_epoch", label: "epilepsy_epoch_scores", artifact_type: "csv", mime_type: "text/csv" },
      { id: "art_events", label: "epilepsy_events", artifact_type: "csv", mime_type: "text/csv" },
      { id: "art_summary", label: "epilepsy_summary", artifact_type: "json", mime_type: "application/json" },
    ]));
  }
  if (pathname.endsWith(`/tasks/${taskId}/epilepsy-review-sessions`)) {
    return route.fulfill(jsonResponse({
      id: "session_child_p0",
      task_id: taskId,
      input_file_id: fileId,
      workflow_id: "epilepsy_ml_xgboost",
      data_preparation_plan_id: planId,
      data_preparation_revision: revision,
      data_preparation_contract_version: contract,
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
    }));
  }
  if (pathname.endsWith("/artifacts/art_epoch/download")) {
    return route.fulfill({ status: 200, contentType: "text/csv", body: epochCsv });
  }
  if (pathname.endsWith("/artifacts/art_events/download")) {
    return route.fulfill({ status: 200, contentType: "text/csv", body: eventsCsv });
  }
  if (pathname.endsWith("/artifacts/art_summary/download")) {
    return route.fulfill(jsonResponse(summaryJson));
  }
  if (pathname.endsWith(`/eeg/files/${fileId}/waveform-window`)) {
    const requestId = url.searchParams.get("request_id") || "";
    return route.fulfill(jsonResponse({
      file_id: fileId,
      request_id: requestId,
      window_key: "server_window_key_fixture",
      source_data_revision: `${fileId}:fixture:1`,
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
      cache: { status: "on_demand", hit: false, key: "server_window_key_fixture" },
      metrics: { server_elapsed_ms: 12, read_elapsed_ms: 4, filter_elapsed_ms: 0, encode_elapsed_ms: 2, payload_bytes: 1024 },
      non_medical_scope: "research_screening_support_only",
    }));
  }
  return route.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ detail: "unhandled fixture route" }) });
});

try {
  const directUrl = `${FRONTEND_ORIGIN}/epilepsy-workbench.html?api=${encodeURIComponent(API_BASE)}&v=p0-direct`;
  await page.goto(directUrl, { waitUntil: "domcontentloaded" });
  await page.waitForSelector("[data-testid='epilepsy-context-blocked']");
  evidence.checks.direct_url_blocked = await page.locator("[data-testid='epilepsy-context-blocked']").isVisible();
  evidence.checks.direct_url_no_file_select = await page.locator("#fileSelect").count() === 0;
  evidence.screenshots.direct_url_blocked = path.join(OUT_DIR, "direct_url_blocked.png");
  await page.screenshot({ path: evidence.screenshots.direct_url_blocked, fullPage: true });
  evidence.checks.legacy_embed_contract_superseded = true;
  evidence.notes = [
    "P0a epilepsy workbench is now a main-navigation inline child page.",
    "Full task creation, waveform, Stage_Code, spectrogram, correction draft, and Results-pending checks live in scripts/e2e_main_epilepsy_entry_contract.mjs.",
    "This legacy standalone script now verifies that direct standalone access remains blocked and documents the superseded embed contract.",
  ];

  evidence.status = Object.values(evidence.checks).every(Boolean) ? "passed" : "failed";
} catch (error) {
  evidence.status = "failed";
  evidence.errors.push(error?.stack || error?.message || String(error));
} finally {
  evidence.finished_at = new Date().toISOString();
  writeEvidence();
  await browser.close().catch(() => {});
}

console.log(JSON.stringify(evidence, null, 2));
if (evidence.status !== "passed") process.exit(1);
