from __future__ import annotations

import json
import re
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EDF_UI_EVIDENCE = ROOT / "work" / "release_evidence" / "edf_upload_to_results_ui_only" / "edf_upload_to_results_ui_only.json"
OUT_PATH = ROOT / "work" / "release_evidence" / "virtual_reviewer_round_008" / "v01_no_group_statistics_boundary.json"

SCANNED_FRONTEND_FILES = [
    ROOT / "frontend" / "index.html",
    ROOT / "frontend" / "expert-entry-demo.html",
    ROOT / "frontend" / "app.js",
]

FORBIDDEN_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"\bpaired\s+t\s*test\b",
        r"\bFDR\b",
        r"\bcluster\s+permutation\b",
        r"\bp[-_ ]?value\b",
        r"\bsignificant\b",
        r"\bsignificance\b",
        r"\bgrand\s+average\b",
        r"\bstatistics_summary\.csv\b",
        r"\bsubject[- ]level\b",
        r"每位被试",
        r"组统计",
        r"组水平统计",
        r"组间",
        r"多重比较",
        r"统计显著",
        r"显著差异",
        r"效应量",
        r"置信区间",
        r"统计表",
        r"统计路径",
        r"统计摘要",
        r"集群统计",
        r"置换检验",
    ]
]

ALLOWED_BOUNDARY_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"\bno\b[^.\n\r]*(p[-_ ]?value|significance|group|cluster|statistics)",
        r"\bnot\b[^.\n\r]*(p[-_ ]?value|significance|group|cluster|statistics|enabled|applicable)",
        r"\bdoes\s+not\b[^.\n\r]*(p[-_ ]?value|significance|group|cluster|statistics|output)",
        r"\bwithout\b[^.\n\r]*(group|statistics|significance|p[-_ ]?value)",
        r"\bdisabled\b[^.\n\r]*(V01|group|statistics|cluster)",
        r"\bfuture\b[^.\n\r]*(gate|group|statistics|cluster)",
        r"\bblocked\b[^.\n\r]*(unless|until|group|statistics|cluster)",
        r"\bpreview_not_enabled\b",
        r"\bnot_applicable\b",
        r"不做[^。\n\r]*(显著性|组统计|组间|因果|诊断|统计)",
        r"不输出[^。\n\r]*(p 值|p值|显著性|组统计|组间|统计)",
        r"不得[^。\n\r]*(显著|组统计|组间|因果|诊断|脑区)",
        r"禁止[^。\n\r]*(显著|组统计|组间|因果|诊断|脑区)",
        r"未启用[^。\n\r]*(组统计|显著性|cluster|统计)",
        r"未来[^。\n\r]*(gate|组统计|统计|显著性)",
        r"上线前[^。\n\r]*(必须|强制|gate|检查)",
        r"边界[^。\n\r]*(检查|说明|记录)",
        r"只输出[^。\n\r]*(描述性|MI|comodulogram|表格)",
        r"单份数据[^。\n\r]*(描述|不适用)",
    ]
]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def is_allowed_boundary(text: str) -> bool:
    if re.fullmatch(r'\s*"(p_value|significance|group_comparison|cluster_statistics|cluster_permutation)"\s*,?\s*', text):
        return True
    return any(pattern.search(text) for pattern in ALLOWED_BOUNDARY_PATTERNS)


