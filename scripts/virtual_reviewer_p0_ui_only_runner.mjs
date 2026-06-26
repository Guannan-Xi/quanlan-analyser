import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const { chromium } = require("../frontend/node_modules/playwright");
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");
const API_BASE = process.env.QLANALYSER_API_URL || "http://127.0.0.1:8001/api";
const FRONTEND_URL =
  process.env.QLANALYSER_FRONTEND_URL ||
  `http://127.0.0.1:4174/?customer_demo=auto&api=${encodeURIComponent(API_BASE)}`;
const FIXTURE =
  process.env.QLANALYSER_P0_UI_SAMPLE ||
  path.join(ROOT, "work", "fixtures", "p0_modules", "p0_synthetic_with_events_raw.fif");
const CUSTOMER_EMAIL = process.env.QLANALYSER_P0_UI_CUSTOMER_EMAIL || "demo.customer@quanlan.cn";
const CUSTOMER_PASSWORD = process.env.QLANALYSER_P0_UI_CUSTOMER_PASSWORD || "demo123456";
const OUT_DIR =
  process.env.QLANALYSER_P0_UI_EVIDENCE_DIR ||
  path.join(ROOT, "work", "release_evidence", "p0_ui_only_runner");
const EVIDENCE_PATH = path.join(OUT_DIR, "p0-ui-only-runner-evidence.json");

const P0_MODULES = [
  ["preprocessing_readiness", "MRO-ITC-0001", "MRO-FX-0001", "MRO-EO-0001", "MRO-VAL-0001"],
  ["event_epoch", "MRO-ITC-0002", "MRO-FX-0002", "MRO-EO-0002", "MRO-VAL-0002"],
  ["psd_bandpower", "MRO-ITC-0003", "MRO-FX-0003", "MRO-EO-0003", "MRO-VAL-0003"],
  ["erp_p300", "MRO-ITC-0004", "MRO-FX-0004", "MRO-EO-0004", "MRO-VAL-0004"],
];

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function sha256File(filePath) {
  const hash = crypto.createHash("sha256");
  hash.update(fs.readFileSync(filePath));
  return hash.digest("hex");
}

function zipHeader(buffer) {
  return buffer.subarray(0, 4).toString("hex");
}

async function screenshot(page, name, evidence) {
  const file = path.join(OUT_DIR, `${name}.png`);
  await page.screenshot({ path: file, fullPage: true, timeout: 15000 }).catch(async () => {
    await page.locator("body").screenshot({ path: file, timeout: 15000 });
  });
  evidence.screenshots.push({ name, path: file });
  return file;
}

async function waitForUiResponse(page, label, predicate, action, timeout = 45000) {
  const responsePromise = page.waitForResponse(predicate, { timeout });
  await action();
  const response = await responsePromise;
  if (!response.ok()) {
    throw new Error(`${label} failed: ${response.status()} ${response.statusText()}`);
  }
  return response;
}

async function clickWhenEnabled(page, selector, timeout = 20000) {
  const locator = page.locator(selector).first();
  console.log(`[runner] waiting visible: ${selector}`);
  await locator.waitFor({ state: "visible", timeout });
  console.log(`[runner] visible: ${selector}`);
  await page.waitForFunction(
    (targetSelector) => {
      const element = document.querySelector(targetSelector);
      return Boolean(element && !element.disabled && element.getAttribute("aria-disabled") !== "true");
    },
    selector,
    { timeout },
  );
  console.log(`[runner] enabled: ${selector}`);
  await locator.click();
  console.log(`[runner] clicked: ${selector}`);
}

async function waitForTask(page, moduleName, label, actionName) {
  console.log(`[runner] task start: ${moduleName} via ${actionName}`);
  const response = await waitForUiResponse(
    page,
    label,
    (resp) => resp.url().includes(`${API_BASE}/tasks`) && resp.request().method() === "POST" && resp.status() === 200,
    () => clickWhenEnabled(page, `button[data-real-action="${actionName}"]`),
    60000,
  );
  console.log(`[runner] task response received: ${moduleName}`);
  const body = await response.json();
  if (body?.module_name !== moduleName) {
    throw new Error(`${label} returned unexpected module_name: ${body?.module_name || "missing"}`);
  }
  console.log(`[runner] task body ok: ${moduleName}`);
  return body;
}

async function hasVisible(page, selector) {
  return page.locator(selector).first().isVisible({ timeout: 2500 }).catch(() => false);
}

