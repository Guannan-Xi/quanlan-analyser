from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException, UploadFile

from backend.models.governance import AccountRead, InboxMessageRead, InvoiceRequestCreate, InvoiceRequestRead
from backend.services import account_service, audit_service, state_store

ROOT = Path(__file__).resolve().parents[2]
INVOICE_ROOT = ROOT / "data" / "invoices"
INVOICES = "invoice_requests"
INBOX = "inbox_messages"


def _load_invoices() -> dict[str, InvoiceRequestRead]:
    return state_store.load_registry(INVOICES, InvoiceRequestRead)


def _load_inbox() -> dict[str, InboxMessageRead]:
    return state_store.load_registry(INBOX, InboxMessageRead)


def create_invoice_request(payload: InvoiceRequestCreate) -> InvoiceRequestRead:
    account = account_service.get_account(payload.account_id)
    if payload.amount_credits <= 0:
        raise HTTPException(status_code=422, detail="Invoice amount must be positive")
    if not payload.invoice_title.strip():
        raise HTTPException(status_code=422, detail="Invoice title is required")
    if not payload.recipient_email.strip():
        raise HTTPException(status_code=422, detail="Recipient email is required")
    invoice_payload = payload.model_dump()
    invoice_payload["account_id"] = account.id
    invoice = InvoiceRequestRead(**invoice_payload)
    state_store.upsert_item(INVOICES, invoice)
    audit_service.record_event(
        action="invoice.requested",
        object_type="invoice",
        object_id=invoice.id,
        organization_id=account.organization_name or "local-org",
        actor_user_id=account.id,
        metadata_json={"amount_credits": invoice.amount_credits, "recipient_email": invoice.recipient_email},
    )
    return invoice


def list_invoices(account_id: str | None = None) -> list[dict]:
    invoices = _load_invoices().values()
    if account_id:
        account = account_service.get_account(account_id)
        invoices = [invoice for invoice in invoices if invoice.account_id == account.id]
    return [invoice.model_dump(mode="json") for invoice in invoices]


async def issue_invoice(invoice_id: str, upload: UploadFile | None, issued_by: str = "ops@quanlan.cn") -> InvoiceRequestRead:
    invoices = _load_invoices()
    invoice = invoices.get(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice request not found")
    if invoice.status == "issued":
        return invoice
    if upload is None:
        raise HTTPException(status_code=422, detail="Invoice file is required")

    filename = Path(upload.filename or f"{invoice_id}.pdf").name
    if not filename.lower().endswith((".pdf", ".ofd", ".png", ".jpg", ".jpeg")):
        raise HTTPException(status_code=422, detail="Invoice file must be PDF/OFD/image")
    target_dir = INVOICE_ROOT / invoice.id
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / filename
    content = await upload.read()
    if not content:
        raise HTTPException(status_code=422, detail="Invoice file is empty")
    target.write_bytes(content)

    invoice.status = "issued"
    invoice.invoice_file_path = str(target)
    invoice.invoice_file_name = filename
    invoice.issued_by = issued_by
    invoice.issued_at = datetime.now(timezone.utc)
    invoice.updated_at = invoice.issued_at
    state_store.upsert_item(INVOICES, invoice)

    message = InboxMessageRead(
        account_id=invoice.account_id,
        subject=f"Invoice issued: {invoice.invoice_title}",
        body="Your electronic invoice has been issued and is attached in the QLanalyser inbox.",
        attachment_path=str(target),
        attachment_name=filename,
        source_id=invoice.id,
    )
    state_store.upsert_item(INBOX, message)
    audit_service.record_event(
        action="invoice.issued",
        object_type="invoice",
        object_id=invoice.id,
        actor_user_id=issued_by,
        metadata_json={"invoice_file_name": filename, "inbox_message_id": message.id},
    )
    return invoice


def list_inbox(account_id: str = "demo-customer") -> list[dict]:
    account = account_service.get_account(account_id)
    messages = [item for item in _load_inbox().values() if item.account_id == account.id]
    return [message.model_dump(mode="json") for message in sorted(messages, key=lambda item: item.created_at, reverse=True)]


def get_inbox_attachment(message_id: str) -> Path:
    messages = _load_inbox()
    message = messages.get(message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Inbox message not found")
    path = Path(message.attachment_path)
    if not path.exists():
        raise HTTPException(status_code=410, detail="Attachment is not available")
    return path


def get_inbox_attachment_for_account(message_id: str, current: AccountRead) -> Path:
    message = _load_inbox().get(message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Inbox message not found")
    if current.role != "admin" and message.account_id != current.id:
        raise HTTPException(status_code=403, detail="Inbox attachment access denied")
    return get_inbox_attachment(message_id)
