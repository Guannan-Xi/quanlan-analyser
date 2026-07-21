# QLanalyser 用户级端到端对抗验收标准

**版本:** 2026-07-02  
**状态:** V01 试点阶段生效  
**适用范围:** QLanalyser Online 客户可见功能、发布候选、全量对抗审核、重要 UI/API 变更

---

## 1. 定义

QLanalyser 的“对抗性审查”必须是**用户级端到端验收**，不是随便看代码、grep 字符串、读几个 API 返回值。

合格的对抗验收必须像真实客户一样完成主路径：打开浏览器、登录、点击、等待、截图、触发 API、验证反馈、下载产物，并记录可复现证据。

静态代码扫描只能作为辅助线索，不能替代用户级 E2E 验收。

---

## 2. V01 试点边界

V01 是稳定 MVP，用于客户免费试用，不是完整商业化平台。因此：

- 暂不做复杂多租户和复杂权限系统。
- 暂不做在线支付真实资金闭环。
- 暂不做临床诊断功能。
- 安全和合规验收仍必须覆盖 P0 硬边界：
  - 非医用边界措辞；
  - 数据完整性；
  - 功能崩溃；
  - 未登录访问保护；
  - 结果/报告产物可追溯。

---

## 3. 必走用户主路径

每次用户级 E2E 对抗验收至少覆盖以下路径：

| 路径 | 必验内容 |
|------|----------|
| 登录与会话 | 正确登录、错误密码、未登录访问、退出/会话状态 |
| 项目管理 | 列表、创建、选择、修改、归档/删除或受保护提示 |
| EEG 数据 | 文件列表、详情、元数据、波形 chunk、空态/404 |
| 数据准备 | 数据准备 gate、波形预览、按钮可用/不可用原因 |
| 分析任务 | 方法卡片、任务创建、失败态、超时态、结果态 |
| 结果查看 | 结果卡片、artifact 链接、报告生成入口、空态 |
| 报告交付 | HTML 报告、ZIP 包、下载链接和错误态 |
| 计费钱包 | 钱包余额、沙盒充值、账本、错误反馈 |
| 管理后台 | 管理员登录、概览、账户、任务/状态、客户禁止访问 |
| 教学模式 | 示例数据可见、教学项目/文件只读保护、教学引导可重新打开 |

---

## 4. 必须截图的页面

每次验收必须保存截图，至少包括：

1. `01-login.png`
2. `02-dashboard.png`
3. `03-storage.png`
4. `04-analysis.png`
5. `05-workflow.png`
6. `06-epilepsy.png`
7. `07-results.png`
8. `08-publication.png`
9. `09-user-center.png`
10. `10-admin-dashboard.png`

如某页面因环境或数据前置条件不可达，报告中必须标注 `environment_blocked` 或 `product_blocked`，不能默默跳过。

---

## 5. 对抗角色

验收时必须至少覆盖以下视角：

| 角色 | 关注点 |
|------|--------|
| 真实客户 | 是否能看懂下一步、完成主任务 |
| 困惑用户 | 空态、错误态、按钮禁用原因是否清楚 |
| 对抗用户 | 未登录、错误输入、越权访问、重复点击 |
| 系统故障场景 | API 不可达、任务超时、空数据、下载失败 |
| 监管审计员 | 非医用边界、诊断性措辞、证据可追溯 |

---

## 6. 证据要求

验收结果必须输出到 `work/release_evidence/<run-id>/`，并包含：

```text
user_level_e2e_adversarial_result.json
user_level_e2e_adversarial_receipt.md
screenshots/*.png
```

JSON 报告必须包含：

- `status`
- `verdict`
- `frontend_url`
- `api_base`
- `started_at` / `finished_at`
- `steps[]`
- `screenshots[]`
- `findings[]`
- `p0_count` / `p1_count` / `p2_count` / `p3_count`
- `classification`
- `remaining_risks[]`

---

## 7. 失败分类

| 分类 | 含义 | 退出码 |
|------|------|--------|
| `passed` | 无 P0/P1，主路径通过 | 0 |
| `conditional_pass` | 无 P0，但有 P1/P2 需后续处理 | 0 |
| `product_failed` | 存在 P0 或主路径断裂 | 1 |
| `environment_blocked` | Playwright/浏览器/依赖缺失 | 2 |
| `service_unreachable` | 前端或后端服务不可达 | 2 |

---

## 8. P0/P1 判定

### P0

- 页面白屏或无法登录；
- 未登录可访问客户数据；
- 主路径无法继续且无恢复路径；
- 报告/产物下载不可用；
- 明确诊断性或临床治疗性表达；
- 数据写入后读回不一致；
- 用户级验收没有截图/报告却声称通过。

### P1

- 关键按钮无禁用原因；
- 加载/失败反馈缺失；
- 管理后台关键入口不可用但不影响客户主路径；
- 任务同步执行导致超时但有已知规避；
- 钱包/余额错误态误导但不造成真实资金风险。

### P2/P3

- 视觉对比度、间距、文案细节、移动端滚动、测试选择器残留等。

---

## 9. 禁止 Fake Pass

以下情况一律不算通过：

- 只读代码，不打开浏览器；
- 只调 API，不点击 UI；
- 只看首页，不走项目/数据/结果链路；
- 没有截图；
- 没有 JSON 报告；
- 没有失败态/错误输入测试；
- 只说“看起来没问题”；
- 发现 P0 后未复测就签收。

---

## 10. 标准命令

本地验收建议命令：

```bash
node scripts/e2e_user_level_adversarial_acceptance.mjs \
  --frontend http://127.0.0.1:4174 \
  --api http://127.0.0.1:8001/api
```

也可使用环境变量：

```bash
QLANALYSER_FRONTEND_URL=http://127.0.0.1:4174 \
QLANALYSER_API_URL=http://127.0.0.1:8001/api \
node scripts/e2e_user_level_adversarial_acceptance.mjs
```

---

## 11. 收据格式

```text
user_level_e2e_adversarial_review:
  standard: qlanalyser_user_level_e2e_adversarial_review_standard_20260702
  run_id: <run-id>
  evidence_dir: <path>
  frontend_url: <url>
  api_base: <url>
  browser: <chromium/edge>
  screenshots: <N>
  steps_passed: <N>
  steps_failed: <N>
  p0: <N>
  p1: <N>
  p2: <N>
  p3: <N>
  verdict: passed | conditional_pass | product_failed | environment_blocked | service_unreachable
  next_real_artifact: <next action>
```
