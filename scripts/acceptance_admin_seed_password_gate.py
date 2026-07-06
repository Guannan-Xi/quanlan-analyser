import importlib
import os
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@contextmanager
def isolated_account_service(app_env: str, admin_password: str | None = None, admin_email: str | None = None):
    old_env = {
        "QLANALYSER_STATE_ROOT": os.environ.get("QLANALYSER_STATE_ROOT"),
        "QLANALYSER_ENV": os.environ.get("QLANALYSER_ENV"),
        "QLANALYSER_ADMIN_EMAIL": os.environ.get("QLANALYSER_ADMIN_EMAIL"),
        "QLANALYSER_ADMIN_PASSWORD": os.environ.get("QLANALYSER_ADMIN_PASSWORD"),
    }
    with tempfile.TemporaryDirectory() as state_root:
        os.environ["QLANALYSER_STATE_ROOT"] = state_root
        os.environ["QLANALYSER_ENV"] = app_env
        if admin_email is None:
            os.environ.pop("QLANALYSER_ADMIN_EMAIL", None)
        else:
            os.environ["QLANALYSER_ADMIN_EMAIL"] = admin_email
        if admin_password is None:
            os.environ.pop("QLANALYSER_ADMIN_PASSWORD", None)
        else:
            os.environ["QLANALYSER_ADMIN_PASSWORD"] = admin_password
        from backend.services import account_service, state_store

        importlib.reload(state_store)
        service = importlib.reload(account_service)
        try:
            yield service
        finally:
            for key, value in old_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
            importlib.reload(state_store)
            importlib.reload(account_service)


def assert_condition(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def login_status(service, email: str, password: str) -> int:
    try:
        service.login(service.AccountLogin(email=email, password=password))
        return 200
    except HTTPException as exc:
        return exc.status_code


def account_by_email(service, email: str):
    return next((account for account in service._load_accounts().values() if account.email == email), None)


def main() -> None:
    with isolated_account_service("production") as service:
        service.ensure_seed_accounts()
        accounts = service._load_accounts()
        assert_condition(all(account.email != service.ADMIN_EMAIL for account in accounts.values()), "production must not seed fixed admin without explicit password")
        assert_condition(login_status(service, service.ADMIN_EMAIL, service.LOCAL_ADMIN_PASSWORD) in {401, 403}, "production fixed admin login must fail")

    with isolated_account_service("production", service.LOCAL_ADMIN_PASSWORD) as service:
        service.ensure_seed_accounts()
        accounts = service._load_accounts()
        assert_condition(all(account.email != service.ADMIN_EMAIL for account in accounts.values()), "production must reject explicitly reused local admin password")

    strong_password = "prod-admin-unique-2026"
    with isolated_account_service("production", strong_password) as service:
        service.ensure_seed_accounts()
        accounts = service._load_accounts()
        assert_condition(any(account.email == service.ADMIN_EMAIL for account in accounts.values()), "production should seed admin when explicit non-default password is provided")
        assert_condition(login_status(service, service.ADMIN_EMAIL, strong_password) == 200, "production explicit admin password should login")
        assert_condition(login_status(service, service.ADMIN_EMAIL, service.LOCAL_ADMIN_PASSWORD) == 403, "production default admin password must remain blocked")

    with isolated_account_service("test") as service:
        service.ensure_seed_accounts()
        unsafe_admin = account_by_email(service, service.ADMIN_EMAIL)
        assert_condition(unsafe_admin is not None, "test fixture should create admin before production reload")
        unsafe_session = service.issue_session(unsafe_admin)
        os.environ["QLANALYSER_ENV"] = "production"
        service = importlib.reload(service)
        try:
            service.get_account_by_token(unsafe_session["token"])
            raise AssertionError("production must reject pre-existing default-admin session")
        except HTTPException as exc:
            assert_condition(exc.status_code == 403, "production default-admin session should be forbidden")

    with isolated_account_service("test") as service:
        service.ensure_seed_accounts()
        old_default_admin = account_by_email(service, service.ADMIN_EMAIL)
        assert_condition(old_default_admin is not None, "test fixture should create default admin before configured production reload")
        old_default_session = service.issue_session(old_default_admin)
        os.environ["QLANALYSER_ENV"] = "production"
        os.environ["QLANALYSER_ADMIN_EMAIL"] = "prod-admin@example.com"
        os.environ["QLANALYSER_ADMIN_PASSWORD"] = strong_password
        service = importlib.reload(service)
        service.ensure_seed_accounts()
        assert_condition(login_status(service, "ops@quanlan.cn", service.LOCAL_ADMIN_PASSWORD) == 403, "production must reject stale default admin even when configured admin email changed")
        try:
            service.get_account_by_token(old_default_session["token"])
            raise AssertionError("production must reject stale default-admin session after configured admin email changes")
        except HTTPException as exc:
            assert_condition(exc.status_code == 403, "stale default-admin session should be forbidden")

    with isolated_account_service("test") as service:
        service.ensure_seed_accounts()
        rotating_admin = account_by_email(service, service.ADMIN_EMAIL)
        assert_condition(rotating_admin is not None, "test fixture should create admin before production password rotation")
        old_session = service.issue_session(rotating_admin)
        os.environ["QLANALYSER_ENV"] = "production"
        os.environ["QLANALYSER_ADMIN_PASSWORD"] = strong_password
        service = importlib.reload(service)
        service.ensure_seed_accounts()
        assert_condition(login_status(service, service.ADMIN_EMAIL, strong_password) == 200, "production password rotation should allow new admin password")
        try:
            service.get_account_by_token(old_session["token"])
            raise AssertionError("production must revoke sessions when admin password rotates")
        except HTTPException as exc:
            assert_condition(exc.status_code == 401, "rotated admin session should be revoked")

    with isolated_account_service("test") as service:
        service.ensure_seed_accounts()
        assert_condition(login_status(service, service.ADMIN_EMAIL, service.LOCAL_ADMIN_PASSWORD) == 200, "test env should keep local admin seed for acceptance scripts")

    print("acceptance_admin_seed_password_gate: passed")


if __name__ == "__main__":
    main()
