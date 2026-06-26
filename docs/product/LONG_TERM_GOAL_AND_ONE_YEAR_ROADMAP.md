# QLanalyser Long-Term Product Goal and One-Year Roadmap

Date: 2026-06-20
Owner intent: Build a globally top-tier research EEG analysis tool and CRO
infrastructure. QLanalyser is not a medical diagnosis, treatment, or clinical
decision product.

## North Star

QLanalyser is not a static EEG demo site and not a medical product. It is a
production-grade research EEG analysis tool and CRO infrastructure that turns
non-standard EEG analysis work into standardized, reproducible, auditable, and
commercially operable workflows.

The long-term product direction is:

- Standardized EEG data and delivery foundation.
- Pluggable analysis-method module system.
- CRO-grade auditability, SOP traceability, and quality management.
- Global scientific and regulatory readiness.
- Customer self-service operation: upload, pay, analyze, review, download, invoice, and audit.
- Explicit non-medical boundary: no clinical diagnosis, no treatment advice, no
  medical device claim, and no clinical decision support claim.

## Strategic Positioning Guardrail

All roadmap, MVP, milestone, commercial, design, backend, and acceptance work
must optimize for this product category:

```text
Top-tier research EEG analysis tool + CRO infrastructure, not medical software.
```

This means QLanalyser should compete on scientific rigor, workflow
standardization, reproducibility, audit evidence, expert usability, and delivery
quality. It should not drift into a generic SaaS dashboard, a consumer wellness
tool, or a clinical medical workflow.

## Current V1 Release Goal

The first production operating version must remain focused on the already defined initial function set:

- Main EEG analysis flow.
- Analysis lab.
- Preset analysis functions.
- Customer registration and login.
- Email registration, phone verification registration, WeChat registration sandbox/operable boundary.
- Alipay and WeChat Pay sandbox or operable confirmation loop.
- Balance, deduction, ledger, orders.
- Invoice information submission.
- Admin backend to view and process invoices.
- Admin uploads invoice PDF and delivers it to customer inbox.
- Admin operations console.
- Report ZIP delivery.
- Security redaction and sanitized evidence package.
- 10-user / 50-task evidence.
- 10 x 200MB and 1 x 1GB data-size evidence.
- Aliyun deployment, rollback, operations preparation.

V1 must be real and runnable, not a static demo. Third-party dependencies may remain sandboxed only when the product contains real orders, statuses, files, records, scripts, and evidence matrices.

## One-Year Roadmap

### Phase 0: V1 stable paid launch, weeks 0-4

Goal: Make the current V1 stable enough for paid pilot usage.

Scope:
- Harden current upload -> analyze -> report ZIP flow.
- Harden registration, sandbox payment, wallet, invoice, admin, inbox.
- Keep QC, preprocessing, PSD/bandpower, ERP/P300 real and evidence-backed.
- Public deployment with rollback evidence.
- Clear sandbox/provider boundaries.
- DeepSeek official-direct Chinese copy gate for all customer-facing text.

Exit criteria:
- Customer can register, recharge in sandbox, upload EEG, run supported analyses, download results, request invoice, and receive invoice PDF.
- Admin can operate tasks and invoices from UI.
- Release evidence matrix passes.
- Public URL smoke and core browser acceptance pass.

### Phase 1: Standardized workflow foundation, months 1-3

Goal: Turn V1 from feature set into a reusable EEG workflow foundation.

Scope:
- Formal project / subject / session / task data model.
- Standard metadata schema for EEG files, events, channels, sampling rate, reference, montage, and acquisition notes.
- QC and preprocessing plan contract: plan id, revision, parameters, operator, timestamp, evidence.
- Standard artifact manifest for every analysis task.
- Report package manifest with inputs, outputs, software versions, parameters, and warnings.
- Basic RBAC and organization isolation.
- Better error states for bad uploads, missing events, bad channel metadata, and failed analysis.

Exit criteria:
- Every output can be traced to source file, preprocessing plan, analysis parameters, software version, and task id.
- Analysis modules no longer invent their own ad hoc input/output contracts.

### Phase 2: Pluggable analysis module architecture, months 3-6

Goal: Make new EEG methods attachable as modules instead of hard-coded pages.

