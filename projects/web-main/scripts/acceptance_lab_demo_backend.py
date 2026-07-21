import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from backend.main import app


def require(condition: bool, message: str):
    if not condition:
        raise AssertionError(message)


def main():
    client = TestClient(app)

    dataset = client.get("/api/lab/demo/dataset")
    require(dataset.status_code == 200, dataset.text)
    dataset_json = dataset.json()
    require(dataset_json["file"]["id"] == "eeg_demo_teaching_oddball", json.dumps(dataset_json)[:500])
    require(
        dataset_json["file"].get("metadata_json", {}).get("events_tsv_path"),
        json.dumps(dataset_json)[:500],
    )

    run_all = client.post("/api/lab/demo/run-all")
    require(run_all.status_code == 200, run_all.text)
    payload = run_all.json()
    tasks = payload["tasks"]
    required_modules = {"qc", "psd", "erp"}
    require(required_modules.issubset(set(tasks)), json.dumps(tasks))
    for module, task in tasks.items():
        require(task["status"] == "completed", json.dumps(task))
        artifacts = client.get(f"/api/tasks/{task['id']}/artifacts")
        require(artifacts.status_code == 200, artifacts.text)
        artifact_rows = artifacts.json()
        require(len(artifact_rows) >= 3, f"{module} artifacts too few: {artifact_rows}")
        first = client.get(f"/api/artifacts/{artifact_rows[0]['id']}/download")
        require(first.status_code == 200 and len(first.content) > 0, f"download failed for {module}")

    erp_artifacts = client.get(f"/api/tasks/{tasks['erp']['id']}/artifacts").json()
    erp_metrics = next(item for item in erp_artifacts if item["label"] == "erp_metrics")
    erp_csv = client.get(f"/api/artifacts/{erp_metrics['id']}/download")
    header = erp_csv.text.splitlines()[0]
    require("roi_channels" in header and "reference" in header, header)

    print(json.dumps({"status": "passed", "tasks": {k: v["id"] for k, v in tasks.items()}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
