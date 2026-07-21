import fs from "node:fs";
import path from "node:path";
import { chromium, chromiumLaunchOptions, classifyAcceptanceFailure } from "./lib/playwright_runtime.mjs";

const DEFAULT_API_URL = "http://127.0.0.1:8001/api";
const DEFAULT_FRONTEND_URL = "http://127.0.0.1:4174/module-lab.html";
const EVIDENCE_DIR = path.resolve("work/release_evidence/module_lab_input_source_gate");
const EVIDENCE_PATH = path.join(EVIDENCE_DIR, "module_lab_input_source_gate.json");
const SCREENSHOT_PATH = path.join(EVIDENCE_DIR, "module_lab_input_source_gate_initial.png");

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
  const rawFrontendUrl = argValue("frontend-url") || process.env.QLANALYSER_FRONTEND_URL || DEFAULT_FRONTEND_URL;
  const frontend = new URL(rawFrontendUrl);
  const apiUrl = trimTrailingSlash(argValue("api-url") || process.env.QLANALYSER_API_URL || frontend.searchParams.get("api") || DEFAULT_API_URL);
  frontend.searchParams.set("api", apiUrl);
  frontend.searchParams.set("acceptance", "input-source-gate");
  return { frontendUrl: frontend.toString(), apiUrl };
}

async function probe(url, expectModuleLab = false) {
  try {
    const response = await fetch(url);
    const text = expectModuleLab ? await response.text() : "";
    return {
      ok: response.ok && (!expectModuleLab || (text.includes("module-lab.js") && text.includes("moduleLab"))),
      status: response.status,
    };
  } catch (error) {
    return { ok: false, error: error.message || String(error) };
  }
}

async function main() {
  const { frontendUrl, apiUrl } = configuredTarget();
  const evidence = {
    status: "running",
    frontendUrl,
    apiUrl,
    serviceHealth: [],
    requests: [],
    checks: {},
    errors: [],
    blockers: [],
  };
  fs.mkdirSync(EVIDENCE_DIR, { recursive: true });

  const backendHealth = await probe(`${apiUrl}/health`);
  const frontendHealth = await probe(frontendUrl, true);
  evidence.serviceHealth.push({ kind: "backend", ...backendHealth });
  evidence.serviceHealth.push({ kind: "frontend", ...frontendHealth });
  if (!backendHealth.ok || !frontendHealth.ok) {
    evidence.status = "blocked";
    evidence.blockers.push("service_unreachable");
    fs.writeFileSync(EVIDENCE_PATH, `${JSON.stringify(evidence, null, 2)}\n`, "utf8");
    console.log(JSON.stringify(evidence, null, 2));
    process.exit(1);
  }

  let browser;
  try {
    browser = await chromium.launch(chromiumLaunchOptions({ headless: true }));
    const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });
    page.on("request", (request) => {
      const url = request.url();
      if (url.includes("/api/tasks") || url.includes("/api/lab/demo/run") || url.includes("/api/eeg/upload")) {
        evidence.requests.push({ method: request.method(), url });
      }
    });
    page.on("pageerror", (error) => evidence.errors.push(error.message || String(error)));

    await page.goto(frontendUrl, { waitUntil: "domcontentloaded", timeout: 60000 });
    await page.waitForSelector("[data-runner-form]", { timeout: 30000 });
    await page.waitForTimeout(1500);
    await page.screenshot({ path: SCREENSHOT_PATH, fullPage: true });

    const initial = await page.evaluate(() => {
      const forms = [...document.querySelectorAll("[data-runner-form]")];
      const selects = forms.map((form) => form.querySelector("[data-file-select]"));
      const buttons = forms.map((form) => form.querySelector("button[type='submit']"));
      return {
        formCount: forms.length,
        selectValues: selects.map((select) => select?.value || ""),
        buttonDisabled: buttons.map((button) => Boolean(button?.disabled)),
        demoOptionCount: selects.filter((select) => [...(select?.options || [])].some((option) => option.value === "__demo__")).length,
        statusText: document.querySelector("#labDataSourceStatus")?.textContent || "",
      };
    });
    evidence.checks.initial = initial;
    evidence.checks.allSelectsEmpty = initial.formCount > 0 && initial.selectValues.every((value) => value === "");
    evidence.checks.allRunButtonsDisabled = initial.formCount > 0 && initial.buttonDisabled.every(Boolean);
    evidence.checks.noDemoOptionByDefault = initial.demoOptionCount === 0;

    const firstButton = page.locator("[data-runner-form] button[type='submit']").first();
    await firstButton.click({ force: true }).catch((error) => {
      evidence.checks.disabledClickError = error.message || String(error);
    });
    await page.waitForTimeout(1500);
    evidence.checks.noRunRequestBeforeExplicitSource = evidence.requests.length === 0;

    await page.locator("#labDemoModeButton").click();
    await page.waitForTimeout(500);
    const afterDemoMode = await page.evaluate(() => {
      const forms = [...document.querySelectorAll("[data-runner-form]")];
      return {
        selectValues: forms.map((form) => form.querySelector("[data-file-select]")?.value || ""),
        buttonDisabled: forms.map((form) => Boolean(form.querySelector("button[type='submit']")?.disabled)),
        statusText: document.querySelector("#labDataSourceStatus")?.textContent || "",
      };
    });
    evidence.checks.afterDemoMode = afterDemoMode;
    evidence.checks.demoModeSelectsEnabled = afterDemoMode.selectValues.every((value) => value === "__demo__")
      && afterDemoMode.buttonDisabled.every((disabled) => disabled === false);

    if (!evidence.checks.allSelectsEmpty) evidence.blockers.push("initial_select_not_empty");
    if (!evidence.checks.allRunButtonsDisabled) evidence.blockers.push("initial_run_button_not_disabled");
    if (!evidence.checks.noDemoOptionByDefault) evidence.blockers.push("demo_option_visible_by_default");
    if (!evidence.checks.noRunRequestBeforeExplicitSource) evidence.blockers.push("run_request_before_explicit_source");
    if (!evidence.checks.demoModeSelectsEnabled) evidence.blockers.push("explicit_demo_mode_not_enabled");
    if (evidence.errors.length) evidence.blockers.push("browser_error");
    evidence.status = evidence.blockers.length ? "failed" : "passed";
  } catch (error) {
    evidence.status = classifyAcceptanceFailure(error, evidence) === "service_unreachable" ? "blocked" : "failed";
    evidence.errors.push(error.message || String(error));
    evidence.blockers.push(evidence.status === "blocked" ? "service_unreachable" : "input_source_gate_failed");
  } finally {
    if (browser) await browser.close().catch(() => {});
  }

  evidence.screenshot = SCREENSHOT_PATH;
  fs.writeFileSync(EVIDENCE_PATH, `${JSON.stringify(evidence, null, 2)}\n`, "utf8");
  console.log(JSON.stringify(evidence, null, 2));
  if (evidence.status !== "passed") process.exit(1);
}

main();
