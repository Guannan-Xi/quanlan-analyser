from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eeg_core.analysis.epilepsy_ml import run_epilepsy_ml

EVIDENCE_DIR = ROOT / "work" / "release_evidence" / "20260701-he105-epilepsy-ml-chunked-fix"
SLICE_PATH = ROOT / "work" / "release_evidence" / "20260701-he105-customer-data-local-test" / "slice_10min" / "HE-105_first_10min.edf"
FULL_PATH = Path(r"D:\Quanlan\Data\HE脑电\HE脑电\HE-105.edf")


def summarize_run(
    label: str,
    input_path: Path,
    *,
    preview_sec: float = 120.0,
    worker_count: int = 1,
    chunk_epochs: int = 128,
) -> dict:
    out_dir = EVIDENCE_DIR / label
    start = time.perf_counter()
    outputs = run_epilepsy_ml(
        input_path,
        out_dir,
        {
            "eeg_channel": "EEG1",
            "epoch_length_sec": 5.0,
            "feature_chunk_epochs": chunk_epochs,
            "feature_worker_count": worker_count,
            "spectrogram_preview_duration_sec": preview_sec,
        },
    )
    elapsed = time.perf_counter() - start
    summary_path = out_dir / "reproducibility" / "epilepsy_ml_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    result = {
        "label": label,
        "input_path": str(input_path),
        "elapsed_sec": round(elapsed, 3),
        "status": summary.get("status"),
        "duration_sec": summary.get("duration_sec"),
        "epoch_count": summary.get("epoch_count"),
        "event_count": summary.get("event_count"),
        "processing_plan": summary.get("processing_plan"),
        "spectrogram_preview": (summary.get("spectrogram") or {}).get("preview"),
        "outputs": {key: str(value) for key, value in outputs.items()},
    }
    (EVIDENCE_DIR / f"{label}_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> None:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    mode = sys.argv[1] if len(sys.argv) > 1 else "slice"
    worker_count = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    chunk_epochs = int(sys.argv[3]) if len(sys.argv) > 3 else 128
    if mode == "slice":
        result = summarize_run(
            f"he105_slice_10min_w{worker_count}_c{chunk_epochs}",
            SLICE_PATH,
            preview_sec=120.0,
            worker_count=worker_count,
            chunk_epochs=chunk_epochs,
        )
    elif mode == "full":
        result = summarize_run(
            f"he105_full_w{worker_count}_c{chunk_epochs}",
            FULL_PATH,
            preview_sec=600.0,
            worker_count=worker_count,
            chunk_epochs=chunk_epochs,
        )
    else:
        raise SystemExit("usage: python scripts/run_he105_epilepsy_ml_chunked_regression.py [slice|full]")
    print(json.dumps({"status": "PASS", "mode": mode, "result": result}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
