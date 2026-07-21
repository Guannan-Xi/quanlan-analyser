import { chromium, chromiumLaunchOptions } from "./lib/playwright_runtime.mjs";
import fs from "node:fs";
import path from "node:path";
const API_BASE=process.env.QLANALYSER_API_BASE_URL||"http://127.0.0.1:8001/api";
const FRONTEND_URL=process.env.QLANALYSER_FRONTEND_URL||`http://127.0.0.1:4174/index.html?customer_demo=auto&teaching_demo=auto&api=${encodeURIComponent(API_BASE)}`;
const OUT_DIR=path.resolve("work/release_evidence/20260627-teaching-sandbox-analysis"); fs.mkdirSync(OUT_DIR,{recursive:true});
const OUT_JSON=path.join(OUT_DIR,"teaching_sandbox_analysis_e2e.json"); const SCREENSHOT=path.join(OUT_DIR,"teaching_sandbox_psd.png");
const checks=[]; const add=(name,pass,details={})=>checks.push({name,pass:Boolean(pass),details});
const browser=await chromium.launch({headless:true,...chromiumLaunchOptions()}); const page=await browser.newPage({viewport:{width:1440,height:1000}});
const requests=[]; page.on("request", req=>{ const url=req.url(); if(url.includes("/api/")) requests.push({url,method:req.method(),post:req.postDataJSON?.()||null}); });
try{
 await page.goto(FRONTEND_URL,{waitUntil:"domcontentloaded",timeout:60000});
 await page.waitForFunction(()=>{ const shell=document.querySelector("#appShell"); const login=document.querySelector("#loginScreen"); return Boolean((shell&&!shell.hidden)||(login&&!login.hidden)); },null,{timeout:30000});
 if(await page.locator("#customerLoginBtn").isVisible().catch(()=>false)) await page.click("#customerLoginBtn");
 await page.waitForSelector("#appShell:not([hidden]), .main",{timeout:30000});
 const alreadyTeaching = await page.evaluate(()=>document.body.classList.contains("teaching-sandbox-active") || document.body.innerText.includes("teaching_oddball_with_montage_raw.fif"));
 if(!alreadyTeaching) await page.click("#teachingModeBtn");
 const overlayVisible = await page.locator("#teachingOverlay.active").isVisible({timeout:5000}).catch(()=>false);
 if(overlayVisible){
   const closeButton = page.locator('#teachingOverlay [data-teaching-action="close"]');
   if(await closeButton.isVisible().catch(()=>false)) await closeButton.click({force:true});
   else for(let i=0;i<8;i++){ if(!(await page.locator("#teachingOverlay.active").isVisible().catch(()=>false))) break; await page.locator('#teachingOverlay [data-teaching-action="next"].primary-btn').click({force:true}); await page.waitForTimeout(250); }
   await page.waitForTimeout(300);
   if(await page.locator("#teachingOverlay.active").isVisible().catch(()=>false)){
     await page.evaluate(()=>{ const overlay=document.querySelector("#teachingOverlay"); if(overlay){ overlay.classList.remove("active"); overlay.hidden=true; } });
   }
 }
 await page.waitForFunction(()=>document.body.classList.contains("teaching-sandbox-active") && !document.querySelector("#teachingOverlay.active"),null,{timeout:30000});
 await page.waitForFunction(()=>{
   const confirm=[...document.querySelectorAll('[data-real-action="confirm-plan-inline"]')].find((node)=>{
     const rect=node.getBoundingClientRect(); const style=getComputedStyle(node);
     return rect.width>0 && rect.height>0 && style.display!=="none" && style.visibility!=="hidden";
   });
   const gate=document.querySelector('[data-testid="analysis-preparation-gate"]');
   return Boolean(confirm || gate?.hidden || gate?.classList.contains("is-ready"));
 },null,{timeout:60000});
 const planReadyBefore=await page.evaluate(()=>{
   const gate=document.querySelector('[data-testid="analysis-preparation-gate"]');
   return Boolean(gate?.hidden || gate?.classList.contains("is-ready"));
 });
 if(!planReadyBefore){
   const confirmButton=page.locator('[data-real-action="confirm-plan-inline"]:visible').first();
   await page.waitForFunction(()=>{
     const node=[...document.querySelectorAll('[data-real-action="confirm-plan-inline"]')].find((item)=>{
       const rect=item.getBoundingClientRect(); const style=getComputedStyle(item);
       return rect.width>0 && rect.height>0 && style.display!=="none" && style.visibility!=="hidden";
     });
     return node && !node.disabled && node.getAttribute("aria-disabled")!=="true";
   },null,{timeout:60000});
   await confirmButton.click();
 }
 await page.waitForFunction(()=>{
   const gate=document.querySelector('[data-testid="analysis-preparation-gate"]');
   return Boolean(gate?.hidden || gate?.classList.contains("is-ready"));
 },null,{timeout:60000});
 await page.evaluate(()=>{ const nodes=[...document.querySelectorAll('[data-view-jump="workflow"], [data-view="workflow"]')]; const node=nodes.find((item)=>item.offsetParent!==null) || nodes[0]; node?.click(); });
 await page.waitForFunction(()=>document.querySelector('#workflow')?.classList.contains('active'),null,{timeout:30000});
 await page.waitForFunction(()=>{
   const node=[...document.querySelectorAll('#workflow [data-real-action="run-psd"]')].find((item)=>{
     const rect=item.getBoundingClientRect(); const style=getComputedStyle(item);
     return rect.width>0 && rect.height>0 && style.display!=="none" && style.visibility!=="hidden";
   });
   return node && !node.disabled && node.getAttribute("aria-disabled")!=="true";
 },null,{timeout:60000});
 await page.evaluate(()=>{
   const node=[...document.querySelectorAll('#workflow [data-real-action="run-psd"]')].find((item)=>{
     const rect=item.getBoundingClientRect(); const style=getComputedStyle(item);
     return rect.width>0 && rect.height>0 && style.display!=="none" && style.visibility!=="hidden" && !item.disabled && item.getAttribute("aria-disabled")!=="true";
   });
   node?.click();
 });
 for(let i=0;i<120;i++){
   if(requests.find(r=>r.url.endsWith("/api/tasks")&&r.method==="POST"&&r.post?.module_name==="psd")) break;
   await page.waitForTimeout(500);
 }
 await page.waitForFunction(()=>document.body.classList.contains("teaching-sandbox-active"),null,{timeout:30000});
 const taskReq=requests.find(r=>r.url.endsWith("/api/tasks")&&r.method==="POST"&&r.post?.module_name==="psd");
 const uploadReq=requests.find(r=>r.url.includes("/eeg/upload")||r.url.includes("/upload"));
 const state=await page.evaluate(()=>({banner:document.querySelector("#teachingSandboxBanner")?.innerText||"", body:document.body.innerText.slice(0,2500)}));
 add("psd_task_uses_teaching_file", Boolean(taskReq&&taskReq.post?.input_file_id==="eeg_demo_teaching_oddball"&&taskReq.post?.project_id==="proj_demo_learning"), {taskReq});
 add("no_upload_triggered", !uploadReq, {uploadReq, apiRequestCount:requests.length});
 add("teaching_sandbox_still_active_after_analysis", await page.evaluate(()=>document.body.classList.contains("teaching-sandbox-active")), state);
 await page.screenshot({path:SCREENSHOT,fullPage:true});
}catch(error){ add("unexpected_error",false,{message:error.message||String(error), requests}); await page.screenshot({path:SCREENSHOT,fullPage:true}).catch(()=>{}); }
finally{ await browser.close(); }
const report={status:checks.every(x=>x.pass)?"passed":"failed",frontendUrl:FRONTEND_URL,apiBase:API_BASE,generatedAt:new Date().toISOString(),checks,screenshot:SCREENSHOT}; fs.writeFileSync(OUT_JSON,JSON.stringify(report,null,2)+"\n","utf8"); console.log(JSON.stringify(report,null,2)); process.exit(report.status==="passed"?0:1);
