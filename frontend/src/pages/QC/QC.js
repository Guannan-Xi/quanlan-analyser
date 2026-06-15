import { sampleDataset } from "../../data/sampleDataset.js";

export const QC = {
  title: "质控中心",
  render() {
    return `
      <section class="grid">
        <article class="panel">
          <h2>信号检查</h2>
          <p class="muted">V1 跟踪时长、通道数、采样率和预处理准备状态。</p>
          <ul class="list">
            <li><span>采样率</span><strong>${sampleDataset.samplingRate}</strong></li>
            <li><span>EEG 通道</span><strong>${sampleDataset.eegChannelCount}</strong></li>
            <li><span>时长</span><strong>${sampleDataset.duration}</strong></li>
          </ul>
        </article>
        <article class="panel">
          <h2>预处理</h2>
          <p class="muted">滤波、重参考、重采样和质量指标统一放在 eeg_core/preprocess 中。</p>
          <ul class="list">
            <li><span>滤波</span><strong>1-40 Hz</strong></li>
            <li><span>重参考</span><strong>平均参考</strong></li>
            <li><span>坏段标注</span><strong>待 MNE 接入</strong></li>
          </ul>
          <div class="toolbar">
            <button class="button" type="button" data-action="previewRaw">预览原始数据</button>
            <button class="button secondary" type="button" data-action="runPreprocess">运行预处理</button>
          </div>
        </article>
        <article class="panel wide">
          <h2>质控结论</h2>
          <p class="muted">${sampleDataset.filename} 已完成 MNE 元数据识别：${sampleDataset.eegChannelCount} EEG 通道、${sampleDataset.annotationsCount} 条 annotations。当前界面只展示科研质控状态，不给出临床诊断或疾病判读。</p>
          <div class="toolbar">
            <span class="badge ok">可进入 PSD</span>
            <span class="badge warn">ERP 需事件文件</span>
            <span class="badge risk">不输出临床结论</span>
          </div>
        </article>
      </section>
    `;
  }
};
