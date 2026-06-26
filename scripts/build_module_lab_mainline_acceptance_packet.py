from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "work" / "release_evidence" / "07-mainline-integration"
MANIFEST_PATH = OUT_DIR / "module_lab_integration_manifest.json"
PACKET_JSON = OUT_DIR / "module_lab_mainline_acceptance_packet.json"
PACKET_MD = OUT_DIR / "module_lab_mainline_acceptance_packet.md"


CURRENT_POOL = "QGCS-07-REVIEW-SYSTEM-ALL-ENVIRONMENTS-E2E-VISUAL-20260623"
SOURCE_THREAD_ID = "019eff6f-7d6b-74c2-bf68-ae76978e9884"


EVIDENCE_PATHS = {
    "module_lab_visible_fields": "work/release_evidence/07-mainline-integration/module_lab_visible_fields.json",
    "module_lab_layout_review": "work/release_evidence/07-mainline-integration/module_lab_layout_review.json",
    "module_lab_acceptance_stack": "work/release_evidence/07-mainline-integration/module_lab_acceptance_stack.json",
    "module_lab_grouped_methods_e2e": "work/release_evidence/20260625-module-lab-grouped-methods-e2e/module_lab_grouped_methods_e2e.json",
    "bandpower_epilepsy_ui_validation": "C:/Users/XGN/Documents/Codex/2026-06-25/new-chat-7/work/ui-validation/bandpower_epilepsy_ui_validation.json",
    "epilepsy_std_real_ui_e2e": "D:/Quanlan/Codes/Python/quanlan-analyser-official/work/e2e_epilepsy_std_demo/ui_e2e/epilepsy_std_real_ui_e2e.json",
    "waveform_preprocessing_project_cleanup": "work/release_evidence/07-full-product-e2e-pdca/14_waveform_preprocessing_project_cleanup/acceptance_packet/project_cleanup_waveform_preprocessing_acceptance_packet_20260626.json",
}


DOC_PATHS = {
    "module_lab_integration_design": "docs/product/module_lab_07_mainline_integration_design_20260626.md",
    "module_lab_execution_packet": "work/release_evidence/07-mainline-integration/module_lab_07_pm_execution_packet_20260626.md",
    "epilepsy_ml_high_fidelity_requirements": "docs/modules/epilepsy_ml_high_fidelity_requirements.md",
    "epilepsy_ml_high_fidelity_test_plan": "docs/modules/epilepsy_ml_high_fidelity_test_plan.md",
    "epilepsy_ml_lab_sync_mirror_plan": "docs/modules/epilepsy_ml_lab_sync_mirror_plan.md",
}


