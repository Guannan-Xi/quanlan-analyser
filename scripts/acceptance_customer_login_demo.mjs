import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";

const require = createRequire(import.meta.url);
const { chromium } = require("../frontend/node_modules/playwright");

const DEFAULT_TARGET_URL = "http://127.0.0.1:4174/?customer_demo=login&api=http://127.0.0.1:8001/api";
const TARGET_URL = process.env.QLANALYSER_TARGET_URL || process.env.QLANALYSER_FRONTEND_URL || DEFAULT_TARGET_URL;
const EVIDENCE_PATH = process.env.QLANALYSER_CUSTOMER_LOGIN_EVIDENCE_PATH || "";
const CUSTOMER_EMAIL = process.env.QLANALYSER_DEMO_EMAIL || "demo.customer@quanlan.cn";
const CUSTOMER_PASSWORD = process.env.QLANALYSER_DEMO_PASSWORD || "demo123456";
const TIMEOUT_MS = Number(process.env.QLANALYSER_UI_TIMEOUT_MS || 30000);
const PROBE_TIMEOUT_MS = Number(process.env.QLANALYSER_PROBE_TIMEOUT_MS || 30000);
const BANNED_VISIBLE_TEXT = [
  "Demo Customer",
  "QLanalyser Pilot",
  "demo.customer@",
  "artifacts",
  "真实数据",
  "生产流程",
  "新手",
  "Choose File",
  "No file chosen",
  "Single-subject EEG report",
  "体验客户",
  "研究工作台",
  "运营入口",
];
const MOJIBAKE_PATTERNS = [
  "瀹㈡埛",
  "椤圭洰",
  "鐮旂┒",
  "鍏ㄦ緶",
  "鏁版嵁",
  "绛夊緟",
  "杩愯",
  "鎶ュ憡",
  "�",
];

const target = new URL(TARGET_URL);
const apiBase = process.env.QLANALYSER_API_URL || target.searchParams.get("api") || "http://127.0.0.1:8001/api";
if (process.env.QLANALYSER_API_URL) {
  target.searchParams.set("api", apiBase);
}
const effectiveTargetUrl = target.toString();
const apiHealthUrl = `${apiBase.replace(/\/$/, "")}/health`;
const report = {
  status: "running",
  targetUrl: effectiveTargetUrl,
  apiHealthUrl,
  checks: [],
  evidence: {},
};

function check(name, ok, detail = {}) {
  const entry = { name, ok: Boolean(ok), ...detail };
  report.checks.push(entry);
  if (!ok) {
    throw new Error(`${name} failed: ${JSON.stringify(detail)}`);
  }
}

async function probeService(label, url, hint) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), PROBE_TIMEOUT_MS);
  try {
    const response = await fetch(url, {
      method: "GET",
      signal: controller.signal,
      cache: "no-store",
    });
    check(`${label} service reachable`, response.ok, {
      url,
      status: response.status,
      hint,
    });
  } catch (error) {
    throw new Error(
      `${label} service is not reachable at ${url}. ${hint} Original error: ${error.message}`,
    );
  } finally {
    clearTimeout(timer);
  }
}

async function textOrEmpty(page, selector) {
  const locator = page.locator(selector);
  if ((await locator.count()) === 0) return "";
  return (await locator.first().innerText()).trim();
}

function bannedHits(text) {
  return BANNED_VISIBLE_TEXT.filter((term) => text.includes(term));
}

function mojibakeHits(text) {
  return MOJIBAKE_PATTERNS.filter((term) => text.includes(term));
}

async function loginWithCustomer(page) {
  await page.addInitScript(() => {
    localStorage.removeItem("qlanalyser_auth_session");
    localStorage.removeItem("qlanalyser_customer_profile");
    sessionStorage.removeItem("qlanalyser_auth_session");
  });

  await page.goto(effectiveTargetUrl, { waitUntil: "domcontentloaded", timeout: TIMEOUT_MS });
  if (await page.locator("#appShell:not([hidden])").isVisible({ timeout: 2000 }).catch(() => false)) {
    return;
  }
  await page.waitForSelector("#customerLoginForm", { state: "visible", timeout: TIMEOUT_MS });

  await page.fill("#customerEmail", CUSTOMER_EMAIL);
  await page.fill("#customerPassword", CUSTOMER_PASSWORD);

  const loginButton = page.locator("#customerLoginBtn");
  const fallbackSubmitButton = page.locator('#customerLoginForm button[type="submit"]');
  const clickableLogin = (await loginButton.count()) > 0 ? loginButton : fallbackSubmitButton;

  await Promise.all([
    page.waitForSelector("#appShell:not([hidden])", { timeout: TIMEOUT_MS }),
    clickableLogin.click(),
  ]);

  await page.waitForFunction(() => {
    const appShell = document.querySelector("#appShell");
    const loginScreen = document.querySelector("#loginScreen");
    return Boolean(appShell && loginScreen && !appShell.hidden && loginScreen.hidden);
  }, null, { timeout: TIMEOUT_MS });
  await page.evaluate(() => window.scrollTo({ top: 0, left: 0, behavior: "auto" }));
  await page.waitForTimeout(50);
}

