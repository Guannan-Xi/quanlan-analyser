from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from simnibs_delivery import validate_project_config


DIRECTORIES = ("input", "results", "figures", "tables", "packages", "quality_control", "reproducibility")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a standard SimNIBS service-project directory.")
    parser.add_argument("config", type=Path, help="simnibs.service-project.v1 JSON file")
    parser.add_argument("output", type=Path, help="New or existing empty project directory")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config_path = args.config.resolve()
    output = args.output.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    validate_project_config(config)

    output.mkdir(parents=True, exist_ok=True)
    existing = [path for path in output.iterdir() if path.name != "project.json"]
    if existing:
        raise FileExistsError(f"Output directory is not empty: {output}")
    for name in DIRECTORIES:
        (output / name).mkdir(exist_ok=True)
    shutil.copy2(config_path, output / "project.json")
    status = {
        "schema_version": "simnibs.service-project-status.v1",
        "project_id": config["project"]["project_id"],
        "stage": "input_pending",
        "report_status": "blocked",
        "blocking_items": ["MRI/头模型、刺激参数和靶区定义尚未完成项目级审核"],
    }
    (output / "PROJECT_STATUS.json").write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": "created", "project": str(output), "directories": len(DIRECTORIES)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
