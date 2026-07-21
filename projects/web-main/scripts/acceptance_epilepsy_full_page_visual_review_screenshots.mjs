import fs from "node:fs";
import path from "node:path";
import { chromium, chromiumLaunchOptions, classifyAcceptanceFailure } from "./lib/playwright_runtime.mjs";

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1")), "..");
const FRONTEND_BASE = process.env.QLANALYSER_LAB_EPILEPSY_FRONTEND_BASE || "http://127.0.0.1:4176";
const API_BASE = process.env.QLANALYSER_LAB_EPILEPSY_API_BASE || "http://127.0.0.1:8043/api";
const RECORD_ID = process.env.QLANALYSER_LAB_EPILEPSY_RECORD_ID || "he-105";
const RUN_ID = new Date().toISOString().replace(/[-:T.Z]/g, "").slice(0, 14);
const OUT_DIR = process.env.QLANALYSER_LAB_EPILEPSY_VISUAL_DIR
  || path.join(ROOT, "work", "release_evidence", "epilepsy_visual_perf_20260708", "full_page_visual_review");
const EVIDENCE_PATH = path.join(OUT_DIR, "epilepsy_full_page_visual_review.json");
const STORAGE_KEYS = [
  "qlanalyser.epilepsy.full_flow.latest",
  "qlanalyser.epilepsy.review_preview.latest",
];

const VIEWPORTS = {
  desktop: { width: 1920, height: 1080 },
  laptop: { width: 1366, height: 768 },
  mobile: { width: 390, height: 844 },
};

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
  url.searchParams.set("v", `visual-review-${RUN_ID}`);
  return url.toString();
}

async function assertApiHealth(evidence) {
  const healthUrl = `${API_BASE.replace(/\/$/, "")}/health`;
  const response = await fetch(healthUrl);
  evidence.service_health = { url: healthUrl, status: response.status };
  ensure(response.ok, `Backend health check failed: ${response.status}`);
}

