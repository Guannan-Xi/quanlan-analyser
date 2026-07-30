# ZCode 工作区整理交接

更新时间：2026-07-22（Asia/Shanghai）  
接收方：ZCode  
工作类型：本地代码工作区整理、清单更新与安全收口

## 1. 任务目标

在不改变科学计算语义、不丢失当前未提交代码、不引入患者数据或密钥的前提下，整理以下权威工作区：

`D:\Quanlan\Codes\Python\qlanalyser-workspace`

本次整理的核心结果应是：目录职责清晰、当前 QEEG 改动全部有归属、临时脚本有明确去留、工作区清单与当前 HEAD/工作树一致、验证可重复。

这不是把所有项目合并为一个应用，也不是删除历史产物的授权。先做只读盘点和整理方案，再做最小、可审查的改动。

## 2. 权威路径

| 用途 | 绝对路径 |
|---|---|
| Git 根目录 | `D:\Quanlan\Codes\Python\qlanalyser-workspace` |
| 唯一 Web 主线 | `D:\Quanlan\Codes\Python\qlanalyser-workspace\projects\web-main` |
| 64 导 QEEG 预研包 | `D:\Quanlan\Codes\Python\qlanalyser-workspace\projects\qeeg-64ch-research` |
| QEEG 源码 | `D:\Quanlan\Codes\Python\qlanalyser-workspace\projects\qeeg-64ch-research\src\qlanalyser_eeg64` |
| QEEG 测试 | `D:\Quanlan\Codes\Python\qlanalyser-workspace\projects\qeeg-64ch-research\tests` |
| 最新报告产物 | `D:\Quanlan\Codes\Python\qlanalyser-workspace\projects\qeeg-64ch-research\results\v0.2.11-complete-microstate-catalog` |
| 工作区治理脚本 | `D:\Quanlan\Codes\Python\qlanalyser-workspace\scripts` |
| 现有工作区清单 | `D:\Quanlan\Codes\Python\qlanalyser-workspace\docs\workspace-inventory` |
| 本轮 Codex 临时目录 | `C:\Users\XGN\Documents\Codex\2026-07-22\quanlan-product-research-health-continuation\work` |

根目录 `AGENTS.md` 是跨项目最高优先级规则。QEEG 项目当前没有独立 `AGENTS.md`，以根规则和 QEEG `README.md` 为准。

## 3. 当前已核验状态

### Git

- 分支：`master`
- HEAD：`8f6d0d51f2ba65266a87825706ca3495c52f05cf`
- HEAD 摘要：`docs: add modularization feature inventory`
- remote/upstream：未配置
- staged：0
- 写入本交接前的工作树：10 个修改文件、8 个未跟踪文件，共 18 项；全部位于 QEEG 项目
- 写入本交接后另有 1 个未跟踪文档：`docs/ZCODE_WORKSPACE_ORGANIZATION_HANDOFF.md`。它不属于 QEEG 科学改动
- 已跟踪修改规模：约 3,334 行增加、157 行删除；未包含 8 个未跟踪文件

修改文件：

```text
projects/qeeg-64ch-research/README.md
projects/qeeg-64ch-research/src/qlanalyser_eeg64/expanded_report.py
projects/qeeg-64ch-research/src/qlanalyser_eeg64/gfp.py
projects/qeeg-64ch-research/src/qlanalyser_eeg64/microstates.py
projects/qeeg-64ch-research/src/qlanalyser_eeg64/pipeline.py
projects/qeeg-64ch-research/src/qlanalyser_eeg64/qc.py
projects/qeeg-64ch-research/src/qlanalyser_eeg64/registry.py
projects/qeeg-64ch-research/src/qlanalyser_eeg64/report.py
projects/qeeg-64ch-research/tests/test_expanded_report_microstate_information.py
projects/qeeg-64ch-research/tests/test_report_contract.py
```

未跟踪文件：

```text
projects/qeeg-64ch-research/src/qlanalyser_eeg64/historical_exports.py
projects/qeeg-64ch-research/tests/test_gfp_retained_intervals.py
projects/qeeg-64ch-research/tests/test_historical_exports_contract.py
projects/qeeg-64ch-research/tests/test_microstate_sequence_dynamics.py
projects/qeeg-64ch-research/tests/test_microstate_sequence_exports.py
projects/qeeg-64ch-research/tests/test_qc_source_time_mapping.py
projects/qeeg-64ch-research/tests/test_saved_microstate_upgrade.py
projects/qeeg-64ch-research/tests/test_saved_report_refresh.py
```

