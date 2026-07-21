# QLanalyser Lab-to-Main Workflow Gate

Updated: 2026-06-19

Owner: C0 product and architecture center

Status: product gate for every analysis lab before main-flow promotion

## 1. Principle

QLanalyser develops analysis capabilities in labs first.

```text
lab design
-> real-data lab workstation
-> internal/customer trial
-> scientific validation
-> capacity/cost/permission validation
-> report/artifact validation
-> C0/C4/C5 acceptance
-> main workflow promotion
```

A lab is not a static feature page. A promoted lab must operate on real backend data and produce reproducible outputs.

## 2. Main customer workflow

The main workflow must remain simple:

```text
Project
-> Data File
-> Data Preparation
-> Analysis Task
-> Result Review
-> Report Delivery
```

The main path should use customer task language:

- create project;
- upload/select EEG file;
- check data quality;
- confirm preparation plan;
- run PSD/ERP;
- review results;
- download report package.

Avoid customer-visible internal language:

- local backend;
- demo API;
- registry;
- task runner debug;
- module dev;
- raw JSON as the default view;
- MNE internals unless inside expert details.

## 3. Common preprocessing vs module-specific preprocessing

### Common data preparation belongs to QC/Data Preparation

QC/Data Preparation owns:

- metadata review;
- sampling rate and channel summary;
- channel type review;
- montage/reference decisions when common;
- bad channel marking;
- bad segment marking;
- annotation action decisions;
- preview-only filter/notch exploration;
- saved preview evidence segments;
- `data_preparation_plan` save/restore/confirm.

### Module-specific choices belong to each module

PSD owns:

- Welch/multitaper method choice;
- frequency range;
- band definitions;
- absolute/relative power;
- channel/group aggregation.

ERP owns:

- event mapping;
- epoch window;
- baseline;
- reject/drop rules;
- ROI/channel/component windows;
- condition comparison.

TFR owns:

- time-frequency method;
- frequencies and cycles;
- baseline correction;
- event/epoch design;
- ERSP/ITC outputs.

PAC owns:

- phase/amplitude bands;
- coupling metric;
- surrogate/null strategy;
- artifact and non-sinusoidal waveform warnings.

Connectivity owns:

- connectivity metric;
- reference/source/sensor caveats;
- frequency/time window;
- volume conduction controls;
- null/reference validation.

## 4. Promotion gates

| Gate | Required evidence | Owner |
| --- | --- | --- |
| Real data service | Lab uses backend APIs and real uploaded/selected EEG files | Module owner |
| Workflow fit | Lab starts from current project/file/plan context | C0/C1 |
| Scientific validation | Synthetic/reference tests cover expected signal and failure cases | C3/C5 |
| Capacity validation | Large-file and 10-user/queued-task behavior accepted | C1/C5 |
| Permission/quota/storage | Object ownership, audit, quota, storage tier hooks exist | C1/C5 |
| Result evidence | Results show input file, plan revision, parameters, limitations | C3/C4 |
| Report package | Artifacts and reproducibility files are downloadable | C3/C5 |
| UI clarity | Beginner view has one primary next action and no internal wording | C4 |

No lab may enter the main flow if any P0 gate fails.

## 5. V1 lab statuses

| Lab | V1 status | Main-flow rule |
| --- | --- | --- |
| QC/Data Preparation | stable target | Required gate before PSD/ERP |
| PSD | stable target | Allowed after confirmed plan |
| ERP | conditional target | Allowed only when event semantics are confirmed and plan parity exists |
| Report | stable target | Allowed only from completed task outputs |
| TFR | preview | Lab/roadmap only |
| PAC | preview | Lab/roadmap only |
| Connectivity | preview | Lab/roadmap only |

## 6. Beginner-friendly UI rules

Every stage must answer:

1. What am I doing now?
2. Why does it matter for EEG analysis?
3. What decision must I make?
4. What can go wrong?
5. What is the next safe action?

Default UI:

- short plain-language summary;
- one primary action;
- state badge;
- simple warnings;
- expert details collapsed.

Expert details:

- MNE function names;
- parameter JSON;
- artifact paths;
- software versions;
- method details.

## 7. Result-page evidence rule

Every promoted analysis result page must display:

- project;
- EEG file;
- task id;
- task status;
- analysis method;
- data preparation plan id/revision if used;
- key parameters;
- applied bad channels/segments;
- figures/tables generated from current task;
- method limitations;
- downloads.

Static sample results may appear only in lab/tutorial areas and must be labelled as examples.

## 8. C4 acceptance checklist

Before promotion, C4 must verify:

- no duplicate entry for the same user action;
- no customer-visible dev/internal wording;
- no stable promise for preview labs;
- no analysis action before required prior gate;
- failed states are actionable;
- report/download path is visible after task completion;
- screenshots or browser evidence exist.
