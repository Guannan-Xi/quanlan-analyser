# QLanalyser Full Product E2E Detailed Design

Date: 2026-06-26
Source requirements: `docs/product/qlanalyser_full_product_e2e_requirements_20260626.md`
Status: design source before implementation and full-product E2E

This document turns the full-product requirements into implementation, UI, test, and review design. It is intentionally detailed so that later workers and scripts do not rely on chat memory.

## 1. Design Target

Target maturity: polished and professional research workflow product.

Design stance:

- Quiet, dense, work-focused, and scannable.
- Scientific context first, decorative elements second.
- One page should answer: what data, what method, what state, what output, what next action, and what not to over-interpret.
- User-facing text speaks from the researcher workflow, not from the backend implementation.

## 2. Reference System Selection

`QLANALYSER_DASHBOARD_REFERENCE_SELECTION`

| Field | Decision |
|---|---|
| Surface | Main workbench, data preparation, analysis results, reports, admin/ops, Module Lab, method library |
| User role | Researcher, lab engineer, reviewer, admin/operator |
| Selected references | Carbon/Fluent/Atlassian patterns for dense enterprise tools; local QLanalyser scientific-dashboard gates |
| Adopted rules | Stable navigation, clear status, restrained palette, visible recovery, dense tables, explicit method boundaries, chart integrity |
| Skipped rules | Marketing landing hero patterns, decorative card-heavy layouts, clinical/diagnostic language, unsupported source-localization phrasing |
| Required screenshot states | default, dense, empty, loading, error, success, disabled/focus, mobile/narrow, wide, scrolled-middle, scrolled-bottom |
| Scientific boundaries | descriptive metrics only unless statistical evidence exists; connectivity is sensor-space association; PAC is coupling descriptor; synthetic fixture is not real-cohort validation |

## 3. Information Architecture

Canonical full-product IA:

```text
Cover / Login
Project Workspace
Data Management
Data Preparation
Current Available Modules
Analysis Tasks
Result Review
Report Delivery
Account / Billing
Admin / Operations
Method Library / Module Lab
```

The main researcher journey should not require opening internal test pages. Internal pages remain available for method evidence and acceptance diagnosis.

## 4. Surface Inventory Design

| Surface | File(s) | Primary user task | E2E role |
|---|---|---|---|
| Cover/login | `frontend/index.html`, `frontend/expert-entry-demo.html`, `frontend/open-design-entry-demo.html` | Identify product, login/register, enter workspace | First-viewport, auth, responsive, scroll review |
| Main app shell | `frontend/index.html`, `frontend/app.js` | Navigate project/data/preparation/analysis/report/account/admin | Main browser E2E path |
| Data preparation | `frontend/app.js`, `frontend/qc-lab.html`, `frontend/qc-lab.js` | Preview waveform, mark/restore channels, segments, events | Auto-preview and reversible edit E2E |
| Current modules | `frontend/app.js`, `frontend/research-modules.html`, `frontend/research-modules.js` | Discover methods and boundaries | Copy, method visibility, direct action mapping |
| Module Lab | `frontend/module-lab.html`, `frontend/module-lab.js` | Internal method parameter/evidence surface | Visible fields, grouped E2E, layout review |
| Method detail pages | `frontend/research-module/*.html` | Inspect method outputs and reproducibility | Scroll, copy, source artifact review |
| Report/export | `backend/api/reports.py`, report services, frontend report controls | Generate and download report package | ZIP inventory, PDF/OCR, claim scan |
| Admin/ops | `backend/api/admin.py`, admin views in app shell | Monitor tasks, accounts, billing, system state | API smoke, UI state, privacy/error review |

## 5. Cover and Login UI Design

Wireframe:

```text
+--------------------------------------------------------------------------------+
| QLanalyser Online                                            [Language/Help]    |
+--------------------------------------------------------------------------------+
| Product identity / research EEG analysis workflow                               |
| Short boundary: research workflow, not diagnostic decision software             |
|                                                                                |
| [Login form] [Register form] [Admin login tab]                                  |
| Email, password, remember, recovery                                             |
| Primary action: Enter workspace                                                 |
| Secondary: create account / forgot password                                     |
+--------------------------------------------------------------------------------+
| If scrolled: product workflow preview, privacy/data boundary, support entry      |
+--------------------------------------------------------------------------------+
```

Design rules:

- The first viewport must not be only a decorative landing page.
- Product identity and workspace entry must be visible without scrolling.
- Admin login must be discoverable but visually secondary.
- Error states preserve entered email and explain recovery.
- Cover images or background visuals must not obscure the form.

## 6. Main Workbench UI Design

