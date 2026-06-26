# QLanalyser API Contract Inventory

Date: 2026-06-22

## 1. Contract purpose

This document is the product-facing map of the backend contract.

It is meant to keep frontend, backend, acceptance scripts, and release evidence aligned.

## 2. Contract rules

- Every user-visible action must have a backend contract or a documented disabled state.
- Every contract response must include user-meaningful status fields, not only storage enums.
- Every destructive action must have clear error and confirmation behavior.
- Every new field must be reflected in the data dictionary and acceptance matrix.

## 3. Core endpoint groups

### 3.1 Health and readiness

- `GET /api/health`

Purpose:

- service liveness;
- readiness smoke;
- release gate probe.

### 3.2 Project management

- `POST /api/projects`
- `GET /api/projects`
- `GET /api/projects/{project_id}`
- `PATCH /api/projects/{project_id}`
- `POST /api/projects/{project_id}/archive`
- `DELETE /api/projects/{project_id}`

Expected response themes:

- `project_id`
- display name
- status label
- file count
- current project hint

### 3.3 Data file management

- `POST /api/eeg/upload`
- `GET /api/eeg/files/{file_id}`
- `GET /api/eeg/files/{file_id}/metadata`
- `PATCH /api/eeg/files/{file_id}`
- `DELETE /api/eeg/files/{file_id}`

Expected response themes:

- file id;
- project id;
- file name;
- format;
- sampling rate;
- channel count;
- business status label;
- user note.

### 3.4 Data preparation

- `POST /api/eeg/files/{file_id}/data-preparation-plan`
- `GET /api/eeg/files/{file_id}/data-preparation-plan`
- `GET /api/eeg/files/{file_id}/data-preparation-plans`

Expected response themes:

- plan id;
- revision;
- status label;
- bad channels;
- bad segments;
- annotation actions;
- preview evidence references.

### 3.5 Preview segments

- `POST /api/eeg/files/{file_id}/preview-segments`
- `GET /api/eeg/files/{file_id}/preview-segments`
- `GET /api/eeg/files/{file_id}/preview-segments/{segment_id}`
- `DELETE /api/eeg/files/{file_id}/preview-segments/{segment_id}`

Expected response themes:

- segment id;
- base plan revision;
- saved preview metadata;
- artifact references;
- conflict error when revision is stale.

### 3.6 Tasks, artifacts, reports

- `POST /api/tasks`
- `GET /api/tasks/{task_id}`
- `GET /api/tasks/{task_id}/artifacts`
- `GET /api/artifacts/{artifact_id}/download`
- `POST /api/reports`
- `GET /api/reports/{report_id}`

Expected response themes:

- task id;
- module id;
- workflow id;
- status label;
- artifact list;
- report package references;
- warnings / limitations.

### 3.7 Account, wallet, invoice

Product workbenches may consume:

- wallet summary;
- recharge state;
- invoice request state;
- inbox/notification state.

These should stay out of the main project workbench unless the user explicitly opens the account area.

## 4. Error style

Errors must be:

- human-readable;
- actionable;
- consistent with the UI wording;
- aligned to the acceptance matrix.

Do not expose raw internal stack details to ordinary users.
