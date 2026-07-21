import fs from "node:fs";
import path from "node:path";

const ROOT = process.cwd();
const OUT_DIR = path.resolve(ROOT, "work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-cloud-target-preflight");
const OUT_FILE = path.join(OUT_DIR, "preflight_result.json");
const SAMPLE_EDF = process.env.QLANALYSER_EPILEPSY_SAMPLE_EDF
  || path.resolve(ROOT, "work/fixtures/epilepsy_regular_labeled/regular_epilepsy_labeled_60s.edf");

function isLocalUrl(rawUrl = "") {
  try {
    const url = new URL(rawUrl);
    return ["127.0.0.1", "localhost", "::1"].includes(url.hostname);
  } catch {
    return true;
  }
}

async function probeUrl(label, rawUrl, options = {}) {
  const startedAt = Date.now();
  try {
    const response = await fetch(rawUrl, {
      method: "GET",
      redirect: "follow",
      signal: AbortSignal.timeout(options.timeoutMs || 15000),
      headers: options.headers || {},
    });
    const text = await response.text().catch(() => "");
    return {
      label,
      url: rawUrl,
      ok: response.ok,
      status: response.status,
      elapsed_ms: Date.now() - startedAt,
      content_type: response.headers.get("content-type") || "",
      body_preview: text.replace(/\s+/g, " ").slice(0, 240),
    };
  } catch (error) {
    return {
      label,
      url: rawUrl,
      ok: false,
      status: null,
      elapsed_ms: Date.now() - startedAt,
      error: error?.message || String(error),
    };
  }
}

const cloudFrontendUrl = process.env.QLANALYSER_CLOUD_FRONTEND_URL || process.env.QLANALYSER_FRONTEND_URL || "";
const cloudApiBaseUrl = process.env.QLANALYSER_CLOUD_API_BASE_URL || process.env.QLANALYSER_API_BASE_URL || "";
const apiHealthUrl = cloudApiBaseUrl ? `${cloudApiBaseUrl.replace(/\/$/, "")}/health` : "";

const checks = {
  frontend_url_present: Boolean(cloudFrontendUrl),
  api_base_url_present: Boolean(cloudApiBaseUrl),
  frontend_url_non_local: Boolean(cloudFrontendUrl && !isLocalUrl(cloudFrontendUrl)),
  api_base_url_non_local: Boolean(cloudApiBaseUrl && !isLocalUrl(cloudApiBaseUrl)),
  sample_edf_exists: fs.existsSync(SAMPLE_EDF),
};

const probes = [];
if (checks.frontend_url_present) {
  probes.push(await probeUrl("frontend", cloudFrontendUrl));
}
if (checks.api_base_url_present) {
  probes.push(await probeUrl("api_health", apiHealthUrl, { headers: { Accept: "application/json,*/*" } }));
}

const frontendProbe = probes.find((item) => item.label === "frontend");
const apiProbe = probes.find((item) => item.label === "api_health");
checks.frontend_reachable = Boolean(frontendProbe?.ok);
checks.api_health_reachable = Boolean(apiProbe?.ok);

const failed = Object.entries(checks).filter(([, value]) => !value).map(([name]) => name);
const result = {
  script: "preflight_epilepsy_cloud_trial_target.mjs",
  generated_at: new Date().toISOString(),
  status: failed.length ? "blocked" : "passed",
  cloud_target: {
    frontend_url: cloudFrontendUrl || null,
    api_base_url: cloudApiBaseUrl || null,
    api_health_url: apiHealthUrl || null,
  },
  sample_edf: {
    path: SAMPLE_EDF,
    exists: checks.sample_edf_exists,
    size_bytes: checks.sample_edf_exists ? fs.statSync(SAMPLE_EDF).size : null,
  },
  checks,
  failed,
  probes,
  next_command: failed.length
    ? "Set non-local QLANALYSER_CLOUD_FRONTEND_URL and QLANALYSER_CLOUD_API_BASE_URL, verify /api/health, then rerun this preflight."
    : "node scripts/run_epilepsy_cloud_trial_acceptance.mjs",
};

fs.mkdirSync(OUT_DIR, { recursive: true });
fs.writeFileSync(OUT_FILE, `${JSON.stringify(result, null, 2)}\n`, "utf8");
console.log(JSON.stringify(result, null, 2));
if ((process.env.QLANALYSER_REQUIRE_CLOUD_TARGET === "1" || process.env.QLANALYSER_REQUIRE_CLOUD === "1") && result.status !== "passed") {
  process.exit(1);
}
