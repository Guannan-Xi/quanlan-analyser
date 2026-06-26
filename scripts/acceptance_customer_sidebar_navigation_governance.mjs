import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";

const require = createRequire(import.meta.url);
const { chromium } = require("../frontend/node_modules/playwright");

const TARGET_URL =
  process.env.QLANALYSER_FRONTEND_URL ||
  "http://127.0.0.1:4174/?customer_demo=login&api=http://127.0.0.1:8001/api";
const OUT_DIR =
  process.env.QLANALYSER_NAV_EVIDENCE_DIR ||
  path.resolve("work/release_evidence/20260625-sidebar-navigation");
const EVIDENCE_PATH = path.join(OUT_DIR, "sidebar_navigation_governance.json");

const checks = [];
const pass = (name, details = {}) => checks.push({ name, pass: true, details });
const fail = (name, details = {}) => checks.push({ name, pass: false, details });

function parseFirstRgb(value) {
  const match = /rgba?\((\d+),\s*(\d+),\s*(\d+)/.exec(value || "");
  return match ? match.slice(1, 4).map(Number) : null;
}

function rgbToHue([r, g, b]) {
  const rn = r / 255;
  const gn = g / 255;
  const bn = b / 255;
  const max = Math.max(rn, gn, bn);
  const min = Math.min(rn, gn, bn);
  const delta = max - min;
  if (delta === 0) return 0;
  let hue =
    max === rn
      ? ((gn - bn) / delta) % 6
      : max === gn
        ? (bn - rn) / delta + 2
        : (rn - gn) / delta + 4;
  hue *= 60;
  return hue < 0 ? hue + 360 : hue;
}

function assertNotGreenOrTeal(name, cssValue) {
  const rgb = parseFirstRgb(cssValue);
  if (!rgb) {
    fail(`${name}-rgb-readable`, { value: cssValue });
    return;
  }
  const hue = Math.round(rgbToHue(rgb));
  const looksGreenOrTeal = hue >= 110 && hue <= 185;
  looksGreenOrTeal
    ? fail(`${name}-not-green-or-teal`, { rgb, hue, value: cssValue })
    : pass(`${name}-not-green-or-teal`, { rgb, hue, value: cssValue });
}

async function run() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    await page.goto(TARGET_URL, { waitUntil: "domcontentloaded", timeout: 30000 });
    await page.evaluate(() => {
      document.querySelector("#loginScreen")?.setAttribute("hidden", "");
      document.querySelector("#appShell")?.removeAttribute("hidden");
      document.body.dataset.role = "customer";
      document.querySelectorAll('[data-role="admin"]').forEach((node) => {
        node.setAttribute("hidden", "");
        node.setAttribute("aria-hidden", "true");
      });
      document.querySelectorAll('[data-role="customer"]').forEach((node) => {
        node.removeAttribute("hidden");
        node.setAttribute("aria-hidden", "false");
      });
    });

    const visibleText = await page.locator(".sidebar").innerText({ timeout: 10000 });
    ["项目管理", "数据管理", "数据准备", "分析任务", "结果查看", "报告交付", "个人中心"].forEach((copy) => {
      visibleText.includes(copy) ? pass(`customer-nav-visible:${copy}`) : fail(`customer-nav-visible:${copy}`);
    });
    ["后台总览", "任务运营", "财务管理", "系统状态"].forEach((copy) => {
      visibleText.includes(copy) ? fail(`admin-nav-hidden:${copy}`) : pass(`admin-nav-hidden:${copy}`);
    });

    const style = await page.evaluate(() => {
      const sidebar = getComputedStyle(document.querySelector(".sidebar"));
      const brandMark = getComputedStyle(document.querySelector(".brand-mark"));
      const active = getComputedStyle(document.querySelector(".nav-item.active"));
      const activeIcon = getComputedStyle(document.querySelector(".nav-item.active svg"));
      return {
        sidebarBackground: sidebar.backgroundImage || sidebar.backgroundColor,
        sidebarBackgroundColor: sidebar.backgroundColor,
        brandMarkBackground: brandMark.backgroundImage || brandMark.backgroundColor,
        activeBackground: active.backgroundImage || active.backgroundColor,
        activeColor: active.color,
        activeIconColor: activeIcon.color,
        activeBoxShadow: active.boxShadow,
      };
    });
    style.sidebarBackground.includes("linear-gradient")
      ? pass("sidebar-uses-governed-gradient", { sidebarBackground: style.sidebarBackground })
      : fail("sidebar-uses-governed-gradient", { sidebarBackground: style.sidebarBackground });
    style.sidebarBackground.includes("8, 24, 51") || style.sidebarBackground.includes("11, 35, 66")
      ? pass("sidebar-uses-blue-navy-not-green", { sidebarBackground: style.sidebarBackground })
      : fail("sidebar-uses-blue-navy-not-green", { sidebarBackground: style.sidebarBackground });
    /18,\s*59,\s*66|13,\s*46,\s*52|10,\s*37,\s*43|44,\s*150,\s*220|80,\s*167,\s*229|93,\s*198,\s*243|143,\s*216,\s*212/.test(style.sidebarBackground)
      ? fail("sidebar-no-green-teal-legacy-colors", { sidebarBackground: style.sidebarBackground })
      : pass("sidebar-no-green-teal-legacy-colors", { sidebarBackground: style.sidebarBackground });
    assertNotGreenOrTeal("brand-mark", style.brandMarkBackground);
    assertNotGreenOrTeal("active-nav", style.activeBackground);
    assertNotGreenOrTeal("active-icon", style.activeIconColor);
    style.activeBoxShadow.includes("inset")
      ? pass("active-nav-has-left-accent", { activeBoxShadow: style.activeBoxShadow })
      : fail("active-nav-has-left-accent", { activeBoxShadow: style.activeBoxShadow });

    const screenshot = path.join(OUT_DIR, "sidebar_navigation.png");
    await page.screenshot({ path: screenshot, fullPage: true });
    const report = {
      script: path.basename(new URL(import.meta.url).pathname),
      target_url: TARGET_URL,
      checked_at: new Date().toISOString(),
      checks,
      style,
      screenshot,
      passed: checks.every((item) => item.pass),
    };
    fs.writeFileSync(EVIDENCE_PATH, `${JSON.stringify(report, null, 2)}\n`, "utf8");
    console.log(JSON.stringify(report, null, 2));
    if (!report.passed) process.exit(1);
  } finally {
    await browser.close();
  }
}

run().catch((error) => {
  console.error(error.stack || error.message);
  process.exit(1);
});
