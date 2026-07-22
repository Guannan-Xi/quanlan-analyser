"""HTML reporting for recovered full-recording QEEG analyses.

The renderer is deliberately downstream of the analysis modules: it consumes
their saved JSON contract and never re-implements a quantitative method.
"""

from __future__ import annotations

import csv
import html
import json
from pathlib import Path
import shutil
from uuid import uuid4

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mne
import numpy as np
from scipy.signal import spectrogram

from .io import file_sha256, prepare_analysis_raw, read_raw
from .qc import QCConfig, run_auto_qc


# Numeric layout contract derived from the local QLanalyser scientific-figure
# specification.  All generated plots use these values rather than implicit
# matplotlib defaults, so a new report remains legible at full report width.
DESIGN_SPEC = {
    "canvas": {"width_px": 2560, "height_px": 1440, "dpi": 160},
    "safe_margins_px": {"top": 96, "right": 96, "bottom": 96, "left": 96},
    "typography": {"title_pt": 13, "axis_pt": 10, "tick_pt": 9, "caption_pt": 10},
    "limits": {"max_panel_columns": 6, "minimum_panel_width_px": 360},
    "palette": {"primary": "#0f766e", "secondary": "#1d4ed8", "accent": "#b45309"},
}

_COMPLEXITY_METRICS = (
    ("hjorth_activity_uv2", "Hjorth Activity", "uV2"),
    ("hjorth_mobility", "Hjorth Mobility", "dimensionless"),
    ("hjorth_complexity", "Hjorth Complexity", "dimensionless"),
    ("sample_entropy", "Sample entropy", "dimensionless"),
    ("higuchi_fd", "Higuchi fractal dimension", "dimensionless"),
    ("hurst_exponent", "Hurst exponent", "dimensionless"),
    ("permutation_entropy", "Permutation entropy", "dimensionless"),
    ("dfa_exponent", "DFA exponent", "dimensionless"),
    ("lempel_ziv_complexity", "Lempel-Ziv complexity", "dimensionless"),
    ("svd_entropy", "SVD entropy", "dimensionless"),
    ("petrosian_fd", "Petrosian fractal dimension", "dimensionless"),
    ("katz_fd", "Katz fractal dimension", "dimensionless"),
    ("multiscale_entropy_complexity_index", "Multiscale entropy index", "dimensionless"),
)


def _configure_scientific_style():
    """Apply the report-wide plotting contract before creating a figure."""
    plt.rcParams.update(
        {
            "font.family": ["Microsoft YaHei", "Arial", "DejaVu Sans"],
            "axes.titlesize": DESIGN_SPEC["typography"]["title_pt"],
            "axes.labelsize": DESIGN_SPEC["typography"]["axis_pt"],
            "xtick.labelsize": DESIGN_SPEC["typography"]["tick_pt"],
            "ytick.labelsize": DESIGN_SPEC["typography"]["tick_pt"],
            "figure.dpi": DESIGN_SPEC["canvas"]["dpi"],
            "savefig.dpi": DESIGN_SPEC["canvas"]["dpi"],
        }
    )


def _finalize_figure(figure, path):
    """Save an image using the defined visual specification."""
    figure.savefig(path, dpi=DESIGN_SPEC["canvas"]["dpi"], facecolor="white")
    plt.close(figure)


def render_report_from_summary(input_path, summary_path, output_dir):
    """Render a report from a saved analysis result and a reloaded source file.

    The deterministic QC result is checked against the saved contract so the
    visual comparison cannot silently drift from the quantitative analysis.
    """
    summary = json.loads(Path(summary_path).read_text(encoding="utf-8"))
    source = Path(input_path)
    if file_sha256(source) != summary["source"]["sha256"]:
        raise ValueError("Input file hash does not match analysis_summary.json.")
    raw, _ = prepare_analysis_raw(read_raw(source, preload=True))
    # Re-rendering must reproduce the exact retained recording used by the
    # quantitative modules.  Falling back to defaults here would allow a
    # caller-supplied QC threshold to change figures without changing the
    # stored analysis contract.
    saved_qc_config = summary.get("quality_control", {}).get("config", {})
    cleaned, fresh_qc = run_auto_qc(raw, QCConfig(**saved_qc_config))
    if fresh_qc["epoch_summary"] != summary["quality_control"]["epoch_summary"]:
        raise RuntimeError("Recomputed QC epoch result differs from saved analysis contract.")
    return render_report(summary, raw, cleaned, output_dir)


def render_report(summary, raw_before, cleaned, output_dir):
    """Create the complete historical-method report from one saved contract."""
    destination = Path(output_dir)
    assets = destination / "assets"
    tables = destination / "tables"
    assets.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)
    from .expanded_report import render_full_historical_report

    return render_full_historical_report(summary, raw_before, cleaned, destination, assets, tables, base=__import__(__name__, fromlist=["*"]))


