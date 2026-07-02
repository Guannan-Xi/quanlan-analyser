import fs from "node:fs";
import path from "node:path";
import { chromium } from "./lib/playwright_runtime.mjs";

const edgeCandidates = [
  "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
  "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
];
const edgePath = edgeCandidates.find((item) => fs.existsSync(item));

const root = process.cwd();
const evidenceDir = path.join(root, "work", "release_evidence", "20260701-customer-analysis-complexity-gate");
fs.mkdirSync(evidenceDir, { recursive: true });

const baseUrl = process.env.QLANALYSER_FRONTEND_URL || "http://127.0.0.1:4174";
const apiBase = process.env.QLANALYSER_API_BASE || "http://127.0.0.1:8001/api";
const url = `${baseUrl}/?customer_demo=auto&api=${encodeURIComponent(apiBase)}&v=customer-analysis-complexity-gate#dashboard`;

const browser = await chromium.launch({
  headless: true,
  executablePath: edgePath,
});
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
const consoleErrors = [];
page.on("console", (message) => {
  if (message.type() === "error") consoleErrors.push(message.text());
});

const result = {
  status: "failed",
  url,
  evidenceDir,
  checks: [],
  failures: [],
  consoleErrors,
};

function check(name, passed, details = {}) {
  result.checks.push({ name, passed: Boolean(passed), ...details });
  if (!passed) result.failures.push({ name, ...details });
}

await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60000 });
await page.waitForTimeout(1500);

await page.evaluate(async () => {
  if (typeof window.__qlanalyserE2ESeedWorkspace === "function") {
    await window.__qlanalyserE2ESeedWorkspace({
      project: {
        id: "e2e_customer_project_no_data",
        name: "客户试用项目",
        status: "active",
        data_count: 0,
        research_type: "research_eeg",
      },
    });
  }
});
await page.locator('[data-view="analysis"]').first().click();
await page.waitForTimeout(1500);

const snapshot = await page.evaluate(() => {
  const visible = (element) => Boolean(
    element
    && !element.hidden
    && getComputedStyle(element).display !== "none"
    && getComputedStyle(element).visibility !== "hidden"
    && element.getClientRects().length
  );
  const visibleText = [...document.querySelectorAll("#analysis *")]
    .filter((node) => visible(node) && node.children.length === 0)
    .map((node) => node.innerText || node.textContent || "")
    .join("\n");
  const buttons = [...document.querySelectorAll("button")]
    .filter(visible)
    .map((button) => ({
      text: button.innerText.trim().replace(/\s+/g, " "),
      disabled: button.disabled,
      action: button.dataset.realAction || button.dataset.iaAction || button.dataset.view || button.dataset.viewJump || "",
      testid: button.closest("[data-testid]")?.dataset?.testid || "",
    }));
  const mainButtons = [...document.querySelectorAll("#analysis button")]
    .filter(visible)
    .map((button) => ({
      text: button.innerText.trim().replace(/\s+/g, " "),
      disabled: button.disabled,
      action: button.dataset.realAction || button.dataset.iaAction || button.dataset.view || button.dataset.viewJump || "",
      testid: button.closest("[data-testid]")?.dataset?.testid || "",
    }));
  const panels = [...document.querySelectorAll("[data-testid]")]
    .map((node) => ({
      testid: node.dataset.testid,
      visible: visible(node),
      text: node.innerText.trim().replace(/\s+/g, " ").slice(0, 500),
    }));
  const visiblePanelIds = panels.filter((panel) => panel.visible).map((panel) => panel.testid);
  const visibleActions = buttons.map((button) => button.action).filter(Boolean);
  const analysisRect = document.querySelector('[data-testid="data-preparation-workbench"]')?.getBoundingClientRect?.();
  const previewRect = document.querySelector('[data-testid="single-file-preview-panel"]')?.getBoundingClientRect?.();
  return {
    hash: location.hash,
    viewTitle: document.querySelector("#viewTitle")?.innerText || "",
    bodyText: visibleText,
    buttons,
    mainButtons,
    panels,
    visiblePanelIds,
    visibleActions,
    analysisLayout: analysisRect ? { width: Math.round(analysisRect.width), height: Math.round(analysisRect.height) } : null,
    previewLayout: previewRect ? { width: Math.round(previewRect.width), height: Math.round(previewRect.height) } : null,
    confirmVisibleCount: buttons.filter((button) => button.action === "confirm-plan-inline").length,
    visibleButtonCount: buttons.length,
    mainVisibleButtonCount: mainButtons.length,
    snippets: {
      prepContextSummary: document.querySelector("#prepContextSummary")?.innerText || "",
      prepRevisionState: document.querySelector("#prepRevisionState")?.innerText || "",
      waveformWorkbenchStatus: document.querySelector("#waveformWorkbenchStatus")?.innerText || "",
    },
  };
});

