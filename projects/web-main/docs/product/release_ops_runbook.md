# QLanalyser Release Operations Runbook

Date: 2026-06-22

## 1. Purpose

This runbook explains how to start, check, review, and roll back a product build.

## 2. Preflight

Before review or release:

- confirm the target branch and workspace;
- confirm the current doc set is updated;
- confirm UTF-8 text checks pass;
- confirm acceptance scripts are available;
- confirm no secrets or production-only data are exposed.

## 3. Service startup

Typical release workflow:

1. Start backend.
2. Start frontend.
3. Check backend health.
4. Open the review URL.
5. Verify login and main workflow entry.
6. Run the acceptance set.

## 4. Smoke checks

Minimum smoke checks:

- health endpoint returns success;
- frontend opens;
- project page renders;
- upload action exists;
- one real user path can be clicked through;
- error state is visible when a prerequisite is missing.

## 5. Evidence collection

Collect:

- screenshots;
- browser trace if available;
- JSON result files;
- log excerpts;
- release checklist output;
- artifact paths.

## 6. Rollback

Rollback must be documented before a risky release.

At minimum record:

- previous version or commit;
- rollback command or action;
- data impact scope;
- whether user-created records are preserved;
- whether reports remain auditable after rollback.

## 7. Operational guardrails

- Do not hide failed startup behind a green page.
- Do not call a preview build production-ready without evidence.
- Do not keep release evidence scattered across page notes.
- Keep review URLs, health URLs, and demo accounts in the current status doc or the latest evidence package.