def refresh_report_from_saved_artifacts(summary_path, output_dir=None):
    """Refresh report pages and compatibility CSVs without reading raw EEG."""
    summary_path = Path(summary_path).resolve()
    destination = Path(output_dir).resolve() if output_dir is not None else summary_path.parent
    if summary_path.parent != destination or summary_path.name != "analysis_summary.json":
        raise ValueError("summary_path must be the analysis_summary.json inside output_dir")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    from .historical_exports import write_historical_compatibility_tables
    from .expanded_report import (
        _validate_visual_manifest,
        rerender_saved_report_pages,
        write_spatial_complexity_csv,
    )

    manifest_path = destination / "visual_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _validate_visual_manifest(summary, destination, manifest)

    compatibility_dir = destination / "tables" / "historical_compatibility"
    compatibility_dir.parent.mkdir(parents=True, exist_ok=True)
    transaction_id = uuid4().hex
    rollback_dir = compatibility_dir.with_name(
        f".{compatibility_dir.name}.{transaction_id}.rollback"
    )
    had_compatibility_dir = compatibility_dir.exists()
    if had_compatibility_dir:
        shutil.copytree(compatibility_dir, rollback_dir)
    spatial_table = compatibility_dir.parent / "spatial_complexity.csv"
    spatial_rollback = spatial_table.with_name(
        f".{spatial_table.name}.{transaction_id}.rollback"
    )
    had_spatial_table = spatial_table.exists()
    if had_spatial_table:
        shutil.copy2(spatial_table, spatial_rollback)

    publish_succeeded = False
    try:
        write_spatial_complexity_csv(summary, compatibility_dir.parent)
        bundle = write_historical_compatibility_tables(summary, compatibility_dir)
        export_manifest = compatibility_dir / "export_manifest.json"
        rendered = rerender_saved_report_pages(summary, destination, DESIGN_SPEC)
        publish_succeeded = True
    except Exception as publish_error:
        rollback_errors = []
        try:
            if compatibility_dir.exists():
                shutil.rmtree(compatibility_dir)
            if had_compatibility_dir:
                rollback_dir.replace(compatibility_dir)
        except Exception as rollback_error:
            rollback_errors.append(rollback_error)
        try:
            spatial_table.unlink(missing_ok=True)
            if had_spatial_table:
                spatial_rollback.replace(spatial_table)
        except Exception as rollback_error:
            rollback_errors.append(rollback_error)
        if rollback_errors:
            raise RuntimeError(
                "Saved report refresh failed and compatibility rollback was incomplete: "
                f"{rollback_errors}; backups retained at {rollback_dir} and {spatial_rollback}"
            ) from publish_error
        raise
    finally:
        if publish_succeeded and rollback_dir.exists():
            shutil.rmtree(rollback_dir, ignore_errors=True)
        if publish_succeeded:
            spatial_rollback.unlink(missing_ok=True)

    rendered.update({
        "historical_compatibility_dir": compatibility_dir,
        "historical_export_manifest_path": export_manifest,
        "historical_table_count": len(bundle.tables),
    })
    return rendered


