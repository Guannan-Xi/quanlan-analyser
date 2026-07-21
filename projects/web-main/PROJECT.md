# web-main — QLanalyser Web 主线

## 是什么

本机 FastAPI + 浏览器前端的脑电分析平台主线代码（含癫痫全流程相关后端能力）。

## 来源基线

| 项 | 值 |
|---|---|
| 原仓库 | `quanlan-analyser`（GitHub） |
| 原分支 | `feature/epilepsy-full-flow-backend-20260706` |
| HEAD | `f1a18f153298da2ba1e4b4fd046be3ae174a0091` |
| 纳入方式 | 完整源码复制（剔除 data/work/outputs/venv/.git/密钥类文件） |

## 入口

- 后端：`backend/main.py`
- 算法核：`eeg_core/`
- 前端：`frontend/`
- Worker 占位：`worker/`
- 依赖：`requirements.txt` / `requirements.prod.lock`

## 本 monorepo 中的角色

- **主参考实现**：任务、报告、QC、稳定方法（PSD / Band Power / ERP）与 Lab 方法。

## Spike 模块归属

Spike 能力纳入本项目的统一单体架构：

```text
现有 frontend/                 统一 Web 工作台
        |
backend/api/                   复用认证、项目、文件、任务和报告契约
backend/services/              Spike 用例编排与持久化适配
worker/tasks/                  长耗时 sorting 与质量指标任务
eeg_core/spike/                Spike 领域算法和外部库适配器
```

不得在 `projects/` 下新增 `spike-analysis` 等平级应用目录，也不得复制一套 FastAPI、登录、数据库或前端。第一阶段只建立模块边界和产品决策，实际数据格式与 sorter 适配器在真实样本确认后按现有任务流实现。

## 已知边界（接手必读）

- 当前任务在 HTTP 请求内同步执行（`local-sync-worker`），长任务会阻塞 API。
- `worker/celery_app.py` 是占位，不是生产队列。
- 不要把 Lab/Beta 结果写成稳定产品结论或临床诊断。
