import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const root = path.resolve(__dirname, "..");
const app = fs.readFileSync(path.join(root, "frontend", "app.js"), "utf8");
const html = fs.readFileSync(path.join(root, "frontend", "index.html"), "utf8");

const checks = [
  {
    name: "qc-preview-is-not-a-required-primary-button",
    pass: !html.includes("运行质控预览") && html.includes("重新加载预览"),
  },
  {
    name: "file-selection-triggers-auto-preview",
    pass: app.includes("requestAutoQcPreviewForSelectedFile(file)") && app.includes("real:auto-qc-preview"),
  },
  {
    name: "preview-and-edit-tools-share-one-workbench",
    pass:
      html.includes('data-testid="preview-edit-workbench"') &&
      html.indexOf('data-testid="preview-edit-workbench"') <
        html.indexOf('data-testid="segment-tag-editor-panel"'),
  },
  {
    name: "segment-exclusion-is-restorable",
    pass:
      app.includes("prepEditState.excludedSegments.push") &&
      app.includes("prepEditState.restoredSegments.push"),
  },
  {
    name: "bad-channel-change-is-restorable",
    pass:
      app.includes("prepEditState.badChannels.push") &&
      app.includes("prepEditState.restoredBadChannels.push") &&
      html.includes("恢复坏道修改"),
  },
  {
    name: "event-label-change-is-restorable",
    pass:
      app.includes("prepEditState.restoredLabels.push") &&
      app.includes('action === "restore-label"') &&
      html.includes("恢复标签"),
  },
  {
    name: "confusing-internal-copy-is-replaced",
    pass:
      html.includes("查看数据概况") &&
      html.includes("保存事件与片段") &&
      html.includes("下载处理记录") &&
      !html.includes("丢弃坏道修改") &&
      !html.includes("保存坏道审计"),
  },
  {
    name: "runtime-copy-does-not-leak-internal-qc-terms",
    pass:
      !app.includes("QC 预览") &&
      !app.includes("Metadata QC") &&
      !app.includes("bad-channel audit") &&
      !app.includes("Upload an EEG file before saving") &&
      !app.includes("Confirm the data-preparation plan"),
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
