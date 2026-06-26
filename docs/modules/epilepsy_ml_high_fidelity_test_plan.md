# Epilepsy ML 高保真迁移测试与验收文档

Status: draft for 07 mainline integration planning
Target docs pair: `epilepsy_ml_high_fidelity_requirements.md`
Date: 2026-06-26

## 1. 测试目标

本测试计划用于验收 AR_analyser1 源码中的 ML Epilepsy Analysis 是否被高保真迁移到 07 主干服务。

测试不是只验证“接口能跑通”，而是验证：

1. 源码 ML 算法行为一致。
2. 模型资产完整。
3. 事件聚合结果一致。
4. 人工复核工作台可用。
5. 保存、历史加载、导出可复验。
6. 非医疗边界不被破坏。
7. 不影响 router / Headroom / IPC。

## 2. 验收分层

| 层级 | 目标 | 必须证据 |
| --- | --- | --- |
| A. 资产层 | 模型/scaler 文件完整 | 文件存在、大小、SHA256、manifest |
| B. 算法层 | 特征、scaler、概率、Stage_Code 与源码一致 | parity JSON/CSV |
| C. 事件层 | `detect_seizures` 聚合一致 | candidate events diff |
| D. 后端任务层 | 07 `/api/tasks` 能跑 ML workflow | task readback、artifact list |
| E. 复核 API 层 | 创建 session、取波形、修改 epoch、保存 | API JSON readback |
| F. 前端工作台层 | 用户能完成看波形、改标注、保存导出 | E2E 截图、导出包 |
| G. 回归边界 | STD/Band Power/PSD 不受影响 | 既有 smoke 或明确未触碰证据 |

## 3. 测试数据

### 3.1 固定 parity fixture

目的：对比 AR_analyser1 源码和 07 迁移实现的数值一致性。

要求：

- 使用固定 EDF/FIF 输入。
- 固定 EEG/EMG/ACC channel。
- 固定 epoch length: 3s 和 5s 各一组。
- 固定采样率，至少一组 `sfreq >= 100Hz`。
- 保存源算法输出：
  - features matrix
  - scaled features
  - probabilities
  - Stage_Code
  - seizure events
  - 30min stats

验收：

- 同一输入、同一 epoch_length、同一模型 hash 下，07 输出与源算法一致。
- 若存在浮点差异，必须记录 tolerance 和原因。

### 3.2 合成功能 fixture

目的：方便 E2E 和人工复核测试。

建议：

- 60-180 秒 EEG。
- 至少 1 段明显候选事件。
- 至少 1 段边界事件，例如只有 1 个 Seizure epoch，应被过滤。
- 至少 4 个通道，包含 EEG/EMG/ACC 或可模拟映射。

验收：

- 能稳定产生候选事件。
- 人工修改后 reviewed events 有可见变化。

### 3.3 边界 fixture

至少覆盖：

- 空事件：全 Normal。
- 连续两个 Seizure epoch：刚好成事件。
- 单个 Seizure epoch：不成事件。
- 事件持续到文件末尾。
- 低采样率 `<100Hz`：warning 而非静默。
- 非 3/5 epoch：如果保留源码兼容，应落到 5s 模型并给 warning。
- 缺少模型资产：明确失败。
- hash 不匹配：明确失败。

## 4. 资产测试

### T-A01 模型文件存在

输入：

- `model_n762_3s.sav`
- `scaler_n762_3s.sav`
- `model_n1814_5s.sav`
- `scaler_n1814_5s.sav`

期望：

- 文件存在于 07 受控资产目录。
- 不在前端静态目录。
- 不通过 router / IPC 加载。

### T-A02 SHA256 校验

期望 hash：

| 文件 | SHA256 |
| --- | --- |
| `model_n762_3s.sav` | `4bf86729f278fa4224c4fbe5007f51e37c194db4f16fc5a68238c3602af86dd7` |
| `scaler_n762_3s.sav` | `10aaee616dbe247f1f38a159faf28a24d199bfb259f6a8bc3ecf8c822905c0b2` |
| `model_n1814_5s.sav` | `907ca24bd22067be367a1aec988f420c8588bc249146b8fbdd956e2bbd58060b` |
| `scaler_n1814_5s.sav` | `cb4199ee1564d717ec55b0089dbd008a654a40cd810bfa7467ee1e67a4d0ced1` |

