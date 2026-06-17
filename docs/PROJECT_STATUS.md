# QLanalyser Online 项目状态

## 1. 当前目标

QLanalyser Online v0.1 Pilot：稳定 MVP，用于客户免费试用。

## 2. 当前技术栈

- 前端：静态 HTML、CSS、JavaScript，使用 `http-server` 本地服务；`frontend/package.json` 中仍有旧命名，需后续统一。
- 后端：FastAPI、Uvicorn、Pydantic、python-multipart。
- 数据库：未发现正式数据库；当前通过 `backend/services/state_store.py` 将项目、受试者、EEG 文件、任务、产物、报告等 registry 持久化到 `data/state/*.json`。
- EEG 分析模块：MNE-Python 与项目内 `eeg_core/`，当前包含 IO、metadata、quality、PSD、ERP、report、workflow 等模块。
- 任务队列：未发现真实 Celery/Redis 队列；`worker/celery_app.py` 是 `LocalWorkerApp` 占位，worker 任务为薄封装。当前 `backend/services/task_service.py` 在创建任务时直接调用 QC/PSD/ERP 分析逻辑。
- 文件存储：本地文件系统。上传文件保存到 `data/uploads/`，分析结果保存到 `data/derivatives/`，报告保存到 `data/reports/`，状态保存到 `data/state/`。
- 部署方式：本地开发使用 Uvicorn 后端与静态前端服务；`frontend/` 中存在 Dockerfile、nginx.conf、DEPLOY.md，但生产部署方案待确认。

## 3. 当前目录结构

- `frontend/`：浏览器端静态工作台页面、样式、脚本、前端部署文件。
- `backend/`：FastAPI 应用、API 路由、Pydantic 模型、项目/文件/任务/报告/状态服务。
- `worker/`：metadata、preprocess、PSD、ERP、report 等后台任务入口；当前主要复用 `eeg_core`。
- `eeg_core/`：EEG 文件读取、元数据提取、预处理质控、PSD、ERP、统计、HTML 报告、workflow 等核心分析代码。
- `data/`：本地开发数据根目录，包括 uploads、derivatives、reports、state。
- `docs/`：产品架构、Research MVP、V01 readiness 与本次新增协作状态文档。
- `outputs/`：历史静态 MVP 和生成演示资产。
- `scripts/`：V01 smoke、acceptance、mojibake 检查等验证脚本。
- `work/`：本地开发脚本、验收工作区和临时产物。
- `.ai/`：AI 协作相关本地目录，具体用途待确认。

## 4. 已完成功能

- FastAPI 应用已注册 health、projects、subjects、eeg_files、templates、tasks、artifacts、reports、billing、data_crud、workflow、admin 等 API 路由。
- 支持创建项目、创建受试者、上传真实 EEG 文件，并限制 EDF、BDF、EEGLAB SET、BrainVision VHDR、CNT、FIF 等格式。
- 支持本地保存 EEG 原始文件路径和元数据 registry，原始文件保存于文件系统。
- 已有 Metadata/QC、Resting PSD、ERP/P300 相关核心分析与任务入口。
- 支持生成分析 artifacts，并通过 artifact 下载接口获取文件。
- 支持生成 HTML 报告与 ZIP 报告包，报告包包含报告、表格和 reproducibility 信息。
- 已有管理员 dashboard 与失败任务列表接口。
- 已有 V01 smoke 与 acceptance 脚本，覆盖项目创建、上传、metadata、QC、PSD、ERP、报告包与高级方法禁用检查。
- 前端静态工作台已存在，包含项目、数据、QC、分析、结果、报告等页面资源，具体联调状态待确认。

## 5. 部分完成的功能

- 登录页与登录逻辑：前端页面存在，但真实认证、会话、权限边界待确认。
- 工作台首页：前端静态工作台存在，真实 API 联调完整性待确认。
- 管理员入口：后端 admin API 已有基础接口，前端入口和权限控制待确认。
- 分析任务状态：后端任务模型包含状态、进度、错误信息，但当前任务执行路径可能同步阻塞；后台运行机制待确认。
- 任务失败原因展示：后端保存 `error_message` 并提供失败任务列表，前端展示完整性待确认。
- 基础日志：报告与任务输出中有 reproducibility 信息，系统级运行日志与审计日志待确认。
- 基础部署和备份说明：前端 DEPLOY 与 README 有局部说明，后端、数据目录、备份恢复说明不完整。
- Billing 路由：代码中存在 billing API，但 v0.1 Pilot 暂不做在线支付，是否保留为占位待确认。

## 6. 未完成功能

- 明确并验证真实登录/鉴权方案，避免 Pilot 试用时出现未授权访问风险。
- 将长时间 EEG 分析任务移出 HTTP 请求阻塞路径，确认本地后台任务、状态刷新和失败重试策略。
- 完成文件上传限制、文件安全检查、存储清理、备份恢复和容量策略。
- 完成产品名与品牌文案在活动页面、报告、包清单、配置文件中的统一清理。
- 完成工作台前后端端到端验收，特别是项目、上传、任务、报告下载流程。
- 完成部署运行手册：前端、后端、数据目录、端口、环境变量、备份、恢复、日志位置。
- 完成 v0.1 Pilot 客户试用前的最小安全检查与错误提示打磨。

## 7. 当前风险点

- 当前 git 工作树已有大量未提交修改和未跟踪文件，后续任务需要先确认边界，避免覆盖他人工作。
- 当前正式数据库缺失，JSON state 适合单机 Pilot，但多用户并发、数据一致性、备份恢复存在风险。
- 当前未接入真实持久化任务队列，分析任务可能阻塞 HTTP 请求；较大 EEG 文件会带来超时和体验风险。
- 上传文件仅按后缀限制，文件大小、恶意文件、重复文件、存储清理和权限隔离策略待完善。
- 前端、报告包、部署说明中仍可能存在旧产品命名和旧定位文案，存在品牌不一致风险。
- 高级分析方法如 PAC、Connectivity、TFR、机器学习应继续保持禁用或明确返回不可用，避免 Pilot 承诺过高。
- 报告可复核性已经有雏形，但仍需持续验证输入文件信息、参数、运行日志、软件版本、输出路径是否完整保存。
- 本地端口、API base、前端 4173/4174 与代理模式并存，客户试用部署前需要统一说明。

## 8. 最近一次修改

本次建立项目协作与交接文档。

## 9. 下一步建议任务

1. 运行或复核 V01 smoke/acceptance，更新当前真实通过/失败状态。
2. 做一次产品命名与品牌文案审计，只清理活动页面、报告与部署文档中的旧命名。
3. 端到端验证项目创建、EEG 上传、QC/PSD/ERP 任务、HTML 报告、ZIP 下载流程，并记录缺口。

## 10. 本地运行方式

后端 API：

```powershell
C:\Users\XGN\miniconda3\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

前端静态服务：

```powershell
cd frontend
npm run serve
```

前端访问 API 示例：

```text
http://127.0.0.1:4174/?api=http://127.0.0.1:8000/api
```

V01 smoke 验证：

```powershell
C:\Users\XGN\miniconda3\python.exe scripts\smoke_v01_api.py
```

V01 完整验收：

```powershell
scripts\run_v01_acceptance.ps1
```

数据库启动方式：未发现正式数据库，当前使用 `data/state/*.json`。

Docker 启动方式：`frontend/` 内有静态前端 Dockerfile；后端 Docker 或统一 compose 方案待确认。
