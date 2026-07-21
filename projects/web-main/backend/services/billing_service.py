from datetime import datetime, timezone

from fastapi import HTTPException

from backend.models.governance import BillingTransactionRead, PaymentConfirm, RechargeCreate, RechargeOrderRead
from backend.services import account_service, audit_service, state_store

RECHARGES = "recharge_orders"
TRANSACTIONS = "billing_transactions"
SUPPORTED_PAYMENT_METHODS = {"alipay", "wechat_pay", "manual_offline"}
PAYMENT_PROVIDER_MODE = "sandbox"
TASK_PRICE_CREDITS = {
    "qc": 1.0,
    "preprocess": 1.0,
    "psd": 5.0,
    "band_power": 5.0,
    "erp": 5.0,
    "multitaper_psd_tfr": 6.0,
}


def _load_orders() -> dict[str, RechargeOrderRead]:
    return state_store.load_registry(RECHARGES, RechargeOrderRead)


def _load_transactions() -> dict[str, BillingTransactionRead]:
    return state_store.load_registry(TRANSACTIONS, BillingTransactionRead)


def _public_account(account_id: str) -> dict:
    account = account_service.get_account(account_id)
    payload = account.model_dump(mode="json")
    payload.pop("password_hash", None)
    payload.pop("password_salt", None)
    return payload


def get_wallet(account_id: str = "demo-customer") -> dict:
    account = account_service.get_account(account_id)
    transactions = [
        tx.model_dump(mode="json")
        for tx in _load_transactions().values()
        if tx.account_id == account.id
    ]
    orders = [
        order.model_dump(mode="json")
        for order in _load_orders().values()
        if order.account_id == account.id
    ]
    return {
        "account": _public_account(account.id),
        "balance_credits": account.balance_credits,
        "trial_credits": account.trial_credits,
        "total_recharged_credits": account.total_recharged_credits,
        "total_spent_credits": account.total_spent_credits,
        "transactions": sorted(transactions, key=lambda item: item["created_at"], reverse=True),
        "recharge_orders": sorted(orders, key=lambda item: item["created_at"], reverse=True),
        "payment_provider_mode": PAYMENT_PROVIDER_MODE,
        "supported_payment_methods": sorted(SUPPORTED_PAYMENT_METHODS - {"manual_offline"}),
    }


def create_recharge_order(payload: RechargeCreate) -> RechargeOrderRead:
    if payload.amount_credits <= 0:
        raise HTTPException(status_code=422, detail="Recharge amount must be positive")
    if payload.payment_method not in SUPPORTED_PAYMENT_METHODS:
        raise HTTPException(status_code=422, detail=f"Unsupported payment method: {payload.payment_method}")
    account = account_service.get_account(payload.account_id)
    order = RechargeOrderRead(
        account_id=account.id,
        amount_credits=round(float(payload.amount_credits), 2),
        payment_method=payload.payment_method,
        note=payload.note,
    )
    if payload.payment_method == "alipay":
        order.payment_url = f"qlanalyser://pay/alipay/{order.id}"
        order.qr_code_url = f"data:text/plain,ALIPAY_SANDBOX_ORDER_{order.id}"
    elif payload.payment_method == "wechat_pay":
        order.payment_url = f"qlanalyser://pay/wechat/{order.id}"
        order.qr_code_url = f"data:text/plain,WECHAT_PAY_SANDBOX_ORDER_{order.id}"
    else:
        order.payment_url = f"qlanalyser://pay/manual/{order.id}"
    state_store.upsert_item(RECHARGES, order)
    audit_service.record_event(
        action="billing.recharge_order.created",
        object_type="recharge_order",
        object_id=order.id,
        organization_id=account.organization_name or "local-org",
        actor_user_id=account.id,
        metadata_json={"amount_credits": order.amount_credits, "payment_method": order.payment_method},
    )
    return order


def get_recharge_order(order_id: str) -> RechargeOrderRead:
    try:
        return _load_orders()[order_id]
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Recharge order not found") from exc


