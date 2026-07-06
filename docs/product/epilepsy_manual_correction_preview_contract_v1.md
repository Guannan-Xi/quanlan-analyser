# 癫痫样事件人工矫正预览契约 v1

更新时间：2026-07-06

## 定位

本模块用于把 AI 癫痫样事件候选转成可追溯的人工复核层。它不修改算法原始输出，不给出临床诊断，只输出 `research_screening_support_only` 范围内的复核状态、边界修正、证据等级、伪迹原因和审计记录。

## 本地预览文件

- `frontend/epilepsy-review-preview.html`
- `frontend/epilepsy-review-preview.css`
- `frontend/epilepsy-review-preview.js`

当前预览使用 HE 数据特征构造本地候选：`HE-105.edf`、`HE-106.edf`、`HE-118.edf`，4 通道 `EEG1/EEG2/EMG/ACC`，约 70 小时。页面是可移植 UI 原型，后续接真实任务时替换数据适配层即可。

下游报告预览契约见 `docs/product/epilepsy_report_preview_contract_v1.md`。

## 主干集成边界

主干新手流程只负责提供入口和上下文，不承载人工矫正页面的大块 DOM/CSS/状态。

推荐入口：

```text
./epilepsy-review-preview.html?embed=1&task={task_id}&file={file_id}&project={project_id}&plan={plan_id}&rev={revision}&contract={contract_version}&return={encoded_results_url}
```

推荐上下文：

```json
{
  "schema_version": "qlanalyser.epilepsy.manual_correction_preview_context.v1",
  "project_id": "",
  "task_id": "",
  "input_file_id": "",
  "workflow_id": "epilepsy_ml_xgboost",
  "data_preparation_plan_id": "",
  "data_preparation_revision": 1,
  "data_preparation_contract_version": "",
  "epoch_length_sec": 5,
  "api_base": "",
  "results_return_url": "",
  "embed_mode": true,
  "source": "main_beginner_flow"
}
```

## 输出契约

预览导出的 JSON 使用：

```text
schema_version = qlanalyser.epilepsy.manual_correction_preview.v1
review_session_schema_version = epilepsy_review_session.v1
```

核心结构：

```json
{
  "record": {
    "file_id": "",
    "filename": "",
    "duration_sec": 0,
    "sfreq": 1000,
    "channels": ["EEG1", "EEG2", "EMG", "ACC"]
  },
  "summary": {
    "auto_candidates": 0,
    "reviewed": 0,
    "confirmed": 0,
    "rejected": 0,
    "needs_review": 0
  },
  "event_reviews": {},
  "reviewed_events": [],
  "actions": []
}
```

状态映射：

```text
preview kept      -> EpilepsyReviewSession confirmed
preview excluded  -> EpilepsyReviewSession rejected
preview uncertain -> EpilepsyReviewSession needs_review
preview unreviewed -> EpilepsyReviewSession unreviewed
```

人工动作类型：

```text
event_review
review_fields
adjust_event_interval
note_template
undo
```

## 接真实后端的路径

优先复用现有接口：

- `GET /api/epilepsy-workbench/{task_id}/events`
- `GET /api/eeg/files/{file_id}/waveform-window`
- `POST /api/tasks/{task_id}/epilepsy-review-sessions`
- `PATCH /api/epilepsy-review-sessions/{session_id}`
- `POST /api/epilepsy-review-sessions/{session_id}/exports`

报告页只读取复核层，不直接把未复核 AI 候选写成结论。

## 不要耦合

- 不直接读写主干 `state.real`。
- 不复用主干 `.panel`、`.btn`、`.view` 等全局样式名。
- 不把教学 demo、standalone lab sample 目录写死进正式模块。
- 不覆盖 `epilepsy_ml` 原始产物。
- 不使用诊断措辞，统一保持科研筛查边界。
