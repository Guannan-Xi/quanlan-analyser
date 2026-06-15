import { currency, pricing } from "../../data/platformModel.js";

export const Billing = {
  title: "充值计费",
  render(state) {
    const ledger = [
      ["充值", "+¥ 1,000.00", "已到账"],
      ["C64RS Metadata", "-¥ 2.00", "已扣费"],
      ["PSD 烟测", "-¥ 28.00", "已扣费"],
      ["报告包预留", currency(state.wallet.frozen), "冻结中"]
    ];

    return `
      <section class="grid">
        <article class="panel">
          <h2>账户余额</h2>
          <p class="metric">${currency(state.wallet.balance)}</p>
          <p class="muted">冻结金额 ${currency(state.wallet.frozen)}，今日消耗 ${currency(state.wallet.spentToday)}</p>
          <div class="toolbar">
            <button class="button" type="button" data-action="recharge">充值</button>
            <button class="button secondary" type="button" data-action="invoice">申请发票</button>
          </div>
        </article>
        <article class="panel">
          <h2>计费规则</h2>
          <ul class="list">
            ${pricing.map((row) => `<li><span>${row[0]}</span><strong>${row[1]}</strong></li>`).join("")}
          </ul>
        </article>
        <article class="panel wide dense">
          <h2>消费台账</h2>
          <table class="table">
            <thead><tr><th>项目</th><th>金额</th><th>状态</th></tr></thead>
            <tbody>
              ${ledger.map((row) => `<tr><td>${row[0]}</td><td>${row[1]}</td><td>${row[2]}</td></tr>`).join("")}
            </tbody>
          </table>
        </article>
      </section>
    `;
  }
};

