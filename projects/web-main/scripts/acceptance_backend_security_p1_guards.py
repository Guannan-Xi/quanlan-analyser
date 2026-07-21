from __future__ import annotations

import asyncio
import importlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

WINDOWS_ABSOLUTE_PATH_RE = re.compile(r"(?i)\b[a-z]:[\\/]")


class BytesUpload:
    def __init__(self, filename: str, content: bytes) -> None:
        self.filename = filename
        self._content = content

    async def read(self) -> bytes:
        return self._content


def require(condition: bool, message: str, detail: Any = None) -> None:
    if not condition:
        raise AssertionError(f"{message}: {detail}")


def expect_http(label: str, expected_status: int, fn) -> None:
    try:
        result = fn()
        if asyncio.iscoroutine(result):
            asyncio.run(result)
    except HTTPException as exc:
        require(exc.status_code == expected_status, f"{label} status", exc.status_code)
        require(not contains_absolute_path(exc.detail), f"{label} detail hides absolute paths", exc.detail)
        return
    raise AssertionError(f"{label}: expected HTTP {expected_status}")


def contains_absolute_path(value: Any) -> bool:
    text = json.dumps(value, ensure_ascii=False, default=str)
    return bool(WINDOWS_ABSOLUTE_PATH_RE.search(text))


def assert_public_response_safe(label: str, payload: Any) -> None:
    require(not contains_absolute_path(payload), f"{label} must not expose absolute paths", payload)
    text = json.dumps(payload, ensure_ascii=False, default=str)
    require("invoice_file_path" not in text, f"{label} hides invoice_file_path", payload)
    require("attachment_path" not in text, f"{label} hides attachment_path", payload)


def restore_env(previous: dict[str, str | None]) -> None:
    for key, value in previous.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def assert_lab_edf_reviewer_gate() -> None:
    import backend.api.lab_edf_reviewer as lab_edf_reviewer

    previous = {
        "QLANALYSER_ENV": os.environ.get("QLANALYSER_ENV"),
        "QLANALYSER_SANDBOX_MODE": os.environ.get("QLANALYSER_SANDBOX_MODE"),
        "QLANALYSER_PUBLIC_LAB_EDF_REVIEWER_ENABLED": os.environ.get("QLANALYSER_PUBLIC_LAB_EDF_REVIEWER_ENABLED"),
    }
    try:
        os.environ.pop("QLANALYSER_ENV", None)
        os.environ["QLANALYSER_SANDBOX_MODE"] = "false"
        os.environ.pop("QLANALYSER_PUBLIC_LAB_EDF_REVIEWER_ENABLED", None)
        expect_http("edf reviewer unknown env status", 404, lab_edf_reviewer.get_status)
        expect_http("edf reviewer unknown env inspect", 404, lambda: lab_edf_reviewer.inspect_edf(file=None))
        expect_http(
            "edf reviewer unknown env waveform",
            404,
            lambda: lab_edf_reviewer.render_waveform(file=None, channels='["EEG Fpz-Cz"]'),
        )

        os.environ["QLANALYSER_ENV"] = "production"
        expect_http("edf reviewer production default status", 404, lab_edf_reviewer.get_status)

        os.environ["QLANALYSER_PUBLIC_LAB_EDF_REVIEWER_ENABLED"] = "true"
        enabled_status = lab_edf_reviewer.get_status()
        require(enabled_status["status"] == "ready", "edf reviewer explicit public flag enables status", enabled_status)
        assert_public_response_safe("edf reviewer status", enabled_status)

        os.environ["QLANALYSER_PUBLIC_LAB_EDF_REVIEWER_ENABLED"] = "false"
        os.environ["QLANALYSER_ENV"] = "test"
        local_status = lab_edf_reviewer.get_status()
        require(local_status["service"] == "edf_reviewer_lab", "edf reviewer local/test env enables status", local_status)
        assert_public_response_safe("edf reviewer local status", local_status)
    finally:
        restore_env(previous)


def load_isolated_invoice_modules(state_root: Path, invoice_root: Path):
    os.environ["QLANALYSER_ENV"] = "test"
    os.environ["QLANALYSER_SANDBOX_MODE"] = "true"
    os.environ["QLANALYSER_STATE_ROOT"] = str(state_root)

    import backend.api.billing as billing_api
    import backend.models.governance as governance_model
    import backend.services.account_service as account_service
    import backend.services.audit_service as audit_service
    import backend.services.invoice_service as invoice_service
    import backend.services.state_store as state_store

    for module in (state_store, audit_service, account_service, invoice_service, billing_api):
        importlib.reload(module)

    invoice_service.INVOICE_ROOT = invoice_root
    return governance_model, state_store, account_service, invoice_service, billing_api


