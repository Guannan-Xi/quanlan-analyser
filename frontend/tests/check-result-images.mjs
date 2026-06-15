import { chromium } from "@playwright/test";

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
await page.goto("http://127.0.0.1:4174/");
await page.getByRole("button", { name: "进入客户工作台" }).click();
await page.getByRole("button", { name: "结果中心" }).click();
const images = await page.locator("figure img").evaluateAll((imgs) =>
  imgs.map((img) => ({
    alt: img.alt,
    width: img.naturalWidth,
    height: img.naturalHeight,
    renderedWidth: img.clientWidth,
    renderedHeight: img.clientHeight
  }))
);
const captions = await page.locator("figcaption").evaluateAll((els) => els.map((el) => el.innerText));
await browser.close();
console.log(JSON.stringify({ images, captions }, null, 2));
