---
name: qlanalyser-conversation-sync
description: Use this skill in QLanalyser Online when architecture, module-design, product-decision, or multi-conversation development context must be fixed into repository documents and summarized for Feishu/GitHub-based collaboration.
---

# QLanalyser Conversation Sync Skill

## Purpose

Use this skill whenever the user asks to:

- 固定本轮对话 / 同步本轮对话 / 记录结论
- 把架构设计、模块详细设计、验收标准写成多个对话都能依据的文档
- 让 GitHub / 仓库文档 / 飞书同步当前设计
- 为其他 Codex、ChatGPT、开发对话生成可执行依据
- 更新软件架构、模块设计、QC/PSD/ERP/TFR/PAC/Connectivity 设计文档

This skill is for QLanalyser Online only.

## Core Rule

The repository is the single source of truth.

- GitHub / repository markdown docs are the canonical development basis.
- Feishu is a review and communication mirror.
- Never treat chat memory, local scratch files, or Feishu comments as canonical unless the conclusion is also written into the repository docs.
- Never claim Feishu has been updated unless a Feishu tool/API call actually succeeds. If no Feishu tool is available, generate a copy-ready Feishu summary instead.

## Information Flow

Convert conversation content into this stable flow:

```text
Conversation
  -> classify content
  -> update canonical repository docs
  -> generate Feishu mirror summary
  -> update handoff/current-status docs
  -> optionally commit locally with qlanalyser-git-guard
```

### Classification

1. Permanent product or architecture decisions
   - Destination: `docs/DECISIONS.md`
   - Examples: source-of-truth rules, login boundary, module lifecycle, public beta boundary.

2. Current project state and next basis for all conversations
   - Destination: `docs/PROJECT_STATUS.md`
   - Include only current facts, active risks, and next tasks.

3. Chronological work record
   - Destination: `docs/TASK_LOG.md`
   - Append a dated entry with scope, files, validation, risks, and next step.

4. Current cross-conversation handoff
   - Destination: `docs/AI_HANDOFF_CURRENT.md`
   - Keep it short enough to paste into a new conversation.

5. Architecture design
   - Destination: `docs/architecture/*.md`
   - Use `docs/templates/architecture_design_doc.md` when creating a new design doc.

6. Module detailed design
   - Destination: `docs/modules/*.md`
   - Use `docs/templates/module_design_doc.md` when creating a new module design doc.

7. Feishu mirror / meeting summary
   - Destination: copy-ready block generated from `docs/templates/feishu_sync_summary.md`
   - If the project later has a Feishu API integration, use it after confirming credentials and target document.

## Operating Procedure

Before editing:

1. Run `git status --short --branch`.
2. Run `git diff --stat`.
3. Identify unrelated or untracked files and do not touch them.
4. Decide whether this is:
   - design sync only,
   - module spec creation,
   - architecture spec creation,
   - or task handoff.

During editing:

1. Summarize decisions rather than copying the whole chat verbatim.
2. Keep secrets, API keys, private customer data, raw EEG data, and local runtime paths out of docs unless they are already public project paths.
3. Write decisions in actionable form: owner, affected modules, acceptance criteria, and open questions.
4. Prefer small focused docs over a giant mixed document.
5. If the user asks for a demo or implementation, still keep design docs canonical before code changes.

After editing:

1. Run lightweight validation appropriate for docs:
   - `git diff --check`
   - `python scripts/check_no_mojibake.py` if text encoding changed
2. Run `git status --short --branch`.
3. Report changed files and unresolved questions.
4. If the task is complete and safe, use `qlanalyser-git-guard` rules for a focused local commit.
5. Do not push unless the user explicitly confirms.

## Required Output Format

When the skill is used, end with:

```markdown
## 对话同步结果

### 1. 已固化到仓库的内容
- ...

### 2. GitHub / 仓库唯一依据
- ...

### 3. 飞书同步摘要
```text
可复制到飞书的摘要
```

### 4. 修改文件
- `path`：原因

### 5. 验证结果
- ...

### 6. 下一步建议
- ...
```

## Recommended Local Commit Message

For this skill itself or sync-only changes:

```text
docs(ai): add conversation sync workflow
```

For later architecture docs:

```text
docs(architecture): add <topic> design basis
```

For later module docs:

```text
docs(module): add <module> detailed design
```
