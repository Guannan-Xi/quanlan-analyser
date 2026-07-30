# QLanalyser 第一阶段功能清单与架构重构路线图

- 状态：草案，待架构组评审
- 日期：2026-07-22
- 编写依据：对 `qlanalyser-workspace` 全部四个项目（`web-main`、`qeeg-64ch-research`、`pc-qlanalyser`、`research-modules`）的只读代码核查，结合产品经理（郤冠楠）确认的 6 项决策
- 关联文档：`product_requirements_freeze.md`（V1冻结范围）、`module_lifecycle_matrix.md`（模块生命周期矩阵）
- 定位：本文档是**工程实施路线图**，供研发/算法团队据此做架构设计和排期，不是需求冻结文档本身，如有冲突以 `product_requirements_freeze.md` 为准并反馈更新。

## 0. 决策承接

1. 超前实现（账户/计费/OSS/配额等）→ 标注"超前实现，第一阶段不对外开放"，**保留代码，不删除**。
2. 自动QC/去噪 → 确认P0，技术路线为 **MNE生态成熟库**（pyprep RANSAC + ICA/ICLabel + autoreject）。
3. 微状态 → 纳入第一阶段；GFP/GMD、复杂度指标、Aperiodic谱 → 延后1.x。
4. SimNIBS → 延后1.x，非第一阶段阻塞项。
5. 架构 → 第一阶段必须重构到需求文档描述的架构（registry驱动、adapter层、版本化实体）。
6. 本文档即该决策的落地清单。

**关键修正**（本轮代码核查新发现，纠正此前判断）：此前认为"坏导检测/ICA+ICLabel/坏段筛选/SafetyGate 在整个代码库都不存在，需从零构建（预估6-9周）"的判断**部分错误**。经过对 `qeeg-64ch-research/src/qlanalyser_eeg64/qc.py` 和 `preprocess.py` 的逐行核查，确认：

- ICA（MNE `mne.preprocessing.ICA`，extended infomax）—— 真实实现，`qc.py:87-135`
- ICLabel 自动分类（`mne_icalabel.label_components`，可选依赖）—— 真实实现，非占位
- SafetyGate 机制（`AUTO_PASS` / `AUTO_PASS_BLOCKED` 结论）—— **已有真实实现**，直接对应 `research-modules/contracts/lifecycle-safety.schema.json` 中此前认为"有schema无实现"的概念
- 滤波（notch → bandpass → 平均参考 → 重采样）—— 真实实现，`preprocess.py:18-45`（顺序以代码为准：`set_eeg_reference`在`resample`之前）
- 坏导检测/坏段剔除 —— 真实实现，但是**手写阈值算法**（robust z-score / peak-to-peak），不是 pyprep/autoreject

即：SafetyGate、滤波可以直接**迁移**而非新建；ICA/ICLabel的算法逻辑同样是现成实现，但目前耦合在同一个函数内，迁移时需要先拆分重构（见1.2节表格说明），不是原样搬移文件；只有坏导检测和坏段剔除需要从"手写阈值"**升级**为 pyprep/autoreject 才符合本次选定的"成熟库路线"。这大幅降低了P0工作量和风险，不再是从零构建。

（前置说明：`pc-qlanalyser` 中 ICA/坏导检测完全缺失的判断依旧成立——该结论只针对 `pc-qlanalyser` 这个独立的遗留桌面项目，与 `qeeg-64ch-research` 的核查结果互不矛盾，两者是不同代码库。）

---

## 1. 第一阶段功能清单

### 1.1 Scalp EEG 核心分析方法（对客户开放）

| 方法 | 状态 | 来源 |
|---|---|---|
| PSD (Welch) | 已实现，保留，**须补接1.2节QC产物消费+SafetyGate门控（见下方说明）** | `web-main/eeg_core/analysis/psd.py` |
| Band Power | 已实现，保留，**须补接1.2节QC产物消费+SafetyGate门控（见下方说明）** | `band_power.py` |
| ERP/P300 | 已实现，保留，**须补接1.2节QC产物消费+SafetyGate门控（见下方说明）** | `erp.py` |
| TFR/ERSP/ITC | 已实现，保留，**须补接1.2节QC产物消费+SafetyGate门控（见下方说明）** | `tfr.py` |
| Multitaper | 已实现，保留，**须补接1.2节QC产物消费+SafetyGate门控（见下方说明）** | `multitaper_psd_tfr.py` |
| PAC v1/v2 | 已实现，v2已进入stable-candidate，**须补接1.2节QC产物消费+SafetyGate门控（见下方说明）** | `pac.py`/`pac_v2.py` |
| Connectivity | 已实现（自研numpy/scipy，非mne-connectivity），保留，**须补接1.2节QC产物消费+SafetyGate门控（见下方说明）** | `connectivity.py` |
| Reference/CSD | 已实现，保留，**须补接1.2节QC产物消费+SafetyGate门控（见下方说明）** | `reference_csd.py` |

**"已实现，保留"不代表这些方法在第一阶段自动QC/SafetyGate接入上无工作量**：经核查（`task_service.py:654-680`），现有8个对客开放方法（PSD/Band Power/ERP/TFR/Multitaper/PAC v1/v2/Connectivity/Reference-CSD）的执行链路完全同构——都是`task_service.create_task()`直接把`eeg_file.stored_path`（原始上传文件路径）传给各自的`run_xxx()`函数，函数内部用`read_raw()`读原始文件，不存在任何独立QC清洗步骤产出中间清洗文件供这些方法消费（web-main当前没有`cleaned_raw`/`PreprocessingVersion`这类概念，`qc.py`只存在于独立的`qeeg-64ch-research`项目，与web-main无引用关系）。即：**这8个方法目前都"尚未接入自动QC管线"**，不存在"部分方法已接入、只差ERP/TFR"的情况；微状态是本文档新增的第9个对客开放方法，同样尚未接入（因为它还未迁移进web-main，不在`task_service.py:654-680`的核查范围内，但同理不存在已接入的情况）。**第一阶段对客开放方法总数为9个（8个现有+微状态）**：ERP/TFR固定走标注式分支，不需要额外决策；其余7个方法（PSD/微状态/Connectivity/Band Power/Multitaper/PAC v1/v2/Reference-CSD——其中6个属于上述已核查的现有8个方法，微状态是新增的第9个）消费QC产物时走的是步骤6拼接产物或标注式分支（二选一，各方法独立选定，已作为Phase 0c纳入排期，覆盖全部9个方法，不只是PSD/微状态/Connectivity三者），接入QC+SafetyGate门控的工作量对这9个方法同等规模，需要一并排期，不能因为1.1节写的是"已实现，保留"就被误判为无需改动。
| **微状态（Microstate）** | **新增P0，迁移** | `qeeg-64ch-research/microstates.py` → `eeg_core/analysis/microstate.py` |
| GFP/GMD、复杂度指标、Aperiodic谱 | **延后1.x**，代码已在qeeg-64ch验证但不进第一阶段 | 不动 |

### 1.2 预处理与自动QC（新增P0，MNE生态路线）

