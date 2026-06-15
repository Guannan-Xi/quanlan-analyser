export const analysisTemplates = [
  {
    id: "raw_browser",
    name: "数据浏览与分段",
    engine: "MNE Raw.plot",
    eeGLAB: "EEGLAB scroll / reject",
    output: "连续波形、事件叠加、坏段标注",
    status: "V1 原型可见",
    cost: 8
  },
  {
    id: "resting_psd",
    name: "静息态功率谱",
    engine: "MNE Raw.compute_psd",
    eeGLAB: "spectopo",
    output: "band_power.csv、PSD 图、alpha peak",
    status: "示例 BDF 已烟测",
    cost: 28
  },
  {
    id: "erp_p300",
    name: "ERP 事件相关电位",
    engine: "MNE Epochs / Evoked",
    eeGLAB: "epoch + pop_averager",
    output: "erp_metrics.csv、差异波、窗口均值",
    status: "待确认事件语义",
    cost: 38
  },
  {
    id: "ica_preprocess",
    name: "ICA 预处理",
    engine: "MNE ICA",
    eeGLAB: "runica / ICLabel",
    output: "ICA 成分、眨眼候选、排除记录",
    status: "规划中",
    cost: 35
  },
  {
    id: "time_frequency",
    name: "时频分析",
    engine: "MNE TFR / Morlet",
    eeGLAB: "ERSP / ITC",
    output: "ERSP、ITC、频段时间窗指标",
    status: "规划中",
    cost: 48
  },
  {
    id: "topomap",
    name: "头皮地形图",
    engine: "MNE topomap",
    eeGLAB: "topoplot",
    output: "频段/时间窗 topomap",
    status: "规划中",
    cost: 18
  },
  {
    id: "ml_classification",
    name: "机器学习分类",
    engine: "MNE Epoch 特征 + sklearn",
    eeGLAB: "BCILAB 思路兼容",
    output: "CSP/LDA、交叉验证、混淆矩阵",
    status: "规划中",
    cost: 88
  }
];

export const paradigmLibrary = [
  ["静息态睁闭眼", "PSD", "alpha reactivity", "适合新手"],
  ["听觉 Oddball P300", "ERP", "p300", "适合新手"],
  ["视觉 Oddball P300", "ERP", "p300", "适合新手"],
  ["Go/No-Go 抑制控制", "N2 / P3", "n2_p3", "常用"],
  ["Flanker 冲突与错误监控", "ERN / theta", "ern_conflict", "常用"],
  ["Stroop 冲突", "ERP / theta", "n450", "常用"],
  ["N-back 工作记忆", "Time-frequency", "frontal_theta", "常用"],
  ["面孔知觉 N170", "ERP", "n170", "常用"],
  ["语义 N400", "ERP", "n400", "常用"],
  ["视觉搜索 N2pc", "Lateralized ERP", "n2pc", "进阶"],
  ["运动想象左右手", "ERD / ML", "mu_beta_erd", "进阶"],
  ["运动执行 MRP", "Readiness potential", "mrp", "常用"],
  ["SSVEP 频率标记", "Frequency response", "snr", "常用"],
  ["ASSR 40 Hz", "Time-frequency", "40hz_assr", "常用"],
  ["冥想 alpha/theta", "Bandpower", "alpha_theta", "常用"],
  ["睡眠纺锤/K-complex", "Sleep EEG", "spindle_kcomplex", "进阶"],
  ["体感 SEP", "ERP", "sep", "常用"],
  ["错误监控 ERN", "ERP", "ern", "进阶"],
  ["奖赏正波 RewP", "ERP", "reward_positivity", "进阶"],
  ["注意提示 CNV", "Slow potential", "cnv", "进阶"]
];
