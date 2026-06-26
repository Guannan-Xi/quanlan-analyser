import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";

const require = createRequire(import.meta.url);
const { chromium } = require("../frontend/node_modules/playwright");

const FRONTEND_URL = process.env.QLANALYSER_FRONTEND_URL || "http://127.0.0.1:4174/?customer_demo=login&api=http://127.0.0.1:8001/api";
const SAMPLE_EDF = process.env.QLANALYSER_UI_SAMPLE_EDF || path.resolve("frontend/assets/teaching_oddball.edf");
const OUT_DIR = process.env.QLANALYSER_EDF_E2E_DIR || path.resolve("work/release_evidence/edf_upload_to_results_ui_only");
const EVIDENCE_PATH = path.join(OUT_DIR, "edf_upload_to_results_ui_only.json");
const PDF_OCR_QA_PATH = path.resolve("work/release_evidence/pdf_ocr_artifact_qa/pdf_ocr_artifact_qa.json");
const CUSTOMER_EMAIL = process.env.QLANALYSER_DEMO_EMAIL || "demo.customer@quanlan.cn";
const CUSTOMER_PASSWORD = process.env.QLANALYSER_DEMO_PASSWORD || "demo123456";

function apiBaseFromFrontendUrl() {
  try {
    const url = new URL(FRONTEND_URL);
    const configured = url.searchParams.get("api");
    if (configured) return configured.replace(/\/$/, "");
  } catch {}
  return "http://127.0.0.1:8001/api";
}

const API_BASE_URL = process.env.QLANALYSER_API_BASE_URL || apiBaseFromFrontendUrl();
const API_HEALTH_URL = `${API_BASE_URL.replace(/\/$/, "")}/health`;

function ensureDir() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
}

function zipHeader(filePath) {
  return fs.readFileSync(filePath).subarray(0, 4).toString("hex");
}

function inspectReportZip(filePath) {
  const script = [
    "import json, sys, zipfile",
    "path=sys.argv[1]",
    "with zipfile.ZipFile(path) as zf:",
    "    names=set(zf.namelist())",
    "    report=json.loads(zf.read('reports/report.json').decode('utf-8'))",
    "    prefixes=sorted({name.split('/')[1] for name in names if name.startswith('analyses/') and len(name.split('/')) > 2})",
    "    print(json.dumps({'entry_count': len(names), 'analysis_prefixes': prefixes, 'included_analyses': report.get('included_analyses', [])}, ensure_ascii=False))",
  ].join("\n");
  return JSON.parse(execFileSync("python", ["-c", script, filePath], { encoding: "utf8" }));
}

function stringifyEvidence(payload) {
  return JSON.stringify(payload, null, 2).replace(/[^\x09\x0a\x0d\x20-\x7e]/g, (char) => {
    return char
      .split("")
      .map((unit) => `\\u${unit.charCodeAt(0).toString(16).padStart(4, "0")}`)
      .join("");
  });
}

function writeEvidence(payload) {
  fs.writeFileSync(EVIDENCE_PATH, `${stringifyEvidence(payload)}\n`, "utf8");
}

function runPdfOcrArtifactQa(filePath) {
  execFileSync("python", ["scripts/acceptance_pdf_ocr_artifact_qa.py", "--report-zip", filePath], {
    encoding: "utf8",
    maxBuffer: 10 * 1024 * 1024,
  });
  const payload = JSON.parse(fs.readFileSync(PDF_OCR_QA_PATH, "utf8"));
  return {
    requirement_id: payload.requirement_id,
    status: payload.status,
    artifact_validator_verdict: payload.artifact_validator_verdict,
    primary_parse: payload.primary_parse,
    auxiliary_text_layer_audit: payload.auxiliary_text_layer_audit,
    report_zip_path: payload.report_zip_path,
    page_count: payload.page_count,
    rendered_pages: payload.rendered_pages,
    page_checks: payload.page_checks,
    blockers: payload.blockers || [],
    revise_items: payload.revise_items || [],
    validator_warnings: payload.validator_warnings || [],
    native_text_audit: payload.native_text_audit,
    important_boundary: payload.important_boundary,
    evidence_path: PDF_OCR_QA_PATH,
  };
}

