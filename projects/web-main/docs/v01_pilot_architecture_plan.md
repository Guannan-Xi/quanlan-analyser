# QLanalyser Online v0.1 Pilot 总体架构与分析模块规划

## 1. 任务目标

本文件规划 `QLanalyser Online v0.1 Pilot` 的总体架构、分析模块边界、任务系统、并发目标、输出契约、测试策略和分阶段改造路线。

本轮只做架构审计和文档规划，不做大规模重构，不修改 EEG 分析算法核心逻辑，不直接引入 PostgreSQL、Redis、Celery 或 RQ，不直接修改上传架构，不大改前端 UI，不删除旧代码，不自动 push。

产品与版本口径：

- 产品名：`QLanalyser Online`
- 当前版本：`QLanalyser Online v0.1 Pilot`
- 品牌：`全澜脑科学®` / `QuanLan BrainScience®`
- 平台边界：本平台用于科研数据管理与分析辅助，结果不作为临床诊断依据。

## 2. 当前项目审计摘要

### 2.1 已有能力

- 前端：`frontend/` 静态 HTML/CSS/JavaScript，具备 Pilot 入口、工作台、上传/任务/报告等演示与联调页面。
- API：`backend/main.py` 注册 health、projects、subjects、eeg_files、templates、tasks、artifacts、reports、billing、data_crud、workflow、admin 等路由。
- 状态存储：`backend/services/state_store.py` 使用 `data/state/*.json` 持久化 project、subject、EEG file、task、artifact、report 等 registry。
- 文件存储：上传文件在 `data/uploads/`，分析输出在 `data/derivatives/`，报告包在 `data/reports/`。
- 分析能力：`eeg_core/` 已有读取、metadata、quality、PSD、ERP、HTML report、reproducibility 等能力。
- 报告系统：`backend/services/report_service.py` 能基于 task artifact 生成 HTML 报告和 ZIP 包。
- 验收脚本：`scripts/` 已有 full API、worker/core、persistence、UI、smoke、mojibake 等验收脚本。

### 2.2 缺失或尚未产品化能力

- 任务队列：当前没有真实 Celery/Redis 队列；`worker/celery_app.py` 是本地占位，`worker/tasks/*` 是薄封装。
- 后台任务隔离：`backend/services/task_service.py` 在 API 创建任务时同步运行 QC/PSD/ERP，20 人并发时会阻塞 API worker。
- 数据库：尚未使用正式数据库，JSON state 适合 Pilot 单机演示，不适合多人长时间并发写入。
- 上传大文件：当前上传与 API 进程耦合，尚未实现分片、断点续传、对象存储直传或服务端 multipart。
- 模块统一契约：PSD/ERP/QC 已写入部分 reproducibility 文件，但 `result.json`、`manifest.json`、`log.txt`、统一 `job_type` registry 还未完全收敛。
- 高级分析：TFR、PAC、connectivity 等已在模板中出现规划状态，但不应在 v0.1 Pilot 承诺 stable。
- 多租户与安全：未发现完整组织/用户隔离、权限校验、审计日志和下载授权链路。

## 3. 当前技术栈判断

当前技术栈适合作为 `QLanalyser Online v0.1 Pilot` 的单机可试用 MVP：

```text
Browser static frontend
  -> FastAPI API
  -> local JSON state store
  -> local filesystem uploads/derivatives/reports
  -> MNE-Python eeg_core analysis
```

判断：

- 适合：客户演示、内部验收、小样本 EEG 文件、单机部署、受控并发、算法输出契约打磨。
- 不适合：长期生产多租户、20 人同时上传 500MB 大文件、严格账务、安全合规审计、失败任务自动重试、横向扩容。

v0.1 Pilot 应承认当前边界，不伪装成完整商业化平台。

## 4. 建议 MVP 目标架构

### 4.1 v0.1 Pilot 目标架构

```text
Frontend static app
  - Pilot entry
  - customer workspace
  - task/report views
  - readiness/status hints
        |
FastAPI API
  - project / subject / EEG file
  - task create/status/artifacts
  - report create/download
  - readiness / admin status
        |
Service layer
  - state_store JSON registry
  - storage_service local files
  - task_service local task runner
  - report_service package builder
        |
Analysis boundary
  - metadata_qc
  - waveform snapshot / preview planning
  - psd_bandpower stable
  - erp_beta gated by event readiness
        |
Local filesystem
  - data/uploads
  - data/derivatives
  - data/reports
  - data/state
```

