# QLanalyser Waveform Scoring Workbench AASM V3 Feishu Source Extract

Date: 20260629
Status: internal source extract, partial source read incorporated at chapter / architecture / contract level
Scope: human PSG, HSAT, sleep staging, arousal, respiratory, movement, cardiac, technical recording, and report-parameter implications for QLanalyser Waveform Scoring Workbench

## 1. Source

User-provided internal Feishu wiki:

```text
https://quanland.feishu.cn/wiki/UevhwictEiaiOFk9tBCcatqqnge?from=from_copylink
```

Public cross-check:

```text
https://shop.aasm.org/products/aasm-scoring-manual-3-ebook
```

Observed title:

```text
AASM sleep staging and associated event scoring manual, V3.0 Chinese internal reference
```

The source references the AASM Manual for the Scoring of Sleep and Associated Events, Version 3.0. AASM's public shop page confirms that Version 3 covers PSG and HSAT scoring, including sleep stages, arousals, respiratory events, movement events, cardiac events, montages, electrode placement, and digital parameters; it also states that AASM-accredited facilities were required to implement Version 3 by 2023-12-31.

## 2. Read Status

Status:

```text
partial_read_from_feishu_aasm_v3_reference
```

Incorporation level:

- chapter-level product scope: incorporated;
- event-layer architecture: incorporated;
- data/API schema categories: incorporated;
- E2E coverage categories: incorporated;
- exact rule thresholds and full translated rule text: controlled internal reference, not reproduced here.

Copyright and use boundary:

- Do not copy the manual or internal translation into external product docs.
- QLanalyser design documents may summarize architecture implications.
- Detailed scoring rule text and thresholds must stay behind authorized internal source access and QA review.

## 3. Chapter-Level Product Implications

The internal source indicates that human sleep work is broader than stage scoring. QLanalyser must treat PSG as a multi-layer scoring workflow:

- report parameters for PSG, MSLT, and MWT;
- digital recording, filtering, montage, and technical acquisition specifications;
- sleep staging;
- arousal scoring;
- cardiac event recording;
- movement event scoring;
- respiratory event scoring;
- HSAT-specific recording and report handling;
- terminology and rule grade governance.

## 4. Required PSG Event Layer Stack

The Waveform Scoring Workbench must reserve explicit layers for:

- Stage layer: epoch labels such as W, N1, N2, N3, REM, artifact or profile-specific alternatives.
- Arousal layer: interval events linked to EEG/physiology evidence, not stage labels.
- Respiratory layer: apnea, hypopnea, RERA, desaturation-linked events, and related interval annotations.
- Movement layer: limb/body/movement-related intervals or events.
- Cardiac layer: rate/rhythm/cardiac event annotations where signals and profile support them.
- Oxygen layer: SpO2 baseline, desaturation, nadir, recovery, and summary outputs.
- Position/snore/auxiliary layer: optional channels and intervals when recorded.
- HSAT layer: reduced-channel home sleep apnea test flow with different reporting constraints from full PSG.

## 5. Rule Governance Implications

QLanalyser must model rule metadata separately from UI labels:

```text
RuleGrade = RECOMMENDED | ACCEPTABLE | OPTIONAL | INTERNAL_PROFILE
```

Every scoring profile should be able to expose:

- source family, for example AASM V3, internal CRO profile, rodent profile, or custom protocol;
- rule grade;
- population or species scope;
- required and optional channels;
- event type;
- minimum required evidence fields;
- citation or internal reference pointer;
- profile version and lock state.

## 6. RERA And Respiratory Event Implications

RERA and respiratory events are interval events, not epoch stage labels. The contract must support:

- event start and end;
- duration;
- airflow or flow-limitation evidence;
- respiratory effort evidence when available;
- arousal association;
- oxygen desaturation association where the selected rule/profile uses it;
- adult / pediatric / study-profile scope;
- source rule grade and citation pointer.

The design documents should avoid freezing exact respiratory thresholds in public or customer-facing text until the internal reference, QA review, and target population scope are finalized.

## 7. What This Changes In The Six-Pack

The previous Feishu authorization blocker label is no longer accurate for the high-level product design. It should be replaced with:

```text
partial_read_from_feishu_aasm_v3_reference; chapter-level concepts and architecture categories incorporated; exact rule-level extraction remains controlled internal reference pending full QA review.
```

Release wording must distinguish:

- P2a: PSG architecture and event schemas;
- P2b: AASM V3 rule-aware scoring support behind authorized internal reference and QA;
- P2c: HSAT support.

## 8. Change Log

- 2026-06-29: Created partial source extract and incorporation guidance after internal Feishu AASM V3 content became readable in the working thread.
