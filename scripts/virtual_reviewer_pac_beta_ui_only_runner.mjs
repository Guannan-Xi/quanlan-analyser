import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const { chromium } = require("../frontend/node_modules/playwright");
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");
const FRONTEND_URL =
  process.env.QLANALYSER_FRONTEND_URL ||
  "http://127.0.0.1:4174/module-lab.html?api=http://127.0.0.1:8001/api&acceptance=pac-beta-ui-only";
const OUT_DIR = process.env.QLANALYSER_PAC_BETA_EVIDENCE_DIR || path.join(ROOT, "work", "release_evidence", "pac_beta");
const EVIDENCE_PATH = path.join(OUT_DIR, "pac-beta-ui-only-runner-evidence.json");
const FIXTURE_DIR = path.join(ROOT, "work", "fixtures", "pac_beta");
const SAMPLE_EDF = path.join(ROOT, "frontend", "assets", "teaching_oddball.edf");

const REQUIRED_SELECTORS = [
  '[data-testid="pac-beta-page"]',
  '[data-testid="pac-file-upload"]',
  '[data-testid="preparation-plan-select"]',
  '[data-testid="pac-analysis-scope"]',
  '[data-testid="pac-channel-select"]',
  '[data-testid="pac-phase-grid"]',
  '[data-testid="pac-phase-band-width"]',
  '[data-testid="pac-amp-grid"]',
  '[data-testid="pac-amp-band-width"]',
  '[data-testid="pac-run"]',
  '[data-testid="pac-comodulogram"]',
  '[data-testid="pac-phase-bins"]',
  '[data-testid="pac-dynamic-curve"]',
  '[data-testid="method-summary"]',
  '[data-testid="artifact-download-list"]',
];

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

async function screenshot(page, name, evidence) {
  const file = path.join(OUT_DIR, `${name}.png`);
  await page.screenshot({ path: file, fullPage: true, timeout: 15000 }).catch(async () => {
    await page.locator("body").screenshot({ path: file, timeout: 15000 });
  });
  evidence.screenshots.push({ name, path: file });
}

async function hasVisible(page, selector) {
  return page.locator(selector).first().isVisible({ timeout: 1500 }).catch(() => false);
}

function runValidator(artifact, outName) {
  const outPath = path.join(OUT_DIR, outName);
  const proc = spawnSync("python", ["scripts\\validate_pac_beta_artifacts.py", artifact, "--out", outPath], {
    cwd: ROOT,
    encoding: "utf8",
  });
  return {
    artifact,
    out_path: outPath,
    returncode: proc.status,
    stdout_tail: (proc.stdout || "").slice(-2000),
    stderr_tail: (proc.stderr || "").slice(-2000),
  };
}

async function run() {
  ensureDir(OUT_DIR);
  const evidence = {
    protocol: "QLANALYSER_PAC_BETA_UI_ONLY_RUNNER",
    implementation_packet_marker: "PAC_BETA_PACKET_READY",
    generated_at: new Date().toISOString(),
    frontend_url: FRONTEND_URL,
    module_id: "pac_cfc",
    lifecycle_state: "beta",
    ui_only_policy: {
      real_user_path: "PAC beta task must be created by visible UI clicks and file/select controls.",
      direct_api_task_mutation_allowed: false,
      api_allowed_only_for: ["network evidence caused by UI clicks", "artifact inspection of UI-exposed downloads"],
    },
    no_direct_api_mutation: true,
    direct_api_mutations: [],
    selectors: [],
    product_gaps: [],
    screenshots: [],
    downloads: [],
    artifact_validator: {},
    boundary: "PAC beta evidence only; no diagnosis, p-value, significance, group comparison, causality, brain-region communication, or source localization claim.",
  };

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ acceptDownloads: true, viewport: { width: 1440, height: 1000 } });
  await context.tracing.start({ screenshots: true, snapshots: true, sources: false });
  const page = await context.newPage();

  try {
    await page.goto(FRONTEND_URL, { waitUntil: "domcontentloaded" });
    await screenshot(page, "pac-beta-01-module-lab", evidence);
    for (const selector of REQUIRED_SELECTORS) {
      const visible = await hasVisible(page, selector);
      evidence.selectors.push({ selector, visible });
      if (!visible) {
        evidence.product_gaps.push({
          severity: "P1",
          selector,
          gap: "PAC beta UI-only runner required selector is not visible in the current product UI.",
          required_action: "Add a visible PAC beta page/control before claiming browser-executable PAC beta.",
        });
      }
    }

    if (fs.existsSync(SAMPLE_EDF)) {
      await page.setInputFiles("#labEegFile", SAMPLE_EDF);
      await page.locator("#labUploadButton").click();
      await page.locator("#labDataSourceStatus").waitFor({ state: "visible", timeout: 15000 }).catch(() => {});
    }

    const pacRunButton = page.locator('[data-testid="pac-run"]').first();
    if (await pacRunButton.isVisible({ timeout: 2000 }).catch(() => false)) {
      await pacRunButton.click();
      const artifactList = page.locator('[data-testid="artifact-download-list"] .artifact').first();
      await artifactList.waitFor({ state: "visible", timeout: 60000 });
      await screenshot(page, "pac-beta-03-pac-result", evidence);
      const download = await Promise.all([
        page.waitForEvent("download", { timeout: 30000 }),
        artifactList.click(),
      ]).then(([item]) => item);
      const downloadPath = path.join(OUT_DIR, download.suggestedFilename() || "pac_beta_artifact_bundle.zip");
      await download.saveAs(downloadPath);
      evidence.downloads.push({
        requirement: "PAC beta artifact bundle",
        path: downloadPath,
        via: "ui-exposed PAC result download link after customer upload",
        bytes: fs.statSync(downloadPath).size,
      });
      evidence.artifact_validator.positive_known_pac = runValidator(downloadPath, "pac-beta-ui-runner-artifact-validator.json");
    }

    const staticPacUrl = "http://127.0.0.1:4174/research-module/pac.html";
    await page.goto(staticPacUrl, { waitUntil: "domcontentloaded" }).catch(() => null);
    await screenshot(page, "pac-beta-02-static-research-page-if-present", evidence);
    evidence.static_research_page_checked = staticPacUrl;

    const tracePath = path.join(OUT_DIR, "pac-beta-ui-only-runner-trace.zip");
    await context.tracing.stop({ path: tracePath });
    evidence.trace = tracePath;
    evidence.verdict = evidence.product_gaps.length ? "revise" : "pass";
  } catch (error) {
    evidence.verdict = "error";
    evidence.error = error.message || String(error);
    try {
      await screenshot(page, "pac-beta-error", evidence);
    } catch {}
    try {
      const tracePath = path.join(OUT_DIR, "pac-beta-ui-only-runner-trace.zip");
      await context.tracing.stop({ path: tracePath });
      evidence.trace = tracePath;
    } catch {}
  } finally {
    await browser.close().catch(() => {});
    fs.writeFileSync(EVIDENCE_PATH, `${JSON.stringify(evidence, null, 2)}\n`, "utf8");
  }

  console.log(JSON.stringify(evidence, null, 2));
  if (evidence.verdict === "error") process.exit(1);
}

run().catch((error) => {
  ensureDir(OUT_DIR);
  fs.writeFileSync(EVIDENCE_PATH, `${JSON.stringify({ protocol: "QLANALYSER_PAC_BETA_UI_ONLY_RUNNER", verdict: "error", error: error.message || String(error) }, null, 2)}\n`, "utf8");
  console.error(error);
  process.exit(1);
});
