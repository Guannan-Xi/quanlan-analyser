# High-Concurrency EEG SaaS Playbook

## Non-negotiable Architecture Decisions

1. Upload bytes bypass the application API.
2. All long-running MNE/EEGLAB-equivalent jobs run in workers, never in request handlers.
3. Every worker task is idempotent and writes an immutable input/output manifest.
4. Queues are separated by workload type so report rendering cannot block upload preflight.
5. Tenants have explicit concurrency limits and fair-share scheduling.

## Workload Isolation

- `upload-preflight`: short metadata reads, file fingerprint registration, upload signing.
- `bids-validation`: BIDS metadata validation and event table validation.
- `qc-preview`: fast visual previews for user confidence.
- `preprocessing-cpu`: filtering, ICA setup, artifact rejection, epoching.
- `time-frequency-cpu`: Morlet/multitaper workloads.
- `source-localization-heavy`: expensive inverse/source workflows.
- `statistics`: subject-level aggregation, t tests, FDR, permutation tests.
- `figure-render`: PNG/PDF/HTML report rendering.
- `publication-package`: zip packaging and manifest writing.

## Backpressure Rules

- Keep upload signing responsive even when analysis queues are full.
- If worker queues grow, show estimated wait time instead of accepting unlimited jobs.
- Apply per-project and per-tenant active job caps.
- Prefer queue delay over uncontrolled memory pressure.
- Degrade optional previews before degrading uploads or metadata integrity.

## Autoscaling Signals

- API: p95 latency, RPS, CPU, connection pool wait.
- Upload signing: signed URL RPS, Redis p95 latency.
- Analysis workers: queue depth, oldest job age, average job runtime.
- Render workers: render queue depth and image/PDF generation latency.
- Storage: PUT/GET throughput, error rate, multipart completion latency.

## Database Strategy

- PostgreSQL stores metadata only, never raw EEG bytes.
- Use read replicas for dashboards and audit views.
- Keep write paths narrow: upload sessions, manifests, task state, billing duration.
- Partition audit logs and task events by date or organization.
- Use connection pooling; workers should not open unlimited database connections.

## Reliability Strategy

- Every upload session has an idempotency key.
- Every analysis task has an input manifest hash and output manifest hash.
- Dead-letter failed jobs with exact error, version, and retry count.
- Store partial progress where possible, especially for long batch jobs.
- Do not delete raw data automatically when derivatives fail.

## Performance Targets

- API p95 < 200 ms for metadata endpoints under normal load.
- Upload signing p95 < 100 ms.
- Queue admission decision < 500 ms.
- Dashboard reads from cache/read replicas.
- Object storage direct upload should use 80-90% of measured uplink.
- Worker utilization target 65-85%, leaving room for burst and retries.
