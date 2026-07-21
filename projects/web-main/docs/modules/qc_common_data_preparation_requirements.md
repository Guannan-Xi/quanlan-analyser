# QC 公共数据准备工作台需求详细设计

更新时间：2026-06-18
状态：需求规格 / 前后端详细设计稿 / 三轮评审后修订版
适用范围：真实 EEG 数据操作服务，不是静态展示页
评审方式：按产品易用性、前后端工程契约、MNE/EEG 科研可靠性三组视角完成 3 轮评审

## 1. 背景与意图

本需求将 QC 从“质量结论页面”升级为“公共数据准备工作台”。用户在进入 PSD、ERP、TFR、PAC、Connectivity 之前，先在 QC 阶段完成所有分析共同需要的数据检查、标记和预览。

本阶段只处理**公共预处理**，不处理各分析独有的预处理：

- PSD 独有的 Welch 参数、频段定义、相对功率等放在 PSD。
- ERP 独有的 event_id 语义、epoch、baseline、reject、ROI、component window 放在 ERP。
- TFR / PAC / Connectivity 的 baseline、surrogate、连接性指标等放在各自模块。

QC 阶段负责建立一份所有后续分析共同认可的：

```text
data_preparation_plan.json
```

该方案记录文件状态、通道状态、坏导、坏段、annotation 处理、波形预览窗口、滤波/陷波预览参数，以及用户主动保存的当前预览波形片段。默认不修改原始 EEG 文件。

## 2. 产品目标

### 2.1 用户目标

用户可以在一个页面内完成：

1. 上传或选择真实 EEG 文件。
2. 查看 metadata、通道和事件/annotation 概览。
3. 在真实波形窗口中进行横轴/纵轴缩放、时间跳转和通道选择。
4. 填写滤波/陷波参数并预览滤波效果。
5. 多选并标记坏导。
6. 框选并标记坏段。
7. 查看已有 annotations，并决定沿用、忽略或转换为坏段。
8. 保存当前预览波形片段，作为可回放、可复核、可写入报告的证据。
9. 保存公共数据准备方案，供后续 PSD / ERP / TFR 等模块复用。

### 2.2 系统目标

1. 所有波形和滤波结果来自后端真实 EEG 数据服务。
2. 大文件按需加载窗口，不把全量数据一次性送到浏览器。
3. 原始 EEG 文件不可被覆盖。
4. 用户操作写入结构化方案，所有参数可复现。
5. 后续分析任务可引用同一份数据准备方案。
6. 失败状态必须给出用户可理解原因和可恢复建议。

## 3. 范围边界

### 3.1 本阶段纳入 QC 公共数据准备

| 能力 | 是否 P0 | 说明 |
| --- | --- | --- |
| 文件 metadata 检查 | 是 | 文件、采样率、时长、通道、事件/annotation 概览 |
| 通道类型检查 | 是 | P0 自动识别、展示和保存已知类型；P1 增强批量人工编辑 |
| 通道命名标准化 | 是 | P0 提示命名风险并保存 rename map；P1 增强批量重命名 UI |
| 单位/幅值合理性检查 | 是 | 检查异常幅值和缩放风险 |
| 真实波形预览 | 是 | 后端按窗口返回数据 |
| 横轴缩放/平移 | 是 | 改变 start_sec/duration_sec 后重新请求窗口 |
| 纵轴缩放 | 是 | 前端显示比例，不改变数据 |
| 滤波/陷波预览 | 是 | 只作用于当前预览窗口 |
| 坏导多选标记 | 是 | 记录 bad_channels，不直接删除原始通道 |
| 坏段框选标记 | 是 | 记录 bad_segments，不直接裁剪原始文件 |
| 当前预览片段保存 | 是 | 保存用户当前看到的窗口数据、视图参数、标注状态和图形快照，不裁剪原始文件 |
| annotations 显示与处理 | 是 | 沿用/忽略/转坏段 |
| 数据不连续检查 | P0 基础 / P1 增强 | P0 显示文件已有 boundary/BAD_ACQ_SKIP 等注释；P1 做更完整自动检测 |
| montage 选择与匹配检查 | P1 | 只记录模板与匹配结果 |
| 保存 data_preparation_plan | 是 | 后续分析引用；P0 必须有 revision 冲突检测，P1 增加历史版本列表 |

### 3.2 不放入 QC 公共数据准备

