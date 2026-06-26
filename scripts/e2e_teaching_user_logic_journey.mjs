import fs from 'node:fs/promises';
import path from 'node:path';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { chromium } = require('../frontend/node_modules/playwright');

const repo = process.cwd();
const outDir = path.join(repo, 'work', 'release_evidence', '20260627-teaching-user-logic-journey');
await fs.mkdir(outDir, { recursive: true });

const edgeCandidates = [
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
];
let executablePath;
for (const candidate of edgeCandidates) {
  try { await fs.access(candidate); executablePath = candidate; break; } catch {}
}

const browser = await chromium.launch({ headless: true, executablePath });
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
const requests = [];
page.on('request', req => {
  if (req.url().includes('/api/')) requests.push({ method: req.method(), url: req.url(), postData: req.postData() });
});

const url = 'http://127.0.0.1:4174/index.html?customer_demo=auto&api=http%3A%2F%2F127.0.0.1%3A8001%2Fapi';
const checks = [];
function add(name, pass, details = {}) { checks.push({ name, pass: Boolean(pass), details }); }
async function snap(name) { await page.screenshot({ path: path.join(outDir, `${name}.png`), fullPage: true }); }
async function visibleLocator(selector) { return page.locator(selector).filter({ hasNot: page.locator('[hidden]') }).first(); }
async function clickTextInMain(regex, timeout = 5000) {
  const scopes = ['#appShell:not([hidden])', 'main:not([hidden])', 'body'];
  for (const scope of scopes) {
    const loc = page.locator(scope).getByText(regex).first();
    if (await loc.count().catch(() => 0)) {
      try { await loc.click({ timeout }); return true; } catch {}
    }
  }
  return false;
}
async function getVisibleAction(action) {
  const locator = page.locator(`[data-real-action="${action}"]:visible`).first();
  if (!(await locator.count().catch(() => 0))) return null;
  return locator;
}
async function appState(label) {
  return await page.evaluate((label) => {
    const isVisible = (el) => !!el && !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
    const visibleRunPsd = [...document.querySelectorAll('[data-real-action="run-psd"]')].find(isVisible);
    const visibleConfirm = [...document.querySelectorAll('[data-real-action="confirm-plan-inline"], [data-action="confirm-plan-inline"]')].find(isVisible);
    const activeViewEls = [...document.querySelectorAll('.view.active, [data-view].active')].filter(isVisible);
    const visibleText = [...document.body.querySelectorAll('body *')]
      .filter(isVisible)
      .map(el => el.innerText || '')
      .join('\n')
      .replace(/\n{3,}/g, '\n\n');
    const teachingBanner = [...document.querySelectorAll('.teaching-sandbox-banner')].find(isVisible)?.innerText || '';
    return {
      label,
      teachingBanner,
      runPsdDisabled: visibleRunPsd ? visibleRunPsd.disabled || visibleRunPsd.getAttribute('aria-disabled') === 'true' : null,
      runPsdText: visibleRunPsd?.innerText || '',
      runPsdTitle: visibleRunPsd?.getAttribute('title') || visibleRunPsd?.getAttribute('data-disabled-reason') || '',
      confirmDisabled: visibleConfirm ? visibleConfirm.disabled || visibleConfirm.getAttribute('aria-disabled') === 'true' : null,
      activeView: activeViewEls.map(e => e.id || e.getAttribute('data-view')).filter(Boolean),
      visibleHasUploadDemand: /请上传|没有上传|上传数据/.test(visibleText),
      visibleHasTeachingText: /教学模式|教学数据|内置|无需上传/.test(visibleText),
      visibleSample: visibleText.slice(0, 1800),
    };
  }, label);
}

