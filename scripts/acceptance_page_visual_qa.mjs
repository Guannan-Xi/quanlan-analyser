import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";

const require = createRequire(import.meta.url);
const { chromium } = require("../frontend/node_modules/playwright");

const FRONTEND_URL = process.env.QLANALYSER_FRONTEND_URL || "http://127.0.0.1:4174/?api=http://127.0.0.1:8001/api";
const API_BASE = process.env.QLANALYSER_API_URL || new URL(FRONTEND_URL).searchParams.get("api") || "http://127.0.0.1:8001/api";
const EVIDENCE_PATH = process.env.QLANALYSER_PAGE_VISUAL_QA_EVIDENCE_PATH || path.resolve("work/release_evidence/20260620-page-visual-qa/page_visual_qa.json");
const SCREENSHOT_DIR = process.env.QLANALYSER_PAGE_VISUAL_QA_SCREENSHOT_DIR || path.resolve("work/release_evidence/20260620-page-visual-qa/screenshots");
const TIMEOUT_MS = 15000;

const viewports = [
  { name: "desktop", width: 1440, height: 900 },
  { name: "mobile", width: 390, height: 844 },
  { name: "narrow", width: 360, height: 800 },
];

const customerUrl = (mode = "login") => {
  const target = new URL(FRONTEND_URL);
  target.searchParams.set("api", API_BASE);
  if (mode) target.searchParams.set("customer_demo", mode);
  return target.toString();
};

const adminUrl = () => {
  const target = new URL(FRONTEND_URL);
  target.searchParams.set("api", API_BASE);
  target.searchParams.delete("customer_demo");
  target.searchParams.set("admin", "1");
  return target.toString();
};

const labUrl = () => new URL("./module-lab.html", customerUrl(null)).toString();
const qcLabUrl = () => new URL("./qc-lab.html", customerUrl(null)).toString();
const presetAnalysisUrl = () => new URL("./research-modules.html", customerUrl(null)).toString();

