import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const root = path.resolve(__dirname, "..");

const html = fs.readFileSync(path.join(root, "frontend/index.html"), "utf8");
const app = fs.readFileSync(path.join(root, "frontend/app.js"), "utf8");
const relevantLines = app
  .split(/\r?\n/)
  .filter((line) =>
    [
      "workspaceShowReviewProjects",
      "projectFilterSummary",
      "project-data-crud-panel",
      "next-action-hint",
      "PRODUCT_NAV_LABELS",
      "PRODUCT_VIEW_TITLES",
      "setTextIfPresent",
      "textContent",
    ].some((marker) => line.includes(marker)),
  )
  .join("\n");
const text = `${html}\n${relevantLines}`;

const banned = [
  "显示验收/归档项目",
  "评审验证",
  "评审门",
  "预处理入口",
  "已显示验收与归档记录",
];
const required = [
  "显示归档项目",
  "项目内数据",
  "质量检查",
  "先从项目开始，再选择项目内数据并准备分析。",
];

const checks = [
  ...banned.map((copy) => ({ name: `banned:${copy}`, pass: !text.includes(copy) })),
  ...required.map((copy) => ({ name: `required:${copy}`, pass: text.includes(copy) })),
];

const result = {
  script: path.basename(__filename),
  checked_at: new Date().toISOString(),
  checks,
  passed: checks.every((item) => item.pass),
};

console.log(JSON.stringify(result, null, 2));
if (!result.passed) process.exit(1);
