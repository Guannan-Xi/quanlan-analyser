# QLanalyser Waveform Scoring Workbench Research Input

Date: 2026-06-29
Status: research input before six-pack specification
Scope: epilepsy event review, sleep staging, human PSG event scoring, animal/preclinical workflows, 1-64 channel waveform review

## 1. Purpose

This document consolidates the current research basis before creating the six-document specification pack:

1. Requirements / PRD
2. Architecture Design
3. Detailed Design
4. Data / API / Artifact Contract
5. E2E Test Plan
6. Release Plan

The goal is to prevent the epilepsy/sleep/PSG/animal waveform scoring module from drifting across chat, screenshots, quick fixes, and isolated page changes.

## 2. Sources Read Or Inspected

### Local QLanalyser / PC sources

- `D:\Quanlan\Codes\Python\AR_analyser1\AR_analyser_PC\src\QlassAnalysis.py`
- `D:\Quanlan\Codes\Python\AR_analyser1\AR_analyser_PC\src\QlassAnalysiscopy.py`
- `D:\Quanlan\Codes\Python\AR_analyser1\AR_analyser_PC\view\xxxAnalysis_main.ui`
- `D:\Quanlan\Codes\Python\AR_analyser1\AR_analyser_PC\view\Anesthesia_Analysis_main.ui`
- `D:\Quanlan\Codes\Python\quanlan-analyser-official\docs\product\qlanalyser_pc_sleep_module_source_review_20260629.md`
- `D:\Quanlan\Codes\Python\quanlan-analyser-official\docs\product\waveform_scoring_workbench_unified_design_20260629.md`

### Knowledge base sources

- `D:\QuanLanKnowledgeBase\learning-notes\qlanalyser\NEURAL_SIGNAL_BENCHMARK_DATASET_CARDS_20260621_CN.md`
- `D:\QuanLanKnowledgeBase\learning-notes\qlanalyser\EEG_BIDS_PIPELINE_DATA_GOVERNANCE_CN.md`
- `D:\QuanLanKnowledgeBase\source-repos\neuro-methods\yasa\docs\changelog.rst`

### Web / public references

- AASM Scoring Manual learning page: `https://learn.aasm.org/Listing/The-AASM-Manual-for-the-Scoring-of-Sleep-and-Associated-Events-Series-2-1455`
- AASM ISR help page: `https://isr.aasm.org/helpv5/TheAASMManualfortheScoringofSlee.html`
- YASA SleepStaging documentation: `https://yasa-sleep.org/generated/yasa.SleepStaging.html`
- YASA eLife paper: `https://elifesciences.org/articles/70092`
- PhysioNet Sleep-EDF Expanded: `https://physionet.org/content/sleep-edfx/1.0.0/`
- PhysioNet polysomnogram resource index: `https://physionet.org/content/?topic=polysomnogram`
- MNE sleep stage classification tutorial: `https://mne.tools/stable/auto_tutorials/clinical/60_sleep.html`
- Rodent sleep scoring review / references discovered through search:
  - open-source rodent sleep staging platform: `https://pmc.ncbi.nlm.nih.gov/articles/PMC12263331/`
  - mouse sleep scoring / seizure classification paper: `https://www.eneuro.org/content/12/10/ENEURO.0226-25.2025`
  - mouse sleep stage scoring with 4-20 second epochs: `https://www.nature.com/articles/s41598-019-51269-8`
  - rodent scoring configuration example: `https://support.datasci.com/hc/en-us/articles/115008514908-Configuring-the-Rodent-Sleep-Scoring-2-Module`

## 3. Sources Partially Read Or Not Yet Incorporated

### Feishu PSG / sleep reference

User-provided link:

```text
https://quanland.feishu.cn/wiki/UevhwictEiaiOFk9tBCcatqqnge?from=from_copylink
```

Current status:

```text
partial_read_from_feishu_aasm_v3_reference
```

Earlier observed failure:

- wiki-node read failed because wiki space `7291178227287293955` is not in the current Feishu authorization whitelist.
- raw read failed because the doc/wiki target is not in the current Feishu authorization whitelist.

Latest working-thread update:

- A later raw read exposed chapter-level content from the internal Feishu AASM V3 reference.
- The readable content covers PSG/HSAT scope, report parameters, technical/digital specifications, sleep staging, arousal, cardiac, movement, respiratory events, and terminology.
- The six-pack may incorporate chapter-level concepts, event-layer categories, and schema/test/release implications.

Rule for future documents:

