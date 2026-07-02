import fs from "node:fs";
import path from "node:path";
import { chromium } from "./lib/playwright_runtime.mjs";

const edgeCandidates = [
  "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
  "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
];
const edgePath = edgeCandidates.find((item) => fs.existsSync(item));
const root = process.cwd();
const evidenceDir = path.join(root, "work", "release_evidence", "20260702-epilepsy-result-review-v3-gate");
fs.mkdirSync(evidenceDir, { recursive: true });

const baseUrl = process.env.QLANALYSER_FRONTEND_URL || "http://127.0.0.1:4174";
const apiBase = process.env.QLANALYSER_API_BASE || "http://127.0.0.1:8001/api";
const url = `${baseUrl}/?customer_demo=auto&api=${encodeURIComponent(apiBase)}&epilepsy_result_review_v3=1&v=epilepsy-v3-gate#statistics`;

const browser = await chromium.launch({ headless: true, executablePath: edgePath });
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
const consoleErrors = [];
page.on("console", (message) => {
  if (message.type() === "error") consoleErrors.push(message.text());
});
page.on("pageerror", (error) => consoleErrors.push(error.message));

const result = {
  status: "failed",
  url,
  evidenceDir,
  checks: [],
  failures: [],
  consoleErrors,
  snapshots: {},
};

function check(name, passed, details = {}) {
  result.checks.push({ name, passed: Boolean(passed), ...details });
  if (!passed) result.failures.push({ name, ...details });
}

const FORBIDDEN_TERMS = ["诊断", "确诊", "阳性", "阴性", "病灶", "发作概率", "治疗", "分诊", "confirmed epilepsy"];

async function loginIfNeeded() {
  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForTimeout(1500);
  const loginButton = page.locator("button", { hasText: "登录并进入项目" }).first();
  if (await loginButton.count()) {
    await loginButton.click().catch(() => null);
  }
  await page.waitForTimeout(3500);
  await page.waitForSelector('[data-view="statistics"], [data-view="dashboard"]', { timeout: 10000 }).catch(() => null);
}

async function snapshot(name) {
  await page.waitForTimeout(900);
  const data = await page.evaluate(() => {
    const visible = (node) => Boolean(
      node
      && !node.hidden
      && getComputedStyle(node).display !== "none"
      && getComputedStyle(node).visibility !== "hidden"
      && node.getClientRects().length
    );
    const rect = (node) => {
      const box = node?.getBoundingClientRect?.();
      return box ? { width: Math.round(box.width), height: Math.round(box.height) } : null;
    };
    const workspace = document.querySelector('[data-testid="epilepsy-v3-review-workspace"]');
    return {
      hash: location.hash,
      viewTitle: document.querySelector("#viewTitle")?.innerText || "",
      bodyText: document.body.innerText,
      visiblePanels: [...document.querySelectorAll("[data-testid]")].filter(visible).map((node) => node.dataset.testid),
      v3WorkspacePresent: Boolean(workspace),
      v3EventIndexVisible: Boolean(workspace && visible(document.querySelector('[data-testid="v3-event-index"]'))),
      v3ViewerVisible: Boolean(workspace && visible(document.querySelector('[data-testid="v3-evidence-viewer"]'))),
      v3ReviewPanelVisible: Boolean(workspace && visible(document.querySelector('[data-testid="v3-review-panel"]'))),
      v3DeliveryCenterVisible: Boolean(workspace && visible(document.querySelector('[data-testid="v3-delivery-center"]'))),
      v3WorkspaceRect: rect(workspace),
      v3EventItems: [...document.querySelectorAll("[data-v3-event]")].length,
      v3SelectedEventId: document.querySelector("[data-v3-event].selected")?.dataset?.v3Event || null,
      v3ViewButtons: [...document.querySelectorAll("[data-v3-view]")].map((b) => b.innerText.trim()),
      v3FilterButtons: [...document.querySelectorAll("[data-v3-filter]")].map((b) => b.innerText.trim()),
      v3CurrentZipHref: document.querySelector("#epilepsyV3CurrentZip")?.href || "",
      v3AllZipHref: document.getElementById("epilepsyV3AllZip")?.href || "",
      v3AllZipIsInHero: (() => {
        const allZip = document.getElementById("epilepsyV3AllZip");
        if (!allZip) return false;
        const deliveryCenter = allZip.closest('[data-testid="v3-delivery-center"]');
        const panelHead = allZip.closest(".panel-head");
        return !deliveryCenter || Boolean(panelHead);
      })(),
      v3ResearchBoundary: workspace?.innerText?.includes("科研") || false,
      v3NonDiagnostic: (() => {
        const terms = ["诊断", "确诊", "阳性", "阴性", "病灶", "发作概率", "治疗", "分诊", "confirmed epilepsy"];
        return !terms.some((t) => workspace?.innerText?.includes(t));
      })(),
    };
  });
  result.snapshots[name] = {
    ...data,
    bodyText: data.bodyText.slice(0, 3000),
  };
  await page.screenshot({ path: path.join(evidenceDir, `${name}.png`), fullPage: true });
  return data;
}

/* ===== test execution ===== */

await loginIfNeeded();

