# Module Detailed Design Docs

This directory contains canonical module detailed design documents for QLanalyser Online.

Use `docs/templates/module_design_doc.md` for module specs such as:

- QC
- PSD
- ERP
- TFR
- PAC
- Connectivity

Rules:

- Each module design should define inputs, parameters, MNE/algorithm mapping, outputs, chart quality standards, risks, and acceptance criteria.
- Experimental Analysis Lab modules should be specified here before being merged into the formal workbench flow.
- Feishu summaries are generated from these docs and are not the canonical source.


## Current canonical module docs

- `docs/modules/analysis_modules_design_matrix.md`: QC / PSD / ERP / TFR / PAC / Connectivity module status, input/output, MNE mapping, risk, and promotion criteria.
- `docs/modules/analysis_module_contract.md`: standard module contract for lifecycle, schemas, execution, artifacts, report mapping, acceptance gates, and non-medical research/CRO boundaries.
- `docs/modules/analysis_method_inheritance_guide.md`: method inheritance ladder from preview to stable, plus subflow split and main-flow promotion rules.
- `docs/modules/eeg_method_portfolio_matrix.md`: main-flow / enhancement / preview matrix across toolkits and EEG method families.

Acceptance:

```powershell
python scripts\acceptance_analysis_module_contract.py
```
