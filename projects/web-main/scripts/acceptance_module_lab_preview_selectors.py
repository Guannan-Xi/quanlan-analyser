from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "work" / "release_evidence" / "module_lab_preview_selectors" / "acceptance_module_lab_preview_selectors.json"

EXPECTED = {
}

RUNNABLE_EXPECTED = {
    "tfr": "TFR / ERSP / ITC",
    "multitaper_psd_tfr": "Multitaper PSD / TFR",
    "pac": "PAC / CFC",
    "reference_csd": "Reference / CSD",
    "connectivity": "Sensor Connectivity",
}


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover
        OUT.parent.mkdir(parents=True, exist_ok=True)
        payload = {"status": "failed", "error": f"playwright import failed: {exc}"}
        OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1

    result: dict[str, object] = {"status": "failed", "checks": {}}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto("http://127.0.0.1:4174/module-lab.html?api=http://127.0.0.1:8001/api&acceptance=pac-beta-ui-only", wait_until="domcontentloaded")
        page.wait_for_timeout(1500)
        checks: dict[str, bool] = {}
        for testid, label in EXPECTED.items():
            locator = page.locator(f'[data-testid="{testid}"]')
            checks[testid] = locator.count() == 1 and label in locator.inner_text()
        for module_id, label in RUNNABLE_EXPECTED.items():
            locator = page.locator(f'[data-runner-form="{module_id}"]')
            card = page.locator(f'[data-module-card="{module_id}"]')
            checks[f"module-runnable-{module_id}"] = locator.count() == 1 and card.count() == 1 and label in card.inner_text()
        result = {
            "status": "passed" if all(checks.values()) else "failed",
            "url": page.url,
            "checks": checks,
            "expected_count": len(EXPECTED) + len(RUNNABLE_EXPECTED),
            "actual_count": sum(1 for passed in checks.values() if passed),
        }
        browser.close()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
