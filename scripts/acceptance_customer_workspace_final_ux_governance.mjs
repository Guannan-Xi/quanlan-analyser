import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const root = path.resolve(__dirname, "..");

const html = fs.readFileSync(path.join(root, "frontend/index.html"), "utf8");
const app = fs.readFileSync(path.join(root, "frontend/app.js"), "utf8");
const visibleMarkers = [
  "setTextIfPresent",
  "setAllTextIfPresent",
  "setRealStatus",
  "setRealActionEnabled",
  "target.innerHTML",
  "delivery.innerHTML",
  "data-report-download",
  "recordUiAction",
  "throw new Error",
  "review-gate-card",
  "loginPairs",
  "valueCards",
];
const appVisible = app
  .split(/\r?\n/)
  .filter((line) => visibleMarkers.some((marker) => line.includes(marker)))
  .join("\n");
const text = `${html}\n${appVisible}`;

const banned = [
  "审计日志",
  "审计记录",
  "运行 QC",
  "QC 预览",
  "Metadata QC",
  "报告 ZIP",
  "ZIP 下载",
  "validator",
  "评审验证",
  "评审门",
  "显示验收/归档项目",
  "预处理入口",
  "下载 JSON",
  "计划 JSON",
  "bad-channel audit",
  "不使用 API",
  "不用 API",
  "必须",
  "必需",
  "可运行",
];
const required = [
  "操作记录",
  "基础质量预览",
  "项目内数据",
  "显示归档项目",
  "生成交付报告",
  "下载完整报告",
  "开始 PSD 分析",
  "质量检查",
  "可用",
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