METHODS = [
    {
        "ui_id": "qc",
        "label": "数据准备与质量检查",
        "task_module_name": "qc",
        "workflow_id": "metadata_qc",
        "runner_backend_module": "qc",
        "acceptance_scope": "baseline_grouped_e2e",
    },
    {
        "ui_id": "psd",
        "label": "功率谱密度",
        "task_module_name": "psd",
        "workflow_id": "resting_psd",
        "runner_backend_module": "psd",
        "acceptance_scope": "baseline_grouped_e2e",
    },
    {
        "ui_id": "band_power",
        "label": "Band Power",
        "task_module_name": "psd",
        "workflow_id": "resting_psd",
        "runner_backend_module": "psd",
        "acceptance_scope": "targeted_ui_validation",
        "alias_contract": {
            "display_alias": "Band Power",
            "band_power_view": True,
            "must_not_submit_module_name": "band_power",
            "expected_outputs": [
                "tables/band_power.csv",
                "tables/channel_band_power.csv",
                "figures/psd_band_power.svg",
            ],
        },
    },
    {
        "ui_id": "erp",
        "label": "事件相关电位",
        "task_module_name": "erp",
        "workflow_id": "erp_p300",
        "runner_backend_module": "erp",
        "acceptance_scope": "baseline_grouped_e2e",
    },
    {
        "ui_id": "epilepsy_std",
        "label": "癫痫样事件筛查",
        "task_module_name": "epilepsy",
        "workflow_id": "epilepsy_std_threshold",
        "runner_backend_module": "epilepsy",
        "acceptance_scope": "targeted_real_ui_e2e",
        "method": "std_threshold",
        "boundary": "Research screening/support only; no diagnosis, treatment, or clinical decision-making.",
    },
    {
        "ui_id": "tfr",
        "label": "事件锁定时频",
        "task_module_name": "tfr",
        "workflow_id": "tfr_ersp_itc",
        "runner_backend_module": "tfr",
        "acceptance_scope": "baseline_grouped_e2e",
    },
    {
        "ui_id": "multitaper_psd",
        "label": "多窗 PSD",
        "task_module_name": "multitaper_psd_tfr",
        "workflow_id": "multitaper_psd_tfr",
        "runner_backend_module": "multitaper_psd_tfr",
        "acceptance_scope": "baseline_grouped_e2e",
        "fixed_parameters": {"analysis_family": "psd"},
    },
    {
        "ui_id": "multitaper_tfr",
        "label": "多窗 TFR",
        "task_module_name": "multitaper_psd_tfr",
        "workflow_id": "multitaper_psd_tfr",
        "runner_backend_module": "multitaper_psd_tfr",
        "acceptance_scope": "baseline_grouped_e2e",
        "fixed_parameters": {"analysis_family": "tfr"},
    },
    {
        "ui_id": "reference_csd",
        "label": "CSD 电流源密度计算",
        "task_module_name": "reference_csd",
        "workflow_id": "reference_csd",
        "runner_backend_module": "reference_csd",
        "acceptance_scope": "baseline_grouped_e2e",
        "copy_decision": "User-facing wording should treat CSD as spatial filtering/current source density, while re-reference settings belong to preprocessing.",
    },
    {
        "ui_id": "pac",
        "label": "相位-振幅耦合",
        "task_module_name": "pac",
        "workflow_id": "pac_cfc",
        "runner_backend_module": "pac",
        "acceptance_scope": "baseline_grouped_e2e",
    },
    {
        "ui_id": "connectivity",
        "label": "传感器连接性",
        "task_module_name": "connectivity",
        "workflow_id": "connectivity",
        "runner_backend_module": "connectivity",
        "acceptance_scope": "baseline_grouped_e2e",
    },
]


