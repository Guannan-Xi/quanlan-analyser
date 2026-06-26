import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";

const require = createRequire(import.meta.url);
const { chromium } = require("../frontend/node_modules/playwright");

const DEFAULT_URL = "http://127.0.0.1:4174/?customer_demo=login&api=http://127.0.0.1:8001/api";
const TARGET_URL = process.env.QLANALYSER_TARGET_URL || process.env.QLANALYSER_FRONTEND_URL || DEFAULT_URL;
const OUT_DIR = process.env.QLANALYSER_MULTIROLE_REVIEW_DIR || path.resolve("work/release_evidence/multirole_click_review_5rounds");
const EVIDENCE_PATH = path.join(OUT_DIR, "multirole_click_review_5rounds.json");
const CUSTOMER_EMAIL = process.env.QLANALYSER_DEMO_EMAIL || "demo.customer@quanlan.cn";
const CUSTOMER_PASSWORD = process.env.QLANALYSER_DEMO_PASSWORD || "demo123456";
const SAMPLE_FIF = process.env.QLANALYSER_UI_SAMPLE || path.resolve("work/acceptance/ui_with_events_raw.fif");
const REVIEW_EMAIL = `reviewer.${Date.now()}@quanlan.cn`;

const BAD_VISIBLE_TEXT_TOKENS = [
  "??",
  "\uFFFD",
  "待完善",
  "Project CRUD",
  "Data CRUD",
  "Persistence Gate",
  "Acceptance project",
  "CRUD persistence",
  "Help and account recovery",
  "Upload help",
  "Activity log",
  "Verification code is invalid or expired",
  "Existing account:",
  "Forgot password:",
];

const MOJIBAKE_TOKENS = [
  "椤圭洰",
  "鏁版嵁",
  "鍒涘缓",
  "绠＄悊",
  "璇峰厛",
  "銆",
  "锛",
  "鐧",
  "寰",
];

function hasBadVisibleText(text) {
  const value = String(text || "");
  return [...BAD_VISIBLE_TEXT_TOKENS, ...MOJIBAKE_TOKENS].some((token) => value.includes(token));
}

function ensureDir() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
}

function shotPath(name) {
  return path.join(OUT_DIR, `${name}.png`);
}

async function screenshot(page, name) {
  const target = shotPath(name);
  await page.screenshot({ path: target, fullPage: true, timeout: 10000 }).catch(async () => {
    await page.locator("body").screenshot({ path: target, timeout: 10000 });
  });
  return target;
}

async function login(page) {
  await page.addInitScript(() => {
    localStorage.removeItem("qlanalyser_auth_session");
    localStorage.removeItem("qlanalyser_customer_profile");
    sessionStorage.removeItem("qlanalyser_auth_session");
  });
  await page.goto(TARGET_URL, { waitUntil: "domcontentloaded", timeout: 20000 });
  await page.waitForSelector("#customerLoginForm", { state: "visible", timeout: 15000 });
  await page.fill("#customerEmail", CUSTOMER_EMAIL);
  await page.fill("#customerPassword", CUSTOMER_PASSWORD);
  await Promise.all([
    page.waitForSelector("#appShell:not([hidden])", { timeout: 20000 }),
    page.locator("#customerLoginBtn").click(),
  ]);
  await page.waitForTimeout(250);
}

async function applyStepPrep(page, step) {
  if (step.hash) {
    await page.evaluate((hash) => { location.hash = hash; }, step.hash);
    await page.waitForTimeout(250);
  }
  for (const [selector, value] of Object.entries(step.fill || {})) {
    const locator = page.locator(selector).first();
    if (await locator.count()) await locator.fill(String(value));
  }
  for (const selector of step.check || []) {
    const locator = page.locator(selector).first();
    if (await locator.count()) await locator.check({ force: true }).catch(() => {});
  }
  if (step.waitAfterPrep) await page.waitForTimeout(step.waitAfterPrep);
}

async function stateSnapshot(page) {
  return page.evaluate(() => {
    const appShell = document.querySelector("#appShell");
    const loginScreen = document.querySelector("#loginScreen");
    const activeRoot = appShell && !appShell.hidden ? appShell : loginScreen && !loginScreen.hidden ? loginScreen : document.body;
    const text = activeRoot?.innerText || document.body.innerText || "";
    const modal = document.querySelector("#modalBackdrop:not([hidden])");
    return {
      url: location.href,
      hash: location.hash,
      title: document.querySelector("#viewTitle")?.textContent?.trim() || "",
      status: document.querySelector("#realRuntimeStatus")?.textContent?.trim() || "",
      loginMessage: document.querySelector("#loginMessage")?.textContent?.trim() || "",
      segment: document.querySelector("#segmentSummary")?.textContent?.trim() || "",
      toast: document.querySelector("#toast")?.textContent?.trim() || "",
      modalVisible: Boolean(modal),
      modalTitle: modal?.querySelector("#modalTitle")?.textContent?.trim() || "",
      auditCount: Array.isArray(window.qlanalyserUiActionAudit) ? window.qlanalyserUiActionAudit.length : 0,
      lastAudit: Array.isArray(window.qlanalyserUiActionAudit) ? (window.qlanalyserUiActionAudit.at(-1) || null) : null,
      activeView: document.querySelector(".view.active")?.id || "",
      visibleTextSample: text.slice(0, 1200),
    };
  });
}