### 4.2 v0.2+ 目标演化

```text
Frontend
  -> API gateway / FastAPI
  -> database-backed state
  -> durable task queue
  -> worker pool
  -> object storage
  -> audit / billing / permission services
```

v0.1 不直接引入这些组件，但应在接口和输出契约上预留迁移空间。

## 5. 分析模块分层建议

建议把分析能力按稳定度分层：

### stable：v0.1 必须稳定

| 模块 | 目标 | 当前状态 | v0.1 要求 |
| --- | --- | --- | --- |
| `metadata_qc` | 读取格式、采样率、通道、时长、annotations、基础质量信息 | 已有 metadata / quality 相关代码 | 失败原因清楚，输出 reproducibility summary |
| `psd_bandpower` | 静息态 PSD、频带功率表、方法说明 | `eeg_core/analysis/psd.py` 已实现 | 固化参数、输出表、summary、method、workflow |
| `report_package` | HTML 报告与 ZIP 可复核包 | `report_service` + `html_report` 已实现 | 统一 manifest，保留 task-relative 路径 |

### beta：v0.1 可提供但必须标注条件

| 模块 | 目标 | 当前状态 | v0.1 边界 |
| --- | --- | --- | --- |
| `erp_beta` | annotation/event 驱动 ERP 指标 | `eeg_core/analysis/erp.py` 已实现 | 仅在事件可读、event_id 合法时启用，报告标注 beta |
| `waveform_snapshot` | 原始波形片段/预览图 | 前端有演示资产，核心规划不足 | 可作为规划或轻量预览，不承诺诊断解释 |
| `preprocess_qc_beta` | 基础滤波、参考、质量提示 | `eeg_core/preprocess/*` 有基础能力 | 避免自动化临床判断，参数必须可复核 |

### experimental：v0.1 不承诺 stable

| 模块 | 原因 | 建议 |
| --- | --- | --- |
| `time_frequency_beta` | 需要 epoch 设计、baseline、统计与可视化约定 | v0.2 以后按 beta 引入 |
| `pac_experimental` | 需要伪迹控制、surrogate、频段选择、统计校正 | 仅规划，不进入 Pilot stable |
| `connectivity_experimental` | 受参考、体积传导、源空间假设影响大 | 仅规划，不进入 Pilot stable |
| `ica_beta` | 自动 ICA 需要人工确认和质量控制 | v0.2 后作为辅助工具，不自动下结论 |

## 6. 推荐模块目录结构差距分析

目标结构可以逐步演化为：

```text
eeg_core/
  common/
    io.py
    schemas.py
    validation.py
    artifacts.py
    logging.py
  modules/
    metadata_qc/
      runner.py
      schema.py
      README.md
      tests/
    waveform_snapshot/
      runner.py
      schema.py
      README.md
      tests/
    psd_bandpower/
      runner.py
      schema.py
      README.md
      tests/
    erp_beta/
      runner.py
      schema.py
      README.md
      tests/
    time_frequency_beta/
      runner.py
      schema.py
      README.md
      tests/
    pac_experimental/
      runner.py
      schema.py
      README.md
      tests/
```

当前项目与目标结构的差距：

- 当前 `eeg_core/analysis/psd.py`、`eeg_core/analysis/erp.py` 是按分析类型分文件，未形成每个模块独立 schema/README/tests。
- 当前共用 IO 在 `eeg_core/io/`，可保留；未来 `eeg_core/common/io.py` 不一定要物理迁移，可先做 facade。
- 当前 artifact 注册在 `backend/services/task_service.py`，分析模块返回 `dict[str, Path]`；未来应由统一 artifact builder 生成 `manifest.json`。
- 当前 worker wrappers 与 API task_service 调用路径并存；未来应收敛到同一 registry。
- 当前 tests 主要以 `scripts/acceptance_*` 存在，模块级 unit tests 还不足。

建议不要立即重构目录。先增加统一接口和契约文档，再按模块逐步迁移。

## 7. 统一模块接口规划

建议未来每个分析模块提供同形接口：

```python
def run_analysis(
    input_file: str,
    parameters: dict,
    output_dir: str,
    context: dict | None = None,
) -> dict:
    ...
```

返回值建议是可 JSON 化对象，而不是只返回 Path：

