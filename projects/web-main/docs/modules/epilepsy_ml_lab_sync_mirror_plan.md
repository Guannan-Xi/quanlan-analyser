# Epilepsy ML 实验室同步测试镜像方案

Status: draft for 07 lab integration
Parent requirements: `epilepsy_ml_high_fidelity_requirements.md`
Parent test plan: `epilepsy_ml_high_fidelity_test_plan.md`
Date: 2026-06-26

## 1. 目标

在 07 的实验室入口中提供一个与主干癫痫 ML 分析完全同源的同步测试镜像，方便产品、研发和验收人员边集成边试用。

这个实验室镜像不是简化版、演示版或第二套算法。它必须复用同一套：

- ML runner
- model/scaler 资产
- feature extraction
- scaler/model inference
- event aggregation
- review session API
- waveform window API
- review workbench component
- independent audit gate

实验室只允许增加：

- 固定测试数据入口
- 一键创建任务/复核 session
- 更显眼的测试说明
- 对比结果下载入口
- 非医疗和“实验室数据”标识

## 2. 硬性原则

1. 不新增 router / Headroom / IPC / front-route。
2. 不复制出第二套癫痫 ML 算法。
3. 不复制出第二套模型文件。
4. 不创建实验室专用 workflow 来绕开正式 workflow。
5. 实验室入口必须调用同一个 `epilepsy_ml_screening` workflow。
6. 实验室工作台必须调用同一个 review session API。
7. 实验室结果必须带 `lab_mode=true` metadata，但算法输出字段与正式任务一致。
8. 实验室 fixture 和 demo 文案不得泄漏到客户主路径、主报告、正式 artifact 页面。
9. 实验室同步测试也必须通过独立子智能体核查门禁。

## 3. 建议入口

### 3.1 module-lab 卡片

在 `frontend/module-lab.html` / `frontend/module-lab.js` 中增加实验室入口卡片：

```text
癫痫样事件筛查 / ML 模型 / 实验室同步测试
```

卡片行为：

1. 选择或自动加载实验室 fixture。
2. 提交同一个后端任务：
   - `module_name=epilepsy`
   - `workflow_id=epilepsy_ml_screening`
   - `method=ml_epoch_classifier`
   - `lab_mode=true`
3. 任务完成后显示：
   - 打开复核工作台
   - 下载 ML artifacts
   - 下载 source-vs-target audit 包

### 3.2 Review workbench 链接

实验室卡片不直接实现波形和复核逻辑，而是跳转到同一个工作台：

```text
frontend/epilepsy-review.html?session_id=<session_id>&lab_mode=1
```

要求：

- 使用同一份 `epilepsy-review.js`。
- 只在页面顶部显示“实验室同步测试”提示。
- 不能 fork 出 `epilepsy-review-lab.js`。

## 4. 实验室 fixture

建议固定目录：

```text
work/e2e_epilepsy_ml_lab/
  fixtures/
    epilepsy_ml_lab_3s_raw.fif
    epilepsy_ml_lab_5s_raw.fif
    epilepsy_ml_lab_empty_raw.fif
    epilepsy_ml_lab_tail_event_raw.fif
  expected/
    source_features_3s.csv
    source_probabilities_3s.csv
    source_events_3s.csv
    source_features_5s.csv
    source_probabilities_5s.csv
    source_events_5s.csv
  audit/
    latest_verdict.json
```

fixture 至少覆盖：

- 3s 模型路径。
- 5s 模型路径。
- 全 Normal。
- 单个 Seizure epoch。
- 连续两个 Seizure epoch。
- 文件尾部事件。
- 尾部不足一个 epoch 的截断。
- 默认通道 EEG3 / EEG1 / ACC0。
- 低采样率 warning。

## 5. 实验室 metadata 合同

实验室任务应在 `parameters_json` 或 task metadata 中记录：

```json
{
  "lab_mode": true,
  "lab_fixture_id": "epilepsy_ml_lab_5s_v1",
  "source_algorithm": "AR_analyser1 EpilepsyAnalysis_ML",
  "target_algorithm": "quanlan-analyser-official epilepsy_ml_screening",
  "independent_audit_required": true,
  "non_medical_scope": "research_screening_only"
}
```

这些字段只用于追踪，不得改变算法行为。

## 6. 实验室 UI 要求

实验室页面必须显示：

- 当前 fixture 名称。
- epoch length。
- 模型文件名和 hash。
- 默认通道或实际通道。
- 是否已完成 source-vs-target independent audit。
- 非医疗说明。
- “打开复核工作台”按钮。
- “下载验收包”按钮。

实验室页面不得显示：

- 诊断、确诊、治疗建议。
- 客户主路径文案。
- 模糊的“AI 诊断”字样。

## 7. 同步测试流程

建议一键流程：

1. 选择 fixture。
2. 运行 ML task。
3. 创建 review session。
4. 打开 review workbench。
5. 自动载入第一个候选事件。
6. 人工修改一个 epoch。
7. 保存 reviewed layer。
8. 导出 reviewed artifacts。
9. 触发独立核查 worker 或读取最新 audit 包。

## 8. 验收标准

实验室同步测试入口完成的标准：

1. module-lab 有 ML 实验室入口。
2. 入口提交正式 `epilepsy_ml_screening` workflow。
3. fixture 可一键运行。
4. 任务完成后可打开同一个 review workbench。
5. 波形、候选事件、人工标注、撤销、重做、保存、导出可用。
6. reviewed layer 重开仍存在。
7. source-vs-target audit 包可下载。
8. 实验室页面不影响客户主路径。
9. 不触碰 router / Headroom / IPC。

## 9. 交给 07 的实现拆包

建议 07-PM 拆成四个 packet：

### Packet A: lab fixture and source expected outputs

- 生成固定 fixture。
- 用 AR_analyser1 源算法跑 expected outputs。
- 保存到 `work/e2e_epilepsy_ml_lab/expected/`。

### Packet B: lab module-lab entry

- 新增实验室卡片。
- 调用正式 workflow。
- 展示 fixture 和 audit 状态。

### Packet C: shared review workbench lab mode

- 同一 `epilepsy-review.js` 支持 `lab_mode=1`。
- 只增加实验室提示和 fixture metadata 展示。

### Packet D: independent audit download

- 将 source-vs-target 核查结果作为 lab 可下载 artifact。
- 未通过时页面必须显示 blocked，不允许显示为通过。
