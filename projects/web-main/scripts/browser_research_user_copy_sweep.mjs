import fs from "node:fs";
import path from "node:path";
import { chromium, chromiumLaunchOptions } from "./lib/playwright_runtime.mjs";

const DEFAULT_URLS = [
  "http://127.0.0.1:4174/?customer_demo=auto&teaching_demo=auto&api=http%3A%2F%2F127.0.0.1%3A8001%2Fapi&v=copy-browser-sweep#dashboard",
  "http://127.0.0.1:4174/?customer_demo=auto&teaching_demo=auto&api=http%3A%2F%2F127.0.0.1%3A8001%2Fapi&v=copy-browser-sweep#analysis",
  "http://127.0.0.1:4174/?customer_demo=auto&teaching_demo=auto&api=http%3A%2F%2F127.0.0.1%3A8001%2Fapi&v=copy-browser-sweep#workflow",
  "http://127.0.0.1:4174/?customer_demo=auto&teaching_demo=auto&api=http%3A%2F%2F127.0.0.1%3A8001%2Fapi&v=copy-browser-sweep#epilepsyWorkbenchInline",
];

const TARGET_URLS = (process.env.QLANALYSER_COPY_SWEEP_URLS || "")
  .split(/\s*,\s*/)
  .map((item) => item.trim())
  .filter(Boolean);

const URLS = TARGET_URLS.length ? TARGET_URLS : DEFAULT_URLS;
const OUT_DIR = process.env.QLANALYSER_COPY_SWEEP_OUT_DIR
  || path.resolve("work/release_evidence/20260701-research-user-copy-governance");
const OUT_FILE = path.join(OUT_DIR, "browser_visible_copy_sweep.json");

const forbiddenPositiveClinicalTerms = [
  "自动诊断",
  "确诊为",
  "治疗建议",
  "临床分诊",
  "医疗决策",
  "一键诊断",
  "智能判断",
];

const forbiddenEpilepsyTerms = [
  "癫痫分期",
  "癫痫样事件分期",
  "开始分期",
  "分期波形",
];

const discouragedTerms = [
  "正在读取真实波形",
  "不会用旧窗口伪装当前数据",
  "请选择一段真实波形",
  "教学模式",
  "教学数据",
  "教学 EDF",
  "教学样本",
  "教学步骤",
  "结束教学",
];

function isExplicitBoundaryText(text) {
  return text.includes("不用于") || text.includes("不作为") || text.includes("不得用于") || text.includes("不能用于");
}

function collectHits(text, terms, { allowBoundary = false } = {}) {
  const hits = [];
  const normalized = String(text || "").replace(/\s+/g, " ").trim();
  for (const term of terms) {
    let cursor = 0;
    while (true) {
      const index = normalized.indexOf(term, cursor);
      if (index === -1) break;
      const excerpt = normalized.slice(Math.max(0, index - 80), Math.min(normalized.length, index + term.length + 80));
      if (!(allowBoundary && isExplicitBoundaryText(excerpt))) {
        hits.push({ term, index, excerpt });
      }
      cursor = index + term.length;
    }
  }
  return hits;
}

async function sweepPage(page, url) {
  const result = {
    url,
    status: "pending",
    final_url: "",
    title: "",
    hash: "",
    body_text_length: 0,
    active_views: [],
    hits: {
      forbidden_positive_clinical: [],
      forbidden_epilepsy_terms: [],
      discouraged_terms: [],
      mojibake: [],
    },
  };
  try {
    await page.goto(url, { waitUntil: "domcontentloaded", timeout: 45000 });
    await page.waitForTimeout(1600);
    const state = await page.evaluate(() => {
      const text = document.body?.innerText || "";
      return {
        title: document.querySelector("#viewTitle")?.textContent?.trim() || document.title,
        hash: window.location.hash || "",
        finalUrl: window.location.href,
        bodyText: text,
        activeViews: Array.from(document.querySelectorAll(".view.active")).map((node) => node.id),
      };
    });
    result.status = "loaded";
    result.final_url = state.finalUrl;
    result.title = state.title;
    result.hash = state.hash;
    result.body_text_length = state.bodyText.length;
    result.active_views = state.activeViews;
    result.hits.forbidden_positive_clinical = collectHits(state.bodyText, forbiddenPositiveClinicalTerms, { allowBoundary: true });
    result.hits.forbidden_epilepsy_terms = collectHits(state.bodyText, forbiddenEpilepsyTerms);
    result.hits.discouraged_terms = collectHits(state.bodyText, discouragedTerms);
    result.hits.mojibake = collectHits(state.bodyText, ["锟", "�", "????"]);
  } catch (error) {
    result.status = "error";
    result.error = error.message || String(error);
  }
  return result;
}

async function main() {
  const browser = await chromium.launch(chromiumLaunchOptions({ headless: true }));
  const context = await browser.newContext({ viewport: { width: 1440, height: 1100 } });
  const page = await context.newPage();
  const pages = [];
  try {
    for (const url of URLS) {
      pages.push(await sweepPage(page, url));
    }
  } finally {
    await browser.close();
  }
  const failed = [];
  for (const item of pages) {
    if (item.status !== "loaded") failed.push(`page_load_failed:${item.url}`);
    for (const [key, hits] of Object.entries(item.hits || {})) {
      if (Array.isArray(hits) && hits.length) failed.push(`${key}:${item.url}`);
    }
  }
  const result = {
    script: "browser_research_user_copy_sweep.mjs",
    generated_at: new Date().toISOString(),
    status: failed.length ? "failed" : "passed",
    urls: URLS,
    pages,
    failed,
    notes: [
      "Browser-visible DOM copy sweep for research-user wording.",
      "Positive clinical terms are allowed only inside explicit negative boundary text.",
      "This script checks visible body text, not historical documentation.",
    ],
  };
  fs.mkdirSync(OUT_DIR, { recursive: true });
  fs.writeFileSync(OUT_FILE, `${JSON.stringify(result, null, 2)}\n`, "utf8");
  console.log(JSON.stringify(result, null, 2));
  if (failed.length) process.exit(1);
}

main().catch((error) => {
  console.error(error.stack || error.message);
  process.exit(1);
});
