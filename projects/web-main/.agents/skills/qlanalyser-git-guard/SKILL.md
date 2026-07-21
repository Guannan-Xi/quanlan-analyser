---
name: qlanalyser-git-guard
description: Use this skill after every small QLanalyser Online development task to verify git status, prevent secret leaks, update handoff docs, create a focused local commit, and prepare for optional push. Do not use it for unrelated repositories.
---

# QLanalyser Git Guard Skill

## Purpose

This skill enforces disciplined Git workflow for QLanalyser Online.

Every completed small task should end with:

1. status check
2. secret check
3. relevant tests or verification
4. documentation update
5. focused local commit
6. handoff summary

Do not push unless the user explicitly confirms.

## Repository

Expected project:
`QLanalyser Online`

Expected remote:
`https://github.com/Guannan-Xi/quanlan-analyser.git`

## Before committing

Run or inspect:

```powershell
git status
git diff --stat
git diff --name-only
git remote -v
```

Check that no unrelated files are included.

Do not commit:

- `.env`
- `.env.local`
- API keys
- tokens
- passwords
- private certificates
- local logs
- temporary screenshots
- `.ai/`
- large generated files unless explicitly requested

If suspicious secrets are found, stop and report file path and variable name only. Do not print the secret value.

## Required checks before commit

For every task, do at least one of:

- Run the relevant automated tests if available.
- Run the app or affected service if applicable.
- For docs-only tasks, confirm that only documentation files changed.
- For UI-only tasks, confirm affected page can still load or provide clear manual verification steps.

If tests fail:

- Do not commit as completed.
- Report the failure.
- Suggest the smallest fix.

## Documentation update

After each task, update:

- `docs/PROJECT_STATUS.md`
- `docs/TASK_LOG.md`

Update `docs/DECISIONS.md` only if product or architecture decisions changed.

## Commit rules

Use small focused commits.

Commit message format:

```text
type(scope): short summary
```

Allowed types:

- `docs`
- `feat`
- `fix`
- `refactor`
- `test`
- `chore`
- `style`

Before committing, stage only relevant files:

```powershell
git add path/to/file1 path/to/file2
git status
git diff --cached --stat
git commit -m "type(scope): summary"
```

Do not use `git add .` if there are unrelated or suspicious files.

## Push rules

Do not push automatically.

After commit, ask the user:

> 本次本地 commit 已完成。是否需要 push 到 GitHub 远程仓库？

If the user confirms, run:

```powershell
git fetch origin
git status -sb
```

If the branch is behind, diverged, or has remote history that is not already integrated, stop and ask for confirmation before merge, rebase, or push.

If the branch is not `main`, report the current branch and ask before changing branch name.

Never run:

```powershell
git push --force
git push -f
```

## Task handoff

After every task, output:

```markdown
## 本次任务交接

### 1. 任务目标
...

### 2. 已完成内容
...

### 3. 修改文件
...

### 4. Git 状态
- 当前分支：
- 当前 remote：
- 本次 commit hash：
- 是否已 push：否

### 5. 远程仓库检查结果
...

### 6. 是否发现敏感信息
...

### 7. 测试结果
...

### 8. 风险点
...

### 9. 需要我确认的问题
...

### 10. 下一步建议
...
```