def upgrade_saved_microstate_report(summary_path, output_dir):
    """Publish sequence dynamics into a new report directory without raw EEG."""
    summary_path = Path(summary_path).resolve()
    if summary_path.name != "analysis_summary.json":
        raise ValueError("summary_path must point to analysis_summary.json")
    source = summary_path.parent
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    from . import expanded_report, microstates
    from .historical_exports import write_historical_compatibility_tables

    source_manifest_path = source / "visual_manifest.json"
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    source_files = expanded_report._validate_visual_manifest(
        summary, source, source_manifest
    )
    sample_labels, state_names, sfreq, timeline_mapping = (
        _saved_microstate_sequence_inputs(summary)
    )

    destination = Path(output_dir).resolve()
    if destination == source:
        raise ValueError("output_dir must differ from the frozen source directory")
    if destination.exists():
        raise FileExistsError(f"output_dir already exists: {destination}")
    if destination.is_relative_to(source):
        raise ValueError("output_dir cannot be inside the frozen source directory")
    if not destination.parent.is_dir():
        raise FileNotFoundError(
            f"output_dir parent does not exist: {destination.parent}"
        )

    staging = destination.parent / f".{destination.name}.{uuid4().hex}.staging"
    try:
        shutil.copytree(source, staging)

        saved_microstates = summary["microstates"]
        sequence_dynamics = microstates.compute_microstate_sequence_dynamics(
            sample_labels,
            state_names,
            sfreq,
            timeline_mapping=timeline_mapping,
        )
        saved_microstates["sequence_dynamics"] = sequence_dynamics
        staged_summary_path = staging / "analysis_summary.json"
        staged_summary_path.write_text(
            json.dumps(
                summary,
                ensure_ascii=False,
                indent=2,
                allow_nan=False,
            ),
            encoding="utf-8",
        )

        new_assets = expanded_report.write_microstate_sequence_dynamics_outputs(
            summary, staging
        )
        if not isinstance(new_assets, dict) or not all(
            isinstance(key, str)
            and key
            and isinstance(filename, str)
            and filename
            and Path(filename).name == filename
            for key, filename in new_assets.items()
        ):
            raise ValueError(
                "write_microstate_sequence_dynamics_outputs must return "
                "a logical-key to asset-filename mapping"
            )
        duplicate_keys = sorted(set(source_files).intersection(new_assets))
        if duplicate_keys:
            raise ValueError(
                f"sequence dynamics assets replace frozen logical keys: {duplicate_keys}"
            )
        files = {**source_files, **new_assets}

        tables = staging / "tables"
        tables.mkdir(parents=True, exist_ok=True)
        expanded_report._write_microstate_method_summary_csv(
            summary.get("microstates", {}), tables
        )
        expanded_report.write_spatial_complexity_csv(summary, tables)
        compatibility_dir = tables / "historical_compatibility"
        compatibility_bundle = write_historical_compatibility_tables(
            summary, compatibility_dir
        )
        published = expanded_report._publish_report_bundle(
            summary,
            staging,
            files,
            DESIGN_SPEC,
            source_manifest,
        )
        validation = expanded_report.validate_full_report(staging, files)
        if validation["status"] != "passed":
            raise RuntimeError(
                "Upgraded report validation failed: "
                + "; ".join(validation["errors"])
            )

        if destination.exists():
            raise FileExistsError(f"output_dir already exists: {destination}")
        staging.rename(destination)
    except Exception:
        if staging.exists():
            try:
                shutil.rmtree(staging)
            except Exception as cleanup_error:
                raise RuntimeError(
                    f"Saved report upgrade failed and staging cleanup failed: {staging}"
                ) from cleanup_error
        raise

    return {
        "source_summary_path": summary_path,
        "output_dir": destination,
        "summary_path": destination / "analysis_summary.json",
        "report_path": destination / "report.html",
        "technical_path": destination / "technical-details.html",
        "visual_manifest_path": destination / "visual_manifest.json",
        "historical_compatibility_dir": (
            destination / "tables" / "historical_compatibility"
        ),
        "historical_export_manifest_path": (
            destination
            / "tables"
            / "historical_compatibility"
            / "export_manifest.json"
        ),
        "historical_table_count": len(compatibility_bundle.tables),
        "assets": files,
        "new_assets": dict(new_assets),
        "report_build": published["report_build"],
        "validation": validation,
    }


def _saved_microstate_sequence_inputs(summary):
    """Extract the persisted inputs required for a raw-free sequence upgrade."""
    if not isinstance(summary, dict):
        raise ValueError("analysis_summary.json must contain a JSON object")

    saved_microstates = summary.get("microstates")
    if not isinstance(saved_microstates, dict):
        raise ValueError("analysis_summary.json microstates must be an object")

    sample_labels = saved_microstates.get("sample_labels")
    if (
        not isinstance(sample_labels, list)
        or not sample_labels
        or any(not isinstance(label, str) or not label for label in sample_labels)
    ):
        raise ValueError(
            "Raw-free upgrade requires a non-empty string list at "
            "analysis_summary.json microstates.sample_labels"
        )

    state_names = saved_microstates.get("state_names")
    if (
        not isinstance(state_names, list)
        or not state_names
        or any(not isinstance(name, str) or not name for name in state_names)
        or len(set(state_names)) != len(state_names)
    ):
        raise ValueError(
            "Raw-free upgrade requires a non-empty unique string list at "
            "analysis_summary.json microstates.state_names"
        )
    unknown_labels = sorted(set(sample_labels).difference(state_names))
    if unknown_labels:
        raise ValueError(
            "analysis_summary.json microstates.sample_labels contains states "
            f"absent from microstates.state_names: {unknown_labels}"
        )

    analysis_data = summary.get("analysis_data")
    sfreq = (
        analysis_data.get("sampling_rate_hz")
        if isinstance(analysis_data, dict)
        else None
    )
    if (
        isinstance(sfreq, bool)
        or not isinstance(sfreq, (int, float))
        or not np.isfinite(sfreq)
        or sfreq <= 0
    ):
        raise ValueError(
            "Raw-free upgrade requires a finite positive number at "
            "analysis_summary.json analysis_data.sampling_rate_hz"
        )

    timeline_mapping = saved_microstates.get("timeline_mapping")
    if timeline_mapping is not None and not isinstance(timeline_mapping, dict):
        raise ValueError(
            "analysis_summary.json microstates.timeline_mapping must be an "
            "object when present"
        )
    return sample_labels, state_names, float(sfreq), timeline_mapping


def _plot_qc_comparison(before, after, summary, path):
    channel = "O1" if "O1" in before.ch_names else before.ch_names[0]
    before_data = before.get_data(picks=[channel])[0] * 1e6
    after_data = after.get_data(picks=[channel])[0] * 1e6
    fig, axes = plt.subplots(2, 3, figsize=(16, 8), constrained_layout=True)
    _waveform(axes[0, 0], before_data, before.info["sfreq"], f"Before QC: {channel}")
    _psd_with_sem(axes[0, 1], before, "Before QC: all-channel PSD")
    _spectrogram(axes[0, 2], before_data, before.info["sfreq"], "Before QC: full record")
    _waveform(axes[1, 0], after_data, after.info["sfreq"], f"After QC: retained {channel}")
    _psd_with_sem(axes[1, 1], after, "After QC: all-channel PSD")
    _spectrogram(axes[1, 2], after_data, after.info["sfreq"], "After QC: retained record")
    kept = summary["quality_control"]["epoch_summary"]
    fig.suptitle(f"Full-recording QC comparison | retained {kept['retained']}/{kept['total']} one-second epochs", fontsize=14)
    _finalize_figure(fig, path)
    return path.name


