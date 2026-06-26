import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const { chromium } = require("../frontend/node_modules/playwright");

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const DEFAULT_FRONTEND = "http://127.0.0.1:4174";
const DEFAULT_API = "http://127.0.0.1:8001/api";
const DEFAULT_OUT = path.join(
  ROOT,
  "work",
  "release_evidence",
  "20260619-2034-aliyun-v1-c0-integration",
  "c2_qc_reusable_gate_evidence",
);

function argValue(name, fallback) {
  const prefix = `--${name}=`;
  const found = process.argv.find((item) => item.startsWith(prefix));
  if (found) return found.slice(prefix.length);
  const index = process.argv.indexOf(`--${name}`);
  if (index >= 0 && process.argv[index + 1]) return process.argv[index + 1];
  const envName = `QLANALYSER_${name.replaceAll("-", "_").toUpperCase()}`;
  return process.env[envName] || fallback;
}

function ensureDir(dir) {
  try {
    fs.mkdirSync(dir, { recursive: true });
    return dir;
  } catch {
    const fallback = path.join(os.tmpdir(), "qlanalyser-qc-browser-gate");
    fs.mkdirSync(fallback, { recursive: true });
    return fallback;
  }
}

function writeJson(file, payload) {
  fs.writeFileSync(file, JSON.stringify(payload, null, 2), "utf8");
}

function includesAny(text, values) {
  return values.some((value) => text.includes(value));
}

async function main() {
  const frontendBase = argValue("frontend", DEFAULT_FRONTEND).replace(/\/$/, "");
  const apiBase = argValue("api", DEFAULT_API).replace(/\/$/, "");
  const outDir = ensureDir(argValue("out", DEFAULT_OUT));
  const url = `${frontendBase}/qc-lab.html?api=${encodeURIComponent(apiBase)}`;

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 });

  let verdict;
  try {
    const response = await page.goto(url, { waitUntil: "networkidle", timeout: 30000 });
    await page.waitForSelector("[data-qc-gate-panel]", { timeout: 15000 });

    const panel = page.locator("[data-qc-gate-panel]").first();
    await panel.scrollIntoViewIfNeeded();

    const gateScreenshot = path.join(outDir, "qc_gate_panel.png");
    const fullScreenshot = path.join(outDir, "qc_lab_full_page.png");
    const gateTextPath = path.join(outDir, "qc_gate_text.txt");
    const pageTextPath = path.join(outDir, "qc_page_text.txt");
    const domPath = path.join(outDir, "qc_gate_dom_attributes.json");
    const verdictPath = path.join(outDir, "qc_gate_verdict.json");

    await panel.screenshot({ path: gateScreenshot });
    await page.screenshot({ path: fullScreenshot, fullPage: true });

    const gateText = await panel.innerText();
    const pageText = await page.locator("body").innerText();
    const rootAttrs = await page.locator("#qcLab").evaluate((el) => ({
      data_qc_plan_status: el.getAttribute("data-qc-plan-status"),
      data_qc_plan_confirmed: el.getAttribute("data-qc-plan-confirmed"),
      data_qc_plan_revision: el.getAttribute("data-qc-plan-revision"),
      data_qc_plan_id: el.getAttribute("data-qc-plan-id"),
      data_qc_file_id: el.getAttribute("data-qc-file-id"),
      data_qc_psd_ready: el.getAttribute("data-qc-psd-ready"),
      data_qc_erp_ready: el.getAttribute("data-qc-erp-ready"),
    }));
    const panelAttrs = await panel.evaluate((el) => ({
      data_plan_status: el.getAttribute("data-plan-status"),
      data_plan_confirmed: el.getAttribute("data-plan-confirmed"),
      data_plan_revision: el.getAttribute("data-plan-revision"),
      data_file_id: el.getAttribute("data-file-id"),
      data_psd_ready: el.getAttribute("data-psd-ready"),
      data_erp_ready: el.getAttribute("data-erp-ready"),
    }));

    const checks = {
      page_ok: Boolean(response && response.ok()),
      gate_panel_visible: await panel.isVisible(),
      draft_or_confirmed_visible: includesAny(gateText, ["Draft plan", "Confirmed plan"]),
      revision_visible: gateText.includes("Revision"),
      file_id_visible: gateText.includes("Current file"),
      psd_readiness_visible: gateText.includes("PSD readiness"),
      erp_readiness_visible: gateText.includes("ERP readiness"),
      confirmed_gate_language_visible: gateText.includes("confirmed plan"),
      preview_only_filter_warning_visible: gateText.includes("Preview-only filter") && gateText.includes("not formal PSD/ERP analysis filters"),
      local_preview_segment_honesty_visible: gateText.includes("Preview segment evidence") && gateText.includes("local/plan JSON evidence"),
      root_attrs_present: Object.values(rootAttrs).every((value) => value !== null),
      panel_attrs_present: Object.values(panelAttrs).every((value) => value !== null),
    };
    const blockers = Object.entries(checks).filter(([, ok]) => !ok).map(([name]) => name);

    fs.writeFileSync(gateTextPath, gateText, "utf8");
    fs.writeFileSync(pageTextPath, pageText, "utf8");
    writeJson(domPath, { root: rootAttrs, panel: panelAttrs });

    verdict = {
      status: blockers.length ? "failed" : "passed",
      url,
      frontend_base: frontendBase,
      api_base: apiBase,
      output_dir: outDir,
      captured_at: new Date().toISOString(),
      checks,
      blockers,
      root_attributes: rootAttrs,
      panel_attributes: panelAttrs,
      files: {
        gate_screenshot: gateScreenshot,
        full_page_screenshot: fullScreenshot,
        gate_text: gateTextPath,
        page_text: pageTextPath,
        dom_attributes: domPath,
        verdict: verdictPath,
      },
    };
    writeJson(verdictPath, verdict);
  } catch (error) {
    verdict = {
      status: "failed",
      url,
      frontend_base: frontendBase,
      api_base: apiBase,
      output_dir: outDir,
      error: String(error && error.stack ? error.stack : error),
      captured_at: new Date().toISOString(),
    };
    writeJson(path.join(outDir, "qc_gate_verdict.json"), verdict);
  } finally {
    await browser.close();
  }

  console.log(JSON.stringify({
    status: verdict.status,
    blockers: verdict.blockers || [],
    output_dir: verdict.output_dir,
    verdict: path.join(verdict.output_dir, "qc_gate_verdict.json"),
  }, null, 2));

  if (verdict.status !== "passed") process.exit(1);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
