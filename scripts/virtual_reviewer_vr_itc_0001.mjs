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
const FRONTEND_URL = process.env.QLANALYSER_FRONTEND_URL || `http://127.0.0.1:4174/?customer_demo=auto&api=${encodeURIComponent(API_BASE)}`;
const FIXTURE = process.env.QLANALYSER_UI_SAMPLE || path.join(ROOT, "work", "acceptance", "ui_with_events_raw.fif");
const OUT_DIR = process.env.QLANALYSER_VR_EVIDENCE_DIR || path.join(ROOT, "work", "release_evidence", "20260621-virtual-reviewer-executable");

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function sha256File(filePath) {
  const hash = crypto.createHash("sha256");
  hash.update(fs.readFileSync(filePath));
  return hash.digest("hex");
}

async function screenshot(page, name, evidence) {
  const file = path.join(OUT_DIR, `${name}.png`);
  await page.screenshot({ path: file, fullPage: true });
  evidence.screenshots.push(file);
  return file;
}

async function waitForApi(page, label, predicate, action, timeout = 30000) {
  const responsePromise = page.waitForResponse(predicate, { timeout });
  await action();
  const response = await responsePromise;
  if (!response.ok()) {
    throw new Error(`${label} failed: ${response.status()} ${response.statusText()}`);
  }
  return response;
}

async function apiJson(pathname, options = {}) {
  const response = await fetch(`${API_BASE}${pathname}`, options);
  if (!response.ok) throw new Error(`${pathname} failed: ${response.status} ${await response.text()}`);
  return response.json();
}

function inspectZipBytes(buffer) {
  return {
    bytes: buffer.length,
    zip_header: buffer.subarray(0, 4).toString("hex"),
    is_zip: buffer.subarray(0, 4).toString("hex") === "504b0304",
  };
}

