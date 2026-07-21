from __future__ import annotations
import json, sys
from pathlib import Path
REQUIRED_IDS={'real_user_path_e2e','workflow_pages_ui_gate','report_zip_inventory','report_evidence_matrix','release_review_gate','review_system_all_env','sanitized_review_package','owner_cloudops_closure_pack','public_cloud_strict_preflight'}
def main():
    p=Path('work/release_evidence/20260620-v01-owner-review-final-index/owner_review_final_index.json')
    d=json.loads(p.read_text(encoding='utf-8'))
    items=d.get('evidence_items',[])
    ids={i.get('id') for i in items}
    missing=sorted(REQUIRED_IDS-ids)
    bad=[i for i in items if not i.get('exists') or not i.get('status_matches')]
    expected_status='local_sandbox_owner_review_ready_public_production_blocked'
    status='passed' if not missing and not bad and d.get('status')==expected_status else 'failed'
    out={'status':status,'index':str(p),'missing_ids':missing,'bad_items':[{'id':i.get('id'),'exists':i.get('exists'),'actual_status':i.get('actual_status'),'required_status':i.get('required_status')} for i in bad], 'index_status':d.get('status')}
    outp=p.with_suffix('.validation.json')
    outp.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(out,ensure_ascii=False,indent=2))
    return 0 if status=='passed' else 1
if __name__=='__main__': raise SystemExit(main())