| 能力 | 处理方式 | 目标实现 |
|---|---|---|
| 滤波（notch → bandpass → 平均参考 → 重采样） | **直接迁移**，qeeg-64ch已是MNE原生实现，**但含`qc.py:47`平均参考bug，须按1.2.1节步骤2修复后再迁移，不能原样搬移** | `preprocess.py` → `eeg_core/preprocess/filter.py`（替换现有4行占位） |
| ICA计算 + ICLabel自动分类 | **不是直接迁移，需要重构拆分**：ICA拟合（`qc.py:92-96`）与ICLabel分类/剔除（`qc.py:105-135`）目前写在同一个函数`_remove_iclabel_components`（`qc.py:87-135`）内部，`ica.apply()`直接作用于拟合出的`ica`对象（132-134行），二者未解耦。迁移到`eeg_core/preprocess/ica.py`前必须先把该函数拆成"ICA拟合"和"ICLabel分类/剔除"两个独立步骤，不能按行号原样切一段代码搬走。**另需修复秩缺陷未处理问题**：`qc.py:93`当前用`n_components=方差比例`按满秩假设拟合，未考虑插值坏导+平均参考带来的秩下降（见1.2.1节步骤4说明），迁移时须显式计算并传入实际数据秩，不能依赖MNE的`rank="info"`自动估计（其依赖`info["bads"]`/SSP投影记录，与本方案的清空`bads`+无投影平均参考不兼容，会高估秩），也不能原样搬移 | `qc.py:87-135`（需重构+秩修复后再迁移），同时将`mne-icalabel`从可选依赖升级为web-main **必装依赖**（P0能力不能默认被跳过） |
| SafetyGate（AUTO_PASS/AUTO_PASS_BLOCKED） | **终态聚合逻辑本身可直接迁移**（`_gate_reasons`，真实实现，非占位），但它聚合的四类输入中两类（坏导检测/坏段剔除）正被pyprep/autoreject替换，迁移时必须同步确认：pyprep RANSAC失败、autoreject拒绝率超限等新失败模式是否需要新增对应的阻断原因（当前逻辑只覆盖手写阈值算法的失败模式），不是把整段代码原样搬走就自动覆盖新算法的失败场景 | `_gate_reasons`定义于`qc.py:344`，在`run_auto_qc`内的调用点是第71行；落地为task_service产出物字段，对应 `lifecycle-safety.schema.json` |
| 坏导检测 | **升级**：手写z-score → `pyprep` RANSAC；**RANSAC本身依赖电极几何/montage才能运行**，无montage时降级为现有手写z-score算法，不是简单"fallback"而是明确的替代路径 | 新写，无montage分支复用现有阈值逻辑 |
| 坏段/坏epoch剔除 | **升级**：手写阈值 → `autoreject`；**`autoreject`的局部修复（epoch级插值式剔除）同样依赖电极几何/montage**（原理是对每个epoch局部插值可疑坏导再评估，与pyprep RANSAC同属"需要通道位置"的算法族），无montage时不能假定其能以同样方式运行，需要与步骤1/步骤5同构地补一条降级路径：无montage时降级为`autoreject`的纯阈值（peak-to-peak）拒绝模式（不做局部插值修复，只做整段epoch剔除），或等价地沿用现有手写阈值算法，而不是无差别调用完整`autoreject`流程 | 新写，无montage分支同样需要复用/降级为阈值-only模式 |
| 坏导插值 | **直接迁移**，MNE `interpolate_bads()`；插值本身无问题，但**插值成功后向下游传递`bad_channels`的方式含`qc.py:47`平均参考bug，须按1.2.1节步骤2修复**，不能原样搬移调用方式 | `qc.py:42-46` |
| raw-to-cleaned时间映射 | **直接迁移**，`qc.py`已有真实实现 | `qc.py:182`的`build_source_time_mapping`、`qc.py:309`的`restore_source_time_axis` |
| 清洗前后对比视图、清洗版本冻结/复用 | **新建**，无现成代码（可复用上一行迁移的时间映射函数作为底层依赖） | 对应第2节Phase C的PreprocessingVersion实体 |

依赖变更提示：新增 `pyprep`、`autoreject`、`mne-icalabel` 为 web-main 后端**必装**依赖（当前均是可选或不存在），需要在 `pyproject.toml`/`requirements` 中声明并纳入CI。

#### 1.2.1 自动QC管线执行顺序（P0，1.2节各子能力必须按此顺序整合，不得并行拆开排期；步骤1相对步骤3的先后关系是暂定顺序，见本节末尾"未决风险"，实施前必须先确认后才能定稿）

1.2节表格里的各子能力不是互相独立的模块，是同一条QC管线的顺序步骤，`qeeg-64ch-research/qc.py`的`run_auto_qc`函数（实际跨越第34-74行，即函数体第一行`def run_auto_qc`到`return`，此前"41-72"的行号引用不准确，已更正）已经按下述顺序真实跑通（该顺序是手写阈值算法验证过的顺序；仅坏导检测/坏段剔除两步升级为pyprep/autoreject时，步骤1是否仍应位于步骤3滤波之前，属于待确认的暂定安排，不是既定结论）。步骤4-5引用的`_remove_iclabel_components`函数**定义**在`qc.py:87-135`（文件中排在`run_auto_qc`之后），但它在`run_auto_qc`内部的**调用点是第48行**——先于第53-57行的坏段重拼接，执行顺序与下述步骤4→6一致；此前的行号引用把"函数定义位置"和"函数调用位置"混同，容易被误读成ICA在重拼接之后执行，特此更正：

1. **坏导检测**（暂定顺序，见末尾未决风险）：有电极几何/montage时用升级后的pyprep RANSAC；无montage时RANSAC不可用，降级为现有手写z-score算法 → 产出候选坏导列表。两种路径都继续进入步骤2，由步骤2统一判定几何缺失是否触发阻断，避免步骤1和步骤2各自对"无几何"重复处置。
2. **坏导插值**（迁移，MNE`interpolate_bads()`）→ 依赖步骤1的候选列表和电极位置信息；若无电极几何信息，跳过插值并进入SafetyGate阻断分支（不是静默丢弃，也不因为步骤1已降级为z-score而豁免这个阻断判定）。**该阻断分支与步骤5的处置方式一致：后续步骤3-6仍继续执行**，此时步骤3的输入是步骤1产出的候选坏导标记、但未插值的连续数据（坏导本身仍在数据里，未被剔除或置零），管线全程带着"存在未处理坏导"的状态往下走，直到步骤7汇总时因步骤2的阻断原因命中而判定整体结论为`AUTO_PASS_BLOCKED`；不能因为无montage就让管线在步骤2处整体停止。**该分支必须把候选坏导写入`info["bads"]`再进入步骤3**（对应`qc.py:47`把`candidate_bads`传入`preprocess_full_recording`的`bad_channels`参数，该函数在滤波/参考前先执行`processed.info["bads"] = known_bads`，见`preprocess.py:24-26`）：MNE的平均参考（`set_eeg_reference(ref_channels="average")`）默认排除`info["bads"]`中的通道，因此未插值的候选坏导不会把噪声混入平均参考、扩散到全部良导；这一步是无montage分支能够安全继续执行、而不污染步骤3-5的前提，不能省略。**有montage、已成功插值的分支存在一个需要同步修复的现状代码缺陷**：`qc.py:47`把`candidate_bads`原样传给`preprocess_full_recording`的`bad_channels`参数，不区分是否已插值；`preprocess.py:24-26`据此无条件把这些通道写入`info["bads"]`，导致步骤3的平均参考会排除这些**已插值、此刻已是良好数据**的通道，使参考基准少算N-k个通道，系统性偏移全部良导的电位值，静默污染PSD/微状态/Connectivity。迁移时必须修正为：有montage且插值成功后，传入`preprocess_full_recording`的`bad_channels`应为空（或插值后显式清空`info["bads"]`），只有无montage/插值失败分支才保留候选坏导写入`info["bads"]`用于排除平均参考。这是现状代码的真实缺陷，不是文档表述遗漏，迁移时必须一并修复，不能原样搬移`qc.py:47`的调用方式。
3. **滤波**（迁移：notch → bandpass → 平均参考 → 重采样）→ 在步骤2之后执行，输入是步骤2的输出——有montage时是插值后的连续数据，无montage时是未插值、仍带候选坏导标记的连续数据（见步骤2说明）。

