# QLanalyser Data Dictionary

Date: 2026-06-22

## 1. Purpose

This document defines the key product objects and their user-facing meaning.

## 2. Core objects

### 2.1 Project

Purpose:

- top-level container for one research workflow space.

Key fields:

- `project_id`
- `name`
- `status`
- `status_label`
- `file_count`
- `created_at`
- `updated_at`
- `owner_id`

### 2.2 EEGFile

Purpose:

- a data file inside a project.

Key fields:

- `file_id`
- `project_id`
- `file_name`
- `format`
- `sampling_rate`
- `channel_count`
- `duration_sec`
- `status`
- `status_label`
- `user_note`
- `metadata_json`

### 2.3 DataPreparationPlan

Purpose:

- shared preparation context for a file or project.

Key fields:

- `plan_id`
- `file_id`
- `project_id`
- `revision`
- `status`
- `status_label`
- `bad_channels`
- `bad_segments`
- `annotation_actions`
- `saved_preview_segments`
- `created_at`
- `updated_at`

### 2.4 PreviewSegment

Purpose:

- saved evidence of a selected window and its preview state.

Key fields:

- `segment_id`
- `plan_id`
- `plan_revision`
- `start_sec`
- `duration_sec`
- `channels`
- `display_sfreq`
- `filter_preview`
- `metadata_json`
- `display_data_json`
- `raw_window_data`
- `figure_svg`
- `figure_png`

### 2.5 AnalysisTask

Purpose:

- one run of one analysis method.

Key fields:

- `task_id`
- `project_id`
- `file_id`
- `module_id`
- `workflow_id`
- `parameters`
- `normalized_parameters`
- `status`
- `status_label`
- `started_at`
- `completed_at`
- `error_code`
- `error_message`

### 2.6 Artifact

Purpose:

- generated output that can be listed or downloaded.

Key fields:

- `artifact_id`
- `task_id`
- `kind`
- `path`
- `sha256`
- `created_at`

### 2.7 Report

Purpose:

- packaged user-deliverable result set.

Key fields:

- `report_id`
- `task_id`
- `project_id`
- `package_path`
- `status`
- `created_at`

### 2.8 Account / wallet / invoice objects

Purpose:

- support customer billing and service operations.

Key fields:

- `account_id`
- `email`
- `name`
- `organization_name`
- `balance`
- `invoice_state`
- `notification_state`
- `security_state`

## 3. Display policy

- Display labels must be translated into user language.
- Raw internal enums are implementation details.
- Fields that do not help the current user task should stay hidden by default.
