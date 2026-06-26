import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1")), "..");
const EVIDENCE_ROOT = process.env.QLANALYSER_EPILEPSY_TIMECHART_EVIDENCE_DIR
  || path.join(ROOT, "work/release_evidence/epilepsy_source_workbench_replica_acceptance/timechart_lab_20260627");
const LATEST_VERDICT = path.join(ROOT, "work/release_evidence/epilepsy_source_workbench_replica_acceptance/latest_final_verdict.json");
const API_BASE = process.env.QLANALYSER_API_BASE || "http://127.0.0.1:8001/api";
const FRONTEND_BASE = process.env.QLANALYSER_FRONTEND_BASE || "http://127.0.0.1:4174";
const CHROME_EXE = process.env.CHROME_EXE || "C:/Users/XGN/AppData/Local/Google/Chrome/Application/chrome.exe";

function latestTaskId() {
  if (process.env.QLANALYSER_EPILEPSY_TASK_ID) return process.env.QLANALYSER_EPILEPSY_TASK_ID;
  try {
    const parsed = JSON.parse(fs.readFileSync(LATEST_VERDICT, "utf8"));
    const check = (parsed.checks || []).find((item) => item.name === "epilepsy_ml_task_completed");
    if (check?.detail?.task_id) return check.detail.task_id;
  } catch {}
  return "task_93d24dd27854";
}

function buildUrl() {
  const url = new URL("/epilepsy-workbench.html", FRONTEND_BASE);
  url.searchParams.set("api", API_BASE);
  url.searchParams.set("mode", "ml_epoch_classifier");
  url.searchParams.set("renderer", "timechart");
  url.searchParams.set("task", latestTaskId());
  return url.toString();
}

function ensure(condition, message) {
  if (!condition) throw new Error(message);
}

async function waveformState(page) {
  return page.evaluate(() => {
    const statusbar = document.querySelector('[data-testid="epilepsy-waveform-statusbar"]');
    const frame = document.querySelector('[data-testid="epilepsy-waveform-frame"]');
    return {
      snapshot: window.__QLANALYSER_EPILEPSY_WAVEFORM_STATE__ || null,
      statusbar_present: Boolean(statusbar),
      minimap_present: Boolean(document.querySelector('[data-testid="epilepsy-waveform-minimap"]')),
      mode: statusbar?.dataset.mode || "",
      gain: statusbar?.dataset.gain || "",
      start_sec: Number(statusbar?.dataset.startSec || 0),
      duration_sec: Number(statusbar?.dataset.durationSec || 0),
      frame_focused: document.activeElement === frame,
      correction_button_disabled: document.querySelector("#markSeizureBtn")?.disabled ?? null,
      stage_button_disabled: document.querySelector("#applyStageSeizureBtn")?.disabled ?? null,
    };
  });
}

async function reviewSnapshot(page) {
  return page.evaluate(() => {
    const prefix = "qlanalyser.epilepsy.review.v1.";
    return Object.keys(localStorage)
      .filter((key) => key.startsWith(prefix))
      .sort()
      .map((key) => {
        try {
          return { key, value: JSON.parse(localStorage.getItem(key) || "{}") };
        } catch (error) {
          return { key, error: String(error) };
        }
      });
  });
}

function reviewWriteCount(snapshot) {
  return snapshot.reduce((count, item) => {
    const overrides = Object.keys(item.value?.epochOverrides || {}).length;
    const actions = (item.value?.reviewActions || []).filter((action) => action.action === "set_stage").length;
    return count + overrides + actions;
  }, 0);
}

async function waitForWaveformAction(page, action) {
  const started = Date.now();
  const responsePromise = page.waitForResponse(
    (response) => response.url().includes("/waveform-window") && response.status() === 200,
    { timeout: 20000 },
  ).catch(() => null);
  await action();
  await responsePromise;
  await page.waitForTimeout(350);
  return Date.now() - started;
}

