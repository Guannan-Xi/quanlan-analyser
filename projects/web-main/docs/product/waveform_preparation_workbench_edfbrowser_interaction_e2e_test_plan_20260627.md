# QLanalyser 数据准备波形工作台：EDFBrowser 风格 E2E 测试补充

版本：2026-06-27
状态：已吸收 Codex + Claude 双评审 P0 建议的可开发基线 v2

目标：验证主工作台 Canvas 波形区符合 EDFbrowser 风格阅片习惯，同时不误写数据准备方案、不接入 TimeChart。

## 1. 测试环境

- 前端：`http://127.0.0.1:4174/index.html?customer_demo=auto&api=http%3A%2F%2F127.0.0.1%3A8001%2Fapi`
- 后端：`http://127.0.0.1:8001/api`
- 数据：教学 EEG 数据 + 至少一个真实/合成多通道 EDF/FIF。
- 证据目录：`work/release_evidence/20260627-edfbrowser-waveform-interaction/`

## 2. 选择器清单

| 元素 | 选择器 |
|---|---|
| 工作台 | `[data-testid="data-preparation-workbench"]` |
| Canvas | `#eegCanvas` |
| Canvas 容器 | `[data-testid="preview-edit-workbench"]` |
| 状态栏 | `[data-testid="waveform-status-bar"]` |
| 浏览模式 | `[data-testid="waveform-mode-browse"]` |
| 选段模式 | `[data-testid="waveform-mode-select-segment"]` |
| 坏段模式 | `[data-testid="waveform-mode-mark-bad-segment"]` |
| 坏道模式 | `[data-testid="waveform-mode-mark-bad-channel"]` |
| 选段开始 | `#segmentStart` |
| 选段结束 | `#segmentEnd` |
| 分析门禁 | `[data-testid="analysis-preparation-gate"]` |
| 教学保护 | `[data-testid="teaching-data-protected"]` |

如实现中缺少选择器，开发任务必须补选择器，不允许 E2E 改用脆弱文本查找。

## 3. 常量与容差

| 常量 | 值 |
|---|---:|
| wheelPanRatio | 0.08 |
| arrowPanRatio | 0.10 |
| pagePanRatio | 1.00 |
| zoomFactor | 1.20 |
| anchorDriftToleranceSec | `max(0.05, 2 / display_sample_rate_hz)` |

t=0 或文件末尾 clamp 导致锚点漂移时，用边界例外断言：窗口合法且没有越界即可。

## 4. P0 自动化用例

### T-EDF-01 普通滚轮水平浏览

步骤：
1. 打开数据准备页并等待 `#eegCanvas` 非空。
2. 记录 `#eegStartInput` 与状态栏 start。
3. 在 canvas 上执行普通 wheel。

断言：
- start 改变，变化接近 `duration * 0.08`。
- duration 不改变。
- canvas 非空。
- 没有新增坏段/选段草稿。

### T-EDF-02 Ctrl/Cmd + 滚轮按鼠标锚点缩放

步骤：
1. 鼠标移动到 canvas 中部。
2. Ctrl/Cmd + wheel。

断言：
- duration 改变，比例接近 `zoomFactor`。
- 鼠标锚点对应的时间点漂移小于 `anchorDriftToleranceSec`。
- 如果锚点靠近 t=0 或文件末尾，允许 clamp 边界例外。
- start 合法，不小于 0，不超过文件末尾。

### T-EDF-03 PageUp/PageDown 翻页

步骤：
1. 记录 start/duration。
2. 按 PageDown。
3. 按 PageUp。

断言：
- PageDown 后 start 约增加一个 duration。
- PageUp 后回到原窗口附近。
- 连续按键不因重绘丢焦点。

### T-EDF-04 Left/Right 小步浏览

步骤：
1. 记录 start/duration。
2. 按 Right。
3. 按 Left。

断言：
- Right 后 start 增加约 `duration * 0.1`。
- Left 后回到原窗口附近。

### T-EDF-05 中键拖动水平浏览

步骤：
1. 在 canvas 中按住中键水平拖动。
2. 释放。

