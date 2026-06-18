# QLanalyser EEG V01 Production Readiness

## Scope

V01 is a production-oriented single-subject EEG analysis workflow. It is intentionally conservative: it runs only methods whose prerequisites can be checked in the local platform and fails clearly when those prerequisites are not met.

Enabled in V01:

1. Real EEG upload: EDF, BDF, EEGLAB SET, BrainVision VHDR, CNT, FIF.
2. Metadata extraction: sampling rate, channel count/types, duration, annotations, filtering info.
3. QC/preprocess summary: readable-file checks, format support, metadata readability, sampling-rate/duration thresholds, EEG channel presence, flat/extreme-amplitude channel checks.
4. Resting-state PSD: MNE Welch PSD and band-power tables.
5. ERP/P300: MNE annotations/events, epoching, baseline correction, evoked averages, N100/P200/P300 window metrics. ERP fails when valid events are absent.
6. Report package: HTML report, CSV/JSON/TXT outputs, parameters, method text, software versions, workflow JSON, ZIP download.

Deferred in V01:

- TFR / ERSP / ITC
- PAC / cross-frequency coupling
- Connectivity

These are visible only as planned capabilities because they require stricter epoch design, artifact controls, surrogate/statistical validation, reference/volume-conduction controls, and study-specific interpretation rules.

## Knowledge-base mapping

| Feishu EEG knowledge requirement | V01 implementation |
| --- | --- |
| Respect EEG signal structure: channels ? time, channel metadata/reference, events/markers, acquisition info | `eeg_core/io/readers.py` uses MNE readers; `eeg_core/io/metadata.py` extracts channel names/types, sampling rate, duration, annotations, high/low-pass metadata. |
| Marker validation is mandatory for ERP/TFR/PAC | `eeg_core/analysis/erp.py` derives events from annotations and raises a clear error when no events or requested event IDs are present. Advanced marker-dependent methods are disabled in V01. |
| QC before interpretation | `eeg_core/preprocess/quality.py` writes `qc_summary.json` and checks file, format, metadata, sampling rate, duration, EEG channel count, flat channels, and extreme amplitude channels. |
| PSD/band power are V01-safe with caveats | `eeg_core/analysis/psd.py` computes Welch PSD through MNE and writes band-power CSV, channel-band CSV, summary JSON, method text, parameters, software versions, and workflow. Reports include interpretation guardrails. |
| ERP requires event semantics | ERP output is generated only from annotations/events. No-event files fail with HTTP 422 and a task-level error. The report states marker semantics must be verified before interpretation. |
| Advanced methods need stricter preprocessing/statistics | `backend/services/task_service.py` rejects `tfr`, `pac`, and `connectivity` with a V01-not-enabled error instead of returning fake results. Frontend labels them as planned with prerequisites. |
| Reproducibility is mandatory | Each QC/PSD/ERP task writes `parameters.json`, `method_description.txt`, `software_versions.json`, and `workflow.json`. Report ZIP preserves `tables/`, `figures/`, and `reproducibility/`. |

## API acceptance smoke test

A TestClient smoke script was run with a synthetic MNE FIF file containing EEG channels and annotations:

- `POST /api/projects`
- `POST /api/eeg/upload`
- `GET /api/eeg/files/{file_id}/metadata`
- `POST /api/tasks` for `qc`, `psd`, `erp`
- `GET /api/tasks/{task_id}/artifacts`
- `POST /api/tasks` for `connectivity` expected HTTP 422 (V01 disabled)
- `POST /api/reports`
- `GET /api/artifacts/{artifact_id}/download`
- `GET /api/reports/{report_id}/package`

Observed smoke result:

```json
{
  "metadata_status": "readable",
  "tasks": ["qc", "psd", "erp"],
  "advanced_method_result": "HTTP 422, not enabled in V01",
  "report_package": "ZIP with reports/report.html, tables/band_power.csv, reproducibility/software_versions.json, reproducibility/workflow.json"
}
```

## Operational notes

- V01 now persists project, subject, EEG file, task, artifact, and report registries to `data/state/*.json` using a lightweight single-node JSON state store.
- A database-backed multi-user state layer and durable job queue remain V1.x hardening items.
- Worker wrappers are thin and call the same `eeg_core` functions as the API path, so Celery integration can be added without diverging analysis behavior.
- The frontend readiness panel and API readiness endpoint both expose the honest V01 boundary.
