from __future__ import annotations

import argparse
import json
from pathlib import Path

from adapt_ernie_ti_example_to_standard import DEFAULT_OUTPUT, build_payload
from build_standard_simnibs_delivery import build_delivery


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the standardized report for the existing ernie TI example.")
    parser.add_argument("--source", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--pdf", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source = args.source.resolve()
    payload_path = source / "standard_report_data.json"
    payload_path.write_text(json.dumps(build_payload(source), ensure_ascii=False, indent=2), encoding="utf-8")
    result = build_delivery(payload_path, export_pdf=args.pdf)
    result["payload"] = str(payload_path)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
