"""Refresh the inverse delivery manifest without rebuilding mutable artifacts."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "simnibs_inverse_ti_discrete_ernie_20260729"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest().upper()


files = []
for path in sorted(path for path in OUT.rglob("*") if path.is_file() and path.name not in {"manifest.json", "dual_acceptance.json", "delivery_root_sha256.txt"}):
    files.append({"path": path.relative_to(OUT).as_posix(), "bytes": path.stat().st_size, "sha256": digest(path)})
(OUT / "manifest.json").write_text(json.dumps({"files": files}, ensure_ascii=False, indent=2), encoding="utf-8")
(OUT / "delivery_root_sha256.txt").write_text(
    f"manifest.json  SHA256  {digest(OUT / 'manifest.json')}\n",
    encoding="ascii",
)