| 能力 | 放到哪里 |
| --- | --- |
| ERP event_id 语义确认 | ERP |
| ERP epoch / baseline / reject / drop log | ERP |
| ERP ROI 和 component window | ERP |
| PSD Welch 参数、频段、相对功率 | PSD |
| TFR baseline、frequency、n_cycles | TFR |
| PAC surrogate/null model | PAC |
| Connectivity metric、volume conduction 控制 | Connectivity |
| ICA 成分剔除 | 后续高级清洗，不进 P0 |

## 4. 前端需求

### 4.1 页面名称与入口

页面名称建议：

```text
QC 与数据准备
```

入口位于体验中心和正式工作台的 EEG 文件详情页。页面必须连接真实后端 API，不允许只展示静态图。

### 4.2 页面布局

```text
QC 与数据准备
├─ 文件与 metadata
├─ 波形操作窗口
│  ├─ 通道选择
│  ├─ 横轴缩放 / 平移 / 跳转
│  ├─ 纵轴缩放
│  ├─ 原始/滤波/叠加显示
│  ├─ 坏段框选
│  ├─ 保存当前预览片段
│  └─ 已保存片段列表
├─ 公共准备参数
│  ├─ 通道类型
│  ├─ 通道命名
│  ├─ 单位检查
│  ├─ 滤波/陷波预览
│  ├─ 坏导标记
│  ├─ 坏段列表
│  └─ annotation 处理
├─ 质量与下一步
└─ 保存/下载 data_preparation_plan
```

### 4.3 文件与 metadata 区

必须显示：

- 文件名、格式、大小。
- 采样率、时长、通道数、EEG 通道数。
- annotations 数量、事件摘要。
- 原始 highpass / lowpass 信息。
- 当前参考信息，如可读取。
- 读取器与 MNE 版本。

用户操作：

- 上传新文件。
- 选择已有文件。
- 刷新 metadata。
- 下载 metadata JSON。

### 4.4 波形操作窗口

#### 4.4.1 波形显示

必须显示真实 EEG 窗口数据：

- 横轴：秒。
- 纵轴：μV 或明确显示偏移规则。
- 多通道垂直偏移，避免重叠。
- 通道名固定在左侧或波形旁。
- annotations / events 以竖线或半透明区域显示。
- 坏导通道用特殊样式标记。
- 坏段用半透明遮罩显示。
- 单次交互预览最多支持 64 个通道；超过 64 个通道时前端必须提示用户缩小通道范围或分批查看。

#### 4.4.2 横轴缩放与平移

支持：

- 鼠标滚轮缩放时间窗。
- 拖动时间轴平移。
- 上一段 / 下一段。
- 快捷窗口：5s、10s、30s。P0 单次窗口最长 30s；更长时间概览应作为 P1 的低分辨率导航条单独设计。
- 输入 `start_sec` 和 `duration_sec`。
- 跳转到 annotation / bad segment / event 附近。

实现原则：每次改变窗口后重新向后端请求当前窗口数据，不在浏览器持有全量 EEG。单次请求最多 64 个通道，后端必须再次校验该上限。

#### 4.4.3 纵轴缩放

支持：

- 纵轴倍率滑条。
- 快捷值：50 μV、100 μV、200 μV、自动。
- 每通道统一比例，后续可扩展单通道比例。

纵轴缩放仅改变显示，不改变数据。

#### 4.4.4 滤波预览显示模式

支持：

- 原始波形。
- 滤波后波形。
- 原始/滤波叠加。
- 上下分屏对比。

页面必须标注：

```text
滤波仅用于当前窗口预览，不会修改原始文件，也不会自动成为 PSD/ERP 的正式滤波参数。
```

#### 4.4.5 当前预览波形片段保存

用户可以把当前正在查看的波形窗口保存为“预览片段”。这里的“保存片段”不是裁剪或覆盖原始 EEG 文件，而是保存当前窗口的可回放证据包。

**术语统一：** 后续统一称为“预览片段”。“快照”只指预览片段中的图形文件，不再作为独立业务对象，避免出现 `snapshot` 和 `preview_segment` 两套保存逻辑。

触发入口：

- 波形窗口工具栏提供 `保存当前片段`。
- 用户标记坏导、框选坏段或切换滤波预览后，页面提示“是否保存当前片段作为证据”。
- 保存方案时，如果当前窗口有未保存的重要操作，提醒用户可一并保存片段。

保存时用户可填写：

- 片段名称，例如“Fp1 噪声复核”“眨眼坏段示例”。
- 片段说明。
- 标签：`artifact_review`、`bad_channel_evidence`、`bad_segment_evidence`、`filter_check`、`teaching_example`、`report_evidence`、`other`。
- 是否加入报告候选。

