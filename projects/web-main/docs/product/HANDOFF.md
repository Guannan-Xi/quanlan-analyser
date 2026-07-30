# QLanalyser 产品文档整理 — 交接说明

写给下一个接手的 Codex 会话。目的是让你不用重新摸索环境和历史，能直接从当前状态继续。

## 一、核心文件与真实状态（写入时刻实测，非记忆）

| 文件 | 路径 | 行数 | SHA256 |
|---|---|---|---|
| 主文档 | `D:\Quanlan\Codes\Python\qlanalyser-workspace\projects\web-main\docs\product\qlanalyser_master_product_requirements.md` | 775 | `1B72FBBA9ED53E6D87DF3F04175B3839AE49E919FD2F04BA3348323B208DCA10` |
| 对外简版 | `D:\Quanlan\Codes\Python\qlanalyser-workspace\projects\web-main\docs\product\qlanalyser_overview_external.md` | 212 | 未重新核对，视为草稿 |

主文档结构：H2=17（正文 9 章 + 附录 A–H 共 8 个），H3=36，H4=6。正文 1–9 章讲背景/定位/业务线/路线/商业/风险；附录 A–H 是细则（状态标签、方法工作流、架构约束、第一阶段版本详细需求、云端权限、计费模型、备份契约、SEEG/ECoG/Spike 专项）。

**验证方法**（不要相信这份文档里任何数字，自己重新跑一遍）：

```powershell
$f='D:\Quanlan\Codes\Python\qlanalyser-workspace\projects\web-main\docs\product\qlanalyser_master_product_requirements.md'
$L=Get-Content -Path $f -Encoding UTF8
Write-Output ('LINES=' + $L.Count)
Write-Output ('HASH=' + (Get-FileHash -Path $f -Algorithm SHA256).Hash)
Write-Output ('H2=' + (($L | Where-Object {$_ -match '^## '}).Count))
```

## 二、飞书文档 — 已与本地主文档同步

飞书文档《QLanalyser 产品总需求（初稿）》，`document_id = HSqpdGlh1oOnc3xHycjc2ydhn4c`，URL：
`https://quanland.feishu.cn/docx/HSqpdGlh1oOnc3xHycjc2ydhn4c`

**2026-07-27 已由 Codex 使用郤冠楠用户权限完成同步，飞书 revision_id = 177。** 第一章经 `claude-opus-5` 评审和优化，并按产品负责人补充的“代码与原理学习成本高、需要图形化流程引导”背景完成第二轮修订；写入前已备份 revision 153 的 info、raw 与 blocks，写入后回读为 24460 字符、464 个根子 block，标题层级为 1/17/36/6，十一项关键字符串均命中，乱码与敏感字段检测均为 0。本地主文档仍是权威版本。

同步工具真实路径（这是本会话验证过的，不要用别的猜测路径）：

```text
skill        C:\Users\Administrator\.zcode\skills\feishu-user-access\
node         C:\Program Files\nodejs\node.exe   （node 不在 PATH 里）
working dir  D:\Quanlan\Codes\Python\quanlan-feishu-assistant   （.env 和 token 文件在这里，CWD 必须是这个目录）
```

读取（`--user` 是只读）：
```powershell
cd /d "D:\Quanlan\Codes\Python\quanlan-feishu-assistant"
"C:\Program Files\nodejs\node.exe" "C:\Users\Administrator\.zcode\skills\feishu-user-access\scripts\feishu-docs.mjs" --user info "https://quanland.feishu.cn/docx/HSqpdGlh1oOnc3xHycjc2ydhn4c"
```

写入必须走临时脚本（导入 `feishu-auth.mjs`），完整方法和坑点见：
`C:\Users\Administrator\.zcode\skills\feishu-user-access\references\write-recipe.md`

写入前必须：① 备份当前飞书内容（raw + blocks）到本地 JSON；② 表格建议降级为"标签: 值"文本行而不是真表格块（真表格块容易触发 `99992402 field validation failed`）；③ 写完立刻 readback 核对 revision_id、字符数、block 数和几个关键字符串是否命中。这套流程已跑通过四次（rev83→105、rev105→129、rev129→153、rev153→177）。

