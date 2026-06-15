import { pages } from "./pages/index.js";
import { platformState, currency } from "./data/platformModel.js";

const app = document.querySelector("#app");
const PRODUCT_TITLE = "QLanalyser 脑科学数据分析平台";
const BRAND_SIGNATURE = "全澜脑科学® QuanLan BrainScience®";

document.title = PRODUCT_TITLE;

const customerNavItems = [
  ["Projects", "项目空间"],
  ["Data", "数据管理"],
  ["QC", "质控中心"],
  ["Analysis", "分析模板"],
  ["Workflow", "流程设计"],
  ["Results", "结果中心"],
  ["Reports", "报告中心"],
  ["Billing", "充值计费"]
];

const adminNavItems = [
  ["Admin", "管理员后台"]
];

let activeRole = "Landing";
let activePage = "Projects";
let lastAction = "等待操作";
const actionLog = [
  { time: new Date().toLocaleTimeString("zh-CN", { hour12: false }), action: "打开工作台", result: "界面已加载" }
];

const actionHandlers = {
  createProject: () => ["创建科研项目", "已生成项目草稿：新建 EEG 科研项目"],
  importDemo: () => ["导入演示数据", "已载入 C64RS BDF 示例元数据"],
  chooseEeg: () => ["选择 EEG 文件", "已定位本地 BDF 示例文件，等待正式上传组件接入"],
  uploadEvents: () => ["上传事件 TSV", "已检查到 BDF annotations，可继续补充 TSV 事件文件"],
  createData: () => {
    const nextIndex = platformState.files.length + 1;
    platformState.files.push({
      id: `new-${nextIndex}`,
      filename: `new_upload_${nextIndex}.bdf`,
      format: "BDF",
      subject: `sub-new-${nextIndex}`,
      status: "草稿",
      risk: "等待上传原始文件",
      active: true
    });
    return ["新增数据", "已创建 EEG 数据记录草稿"];
  },
  editData: () => {
    const item = platformState.files.find((file) => file.id === "demo-bdf");
    if (item) item.status = "编辑中";
    return ["编辑数据", "已打开 C64RS 示例数据编辑状态"];
  },
  archiveData: () => {
    const item = platformState.files.find((file) => file.id === "sub-02");
    if (item) item.status = "已归档";
    return ["归档数据", "已将数据标记为归档，保留审计记录"];
  },
  deleteData: () => {
    const item = platformState.files.find((file) => file.id === "resting-demo");
    if (item) item.status = "待删除确认";
    return ["删除数据", "已进入删除确认流程，原始数据不会直接物理删除"];
  },
  startPsd: () => {
    platformState.wallet.frozen += 28;
    return ["启动 PSD", "已通过 MNE 对前 30 秒 BDF 完成 PSD 烟测"];
  },
  checkEvents: () => ["检查事件标记", "已识别 80 条 annotations，仍需确认任务语义"],
  recommendAnalysis: () => ["推荐分析方法", "已根据事件锁定任务推荐 ERP/P300，并保留 PSD 作为快速质控"],
  runPreprocess: () => {
    platformState.wallet.frozen += 20;
    return ["运行预处理", "已创建滤波、重参考、坏段检查任务，预计扣费 ¥20.00"];
  },
  previewRaw: () => ["预览原始数据", "已打开前 5 秒原始波形、PSD 和事件分布预览"],
  createReport: () => ["生成报告", "已排队生成 HTML 科研报告"],
  downloadZip: () => ["下载 ZIP", "已准备结果包结构，正式下载待后端打包接入"],
  recharge: () => {
    platformState.wallet.balance += 1000;
    return ["充值", `已创建 ¥1,000 充值订单，当前余额 ${currency(platformState.wallet.balance)}`];
  },
  invoice: () => {
    platformState.wallet.invoiceQueue += 1;
    return ["申请发票", "已生成发票申请草稿，管理员后台可处理"];
  },
  saveWorkflow: () => {
    platformState.workflow.saved = true;
    return ["保存流程", "已保存 Metadata -> Preview -> Preprocess -> Analysis -> Report 流程草稿"];
  },
  estimateCost: () => {
    platformState.wallet.frozen = platformState.workflow.estimatedCost;
    return ["估算费用", "当前 C64RS 流程预计冻结 ¥68.00"];
  },
  lockParameters: () => ["锁定参数", "已锁定 epoch、baseline、滤波、参考和输出 manifest 字段"],
  submitQueue: () => {
    platformState.admin.runningTasks += 1;
    platformState.wallet.frozen = platformState.workflow.estimatedCost;
    return ["提交到队列", "已提交 metadata -> preview -> preprocess -> analysis -> report 队列"];
  },
  reviewFailedTask: () => {
    platformState.admin.failedTasks = Math.max(0, platformState.admin.failedTasks - 1);
    return ["查看失败原因", "已打开失败任务复核队列"];
  },
  adminInvoice: () => {
    platformState.admin.invoiceQueue = Math.max(0, platformState.admin.invoiceQueue - 1);
    return ["处理发票", "已进入发票申请处理列表"];
  },
  publishTemplate: () => ["发布模板", "已将 ERP/P300 模板标记为可售卖，等待管理员二次确认"],
  pauseTemplate: () => ["暂停模板", "已暂停机器学习分类模板，避免未验证方法被客户购买"],
  storageAudit: () => ["查看存储", "当前存储占用 128 GB，原始数据未提交到 Git"]
};

