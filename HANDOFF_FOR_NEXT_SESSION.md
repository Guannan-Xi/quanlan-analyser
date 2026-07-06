# QLanalyser Handoff 2026-07-02 — 用户级 E2E 对抗验收上线

## 当前会话产出摘要

1. **安全加固 6 项 P0/P1 修复**（本会话前半段）
2. **静态对抗审核 → 用户级端到端验收升级**（本会话后半段）
3. **新增标准 + 脚本 + 证据**

---

## 起服务

两个服务已经在跑（如挂了需重开）：

```bash
# 后端（miniconda Python）
cd D:\Quanlan\Codes\Python\quanlan-analyser-official
C:/Users/XGN/miniconda3/python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8001

# 前端（node http-server，可能已经在跑）
cd D:\Quanlan\Codes\Python\quanlan-analyser-official\frontend
npx http-server . -p 4174 -c-1
```

前端 URL：`http://127.0.0.1:4174/?api=http://127.0.0.1:8001/api`
演示账户：`demo.customer@quanlan.cn / demo123456`
管理账户：本地/测试环境使用 `QLANALYSER_ADMIN_EMAIL` 与 `QLANALYSER_ADMIN_PASSWORD`；生产环境必须配置非本地默认口令。

---

## 运行用户级对抗验收

```bash
cd D:\Quanlan\Codes\Python\quanlan-analyser-official
node --check scripts/e2e_user_level_adversarial_acceptance.mjs
QLANALYSER_UI_TIMEOUT_MS=10000 node scripts/e2e_user_level_adversarial_acceptance.mjs --frontend http://127.0.0.1:4174 --api http://127.0.0.1:8001/api
```

## 最近一次验收结果

- **证据目录：** `work/release_evidence/user_level_e2e_adversarial_20260702_122302/`
- **结果：** `conditional_pass`
- **P0：** 0
- **P1：** 2
- **截图：** 10 张（01-login ~ 10-admin-dashboard）

### 剩余 P1（2 项）

| P1 | 说明 |
|----|------|
| navigate:#epilepsyWorkbenchInline | 癫痫工作台没有主导航按钮，`window.setView` 也不暴露，无法从客户路径直接进入 |
| customer:epilepsy-workbench-visible | 癫痫工作台面板不可见（同上） |

---

## 本次会话修改的文件

### 后端安全修复（P0）

| 文件 | 改了什么 |
|------|---------|
| `backend/services/state_store.py` | 新增 `atomic_cross_registry_lock()` + 可重入锁 |
| `backend/services/billing_service.py` | `charge_analysis_task` 和 `confirm_recharge_order` 包原子锁 |
| `backend/services/object_storage_service.py` | `MAX_UPLOAD_BYTES`(2GB) + `UploadSizeExceeded(413)` |
| `backend/api/artifacts.py` | `_assert_path_within_derivatives` 用 `Path.relative_to()` |
| `backend/api/projects.py` | `create_project` 注入 `owner_user_id=current.id` + 空名 422 |
| `backend/api/tasks.py` | 路由级认证 + 读操作无 owner 校验 |
| `backend/api/eeg_files.py` | 路由级认证 + 读操作无 owner 校验 |
| `backend/models/project.py` | 删除废弃 `owner_id` 字段 |
| `backend/services/account_service.py` | `_verify_password` 短密码不泄露信息 |

### 前端修复

| 文件 | 改了什么 |
|------|---------|
| `frontend/app.js` | XSS `escapeHtml(_liveError)` + localStorage 不存密码 + 历史密码清除 + 双击防护 |
| `frontend/index.html` | CSP meta + lucide `defer` + 移除硬编码凭证 |
| `frontend/styles.css` | modal z-index 40→100, toast z-index→1500 |

### 用户级 E2E 对抗验收（新增）

| 文件 | 说明 |
|------|------|
| `docs/product/qlanalyser_user_level_e2e_adversarial_review_standard_20260702.md` | **新增**：用户级对抗验收标准 |
| `scripts/e2e_user_level_adversarial_acceptance.mjs` | **新增**：浏览器 E2E 验收脚本 |
| `AGENTS.md` | 项目级规则新增用户级 E2E 要求 |
| `docs/product/README.md` | 新增标准文档索引 |
| `docs/TASK_LOG.md` | 追加本次任务记录 |
| `docs/PROJECT_STATUS_CURRENT.md` | 追加证据入口 |

### 全局规范升级

| 文件 | 改了什么 |
|------|---------|
| `C:\Users\XGN\AGENTS.md` | Model 规则加 MUST NOT + 互为替补 + V01 豁免 + Lane 自律 |

---

## 已知状态

- Git 工作树脏（所有修改未提交）
- GLM-5.2 通道 403（`_route.py glm-5.2` 不可用）
- GPT-5.5 通道短 prompt 可用，长 prompt 超时
- DeepSeek API key 过期
- E2E 浏览器上传超时 45s（已知，非本次回归）
- Playwright 未全局安装

---

## 建议下一步

1. **看截图：** `work/release_evidence/user_level_e2e_adversarial_20260702_122302/screenshots/`
2. **修 P1：** 给癫痫工作台加主导航入口 or 在验收脚本中从 workflow 页面点 `[data-real-action="open-epilepsy-workbench"]` 进入
3. **提交：** `git add -A && git commit -m "feat: user-level E2E adversarial acceptance standard + security hardening"`（等确认后）
4. **继续修后端 P0/P1：** 按 `ZCODE_HANDOFF_QLANALYSER_FULL_AUDIT_20260702.md` 上线前清单
