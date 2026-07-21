import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const root = path.resolve(__dirname, "..");
const css = fs.readFileSync(path.join(root, "frontend/styles.css"), "utf8");

const requiredTokens = [
  "--ql-bg-canvas",
  "--ql-bg-panel",
  "--ql-border",
  "--ql-text",
  "--ql-primary",
  "--ql-success",
  "--ql-warning",
  "--ql-danger",
  "--ql-shadow-panel",
];

const requiredSelectors = [
  ".primary-btn",
  ".ghost-btn",
  ".metric",
  ".status-chip",
  ".ia-table .table-row.selected",
  ".danger-soft",
  ".review-gate-card b",
  ".ia-method-card b",
  "#dashboard .ia-data-ledger .segment-summary",
  ".project-detail-summary span",
];

const requiredUsage = [
  "var(--ql-primary)",
  "var(--ql-success)",
  "var(--ql-warning)",
  "var(--ql-danger)",
  "var(--ql-bg-panel)",
  "var(--ql-border)",
];

const governanceBlock = css.slice(css.indexOf("/* 2026-06-25 UX color governance"));
const checks = [
  ...requiredTokens.map((item) => ({ name: `token:${item}`, pass: css.includes(item) })),
  ...requiredSelectors.map((item) => ({ name: `selector:${item}`, pass: governanceBlock.includes(item) })),
  ...requiredUsage.map((item) => ({ name: `usage:${item}`, pass: governanceBlock.includes(item) })),
  {
    name: "governance-block-present",
    pass: governanceBlock.startsWith("/* 2026-06-25 UX color governance"),
  },
  {
    name: "ordinary-info-not-success-green",
    pass:
      /#dashboard \.ia-data-ledger(?:\:not\(\.has-project\))? \.segment-summary[\s\S]{0,180}var\(--ql-primary-soft\)/.test(
        governanceBlock,
      ) && !/#dashboard \.ia-data-ledger(?:\:not\(\.has-project\))? \.segment-summary[\s\S]{0,180}var\(--ql-success-soft\)/.test(
        governanceBlock,
      ),
  },
];

const result = {
  script: path.basename(__filename),
  checked_at: new Date().toISOString(),
  checks,
  passed: checks.every((item) => item.pass),
};

console.log(JSON.stringify(result, null, 2));
if (!result.passed) process.exit(1);
