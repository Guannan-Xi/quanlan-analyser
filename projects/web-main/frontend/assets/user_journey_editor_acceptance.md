# User Journey: 1000 RMB, 10 EEG Files, One Paradigm, Editor Acceptance

## Persona

- User: first-time EEG researcher
- Budget: 1000 RMB
- Data: 10 EEG files
- Question: analyze one paradigm and produce publication-ready figure/data
- Constraint: the user does not know which analysis method to choose

## End-to-End Flow

1. Create project: `P300 oddball pilot`
2. Upload 10 EEG files through resumable multipart upload
3. System reads headers and event table
4. User selects research interest: `Oddball / P300`
5. System recommends method: event-locked ERP, target-standard contrast, P300 280-420 ms, posterior channels
6. User accepts default workflow
7. Platform runs QC, epoching, baseline, averaging, subject-level metrics
8. Platform runs paired t test, FDR correction, and cluster permutation
9. Platform renders publication figure and exports CSV/manifest/methods text
10. User sends package to editor
11. Editor checks figure, statistics, methods, raw subject-level table, and reproducibility manifest
12. Editor accepts the technical package as complete

## Budget

- Billing rule: 1 RMB per hour of raw EEG recording
- Assumption: 10 EEG files, each 1.5 hours
- Billable hours: 15 h
- Analysis charge: 15 RMB
- Remaining balance: 985 RMB
- Storage and publication export: free in this prototype scenario

## If the User Does Not Know the Method

The platform asks:

1. What type of event or task do you have?
2. Are there stimulus labels such as target/standard, congruent/incongruent, left/right, face/object?
3. Is the outcome time-locked to events, frequency-tagged, continuous resting-state, or sleep-stage related?
4. Do you need a figure, a statistical table, or both?

For `target` and `standard` events, the platform recommends:

- ERP analysis
- Epoch window: -0.2 to 0.8 s
- Baseline: -0.2 to 0 s
- Main contrast: target minus standard
- Main metric: P300 mean amplitude, 280-420 ms
- Suggested channels: Pz, P3, P4
- Statistics: subject-level paired t test + FDR; optional cluster permutation
- Required exports: ERP figure, subject-level CSV, statistics summary, methods snippet, manifest

## Editor Acceptance Checklist

- Figure has clear axes, units, legend, and panel labels
- Statistics are performed on subject-level data
- Multiple comparisons are corrected or justified
- QC metrics are reported
- Methods include preprocessing, epoching, baseline, windows, statistics, software versions
- CSV and manifest are provided for reproducibility
