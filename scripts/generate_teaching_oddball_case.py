from __future__ import annotations

import csv
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import mne
import numpy as np

from eeg_core.analysis.erp import run_erp
from eeg_core.analysis.psd import run_psd
from eeg_core.preprocess.quality import run_quality_check


WORK = ROOT / "work" / "learning_case"
DATA = WORK / "data"
OUTPUTS = WORK / "outputs"

CHANNELS = ["Fz", "Cz", "Pz", "Oz", "P3", "P4", "O1", "O2"]
SFREQ = 250.0
DURATION_SEC = 60.0
RANDOM_SEED = 20260618


STANDARD_ONSETS = np.arange(2.0, 50.0, 2.0)[:24]
TARGET_ONSETS = np.array([5.0, 11.0, 17.0, 23.0, 29.0, 35.0, 41.0, 47.0, 53.0, 55.5, 57.0, 58.5])
TARGET_ONSETS = TARGET_ONSETS[TARGET_ONSETS < DURATION_SEC - 1.0]


def _gaussian(t: np.ndarray, mu: float, sigma: float, amp: float) -> np.ndarray:
    return amp * np.exp(-0.5 * ((t - mu) / sigma) ** 2)


def build_raw() -> mne.io.Raw:
    times = np.arange(int(SFREQ * DURATION_SEC)) / SFREQ
    info = mne.create_info(CHANNELS, sfreq=SFREQ, ch_types="eeg")
    rng = np.random.default_rng(RANDOM_SEED)
    data = np.zeros((len(CHANNELS), len(times)))

    posterior_alpha_weight = {
        "Fz": 0.2,
        "Cz": 0.35,
        "Pz": 1.0,
        "Oz": 1.2,
        "P3": 0.8,
        "P4": 0.8,
        "O1": 1.1,
        "O2": 1.1,
    }
    for ci, ch_name in enumerate(CHANNELS):
        data[ci] += posterior_alpha_weight[ch_name] * 8e-6 * np.sin(2 * np.pi * 10 * times + rng.uniform(0, 2 * np.pi))
        data[ci] += 1.5e-6 * np.sin(2 * np.pi * 6 * times + rng.uniform(0, 2 * np.pi))
        data[ci] += 0.8e-6 * np.sin(2 * np.pi * 20 * times + rng.uniform(0, 2 * np.pi))
        data[ci] += 0.7e-6 * rng.normal(size=len(times))

    erp_time = np.arange(int(1.0 * SFREQ)) / SFREQ
    n100 = _gaussian(erp_time, 0.11, 0.025, -2.5e-6)
    p200 = _gaussian(erp_time, 0.21, 0.04, 2.0e-6)
    p300_target = _gaussian(erp_time, 0.34, 0.06, 7.0e-6)
    p300_standard = _gaussian(erp_time, 0.32, 0.06, 2.0e-6)
    p300_spatial = {"Fz": 0.35, "Cz": 0.65, "Pz": 1.0, "Oz": 0.55, "P3": 0.85, "P4": 0.85, "O1": 0.45, "O2": 0.45}
    early_spatial = {"Fz": 0.8, "Cz": 0.8, "Pz": 0.7, "Oz": 0.5, "P3": 0.6, "P4": 0.6, "O1": 0.45, "O2": 0.45}

    def inject_event(onset: float, *, target: bool) -> None:
        start = int(round(onset * SFREQ))
        end = min(start + len(erp_time), data.shape[1])
        width = end - start
        for ci, ch_name in enumerate(CHANNELS):
            wave = early_spatial[ch_name] * (n100[:width] + p200[:width])
            wave += p300_spatial[ch_name] * ((p300_target if target else p300_standard)[:width])
            data[ci, start:end] += wave

    for onset in STANDARD_ONSETS:
        inject_event(float(onset), target=False)
    for onset in TARGET_ONSETS:
        inject_event(float(onset), target=True)

    raw = mne.io.RawArray(data, info, verbose="ERROR")
    raw.set_montage("standard_1020", on_missing="ignore", verbose="ERROR")
    onsets = list(map(float, STANDARD_ONSETS)) + list(map(float, TARGET_ONSETS))
    descriptions = ["standard"] * len(STANDARD_ONSETS) + ["target"] * len(TARGET_ONSETS)
    order = np.argsort(onsets)
    raw.set_annotations(
        mne.Annotations(
            onset=np.array(onsets)[order],
            duration=[0] * len(order),
            description=np.array(descriptions)[order],
        ),
        verbose="ERROR",
    )
    return raw


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def run_case() -> dict:
    if WORK.exists():
        shutil.rmtree(WORK)
    DATA.mkdir(parents=True)
    OUTPUTS.mkdir(parents=True)

    raw = build_raw()
    fif_path = DATA / "teaching_oddball_raw.fif"
    edf_path = DATA / "teaching_oddball.edf"
    raw.save(fif_path, overwrite=True, verbose="ERROR")
    raw.export(edf_path, fmt="edf", overwrite=True, verbose="ERROR")

    qc_paths = run_quality_check(edf_path, OUTPUTS / "qc", {})
    psd_paths = run_psd(edf_path, OUTPUTS / "psd", {"fmin": 1, "fmax": 40})
    # Teaching mode uses no re-reference here because the current ERP metric averages all EEG channels.
    # Average-reference + all-channel averaging cancels the synthetic topography and is documented as a design gap.
    erp_paths = run_erp(
        edf_path,
        OUTPUTS / "erp_teaching_reference_none",
        {
            "event_id": {"standard": 1, "target": 2},
            "tmin": -0.2,
            "tmax": 0.8,
            "baseline": [None, 0],
            "l_freq": 0.1,
            "h_freq": 30.0,
            "reference": None,
        },
    )
    erp_average_ref_paths = run_erp(
        edf_path,
        OUTPUTS / "erp_current_default_average_reference",
        {
            "event_id": {"standard": 1, "target": 2},
            "tmin": -0.2,
            "tmax": 0.8,
            "baseline": [None, 0],
            "l_freq": 0.1,
            "h_freq": 30.0,
            "reference": "average",
        },
    )

    qc_summary = json.loads(Path(qc_paths["qc_summary"]).read_text(encoding="utf-8"))
    psd_summary = json.loads(Path(psd_paths["psd_summary"]).read_text(encoding="utf-8"))
    erp_summary = json.loads(Path(erp_paths["erp_summary"]).read_text(encoding="utf-8"))
    band_power = {row["band"]: float(row["mean_psd"]) for row in _read_csv_rows(Path(psd_paths["band_power"]))}
    p300 = [row for row in _read_csv_rows(Path(erp_paths["erp_metrics"])) if row["component"] == "P300"]
    p300_average_ref = [row for row in _read_csv_rows(Path(erp_average_ref_paths["erp_metrics"])) if row["component"] == "P300"]

    summary = {
        "dataset": {
            "edf": str(edf_path),
            "fif": str(fif_path),
            "duration_sec": DURATION_SEC,
            "sfreq_hz": SFREQ,
            "channels": CHANNELS,
            "events": {"standard": len(STANDARD_ONSETS), "target": len(TARGET_ONSETS)},
            "signal_design": "posterior 10 Hz alpha plus target-enhanced P300-like response",
        },
        "qc": {"status": qc_summary.get("status"), "checks": qc_summary.get("checks")},
        "psd": {
            "freq_range_hz": psd_summary.get("freq_range_hz"),
            "freq_bins": psd_summary.get("freq_bins"),
            "band_power_mean": band_power,
            "expected_reading": "alpha should dominate because the synthetic signal contains a strong posterior 10 Hz rhythm",
        },
        "erp": {
            "events_total": erp_summary.get("events_total"),
            "event_id": erp_summary.get("event_id"),
            "epochs_total": erp_summary.get("epochs_total"),
            "conditions": erp_summary.get("conditions"),
            "p300_metrics_reference_none": p300,
            "p300_metrics_average_reference_all_channel_current_gap": p300_average_ref,
            "expected_reading": "target P300 amplitude should be larger than standard; current all-channel averaging after average reference can cancel this and must be fixed with ROI-aware metrics",
        },
        "outputs": {
            "qc": {k: str(v) for k, v in qc_paths.items()},
            "psd": {k: str(v) for k, v in psd_paths.items()},
            "erp_teaching_reference_none": {k: str(v) for k, v in erp_paths.items()},
            "erp_current_default_average_reference": {k: str(v) for k, v in erp_average_ref_paths.items()},
        },
    }
    summary_path = WORK / "teaching_oddball_run_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "summary": str(summary_path), "edf": str(edf_path)}


if __name__ == "__main__":
    print(json.dumps(run_case(), ensure_ascii=False, indent=2))
