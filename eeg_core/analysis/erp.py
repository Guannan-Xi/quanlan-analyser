import csv
import json
from pathlib import Path


def run_erp(input_path: str | Path, output_dir: str | Path, parameters: dict) -> dict[str, Path]:
    output_path = Path(output_dir)
    tables = output_path / "tables"
    reproducibility = output_path / "reproducibility"
    for directory in (tables, reproducibility):
        directory.mkdir(parents=True, exist_ok=True)

    metrics_path = tables / "erp_metrics.csv"
    with metrics_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["component", "window_ms", "amplitude_uv", "latency_ms"])
        writer.writeheader()
        writer.writerow(
            {
                "component": "P300",
                "window_ms": "280-420",
                "amplitude_uv": "placeholder",
                "latency_ms": "placeholder",
            }
        )

    parameters_path = reproducibility / "parameters.json"
    parameters_path.write_text(
        json.dumps({"input": str(input_path), "module": "erp", "parameters": parameters}, indent=2),
        encoding="utf-8",
    )

    method_path = reproducibility / "method_description.txt"
    method_path.write_text("ERP/P300 analysis placeholder pending MNE event handling.\n", encoding="utf-8")

    return {
        "erp_metrics": metrics_path,
        "parameters": parameters_path,
        "method_description": method_path,
    }

