import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { chromium } = require("../frontend/node_modules/playwright");

const FRONTEND_URL = process.env.QLANALYSER_FRONTEND_URL
  || "http://127.0.0.1:4174/module-lab.html?api=http://127.0.0.1:8001/api&acceptance=visible-fields";
const EVIDENCE_DIR = path.resolve("work/release_evidence/07-mainline-integration");
const EVIDENCE_PATH = process.env.QLANALYSER_VISIBLE_FIELDS_EVIDENCE
  || path.join(EVIDENCE_DIR, "module_lab_visible_fields.json");
const SCREENSHOT_PATH = process.env.QLANALYSER_VISIBLE_FIELDS_SCREENSHOT
  || path.join(EVIDENCE_DIR, "module_lab_visible_fields.png");

const EXPECTED_GROUPS = [
  "data-readiness",
  "stationary-spectral-power",
  "event-locked-time-domain",
  "event-screening-research",
  "event-locked-time-frequency",
  "multitaper-spectral-power",
  "multitaper-time-frequency",
  "csd-spatial-filter",
  "cross-frequency-coupling",
  "sensor-connectivity",
];

const REQUIRED_FIELDS = {
  band_power: ["fmin", "fmax", "bad_channels"],
  tfr: ["picks", "average"],
  multitaper_psd: ["picks"],
  multitaper_tfr: ["picks"],
  erp: ["bad_channels"],
  epilepsy_std: ["std_factor", "min_event_epochs", "bad_channels"],
  reference_csd: ["bipolar_pairs"],
  pac: ["n_surrogates"],
  connectivity: ["reference"],
};

const BACKEND_CONTRACTS = {
  qc: { workflow: "metadata_qc", backendModule: null },
  psd: { workflow: "resting_psd", backendModule: null },
  band_power: { workflow: "resting_psd", backendModule: "psd" },
  erp: { workflow: "erp_p300", backendModule: null },
  epilepsy_std: { workflow: "epilepsy_std_threshold", backendModule: "epilepsy" },
  tfr: { workflow: "tfr_ersp_itc", backendModule: null },
  multitaper_psd: { workflow: "multitaper_psd_tfr", backendModule: "multitaper_psd_tfr" },
  multitaper_tfr: { workflow: "multitaper_psd_tfr", backendModule: "multitaper_psd_tfr" },
  reference_csd: { workflow: "reference_csd", backendModule: null },
  pac: { workflow: "pac_cfc", backendModule: null },
  connectivity: { workflow: "connectivity", backendModule: null },
};

const evidence = {
  status: "running",
  frontendUrl: FRONTEND_URL,
  startedAt: new Date().toISOString(),
  groups: {},
  modules: {},
  checks: {},
  errors: [],
};

function writeEvidence() {
  fs.mkdirSync(EVIDENCE_DIR, { recursive: true });
  fs.writeFileSync(EVIDENCE_PATH, `${JSON.stringify(evidence, null, 2)}\n`, "utf8");
}

function localBrowserExecutable() {
  const candidates = [
    process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE,
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  ].filter(Boolean);
  return candidates.find((item) => fs.existsSync(item)) || "";
}

async function inputState(locator) {
  const count = await locator.count();
  if (count !== 1) return { count, visible: false, enabled: false, editable: false };
  const handle = locator.first();
  const visible = await handle.isVisible();
  const enabled = await handle.isEnabled();
  const editable = await handle.evaluate((node) => {
    const tag = node.tagName.toLowerCase();
    if (node.disabled) return false;
    if (tag === "select") return true;
    if (tag === "input" || tag === "textarea") return !node.readOnly;
    return false;
  });
  return { count, visible, enabled, editable };
}

async function main() {
  const executablePath = localBrowserExecutable();
  const browser = await chromium.launch(executablePath ? { executablePath } : {});
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });

  page.on("pageerror", (error) => evidence.errors.push(error.message));
  page.on("console", (msg) => {
    if (msg.type() === "error" && !msg.text().includes("Failed to load resource")) {
      evidence.errors.push(msg.text());
    }
  });

  try {
    await page.goto(FRONTEND_URL, { waitUntil: "networkidle", timeout: 60000 });
    await page.waitForSelector("[data-method-group]", { timeout: 20000 });

    const groupIds = await page.locator("[data-method-group]").evaluateAll((items) =>
      items.map((item) => item.getAttribute("data-method-group")),
    );
    const missingGroups = EXPECTED_GROUPS.filter((id) => !groupIds.includes(id));
    evidence.groups = {
      count: groupIds.length,
      expectedCount: EXPECTED_GROUPS.length,
      ids: groupIds,
      missingGroups,
    };

    const pickerCount = await page.locator("[data-method-picker]").count();
    evidence.checks.pickerCount = pickerCount;
    evidence.checks.noMethodPicker = pickerCount === 0;

    for (const [moduleId, fields] of Object.entries(REQUIRED_FIELDS)) {
      const switchButton = page.locator(`[data-target-method="${moduleId}"]`);
      if (await switchButton.count()) {
        await switchButton.first().click();
      }
      const form = page.locator(`[data-runner-form="${moduleId}"]`);
      const moduleEvidence = {
        formCount: await form.count(),
        formVisible: await form.first().isVisible().catch(() => false),
        requiredFields: {},
        contract: BACKEND_CONTRACTS[moduleId],
      };
      for (const fieldName of fields) {
        moduleEvidence.requiredFields[fieldName] = await inputState(
          form.locator(`[name="${fieldName}"]`),
        );
      }
      moduleEvidence.passed = moduleEvidence.formCount === 1
        && moduleEvidence.formVisible
        && Object.values(moduleEvidence.requiredFields).every((field) =>
          field.count === 1 && field.visible && field.enabled && field.editable,
        );
      evidence.modules[moduleId] = moduleEvidence;
    }

    const legacyFormId = ["multitaper", "psd", "tfr"].join("_");
    const legacyFormCount = await page.locator(`[data-runner-form="${legacyFormId}"]`).count();
    evidence.checks.legacyMultitaperFormIdCount = legacyFormCount;
    evidence.checks.legacyMultitaperFormIdCleared = legacyFormCount === 0;

    await page.screenshot({ path: SCREENSHOT_PATH, fullPage: true });

    const modulesPassed = Object.values(evidence.modules).every((item) => item.passed);
    evidence.status = evidence.groups.missingGroups.length === 0
      && evidence.groups.count === EXPECTED_GROUPS.length
      && evidence.checks.noMethodPicker
      && evidence.checks.legacyMultitaperFormIdCleared
      && modulesPassed
      && evidence.errors.length === 0
      ? "passed"
      : "failed";
  } catch (error) {
    evidence.status = "failed";
    evidence.errors.push(error.message || String(error));
    try {
      await page.screenshot({ path: SCREENSHOT_PATH, fullPage: true });
    } catch (_) {}
  } finally {
    evidence.finishedAt = new Date().toISOString();
    await browser.close();
    writeEvidence();
  }

  console.log(JSON.stringify(evidence, null, 2));
  if (evidence.status !== "passed") process.exit(1);
}

writeEvidence();
main();
