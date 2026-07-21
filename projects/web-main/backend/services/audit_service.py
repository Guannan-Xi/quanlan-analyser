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


def list_events(
    *,
    action: str | None = None,
    object_type: str | None = None,
    object_id: str | None = None,
    actor_user_id: str | None = None,
    project_id: str | None = None,
) -> list[AuditEventRead]:
    events = list(state_store.load_registry(REGISTRY, AuditEventRead).values())
    if action is not None:
        events = [event for event in events if event.action == action]
    if object_type is not None:
        events = [event for event in events if event.object_type == object_type]
    if object_id is not None:
        events = [event for event in events if event.object_id == object_id]
    if actor_user_id is not None:
        events = [event for event in events if event.actor_user_id == actor_user_id]
    if project_id is not None:
        events = [event for event in events if event.project_id == project_id]
    return sorted(events, key=lambda event: event.created_at, reverse=True)
