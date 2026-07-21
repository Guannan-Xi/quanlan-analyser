import fs from "node:fs";
import path from "node:path";
import { chromium, chromiumLaunchOptions, classifyAcceptanceFailure } from "./lib/playwright_runtime.mjs";

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1")), "..");
const FRONTEND_BASE = process.env.QLANALYSER_LAB_EPILEPSY_FRONTEND_BASE || "http://127.0.0.1:4176";
const API_BASE = process.env.QLANALYSER_LAB_EPILEPSY_API_BASE || "http://127.0.0.1:8001/api";
const RECORD_ID = process.env.QLANALYSER_LAB_EPILEPSY_RECORD_ID || "he-105";
const RUN_ID = new Date().toISOString().replace(/[-:T.Z]/g, "").slice(0, 14);
const OUT_DIR = process.env.QLANALYSER_LAB_EPILEPSY_BROWSER_EVIDENCE_DIR
  || path.join(ROOT, "work", "release_evidence", "lab_epilepsy_full_flow_browser", RUN_ID);
const EVIDENCE_PATH = path.join(OUT_DIR, "browser_e2e_evidence.json");
const STORAGE_KEYS = [
  "qlanalyser.epilepsy.full_flow.latest",
  "qlanalyser.epilepsy.review_preview.latest",
];

function ensure(condition, message, details = {}) {
  if (!condition) {
    const error = new Error(message);
    error.details = details;
    throw error;
  }
}

function fullFlowUrl() {
  const url = new URL("/epilepsy-full-flow-preview.html", FRONTEND_BASE);
  url.searchParams.set("api", API_BASE);
  url.searchParams.set("v", `browser-e2e-${RUN_ID}`);
  return url.toString();
}

async function screenshot(page, evidence, name, fullPage = true) {
  const file = path.join(OUT_DIR, `${name}.png`);
  await page.screenshot({ path: file, fullPage, timeout: 20000 });
  evidence.screenshots[name] = file;
}

async function readTimes(scope) {
  return {
    start: Number(await scope.locator("#startInput").inputValue()),
    end: Number(await scope.locator("#endInput").inputValue()),
  };
}

async function dragBy(page, selector, dx, dy = 0) {
  const locator = page.locator(selector);
  await dragLocatorBy(page, locator, dx, dy);
}

async function dragLocatorBy(page, locator, dx, dy = 0) {
  await locator.waitFor({ state: "visible", timeout: 30000 });
  const box = await locator.boundingBox();
  ensure(box, "Cannot drag missing element.");
  const x = box.x + box.width / 2;
  const y = box.y + box.height / 2;
  await page.mouse.move(x, y);
  await page.mouse.down();
  await page.mouse.move(x + dx, y + dy, { steps: 12 });
  await page.mouse.up();
  await page.waitForTimeout(250);
}

async function saveDownload(download, filenamePrefix) {
  const suggested = download.suggestedFilename();
  const file = path.join(OUT_DIR, `${filenamePrefix}_${suggested}`);
  await download.saveAs(file);
  return file;
}

async function assertApiHealth(evidence) {
  const healthUrl = `${API_BASE.replace(/\/$/, "")}/health`;
  const response = await fetch(healthUrl);
  evidence.serviceHealth = { url: healthUrl, status: response.status };
  ensure(response.ok, `Backend health check failed: ${response.status}`);
}