**第一阶段montage可用性假设（影响P0自动核准的实际覆盖率，未经统计核实）**：经核查，web-main真实上传路径（`storage_service.py`的`create_eeg_file()` → `metadata_service.extract_metadata()`）**不会**为上传文件生成或补齐标准montage，完全依赖上传文件自身是否携带电极位置信息；`docs/modules/qc_common_data_preparation_requirements.md`把"montage选择/模板匹配"列为**P1需求**，前端状态默认`montage: { mode: "not_set", template: null }`，即产品设计上默认认为用户刚上传的数据**处于未设置montage状态**，需要用户后续手动选择模板匹配。这意味着如果客户不主动完成montage匹配这一步（P1，非本文档讨论的P0自动QC范围内），到达本节自动QC管线时很可能落入"无montage"分支。本文档核查范围内**未找到**第一阶段实际客户数据montage覆盖率的统计或假设（是否默认标准64导、多少比例会主动完成模板匹配），这是一个需要产品/算法团队在实施前补充确认的未知项，不能假设"有montage"是常态——若无montage是常见情况，步骤5-7的ICLabel/SafetyGate在多数上传上会直接落入`AUTO_PASS_BLOCKED`（因步骤5"无montage必然分类失败"），P0自动核准的实际覆盖率可能远低于预期，需要在排期前对这一风险做评估，而不是假定管线在多数场景下都能跑通AUTO_PASS路径。

**这不是一条可以留待"后续观察"的次要风险，而是P0自动QC能否交付其核心价值（自动核准/AUTO_PASS）的前置矛盾，已作为第2节Phase 0b纳入第一阶段架构排期（二选一并写入排期，指定归属人，须在本节实现方案定稿前完成），本处仅记录风险来源，具体决策要求见Phase 0b：(a) 把montage模板匹配（或至少"无自带定位时默认套用标准64导/10-20模板"的兜底逻辑，做法类比`qeeg-64ch-research/io.py:33-34`已有的`make_standard_montage("standard_1005")`按名匹配）从P1提升为P0自动QC的前置依赖；或 (b) 明确承认并书面declare本阶段AUTO_PASS的交付范围**以montage可用性为条件**，产品侧相应调整对外的P0自动QC价值主张。
4. **ICA计算**（算法逻辑现成，extended infomax；迁移时需重构拆分，见1.2节表格说明）→ 输入是步骤3滤波后的连续数据。**有montage且插值成功的分支存在秩缺陷未处理的问题**：插值坏导本身是邻近导联的线性组合（`interpolate_bads`产生的数据不提供独立信息），步骤3的平均参考（`preprocess.py:37`的`set_eeg_reference("average", projection=False)`，直接从数据中减去均值而非以投影方式保留）本身也会再降一阶秩；`qc.py:93`的`ICA(n_components=config.ica_variance_fraction, ...)`用方差比例（浮点数）指定成分数，若不显式声明数据秩，会按满秩假设拟合，可能产出不稳定/退化的成分，静默降低ICLabel分类质量和P0的`AUTO_PASS`/`AUTO_PASS_BLOCKED`判定可信度。**不能用MNE的`rank="info"`自动估计代替显式计算**：`rank="info"`依赖`info["bads"]`和SSP投影记录来推断秩，但步骤2要求有montage插值成功后清空`info["bads"]`，且步骤3的平均参考用`projection=False`直接相减（不记录SSP projector），因此`rank="info"`无法感知插值和平均参考造成的降维，会高估秩、等同于未处理。迁移时必须显式计算并传入实际数据秩（按`原始通道数-插值导联数-1`，其中`-1`对应平均参考降的一阶），并在1.2节表格ICA行标注此约束，不能按原样`n_components=方差比例`直接迁移，也不能依赖`rank="info"`自动兜底。
5. **ICLabel自动分类 + SafetyGate**（算法逻辑现成；迁移时需重构拆分，见1.2节表格说明）→ 依赖步骤4的ICA分解结果。**ICLabel本身依赖电极几何/montage**（需要按通道位置生成topomap才能分类），这一前提与步骤1-2讨论的montage降级路径是同一个约束，不是独立的新问题：`qc.py:105-107`已经用`try/except`把`label_components`因缺montage等原因抛出的异常捕获为`blocked_classification_unavailable`，不会导致管线崩溃，而是走`ica_result["status"] != "completed"`这条已有的阻断路径（见步骤7）。因此无montage记录到达步骤5时**必然分类失败**（不是"可能失败"），直接产出`blocked_classification_unavailable`，与ICA拟合本身（步骤4，不依赖montage，可正常完成）无关；若`mne-icalabel`因其他原因分类失败或排除比例超限，同样直接产出`AUTO_PASS_BLOCKED`，后续步骤仍执行但结果标记为"不可自动核准"。
6. **坏段/坏epoch剔除**（升级为autoreject）→ 输入是步骤5清洗后的连续数据，按epoch粒度筛选，最后一步。
7. **SafetyGate终态判定**：汇总步骤1-6的阻断原因（坏导比例超限/插值不可用/ICA拟合失败/ICLabel分类失败或排除超限/有效epoch数不足），任一命中则整体结论为`AUTO_PASS_BLOCKED`，否则为`AUTO_PASS`。**`AUTO_PASS_BLOCKED`不是单纯的标签，必须有实际的消费限制**：`qc.py`原有语义是"结果仍保留供人工复核，但不得被标注为自动核准"（docstring: "results remain available for review but must not be labelled auto-approved"）。第一阶段落地时必须保留这个约束的实质效果——1.1节全部9个对客开放分析方法（8个现有：PSD/Band Power/ERP/TFR/Multitaper/PAC v1/v2/Connectivity/Reference-CSD，加本文档新增的微状态）的**自动/默认消费路径**不能对`AUTO_PASS_BLOCKED`的产物直接放行产出交付结果，必须先经人工复核确认后才能进入下游分析或对客户交付；仅供人工复核查看的场景（如清洗前后对比视图）不受此限制。若不做这层限制，`AUTO_PASS_BLOCKED`只是一个不影响任何后续行为的标签，SafetyGate作为P0安全机制将失去实际意义。

