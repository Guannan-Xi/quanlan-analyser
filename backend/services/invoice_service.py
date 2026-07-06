from datetime import datetime, timezone
import math
from pathlib import Path

from fastapi import HTTPException, UploadFile

from backend.models.governance import AccountRead, InboxMessageRead, InvoiceRequestCreate, InvoiceRequestRead
from backend.services import account_service, audit_service, state_store

ROOT = Path(__file__).resolve().parents[2]
INVOICE_ROOT = ROOT / "data" / "invoices"
INVOICES = "invoice_requests"
INBOX = "inbox_messages"
_INVOICE_COMMITTED_STATUSES = {"pending", "issued"}


def _load_invoices() -> dict[str, InvoiceRequestRead]:
    return state_store.load_registry(INVOICES, InvoiceRequestRead)


def _load_inbox() -> dict[str, InboxMessageRead]:
    return state_store.load_registry(INBOX, InboxMessageRead)


def _invoice_root() -> Path:
    return INVOICE_ROOT.resolve()


def _assert_path_within_invoice_root(raw_path: Path) -> Path:
    resolved = raw_path.resolve()
    try:
        resolved.relative_to(_invoice_root())
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="Inbox attachment path is outside the allowed directory") from exc
    return resolved


def public_invoice_payload(invoice: InvoiceRequestRead) -> dict:
    payload = invoice.model_dump(mode="json")
    payload.pop("invoice_file_path", None)
    return payload


def public_inbox_payload(message: InboxMessageRead) -> dict:
    payload = message.model_dump(mode="json")
    payload.pop("attachment_path", None)
    return payload


def _committed_invoice_amount(account_id: str, invoices: dict[str, InvoiceRequestRead]) -> float:
    return round(
        sum(
            float(invoice.amount_credits or 0)
            for invoice in invoices.values()
            if invoice.account_id == account_id and invoice.status in _INVOICE_COMMITTED_STATUSES
        ),
        2,
    )


def _assert_invoice_amount_available(
    account: AccountRead,
    amount_credits: float,
    invoices: dict[str, InvoiceRequestRead],
) -> None:
    total_recharged = round(max(float(account.total_recharged_credits or 0), 0.0), 2)
    committed = _committed_invoice_amount(account.id, invoices)
    available = round(max(total_recharged - committed, 0.0), 2)
    if amount_credits > available:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "INVOICE_AMOUNT_EXCEEDS_RECHARGED_BALANCE",
                "message": "Invoice amount exceeds available recharged credits",
                "requested_credits": amount_credits,
                "available_invoice_credits": available,
                "total_recharged_credits": total_recharged,
                "committed_invoice_credits": committed,
            },
        )


def create_invoice_request(payload: InvoiceRequestCreate) -> InvoiceRequestRead:
    with state_store.atomic_cross_registry_lock([account_service.ACCOUNTS, INVOICES]):
        account = account_service.get_account(payload.account_id)
        amount_credits = round(float(payload.amount_credits), 2)
        if not math.isfinite(amount_credits) or amount_credits <= 0:
            raise HTTPException(status_code=422, detail="Invoice amount must be positive")
        if not payload.invoice_title.strip():
            raise HTTPException(status_code=422, detail="Invoice title is required")
        if not payload.recipient_email.strip():
            raise HTTPException(status_code=422, detail="Recipient email is required")
        invoices = _load_invoices()
        _assert_invoice_amount_available(account, amount_credits, invoices)
        invoice_payload = payload.model_dump()
        invoice_payload["account_id"] = account.id
        invoice_payload["amount_credits"] = amount_credits
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
    return [public_invoice_payload(invoice) for invoice in invoices]


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
    target_dir = _invoice_root() / invoice.id
    target_dir.mkdir(parents=True, exist_ok=True)
    target = _assert_path_within_invoice_root(target_dir / filename)
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
    return [public_inbox_payload(message) for message in sorted(messages, key=lambda item: item.created_at, reverse=True)]


def get_inbox_attachment(message_id: str) -> Path:
    messages = _load_inbox()
    message = messages.get(message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Inbox message not found")
    if not message.attachment_path:
        raise HTTPException(status_code=410, detail="Attachment is not available")
    path = _assert_path_within_invoice_root(Path(message.attachment_path))
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=410, detail="Attachment is not available")
    return path


def get_inbox_attachment_for_account(message_id: str, current: AccountRead) -> Path:
    message = _load_inbox().get(message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Inbox message not found")
    if current.role != "admin" and message.account_id != current.id:
        raise HTTPException(status_code=403, detail="Inbox attachment access denied")
    return get_inbox_attachment(message_id)