片段必须保存：

- `segment_id`、`input_file_id`、`plan_id`、`plan_revision`。
- 原始文件指纹：文件大小、上传记录 ID、可选 sha256、读取器和 MNE 版本。
- 当前时间窗：`start_sec`、`duration_sec`、`end_sec`。
- 当前通道列表，最多 64 个。
- 当前显示参数：纵轴比例、显示采样率、显示模式、通道顺序。
- 当前滤波预览参数和 `preview_only=true` 标记。
- 当前坏导、坏段、annotation/event 可视状态。
- 显示级窗口数据，用于快速回放。
- 原始采样率窗口数据的压缩产物，优先使用 `.npz` 或 `.fif`；如果因为体积策略不保存，必须在 metadata 中明确 `raw_window_copy_saved=false`，并保留可从原始文件重读的完整索引。
- 如开启滤波预览，同时保存滤波后显示数据；滤波数据必须标记为 preview-only。
- 可视化图形文件 SVG；PNG 可作为报告兼容格式。
- 创建时间、操作者、备注。

片段保存后页面必须支持：

- 片段列表。
- 点击片段后恢复当时的窗口、通道、缩放和显示模式。
- 删除片段。
- 修改片段名称、说明、标签和是否进入报告候选。
- 下载片段 metadata、显示数据、原始窗口压缩数据和图形文件。
- 当原始文件不存在、plan revision 不一致或片段产物缺失时，给出明确的不可回放原因。

### 4.5 通道选择与坏导标记

#### 4.5.1 通道选择

支持：

- 通道搜索。
- 单选/多选。
- 按类型筛选：EEG/EOG/ECG/EMG/Stim/Misc。
- 按脑区快捷选择：frontal、central、parietal、occipital、temporal。
- 一键显示前 N 个 EEG 通道。

#### 4.5.2 坏导多选

用户可以：

- 勾选一个或多个通道。
- 批量标记为坏导。
- 选择原因：flat、extreme_amplitude、noisy、dropout、user_review。
- 取消坏导标记。
- 查看系统候选坏导。

坏导标记不删除通道，只进入 plan。

### 4.6 坏段框选

用户在波形窗口中拖拽选择时间范围。松开后弹出确认面板：

```text
标记坏段
放大查看
取消
```

标记坏段时需要选择原因：

- eye_blink
- movement
- muscle_artifact
- electrode_pop
- saturation
- external_noise
- discontinuity
- other

坏段必须能编辑、删除、跳转查看。

### 4.7 Annotation 处理

页面显示文件已有 annotation：

- onset。
- duration。
- description。
- 是否包含 `BAD`。

用户可以选择：

- 沿用。
- 忽略。
- 转为坏段。

转换为坏段后写入 `bad_segments`，并保留来源 `annotation`。

### 4.8 公共数据准备方案保存

页面提供：

- 保存方案。
- 另存为新版本。
- 下载 JSON。
- 恢复上次方案。
- 重置为默认。

保存成功后显示：

- plan_id。
- 创建时间。
- 操作者/来源。
- 后续分析是否可用。

### 4.9 下一步建议

页面基于 QC 和 plan 给出：

- PSD 是否可继续。
- ERP 是否可继续，是否缺少事件。
- 是否坏导过多。
- 是否坏段过多。
- 是否需要人工复核。

## 5. 前端状态模型

```js
state = {
  fileId: "",
  metadata: null,
  planRevision: null,
  viewport: {
    startSec: 0,
    durationSec: 12,
    verticalScaleUv: 100,
    displaySfreq: 250,
    mode: "raw" // raw | filtered | overlay | stacked
  },
  selectedChannels: [],
  channelTypes: {},
  channelRenames: {},
  unitScaling: { enabled: false, factor: 1.0 },
  filterPreview: {
    enabled: true,
    bandpass: { enabled: true, lFreq: 1.0, hFreq: 40.0, method: "fir" },
    notch: { enabled: true, freqs: [50.0], method: "fir" }
  },
  badChannels: [],
  badSegments: [],
  annotationActions: [],
  savedPreviewSegments: [],
  activePreviewSegmentId: null,
  montage: { mode: "not_set", template: null },
  plan: null,
  unsavedChanges: false,
  messages: []
};
```

## 6. 后端需求

### 6.1 总体原则