async function discoverUiCapabilities(page) {
  return {
    create_project: await hasVisible(page, 'button[data-real-action="create-project"]'),
    upload_eeg: await hasVisible(page, 'button[data-real-action="upload-eeg"]'),
    run_qc: await hasVisible(page, 'button[data-real-action="run-qc-preview-inline"]'),
    run_psd: await hasVisible(page, 'button[data-real-action="run-psd"]'),
    run_erp: await hasVisible(page, 'button[data-real-action="run-erp"]'),
    create_report: await hasVisible(page, 'button[data-real-action="create-report"]'),
    preprocessing_readiness_panel: await hasVisible(page, '[data-testid="preprocessing-readiness-panel"]'),
    confirm_plan_inline: await hasVisible(page, '[data-real-action="confirm-plan-inline"]'),
    download_plan_json: await hasVisible(page, '[data-real-action="download-plan-json"]'),
    readiness_checklist: await hasVisible(page, '[data-testid="readiness-checklist"]'),
    readiness_v01_boundary: await hasVisible(page, '[data-testid="readiness-v01-boundary"]'),
    qc_preview_inline: await hasVisible(page, '[data-real-action="run-qc-preview-inline"]'),
    bad_channel_audit_controls: await hasVisible(page, '[data-testid="bad-channel-audit-controls"]'),
    save_bad_channel_audit: await hasVisible(page, '[data-real-action="save-bad-channel-audit"]'),
    discard_bad_channel_audit: await hasVisible(page, '[data-real-action="discard-bad-channel-audit"]'),
    event_epoch_panel: await hasVisible(page, '[data-testid="event-epoch-panel"]'),
    save_epoch_set: await hasVisible(page, '[data-real-action="save-epoch-set"]'),
    download_epoch_manifest: await hasVisible(page, '[data-real-action="download-epoch-manifest"]'),
    event_mapping_table: await hasVisible(page, '[data-testid="event-mapping-table"]'),
    epoch_drop_log_preview: await hasVisible(page, '[data-testid="epoch-preview-drop-log"]'),
    epoch_manifest_preview: await hasVisible(page, '[data-testid="epoch-set-manifest-preview"]'),
    dedicated_preprocessing_crud: await hasVisible(page, '[data-module-id="preprocessing_readiness"], [data-real-action*="preprocess"]'),
    dedicated_event_epoch_crud: await hasVisible(page, '[data-testid="epoch-set-manager"], [data-module-id="event_epoch"]'),
  };
}

