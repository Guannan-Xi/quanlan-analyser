# QuanLan Analyser Workspace

这是 QuanLan Analyser 的本地总工作区。以 `projects/web-main`（QLanalyser Web）为唯一核心平台，
其他预研成果作为独立模块逐项验证后再纳入，最终目标是整合成统一的电生理分析平台 Web 版本。

## 项目角色

| 项目 | 角色 | 说明 |
|---|---|---|
| `projects/web-main` | 核心平台（唯一 Web 主线） | FastAPI + `eeg_core`，backend/frontend/worker 分层齐全，已通过阿里云公网演示验收。所有面向客户的分析能力最终都应在此落地。当前仍是 v0.1 Pilot MVP，`worker` 是同步占位，尚未接真正的异步队列。 |
| `projects/qeeg-64ch-research` | 待整合的预研模块（64 导 QEEG） | 独立 Python 包（`pyproject.toml` + `pytest` + CLI），工程质量目前是几个项目里最好的。从 `pc-qlanalyser` 的算法源重建而来，生命周期是 Lab/internal validation，尚未被 `web-main` 引用。 |
| `projects/pc-qlanalyser` | 遗留桌面参考 | PyQt5 桌面版，仅作算法与数值对照来源，不是开发主线，不再新增功能。内部存在历史遗留的重复/漂移文件，暂不清理。 |
| `projects/spike-analysis` | 待整合的预研模块（Spike sorting/分析） | 独立顶层项目，目前仅有目录占位（README + `__init__.py`），尚未搭建 `pyproject.toml`/`tests`/CLI。2026-07-22 曾短暂并入 `web-main/eeg_core/spike/`，同一天撤回，理由与 `qeeg-64ch-research` 一致：预研先独立验证，不整包合并。 |

## 预研成果接入约定

- 新的预研成果一律先在 `projects/` 下建立独立顶层项目：模块化指的是"独立可测试的 Python 包/服务"，
  不是直接塞进 `web-main` 内部改动其现有结构。
- 生命周期路径固定为：Lab/internal validation → 数值/契约对照验证 → 逐项方法提升进 `web-main/eeg_core`。
  不允许把整包未经验证的 Lab 代码一次性合并进核心平台。
- 不允许再新建与 `web-main` 同构的整份拷贝或并行 Web 服务（历史上出现过的 `epilepsy-demo-20260722`
  就是教训：几乎是 `web-main` 某个时间点的完整重复部署，维护成本翻倍，最终被删除）。
- 不允许把未经验证的 Lab 方法直接接入 `task_service` 的同步分支，或加入客户任务白名单。

## 工作方式

各项目维护自己的 README、产品边界和开发规则。原始 EEG/电生理数据、运行输出、密钥和本地环境文件
不得提交到版本库。
