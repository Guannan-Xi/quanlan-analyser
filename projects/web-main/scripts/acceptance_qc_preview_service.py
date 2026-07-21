import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import mne
import numpy as np
from fastapi.testclient import TestClient

from backend.main import app


def build_sample(channel_count: int = 8) -> Path:
    work = Path(tempfile.mkdtemp(prefix="qlanalyser_qc_preview_"))
    sample = work / f"qc_preview_{channel_count}ch_raw.fif"
    sfreq = 200.0
    base_names = ["Fz", "Cz", "Pz", "Oz", "Fp1", "Fp2", "C3", "C4"]
    ch_names = base_names if channel_count <= len(base_names) else [f"EEG{idx:03d}" for idx in range(1, channel_count + 1)]
    info = mne.create_info(ch_names, sfreq=sfreq, ch_types="eeg")
    times = np.arange(int(sfreq * 20)) / sfreq
    rng = np.random.default_rng(20260618)
    data = 1e-6 * rng.normal(size=(len(ch_names), len(times)))
    data += 8e-6 * np.sin(2 * np.pi * 10 * times)
    raw = mne.io.RawArray(data, info, verbose="ERROR")
    raw.set_annotations(mne.Annotations(onset=[2.0, 5.0, 9.0, 14.0], duration=[0, 0, 0, 0], description=["start", "target", "standard", "end"]))
    raw.save(sample, overwrite=True, verbose="ERROR")
    return sample


def assert_true(name: str, condition: bool, detail="") -> None:
    if not condition:
        raise AssertionError(f"{name} failed: {detail}")


def main() -> None:
    client = TestClient(app)
    sample = build_sample()
    project = client.post("/api/projects", json={"name": "QC preview acceptance", "research_type": "qc_lab"}).json()
    with sample.open("rb") as handle:
        eeg_file = client.post(
            f"/api/eeg/upload?project_id={project['id']}",
            files={"file": (sample.name, handle, "application/octet-stream")},
        ).json()

    payload = {
        "project_id": project["id"],
        "module_name": "qc",
        "workflow_id": "qc_waveform_preview",
        "input_file_id": eeg_file["id"],
        "parameters_json": {
            "preview": {"start_sec": 1.0, "duration_sec": 8.0, "channels": ["Fz", "Cz", "Pz", "Oz"], "display_sfreq": 100.0},
            "filter_preview": {"enabled": True, "bandpass": {"enabled": True, "l_freq": 1.0, "h_freq": 40.0}, "notch": {"enabled": False, "freqs": []}},
            "snapshot": {"label": "acceptance snapshot"},
        },
    }
    response = client.post("/api/tasks", json=payload)
    assert_true("task created", response.status_code == 200, response.text)
    task = response.json()
    assert_true("task completed", task["status"] == "completed", task)

    artifacts = client.get(f"/api/tasks/{task['id']}/artifacts").json()
    by_label = {item["label"]: item for item in artifacts}
    required = {"waveform_preview", "filter_preview", "raw_preview_figure", "filter_preview_figure", "snapshot_figure", "snapshot_json", "result", "manifest", "log"}
    assert_true("required artifacts", required.issubset(by_label), sorted(by_label))

    waveform = client.get(f"/api/artifacts/{by_label['waveform_preview']['id']}/download").json()
    filtered = client.get(f"/api/artifacts/{by_label['filter_preview']['id']}/download").json()
    result = client.get(f"/api/artifacts/{by_label['result']['id']}/download").json()
    svg = client.get(f"/api/artifacts/{by_label['snapshot_figure']['id']}/download")

    assert_true("waveform channels", waveform["channels"] == ["Fz", "Cz", "Pz", "Oz"], waveform.get("channels"))
    assert_true("waveform data", len(waveform["data_uv"]) == 4 and len(waveform["times_sec"]) > 100, "data shape")
    assert_true("filter preview flag", filtered["filter_preview_only"] is True, filtered)
    assert_true("filter data", len(filtered["data_uv"]) == 4, "filter data shape")
    assert_true("result contract", result["job_type"] == "qc_waveform_preview" and result["schema_version"] == "qlanalyser-output-v0.1", result)
    assert_true("svg download", svg.status_code == 200 and "svg" in svg.headers.get("content-type", ""), svg.headers)

    sample64 = build_sample(channel_count=64)
    with sample64.open("rb") as handle:
        upload64 = client.post("/api/eeg/upload", params={"project_id": project["id"]}, files={"file": (sample64.name, handle, "application/octet-stream")})
    assert_true("upload 64ch", upload64.status_code == 200, upload64.text)
    eeg64 = upload64.json()
    channels64 = [f"EEG{idx:03d}" for idx in range(1, 65)]
    task64_payload = {
        "project_id": project["id"],
        "module_name": "qc",
        "workflow_id": "qc_waveform_preview",
        "input_file_id": eeg64["id"],
        "parameters_json": {
            "preview": {"start_sec": 0.0, "duration_sec": 2.0, "channels": channels64, "display_sfreq": 100.0},
            "filter_preview": {"enabled": False},
            "snapshot": {"enabled": True, "label": "64 channel acceptance"},
        },
    }
    task64_response = client.post("/api/tasks", json=task64_payload)
    assert_true("64 channel preview task", task64_response.status_code == 200, task64_response.text)
    task64 = task64_response.json()
    artifacts64 = client.get(f"/api/tasks/{task64['id']}/artifacts").json()
    waveform64_artifact = next(item for item in artifacts64 if item["label"] == "waveform_preview")
    waveform64 = client.get(f"/api/artifacts/{waveform64_artifact['id']}/download").json()
    assert_true("64 channel preview count", len(waveform64["channels"]) == 64, waveform64.get("channels"))

    print(json.dumps({"status": "passed", "task_id": task["id"], "artifacts": len(artifacts), "max_preview_channels_checked": 64}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
