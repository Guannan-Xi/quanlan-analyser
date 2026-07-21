# QLanalyser EDFbrowser 风格波形交互双评审摘要（Codex + Claude）

版本：2026-06-27

## 一句话结论

Codex note:

这组三份 EDFbrowser 交互补充文档把方向扳对了：07 Canvas 主工作台应采用专业 EEG 阅片习惯，而不是普通网页图表习惯。但 Codex 与 Claude 都不建议把它直接交给 07 当最终实现基线；应先补齐模式切换、写入时机、数值常量和 E2E 门禁四类 P0 文档缺口。

Claude says:

Claude 的有效评审结论是 `Conditional GO`：核心设计正确，浏览优先/显式写入是正确心智；但还有 P0 规格洞会导致实现者猜测，尤其是模式切换入口、`selected_segment` 写入层级、数值常量表、分析门禁自动化用例。

## 双方一致意见

1. 同意废弃旧口径：普通滚轮默认缩放、左键拖动默认平移、Ctrl/Cmd+滚轮改增益。
2. 同意采用 EDFbrowser 风格：普通滚轮水平浏览，Ctrl/Cmd+滚轮时间缩放，PageUp/PageDown 翻页，Left/Right 1/10 页移动，中键拖动水平浏览。
3. 同意浏览模式和写入模式必须分离，默认浏览不得写入坏段/选段。
4. 同意 Canvas 主线继续保留，不在本轮主工作台接入 TimeChart。
5. 同意当前三份文档是“方向正确的补充规范”，但还不是可直接实现/验收的完整开发包。

## 必补 P0

| P0 | 问题 | 影响 | 建议补法 |
|---|---|---|---|
| P0-1 | 模式切换入口未定义 | E2E 无法切换到选段/坏段/坏道模式 | 增加按钮、快捷键、selector、状态栏反馈 |
| P0-2 | 选段写入时机不统一 | 实现可能误写准备方案 | 定义 transient / UI draft / persisted revision 三层 |
| P0-3 | 数值常量不统一 | 自动化断言不稳定 | 增加 constants 表 |
| P0-4 | 分析门禁缺少正向 E2E | 下游 PSD/ERP 可能绕过准备方案 | 增加未确认阻止、确认后携带 id/revision/version 用例 |
| P0-5 | 状态栏完整性未自动化 | 用户无法知道模式/窗口/增益/准备状态 | 增加状态栏字段断言 |

## 给 07 的下一步 1-2 小时包

1. 先补三份文档，不急着改代码。
2. 把模式切换控件、selector、快捷键写成表。
3. 把滚轮比例、缩放因子、时间窗边界、增益步长写成 constants。
4. 把写入模型改成三层：临时拖拽、UI 草稿、持久化准备方案 revision。
5. 扩展 E2E：mode selector、status bar、analysis gate、browse-mode-no-write。

## 产物路径

- Codex 评审：`docs/product/waveform_preparation_workbench_edfbrowser_interaction_codex_review_20260627.md`
- Claude 评审：`docs/product/waveform_preparation_workbench_edfbrowser_interaction_claude_review_20260627.md`
- 双评审摘要：`docs/product/waveform_preparation_workbench_edfbrowser_interaction_dual_review_summary_20260627.md`
- Claude raw evidence：`work/release_evidence/20260627-edfbrowser-waveform-interaction/claude_edfbrowser_interaction_review_embedded_ascii.md`

route_decision: gpt55_planner_or_acceptance + Claude Opus 4.8 sidecar + script_validator
execution_packet_or_skip_reason: Claude 已真实调用；Codex 独立复核 EDFbrowser 文档、02 线程复用结论和官方手册证据。
executor_evidence: Claude embedded raw review、Codex review、EDFBrowser docs、manual probe JSON。
gpt55_acceptance: 双方结论一致：方向正确，P0 文档澄清后再交 07 实现。
final_receipt: completed_edfbrowser_interaction_dual_review_documents
next_real_artifact: P0 文档澄清修订包。
