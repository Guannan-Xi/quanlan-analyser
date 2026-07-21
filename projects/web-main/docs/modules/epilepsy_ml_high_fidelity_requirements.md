# Epilepsy ML 高保真迁移需求与详细设计

Status: draft for 07 mainline integration planning
Owner lane: 07 QLanalyser main service / Codex acceptance
Source system: `D:\Quanlan\Codes\Python\AR_analyser1\AR_analyser_PC`
Target system: `D:\Quanlan\Codes\Python\quanlan-analyser-official`
Date: 2026-06-26

## 1. 结论

本迁移不是把“癫痫分析”做成一个只输出 CSV 的后端任务，而是要把 AR_analyser1 里的 **ML Epilepsy Analysis 算法链路 + 交互复核工作台** 高保真迁移到 07 主干服务。

当前 07 已有 `epilepsy_std_threshold` 的最小 STD 阈值筛查底座，能生成 epoch/event/window 表格；它适合作为 V0 自动筛查基础，但不能代表源码中的 ML 癫痫分析体验。生产级迁移目标应是：

1. 保留 ML 算法关键行为：epoch 长度选择、特征列顺序、模型/scaler 加载、概率阈值、事件聚合、统计输出。
2. 保留人工复核体验：波形查看、分期条、事件跳转、Seizure/Normal 标注、撤销、重做、重置、保存、历史加载。
3. 转为 07 的 Web/API 架构：任务产物、复核会话、审计轨迹、导出包、可复验测试证据。
4. 坚持非医疗定位：科研筛查、辅助复核、候选事件，不写成诊断、确诊、治疗、分诊或临床决策工具。
5. 不改 router / Headroom / IPC / front-route；迁移落在 07 服务内部 API、worker、artifact 和前端工作台。
6. 在实验室入口提供同源同步测试镜像，供用户同步试用；实验室镜像不得 fork 算法、模型、workflow 或 review workbench。

## 2. 非医疗产品边界

必须使用以下口径：

- “癫痫样事件筛查”
- “候选事件”
- “科研辅助复核”
- “人工复核后事件集”
- “高幅/模型候选 epoch”

禁止使用以下口径作为功能承诺：

- “诊断癫痫”
- “确诊发作”
- “临床决策”
- “治疗建议”
- “自动判定患者状态”
- “代替医生/实验员复核”

所有 UI、报告、导出包和 API metadata 必须带有非医疗说明：本模块仅用于科研数据分析和候选事件复核，不用于临床诊断、治疗或急救决策。

## 3. 源码证据清单

