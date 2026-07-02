# QLanalyser WaveformWorkbench 客户级 UI / 交互逻辑评审

日期：2026-06-27  
对象：数据准备页 / WaveformWorkbench / 教学模式 EEG 波形工作台  
评审目标：外部科研客户试用时，页面必须可信、清晰、专业、交互友好，并符合 `docs/product/waveform_workbench_DESIGN.md` 与 Google Labs `design.md` 设计合同思路。  
最终裁定人：Codex / GPT-5.5  
外部侧评：Claude（用户要求 4.8；本地 CLI 以 `--model opus` 执行）+ DeepSeek（代码逻辑评审，无视觉能力）

---

## 1. 证据来源

### 1.1 设计合同

- `D:/Quanlan/Codes/Python/quanlan-analyser-official/docs/product/waveform_workbench_DESIGN.md`
- `D:/QuanLanKnowledgeBase/manifests/design/GOOGLE_LABS_DESIGN_MD_CONTRACT_TOOL_20260627.md`

### 1.2 页面和自动化证据

- `D:/Quanlan/Codes/Python/quanlan-analyser-official/work/release_evidence/20260627-customer-level-ui-review/customer_level_ui_review_probe.json`
- `D:/Quanlan/Codes/Python/quanlan-analyser-official/work/release_evidence/20260627-customer-level-ui-review/desktop_1440_analysis_top.png`
- `D:/Quanlan/Codes/Python/quanlan-analyser-official/work/release_evidence/20260627-customer-level-ui-review/desktop_1440_analysis_full.png`
- `D:/Quanlan/Codes/Python/quanlan-analyser-official/work/release_evidence/20260627-customer-level-ui-review/laptop_1280_analysis_top.png`
- `D:/Quanlan/Codes/Python/quanlan-analyser-official/work/release_evidence/20260627-customer-level-ui-review/laptop_1280_analysis_full.png`
- `D:/Quanlan/Codes/Python/quanlan-analyser-official/work/release_evidence/20260627-customer-level-ui-review/mobile_390_analysis_top.png`
- `D:/Quanlan/Codes/Python/quanlan-analyser-official/work/release_evidence/20260627-customer-level-ui-review/mobile_390_analysis_full.png`
- `D:/Quanlan/Codes/Python/quanlan-analyser-official/work/release_evidence/20260627-main-data-prep-waveform-visible/main_data_prep_waveform_visible_e2e.json`：主数据准备页波形显示 E2E，status=passed
- `D:/Quanlan/Codes/Python/quanlan-analyser-official/work/release_evidence/20260627-waveform-workbench-module/waveform_workbench_e2e_result.json`：独立 WaveformWorkbench E2E，status=passed

### 1.3 外部评审证据

- Claude 原始回执：`D:/Quanlan/Codes/Python/quanlan-analyser-official/work/claude48_customer_ui_logic_review_20260627.md`
- DeepSeek 原始回执：`D:/Quanlan/Codes/Python/quanlan-analyser-official/work/deepseek_code_logic_ui_review_20260627.md`

说明：Claude 回执文件在当前 Windows 终端链路中有局部编码噪声，因此本文只保留 Claude 可读结论摘要，不直接嵌入污染文本。

---

## 2. 总体结论

**当前成熟度：good usability，尚未达到 polished and professional。**

当前页面已经可以完成主要任务：教学数据自动加载、主页面波形可见、独立 WaveformWorkbench 通过 E2E、滚轮/键盘/模式交互已有基础。但作为客户级外部试用页面，它仍有几个明显问题：

1. 首屏加载态容易被客户理解为“选了数据但没有波形”。
2. 按钮和控件太多，客户不知道哪些是主动作、哪些是高级动作。
3. 部分按钮和功能区重复，尤其是模式切换、片段/坏道/参考入口、保存/恢复类按钮。
4. 坏段流程更像“拖拽即排除”，不够像科研人员的“候选标记 -> 复核 -> 确认”。
5. 移动端纵向过长，需要专门的波形全屏/底部工具条模式。

结论：**不阻断内部开发和试用；不建议作为最终客户公测 UI 直接发布。建议先完成 P0/P1 交互治理。**

---

## 3. 亮点

- **产品定位正确**：QC 已回到数据准备依赖，不再作为分析方法卡片。
- **波形主视觉已恢复**：主页面 E2E 确认 Canvas 可见，空态隐藏，无 `Failed to fetch`。
- **交互方向正确**：浏览模式、选段模式、坏段模式、坏道模式已建立；浏览模式默认不写草稿。
- **科研边界明确**：多处提示“预览不改写原始 EEG”“科研数据准备，不用于诊断”。
- **教学模式方向正确**：内置数据可练习、可试跑、不可删除/覆盖，符合产品演示需求。