禁止在归属和验证完成前执行 `git reset --hard`、`git checkout --`、`git restore`、`git clean`，也不要覆盖或批量格式化这些文件。

### QEEG 验证基线

2026-07-22 在当前工作树重新执行：

- `python -m pytest -q`：`85 passed, 1 warning`
- `python -m compileall -q src`：通过
- `git diff --check`：通过；仅有 LF/CRLF 转换提示
- 当前包：18 个 Python 模块、15 个测试文件

唯一 warning 来自 ICLabel 对 1-100 Hz 滤波前提的运行时提醒。不要为消除 warning 而静默改变 QC 或滤波语义；如需处理，必须单独评审并补契约测试。

### 最新报告基线

- 目录：`v0.2.11-complete-microstate-catalog`
- `visual_manifest.json`：`status = passed`
- Build ID：`727fe56223960bf4484d5f471918866ada11e0c0af006674ae45e78bc0ed8478`
- manifest 资产数：65
- 两个 HTML 合计 74 次 PNG 引用、65 个唯一 PNG，缺失引用为 0
- `visual_manifest.json` SHA-256：`0ED66640D9C00E1A1F1BC9FC730418A692F789C729DD5D46F7C5A96AEA81DD22`
- `report.html` SHA-256：`FC9A3B58192BED05E7D831AA36E3AC251E909FE3510D20666CCE000C2DAABD88`
- `technical-details.html` SHA-256：`68B3055320B69B32B7F19FE4FB7744AF43D5D9C5E506ECD51EBCBDB12ECBB71C`

报告仍有必须保留的科学限制：19 个连续保留区间中有 1 个不满足当前 GFP 三周期要求。该历史 GFP 结果只能用于追溯，不能表述为已满足当前策略；要完成科学验收，需从原始记录重跑。

当前 Opus 审核门禁仍是 `ACCEPTANCE_INCOMPLETE`。测试通过和 manifest `passed` 只证明当前工程合同，不等同于独立科学审核完成、临床有效或可发布。

## 4. 不可破坏边界

1. `projects\web-main` 是唯一 Web 主线。不得新建平行 Web 服务或复制一整套 backend/frontend/worker。
2. `projects\qeeg-64ch-research` 是独立的 Lab/internal validation 预研包。不得整包并入 `web-main`；只能在独立验证后逐项提升方法。
3. `projects\pc-qlanalyser` 是遗留算法和数值对照来源，不是开发主线。本轮不要移动、清理或模块化它。
4. 所有研究方法必须保留 `research-only / pending professional review` 边界，不得改写为稳定临床结论、诊断或治疗建议。
5. 19 导常模不得外推或命名为 64 导常模。
6. 原始 EEG/生理数据、患者报告、客户标识、数据库、密钥、认证缓存、模型和常模资产不得提交、复制到交接材料或写入日志。
7. `data/`、`work/`、`outputs/`、`results/`、EEG 文件、NumPy 数据、数据库、压缩包、PDF、`.env`、日志、缓存及模型资产已由根 `.gitignore` 排除。不要用 `git add -f` 绕过。
8. 生成报告只作为本地验证证据。不得把 `results/` payload 纳入 Git baseline；清单只记录路径、数量、体积、mtime 和哈希。
9. 不要通过读取旧 Codex 对话、复制 Base64 图片或复制患者报告来“恢复”源码。
10. 当前无 Git remote。未经 XGN 明确确认，不要 push、发布或上传到外部系统。

若需要调用 Opus 审核：使用 OpenAI-compatible 路由；base URL 只从 `REVIEW_MODEL_OPUS48_BASE_URL` 读取，key 只从 `REVIEW_MODEL_OPUS48_API_KEY` 读取，模型名只从 `REVIEW_MODEL_OPUS48_MODEL` 读取。不得输出 key；分发前必须确认上游公布该模型。模型不可用或出现 4xx/5xx 时，门禁继续保持 `ACCEPTANCE_INCOMPLETE`。

## 5. 现有清单与已知过期点

优先复用 `docs\workspace-inventory`，不要重新扫描或复制大体积 payload。重点文件包括：

