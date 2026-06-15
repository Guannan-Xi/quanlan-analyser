const http = require("http");
const { performance } = require("perf_hooks");

const baseUrl = process.env.STRESS_BASE_URL || "http://127.0.0.1:4173";
const concurrency = Number(process.env.STRESS_CONCURRENCY || 80);
const totalRequests = Number(process.env.STRESS_REQUESTS || 800);
const paths = [
  "/?v=stress",
  "/styles.css?v=stress",
  "/app.js?v=stress",
  "/assets/system_teaching_oddball/system_teaching_manifest.json",
  "/assets/system_teaching_oddball/system_visual_oddball_p300_events.tsv",
  "/assets/system_teaching_oddball/system_visual_oddball_p300.edf",
];

function apiPlan(index) {
  const phone = `139${String(26000000 + index).slice(-8)}`;
  const amount = [100, 500, 1000, 5000][index % 4];
  return [
    { path: "/api/platform/config", method: "GET" },
    { path: "/api/auth/sms-code", method: "POST", body: { phone, purpose: "register" } },
    { path: "/api/payments/alipay/create", method: "POST", body: { amount, customer: `stress-${index}` } },
  ][index % 3];
}

function request(pathname, method = "GET", body = null) {
  const startedAt = performance.now();
  return new Promise((resolve) => {
    const payload = body ? Buffer.from(JSON.stringify(body)) : null;
    const url = new URL(`${baseUrl}${pathname}`);
    const options = {
      method,
      hostname: url.hostname,
      port: url.port,
      path: `${url.pathname}${url.search}`,
      headers: payload ? {
        "Content-Type": "application/json",
        "Content-Length": payload.length,
      } : {},
    };
    const req = http.request(options, (res) => {
      let bytes = 0;
      let text = "";
      res.on("data", (chunk) => {
        bytes += chunk.length;
        if (text.length < 4096) text += chunk.toString("utf8");
      });
      res.on("end", () => {
        resolve({
          path: pathname,
          method,
          status: res.statusCode,
          ms: performance.now() - startedAt,
          bytes,
          ok: res.statusCode >= 200 && res.statusCode < 400,
          body: text,
        });
      });
    });
    req.on("error", (error) => {
      resolve({ path: pathname, status: 0, ms: performance.now() - startedAt, bytes: 0, ok: false, error: error.message });
    });
    if (payload) req.write(payload);
    req.end();
  });
}

async function paymentRound(index) {
  const create = await request("/api/payments/alipay/create", "POST", { amount: 100 + (index % 5) * 100, customer: `stress-pay-${index}` });
  let paymentNo = "";
  try {
    paymentNo = JSON.parse(create.body).order.paymentNo;
  } catch {
    return create;
  }
  const notify = await request("/api/payments/alipay/mock-notify", "POST", { paymentNo });
  notify.path = "/api/payments/alipay/create+mock-notify";
  notify.ms += create.ms;
  notify.ok = create.ok && notify.ok;
  notify.bytes += create.bytes;
  return notify;
}

function percentile(values, p) {
  if (!values.length) return 0;
  const index = Math.min(values.length - 1, Math.ceil((p / 100) * values.length) - 1);
  return values[index];
}

async function main() {
  const startedAt = performance.now();
  const results = [];
  let next = 0;
  async function worker() {
    while (next < totalRequests) {
      const index = next;
      next += 1;
      if (index % 9 === 0) {
        results.push(await paymentRound(index));
      } else if (index % 4 === 0) {
        const plan = apiPlan(index);
        results.push(await request(plan.path, plan.method, plan.body));
      } else {
        results.push(await request(paths[index % paths.length]));
      }
    }
  }
  await Promise.all(Array.from({ length: concurrency }, worker));
  const elapsedSec = (performance.now() - startedAt) / 1000;
  const latencies = results.map((item) => item.ms).sort((a, b) => a - b);
  const failures = results.filter((item) => !item.ok);
  const allPaths = [...new Set(results.map((item) => item.path))];
  const byPath = Object.fromEntries(allPaths.map((pathname) => {
    const items = results.filter((item) => item.path === pathname);
    const ok = items.filter((item) => item.ok).length;
    const bytes = items.reduce((sum, item) => sum + item.bytes, 0);
    return [pathname, { requests: items.length, ok, failures: items.length - ok, bytes }];
  }));
  const errorTypes = failures.reduce((acc, item) => {
    const key = item.error || `HTTP ${item.status}`;
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});
  const summary = {
    baseUrl,
    concurrency,
    totalRequests,
    elapsedSec: Number(elapsedSec.toFixed(3)),
    requestsPerSec: Number((results.length / elapsedSec).toFixed(1)),
    failures: failures.length,
    latencyMs: {
      min: Number((latencies[0] || 0).toFixed(1)),
      p50: Number(percentile(latencies, 50).toFixed(1)),
      p90: Number(percentile(latencies, 90).toFixed(1)),
      p95: Number(percentile(latencies, 95).toFixed(1)),
      p99: Number(percentile(latencies, 99).toFixed(1)),
      max: Number((latencies[latencies.length - 1] || 0).toFixed(1)),
    },
    errorTypes,
    byPath,
  };
  console.log(JSON.stringify(summary, null, 2));
  if (failures.length) process.exitCode = 1;
}

main();
