from __future__ import annotations
import argparse, json, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/release_evidence/20260620-aliyun-staging/strict_cloud_gate_rerun.json'
COMMANDS=[
 ('strict_preflight',[sys.executable,'scripts/aliyun_staging_preflight.py','--strict'],False),
 ('aliyun_storage_contract',[sys.executable,'scripts/acceptance_aliyun_storage_contract.py','--target','aliyun','--strict'],True),
 ('aliyun_backup_restore_drill',[sys.executable,'scripts/acceptance_backup_restore_drill.py','--target','aliyun','--strict'],True),
 ('v01_acceptance_powershell',['powershell','-NoProfile','-ExecutionPolicy','Bypass','-File','scripts\\run_v01_acceptance.ps1'],True),
]
def utc(): return datetime.now(timezone.utc).isoformat()
def run(name:str,cmd:list[str],skip:bool)->dict[str,Any]:
    started=utc()
    if skip:
        return {'name':name,'command':cmd,'status':'skipped_until_preflight_passes','started_at':started,'finished_at':utc(),'returncode':None,'stdout_tail':'','stderr_tail':''}
    p=subprocess.run(cmd,cwd=ROOT,text=True,encoding='utf-8',errors='replace',capture_output=True)
    return {'name':name,'command':cmd,'status':'passed' if p.returncode==0 else 'failed','started_at':started,'finished_at':utc(),'returncode':p.returncode,'stdout_tail':(p.stdout or '')[-4000:],'stderr_tail':(p.stderr or '')[-4000:]}
def main():
    ap=argparse.ArgumentParser(description='Run QLanalyser strict cloud gate sequence after owner/cloudops inputs are supplied.')
    ap.add_argument('--execute-after-preflight',action='store_true',help='If strict preflight passes, run OSS/backup/V01 gates. Without this flag, only preflight runs and later gates are skipped.')
    ap.add_argument('--output',default=str(OUT))
    args=ap.parse_args()
    results=[]
    pre=run(COMMANDS[0][0],COMMANDS[0][1],False); results.append(pre)
    pre_ok=pre['status']=='passed'
    for name,cmd,requires_pre in COMMANDS[1:]:
        results.append(run(name,cmd, skip=(requires_pre and (not pre_ok or not args.execute_after_preflight))))
    status='passed' if pre_ok and all(r['status'] in ('passed','skipped_until_preflight_passes') for r in results) else 'blocked_or_failed'
    if pre_ok and args.execute_after_preflight and all(r['status']=='passed' for r in results): status='passed_all_strict_cloud_gates'
    payload={'generated_at':utc(),'status':status,'execute_after_preflight':args.execute_after_preflight,'preflight_passed':pre_ok,'results':results,'safe_claim':'Production readiness can only be claimed if status == passed_all_strict_cloud_gates and GPT-5.5/Codex final acceptance confirms current evidence.'}
    out=Path(args.output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':status,'output':str(out),'preflight_passed':pre_ok,'ran_after_preflight':args.execute_after_preflight and pre_ok},ensure_ascii=False,indent=2))
    return 0 if status.startswith('passed') else 1
if __name__=='__main__': raise SystemExit(main())