async function collectWorkspaceEvidence(page) {
  return await page.evaluate(({ bannedTerms, mojibakeTerms }) => {
    const appShell = document.querySelector("#appShell");
    const visibleText = appShell?.innerText || "";
    const rectOf = (selector) => {
      const node = document.querySelector(selector);
      if (!node) return null;
      const rect = node.getBoundingClientRect();
      const style = window.getComputedStyle(node);
      return {
        text: node.innerText || "",
        top: Math.round(rect.top),
        bottom: Math.round(rect.bottom),
        left: Math.round(rect.left),
        right: Math.round(rect.right),
        width: Math.round(rect.width),
        height: Math.round(rect.height),
        visible: style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0,
        inViewport: rect.top >= 0 && rect.left >= 0 && rect.bottom <= window.innerHeight && rect.right <= window.innerWidth,
      };
    };
    return {
      roleLabel: document.querySelector("#roleLabel")?.textContent?.trim() || "",
      viewTitle: document.querySelector("#viewTitle")?.textContent?.trim() || "",
      visibleTextSample: visibleText.slice(0, 700),
      bannedHits: bannedTerms.filter((term) => visibleText.includes(term)),
      mojibakeHits: mojibakeTerms.filter((term) => visibleText.includes(term)),
      nextAction: rectOf(".real-actions .next-action"),
      methodTopLink: rectOf(".workbench-link"),
      filePicker: rectOf(".file-picker-btn"),
    };
  }, { bannedTerms: BANNED_VISIBLE_TEXT, mojibakeTerms: MOJIBAKE_PATTERNS });
}

async function run() {
  await probeService(
    "Frontend",
    effectiveTargetUrl,
    "Start the frontend from frontend/ with: npm run serve",
  );
  await probeService(
    "Backend API",
    apiHealthUrl,
    `Start the backend API for ${apiBase} before running this acceptance script.`,
  );

  const browser = await chromium.launch();
  const page = await browser.newPage();
  const pageErrors = [];
  const consoleErrors = [];

  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });

  try {
    await loginWithCustomer(page);

    const appShellVisible = await page.locator("#appShell").isVisible();
    const loginScreenHidden = await page.locator("#loginScreen").evaluate((node) => node.hidden);
    const desktopEvidence = await collectWorkspaceEvidence(page);
    const { roleLabel, viewTitle } = desktopEvidence;
    const roleEvidence = roleLabel.includes("客户") || /customer/i.test(roleLabel);
    const viewEvidence = viewTitle.includes("项目") || /project|workbench/i.test(viewTitle);
    const leakedInternalText = desktopEvidence.bannedHits.length > 0;

    check("appShell visible after customer login", appShellVisible, { appShellVisible });
    check("loginScreen hidden after customer login", loginScreenHidden, { loginScreenHidden });
    check("roleLabel or viewTitle shows customer workspace evidence", roleEvidence || viewEvidence, {
      roleLabel,
      viewTitle,
    });
    check("customer workspace hides internal demo wording", !leakedInternalText, {
      bannedHits: desktopEvidence.bannedHits,
    });
    check("customer workspace has no mojibake", desktopEvidence.mojibakeHits.length === 0, {
      mojibakeHits: desktopEvidence.mojibakeHits,
    });
    check("desktop has primary next action", Boolean(desktopEvidence.nextAction?.visible), {
      nextAction: desktopEvidence.nextAction,
    });
    check("no page errors during login", pageErrors.length === 0, { pageErrors });

    const mobilePage = await browser.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
    const mobilePageErrors = [];
    const mobileConsoleErrors = [];
    mobilePage.on("pageerror", (error) => mobilePageErrors.push(error.message));
    mobilePage.on("console", (message) => {
      if (message.type() === "error") mobileConsoleErrors.push(message.text());
    });
    let mobileEvidence;
    try {
      await loginWithCustomer(mobilePage);
      mobileEvidence = await collectWorkspaceEvidence(mobilePage);
      check("mobile customer workspace hides internal demo wording", mobileEvidence.bannedHits.length === 0, {
        bannedHits: mobileEvidence.bannedHits,
      });
      check("mobile customer workspace has no mojibake", mobileEvidence.mojibakeHits.length === 0, {
        mojibakeHits: mobileEvidence.mojibakeHits,
      });
      check("mobile primary next action is visible in first viewport", Boolean(mobileEvidence.nextAction?.visible && mobileEvidence.nextAction?.inViewport), {
        nextAction: mobileEvidence.nextAction,
      });
      check("mobile top method-validation shortcut is hidden", !mobileEvidence.methodTopLink?.visible, {
        methodTopLink: mobileEvidence.methodTopLink,
      });
      check("mobile file picker uses localized button", Boolean(mobileEvidence.filePicker?.visible && /选择\s*(EEG|脑电)\s*数据/.test(mobileEvidence.filePicker.text)), {
        filePicker: mobileEvidence.filePicker,
      });
      check("no page errors during mobile login", mobilePageErrors.length === 0, { mobilePageErrors });
    } finally {
      await mobilePage.close();
    }

    report.status = "passed";
    report.evidence = {
      desktop: desktopEvidence,
      mobile: mobileEvidence,
      consoleErrors,
      mobileConsoleErrors,
    };
    if (EVIDENCE_PATH) {
      fs.mkdirSync(path.dirname(EVIDENCE_PATH), { recursive: true });
      fs.writeFileSync(EVIDENCE_PATH, `${JSON.stringify(report, null, 2)}\n`, "utf8");
    }
    console.log(JSON.stringify(report, null, 2));
  } finally {
    await browser.close();
  }
}

run().catch((error) => {
  report.status = "failed";
  report.error = error.message;
  console.error(JSON.stringify(report, null, 2));
  console.error(error.stack || error.message);
  process.exit(1);
});
