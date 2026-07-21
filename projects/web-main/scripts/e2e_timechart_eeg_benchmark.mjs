import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';

const url = process.env.TIMECHART_BENCHMARK_URL || 'http://127.0.0.1:4174/timechart-eeg-benchmark.html';
const outDir = path.resolve('work/release_evidence/20260627-timechart-eeg-benchmark');
fs.mkdirSync(outDir, { recursive: true });
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
const consoleErrors = [];
page.on('console', msg => { if (msg.type() === 'error') consoleErrors.push(msg.text()); });
await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
await page.getByTestId('run-benchmark').click();
await page.waitForFunction(() => window.__TIMECHART_EEG_BENCHMARK__ && window.__TIMECHART_EEG_BENCHMARK__.point_count > 0, null, { timeout: 60000 });
const metrics = await page.evaluate(() => window.__TIMECHART_EEG_BENCHMARK__);
const hostBox = await page.getByTestId('timechart-host').boundingBox();
const fallbackHidden = await page.getByTestId('canvas-fallback').evaluate(el => el.hidden);
const overlayBox = await page.getByTestId('overlay-layer').boundingBox();
const status = await page.getByTestId('renderer-status').textContent();
await page.screenshot({ path: path.join(outDir, 'timechart_eeg_benchmark.png'), fullPage: true });
await browser.close();
const result = {
  status: 'passed',
  url,
  metrics,
  renderer_status: status,
  checks: [
    { name: 'page_loaded', pass: true },
    { name: 'benchmark_metrics_available', pass: metrics.point_count > 0 },
    { name: 'chart_host_visible', pass: !!hostBox && hostBox.width > 800 && hostBox.height > 400 },
    { name: 'overlay_visible', pass: !!overlayBox && overlayBox.width > 800 && overlayBox.height > 400 },
    { name: 'renderer_or_fallback_available', pass: metrics.webgl_available || fallbackHidden === false },
    { name: 'no_mainline_wiring', pass: metrics.no_mainline_wiring === true },
    { name: 'console_errors_empty', pass: consoleErrors.length === 0 }
  ],
  console_errors: consoleErrors,
  screenshot: path.join(outDir, 'timechart_eeg_benchmark.png')
};
result.status = result.checks.every(c => c.pass) ? 'passed' : 'failed';
fs.writeFileSync(path.join(outDir, 'timechart_eeg_benchmark_e2e.json'), JSON.stringify(result, null, 2));
if (result.status !== 'passed') {
  console.error(JSON.stringify(result, null, 2));
  process.exit(1);
}
console.log(JSON.stringify(result, null, 2));
