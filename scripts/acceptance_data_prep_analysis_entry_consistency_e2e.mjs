import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";

const require = createRequire(import.meta.url);
const { chromium } = require("../frontend/node_modules/playwright");

const TARGET_URL =
  process.env.QLANALYSER_FRONTEND_URL ||
  "http://127.0.0.1:4174/?customer_demo=login&api=http://127.0.0.1:8001/api";
const OUT_DIR =
  process.env.QLANALYSER_DATA_PREP_ENTRY_E2E_DIR ||
  path.resolve("work/release_evidence/07-full-product-e2e-pdca/13_data_prep_analysis_entry_consistency/05_browser_e2e");
const EVIDENCE_PATH = path.join(OUT_DIR, "data_prep_analysis_entry_consistency_e2e.json");

function check(name, pass, details = {}) {
  return { name, pass: Boolean(pass), details };
}

async function ensureLoggedIn(page) {
  await page.goto(TARGET_URL, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForTimeout(600);
  const loginButton = page.locator("#customerLoginBtn");
  if (await loginButton.isVisible().catch(() => false)) {
    await loginButton.click();
  }
  await page.locator("#appShell, .shell").first().waitFor({ state: "visible", timeout: 30000 });
}

async function viewportNoHorizontalOverflow(page) {
  return page.evaluate(() => {
    const root = document.documentElement;
    const body = document.body;
    return {
      ok: Math.max(root.scrollWidth, body.scrollWidth) <= root.clientWidth + 2,
      scrollWidth: Math.max(root.scrollWidth, body.scrollWidth),
      clientWidth: root.clientWidth,
    };
  });
}

async function rectWithinViewport(page, selector) {
  return page.locator(selector).first().evaluate((node) => {
    const rect = node.getBoundingClientRect();
    return {
      ok: rect.left >= 0 && rect.top >= 0 && rect.right <= window.innerWidth && rect.bottom <= window.innerHeight,
      rect: { left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom, width: rect.width, height: rect.height },
      viewport: { width: window.innerWidth, height: window.innerHeight },
    };
  });
}

async function waitForTeachingStep(page, marker) {
  await page.waitForFunction(
    (text) => document.querySelector("#teachingStepTitle")?.textContent.includes(text),
    marker,
    { timeout: 30000 },
  );
}

async function advanceTeachingTo(page, marker) {
  const nextButton = page.locator('#teachingOverlay [data-teaching-action="next"].primary-btn');
  for (let attempt = 0; attempt < 8; attempt += 1) {
    const currentTitle = await page.locator("#teachingStepTitle").textContent().catch(() => "");
    if (currentTitle.includes(marker)) return;
    await nextButton.click();
    await page.waitForTimeout(700);
  }
  await waitForTeachingStep(page, marker);
}

async function hideTeachingOverlayForValidation(page) {
  await page.evaluate(() => {
    document.querySelector("#teachingOverlay")?.classList.remove("active");
    document.body.classList.remove("teaching-mode-active");
  });
  await page.waitForFunction(() => !document.querySelector("#teachingOverlay")?.classList.contains("active"), null, { timeout: 15000 });
}

async function canvasStats(page) {
  return page.locator("#eegCanvas").evaluate((canvas) => {
    const ctx = canvas.getContext("2d", { willReadFrequently: true });
    const width = canvas.width;
    const height = canvas.height;
    if (!ctx || !width || !height) return { ok: false, width, height, nonWhite: 0, sampled: 0 };
    const image = ctx.getImageData(0, 0, width, height).data;
    let sampled = 0;
    let nonWhite = 0;
    const step = Math.max(4, Math.floor(Math.sqrt((width * height) / 18000)));
    for (let y = 0; y < height; y += step) {
      for (let x = 0; x < width; x += step) {
        const i = (y * width + x) * 4;
        sampled += 1;
        const r = image[i];
        const g = image[i + 1];
        const b = image[i + 2];
        const a = image[i + 3];
        if (a > 0 && (r < 245 || g < 245 || b < 245)) nonWhite += 1;
      }
    }
    return { ok: nonWhite > 80, width, height, nonWhite, sampled };
  });
}

async function waitForWaveform(page) {
  await page.waitForFunction(() => {
    const activeView = document.querySelector(".view.active");
    const empty = document.querySelector("#eegEmpty");
    const canvas = document.querySelector("#eegCanvas");
    const canvasRect = canvas?.getBoundingClientRect?.();
    return Boolean(
      activeView?.id === "analysis" &&
      canvas &&
      empty &&
      canvasRect?.width > 0 &&
      canvasRect?.height > 0 &&
      getComputedStyle(canvas).visibility !== "hidden" &&
      getComputedStyle(empty).display === "none",
    );
  }, null, { timeout: 90000 });
  return canvasStats(page);
}

async function run() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const evidence = {
    script: path.basename(new URL(import.meta.url).pathname),
    target_url: TARGET_URL,
    generated_at: new Date().toISOString(),
    checks: [],
    screenshots: [],
    errors: [],
    status: "running",
  };
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  page.setDefaultTimeout(45000);

  try {
    await ensureLoggedIn(page);

    const normalBody = await page.locator("body").innerText({ timeout: 15000 });
    evidence.checks.push(check("normal_mode_no_demo_project_visible", !normalBody.includes("proj_demo_learning") && !normalBody.includes("teaching_oddball")));
    for (const term of ["预览方法可试用", "可开始准备", "待建立准备方案", "Reference / CSD", "结合临床判断"]) {
      evidence.checks.push(check(`normal_mode_forbidden_copy_absent:${term}`, !normalBody.includes(term)));
    }
    evidence.checks.push(check("desktop_no_horizontal_overflow_initial", (await viewportNoHorizontalOverflow(page)).ok, await viewportNoHorizontalOverflow(page)));

    await page.locator("#teachingModeBtn").click();
    await page.locator(".teaching-overlay.active").waitFor({ state: "visible", timeout: 30000 });
    const teachingDesktop = await rectWithinViewport(page, ".teaching-card");
    evidence.checks.push(check("teaching_card_within_desktop_viewport", teachingDesktop.ok, teachingDesktop));
    const teachingScreenshot = path.join(OUT_DIR, "teaching_overlay_desktop.png");
    await page.screenshot({ path: teachingScreenshot, fullPage: true });
    evidence.screenshots.push(teachingScreenshot);

    await page.setViewportSize({ width: 390, height: 844 });
    await page.waitForTimeout(300);
    const teachingMobile = await rectWithinViewport(page, ".teaching-card");
    evidence.checks.push(check("teaching_card_within_mobile_viewport", teachingMobile.ok, teachingMobile));
    evidence.checks.push(check("mobile_no_horizontal_overflow_teaching", (await viewportNoHorizontalOverflow(page)).ok, await viewportNoHorizontalOverflow(page)));
    const mobileScreenshot = path.join(OUT_DIR, "teaching_overlay_mobile.png");
    await page.screenshot({ path: mobileScreenshot, fullPage: true });
    evidence.screenshots.push(mobileScreenshot);

    await page.setViewportSize({ width: 1440, height: 900 });
    await page.locator('[data-teaching-action="close"]').last().click();
    await page.locator(".teaching-overlay.active").waitFor({ state: "hidden", timeout: 15000 });
    await page.waitForTimeout(500);
    const afterCloseBody = await page.locator("body").innerText();
    evidence.checks.push(check("teaching_close_hides_demo_from_normal_body", !afterCloseBody.includes("proj_demo_learning") && !afterCloseBody.includes("teaching_oddball")));

    await page.locator("#teachingModeBtn").click();
    await page.locator(".teaching-overlay.active").waitFor({ state: "visible", timeout: 30000 });
    await waitForTeachingStep(page, "1/8");
    await advanceTeachingTo(page, "3/8");
    await page.waitForFunction(() => document.querySelector(".view.active")?.id === "analysis", null, { timeout: 15000 });
    await hideTeachingOverlayForValidation(page);
    await page.locator('[data-testid="single-file-preview-panel"]').waitFor({ state: "visible", timeout: 30000 });
    const fileRows = page.locator('[data-file-select]:visible');
    await fileRows.first().waitFor({ state: "visible", timeout: 30000 });
    await fileRows.first().click();
    const waveform = await waitForWaveform(page);
    evidence.checks.push(check("selected_data_draws_nonblank_waveform_canvas", waveform.ok, waveform));
    evidence.checks.push(check("waveform_empty_overlay_hidden", await page.locator("#eegEmpty").evaluate((node) => getComputedStyle(node).display === "none")));
    const waveformScreenshot = path.join(OUT_DIR, "selected_data_waveform.png");
    await hideTeachingOverlayForValidation(page);
    await page.screenshot({ path: waveformScreenshot, fullPage: false });
    evidence.screenshots.push(waveformScreenshot);

    await hideTeachingOverlayForValidation(page);
    await page.locator('[data-real-action="confirm-plan-inline"]:visible').first().scrollIntoViewIfNeeded();
    await page.locator('[data-real-action="confirm-plan-inline"]:visible').first().click();
    await page.waitForTimeout(1500);
    await page.locator('[data-view="workflow"]').first().click();
    await page.locator('[data-testid="analysis-method-scope-panel"]').waitFor({ state: "visible", timeout: 30000 });
    const cardCount = await page.locator('[data-testid="analysis-method-scope-panel"] .ia-method-card').count();
    const oldPanelCount = await page.locator('[data-testid="analysis-method-run-panel"]').count();
    const cardActions = await page.locator('[data-testid="analysis-method-scope-panel"] .ia-method-card').evaluateAll((nodes) =>
      nodes.map((node) => ({ id: node.getAttribute("data-module-id"), action: node.getAttribute("data-real-action"), disabled: node.disabled, title: node.getAttribute("title") || "" })),
    );
    evidence.checks.push(check("only_card_method_entries_visible", cardCount === 8 && oldPanelCount === 0, { cardCount, oldPanelCount }));
    evidence.checks.push(check("method_cards_have_actions", cardActions.length === 8 && cardActions.every((item) => item.action), { cardActions }));
    evidence.checks.push(check("method_cards_enabled_after_data_preparation_confirmation", cardActions.length === 8 && cardActions.every((item) => !item.disabled), { cardActions }));
    evidence.checks.push(check("analysis_page_no_horizontal_overflow", (await viewportNoHorizontalOverflow(page)).ok, await viewportNoHorizontalOverflow(page)));
    const cardsScreenshot = path.join(OUT_DIR, "analysis_method_cards.png");
    await page.screenshot({ path: cardsScreenshot, fullPage: true });
    evidence.screenshots.push(cardsScreenshot);
  } catch (error) {
    evidence.errors.push(error.stack || error.message);
  } finally {
    evidence.status = evidence.errors.length === 0 && evidence.checks.every((item) => item.pass) ? "passed" : "failed";
    fs.writeFileSync(EVIDENCE_PATH, `${JSON.stringify(evidence, null, 2)}\n`, "utf8");
    await browser.close();
  }
  console.log(JSON.stringify(evidence, null, 2));
  if (evidence.status !== "passed") process.exit(1);
}

run().catch((error) => {
  console.error(error.stack || error.message);
  process.exit(1);
});