**SafetyGate结论必须绑定"该方法在Phase 0c选定的消费路径"，不能对全部方法统一读取同一条汇总结论**：上述汇总的"有效epoch数不足"这一阻断原因，来自步骤6物理剔除+重拼接分支的epoch留存统计，只对**实际消费这份重拼接产物**的路径有效。ERP/TFR天然不消费步骤6的重拼接产物（见下文"事件锁定型方法不消费步骤6"说明），走的是自己的标注式`reject_by_annotation`分支，因此必须用另一条结论。但PSD/微状态/Connectivity的消费路径本身在上文（"跨拼接点精度风险"一节）是**二选一、已作为Phase 0c纳入排期**的决策：(a) 消费步骤6物理剔除+重拼接产物（分段对齐拼接点）；(b) 改走事件锁定型方法已使用的标注式分支（消费步骤5输出+`BAD_*`标注）。若某方法最终选择路径(b)，它同样不消费步骤6的重拼接产物，此时不能读取步骤1-6汇总结论，而必须和ERP/TFR用同一条基于标注式分支的结论；只有选择路径(a)的方法才能用步骤1-6汇总结论。**因此SafetyGate结论的选择规则是"看该方法在Phase 0c选定的消费路径"**：Phase 0c要求每个方法（PSD/微状态/Connectivity/Band Power/Multitaper/PAC v1/v2/Reference-CSD）在实施前静态选定(a)或(b)并写入排期，一旦选定即成为该方法固定不变的属性，不是逐次请求可能变化的运行期状态。消费步骤6重拼接产物的方法（选了路径(a)的方法）用步骤1-6汇总结论；消费步骤5输出+标注式分支的方法（ERP/TFR固定如此，或其他方法选了路径(b)）用步骤1-5的阻断原因（坏导比例超限/插值不可用/ICA拟合失败/ICLabel分类失败或排除超限）。**路径(b)的epoch留存统计不能在TaskExecutor门控时预先给出，必须拆成两级门控**：标注式分支本身（步骤6新增分支，见下文说明）只产出`BAD_*`标注、不做epoching，不存在"epoch留存统计"这个中间产物——这份统计只有在消费方法自己按事件时间轴跑完`mne.Epochs(..., reject_by_annotation=True)`之后才存在，而那时方法已经开始执行，TaskExecutor不可能在派发前读到它。因此路径(b)方法的门控必须分两级：第一级在TaskExecutor派发前，只用步骤1-5阻断原因判定（不含epoch留存这一项，可能判定结果是`AUTO_PASS`但仍存在留存不足风险）；第二级在方法自身完成事件锁定epoching之后，若留存epoch数低于阈值，由方法自己产出第二次阻断结论（标记为不可自动核准、转人工复核，不直接对外交付结果），而不是指望一次性的预执行判定覆盖这个原因。`_gate_reasons`（`qc.py:344`）目前只产出一份汇总结论，迁移时需要拆分成路径(a)的步骤1-6单级结论，和路径(b)的步骤1-5预执行结论+方法内epoch留存二级结论，并按"方法→Phase 0c选定路径→对应结论"这张静态查表在TaskExecutor门控时路由，这也是本节表格SafetyGate行"迁移+新增终态聚合层"工作量的一部分。

各步骤输入输出契约：连续数据（Raw）贯穿步骤1-5，仅步骤6把数据切成epoch筛选；筛选后**保留的epoch会被重新拼接回连续数据**（对应`qc.py:54-57`的`RawArray`重建）。这份拼接后的连续数据是`qc.py`现状代码的输出产物，但**不是**PSD/微状态/Connectivity在第一阶段的默认消费输入——它们的实际消费路径由下方"跨拼接点精度风险"约束决定（分段对齐拼接点，或改走标注式分epoch统计），拼接产物本身只用于不要求逐点统计严格性的场景（如清洗前后对比视图的展示）。由于剔除的坏段会造成时间上的不连续（被拼接掉的epoch之间原本有时间间隔），这份连续序列是"剔除坏段后拼接的连续序列"，不是原始时间轴上的连续序列；如果需要在原始记录时间轴上展示（如清洗前后对比视图），必须用`raw-to-cleaned时间映射`（对应`qc.py`的`build_source_time_mapping`/`restore_source_time_axis`）把拼接后的样本点换算回原始记录时间轴，缺口处显式标记为空白而非连续。

**PSD/微状态/Connectivity消费拼接产物均存在跨拼接点的精度风险，不只是展示问题**：物理拼接会在拼接点两侧产生原本不相邻的样本被强行连续的边界。PSD（Welch）/Connectivity若计算窗口跨越拼接点会引入边界频谱泄漏/伪相干；微状态若在拼接后的序列上直接算平均持续时间/转移概率/覆盖率，每个拼接点都会被误判成一次真实的状态转移，静默污染这些时序统计。第一阶段实现这三类方法时，不能直接对整段拼接产物无差别地跑计算，必须二选一：(a) 复用步骤6"判定/应用"拆分后的坏段边界信息，让PSD/Connectivity的分段窗口、微状态的转移序列都在拼接点处断开、不跨界统计，再按段汇总或排除跨界转移；或 (b) 改走事件锁定型方法已使用的标注式分支（消费步骤5输出+`BAD_*`标注，用`reject_by_annotation=True`分epoch后逐epoch计算再汇总）。**两种路径的选择不是留待实现阶段随意决定的开放项，已作为第2节Phase 0c纳入第一阶段排期（三个方法各自二选一并写入排期，指定归属人，须在微状态P0实现方案定稿和Phase C2门控路由代码编写前完成）**，本处只固定"不能跨拼接边界统计"这一约束，对PSD/Connectivity/微状态三者同等适用，具体决策要求见Phase 0c。

**事件锁定型方法（ERP/P300、TFR/ERSP/ITC）不消费步骤6的重拼接产物**：重拼接会抹掉事件标记相对刺激时刻的真实时间位置，ERP/TFR依赖`mne.events_from_annotations`按原始时间轴取epoch（现状见`eeg_core/analysis/erp.py:178,237-248`，该模块目前直接读取原始文件自行滤波/epoching，尚未接入本节的自动QC管线），第一阶段接入自动QC时必须走不同的消费路径：只消费步骤1-5的坏导检测/插值/滤波/ICA/ICLabel清洗结果（这几步保持连续数据、不破坏时间轴）。

**步骤6需要新增一个标注式输出分支，供事件锁定型方法使用**：`qc.py`现有的步骤6（autoreject/坏段剔除）只产出"物理剔除+重拼接"的结果，本身不生成任何标注，所以ERP/TFR路径不能直接复用步骤6的现有实现，必须新增一个并行分支——把步骤6用的坏段判定逻辑（升级后的autoreject epoch级判定）应用在步骤5输出的连续数据上，但判定结果不做物理剔除/重拼接，而是把每个被判定为坏的时间区间转换成`mne.Annotations`（`BAD_*`前缀）写回这份连续数据；ERP/TFR消费这份"带BAD标注、未物理剔除"的连续数据，自己按事件时间轴做`mne.Epochs(..., reject_by_annotation=True)`完成标注驱动的按epoch剔除。这个标注式分支和步骤6原有的物理剔除分支共享同一套坏段判定算法，只是输出形式不同（标注vs物理剔除+重拼接），需要在实现时拆成"判定"与"应用"两个独立函数，供两条消费路径分别复用"判定"部分。**这个分支本身只产出标注、不产出epoch**：因此消费它的方法（ERP/TFR，或Phase 0c选路径(b)的其他方法）的"epoch留存统计"这项SafetyGate阻断原因，无法在标注式分支这一步计算出来，只能等消费方法自己按事件时间轴做`reject_by_annotation=True`分epoch之后才存在，这是步骤7SafetyGate门控要拆成两级判定的直接原因。

