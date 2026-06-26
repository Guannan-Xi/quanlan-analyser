import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    latest = ROOT / "work" / "acceptance" / "v01_acceptance_latest.json"
    if not latest.exists():
        raise AssertionError("Run scripts/acceptance_v01_full.py before report ZIP contract acceptance.")

    summary = json.loads(latest.read_text(encoding="utf-8"))
    package_path = Path(summary["package_path"])
    if not package_path.exists():
        raise AssertionError(f"Report package missing: {package_path}")

    required_suffixes = {
        "reports/report.html",
        "reports/report_manifest.json",
        "reports/report.pdf",
        "reports/report.json",
        "tables/metrics.csv",
        "result.json",
        "manifest.json",
        "log.txt",
        "reproducibility/parameters.json",
        "reproducibility/software_versions.json",
        "reproducibility/workflow.json",
        "reproducibility/method_description.txt",
    }
    with zipfile.ZipFile(package_path) as zf:
        names = set(zf.namelist())
        normalized = {name.replace("\\", "/") for name in names}
        missing = [suffix for suffix in sorted(required_suffixes) if not any(name.endswith(suffix) for name in normalized)]
        if missing:
            raise AssertionError(f"Report package missing required reproducibility files: {missing}; files={sorted(normalized)[:80]}")
        non_empty = [info.filename for info in zf.infolist() if info.file_size > 0]
        if len(non_empty) < len(required_suffixes):
            raise AssertionError("Report package contains too few non-empty files")
        report_manifest = json.loads(zf.read("reports/report_manifest.json").decode("utf-8"))
        report_html = zf.read("reports/report.html").decode("utf-8", errors="replace")
        public_html_forbidden = [
            "D:\\",
            "D:/",
            "Acceptance PSD Report",
            "Registered artifacts",
            "Task metadata",
            "Clinical/research interpretation guardrails",
            "Not generated for this task",
            "<th>Path</th>",
        ]
        hits = [item for item in public_html_forbidden if item in report_html]
        if hits:
            raise AssertionError(f"Customer report HTML exposes internal/debug copy: {hits}")
        if "解释边界" not in report_html or "交付文件" not in report_html or "软件版本" not in report_html:
            raise AssertionError("Customer report HTML is missing localized trust/report sections")
        manifest_text = zf.read("manifest.txt").decode("utf-8", errors="replace")
        public_manifest_text = json.dumps(report_manifest, ensure_ascii=False) + "\n" + manifest_text
        if "D:\\" in public_manifest_text or "D:/" in public_manifest_text or "C:\\Users" in public_manifest_text or "C:/Users" in public_manifest_text:
            raise AssertionError("Report public manifests expose host filesystem paths")
        customer_text_suffixes = (".json", ".txt", ".log", ".csv", ".tsv", ".md", ".html", ".xml", ".yaml", ".yml")
        host_path_hits = []
        for name in sorted(normalized):
            if not name.lower().endswith(customer_text_suffixes):
                continue
            text = zf.read(name).decode("utf-8", errors="replace")
            if "D:\\" in text or "D:/" in text or "C:\\Users" in text or "C:/Users" in text:
                host_path_hits.append(name)
        if host_path_hits:
            raise AssertionError(f"Report ZIP text payload exposes host filesystem paths: {host_path_hits}")
        if report_manifest.get("contract_version") != "qlanalyser-report-package-v0.1":
            raise AssertionError(f"Unexpected report package contract: {report_manifest}")
        if report_manifest.get("report_id") != summary.get("report_id"):
            raise AssertionError(f"Report manifest does not match acceptance report_id: {report_manifest}")
        if report_manifest.get("task_id") != summary.get("tasks", {}).get("psd"):
            raise AssertionError(f"Report manifest does not match current task_id: {report_manifest}")
        if not report_manifest.get("artifact_count"):
            raise AssertionError(f"Report manifest has no registered artifacts: {report_manifest}")

    print(json.dumps({
        "status": "passed",
        "package_path": str(package_path),
        "report_manifest": report_manifest,
        "required_suffixes": sorted(required_suffixes),
        "file_count": len(names),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