Wireframe:

```text
+--------------------------------------------------------------------------------+
| Top bar: Product / project / account / service state                            |
+---------------------+----------------------------------------------------------+
| Sidebar             | Page title + current object                              |
| Project             | Project: ...  Data: ...  Preparation: ...                |
| Data                +----------------------------------------------------------+
| Preparation         | Step strip: Upload -> Preview -> Prepare -> Analyze      |
| Analysis            |             -> Result -> Report                          |
| Results             +----------------------------------------------------------+
| Reports             | Active panel                                             |
| Account/Admin       | Contextual summary + one primary action                  |
+---------------------+----------------------------------------------------------+
```

Navigation design:

- Sidebar active state uses navy/blue or neutral tokens, not green.
- Green is reserved for success.
- Preview/review methods use warning/neutral review status, not success green.
- Keyboard focus must be visible.

Content design:

- Each page has one primary object and one primary action.
- Reproducibility details are available under details/disclosure, not as default clutter.
- Internal identifiers are hidden unless needed for support or export provenance.

## 7. Data Preparation UI Design

Desktop 1440x900 target:

```text
+--------------------------------------------------------------------------------+
| Current data: synthetic_oddball.edf | 8 ch | 250 Hz | 60 s | Preview loaded     |
+---------------------+-------------------------------+--------------------------+
| Data queue          | Waveform preview              | Preparation tools        |
| selected row        | channel/time/event view       | Bad channels             |
| click row => preview| no separate primary preview   | Excluded segments        |
| file metadata       | loading/error/success state   | Event labels             |
+---------------------+-------------------------------+--------------------------+
| Processing record: before/after, user source, restore action, plan inclusion    |
+--------------------------------------------------------------------------------+
```

Narrow viewport target:

```text
Data summary
Data queue
Waveform preview
Preparation tools
Processing record
Confirm plan
```

Design rules:

- Data row click triggers preview automatically.
- A reload preview action may exist only after automatic preview is available.
- Bad channel, segment, and event tools sit on the same page as waveform preview.
- Restore action is visible in the processing record.
- Confirm plan is disabled until preview state is known.
- Long waveform/result panels may scroll internally only if the page still exposes the controls and recovery actions.

## 8. Current Available Modules and Method Actions

Module grouping:

```text
Current Available Modules
  Data preparation
    QC / data preparation and quality check
  Available analysis
    PSD / Bandpower
    ERP / P300
  Preview methods, needs review
    TFR / ERSP-ITC
    Multitaper PSD
    Multitaper TFR
    Reference / CSD
    PAC / CFC
    Connectivity
```

Direct analysis actions:

| UI action | Backend module | Workflow | Boundary |
|---|---|---|---|
| PSD | `psd` | `resting_psd` | Available |
| ERP | `erp` | `erp_p300` | Requires event markers |
| TFR | `tfr` | `tfr_ersp_itc` | Preview method, needs review |
| Multitaper PSD | `multitaper_psd_tfr` | `multitaper_psd_tfr` | Split UI action, PSD family |
| Multitaper TFR | `multitaper_psd_tfr` | `multitaper_psd_tfr` | Split UI action, TFR family |
| Reference/CSD | `reference_csd` | `reference_csd` | Sensor/reference transform boundary |
| PAC | `pac` | `pac_cfc` | Coupling descriptor, not causality |
| Connectivity | `connectivity` | `connectivity` | Sensor-space association, not source communication |

QC stays in data preparation and is not duplicated as an analysis button.

Card design:

```text
[Method name]                         [Status badge]
When to use: ...
Prerequisites: data/events/reference...
Outputs: figures, tables, reproducibility record
Boundary: descriptive/review-needed statement
[Run method] [View method details]
<details>Reproducibility details</details>
```

## 9. Analysis Method Design Contracts

Each method has a source-comparison row:

| Method | Source file | Runner | Reference behavior to compare |
|---|---|---|---|
| QC/data prep | `eeg_core/preprocess/qc_preview.py`, data preparation services | preview/metadata runners | MNE raw metadata, channel/event preview, non-destructive edits |
| PSD | `eeg_core/analysis/psd.py` | `run_psd` | MNE/NumPy spectral estimate behavior, bandpower table, frequency range |
| ERP | `eeg_core/analysis/erp.py` | `run_erp` | event epoching, baseline window, latency/amplitude metric recovery |
| TFR | `eeg_core/analysis/tfr.py` | `run_tfr` | time-frequency power/ITC shape, event lock, baseline interpretation |
| Multitaper | `eeg_core/analysis/multitaper_psd_tfr.py` | `run_multitaper_psd_tfr` | multitaper PSD/TFR family separation, output family flag |
| Reference/CSD | `eeg_core/analysis/reference_csd.py` | `run_reference_csd` | reference transform before/after, sensor-space boundary |
| PAC | `eeg_core/analysis/pac.py` | `run_pac` | phase-amplitude coupling descriptor, surrogate/null boundary if available |
| Connectivity | `eeg_core/analysis/connectivity.py` | `run_connectivity` | correlation/coherence matrix, sensor-space association boundary |