```text
README.md
baseline-verification.md
exclusions-and-risks.md
qeeg-dynamic-freeze.md
files.csv
duplicate-candidates.csv
generated-output-index.csv
feature-ledger.csv
traceability-matrix.csv
security-path-review.csv
```

这些清单不是当前完成证明，存在明确漂移：

- `qeeg-dynamic-freeze.md` 仍以 `6b18faf` 为稳定参考，当前 HEAD 已是 `8f6d0d5`。
- 冻结文档只记录了 3 个 QEEG 漂移文件，当前实际有 18 个工作树条目。
- 旧 `generated-output-index.csv` 的结果数量和体积已落后于当前本地产物。
- `pyproject.toml` 包版本仍是 `0.2.0`，结果目录已到 `v0.2.11`。不要直接改历史目录名；应先定义“包版本、报告格式版本、产物批次版本”各自语义。
- `baseline-verification.md` 记录的是旧环境无法运行 QEEG 测试；当前环境已验证为 `85 passed, 1 warning`。更新时保留历史记录，同时新增当前验证，不要篡改成“当时也通过”。

## 6. 临时目录处理

临时目录：

`C:\Users\XGN\Documents\Codex\2026-07-22\quanlan-product-research-health-continuation\work`

已知内容：

- `build_v0210.py`：2,065 字节的一次性报告复制/发布包装器。
- `browser-evidence\`：浏览器验证截图/证据。
- `pytest-qeeg-refresh-audit\`：测试生成的报告页面、表和缓存。
- `opus-review-output\`、`opus_review_artifact.txt`、`opus_review_brief.txt`：未完成的审核材料。

QEEG 项目内另有三处可立即再生的缓存，合计约 1.2 MB：

```text
projects\qeeg-64ch-research\.pytest_cache
projects\qeeg-64ch-research\src\qlanalyser_eeg64\__pycache__
projects\qeeg-64ch-research\tests\__pycache__
```

只允许精确清理这三个缓存目录，不得把范围扩大到 `src`、`tests` 或项目根目录。

`build_v0210.py` 没有新科学方法，只调用工作区中的报告输出与校验函数，并直接依赖若干下划线开头的内部函数。工作区当前已有公共入口：

```text
qlanalyser_eeg64.report.refresh_report_from_saved_artifacts
qlanalyser_eeg64.report.upgrade_saved_microstate_report
```

处理原则：

- 不要把版本特定的 `build_v0210.py` 原样长期复制进仓库。
- 若确有重复使用需求，在 `scripts\` 下实现通用、无版本号的入口，例如 `rebuild_saved_report.py`，优先调用公共 API，并补 CLI/失败清理/禁止覆盖测试。
- 若公共入口已覆盖用途，记录对照证据后删除临时副本。
- 浏览器证据、pytest 缓存和审核输出只在必要摘要、状态和哈希完成落档后清理。
- Opus 审核材料的存在不代表审核通过；不得把临时输出改写为 `ACCEPTANCE_COMPLETE`。

## 7. 推荐整理顺序

### 阶段 A：只读快照

1. 记录 `git status --short --branch`、HEAD、18 个工作树条目、mtime 和代码文件 SHA-256。
2. 确认没有其他进程继续写入 QEEG 目录；有外部写入时停止移动、重命名、删除和清单再生成。
3. 对照本交接列出的 18 项 QEEG 改动；仓库内本交接文档单独计数。其他任何新增或消失都先解释再继续。

### 阶段 B：归属与结构

1. 将 QEEG 改动按“QC/源时间映射、GFP、微状态、历史导出、报告发布、注册/管线、测试/文档”分类。
2. 检查公共 API、导入方向和测试覆盖；不要为目录整齐而拆散紧密的科学计算与契约测试。
3. 保留 `qlanalyser_eeg64` 单一包结构，不新建第二套 QEEG 包或复制报告渲染层。
4. 对重复候选执行四级证据：字节一致、引用关系、语义一致、新路径验收。`duplicate-candidates.csv` 只是候选，不是删除授权。

### 阶段 C：脚本与产物

1. 判断一次性报告脚本应泛化还是淘汰；不得复制内部私有 API 形成第二条发布链。
2. 保留 `v0.2.11-complete-microstate-catalog` 作为当前验收基线。
3. 历史 `results\v*` 版本在没有 XGN 明确确认前不删除。若后续获准清理，先生成目录级文件数、体积、mtime、manifest/build ID 和 SHA-256 对照，不读取或复制患者数值。
4. 不创建名为 `latest` 的隐式副本；如需稳定入口，使用有文档的指针/文本清单，并避免复制整个报告目录。

### 阶段 D：清单更新

1. 先确认外部写入停止，再解除旧 QEEG 动态冻结。
2. 复用现有脚本更新 inventory、安全扫描、feature ledger 和 traceability matrix。
3. 更新 `qeeg-dynamic-freeze.md`：记录旧基线、当前 HEAD、全部 18 项漂移及其最终归属。
4. 更新 `baseline-verification.md` 和 `generated-output-index.csv`，区分历史结果与本轮实测结果。
5. 清单不得嵌入患者字段、报告正文、CSV 数值、图片或 Base64；只保留元数据。

### 阶段 E：提交策略

1. 先给 XGN 审查最终文件清单和拟删除清单。
2. 建议把“QEEG 科学代码/测试”“工作区清单/文档”“通用维护脚本”分成可独立审查的提交。
3. 不要把忽略的 results、临时证据、密钥或患者数据带入提交。
4. 未获确认前不 commit；当前无 remote，任何情况下都不要擅自 push。

## 8. 验证命令

在工作区根目录：

```powershell
cd D:\Quanlan\Codes\Python\qlanalyser-workspace
git status --short --branch
git diff --stat
git diff --check
python scripts\build_workspace_inventory.py --check
python scripts\scan_baseline_safety.py --fail-on-block
```

在 QEEG 项目目录：

```powershell
cd D:\Quanlan\Codes\Python\qlanalyser-workspace\projects\qeeg-64ch-research
python -m compileall -q src
python -m pytest -q
```

若本轮没有重新生成报告，三个报告文件的 SHA-256 和 Build ID 应保持本交接中的值。若重新生成，必须记录新旧 Build ID、manifest 状态、资产数量、HTML 图片缺失数、科学限制变化原因，并保证源报告目录不被原地覆盖。

## 9. 验收清单

- [ ] 原有 10 个修改文件和 8 个未跟踪 QEEG 文件全部有书面归属，没有丢失或被覆盖；本交接文档单独计数。
- [ ] `git diff --check` 通过；不通过时没有用全仓格式化掩盖问题。
- [ ] QEEG 完整测试不少于 `85 passed`，warning 被保留或有单独评审证据。
- [ ] `v0.2.11-complete-microstate-catalog` 仍可用，manifest `passed`，HTML 无图片断链。
- [ ] GFP 三周期限制仍出现在 manifest/报告中，没有被弱化或删除。
- [ ] `ACCEPTANCE_INCOMPLETE` 保持不变，除非 Opus 模型可用性和独立审核均按门禁完成。
- [ ] QEEG 仍为独立 Lab/internal validation 包，没有整包接入 `web-main`。
- [ ] 19 导常模没有被改称或外推为 64 导常模。
- [ ] 旧动态冻结和基线文档已按当前 HEAD/工作树更新，历史与当前结果清楚分开。
- [ ] inventory、feature ledger、traceability matrix 和 generated-output index 已重新核验，没有把 payload 纳入 Git。
- [ ] 临时脚本已“泛化并测试”或“确认冗余后清理”，没有形成第二条报告发布链。
- [ ] 没有提交患者数据、EEG 文件、密钥、认证缓存、模型/常模资产、报告 payload 或 Base64。
- [ ] 最终 `git status`、变更摘要、测试结果、未解决风险和拟提交文件清单已回传 XGN。
- [ ] 未经确认没有 commit、push、发布或外部上传。

## 10. 停止条件

遇到以下任一情况，停止删除/迁移并回报：

- 18 个现有工作树条目之外出现无法解释的新增写入；
- 文件没有 ledger 分类或调用链不清楚；
- 科学数值、报告合同或测试发生回归；
- 只能靠视觉相似证明科学结果一致；
- 发现患者、客户、密钥、原始 EEG 或未明来源数据；
- 拟删除项缺少字节、引用、语义和新路径验收证据；
- 拟将 Lab 方法直接放入客户稳定白名单或同步 HTTP 长任务路径；
- Opus 上游模型不可用、返回 4xx/5xx，或模型名未被上游公布。

交付时请只回传：变更文件清单、目录结构变化、验证结果、被保留的风险、需要 XGN 决策的删除/提交项。不要回传患者数据、完整报告正文、Base64 图片或完整渲染/审核日志。
