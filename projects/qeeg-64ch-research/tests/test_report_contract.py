from pathlib import Path

import matplotlib.image as mpimg
import numpy as np

from qlanalyser_eeg64.report import DESIGN_SPEC, _COMPLEXITY_METRICS, _plot_complexity, validate_report_output
from qlanalyser_eeg64.registry import METHOD_REGISTRY


def test_complexity_figure_uses_independent_metric_panels(tmp_path):
    rows = []
    for channel in range(4):
        row = {"channel": f"C{channel}"}
        for index, (key, _, _) in enumerate(_COMPLEXITY_METRICS, start=1):
            row[key] = float(index + channel / 10)
        rows.append(row)
    path = tmp_path / "complexity.png"
    _plot_complexity({"complexity": {"channel_metrics": rows}}, path)
    image = mpimg.imread(path)
    assert image.shape[1] == DESIGN_SPEC["canvas"]["width_px"]
    assert image.shape[0] > 1000


def test_report_smoke_check_requires_all_report_artifacts(tmp_path):
    (tmp_path / "assets").mkdir()
    for filename in ("analysis_summary.json", "report.html", "technical-details.html", "visual_manifest.json"):
        (tmp_path / filename).write_text("<html>ok</html>", encoding="utf-8")
    for filename in (
        "qc_full_recording_comparison.png",
        "spectral_overview.png",
        "bandpower_topographies.png",
        "gfp_microstates.png",
        "complexity_overview.png",
        "connectivity_overview.png",
        "cross_frequency_coupling.png",
    ):
        path = tmp_path / "assets" / filename
        mpimg.imsave(path, np.ones((2, 2, 3)))
    assert validate_report_output(tmp_path)["status"] == "passed"


def test_registry_declares_recovered_html_renderer():
    assert METHOD_REGISTRY["clinical_report_renderer"]["status"] == "implemented"