- Do not copy full rule text or controlled translated content into public/customer-facing docs.
- Do not claim full AASM V3 rule-level scoring until the internal source is fully extracted, QA-reviewed, and authorized for product use.
- Use `partial_read_from_feishu_aasm_v3_reference` for current architecture-level incorporation.

## 4. Research Conclusions

## 4.1 The product should be a scoring workbench, not isolated analysis pages

The recurring product chain should be:

```text
Data Preparation
-> Analysis Task
-> Embedded Scoring Workbench
-> Manual Correction / Review Revision
-> Results
```

The workbench must stay inside the QLanalyser main navigation frame. It should not become a separate upload page or mini-app.

## 4.2 One timeline state must drive all evidence panels

The central state should include:

```json
{
  "window_start_sec": 0,
  "window_duration_sec": 30,
  "selected_event_id": null,
  "selected_epoch_indices": [],
  "domain": "epilepsy_event | sleep_staging | human_psg | animal_preclinical"
}
```

Waveform, spectrogram, hypnogram/stage strip, respiratory-event strip, candidate table, and correction panel must subscribe to this same state.

No panel should keep an independent hidden time range.

## 4.3 Human PSG is broader than sleep staging

The public AASM sources describe the scoring manual as covering:

- sleep stages;
- arousals;
- respiratory events;
- movements during sleep;
- cardiac events;
- standard montages, electrode placements, and digitization parameters;
- PSG and HSAT evaluation.

Therefore, human PSG support cannot be modeled as only:

```text
Wake / N1 / N2 / N3 / REM
```

It must support interval event layers such as:

- apnea;
- hypopnea;
- RERA or related respiratory events, if in scope;
- oxygen desaturation;
- arousal;
- movement;
- snoring;
- body position;
- cardiac event annotations, if in scope.

## 4.4 Sleep stage labels and event labels are different data types

Sleep staging is usually epoch-level:

```text
epoch 100 = N2
```

Respiratory and many PSG events are interval-level:

```text
hypopnea: 123.4s -> 138.6s
oxygen desaturation: 128.0s -> 150.0s
```

The architecture must separate:

- `StageSchema`
- `EventSchema`
- `RespiratoryEventSchema`
- `ArousalEventSchema`
- `MovementEventSchema`
- `OxygenEventSchema`
- `ChannelRoleSchema`

These should not be collapsed into a single `Stage_Code` array.

## 4.5 Human and animal sleep scoring differ

Human sleep commonly uses W/N1/N2/N3/REM with 30-second epochs in many PSG workflows.

YASA uses an MNE Raw input and supports central EEG plus optional EOG and EMG channels; its documentation and paper describe automatic sleep staging over PSG data using LightGBM/antropy and common 30-second PSG epoch assumptions.

Rodent sleep scoring commonly uses fewer major states:

```text
Wake / NREM / REM
```

Rodent work often uses shorter epochs, commonly in the 4-20 second range depending on lab and model. QLanalyser-PC currently uses a 4-second default in the sleep module lineage.

Therefore, the platform must not hardcode one global sleep profile.

## 4.6 Animal/preclinical workflows need species and experiment profiles

The requirement "compatible with any animal" should be interpreted as:

```text
The platform supports configurable species/profile/channel/label schemas.
Specific species algorithms and scoring validity require separate validation.
```

Minimum profile fields:

```json
{
  "species": "human | mouse | rat | dog | monkey | custom",
  "domain": "sleep_staging | epilepsy_event | human_psg | animal_preclinical",
  "epoch_length_sec": 4,
  "channel_count": 1,
  "label_schema_id": "sleep_rodent_v1",
  "event_schema_id": "epilepsy_rodent_racine_v1",
  "model_id": "optional"
}
```

## 4.7 1-64 channel support must be an architecture requirement

The workbench must support:

- 1 to 64 channels;
- channel roles, not only raw channel names;
- visible channel subsets;
- channel grouping;
- per-channel gain;
- bad-channel states;
- event-related channel highlighting;
- rendering strategies that do not draw all 64 channels naively in every viewport.

Channel roles may include:

- EEG;
- EOG;
- EMG;
- ECG;
- airflow;
- respiratory effort;
- SpO2;
- snore/audio-derived event stream;
- body position;
- ACC/motion;
- temperature;
- custom auxiliary signal.

## 4.8 Epilepsy event review is different from diagnosis

The workbench should use non-medical research-support language:

- candidate event;
- automated screening;
- review support;
- manual correction;
- artifact;
- needs review.

It must not claim:

