# 07 Canvas 数据准备波形工作台双评审摘要（Codex + Claude，2026-06-27）

## 一句话结论

Codex note:

07 最新工作“工程里程碑通过，但专业 EEG reviewer 体验未通过”。现在可以承认它是可用的 Canvas 数据准备草稿编辑器，不建议直接进入最终产品验收。下一步最稳是让 07 做 `waveform-viewport-p0`：本地视口、键盘导航、固定 uV/格灵敏度。

Claude says:

Claude 的有效复审文件在 `docs/product/waveform_canvas_workbench_claude_review_20260627.md`。它的结论与 Codex 基本一致：当前 dev-ready 成立，但不建议终审；应先回炉 P0 UX 包。Claude 额外强调三件事：视口不应每次打后端任务，键盘导航缺失，当前 `maxAbs` 自适应缩放不是 EEG 可读的 uV/格。

## 已生成文档

- `docs/product/waveform_canvas_workbench_codex_review_20260627.md`
- `docs/product/waveform_canvas_workbench_claude_review_20260627.md`
- `docs/product/waveform_canvas_workbench_dual_review_summary_20260627.md`
- Claude 调用原始证据：`work/release_evidence/20260627-waveform-canvas-workbench-dual-review/claude_full_review_raw_v3.md`

## 双方一致认可的完成项

- Canvas 已能自动显示真实 EEG 波形，loading overlay 能隐藏。
- 坐标映射、`times_sec` 绘制、坏段/选段/事件叠加、DPR/resize、旧响应保护已补。
- 数据准备确认后向下游分析传递 plan id、revision、contract version 的方向正确。
- 教学数据保护、分析门禁选择器、静态契约、浏览器 E2E 都有 evidence。
- 当前没有接入 TimeChart，符合 Canvas 主线。

## 双方一致认为的主要问题

- 波形仍像“表单里的预览图”，不是 EEG reviewer 的主工作面。
- 每次平移/缩放仍容易走 `reloadWaveformPreview()` / 后端 task 流程，视口不是一等公民。
- 灵敏度用 `2x` 和每通道 `maxAbs` 自适应缩放，不是 uV/格。
- 缺键盘导航、mini map、通道 gutter、montage、事件导航。
- 缺浏览/标注/确认模式隔离，浏览时也可能触发选段编辑。
- E2E 证明功能可跑，但没有充分证明 EEG 专家操作效率和用户逻辑安全。

## 下一步给 07 的最小开发包

`waveform-viewport-p0`，只做 1-2 小时内可落的 P0：

1. 本地视口重绘：已加载 buffer 内 pan/zoom/翻页不新增 task POST，越界才预取。
2. 固定 uV/格灵敏度：使用 `scale_uv`，替换 `2x`，画校准条。
3. 键盘导航：左右键、PageUp/PageDown、Home、`+/-`、`[`/`]`。
4. 补证据：task POST 计数为 0 的本地视口 E2E、键盘 E2E、固定灵敏度静态验证、大窗口降采样保峰值 E2E、更新截图。

## 验收口径

- 可以通过：`Canvas 数据准备工作台 dev-ready`。
- 不应通过：`专业 EEG reviewer / 最终产品验收`。
- 进入下一阶段条件：P0-1 本地视口、P0-2 键盘导航、P0-3 固定 uV/格闭环，并有截图和 E2E 证据。

route_decision: gpt55_planner_or_acceptance + Claude Opus 4.8 sidecar + script_validator
execution_packet_or_skip_reason: Claude 已真实调用；Codex 独立复核本地 evidence、截图、源码锚点和验证脚本。
executor_evidence: Claude raw v3、Codex report、validation rerun、UTF-8/mojibake checks、07 thread readback、screenshot visual review。
gpt55_acceptance: 双评审结论一致，建议回 07 做 `waveform-viewport-p0` 后再终审。
final_receipt: completed_dual_review_documents_ready
next_real_artifact: 给 07 投递 `waveform-viewport-p0` 开发包。
