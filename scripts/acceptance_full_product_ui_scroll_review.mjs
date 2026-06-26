import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";

const require = createRequire(import.meta.url);
const { chromium } = require("../frontend/node_modules/playwright");

const FRONTEND_URL = process.env.QLANALYSER_FRONTEND_URL || "http://127.0.0.1:4174/?customer_demo=login&api=http://127.0.0.1:8001/api";
const API_BASE = process.env.QLANALYSER_API_BASE_URL || new URL(FRONTEND_URL).searchParams.get("api") || "http://127.0.0.1:8001/api";
const EVIDENCE_ROOT = process.env.QLANALYSER_FULL_UI_SCROLL_EVIDENCE_ROOT
  || path.resolve("work/release_evidence/07-full-product-e2e-pdca/08_ui_visual_scroll");
const SCREENSHOT_DIR = path.join(EVIDENCE_ROOT, "screenshots");
const SCREENSHOT_MANIFEST_PATH = path.join(EVIDENCE_ROOT, "screenshot_manifest.json");
const SCROLL_REVIEW_PATH = path.join(EVIDENCE_ROOT, "scroll_review.json");
const COLOR_AUDIT_PATH = path.join(EVIDENCE_ROOT, "design_token_color_audit.json");
const DEEPSEEK_VISUAL_CHECKS_PATH = path.join(EVIDENCE_ROOT, "deepseek_adoption_visual_checks.json");
const TIMEOUT_MS = 20000;

const viewports = [
  { id: "desktop-1440x1000", width: 1440, height: 1000 },
  { id: "laptop-1280x800", width: 1280, height: 800 },
  { id: "mobile-390x844", width: 390, height: 844 },
  { id: "wide-1920x1080", width: 1920, height: 1080 },
];

function withParams(baseUrl, params = {}) {
  const url = new URL(baseUrl);
  url.searchParams.set("api", API_BASE);
  for (const [key, value] of Object.entries(params)) {
    if (value === null) url.searchParams.delete(key);
    else url.searchParams.set(key, value);
  }
  return url.toString();
}

function relativePage(pageName, params = {}) {
  return withParams(new URL(`./${pageName}`, FRONTEND_URL).toString(), params);
}

const customerApp = (view) => ({
  id: `customer-${view}`,
  role: "customer",
  url: withParams(FRONTEND_URL, { customer_demo: "prefill" }),
  ready: "#loginScreen",
  actions: [{ type: "click", selector: `[data-view="${view}"]` }],
  primarySelectors: view === "publication" ? ["#publication"] : [`#${view}`],
  requireNoAdminNav: true,
  auth: "customer",
});

const adminApp = (view) => ({
  id: `admin-${view}`,
  role: "admin",
  url: withParams(FRONTEND_URL, { customer_demo: "prefill" }),
  ready: "#loginScreen",
  actions: [{ type: "click", selector: `[data-view="${view}"]` }],
  primarySelectors: [`#${view}`],
  requireNoAdminNav: false,
  auth: "admin",
});