function changed(before, after) {
  return before.url !== after.url
    || before.hash !== after.hash
    || before.title !== after.title
    || before.status !== after.status
    || before.loginMessage !== after.loginMessage
    || before.segment !== after.segment
    || before.toast !== after.toast
    || before.modalVisible !== after.modalVisible
    || before.modalTitle !== after.modalTitle
    || before.auditCount !== after.auditCount
    || before.activeView !== after.activeView;
}

function visibleTextIssue(text) {
  const value = String(text || "");
  const token = [...BAD_VISIBLE_TEXT_TOKENS, ...MOJIBAKE_TOKENS].find((item) => value.includes(item));
  if (!token) return "";
  const index = Math.max(0, value.indexOf(token));
  return value.slice(index, index + 180);
}

function auditMismatch(lastAudit, expectedAudit) {
  const failures = [];
  for (const [key, expected] of Object.entries(expectedAudit || {})) {
    const actual = lastAudit?.[key];
    if (actual !== expected) {
      failures.push(`${key} expected ${expected}, got ${actual ?? "missing"}`);
    }
  }
  return failures;
}

async function clickAndJudge(page, selector, label, roundName, expectedAudit = {}) {
  const locator = page.locator(selector).first();
  const count = await locator.count();
  if (!count) {
    return { label, selector, verdict: "missing", issue: "selector not found" };
  }
  const visible = await locator.isVisible().catch(() => false);
  if (!visible) {
    return { label, selector, verdict: "hidden", issue: "not visible in current role path" };
  }
  const disabled = await locator.isDisabled().catch(() => false);
  const title = await locator.getAttribute("title").catch(() => "");
  if (disabled) {
    return {
      label,
      selector,
      verdict: title ? "disabled-with-reason" : "disabled-missing-reason",
      disabled: true,
      title: title || "",
    };
  }
  const before = await stateSnapshot(page);
  let downloadPath = "";
  let clickError = "";
  try {
    const downloadPromise = page.waitForEvent("download", { timeout: 1500 }).catch(() => null);
    await locator.click({ timeout: 10000 });
    const download = await downloadPromise;
    if (download) {
      downloadPath = path.join(OUT_DIR, `${roundName}-${download.suggestedFilename()}`);
      await download.saveAs(downloadPath).catch(() => {});
    }
    await page.waitForTimeout(1500);
  } catch (error) {
    clickError = error.message;
  }
  const after = await stateSnapshot(page);
  const hasChange = changed(before, after) || Boolean(downloadPath);
  const auditFailures = auditMismatch(after.lastAudit, expectedAudit);
  return {
    label,
    selector,
    verdict: clickError ? "broken" : auditFailures.length ? "contract-mismatch" : hasChange ? "pass" : "no-op",
    clickError,
    auditFailures,
    before,
    after,
    downloadPath,
  };
}

async function setSampleFileIfPresent(page) {
  if (!fs.existsSync(SAMPLE_FIF)) return false;
  const input = page.locator("#real-eeg-file");
  if ((await input.count()) === 0) return false;
  await input.setInputFiles(SAMPLE_FIF);
  await page.waitForTimeout(250);
  return true;
}

