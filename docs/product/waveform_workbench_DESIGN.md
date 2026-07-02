# WaveformWorkbench DESIGN

Date: 2026-06-27
Module: QLanalyser WaveformWorkbench / Data Preparation Waveform Area
Status: active design contract

## Purpose

WaveformWorkbench is the EEG reading and data-preparation surface for researchers. It must feel closer to EDFbrowser than to a generic web chart: open data, see continuous multi-channel EEG, browse quickly, adjust time scale and amplitude, then mark segments, bad segments, bad channels, filter preview, and reference settings without overwriting the raw file.

This contract applies to:

- `frontend/waveform-workbench.html`
- `frontend/waveform-workbench.css`
- `frontend/waveform-workbench.js`
- the main data-preparation waveform area in `frontend/index.html`, `frontend/app.js`, and `frontend/styles.css`

## Target Users

- EEG researchers, students, CRO operators, and lab staff.
- They need to inspect signal quality and prepare data before formal methods such as PSD, Band Power, TFR, ERP, PAC, Connectivity, and CSD.
- They are not using this as a medical diagnostic viewer.

## First Screen Rule

When a teaching dataset or selected EEG file is active, the waveform must be visible without an extra preview button.

Required first-screen signals:

- selected file name and protected teaching-data status when applicable;
- large, readable multi-channel waveform;
- current time window, seconds per page, channel count, uV/row, Raw/Filter state;
- mode: browse, select segment, bad segment, or bad channel;
- nearby preprocessing controls for filter preview, bad channels, segments, and reference.

The waveform must not be a small thumbnail. At desktop width, it should be the primary visual object in the data-preparation page. If the screen is too narrow to show preprocessing beside it, preprocessing moves below the waveform instead of compressing the waveform.

## Layout Contract

Desktop:

- Left navigation remains stable.
- Data queue may sit on the left, but it must not squeeze the waveform below a readable width.
- The waveform column should remain at least about 620 px wide before the preprocessing panel is allowed beside it.
- Preprocessing controls may sit beside the waveform only when there is enough horizontal space.
- On narrower desktop or tablet widths, preprocessing must wrap below the waveform.

Mobile:

- Stack in this order: selected data, waveform controls, waveform, status, draft/preprocessing controls.
- Avoid tall empty waveform placeholders before data is selected.

## Interaction Contract

Browse mode is the default and must not write data-preparation draft state.

Mouse and keyboard:

- ordinary wheel pans horizontally;
- Ctrl/Cmd + wheel changes time scale around the cursor anchor;
- PageUp/PageDown moves by one page;
- Left/Right moves by 1/10 page;
- +/- changes amplitude sensitivity;
- Ctrl/Cmd +/- changes time scale;
- middle-drag pans horizontally when supported;
- select segment, mark bad segment, and mark bad channel require explicit mode switching.

Draft model:

- L1 transient interaction: hover and drag preview only;
- L2 local UI draft: selected segment, bad segment, bad channel, with undo/restore affordances;
- L3 persisted preparation plan revision: only after explicit confirmation/save.

Raw EEG must not be modified by preview, browsing, filtering preview, or draft edits.

## Visual Style

Use a calm scientific-product style:

- neutral light background;
- dark text with strong contrast;
- restrained blue/teal interaction accents;
- clear cards only where they frame a tool or repeated item;
- no decorative blobs, hero gradients, or marketing composition in the workbench;
- no one-note green page. Green may indicate success/confirmed state, not dominate the navigation or waveform area.

Waveform:

- white canvas background;
- subtle grid lines;
- readable channel labels;
- distinct channel colors with scientific restraint;
- no rainbow/jet colormap for scientific output;
- overlays for selection/bad segments must be translucent and aligned with the time axis.

## Copy Contract

Copy must speak to the user, not the developer.

Use:

- "数据准备", "预览波形", "确认数据准备", "坏道", "坏段", "重参考设置", "滤波预览";
- "科研数据准备，不用于诊断";
- "预览不改写原始 EEG";
- "保存前可恢复".

Avoid:

- "preview method", "internal validation", "runner", "artifact", "workflow id", "QC as analysis method";
- any positive diagnostic, treatment, clinical triage, or medical decision promise.

QC is a data-preparation dependency, not an analysis method card.

## Data And Loading Contract

- Teaching mode must load protected built-in data automatically.
- Teaching data cannot be deleted, overwritten, or treated as user-uploaded mutable data.
- Existing waveform preview artifacts may be reused, but they must include or recover the full recording duration.
- If an old preview artifact only contains the current window, the UI must still know the file duration from file metadata or request a longer preview.
- A failed reload must not cover an already drawn valid waveform with an error overlay. Keep the waveform visible and report the issue in status text or a retry action.

## Accessibility And Readability

- Controls need stable button sizes and visible focus states.
- Icon-only controls need titles/tooltips.
- Text must not overflow buttons, cards, or sidebars at 1440, 1280, and 390 px viewport widths.
- Status text should be scannable, not a paragraph wall.

## Acceptance Gates

Before merging visual or interaction changes, run or update evidence for:

- independent WaveformWorkbench page loads teaching data and shows waveform;
- main data-preparation page loads teaching data and shows waveform;
- empty overlay is hidden when waveform data exists;
- ordinary wheel pans, Ctrl/Cmd wheel zooms, PageDown and ArrowRight move as specified;
- browse drag does not write drafts;
- select segment, bad segment, and bad channel modes write recoverable UI draft;
- scrolling the page does not make the waveform disappear;
- no forbidden route changes: router, Headroom, gateway, IPC, model route;
- no TimeChart dependency in the current Canvas route.

Current evidence paths:

- `work/release_evidence/20260627-waveform-workbench-module/waveform_workbench_e2e_result.json`
- `work/release_evidence/20260627-waveform-workbench-module/01_initial_loaded.png`
- `work/release_evidence/20260627-waveform-workbench-module/02_after_wheel_pan.png`
- `work/release_evidence/20260627-waveform-workbench-module/03_after_ctrl_zoom.png`
- `work/release_evidence/20260627-waveform-workbench-module/04_after_write_mode_draft.png`
- `work/release_evidence/20260627-waveform-workbench-module/05_after_scroll_persistence.png`
- `work/release_evidence/20260627-main-data-prep-waveform-visible/main_data_prep_waveform_visible_e2e.json`
- `work/release_evidence/20260627-main-data-prep-waveform-visible/main_data_prep_waveform_visible.png`

## Do Not Do

- Do not turn the waveform into a static screenshot.
- Do not require a separate "run QC preview" button before the user can see selected teaching data.
- Do not put preprocessing controls far below the waveform.
- Do not let a side panel compress the waveform into a narrow strip.
- Do not show stale error overlays on top of a valid waveform.
- Do not treat reference settings as an analysis method.
- Do not introduce TimeChart into this slice.
