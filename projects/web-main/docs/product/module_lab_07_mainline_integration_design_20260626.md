# Module Lab 02 -> 07 主干集成生产级设计（2026-06-26）

Owner: 02｜QLanalyser 模块开发支援
Receiver: 07-PM｜QLanalyser 事业部｜规划验收入口 v2｜正式
Repo: `D:\Quanlan\Codes\Python\quanlan-analyser-official`
Status: 02 功能级验收通过，进入 07 主干集成候选。

---

## 1. 目标

将 02 已实现并测试通过的 Module Lab grouped-methods 功能集成到 07 QLanalyser 主干服务，形成可合并、可运行、可测试、可验收、可回滚的生产级交付。

本集成不是单纯拷贝文件，而是完成以下目标：

1. 明确纳入 07 主干的最小变更集。
2. 保持后端 module / workflow / artifact 合同稳定。
3. 保证 Module Lab 的 9 个方法入口在真实浏览器中可见、可编辑、可运行。
4. 建立轻量回归，避免 closed details / hidden input 类问题复发。
5. 建立启动链路标准，避免 8001 / 4174 环境不一致导致假失败。
6. 生成 07-PM 可接收的验收包和回滚方案。
7. 明确不修改 router、Headroom、IPC、gateway 或进程间通信配置。

---

## 2. 当前已完成事实

### 2.1 已通过的功能链路

02 已验证 Module Lab grouped-methods 全链路：

- 页面按 9 个 grouped UI entry 展示。
- 每个 UI entry 独立提交真实 `/api/tasks`。
- 每个方法都使用同一个上传的 generated EDF 文件。
- 每个任务完成后有参数回显和 artifacts 下载链接。
- 高级参数默认展开，真实浏览器可编辑 `picks` 等原先被折叠隐藏的字段。

已通过模块：

- `qc`
- `psd`
- `tfr`
- `multitaper_psd`
- `multitaper_tfr`
- `erp`
- `reference_csd`
- `pac`
- `connectivity`

### 2.2 核心证据

- Full generated-EDF E2E: `work\release_evidence\20260625-module-lab-grouped-methods-e2e\module_lab_grouped_methods_e2e.json`
- Screenshot: `work\release_evidence\20260625-module-lab-grouped-methods-e2e\module_lab_grouped_methods_e2e.png`
- E2E summary:
  - status: `passed`
  - errors: `0`
  - groupCount: `9`
  - pickerCount: `0`
  - uploaded EDF: `module_lab_grouped_methods_local.edf`, channels `8`, duration `60` sec

### 2.3 已修复根因

旧失败根因：`multitaper_psd.picks` 输入框存在于 DOM 中，但位于关闭的 `details.advanced-params` 内，真实浏览器无法编辑，E2E 在 `locator.fill` 阶段超时。

已修复：`frontend/module-lab.js` 中 `renderParameterFields()` 现在渲染：

```html
<details class="advanced-params" open>
```

该修复只改变可见性，不改变后端合同、参数名、module id、workflow id、artifact 输出合同。

---

## 3. 集成边界

### 3.1 建议纳入 07 主干的候选文件

必须审计后纳入：

- `frontend/module-lab.html`
- `frontend/module-lab.css`
- `frontend/module-lab.js`
- `scripts/generate_module_lab_grouped_methods_edf.py`
- `scripts/acceptance_module_lab_grouped_methods_e2e.mjs`
- `docs/product/module_lab_method_test_bench_requirements_and_test_plan.md`
- `docs/PROJECT_STATUS.md`
- `docs/TASK_LOG.md`

需要确认是否属于本次集成范围：

- `eeg_core/analysis/multitaper_psd_tfr.py`
- `backend/services/task_service.py`
- `backend/services/lab_demo_service.py`
- `backend/services/billing_service.py`
- `backend/services/quota_service.py`

### 3.2 明确非目标

本轮主干集成不做：

- 不上线公网正式客户入口。
- 不把 beta EEG 方法包装成医疗或诊断能力。
- 不修改 router / Headroom / IPC / gateway / 进程通信。
- 不重构整个 QLanalyser 前端导航。
- 不清理仓库所有历史未提交变更。
- 不改生产部署配置，除非 07-PM 明确进入发布阶段。

---

## 4. 产品模式建议

Module Lab 当前应作为：

```text
07 主干内部 beta / review surface
```

不建议直接作为公开生产入口。

### 4.1 内部 beta / review surface

允许：

