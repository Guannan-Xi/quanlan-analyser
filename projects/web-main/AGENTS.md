# QLanalyser Online Agent Rules

Brand/product: QLanalyser Online, QuanLan BrainScience. v0.1 Pilot MVP for free customer trials. Research data management and EEG analysis aid only; results are not clinical diagnosis.

## Product Scope
- Core flow: login -> project -> upload EEG -> create analysis task -> background analysis -> task status -> results -> report ZIP.
- Priority: login, dashboard, project/file metadata, EEG upload, Metadata/QC, resting PSD, task status/failure reason, HTML/ZIP reports, admin entry, basic logs/deploy backup.
- Not now: self signup, complex multi-tenant/RBAC, payment, PAC/connectivity/TFR/ML, clinical diagnosis, Kubernetes, microservices, complex PDF layout.

## Development Rules
- One small clear task at a time; no full rewrite or broad refactor.
- Avoid unnecessary dependencies. Keep product name exactly `QLanalyser Online`.
- Do not store raw EEG files in DB. Long analysis tasks must not block HTTP requests.
- Persist complete analysis parameters and logs.
- After each task, update `docs/PROJECT_STATUS.md` and `docs/TASK_LOG.md`; record product/architecture decisions in `docs/DECISIONS.md`.

## QGCS Project Overrides
- P0 audit only for hard boundaries: non-medical wording, data integrity, and functional crash. Out-of-scope features do not trigger P0 requirements.
- Single-file changes <= 6 lines can be handled directly by Codex; larger/multi-file changes follow global routing.
- This is a monolith (FastAPI + static frontend); Sprint Board multi-worker routing is optional.
- Keep full adversarial review, but during v0.1 use single-model compliance scan instead of GPT-5.5 + DeepSeek N-Fold; re-enable dual-model N-Fold after commercialization.
- User-level adversarial acceptance must follow `docs/product/qlanalyser_user_level_e2e_adversarial_review_standard_20260702.md`; static scans do not replace E2E acceptance.

## Git And Handoff
- Commit after each small task when requested/appropriate. Never push automatically; never force-push. Stop and report conflicts.
- Finish notes should include: goal, completed work, changed files, run/test steps, results, risks, unfinished items, next step.
- Before development, fetch/check `origin/main` when GitHub baseline matters; check again before commit if remote drift is likely.

## Spike Module Status (moved out)

Spike sorting and analysis is no longer an internal `web-main` module. On
2026-07-22 it was briefly merged in, then reversed the same day back to an
independent top-level pre-research project at `projects/spike-analysis`
(workspace root), following the same lifecycle as `qeeg-64ch-research`. See
workspace-root `AGENTS.md`/`README.md` for current ownership. If a Spike
method is later promoted into the core platform, it goes through
`backend/api/`, `backend/services/`, and `worker/tasks/` at that time — do not
create a sibling application or duplicate service entry point.
