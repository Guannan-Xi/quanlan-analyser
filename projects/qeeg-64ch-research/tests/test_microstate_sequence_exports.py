import csv
import hashlib
import json
from collections import defaultdict

import matplotlib.image as mpimg
import numpy as np

from qlanalyser_eeg64.expanded_report import (
    MICROSTATE_SEQUENCE_EXPORT_SCHEMA_VERSION,
    MICROSTATE_SEQUENCE_METHOD_VERSION,
    _microstate_method_atlas_html,
    write_microstate_sequence_dynamics_outputs,
)
from qlanalyser_eeg64.microstates import compute_microstate_sequence_dynamics


def _summary():
    dynamics = compute_microstate_sequence_dynamics(
        list("AABBABBBCCAC"),
        ["A", "B", "C", "D"],
        100.0,
    )
    return {"microstates": {"sequence_dynamics": dynamics}}


def test_sequence_outputs_have_versioned_tables_manifest_and_valid_figures(tmp_path):
    files = write_microstate_sequence_dynamics_outputs(_summary(), tmp_path)
    table_dir = tmp_path / "tables" / "sequence_dynamics"
    manifest = json.loads((table_dir / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["schema_version"] == MICROSTATE_SEQUENCE_EXPORT_SCHEMA_VERSION
    assert manifest["method_version"] == MICROSTATE_SEQUENCE_METHOD_VERSION
    assert [entry["path"] for entry in manifest["tables"]] == [
        "tables/sequence_dynamics/markov_transition_entropy.csv",
        "tables/sequence_dynamics/transition_syntax_residuals.csv",
        "tables/sequence_dynamics/block_entropy.csv",
        "tables/sequence_dynamics/lempel_ziv.csv",
        "tables/sequence_dynamics/dwell_survival.csv",
        "tables/sequence_dynamics/duration_summary.csv",
        "tables/sequence_dynamics/per_second_distribution.csv",
    ]
    for entry in manifest["tables"]:
        path = tmp_path / entry["path"]
        assert path.is_file()
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.reader(handle)
            header = next(reader)
            rows = list(reader)
        assert header == entry["header"]
        assert len(rows) == entry["row_count"]
        assert path.stat().st_size == entry["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]
        assert all(
            cell.lower() not in {"nan", "inf", "+inf", "-inf"}
            for row in rows
            for cell in row
        )

    lz_rows = list(csv.DictReader((table_dir / "lempel_ziv.csv").open(encoding="utf-8")))
    assert [row["scope"] for row in lz_rows] == ["pooled", "continuous_block"]
    assert lz_rows[0]["normalization_formula"] == "c(n) * log_K(n) / n"
    assert lz_rows[0]["raw_phrase_count_c_n"] == "7"
    assert lz_rows[1]["block_index"] == "0"
    assert lz_rows[1]["status"] == "ok"

    assert set(files) == {
        "micro_sample_markov",
        "micro_sequence_dynamics",
        "micro_transition_syntax",
        "micro_dwell_survival",
    }
    for filename in files.values():
        image = mpimg.imread(tmp_path / "assets" / filename)
        assert image.shape == (1080, 1800, 4)
        assert float(np.asarray(image).var()) > 0


def test_sequence_exports_are_byte_deterministic(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    write_microstate_sequence_dynamics_outputs(_summary(), first)
    write_microstate_sequence_dynamics_outputs(_summary(), second)

    relative_files = [
        "tables/sequence_dynamics/markov_transition_entropy.csv",
        "tables/sequence_dynamics/transition_syntax_residuals.csv",
        "tables/sequence_dynamics/block_entropy.csv",
        "tables/sequence_dynamics/lempel_ziv.csv",
        "tables/sequence_dynamics/dwell_survival.csv",
        "tables/sequence_dynamics/duration_summary.csv",
        "tables/sequence_dynamics/per_second_distribution.csv",
        "tables/sequence_dynamics/manifest.json",
        "assets/microstate_sample_markov_matrix.png",
        "assets/microstate_sequence_dynamics.png",
        "assets/microstate_transition_syntax.png",
        "assets/microstate_dwell_survival.png",
    ]
    for relative in relative_files:
        assert (first / relative).read_bytes() == (second / relative).read_bytes()


def test_legacy_summary_without_sequence_dynamics_is_unchanged(tmp_path):
    assert write_microstate_sequence_dynamics_outputs({"microstates": {}}, tmp_path) == {}
    assert not (tmp_path / "tables").exists()


def test_method_atlas_exposes_each_sequence_method_and_structured_result():
    files = defaultdict(lambda: "placeholder.png")
    files.update(
        {
            "micro_sample_markov": "microstate_sample_markov_matrix.png",
            "micro_sequence_dynamics": "microstate_sequence_dynamics.png",
            "micro_transition_syntax": "microstate_transition_syntax.png",
            "micro_dwell_survival": "microstate_dwell_survival.png",
        }
    )

    atlas = _microstate_method_atlas_html(_summary(), files)

    assert 'id="microstate-method-atlas"' in atlas
    assert "microstate_sample_markov_matrix.png" in atlas
    assert "microstate_transition_syntax.png" in atlas
    assert "microstate_dwell_survival.png" in atlas
    assert "Markov" in atlas
    assert "Jump-chain" in atlas
    assert "LZ76" in atlas
    assert "ECDF" in atlas
    for name in (
        "markov_transition_entropy.csv",
        "transition_syntax_residuals.csv",
        "block_entropy.csv",
        "lempel_ziv.csv",
        "duration_summary.csv",
        "per_second_distribution.csv",
    ):
        assert name in atlas
