# QLanalyser Analysis Module Contract

Date: 2026-06-20
Scope: research EEG analysis modules and CRO-style delivery evidence.

This is the standard contract for adding or promoting an EEG analysis method in
QLanalyser. It exists to keep the product modular, reproducible, auditable, and
aligned with the non-medical research/CRO goal.

## Product Boundary

Every module must stay within this category:

```text
Research EEG analysis tool + CRO infrastructure, not medical software.
```

Forbidden claims:

- Clinical diagnosis.
- Treatment advice.
- Medical device status.
- Clinical decision support.
- Unsupported CRO/GxP/regulatory certification.

## Module Lifecycle

```text
draft -> internal_validation -> beta -> stable -> deprecated
```

Lifecycle rules:

- `draft`: design only; no customer promise.
- `internal_validation`: executable internally; no paid workflow exposure.
- `beta`: customer-visible only with explicit limitations and evidence.
- `stable`: allowed in the paid workflow and reports.
- `deprecated`: hidden from new work; old outputs remain auditable.

Only `stable` modules may appear as default paid-workflow actions. `beta`
modules may appear in the analysis lab with visible limitations. `preview`
content is not a lifecycle state for production; use `draft` or `beta`.

## Required Module Specification

Each module must define these fields before implementation:

```yaml
module_id: stable_ascii_identifier
display_name:
scientific_purpose:
lifecycle_state: draft|internal_validation|beta|stable|deprecated
owner:
version:
non_medical_boundary:
input_requirements:
  file_formats:
  required_metadata:
  required_events:
  channel_requirements:
  sampling_rate_requirements:
  duration_requirements:
  preprocessing_prerequisites:
parameters_schema:
  type: object
  required: []
  properties: {}
execution_contract:
  api_endpoint: /api/tasks
  task_module:
  runner:
  expected_runtime_class:
  failure_modes:
output_schema:
  result_json:
  tables:
  figures:
  reproducibility_files:
artifact_manifest:
  required_fields:
    - artifact_id
    - task_id
    - module_id
    - input_file_id
    - parameters_hash
    - software_versions
    - sha256
    - created_at
report_mapping:
  summary_sections:
  table_sections:
  figure_sections:
  limitations_section:
acceptance_gates:
  unit:
  api:
  browser:
  report_zip:
  evidence_matrix:
customer_copy_gate:
  deepseek_official_direct_required: true
```

## Input Requirements

A module must reject unsupported inputs before it creates misleading outputs.
The rejection must be visible to the API, UI, report evidence, and audit trail.

Minimum input checks:

- File can be read by the supported EEG reader.
- At least one usable EEG channel exists.
- Required metadata is present or explicitly marked unknown.
- Required event markers exist for event-based methods.
- Sampling rate is valid for the requested frequency/time range.
- Preprocessing prerequisites are satisfied or documented as intentionally not
  applied.

## Parameter Schema

Parameters must be explicit, typed, bounded, and serializable. Defaults must be
scientifically defensible and visible in reproducibility outputs.

Required parameter evidence:

- Raw submitted parameters.
- Normalized parameters after defaults and validation.
- Parameter hash.
- Parameter schema version.
- Project/template override source when applicable.

## Execution Contract

All stable modules must run through the task contract:

```text
UI action -> POST /api/tasks -> task_service -> module runner -> artifacts -> report ZIP
```

## Total Workflow Integration Contract

QLanalyser's module system is not a collection of isolated side pages. New or
optimized analysis methods must enter the total analysis workflow framework when
they mature.

Required integration path:

```text
method design packet
-> module contract
-> workflow template
-> task schema
-> task_service routing
-> artifact manifest
-> report mapping
-> release evidence matrix
```

Integration rules:

- Lab and beta pages may be used to validate a method, but they are temporary
  proving grounds, not the long-term product home for stable methods.
- A method cannot be promoted to `stable` unless it has a `workflow_id` and is
  reachable from the main customer analysis flow or a governed preset workflow.
- Optimizing an existing method must preserve prior task/report auditability and
  must record the method version, parameter schema version, and artifact schema
  version.
- Every workflow template must declare lifecycle state, allowed input class,
  required preprocessing state, output artifacts, report sections, and acceptance
  evidence.
- A customer-visible method must not bypass `/api/tasks`, task status, artifact
  registry, report ZIP, quota/audit accounting, or non-medical boundary checks.
- Experimental methods may stay in the lab only while labeled `draft`,
  `internal_validation`, or `beta`; once stable, they must be mounted into the
  total workflow framework.

The task record must preserve:

- `account_id`
- `project_id`
- `input_file_id`
- `module_id`
- `workflow_id`
- `parameters`
- `normalized_parameters`
- `software_versions`
- `status`
- `started_at`
- `completed_at`
- `artifact_count`
- `error_code` and `error_message` when failed

## Output and Artifact Contract

Each successful run must write:

- `result.json`
- `manifest.json`
- `log.txt`
- `reproducibility/parameters.json`
- `reproducibility/software_versions.json`
- `reproducibility/method_description.txt`
- Method-specific tables and figures.

Every artifact must be downloadable through the product or included in the
report package when appropriate.

## Report Mapping

Every stable module must map outputs into the report package:

- Customer-readable summary.
- Method and parameter section.
- Result tables and figures.
- Limitations and interpretation boundary.
- Artifact manifest with hashes.

Report language must not imply medical diagnosis or treatment.

## Acceptance Gates

A module cannot become `stable` unless all gates pass:

- Unit or core runner test.
- API task creation and artifact listing.
- Browser path when customer-visible.
- Report ZIP inclusion.
- Evidence matrix entry.
- Page visual QA if it adds or changes UI.
- DeepSeek official-direct copy gate for customer-visible Chinese copy.

For V1 stable modules, the minimum stable set is:

- `qc`
- `preprocessing_readiness`
- `psd_bandpower`
- `erp_p300`

For V1 beta/lab modules:

- `tfr_ersp_itc`
- `multitaper_psd_tfr`
- `pac_cfc`
- `qc_preview_extensions`

Not stable until stronger evidence:

- `connectivity`
- `source_localization`
- `ai_interpretation`

## C0 Review Checklist

Before accepting a module packet, C0 must verify:

- The module serves research EEG/CRO delivery, not generic SaaS or medical use.
- Lifecycle state matches evidence.
- Inputs and parameters are schema-backed.
- Output schema and report mapping exist.
- The backend runner produces real artifacts.
- The frontend does not present preview content as stable.
- The evidence matrix proves the claimed state.
- Rollback leaves prior reports auditable.
