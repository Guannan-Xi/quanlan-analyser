from __future__ import annotations

import importlib
import json
import os
import sys
import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _expect_http(label: str, status_code: int, fn) -> None:
    try:
        fn()
    except HTTPException as exc:
        if exc.status_code != status_code:
            raise AssertionError(f"{label}: expected HTTP {status_code}, got {exc.status_code}") from exc
        return
    raise AssertionError(f"{label}: expected HTTP {status_code}")


def _load_count(state_store, registry: str, model_type) -> int:
    return len(state_store.load_registry(registry, model_type))


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="qlanalyser-task-guards-") as tmp:
        root = Path(tmp)
        os.environ["QLANALYSER_STATE_ROOT"] = str(root / "state")
        os.environ["QLANALYSER_DERIVATIVES_ROOT"] = str(root / "derivatives")

        import backend.models.analysis_task as task_model
        import backend.models.artifact as artifact_model
        import backend.models.data_preparation as prep_model
        import backend.models.eeg_file as eeg_model
        import backend.models.governance as governance_model
        import backend.models.project as project_model
        import backend.api.artifacts as artifacts_api
        import backend.api.projects as projects_api
        import backend.api.tasks as tasks_api
        import backend.services.account_service as account_service
        import backend.services.billing_service as billing_service
        import backend.services.data_preparation_service as data_preparation_service
        import backend.services.quota_service as quota_service
        import backend.services.state_store as state_store
        import backend.services.storage_service as storage_service
        import backend.services.task_service as task_service

        for module in (
            state_store,
            account_service,
            artifacts_api,
            projects_api,
            tasks_api,
            billing_service,
            quota_service,
            storage_service,
            data_preparation_service,
            task_service,
        ):
            importlib.reload(module)

        task_service.DERIVATIVES_ROOT = root / "derivatives"
        artifacts_api._DERIVATIVES_ROOT = (root / "derivatives").resolve()
        projects_api._DERIVATIVES_ROOT = (root / "derivatives").resolve()
        tasks_api._DERIVATIVES_ROOT = (root / "derivatives").resolve()
        (root / "uploads").mkdir(parents=True, exist_ok=True)
        source_path = root / "uploads" / "shared-teaching.edf"
        source_path.write_bytes(b"not a real edf; fake runner avoids parsing")

        state_store.upsert_item(
            "accounts",
            governance_model.AccountRead(
                id="owner-a",
                email="owner-a@example.test",
                balance_credits=100.0,
                trial_credits=0.0,
            ),
        )
        state_store.upsert_item(
            "accounts",
            governance_model.AccountRead(
                id="owner-b",
                email="owner-b@example.test",
                balance_credits=100.0,
                trial_credits=0.0,
            ),
        )
        state_store.upsert_item(
            "projects",
            project_model.ProjectRead(
                id="proj_demo_learning",
                name="Protected teaching project",
                owner_user_id="public-teaching",
                created_by="public-teaching",
                permission_policy={"protected_teaching_dataset": True},
            ),
        )
        state_store.upsert_item(
            "eeg_files",
            eeg_model.EEGFileRead(
                id="eeg_demo_teaching_oddball",
                project_id="proj_demo_learning",
                original_filename="shared-teaching.edf",
                stored_path=source_path,
                detected_format="edf",
                owner_user_id="public-teaching",
                created_by="public-teaching",
                permission_policy={"protected_teaching_dataset": True},
                retention_policy="protected_teaching_demo",
                size_bytes=source_path.stat().st_size,
            ),
        )

        owner_a_plan = data_preparation_service.save_plan(
            prep_model.DataPreparationPlanCreate(
                project_id="proj_demo_learning",
                input_file_id="eeg_demo_teaching_oddball",
                owner_user_id="owner-a",
                created_by="owner-a",
                status="confirmed",
                module_scope=["psd", "erp", "qc"],
            )
        )
        owner_b_plan = data_preparation_service.save_plan(
            prep_model.DataPreparationPlanCreate(
                project_id="proj_demo_learning",
                input_file_id="eeg_demo_teaching_oddball",
                owner_user_id="owner-b",
                created_by="owner-b",
                status="confirmed",
                module_scope=["psd", "erp", "qc"],
            )
        )

        owner_a_epoch = data_preparation_service.save_epoch_set_for_file(
            "eeg_demo_teaching_oddball",
            prep_model.EpochSetCreate(
                project_id="proj_demo_learning",
                input_file_id="eeg_demo_teaching_oddball",
                owner_user_id="owner-a",
                created_by="owner-a",
                data_preparation_plan_id=owner_a_plan.id,
                data_preparation_revision=owner_a_plan.revision,
                event_mapping=[{"event_code": "target", "label": "target"}],
                event_count=1,
                estimated_epoch_count=1,
                tmin=-0.2,
                tmax=0.8,
            ),
            requesting_user_id="owner-a",
        )
        if owner_a_epoch.id in {item.id for item in data_preparation_service.list_epoch_sets(input_file_id="eeg_demo_teaching_oddball", owner_user_id="owner-b")}:
            raise AssertionError("owner-b should not list owner-a epoch sets on a shared teaching file")
        _expect_http(
            "owner-b cannot get owner-a epoch set on a shared teaching file",
            403,
            lambda: data_preparation_service.get_epoch_set(owner_a_epoch.id, requesting_user_id="owner-b"),
        )
        _expect_http(
            "owner-b cannot update owner-a epoch set on a shared teaching file",
            403,
            lambda: data_preparation_service.update_epoch_set(
                owner_a_epoch.id,
                prep_model.EpochSetUpdate(expected_revision=owner_a_epoch.revision, title="cross-owner overwrite"),
                requesting_user_id="owner-b",
            ),
        )
        _expect_http(
            "owner-b cannot create epoch set with owner-a data-preparation plan",
            403,
            lambda: data_preparation_service.save_epoch_set_for_file(
                "eeg_demo_teaching_oddball",
                prep_model.EpochSetCreate(
                    project_id="proj_demo_learning",
                    input_file_id="eeg_demo_teaching_oddball",
                    owner_user_id="owner-b",
                    created_by="owner-b",
                    data_preparation_plan_id=owner_a_plan.id,
                    data_preparation_revision=owner_a_plan.revision,
                    event_mapping=[{"event_code": "target", "label": "target"}],
                    event_count=1,
                    estimated_epoch_count=1,
                    tmin=-0.2,
                    tmax=0.8,
                ),
                requesting_user_id="owner-b",
            ),
        )
        owner_a_quality_root = (owner_a_plan.artifact_root or (root / "derivatives" / "proj_demo_learning" / "data_preparation" / owner_a_plan.id / f"revision_{owner_a_plan.revision}")) / "quality"
        before_owner_a_audits = set(owner_a_quality_root.glob("*")) if owner_a_quality_root.exists() else set()
        _expect_http(
            "owner-b cannot write bad-channel audit into owner-a plan root",
            403,
            lambda: data_preparation_service.save_bad_channel_audit_for_file(
                "eeg_demo_teaching_oddball",
                prep_model.BadChannelAuditCreate(
                    project_id="proj_demo_learning",
                    input_file_id="eeg_demo_teaching_oddball",
                    plan_id=owner_a_plan.id,
                    plan_revision=owner_a_plan.revision,
                    actor_user_id="owner-b",
                    changed_channels=[{"name": "Oz", "before": "good", "after": "bad"}],
                ),
                requesting_user_id="owner-b",
            ),
        )
        after_owner_a_audits = set(owner_a_quality_root.glob("*")) if owner_a_quality_root.exists() else set()
        if after_owner_a_audits != before_owner_a_audits:
            raise AssertionError("failed cross-owner bad-channel audit should not write files to owner-a plan root")
        owner_b_audit = data_preparation_service.save_bad_channel_audit_for_file(
            "eeg_demo_teaching_oddball",
            prep_model.BadChannelAuditCreate(
                project_id="proj_demo_learning",
                input_file_id="eeg_demo_teaching_oddball",
                plan_id=owner_b_plan.id,
                plan_revision=owner_b_plan.revision,
                actor_user_id="owner-b",
                changed_channels=[{"name": "Oz", "before": "good", "after": "bad"}],
            ),
            requesting_user_id="owner-b",
        )
        if owner_b_audit.actor_user_id != "owner-b" or not owner_b_audit.audit_json_path:
            raise AssertionError("owner-b bad-channel audit happy path did not write audit evidence")

        calls: list[dict] = []

        def fake_psd_runner(input_path, output_dir, parameters=None):
            calls.append(dict(parameters or {}))
            output = Path(output_dir)
            output.mkdir(parents=True, exist_ok=True)
            result = output / "result.json"
            result.write_text(json.dumps({"status": "ok"}) + "\n", encoding="utf-8")
            return {"result": result}

        task_service.run_psd = fake_psd_runner

        _expect_http(
            "task creation cannot use another user's data-preparation plan on a shared teaching file",
            403,
            lambda: task_service.create_task(
                task_model.AnalysisTaskCreate(
                    project_id="proj_demo_learning",
                    input_file_id="eeg_demo_teaching_oddball",
                    module_name="psd",
                    workflow_id="resting_psd",
                    owner_user_id="owner-b",
                    created_by="owner-b",
                    parameters_json={
                        "data_preparation_plan_id": owner_a_plan.id,
                        "data_preparation_revision": owner_a_plan.revision,
                    },
                ),
                requesting_user_id="owner-b",
            ),
        )

        first = task_service.create_task(
            task_model.AnalysisTaskCreate(
                project_id="proj_demo_learning",
                input_file_id="eeg_demo_teaching_oddball",
                module_name="psd",
                workflow_id="resting_psd",
                owner_user_id="owner-b",
                created_by="owner-b",
                idempotency_key="explicit-key-1",
                parameters_json={
                    "z": 1,
                    "a": 2,
                    "data_preparation_plan_id": owner_b_plan.id,
                    "data_preparation_revision": owner_b_plan.revision,
                },
            ),
            requesting_user_id="owner-b",
        )
        second = task_service.create_task(
            task_model.AnalysisTaskCreate(
                project_id="proj_demo_learning",
                input_file_id="eeg_demo_teaching_oddball",
                module_name="psd",
                workflow_id="resting_psd",
                owner_user_id="owner-b",
                created_by="owner-b",
                idempotency_key="explicit-key-1",
                parameters_json={
                    "a": 2,
                    "z": 1,
                    "data_preparation_revision": owner_b_plan.revision,
                    "data_preparation_plan_id": owner_b_plan.id,
                },
            ),
            requesting_user_id="owner-b",
        )
        if first.id != second.id:
            raise AssertionError("explicit idempotency_key should return the existing task despite parameter key order")
        if len(calls) != 1:
            raise AssertionError(f"idempotent duplicate should not rerun worker, got {len(calls)} runs")

        original_charge = billing_service.charge_analysis_task

        def failing_charge(**kwargs):
            raise HTTPException(status_code=402, detail={"message": "forced billing failure"})

        usage_before = _load_count(state_store, "usage_records", governance_model.UsageRecordRead)
        billing_service.charge_analysis_task = failing_charge
        try:
            _expect_http(
                "billing failure keeps completed usage record from being written",
                402,
                lambda: task_service.create_task(
                    task_model.AnalysisTaskCreate(
                        project_id="proj_demo_learning",
                        input_file_id="eeg_demo_teaching_oddball",
                        module_name="psd",
                        workflow_id="resting_psd",
                        owner_user_id="owner-b",
                        created_by="owner-b",
                        idempotency_key="forced-billing-failure",
                        parameters_json={
                            "data_preparation_plan_id": owner_b_plan.id,
                            "data_preparation_revision": owner_b_plan.revision,
                            "distinct": "billing-failure",
                        },
                    ),
                    requesting_user_id="owner-b",
                ),
            )
        finally:
            billing_service.charge_analysis_task = original_charge
        usage_after = _load_count(state_store, "usage_records", governance_model.UsageRecordRead)
        if usage_after != usage_before:
            raise AssertionError(f"usage record count changed before a successful billing charge: {usage_before} -> {usage_after}")
        first_usage = [
            record
            for record in state_store.load_registry("usage_records", governance_model.UsageRecordRead).values()
            if record.source_id == first.id and record.action == "analysis_task.completed"
        ]
        if not first_usage or first_usage[0].quota_account_id != "owner-b":
            raise AssertionError(f"completed usage should record quota_account_id=owner-b, got {first_usage}")
        failed_task = next(
            task
            for task in state_store.load_registry("tasks", task_model.AnalysisTaskRead).values()
            if task.error_code == "TASK_PAYMENT_FAILED"
        )
        orphan_artifact_path = (root / "derivatives" / failed_task.project_id / failed_task.id / "result.json")
        orphan_artifact_path.parent.mkdir(parents=True, exist_ok=True)
        orphan_artifact_path.write_text(json.dumps({"status": "orphaned-after-payment-failure"}) + "\n", encoding="utf-8")
        state_store.upsert_item(
            "artifacts",
            artifact_model.ArtifactRead(
                id="artifact_for_payment_failed_task",
                task_id=failed_task.id,
                project_id=failed_task.project_id,
                input_file_id=failed_task.input_file_id,
                artifact_type="json",
                label="result",
                path=orphan_artifact_path,
                mime_type="application/json",
            ),
        )
        current = governance_model.AccountRead(id="owner-b", email="owner-b@example.test")
        app = FastAPI()
        app.dependency_overrides[account_service.require_current_account] = lambda: current
        app.include_router(tasks_api.router, prefix="/api")
        app.include_router(projects_api.router, prefix="/api")
        client = TestClient(app)
        list_resp = client.get(f"/api/tasks/{failed_task.id}/artifacts")
        if list_resp.status_code != 402:
            raise AssertionError(f"payment_failed task artifact list should be blocked, got {list_resp.status_code}: {list_resp.text}")
        batch_resp = client.post(f"/api/tasks/{failed_task.id}/artifacts/batch")
        if batch_resp.status_code != 402:
            raise AssertionError(f"payment_failed task batch should be blocked, got {batch_resp.status_code}: {batch_resp.text}")
        project_batch_resp = client.post(f"/api/projects/{failed_task.project_id}/tasks/{failed_task.id}/artifacts/batch")
        if project_batch_resp.status_code != 402:
            raise AssertionError(f"payment_failed project batch should be blocked, got {project_batch_resp.status_code}: {project_batch_resp.text}")
        _expect_http(
            "payment_failed task direct artifact download should be blocked",
            402,
            lambda: artifacts_api.download_artifact("artifact_for_payment_failed_task", current=current),
        )

    print("PASS data-prep task billing guards")


if __name__ == "__main__":
    main()