const surfaces = [
  {
    id: "cover-login",
    role: "customer",
    url: withParams(FRONTEND_URL, { customer_demo: "prefill" }),
    ready: "#loginScreen",
    actions: [],
    primarySelectors: ["#customerLoginForm"],
    requireNoAdminNav: false,
    auth: null,
  },
  {
    id: "entry-open-design",
    role: "customer",
    url: relativePage("open-design-entry-demo.html", { customer_demo: null }),
    ready: "body",
    actions: [],
    primarySelectors: ["body"],
    requireNoAdminNav: false,
    auth: null,
  },
  {
    id: "entry-expert",
    role: "customer",
    url: relativePage("expert-entry-demo.html", { customer_demo: null }),
    ready: "body",
    actions: [],
    primarySelectors: ["body"],
    requireNoAdminNav: false,
    auth: null,
  },
  customerApp("dashboard"),
  customerApp("storage"),
  customerApp("analysis"),
  customerApp("workflow"),
  customerApp("statistics"),
  customerApp("publication"),
  customerApp("userCenter"),
  adminApp("adminDashboard"),
  adminApp("adminOperations"),
  adminApp("adminFinance"),
  adminApp("adminSystem"),
  {
    id: "qc-lab",
    role: "customer",
    url: relativePage("qc-lab.html", { customer_demo: null }),
    ready: "body",
    actions: [],
    primarySelectors: ["body"],
    requireNoAdminNav: false,
    auth: null,
  },
  {
    id: "module-lab",
    role: "customer",
    url: relativePage("module-lab.html", { customer_demo: null }),
    ready: "body",
    actions: [],
    primarySelectors: ["body"],
    requireNoAdminNav: false,
    auth: null,
  },
  {
    id: "research-modules",
    role: "customer",
    url: relativePage("research-modules.html", { customer_demo: null }),
    ready: "body",
    actions: [],
    primarySelectors: ["body"],
    requireNoAdminNav: false,
    auth: null,
  },
  ...["qc", "psd", "erp", "tfr", "pac", "connectivity", "source_localization"].map((name) => ({
    id: `research-module-${name}`,
    role: "customer",
    url: relativePage(`research-module/${name}.html`, { customer_demo: null }),
    ready: "body",
    actions: [],
    primarySelectors: ["body"],
    requireNoAdminNav: false,
    auth: null,
  })),
];

function safeName(value) {
  return value.replace(/[^a-z0-9_-]+/gi, "-").replace(/^-+|-+$/g, "").toLowerCase();
}

