import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";

const ROOT = process.cwd();
const OUT_DIR = path.resolve(ROOT, "work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-cloud-acceptance-run");
const OUT_FILE = path.join(OUT_DIR, "acceptance_run.json");
const CLOUD_E2E_DIR = "work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-cloud-upload-to-export";

function isLocalUrl(rawUrl = "") {
  try {
    const url = new URL(rawUrl);
    return ["127.0.0.1", "localhost", "::1"].includes(url.hostname);
  } catch {
    return true;
  }
}

function writeResult(result) {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  fs.writeFileSync(OUT_FILE, `${JSON.stringify(result, null, 2)}\n`, "utf8");
  console.log(JSON.stringify(result, null, 2));
}

function runStep(name, args, env) {
  const startedAt = new Date().toISOString();
  const child = spawnSync(process.execPath, args, {
    cwd: ROOT,
    env,
    encoding: "utf8",
    maxBuffer: 1024 * 1024 * 20,
  });
  return {
    name,
    command: `node ${args.join(" ")}`,
    started_at: startedAt,
    finished_at: new Date().toISOString(),
    exit_code: child.status,
    signal: child.signal,
    stdout_tail: String(child.stdout || "").slice(-6000),
    stderr_tail: String(child.stderr || "").slice(-6000),
    passed: child.status === 0,
  };
}

const cloudFrontendUrl = process.env.QLANALYSER_CLOUD_FRONTEND_URL || process.env.QLANALYSER_FRONTEND_URL || "";
const cloudApiBaseUrl = process.env.QLANALYSER_CLOUD_API_BASE_URL || process.env.QLANALYSER_API_BASE_URL || "";

const result = {
  script: "run_epilepsy_cloud_trial_acceptance.mjs",
  generated_at: new Date().toISOString(),
  status: "running",
  cloud_target: {
    frontend_url: cloudFrontendUrl || null,
    api_base_url: cloudApiBaseUrl || null,
    frontend_is_non_local: Boolean(cloudFrontendUrl && !isLocalUrl(cloudFrontendUrl)),
    api_is_non_local: Boolean(cloudApiBaseUrl && !isLocalUrl(cloudApiBaseUrl)),
  },
  evidence_paths: {
    cloud_target_preflight: "work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-cloud-target-preflight/preflight_result.json",
    cloud_browser_e2e: `${CLOUD_E2E_DIR}/browser_upload_to_export.json`,
    release_gate: "work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-release-gate/release_gate_result.json",
    readiness_packet: "work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-readiness/readiness_packet.json",
  },
  steps: [],
  blockers: [],
};

if (!cloudFrontendUrl || !cloudApiBaseUrl || isLocalUrl(cloudFrontendUrl) || isLocalUrl(cloudApiBaseUrl)) {
  result.status = "blocked_cloud_target_missing";
  result.blockers.push("Set non-local QLANALYSER_CLOUD_FRONTEND_URL and QLANALYSER_CLOUD_API_BASE_URL.");
  result.next_command = "QLANALYSER_CLOUD_FRONTEND_URL=<cloud_or_staging_frontend_url> QLANALYSER_CLOUD_API_BASE_URL=<cloud_or_staging_api_url> node scripts/run_epilepsy_cloud_trial_acceptance.mjs";
  writeResult(result);
  process.exit(1);
}

const env = {
  ...process.env,
  QLANALYSER_FRONTEND_URL: cloudFrontendUrl,
  QLANALYSER_API_BASE_URL: cloudApiBaseUrl,
  QLANALYSER_EPILEPSY_UPLOAD_E2E_DIR: CLOUD_E2E_DIR,
};

result.steps.push(runStep("cloud_target_preflight", ["scripts/preflight_epilepsy_cloud_trial_target.mjs"], {
  ...env,
  QLANALYSER_REQUIRE_CLOUD_TARGET: "1",
}));

if (result.steps.at(-1)?.passed) {
  result.steps.push(runStep("cloud_browser_upload_to_export_e2e", ["scripts/e2e_epilepsy_cloud_trial_upload_to_export_browser.mjs"], env));
}

if (result.steps.at(-1)?.passed) {
  result.steps.push(runStep("strict_cloud_release_gate", ["scripts/validate_epilepsy_cloud_trial_v0_1_release_gate.mjs"], {
    ...env,
    QLANALYSER_REQUIRE_CLOUD: "1",
  }));
}

result.steps.push(runStep("readiness_packet", ["scripts/build_epilepsy_cloud_trial_readiness_packet.mjs"], env));

const failedSteps = result.steps.filter((step) => !step.passed).map((step) => step.name);
result.status = failedSteps.length ? "failed" : "passed";
result.blockers = failedSteps;
result.finished_at = new Date().toISOString();
writeResult(result);
if (result.status !== "passed") process.exit(1);
