# WaveformWorkbench 连续性修复回执

日期：2026-06-28  
目标页面：`http://127.0.0.1:4174/waveform-workbench.html?teaching_demo=auto&api=http://127.0.0.1:8001/api&v=e2e`

## 结论

本轮已修复用户反馈的“数据看起来不连续”的主要交互根因：前端不再把旧窗口波形重新映射到新时间窗。窗口切换时，如果新时间窗尚未读取完成，页面会显示明确的读取状态，而不是用旧数据伪装连续。

## 已改内容

1. 连续性数据层：
   - 新增 `windowCache`，保存真实读取到的时间窗 chunk。
   - 当前窗口只绘制缓存中真实落在该时间范围内的采样点。
   - 移除旧的 `fallbackWindowData()` 视觉策略。
   - `usesRemappedFallback` 固定为 `false` 并纳入 E2E。

2. 教学数据稳定性：
   - 自动教学加载改为幂等入口。
   - 如果后端教学接口超时，自动使用 60 秒本地连续合成 EEG，避免空工作台。
   - 如果后端返回的旧 `qc_preview_task` 不是从 0 秒开始，则丢弃并重新生成首页窗口。

3. 读片可理解性：
   - 新增全局 overview strip，显示全程、当前窗口、已加载范围、事件和草稿覆盖。
   - 新增事件显示模式：简洁 / 详细 / 隐藏。
   - 默认事件线降噪，减少竖线把波形“切碎”的错觉。
   - 加入明确 loading overlay：不会用旧波形伪装新时间窗。

4. 文案：
   - 页面标题改为“脑电波形与数据准备工作台”。
   - 副标题改为客户可理解的连续浏览和草稿写入口径。

## 验证结果

验证产物：

- `work/release_evidence/20260628-waveform-workbench-continuity-fix/waveform_workbench_e2e_result.json`
- `work/release_evidence/20260628-waveform-workbench-continuity-fix/01_initial_loaded.png`
- `work/release_evidence/20260628-waveform-workbench-continuity-fix/02_after_wheel_pan.png`
- `work/release_evidence/20260628-waveform-workbench-continuity-fix/03_after_ctrl_zoom.png`
- `work/release_evidence/20260628-waveform-workbench-continuity-fix/04_after_write_mode_draft.png`
- `work/release_evidence/20260628-waveform-workbench-continuity-fix/04b_after_epoch_selection.png`
- `work/release_evidence/20260628-waveform-workbench-continuity-fix/05_after_scroll_persistence.png`

通过项：25 / 25。

新增连续性检查：

- `T-CONT-01-initial-window-uses-real-cache`
- `T-CONT-02-no-old-payload-remap-while-panning`
- `T-CONT-03-pan-window-real-cache-or-explicit-loading`
- `T-CONT-05-overview-visible`
- `T-CONT-06-event-display-toggle`

语法和编码：

- `node --check frontend/waveform-workbench.js` passed
- `node --check scripts/e2e_waveform_workbench_module.mjs` passed
- UTF-8/mojibake scan passed

## 剩余建议

1. 后端仍是 QC preview 窗口任务模型，长 EEG 的高性能连续浏览最终应建设专用 waveform chunk API。
2. Browse 模式未来可支持 60/300 秒概览；当前仍受后端 30 秒 preview 上限约束。
3. 事件密集数据建议后续加入事件密度聚合和 hover tooltip。
4. 右侧操作区还可以继续按“当前选择 / 建议动作 / 草稿历史 / 确认准备”重排。

