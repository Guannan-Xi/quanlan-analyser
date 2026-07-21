# QuanLan Analyser Product Architecture

## Positioning

QuanLan Analyser V1 is a research EEG analysis platform. It helps research users organize projects, upload EEG files, inspect metadata, run PSD/ERP analyses, and download reproducible result packages.

It is not a clinical diagnosis product.

## Layers

### Frontend

- Project pages
- Upload pages
- Parameter forms
- Task progress
- Figure and table display
- Report download

### Backend API

- Users, projects, subjects, sessions, EEG files, tasks, artifacts, and reports
- File upload
- Metadata extraction
- Analysis task creation
- Task status query

### Worker

- Executes metadata, preprocessing, PSD, ERP, and report jobs
- Records generated artifacts and reproducibility files

### EEG Core

- MNE readers and metadata wrappers
- Preprocessing
- PSD
- ERP
- Time-frequency analysis
- Statistics
- HTML reports
- Workflow schemas and runners

## V1 API Surface

```text
GET  /api/health

POST /api/projects
GET  /api/projects
GET  /api/projects/{project_id}

POST /api/projects/{project_id}/subjects
GET  /api/projects/{project_id}/subjects

POST /api/eeg/upload
GET  /api/eeg/files/{file_id}
GET  /api/eeg/files/{file_id}/metadata

GET  /api/templates
GET  /api/templates/{template_id}

POST /api/tasks
GET  /api/tasks/{task_id}
GET  /api/tasks/{task_id}/artifacts

GET  /api/artifacts/{artifact_id}/download

POST /api/reports
GET  /api/reports/{report_id}
```

## Core Objects

- User
- Organization
- Project
- Subject
- Session
- EEGFile
- WorkflowTemplate
- AnalysisTask
- Artifact
- Report

## Data Roots

```text
data/uploads/       Original uploaded EEG files.
data/derivatives/   Analysis outputs and reproducibility files.
data/reports/       HTML reports and packaged deliverables.
```