async function runRound(browser, round) {
  const page = await browser.newPage({ viewport: { width: round.width || 1440, height: round.height || 900 }, acceptDownloads: true });
  const pageErrors = [];
  const consoleErrors = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });
  const result = {
    role: round.role,
    focus: round.focus,
    verdict: "running",
    findings: [],
    pageErrors,
    consoleErrors,
    screenshots: {},
  };
  try {
    if (round.skipLogin) {
      await page.addInitScript(() => {
        localStorage.removeItem("qlanalyser_auth_session");
        localStorage.removeItem("qlanalyser_customer_profile");
        sessionStorage.removeItem("qlanalyser_auth_session");
      });
      const authUrl = new URL(TARGET_URL);
      authUrl.searchParams.delete("customer_demo");
      await page.goto(authUrl.toString(), { waitUntil: "domcontentloaded", timeout: 20000 });
      await page.waitForTimeout(350);
    } else {
      await login(page);
    }
    if (round.hash) {
      await page.evaluate((hash) => { location.hash = hash; }, round.hash);
      await page.waitForTimeout(400);
    }
    if (round.prepareFile) {
      result.sampleFileAttached = await setSampleFileIfPresent(page);
    }
    result.screenshots.start = await screenshot(page, `${round.id}-start`);
    for (const step of round.steps) {
      if (step.beforeHash) {
        await page.evaluate((hash) => { location.hash = hash; }, step.beforeHash);
        await page.waitForTimeout(250);
      }
      await applyStepPrep(page, step);
      if (step.attachSampleFile) {
        result.sampleFileAttached = await setSampleFileIfPresent(page);
      }
      result.findings.push(await clickAndJudge(page, step.selector, step.label, round.id, step.expectedAudit || {}));
    }
    result.screenshots.end = await screenshot(page, `${round.id}-end`);
    const finalText = (await stateSnapshot(page)).visibleTextSample;
    result.visibleMojibake = hasBadVisibleText(finalText);
    result.visibleTextFindings = [];
    for (const finding of result.findings) {
      for (const phase of ["before", "after"]) {
        const issueSample = visibleTextIssue(finding?.[phase]?.visibleTextSample);
        if (issueSample) {
          result.visibleTextFindings.push({
            label: finding.label,
            selector: finding.selector,
            phase,
            issue: "visible placeholder or mojibake text",
            sample: issueSample,
          });
        }
      }
    }
    const hardIssues = [
      ...result.findings.filter((item) => ["broken", "no-op", "disabled-missing-reason", "contract-mismatch"].includes(item.verdict)),
      ...result.visibleTextFindings,
    ];
    result.verdict = hardIssues.length || pageErrors.length || result.visibleMojibake ? "revise" : "pass";
    result.hardIssues = hardIssues;
  } catch (error) {
    result.verdict = "block";
    result.error = error.message;
    result.screenshots.error = await screenshot(page, `${round.id}-error`).catch(() => "");
  } finally {
    await page.close();
  }
  return result;
}

