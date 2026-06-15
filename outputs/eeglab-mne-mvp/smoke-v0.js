const http = require("http");
const { spawn } = require("child_process");
const os = require("os");
const path = require("path");

const baseUrl = process.env.SMOKE_BASE_URL || "http://127.0.0.1:4173/v0.html";
const edgePath = process.env.EDGE_PATH || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const remotePort = Number(process.env.SMOKE_V0_REMOTE_PORT || 9224);

function getJson(url, method = "GET") {
  return new Promise((resolve, reject) => {
    const parsed = new URL(url);
    const req = http.request({
      method,
      hostname: parsed.hostname,
      port: parsed.port,
      path: `${parsed.pathname}${parsed.search}`,
    }, (res) => {
      let body = "";
      res.on("data", (chunk) => { body += chunk; });
      res.on("end", () => {
        try {
          resolve(JSON.parse(body));
        } catch (error) {
          reject(error);
        }
      });
    });
    req.on("error", reject);
    req.end();
  });
}

async function waitForDebugger() {
  const deadline = Date.now() + 10000;
  while (Date.now() < deadline) {
    try {
      const version = await getJson(`http://127.0.0.1:${remotePort}/json/version`);
      if (version.webSocketDebuggerUrl) return version;
    } catch {
      await new Promise((resolve) => setTimeout(resolve, 200));
    }
  }
  throw new Error("Edge remote debugging port did not start");
}

function connectWebSocket(url) {
  return new Promise((resolve, reject) => {
    const parsed = new URL(url);
    const key = Buffer.from(`${Date.now()}-${Math.random()}`).toString("base64");
    const req = http.request({
      hostname: parsed.hostname,
      port: parsed.port,
      path: `${parsed.pathname}${parsed.search}`,
      headers: {
        Connection: "Upgrade",
        Upgrade: "websocket",
        "Sec-WebSocket-Version": "13",
        "Sec-WebSocket-Key": key,
      },
    });
    req.on("upgrade", (_res, socket) => {
      socket.setNoDelay(true);
      resolve(socket);
    });
    req.on("error", reject);
    req.end();
  });
}

function encodeFrame(text) {
  const payload = Buffer.from(text);
  const header = payload.length < 126
    ? Buffer.from([0x81, 0x80 | payload.length])
    : Buffer.from([0x81, 0x80 | 126, payload.length >> 8, payload.length & 255]);
  const mask = Buffer.from([1, 2, 3, 4]);
  const masked = Buffer.alloc(payload.length);
  for (let i = 0; i < payload.length; i += 1) masked[i] = payload[i] ^ mask[i % 4];
  return Buffer.concat([header, mask, masked]);
}

function createCdp(socket) {
  let id = 0;
  let buffer = Buffer.alloc(0);
  const pending = new Map();

  function parseFrames() {
    while (buffer.length >= 2) {
      const lenByte = buffer[1] & 0x7f;
      let offset = 2;
      let length = lenByte;
      if (lenByte === 126) {
        if (buffer.length < 4) return;
        length = buffer.readUInt16BE(2);
        offset = 4;
      }
      const masked = Boolean(buffer[1] & 0x80);
      const maskOffset = masked ? 4 : 0;
      if (buffer.length < offset + maskOffset + length) return;
      let payload = buffer.slice(offset + maskOffset, offset + maskOffset + length);
      if (masked) {
        const mask = buffer.slice(offset, offset + 4);
        payload = Buffer.from(payload.map((byte, index) => byte ^ mask[index % 4]));
      }
      buffer = buffer.slice(offset + maskOffset + length);
      const message = JSON.parse(payload.toString("utf8"));
      if (message.id && pending.has(message.id)) {
        const { resolve, reject } = pending.get(message.id);
        pending.delete(message.id);
        if (message.error) reject(new Error(message.error.message));
        else resolve(message.result);
      }
    }
  }

  socket.on("data", (chunk) => {
    buffer = Buffer.concat([buffer, chunk]);
    parseFrames();
  });
  socket.on("error", () => {});

  function send(method, params = {}) {
    const message = { id: ++id, method, params };
    socket.write(encodeFrame(JSON.stringify(message)));
    return new Promise((resolve, reject) => {
      pending.set(message.id, { resolve, reject });
      setTimeout(() => {
        if (pending.has(message.id)) {
          pending.delete(message.id);
          reject(new Error(`CDP timeout: ${method}`));
        }
      }, 60000);
    });
  }

  return { send };
}