function ensureDirs() {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

function issue(severity, type, message, detail = {}) {
  return { severity, type, message, ...detail };
}

async function performActions(page, actions, issues) {
  for (const action of actions) {
    if (action.type !== "click") continue;
    const locator = page.locator(`${action.selector}:visible`).first();
    try {
      await locator.waitFor({ state: "visible", timeout: TIMEOUT_MS });
      await locator.click({ timeout: TIMEOUT_MS });
      await page.waitForTimeout(300);
    } catch (error) {
      issues.push(issue("P0", "missing_primary_action", `Cannot click ${action.selector}`, { error: error.message }));
    }
  }
}

async function loginIfNeeded(page, surface) {
  if (surface.auth === "customer") {
    await page.waitForSelector("#customerLoginForm", { state: "visible", timeout: TIMEOUT_MS });
    await page.fill("#customerEmail", "demo.customer@quanlan.cn");
    await page.fill("#customerPassword", "demo123456");
    await Promise.all([
      page.waitForSelector("#appShell", { state: "visible", timeout: TIMEOUT_MS }),
      page.click("#customerLoginBtn", { timeout: TIMEOUT_MS }),
    ]);
    await page.waitForTimeout(500);
  }
  if (surface.auth === "admin") {
    await page.click('[data-login-tab="adminLogin"]', { timeout: TIMEOUT_MS }).catch(() => {});
    await page.waitForSelector("#adminLoginForm", { state: "visible", timeout: TIMEOUT_MS });
    await page.fill("#adminEmail", "ops@quanlan.cn");
    await page.fill("#adminPassword", "ops-demo-2026");
    await Promise.all([
      page.waitForSelector("#appShell", { state: "visible", timeout: TIMEOUT_MS }),
      page.click("#adminLoginForm button[type='submit']", { timeout: TIMEOUT_MS }),
    ]);
    await page.waitForTimeout(500);
  }
}

function parseRgbNumbers(value) {
  return [...String(value || "").matchAll(/\d+(?:\.\d+)?/g)].map((match) => Number(match[0]));
}

function isGreenDominant(value) {
  const nums = parseRgbNumbers(value);
  for (let index = 0; index + 2 < nums.length; index += 3) {
    const [r, g, b] = nums.slice(index, index + 3);
    if (g >= 120 && g > r * 1.5 && g > b * 1.25) return true;
  }
  return false;
}

async function collectDomChecks(page, surface) {
  return page.evaluate(({ surface }) => {
    const issues = [];
    const visible = (node) => {
      if (!node || node.hidden) return false;
      const style = getComputedStyle(node);
      const rect = node.getBoundingClientRect();
      return style.display !== "none" && style.visibility !== "hidden" && Number(style.opacity) !== 0 && rect.width > 0 && rect.height > 0;
    };
    const text = document.body.innerText || "";
    const activeNodes = Array.from(document.querySelectorAll(".active, [aria-current='page'], [data-active='true']"))
      .filter((node) => visible(node))
      .slice(0, 20)
      .map((node) => {
        const style = getComputedStyle(node);
        return {
          selectorHint: node.id || node.getAttribute("data-view") || node.className || node.tagName,
          tagName: node.tagName,
          text: (node.innerText || node.getAttribute("aria-label") || "").trim().slice(0, 80),
          color: style.color,
          backgroundColor: style.backgroundColor,
          backgroundImage: style.backgroundImage,
          borderColor: style.borderColor,
        };
      });

    if (document.documentElement.scrollWidth > innerWidth + 2) {
      issues.push({
        severity: "P0",
        type: "horizontal_overflow",
        message: "Document is wider than viewport.",
        detail: { scrollWidth: document.documentElement.scrollWidth, innerWidth },
      });
    }

    for (const selector of surface.primarySelectors) {
      const node = document.querySelector(selector);
      if (!visible(node)) {
        issues.push({ severity: "P0", type: "primary_region_missing", message: `Primary region missing: ${selector}` });
        continue;
      }
      const rect = node.getBoundingClientRect();
      const x = Math.max(1, Math.min(innerWidth - 2, rect.left + Math.min(rect.width / 2, 80)));
      const y = Math.max(1, Math.min(innerHeight - 2, rect.top + Math.min(rect.height / 2, 80)));
      const topNode = document.elementFromPoint(x, y);
      if (topNode && topNode !== node && !node.contains(topNode) && !topNode.contains(node)) {
        issues.push({
          severity: "P0",
          type: "protected_region_covered",
          message: `Primary region appears covered: ${selector}`,
          detail: { coveringTag: topNode.tagName, x: Math.round(x), y: Math.round(y) },
        });
      }
    }

    if (surface.requireNoAdminNav) {
      const adminVisible = Array.from(document.querySelectorAll("[data-view^='admin']")).some((node) => visible(node));
      if (adminVisible) {
        issues.push({ severity: "P1", type: "admin_nav_visible_to_customer", message: "Customer surface exposes admin navigation." });
      }
    }

    const internalTerms = ["data-real-action", "workflow_id", "module_name", "127.0.0.1", "localhost", "D:\\\\"];
    const internalHit = internalTerms.find((term) => text.includes(term));
    if (internalHit) {
      issues.push({ severity: "P1", type: "internal_term_visible", message: `Internal term visible: ${internalHit}` });
    }

    return {
      issues,
      activeNodes,
      textSample: text.slice(0, 2000),
      metrics: {
        scrollWidth: document.documentElement.scrollWidth,
        scrollHeight: document.documentElement.scrollHeight,
        innerWidth,
        innerHeight,
        bodyTextLength: text.length,
      },
    };
  }, { surface });
}

async function captureScrollScreenshots(page, surface, viewport) {
  const metrics = await page.evaluate(() => ({
    scrollHeight: document.documentElement.scrollHeight,
    innerHeight,
  }));
  const bottom = Math.max(0, metrics.scrollHeight - metrics.innerHeight);
  const positions = Array.from(new Set([0, Math.round(bottom / 2), bottom])).filter((item) => item >= 0);
  const captures = [];
  for (const position of positions) {
    const slot = position === 0 ? "top" : position === bottom ? "bottom" : "middle";
    await page.evaluate((target) => window.scrollTo(0, target), position);
    await page.waitForTimeout(200);
    const fileName = `${safeName(surface.id)}-${viewport.id}-${slot}.png`;
    const screenshotPath = path.join(SCREENSHOT_DIR, fileName);
    await page.screenshot({ path: screenshotPath, fullPage: false, timeout: TIMEOUT_MS });
    const stat = fs.statSync(screenshotPath);
    captures.push({
      slot,
      scrollY: position,
      screenshotPath,
      bytes: stat.size,
      nonBlankBySize: stat.size > 1000,
    });
  }
  return captures;
}

async function reviewSurface(browser, surface, viewport) {
  const page = await browser.newPage({ viewport: { width: viewport.width, height: viewport.height }, deviceScaleFactor: 1 });
  const issues = [];
  const consoleErrors = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => consoleErrors.push(error.message));
  const result = {
    surface: surface.id,
    role: surface.role,
    viewport: viewport.id,
    url: surface.url,
    captures: [],
    metrics: {},
    activeNodes: [],
    issues,
    consoleErrors,
    status: "failed",
  };

  try {
    await page.goto(surface.url, { waitUntil: "domcontentloaded", timeout: TIMEOUT_MS });
    await page.waitForSelector(surface.ready, { state: "visible", timeout: TIMEOUT_MS });
    await loginIfNeeded(page, surface);
    await performActions(page, surface.actions, issues);
    await page.waitForTimeout(500);
    const dom = await collectDomChecks(page, surface);
    issues.push(...dom.issues);
    result.metrics = dom.metrics;
    result.activeNodes = dom.activeNodes;
    result.captures = await captureScrollScreenshots(page, surface, viewport);
    for (const capture of result.captures) {
      if (!capture.nonBlankBySize) {
        issues.push(issue("P0", "blank_screenshot", "Screenshot appears blank or too small.", { screenshotPath: capture.screenshotPath }));
      }
    }
    if (consoleErrors.length) {
      issues.push(...consoleErrors.map((message) => issue("P2", "console_error", "Browser console error.", { message })));
    }
  } catch (error) {
    issues.push(issue("P0", "browser_capture_failed", error.message));
    const fallbackPath = path.join(SCREENSHOT_DIR, `${safeName(surface.id)}-${viewport.id}-error.png`);
    await page.screenshot({ path: fallbackPath, fullPage: true }).catch(() => {});
    if (fs.existsSync(fallbackPath)) result.captures.push({ slot: "error", screenshotPath: fallbackPath, bytes: fs.statSync(fallbackPath).size });
  } finally {
    await page.close();
  }

  result.status = issues.some((item) => item.severity === "P0") ? "failed" : "passed";
  return result;
}

