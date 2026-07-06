# QLanalyser 分析功能模块清单

Date: 2026-07-03 (updated: PAC V2 推广至 stable candidate)
Owner: 07 PM / GPT-5.5 acceptance lane
Purpose: 功能模块开发、集成、验收的统一索引

---

## 1. 已实现核心分析模块

### 1.1 稳定模块 (stable)

| 模块 ID | 显示名称 | 科学用途 | 代码位置 | 生命周期 |
|---------|---------|---------|---------|---------|
| `qc` | 质量控制 | 数据完整性、信噪比、伪迹检测 | `eeg_core/preprocess/` | stable |
| `preprocessing_readiness` | 预处理就绪检查 | 采样率、通道数、时长检查 | `eeg_core/preprocess/` | stable |
| `psd_bandpower` | 功率谱密度与频段能量 | 静息态脑电频谱分析 | `eeg_core/analysis/psd.py` | stable |
| `erp_p300` | 事件相关电位 P300 | 基于标记的 ERP 分析 | `eeg_core/analysis/erp.py` | stable |

### 1.2 Beta / Lab 模块

| 模块 ID | 显示名称 | 科学用途 | 代码位置 | 生命周期 |
|---------|---------|---------|---------|---------|
| `tfr_ersp_itc` | 时频分析 (ERSP/ITC) | 事件相关时频功率与相位同步 | `eeg_core/analysis/tfr.py` | beta |
| `multitaper_psd_tfr` | 多锥度 PSD/TFR | 高频率分辨率功率谱 | `eeg_core/analysis/multitaper_psd_tfr.py` | beta |
| `pac_cfc` | 相位-幅值耦合 V1 | 跨频段耦合分析 | `eeg_core/analysis/pac.py` | beta |
| `pac_cfc_v2` | 相位-幅值耦合 V2 | 多指标 PAC 分析 (MI/MVL/KL) | `eeg_core/analysis/pac_v2.py` | **promoted_to_stable_from_beta** (2026-07-03) |
| `connectivity` | 功能连接 | 通道间连接性度量 | `eeg_core/analysis/connectivity.py` | beta |
| `reference_csd` | 参考电极与 CSD | 电流源密度变换 | `eeg_core/analysis/reference_csd.py` | beta |

### 1.3 预览 / 内部验证模块

| 模块 ID | 显示名称 | 科学用途 | 代码位置 | 生命周期 |
|---------|---------|---------|---------|---------|
| `epilepsy_ml` | 癫痫检测 (ML) | 癫痫样放电识别 | `eeg_core/analysis/epilepsy_ml.py` | internal_validation |
| `epilepsy` | 癫痫工作台 | 癫痫波形标注与审核 | `eeg_core/analysis/epilepsy.py` | internal_validation |
| `time_frequency` | 通用时频分析 | 时频表示基础设施 | `eeg_core/analysis/time_frequency.py` | internal_validation |

---

## 2. 分析模块技术栈

### 2.1 代码组织

```
eeg_core/
├── io/                     # EEG 文件读写 (FIF, EDF, BDF, ...)
├── preprocess/             # QC、滤波、重参考、伪迹去除
├── analysis/               # 核心分析算法
│   ├── psd.py             # 功率谱密度
│   ├── erp.py             # 事件相关电位
│   ├── tfr.py             # 时频分析
│   ├── pac.py             # 相位-幅值耦合 V1 (beta)
│   ├── pac_v2.py          # 相位-幅值耦合 V2 (stable candidate)
│   ├── connectivity.py    # 功能连接
│   ├── epilepsy.py        # 癫痫工作台
│   ├── epilepsy_ml.py     # 癫痫 ML 检测
│   └── ...
├── workflow/               # 工作流定义与执行
│   ├── schema.py          # 工作流模式
│   └── runner.py          # 工作流执行器
├── stats/                  # 统计检验
├── report/                 # 报告生成
└── resources/              # 模型、模板资源

backend/
├── api/                    # FastAPI 路由层
├── services/               # 业务逻辑服务
└── models/                 # 数据模型

frontend/
├── app.js                  # 主应用逻辑
├── modules/                # 功能模块 UI
└── styles.css              # 样式
```

### 2.2 技术依赖

- **EEG 处理**: MNE-Python
- **数值计算**: NumPy, SciPy
- **机器学习**: scikit-learn (癫痫 ML)
- **后端**: FastAPI, uvicorn
- **前端**: 原生 JS + Lucide 图标
- **可视化**: matplotlib (报告生成)

---

## 3. 模块生命周期管理

### 3.1 生命周期状态定义

参考: `docs/modules/analysis_module_contract.md`

```
draft → internal_validation → beta → stable → deprecated
```

### 3.2 升级到 stable 的必要条件

- [ ] 输入需求定义 (file_formats, channel_requirements, sampling_rate_requirements)
- [ ] 参数模式 (JSON schema)
- [ ] 输出模式 (result.json, manifest.json, reproducibility/)
- [ ] 工作流集成 (`/api/tasks` 路由)
- [ ] 报告映射 (summary, tables, figures, limitations)
- [ ] 验收脚本 (unit, API, browser, report ZIP)
- [ ] 用户文案审核 (DeepSeek official-direct 中文文案)
- [ ] 非医疗边界声明

### 3.3 当前推广目标