function renderNav() {
  const navItems = activeRole === "Admin" ? adminNavItems : customerNavItems;
  return navItems
    .map(([key, label]) => {
      const active = key === activePage ? " active" : "";
      return `<button class="nav-item${active}" data-page="${key}" type="button">${label}</button>`;
    })
    .join("");
}

function renderLanding() {
  app.innerHTML = `
    <main class="entry-screen">
      <button class="entry-admin-link" type="button" data-enter-role="Admin" aria-label="进入管理员后台">管理</button>
      <section class="entry-shell">
        <div class="entry-wordmark" aria-label="QLanalyser">
          <strong>QLanalyser</strong>
          <span>${BRAND_SIGNATURE}</span>
        </div>
        <h1>${PRODUCT_TITLE}</h1>
        <p class="entry-lead">面向科研客户的在线付费脑电分析工作台，覆盖数据管理、预处理、可视化结果和报告交付。</p>
        <section class="entry-customer-panel" aria-label="客户入口">
          <div>
            <span class="badge ok">客户工作台</span>
            <h2>开始新的脑电分析项目</h2>
            <p>上传原始数据，配置预处理与分析流程，查看可视化结果并下载报告。</p>
          </div>
          <button class="button entry-primary-action" type="button" data-enter-role="Customer">进入客户工作台</button>
        </section>
        <div class="entry-proof-grid" aria-label="平台能力">
          <div><strong>数据</strong><span>BDF / EDF / SET 项目化管理</span></div>
          <div><strong>分析</strong><span>MNE / EEGLAB 流程模板</span></div>
          <div><strong>交付</strong><span>结果可视化、报告与计费</span></div>
        </div>
      </section>
    </main>
  `;

  document.querySelectorAll("[data-enter-role]").forEach((button) => {
    button.addEventListener("click", () => {
      activeRole = button.dataset.enterRole;
      activePage = activeRole === "Admin" ? "Admin" : "Projects";
      lastAction = activeRole === "Admin" ? "已进入管理员后台" : "已进入客户工作台";
      render();
    });
  });
}

function render() {
  if (activeRole === "Landing") {
    renderLanding();
    return;
  }

  const page = pages[activePage];
  const roleLabel = activeRole === "Admin" ? "管理员后台" : "客户工作台";
  app.innerHTML = `
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-copy">
          <strong>QLanalyser</strong>
          <span>${BRAND_SIGNATURE}</span>
        </div>
      </div>
      <nav>${renderNav()}</nav>
      <button class="switch-entry" type="button" data-switch-entry>返回进入界面</button>
    </aside>
    <main class="workspace">
      <header class="topbar">
        <div>
          <p class="eyebrow">在线付费 EEG 数据分析平台</p>
          <h1>${page.title}</h1>
        </div>
        <div class="top-actions" aria-label="当前状态">
          <span class="status muted-status">余额 ${currency(platformState.wallet.balance)}</span>
          <span class="status">${roleLabel}</span>
        </div>
      </header>
      ${page.render(platformState)}
      <section class="panel wide action-panel" aria-live="polite">
        <div>
          <h2>操作反馈</h2>
          <p class="muted">${lastAction}</p>
        </div>
        <ol class="action-log">
          ${actionLog
            .slice(-5)
            .map((item) => `<li><span>${item.time}</span><strong>${item.action}</strong><em>${item.result}</em></li>`)
            .join("")}
        </ol>
      </section>
    </main>
  `;

  document.querySelectorAll("[data-page]").forEach((button) => {
    button.addEventListener("click", () => {
      activePage = button.dataset.page;
      render();
    });
  });

  document.querySelector("[data-switch-entry]").addEventListener("click", () => {
    activeRole = "Landing";
    activePage = "Projects";
    lastAction = "等待操作";
    render();
  });

  document.querySelectorAll("[data-action]").forEach((button) => {
    button.addEventListener("click", () => {
      const handler = actionHandlers[button.dataset.action];
      const [action, result] = handler ? handler() : ["未知操作", "已记录"];
      lastAction = `${action}：${result}`;
      actionLog.push({
        time: new Date().toLocaleTimeString("zh-CN", { hour12: false }),
        action,
        result
      });
      render();
    });
  });
}

render();
