import json
from pathlib import Path
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import mne
import numpy as np
from fastapi.testclient import TestClient

from backend.main import app


def build_sample_fif() -> Path:
    work = Path(tempfile.mkdtemp(prefix="qlanalyser_smoke_"))
    sample_path = work / "synthetic_erp_raw.fif"
    sfreq = 200.0
    ch_names = ["Fz", "Cz", "Pz", "Oz"]
    info = mne.create_info(ch_names, sfreq=sfreq, ch_types="eeg")
    times = np.arange(int(sfreq * 12)) / sfreq
    rng = np.random.default_rng(42)
    data = 1e-6 * rng.normal(size=(len(ch_names), len(times)))
    data += 5e-6 * np.sin(2 * np.pi * 10 * times)
    raw = mne.io.RawArray(data, info, verbose="ERROR")
    raw.set_montage("standard_1020", on_missing="ignore", verbose="ERROR")
    raw.set_annotations(
        mne.Annotations(
            onset=[1.0, 3.0, 5.0, 7.0, 9.0],
            duration=[0, 0, 0, 0, 0],
            description=["target", "standard", "target", "standard", "target"],
        )
    )
    raw.save(sample_path, overwrite=True, verbose="ERROR")
    return sample_path


def main() -> None:
    client = TestClient(app)
    sample_path = build_sample_fif()

    response = client.post(
        "/api/projects",
        json={"name": "V01 smoke project", "description": "api smoke", "research_type": "eeg_v01"},
    )
    response.raise_for_status()
    project = response.json()

    with sample_path.open("rb") as handle:
        response = client.post(
            f"/api/eeg/upload?project_id={project['id']}",
            files={"file": (sample_path.name, handle, "application/octet-stream")},
        )
    response.raise_for_status()
    eeg_file = response.json()

    response = client.get(f"/api/eeg/files/{eeg_file['id']}/metadata")
    response.raise_for_status()
    metadata = response.json()
    assert metadata["status"] == "readable", metadata
    assert metadata["annotation_count"] >= 5, metadata

    results = {}
    modules = [
        ("qc", "metadata_qc", {}),
        ("psd", "resting_psd", {"fmin": 1, "fmax": 40}),
        ("erp", "erp_p300", {"tmin": -0.2, "tmax": 0.6, "baseline": [None, 0]}),
    ]
    for module, workflow, params in modules:
        response = client.post(
            "/api/tasks",
            json={
                "project_id": project["id"],
                "module_name": module,
                "workflow_id": workflow,
                "input_file_id": eeg_file["id"],
                "parameters_json": params,
            },
        )
        response.raise_for_status()
        task = response.json()
        assert task["status"] == "completed", task
        response = client.get(f"/api/tasks/{task['id']}/artifacts")
        response.raise_for_status()
        artifacts = response.json()
        labels = {item["label"] for item in artifacts}
        assert {"parameters", "method_description", "software_versions", "workflow"}.issubset(labels), labels
        results[module] = {"task": task, "artifacts": artifacts}

    response = client.post(
        "/api/tasks",
        json={
            "project_id": project["id"],
            "module_name": "connectivity",
            "workflow_id": "connectivity",
            "input_file_id": eeg_file["id"],
            "parameters_json": {},
        },
    )
    assert response.status_code == 422, response.text
    assert "not enabled in V01" in response.text

    psd_task = results["psd"]["task"]
    response = client.post(
        "/api/reports",
        json={"project_id": project["id"], "task_id": psd_task["id"], "title": "V01 Smoke PSD Report"},
    )
    response.raise_for_status()
    report = response.json()
    package_path = Path(report["package_path"])
    assert package_path.exists(), package_path
    with zipfile.ZipFile(package_path) as zf:
        names = set(zf.namelist())
        assert "reports/report.html" in names, names
        assert "tables/band_power.csv" in names, names
        assert "reproducibility/software_versions.json" in names, names
        assert "reproducibility/workflow.json" in names, names

    artifact_id = results["psd"]["artifacts"][0]["id"]
    response = client.get(f"/api/artifacts/{artifact_id}/download")
    response.raise_for_status()
    assert response.content

    response = client.get(f"/api/reports/{report['id']}/package")
    response.raise_for_status()
    assert response.headers["content-type"].startswith("application/zip")

    print(
        json.dumps(
            {
                "status": "passed",
                "project_id": project["id"],
                "file_id": eeg_file["id"],
                "metadata_status": metadata["status"],
                "tasks": {key: value["task"]["id"] for key, value in results.items()},
                "report_id": report["id"],
                "package": str(package_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
