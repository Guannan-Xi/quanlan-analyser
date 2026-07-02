import fs from "node:fs";
import path from "node:path";

const ROOT = process.cwd();
const OUT_DIR = path.resolve(ROOT, "work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-copy-governance");
const OUT_FILE = path.join(OUT_DIR, "copy_governance_result.json");

function read(rel) {
  return fs.readFileSync(path.resolve(ROOT, rel), "utf8");
}

function countMatches(text, pattern) {
  const matches = text.match(new RegExp(pattern.source, `${pattern.flags.includes("g") ? pattern.flags : `${pattern.flags}g`}`));
  return matches ? matches.length : 0;
}

function collectHits(files, terms) {
  const hits = [];
  for (const file of files) {
    const text = read(file);
    const lines = text.split(/\r?\n/);
    for (const term of terms) {
      lines.forEach((line, index) => {
        if (line.includes(term)) {
          hits.push({
            file,
            line: index + 1,
            term,
            text: line.trim().slice(0, 240),
          });
        }
      });
    }
  }
  return hits;
}

const customerUiFiles = [
  "frontend/index.html",
  "frontend/app.js",
];

const app = read("frontend/app.js");
const index = read("frontend/index.html");
const e2e = read("scripts/e2e_epilepsy_cloud_trial_upload_to_export_browser.mjs");

const requiredCustomerPhrases = [
  "癫痫样事件分析台",
  "开始初筛",
  "候选事件",
  "人工矫正",
  "科研支持用途，不用于诊断、确诊、治疗或临床分诊",
];

const forbiddenCustomerTerms = [
  "癫痫分期",
  "开始分期",
  "初筛/分期",
  "诊断结论",
  "治疗建议",
  "Video unavailable",
  "当前数据无视频",
  "视频占位",
];

const forbiddenCustomerHits = collectHits(customerUiFiles, forbiddenCustomerTerms);
const indexOldLabelHits = collectHits(["frontend/index.html"], ["Seizure", "Normal", "Needs review"]);

const requiredPhraseCoverage = Object.fromEntries(
  requiredCustomerPhrases.map((phrase) => [phrase, app.includes(phrase) || index.includes(phrase)]),
);

const displayLabelChecks = {
  display_keep_candidate: app.includes("保留候选"),
  display_exclude_candidate: app.includes("排除候选"),
  display_needs_review: app.includes("需复核"),
  internal_seizure_label_mapping_exists: /Seizure[\s\S]{0,160}保留候选|保留候选[\s\S]{0,160}Seizure/.test(app),
  internal_normal_label_mapping_exists: /Normal[\s\S]{0,160}排除候选|排除候选[\s\S]{0,160}Normal/.test(app),
  internal_needs_review_label_mapping_exists: /Needs review[\s\S]{0,180}需复核|需复核[\s\S]{0,180}Needs review/.test(app),
};

const e2eGuards = {
  checks_old_labels_are_hidden: e2e.includes("no_old_labels_in_candidate_panel"),
  checks_no_epilepsy_staging_copy: e2e.includes("no_epilepsy_staging_copy"),
  checks_no_diagnosis_or_treatment_copy: e2e.includes("no_diagnosis_or_treatment_copy"),
  checks_no_video_placeholder_copy: e2e.includes("no_video_placeholder_copy"),
};

const result = {
  generated_at: new Date().toISOString(),
  status: "pending",
  scope: {
    purpose: "Epilepsy-like event screening cloud trial v0.1 customer-facing terminology gate",
    customer_ui_files: customerUiFiles,
    internal_model_labels_allowed_when_mapped: ["Seizure", "Normal", "Needs review"],
    forbidden_customer_terms: forbiddenCustomerTerms,
  },
  required_phrase_coverage: requiredPhraseCoverage,
  display_label_checks: displayLabelChecks,
  e2e_guards: e2eGuards,
  forbidden_customer_hits: forbiddenCustomerHits,
  index_old_label_hits: indexOldLabelHits,
  counts: {
    app_internal_seizure_occurrences: countMatches(app, /\bSeizure\b/g),
    app_internal_normal_occurrences: countMatches(app, /\bNormal\b/g),
    app_internal_needs_review_occurrences: countMatches(app, /Needs review/g),
  },
};

const failed = [];
for (const [key, ok] of Object.entries(requiredPhraseCoverage)) {
  if (!ok) failed.push(`missing_required_phrase:${key}`);
}
for (const [key, ok] of Object.entries(displayLabelChecks)) {
  if (!ok) failed.push(`display_label_contract:${key}`);
}
for (const [key, ok] of Object.entries(e2eGuards)) {
  if (!ok) failed.push(`missing_e2e_guard:${key}`);
}
if (forbiddenCustomerHits.length) failed.push("forbidden_customer_terms_visible");
if (indexOldLabelHits.length) failed.push("old_internal_labels_visible_in_index");

result.failed = failed;
result.status = failed.length ? "failed" : "passed";

fs.mkdirSync(OUT_DIR, { recursive: true });
fs.writeFileSync(OUT_FILE, `${JSON.stringify(result, null, 2)}\n`, "utf8");
console.log(JSON.stringify(result, null, 2));
if (failed.length) process.exit(1);