断言：
- start 改变。
- duration 不改变。
- 不生成坏段/选段草稿。
- 如果浏览器自动化不能稳定发中键事件，保留人工验证截图/录屏，并用键盘/滚轮路径作为自动化替代。

### T-EDF-06 浏览模式左键不写入

步骤：
1. 点击 `[data-testid="waveform-mode-browse"]`。
2. 左键拖动 canvas。

断言：
- 容器 `data-mode="browse"`。
- 不写入 bad_segments。
- 不确认 selected_segment。
- 如果实现了框选 zoom，则 duration 变小；如果暂未实现，则显示临时选择/时间读数但不写入。

### T-EDF-07 选段模式左键写入 UI draft

步骤：
1. 点击 `[data-testid="waveform-mode-select-segment"]` 或按 S。
2. 左键拖拽一段。

断言：
- 容器 `data-mode="selectSegment"`。
- `#segmentStart` / `#segmentEnd` 更新。
- 选段 overlay 与时间轴对齐。
- 在点击保存/确认前，不产生新的 persisted preparation revision。

### T-EDF-08 坏段模式可撤销且有 audit

步骤：
1. 点击 `[data-testid="waveform-mode-mark-bad-segment"]` 或按 X。
2. 框选一段坏段候选。
3. 点击恢复/撤销。

断言：
- 候选坏段先进入 UI draft。
- 撤销后 overlay 消失。
- audit_actions 保留创建和撤销记录。

### T-EDF-09 振幅与时间缩放分离

步骤：
1. 记录 duration 与 `uV/row`。
2. 按普通 `+`。
3. 按 Ctrl/Cmd + `+`。

断言：
- 普通 `+` 只改变 `uV/row`，不改变 duration。
- Ctrl/Cmd + `+` 改变 duration。
- 状态栏同步更新。

### T-EDF-10 模式按钮与状态栏完整性

步骤：
1. 依次点击四个模式按钮。
2. 读取 `[data-testid="waveform-status-bar"]`。

断言：
- 每个模式按钮可达。
- `data-mode` 与按钮选中态一致。
- 状态栏包含：模式、`hh:mm:ss-hh:mm:ss`、`s/page`、通道数、`uV/row`、Raw/Filter、准备方案状态。
- 写入模式显示“不修改原始 EEG”提示。

### T-EDF-11 分析门禁

步骤：
1. 在未确认准备方案时尝试提交 PSD/ERP。
2. 确认准备方案。
3. 再次提交 PSD/ERP。

断言：
- 未确认时 `[data-testid="analysis-preparation-gate"]` 阻止提交。
- 确认后 payload 带 `data_preparation_plan_id`。
- 确认后 payload 带 `data_preparation_revision`。
- 确认后 payload 带 `data_preparation_contract_version == "qlanalyser-data-preparation-v0.2"`。

### T-EDF-12 非医疗边界与 TimeChart 禁入

断言：
- 数据准备页不出现“诊断、治疗、医疗决策、自动诊断”等承诺性文案。
- 主工作台不加载 TimeChart renderer。
- Canvas 仍为主渲染器。

## 5. P1 人工/半自动视觉评审

1. 状态栏是否像 EEG 阅片工具而不是普通图表卡片。
2. 滚轮翻阅时是否有“连续阅片”感觉，是否出现白屏或旧响应覆盖。
3. 写入模式是否足够醒目，用户是否能理解“不会改原始 EEG”。
4. 窄屏下波形仍是主区域，预处理面板不挤占波形。
5. 快捷键帮助是否可见且用词像用户语言。

## 6. 失败判定

以下任一项失败即不得进入最终产品验收：

- 普通滚轮仍默认缩放。
- 左键拖动默认平移且无模式说明。
- PageUp/PageDown 或 Left/Right 不可用。
- 快捷键触发一次后焦点丢失。
- 浏览模式下误写坏段/选段。
- 未确认准备方案仍能提交 PSD/ERP。
- 确认后提交 PSD/ERP 未携带准备方案 id/revision/version。
- 状态栏缺少模式、时间窗、灵敏度或准备方案状态。
- 教学数据可删除/覆盖。
