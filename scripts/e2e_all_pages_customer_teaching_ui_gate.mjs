import fs from "node:fs";
import path from "node:path";
import { chromium } from "./lib/playwright_runtime.mjs";

const edgeCandidates = [
  "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
  "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
];
const edgePath = edgeCandidates.find((item) => fs.existsSync(item));
const root = process.cwd();
const evidenceDir = path.join(root, "work", "release_evidence", "20260701-all-pages-customer-teaching-ui-gate");
fs.mkdirSync(evidenceDir, { recursive: true });

const baseUrl = process.env.QLANALYSER_FRONTEND_URL || "http://127.0.0.1:4174";
const apiBase = process.env.QLANALYSER_API_BASE || "http://127.0.0.1:8001/api";
const url = `${baseUrl}/?customer_demo=auto&api=${encodeURIComponent(apiBase)}&v=all-pages-customer-teaching-ui-gate#dashboard`;

const browser = await chromium.launch({ headless: true, executablePath: edgePath });
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
const consoleErrors = [];
page.on("console", (message) => {
  if (message.type() === "error") consoleErrors.push(message.text());
});
page.on("pageerror", (error) => consoleErrors.push(error.message));

const result = {
  status: "failed",
  url,
  evidenceDir,
  checks: [],
  failures: [],
  consoleErrors,
  snapshots: {},
};

function check(name, passed, details = {}) {
  result.checks.push({ name, passed: Boolean(passed), ...details });
  if (!passed) result.failures.push({ name, ...details });
}

async function loginIfNeeded() {
  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForTimeout(1500);
  const loginButton = page.locator("button", { hasText: "登录并进入项目" }).first();
  if (await loginButton.count()) {
    await loginButton.click().catch(() => null);
  }
  await page.waitForTimeout(3500);
  await page.waitForSelector('[data-view="dashboard"], #loginPanel', { timeout: 10000 }).catch(() => null);
}

async function snapshot(name) {
  await page.waitForTimeout(900);
  const data = await page.evaluate(() => {
    const visible = (node) => Boolean(
      node
      && !node.hidden
      && getComputedStyle(node).display !== "none"
      && getComputedStyle(node).visibility !== "hidden"
      && node.getClientRects().length
    );
    const rect = (node) => {
      const box = node?.getBoundingClientRect?.();
      return box ? { width: Math.round(box.width), height: Math.round(box.height) } : null;
    };
    return {
      hash: location.hash,
      title: document.querySelector("#viewTitle")?.innerText || "",
      bodyText: document.body.innerText,
      visibleButtons: [...document.querySelectorAll("button")].filter(visible).map((button) => button.innerText.trim().replace(/\s+/g, " ")),
      visiblePanels: [...document.querySelectorAll("[data-testid]")].filter(visible).map((node) => node.dataset.testid),
      analysisLayout: rect(document.querySelector('[data-testid="data-preparation-workbench"]')),
      previewLayout: rect(document.querySelector('[data-testid="single-file-preview-panel"]')),
      teachingBanner: document.querySelector("#teachingSandboxBanner")?.innerText || "",
      loginVisible: Boolean(document.querySelector("#loginPanel") && visible(document.querySelector("#loginPanel"))),
    };
  });
  result.snapshots[name] = {
    ...data,
    bodyText: data.bodyText.slice(0, 3000),
  };
  await page.screenshot({ path: path.join(evidenceDir, `${name}.png`), fullPage: true });
  return data;
}

async function clickNav(view) {
  await page.locator(`[data-view="${view}"]`).first().click();
  await page.waitForTimeout(900);
}

await loginIfNeeded();
let dashboard = await snapshot("dashboard");
check("customer workspace is logged in", !dashboard.loginVisible, { loginVisible: dashboard.loginVisible, bodyText: dashboard.bodyText.slice(0, 200) });
check("dashboard hides internal project search", !dashboard.bodyText.includes("搜索项目"), { bodyText: dashboard.bodyText.slice(0, 1200) });
check("dashboard hides internal archive toggle", !dashboard.bodyText.includes("显示内部/归档项目"), { bodyText: dashboard.bodyText.slice(0, 1200) });
check("dashboard has a clear create project action", dashboard.bodyText.includes("创建项目"), { bodyText: dashboard.bodyText.slice(0, 1200) });

