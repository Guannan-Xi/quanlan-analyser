# QuanLan Analyser Workspace — 跨项目治理规则

本文件管跨项目边界；各子项目自己的开发规则见其各自的 `AGENTS.md`/`PROJECT.md`
（例如 `projects/web-main/AGENTS.md`）。这里的规则优先级更高，子项目规则不得与本文件冲突。

## 核心结构

- `projects/web-main` 是唯一的 Web 核心平台主线。所有面向客户的分析能力最终都应在这里落地。
- `projects/qeeg-64ch-research` 是待整合的预研模块，目前独立存在，未接入 `web-main`。
- `projects/pc-qlanalyser` 是遗留桌面参考，仅提供算法/数值对照，不是开发主线。
- `projects/spike-analysis` 是待整合的预研模块（Spike sorting/分析），目前只有目录占位，未接入 `web-main`。

## 硬性红线

1. **不新建与 `web-main` 同构的整份拷贝或并行 Web 服务。** 曾经出现过 `epilepsy-demo-20260722`
   ——几乎是 `web-main` 某个时间点的完整重复部署（同款 backend/frontend/worker/eeg_core），
   独立跑通了公网验收却与主线完全脱钩维护，最终因为纯属重复被删除。新的 demo/pilot 需求应该
   在 `web-main` 内部通过配置、feature flag 或独立 report profile 实现，不要复制整个服务。

2. **预研成果先独立成包，再逐项提升，不整包合并。** 新的分析方法/管线（如 `qeeg-64ch-research`
   这类）应该：
   - 先在 `projects/` 下建立独立的、不依赖 FastAPI/PyQt/SQLite 的 Python 包；
   - 生命周期标注为 Lab/internal validation；
   - 用合成/去客户化 fixture 做数值验证，不能只靠视觉比较；
   - 通过验证的单个方法才逐项迁入 `web-main/eeg_core`，不允许把整条管线一次性接入
     `task_service` 的同步分支或客户任务白名单。

3. **不得把 Lab/Beta 方法包装成 stable 结论或临床诊断。** 所有研究性方法在文档、报告和 API
   响应中都必须带明确的科学边界说明（research-only / pending professional review 等）。

4. **不得把 19 导常模外推为 64 导常模。** 涉及 PC 端 `EEGnorms` 常模资产的任何复用，都要在文档
   里写清楚实际覆盖的导联数量和适用范围。

5. **原始 EEG/电生理数据、密钥、客户报告标识不进入版本库。** 任何恢复/重建工作（例如从 Codex
   会话日志重放源码）必须先做秘密和患者数据扫描，产物目录（outputs/results 等）只作数值证据，
   不当作源码恢复的依据保留进仓库。

## 变更前检查

新增/移动/删除 `projects/` 下的顶层项目前，先确认：
- 是不是已有项目的重复部署（参考红线 1）；
- 有没有被其他项目、脚本、CI、部署配置引用（全仓库搜索项目名/路径）；
- 根目录 `README.md` 的项目角色表是否需要同步更新。
