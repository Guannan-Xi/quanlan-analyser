from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SLICE = ROOT / "work" / "release_evidence" / "07-full-product-e2e-pdca" / "13_data_prep_analysis_entry_consistency"
DOCS = ROOT / "docs" / "product"
DATE = "20260626"

SCREENSHOT_SOURCES = [
    ("01_teaching_overlay_overflow.png", Path(r"C:\Users\XGN\xwechat_files\wxid_vcs1q0qhwqdb21_2c98\temp\InputTemp\dbd34c36-ffed-4781-883c-8f59142fba94.png")),
    ("02_project_data_fake_status.png", Path(r"C:\Users\XGN\xwechat_files\wxid_vcs1q0qhwqdb21_2c98\temp\InputTemp\9e53c670-f82c-4b47-8078-a6b9878a8cc3.png")),
    ("03_data_prep_blank_waveform.png", Path(r"C:\Users\XGN\xwechat_files\wxid_vcs1q0qhwqdb21_2c98\temp\InputTemp\db37ed8b-9730-47ed-b908-5baf47137785.png")),
    ("04_project_data_overlapping_card.png", Path(r"C:\Users\XGN\xwechat_files\wxid_vcs1q0qhwqdb21_2c98\temp\InputTemp\5eac90b4-6f59-45d0-9c89-a7c078342fbd.png")),
    ("05_selected_data_no_waveform.png", Path(r"C:\Users\XGN\xwechat_files\wxid_vcs1q0qhwqdb21_2c98\temp\InputTemp\3a6a41da-ddd3-43a3-932d-5156b790f7a2.png")),
    ("06_duplicate_analysis_entry.png", Path(r"C:\Users\XGN\xwechat_files\wxid_vcs1q0qhwqdb21_2c98\temp\InputTemp\1b24d1bd-aa44-4a04-b708-ad1d0d26b601.png")),
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def copy_screenshots() -> list[dict]:
    out = SLICE / "00_user_screenshots"
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for name, src in SCREENSHOT_SOURCES:
        dst = out / name
        exists = src.exists()
        if exists:
            shutil.copy2(src, dst)
        rows.append(
            {
                "name": name,
                "source": str(src),
                "evidence": rel(dst),
                "exists": exists,
                "bytes": dst.stat().st_size if dst.exists() else None,
            }
        )
    manifest = {"generated_at": now(), "screenshots": rows}
    write(out / "screenshot_manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    return rows


def requirements_doc() -> str:
    return f"""
# QLanalyser 数据准备与分析入口一致性修复需求文档

日期：{DATE}
需求来源：用户截图 ①-⑥ 与当前 07 主干验收反馈。
适用范围：项目管理、数据管理、数据准备、分析任务、教学模式、封面/后台/全局 UI E2E。

本文件是本次修复的唯一需求来源。实现、DeepSeek 逻辑评审、测试脚本和最终验收必须读取本文件；不得只根据聊天记录转述需求。

## 1. 问题归纳

| 类别 | 截图证据 | 用户表述 | 本次归纳 |
|---|---|---|---|
| R1 布局与溢出 | 图①、图④ | 元素溢出，文案非面向客户 | 弹层、卡片、长文件名、按钮组必须在视口内自适应；客户界面不得出现开发视角、内部状态或挤压布局。 |
| R2 数据状态真实性 | 图②、图④ | 只有教学模式下预置有数据项目；无上传时不要阈值虚假信息；数据状态要一致 | 普通模式不自动塞演示数据；无数据时只能显示空状态和上传/选择入口；不能显示“可开始准备”“待预处理”“阈值”等像真实检测已发生的状态。 |
| R3 选择数据即预览波形 | 图③、图⑤ | 选择数据后要展示波形，没有展示是什么原因 | 点击数据行后应自动进入数据准备并加载可见波形；若后端预览未返回，应显示明确错误/重试，而不是大片空白。 |
| R4 分析任务可用性 | 图⑥ | 分析任务都点不开不能正常使用 | 每个当前可用分析方法卡片必须可点击并触发真实 `/api/tasks`；不可运行时要说明缺少数据/事件/通道位置等前置条件。 |
| R5 入口去重 | 图⑥ | 选择按钮不需要重复显示，保留图6的卡片式即可 | 删除上方重复的“开始 PSD/ERP/...”按钮区；卡片式“当前可用分析方法”成为唯一主入口。 |

## 2. 产品原则

1. 以科研人员真实流程为主线：项目 -> 数据 -> 数据准备/波形预览 -> 修订 -> 选择分析方法 -> 查看结果/下载报告。
2. 演示数据只属于教学模式；普通项目管理页默认不伪造项目、不伪造阈值、不伪造准备状态。
3. 页面状态必须和数据事实一致：没有项目、没有数据、已选择数据、预览加载中、预览失败、可分析、缺少事件、缺少通道位置，分别显示不同状态。
4. 用户看到的是任务语言，不是开发语言：避免“selector、preview method、beta、task runner、workflow id、threshold fake、demo-only”等内部词。
5. 可点击的东西必须可完成；不能完成时必须给可恢复路径。

## 3. 功能需求

### FR-01 教学模式与普通模式隔离

- 普通登录/普通项目管理：不得自动预置“体验中心示例项目”或教学 EEG 文件。
- 只有点击“教学模式”后，系统才加载内置合成 EEG 项目和文件。
- 教学模式应清楚标注“内置示例 EEG 数据，仅用于熟悉流程”。
- 退出教学模式后，不应把示例数据误显示成用户真实项目。

验收：
- 普通模式新会话：项目列表可以为空或只显示真实项目；不得出现教学示例文件。
- 教学模式：出现且只出现一套内置示例项目/文件，可跑通全流程。

### FR-02 无数据状态真实性

- 无项目：提示“请先创建或打开项目”。
- 有项目无数据：提示“当前项目还没有 EEG 数据”，只提供上传入口。
- 有数据未预览：提示“选择数据后自动预览波形”。
- 未生成准备记录：显示“尚未生成数据准备记录”，不得显示“可开始准备”作为质控结论。
- 阈值、滤波、坏道、事件统计只在有真实预览/准备记录后出现。

验收：
- 无数据时页面无“可开始准备”“待预处理”“阈值通过”“已上传后可分析”等误导状态。
- 状态卡、数据行、详情卡、顶部摘要四处状态一致。

### FR-03 选择数据后自动波形预览

- 点击数据行后自动：
  1. 设置当前数据；
  2. 进入数据准备页；
  3. 调用预览接口；
  4. 在主预览区绘制 EEG 波形；
  5. 更新通道数、采样率、窗口、增益和事件信息。
- 预览加载中要显示 skeleton/loading，不得显示空白大框。
- 预览失败要显示原因和“重新加载预览”。

验收：
- 选择示例 FIF/EDF 后 5 秒内可见 canvas 波形或明确错误。
- 大面积空白区域、只有“预览记录已生成”但无波形，均为 P0。

### FR-04 数据准备页布局治理

- 数据列表宽度固定为辅助栏，长文件名省略并可通过 title 查看全称。
- 主预览区必须优先展示波形，操作按钮不挤占绘图区。
- 页面横向滚动条不得因卡片溢出产生。
- 教学蒙版在 390px、768px、1280px、1920px 宽度下不越界。

验收：
- Playwright 检查 body scrollWidth <= viewport width + 2。
- 教学弹层每一步 bounding box 都在视口内。
- 长文件名不会遮盖相邻卡片或按钮。

### FR-05 分析入口唯一且可运行

- 删除或隐藏“选择分析方法”上方重复按钮区。
- “当前可用分析方法”卡片成为唯一主入口。
- 卡片必须是 button 或带 role/button 与键盘可达。
- 点击卡片触发对应真实分析任务：
  - PSD
  - ERP
  - TFR
  - Multitaper PSD
  - Multitaper TFR
  - PAC
  - Connectivity
  - CSD 电流源密度计算
- 无法运行时展示前置条件，不静默失败。

验收：
- DOM 中不再存在重复的 `analysis-method-run-panel` 主按钮区。
- 8 个卡片都可点击、可键盘触发、可产生任务或明确阻断原因。
- 合成数据 E2E 至少覆盖每个方法一次。

### FR-06 客户文案治理

- 所有主页面文案从客户/科研人员角度写：做什么、为什么、下一步是什么。
- 不使用开发词、内部词、半截英文缩写解释不清的词。
- 方法名允许保留学术英文缩写，但必须配中文说明和边界。
- CSD 文案必须说明：传感器空间滤波，不是源定位或诊断。
- Connectivity/PAC 文案必须说明：不能单独解释为因果或信息流方向。

验收：
- 专项文案扫描无 beta/preview/internal/dev/fake 状态。
- DeepSeek 逻辑评审无 P0/P1 未采纳问题。

## 4. 非功能需求

- 性能：选中数据到预览可见，合成示例数据 5 秒内完成；失败时 5 秒内出现错误说明。
- 可访问性：方法卡片可键盘 Tab 聚焦，Enter/Space 可触发。
- 可靠性：真实 API 错误必须可见，不吞掉错误。
- 科学边界：不得把演示数据、单例结果或描述统计写成科学结论。
- 安全：错误信息不得暴露本地绝对路径、密钥或用户隐私。

## 5. PDCA

Plan：以本需求文档、设计文档、UI 设计稿和测试文档作为唯一工作包。

Do：修复教学模式、数据状态、波形预览、分析卡片入口、文案与布局。

Check：静态扫描、DeepSeek 逻辑评审、浏览器 E2E、后台 API smoke、合成数据全方法 E2E、视觉滚动审计。

Act：生成收口验收包；未通过项目进入阻断清单，不以聊天确认替代。
"""


def design_doc() -> str:
    return f"""
# QLanalyser 数据准备与分析入口一致性详细设计

日期：{DATE}
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
{{
  "selectedProjectId": "project id or null",
  "selectedFileId": "file id or null",
  "teachingMode": "off|on",
  "preview": {{
    "fileId": "file id",
    "status": "idle|loading|ready|error",
    "error": "safe user-facing message",
    "waveform": "canvas data or API payload"
  }}
}}
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

选择数据时调用 `chooseWorkspaceFile(fileId, {{ jumpToAnalysis: true, autoPreview: true }})`。如果当前实现没有 `autoPreview`，本次补齐。

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
"""


def ui_doc() -> str:
    return f"""
# QLanalyser 数据准备与分析入口 UI 设计稿

日期：{DATE}
视觉来源：知识库视觉规范中的 B2B scientific dashboard、UX state feedback、design token、scientific chart color gate。当前会话未暴露 Open Design MCP 时，以本地知识库规范和浏览器截图审计作为 fallback。

## 1. 设计目标

达到 `aesthetic and professional`：

- 科研软件可信；
- 首屏能看懂当前状态；
- 操作入口少而明确；
- 不靠绿色表示导航或“可用”，绿色仅表示成功；
- 图表区域不空、不假、不挤。

## 2. 页面线框

### 2.1 数据准备页

```text
┌────────────────────────────────────────────────────────────────────┐
│ 数据准备                                                            │
│ 当前项目 / 当前数据 / 下一步                                         │
├───────────────┬────────────────────────────────────────────────────┤
│ 数据队列       │ 1 选择数据  2 预览波形  3 编辑片段  4 检查  5 确认 │
│ ┌───────────┐ │ ┌────────────────────────────────────────────────┐ │
│ │ 文件 A     │ │ │ 当前数据：文件 A                              │ │
│ │ 已预览     │ │ │ 工具：起点/时间窗/增益/通道/重载              │ │
│ └───────────┘ │ │                                                │ │
│ ┌───────────┐ │ │ EEG 波形 canvas                                │ │
│ │ 文件 B     │ │ │                                                │ │
│ │ 未预览     │ │ └────────────────────────────────────────────────┘ │
│ └───────────┘ │ 片段与标签 / 坏道修订 / 数据准备检查                │
└───────────────┴────────────────────────────────────────────────────┘
```

规则：

- 左侧队列宽 320-420 px，不把长文件名撑开。
- 右侧波形区最小高度 420 px。
- 画布空状态只能出现在无文件/加载/错误场景，不能在“已生成预览”时空白。

### 2.2 分析任务页

```text
┌────────────────────────────────────────────────────────────────────┐
│ 分析任务                                                            │
│ 当前数据：文件 A｜准备记录第 N 版                                    │
├────────────────────────────────────────────────────────────────────┤
│ 当前可用分析方法                                                     │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐               │
│ │ PSD      │ │ ERP      │ │ TFR      │ │ Multi PSD│               │
│ │ 可运行   │ │ 需事件   │ │ 需事件   │ │ 可运行   │               │
│ └──────────┘ └──────────┘ └──────────┘ └──────────┘               │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐               │
│ │ Multi TFR│ │ PAC      │ │ Conn.    │ │ CSD      │               │
│ │ 需事件   │ │ 需频段   │ │ 可运行   │ │ 需位置   │               │
│ └──────────┘ └──────────┘ └──────────┘ └──────────┘               │
└────────────────────────────────────────────────────────────────────┘
```

规则：

- 不再显示上方横向“开始 PSD/ERP/...”按钮组。
- 卡片是唯一主入口。
- 卡片 hover/focus 有清晰边框和阴影。
- 不可运行卡片不灰到不可读；显示“缺少事件”并允许查看说明。

### 2.3 教学蒙版

```text
┌───────────── spotlight ─────────────┐
│ 被引导元素                            │
└──────────────────────────────────────┘
         ┌──────────────────────────┐
         │ 教学模式 1/8              │
         │ 已准备一份合成 EEG...     │
         │ 上一步  下一步  结束教学  │
         └──────────────────────────┘
```

规则：

- 桌面弹层最大宽度 460 px。
- 移动端宽度 `calc(100vw - 32px)`。
- 弹层 position 必须 clamp 到视口内。
- 文案不说“已为你准备一份合成 oddball EEG”后又遮挡；改为更短句。

## 3. 组件规范

### 3.1 长文件名

- 主显示：单行省略；
- title：完整文件名；
- 小字：文件类型、通道数、采样率；
- 不允许撑开卡片。

### 3.2 状态 chip

| 状态 | 颜色 | 文案 |
|---|---|---|
| 空 | neutral | 未选择数据 |
| 上传完成 | info | 已上传 |
| 预览中 | info | 正在预览 |
| 已预览 | success | 已预览 |
| 有准备记录 | success | 准备记录第 N 版 |
| 需要处理 | warning | 需要检查 |
| 错误 | error | 预览失败 |

### 3.3 波形

- 背景：白色；
- 网格线：浅灰；
- 多通道曲线：使用可区分的蓝/紫/橙/灰，不用 rainbow/jet；
- 轴和单位必须可见；
- 有通道名和时间刻度。

## 4. 响应式验收

- 390x844：无横向滚动；教学弹层不越界；卡片单列。
- 768x900：数据队列在上或左，波形区可见。
- 1280x800：首屏可见数据队列、步骤条、波形区。
- 1920x1080：内容不铺满到松散，最大宽度受控。

## 5. 禁止项

- 大块空白但提示“已生成预览”。
- 重复主入口。
- 未上传数据却显示阈值、滤波、坏道结论。
- 开发语言、内部状态、beta/preview/review-needed。
- 卡片文字溢出、按钮挤出容器。
"""


def test_doc() -> str:
    return f"""
# QLanalyser 数据准备与分析入口一致性测试验证文档

日期：{DATE}
测试目标：验证截图 ①-⑥ 暴露的同类问题已被系统性修复。

## 1. 测试范围

- 封面与登录；
- 项目管理；
- 数据管理；
- 数据准备；
- 教学模式；
- 分析任务；
- 结果查看；
- 报告交付；
- 后台健康接口；
- 合成 EDF/FIF 全方法分析；
- UI 滚动、溢出、颜色和文案。

## 2. 测试数据

### 2.1 普通模式

- 不自动创建示例项目。
- 用测试脚本创建临时项目和合成 EEG 文件。
- 无数据状态必须真实。

### 2.2 教学模式

- 使用内置合成 oddball EEG。
- 只在点击教学模式后加载。
- 用于跑通端到端流程，不作为科学结论。

## 3. 自动化测试用例

| ID | 用例 | 步骤 | 通过标准 |
|---|---|---|---|
| T01 | 普通模式无教学数据 | 打开普通项目管理 | 不出现体验中心示例项目/teaching 文件 |
| T02 | 无数据不造假 | 创建空项目并打开 | 不出现可开始准备/阈值/待预处理误导状态 |
| T03 | 教学模式加载示例数据 | 点击教学模式 | 出现且只出现内置示例项目与数据 |
| T04 | 数据选择自动预览 | 选择合成 EEG 文件 | 5 秒内可见波形 canvas 或明确错误 |
| T05 | 波形非空 | 截图检查预览区 | canvas 有非空绘制，不是纯白大框 |
| T06 | 长文件名不溢出 | 使用 teaching_oddball_with_montage_raw.fif | 文件名省略，不遮挡相邻卡片 |
| T07 | 教学蒙版不越界 | 390/768/1280/1920 视口逐步点击 | 每步 tooltip 在视口内 |
| T08 | 分析入口去重 | 打开分析任务页 | 不存在重复按钮区；只有 8 张方法卡主入口 |
| T09 | 方法卡片可点击 | 点击 8 张卡片 | 每张卡片产生真实任务或明确前置条件 |
| T10 | 键盘可达 | Tab/Enter/Space 操作方法卡 | 可聚焦、可触发 |
| T11 | 合成数据全方法 | 运行模块级合成数据 E2E | 8 个当前方法全部通过 |
| T12 | 后台 smoke | 运行后台 API smoke | status passed，blockers 为空 |
| T13 | 科学绘图规范 | 审计输出图 | 无 rainbow/jet 默认、轴/单位/边界说明存在 |
| T14 | 文案治理 | 扫描客户界面 | 无 beta/preview/internal/dev/fake 词 |
| T15 | 全页面滚动 | 多视口截图 | body 无横向溢出，P0/P1 为 0 |

## 4. 手工验收清单

- 图①：教学蒙版内容不被右侧裁切，按钮完整，文案短。
- 图②：普通模式不预置教学文件；教学模式才出现示例数据。
- 图③/⑤：选中数据后主区域显示真实波形，不是空白。
- 图④：项目/数据卡不重叠，长文件名不撑开布局。
- 图⑥：上方重复按钮区消失；卡片式方法可点击。

## 5. DeepSeek 评审

必须把需求、设计、UI 设计稿和测试计划发送给 DeepSeek 逻辑评审，重点问：

1. 数据准备流程是否符合科研人员习惯；
2. 无数据/教学数据边界是否清楚；
3. 分析入口是否足够明确；
4. 文案是否像客户能理解的任务语言；
5. 是否存在科学边界过度承诺。

DeepSeek 输出只作为建议，最终采纳由 GPT-5.5/Codex 负责。

## 6. 收口标准

所有自动化测试通过；DeepSeek P0/P1 已采纳或有合理拒绝记录；浏览器截图证据存在；最终验收包为 `completed_final_receipt` 且 blockers=0。
"""


def execution_packet() -> str:
    return f"""
# 07 Execution Packet: Data Preparation and Analysis Entry Consistency

日期：{DATE}
仓库：`D:\\Quanlan\\Codes\\Python\\quanlan-analyser-official`
Pool：复用当前 07 验收池，不改 router/headroom/ipc/gateway。

## Objective

Fix the screenshot-reported class of issues across QLanalyser customer workflow:

1. No layout overflow.
2. No fake status when no data exists.
3. Selecting data automatically shows waveform preview.
4. Analysis method cards are the only primary method entry.
5. Every current method entry is clickable and E2E tested.

## Allowed write scope

- `frontend/index.html`
- `frontend/app.js`
- `frontend/styles.css`
- targeted acceptance scripts under `scripts/`
- docs/evidence under this slice

## Forbidden scope

- router / Headroom / IPC / gateway changes
- secret files
- broad git reset
- deployment or push

## Execution packets

1. Documentation packet: generate requirements/design/UI/test docs and screenshot manifest.
2. DeepSeek packet: researcher workflow and Chinese operation logic review.
3. UI implementation packet: layout, states, entry dedupe.
4. Script-validator packet: static, browser, API, synthetic data, visual scroll.
5. Acceptance packet: final evidence manifest and receipt.

## Required commands

```text
python -X utf8 scripts/check_no_mojibake.py <new docs/evidence>
node --check frontend/app.js
node --check <new acceptance scripts>
python -X utf8 -m py_compile <new python scripts>
node <browser acceptance for data prep and analysis cards>
python -X utf8 scripts/run_full_product_backend_api_smoke.py
python -X utf8 scripts/acceptance_synthetic_edf_full_analysis_scientific_figures.py
python -X utf8 <final acceptance packet builder>
```

## Stop conditions

- Preview API cannot return drawable data and no safe fallback is available.
- Analysis actions fail due backend task contract mismatch.
- Browser E2E cannot reach 4174/8001.
- DeepSeek route unavailable after route-check; then record unavailable evidence and continue with script/browser validation.
"""


def deepseek_prompt() -> str:
    return f"""
# DeepSeek Researcher Logic Review Prompt

请你作为脑电科研工作流与中文操作逻辑评审员，审阅以下文档：

- `docs/product/qlanalyser_data_prep_analysis_entry_consistency_requirements_20260626.md`
- `docs/product/qlanalyser_data_prep_analysis_entry_consistency_design_20260626.md`
- `docs/product/qlanalyser_data_prep_analysis_entry_consistency_ui_design_20260626.md`
- `docs/product/qlanalyser_data_prep_analysis_entry_consistency_test_plan_20260626.md`

本次要修复的问题：

1. 教学蒙版和长文件名导致元素溢出，客户文案不自然。
2. 普通模式不应预置教学项目；没有上传数据时不能显示阈值或虚假准备状态。
3. 选择数据后必须展示波形；不能只显示“预览记录已生成”但画布为空。
4. 分析任务当前点不开；8 个正式方法必须可点击或给出明确前置条件。
5. 重复的“选择分析方法”按钮区要删除，保留卡片式方法入口。

请输出：

```text
结论: pass|revise|block
主要问题:
- [P0/P1/P2/P3] 问题、原因、对科研人员的影响、建议
必须进入测试的验收点:
- ...
可接受的残余风险:
- ...
不应出现的过度承诺:
- ...
```

请重点从科研人员习惯、数据状态真实性、分析入口可理解性、中文客户文案、非医疗科研边界五个角度评审。
"""


def main() -> int:
    screenshots = copy_screenshots()
    files = {
        DOCS / f"qlanalyser_data_prep_analysis_entry_consistency_requirements_{DATE}.md": requirements_doc(),
        DOCS / f"qlanalyser_data_prep_analysis_entry_consistency_design_{DATE}.md": design_doc(),
        DOCS / f"qlanalyser_data_prep_analysis_entry_consistency_ui_design_{DATE}.md": ui_doc(),
        DOCS / f"qlanalyser_data_prep_analysis_entry_consistency_test_plan_{DATE}.md": test_doc(),
        SLICE / f"data_prep_analysis_entry_consistency_execution_packet_{DATE}.md": execution_packet(),
        SLICE / "deepseek" / "researcher_logic_review_prompt.md": deepseek_prompt(),
    }
    for path, text in files.items():
        write(path, text)
    summary = {
        "status": "prepared",
        "generated_at": now(),
        "docs": [rel(path) for path in files],
        "screenshots": screenshots,
    }
    write(SLICE / "docs_manifest.json", json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