```python
{
    "job_id": "task_xxx",
    "job_type": "psd_bandpower",
    "status": "succeeded",
    "summary": {...},
    "metrics": {...},
    "warnings": [],
    "artifacts": [
        {"type": "table", "label": "Band power", "path": "tables/band_power.csv"},
        {"type": "json", "label": "Parameters", "path": "parameters.json"}
    ],
    "reproducibility": {
        "software_versions": "reproducibility/software_versions.json",
        "workflow": "reproducibility/workflow.json"
    }
}
```

worker/API 调度建议使用 registry：

```python
ANALYSIS_REGISTRY = {
    "metadata_qc": run_metadata_qc,
    "waveform_snapshot": run_waveform_snapshot,
    "psd_bandpower": run_psd_bandpower,
    "erp_beta": run_erp_beta,
    "time_frequency_beta": run_time_frequency,
    "pac_experimental": run_pac,
}
```

v0.1 可先建立 registry 文档和 adapter，不必立即迁移所有旧函数。

## 8. 任务系统规划

### 8.1 当前状态

- `AnalysisTaskCreate` 使用 `module_name`、`workflow_id`、`input_file_id`、`parameters_json`。
- `task_service.create_task()` 创建任务后同步执行 `psd`、`erp`、`qc`。
- 任务状态包含 `queued/running/completed/failed` 语义，但实际没有后台队列。
- artifact 在任务完成后由 task_service 从返回 Path 注册。

### 8.2 v0.1 Pilot 建议

v0.1 不引入真实队列，但应把语义固定为：

```text
created -> queued -> running -> succeeded | failed | cancelled
```

建议增加但暂不强制实现的字段：

- `job_type`：稳定任务类型，例如 `metadata_qc`、`psd_bandpower`、`erp_beta`。
- `runner_version`：模块 runner 版本。
- `queued_at`、`started_at`、`finished_at`。
- `duration_seconds`。
- `attempt`。
- `error_code` 与 `error_message`。
- `input_snapshot`：文件、参数、采样率、通道、时间窗摘要。

### 8.3 v0.2+ 演化

当引入 Redis/Celery/RQ 或其他队列时，API 只负责创建 task record 和 enqueue；worker 通过 registry 执行分析并写回 state/database。不要让 API route 与 MNE 计算强耦合。

## 9. 统一输出契约规划

建议所有分析任务最终输出：

```text
analysis_jobs/
  job_xxx/
    parameters.json
    result.json
    manifest.json
    log.txt
    report.html
    report_package.zip
    figures/
    tables/
    reproducibility/
      software_versions.json
      workflow.json
      method_description.txt
```

当前项目实际路径可先映射到：

```text
data/derivatives/{project_id}/{task_id}/
data/reports/{project_id}/{report_id}/
```

### 9.1 `parameters.json`

至少包含：

- `job_id`
- `job_type`
- `analysis_name`
- `input_file_id`
- `input_file_name`
- `channels`
- `time_range`
- `sampling_rate`
- `module_specific_parameters`
- `created_at`
- `created_by`

### 9.2 `result.json`

至少包含：

- `job_id`
- `job_type`
- `status`
- `summary`
- `metrics`
- `warnings`
- `errors`
- `started_at`
- `finished_at`
- `duration_seconds`

### 9.3 `manifest.json`

至少包含：

- `job_id`
- `files[]`
  - `path`
  - `type`
  - `label`
  - `mime_type`
  - `size_bytes`
  - `sha256`（v0.2 可补）
- `report_package`
- `created_at`

### 9.4 `log.txt`

至少记录：

- 输入文件与参数摘要
- 关键处理步骤
- warning
- exception traceback 摘要
- 输出文件列表

## 10. 并发与 500MB 文件目标评估

### 10.1 目标解释

“20 人并发、500MB 文件”建议定义为：

- 最多 20 个用户同时在线操作页面和查询任务状态。
- 不建议 v0.1 承诺 20 个 500MB 文件同时上传并同时运行 MNE 分析。
- v0.1 可承诺受控试用：少量并行上传、串行或低并行分析、明确排队提示。

### 10.2 当前瓶颈

- API 同步执行分析，会阻塞请求。
- JSON state 并发写入需要小心锁和原子写，当前适合单机低并发。
- 500MB 上传经 API 进程会占用带宽、磁盘与 worker 内存。
- MNE 读取大文件可能需要 preload，内存占用不可忽略。
- 没有任务取消、重试、超时、资源限额。

