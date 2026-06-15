import { currency } from "../../data/platformModel.js";

export const Workflow = {
  title: "流程设计",
  render(state) {
    return `
      <section class="grid">
        <article class="panel wide">
          <h2>分析流程</h2>
          <div class="workflow">
            ${state.workflow.steps
              .map((step, index) => `<div class="workflow-step"><strong>${index + 1}. ${step[0]}</strong><p class="muted">${step[1]}</p></div>`)
              .join("")}
          </div>
          <div class="toolbar">
            <button class="button" type="button" data-action="saveWorkflow">保存流程</button>
            <button class="button secondary" type="button" data-action="estimateCost">估算费用</button>
          </div>
          <p class="muted">保存状态：${state.workflow.saved ? "已保存" : "未保存"}；预估费用：${currency(state.workflow.estimatedCost)}</p>
        </article>
        <article class="panel wide dense">
          <h2>可选模块</h2>
          <table class="table">
            <thead><tr><th>模块</th><th>状态</th><th>说明</th></tr></thead>
            <tbody>
              <tr><td>MNE Raw Preview</td><td><span class="badge ok">已接入</span></td><td>原始波形、PSD、events 预览</td></tr>
              <tr><td>Preprocess</td><td><span class="badge warn">表单原型</span></td><td>滤波、重参考、坏段/坏道、ICA</td></tr>
              <tr><td>PSD</td><td><span class="badge ok">已烟测</span></td><td>Welch 1-40 Hz</td></tr>
              <tr><td>ERP</td><td><span class="badge warn">待映射事件</span></td><td>需要确认实验条件语义</td></tr>
              <tr><td>EEGLAB-compatible</td><td><span class="badge">规划中</span></td><td>导入 SET、对齐 EEGLAB 方法说明</td></tr>
            </tbody>
          </table>
        </article>
        <article class="panel wide">
          <h2>分析向导闭环</h2>
          <div class="workflow">
            <div class="workflow-step"><strong>1. 选择范式</strong><p class="muted">例如 Oddball、Stroop、静息态、SSVEP，决定事件映射和主分析。</p></div>
            <div class="workflow-step"><strong>2. 读取数据</strong><p class="muted">上传原始文件和事件表，自动抽取通道、采样率、时长和 annotations。</p></div>
            <div class="workflow-step"><strong>3. 推荐方法</strong><p class="muted">根据任务类型和事件标记推荐 PSD、ERP 或时频分析；参数可在执行前锁定。</p></div>
            <div class="workflow-step"><strong>4. 冻结费用</strong><p class="muted">按模板估价冻结余额，任务失败或取消时回滚未消耗金额。</p></div>
            <div class="workflow-step"><strong>5. 运行队列</strong><p class="muted">metadata、preview、preprocess、analysis、report 进入 worker。</p></div>
            <div class="workflow-step"><strong>6. 交付结果</strong><p class="muted">图表、CSV、HTML、方法文本和复现 manifest 打包下载。</p></div>
          </div>
          <div class="toolbar">
            <button class="button secondary" type="button" data-action="lockParameters">锁定参数</button>
            <button class="button secondary" type="button" data-action="submitQueue">提交到队列</button>
          </div>
        </article>
      </section>
    `;
  }
};
