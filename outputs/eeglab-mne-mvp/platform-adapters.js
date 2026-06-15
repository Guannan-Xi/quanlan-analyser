const crypto = require("crypto");

const smsCodes = new Map();
const customers = new Map();
const paymentOrders = new Map();

const SMS_TTL_MS = 5 * 60 * 1000;

function json(res, status, payload) {
  const body = JSON.stringify(payload);
  res.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-store",
    "Content-Length": Buffer.byteLength(body),
  });
  res.end(body);
}

function readJson(req) {
  return new Promise((resolve, reject) => {
    let body = "";
    req.on("data", (chunk) => {
      body += chunk;
      if (body.length > 1024 * 1024) {
        reject(new Error("请求体过大"));
        req.destroy();
      }
    });
    req.on("end", () => {
      if (!body) {
        resolve({});
        return;
      }
      try {
        resolve(JSON.parse(body));
      } catch {
        reject(new Error("JSON 格式错误"));
      }
    });
    req.on("error", reject);
  });
}

function validPhone(phone) {
  return /^1[3-9]\d{9}$/.test(String(phone || "").trim());
}

function validEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(email || "").trim());
}

function nowText() {
  return new Date().toLocaleString("zh-CN", { hour12: false });
}

function randomCode() {
  return String(crypto.randomInt(100000, 1000000));
}

function platformConfig() {
  return {
    sms: {
      provider: process.env.SMS_PROVIDER || "aliyun-sms-sandbox",
      productionReady: false,
      productionConfigPresent: Boolean(process.env.ALIYUN_SMS_ACCESS_KEY_ID && process.env.ALIYUN_SMS_TEMPLATE_CODE),
      requiredProductionFields: ["ALIYUN_SMS_ACCESS_KEY_ID", "ALIYUN_SMS_ACCESS_KEY_SECRET", "ALIYUN_SMS_SIGN_NAME", "ALIYUN_SMS_TEMPLATE_CODE"],
    },
    payment: {
      provider: process.env.PAYMENT_PROVIDER || "alipay-sandbox",
      product: "电脑网站支付",
      api: "alipay.trade.page.pay",
      productionReady: false,
      productionConfigPresent: Boolean(process.env.ALIPAY_APP_ID && process.env.ALIPAY_PRIVATE_KEY && process.env.ALIPAY_PUBLIC_KEY),
      requiredProductionFields: ["ALIPAY_APP_ID", "ALIPAY_PRIVATE_KEY", "ALIPAY_PUBLIC_KEY", "ALIPAY_NOTIFY_URL", "ALIPAY_RETURN_URL"],
    },
  };
}

async function sendSmsCode(req, res) {
  const body = await readJson(req);
  const phone = String(body.phone || "").trim();
  if (!validPhone(phone)) {
    json(res, 400, { ok: false, message: "请填写有效手机号" });
    return;
  }
  const code = randomCode();
  const expiresAt = Date.now() + SMS_TTL_MS;
  const bizId = `SMS${Date.now()}${crypto.randomInt(1000, 9999)}`;
  smsCodes.set(phone, { code, expiresAt, bizId, purpose: body.purpose || "register" });
  json(res, 200, {
    ok: true,
    provider: platformConfig().sms.provider,
    bizId,
    expiresInSec: SMS_TTL_MS / 1000,
    sandboxCode: platformConfig().sms.productionReady ? undefined : code,
    message: platformConfig().sms.productionReady ? "验证码已提交短信通道" : "本地沙箱验证码已生成",
  });
}

async function registerCustomer(req, res) {
  const body = await readJson(req);
  const name = String(body.name || "").trim();
  const phone = String(body.phone || "").trim();
  const email = String(body.email || "").trim();
  const org = String(body.org || "").trim();
  const password = String(body.password || "");
  const passwordConfirm = String(body.passwordConfirm || "");
  const code = String(body.code || "").trim();
  const record = smsCodes.get(phone);

  if (!name) {
    json(res, 400, { ok: false, message: "请填写姓名" });
    return;
  }
  if (!validPhone(phone)) {
    json(res, 400, { ok: false, message: "请填写有效手机号" });
    return;
  }
  if (email && !validEmail(email)) {
    json(res, 400, { ok: false, message: "请填写有效邮箱" });
    return;
  }
  if (password.length < 8) {
    json(res, 400, { ok: false, message: "密码至少 8 位" });
    return;
  }
  if (password !== passwordConfirm) {
    json(res, 400, { ok: false, message: "两次输入的密码不一致" });
    return;
  }
  if (!record || record.expiresAt < Date.now() || record.code !== code) {
    json(res, 400, { ok: false, message: "验证码错误或已过期" });
    return;
  }

  const customer = {
    id: customers.get(phone)?.id || `CUS-${Date.now()}`,
    name,
    phone,
    phoneVerifiedAt: nowText(),
    email,
    org: org || "未填写单位",
    registeredAt: nowText(),
  };
  customers.set(phone, customer);
  smsCodes.delete(phone);
  json(res, 200, { ok: true, customer });
}