function inspectZip(packagePath) {
  const script = [
    "import csv, json, sys, zipfile",
    "from pathlib import Path",
    "package = Path(sys.argv[1])",
    "out = {'package_path': str(package), 'exists': package.exists(), 'entries': [], 'checks': {}, 'boundary_scan': {}}",
    "if package.exists():",
    "  with zipfile.ZipFile(package) as zf:",
    "    names = zf.namelist()",
    "    out['entries'] = names",
    "    out['checks']['report_pdf_present'] = 'reports/report.pdf' in names",
    "    out['checks']['report_json_present'] = 'reports/report.json' in names",
    "    out['checks']['metrics_csv_present'] = 'tables/metrics.csv' in names",
    "    out['checks']['manifest_present'] = any(name.endswith('manifest.json') for name in names)",
    "    out['checks']['csv_entries'] = [name for name in names if name.endswith('.csv')]",
    "    out['checks']['json_entries'] = [name for name in names if name.endswith('.json')]",
    "    text_blob = ''",
    "    for name in names:",
    "      if name.endswith(('.json', '.csv', '.txt', '.md', '.html')):",
    "        try:",
    "          text_blob += '\\n' + zf.read(name).decode('utf-8', errors='ignore')",
    "        except Exception:",
    "          pass",
    "    out['boundary_scan']['non_diagnostic_boundary'] = 'not for clinical diagnosis' in text_blob.lower() or '不用于临床诊断' in text_blob",
    "    out['boundary_scan']['forbidden_source_claims'] = [term for term in ['brain activation', 'source localization', 'diagnosis', 'treatment decision', 'causal'] if term in text_blob.lower()]",
    "    if 'reports/report.pdf' in names:",
    "      data = zf.read('reports/report.pdf')",
    "      out['checks']['pdf_header'] = data.startswith(b'%PDF')",
    "      out['checks']['pdf_size_bytes'] = len(data)",
    "      try:",
    "        import fitz",
    "        doc = fitz.open(stream=data, filetype='pdf')",
    "        pdf_text = '\\n'.join(page.get_text() for page in doc)",
    "        out['checks']['pdf_text_extractable'] = bool(pdf_text.strip())",
    "        out['checks']['pdf_method_summary'] = 'Method summary' in pdf_text or 'Effective parameters' in pdf_text",
    "        out['boundary_scan']['pdf_non_diagnostic_boundary'] = 'not for clinical diagnosis' in pdf_text.lower()",
    "        out['boundary_scan']['pdf_sensor_space_boundary'] = 'sensor/channel-space' in pdf_text.lower()",
    "      except Exception as exc:",
    "        out['checks']['pdf_text_extract_error'] = str(exc)",
    "    def read_text(name):",
    "      if name not in names:",
    "        return ''",
    "      return zf.read(name).decode('utf-8', 'replace')",
    "    def read_json(name):",
    "      text = read_text(name)",
    "      if not text:",
    "        return {}",
    "      try:",
    "        return json.loads(text)",
    "      except Exception:",
    "        return {}",
    "    def flatten_text(value):",
    "      if isinstance(value, dict):",
    "        return ' '.join(flatten_text(v) for v in value.values())",
    "      if isinstance(value, list):",
    "        return ' '.join(flatten_text(v) for v in value)",
    "      return str(value)",
    "    result_json = read_json('result.json')",
    "    report_json = read_json('reports/report.json')",
    "    manifest_json = read_json('manifest.json')",
    "    workflow_json = read_json('reproducibility/workflow.json')",
    "    software_versions = read_json('reproducibility/software_versions.json')",
    "    parameters_json = read_json('reproducibility/parameters.json')",
    "    json_text = ' '.join(flatten_text(item) for item in [result_json, report_json, manifest_json, workflow_json, software_versions, parameters_json]).lower()",
    "    created_at = result_json.get('created_at') or manifest_json.get('created_at') or report_json.get('generated_at')",
    "    parameters = result_json.get('parameters') or report_json.get('parameters') or parameters_json.get('parameters')",
    "    workflow_steps = workflow_json.get('steps') or result_json.get('processing_steps') or report_json.get('processing_steps')",
    "    source_metadata_present = bool(result_json.get('input') or report_json.get('task', {}).get('input_file_id') or any((item.get('sha256') and item.get('path')) for item in manifest_json.get('files', []) if isinstance(item, dict)))",
    "    out['report_pdf_present'] = bool(out['checks'].get('report_pdf_present'))",
    "    out['pdf_checks'] = {",
    "      'pdf_header': bool(out['checks'].get('pdf_header')),",
    "      'text_extractable': bool(out['checks'].get('pdf_text_extractable')),",
    "      'method_summary': bool(out['checks'].get('pdf_method_summary')),",
    "    }",
    "    out['json_checks'] = {",
    "      'schema_version': bool(result_json.get('schema_version') or report_json.get('schema_version') or manifest_json.get('schema_version')),",
    "      'parameters': bool(parameters),",
    "      'processing_steps': bool(workflow_steps),",
    "      'software_or_workflow_reference': bool(workflow_json or software_versions),",
    "      'timestamp': bool(created_at),",
    "      'warnings_field': 'warnings' in report_json or 'warnings' in result_json,",
    "      'warnings_or_boundary': any(term in json_text for term in ['not for clinical diagnosis', 'single-record', 'sensor-space', 'non-diagnostic', 'clinical diagnosis']),",
    "      'source_metadata': source_metadata_present,",
    "      'workflow_json': bool(workflow_json),",
    "    }",
    "    csv_headers = []",
    "    for csv_name in out['checks'].get('csv_entries', []):",
    "      try:",
    "        first_line = read_text(csv_name).splitlines()[0]",
    "      except Exception:",
    "        first_line = ''",
    "      csv_headers.extend([cell.strip().lower() for cell in first_line.split(',') if cell.strip()])",
    "    header_text = ' '.join(csv_headers)",
    "    out['csv_checks'] = {",
    "      'table_dictionary_present': 'table_dictionary' in report_json or any(item.get('type') == 'table' for item in manifest_json.get('files', []) if isinstance(item, dict)),",
    "      'units_present': any(unit in header_text for unit in ['_uv', '_ms', '_hz', 'unit', 'units']),",
    "      'band_power_csv': any(term in header_text for term in ['band_power', 'frequency', 'freq_hz', 'band']),",
    "      'channel_band_power_csv': any('channel_band_power' in name or 'band_power' in name for name in out['checks'].get('csv_entries', [])),",
    "      'erp_csv': all(term in header_text for term in ['component', 'amplitude_uv', 'latency_ms']),",
    "      'channel_or_frequency_labels': any(term in header_text for term in ['channel', 'roi_channels', 'frequency', 'freq', 'band']),",
    "      'headers': csv_headers,",
    "    }",
    "    combined_text = (json_text + ' ' + str(out.get('boundary_scan', {})).lower())",
    "    source_overclaim_terms = ['brain activation map', 'brain-region activation', 'brain region activation map', 'source-localized', 'source localized', 'cortical source estimate', 'localized brain source']",
    "    out['boundary_checks'] = {",
    "      'non_diagnostic_boundary': bool(out['boundary_scan'].get('non_diagnostic_boundary') or out['boundary_scan'].get('pdf_non_diagnostic_boundary') or 'not for clinical diagnosis' in combined_text),",
    "      'psd_sensor_space_boundary': bool(out['boundary_scan'].get('pdf_sensor_space_boundary') or 'sensor/channel-space' in combined_text or 'sensor-space' in combined_text or 'sensor space' in combined_text),",
    "      'no_source_claim': not any(term in combined_text for term in source_overclaim_terms),",
    "    }",
    "print(json.dumps(out, ensure_ascii=False))",
  ].join("\n");
  const proc = spawnSync("python", ["-c", script, packagePath], { encoding: "utf8" });
  if (proc.status !== 0) {
    return { error: proc.stderr || proc.stdout || `python exited ${proc.status}` };
  }
  return JSON.parse(proc.stdout);
}

