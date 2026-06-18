import json
from html import escape
from pathlib import Path
from typing import Any


SUMMARY_FILES = {
    "QC summary": "reproducibility/qc_summary.json",
    "PSD summary": "reproducibility/psd_summary.json",
    "ERP summary": "reproducibility/erp_summary.json",
    "Software versions": "reproducibility/software_versions.json",
    "Workflow": "reproducibility/workflow.json",
}


def _html(value: Any) -> str:
    return escape("" if value is None else str(value))


def _json_preview(payload: Any, *, max_chars: int = 5000) -> str:
    text = json.dumps(payload, ensure_ascii=False, indent=2) if not isinstance(payload, str) else payload
    if len(text) > max_chars:
        text = text[:max_chars] + "\n... truncated in HTML preview; see package files for full content."
    return _html(text)


def _read_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - defensive report rendering
        return {"status": "unreadable", "path": str(path), "error": str(exc)}


def _task_table(task: dict) -> str:
    rows = []
    for key in (
        "id",
        "project_id",
        "workflow_id",
        "module_name",
        "input_file_id",
        "status",
        "progress",
        "error_message",
        "created_at",
        "started_at",
        "finished_at",
    ):
        rows.append(f"<tr><th>{_html(key)}</th><td>{_html(task.get(key))}</td></tr>")
    params = task.get("parameters_json") or {}
    rows.append(f"<tr><th>parameters_json</th><td><pre>{_json_preview(params)}</pre></td></tr>")
    return "\n".join(rows)


def _artifact_table(artifacts: list[dict]) -> str:
    if not artifacts:
        return '<p class="muted">No task artifacts are registered yet.</p>'
    rows = []
    for artifact in artifacts:
        rows.append(
            "<tr>"
            f"<td>{_html(artifact.get('label'))}</td>"
            f"<td>{_html(artifact.get('artifact_type'))}</td>"
            f"<td>{_html(artifact.get('mime_type'))}</td>"
            f"<td>{_html(artifact.get('path'))}</td>"
            "</tr>"
        )
    return """
<table>
  <thead><tr><th>Label</th><th>Type</th><th>MIME</th><th>Path</th></tr></thead>
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
                f"<section class=\"summary-card\"><h3>{_html(title)}</h3>"
                f"<p class=\"muted\">Not generated for this task. Expected: {_html(relative_path)}</p></section>"
            )
        else:
            blocks.append(
                f"<section class=\"summary-card\"><h3>{_html(title)}</h3>"
                f"<p class=\"muted\">Source: {_html(relative_path)}</p>"
                f"<pre>{_json_preview(payload)}</pre></section>"
            )
    method_path = task_output_dir / "reproducibility" / "method_description.txt"
    if method_path.exists():
        blocks.append(
            "<section class=\"summary-card\"><h3>Method description</h3>"
            f"<pre>{_html(method_path.read_text(encoding='utf-8', errors='replace'))}</pre></section>"
        )
    return "\n".join(blocks)


def write_html_report(output_dir: str | Path, title: str, context: dict) -> Path:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    html_path = output_path / "report.html"

    task = context.get("task") or {}
    artifacts = context.get("artifacts") or []
    task_output_dir = Path(context.get("task_output_dir") or output_path)

    status = str(task.get("status") or "unknown")
    status_class = "ok" if status == "completed" else "danger" if status == "failed" else "warn"
    module_name = task.get("module_name") or "unknown"

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
      h1, h2, h3 {{ margin-top:0; }}
      table {{ border-collapse:collapse; width:100%; font-size:14px; }}
      th, td {{ border:1px solid var(--line); padding:9px 10px; text-align:left; vertical-align:top; }}
      th {{ background:#f7fafb; width:220px; }}
      pre {{ white-space:pre-wrap; word-break:break-word; background:#0e1b22; color:#e7f5f3; border-radius:12px; padding:14px; overflow:auto; }}
      .muted {{ color:var(--muted); }}
      .badge {{ display:inline-block; border-radius:999px; padding:4px 10px; color:white; font-weight:700; font-size:12px; }}
      .ok {{ background:var(--ok); }} .warn {{ background:var(--warn); }} .danger {{ background:var(--danger); }}
      .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:14px; }}
      .summary-card {{ box-shadow:none; margin:0; }}
      .callout {{ border-left:5px solid var(--accent); }}
      footer {{ color:var(--muted); padding:8px 2px 28px; }}
    </style>
  </head>
  <body>
    <main>
      <header>
        <p class="muted">QLanalyser EEG V01 ? Single-subject deliverable</p>
        <h1>{_html(title)}</h1>
        <p>Module: <strong>{_html(module_name)}</strong> ? Status: <span class="badge {status_class}">{_html(status)}</span></p>
      </header>

      <section class="callout">
        <h2>Clinical/research interpretation guardrails</h2>
        <p>This report summarizes computational EEG outputs for research workflow review. It does not provide a clinical diagnosis. Interpret PSD, QC, and ERP metrics with the acquisition montage, reference, artifact profile, marker semantics, and study design.</p>
        <ul>
          <li>PSD/band-power metrics require readable EEG channels and artifact-aware QC.</li>
          <li>ERP metrics require valid event markers/annotations and verified condition semantics.</li>
          <li>TFR, PAC/CFC, and connectivity are intentionally not enabled in V01 until preprocessing, artifact controls, surrogate/statistical validation, and reference/volume-conduction controls are configured.</li>
        </ul>
      </section>

      <section>
        <h2>Task metadata</h2>
        <table><tbody>{_task_table(task)}</tbody></table>
      </section>

      <section>
        <h2>Registered artifacts</h2>
        {_artifact_table(artifacts)}
      </section>

      <section>
        <h2>Analysis summaries and reproducibility</h2>
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
