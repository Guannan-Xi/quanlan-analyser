import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";
const require = createRequire(import.meta.url);
const { chromium } = require("../frontend/node_modules/playwright");
const API_BASE = process.env.QLANALYSER_API_BASE_URL || "http://127.0.0.1:8001/api";
const FRONTEND_URL = process.env.QLANALYSER_FRONTEND_URL || `http://127.0.0.1:4174/index.html?customer_demo=auto&api=${encodeURIComponent(API_BASE)}`;
const OUT_DIR = path.resolve("work/release_evidence/20260627-teaching-sandbox-mode");
const OUT_JSON = path.join(OUT_DIR, "teaching_sandbox_mode_e2e.json");
const SCREENSHOT = path.join(OUT_DIR, "teaching_sandbox_after_guide.png");
function localBrowserExecutable(){return ["C:/Program Files/Microsoft/Edge/Application/msedge.exe","C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"].find(fs.existsSync)||"";}
const checks=[]; const add=(name,pass,details={})=>checks.push({name,pass:Boolean(pass),details});
fs.mkdirSync(OUT_DIR,{recursive:true});
const browser=await chromium.launch({headless:true,...(localBrowserExecutable()?{executablePath:localBrowserExecutable()}:{})});
const page=await browser.newPage({viewport:{width:1440,height:1000}});
try{
 await page.goto(FRONTEND_URL,{waitUntil:"domcontentloaded",timeout:60000});
 await page.waitForSelector("#appShell, #loginScreen",{timeout:30000});
 if(await page.locator("#customerLoginBtn").isVisible().catch(()=>false)) await page.click("#customerLoginBtn");
 await page.waitForSelector("#appShell:not([hidden]), .main",{timeout:30000});
 await page.click("#teachingModeBtn");
 await page.waitForSelector("#teachingOverlay.active",{timeout:60000});
 for(let i=0;i<8;i+=1){
   const active=await page.locator("#teachingOverlay.active").isVisible().catch(()=>false);
   if(!active) break;
   await page.locator('#teachingOverlay [data-teaching-action="next"].primary-btn').click({force:true});
   await page.waitForTimeout(250);
 }
 await page.waitForFunction(()=>document.body.classList.contains("teaching-sandbox-active") && !document.querySelector("#teachingOverlay.active"),null,{timeout:30000});
 const state=await page.evaluate(()=>({
   banner:document.querySelector("#teachingSandboxBanner")?.innerText||"",
   button:document.querySelector("#teachingModeBtn")?.innerText||"",
   hash:location.hash,
   activeViews:[...document.querySelectorAll(".view.active")].map(n=>n.id),
   body:document.body.innerText,
   selectedFile:[...document.querySelectorAll("#prepDataQueue .selected")].map(n=>n.innerText).join("\n"),
   canvasRect:(()=>{const r=document.querySelector("#eegCanvas")?.getBoundingClientRect();return r?{w:r.width,h:r.height}:null})()
 }));
 add("guide_finish_keeps_teaching_sandbox", state.banner.includes("教学模式") && state.button.includes("返回普通模式"), state);
 add("demo_data_still_selected", state.body.includes("teaching_oddball_with_montage_raw.fif") && state.selectedFile.includes("teaching_oddball"), state);
 add("does_not_require_upload_after_guide", !/上传 EEG 数据|请上传|没有上传/.test(state.body), {bodyHead:state.body.slice(0,1500)});
 add("data_preparation_canvas_available", state.activeViews.includes("analysis") && state.canvasRect?.w > 500 && state.canvasRect?.h > 300, state.canvasRect||{});
 await page.click("#teachingModeBtn");
 await page.waitForTimeout(500);
 const afterExit=await page.evaluate(()=>({active:document.body.classList.contains("teaching-sandbox-active"), button:document.querySelector("#teachingModeBtn")?.innerText||"", bannerHidden:document.querySelector("#teachingSandboxBanner")?.hidden ?? true}));
 add("exit_returns_normal_mode", !afterExit.active && afterExit.button.includes("教学模式") && afterExit.bannerHidden, afterExit);
 await page.screenshot({path:SCREENSHOT,fullPage:true});
}catch(error){add("unexpected_error",false,{message:error.message||String(error)}); await page.screenshot({path:SCREENSHOT,fullPage:true}).catch(()=>{});}finally{await browser.close();}
const report={status:checks.every(x=>x.pass)?"passed":"failed",frontendUrl:FRONTEND_URL,apiBase:API_BASE,generatedAt:new Date().toISOString(),checks,screenshot:SCREENSHOT};
fs.writeFileSync(OUT_JSON,JSON.stringify(report,null,2)+"\n","utf8");
console.log(JSON.stringify(report,null,2));
process.exit(report.status==="passed"?0:1);
