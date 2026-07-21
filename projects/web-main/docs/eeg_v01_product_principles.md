# QLanalyser V01 EEG Product Principles

This document turns EEG domain knowledge into product, backend, report, and acceptance rules for QLanalyser V01.

V01 north star: turn non-standard, expert-dependent EEG analysis into a conservative, reproducible, easy-to-follow research workflow that teaches users while producing publication-grade evidence packages.

V01 is a research analysis platform, not a clinical diagnosis system.

## Scope

Stable in V01:

- Metadata review.
- QC and common data preparation plan.
- PSD with conservative Welch defaults.
- ERP/P300 from existing event markers.
- HTML report and ZIP package.
- Parameters, software versions, workflow records, manifests, and downloadable artifacts.

Beta or research workbench only:

- TFR.
- PAC.
- QC preview interactions.
- Exploratory method pages.

Out of V01 stable scope:

- Connectivity.
- Source localization.
- AI interpretation.
- Clinical diagnosis.
- Full BIDS workflow.
- Visual workflow builder.
- Payments and complex permission systems.

## Ten Professional Rules

1. Preconditions must be explicit.
   UI buttons must show why they are disabled. APIs must return machine-readable failure reasons. Reports must preserve blocked or warning states.

2. The stable path must be conservative.
   V01 exposes Metadata, QC, PSD, ERP/P300, and Report ZIP as the customer path. Advanced methods stay secondary until their prerequisites and limitations are fully represented.

3. Every output must be reproducible.
   Reports must include parameters, software versions, workflow descriptions, method text, manifests, result tables, and source task references.

4. ERP requires event markers and time alignment.
   If event markers are missing or ambiguous, ERP must block with a repair path rather than silently producing a weak result.

5. PSD is sensor-level spectral analysis unless proven otherwise.
   Topomaps must be described as scalp sensor-space distributions, not brain-region source results.

6. TFR and PAC require stronger teaching and limitation language.
   They may be useful, but in V01 they belong in Beta/research workbench surfaces, not stable customer conclusions.

7. Connectivity must not imply causality by default.
   Sensor-level connectivity is sensitive to method choices and volume conduction. It is outside stable V01 reporting.

8. Source localization requires anatomy, forward model, inverse method, and clear assumptions.
   V01 must not infer brain sources from scalp topomaps.

9. Metadata quality is a first-class product feature.
   Sampling rate, channel count, reference, channel labels, event count, duration, and file identity are part of the analytical evidence, not background detail.

10. The product must teach without clutter.
    Each page should explain what the user can trust, what the result can support, what it cannot support, and what to do next.

## UX Teaching Pattern

Each major page should follow this evidence ladder:

1. Data facts: file, channels, sampling rate, duration, event count.
2. Readiness: what is valid, missing, warned, or blocked.
3. Method parameters: only the parameters that affect the current result.
4. Result: figure, table, and concise interpretation.
5. Boundary: what the result does not prove.
6. Next action: continue, go back to QC, download report, or repair the input.

Disable states should answer three questions:

- What is missing?
- Why does it matter scientifically?
- Which action fixes it?

## Beauty And Trust Rules

- The interface should feel like a serious research instrument, not a marketing page.
- One screen should have one primary next action.
- Cards are for repeated items or tools, not nested page structure.
- Status colors must be consistent and restrained.
- Figure titles must state the signal level and method, for example `Sensor-level PSD - Welch`.
- Reports should lead with method, parameters, and evidence before interpretation.
- Do not use internal words such as demo, artifact, local API, pipeline, or production workflow in the customer path.
- Do not over-explain the product's own obvious function; QLanalyser users already know they are analyzing EEG.

## Backend And Report Implications

Every stable task should preserve:

- `project_id`
- `input_file_id`
- `module_name`
- `workflow_id`
- `parameters_json`
- `data_preparation_plan_id` when applicable
- `data_preparation_revision` when applicable
- `software_versions`
- `workflow`
- `method_description`
- `manifest`

Report packages should contain:

- Customer-readable HTML report.
- Tables.
- Figures.
- Parameters.
- Software versions.
- Workflow record.
- Method description.
- Result JSON.
- Manifest.
- Log.

## Acceptance Checklist

Stable V01 acceptance must verify:

- Customer demo link opens with the customer account path.
- Customer-visible UI contains no internal/demo/developer wording.
- The running backend exposes the normalized data-preparation routes.
- QC creates a confirmed data-preparation plan before PSD/ERP.
- PSD/ERP task payloads carry plan id and revision.
- ERP blocks or warns clearly when event markers are absent.
- Report HTML and ZIP are bound to the current report, not static demo assets.
- ZIP starts with `PK` and includes report, figures, tables, parameters, workflow, software versions, method text, manifest, and result JSON.
- Chinese customer copy has passed a direct DeepSeek review or records why the review was skipped.

## Source Map

Local references:

- `C:\Users\XGN\Documents\Codex\2026-06-19\new-chat-2\outputs\qlanalyser_department_packet_2026-06-20.md`
- `C:\Users\XGN\Documents\Codex\2026-06-19\new-chat-2\outputs\qlanalyser_department_learning_notes.md`
- `C:\Users\XGN\Documents\Codex\2026-06-19\new-chat-2\outputs\qlanalyser_ui_backend_design_spec.md`
- `D:\Quanlan\Codes\Python\quanlan-analyser-official\README.md`
- `D:\Quanlan\Codes\Python\quanlan-analyser-official\PRODUCT.md`
- `D:\Quanlan\Codes\Python\quanlan-analyser-official\docs\v01_production_readiness.md`

Official references:

- MNE-Python tutorials: https://mne.tools/stable/auto_tutorials/index.html
- MNE ERP tutorial: https://mne.tools/stable/auto_tutorials/evoked/30_eeg_erp.html
- MNE time-frequency tutorials: https://mne.tools/stable/auto_tutorials/time-freq/index.html
- MNE source localization tutorial: https://mne.tools/stable/auto_tutorials/inverse/30_mne_dspm_loreta.html
- MNE citation guidance: https://mne.tools/stable/documentation/cite.html
- MNE-BIDS: https://mne.tools/mne-bids/stable/index.html
- EEGLAB tutorials: https://eeglab.org/tutorials/
- EEGLAB references: https://eeglab.org/others/EEGLAB_References.html
- FieldTrip documentation: https://www.fieldtriptoolbox.org/documentation/
- FieldTrip tutorials: https://www.fieldtriptoolbox.org/tutorial/
- FieldTrip connectivity tutorial: https://www.fieldtriptoolbox.org/tutorial/connectivity/connectivity_sensor_source/
- Brainstorm tutorials: https://neuroimage.usc.edu/brainstorm/Tutorials
- Brainstorm source estimation: https://neuroimage.usc.edu/brainstorm/Tutorials/SourceEstimation
- BIDS EEG specification: https://bids-specification.readthedocs.io/en/stable/modality-specific-files/electroencephalography.html
- NWB: https://nwb.org/

## Anti-Overclaim Rules

- A topomap is not source localization.
- PSD does not identify brain sources.
- Connectivity is not causality unless the method and assumptions justify that claim.
- TFR/PAC should not appear as stable V01 conclusions.
- AI interpretation must not replace method evidence, statistical evidence, or limitations.