失败处理：

- hash 不匹配时，任务应失败并返回明确错误。
- 不允许静默降级为 STD 或其他模型。

### T-A03 依赖加载

期望：

- `joblib` 可加载 scaler/model。
- `xgboost` / `scikit-learn` 版本兼容 `.sav`。
- `pyeeg` 行为或 fallback 行为被明确锁定。
- 后端不引入 PyQt5/pyqtgraph。

## 5. 算法 parity 测试

### T-B01 3 秒模型选择

输入：

```json
{"epoch_length_sec": 3.0}
```

期望：

- 加载 `model_n762_3s.sav`。
- 加载 `scaler_n762_3s.sav`。
- model manifest 写入 epoch_length = 3.0。

### T-B02 5 秒模型选择

输入：

```json
{"epoch_length_sec": 5.0}
```

期望：

- 加载 `model_n1814_5s.sav`。
- 加载 `scaler_n1814_5s.sav`。

### T-B03 非 3/5 epoch 兼容

输入：

```json
{"epoch_length_sec": 4.0}
```

期望：

- 若产品决定高保真保留源码行为：加载 5s 模型并输出 warning。
- 若产品决定生产上禁止：返回参数错误。
- 二者只能选其一，并写入需求/manifest；不能静默行为不明。

### T-B04 默认通道和单位链

输入：

- 包含 `EEG3`、`EEG1`、`ACC0` 的 fixture。
- EDF/BDF 导入路径和已转换 raw/FIF 路径各一组。

期望：

- 默认 EEG=`EEG3`、EMG=`EEG1`、ACC=`ACC0`，缺失时返回明确 fallback 或要求选择。
- EDF/BDF 导入后的 `1e6` 微伏转换被记录。
- ACC 在 ML 线程中的 `1e-6` 缩放被记录。
- 不发生重复缩放或漏缩放。

### T-B05 采样率边界

输入：

- `sfreq < 100Hz`
- `sfreq > 1000Hz`

期望：

- `<100Hz` 按源码行为给 warning，不静默。
- `>1000Hz` 若保留源码行为应拒绝；若 07 批准改变，必须在 manifest 写明。

### T-B06 尾部样本截断

输入：

- 总样本数不能整除 `epoch_samples` 的数据。

期望：

- `n_epochs = len(eeg_data) // epoch_samples`。
- 不足一个 epoch 的尾部样本不进入 features/probabilities/events。
- parity 对比中源实现与 07 实现一致。

### T-B07 特征列顺序

期望特征列：

```text
mean, mobility, TKEO,
P_delta, P_theta, P_alpha, P_beta, P_gamma, P_total,
rel_delta, rel_theta, rel_alpha, rel_beta, rel_gamma,
pfd, skew, kurtosis, var, envelope
```

验收：

- 输出 `epilepsy_ml_features.csv` 列顺序完全一致。
- 对固定 epoch，07 与源码每列差异在约定 tolerance 内。

### T-B08 预处理数值保护

验证：

- NaN -> 0。
- +Inf/-Inf -> 0。
- clip 到 `[-1e6, 1e6]`。
- dtype 为 float32 或 manifest 明确说明。

### T-B09 概率与阈值

期望：

- `predict_proba[:, 1]` 被保存为 `probability_seizure`。
- `probability_seizure >= 0.5` 时 `Stage_Code=1`。
- `<0.5` 时 `Stage_Code=0`。

验收：

- 固定输入下 3s/5s 概率与源码一致。
- Stage_Code 与源码一致。

## 6. 事件聚合测试

### T-C01 连续两个 Seizure epoch 成事件

输入 Stage_Code：

```text
0, 1, 1, 0
```

期望：

- 生成 1 个事件。
- start epoch = 2。
- end epoch = 3。
- start_sec = `1 * epoch_length`。
- end_sec = `3 * epoch_length`。

### T-C02 单个 Seizure epoch 不成事件

输入：

```text
0, 1, 0
```

期望：

- 不生成事件。
- epoch mask 全 0 或仅 reviewed epoch 保留在 epoch_scores，但 events 为空。

### T-C03 文件末尾事件

输入：

```text
0, 1, 1
```

期望：

- 事件 end_sec 不超过总时长。

### T-C04 30 分钟统计

期望：