### 10.3 v0.1 Pilot 可接受策略

- 单机部署，限制同时运行分析任务数量为 1-2。
- 前端明确显示 Pilot 排队/处理中状态。
- API 对大文件给出文件大小、格式、持续时间、通道数提示。
- 验收以 1 个 500MB 以内样本文件上传 + metadata + QC/PSD/ERP 条件执行为目标，不承诺满并发压测。
- 文档中声明 Pilot 不代表生产容量。

### 10.4 v0.2+ 必要能力

- 对象存储直传或分片上传。
- 数据库存储 task/file/report 状态。
- Durable queue + worker pool。
- Worker 资源配额、任务超时、失败重试、取消。
- 下载鉴权与审计。
- 容量指标：P95 上传完成时间、任务排队时间、分析耗时、失败率、磁盘占用。

## 11. API / service / worker 边界建议

### API 层

负责：

- 请求校验
- 权限/租户校验（未来）
- 创建 task/report/file 资源
- 返回状态和下载链接

不负责：

- 直接实现 MNE 分析细节
- 直接拼装复杂 report package
- 直接管理 worker 内部日志

### service 层

负责：

- 状态读写
- 文件路径解析
- artifact/report registry
- task 状态迁移
- 调用 runner/worker adapter

### worker 层

负责：

- 根据 `job_type` 调用分析 registry
- 捕获异常并写回失败状态
- 写入统一输出契约
- 记录运行日志

### eeg_core 层

负责：

- EEG 文件读取
- 参数校验
- 分析计算
- 生成图表/表格/reproducibility 文件

不依赖 FastAPI、HTTP、用户 session 或前端状态。

## 12. 报告系统规划

v0.1 report package 应包含：

```text
reports/report.html
tables/*.csv
figures/*
reproducibility/parameters.json
reproducibility/software_versions.json
reproducibility/workflow.json
reproducibility/method_description.txt
manifest.json
```

每个报告必须能回答：

1. 用了哪个 EEG 文件。
2. 用了哪些通道。
3. 用了什么参数。
4. 采样率是什么。
5. 时间窗是什么。
6. 任务什么时候开始与结束。
7. 软件版本是什么。
8. 任务是否成功。
9. 如果失败，失败原因是什么。
10. 生成了哪些图、表和 JSON。
11. 报告包里包含哪些文件。
12. 是否可以复核。

报告页面必须保留科研用途边界，不输出临床诊断、疾病判断或医疗结论。

## 13. 测试计划

### 13.1 最小测试计划

每次改动至少运行：

```powershell
python -m compileall backend eeg_core worker scripts
cd frontend; npm run check
C:\Users\XGN\miniconda3\python.exe scripts\check_no_mojibake.py
```

### 13.2 功能验收

- `scripts/smoke_v01_api.py`
- `scripts/acceptance_v01_worker_core.py`
- `scripts/acceptance_v01_full.py`
- `scripts/acceptance_v01_persistence.py`
- `scripts/acceptance_v01_ui.mjs`（需先启动 backend/frontend）

### 13.3 模块级测试建议

后续为每个分析模块补充：

- 参数 schema 测试
- 缺失/非法文件测试
- 无 EEG 通道测试
- 无 annotations 的 ERP 失败测试
- 输出契约测试：`parameters.json`、`result.json`、`manifest.json`、`log.txt`
- report package 文件完整性测试

### 13.4 500MB / 并发测试建议

v0.1 只做容量摸底：

- 1 个 500MB 以内 EEG 文件 metadata 提取耗时。
- 1 个 500MB 以内 EEG 文件 PSD 耗时与峰值内存。
- 5-20 个用户同时查询页面/API 的响应稳定性。
- 2 个分析任务并行时 API 是否仍可响应 health/status。

## 14. 分阶段改造路线

### Phase 0：文档与边界固化（当前）

- 固化产品命名：QLanalyser Online v0.1 Pilot。
- 固化 stable/beta/experimental 分析模块边界。
- 明确 Pilot 并发容量不等于生产容量。
- 确认输出契约和测试策略。

### Phase 1：契约优先，不大改目录

