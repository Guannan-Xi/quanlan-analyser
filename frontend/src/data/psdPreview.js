export const psdPreview = {
  source: "C64RS_390026040074_260531103644.bdf",
  method: "MNE Raw.compute_psd / Welch",
  durationUsed: "前 30 秒",
  channels: 64,
  sfreq: "1000 Hz",
  freqBins: 79,
  psdImage: "./src/assets/c64rs_psd_overview.png",
  rawImage: "./src/assets/c64rs_raw_preview.png",
  eventImage: "./src/assets/c64rs_event_overview.png",
  events: {
    count: 80,
    descriptions: [
      ["FocusChange", 62],
      ["SelectedPatchesChange", 14],
      ["KeyPress", 1],
      ["SessionStarts", 1],
      ["recording start", 1],
      ["recording end", 1]
    ],
    readiness: "可从 annotations 生成 events；ERP 条件语义仍需研究者确认。"
  },
  bands: [
    { band: "delta", range: "1-4 Hz", meanPsd: "9.10e-12" },
    { band: "theta", range: "4-8 Hz", meanPsd: "2.14e-12" },
    { band: "alpha", range: "8-13 Hz", meanPsd: "1.19e-12" },
    { band: "beta", range: "13-30 Hz", meanPsd: "1.20e-12" },
    { band: "gamma_low", range: "30-40 Hz", meanPsd: "1.36e-12" }
  ],
  alphaThetaRatio: "0.556",
  alphaBetaRatio: "0.993",
  note: "这是轻量烟测结果，用于验证真实 BDF 能跑通 PSD；正式科研报告仍需加入滤波、坏段、重参考和事件/任务语义。"
};