- 以事件开始时间归入 30 分钟窗口。
- 输出 `Seizure Count`。
- 输出标准化 `Seizure Frequency (Events/h)`。

### T-C05 保存复核后重新聚合

步骤：

1. 初始 ML 输出事件 A。
2. 人工把某些 epoch 改为 Normal。
3. 保存。

期望：

- `reviewed_events.csv` 基于人工修改后的 epoch 重新生成。
- 原始 `epilepsy_ml_events.csv` 不被覆盖。
- `review_actions.jsonl` 记录修改。

## 7. 后端 API 测试

### T-D01 创建 ML task

请求：

```json
{
  "module_name": "epilepsy",
  "workflow_id": "epilepsy_ml_screening",
  "parameters_json": {
    "method": "ml_epoch_classifier",
    "epoch_length_sec": 5.0
  }
}
```

期望：

- task 状态完成。
- artifact list 包含：
  - `tables/epilepsy_ml_epoch_scores.csv`
  - `tables/epilepsy_ml_events.csv`
  - `tables/epilepsy_ml_window_stats_30min.csv`
  - `tables/epilepsy_ml_features.csv`
  - `reproducibility/epilepsy_ml_summary.json`
  - `reproducibility/epilepsy_ml_model_manifest.json`

### T-D02 从 task 创建 review session

期望：

- 返回 `session_id`。
- session 记录 input task、model manifest、epoch_length、n_epochs、channels。

### T-D03 获取 waveform window

请求：

```text
GET /api/epilepsy/review-sessions/{session_id}/waveform?start_sec=0&duration_sec=30&channels=eeg,emg,acc
```

期望：

- 返回窗口数据，不返回全量文件。
- 包含 epoch overlay 和 event overlay。
- 大窗口请求可 decimate 或分页。

### T-D04 修改 epoch

请求：

```json
{
  "epoch_indices": [10, 11, 12],
  "review_stage_code": 1,
  "reason": "manual_review"
}
```

期望：

- session epoch 状态改变。
- audit trail 增加一条 action。
- undo 可恢复。

### T-D05 保存复核

期望：

- 生成 reviewed artifacts。
- 返回 reviewed event count。
- 原始模型 artifacts 不被覆盖。

## 8. 前端 E2E 测试

### T-E01 从 module-lab 进入工作台

步骤：

1. 上传 EEG 文件。
2. 选择“癫痫样事件筛查 / ML 模型”。
3. 运行任务。
4. 任务完成后点击“打开复核工作台”。

期望：

- 工作台打开正确 session。
- 顶部显示非医疗说明。
- 显示模型版本和 epoch_length。

### T-E01B 从实验室同步测试入口进入同一工作台

步骤：

1. 打开 module-lab。
2. 点击“癫痫样事件筛查 / ML 模型 / 实验室同步测试”。
3. 选择固定 fixture 或使用默认 fixture。
4. 运行任务。
5. 点击“打开复核工作台”。

期望：

- 提交的是同一个 `epilepsy_ml_screening` workflow。
- 参数中包含 `lab_mode=true`，但算法输出不因 lab_mode 改变。
- 打开的是同一个 `epilepsy-review.html/js`，不是 fork 出来的实验室工作台。
- 页面显示 fixture 名称、模型 hash、audit 状态和非医疗说明。
- 客户主路径不出现实验室 fixture 文案。

### T-E02 事件点击跳转

步骤：

1. 在事件列表点击第一个候选事件。
2. 观察波形区。

期望：

- 时间窗口跳到事件附近。
- EEG/EMG/ACC/时频图同步。
- 分期条对应区间高亮。

### T-E03 人工 Seizure/Normal 标注

步骤：

1. 选中一个或多个 epoch。
2. 点击 Seizure。
3. 点击 Normal。

期望：

- 分期条立即更新。
- 事件列表提示有未保存修改。
- `review_stage_code` 与 UI 一致。

### T-E04 快捷键

步骤：

1. 选中 epoch。
2. 按 Shift+2。
3. 按 Shift+1。

期望：

- Shift+2 标为 Seizure。
- Shift+1 标为 Normal。
- 与按钮行为一致。

### T-E05 Undo / Redo / Reset

步骤：

1. 做三次标注。
2. Undo。
3. Redo。
4. Reset。

期望：

- Undo/Redo 精确恢复 action。
- Reset 恢复模型原始 Stage_Code。
- 保存前后状态清晰。