Scope:
- Module registry: id, name, scientific purpose, input requirements, parameter schema, output schema, report sections, QC prerequisites.
- Module lifecycle: draft -> internal validation -> beta -> stable -> deprecated.
- Standard frontend renderer for module parameters and results.
- Standard backend runner contract for module execution.
- Standard acceptance template for each module.
- Canonical contract: `docs/modules/analysis_module_contract.md`.
- Initial stable modules: preprocessing/QC, PSD/bandpower, ERP/P300.
- Beta modules: TFR/ERSP/ITC, PAC/CFC, QC preview extensions.
- Explicitly not stable until evidence: connectivity, source localization, AI interpretation.

Exit criteria:
- A new analysis method can be added by registering schema, runner, report mapping, and acceptance gates without rewriting the whole product shell.
- `python scripts\acceptance_analysis_module_contract.py` passes and every new method links to the module contract.

### Phase 3: CRO-grade quality and compliance layer, months 6-9

Goal: Make QLanalyser credible for CRO, pharma research, and research-service
delivery contexts without falsely claiming medical, GxP, or regulatory
certifications.

Scope:
- Audit trail for data upload, parameter change, task run, report generation, invoice/admin actions.
- Report versioning and immutable delivery records.
- Review and approval workflow: analyst review, scientific reviewer, admin release.
- Electronic signature / approval placeholder architecture.
- SOP-linked tasks and controlled templates.
- Data integrity principles: ALCOA+ alignment as product design principle.
- Security controls: customer isolation, redaction, access logs, least privilege.
- Research/CRO standard mapping notes for China and global contexts, without
  unsupported medical, GxP, or regulatory compliance claims.
- Canonical traceability contract: `docs/compliance/cro_traceability_contract.md`.

Exit criteria:
- A CRO-style reviewer can answer: who did what, when, with which data, which parameters, which software version, which output, and who approved it.
- `python scripts\acceptance_cro_traceability_contract.py` passes.

### Phase 4: Global-grade scientific and operational infrastructure, months 9-12

Goal: Move from product to globally competitive EEG analysis infrastructure.

Scope:
- Internationalization-ready UI and report structure.
- Method library mapped to major EEG research paradigms.
- Reproducible container/runtime strategy.
- Cloud storage lifecycle and backup/restore production evidence.
- Stronger concurrency and large-file pipeline.
- Monitoring, alerting, task observability, cost accounting.
- Module validation benchmark datasets.
- Publishable report and figure standards.
- Customer success loop: usage analytics, funnel, module performance, support dashboard.

Exit criteria:
- QLanalyser can support paid pilots across research teams with standardized delivery, repeatable reports, evidence-backed modules, and an upgrade path toward CRO-grade compliance.

## Non-Drift Rules

Every future task must be checked against these rules:

1. Do not drift into medical diagnosis, treatment advice, medical-device claims,
   or clinical decision support.
2. Do not drift into generic SaaS; every major feature must serve research EEG
   analysis standardization, CRO delivery, or paid scientific operations.
3. Do not replace real analysis with static text, images, or fake buttons.
4. Do not hard-code one-off analysis flows when a module contract is needed.
5. Do not call sandbox/provider-gated features real production integrations without evidence.
6. Do not add a method as stable without input requirements, parameter schema, output schema, report mapping, and acceptance evidence.
7. Do not weaken traceability: every result must keep source, parameters, software version, task id, and artifact manifest.
8. Do not claim CRO/GxP/medical compliance before formal validation; design toward compliance and label readiness accurately.
9. Do not let visual polish hide missing backend execution.
10. Do not let internal/demo/lab paths dominate the customer paid workflow.
11. Do not skip Chinese copy review for customer-facing text when it affects trust or payment.
12. Do not treat V1 as complete until the customer can actually upload, pay/sandbox pay, analyze, download, invoice, and admin-operate the flow.

## Version Naming

- V1: Paid pilot launch, stable initial methods and operations loop.
- V1.5: Workflow foundation and traceability hardening.
- V2: Pluggable EEG analysis module platform.
- V3: CRO-grade audit, review, and controlled delivery layer.
- V4: Global EEG analysis infrastructure with validated module marketplace and international deployment readiness.
