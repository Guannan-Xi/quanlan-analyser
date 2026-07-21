import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_ACCEPTANCE = ROOT / "work" / "acceptance" / "v01_acceptance_latest.json"
DEFAULT_OUTPUT = ROOT / "work" / "release_evidence" / "20260620-report-zip-evidence-matrix" / "report_zip_evidence_matrix.json"


REQUIREMENTS = [
    {
        "claim": "V01 report package exposes a stable report package contract.",
        "evidence_type": "manifest",
        "required": ["reports/report_manifest.json"],
        "manifest_checks": {
            "contract_version": "qlanalyser-report-package-v0.1",
        },
    },
    {
        "claim": "Report package is bound to the current PSD task, not a static demo artifact.",
        "evidence_type": "manifest",
        "required": ["reports/report_manifest.json"],
        "manifest_checks_from_summary": {
            "report_id": "report_id",
            "task_id": "tasks.psd",
        },
    },
    {
        "claim": "Report package contains customer-readable HTML report.",
        "evidence_type": "report",
        "required": ["reports/report.html"],
    },
    {
        "claim": "Report package contains PSD result tables.",
        "evidence_type": "table",
        "required": ["tables/band_power.csv", "tables/channel_band_power.csv"],
    },
    {
        "claim": "Report package contains PSD figures.",
        "evidence_type": "figure",
        "required": ["figures/psd_mean_spectrum.svg", "figures/psd_band_power.svg"],
    },
    {
        "claim": "Report package preserves method parameters and reproducibility records.",
        "evidence_type": "reproducibility",
        "required": [
            "reproducibility/parameters.json",
            "reproducibility/software_versions.json",
            "reproducibility/workflow.json",
            "reproducibility/method_description.txt",
            "reproducibility/psd_summary.json",
        ],
    },
    {
        "claim": "Report package contains task result contract files for audit/debug.",
        "evidence_type": "contract",
        "required": ["result.json", "manifest.json", "log.txt"],
    },
]


def nested(summary: dict, path: str):
    value = summary
    for part in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def read_json_from_zip(zf: zipfile.ZipFile, name: str) -> dict:
    return json.loads(zf.read(name).decode("utf-8"))


def build_matrix(summary_path: Path = DEFAULT_ACCEPTANCE) -> dict:
    if not summary_path.exists():
        raise AssertionError(f"Acceptance summary missing: {summary_path}. Run scripts/acceptance_v01_full.py first.")

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    package_path = Path(summary["package_path"])
    if not package_path.exists():
        raise AssertionError(f"Report package missing: {package_path}")

    with zipfile.ZipFile(package_path) as zf:
        names = sorted({name.replace("\\", "/") for name in zf.namelist()})
        info_by_name = {info.filename.replace("\\", "/"): info for info in zf.infolist()}
        report_manifest = read_json_from_zip(zf, "reports/report_manifest.json")

        matrix = []
        for requirement in REQUIREMENTS:
            required = requirement["required"]
            present = [name for name in required if name in names and info_by_name[name].file_size > 0]
            missing = [name for name in required if name not in present]
            checks = []

            for key, expected in requirement.get("manifest_checks", {}).items():
                actual = report_manifest.get(key)
                checks.append({
                    "field": key,
                    "expected": expected,
                    "actual": actual,
                    "ok": actual == expected,
                })

            for key, summary_path_key in requirement.get("manifest_checks_from_summary", {}).items():
                expected = nested(summary, summary_path_key)
                actual = report_manifest.get(key)
                checks.append({
                    "field": key,
                    "expected_from_summary": summary_path_key,
                    "expected": expected,
                    "actual": actual,
                    "ok": actual == expected,
                })

            matrix.append({
                "claim": requirement["claim"],
                "evidence_type": requirement["evidence_type"],
                "required": required,
                "present": present,
                "missing": missing,
                "manifest_checks": checks,
                "status": "passed" if not missing and all(check["ok"] for check in checks) else "failed",
            })

    status = "passed" if all(row["status"] == "passed" for row in matrix) else "failed"
    return {
        "status": status,
        "source_acceptance": str(summary_path),
        "package_path": str(package_path),
        "report_id": summary.get("report_id"),
        "task_id": summary.get("tasks", {}).get("psd"),
        "file_count": len(names),
        "matrix": matrix,
        "all_files": names,
    }


def main() -> None:
    output_path = DEFAULT_OUTPUT
    if len(sys.argv) > 1:
        output_path = Path(sys.argv[1])
        if not output_path.is_absolute():
            output_path = ROOT / output_path

    matrix = build_matrix()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(matrix, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": matrix["status"],
        "output_path": str(output_path),
        "package_path": matrix["package_path"],
        "claims": len(matrix["matrix"]),
        "failed_claims": [row["claim"] for row in matrix["matrix"] if row["status"] != "passed"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