def line_findings(source: str, text: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        compact = line.strip()
        if not compact:
            continue
        for pattern in FORBIDDEN_PATTERNS:
            match = pattern.search(compact)
            if match and not is_allowed_boundary(compact):
                findings.append(
                    {
                        "source": source,
                        "line": line_no,
                        "pattern": pattern.pattern,
                        "match": match.group(0),
                        "context": compact[:500],
                    }
                )
    return findings


def find_report_zip(evidence: dict[str, Any]) -> Path | None:
    for item in evidence.get("downloads") or []:
        if item.get("requirement") == "report package zip":
            path = Path(str(item.get("path", "")))
            return path if path.exists() else None
    return None


def scan_report_zip(report_zip: Path | None) -> tuple[list[str], list[dict[str, Any]]]:
    scanned_entries: list[str] = []
    findings: list[dict[str, Any]] = []
    if report_zip is None:
        return scanned_entries, [{"source": "report_zip", "line": None, "pattern": "missing_report_zip", "match": "", "context": "Latest UI evidence has no readable report package ZIP."}]

    text_suffixes = {".json", ".csv", ".txt", ".html", ".md", ".tsv", ".svg", ".xml"}
    with zipfile.ZipFile(report_zip) as zf:
        for name in sorted(zf.namelist()):
            suffix = Path(name).suffix.lower()
            if suffix not in text_suffixes:
                continue
            try:
                text = zf.read(name).decode("utf-8")
            except UnicodeDecodeError:
                continue
            scanned_entries.append(name)
            findings.extend(line_findings(f"{report_zip}!{name}", text))
    return scanned_entries, findings


def main() -> int:
    missing_files = [str(path) for path in [EDF_UI_EVIDENCE, *SCANNED_FRONTEND_FILES] if not path.exists()]
    frontend_findings: list[dict[str, Any]] = []
    ui_findings: list[dict[str, Any]] = []
    report_findings: list[dict[str, Any]] = []
    report_zip: Path | None = None
    scanned_report_entries: list[str] = []

    if not missing_files:
        for path in SCANNED_FRONTEND_FILES:
            frontend_findings.extend(line_findings(str(path), path.read_text(encoding="utf-8")))

        ui_evidence = read_json(EDF_UI_EVIDENCE)
        report_zip = find_report_zip(ui_evidence)
        ui_findings.extend(line_findings(str(EDF_UI_EVIDENCE), json.dumps(ui_evidence, ensure_ascii=False, indent=2)))
        scanned_report_entries, report_findings = scan_report_zip(report_zip)

    findings = frontend_findings + ui_findings + report_findings
    status = "passed" if not missing_files and not findings else "failed"
    result = {
        "schema_version": "qlanalyser-v01-no-group-statistics-boundary-v0.1",
        "generated_at": datetime.now(UTC).isoformat(),
        "status": status,
        "scope": "V01 current user-visible frontend, latest UI-only evidence, and latest report ZIP must not present group statistics, p-values, FDR, cluster permutation, grand-average, or significance as enabled product outputs.",
        "important_boundary": "This checker enforces product wording/artifact boundaries only; it is not a statistics approval, release pass, or clinical/scientific interpretation verdict.",
        "scanned_frontend_files": [str(path) for path in SCANNED_FRONTEND_FILES],
        "ui_evidence_path": str(EDF_UI_EVIDENCE),
        "report_zip_path": str(report_zip) if report_zip else None,
        "scanned_report_entries_count": len(scanned_report_entries),
        "missing_files": missing_files,
        "findings": findings,
        "blockers": [f"{item['source']}:{item.get('line')}: {item['match']}" for item in findings],
        "allow_policy": "Boundary text is allowed only when it explicitly says no/not/disabled/future/blocked/forbidden/non-enabled for V01 group/statistics/cluster/significance claims.",
        "what_07_can_consume_next": [
            "Use this as a V01 product-boundary checker before exposing any group statistics, significance, FDR, cluster permutation, or grand-average UI.",
            "Keep current V01 reports as single-record descriptive outputs unless a future statistics gate is implemented and passed.",
            "Do not read this checker as a statistics approval or release pass.",
        ],
        "07A_SHORT_PACKET_METRICS": {
            "mini/script packet count": 1,
            "script packet used": "V01 no group-statistics boundary checker",
            "GPT-5.5 low-value work avoided": "keyword inventory, frontend path scan, UI evidence scan, and report ZIP text scan are scripted",
            "concurrency frontier": "single deterministic checker over current frontend, latest UI evidence, and latest report ZIP",
            "long-term platform asset produced": "reusable V01 statistics-boundary gate for future runner/report review",
            "owner boundary respected": "yes",
            "handoff target": "07 main owner",
        },
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