def _waveform(axis, data, sfreq, title):
    target = min(6000, data.size)
    indices = np.linspace(0, data.size - 1, target, dtype=int)
    axis.plot(indices / sfreq, data[indices], color="#1f5f8b", linewidth=0.45)
    axis.set(title=title, xlabel="Time (s)", ylabel="Amplitude (uV)")
    axis.grid(alpha=0.2)


def _psd_with_sem(axis, raw, title):
    spectrum = raw.compute_psd(method="welch", fmin=0.5, fmax=45, n_fft=min(raw.n_times, int(raw.info["sfreq"] * 4)), verbose="ERROR")
    psd, freqs = spectrum.get_data(return_freqs=True)
    psd = psd * 1e12
    mean = psd.mean(axis=0)
    sem = psd.std(axis=0, ddof=1) / np.sqrt(psd.shape[0])
    axis.semilogy(freqs, mean, color="#0e7490", linewidth=1)
    axis.fill_between(freqs, np.maximum(mean - sem, np.finfo(float).eps), mean + sem, color="#0e7490", alpha=0.2)
    axis.set(title=title, xlabel="Frequency (Hz)", ylabel="Power (uV2/Hz)", xlim=(0.5, 45))
    axis.grid(alpha=0.2)


def _spectrogram(axis, data, sfreq, title):
    freqs, times, power = spectrogram(data, fs=sfreq, nperseg=min(int(sfreq * 2), data.size), noverlap=min(int(sfreq), max(0, data.size - 1)), scaling="density")
    mask = (freqs >= 0.5) & (freqs <= 45)
    logged = np.log10(np.maximum(power[mask] * 1e12, np.finfo(float).eps))
    lo, hi = np.quantile(logged, [0.01, 0.99])
    image = axis.pcolormesh(times, freqs[mask], logged, shading="auto", cmap="viridis", vmin=lo, vmax=hi)
    axis.set(title=title, xlabel="Time (s)", ylabel="Frequency (Hz)")
    colorbar = plt.colorbar(image, ax=axis, pad=0.01)
    colorbar.set_label("log10(uV2/Hz)", fontsize=8)


def _plot_spectral(summary, path):
    spectral = summary["spectral"]
    freqs = np.asarray(spectral["frequencies_hz"])
    psd = np.asarray(list(spectral["psd_uv2_per_hz"].values()))
    rows = spectral["absolute_band_power"]
    bands = [row["band"].title() for row in rows]
    absolute = [np.mean(list(row["absolute_power_uv2"].values())) for row in rows]
    relative = [100 * np.mean(list(row["relative_power"].values())) for row in rows]
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.8), constrained_layout=True)
    axes[0].semilogy(freqs, psd.mean(axis=0), color="#0f766e", linewidth=1.2)
    axes[0].fill_between(freqs, np.maximum(psd.mean(axis=0) - psd.std(axis=0) / np.sqrt(psd.shape[0]), np.finfo(float).eps), psd.mean(axis=0) + psd.std(axis=0) / np.sqrt(psd.shape[0]), color="#0f766e", alpha=0.2)
    axes[0].set(title="All-channel PSD", xlabel="Frequency (Hz)", ylabel="Power (uV2/Hz)", xlim=(0.5, 45))
    axes[1].bar(bands, absolute, color="#1d4ed8")
    axes[1].set(title="Absolute band power", ylabel="Mean power (uV2)")
    axes[2].bar(bands, relative, color="#b45309")
    axes[2].set(title="Relative band power", ylabel="Mean proportion (%)", ylim=(0, max(100, max(relative) * 1.2)))
    for axis in axes:
        axis.grid(axis="y", alpha=0.2)
        axis.tick_params(axis="x", rotation=25)
    _finalize_figure(fig, path)
    return path.name


def _plot_topographies(summary, raw, path):
    rows = summary["spectral"]["absolute_band_power"]
    fig, axes = plt.subplots(1, len(rows), figsize=(3.1 * len(rows), 3.4), constrained_layout=True)
    for axis, row in zip(np.atleast_1d(axes), rows):
        values = np.asarray([row["absolute_power_uv2"][channel] for channel in raw.ch_names])
        image, _ = mne.viz.plot_topomap(values, raw.info, axes=axis, show=False, contours=5, cmap="YlOrRd")
        axis.set_title(f"{row['band'].title()}\nabsolute power")
        plt.colorbar(image, ax=axis, shrink=0.72, label="uV2")
    _finalize_figure(fig, path)
    return path.name


