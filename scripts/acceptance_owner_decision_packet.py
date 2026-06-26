from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "work" / "release_evidence" / "20260620-aliyun-staging" / "owner_decision_packet.md"
PREFLIGHT = ROOT / "work" / "release_evidence" / "20260620-aliyun-staging" / "aliyun_staging_preflight.json"
OUTPUT = ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "acceptance_owner_decision_packet.json"

REQUIRED_PHRASES = [
    "Status: blocked on owner/cloud prerequisites",
    "Do not claim Aliyun staging or production readiness until strict cloud smoke passes.",
    "Main EEG analysis workflow: QC / PSD / ERP / report ZIP",
    "Analysis lab and preset analysis library",
    "Email, phone, and WeChat sandbox registration",
    "Alipay and WeChat Pay sandbox billing flow",
    "Wallet, ledger, invoice request, admin invoice upload, customer inbox",
    "Queue contract: 10 users / 50 tasks",
    "Upload capacity evidence: 10 x 200 MB and 1 x 1 GB",
    "Provide these only through the staging runtime or CI secret store. Do not commit filled values.",
    "deploy/aliyun/qlanalyser-v01-staging.env.example",
    "python scripts\\aliyun_staging_preflight.py --strict",
    "python scripts\\acceptance_aliyun_storage_contract.py --target aliyun --strict",
    "python scripts\\acceptance_backup_restore_drill.py --target aliyun --strict",
    "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\run_v01_acceptance.ps1",
    "work/release_evidence/20260620-aliyun-staging/aliyun_staging_preflight.json",
    "work/release_evidence/20260620-aliyun-staging/owner_input_checklist.md",
    "blocked_missing_prerequisites",
    "2 pass / 9 todo / 0 failed",
    "work/release_evidence/20260620-v01-sanitized-review",
]

REQUIRED_ENV_KEYS = [
    "QLANALYSER_PUBLIC_BASE_URL",
    "QLANALYSER_API_BASE_URL",
    "QLANALYSER_CORS_ORIGINS",
    "QLANALYSER_STORAGE_BACKEND=oss",
    "QLANALYSER_ALIYUN_OSS_ENDPOINT",
    "QLANALYSER_ALIYUN_OSS_BUCKET",
    "QLANALYSER_ALIYUN_OSS_ACCESS_KEY_ID",
    "QLANALYSER_ALIYUN_OSS_ACCESS_KEY_SECRET",
    "QLANALYSER_ALIYUN_OSS_ALLOW_WRITE=1",
    "QLANALYSER_ALIYUN_OSS_LIFECYCLE_POLICY_EVIDENCE",
    "QLANALYSER_ALIYUN_BACKUP_BUCKET",
    "QLANALYSER_ALIYUN_BACKUP_PREFIX",
    "QLANALYSER_PAYMENT_PROVIDER_MODE=sandbox",
    "QLANALYSER_ALIPAY_CALLBACK_EVIDENCE",
    "QLANALYSER_WECHAT_PAY_CALLBACK_EVIDENCE",
    "QLANALYSER_EMAIL_PROVIDER_MODE=sandbox",
    "QLANALYSER_SMS_PROVIDER_MODE=sandbox",
    "QLANALYSER_WECHAT_AUTH_PROVIDER_MODE=sandbox",
    "QLANALYSER_MESSAGE_PROVIDER_EVIDENCE",
]


def main() -> int:
    text = PACKET.read_text(encoding="utf-8")
    preflight = json.loads(PREFLIGHT.read_text(encoding="utf-8"))
    missing_phrases = [phrase for phrase in REQUIRED_PHRASES if phrase not in text]
    missing_env_keys = [key for key in REQUIRED_ENV_KEYS if key not in text]
    blocked_without_failures = (
        preflight.get("status") == "blocked_missing_prerequisites"
        and not [check for check in preflight.get("checks", []) if check.get("status") == "fail"]
    )
    status = "passed" if not missing_phrases and not missing_env_keys and blocked_without_failures else "failed"
    result = {
        "status": status,
        "packet": str(PACKET),
        "preflight": str(PREFLIGHT),
        "preflight_blocked_without_failures": blocked_without_failures,
        "required_phrases": len(REQUIRED_PHRASES),
        "required_env_keys": len(REQUIRED_ENV_KEYS),
        "missing_phrases": missing_phrases,
        "missing_env_keys": missing_env_keys,
        "policy": "Owner decision packet must preserve cloud input boundaries, verification commands, and safe evidence-sharing rules.",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
