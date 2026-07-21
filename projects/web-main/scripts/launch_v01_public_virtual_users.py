import json
import re
import sys
import urllib.request

BASE = sys.argv[1].rstrip('/') if len(sys.argv) > 1 else 'http://39.97.248.225'


def fetch(path: str):
    with urllib.request.urlopen(BASE + path, timeout=20) as response:
        body = response.read().decode('utf-8', errors='replace')
        ctype = response.headers.get('content-type', '')
        status = response.status
    if 'json' in ctype or body[:1] in '{[':
        try:
            return status, json.loads(body), body
        except Exception:
            return status, None, body
    return status, None, body


def no_mojibake(text: str) -> bool:
    markers = ['\ufffd', '\u00c3', '\u00c2', '\u00e2\u20ac', '\u9359', '\u93c2', '\u9366']
    return not any(marker in text for marker in markers)


def score(name, threshold, checks):
    value = round(sum(weight for _, weight, ok in checks if ok), 4)
    return {'persona': name, 'score': value, 'threshold': threshold, 'satisfied': value >= threshold, 'details': [{'check': c, 'weight': w, 'ok': bool(ok)} for c, w, ok in checks]}


def main() -> None:
    health_status, health_json, health_body = fetch('/api/health')
    ready_status, ready_json, ready_body = fetch('/api/health/readiness')
    index_status, _, index_html = fetch('/')
    research_status, _, research_html = fetch('/research-modules.html')
    qc_status, _, qc_html = fetch('/research-module/qc.html')
    manifest_status, manifest_json, manifest_body = fetch('/assets/research-modules/reproducibility/research_module_manifest.json')
    combined = '\n'.join([index_html, research_html, qc_html, manifest_body])
    modules = set((manifest_json or {}).get('modules', {}))
    disabled = set((ready_json or {}).get('disabled_workflows', []))
    personas = [
        score('Public Research Customer', .90, [
            ('index_200', .14, index_status == 200),
            ('research_200', .16, research_status == 200 and qc_status == 200),
            ('brand_visible', .14, 'QLanalyser Online' in combined),
            ('downloads_visible', .14, 'download' in combined.lower() or '.csv' in combined.lower() or '.zip' in combined.lower()),
            ('guardrail_visible', .16, all(x in combined.lower() for x in ['clinical diagnosis', 'synthetic', 'research'])),
            ('no_mojibake', .16, no_mojibake(combined)),
            ('manifest_modules', .10, {'qc', 'psd', 'erp', 'tfr', 'pac', 'connectivity'}.issubset(modules)),
        ]),
        score('Public API Integrator', .90, [
            ('health_200', .18, health_status == 200 and (health_json or {}).get('status') == 'ok'),
            ('readiness_200', .18, ready_status == 200 and (ready_json or {}).get('status') == 'ready'),
            ('advanced_disabled', .18, {'tfr_ersp_itc', 'pac_cfc', 'connectivity'}.issubset(disabled)),
            ('state_ready', .16, not (ready_json or {}).get('blockers')),
            ('storage_roots', .14, all(v.get('exists') for v in (ready_json or {}).get('storage_roots', {}).values())),
            ('no_mojibake', .16, no_mojibake(ready_body + health_body)),
        ]),
    ]
    summary = {'status': 'passed' if all(item['satisfied'] for item in personas) else 'failed', 'base': BASE, 'personas': personas, 'min_score': min(item['score'] for item in personas)}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if summary['status'] != 'passed':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
