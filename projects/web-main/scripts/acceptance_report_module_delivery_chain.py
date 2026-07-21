from __future__ import annotations

import csv
import importlib
import json
import os
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("QLANALYSER_ENV", "test")
os.environ.setdefault("QLANALYSER_SANDBOX_MODE", "true")


WORK = ROOT / "work" / "release_evidence" / "report_module_delivery_chain"
PROJECT_ID = "proj_report_module_delivery"
INPUT_FILE_ID = "eeg_report_module_delivery"
OWNER_USER_ID = "demo-customer"
ACCEPTANCE_CHARGE_CREDITS = 1.0

MODULE_TABLES = {
    "psd": ("resting_psd", "tables/band_power.csv"),
    "erp": ("erp_p300", "tables/erp_metrics.csv"),
    "tfr": ("tfr_ersp_itc", "tables/tfr_summary_table.csv"),
    "multitaper_psd_tfr": ("multitaper_psd_tfr", "tables/multitaper_band_power.csv"),
    "pac": ("pac_cfc", "tables/pac_channel_summary.csv"),
    "pac_v2": ("pac_v2_lab", "tables/pac_v2_channel_summary.csv"),
    "reference_csd": ("reference_csd", "tables/reference_channels.csv"),
    "connectivity": ("connectivity", "tables/connectivity_edges_long.csv"),
}


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    _write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def _charge_preview() -> dict[str, Any]:
    return {
        "billing_account_id": OWNER_USER_ID,
        "estimated_credits": ACCEPTANCE_CHARGE_CREDITS,
    }


def _seed_posted_charge(state_store, governance_model, task_id: str, module_name: str) -> None:
    state_store.upsert_item(
        "billing_transactions",
        governance_model.BillingTransactionRead(
            id=f"billtx_{task_id}",
            account_id=OWNER_USER_ID,
            direction="debit",
            amount_credits=ACCEPTANCE_CHARGE_CREDITS,
            balance_after_credits=99.0,
            source_type="analysis_task",
            source_id=task_id,
            description=f"{module_name.upper()} acceptance posted charge",
            metadata_json={"module_name": module_name},
        ),
    )


def _seed_output(output_dir: Path, module_name: str, workflow_id: str, table_relative: str) -> list[Path]:
    table_path = output_dir / table_relative
    _write_text(table_path, f"metric,value\n{module_name}_metric,1\n")
    _write_json(
        output_dir / "result.json",
        {
            "status": "completed",
            "module_name": module_name,
            "workflow_id": workflow_id,
            "parameters": {"acceptance": "report_module_delivery_chain"},
            "warnings": [],
        },
    )
    _write_json(
        output_dir / "manifest.json",
        {
            "schema_version": "acceptance-module-manifest-v0.1",
            "artifact_schema_version": "acceptance-module-artifacts-v0.1",
            "files": [table_relative, "result.json"],
        },
    )
    _write_text(output_dir / "log.txt", f"{module_name} completed\n")
    _write_json(output_dir / "reproducibility" / "parameters.json", {"module_name": module_name})
    _write_json(output_dir / "reproducibility" / "software_versions.json", {"qlanalyser": "acceptance"})
    _write_json(
        output_dir / "reproducibility" / "workflow.json",
        {"steps": [{"name": "seed_acceptance_artifact", "module": module_name}]},
    )
    _write_json(
        output_dir / "reproducibility" / "table_dictionary.json",
        {table_relative: {"description": f"{module_name} primary table"}},
    )
    _write_json(
        output_dir / "reproducibility" / "scope_contract.json",
        {
            "analysis_scope": f"{module_name}_acceptance_delivery",
            "disallowed_claims": ["diagnosis", "source_localization", "causality"],
        },
    )
    _write_text(output_dir / "reproducibility" / "method_description.txt", f"{module_name} acceptance method.\n")
    return [
        table_path,
        output_dir / "result.json",
        output_dir / "manifest.json",
        output_dir / "reproducibility" / "parameters.json",
        output_dir / "reproducibility" / "method_description.txt",
    ]


