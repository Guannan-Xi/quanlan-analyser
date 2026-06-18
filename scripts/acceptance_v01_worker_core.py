import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import mne
import numpy as np

from eeg_core.analysis.erp import run_erp
from eeg_core.analysis.psd import run_psd
from eeg_core.io.metadata import read_metadata
from eeg_core.preprocess.quality import run_quality_check, summarize_quality
from worker.tasks.erp import run_task as worker_erp
from worker.tasks.metadata import extract_metadata as worker_metadata
from worker.tasks.preprocess import run_task as worker_qc
from worker.tasks.psd import run_task as worker_psd
from worker.tasks.report import run_task as worker_report


def make_raw(path: Path, *, events: bool) -> Path:
    sfreq = 200.0
    info = mne.create_info(["Fz", "Cz", "Pz", "Oz"], sfreq=sfreq, ch_types="eeg")
    times = np.arange(int(sfreq * 8)) / sfreq
    data = 1e-6 * np.random.default_rng(7).normal(size=(4, len(times))) + 4e-6 * np.sin(2 * np.pi * 10 * times)
    raw = mne.io.RawArray(data, info, verbose="ERROR")
    if events:
        raw.set_annotations(mne.Annotations(onset=[1, 3, 5], duration=[0, 0, 0], description=["target", "standard", "target"]))
    raw.save(path, overwrite=True, verbose="ERROR")
    return path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def require_output_contract(paths: dict, job_type: str, expected_rel_paths: set[str]) -> None:
    result_path = Path(paths["result"])
    manifest_path = Path(paths["manifest"])
    log_path = Path(paths["log"])
    result = json.loads(result_path.read_text(encoding="utf-8"))
    require(result.get("schema_version") == "qlanalyser-output-v0.1", json.dumps(result, ensure_ascii=False)[:1000])
    require(result.get("product_name") == "QLanalyser Online", json.dumps(result, ensure_ascii=False)[:1000])
    require(result.get("job_type") == job_type, json.dumps(result, ensure_ascii=False)[:1000])
    require(result.get("status") == "completed", json.dumps(result, ensure_ascii=False)[:1000])
    result_outputs = {item.get("path") for item in result.get("outputs", [])}
    require(expected_rel_paths.issubset(result_outputs), str(sorted(result_outputs)))

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = {item.get("path"): item for item in manifest.get("files", [])}
    required_manifest_paths = set(expected_rel_paths) | {"result.json", "log.txt"}
    require(required_manifest_paths.issubset(entries), str(sorted(entries)))
    require("manifest.json" not in entries, str(sorted(entries)))
    for rel_path in required_manifest_paths:
        entry = entries[rel_path]
        require(int(entry.get("size_bytes", 0)) > 0, json.dumps(entry, ensure_ascii=False))
        require(len(str(entry.get("sha256", ""))) == 64, json.dumps(entry, ensure_ascii=False))
    require(log_path.read_text(encoding="utf-8").strip(), str(log_path))


def main() -> None:
    work = Path(tempfile.mkdtemp(prefix="qlanalyser_worker_core_"))
    raw_path = make_raw(work / "events_raw.fif", events=True)
    no_event_path = make_raw(work / "no_events_raw.fif", events=False)

    metadata = read_metadata(raw_path)
    require(metadata["status"] == "readable" and metadata["eeg_channel_count"] == 4, json.dumps(metadata))
    worker_meta = worker_metadata(raw_path)
    require(worker_meta["status"] == "readable", json.dumps(worker_meta))

    qc_summary = summarize_quality(raw_path)
    require(qc_summary["status"] in {"passed", "warning"}, json.dumps(qc_summary)[:1000])
    qc_paths = run_quality_check(raw_path, work / "core_qc")
    worker_qc_paths = worker_qc(raw_path, work / "worker_qc")
    qc_expected = {"reproducibility/qc_summary.json", "reproducibility/parameters.json", "reproducibility/method_description.txt", "reproducibility/software_versions.json", "reproducibility/workflow.json"}
    for paths in [qc_paths, worker_qc_paths]:
        require({"qc_summary", "parameters", "method_description", "software_versions", "workflow", "result", "manifest", "log"}.issubset(paths), str(paths))
        for path in paths.values():
            require(Path(path).exists() and Path(path).stat().st_size > 0, str(path))
        require_output_contract(paths, "metadata_qc", qc_expected)

    psd_paths = run_psd(raw_path, work / "core_psd", {"fmin": 1, "fmax": 40})
    worker_psd_paths = worker_psd(raw_path, work / "worker_psd", {"fmin": 1, "fmax": 40})
    psd_expected = {"tables/band_power.csv", "tables/channel_band_power.csv", "reproducibility/psd_summary.json", "reproducibility/parameters.json", "reproducibility/method_description.txt", "reproducibility/software_versions.json", "reproducibility/workflow.json"}
    for paths in [psd_paths, worker_psd_paths]:
        require({"band_power", "channel_band_power", "psd_summary", "parameters", "method_description", "software_versions", "workflow", "result", "manifest", "log"}.issubset(paths), str(paths))
        for path in paths.values():
            require(Path(path).exists() and Path(path).stat().st_size > 0, str(path))
        require_output_contract(paths, "resting_psd", psd_expected)

    erp_paths = run_erp(raw_path, work / "core_erp", {"tmin": -0.2, "tmax": 0.6, "baseline": [None, 0]})
    worker_erp_paths = worker_erp(raw_path, work / "worker_erp", {"tmin": -0.2, "tmax": 0.6, "baseline": [None, 0]})
    erp_expected = {"tables/erp_metrics.csv", "reproducibility/erp_summary.json", "reproducibility/event_confirmation.json", "reproducibility/drop_log_summary.json", "reproducibility/parameters.json", "reproducibility/method_description.txt", "reproducibility/software_versions.json", "reproducibility/workflow.json"}
    for paths in [erp_paths, worker_erp_paths]:
        require({"erp_metrics", "erp_summary", "event_confirmation", "drop_log_summary", "parameters", "method_description", "software_versions", "workflow", "result", "manifest", "log"}.issubset(paths), str(paths))
        for path in paths.values():
            require(Path(path).exists() and Path(path).stat().st_size > 0, str(path))
        erp_header = Path(paths["erp_metrics"]).read_text(encoding="utf-8").splitlines()[0]
        require("roi_channels" in erp_header and "reference" in erp_header, erp_header)
        require_output_contract(paths, "erp_p300", erp_expected)

    try:
        run_erp(no_event_path, work / "erp_should_fail")
        raise AssertionError("ERP without events should fail")
    except ValueError as exc:
        require("event" in str(exc).lower(), str(exc))

    try:
        run_psd(raw_path, work / "psd_should_fail", {"fmin": 40, "fmax": 1})
        raise AssertionError("PSD invalid range should fail")
    except ValueError as exc:
        require("frequency range" in str(exc).lower(), str(exc))

    report_path = worker_report(work / "worker_report", "Worker Report", {"task": {"module_name": "psd", "status": "completed"}, "artifacts": [], "task_output_dir": str(work / "worker_psd")})
    require(Path(report_path).exists() and "QLanalyser EEG V01" in Path(report_path).read_text(encoding="utf-8"), str(report_path))

    print(json.dumps({"status": "passed", "work": str(work)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