Required comparison dimensions:

- Input file format and metadata.
- Required channels/events.
- Parameter defaults and validation.
- Output artifact names and schemas.
- Figure titles, axes, units, legend, color semantics.
- Warnings and limitations.
- Repeated-run determinism or tolerance.
- Difference from reference library/API behavior.

## 10. Synthetic Fixture Design

Fixture design:

| Signal component | Purpose | Expected recovery |
|---|---|---|
| Alpha rhythm around posterior channels | PSD/bandpower sanity | alpha band visibly elevated |
| Target event response | ERP sanity | latency and amplitude near injected response |
| Time-locked burst | TFR sanity | burst appears around known time/frequency |
| Coupled phase/amplitude component | PAC sanity | coupling output exists and boundary text warns against causality |
| Channel relationship pair | Connectivity sanity | related channels appear among stronger associations |
| Bad channel/noisy segment | QC/data preparation sanity | mark/restore path is meaningful |

Fixture metadata:

- seed
- sampling rate
- channel names
- duration
- event labels
- known signal definitions
- expected output ranges
- checksum
- non-sensitive synthetic status

## 11. Result and Report Design

Result review layout:

```text
+--------------------------------------------------------------------------------+
| Method result: PSD / ERP / ... | Task completed | Source data | Preparation rev |
+--------------------------------------------------------------------------------+
| Summary cards: method, data, parameters, quality warnings, outputs              |
+--------------------------------------------------------------------------------+
| Figures with titles, axes, units, legend, boundary note                         |
+--------------------------------------------------------------------------------+
| Tables with units and export actions                                            |
+--------------------------------------------------------------------------------+
| Reproducibility details: parameters, versions, workflow, processing record       |
+--------------------------------------------------------------------------------+
```

Report package must include:

- `reports/report.html`
- `reports/report.pdf`
- `reports/report_manifest.json`
- figures
- tables/CSV
- method text
- parameters
- software versions
- workflow/provenance
- processing record

No report may use local path or internal ID as its main user-facing explanation.

## 12. UI State Design

Required states:

| State | Required user answer |
|---|---|
| Empty | What would appear here, why empty now, what to do next |
| Loading | What is running, which stage, whether user can wait/background/cancel |
| Error | What failed, affected object, next action, safe support ID |
| Success | What completed, where result is, next action |
| Disabled | Why disabled and what prerequisite is missing |
| Long task | stage, progress if measurable, retry/background/cancel policy |

Long analysis/report tasks must not use an unexplained spinner as the only feedback.

## 13. Scroll and Responsive Design

Scroll review must include:

- top, middle, bottom screenshots for long pages
- browser scroll and inner-panel scroll
- no horizontal overflow at 390 width
- sticky/fixed controls do not cover content
- primary actions do not disappear behind the fold without an anchor
- long method names and long file names wrap or truncate predictably
- keyboard focus remains visible after scroll
- error summary links or moves focus to the failing field

Known high-risk pages:

- `frontend/index.html` main workbench
- data preparation section in `frontend/app.js`
- `frontend/module-lab.html`
- `frontend/research-modules.html`
- `frontend/research-module/*.html`
- admin/ops sections in the main app shell
- report/result review views

## 14. Visual Token Design

Token principles:

- Semantic tokens before raw colors.
- Status colors are not brand colors.
- Green is only success.
- Warning/review methods use amber/neutral review status.
- Error uses text/icon/label, not color alone.
- Focus ring is visible and consistent.
- Scientific chart palettes are separate from UI status colors.

Audit targets:

- Sidebar active state.
- Primary/secondary/danger/disabled buttons.
- Status badges.
- Form validation.
- Tables.
- Chart palettes.
- Report export UI.
- Admin status cards.

## 15. Scientific Figure Design

Each generated figure must show or record:

- method name
- source data
- axis labels
- units
- frequency/time range when relevant
- legend/colorbar/direct labels
- baseline/normalization when relevant
- sample/epoch/event context when available
- limitation or boundary note when the visual can be over-interpreted

Unsafe figure decisions:

- rainbow/jet default for quantitative scientific data
- topomap or connectivity wording implying source localization without evidence
- PAC/connectivity arrows implying causality
- statistical significance markers without statistical test evidence

