# 癫痫源码工作台复刻端到端测试文档

状态：生产级 E2E/性能测试草案，供 07 主干集成使用
日期：2026-06-27
源系统：`D:/Quanlan/Codes/Python/AR_analyser1/AR_analyser_PC`
目标系统：`D:/Quanlan/Codes/Python/quanlan-analyser-official`

## 0. P0 验收门槛

本测试文档的 P0 验收门槛：源码式主工作台、Stage_Code 突变显示、EEG/EMG/ACC/频谱同步、事件/epoch 跳转、Seizure/Normal 人工矫正、Undo/Redo/Reset、reviewed 保存重开导出、性能预算、非医疗文案、router/Headroom/IPC 无回归。P0 任一失败，最终 verdict 必须为不通过。

## 1. 测试目标

验证 07 主干中的癫痫样事件工作台是否达到源码交互复刻和生产级性能要求。

测试不只验证 API 能跑通，还要验证：

1. 工作台整体布局接近源码工作流；
2. Stage_Code 以离散突变状态显示；
3. EEG/EMG/ACC/频谱证据同步联动；
4. 人工矫正、Undo、Redo、Reset 正确；
5. reviewed 保存、重开、导出正确；
6. 大 EDF 和 All 模式不卡顿；
7. 非医疗边界无违规；
8. 不影响 router、Headroom、IPC。

## 2. 测试环境

建议环境：

- Windows 本机开发环境；
- 后端 FastAPI 本地服务；
- 前端静态服务；
- Chromium/Edge Playwright；
- 固定 EDF fixture；
- 大文件压力 fixture；
- 源码 parity 产物。

必须记录：

- git commit 或工作区状态；
- backend URL；
- frontend URL；
- fixture 路径和 hash；
- 浏览器版本；
- 测试开始和结束时间；
- 是否启用实验室模式。

## 3. 测试数据

### 3.1 功能 fixture

至少包含：

- EDF：`epilepsy_ml_demo_source_channels.edf` 或等价实验室数据；
- 通道：EEG3、EEG1、ACC0；
- epoch length：5s 主路径；
- 至少一个连续 2 epoch Seizure 候选事件；
- 至少一个 Normal 区间；
- 可稳定生成 reviewed event。

### 3.2 边界 fixture

- all_normal：全 Normal；
- single_seizure：单个 Seizure epoch，不形成事件；
- two_seizure：连续两个 Seizure epoch，形成事件；
- tail_seizure：文件末尾事件；
- two_events：两个独立事件；
- short_tail：尾部不足一个 epoch；
- missing_default_channels：缺少 EEG3/EEG1/ACC0；
- low_sfreq：采样率低于 100Hz，验证 warning。

### 3.3 性能 fixture

- 1 小时 EDF；
- 12 小时 EDF；
- 24 小时压力 EDF 或合成等价数据；
- 高事件密度 Stage_Code 序列；
- 超长 all_normal 序列；
- 大量 manual actions session。

## 4. E2E 功能测试

### T-E2E-001 打开工作台空状态

步骤：

1. 打开 `epilepsy-workbench.html`。
2. 不选择文件。
3. 观察页面。

预期：

- 页面可打开；
- 非医疗科研筛查边界可见；
- 文件选择和上传入口可见；
- 没有诊断、确诊、治疗、临床决策等禁用词；
- 空状态不报错。

证据：截图 `01_empty_state.png`。

### T-E2E-002 选择 EDF 并运行 ML

步骤：

1. 点击选择实验室 EDF fixture；
2. 确认 EEG/EMG/ACC 通道；
3. epoch length 选择 5；
4. 点击运行 ML；
5. 等待完成。

预期：

- 任务完成；
- artifact 包含 epoch scores、events、summary、model manifest；
- 自动进入复核工作台；
- 没有卡死；
- 运行错误不泄露隐私路径。

证据：`02_task_complete.png`、`task_readback.json`、`artifact_inventory.json`。

### T-E2E-003 源码式主画布

步骤：

1. 分析完成后查看首屏；
2. 检查状态条、EEG、EMG、ACC、频谱是否在同一工作台；
3. 检查参数区、导航、Seizure/Normal、Undo/Redo/Reset。

预期：

- 首屏核心是复核画布；
- 状态条 + 波形证据一屏可用；
- 页面不是以 hero/summary/download 为主；
- 工具条符合源码工作流。

