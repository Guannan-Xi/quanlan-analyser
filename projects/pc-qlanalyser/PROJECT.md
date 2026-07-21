# pc-qlanalyser — QLanalyser 桌面端（PC）

## 是什么

PyQt5 桌面端 QLanalyser（产品线 v2.x beta 相关代码）。包含 UI、任务分派、QEEG 算法树、报告生成（Jinja2 + matplotlib）及部分模型/常模资产。

## 来源基线

| 项 | 值 |
|---|---|
| 原 git 根 | `AR_analyser1` |
| 子目录 | `AR_analyser_PC/` |
| 原分支 | `dev_xgn0625` |
| HEAD | `52621a64e2bbdf71355d298ae5e9bf7d1d5196c2` |
| 远程 | 内网 GitLab 风格地址（见 evidence 溯源） |
| 纳入方式 | 完整源码 + 算法依赖资产（`.pkl` / `.nrm` / `.sav` 等），剔除 license/config 运行态、生成报告、venv |

## 入口

- 应用入口：`AR_analyser.py`
- 任务分派：`src/task_Analysis.py`
- QEEG 核：`src/qeeg_algorithm-main/qeeg/`（另有 `src/qlelib/qeeg_algorithm-main/` 双份树，有漂移风险）
- 报告：`src/Analyze_report_pro.py`、`src/QEEGAnalysis.py`
- 模型/常模：`src/Epilepsy/`、`src/newEpilepsy/`、`**/EEGnorms/*.NRM` 等

## 本 monorepo 中的角色

- **算法与历史数值对照源**，不是 Web 主线。
- 参数、公式、色标、报告版式可参考；**不要**把 PyQt 线程模型、绝对路径、报告时再算一遍的旁路直接搬进 Web。

## 体量说明

- 本目录约 800MB+，主要是 LightGBM / 癫痫模型与 QEEG 常模文件。
- 它们是算法可跑的依赖资产，不是客户 EEG。
- 19 导常模 **不能**直接当作 64 导全通道常模发布。
