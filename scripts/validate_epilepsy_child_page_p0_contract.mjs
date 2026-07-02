import fs from "node:fs";
import path from "node:path";

const ROOT = process.cwd();
const OUT_DIR = path.resolve(ROOT, "work/release_evidence/20260629-epilepsy-child-page-p0");
const OUT_FILE = path.join(OUT_DIR, "static_epilepsy_child_page_contract.json");

function read(rel) {
  return fs.readFileSync(path.resolve(ROOT, rel), "utf8");
}

function includesAll(text, items) {
  return items.every((item) => text.includes(item));
}

const app = read("frontend/app.js");
const index = read("frontend/index.html");

const checks = {
  inline_section_exists_inside_main_shell: index.indexOf('<div class="shell" id="appShell"') >= 0
    && index.indexOf('<main class="main">') >= 0
    && index.indexOf('id="epilepsyWorkbenchInline"') > index.indexOf('<main class="main">')
    && index.indexOf('id="epilepsyWorkbenchInline"') < index.indexOf('</main>'),
  inline_section_has_contract_id: includesAll(index, [
    'id="epilepsyWorkbenchInline"',
    'data-testid="main-epilepsy-workbench-inline"',
    'data-testid="inline-epilepsy-context-header"',
    'data-testid="inline-epilepsy-screening-panel"',
    'data-testid="inline-epilepsy-summary-panel"',
  ]),
  main_card_opens_inline_console_first: index.includes('data-real-action="open-epilepsy-workbench"')
    && !index.includes('data-real-action="run-epilepsy-ml"'),
  inherited_entry_switches_to_inline_view: includesAll(app, [
    "async function openEpilepsyWorkbenchFromPlan()",
    'setView("epilepsyWorkbenchInline")',
    "renderInlineEpilepsyWorkbench()",
    "plan_id: state.real.plan?.id",
    "gated: !hasConfirmedPlan()",
  ]),
  inline_renderer_exists: includesAll(app, [
    "function renderInlineEpilepsyWorkbench()",
    "dataPreparationContractVersion(plan)",
    'data-testid="inline-epilepsy-start-screening"',
    'data-real-action="run-epilepsy-ml"',
  ])
    && !app.includes("window.location.assign(url)"),
  inline_navigation_targets_main_views: includesAll(index, [
    'data-view="workflow"',
    'data-view="statistics"',
  ]) && includesAll(app, [
    'data-view-jump="workflow"',
    'data-view-jump="statistics"',
  ]),
  inline_child_view_has_parent_nav_mapping: includesAll(app, [
    "const parentViews",
    'epilepsyWorkbenchInline: "workflow"',
    'epilepsyWorkbenchInline: "癫痫样事件分析台"',
  ]),
  real_action_dispatch_runs_epilepsy_ml: app.includes('action === "run-epilepsy-ml"')
    && app.includes('runRealTask("epilepsy_ml", "epilepsy_ml_xgboost")'),
  inline_entry_label_not_question_marks: app.includes("癫痫样事件分析台")
    && app.includes("开始初筛")
    && !app.includes("开始初筛/分期")
    && !app.includes("癫痫分期")
    && !/癫痫样事件分析台[?？]/.test(app)
    && !/开始初筛[?？]/.test(app)
    && !app.includes("<span>????????????</span>"),
  inline_copy_uses_screening_not_staging: app.includes("候选事件初筛")
    && app.includes("人工矫正")
    && !app.includes("癫痫分期"),
  inline_review_label_contract: app.includes("保留候选")
    && app.includes("排除候选")
    && app.includes("需复核")
    && app.includes("display_label"),
  inline_stage_code_overlay_is_real_control: includesAll(app, [
    'data-testid="inline-epilepsy-toggle-stage"',
    "canvas.dataset.stageOverlay",
    "reader.overlayVisibility.stageCode",
    "Stage_Code",
  ]),
  inline_copy_no_old_review_labels: !app.includes("Seizure / Normal / Needs review"),
  inline_non_medical_boundary_visible: app.includes("科研支持用途，不用于诊断、确诊、治疗或临床分诊"),
  main_results_duplicate_entry_removed: !app.includes("const workbenchLink = moduleName === \"epilepsy_ml\""),
};

const failed = Object.entries(checks).filter(([, passed]) => !passed).map(([name]) => name);
const result = {
  script: "validate_epilepsy_child_page_p0_contract.mjs",
  generated_at: new Date().toISOString(),
  checks,
  failed,
  status: failed.length ? "failed" : "passed",
};

fs.mkdirSync(OUT_DIR, { recursive: true });
fs.writeFileSync(OUT_FILE, `${JSON.stringify(result, null, 2)}\n`, "utf8");
console.log(JSON.stringify(result, null, 2));
if (failed.length) process.exit(1);
