import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUNDS = int(sys.argv[1]) if len(sys.argv) > 1 else 10
RUNNER = ROOT / "scripts" / "launch_v01_virtual_users.py"
LATEST = ROOT / "work" / "acceptance" / "v01_virtual_users_latest.json"


def main() -> None:
    rounds = []
    for index in range(1, ROUNDS + 1):
        proc = subprocess.run([sys.executable, str(RUNNER)], cwd=ROOT, text=True, capture_output=True, timeout=120)
        detail = {}
        if LATEST.exists():
            try:
                detail = json.loads(LATEST.read_text(encoding="utf-8"))
            except Exception:
                detail = {}
        rounds.append({
            "round": index,
            "status": "passed" if proc.returncode == 0 and detail.get("status") == "passed" else "failed",
            "returncode": proc.returncode,
            "min_score": detail.get("min_score"),
            "stderr_tail": proc.stderr[-1000:],
        })
        if rounds[-1]["status"] != "passed":
            break
    summary = {
        "status": "passed" if len(rounds) == ROUNDS and all(item["status"] == "passed" for item in rounds) else "failed",
        "round_count": ROUNDS,
        "rounds": rounds,
        "min_score": min((item.get("min_score") or 0) for item in rounds) if rounds else 0,
    }
    out = ROOT / "work" / "acceptance" / "v01_merge9_virtual_users_10rounds.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if summary["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
