# QLanalyser 当前可用分析方法、教学模式与全流程 E2E 测试验证文档

Date: 2026-06-26
Source requirements: `docs/product/qlanalyser_current_modules_teaching_mode_requirements_20260626.md`
Source design: `docs/product/qlanalyser_current_modules_teaching_mode_design_20260626.md`
Source UI draft: `docs/product/qlanalyser_current_modules_teaching_mode_ui_design_20260626.md`
Status: test and validation contract before implementation

## 1. Evidence Root

All evidence for this slice is saved under:

```text
work/release_evidence/07-full-product-e2e-pdca/12_current_modules_teaching_mode/
```

Required subfolders:

```text
00_docs/
01_inventory/
02_deepseek/
03_static_checks/
04_backend_api/
05_synthetic_data/
06_methods/
07_ui_browser/
08_reports_figures/
09_acceptance_packet/
```

## 2. PDCA Test Record Schema

Each validation item writes a JSON record:

```json
{
  "id": "TC-...",
  "requirements": ["R-..."],
  "pdca": {
    "plan": "what is tested and why",
    "do": "command/browser/API/action",
    "check": "assertions and evidence paths",
    "act": "accepted|fixed|blocked|backlog"
  },
  "status": "passed|failed|blocked|skipped_with_reason",
  "evidence": [],
  "findings": []
}
```

No test may be marked `passed` without an evidence path.

## 3. Documentation and DeepSeek Gate

| ID | Requirements | Test | Pass condition |
|---|---|---|---|
| DOC-1 | R-DEEPSEEK-01 | Check requirements/design/UI/test docs exist. | All four docs exist and are UTF-8 readable. |
| DOC-2 | R-DEEPSEEK-01 | Run `scripts/check_no_mojibake.py` on new docs and review packets. | No mojibake markers. |
| DOC-3 | R-DEEPSEEK-01 | Create DeepSeek review prompt from these docs. | Prompt saved under evidence root. |
| DOC-4 | R-DEEPSEEK-01 | Run DeepSeek polish/logic route if available. | Review saved, or explicit unavailable JSON with command/error. |
| DOC-5 | R-DEEPSEEK-01 | Codex adoption review. | Every DeepSeek issue accepted/rejected with reason. |

## 4. Static Copy and UI Inventory Gate

Forbidden visible terms:

- `预览方法`
- `可试用`
- `需复核`
- `beta`
- `Reference / CSD`
- `参考方案与 CSD`
- `module id`
- `workflow id`
- `/api/tasks`
- `acceptance`
- `gate`
- `debug`

Allowed contexts:

- Developer docs.
- Test files that define forbidden terms.
- Reproducibility downloads or collapsed admin diagnostics.

Tests:

| ID | Requirements | Scope | Pass condition |
|---|---|---|---|
| COPY-1 | R-COPY-01 | `frontend/index.html`, `frontend/app.js`, customer-visible frontend HTML/JS | No forbidden release-maturity wording. |
| COPY-2 | R-COPY-02 | method card bodies and result boundary text | CSD/PAC/Connectivity limitations remain visible. |
| COPY-3 | R-IA-01/R-IA-03 | method card inventory | Exactly 8 current available analysis method cards. |
| COPY-4 | R-NAV-01/R-NAV-02 | nav/topbar inventory | `个人中心` and `教学模式` are globally reachable. |

## 5. Synthetic Data Fixture Gate

Fixture requirements:

- Deterministic seed.
- EDF output.
- Channel list includes valid EEG labels with montage positions.
- Events include at least `standard` and `target`.
- Signal design supports:
  - PSD: alpha rhythm dominance.
  - ERP: target P300-like response.
  - TFR/Multitaper TFR: event-related time-frequency window.
  - PAC: synthetic or at least non-empty phase/amplitude bands.
  - Connectivity: multiple channels and stable segment windows.
  - CSD: montage/channel locations.

Tests:

| ID | Requirements | Command/source | Pass condition |
|---|---|---|---|
| FX-1 | R-TEACH-01/R-E2E-01 | `scripts/generate_teaching_oddball_case.py` or equivalent | EDF/events generated, manifest records seed and synthetic status. |
| FX-2 | R-CSD-02 | fixture metadata | Montage/channel locations present. |
| FX-3 | R-TEACH-03 | demo service state | Demo project/file IDs are isolated from real projects. |

## 6. Backend/API Gate

| ID | Requirements | Endpoint/script | Pass condition |
|---|---|---|---|
| API-1 | R-TEACH-01 | `/api/lab/demo/dataset` | Returns project and file. |
| API-2 | R-E2E-01 | `/api/lab/demo/run-all` | Runs supported synthetic demo methods and returns task list. |
| API-3 | R-CSD-01/R-CSD-02 | `/api/tasks` with `module_name=reference_csd`, `reference_mode=csd` | CSD runs when montage is present. |
| API-4 | R-CSD-02 | CSD with missing montage fixture | Fails with recoverable montage-required message, not generic crash. |
| API-5 | R-REF-01 | Re-reference modes through preparation/parameters | Average/specific/bipolar modes are recorded as preprocessing, not method cards. |