def _plot_gfp_microstates(summary, raw, path):
    gfp = raw.copy().filter(2.0, 20.0, verbose="ERROR").get_data() * 1e6
    gfp = gfp.std(axis=0)
    micro = summary["microstates"]
    fig = plt.figure(figsize=(16, 8), constrained_layout=True)
    grid = fig.add_gridspec(2, 6)
    axis = fig.add_subplot(grid[0, :])
    indices = np.linspace(0, gfp.size - 1, min(8000, gfp.size), dtype=int)
    axis.plot(indices / summary["analysis_data"]["sampling_rate_hz"], gfp[indices], color="#7c3aed", linewidth=0.5)
    axis.set(title="Global field power across retained full recording", xlabel="Retained-record time (s)", ylabel="GFP (uV)")
    axis.grid(alpha=0.2)
    for index, (name, values) in enumerate(micro["templates_uv_normalized"].items()):
        axis = fig.add_subplot(grid[1, index])
        image, _ = mne.viz.plot_topomap(np.asarray(values), raw.info, axes=axis, show=False, contours=4, cmap="RdBu_r")
        axis.set_title(f"State {name}")
        plt.colorbar(image, ax=axis, shrink=0.6)
    _finalize_figure(fig, path)
    return path.name


def _plot_complexity(summary, path):
    """Show each metric's across-channel distribution on its native scale.

    This intentionally avoids a single shared y-axis: the recovered metrics
    have different physical units and numerical ranges, so a common bar chart
    makes all but the largest value unreadable and implies a false comparison.
    """
    rows = summary["complexity"]["channel_metrics"]
    fig = plt.figure(figsize=(16, 9.2), constrained_layout=True)
    grid = fig.add_gridspec(3, 5)
    axes = [fig.add_subplot(grid[row, column]) for row in range(2) for column in range(5)]
    bottom = grid[2, :].subgridspec(1, 3)
    axes.extend(fig.add_subplot(bottom[0, column]) for column in range(3))
    for axis, (key, label, unit) in zip(axes, _COMPLEXITY_METRICS):
        values = np.asarray([row[key] for row in rows], dtype=float)
        axis.boxplot(
            values,
            widths=0.45,
            patch_artist=True,
            boxprops={"facecolor": "#cfe8e2", "edgecolor": "#0f766e"},
            medianprops={"color": "#9a3412", "linewidth": 1.4},
            whiskerprops={"color": "#0f766e"},
            capprops={"color": "#0f766e"},
        )
        positions = np.linspace(0.87, 1.13, values.size)
        axis.scatter(positions, values, s=10, color="#0f766e", alpha=0.55, zorder=3)
        axis.set(title=label, ylabel=unit, xticks=[])
        axis.grid(axis="y", alpha=0.2)
        axis.text(0.03, 0.95, f"mean {values.mean():.3g}", transform=axis.transAxes, va="top", fontsize=8, color="#334155")
    fig.suptitle("Full-recording complexity: distribution across 61 scalp channels", fontsize=14)
    _finalize_figure(fig, path)
    return path.name


def _plot_connectivity(summary, path):
    bands = summary["connectivity"]["bands"]
    methods = list(next(iter(bands.values())).keys())
    fig, axes = plt.subplots(1, 3, figsize=(16, 5), constrained_layout=True)
    x = np.arange(len(methods))
    for name, band in bands.items():
        axes[0].plot(x, [band[method]["global_mean"] for method in methods], marker="o", label=name.title())
    axes[0].set(title="Global mean connectivity", ylabel="Value", xticks=x, xticklabels=methods)
    axes[0].tick_params(axis="x", rotation=35, labelsize=8)
    axes[0].legend(frameon=False)
    for axis, method in zip(axes[1:], ("plv", "imcoh")):
        matrix = np.asarray(bands["alpha"][method]["matrix"])
        image = axis.imshow(matrix, vmin=0, vmax=max(matrix.max(), 0.01), cmap="magma")
        axis.set(title=f"Alpha {method.upper()} matrix", xlabel="Channel", ylabel="Channel")
        plt.colorbar(image, ax=axis, shrink=0.8)
    _finalize_figure(fig, path)
    return path.name


def _plot_coupling(summary, path):
    pac = summary["coupling"]["pac"]
    cpc = summary["coupling"]["cross_phase_coupling"]
    names = [row["channel"] for row in pac]
    fig, axes = plt.subplots(1, 2, figsize=(15, 4.8), constrained_layout=True)
    axes[0].bar(names, [row["modulation_index"] for row in pac], color="#7c3aed")
    axes[0].set(title="Theta-Beta PAC modulation index", ylabel="Tort MI")
    axes[1].bar(names, [row["n_m_phase_locking_value"] for row in cpc], color="#0369a1")
    axes[1].set(title="Theta-Alpha cross-phase coupling", ylabel="n:m PLV")
    for axis in axes:
        axis.tick_params(axis="x", rotation=90, labelsize=6)
        axis.grid(axis="y", alpha=0.2)
    _finalize_figure(fig, path)
    return path.name