def _seed_task(
    *,
    state_store,
    task_model,
    artifact_model,
    derivatives_root: Path,
    module_name: str,
    workflow_id: str,
    table_relative: str,
) -> str:
    task_id = f"task_{module_name}"
    output_dir = derivatives_root / PROJECT_ID / task_id
    artifact_paths = _seed_output(output_dir, module_name, workflow_id, table_relative)
    task = task_model.AnalysisTaskRead(
        id=task_id,
        organization_id="local-org",
        project_id=PROJECT_ID,
        module_name=module_name,
        workflow_id=workflow_id,
        input_file_id=INPUT_FILE_ID,
        owner_user_id=OWNER_USER_ID,
        created_by=OWNER_USER_ID,
        status="completed",
        queue_status="completed",
        progress=100,
        parameters_json={"acceptance": "report_module_delivery_chain"},
        quota_charge_preview_json=_charge_preview(),
    )
    state_store.upsert_item("tasks", task)
    for index, path in enumerate(artifact_paths, start=1):
        artifact = artifact_model.ArtifactRead(
            id=f"artifact_{module_name}_{index}",
            task_id=task_id,
            organization_id=task.organization_id,
            project_id=PROJECT_ID,
            input_file_id=INPUT_FILE_ID,
            artifact_type=path.suffix.lstrip(".") or "file",
            label=path.stem,
            path=path,
            size_bytes=path.stat().st_size,
            mime_type="text/csv" if path.suffix == ".csv" else "application/json",
        )
        state_store.upsert_item("artifacts", artifact)
    return task_id


def _seed_qc_related_artifact(state_store, task_model, artifact_model, derivatives_root: Path, task_id: str = "task_qc_related") -> None:
    output_dir = derivatives_root / PROJECT_ID / task_id
    qc_path = output_dir / "reproducibility" / "qc_summary.json"
    _write_json(qc_path, {"status": "completed", "module_name": "qc"})
    task = task_model.AnalysisTaskRead(
        id=task_id,
        organization_id="local-org",
        project_id=PROJECT_ID,
        module_name="qc",
        workflow_id="metadata_qc",
        input_file_id=INPUT_FILE_ID,
        owner_user_id=OWNER_USER_ID,
        status="completed",
        queue_status="completed",
        progress=100,
        quota_charge_preview_json=_charge_preview(),
    )
    state_store.upsert_item("tasks", task)
    state_store.upsert_item(
        "artifacts",
        artifact_model.ArtifactRead(
            id=f"artifact_qc_summary_{task_id}",
            task_id=task_id,
            organization_id=task.organization_id,
            project_id=PROJECT_ID,
            input_file_id=INPUT_FILE_ID,
            artifact_type="json",
            label="qc_summary",
            path=qc_path,
            size_bytes=qc_path.stat().st_size,
            mime_type="application/json",
        ),
    )


def _mark_reviewed(audit_service, task_id: str) -> None:
    audit_service.record_event(
        action="result.reviewed",
        object_type="analysis_task",
        object_id=task_id,
        project_id=PROJECT_ID,
        actor_user_id=OWNER_USER_ID,
    )


