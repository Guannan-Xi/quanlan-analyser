import { chromium, chromiumLaunchOptions, classifyAcceptanceFailure } from "./lib/playwright_runtime.mjs";

const DEFAULT_API_URL = "http://127.0.0.1:8001/api";
const DEFAULT_FRONTEND_URL = "http://127.0.0.1:4174/module-lab.html";
const ACCEPTANCE_MARK = "public-demo-run";
const RUN_FAILED_RE = /\u8fd0\u884c\u5931\u8d25/;

const BACKEND_MODULE_BY_METHOD = {
  epilepsy_std: "epilepsy",
  epilepsy_lab_std: "epilepsy",
  multitaper_psd: "multitaper_psd_tfr",
  multitaper_tfr: "multitaper_psd_tfr",
};

function argValue(name) {
  const exactIndex = process.argv.indexOf(`--${name}`);
  if (exactIndex >= 0) return process.argv[exactIndex + 1] || "";
  const prefix = `--${name}=`;
  return process.argv.find((item) => item.startsWith(prefix))?.slice(prefix.length) || "";
}

function trimTrailingSlash(value) {
  return String(value || "").replace(/\/+$/, "");
}

function configuredTarget() {
  const rawFrontendUrl = argValue("frontend-url")
    || process.env.QLANALYSER_FRONTEND_URL
    || process.env.FRONTEND_URL
    || DEFAULT_FRONTEND_URL;
  const frontend = new URL(rawFrontendUrl);
  const rawApiUrl = argValue("api-url")
    || process.env.QLANALYSER_API_URL
    || process.env.QLANALYSER_API_BASE_URL
    || process.env.API_URL
    || frontend.searchParams.get("api")
    || DEFAULT_API_URL;
  const apiUrl = trimTrailingSlash(rawApiUrl);
  frontend.searchParams.set("api", apiUrl);
  frontend.searchParams.set("acceptance", ACCEPTANCE_MARK);
  return { frontendUrl: frontend.toString(), apiUrl };
}

function healthUrlFor(apiUrl) {
  return `${trimTrailingSlash(apiUrl)}/health`;
}

async function fetchProbe(url, { expectModuleLab = false } = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 4000);
  try {
    const response = await fetch(url, { signal: controller.signal });
    const text = expectModuleLab ? await response.text() : "";
    const servesModuleLab = expectModuleLab ? text.includes("module-lab.js") && text.includes("moduleLab") : undefined;
    return {
      url,
      ok: response.ok && (expectModuleLab ? servesModuleLab : true),
      status: response.status,
      servesModuleLab,
    };
  } catch (error) {
    return { url, ok: false, error: error.message || String(error) };
  } finally {
    clearTimeout(timeout);
  }
}

function safePath(url) {
  try {
    const parsed = new URL(url);
    return parsed.pathname;
  } catch (_) {
    return String(url || "");
  }
}

function relevantApiUrl(url) {
  const path = safePath(url);
  return path.includes("/api/") || path.includes("/lab/demo/");
}

function methodBackendId(methodId) {
  return BACKEND_MODULE_BY_METHOD[methodId] || methodId;
}

async function ensureMethodVisible(page, methodId) {
  const form = page.locator(`[data-runner-form="${methodId}"]`);
  if (await form.isVisible().catch(() => false)) return form;
  const switchButton = page.locator(`[data-target-method="${methodId}"]`);
  if (await switchButton.count()) await switchButton.first().click();
  await form.waitFor({ state: "visible", timeout: 20000 });
  return form;
}

async function setStableParameters(form, methodId) {
  if (methodId === "psd" || methodId === "band_power") {
    await form.locator('input[name="fmin"]').fill("2");
    await form.locator('input[name="fmax"]').fill("35");
    return;
  }
  if (methodId === "qc") {
    await form.locator('input[name="min_sampling_rate_hz"]').fill("100");
    await form.locator('input[name="min_duration_sec"]').fill("5");
    await form.locator('input[name="bad_channel_limit"]').fill("2");
  }
}

function protectedPathHrefs(hrefs) {
  return hrefs.filter((href) => {
    const path = safePath(href);
    return /\/api\/tasks\/[^/]+\/artifacts(?:\/|$)/.test(path)
      || /\/api\/artifacts\/[^/]+\/download(?:\/|$)/.test(path);
  });
}

