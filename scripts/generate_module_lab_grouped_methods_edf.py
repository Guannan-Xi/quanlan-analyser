from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.generate_teaching_oddball_case import build_raw


OUT_DIR = ROOT / "work" / "release_evidence" / "20260625-module-lab-grouped-methods-e2e"
EDF_PATH = OUT_DIR / "module_lab_grouped_methods_local.edf"
EVENTS_PATH = OUT_DIR / "module_lab_grouped_methods_events.tsv"
SUMMARY_PATH = OUT_DIR / "generated_edf_summary.json"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    raw = build_raw()
    raw.export(EDF_PATH, fmt="edf", overwrite=True, verbose="ERROR")

    with EVENTS_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["onset", "duration", "trial_type"], delimiter="\t")
        writer.writeheader()
        for onset, duration, description in zip(raw.annotations.onset, raw.annotations.duration, raw.annotations.description):
            writer.writerow(
                {
                    "onset": f"{float(onset):.3f}",
                    "duration": f"{float(duration):.3f}",
                    "trial_type": str(description),
                }
            )

    summary = {
        "status": "passed",
        "edf_path": str(EDF_PATH),
        "events_path": str(EVENTS_PATH),
        "channels": raw.ch_names,
        "sampling_rate_hz": float(raw.info["sfreq"]),
        "duration_sec": float(raw.times[-1]),
        "annotation_count": len(raw.annotations),
        "purpose": "Local EDF for Module Lab grouped-method end-to-end review.",
    }
    SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
