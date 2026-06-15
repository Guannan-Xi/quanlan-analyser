const fs = require("fs");
const path = require("path");

const root = __dirname;
const html = fs.readFileSync(path.join(root, "index.html"), "utf8");
const js = fs.readFileSync(path.join(root, "app.js"), "utf8");
const server = fs.readFileSync(path.join(root, "local-static-server.js"), "utf8");
const adapters = fs.readFileSync(path.join(root, "platform-adapters.js"), "utf8");

const failures = [];
const warnings = [];

function stripTags(value) {
  return value.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
}

function attrsOf(tag) {
  return Object.fromEntries([...tag.matchAll(/\s([\w:-]+)(?:="([^"]*)")?/g)].map((match) => [match[1], match[2] || ""]));
}

function hasJsReference(key) {
  const datasetName = key.replace(/^data-/, "").replace(/-([a-z])/g, (_, char) => char.toUpperCase());
  return js.includes(`#${key}`) ||
    js.includes(`[${key}`) ||
    js.includes(`.${key}`) ||
    js.includes(key) ||
    js.includes(`dataset.${datasetName}`);
}

const buttons = [...html.matchAll(/<button\b[^>]*>[\s\S]*?<\/button>/g)].map((match) => {
  const tag = match[0].match(/<button\b[^>]*>/)[0];
  return { html: match[0], attrs: attrsOf(tag), label: stripTags(match[0]) };
});

buttons.forEach((button) => {
  const { attrs, label } = button;
  const dynamic = attrs.id || attrs["data-view"] || attrs["data-view-jump"] || attrs["data-project-action"] ||
    attrs["data-login-tab"] || attrs["data-segment"] || attrs["data-admin-system-action"] || attrs["data-teaching-action"] ||
    attrs["data-preview-download"] || attrs["data-help-topic"] || attrs["data-pay-method"] || attrs["data-recharge"] || attrs.type === "submit";
  if (!dynamic) failures.push(`按钮缺少可审计入口：${label || button.html.slice(0, 80)}`);
  if (attrs.id && !js.includes(`#${attrs.id}`)) failures.push(`按钮 id 未绑定：#${attrs.id}（${label}）`);
  Object.entries(attrs)
    .filter(([key]) => key.startsWith("data-"))
    .forEach(([key]) => {
      if (!hasJsReference(key)) failures.push(`按钮 data 属性未被 JS 使用：${key}（${label}）`);
    });
});

const downloads = [...html.matchAll(/<a\b[^>]*download[^>]*>[\s\S]*?<\/a>/g)].map((match) => {
  const tag = match[0].match(/<a\b[^>]*>/)[0];
  return { attrs: attrsOf(tag), label: stripTags(match[0]) };
});

if (downloads.length) failures.push("页面存在直下 download 链接；交付件必须先预览再下载");

downloads.forEach((link) => {
  const href = link.attrs.href;
  if (!href) {
    failures.push(`下载链接缺少 href：${link.label}`);
    return;
  }
  if (!href.startsWith("./")) {
    warnings.push(`下载链接不是本地资产：${link.label} -> ${href}`);
    return;
  }
  const localPath = path.join(root, href.replace(/^\.\//, ""));
  if (!fs.existsSync(localPath)) failures.push(`下载资产不存在：${link.label} -> ${href}`);
});

[
  ["#adminMetrics", "renderAdminMetrics"],
  ["#adminQueueGrid", "renderAdminQueueGrid"],
  ["#adminCustomerTable", "renderAdminCustomers"],
  ["#adminOrderTable", "renderAdminOrders"],
  ["#projectFileTable", "renderProjectFiles"],
  ["#customerOrderTable", "renderAdminOrders"],
  ["#adminOperationLog", "renderAdminOperationLog"],
  ["#invoiceStatusChecklist", "renderChecklists"],
].forEach(([selector, renderer]) => {
  if (!html.includes(selector.slice(1))) failures.push(`缺少渲染容器：${selector}`);
  if (!js.includes(`function ${renderer}`)) failures.push(`缺少渲染函数：${renderer}`);
});

[
  "handleFileAction",
  "handleAdminSystemAction",
  "handleOrderAction",
  "saveProfileFromForm",
  "submitInvoice",
  "appendAdminTaskFromCustomer",
  "recordOperation",
].forEach((name) => {
  if (!js.includes(`function ${name}`)) failures.push(`缺少行为函数：${name}`);
});

[
  "sendRegisterSmsCode",
  "registerCustomer",
  "createAlipayRecharge",
  "mockAlipayNotify",
  "renderPaymentStatus",
].forEach((name) => {
  if (!js.includes(`function ${name}`)) failures.push(`缺少支付/注册行为函数：${name}`);
});

[
  "/api/auth/sms-code",
  "/api/auth/register",
  "/api/payments/alipay/create",
  "/api/payments/alipay/mock-notify",
].forEach((route) => {
  if (!adapters.includes(route)) failures.push(`缺少本地 API 适配路由：${route}`);
});

if (!server.includes("handleApi")) failures.push("本地服务器未接入 API 适配器");
if (html.includes("微信支付")) failures.push("当前只接入支付宝，不应展示未接入的微信支付入口");
if (!html.includes("registerPhone") || !html.includes("registerSmsCode")) failures.push("注册表单缺少手机号或短信验证码字段");
if (!html.includes("registerPassword") || !html.includes("registerPasswordConfirm")) failures.push("注册表单缺少密码二次确认字段");
if (!js.includes("passwordConfirm") || !adapters.includes("passwordConfirm")) failures.push("前后端注册链路缺少密码二次确认校验");
if (!html.includes("mockAlipayNotifyBtn")) failures.push("支付宝沙箱回调入口缺失");

const result = {
  buttons: buttons.length,
  downloads: downloads.length,
  failures,
  warnings,
};

console.log(JSON.stringify(result, null, 2));
if (failures.length) process.exit(1);
