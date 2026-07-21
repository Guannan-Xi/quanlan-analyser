# Spike 分析模块：产品与架构决策

## 决策结论

Spike 分析并入 `web-main`，作为 QLanalyser 的一个内部分析模块。它可以在本机执行数据读取和离线分析，但产品形态仍是同一个 FastAPI + 浏览器 Web 应用，不单独维护第二个软件。

本决策解决了三个边界问题：

- 只保留一个应用入口、账号体系、项目/文件模型、任务状态和报告导出链路。
- Spike 领域逻辑与现有 EEG/癫痫分析逻辑分目录，避免把新算法散落到通用代码中。
- 外部 sorter 和设备格式通过适配器接入，未验证的依赖不提前写进稳定产品承诺。

## 产品概念

QLanalyser 为神经电生理实验人员提供一个统一的研究数据分析工作台：用户在项目中导入数据，创建分析任务，查看波形和质量指标，人工审核 cluster，并导出可追溯的统计结果与报告。

Spike 模块的 MVP 范围：

- 本地选择数据目录并读取实验元信息。
- 连续信号浏览、通道选择、时间跳转、降采样和基础预处理配置。
- 离线调用已验证的 spike sorter。
- 查看 waveform、ISI、firing rate、raster 和质量指标。
- 对 cluster 执行保留、删除、合并和标记，并记录审核者、参数和运行日志。
- 导出图表、CSV 统计结果和分析摘要。

明确不属于首版：云端上传原始实验数据、在线实时 sorting、自研 sorter、AI 自动判读、账号/支付新体系，以及临床诊断或治疗建议。

## 选型

| 层 | 选择 | 说明 |
|---|---|---|
| 应用形态 | 现有 FastAPI + 浏览器前端 | 复用 `web-main/backend/main.py` 和现有静态前端，不复制第二个应用。 |
| 领域算法 | `eeg_core/spike/` | 与 API、任务编排解耦，便于测试和替换实现。 |
| 外部生态 | SpikeInterface / Kilosort 适配器 | 先以可选依赖和真实样本验证结果，再纳入正式安装链路。 |
| 任务执行 | 现有 task/Worker 边界 | sorting、质量指标和报告生成不能阻塞 HTTP 请求。 |
| 元数据 | 现有项目/文件/任务/报告模型 | 数据库保存元数据、参数、日志和审核结果，不保存原始电生理文件。 |
| 可视化 | 复用现有前端图表能力 | 先满足波形、cluster 和质量指标的检查工作流，再扩展高性能渲染。

上表中的 SpikeInterface、Kilosort 和具体设备格式是架构候选，不代表当前环境已经安装或已经完成兼容性验证。

## 代码边界

```text
frontend/                 统一分析工作台和 Spike 视图
backend/api/              统一 API 契约与鉴权适配
backend/services/         用例编排、任务和结果持久化
worker/tasks/             长耗时分析任务
eeg_core/spike/           Spike 算法、数据格式和外部库适配
docs/product/             产品、架构和验收决策
```

当前只建立 `eeg_core/spike/` 领域包和文档边界；在真实数据格式、排序器版本、GPU/CPU 要求明确前，不增加空的 API 路由或第二套启动命令。

## 当前实现状态与风险

本次合并不代表 Spike 功能已经可运行。当前 `web-main` 的 `worker/celery_app.py` 仍是占位实现，任务服务存在 `local-sync-worker` 同步执行路径；Spike sorting 接入前必须先解决长任务不阻塞 HTTP 的执行机制。

现有读取器和报告契约也不能直接假定覆盖 Open Ephys、Intan、Neuropixels、spike times、waveform snippets、ISI、raster 或 cluster 审核。SpikeInterface、Kilosort、GPU/CUDA 版本和首批真实数据格式均未验证，不能提前写入正式依赖或客户报告契约。

## 实施顺序

1. 用真实样本确认首个输入格式和采样/通道元数据契约。
2. 在 `eeg_core/spike/` 添加读取、预处理和 sorter 适配器，并为每个适配器保留版本与参数。
3. 接入现有任务状态、artifact、报告和前端模块，不新增独立项目模型。
4. 完成人工审核、可复现性、失败恢复和非临床措辞验收后，再扩大设备和 sorter 支持范围。

## 待确认事项

- 首批设备和数据格式：Open Ephys、Intan、Neuropixels、MEA 或其他格式。
- Windows CPU/GPU 支持矩阵及 CUDA 版本。
- 首版优先的质量指标、cluster 审核流程和报告字段。
- 是否需要在统一 Web 应用内增加桌面壳层；这不改变后端和领域模块的归属。
