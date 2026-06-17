# EEG Upload & Storage Performance Playbook

## Product Goal

Make large EEG uploads feel reliable on ordinary lab networks and fast on high-throughput institutional networks. The application API must not become the data bottleneck.

## Critical Path

1. Browser reads file headers locally.
2. Browser calculates file fingerprint and chunk SHA-256 in Web Workers.
3. API creates upload session and returns pre-signed multipart URLs.
4. Browser uploads chunks directly to object storage with adaptive concurrency.
5. API records completed parts and verifies chunk checksums.
6. Object storage completes multipart upload.
7. Worker indexes metadata, validates BIDS, creates QC preview, and stores manifest.
8. Analysis jobs read objects by immutable content hash and pipeline version.

## Frontend Optimization

- Use `File.slice()` to avoid loading whole EDF/SET/FIF files into memory.
- Hash chunks in Web Workers so the UI thread stays responsive.
- Keep a bounded upload queue; never start unlimited fetch requests.
- Persist upload state in IndexedDB: upload id, part numbers, ETags, hashes, size, modified time.
- Retry failed chunks with exponential backoff and jitter.
- Pause/resume by stopping the queue, not by discarding completed chunks.
- Use adaptive concurrency:
  - 2-3 workers for unstable 10-30 Mbps networks.
  - 4 workers for ordinary 100 Mbps lab networks.
  - 6-8 workers for 500 Mbps+ networks.
- Use adaptive chunk size:
  - 16-32 MB for poor networks.
  - 64 MB for balanced networks.
  - 128 MB for high-throughput uploads.

## Backend Optimization

- API only signs upload parts, stores metadata, and completes multipart sessions.
- File bytes go browser -> object storage directly.
- Use Redis for active upload progress and locks.
- Use PostgreSQL for durable file manifests, project ACL, BIDS index, billing duration.
- Use object lifecycle rules for partial multipart cleanup.
- Run metadata extraction and BIDS validation asynchronously after upload completion.
- Store derived figures, reports, and statistics under pipeline-versioned derivative paths.

## Storage Layout

```text
sourcedata/{sha256}/{original_filename}
bids/sub-*/ses-*/eeg/*
derivatives/{pipeline_version}/{analysis_id}/
publication/{analysis_id}/
```

## Integrity

- Chunk SHA-256 before upload.
- ETag or checksum confirmation after upload.
- Whole-file SHA-256 before analysis.
- Manifest includes file size, hash, format, event table hash, pipeline version, and user id.

## Performance Targets

- Upload should use 80-90% of available uplink on stable networks.
- Interrupted uploads should lose zero completed chunks.
- API server large-file bandwidth should remain near zero.
- Metadata preflight should complete before full upload whenever possible.
- Completed publication packages should be immutable unless explicitly regenerated.

## Storage Cost Controls

- Deduplicate identical raw files by whole-file hash.
- Keep raw data hot while the project is active.
- Move old derivatives and publication packages to warm/cold storage by lifecycle rule.
- Clean abandoned multipart sessions after 24 hours.
- Keep subject-level CSV and manifests small, hot, and quickly searchable.
