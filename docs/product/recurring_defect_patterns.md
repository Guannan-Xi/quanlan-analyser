# 全澜 QNACR 可重复缺陷模式注册表

## 使用说明

- 每次 QNACR 评审收敛后，将新增的 P0/P1 缺陷模式追加到此文件
- **作者开工前必须将此文件内容粘贴到提示语尾部自检**
- 每季度审查一次，删除过时条目
- 预防规则应具体到"在提示词中加入 \<某指令\>"的程度

---

## 模式列表

- ID: DP-20260702-001
  模式: 前端 DTO 字段映射与后端返回字段不匹配（start_sec、rms、review_status 等）
  级别: P0/P1
  出现工件: frontend/app.js fetchEpilepsyV3LiveEvents
  修复: 后端的字段名必须与前端读取的字段名一致；采用契约优先原则，先定义 DTO 接口再写两端
  预防规则: 每次添加新的数据端点时，在作者提示词中加入 $check-dto-field-consistency

- ID: DP-20260702-002
  模式: innerHTML 拼接动态用户数据时未转义
  级别: P0
  出现工件: frontend/app.js renderEpilepsyResultReviewV3Panel
  修复: 对所有动态内容使用 escapeHtml() 或 textContent
  预防规则: 在作者提示词中加入 $check-innerhtml-xss-escape

- ID: DP-20260702-003
  模式: 证据图 amplitude 阈值硬编码（0.82/0.70），未适配原始微伏级幅值
  级别: P1
  出现工件: backend/api/epilepsy_workbench.py:_event_review_status
  修复: 对所有事件的 score 做 max 归一化后再进行阈值判定
  预防规则: 添加新评分阈值逻辑时，必须确认输入值域范围并在提示词中注明

- ID: DP-20260702-004
  模式: 证据点 event_id 匹配直接用 CSV 列值，未处理缺列时的自动 ID 生成
  级别: P1
  出现工件: backend/api/epilepsy_workbench.py:_load_task_events_csv / get_event_evidence
  修复: CSV 加载时自动补齐 event_id（缺列时生成 E-XXX），确保 DTO 和证据端点共享同一 ID
  预防规则: 所有基于 CSV 的数据加载函数必须处理缺列回退

- ID: DP-20260702-005
  模式: matplotlib 图对象在异常路径下未确保 plt.close() 执行
  级别: P2
  出现工件: backend/api/epilepsy_workbench.py:_generate_event_evidence_png
  修复: plt.close(fig) 放入 try/finally 块
  预防规则: 所有 matplotlib 图像生成函数检查异常路径下的资源释放

- ID: DP-20260702-006
  模式: events.map 中单个异常事件导致整个列表崩溃
  级别: P2
  出现工件: frontend/app.js fetchEpilepsyV3LiveEvents
  修复: map 内增加 try-catch，异常事件设为 null 后用 .filter(Boolean) 过滤
  预防规则: 数据处理管道中每个独立元素须有容错

---

## 统计

| 统计项 | 值 |
|-------|-----|
| 总条目数 | 0 |
| P0 条目 | 0 |
| P1 条目 | 0 |
| 最后更新 | 2026-07-02 |
