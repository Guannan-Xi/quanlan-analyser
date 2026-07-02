import { chromium, chromiumLaunchOptions } from "./lib/playwright_runtime.mjs";
import fs from "node:fs";
import path from "node:path";

const TARGET_URL = process.env.QLANALYSER_FRONTEND_URL || "http://127.0.0.1:4174/?customer_demo=auto&api=http://127.0.0.1:8001/api&v=project-delete-empty-e2e#dashboard";
const API_BASE = process.env.QLANALYSER_API_BASE_URL || "http://127.0.0.1:8001/api";
const OUT_DIR = process.env.QLANALYSER_PROJECT_DELETE_E2E_DIR || path.resolve("work/release_evidence/20260630-project-list-delete-e2e");
const EVIDENCE_PATH = path.join(OUT_DIR, "project_list_delete_e2e.json");

fs.mkdirSync(OUT_DIR, { recursive: true });

async function apiJson(pathname, options = {}) {
  const response = await fetch(`${API_BASE}${pathname}`, options);
  const text = await response.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = text; }
  if (!response.ok) throw new Error(`${options.method || "GET"} ${pathname} failed: ${response.status} ${text}`);
  return data;
}

async function waitForApp(page) {
  await page.waitForSelector("#dashboard", { timeout: 30000 });
  await page.waitForFunction(() => document.querySelector("#iaProjectRows") && !document.body.innerText.includes("登录中"), null, { timeout: 30000 });
}

async function collectState(page) {
  return await page.evaluate(() => {
    const rows = Array.from(document.querySelectorAll("#iaProjectRows .project-row"));
    const rowTexts = rows.map((row) => row.innerText.trim());
    const hiddenToggle = document.querySelector("#workspaceShowReviewProjects");
    const filterSummary = document.querySelector("#workspaceProjectFilterSummary")?.innerText || "";
    const emptyText = document.querySelector("#iaProjectRows .empty-object-state")?.innerText || "";
    const currentProject = window.__QLANALYSER_E2E_STATE__?.real?.project?.id || "";
    return { rowCount: rows.length, rowTexts, filterSummary, emptyText, showInternal: Boolean(hiddenToggle?.checked), currentProject };
  });
}

async function run() {
  const evidence = {
    script: "e2e_project_list_empty_and_delete.mjs",
    started_at: new Date().toISOString(),
    frontend_url: TARGET_URL,
    api_base: API_BASE,
    checks: {},
    steps: [],
    errors: [],
  };
  const browser = await chromium.launch(chromiumLaunchOptions());
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const consoleErrors = [];
  page.on("console", (msg) => { if (["error"].includes(msg.type())) consoleErrors.push(msg.text()); });
  page.on("dialog", async (dialog) => {
    evidence.steps.push({ action: "dialog", type: dialog.type(), message: dialog.message() });
    await dialog.accept();
  });

  try {
    await page.goto(TARGET_URL, { waitUntil: "domcontentloaded", timeout: 60000 });
    await waitForApp(page);
    await page.waitForTimeout(1000);
    evidence.initial = await collectState(page);
    evidence.checks.initial_no_legacy_my_research_rows = !evidence.initial.rowTexts.some((text) => /我的研究项目/.test(text));
    evidence.checks.initial_no_internal_rows = evidence.initial.rowTexts.every((text) => !/e2e|acceptance|smoke|demo|fixture|我的研究项目/i.test(text));

    await page.locator('[data-real-action="create-project"]').filter({ visible: true }).first().click();
    const created = await page.waitForFunction(() => {
      const project = window.__QLANALYSER_E2E_STATE__?.real?.project;
      return project?.id ? { id: project.id, name: project.name || project.title || project.id } : null;
    }, null, { timeout: 30000 }).then((handle) => handle.jsonValue());
    evidence.created_project = { id: created.id, name: created.name };
    await page.waitForFunction((projectId) => {
      const rows = Array.from(document.querySelectorAll("#iaProjectRows .project-row"));
      return rows.some((row) => row.innerText.includes(projectId));
    }, created.id, { timeout: 30000 });
    evidence.afterCreate = await collectState(page);
    evidence.checks.created_project_visible = evidence.afterCreate.rowTexts.some((text) => text.includes(created.id) || text.includes(created.name));
    evidence.checks.created_project_selected = evidence.afterCreate.currentProject === created.id;
    evidence.checks.created_project_data_list_empty = await page.evaluate(() => {
      const dataRows = Array.from(document.querySelectorAll("#iaDataRows .table-row"));
      const emptyText = document.querySelector("#iaDataEmptyState")?.innerText || document.body.innerText || "";
      return dataRows.length === 0 || /暂无数据|上传|选择 EEG 数据/.test(emptyText);
    });

    const escapedId = String(created.id).replace(/"/g, '\\"');
    if (evidence.afterCreate.currentProject !== created.id) {
      await page.click(`[data-project-select="${escapedId}"]`);
    }
    await page.waitForTimeout(500);
    const selectedBeforeDelete = await collectState(page);
    evidence.selected_before_delete = selectedBeforeDelete.currentProject;
    await page.click('[data-ia-action="delete-project"]');
    await page.waitForFunction((projectId) => {
      const rows = Array.from(document.querySelectorAll("#iaProjectRows .project-row"));
      return !rows.some((row) => row.innerText.includes(projectId));
    }, created.id, { timeout: 30000 });
    evidence.afterDelete = await collectState(page);
    const deletedReadback = await apiJson(`/projects/${encodeURIComponent(created.id)}`);
    evidence.deleted_readback = { id: deletedReadback.id, status: deletedReadback.status };
    evidence.checks.delete_soft_deleted_backend = deletedReadback.status === "deleted";
    evidence.checks.deleted_project_hidden_from_default_list = !evidence.afterDelete.rowTexts.some((text) => text.includes(created.id) || text.includes(created.name));
    evidence.checks.selection_cleared_after_delete = !evidence.afterDelete.currentProject;
    evidence.checks.no_console_errors = consoleErrors.length === 0;
    evidence.console_errors = consoleErrors;
    evidence.status = Object.values(evidence.checks).every(Boolean) ? "passed" : "failed";
  } catch (error) {
    evidence.status = "failed";
    evidence.errors.push(error.stack || error.message || String(error));
  } finally {
    evidence.finished_at = new Date().toISOString();
    await page.screenshot({ path: path.join(OUT_DIR, "project_list_delete_final.png"), fullPage: true }).catch(() => null);
    await browser.close().catch(() => null);
    fs.writeFileSync(EVIDENCE_PATH, `${JSON.stringify(evidence, null, 2)}\n`, "utf8");
    console.log(JSON.stringify(evidence, null, 2));
  }
  if (evidence.status !== "passed") process.exit(1);
}

run().catch((error) => {
  console.error(error.stack || error.message || String(error));
  process.exit(1);
});
