import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);

const moduleRoots = [
  process.env.QLANALYSER_PLAYWRIGHT_MODULE_DIR,
  path.join(process.cwd(), "node_modules", "playwright"),
  path.join(process.cwd(), "frontend", "node_modules", "playwright"),
  path.join(process.cwd(), "work", "deploy", "qlanalyser-current", "frontend", "node_modules", "playwright"),
].filter(Boolean);

function candidatePlaywrightPaths(moduleRoot) {
  const candidates = [moduleRoot];
  if (!fs.existsSync(moduleRoot)) return candidates;
  const stat = fs.statSync(moduleRoot);
  if (stat.isDirectory()) {
    candidates.push(path.join(moduleRoot, "playwright"));
    const pnpmRoot = path.join(moduleRoot, ".pnpm");
    if (fs.existsSync(pnpmRoot)) {
      for (const entry of fs.readdirSync(pnpmRoot)) {
        if (entry.startsWith("playwright@")) {
          candidates.push(path.join(pnpmRoot, entry, "node_modules", "playwright"));
        }
      }
    }
  }
  return [...new Set(candidates)];
}

async function loadPlaywright() {
  try {
    return await import("playwright");
  } catch (packageError) {
    const attempted = [];
    for (const moduleRoot of moduleRoots) {
      for (const candidate of candidatePlaywrightPaths(moduleRoot)) {
        try {
          attempted.push(candidate);
          if (fs.existsSync(candidate)) return require(candidate);
        } catch {
          // Try the next configured runtime.
        }
        try {
          const indexPath = path.join(candidate, "index.js");
          attempted.push(indexPath);
          if (fs.existsSync(indexPath)) return require(indexPath);
        } catch {
          // Try the next configured runtime.
        }
      }
    }
    const hint = [
      "Playwright is not resolvable for this QA runner.",
      "Install project test dependencies or set QLANALYSER_PLAYWRIGHT_MODULE_DIR to a Playwright package directory.",
      `Original package import error: ${packageError.message}`,
      `Attempted: ${attempted.join("; ") || "none"}`,
    ].join(" ");
    throw new Error(hint);
  }
}

let playwrightPromise = null;

async function getPlaywright() {
  if (!playwrightPromise) playwrightPromise = loadPlaywright();
  return playwrightPromise;
}

export const chromium = {
  async launch(options = {}) {
    const playwright = await getPlaywright();
    return playwright.chromium.launch(options);
  },
};

export function chromiumLaunchOptions(extra = {}) {
  const edgePaths = [
    process.env.QLANALYSER_BROWSER_EXECUTABLE,
    "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
    "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
  ].filter(Boolean);
  const executablePath = edgePaths.find((candidate) => fs.existsSync(candidate));
  return {
    ...(executablePath ? { executablePath } : {}),
    ...extra,
  };
}

export function classifyAcceptanceFailure(error, evidence = {}) {
  const message = String(error?.message || error || "");
  const stack = String(error?.stack || "");
  const combined = `${message}\n${stack}`;
  if (/Playwright is not resolvable|Cannot find package 'playwright'|Executable doesn't exist|browserType\.launch|Host system is missing dependencies|Please run .*playwright install|No executable path/i.test(combined)) {
    return "environment_blocked";
  }
  if (/ECONNREFUSED|ERR_CONNECTION_REFUSED|ERR_CONNECTION_CLOSED|ERR_NAME_NOT_RESOLVED|fetch failed|AbortError|Timeout .*page\.goto|page\.goto: Timeout|net::ERR_|frontend_down|backend_down/i.test(combined)) {
    return "service_unreachable";
  }
  const healthSamples = Array.isArray(evidence?.serviceHealthSamples) ? evidence.serviceHealthSamples : [];
  if (healthSamples.length && healthSamples.every((sample) => sample && sample.ok === false)) {
    return "service_unreachable";
  }
  return "product_failed";
}

export function isAcceptancePassedStatus(status) {
  return status === "passed";
}
