from datetime import datetime

from pydantic import BaseModel, Field

from backend.models.base import new_id, utc_now


class AuditEventRead(BaseModel):
    id: str = Field(default_factory=lambda: new_id("audit"))
    audit_trace_id: str = Field(default_factory=lambda: new_id("trace"))
    organization_id: str = "local-org"
    project_id: str | None = None
    actor_user_id: str = "local-user"
    action: str
    object_type: str
    object_id: str
    status: str = "recorded"
    metadata_json: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class UsageRecordRead(BaseModel):
    id: str = Field(default_factory=lambda: new_id("usage"))
    organization_id: str = "local-org"
    project_id: str | None = None
    owner_user_id: str = "local-user"
    quota_account_id: str | None = None
    resource_type: str
    action: str
    quantity: float
    unit: str
    source_type: str
    source_id: str
    billable: bool = False
    status: str = "recorded"
    metadata_json: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class AccountRead(BaseModel):
    id: str = Field(default_factory=lambda: new_id("acct"))
    email: str
    name: str = ""
    organization_name: str = ""
    phone: str = ""
    wechat_openid: str = ""
    wechat_nickname: str = ""
    register_method: str = "email"
    role: str = "customer"
    status: str = "active"
    password_hash: str = ""
    password_salt: str = ""
    balance_credits: float = 0.0
    trial_credits: float = 30.0
    total_recharged_credits: float = 0.0
    total_spent_credits: float = 0.0
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class AccountCreate(BaseModel):
    register_method: str = "email"
    email: str = ""
    password: str = ""
    name: str = ""
    organization_name: str = ""
    phone: str = ""
    wechat_openid: str = ""
    wechat_nickname: str = ""
    verification_code: str = ""


class AccountLogin(BaseModel):
    email: str
    password: str


class SessionRead(BaseModel):
    id: str = Field(default_factory=lambda: new_id("session"))
    token: str
    account_id: str
    role: str = "customer"
    status: str = "active"
    expires_at: datetime
    created_at: datetime = Field(default_factory=utc_now)


class RechargeCreate(BaseModel):
    account_id: str = "demo-customer"
    amount_credits: float
    payment_method: str = "alipay"
    note: str = ""


class RechargeOrderRead(BaseModel):
    id: str = Field(default_factory=lambda: new_id("recharge"))
    account_id: str
    amount_credits: float
    payment_method: str = "alipay"
    status: str = "pending"
    provider_trade_no: str = ""
    payment_url: str = ""
    qr_code_url: str = ""
    note: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    paid_at: datetime | None = None


class PaymentConfirm(BaseModel):
    provider_trade_no: str = ""
    status: str = "paid"
    operator_note: str = ""


class BillingTransactionRead(BaseModel):
    id: str = Field(default_factory=lambda: new_id("billtx"))
    account_id: str
    direction: str
    amount_credits: float
    balance_after_credits: float
    source_type: str
    source_id: str
    description: str = ""
    status: str = "posted"
    metadata_json: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class VerificationCodeRequest(BaseModel):
    channel: str = "email"
    target: str


class VerificationCodeRead(BaseModel):
    id: str = Field(default_factory=lambda: new_id("verify"))
    channel: str
    target: str
    code: str
    status: str = "sent"
    provider_mode: str = "sandbox"
    expires_at: datetime
    created_at: datetime = Field(default_factory=utc_now)


class InvoiceRequestCreate(BaseModel):
    account_id: str = "demo-customer"
    invoice_title: str
    tax_number: str = ""
    amount_credits: float
    recipient_email: str
    recipient_name: str = ""
    address: str = ""
    phone: str = ""
    bank_name: str = ""
    bank_account: str = ""
    note: str = ""


class InvoiceRequestRead(InvoiceRequestCreate):
    id: str = Field(default_factory=lambda: new_id("invoice"))
    status: str = "pending"
    invoice_file_path: str = ""
    invoice_file_name: str = ""
    issued_by: str = ""
    issued_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class InboxMessageRead(BaseModel):
    id: str = Field(default_factory=lambda: new_id("inbox"))
    account_id: str
    subject: str
    body: str
    message_type: str = "invoice"
    status: str = "unread"
    attachment_path: str = ""
    attachment_name: str = ""
    source_type: str = "invoice"
    source_id: str = ""
    created_at: datetime = Field(default_factory=utc_now)
