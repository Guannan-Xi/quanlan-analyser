# QLanalyser WaveformWorkbench 主干基线声明

版本：2026-06-27  
状态：主干基线 / 后续 WaveformWorkbench 独立模块开发必须继承

## 1. 主干来源

本轮 QLanalyser 后续开发以完整功能保留备份分支作为主干保护点：

- GitHub 分支：`origin/backup/full-qlanalyser-preserve-20260627`
- 本地分支：`backup/full-qlanalyser-preserve-20260627`
- 提交号：`738609e466db7093686c743f8401222695cba8a1`
- PR 入口：https://github.com/Guannan-Xi/quanlan-analyser/pull/new/backup/full-qlanalyser-preserve-20260627
- 远端读回：已确认远端分支提交号与本地一致
- `main`：没有被合并或覆盖

主干来源对话：

- thread id：`019f04c3-c297-7883-87d9-a23cf6729be6`
- title：`Caludecode`
- 角色：完整全产品 E2E 双评审、修复包验收、主干 acceptance 入口

本轮 WaveformWorkbench 开发不再以零散聊天口头需求为基线，而是以该完整功能保留分支和双评审证据为基线。

## 2. 必须继承的主干结论

1. 整个 QLanalyser 功能体系保留，不按“只留 07”裁剪其他功能。
2. 当前产品合同是 **8 个正式分析方法 + QC 作为数据准备依赖**。
3. QC 不是独立分析方法卡片。
4. 数据准备和波形预览属于分析前准备流程。
5. Canvas 是当前主线；本轮不接入 TimeChart。
6. 教学模式与普通模式独立，但共用同源分析和波形工作台。
7. 非医疗科研边界必须保留，不输出诊断、治疗、临床决策口径。
8. 外部完整发布仍因授权匿名 owner data `input_manifest.json` 缺失而 blocked。
9. 内部开发状态为 `pass_with_risks`，允许继续开发和模块化重构。

## 3. 已确认的备份安全检查

来源线程已确认：

- 暂存里没有 `work/`、`data/invoices/`、真实 `.env`、私钥、`.bak` 临时文件。
- `.gitignore` 已补：`*.bak-*`、`data/invoices/**`。
- 只发现 2 个大于 1MB 文件，均为癫痫 ML 模型资产，按全功能保留策略保留。
- 脱敏密钥扫描 9 个命中，未发现真实外部 API key；主要是 demo/test 密码、占位符、选择器/路径假阳性。
- 已通过：`git diff --cached --check`、Python 编译检查、前端 app/module-lab/qc-lab 语法检查、Canvas 合同校验。
- GitHub 远端读回确认：分支提交号与本地一致。

## 4. 主干证据文件

- `docs/product/qlanalyser_full_product_complete_e2e_review_20260627.md`
- `work/release_evidence/20260627-full-product-complete-review/complete_review_result.json`
- `docs/product/qlanalyser_complete_e2e_release_blocker_fixes_acceptance_20260627.md`
- `work/release_evidence/20260627-complete-e2e-release-blocker-fixes-acceptance/acceptance_result.json`
- `docs/product/qlanalyser_complete_e2e_fix_packet_to_07_20260627.md`
- `work/release_evidence/20260627-complete-e2e-release-blocker-fixes/complete_e2e_release_blocker_fix_receipt.json`

机器可读 manifest：

- `work/release_evidence/20260627-waveform-workbench-mainline/mainline_manifest.json`

## 5. Git 分支策略

当前本地开发分支：

- `feature/waveform-workbench-edfbrowser-v2`

主干保护点：

- `backup/full-qlanalyser-preserve-20260627` at `738609e466db7093686c743f8401222695cba8a1`

后续规则：

1. 把 `backup/full-qlanalyser-preserve-20260627` 视为完整产品主干保护点。
2. 把 `feature/waveform-workbench-edfbrowser-v2` 作为 WaveformWorkbench 独立开发分支。
3. 不直接把当前工作树推为 GitHub default branch。
4. WaveformWorkbench 独立 E2E 通过后，再按 PR/合并包进入主干。
5. 其他对话开发必须基于该主干保护点，不能另起不明来源分支。

## 6. 其他对话协作规则

其他对话接包前必须先读：

1. 本文件。
2. `docs/product/waveform_workbench_module_requirements_20260627.md`
3. `docs/product/waveform_workbench_module_detailed_design_20260627.md`
4. `docs/product/waveform_workbench_module_e2e_test_plan_20260627.md`
5. `docs/product/waveform_workbench_git_collaboration_plan_20260627.md`

回包必须包含：

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

## 7. 禁止范围

本轮 WaveformWorkbench 不触碰：

- router
- Headroom
- gateway
- IPC
- model route
- TimeChart dependency
- epilepsy workbench
- 主分析算法实现

## 8. 下一真实动作

以该主干保护点为准，开始独立 `WaveformWorkbench` 模块开发：先 shell + Canvas 显示，再鼠标/键盘交互，再草稿/恢复，再 E2E，最后集成数据准备页。