async function run() {
  ensureDir(OUT_DIR);
  const evidence = {
    protocol: "QLANALYSER_EXECUTABLE_VIRTUAL_REVIEWER_READY",
    task_id: "VR-ITC-0001",
    fixture_requirement: "VR-FX-0001",
    expected_output_requirement: "VR-EO-0001",
    generated_at: new Date().toISOString(),
    frontend_url: FRONTEND_URL,
    api_base: API_BASE,
    fixture: {
      path: FIXTURE,
      exists: fs.existsSync(FIXTURE),
      size_bytes: fs.existsSync(FIXTURE) ? fs.statSync(FIXTURE).size : null,
      sha256: fs.existsSync(FIXTURE) ? sha256File(FIXTURE) : null,
      privacy_boundary: "synthetic software-test FIF; no real participant data",
    },
    runner_plan_coverage: ["click", "upload", "wait", "screenshot", "download", "artifact_inspect"],
    screenshots: [],
    steps: [],
    downloads: [],
    artifact_inspect: {},
    gaps: [],
  };

  if (!evidence.fixture.exists) throw new Error(`Fixture missing: ${FIXTURE}`);

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ acceptDownloads: true, viewport: { width: 1440, height: 1000 } });
  await context.tracing.start({ screenshots: true, snapshots: true, sources: false });
  const page = await context.newPage();

  try {
    await page.goto(FRONTEND_URL, { waitUntil: "domcontentloaded" });
    await page.waitForSelector("#appShell:not([hidden])", { timeout: 20000 });
    await screenshot(page, "vr-itc-0001-01-dashboard", evidence);
    evidence.steps.push({ action: "click", target: "New Project", status: "ready" });

    const projectResponse = await waitForApi(
      page,
      "create project",
      (response) => response.url().includes(`${API_BASE}/projects`) && response.request().method() === "POST",
      () => page.click('button[data-real-action="create-project"]'),
    );
    const project = await projectResponse.json();
    evidence.project_id = project.id;
    evidence.steps.push({ action: "click", target: "New Project", status: "passed", project_id: project.id });
    await screenshot(page, "vr-itc-0001-02-project-created", evidence);

    await page.setInputFiles("#real-eeg-file", FIXTURE);
    const uploadResponse = await waitForApi(
      page,
      "upload fixture",
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
    evidence.steps.push({ action: "upload", target: "EEG fixture", status: "passed", file_id: uploaded.id });
    await screenshot(page, "vr-itc-0001-03-metadata-preview", evidence);

    const qcTask = await waitForTask(page, "qc", "Run QC", "run-qc");
    evidence.steps.push({ action: "click/wait", target: "Run QC", status: "passed", task_id: qcTask.id });
    await screenshot(page, "vr-itc-0001-04-qc-summary", evidence);

    const psdTask = await waitForTask(page, "psd", "View PSD", "run-psd");
    evidence.steps.push({ action: "click/wait", target: "View PSD/topomap", status: "passed", task_id: psdTask.id });
    await screenshot(page, "vr-itc-0001-05-psd-result", evidence);

    const reportResponse = await waitForApi(
      page,
      "export report",
      (response) => response.url().includes(`${API_BASE}/reports`) && response.request().method() === "POST",
      () => page.click('button[data-real-action="create-report"]'),
      30000,
    );
    const report = await reportResponse.json();
    evidence.report_id = report.id;
    await page.waitForTimeout(1500);
    await screenshot(page, "vr-itc-0001-06-export-success", evidence);

    const packageUrl = `${API_BASE}/reports/${report.id}/package`;
    const packageResponse = await page.request.get(packageUrl);
    const packageBody = await packageResponse.body();
    const packagePath = path.join(OUT_DIR, `${report.id}.zip`);
    fs.writeFileSync(packagePath, packageBody);
    evidence.downloads.push({ requirement: "report bundle", url: packageUrl, path: packagePath, status: packageResponse.status(), ...inspectZipBytes(packageBody) });

    evidence.artifact_inspect = await inspectArtifacts(project.id, psdTask.id, report.id, packagePath);
    if (!evidence.artifact_inspect.report_pdf_present) evidence.gaps.push("report.pdf not present in report ZIP");
    if (!evidence.artifact_inspect.report_json_present) evidence.gaps.push("report.json not present by filename; result.json and reports/report_manifest.json present");
    evidence.verdict = evidence.gaps.length ? "revise" : "pass";
  } catch (error) {
    evidence.verdict = "error";
    evidence.error = error.message || String(error);
    throw error;
  } finally {
    const tracePath = path.join(OUT_DIR, "vr-itc-0001-trace.zip");
    await context.tracing.stop({ path: tracePath });
    evidence.trace = tracePath;
    await browser.close();
    const evidencePath = path.join(OUT_DIR, "vr-itc-0001-runner-evidence.json");
    fs.writeFileSync(evidencePath, `${JSON.stringify(evidence, null, 2)}\n`, "utf8");
  }

  console.log(JSON.stringify(evidence, null, 2));
}

async function waitForTask(page, moduleName, label, actionName) {
  const response = await waitForApi(
    page,
    label,
    async (resp) => {
      if (!resp.url().includes(`${API_BASE}/tasks`) || resp.request().method() !== "POST" || resp.status() !== 200) return false;
      try {
        const body = await resp.json();
        return body.module_name === moduleName;
      } catch {
        return false;
      }
    },
    () => page.click(`button[data-real-action="${actionName}"]`),
    45000,
  );
  return response.json();
}