def confirm_recharge_order(order_id: str, payload: PaymentConfirm | None = None) -> RechargeOrderRead:
    with state_store.atomic_cross_registry_lock([RECHARGES, TRANSACTIONS, "accounts"]):
        orders = state_store.load_registry(RECHARGES, RechargeOrderRead)
        order = orders.get(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Recharge order not found")
        if payload and payload.status not in {"paid", "failed", "cancelled"}:
            raise HTTPException(status_code=422, detail="Unsupported payment status")
        if order.status == "paid":
            return order
        if payload and payload.status in {"failed", "cancelled"}:
            order.status = payload.status
            order.provider_trade_no = payload.provider_trade_no
            state_store.upsert_item(RECHARGES, order)
            return order
        account = account_service.get_account(order.account_id)
        account.balance_credits = round(account.balance_credits + order.amount_credits, 2)
        account.total_recharged_credits = round(account.total_recharged_credits + order.amount_credits, 2)
        account_service.update_account(account)
        order.status = "paid"
        order.provider_trade_no = payload.provider_trade_no if payload else ""
        order.paid_at = datetime.now(timezone.utc)
        state_store.upsert_item(RECHARGES, order)
        tx = BillingTransactionRead(
            account_id=account.id,
            direction="credit",
            amount_credits=order.amount_credits,
            balance_after_credits=account.balance_credits,
            source_type="recharge_order",
            source_id=order.id,
            description=f"{order.payment_method} recharge",
            metadata_json={"payment_method": order.payment_method, "provider_trade_no": order.provider_trade_no},
        )
        state_store.upsert_item(TRANSACTIONS, tx)
        audit_service.record_event(
            action="billing.recharge_order.paid",
            object_type="recharge_order",
            object_id=order.id,
            organization_id=account.organization_name or "local-org",
            actor_user_id=account.id,
            metadata_json={"amount_credits": order.amount_credits, "payment_method": order.payment_method},
        )
        return order


def charge_analysis_task(*, account_id: str, task_id: str, module_name: str, quantity_credits: float, metadata_json: dict | None = None) -> BillingTransactionRead:
    with state_store.atomic_cross_registry_lock([TRANSACTIONS, "accounts"]):
        normalized_account_id = normalize_account_id(account_id)
        amount = round(max(float(quantity_credits), 0.0), 2)
        if amount <= 0:
            amount = 1.0
        for tx in _load_transactions().values():
            if (
                tx.source_type == "analysis_task"
                and tx.source_id == task_id
                and tx.direction == "debit"
                and tx.status == "posted"
                and tx.account_id == normalized_account_id
                and round(float(tx.amount_credits or 0), 2) == amount
                and (str(module_name).upper() in tx.description.upper() or tx.metadata_json.get("module_name") == module_name)
            ):
                return tx
        account = account_service.get_account(normalized_account_id)
        if account.balance_credits < amount:
            raise HTTPException(status_code=402, detail={"message": "Insufficient balance", "required_credits": amount, "balance_credits": account.balance_credits})
        account.balance_credits = round(account.balance_credits - amount, 2)
        account.total_spent_credits = round(account.total_spent_credits + amount, 2)
        account_service.update_account(account)
        tx = BillingTransactionRead(
            account_id=account.id,
            direction="debit",
            amount_credits=amount,
            balance_after_credits=account.balance_credits,
            source_type="analysis_task",
            source_id=task_id,
            description=f"{module_name.upper()} analysis task",
            metadata_json={**(metadata_json or {}), "module_name": module_name},
        )
        state_store.upsert_item(TRANSACTIONS, tx)
        audit_service.record_event(
            action="billing.analysis_task.charged",
            object_type="analysis_task",
            object_id=task_id,
            organization_id=account.organization_name or "local-org",
            actor_user_id=account.id,
            metadata_json={"amount_credits": amount, "module_name": module_name},
        )
        return tx


def has_posted_analysis_task_charge(
    task_id: str,
    transaction_id: str | None = None,
    *,
    account_id: str | None = None,
    module_name: str | None = None,
    expected_credits: float | None = None,
) -> bool:
    normalized_account_id = normalize_account_id(account_id) if account_id else None
    expected_amount = round(float(expected_credits), 2) if expected_credits is not None else None
    return any(
        tx.source_type == "analysis_task"
        and tx.source_id == task_id
        and tx.direction == "debit"
        and tx.status == "posted"
        and (transaction_id is None or tx.id == transaction_id)
        and (normalized_account_id is None or tx.account_id == normalized_account_id)
        and (module_name is None or str(module_name).upper() in tx.description.upper() or tx.metadata_json.get("module_name") == module_name)
        and (expected_amount is None or round(float(tx.amount_credits or 0), 2) == expected_amount)
        for tx in _load_transactions().values()
    )


def list_recharge_orders() -> list[dict]:
    return [order.model_dump(mode="json") for order in _load_orders().values()]


def list_transactions() -> list[dict]:
    return [tx.model_dump(mode="json") for tx in _load_transactions().values()]


def normalize_account_id(account_id: str | None) -> str:
    if not account_id or account_id in {"local-user", "demo", "customer"}:
        return "demo-customer"
    try:
        account_service.get_account(account_id)
    except HTTPException as exc:
        if exc.status_code == 404:
            return "demo-customer"
        raise
    return account_id


def estimate_task_price(module_name: str, workflow_id: str | None = None) -> float:
    if workflow_id in {"qc_waveform_preview", "qc_filter_preview", "qc_snapshot"}:
        return 0.5
    return TASK_PRICE_CREDITS.get(module_name, 2.0)


def assert_sufficient_balance(account_id: str | None, amount_credits: float) -> None:
    account = account_service.get_account(normalize_account_id(account_id))
    if account.balance_credits < amount_credits:
        raise HTTPException(
            status_code=402,
            detail={
                "message": "Insufficient balance",
                "required_credits": amount_credits,
                "balance_credits": account.balance_credits,
            },
        )


def refund_failed_task(*, account_id: str, task_id: str, amount_credits: float, reason: str = "Task failed") -> BillingTransactionRead:
    """P0-TASK-02 FIX: Refund credits when analysis task fails.
    
    Args:
        account_id: The account to refund
        task_id: The failed task ID
        amount_credits: Amount to refund
        reason: Reason for refund
        
    Returns:
        BillingTransactionRead: The refund transaction record
    """
    with state_store.atomic_cross_registry_lock([TRANSACTIONS, "accounts"]):
        account = account_service.get_account(normalize_account_id(account_id))
        amount = round(max(float(amount_credits), 0.0), 2)
        
        if amount <= 0:
            return None
        
        # Credit back to account
        account.balance_credits = round(account.balance_credits + amount, 2)
        account.total_spent_credits = round(account.total_spent_credits - amount, 2)
        account_service.update_account(account)
        
        # Create refund transaction
        tx = BillingTransactionRead(
            account_id=account.id,
            direction="credit",
            amount_credits=amount,
            balance_after_credits=account.balance_credits,
            source_type="task_refund",
            source_id=task_id,
            description=f"Refund: {reason}",
            metadata_json={"reason": reason, "original_task_id": task_id},
        )
        state_store.upsert_item(TRANSACTIONS, tx)
        
        # Audit the refund
        audit_service.record_event(
            action="billing.task_refund.completed",
            object_type="analysis_task",
            object_id=task_id,
            organization_id=account.organization_name or "local-org",
            actor_user_id=account.id,
            metadata_json={"amount_credits": amount, "reason": reason},
        )
        
        return tx
