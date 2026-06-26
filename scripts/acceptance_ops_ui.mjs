import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";

const require = createRequire(import.meta.url);
const { chromium } = require("../frontend/node_modules/playwright");

const FRONTEND_URL = process.env.QLANALYSER_FRONTEND_URL || "http://127.0.0.1:4174/?api=http://127.0.0.1:8001/api";
const API_BASE = process.env.QLANALYSER_API_URL || "http://127.0.0.1:8001/api";
const EVIDENCE_PATH = process.env.QLANALYSER_OPS_UI_EVIDENCE_PATH || "";

function assert(ok, message, detail = {}) {
  if (!ok) {
    const error = new Error(`${message}: ${JSON.stringify(detail)}`);
    error.detail = detail;
    throw error;
  }
}

function redactAuthRequests(requests) {
  return requests.map((item) => ({
    method: item.method,
    pathname: item.pathname,
    hasBearer: item.authorization.startsWith("Bearer "),
    authorization: item.authorization ? "Bearer <redacted>" : "",
  }));
}

async function api(pathname, options = {}, token = "") {
  const headers = { Accept: "application/json", ...(options.headers || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(`${API_BASE}${pathname}`, {
    ...options,
    headers,
  });
  const text = await response.text();
  let body;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = text;
  }
  assert(response.ok, `API ${pathname} failed`, { status: response.status, body });
  return body;
}

async function run() {
  const suffix = Date.now();
  const email = `ui-${suffix}@example.com`;
  const password = "StrongPass123";
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const consoleErrors = [];
  const protectedRequests = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("request", (request) => {
    const requestUrl = request.url();
    if (!requestUrl.startsWith(API_BASE)) return;
    const pathname = new URL(requestUrl).pathname;
    if (!["/api/billing/recharge", "/api/invoices", "/api/admin/overview"].includes(pathname) && !pathname.includes("/api/admin/invoices/") && !pathname.includes("/api/inbox")) return;
    protectedRequests.push({
      method: request.method(),
      pathname,
      authorization: request.headers().authorization || "",
    });
  });

  const url = new URL(FRONTEND_URL);
  url.searchParams.set("api", API_BASE);
  await page.goto(url.toString(), { waitUntil: "domcontentloaded" });

  await page.click('[data-login-tab="customerRegister"]');
  await page.fill("#registerName", "UI Ops User");
  await page.fill("#registerOrg", "UI Ops Lab");
  await page.fill("#registerEmail", email);
  await page.fill("#registerPassword", password);
  await page.click("#sendCodeBtn");
  await page.waitForFunction(() => document.querySelector("#registerCode")?.value === "000000", null, { timeout: 10000 });
  await page.click('#customerRegisterForm button[type="submit"]');
  await page.waitForSelector("#appShell:not([hidden])", { timeout: 10000 });

  const customer = await page.evaluate(() => JSON.parse(localStorage.getItem("qlanalyser_customer_profile") || "{}"));
  const customerSession = await page.evaluate(() => JSON.parse(localStorage.getItem("qlanalyser_auth_session") || "{}"));
  assert(customer.accountId, "registered customer has backend account id", customer);
  assert(customerSession.token && customerSession.accountId === customer.accountId, "registered customer has bearer token", customerSession);

  await page.click('[data-view="billing"]');
  await page.click('[data-pay-method="wechat_pay"]');
  await page.click('[data-recharge="500"]');
  await page.click("#rechargeBtn");
  await page.waitForFunction(() => Number(document.querySelector("#balanceMain")?.textContent || 0) >= 530, null, { timeout: 10000 });
  assert(
    protectedRequests.some((item) => item.method === "POST" && item.pathname === "/api/billing/recharge" && item.authorization === `Bearer ${customerSession.token}`),
    "browser recharge request sends customer bearer token",
    { protectedRequests: redactAuthRequests(protectedRequests) },
  );

  await page.click('[data-view="invoice"]');
  await page.fill("#invoiceTitleInput", "UI Ops Lab");
  await page.fill("#invoiceTaxInput", "91310000UIOPS2026");
  await page.fill("#invoiceAmountInput", "200");
  await page.fill("#invoiceEmailInput", email);
  await page.click("#invoiceBtn");
  await page.waitForFunction(() => document.querySelector("#invoiceNotice")?.innerText.length > 0, null, { timeout: 10000 });
  assert(
    protectedRequests.some((item) => item.method === "POST" && item.pathname === "/api/invoices" && item.authorization === `Bearer ${customerSession.token}`),
    "browser invoice request sends customer bearer token",
    { protectedRequests: redactAuthRequests(protectedRequests) },
  );
  await page.waitForFunction(() => document.querySelector("#invoiceNotice")?.innerText.includes("沙盒发票申请已提交"), null, { timeout: 10000 });

  const invoices = await api(`/invoices?account_id=${encodeURIComponent(customer.accountId)}`, {}, customerSession.token);
  const invoice = invoices.find((item) => item.invoice_title === "UI Ops Lab");
  assert(invoice?.status === "pending", "frontend-created invoice is pending", { invoices });

  const adminUrl = new URL(FRONTEND_URL);
  adminUrl.searchParams.set("api", API_BASE);
  adminUrl.searchParams.set("admin", "1");
  await page.goto(adminUrl.toString(), { waitUntil: "domcontentloaded" });
  await page.waitForSelector("#appShell:not([hidden])", { timeout: 10000 });
  await page.waitForFunction(() => {
    const session = JSON.parse(localStorage.getItem("qlanalyser_auth_session") || "{}");
    return session.role === "admin" && session.token;
  }, null, { timeout: 10000 });
  const adminSession = await page.evaluate(() => JSON.parse(localStorage.getItem("qlanalyser_auth_session") || "{}"));
  await page.click('[data-view="adminFinance"]');
  await page.waitForFunction(() => document.querySelector("#adminFinanceTable")?.innerText.includes("UI Ops Lab"), null, { timeout: 10000 });

  const overview = await api("/admin/overview", {}, adminSession.token);
  assert(overview.pending_invoices >= 1, "admin overview sees pending invoice", overview);
  assert(
    protectedRequests.some((item) => item.method === "GET" && item.pathname === "/api/admin/overview" && item.authorization === `Bearer ${adminSession.token}`),
    "browser admin overview request sends admin bearer token",
    { protectedRequests: redactAuthRequests(protectedRequests) },
  );

  const invoicePdfPath = path.join(process.cwd(), "work", "release_evidence", "20260620-v01-acceptance", "ui-ops-invoice.pdf");
  fs.mkdirSync(path.dirname(invoicePdfPath), { recursive: true });
  fs.writeFileSync(invoicePdfPath, "%PDF-1.4\n% QLanalyser visible admin invoice acceptance\n");
  await page.waitForSelector(`[data-admin-issue-invoice="${invoice.id}"]`, { timeout: 10000 });
  const adminInvoiceUploadControlVisible = await page.locator(`[data-admin-issue-invoice="${invoice.id}"]`).isVisible();
  assert(adminInvoiceUploadControlVisible, "admin invoice upload control is visible", { invoiceId: invoice.id });
  await page.click(`[data-admin-issue-invoice="${invoice.id}"]`);
  await page.waitForSelector('input[type="file"][accept="application/pdf"]', { state: "attached", timeout: 10000 });
  const issueResponsePromise = page.waitForResponse((response) => response.url().includes(`/api/admin/invoices/${invoice.id}/issue`) && response.request().method() === "POST");
  await page.setInputFiles('input[type="file"][accept="application/pdf"]', invoicePdfPath);
  const issueResponse = await issueResponsePromise;
  assert(issueResponse.ok(), "admin invoice upload control posts issue request", { status: issueResponse.status() });
  const issued = await issueResponse.json();
  assert(issued.status === "issued" && issued.invoice_file_name === "ui-ops-invoice.pdf", "admin issues invoice attachment", issued);
  assert(
    protectedRequests.some((item) => item.method === "POST" && item.pathname === `/api/admin/invoices/${invoice.id}/issue` && item.authorization === `Bearer ${adminSession.token}`),
    "browser/admin invoice issue request sends admin bearer token",
    { protectedRequests: redactAuthRequests(protectedRequests) },
  );

  await page.goto(url.toString(), { waitUntil: "domcontentloaded" });
  await page.evaluate((session) => {
    localStorage.setItem("qlanalyser_auth_session", JSON.stringify(session));
  }, customerSession);
  await page.goto(url.toString(), { waitUntil: "domcontentloaded" });
  await page.waitForSelector("#appShell:not([hidden])", { timeout: 10000 });
  const inboxMessages = await api(`/inbox?account_id=${encodeURIComponent(customer.accountId)}`, {}, customerSession.token);
  const invoiceMessage = inboxMessages.find((item) => item.source_id === invoice.id);
  assert(invoiceMessage, "customer inbox receives issued invoice", { inboxMessages });
  await page.locator('[data-view="inbox"]').click({ force: true });
  await page.waitForSelector(`[data-inbox-download="${invoiceMessage.id}"]`, { timeout: 10000 });
  const attachmentResponsePromise = page.waitForResponse((response) => response.url().includes(`/api/inbox/${invoiceMessage.id}/attachment`) && response.request().method() === "GET", { timeout: 10000 });
  await page.click(`[data-inbox-download="${invoiceMessage.id}"]`);
  const attachmentResponse = await attachmentResponsePromise;
  assert(attachmentResponse.ok(), "browser requests invoice PDF attachment", { status: attachmentResponse.status() });
  const attachmentDirect = await fetch(`${API_BASE}/inbox/${encodeURIComponent(invoiceMessage.id)}/attachment`, {
    headers: { Authorization: `Bearer ${customerSession.token}` },
  });
  const attachmentBytes = Buffer.from(await attachmentDirect.arrayBuffer());
  assert(attachmentDirect.ok && attachmentBytes.subarray(0, 4).toString() === "%PDF", "customer downloads invoice PDF from inbox", { status: attachmentDirect.status, byteLength: attachmentBytes.length });
  assert(consoleErrors.length === 0, "no console errors", { consoleErrors });

  await browser.close();
  const result = {
    status: "passed",
    frontendUrl: url.toString(),
    apiBase: API_BASE,
    accountId: customer.accountId,
    invoiceId: invoice.id,
    adminInvoiceUploadControlVisible,
    issuedInvoiceStatus: issued.status,
    invoiceMessageId: invoiceMessage.id,
    invoiceAttachmentDownloaded: true,
    walletBalanceText: await api(`/billing/wallet?account_id=${encodeURIComponent(customer.accountId)}`, {}, customerSession.token).then((wallet) => wallet.balance_credits),
    adminOverview: overview,
    browserAuthRequests: redactAuthRequests(protectedRequests),
  };
  if (EVIDENCE_PATH) {
    fs.mkdirSync(path.dirname(EVIDENCE_PATH), { recursive: true });
    fs.writeFileSync(EVIDENCE_PATH, `${JSON.stringify(result, null, 2)}\n`, "utf8");
  }
  console.log(JSON.stringify(result, null, 2));
}

run().catch((error) => {
  console.error(error);
  process.exit(1);
});
