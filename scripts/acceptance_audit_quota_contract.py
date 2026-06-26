import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.models.governance import AuditEventRead, UsageRecordRead
from backend.services import state_store


def main() -> None:
    audit_events = state_store.load_registry("audit_events", AuditEventRead)
    usage_records = state_store.load_registry("usage_records", UsageRecordRead)

    required_actions = {"eeg_file.uploaded", "analysis_task.completed", "report.created"}
    actions = {event.action for event in audit_events.values()}
    missing_actions = sorted(required_actions - actions)
    if missing_actions:
        raise AssertionError(f"Missing audit actions: {missing_actions}; seen={sorted(actions)}")

    required_resources = {"storage_bytes_hot", "analysis_task", "report_package_storage_bytes"}
    resources = {record.resource_type for record in usage_records.values()}
    missing_resources = sorted(required_resources - resources)
    if missing_resources:
        raise AssertionError(f"Missing usage resources: {missing_resources}; seen={sorted(resources)}")

    billable_records = [record.id for record in usage_records.values() if record.billable is not False]
    if billable_records:
        raise AssertionError(f"V1 trial usage records must be no-charge; billable={billable_records}")

    print(json.dumps({
        "status": "passed",
        "audit_events": len(audit_events),
        "usage_records": len(usage_records),
        "actions": sorted(actions),
        "resources": sorted(resources),
        "billable": False,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
