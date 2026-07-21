import fs from "node:fs";
import path from "node:path";

const { chromium } = await import("playwright");

const repoRoot = process.cwd();
const evidenceDir = process.env.QLANALYSER_EDFBROWSER_E2E_DIR
  || path.join(repoRoot, "work", "release_evidence", "20260627-edfbrowser-waveform-interaction-dev");
fs.mkdirSync(evidenceDir, { recursive: true });

const frontendUrl = process.env.QLANALYSER_FRONTEND_URL || "http://127.0.0.1:4174/index.html?customer_demo=auto&api=http%3A%2F%2F127.0.0.1%3A8001%2Fapi";
const edgePath = "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";
const launchOptions = fs.existsSync(edgePath) ? { executablePath: edgePath } : {};

function changed(a, b, tolerance = 0.0001) {
  if (a === null || b === null) return false;
  return Math.abs(a - b) > tolerance;
}

function approx(actual, expected, tolerance = 0.35) {
  return Number.isFinite(actual) && Number.isFinite(expected) && Math.abs(actual - expected) <= tolerance;
}

function sensitivityValue(label = "") {
  const value = Number(String(label).match(/\d+(?:\.\d+)?/)?.[0] || NaN);
  return Number.isFinite(value) ? value : null;
}

async function canvasBox(page) {
  const canvas = page.locator("#eegCanvas");
  await canvas.waitFor({ state: "visible", timeout: 30000 });
  const box = await canvas.boundingBox();
  if (!box) throw new Error("Canvas bounding box is unavailable");
  return box;
}

async function readState(page) {
  return page.evaluate(() => ({
    start: Number(document.querySelector("#eegStartInput")?.value || 0),
    windowSec: Number(document.querySelector("#eegWindowInput")?.value || 0),
    windowMax: Number(document.querySelector("#eegWindowInput")?.max || 0),
    gainLabel: document.querySelector("#eegGainLabel")?.textContent || "",
    segmentStart: document.querySelector("#segmentStart")?.value || "",
    segmentEnd: document.querySelector("#segmentEnd")?.value || "",
    mode: document.querySelector('[data-testid="preview-edit-workbench"]')?.dataset.mode || "",
    statusText: document.querySelector('[data-testid="waveform-status-bar"]')?.textContent || "",
    gateText: document.querySelector('[data-testid="analysis-preparation-gate"]')?.textContent || "",
    gateHidden: Boolean(document.querySelector('[data-testid="analysis-preparation-gate"]')?.hidden),
    canvasMode: document.querySelector("#eegCanvas")?.dataset.mode || "",
    timechartCount: document.querySelectorAll("[class*=TimeChart], [id*=TimeChart], timechart").length,
  }));
}

async function dragCanvas(page, startRatio, endRatio) {
  const box = await canvasBox(page);
  const y = box.y + box.height * 0.48;
  const x1 = box.x + box.width * startRatio;
  const x2 = box.x + box.width * endRatio;
  await page.mouse.move(x1, y);
  await page.mouse.down({ button: "left" });
  await page.mouse.move(x2, y, { steps: 6 });
  await page.mouse.up({ button: "left" });
  await page.waitForTimeout(250);
}