- 上传 EDF/FIF 测试文件。
- 跑 beta 方法。
- 展示 task id、参数、artifacts。
- 标注“方法测试试验台 / beta”。

### 4.2 未来客户试用模式

需要额外 gate：

- 登录或受控访问。
- 上传大小限制。
- 任务并发限制。
- beta 方法显著标识。
- 明确非医疗、非诊断声明。

### 4.3 正式生产模式

暂不建议直接开放全部 beta 方法，需要补：

- 用户/项目权限。
- 队列与配额。
- 资源限流。
- 审计日志。
- 失败恢复。
- 数据隐私边界。

---

## 5. 后端合同设计

07 主干接收时必须保持以下映射稳定：

| UI entry | backend module | workflow | 说明 |
|---|---|---|---|
| `qc` | `metadata_qc` | `metadata_qc` | 数据准备 / QC |
| `psd` | `resting_psd` | `resting_psd` | 连续频谱功率 |
| `erp` | `erp_p300` | `erp_p300` | 事件锁定时域 |
| `tfr` | `tfr_ersp_itc` | `tfr_ersp_itc` | 事件锁定时频 |
| `multitaper_psd` | `multitaper_psd_tfr` | `multitaper_psd_tfr` | 多窗 PSD，固定 `analysis_family=psd` |
| `multitaper_tfr` | `multitaper_psd_tfr` | `multitaper_psd_tfr` | 事件锁定多窗 TFR，固定 `analysis_family=tfr` |
| `reference_csd` | `reference_csd` | `reference_csd` | 参考 / CSD |
| `pac` | `pac_cfc` | `pac_cfc` | 跨频耦合 |
| `connectivity` | `connectivity` | `connectivity` | 传感器连接性 |

### 5.1 共享 runner 的边界

`multitaper_psd` 和 `multitaper_tfr` 共享后端 runner 是可接受的，但必须满足：

- UI id 不再使用 `multitaper_psd_tfr`。
- backend module id 保留 `multitaper_psd_tfr`。
- PSD 入口固定 `analysis_family=psd`。
- TFR 入口固定 `analysis_family=tfr`。
- result / manifest / parameters 必须能区分 PSD 与 TFR 调用语义。

---

## 6. 前端生产化要求

### 6.1 可见性与可编辑性

所有 E2E 必填字段必须满足：

- visible
- enabled
- editable
- not hidden by closed details
- not hidden behind method picker

重点字段：

- `tfr.picks`
- `tfr.average`
- `multitaper_psd.picks`
- `multitaper_tfr.picks`
- `erp.bad_channels`
- `reference_csd.bipolar_pairs`
- `pac.n_surrogates`
- `connectivity.reference`

### 6.2 错误状态

API 不可用时，页面必须显示明确错误：

- API base。
- 失败原因。
- 提示检查 8001。
- 不应静默空白。

### 6.3 布局标准

必须通过：

- 桌面宽屏。
- 窄屏。
- 无横向溢出。
- 高级参数展开后运行按钮仍可定位。
- 参数区不遮挡产物区。

---

## 7. 生产级测试矩阵

### 7.1 静态检查

```powershell
node --check frontend\module-lab.js
node --check scripts\acceptance_module_lab_grouped_methods_e2e.mjs
python -X utf8 scripts\check_no_mojibake.py frontend\module-lab.js frontend\module-lab.css frontend\module-lab.html
```

### 7.2 轻量 DOM 回归（待补）

建议新增：

```text
scripts/acceptance_module_lab_visible_fields.mjs
```

验收目标：

- 9 groups 存在。
- 0 不必要 method pickers。
- 所有 E2E 需要填写的字段 visible + enabled + editable。
- 输出 JSON 证据。

### 7.3 后端模块合同测试

建议执行或补齐：

```powershell
python scripts\acceptance_multitaper_psd_tfr_module.py
python scripts\acceptance_connectivity_module.py
python scripts\acceptance_reference_csd_module.py
python scripts\acceptance_pac_beta_module.py
```

若脚本名与当前仓库不同，以现有脚本为准。

### 7.4 Full generated-EDF E2E

```powershell
python -X utf8 scripts\generate_module_lab_grouped_methods_edf.py
node scripts\acceptance_module_lab_grouped_methods_e2e.mjs
```

必须满足：

- `status=passed`
- `errors=0`
- `groupCount=9`
- `pickerCount=0`
- `modules=9`
- 每个 module `passed=true`

### 7.5 启动链路测试（待补）

建议新增：

