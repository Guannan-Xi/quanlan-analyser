import json
import multiprocessing as mp
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.models.project import ProjectRead
from backend.services import state_store


def worker(state_root: str, worker_id: int, rounds: int, queue: mp.Queue) -> None:
    os.environ["QLANALYSER_STATE_ROOT"] = state_root
    # Patch module-level state root after import in this child process.
    state_store.STATE_ROOT = Path(state_root)
    try:
        for index in range(rounds):
            registry = state_store.load_registry("projects", ProjectRead)
            project = ProjectRead(name=f"concurrency-{worker_id}-{index}", description="state-store-lock")
            registry[project.id] = project
            state_store.save_registry("projects", registry)
        queue.put({"worker": worker_id, "ok": True})
    except Exception as exc:
        queue.put({"worker": worker_id, "ok": False, "error": f"{type(exc).__name__}: {exc}"})


def main() -> None:
    work = Path(tempfile.mkdtemp(prefix="qlanalyser_state_concurrency_"))
    workers = 6
    rounds = 12
    queue: mp.Queue = mp.Queue()
    processes = [mp.Process(target=worker, args=(str(work), idx, rounds, queue)) for idx in range(workers)]
    for process in processes:
        process.start()
    results = [queue.get(timeout=30) for _ in processes]
    for process in processes:
        process.join(timeout=10)
    failed = [item for item in results if not item.get("ok")]
    if failed:
        raise AssertionError(json.dumps(failed, ensure_ascii=False, indent=2))
    state_store.STATE_ROOT = work
    registry = state_store.load_registry("projects", ProjectRead)
    expected = workers * rounds
    if len(registry) < expected:
        raise AssertionError(f"expected at least {expected} persisted projects, got {len(registry)}")
    projects_json = work / "projects.json"
    json.loads(projects_json.read_text(encoding="utf-8"))
    print(json.dumps({"status": "passed", "workers": workers, "rounds": rounds, "persisted": len(registry), "state_root": str(work)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    mp.freeze_support()
    main()
