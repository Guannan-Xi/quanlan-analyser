from __future__ import annotations

import html
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .contract import validate_delivery


def _esc(value: Any) -> str:
    return html.escape(str(value))


def _figure(item: Mapping[str, Any], number: int) -> str:
    links = []
    for label, key in (("SVG", "vector"), ("PDF", "pdf"), ("数据", "source_data")):
        if item.get(key):
            links.append(f'<a href="{_esc(item[key])}">{label}</a>')
    return f'''<figure id="figure-{_esc(item['figure_id'])}"><img src="{_esc(item['image'])}" alt="{_esc(item['title'])}"><figcaption><strong>图 {number}｜{_esc(item['title'])}</strong><span>{_esc(item['conclusion'])}</span><small>{" · ".join(links)}</small></figcaption></figure>'''


def _metric_table(data: Mapping[str, Any]) -> str:
    definitions = data["results"]["metric_definitions"]
    metric_ids = list(definitions)
    headers = "".join(f"<th>{_esc(definitions[key]['label'])} ({_esc(definitions[key]['unit'])})</th>" for key in metric_ids)
    rows = []
    targets = {item["target_id"]: item["name"] for item in data["targets"]}
    conditions = {item["condition_id"]: item["label"] for item in data["protocol"]["conditions"]}
    for row in data["results"]["roi_metrics"]:
        cells = []
        for key in metric_ids:
            value = row["values"].get(key)
            decimals = definitions[key].get("decimals")
            if isinstance(value, (int, float)) and isinstance(decimals, int):
                display = f"{value:.{decimals}f}"
            else:
                display = "—" if value is None else value
            cells.append(f"<td>{_esc(display)}</td>")
        values = "".join(cells)
        rows.append(f"<tr><td>{_esc(conditions[row['condition_id']])}</td><td>{_esc(targets.get(row['target_id'], row['target_id']))}</td>{values}</tr>")
    return f'<div class="table-wrap"><table><thead><tr><th>方案</th><th>区域</th>{headers}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'


def _protocol_conditions(conditions: Sequence[Mapping[str, Any]]) -> str:
    blocks = []
    for condition in conditions:
        channels = "；".join(_esc(channel.get("description", channel.get("channel_id", ""))) for channel in condition["channels"])
        blocks.append(f'<div><h3>{_esc(condition["label"])}</h3><p>{channels}</p></div>')
    return f'<div class="condition-grid">{"".join(blocks)}</div>'


