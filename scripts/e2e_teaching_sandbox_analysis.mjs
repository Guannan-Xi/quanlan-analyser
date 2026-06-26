import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";
const require=createRequire(import.meta.url); const {chromium}=require("../frontend/node_modules/playwright");
const API_BASE=process.env.QLANALYSER_API_BASE_URL||"http://127.0.0.1:8001/api";
const FRONTEND_URL=process.env.QLANALYSER_FRONTEND_URL||`http://127.0.0.1:4174/index.html?customer_demo=auto&api=${encodeURIComponent(API_BASE)}`;
const OUT_DIR=path.resolve("work/release_evidence/20260627-teaching-sandbox-analysis"); fs.mkdirSync(OUT_DIR,{recursive:true});
const OUT_JSON=path.join(OUT_DIR,"teaching_sandbox_analysis_e2e.json"); const SCREENSHOT=path.join(OUT_DIR,"teaching_sandbox_psd.png");
function exe(){return ["C:/Program Files/Microsoft/Edge/Application/msedge.exe","C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"].find(fs.existsSync)||"";}
const checks=[]; const add=(name,pass,details={})=>checks.push({name,pass:Boolean(pass),details});
const browser=await chromium.launch({headless:true,...(exe()?{executablePath:exe()}:{})}); const page=await browser.newPage({viewport:{width:1440,height:1000}});
const requests=[]; page.on("request", req=>{ const url=req.url(); if(url.includes("/api/")) requests.push({url,method:req.method(),post:req.postDataJSON?.()||null}); });
try{
 await page.goto(FRONTEND_URL,{waitUntil:"domcontentloaded",timeout:60000});
 await page.waitForSelector("#appShell, #loginScreen",{timeout:30000});
 if(await page.locator("#customerLoginBtn").isVisible().catch(()=>false)) await page.click("#customerLoginBtn");
 await page.waitForSelector("#appShell:not([hidden]), .main",{timeout:30000});
 await page.click("#teachingModeBtn"); await page.waitForSelector("#teachingOverlay.active",{timeout:60000});
 for(let i=0;i<8;i++){ if(!(await page.locator("#teachingOverlay.active").isVisible().catch(()=>false))) break; await page.locator('#teachingOverlay [data-teaching-action="next"].primary-btn').click({force:true}); await page.waitForTimeout(250); }
 await page.waitForFunction(()=>document.body.classList.contains("teaching-sandbox-active") && !document.querySelector("#teachingOverlay.active"),null,{timeout:30000});
 await page.waitForFunction(()=>document.body.innerText.includes("teaching_oddball_with_montage_raw.fif"),null,{timeout:30000});
 await page.click('[data-view="workflow"]');
 await page.waitForSelector('[data-real-action="run-psd"]',{timeout:30000});
 await page.waitForFunction(()=>!document.querySelector('[data-real-action="run-psd"]')?.disabled,null,{timeout:60000});
 const psdRequestPromise=page.waitForRequest(req=>req.url().endsWith("/api/tasks")&&req.method()==="POST"&&req.postDataJSON?.()?.module_name==="psd",{timeout:120000});
 await page.click('[data-real-action="run-psd"]');
 await psdRequestPromise;
 await page.waitForFunction(()=>document.body.classList.contains("teaching-sandbox-active"),null,{timeout:30000});
 const taskReq=requests.find(r=>r.url.endsWith("/api/tasks")&&r.method==="POST"&&r.post?.module_name==="psd");
 const uploadReq=requests.find(r=>r.url.includes("/eeg/upload")||r.url.includes("/upload"));
 const state=await page.evaluate(()=>({banner:document.querySelector("#teachingSandboxBanner")?.innerText||"", body:document.body.innerText.slice(0,2500)}));
 add("psd_task_uses_teaching_file", Boolean(taskReq&&taskReq.post?.input_file_id==="eeg_demo_teaching_oddball"&&taskReq.post?.project_id==="proj_demo_learning"), {taskReq});
 add("no_upload_triggered", !uploadReq, {uploadReq, apiRequestCount:requests.length});
 add("teaching_sandbox_still_active_after_analysis", state.banner.includes("教学模式"), state);
 await page.screenshot({path:SCREENSHOT,fullPage:true});
}catch(error){ add("unexpected_error",false,{message:error.message||String(error), requests}); await page.screenshot({path:SCREENSHOT,fullPage:true}).catch(()=>{}); }
finally{ await browser.close(); }
const report={status:checks.every(x=>x.pass)?"passed":"failed",frontendUrl:FRONTEND_URL,apiBase:API_BASE,generatedAt:new Date().toISOString(),checks,screenshot:SCREENSHOT}; fs.writeFileSync(OUT_JSON,JSON.stringify(report,null,2)+"\n","utf8"); console.log(JSON.stringify(report,null,2)); process.exit(report.status==="passed"?0:1);