def _seed_excluded_epilepsy_task(state_store, task_model, artifact_model, derivatives_root: Path) -> None:
    task_id = "task_epilepsy_excluded"
    output_dir = derivatives_root / PROJECT_ID / task_id
    table_path = output_dir / "tables" / "epilepsy_events.csv"
    _write_text(table_path, "event_id,start_sec,end_sec\nexcluded,0,1\n")
    task = task_model.AnalysisTaskRead(
        id=task_id,
        organization_id="local-org",
        project_id=PROJECT_ID,
        module_name="epilepsy",
        workflow_id="epilepsy_std_threshold",
        input_file_id=INPUT_FILE_ID,
        owner_user_id=OWNER_USER_ID,
        status="completed",
        queue_status="completed",
        progress=100,
        quota_charge_preview_json=_charge_preview(),
    )
    state_store.upsert_item("tasks", task)
    state_store.upsert_item(
        "artifacts",
        artifact_model.ArtifactRead(
            id="artifact_epilepsy_excluded",
            task_id=task_id,
            organization_id=task.organization_id,
            project_id=PROJECT_ID,
            input_file_id=INPUT_FILE_ID,
            artifact_type="csv",
            label="epilepsy_events",
            path=table_path,
            size_bytes=table_path.stat().st_size,
            mime_type="text/csv",
        ),
    )


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True, exist_ok=True)

    state_root = WORK / "state"
    derivatives_root = WORK / "derivatives"
    reports_root = WORK / "reports"
    os.environ["QLANALYSER_STATE_ROOT"] = str(state_root)

    import backend.services.state_store as state_store
    import backend.services.audit_service as audit_service
    import backend.services.quota_service as quota_service
    import backend.services.task_service as task_service
    import backend.services.report_service as report_service
    import backend.models.analysis_task as task_model
    import backend.models.artifact as artifact_model
    import backend.models.governance as governance_model
    import backend.models.report as report_model

    for module in (state_store, audit_service, quota_service, task_service, report_service):
        importlib.reload(module)

    task_service.DERIVATIVES_ROOT = derivatives_root
    report_service.DERIVATIVES_ROOT = derivatives_root
    report_service.REPORT_ROOT = reports_root

    task_ids: dict[str, str] = {}
    for module_name, (workflow_id, table_relative) in MODULE_TABLES.items():
        task_ids[module_name] = _seed_task(
            state_store=state_store,
            task_model=task_model,
            artifact_model=artifact_model,
            derivatives_root=derivatives_root,
            module_name=module_name,
            workflow_id=workflow_id,
            table_relative=table_relative,
        )
        _seed_posted_charge(state_store, governance_model, task_ids[module_name], module_name)
    unpaid_erp_task_id = _seed_task(
        state_store=state_store,
        task_model=task_model,
        artifact_model=artifact_model,
        derivatives_root=derivatives_root,
        module_name="erp",
        workflow_id="erp_p300",
        table_relative="tables/erp_metrics.csv",
    )
    # This later record replaces the seeded task id to a task with no posted charge.
    unpaid_task = task_model.AnalysisTaskRead(
        id="task_erp_unpaid_sibling",
        organization_id="local-org",
        project_id=PROJECT_ID,
        module_name="erp",
        workflow_id="erp_p300",
        input_file_id=INPUT_FILE_ID,
        owner_user_id=OWNER_USER_ID,
        created_by=OWNER_USER_ID,
        status="completed",
        queue_status="completed",
        progress=100,
        quota_charge_preview_json=_charge_preview(),
    )
    unpaid_dir = derivatives_root / PROJECT_ID / unpaid_task.id
    _seed_output(unpaid_dir, "erp", "erp_p300", "tables/erp_metrics.csv")
    state_store.upsert_item("tasks", unpaid_task)
    for artifact in list(state_store.load_registry("artifacts", artifact_model.ArtifactRead).values()):
        if artifact.task_id == unpaid_erp_task_id:
            clone = artifact.model_copy(update={
                "id": f"{artifact.id}_unpaid",
                "task_id": unpaid_task.id,
                "path": unpaid_dir / Path(str(artifact.path)).relative_to(derivatives_root / PROJECT_ID / unpaid_erp_task_id),
            })
            state_store.upsert_item("artifacts", clone)
    _mark_reviewed(audit_service, unpaid_task.id)
    _seed_qc_related_artifact(state_store, task_model, artifact_model, derivatives_root)
    _seed_qc_related_artifact(state_store, task_model, artifact_model, derivatives_root, task_id="task_qc_unreviewed")
    _seed_posted_charge(state_store, governance_model, "task_qc_related", "qc")
    _seed_excluded_epilepsy_task(state_store, task_model, artifact_model, derivatives_root)
    _seed_posted_charge(state_store, governance_model, "task_epilepsy_excluded", "epilepsy")

    alias_sources: dict[str, str] = {}
    for module_name, (_, table_relative) in MODULE_TABLES.items():
        alias_dir = WORK / "alias_checks" / module_name
        alias_dir.mkdir(parents=True, exist_ok=True)
        alias_path = report_service._write_metrics_csv_alias(
            alias_dir,
            derivatives_root / PROJECT_ID / task_ids[module_name],
        )
        if alias_path is None:
            raise AssertionError(f"metrics alias missing for {module_name}")
        rows = _read_csv_rows(alias_path)
        if not rows:
            raise AssertionError(f"metrics alias has no rows for {module_name}")
        source_table = rows[0].get("source_table")
        expected_source = Path(table_relative).name
        if source_table != expected_source:
            raise AssertionError(f"{module_name} metrics alias used {source_table}, expected {expected_source}")
        alias_sources[module_name] = str(source_table)

    primary_task_id = task_ids["psd"]
    _mark_reviewed(audit_service, primary_task_id)
    _mark_reviewed(audit_service, task_ids["erp"])
    _mark_reviewed(audit_service, "task_qc_related")
    report = report_service.create_report(
        report_model.ReportCreate(
            project_id=PROJECT_ID,
            task_id=primary_task_id,
            title="Report module delivery chain acceptance",
            owner_user_id=OWNER_USER_ID,
            created_by=OWNER_USER_ID,
        )
    )
    if report.package_path is None or not Path(report.package_path).exists():
        raise AssertionError("report package was not created")

    with zipfile.ZipFile(report.package_path) as zf:
        names = {name.replace("\\", "/") for name in zf.namelist()}
        report_manifest = json.loads(zf.read("reports/report_manifest.json").decode("utf-8"))
        report_json = json.loads(zf.read("reports/report.json").decode("utf-8"))
        metrics_rows = list(csv.DictReader(zf.read("tables/metrics.csv").decode("utf-8").splitlines()))

    expected_modules = sorted(["psd", "erp"])
    manifest_modules = sorted(report_manifest.get("included_analysis_modules") or [])
    report_json_modules = sorted(item.get("module_name") for item in report_json.get("included_analyses") or [])
    if manifest_modules != expected_modules:
        raise AssertionError(f"manifest included modules mismatch: {manifest_modules} != {expected_modules}")
    if report_json_modules != expected_modules:
        raise AssertionError(f"report.json included modules mismatch: {report_json_modules} != {expected_modules}")

    missing_package_entries: list[str] = []
    for module_name in expected_modules:
        _, table_relative = MODULE_TABLES[module_name]
        expected = f"analyses/{module_name}_{task_ids[module_name]}/{table_relative}"
        if expected not in names:
            missing_package_entries.append(expected)
    if missing_package_entries:
        raise AssertionError(f"report package missing sibling analysis entries: {missing_package_entries}")

    advanced_modules = sorted(set(MODULE_TABLES) - set(expected_modules))
    advanced_entries = [
        name
        for name in names
        if any(name.startswith(f"analyses/{module_name}_") for module_name in advanced_modules)
    ]
    if advanced_entries:
        raise AssertionError(f"advanced modules should not be included by default: {advanced_entries[:20]}")

    if any(name.startswith("analyses/epilepsy_") for name in names):
        raise AssertionError("epilepsy analysis should not be included in the non-sleep/non-epilepsy delivery chain")
    if "qc/metadata_qc/qc_summary.json" not in names:
        raise AssertionError("related QC artifact was not included")
    blocked_unpaid_entries = [name for name in names if "task_erp_unpaid_sibling" in name]
    if blocked_unpaid_entries:
        raise AssertionError(f"unpaid sibling analysis should not be included: {blocked_unpaid_entries}")
    blocked_unreviewed_qc = [name for name in names if "task_qc_unreviewed" in name]
    if blocked_unreviewed_qc:
        raise AssertionError(f"unreviewed QC artifacts should not be included: {blocked_unreviewed_qc}")
    if not metrics_rows or metrics_rows[0].get("source_table") != "band_power.csv":
        raise AssertionError(f"report package metrics.csv did not use the PSD primary table: {metrics_rows[:1]}")

    evidence = {
        "status": "passed",
        "report_id": report.id,
        "report_package": str(report.package_path),
        "primary_task_id": primary_task_id,
        "included_modules": manifest_modules,
        "alias_sources": alias_sources,
        "checked_package_entries": sorted(
            f"analyses/{module_name}_{task_ids[module_name]}/{table_relative}"
            for module_name, (_, table_relative) in MODULE_TABLES.items()
            if module_name in expected_modules
        ),
        "excluded_modules": ["epilepsy", *advanced_modules],
        "qc_related_artifact": "qc/metadata_qc/qc_summary.json",
        "file_count": len(names),
    }
    evidence_path = WORK / "acceptance_report_module_delivery_chain.json"
    evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