async function main() {
  const { frontendUrl, apiUrl } = configuredTarget();
  const methodId = argValue("method") || process.env.QLANALYSER_MODULE_LAB_PUBLIC_DEMO_METHOD || "psd";
  const backendModuleId = methodBackendId(methodId);
  const timeoutMs = Number(argValue("timeout-ms") || process.env.QLANALYSER_MODULE_LAB_PUBLIC_DEMO_TIMEOUT_MS || 180000);
  const evidence = {
    status: "running",
    startedAt: new Date().toISOString(),
    frontendUrl,
    apiUrl,
    methodId,
    backendModuleId,
    checks: {},
    serviceHealth: [],
    requests: [],
    responses: [],
    artifactHrefs: [],
    errors: [],
    blockers: [],
  };

  const backendHealth = await fetchProbe(healthUrlFor(apiUrl));
  const frontendHealth = await fetchProbe(frontendUrl, { expectModuleLab: true });
  evidence.serviceHealth.push({ kind: "backend", ...backendHealth });
  evidence.serviceHealth.push({ kind: "frontend", ...frontendHealth });
  if (!backendHealth.ok || !frontendHealth.ok) {
    evidence.status = "blocked";
    evidence.blockers.push("service_unreachable");
    evidence.finishedAt = new Date().toISOString();
    console.log(JSON.stringify(evidence, null, 2));
    process.exit(1);
  }

  let browser;
  let phase = "load";
  try {
    browser = await chromium.launch(chromiumLaunchOptions({ headless: true }));
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });

    page.on("request", (request) => {
      if (!relevantApiUrl(request.url())) return;
      const headers = request.headers();
      evidence.requests.push({
        phase,
        method: request.method(),
        url: request.url(),
        hasAuthorization: Boolean(headers.authorization),
      });
    });
    page.on("response", (response) => {
      if (!relevantApiUrl(response.url())) return;
      evidence.responses.push({
        phase,
        method: response.request().method(),
        url: response.url(),
        status: response.status(),
        ok: response.ok(),
      });
    });
    page.on("pageerror", (error) => evidence.errors.push(error.message || String(error)));
    page.on("console", (msg) => {
      const text = msg.text();
      if (msg.type() === "error" && !text.includes("Failed to load resource")) {
        evidence.errors.push(text);
      }
    });

    const datasetResponsePromise = page.waitForResponse(
      (response) => response.url().includes("/api/lab/demo/dataset"),
      { timeout: 30000 },
    ).catch((error) => ({ acceptanceError: error.message || String(error) }));

    await page.goto(frontendUrl, { waitUntil: "domcontentloaded", timeout: 60000 });
    await page.waitForSelector("[data-method-group]", { timeout: 30000 });
    const datasetResponse = await datasetResponsePromise;
    if (datasetResponse.acceptanceError) throw new Error(`demo_dataset_not_loaded:${datasetResponse.acceptanceError}`);
    evidence.checks.demoDatasetStatus = datasetResponse.status();
    evidence.checks.demoDatasetOk = datasetResponse.ok();
    const datasetPayload = await datasetResponse.json().catch(() => null);
    evidence.checks.demoDatasetFileId = datasetPayload?.file?.id || "";

    const form = await ensureMethodVisible(page, methodId);
    await page.locator("#labDemoModeButton").click();
    const datasetSelect = form.locator('select[name="dataset"]');
    await datasetSelect.waitFor({ state: "visible", timeout: 15000 });
    await datasetSelect.selectOption("__demo__");
    await setStableParameters(form, methodId);

    const selectedDataset = await datasetSelect.inputValue();
    const fileInputCount = await page.locator("#labEegFile").evaluate((node) => node.files.length);
    evidence.checks.datasetSelectValue = selectedDataset;
    evidence.checks.noCustomerFileSelected = selectedDataset === "__demo__" && fileInputCount === 0;

    const runResponsePromise = page.waitForResponse(
      (response) => response.url().includes(`/api/lab/demo/run/${backendModuleId}/configured`)
        && response.request().method() === "POST",
      { timeout: timeoutMs },
    );
    const artifactResponsePromise = page.waitForResponse(
      (response) => response.url().includes("/api/lab/demo/artifacts/")
        && !response.url().includes("/download/")
        && response.request().method() === "GET",
      { timeout: timeoutMs },
    );

    phase = "run";
    await form.locator('button[type="submit"]').click();
    const runResponse = await runResponsePromise;
    const taskPayload = await runResponse.json();
    const artifactResponse = await artifactResponsePromise;
    const artifactPayload = await artifactResponse.json();

    evidence.checks.runStatus = runResponse.status();
    evidence.checks.runOk = runResponse.ok();
    evidence.checks.artifactListStatus = artifactResponse.status();
    evidence.checks.artifactListOk = artifactResponse.ok();
    evidence.checks.taskId = taskPayload?.id || "";
    evidence.checks.taskStatus = taskPayload?.status || "";
    evidence.checks.taskWorkflow = taskPayload?.workflow_id || "";
    evidence.checks.taskLabPreviewRun = taskPayload?.parameters_json?.lab_preview_run === true;
    evidence.checks.taskDeliveryScope = taskPayload?.parameters_json?.delivery_scope || "";
    evidence.checks.taskDataSourceType = taskPayload?.parameters_json?.data_source_type || "";
    evidence.checks.artifactCountFromApi = Array.isArray(artifactPayload) ? artifactPayload.length : 0;

    await page.waitForFunction(
      (id) => {
        const result = document.querySelector(`[data-result="${id}"]`);
        return Boolean(result?.querySelector('[data-testid="method-summary"]'))
          && result.querySelectorAll('a.artifact[href*="/lab/demo/artifacts/"]').length > 0;
      },
      methodId,
      { timeout: timeoutMs },
    );

    const resultBox = page.locator(`[data-result="${methodId}"]`);
    const bodyText = await page.locator("body").evaluate((node) => node.textContent || "");
    const resultText = await resultBox.evaluate((node) => node.textContent || "");
    const artifactHrefs = await resultBox.locator("a.artifact").evaluateAll((links) =>
      links.map((link) => link.href),
    );
    evidence.artifactHrefs = artifactHrefs;

    const protectedHrefs = protectedPathHrefs(artifactHrefs);
    const protectedTaskRequests = evidence.requests.filter((request) =>
      /\/api\/tasks(?:\/|$)/.test(safePath(request.url)),
    );
    const protectedArtifactRequests = evidence.requests.filter((request) =>
      /\/api\/artifacts\/[^/]+\/download(?:\/|$)/.test(safePath(request.url)),
    );
    const uploadRequests = evidence.requests.filter((request) => safePath(request.url).includes("/api/eeg/upload"));
    const authHeaderRequests = evidence.requests.filter((request) => request.hasAuthorization);

    evidence.checks.noBearerTokenRequiredVisible = !bodyText.includes("Bearer token required");
    evidence.checks.noRunFailedVisible = !RUN_FAILED_RE.test(bodyText);
    evidence.checks.noVisibleErrorBox = await page.locator(".demo-status.error").count() === 0;
    evidence.checks.resultMentionsWorkflow = resultText.includes(evidence.checks.taskWorkflow);
    evidence.checks.hasPublicDemoArtifactHref = artifactHrefs.some((href) => href.includes("/lab/demo/artifacts/"));
    evidence.checks.allArtifactHrefsArePublicDemo = artifactHrefs.length > 0
      && artifactHrefs.every((href) => href.includes("/lab/demo/artifacts/"));
    evidence.checks.noProtectedArtifactHref = protectedHrefs.length === 0;
    evidence.checks.noProtectedTaskArtifactRequest = protectedTaskRequests.length === 0;
    evidence.checks.noProtectedArtifactDownloadRequest = protectedArtifactRequests.length === 0;
    evidence.checks.noUploadRequest = uploadRequests.length === 0;
    evidence.checks.noAuthorizationHeader = authHeaderRequests.length === 0;
    evidence.checks.completedTask = evidence.checks.taskStatus === "completed";
    evidence.checks.labPreviewOnlyTask = evidence.checks.taskLabPreviewRun
      && evidence.checks.taskDeliveryScope === "lab_preview_only"
      && evidence.checks.taskDataSourceType === "teaching_demo";

    if (!evidence.checks.noBearerTokenRequiredVisible) evidence.blockers.push("bearer_token_required_visible");
    if (!evidence.checks.noRunFailedVisible || !evidence.checks.noVisibleErrorBox) evidence.blockers.push("visible_error_state");
    if (!evidence.checks.noCustomerFileSelected) evidence.blockers.push("customer_file_selected");
    if (!evidence.checks.hasPublicDemoArtifactHref) evidence.blockers.push("missing_public_demo_artifact_href");
    if (!evidence.checks.allArtifactHrefsArePublicDemo || !evidence.checks.noProtectedArtifactHref) {
      evidence.blockers.push("protected_artifact_href");
    }
    if (!evidence.checks.noProtectedTaskArtifactRequest || !evidence.checks.noProtectedArtifactDownloadRequest) {
      evidence.blockers.push("protected_artifact_request");
    }
    if (!evidence.checks.noUploadRequest) evidence.blockers.push("unexpected_upload_request");
    if (!evidence.checks.noAuthorizationHeader) evidence.blockers.push("authorization_header_present");
    if (!evidence.checks.completedTask) evidence.blockers.push("task_not_completed");
    if (!evidence.checks.labPreviewOnlyTask) evidence.blockers.push("demo_task_not_lab_preview_only");
    if (evidence.errors.length) evidence.blockers.push("browser_error");

    evidence.status = evidence.blockers.length === 0 ? "passed" : "failed";
  } catch (error) {
    evidence.status = classifyAcceptanceFailure(error, evidence) === "service_unreachable" ? "blocked" : "failed";
    evidence.errors.push(error.message || String(error));
    if (evidence.status === "blocked") evidence.blockers.push("service_unreachable");
    else evidence.blockers.push("public_demo_run_failed");
  } finally {
    if (browser) await browser.close().catch(() => {});
  }

  evidence.finishedAt = new Date().toISOString();
  console.log(JSON.stringify(evidence, null, 2));
  if (evidence.status !== "passed") process.exit(1);
}

main();
