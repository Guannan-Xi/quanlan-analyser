# Spike Analysis (预研模块)

Spike sorting 与分析的独立预研模块。此前短暂并入过 `projects/web-main/eeg_core/spike/`
（2026-07-22 决策），随后同一天被撤回，重新拆回独立顶层项目，理由和
`qeeg-64ch-research` 一致：预研阶段的方法应先在独立包里做数值验证，
不直接绑定 FastAPI/数据库/任务队列，避免过早耦合进核心平台。

当前状态：仅有目录占位和边界说明（本文件 + `__init__.py`），尚未搭建
`pyproject.toml` / `tests` / CLI 工程骨架，也没有实际的读取器、预处理、
sorter 适配器或质量指标实现。

## 边界（沿用之前的产品/架构决策）

- 不复制第二套账号、数据库、Web 应用或启动命令；未来若要接入
  `web-main`，走现有的 `backend/api/`、`backend/services/`、
  `worker/tasks/` 边界，而不是让 Spike 自己起服务。
- 外部 sorter（如 SpikeInterface / Kilosort）和设备格式适配器，在真实
  样本验证前不写入正式依赖或客户报告契约。
- 不得把 Spike 结果描述为临床诊断或治疗建议。
- 原始电生理数据、运行产物、密钥不进版本库。

详细产品/架构背景见 `projects/web-main/docs/product/spike_analysis_product_and_architecture.md`
（历史文档，记录了并入决策的完整背景，当前以本文件和根目录
`AGENTS.md`/`README.md` 的"独立预研模块"定位为准）。

## 生命周期

Lab/internal validation → 数值/契约对照验证 → 逐项方法提升进
`web-main/eeg_core`（跟 `qeeg-64ch-research` 走一样的路径，不整包合并）。
