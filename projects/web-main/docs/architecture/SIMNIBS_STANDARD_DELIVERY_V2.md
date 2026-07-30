# 标准化 SimNIBS 仿真服务交付架构 v2

## 目标

同一套交付系统支持 tES、时间干涉刺激（TI）、TMS、方案比较、逆向优化和组分析。参考论文用于确定分析方法和图表要求，不作为客户报告的项目身份。

## 三层架构

1. **客户报告层**：五段式 HTML/PDF，依次呈现主要结论、模型与方案、模拟结果、结果解读、方法与交付。
2. **发表成果层**：每张图均绑定结论、PNG、SVG/PDF 和源数据；区域统计使用结构化指标定义。
3. **数据追溯层**：项目、对象、条件、ROI、指标、质控、限制和交付文件均进入 `simnibs.delivery.v2` 数据契约。

## 代码边界

- `scripts/simnibs_delivery/contract.py`：通用数据契约和跨模块约束。
- `scripts/simnibs_delivery/modules.py`：TI、tES、TMS 专用字段验证。
- `scripts/simnibs_delivery/render.py`：不依赖仿真类型的客户报告渲染器。
- `scripts/build_standard_simnibs_delivery.py`：通用构建入口，生成 HTML、PDF 和标准清单。
- `scripts/adapt_ernie_ti_example_to_standard.py`：现有 ernie TI 案例适配器，仅负责把旧结果转换为 v2。
- `frontend/assets/simnibs-delivery-v2.schema.json`：供前端、服务端和外部工具使用的 JSON Schema。

## 核心契约

核心层只识别以下对象：

- `project`：项目身份、研究问题和交付状态。
- `subject`：MRI/头模型来源。
- `targets`：一个或多个靶区、对照区和非靶区。
- `protocol.conditions`：一个或多个刺激条件及通道。
- `results`：结论、指标定义、ROI 统计和方案比较。
- `quality_control`：已执行检查、状态、证据和未评估内容。
- `figures`：图件类别、结论、图像和源数据。
- `artifacts`：客户可见交付文件。
- `modules`：仿真类型专有字段。

## 模块规则

### 时间干涉刺激

记录主指标、补充指标、两个载波频率、差频和方向来源。差频必须等于两个载波频率之差。

### tES

记录主要电场分量（总场、法向或切向）、电流单位和场强单位。电极与电流配置仍通过通用 `protocol.conditions` 提供。

### TMS

记录线圈型号、主要场指标、单位和线圈位姿。线圈中心与方向必须为三维数值向量。

## 图件规范

图件按科学问题分为 anatomy、protocol、field、quantitative、localization 和 robustness。报告按类别自动排版，不依赖固定图号。每张图必须包含：

- 一句可以独立阅读的标题；
- 一句结果性图注；
- PNG；
- 可用时提供 SVG/PDF；
- 支撑图件的 CSV、NIfTI、HDF5 或其他机器可读数据。

## 状态与质量门控

- `ready`：所有预先声明的硬门控通过，且没有阻断发表的缺失项。
- `draft`：计算和交付可供内部或客户预览，但仍有待确认输入或稳健性分析。
- `blocked`：输入、模型、求解或验证存在阻断问题，报告不得给出方案推荐。

未执行的敏感性分析必须写入 `quality_control.limitations`，不能用笼统的“结果可靠”替代。

## 当前迁移状态

ernie TI 案例已迁移到 v2，并用于验证通用报告、TI 模块、图件加载、移动端布局和 PDF 输出。原始 Violante 参考仍保留在方法来源中，但不再作为报告标题或项目定位。
