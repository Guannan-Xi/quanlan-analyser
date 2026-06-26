from fastapi import APIRouter, Depends

from backend.models.governance import AccountCreate, AccountLogin, VerificationCodeRequest
from backend.services import account_service

router = APIRouter()


@router.post("/auth/verification-code")
def request_verification_code(payload: VerificationCodeRequest) -> dict:
    return account_service.request_verification_code(payload)


@router.post("/auth/register")
def register(payload: AccountCreate) -> dict:
    return account_service.create_account(payload)


@router.post("/auth/login")
def login(payload: AccountLogin) -> dict:
    return account_service.login(payload)


@router.get("/accounts")
def list_accounts(_admin=Depends(account_service.require_admin_account)) -> list[dict]:
    return account_service.list_accounts()