async function run() {
  ensureDir(OUT_DIR);
  const evidence = {
    protocol: "QLANALYSER_P0_UI_ONLY_RUNNER",
    implementation_packet_marker: "P0_UI_ONLY_RUNNER_PACKET_READY",
    generated_at: new Date().toISOString(),
    frontend_url: FRONTEND_URL,
    api_base: API_BASE,
    ui_only_policy: {
      real_user_path: "click/upload/wait/screenshot/download through visible UI only",
      direct_api_task_mutation_allowed: false,
      api_allowed_only_for: ["network evidence caused by UI clicks", "artifact inspection of UI-exposed downloads"],
    },
    no_direct_api_mutation: true,
    direct_api_mutations: [],
    p0_modules: Object.fromEntries(
      P0_MODULES.map(([module_id, itc, fixture_requirement, expected_output_requirement, artifact_validator]) => [
        module_id,
        {
          module_id,
          interaction_test_case: itc,
          fixture_requirement,
          expected_output_requirement,
          artifact_validator,
          status: "pending",
        },
      ]),
    ),
    fixture: {
      path: FIXTURE,
      exists: fs.existsSync(FIXTURE),
      size_bytes: fs.existsSync(FIXTURE) ? fs.statSync(FIXTURE).size : null,
      sha256: fs.existsSync(FIXTURE) ? sha256File(FIXTURE) : null,
      privacy_boundary: "synthetic software-test FIF; no real participant/customer/PHI data",
    },
    runner_plan_coverage: ["click", "upload", "wait", "screenshot", "download", "artifact_inspect"],
    requests_observed: [],
    responses_observed: [],
    ui_capabilities: {},
    steps: [],
    screenshots: [],
    downloads: [],
    product_gaps: [],
    artifact_inspect: {},
    warnings: [],
  };

  if (!evidence.fixture.exists) throw new Error(`Fixture missing: ${FIXTURE}`);

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ acceptDownloads: true, viewport: { width: 1440, height: 1000 } });
  await context.tracing.start({ screenshots: true, snapshots: true, sources: false });
  const page = await context.newPage();

  page.on("request", (request) => {
    if (request.url().includes("/api/")) {
      evidence.requests_observed.push({
        method: request.method(),
        url: request.url(),
        resource_type: request.resourceType(),
      });
    }
  });
  page.on("response", (response) => {
    if (response.url().includes("/api/")) {
      evidence.responses_observed.push({
        status: response.status(),
        url: response.url(),
        method: response.request().method(),
      });
    }
  });
  page.on("close", () => {
    evidence.warnings.push("page_closed_event_observed");
    console.log("[runner] page closed");
  });
  page.on("crash", () => {
    evidence.warnings.push("page_crash_event_observed");
    console.log("[runner] page crashed");
  });
  page.on("pageerror", (error) => {
    evidence.warnings.push(`pageerror:${error?.message || String(error)}`);
    console.log("[runner] pageerror", error?.message || String(error));
  });
  page.on("requestfailed", (request) => {
    evidence.warnings.push(`requestfailed:${request.method()} ${request.url()}`);
    console.log("[runner] requestfailed", request.method(), request.url());
  });
  page.on("console", (message) => {
    if (message.type() === "error" || message.type() === "warning") {
      evidence.warnings.push(`console:${message.type()}:${message.text()}`);
      console.log("[runner] console", message.type(), message.text());
    }
  });

  try {
    await page.goto(FRONTEND_URL, { waitUntil: "domcontentloaded" });
    await page.waitForSelector("#loginScreen, #appShell", { timeout: 20000 });
    const shellVisible = await page.locator("#appShell").isVisible().catch(() => false);
    if (!shellVisible) {
      await page.locator("#customerEmail").fill(CUSTOMER_EMAIL);
      await page.locator("#customerPassword").fill(CUSTOMER_PASSWORD);
      await page.locator("#rememberCustomer").check().catch(() => {});
      await clickWhenEnabled(page, "#customerLoginBtn");
      await page.waitForSelector("#appShell:not([hidden])", { timeout: 20000 });
    }
    evidence.ui_capabilities = await discoverUiCapabilities(page);
    evidence.ui_capabilities_by_view = { dashboard: { ...evidence.ui_capabilities } };
    await screenshot(page, "p0-ui-01-dashboard", evidence);

    const projectResponse = await waitForUiResponse(
      page,
      "create project",
      (response) => response.url().includes(`${API_BASE}/projects`) && response.request().method() === "POST",
      () => page.click('button[data-real-action="create-project"]'),
    );
    const project = await projectResponse.json();
    evidence.project_id = project.id;
    evidence.steps.push({ action: "click", target: "create-project", status: "passed", project_id: project.id });
    await screenshot(page, "p0-ui-02-project-created", evidence);

    await page.setInputFiles("#real-eeg-file", FIXTURE);
    const uploadResponse = await waitForUiResponse(
      page,
      "upload synthetic P0 fixture",
      (response) => response.url().includes(`${API_BASE}/eeg/upload`) && response.status() === 200,
      () => page.click('button[data-real-action="upload-eeg"]'),
      30000,
    );
    const uploaded = await uploadResponse.json();
    evidence.uploaded_file_id = uploaded.id;
    evidence.metadata_preview = {
      filename: uploaded.original_filename,
      detected_format: uploaded.detected_format,
      sampling_rate: uploaded.sampling_rate,
      channel_count: uploaded.channel_count,
      duration_sec: uploaded.duration_sec,
      metadata_keys: Object.keys(uploaded.metadata_json || {}),
    };
    evidence.steps.push({ action: "upload", target: "upload-eeg", status: "passed", file_id: uploaded.id });
    await screenshot(page, "p0-ui-03-upload-metadata-preview", evidence);

    await clickWhenEnabled(page, 'button[data-view-jump="analysis"]');
    evidence.steps.push({ action: "click", target: "data-view-jump=analysis", status: "passed" });
    await page.waitForSelector('[data-testid="data-preparation-workbench"]', { timeout: 20000 }).catch(() => {});
    await screenshot(page, "p0-ui-03b-analysis-workbench-open", evidence);

    const qcTask = await waitForTask(page, "qc", "run QC/data preparation", "run-qc-preview-inline");
    evidence.p0_modules.preprocessing_readiness.status = "ui_task_created";
    evidence.p0_modules.preprocessing_readiness.task_id = qcTask.id;
    evidence.p0_modules.preprocessing_readiness.ui_path = ["create-project", "upload-eeg", "run-qc-preview-inline"];
    evidence.steps.push({ action: "click/wait", target: "run-qc-preview-inline", status: "passed", task_id: qcTask.id });
    await screenshot(page, "p0-ui-04-qc-data-preparation", evidence);

    const planResponse = await waitForUiResponse(
      page,
      "confirm data-preparation plan",
      (response) => response.url().includes(`${API_BASE}/data-preparation/plans`) && response.request().method() === "POST" && response.status() === 200,
      () => page.click('[data-real-action="confirm-plan-inline"]'),
      30000,
    );
    const plan = await planResponse.json();
    evidence.confirm_response_plan = {
      id: plan.id,
      revision: plan.revision,
      status: plan.status,
      schema_version: plan.schema_version,
      module_scope: plan.module_scope,
      preprocessing_json: plan.preprocessing_json,
      artifact_contract_json: plan.artifact_contract_json,
    };
    evidence.p0_modules.preprocessing_readiness.status = "confirmed_plan_created";
    evidence.p0_modules.preprocessing_readiness.plan_id = plan.id;
    evidence.p0_modules.preprocessing_readiness.plan_revision = plan.revision;
    evidence.p0_modules.preprocessing_readiness.ui_path.push("confirm-plan-inline");
    evidence.steps.push({ action: "click/wait", target: "confirm-plan-inline", status: "passed", plan_id: plan.id, revision: plan.revision });
    await screenshot(page, "p0-ui-05-confirmed-data-preparation-plan", evidence);

    await clickWhenEnabled(page, 'button[data-view="analysis"]');
    evidence.steps.push({ action: "click", target: "data-view=analysis", status: "passed" });
    await page.waitForSelector('[data-testid="data-preparation-workbench"]', { timeout: 20000 }).catch(() => {});
    evidence.ui_capabilities_by_view.analysis = await discoverUiCapabilities(page);
    const analysisCaps = evidence.ui_capabilities_by_view.analysis;
    if (!analysisCaps.preprocessing_readiness_panel || !analysisCaps.confirm_plan_inline) {
      evidence.product_gaps.push({
        module_id: "preprocessing_readiness",
        severity: "P0",
        gap: "No visible preprocessing readiness panel or data-preparation confirmation action was found in the analysis workbench view.",
        required_action: "Expose a visible data-preparation confirmation UI and persist a confirmed plan before PSD/ERP.",
      });
    } else if (!analysisCaps.dedicated_preprocessing_crud) {
      evidence.product_gaps.push({
        module_id: "preprocessing_readiness",
        severity: "P2",
        gap: "Data-preparation confirmation UI is present, but no full CRUD/special-preprocessing branch editor was found in the analysis workbench view.",
        required_action: "Add visible UI controls for module-specific preprocessing plan create/update/delete/review or document why V01 only supports fixed QC readiness.",
      });
    }
    if (!analysisCaps.event_epoch_panel) {
      evidence.product_gaps.push({
        module_id: "event_epoch",
        severity: "P0",
        gap: "No visible event/epoch parameter panel was found in the analysis workbench view.",
        required_action: "Expose event mapping, epoch window, and baseline controls before ERP/P300 UI-only validation.",
      });
    } else if (!analysisCaps.dedicated_event_epoch_crud) {
      evidence.product_gaps.push({
        module_id: "event_epoch",
        severity: "P1",
        gap: "Event/epoch parameter panel is present, but no standalone epoch_set CRUD, drop log, epoch_set_id, or manifest preview UI was found in the analysis workbench view.",
        required_action: "Add visible event/epoch set management UI with epoch_set_id/manifest preview before treating event_epoch as a standalone module.",
      });
    }

    const [planDownload] = await Promise.all([
      page.waitForEvent("download", { timeout: 15000 }),
      page.click('[data-real-action="download-plan-json"]'),
    ]);
    const planDownloadPath = path.join(OUT_DIR, planDownload.suggestedFilename() || `data_preparation_plan_${plan.id}.json`);
    await planDownload.saveAs(planDownloadPath);
    const downloadedPlan = JSON.parse(fs.readFileSync(planDownloadPath, "utf8"));
    evidence.data_preparation_plan = {
      id: downloadedPlan.id,
      revision: downloadedPlan.revision,
      status: downloadedPlan.status,
      schema_version: downloadedPlan.schema_version,
      module_scope: downloadedPlan.module_scope,
      preprocessing_json: downloadedPlan.preprocessing_json,
      artifact_contract_json: downloadedPlan.artifact_contract_json,
      source: "visible UI exported JSON",
    };
    evidence.p0_modules.preprocessing_readiness.plan_id = downloadedPlan.id;
    evidence.p0_modules.preprocessing_readiness.plan_revision = downloadedPlan.revision;
    evidence.downloads.push({
      requirement: "data_preparation_plan.json",
      via: "visible UI download-plan-json button",
      path: planDownloadPath,
      bytes: fs.statSync(planDownloadPath).size,
    });
    evidence.steps.push({ action: "download", target: "download-plan-json", status: "passed", path: planDownloadPath });

    const qcPreviewTask = await waitForTask(page, "qc", "run QC waveform preview", "run-qc-preview-inline");
    evidence.qc_preview_task = {
      task_id: qcPreviewTask.id,
      workflow_id: qcPreviewTask.workflow_id,
      status: qcPreviewTask.status,
      source: "visible UI run-qc-preview-inline button",
    };
    evidence.steps.push({ action: "click/wait", target: "run-qc-preview-inline", status: "passed", task_id: qcPreviewTask.id });

    const saveAuditResponse = await waitForUiResponse(
      page,
      "save bad-channel audit",
      (response) => response.url().includes(`${API_BASE}/eeg/files/`) && response.url().includes("/bad-channel-audit") && response.request().method() === "POST" && response.status() === 200,
      () => page.click('[data-real-action="save-bad-channel-audit"]'),
      30000,
    );
    const savedBadChannelAudit = await saveAuditResponse.json();
    evidence.bad_channel_audit = {
      audit_id: savedBadChannelAudit.audit_id,
      decision: savedBadChannelAudit.decision,
      plan_id: savedBadChannelAudit.plan_id,
      plan_revision: savedBadChannelAudit.plan_revision,
      channels_tsv_path: savedBadChannelAudit.channels_tsv_path,
      audit_json_path: savedBadChannelAudit.audit_json_path,
      ui_evidence_path: savedBadChannelAudit.ui_evidence_path,
      source_integrity_path: savedBadChannelAudit.source_integrity_path,
      artifact_root: savedBadChannelAudit.artifact_root,
      source: "visible UI save-bad-channel-audit button",
    };
    evidence.steps.push({ action: "click/wait", target: "save-bad-channel-audit", status: "passed", audit_id: savedBadChannelAudit.audit_id });

    const discardAuditResponse = await waitForUiResponse(
      page,
      "discard bad-channel audit",
      (response) => response.url().includes(`${API_BASE}/eeg/files/`) && response.url().includes("/bad-channel-audit") && response.request().method() === "POST" && response.status() === 200,
      () => page.click('[data-real-action="discard-bad-channel-audit"]'),
      30000,
    );
    const discardedBadChannelAudit = await discardAuditResponse.json();
    evidence.bad_channel_discard_audit = {
      audit_id: discardedBadChannelAudit.audit_id,
      decision: discardedBadChannelAudit.decision,
      plan_id: discardedBadChannelAudit.plan_id,
      plan_revision: discardedBadChannelAudit.plan_revision,
      channels_tsv_path: discardedBadChannelAudit.channels_tsv_path,
      audit_json_path: discardedBadChannelAudit.audit_json_path,
      ui_evidence_path: discardedBadChannelAudit.ui_evidence_path,
      source_integrity_path: discardedBadChannelAudit.source_integrity_path,
      artifact_root: discardedBadChannelAudit.artifact_root,
      source: "visible UI discard-bad-channel-audit button",
    };
    evidence.steps.push({ action: "click/wait", target: "discard-bad-channel-audit", status: "passed", audit_id: discardedBadChannelAudit.audit_id });
    await screenshot(page, "p0-ui-06-qc-preview-and-bad-channel-audit", evidence);

    const epochSetResponse = await waitForUiResponse(
      page,
      "save epoch set",
      (response) => response.url().includes(`${API_BASE}/eeg/files/`) && response.url().includes("/epoch-sets") && response.request().method() === "POST" && response.status() === 200,
      () => page.click('[data-real-action="save-epoch-set"]'),
      30000,
    );
    const persistedEpochSet = await epochSetResponse.json();
    evidence.persisted_epoch_set = {
      id: persistedEpochSet.id,
      revision: persistedEpochSet.revision,
      status: persistedEpochSet.status,
      schema_version: persistedEpochSet.schema_version,
      data_preparation_plan_id: persistedEpochSet.data_preparation_plan_id,
      data_preparation_revision: persistedEpochSet.data_preparation_revision,
      artifact_root: persistedEpochSet.artifact_root,
      lineage_json: persistedEpochSet.lineage_json,
      source: "visible UI save-epoch-set API response",
    };
    evidence.steps.push({ action: "click/wait", target: "save-epoch-set", status: "passed", epoch_set_id: persistedEpochSet.id, revision: persistedEpochSet.revision });

    const [epochDownload] = await Promise.all([
      page.waitForEvent("download", { timeout: 15000 }),
      page.click('[data-real-action="download-epoch-manifest"]'),
    ]);
    const epochDownloadPath = path.join(OUT_DIR, epochDownload.suggestedFilename() || "epoch_set_manifest.json");
    await epochDownload.saveAs(epochDownloadPath);
    const downloadedEpochManifest = JSON.parse(fs.readFileSync(epochDownloadPath, "utf8"));
    evidence.epoch_set_manifest = {
      schema_version: downloadedEpochManifest.schema_version,
      epoch_set_id: downloadedEpochManifest.epoch_set_id || downloadedEpochManifest.id,
      id: downloadedEpochManifest.id,
      revision: downloadedEpochManifest.revision,
      status: downloadedEpochManifest.status,
      event_id: downloadedEpochManifest.event_id,
      event_mapping: downloadedEpochManifest.event_mapping,
      event_count: downloadedEpochManifest.event_count,
      estimated_epoch_count: downloadedEpochManifest.estimated_epoch_count,
      tmin: downloadedEpochManifest.tmin,
      tmax: downloadedEpochManifest.tmax,
      baseline: downloadedEpochManifest.baseline,
      drop_log_preview: downloadedEpochManifest.drop_log_preview,
      boundary: downloadedEpochManifest.boundary,
      lineage_json: downloadedEpochManifest.lineage_json,
      artifact_root: downloadedEpochManifest.artifact_root,
      persisted: downloadedEpochManifest.persisted,
      source: "visible UI exported JSON",
    };
    evidence.p0_modules.event_epoch.epoch_set_id = downloadedEpochManifest.epoch_set_id || downloadedEpochManifest.id;
    evidence.p0_modules.event_epoch.epoch_set_revision = downloadedEpochManifest.revision;
    evidence.p0_modules.event_epoch.event_mapping = downloadedEpochManifest.event_mapping;
    evidence.p0_modules.event_epoch.estimated_epoch_count = downloadedEpochManifest.estimated_epoch_count;
    if (downloadedEpochManifest.schema_version === "qlanalyser-epoch-set-manifest-draft-v0.1") {
      evidence.product_gaps.push({
        module_id: "event_epoch",
        severity: "P1",
        gap: "Standalone event/epoch workbench now exposes mapping, epoch_set_id, drop-log preview, manifest preview, and JSON export, but the exported epoch_set is still a draft rather than durable persisted module state.",
        required_action: "Persist epoch_set records with revision/lineage and rerun UI trace plus artifact validator before stable promotion.",
      });
    }
    evidence.downloads.push({
      requirement: "epoch_set_manifest.json",
      via: "visible UI download-epoch-manifest button",
      path: epochDownloadPath,
      bytes: fs.statSync(epochDownloadPath).size,
    });
    evidence.steps.push({ action: "download", target: "download-epoch-manifest", status: "passed", path: epochDownloadPath });
    await screenshot(page, "p0-ui-06-prep-and-epoch-downloads", evidence);

    await clickWhenEnabled(page, 'button[data-view="workflow"]');
    evidence.steps.push({ action: "click", target: "data-view=workflow", status: "passed" });
    await page.waitForSelector('[data-testid="analysis-task-workbench"]', { timeout: 20000 }).catch(() => {});
    evidence.ui_capabilities_by_view.workflow = await discoverUiCapabilities(page);
    await screenshot(page, "p0-ui-06b-workflow-workbench-open", evidence);

    const psdTask = await waitForTask(page, "psd", "run PSD/bandpower", "run-psd");
    evidence.p0_modules.psd_bandpower.status = "ui_task_created";
    evidence.p0_modules.psd_bandpower.task_id = psdTask.id;
    evidence.p0_modules.psd_bandpower.ui_path = ["run-psd"];
    evidence.steps.push({ action: "click/wait", target: "run-psd", status: "passed", task_id: psdTask.id });
    await screenshot(page, "p0-ui-07-psd-bandpower", evidence);

    const erpTask = await waitForTask(page, "erp", "run ERP/P300", "run-erp");
    evidence.p0_modules.event_epoch.status = evidence.persisted_epoch_set?.id
      ? "persistent_epoch_set_created"
      : evidence.epoch_set_manifest?.epoch_set_id
        ? "standalone_epoch_manifest_exported"
      : "implicit_fixture_events_only";
    evidence.p0_modules.event_epoch.task_id = erpTask.id;
    evidence.p0_modules.event_epoch.ui_path = ["epoch-set-manager", "save-epoch-set", "download-epoch-manifest", "run-erp"];
    evidence.p0_modules.erp_p300.status = "ui_task_created";
    evidence.p0_modules.erp_p300.task_id = erpTask.id;
    evidence.p0_modules.erp_p300.ui_path = ["run-erp"];
    evidence.steps.push({ action: "click/wait", target: "run-erp", status: "passed", task_id: erpTask.id });
    await screenshot(page, "p0-ui-08-erp-p300", evidence);

    const reportResponse = await waitForUiResponse(
      page,
      "create report",
      (response) => response.url().includes(`${API_BASE}/reports`) && response.request().method() === "POST",
      () => page.click('button[data-real-action="create-report"]'),
      30000,
    );
    const report = await reportResponse.json();
    evidence.report_id = report.id;
    evidence.steps.push({ action: "click/wait", target: "create-report", status: "passed", report_id: report.id });
    await clickWhenEnabled(page, 'button[data-view="publication"]');
    evidence.steps.push({ action: "click", target: "data-view=publication", status: "passed" });
    await page.waitForSelector('a[data-report-download="package"]:visible', { timeout: 10000 });
    evidence.ui_capabilities_by_view.publication = await discoverUiCapabilities(page);
    await screenshot(page, "p0-ui-09-report-ready", evidence);

    const downloadButton = page.locator('a[data-report-download="package"]:visible').first();
    const uiDownloadPath = await downloadButton.getAttribute("data-report-download");
    const [download] = await Promise.all([
      page.waitForEvent("download", { timeout: 30000 }),
      downloadButton.click(),
    ]);
    const suggested = download.suggestedFilename() || `${report.id}.zip`;
    const packagePath = path.join(OUT_DIR, suggested);
    await download.saveAs(packagePath);
    const packageBody = fs.readFileSync(packagePath);
    evidence.downloads.push({
      requirement: "report bundle",
      via: "visible UI data-report-download button",
      ui_exposed_path: uiDownloadPath,
      suggested_filename: suggested,
      path: packagePath,
      bytes: packageBody.length,
      zip_header: zipHeader(packageBody),
      is_zip: zipHeader(packageBody) === "504b0304",
    });
    evidence.steps.push({ action: "download", target: "data-report-download", status: "passed", path: packagePath });

    evidence.artifact_inspect = inspectZip(packagePath);
    evidence.artifact_inspect.module_task_ids = {
      preprocessing_readiness: qcTask.id,
      event_epoch: erpTask.id,
      psd_bandpower: psdTask.id,
      erp_p300: erpTask.id,
    };

    const tracePath = path.join(OUT_DIR, "p0-ui-only-runner-trace.zip");
    await context.tracing.stop({ path: tracePath });
    evidence.trace = tracePath;
    evidence.verdict = evidence.product_gaps.length ? "revise" : "pass";
  } catch (error) {
    evidence.verdict = "error";
    evidence.error = error.message || String(error);
    try {
      await screenshot(page, "p0-ui-error", evidence);
    } catch {
      // Keep original failure.
    }
    try {
      const tracePath = path.join(OUT_DIR, "p0-ui-only-runner-trace.zip");
      await context.tracing.stop({ path: tracePath });
      evidence.trace = tracePath;
    } catch {
      // Tracing can already be stopped or unavailable after browser failures.
    }
  } finally {
    await browser.close().catch(() => {});
    fs.writeFileSync(EVIDENCE_PATH, `${JSON.stringify(evidence, null, 2)}\n`, "utf8");
  }

  console.log(JSON.stringify(evidence, null, 2));
  if (evidence.verdict === "error") process.exit(1);
}

run().catch((error) => {
  ensureDir(OUT_DIR);
  fs.writeFileSync(
    EVIDENCE_PATH,
    `${JSON.stringify({ protocol: "QLANALYSER_P0_UI_ONLY_RUNNER", verdict: "error", error: error.message || String(error) }, null, 2)}\n`,
    "utf8",
  );
  console.error(error);
  process.exit(1);
});