async function screenshot(page, name, evidence) {
  const target = path.join(OUT_DIR, `${name}.png`);
  await page.screenshot({ path: target, fullPage: true, timeout: 15000 }).catch(async () => {
    await page.locator("body").screenshot({ path: target, timeout: 15000 });
  });
  evidence.screenshots.push(target);
  return target;
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function sampleHealth(evidence, label, attempts = 3) {
  const sample = {
    label,
    at: new Date().toISOString(),
    url: API_HEALTH_URL,
    ok: false,
    attempts: [],
  };
  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    const attemptResult = {
      attempt,
      at: new Date().toISOString(),
      ok: false,
    };
    try {
      const response = await fetch(API_HEALTH_URL);
      attemptResult.http_status = response.status;
      attemptResult.body = await response.json().catch(() => null);
      attemptResult.ok = response.ok && attemptResult.body?.status === "ok";
    } catch (error) {
      attemptResult.error = error.message;
    }
    sample.attempts.push(attemptResult);
    if (attemptResult.ok) {
      sample.http_status = attemptResult.http_status;
      sample.body = attemptResult.body;
      sample.ok = true;
      break;
    }
    if (attempt < attempts) await delay(750);
  }
  if (!sample.ok) {
    const lastAttempt = sample.attempts[sample.attempts.length - 1] || {};
    sample.http_status = lastAttempt.http_status;
    sample.body = lastAttempt.body;
    sample.error = lastAttempt.error || "health check failed";
  }
  evidence.serviceHealthSamples.push(sample);
  return sample;
}

function serviceProcessIds(evidence) {
  return [...new Set(
    (evidence.serviceHealthSamples || [])
      .map((sample) => sample?.body?.process_id)
      .filter((value) => value !== undefined && value !== null),
  )];
}

function finalizeServiceHealthChecks(evidence, allowMissingPid = false) {
  const processIds = serviceProcessIds(evidence);
  evidence.backendProcessIdsObserved = processIds;
  evidence.checks.backendHealthSamplesOk = evidence.serviceHealthSamples.every((sample) => sample.ok);
  evidence.checks.backendProcessStable = allowMissingPid
    ? processIds.length <= 1
    : processIds.length === 1;
}

async function waitForResponseAfter(page, label, predicate, action, timeout = 45000) {
  let lastActionError = null;
  for (let attempt = 1; attempt <= 2; attempt += 1) {
    const responsePromise = page.waitForResponse(predicate, { timeout }).catch((error) => error);
    try {
      await action(attempt);
    } catch (error) {
      lastActionError = error;
      responsePromise.catch(() => {});
      if (attempt === 2) throw new Error(`${label} click/action failed: ${error.message}`);
      continue;
    }
    const response = await responsePromise;
    if (response instanceof Error) {
      if (attempt === 2) {
        const actionMessage = lastActionError ? `; last click error: ${lastActionError.message}` : "";
        throw new Error(`${label} response was not observed after ${attempt} UI click attempts: ${response.message}${actionMessage}`);
      }
      await page.waitForTimeout(500);
      continue;
    }
    if (!response.ok()) {
      throw new Error(`${label} failed with HTTP ${response.status()}`);
    }
    return response;
  }
  throw new Error(`${label} response was not observed`);
}

async function clickEnabled(page, selector, label, timeout = 30000) {
  const visibleSelector = `${selector}:visible`;
  const target = page.locator(visibleSelector).first();
  await target.waitFor({ state: "visible", timeout });
  await page.waitForFunction((targetSelector) => {
    const node = Array.from(document.querySelectorAll(targetSelector)).find((item) => {
      const style = window.getComputedStyle(item);
      const rect = item.getBoundingClientRect();
      return style.visibility !== "hidden" && style.display !== "none" && rect.width > 0 && rect.height > 0;
    });
    return Boolean(node && !node.disabled && node.getAttribute("aria-disabled") !== "true");
  }, selector, { timeout });
  await target.scrollIntoViewIfNeeded();
  await target.click({ trial: true, timeout });
  const box = await target.boundingBox();
  if (!box) throw new Error(`${label} button has no clickable box`);
  await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
}

