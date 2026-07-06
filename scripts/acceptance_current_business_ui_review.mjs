import fs from "node:fs";
import path from "node:path";
import { chromium, chromiumLaunchOptions } from "./lib/playwright_runtime.mjs";

const FRONTEND = process.env.QLANALYSER_FRONTEND_URL || "http://127.0.0.1:4174";
const API = process.env.QLANALYSER_API_URL || "http://127.0.0.1:8001/api";
const OUT_DIR = process.env.QLANALYSER_CURRENT_BUSINESS_UI_DIR
  || path.resolve("work/release_evidence/20260706-current-business-ui-review");
const EVIDENCE_PATH = path.join(OUT_DIR, "current_business_ui_review.json");
const REVIEW_STORAGE_KEY = "qlanalyser.epilepsy.review_preview.latest";

function ensureDir() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
}

function urlFor(pathname = "/", params = {}) {
  const url = new URL(pathname, FRONTEND);
  url.searchParams.set("api", API);
  for (const [key, value] of Object.entries(params)) url.searchParams.set(key, value);
  return url.toString();
}

function check(name, passed, details = {}) {
  return { name, passed: Boolean(passed), ...details };
}

async function screenshot(page, name, fullPage = true) {
  const file = path.join(OUT_DIR, `${name}.png`);
  await page.screenshot({ path: file, fullPage, timeout: 15000 });
  return file;
}

async function loginCustomer(page) {
  await page.goto(urlFor("/", { v: "current-business-ui" }), { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.locator("#customerEmail").fill("demo.customer@quanlan.cn");
  await page.locator("#customerPassword").fill("demo123456");
  await page.locator("#customerLoginForm button[type='submit']").click();
  await page.waitForSelector("#appShell:not([hidden])", { timeout: 30000 });
}

async function noHorizontalOverflow(page) {
  return page.evaluate(() => {
    const root = document.documentElement;
    const body = document.body;
    const scrollWidth = Math.max(root.scrollWidth, body.scrollWidth);
    return { ok: scrollWidth <= root.clientWidth + 2, scrollWidth, clientWidth: root.clientWidth };
  });
}

async function runCustomerPsdFlow(browser, evidence) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 950 }, acceptDownloads: true });
  const responses = [];
  page.on("response", (response) => {
    if (response.url().includes("/api/tasks")) {
      responses.push({ url: response.url(), status: response.status(), method: response.request().method() });
    }
  });
  try {
    await loginCustomer(page);
    await page.locator("[data-teaching-action='quickstart']").first().click();
    await page.waitForFunction(() => document.querySelector(".view.active")?.id === "analysis", null, { timeout: 60000 });
    await page.locator("[data-real-action='confirm-plan-inline']:not([disabled])").first().waitFor({ state: "visible", timeout: 60000 });
    evidence.screenshots.push(await screenshot(page, "01_customer_data_preparation", false));

    await page.locator("[data-real-action='confirm-plan-inline']:not([disabled])").first().click();
    await page.waitForTimeout(2500);
    await page.locator("[data-view='workflow']").click();
    await page.waitForFunction(() => document.querySelector(".view.active")?.id === "workflow", null, { timeout: 15000 });
    await page.locator("[data-real-action='run-psd']").first().waitFor({ state: "visible", timeout: 30000 });

    const methodState = await page.evaluate(() => {
      const ids = [
        "run-psd",
        "run-erp",
        "run-tfr",
        "run-multitaper-psd",
        "run-multitaper-tfr",
        "run-pac",
        "run-connectivity",
        "run-reference-csd",
        "open-epilepsy-workbench",
      ];
      return Object.fromEntries(ids.map((id) => {
        const node = document.querySelector(`[data-real-action="${id}"]`);
        return [id, node ? {
          disabled: Boolean(node.disabled),
          title: node.getAttribute("title") || "",
          text: node.textContent.replace(/\s+/g, " ").trim(),
          visible: Boolean(node.offsetWidth || node.offsetHeight || node.getClientRects().length),
        } : null];
      }));
    });

    evidence.checks.push(check("customer_psd_enabled_after_data_preparation", methodState["run-psd"] && !methodState["run-psd"].disabled, { methodState }));
    evidence.checks.push(check(
      "customer_erp_visible_with_event_prerequisite_not_internal_lock",
      methodState["run-erp"]
        && methodState["run-erp"].visible
        && methodState["run-erp"].disabled
        && methodState["run-erp"].title.includes("事件")
        && !methodState["run-erp"].title.includes("客户工作区暂不开放"),
      { methodState },
    ));
    const advancedIds = ["run-tfr", "run-multitaper-psd", "run-multitaper-tfr", "run-pac", "run-connectivity", "run-reference-csd", "open-epilepsy-workbench"];
    evidence.checks.push(check(
      "advanced_and_epilepsy_modules_remain_closed_for_customer",
      advancedIds.every((id) => methodState[id]?.disabled),
      { methodState },
    ));
    evidence.checks.push(check("workflow_no_horizontal_overflow", (await noHorizontalOverflow(page)).ok, await noHorizontalOverflow(page)));
    evidence.screenshots.push(await screenshot(page, "02_customer_psd_enabled_workflow"));

    const psdResponse = page.waitForResponse(
      (response) => response.url().includes("/api/tasks") && response.request().method() === "POST",
      { timeout: 90000 },
    ).catch((error) => ({ error: error.message }));
    await page.locator("[data-real-action='run-psd']").first().click();
    const psdResult = await psdResponse;
    const psdStatus = typeof psdResult.status === "function" ? psdResult.status() : null;
    const observedPsdPost = responses.find((item) => item.method === "POST" && item.url.endsWith("/api/tasks") && item.status >= 200 && item.status < 300);
    evidence.checks.push(check("customer_psd_task_post_succeeds", Boolean(observedPsdPost) || (psdStatus !== null && psdStatus >= 200 && psdStatus < 300), { psdStatus, psdResult, observedPsdPost, responses }));
    await page.waitForTimeout(2000);
    evidence.screenshots.push(await screenshot(page, "03_customer_after_psd_click"));
  } finally {
    await page.close();
  }
}