```text
scripts/run_module_lab_acceptance_stack.py
```

功能：

1. 检查 8001 是否已有进程。
2. 没有则启动当前仓库后端。
3. 检查 4174 是否指向当前仓库。
4. 检查 `/api/health`。
5. 跑 visible-fields 或 grouped E2E。
6. 只停止自己启动的进程。
7. 输出 JSON 证据。

---

## 8. 推荐工作包

### Package A: 主干差异盘点

目标：生成 integration manifest。

输出：

```text
work/release_evidence/07-mainline-integration/module_lab_integration_manifest.json
```

必须记录：

- include / exclude 文件。
- 每个文件是否属于 02 功能。
- 是否影响后端合同。
- 是否需要 07-PM 接收。
- 风险等级。
- 验收命令。

### Package B: 可见字段轻量回归

新增：

```text
scripts/acceptance_module_lab_visible_fields.mjs
```

目标：将这次 closed details 的根因变成自动回归。

### Package C: 旧 UI id 清理

目标：清理旧 UI form id `multitaper_psd_tfr`。

注意：不能删除 backend module id `multitaper_psd_tfr`。

验收：

- 有效 UI 脚本不再查找 `data-runner-form="multitaper_psd_tfr"`。
- 后端合同仍保留 `backendModule: multitaper_psd_tfr`。

### Package D: 启动链路标准化

新增：

```text
scripts/run_module_lab_acceptance_stack.py
```

目标：避免“8001 未启动 / 4174 指向旧目录 / 旧 uvicorn 进程”造成假失败。

### Package E: 07-PM 接收包

输出：

```text
work/release_evidence/07-mainline-integration/module_lab_mainline_acceptance_packet.json
work/release_evidence/07-mainline-integration/module_lab_mainline_acceptance_packet.md
```

内容：

- 变更文件。
- 证据路径。
- 测试结果。
- 风险。
- 回滚。
- 接收结论。

---

## 9. 07 主干接收标准

07-PM 接收前必须全部满足：

1. 代码变更边界清楚。
2. 9 个 Module Lab 方法入口存在。
3. 9 个方法真实 `/api/tasks` E2E 全部通过。
4. 高级参数字段可见/可编辑。
5. no mojibake。
6. 桌面和窄屏布局通过。
7. 后端 module/workflow 映射稳定。
8. beta 方法科学边界清楚。
9. 不修改 router / Headroom / IPC / gateway。
10. 临时服务进程可清理。
11. `PROJECT_STATUS.md` / `TASK_LOG.md` 已记录。
12. 有 07-PM 可接收的 acceptance packet。

---

## 10. 风险与回滚

### 10.1 风险

- PAC / TFR / multitaper TFR 耗时重。
- 无账号上传如果公开会有数据和资源风险。
- beta EEG 方法不能被误读为医疗诊断。
- 旧脚本仍可能引用旧 UI id。
- 8001 / 4174 启动状态容易造成假失败。

### 10.2 回滚

前端回滚：

- `frontend/module-lab.html`
- `frontend/module-lab.css`
- `frontend/module-lab.js`

功能降级：

- 保留 QC / PSD / ERP。
- 临时隐藏 beta group。
- 或显示 beta locked。

服务回滚：

- 不动 router。
- 不动 Headroom。
- 不动 IPC。
- 停止新增 local backend。
- 恢复上一版静态前端。
- 保留错误日志和证据文件。

---

## 11. 建议 07-PM 立即执行顺序

1. 读取本文档和当前 02 证据。
2. 生成 integration manifest。
3. 补 visible-fields 轻量回归脚本。
4. 清理旧 UI id 引用。
5. 标准化本地 8001 / 4174 acceptance stack。
6. 跑完整测试矩阵。
7. 生成 07-PM acceptance packet。
8. 给出 `accepted` 或 `blocked` 结论。

---

## 12. QGCS 接收要求

07-PM 不应直接长 ACK。必须收口为：

```text
route_decision:
reused_pool_or_new_pool:
execution_packets:
executor_evidence:
targeted_or_full_e2e:
page_visual_review:
gpt55_acceptance:
final_receipt:
next_real_artifact:
route_chain:
model_lane:
headroom_savings:
```

推荐复用当前 07 pool：

```text
QGCS-07-REVIEW-SYSTEM-ALL-ENVIRONMENTS-E2E-VISUAL-20260623
```

不要新建 task_pool，除非 07-PM 判断这是 release/checkpoint 级主干接收阶段。
