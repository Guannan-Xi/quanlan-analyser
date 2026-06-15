import { currency } from "../../data/platformModel.js";
import { analysisTemplates } from "../../data/productLibrary.js";

export const Admin = {
  title: "管理员后台",
  render(state) {
    const admin = state.admin;
    const templateRows = analysisTemplates
      .slice(0, 5)
      .map((item) => `<tr><td>${item.name}</td><td>${item.engine}</td><td>${currency(item.cost)}</td><td><span class="badge">${item.status}</span></td></tr>`)
      .join("");
    return `
      <section class="grid">
        <article class="panel"><h2>客户数</h2><p class="metric">${admin.customers}</p><p class="muted">含试用和付费客户</p></article>
        <article class="panel"><h2>今日充值</h2><p class="metric">${currency(admin.rechargeToday)}</p><p class="muted">线上充值入账</p></article>
        <article class="panel"><h2>今日消耗</h2><p class="metric">${currency(admin.consumptionToday)}</p><p class="muted">分析任务扣费</p></article>
        <article class="panel"><h2>Worker</h2><p class="metric">${admin.workerStatus}</p><p class="muted">队列任务 ${admin.runningTasks}，失败 ${admin.failedTasks}</p></article>
        <article class="panel wide dense">
          <h2>运营任务</h2>
          <table class="table">
            <thead><tr><th>事项</th><th>状态</th><th>操作</th></tr></thead>
            <tbody>
              <tr><td>失败任务复核</td><td><span class="badge warn">${admin.failedTasks} 条</span></td><td><button class="button secondary" type="button" data-action="reviewFailedTask">查看失败原因</button></td></tr>
              <tr><td>发票申请</td><td><span class="badge">${admin.invoiceQueue} 条</span></td><td><button class="button secondary" type="button" data-action="adminInvoice">处理发票</button></td></tr>
              <tr><td>存储占用</td><td><span class="badge ok">${admin.storageUsed}</span></td><td><button class="button secondary" type="button" data-action="storageAudit">查看存储</button></td></tr>
            </tbody>
          </table>
        </article>
        <article class="panel wide dense">
          <h2>分析模板定价</h2>
          <table class="table">
            <thead><tr><th>模板</th><th>引擎</th><th>单次估价</th><th>状态</th></tr></thead>
            <tbody>${templateRows}</tbody>
          </table>
          <div class="toolbar">
            <button class="button secondary" type="button" data-action="publishTemplate">发布模板</button>
            <button class="button secondary" type="button" data-action="pauseTemplate">暂停模板</button>
          </div>
        </article>
      </section>
    `;
  }
};
