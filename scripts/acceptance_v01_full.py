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

RESULTS: list[dict] = []


def record(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append({"name": name, "ok": bool(ok), "detail": detail})
    if not ok:
        raise AssertionError(f"{name}: {detail}")


def assert_status(response, expected: int, name: str):
    if response.status_code != expected:
        record(name, False, f"expected {expected}, got {response.status_code}: {response.text[:500]}")
    record(name, True, f"HTTP {expected}")
    return response


def assert_contract_artifacts(module: str, workflow: str, artifacts: list[dict]) -> None:
    expected_outputs = {
        "qc": {"reproducibility/qc_summary.json", "reproducibility/parameters.json", "reproducibility/method_description.txt", "reproducibility/software_versions.json", "reproducibility/workflow.json"},
        "psd": {"tables/band_power.csv", "tables/channel_band_power.csv", "reproducibility/psd_summary.json", "reproducibility/parameters.json", "reproducibility/method_description.txt", "reproducibility/software_versions.json", "reproducibility/workflow.json"},
        "erp": {"tables/erp_metrics.csv", "reproducibility/erp_summary.json", "reproducibility/parameters.json", "reproducibility/method_description.txt", "reproducibility/software_versions.json", "reproducibility/workflow.json"},
    }[module]
    by_label = {item["label"]: item for item in artifacts}
    result_path = Path(by_label["result"]["path"])
    manifest_path = Path(by_label["manifest"]["path"])
    log_path = Path(by_label["log"]["path"])

    result = json.loads(result_path.read_text(encoding="utf-8"))
    record(f"contract result schema {module}", result.get("schema_version") == "qlanalyser-output-v0.1", json.dumps(result, ensure_ascii=False)[:1000])
    record(f"contract result job_type {module}", result.get("job_type") == workflow, json.dumps(result, ensure_ascii=False)[:1000])
    result_outputs = {item.get("path") for item in result.get("outputs", [])}
    record(f"contract result outputs {module}", expected_outputs.issubset(result_outputs), str(sorted(result_outputs)))

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = {item.get("path"): item for item in manifest.get("files", [])}
    required = expected_outputs | {"result.json", "log.txt"}
    record(f"contract manifest files {module}", required.issubset(entries) and "manifest.json" not in entries, str(sorted(entries)))
    for rel_path in required:
        entry = entries[rel_path]
        record(f"contract manifest hash {module}:{rel_path}", int(entry.get("size_bytes", 0)) > 0 and len(str(entry.get("sha256", ""))) == 64, json.dumps(entry, ensure_ascii=False))
    record(f"contract log non-empty {module}", bool(log_path.read_text(encoding="utf-8").strip()), str(log_path))


def build_fif(path: Path, *, with_events: bool) -> Path:
    sfreq = 200.0
    ch_names = ["Fz", "Cz", "Pz", "Oz"]
    info = mne.create_info(ch_names, sfreq=sfreq, ch_types="eeg")
    times = np.arange(int(sfreq * 12)) / sfreq
    rng = np.random.default_rng(42 if with_events else 24)
    data = 1e-6 * rng.normal(size=(len(ch_names), len(times)))
    data += 5e-6 * np.sin(2 * np.pi * 10 * times)
    raw = mne.io.RawArray(data, info, verbose="ERROR")
    raw.set_montage("standard_1020", on_missing="ignore", verbose="ERROR")
    if with_events:
        raw.set_annotations(
            mne.Annotations(
                onset=[1.0, 3.0, 5.0, 7.0, 9.0],
                duration=[0, 0, 0, 0, 0],
                description=["target", "standard", "target", "standard", "target"],
            )
        )
    raw.save(path, overwrite=True, verbose="ERROR")
    return path


def upload_file(client: TestClient, project_id: str, path: Path) -> dict:
    with path.open("rb") as handle:
        response = client.post(
            f"/api/eeg/upload?project_id={project_id}",
            files={"file": (path.name, handle, "application/octet-stream")},
        )
    assert_status(response, 200, f"upload {path.suffix}")
    return response.json()


def run_task(client: TestClient, project_id: str, file_id: str, module: str, workflow: str, params: dict) -> tuple[dict, list[dict]]:
    response = client.post(
        "/api/tasks",
        json={
            "project_id": project_id,
            "module_name": module,
            "workflow_id": workflow,
            "input_file_id": file_id,
            "parameters_json": params,
        },
    )
    assert_status(response, 200, f"run task {module}")
    task = response.json()
    record(f"task {module} completed", task["status"] == "completed", json.dumps(task, ensure_ascii=False))
    response = client.get(f"/api/tasks/{task['id']}/artifacts")
    assert_status(response, 200, f"list artifacts {module}")
    artifacts = response.json()
    labels = {item["label"] for item in artifacts}
    required = {"parameters", "method_description", "software_versions", "workflow", "result", "manifest", "log"}
    record(f"task {module} reproducibility artifacts", required.issubset(labels), str(labels))
    for artifact in artifacts:
        path = Path(artifact["path"])
        record(f"artifact exists {module}:{artifact['label']}", path.exists() and path.stat().st_size > 0, str(path))
    assert_contract_artifacts(module, workflow, artifacts)
    return task, artifacts


def main() -> None:
    client = TestClient(app)
    work = Path(tempfile.mkdtemp(prefix="qlanalyser_acceptance_"))
    event_fif = build_fif(work / "with_events_raw.fif", with_events=True)
    no_event_fif = build_fif(work / "no_events_raw.fif", with_events=False)
    unsupported = work / "not_eeg.txt"
    unsupported.write_text("not an eeg file", encoding="utf-8")
    empty_fif = work / "empty.fif"
    empty_fif.write_bytes(b"")

    # Health and catalog surfaces.
    response = client.get("/api/health")
    assert_status(response, 200, "health")
    health = response.json()
    record("health version", health.get("scope") == "eeg-v01-production" and health.get("version") == "0.1.0", json.dumps(health))

    response = client.get("/api/templates")
    assert_status(response, 200, "list workflow templates")
    templates = response.json()
    template_ids = {item["id"] for item in templates}
    record("workflow templates include V01 modules", {"metadata_qc", "resting_psd", "erp_p300"}.issubset(template_ids), str(template_ids))
    assert_status(client.get("/api/templates/resting_psd"), 200, "get template resting_psd")
    assert_status(client.get("/api/templates/does-not-exist"), 404, "missing template 404")
    assert_status(client.get("/api/analysis-templates"), 200, "analysis templates")
    analysis_templates = client.get("/api/analysis-templates").json()
    record("analysis templates no billing price", all("price_cny" not in item for item in analysis_templates), json.dumps(analysis_templates))
    assert_status(client.get("/api/paradigms"), 200, "paradigms")
    assert_status(client.get("/api/recommendation-rules"), 200, "recommendation rules")
    assert_status(client.get("/api/workflows/templates"), 200, "workflow templates alias")
    estimate = assert_status(client.post("/api/workflows/estimate?template_id=resting_psd"), 200, "workflow estimate").json()
    record("workflow estimate no billing", estimate.get("billing_enabled") is False and "estimated_cost" not in estimate, json.dumps(estimate))
    assert_status(client.post("/api/workflows/estimate?template_id=missing"), 404, "workflow estimate missing")

    # Project and subject management.
    response = client.post("/api/projects", json={"name": "Acceptance project", "description": "full v01", "research_type": "eeg_v01"})
    assert_status(response, 200, "create project")
    project = response.json()
    assert_status(client.get("/api/projects"), 200, "list projects")
    assert_status(client.get(f"/api/projects/{project['id']}"), 200, "get project")
    assert_status(client.get("/api/projects/missing"), 404, "missing project 404")
    subject_payload = {"subject_code": "sub-acceptance", "group_name": "control", "age": 30, "sex": "NA", "notes": "synthetic"}
    subject = assert_status(client.post(f"/api/projects/{project['id']}/subjects", json=subject_payload), 200, "create subject").json()
    record("subject linked to project", subject["project_id"] == project["id"], json.dumps(subject))
    assert_status(client.get(f"/api/projects/{project['id']}/subjects"), 200, "list subjects")

    # Upload validation.
    assert_status(client.post(f"/api/eeg/upload?project_id={project['id']}"), 422, "upload missing file fails")
    with unsupported.open("rb") as handle:
        assert_status(
            client.post(f"/api/eeg/upload?project_id={project['id']}", files={"file": (unsupported.name, handle, "text/plain")}),
            422,
            "unsupported upload fails",
        )
    with empty_fif.open("rb") as handle:
        assert_status(
            client.post(f"/api/eeg/upload?project_id={project['id']}", files={"file": (empty_fif.name, handle, "application/octet-stream")}),
            422,
            "empty upload fails",
        )

    eeg_file = upload_file(client, project["id"], event_fif)
    no_event_file = upload_file(client, project["id"], no_event_fif)
    assert_status(client.get(f"/api/eeg/files/{eeg_file['id']}"), 200, "get eeg file")
    metadata = assert_status(client.get(f"/api/eeg/files/{eeg_file['id']}/metadata"), 200, "metadata readable").json()
    record("metadata has signal structure", metadata.get("status") == "readable" and metadata.get("eeg_channel_count") == 4 and metadata.get("annotation_count") >= 5, json.dumps(metadata, ensure_ascii=False)[:1000])
    metadata_no_event = assert_status(client.get(f"/api/eeg/files/{no_event_file['id']}/metadata"), 200, "metadata no-event readable").json()
    record("no-event metadata has zero annotations", metadata_no_event.get("annotation_count") == 0, json.dumps(metadata_no_event, ensure_ascii=False)[:1000])
    assert_status(client.get("/api/eeg/files/missing/metadata"), 404, "missing metadata 404")

    # Data CRUD surface.
    files = assert_status(client.get("/api/data/files"), 200, "data files list").json()
    record("data list includes uploads", any(item["id"] == eeg_file["id"] for item in files), json.dumps(files, ensure_ascii=False))
    patched = assert_status(client.patch(f"/api/data/files/{eeg_file['id']}?label=acceptance-label"), 200, "data patch label").json()
    record("data patch persists label", patched.get("label") == "acceptance-label", json.dumps(patched, ensure_ascii=False))

    # Real analysis modules.
    qc_task, qc_artifacts = run_task(client, project["id"], eeg_file["id"], "qc", "metadata_qc", {})
    psd_task, psd_artifacts = run_task(client, project["id"], eeg_file["id"], "psd", "resting_psd", {"fmin": 1, "fmax": 40})
    erp_task, erp_artifacts = run_task(client, project["id"], eeg_file["id"], "erp", "erp_p300", {"tmin": -0.2, "tmax": 0.6, "baseline": [None, 0]})
    for task in [qc_task, psd_task, erp_task]:
        fetched_task = assert_status(client.get(f"/api/tasks/{task['id']}"), 200, f"get task {task['module_name']}").json()
        record(f"get task {task['module_name']} identity", fetched_task["id"] == task["id"] and fetched_task["status"] == "completed", json.dumps(fetched_task))
    assert_status(client.get("/api/tasks/missing"), 404, "missing task 404")

    psd_labels = {item["label"] for item in psd_artifacts}
    record("psd scientific outputs", {"band_power", "channel_band_power", "psd_summary"}.issubset(psd_labels), str(psd_labels))
    erp_labels = {item["label"] for item in erp_artifacts}
    record("erp scientific outputs", {"erp_metrics", "erp_summary"}.issubset(erp_labels), str(erp_labels))
    qc_summary_path = next(Path(item["path"]) for item in qc_artifacts if item["label"] == "qc_summary")
    qc_summary = json.loads(qc_summary_path.read_text(encoding="utf-8"))
    record("qc summary status real", qc_summary.get("status") in {"passed", "warning"}, json.dumps(qc_summary, ensure_ascii=False)[:1000])

    # Failure boundaries: ERP without events, invalid PSD range, advanced methods, unsupported module.
    response = client.post(
        "/api/tasks",
        json={"project_id": project["id"], "module_name": "erp", "workflow_id": "erp_p300", "input_file_id": no_event_file["id"], "parameters_json": {}},
    )
    assert_status(response, 422, "erp without events fails")
    failed_task_id = response.json()["detail"]["task_id"]
    failed_task = assert_status(client.get(f"/api/tasks/{failed_task_id}"), 200, "failed task retrievable").json()
    record("failed ERP task stores error", failed_task["status"] == "failed" and "event" in failed_task["error_message"].lower(), json.dumps(failed_task))

    response = client.post(
        "/api/tasks",
        json={"project_id": project["id"], "module_name": "psd", "workflow_id": "resting_psd", "input_file_id": eeg_file["id"], "parameters_json": {"fmin": 40, "fmax": 1}},
    )
    assert_status(response, 422, "invalid psd range fails")
    for module in ["tfr", "pac", "connectivity"]:
        response = client.post(
            "/api/tasks",
            json={"project_id": project["id"], "module_name": module, "workflow_id": module, "input_file_id": eeg_file["id"], "parameters_json": {}},
        )
        assert_status(response, 422, f"advanced {module} disabled")
        record(f"advanced {module} explains V01", "not enabled in V01" in response.text, response.text)
    assert_status(
        client.post(
            "/api/tasks",
            json={"project_id": project["id"], "module_name": "unknown", "workflow_id": "unknown", "input_file_id": eeg_file["id"], "parameters_json": {}},
        ),
        422,
        "unknown module fails",
    )

    # Artifact downloads.
    for artifact in psd_artifacts:
        response = client.get(f"/api/artifacts/{artifact['id']}/download")
        assert_status(response, 200, f"download artifact {artifact['label']}")
        record(f"download artifact non-empty {artifact['label']}", len(response.content) > 0, artifact["path"])
    assert_status(client.get("/api/artifacts/missing/download"), 404, "missing artifact download 404")
    transient_artifact = psd_artifacts[0]
    transient_path = Path(transient_artifact["path"])
    backup_path = transient_path.with_suffix(transient_path.suffix + ".bak_acceptance")
    transient_path.rename(backup_path)
    try:
        assert_status(client.get(f"/api/artifacts/{transient_artifact['id']}/download"), 410, "missing artifact file 410")
    finally:
        backup_path.rename(transient_path)

    # Reports and packages.
    assert_status(
        client.post("/api/reports", json={"project_id": "wrong-project", "task_id": psd_task["id"], "title": "Wrong Project Report"}),
        422,
        "report project mismatch fails",
    )
    report = assert_status(
        client.post("/api/reports", json={"project_id": project["id"], "task_id": psd_task["id"], "title": "Acceptance PSD Report"}),
        200,
        "create report",
    ).json()
    package_path = Path(report["package_path"])
    html_path = Path(report["html_path"])
    record("report files exist", package_path.exists() and html_path.exists(), json.dumps(report))
    html = html_path.read_text(encoding="utf-8")
    record("report contains guardrails", "Clinical/research interpretation guardrails" in html and "Software versions" in html, html[:500])
    with zipfile.ZipFile(package_path) as zf:
        names = set(zf.namelist())
        required = {"reports/report.html", "tables/band_power.csv", "tables/channel_band_power.csv", "reproducibility/psd_summary.json", "reproducibility/software_versions.json", "reproducibility/workflow.json", "result.json", "manifest.json", "log.txt"}
        record("report zip required files", required.issubset(names), str(sorted(names)))
    assert_status(client.get(f"/api/reports/{report['id']}"), 200, "get report")
    assert_status(client.get(f"/api/reports/{report['id']}/html"), 200, "download report html")
    package_download = assert_status(client.get(f"/api/reports/{report['id']}/package"), 200, "download report package")
    record("report package content-type", package_download.headers["content-type"].startswith("application/zip"), package_download.headers["content-type"])
    assert_status(client.get("/api/reports/missing"), 404, "missing report 404")

    # Billing/admin are honest, not fake commerce.
    wallet = assert_status(client.get("/api/billing/wallet"), 200, "billing disabled wallet").json()
    record("billing disabled", wallet.get("enabled") is False and wallet.get("balance") == 0.0, json.dumps(wallet))
    assert_status(client.post("/api/billing/recharge?amount=100"), 501, "billing recharge disabled")
    ledger = assert_status(client.get("/api/billing/ledger"), 200, "billing ledger empty").json()
    record("billing ledger empty", ledger == [], json.dumps(ledger))
    admin = assert_status(client.get("/api/admin/dashboard"), 200, "admin dashboard").json()
    record("admin counts tasks", admin.get("total_tasks", 0) >= 3 and admin.get("failed_tasks", 0) >= 1, json.dumps(admin))
    failed = assert_status(client.get("/api/admin/tasks/failed"), 200, "admin failed tasks").json()
    record("admin failed task list", any(item["task_id"] == failed_task_id for item in failed), json.dumps(failed))

    # Deletion after all analysis should remove file from storage registry and disk.
    delete_target = upload_file(client, project["id"], build_fif(work / "delete_target_raw.fif", with_events=False))
    delete_path = Path(delete_target["stored_path"])
    assert_status(client.delete(f"/api/data/files/{delete_target['id']}"), 200, "delete uploaded file")
    record("deleted file removed from disk", not delete_path.exists(), str(delete_path))
    assert_status(client.get(f"/api/eeg/files/{delete_target['id']}"), 404, "deleted file registry removed")

    # Produce machine-readable acceptance report.
    summary = {
        "status": "passed",
        "checks": len(RESULTS),
        "project_id": project["id"],
        "file_id": eeg_file["id"],
        "tasks": {"qc": qc_task["id"], "psd": psd_task["id"], "erp": erp_task["id"]},
        "report_id": report["id"],
        "package_path": str(package_path),
        "results": RESULTS,
    }
    report_dir = ROOT / "work" / "acceptance"
    report_dir.mkdir(parents=True, exist_ok=True)
    output = report_dir / "v01_acceptance_latest.json"
    output.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "results"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