async function main() {
  const userDataDir = path.join(os.tmpdir(), `qlanalyser-v0-edge-${Date.now()}`);
  const edge = spawn(edgePath, [
    `--remote-debugging-port=${remotePort}`,
    `--user-data-dir=${userDataDir}`,
    "--headless=new",
    "--disable-gpu",
    "about:blank",
  ], { stdio: "ignore" });

  try {
    await waitForDebugger();
    const tab = await getJson(`http://127.0.0.1:${remotePort}/json/new?${encodeURIComponent(`${baseUrl}?v=smoke-v0-${Date.now()}`)}`, "PUT");
    const socket = await connectWebSocket(tab.webSocketDebuggerUrl);
    const cdp = createCdp(socket);
    await cdp.send("Runtime.enable");
    await cdp.send("Page.enable");
    await new Promise((resolve) => setTimeout(resolve, 1000));

    const expression = `(${async function smokeV0() {
      const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
      const text = (selector) => document.querySelector(selector)?.textContent || "";
      const fill = (selector, value) => {
        const el = document.querySelector(selector);
        el.focus();
        el.value = value;
        el.dispatchEvent(new InputEvent("input", { bubbles: true, data: value }));
        el.dispatchEvent(new Event("change", { bubbles: true }));
      };
      const waitForText = async (selector, expected) => {
        for (let i = 0; i < 180; i += 1) {
          if (text(selector).includes(expected)) return true;
          await sleep(100);
        }
        throw new Error("missing text " + selector + " -> " + expected);
      };
      const waitFor = async (selector) => {
        for (let i = 0; i < 180; i += 1) {
          const el = document.querySelector(selector);
          if (el) return el;
          await sleep(100);
        }
        throw new Error("missing element " + selector);
      };
      const waitForCondition = async (fn, label) => {
        for (let i = 0; i < 180; i += 1) {
          if (fn()) return true;
          await sleep(100);
        }
        throw new Error("condition failed: " + label);
      };
      await waitFor("#customerEmail");
      await waitForText("#loginMessage", "demo@qlanalyser.local");
      const mode = document.documentElement.dataset.productMode || "";
      const loginHasCover = text("#loginScreen").includes("QLanalyser") && text("#loginScreen").includes("V0 \u5ba2\u6237\u5165\u53e3");
      fill("#customerEmail", "demo@qlanalyser.local");
      fill("#customerPassword", "demo123456");
      document.querySelector("#customerLoginForm").requestSubmit();
      await waitForCondition(() => document.querySelector("#appShell") && !document.querySelector("#appShell").hidden, "customer workspace visible");
      const navText = [...document.querySelectorAll(".nav-item")]
        .filter((item) => !item.hidden && getComputedStyle(item).display !== "none")
        .map((item) => item.textContent)
        .join("");
      const v0HidesBilling = !navText.includes("\u8d26\u6237");
      const v0KeepsCoreNav = navText.includes("\u9879\u76ee") && navText.includes("\u5206\u6790") && navText.includes("\u4ea4\u4ed8") && !navText.includes("\u8bd5\u8dd1");
      document.querySelector("#tutorialBtn").click();
      await waitForText("#projectFileTable", "C64RS_390026040074_260531103644.bdf");
      const beforePreviewDisabled = document.querySelector("#createTaskBtn").disabled;
      const previewButton = [...document.querySelectorAll("#projectFileTable button")]
        .find((button) => button.textContent.includes("\u9884\u89c8"));
      previewButton.click();
      await waitForText("#eegMeta", "\u901a\u9053\uff1a64");
      await waitForText("#eegMeta", "FocusChange 62");
      const afterPreviewEnabled = !document.querySelector("#createTaskBtn").disabled;
      document.querySelector('[data-view="analysis"]').click();
      await waitForText("#moduleRail", "\u5206\u6790\u65b9\u6cd5");
      const methodButtons = [...document.querySelectorAll('#moduleRail [data-rail-kind="method"]')];
      const checkedMethods = methodButtons.filter((button) => button.classList.contains("active"));
      const templateText = text("#templateList");
      document.querySelector('[data-analysis-page="submit"]').click();
      document.querySelector("#createTaskBtn").click();
      await waitForText("#publication", "GFP");
      const figureCount = document.querySelectorAll("#publication .formal-result-figures img").length;
      const deliveryCount = document.querySelectorAll("#publication [data-preview-download]").length;
      const firstSvgButton = [...document.querySelectorAll("#publication [data-preview-download]")]
        .find((button) => button.textContent.includes("SVG"));
      firstSvgButton.click();
      await waitForText("#deliveryPreviewModal", "SVG");
      const svgModal = text("#deliveryPreviewModal");
      document.querySelector("#deliveryPreviewCancel").click();
      await sleep(100);
      const manifestButton = [...document.querySelectorAll("#publication [data-preview-download]")]
        .find((button) => button.textContent.includes("\u590d\u73b0\u8bb0\u5f55"));
      manifestButton.click();
      await waitForText("#deliveryPreviewModal", "\u590d\u73b0\u8bb0\u5f55");
      const manifestModal = text("#deliveryPreviewModal");
      return {
        title: document.title,
        mode,
        loginHasCover,
        navText,
        v0HidesBilling,
        v0KeepsCoreNav,
        fileName: text("#projectFileTable"),
        meta: text("#eegMeta"),
        eventBox: text("#eegMeta"),
        beforePreviewDisabled,
        afterPreviewEnabled,
        routeCount: methodButtons.length,
        checkedRouteCount: checkedMethods.length,
        routeText: methodButtons.map((button) => button.textContent).join("|"),
        templateText,
        deliveryState: text("#publication"),
        figureCount,
        deliveryCount,
        svgModal,
        manifestModal,
      };
    }.toString()})()`;

    const evaluated = await cdp.send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
    if (evaluated.exceptionDetails) {
      throw new Error(evaluated.exceptionDetails.exception?.description || evaluated.exceptionDetails.text || "V0 smoke failed");
    }
    const result = evaluated.result.value;
    console.log(JSON.stringify(result, null, 2));
    const failed = [
      !result.title.includes("V0") && "V0 title missing",
      result.mode !== "v0" && "V0 mode marker missing",
      !result.loginHasCover && "V0 does not preserve original cover/login",
      !result.v0HidesBilling && "V0 should hide billing entry",
      !result.v0KeepsCoreNav && "V0 should keep original project/analysis/delivery navigation",
      !result.fileName.includes("C64RS_390026040074_260531103644.bdf") && "sample file not loaded",
      !result.meta.includes("\u901a\u9053\uff1a64") && "metadata channel count missing",
      !result.meta.includes("1000 Hz") && "metadata sampling rate missing",
      !result.eventBox.includes("FocusChange 62") && "annotation event counts missing",
      !result.beforePreviewDisabled && "run button enabled before preview",
      !result.afterPreviewEnabled && "run button blocked after preview",
      result.routeCount !== 3 && "V0 should expose exactly three analysis method choices",
      result.checkedRouteCount !== 1 && "V0 should keep exactly one active analysis method",
      !result.routeText.includes("ERP/RRP") && "ERP/RRP method missing",
      !result.routeText.includes("PSD") && "PSD method missing",
      !result.routeText.includes("TFR") && "TFR method missing",
      result.templateText.includes("机器学习分类") && "V0 should not expose ML template",
      result.templateText.includes("头皮地形图") && "V0 should not expose topomap template",
      result.templateText.includes("ICA 预处理") && "V0 should not expose ICA template",
      result.templateText.includes("数据浏览与分段") && "V0 should treat data browsing as a workflow step, not analysis template",
      !result.deliveryState.includes("GFP") && "delivery not ready",
      result.figureCount !== 5 && "V0 should render five figures",
      result.deliveryCount < 10 && "V0 delivery list incomplete",
      !result.svgModal.includes("下载文件") && "SVG modal did not open before download",
      !result.manifestModal.includes("复现记录") && "manifest preview did not open before download",
    ].filter(Boolean);
    if (failed.length) {
      console.error(failed.join("\n"));
      process.exitCode = 1;
    }
    socket.end();
  } finally {
    edge.kill();
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
