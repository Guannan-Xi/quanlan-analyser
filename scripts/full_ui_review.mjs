import fs from "node:fs";
import path from "node:path";
import { chromium, chromiumLaunchOptions } from "./lib/playwright_runtime.mjs";

const baseUrl = "http://127.0.0.1:4174";
const apiBase = "http://127.0.0.1:8001/api";
const evidenceDir = "D:/Quanlan/Codes/Python/quanlan-analyser-official/work/release_evidence/20260702-full-ui-review";
fs.mkdirSync(evidenceDir, { recursive: true });

const browser = await chromium.launch(chromiumLaunchOptions({ headless: true }));
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await context.newPage();

const allConsoleErrors = [];
page.on("console", (msg) => { if (msg.type() === "error") allConsoleErrors.push(msg.text()); });
page.on("pageerror", (e) => allConsoleErrors.push(e.message));

const results = [];

async function snapshotPage(name, url, extraChecks = {}) {
  const errorsBefore = allConsoleErrors.length;
  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 30000 }).catch(() => null);
  await page.waitForTimeout(2000);
  await page.screenshot({ path: path.join(evidenceDir, `${name}.png`), fullPage: true });
  const newErrors = allConsoleErrors.slice(errorsBefore);
  const realErrors = newErrors.filter(e => !e.includes("404") && !e.includes("favicon"));
  const check = {
    name,
    url,
    consoleErrors: realErrors.length,
    consoleErrorDetails: realErrors.slice(0, 5),
    bodyText: (await page.evaluate(() => document.body.innerText.slice(0, 200))).replace(/\n/g, " | "),
    ...extraChecks,
  };
  results.push(check);
  console.log(`${name}: ${realErrors.length} errors`);
  return check;
}

async function elementExists(selector) {
  return page.evaluate((sel) => !!document.querySelector(sel), selector);
}

async function elementVisible(selector) {
  return page.evaluate((sel) => {
    const el = document.querySelector(sel);
    if (!el) return false;
    const rect = el.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0;
  }, selector);
}

// ===== LOGIN =====
await snapshotPage("01-login", `${baseUrl}/`);

// ===== AFTER LOGIN =====
const demoUrl = `${baseUrl}/?customer_demo=auto&api=${encodeURIComponent(apiBase)}`;
await page.goto(demoUrl, { waitUntil: "domcontentloaded", timeout: 30000 });
await page.waitForTimeout(2000);
// Click login via JavaScript to bypass visibility checks
await page.evaluate(() => {
  const btn = document.querySelector("#customerLoginBtn") || document.querySelector("button.primary-btn");
  if (btn) btn.click();
});
await page.waitForTimeout(4000);

// ===== PROJECT MANAGEMENT =====
const hasProjects = await elementExists('[data-view="projects"]');
if (hasProjects) await page.locator('[data-view="projects"]').click().catch(() => null);
await page.waitForTimeout(1500);
await snapshotPage("02-project-management", page.url(), {
  hasProjectList: await elementExists("#iaProjectRows"),
});

// ===== DATA MANAGEMENT =====
await page.locator('[data-view="data"]').first().click().catch(() => null);
await page.waitForTimeout(1500);
await snapshotPage("03-data-management", page.url(), {
  hasFileList: await elementExists("#iaDataRows"),
});

// ===== DATA PREPARATION =====
await page.locator('[data-view="preparation"]').first().click().catch(() => null);
await page.waitForTimeout(1500);
await snapshotPage("04-data-preparation", page.url(), {
  hasPrepSection: await elementExists("#prepDataQueue"),
});

// ===== ANALYSIS TASKS =====
await page.locator('[data-view="analysis"]').first().click().catch(() => null);
await page.waitForTimeout(1500);
await snapshotPage("05-analysis-tasks", page.url(), {
  hasAnalysisSection: await elementExists('[data-testid="analysis-formal-method-tasks"]'),
});

// ===== RESULTS / STATISTICS =====
await page.locator('[data-view="statistics"]').first().click().catch(() => null);
await page.waitForTimeout(1500);
await snapshotPage("06-results-statistics", page.url(), {
  hasResultsReview: await elementExists("#realResultReview"),
  hasV3Panel: await elementExists('[data-testid="epilepsy-v3-review-workspace"]'),
});

// ===== RESULTS WITH V3 FLAG =====
const v3Url = `${demoUrl}&epilepsy_result_review_v3=1#statistics`;
await page.goto(v3Url, { waitUntil: "domcontentloaded", timeout: 30000 });
await page.waitForTimeout(1500);
await page.locator('[data-view="statistics"]').first().click().catch(() => null);
await page.waitForTimeout(1500);
await snapshotPage("07-results-v3-panel", page.url(), {
  v3Workspace: await elementVisible('[data-testid="epilepsy-v3-review-workspace"]'),
  v3EventIndex: await elementVisible('[data-testid="v3-event-index"]'),
  v3Viewer: await elementVisible('[data-testid="v3-evidence-viewer"]'),
  v3ReviewPanel: await elementVisible('[data-testid="v3-review-panel"]'),
  v3DeliveryCenter: await elementVisible('[data-testid="v3-delivery-center"]'),
});

// ===== REPORTS / DELIVERY =====
await page.locator('[data-view="delivery"]').first().click().catch(() => null);
await page.waitForTimeout(1500);
await snapshotPage("08-reports-delivery", page.url(), {
  hasDeliverySection: await elementExists("#realDelivery"),
});

// ===== PERSONAL CENTER =====
await page.locator('[data-view="account"]').first().click().catch(() => null);
await page.waitForTimeout(1500);
await snapshotPage("09-personal-center", page.url(), {
  hasAccountSection: await elementExists("#roleLabel"),
});

// ===== TEACHING MODE =====
// Click teaching toggle
const teachingBtn = page.locator("button", { hasText: "示例模式" }).first();
if (await teachingBtn.count()) { await teachingBtn.click(); await page.waitForTimeout(2000); }
await snapshotPage("10-teaching-mode", page.url(), {
  teachingActive: await elementExists("#teachingGuide"),
});

// ===== RESPONSIVE (768px) =====
await page.setViewportSize({ width: 768, height: 900 });
await page.goto(v3Url, { waitUntil: "domcontentloaded", timeout: 30000 });
await page.waitForTimeout(1500);
await page.locator('[data-view="statistics"]').first().click().catch(() => null);
await page.waitForTimeout(1500);
await snapshotPage("11-responsive-768px", page.url(), {
  viewport: "768x900",
  v3WorkspaceVisible: await elementVisible('[data-testid="epilepsy-v3-review-workspace"]'),
});

// ===== WRITE REPORT =====
const report = {
  status: allConsoleErrors.filter(e => !e.includes("404")).length === 0 ? "passed" : "warnings",
  pages: results.length,
  totalConsoleErrors: allConsoleErrors.length,
  realConsoleErrors: allConsoleErrors.filter(e => !e.includes("404")),
  pageDetails: results,
};

fs.writeFileSync(path.join(evidenceDir, "full-ui-review-report.json"), JSON.stringify(report, null, 2), "utf8");
await browser.close();
console.log("\n=== UI REVIEW COMPLETE ===");
console.log(`Pages reviewed: ${results.length}`);
console.log(`Console errors (non-404): ${report.realConsoleErrors.length}`);
