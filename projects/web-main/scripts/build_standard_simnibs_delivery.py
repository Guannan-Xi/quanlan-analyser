from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

from simnibs_delivery import render_report, validate_delivery


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a standardized SimNIBS service report from a v2 payload.")
    parser.add_argument("payload", type=Path, help="Path to a simnibs.delivery.v2 JSON payload")
    parser.add_argument("--html", type=Path, help="Output HTML path; defaults to report.html beside the payload")
    parser.add_argument("--pdf", action="store_true", help="Also export report.pdf with Microsoft Edge")
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def find_edge() -> Path:
    candidates = [
        Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Microsoft/Edge/Application/msedge.exe",
        Path(os.environ.get("PROGRAMFILES", "")) / "Microsoft/Edge/Application/msedge.exe",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("Microsoft Edge is required for PDF export")


def main() -> None:
    args = parse_args()
    payload_path = args.payload.resolve()
    root = payload_path.parent
    data = json.loads(payload_path.read_text(encoding="utf-8"))
    validate_delivery(data, root=root)

    html_path = (args.html or root / "report.html").resolve()
    if html_path.parent != root:
        raise ValueError("The HTML must be written beside the payload so relative artifact links remain valid")
    html_path.write_text(render_report(data, root=root), encoding="utf-8")

    generated = [payload_path, html_path]
    if args.pdf:
        pdf_path = root / "report.pdf"
        completed = subprocess.run(
            [str(find_edge()), "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={pdf_path}", html_path.as_uri()],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if completed.returncode != 0 or not pdf_path.is_file() or pdf_path.stat().st_size == 0:
            raise RuntimeError(f"PDF export failed: {completed.stderr[-1000:]}")
        generated.append(pdf_path)

    publication_index_path = root / "publication_index.json"
    publication_index = {
        "schema_version": "simnibs.publication-index.v1",
        "project_id": data["project"]["project_id"],
        "figures": [
            {
                "figure_id": item["figure_id"],
                "category": item["category"],
                "title": item["title"],
                "conclusion": item["conclusion"],
                "image": item["image"],
                "vector": item.get("vector"),
                "pdf": item.get("pdf"),
                "source_data": item["source_data"],
            }
            for item in data["figures"]
        ],
    }
    publication_index_path.write_text(json.dumps(publication_index, ensure_ascii=False, indent=2), encoding="utf-8")
    generated.append(publication_index_path)

    declared_artifacts = []
    for item in data["artifacts"]:
        artifact_path = root / item["path"]
        entry = dict(item)
        if artifact_path.is_file() and artifact_path.name != "standard_manifest.json":
            entry.update({"bytes": artifact_path.stat().st_size, "sha256": sha256(artifact_path)})
        declared_artifacts.append(entry)

    manifest = {
        "schema_version": "simnibs.delivery.manifest.v2",
        "project_id": data["project"]["project_id"],
        "generated_files": [
            {"path": path.name, "bytes": path.stat().st_size, "sha256": sha256(path)} for path in generated
        ],
        "declared_artifacts": declared_artifacts,
    }
    manifest_path = root / "standard_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": "complete", "html": str(html_path), "files": len(generated)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
