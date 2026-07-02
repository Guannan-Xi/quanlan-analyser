# Data Preparation Page Adversarial Audit and Cleanup - 2026-06-28

## Verdict

**passed_release_candidate_for_data_preparation_page**

本轮以客户最终交互版本为标准，对数据准备页进行了 7 轮自我对抗审核、整改和回归验证。目标不是增加功能，而是减少重复、收敛主路径、保留科研人员必要控制。

## Design Rules Applied

- One task, one primary visible path.
- 基础数据准备页不展示 epoch/event 复核入口；epoch 复核留给癫痫/睡眠分期等专用工作台。
- 写入操作集中在右侧“当前选择与准备”面板，波形区只负责浏览和选中。
- 时间位置只保留一个可拖动进度条，避免起点输入与进度条重复。
- 高级参考/滤波默认折叠，不占首屏。
- 核心按钮必须有可见语义，不只靠图标或 tooltip。

## Rounds

### Round 1 - 重复入口与信息架构

- Finding: 左侧数据队列、全局导航、底部进入分析、右侧操作面板同时承担跳转/准备/下一步，用户难以判断主路径。
- Fix: 左侧导航降级为辅助；右侧面板成为唯一写入入口；独立波形页降级为辅助链接。
- Acceptance: 主路径收敛为当前数据 -> 波形 -> 右侧准备 -> 进入分析。

### Round 2 - 时间控制重复

- Finding: 起点输入、时间窗下拉、下方进度条同时可见，控制语义重复。
- Fix: 隐藏起点输入，保留时间窗和可拖动进度条；起点仍由内部状态维护。
- Acceptance: 最终 DOM 仅 visibleTimeControls=[eegWindowPreset,eegTimeSlider]。

### Round 3 - 写入操作重复

- Finding: 中间 6 张编辑卡与右侧按钮重复，且旧卡片会把用户从波形任务中拉走。
- Fix: 隐藏 legacy edit grid；右侧补齐添加标签、取消候选，保证能力不丢。
- Acceptance: legacyGridVisible=false，E2E add/confirm candidate 仍通过。

### Round 4 - 基础数据准备与 epoch/event 复核边界

- Finding: 基础数据准备页出现事件分段入口，和后续癫痫/睡眠 epoch 复核概念混在一起。
- Fix: 基础页隐藏 event segment 模式；保留相对时间选段。
- Acceptance: eventSegmentVisible=false。

### Round 5 - 状态信息重复与折叠面板

- Finding: 右侧同时显示“已确认”和“已确认 r1”；折叠 details 内部控件仍被判定可见，造成信息过载。
- Fix: 状态徽标改为“准备完成”；草稿摘要改为“当前 r1 · 无未提交草稿”；修复 details closed 时内部控件显示。
- Acceptance: collapsedDetailsControlsVisible=[]。

### Round 6 - 按钮可发现性与工具栏布局

- Finding: 波形浏览/缩放按钮只有图标，客户不知道开头、上一页、下一页、末尾、缩小、放大分别是什么；加文字后工具栏出现拥挤风险。
- Fix: 给核心按钮加可见短标签；工具栏按钮行改为 flex wrap；浏览组/显示组跨列布局。
- Acceptance: toolbar overlapCount=0，page overflow=0。

### Round 7 - 业务闭环和测试一致性

- Finding: 进入分析入口在收敛过程中不够明确；滚轮 E2E 使用横向滚轮参数，与产品普通滚轮语义不一致。
- Fix: 右侧主操作面板恢复“进入分析任务”；E2E 改为纵向 wheel deltaY。
- Acceptance: 状态矩阵与 Canvas chunk E2E 均 passed。

## Changed Files

- `frontend/index.html`
- `frontend/styles.css`
- `frontend/app.js`
- `scripts/e2e_main_data_prep_canvas_chunk_interaction.mjs`

## Evidence

- Evidence directory: `D:\Quanlan\Codes\Python\quanlan-analyser-official\work\release_evidence\20260628-data-prep-adversarial-audit`
- `round0_before_viewport.png` / `round0_before_fullpage.png`
- `round7_final_rc4_viewport.png`
- `round7_final_rc4_layout.json`
- `round6_final_rc3_dom_audit.json`
- `adversarial_audit_result.json`

## Verification

- node --check frontend/app.js: passed
- node --check scripts/e2e_main_data_prep_canvas_chunk_interaction.mjs: passed
- node --check scripts/e2e_data_prep_interaction_controls_state_matrix.mjs: passed
- scripts/e2e_main_data_prep_canvas_chunk_interaction.mjs: passed
- scripts/e2e_data_prep_interaction_controls_state_matrix.mjs: passed
- scripts/audit_data_preparation_page_release_candidate.mjs: passed
- scripts/audit_frontend_design_debt_static.mjs: passed_with_known_debt; unexpectedDuplicateCount=0

## Remaining Risks

- 当前结论是数据准备页本地 release-candidate；完整外部发布仍需真实匿名 owner-data regression。
- frontend/app.js 仍有既有设计债，本轮只做低风险 UI/交互收敛，未大重构。

## Protected Boundaries

No router, Headroom, gateway, IPC, front-route, model route, TimeChart, or epilepsy source workbench implementation was changed in this slice.