## 三、本次会话对主文档做了什么修改（真实发生的，均已验证）

1. **§2 第24行**：`数据与安全边界不因阶段变化` 这句在正文第一次出现"阶段"概念之前就用了这个词，读者会愣一下。已删除该句独立存在的位置，合并进上一句末尾。
2. **§6 开头**：原来直接从"6.1 第一阶段"细节切入，缺一句总述。已新增：`全产品只分两个阶段：第一阶段（本地）与云端阶段。数据不可变性、科研边界与安全要求不因阶段变化，两个阶段共用同一套规则（见附录 A—G）。`
3. **附录 H.3**：原文写"不进入第一/第二/第三阶段现有排期"，但全文只有两阶段结构（第一阶段 + 云端阶段），这是更早版本的残留提法。已改为"不进入第一阶段或云端阶段现有排期"。
4. **附录 F 三处 + 附录 G 一处**：上一轮全文正则替换"第二阶段→云端阶段"时产生了"云端阶段云端"重复词（第442、500、634行附近）。已修正为"云端阶段"。
5. **§8 拟构建的长期能力与壁垒**：原来七条里有两条是纯架构实现细节（"领域代码可在本地云端间复用"、单纯罗列"数据不变量+备份隔离+审计"），不构成竞争壁垒，是类别错误。已删除第一条（附录 C.2 已有），第二条改写为"可审计、不可篡改的数据治理体系...形成医院与临床客户可核验的信任基础"，让它真正读作"壁垒"而不是"合规清单"。

## 四、已知遗留问题（未处理，需要判断或用户输入）

- **§9.2 战略待决策共8项**，全部需要产品负责人（郤冠楠）拍板，文档逻辑本身推不出答案，不要试图自己填空：云端启动条件、第一阶段命名与技术栈、科学交付门槛、SimNIBS 部署条件、SEEG/ECoG 顺序、云端治理细则、备份服务承诺（RPO/RTO）、Spike 重启门槛。
- **对外简版文档**（`qlanalyser_overview_external.md`，212行）已做结构与关键词核对：两阶段表述、Spike 暂缓和非诊断边界与主文档一致；它不是主文档逐段缩写，本轮未自动改写。后续若调整对外措辞，仍需单独评审。

## 五、这份工作流程里踩过的坑（写给你避雷）

1. **不要相信任何未经当次工具调用验证的"已完成"陈述**——包括这份交接文档本身列的数字，如果时间过去太久，重新跑一遍第一节的验证命令。
2. **飞书同步是删除全部 block 再重写**，不是增量更新。写之前必须先备份（raw + blocks 存成本地 JSON），这是唯一的回退手段，没有 git 版本控制。
3. **表格在飞书里容易写坏**，真表格块（block_type 相关字段）经常触发 `99992402 field validation failed`，稳妥做法是降级成 `标签: 值` 的纯文本行。
4. **全文正则替换后必须重新扫描一遍替换结果**，本会话就因为"第二阶段→云端阶段"的替换产生过三处"云端阶段云端"这种机械拼接错误，靠肉眼读没发现，是用 PowerShell 正则扫出来的。
5. **这些产品文档目前在父仓库中仍是未跟踪文件，尚无可依赖的版本历史**。任何大改动前先复制带时间戳的备份；进入正式维护后再由负责人决定是否纳入版本控制。

## 六、2026-07-27 Codex 接手后的增量核验