证据：`03_source_like_canvas.png`。

### T-E2E-004 Stage_Code 突变语义

步骤：

1. 找到 Normal -> Seizure -> Normal 区间；
2. 观察状态条；
3. 检查是否存在主 probability 平滑折线。

预期：

- 状态切换为突变；
- Seizure 区间为红色/暖色块或段；
- Normal 区间为蓝色/冷色块或段；
- probability/RMS 不作为主图连续解释；
- threshold 不作为 ML 主状态解释。

证据：`04_discrete_stage_strip.png`。

### T-E2E-005 事件点击跳转

步骤：

1. 点击候选事件表第一条事件；
2. 查看状态条和 EEG/EMG/ACC/频谱。

预期：

- 所有视图跳转到事件附近时间窗；
- 当前事件区间高亮；
- 当前 epoch/range 与事件一致；
- waveform 数据在性能预算内出现。

证据：`05_event_jump.png`、performance trace。

### T-E2E-006 epoch 点击和范围选择

步骤：

1. 点击某个 Normal epoch；
2. Shift 点击另一个 epoch 或使用范围输入；
3. 检查选区。

预期：

- 选中范围明确；
- 状态条、波形 overlay 同步；
- selected range 可以用于人工矫正。

证据：`06_epoch_range_select.png`。

### T-E2E-007 Seizure 人工矫正

步骤：

1. 选择 2 个 Normal epoch；
2. 点击 Seizure 或按 Shift+2；
3. 查看事件表和状态条。

预期：

- 选中 epoch 变为 Seizure；
- 状态条立即突变显示红色；
- reviewed events 重算并出现或更新事件；
- source/model layer 不被覆盖；
- action stack 增加。

证据：`07_mark_seizure.png`、`review_actions_after_seizure.json`。

### T-E2E-008 Normal 人工矫正

步骤：

1. 选择一个已有候选事件区间；
2. 点击 Normal 或按 Shift+1；
3. 查看事件表。

预期：

- 选中 epoch 变为 Normal；
- 对应候选事件被拆分、缩短或消失；
- reviewed events 基于 reviewed Stage_Code；
- source events 保留。

证据：`08_mark_normal.png`、`reviewed_events_after_normal.csv`。

### T-E2E-009 Undo / Redo / Reset

步骤：

1. 完成一次 Seizure 修改和一次 Normal 修改；
2. 点击 Undo；
3. 点击 Redo；
4. 点击 Reset。

预期：

- Undo 恢复上一动作前状态；
- Redo 重新应用；
- Reset 恢复 source/model 初始状态；
- 事件表随每一步重算；
- 按钮启用/禁用状态正确。

证据：`09_undo_redo_reset.png`、action stack JSON。

### T-E2E-010 保存、重开和导出

步骤：

1. 完成若干人工修改；
2. 保存 review session；
3. 刷新页面或用 session_id 重开；
4. 导出复核包。

预期：

- reviewed labels 恢复；
- reviewed events 恢复；
- action stack 恢复；
- 导出包包含 reviewed_epoch_scores.csv、reviewed_events.csv、review_actions.jsonl、review_session_manifest.json、non_medical_scope.txt；
- 原始模型 artifacts 未覆盖。

证据：`10_reload_saved_session.png`、export zip manifest。

## 5. 性能测试

### T-PERF-001 打开工作台性能

步骤：

1. 准备已有 task 和 review session；
2. 打开 workbench；
3. 记录 time to interactive、first canvas render、long tasks。

通过标准：

- 普通 fixture p50 < 1.5s；
- p95 < 3s；
- long task > 200ms 为 0 或有记录豁免；
- 无控制台严重错误。

证据：`perf_open_trace.json`。

### T-PERF-002 事件跳转性能

步骤：

1. 连续点击 20 个候选事件；
2. 记录视觉反馈、waveform API、绘图耗时。

通过标准：

- selection feedback p95 < 50ms；
- cached redraw p95 < 100ms；
- uncached 30-60s 窗口 p95 < 800ms；
- 不整页闪烁。

证据：`perf_event_jump.json`。

### T-PERF-003 All 模式压力

步骤：

1. 用 12h/24h fixture 打开 All；
2. 观察 epoch strip；
3. hover 和点击若干位置。

通过标准：

