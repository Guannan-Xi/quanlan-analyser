# QLanalyser 完整审核+优化 — 长任务计划

**开始日期:** 2026-07-02  
**目标:** 上线标准（P0=0, P1≤2, E2E 全门控通过）  
**测试数据:** `D:\Quanlan\Data\HE脑电\HE脑电\HE-105.edf`  
**模型:** DeepSeek v4 Flash（编排+修改）、GLM-5.2（主审）、DeepSeek v4-pro（副审）、Grok（红队）、Gemini（科学核验）  
**收敛门:** 标记 `QNACR_NFOLD_INCOMPLETE`（无 GPT-5.5），最终接受需后续会话

---

## 阶段划分

### Phase 0 — 多模型并行对抗评审（当前阶段）
4 个模型独立审阅，取并集：

| 模型 | 审阅范围 | 状态 |
|------|---------|------|
| GLM-5.2 | 前端 app.js 全量 + 后端 epilepsy_workbench.py | ⏳ |
| DeepSeek v4-pro | 后端 16 个 API 路由 + 数据完整性 | ⏳ |
| Grok-420-fast | 安全审计：认证、XSS、注入、路径遍历 | ⏳ |
| Gemini-3.5-flash | 科学边界措辞 + EEG 领域合规性 | ⏳ |

### Phase 1 — 修复（P0 + P1）
收集四模型并集，按 P0→P1 优先级修复

### Phase 2 — HE-105.edf 全管道验证
上传 → 数据准备 → PSD → 癫痫 ML → 报告 → 验证结果页面

### Phase 3 — 非医用边界+副本治理
全端禁用词扫描 + DeepSeek 中文措辞门控

### Phase 4 — E2E 门控
`acceptance_edf_upload_to_results_ui_only.mjs` + `validate_epilepsy_cloud_trial_v0_1_release_gate.mjs`

### Phase 5 — 缺陷回流 + 收据
`recurring_defect_patterns.md` 更新 + QNACR 收据 + Feishu 通知草稿