async function run() {
  const browser = await chromium.launch({ headless: true, ...launchOptions });
  const page = await browser.newPage({ viewport: { width: 1440, height: 980 }, deviceScaleFactor: 1 });
  const checks = [];
  const add = (id, passed, details = {}) => checks.push({ id, passed: Boolean(passed), details });

  try {
    await page.goto(frontendUrl, { waitUntil: "domcontentloaded", timeout: 60000 });
    await page.waitForTimeout(1000);
    await page.getByText("教学模式").first().click();
    await page.waitForTimeout(1500);
    await page.keyboard.press("Escape");
    await page.waitForTimeout(1000);
    await page.locator('[data-view="analysis"]').first().click({ force: true });
    await page.locator("#eegCanvas").waitFor({ state: "visible", timeout: 30000 });
    await page.waitForFunction(() => document.querySelector('[data-testid="waveform-status-bar"]')?.textContent.includes("uV/row"), null, { timeout: 30000 });
    if (!(await page.locator('[data-testid="analysis-preparation-gate"]').evaluate((el) => el.hidden).catch(() => true))) {
      await page.locator('[data-real-action="confirm-plan-inline"]').click({ force: true });
      await page.waitForFunction(() => document.querySelector('[data-testid="analysis-preparation-gate"]')?.hidden === true, null, { timeout: 30000 }).catch(() => {});
    }
    await page.waitForTimeout(1000);

    const initial = await readState(page);
    add("T-EDF-10", initial.statusText.includes("uV/row") && initial.statusText.includes("s/page") && initial.mode === "browse", initial);
    add("T-EDF-12", initial.timechartCount === 0 && !/自动诊断|临床诊断|治疗|医疗决策/.test(await page.locator("body").innerText()), { timechartCount: initial.timechartCount });

    await page.locator('[data-testid="waveform-mode-browse"]').click();
    const beforeBrowseDrag = await readState(page);
    await dragCanvas(page, 0.25, 0.60);
    const afterBrowseDrag = await readState(page);
    add("T-EDF-06", beforeBrowseDrag.segmentStart === afterBrowseDrag.segmentStart && beforeBrowseDrag.segmentEnd === afterBrowseDrag.segmentEnd && afterBrowseDrag.mode === "browse", { beforeBrowseDrag, afterBrowseDrag });

    await page.locator('[data-testid="waveform-mode-select-segment"]').click();
    await dragCanvas(page, 0.22, 0.58);
    const afterSelect = await readState(page);
    add("T-EDF-07", afterSelect.mode === "selectSegment" && afterSelect.segmentStart !== afterSelect.segmentEnd, afterSelect);

    await page.locator('[data-testid="waveform-mode-mark-bad-segment"]').click();
    await dragCanvas(page, 0.32, 0.50);
    await page.waitForTimeout(500);
    const afterBadSegment = await readState(page);
    add("T-EDF-08", afterBadSegment.mode === "markBadSegment" && /剔除|坏段|恢复/.test(afterBadSegment.statusText + " " + await page.locator("#eegEvents").innerText()), afterBadSegment);

    await page.locator('[data-testid="waveform-mode-browse"]').click();
    const box = await canvasBox(page);
    await page.mouse.move(box.x + box.width * 0.5, box.y + box.height * 0.5);
    await page.keyboard.down(process.platform === "darwin" ? "Meta" : "Control");
    await page.mouse.wheel(0, -400);
    await page.keyboard.up(process.platform === "darwin" ? "Meta" : "Control");
    await page.waitForTimeout(500);
    const beforeWheel = await readState(page);
    await page.mouse.wheel(0, 400);
    await page.waitForTimeout(500);
    const afterWheel = await readState(page);
    const expectedWheelStart = beforeWheel.start + beforeWheel.windowSec * 0.08;
    add("T-EDF-01", approx(afterWheel.start, expectedWheelStart) && !changed(beforeWheel.windowSec, afterWheel.windowSec), { beforeWheel, afterWheel, expectedWheelStart });

    const beforeCtrlWheel = await readState(page);
    await page.mouse.move(box.x + box.width * 0.5, box.y + box.height * 0.5);
    await page.keyboard.down(process.platform === "darwin" ? "Meta" : "Control");
    await page.mouse.wheel(0, -400);
    await page.keyboard.up(process.platform === "darwin" ? "Meta" : "Control");
    await page.waitForTimeout(500);
    const afterCtrlWheel = await readState(page);
    const expectedCtrlWheelWindow = beforeCtrlWheel.windowSec / 1.2;
    const beforeCtrlAnchor = beforeCtrlWheel.start + beforeCtrlWheel.windowSec * 0.5;
    const afterCtrlAnchor = afterCtrlWheel.start + afterCtrlWheel.windowSec * 0.5;
    const anchorDriftToleranceSec = Math.max(0.05, 2 / 200);
    add("T-EDF-02", approx(afterCtrlWheel.windowSec, expectedCtrlWheelWindow) && approx(afterCtrlAnchor, beforeCtrlAnchor, anchorDriftToleranceSec + 0.35), { beforeCtrlWheel, afterCtrlWheel, expectedCtrlWheelWindow, beforeCtrlAnchor, afterCtrlAnchor, anchorDriftToleranceSec });

    const beforePage = await readState(page);
    await page.keyboard.press("PageDown");
    await page.waitForTimeout(500);
    const afterPage = await readState(page);
    const expectedPageStart = beforePage.start + beforePage.windowSec;
    add("T-EDF-03", approx(afterPage.start, expectedPageStart), { beforePage, afterPage, expectedPageStart });

    const beforeArrow = await readState(page);
    await page.keyboard.press("ArrowRight");
    await page.waitForTimeout(500);
    const afterArrow = await readState(page);
    const expectedArrowStart = beforeArrow.start + beforeArrow.windowSec * 0.10;
    add("T-EDF-04", approx(afterArrow.start, expectedArrowStart), { beforeArrow, afterArrow, expectedArrowStart });

    const beforeMiddle = await readState(page);
    await page.mouse.move(box.x + box.width * 0.6, box.y + box.height * 0.5);
    await page.mouse.down({ button: "middle" });
    await page.mouse.move(box.x + box.width * 0.35, box.y + box.height * 0.5, { steps: 6 });
    await page.mouse.up({ button: "middle" });
    await page.waitForTimeout(500);
    const afterMiddle = await readState(page);
    const expectedMiddleStart = beforeMiddle.start + beforeMiddle.windowSec * 0.25;
    add("T-EDF-05", approx(afterMiddle.start, expectedMiddleStart), { beforeMiddle, afterMiddle, expectedMiddleStart });

    const beforePlus = await readState(page);
    await page.keyboard.press("+");
    await page.waitForTimeout(250);
    const afterPlus = await readState(page);
    await page.keyboard.down(process.platform === "darwin" ? "Meta" : "Control");
    await page.keyboard.press("+");
    await page.keyboard.up(process.platform === "darwin" ? "Meta" : "Control");
    await page.waitForTimeout(500);
    const afterCtrlPlus = await readState(page);
    const beforeSensitivity = sensitivityValue(beforePlus.gainLabel);
    const afterSensitivity = sensitivityValue(afterPlus.gainLabel);
    add("T-EDF-09", approx(afterSensitivity, beforeSensitivity / 1.2, 0.8) && approx(afterCtrlPlus.windowSec, afterPlus.windowSec / 1.2), { beforePlus, afterPlus, afterCtrlPlus, beforeSensitivity, afterSensitivity });

    add("T-EDF-11", await page.locator('[data-testid="analysis-preparation-gate"]').count() === 1, await readState(page));
    const beforeMaxZoomOut = await readState(page);
    for (let index = 0; index < 30; index += 1) {
      await page.locator("#eegZoomOutBtn").click({ force: true });
      await page.waitForTimeout(120);
    }
    const afterMaxZoomOut = await readState(page);
    add("T-EDF-13", afterMaxZoomOut.windowMax > 30 && afterMaxZoomOut.windowMax <= 300 && afterMaxZoomOut.windowSec > 30 && afterMaxZoomOut.windowSec <= afterMaxZoomOut.windowMax, { beforeMaxZoomOut, afterMaxZoomOut });

    const screenshotPath = path.join(evidenceDir, "edfbrowser_waveform_interaction_e2e.png");
    await page.screenshot({ path: screenshotPath, fullPage: true });

    const status = checks.every((check) => check.passed) ? "passed" : "failed";
    const result = {
      status,
      generated_at: new Date().toISOString(),
      frontendUrl,
      checks,
      screenshotPath,
    };
    const outputPath = path.join(evidenceDir, "edfbrowser_waveform_interaction_browser_e2e.json");
    fs.writeFileSync(outputPath, `${JSON.stringify(result, null, 2)}\n`, "utf8");
    console.log(JSON.stringify({ status, outputPath, screenshotPath, failed: checks.filter((check) => !check.passed).map((check) => check.id) }, null, 2));
    if (status !== "passed") process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

try {
  await run();
} catch (error) {
  const outputPath = path.join(evidenceDir, "edfbrowser_waveform_interaction_browser_e2e.json");
  fs.writeFileSync(outputPath, `${JSON.stringify({ status: "failed", error: error.stack || String(error), generated_at: new Date().toISOString() }, null, 2)}\n`, "utf8");
  console.error(error.stack || String(error));
  process.exit(1);
}
