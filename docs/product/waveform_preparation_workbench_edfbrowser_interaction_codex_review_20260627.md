# QLanalyser EDFbrowser 风格波形交互 Codex 评审

版本：2026-06-27

评审对象：

- `docs/product/waveform_preparation_workbench_edfbrowser_interaction_requirements_20260627.md`
- `docs/product/waveform_preparation_workbench_edfbrowser_interaction_detailed_design_20260627.md`
- `docs/product/waveform_preparation_workbench_edfbrowser_interaction_e2e_test_plan_20260627.md`

## Codex note

结论：方向正确，但现在应标为“可进入实现准备，不应直接作为最终验收基线”。这组三份文档已经把关键口径扳正：主工作台采用 Canvas，波形区按 EDFbrowser 的阅片习惯设计，普通滚轮默认水平浏览，Ctrl/Cmd + 滚轮才做时间缩放，PageUp/PageDown 与左右箭头成为一等公民，默认浏览模式不写入坏段/选段。

## 最强点

1. 明确废弃“普通滚轮默认缩放、左键拖动默认平移”的网页图表口径。
2. 把浏览模式和写入模式分离，避免 EEG 阅片时误写数据准备草稿。
3. 保持 Canvas 主线，不把 TimeChart 实验线混进 07 主工作台。
4. 把交互习惯落到了 E2E：滚轮、Ctrl 缩放、Page、Arrow、中键、左键不误写、模式写入、非医疗边界。
5. 与现有 Canvas 契约兼容：times_sec、requestSeq、downsample、教学保护、分析门禁都没有被推翻。

## P0 缺口

1. 模式切换入口还不够具体：需要定义“浏览 / 选段 / 坏段 / 坏道”对应的按钮、快捷键、`data-testid`、状态栏可见反馈。
2. `selected_segment` 写入时机需要统一：拖拽过程、UI 草稿、持久化准备方案 revision 三层要说清楚。
3. 数值常量表缺失：滚轮平移比例、缩放因子、最短/最长窗口、增益步长、增益边界需要统一。
4. E2E 缺少分析门禁的正向用例：未确认准备阻止 PSD/ERP、确认后 payload 携带 id/revision/contract version。
5. 状态栏完整性应成为自动化断言，而不是只做视觉建议。

## Codex 建议

进入 07 开发前，先补一个 1-2 小时的文档修订包：

1. 在需求和设计里增加模式切换控件表。
2. 增加统一 constants 表。
3. 明确三层写入模型：transient selection -> UI draft -> persisted preparation plan revision。
4. 在 E2E 里补 analysis gate、status bar completeness、mode selector cases。

## Codex verdict

`conditional_go_after_p0_doc_clarification`
