---
name: qlanalyser-github-baseline-sync
description: Use this skill for every QLanalyser Online development/design task before starting work and again before finishing, committing, and pushing, so all parallel conversations use the latest GitHub baseline and canonical architecture/version/module docs.
---

# QLanalyser GitHub Baseline Sync Skill

## Purpose

Use this skill for every QLanalyser Online task that may change code, architecture docs, module design docs, tests, deployment docs, or project handoff docs.

This skill protects parallel development conversations from working on stale assumptions and makes a clean post-task push the expected finish path.

It must run:

1. At task start, before deep reading or editing.
2. Before staging or committing.
3. Before pushing.
4. After a completed task, push the committed work when the remote check is clean and the branch is only ahead of `origin/main`; if there is any difference, conflict, or overwrite risk, stop and ask the user first.

## Core Rule

GitHub `origin/main` plus the repository canonical docs are the baseline.

Every development conversation must refresh and inspect this baseline before using it as a foundation.

Canonical docs that must be read or rechecked for architecture/module work:

- `AGENTS.md`
- `docs/AI_CONVERSATION_SYNC.md`
- `docs/AI_HANDOFF_CURRENT.md`
- `docs/DECISIONS.md`
- `docs/PROJECT_STATUS.md`
- `docs/architecture/system_architecture.md`
- `docs/architecture/version_detailed_design.md`
- `docs/modules/analysis_modules_design_matrix.md`
- The specific module or architecture document related to the task.

## Start-of-Task Procedure

Run:

```powershell
git fetch origin
git status --short --branch
git rev-parse HEAD
git rev-parse origin/main
git log --oneline --decorate -5 --all
```

Then classify the local branch state:

- Up to date: local `main` equals `origin/main`.
- Ahead only: local has commits not pushed; continue only if those commits are intentional and known to the user.
- Behind: stop and ask before pulling, merging, rebasing, or overwriting local files.
- Diverged: stop and ask; do not merge, rebase, reset, or force push automatically.
- Local uncommitted changes: identify them. Do not overwrite unrelated or user-owned files.

If `git fetch origin` fails because of network, report the failure. Continue only if the user explicitly accepts working from the last known `origin/main` reference.

## Required Baseline Reading

After the GitHub check, read the canonical docs relevant to the task.

For all architecture/module/version work, at minimum inspect:

```text
docs/architecture/system_architecture.md
docs/architecture/version_detailed_design.md
docs/modules/analysis_modules_design_matrix.md
docs/DECISIONS.md
docs/PROJECT_STATUS.md
```

If these docs have changed on `origin/main` compared with local assumptions, update the plan before editing.

## Before Commit Procedure

Before staging or committing, run again:

```powershell
git fetch origin
git status --short --branch
git diff --stat
git diff --name-only
git diff --check
```

Then compare the branch state.

If local is behind or diverged:

- Stop.
- Explain what changed locally and remotely.
- Ask the user whether to pull/rebase/merge, resolve manually, or continue on a branch.
- Do not stage or commit until the user decides, unless the user explicitly asks for a local WIP commit before reconciliation.

If remote has changed in canonical docs during the task:

- Stop and report which canonical docs changed.
- Ask whether to refresh the design basis before continuing.

## Commit Rule

Use `qlanalyser-git-guard` after this skill passes.

Do not use `git add .` in mixed worktrees. Stage exact files only.

## Push Procedure

Before push, run:

```powershell
git fetch origin
git status --short --branch
git log --oneline --decorate -5
```

After a completed task, the expected finish path is commit then push.

Push only when all are true:

- Current branch is intended for push.
- Local branch is ahead of `origin/main` only, not behind or diverged.
- Staged/committed files are related to the task.
- No unrelated untracked files are being pushed.
- The task policy or user instruction expects push after completion. If there is any uncertainty, ask once before pushing.

Never run:

```powershell
git push --force
git push -f
git reset --hard origin/main
```

unless the user gives an explicit, task-specific instruction and the risk has been explained. Even then, prefer safer alternatives.

## Conflict / Difference Questions

When there is a local-vs-GitHub difference, ask the user in plain language:

- GitHub has newer commits. Should I update this workspace first, or keep working from the current local state?
- This file changed both locally and remotely. Should I merge carefully, keep local, keep GitHub, or pause for manual review?
- The architecture/version/module design docs changed on GitHub. Should I re-read and revise the implementation plan before editing?
- After local commit, should I push now, or keep it local?

Do not phrase the choice as "overwrite" unless that is genuinely what would happen. If an overwrite is possible, say exactly which files would be overwritten.

## Required Handoff Fields

Every task that uses this skill must report:

```markdown
### GitHub baseline check
- `git fetch origin`: passed/failed
- Local HEAD:
- origin/main:
- Branch relation: up to date / ahead / behind / diverged
- Canonical docs checked:
- Remote changes during task: yes/no

### Conflict / overwrite risk
- Risk:
- User decision needed:
```

## Interaction With Other Skills

- Use this before `qlanalyser-git-guard`.
- Use this with `qlanalyser-conversation-sync` when architecture/module decisions are updated.
- Use this with `qlanalyser-continue-project-context` when starting from a new conversation.
