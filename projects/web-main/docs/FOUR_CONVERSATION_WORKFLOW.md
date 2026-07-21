# QLanalyser 四对话并行开发指挥流程

更新时间：2026-06-19
状态：协作流程 / 双模块并行开发 / 调研设计对话作为任务指挥中枢 / 已接入团队治理基线

## 0. 上位治理规则

本流程现在受 docs/TEAM_OPERATING_MODEL.md 约束。

执行任何非平凡任务前，调研与设计对话应优先使用：

- qlanalyser-team-orchestrator：把用户产品语言转换成多对话任务包。
- qlanalyser-clean-code-quality-gate：按 Clean Code 思想做代码质量门禁。
- qlanalyser-ui-business-flow-review：治理客户界面、业务流程、截图评审和文案。
- qlanalyser-release-maintenance-gate：发布、测试、维护、回滚门禁。
- qlanalyser-github-baseline-sync 和 qlanalyser-git-guard：防止并行开发冲突和误 push。

当前四对话流程是 6 对话团队模型的过渡形态：模块开发2应优先承接 PSD 或下一个独立分析模块；后续应新增质量/发布维护对话，形成 C0-C5 闭环。

## 1. 当前对话编排

当前 Codex 对话按用户实际命名编排为：

```text
脑电分析平台（模块开发1）
脑电分析平台（模块开发2）
脑电分析平台 合开发（主框架开发）
脑电分析平台（调研与设计）
```

用户主要和 `脑电分析平台（调研与设计）` 对话，也就是本对话沟通。

本对话负责：

- 理解用户目标。
- 调研 MNE / EEG 方法依据。
- 做产品、架构、神经科学和工程设计。
- 拆解任务。
- 生成给其他三个执行对话的工作指令。
- 定义阶段验收标准。
- 汇总其他对话阶段成果，给用户做抽查评审。

用户主要负责：

- 决定方向。
- 抽查阶段成果。
- 对关键设计、界面、结果和部署效果做最终确认。

用户不需要持续盯每个执行对话的实现细节。

## 2. 四个角色职责

### 2.1 脑电分析平台（调研与设计）

定位：总设计中枢、任务拆解者、架构评审者、神经科学和 MNE 方法把关者。

职责：

1. 产品意图澄清。
2. EEG / MNE / EEGLAB / FieldTrip 调研。
3. 输出模块需求文档。
4. 输出前后端详细设计。
5. 进行多视角评审。
6. 拆解开发任务。
7. 给模块开发1、模块开发2、主框架开发分别生成任务提示。
8. 定义验收标准。
9. 汇总执行结果。
10. 指导用户抽查。

本对话不负责大规模写业务代码，除非用户明确要求小范围补文档或修正规格。

### 2.2 脑电分析平台 合开发（主框架开发）

定位：平台公共底座和集成负责人。

职责：

- 主应用入口。
- 登录 / 注册 / 体验中心 / 正式工作台。
- 项目、被试、文件、任务、artifact、报告。
- `/api/tasks`、task runner、state store。
- `data_preparation_plan` 公共服务。
- preview segment 公共服务。
- artifact 下载和报告包。
- 模块接入主流程。
- 全局验收、部署和 push。

当前优先任务：

1. `data_preparation_plan` 保存 / 读取。
2. revision 冲突检测。
3. preview segment 保存 / 列表 / 读取 / 删除。
4. `/api/tasks` 支持 `data_preparation_plan_id`。
5. artifact 输出规范统一。
6. report package 复现文件统一。

主框架开发不得擅自改变 QC / PSD 算法细节。

### 2.3 脑电分析平台（模块开发1）

定位：第一个单模块开发者。

当前建议负责：

```text
QC 公共数据准备工作台
```

职责：

- 实现 QC 模块前端交互。
- 实现或适配 QC 后端 preview 能力。
- 64 通道真实波形预览。
- 横轴 / 纵轴缩放。
- 坏导多选。
- 坏段框选。
- annotation 处理。
- 保存当前预览片段。
- 接入主框架提供的 `data_preparation_plan` API。
- 模块级验收脚本。

主要依据：

