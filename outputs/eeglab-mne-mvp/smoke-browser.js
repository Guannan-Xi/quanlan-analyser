const http = require("http");
const { spawn } = require("child_process");
const os = require("os");
const path = require("path");

const baseUrl = process.env.SMOKE_BASE_URL || "http://127.0.0.1:4173";
const edgePath = process.env.EDGE_PATH || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const remotePort = Number(process.env.SMOKE_REMOTE_PORT || 9223);

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
      } else if (lenByte === 127) {
        if (buffer.length < 10) return;
        length = Number(buffer.readBigUInt64BE(2));
        offset = 10;
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
      const text = payload.toString("utf8");
      if (!text) continue;
      const message = JSON.parse(text);
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

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function main() {
  const userDataDir = path.join(os.tmpdir(), `qlanalyser-edge-${Date.now()}`);
  const edge = spawn(edgePath, [
    `--remote-debugging-port=${remotePort}`,
    `--user-data-dir=${userDataDir}`,
    "--headless=new",
    "--disable-gpu",
    "about:blank",
  ], { stdio: "ignore" });

  try {
    await waitForDebugger();
    const tab = await getJson(`http://127.0.0.1:${remotePort}/json/new?${encodeURIComponent(`${baseUrl}/?v=smoke-cdp-${Date.now()}`)}`, "PUT");
    const socket = await connectWebSocket(tab.webSocketDebuggerUrl);
    const cdp = createCdp(socket);

    await cdp.send("Runtime.enable");
    await cdp.send("Page.enable");
    await cdp.send("Input.setIgnoreInputEvents", { ignore: false }).catch(() => {});
    await sleep(1200);

    const expression = `(${async function smokeFlow() {
      const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
      const waitFor = async (selector, tries = 120) => {
        for (let i = 0; i < tries; i += 1) {
          const el = document.querySelector(selector);
          if (el) return el;
          await sleep(100);
        }
        throw new Error(`missing element: ${selector}`);
      };
      const waitForText = async (selector, text, tries = 300) => {
        for (let i = 0; i < tries; i += 1) {
          const el = document.querySelector(selector);
          if ((el?.innerText || "").includes(text)) return el;
          await sleep(100);
        }
        throw new Error(`missing text: ${selector} -> ${text}`);
      };
      const waitForVisible = async (selector, tries = 160) => {
        for (let i = 0; i < tries; i += 1) {
          const el = document.querySelector(selector);
          if (el && !el.hidden && getComputedStyle(el).display !== "none") return el;
          await sleep(100);
        }
        throw new Error(`not visible: ${selector}`);
      };
      const fill = async (selector, value) => {
        const el = await waitFor(selector);
        el.focus();
        el.value = value;
        el.dispatchEvent(new InputEvent("input", { bubbles: true, data: value }));
        el.dispatchEvent(new Event("change", { bubbles: true }));
      };
      const click = async (selector) => (await waitFor(selector)).click();
      const text = (selector) => document.querySelector(selector)?.innerText || "";
      const activeViewId = () => document.querySelector(".view.active")?.id || "";
      const phone = `139${String(Date.now()).slice(-8)}`;
      await waitFor('[data-login-tab="customerRegister"]');
      await click('[data-login-tab="customerRegister"]');
      await fill("#registerName", "\u6d4f\u89c8\u5668\u70df\u6d4b\u5ba2\u6237");
      await fill("#registerPhone", phone);
      await fill("#registerEmail", `smoke-${Date.now()}@example.com`);
      await fill("#registerOrg", "\u5168\u6f9c\u70df\u6d4b");
      await fill("#registerPassword", "Passw0rd!");
      await fill("#registerPasswordConfirm", "Passw0rd!");
      await click("#sendSmsCodeBtn");
      await sleep(300);
      await click('#customerRegisterForm button[type="submit"]');
      await sleep(700);

      const initialProjectCount = text("#projectCount");
      const initialProjectTable = text("#projectTable");
      const initialOrderTable = text("#customerOrderTable");
      await click('[data-view="publication"]');
      await sleep(150);
      const initialPublication = text("#publication");

      await click('[data-view="teaching"]');
      await sleep(200);
      await click("#loadTeachingEegBtn");
      await waitForText("#projectFileTable", "system_visual_oddball_p300.edf");
      const teachingActiveView = activeViewId();
      const teachingCost = text("#analysisCost");
      const teachingTotal = text("#totalCost");
      const teachingNotice = text("#projectFileNotice");
      await click('[data-view="dashboard"]');
      await sleep(150);
      const teachingRow = [...document.querySelectorAll("#projectTable .project-row")]
        .find((row) => row.innerText.includes("system_visual_oddball_p300.edf"));
      const teachingAnalyzeButton = [...(teachingRow?.querySelectorAll("button") || [])]
        .find((button) => button.innerText.includes("\u5206\u6790"));
      if (!teachingAnalyzeButton) throw new Error("missing project analyze entry");
      teachingAnalyzeButton.click();
      await waitForText("#projectFileTable", "system_visual_oddball_p300.edf");
      const projectOpenTarget = activeViewId();
      await click("#createTaskBtn");
      await waitForText("#publication", "\u5b66\u4e60\u4ea4\u4ed8 manifest");
      const teachingPublication = text("#publication");
      const teachingProjectCount = text("#projectCount");
      const teachingPreviewButton = [...document.querySelectorAll("#publication [data-preview-download]")]
        .find((button) => button.innerText.includes("\u5b66\u4e60\u4ea4\u4ed8 manifest"));
      if (!teachingPreviewButton) throw new Error("missing teaching delivery preview button");
      teachingPreviewButton.click();
      await waitForVisible("#deliveryPreviewModal:not([hidden])");
      const teachingPreviewModalText = text("#deliveryPreviewModal");
      await click("#deliveryPreviewCancel");

      await click('[data-view="billing"]');
      await sleep(150);
      await click('[data-recharge="500"]');
      await click("#rechargeBtn");
      await waitForText("#paymentStatus", "\u5f85\u652f\u4ed8");
      const pendingText = text("#paymentStatus");
      await click("#mockAlipayNotifyBtn");
      await waitForText("#paymentStatus", "\u5df2\u5165\u8d26");
      const paidText = text("#paymentStatus");
      const customerOrderText = text("#customerOrderTable");
      const balance = text("#balanceMain");

      await click('[data-view="analysis"]');
      await sleep(150);
      await click("#loadLocalBdfBtn");
      await waitForText("#projectFileTable", "C64RS_390026040074_260531103644.bdf");
      const localBdfProjectText = text("#projectFileTable");
      const submitReadinessBeforePreview = text("#submitReadiness");
      const submitBlockedBeforePreview = Boolean(document.querySelector("#createTaskBtn")?.disabled);
      const localRow = [...document.querySelectorAll("#projectFileTable .table-row")]
        .find((row) => row.innerText.includes("C64RS_390026040074_260531103644.bdf"));
      const previewButton = [...(localRow?.querySelectorAll("button") || [])]
        .find((button) => button.innerText.includes("\u9884\u89c8"));
      if (!previewButton) throw new Error("missing local BDF preview button");
      previewButton.click();
      await waitForText("#eegMeta", "\u901a\u9053\uff1a64");
      await waitForText("#eegMeta", "\u91c7\u6837\u7387\uff1a1000 Hz");
      await waitForText("#eegMeta", "Nyquist\uff1a500 Hz");
      await waitForText("#methodRecommendation", "FocusChange");
      await waitForText("#methodRecommendation", "SelectedPatchesChange");
      const eventOptions = [...document.querySelectorAll("#eventType option")].map((option) => option.value);
      if (!eventOptions.includes("FocusChange") || !eventOptions.includes("SelectedPatchesChange")) {
        throw new Error(`event labels not populated from EEG events: ${eventOptions.join(",")}`);
      }
      await waitForText("#eegFilterLimit", "Nyquist 500 Hz");
      const lowpassMax = Number(document.querySelector("#eegLowpassInput")?.max || 0);
      const notchMax = Number(document.querySelector("#eegNotchInput")?.max || 0);
      if (!(lowpassMax > 0 && lowpassMax < 500)) throw new Error(`invalid lowpass max: ${lowpassMax}`);
      if (!(notchMax > 0 && notchMax < 500)) throw new Error(`invalid notch max: ${notchMax}`);
      document.querySelector("#eegNotchEnable").click();
      await waitForText("#eegFilterLabel", "\u9677\u6ce2 50 Hz");
      const bdfPreviewMeta = text("#eegMeta");
      const submitReadinessAfterPreview = text("#submitReadiness");
      const submitReadyAfterPreview = !document.querySelector("#createTaskBtn")?.disabled;
      await click("#createTaskBtn");
      await waitForText("#publication", "\u4ea4\u4ed8\u4ef6");
      const submittedProjectTable = text("#projectTable");
      if (!submittedProjectTable.includes("\u5df2\u5206\u6790")) throw new Error("project list missing analyzed state");
      const chargedOrderText = text("#customerOrderTable");
      const directPublication = text("#publication");
      const directPreviewCount = document.querySelectorAll("#publication [data-preview-download]").length;
      const directFigureCount = document.querySelectorAll("#publication .formal-result-figures img").length;
      const svgPreviewButton = [...document.querySelectorAll("#publication [data-preview-download]")]
        .find((button) => button.innerText.includes("GFP \u6761\u4ef6\u56fe SVG"));
      if (!svgPreviewButton) throw new Error("missing SVG preview button");
      svgPreviewButton.click();
      await waitForVisible("#deliveryPreviewModal:not([hidden])");
      const svgPreviewModalText = text("#deliveryPreviewModal");
      await click("#deliveryPreviewCancel");

      await click("#logoutBtn");
      await sleep(150);
      await click("#adminEntryBtn");
      await sleep(500);
      await click('[data-view="adminOrders"]');
      await waitForText("#adminOrderTable", "\u5df2\u6263\u8d39");
      const chainText = text("#adminBusinessChain");
      const adminOrderText = text("#adminOrderTable");
      const methodText = text("#adminMethodGrid");

      await click("#logoutBtn");
      await sleep(150);
      await fill("#customerEmail", phone);
      await fill("#customerPassword", "Passw0rd!");
      await click('#customerLoginForm button[type="submit"]');
      await sleep(450);
      await click('[data-view="publication"]');
      await waitForText("#publication", "\u4ea4\u4ed8\u4ef6");
      const finalPublication = text("#publication");
      const finalDownloadCount = document.querySelectorAll("#publication a[download]").length;
      const finalPreviewCount = document.querySelectorAll("#publication [data-preview-download]").length;
      const architectureModel = document.documentElement.dataset.architectureModel || "";
      const architectureSourceVersion = window.QLANALYSER_ARCHITECTURE?.source?.version || "";
      const lifecycleCount = document.querySelectorAll(".architecture-lifecycle").length;
      const lifecycleText = [...document.querySelectorAll(".architecture-lifecycle")]
        .map((item) => item.innerText || "")
        .join("\n");
      let activeProjectArchitecture = { error: "state not inspected" };
      try {
        const activeProject = state.projects.find((project) => project.id === state.activeProjectId);
        activeProjectArchitecture = {
          objectType: activeProject?.objectType || "",
          eegFileIds: activeProject?.eegFileIds?.length || 0,
          taskIds: activeProject?.taskIds?.length || 0,
          artifactIds: activeProject?.artifactIds?.length || 0,
        };
      } catch (error) {
        activeProjectArchitecture = { error: String(error?.message || error) };
      }
      const firstDeliveryPreview = document.querySelector("#publication [data-preview-download]");
      if (!firstDeliveryPreview) throw new Error("missing formal delivery preview button");
      firstDeliveryPreview.click();
      await waitForVisible("#deliveryPreviewModal:not([hidden])");
      const formalPreviewModalText = text("#deliveryPreviewModal");
      const finalFigureCount = document.querySelectorAll("#publication .formal-result-figures img").length;

      return {
        initialProjectCount,
        initialProjectTable,
        initialOrderTable,
        initialPublication,
        teachingActiveView,
        teachingCost,
        teachingTotal,
        teachingNotice,
        projectOpenTarget,
        teachingPublication,
        teachingProjectCount,
        teachingPreviewModalText,
        pendingText,
        paidText,
        customerOrderHasPaid: customerOrderText.includes("\u5df2\u5165\u8d26"),
        balance,
        localBdfProjectText,
        submitReadinessBeforePreview,
        submitBlockedBeforePreview,
        bdfPreviewMeta,
        submitReadinessAfterPreview,
        submitReadyAfterPreview,
        submittedProjectTable,
        directPublication,
        directPreviewCount,
        directFigureCount,
        svgPreviewModalText,
        chargedOrderHasTask: chargedOrderText.includes("\u5df2\u6263\u8d39"),
        adminOrderHasPayment: adminOrderText.includes("PAY-") && adminOrderText.includes("\u5df2\u5165\u8d26"),
        adminOrderHasChargedTask: adminOrderText.includes("\u5df2\u6263\u8d39"),
        adminChainHasPayment: chainText.includes("\u652f\u4ed8\u56de\u8c03") || chainText.includes("\u521b\u5efa\u8ba2\u5355"),
        adminMethodHasAdapters: methodText.includes("\u652f\u4ed8\u5b9d") && methodText.includes("\u6ce8\u518c\u77ed\u4fe1"),
        finalPublication,
        finalDownloadCount,
        finalPreviewCount,
        architectureModel,
        architectureSourceVersion,
        lifecycleCount,
        lifecycleText,
        activeProjectArchitecture,
        formalPreviewModalText,
        finalFigureCount,
      };
    }.toString()})()`;

    let evaluated;
    try {
      evaluated = await cdp.send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
    } catch (error) {
      if (!String(error.message || "").includes("Execution context was destroyed")) throw error;
      await sleep(1200);
      evaluated = await cdp.send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
    }
    if (evaluated.exceptionDetails) {
      throw new Error(evaluated.exceptionDetails.exception?.description || evaluated.exceptionDetails.text || "browser smoke failed");
    }
    const result = evaluated.result.value;
    if (!result || !Object.keys(result).length) {
      throw new Error(`browser smoke returned no result: ${JSON.stringify(evaluated)}`);
    }

    console.log(JSON.stringify(result, null, 2));
    const failed = [
      result.initialProjectCount !== "0" && "new customer should start with 0 projects",
      !result.initialProjectTable.includes("\u8fd8\u6ca1\u6709\u9879\u76ee") && "formal project empty state missing",
      !result.initialOrderTable.includes("\u8fd8\u6ca1\u6709\u8d26\u6237\u6d41\u6c34") && "initial ledger is polluted",
      !result.initialPublication.includes("\u6682\u65e0\u7ed3\u679c") && "formal delivery empty state missing",
      result.teachingActiveView !== "analysis" && "learning mode did not enter formal analysis view",
      !result.teachingCost.includes("\u5b66\u4e60\u6a21\u5f0f\u514d\u6263\u8d39") && "learning cost is not free",
      !result.teachingTotal.includes("0.00") && "learning total is not zero",
      !result.teachingNotice.includes("\u514d\u6263\u8d39") && "learning file notice does not explain free run",
      !result.teachingPublication.includes("\u590d\u6838\u94fe\u8def") && "learning delivery lacks audit trace",
      !result.teachingPublication.includes("\u5b66\u4e60\u4ea4\u4ed8 manifest") && "learning delivery manifest missing",
      !result.teachingPublication.includes("P300") && "learning P300 result missing",
      result.teachingProjectCount !== "1" && "learning mode should create a learning project in the formal project list",
      !result.teachingPreviewModalText.includes("\u7ed3\u679c\u5305") && !result.teachingPreviewModalText.includes("manifest") && "learning delivery did not open preview first",
      !result.paidText.includes("\u5df2\u5165\u8d26") && "sandbox payment not credited",
      !result.customerOrderHasPaid && "customer ledger did not show credited payment",
      !result.localBdfProjectText.includes("\u672c\u673a\u6d4b\u8bd5\u6570\u636e") && "local BDF did not enter project files",
      !result.submitReadinessBeforePreview.includes("Preview") && "submit readiness does not expose Preview gate",
      !result.submitBlockedBeforePreview && "formal BDF task can be submitted before preview",
      !result.bdfPreviewMeta.includes("\u901a\u9053\uff1a64") && "local BDF preview did not show 64 EEG channels",
      !result.bdfPreviewMeta.includes("\u91c7\u6837\u7387\uff1a1000 Hz") && "local BDF preview did not show raw 1000 Hz sampling rate",
      !result.bdfPreviewMeta.includes("\u65f6\u957f\uff1a188.0 s") && "local BDF preview did not show 188.0 s duration",
      !result.submitReadinessAfterPreview.includes("\u5df2\u6838\u5bf9\u4fe1\u53f7") && "submit readiness does not confirm preview after EEG preview",
      !result.submitReadyAfterPreview && "formal BDF task is still blocked after preview",
      !result.submittedProjectTable.includes("\u7ed3\u679c\u5f85\u67e5\u770b") && "formal local BDF project did not move to result-ready status",
      !result.directPublication.includes("GFP") && "formal local BDF delivery did not show ERP/GFP figures",
      result.directPreviewCount < 15 && "formal local BDF delivery does not expose all figure/file previews",
      result.directFigureCount < 5 && "formal local BDF result does not render all five figures",
      !result.svgPreviewModalText.includes("GFP \u6761\u4ef6\u56fe SVG") && "SVG delivery did not open the selected SVG preview first",
      !result.chargedOrderHasTask && "customer ledger did not show completed task charge",
      !result.adminOrderHasPayment && "admin order table did not show payment order",
      !result.adminOrderHasChargedTask && "admin did not confirm task charge",
      !result.adminChainHasPayment && "admin business chain lacks payment/order node",
      !result.adminMethodHasAdapters && "admin system config lacks SMS/payment adapter status",
      !result.finalPublication.includes("\u4ea4\u4ed8\u4ef6") && "formal delivery did not appear after admin charge",
      result.finalDownloadCount !== 0 && "formal delivery still has direct download links",
      result.finalPreviewCount < 5 && "formal delivery preview buttons are insufficient",
      result.architectureModel !== "v1-research-paid-platform" && "architecture model DOM marker missing",
      result.architectureSourceVersion !== "v1-research-paid-platform" && "architecture model source version missing",
      result.lifecycleCount < 2 && "project lifecycle strips are missing",
      !result.lifecycleText.includes("Project") && "lifecycle strip does not show Project",
      !result.lifecycleText.includes("EEGFile") && "lifecycle strip does not show EEGFile",
      !result.lifecycleText.includes("AnalysisTask") && "lifecycle strip does not show AnalysisTask",
      !result.lifecycleText.includes("Artifact") && "lifecycle strip does not show Artifact",
      result.activeProjectArchitecture.error && `active project architecture state unavailable: ${result.activeProjectArchitecture.error}`,
      result.activeProjectArchitecture.objectType !== "Project" && "active project is not a formal Project object",
      result.activeProjectArchitecture.eegFileIds < 1 && "active project is not linked to EEGFile ids",
      result.activeProjectArchitecture.taskIds < 1 && "active project is not linked to AnalysisTask ids",
      result.activeProjectArchitecture.artifactIds < 1 && "active project is not linked to Artifact ids",
      !result.formalPreviewModalText.includes("GFP \u6761\u4ef6\u56fe") && "formal delivery did not open the first result figure preview",
      result.finalFigureCount < 2 && "formal result figures did not render",
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