| 主题 | 源码证据 |
| --- | --- |
| ML 入口 | `D:\Quanlan\Codes\Python\AR_analyser1\AR_analyser_PC\src\Data_Info.py:781-834` 定义 Epilepsy STD / ML 子菜单；`Data_Info.py:1003-1014` 绑定 `open_epilepsy_ml_analysis`；`Data_Info.py:2507-2518` 打开 ML 窗口并注入 `raw_processed`。 |
| ML UI 类 | `D:\Quanlan\Codes\Python\AR_analyser1\AR_analyser_PC\src\EpilepsyAnalysis_ML.py:976-992` 返回 `Thread_run_analysis_ML`，标题为 `ML Epilepsy Analysis`，历史目录为 `Epilepsy_data_History/ML`。 |
| 模型选择 | `EpilepsyAnalysis_ML.py:298-311` 根据 `epoch_length` 选择 3s 或 5s 模型，其他 epoch 默认走 5s 模型。 |
| 模型加载 | `EpilepsyAnalysis_ML.py:315-336` 用 `joblib.load` 加载 model/scaler，并设置 XGBoost 兼容字段。 |
| 数据通道 | `EpilepsyAnalysis_ML.py:362-368` 从 `raw_processed` 取 sfreq、EEG、EMG、ACC，其中 ACC 乘 `1e-6`。 |
| 频谱/包络 | `EpilepsyAnalysis_ML.py:373-380` 计算 EMG Hilbert envelope 和 spectrogram。 |
| 特征提取 | `EpilepsyAnalysis_ML.py:124-240` 逐 epoch 提取 19 个特征并 `nan_to_num`、clip 到 `[-1e6, 1e6]`、转 `float32`。 |
| 预测阈值 | `EpilepsyAnalysis_ML.py:405-417` scaler transform 后取 `predict_proba[:, 1]`，阈值 `>= 0.5` 为 Seizure。 |
| 事件聚合 | `D:\Quanlan\Codes\Python\AR_analyser1\AR_analyser_PC\src\EpilepsyAnalysis.py:81-324` 将连续 Seizure epoch 聚成事件，内部常量 `MIN_SEIZURE_EPOCHS = 2`。 |
| 初始 ML 后处理 | `EpilepsyAnalysis_ML.py:453-488` 调用 `detect_seizures` 生成 seizure info、30 分钟统计和 epoch mask。 |
| 人工标注按钮 | `EpilepsyAnalysis.py:576-640` 定义 Seizure / Normal / redo / undo / reset 按钮。 |
| 标注绑定 | `EpilepsyAnalysis.py:2100-2130` 将按钮和快捷键绑定到 Seizure/Normal、undo/redo/reset、保存等动作。 |
| 波形和分期显示 | `EpilepsyAnalysis.py:2530-2808` 绘制分期条、EEG、EMG envelope、ACC、时频图。 |
| 跳转/hover/选区 | `EpilepsyAnalysis.py:1408-1528` 实现 epoch 跳转和 hover；`EpilepsyAnalysis.py:1599-2048` 实现选区高亮、同步和局部 zoom。 |
| 人工修改历史 | `D:\Quanlan\Codes\Python\AR_analyser1\AR_analyser_PC\src\Domain\HistoricalWarehouse.py:40-65` 保存 EpilepsyScoreWH 的撤销/重做栈。 |
| 复核后保存 | `EpilepsyAnalysis_ML.py:824-918` 保存前从人工修正后的 `df_display_score` 重新计算 seizure 统计。 |
| 历史加载 | `EpilepsyAnalysis.py:3949-4212` 加载和保存 `.cache`，恢复 df_score、raw、通道、spectrogram、epoch_length 等。 |

## 4. 当前 07 基线

当前 07 已有：

- `D:\Quanlan\Codes\Python\quanlan-analyser-official\eeg_core\analysis\epilepsy.py`
  - workflow: `epilepsy_std_threshold`
  - method: `std_threshold`
  - 产出 `epilepsy_epoch_scores.csv`、`epilepsy_events.csv`、`epilepsy_window_stats_30min.csv`、`epilepsy_summary.json`
- `D:\Quanlan\Codes\Python\quanlan-analyser-official\worker\tasks\epilepsy.py`
  - 简单 wrapper 调用 `run_epilepsy`
- `D:\Quanlan\Codes\Python\quanlan-analyser-official\backend\services\task_service.py:72-82`
  - 已登记 `epilepsy_std_threshold`
- `D:\Quanlan\Codes\Python\quanlan-analyser-official\frontend\module-lab.js`
  - 已有“癫痫样事件筛查 / STD 阈值”卡片

当前缺口：

1. 无 ML runner。
2. 无 ML model/scaler 资产合同。
3. 无波形窗口 API。
4. 无事件复核会话 API。
5. 无人工改 epoch/event 的保存与审计。
6. 无工作台页面。
7. 无源码 parity 测试。
8. 无复核后重新统计与导出合同。

## 5. 高保真算法需求

### 5.1 Workflow 命名

建议新增 workflow：

- `epilepsy_ml_screening`
- module: `epilepsy`
- method: `ml_epoch_classifier`
- production status: `internal_validation_non_medical_research_screening`

STD workflow 保留：

- `epilepsy_std_threshold`
- 用于 V0 阈值筛查、对照测试和低依赖 fallback。

### 5.2 输入数据

ML runner 必须接收：

```json
{
  "input_file_id": "eeg_xxx",
  "module_name": "epilepsy",
  "workflow_id": "epilepsy_ml_screening",
  "parameters_json": {
    "method": "ml_epoch_classifier",
    "epoch_length_sec": 5.0,
    "eeg_channel": null,
    "emg_channel": null,
    "acc_channel": null,
    "bad_channels": [],
    "prediction_threshold": 0.5,
    "event_window_sec": 1800.0
  }
}
```

要求：

