from fastapi import APIRouter

router = APIRouter()


@router.get("/billing/wallet")
def get_wallet() -> dict:
    return {"balance": 1000.0, "frozen": 68.0, "currency": "CNY"}


@router.post("/billing/recharge")
def create_recharge_order(amount: float = 1000.0) -> dict:
    return {"order_id": "recharge_demo_001", "amount": amount, "status": "pending_payment"}


@router.get("/billing/ledger")
def list_ledger() -> list[dict]:
    return [
        {"item": "recharge", "amount": 1000.0, "status": "posted"},
        {"item": "metadata", "amount": -2.0, "status": "charged"},
        {"item": "psd", "amount": -28.0, "status": "charged"},
    ]