const contracts = [
  {
    name: "customer-login",
    pageGoal: "Customer can understand login, registration, and non-diagnostic product boundaries before entering.",
    primaryAction: "进入项目工作台",
    url: customerUrl("prefill"),
    ready: "#loginScreen",
    actions: [],
    mustText: ["QLanalyser Online", "进入项目工作台", "注册", "不提供医疗建议"],
    primarySelectors: ['#customerLoginForm button[type="submit"]'],
    forbiddenOverlapSelectors: [".login-panel", ".login-brand", ".primary-btn.full"],
    businessChecks: ["analysis-boundary", "no-demo-leaks"],
  },
  {
    name: "customer-register-email",
    pageGoal: "Customer can register with an email verification code and see required account fields.",
    primaryAction: "发送验证码",
    url: customerUrl("prefill"),
    ready: "#loginScreen",
    actions: [
      { type: "click", selector: '[data-login-tab="customerRegister"]' },
      { type: "check", selector: 'input[name="registerMode"][value="email"]' },
      { type: "fill", selector: "#registerEmail", value: "demo.customer@example.com" },
    ],
    mustText: ["邮箱验证码", "邮箱", "验证码", "设置密码", "发送验证码"],
    primarySelectors: ["#registerEmail", "#registerCode", "#registerPassword", "#sendCodeBtn", "#customerRegisterForm"],
    forbiddenOverlapSelectors: ["#customerRegisterForm", "#loginMessage"],
    businessChecks: ["no-demo-leaks"],
  },
  {
    name: "customer-register-phone",
    pageGoal: "Customer can register with a phone verification code and see required account fields.",
    primaryAction: "发送验证码",
    url: customerUrl("prefill"),
    ready: "#loginScreen",
    actions: [
      { type: "click", selector: '[data-login-tab="customerRegister"]' },
      { type: "check", selector: 'input[name="registerMode"][value="phone"]' },
      { type: "fill", selector: "#registerPhone", value: "13800000000" },
    ],
    mustText: ["手机验证码", "手机号", "验证码", "设置密码", "发送验证码"],
    primarySelectors: ["#registerPhone", "#registerCode", "#registerPassword", "#sendCodeBtn", "#customerRegisterForm"],
    forbiddenOverlapSelectors: ["#customerRegisterForm", "#loginMessage"],
    businessChecks: ["no-demo-leaks"],
  },
  {
    name: "customer-register-wechat",
    pageGoal: "Customer can choose WeChat sandbox authorization registration without mistaking it for production WeChat auth.",
    primaryAction: "发送验证码",
    url: customerUrl("prefill"),
    ready: "#loginScreen",
    actions: [
      { type: "click", selector: '[data-login-tab="customerRegister"]' },
      { type: "check", selector: 'input[name="registerMode"][value="wechat"]' },
      { type: "click", selector: "#sendCodeBtn" },
    ],
  mustText: ["微信授权注册", "沙盒验证环境", "当前为微信授权沙盒验证环境", "仅模拟界面流程", "不产生真实微信授权"],
    primarySelectors: ["#sendCodeBtn", "#customerRegisterForm"],
    forbiddenOverlapSelectors: ["#customerRegisterForm", "#loginMessage"],
    businessChecks: ["wechat-sandbox", "no-demo-leaks"],
  },
  {
    name: "customer-dashboard",
    pageGoal: "Customer can start the analysis workflow and see research-use boundaries.",
    primaryAction: "开始本次分析流程",
    url: customerUrl("login"),
    ready: "#appShell",
    actions: [{ type: "click", selector: '[data-view="dashboard"]' }],
    mustText: ["项目工作台", "开始本次分析流程", "数据准备", "分析任务", "不提供医疗建议"],
    primarySelectors: ['[data-view="upload"]', "#topEyebrow"],
    forbiddenOverlapSelectors: [".sidebar", ".topbar", "#dashboard"],
    businessChecks: ["analysis-boundary", "no-demo-leaks"],
  },
  {
    name: "customer-billing",
    pageGoal: "Customer can see sandbox payment, simulated recharge, balance, and no-real-funds wording.",
  primaryAction: "沙盒模拟充值",
    url: customerUrl("login"),
    ready: "#appShell",
    actions: [
      { type: "click", selector: '[data-view="billing"]' },
      { type: "click", selector: '[data-pay-method="wechat_pay"]' },
    ],
  mustText: ["沙盒支付与计费", "沙盒模拟充值", "不涉及真实资金", "支付宝", "微信"],
    primarySelectors: ["#rechargeBtn", '[data-recharge="1000"]'],
    forbiddenOverlapSelectors: ["#billing", "#rechargeBtn", ".pay-options"],
    businessChecks: ["payment-sandbox", "no-demo-leaks"],
  },
  {
    name: "customer-invoice",
    pageGoal: "Customer can submit sandbox simulated invoice information and understand the simulated flow.",
  primaryAction: "提交沙盒发票申请",
    url: customerUrl("login"),
    ready: "#appShell",
    actions: [{ type: "click", selector: '[data-view="invoice"]' }],
  mustText: ["沙盒发票申请", "提交模拟申请", "站内通知（模拟）", "发票抬头", "税号"],
    primarySelectors: ["#invoiceBtn", "#invoiceTitleInput", "#invoiceEmailInput"],
    forbiddenOverlapSelectors: ["#invoice", "#invoiceBtn", "#invoiceNotice"],
    businessChecks: ["invoice-sandbox", "no-demo-leaks"],
  },
  {
    name: "customer-inbox-empty",
    pageGoal: "Customer can understand where simulated invoice attachments will appear.",
    primaryAction: "查看发票箱",
    url: customerUrl("login"),
    ready: "#appShell",
    actions: [{ type: "click", selector: '[data-view="inbox"]' }],
  mustText: ["沙盒发票箱", "沙盒发票", "处理完成后"],
    primarySelectors: ["#inboxTable"],
    forbiddenOverlapSelectors: ["#inbox", "#inboxTable"],
    businessChecks: ["invoice-sandbox", "no-demo-leaks"],
  },
  {
    name: "customer-report-download",
    pageGoal: "Customer can find report/download outputs and see delivery package affordances.",
    primaryAction: "下载",
    url: customerUrl("login"),
    ready: "#appShell",
    actions: [{ type: "click", selector: '[data-view="publication"]' }],
    mustText: ["报告下载", "下载"],
    primarySelectors: ["#publication"],
    forbiddenOverlapSelectors: ["#publication"],
    businessChecks: ["no-demo-leaks"],
  },
  {
    name: "qc-data-preparation-lab",
    pageGoal: "Customer can inspect QC data preparation controls, preview state, and plan actions before PSD or ERP.",
    primaryAction: "Confirm plan",
    url: qcLabUrl(),
    ready: "#qcLab",
    actions: [],
    mustText: ["QC 与数据准备", "通道选择", "公共准备", "Refresh waveform", "Save evidence segment", "Confirm plan"],
    primarySelectors: ["#qcLab", ".hero-card", ".hero-actions"],
    forbiddenOverlapSelectors: [".hero", ".hero-actions", ".side-card"],
    businessChecks: ["no-demo-leaks"],
  },
  {
    name: "lab-workbench",
    pageGoal: "User can inspect lab/method workbench with method boundaries.",
    primaryAction: "查看方法配置",
    url: labUrl(),
    ready: "body",
    actions: [],
    mustText: ["QC", "PSD", "ERP"],
    primarySelectors: ["body"],
    forbiddenOverlapSelectors: ["body"],
    businessChecks: ["analysis-boundary", "no-demo-leaks"],
  },
  {
    name: "preset-analysis-library",
    pageGoal: "Customer can inspect preset EEG analysis modules and stable/preview method boundaries.",
    primaryAction: "从 QC 开始体验",
    url: presetAnalysisUrl(),
    ready: "#moduleGrid",
    actions: [],
    mustText: ["分析实验室", "QC", "PSD", "ERP", "TFR", "PAC", "Connectivity", "合成科研测试数据", "不作为临床诊断依据"],
    primarySelectors: [".hero-actions .primary", ".hero-card"],
    forbiddenOverlapSelectors: [".hero-shell", ".hero-actions", ".hero-card"],
    businessChecks: ["no-demo-leaks"],
  },
  {
    name: "admin-overview",
    pageGoal: "Admin can see operations overview after authorized login.",
      primaryAction: "查看管理总览",
    url: adminUrl(),
    ready: "#appShell",
    actions: [{ type: "click", selector: '[data-view="adminDashboard"]' }],
  mustText: ["管理总览", "今日项目", "待处理任务（运营）", "本次沙盒扣费"],
    primarySelectors: ["#adminDashboard"],
    forbiddenOverlapSelectors: ["#adminDashboard", ".sidebar"],
    businessChecks: ["admin-only", "no-demo-leaks"],
  },
  {
    name: "admin-operations",
    pageGoal: "Admin can review task operations, customer task status, and next operational actions.",
    primaryAction: "查看任务运营",
    url: adminUrl(),
    ready: "#appShell",
    actions: [{ type: "click", selector: '[data-view="adminOperations"]' }],
    mustText: ["任务运营", "查看上传", "ERP-P300-2401", "已完成", "任务详情", "待复核"],
    primarySelectors: ["#adminOperations", "#adminOperations .storage-table"],
    forbiddenOverlapSelectors: ["#adminOperations", "#adminOperations .storage-table"],
    businessChecks: ["admin-only", "no-demo-leaks"],
  },
  {
    name: "admin-finance",
    pageGoal: "Admin can inspect sandbox finance and invoice operations.",
    primaryAction: "查看订单开票",
    url: adminUrl(),
    ready: "#appShell",
    actions: [{ type: "click", selector: '[data-view="adminFinance"]' }],
  mustText: ["订单", "开票", "沙盒财务摘要", "沙盒充值入账"],
    primarySelectors: ["#adminFinance", "#adminFinanceTable"],
    forbiddenOverlapSelectors: ["#adminFinance", "#adminFinanceTable"],
    businessChecks: ["admin-only", "invoice-sandbox"],
  },
];