async function collectDomSnapshot(page, name, viewportName) {
  return page.evaluate(({ name, viewportName }) => {
    const visible = (node) => {
      if (!node || node.hidden) return false;
      const style = getComputedStyle(node);
      const rect = node.getBoundingClientRect();
      return style.display !== "none" && style.visibility !== "hidden" && Number(style.opacity) !== 0 && rect.width > 0 && rect.height > 0;
    };
    const hiddenByAncestor = (node) => {
      let current = node?.parentElement || null;
      while (current && current !== document.body) {
        if (current.hidden) return true;
        const style = getComputedStyle(current);
        if (style.display === "none" || style.visibility === "hidden" || Number(style.opacity) === 0) return true;
        const rect = current.getBoundingClientRect();
        if (rect.width <= 1 || rect.height <= 1) return true;
        current = current.parentElement;
      }
      return false;
    };
    const rectOf = (selector) => {
      const node = document.querySelector(selector);
      if (!node) return null;
      const rect = node.getBoundingClientRect();
      return {
        selector,
        visible: visible(node),
        disabled: Boolean(node.disabled || node.getAttribute("aria-disabled") === "true"),
        x: Math.round(rect.x),
        y: Math.round(rect.y),
        width: Math.round(rect.width),
        height: Math.round(rect.height),
      };
    };
    const enabledZeroSizedButtons = Array.from(document.querySelectorAll("button, [role='button']"))
      .map((node) => {
        const rect = node.getBoundingClientRect();
        const style = getComputedStyle(node);
        return {
          text: (node.innerText || node.getAttribute("aria-label") || node.id || "").trim().slice(0, 80),
          id: node.id || "",
          width: Math.round(rect.width),
          height: Math.round(rect.height),
          disabled: Boolean(node.disabled || node.getAttribute("aria-disabled") === "true"),
          hidden_by_ancestor: hiddenByAncestor(node),
          display: style.display,
          visibility: style.visibility,
        };
      })
      .filter((item) => !item.disabled && !item.hidden_by_ancestor && item.display !== "none" && item.visibility !== "hidden" && (item.width <= 1 || item.height <= 1));
    const bodyText = document.body.innerText || "";
    const badMarkers = [
      "\uFFFD",
      "task_id",
      "workflow_id",
      "Traceback",
      "localhost",
      "D:\\",
      "C:\\",
      "\\\\",
      "diagnosis confirmed",
      "clinical diagnosis",
      "treatment recommendation",
    ].filter((marker) => bodyText.includes(marker));
    const headings = Array.from(document.querySelectorAll("h1,h2,h3"))
      .map((node) => node.innerText.trim())
      .filter(Boolean)
      .slice(0, 30);
    const canvasStats = Array.from(document.querySelectorAll("canvas")).map((canvas) => {
      const rect = canvas.getBoundingClientRect();
      let nonBlankSample = null;
      try {
        const ctx = canvas.getContext("2d");
        const w = Math.max(1, Math.min(canvas.width, 80));
        const h = Math.max(1, Math.min(canvas.height, 80));
        const data = ctx.getImageData(0, 0, w, h).data;
        let colored = 0;
        for (let index = 0; index < data.length; index += 4) {
          const r = data[index];
          const g = data[index + 1];
          const b = data[index + 2];
          const a = data[index + 3];
          if (a > 0 && (r < 245 || g < 245 || b < 245)) colored += 1;
        }
        nonBlankSample = colored;
      } catch {
        nonBlankSample = null;
      }
      return {
        id: canvas.id || "",
        width: Math.round(rect.width),
        height: Math.round(rect.height),
        backing_width: canvas.width,
        backing_height: canvas.height,
        non_blank_sample: nonBlankSample,
      };
    });
    return {
      name,
      viewport_name: viewportName,
      url: location.href,
      title: document.title,
      headings,
      body_text_length: bodyText.length,
      bad_markers: badMarkers,
      enabled_zero_sized_buttons: enabledZeroSizedButtons,
      horizontal_overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 2,
      scroll_width: document.documentElement.scrollWidth,
      client_width: document.documentElement.clientWidth,
      scroll_height: document.documentElement.scrollHeight,
      client_height: document.documentElement.clientHeight,
      key_rects: [
        rectOf("[data-testid='epilepsy-full-flow-preview']"),
        rectOf("#reviewWorkbenchFrame"),
        rectOf("[data-testid='epilepsy-review-preview']"),
        rectOf("[data-testid='epilepsy-report-preview']"),
        rectOf(".ep-flow-shell"),
        rectOf(".er-workspace"),
        rectOf(".er-waveform-shell"),
        rectOf("#eventBand"),
        rectOf("#startHandle"),
        rectOf("#endHandle"),
        rectOf("#exportReportJsonBtn"),
      ].filter(Boolean),
      canvas_stats: canvasStats,
    };
  }, { name, viewportName });
}

async function capture(page, evidence, name, viewportName = "desktop") {
  const file = path.join(OUT_DIR, `${name}_${viewportName}.png`);
  await page.screenshot({ path: file, fullPage: true, timeout: 30000 });
  const dom = await collectDomSnapshot(page, name, viewportName);
  evidence.pages.push({ ...dom, screenshot: file });
  evidence.screenshots[`${name}_${viewportName}`] = file;
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
  await page.mouse.move(x + dx, y + dy, { steps: 16 });
  await page.mouse.up();
  await page.waitForTimeout(250);
}