1. 后端读取真实 EEG 文件。
2. 后端只返回当前窗口波形，不返回整段 EEG。
3. 滤波/陷波预览只作用于复制的窗口数据。
4. 原始文件不可被修改。
5. data preparation plan 单独保存，可以被后续分析引用。
6. 所有输出进入统一 `result.json`、`manifest.json`、`log.txt` 和 reproducibility 文件。

### 6.2 数据模型：`DataPreparationPlan`

```json
{
  "schema_version": "qlanalyser-data-preparation-v0.2",
  "plan_id": "prep_xxx",
  "input_file_id": "eeg_xxx",
  "project_id": "proj_xxx",
  "revision": 1,
  "created_at": "2026-06-18T00:00:00Z",
  "updated_at": "2026-06-18T00:00:00Z",
  "scope": "common_qc_preparation",
  "status": "draft | confirmed",
  "source_file": {
    "file_id": "eeg_xxx",
    "size_bytes": 12345678,
    "sha256": "optional_when_available",
    "reader": "mne.io.read_raw_edf",
    "mne_version": "x.y.z"
  },
  "metadata_review": {
    "sfreq": 500.0,
    "duration_sec": 300.0,
    "n_channels": 64,
    "n_eeg_channels": 62,
    "annotations_count": 12,
    "channel_types_confirmed": false,
    "channel_names_reviewed": false
  },
  "viewport": {
    "start_sec": 10.0,
    "duration_sec": 12.0,
    "channels": ["Fz", "Cz", "Pz"],
    "display_sfreq": 250.0,
    "vertical_scale_uv": 100.0,
    "display_mode": "raw | filtered | overlay | stacked"
  },
  "channel_types": {
    "VEOG": "eog",
    "ECG": "ecg"
  },
  "channel_renames": {
    "EEG Fp1": "Fp1"
  },
  "unit_scaling": {
    "enabled": false,
    "factor": 1.0,
    "reason": "no scaling applied",
    "confirmed_by_user": false
  },
  "montage": {
    "mode": "template | custom | not_set",
    "template": "standard_1020",
    "matched_channels": [],
    "missing_channels": []
  },
  "filter_preview": {
    "enabled": true,
    "preview_only": true,
    "bandpass": {"enabled": true, "l_freq": 1.0, "h_freq": 40.0, "method": "fir"},
    "notch": {"enabled": true, "freqs": [50.0], "method": "fir"},
    "edge_policy": {"pad_before_sec": 2.0, "pad_after_sec": 2.0, "trim_to_requested_window": true}
  },
  "bad_channels": [
    {"name": "Fp1", "reason": "noisy", "source": "user", "note": "large drift"}
  ],
  "bad_segments": [
    {"id": "badseg_001", "start_sec": 12.4, "end_sec": 14.8, "reason": "muscle_artifact", "source": "user", "applies_to": "all_channels", "channels": [], "note": "high frequency burst"}
  ],
  "annotation_actions": [
    {"annotation_key": "ann_0001_12.400_2.400_BAD_artifact", "action": "convert_to_bad_segment", "reason": "BAD_artifact"}
  ],
  "saved_preview_segments": [
    {
      "segment_id": "seg_001",
      "name": "Fp1 噪声复核",
      "tags": ["bad_channel_evidence"],
      "time_window": {"start_sec": 10.0, "end_sec": 22.0, "duration_sec": 12.0},
      "channels": ["Fp1", "Fp2", "Fz", "Cz"],
      "display": {"display_sfreq": 250.0, "vertical_scale_uv": 100.0, "display_mode": "overlay"},
      "filter_preview": {"enabled": true, "preview_only": true},
      "artifacts": {
        "metadata_json": {"artifact_id": "art_seg_001_meta", "path": "data/preview_segments/seg_001_metadata.json"},
        "display_data_json": {"artifact_id": "art_seg_001_display", "path": "data/preview_segments/seg_001_display.json"},
        "raw_window_data": {"artifact_id": "art_seg_001_raw", "path": "data/preview_segments/seg_001_raw.npz"},
        "filtered_display_json": {"artifact_id": "art_seg_001_filtered", "path": "data/preview_segments/seg_001_filtered_display.json"},
        "figure_svg": {"artifact_id": "art_seg_001_svg", "path": "figures/preview_segments/seg_001.svg"},
        "figure_png": {"artifact_id": "art_seg_001_png", "path": "figures/preview_segments/seg_001.png"}
      },
      "source_plan_revision": 1,
      "include_in_report": true,
      "note": "保存当前窗口用于说明 Fp1 噪声判断依据。"
    }
  ],
  "discontinuities": [],
  "next_step_recommendation": {
    "psd": {"status": "allowed | needs_review | blocked", "reasons": []},
    "erp": {"status": "allowed | needs_events | needs_review | blocked", "reasons": ["events_not_confirmed"]},
    "tfr": {"status": "planned", "reasons": ["module_not_enabled_in_v0.1"]}
  },
  "warnings": []
}
```