async function waitForModuleResult(page, moduleName, timeout = 45000) {
  await page.waitForFunction((name) => {
    const item = document.querySelector(`[data-result-module="${name}"]`);
    return Boolean(item && /completed|已完成/i.test(item.textContent || ""));
  }, moduleName, { timeout });
}

async function login(page) {
  await page.addInitScript(() => {
    localStorage.removeItem("qlanalyser_auth_session");
    localStorage.removeItem("qlanalyser_customer_profile");
    sessionStorage.removeItem("qlanalyser_auth_session");
  });
  await page.goto(FRONTEND_URL, { waitUntil: "domcontentloaded", timeout: 20000 });
  await page.waitForSelector("#customerLoginForm", { state: "visible", timeout: 15000 });
  await page.fill("#customerEmail", CUSTOMER_EMAIL);
  await page.fill("#customerPassword", CUSTOMER_PASSWORD);
  await Promise.all([
    page.waitForSelector("#appShell:not([hidden])", { timeout: 20000 }),
    page.locator("#customerLoginBtn").click(),
  ]);
}

async function visibleState(page) {
  return page.evaluate(() => ({
    view: document.querySelector(".view.active")?.id || "",
    title: document.querySelector("#viewTitle")?.textContent?.trim() || "",
    status: document.querySelector("#realRuntimeStatus")?.textContent?.trim() || "",
    resultText: document.querySelector("#realResultReview")?.innerText || "",
    deliveryText: document.querySelector("#realDeliveryLinks")?.innerText || "",
    auditCount: Array.isArray(window.qlanalyserUiActionAudit) ? window.qlanalyserUiActionAudit.length : 0,
  }));
}

async function openStorageForUpload(page, evidence) {
  const jumpedFromDashboard = await page.locator('[data-view-jump="storage"]:visible').first().isVisible().catch(() => false);
  if (jumpedFromDashboard) {
    await clickEnabled(page, '[data-view-jump="storage"]', "open storage from project detail");
  } else {
    await clickEnabled(page, '[data-view="storage"]', "open storage");
  }
  await page.waitForSelector('#storage.active, .view#storage.active', { timeout: 15000 });
  await page.locator('#storage [data-real-action="upload-eeg"]:visible').first().waitFor({ state: "visible", timeout: 15000 });
  evidence.steps.push({ action: "open storage for upload", status: "passed" });
}