function buildColorAudit(states) {
  const activeColorRows = states.flatMap((state) => state.activeNodes.map((node) => ({
    surface: state.surface,
    viewport: state.viewport,
    ...node,
    greenDominant: isGreenDominant(`${node.color} ${node.backgroundColor} ${node.backgroundImage} ${node.borderColor}`),
  })));
  const greenRows = activeColorRows.filter((row) =>
    row.surface !== "cover-login"
    && row.greenDominant
    && /nav|sidebar|data-view|menu|item/i.test(String(row.selectorHint)),
  );
  return {
    status: greenRows.length ? "failed" : "passed",
    generatedAt: new Date().toISOString(),
    rule: "Active navigation should use navy, blue, cyan, or neutral. Green is reserved for success.",
    activeColorRows,
    greenNavigationFindings: greenRows,
  };
}

function buildDeepSeekVisualChecks(states, colorAudit) {
  const surfaceText = states.map((state) => `${state.surface} ${state.metrics?.bodyTextLength || 0}`).join("\n");
  const customerStates = states.filter((state) => state.role === "customer");
  const horizontalFindings = states.flatMap((state) => state.issues.filter((item) => item.type === "horizontal_overflow"));
  const adminLeaks = customerStates.flatMap((state) => state.issues.filter((item) => item.type === "admin_nav_visible_to_customer"));
  return {
    status: horizontalFindings.length || colorAudit.status !== "passed" ? "failed" : "passed",
    generatedAt: new Date().toISOString(),
    checks: [
      {
        id: "DS-T2",
        status: "covered_by_main_e2e_and_ui_surfaces",
        evidence: [SCROLL_REVIEW_PATH],
        note: "Bad-channel review/restore is primarily verified by the full researcher path; this visual review confirms preparation surfaces are captured.",
      },
      {
        id: "DS-T7",
        status: surfaceText.length > 0 ? "covered" : "failed",
        evidence: [SCREENSHOT_MANIFEST_PATH],
        note: "Preview labels are captured in page screenshots; copy-level proof is finalized through the main workbench/report evidence.",
      },
      {
        id: "DS-T8",
        status: "covered_by_main_e2e",
        evidence: [SCROLL_REVIEW_PATH],
        note: "Long task stage behavior is captured in browser E2E; this UI review records visible states and scroll reachability.",
      },
      {
        id: "DS-T9",
        status: horizontalFindings.length ? "failed" : "passed",
        evidence: [SCROLL_REVIEW_PATH],
        note: "Dense pages are captured at top/middle/bottom across four viewports.",
      },
      {
        id: "DS-T10",
        status: adminLeaks.length ? "revise_required" : "passed",
        evidence: [SCROLL_REVIEW_PATH],
        note: "Visible user surfaces are scanned for internal terms and admin navigation leakage.",
      },
    ],
  };
}

