from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path
from typing import Any
SECRET_PATTERNS=[
  re.compile(r'(?i)(access[_-]?key[_-]?secret|secret[_-]?key|api[_-]?key|token|password)\s*[:=]\s*[^<\s][^\s,}]{8,}'),
  re.compile(r'AKIA[0-9A-Z]{16}'),
  re.compile(r'(?i)-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----'),
]
REQUIRED={
 'qlanalyser-oss-lifecycle-policy-evidence-v0.1':['environment','bucket','prefix','rules','secret_policy'],
 'qlanalyser-provider-callback-evidence-v0.1':['provider','mode','callback_url','http_status','signature_verified','secret_policy'],
 'qlanalyser-message-provider-evidence-v0.1':['mode','email_provider_mode','sms_provider_mode','wechat_auth_provider_mode','samples','secret_policy'],
 'qlanalyser-staging-origin-evidence-v0.1':['public_base_url','api_base_url','cors_origins','secret_policy'],
 'qlanalyser-backup-env-evidence-v0.1':['backup_bucket','backup_prefix','restore_drill_command','secret_policy'],
}
def scan_text(text:str)->list[str]:
    return [p.pattern for p in SECRET_PATTERNS if p.search(text)]
def validate_file(path:Path)->dict[str,Any]:
    text=path.read_text(encoding='utf-8')
    findings=scan_text(text)
    try:
        data=json.loads(text)
    except Exception as e:
        return {'path':str(path),'status':'fail','error':f'json_parse:{e}','secret_findings':findings}
    schema=data.get('schema')
    missing=[k for k in REQUIRED.get(schema,[]) if k not in data]
    placeholder_ok=not findings
    status='pass' if schema in REQUIRED and not missing and placeholder_ok else 'fail'
    return {'path':str(path),'schema':schema,'status':status,'missing':missing,'secret_findings':findings}
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('base', nargs='?', default='work/release_evidence/20260620-aliyun-staging/evidence_templates')
    args=ap.parse_args()
    base=Path(args.base)
    files=sorted(p for p in base.glob('*.json'))
    results=[validate_file(p) for p in files]
    status='passed' if files and all(r['status']=='pass' for r in results) else 'failed'
    out={'status':status,'base':str(base),'file_count':len(files),'results':results}
    print(json.dumps(out,ensure_ascii=False,indent=2))
    return 0 if status=='passed' else 1
if __name__=='__main__':
    raise SystemExit(main())