---

## 4. P0 问题

### P0-1｜冷启动加载态会造成“没有波形”的误判

证据：客户级截图探针中，首屏可能处于“正在准备 EEG 波形”的骨架态；主页面专项 E2E 后续通过，说明不是功能坏了，而是加载状态表达不够清楚。

影响：客户会误以为数据没有加载成功，反复点击重新加载或怀疑系统不可用。

建议：

- 把加载态分成明确阶段：
  - 正在读取教学数据
  - 正在恢复已有预览
  - 正在生成波形预览
  - 已完成
  - 超时可重试
- 如果已有有效波形，错误提示不能覆盖波形，只能进入状态栏或 toast。
- 增加 cold-load E2E：记录初始加载、完成后波形、失败重试三个状态。

### P0-2｜坏段流程应从“立即排除”改为“候选坏段”

现状：坏段模式下拖拽释放后接近立即执行剔除动作。

风险：科研人员阅片时常需要先标记多个可疑片段，再统一复核确认；拖错后马上进入恢复流程，体验不顺。

建议：

- 增加“候选坏段”状态。
- 拖拽只生成候选坏段草稿。
- 侧栏提供“确认排除候选坏段”“全部恢复”。
- 状态栏显示：候选 X 段 / 已排除 Y 段 / 可恢复 Z 段。

---

## 5. P1 问题：按钮与功能逻辑

### P1-1｜按钮总量过高

DOM probe 显示 #analysis 区域可交互控件约 53 个。对科研工作台来说，功能丰富可以，但首屏同时出现太多按钮会让客户不知道下一步。

建议分层：

| 层级 | 交互形式 | 示例 |
|---|---|---|
| 主动作 | 单一主按钮 | 确认数据准备 |
| 高频动作 | 模式工具条/快捷键 | 浏览、选段、坏段、坏道 |
| 上下文动作 | 选段浮层/右键菜单 | 标记坏段、添加标签、排除该段 |
| 低频设置 | 折叠高级面板 | 重参考、滤波参数、数据概况 |
| 状态信息 | token 状态栏 | Raw/Filter、uV/row、教学保护、修订版本 |

### P1-2｜重复按钮和低价值按钮

建议治理：

1. “片段 / 坏道 / 参考”快捷按钮：
   - 片段、坏道已经有模式按钮；参考属于预处理设置。
   - 建议移除这组跳转按钮，或改成状态栏/引导提示。
2. 多个“恢复”按钮：
   - 容易不知道恢复什么。
   - 改成“恢复最近坏段”“恢复最近坏道”“恢复最近标签”，并放在对应草稿区。
3. “查看数据概况”：
   - 放到数据队列卡片或文件详情抽屉，不占波形主工作区按钮位。
4. “确认数据准备”：
   - 页面只保留一个主确认按钮；如果底部也出现，需要改为 sticky footer 或移除重复。

### P1-3｜快捷键不可发现

系统已有快捷键，但用户看不到：滚轮、Ctrl/Cmd+滚轮、PageUp/PageDown、Left/Right、+/-、S/X/C/B。

建议：

- 状态栏增加 `? 快捷键`。
- 教学模式引导第一轮显示：
  - 滚轮：浏览时间
  - Ctrl/Cmd + 滚轮：缩放时间窗
  - S：选段
  - X：坏段
  - C：坏道
  - B/Esc：浏览

### P1-4｜教学模式保护需要更贴近操作点

DeepSeek 建议“禁止教学模式写草稿”，Codex 不完全采纳。

产品裁定：教学模式应允许练习、试跑、生成练习结果，但不能删除/覆盖内置数据，也不能污染普通项目。

建议：

- 状态栏固定显示：`教学数据 / 受保护 / 草稿仅练习 / 不覆盖原始数据`。
- 保存或确认时提示：`这是教学练习记录，不会修改内置数据`。
- 普通模式和教学模式的持久化记录隔离。

---

## 6. P2 改进：更好的交互形式

### 6.1 选段浮动操作条

拖拽选段后，在选区附近显示：

```text
12.30-18.20 s | 标为坏段 | 添加标签 | 取消
```

这样比用户去下方寻找按钮更自然。

### 6.2 右键菜单 / 长按菜单

右键波形或选段：

- 标记为坏段
- 添加标签
- 排除该段
- 恢复最近操作
- 复制时间范围

