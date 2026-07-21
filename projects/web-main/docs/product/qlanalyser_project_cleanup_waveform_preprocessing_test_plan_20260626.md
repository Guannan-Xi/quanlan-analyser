# QLanalyser 项目清洁、波形操作与预处理同屏测试验证文档

日期：2026-06-26
依赖需求：`docs/product/qlanalyser_project_cleanup_waveform_preprocessing_requirements_20260626.md`
依赖设计：`docs/product/qlanalyser_project_cleanup_waveform_preprocessing_design_20260626.md`

## 1. 测试原则

1. 只通过聊天确认不算通过。
2. 静态合同、浏览器点击、后端 API、截图和证据包必须形成闭环。
3. 所有客户可见中文要做 mojibake 检查。
4. 波形必须检查 canvas 非空和交互后的像素/状态变化。
5. 预览滤波必须确认来自后端 `filter_preview.json` 或明确标记为不可用。
6. 合成 EDF 可用于端到端验证，但不能替代真实研究队列科学有效性。

## 2. 静态检查

脚本：`scripts/acceptance_project_cleanup_waveform_preprocessing_static.mjs`

必须检查：

1. 需求/设计/UI/测试文档存在。
2. 执行包存在。
3. `frontend/index.html` 存在波形工具按钮：
   - `#eegPrevBtn`
   - `#eegZoomOutBtn`
   - `#eegZoomInBtn`
   - `#eegNextBtn`
   - `#eegResetBtn`
   - `#loadEegBtn`
4. 存在预览滤波控件：
   - `#eegFilterPreviewToggle`
   - `#presetPrepLfreq`
   - `#presetPrepHfreq`
   - `#presetPrepNotch`
5. 存在参考设置控件：
   - `#presetPrepReference`
   - `#presetPrepReferenceChannels`
   - `#presetPrepBipolarPairs`
6. 存在坏道草稿操作：
   - `data-ia-action="mark-bad-channel"`
   - `data-ia-action="restore-bad-channel"`
7. `runQcPreviewFromUi()` 发送 `preview` 和 `filter_preview` 参数。
8. `renderEegPreviewMetadata()` 不再生成 `QC 任务`、`结果文件`、`状态 可继续准备` 芯片。
9. `filteredWorkspaceProjects()` 默认隐藏内部/验收/自动 pilot 项目。
10. CSD 卡片文案不再混用“参考方案”，必须显示“CSD 电流源密度计算”。

通过标准：所有检查 `passed=true`，错误数为 0。

## 3. 浏览器 E2E

脚本：`scripts/acceptance_project_cleanup_waveform_preprocessing_e2e.mjs`

目标 URL：

`http://127.0.0.1:4174/?api=http://127.0.0.1:8001/api`

前置：

1. 后端 `8001` 可访问。
2. 前端 `4174` 可访问。
3. 若无真实项目，使用教学模式或上传合成 EDF 创建一条可测路径。

检查点：

1. 项目管理默认列表不显示内部项目关键词。
2. “显示内部/归档项目”开关存在，开启后列表数量或内容变化。
3. 教学模式只加载一个示例项目和一个示例数据。
4. 点击数据行后进入数据准备页面。
5. 波形 canvas 非空，像素检查通过。
6. 点击前后/缩放/复位按钮后：
   - 起点或窗口标签变化；
   - 触发预览刷新；
   - canvas 仍非空。
7. 调整增益和通道数后：
   - label 变化；
   - canvas 重绘。
8. 开启预览滤波并刷新：
   - 页面显示“预览滤波”；
   - 页面显示“不改写原始数据”；
   - 后端任务 artifacts 包含 filter preview。
9. 标记坏道：
   - 当前修改记录增加坏道修改。
   - 恢复坏道后记录显示恢复。
10. 预处理参数与波形在同一 viewport 或相邻区域可见。
11. 底部不再出现重复主按钮区。
12. 分析方法卡片仍可点击并触发真实 `/api/tasks`。