result.snapshot = {
  hash: snapshot.hash,
  viewTitle: snapshot.viewTitle,
  visiblePanelIds: snapshot.visiblePanelIds,
  visibleActions: snapshot.visibleActions,
  confirmVisibleCount: snapshot.confirmVisibleCount,
  visibleButtonCount: snapshot.visibleButtonCount,
  mainVisibleButtonCount: snapshot.mainVisibleButtonCount,
  analysisLayout: snapshot.analysisLayout,
  previewLayout: snapshot.previewLayout,
  snippets: snapshot.snippets,
};

await page.screenshot({ path: path.join(evidenceDir, "customer_analysis_complexity_gate.png"), fullPage: true });
fs.writeFileSync(path.join(evidenceDir, "customer_analysis_complexity_snapshot.json"), JSON.stringify(snapshot, null, 2), "utf8");

check("analysis view is reachable after current-session project", snapshot.hash === "#analysis", { actual: snapshot.hash });
check("page title is data preparation", snapshot.viewTitle.includes("数据准备"), { actual: snapshot.viewTitle });
check("single file preview remains visible", snapshot.visiblePanelIds.includes("single-file-preview-panel"), { visiblePanelIds: snapshot.visiblePanelIds });
check("preprocessing settings hidden until a file is selected", !snapshot.visiblePanelIds.includes("preprocessing-inline-panel"), { visiblePanelIds: snapshot.visiblePanelIds });
check("internal readiness panel hidden", !snapshot.visiblePanelIds.includes("preprocessing-readiness-panel"), { visiblePanelIds: snapshot.visiblePanelIds });
check("event epoch internal panel hidden", !snapshot.visiblePanelIds.includes("event-epoch-panel"), { visiblePanelIds: snapshot.visiblePanelIds });
check("submit duplicate hidden without file", !snapshot.visiblePanelIds.includes("data-preparation-submit-last"), { visiblePanelIds: snapshot.visiblePanelIds });
check("preview edit advanced workbench hidden", !snapshot.visiblePanelIds.includes("preview-edit-workbench"), { visiblePanelIds: snapshot.visiblePanelIds });
check("only one visible confirm action", snapshot.confirmVisibleCount <= 1, { confirmVisibleCount: snapshot.confirmVisibleCount });
check("analysis layout does not collapse into a narrow column", Number(snapshot.analysisLayout?.width || 0) >= 900, { analysisLayout: snapshot.analysisLayout });
check("preview panel has usable workbench width", Number(snapshot.previewLayout?.width || 0) >= 650, { previewLayout: snapshot.previewLayout });
check("customer has a project/data next-step entry when no file selected", snapshot.bodyText.includes("创建或打开项目") || snapshot.bodyText.includes("上传或选择 EEG 数据"), { visibleActions: snapshot.visibleActions });

const hiddenActions = [
  "save-bad-channel-audit",
  "discard-bad-channel-audit",
  "save-epoch-set",
  "download-epoch-record",
  "download-plan-json",
];
for (const action of hiddenActions) {
  check(`customer mode hides ${action}`, !snapshot.visibleActions.includes(action), { visibleActions: snapshot.visibleActions });
}

const forbiddenTexts = [
  "下载处理记录",
  "下载数据准备记录",
  "保存事件与片段",
  "保存坏道修改",
  "恢复坏道修改",
  "数据队列",
  "受保护",
  "内部/归档",
];
for (const text of forbiddenTexts) {
  check(`customer visible copy avoids ${text}`, !snapshot.bodyText.includes(text), { text });
}

check("analysis content button count is restrained", snapshot.mainVisibleButtonCount <= 6, { mainVisibleButtonCount: snapshot.mainVisibleButtonCount });
check("no browser console errors", consoleErrors.length === 0, { consoleErrors });

result.status = result.failures.length ? "failed" : "passed";
fs.writeFileSync(path.join(evidenceDir, "customer_analysis_complexity_gate_result.json"), JSON.stringify(result, null, 2), "utf8");
await browser.close();

if (result.status !== "passed") {
  console.error(JSON.stringify(result, null, 2));
  process.exit(1);
}
console.log(JSON.stringify(result, null, 2));
