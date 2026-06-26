import csv
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import mne
import numpy as np

from eeg_core.analysis.erp import run_erp


def build_p300_fif(path: Path, *, with_events: bool) -> Path:
    sfreq = 200.0
    duration = 12.0
    ch_names = ["Fz", "Cz", "Pz", "P3", "P4", "Oz"]
    info = mne.create_info(ch_names, sfreq=sfreq, ch_types="eeg")
    times = np.arange(int(sfreq * duration)) / sfreq
    rng = np.random.default_rng(20260619 if with_events else 20260620)
    data = 0.2e-6 * rng.normal(size=(len(ch_names), len(times)))
    data += 0.5e-6 * np.sin(2 * np.pi * 8.0 * times)

    raw = mne.io.RawArray(data, info, verbose="ERROR")
    raw.set_montage("standard_1020", on_missing="ignore")
    if with_events:
        target_onsets = [2.0, 5.0, 8.0]
        standard_onsets = [3.2, 6.2, 9.2]
        p300_template = 6.0e-6 * np.exp(-0.5 * ((times[: int(0.7 * sfreq)] - 0.32) / 0.045) ** 2)
        standard_template = 1.0e-6 * np.exp(-0.5 * ((times[: int(0.7 * sfreq)] - 0.32) / 0.045) ** 2)
        for onset in target_onsets:
            start = int(onset * sfreq)
            stop = min(start + len(p300_template), data.shape[1])
            data[ch_names.index("Pz"), start:stop] += p300_template[: stop - start]
            data[ch_names.index("P3"), start:stop] += 0.7 * p300_template[: stop - start]
            data[ch_names.index("P4"), start:stop] += 0.7 * p300_template[: stop - start]
        for onset in standard_onsets:
            start = int(onset * sfreq)
            stop = min(start + len(standard_template), data.shape[1])
            data[ch_names.index("Pz"), start:stop] += standard_template[: stop - start]
        raw = mne.io.RawArray(data, info, verbose="ERROR")
        raw.set_montage("standard_1020", on_missing="ignore")
        raw.set_annotations(
            mne.Annotations(
                onset=target_onsets + standard_onsets,
                duration=[0.0] * (len(target_onsets) + len(standard_onsets)),
                description=["target"] * len(target_onsets) + ["standard"] * len(standard_onsets),
            )
        )
    raw.save(path, overwrite=True, verbose="ERROR")
    return path


def _load_metrics(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _component_mean(rows: list[dict], *, condition: str, component: str) -> float:
    values = [
        float(row["amplitude_uv"])
        for row in rows
        if row.get("condition") == condition and row.get("component") == component
    ]
    if not values:
        raise AssertionError(f"No rows for condition={condition}, component={component}")
    return float(np.mean(values))


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="qlanalyser-synthetic-erp-") as tmp:
        work = Path(tmp)
        erp_path = build_p300_fif(work / "synthetic_p300_raw.fif", with_events=True)
        out = work / "erp_out"
        result = run_erp(
            erp_path,
            out,
            {
                "tmin": -0.2,
                "tmax": 0.7,
                "baseline": [-0.2, 0.0],
                "roi_channels": {"P300": ["Pz", "P3", "P4"], "default": ["Pz"]},
                "components": {"P300": [0.28, 0.45]},
            },
        )

        metrics_path = result["erp_metrics"]
        rows = _load_metrics(metrics_path)
        target_p300 = _component_mean(rows, condition="target", component="P300")
        standard_p300 = _component_mean(rows, condition="standard", component="P300")
        if not target_p300 > standard_p300:
            raise AssertionError(f"Expected target P300 > standard P300, got target={target_p300}, standard={standard_p300}")

        summary = json.loads(result["erp_summary"].read_text(encoding="utf-8"))
        if summary.get("events_total", 0) < 6:
            raise AssertionError(f"Expected synthetic events, got summary={summary}")
        if summary.get("epochs_total", 0) < 6:
            raise AssertionError(f"Expected retained epochs, got summary={summary}")

        no_event_path = build_p300_fif(work / "synthetic_no_events_raw.fif", with_events=False)
        no_event_error = ""
        try:
            run_erp(no_event_path, work / "no_event_out", {"event_id": {"target": 1}})
        except ValueError as exc:
            no_event_error = str(exc)
        if "requires event" not in no_event_error.lower() and "none were found" not in no_event_error.lower():
            raise AssertionError(f"No-event ERP should fail clearly, got: {no_event_error!r}")

        print(json.dumps({
            "status": "passed",
            "target_p300_mean": target_p300,
            "standard_p300_mean": standard_p300,
            "events_total": summary.get("events_total"),
            "epochs_total": summary.get("epochs_total"),
            "no_event_error": no_event_error,
        }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