- 不渲染数万个 DOM button；
- 浏览器不崩溃；
- hover p95 < 50ms；
- 内存不持续无限增长；
- All 模式显示为聚合状态条或等价概览。

证据：`perf_all_mode.json`、DOM node count、heap snapshot。

### T-PERF-004 人工矫正性能

步骤：

1. 对 1、10、100、1000 epoch 范围分别执行 Seizure/Normal；
2. 记录 stage edit 和 event recompute 耗时。

通过标准：

- 100 epoch 范围 p95 < 200ms；
- 1000 epoch 范围不冻结，必要时显示局部 loading；
- action stack 正确；
- no long task > 200ms 或有降级解释。

证据：`perf_stage_edit.json`。

### T-PERF-005 波形窗口缓存

步骤：

1. 请求同一事件窗口两次；
2. 请求相邻事件窗口；
3. 请求不同 channel set。

通过标准：

- 第二次请求 cache hit；
- 相邻窗口预取可用或不影响交互；
- cache key 区分 channel、filter、decimation；
- cache 不无限增长。

证据：`perf_waveform_cache.json`。

### T-PERF-006 内存和泄漏

步骤：

1. 连续事件跳转 100 次；
2. 连续窗口 pan/zoom 100 次；
3. 连续人工修改/undo/redo 100 次；
4. 记录 heap。

通过标准：

- heap 无线性增长；
- detached DOM node 不持续增加；
- canvas/webgl resources 可释放；
- waveform cache 遵守上限。

证据：heap snapshots。

## 6. API 测试

### T-API-001 创建 review session

预期：

- 从 task 创建 session；
- 返回 session_id；
- 包含 epoch_length、channels、source artifact ids、non_medical_scope。

### T-API-002 获取 epochs/events

预期：

- epochs 包含 source_stage_code 和 review_stage_code；
- events 来自 reviewed Stage_Code；
- source events 可追溯。

### T-API-003 waveform window

预期：

- 按 start_sec/duration_sec/channel 返回窗口数据；
- 不返回全量原始文件；
- 返回 decimation 信息；
- 包含 epoch/event overlay；
- 大窗口自动降采样。

### T-API-004 PATCH epochs

预期：

- 修改 selected epoch range；
- 生成 action；
- reviewed events 重算；
- source layer 不变。

### T-API-005 undo/redo/reset/save/export

预期：

- action stack 行为正确；
- save 后可重开；
- export 包完整。

## 7. 视觉和源码复刻检查

截图集合：

```text
frontend_epilepsy_source_replica_screenshots/
  01_empty_state.png
  02_task_complete.png
  03_source_like_canvas.png
  04_discrete_stage_strip.png
  05_event_jump.png
  06_epoch_range_select.png
  07_mark_seizure.png
  08_mark_normal.png
  09_undo_redo_reset.png
  10_reload_saved_session.png
  11_all_mode_large_file.png
  12_export_package.png
```

检查点：

- 是否为工作台布局；
- 状态条是否突变；
- 波形和频谱是否在同一复核链；
- 工具栏是否包含源码关键操作；
- 不出现医疗化措辞；
- 错误/加载/空状态是否可恢复；
- 窄屏和宽屏是否可用。

源码复刻 Parity Matrix：

| 源码证据 | Web selector/testid | 必测交互 | 证据文件 |
| --- | --- | --- | --- |
| `EpilepsyAnalysis.py:548` | `[data-testid="epoch-count-select"]` | `All/100/50/30/20/10/5/3` 切换 | `parity/epoch_count_modes.json` |
| `EpilepsyAnalysis.py:2113` | `[data-testid="time-slider"]` | 拖动时间滑块并联动波形窗口 | `parity/time_slider_trace.json` |
| `EpilepsyAnalysis.py:2115` | `[data-testid="stage-edit-toolbar"]` | Seizure/Normal/Undo/Redo/Reset | `parity/stage_edit_actions.json` |
| `EpilepsyAnalysis.py:3198` | `[data-testid="amplitude-control"]` | EEG/EMG/ACC Auto/Manual 振幅 | `parity/amplitude_modes.json` |
| `EpilepsyAnalysis.py:1042` | `[data-testid="signal-pane-stack"]` | EEG/EMG/ACC/频谱四轨同步 | `parity/signal_stack_alignment.json` |
| `EpilepsyAnalysis.py:1087` | `[data-testid="source-replica-canvas"]` | 状态条、波形、频谱布局顺序 | `parity/layout_screenshot.png` |
| 保存图片/数据/历史源码入口 | `[data-testid="artifact-export-panel"]` | 截图、review CSV、session manifest、history reload | `parity/export_reload.json` |