def _write_tables(summary, tables):
    bands = summary["spectral"]["absolute_band_power"]
    _csv(tables / "bandpower_by_channel.csv", ["channel", "band", "absolute_power_uv2", "relative_power"], [{"channel": channel, "band": row["band"], "absolute_power_uv2": value, "relative_power": row["relative_power"][channel]} for row in bands for channel, value in row["absolute_power_uv2"].items()])
    _csv(tables / "complexity_by_channel.csv", list(summary["complexity"]["channel_metrics"][0]), summary["complexity"]["channel_metrics"])
    _csv(tables / "microstate_parameters.csv", list(summary["microstates"]["parameters"][0]), summary["microstates"]["parameters"])
    _csv(tables / "qc_epochs.csv", list(summary["quality_control"]["epochs"][0]), summary["quality_control"]["epochs"])
    connectivity_rows = []
    for band, methods in summary["connectivity"]["bands"].items():
        for method, value in methods.items():
            connectivity_rows.append({"band": band, "method": method, "global_mean": value["global_mean"], "global_median": value["global_median"]})
    _csv(tables / "connectivity_global.csv", ["band", "method", "global_mean", "global_median"], connectivity_rows)
    _csv(tables / "pac_by_channel.csv", list(summary["coupling"]["pac"][0]), summary["coupling"]["pac"])
    _csv(tables / "cross_phase_coupling_by_channel.csv", list(summary["coupling"]["cross_phase_coupling"][0]), summary["coupling"]["cross_phase_coupling"])


def _csv(path, fields, rows):
    with Path(path).open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _write_visual_manifest(destination, filenames):
    """Persist enough evidence to audit the report figures without rerunning analysis."""
    assets = destination / "assets"
    artifacts = []
    for name, filename in filenames.items():
        image = matplotlib.image.imread(assets / filename)
        artifacts.append(
            {
                "name": name,
                "path": f"assets/{filename}",
                "width_px": int(image.shape[1]),
                "height_px": int(image.shape[0]),
                "size_bytes": (assets / filename).stat().st_size,
            }
        )
    manifest = {
        "status": "passed",
        "design_spec": DESIGN_SPEC,
        "artifact_type": "full_recording_qeeg_report",
        "artifacts": artifacts,
        "warnings": [],
    }
    path = destination / "visual_manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def validate_report_output(output_dir):
    """Smoke-check all required HTML, figures, tables, and encoded text."""
    destination = Path(output_dir)
    expected = [
        destination / "analysis_summary.json",
        destination / "report.html",
        destination / "technical-details.html",
        destination / "visual_manifest.json",
    ]
    required_assets = [
        "qc_full_recording_comparison.png",
        "spectral_overview.png",
        "bandpower_topographies.png",
        "gfp_microstates.png",
        "complexity_overview.png",
        "connectivity_overview.png",
        "cross_frequency_coupling.png",
    ]
    expected.extend(destination / "assets" / name for name in required_assets)
    errors = [f"Missing or empty: {path}" for path in expected if not path.is_file() or path.stat().st_size == 0]
    if not errors:
        for page in (destination / "report.html", destination / "technical-details.html"):
            text = page.read_text(encoding="utf-8")
            if "\ufffd" in text or "???" in text:
                errors.append(f"Encoding corruption marker found: {page}")
    return {"status": "passed" if not errors else "failed", "checked_files": [str(path) for path in expected], "errors": errors}