- 为 task output 增加 `result.json`、`manifest.json`、`log.txt`。
- 为 PSD/QC/ERP 增加 adapter，让返回值可 JSON 化。
- 将 `module_name` 映射到稳定 `job_type`。
- 为 report package 加入 manifest。

### Phase 2：模块 registry

- 新增 `eeg_core/modules/` 或轻量 `eeg_core/registry.py`。
- PSD/QC/ERP 先通过 adapter 接入 registry。
- worker 与 API service 共用 registry 调用，不复制逻辑。
- 增加模块级 README 和 tests。

### Phase 3：任务后台化准备

- service 层拆出 enqueue/runner adapter。
- API 返回 queued/running 状态，不阻塞长分析。
- 本地单机可先用进程内队列或后台线程，但接口保持可迁移。

### Phase 4：生产化基础设施

- 数据库替代 JSON state。
- Redis/Celery/RQ 或等价 durable queue。
- 对象存储分片/直传。
- 多租户权限、审计、账务一致性。

## 15. 必须改造项

进入可试用 MVP 前建议必须完成：

1. 明确并文档化 v0.1 stable 模块：metadata/QC、PSD、报告包；ERP 标注 beta。
2. 统一 `job_type` 与 task 状态语义。
3. 每个成功任务输出可复核参数、结果摘要、方法说明、软件版本、workflow。
4. 报告 ZIP 内包含 manifest 或等价文件列表。
5. UI acceptance 的服务启动依赖要么自动化，要么在 README 中清楚说明。
6. 产品文案避免 `QLanalyser EEG`、`QLanalyser Pilot` 等旧/误导命名。
7. Pilot 容量边界写清楚：单机、低并发、受控试用。

## 16. 可以暂缓项

可放到 v0.2 或更后：

- PostgreSQL / MySQL 等正式数据库。
- Redis、Celery、RQ 或其他真实任务队列。
- 对象存储直传与断点续传。
- PAC、connectivity、完整 TFR stable。
- 多机构权限、完整账务、发票、审计系统。
- 横向扩容和生产 SLA。
- 自动化临床解释或诊断相关能力（不建议做）。

## 17. 修改文件

本轮规划任务修改：

- `docs/v01_pilot_architecture_plan.md`：新增 v0.1 Pilot 总体架构、分析模块、并发、输出契约、测试和分阶段改造规划。
- `docs/PROJECT_STATUS.md`：补充本规划文档索引和当前架构判断。
- `docs/TASK_LOG.md`：记录本轮架构规划任务、审计结论和验证方式。

## 18. Git 状态

截至文档编写时：

- 当前分支：`main...origin/main [ahead 6, behind 1]`
- 本次 commit：未创建。
- 是否已 push：否，等待用户确认。

注意：工作树中已有大量未提交改动，本轮不应把无关前端、后端、脚本或 data/state 产物混入文档规划 commit。

## 19. 风险点

- 当前工作树已有较宽改动，后续 commit 需要精确 stage。
- `origin/main` 比本地多 1 个提交，push 前需要确认同步策略。
- 当前 JSON state 与同步 task runner 不能代表生产并发能力。
- 20 人并发与 500MB 文件目标需要定义为 Pilot 容量摸底，而不是生产 SLA。
- 部分历史文档仍可能存在旧编码乱码，应避免复制到新文档。

## 20. 建议同步给 ChatGPT 网页版的问题

1. `QLanalyser Online v0.1 Pilot` 是否只承诺 metadata/QC、PSD、report package 为 stable，ERP 标注 beta？
2. 20 人并发、500MB 文件目标是否接受“受控 Pilot 容量摸底”，还是必须作为上线准入硬指标？
3. 输出契约是否以 `parameters.json`、`result.json`、`manifest.json`、`log.txt` 为下一阶段优先改造？
4. 是否允许在 v0.1 内先做 in-process/background runner adapter，而把 Celery/Redis 延后到 v0.2？

## 21. 下一步建议

最多三个小任务：

1. 为 PSD/QC/ERP 增加统一输出契约 adapter，先生成 `result.json` 与 `manifest.json`。
2. 固化 UI acceptance 启动流程，让 `scripts/run_v01_acceptance.ps1` 自动启动或明确检测 4174/8001；`8000` 仅保留为旧线兼容回退。
3. 做一次命名审计，只清理活动页面、报告和部署文档中的 `QLanalyser EEG` / `QLanalyser Pilot` 残留。
