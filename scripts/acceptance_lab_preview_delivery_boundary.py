from __future__ import annotations

import importlib
import json
import os
import sys
import tempfile
from pathlib import Path

from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def expect_http(label: str, status_code: int, code: str, fn) -> dict:
    try:
        fn()
    except HTTPException as exc:
        if exc.status_code != status_code:
            raise AssertionError(f"{label}: expected HTTP {status_code}, got {exc.status_code}: {exc.detail}") from exc
        detail = exc.detail if isinstance(exc.detail, dict) else {}
        if detail.get("code") != code:
            raise AssertionError(f"{label}: expected code {code}, got {exc.detail}") from exc
        return {"name": label, "status": "passed", "http_status": exc.status_code, "code": code}
    raise AssertionError(f"{label}: expected HTTP {status_code}")


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="qlanalyser-lab-preview-boundary-") as tmp:
        root = Path(tmp)
        os.environ["QLANALYSER_STATE_ROOT"] = str(root / "state")
        os.environ["QLANALYSER_DERIVATIVES_ROOT"] = str(root / "derivatives")

        import backend.models.analysis_task as task_model
        import backend.models.data_preparation as prep_model
        import backend.models.eeg_file as eeg_model
        import backend.models.governance as governance_model
        import backend.models.project as project_model
        import backend.models.report as report_model
        import backend.services.account_service as account_service
        import backend.services.audit_service as audit_service
        import backend.services.billing_service as billing_service
        import backend.services.data_preparation_service as data_preparation_service
        import backend.services.report_service as report_service
        import backend.services.state_store as state_store
        import backend.services.storage_service as storage_service
        import backend.services.task_service as task_service

        for module in (
            state_store,
            account_service,
            audit_service,
            billing_service,
            storage_service,
            data_preparation_service,
            task_service,
            report_service,
        ):
            importlib.reload(module)

        task_service.DERIVATIVES_ROOT = root / "derivatives"
        report_service.REPORT_ROOT = root / "reports"
        report_service.DERIVATIVES_ROOT = root / "derivatives"

        source_path = root / "uploads" / "lab-preview.edf"
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_bytes(b"fake edf; fake runner avoids parsing")

        state_store.upsert_item(
            "accounts",
            governance_model.AccountRead(
                id="owner-lab",
                email="owner-lab@example.test",
                balance_credits=100.0,
                trial_credits=0.0,
            ),
        )
        state_store.upsert_item(
            "projects",
            project_model.ProjectRead(
                id="proj_lab_preview_boundary",
                name="Lab preview delivery boundary",
                owner_user_id="owner-lab",
                created_by="owner-lab",
            ),
        )
        state_store.upsert_item(
            "eeg_files",
            eeg_model.EEGFileRead(
                id="eeg_lab_preview_boundary",
                project_id="proj_lab_preview_boundary",
                original_filename="lab-preview.edf",
                stored_path=source_path,
                detected_format="edf",
                owner_user_id="owner-lab",
                created_by="owner-lab",
                upload_authorization_confirmed=True,
                size_bytes=source_path.stat().st_size,
            ),
        )

        lab_plan = data_preparation_service.save_plan(
            prep_model.DataPreparationPlanCreate(
                project_id="proj_lab_preview_boundary",
                input_file_id="eeg_lab_preview_boundary",
                owner_user_id="owner-lab",
                created_by="owner-lab",
                status="confirmed",
                delivery_scope="lab_preview_only",
                module_scope=["psd", "erp", "qc"],
                metadata_review={"reviewed_in": "module-lab", "status": "accepted_for_lab_preview"},
                artifact_contract_json={"producer": "module-lab", "delivery_scope": "lab_preview_only"},
            )
        )

        checks = [
            expect_http(
                "formal task rejects lab-preview data preparation plan",
                422,
                "LAB_PREVIEW_PLAN_NOT_FORMAL_DELIVERY",
                lambda: task_service.create_task(
                    task_model.AnalysisTaskCreate(
                        project_id="proj_lab_preview_boundary",
                        input_file_id="eeg_lab_preview_boundary",
                        module_name="psd",
                        workflow_id="resting_psd",
                        owner_user_id="owner-lab",
                        created_by="owner-lab",
                        parameters_json={
                            "data_preparation_plan_id": lab_plan.id,
                            "data_preparation_revision": lab_plan.revision,
                        },
                    ),
                    requesting_user_id="owner-lab",
                ),
            )
        ]

        def fake_psd_runner(input_path, output_dir, parameters=None):
            output = Path(output_dir)
            output.mkdir(parents=True, exist_ok=True)
            result = output / "result.json"
            result.write_text(json.dumps({"status": "ok", "parameters": parameters or {}}) + "\n", encoding="utf-8")
            return {"result": result}

        task_service.run_psd = fake_psd_runner
        task = task_service.create_task(
            task_model.AnalysisTaskCreate(
                project_id="proj_lab_preview_boundary",
                input_file_id="eeg_lab_preview_boundary",
                module_name="psd",
                workflow_id="resting_psd",
                owner_user_id="owner-lab",
                created_by="owner-lab",
                parameters_json={
                    "lab_preview_run": True,
                    "data_preparation_plan_id": lab_plan.id,
                    "data_preparation_revision": lab_plan.revision,
                },
            ),
            requesting_user_id="owner-lab",
        )
        if task.status != "completed" or not task.parameters_json.get("lab_preview_run"):
            raise AssertionError(f"lab preview task did not complete as preview: {task}")
        checks.append({"name": "lab-preview task can run with explicit preview marker", "status": "passed"})

        audit_service.record_event(
            action="result.reviewed",
            object_type="analysis_task",
            object_id=task.id,
            project_id=task.project_id,
            actor_user_id="owner-lab",
        )
        checks.append(
            expect_http(
                "default report rejects lab-preview task",
                422,
                "LAB_PREVIEW_TASK_NOT_REPORTABLE",
                lambda: report_service.create_report(
                    report_model.ReportCreate(
                        project_id=task.project_id,
                        task_id=task.id,
                        title="Should be blocked",
                        owner_user_id="owner-lab",
                        created_by="owner-lab",
                    )
                ),
            )
        )

        print(json.dumps({"status": "passed", "checks": checks}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
