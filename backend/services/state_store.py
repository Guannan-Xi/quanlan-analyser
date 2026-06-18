import json
import os
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import TypeVar

from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[2]
STATE_ROOT = Path(os.getenv("QLANALYSER_STATE_ROOT", ROOT / "data" / "state"))
_LOCK_POLL_SEC = 0.025
_LOCK_TIMEOUT_SEC = 10.0
_REPLACE_RETRIES = 20
_REPLACE_BACKOFF_SEC = 0.025
_PROCESS_LOCK = threading.RLock()

ModelT = TypeVar("ModelT", bound=BaseModel)


def _state_file(name: str) -> Path:
    return STATE_ROOT / f"{name}.json"


def _lock_file(name: str) -> Path:
    return STATE_ROOT / f".{name}.lock"


@contextmanager
def _registry_lock(name: str):
    """Serialize registry writes across threads and local processes.

    The V01 pilot uses JSON registry files rather than a database. On Windows,
    concurrent os.replace calls against the same data/state directory can raise
    PermissionError when another process briefly owns the target or temp file.
    A tiny lock file keeps the file-system backend predictable until the product
    graduates to a real transactional store.
    """
    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    lock_path = _lock_file(name)
    start = time.monotonic()
    handle = None
    with _PROCESS_LOCK:
        while True:
            try:
                handle = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(handle, f"pid={os.getpid()} time={time.time()}\n".encode("utf-8"))
                break
            except FileExistsError:
                if time.monotonic() - start > _LOCK_TIMEOUT_SEC:
                    # If the owning process is gone, the stale lock should not
                    # permanently block local development or acceptance tests.
                    try:
                        age = time.time() - lock_path.stat().st_mtime
                    except OSError:
                        age = 0
                    if age > _LOCK_TIMEOUT_SEC:
                        try:
                            lock_path.unlink()
                            continue
                        except OSError:
                            pass
                    raise TimeoutError(f"Timed out waiting for state registry lock: {lock_path}")
                time.sleep(_LOCK_POLL_SEC)
        try:
            yield
        finally:
            if handle is not None:
                os.close(handle)
            try:
                lock_path.unlink()
            except FileNotFoundError:
                pass


def _replace_with_retry(temp_path: Path, target_path: Path) -> None:
    last_error: PermissionError | None = None
    for attempt in range(_REPLACE_RETRIES):
        try:
            temp_path.replace(target_path)
            return
        except PermissionError as exc:
            last_error = exc
            time.sleep(_REPLACE_BACKOFF_SEC * (attempt + 1))
    if last_error is not None:
        raise last_error


def load_registry(name: str, model_type: type[ModelT]) -> dict[str, ModelT]:
    path = _state_file(name)
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    registry: dict[str, ModelT] = {}
    for item in data:
        model = model_type.model_validate(item)
        registry[model.id] = model
    return registry



def _write_payload(name: str, payload: list[dict]) -> None:
    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    path = _state_file(name)
    temp_path: Path | None = None
    with NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=STATE_ROOT) as temp:
        temp_path = Path(temp.name)
        json.dump(payload, temp, ensure_ascii=False, indent=2)
        temp.write("\n")
        temp.flush()
        os.fsync(temp.fileno())
    try:
        _replace_with_retry(temp_path, path)
    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass


def _load_payload_unlocked(name: str) -> list[dict]:
    path = _state_file(name)
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def upsert_item(name: str, item: BaseModel) -> None:
    with _registry_lock(name):
        payload = _load_payload_unlocked(name)
        by_id = {entry.get("id"): entry for entry in payload if isinstance(entry, dict) and entry.get("id")}
        by_id[item.id] = item.model_dump(mode="json")
        _write_payload(name, list(by_id.values()))


def delete_item(name: str, item_id: str) -> None:
    with _registry_lock(name):
        payload = _load_payload_unlocked(name)
        filtered = [entry for entry in payload if not (isinstance(entry, dict) and entry.get("id") == item_id)]
        _write_payload(name, filtered)

def save_registry(name: str, registry: dict[str, BaseModel]) -> None:
    incoming = [item.model_dump(mode="json") for item in registry.values()]
    with _registry_lock(name):
        # Merge by id so a stale in-memory registry from another worker does not
        # erase records that were created after that worker loaded its snapshot.
        existing = _load_payload_unlocked(name)
        by_id = {entry.get("id"): entry for entry in existing if isinstance(entry, dict) and entry.get("id")}
        for entry in incoming:
            if isinstance(entry, dict) and entry.get("id"):
                by_id[entry["id"]] = entry
        _write_payload(name, list(by_id.values()))


def state_summary() -> dict:
    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    registries = {}
    for name in ["projects", "subjects", "eeg_files", "tasks", "artifacts", "reports"]:
        path = _state_file(name)
        if not path.exists():
            registries[name] = {"exists": False, "count": 0}
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            registries[name] = {"exists": True, "count": len(data)}
        except Exception as exc:  # pragma: no cover - readiness detail only
            registries[name] = {"exists": True, "count": None, "error": str(exc)}
    writable = False
    error = ""
    probe = STATE_ROOT / ".write_probe"
    try:
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        writable = True
    except Exception as exc:  # pragma: no cover - environment-specific
        error = str(exc)
    return {
        "path": str(STATE_ROOT),
        "exists": STATE_ROOT.exists(),
        "writable": writable,
        "registries": registries,
        "error": error,
    }


def get_state_status() -> dict:
    return state_summary()
