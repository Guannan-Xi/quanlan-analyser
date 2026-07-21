from backend.services import account_service, billing_service, invoice_service, state_store, task_service

from fastapi import APIRouter, Depends

router = APIRouter()


@router.get("/admin/overview")
def get_admin_overview(_admin=Depends(account_service.require_admin_account)) -> dict:
    accounts = account_service.list_accounts()
    recharge_orders = billing_service.list_recharge_orders()
    transactions = billing_service.list_transactions()
    invoices = invoice_service.list_invoices()
    tasks = task_service.list_tasks()
    return {
        "accounts": len(accounts),
        "active_customers": len([account for account in accounts if account.get("role") == "customer" and account.get("status") == "active"]),
        "tasks": len(tasks),
        "failed_tasks": len([task for task in tasks if task.status == "failed"]),
        "recharge_orders": len(recharge_orders),
        "paid_recharge_orders": len([order for order in recharge_orders if order.get("status") == "paid"]),
        "transactions": len(transactions),
        "invoice_requests": len(invoices),
        "pending_invoices": len([invoice for invoice in invoices if invoice.get("status") == "pending"]),
        "issued_invoices": len([invoice for invoice in invoices if invoice.get("status") == "issued"]),
    }


@router.get("/admin/accounts")
def list_accounts(_admin=Depends(account_service.require_admin_account)) -> list[dict]:
    return account_service.list_accounts()


@router.get("/admin/billing/recharge-orders")
def list_recharge_orders(_admin=Depends(account_service.require_admin_account)) -> list[dict]:
    return billing_service.list_recharge_orders()


@router.get("/admin/billing/transactions")
def list_transactions(_admin=Depends(account_service.require_admin_account)) -> list[dict]:
    return billing_service.list_transactions()


@router.get("/admin/invoices")
def list_invoice_requests(_admin=Depends(account_service.require_admin_account)) -> list[dict]:
    return invoice_service.list_invoices()


@router.get("/admin/tasks")
def list_tasks(_admin=Depends(account_service.require_admin_account)) -> list[dict]:
    return [task.model_dump(mode="json") for task in task_service.list_tasks()]


@router.get("/admin/tasks/failed")
def list_failed_tasks(_admin=Depends(account_service.require_admin_account)) -> list[dict]:
    return [
        {"task_id": task.id, "module": task.module_name, "reason": task.error_message, "status": task.status}
        for task in task_service.list_tasks()
        if task.status == "failed"
    ]


@router.get("/admin/state")
def get_state_status(_admin=Depends(account_service.require_admin_account)) -> dict:
    return state_store.get_state_status()