- `epoch_length_sec` 首期只开放 3.0 和 5.0。
- 如果传入其他值，为了高保真可以兼容为 5s 模型，但 UI 必须提示“当前模型仅校验 3s/5s，其他值按 5s 模型处理”，并在 metadata 记录。
- 旧版默认通道为 EEG=`EEG3`、EMG=`EEG1`、ACC=`ACC0`；迁移时应优先复刻该默认值，若目标文件无这些通道，必须让用户选择或采用明确 fallback，并写入 metadata。
- 源码导入 EDF/BDF 后全通道乘 `1e6` 转为微伏；ML 线程中 ACC 再乘 `1e-6`。07 迁移必须显式记录输入单位状态，避免重复缩放或漏缩放。
- 原源码对低采样率 `<100Hz` 只警告，不阻断；迁移后应保留 warning metadata，不直接失败，除非特征计算无法完成。
- 原源码在数据导入阶段拒绝 `sfreq > 1000Hz`；07 若改变该行为，必须在需求和测试中显式说明原因。

### 5.3 模型资产合同

源模型资产：

| 文件 | 大小 | SHA256 |
| --- | ---: | --- |
| `newEpilepsy/model_n762_3s.sav` | 2,747,161 | `4bf86729f278fa4224c4fbe5007f51e37c194db4f16fc5a68238c3602af86dd7` |
| `newEpilepsy/scaler_n762_3s.sav` | 767 | `10aaee616dbe247f1f38a159faf28a24d199bfb259f6a8bc3ecf8c822905c0b2` |
| `newEpilepsy/model_n1814_5s.sav` | 4,156,984 | `907ca24bd22067be367a1aec988f420c8588bc249146b8fbdd956e2bbd58060b` |
| `newEpilepsy/scaler_n1814_5s.sav` | 767 | `cb4199ee1564d717ec55b0089dbd008a654a40cd810bfa7467ee1e67a4d0ced1` |

迁移要求：

- 放入 07 受控资产目录，例如 `eeg_core/assets/epilepsy/newEpilepsy/` 或 `models/epilepsy_ml/`。
- 新增 `model_manifest.json`，记录文件名、大小、sha256、epoch_length、source_path、loaded_by、dependency versions。
- 启动/运行时检查 sha256，不匹配则返回明确错误，不静默 fallback 到其他模型。
- 不把 `.sav` 文件散落到前端或静态目录。
- 不经由 router / Headroom / IPC 传递模型文件。

### 5.4 依赖合同

AR_analyser1 requirements 可见：

- `joblib==1.4.2`
- `mne==1.7.1`
- `numpy==1.26.4`
- `scikit-learn==1.5.1`
- `scipy==1.14.1`
- `xgboost==2.1.4`
- PyQt5 / pyqtgraph 仅属于桌面 UI，不应带入 07 后端。

07 当前 requirements 主要是 FastAPI/MNE/reportlab 等，尚未包含 ML 依赖。迁移时应：

- 后端增加 `joblib`、`scipy`、`scikit-learn`、`xgboost`。
- `pyeeg` 在源码中被 import，但 requirements 未显式列出；迁移时必须确认可用来源。若不引入 pyeeg，应复刻源码里的 fallback 行为，并做数值 parity 测试。
- 避免在 Web 服务主进程里引入 PyQt5 / pyqtgraph。

### 5.5 特征提取合同

必须按源码顺序输出 19 个特征：

1. `mean`
2. `mobility`
3. `TKEO`
4. `P_delta`
5. `P_theta`
6. `P_alpha`
7. `P_beta`
8. `P_gamma`
9. `P_total`
10. `rel_delta`
11. `rel_theta`
12. `rel_alpha`
13. `rel_beta`
14. `rel_gamma`
15. `pfd`
16. `skew`
17. `kurtosis`
18. `var`
19. `envelope`

细节要求：