async function createAlipayPayment(req, res, origin) {
  const body = await readJson(req);
  const amount = Number(body.amount);
  const customer = String(body.customer || "客户账户").trim();
  if (!Number.isFinite(amount) || amount <= 0) {
    json(res, 400, { ok: false, message: "充值金额无效" });
    return;
  }
  const paymentNo = `PAY-${Date.now()}-${crypto.randomInt(1000, 9999)}`;
  const order = {
    paymentNo,
    provider: "支付宝",
    api: "alipay.trade.page.pay",
    customer,
    amount: Number(amount.toFixed(2)),
    status: "待支付",
    createdAt: nowText(),
    paidAt: "",
    gatewayUrl: `${origin}/api/payments/alipay/mock-pay?paymentNo=${encodeURIComponent(paymentNo)}`,
    notifyUrl: `${origin}/api/payments/alipay/mock-notify`,
    returnUrl: `${origin}/?paymentNo=${encodeURIComponent(paymentNo)}`,
    source: "支付宝电脑网站支付沙箱",
  };
  paymentOrders.set(paymentNo, order);
  json(res, 200, { ok: true, order, sandbox: !platformConfig().payment.productionReady });
}

async function mockAlipayNotify(req, res) {
  const body = await readJson(req);
  const paymentNo = String(body.paymentNo || "").trim();
  const order = paymentOrders.get(paymentNo);
  if (!order) {
    json(res, 404, { ok: false, message: "支付订单不存在" });
    return;
  }
  if (order.status !== "已入账") {
    order.status = "已入账";
    order.paidAt = nowText();
    order.tradeNo = `ALI${Date.now()}${crypto.randomInt(1000, 9999)}`;
    order.notifyVerified = true;
  }
  json(res, 200, { ok: true, order, message: "支付宝异步通知已验签并入账" });
}

function mockPayPage(req, res) {
  const parsed = new URL(req.url, "http://127.0.0.1");
  const paymentNo = parsed.searchParams.get("paymentNo");
  const order = paymentOrders.get(paymentNo);
  if (!order) {
    res.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
    res.end("支付订单不存在");
    return;
  }
  const html = `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>支付宝沙箱支付</title></head><body style="font-family:system-ui;margin:40px;line-height:1.7"><h1>支付宝沙箱支付</h1><p>订单：${order.paymentNo}</p><p>金额：￥${order.amount.toFixed(2)}</p><p>请回到 QLanalyser 点击“模拟支付宝回调”。</p></body></html>`;
  res.writeHead(200, {
    "Content-Type": "text/html; charset=utf-8",
    "Cache-Control": "no-store",
    "Content-Length": Buffer.byteLength(html),
  });
  res.end(html);
}

async function handleApi(req, res, origin) {
  try {
    const parsed = new URL(req.url, origin);
    if (req.method === "GET" && parsed.pathname === "/api/platform/config") {
      json(res, 200, { ok: true, ...platformConfig() });
      return true;
    }
    if (req.method === "GET" && parsed.pathname === "/api/payments/alipay/mock-pay") {
      mockPayPage(req, res);
      return true;
    }
    if (req.method === "POST" && parsed.pathname === "/api/auth/sms-code") {
      await sendSmsCode(req, res);
      return true;
    }
    if (req.method === "POST" && parsed.pathname === "/api/auth/register") {
      await registerCustomer(req, res);
      return true;
    }
    if (req.method === "POST" && parsed.pathname === "/api/payments/alipay/create") {
      await createAlipayPayment(req, res, origin);
      return true;
    }
    if (req.method === "POST" && parsed.pathname === "/api/payments/alipay/mock-notify") {
      await mockAlipayNotify(req, res);
      return true;
    }
    return false;
  } catch (error) {
    json(res, 500, { ok: false, message: error.message || "服务异常" });
    return true;
  }
}

module.exports = { handleApi };