### T-E06 保存并重新打开

步骤：

1. 修改 epoch。
2. 保存复核。
3. 关闭工作台。
4. 从 session 或 task 重新打开。

期望：

- 复核结果仍在。
- audit trail 仍在。
- 原始模型结果仍可对比。
- 07 不得继承旧桌面 `.cache` 疑似只保存 `df_score` 而丢失 `df_display_score` 的缺陷；reviewed layer 必须可持久化。

### T-E07 导出包

期望导出包包含：

- `reviewed_epoch_scores.csv`
- `reviewed_events.csv`
- `reviewed_window_stats_30min.csv`
- `review_actions.jsonl`
- `review_session_manifest.json`
- `model_manifest.json`
- `non_medical_scope.txt`

### T-E08 截图证据

E2E 必须保存：

- 上传/任务完成截图。
- 工作台初始截图。
- 点击事件后波形截图。
- 人工修改后截图。
- 保存成功后截图。
- 导出包清单 JSON。

## 9. 性能测试

### T-P01 中等数据

输入：

- 30 分钟 EEG。

期望：

- 后端任务完成时间在可接受范围内。
- 工作台首次打开不加载全量波形。

### T-P02 大数据

输入：

- 2 小时 EEG。

期望：

- waveform API 分窗返回。
- 前端滚动/跳转不卡死。
- 单次响应 payload 有上限。

### T-P03 All epoch 警告

源码对 All epoch 显示有性能警告。Web 迁移应：

- 对 All 或超大窗口显示明确提示。
- 默认用分页/窗口加载。

## 10. 非医疗文案测试

检查位置：

- module-lab 卡片。
- 工作台顶部。
- 任务 summary。
- report HTML。
- 导出包 `non_medical_scope.txt`。

必须出现：

- “科研辅助复核”
- “候选事件”
- “不用于诊断、治疗或临床决策”

禁止出现：

- “诊断结果”
- “确诊”
- “治疗建议”
- “临床判定”

## 11. 回归测试

迁移 ML 时必须确认：

- `epilepsy_std_threshold` 仍可跑通。
- Band Power 仍作为 PSD alias，不新增独立 router/API。
- `/api/tasks` 既有 PSD/ERP/QC 基础路径不受影响。
- 不改 router / Headroom / IPC。

推荐 smoke：

1. STD 合成数据跑通。
2. PSD 或 Band Power alias 跑通。
3. ML task 跑通。
4. Review session 保存跑通。

## 12. 独立子智能体核查测试

算法迁移完成后，必须启动独立核查子智能体执行本节测试。该子智能体只负责核查，不负责实现；它必须同时运行 AR_analyser1 源算法与 07 迁移算法，并用构造数据与固定 fixture 对比结果。

### T-X01 独立 worker 身份

期望：

- 核查 worker 与实现 worker 分离。
- 核查报告中写明 source path、target path、模型 hash、测试数据路径。
- 不能以“代码看起来一致”作为通过依据。

### T-X02 模型资产字节级一致

步骤：

1. 对源模型/scaler 计算 SHA256。
2. 对 07 迁移后的模型/scaler 计算 SHA256。
3. 比较文件大小和 SHA256。

期望：

- 四个文件大小和 SHA256 完全一致。
- 不一致时 `accepted=false`。

### T-X03 构造 epoch 数据对比

构造至少以下 Stage_Code 序列，并分别喂给源 `detect_seizures` 和 07 实现：

```text
all_normal:       0,0,0,0,0
single_seizure:   0,1,0,0,0
two_seizure:      0,1,1,0,0
tail_seizure:     0,0,1,1
two_events:       1,1,0,0,1,1
```

期望：

- 事件数量一致。
- 事件起止 epoch 一致。
- 事件起止秒一致。
- 30 分钟统计一致。

### T-X04 特征矩阵逐列对比

步骤：

1. 构造固定 EEG epoch 数据，覆盖平稳段、高幅段、含 NaN/Inf 后清洗段、低 Nyquist 分支。
2. 用源 `extract_features_using_epochs` 输出 features。
3. 用 07 实现输出 features。
4. 逐列比较。

期望：

- 列名和顺序完全一致。
- 每列最大绝对差、均方差写入 `feature_diff.json`。
- 超出 tolerance 时 `accepted=false`。