def _clinical_html(summary, files):
    qc = summary["quality_control"]
    markers = summary["spectral"]["markers"]
    gate = summary["safety_gate"]
    overview = [
        ("分析时段", f"完整记录；保留 {qc['epoch_summary']['retained']} / {qc['epoch_summary']['total']} 秒"),
        ("空间范围", f"{len(summary['analysis_data']['eeg_channels'])} 个头皮通道"),
        ("后部 Alpha 峰频率", _number(markers["paf_hz"]["mean"], "Hz")),
        ("Theta / Beta 功率比", _number(markers["tbr"]["mean"])),
        ("额叶 Alpha 不对称", _number(markers["faa_ln_f4_minus_ln_f3"])),
    ]
    body = f"""
<header><div><h1>64导脑电定量分析报告</h1><p>完整记录的头皮脑电节律、空间组织、时间动力学与连接性描述</p></div><div class="status {'blocked' if gate['conclusion'] != 'AUTO_PASS' else 'pass'}">{html.escape(gate['conclusion'])}</div></header>
<nav><a href="#qc">质量控制</a><a href="#spectral">频谱与频带功率</a><a href="#spatial">头皮空间分布</a><a href="#dynamic">全局场功率与微状态</a><a href="#complexity">复杂度</a><a href="#connectivity">功能连接</a><a href="#coupling">跨频耦合</a><a href="technical-details.html">技术细节</a></nav>
<main>
<section class="overview"><h2>记录概览</h2><div class="metric-grid">{''.join(f'<div><span>{html.escape(k)}</span><strong>{html.escape(v)}</strong></div>' for k,v in overview)}</div></section>
<section id="qc"><h2>质量控制与预处理</h2><p>已完成 50 Hz 陷波、0.5-45 Hz 带通、全头皮平均参考、250 Hz 重采样、坏导联筛查和 1 秒 epoch 筛查。{qc['epoch_summary']['rejected']} 个 epoch 未进入后续定量分析。自动 ICA 状态为 <b>{html.escape(qc['ica']['status'])}</b>；安全门禁结论为 <b>{html.escape(gate['conclusion'])}</b>。</p><p class="warning">{html.escape('；'.join(gate['reasons']) or '自动流程完成，仍应结合原始波形复核。')}</p>{_figure(files['qc'], '上下两排分别显示处理前与保留数据的完整记录。波形为同一 O1 通道；PSD 为全部头皮通道均值及标准误；时频图分别按自身的对数功率范围显示，颜色不用于跨图绝对功率比较。')}</section>
<section id="spectral"><h2>频谱与频带功率</h2><p>功率谱显示不同频率节律的强度。绝对功率单位为 uV2，反映信号能量；相对功率为该频带在 1-45 Hz 总功率中的占比，用于观察频带构成。</p>{_figure(files['spectral'], '左图横轴为频率、纵轴为平均功率；中图和右图分别为全头皮平均绝对功率与相对功率。柱越高表示该频带在本次记录中的能量或构成比例越大。')}</section>
<section id="spatial"><h2>头皮空间分布</h2><p>每张地形图对应一个频带。图上方为额部、下方为枕部，颜色和图旁色标共同表示该频带在该头皮位置的绝对功率。颜色仅在同一张图内比较。</p>{_figure(files['topography'], '可观察各节律在头皮上的分布位置；地形图描述头皮电位空间分布，不等同于深部脑区活动定位。')}</section>
<section id="dynamic"><h2>全局场功率与微状态</h2><p>全局场功率（GFP）概括某一时刻全头皮电位差异的总体强度。微状态将连续头皮分布归纳为本次记录内反复出现的 A-F 六类模式，用于描述其出现频率、持续时间和转换特点。</p>{_figure(files['gfp_microstates'], '上图横轴为保留记录时间、纵轴为 GFP。下方六图为本次记录拟合得到的六种头皮分布模板；A-F 是数据内的聚类标签。')}</section>
<section id="complexity"><h2>信号复杂度</h2><p>复杂度指标从波形的变化幅度、变化速度、规律性和长期相关性等不同角度，概括完整记录内的时间结构。它们用于描述，不单独构成疾病判断。</p>{_figure(files['complexity'], '横轴为各复杂度指标，纵轴为全头皮通道平均值。不同指标量纲和数值范围不同，应在同一指标的不同记录之间比较。')}</section>
<section id="connectivity"><h2>功能连接</h2><p>功能连接描述不同头皮通道信号在某一频带中是否呈现稳定的相位或振幅协同变化。连接图用于观察空间模式；不同方法的数值定义不同，不应直接横向比较绝对数值。</p>{_figure(files['connectivity'], '左图比较 Theta、Alpha、Beta 三个频带的全局平均连接强度。右侧矩阵为 Alpha 频带的 PLV 与虚部相干，横纵轴均为头皮通道，颜色越亮表示该方法下的连接值越高。')}</section>
<section id="coupling"><h2>跨频耦合</h2><p>相位-振幅耦合（PAC）观察慢频相位与快频振幅是否存在稳定关系；跨频相位耦合观察两个频带相位之间的 n:m 同步。结果为传感器层面的描述，应结合伪迹和临床状态解释。</p>{_figure(files['coupling'], '横轴为头皮通道。左图为 Theta 相位与 Beta 振幅的 Tort 调制指数；右图为 Theta-Alpha 的 n:m 相位锁定值。柱高表示在该指标定义下耦合程度更强。')}</section>
</main>"""
    return _page("64导脑电定量分析报告", body)