## 8. 非医疗文案测试

扫描范围：

- HTML；
- JS visible copy；
- CSS content；
- export manifest；
- report/snapshot title；
- error messages。

禁止词示例：

- 诊断；
- 确诊；
- 治疗；
- 临床决策；
- 患者分诊；
- 发作确认；
- 医疗建议。

允许词：

- 癫痫样候选事件；
- 科研筛查；
- 人工复核；
- 候选区间；
- reviewed label；
- epoch state。

上下文规则：

- 允许否定边界句，例如“本工具不用于诊断”；
- 禁止正向承诺，例如“诊断癫痫”“确诊发作”“给出治疗建议”“临床分诊”；
- 扫描器输出必须包含 `location`, `context`, `term`, `disposition=allowed_boundary|blocked_claim`；
- 只要存在 `blocked_claim`，最终 P0 不通过。

## 9. Router / Headroom / IPC 回归

步骤：

1. 启动 07 服务；
2. 运行癫痫工作台 E2E；
3. 同时执行主干 health/readback；
4. 检查 router/Headroom/IPC 相关服务未被改动或阻断。

通过标准：

- 既有 API health 正常；
- 不新增 router/front-route 依赖；
- 不改 Headroom 配置；
- IPC/线程通信不受影响；
- 癫痫长任务不阻塞其他 API。

证据：`ipc_regression_health.json`、`service_health_after_epilepsy_e2e.json`。

## 9.1 ML 高保真与 Band Power 边界回归

目标：确认源码 UI/交互复刻不会改动 ML 算法合同，也不会把 Band Power 迁移误并入癫痫工作台。

步骤：

1. 使用固定 EDF fixture 分别运行源码 ML parity 检查和 07 主干 ML workflow；
2. 对比模型参数摘要、scaler 摘要、特征列顺序、epoch length、probability、阈值后 `Stage_Code`；
3. 打开癫痫工作台并完成一次人工复核，确认人工覆盖只写 review session，不回写 source ML artifact；
4. 检查 Band Power 模块入口、任务名、artifact label 和导出产物，确认不出现 Seizure/Normal、`Stage_Code`、review session 语义。

通过标准：

- ML parity 结果由 `epilepsy_ml_high_fidelity_test_plan.md` 判定，本测试引用其通过证据；
- 验收包必须包含 `epilepsy_ml_high_fidelity_acceptance.json`、model/scaler hash、feature schema、3s/5s 路由、0.5 threshold 和源 fixture prediction parity 摘要；
- source ML artifact 在人工复核前后 checksum 不变；
- Band Power 与癫痫工作台只共享基础设施，不共享癫痫事件复核语义；
- 若 UI 复刻导致模型参数、scaler、特征顺序或 `Stage_Code` 规则变化，P0 失败。

证据：`ml_parity/ml_source_vs_07.json`、`review/source_artifact_checksum_before_after.json`、`band_power/band_power_boundary_check.json`。

## 10. 最终验收包

```text
epilepsy_source_workbench_replica_acceptance/
  backend/
    task_readback.json
    review_session_readback.json
    waveform_window_sample.json
    artifact_inventory.json
  frontend/
    screenshots/
    playwright_trace.zip
    console_errors.json
  performance/
    perf_open_trace.json
    perf_event_jump.json
    perf_all_mode.json
    perf_stage_edit.json
    perf_waveform_cache.json
    heap_snapshots/
  export/
    reviewed_epoch_scores.csv
    reviewed_events.csv
    review_actions.jsonl
    review_session_manifest.json
    non_medical_scope.txt
  regression/
    ipc_regression_health.json
    router_headroom_no_change_note.md
  final_verdict.json
```

`final_verdict.json` 必须包含：

```json
{
  "accepted": false,
  "p0_passed": [],
  "p0_failed": [],
  "performance_passed": false,
  "non_medical_scope_passed": false,
  "router_headroom_ipc_regression_passed": false,
  "blocking_issues": [],
  "evidence_root": "..."
}
```

