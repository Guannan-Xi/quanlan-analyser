import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const { chromium } = require("../frontend/node_modules/playwright");
const url = "http://127.0.0.1:4174/index.html?customer_demo=auto&api=http%3A%2F%2F127.0.0.1%3A8001%2Fapi";
const browser = await chromium.launch({ headless: true, channel: "msedge" });
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }});
const logs = [];
page.on("console", msg => logs.push({ type: msg.type(), text: msg.text() }));
page.on("pageerror", err => logs.push({ type: "pageerror", text: err.stack || err.message }));
await page.goto(url, { waitUntil: "domcontentloaded", timeout: 30000 });
await page.waitForTimeout(5000);
const state = await page.evaluate(() => {
  const main = document.querySelector(".main");
  const appShell = document.querySelector("#appShell");
  const login = document.querySelector("#loginView, .login, [data-view='login']");
  return {
    title: document.title,
    bodyText: document.body.innerText.slice(0, 3000),
    bodyClass: document.body.className,
    mainHidden: main ? main.hidden : null,
    mainClass: main ? main.className : null,
    mainDisplay: main ? getComputedStyle(main).display : null,
    appShellHidden: appShell ? appShell.hidden : null,
    appShellClass: appShell ? appShell.className : null,
    appShellDisplay: appShell ? getComputedStyle(appShell).display : null,
    loginText: login ? login.innerText.slice(0,1000) : null,
    scriptCount: document.scripts.length,
    localStorageKeys: Object.keys(localStorage).slice(0, 50),
  };
});
console.log(JSON.stringify({ url, state, logs }, null, 2));
await page.screenshot({ path: "D:/Quanlan/Codes/Python/quanlan-analyser-official/work/release_evidence/probe_app_shell.png", fullPage: true });
await browser.close();