const rounds = [
  {
    id: "round00_auth_access",
    role: "review_access_user",
    focus: "login, help, verification-code, registration, and admin entry controls must respond",
    skipLogin: true,
    steps: [
      { selector: "#customerLoginBtn", label: "empty login feedback" },
      { selector: "#forgotPasswordBtn", label: "account recovery help modal" },
      { selector: "#modalCloseBtn", label: "close account help modal" },
      { selector: '[data-login-tab="customerRegister"]', label: "switch to register tab" },
      {
        selector: "#sendCodeBtn",
        label: "send sandbox verification code",
        fill: { "#registerEmail": REVIEW_EMAIL },
      },
      {
        selector: "#customerRegisterForm button[type='submit']",
        label: "submit sandbox registration form",
        fill: {
          "#registerName": "Review User",
          "#registerOrg": "QuanLan Review",
          "#registerEmail": REVIEW_EMAIL,
          "#registerCode": "1234",
          "#registerPassword": "review-demo-2026",
        },
      },
    ],
  },
  {
    id: "round01_beginner",
    role: "beginner_user",
    focus: "first login, page navigation, and empty-state feedback",
    steps: [
      { selector: '[data-view="analysis"]', label: "open data preparation" },
      { selector: '[data-real-action="confirm-plan-inline"]', label: "confirm preparation without uploaded file" },
      { selector: "#submitBtn", label: "submit analysis before preparation" },
      { selector: "#knowledgeBtn", label: "open knowledge modal" },
      { selector: "#modalCloseBtn", label: "close knowledge modal" },
      { selector: "#auditBtn", label: "open audit modal" },
      { selector: "#modalCloseBtn", label: "close audit modal" },
      { selector: '[data-view="dashboard"]', label: "return project workspace" },
    ],
  },
  {
    id: "round02_project_data_manager",
    role: "project_data_manager",
    focus: "project/data CRUD controls must show state or unavailable reason",
    steps: [
      { selector: '[data-real-action="create-project"]', label: "create project" },
      {
        selector: '[data-ia-action="edit-project"]',
        label: "edit project",
        fill: { "#realProjectName": `Review project ${Date.now()}` },
        expectedAudit: { action: "ia:edit-project", verdict: "pass", persistence: "backend_patch" },
      },
      { selector: '[data-ia-action="archive-project"]', label: "archive project", expectedAudit: { action: "ia:archive-project", verdict: "pass", persistence: "backend_archive" } },
      { selector: '[data-ia-action="delete-project"]', label: "delete project guarded", expectedAudit: { action: "ia:delete-project", verdict: "blocked", persistence: "not_mutated" } },
      { selector: '[data-real-action="upload-eeg"]', label: "upload sample data before data CRUD", attachSampleFile: true },
      { selector: '[data-ia-action="rename-data"]', label: "rename data", expectedAudit: { action: "ia:rename-data", verdict: "pass", persistence: "backend_patch" } },
    ],
  },
  {
    id: "round03_preprocessing_reviewer",
    role: "preprocessing_reviewer",
    focus: "data preparation segment/tag/QC buttons must update visible evidence",
    hash: "#analysis",
    prepareFile: true,
    steps: [
      { selector: '[data-ia-action="select-prep-data"]', label: "select data for preparation" },
      { selector: '[data-ia-action="exclude-segment"]', label: "exclude segment" },
      { selector: '[data-ia-action="restore-segment"]', label: "restore segment" },
      { selector: '[data-ia-action="add-annotation"]', label: "add annotation" },
      { selector: '[data-ia-action="edit-annotation"]', label: "edit annotation" },
    ],
  },
  {
    id: "round04_eeg_analyst",
    role: "eeg_analyst",
    focus: "QC/readiness/epoch/report controls must run or block with explicit reason",
    hash: "#analysis",
    prepareFile: true,
    steps: [
      { selector: '[data-real-action="run-qc-preview-inline"]', label: "run QC preview" },
      { selector: '[data-real-action="confirm-plan-inline"]', label: "confirm data preparation" },
      { selector: '[data-real-action="save-epoch-set"]', label: "save epoch set" },
      { selector: '[data-real-action="download-epoch-manifest"]', label: "download epoch manifest" },
      { selector: '[data-real-action="create-report"]', label: "create report before analysis task" },
    ],
  },
  {
    id: "round05_science_boundary_qa",
    role: "science_boundary_qa",
    focus: "method branches, QC-not-analysis boundary, and report/download navigation",
    hash: "#workflow",
    steps: [
      { selector: '[data-view-jump="analysis"]', label: "back to data preparation" },
      { selector: '[data-testid="data-preparation-submit-last"] [data-view-jump="workflow"]', label: "enter analysis task from final prep step", beforeHash: "#analysis" },
      { selector: '[data-view-jump="statistics"]', label: "view results" },
      { selector: '[data-view="publication"]', label: "download reports view" },
      { selector: ".workbench-link", label: "open method workbench" },
    ],
  },
  {
    id: "round06_ops_billing_delivery",
    role: "ops_billing_delivery_reviewer",
    focus: "account center, billing, invoice, security, and logout controls must produce visible feedback",
    steps: [
      { selector: '[data-view="userCenter"]', label: "open account center" },
      { selector: '[data-modal="security"]', label: "open security explanation" },
      { selector: "#modalCloseBtn", label: "close security explanation" },
      { selector: '[data-pay-method="微信支付"]', label: "select sandbox wechat payment" },
      { selector: '[data-recharge="500"]', label: "select sandbox recharge amount" },
      { selector: "#rechargeBtn", label: "submit sandbox recharge" },
      {
        selector: "#invoiceBtn",
        label: "submit sandbox invoice",
        fill: {
          "#invoiceTitleInput": "QuanLan Review Sandbox",
          "#invoiceTaxInput": "91310000MA1EEG2026",
          "#invoiceAmountInput": "5.00",
          "#invoiceEmailInput": "demo.customer@quanlan.cn",
        },
      },
      { selector: "#logoutBtnUserCenter", label: "logout from account center" },
      { selector: "#customerLoginBtn", label: "login feedback after logout" },
    ],
  },
];

async function main() {
  ensureDir();
  const browser = await chromium.launch();
  const evidence = {
    status: "running",
    targetUrl: TARGET_URL,
    generatedAt: new Date().toISOString(),
    policy: "Five-round multi-role UI-only review. User paths are exercised by clicks; API calls are only observed through the app.",
    defaultTestAccount: {
      account: CUSTOMER_EMAIL,
      passwordOrLogin: CUSTOMER_PASSWORD,
      scope: "demo customer, low privilege, local review only",
    },
    rounds: [],
  };
  try {
    for (const round of rounds) {
      evidence.rounds.push(await runRound(browser, round));
    }
    const blocking = evidence.rounds.flatMap((round) =>
      (round.hardIssues || []).map((issue) => ({ role: round.role, focus: round.focus, ...issue })),
    );
    evidence.blockingFindings = blocking;
    evidence.status = blocking.length || evidence.rounds.some((round) => round.verdict === "block") ? "revise" : "passed";
  } finally {
    await browser.close();
    fs.writeFileSync(EVIDENCE_PATH, `${JSON.stringify(evidence, null, 2)}\n`, "utf8");
  }
  console.log(JSON.stringify(evidence, null, 2));
  if (evidence.status !== "passed") process.exit(1);
}

main().catch((error) => {
  ensureDir();
  fs.writeFileSync(EVIDENCE_PATH, `${JSON.stringify({ status: "block", error: error.message }, null, 2)}\n`, "utf8");
  console.error(error);
  process.exit(1);
});
