from __future__ import annotations

import importlib
import io
import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("QLANALYSER_ENV", "test")
os.environ.setdefault("QLANALYSER_SANDBOX_MODE", "true")

ACCEPTANCE_BILLING_ACCOUNT_ID = "demo-customer"
ACCEPTANCE_CHARGE_CREDITS = 1.0


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    _write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def _expect_http(label: str, status_code: int, fn) -> None:
    try:
        fn()
    except HTTPException as exc:
        if exc.status_code != status_code:
            raise AssertionError(f"{label}: expected HTTP {status_code}, got {exc.status_code}") from exc
        return
    raise AssertionError(f"{label}: expected HTTP {status_code}")


def _assert_public_lab_demo_policy(lab_demo_api) -> None:
    previous_env = {
        "QLANALYSER_ENV": os.environ.get("QLANALYSER_ENV"),
        "QLANALYSER_SANDBOX_MODE": os.environ.get("QLANALYSER_SANDBOX_MODE"),
        "QLANALYSER_PUBLIC_LAB_DEMO_ENABLED": os.environ.get("QLANALYSER_PUBLIC_LAB_DEMO_ENABLED"),
    }
    try:
        os.environ["QLANALYSER_ENV"] = "production"
        os.environ["QLANALYSER_SANDBOX_MODE"] = "false"
        os.environ.pop("QLANALYSER_PUBLIC_LAB_DEMO_ENABLED", None)
        _expect_http(
            "public lab demo sample endpoint is disabled by default in production",
            404,
            lab_demo_api.list_sample_files,
        )

        os.environ["QLANALYSER_SANDBOX_MODE"] = "true"
        sample_listing = lab_demo_api.list_sample_files()
        if sample_listing.get("root") != "work/sample_data":
            raise AssertionError("lab demo sample listing should not expose an absolute local path")
    finally:
        for key, value in previous_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _charge_preview() -> dict[str, Any]:
    return {
        "billing_account_id": ACCEPTANCE_BILLING_ACCOUNT_ID,
        "estimated_credits": ACCEPTANCE_CHARGE_CREDITS,
    }


def _seed_posted_charge(state_store, governance_model, task_id: str, module_name: str) -> None:
    state_store.upsert_item(
        "billing_transactions",
        governance_model.BillingTransactionRead(
            id=f"billtx_{task_id}",
            account_id=ACCEPTANCE_BILLING_ACCOUNT_ID,
            direction="debit",
            amount_credits=ACCEPTANCE_CHARGE_CREDITS,
            balance_after_credits=99.0,
            source_type="analysis_task",
            source_id=task_id,
            description=f"{module_name.upper()} acceptance posted charge",
            metadata_json={"module_name": module_name},
        ),
    )


