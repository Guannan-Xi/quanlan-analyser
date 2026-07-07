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

function reviewUrl() {
  const url = new URL("/epilepsy-review-preview.html", FRONTEND_BASE);
  url.searchParams.set("api", API_BASE);
  url.searchParams.set("source", "full-flow-preview");
  url.searchParams.set("v", `browser-e2e-${RUN_ID}`);
  return url.toString();
}

async function screenshot(page, evidence, name, fullPage = true) {
  const file = path.join(OUT_DIR, `${name}.png`);
  await page.screenshot({ path: file, fullPage, timeout: 20000 });
  evidence.screenshots[name] = file;
}

async function readTimes(page) {
  return page.evaluate(() => ({
    start: Number(document.querySelector("#startInput")?.value),
    end: Number(document.querySelector("#endInput")?.value),
  }));
}

async function dragBy(page, selector, dx, dy = 0) {
  const locator = page.locator(selector);
  await locator.waitFor({ state: "visible", timeout: 30000 });
  const box = await locator.boundingBox();
  ensure(box, `Cannot drag missing element: ${selector}`);
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
        && response.request().method() === "POST"
        && response.status() < 400,
      { timeout: 120000 },
    );
    await page.click("#generateCandidatesBtn");
    const candidatePackage = await (await candidatesResponse).json();
    evidence.candidates = {
      count: candidatePackage.candidates?.length || 0,
      source: candidatePackage.candidate_source,
      algorithm_status: candidatePackage.algorithm_status,
    };
    ensure(evidence.candidates.count > 0, "No candidates generated from HE sample.");
    await page.waitForFunction(() => document.body.innerText.includes("HE-105-SCAN"), null, { timeout: 60000 });
    await screenshot(page, evidence, "02_candidates_generated", false);

    const fullFlowText = await page.locator("body").innerText();
    ensure(fullFlowText.includes("当前页直接复核"), "Full-flow review step does not expose inline review controls.");
    ensure(!fullFlowText.includes("打开工作台"), "Full-flow review step still shows redundant open-workbench copy.");
    ensure(!fullFlowText.includes("详细复核页"), "Full-flow review step still exposes a redundant detailed-review entry.");
    ensure(!fullFlowText.includes("填充预览复核"), "Full-flow review step still exposes a demo-fill action.");
    await page.click('[data-flow-status="confirmed"]');
    await page.fill("#reviewNoteInput", "双导同步尖慢波，EMG/ACC 未见同步增高。");
    const inlineReviewSessionResponse = page.waitForResponse(
      (response) => response.url().includes("/lab/epilepsy-full-flow/review-sessions")
        && response.request().method() === "POST"
        && response.status() < 400,
      { timeout: 60000 },
    );
    await page.click("#saveReviewBtn");
    evidence.inlineReviewSessionResponse = {
      status: (await inlineReviewSessionResponse).status(),
    };
    await screenshot(page, evidence, "03_inline_review_saved", false);

    await page.goto(reviewUrl(), { waitUntil: "domcontentloaded", timeout: 60000 });
    await page.waitForSelector('[data-testid="epilepsy-review-preview"]', { timeout: 30000 });
    await page.waitForSelector("#candidateList [data-candidate-id]", { timeout: 30000 });
    const candidateSelector = '#candidateList [data-candidate-id="HE-105-SCAN-003"]';
    ensure(await page.locator(candidateSelector).count(), "Review page did not receive scan candidates from full-flow handoff.");
    await page.click(candidateSelector);
    await page.waitForSelector("#eventBand", { timeout: 30000 });
    const beforeMove = await readTimes(page);
    await page.click('[data-status="kept"]');
    await dragBy(page, "#eventBand", 70);
    const afterMove = await readTimes(page);
    ensure(afterMove.start !== beforeMove.start && afterMove.end !== beforeMove.end, "Whole segment drag did not move both boundaries.", { beforeMove, afterMove });
    ensure(Math.abs((afterMove.end - afterMove.start) - (beforeMove.end - beforeMove.start)) < 0.2, "Whole segment drag changed duration.", { beforeMove, afterMove });

    await dragBy(page, "#startHandle", 28);
    const afterStartHandle = await readTimes(page);
    ensure(afterStartHandle.start > afterMove.start && Math.abs(afterStartHandle.end - afterMove.end) < 0.2, "Start handle did not adjust start only.", { afterMove, afterStartHandle });
    await dragBy(page, "#endHandle", 28);
    const afterEndHandle = await readTimes(page);
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
      page.click("#reportPreviewBtn"),
    ]);
    evidence.backendReviewSessionResponse = {
      status: reviewSessionRawResponse.status(),
      url: reviewSessionRawResponse.url(),
    };
    await page.waitForURL(/epilepsy-report-preview\.html/, { timeout: 60000 });
    const reviewSession = await page.evaluate(() => {
      const payload = JSON.parse(localStorage.getItem("qlanalyser.epilepsy.review_preview.latest") || "{}");
      return payload.backend_review_session || {};
    });
    evidence.backendReviewSession = reviewSession;
    ensure(Boolean(reviewSession.session_id), "Backend review session was not created.");

    await page.waitForSelector('[data-testid="epilepsy-report-preview"]', { timeout: 30000 });
    await page.waitForFunction(() => document.querySelector("#eventTableBody tr") && document.body.innerText.includes("候选复核表"), null, { timeout: 30000 });
    const reportText = await page.locator("body").innerText();
    ensure(reportText.includes("HE-105-SCAN-003"), "Report page does not show adjusted candidate.");
    ensure(reportText.includes("纳入草稿候选"), "Report page does not show confirmed draft status.");
    await screenshot(page, evidence, "04_report_ready", false);

    const [reportDownload] = await Promise.all([
      page.waitForEvent("download", { timeout: 30000 }),
      page.click("#exportReportBtn"),
    ]);
    evidence.downloads.report_json = await saveDownload(reportDownload, "report");
    const reportJsonText = fs.readFileSync(evidence.downloads.report_json, "utf8");
    ensure(reportJsonText.includes("research_screening_support_only") || reportJsonText.includes("科研筛查"), "Report export missing research boundary.");
    ensure(!/D:\\|C:\\|\\\\/.test(reportJsonText), "Report export appears to expose an absolute local path.");

    const [csvDownload] = await Promise.all([
      page.waitForEvent("download", { timeout: 30000 }),
      page.click("#exportCsvBtn"),
    ]);
    evidence.downloads.events_csv = await saveDownload(csvDownload, "events");
    const csvText = fs.readFileSync(evidence.downloads.events_csv, "utf8");
    ensure(csvText.includes("候选") || csvText.includes("事件编号"), "CSV export missing candidate table headers.");

    await Promise.all([
      page.waitForURL(/epilepsy-review-preview\.html/, { timeout: 60000 }),
      page.click("#returnFromReportBtn"),
    ]);
    await page.waitForSelector("#backToFlowBtn", { timeout: 30000 });
    await Promise.all([
      page.waitForURL(/epilepsy-full-flow-preview\.html/, { timeout: 60000 }),
      page.click("#backToFlowBtn"),
    ]);
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
        bodyHasConfirmed: document.body.innerText.includes("纳入草稿候选"),
        reviewSaved: flow.review_saved,
        backendReviewSessionId: flow.backend_review_session?.session_id || review.backend_review_session?.session_id || null,
        scan003: scan003 ? scan003[1] : null,
      };
    });
    evidence.restoredFullFlow = restored;
    ensure(restored.record === "HE-105.edf", "Full-flow did not restore HE-105 record.", restored);
    ensure(restored.bodyHasScan003 && restored.bodyHasConfirmed, "Full-flow did not restore adjusted review state.", restored);
    ensure(restored.reviewSaved === true, "Full-flow did not preserve review_saved state.", restored);
    ensure(Boolean(restored.backendReviewSessionId), "Full-flow did not preserve backend review session id.", restored);
    await screenshot(page, evidence, "05_full_flow_restored", false);

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
      full_flow_restored: restored.bodyHasScan003 && restored.bodyHasConfirmed && restored.reviewSaved === true,
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
