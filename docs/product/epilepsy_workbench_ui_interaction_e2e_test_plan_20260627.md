# 癫痫工作台 UI/交互重构测试文档

版本：2026-06-27
目标：验证实验室癫痫工作台第一阶段 EEG 波形交互和复核安全。

## 1. 测试环境

- 前端：`http://127.0.0.1:4174`
- 后端：`http://127.0.0.1:8001/api`
- 页面：`/epilepsy-workbench.html?mode=ml_epoch_classifier&renderer=timechart&task=<task_id>`
- 数据：`epilepsy_ml_demo_source_channels.edf`

## 2. 静态检查

1. `node --check frontend/epilepsy-workbench.js`
2. `node --check scripts/e2e_epilepsy_timechart_lab.mjs`
3. 三份文档 UTF-8 readback，确认中文未乱码。

## 3. API 合同回归

复用：

```text
scripts/acceptance_epilepsy_workbench_api_contract.py
```

关键断言：

- EDF fixture ready。
- epilepsy_ml_xgboost task completed。
- waveform raw window returned。
- waveform filter window returned。
- export review session includes reviewed Stage_Code。

## 4. UI E2E

扩展 `scripts/e2e_epilepsy_timechart_lab.mjs`：

### 4.1 自然 TimeChart 路径

1. 打开实验页。
2. 等待候选事件出现。
3. 确认 TimeChart experimental 选中。
4. 候选事件自动加载或点击后加载波形。
5. 断言状态条显示窗口、事件、滤波、增益、模式。
6. 断言 mini map 存在当前窗口和事件块。
7. wheel 缩放后窗口 duration 变化。
8. drag 后 startSec 变化。
9. ArrowRight 后 startSec 变化。
10. 点击 SVG current 后 SVG 仍可见。

### 4.2 强制 fallback 路径

阻断 d3/timechart CDN：

1. 页面仍加载。
2. TimeChart 失败后 SVG fallback 可见。
3. 无白屏。
4. console error 只允许 expected blocked resource。

### 4.3 复核模式安全

1. 默认 browse mode。
2. browse mode 下 Shift+2 不改变 localStorage 的 epochOverrides。
3. 点击 Correction mode。
4. Shift+2 或按钮修改 Stage_Code。
5. localStorage 出现 `set_stage` action。
6. Stage_Code DOM 仍只出现 normal/seizure 离散类。

## 5. 性能预算

| 项目 | 目标 | 阈值 |
|---|---:|---:|
| waveform-window raw/filter | < 500 ms | < 2000 ms |
| wheel/drag debounce 后请求 | 单次最终请求 | 不连续刷屏 |
| TimeChart 渲染 | < 1000 ms | < 2000 ms |
| SVG fallback | 可见 | 不白屏 |

## 6. 截图证据

保存到：

```text
work/release_evidence/epilepsy_source_workbench_replica_acceptance/timechart_lab_20260627/
```

至少包含：

- `01_loaded.png`
- `02_timechart_or_fallback.png`
- `03_svg_current.png`
- `04_interaction_zoom_pan.png`
- `05_correction_mode.png`

## 7. 失败处理

任何失败需要写入：

```json
{
  "status": "failed",
  "error": "...",
  "screenshots": {},
  "checks": {}
}
```

不得用“脚本通过”替代视觉检查；截图必须可读、非空。

## 8. Stage_Code FSM 测试

必须新增 `stage_code_fsm.json`，至少覆盖：

1. 浏览模式下 Shift+1 / Shift+2 不产生 `set_stage` action。
2. Correction mode 下 Shift+1 / Shift+2 才产生 `set_stage` action。
3. Seizure / Normal 按钮在浏览模式 disabled，在 Correction mode enabled。
4. 非 enum 值写入被拒绝或回滚。
5. source Stage_Code 相同值写入时不产生多余 override，但可记录合法复核动作。
6. 导出中的 `reviewed_epoch_scores.Stage_Code` 只出现 `0` 或 `1`。
7. DOM 中 Stage_Code 只出现 `.normal` / `.seizure` 离散类，不出现连续 Stage_Code 曲线。

## 9. 边界扫描测试

每次 E2E 后扫描页面文本、导出 manifest、review session JSON：

- 不得出现诊断、确诊、治疗、临床决策等医疗承诺。
- 必须出现非医疗科研筛查/候选复核边界。
- 不得出现 07 主工作台入口或主干集成开关。
- 不得出现 Band Power / PSD 混用字段。
- 不得改写 router / Headroom / gateway / IPC 配置。

## 10. 性能与证据索引

P0 当前脚本记录单次 `waveform_window_response_ms` 和交互截图。

P1 需要新增：

- `performance_p95.json`：raw/filter 各 30 次窗口读取，记录 min/p50/p95/p99/max。
- `browser_smoke.json`：页面加载、TimeChart、SVG fallback、键鼠交互、导出路径。
- `non_medical_snapshot.json`：页面可见文本和导出文本边界扫描结果。
- dated evidence folder，并在 `latest_final_verdict.json` 写入索引。