async function main() {
  ensureDir();
  const evidence = {
    status: "running",
    policy: "UI-only product path: login, click, upload teaching EDF sample, run preparation/analysis, create and download report ZIP. No direct API task mutation.",
    frontendUrl: FRONTEND_URL,
    sampleEdf: SAMPLE_EDF,
    defaultTestAccount: {
      account: CUSTOMER_EMAIL,
      passwordOrLogin: CUSTOMER_PASSWORD,
      scope: "demo customer, low privilege, local review only",
    },
    generatedAt: new Date().toISOString(),
    steps: [],
    requests: [],
    responses: [],
    screenshots: [],
    downloads: [],
    serviceHealthSamples: [],
    checks: {},
    errors: [],
    browserEvents: [],
  };
  if (!fs.existsSync(SAMPLE_EDF)) {
    throw new Error(`Synthetic EDF not found: ${SAMPLE_EDF}`);
  }
  evidence.sampleEdfBytes = fs.statSync(SAMPLE_EDF).size;

  const browser = await chromium.launch();
  const context = await browser.newContext({ acceptDownloads: true, viewport: { width: 1440, height: 1000 } });
  const page = await context.newPage();
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
  page.on("pageerror", (error) => {
    evidence.browserEvents.push({ type: "pageerror", message: error.message, stack: error.stack });
    evidence.errors.push(error.message);
  });
  page.on("console", (msg) => {
    if (msg.type() === "error") {
      evidence.browserEvents.push({ type: "console-error", text: msg.text(), location: msg.location() });
      evidence.errors.push(msg.text());
    }
  });

  try {
    await sampleHealth(evidence, "before-login");
    await login(page);
    evidence.steps.push({ action: "login", status: "passed" });
    await sampleHealth(evidence, "after-login");
    await screenshot(page, "01-login-dashboard", evidence);

    const projectResponse = await waitForResponseAfter(
      page,
      "create project",
      (response) => response.url().includes("/api/projects") && response.request().method() === "POST",
      () => clickEnabled(page, '[data-real-action="create-project"]', "create project"),
    );
    const project = await projectResponse.json();
    evidence.projectId = project.id;
    evidence.steps.push({ action: "click create-project", status: "passed", projectId: project.id });
    await sampleHealth(evidence, "after-create-project");

    await openStorageForUpload(page, evidence);
    await page.setInputFiles("#real-eeg-file", SAMPLE_EDF);
    evidence.steps.push({ action: "select teaching EDF", status: "passed", file: SAMPLE_EDF });
    const uploadResponse = await waitForResponseAfter(
      page,
      "upload EDF",
      (response) => response.url().includes("/api/eeg/upload") && response.status() === 200,
      () => clickEnabled(page, '#storage [data-real-action="upload-eeg"]', "upload EEG"),
      45000,
    );
    const uploaded = await uploadResponse.json();
    evidence.uploadedFile = {
      id: uploaded.id,
      original_filename: uploaded.original_filename,
      detected_format: uploaded.detected_format,
      sampling_rate: uploaded.sampling_rate,
      channel_count: uploaded.channel_count,
      duration_sec: uploaded.duration_sec,
    };
    evidence.checks.uploadedEdfDetected = uploaded.detected_format === "edf" || /\.edf$/i.test(uploaded.original_filename || "");
    evidence.steps.push({ action: "click upload-eeg", status: "passed", fileId: uploaded.id });
    await sampleHealth(evidence, "after-upload-eeg");
    await screenshot(page, "02-edf-uploaded", evidence);

    await page.waitForSelector(`[data-file-select="${uploaded.id}"]`, { timeout: 20000 });
    const qcResponse = await waitForResponseAfter(
      page,
      "auto preview after selecting data row",
      (response) => response.url().includes("/api/tasks") && response.request().method() === "POST",
      () => clickEnabled(page, `[data-file-select="${uploaded.id}"]`, "select data row for automatic preview"),
      60000,
    );
    const qcTask = await qcResponse.json();
    evidence.qcTask = { id: qcTask.id, module_name: qcTask.module_name, status: qcTask.status };
    evidence.steps.push({ action: "select data row -> automatic preview", status: "passed", taskId: qcTask.id });
    await sampleHealth(evidence, "after-qc");

    await clickEnabled(page, '[data-view="analysis"]', "open data preparation");
    const metadataQcResponse = await waitForResponseAfter(
      page,
      "run metadata QC",
      (response) => response.url().includes("/api/tasks") && response.request().method() === "POST",
      () => clickEnabled(page, '[data-real-action="run-metadata-qc-inline"]', "run metadata QC"),
      60000,
    );
    const metadataQcTask = await metadataQcResponse.json();
    evidence.metadataQcTask = {
      id: metadataQcTask.id,
      module_name: metadataQcTask.module_name,
      workflow_id: metadataQcTask.workflow_id,
      status: metadataQcTask.status,
    };
    evidence.steps.push({ action: "click run-metadata-qc-inline", status: "passed", taskId: metadataQcTask.id });
    await sampleHealth(evidence, "after-metadata-qc");

    const planResponse = await waitForResponseAfter(
      page,
      "confirm data preparation",
      (response) => response.url().includes("/api/data-preparation/plans") && response.request().method() === "POST",
      () => clickEnabled(page, '[data-real-action="confirm-plan-inline"]', "confirm preparation"),
      45000,
    );
    const plan = await planResponse.json();
    evidence.plan = { id: plan.id, revision: plan.revision, status: plan.status };
    evidence.steps.push({ action: "click confirm-plan-inline", status: "passed", planId: plan.id, revision: plan.revision });
    await sampleHealth(evidence, "after-confirm-plan");

    const saveAuditResponse = await waitForResponseAfter(
      page,
      "save bad-channel audit",
      (response) => response.url().includes("/api/eeg/files/") && response.url().includes("/bad-channel-audit") && response.request().method() === "POST",
      () => clickEnabled(page, '[data-real-action="save-bad-channel-audit"]', "save bad-channel audit"),
      45000,
    );
    const savedBadChannelAudit = await saveAuditResponse.json();
    evidence.badChannelAudit = {
      audit_id: savedBadChannelAudit.audit_id,
      decision: savedBadChannelAudit.decision,
      plan_id: savedBadChannelAudit.plan_id,
      plan_revision: savedBadChannelAudit.plan_revision,
      channels_tsv_path: savedBadChannelAudit.channels_tsv_path,
      audit_json_path: savedBadChannelAudit.audit_json_path,
      ui_evidence_path: savedBadChannelAudit.ui_evidence_path,
      source_integrity_path: savedBadChannelAudit.source_integrity_path,
      source: "visible UI save-bad-channel-audit button",
    };
    evidence.steps.push({ action: "click save-bad-channel-audit", status: "passed", auditId: savedBadChannelAudit.audit_id });
    await sampleHealth(evidence, "after-save-bad-channel-audit");

    const discardAuditResponse = await waitForResponseAfter(
      page,
      "discard bad-channel audit",
      (response) => response.url().includes("/api/eeg/files/") && response.url().includes("/bad-channel-audit") && response.request().method() === "POST",
      () => clickEnabled(page, '[data-real-action="discard-bad-channel-audit"]', "discard bad-channel audit"),
      45000,
    );
    const discardedBadChannelAudit = await discardAuditResponse.json();
    evidence.badChannelDiscardAudit = {
      audit_id: discardedBadChannelAudit.audit_id,
      decision: discardedBadChannelAudit.decision,
      plan_id: discardedBadChannelAudit.plan_id,
      plan_revision: discardedBadChannelAudit.plan_revision,
      channels_tsv_path: discardedBadChannelAudit.channels_tsv_path,
      audit_json_path: discardedBadChannelAudit.audit_json_path,
      ui_evidence_path: discardedBadChannelAudit.ui_evidence_path,
      source_integrity_path: discardedBadChannelAudit.source_integrity_path,
      source: "visible UI discard-bad-channel-audit button",
    };
    evidence.steps.push({ action: "click discard-bad-channel-audit", status: "passed", auditId: discardedBadChannelAudit.audit_id });
    await sampleHealth(evidence, "after-discard-bad-channel-audit");

    const epochResponse = await waitForResponseAfter(
      page,
      "save epoch set",
      (response) => response.url().includes("/api/eeg/files/") && response.url().includes("/epoch-sets") && response.request().method() === "POST",
      () => clickEnabled(page, '[data-real-action="save-epoch-set"]', "save epoch set"),
      45000,
    );
    const epochSet = await epochResponse.json();
    evidence.epochSet = { id: epochSet.id, revision: epochSet.revision, status: epochSet.status };
    evidence.steps.push({ action: "click save-epoch-set", status: "passed", epochSetId: epochSet.id });
    await sampleHealth(evidence, "after-epoch-set");
    await screenshot(page, "03-preparation-complete", evidence);

    await clickEnabled(page, '[data-view="workflow"]', "open analysis workflow");
    const psdResponse = await waitForResponseAfter(
      page,
      "run PSD",
      (response) => response.url().includes("/api/tasks") && response.request().method() === "POST",
      () => clickEnabled(page, '[data-real-action="run-psd"]', "run PSD"),
      60000,
    );
    const psdTask = await psdResponse.json();
    evidence.psdTask = { id: psdTask.id, module_name: psdTask.module_name, status: psdTask.status };
    evidence.steps.push({ action: "click run-psd", status: "passed", taskId: psdTask.id });
    await waitForModuleResult(page, "psd");
    await sampleHealth(evidence, "after-psd");

    const erpResponse = await waitForResponseAfter(
      page,
      "run ERP",
      (response) => response.url().includes("/api/tasks") && response.request().method() === "POST",
      () => clickEnabled(page, '[data-real-action="run-erp"]', "run ERP"),
      90000,
    );
    const erpTask = await erpResponse.json();
    evidence.erpTask = { id: erpTask.id, module_name: erpTask.module_name, status: erpTask.status };
    evidence.steps.push({ action: "click run-erp", status: "passed", taskId: erpTask.id });
    await waitForModuleResult(page, "erp");
    await sampleHealth(evidence, "after-erp");
    const tfrResponse = await waitForResponseAfter(
      page,
      "run TFR",
      (response) => response.url().includes("/api/tasks") && response.request().method() === "POST",
      () => clickEnabled(page, '[data-real-action="run-tfr"]', "run TFR"),
      120000,
    );
    const tfrTask = await tfrResponse.json();
    evidence.tfrTask = { id: tfrTask.id, module_name: tfrTask.module_name, status: tfrTask.status };
    evidence.steps.push({ action: "click run-tfr", status: "passed", taskId: tfrTask.id });
    await waitForModuleResult(page, "tfr");
    await sampleHealth(evidence, "after-tfr");

    const pacResponse = await waitForResponseAfter(
      page,
      "run PAC",
      (response) => response.url().includes("/api/tasks") && response.request().method() === "POST",
      () => clickEnabled(page, '[data-real-action="run-pac"]', "run PAC"),
      120000,
    );
    const pacTask = await pacResponse.json();
    evidence.pacTask = { id: pacTask.id, module_name: pacTask.module_name, status: pacTask.status };
    evidence.steps.push({ action: "click run-pac", status: "passed", taskId: pacTask.id });
    await waitForModuleResult(page, "pac");
    await sampleHealth(evidence, "after-pac");
    await screenshot(page, "04-analysis-results", evidence);

    await clickEnabled(page, '[data-view="statistics"]', "open results");
    const resultState = await visibleState(page);
    evidence.resultState = resultState;
    evidence.checks.resultPageShowsTasks = /PSD \/ Bandpower/i.test(resultState.resultText)
      && /ERP \/ P300/i.test(resultState.resultText)
      && /TFR \/ ERSP \/ ITC/i.test(resultState.resultText)
      && /PAC \/ CFC/i.test(resultState.resultText);

    const reportResponse = await waitForResponseAfter(
      page,
      "create report",
      (response) => response.url().includes("/api/reports") && response.request().method() === "POST",
      () => clickEnabled(page, '[data-real-action="create-report"]', "create report"),
      60000,
    );
    const report = await reportResponse.json();
    evidence.report = { id: report.id, title: report.title };
    evidence.steps.push({ action: "click create-report", status: "passed", reportId: report.id });
    await sampleHealth(evidence, "after-create-report");

    await clickEnabled(page, '[data-view="publication"]', "open publication");
    const deliveryBeforeDownload = await visibleState(page);
    evidence.deliveryState = deliveryBeforeDownload;
    evidence.reportDownloadLinks = await page.evaluate(() => {
      const readLink = (kind) => {
        const node = document.querySelector(`[data-report-download="${kind}"]`);
        return node
        ? {
            outerHTML: node.outerHTML,
            href: node.getAttribute("href"),
            tagName: node.tagName,
            text: node.textContent?.trim() || "",
            downloadAuthorizedFileType: typeof window.downloadAuthorizedFile,
          }
        : null;
      };
      return {
        package: readLink("package"),
        html: readLink("html"),
      };
    });
    evidence.reportDownloadDom = evidence.reportDownloadLinks.package;
    const packageHref = evidence.reportDownloadLinks.package?.href || "";
    const htmlHref = evidence.reportDownloadLinks.html?.href || "";
    evidence.reportDownloadContract = {
      packageLinkPresent: Boolean(evidence.reportDownloadLinks.package),
      htmlLinkPresent: Boolean(evidence.reportDownloadLinks.html),
      packageHrefMatchesReport: packageHref.includes(`/reports/${report.id}/package`),
      htmlHrefMatchesReport: htmlHref.includes(`/reports/${report.id}/html`),
    };
    evidence.checks.deliveryPageShowsReport = Object.values(evidence.reportDownloadContract).every(Boolean);
    const reportZipPath = path.join(OUT_DIR, `${report.id}.zip`);
    const packageDownload = await Promise.all([
      page.waitForEvent("download", { timeout: 30000 }),
      page.locator('[data-report-download="package"]:visible').first().click(),
    ]).then(([item]) => item);
    await packageDownload.saveAs(reportZipPath);
    const stat = fs.statSync(reportZipPath);
    const reportZipInspect = inspectReportZip(reportZipPath);
    evidence.reportZipInspect = reportZipInspect;
    evidence.downloads.push({ requirement: "report package zip", path: reportZipPath, bytes: stat.size, header: zipHeader(reportZipPath) });
    evidence.checks.reportZipDownloaded = stat.size > 0 && zipHeader(reportZipPath) === "504b0304";
    const includedModules = new Set((reportZipInspect.included_analyses || []).map((item) => item.module_name));
    evidence.checks.reportZipIncludesMainlineModules = ["psd", "erp", "tfr", "pac"].every((moduleName) => includedModules.has(moduleName));
    evidence.checks.reportZipHasAnalysisDirectories = ["psd", "erp", "tfr", "pac"].every((moduleName) => {
      return (reportZipInspect.analysis_prefixes || []).some((prefix) => prefix.startsWith(`${moduleName}_`));
    });
    evidence.pdfOcrArtifactQa = runPdfOcrArtifactQa(reportZipPath);
    evidence.checks.pdfOcrArtifactQaPassed = evidence.pdfOcrArtifactQa.status === "passed"
      && evidence.pdfOcrArtifactQa.requirement_id === "QLANALYSER_PDF_OCR_ARTIFACT_QA_READY"
      && evidence.pdfOcrArtifactQa.primary_parse === "PaddleOCR_all_pages"
      && evidence.pdfOcrArtifactQa.auxiliary_text_layer_audit === "yes"
      && evidence.pdfOcrArtifactQa.artifact_validator_verdict === "pass"
      && evidence.pdfOcrArtifactQa.blockers.length === 0
      && path.resolve(evidence.pdfOcrArtifactQa.report_zip_path || "") === path.resolve(reportZipPath);
    await sampleHealth(evidence, "after-report-download");
    finalizeServiceHealthChecks(evidence);
    await screenshot(page, "05-report-downloaded", evidence);

    evidence.status = evidence.checks.uploadedEdfDetected
      && evidence.qcTask.status === "completed"
      && evidence.metadataQcTask.status === "completed"
      && evidence.plan.status === "confirmed"
      && Boolean(evidence.epochSet.id)
      && evidence.psdTask.status === "completed"
      && evidence.erpTask.status === "completed"
      && evidence.tfrTask.status === "completed"
      && evidence.pacTask.status === "completed"
      && evidence.checks.resultPageShowsTasks
      && evidence.checks.deliveryPageShowsReport
      && evidence.checks.reportZipDownloaded
      && evidence.checks.reportZipIncludesMainlineModules
      && evidence.checks.reportZipHasAnalysisDirectories
      && evidence.checks.pdfOcrArtifactQaPassed
      && evidence.checks.backendHealthSamplesOk
      && evidence.checks.backendProcessStable
      && evidence.errors.length === 0
      ? "passed"
      : "failed";
  } catch (error) {
    evidence.status = "failed";
    evidence.errors.push(error.message);
    await sampleHealth(evidence, "after-failure").catch(() => null);
    finalizeServiceHealthChecks(evidence, true);
    evidence.failureState = await page.evaluate(() => ({
      view: document.querySelector(".view.active")?.id || "",
      status: document.querySelector("#realRuntimeStatus")?.textContent?.trim() || "",
      segment: document.querySelector("#segmentSummary")?.textContent?.trim() || "",
      toast: document.querySelector("#toast")?.textContent?.trim() || "",
      previewRecoveryButton: {
        disabled: document.querySelector('[data-real-action="run-qc-preview-inline"]')?.disabled,
        ariaDisabled: document.querySelector('[data-real-action="run-qc-preview-inline"]')?.getAttribute("aria-disabled"),
        title: document.querySelector('[data-real-action="run-qc-preview-inline"]')?.getAttribute("title"),
        text: document.querySelector('[data-real-action="run-qc-preview-inline"]')?.innerText,
      },
      audit: window.qlanalyserUiActionAudit || [],
      resources: performance.getEntriesByType("resource").map((item) => item.name).filter((name) => name.includes("/api/")).slice(-20),
    })).catch((stateError) => ({ error: stateError.message }));
    await screenshot(page, "error", evidence).catch(() => {});
  } finally {
    await browser.close();
    writeEvidence(evidence);
  }
  console.log(stringifyEvidence(evidence));
  if (evidence.status !== "passed") process.exit(1);
}

main().catch((error) => {
  ensureDir();
  writeEvidence({ status: "failed", error: error.message });
  console.error(error);
  process.exit(1);
});