const states = [];
try {
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(1500);
  states.push(await appState('initial'));
  await snap('01_initial');

  await clickTextInMain(/登录并进入项目|登录/, 10000);
  await page.waitForTimeout(3000);
  states.push(await appState('after_login'));
  await snap('02_after_login');

  await clickTextInMain(/教学模式|进入教学|开始教学/, 10000);
  await page.waitForTimeout(3000);
  states.push(await appState('after_enter_teaching'));
  await snap('03_after_enter_teaching');

  for (let i = 0; i < 10; i++) {
    const clicked = await clickTextInMain(/下一步|完成|我知道了|开始体验/, 1500);
    if (!clicked) break;
    await page.waitForTimeout(500);
  }
  states.push(await appState('after_guide_steps'));
  await snap('04_after_guide_steps');

  // The primary user path can use the prominent next action instead of guessing a nav target.
  await clickTextInMain(/进入数据准备|数据准备|预处理/, 5000);
  await page.waitForTimeout(2500);
  states.push(await appState('data_prep'));
  await snap('05_data_prep');

  const dataPrepState = states.at(-1);
  add('教学引导结束后仍有教学模式标识', /教学模式/.test(dataPrepState.teachingBanner || dataPrepState.visibleSample), dataPrepState);
  add('教学模式明确声明无需上传', /无需上传/.test(dataPrepState.teachingBanner || dataPrepState.visibleSample), dataPrepState);
  add('教学内置数据语义可见', /教学数据|内置/.test(dataPrepState.visibleSample), dataPrepState);

  const confirm = await getVisibleAction('confirm-plan-inline');
  if (confirm) {
    const disabled = await confirm.evaluate(el => el.disabled || el.getAttribute('aria-disabled') === 'true').catch(() => true);
    if (!disabled) { await confirm.click(); await page.waitForTimeout(2500); }
  }
  states.push(await appState('after_confirm_attempt'));
  await snap('06_after_confirm_attempt');

  await clickTextInMain(/进入分析任务|分析任务|当前可用分析方法/, 5000);
  await page.waitForTimeout(2500);
  states.push(await appState('analysis_view'));
  await snap('07_analysis_view');

  const analysisState = states.at(-1);
  add('教学分析入口中 PSD 可见且可点击', analysisState.runPsdDisabled === false, analysisState);

  const runPsd = await getVisibleAction('run-psd');
  if (runPsd) {
    const disabled = await runPsd.evaluate(el => el.disabled || el.getAttribute('aria-disabled') === 'true').catch(() => true);
    if (!disabled) { await runPsd.click(); await page.waitForTimeout(6000); }
  }
  states.push(await appState('after_run_psd_attempt'));
  await snap('08_after_run_psd_attempt');

  const taskPosts = requests.filter(r => r.method === 'POST' && r.url.includes('/api/tasks'));
  const psdPosts = taskPosts.filter(r => {
    try { return JSON.parse(r.postData || '{}').module_name === 'psd'; } catch { return /"module_name"\s*:\s*"psd"/.test(r.postData || ''); }
  });
  add('点击 PSD 后发起 psd 分析任务请求', psdPosts.length > 0, { psdPosts, taskPosts });
  add('PSD 请求使用教学数据且不触发上传', psdPosts.some(r => {
    try { const j = JSON.parse(r.postData || '{}'); return j.input_file_id === 'eeg_demo_teaching_oddball' && j.project_id === 'proj_demo_learning'; } catch { return false; }
  }) && !requests.some(r => r.method === 'POST' && /\/api\/data\/files|upload/i.test(r.url)), { psdPosts });

} catch (error) {
  add('journey_unexpected_error', false, { message: String(error?.stack || error) });
} finally {
  await browser.close();
}

const pass = checks.every(c => c.pass);
const result = { status: pass ? 'passed' : 'failed', url, executablePath, checks, states, requests, generatedAt: new Date().toISOString() };
await fs.writeFile(path.join(outDir, 'teaching_user_logic_journey.json'), JSON.stringify(result, null, 2), 'utf8');
console.log(JSON.stringify(result, null, 2));
process.exit(pass ? 0 : 1);