- 重新核验主文档：675 行，SHA256 为 `BE2AA1175193799BBF602D8BBC45190C4DDEF51C583C0F53159A57B348BC6FE6`，H2/H3/H4 分别为 17/36/6；§9.2 八项仍保持待决策。
- 使用郤冠楠用户身份回读飞书文档 `HSqpdGlh1oOnc3xHycjc2ydhn4c`，确认当前 `revision_id = 177`。因此“飞书仍停留在 revision 105、等待同步”属于旧状态，不再成立。
- 修复 `PRODUCT.md` 的跨文档冲突：Spike 当前是工作区顶层独立预研项目 `projects/spike-analysis`，不属于 `web-main` 内部模块；当前暂缓、不实现、不定价、不进入现有版本排期。
- 已读取两个飞书参考源，并在主文档第一章写明三层权威边界：产品事实与边界以产品总需求为准，跨岗位流程以《用 AI 升级软件研发流程》手册为准，当前执行状态以 QLanalyser 项目文档系统为准。新产品决定先回写主文档，再进入版本与专业交付文档。
- Opus 评审门禁尚未完成：当前进程未加载 `REVIEW_MODEL_OPUS48_API_KEY`、`REVIEW_MODEL_OPUS48_BASE_URL` 和 `REVIEW_MODEL_OPUS48_MODEL`，路由预检随后两次超时。本轮没有向外发送主文档，不得把本地审查描述为 Opus 已通过；状态保持 `ACCEPTANCE_INCOMPLETE`。

## 七、2026-07-27 QEEG 与市场测算增量

- 主文档已实测为 702 行，SHA256 为 `4F035DEC6735D67046EC2C36E73D852B75508A1AF63F54C7869828E45CBB29B5`，H2/H3/H4 分别为 17/37/6。
- QEEG 已明确支持 19、32、64 三类导联配置选择。三类配置必须分别绑定通道映射、参考、QC、可用方法、适用常模和验证状态；现有 19 导常模不得外推到 32/64 导，缺少对应验证证据时不得开放常模 Z-Score 或宣称常模有效。
- 版本边界已明确：V1 提供 QEEG 19/32/64 配置入口和已有科研辅助能力迁移；V3 承担专业 scalp EEG 方法、自动 QC、ICA/ICLabel、SafetyGate、清洗版本和结果契约。
- 已增加 `F.3 QLanalyser Online 需求量级情景测算（内部、未验证）`。214.3 万元/年仅为给定假设下的全量覆盖理论金额，不是市场规模、收入预测、定价或销售承诺；原始参数来源尚未补齐。
- `claude-opus-5` 分块全文审核及跨章节综合结论为 `FAIL`。主要整改项包括版本 Gate、V2 验收、云端启动必要条件、SEEG/ECoG 顺序归属、备份授权边界和市场测算证据。QEEG 的 V1/V3 文字冲突已按上述版本边界修复，但不得据此宣称整篇审核通过。
- 飞书产品总需求仍为 revision 177，是本轮修改前的同步点。本轮 QEEG 与市场测算尚未写入飞书；本地主文档继续作为权威版本，未经明确确认不得覆盖飞书。

## 八、2026-07-27 两阶段、线上版本与文档系统更新

- 产品阶段已统一为“本地阶段”和“线上阶段”。本地阶段包含本地 V1—V3；线上阶段明确为 Online V1 单用户在线分析、Online V2 团队协作、Online V3 商业化运营、Online V4 数据保护与规模化。
- 原 scalp EEG 产品名称已统一为“头皮脑电专业分析”，首次出现保留英文括注；SEEG/ECoG 继续作为后续独立专业模块。
- 第一章新增三份核心文档的组织关系和维护规则：产品总需求维护产品基线，AI 研发流程手册维护通用协作规则，QLanalyser 项目文档系统维护当前执行状态和专业交付物入口。
- 附录 C.1 新增四个本地参考代码库的绝对路径、对应版本、审阅重点和迁移证据要求。参考代码只用于审阅、迁移和数值对照，不代表已经通过产品或科学验收。
- 主文档当前实测为 775 行，SHA256 为 `1B72FBBA9ED53E6D87DF3F04175B3839AE49E919FD2F04BA3348323B208DCA10`，H2/H3/H4 为 18/40/6，代码围栏共 16 行（8 组）。
- 已使用郤冠楠用户身份覆盖同步飞书产品总需求。写入前备份 revision 177 的 info/raw/blocks，备份时间戳为 `2026-07-27T15-13-26-043Z`；写入后回读 revision 203、28686 字符、527 个根内容块，标题块为 1/18/40/6。关键内容全部命中，乱码和敏感字段检测均为 0。
- 上一节“飞书仍为 revision 177、尚未同步”已被本节取代；当前飞书和本地主文档已同步到本轮基线。
