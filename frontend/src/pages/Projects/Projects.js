import { sampleDataset } from "../../data/sampleDataset.js";
import { paradigmLibrary } from "../../data/productLibrary.js";

export const Projects = {
  title: "项目空间",
  render() {
    const beginnerParadigms = paradigmLibrary.filter((row) => row[3] === "适合新手").slice(0, 4);
    return `
      <section class="grid">
        <article class="panel">
          <h2>进行中的项目</h2>
          <p class="metric">3</p>
          <p class="muted">科研项目用于组织被试、session、EEG 文件、分析任务和结果报告。</p>
          <div class="toolbar">
            <button class="button" type="button" data-action="createProject">新建科研项目</button>
            <button class="button secondary" type="button" data-action="importDemo">导入演示数据</button>
          </div>
        </article>
        <article class="panel">
          <h2>项目类型</h2>
          <ul class="list">
            <li><span>静息态 EEG</span><strong>PSD</strong></li>
            <li><span>Oddball ERP</span><strong>P300</strong></li>
            <li><span>自定义实验</span><strong>手动配置</strong></li>
          </ul>
        </article>
        <article class="panel">
          <h2>可选范式库</h2>
          <p class="metric">${paradigmLibrary.length}</p>
          <p class="muted">覆盖常见静息态、ERP、时频和认知任务分析。</p>
        </article>
        <article class="panel">
          <h2>新手推荐</h2>
          <ul class="list">
            ${beginnerParadigms.map((row) => `<li><span>${row[0]}</span><strong>${row[1]}</strong></li>`).join("")}
          </ul>
        </article>
        <article class="panel wide">
          <h2>科研分析流程</h2>
          <div class="workflow" aria-label="科研分析流程">
            <div class="workflow-step"><strong>1. 创建项目</strong><span class="badge ok">已就绪</span><p class="muted">建立课题、被试分组和任务类型。</p></div>
            <div class="workflow-step"><strong>2. 上传 EEG</strong><span class="badge warn">待上传</span><p class="muted">读取格式、采样率、通道数和事件文件。</p></div>
            <div class="workflow-step"><strong>3. 运行分析</strong><span class="badge">PSD / ERP</span><p class="muted">先交付静息态 PSD 与 Oddball ERP。</p></div>
            <div class="workflow-step"><strong>4. 下载报告</strong><span class="badge">HTML / ZIP</span><p class="muted">带走图表、CSV、参数和方法学说明。</p></div>
          </div>
        </article>
        <article class="panel wide dense">
          <h2>项目任务概览</h2>
          <table class="table">
            <thead><tr><th>项目</th><th>数据</th><th>分析</th><th>报告</th><th>下一步</th></tr></thead>
            <tbody>
              <tr><td>${sampleDataset.label}</td><td><span class="badge ok">${sampleDataset.eegChannelCount} EEG 通道</span></td><td>MNE 元数据已识别</td><td>待生成</td><td>接入 PSD/ERP 信号分析</td></tr>
              <tr><td>静息态 EEG 示例</td><td><span class="badge ok">1 文件</span></td><td>PSD 已完成</td><td>可下载</td><td>补充方法说明</td></tr>
              <tr><td>自定义实验</td><td><span class="badge warn">未上传</span></td><td>未开始</td><td>未开始</td><td>上传原始文件</td></tr>
            </tbody>
          </table>
        </article>
      </section>
    `;
  }
};
