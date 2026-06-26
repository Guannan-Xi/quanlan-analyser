# QLanalyser Current Project Status

Date: 2026-06-20

This is the clean current-status entry. `docs/PROJECT_STATUS.md` contains
legacy mojibake notes and should not be used as the source of truth for the
current product boundary.

## Long-Term Goal

The authoritative long-term roadmap is:

```text
docs\product\LONG_TERM_GOAL_AND_ONE_YEAR_ROADMAP.md
```

QLanalyser is being built into a globally top-tier research EEG analysis tool
and CRO infrastructure: standardized, modular, reproducible, auditable,
commercially operable, and ready to evolve toward CRO-grade workflows.

Hard boundary: QLanalyser is not medical software. It must not claim clinical
diagnosis, treatment advice, medical-device status, or clinical decision
support.

Every new requirement, MVP slice, milestone, commercial feature, backend
contract, and acceptance gate must serve research EEG analysis standardization,
CRO delivery, or paid scientific operations. Do not drift into generic SaaS or
medical clinical workflows.

## Current Phase 0 / V1 Target

V1 is the production-grade paid-pilot operating release. It must preserve:

- Real EEG upload.
- QC/preprocessing readiness.
- PSD and bandpower.
- ERP/P300.
- Analysis lab.
- Preset analysis workflows.
- Report ZIP download.
- Customer registration/login.
- Email, phone verification, and WeChat registration sandbox/operable boundary.
- Sandbox Alipay/WeChat Pay confirmation loop.
- Wallet, deduction, ledger, and orders.
- Customer invoice request.
- Admin invoice review and PDF upload.
- Customer inbox delivery for issued invoices.
- Admin operations console.
- Sanitized/security-redacted evidence.
- Aliyun deployment, rollback, and ops evidence.
- Analysis lab beta runners for TFR, PAC, Reference/CSD, Multitaper PSD/TFR, and Connectivity behind explicit gates.

Static screenshots or copy are not acceptable substitutes for executable EEG
analysis, billing, invoice, or admin workflows.

## Public Review Links

```text
Customer: http://39.97.248.225/?customer_demo=login&api=http://39.97.248.225/api
Lab:      http://39.97.248.225/module-lab.html?api=http://39.97.248.225/api
API:      http://39.97.248.225/api/health
```

Demo account:

```text
Customer: demo.customer@quanlan.cn / demo123456
Admin:    ops@quanlan.cn, via the top-right management entry
```

## Evidence Entry Points

```text
work\release_evidence\20260620-v01-acceptance\START_HERE_RELEASE_REVIEW.md
work\release_evidence\20260620-v01-public\PUBLIC_DEPLOYMENT_EVIDENCE.md
work\release_evidence\20260620-v01-acceptance\production_goal_requirement_matrix.md
work\release_evidence\20260620-v01-acceptance\release_gate_summary.md
docs\product\README.md
docs\product\page_change_log.md
docs\product\review_system_governance.md
docs\product\product_doc_governance.md
```

## Living Product Docs

The current product delivery working set is maintained in:

- `docs/product/README.md`
- `docs/product/product_doc_governance.md`
- `docs/product/review_system_governance.md`
- `docs/product/page_change_log.md`
- `docs/product/page_interaction_inventory.md`
- `docs/product/api_contract_inventory.md`
- `docs/product/data_dictionary.md`
- `docs/product/acceptance_matrix.md`
- `docs/product/release_ops_runbook.md`
- `docs/product/user_guide.md`
- `docs/product/module_lifecycle_matrix.md`
- `docs/product/error_code_catalog.md`

When product scope changes, update this working set before treating the change as complete.

## Current Quality Gates

Current V1 review evidence is guarded by:

- 18-step release review gate: `python scripts\run_release_review_gate.py`.
- 20-item production goal requirement matrix.
- UTF-8 text preflight that rejects non-UTF-8 persisted text and literal
  question-mark mojibake before acceptance.
- Analysis module contract gate.
- CRO traceability contract gate.
- External-boundary gate that keeps Aliyun/provider production readiness blocked
  until the required cloud, backup, provider callback, and DeepSeek
  official-direct evidence exists.

## Module Expansion Rule

New analysis methods must follow:

```text
docs\modules\analysis_module_contract.md
```

Do not promote a module to stable unless it has input requirements, parameter
schema, output schema, artifact manifest, report mapping, acceptance gates, and
non-medical customer copy review. The current V1 stable target remains
QC/preprocessing readiness, PSD/bandpower, and ERP/P300. TFR/ERSP/ITC and
PAC/CFC remain beta/lab candidates until stronger evidence exists.

## CRO Traceability Rule

Research/CRO traceability work must follow:

```text
docs\compliance\cro_traceability_contract.md
```

Do not claim formal GxP, medical, electronic-signature, or regulatory
certification. The safe V1 claim is that QLanalyser is designed toward
CRO-grade research traceability and has paid-pilot evidence for account,
upload, task, artifact, report, billing, invoice, inbox, admin, and audit
records.

## Current Safe Claim

The current V1 paid-pilot sandbox loop is review-ready with public ECS smoke
evidence.

Do not claim strict full public production readiness until current evidence
exists for official-direct DeepSeek copy review, real OSS and backup
configuration, HTTPS/domain/CORS finalization if required, and real provider
callbacks for payment, SMS, WeChat, and email if leaving sandbox mode.
