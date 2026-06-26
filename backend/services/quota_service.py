from backend.models.governance import UsageRecordRead
from backend.services import state_store

REGISTRY = "usage_records"


def upload_quota_preview(size_bytes: int | None) -> dict:
    size = int(size_bytes or 0)
    return {
        "billable": False,
        "resource_type": "storage_bytes_hot",
        "quantity": size,
        "unit": "bytes",
        "policy": "v1_trial_no_charge",
    }


def task_resource_estimate(module_name: str, file_size_bytes: int | None, parameters_json: dict | None = None) -> dict:
    size = int(file_size_bytes or 0)
    params = parameters_json or {}
    return {
        "module_name": module_name,
        "input_size_bytes": size,
        "estimated_storage_bytes": max(size // 20, 1024),
        "estimated_cpu_seconds": _estimate_cpu_seconds(module_name, size, params),
        "policy": "v1_local_worker_estimate",
    }


def task_quota_preview(estimate: dict) -> dict:
    return {
        "billable": False,
        "resource_type": "analysis_task",
        "quantity": 1,
        "unit": "task",
        "estimated_cpu_seconds": estimate.get("estimated_cpu_seconds"),
        "estimated_storage_bytes": estimate.get("estimated_storage_bytes"),
        "policy": "v1_trial_no_charge",
    }


def record_usage(
    *,
    resource_type: str,
    action: str,
    quantity: float,
    unit: str,
    source_type: str,
    source_id: str,
    organization_id: str = "local-org",
    project_id: str | None = None,
    owner_user_id: str = "local-user",
    quota_account_id: str | None = None,
    metadata_json: dict | None = None,
) -> UsageRecordRead:
    record = UsageRecordRead(
        organization_id=organization_id,
        project_id=project_id,
        owner_user_id=owner_user_id,
        quota_account_id=quota_account_id,
        resource_type=resource_type,
        action=action,
        quantity=quantity,
        unit=unit,
        source_type=source_type,
        source_id=source_id,
        metadata_json=metadata_json or {},
    )
    state_store.upsert_item(REGISTRY, record)
    return record


def _estimate_cpu_seconds(module_name: str, size_bytes: int, parameters_json: dict) -> int:
    size_mb = max(size_bytes / (1024 * 1024), 1)
    module_factor = {
        "qc": 0.25,
        "psd": 0.8,
        "erp": 0.7,
        "multitaper_psd_tfr": 1.1,
        "pac": 1.2,
        "reference_csd": 0.6,
        "connectivity": 0.8,
    }.get(module_name, 1.0)
    if parameters_json.get("preview"):
        module_factor = min(module_factor, 0.2)
    return max(int(size_mb * module_factor), 1)
