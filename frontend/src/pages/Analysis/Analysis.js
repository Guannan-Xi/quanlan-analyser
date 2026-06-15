import { sampleDataset } from "../../data/sampleDataset.js";
import { psdPreview } from "../../data/psdPreview.js";
import { analysisTemplates } from "../../data/productLibrary.js";

export const Analysis = {
  title: "分析模板",
  render() {
    const templateRows = analysisTemplates
      .map(
        (item) => `
          <tr>
            <td>${item.name}</td>
            <td>${item.engine}</td>
            <td>${item.eeGLAB}</td>
            <td>${item.output}</td>
            <td><span class="badge ${item.status.includes("已") || item.status.includes("可见") ? "ok" : "warn"}">${item.status}</span></td>
            <td>¥ ${item.cost}</td>
          </tr>
        `
      )
      .join("");

    return `
      <section class="grid">
        <article class="panel">
          <h2>静息态 PSD</h2>
          <p class="muted">面向 ${sampleDataset.format} / ${sampleDataset.samplingRate} 数据生成频段功率表和 PSD 图表。</p>
          <div class="toolbar"><button class="button" type="button" data-action="startPsd">启动 PSD</button></div>
        </article>
        <article class="panel">
          <h2>ERP / P300</h2>
          <p class="muted">已从 BDF annotations 解析 ${psdPreview.events.count} 个 events；条件语义需要研究者确认后再生成 ERP/P300。</p>
          <div class="toolbar"><button class="button secondary" type="button" data-action="checkEvents">检查事件标记</button></div>
        </article>
        <article class="panel">
          <h2>任务进度</h2>
          <p class="muted">分析任务通过后端服务和 worker 在排队、运行、完成、失败之间流转。</p>
          <div class="toolbar"><button class="button secondary" type="button" data-action="recommendAnalysis">推荐分析方法</button></div>
        </article>
        <article class="panel wide dense">
          <h2>MNE / EEGLAB 模板库</h2>
          <table class="table">
            <thead><tr><th>模板</th><th>MNE 核心</th><th>EEGLAB 对应</th><th>输出</th><th>状态</th><th>估价</th></tr></thead>
            <tbody>${templateRows}</tbody>
          </table>
        </article>
        <article class="panel wide dense">
          <h2>模板边界</h2>
          <table class="table">
            <thead><tr><th>模板</th><th>V1 输出</th><th>暂不包含</th></tr></thead>
            <tbody>
              <tr><td>静息态 PSD</td><td>band_power.csv、参数 JSON、方法说明</td><td>高级连接性、自动诊断</td></tr>
              <tr><td>ERP / P300</td><td>erp_metrics.csv、事件窗口、方法说明</td><td>AI 判读、复杂统计模型</td></tr>
              <tr><td>C64RS BDF 元数据</td><td>${sampleDataset.eegChannelCount} EEG 通道、${sampleDataset.duration}、${sampleDataset.samplingRate}、${sampleDataset.annotationsCount} 条 annotations</td><td>暂不提交原始 BDF</td></tr>
            </tbody>
          </table>
        </article>
        <article class="panel wide dense">
          <h2>事件分布</h2>
          <table class="table">
            <thead><tr><th>Annotation</th><th>数量</th><th>ERP 意义</th></tr></thead>
            <tbody>
              ${psdPreview.events.descriptions
                .map((row) => `<tr><td>${row[0]}</td><td>${row[1]}</td><td>${row[0].includes("Focus") || row[0].includes("Patch") ? "候选事件，需要映射实验条件" : "记录/操作事件"}</td></tr>`)
                .join("")}
            </tbody>
          </table>
          <p class="muted">${psdPreview.events.readiness}</p>
        </article>
      </section>
    `;
  }
};
