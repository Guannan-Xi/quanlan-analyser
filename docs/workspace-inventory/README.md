# Workspace Inventory

本目录是大型模块化整理的阶段 0/1 证据入口。清单由当前工作树生成，不把历史文档中的“已完成”陈述当成当前验证结果。

## 范围

模块化审计范围：

- `projects/web-main`
- `projects/qeeg-64ch-research`
- `projects/spike-analysis`

`projects/pc-qlanalyser` 明确排除在模块化改造外；只记录其大模型/常模资产的路径、大小和 SHA-256，文件保持原位、不删除、不迁移。

## 生成方法

```bash
python scripts/build_workspace_inventory.py
python scripts/scan_baseline_safety.py --fail-on-block
```

生成文件：

- `inventory-summary.json`：总量、范围、局限；
- `files.csv`：纳入审计的源码/文档/配置/静态资产，包含路径、大小、SHA-256 和类别；
- `python-symbols.csv`：Python 函数、类、API route、router registration；
- `frontend-entries.csv`：HTML/JS/MJS/CSS 入口、行数、API 字面调用和事件数量；
- `generated-output-index.csv`：生成产物根目录的文件数量和体积，不提交 payload；
- `large-excluded-assets.csv`：PC 大模型/常模资产清单；
- `security-path-review.csv`：客户/患者/秘密样式路径的人工复核入口；
- `baseline-safety-scan.json`：内容级签名扫描结果，只记录路径/规则/行号，不记录命中的值；
- `feature-ledger.csv`：功能—源路径—模块—层级—状态总账；
- `feature-ledger-summary.json`：记录分类数量、基线 commit、未分类计数及动态冻结状态；
- `traceability-matrix.csv`：模块的前端/API/service/worker/domain/report/test/evidence 对照；
- `duplicate-candidates.csv`：重复候选，只登记，不代表可删除；
- `exclusions-and-risks.md`：排除项、已知风险和阻断条件；
- `qeeg-dynamic-freeze.md`：QEEG 外部写入漂移及解除冻结的验收关口。

## 当前基线边界

- 顶层 Git 仓库没有历史 commit，也没有 remote；本轮将创建首个**仅本地**基线，不 push。
- QEEG `results/` 是 355 个文件、约 176 MB 的运行产物，只登记根目录，不进入 baseline commit。
- PC 的 `.pkl` / `.NRM` 大资产保留在磁盘，只登记哈希，不进入普通 Git。
- 原始 EEG、电生理数据、数据库、压缩包、密钥和本地运行状态由根 `.gitignore` 排除。
- `frontend/assets/customer_oddball_case/` 的 manifest 明确说明它是 teaching oddball sample 的 customer-facing alias；未发现原始 EDF 被纳入 Git。该目录仍保留 provenance review 标记，不能据文件名推断成真实客户数据或反过来宣称已做独立隐私审计。
- 安全扫描当前有 4 个 `review`：均是 demo/验收脚本中的本地测试密码字面值；没有发现 private-key、AWS key、GitHub token、OpenAI-style key、Bearer token 或 JWT 阻断签名。匹配值未写入报告。

## “任何功能不要漏”的定义

当前阶段的“纳入总账”不等于“实现正确”或“可发布”。完整性要求是：

1. 每个纳入范围的文件都出现在 `files.csv`；
2. 每个 Python API route/router registration 都出现在 `python-symbols.csv`；
3. 每个前端 HTML/JS/MJS/CSS 入口都出现在 `frontend-entries.csv`；
4. 每个功能要么映射到功能模块，要么明确标为平台公共能力、实验/演示、历史/备份、生成证据或 placeholder；
5. 去重前必须同时满足字节、引用、语义和新路径验收四级证据；
6. 未分类项不允许被删除，也不允许宣称整理完成。

这些清单是后续迁移的防漏底座，仍需在每个模块迁移时补充符号级调用链、数值契约和 E2E 证据。
