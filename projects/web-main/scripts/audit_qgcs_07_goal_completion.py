from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[1]
REQUIREMENTS=[
 ('pdca_loop_executed','work/qgcs_07_pdca_round5_outputs_package.json','outputs_package_ready_goal_active_public_cloud_inputs_pending'),
 ('advancement_review_done','work/qgcs_07_pdca_round1_acceptance_matrix.json','local_sandbox_production_candidate_pass_public_cloud_not_claimed'),
 ('page_function_e2e_done','work/release_evidence/edf_upload_to_results_ui_only/edf_upload_to_results_ui_only.json','passed'),
 ('workflow_visual_gate_done','work/release_evidence/ui_interaction_review/workflow_pages_gate/workflow_pages_ui_gate.json','passed'),
 ('parallel_dev_review_done','work/qgcs_07_pdca_round1_acceptance_matrix.json','local_sandbox_production_candidate_pass_public_cloud_not_claimed'),
 ('release_gate_local_passed','work/release_evidence/20260620-v01-acceptance/release_review_gate_run.json','passed'),
 ('owner_review_package_ready','work/release_evidence/20260620-v01-owner-review-final-index/owner_review_final_index.json','local_sandbox_owner_review_ready_public_production_blocked'),
 ('strict_cloud_preflight_passed','work/release_evidence/20260620-aliyun-staging/aliyun_staging_preflight.json','passed'),
 ('strict_cloud_rerun_all_passed','work/release_evidence/20260620-aliyun-staging/strict_cloud_gate_rerun.json','passed_all_strict_cloud_gates'),
]
def load_status(rel:str):
    p=ROOT/rel
    if not p.exists(): return None, False, str(p)
    try:
        d=json.loads(p.read_text(encoding='utf-8'))
        return d.get('status'), True, str(p)
    except Exception as e:
        return f'parse_error:{e}', True, str(p)
def main():
    items=[]
    for rid,rel,expected in REQUIREMENTS:
        actual,exists,path=load_status(rel)
        if actual==expected: verdict='proved'
        elif exists: verdict='contradicts_or_incomplete'
        else: verdict='missing'
        items.append({'id':rid,'path':path,'exists':exists,'expected_status':expected,'actual_status':actual,'verdict':verdict})
    complete=all(i['verdict']=='proved' for i in items)
    out={'schema':'qgcs-07-goal-completion-audit-v0.1','generated_at':datetime.now(timezone.utc).isoformat(),'status':'complete_proved' if complete else 'not_complete','goal_complete':complete,'items':items,'summary':{'proved':sum(i['verdict']=='proved' for i in items),'incomplete':sum(i['verdict']!='proved' for i in items)},'completion_rule':'Goal can be complete only when every item verdict is proved.'}
    p=ROOT/'work/qgcs_07_goal_completion_audit.json'
    p.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':out['status'],'proved':out['summary']['proved'],'incomplete':out['summary']['incomplete'],'output':str(p)},ensure_ascii=False,indent=2))
    return 0 if complete else 1
if __name__=='__main__': raise SystemExit(main())