## 7. Analysis Method Source-Comparison Gate

Every method must be compared against source implementation and output artifacts.

| ID | Method | Source check | Runtime check | Figure/report check |
|---|---|---|---|---|
| M-PSD | PSD 频谱与频段功率 | `eeg_core/analysis/psd.py` | task/API or direct runner | spectrum axes, units, band table |
| M-ERP | ERP 事件相关电位 | `eeg_core/analysis/erp.py` | event fixture | waveform, metrics, drop log, baseline |
| M-TFR | TFR 时频分析 | `eeg_core/analysis/tfr.py` | event fixture | time-frequency image, colorbar, baseline mode |
| M-MTP | Multitaper PSD | multitaper source family | `analysis_family=psd` | bandwidth/parameter record |
| M-MTT | Multitaper TFR | multitaper source family | `analysis_family=tfr` | time-frequency output and ITC if supported |
| M-PAC | PAC 相位-振幅耦合 | `eeg_core/analysis/pac.py` | synthetic channels/bands | comodulogram/phase-bin outputs, no causality claim |
| M-CON | Connectivity 连接性分析 | `eeg_core/analysis/connectivity.py` | multi-channel fixture | matrix/edge table, no information-flow claim |
| M-CSD | CSD 电流源密度计算 | `eeg_core/analysis/reference_csd.py`, `compute_current_source_density` | `reference_mode=csd` with montage | before/after preview, CSD summary, not source localization |

Pass condition:

- Required output artifacts exist.
- Parameter manifest exists.
- Method boundary text does not overclaim.
- Figures meet scientific plotting gate: title, axes/units where applicable, colorbar/legend for heatmaps/topomaps, source/parameter provenance.

## 8. Browser/UI E2E Gate

Required screenshot/click paths:

| ID | Requirements | Path | Pass condition |
|---|---|---|---|
| UI-1 | R-E2E-01 | Cover/login customer path | User reaches project management. |
| UI-2 | R-NAV-01 | Project management -> personal center | Personal center visible and reachable. |
| UI-3 | R-NAV-02/R-TEACH-02 | Project management -> teaching mode | Top-right teaching button opens overlay. |
| UI-4 | R-QC-01 | Data row click | Waveform/QC enters loading/success without `运行质控预览`. |
| UI-5 | R-QC-02 | Mark/restore bad channel/segment/event | Each edit is visible and individually recoverable. |
| UI-6 | R-REF-01 | Re-reference panel | Modes are in data preparation, not method cards. |
| UI-7 | R-IA-03 | Analysis task page | 8 method cards, no data-prep duplicate. |
| UI-8 | R-CSD-01 | Method card | CSD appears as `CSD 电流源密度计算`. |
| UI-9 | R-TEACH-04 | Teaching full path | Steps progress through data, preparation, method, result, report. |
| UI-10 | R-VIS-01 | Desktop/mobile scroll | No core tool hidden below fold; no overlap; colors/status/focus pass review. |

Screenshot matrix:

- desktop 1440x1000
- laptop 1280x800
- mobile 390x844
- wide 1920x1080
- states: default, teaching, data loading, data success, method cards, result/report, error/recovery where practical

## 9. Scientific Figure Gate

| ID | Requirement | Check |
|---|---|---|
| FIG-1 | R-VIS-02 | No rainbow/jet default for quantitative heatmaps unless explicitly justified. |
| FIG-2 | R-VIS-02 | TFR/PAC/connectivity figures include legend/colorbar or direct labels. |
| FIG-3 | R-VIS-02 | Axes and units are present where the plot has physical dimensions. |
| FIG-4 | R-COPY-02 | Figure titles/captions do not imply diagnosis, source localization, or causality. |
| FIG-5 | R-E2E-01 | Exported report includes method, parameters, data provenance, and boundary text. |

## 10. Final Acceptance Packet

Final packet fields:

```json
{
  "route_decision": "",
  "reused_pool_or_new_pool": "",
  "execution_packets": [],
  "executor_evidence": [],
  "targeted_or_full_e2e": "",
  "page_visual_review": "",
  "deepseek_logic_review": "",
  "gpt55_acceptance": "",
  "final_receipt": "completed_final_receipt|blocked_final_receipt",
  "next_real_artifact": "",
  "route_chain": "",
  "model_lane": "",
  "headroom_savings": ""
}
```

Acceptance can pass only if:

- Docs exist and pass mojibake checks.
- DeepSeek review is completed or explicitly unavailable with saved prompt/error.
- Static copy gate passes.
- Backend/API smoke passes.
- Synthetic data method E2E passes for all supported methods.
- Browser/UI E2E screenshots exist.
- Scientific figure audit passes or lists blockers.
- Codex/GPT-5.5 final acceptance reviews all evidence.
