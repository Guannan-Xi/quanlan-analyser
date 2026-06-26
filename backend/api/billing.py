from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from backend.models.governance import AccountRead, InvoiceRequestCreate, PaymentConfirm, RechargeCreate
from backend.services import account_service, billing_service, invoice_service

router = APIRouter()


@router.get("/billing/wallet")
def get_wallet(account_id: str = "demo-customer", current: AccountRead = Depends(account_service.require_current_account)) -> dict:
    account = account_service.assert_same_account_or_admin(account_id, current)
    return billing_service.get_wallet(account.id)


@router.post("/billing/recharge")
def create_recharge_order(payload: RechargeCreate, current: AccountRead = Depends(account_service.require_current_account)) -> dict:
    account_service.assert_same_account_or_admin(payload.account_id, current)
    return billing_service.create_recharge_order(payload).model_dump(mode="json")


@router.post("/billing/recharge/{order_id}/confirm")
def confirm_recharge_order(order_id: str, payload: PaymentConfirm | None = None, current: AccountRead = Depends(account_service.require_current_account)) -> dict:
    order = billing_service.get_recharge_order(order_id)
    account_service.assert_same_account_or_admin(order.account_id, current)
    return billing_service.confirm_recharge_order(order_id, payload).model_dump(mode="json")


@router.get("/billing/ledger")
def list_ledger(account_id: str | None = None, current: AccountRead = Depends(account_service.require_current_account)) -> list[dict]:
    if current.role == "admin":
        transactions = billing_service.list_transactions()
        if account_id:
            transactions = [item for item in transactions if item.get("account_id") == account_id]
        return transactions
    if account_id and account_id != current.id:
        raise HTTPException(status_code=403, detail="Account access denied")
    return [item for item in billing_service.list_transactions() if item.get("account_id") == current.id]


@router.post("/invoices")
def create_invoice_request(payload: InvoiceRequestCreate, current: AccountRead = Depends(account_service.require_current_account)) -> dict:
    account_service.assert_same_account_or_admin(payload.account_id, current)
    return invoice_service.create_invoice_request(payload).model_dump(mode="json")


@router.get("/invoices")
def list_invoices(account_id: str | None = None, current: AccountRead = Depends(account_service.require_current_account)) -> list[dict]:
    if current.role == "admin":
        return invoice_service.list_invoices(account_id)
    if account_id and account_id != current.id:
        raise HTTPException(status_code=403, detail="Account access denied")
    return invoice_service.list_invoices(current.id)


@router.get("/inbox")
def list_inbox(account_id: str = "demo-customer", current: AccountRead = Depends(account_service.require_current_account)) -> list[dict]:
    account = account_service.assert_same_account_or_admin(account_id, current)
    return invoice_service.list_inbox(account.id)


@router.get("/inbox/{message_id}/attachment")
def get_inbox_attachment(message_id: str, current: AccountRead = Depends(account_service.require_current_account)) -> FileResponse:
    path = invoice_service.get_inbox_attachment_for_account(message_id, current)
    return FileResponse(path, filename=path.name)


@router.post("/admin/invoices/{invoice_id}/issue")
async def issue_invoice(invoice_id: str, issued_by: str = "ops@quanlan.cn", file: UploadFile = File(...), admin: AccountRead = Depends(account_service.require_admin_account)) -> dict:
    return (await invoice_service.issue_invoice(invoice_id, file, admin.email)).model_dump(mode="json")