async function inspectArtifacts(projectId, taskId, reportId, packagePath) {
  const result = {
    project_id: projectId,
    task_id: taskId,
    report_id: reportId,
    package_path: packagePath,
    report_pdf_present: false,
    report_json_present: false,
    metrics_csv_present: false,
    pdf_checks: {},
    json_checks: {},
    csv_checks: {},
    boundary_checks: {},
  };
  const artifacts = await apiJson(`/tasks/${taskId}/artifacts`);
  result.artifact_count = artifacts.length;
  result.artifact_labels = artifacts.map((item) => item.label);

  const derivativeRoot = path.join(ROOT, "data", "derivatives", projectId, taskId);
  const resultJsonPath = path.join(derivativeRoot, "result.json");
  const manifestJsonPath = path.join(derivativeRoot, "manifest.json");
  const tableDictionaryPath = path.join(derivativeRoot, "reproducibility", "table_dictionary.json");
  const scopeContractPath = path.join(derivativeRoot, "reproducibility", "scope_contract.json");
  const bandPowerPath = path.join(derivativeRoot, "tables", "band_power.csv");
  const channelBandPath = path.join(derivativeRoot, "tables", "channel_band_power.csv");
  const zipInspect = inspectZipEntries(packagePath);
  Object.assign(result, zipInspect);
  for (const filePath of [resultJsonPath, manifestJsonPath, tableDictionaryPath, scopeContractPath]) {
    result.json_checks[path.basename(filePath)] = fs.existsSync(filePath);
  }
  if (fs.existsSync(resultJsonPath)) {
    const payload = JSON.parse(fs.readFileSync(resultJsonPath, "utf8"));
    result.json_checks.schema_version = Boolean(payload.schema_version);
    result.json_checks.parameters = Boolean(payload.parameters);
    result.json_checks.parameters_hash = Boolean(payload.parameters_hash);
    result.json_checks.software_or_workflow_reference = Boolean(payload.references?.software_versions && payload.references?.workflow);
    result.json_checks.timestamp = Boolean(payload.generated_at || payload.finished_at);
    result.json_checks.warnings_field = Array.isArray(payload.warnings);
  }
  if (fs.existsSync(tableDictionaryPath)) {
    const tableDictionary = JSON.parse(fs.readFileSync(tableDictionaryPath, "utf8"));
    result.csv_checks.table_dictionary_present = true;
    result.csv_checks.units_present = JSON.stringify(tableDictionary).includes('"unit"');
  }
  result.csv_checks.band_power_csv = fs.existsSync(bandPowerPath);
  result.csv_checks.channel_band_power_csv = fs.existsSync(channelBandPath);
  result.metrics_csv_present = fs.existsSync(bandPowerPath) || fs.existsSync(channelBandPath);
  if (fs.existsSync(scopeContractPath)) {
    const scope = JSON.parse(fs.readFileSync(scopeContractPath, "utf8"));
    result.boundary_checks.non_diagnostic_boundary = JSON.stringify(scope).includes("diagnosis_or_treatment_recommendation");
    result.boundary_checks.psd_sensor_space_boundary = scope.analysis_scope === "single_record_descriptive_sensor_space_psd";
    result.boundary_checks.no_source_claim = JSON.stringify(scope.disallowed_claims || []).includes("source_localization_or_brain_region_activation");
  }
  return result;
}

function inspectZipEntries(packagePath) {
  const script = [
    "import json, sys, zipfile",
    "from pathlib import Path",
    "package=Path(sys.argv[1])",
    "out={'report_pdf_present': False, 'report_json_present': False, 'metrics_csv_present': False, 'pdf_checks': {}}",
    "with zipfile.ZipFile(package) as zf:",
    "    names=set(zf.namelist())",
    "    out['zip_entries']=sorted(names)",
    "    out['report_pdf_present']='reports/report.pdf' in names",
    "    out['report_json_present']='reports/report.json' in names",
    "    out['metrics_csv_present']='tables/metrics.csv' in names",
    "    if out['report_pdf_present']:",
    "        data=zf.read('reports/report.pdf')",
    "        out['pdf_checks']['pdf_header']=data.startswith(b'%PDF')",
    "        out['pdf_checks']['size_bytes']=len(data)",
    "        try:",
    "            import fitz",
    "            doc=fitz.open(stream=data, filetype='pdf')",
    "            text='\\n'.join(page.get_text() for page in doc)",
    "            out['pdf_checks']['text_extractable']=bool(text.strip())",
    "            out['pdf_checks']['method_summary']=('Method summary' in text or 'Effective parameters' in text)",
    "            out['pdf_checks']['non_diagnostic_boundary']='not for clinical diagnosis' in text.lower()",
    "            out['pdf_checks']['sensor_space_boundary']='sensor/channel-space' in text.lower()",
    "        except Exception as exc:",
    "            out['pdf_checks']['text_extract_error']=str(exc)",
    "print(json.dumps(out))",
  ].join("\n");
  const proc = spawnSync("python", ["-c", script, packagePath], { encoding: "utf8" });
  if (proc.status !== 0) {
    return { zip_inspect_error: proc.stderr || proc.stdout || `python exited ${proc.status}` };
  }
  return JSON.parse(proc.stdout);
}

run().catch((error) => {
  console.error(error);
  process.exit(1);
});
