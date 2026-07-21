---
name: qlanalyser-close-chat-handoff
description: Use this skill when the user wants to end the current QLanalyser Online conversation, generate or refresh project handoff documents, and safely continue in a new ChatGPT/Codex conversation.
---

# qlanalyser-close-chat-handoff

## Purpose

When the user says phrases such as:

- ????????
- ????????
- ??????
- ??????
- ?? AI ??
- ??????????

this skill updates the project handoff documents so the user can safely continue QLanalyser Online in a new ChatGPT conversation.

This skill is for QLanalyser Online only.

---

## Project Identity

Product name:

- QLanalyser Online

Version:

- QLanalyser Online v0.1 Pilot

Brand:

- ?????<sup>?</sup>
- QuanLan BrainScience<sup>?</sup>

Platform boundary:

- ?????????????????????????????

Pilot is a version state, not the product name.

---

## What This Skill Should Do

1. Read the current project documentation before summarizing:
   - `docs/AI_HANDOFF_CURRENT.md` if it exists
   - `docs/PROJECT_STATUS.md`
   - `docs/TASK_LOG.md`
   - `docs/DECISIONS.md`
   - `AGENTS.md`
2. Inspect the current repository state:
   - `git status`
   - `git diff --stat`
   - `git diff --name-only`
3. Update or create `docs/AI_HANDOFF_CURRENT.md` as the current continuation document.
4. Update `docs/PROJECT_STATUS.md` and `docs/TASK_LOG.md` with the latest task state.
5. Update `docs/DECISIONS.md` only if a real product, architecture, naming, or workflow decision changed.
6. Check that no sensitive information is included in the handoff.
7. Use `qlanalyser-git-guard` rules before committing.
8. Do not push automatically.

---

## What This Skill Must Not Do

- Do not modify EEG analysis algorithms.
- Do not modify business logic unless the user explicitly asks in a separate task.
- Do not introduce new dependencies.
- Do not ask the user to paste API keys, tokens, passwords, private keys, or server credentials.
- Do not assume access to old chat history.
- Do not call Pilot the product name.
- Do not claim clinical diagnostic use.
- Do not automatically push to GitHub.

---

## Handoff Document Structure

When updating `docs/AI_HANDOFF_CURRENT.md`, include these sections:

### 1. Project Identity

Summarize product name, version, brand, platform boundary, and repository path.

### 2. Current Goal

Describe the current QLanalyser Online v0.1 Pilot goal in plain language.

### 3. Current Technical Stack

Summarize frontend, backend, data storage, EEG analysis modules, worker/task model, and local run commands.

### 4. Current Repository State

Include branch, remote status, and a concise summary of modified/untracked files without exposing secrets.

### 5. Completed Capabilities

Summarize currently verified product capabilities.

### 6. Known Gaps and Risks

Keep the list practical. Include current known risks such as:

- authentication/authorization not fully verified
- long EEG analysis should not block API
- results must be traceable
- failed tasks must be explainable
- Pilot is not product name
- PAC is experimental
- PSD and Bandpower should be planned as one clear module where possible

### 7. Important Decisions

Summarize decisions from `docs/DECISIONS.md`.

### 8. Operating Rules for the Next Conversation

Include rules for small tasks, small verification, focused commits, no force push, and no credential sharing.

### 9. Recently Completed Tasks

Summarize the latest 3-5 completed tasks and test results.

### 10. Current Next Tasks

List up to 5 clear next tasks.

### 11. New ChatGPT Conversation Startup Prompt

Include a copy-paste prompt the user can paste into a new ChatGPT conversation.

---

## New ChatGPT Startup Prompt Template

At the end of `docs/AI_HANDOFF_CURRENT.md`, include:

```text
??????? QLanalyser Online v0.1 Pilot?

???????????????????? Codex ???????

?????
1. ?????????????????
2. ?????????????
3. ????????????????? Codex ?????
4. ????????????
5. ????????????????????
6. ????? API key?env????token??????????
7. ??????????? Codex ???
8. ??????? QLanalyser Online v0.1 Pilot?
9. ?????? QLanalyser Online?
10. ???????????????????????

???????
1. ???????????????
2. ???????? 5 ????
3. ?????????? Codex ? 1 ?????

??????????
```

---

## Git Rules

Use git guard:

1. Run `git status`.
2. Run `git diff --stat`.
3. Check for sensitive information.
4. Stage only related documentation and skill files.
5. Commit locally if safe.
6. Do not push.

Suggested commit message:

`docs(ai): add project handoff skills`
