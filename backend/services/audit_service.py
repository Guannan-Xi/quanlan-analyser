from backend.models.governance import AuditEventRead
from backend.services import state_store

REGISTRY = "audit_events"


def record_event(
    *,
    action: str,
    object_type: str,
    object_id: str,
    organization_id: str = "local-org",
    project_id: str | None = None,
    actor_user_id: str = "local-user",
    metadata_json: dict | None = None,
) -> AuditEventRead:
    event = AuditEventRead(
        organization_id=organization_id,
        project_id=project_id,
        actor_user_id=actor_user_id,
        action=action,
        object_type=object_type,
        object_id=object_id,
        metadata_json=metadata_json or {},
    )
    state_store.upsert_item(REGISTRY, event)
    return event