注意：示例中的 `accepted=false` 是占位，真实验收必须由测试结果决定。


## 11. 子智能体补充 E2E 矩阵

以下矩阵作为第 4-9 节的执行型索引，便于 Playwright/API runner 直接落地：

| ID | 可执行步骤 | 预期结果 | 证据文件 |
| --- | --- | --- | --- |
| E2E-01 启动 | 打开 `frontend/epilepsy-workbench.html?api=http://127.0.0.1:8001/api`，等待文件列表加载 | 页面可交互；无空白页、无乱码、无 console error；可见非医疗边界 | `ui/01_initial.png`, `logs/console.json` |
| E2E-02 选择/上传 EDF | 选择实验室 EDF；再用一个合成 EDF 走上传 | `GET /eeg/files`、`POST /eeg/upload` 成功；文件 id、文件名、元数据可见 | `api/eeg_files.json`, `api/upload_result.json` |
| E2E-03 参数运行 ML | 选择 ML 模式，epoch=5，运行筛查 | 创建 `module_name=epilepsy_ml`、`workflow_id=epilepsy_ml_xgboost`；产物含 epoch scores、events、summary、model manifest | `api/task_ml.json`, `artifacts/ml_manifest.json` |
| E2E-04 参数运行 STD | 切换 STD，设 `std_factor/rms_window/min_event_epochs`，运行 | 创建 `module_name=epilepsy`、`workflow_id=epilepsy_std_threshold`；阈值、事件、30min 统计可下载 | `api/task_std.json`, `artifacts/std_summary.json` |
| E2E-05 epoch 导航 | 依次测 All、100、50、30、20、10、5、3；点击 First/Prev/Next/Last；输入 epoch 跳转 | 选择位置正确；页码/窗口范围正确；不跳出窗口；All 不锁死浏览器 | `ui/nav_all.png`, `perf/nav_trace.json` |
| E2E-06 事件选择 | 点击候选事件表 #1/#N，检查时间轴高亮与当前事件面板 | 事件、epoch 范围、备注框、复核状态同步 | `ui/event_selected.png` |
| E2E-07 手工矫正 | 选单个 epoch、Shift 选范围；点 Seizure/Normal；再按 `Shift+2/Shift+1` | `Stage_Code` 改变；事件按连续 >=2 个 Seizure epoch 重算；原始 artifact 不被覆盖 | `review/stage_correction.json` |
| E2E-08 Undo/Redo/Reset | 连续做 3 次矫正，依次 Undo、Redo、Reset | 历史栈正确；按钮启停正确；Reset 后回到源结果 | `review/history_actions.json` |
| E2E-09 波形预览 | 选事件后刷新候选波形；切 Raw / Filter preview | 只取事件附近窗口；Raw/Filter 视图可用；不把全量 EDF 推给前端 | `api/waveform_task.json`, `ui/waveform_raw_filter.png` |
| E2E-10 导出 | 下载 review JSON、reviewed epoch CSV、reviewed events CSV 和后端 artifacts | JSON 可解析；CSV UTF-8；包含源 Stage 与矫正 Stage；无本地绝对路径/密钥 | `exports/review_session_manifest.json`, `exports/csv_parse.json` |
| E2E-11 重载 | 带 `?task=<task_id>` 或 `session_id` 重开；保留/清空 localStorage 各测一次 | artifact/session 可重载；本地复核状态只按当前 task/session key 恢复，不串任务 | `reload/reload_with_store.json`, `reload/reload_clean.json` |
| E2E-12 错误恢复 | 后端断开、无文件、非法 task、artifact 404、波形任务失败 | 页面给出可恢复提示；按钮不乱启用；错误不暴露私密路径 | `errors/error_states.png`, `errors/api_errors.json` |

## 12. 补充性能预算