function reportPayload(kind) {
  const record = {
    id: `report-${kind}`,
    filename: `report-${kind}.edf`,
    duration_sec: 3600,
    sfreq: 250,
    channels: ["Fz", "Cz"],
  };
  const eventA = {
    event_id: "E1",
    start_sec: 12,
    end_sec: 13.2,
    event_type: "unknown",
    channels: ["Fz"],
    status: "confirmed",
    evidence_grade: "B",
    preview_rms_ptp_rank_score: 0.72,
  };
  const eventB = {
    event_id: "E2",
    start_sec: 42,
    end_sec: 43.1,
    event_type: "artifact_suspect",
    channels: ["Cz"],
    status: "rejected",
    evidence_grade: "X",
    preview_rms_ptp_rank_score: 0.31,
  };
  if (kind === "empty") {
    return { schema_version: "qlanalyser.epilepsy.manual_correction_preview.v1", record, reviewed_events: [], metadata: { has_full_candidate_set: false } };
  }
  if (kind === "partial") {
    return { schema_version: "qlanalyser.epilepsy.manual_correction_preview.v1", record, confirmed_events: [eventA], metadata: { has_full_candidate_set: false } };
  }
  return {
    schema_version: "qlanalyser.epilepsy.manual_correction_preview.v1",
    record,
    reviewed_events: [eventA, eventB],
    metadata: { has_full_candidate_set: true, candidate_denominator: 2 },
    actions: [{ action: "acceptance_fixture", at: new Date().toISOString() }],
  };
}

