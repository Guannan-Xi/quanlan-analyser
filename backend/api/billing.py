from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/billing/wallet")
def get_wallet() -> dict:
    return {
        "enabled": False,
        "balance": 0.0,
        "frozen": 0.0,
        "currency": "CNY",
        "message": "V01 research release does not enable real billing. Connect a payment provider before production charging.",
    }


@router.post("/billing/recharge")
def create_recharge_order(amount: float = 0.0) -> dict:
    raise HTTPException(status_code=501, detail="Recharge is not enabled in V01 research release")


@router.get("/billing/ledger")
def list_ledger() -> list[dict]:
    return []