const fail = (type, message, detail = {}) => ({ type, message, ...detail });

function safeName(value) {
  return value.replace(/[^a-z0-9_-]+/gi, "-").replace(/^-+|-+$/g, "").toLowerCase();
}

async function performActions(page, actions) {
  for (const action of actions) {
    if (action.type === "click") {
      await page.locator(action.selector).first().click({ timeout: TIMEOUT_MS });
    } else if (action.type === "check") {
      await page.locator(action.selector).first().check({ timeout: TIMEOUT_MS });
    } else if (action.type === "fill") {
      await page.locator(action.selector).first().fill(action.value, { timeout: TIMEOUT_MS });
    }
    await page.waitForTimeout(250);
  }
}

async function collectHardChecks(page, contract) {
  return page.evaluate(({ contract }) => {
    const issues = [];
    const visible = (el) => {
      if (!el || el.hidden) return false;
      const style = getComputedStyle(el);
      if (style.display === "none" || style.visibility === "hidden" || Number(style.opacity) === 0) return false;
      const rect = el.getBoundingClientRect();
      return rect.width > 0 && rect.height > 0 && rect.bottom >= 0 && rect.right >= 0 && rect.top <= innerHeight && rect.left <= innerWidth;
    };
    const text = document.body.innerText || "";

    if (document.documentElement.scrollWidth > innerWidth + 2) {
      issues.push({ type: "mobile_break", message: "page has horizontal overflow", evidence: { scrollWidth: document.documentElement.scrollWidth, innerWidth } });
    }

    for (const must of contract.mustText) {
      if (!text.includes(must)) {
        issues.push({ type: "unreadable", message: `must-readable text missing: ${must}` });
      }
    }

    for (const selector of contract.primarySelectors) {
      const el = document.querySelector(selector);
      if (!visible(el)) {
        issues.push({ type: "missing_state", message: `primary selector is not visible: ${selector}` });
      }
    }

    const mojibakePatterns = ["鐎", "閻", "锟", "�", "????"];
    const mojibakeHit = mojibakePatterns.find((item) => text.includes(item));
    if (mojibakeHit) {
      issues.push({ type: "unreadable", message: `visible mojibake marker found: ${mojibakeHit}` });
    }

    const banned = ["Demo Customer", "QLanalyser Pilot", "artifacts", "Single-subject EEG report", "Choose File", "No file chosen"];
    const bannedHit = banned.find((item) => text.includes(item));
    if (bannedHit) {
      issues.push({ type: "misleading_business_state", message: `customer-visible internal/demo text found: ${bannedHit}` });
    }

    const hitTargets = Array.from(document.querySelectorAll("button, a, input, select, textarea")).filter((el) => {
      const tag = el.tagName.toLowerCase();
      const type = (el.getAttribute("type") || "").toLowerCase();
      if (tag === "input" && ["checkbox", "radio", "file", "hidden"].includes(type)) return false;
      return visible(el);
    });
    for (const el of hitTargets) {
      const rect = el.getBoundingClientRect();
      const label = (el.innerText || el.getAttribute("aria-label") || el.id || el.className || el.tagName).toString().trim().slice(0, 80);
      if (rect.width < 28 || rect.height < 28) {
        issues.push({ type: "text_overflow", message: "interactive target is too small", evidence: { label, width: Math.round(rect.width), height: Math.round(rect.height) } });
      }
    }

    const overflowCandidates = Array.from(document.querySelectorAll("button span, a span, a small, label span, input, .nav-item span, .panel-head h2, .panel-head p, .notice span, .table-row span, .cost-row span, .cost-row b, .metric strong, .metric small, .login-panel small")).filter((el) => {
      const type = (el.getAttribute("type") || "").toLowerCase();
      if (el.tagName.toLowerCase() === "input" && ["file", "hidden", "checkbox", "radio"].includes(type)) return false;
      return visible(el);
    });
    for (const el of overflowCandidates) {
      const rect = el.getBoundingClientRect();
      const label = (el.innerText || el.value || el.getAttribute("placeholder") || el.tagName).toString().trim().slice(0, 80);
      if (el.scrollWidth > el.clientWidth + 3 && rect.width > 0 && getComputedStyle(el).whiteSpace !== "normal") {
        issues.push({ type: "text_overflow", message: "text may be clipped horizontally", evidence: { label, scrollWidth: el.scrollWidth, clientWidth: el.clientWidth } });
      }
    }

    for (const selector of contract.forbiddenOverlapSelectors) {
      const el = document.querySelector(selector);
      if (!visible(el)) continue;
      const rect = el.getBoundingClientRect();
      const points = [
        [rect.left + rect.width / 2, rect.top + rect.height / 2],
        [rect.left + Math.min(12, rect.width / 2), rect.top + Math.min(12, rect.height / 2)],
      ];
      for (const [x, y] of points) {
        if (x < 0 || y < 0 || x > innerWidth || y > innerHeight) continue;
        const top = document.elementFromPoint(x, y);
        if (top && top !== el && !el.contains(top) && !top.contains(el)) {
          issues.push({ type: "collision", message: `protected region appears covered: ${selector}`, evidence: { covering: top.tagName, x: Math.round(x), y: Math.round(y) } });
          break;
        }
      }
    }

    const requireText = (kind, words) => {
      const missing = words.filter((word) => !text.includes(word));
      if (missing.length) {
        issues.push({ type: "misleading_business_state", message: `${kind} wording missing`, evidence: { missing } });
      }
    };
    if (contract.businessChecks.includes("payment-sandbox")) requireText("payment sandbox", ["沙盒", "模拟", "不涉及真实资金"]);
    if (contract.businessChecks.includes("invoice-sandbox")) requireText("invoice sandbox", ["沙盒", "模拟"]);
    if (contract.businessChecks.includes("wechat-sandbox")) requireText("wechat sandbox", ["微信", "沙盒", "不产生真实微信授权"]);
    if (contract.businessChecks.includes("analysis-boundary")) requireText("analysis boundary", ["科研", "不提供医疗建议"]);
    if (contract.businessChecks.includes("admin-only") && !text.includes("运营") && !text.includes("管理")) {
      issues.push({ type: "misleading_business_state", message: "admin page does not visibly identify operations context" });
    }

    return issues;
  }, { contract });
}