def _seed_report_task(state_store, task_model, artifact_model, derivatives_root: Path, module_name: str) -> str:
    workflow_by_module = {"psd": "resting_psd", "tfr": "tfr_ersp_itc"}
    table_by_module = {"psd": "tables/band_power.csv", "tfr": "tables/tfr_summary_table.csv"}
    task_id = f"task_report_{module_name}"
    output_dir = derivatives_root / "proj_delivery_guard" / task_id
    _write_text(output_dir / table_by_module[module_name], "metric,value\nacceptance,1\n")
    _write_json(output_dir / "result.json", {"module_name": module_name, "warnings": []})
    _write_json(output_dir / "manifest.json", {"files": [table_by_module[module_name], "result.json"]})
    _write_json(output_dir / "reproducibility" / "parameters.json", {"module_name": module_name})
    _write_json(output_dir / "reproducibility" / "workflow.json", {"steps": [{"module": module_name}]})
    _write_json(output_dir / "reproducibility" / "software_versions.json", {"qlanalyser": "acceptance"})
    _write_text(output_dir / "reproducibility" / "method_description.txt", f"{module_name} acceptance\n")
    task = task_model.AnalysisTaskRead(
        id=task_id,
        project_id="proj_delivery_guard",
        input_file_id="eeg_delivery_guard",
        module_name=module_name,
        workflow_id=workflow_by_module[module_name],
        owner_user_id="owner-a",
        created_by="owner-a",
        status="completed",
        queue_status="completed",
        progress=100,
        quota_charge_preview_json=_charge_preview(),
    )
    state_store.upsert_item("tasks", task)
    table_path = output_dir / table_by_module[module_name]
    state_store.upsert_item(
        "artifacts",
        artifact_model.ArtifactRead(
            id=f"artifact_report_{module_name}",
            task_id=task_id,
            project_id=task.project_id,
            input_file_id=task.input_file_id,
            artifact_type="csv",
            label=Path(table_by_module[module_name]).stem,
            path=table_path,
            size_bytes=table_path.stat().st_size,
            mime_type="text/csv",
        ),
    )
    return task_id


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="qlanalyser-delivery-policy-") as tmp:
        root = Path(tmp)
        state_root = root / "state"
        derivatives_root = root / "derivatives"
        reports_root = root / "reports"
        os.environ["QLANALYSER_STATE_ROOT"] = str(state_root)

        import backend.api.artifacts as artifacts_api
        import backend.api.lab_demo as lab_demo_api
        import backend.api.projects as projects_api
        import backend.api.tasks as tasks_api
        import backend.models.artifact as artifact_model
        import backend.models.analysis_task as task_model
        import backend.models.governance as governance_model
        import backend.models.project as project_model
        import backend.models.report as report_model
        import backend.services.account_service as account_service
        import backend.services.audit_service as audit_service
        import backend.services.quota_service as quota_service
        import backend.services.report_service as report_service
        import backend.services.state_store as state_store
        import backend.services.task_service as task_service

        for module in (
            state_store,
            audit_service,
            quota_service,
            task_service,
            report_service,
            artifacts_api,
            lab_demo_api,
            projects_api,
            tasks_api,
        ):
            importlib.reload(module)

        task_service.DERIVATIVES_ROOT = derivatives_root
        report_service.DERIVATIVES_ROOT = derivatives_root
        report_service.REPORT_ROOT = reports_root
        artifacts_api._DERIVATIVES_ROOT = derivatives_root.resolve()
        lab_demo_api._DERIVATIVES_ROOT = derivatives_root.resolve()
        lab_demo_api._DEMO_PROJECT_IDS = {"proj_delivery_guard"}
        projects_api._DERIVATIVES_ROOT = derivatives_root.resolve()
        tasks_api._DERIVATIVES_ROOT = derivatives_root.resolve()
        _assert_public_lab_demo_policy(lab_demo_api)
        state_store.upsert_item(
            "projects",
            project_model.ProjectRead(
                id="proj_delivery_guard",
                name="Delivery policy guard project",
                owner_user_id="owner-a",
                created_by="owner-a",
            ),
        )

        task_id = "task_epilepsy_legacy_guard"
        task = task_model.AnalysisTaskRead(
            id=task_id,
            project_id="proj_delivery_guard",
            input_file_id="eeg_delivery_guard",
            module_name="epilepsy_ml",
            workflow_id="epilepsy_ml",
            owner_user_id="owner-a",
            created_by="owner-a",
            status="completed",
            queue_status="completed",
            progress=100,
            quota_charge_preview_json=_charge_preview(),
        )
        state_store.upsert_item("tasks", task)
        _seed_posted_charge(state_store, governance_model, task_id, "epilepsy_ml")
        legacy_zip = derivatives_root / "proj_delivery_guard" / task_id / "evidence_packages" / "qlanalyser_epilepsy_all_events_evidence_package.zip"
        legacy_zip.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(legacy_zip, "w") as zf:
            zf.writestr("manifest.json", "{}\n")
        events_csv = derivatives_root / "proj_delivery_guard" / task_id / "tables" / "epilepsy_ml_events.csv"
        _write_text(events_csv, "event_id,start_sec,end_sec\nE-001,0,1\n")
        state_store.upsert_item(
            "artifacts",
            artifact_model.ArtifactRead(
                id="artifact_legacy_epilepsy_package",
                task_id=task_id,
                project_id=task.project_id,
                input_file_id=task.input_file_id,
                artifact_type="zip",
                label="epilepsy_all_events_evidence_package",
                path=legacy_zip,
                object_key="evidence_packages/qlanalyser_epilepsy_all_events_evidence_package.zip",
                size_bytes=legacy_zip.stat().st_size,
                mime_type="application/zip",
            ),
        )
        state_store.upsert_item(
            "artifacts",
            artifact_model.ArtifactRead(
                id="artifact_epilepsy_events_csv",
                task_id=task_id,
                project_id=task.project_id,
                input_file_id=task.input_file_id,
                artifact_type="csv",
                label="epilepsy_ml_events",
                path=events_csv,
                object_key="tables/epilepsy_ml_events.csv",
                size_bytes=events_csv.stat().st_size,
                mime_type="text/csv",
            ),
        )

        current = governance_model.AccountRead(id="owner-a", email="owner-a@example.test")
        _expect_http(
            "legacy formal epilepsy package cannot be downloaded as artifact",
            409,
            lambda: artifacts_api.download_artifact("artifact_legacy_epilepsy_package", current=current),
        )
        benign = artifacts_api.download_artifact("artifact_epilepsy_events_csv", current=current)
        if getattr(benign, "status_code", 200) != 200:
            raise AssertionError("ordinary epilepsy event CSV should remain downloadable")

        app = FastAPI()
        app.dependency_overrides[account_service.require_current_account] = lambda: current
        app.include_router(tasks_api.router, prefix="/api")
        app.include_router(projects_api.router, prefix="/api")
        client = TestClient(app)
        batch = client.post(f"/api/tasks/{task_id}/artifacts/batch")
        if batch.status_code != 200:
            raise AssertionError(f"batch artifact download should remain available, got {batch.status_code}: {batch.text}")
        with zipfile.ZipFile(io.BytesIO(batch.content)) as zf:
            names = set(zf.namelist())
        if "epilepsy_all_events_evidence_package.zip" in names:
            raise AssertionError("legacy formal epilepsy package must not be included in task batch downloads")
        if "epilepsy_ml_events.csv" not in names:
            raise AssertionError("ordinary epilepsy event CSV should remain in task batch downloads")
        project_batch = client.post(f"/api/projects/proj_delivery_guard/tasks/{task_id}/artifacts/batch")
        if project_batch.status_code != 200:
            raise AssertionError(f"project batch artifact download should remain available, got {project_batch.status_code}: {project_batch.text}")
        with zipfile.ZipFile(io.BytesIO(project_batch.content)) as zf:
            project_names = set(zf.namelist())
        if "epilepsy_all_events_evidence_package.zip" in project_names:
            raise AssertionError("legacy formal epilepsy package must not be included in project batch downloads")
        demo_listing = lab_demo_api.list_demo_artifacts(task_id)
        if any("evidence_package" in (item.get("label", "") + item.get("filename", "")).lower() for item in demo_listing):
            raise AssertionError("lab demo listing must not expose legacy epilepsy evidence package")
        _expect_http(
            "lab demo public endpoint cannot download legacy epilepsy package",
            409,
            lambda: lab_demo_api.download_demo_artifact(task_id, "epilepsy_all_events_evidence_package"),
        )

        psd_task_id = _seed_report_task(state_store, task_model, artifact_model, derivatives_root, "psd")
        tfr_task_id = _seed_report_task(state_store, task_model, artifact_model, derivatives_root, "tfr")
        _seed_posted_charge(state_store, governance_model, psd_task_id, "psd")
        _seed_posted_charge(state_store, governance_model, tfr_task_id, "tfr")
        _expect_http(
            "PSD report cannot be created before result review",
            422,
            lambda: report_service.create_report(
                report_model.ReportCreate(
                    project_id="proj_delivery_guard",
                    task_id=psd_task_id,
                    title="PSD report blocked before review",
                    owner_user_id="owner-a",
                    created_by="owner-a",
                )
            ),
        )
        queued_psd = task_model.AnalysisTaskRead(
            id="task_report_psd_queued",
            project_id="proj_delivery_guard",
            input_file_id="eeg_delivery_guard",
            module_name="psd",
            workflow_id="resting_psd",
            owner_user_id="owner-a",
            created_by="owner-a",
            status="queued",
            queue_status="queued",
            quota_charge_preview_json=_charge_preview(),
        )
        state_store.upsert_item("tasks", queued_psd)
        _expect_http(
            "PSD report cannot be created from an incomplete task",
            422,
            lambda: report_service.create_report(
                report_model.ReportCreate(
                    project_id="proj_delivery_guard",
                    task_id=queued_psd.id,
                    title="PSD queued report blocked",
                    owner_user_id="owner-a",
                    created_by="owner-a",
                )
            ),
        )
        fake_billing_task_id = "task_report_psd_fake_billing_id"
        fake_billing_output = derivatives_root / "proj_delivery_guard" / fake_billing_task_id
        _write_text(fake_billing_output / "tables" / "band_power.csv", "metric,value\nfake,1\n")
        fake_billing_task = task_model.AnalysisTaskRead(
            id=fake_billing_task_id,
            project_id="proj_delivery_guard",
            input_file_id="eeg_delivery_guard",
            module_name="psd",
            workflow_id="resting_psd",
            owner_user_id="owner-a",
            created_by="owner-a",
            status="completed",
            queue_status="completed",
            progress=100,
            quota_charge_preview_json=_charge_preview(),
            actual_resource_usage_json={"billing_transaction_id": "billtx_missing_or_unposted"},
        )
        state_store.upsert_item("tasks", fake_billing_task)
        state_store.upsert_item(
            "artifacts",
            artifact_model.ArtifactRead(
                id="artifact_report_psd_fake_billing",
                task_id=fake_billing_task_id,
                project_id=fake_billing_task.project_id,
                input_file_id=fake_billing_task.input_file_id,
                artifact_type="csv",
                label="band_power",
                path=fake_billing_output / "tables" / "band_power.csv",
                size_bytes=(fake_billing_output / "tables" / "band_power.csv").stat().st_size,
                mime_type="text/csv",
            ),
        )
        _expect_http(
            "completed task with fake billing_transaction_id is not deliverable",
            402,
            lambda: task_service.assert_task_artifacts_deliverable(fake_billing_task),
        )
        audit_service.record_event(
            action="result.reviewed",
            object_type="analysis_task",
            object_id=psd_task_id,
            project_id="proj_delivery_guard",
            actor_user_id="owner-a",
        )
        psd_report = report_service.create_report(
            report_model.ReportCreate(
                project_id="proj_delivery_guard",
                task_id=psd_task_id,
                title="PSD report allowed",
                owner_user_id="owner-a",
                created_by="owner-a",
            )
        )
        if not psd_report.package_path or not Path(psd_report.package_path).exists():
            raise AssertionError("PSD report should be created")
        _expect_http(
            "TFR cannot be a default customer report primary module",
            422,
            lambda: report_service.create_report(
                report_model.ReportCreate(
                    project_id="proj_delivery_guard",
                    task_id=tfr_task_id,
                    title="TFR report blocked",
                    owner_user_id="owner-a",
                    created_by="owner-a",
                )
            ),
        )

    print("PASS delivery policy guards")


if __name__ == "__main__":
    main()
