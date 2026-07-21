---
name: qlanalyser-continue-project-context
description: Use this skill when the user starts a new conversation and wants to continue QLanalyser Online from repository handoff documents without relying on previous chat history.
---

# qlanalyser-continue-project-context

## Purpose

When the user says phrases such as:

- ??? QLanalyser Online ??
- ?? QLanalyser ??
- ?????????
- ??????
- ???? Pilot ??
- ?? AI_HANDOFF_CURRENT ??
- ???????

this skill helps the assistant or Codex restore the current QLanalyser Online project context from repository documents.

This skill does not assume access to previous chat history.

The source of truth is the project repository documentation, especially:

- `docs/AI_HANDOFF_CURRENT.md`
- `docs/PROJECT_STATUS.md`
- `docs/TASK_LOG.md`
- `docs/DECISIONS.md`

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

1. Read repository context in this order:
   - `AGENTS.md`
   - `docs/AI_HANDOFF_CURRENT.md` if present
   - `docs/PROJECT_STATUS.md`
   - `docs/TASK_LOG.md`
   - `docs/DECISIONS.md`
   - relevant README or deployment docs only when needed
2. Summarize the current project state in the assistant's own words.
3. Identify the most important current risks and constraints.
4. Recommend one small next Codex task that can be implemented and verified safely.
5. Preserve the platform boundary: research data management and analysis assistance only; no clinical diagnosis claims.
6. Keep the product name as `QLanalyser Online`; treat `Pilot` as the version state.

---

## What This Skill Must Not Do

- Do not assume previous chat history.
- Do not invent project status beyond repository documents.
- Do not request secrets, API keys, passwords, tokens, private keys, or `.env` contents.
- Do not propose broad rewrites before a focused audit.
- Do not modify files unless the user explicitly asks.
- Do not automatically push to GitHub.

---

## Continuation Response Checklist

When continuing the project in a new conversation, respond with:

1. Current project summary.
2. Current goal and product boundary.
3. Most important risks, up to 5.
4. Recently completed tasks, if documented.
5. One recommended next small Codex task.
6. Any missing information that should be audited before implementation.

---

## Git Rules

This skill usually should not modify files.

If the user explicitly asks to update documents:

1. Run `git status`.
2. Run `git diff --stat`.
3. Check for sensitive information.
4. Stage only related files.
5. Commit locally if safe.
6. Do not push.

Suggested commit message if documentation is updated:

`docs(ai): refresh project continuation context`