### 6.3 API 设计

#### 6.3.1 获取 metadata

已有接口：

```http
GET /api/eeg/files/{file_id}/metadata
```

需要补充或保证返回：

- 通道名。
- 通道类型。
- 原始 highpass / lowpass。
- annotations 摘要。
- events 摘要，如可提取。
- amplitude range / unit risk。
- bad channel candidates。

#### 6.3.2 波形窗口预览

可以继续使用现有 task：

```http
POST /api/tasks
workflow_id = qc_waveform_preview
```

建议后续增加直连 endpoint：

```http
POST /api/analysis/qc/waveform-preview
```

输入：

```json
{
  "input_file_id": "eeg_xxx",
  "preview": {
    "start_sec": 10.0,
    "duration_sec": 12.0,
    "channels": ["Fz", "Cz", "Pz"],
    "display_sfreq": 250.0,
    "vertical_scale_uv": 100.0,
    "show_annotations": true,
    "show_events": true
  },
  "bad_channels": [],
  "bad_segments": []
}
```

输出：

```json
{
  "input_file_id": "eeg_xxx",
  "start_sec": 10.0,
  "duration_sec": 12.0,
  "sfreq_original": 500.0,
  "sfreq_display": 250.0,
  "channels": ["Fz", "Cz", "Pz"],
  "unit": "uV",
  "times_sec": [],
  "data_uv": [],
  "annotations": [],
  "events": [],
  "bad_channels": [],
  "bad_segments": []
}
```

约束：

- `channels` 最多 64 个。
- 默认窗口建议 5-30 秒；60 秒只作为用户主动选择的长窗口。
- 返回数据可按 `display_sfreq` 降采样，但必须在响应中写明原始采样率和显示采样率。

#### 6.3.3 滤波预览

可以继续使用现有 task：

```http
POST /api/tasks
workflow_id = qc_filter_preview
```

要求：

- 只处理当前窗口。
- 返回滤波后数据。
- 返回滤波参数和 warnings。
- 不写回原始文件。

#### 6.3.4 保存公共数据准备方案

新增接口：

```http
POST /api/eeg/files/{file_id}/data-preparation-plan
```

请求体为 `DataPreparationPlan` 的可编辑字段，并必须携带 `base_revision`。后端保存前检查当前 plan revision，若已被其他会话更新，返回 `PLAN_REVISION_CONFLICT`，由前端提示用户选择“加载最新方案后合并”或“另存为新版本”。

响应：

```json
{
  "plan_id": "prep_xxx",
  "input_file_id": "eeg_xxx",
  "status": "saved",
  "revision": 2,
  "created_at": "2026-06-18T00:00:00Z",
  "updated_at": "2026-06-18T00:00:00Z"
}
```

#### 6.3.5 获取当前方案

```http
GET /api/eeg/files/{file_id}/data-preparation-plan
```

如果没有方案，返回默认草稿方案，并标记 `is_default=true`、`revision=0`。

#### 6.3.6 方案版本列表

P1：

```http
GET /api/eeg/files/{file_id}/data-preparation-plans
```

P0 只要求单个当前方案加 revision 冲突检测；P1 再提供完整历史版本列表、版本比较和恢复。

#### 6.3.7 保存当前预览片段

新增接口：

```http
POST /api/eeg/files/{file_id}/preview-segments
```

请求体：

```json
{
  "plan_id": "prep_xxx",
  "base_plan_revision": 1,
  "name": "Fp1 噪声复核",
  "note": "保存当前窗口用于说明坏导判断依据。",
  "tags": ["bad_channel_evidence"],
  "include_in_report": true,
  "preview": {
    "start_sec": 10.0,
    "duration_sec": 12.0,
    "channels": ["Fp1", "Fp2", "Fz", "Cz"],
    "display_sfreq": 250.0,
    "vertical_scale_uv": 100.0,
    "display_mode": "overlay"
  },
  "filter_preview": {
    "enabled": true,
    "preview_only": true,
    "bandpass": {"enabled": true, "l_freq": 1.0, "h_freq": 40.0},
    "notch": {"enabled": true, "freqs": [50.0]},
    "edge_policy": {"pad_before_sec": 2.0, "pad_after_sec": 2.0, "trim_to_requested_window": true}
  },
  "bad_channels": [],
  "bad_segments": [],
  "annotation_actions": []
}
```