async function runCase(browser, name, options = {}) {
  const outDir = path.join(EVIDENCE_ROOT, name);
  fs.rmSync(outDir, { recursive: true, force: true });
  fs.mkdirSync(outDir, { recursive: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1180 } });
  const page = await context.newPage();
  const evidence = {
    case: name,
    url: buildUrl(),
    not_07_main_workbench: true,
    console_errors: [],
    failed_requests: [],
    http_errors: [],
    waveform_window_response_ms: null,
    interaction_response_ms: {},
    checks: {},
    screenshots: {},
  };

  page.on("console", (message) => {
    if (["error", "warning"].includes(message.type())) {
      evidence.console_errors.push({ type: message.type(), text: message.text() });
    }
  });
  page.on("requestfailed", (request) => {
    const url = request.url();
    if (!options.forceFallback || /timechart|d3/.test(url)) {
      evidence.failed_requests.push({ url, failure: request.failure()?.errorText || "" });
    }
  });
  page.on("response", (response) => {
    if (response.status() >= 400) {
      evidence.http_errors.push({ url: response.url(), status: response.status() });
    }
  });
  if (options.forceFallback) {
    await context.route(/(timechart|d3).*\.js/i, (route) => route.abort("blockedbyclient"));
  }

  try {
    await page.goto(evidence.url, { waitUntil: "networkidle", timeout: 60000 });
    await page.waitForSelector('[data-testid="epilepsy-event-table"] tbody tr', { timeout: 60000 });
    await page.click('[data-testid="epilepsy-event-table"] tbody tr:first-child [data-select-event]');
    await page.screenshot({ path: path.join(outDir, "01_loaded.png"), fullPage: true });
    evidence.screenshots.loaded = path.join(outDir, "01_loaded.png");

    const waveformStarted = Date.now();
    const waveformResponsePromise = page.waitForResponse(
      (response) => response.url().includes("/waveform-window") && response.status() === 200,
      { timeout: 60000 },
    );
    await page.click("#runWaveformBtn");
    await waveformResponsePromise;
    evidence.waveform_window_response_ms = Date.now() - waveformStarted;

    await page.waitForFunction((forceFallback) => {
      const metrics = window.__QLANALYSER_EPILEPSY_TIMECHART__;
      const traceCount = document.querySelectorAll('[data-testid="epilepsy-waveform-frame"] .waveform-line, [data-testid="epilepsy-waveform-frame"] .waveform-envelope').length;
      if (forceFallback) return Boolean(metrics?.fallback && traceCount > 0);
      if (metrics?.renderer === "timechart" && Number(metrics.point_count || 0) > 0) return true;
      return Boolean(metrics?.fallback && traceCount > 0);
    }, Boolean(options.forceFallback), { timeout: 70000 });
    await page.screenshot({ path: path.join(outDir, "02_timechart_or_fallback.png"), fullPage: true });
    evidence.screenshots.timechart_or_fallback = path.join(outDir, "02_timechart_or_fallback.png");

    evidence.timechart_metrics = await page.evaluate(() => window.__QLANALYSER_EPILEPSY_TIMECHART__ || null);
    evidence.dom = await page.evaluate(() => {
      const host = document.querySelector('[data-testid="epilepsy-timechart-host"]');
      const svg = document.querySelector('[data-testid="epilepsy-waveform-frame"] .waveform-svg');
      const epochCells = Array.from(document.querySelectorAll("[data-epoch]"));
      const traceCount = document.querySelectorAll('[data-testid="epilepsy-waveform-frame"] .waveform-line, [data-testid="epilepsy-waveform-frame"] .waveform-envelope').length;
      return {
        body_text_sample: document.body.innerText.slice(0, 500),
        host_present: Boolean(host),
        host_rect: host ? host.getBoundingClientRect().toJSON() : null,
        svg_present: Boolean(svg),
        svg_rect: svg ? svg.getBoundingClientRect().toJSON() : null,
        trace_count: traceCount,
        renderer_buttons: Array.from(document.querySelectorAll("[data-waveform-renderer]")).map((button) => ({
          renderer: button.dataset.waveformRenderer,
          text: button.textContent.trim(),
          primary: button.classList.contains("primary"),
        })),
        epoch_count: epochCells.length,
        epoch_class_domain_ok: epochCells.every((cell) => cell.classList.contains("normal") || cell.classList.contains("seizure")),
        event_overlay_present: Boolean(document.querySelector(".timechart-event-overlay, .waveform-event-band")),
      };
    });

    const frame = page.locator('[data-testid="epilepsy-waveform-frame"]');
    await frame.focus();
    evidence.interaction = {
      initial: await waveformState(page),
      review_before_browse_shortcut: await reviewSnapshot(page),
    };

    evidence.interaction_response_ms.wheel_pan = await waitForWaveformAction(page, async () => {
      await frame.hover();
      await page.mouse.wheel(0, 650);
    });
    evidence.interaction.after_wheel_pan = await waveformState(page);

    evidence.interaction_response_ms.ctrl_wheel_zoom = await waitForWaveformAction(page, async () => {
      await frame.focus();
      await frame.hover();
      await page.keyboard.down("Control");
      await page.mouse.wheel(0, -650);
      await page.keyboard.up("Control");
    });
    evidence.interaction.after_ctrl_wheel_zoom = await waveformState(page);

    const gainStarted = Date.now();
    await frame.focus();
    await page.keyboard.press("+");
    await page.waitForTimeout(180);
    evidence.interaction.after_plus_gain = await waveformState(page);
    await page.keyboard.press("-");
    await page.waitForTimeout(180);
    evidence.interaction_response_ms.plus_minus_gain = Date.now() - gainStarted;
    evidence.interaction.after_minus_gain = await waveformState(page);

    await frame.focus();
    await frame.hover();
    const box = await frame.boundingBox();
    if (box) {
      evidence.interaction_response_ms.left_drag_zoom_select = await waitForWaveformAction(page, async () => {
        await page.mouse.move(box.x + box.width * 0.25, box.y + box.height * 0.5);
        await page.mouse.down();
        await page.mouse.move(box.x + box.width * 0.72, box.y + box.height * 0.5, { steps: 5 });
        await page.mouse.up();
      });
    }
    evidence.interaction.after_left_drag_zoom_select = await waveformState(page);

    const boxAfterZoom = await frame.boundingBox();
    if (boxAfterZoom) {
      evidence.interaction_response_ms.middle_drag_pan = await waitForWaveformAction(page, async () => {
        await page.mouse.move(boxAfterZoom.x + boxAfterZoom.width * 0.68, boxAfterZoom.y + boxAfterZoom.height * 0.5);
        await page.mouse.down({ button: "middle" });
        await page.mouse.move(boxAfterZoom.x + boxAfterZoom.width * 0.35, boxAfterZoom.y + boxAfterZoom.height * 0.5, { steps: 5 });
        await page.mouse.up({ button: "middle" });
      });
    }
    evidence.interaction.after_middle_drag_pan = await waveformState(page);

    evidence.interaction_response_ms.arrow_key_pan = await waitForWaveformAction(page, async () => {
      await frame.focus();
      await page.keyboard.press("ArrowRight");
    });
    evidence.interaction.after_arrow_key_pan = await waveformState(page);

    evidence.interaction_response_ms.page_key_pan = await waitForWaveformAction(page, async () => {
      await frame.focus();
      await page.keyboard.press("PageDown");
    });
    evidence.interaction.after_page_key_pan = await waveformState(page);

    evidence.interaction_response_ms.filter_key_toggle = await waitForWaveformAction(page, async () => {
      await frame.focus();
      await page.keyboard.press("f");
    });
    evidence.interaction.after_filter_key_toggle = await waveformState(page);

    evidence.interaction_response_ms.reset_key = await waitForWaveformAction(page, async () => {
      await frame.focus();
      await page.keyboard.press("r");
    });
    evidence.interaction.after_reset_key = await waveformState(page);

    await frame.focus();
    await page.keyboard.press("e");
    await page.waitForTimeout(150);
    evidence.interaction.after_keyboard_e_correct = await waveformState(page);
    await frame.focus();
    await page.keyboard.press("e");
    await page.waitForTimeout(150);
    evidence.interaction.after_keyboard_e_browse = await waveformState(page);

    await page.screenshot({ path: path.join(outDir, "04_edfbrowser_interaction.png"), fullPage: true });
    evidence.screenshots.edfbrowser_interaction = path.join(outDir, "04_edfbrowser_interaction.png");

    await page.click('[data-testid="epilepsy-waveform-mode-browse"]');
    await page.keyboard.down("Shift");
    await page.keyboard.press("Digit2");
    await page.keyboard.up("Shift");
    await page.waitForTimeout(250);
    evidence.interaction.review_after_browse_shortcut = await reviewSnapshot(page);
    evidence.interaction.after_browse_shortcut = await waveformState(page);

    await page.click('[data-testid="epilepsy-waveform-mode-correct"]');
    await page.keyboard.down("Shift");
    await page.keyboard.press("Digit2");
    await page.keyboard.up("Shift");
    await page.waitForTimeout(450);
    evidence.interaction.review_after_correction_shortcut = await reviewSnapshot(page);
    evidence.interaction.after_correction_shortcut = await waveformState(page);
    await page.screenshot({ path: path.join(outDir, "05_correction_mode.png"), fullPage: true });
    evidence.screenshots.correction_mode = path.join(outDir, "05_correction_mode.png");

    await page.click('[data-testid="epilepsy-renderer-svg"]');
    await page.waitForSelector('[data-testid="epilepsy-waveform-frame"] .waveform-svg', { timeout: 15000 });
    await page.screenshot({ path: path.join(outDir, "03_svg_current.png"), fullPage: true });
    evidence.screenshots.svg_current = path.join(outDir, "03_svg_current.png");

    const svgInfo = await page.evaluate(() => {
      const svg = document.querySelector('[data-testid="epilepsy-waveform-frame"] .waveform-svg');
      return {
        visible: Boolean(svg),
        path_count: document.querySelectorAll(".waveform-line, .waveform-envelope").length,
        event_band_count: document.querySelectorAll(".waveform-event-band").length,
      };
    });

    const unexpectedHttpErrors = evidence.http_errors.filter((item) => !/\/favicon\.ico$/i.test(new URL(item.url).pathname));
    const unexpectedConsoleErrors = evidence.console_errors.filter((item) => {
      if (/blockedbyclient|ERR_BLOCKED_BY_CLIENT/i.test(item.text)) return false;
      if (/Failed to load resource/i.test(item.text) && unexpectedHttpErrors.length === 0) return false;
      return true;
    });
    evidence.checks = {
      page_loaded: true,
      event_rows_present: await page.locator('[data-testid="epilepsy-event-table"] tbody tr').count() > 0,
      waveform_window_fast_enough: evidence.waveform_window_response_ms < 2000,
      renderer_buttons_present: evidence.dom.renderer_buttons.length === 2,
      timechart_or_fallback_nonblank: Boolean(
        (evidence.timechart_metrics?.renderer === "timechart" && Number(evidence.timechart_metrics?.point_count || 0) > 0)
        || evidence.dom.trace_count > 0,
      ),
      fallback_recorded_when_forced: !options.forceFallback || Boolean(evidence.timechart_metrics?.fallback && evidence.dom.trace_count > 0),
      svg_current_still_works: svgInfo.visible && svgInfo.path_count > 0,
      stage_code_discrete_dom: evidence.dom.epoch_class_domain_ok && evidence.dom.epoch_count > 0,
      event_overlay_present: evidence.dom.event_overlay_present || svgInfo.event_band_count > 0,
      waveform_statusbar_present: evidence.interaction.initial.statusbar_present,
      waveform_minimap_present: evidence.interaction.initial.minimap_present,
      wheel_pans_start: Math.abs(evidence.interaction.after_wheel_pan.start_sec - evidence.interaction.initial.start_sec) > 0.05,
      wheel_does_not_zoom_time: Math.abs(evidence.interaction.after_wheel_pan.duration_sec - evidence.interaction.initial.duration_sec) < 0.15,
      ctrl_wheel_zooms_duration: Math.abs(evidence.interaction.after_ctrl_wheel_zoom.duration_sec - evidence.interaction.after_wheel_pan.duration_sec) > 0.05,
      ctrl_wheel_does_not_change_gain: evidence.interaction.after_ctrl_wheel_zoom.gain === evidence.interaction.after_wheel_pan.gain,
      plus_minus_changes_gain: evidence.interaction.after_plus_gain.gain !== evidence.interaction.after_ctrl_wheel_zoom.gain
        && evidence.interaction.after_minus_gain.gain === evidence.interaction.after_ctrl_wheel_zoom.gain,
      left_drag_zoom_select_changes_duration: Math.abs(evidence.interaction.after_left_drag_zoom_select.duration_sec - evidence.interaction.after_ctrl_wheel_zoom.duration_sec) > 0.05,
      middle_drag_pans_start: Math.abs(evidence.interaction.after_middle_drag_pan.start_sec - evidence.interaction.after_left_drag_zoom_select.start_sec) > 0.05,
      arrow_key_pans_one_tenth: Math.abs(
        Math.abs(evidence.interaction.after_arrow_key_pan.start_sec - evidence.interaction.after_middle_drag_pan.start_sec)
        - evidence.interaction.after_middle_drag_pan.duration_sec * 0.1,
      ) < 0.35,
      page_key_pans_page: Math.abs(
        Math.abs(evidence.interaction.after_page_key_pan.start_sec - evidence.interaction.after_arrow_key_pan.start_sec)
        - evidence.interaction.after_arrow_key_pan.duration_sec,
      ) < 0.8,
      filter_key_changes_profile: evidence.interaction.after_filter_key_toggle.snapshot?.filter_profile_id !== evidence.interaction.after_page_key_pan.snapshot?.filter_profile_id,
      reset_key_refits_event: Math.abs(evidence.interaction.after_reset_key.duration_sec - evidence.interaction.initial.duration_sec) < 0.15,
      keyboard_e_toggles_mode: evidence.interaction.after_keyboard_e_correct.mode === "correct" && evidence.interaction.after_keyboard_e_browse.mode === "browse",
      browse_mode_blocks_stage_write: reviewWriteCount(evidence.interaction.review_after_browse_shortcut) === reviewWriteCount(evidence.interaction.review_before_browse_shortcut),
      correction_mode_enables_stage_write: reviewWriteCount(evidence.interaction.review_after_correction_shortcut) > reviewWriteCount(evidence.interaction.review_after_browse_shortcut),
      correction_mode_buttons_enabled: evidence.interaction.after_correction_shortcut.correction_button_disabled === false && evidence.interaction.after_correction_shortcut.stage_button_disabled === false,
      no_unexpected_console_errors: unexpectedConsoleErrors.length === 0 && unexpectedHttpErrors.length === 0,
    };
    ensure(Object.values(evidence.checks).every(Boolean), `Checks failed in ${name}`);
    evidence.status = "passed";
  } catch (error) {
    evidence.status = "failed";
    evidence.error = String(error?.stack || error);
    try {
      await page.screenshot({ path: path.join(outDir, "failure.png"), fullPage: true });
      evidence.screenshots.failure = path.join(outDir, "failure.png");
    } catch {}
  } finally {
    await context.close();
    fs.writeFileSync(path.join(outDir, "evidence.json"), `${JSON.stringify(evidence, null, 2)}\n`, "utf8");
  }
  return evidence;
}