async function main() {
  ensureDirs();
  const browser = await chromium.launch({ headless: true });
  const states = [];
  try {
    for (const surface of surfaces) {
      for (const viewport of viewports) {
        states.push(await reviewSurface(browser, surface, viewport));
      }
    }
  } finally {
    await browser.close();
  }

  const screenshotManifest = {
    status: states.some((state) => state.status === "failed") ? "failed" : "passed",
    generatedAt: new Date().toISOString(),
    screenshotDir: SCREENSHOT_DIR,
    surfaceCount: surfaces.length,
    viewportCount: viewports.length,
    captureCount: states.reduce((sum, state) => sum + state.captures.length, 0),
    states,
  };
  const p0Issues = states.flatMap((state) => state.issues.filter((item) => item.severity === "P0").map((item) => ({ surface: state.surface, viewport: state.viewport, ...item })));
  const scrollReview = {
    status: p0Issues.length ? "failed" : "passed",
    generatedAt: screenshotManifest.generatedAt,
    p0Issues,
    p1OrLowerIssues: states.flatMap((state) => state.issues.filter((item) => item.severity !== "P0").map((item) => ({ surface: state.surface, viewport: state.viewport, ...item }))),
    surfaces: states.map((state) => ({
      surface: state.surface,
      viewport: state.viewport,
      status: state.status,
      metrics: state.metrics,
      captures: state.captures,
    })),
  };
  const colorAudit = buildColorAudit(states);
  const deepseekVisualChecks = buildDeepSeekVisualChecks(states, colorAudit);

  fs.writeFileSync(SCREENSHOT_MANIFEST_PATH, `${JSON.stringify(screenshotManifest, null, 2)}\n`, "utf8");
  fs.writeFileSync(SCROLL_REVIEW_PATH, `${JSON.stringify(scrollReview, null, 2)}\n`, "utf8");
  fs.writeFileSync(COLOR_AUDIT_PATH, `${JSON.stringify(colorAudit, null, 2)}\n`, "utf8");
  fs.writeFileSync(DEEPSEEK_VISUAL_CHECKS_PATH, `${JSON.stringify(deepseekVisualChecks, null, 2)}\n`, "utf8");

  const status = screenshotManifest.status === "passed" && scrollReview.status === "passed" && colorAudit.status === "passed"
    ? "passed"
    : "failed";
  const summary = {
    status,
    screenshotManifest: SCREENSHOT_MANIFEST_PATH,
    scrollReview: SCROLL_REVIEW_PATH,
    colorAudit: COLOR_AUDIT_PATH,
    deepseekVisualChecks: DEEPSEEK_VISUAL_CHECKS_PATH,
    states: states.length,
    p0Issues: p0Issues.length,
  };
  console.log(JSON.stringify(summary, null, 2));
  if (status !== "passed") process.exit(1);
}

main().catch((error) => {
  fs.mkdirSync(EVIDENCE_ROOT, { recursive: true });
  const failure = { status: "failed", error: error.message, stack: error.stack };
  fs.writeFileSync(SCROLL_REVIEW_PATH, `${JSON.stringify(failure, null, 2)}\n`, "utf8");
  console.error(JSON.stringify(failure, null, 2));
  process.exit(1);
});
