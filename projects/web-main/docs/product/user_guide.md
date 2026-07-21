# QLanalyser User Guide

Date: 2026-07-03

## 1. What this product does

QLanalyser helps research users work with EEG files in a structured way:

- organize projects;
- upload or select data;
- inspect data quality;
- prepare the file;
- run an analysis;
- review results;
- download a report.

## 2. Basic workflow

### Step 1: Choose a project

Pick the project you are working on. If the project does not exist yet, create it first. The file list stays collapsed until you choose a project.

### Step 2: Add data

Upload or select the EDF file for that project. Use the project-scoped file list instead of browsing unrelated data.

### Step 3: Review the data

Check the file name, format, sampling rate, channels, and any summary warnings.

### Step 4: Prepare the data

Use the preview panel to inspect a time window, mark bad channels, mark bad segments, and handle annotations.

### Step 5: Save the preparation plan

Save the preparation state so later analysis can reuse it.

### Step 6: Run the analysis

Choose the allowed analysis module and run it when prerequisites are satisfied.

### Step 7: Review the result

Open the result page and check the summary, tables, figures, and warnings.

### Step 8: Download the report

Download the report package for review or handoff.

## 3. Analysis modules

### 3.1 Phase-Amplitude Coupling (PAC)

QLanalyser provides two PAC variants:

- **PAC V1** (`pac_cfc`, beta): single-metric Tort Modulation Index output with
  comodulogram, phase-bin, and dynamic-curve figures plus a full artifact bundle.
- **PAC V2** (`pac_cfc_v2`, stable candidate, promoted 2026-07-03): a faster,
  multi-metric PAC variant supporting Modulation Index (MI), Mean Vector Length
  (MVL), and KL divergence. V2 is 2.22x-4.74x faster than V1 and its MI output
  matches V1 exactly (correlation r = 1.000000).

PAC is single-record descriptive sensor-space output only. It is not for
diagnosis, treatment, clinical decision support, causality, source localization,
brain-region communication, or group-level inference. No p-value or formal
significance conclusion is produced.

For the full V1/V2 differences (default parameters, metric support, output
format, speed), see `work/pac_dev/PAC_V1_V2_COMPARISON.md`.

## 4. What belongs in the personal center

The personal center is for account-related actions:

- balance;
- recharge;
- invoice;
- notifications;
- security;
- help.

It can also hold account status, reminders, and other non-workflow items that would otherwise clutter the project workspace.

## 5. What does not belong in the main work area

The main workflow should not be cluttered with:

- internal audit tokens;
- debug wording;
- irrelevant billing controls;
- method previews that are not part of the current task.

## 6. When something goes wrong

If a button does not work or a step is blocked:

- check the message shown on screen;
- check whether the prerequisite step is missing;
- check whether the file or project is selected;
- refresh the page if the state looks stale;
- if it still fails, record the step and the error for support.