**未决风险（需要架构组/算法组在实施前专门核实，不能直接照搬现有顺序）**：现有七步顺序是`qc.py`手写阈值坏导检测算法验证过的顺序（坏导检测在滤波之前）。升级为pyprep RANSAC后，不能假定同样的顺序安全——pyprep的`NoisyChannels`/RANSAC坏导检测对输入数据是否需要预先去线噪/高通滤波，本次核查未能从文档明确证实（pyprep官方文档描述了内部去趋势`do_detrend`开关，但未清楚说明是否要求外部预滤波），需要算法组在实施前专门确认pyprep的前提条件，必要时调整坏导检测步骤相对于滤波步骤的顺序，而不能沿用"仅换算法不改顺序"的假设。autoreject坏段剔除对输入数据顺序的前提条件同样未在本次核查中确认，需一并核实。**autoreject的montage依赖需要与步骤1/步骤5对称处理**：步骤6"局部插值式"修复同样需要电极几何（原理同RANSAC，都是靠通道位置做局部插值），无montage时不能假定能以完整模式运行，须按1.2节表格"坏段/坏epoch剔除"行的说明降级为阈值-only模式；这不是"仅换算法不改顺序"之外的新增开放项，而是与步骤1（pyprep→z-score降级）、步骤5（ICLabel必然分类失败→`blocked_classification_unavailable`）同一约束在步骤6的延伸，实施前需一并确认。**任何重排都必须保持一个不变量，且该不变量只适用于无montage/插值失败分支：候选坏导必须先被写入`info["bads"]`，才能执行步骤3的平均参考**（对应步骤2说明的"平均参考默认排除`info['bads']`中的通道"这一前提）——如果算法组把坏导检测整体后移到平均参考之后，会导致该分支下平均参考不再排除候选坏导，坏导噪声扩散到全部良导，静默污染PSD/微状态/Connectivity的产物。**有montage且插值成功分支不适用此不变量，规则相反**：该分支必须在平均参考执行前清空`info["bads"]`（见步骤2关于`qc.py:47`现状缺陷的说明），任何重排都不能让候选坏导在插值成功后仍残留在`info["bads"]`里进入平均参考，否则会重新引入步骤2指出的"已插值良导被误排除"的bug。若确需重排，必须相应拆分"参考"与"notch/bandpass"两个子步骤，确保上述两条分支相反的先后关系在任何最终顺序里都成立，而不是把整个"坏导检测"和整个"滤波"当作两个不可拆分的原子块简单对调。

### 1.3 超前实现能力（标注，不删除，第一阶段不对外开放）

账户/登录注册、计费钱包/充值/账单、OSS对象存储、配额管理、癫痫工作台（8个API+ML分类器）、波形工作台、后台管理（运营/财务/系统）、教学数据管理、模块实验室（module-lab）、审计服务 —— 全部保留在代码中，产品文档标注为"超前实现，Phase 1 不对外开放"，避免团队误删或误当成待办重新实现。

### 1.4 明确延后到1.x（非第一阶段阻塞项）

SimNIBS电场仿真、GFP/GMD、复杂度指标、Aperiodic谱、SEEG/ECoG专项分析、Spike sorting、Kubernetes编排、复杂RBAC、AI解读。

---

## 2. 架构重构路线图（第一阶段必做）

对应 `task_service.py`、`object_storage_service.py`、`backup_service.py`、`worker/celery_app.py` 现状，按风险从低到高分三段推进，可增量上线（每段都不破坏现有API签名）：

### Phase 0：自动QC执行底座决策（前置项，架构组负责，必须在Phase C2启动前完成）

这不是可以留在"风险与阻塞项"里无限期讨论的旁项，而是与Phase A/B/C并列、纳入第一阶段排期的必做前置决策，对应第5节风险第4条：`worker/celery_app.py`目前是`LocalWorkerApp`占位同步执行，64导以上数据的ICA/pyprep/autoreject耗时在同步占位下极可能触发请求超时（`system_architecture.md`第14节已记录该已知风险）。架构组必须在1.2节自动QC具体实现方案确定之前、Phase C2（自动QC接入执行流）启动之前，二选一并写入排期：(a) 把真实异步任务队列（替换`LocalWorkerApp`）提前到第一阶段，作为P0自动QC的前置依赖；或 (b) 明确保留同步执行架构，但必须为自动QC补充超时上限和进度反馈机制，且要给出64导数据下的实测耗时评估证明同步方式可接受。此决策需要指定归属人和完成日期，缺失该决策，Phase C2的排期估算不成立。

### Phase 0b：montage前置依赖决策（前置项，产品组+算法组联合负责，必须在1.2节自动QC具体实现方案确定之前完成）

与Phase 0同等地位的必做前置决策，对应1.2.1节步骤3之后的montage可用性说明和第5节风险第6条：P0自动QC的核心价值（AUTO_PASS自动核准）在无montage时因ICLabel必然分类失败而无法交付，但montage模板匹配目前在产品需求文档中仍是P1、且真实上传路径不会自动补齐montage。**无montage对Decision 2"成熟库路线"四个组件的影响并不一致，不能笼统说"全部退回手写"**：无montage时步骤1的pyprep RANSAC不可用降级为手写z-score，步骤6的autoreject局部插值式修复同样依赖电极几何、需降级为阈值-only模式（见1.2节表格及1.2.1节步骤6/未决风险说明）——这两项确实退化为手写规则；步骤4的ICA拟合本身不依赖montage，无montage时`ica.fit()`仍能正常完整执行；但**ICA的实际清洗效果依赖ICLabel剔除，无montage时这一步被阻断，ICA拟合出的成分不会被应用到数据上**：`qc.py:105-113`的`blocked_classification_unavailable`分支直接`return`未经处理的原始`raw`，`ica.exclude`赋值和`ica.apply()`（132-134行）只在`label_components`分类成功、走到函数最后的`status="completed"`分支时才会执行——无montage时ICLabel分类失败，函数在105-113行就返回了，`ica.apply()`根本不会被调用。因此无montage时ICA"拟合"这一步确实按成熟库跑完了，但它对最终数据没有任何清洗贡献（既不剔除眼动/心跳/肌电等伪迹成分，也不修改数据），实际净效果等同于跳过ICA这一步。步骤5的ICLabel不是"退化为手写分类兜底"，而是直接分类失败、产出`blocked_classification_unavailable`，整体走向`AUTO_PASS_BLOCKED`——数据被阻断转人工复核，不是被静默地用手写规则处理后当作正常结果交付。因此无montage的实际后果是：ICA拟合本身跑成熟库代码但不产生清洗效果（因ICLabel阻断导致`apply`未执行），坏导检测/坏段剔除退化为手写规则，ICLabel/SafetyGate直接阻断——不是"和升级前现状代码基本等价"（现状代码没有ICA这一步，这里ICA拟合本身仍消耗计算资源但无输出效果，是新增的空转成本），也不是"成熟库路线完全不生效"，而是坏导检测/坏段剔除降级为手写规则、ICA空转无效果、ICLabel/SafetyGate转阻断。产品组+算法组必须在1.2节实现方案定稿前二选一并写入排期：(a) 把montage模板匹配（或默认标准64导/10-20模板兜底）提升为P0自动QC的前置依赖一并排期；或 (b) 书面declare本阶段AUTO_PASS的交付范围以montage可用性为条件，并说明无montage数据的实际处置是"部分组件降级为手写规则+ICLabel阻断转人工复核"，而不是"QC管线整体不生效"。**若选(a)，默认套用标准模板前必须先校验通道名/数量与模板匹配，不匹配则按无montage处理，不能无条件赋位**：`make_standard_montage`+`set_montage(..., on_missing="ignore")`（类比`io.py:33-34`）在通道名不完全匹配标准10-20命名时会静默忽略缺失通道、把能匹配上的通道名赋予对应标准位置，若实际电极物理布局与标准模板不一致（如通道命名恰好撞上标准名称但物理位置不同、或非标准布局用了非标准命名而被`on_missing="ignore"`跳过部分通道却仍判定为"有montage"），RANSAC/ICLabel/autoreject会在错误几何上运行并产出看似正常的`AUTO_PASS`结果，绕过SafetyGate"不可信数据必须阻断"的安全意图，比"直接判定无montage走阻断分支"更危险。因此若选(a)，兜底逻辑必须先做通道名集合/数量与模板的匹配校验，只有校验通过才视为"有montage"进入插值/ICA路径，校验不通过必须按无montage处理（降级路径+`AUTO_PASS_BLOCKED`判定），不能对未经校验的布局默认赋位。此决策需要指定归属人和完成日期，缺失该决策，本节P0自动QC的排期估算和价值主张都不成立。