| 模块 | 当前状态 | 目标状态 | 阻塞项 |
|------|---------|---------|--------|
| `psd_bandpower` | stable | stable | (已完成) |
| `erp_p300` | stable | stable | (已完成) |
| `tfr_ersp_itc` | beta | stable | 需要 epoch baseline 统计验证 |
| `pac_cfc` | beta | beta | V1 保留 beta; surrogate/null 边界控制仍需完善 |
| `pac_cfc_v2` | **promoted_to_stable_from_beta** | stable | (已完成推广) — 见 §3.4 |
| `epilepsy` | internal | beta | 需要主导航入口 + 用户文档 |

### 3.4 PAC V2 推广记录 (2026-07-03)

PAC V2 (`pac_cfc_v2`) 从 beta/lab 推广至 stable candidate。

验证证据：
- 6 个真实 EEG 场景，MI 相关性 r = 1.000000 与 V1 一致
- 速度提升 2.22x-4.74x
- E2E 实验室集成验证通过
- P1 修复：参数默认可见
- P2 修复：`duration_sec` 使用实际 `sfreq` 而非硬编码 `/250.0`

V1 (`pac_cfc`) 未做任何修改，保留 beta 状态。
详细差异见 `work/pac_dev/PAC_V1_V2_COMPARISON.md`。

---

## 4. 工作流集成路径

### 4.1 标准工作流

```
客户上传 EEG 文件
  ↓
QC / 预处理就绪检查
  ↓
选择分析预设 (Preset Workflow)
  ├─ 静息态分析: PSD + Bandpower
  ├─ 事件分析: ERP + TFR
  └─ 高级分析: PAC + Connectivity
  ↓
任务创建 (POST /api/tasks)
  ↓
后台执行 (worker/)
  ↓
生成工件 (artifacts/)
  ↓
报告打包 (report ZIP)
  ↓
客户下载
```

### 4.2 实验工作台路径

```
分析实验室 (module-lab.html)
  ↓
选择 beta/preview 模块
  ↓
配置高级参数
  ↓
执行分析
  ↓
查看结果 (不纳入标准报告)
```

---

## 5. API 合约

### 5.1 任务创建

```http
POST /api/tasks
Content-Type: application/json

{
  "project_id": "proj_xxx",
  "file_id": "file_xxx",
  "module_id": "psd_bandpower",
  "workflow_id": "resting_state_v1",
  "parameters": {
    "fmin": 0.5,
    "fmax": 40,
    "method": "welch"
  }
}
```

### 5.2 工件列表

```http
GET /api/artifacts?task_id=task_xxx
```

### 5.3 报告下载

```http
GET /api/reports/{task_id}/download
```

---

## 6. 模块开发检查清单

开发新模块时，按顺序完成：

1. **需求定义**: `docs/modules/{module_id}_requirements.md`
2. **设计文档**: `docs/modules/{module_id}_design.md`
3. **算法实现**: `eeg_core/analysis/{module_id}.py`
4. **工作流注册**: `eeg_core/workflow/schema.py`
5. **后端服务**: `backend/services/task_service.py` 路由
6. **API 端点**: `backend/api/tasks.py` (如需新端点)
7. **前端 UI**: `frontend/modules/{module_id}.js`
8. **单元测试**: `tests/test_{module_id}.py`
9. **API 测试**: `scripts/test_api_{module_id}.py`
10. **E2E 验收**: `scripts/e2e_user_level_adversarial_acceptance.mjs` 更新
11. **用户文档**: `docs/product/user_guide.md` 追加
12. **证据包**: `work/release_evidence/{module_id}/`

---

## 7. 当前开发约束

### 7.1 产品边界

- ✅ 研究 EEG 分析工具 + CRO 基础设施
- ❌ 医疗诊断、治疗建议、医疗器械、临床决策支持

### 7.2 质量门禁

- 用户级 E2E 对抗验收: `scripts/e2e_user_level_adversarial_acceptance.mjs`
- 18 步发布审核门禁: `scripts/run_release_review_gate.py`
- 分析模块合约门禁: `docs/modules/analysis_module_contract.md`
- CRO 可追溯性合约: `docs/compliance/cro_traceability_contract.md`

### 7.3 中文文案审核

客户可见中文文案必须通过 DeepSeek official-direct 审核（非 GLM-5.2）。

---

## 8. 参考文档

| 文档 | 路径 |
|------|------|
| 模块生命周期矩阵 | `docs/product/module_lifecycle_matrix.md` |
| 分析模块合约 | `docs/modules/analysis_module_contract.md` |
| 产品长期目标 | `docs/product/LONG_TERM_GOAL_AND_ONE_YEAR_ROADMAP.md` |
| 当前项目状态 | `docs/PROJECT_STATUS_CURRENT.md` |
| 用户指南 | `docs/product/user_guide.md` |
| API 合约清单 | `docs/product/api_contract_inventory.md` |
| 验收矩阵 | `docs/product/acceptance_matrix.md` |

---

## 9. 下一步扩展方向

### 9.1 近期推广 (Q3 2026)

- 癫痫工作台 beta 推广（需主导航入口）
- TFR/ERSP/ITC stable 推广（需统计验证）
- PAC/CFC stable 推广（需边界控制）

### 9.2 中期研发 (Q4 2026)

- 源定位 (source localization) 进入 beta
- 功能连接 (connectivity) 稳定化
- 批量分析工作流

### 9.3 长期路线图 (2027)

- CRO 级审计追溯
- BIDS 工作流
- 可视化工作流构建器
- HIS/PACS 集成（需明确非医疗边界）

---

**下次更新**: 当模块生命周期状态变化、新模块加入、或工作流路径调整时更新。
