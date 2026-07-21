import fs from "node:fs";
import path from "node:path";

const ROOT = process.cwd();
const OUT_DIR = path.resolve(ROOT, "work/release_evidence/20260701-research-user-copy-governance");
const OUT_FILE = path.join(OUT_DIR, "research_user_copy_governance_result.json");

const customerFiles = [
  "frontend/index.html",
  "frontend/app.js",
  "frontend/waveform-workbench.html",
  "frontend/waveform-workbench.js",
  "frontend/epilepsy-workbench.js",
];

const requiredDocs = [
  "docs/product/qlanalyser_research_user_copy_governance_spec_20260701.md",
  "docs/product/epilepsy_sleep_terminology_contract_20260629.md",
];

const forbiddenPositiveClinicalTerms = [
  "自动诊断",
  "确诊为",
  "治疗建议",
  "临床分诊",
  "医疗决策",
  "一键诊断",
  "智能判断",
];

const forbiddenEpilepsyTerms = [
  "癫痫分期",
  "癫痫样事件分期",
  "开始分期",
  "分期波形",
];

const discouragedVisibleTerms = [
  "正在读取真实波形",
  "不会用旧窗口伪装当前数据",
  "请选择一段真实波形",
];

const discouragedExampleModeTerms = [
  "教学模式",
  "教学数据",
  "教学 EDF",
  "教学样本",
  "教学步骤",
  "结束教学",
];

const requiredPhrases = [
  "示例模式",
  "示例数据",
  "癫痫样事件初筛",
  "候选事件",
  "人工矫正",
  "科研支持",
];

function readUtf8(relPath) {
  return fs.readFileSync(path.resolve(ROOT, relPath), "utf8");
}

function collectLiteralHits(files, terms) {
  const hits = [];
  for (const file of files) {
    const text = readUtf8(file);
    const lines = text.split(/\r?\n/);
    for (const term of terms) {
      lines.forEach((line, index) => {
        if (line.includes(term)) {
          hits.push({
            file,
            line: index + 1,
            term,
            excerpt: line.trim().slice(0, 240),
          });
        }
      });
    }
  }
  return hits;
}

function isExplicitBoundaryLine(line) {
  return line.includes("不用于") || line.includes("不作为") || line.includes("不得用于") || line.includes("不能用于");
}

function collectPositiveClinicalHits(files, terms) {
  return collectLiteralHits(files, terms).filter((hit) => !isExplicitBoundaryLine(hit.excerpt));
}

function hasAny(files, phrase) {
  return files.some((file) => readUtf8(file).includes(phrase));
}

const missingDocs = requiredDocs.filter((file) => !fs.existsSync(path.resolve(ROOT, file)));
const missingPhrases = requiredPhrases.filter((phrase) => !hasAny(customerFiles, phrase) && !hasAny(requiredDocs.filter((file) => fs.existsSync(path.resolve(ROOT, file))), phrase));

const forbiddenClinicalHits = collectPositiveClinicalHits(customerFiles, forbiddenPositiveClinicalTerms);
const forbiddenEpilepsyHits = collectLiteralHits(customerFiles, forbiddenEpilepsyTerms);
const discouragedHits = collectLiteralHits(customerFiles, discouragedVisibleTerms);
const discouragedExampleModeHits = collectLiteralHits(customerFiles, discouragedExampleModeTerms);

const result = {
  script: "validate_research_user_copy_governance.mjs",
  generated_at: new Date().toISOString(),
  status: "passed",
  checked_files: customerFiles,
  required_docs: requiredDocs,
  missing_docs: missingDocs,
  missing_phrases: missingPhrases,
  forbidden_clinical_hits: forbiddenClinicalHits,
  forbidden_epilepsy_hits: forbiddenEpilepsyHits,
  discouraged_visible_hits: discouragedHits,
  discouraged_example_mode_hits: discouragedExampleModeHits,
  notes: [
    "This gate checks customer-visible source files for high-risk wording.",
    "Internal class names, test IDs, and older product docs are intentionally not swept here.",
    "Clinical terms used in explicit negative boundary copy are allowed when not matching positive patterns.",
  ],
};

const failed = [];
if (missingDocs.length) failed.push("missing_required_copy_governance_doc");
if (missingPhrases.length) failed.push("missing_required_research_user_phrase");
if (forbiddenClinicalHits.length) failed.push("forbidden_positive_clinical_terms");
if (forbiddenEpilepsyHits.length) failed.push("forbidden_epilepsy_staging_terms");
if (discouragedHits.length) failed.push("discouraged_waveform_copy_visible");
if (discouragedExampleModeHits.length) failed.push("discouraged_example_mode_copy_visible");

result.failed = failed;
result.status = failed.length ? "failed" : "passed";

fs.mkdirSync(OUT_DIR, { recursive: true });
fs.writeFileSync(OUT_FILE, `${JSON.stringify(result, null, 2)}\n`, "utf8");
console.log(JSON.stringify(result, null, 2));
if (failed.length) process.exit(1);
