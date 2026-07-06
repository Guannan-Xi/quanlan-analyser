import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("QLANALYSER_ENV", "test")
os.environ.setdefault("QLANALYSER_SANDBOX_MODE", "true")
os.environ["QLANALYSER_STATE_ROOT"] = tempfile.mkdtemp(prefix="qlanalyser-report-gate-state-")

from backend.models.analysis_task import AnalysisTaskRead
from backend.models.governance import BillingTransactionRead
from backend.models.report import ReportRead
from backend.services import audit_service, report_service, state_store

ACCEPTANCE_BILLING_ACCOUNT_ID = "demo-customer"
ACCEPTANCE_CHARGE_CREDITS = 1.0


def charge_preview() -> dict:
    return {
        "billing_account_id": ACCEPTANCE_BILLING_ACCOUNT_ID,
        "estimated_credits": ACCEPTANCE_CHARGE_CREDITS,
    }


def expect_http_error(name: str, status_code: int, fn) -> dict:
    try:
        fn()
    except HTTPException as exc:
        if exc.status_code != status_code:
            raise AssertionError(f"{name}: expected {status_code}, got {exc.status_code}: {exc.detail}") from exc
        return {"name": name, "status": "passed", "http_status": exc.status_code}
    raise AssertionError(f"{name}: expected HTTP {status_code}")


def main() -> None:
    owner_user_id = "acct_report_gate_customer"
    project_id = "proj_report_gate"
    task_id = "task_report_gate_psd"
    report_dir = report_service.REPORT_ROOT / project_id / "acceptance_report_release_gate"
    report_dir.mkdir(parents=True, exist_ok=True)
    html_path = report_dir / "report.html"
    package_path = report_dir / "report.zip"
    html_path.write_text("<html><body>release gate</body></html>", encoding="utf-8")
    package_path.write_bytes(b"release gate package")

    report = ReportRead(
        project_id=project_id,
        task_id=task_id,
        title="Release gate report",
        owner_user_id=owner_user_id,
        created_by=owner_user_id,
        html_path=html_path,
        package_path=package_path,
    )
    state_store.upsert_item("reports", report)

    checks = [
        expect_http_error("customer read blocked before result review", 423, lambda: report_service.get_report(report.id, requesting_user_id=owner_user_id)),
        expect_http_error("customer html blocked before result review", 423, lambda: report_service.get_report_file(report.id, "html", requesting_user_id=owner_user_id)),
    ]

    internal_report = report_service.get_report(report.id)
    if internal_report.id != report.id:
        raise AssertionError("internal/admin read should keep operations access")
    checks.append({"name": "internal/admin read allowed", "status": "passed"})

    audit_service.record_event(
        action="result.reviewed",
        object_type="analysis_task",
        object_id=task_id,
        organization_id=report.organization_id,
        project_id=project_id,
        actor_user_id=owner_user_id,
        metadata_json={"source": "acceptance_report_release_gate"},
    )
    checks.append(
        expect_http_error(
            "customer report blocked when source task is missing after review",
            409,
            lambda: report_service.get_report(report.id, requesting_user_id=owner_user_id),
        )
    )

    state_store.upsert_item(
        "tasks",
        AnalysisTaskRead(
            id=task_id,
            organization_id=report.organization_id,
            project_id=project_id,
            input_file_id="eeg_report_gate",
            module_name="psd",
            workflow_id="resting_psd",
            owner_user_id=owner_user_id,
            created_by=owner_user_id,
            status="completed",
            queue_status="completed",
            progress=100,
            quota_charge_preview_json=charge_preview(),
        ),
    )
    state_store.upsert_item(
        "billing_transactions",
        BillingTransactionRead(
            id=f"billtx_{task_id}",
            account_id=ACCEPTANCE_BILLING_ACCOUNT_ID,
            direction="debit",
            amount_credits=ACCEPTANCE_CHARGE_CREDITS,
            balance_after_credits=99.0,
            source_type="analysis_task",
            source_id=task_id,
            description="PSD acceptance posted charge",
            metadata_json={"module_name": "psd"},
        ),
    )

    released_report = report_service.get_report(report.id, requesting_user_id=owner_user_id)
    released_html = report_service.get_report_file(report.id, "html", requesting_user_id=owner_user_id)
    released_package = report_service.get_report_file(report.id, "package", requesting_user_id=owner_user_id)
    if released_report.id != report.id or released_html != html_path.resolve() or released_package != package_path.resolve():
        raise AssertionError("released customer report/file access did not resolve as expected")
    checks.append({"name": "customer access allowed after result review", "status": "passed"})

    outside_path = Path(tempfile.gettempdir()) / "qlanalyser_report_gate_outside.html"
    outside_path.write_text("outside report root", encoding="utf-8")
    outside_report = ReportRead(
        project_id=project_id,
        task_id="task_report_gate_outside",
        title="Outside path report",
        owner_user_id=owner_user_id,
        created_by=owner_user_id,
        html_path=outside_path,
        package_path=package_path,
    )
    state_store.upsert_item("reports", outside_report)
    audit_service.record_event(
        action="result.reviewed",
        object_type="analysis_task",
        object_id=outside_report.task_id,
        organization_id=outside_report.organization_id,
        project_id=outside_report.project_id,
        actor_user_id=owner_user_id,
        metadata_json={"source": "acceptance_report_release_gate"},
    )
    state_store.upsert_item(
        "tasks",
        AnalysisTaskRead(
            id=outside_report.task_id,
            organization_id=outside_report.organization_id,
            project_id=outside_report.project_id,
            input_file_id="eeg_report_gate",
            module_name="psd",
            workflow_id="resting_psd",
            owner_user_id=owner_user_id,
            created_by=owner_user_id,
            status="completed",
            queue_status="completed",
            progress=100,
            quota_charge_preview_json=charge_preview(),
        ),
    )
    state_store.upsert_item(
        "billing_transactions",
        BillingTransactionRead(
            id=f"billtx_{outside_report.task_id}",
            account_id=ACCEPTANCE_BILLING_ACCOUNT_ID,
            direction="debit",
            amount_credits=ACCEPTANCE_CHARGE_CREDITS,
            balance_after_credits=98.0,
            source_type="analysis_task",
            source_id=outside_report.task_id,
            description="PSD acceptance posted charge",
            metadata_json={"module_name": "psd"},
        ),
    )
    checks.append(
        expect_http_error(
            "customer html outside report root blocked",
            403,
            lambda: report_service.get_report_file(outside_report.id, "html", requesting_user_id=owner_user_id),
        )
    )

    outside_path.unlink(missing_ok=True)
    shutil.rmtree(report_dir, ignore_errors=True)
    shutil.rmtree(state_store.STATE_ROOT, ignore_errors=True)
    print(json.dumps({"status": "passed", "checks": checks}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
