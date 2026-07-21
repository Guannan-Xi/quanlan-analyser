import json
import re
from html import escape
from pathlib import Path
from typing import Any


SUMMARY_FILES = {
    "QC 质控摘要": "reproducibility/qc_summary.json",
    "PSD 功率谱摘要": "reproducibility/psd_summary.json",
    "ERP 事件相关摘要": "reproducibility/erp_summary.json",
    "软件版本": "reproducibility/software_versions.json",
    "工作流记录": "reproducibility/workflow.json",
}


def _html(value: Any) -> str:
    return escape("" if value is None else str(value))


def _customer_title(title: str) -> str:
    stripped = (title or "").strip()
    if not stripped or stripped.lower() in {"acceptance psd report", "single-subject eeg report"}:
        return "单被试脑电分析报告"
    return stripped


def _redact_customer_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _redact_customer_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_customer_value(item) for item in value]
    if isinstance(value, str):
        normalized = value.replace("\\", "/")
        if "D:/Quanlan/" in normalized or "C:/Users/" in normalized:
            return f"local-reference:{Path(normalized).name}"
    return value


def _json_preview(payload: Any, *, max_chars: int = 5000) -> str:
    payload = _redact_customer_value(payload)
    text = json.dumps(payload, ensure_ascii=False, indent=2) if not isinstance(payload, str) else payload
    if len(text) > max_chars:
        text = text[:max_chars] + "\n... HTML 预览已截断；完整内容见 ZIP 报告包。"
    return _html(text)


def _read_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - defensive report rendering
        return {"status": "unreadable", "file": path.name, "error": str(exc)}


def readable_artifact_label(artifact: dict[str, Any] | str | None) -> str:
    if isinstance(artifact, dict):
        raw = artifact.get("label") or artifact.get("artifact_type") or Path(str(artifact.get("path", ""))).stem
    else:
        raw = artifact
    key = str(raw or "").lower()
    key = re.sub(r"\.[a-z0-9]+$", "", key)
    key = re.sub(r"[-\s]+", "_", key)
    label_map = [
        (r"channel_band_power|band_power_by_channel", "通道频段功率表"),
        (r"band_power|psd_band_power", "频段功率表"),
        (r"psd_mean_spectrum|power_spectrum|spectrum_long|powerspectrum", "PSD 频谱图"),
        (r"erp_metrics|erp_metric|p300", "ERP 指标表"),
        (r"drop_log_summary|epoch_drop|reject", "Epoch 剔除记录"),
        (r"tfr_power_long|ersp|itc|time_frequency", "时频功率明细表"),
        (r"pac_dynamic_curve|pac_curve|cfc", "PAC 动态曲线"),
        (r"pac_comodulogram|phase_bins|binned_amplitude|pac_channel|pac_summary|frequency_grid|filter_edge", "PAC 结果文件"),
        (r"parameters|parameter_schema|threshold_validation", "参数记录"),
        (r"workflow|plan|preparation", "处理流程记录"),
        (r"method_description|method", "方法说明"),
        (r"software_versions|version", "软件版本记录"),
        (r"manifest|log", "文件清单"),
        (r"metadata|dictionary|source", "数据说明"),
        (r"contract|scope|effective_call", "结果范围说明"),
    ]
    for pattern, label in label_map:
        if re.search(pattern, key):
            return label
    return "结果文件"


def _task_table(task: dict) -> str:
    labels = {
        "id": "任务 ID",
        "project_id": "项目 ID",
        "workflow_id": "工作流",
        "module_name": "分析模块",
        "input_file_id": "数据文件",
        "status": "任务状态",
        "progress": "进度",
        "created_at": "创建时间",
        "started_at": "开始时间",
        "finished_at": "完成时间",
        "data_preparation_plan_id": "数据准备方案",
        "data_preparation_revision": "准备方案版本",
    }
    rows = []
    for key, label in labels.items():
        value = task.get(key)
        if value not in (None, ""):
            rows.append(f"<tr><th>{_html(label)}</th><td>{_html(value)}</td></tr>")
    params = task.get("parameters_json") or {}
    if params:
        rows.append(f"<tr><th>分析参数</th><td><pre>{_json_preview(params)}</pre></td></tr>")
    return "\n".join(rows)


