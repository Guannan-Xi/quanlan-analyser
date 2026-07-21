# QLanalyser 教学模式独立产品形态测试验证文档

生成时间：2026-06-26T10:35:39.972886+00:00
文档状态：实施前测试计划 v1

## 1. 测试目标

验证教学模式与普通模式完全隔离，并能用不可删除内置教学数据端到端跑通所有上线分析方法；同时验证引导式教学、视觉状态、科学图表规范、错误恢复和非医疗边界。

## 2. 测试范围

包含：普通/教学模式切换、教学项目和教学数据自动准备、教学数据不可删除、卡片式学习路径、蒙版步骤引导、每个分析方法端到端运行、统一结果预览、科学图表和导出包检查、后台 API 与前端 UI 一致性。

不包含：重新开发癫痫 ML；仅在 02 交接后接收并纳入教学 E2E。也不包含生产临床验证、支付/权限系统重构、router / Headroom / IPC / gateway 变更。

## 3. 测试数据

| 数据 | 生成/来源 | 覆盖 |
|---|---|---|
| Oddball 教学 EEG | `scripts/generate_teaching_oddball_case.py` 或现有 `lab_demo_service` | QC、ERP、PSD、Band Power、TFR、Multitaper、PAC |
| 癫痫样事件教学 EEG | 02 交接的 ML trigger fixture | Epilepsy STD/ML、工作台、人工复核 |
| 合成虚拟 EEG | 新增 release E2E 生成脚本 | 所有方法的可控回归 |
| 错误数据 fixture | 低采样率、无事件、缺通道、短时长 | 错误恢复和禁用状态 |

## 4. 测试矩阵

### T-MODE 模式隔离

| ID | 场景 | 步骤 | 预期 |
|---|---|---|---|
| T-MODE-01 | 普通模式默认 | 打开首页 | 不显示教学项目/教学数据 |
| T-MODE-02 | 进入教学模式 | 点击进入教学模式 | 显示教学状态条、教学路径卡、教学数据 |
| T-MODE-03 | 返回普通模式 | 点击返回普通模式 | 不保留教学数据选中态 |
| T-MODE-04 | 刷新保持模式 | 教学模式刷新 | 保持教学模式或按设计恢复，并显示明确状态 |
| T-MODE-05 | 个人中心保持 | 两种模式都检查右上角 | 个人中心可见可用 |

### T-DATA 教学数据保护

| ID | 场景 | 步骤 | 预期 |
|---|---|---|---|
| T-DATA-01 | 自动准备教学数据 | 进入教学模式 | 教学项目与教学文件存在 |
| T-DATA-02 | UI 删除保护 | 查看教学数据卡 | 删除隐藏或禁用并说明原因 |
| T-DATA-03 | API 删除保护 | 调删除接口 | 返回 `TEACHING_DATASET_PROTECTED` |
| T-DATA-04 | 普通模式隔离 | 返回普通模式 | 教学数据不显示 |
| T-DATA-05 | 重启恢复 | 重启后端后进入教学模式 | 教学数据仍可用 |

### T-GUIDE 引导蒙版

| ID | 场景 | 步骤 | 预期 |
|---|---|---|---|
| T-GUIDE-01 | 首次引导 | 首次进入教学模式 | 显示卡片与开始引导 CTA |
| T-GUIDE-02 | 蒙版定位 | 点击开始引导 | 目标控件高亮，文案解释当前动作 |
| T-GUIDE-03 | 前进后退 | 点击下一步/上一步 | 锚点正确、滚动稳定 |
| T-GUIDE-04 | 跳过恢复 | 跳过后刷新 | 可继续或重置 |
| T-GUIDE-05 | 键盘操作 | Tab/Esc 操作 | 焦点可达，Esc 关闭 |
| T-GUIDE-06 | 窄屏 | 390px 宽度 | 无横向溢出，蒙版不遮挡目标 |

### T-METHOD 全方法端到端

| ID | 方法 | 数据 | 验收 |
|---|---|---|---|
| T-METHOD-QC | QC/数据准备 | Oddball | 质量摘要、波形预览、预处理状态可见 |
| T-METHOD-PSD | PSD | Oddball/合成 EEG | PSD 图、表、参数 manifest |
| T-METHOD-BAND | Band Power | Oddball/合成 EEG | 提交 PSD alias，频带图/表可见 |
| T-METHOD-ERP | ERP | Oddball events | ERP 图和事件摘要 |
| T-METHOD-TFR | TFR | Oddball events | 时频图、baseline、色条说明 |
| T-METHOD-MTPSD | Multitaper PSD | 合成 EEG | 多窗 PSD 输出 |
| T-METHOD-MTTFR | Multitaper TFR | Oddball events | 多窗时频输出 |
| T-METHOD-PAC | PAC | 合成 PAC 数据 | PAC 图/表，统计限制可见 |
| T-METHOD-CSD | CSD | 合成 EEG | CSD 输出，文案不混作重参考 |
| T-METHOD-CONN | Connectivity | 合成 EEG | 连接性结果，不暗示因果 |
| T-METHOD-EPI | Epilepsy | 02 fixture | 候选事件、工作台、复核导出 |

## 5. 自动化脚本建议

```text
scripts/acceptance_teaching_mode_static.mjs
scripts/e2e_teaching_mode_full_flow.mjs
scripts/generate_teaching_mode_virtual_data.py
scripts/validate_teaching_mode_artifacts.py
scripts/review_teaching_mode_figures.py
```

输出目录：

```text
work/release_evidence/20260626-teaching-mode-independent-product-design/
  requirements_design_test_manifest.json
  static_acceptance.json
  browser_e2e.json
  visual_review/
  figure_review.json
  deepseek_logic_review_packet.md
  final_acceptance_packet.json
  final_acceptance_packet.md
```

## 6. DeepSeek 逻辑评审门禁

当前 Codex 会生成 DeepSeek 评审包，但若没有真实 DeepSeek 调用证据，不得标记为已通过。

DeepSeek 评审问题：教学模式/普通模式隔离是否合理；教学数据不可删除是否符合科研客户试用习惯；卡片引导是否自然；是否污染真实项目；方法顺序是否符合 EEG 分析逻辑；癫痫教学是否避免医疗化误读；文案是否客户视角。

## 7. 发布阻断项

P0：普通模式出现教学数据；教学数据可删；教学模式无法跑通核心方法且无降级；蒙版遮挡目标控件；结果页缺参数/单位/导出；癫痫文案出现诊断/治疗；错误泄露路径或密钥。

P1：空状态没有下一步；长任务没有阶段反馈；mini-check 缺失；窄屏拥挤；DeepSeek 逻辑评审未完成但准备公测。

## 8. 最终验收包字段

```json
{
  "route_decision": "...",
  "mode_isolation": "passed|failed",
  "teaching_data_protection": "passed|failed",
  "guided_onboarding": "passed|failed",
  "method_e2e": {},
  "visual_review": {},
  "scientific_figure_review": {},
  "deepseek_logic_review": {},
  "backend_api_review": {},
  "gpt55_acceptance": "passed|blocked",
  "final_receipt": "completed_final_receipt|blocked_final_receipt",
  "next_real_artifact": "..."
}
```
