import argparse
import json
import os
import sys
import time
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.main import app


def require(condition: bool, message: str, detail=None) -> None:
    if not condition:
        raise AssertionError(f"{message}: {detail}")


def auth_headers(session: dict) -> dict:
    return {"Authorization": f"Bearer {session['token']}"}


def post_json(client: TestClient, path: str, payload: dict, expected: int = 200, headers: dict | None = None) -> dict:
    response = client.post(path, json=payload, headers=headers or {})
    require(response.status_code == expected, f"{path} status", response.text)
    return response.json()


def write_evidence(path: Path | None, payload: dict) -> None:
    if not path:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate registration, sandbox billing, invoice, inbox, and admin API flow.")
    parser.add_argument(
        "--evidence-path",
        type=Path,
        default=Path(os.getenv("QLANALYSER_OPS_BILLING_EVIDENCE_PATH")) if os.getenv("QLANALYSER_OPS_BILLING_EVIDENCE_PATH") else None,
    )
    args = parser.parse_args()

    suffix = str(int(time.time() * 1000))
    with TestClient(app) as client:
        email_target = f"ops-{suffix}@example.com"
        code = post_json(client, "/api/auth/verification-code", {"channel": "email", "target": email_target})
        require(code["provider_mode"] == "sandbox" and code["sandbox_code"] == "000000", "email verification sandbox", code)

        email_session = post_json(
            client,
            "/api/auth/register",
            {
                "register_method": "email",
                "email": email_target,
                "password": "StrongPass123",
                "name": "Ops Email User",
                "organization_name": "Ops Lab",
                "verification_code": "000000",
            },
        )
        email_account = email_session["account"]
        require(email_account["register_method"] == "email", "email registration method", email_account)

        phone = f"139{suffix[-8:]}"
        phone_code = post_json(client, "/api/auth/verification-code", {"channel": "phone", "target": phone})
        require(phone_code["sandbox_code"] == "000000", "phone verification sandbox", phone_code)
        phone_session = post_json(
            client,
            "/api/auth/register",
            {
                "register_method": "phone",
                "phone": phone,
                "password": "StrongPass123",
                "name": "Ops Phone User",
                "verification_code": "000000",
            },
        )
        require(phone_session["account"]["register_method"] == "phone", "phone registration method", phone_session)

        wechat_session = post_json(
            client,
            "/api/auth/register",
            {
                "register_method": "wechat",
                "wechat_openid": f"wx_{suffix}",
                "wechat_nickname": "Ops Wechat User",
                "name": "Ops Wechat User",
            },
        )
        require(wechat_session["account"]["register_method"] == "wechat", "wechat registration method", wechat_session)

        customer_headers = auth_headers(email_session)
        phone_headers = auth_headers(phone_session)
        admin_session = post_json(client, "/api/auth/login", {"email": "ops@quanlan.cn", "password": "ops-demo-2026"})
        admin_headers = auth_headers(admin_session)

        unauth_admin = client.get("/api/admin/overview")
        require(unauth_admin.status_code == 401, "admin overview rejects anonymous callers", unauth_admin.text)
        unauth_wallet = client.get(f"/api/billing/wallet?account_id={email_account['id']}")
        require(unauth_wallet.status_code == 401, "wallet rejects anonymous callers", unauth_wallet.text)
        unauth_recharge = client.post(
            "/api/billing/recharge",
            json={"account_id": email_account["id"], "amount_credits": 10, "payment_method": "alipay"},
        )
        require(unauth_recharge.status_code == 401, "recharge rejects anonymous callers", unauth_recharge.text)
        customer_admin = client.get("/api/admin/overview", headers=customer_headers)
        require(customer_admin.status_code == 403, "admin overview rejects customer callers", customer_admin.text)
        cross_wallet = client.get(f"/api/billing/wallet?account_id={phone_session['account']['id']}", headers=customer_headers)
        require(cross_wallet.status_code == 403, "wallet rejects cross-account customer", cross_wallet.text)
        cross_ledger = client.get(f"/api/billing/ledger?account_id={phone_session['account']['id']}", headers=customer_headers)
        require(cross_ledger.status_code == 403, "ledger rejects cross-account customer", cross_ledger.text)
        cross_invoices = client.get(f"/api/invoices?account_id={phone_session['account']['id']}", headers=customer_headers)
        require(cross_invoices.status_code == 403, "invoice list rejects cross-account customer", cross_invoices.text)
        cross_inbox = client.get(f"/api/inbox?account_id={phone_session['account']['id']}", headers=customer_headers)
        require(cross_inbox.status_code == 403, "inbox rejects cross-account customer", cross_inbox.text)
        cross_recharge = client.post(
            "/api/billing/recharge",
            json={"account_id": phone_session["account"]["id"], "amount_credits": 10, "payment_method": "alipay"},
            headers=customer_headers,
        )
        require(cross_recharge.status_code == 403, "recharge rejects cross-account customer", cross_recharge.text)

        wallet_before_response = client.get(f"/api/billing/wallet?account_id={email_account['id']}", headers=customer_headers)
        require(wallet_before_response.status_code == 200, "wallet authorized status", wallet_before_response.text)
        wallet_before = wallet_before_response.json()
        require(wallet_before["balance_credits"] >= 30, "trial credits available", wallet_before)

        alipay_order = post_json(
            client,
            "/api/billing/recharge",
            {"account_id": email_account["id"], "amount_credits": 120, "payment_method": "alipay"},
            headers=customer_headers,
        )
        require(alipay_order["status"] == "pending" and "alipay" in alipay_order["payment_url"], "alipay order pending", alipay_order)
        cross_confirm = client.post(
            f"/api/billing/recharge/{alipay_order['id']}/confirm",
            json={"status": "paid", "provider_trade_no": f"CROSS-{suffix}"},
            headers=phone_headers,
        )
        require(cross_confirm.status_code == 403, "recharge confirm rejects cross-account customer", cross_confirm.text)
        paid_alipay = post_json(
            client,
            f"/api/billing/recharge/{alipay_order['id']}/confirm",
            {"status": "paid", "provider_trade_no": f"ALI-{suffix}"},
            headers=customer_headers,
        )
        require(paid_alipay["status"] == "paid", "alipay paid", paid_alipay)

        wechat_order = post_json(
            client,
            "/api/billing/recharge",
            {"account_id": email_account["id"], "amount_credits": 80, "payment_method": "wechat_pay"},
            headers=customer_headers,
        )
        require(wechat_order["status"] == "pending" and "wechat" in wechat_order["payment_url"], "wechat order pending", wechat_order)
        paid_wechat = post_json(
            client,
            f"/api/billing/recharge/{wechat_order['id']}/confirm",
            {"status": "paid", "provider_trade_no": f"WX-{suffix}"},
            headers=customer_headers,
        )
        require(paid_wechat["status"] == "paid", "wechat paid", paid_wechat)

        wallet_after = client.get(f"/api/billing/wallet?account_id={email_account['id']}", headers=customer_headers).json()
        require(wallet_after["balance_credits"] >= wallet_before["balance_credits"] + 200, "wallet credited", wallet_after)
        require(len(wallet_after["transactions"]) >= 2, "wallet ledger records", wallet_after["transactions"])

        invoice = post_json(
            client,
            "/api/invoices",
            {
                "account_id": email_account["id"],
                "invoice_title": "Ops Lab",
                "tax_number": "91310000TEST2026",
                "amount_credits": 200,
                "recipient_email": email_target,
                "recipient_name": "Ops Finance",
                "note": "Acceptance invoice",
            },
            headers=customer_headers,
        )
        require(invoice["status"] == "pending", "invoice pending", invoice)

        admin_invoices_response = client.get("/api/admin/invoices", headers=admin_headers)
        require(admin_invoices_response.status_code == 200, "admin invoices authorized", admin_invoices_response.text)
        admin_invoices = admin_invoices_response.json()
        require(any(item["id"] == invoice["id"] for item in admin_invoices), "admin sees invoice", admin_invoices)

        customer_issue_response = client.post(
            f"/api/admin/invoices/{invoice['id']}/issue",
            data={"issued_by": "customer-spoof@example.com"},
            files={"file": ("customer-spoof.pdf", b"%PDF-1.4\n% should not issue\n", "application/pdf")},
            headers=customer_headers,
        )
        require(customer_issue_response.status_code == 403, "invoice issue rejects customer callers", customer_issue_response.text)
        issue_response = client.post(
            f"/api/admin/invoices/{invoice['id']}/issue",
            data={"issued_by": "spoofed-admin@example.com"},
            files={"file": ("invoice.pdf", b"%PDF-1.4\n% QLanalyser invoice acceptance\n", "application/pdf")},
            headers=admin_headers,
        )
        require(issue_response.status_code == 200, "issue invoice status", issue_response.text)
        issued = issue_response.json()
        require(issued["status"] == "issued" and issued["invoice_file_name"] == "invoice.pdf", "invoice issued", issued)
        require(issued["issued_by"] == admin_session["account"]["email"], "invoice issued_by uses authenticated admin", issued)

        inbox = client.get(f"/api/inbox?account_id={email_account['id']}", headers=customer_headers).json()
        invoice_messages = [item for item in inbox if item["source_id"] == invoice["id"]]
        require(invoice_messages, "customer inbox receives invoice", inbox)
        cross_attachment = client.get(f"/api/inbox/{invoice_messages[0]['id']}/attachment", headers=phone_headers)
        require(cross_attachment.status_code == 403, "invoice attachment rejects cross-account customer", cross_attachment.text)
        attachment = client.get(f"/api/inbox/{invoice_messages[0]['id']}/attachment", headers=customer_headers)
        require(attachment.status_code == 200 and attachment.content.startswith(b"%PDF"), "invoice attachment download", attachment.status_code)

        overview = client.get("/api/admin/overview", headers=admin_headers).json()
        require(overview["pending_invoices"] >= 0 and overview["issued_invoices"] >= 1, "admin overview invoice counts", overview)
        admin_wallet = client.get(f"/api/billing/wallet?account_id={email_account['id']}", headers=admin_headers)
        require(admin_wallet.status_code == 200, "admin can inspect customer wallet", admin_wallet.text)

    payload = {
        "status": "passed",
        "scope": "registration_login_billing_invoice_inbox_admin",
        "email_account_id": email_account["id"],
        "phone_account_id": phone_session["account"]["id"],
        "wechat_account_id": wechat_session["account"]["id"],
        "email_provider_mode": code["provider_mode"],
        "phone_provider_mode": phone_code["provider_mode"],
        "payment_modes": ["alipay_sandbox", "wechat_pay_sandbox"],
        "alipay_order_id": alipay_order["id"],
        "wechat_order_id": wechat_order["id"],
        "invoice_id": invoice["id"],
        "invoice_status": issued["status"],
        "invoice_file_name": issued["invoice_file_name"],
        "invoice_issued_by": issued["issued_by"],
        "wallet_balance": wallet_after["balance_credits"],
        "wallet_transaction_count": len(wallet_after["transactions"]),
        "inbox_messages": len(invoice_messages),
        "admin_pending_invoices": overview["pending_invoices"],
        "admin_issued_invoices": overview["issued_invoices"],
        "rbac_negative_checks": [
            "anonymous_admin_401",
            "anonymous_wallet_401",
            "anonymous_recharge_401",
            "customer_admin_403",
            "cross_account_wallet_403",
            "cross_account_ledger_403",
            "cross_account_invoices_403",
            "cross_account_inbox_403",
            "cross_account_recharge_403",
            "cross_account_recharge_confirm_403",
            "customer_invoice_issue_403",
            "cross_account_attachment_403",
        ],
    }
    write_evidence(args.evidence_path, payload)
    if args.evidence_path:
        payload["evidence_path"] = str(args.evidence_path)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