def render_report(data: Mapping[str, Any], root: Path | None = None) -> str:
    validate_delivery(data, root=root)
    project = data["project"]
    subject = data["subject"]
    figures = data["figures"]
    by_category: dict[str, list[Mapping[str, Any]]] = {}
    for item in figures:
        by_category.setdefault(item["category"], []).append(item)

    figure_number = {item["figure_id"]: index for index, item in enumerate(figures, 1)}

    def figures_for(*categories: str) -> str:
        selected = [item for category in categories for item in by_category.get(category, [])]
        return "".join(_figure(item, figure_number[item["figure_id"]]) for item in selected)

    findings = "".join(f"<li>{_esc(item)}</li>" for item in data["results"]["headline_findings"])
    interpretations = "".join(f"<li>{_esc(item)}</li>" for item in data["results"].get("interpretation", []))
    status_labels = {"pass": "通过", "warning": "需注意", "fail": "未通过", "not_assessed": "未评估"}
    checks = "".join(f'<tr><td>{_esc(item["name"])}</td><td><span class="status {item["status"]}">{status_labels[item["status"]]}</span></td><td>{_esc(item.get("evidence", "—"))}</td></tr>' for item in data["quality_control"]["checks"])
    limitations = "".join(f"<li>{_esc(item)}</li>" for item in data["quality_control"]["limitations"])
    methods = "".join(f'<h3>{_esc(item["title"])}</h3><p>{_esc(item["text"])}</p>' for item in data.get("methods", []))
    artifacts = "".join(f'<a href="{_esc(item["path"])}"><strong>{_esc(item["label"])}</strong><span>{_esc(item["purpose"])}</span></a>' for item in data["artifacts"] if item.get("customer_visible", True))

    css = """
    :root{--ink:#17212b;--muted:#586674;--line:#d7dee4;--paper:#fff;--wash:#f5f7f8;--green:#08785f;--orange:#c86518;--max:1160px}*{box-sizing:border-box}body{margin:0;background:#edf1f3;color:var(--ink);font-family:Arial,'Microsoft YaHei',sans-serif;line-height:1.72;letter-spacing:0}.shell{max-width:var(--max);margin:auto;background:var(--paper);min-height:100vh}header{padding:46px 60px 30px;border-bottom:1px solid var(--line)}.brand{font-size:13px;font-weight:700;color:var(--green)}h1{font-size:34px;line-height:1.25;margin:18px 0 12px}header p{font-size:17px;max-width:850px}.meta{display:flex;gap:20px;flex-wrap:wrap;color:var(--muted);font-size:13px}nav{position:sticky;top:0;z-index:5;display:flex;overflow:auto;gap:18px;padding:11px 60px;background:rgba(255,255,255,.96);border-bottom:1px solid var(--line)}nav a{white-space:nowrap;color:#33414c;text-decoration:none;font-size:14px}main{padding:0 60px 70px}section{padding:44px 0;border-bottom:1px solid var(--line)}h2{font-size:25px;margin:0 0 18px}h3{font-size:18px;margin:28px 0 10px}.lead{font-size:18px}.finding-list,.interpretation-list{padding-left:24px}.finding-list li,.interpretation-list li{margin:9px 0}.condition-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:1px;background:var(--line);border:1px solid var(--line);margin:20px 0}.condition-grid>div{background:#fff;padding:18px}.condition-grid h3{margin:0 0 8px}figure{margin:30px 0 46px}figure img{display:block;width:100%;height:auto;border:1px solid var(--line)}figcaption{margin-top:10px;font-size:14px}figcaption strong,figcaption span,figcaption small{display:block}figcaption span{color:#33414c}figcaption small{margin-top:5px;color:var(--muted)}a{color:#006a91}.table-wrap{overflow:auto;border:1px solid var(--line)}table{border-collapse:collapse;width:100%;font-size:13px}th,td{padding:10px 12px;text-align:left;border-bottom:1px solid var(--line);white-space:nowrap}th{background:var(--wash)}.status{font-weight:700}.status.pass{color:var(--green)}.status.warning,.status.not_assessed{color:var(--orange)}.status.fail{color:#b42318}.note{padding:14px 18px;border-left:4px solid var(--orange);background:#fff6ec}.downloads{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.downloads a{padding:14px;border:1px solid var(--line);text-decoration:none;color:var(--ink)}.downloads strong,.downloads span{display:block}.downloads span{font-size:13px;color:var(--muted)}footer{padding:24px 60px;background:#202a33;color:#dce2e7;font-size:12px}@media(max-width:720px){header,main{padding-left:20px;padding-right:20px}nav{position:static;padding-left:20px;padding-right:20px}h1{font-size:28px}.downloads{grid-template-columns:1fr}}@media print{body{background:#fff}.shell{max-width:none}nav{display:none}header,main{padding-left:13mm;padding-right:13mm}main{padding-bottom:3mm}section{break-inside:auto}figure{break-inside:avoid}.downloads{grid-template-columns:repeat(3,1fr);gap:2mm}.downloads a{padding:2mm;break-inside:avoid}.downloads span{font-size:10px}#methods{font-size:12px;line-height:1.5}#methods h3{font-size:15px;margin:4mm 0 1.5mm}#methods p,#methods ul{margin-top:1.5mm;margin-bottom:2mm}#methods table{font-size:10px}#methods th,#methods td{padding:1.5mm 2mm}footer{padding:3mm 13mm;background:#fff;color:#333;border-top:1px solid var(--line);break-inside:avoid}}
    """
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{_esc(project['title'])}</title><style>{css}</style></head><body><div class="shell"><header><div class="brand">QuanLan BrainScience · SimNIBS 仿真服务</div><h1>{_esc(project['title'])}</h1><p>{_esc(project['scientific_question'])}</p><div class="meta"><span>项目编号：{_esc(project['project_id'])}</span><span>对象：{_esc(subject['subject_id'])}</span><span>模型：{_esc(subject['model_type'])}</span><span>状态：{_esc(project['service_status'])}</span></div></header><nav><a href="#summary">结论</a><a href="#protocol">方案</a><a href="#results">结果</a><a href="#interpretation">解读</a><a href="#methods">方法与交付</a></nav><main><section id="summary"><h2>一、主要结论</h2><ol class="finding-list">{findings}</ol></section><section id="protocol"><h2>二、模型与刺激方案</h2><p class="lead">{_esc(subject['image_source'])}</p>{_protocol_conditions(data['protocol']['conditions'])}{figures_for('anatomy','protocol')}</section><section id="results"><h2>三、模拟结果</h2>{figures_for('field','quantitative','localization')}{_metric_table(data)}</section><section id="interpretation"><h2>四、结果解读</h2><ul class="interpretation-list">{interpretations}</ul>{figures_for('robustness')}<p class="note">{_esc(data['results'].get('interpretation_boundary','结果仅适用于所声明的模型和参数。'))}</p></section><section id="methods"><h2>五、方法、质量控制与交付</h2>{methods}<h3>质量控制</h3><div class="table-wrap"><table><thead><tr><th>检查</th><th>状态</th><th>依据</th></tr></thead><tbody>{checks}</tbody></table></div><h3>尚未评估或不能外推的内容</h3><ul>{limitations}</ul><h3>交付文件</h3><div class="downloads">{artifacts}</div></section></main><footer>报告由标准化 SimNIBS 交付生成器生成。Schema: {_esc(data['schema_version'])}</footer></div></body></html>'''
