# QLanalyser 数据准备与分析入口一致性详细设计

日期：20260626
来源需求：`docs/product/qlanalyser_data_prep_analysis_entry_consistency_requirements_20260626.md`

## 1. 总体设计

本次把页面改成一条明确路径：

```text
普通模式：项目管理 -> 数据管理/上传 -> 数据准备自动预览 -> 修订/确认 -> 分析任务卡片 -> 结果/报告
教学模式：点击教学模式 -> 加载一套合成 EEG 项目/文件 -> 引导用户沿同一路径跑通
```

核心变化：

1. 教学数据不再污染普通项目管理。
2. 数据状态从真实对象推导，不从乐观文案推导。
3. 数据行点击即预览波形。
4. 分析方法卡片成为唯一入口，去掉重复按钮区。
5. 所有状态都有 loading/empty/error/success 四态。

## 2. 状态模型

### 2.1 Workspace state

```json
{
  "selectedProjectId": "project id or null",
  "selectedFileId": "file id or null",
  "teachingMode": "off|on",
  "preview": {
    "fileId": "file id",
    "status": "idle|loading|ready|error",
    "error": "safe user-facing message",
    "waveform": "canvas data or API payload"
  }
}
```

### 2.2 数据状态显示规则

| 条件 | 显示 |
|---|---|
| 无项目 | 请先创建或打开项目 |
| 有项目无数据 | 当前项目还没有 EEG 数据 |
| 有数据未预览 | 选择数据后自动预览 |
| 预览加载中 | 正在加载波形 |
| 预览成功 | 已预览，可继续修订 |
| 有准备记录 | 准备记录第 N 版 |
| 预览失败 | 波形预览失败，可重试 |

禁止使用“可开始准备”作为未检查数据的结论。

## 3. 页面结构

### 3.1 项目管理

- 显示项目列表、当前项目摘要、当前项目内数据概况。
- 普通模式不预置教学项目。
- 有项目无数据时，只显示上传入口和空状态。

### 3.2 数据管理

- 数据列表只显示当前项目内文件。
- 长文件名：视觉上省略，title 保留全名。
- 文件详情卡不遮挡、不跨栏。

### 3.3 数据准备

左侧：当前项目的数据队列。

右侧：主工作区，首屏必须包含：

1. 当前数据摘要；
2. 步骤条；
3. 波形工具条；
4. 波形画布；
5. 片段和标签操作。

选择数据时调用 `chooseWorkspaceFile(fileId, { jumpToAnalysis: true, autoPreview: true })`。如果当前实现没有 `autoPreview`，本次补齐。

### 3.4 分析任务

删除重复按钮区：

```html
<section data-testid="analysis-method-run-panel">...</section>
```

保留并升级：

```html
<section data-testid="analysis-method-scope-panel">
  <button class="ia-method-card" data-real-action="run-psd">...</button>
</section>
```

每个卡片承担：

- 方法名称；
- 适用场景；
- 前置条件；
- 点击/键盘触发真实任务；
- 不可运行时显示阻断原因。

## 4. API 与错误处理

### 4.1 数据预览

优先复用现有 QC preview / waveform preview API。前端不直接伪造波形。

如果 API 返回失败：

- 显示“波形预览失败”；
- 展示安全原因；
- 提供“重新加载预览”；
- 不显示“预览记录已生成”。

### 4.2 分析任务

点击方法卡片调用现有 `handleRealAction(action)`。

卡片映射：

| 卡片 | action |
|---|---|
| PSD | run-psd |
| ERP | run-erp |
| TFR | run-tfr |
| Multitaper PSD | run-multitaper-psd |
| Multitaper TFR | run-multitaper-tfr |
| PAC | run-pac |
| Connectivity | run-connectivity |
| CSD | run-reference-csd |

## 5. 客户文案设计

原则：

- “你现在能做什么”优先；
- “系统已经真实做了什么”必须准确；
- “下一步”必须能点击到；
- 方法边界在卡片中用一句话说明。

示例：

- 无数据：当前项目还没有 EEG 数据。上传 EDF/FIF 等文件后，系统会在数据准备页自动预览波形。
- 预览失败：波形没有加载成功。请重新加载预览；如果仍失败，请检查文件格式或通道信息。
- CSD：基于通道位置计算头皮电位空间分布变化；这是传感器空间滤波，不是源定位或诊断。

## 6. 风险与回滚

风险：

- 当前前端存在多处动态文案覆盖逻辑，可能互相覆盖。
- 如果后端预览 API 数据不足，需要前端先显示明确错误，而不是临时伪造波形。
- 分析方法有前置条件，不能为了“都可点”而跳过科学边界。

回滚：

- 回滚 `frontend/index.html`、`frontend/app.js`、`frontend/styles.css`。
- 保留文档和证据作为失败记录。