await clickNav("analysis");
const analysis = await snapshot("analysis");
check("analysis page has usable layout width", Number(analysis.analysisLayout?.width || 0) >= 900, { analysisLayout: analysis.analysisLayout });
check("analysis preview has usable width", Number(analysis.previewLayout?.width || 0) >= 650, { previewLayout: analysis.previewLayout });
check("analysis no internal event save in empty customer path", !analysis.bodyText.includes("保存事件与片段"), { bodyText: analysis.bodyText.slice(0, 1600) });

await clickNav("publication");
const publication = await snapshot("publication");
check("publication page provides empty-state next step", publication.bodyText.includes("去数据准备") || publication.bodyText.includes("生成交付报告"), { bodyText: publication.bodyText.slice(0, 1600) });

await clickNav("dashboard");
await page.locator("#teachingModeBtn").click();
await page.waitForTimeout(5000);
const teaching = await snapshot("teaching_dashboard");
check("teaching mode uses example wording", teaching.bodyText.includes("示例模式"), { bodyText: teaching.bodyText.slice(0, 1600) });
check("teaching banner avoids old teaching-mode title", !teaching.teachingBanner.includes("教学模式"), { teachingBanner: teaching.teachingBanner });
check("teaching mode has return to normal mode action", teaching.bodyText.includes("返回普通模式"), { bodyText: teaching.bodyText.slice(0, 1600) });
check("teaching mode hides internal project search", !teaching.bodyText.includes("搜索项目"), { bodyText: teaching.bodyText.slice(0, 2200) });
check("teaching mode hides internal archive toggle", !teaching.bodyText.includes("显示内部/归档项目"), { bodyText: teaching.bodyText.slice(0, 2200) });
check("teaching mode hides destructive project actions", !teaching.bodyText.includes("归档\n删除") && !teaching.visibleButtons.includes("删除"), { visibleButtons: teaching.visibleButtons });

await clickNav("storage");
const teachingStorage = await snapshot("teaching_storage");
check("teaching storage hides upload action", !teachingStorage.visibleButtons.includes("上传到当前项目"), { visibleButtons: teachingStorage.visibleButtons });
check("teaching storage hides file picker", !teachingStorage.visibleButtons.includes("选择 EEG 文件"), { visibleButtons: teachingStorage.visibleButtons });
check("teaching storage hides upload authorization", !teachingStorage.bodyText.includes("我确认有权上传"), { bodyText: teachingStorage.bodyText.slice(0, 1800) });
check("teaching storage hides edit metadata action", !teachingStorage.visibleButtons.includes("编辑名称 / 备注"), { visibleButtons: teachingStorage.visibleButtons });
check("teaching storage keeps data-prep next step", teachingStorage.visibleButtons.includes("进入数据准备"), { visibleButtons: teachingStorage.visibleButtons });

await clickNav("analysis");
const teachingAnalysis = await snapshot("teaching_analysis");
check("teaching analysis hides event and epoch panel", !teachingAnalysis.visiblePanels.includes("event-epoch-panel"), { visiblePanels: teachingAnalysis.visiblePanels });
check("teaching analysis hides readiness internals", !teachingAnalysis.visiblePanels.includes("preprocessing-readiness-panel"), { visiblePanels: teachingAnalysis.visiblePanels });
check("teaching analysis keeps protected example note", teachingAnalysis.visiblePanels.includes("teaching-data-protected"), { visiblePanels: teachingAnalysis.visiblePanels });
check("teaching analysis hides internal save/download actions", !["保存事件与片段", "下载数据准备记录", "下载处理记录", "保存坏道修改", "恢复坏道修改"].some((text) => teachingAnalysis.bodyText.includes(text)), { bodyText: teachingAnalysis.bodyText.slice(0, 2400) });
check("teaching analysis avoids old teaching wording", !teachingAnalysis.bodyText.includes("教学模式") && !teachingAnalysis.bodyText.includes("教学引导"), { bodyText: teachingAnalysis.bodyText.slice(0, 2400) });
check("teaching analysis avoids upload-or-select wording", !teachingAnalysis.bodyText.includes("上传或选择 EEG 数据"), { bodyText: teachingAnalysis.bodyText.slice(0, 2400) });

result.status = result.failures.length ? "failed" : "passed";
fs.writeFileSync(path.join(evidenceDir, "all_pages_customer_teaching_ui_gate_result.json"), JSON.stringify(result, null, 2), "utf8");
await browser.close();

if (result.status !== "passed") {
  console.error(JSON.stringify(result, null, 2));
  process.exit(1);
}
console.log(JSON.stringify(result, null, 2));