async function captureState(browser, contract, viewport) {
  const page = await browser.newPage({ viewport: { width: viewport.width, height: viewport.height }, deviceScaleFactor: 1 });
  const consoleErrors = [];
  page.on("console", (message) => {
    if (["error"].includes(message.type())) consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => consoleErrors.push(error.message));

  const screenshotPath = path.join(SCREENSHOT_DIR, `${safeName(contract.name)}-${viewport.name}-${viewport.width}x${viewport.height}.png`);
  const result = {
    page: contract.name,
    viewport: viewport.name,
    viewportSize: { width: viewport.width, height: viewport.height },
    screenshotPath,
    pageContract: {
      pageGoal: contract.pageGoal,
      primaryUserAction: contract.primaryAction,
      mustReadable: contract.mustText,
      protectedRegions: contract.forbiddenOverlapSelectors,
      forbiddenOverlaps: contract.forbiddenOverlapSelectors,
      businessStateConsistency: contract.businessChecks,
    },
    pass: false,
    issues: [],
    consoleErrors,
  };

  try {
    await page.goto(contract.url, { waitUntil: "domcontentloaded", timeout: TIMEOUT_MS });
    await page.waitForSelector(contract.ready, { state: "visible", timeout: TIMEOUT_MS });
    await performActions(page, contract.actions);
    await page.waitForLoadState("networkidle", { timeout: TIMEOUT_MS }).catch(() => {});
    await page.screenshot({ path: screenshotPath, fullPage: true });
    result.issues = await collectHardChecks(page, contract);
    if (consoleErrors.length) {
      result.issues.push(...consoleErrors.map((message) => fail("missing_state", "browser console error", { evidence: { message } })));
    }
    result.pass = result.issues.length === 0;
  } catch (error) {
    await page.screenshot({ path: screenshotPath, fullPage: true }).catch(() => {});
    result.issues.push(fail("missing_state", error.message));
  } finally {
    await page.close();
  }
  return result;
}

async function run() {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
  fs.mkdirSync(path.dirname(EVIDENCE_PATH), { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const states = [];
  try {
    for (const contract of contracts) {
      for (const viewport of viewports) {
        states.push(await captureState(browser, contract, viewport));
      }
    }
  } finally {
    await browser.close();
  }

  const failedStates = states.filter((state) => !state.pass);
  const report = {
    status: failedStates.length ? "failed" : "passed",
    targetUrl: FRONTEND_URL,
    apiBase: API_BASE,
    generatedAt: new Date().toISOString(),
    pageVisualQa: {
      pass: failedStates.length === 0,
      pageCount: contracts.length,
      viewportCount: viewports.length,
      screenshotDir: SCREENSHOT_DIR,
      failOutputSchema: {
        pass: "boolean",
        page_state_viewport: "page + viewport",
        issue_type: "text_overflow | collision | unreadable | contrast_low | mobile_break | missing_state | misleading_business_state",
        screenshot_path: "absolute or workspace-relative path",
        evidence: "issue-specific object",
        recommended_action: "fix page, copy, layout, or business state and rerun",
        c0_decision_needed: "true when issue is business/contract ambiguity",
      },
    },
    states,
  };

  fs.writeFileSync(EVIDENCE_PATH, `${JSON.stringify(report, null, 2)}\n`, "utf8");
  console.log(JSON.stringify(report, null, 2));
  if (failedStates.length) process.exit(1);
}

run().catch((error) => {
  const report = { status: "failed", error: error.message, stack: error.stack };
  fs.mkdirSync(path.dirname(EVIDENCE_PATH), { recursive: true });
  fs.writeFileSync(EVIDENCE_PATH, `${JSON.stringify(report, null, 2)}\n`, "utf8");
  console.error(JSON.stringify(report, null, 2));
  process.exit(1);
});