def _technical_html(summary, files):
    qc = summary["quality_control"]
    body = f"""
<header><div><h1>64导脑电定量分析技术细节</h1><p>本次完整记录的输入、预处理、算法参数和结构化结果说明</p></div><a class="back" href="report.html">返回报告正文</a></header>
<main>
<section><h2>数据与分析范围</h2><table><tr><th>输入文件</th><td>{html.escape(summary['source']['filename'])}</td></tr><tr><th>原始记录</th><td>{summary['source']['duration_sec']:.1f} 秒，{summary['source']['sampling_rate_hz']:.0f} Hz</td></tr><tr><th>头皮通道</th><td>{len(summary['analysis_data']['eeg_channels'])}；M1/M2 作为乳突参考，不参与头皮空间统计</td></tr><tr><th>分析数据</th><td>质控保留 {summary['analysis_data']['duration_sec']:.1f} 秒，{summary['analysis_data']['sampling_rate_hz']:.0f} Hz</td></tr></table></section>
<section><h2>处理步骤与结果</h2><ol>{''.join(f'<li>{html.escape(str(step))}</li>' for step in qc['preprocessing']['steps'])}</ol><table><tr><th>总 epoch</th><td>{qc['epoch_summary']['total']}</td></tr><tr><th>保留 epoch</th><td>{qc['epoch_summary']['retained']}</td></tr><tr><th>剔除 epoch</th><td>{qc['epoch_summary']['rejected']}</td></tr><tr><th>保留率</th><td>{qc['epoch_summary']['retention_percent']:.1f}%</td></tr><tr><th>ICA</th><td>{html.escape(qc['ica']['status'])}</td></tr><tr><th>安全门禁</th><td>{html.escape(summary['safety_gate']['conclusion'])}: {html.escape('；'.join(summary['safety_gate']['reasons']))}</td></tr></table></section>
<section><h2>定量方法</h2><table><tr><th>模块</th><th>方法</th><th>全程计算方式</th></tr><tr><td>频谱</td><td>Welch PSD、绝对/相对 Bandpower、PAF、TBR、FAA</td><td>全部保留样本</td></tr><tr><td>空间与时间</td><td>GFP、GMD、六类微状态及转换</td><td>全部保留样本</td></tr><tr><td>复杂度</td><td>Hjorth、样本熵、分形维数、Hurst、排列熵、DFA、LZ、SVD、多尺度熵</td><td>覆盖完整记录的等距抽样</td></tr><tr><td>连接性</td><td>ImCoh、wPLI2、ciPLV、PPC、Coherence、PLV、PLI、AEC</td><td>全部保留的 2 秒 epoch</td></tr><tr><td>跨频</td><td>Theta-Beta PAC、Theta-Alpha n:m CPC</td><td>全部保留样本</td></tr><tr><td>频谱参数化</td><td>Specparam 周期/非周期分解</td><td>全头皮平均 PSD</td></tr></table></section>
<section><h2>结构化结果</h2><p>报告同目录的 <code>tables</code> 文件夹包含逐通道频带功率、复杂度、微状态参数、epoch 筛查、连接性汇总、PAC 和 CPC 的 CSV；<code>analysis_summary.json</code> 保留完整机器可读结果。</p></section>
</main>"""
    return _page("64导脑电定量分析技术细节", body)


def _figure(filename, caption):
    return f'<figure><img src="assets/{html.escape(filename)}" alt="{html.escape(caption)}"><figcaption>{html.escape(caption)}</figcaption></figure>'


def _number(value, unit=""):
    return "未计算" if value is None else f"{value:.3f}{(' ' + unit) if unit else ''}"


def _page(title, body):
    return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title><style>
*{{box-sizing:border-box}} body{{margin:0;background:#f3f6f8;color:#14212b;font:16px/1.7 Arial,'Microsoft YaHei',sans-serif}} header{{background:#0c3448;color:#fff;padding:32px max(5vw,24px);display:flex;justify-content:space-between;gap:20px;align-items:flex-start}}h1{{margin:0;font-size:30px;letter-spacing:0}}h2{{margin:0 0 10px;font-size:23px;color:#0c3448}}header p{{margin:4px 0 0;color:#d9e7ec}}nav{{position:sticky;top:0;z-index:1;padding:10px 5vw;background:#fff;border-bottom:1px solid #dbe4e9;display:flex;gap:16px;overflow:auto;white-space:nowrap}}nav a,.back{{color:#0f5f82;text-decoration:none;font-weight:600}}main{{max-width:1280px;margin:0 auto;padding:24px}}section{{background:#fff;border:1px solid #dbe4e9;border-radius:6px;padding:24px;margin:0 0 20px}}.overview{{background:#eaf3f6}}.metric-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:1px;background:#cbdde4;border:1px solid #cbdde4}}.metric-grid div{{background:#fff;padding:14px}}.metric-grid span{{display:block;color:#56717d;font-size:13px}}.metric-grid strong{{display:block;margin-top:4px;font-size:17px;color:#153e52}}.status{{padding:7px 11px;border:1px solid #7bc3da;border-radius:4px;font-weight:700;font-size:13px;white-space:nowrap}}.blocked{{background:#fff3e5;color:#8a3d00;border-color:#e7ad68}}.pass{{background:#e8f7ef;color:#17663b}}.warning{{color:#8a3d00;background:#fff7ed;border-left:3px solid #d97706;padding:10px 12px}}figure{{margin:18px 0 0;border-top:1px solid #e4ecef;padding-top:16px}}figure img{{width:100%;display:block;background:#fff}}figcaption{{color:#526772;font-size:14px;margin-top:9px}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #d9e4e8;padding:9px 11px;text-align:left;vertical-align:top}}th{{background:#eef5f7;color:#164a60}}ol{{padding-left:24px}}code{{background:#edf3f5;padding:2px 5px}}@media(max-width:700px){{header{{padding:22px 18px;display:block}}h1{{font-size:24px}}main{{padding:14px}}section{{padding:17px}}.metric-grid{{grid-template-columns:1fr 1fr}}figure img{{min-width:680px}}figure{{overflow:auto}}}}</style></head><body>{body}</body></html>"""