- 输入 shape 保持 `[num_epochs, 1, epoch_samples]`。
- `n_epochs = len(eeg_data) // epoch_samples`；不足一个 epoch 的尾部样本按源码行为丢弃，不参与特征、预测和事件聚合。
- delta: 0.1-4 Hz。
- theta: 4-8 Hz，Nyquist 不足时置 0。
- alpha: 8-16 Hz，Nyquist 不足时置 0。
- beta: 16-32 Hz，Nyquist 不足时置 0。
- gamma: 32-64 Hz，Nyquist 不足或上限不够时置 0。
- `P_total = mean(epoch ** 2)`。
- 相对功率以 `P_total` 分母，`P_total <= 0` 时相对功率置 0。
- Hilbert envelope 取均值。
- 最后必须 `np.nan_to_num(..., nan=0, posinf=0, neginf=0)`。
- 最后必须 clip 到 `[-1e6, 1e6]` 并转 `float32`。

### 5.6 预测合同

源码行为：

- 先 `features_scaled = scaler.transform(features)`。
- 再 `predictions_proba = model.predict_proba(features_scaled)[:, 1]`。
- `predictions = (predictions_proba >= 0.5).astype(int)`。

迁移要求：

- 默认阈值为 0.5。
- 保存每个 epoch 的 `probability_seizure`。
- 保存每个 epoch 的二值 `Stage_Code`，0 = Normal，1 = Seizure。
- 保存模型/scaler 文件指纹、阈值、epoch_length、channel、sfreq、n_epochs。

### 5.7 事件聚合合同

源码 `detect_seizures` 的核心行为：

- 连续 Seizure epoch 形成候选事件。
- 内部常量 `MIN_SEIZURE_EPOCHS = 2`。
- 事件开始秒 = `start_idx * epoch_length`。
- 事件结束秒 = `(end_idx + 1) * epoch_length`，不超过记录总时长。
- 事件统计包括 RMS、最大幅值、起止 UTC、持续秒、起止 epoch。
- 30 分钟窗口统计以事件开始时间计数，并计算 Events/h。
- 返回 `seizure_epoch_mask`。

注意：源码在 ML 初始运行时传 `min_no_seizure_epochs=2`，保存复核结果时传 `min_no_seizure_epochs=3`，但 `detect_seizures` 实际使用内部常量 2。迁移时应以“源码实际行为”为准，并在文档/测试中锁定，避免实现者误以为复核保存时事件最小长度变成 3。

## 6. 人工复核工作台需求

### 6.1 页面建议

不要把所有交互塞进 `module-lab` 卡片。建议新增：

- `frontend/epilepsy-review.html`
- `frontend/epilepsy-review.js`
- `frontend/epilepsy-review.css`

`module-lab` 只负责启动 ML/STD 筛查任务；任务完成后给出“打开复核工作台”的入口。

实验室同步测试入口必须复用同一个工作台。具体方案见：

- `docs/modules/epilepsy_ml_lab_sync_mirror_plan.md`

实验室只允许增加 fixture 选择、一键运行、audit 状态和“实验室同步测试”提示，不允许复制一套 `epilepsy-review-lab.js` 或实验室专用算法。

### 6.2 工作台布局

建议四区布局：

1. 左侧参数与数据区
   - 输入文件
   - workflow: STD / ML
   - epoch length: 3s / 5s
   - EEG/EMG/ACC channel
   - 模型资产版本
   - 非医疗说明

2. 顶部导航区
   - 当前 epoch
   - 跳转到 epoch
   - 上一页/下一页/首页/末页
   - 每页显示 epoch 数：All / 100 / 50 / 30 / 20 / 10 / 5 / 3
   - 时间滑块

3. 中央波形区
   - Stage 分期条：Normal / Seizure
   - EEG 波形
   - EMG envelope
   - ACC 波形
   - EEG spectrogram
   - 事件区间 overlay
   - 鼠标 hover 显示 epoch
   - 框选/高亮选区

4. 右侧事件与复核区
   - 候选事件列表
   - 每个事件起止秒、起止 epoch、持续秒、RMS、最大幅值、来源 ML/STD/manual
   - 点击事件跳转
   - Seizure / Normal 按钮
   - Undo / Redo / Reset
   - 保存复核
   - 导出数据/图片/复核报告

### 6.3 人工修改模型

复核对象必须是 epoch-level 标注，而不是只改事件表。

数据结构建议：