## 16. DeepSeek Logic Review Design

DeepSeek is used only after Codex has written the requirement/design/test package and route-check confirms official direct DeepSeek:

```text
role: polish / logic review
model: deepseek-chat
base: https://api.deepseek.com/v1
uses_headroom: false
```

DeepSeek review packet input:

- this design document
- requirements document
- test plan
- method/action matrix
- researcher workflow questions

DeepSeek output must be saved as UTF-8 under:

```text
work/release_evidence/07-full-product-e2e-pdca/deepseek/researcher_logic_review.md
```

Codex acceptance rules:

- DeepSeek may identify logic/copy/workflow risks.
- DeepSeek cannot issue release/pass verdict.
- Codex must map findings to requirement IDs and either fix, backlog, or reject with evidence.

## 17. Implementation Sequence

1. Save requirements/design/test-plan documents.
2. Generate inventory and method matrix.
3. Generate synthetic fixture manifest.
4. Run static and API preflight.
5. Run method source-comparison tests.
6. Run main workbench E2E for every direct method.
7. Run report ZIP and scientific figure checks.
8. Run UI screenshot/scroll/state review.
9. Run DeepSeek researcher-logic review.
10. Build acceptance packet.

## 18. Rollback and Safety

- Do not change router, Headroom, IPC, gateway, or production process communication.
- Do not delete ignored work evidence.
- Do not reset dirty worktree changes.
- Do not use real customer data.
- Any code fix must be file-scoped and verified before acceptance.
- If a P0 appears, stop the acceptance claim and write a blocked packet.

## 19. DeepSeek Researcher Logic Review Adoption

Source:

```text
work/release_evidence/07-full-product-e2e-pdca/09_deepseek/researcher_logic_review_ascii.md
```

Adopted design refinements:

1. Data import summary must show channel type assumptions. If mixed channel types are detected or unknown, the UI must show a review-needed warning before analysis.
2. Bad-channel automation must not remove channels silently. Researcher review/override is required before any automatic suggestion enters the preparation plan.
3. PSD action should show data-quality status: previewed/prepared/unknown, filter/artifact status if available, and a warning when status is unknown.
4. ERP action should validate event marker availability and show a specific no-event recovery state.
5. TFR action should compare epoch length with the lowest requested frequency and warn when the requested window is likely too short.
6. Connectivity results must keep the sensor-space association boundary visible near the figure and table.
7. Preview panels must state whether they use full data or a subset. If a subset is used, the subset rule must be displayed near the preview title.
8. Long analyses must show a stage label after 5 seconds or earlier: queued, loading data, preprocessing, running analysis, rendering, packaging, complete, failed.
9. Dense scroll designs must include long channel names, more than 50 channels when fixture-supported, and more than 100 frequency rows/bins where applicable.
10. Copy must not imply manual artifact rejection, all EEG formats, real-time analysis, cloud processing, or multi-user collaboration unless the implementation and evidence explicitly support it.

Design impact:

- These refinements are treated as P1/P2 quality gates for full-product release readiness.
- They are not allowed to introduce clinical/diagnostic language.
- If current code cannot fully implement them in one slice, the UI must at least show honest boundary text and the acceptance packet must record the gap.

## 20. Backend/Admin Smoke and Copy Guard Design Addendum

Backend/admin verification is a separate product surface because researchers and operations users rely on it indirectly even when the main UI flow works.

Backend smoke flow:

```text
+--------------------+     +-------------------+     +----------------------+
| Health/readiness   | --> | Customer login    | --> | Customer resources   |
| OpenAPI contract   |     | Admin login       |     | Admin operations     |
+--------------------+     +-------------------+     +----------------------+
           |                         |                         |
           v                         v                         v
   route presence          role/token assertions       structured JSON evidence
```

Admin UI intent sketch:

```text
+----------------------------------------------------------------------------+
| Operations backstage                                                        |
+----------------------------------------------------------------------------+
| Overview metrics | Account list | Billing and invoices | Task status | State |
| No customer-only navigation leaks; no technical IDs as primary explanations |
+----------------------------------------------------------------------------+
```

Design rules:

- Admin routes require admin token; unauthenticated access is a product blocker.
- Backend smoke uses seeded demo accounts and synthetic/demo datasets only.
- Demo run-all is allowed as a fixture-safe backend exercise; it must not imply real-cohort validation.
- Customer-facing copy remains task-oriented: what the researcher can do next, what the prerequisite is, and what the output means.
- Developer IDs, backend module names, ZIP wording, and internal contract language may appear only in details/download metadata, not as primary visible copy.