async function openReportWithPayload(browser, kind) {
  const page = await browser.newPage({ viewport: { width: 1360, height: 920 } });
  await page.addInitScript(({ key, payload }) => {
    window.sessionStorage.setItem(key, JSON.stringify(payload));
  }, { key: REVIEW_STORAGE_KEY, payload: reportPayload(kind) });
  await page.goto(urlFor("/epilepsy-report-preview.html", { v: `report-${kind}` }), { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForTimeout(1200);
  return page;
}

async function runReportPreviewStates(browser, evidence) {
  for (const kind of ["empty", "partial", "complete"]) {
    const page = await openReportWithPayload(browser, kind);
    try {
      const state = await page.evaluate(() => ({
        exportDisabled: document.querySelector("#exportReportBtn")?.disabled,
        csvDisabled: document.querySelector("#exportCsvBtn")?.disabled,
        statement: document.querySelector("#overallStatement")?.textContent || "",
        summary: document.querySelector("#interpretationText")?.textContent || "",
        overflow: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) - document.documentElement.clientWidth,
      }));
      if (kind === "empty") {
        evidence.checks.push(check("report_empty_payload_blocks_draft_download", state.exportDisabled === true && state.csvDisabled === true, state));
      } else if (kind === "partial") {
        evidence.checks.push(check("report_partial_payload_blocks_draft_download", state.exportDisabled === true && state.csvDisabled === false, state));
      } else {
        evidence.checks.push(check(
          "report_complete_payload_enables_draft_and_keeps_rate_boundary",
          state.exportDisabled === false && state.summary.includes("不代表发作频率"),
          state,
        ));
      }
      evidence.checks.push(check(`report_${kind}_no_horizontal_overflow`, state.overflow <= 2, state));
      evidence.screenshots.push(await screenshot(page, `04_report_${kind}`));
    } finally {
      await page.close();
    }
  }
}

async function runReviewMobile(browser, evidence) {
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await page.addInitScript(({ key, payload }) => {
    window.sessionStorage.setItem(key, JSON.stringify(payload));
  }, { key: REVIEW_STORAGE_KEY, payload: reportPayload("complete") });
  try {
    await page.goto(urlFor("/epilepsy-review-preview.html", { v: "review-mobile" }), { waitUntil: "domcontentloaded", timeout: 60000 });
    await page.waitForTimeout(1200);
    const state = await page.evaluate(() => {
      const workspace = document.querySelector(".er-workspace");
      const workspaceStyle = workspace ? getComputedStyle(workspace) : null;
      return {
        overflow: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) - document.documentElement.clientWidth,
        workspaceHeight: workspaceStyle?.height || "",
        workspaceMinHeight: workspaceStyle?.minHeight || "",
        bodyText: document.body.innerText,
      };
    });
    evidence.checks.push(check("review_mobile_no_horizontal_overflow", state.overflow <= 2, state));
    evidence.checks.push(check("review_mobile_workspace_height_is_content_based", state.workspaceMinHeight === "0px", state));
    evidence.checks.push(check("review_unknown_event_type_preserved_as_candidate_window", state.bodyText.includes("候选窗口"), state));
    evidence.screenshots.push(await screenshot(page, "05_review_mobile", true));
  } finally {
    await page.close();
  }
}

async function runFullFlowUploadPreflight(browser, evidence) {
  const page = await browser.newPage({ viewport: { width: 1360, height: 920 } });
  try {
    await page.goto(urlFor("/epilepsy-full-flow-preview.html", { v: "upload-preflight" }), { waitUntil: "domcontentloaded", timeout: 60000 });
    await page.setInputFiles("#edfInput", path.resolve("frontend/assets/synthetic_8ch_120s.edf"));
    await page.waitForTimeout(500);
    await page.locator("#runPreflightBtn").click();
    await page.waitForFunction(() => document.querySelector("#contextQc")?.textContent.includes("待读取元数据"), null, { timeout: 15000 });
    const state = await page.evaluate(() => ({
      contextQc: document.querySelector("#contextQc")?.textContent || "",
      candidateStepDisabled: document.querySelector('[data-step="candidates"]')?.disabled,
      bodyText: document.body.innerText,
      overflow: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) - document.documentElement.clientWidth,
    }));
    evidence.checks.push(check("full_flow_upload_only_preflight_is_limited_metadata", state.contextQc.includes("待读取元数据"), state));
    evidence.checks.push(check("full_flow_upload_only_blocks_candidate_step", state.candidateStepDisabled === true, state));
    evidence.checks.push(check("full_flow_upload_no_horizontal_overflow", state.overflow <= 2, state));
    evidence.screenshots.push(await screenshot(page, "06_full_flow_upload_limited_preflight"));
  } finally {
    await page.close();
  }
}

async function main() {
  ensureDir();
  const evidence = {
    status: "running",
    generated_at: new Date().toISOString(),
    frontend: FRONTEND,
    api: API,
    checks: [],
    screenshots: [],
    errors: [],
  };
  const browser = await chromium.launch(chromiumLaunchOptions({ headless: true }));
  try {
    await runCustomerPsdFlow(browser, evidence);
    await runReportPreviewStates(browser, evidence);
    await runReviewMobile(browser, evidence);
    await runFullFlowUploadPreflight(browser, evidence);
  } catch (error) {
    evidence.errors.push(error.stack || error.message);
  } finally {
    await browser.close();
  }
  evidence.status = evidence.errors.length === 0 && evidence.checks.every((item) => item.passed) ? "passed" : "failed";
  fs.writeFileSync(EVIDENCE_PATH, `${JSON.stringify(evidence, null, 2)}\n`, "utf8");
  console.log(JSON.stringify(evidence, null, 2));
  if (evidence.status !== "passed") process.exit(1);
}

main().catch((error) => {
  ensureDir();
  fs.writeFileSync(EVIDENCE_PATH, `${JSON.stringify({ status: "failed", error: error.stack || error.message }, null, 2)}\n`, "utf8");
  console.error(error.stack || error.message);
  process.exit(1);
});
