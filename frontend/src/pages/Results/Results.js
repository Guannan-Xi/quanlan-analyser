import { psdPreview } from "../../data/psdPreview.js";

export const Results = {
  title: "结果中心",
  render() {
    return `
      <section class="grid">
        <article class="panel">
          <h2>结果文件</h2>
          <ul class="list">
            <li><span>图表</span><strong>PNG</strong></li>
            <li><span>表格</span><strong>CSV</strong></li>
            <li><span>参数</span><strong>JSON/YAML</strong></li>
          </ul>
        </article>
        <article class="panel">
          <h2>可重复性</h2>
          <p class="muted">每个结果包应包含参数、workflow、软件版本和方法学说明。</p>
        </article>
        <article class="panel wide">
          <h2>C64RS PSD 烟测结果</h2>
          <p class="muted">${psdPreview.source}：${psdPreview.method}，${psdPreview.durationUsed}，${psdPreview.channels} 通道，${psdPreview.sfreq}。</p>
          <div class="score-grid">
            <div class="score"><span>频点数</span><strong>${psdPreview.freqBins}</strong></div>
            <div class="score"><span>Alpha / Theta</span><strong>${psdPreview.alphaThetaRatio}</strong></div>
            <div class="score"><span>Alpha / Beta</span><strong>${psdPreview.alphaBetaRatio}</strong></div>
          </div>
        </article>
        <article class="panel wide">
          <h2>可视化结果</h2>
          <div class="figure-grid">
            <figure>
              <img src="${psdPreview.psdImage}" alt="C64RS BDF PSD 概览图" />
              <figcaption>PSD 概览：1-40 Hz Welch 频谱和频段功率预览。</figcaption>
            </figure>
            <figure>
              <img src="${psdPreview.rawImage}" alt="C64RS BDF 原始波形预览图" />
              <figcaption>原始波形预览：前 5 秒、前 8 个通道，仅用于快速质控。</figcaption>
            </figure>
            <figure>
              <img src="${psdPreview.eventImage}" alt="C64RS BDF 事件分布图" />
              <figcaption>事件分布：由 annotations 转换得到 ${psdPreview.events.count} 个 events，条件语义仍需确认。</figcaption>
            </figure>
          </div>
        </article>
        <article class="panel wide dense">
          <h2>频段功率预览</h2>
          <table class="table">
            <thead><tr><th>频段</th><th>范围</th><th>平均 PSD</th></tr></thead>
            <tbody>
              ${psdPreview.bands.map((row) => `<tr><td>${row.band}</td><td>${row.range}</td><td>${row.meanPsd}</td></tr>`).join("")}
            </tbody>
          </table>
          <p class="muted">${psdPreview.note}</p>
        </article>
        <article class="panel wide dense">
          <h2>结果包结构</h2>
          <table class="table">
            <thead><tr><th>目录</th><th>内容</th><th>用途</th></tr></thead>
            <tbody>
              <tr><td>figures/</td><td>PSD、ERP、topomap 图</td><td>论文和汇报</td></tr>
              <tr><td>tables/</td><td>band_power.csv、erp_metrics.csv</td><td>二次统计</td></tr>
              <tr><td>reports/</td><td>report.html</td><td>项目交付</td></tr>
              <tr><td>reproducibility/</td><td>parameters、workflow、versions、method text</td><td>复现分析</td></tr>
            </tbody>
          </table>
        </article>
      </section>
    `;
  }
};
