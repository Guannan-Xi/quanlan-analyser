import fs from "node:fs";
import path from "node:path";
import { chromium } from "./lib/playwright_runtime.mjs";

const edgeCandidates = [
  "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
  "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
];
const edgePath = edgeCandidates.find((item) => fs.existsSync(item));

const root = process.cwd();
const evidenceDir = path.join(root, "work", "release_evidence", "20260701-customer-demo-p0-ui-fix");
fs.mkdirSync(evidenceDir, { recursive: true });
const baseUrl = process.env.QLANALYSER_FRONTEND_URL || "http://127.0.0.1:4174";
const url = `${baseUrl}/?customer_demo=auto&api=http%3A%2F%2F127.0.0.1%3A8001%2Fapi&v=customer-p0-ui-fix#dashboard`;
const badCopyPattern = /[锟�]|椤圭洰|鏁版嵁|鍒嗘瀽|缁撴灉|鎶ュ憡|璐|鐧|涓|浠诲姟|褰撳墠/;
const checks = [];
const add = (name, pass, details = {}) => checks.push({ name, pass: Boolean(pass), details });

const browser = await chromium.launch({ headless: true, ...(edgePath ? { executablePath: edgePath } : {}) });
const page = await browser.newPage({ viewport: { width: 1440, height: 960 } });
const consoleErrors = [];
page.on("console", (msg) => { if (["error"].includes(msg.type())) consoleErrors.push(msg.text()); });
page.on("pageerror", (err) => consoleErrors.push(err.message));

await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60000 });
await page.waitForTimeout(2500);

async function collectState(label) {
  const data = await page.evaluate(() => ({
    hash: window.location.hash,
    title: document.querySelector("#viewTitle")?.textContent?.trim() || "",
    activeView: document.querySelector(".view.active")?.id || "",
    nav: Array.from(document.querySelectorAll(".nav [data-view] span")).map((n) => n.textContent.trim()),
    bodyText: document.body.innerText.slice(0, 5000),
    projectRows: Array.from(document.querySelectorAll("#iaProjectRows [data-project-select]")).map((n) => n.textContent.trim()),
    projectEmpty: document.querySelector('[data-testid="customer-empty-project-list"]')?.textContent?.trim() || "",
    reportText: document.querySelector("#realDeliveryLinks")?.textContent?.trim() || "",
    resultText: document.querySelector("#realResultReview")?.textContent?.trim() || "",
  }));
  fs.writeFileSync(path.join(evidenceDir, `${label}.json`), JSON.stringify(data, null, 2), "utf8");
  await page.screenshot({ path: path.join(evidenceDir, `${label}.png`), fullPage: true });
  return data;
}

let state = await collectState("dashboard");
add("dashboard_visible", state.activeView === "dashboard" && state.title.includes("项目管理"), state);
add("nav_copy_clean", ["项目管理", "数据管理", "数据准备", "分析任务", "结果查看", "报告交付"].every((item) => state.nav.includes(item)), { nav: state.nav });
add("dashboard_no_mojibake", !badCopyPattern.test(state.bodyText), { sample: state.bodyText.slice(0, 1000) });
add("customer_trial_project_list_empty_by_default", state.projectRows.length === 0, { projectRows: state.projectRows, projectEmpty: state.projectEmpty });

await page.click('[data-view="statistics"]');
await page.waitForTimeout(800);
state = await collectState("statistics");
add("statistics_route", state.activeView === "statistics" && page.url().includes("#statistics"), state);
add("statistics_empty_clear", /还没有可查看的分析结果|结果查看/.test(state.resultText + state.bodyText), { resultText: state.resultText });
add("statistics_no_mojibake", !badCopyPattern.test(state.bodyText), { sample: state.bodyText.slice(0, 1000) });

await page.click('[data-view="publication"]');
await page.waitForTimeout(800);
state = await collectState("publication");
add("publication_route", state.activeView === "publication" && page.url().includes("#publication"), state);
add("publication_empty_clear", /还没有可下载报告|报告交付/.test(state.reportText + state.bodyText), { reportText: state.reportText });
add("publication_no_workflow_fallback", state.activeView !== "workflow", state);
add("publication_no_mojibake", !badCopyPattern.test(state.bodyText), { sample: state.bodyText.slice(0, 1000) });

const result = {
  status: checks.every((c) => c.pass) && consoleErrors.length === 0 ? "passed" : "failed",
  url,
  checks,
  consoleErrors,
  evidenceDir,
};
fs.writeFileSync(path.join(evidenceDir, "customer_demo_p0_ui_fix_result.json"), JSON.stringify(result, null, 2), "utf8");
await browser.close();
if (result.status !== "passed") {
  console.error(JSON.stringify(result, null, 2));
  process.exit(1);
}
console.log(JSON.stringify(result, null, 2));