- diagnosis;
- confirmed clinical seizure;
- treatment recommendation;
- clinical triage.

Source algorithm output must remain read-only. Manual correction should be saved as review draft/revision and then published to Results.

## 4.9 Spectrogram is a synchronized evidence layer

The QLanalyser-PC sleep module uses STFT-style spectrogram evidence:

- STFT;
- log power;
- frequency range around 0.5-50 Hz in the inspected PC module;
- robust color range such as percentile scaling.

For the Web workbench, spectrogram should be a synchronized review evidence layer, not a substitute for formal TFR / PSD / Band Power modules.

## 5. Proposed Domain Model

```text
ScoringWorkbench
  ScoringProfile
  ChannelManager
  TimelineState
  EvidencePanels
    WaveformPanel
    SpectrogramPanel
    StageStripPanel
    EventStripPanel
    OptionalAuxiliaryPanels
  ReviewSession
    ReviewAction[]
    UndoStack
    RedoStack
    ReviewRevision
  ResultsPublisher
```

## 6. Proposed Release Planning Direction

### P0: Epilepsy event review closed loop

Goal:

```text
Data Preparation -> Epilepsy Workbench -> automated candidate events -> waveform/spectrogram/event sync -> manual correction -> Results
```

Includes:

- main-system child page;
- waveform-first entry;
- epilepsy candidate event task;
- candidate list;
- synchronized spectrogram evidence;
- event strip;
- confirm / reject / artifact / adjust event;
- Undo/Redo;
- publish to Results.

Excludes:

- full human PSG respiratory scoring;
- full animal species profile library;
- high-performance 64-channel stress optimization beyond initial safeguards.

### P1: Basic sleep staging workbench

Includes:

- sleep domain shell;
- Wake/NREM/REM for rodent-style scoring or W/N1/N2/N3/REM where human profile applies;
- hypnogram;
- epoch selection;
- manual stage correction;
- sleep stage summary;
- publish to Results.

Requires:

- explicit profile selection;
- epoch length configuration.

### P2: Human PSG / HSAT event scoring foundation

Includes:

- PSG channel roles;
- stage schema and interval event schemas;
- respiratory-event layer;
- arousal/movement/oxygen event layer foundations;
- AHI/ODI/TST/sleep efficiency style output structures if validated;
- Feishu AASM V3/internal spec chapter-level concepts incorporated; exact rule-level extraction remains controlled.

### P3: Animal/preclinical profile system

Includes:

- species profiles;
- rodent sleep and epilepsy event schemas;
- Racine / modified Racine severity scoring if required;
- animal ID / group / treatment / light-cycle metadata;
- experiment-level statistics.

### P4: 1-64 channel performance and scale

Includes:

- channel virtualization;
- min-max chunk rendering;
- spectrogram tile/cache;
- large file regression;
- multi-channel event localization;
- batch/session workflows.

## 7. Six-Pack Documents To Create Next

```text
docs/product/qlanalyser_waveform_scoring_workbench_requirements_20260629.md
docs/product/qlanalyser_waveform_scoring_workbench_architecture_20260629.md
docs/product/qlanalyser_waveform_scoring_workbench_detailed_design_20260629.md
docs/product/qlanalyser_waveform_scoring_workbench_data_api_contract_20260629.md
docs/product/qlanalyser_waveform_scoring_workbench_e2e_test_plan_20260629.md
docs/product/qlanalyser_waveform_scoring_workbench_release_plan_20260629.md
```

## 8. Current Sufficiency Assessment

### Sufficient for P0 epilepsy architecture

The current research is sufficient to design the epilepsy event review closed loop at P0.

### Mostly sufficient for basic sleep staging architecture

The current research is sufficient for a basic configurable sleep staging workbench, as long as the design does not claim full human PSG respiratory scoring.

### Not yet sufficient for full human PSG scoring

Human PSG event scoring now has enough internal-source support for architecture-level event categories and schema planning. Full release-grade AASM V3 scoring still needs full rule-level extraction, QA review, authorized citation handling, and fixture-based threshold tests.

### Not yet sufficient for "any animal" algorithm claims

Architecture can support configurable animal profiles, but algorithm validity and scoring rules must be added per species/model with separate validation.


## 9. Change Log

- 2026-06-29: Created research input for waveform scoring workbench six-pack.
- 2026-06-29: Updated Feishu AASM V3 status from authorization-blocked to partial source read; incorporated PSG/HSAT chapter-level concepts while keeping full rule-level scoring gated by QA and authorization.