截图证据：

1. `project_management_default.png`
2. `project_management_internal_toggle.png`
3. `waveform_preprocessing_workbench.png`
4. `waveform_filter_preview.png`
5. `bad_channel_reversible.png`
6. `mobile_waveform_preprocessing.png`

通过标准：检查项全部通过，截图存在，P0=0。

## 4. 后端 API smoke

复用或新增最小 smoke：

1. GET `/api/projects`
2. POST `/api/tasks` module=`qc`, workflow=`qc_waveform_preview`
3. GET `/api/tasks/{task_id}/artifacts`
4. 下载 `waveform_preview.json`
5. 下载 `filter_preview.json`

检查：

1. task completed。
2. `waveform_preview.json` 包含 channels、times_sec、data_uv、unit、sfreq_display。
3. `filter_preview.json` 包含 `filter_preview_only=true`。
4. `parameters.json` 记录 preview 和 filter_preview。

## 5. DeepSeek 审阅

路径：

1. 路由检查：`work/release_evidence/07-full-product-e2e-pdca/14_waveform_preprocessing_project_cleanup/04_deepseek/deepseek_route_check_20260626.json`
2. 审阅提示：`work/release_evidence/07-full-product-e2e-pdca/14_waveform_preprocessing_project_cleanup/04_deepseek/researcher_logic_review_prompt.md`
3. 审阅结果：`work/release_evidence/07-full-product-e2e-pdca/14_waveform_preprocessing_project_cleanup/04_deepseek/researcher_logic_review.md`
4. 采纳记录：`work/release_evidence/07-full-product-e2e-pdca/14_waveform_preprocessing_project_cleanup/04_deepseek/researcher_logic_review_adoption.json`

审阅问题：

1. 项目管理默认隐藏内部项目是否符合科研人员习惯？
2. 波形预览信息删减是否会损失必要判断依据？
3. 预处理同屏流程是否符合 EEG 研究工作流？
4. 重参考和 CSD 边界是否清楚？
5. 中文文案是否像客户界面，而不是开发者界面？

通过标准：

1. DeepSeek route-check 可用；若不可用，必须保存失败证据。
2. Codex/GPT-5.5 只采纳可验证、符合产品边界的意见。
3. 采纳/不采纳原因写入 JSON。

## 6. UI 视觉审查

使用知识库规则：

1. `B2B_SCIENTIFIC_DASHBOARD_SCREENSHOT_AUDIT_GATE`
2. `QLANALYSER_DASHBOARD_REFERENCE_SELECTION`
3. `Aesthetic Review v3`
4. `UX_STATE_COVERAGE_GATE`

最低检查：

1. 默认真实数据态。
2. 高密度项目列表态。
3. 空项目态。
4. 波形加载中。
5. 波形加载失败。
6. 波形加载成功。
7. 预览滤波成功。
8. 坏道标记/恢复。
9. 720px 窄屏。
10. 页面上下滚动，无关键操作被折叠到不可见区。

阻断项：

1. 波形与预处理无法同屏或相邻可见。
2. 项目管理仍显示大量内部项目。
3. 文案仍有 beta、preview method、task runner 等开发词。
4. 客户界面出现乱码。
5. CSD 被描述为参考方案或源定位。
6. 预览滤波暗示改写原始数据。

## 7. 最终验收包

生成：

`work/release_evidence/07-full-product-e2e-pdca/14_waveform_preprocessing_project_cleanup/acceptance_packet/project_cleanup_waveform_preprocessing_acceptance_packet_20260626.json`

必须包含：

1. `route_decision`
2. `execution_packets`
3. `executor_evidence`
4. `targeted_or_full_e2e`
5. `page_visual_review`
6. `deepseek_review`
7. `gpt55_acceptance`
8. `final_receipt`
9. `next_real_artifact`
10. `route_chain`
11. `model_lane`
12. `headroom_savings`
13. `pdca`
14. `blockers`
