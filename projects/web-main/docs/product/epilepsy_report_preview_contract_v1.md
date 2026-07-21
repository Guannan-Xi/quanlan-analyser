# 癫痫样事件报告预览契约 v1

更新时间：2026-07-06

## 定位

`epilepsy-report-preview` 是人工复核后的报告预览层。它只读取复核层，不直接把 AI 未复核候选写成报告结论；不修改算法原始产物；不提供临床诊断、治疗或用药建议。

## 本地预览文件

- `frontend/epilepsy-report-preview.html`
- `frontend/epilepsy-report-preview.css`
- `frontend/epilepsy-report-preview.js`

开发态可从 `frontend/epilepsy-review-preview.html` 点击“报告预览”进入。页面会读取：

```text
localStorage["qlanalyser.epilepsy.review_preview.latest"]
```

正式态应改为读取后端 `EpilepsyReviewSession` 导出结果或报告服务产物。

## 输入契约

报告输入必须来自复核层：

```json
{
  "schema_version": "qlanalyser.epilepsy.manual_correction_preview.v1",
  "record": {
    "file_id": "",
    "filename": "",
    "duration_sec": 0,
    "sfreq": 0,
    "channels": []
  },
  "context": {
    "workflow_id": "",
    "task_id": "",
    "input_file_id": "",
    "review_session_id": "",
    "source_algorithm_artifact_id": ""
  },
  "model": {
    "detector_version": "",
    "threshold": null
  },
  "reviewed_events": [],
  "event_reviews": {},
  "actions": []
}
```

`GET /api/epilepsy-workbench/{task_id}/events` 只能作为候选来源，不能直接作为报告结论来源。

## 输出契约

导出的报告预览 JSON 使用：

```text
schema_version = qlanalyser.epilepsy.report_preview.v1
```

核心字段：

```json
{
  "schema_version": "qlanalyser.epilepsy.report_preview.v1",
  "source_review_schema_version": "",
  "non_medical_scope": "research_screening_support_only",
  "record": {},
  "summary": {
    "auto_candidates": 0,
    "reviewed": 0,
    "confirmed": 0,
    "rejected": 0,
    "needs_review": 0,
    "unreviewed": 0,
    "confirmed_rate_per_hour": 0
  },
  "interpretation": "",
  "methods": "",
  "figure_manifest": [],
  "provenance": {},
  "confirmed_events": [],
  "all_reviewed_events": [],
  "actions": []
}
```

## 图表来源规则

当前本地预览的代表波形是合成示意，不是真实 EDF 证据。正式报告必须将 `waveformFigure` 替换为真实来源：

- `GET /api/eeg/files/{file_id}/waveform-window`
- 或 `POST /api/epilepsy-review-sessions/{session_id}/exports` 注册的 evidence package

每个图必须在 `figure_manifest` 中声明：

```json
{
  "id": "waveformFigure",
  "title": "代表事件波形",
  "source": "waveform-window",
  "provenance": "real_edf_window",
  "window_sec": [-10, 20],
  "channels": ["EEG1", "EEG2", "EMG", "ACC"],
  "filter_profile": "preview_0p5_45_notch50",
  "unit": ""
}
```

## 统计口径

- `confirmed`：人工保留候选，可进入负荷统计、代表图和摘要。
- `rejected`：人工排除候选，只进入追溯记录。
- `needs_review`：存疑候选，单列为待确认。
- `unreviewed`：未复核候选，不能写成报告结论。

当 `needs_review + unreviewed > 0` 时，报告状态必须为：

```text
partial_review_draft
```

此时事件负荷只能表述为“已复核人工保留候选负荷”，不能表述为患者或记录的完整事件负荷。

## Methods 最低字段

正式报告至少记录：

- 输入文件、记录时长、采样率、通道。
- 预处理/滤波/参考/窗口参数。
- 候选生成工作流、模型版本、候选阈值。
- 人工复核状态映射。
- 证据等级 A/B/C/X 定义。
- 排除规则：EMG、ACC 体动、电极、饱和、不可判读、重复候选等。
- 统计口径。
- 局限性：无同步视频、无临床标注、4 通道限制、外部验证不足、不能估计敏感性/特异性、不能代表确认或排除发作。

## 避免措辞

不要使用：

- 临床诊断结论
- 确认癫痫
- 排除癫痫
- 发作概率类英文表述
- 临床置信度类英文表述
- 未解释的 positive / negative 表述

建议使用：

- 癫痫样事件候选
- 人工保留候选
- 存疑候选
- 已复核人工保留候选负荷
- 科研筛查支持
