import asyncio
import importlib
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class ChunkedUpload:
    def __init__(self, filename: str, total_bytes: int, chunk_byte: bytes = b"q"):
        self.filename = filename
        self.content_type = "application/octet-stream"
        self.total_bytes = total_bytes
        self.sent = 0
        self.read_sizes: list[int] = []
        self.chunk_byte = chunk_byte

    async def read(self, size: int = -1) -> bytes:
        self.read_sizes.append(size)
        if self.sent >= self.total_bytes:
            return b""
        if size is None or size < 0:
            size = self.total_bytes - self.sent
        length = min(size, self.total_bytes - self.sent)
        self.sent += length
        return self.chunk_byte * length


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="qlanalyser-aliyun-v1-") as tmp:
        root = Path(tmp)
        os.environ["QLANALYSER_STATE_ROOT"] = str(root / "state")
        os.environ["QLANALYSER_OBJECT_ROOT"] = str(root / "objects")
        os.environ["QLANALYSER_DERIVATIVES_ROOT"] = str(root / "derivatives")
        os.environ["QLANALYSER_UPLOAD_CHUNK_BYTES"] = str(64 * 1024)

        import backend.services.state_store as state_store
        import backend.services.object_storage_service as object_storage_service
        import backend.services.storage_service as storage_service
        import backend.services.audit_service as audit_service
        import backend.services.quota_service as quota_service
        import backend.services.task_service as task_service
        import backend.services.report_service as report_service
        import backend.services.account_service as account_service
        import backend.models.project as project_model
        import backend.models.analysis_task as task_model
        import backend.models.report as report_model

        for module in (
            state_store,
            object_storage_service,
            storage_service,
            audit_service,
            quota_service,
            task_service,
            report_service,
            account_service,
        ):
            importlib.reload(module)
        account_service.ensure_seed_accounts()

        project = storage_service.create_project(project_model.ProjectCreate(
            name="Aliyun V1 contract project",
            organization_id="org_acceptance",
            owner_user_id="demo-customer",
            quota_account_id="quota_acceptance",
        ))

        upload = ChunkedUpload("contract.edf", total_bytes=1024 * 1024)
        eeg_file = asyncio.run(storage_service.create_eeg_file(project.id, None, upload))
        assert eeg_file.object_key
        assert eeg_file.size_bytes == 1024 * 1024
        assert eeg_file.sha256
        assert eeg_file.upload_status == "uploaded"
        assert max(upload.read_sizes) <= 64 * 1024
        assert object_storage_service.exists(eeg_file.object_key)

        def fake_qc_runner(input_path, output_dir, parameters=None):
            output = Path(output_dir)
            (output / "reproducibility").mkdir(parents=True, exist_ok=True)
            (output / "tables").mkdir(parents=True, exist_ok=True)
            result_path = output / "result.json"
            result_path.write_text(json.dumps({"ok": True}), encoding="utf-8")
            params_path = output / "reproducibility" / "parameters.json"
            params_path.write_text(json.dumps(parameters or {}), encoding="utf-8")
            table_path = output / "tables" / "qc.csv"
            table_path.write_text("metric,value\nok,1\n", encoding="utf-8")
            return {"result": result_path, "parameters": params_path, "qc_table": table_path}

        task_service.run_quality_check = fake_qc_runner
        task = task_service.create_task(task_model.AnalysisTaskCreate(
            organization_id=project.organization_id,
            project_id=project.id,
            module_name="qc",
            workflow_id="metadata_qc",
            input_file_id=eeg_file.id,
            owner_user_id=project.owner_user_id,
            queue_name="analysis-v1-local",
        ))
        assert task.status == "completed"
        assert task.queue_status == "completed"
        assert task.resource_estimate_json["input_size_bytes"] == eeg_file.size_bytes
        assert task.quota_charge_preview_json["billing_account_id"] == "demo-customer"
        assert task.quota_charge_preview_json["estimated_credits"] > 0
        assert task.actual_resource_usage_json["artifact_count"] == 3
        assert task.actual_resource_usage_json["charged_credits"] > 0
        assert task.audit_trace_id

        artifacts = task_service.list_task_artifacts(task.id)
        assert artifacts
        assert all(artifact.project_id == project.id for artifact in artifacts)
        assert all(artifact.input_file_id == eeg_file.id for artifact in artifacts)
        assert all(artifact.object_key for artifact in artifacts)
        assert all(artifact.size_bytes is not None for artifact in artifacts)
        assert all(artifact.sha256 for artifact in artifacts)

        report = report_service.create_report(report_model.ReportCreate(
            organization_id=project.organization_id,
            project_id=project.id,
            task_id=task.id,
            title="Aliyun V1 contract report",
            owner_user_id=project.owner_user_id,
        ))
        assert report.package_path and Path(report.package_path).exists()
        assert report.package_object_key
        assert report.size_bytes and report.size_bytes > 0
        assert report.sha256
        assert report.audit_trace_id

        audit_events = state_store.load_registry("audit_events", audit_service.AuditEventRead)
        usage_records = state_store.load_registry("usage_records", quota_service.UsageRecordRead)
        assert any(event.action == "eeg_file.uploaded" for event in audit_events.values())
        assert any(event.action == "analysis_task.completed" for event in audit_events.values())
        assert any(event.action == "report.created" for event in audit_events.values())
        assert any(record.resource_type == "storage_bytes_hot" for record in usage_records.values())
        assert any(record.resource_type == "analysis_task" for record in usage_records.values())
        assert any(record.resource_type == "report_package_storage_bytes" for record in usage_records.values())

        print(json.dumps({
            "status": "passed",
            "project_id": project.id,
            "file_id": eeg_file.id,
            "task_id": task.id,
            "report_id": report.id,
            "audit_events": len(audit_events),
            "usage_records": len(usage_records),
        }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