def assert_invoice_and_inbox_guards() -> None:
    previous = {
        "QLANALYSER_ENV": os.environ.get("QLANALYSER_ENV"),
        "QLANALYSER_SANDBOX_MODE": os.environ.get("QLANALYSER_SANDBOX_MODE"),
        "QLANALYSER_STATE_ROOT": os.environ.get("QLANALYSER_STATE_ROOT"),
    }
    try:
        with tempfile.TemporaryDirectory(prefix="qlanalyser-p1-security-") as tmp:
            tmp_root = Path(tmp)
            governance_model, state_store, _account_service, invoice_service, billing_api = load_isolated_invoice_modules(
                tmp_root / "state",
                tmp_root / "invoices",
            )
            account = governance_model.AccountRead(
                id="acct_invoice_guard",
                email="invoice-guard@example.test",
                balance_credits=250.0,
                trial_credits=30.0,
                total_recharged_credits=200.0,
            )
            state_store.upsert_item("accounts", account)

            first_invoice = billing_api.create_invoice_request(
                governance_model.InvoiceRequestCreate(
                    account_id=account.id,
                    invoice_title="Invoice Guard",
                    amount_credits=120.0,
                    recipient_email=account.email,
                ),
                current=account,
            )
            require(first_invoice["status"] == "pending", "valid invoice remains pending for admin review", first_invoice)
            assert_public_response_safe("created invoice API response", first_invoice)

            expect_http(
                "invoice amount cannot exceed remaining recharged credits",
                422,
                lambda: billing_api.create_invoice_request(
                    governance_model.InvoiceRequestCreate(
                        account_id=account.id,
                        invoice_title="Invoice Guard Excess",
                        amount_credits=90.0,
                        recipient_email=account.email,
                    ),
                    current=account,
                ),
            )

            low_recharge_account = governance_model.AccountRead(
                id="acct_low_recharge_guard",
                email="low-recharge@example.test",
                balance_credits=100.0,
                trial_credits=100.0,
                total_recharged_credits=50.0,
            )
            state_store.upsert_item("accounts", low_recharge_account)
            expect_http(
                "single invoice cannot exceed total recharged credits",
                422,
                lambda: billing_api.create_invoice_request(
                    governance_model.InvoiceRequestCreate(
                        account_id=low_recharge_account.id,
                        invoice_title="Too Large",
                        amount_credits=60.0,
                        recipient_email=low_recharge_account.email,
                    ),
                    current=low_recharge_account,
                ),
            )

            admin = governance_model.AccountRead(id="acct_admin_guard", email="ops@quanlan.cn", role="admin")
            issued = asyncio.run(
                billing_api.issue_invoice(
                    first_invoice["id"],
                    file=BytesUpload("invoice.pdf", b"%PDF-1.4\n% invoice guard\n"),
                    admin=admin,
                )
            )
            require(issued["status"] == "issued", "admin issuance remains available", issued)
            assert_public_response_safe("issued invoice API response", issued)
            assert_public_response_safe("invoice list response", invoice_service.list_invoices(account.id))

            inbox = invoice_service.list_inbox(account.id)
            require(len(inbox) == 1 and inbox[0]["attachment_name"] == "invoice.pdf", "inbox lists issued invoice", inbox)
            assert_public_response_safe("inbox list response", inbox)

            message = next(iter(state_store.load_registry("inbox_messages", governance_model.InboxMessageRead).values()))
            attachment_path = invoice_service.get_inbox_attachment_for_account(message.id, account)
            attachment_path.relative_to(invoice_service.INVOICE_ROOT.resolve())
            require(attachment_path.read_bytes().startswith(b"%PDF"), "inbox attachment can be downloaded inside invoice root")

            outside_path = tmp_root / "outside.pdf"
            outside_path.write_bytes(b"%PDF-1.4\n% outside\n")
            outside_message = governance_model.InboxMessageRead(
                id="inbox_outside_guard",
                account_id=account.id,
                subject="Outside invoice",
                body="Should be blocked",
                attachment_path=str(outside_path),
                attachment_name="outside.pdf",
                source_id=first_invoice["id"],
            )
            state_store.upsert_item("inbox_messages", outside_message)
            expect_http(
                "inbox attachment outside invoice root is blocked",
                403,
                lambda: invoice_service.get_inbox_attachment_for_account(outside_message.id, account),
            )
    finally:
        restore_env(previous)


def main() -> None:
    assert_lab_edf_reviewer_gate()
    assert_invoice_and_inbox_guards()
    print(
        json.dumps(
            {
                "status": "passed",
                "checks": [
                    "lab_edf_reviewer_default_closed_gate",
                    "invoice_recharged_credit_ceiling",
                    "inbox_attachment_invoice_root_boundary",
                    "public_responses_hide_absolute_paths",
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
