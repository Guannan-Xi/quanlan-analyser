from fastapi import APIRouter

from backend.services import task_service

router = APIRouter()


@router.get("/admin/dashboard")
def get_admin_dashboard() -> dict:
    tasks = list(task_service._tasks.values())  # local in-memory V01 store
    return {
        "customers": 0,
        "billing_enabled": False,
        "total_tasks": len(tasks),
        "running_tasks": sum(1 for task in tasks if task.status == "running"),
        "completed_tasks": sum(1 for task in tasks if task.status == "completed"),
        "failed_tasks": sum(1 for task in tasks if task.status == "failed"),
        "worker_status": "local synchronous worker",
    }


@router.get("/admin/tasks/failed")
def list_failed_tasks() -> list[dict]:
    return [
        {"task_id": task.id, "module": task.module_name, "reason": task.error_message, "status": task.status}
        for task in task_service._tasks.values()
        if task.status == "failed"
    ]
