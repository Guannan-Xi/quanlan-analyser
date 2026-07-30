# SimNIBS 结果报告模板

入口：`frontend/simnibs-report-template.html`

该文件可直接双击打开，不依赖本地服务。默认只呈现模板结构和缺失状态，不包含模拟或虚构的仿真结果。点击“载入报告 JSON”可将软件导出的结构化结果绑定到报告；数据契约见 `frontend/assets/simnibs-report.schema.json`。

## 支持的任务模式

- `forward_single`：单个既定刺激方案的正向电场仿真。
- `forward_compare`：在相同模型、ROI 和统计口径下比较多个正向方案。
- `inverse_optimization`：由目标和约束反求电极与电流配置，并报告理论解、设备可执行方案及独立完整 FEM 复算。

`stimulation_modality` 控制场图组成：`tes` 只呈现预定义的主要电场结果，`temporal_interference` 额外呈现 E1、E2 和 TImax。

## 生成规则

1. 软件先冻结本次报告使用的 `report_id` 和全部 `run_id`。
2. 图像导出为 SVG、PNG 或 WebP，并在 `figures` 中记录相对路径、替代文本和来源 `run_id`。
3. 数值表由场数组和 ROI 掩膜直接生成，不从图像反读。
4. 质量门控至少覆盖设备兼容性、安全限制、关键输入完整性和数值计算质量。
5. 逆向优化的推荐方案必须具有独立完整 FEM `run_id`；未复算时报告状态只能是 `draft` 或 `blocked`。
6. 缺失分析保留为“未纳入本次分析”，不得自动补写结论。
7. 正式交付时将 HTML、报告 JSON、图件、表格、场数组、ROI 掩膜、运行参数、软件版本和 SHA-256 清单置于同一目录树中。

## 建议交付目录

```text
report_package/
├─ report.html
├─ report_data.json
├─ figures/
│  ├─ model_registration.svg
│  ├─ stimulation_montage.svg
│  └─ ...
├─ tables/
│  ├─ roi_metrics.csv
│  ├─ electrode_currents.csv
│  └─ robustness.csv
├─ fields/
│  ├─ E1.msh
│  ├─ E2.msh
│  └─ TImax.nii.gz
├─ roi/
├─ methods/
└─ manifest.json
```

正式导出程序应在生成 HTML 前使用 JSON Schema 校验数据，并在硬门控失败时阻止 `report.status=ready`。