def _artifact_table(artifacts: list[dict]) -> str:
    if not artifacts:
        return '<p class="muted">当前任务尚未登记交付文件。</p>'
    grouped: dict[str, dict[str, Any]] = {}
    for artifact in artifacts:
        friendly_name = readable_artifact_label(artifact)
        item = grouped.setdefault(
            friendly_name,
            {
                "count": 0,
                "artifact_type": artifact.get("artifact_type"),
                "mime_type": artifact.get("mime_type"),
            },
        )
        item["count"] += 1
    rows = []
    for friendly_name, item in grouped.items():
        count_text = f"{item['count']} 个文件" if item["count"] != 1 else "1 个文件"
        rows.append(
            "<tr>"
            f"<td>{_html(friendly_name)}</td>"
            f"<td>{_html(count_text)}</td>"
            f"<td>{_html(item.get('mime_type') or item.get('artifact_type') or '文件')}</td>"
            "</tr>"
        )
    return """
<table>
  <thead><tr><th>文件类别</th><th>数量</th><th>格式</th></tr></thead>
  <tbody>{rows}</tbody>
</table>
""".format(rows="\n".join(rows))


def _summaries(task_output_dir: Path) -> str:
    blocks = []
    for title, relative_path in SUMMARY_FILES.items():
        path = task_output_dir / relative_path
        payload = _read_json(path)
        if payload is None:
            blocks.append(
                f"<section class=\"summary-card scope-note\"><h3>{_html(title)}</h3>"
                "<p class=\"muted\">本任务未生成该模块结果。该项属于本次报告范围之外，并不表示任务失败。</p></section>"
            )
        else:
            blocks.append(
                f"<section class=\"summary-card\"><h3>{_html(title)}</h3>"
                "<p class=\"muted\">已随完整报告包交付，可用于复核本次分析。</p>"
                f"<pre>{_json_preview(payload)}</pre></section>"
            )
    method_path = task_output_dir / "reproducibility" / "method_description.txt"
    if method_path.exists():
        blocks.append(
            "<section class=\"summary-card\"><h3>方法说明</h3>"
            f"<pre>{_html(method_path.read_text(encoding='utf-8', errors='replace'))}</pre></section>"
        )
    return "\n".join(blocks)


def _result_summary(task: dict, artifacts: list[dict]) -> str:
    module = str(task.get("module_name") or "analysis").upper()
    status = str(task.get("status") or "unknown")
    plan_id = task.get("data_preparation_plan_id")
    plan_revision = task.get("data_preparation_revision")
    plan_text = (
        f"已应用数据准备方案 {plan_id}（第 {plan_revision} 版）。"
        if plan_id and plan_revision is not None
        else "本任务未记录独立数据准备方案引用。"
    )
    return f"""
      <section class="summary-hero">
        <div>
          <p class="eyebrow">结果摘要</p>
          <h2>{_html(module)} 任务已生成报告包</h2>
          <p>任务状态：<strong>{_html(status)}</strong>。{_html(plan_text)}报告包包含图表、表格、方法说明、参数、软件版本和复现记录。</p>
        </div>
        <div class="summary-stat"><span>交付文件</span><strong>{len(artifacts)}</strong><small>项交付文件</small></div>
      </section>
    """


