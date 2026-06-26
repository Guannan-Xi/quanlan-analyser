import csv
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import mne
import numpy as np

from eeg_core.analysis.psd import run_psd, validate_psd_parameters


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def make_alpha_raw(path: Path) -> Path:
    sfreq = 200.0
    times = np.arange(int(sfreq * 8.0)) / sfreq
    alpha = 8e-6 * np.sin(2 * np.pi * 10.0 * times)
    noise = 0.2e-6 * np.random.default_rng(17).normal(size=(4, len(times)))
    data = np.vstack([alpha, alpha * 0.8, noise[2], noise[3]])
    info = mne.create_info(["Fz", "Cz", "Pz", "Oz"], sfreq=sfreq, ch_types="eeg")
    raw = mne.io.RawArray(data, info, verbose="ERROR")
    raw.save(path, overwrite=True, verbose="ERROR")
    return path


def read_csv_rows(path: Path):
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main():
    with tempfile.TemporaryDirectory(prefix="qlanalyser_psd_p0_") as temp:
        work = Path(temp)
        fif = make_alpha_raw(work / "alpha_raw.fif")
        output = work / "psd"
        artifacts = run_psd(
            fif,
            output,
            {
                "workflow_id": "resting_psd",
                "data_preparation_plan_id": "plan-demo-001",
                "data_preparation_revision": 7,
                "bad_channels": ["Oz"],
                "bad_segments": [{"start_sec": 0.0, "end_sec": 0.2, "description": "bad_psd_segment"}],
                "annotation_actions": [{"action": "mark_bad_segment", "description": "BAD_manual"}],
                "fmin": 1.0,
                "fmax": 40.0,
                "n_fft": 256,
                "n_overlap": 64,
            },
        )

        expected_keys = {
            "band_power",
            "channel_band_power",
            "spectrum_long",
            "psd_mean_spectrum",
            "psd_band_power",
            "parameters",
            "psd_summary",
            "parameter_schema_snapshot",
            "threshold_validation",
            "effective_call",
            "source_metadata",
            "table_dictionary",
            "scope_contract",
            "result",
            "manifest",
            "log",
        }
        require(expected_keys.issubset(artifacts), f"missing artifact keys: {expected_keys - set(artifacts)}")
        for key in expected_keys:
            path = Path(artifacts[key])
            require(path.exists() and path.stat().st_size > 0, f"empty artifact: {key} {path}")

        band_rows = read_csv_rows(Path(artifacts["band_power"]))
        alpha = next(row for row in band_rows if row["band"] == "alpha")
        beta = next(row for row in band_rows if row["band"] == "beta")
        require(float(alpha["mean_psd"]) > float(beta["mean_psd"]), "synthetic 10 Hz signal should favor alpha band")

        channel_rows = read_csv_rows(Path(artifacts["channel_band_power"]))
        require({row["channel"] for row in channel_rows} == {"Fz", "Cz", "Pz"}, "bad channel should be excluded")

        spectrum_rows = read_csv_rows(Path(artifacts["spectrum_long"]))
        require({"channel", "frequency_hz", "psd"} <= set(spectrum_rows[0]), "spectrum_long schema mismatch")

        summary = json.loads(Path(artifacts["psd_summary"]).read_text(encoding="utf-8"))
        require(summary["data_preparation_plan_id"] == "plan-demo-001", "plan id not recorded")
        require(summary["data_preparation_revision"] == 7, "plan revision not recorded")
        require(summary["applied_data_preparation"]["bad_channels"] == ["Oz"], "bad channel directive not recorded")
        require(summary["applied_data_preparation"]["bad_segments"] == [{"onset": 0.0, "duration": 0.2, "description": "bad_psd_segment"}], "start/end bad segment not normalized")
        require(summary["applied_data_preparation"]["annotation_actions"] == [{"action": "mark_bad_segment", "description": "BAD_manual"}], "annotation actions not recorded")
        require("parameter_schema" in summary, "parameter schema missing from summary")
        require("data_preparation_revision" in summary["parameter_schema"], "revision schema missing")
        require("mne/time_frequency/psd.py:98" in "\n".join(summary["mne_reference"]["paths"]), "MNE PSD reference missing")

        result = json.loads(Path(artifacts["result"]).read_text(encoding="utf-8"))
        require(result["artifact_schema_version"] == "qlanalyser-artifact-registry-v0.1", "result missing artifact schema version")
        require(len(result["parameters_hash"]) == 64, "result missing parameters hash")
        require(result["parameters"]["data_preparation_plan_id"] == "plan-demo-001", "result missing plan id")
        require(result["parameters"]["data_preparation_revision"] == 7, "result missing plan revision")
        require(result["summary"]["data_preparation_revision"] == 7, "result summary missing plan revision")
        for reference in (
            "parameter_schema_snapshot",
            "threshold_validation",
            "effective_call",
            "source_metadata",
            "table_dictionary",
            "scope_contract",
        ):
            require(reference in result["references"], f"result missing {reference} reference")

        workflow = json.loads(Path(artifacts["workflow"]).read_text(encoding="utf-8"))
        require(workflow["parameters"]["data_preparation_revision"] == 7, "workflow missing plan revision")

        parameter_schema = json.loads(Path(artifacts["parameter_schema_snapshot"]).read_text(encoding="utf-8"))
        require("data_preparation_revision" in parameter_schema["parameter_schema"], "sidecar schema missing plan revision")
        require(len(parameter_schema["parameter_schema_hash"]) == 64, "schema hash missing")

        effective_call = json.loads(Path(artifacts["effective_call"]).read_text(encoding="utf-8"))
        require(effective_call["call"] == "Raw.compute_psd", "effective call should preserve MNE PSD runner")
        require(effective_call["kwargs"]["method"] == "welch", "effective call should use Welch")
        require(effective_call["kwargs"]["n_fft"] == 256, "effective call missing n_fft")
        require(effective_call["output_shape"]["channels"] == 3, "effective call channel count mismatch")

        threshold_validation = json.loads(Path(artifacts["threshold_validation"]).read_text(encoding="utf-8"))
        require(threshold_validation["status"] == "passed", "threshold validation did not pass")
        require({check["field"] for check in threshold_validation["checks"]} >= {"fmin", "fmax", "n_fft", "n_overlap"}, "threshold checks incomplete")

        table_dictionary = json.loads(Path(artifacts["table_dictionary"]).read_text(encoding="utf-8"))
        require("tables/spectrum_long.csv" in table_dictionary["tables"], "table dictionary missing spectrum table")
        require(table_dictionary["tables"]["tables/spectrum_long.csv"]["columns"]["frequency_hz"]["unit"] == "Hz", "frequency unit missing")

        source_metadata = json.loads(Path(artifacts["source_metadata"]).read_text(encoding="utf-8"))
        require(source_metadata["source_file"]["filename"] == "alpha_raw.fif", "source metadata should record filename")
        require(len(source_metadata["source_file"]["sha256"]) == 64, "source file hash missing")
        require(":" not in source_metadata["source_file"]["filename"], "source metadata leaked path-like filename")

        scope_contract = json.loads(Path(artifacts["scope_contract"]).read_text(encoding="utf-8"))
        require(scope_contract["analysis_scope"] == "single_record_descriptive_sensor_space_psd", "scope contract mismatch")
        require("diagnosis_or_treatment_recommendation" in scope_contract["disallowed_claims"], "clinical boundary missing")

        log_text = Path(artifacts["log"]).read_text(encoding="utf-8")
        require("data_preparation_plan_id=plan-demo-001" in log_text, "log missing plan id")
        require("data_preparation_revision=7" in log_text, "log missing plan revision")

        manifest = json.loads(Path(artifacts["manifest"]).read_text(encoding="utf-8"))
        require(manifest["artifact_schema_version"] == "qlanalyser-artifact-registry-v0.1", "manifest missing artifact schema version")
        manifest_paths = {entry["path"] for entry in manifest["files"]}
        require(
            {
                "result.json",
                "reproducibility/parameters.json",
                "reproducibility/workflow.json",
                "reproducibility/effective_call.json",
                "reproducibility/parameter_schema_snapshot.json",
                "reproducibility/threshold_validation.json",
                "reproducibility/source_metadata.json",
                "reproducibility/table_dictionary.json",
                "reproducibility/scope_contract.json",
            }
            <= manifest_paths,
            "manifest missing evidence files",
        )

        try:
            validate_psd_parameters({"fmin": 20.0, "fmax": 10.0}, sfreq=200.0, n_times=1000)
        except ValueError as exc:
            require("frequency range" in str(exc).lower(), str(exc))
        else:
            raise AssertionError("invalid frequency range should fail")

        print(json.dumps({"status": "passed", "work": str(work), "artifacts": sorted(artifacts)}, indent=2))


if __name__ == "__main__":
    main()