```json
{
  "session_id": "eprev_xxx",
  "task_id": "task_xxx",
  "epoch_length_sec": 5.0,
  "epochs": [
    {
      "epoch_index": 0,
      "start_sec": 0.0,
      "end_sec": 5.0,
      "model_stage_code": 0,
      "review_stage_code": 0,
      "probability_seizure": 0.12,
      "source": "ml"
    }
  ],
  "review_actions": [
    {
      "action_id": "act_xxx",
      "action": "mark_seizure",
      "epoch_indices": [10, 11],
      "before": [0, 0],
      "after": [1, 1],
      "created_at": "2026-06-26T00:00:00Z",
      "actor": "local_user"
    }
  ]
}
```

要求：

- Undo/Redo 基于 action stack。
- Reset 恢复到模型初始结果。
- 保存后用 `review_stage_code` 重新运行事件聚合。
- 原始模型输出不可覆盖，只能追加 reviewed 层。
- 所有人工修改必须有 audit trail。
- 旧桌面源码的 `.cache` 保存疑似只保存 `df_score`，而人工修改主要在 `df_display_score`；07 Web 迁移不得继承这个持久化缺陷，必须保存并重开 reviewed layer。

## 7. 后端/API 设计建议

### 7.1 Runner 层

建议新增：

- `eeg_core/analysis/epilepsy_ml.py`
- `worker/tasks/epilepsy_ml.py` 或在 `worker/tasks/epilepsy.py` 内按 method 分派

核心函数：

```python
run_epilepsy_ml(input_path, output_dir, parameters) -> dict[str, Path]
```

产物建议：

- `tables/epilepsy_ml_epoch_scores.csv`
- `tables/epilepsy_ml_events.csv`
- `tables/epilepsy_ml_window_stats_30min.csv`
- `tables/epilepsy_ml_features.csv`
- `reproducibility/epilepsy_ml_summary.json`
- `reproducibility/epilepsy_ml_model_manifest.json`
- `reproducibility/parameters.json`
- `review/epilepsy_review_session.seed.json`

### 7.2 Review session API

建议新增 07 内部 API，不经过 router/IPC：

- `POST /api/epilepsy/review-sessions/from-task/{task_id}`
  - 从 ML/STD 任务产物创建复核会话。
- `GET /api/epilepsy/review-sessions/{session_id}`
  - 获取 session metadata、事件列表、epoch 摘要。
- `GET /api/epilepsy/review-sessions/{session_id}/waveform`
  - 参数：`start_sec`、`duration_sec`、`channels`、`decimate`。
  - 返回前端可绘图的窗口数据，不一次性传全量大文件。
- `PATCH /api/epilepsy/review-sessions/{session_id}/epochs`
  - 批量修改 epoch 标注。
- `POST /api/epilepsy/review-sessions/{session_id}/undo`
- `POST /api/epilepsy/review-sessions/{session_id}/redo`
- `POST /api/epilepsy/review-sessions/{session_id}/reset`
- `POST /api/epilepsy/review-sessions/{session_id}/save`
  - 重新计算 reviewed events 和 30 分钟统计。
- `POST /api/epilepsy/review-sessions/{session_id}/export`
  - 导出复核包。

### 7.3 Waveform API 合同

```json
{
  "session_id": "eprev_xxx",
  "start_sec": 100.0,
  "duration_sec": 30.0,
  "sfreq": 500.0,
  "decimate": 5,
  "channels": [
    {
      "name": "EEG1",
      "kind": "eeg",
      "unit": "uV",
      "times_sec": [100.0, 100.01],
      "values": [1.2, 1.3]
    }
  ],
  "epoch_overlays": [
    {
      "epoch_index": 20,
      "start_sec": 100.0,
      "end_sec": 105.0,
      "review_stage_code": 1
    }
  ],
  "event_overlays": [
    {
      "event_id": "evt_001",
      "start_sec": 100.0,
      "end_sec": 115.0,
      "source": "ml_candidate"
    }
  ]
}
```

### 7.4 复核导出包

复核包必须包含：

- `reviewed_epoch_scores.csv`
- `reviewed_events.csv`
- `reviewed_window_stats_30min.csv`
- `review_actions.jsonl`
- `review_session_manifest.json`
- `model_manifest.json`
- `non_medical_scope.txt`
- 可选：当前视窗 SVG/PNG、report HTML。

## 8. 前端高保真要求

### 8.1 必保留交互

