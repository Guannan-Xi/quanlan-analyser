from __future__ import annotations

import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EDF_UI_EVIDENCE = ROOT / "work" / "release_evidence" / "edf_upload_to_results_ui_only" / "edf_upload_to_results_ui_only.json"
OUT_PATH = ROOT / "work" / "release_evidence" / "virtual_reviewer_round_007" / "round_007_real_report_consumption.json"


def status(ok: bool, evidence: Any = None) -> dict[str, Any]:
    item: dict[str, Any] = {"status": "pass" if ok else "block"}
    if evidence is not None:
        item["evidence"] = evidence
    return item


def load_json_from_zip(zf: zipfile.ZipFile, name: str) -> dict[str, Any]:
    return json.loads(zf.read(name).decode("utf-8"))


def text_blob(*items: Any) -> str:
    return " ".join(json.dumps(item, ensure_ascii=False, sort_keys=True) for item in items).lower()


def find_first(names: set[str], suffix: str) -> str | None:
    for name in sorted(names):
        if name.endswith(suffix):
            return name
    return None


def find_report_zip(evidence: dict[str, Any]) -> Path | None:
    for item in evidence.get("downloads") or []:
        if item.get("requirement") == "report package zip" and item.get("path"):
            return Path(str(item["path"]))
    return None


def has_any_key(payload: Any, keys: set[str]) -> bool:
    if isinstance(payload, dict):
        if keys.intersection(payload.keys()):
            return True
        return any(has_any_key(value, keys) for value in payload.values())
    if isinstance(payload, list):
        return any(has_any_key(value, keys) for value in payload)
    return False