async function main() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const evidence = {
    schema_version: "qlanalyser.epilepsy.full_page_visual_review.v1",
    run_id: RUN_ID,
    status: "running",
    frontend_base: FRONTEND_BASE,
    api_base: API_BASE,
    record_id: RECORD_ID,
    screenshots: {},
    pages: [],
    requests: [],
    responses: [],
    console: [],
    findings: [],
  };
  await assertApiHealth(evidence);

  const browser = await chromium.launch(chromiumLaunchOptions({ headless: true }));
  const page = await browser.newPage({ viewport: VIEWPORTS.desktop, deviceScaleFactor: 1, acceptDownloads: true });
  page.on("console", (message) => {
    if (["error", "warning"].includes(message.type())) {
      evidence.console.push({ type: message.type(), text: message.text() });
    }
  });
  page.on("pageerror", (error) => {
    evidence.console.push({ type: "pageerror", text: String(error?.message || error) });
  });
  page.on("request", (request) => {
    if (request.url().includes("/api/")) {
      evidence.requests.push({ method: request.method(), url: request.url() });
    }
  });
  page.on("response", (response) => {
    if (response.url().includes("/api/")) {
      evidence.responses.push({ status: response.status(), method: response.request().method(), url: response.url() });
    }
  });

  try {
    await page.goto(fullFlowUrl(), { waitUntil: "domcontentloaded", timeout: 60000 });
    await page.evaluate((keys) => {
      for (const key of keys) {
        localStorage.removeItem(key);
        sessionStorage.removeItem(key);
      }
    }, STORAGE_KEYS);
    await page.reload({ waitUntil: "domcontentloaded", timeout: 60000 });
    await page.waitForSelector('[data-testid="epilepsy-full-flow-preview"]', { timeout: 30000 });
    await page.waitForSelector(`#sampleGrid [data-record-id="${RECORD_ID}"]`, { timeout: 60000 });
    await page.click(`#sampleGrid [data-record-id="${RECORD_ID}"]`);
    await capture(page, evidence, "01_full_flow_record_selected");

    const preflightResponse = page.waitForResponse(
      (response) => response.url().includes(`/lab/epilepsy-full-flow/records/${RECORD_ID}/preflight`) && response.status() < 400,
      { timeout: 90000 },
    );
    await page.click("#runPreflightBtn");
    evidence.preflight = await (await preflightResponse).json();
    await page.waitForTimeout(800);
    await capture(page, evidence, "02_full_flow_after_preflight");

    const candidatesResponse = page.waitForResponse(
      (response) => response.url().includes(`/lab/epilepsy-full-flow/records/${RECORD_ID}/candidates`)
        && response.request().method() === "POST",
      { timeout: 180000 },
    );
    await page.click("#generateCandidatesBtn");
    const candidatesRawResponse = await candidatesResponse;
    const candidatesRawText = await candidatesRawResponse.text();
    ensure(candidatesRawResponse.ok(), `Candidate generation failed: ${candidatesRawResponse.status()}`, {
      status: candidatesRawResponse.status(),
      body: candidatesRawText.slice(0, 2000),
    });
    evidence.candidate_package = JSON.parse(candidatesRawText);
    ensure((evidence.candidate_package.candidates || []).length > 0, "No candidates generated.");
    await page.waitForTimeout(800);
    await capture(page, evidence, "03_full_flow_candidates_generated");

    await page.click('[data-step="review"]');
    await page.waitForFunction(() => document.body.innerText.includes("本页判读区") || document.body.innerText.includes("判读区已并入全流程"), null, { timeout: 30000 });
    ensure(await page.locator('[data-flow-status]').count() === 0, "Full-flow handoff still exposes inline review decision controls.");
    ensure(await page.locator("#reviewNoteInput").count() === 0, "Full-flow handoff still exposes inline review notes.");
    await page.locator("#reviewWorkbenchFrame").waitFor({ state: "visible", timeout: 30000 });
    evidence.review_handoff = {
      inline_decision_controls: await page.locator('[data-flow-status]').count(),
      inline_note_controls: await page.locator("#reviewNoteInput").count(),
      has_refresh_button: await page.locator("#openReviewHandoffBtn").count() > 0,
      has_embedded_frame: await page.locator("#reviewWorkbenchFrame").count() > 0,
      embedded_frame_src: await page.locator("#reviewWorkbenchFrame").getAttribute("src"),
    };
    ensure(evidence.review_handoff.embedded_frame_src?.includes("embed=1"), "Embedded review frame did not load in embed mode.", evidence.review_handoff);
    await page.waitForTimeout(800);
    await capture(page, evidence, "04_full_flow_review_handoff");

    await page.click("#openReviewHandoffBtn");
    const reviewFrame = page.frameLocator("#reviewWorkbenchFrame");
    await reviewFrame.locator('[data-testid="epilepsy-review-preview"]').waitFor({ state: "visible", timeout: 30000 });
    await reviewFrame.locator("#candidateList [data-candidate-id]").first().waitFor({ state: "visible", timeout: 30000 });
    const preferredCandidate = '#candidateList [data-candidate-id="HE-105-SCAN-003"]';
    if (await reviewFrame.locator(preferredCandidate).count()) await reviewFrame.locator(preferredCandidate).click();
    else await reviewFrame.locator("#candidateList [data-candidate-id]").first().click();
    await reviewFrame.locator("#eventBand").waitFor({ state: "visible", timeout: 30000 });
    await page.waitForTimeout(1200);
    await capture(page, evidence, "05_review_loaded");

    await reviewFrame.locator('[data-status="kept"]').click();
    await dragLocatorBy(page, reviewFrame.locator("#eventBand"), 80);
    await dragLocatorBy(page, reviewFrame.locator("#startHandle"), 24);
    await dragLocatorBy(page, reviewFrame.locator("#endHandle"), 24);
    await capture(page, evidence, "06_review_after_drag");

    const reviewSessionResponse = page.waitForResponse(
      (response) => response.url().includes("/lab/epilepsy-full-flow/review-sessions")
        && response.request().method() === "POST"
        && response.status() < 400,
      { timeout: 90000 },
    );
    await Promise.all([
      reviewSessionResponse,
      reviewFrame.locator("#reportPreviewBtn").click(),
    ]);
    await page.waitForSelector('[data-testid="epilepsy-full-flow-preview"]', { timeout: 30000 });
    await page.waitForFunction(() => document.querySelector("#exportReportJsonBtn") && !document.querySelector("#exportReportJsonBtn").disabled, null, { timeout: 30000 });
    await page.waitForTimeout(1000);
    await capture(page, evidence, "07_report_ready");

    await page.setViewportSize(VIEWPORTS.laptop);
    await page.waitForTimeout(400);
    await capture(page, evidence, "07_report_ready", "laptop");
    await page.setViewportSize(VIEWPORTS.mobile);
    await page.waitForTimeout(400);
    await capture(page, evidence, "07_report_ready", "mobile");
    await page.setViewportSize(VIEWPORTS.desktop);
    await page.waitForTimeout(400);

    await page.waitForSelector('[data-testid="epilepsy-full-flow-preview"]', { timeout: 30000 });
    await page.waitForTimeout(1000);
    await capture(page, evidence, "08_full_flow_restored");

    for (const pageState of evidence.pages) {
      if (pageState.horizontal_overflow) {
        evidence.findings.push({ severity: "P1", page: pageState.name, viewport: pageState.viewport_name, issue: "horizontal_overflow" });
      }
      if (pageState.bad_markers.length) {
        evidence.findings.push({ severity: "P1", page: pageState.name, viewport: pageState.viewport_name, issue: "bad_visible_marker", markers: pageState.bad_markers });
      }
      if (pageState.enabled_zero_sized_buttons.length) {
        evidence.findings.push({ severity: "P0", page: pageState.name, viewport: pageState.viewport_name, issue: "enabled_zero_sized_control", controls: pageState.enabled_zero_sized_buttons });
      }
      for (const canvas of pageState.canvas_stats) {
        if (canvas.width > 20 && canvas.height > 20 && canvas.non_blank_sample === 0) {
          evidence.findings.push({ severity: "P1", page: pageState.name, viewport: pageState.viewport_name, issue: "blank_canvas_sample", canvas });
        }
      }
    }
    evidence.status = evidence.findings.some((finding) => finding.severity === "P0") ? "failed" : "passed";
    fs.writeFileSync(EVIDENCE_PATH, `${JSON.stringify(evidence, null, 2)}\n`, "utf8");
    console.log(JSON.stringify({
      status: evidence.status,
      evidence_path: EVIDENCE_PATH,
      screenshot_count: Object.keys(evidence.screenshots).length,
      findings: evidence.findings,
    }, null, 2));
    if (evidence.status !== "passed") process.exitCode = 1;
  } catch (error) {
    evidence.status = "failed";
    evidence.failure_class = classifyAcceptanceFailure(error, evidence);
    evidence.error = String(error?.stack || error);
    evidence.error_details = error?.details || {};
    try {
      await capture(page, evidence, "failure");
    } catch {
      // Keep the original failure if screenshot capture also fails.
    }
    fs.writeFileSync(EVIDENCE_PATH, `${JSON.stringify(evidence, null, 2)}\n`, "utf8");
    console.error(error);
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

main();