- 页面交互 P95 < 150ms。
- Next/Prev/Goto < 200ms。
- 手工矫正 1-1000 epoch < 500ms；其中生产常用 1-100 epoch 目标 < 200ms。
- All 模式首次渲染不超过 3s；超过即标 P1/P0 风险并要求虚拟化或分块渲染。
- 波形预览或主波形窗口只请求 6-30s 或当前视窗所需数据，不把整段 EDF 推给前端。
- 连续预览 50 次后 Chrome heap 增长不超过 150MB 或 20%。
- Python worker 任务完成后内存应回落，无持续泄漏。
- 大 EDF 任务运行中 `/health` 仍能响应，不阻塞主服务健康检查。
- 后端 review session 持久化必须通过：保存后清空 localStorage，使用 `session_id` 重开仍能读回 reviewed epochs、events、actions 和 UI 游标。
- 12h/24h EDF 压测期间 `/health` p95 < 300ms；其他轻量 API smoke 不超时。
- All 模式硬断言：DOM node count 不随 epoch 总数线性增长；hover p95 < 50ms；>200ms main-thread long task 为 0，或必须记录降级解释。
- Raw/Filter preview 硬断言：请求窗口限定在 6-30s 或当前视窗；相同窗口第二次必须体现 cache hit；cache key 区分 channel、filter、decimation。

证据文件：`perf/playwright_trace.zip`、`perf/browser_metrics.json`、`perf/api_timing.json`、`perf/python_worker_memory.csv`、`perf/large_edf_all_mode.png`。

性能证据硬门槛：

- 必须生成 `perf_trace.json`、`longtask_summary.json`、`dom_node_count.json`、`heap_before_after.json`、`waveform_payload_bytes.json`、`waveform_max_points.json`、`cache_eviction.json`；
- 任一证据缺失，`final_verdict.json.accepted` 必须为 `false`；
- 人工描述“不卡顿”不能替代浏览器 trace、API timing 和 worker memory 证据。

## 12.1 Waveform fidelity and overlay alignment

使用合成 EDF fixture 构造已知 spike、已知事件边界、EEG/EMG/ACC 同步脉冲和频谱能量变化。

通过标准：

- EEG/EMG/ACC 三轨时间轴对齐，误差不超过 1 个采样周期或实现记录的 decimation tolerance；
- min/max envelope 保留已知 spike 峰值，不能被均值抽稀抹平；
- event overlay 与 `Stage_Code` 区间对齐误差不超过 1 个 epoch；
- 频谱 tile 的时间窗口与 waveform window 一致；
- Raw/Filter preview 的 filter profile、cache key、payload bytes 可读回。

证据：`waveform_fidelity/spike_peak_preserved.json`、`waveform_fidelity/overlay_alignment.json`、`waveform_fidelity/spectrogram_window_match.json`。

## 13. 补充 API 覆盖

API smoke 至少覆盖：

- `GET /health`
- `GET /eeg/files`
- `POST /projects`
- `POST /eeg/upload`
- `GET /eeg/files/{id}/metadata`
- `POST /tasks`
- `GET /tasks/{id}`
- `GET /tasks/{id}/artifacts`
- `GET /artifacts/{id}/download`
- `GET /lab/demo/epilepsy`

断言：ML/STD payload 的 `module_name`、`workflow_id`、`parameters_json`、`non_medical_boundary` 正确；artifact label 与前端读取一致；下载内容类型和文件名正确；失败时返回结构化错误；大 EDF 任务不会阻塞健康检查。

## 14. 补充静态回归扫描

不得影响 router/Headroom/IPC。静态扫描范围：`epilepsy-workbench.*`、后端 epilepsy/qc 路径、新增 review API。禁止新增以下依赖或硬编码：

- `Headroom`
- `ipcRenderer`
- `window.require`
- `child_process`
- `8790`
- `8787`
- 非 QLanalyser API 的 Codex/IPC 控制面调用

证据：`regression/static_no_router_headroom_ipc.json`、`regression/service_health_before_after.json`。

No-touch allowlist：

- `git diff --name-only` 应只命中 epilepsy 业务文件、共享 EEG 文件管理、artifact/export、实验室 fixture、测试 runner、文档；
- 若命中 router、Headroom、gateway、IPC、model route、Codex 控制面配置，必须在 `final_verdict.json.blocking_issues` 中列为 P0 blocker；
- 记录 Headroom/router 配置 hash/readback，形成 `regression/router_headroom_config_hash_before_after.json`。

Band Power / PSD 边界静态扫描：

- epilepsy UI/API/export 中禁止新增 `band_power`、`psd_band_power`、`channel_band_power`、`频段功率` 字段或文案；
- 文档中的边界说明允许出现这些词，但测试 runner 需要标记为 `allowed_boundary_doc`；
- 若 epilepsy artifact label、task workflow、review session payload 中出现 Band Power/PSD 结果语义，P0 失败。
