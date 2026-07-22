# research-modules — 可模块化取用的预研成果库

聚合除 `pc-qlanalyser` 外所有功能项目的预研成果，作为可按需装配进 Web 产品壳
（`projects/web-main`）的**完整功能包**。前端功能点与后端服务都在范围内，任何功能都
以登记为先，不因“看似重复/demo/lab/preview/bak”被直接删除。

## 这个库不是什么

- 不是新的运行时。可运行 Web 产品仍然只有 `projects/web-main`。
- 不是算法的第二份拷贝。阶段 2 只建立**契约**；算法迁移在后续阶段按功能包逐个进行，
  迁移前保留原位置，数值/字段/报告对照通过后才切换、才谈去重。
- 不是把 Lab/recovered 方法包装成 stable 或临床结论的地方。生命周期状态如实标注。

## 目录

```text
research-modules/
├─ README.md                # 本文件
├─ registry.json            # 全模块总表，防遗漏；阶段 3 起逐条登记
├─ contracts/               # 阶段 2：统一科学/产品契约（先契约，暂不搬算法）
│  ├─ module-manifest/          # 模块清单与 registry schema
│  ├─ eeg-source/               # EEG 数据来源描述
│  ├─ channel-montage/          # 通道 / 蒙太奇 / 参考
│  ├─ preprocessing-provenance/ # 预处理溯源
│  ├─ result-envelope/          # 分析结果信封（三类状态分离）
│  ├─ artifact-manifest/        # 工件清单
│  ├─ lifecycle-safety/         # 生命周期与 SafetyGate 措辞
│  └─ frontend-backend-adapter/ # 前后端 adapter / feature flag / 权限 / 报告 section
├─ shared/                  # 经对照验证后的纯计算公共基础（后续阶段建立）
└─ modules/                 # 完整功能包（阶段 3 起逐个登记 / 阶段 4 起逐个迁移）
```

## 契约来源（形式化已有约定，不是凭空发明）

阶段 2 的契约统一了工作区里三套已经存在的事实约定：

1. **后端任务契约** — `web-main/eeg_core/report/reproducibility.py`
   （`qlanalyser-output-v0.1` result + `qlanalyser-artifact-registry-v0.1` manifest、
   `module_name`、`parameters_hash`/`summary_hash`、sidecars）。
2. **前端模块描述** — `web-main/frontend/assets/research-modules/.../research_module_manifest.json`
   （`slug/page/statusLevel(enabled|preview)/inputs/controls/outputs/risks/figures/tables/docs/package` +
   `researchGuardrail`）。
3. **Lab 摘要与安全门** — `qeeg-64ch-research` 的 `_base_summary`
   （`version`、`source{sha256,sampling_rate_hz,duration_sec}`、`analysis_data`、`pipeline`）
   与 `safety_gate{conclusion: AUTO_PASS|AUTO_PASS_BLOCKED, reasons}`、
   `blocked_*` 状态族。

## 生命周期（不可虚报）

`draft → internal_validation → beta → stable → deprecated`，与
`implementation_status`（`implemented / placeholder / pending_contract / optional_dependency`）
正交。晋升到 `stable` 或进入客户白名单需要独立数值/契约证据，且：

- Lab/recovered 方法不自动提升为 stable，不包装为临床诊断；
- 19 导常模不外推 64 导；
- 未建立真实异步 worker 前，不宣称重型分析适合生产；
- 测试失败如实记录，不调整断言掩盖；
- 原始 EEG / 密钥 / 客户报告标识不进版本库。

## 进度

- 阶段 0 基线 `6b18faf`、阶段 1 功能总账（`unclassified==0`）已完成。
- QEEG 解冻并入见 `docs/workspace-inventory/qeeg-dynamic-freeze.md`。
- **当前：阶段 2 — 定义 `contracts/` 下的统一契约。**