- 选择 epoch length 3/5。
- 选择 EEG/EMG/ACC 通道。
- 运行后显示分期条。
- 显示 EEG、EMG envelope、ACC、时频图。
- 每页 epoch 数选择。
- 当前 epoch 输入和跳转。
- 鼠标 hover 显示 epoch。
- 点击事件跳到对应时间段。
- 支持 Seizure/Normal 人工标注。
- 支持 Shift+1 Normal、Shift+2 Seizure 的快捷键映射。
- 支持 undo、redo、reset。
- 支持保存复核结果和重新加载历史。
- 支持导出数据和图片。

### 8.2 Web 可接受差异

以下可以不是像素级复刻，但必须保留功能含义：

- PyQtGraph 可替换为 Canvas / SVG / Plotly / uPlot / ECharts，但必须能流畅显示窗口数据和 overlay。
- `.cache` pickle 不应直接搬到 Web；应转为 JSON manifest + artifact 文件。
- 桌面弹窗保存路径改为浏览器下载或服务器 artifact。
- 旧版窗口最大化改为 Web 工作台全屏布局。

## 9. 集成阶段

### Phase A: 源码合同冻结

产物：

- 本文档。
- `model_manifest.json` 草案。
- 源码 parity 样例数据。

验收：

- 07 PM 能看到 ML 算法链路、UI 链路、测试链路。
- 模型资产 hash 已记录。
- 不改 router/IPC。

### Phase B: ML runner 高保真迁移

产物：

- `epilepsy_ml.py`
- model/scaler 资产目录
- parity test
- ML task artifacts

验收：

- 同一输入下，特征矩阵、概率、Stage_Code、事件表与源算法一致或差异可解释。

### Phase C: 复核 session API

产物：

- Review session API
- waveform window API
- reviewed 保存/导出
- audit trail

验收：

- 可从任务产物创建 session。
- 可修改 epoch，保存后重新生成事件表。
- 原始模型输出不被覆盖。

### Phase D: 前端工作台

产物：

- `epilepsy-review.html/js/css`
- module-lab 到工作台入口
- module-lab 实验室同步测试入口，复用同一个 `epilepsy_ml_screening` workflow 和同一个 review workbench

验收：

- 用户可跑 ML、看波形、点事件跳转、人工矫正、保存、导出。
- 用户可在实验室入口用固定 fixture 同步测试同一套能力。

### Phase E: 生产级 E2E

产物：

- 合成测试数据
- 源码 parity evidence
- Web E2E 截图
- 导出包

验收：

- 按测试文档全部通过。

## 10. 风险和处理

| 风险 | 影响 | 处理 |
| --- | --- | --- |
| `pyeeg` 来源不明 | 特征 parity 失败 | 明确依赖来源，或复刻 fallback 并用固定 epoch 比对特征。 |
| `.sav` 依赖 xgboost/sklearn 版本 | 模型加载失败或概率漂移 | 固定依赖版本；记录 model hash；做 load smoke 和概率 parity。 |
| 大文件波形 Web 性能 | 页面卡顿 | waveform window + decimate + lazy loading，不一次性传全量。 |
| 人工修改不可追踪 | 结果不可审计 | review_actions.jsonl 和原始/复核两层结果。 |
| 医疗化表述 | 合规和产品定位风险 | 文案 gate 和报告 gate 必须检查。 |
| 旧版 `.cache` 是 pickle | Web 安全和兼容风险 | 用 JSON manifest/artifact 替代，不开放任意 pickle 上传。 |
| 旧版复核 cache 可能不持久化 `df_display_score` | 人工复核结果重开后丢失 | 07 必须把 reviewed epoch layer、review actions、reviewed events 作为一等产物保存。 |
| 显示层事件边界可能多涂结束 epoch | UI 与事件表不一致 | 独立测试比较 algorithm events 与 display overlay；若修正，需写入变更说明。 |
| 当前 07 已有大量未提交改动 | 合并冲突 | 只做 scoped files；不 reset、不 git add .、不改无关模块。 |

## 11. 独立子智能体核查门禁

算法迁移完成后，必须启动一个独立核查子智能体或等价的独立 verification worker。该 worker 不能是算法实现者，不能只看代码，也不能只看模型文件存在性；必须用构造数据和固定真实 fixture 同时运行源代码与 07 迁移实现，产出可读回的数值对比证据。

