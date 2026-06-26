import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const root = path.resolve(__dirname, "..");
const outDir =
  process.env.QLANALYSER_COPY_GOVERNANCE_EVIDENCE_DIR ||
  path.join(root, "work", "release_evidence", "07-mainline-productization", "user_copy_governance");
const evidencePath = path.join(outDir, "product_wide_ux_copy_governance.json");

const files = [
  "frontend/index.html",
  "frontend/app.js",
  "frontend/module-lab.html",
  "frontend/module-lab.js",
  "frontend/qc-lab.html",
  "frontend/qc-lab.js",
  "frontend/research-modules.html",
  "frontend/research-modules.js",
  "frontend/research-module/qc.html",
  "frontend/research-module/psd.html",
  "frontend/research-module/erp.html",
  "frontend/research-module/tfr.html",
  "frontend/research-module/pac.html",
  "frontend/research-module/connectivity.html",
  "frontend/research-module/source_localization.html",
  "frontend/assets/research-modules/reproducibility/research_module_manifest.json",
];
const html = fs.readFileSync(path.join(root, "frontend/index.html"), "utf8");
const app = fs.readFileSync(path.join(root, "frontend/app.js"), "utf8");
const fullText = files.map((file) => `\n--- ${file} ---\n${fs.readFileSync(path.join(root, file), "utf8")}`).join("\n");
const visibleRuntimeSlices = [
  "setTextIfPresent",
  "setAllTextIfPresent",
  "setRealStatus",
  "setRealActionEnabled",
  "target.innerHTML",
  "delivery.innerHTML",
  "data-report-download",
  "recordUiAction",
  "throw new Error",
];
const appVisibleLines = app
  .split(/\r?\n/)
  .filter((line) => visibleRuntimeSlices.some((marker) => line.includes(marker)))
  .join("\n");
const text = `\n--- frontend/index.html ---\n${html}\n--- frontend/app.js visible runtime copy ---\n${appVisibleLines}`;

const bannedCustomerCopy = [
  "报告 ZIP",
  "生成报告 ZIP",
  "下载报告 ZIP",
  "运行 PSD",
  "运行 ERP",
  "运行 TFR",
  "运行 PAC",
  "计划 JSON",
  "下载 JSON",
  "Metadata QC",
  "QC 预览",
  "bad-channel audit",
  "方法分支",
  "分析任务工作台",
  "9 个模块",
  "项目 ID",
  "方法模块实验室",
  "方法开发测试试验台",
  "科研 beta 实验区",
  "Beta 方法",
  "可运行 beta",
  "真实后端任务",
  "参数回显",
  "产物证据",
  "API 服务",
  "运行 failed",
  "Workflow contract",
  "Publication preview",
  "Research Module",
  "Preview only",
  "preview only",
  "Standalone static research-module pages",
  "customer testing",
  "scientific UI review",
  "输出合同",
  "审稿风险",
  "Data preparation plan",
  "Evidence file",
  "Open reproducibility output",
  "Channel selection",
  "Search channels",
  "Select first",
  "Bad-channel reason",
  "Mark selected as bad",
  "Quality gate",
  "Plan id",
  "Current file",
  "Plan state",
  "PSD readiness",
  "ERP readiness",
  "Preview-only",
  "Confirmed revision",
  "main workflow",
  "Preview lab only",
  "production execution",
  "Current preview evidence segment",
  "测试输入数据",
  "合成科研测试数据",
];

const requiredCopy = [
  "生成交付报告",
  "下载完整报告",
  "在线预览",
  "当前可用模块",
  "当前可用：9 项分析能力",
  "预览方法，需复核",
  "进入分析项目",
  "分析方法库",
  "QC 与数据准备",
  "数据准备状态",
  "下载结果材料",
  "开始 PSD 分析",
  "开始 ERP 分析",
  "试用 TFR 时频分析（需复核）",
  "试用 Multitaper PSD（需复核）",
  "试用 Multitaper TFR（需复核）",
  "试用 Reference / CSD（需复核）",
  "试用 PAC 耦合分析（需复核）",
  "试用 Connectivity（需复核）",
  "选择分析方法后，可在结果查看中查看图表和表格，并在报告交付中下载完整材料。",
  "示例输入数据",
  "合成科研示例数据",
];

const checks = [
  ...bannedCustomerCopy.map((item) => ({
    name: `banned-copy:${item}`,
    pass: !fullText.includes(item),
  })),
  ...requiredCopy.map((item) => ({
    name: `required-copy:${item}`,
    pass: fullText.includes(item),
  })),
];

const result = {
  script: path.basename(__filename),
  checked_at: new Date().toISOString(),
  files,
  checks,
  passed: checks.every((item) => item.pass),
  evidence_path: evidencePath,
};

fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(evidencePath, `${JSON.stringify(result, null, 2)}\n`, "utf8");
console.log(JSON.stringify(result, null, 2));
if (!result.passed) process.exit(1);
