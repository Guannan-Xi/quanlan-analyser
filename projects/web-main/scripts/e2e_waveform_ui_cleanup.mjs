import { chromium, chromiumLaunchOptions } from "./lib/playwright_runtime.mjs";
import fs from "node:fs";
import path from "node:path";

const evidenceDir = path.resolve("work/release_evidence/20260627-waveform-ui-cleanup");
fs.mkdirSync(evidenceDir, { recursive: true });
const url = "http://127.0.0.1:4174/?customer_demo=auto&teaching_demo=auto&api=http://127.0.0.1:8001/api&v=wave-ui-cleanup#analysis";
const browser = await chromium.launch(chromiumLaunchOptions({ headless: true }));
const page = await browser.newPage({ viewport: { width: 1440, height: 960 } });
const result = { status: "pending", url, checks: {}, errors: [] };
try {
  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForSelector("#eegCanvas", { timeout: 60000 });
  await page.waitForFunction(() => {
    const canvas = document.querySelector("#eegCanvas");
    const empty = document.querySelector("#eegEmpty");
    return canvas && canvas.width > 0 && canvas.height > 0 && empty?.classList.contains("ready");
  }, { timeout: 60000 });
  result.checks.waveformReady = true;
  result.checks.confirmPlanButtonCount = await page.locator('button[data-real-action="confirm-plan-inline"]').count();
  result.checks.oldSegmentJumpCount = await page.locator('[data-preview-jump="segment"], [data-preview-jump="bad-channel"]').count();
  result.checks.shortcutButtonCount = await page.locator('[data-ia-action="show-waveform-shortcuts"]').count();
  await page.click('[data-ia-action="show-waveform-shortcuts"]');
  result.checks.shortcutTextVisible = (await page.locator('#eegEvents').innerText()).includes('快捷键');
  await page.click('[data-mode-target="markBadSegment"]');
  const box = await page.locator('#eegCanvas').boundingBox();
  if (!box) throw new Error('canvas box missing');
  await page.mouse.move(box.x + box.width * 0.28, box.y + box.height * 0.35);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * 0.45, box.y + box.height * 0.35, { steps: 8 });
  await page.mouse.up();
  const statusAfterCandidate = await page.locator('[data-testid="waveform-status-bar"]').innerText();
  const summaryAfterCandidate = await page.locator('#segmentSummary').innerText();
  result.checks.candidateVisible = /候选坏段\s*[1-9]/.test(statusAfterCandidate + "\n" + summaryAfterCandidate);
  result.checks.excludedNotImmediate = !/已确认剔除\s*[1-9]/.test(statusAfterCandidate);
  await page.click('[data-ia-action="confirm-candidate-bad-segments"]');
  const statusAfterConfirm = await page.locator('[data-testid="waveform-status-bar"]').innerText();
  result.checks.confirmedExcludedVisible = /已确认剔除\s*[1-9]/.test(statusAfterConfirm);
  await page.screenshot({ path: path.join(evidenceDir, 'waveform_ui_cleanup_after_candidate_confirm.png'), fullPage: true });
  const failed = Object.entries(result.checks).filter(([key, value]) => {
    if (key === 'confirmPlanButtonCount') return value !== 1;
    if (key === 'oldSegmentJumpCount') return value !== 0;
    if (key === 'shortcutButtonCount') return value !== 1;
    return value !== true;
  });
  result.status = failed.length ? 'failed' : 'passed';
  result.failed = failed;
} catch (error) {
  result.status = 'failed';
  result.errors.push(error.message || String(error));
} finally {
  await browser.close();
  fs.writeFileSync(path.join(evidenceDir, 'waveform_ui_cleanup_e2e.json'), JSON.stringify(result, null, 2), 'utf8');
  console.log(JSON.stringify(result, null, 2));
  if (result.status !== 'passed') process.exit(1);
}