### 11.1 核查目标

核查目标是确认“高保真迁移”不是近似复写，而是源码行为逐项复制：

1. 模型/scaler 文件字节级一致：文件大小和 SHA256 必须一致。
2. 模型选择一致：3s 加载 3s model/scaler，5s 加载 5s model/scaler，非 3/5 的策略与需求文档一致。
3. 特征提取一致：19 个特征名、顺序、滤波频段、NaN/Inf 处理、clip、dtype 与源码一致。
4. 单位链一致：EDF/BDF 导入后的微伏转换、ACC 缩放、低/高采样率处理、尾部样本截断均与源码或批准变更一致。
5. scaler 输出一致：同一特征矩阵经过 scaler 后的结果在 tolerance 内一致。
6. 模型概率一致：`predict_proba[:, 1]` 在 tolerance 内一致。
7. 阈值分类一致：`probability >= 0.5` 的 Stage_Code 完全一致。
8. 事件聚合一致：事件起止 epoch、起止秒、持续时间、RMS、最大幅值、30 分钟统计一致或差异有明确原因。
9. 复核后重算一致：人工修改后的 reviewed epoch set 重新聚合，不能覆盖原始模型输出。
10. 显示 overlay 一致或有批准变更：特别检查结束边界 epoch 是否被额外显示。

### 11.2 构造数据要求

核查 worker 必须构造或准备至少以下 fixture：

- 全 Normal 数据：确认不会生成事件。
- 单个 Seizure epoch：确认不会生成事件。
- 连续两个 Seizure epoch：确认刚好生成 1 个事件。
- 文件末尾事件：确认 end_sec 不超过总时长。
- 高幅模拟片段：确认 waveform/event overlay 能定位到候选区间。
- 3s 和 5s 两套 epoch_length fixture：分别覆盖两套模型。
- 含尾部不足一个 epoch 的数据：确认尾部被丢弃或批准行为变更。
- 含 EEG3/EEG1/ACC0 通道名的数据：确认默认通道选择。

### 11.3 核查输出

核查 worker 必须输出：

```text
epilepsy_ml_independent_audit/
  asset_hash_check.json
  source_runner_outputs/
    features.csv
    scaled_features.csv
    probabilities.csv
    epoch_scores.csv
    events.csv
  qlanalyser_runner_outputs/
    features.csv
    scaled_features.csv
    probabilities.csv
    epoch_scores.csv
    events.csv
  diffs/
    feature_diff.json
    scaled_feature_diff.json
    probability_diff.json
    stage_code_diff.json
    event_diff.json
  verdict.json
```

`verdict.json` 必须包含：

- `accepted: true|false`
- `blocking_differences`
- `tolerance_used`
- `asset_hashes`
- `source_commit_or_path`
- `target_commit_or_path`
- `non_medical_scope_checked`

### 11.4 阻断条件

出现以下任一情况，不能进入生产级验收：

- 模型/scaler hash 不一致且没有明确批准的模型升级记录。
- 特征列顺序不同。
- Stage_Code 不一致且无法解释。
- 事件起止时间不同且不是浮点 rounding 差异。
- 人工复核保存覆盖了原始模型输出。
- 人工复核保存后重新打开丢失 reviewed layer。
- 只做了代码审查，没有构造数据对比。
- 实现者自测代替独立核查。

## 12. 生产级完成定义

达到以下条件才算“ML 癫痫分析迁移完成”：

1. ML 模型资产 hash 检查通过。
2. 特征提取 parity 测试通过。
3. 概率和 Stage_Code parity 测试通过。
4. 事件聚合 parity 测试通过。
5. 07 后端任务能产出 ML artifacts。
6. 复核 session 能从 task 创建。
7. 波形窗口可加载并带 overlay。
8. 人工 Seizure/Normal 修改可保存、撤销、重做、重置。
9. 保存后 reviewed events 重新计算。
10. 导出包包含原始模型结果、复核结果、audit trail、模型 manifest、非医疗说明。
11. Web E2E 可用截图和 JSON readback 证明。
12. 不影响 router / Headroom / IPC。
13. 独立子智能体核查完成，并提交 source-vs-target 数值 parity 证据。
