# WaveformWorkbench GitHub 分支与多对话协作计划

版本：2026-06-27  
仓库：`https://github.com/Guannan-Xi/quanlan-analyser.git`  
主干保护点：`origin/backup/full-qlanalyser-preserve-20260627` at `738609e466db7093686c743f8401222695cba8a1`  
开发分支：`feature/waveform-workbench-edfbrowser-v2`


## 0. Canonical Mainline

后续所有 WaveformWorkbench 分包都必须继承：

```text
base_branch: backup/full-qlanalyser-preserve-20260627
base_commit: 738609e466db7093686c743f8401222695cba8a1
remote_readback: origin/backup/full-qlanalyser-preserve-20260627 == 738609e466db7093686c743f8401222695cba8a1
main_status: not merged or overwritten
```

不得以旧 07 临时状态、未说明来源的 worktree、或聊天口头需求作为主干。

## 1. 当前仓库状态

当前完整功能主干已备份并推送到 GitHub：`origin/backup/full-qlanalyser-preserve-20260627`，提交号 `738609e466db7093686c743f8401222695cba8a1`。本轮不得 `git add .`、不得 reset/stash/clean。所有提交必须小范围、可审查、可回滚。

当前策略：

1. 所有开发包必须声明 base branch 和 base commit：`backup/full-qlanalyser-preserve-20260627@738609e466db7093686c743f8401222695cba8a1`。
2. 先在本地分支完成文档和独立模块。
3. 每个提交只收本切片相关文件。
4. 主干集成前先跑独立 E2E。
5. 通过后再开 PR 或合并回主数据准备页。

## 2. 推荐分支模型

```text
main / release candidate
  ↑
feature/waveform-workbench-edfbrowser-v2
  ├─ docs/waveform-workbench-contract
  ├─ feat/waveform-workbench-shell
  ├─ feat/waveform-workbench-interactions
  ├─ feat/waveform-workbench-drafts
  ├─ test/waveform-workbench-e2e
  └─ feat/integrate-waveform-workbench-data-prep
```

如果 GitHub 上不希望多分支，也可以保持一个 feature 分支，用目录化 evidence 和分阶段 commit 表达上述阶段。

## 3. 提交规范

建议提交：

```text
docs(waveform): define EDFBrowser-style workbench contract
feat(waveform): add standalone workbench shell
feat(waveform): implement EDFBrowser keyboard and mouse controls
feat(waveform): add segment and channel draft overlays
test(waveform): add standalone workbench e2e evidence
feat(data-prep): embed WaveformWorkbench after standalone acceptance
```

禁止：

- `git add .`
- 把癫痫工作台、TimeChart、路由、Headroom 改动混入同一提交。
- 未跑 E2E 就合并主页面。
- 用聊天口头需求替代文档。

## 4. 多对话协作包

### Build 对话包

目标：实现独立 `WaveformWorkbench` shell 和 Canvas renderer。

只允许改：

- `frontend/waveform-workbench.html`
- `frontend/waveform-workbench.js`
- `frontend/waveform-workbench.css`
- `frontend/waveform-workbench-adapter.js`

产出：

- 能加载教学数据并显示 8 通道波形。
- 状态栏显示完整字段。
- 不触碰主 `index.html/app.js`。

### Interaction 对话包

目标：实现 EDFbrowser 鼠标键盘交互。

输入文档：

- `docs/product/waveform_workbench_module_requirements_20260627.md`
- `docs/product/waveform_workbench_module_detailed_design_20260627.md`

必须覆盖：

- 普通滚轮水平浏览。
- Ctrl/Cmd 滚轮锚点缩放。
- PageUp/PageDown。
- Left/Right。
- `+/-` 振幅。
- Ctrl/Cmd + `+/-` 时间窗。
- Browse/write mode separation。

### Verify 对话包

目标：写并运行 E2E。

只允许改：

- `scripts/e2e_waveform_workbench_module.mjs`
- `scripts/validate_waveform_workbench_contract.mjs`
- `work/release_evidence/20260627-waveform-workbench-module/`

产出：

- JSON result。
- 截图。
- active diff no-touch scan。

### Review 对话包

目标：产品/UI/科研逻辑评审。

不改代码，输出：

- 是否符合 EDFbrowser 阅片习惯。
- 是否符合科研人员数据准备逻辑。
- 是否有医疗化文案风险。
- 是否适合集成回主页面。

## 5. Join 标准

所有对话返回必须包含：

```text
branch_or_worktree:
base_branch:
base_commit:
files_changed:
commands_run:
evidence_paths:
passed_tests:
blocked_tests:
no_touch_router_headroom_ipc:
final_receipt:
```

主 PM 只接受 evidence，不接受“我觉得可以”。

## 6. GitHub PR 验收门

PR 必须包含：

- 文档链接。
- E2E JSON。
- Before/after 截图。
- No-touch scan。
- 分析方法不受影响的 smoke。
- 真实或合成 EDF/FIF 数据说明。

外部发布前必须另外补真实匿名 owner data regression。