async function main() {
  fs.mkdirSync(EVIDENCE_ROOT, { recursive: true });
  const launchOptions = { headless: true };
  if (fs.existsSync(CHROME_EXE)) launchOptions.executablePath = CHROME_EXE;
  const browser = await chromium.launch(launchOptions);
  const cases = [];
  try {
    cases.push(await runCase(browser, "natural_timechart"));
    cases.push(await runCase(browser, "forced_fallback", { forceFallback: true }));
  } finally {
    await browser.close();
  }
  const summary = {
    schema_version: "epilepsy_timechart_lab_e2e.v1",
    status: cases.every((item) => item.status === "passed") ? "passed" : "failed",
    evidence_root: EVIDENCE_ROOT,
    frontend_url: buildUrl(),
    cases: cases.map((item) => ({
      case: item.case,
      status: item.status,
      waveform_window_response_ms: item.waveform_window_response_ms,
      metrics: item.timechart_metrics,
      checks: item.checks,
      screenshots: item.screenshots,
      error: item.error || null,
    })),
    generated_at: new Date().toISOString(),
  };
  const summaryPath = path.join(EVIDENCE_ROOT, "timechart_epilepsy_workbench_experiment_20260627.json");
  fs.writeFileSync(summaryPath, `${JSON.stringify(summary, null, 2)}\n`, "utf8");
  console.log(JSON.stringify({ status: summary.status, summary_path: summaryPath, evidence_root: EVIDENCE_ROOT }, null, 2));
  if (summary.status !== "passed") process.exit(1);
}

main();