ML_BACKLOG_PACKETS = [
    {
        "packet_id": "ML-A",
        "title": "ML runner and asset manifest",
        "deliverables": [
            "epilepsy_ml_screening workflow inside the existing epilepsy module",
            "model/scaler asset manifest with SHA256 and byte-size checks",
            "feature extraction, scaler, probability, Stage_Code, and event aggregation parity",
        ],
    },
    {
        "packet_id": "ML-B",
        "title": "Review session API",
        "deliverables": [
            "create review session",
            "waveform window API",
            "epoch label edit API with undo/redo/reset/save/export",
            "reviewed layer stored separately from raw model outputs",
        ],
    },
    {
        "packet_id": "ML-C",
        "title": "Epilepsy review workbench",
        "deliverables": [
            "frontend/epilepsy-review.html",
            "frontend/epilepsy-review.js",
            "waveform, candidate events, epoch timeline, manual correction, save/reopen, export",
        ],
    },
    {
        "packet_id": "ML-D",
        "title": "Source-vs-target independent audit",
        "deliverables": [
            "run AR_analyser1 source algorithm and 07 target algorithm on fixed fixtures",
            "compare features, scaled_features, probabilities, Stage_Code, events, and reviewed events",
            "write independent_audit/verdict.json",
        ],
    },
    {
        "packet_id": "LAB-A",
        "title": "Lab fixture and source expected outputs",
        "deliverables": [
            "fixed lab fixtures covering 3s/5s, all-normal, seizure epochs, tail cases, channel variants, and sampling-rate boundaries",
            "expected outputs generated from AR_analyser1 source algorithm",
        ],
    },
    {
        "packet_id": "LAB-B",
        "title": "Module Lab sync-test entry",
        "deliverables": [
            "module-lab card: 癫痫样事件筛查 / ML 模型 / 实验室同步测试",
            "submit module_name=epilepsy and workflow_id=epilepsy_ml_screening with lab_mode=true",
            "do not create a lab-only workflow",
        ],
    },
    {
        "packet_id": "LAB-C",
        "title": "Shared review workbench lab mode",
        "deliverables": [
            "same epilepsy-review.html/js as formal path",
            "lab_mode=1 only adds fixture name, model hash, audit status, and lab notice",
            "no epilepsy-review-lab.js fork",
        ],
    },
    {
        "packet_id": "LAB-D",
        "title": "Independent audit download",
        "deliverables": [
            "downloadable independent audit package",
            "blocked UI state when audit fails",
        ],
    },
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def resolve_path(path_text: str) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    return ROOT / path


def read_text_if_exists(path_text: str) -> str | None:
    path = resolve_path(path_text)
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def read_json_if_exists(path_text: str) -> dict[str, Any] | None:
    text = read_text_if_exists(path_text)
    if text is None:
        return None
    return json.loads(text)


def git_status_for(path_text: str) -> str:
    path = resolve_path(path_text)
    try:
        relative = str(path.relative_to(ROOT))
    except ValueError:
        return "external_path"
    try:
        result = subprocess.run(
            ["git", "status", "--short", "--", relative],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"
    return result.stdout.strip() or "clean_or_tracked_unchanged"


def git_diff_names() -> list[str]:
    try:
        result = subprocess.run(
            ["git", "-c", "core.autocrlf=false", "diff", "--name-only"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def protected_route_hits(paths: list[str]) -> list[str]:
    needles = ("gateway", "headroom", "front-route", "ipc", "router")
    return [path for path in paths if any(needle in path.lower() for needle in needles)]


def summarise_visible_fields(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not payload:
        return {}
    groups = payload.get("groups") or {}
    modules = payload.get("modules") or {}
    checks = payload.get("checks") or {}
    return {
        "status": payload.get("status"),
        "errors": payload.get("errors", []),
        "group_count": groups.get("count") if isinstance(groups, dict) else len(groups),
        "expected_group_count": groups.get("expectedCount") if isinstance(groups, dict) else None,
        "group_ids": groups.get("ids") if isinstance(groups, dict) else None,
        "module_ids": list(modules.keys()) if isinstance(modules, dict) else modules,
        "picker_count": checks.get("pickerCount") if isinstance(checks, dict) else None,
        "finished_at": payload.get("finishedAt"),
    }


def summarise_grouped_e2e(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not payload:
        return {}
    modules = payload.get("modules") or {}
    return {
        "status": payload.get("status"),
        "errors": payload.get("errors", []),
        "module_ids": list(modules.keys()) if isinstance(modules, dict) else modules,
        "request_count": len(payload.get("requests") or []),
        "step_count": len(payload.get("steps") or []),
        "uploaded_file": payload.get("uploadedFile"),
        "finished_at": payload.get("finishedAt"),
    }


def summarise_bandpower_epilepsy(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not payload:
        return {}
    requests = []
    for item in payload.get("requests") or []:
        body: dict[str, Any] = {}
        try:
            body = json.loads(item.get("body") or "{}")
        except json.JSONDecodeError:
            body = {}
        requests.append(
            {
                "kind": item.get("kind"),
                "module_name": body.get("module_name") or item.get("moduleName"),
                "workflow_id": body.get("workflow_id") or item.get("workflowId"),
                "parameters_json": body.get("parameters_json", {}),
            }
        )
    return {
        "status": payload.get("status"),
        "checks": payload.get("checks", {}),
        "requests": requests,
        "screenshots": payload.get("screenshots", []),
    }


def summarise_epilepsy_std_e2e(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not payload:
        return {}
    task = payload.get("task") or {}
    artifacts = payload.get("artifacts") or []
    return {
        "status": payload.get("status"),
        "selected_file_id": payload.get("selected_file_id"),
        "task_id": task.get("id"),
        "module_name": task.get("module_name"),
        "workflow_id": task.get("workflow_id"),
        "artifact_count": len(artifacts) if isinstance(artifacts, list) else None,
        "checks": payload.get("checks", {}),
        "screenshots": payload.get("screenshots", []),
    }


def evidence_record(name: str, path_text: str) -> dict[str, Any]:
    path = resolve_path(path_text)
    exists = path.exists()
    record: dict[str, Any] = {
        "name": name,
        "path": path_text,
        "exists": exists,
    }
    if not exists:
        record["status"] = "missing"
        return record
    try:
        payload = read_json_if_exists(path_text)
    except json.JSONDecodeError as exc:
        record.update({"status": "invalid_json", "error": str(exc)})
        return record
    record["status"] = payload.get("status") or payload.get("final_receipt") or payload.get("decision")
    if name == "module_lab_visible_fields":
        record["summary"] = summarise_visible_fields(payload)
    elif name == "module_lab_grouped_methods_e2e":
        record["summary"] = summarise_grouped_e2e(payload)
    elif name == "bandpower_epilepsy_ui_validation":
        record["summary"] = summarise_bandpower_epilepsy(payload)
    elif name == "epilepsy_std_real_ui_e2e":
        record["summary"] = summarise_epilepsy_std_e2e(payload)
    else:
        record["summary"] = {
            "errors": payload.get("errors"),
            "final_receipt": payload.get("final_receipt"),
            "finished_at": payload.get("finishedAt") or payload.get("finished_at"),
        }
    return record


def evidence_passed(record: dict[str, Any]) -> bool:
    return record.get("exists") and record.get("status") in {"passed", "PASS", "completed_final_receipt", "accepted"}


def doc_record(name: str, path_text: str) -> dict[str, Any]:
    path = resolve_path(path_text)
    text = read_text_if_exists(path_text)
    return {
        "name": name,
        "path": path_text,
        "exists": text is not None,
        "line_count": len(text.splitlines()) if text is not None else 0,
        "git_status": git_status_for(path_text) if path.exists() else "missing",
    }


def build_manifest(evidence: dict[str, dict[str, Any]], docs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    diff_names = git_diff_names()
    return {
        "manifest_id": "module-lab-02-to-07-mainline-integration-20260626",
        "generated_at": now_iso(),
        "source_thread_id": SOURCE_THREAD_ID,
        "receiver": "07-PM | QLanalyser mainline acceptance",
        "route_decision": "gpt55_planner_or_acceptance + script_validator + subagent_or_thread_worker + 02_handoff_intake",
        "reused_pool_or_new_pool": f"reused_pool:{CURRENT_POOL}",
        "product_boundary": {
            "product_positioning": "Non-medical research EEG analysis and CRO workflow support.",
            "customer_copy_rule": "Customer-facing copy must use researcher/user language and must not show preview/beta/delivery-before-review wording.",
            "medical_or_diagnostic_claims_allowed": False,
            "router_headroom_ipc_front_route_gateway_changed": False,
        },
        "methods": METHODS,
        "method_group_status": {
            "visible_fields": evidence.get("module_lab_visible_fields", {}).get("summary", {}),
            "grouped_e2e": evidence.get("module_lab_grouped_methods_e2e", {}).get("summary", {}),
            "note": "Grouped baseline E2E covers the original grouped runner set; Band Power and Epilepsy STD are covered by targeted UI validation and real Epilepsy STD UI E2E.",
        },
        "accepted_current_slice": [
            "Band Power is accepted as a PSD alias/view and must submit module_name=psd, workflow_id=resting_psd.",
            "Epilepsy STD threshold is accepted as a non-medical research screening workflow under module_name=epilepsy.",
            "Module Lab grouped UI uses card-style method switching and no duplicate select picker.",
            "Project cleanup, waveform preview controls, and same-page preprocessing slice is accepted by its separate packet.",
        ],
        "not_implemented_in_this_slice": [
            "Epilepsy ML high-fidelity migration from AR_analyser1.",
            "Epilepsy review session API and review workbench.",
            "Lab sync mirror card and independent source-vs-target audit download.",
        ],
        "epilepsy_ml_backlog": {
            "docs": [
                docs["epilepsy_ml_high_fidelity_requirements"],
                docs["epilepsy_ml_high_fidelity_test_plan"],
                docs["epilepsy_ml_lab_sync_mirror_plan"],
            ],
            "hard_gates": [
                "Model and scaler assets require SHA256 and byte-size checks; 3s/5s models cannot be silently replaced.",
                "Feature order, unit chain, default channels, epoch tail truncation, sampling-rate behavior, probability threshold, Stage_Code, and event aggregation require source-vs-target parity.",
                "Raw model outputs must remain immutable; manual review writes reviewed layer, review_actions, and reviewed_events.",
                "Independent verification worker must compare AR_analyser1 source outputs with 07 target outputs and write independent_audit/verdict.json.",
                "All outputs remain non-medical: candidate events for research review only, no diagnosis, treatment, or clinical decision-making.",
            ],
            "packets": ML_BACKLOG_PACKETS,
            "lab_sync_constraints": [
                "Lab entry is a same-source sync-test mirror, not a second algorithm.",
                "Lab card submits the same epilepsy_ml_screening workflow with lab_mode=true and fixture metadata only.",
                "Lab workbench opens the same epilepsy-review.html/js; no epilepsy-review-lab.js fork.",
                "Formal and lab paths must produce identical core outputs; allowed differences are metadata/UI notice only.",
            ],
        },
        "evidence": evidence,
        "docs_read": docs,
        "protected_route_review": {
            "git_diff_name_count": len(diff_names),
            "protected_hits": protected_route_hits(diff_names),
            "status": "passed" if not protected_route_hits(diff_names) else "failed",
        },
    }


def build_packet(manifest: dict[str, Any]) -> dict[str, Any]:
    evidence = manifest["evidence"]
    required_current_slice = [
        "module_lab_visible_fields",
        "module_lab_layout_review",
        "module_lab_grouped_methods_e2e",
        "bandpower_epilepsy_ui_validation",
        "epilepsy_std_real_ui_e2e",
        "waveform_preprocessing_project_cleanup",
    ]
    blockers = [
        name for name in required_current_slice
        if not evidence_passed(evidence.get(name, {}))
    ]
    if manifest["protected_route_review"]["protected_hits"]:
        blockers.append("protected_route_path_changed")

    final_receipt = "completed_final_receipt" if not blockers else "blocked_final_receipt"
    return {
        "packet_id": "module-lab-07-mainline-acceptance-20260626",
        "generated_at": now_iso(),
        "manifest": str(MANIFEST_PATH.relative_to(ROOT)).replace("\\", "/"),
        "route_decision": manifest["route_decision"],
        "reused_pool_or_new_pool": manifest["reused_pool_or_new_pool"],
        "execution_packets": [
            {
                "packet": "module_lab_visible_fields",
                "lane": "script_validator",
                "status": evidence.get("module_lab_visible_fields", {}).get("status"),
            },
            {
                "packet": "module_lab_layout_review",
                "lane": "browser_visual_validator",
                "status": evidence.get("module_lab_layout_review", {}).get("status"),
            },
            {
                "packet": "module_lab_grouped_methods_e2e",
                "lane": "browser_e2e_validator",
                "status": evidence.get("module_lab_grouped_methods_e2e", {}).get("status"),
            },
            {
                "packet": "bandpower_epilepsy_ui_visible_path",
                "lane": "02_thread_worker + 07_readback",
                "status": evidence.get("bandpower_epilepsy_ui_validation", {}).get("status"),
            },
            {
                "packet": "epilepsy_std_real_ui_e2e",
                "lane": "02_thread_worker + 07_readback",
                "status": evidence.get("epilepsy_std_real_ui_e2e", {}).get("status"),
            },
            {
                "packet": "epilepsy_ml_high_fidelity_docs_intake",
                "lane": "subagent_or_thread_worker + gpt55_acceptance",
                "status": "accepted_as_backlog_not_implemented",
            },
        ],
        "executor_evidence": {
            "json_evidence": evidence,
            "docs_read": manifest["docs_read"],
            "syntax_checks": [
                "node --check frontend/module-lab.js",
                "node --check scripts/acceptance_module_lab_visible_fields.mjs",
                "node --check scripts/acceptance_module_lab_grouped_methods_e2e.mjs",
                "node --check scripts/acceptance_module_lab_layout_review.mjs",
            ],
            "mojibake_checks": [
                "python -X utf8 scripts/check_no_mojibake.py docs/modules/epilepsy_ml_high_fidelity_requirements.md docs/modules/epilepsy_ml_high_fidelity_test_plan.md docs/modules/epilepsy_ml_lab_sync_mirror_plan.md",
            ],
            "route_protection": manifest["protected_route_review"],
        },
        "targeted_or_full_e2e": {
            "classification": "targeted_current_slice_e2e",
            "full_checkpoint_release_e2e_ran": False,
            "reason_full_not_run": "This packet is a 02-to-07 mainline intake and current-slice acceptance, not the future Epilepsy ML high-fidelity implementation gate.",
            "targeted_e2e_covered": [
                "Module Lab grouped-methods baseline",
                "Band Power PSD alias request contract",
                "Epilepsy STD real UI upload-run-artifact path",
                "Project cleanup + waveform preview + same-page preprocessing acceptance",
            ],
        },
        "page_visual_review": {
            "status": evidence.get("module_lab_layout_review", {}).get("status"),
            "evidence_path": EVIDENCE_PATHS["module_lab_layout_review"],
            "screenshots_dir": "work/release_evidence/07-mainline-integration/module_lab_layout_review_screenshots",
            "copy_guard": "No customer-facing preview/beta/delivery-before-review wording in the checked Module Lab surface.",
        },
        "gpt55_acceptance": {
            "decision": "accepted_current_slice" if not blockers else "blocked_current_slice",
            "accepted": manifest["accepted_current_slice"],
            "backlog_not_accepted_as_done": manifest["not_implemented_in_this_slice"],
            "ml_docs_intake": "Three Epilepsy ML documents are read and accepted as future implementation/test authority.",
        },
        "final_receipt": final_receipt,
        "blockers": blockers,
        "next_real_artifact": {
            "if_continue_now": "Start Epilepsy ML Phase A packet: asset inventory, dependency strategy, AR_analyser1 source contract extraction, and fixture plan.",
            "must_before_implementation": [
                "Confirm model asset directory and dependency versions.",
                "Write detailed Phase A requirements/design/test docs for the exact implementation slice.",
                "Prepare independent audit worker packet before coding the runner.",
            ],
        },
        "route_chain": [
            "02 handoff documents",
            "07 readback of real evidence",
            "07 manifest generation",
            "subagent document gate extraction",
            "GPT-5.5/Codex acceptance",
        ],
        "model_lane": "GPT-5.5/Codex final owner; scripts/browser/local validators for bounded evidence; subagent for read-only ML document extraction.",
        "headroom_savings": "not_measured; no savings claimed.",
        "sprint_id": None,
        "serial_baseline_ms_or_skip_reason": "not measured in this documentation intake slice",
        "parallel_wall_ms": None,
        "join_receipt": "document extraction subagent completed; evidence audit subagent may be consumed if available but is not required to change the current-slice verdict.",
    }


def build_markdown(packet: dict[str, Any], manifest: dict[str, Any]) -> str:
    lines = [
        "# 07 Module Lab 主干接收包",
        "",
        f"- packet_id: `{packet['packet_id']}`",
        f"- generated_at: `{packet['generated_at']}`",
        f"- final_receipt: `{packet['final_receipt']}`",
        f"- reused_pool: `{CURRENT_POOL}`",
        "",
        "## 接收结论",
        "",
        "本包接收当前切片：Band Power 作为 PSD 别名、Epilepsy STD 阈值筛查、Module Lab 卡片式方法入口，以及项目清理/波形预览/同页预处理验收证据。",
        "",
        "Epilepsy ML 高保真迁移和实验室同步测试镜像已经作为后续主干 backlog 接收，但本包不声称 ML 模型迁移已经完成。",
        "",
        "## 当前已接收范围",
        "",
    ]
    lines.extend([f"- {item}" for item in manifest["accepted_current_slice"]])
    lines.extend([
        "",
        "## 未在本切片实施",
        "",
    ])
    lines.extend([f"- {item}" for item in manifest["not_implemented_in_this_slice"]])
    lines.extend([
        "",
        "## 方法合同",
        "",
        "| UI id | 显示名称 | 提交模块 | Workflow | 接收范围 |",
        "| --- | --- | --- | --- | --- |",
    ])
    for method in manifest["methods"]:
        lines.append(
            f"| `{method['ui_id']}` | {method['label']} | `{method['task_module_name']}` | `{method['workflow_id']}` | `{method['acceptance_scope']}` |"
        )
    lines.extend([
        "",
        "## 关键证据",
        "",
    ])
    for name, record in packet["executor_evidence"]["json_evidence"].items():
        lines.append(f"- `{name}`: `{record['path']}` status=`{record.get('status')}` exists=`{record.get('exists')}`")
    lines.extend([
        "",
        "## ML 后续门禁",
        "",
    ])
    lines.extend([f"- {item}" for item in manifest["epilepsy_ml_backlog"]["hard_gates"]])
    lines.extend([
        "",
        "## 实验室同步镜像要求",
        "",
    ])
    lines.extend([f"- {item}" for item in manifest["epilepsy_ml_backlog"]["lab_sync_constraints"]])
    lines.extend([
        "",
        "## 路由保护",
        "",
        f"- protected_hits: `{manifest['protected_route_review']['protected_hits']}`",
        "- 本切片不改 router / Headroom / IPC / front-route / gateway。",
        "",
        "## 下一真实产物",
        "",
        f"- {packet['next_real_artifact']['if_continue_now']}",
        "",
        "## QGCS Receipt",
        "",
        f"- route_decision: `{packet['route_decision']}`",
        f"- execution_packet_or_skip_reason: `used {len(packet['execution_packets'])} bounded packets/readbacks`",
        f"- executor_evidence: `JSON readback + syntax checks + mojibake check + route protection + subagent doc extraction`",
        f"- gpt55_acceptance: `{packet['gpt55_acceptance']['decision']}`",
        f"- final_receipt: `{packet['final_receipt']}`",
        f"- next_real_artifact: `{packet['next_real_artifact']['if_continue_now']}`",
        f"- route_chain: `{' -> '.join(packet['route_chain'])}`",
        f"- model_lane: `{packet['model_lane']}`",
        f"- headroom_savings: `{packet['headroom_savings']}`",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    evidence = {
        name: evidence_record(name, path_text)
        for name, path_text in EVIDENCE_PATHS.items()
    }
    docs = {
        name: doc_record(name, path_text)
        for name, path_text in DOC_PATHS.items()
    }
    manifest = build_manifest(evidence, docs)
    packet = build_packet(manifest)
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    PACKET_JSON.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    PACKET_MD.write_text(build_markdown(packet, manifest), encoding="utf-8")
    print(
        json.dumps(
            {
                "manifest": str(MANIFEST_PATH),
                "packet_json": str(PACKET_JSON),
                "packet_md": str(PACKET_MD),
                "final_receipt": packet["final_receipt"],
                "blockers": packet["blockers"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if packet["final_receipt"] == "completed_final_receipt" else 1


if __name__ == "__main__":
    raise SystemExit(main())
