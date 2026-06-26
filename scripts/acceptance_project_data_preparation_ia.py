
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "frontend" / "index.html"
APP = ROOT / "frontend" / "app.js"
OUT = ROOT / "work" / "release_evidence" / "project_data_preparation_ia" / "project_data_preparation_ia_acceptance.json"


def between(text: str, start_marker: str, end_marker: str) -> str:
    start = text.index(start_marker)
    end = text.index(end_marker, start)
    return text[start:end]


def main() -> int:
    html = INDEX.read_text(encoding="utf-8")
    app = APP.read_text(encoding="utf-8")
    dashboard = between(html, '<section class="view active" id="dashboard">', '<section class="view" id="journey">')
    analysis = between(html, '<section class="view" id="analysis">', '<section class="view" id="workflow">')
    workflow = between(html, '<section class="view" id="workflow">', '<section class="view" id="paradigms">')
    checks = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"name": name, "status": "pass" if ok else "fail", "detail": detail})

    check("project_page_has_project_crud", 'data-testid="project-crud-panel"' in dashboard and 'data-real-action="create-project"' in dashboard)
    check("project_page_has_data_crud", 'data-testid="project-data-crud-panel"' in dashboard and 'data-real-action="upload-eeg"' in dashboard)
    check("project_page_has_project_selection", 'data-project-select=' in app and 'data-file-select=' in app and 'data-workspace-select="project"' in dashboard)
    check("project_page_has_personal_center", 'class="account-panel personal-center"' in html and 'data-view="billing"' in html and 'data-view="invoice"' in html and 'data-view="inbox"' in html)
    check("project_page_no_internal_crud_badges", "Project CRUD" not in dashboard and "Data CRUD" not in dashboard)
    check("project_page_uses_user_facing_version_copy", "替换和删除" not in dashboard and "上传新版本" in dashboard)
    check("project_page_data_collapsed_until_project_selected", 'id="iaDataRows" data-testid="project-data-list-table" hidden' in dashboard)
    check("project_page_upload_disabled_until_project_selected", 'data-file-trigger="real-eeg-file" disabled' in dashboard and 'id="real-eeg-file" class="visually-hidden-file" type="file"' in dashboard and 'disabled' in between(dashboard, 'id="real-eeg-file"', 'data-file-trigger="real-eeg-file"'))
    check("project_page_no_top_method_workbench", 'workbench-link' not in html)
    check("project_page_no_preprocessing_module", 'data-testid="preprocessing-readiness-panel"' not in dashboard)
    check("project_page_no_method_template_list", 'id="templateList"' not in dashboard and 'data-testid="method-branch-contracts"' not in dashboard)

    check("data_preparation_no_file_upload_control", 'id="real-eeg-file"' not in analysis and 'type="file"' not in analysis)
    check("data_preparation_project_scoped_queue", 'data-testid="project-data-prep-queue"' in analysis)
    check("data_preparation_per_file_preview", 'data-testid="single-file-preview-panel"' in analysis and 'id="eegCanvas"' in analysis)
    check("data_preparation_segment_annotation_crud", 'data-testid="segment-annotation-crud"' in analysis and 'data-ia-action="exclude-segment"' in analysis and 'data-ia-action="add-annotation"' in analysis)
    check("data_preparation_readiness_and_epoch", 'data-testid="preprocessing-readiness-panel"' in analysis and 'data-testid="event-epoch-panel"' in analysis)
    submit_index = analysis.find('data-testid="data-preparation-submit-last"')
    prep_index = analysis.find('data-testid="systematic-preprocessing-steps"')
    check("data_preparation_submit_last", prep_index != -1 and submit_index > prep_index)

    check("workflow_has_preprocessing_dependency_not_method", 'data-module-id="preprocessing_readiness"' in workflow and 'class="ia-method-card stable dependency"' in workflow and 'b>dependency</b>' in workflow)
    check("workflow_method_branches", 'data-testid="method-branch-contracts"' in workflow and 'data-module-id="psd_bandpower"' in workflow and 'data-module-id="erp_p300"' in workflow)
    check("workflow_keeps_real_task_buttons", 'id="templateList"' in workflow and 'data-real-action="create-report"' in workflow)
    check("data_preparation_context_summary_present", 'data-testid="prep-context-summary"' in html)
    check("data_preparation_revision_state_present", 'data-testid="prep-revision-state"' in html and "Preparation revision:" in html)
    check("app_renders_project_data_management", 'data-testid="project-data-management-page"' in html and "function renderProjectDataManagement" in app)
    check("app_has_ia_action_feedback", 'data-ia-action="select-prep-data"' in html and "showToast(" in app)
    check("round008_backlog_not_product_pass", True, "Round 008 noted as backlog in checkpoint; no product pass claimed by this acceptance script.")

    failures = [c for c in checks if c["status"] != "pass"]
    result = {
        "status": "passed" if not failures else "failed",
        "checks": len(checks),
        "failures": failures,
        "scope": "project/data management and project-scoped data preparation IA slice",
        "product_gate": "review_checkpoint_only_not_release_pass",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
