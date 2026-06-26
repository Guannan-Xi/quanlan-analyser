import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Header, HTTPException

from backend.models.governance import AccountCreate, AccountLogin, AccountRead, SessionRead, VerificationCodeRead, VerificationCodeRequest
from backend.services import audit_service, state_store

ACCOUNTS = "accounts"
SESSIONS = "account_sessions"
VERIFICATION_CODES = "verification_codes"
PBKDF2_ITERATIONS = 120_000
DEMO_EMAIL = "demo.customer@quanlan.cn"
DEMO_PASSWORD = "demo123456"
ADMIN_EMAIL = "ops@quanlan.cn"
ADMIN_PASSWORD = "ops-demo-2026"
SANDBOX_CODE = "000000"
DEMO_CUSTOMER_NAME = "\u5ba2\u6237\u8d26\u6237"
DEMO_CUSTOMER_ORG = "\u5168\u6f9c\u8111\u79d1\u5b66"


def _normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def _hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    if len(password or "") < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters")
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), PBKDF2_ITERATIONS)
    return digest.hex(), salt


def _verify_password(password: str, account: AccountRead) -> bool:
    if not account.password_hash or not account.password_salt:
        return False
    digest, _ = _hash_password(password, account.password_salt)
    return hmac.compare_digest(digest, account.password_hash)


def _public_account(account: AccountRead) -> dict:
    payload = account.model_dump(mode="json")
    payload.pop("password_hash", None)
    payload.pop("password_salt", None)
    return payload


def _load_accounts() -> dict[str, AccountRead]:
    return state_store.load_registry(ACCOUNTS, AccountRead)


def _load_codes() -> dict[str, VerificationCodeRead]:
    return state_store.load_registry(VERIFICATION_CODES, VerificationCodeRead)


def _load_sessions() -> dict[str, SessionRead]:
    return state_store.load_registry(SESSIONS, SessionRead)


def ensure_seed_accounts() -> None:
    accounts = _load_accounts()
    by_email = {account.email: account for account in accounts.values()}
    if DEMO_EMAIL not in by_email:
        create_account(
            AccountCreate(
                register_method="email",
                email=DEMO_EMAIL,
                password=DEMO_PASSWORD,
                name=DEMO_CUSTOMER_NAME,
                organization_name=DEMO_CUSTOMER_ORG,
                verification_code=SANDBOX_CODE,
            ),
            trial_credits=100.0,
        )
    else:
        demo = by_email[DEMO_EMAIL]
        if demo.name in {"", "Demo Customer"}:
            demo.name = DEMO_CUSTOMER_NAME
        if demo.organization_name in {"", "QuanLan Demo Center"}:
            demo.organization_name = DEMO_CUSTOMER_ORG
        if demo.balance_credits < 100.0:
            demo.balance_credits = 100.0
            demo.trial_credits = max(demo.trial_credits, 100.0)
        update_account(demo)
    if ADMIN_EMAIL not in by_email:
        digest, salt = _hash_password(ADMIN_PASSWORD)
        admin = AccountRead(
            email=ADMIN_EMAIL,
            name="Operations Admin",
            organization_name="QuanLan",
            role="admin",
            trial_credits=0.0,
            balance_credits=0.0,
            register_method="email",
            password_hash=digest,
            password_salt=salt,
        )
        state_store.upsert_item(ACCOUNTS, admin)


