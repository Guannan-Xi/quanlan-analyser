# QLanalyser Epilepsy / Sleep Terminology Contract - 2026-06-29

Status: active terminology baseline for customer-facing UI and acceptance tests.

## Purpose

QLanalyser supports both epilepsy-like event analysis and sleep staging workflows. These workflows share waveform, epoch, spectrogram, and manual review infrastructure, but their product language must stay separate.

The epilepsy module must not be described as "staging" in Chinese customer-facing copy. "Staging / 分期" belongs to sleep staging.

## Epilepsy-like Event Analysis Terms

Use these terms for epilepsy workflows:

- 癫痫样事件初筛
- 候选事件检测
- 查看候选事件
- 人工复核
- 事件修正
- 保存复核版本
- 导出结果
- Stage_Code / epoch 结果
- 癫痫样候选事件
- 波形证据
- 时频证据

Recommended button labels:

- 开始初筛
- 查看候选事件
- 进入人工复核
- 保存复核版本
- 导出结果

Allowed English terms:

- Epilepsy-like Event Screening
- Candidate Event Detection
- Manual Review
- Event Correction
- Review Revision
- Export Results

## Sleep Terms

Use these terms for sleep workflows:

- 睡眠分期
- 分期结果
- 分期图
- 人工校正
- 保存分期复核版本
- Hypnogram
- Sleep stage

## Forbidden or Deprecated Epilepsy Terms

Do not use these in epilepsy customer-facing UI:

- 癫痫分期
- 癫痫样事件分期
- 癫痫样事件分期分析台
- 开始分期
- 初筛/分期
- 分期波形

If a technical document discusses shared infrastructure, use "Stage_Code / epoch result" or "discrete label strip" instead of implying clinical or sleep-style staging.

## Product Boundary

Epilepsy output is a research-screening and manual-review support layer. It is not diagnosis, seizure confirmation, treatment recommendation, clinical triage, or medical decision support.

## Traceability / Acceptance Mapping

| Area | Required terminology |
| --- | --- |
| Analysis entry | 进入癫痫样事件分析台 / 进入癫痫样事件初筛 |
| Run button | 开始初筛 |
| Result panel | 候选事件 / Stage_Code / 波形证据 / 时频证据 |
| Correction | 进入人工复核 / 事件修正 / 保存复核版本 |
| Export | 导出结果 |
| Sleep module | 睡眠分期 / 分期图 / Hypnogram |

## Change Log

- 2026-06-29: Created terminology contract after owner decision to separate epilepsy event screening from sleep staging.