```text
docs/modules/qc_common_data_preparation_requirements.md
```

### 2.4 脑电分析平台（模块开发2）

定位：第二个单模块开发者，可与模块开发1并行。

当前建议负责：

```text
PSD 频谱与频段功率
```

职责：

- 实现 PSD 参数 schema。
- 实现 Welch 参数校验。
- 接入 `data_preparation_plan_id`。
- 应用 bad_channels / bad_segments / annotation_actions。
- 调用 MNE `Raw.compute_psd(method="welch")`。
- 输出 `spectrum_long.csv`。
- 输出 `psd_mean_spectrum.svg`。
- 输出 `psd_band_power.svg`。
- 补 PSD 成功和失败路径验收。

主要依据：

```text
docs/modules/psd_design.md
D:\Quanlan\Codes\Python\third_party_eeg_reference_sources\mne-python
```

## 3. 多视角评审机制

当前 Codex 环境未提供直接调用外部多个模型的独立工具接口，因此本对话采用“多视角评审机制”来逼近多模型评审：

每个核心模块设计至少经过以下视角：

1. 顶层架构师视角：模块边界、公共服务、扩展性、冲突风险。
2. 神经科学视角：EEG 方法是否可靠，是否会误导用户。
3. MNE 工程视角：API 是否正确，参数是否可复现，版本是否兼容。
4. 产品体验视角：脑电小白是否能用，文案是否清晰。
5. 前端工程视角：交互是否可实现，状态模型是否清楚。
6. 后端工程视角：接口、schema、artifact、错误码是否完整。
7. QA 验收视角：成功路径、失败路径、性能边界是否可测。

如果后续用户或其他工具提供真正的多模型接口，本对话将把同一份设计拆成多模型评审提示，再汇总结论。

## 4. 用户工作方式

用户以后主要做三件事：

1. 在调研设计对话里提出目标。
2. 把本对话生成的任务提示复制给其他三个执行对话。
3. 按本对话给出的抽查清单评审阶段成果。

用户不需要：

- 每天盯代码细节。
- 在多个对话之间反复解释同一件事。
- 自己判断每个 API 或 MNE 参数是否可靠。

这些由调研设计对话负责拆解、汇总和提醒。

## 5. 标准开发流程

```text
用户提出目标
  -> 调研与设计对话调研和设计
  -> 调研与设计对话输出任务分发提示
  -> 主框架开发做公共底座
  -> 模块开发1做 QC 或指定模块
  -> 模块开发2做 PSD 或指定模块
  -> 各执行对话按里程碑交付
  -> 调研与设计对话汇总并给用户抽查清单
  -> 用户抽查确认
  -> 主框架开发集成、部署、push
```

## 6. Git 和冲突规则

每个执行对话开始前必须执行：

```powershell
git fetch origin
git status --short --branch
git diff --stat
```

规则：

- 本地有未提交改动时，先说明是谁的改动。
- 远端有更新时，先同步或询问。
- 不覆盖其他对话正在改的文件。
- 公共文件由主框架开发优先修改。
- 模块文件由对应模块开发对话优先修改。
- 有冲突必须问用户，不自动覆盖。

## 7. 当前阶段推荐分工

### 7.1 主框架开发

交给：

```text
脑电分析平台 合开发（主框架开发）
```

任务：

```text
请优先实现 QC/PSD 共用公共底座：
1. data_preparation_plan 保存 / 读取。
2. revision 冲突检测。
3. preview segment 保存 / 列表 / 读取 / 删除。
4. /api/tasks 支持 data_preparation_plan_id。
5. artifact 输出规范统一。
6. report package 复现文件统一。
不要擅自修改 QC/PSD 算法细节。
```

### 7.2 模块开发1：QC

交给：

```text
脑电分析平台（模块开发1）
```

任务：

```text
请继续开发 QC 公共数据准备工作台：
1. 64 通道真实波形预览。
2. 横轴/纵轴缩放。
3. 坏导多选。
4. 坏段框选。
5. annotation 处理。
6. 保存当前预览片段。
7. 对接 data_preparation_plan API。
依据 docs/modules/qc_common_data_preparation_requirements.md。
```