响应：

```json
{
  "segment_id": "seg_001",
  "input_file_id": "eeg_xxx",
  "plan_id": "prep_xxx",
  "plan_revision": 2,
  "status": "saved",
  "artifacts": {
    "metadata_json": "data/preview_segments/seg_001_metadata.json",
    "display_data_json": "data/preview_segments/seg_001_display.json",
    "raw_window_data": "data/preview_segments/seg_001_raw.npz",
    "filtered_display_json": "data/preview_segments/seg_001_filtered_display.json",
    "figure_svg": "figures/preview_segments/seg_001.svg",
    "figure_png": "figures/preview_segments/seg_001.png"
  },
  "created_at": "2026-06-18T00:00:00Z"
}
```

后端规则：

- 保存片段时重新从原始 EEG 文件读取当前窗口，不能只信任浏览器传回的数据。
- 单个片段最多 64 通道，P0 单段最长 30 秒。
- 保存片段不修改原始 EEG 文件，不生成正式预处理后的 EEG 文件。
- 片段必须写入 plan 的 `saved_preview_segments` 索引，并使 plan revision +1。
- 片段 metadata 必须记录原始采样率、显示采样率、单位、通道顺序、MNE 版本、读取器和滤波 preview-only 状态。
- `display_data_json` 用于前端快速回放，可以按 `display_sfreq` 降采样。
- `raw_window_data` 用于科研复核，优先使用压缩 `.npz` 或 `.fif` 保存原始采样率窗口数据；若服务因体积策略不保存，必须明确返回 `raw_window_copy_saved=false` 并保留从原始文件重读所需索引。
- 如启用滤波预览，应保存滤波后的显示级数据；滤波预览结果不得被后续 PSD/ERP 自动当作正式输入。
- 片段图形必须能独立下载，用于报告、复核和教学。
- 若 `base_plan_revision` 不是最新，返回 `PLAN_REVISION_CONFLICT`，避免多个对话或多个用户互相覆盖。

获取片段列表：

```http
GET /api/eeg/files/{file_id}/preview-segments
```

获取单个片段：

```http
GET /api/eeg/files/{file_id}/preview-segments/{segment_id}
```

删除片段：

```http
DELETE /api/eeg/files/{file_id}/preview-segments/{segment_id}
```

#### 6.3.8 后续分析引用方案

PSD / ERP / TFR 等 task 参数增加：

```json
{
  "data_preparation_plan_id": "prep_xxx"
}
```

后续分析读取该 plan，但只应用公共部分：bad_channels、bad_segments、channel types、channel renames、annotation decisions。分析专属滤波、epoch、baseline 仍在各自模块决定。

## 7. 后端处理规则

### 7.1 通道类型

- 保存用户确认的 channel_types。
- 应用于后续分析前的 Raw copy。
- 未确认时使用 MNE 读取结果，但报告中标记 `channel_types_confirmed=false`。

### 7.2 通道重命名

- 保存 rename map。
- 校验重命名后不能重复。
- 校验不能产生空通道名。
- 后续分析按 rename 后通道名匹配 ROI / montage。

### 7.3 坏导

- 保存 bad_channels。
- 后续分析默认排除 bad channels。
- 插值不是公共 P0，不在 QC 自动执行。

### 7.4 坏段

- 保存 bad_segments。
- 后续分析默认将其作为 annotations 或时间 mask 排除。
- 坏段不能越界，不能 end <= start。
- 重叠坏段保存时可合并或提示用户。

### 7.5 滤波/陷波预览

- 仅作用于当前窗口 copy。
- 保存为 `filter_preview.preview_only=true`。
- 不自动传给 PSD/ERP 作为正式滤波。
- 如果后续模块想沿用，必须在对应分析页面中显式确认。
- 为降低短窗口滤波边缘效应，后端应读取比目标窗口更长的 padding 窗口，滤波后再裁回用户请求的 `start_sec` 到 `end_sec`。
- padding 不足时必须返回 warning，例如文件开头/结尾附近的滤波预览可靠性较低。
- 陷波频率不得默认强制开启；页面可建议 50Hz/60Hz，但用户必须能关闭。

### 7.6 Annotation 处理

