# NeuroCloud EEG MVP 交接说明

更新时间：2026-06-06

## 项目位置

根目录：

```text
C:\Users\XGN\Documents\Codex\2026-06-06\eeglab-mne-1
```

前端 MVP：

```text
C:\Users\XGN\Documents\Codex\2026-06-06\eeglab-mne-1\outputs\eeglab-mne-mvp
```

本地访问：

```text
http://127.0.0.1:4173/
```

如服务未启动：

```powershell
C:\Users\XGN\miniconda3\envs\mineru\python.exe -m http.server 4173 --bind 127.0.0.1
```

工作目录需要是：

```text
outputs\eeglab-mne-mvp
```

## 当前产品结构

当前是一个静态前端 MVP，包含：

- 登录页
- 客户工作台
- 管理员后台
- 真实 MNE 生成的 EEG 示例图、统计表、结果包
- 本地化图标库 `vendor/lucide.min.js`
- Docker/Nginx 静态部署文件

关键文件：

```text
outputs\eeglab-mne-mvp\index.html
outputs\eeglab-mne-mvp\styles.css
outputs\eeglab-mne-mvp\app.js
outputs\eeglab-mne-mvp\assets\
outputs\eeglab-mne-mvp\vendor\lucide.min.js
outputs\eeglab-mne-mvp\package.json
outputs\eeglab-mne-mvp\Dockerfile
outputs\eeglab-mne-mvp\nginx.conf
outputs\eeglab-mne-mvp\DEPLOY.md
```

生成脚本：

```text
work\generate_mne_assets.py
work\generate_paradigm_benchmarks.py
work\generate_customer_oddball_case.py
```

## 已完成内容

### 客户入口

客户登录后只看到客户功能：

- 新手教程
- 项目总览
- 开始分析
- 方法向导
- 范式库
- 统计结果
- 投稿图
- 上传数据
- 我的数据
- 充值计费
- 申请开票

客户默认进入“新手教程”，教程按小白用户设计：

1. 先建项目
2. 上传脑电
3. 看懂费用
4. 不会选方法
5. 使用默认参数
6. 查看质控
7. 生成图和表
8. 提交或开票

客户页面已经尽量清理掉不应暴露的内容，例如：

- 高并发
- 内部测试
- 商户授权
- MVP / 原型
- 开发验证

### 管理员入口

管理员登录后只看到后台功能：

- 后台总览
- 任务运营
- 订单开票
- 系统状态

后台可查看：

- 客户项目
- 任务状态
- 订单与开票
- 存储和系统状态

### MNE 真实示例资产

已有真实 MNE/Matplotlib 生成图：

```text
assets\analysis-erp.png
assets\analysis-psd.png
assets\analysis-ica.png
assets\analysis-timefreq.png
assets\analysis-source.png
assets\analysis-ml.png
assets\publication-main-figure.png
assets\publication-erp-grand-average.png
assets\publication-bandpower-statistics.png
assets\publication-qc-dashboard.png
```

已有结果数据：

```text
assets\subject_level_metrics.csv
assets\statistics_summary.csv
assets\bandpower_long_format.csv
assets\methods_snippet.txt
assets\figure_caption.txt
assets\analysis_manifest.json
assets\publication_package.zip
```

### 20 个范式数据集

位于：

```text
outputs\eeglab-mne-mvp\assets\paradigm_benchmark
```

包含 20 个常见 EEG 范式的模拟 EDF、事件 TSV 和 metadata。

### 当前正在做的客户/运营验收任务

用户最新任务是：

客户角色：

- 充值 1000 元
- 带 5 份脑电数据
- 生成 5 份 Oddball EEG
- 完成一次完整 Oddball ERP 分析流程
- 结果发送到 `399467826@qq.com`

运营角色：

- 查看客户注册信息
- 查看消费信息
- 查看分析结果
- 确认功能正常

已新增脚本：

```text
work\generate_customer_oddball_case.py
```

该脚本会生成：

```text
outputs\eeglab-mne-mvp\assets\customer_oddball_case\
```

计划生成内容：

- `sub-001_oddball.edf` 到 `sub-005_oddball.edf`
- 每个被试对应 `*_events.tsv`
- `customer_subject_level_metrics.csv`
- `customer_statistics_summary.csv`
- `customer_oddball_erp_pz.png`
- `customer_oddball_p300_topomap.png`
- `customer_methods.txt`
- `customer_figure_caption.txt`
- `customer_analysis_manifest.json`
- `customer_oddball_erp_package.zip`
- `prepared_email_to_399467826.eml`

注意：当前环境未发现 SMTP / 邮箱凭证。不能假装邮件已发送。应先生成邮件草稿和附件包，页面显示“邮件待发送”，等配置 SMTP 后再真实发送。

推荐运行命令：

```powershell
C:\Users\XGN\miniconda3\envs\mineru\python.exe work\generate_customer_oddball_case.py
```

## 验证命令

前端语法：

```powershell
node --check outputs\eeglab-mne-mvp\app.js
```

资源引用检查示例：

```powershell
@'
const fs=require('fs'); const path=require('path');
const root='outputs/eeglab-mne-mvp';
const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
const sections=[...html.matchAll(/<section class="view[^"]*" id="([^"]+)"/g)].map(m=>m[1]);
const views=[...html.matchAll(/data-view="([^"]+)"/g)].map(m=>m[1]);
const jumps=[...html.matchAll(/data-view-jump="([^"]+)"/g)].map(m=>m[1]);
const missing=[...new Set([...views,...jumps].filter(v=>!sections.includes(v)))];
const refs=[...html.matchAll(/(?:src|href)="\.\/([^"]+)"/g)].map(m=>m[1]);
const missingRefs=refs.filter(p=>!fs.existsSync(path.join(root,p)));
console.log({sections:sections.length, views:[...new Set(views)].length, jumps:[...new Set(jumps)].length, missing, refs:refs.length, missingRefs});
'@ | node -
```

乱码扫描：

```powershell
Select-String -Path 'outputs\eeglab-mne-mvp\index.html','outputs\eeglab-mne-mvp\app.js','outputs\eeglab-mne-mvp\styles.css' -Pattern '锟|涓|鐨|�'
```

## 最近一次已通过验证

之前已经通过：

- 客户登录默认进入 `journey`
- 客户 11 个导航全部可点
- 管理员登录默认进入 `adminDashboard`
- 管理员 4 个导航全部可点
- 控制台无错误
- `node --check app.js` 通过
- 页面资源引用匹配
- 无乱码

注意：之后若继续修改，需要重新验证。

## 下一步建议

1. 运行 `work\generate_customer_oddball_case.py`
2. 把生成的客户 Oddball 结果包挂到客户“投稿图/统计结果”页面
3. 把客户注册、充值、消费、分析结果挂到管理员后台页面
4. 邮件部分：
   - 若无 SMTP 凭证：提供 `.eml` 草稿和 ZIP 附件，状态写“待发送”
   - 若有 SMTP 凭证：真实发送到 `399467826@qq.com`，并在后台写发送记录
5. 再次验证客户和管理员路径

## 重要约束

- 不要在客户页面暴露内部测试、并发压测、商户授权未接入、MVP、开发验证等信息。
- 客户页面必须小白友好，默认教程优先。
- 管理员页面可以展示运营、任务、订单、系统状态。
- 邮件不能伪造发送状态；没有凭证就只能生成草稿和附件。
- 不要删除已生成的 MNE 资产和范式资产。
