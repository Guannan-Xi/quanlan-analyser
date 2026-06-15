export const platformState = {
  wallet: {
    balance: 1000,
    frozen: 68,
    spentToday: 132,
    invoiceQueue: 1
  },
  files: [
    {
      id: "demo-bdf",
      filename: "C64RS_390026040074_260531103644.bdf",
      format: "BDF",
      subject: "C64RS 示例",
      status: "MNE 已识别",
      risk: "待接入 PSD/ERP 信号级分析",
      active: true
    },
    {
      id: "sub-02",
      filename: "sub-02_task-oddball.edf",
      format: "EDF",
      subject: "sub-02",
      status: "等待事件文件",
      risk: "ERP 需要事件标记",
      active: true
    },
    {
      id: "resting-demo",
      filename: "resting_demo.set",
      format: "SET",
      subject: "sub-rest",
      status: "可分析",
      risk: "需确认参考电极",
      active: true
    }
  ],
  workflow: {
    saved: false,
    estimatedCost: 68,
    steps: [
      ["Metadata", "读取格式、采样率、通道、annotations"],
      ["Preview", "原始波形、PSD、事件分布预览"],
      ["Preprocess", "滤波、重参考、重采样、坏道/坏段、ICA"],
      ["Analysis", "PSD、ERP、时频、连接性"],
      ["Report", "HTML 报告、CSV、PNG、复现文件、ZIP"]
    ]
  },
  admin: {
    customers: 18,
    rechargeToday: 6800,
    consumptionToday: 1240,
    runningTasks: 4,
    failedTasks: 1,
    storageUsed: "128 GB",
    workerStatus: "3 / 3 在线",
    invoiceQueue: 5
  }
};

export const pricing = [
  ["Metadata 读取", "¥ 2 / 文件"],
  ["原始数据预览", "¥ 8 / 文件"],
  ["预处理", "¥ 20 / 文件"],
  ["PSD 分析", "¥ 28 / 文件"],
  ["ERP 分析", "¥ 38 / 文件"],
  ["报告包", "¥ 20 / 次"]
];

export const architectureLayers = [
  ["Browser Frontend", "客户工作台、管理员后台、充值计费、流程设计"],
  ["Backend API", "用户、组织、项目、数据 CRUD、订单、任务、报告"],
  ["Task Queue / Worker", "metadata、preview、preprocess、PSD、ERP、ICA、报告包"],
  ["EEG Core", "MNE-Python 主分析引擎，EEGLAB-compatible 工作流"],
  ["Storage", "原始文件、derivatives、reports、ledger、audit logs"]
];

export function currency(value) {
  return `¥ ${Number(value).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