### Phase 0c：拼接产物消费路径决策（前置项，算法组负责，必须在微状态P0实现与Phase C2门控路由定稿前完成）

与Phase 0/Phase 0b同等地位的必做前置决策，对应1.2.1节"跨拼接点精度风险"一节和第5节风险第5条、第7条：消费步骤6拼接产物的方法在路径选择上——(a) 复用坏段边界信息使窗口/转移序列在拼接点处断开；或(b) 改走事件锁定型方法已使用的标注式分支（消费步骤5输出+`BAD_*`标注）——目前文档只写"留给实现阶段技术评审"，没有指定归属人和截止日期。这个决策不是纯技术细节，它同时决定了两件排期项：涉及连续时序统计的方法（微状态）的实际改造工作量（选(a)要做分段对齐拼接点的改造，选(b)要做标注式分epoch统计的改造，两者代码路径不同）；以及Phase C2的SafetyGate门控路由方式（选(a)读取步骤1-6汇总结论，选(b)读取步骤1-5+标注留存统计的结论，见1.2.1节步骤7说明）。**本决策覆盖1.1节全部9个对客开放方法**（8个现有：PSD/Band Power/ERP/TFR/Multitaper/PAC v1/v2/Connectivity/Reference-CSD，加微状态）：ERP/TFR固定走标注式分支(b)，不需要额外决策；其余7个方法（PSD/微状态/Connectivity，以及此前未被本节讨论覆盖的Band Power/Multitaper/PAC v1/v2/Reference-CSD）均需各自选定(a)或(b)（各方法可选择不同路径，不要求统一）。算法组必须在微状态P0具体实现方案定稿、以及Phase C2门控路由代码开始编写之前，为这7个方法逐一写入排期决策，指定归属人和完成日期。缺失任一方法的该决策，微状态P0工时估算和Phase C2门控路由设计（该方法所在的部分）都不成立。

### Phase A：Registry驱动的工作流模板（分两步，第一阶段末必须完成收敛）

Phase A本身要分两步，第二步是决策5"第一阶段必须重构到registry驱动架构"的实际达标点，不能止步于叠加层：

- **A1（起步，风险最低）**：新建 `backend/services/workflow_registry.py`：加载 `research-modules/registry.json` + 各模块 `manifest.json`，构建 `module_id → module_name` 映射；提供 `build_workflow_templates_from_registry(base_templates)`，把 `lifecycle_status`/`enabled` 叠加到现有 `_BASE_WORKFLOW_TEMPLATES` 上。`task_service.py` 改动仅3行（导入+调用叠加函数）。**此步`_BASE_WORKFLOW_TEMPLATES`仍是权威数据源，registry只是叠加状态字段，尚不构成"registry驱动"，只是迁移的起步动作。**
- **A2（收敛，第一阶段末必须完成）**：把`_BASE_WORKFLOW_TEMPLATES`里的模板定义本身（`id/name/module/outputs/production_status/enabled`等字段）迁入`registry.json`各模块的`manifest.json`，改为`workflow_registry.py`直接从registry构建完整模板列表；`task_service.py`原有的硬编码列表降级为**迁移期只读fallback**（当某模块registry条目缺失时兜底，不再是新增模板的编辑入口），最终状态是新增/修改工作流只需改registry，不需要改`task_service.py`代码。
- 前置阻塞项：`module_contract_service.py` 当前从硬编码外部路径 `D:\QuanLanKnowledgeBase\...` 加载YAML契约，需先迁入工作区或改走registry，否则A2和Phase C都无法干净收尾（Phase B的StorageAdapter抽象与契约加载无关，不受此阻塞）。

### Phase B：StorageAdapter 抽象

- 新建 `backend/storage/base.py`：`ABC StorageAdapter`，7个抽象方法（`put_stream/exists/get_readable/stat/signed_download_url/copy_to_tier/delete`）。
- `backend/storage/local_adapter.py`、`oss_adapter.py`：从`object_storage_service.py`现有的 `if _uses_oss(): ... else: ...` 分支逐条搬移，逻辑不变。
- `object_storage_service.py` 收敛为按 `QLANALYSER_STORAGE_BACKEND` 环境变量路由的薄层，对外函数签名不变。

### Phase C：TaskExecutor分发 + 版本化实体渐进落地