/* navigate to #statistics (Results) */
await page.locator('[data-view="statistics"]').first().click().catch(() => null);
await page.waitForTimeout(1000);
/* ensure we actually landed on statistics view */
await page.waitForFunction(() => {
  const stats = document.getElementById("statistics");
  return stats && stats.classList.contains("active");
}, { timeout: 8000 }).catch(() => null);
await page.waitForTimeout(800);

/* T1: Feature flag ON — v3 workspace should be visible on #statistics */
const statsDefault = await snapshot("statistics_default");
check("T1 v3 workspace is present on #statistics", statsDefault.v3WorkspacePresent, { url, hash: statsDefault.hash });
check("T1 event index is visible", statsDefault.v3EventIndexVisible);
check("T1 evidence viewer is visible", statsDefault.v3ViewerVisible);
check("T1 review panel is visible", statsDefault.v3ReviewPanelVisible);
check("T1 delivery center is visible", statsDefault.v3DeliveryCenterVisible);
check("T1 event list has items", statsDefault.v3EventItems >= 1, { count: statsDefault.v3EventItems });

/* T2: Event selection works — click a different event if more than 1, else verify single is selected */
{
  const eventCount = statsDefault.v3EventItems;
  if (eventCount > 1) {
    const targetIdx = Math.min(1, eventCount - 1); /* click 2nd event (or last if only 2) */
    await page.locator('[data-v3-event]').nth(targetIdx).click().catch(() => null);
    await page.waitForTimeout(600);
    const afterSelect = await snapshot("after_event_select");
    check("T2 event selection changes selected item", afterSelect.v3SelectedEventId !== statsDefault.v3SelectedEventId, {
      before: statsDefault.v3SelectedEventId,
      after: afterSelect.v3SelectedEventId,
    });
  } else {
    check("T2 single-event task keeps event selected", statsDefault.v3SelectedEventId && statsDefault.v3SelectedEventId.length > 0, {
      selected: statsDefault.v3SelectedEventId,
      note: "only 1 event available — selection change not applicable",
    });
  }
}

/* T3: View switching works — in P0 src includes view name; in P1 live src is evidence endpoint */
if (statsDefault.v3ViewButtons.length > 1) {
  await page.locator('[data-v3-view="overview"]').first().click().catch(() => null);
  await page.waitForTimeout(600);
  const afterView = await snapshot("after_view_switch");
  const imgInfo = await page.evaluate(() => {
    const el = document.getElementById("epilepsyV3MainImage");
    return { src: el?.src || "", alt: el?.alt || "" };
  });
  /* P0: src contains view suffix name; P1: src is evidence endpoint (stable URL) — either is acceptable */
  const viewChanged = imgInfo.src.includes("overview") || imgInfo.src.includes("/evidence");
  check("T3 view switch keeps evidence image available", viewChanged, { src: imgInfo.src.slice(0, 120) });
}

/* T4: Current-event ZIP in review panel, not hero */
check("T4 current-event ZIP href exists", statsDefault.v3CurrentZipHref.length > 0, { href: statsDefault.v3CurrentZipHref.slice(0, 100) });
check("T4 all-event ZIP exists in delivery center", statsDefault.v3AllZipHref.length > 0, { href: statsDefault.v3AllZipHref.slice(0, 100) });
check("T4 all-event ZIP is NOT in hero/top action", !statsDefault.v3AllZipIsInHero);

/* T5: Non-medical wording */
check("T5 research boundary label present", statsDefault.v3ResearchBoundary);
check("T5 no forbidden clinical terms", statsDefault.v3NonDiagnostic, { bodyText: statsDefault.bodyText.slice(0, 500) });

/* T6: Feature flag OFF — v3 workspace should be absent */
const urlOff = `${baseUrl}/?customer_demo=auto&api=${encodeURIComponent(apiBase)}&v=epilepsy-v3-gate#statistics`;
await page.goto(urlOff, { waitUntil: "domcontentloaded", timeout: 30000 });
await page.waitForTimeout(2000);
/* navigate to statistics even without hash */
await page.locator('[data-view="statistics"]').first().click().catch(() => null);
await page.waitForTimeout(1000);
const flagOff = await snapshot("flag_off");
check("T6 v3 workspace absent when flag off", !flagOff.v3WorkspacePresent, { bodyText: flagOff.bodyText.slice(0, 500) });
check("T6 normal results still render", flagOff.bodyText.includes("结果查看"), { bodyText: flagOff.bodyText.slice(0, 800) });

/* T7: Console errors (allow 404 for static event_previews — P0 static assets not yet served) */
const realErrors = consoleErrors.filter((e) => !e.includes("404"));
check("T7 no unexpected console errors", realErrors.length === 0, { consoleErrors: realErrors, totalConsoleErrors: consoleErrors.length, note: "404 for event_previews assets is expected in P0 static prototype" });

/* ===== write result ===== */
result.status = result.failures.length ? "failed" : "passed";
fs.writeFileSync(path.join(evidenceDir, "epilepsy_result_review_v3_gate_result.json"), JSON.stringify(result, null, 2), "utf8");
await browser.close();

if (result.status !== "passed") {
  console.error(JSON.stringify(result, null, 2));
  process.exit(1);
}
console.log(JSON.stringify(result, null, 2));
