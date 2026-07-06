import json
import os
import threading
import time
from contextlib import ExitStack, contextmanager
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

# Reentrancy tracker: lets the same thread acquire the same registry lock
# multiple times (and lets billing hold accounts+transactions atomically while
# inner helpers call upsert_item). Per-thread dict name -> depth.
_HELD_LOCKS = threading.local()


def _held_counts() -> dict[str, int]:
    counts = getattr(_HELD_LOCKS, "counts", None)
    if counts is None:
        counts = {}
        _HELD_LOCKS.counts = counts
    return counts


def _state_file(name: str) -> Path:
    return STATE_ROOT / f"{name}.json"


def _backup_file(name: str, timestamp: str | None = None) -> Path:
    """P0-STORAGE-03 FIX: Generate backup file path."""
    if timestamp is None:
        from datetime import datetime, timezone
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return STATE_ROOT / "backups" / f"{name}_{timestamp}.json"


def _lock_file(name: str) -> Path:
    return STATE_ROOT / f".{name}.lock"


@contextmanager
def _registry_lock(name: str):
    """Serialize registry writes across threads and local processes.

    Reentrant within the same thread (so billing can hold accounts lock and
    still call upsert_item("billing_transactions", ...)).
    """
    counts = _held_counts()
    depth = counts.get(name, 0)
    if depth > 0:
        # Already held by this thread — re-enter without re-acquiring.
        counts[name] = depth + 1
        try:
            yield
        finally:
            counts[name] -= 1
        return

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
    counts[name] = 1
    try:
        yield
    finally:
        counts[name] -= 1
        if handle is not None:
            os.close(handle)
        if counts.get(name, 0) <= 0:
            counts.pop(name, None)
            try:
                lock_path.unlink()
            except FileNotFoundError:
                pass


@contextmanager
def atomic_cross_registry_lock(registry_names: list[str]):
    """Hold multiple registry locks atomically for cross-registry transactions
    (e.g. billing: accounts + transactions).

    Acquires locks in sorted name order to prevent deadlock.
    """
    sorted_names = sorted(registry_names)
    with ExitStack() as stack:
        for name in sorted_names:
            stack.enter_context(_registry_lock(name))
        yield


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
    """Write registry data with automatic backup.
    
    P0-STORAGE-03 FIX: Create backup before writing to prevent data loss.
    """
    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    path = _state_file(name)
    
    # P0-STORAGE-03 FIX: Create backup of existing file before writing
    backup_dir = STATE_ROOT / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    if path.exists():
        try:
            from datetime import datetime, timezone
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            backup_path = _backup_file(name, timestamp)
            
            # Copy existing file to backup
            import shutil
            shutil.copy2(path, backup_path)
            
            # Keep only last 10 backups per registry
            existing_backups = sorted(backup_dir.glob(f"{name}_*.json"))
            if len(existing_backups) > 10:
                for old_backup in existing_backups[:-10]:
                    try:
                        old_backup.unlink()
                    except OSError:
                        pass  # Ignore errors on cleanup
        except Exception:
            # Don't fail write if backup fails, but log it
            pass
    
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


def restore_from_backup(name: str, timestamp: str | None = None) -> bool:
    """P0-STORAGE-03 FIX: Restore registry from backup.
    
    Args:
        name: Registry name (e.g., 'projects', 'tasks')
        timestamp: Specific backup timestamp, or None for latest
        
    Returns:
        bool: True if restore succeeded, False otherwise
    """
    backup_dir = STATE_ROOT / "backups"
    if not backup_dir.exists():
        return False
    
    if timestamp:
        backup_path = _backup_file(name, timestamp)
        if not backup_path.exists():
            return False
    else:
        # Find latest backup
        existing_backups = sorted(backup_dir.glob(f"{name}_*.json"))
        if not existing_backups:
            return False
        backup_path = existing_backups[-1]
    
    try:
        # Validate backup can be loaded
        backup_data = json.loads(backup_path.read_text(encoding="utf-8"))
        
        # Write to main file
        with _registry_lock(name):
            main_path = _state_file(name)
            backup_path.replace(main_path)
        
        return True
    except Exception:
        return False