- `BAD*` annotations 默认建议转为坏段，但用户可取消。
- 非 BAD annotations 默认只显示，不转坏段。
- 所有转换保留 `source=annotation`。
- MNE annotation 没有天然稳定 ID 时，后端生成 `annotation_key = index + onset + duration + description`，用于前端操作和 plan 保存。

## 8. 错误码

| code | 场景 | 用户提示 |
| --- | --- | --- |
| `FILE_NOT_FOUND` | 文件不存在 | 文件未找到，请重新上传或选择文件。 |
| `UNSUPPORTED_FORMAT` | 格式不支持 | 当前格式暂不支持，请上传 EDF/BDF/FIF/BrainVision/SET/CNT。 |
| `CHANNEL_NOT_FOUND` | 请求通道不存在 | 选择的通道不在文件中，请重新选择。 |
| `WINDOW_OUT_OF_RANGE` | 时间窗越界 | 当前时间窗超出文件范围，请调整起止时间。 |
| `TIME_WINDOW_TOO_LONG` | 时间窗超过上限 | P0 单次预览最长 30 秒，请缩短窗口。 |
| `TOO_MANY_CHANNELS` | 通道超过 64 个 | 当前最多支持同时预览 64 个通道，请减少通道数量或分批查看。 |
| `PREVIEW_SEGMENT_SAVE_FAILED` | 当前预览片段保存失败 | 当前片段保存失败，请稍后重试，或减少通道数量后再保存。 |
| `PREVIEW_SEGMENT_RAW_COPY_SKIPPED` | 原始采样率片段副本未保存 | 当前片段可回放显示数据，但原始采样率副本因体积限制未保存；复核时会从原始文件重读。 |
| `PREVIEW_SEGMENT_NOT_FOUND` | 预览片段不存在 | 未找到该预览片段，请刷新片段列表。 |
| `INVALID_FILTER_PARAMETER` | 滤波参数非法 | 请检查高通、低通和采样率限制。 |
| `BAD_SEGMENT_OUT_OF_RANGE` | 坏段越界 | 坏段必须位于文件时长内。 |
| `BAD_SEGMENT_INVALID` | 坏段 end <= start | 坏段结束时间必须晚于开始时间。 |
| `DUPLICATE_CHANNEL_RENAME` | 重命名冲突 | 多个通道不能重命名为同一个名称。 |
| `PLAN_REVISION_CONFLICT` | 方案版本冲突 | 当前方案已被其他会话更新，请先加载最新方案再保存，或另存为新版本。 |
| `PLAN_SAVE_FAILED` | 方案保存失败 | 当前方案保存失败，请稍后重试。 |

## 9. 输出与复现文件

QC 数据准备任务至少输出：

```text
result.json
manifest.json
log.txt
reproducibility/
  qc_summary.json
  data_preparation_plan.json
  parameters.json
  workflow.json
  software_versions.json
  method_description.txt
data/
  waveform_preview.json
  filter_preview.json
  preview_segments/
    seg_001_metadata.json
    seg_001_display.json
    seg_001_raw.npz
    seg_001_filtered_display.json
figures/
  waveform_raw_preview.svg
  waveform_filter_preview.svg
  preview_segments/
    seg_001.svg
    seg_001.png
tables/
  channel_qc.csv
  annotation_summary.csv
```

## 10. 验收标准

### 10.1 前端验收

- [ ] 可以上传或选择真实 EEG 文件。
- [ ] 可以展示 metadata。
- [ ] 可以显示真实波形数据，而不是静态图。
- [ ] 可以横轴缩放和平移，并重新请求后端窗口。
- [ ] 可以纵轴缩放，且不改变数据。
- [ ] 可以选择/搜索/批量选择通道。
- [ ] 可以填写滤波和陷波参数。
- [ ] 可以运行滤波预览并显示原始/滤波/叠加/上下对比。
- [ ] 可以多选坏导并选择原因。
- [ ] 可以框选坏段并选择原因。
- [ ] 可以显示、转换、忽略已有 annotations。
- [ ] 可以保存当前预览片段，并在片段列表中恢复当时的窗口、通道、缩放和显示模式。
- [ ] 可以下载已保存片段的 metadata、显示数据、原始窗口压缩数据和图形文件。
- [ ] 当方案被其他会话更新时，保存前提示版本冲突，避免覆盖。
- [ ] 可以保存并重新加载 data_preparation_plan。
- [ ] 页面明确说明滤波是预览，不是正式分析滤波。

### 10.2 后端验收

