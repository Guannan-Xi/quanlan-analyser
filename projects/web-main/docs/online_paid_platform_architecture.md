# 全澜脑科学在线付费脑电数据分析平台架构

## 1. 产品定位

本平台是一个在线付费的脑电数据分析平台，面向科研用户、课题组、医院科研团队和脑科学数据服务场景。

平台目标是让客户可以在线管理自己的 EEG 数据、充值付费、创建分析项目、配置分析流程、预览原始数据、运行预处理和核心分析方法，并下载可复现的结果包。

平台不是临床诊断系统，不输出疾病诊断、自动判读或医疗结论。

## 2. 用户角色

### 客户

- 注册和登录
- 充值余额
- 查看消费明细和发票
- 创建、编辑、删除自己的数据
- 创建分析项目
- 设计分析流程
- 运行预处理、PSD、ERP、时频、ICA 等分析
- 预览原始数据和分析图表
- 下载结果包

### 管理员

- 查看客户、余额、订单和发票
- 查看任务队列和失败原因
- 审核大文件、异常任务和退款申请
- 管理分析模板和价格
- 查看系统资源、存储、worker、队列和错误日志

## 3. 总体架构

```text
Browser Frontend
  Customer Workspace
  Admin Console
  Billing Center
  Workflow Designer
        |
Backend API
  Auth / User / Organization
  Project / Subject / Session
  EEG File CRUD
  Billing / Recharge / Orders / Invoices
  Workflow Template / Analysis Task
  Artifact / Report / Download
        |
Task Queue / Worker
  Metadata
  Preview
  Preprocess
  PSD
  ERP
  ICA
  Time-Frequency
  Report Package
        |
EEG Core
  MNE-Python Engine
  EEGLAB-Compatible Workflows
  Readers / Preprocessing / Analysis / Visualization
        |
Storage
  Object Storage for EEG files
  Derivatives
  Reports
  Database
  Audit Logs
```

## 4. 核心模块

### 客户工作台

- 项目空间
- 数据管理
- 原始数据预览
- 质控和预处理
- 分析模板
- 流程设计
- 结果中心
- 报告中心
- 充值计费

### 管理员后台

- 客户列表
- 订单和充值
- 分析任务
- 存储使用
- Worker 状态
- 价格和模板管理
- 风险审核

## 5. 数据 CRUD

客户只能管理自己组织内的数据。

```text
POST   /api/eeg/upload
GET    /api/eeg/files
GET    /api/eeg/files/{file_id}
PATCH  /api/eeg/files/{file_id}
DELETE /api/eeg/files/{file_id}
GET    /api/eeg/files/{file_id}/metadata
GET    /api/eeg/files/{file_id}/preview
```

数据对象至少包含：

- 文件名
- 格式
- 大小
- 采样率
- 通道数
- 时长
- annotations/events
- 所属项目、被试、session
- 状态：uploaded / metadata_ready / preview_ready / processing / archived / deleted

## 6. 充值计费

### 计费对象

- 文件上传存储
- Metadata 读取
- 原始数据预览
- 预处理
- PSD
- ERP
- ICA
- 时频
- 报告包
- 私有化或批量服务

### 账务对象

- Wallet
- RechargeOrder
- AnalysisOrder
- LedgerEntry
- InvoiceRequest

### 计费流程

```text
客户充值
  -> 支付成功
  -> 余额入账
  -> 创建分析任务前预估价格
  -> 冻结余额
  -> 任务完成后扣费
  -> 任务失败则解冻或部分扣费
  -> 生成消费明细和发票申请
```

## 7. 分析流程设计

客户可以基于模板创建 workflow：

```text
读取 metadata
  -> 原始数据预览
  -> 预处理
     - 滤波
     - 重参考
     - 重采样
     - 坏段/坏道标记
     - ICA
  -> 分析
     - PSD
     - ERP
     - Time-Frequency
     - Connectivity
  -> 可视化
  -> 报告
  -> 结果包下载
```

V1 优先实现：

- Metadata
- 原始数据预览
- 预处理配置表单
- PSD
- annotation-derived events
- ERP 准备度检查
- HTML 报告
- ZIP 结果包结构

## 8. 分析引擎

### MNE-Python

MNE-Python 是服务端主分析引擎，用于：

- Raw 读取
- annotations/events
- preprocessing
- epochs
- PSD
- ERP / evoked
- ICA
- time-frequency
- visualization

### EEGLAB-Compatible

EEGLAB 侧作为工作流兼容层：

- 支持导入 `.set`
- 对齐 EEGLAB 常见分析概念
- 导出接近 EEGLAB 用户习惯的参数和方法说明
- 后续可通过 MATLAB Engine 或离线转换加入更深度兼容

## 9. 存储策略

原始数据不能提交到 Git。

```text
data/uploads/       原始 EEG 文件
data/derivatives/   中间结果和分析输出
data/reports/       HTML/ZIP 报告
audit/              操作审计
```

生产环境应使用对象存储和数据库，不应只依赖本地目录。

## 10. 安全与合规边界

- 客户只能访问自己的数据
- 原始数据默认私有
- 所有下载和删除需要审计
- 管理员操作需要日志
- 不输出临床诊断
- 不宣传自动疾病判读
- 报告必须标注科研用途

## 11. 管理员后台指标

- 今日充值金额
- 今日消耗金额
- 待处理发票
- 运行中任务
- 失败任务
- 存储占用
- Worker 心跳
- 高风险任务

## 12. V1 交付路径

1. 完整前端业务闭环原型
2. BDF/MNE 元数据读取
3. 原始波形预览
4. PSD 烟测和可视化
5. annotations -> events
6. 充值/扣费台账原型
7. 管理员后台原型
8. 结果包结构
9. Playwright 全功能点击测试