### 7.3 模块开发2：PSD

交给：

```text
脑电分析平台（模块开发2）
```

任务：

```text
请开始 PSD 频谱与频段功率模块开发：
1. 阅读 docs/modules/psd_design.md。
2. 阅读 D:\Quanlan\Codes\Python\third_party_eeg_reference_sources\mne-python。
3. 实现 PSD 参数 schema。
4. 实现 Welch 参数校验。
5. 接入 data_preparation_plan_id。
6. 应用 bad_channels / bad_segments / annotation_actions。
7. 输出 spectrum_long.csv。
8. 输出 psd_mean_spectrum.svg 和 psd_band_power.svg。
9. 补 PSD 成功和失败路径验收。
不要擅自修改 QC 模块和平台主框架公共文件。
```

## 8. 阶段成果抽查点

用户只需要在以下节点抽查：

### 主框架开发抽查点

- 是否能保存 / 读取 `data_preparation_plan`。
- 是否支持 revision 冲突检测。
- 是否能保存 / 读取 preview segment。
- `/api/tasks` 是否能接受 `data_preparation_plan_id`。

### QC 模块抽查点

- 是否能真实显示 64 通道波形。
- 横轴 / 纵轴缩放是否顺畅。
- 坏导和坏段是否能保存并恢复。
- 当前预览片段是否能回放。
- 是否明确提示滤波只是预览。

### PSD 模块抽查点

- 是否能基于 QC plan 运行。
- 是否排除了坏导和坏段。
- Welch 参数是否合法并可追溯。
- 是否输出频谱图、频段功率图和 CSV。
- 是否有科研边界提示，不能输出诊断。

## 9. 给三个执行对话的固定启动提示

### 9.1 主框架开发启动提示

```text
你是 QLanalyser Online 的主框架开发对话。
你的职责是平台公共架构、主流程、API、task、artifact、report、部署和集成。
开始前请先执行 git fetch origin、git status --short --branch、git diff --stat。
当前优先任务：实现 QC/PSD 共用的 data_preparation_plan 服务，包括保存、读取、revision 冲突检测、task 引用、artifact 输出规范。不要擅自改 PSD/QC 算法细节。遇到本地或远端冲突必须先提醒我确认。
请先阅读：
- docs/FOUR_CONVERSATION_WORKFLOW.md
- docs/modules/qc_common_data_preparation_requirements.md
- docs/modules/psd_design.md
- docs/architecture/system_architecture.md
```

### 9.2 模块开发1 / QC 启动提示

```text
你是 QLanalyser Online 的模块开发1对话，当前负责 QC 公共数据准备工作台。
开始前请先执行 git fetch origin、git status --short --branch、git diff --stat。
请阅读 docs/FOUR_CONVERSATION_WORKFLOW.md 和 docs/modules/qc_common_data_preparation_requirements.md。
你的任务是实现 64 通道真实波形预览、波形交互、坏导多选、坏段框选、annotation 处理、保存当前预览片段，并对接主框架提供的 data_preparation_plan API。
不要擅自修改 PSD 模块和平台主框架公共文件；需要公共 API 时向主框架开发对话提出集成需求。遇到冲突先提醒我确认。
```

### 9.3 模块开发2 / PSD 启动提示

```text
你是 QLanalyser Online 的模块开发2对话，当前负责 PSD 频谱与频段功率模块。
开始前请先执行 git fetch origin、git status --short --branch、git diff --stat。
请阅读 docs/FOUR_CONVERSATION_WORKFLOW.md 和 docs/modules/psd_design.md。
MNE 依据优先读取 D:\Quanlan\Codes\Python\third_party_eeg_reference_sources\mne-python。
你的任务是实现 PSD 参数 schema、Welch 参数校验、data_preparation_plan_id 接入、bad_channels/bad_segments/annotation_actions 应用、spectrum_long.csv、psd_mean_spectrum.svg、psd_band_power.svg 和 PSD 验收脚本。
不要擅自修改 QC 模块和平台主框架公共文件；需要公共 API 时向主框架开发对话提出集成需求。遇到冲突先提醒我确认。
```