def write_html_report(output_dir: str | Path, title: str, context: dict) -> Path:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    html_path = output_path / "report.html"

    task = context.get("task") or {}
    artifacts = context.get("artifacts") or []
    task_output_dir = Path(context.get("task_output_dir") or output_path)
    title = _customer_title(title)

    status = str(task.get("status") or "unknown")
    status_class = "ok" if status == "completed" else "danger" if status == "failed" else "warn"
    html_path.write_text(
        f"""<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <title>{_html(title)}</title>
    <style>
      :root {{ --ink:#18202b; --muted:#627084; --line:#d9e0e8; --panel:#fff; --page:#f4f6f8; --accent:#167d7f; --ok:#237348; --warn:#a65f00; --danger:#b2413b; }}
      body {{ margin:0; background:var(--page); color:var(--ink); font-family:"Segoe UI", Arial, sans-serif; line-height:1.55; }}
      main {{ max-width:1120px; margin:0 auto; padding:32px; }}
      header, section {{ background:var(--panel); border:1px solid var(--line); border-radius:18px; padding:24px; margin:0 0 18px; box-shadow:0 10px 28px rgba(24,32,43,.06); }}
      h1 {{ margin:0 0 8px; font-size:34px; }}
      h2 {{ margin:0 0 12px; }}
      h3 {{ margin:0 0 8px; }}
      .muted, footer {{ color:var(--muted); }}
      .badge {{ display:inline-flex; padding:6px 10px; border-radius:999px; font-weight:700; margin-top:10px; }}
      .ok {{ background:#e9f8ef; color:var(--ok); }}
      .warn {{ background:#fff4dc; color:var(--warn); }}
      .danger {{ background:#ffe9e5; color:var(--danger); }}
      .eyebrow {{ margin:0 0 4px; color:var(--accent); font-weight:800; text-transform:uppercase; font-size:12px; letter-spacing:.08em; }}
      table {{ width:100%; border-collapse:collapse; margin-top:10px; }}
      th, td {{ text-align:left; border-bottom:1px solid var(--line); padding:10px; vertical-align:top; }}
      th {{ width:210px; color:var(--muted); }}
      pre {{ white-space:pre-wrap; overflow:auto; background:#111827; color:#f8fafc; border-radius:12px; padding:14px; max-height:420px; }}
      .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:16px; }}
      .summary-card {{ border:1px solid var(--line); border-radius:16px; padding:18px; background:#fbfcfe; }}
      .scope-note {{ background:#f8fafc; }}
      .summary-hero {{ display:flex; justify-content:space-between; gap:22px; align-items:center; border-color:#b8e4df; background:#f3fffc; }}
      .summary-hero h2 {{ margin:.15rem 0 .4rem; }}
      .summary-stat {{ min-width:150px; border:1px solid #b8e4df; border-radius:14px; padding:16px; text-align:center; background:white; }}
      .summary-stat span, .summary-stat small {{ display:block; color:var(--muted); }}
      .summary-stat strong {{ display:block; font-size:2rem; }}
      footer {{ padding:12px 4px 32px; }}
      @media (max-width: 720px) {{ main {{ padding:16px; }} .summary-hero {{ display:block; }} .summary-stat {{ margin-top:14px; }} }}
    </style>
  </head>
  <body>
    <main>
      <header>
        <p class="eyebrow">QLanalyser EEG V01</p>
        <h1>{_html(title)}</h1>
        <p>本报告为当前分析任务面向客户的可读摘要。完整图表、表格、方法说明、参数和复现记录已随 ZIP 报告包一并交付。</p>
        <div class="badge {status_class}">任务状态：{_html(status)}</div>
      </header>

      {_result_summary(task, artifacts)}

      <section class="callout">
        <h2>解释边界</h2>
        <p>本报告用于科研分析流程复核，不提供临床诊断。PSD、QC 和 ERP 指标需要结合采集导联配置（montage）、参考方式、伪迹情况、事件语义和研究设计解释。</p>
        <ul>
          <li>PSD / 频段功率指标需要可读 EEG 通道和伪迹敏感的质控记录。</li>
          <li>ERP 指标需要有效事件标记和经过确认的条件语义。</li>
          <li>TFR、PAC/CFC 和 connectivity 在 V01 中不作为稳定结论输出。</li>
        </ul>
      </section>

      <section>
        <h2>任务记录</h2>
        <table><tbody>{_task_table(task)}</tbody></table>
      </section>

      <section>
        <h2>交付文件</h2>
        {_artifact_table(artifacts)}
      </section>

      <section>
        <h2>分析摘要与复现记录</h2>
        <div class="grid">{_summaries(task_output_dir)}</div>
      </section>

      <footer>Generated by QLanalyser EEG V01. Full machine-readable tables and reproducibility files are included in the ZIP package.</footer>
    </main>
  </body>
</html>
""",
        encoding="utf-8",
    )
    return html_path