- 新建 `backend/execution/base.py`（`ABC TaskExecutor.execute(...)`）+ `backend/execution/executors/*.py`（每方法一个文件，如`psd.py`包一层`run_psd`）+ `backend/execution/registry.py`（`_REGISTRY`映射 + `get_executor()`）。替代`task_service.py`的if/elif长链，可与旧链并存过渡。
- **数据模型说明（重要更正）**：web-main没有SQLAlchemy/SQL，全部是Pydantic `BaseModel` + JSON `state_store`。因此不涉及SQL migration。但Phase C内部要分两类工作，风险不同，不能笼统标"纯新增/低风险"：

  **C1（模型定义，纯新增，低风险）**：
  - `backend/models/session.py`（`SessionCreate`/`SessionRead`）
  - `backend/models/source_version.py`（含`derived_from_id`血缘链）
  - `backend/models/preprocessing_version.py`（`parameters_sha256`复用现有canonical-hash函数；`PreprocessingVersion`必须显式引用其所属的`source_version_id`，即挂在`SourceVersion`的血缘链下，不是脱离源数据的独立版本序列）
  - `state_store.state_summary()`追加3个新registry名；`EEGFileRead`已有闲置的`session_id`字段可直接启用。
  - 这一层只是定义模型和落盘位置，不改动现有模型/API，可独立先行。

  **C2（接入执行流，中风险，是1.2节"清洗版本冻结/复用"P0能力真正的落地工作）**：
  - `PreprocessingVersion`要真正支撑"冻结/复用"，必须让预处理执行路径（滤波/ICA/坏导检测等自动QC流程）在运行前按**`(source_version_id, parameters_sha256)`组合键**查询是否已有匹配的版本（不能只用`parameters_sha256`单独查询，否则不同录制文件用了相同参数会被误判为可复用同一份清洗产物，静默返回错误数据）、运行后把版本记录关联到`EEGFile`/`AnalysisTask`，即读写现有执行流的关键路径，不是新增文件就能完成。
  - **`AUTO_PASS_BLOCKED`消费限制（1.2.1节步骤7要求的强制项）在此落地**：TaskExecutor分发1.1节全部9个对客开放分析方法（8个现有：PSD/Band Power/ERP/TFR/Multitaper/PAC v1/v2/Connectivity/Reference-CSD，加微状态）的执行请求时，必须先读取该数据对应的`PreprocessingVersion`/QC结果的SafetyGate结论，若为`AUTO_PASS_BLOCKED`则拒绝走自动/默认交付路径（返回需人工复核的状态，而不是静默执行分析并交付结果）；这是TaskExecutor改造和1.2节自动QC能否形成闭环安全机制的必要条件，不是可选项。**存在两条SafetyGate结论，路由依据是该方法在Phase 0c静态选定的消费路径**（见1.2.1节步骤7说明）：Phase 0c要求每个方法在实施前选定(a)或(b)，一旦选定即为该方法固定属性，不随每次请求变化。消费步骤6重拼接产物的方法（路径(a)）用步骤1-6汇总结论，TaskExecutor派发前可一次性判定完毕。消费步骤5输出+标注式分支的方法（路径(b)：ERP/TFR固定如此，其余方法若在Phase 0c选择标注式路径也如此）**门控必须拆成两级**：派发前只能用步骤1-5阻断原因做第一级判定（不含epoch留存统计，因为标注式分支只产出`BAD_*`标注、不做epoching，这份统计要等方法自己跑完事件锁定epoching才存在，派发前读不到）；方法执行内部完成`mne.Epochs(..., reject_by_annotation=True)`后，若留存epoch数不足，由方法自身产出第二级阻断结论，标记结果为不可自动核准、转人工复核，不直接对外交付。Phase 0c已覆盖全部9个对客开放方法的消费路径决策（不只是PSD/微状态/Connectivity三者），TaskExecutor门控路由的前置依赖是这9个方法各自的路径决策都已完成，路由实现按"方法→Phase 0c选定路径→对应结论（路径(a)为单级，路径(b)为两级）"这张静态查表即可，不需要每次请求携带路径信息。当前全部9个方法均尚未接入自动QC管线（见1.1节表格说明，不是只有`erp.py`如此），接入时必须同步接入这一层门控（路径(b)方法还需同步接入方法内的第二级门控），不能只接数据、不接门控判定。
  - 这部分需要与Phase C的TaskExecutor改造、以及1.2节自动QC实施同步设计，工作量和风险应按"中风险，涉及现有执行路径改动"排期，不要按C1的"低风险"一并估算。
  - 排期建议：C1可与Phase A并行先行；C2应安排在1.2节自动QC具体实现方案确定之后、且Phase 0（自动QC执行底座决策）完成之后，作为该实现的一部分交付，而非独立的"纯新增"任务——C2要接入的预处理执行路径（滤波/ICA/坏导检测）正是Phase 0要决策的执行底座（同步/异步）所承载的路径，底座未定则C2的接入方式和风险评估都不成立。

---

## 3. 微状态迁移实施清单（第一阶段，P0）

- 直接复制 `qeeg-64ch-research/src/qlanalyser_eeg64/microstates.py`（核心函数`compute_microstates`，KMeans峰值拟合+全序列反投影，Pascual-Marqui方法）。**该函数当前对输入序列做全序列连续反投影和转移统计，未按段/事件边界断开**——这与1.2.1节"微状态不能对整段拼接产物无差别地跑计算，必须分段对齐拼接点或改走标注式分epoch统计"的强制约束直接冲突。迁移时不能是纯粹的原样复制：`compute_microstates`需要改造为接受分段边界（或`BAD_*`标注）输入，在计算持续时间/转移概率/覆盖率时跳过跨边界的转移，这部分改造属于迁移工作量的一部分，不是"直接复制"就能满足1.2.1节的约束。**具体改造成哪一种输入形式（分段边界还是`BAD_*`标注）取决于Phase 0c为微状态选定的消费路径(a)/(b)，该决策未定稿前，本条目的工作量只能按"两种改造方式中较大者"估算区间，不能定点估算。**
- **回归基线口径必须相应调整**：下方提到的`analysis_summary.json`基线是在`qc.py:54-57`产出的拼接连续数据上、用未改造的全序列版本算出的，只能用于验证"改造前的核心算法逐点计算逻辑迁移无误"（如GFP峰值检测、KMeans拟合本身的数值一致性），**不能作为改造后（分段感知）版本的通过标准**；分段感知版本需要另建一套基于同一份37.5MB真实数据、但显式标注了段边界的基线，用于验证跨边界转移已被正确排除。**该基线还与1.2.1节步骤2要求的`qc.py:47`平均参考bug修复存在口径冲突，必须先核实再使用**：若这份37.5MB基线数据存在montage且有被插值的坏导，那么基线本身是由含该bug的旧管线产出的——旧管线错误地把已插值的良导排除出平均参考，参考基准本身就是错的。平均参考是线性变换，一旦按步骤2的要求修复该bug，所有通道的电位值都会随之改变，GFP（`data.std(axis=0)`）和地图反投影的**逐点数值本身也会变**，不只是分段感知改造才会导致数值偏离。因此必须先核实这份基线数据是否含montage+插值坏导：若含，逐点数值一致性核对必须用"修复bug后的管线重新生成"的基线，禁止拿旧基线的逐点数值做等值判据，否则会导致工程师误判迁移出错、或反过来篡改新代码去对齐旧基线，从而静默回退步骤2要求修复的那个bug；若不含（数据本身没有需要插值的坏导），旧基线在这一点上不受影响，可按原计划使用。
- 唯一内部依赖是从`gfp.py`复制的4行`_normalize_maps`辅助函数，一并内联，不引入gfp.py整体依赖（因为GFP/GMD本身延后1.x）。经二次核查确认：`compute_microstates`的GFP计算（`data.std(axis=0)`）和GFP峰值检测（`scipy.signal.find_peaks`）均在`microstates.py`内部独立实现，未调用`gfp.py`的任何峰值逻辑，`gfp.py`唯一被引用的符号就是`_normalize_maps`（`microstates.py:13`），迁移范围与风险评估成立。
- 无新增第三方依赖（sklearn已是web-main现有依赖）。
- 通过现有参数schema模式接入，复用现有`reproducibility.py`契约记录随机种子（`random_state=42`固定，理论上完全可复现）。
- 复杂的matplotlib/HTML可视化层（`expanded_report.py`，13+绘图函数）**不迁移**，第一阶段按web-main自己的报告架构重新设计输出，避免引入旧的可视化耦合。
- 现有基线：`qeeg-64ch-research/results/v0.2.11-complete-microstate-catalog/analysis_summary.json`（37.5MB真实数据全流程结果）。**用途范围与上方第2条一致，这里不重复放宽**：只用于核对逐点计算逻辑（GFP峰值检测、KMeans拟合、地图反投影）迁移后数值不变，不是端到端验收标准；端到端验收（含跨段转移是否被正确排除）必须用另建的段边界标注基线。
- 现有测试（26个，4个文件）均为合成序列（如`list("ABABAB")`），迁移后建议补两组回归测试：一组基于上述真实数据基线核对逐点计算数值一致性，另一组基于新建的段边界标注基线核对分段感知改造是否正确排除跨边界转移。