def main() -> int:
    failures: list[str] = []
    warnings: list[str] = []
    evidence = json.loads(EDF_UI_EVIDENCE.read_text(encoding="utf-8"))
    report_zip = find_report_zip(evidence)

    if evidence.get("status") != "passed":
        failures.append("EDF UI-only evidence is not passed")
    if report_zip is None or not report_zip.exists():
        failures.append("report package zip is missing")

    checks: dict[str, Any] = {}
    report_entries: dict[str, Any] = {}

    if not failures and report_zip is not None:
        with zipfile.ZipFile(report_zip) as zf:
            names = {name.replace("\\", "/") for name in zf.namelist()}
            report_entries = {
                "qc_entries": sorted(name for name in names if name.startswith("qc/")),
                "bad_channel_entries": sorted(name for name in names if name.startswith("quality/bad_channel_audit/")),
                "analysis_reproducibility_entries": sorted(name for name in names if "/reproducibility/" in name),
                "ica_entries": sorted(name for name in names if "ica" in name.lower()),
                "epoch_named_entries": sorted(name for name in names if "epoch" in name.lower()),
            }

            qc_params_name = "qc/qc_waveform_preview/parameters.json"
            qc_workflow_name = "qc/qc_waveform_preview/workflow.json"
            qc_filter_preview_name = "qc/qc_waveform_preview/filter_preview.json"
            qc_result_name = "qc/qc_waveform_preview/result.json"
            metadata_summary_name = "qc/metadata_qc/qc_summary.json"
            data_prep_ref_name = "artifacts/data_preparation_task_reference.json"
            erp_params_name = find_first(names, "/reproducibility/parameters.json")
            erp_drop_log_name = find_first(names, "/reproducibility/drop_log_summary.json")
            erp_summary_name = find_first(names, "/reproducibility/erp_summary.json")

            required_preprocessing = {
                "qc_waveform_parameters_present": qc_params_name,
                "qc_waveform_workflow_present": qc_workflow_name,
                "qc_filter_preview_present": qc_filter_preview_name,
                "metadata_qc_summary_present": metadata_summary_name,
                "data_preparation_reference_present": data_prep_ref_name,
            }
            for label, name in required_preprocessing.items():
                checks[label] = status(name in names, name)

            if all(name in names for name in required_preprocessing.values()):
                qc_params = load_json_from_zip(zf, qc_params_name)
                qc_workflow = load_json_from_zip(zf, qc_workflow_name)
                qc_filter_preview = load_json_from_zip(zf, qc_filter_preview_name)
                metadata_summary = load_json_from_zip(zf, metadata_summary_name)
                data_prep_ref = load_json_from_zip(zf, data_prep_ref_name)
                qc_result = load_json_from_zip(zf, qc_result_name) if qc_result_name in names else {}
                combined = text_blob(qc_params, qc_workflow, qc_filter_preview, metadata_summary, data_prep_ref, qc_result)
                filter_defaults = (qc_params.get("defaults") or {}).get("filter_preview") or {}
                bandpass = filter_defaults.get("bandpass") or {}
                notch = filter_defaults.get("notch") or {}
                workflow_steps = [str(step.get("name", "")).lower() for step in qc_workflow.get("steps") or []]
                metadata = metadata_summary.get("metadata") or {}
                task_params = data_prep_ref.get("parameters_json") or {}

                checks.update(
                    {
                        "VR-EO-0020_filter_low_high_notch_present": status(
                            bandpass.get("l_freq") is not None
                            and bandpass.get("h_freq") is not None
                            and notch.get("freqs") is not None,
                            {"bandpass": bandpass, "notch": notch},
                        ),
                        "VR-EO-0020_filter_design_and_scope_present": status(
                            bool(bandpass.get("method"))
                            and bool(notch.get("method"))
                            and filter_defaults.get("apply_to") == "preview_window_only"
                            and qc_params.get("preview_only_filtering") is True,
                            {
                                "bandpass_method": bandpass.get("method"),
                                "notch_method": notch.get("method"),
                                "apply_to": filter_defaults.get("apply_to"),
                                "preview_only_filtering": qc_params.get("preview_only_filtering"),
                            },
                        ),
                        "VR-EO-0020_original_sampling_rate_present": status(
                            metadata.get("sampling_rate") is not None,
                            metadata.get("sampling_rate"),
                        ),
                        "VR-EO-0020_resampling_policy_present": status(
                            "resample" in combined or "resampling" in combined or "new_sampling_rate" in combined,
                            "expected explicit no-resampling or original/new sampling-rate policy",
                        ),
                        "VR-EO-0020_reference_policy_present": status(
                            "reference" in combined and bool(task_params.get("data_preparation_plan_id")),
                            {
                                "data_preparation_plan_id": task_params.get("data_preparation_plan_id"),
                                "reference_mentions": "reference" in combined,
                            },
                        ),
                        "VR-EO-0020_provenance_present": status(
                            bool(task_params.get("data_preparation_plan_id"))
                            and task_params.get("data_preparation_revision") is not None
                            and bool(task_params.get("data_preparation_contract_version")),
                            task_params,
                        ),
                        "VR-EO-0020_warnings_or_boundary_present": status(
                            "warning" in combined
                            or "non-diagnostic" in combined
                            or "not for clinical diagnosis" in combined
                            or "research preprocessing preview only" in combined,
                            "warning/boundary scan over QC and data-preparation artifacts",
                        ),
                        "VR-EO-0020_workflow_records_preprocessing_steps": status(
                            "read_raw" in workflow_steps
                            and "select_preview_window" in workflow_steps
                            and "optional_filter_preview" in workflow_steps,
                            workflow_steps,
                        ),
                    }
                )

            ica_entries = report_entries["ica_entries"]
            ica_payloads = []
            for name in ica_entries:
                if name.lower().endswith(".json"):
                    try:
                        ica_payloads.append(load_json_from_zip(zf, name))
                    except (KeyError, json.JSONDecodeError):
                        pass
            ica_text = text_blob(ica_entries, ica_payloads)
            checks.update(
                {
                    "VR-EO-0021_ica_artifact_namespace_present": status(
                        bool(ica_entries),
                        ica_entries or "expected ICA audit artifact namespace",
                    ),
                    "VR-EO-0021_removed_components_recorded": status(
                        "removed_components" in ica_text or "kept_components" in ica_text,
                        ica_payloads or "expected removed/kept ICA component records",
                    ),
                    "VR-EO-0021_component_reason_score_label_present": status(
                        all(token in ica_text for token in ("component", "reason", "score", "label")),
                        ica_payloads or "expected ICA reason/score/label evidence",
                    ),
                    "VR-EO-0021_before_after_provenance_present": status(
                        all(token in ica_text for token in ("before", "after", "provenance")),
                        ica_payloads or "expected before/after ICA provenance",
                    ),
                    "VR-EO-0021_no_brain_source_claim_in_ica": status(
                        "source localization" not in ica_text
                        and "brain source" not in ica_text
                        and "brain region activation" not in ica_text,
                        "ICA artifact boundary scan",
                    ),
                }
            )

            if erp_drop_log_name and erp_summary_name and erp_params_name:
                drop_log = load_json_from_zip(zf, erp_drop_log_name)
                erp_summary = load_json_from_zip(zf, erp_summary_name)
                erp_params = load_json_from_zip(zf, erp_params_name)
                params = erp_params.get("parameters") or {}
                combined_epoch = text_blob(drop_log, erp_summary, erp_params)
                per_condition_counts = erp_summary.get("per_condition_epoch_counts") or {
                    key: value.get("n_epochs")
                    for key, value in (erp_summary.get("conditions") or {}).items()
                    if isinstance(value, dict) and value.get("n_epochs") is not None
                }
                checks.update(
                    {
                        "VR-EO-0022_epoch_window_present": status(
                            params.get("tmin") is not None and params.get("tmax") is not None,
                            {"tmin": params.get("tmin"), "tmax": params.get("tmax")},
                        ),
                        "VR-EO-0022_baseline_present": status(
                            "baseline" in params and params.get("baseline") is not None,
                            params.get("baseline"),
                        ),
                        "VR-EO-0022_reject_by_annotation_present": status(
                            "reject_by_annotation" in erp_summary,
                            erp_summary.get("reject_by_annotation"),
                        ),
                        "VR-EO-0022_initial_final_epoch_counts_present": status(
                            drop_log.get("total_input_events") is not None
                            and drop_log.get("kept_epochs") is not None
                            and drop_log.get("dropped_epochs") is not None,
                            drop_log,
                        ),
                        "VR-EO-0022_per_condition_remaining_counts_present": status(
                            bool(per_condition_counts),
                            per_condition_counts,
                        ),
                        "VR-EO-0022_drop_reasons_present": status(
                            bool(drop_log.get("reasons"))
                            or (
                                drop_log.get("dropped_epochs") == 0
                                and isinstance(drop_log.get("reasons"), dict)
                                and "epoch_rejection_policy" in drop_log
                            ),
                            {
                                "reasons": drop_log.get("reasons"),
                                "dropped_epochs": drop_log.get("dropped_epochs"),
                                "none_policy": drop_log.get("epoch_rejection_policy"),
                            },
                        ),
                        "VR-EO-0022_bad_spans_or_breaks_present": status(
                            "bad span" in combined_epoch
                            or "bad_spans" in combined_epoch
                            or "break" in combined_epoch,
                            "expected bad spans/break artifact or explicit none policy",
                        ),
                        "VR-EO-0022_rejection_thresholds_present": status(
                            has_any_key(params, {"reject", "reject_thresholds", "rejection_thresholds", "flat", "amplitude_threshold"})
                            or has_any_key(erp_summary, {"reject", "reject_thresholds", "rejection_thresholds", "flat", "amplitude_threshold"}),
                            "expected epoch rejection threshold fields or explicit none policy",
                        ),
                        "VR-EO-0022_imbalance_or_over_rejection_warning_present": status(
                            "warning" in combined_epoch
                            or "imbalance" in combined_epoch
                            or "over" in combined_epoch,
                            "expected over-rejection/condition-balance warning or explicit none policy",
                        ),
                    }
                )
            else:
                checks.update(
                    {
                        "VR-EO-0022_drop_log_summary_present": status(False, erp_drop_log_name),
                        "VR-EO-0022_erp_summary_present": status(False, erp_summary_name),
                        "VR-EO-0022_erp_parameters_present": status(False, erp_params_name),
                    }
                )

    blockers = [key for key, item in checks.items() if isinstance(item, dict) and item.get("status") == "block"]
    failures.extend(blockers)
    result = {
        "schema_version": "qlanalyser-round007-real-report-consumption-v0.1",
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "passed" if not failures else "failed",
        "requirement_ids": ["VR-EO-0020", "VR-EO-0021", "VR-EO-0022"],
        "scope": "real UI-only report ZIP consumption for preprocessing parameters, ICA audit, and epoch rejection summary",
        "important_boundary": "This is artifact consumption evidence only; not release pass, clinical/diagnostic approval, or scientific/statistical interpretation approval.",
        "ui_evidence_path": str(EDF_UI_EVIDENCE),
        "report_zip_path": str(report_zip) if report_zip else None,
        "report_entries": report_entries,
        "checks": checks,
        "blockers": failures,
        "warnings": warnings,
        "what_07_can_consume_next": [
            "Use this as the real-report counterpart to round_007 VR-EO-0020/0021/0022.",
            "For VR-EO-0020, add explicit resampling policy and original/new reference metadata to exported preprocessing artifacts.",
            "For VR-EO-0021, add an ICA audit artifact namespace only when ICA cleaning is actually available; otherwise export an explicit not-run/not-applicable boundary artifact.",
            "For VR-EO-0022, add bad-span/break policy, rejection thresholds, and over-rejection or condition-balance warnings to epoch artifacts.",
            "Do not use this checker as a release-pass or scientific interpretation decision.",
        ],
        "07A_SHORT_PACKET_METRICS": {
            "mini/script packet count": 2,
            "script packet used": "ZIP inventory packet plus round_007 real report consumption checker",
            "GPT-5.5 low-value work avoided": "ZIP entry inventory, JSON field presence checks, and blocker normalization are scripted",
            "concurrency frontier": "single deterministic checker over latest UI-only report ZIP; no broad worker fan-out",
            "long-term platform asset produced": "real artifact-consumption checker for preprocessing/ICA/epoch-rejection review gates",
            "owner boundary respected": "yes",
            "handoff target": "07 main owner",
        },
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
