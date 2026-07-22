# contracts — 统一模块契约（阶段 2）

阶段 2 只建立契约，**不搬算法**。这些契约形式化工作区里已经存在的三套事实约定
（见上一级 README），并消除“同名不同义”。所有 schema 采用 JSON Schema
`2020-12`，与现有 `schema_version` 字符串约定并存、可平滑升级。

## 契约清单

| 目录 | 契约 | 作用 | 主要现有来源 |
| --- | --- | --- | --- |
| `module-manifest/` | `ModuleManifest` + `registry` | 每个功能包的身份、生命周期、层次、入口、边界 | 前端 `research_module_manifest.json`、后端 `module_name` |
| `eeg-source/` | `EEGSourceDescriptor` | 数据来源：格式、哈希、采样率、时长、通道、单位 | qeeg `_base_summary.source`、web-main `source_metadata` |
| `channel-montage/` | `ChannelMontageReference` | 通道集合、蒙太奇、参考方案、单位、坐标 | web-main `rereference.py`、qeeg `qc` scalp 处理 |
| `preprocessing-provenance/` | `PreprocessingProvenance` | 滤波/重采样/重参考/坏导/坏段/保留区间/ICA-ICLabel | qeeg `qc.py` trace、web-main `preprocess/` |
| `result-envelope/` | `AnalysisResultEnvelope` | 方法 ID + profile + 版本 + **三类状态分离** | web-main `reproducibility` result、qeeg summary |
| `artifact-manifest/` | `ArtifactManifest` | JSON/CSV/SVG/PNG/HTML/PDF/ZIP 工件登记 + sha256 | web-main `manifest.json`、qeeg `visual_manifest` |
| `lifecycle-safety/` | `LifecycleState` + `SafetyGate` | 生命周期取值、安全门措辞、forbidden claims | qeeg `safety_gate`、`blocked_*` 状态族 |
| `frontend-backend-adapter/` | `ModuleAdapterBinding` | 前端入口 ↔ API 路由 ↔ service ↔ report section、feature flag、权限 | 前端 `statusLevel`、后端路由注册 |

## 命名规范：消除同名不同义

`psd`、`band_power`、`preprocess`、`connectivity`、`pac`、`report`、`pipeline`、
`registry`、`status` 在不同项目/profile 下含义不同，不再作为含混稳定 ID。稳定标识统一为：

```text
<namespace>.<estimator>.<profile>@<schema_version>
```

- `namespace`：`platform` / `feature` / `lab` / `shared` / `research` / `assets` /
  `governance`（与阶段 1 总账 module_id 前缀一致）。
- `estimator`：具体方法，如 `welch-psd`、`multitaper-psd`、`tort-pac`、`mvl-pac`、
  `wpli-connectivity`、`morlet-tfr`。
- `profile`：输入/参数语义档位，如 `resting-eyes-open`、`spectral-only`、
  `full-qc-recovered`、`event-locked`。
- `schema_version`：结果字段结构版本，如 `v0.1`、`v1.0`。

### 已知冲突登记（阶段 4 迁移时逐条对照，不得静默合并）

| 含糊名 | 冲突实例 | 处置 |
| --- | --- | --- |
| `psd` | web-main `analysis/psd.py`（Welch）vs qeeg `spectral.py` | 拆为 `feature.welch-psd.*` 与 `research.qeeg-spectral.*`，不同 schema |
| `pac` | web-main `pac.py` v1、`pac_v2.py`、qeeg `coupling.py`（Tort/MVL/n:m） | 每个 estimator 独立 ID，禁止粗暴合并数值语义 |
| `preprocess` | web-main `preprocess/` vs qeeg `preprocess.py`/`qc.py` | 统一到 `PreprocessingProvenance`，保留各自 profile |
| `connectivity` | web-main `connectivity.py` vs qeeg `connectivity.py` | 按 estimator + 参考方案分档 |
| `pipeline` | qeeg `spectral_baseline` vs `recovered_full_recording` | 明确不是同一流程；输入语义不同，profile 区分 |
| `report` | web-main `report/` vs qeeg `report.py`/`expanded_report.py` | 渲染层与分析层分离；共享校验后归入 `shared/` |
| `safety_gate` | qeeg `AUTO_PASS_BLOCKED` | 纳入 `SafetyGate` 契约，`blocked_*` 不得包装成通过 |

## 三类状态分离（`AnalysisResultEnvelope` 的核心）

绝不把三种状态混为一谈：

- **execution_status**：`completed / failed / blocked_missing_dependency /
  blocked_ica_fit / blocked_classification_unavailable / blocked_exclusion_limit`
  —— 这次运行发生了什么（技术层）。
- **validation_status**：`not_validated / numeric_checked / contract_verified /
  golden_matched` —— 结果被验证到什么程度（证据层）。
- **lifecycle_status**：`draft / internal_validation / beta / stable / deprecated`
  —— 方法整体成熟度（产品/科研层）。

`execution_status == completed` **不**等于结果可信，更不等于可临床使用。

## 校验

`validate_contracts.py` 对本目录所有 `*.schema.json` 做 JSON Schema 元校验，并校验随附的
`*.example.json` 样例符合对应 schema。CI/本地都应在契约改动后运行。
