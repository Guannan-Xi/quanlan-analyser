# QLanalyser Error Code Catalog

Date: 2026-06-22

## 1. Purpose

This catalog keeps user-facing error language consistent.

## 2. Error style rules

- The message should say what happened.
- The message should say what the user can do next.
- The message should not expose unnecessary internal implementation details.
- The message should use normal product language.

## 3. Core categories

### 3.1 Project errors

- project not found
- project archived
- project deletion blocked
- project update conflict

### 3.2 Data file errors

- file not found
- unsupported format
- upload failed
- metadata unreadable
- data file locked or unavailable

### 3.3 Preparation errors

- no project selected
- no file selected
- no preview window selected
- plan revision conflict
- bad segment invalid
- bad channel invalid

### 3.4 Analysis errors

- prerequisite missing
- events missing
- unsupported method in current mode
- parameter invalid
- task execution failed

### 3.5 Report and artifact errors

- report package not ready
- artifact download failed
- manifest missing
- result unavailable

### 3.6 Account and billing errors

- account not authenticated
- balance unavailable
- invoice submission failed
- notification unavailable

## 4. Suggested message format

Preferred pattern:

```text
发生了什么 + 为什么不能继续 + 下一步怎么做
```

Example style:

- “未选择项目，请先选择一个项目后再查看数据。”
- “当前文件不支持该格式，请重新上传 EDF 或受支持格式。”
- “准备方案版本已更新，请先加载最新版本再保存。”

## 5. Update rule

Whenever a new failure message appears in the UI:

- add the category here;
- add the technical mapping in the API contract inventory if needed;
- add the scenario to the acceptance matrix;
- add a note in the page change log if it affects visible copy.
