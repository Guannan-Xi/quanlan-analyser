from __future__ import annotations
import json, re, sys
from pathlib import Path
SECRET_PATTERNS=[re.compile(r'(?i)(access[_-]?key[_-]?secret|api[_-]?key|token|password)\s*[:=]\s*[^<\s][^\s,}]{8,}'), re.compile(r'(?i)-----BEGIN .*PRIVATE KEY-----')]
REQUIRED_BLOCKERS={'deepseek_copy_gate','oss_required_env','oss_storage_backend','oss_allow_write','oss_lifecycle_evidence','backup_required_env','deploy_origin_env','provider_boundary_env'}
REQUIRED_COMMANDS=['python scripts/aliyun_staging_preflight.py --strict','python scripts/acceptance_aliyun_storage_contract.py --target aliyun --strict','python scripts/acceptance_backup_restore_drill.py --target aliyun --strict','powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\run_v01_acceptance.ps1']
def main():
    base=Path('work/release_evidence/20260620-aliyun-staging')
    p=base/'owner_cloudops_closure_pack.json'
    text=p.read_text(encoding='utf-8')
    data=json.loads(text)
    findings=[pat.pattern for pat in SECRET_PATTERNS if pat.search(text)]
    blockers={b.get('id') for b in data.get('blockers',[])}
    missing_blockers=sorted(REQUIRED_BLOCKERS-blockers)
    commands=data.get('commands_after_inputs_are_set') or []
    missing_commands=[c for c in REQUIRED_COMMANDS if c not in commands]
    evidence_files=data.get('required_evidence_files') or []
    missing_templates=[]
    for item in evidence_files:
        if not (base/item['template']).exists(): missing_templates.append(item['template'])
    env_count=len(data.get('required_runtime_env') or {})
    status='passed' if not findings and not missing_blockers and not missing_commands and not missing_templates and env_count>=10 else 'failed'
    out={'status':status,'pack':str(p),'blocker_count':len(blockers),'env_count':env_count,'evidence_file_count':len(evidence_files),'secret_findings':findings,'missing_blockers':missing_blockers,'missing_commands':missing_commands,'missing_templates':missing_templates}
    outp=base/'owner_cloudops_closure_pack.validation.json'
    outp.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(out,ensure_ascii=False,indent=2))
    return 0 if status=='passed' else 1
if __name__=='__main__':
    raise SystemExit(main())