async function main() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const evidence = {
    schema_version: "qlanalyser.lab_epilepsy_full_flow_browser_e2e.v1",
    run_id: RUN_ID,
    status: "running",
    frontend_url: fullFlowUrl(),
    api_base_url: API_BASE,
    record_id: RECORD_ID,
    screenshots: {},
    downloads: {},
    requests: [],
    responses: [],
    console: [],
    checks: {},
  };

  await assertApiHealth(evidence);

  const browser = await chromium.launch(chromiumLaunchOptions({ headless: true }));
  const page = await browser.newPage({ viewport: { width: 1440, height: 1200 }, acceptDownloads: true });
  page.on("console", (message) => {
    if (["error", "warning"].includes(message.type())) {
      evidence.console.push({ type: message.type(), text: message.text() });
    }
  });
  page.on("request", (request) => {
    if (request.url().includes("/api/")) {
      evidence.requests.push({ method: request.method(), url: request.url(), body: request.postData() || "" });
    }
  });
  page.on("response", (response) => {
    if (response.url().includes("/api/")) {
      evidence.responses.push({ status: response.status(), method: response.request().method(), url: response.url() });
    }
  });
  page.on("pageerror", (error) => {
    evidence.console.push({ type: "pageerror", text: String(error?.message || error) });
  });

  try {
    await page.goto(fullFlowUrl(), { waitUntil: "domcontentloaded", timeout: 60000 });
    await page.evaluate((keys) => {
      for (const key of keys) {
        window.localStorage.removeItem(key);
        window.sessionStorage.removeItem(key);
      }
    }, STORAGE_KEYS);
    await page.reload({ waitUntil: "domcontentloaded", timeout: 60000 });
    await page.waitForSelector('[data-testid="epilepsy-full-flow-preview"]', { timeout: 30000 });
    await page.waitForSelector(`#sampleGrid [data-record-id="${RECORD_ID}"]`, { timeout: 60000 });
    await page.click(`#sampleGrid [data-record-id="${RECORD_ID}"]`);
    await screenshot(page, evidence, "01_full_flow_loaded", false);

    const preflightResponse = page.waitForResponse(
      (response) => response.url().includes(`/lab/epilepsy-full-flow/records/${RECORD_ID}/preflight`) && response.status() < 400,
      { timeout: 60000 },
    );
    await page.click("#runPreflightBtn");
    const preflight = await (await preflightResponse).json();
    evidence.preflight = {
      sfreq: preflight.sfreq,
      duration_sec: preflight.duration_sec,
      channel_count: preflight.channel_count,
    };
    await page.waitForFunction(() => document.querySelector("#contextQc")?.textContent?.includes("已完成"), null, { timeout: 30000 });

    const candidatesResponse = page.waitForResponse(
      (response) => response.url().includes(`/lab/epilepsy-full-flow/records/${RECORD_ID}/candidates`)
        && response.request().method() === "POST",
      { timeout: 120000 },
    );
    await page.click("#generateCandidatesBtn");
    const candidatesRawResponse = await candidatesResponse;
    const candidatesRawText = await candidatesRawResponse.text();
    ensure(candidatesRawResponse.ok(), `Candidate generation failed: ${candidatesRawResponse.status()}`, {
      status: candidatesRawResponse.status(),
      body: candidatesRawText.slice(0, 2000),
    });
    const candidatePackage = JSON.parse(candidatesRawText);
    evidence.candidates = {
      count: candidatePackage.candidates?.length || 0,
      source: candidatePackage.candidate_source,
      algorithm_status: candidatePackage.algorithm_status,
      fallback_reason: candidatePackage.fallback_reason || "",
    };
    ensure(evidence.candidates.count > 0, "No candidates generated from HE sample.");
    ensure(evidence.candidates.source === "bounded_full_record_window_scan_rms_ptp_v1", "Candidate source is not the real bounded EDF scan.", evidence.candidates);
    ensure(!evidence.candidates.fallback_reason, "Candidate generation used a fallback.", evidence.candidates);
    ensure(!String(evidence.candidates.algorithm_status || "").toLowerCase().includes("fallback"), "Candidate algorithm status indicates fallback.", evidence.candidates);
    await page.waitForFunction(() => document.body.innerText.includes("HE-105-SCAN"), null, { timeout: 60000 });
    await page.waitForFunction(() => document.body.innerText.includes("候选包范围"), null, { timeout: 30000 });
    await screenshot(page, evidence, "02_candidates_generated", false);

    const candidateSummaryText = await page.locator("body").innerText();
    ensure(
      candidateSummaryText.includes("不代表全记录事件总数") || candidateSummaryText.includes("不是全记录负荷估计"),
      "Candidate summary does not explain bounded scan limitations.",
    );
    await page.click('[data-step="review"]');
    await page.waitForFunction(() => document.body.innerText.includes("本页复核区") || document.body.innerText.includes("复核区已并入全流程"), null, { timeout: 30000 });
    const fullFlowText = await page.locator("body").innerText();
    ensure(fullFlowText.includes("本页复核区") || fullFlowText.includes("复核区已并入全流程"), "Full-flow review step does not expose the embedded review area.");
    ensure(!fullFlowText.includes("全流程页只做候选包交接"), "Full-flow review step still describes review as a handoff-only page.");
    ensure(!fullFlowText.includes("填充预览复核"), "Full-flow review step still exposes a demo-fill action.");
    ensure(await page.locator('[data-flow-status]').count() === 0, "Full-flow page still exposes inline review decision buttons.");
    ensure(await page.locator("#reviewNoteInput").count() === 0, "Full-flow page still exposes inline review note input.");
    await page.locator("#reviewWorkbenchFrame").waitFor({ state: "visible", timeout: 30000 });
    evidence.reviewHandoff = {
      has_refresh_button: await page.locator("#openReviewHandoffBtn").count() > 0,
      has_embedded_frame: await page.locator("#reviewWorkbenchFrame").count() > 0,
      embedded_frame_src: await page.locator("#reviewWorkbenchFrame").getAttribute("src"),
      inline_decision_controls: await page.locator('[data-flow-status]').count(),
      inline_note_controls: await page.locator("#reviewNoteInput").count(),
    };
    ensure(evidence.reviewHandoff.embedded_frame_src?.includes("embed=1"), "Embedded review frame did not load in embed mode.", evidence.reviewHandoff);
    await screenshot(page, evidence, "03_review_handoff", false);

    await page.click("#openReviewHandoffBtn");
    const reviewFrame = page.frameLocator("#reviewWorkbenchFrame");
    await reviewFrame.locator('[data-testid="epilepsy-review-preview"]').waitFor({ state: "visible", timeout: 30000 });
    await reviewFrame.locator("#candidateList [data-candidate-id]").first().waitFor({ state: "visible", timeout: 30000 });
    const candidateSelector = '#candidateList [data-candidate-id="HE-105-SCAN-003"]';
    ensure(await reviewFrame.locator(candidateSelector).count(), "Embedded review frame did not receive scan candidates from full-flow handoff.");
    await reviewFrame.locator(candidateSelector).click();
    await reviewFrame.locator("#eventBand").waitFor({ state: "visible", timeout: 30000 });
    const beforeMove = await readTimes(reviewFrame);
    await reviewFrame.locator('[data-status="kept"]').click();
    await dragLocatorBy(page, reviewFrame.locator("#eventBand"), 70);
    const afterMove = await readTimes(reviewFrame);
    ensure(afterMove.start !== beforeMove.start && afterMove.end !== beforeMove.end, "Whole segment drag did not move both boundaries.", { beforeMove, afterMove });
    ensure(Math.abs((afterMove.end - afterMove.start) - (beforeMove.end - beforeMove.start)) < 0.2, "Whole segment drag changed duration.", { beforeMove, afterMove });

    await dragLocatorBy(page, reviewFrame.locator("#startHandle"), 28);
    const afterStartHandle = await readTimes(reviewFrame);
    ensure(afterStartHandle.start > afterMove.start && Math.abs(afterStartHandle.end - afterMove.end) < 0.2, "Start handle did not adjust start only.", { afterMove, afterStartHandle });
    await dragLocatorBy(page, reviewFrame.locator("#endHandle"), 28);
    const afterEndHandle = await readTimes(reviewFrame);
    ensure(afterEndHandle.end > afterStartHandle.end && Math.abs(afterEndHandle.start - afterStartHandle.start) < 0.2, "End handle did not adjust end only.", { afterStartHandle, afterEndHandle });
    evidence.reviewDrag = { beforeMove, afterMove, afterStartHandle, afterEndHandle };
    await screenshot(page, evidence, "03_review_dragged", false);

    const reviewSessionResponse = page.waitForResponse(
      (response) => response.url().includes("/lab/epilepsy-full-flow/review-sessions")
        && response.request().method() === "POST"
        && response.status() < 400,
      { timeout: 60000 },
    );
    const [reviewSessionRawResponse] = await Promise.all([
      reviewSessionResponse,
      reviewFrame.locator("#reportPreviewBtn").click(),
    ]);
    evidence.backendReviewSessionResponse = {
      status: reviewSessionRawResponse.status(),
      url: reviewSessionRawResponse.url(),
    };
    const reviewSession = await page.evaluate(() => {
      const payload = JSON.parse(localStorage.getItem("qlanalyser.epilepsy.review_preview.latest") || "{}");
      return payload.backend_review_session || {};
    });
    evidence.backendReviewSession = reviewSession;
    ensure(Boolean(reviewSession.session_id), "Backend review session was not created.");
    const exportProbeResponse = await fetch(`${API_BASE}/lab/epilepsy-full-flow/review-sessions/${encodeURIComponent(reviewSession.session_id)}/exports`, { method: "POST" });
    const reportProbeResponse = await fetch(`${API_BASE}/lab/epilepsy-full-flow/review-sessions/${encodeURIComponent(reviewSession.session_id)}/report`);
    ensure(exportProbeResponse.ok, `Backend export probe failed: ${exportProbeResponse.status}`);
    ensure(reportProbeResponse.ok, `Backend report probe failed: ${reportProbeResponse.status}`);
    const backendExportProbe = await exportProbeResponse.json();
    const backendReportProbe = await reportProbeResponse.json();
    evidence.backendExportProbe = {
      schema_version: backendExportProbe.schema_version,
      session_id: backendExportProbe.session_id,
      export_source: backendExportProbe.export_source,
      evidence_ready: backendExportProbe.evidence_ready,
      manifest_hash: backendExportProbe.manifest?.manifest_hash,
    };
    evidence.backendReportProbe = {
      schema_version: backendReportProbe.schema_version,
      export_source: backendReportProbe.export_source,
      evidence_ready: backendReportProbe.evidence_ready,
      figure_evidence_ready: backendReportProbe.report_readiness?.figure_evidence_ready,
    };
    ensure(backendExportProbe.export_source === "backend_review_session_export", "Backend export probe did not come from backend export.", backendExportProbe);
    ensure(backendExportProbe.session_id === reviewSession.session_id, "Backend export session mismatch.", backendExportProbe);
    ensure(backendExportProbe.evidence_ready === true, "Backend export evidence is not ready.", backendExportProbe.manifest);
    ensure(backendReportProbe.report_readiness?.figure_evidence_ready === true, "Backend report figure evidence is not ready.", backendReportProbe.report_readiness);

    await page.waitForSelector('[data-testid="epilepsy-full-flow-preview"]', { timeout: 30000 });
    await page.waitForFunction(() => document.querySelector("#exportReportJsonBtn") && !document.querySelector("#exportReportJsonBtn").disabled, null, { timeout: 30000 });
    const reportText = await page.locator("body").innerText();
    ensure(reportText.includes("HE-105-SCAN-003"), "Report page does not show adjusted candidate.");
    ensure(reportText.includes("暂列入复核草稿") || reportText.includes("纳入草稿候选"), "Report page does not show confirmed draft status.");
    evidence.reportExportGate = await page.evaluate(() => {
      const button = document.querySelector("#exportReportJsonBtn");
      let payload = {};
      try {
        payload = JSON.parse(localStorage.getItem("qlanalyser.epilepsy.review_preview.latest") || "{}");
      } catch {
        payload = {};
      }
      const firstEvent = Array.isArray(payload.reviewed_events) ? payload.reviewed_events[0] : null;
      return {
        disabled: Boolean(button?.disabled),
        title: button?.title || "",
        text: button?.innerText || "",
        has_backend_review_session: Boolean(payload.backend_review_session?.session_id),
        reviewed_event_count: Array.isArray(payload.reviewed_events) ? payload.reviewed_events.length : 0,
        first_evidence_window: firstEvent?.evidence_window || null,
      };
    });
    ensure(!evidence.reportExportGate.disabled, "Report export button is disabled before backend download.", evidence.reportExportGate);
    await screenshot(page, evidence, "04_report_ready", false);

    const [reportDownload] = await Promise.all([
      page.waitForEvent("download", { timeout: 30000 }),
      page.click("#exportReportJsonBtn"),
    ]);
    evidence.downloads.report_json = await saveDownload(reportDownload, "report");
    const reportJsonText = fs.readFileSync(evidence.downloads.report_json, "utf8");
    const reportJson = JSON.parse(reportJsonText);
    evidence.downloadedReportSummary = {
      schema_version: reportJson.schema_version,
      export_source: reportJson.export_source,
      session_id: reportJson.session_id,
      evidence_ready: reportJson.evidence_ready,
      manifest_hash: reportJson.manifest?.manifest_hash,
    };
    ensure(reportJson.non_medical_scope === "research_screening_support_only" || reportJsonText.includes("科研筛查"), "Report export missing research boundary.", reportJson);
    ensure(reportJson.export_source === "backend_review_session_export", "Downloaded report JSON did not come from backend export.", reportJson);
    ensure(reportJson.session_id === reviewSession.session_id, "Downloaded report JSON session mismatch.", reportJson);
    ensure(reportJson.evidence_ready === true, "Downloaded report JSON evidence_ready is not true.", reportJson);
    ensure(reportJson.manifest?.schema_version === "qlanalyser.epilepsy.review_export_manifest.v1", "Downloaded report JSON missing export manifest.", reportJson.manifest);
    ensure(reportJson.qc_manifest?.schema_version === "qlanalyser.epilepsy.qc_manifest.v1", "Downloaded report JSON missing QC manifest.", reportJson.qc_manifest);
    ensure(Array.isArray(reportJson.event_evidence_manifest) && reportJson.event_evidence_manifest.length > 0, "Downloaded report JSON missing event evidence manifest.", reportJson);
    ensure(reportJson.event_evidence_manifest.every((item) => item.evidence_kind === "real_edf_waveform_window" && item.evidence_ready === true), "Downloaded report JSON contains non-real evidence.", reportJson.event_evidence_manifest);
    ensure(reportJson.manifest?.scan_parameters?.candidate_source === "bounded_full_record_window_scan_rms_ptp_v1", "Downloaded report JSON scan parameters do not show real scan source.", reportJson.manifest?.scan_parameters);
    ensure(!/D:\\|C:\\|\\\\/.test(reportJsonText), "Report export appears to expose an absolute local path.");

    const [csvDownload] = await Promise.all([
      page.waitForEvent("download", { timeout: 30000 }),
      page.click("#exportCsvBtn"),
    ]);
    evidence.downloads.candidates_csv = await saveDownload(csvDownload, "candidates");
    evidence.downloads.events_csv = evidence.downloads.candidates_csv;
    const csvText = fs.readFileSync(evidence.downloads.events_csv, "utf8");
    ensure(csvText.includes("候选编号"), "CSV export missing candidate table headers.");
    ensure(csvText.includes("HE-105-SCAN-003") && csvText.includes("纳入草稿候选"), "CSV export missing backend reviewed candidate row.");

    await page.waitForSelector('[data-testid="epilepsy-full-flow-preview"]', { timeout: 30000 });
    await page.waitForFunction(() => document.querySelector("#contextReview")?.textContent?.trim() !== "-", null, { timeout: 30000 });
    const restored = await page.evaluate(() => {
      const flow = JSON.parse(localStorage.getItem("qlanalyser.epilepsy.full_flow.latest") || "{}");
      const review = JSON.parse(localStorage.getItem("qlanalyser.epilepsy.review_preview.latest") || "{}");
      const scan003 = Object.entries(flow.reviews || {}).find(([key]) => key === "HE-105-SCAN-003");
      return {
        record: document.querySelector("#contextRecord")?.textContent?.trim(),
        reviewCoverage: document.querySelector("#contextReview")?.textContent?.trim(),
        reportStatus: document.querySelector("#contextReport")?.textContent?.trim(),
        bodyHasScan003: document.body.innerText.includes("HE-105-SCAN-003"),
        bodyHasConfirmed: document.body.innerText.includes("暂列入复核草稿"),
        reviewSaved: flow.review_saved,
        backendReviewSessionId: flow.backend_review_session?.session_id || review.backend_review_session?.session_id || null,
        scan003: scan003 ? scan003[1] : null,
      };
    });
    evidence.restoredFullFlow = restored;
    ensure(restored.record === "HE-105.edf", "Full-flow did not restore HE-105 record.", restored);
    ensure(restored.bodyHasScan003 && restored.bodyHasConfirmed && restored.scan003?.status === "confirmed", "Full-flow did not restore adjusted review state.", restored);
    ensure(restored.reviewSaved === true, "Full-flow did not preserve review_saved state.", restored);
    ensure(Boolean(restored.backendReviewSessionId), "Full-flow did not preserve backend review session id.", restored);
    ensure(restored.backendReviewSessionId === reviewSession.session_id, "Full-flow restored a different backend review session id.", { restored, reviewSession });
    await screenshot(page, evidence, "05_full_flow_restored", false);
    const forbiddenFallbackMarkers = [
      "backend_export_package_failed",
      "backend_csv_export_failed",
      "已回退为浏览器本地",
      "local_fallback",
    ];
    const forbiddenReviewerMarkers = [
      "preview_reviewer",
      "trial_research_reviewer",
      "demo_autofill_reviewer",
    ];
    const evidenceText = JSON.stringify(evidence);
    ensure(!forbiddenFallbackMarkers.some((marker) => evidenceText.includes(marker) || reportJsonText.includes(marker) || csvText.includes(marker)), "Browser E2E observed a forbidden export fallback marker.");
    ensure(!forbiddenReviewerMarkers.some((marker) => evidenceText.includes(marker) || reportJsonText.includes(marker) || csvText.includes(marker)), "Browser E2E observed an internal reviewer placeholder.");

    evidence.checks = {
      preflight_passed: Number.isFinite(Number(preflight.sfreq))
        && Number(preflight.duration_sec) > 0
        && Number(preflight.channel_count) > 0,
      candidates_generated: evidence.candidates.count > 0,
      real_review_session_saved: Boolean(reviewSession.session_id),
      whole_segment_drag_preserved_duration: Math.abs((afterMove.end - afterMove.start) - (beforeMove.end - beforeMove.start)) < 0.2,
      boundary_drag_separated: afterStartHandle.start > afterMove.start && afterEndHandle.end > afterStartHandle.end,
      report_exported: fs.existsSync(evidence.downloads.report_json),
      csv_exported: fs.existsSync(evidence.downloads.events_csv),
      backend_export_source_verified: reportJson.export_source === "backend_review_session_export",
      backend_manifest_verified: reportJson.manifest?.schema_version === "qlanalyser.epilepsy.review_export_manifest.v1",
      backend_evidence_verified: reportJson.evidence_ready === true,
      reviewer_trace_label_clean: restored.scan003?.reviewer === "本地研究复核人",
      backend_review_session_preserved: restored.backendReviewSessionId === reviewSession.session_id,
      full_flow_restored: restored.bodyHasScan003 && restored.bodyHasConfirmed && restored.scan003?.status === "confirmed" && restored.reviewSaved === true,
      no_console_errors: evidence.console.length === 0,
    };
    for (const [name, passed] of Object.entries(evidence.checks)) ensure(passed, `Browser E2E check failed: ${name}`);

    evidence.status = "passed";
    fs.writeFileSync(EVIDENCE_PATH, `${JSON.stringify(evidence, null, 2)}\n`, "utf8");
    console.log(JSON.stringify({
      status: evidence.status,
      evidence_path: EVIDENCE_PATH,
      screenshots: evidence.screenshots,
      downloads: evidence.downloads,
      backend_review_session_id: reviewSession.session_id,
      restored,
    }, null, 2));
  } catch (error) {
    evidence.status = "failed";
    evidence.failure_class = classifyAcceptanceFailure(error, evidence);
    evidence.error = String(error?.stack || error);
    evidence.error_details = error?.details || {};
    try {
      await screenshot(page, evidence, "failure", true);
    } catch {}
    fs.writeFileSync(EVIDENCE_PATH, `${JSON.stringify(evidence, null, 2)}\n`, "utf8");
    console.error(error);
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

main();