---

## 4. 命名与契约对齐

- 现有`workflow_id`是随意snake_case（`resting_psd`/`epilepsy_ml_xgboost`），不符合需求文档`domain.method.algorithm@version`规范（如`scalp_eeg.psd.welch_resting@v0.1`）。第一阶段随Registry驱动改造（第2节Phase A）一并做命名映射表，不要求立刻重命名现有ID（避免破坏现有产物路径），但新增方法（微状态、升级后的自动QC）一律用新规范命名。
- `research-modules/contracts/`的9个JSON Schema契约（module-manifest/registry/result-envelope/eeg-source/channel-montage/preprocessing-provenance/artifact-manifest/lifecycle-safety/adapter-binding）第一阶段起对新增能力（微状态、自动QC）强制校验落地，存量方法逐步补齐，不作为第一阶段阻塞项。

---

## 5. 风险与阻塞项

1. `module_contract_service.py`硬编码外部KB路径 —— 阻塞Phase A2和Phase C干净收尾（契约加载与Phase B的StorageAdapter抽象无关，不阻塞Phase B），需先处理。
2. `mne-icalabel`当前环境未安装（可选依赖），升级为必装后需要验证安装/CI/生产环境的可用性（依赖较重，含预训练分类器权重）。
3. pyprep/autoreject是新引入的依赖，需做兼容性和性能验证（尤其是64导以上数据的运行耗时，可能影响v0.1同步执行架构下的请求超时）。
4. **第一阶段P0自动QC的执行底座决策**：`worker/celery_app.py`目前是`LocalWorkerApp`占位同步执行，64导以上数据的ICA/pyprep/autoreject耗时在同步占位下极可能触发请求超时（`system_architecture.md`第14节已记录该已知风险），导致P0自动QC实际不可交付。这不是留在本节的开放评估，已作为第2节Phase 0纳入第一阶段架构排期（二选一并写入排期，指定归属人，须在Phase C2启动前完成），本条仅记录风险来源，具体决策要求见Phase 0。
5. 步骤6物理拼接产物供PSD/微状态/Connectivity消费时存在跨拼接点的边界效应（PSD/Connectivity表现为频谱泄漏/伪相干，微状态表现为虚假状态转移污染持续时间/转移概率/覆盖率统计），具体偏差幅度本次核查未实测，需算法组在实现前用真实数据评估是否需要强制走分段对齐拼接点或标注式分epoch求平均/统计的路径（见1.2.1节末尾说明），不能默认忽略，三类方法同等适用。
6. **P0自动QC的AUTO_PASS依赖P1的montage匹配，且无montage对成熟库路线各组件的影响并不一致**：无montage时ICLabel（步骤5）必然分类失败，直接导致`AUTO_PASS_BLOCKED`（阻断转人工复核，不是手写兜底）；pyprep（步骤1）降级为手写z-score、autoreject局部插值修复（步骤6）降级为阈值-only，这两项确实退化为手写规则；ICA拟合（步骤4）本身不依赖montage仍会正常执行，但因ICLabel阻断导致`ica.apply()`（`qc.py:132-134`）不会被调用（`blocked_classification_unavailable`分支在105-113行就直接返回未处理的原始数据），ICA拟合对最终数据没有清洗效果，是空转。即Decision 2的"成熟库路线"对无montage数据是"两项降级为手写规则+ICA空转无效果+ICLabel/SafetyGate转阻断"，不是整体不生效，但ICA也不是"正常发挥成熟库效果"，不只是AUTO_PASS覆盖率下降。montage模板匹配目前只是P1需求且真实上传路径不会自动补齐，第一阶段客户数据实际montage覆盖率本次核查未找到统计。这不是留在本节的开放评估，已作为第2节Phase 0b纳入第一阶段排期（二选一并写入排期，指定归属人，须在1.2节实现方案定稿前完成），本条仅记录风险来源，具体决策要求见Phase 0b。
7. **消费拼接产物的路径(a)/(b)未定稿会悬置微状态P0工时和Phase C2门控路由设计**：两条路径对应不同的代码改造方式（分段对齐拼接点 vs 标注式分epoch统计）和不同的SafetyGate结论读取方式（步骤1-6汇总 vs 步骤1-5+标注留存统计），只要该决策未定，第3节微状态改造工时和Phase C2门控路由代码（覆盖全部9个对客开放方法）都无法定点估算。这不是留在本节的开放评估，已作为第2节Phase 0c纳入第一阶段排期（7个方法——PSD/微状态/Connectivity/Band Power/Multitaper/PAC v1/v2/Reference-CSD——各自二选一并写入排期，指定归属人，须在微状态P0实现方案定稿和Phase C2门控路由代码编写前完成；ERP/TFR固定走标注式分支，无需此决策），本条仅记录风险来源，具体决策要求见Phase 0c。

## 6. 明确不做的事（本文档产出，非代码变更）

- 本文档产出阶段（撰写本路线图）不删除或重写任何现有代码，所有代码事实均来自只读核查——**这条约束的对象是"写文档"这个动作本身，不是第一阶段实施范围**：决策5要求的架构重构（Phase A2改写`task_service.py`、Phase B改写`object_storage_service.py`）、1.2.1节要求的`qc.py:47`平均参考排除bug修复、Phase C2要求的`erp.py`等接入SafetyGate门控，这些第一阶段实施工作本身就包含对现有代码的重写/修改，不受本条约束。
- 不把GFP/GMD、复杂度指标、Aperiodic谱、SimNIBS、SEEG/ECoG、Spike纳入第一阶段范围。
- 不把超前实现的账户/计费/OSS等功能从代码中移除（保留在代码里，标注不对外开放，不是"不修改相关代码"）。
- 本文档撰写阶段不修改`pc-qlanalyser`（只读参考）。

## 7. 证据来源说明

本文档所有代码事实均来自对以下路径的只读核查，未执行任何写操作：

- `qlanalyser-workspace/README.md`、`AGENTS.md`（工作区角色与红线规则）
- `projects/web-main/backend/services/task_service.py`、`object_storage_service.py`、`backup_service.py`、`worker/celery_app.py`
- `projects/web-main/docs/architecture/system_architecture.md`、`docs/product/product_requirements_freeze.md`、`docs/product/module_lifecycle_matrix.md`
- `projects/qeeg-64ch-research/pyproject.toml`、`src/qlanalyser_eeg64/{microstates,preprocess,qc,gfp,io}.py`、`results/v0.2.11-complete-microstate-catalog/analysis_summary.json`
- `projects/pc-qlanalyser/src/{qeeg_algorithm-main/qeeg/preprocessing.py,models.py,Filter.py,PreviewandRejection.py,Data_Info.py}`
- `projects/research-modules/registry.json`、`contracts/*.schema.json`、`modules/*/manifest.json`
