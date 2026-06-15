import { expect, test } from "@playwright/test";

const customerNavChecks = [
  ["项目空间", "项目空间"],
  ["数据管理", "数据管理"],
  ["质控中心", "质控中心"],
  ["分析模板", "分析模板"],
  ["流程设计", "流程设计"],
  ["结果中心", "结果中心"],
  ["报告中心", "报告中心"],
  ["充值计费", "充值计费"]
];

const customerActionChecks = [
  ["项目空间", "新建科研项目", "已生成项目草稿"],
  ["项目空间", "导入演示数据", "已载入 C64RS BDF 示例元数据"],
  ["数据管理", "选择 EEG 文件", "已定位本地 BDF 示例文件"],
  ["数据管理", "上传事件 TSV", "已检查到 BDF annotations"],
  ["数据管理", "新增数据记录", "已创建 EEG 数据记录草稿"],
  ["数据管理", "编辑", "已打开 C64RS 示例数据编辑状态"],
  ["数据管理", "归档", "已将数据标记为归档"],
  ["数据管理", "删除", "已进入删除确认流程"],
  ["质控中心", "预览原始数据", "已打开前 5 秒原始波形"],
  ["质控中心", "运行预处理", "已创建滤波、重参考、坏段检查任务"],
  ["分析模板", "启动 PSD", "已通过 MNE 对前 30 秒 BDF 完成 PSD 烟测"],
  ["分析模板", "检查事件标记", "已识别 80 条 annotations"],
  ["分析模板", "推荐分析方法", "已根据事件锁定任务推荐 ERP/P300"],
  ["流程设计", "保存流程", "已保存 Metadata -> Preview -> Preprocess -> Analysis -> Report 流程草稿"],
  ["流程设计", "估算费用", "当前 C64RS 流程预计冻结 ¥68.00"],
  ["流程设计", "锁定参数", "已锁定 epoch、baseline、滤波、参考和输出 manifest 字段"],
  ["流程设计", "提交到队列", "已提交 metadata -> preview -> preprocess -> analysis -> report 队列"],
  ["报告中心", "生成报告", "已排队生成 HTML 科研报告"],
  ["报告中心", "下载 ZIP", "已准备结果包结构"],
  ["充值计费", "充值", "已创建 ¥1,000 充值订单"],
  ["充值计费", "申请发票", "已生成发票申请草稿"]
];

const adminActionChecks = [
  ["查看失败原因", "已打开失败任务复核队列"],
  ["处理发票", "已进入发票申请处理列表"],
  ["发布模板", "已将 ERP/P300 模板标记为可售卖"],
  ["暂停模板", "已暂停机器学习分类模板"],
  ["查看存储", "当前存储占用 128 GB"]
];

test("role entrance separates customer workspace and admin backend", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveTitle("QLanalyser 脑科学数据分析平台");
  await expect(page.getByText("QLanalyser 脑科学数据分析平台")).toBeVisible();
  await expect(page.getByRole("button", { name: "进入客户工作台" })).toBeVisible();
  await expect(page.getByRole("button", { name: "进入管理员后台" })).toBeVisible();

  await page.getByRole("button", { name: "进入客户工作台" }).click();
  await expect(page.getByRole("heading", { name: "项目空间" })).toBeVisible();
  await expect(page.locator(".status").filter({ hasText: "客户工作台" })).toBeVisible();
  await expect(page.getByRole("button", { name: "管理员后台" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "平台架构" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "压力测试" })).toHaveCount(0);

  for (const [navName, heading] of customerNavChecks) {
    await page.getByRole("button", { name: navName }).click();
    await expect(page.getByRole("heading", { name: heading })).toBeVisible();
  }

  await page.getByRole("button", { name: "数据管理" }).click();
  await expect(page.getByRole("cell", { name: "C64RS_390026040074_260531103644.bdf" })).toBeVisible();
  await expect(page.getByText("MNE 1.12.1 / preload=False")).toBeVisible();
  await expect(page.getByText("大文件上传架构")).toHaveCount(0);
  await expect(page.getByText("新增数据记录")).toBeVisible();
  await expect(page.locator("tbody tr")).toHaveCount(3);
  await page.getByRole("button", { name: "新增数据记录" }).click();
  await expect(page.locator("tbody tr")).toHaveCount(4);

  await page.getByRole("button", { name: "结果中心" }).click();
  await expect(page.getByText("Alpha / Theta")).toBeVisible();
  await expect(page.getByText("0.556")).toBeVisible();
  await expect(page.getByAltText("C64RS BDF PSD 概览图")).toBeVisible();
  await expect(page.getByAltText("C64RS BDF 原始波形预览图")).toBeVisible();
  await expect(page.getByAltText("C64RS BDF 事件分布图")).toBeVisible();

  await page.getByRole("button", { name: "分析模板" }).click();
  await expect(page.getByText("MNE / EEGLAB 模板库")).toBeVisible();
  await expect(page.getByText("机器学习分类")).toBeVisible();
  await expect(page.getByText("20 个常见脑电范式")).toHaveCount(0);
  await expect(page.getByText("FocusChange")).toBeVisible();

  await page.getByRole("button", { name: "报告中心" }).click();
  await expect(page.getByText("审稿人清单")).toHaveCount(0);
  await expect(page.getByText("单被试报告")).toBeVisible();
  await expect(page.getByText("结果包下载")).toBeVisible();

  for (const [navName, buttonName, expectedFeedback] of customerActionChecks) {
    await page.getByRole("button", { name: navName }).click();
    await page.getByRole("button", { name: buttonName, exact: true }).click();
    await expect(page.locator(".action-panel p.muted")).toContainText(expectedFeedback);
  }

  await page.getByRole("button", { name: "返回进入界面" }).click();
  await expect(page.getByText("QLanalyser 脑科学数据分析平台")).toBeVisible();

  await page.getByRole("button", { name: "进入管理员后台" }).click();
  await expect(page.getByRole("heading", { name: "管理员后台" })).toBeVisible();
  await expect(page.locator(".status").filter({ hasText: "管理员后台" })).toBeVisible();
  await expect(page.getByRole("button", { name: "项目空间" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "充值计费" })).toHaveCount(0);
  await expect(page.getByText("今日充值")).toBeVisible();
  await expect(page.getByText("Worker")).toBeVisible();
  await expect(page.getByText("分析模板定价")).toBeVisible();
  await expect(page.getByText("存储与上传策略")).toHaveCount(0);

  for (const [buttonName, expectedFeedback] of adminActionChecks) {
    await page.getByRole("button", { name: buttonName, exact: true }).click();
    await expect(page.locator(".action-panel p.muted")).toContainText(expectedFeedback);
  }

  await expect(page.locator(".action-log li")).toHaveCount(5);
});
