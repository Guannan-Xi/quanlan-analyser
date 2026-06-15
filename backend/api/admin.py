from fastapi import APIRouter

router = APIRouter()


@router.get("/admin/dashboard")
def get_admin_dashboard() -> dict:
    return {
        "customers": 18,
        "recharge_today": 6800.0,
        "consumption_today": 1240.0,
        "running_tasks": 4,
        "failed_tasks": 1,
        "worker_status": "3/3 online",
    }


@router.get("/admin/tasks/failed")
def list_failed_tasks() -> list[dict]:
    return [{"task_id": "task_demo_failed", "reason": "event mapping missing", "status": "needs_review"}]

