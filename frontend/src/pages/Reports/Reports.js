export const Reports = {
  title: "报告中心",
  render() {
    return `
      <section class="grid">
        <article class="panel">
          <h2>单被试报告</h2>
          <p class="muted">HTML 报告汇总项目元数据、输入文件、分析参数、质控、图表和结果表。</p>
        </article>
        <article class="panel">
          <h2>结果包下载</h2>
          <p class="muted">报告 ZIP 是可带走的科研交付物，可用于论文、汇报和二次分析。</p>
          <div class="toolbar">
            <button class="button" type="button" data-action="createReport">生成报告</button>
            <button class="button secondary" type="button" data-action="downloadZip">下载 ZIP</button>
          </div>
        </article>
        <article class="panel wide">
          <h2>报告应包含</h2>
          <div class="workflow">
            <div class="workflow-step"><strong>项目概况</strong><p class="muted">项目名称、被试、任务类型。</p></div>
            <div class="workflow-step"><strong>输入文件</strong><p class="muted">文件名、格式、采样率、通道数。</p></div>
            <div class="workflow-step"><strong>分析参数</strong><p class="muted">滤波、epoch、baseline、频段。</p></div>
            <div class="workflow-step"><strong>结果交付</strong><p class="muted">图、表、HTML、复现文件。</p></div>
          </div>
        </article>
      </section>
    `;
  }
};