def request_verification_code(payload: VerificationCodeRequest) -> dict:
    channel = payload.channel.strip().lower()
    target = payload.target.strip().lower()
    if channel not in {"email", "phone"}:
        raise HTTPException(status_code=422, detail="Verification channel must be email or phone")
    if not target:
        raise HTTPException(status_code=422, detail="Verification target is required")
    item = VerificationCodeRead(
        channel=channel,
        target=target,
        code=SANDBOX_CODE,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    state_store.upsert_item(VERIFICATION_CODES, item)
    audit_service.record_event(
        action=f"account.verification_code.{channel}.sent",
        object_type="verification_code",
        object_id=item.id,
        metadata_json={"target": target, "provider_mode": item.provider_mode},
    )
    return {
        "status": "sent",
        "channel": channel,
        "target": target,
        "provider_mode": item.provider_mode,
        "sandbox_code": SANDBOX_CODE,
        "expires_at": item.expires_at.isoformat(),
    }


def _assert_verification(channel: str, target: str, code: str) -> None:
    if code == SANDBOX_CODE:
        return
    now = datetime.now(timezone.utc)
    for item in _load_codes().values():
        expires_at = item.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if item.channel == channel and item.target == target and item.code == code and expires_at > now:
            return
    raise HTTPException(status_code=422, detail="Verification code is invalid or expired")


def create_account(payload: AccountCreate, *, trial_credits: float = 30.0) -> dict:
    method = payload.register_method.strip().lower()
    if method not in {"email", "phone", "wechat"}:
        raise HTTPException(status_code=422, detail="Unsupported registration method")

    email = _normalize_email(payload.email)
    phone = payload.phone.strip()
    wechat_openid = payload.wechat_openid.strip()

    if method == "email":
        if not email:
            raise HTTPException(status_code=422, detail="Email is required")
        _assert_verification("email", email, payload.verification_code)
    elif method == "phone":
        if not phone:
            raise HTTPException(status_code=422, detail="Phone is required")
        _assert_verification("phone", phone, payload.verification_code)
        if not email:
            email = f"{phone}@phone.qlanalyser.local"
    else:
        if not wechat_openid:
            raise HTTPException(status_code=422, detail="Wechat openid is required")
        if not email:
            email = f"wechat_{wechat_openid}@wechat.qlanalyser.local"

    accounts = _load_accounts()
    duplicate = any(
        account.email == email
        or (phone and account.phone == phone)
        or (wechat_openid and account.wechat_openid == wechat_openid)
        for account in accounts.values()
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="Account already exists")

    password = payload.password or secrets.token_urlsafe(18)
    digest, salt = _hash_password(password)
    account = AccountRead(
        email=email,
        name=payload.name.strip() or payload.wechat_nickname.strip() or email.split("@")[0],
        organization_name=payload.organization_name.strip(),
        phone=phone,
        wechat_openid=wechat_openid,
        wechat_nickname=payload.wechat_nickname.strip(),
        register_method=method,
        password_hash=digest,
        password_salt=salt,
        trial_credits=trial_credits,
        balance_credits=trial_credits,
    )
    state_store.upsert_item(ACCOUNTS, account)
    audit_service.record_event(
        action="account.registered",
        object_type="account",
        object_id=account.id,
        organization_id=account.organization_name or "local-org",
        actor_user_id=account.id,
        metadata_json={"email": account.email, "role": account.role, "register_method": account.register_method},
    )
    return issue_session(account)


def issue_session(account: AccountRead) -> dict:
    token = f"qls_{secrets.token_urlsafe(32)}"
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    state_store.upsert_item(SESSIONS, SessionRead(token=token, account_id=account.id, role=account.role, expires_at=expires_at))
    return {"token": token, "account": _public_account(account), "expires_at": expires_at.isoformat()}


def login(payload: AccountLogin) -> dict:
    ensure_seed_accounts()
    email = _normalize_email(payload.email)
    accounts = _load_accounts()
    account = next((item for item in accounts.values() if item.email == email), None)
    if not account or not _verify_password(payload.password, account):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if account.status != "active":
        raise HTTPException(status_code=403, detail="Account is not active")
    audit_service.record_event(
        action="account.logged_in",
        object_type="account",
        object_id=account.id,
        organization_id=account.organization_name or "local-org",
        actor_user_id=account.id,
        metadata_json={"email": account.email, "role": account.role},
    )
    return issue_session(account)


def get_account(account_id: str) -> AccountRead:
    ensure_seed_accounts()
    accounts = _load_accounts()
    if account_id == "demo-customer":
        account = next((item for item in accounts.values() if item.email == DEMO_EMAIL), None)
        if account:
            return account
    try:
        return accounts[account_id]
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Account not found") from exc


def get_account_by_token(token: str) -> AccountRead:
    ensure_seed_accounts()
    session = next((item for item in _load_sessions().values() if item.token == token and item.status == "active"), None)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")
    account = get_account(session.account_id)
    if account.status != "active":
        raise HTTPException(status_code=403, detail="Account is not active")
    return account


def require_current_account(authorization: str = Header(default="")) -> AccountRead:
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        raise HTTPException(status_code=401, detail="Bearer token required")
    return get_account_by_token(authorization[len(prefix):].strip())


def require_admin_account(authorization: str = Header(default="")) -> AccountRead:
    account = require_current_account(authorization)
    if account.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return account


def assert_same_account_or_admin(requested_account_id: str, current: AccountRead) -> AccountRead:
    account = get_account(requested_account_id)
    if current.role != "admin" and account.id != current.id:
        raise HTTPException(status_code=403, detail="Account access denied")
    return account


def list_accounts() -> list[dict]:
    ensure_seed_accounts()
    return [_public_account(account) for account in _load_accounts().values()]


def update_account(account: AccountRead) -> AccountRead:
    account.updated_at = datetime.now(timezone.utc)
    state_store.upsert_item(ACCOUNTS, account)
    return account