手机端用长按替代。

### 6.3 高级设置折叠

默认只显示：

- 滤波预览开关
- 当前参考方案摘要
- 确认数据准备

展开高级后才显示：参考通道、双极通道对、低切、高切、陷波、数据概况。

### 6.4 移动端专用波形模式

390px 下不要把桌面按钮全部纵向堆叠。建议：

- 波形全屏模式
- 底部固定工具条：浏览 / 选段 / 坏段 / 坏道 / 确认
- 高级预处理用抽屉
- 数据队列折叠成当前数据卡片

---

## 7. 科研和非医疗边界

继续保留并强化：

- 统一使用“候选”“草稿”“需复核”，避免暗示诊断。
- 状态栏固定非医疗边界：`科研数据准备，不用于诊断`。
- 结果图表必须有单位、时间窗、采样率、通道名、处理记录。
- 科学图默认避免 rainbow/jet 作为连续量配色。

---

## 8. Claude 侧评摘要

Claude 的核心结论：

- 成熟度：good usability，未达到 polished and professional。
- 主要优点：交互模型、草稿模型、教学保护和非医疗边界方向正确。
- 主要风险：客户级冷启动加载态可能被误解为没显示；按钮过多；恢复/确认类动作重复；移动端纵向过长；状态栏和按钮层级需要进一步清晰化。
- Claude 明确说明其不能直接解码 PNG，只基于 JSON、DOM、源码与 E2E 证据判断。

原始回执路径：`D:/Quanlan/Codes/Python/quanlan-analyser-official/work/claude48_customer_ui_logic_review_20260627.md`。

---

## 9. DeepSeek 代码逻辑评审摘要

DeepSeek 的核心结论：

- 没有视觉能力，仅基于代码、DOM JSON 和设计合同评审。
- 认为整体逻辑接近 polished，但存在按钮堆砌、坏段流程过快、教学保护表达不足、快捷键不可发现等问题。
- 建议治理按钮数量、增加右键菜单/浮层、强化状态栏教学保护和非医疗边界。

原始回执路径：`D:/Quanlan/Codes/Python/quanlan-analyser-official/work/deepseek_code_logic_ui_review_20260627.md`。

### Codex 对 DeepSeek 的采纳判断

- 采纳：按钮过多、坏段流程候选化、快捷键不可发现、移动端需要专门模式。
- 部分采纳：教学数据保护。DeepSeek 建议禁止教学写草稿；但产品需求是教学数据可练习、可试跑，不可删除/覆盖。因此应做“练习草稿隔离 + 明确保护提示”，不是完全禁用写模式。

---

## 10. 下一步 5 个开发任务

1. **冷启动加载态治理**  
   分阶段加载提示、超时重试、已有波形不被错误遮罩覆盖。

2. **按钮和功能区减负**  
   删除/降级重复按钮，保留一个主确认动作，把低频功能折叠。

3. **坏段候选草稿模型**  
   拖拽坏段先生成候选，批量确认排除，支持全部恢复。

4. **快捷键提示与选段上下文菜单**  
   增加 `? 快捷键`、选段浮动操作条、右键/长按菜单。

5. **移动端专用波形模式**  
   全屏波形、底部工具条、高级设置抽屉，减少纵向瀑布。

---

## 11. 验收标准

- 1440 / 1280 / 390 无横向溢出。
- 教学数据选择后 10 秒内显示波形或明确加载进度。
- 桌面波形宽度不低于 620px。
- 默认浏览模式不写草稿。
- 选段、坏段、坏道均可恢复。
- 状态栏显示：模式、时间窗、s/page、通道数、uV/row、Raw/Filter、准备状态、教学保护、非医疗边界。
- 主操作只有一个，重复“恢复/确认/跳转”按钮被治理。
- 移动端不再以 50+ 控件瀑布流作为主交互。
- Claude / DeepSeek P0/P1 建议已采纳或记录拒绝理由。
- 更新后的截图与 E2E 证据输出到新 release_evidence 目录。

---

## 12. Final Receipt

route_decision: gpt55_planner_or_acceptance + claude_review + deepseek_code_logic_review + script_validator  
executor_evidence: customer-level screenshot probe, main waveform visible E2E, independent WaveformWorkbench E2E, Claude review, DeepSeek review  
gpt55_acceptance: accepted with corrections; current page is good usability, not yet polished professional  
final_receipt: customer_level_ui_logic_review_completed_with_p1_followup  
next_real_artifact: implement Task 1-5 as a focused UI/interaction cleanup slice
