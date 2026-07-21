import importlib
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def write_evidence(path: Path | None, payload: dict) -> None:
    if not path:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Validate queue-ready task lifecycle contract.")
    parser.add_argument("--users", type=int, default=10)
    parser.add_argument("--tasks", type=int, default=50)
    parser.add_argument(
        "--evidence-path",
        type=Path,
        default=Path(os.getenv("QLANALYSER_QUEUE_CAPACITY_EVIDENCE_PATH")) if os.getenv("QLANALYSER_QUEUE_CAPACITY_EVIDENCE_PATH") else None,
    )
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="qlanalyser-task-queue-") as tmp:
        root = Path(tmp)
        os.environ["QLANALYSER_STATE_ROOT"] = str(root / "state")
        os.environ["QLANALYSER_DERIVATIVES_ROOT"] = str(root / "derivatives")
        os.environ["QLANALYSER_OBJECT_ROOT"] = str(root / "objects")

        import backend.services.state_store as state_store
        import backend.services.storage_service as storage_service
        import backend.services.task_service as task_service
        import backend.services.audit_service as audit_service
        import backend.services.quota_service as quota_service
        import backend.services.account_service as account_service
        import backend.models.governance as governance_model
        import backend.models.project as project_model
        import backend.models.eeg_file as eeg_file_model
        import backend.models.analysis_task as task_model

        if args.users <= 0 or args.tasks <= 0:
            raise AssertionError("--users and --tasks must be positive")

        for module in (state_store, storage_service, task_service, audit_service, quota_service, account_service):
            importlib.reload(module)
        account_service.ensure_seed_accounts()

        accounts = []
        for user_idx in range(args.users):
            session = account_service.create_account(
                governance_model.AccountCreate(
                    register_method="email",
                    email=f"queue-user-{user_idx + 1}@qlanalyser.local",
                    password="queue-capacity-2026",
                    name=f"Queue User {user_idx + 1}",
                    organization_name="Queue Capacity Lab",
                    verification_code=account_service.SANDBOX_CODE,
                ),
                trial_credits=max(float(args.tasks), 100.0),
            )
            accounts.append(session["account"])
        account_ids = [account["id"] for account in accounts]

        project = storage_service.create_project(project_model.ProjectCreate(name="Queue capacity acceptance"))
        input_path = root / "input.edf"
        input_path.write_bytes(b"not-real-eeg-but-task-input")
        eeg_file = eeg_file_model.EEGFileRead(
            project_id=project.id,
            original_filename="queue.edf",
            stored_path=input_path,
            detected_format="edf",
            size_bytes=input_path.stat().st_size,
            object_key="uploads/queue.edf",
            sha256="queue-test",
        )
        storage_service._eeg_files[eeg_file.id] = eeg_file
        state_store.upsert_item("eeg_files", eeg_file)

        def fake_runner(input_path, output_dir, parameters=None):
            output = Path(output_dir)
            (output / "reproducibility").mkdir(parents=True, exist_ok=True)
            (output / "result.json").write_text('{"ok": true}', encoding="utf-8")
            (output / "reproducibility" / "parameters.json").write_text("{}", encoding="utf-8")
            return {"result": output / "result.json", "parameters": output / "reproducibility" / "parameters.json"}

        task_service.run_quality_check = fake_runner

        tasks = []
        for idx in range(args.tasks):
            owner_user_id = account_ids[idx % len(account_ids)]
            task = task_service.create_task(task_model.AnalysisTaskCreate(
                project_id=project.id,
                module_name="qc",
                workflow_id="metadata_qc",
                input_file_id=eeg_file.id,
                owner_user_id=owner_user_id,
                queue_name="analysis-v1-local",
                parameters_json={"capacity_index": idx, "capacity_owner_index": idx % len(account_ids)},
            ))
            tasks.append(task)

        assert len(tasks) == args.tasks
        assert all(task.status == "completed" for task in tasks)
        assert all(task.queue_status == "completed" for task in tasks)
        assert all(task.resource_estimate_json for task in tasks)
        assert all(task.owner_user_id in account_ids for task in tasks)
        assert all(task.quota_charge_preview_json.get("billing_account_id") == task.owner_user_id for task in tasks)
        assert all(task.quota_charge_preview_json.get("estimated_credits", 0) > 0 for task in tasks)
        distinct_task_owners = sorted({task.owner_user_id for task in tasks})
        expected_distinct_owners = min(args.users, args.tasks)
        assert len(distinct_task_owners) == expected_distinct_owners

        audit_events = state_store.load_registry("audit_events", audit_service.AuditEventRead)
        usage_records = state_store.load_registry("usage_records", quota_service.UsageRecordRead)
        completed_events = [event for event in audit_events.values() if event.action == "analysis_task.completed"]
        task_usage = [record for record in usage_records.values() if record.resource_type == "analysis_task"]
        assert len(completed_events) == args.tasks
        assert len(task_usage) == args.tasks

        payload = {
            "status": "passed",
            "mode": "local_queue_ready_contract",
            "users": args.users,
            "created_accounts": len(accounts),
            "distinct_task_owners": len(distinct_task_owners),
            "owner_user_ids": distinct_task_owners,
            "tasks": args.tasks,
            "completed": len(tasks),
            "audit_completed_events": len(completed_events),
            "usage_records": len(task_usage),
            "note": "This validates queue-ready lifecycle fields with local execution; distributed worker capacity remains a deployment gate.",
        }
        write_evidence(args.evidence_path, payload)
        if args.evidence_path:
            payload["evidence_path"] = str(args.evidence_path)
        print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