### T-X05 scaler 与概率对比

步骤：

1. 对同一 features 分别运行源 scaler/model 和 07 scaler/model。
2. 保存 scaled features、probability、Stage_Code。

期望：

- scaled feature 差异在 tolerance 内。
- probability 差异在 tolerance 内。
- Stage_Code 必须完全一致。

### T-X06 端到端 fixture 对比

步骤：

1. 使用同一个 FIF/EDF fixture。
2. 源代码跑 ML 分析，导出 features/probabilities/events。
3. 07 跑 `epilepsy_ml_screening`。
4. 比较全部核心产物。

期望：

- `features.csv` 一致或在 tolerance 内。
- `probabilities.csv` 一致或在 tolerance 内。
- `epoch_scores.csv` 的 Stage_Code 完全一致。
- `events.csv` 的事件数量和起止时间一致。

### T-X06B 显示 overlay 边界核查

步骤：

1. 构造事件刚好结束在 epoch 边界的 fixture。
2. 比较源码显示层 `_build_event_display_score()` 与 07 Web overlay。
3. 同时比较算法事件表。

期望：

- 如果目标是像素级/行为级继承，Web overlay 应复刻源码边界显示。
- 如果 07 决定修正源码可能多涂结束边界 epoch 的行为，必须在验收报告中标记为批准变更，不能当作无差异通过。

### T-X07 复核后重算对比

步骤：

1. 构造一组人工修改：把连续两个 Seizure 改为 Normal；把两个 Normal 改为 Seizure。
2. 源逻辑用修改后的 `df_display_score` 重新聚合。
3. 07 review session 保存后重新聚合。

期望：

- reviewed events 一致。
- 原始模型 events 未被覆盖。
- audit trail 记录修改。
- 保存后重新打开，reviewed epoch layer、review actions、reviewed events 全部仍可读回。

### T-X08 核查 verdict

核查 worker 最终必须输出：

```json
{
  "accepted": false,
  "blocking_differences": [],
  "tolerance_used": {
    "features_abs": 1e-6,
    "probability_abs": 1e-6
  },
  "asset_hashes": {},
  "source_path": "D:/Quanlan/Codes/Python/AR_analyser1/AR_analyser_PC/src",
  "target_path": "D:/Quanlan/Codes/Python/quanlan-analyser-official",
  "non_medical_scope_checked": true
}
```

注：`accepted` 示例值必须由实际结果决定；文档里的 `false` 只是占位，不能照抄为通过。

### T-X09 实验室镜像同源核查

步骤：

1. 从正式入口运行 `epilepsy_ml_screening`。
2. 从实验室入口用同一个 fixture 运行 `epilepsy_ml_screening`。
3. 比较两次任务的 model_manifest、features、probabilities、Stage_Code、events。
4. 打开正式 review workbench 和实验室 review workbench，比较 session API 和 reviewed artifacts。

期望：

- 正式入口和实验室入口的核心输出完全一致。
- 差异只允许存在于 metadata：`lab_mode`、`lab_fixture_id`、UI 提示。
- 若实验室入口产生不同算法输出，验收失败。

## 13. 最终验收包

每次提交给 07 PM 的验收包应包含：

```text
epilepsy_ml_acceptance/
  source_parity/
    features_diff.json
    probabilities_diff.json
    events_diff.json
  backend/
    task_readback.json
    artifact_inventory.json
    model_manifest.json
  frontend/
    01_task_complete.png
    02_review_initial.png
    03_event_jump.png
    04_manual_edit.png
    05_saved_review.png
  export/
    reviewed_epoch_scores.csv
    reviewed_events.csv
    reviewed_window_stats_30min.csv
    review_actions.jsonl
    review_session_manifest.json
    non_medical_scope.txt
  independent_audit/
    asset_hash_check.json
    feature_diff.json
    scaled_feature_diff.json
    probability_diff.json
    stage_code_diff.json
    event_diff.json
    verdict.json
  final_receipt.json
```

通过标准：

- 所有必测项通过，或阻塞项有明确 owner 和下一步。
- 数值 parity 差异在 tolerance 内。
- 人工复核状态可保存、重开、导出。
- 非医疗文案 gate 通过。
- 未触碰 router / Headroom / IPC。
- 独立子智能体核查通过，且 source-vs-target 对比证据可读回。
