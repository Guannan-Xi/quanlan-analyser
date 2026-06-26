import importlib
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import HTTPException


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="qlanalyser-prep-plan-") as tmp:
        root = Path(tmp)
        os.environ["QLANALYSER_STATE_ROOT"] = str(root / "state")
        os.environ["QLANALYSER_DERIVATIVES_ROOT"] = str(root / "derivatives")

        import backend.services.state_store as state_store
        import backend.services.storage_service as storage_service
        import backend.services.data_preparation_service as data_preparation_service
        import backend.services.task_service as task_service
        import backend.models.eeg_file as eeg_model
        import backend.models.data_preparation as prep_model
        import backend.models.analysis_task as task_model

        importlib.reload(state_store)
        importlib.reload(storage_service)
        importlib.reload(data_preparation_service)
        importlib.reload(task_service)

        eeg_file = eeg_model.EEGFileRead(
            id="eeg_acceptance",
            project_id="proj_acceptance",
            subject_id="sub_01",
            original_filename="acceptance.edf",
            stored_path=root / "uploads" / "acceptance.edf",
            detected_format="edf",
            sampling_rate=250.0,
            channel_count=32,
            duration_sec=60.0,
        )
        state_store.upsert_item("eeg_files", eeg_file)

        created = data_preparation_service.save_plan(prep_model.DataPreparationPlanCreate(
            project_id="proj_acceptance",
            input_file_id="eeg_acceptance",
            preprocessing_json={"reference": "average", "notch_hz": 50},
            qc_json={"min_duration_sec": 30},
            psd_json={"bands": {"alpha": [8, 12]}, "fmin": 2, "fmax": 35},
            bad_channels=[{"name": "Oz", "reason": "flat"}],
            bad_segments=[{"start_sec": 1.0, "end_sec": 2.5, "reason": "motion"}],
            annotation_actions=[{"action": "exclude", "description": "BAD_manual"}],
        ))
        assert created.revision == 1
        assert created.schema_version == data_preparation_service.CONTRACT_VERSION
        assert created.artifact_root is not None
        assert (created.artifact_root / "reproducibility" / "data_preparation_plan.json").exists()
        assert (created.artifact_root / "reproducibility" / "data_preparation_artifact_contract.json").exists()
        contract = json.loads((created.artifact_root / "reproducibility" / "data_preparation_artifact_contract.json").read_text(encoding="utf-8"))
        assert contract["contract_version"] == "qlanalyser-data-preparation-v0.2"
        assert "erp" in contract["allowed_modules"]

        read_back = data_preparation_service.get_plan(created.id)
        assert read_back.id == created.id
        assert read_back.input_file_id == "eeg_acceptance"

        updated = data_preparation_service.update_plan(created.id, prep_model.DataPreparationPlanUpdate(
            expected_revision=1,
            preprocessing_json={"reference": "average", "notch_hz": 60},
        ))
        assert updated.revision == 2
        try:
            data_preparation_service.update_plan(created.id, prep_model.DataPreparationPlanUpdate(
                expected_revision=1,
                description="stale edit",
            ))
        except HTTPException as exc:
            assert exc.status_code == 409
            assert exc.detail["error_code"] == "PLAN_REVISION_CONFLICT"
            assert exc.detail["legacy_error_code"] == "data_preparation_revision_conflict"
        else:
            raise AssertionError("stale revision update should fail")

        default_plan = data_preparation_service.get_current_plan_for_file("eeg_acceptance")
        assert default_plan.id == created.id
        assert default_plan.is_default is False
        default_plan.module_scope = ["qc", "psd", "erp", "tfr", "pac", "reference_csd"]
        state_store.upsert_item("data_preparation_plans", default_plan)
        migrated_plan = data_preparation_service.get_plan(created.id)
        assert "multitaper_psd_tfr" in migrated_plan.module_scope
        assert "connectivity" in migrated_plan.module_scope
        migrated_contract = json.loads((migrated_plan.artifact_root / "reproducibility" / "data_preparation_artifact_contract.json").read_text(encoding="utf-8"))
        assert "multitaper_psd_tfr" in migrated_contract["allowed_modules"]
        assert "connectivity" in migrated_contract["allowed_modules"]

        eeg_default = eeg_model.EEGFileRead(
            id="eeg_default",
            project_id="proj_acceptance",
            original_filename="default.edf",
            stored_path=root / "uploads" / "default.edf",
            detected_format="edf",
        )
        state_store.upsert_item("eeg_files", eeg_default)
        new_default = data_preparation_service.get_current_plan_for_file("eeg_default")
        assert new_default.is_default is True
        assert new_default.revision == 0

        ref = data_preparation_service.create_task_reference(created.id, prep_model.DataPreparationTaskReferenceCreate(
            module_name="psd",
            workflow_id="resting_psd",
            expected_revision=2,
            task_id="task_acceptance",
        ))
        assert ref.parameters_json["data_preparation_plan_id"] == created.id
        assert ref.parameters_json["data_preparation_revision"] == 2
        assert (ref.artifact_root / "reproducibility" / "data_preparation_task_reference.json").exists()

        task_parameters = {
            "data_preparation_plan_id": created.id,
            "data_preparation_revision": 2,
        }
        task_plan = data_preparation_service.validate_task_parameters("qc", task_parameters)
        assert task_plan.id == created.id
        assert task_parameters["data_preparation_contract_version"] == data_preparation_service.CONTRACT_VERSION
        erp_parameters = {
            "data_preparation_plan_id": created.id,
            "data_preparation_revision": 2,
        }
        erp_plan = data_preparation_service.validate_task_parameters("erp", erp_parameters)
        assert erp_plan.id == created.id
        assert erp_parameters["data_preparation_contract_version"] == data_preparation_service.CONTRACT_VERSION


        # Verify task-level plan reference writes a task-scoped artifact without changing PSD algorithm details.
        def fake_qc_runner(input_path, output_dir, parameters=None):
            output = Path(output_dir)
            (output / "reproducibility").mkdir(parents=True, exist_ok=True)
            result_path = output / "result.json"
            result_path.write_text("{}\n", encoding="utf-8")
            return {"result": result_path}

        task_service.run_quality_check = fake_qc_runner
        task = task_service.create_task(task_model.AnalysisTaskCreate(
            project_id="proj_acceptance",
            module_name="qc",
            workflow_id="metadata_qc",
            input_file_id="eeg_acceptance",
            parameters_json={
                "data_preparation_plan_id": created.id,
                "data_preparation_revision": 2,
            },
        ))
        artifacts = task_service.list_task_artifacts(task.id)
        labels = {artifact.label for artifact in artifacts}
        assert "Data preparation task reference" in labels

        captured_psd_parameters = {}

        def fake_psd_runner(input_path, output_dir, parameters=None):
            captured_psd_parameters.update(parameters or {})
            output = Path(output_dir)
            (output / "reproducibility").mkdir(parents=True, exist_ok=True)
            result_path = output / "result.json"
            result_path.write_text("{}\n", encoding="utf-8")
            return {"result": result_path}

        task_service.run_psd = fake_psd_runner
        psd_task = task_service.create_task(task_model.AnalysisTaskCreate(
            project_id="proj_acceptance",
            module_name="psd",
            workflow_id="resting_psd",
            input_file_id="eeg_acceptance",
            parameters_json={
                "data_preparation_plan_id": created.id,
                "data_preparation_revision": 2,
            },
        ))
        psd_artifacts = task_service.list_task_artifacts(psd_task.id)
        psd_labels = {artifact.label for artifact in psd_artifacts}
        assert "Data preparation task reference" in psd_labels
        assert captured_psd_parameters["data_preparation_plan_id"] == created.id
        assert captured_psd_parameters["data_preparation_revision"] == 2
        assert captured_psd_parameters["bad_channels"] == ["Oz"]
        assert captured_psd_parameters["bad_segments"] == [{"onset": 1.0, "duration": 1.5, "description": "motion"}]
        assert captured_psd_parameters["annotation_actions"] == [{"action": "exclude", "description": "BAD_manual"}]
        assert captured_psd_parameters["fmin"] == 2
        assert captured_psd_parameters["fmax"] == 35

        erp_ref = data_preparation_service.create_task_reference(created.id, prep_model.DataPreparationTaskReferenceCreate(
            module_name="erp",
            workflow_id="erp_p300",
            expected_revision=2,
            task_id="task_erp_acceptance",
        ))
        assert erp_ref.module_name == "erp"
        captured_erp_parameters = {}

        def fake_erp_runner(input_path, output_dir, parameters=None):
            captured_erp_parameters.update(parameters or {})
            output = Path(output_dir)
            (output / "reproducibility").mkdir(parents=True, exist_ok=True)
            result_path = output / "erp_result.json"
            result_path.write_text("{}\n", encoding="utf-8")
            return {"erp_result": result_path}

        task_service.run_erp_p300 = fake_erp_runner
        erp_task = task_service.create_task(task_model.AnalysisTaskCreate(
            project_id="proj_acceptance",
            module_name="erp",
            workflow_id="erp_p300",
            input_file_id="eeg_acceptance",
            parameters_json={
                "data_preparation_plan_id": created.id,
                "data_preparation_revision": 2,
            },
        ))
        erp_artifacts = task_service.list_task_artifacts(erp_task.id)
        erp_labels = {artifact.label for artifact in erp_artifacts}
        assert "Data preparation task reference" in erp_labels
        assert captured_erp_parameters["data_preparation_plan_id"] == created.id
        assert captured_erp_parameters["data_preparation_revision"] == 2
        assert captured_erp_parameters["bad_channels"] == ["Oz"]
        assert captured_erp_parameters["bad_segments"] == [{"onset": 1.0, "duration": 1.5, "description": "motion"}]
        assert captured_erp_parameters["annotation_actions"] == [{"action": "exclude", "description": "BAD_manual"}]
        assert "fmin" not in captured_erp_parameters
        assert "fmax" not in captured_erp_parameters

        multitaper_ref = data_preparation_service.create_task_reference(created.id, prep_model.DataPreparationTaskReferenceCreate(
            module_name="multitaper_psd_tfr",
            workflow_id="multitaper_psd_tfr",
            expected_revision=2,
            task_id="task_multitaper_acceptance",
        ))
        assert multitaper_ref.module_name == "multitaper_psd_tfr"
        captured_multitaper_parameters = {}

        def fake_multitaper_runner(input_path, output_dir, parameters=None):
            captured_multitaper_parameters.update(parameters or {})
            output = Path(output_dir)
            (output / "reproducibility").mkdir(parents=True, exist_ok=True)
            result_path = output / "multitaper_result.json"
            result_path.write_text("{}\n", encoding="utf-8")
            return {"multitaper_result": result_path}

        task_service.run_multitaper_psd_tfr = fake_multitaper_runner
        multitaper_task = task_service.create_task(task_model.AnalysisTaskCreate(
            project_id="proj_acceptance",
            module_name="multitaper_psd_tfr",
            workflow_id="multitaper_psd_tfr",
            input_file_id="eeg_acceptance",
            parameters_json={
                "analysis_family": "psd",
                "data_preparation_plan_id": created.id,
                "data_preparation_revision": 2,
            },
        ))
        multitaper_artifacts = task_service.list_task_artifacts(multitaper_task.id)
        multitaper_labels = {artifact.label for artifact in multitaper_artifacts}
        assert "Data preparation task reference" in multitaper_labels
        assert captured_multitaper_parameters["data_preparation_plan_id"] == created.id
        assert captured_multitaper_parameters["data_preparation_revision"] == 2
        assert captured_multitaper_parameters["bad_channels"] == ["Oz"]
        assert captured_multitaper_parameters["bad_segments"] == [{"onset": 1.0, "duration": 1.5, "description": "motion"}]
        assert captured_multitaper_parameters["annotation_actions"] == [{"action": "exclude", "description": "BAD_manual"}]

        connectivity_ref = data_preparation_service.create_task_reference(created.id, prep_model.DataPreparationTaskReferenceCreate(
            module_name="connectivity",
            workflow_id="connectivity",
            expected_revision=2,
            task_id="task_connectivity_acceptance",
        ))
        assert connectivity_ref.module_name == "connectivity"
        captured_connectivity_parameters = {}

        def fake_connectivity_runner(input_path, output_dir, parameters=None):
            captured_connectivity_parameters.update(parameters or {})
            output = Path(output_dir)
            (output / "reproducibility").mkdir(parents=True, exist_ok=True)
            result_path = output / "connectivity_result.json"
            result_path.write_text("{}\n", encoding="utf-8")
            return {"connectivity_result": result_path}

        task_service.run_connectivity = fake_connectivity_runner
        connectivity_task = task_service.create_task(task_model.AnalysisTaskCreate(
            project_id="proj_acceptance",
            module_name="connectivity",
            workflow_id="connectivity",
            input_file_id="eeg_acceptance",
            parameters_json={
                "method": "correlation",
                "data_preparation_plan_id": created.id,
                "data_preparation_revision": 2,
            },
        ))
        connectivity_artifacts = task_service.list_task_artifacts(connectivity_task.id)
        connectivity_labels = {artifact.label for artifact in connectivity_artifacts}
        assert "Data preparation task reference" in connectivity_labels
        assert captured_connectivity_parameters["data_preparation_plan_id"] == created.id
        assert captured_connectivity_parameters["data_preparation_revision"] == 2
        assert captured_connectivity_parameters["bad_channels"] == ["Oz"]
        assert captured_connectivity_parameters["bad_segments"] == [{"onset": 1.0, "duration": 1.5, "description": "motion"}]
        assert captured_connectivity_parameters["annotation_actions"] == [{"action": "exclude", "description": "BAD_manual"}]

        try:
            data_preparation_service.validate_task_parameters("psd", {
                "data_preparation_plan_id": created.id,
                "data_preparation_revision": 1,
            })
        except HTTPException as exc:
            assert exc.status_code == 409
        else:
            raise AssertionError("stale task reference should fail")

        print(json.dumps({
            "status": "passed",
            "plan_id": created.id,
            "revision": updated.revision,
            "artifact_root": str(updated.artifact_root),
            "task_reference_module": ref.module_name,
            "task_id": task.id,
        }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