- [ ] metadata endpoint 返回通道、采样率、时长、annotation 摘要。
- [ ] waveform preview 只返回请求窗口。
- [ ] filter preview 不修改原始文件。
- [ ] bad_channels 保存后可再次读取。
- [ ] bad_segments 保存后可再次读取。
- [ ] plan 保存后可被 PSD/ERP task 参数引用。
- [ ] preview segment 保存时由后端重新读取原始文件窗口，生成 metadata、display data、raw window data、filter display data 和图形产物。
- [ ] saved_preview_segments 写入 data_preparation_plan，并可列表、读取、删除。
- [ ] 所有错误返回结构化 code 和用户可读 message。
- [ ] plan 保存和 preview segment 保存均支持 revision 冲突检测。
- [ ] 输出包含 result、manifest、log 和 reproducibility 文件。

### 10.3 性能验收

- [ ] 预览窗口默认不超过 30 秒。
- [ ] 单次预览请求最多支持 64 个通道，超过时前后端都必须拦截并给出清晰提示。
- [ ] 返回点数可按 display_sfreq 降采样，但必须记录原始采样率和降采样策略。
- [ ] 单次 preview 请求在常规 64 通道 EDF 上应在 2 秒内返回。
- [ ] 大文件不一次性 preload 全量到浏览器。

## 11. 分阶段实现

### P0：可用闭环

1. 真实波形窗口。
2. 横轴/纵轴缩放。
3. 滤波/陷波预览。
4. 坏导多选。
5. 坏段框选。
6. 保存当前预览波形片段。
7. 保存 data_preparation_plan，并支持 revision 冲突检测。
8. PSD/ERP 可引用 plan。

### P1：科研增强

1. 通道类型批量编辑与模板化确认 UI。
2. 通道重命名批量导入/导出 UI。
3. annotation 转坏段。
4. montage 模板匹配检查。
5. 数据不连续检查。
6. 方案版本管理。

### P2：高级清洗

1. ICA 成分查看与用户确认。
2. 眼电/心电/肌电自动候选。
3. 坏段自动候选。
4. 派生 `processed_raw.fif` 生成。

## 12. 与现有实现关系

当前已有基础：

- `qc_waveform_preview` 已通过 `/api/tasks` 运行。
- `eeg_core/preprocess/qc_preview.py` 已支持真实窗口读取、滤波预览和 SVG 快照；当前实现仍有 `MAX_CHANNELS=32`，开发时必须提升到需求要求的 64。
- `frontend/qc-lab.html/js/css` 已有第一版上传、参数、预览、产物下载；尚未完成可交互波形操作台、预览片段列表和 plan revision 冲突处理。

下一步开发重点：

1. 前端波形从 SVG 图片升级为可交互 canvas/svg 操作台。
2. 后端新增 data preparation plan 保存/读取接口。
3. 后端新增 preview segments 保存/列表/读取/删除接口。
4. QC preview payload 增加 bad_channels、bad_segments、annotation_actions。
5. PSD/ERP runner 支持引用公共 plan。


## 13. 三轮评审结论

### 第 1 轮：产品与用户流程评审

已解决：

- 将“快照”和“预览片段”统一为一个概念：业务对象叫预览片段，图形文件只是片段的一种产物。
- P0 窗口上限统一为 30 秒，删除 60 秒作为 P0 快捷窗口的冲突；长时间概览放到 P1 单独设计。
- P0/P1 边界重新定义：P0 做自动识别、展示、保存和冲突检测；P1 做批量编辑、版本比较和增强检测。
- 为新手用户保留直白文案：坏导、坏段、保存当前片段、滤波仅预览。

### 第 2 轮：前后端工程契约评审

已解决：

- 单次预览上限统一为 64 通道，前端和后端都必须拦截。
- `data_preparation_plan` 增加 `revision`，保存方案和保存片段都必须做版本冲突检测。
- 预览片段保存接口明确产物：metadata、display data、raw window data、filtered display data、SVG/PNG figure。
- 明确当前实现差距：现有 `qc_preview.py` 仍是 32 通道上限，开发实现时必须同步修改常量、前端限制和验收脚本。

### 第 3 轮：MNE / EEG 科研可靠性评审

已解决：

- 滤波预览增加 padding + trim 规则，降低短窗口滤波边缘效应。
- 片段保存区分显示级数据和原始采样率窗口数据，避免把降采样预览误当作原始数据。
- Annotation 操作增加稳定 `annotation_key` 生成规则。
- 强化“原始 EEG 不修改、坏导坏段只写 plan、滤波 preview-only”的边界，避免误生成不可追溯的预处理结果。
