"""Full method atlas renderer for the recovered 64-channel QEEG report.

This module deliberately contains presentation derivatives only.  Every
quantitative value comes from the saved analysis contract, which means the
same functions can be reused by a future service UI without changing the
analysis modules.
"""

from __future__ import annotations

import csv
import html
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mne
import numpy as np

from .microstates import (
    write_microstate_information_csv,
    write_microstate_lagged_information_csv,
    write_microstate_source_segments_csv,
    write_microstate_state_self_information_csv,
    write_microstate_timeline_mapping_csv,
    write_microstate_transition_counts_csv,
)
from .gfp import write_gfp_peak_topography_gmd_csv
from .spectral import compute_alpha_spectral_dispersion, write_alpha_spectral_dispersion_csv


METHOD_LABELS = {
    "imcoh": "虚部相干 (ImCoh)", "wpli2_debiased": "去偏 wPLI²",
    "ciplv": "校正相位锁定值 (ciPLV)", "ppc": "成对相位一致性 (PPC)",
    "coherence": "相干 (Coherence)", "plv": "相位锁定值 (PLV)",
    "pli": "相位滞后指数 (PLI)", "aec": "振幅包络相关 (AEC)",
}


def render_full_historical_report(summary, raw_before, cleaned, destination, assets, tables, base):
    """Render the complete method set represented in the historical HTML.

    ``base`` is the small stable renderer module.  Keeping its basic figure
    functions avoids duplicating QC plotting while this module owns the
    method-specific atlas and HTML structure.
    """
    base._configure_scientific_style()
    _write_all_tables(summary, tables, cleaned)
    files = {
        "qc": base._plot_qc_comparison(raw_before, cleaned, summary, assets / "qc_full_recording_comparison.png"),
        "clinical_scalp_waveform": _plot_clinical_scalp_waveform(cleaned, assets / "clinical_scalp_waveform.png"),
        "spectral": base._plot_spectral(summary, assets / "spectral_overview.png"),
        "cleaned_psd_detail": _plot_cleaned_psd_detail(summary, assets / "cleaned_psd_detail.png"),
        "bandpower": _plot_bandpower_topomaps(summary, cleaned, assets / "bandpower_topomaps.png"),
        "bandpower_relative": _plot_bandpower_topomaps(summary, cleaned, assets / "bandpower_relative_topomaps.png", relative=True),
        "bandpower_bars": _plot_global_bandpower(summary, assets / "global_bandpower_bars.png"),
        "alpha": _plot_posterior_alpha(summary, cleaned, assets / "alpha_posterior_distribution.png"),
        "alpha_dispersion": _plot_alpha_dispersion(summary, cleaned, assets / "alpha_spectral_dispersion.png"),
        "alpha_dispersion_topomaps": _plot_alpha_dispersion_topomaps(summary, cleaned, assets / "alpha_spectral_dispersion_topomaps.png"),
        "alpha_hemisphere_views": _plot_alpha_hemisphere_views(summary, assets / "alpha_spectral_dispersion_hemisphere_views.png"),
        "beta_envelopes": _plot_beta_envelopes(summary, assets / "beta_hemisphere_envelopes.png"),
        "spectral_statistics": _plot_spectral_statistics(summary, assets / "spectral_statistics.png"),
        "band_peaks": _plot_band_peaks(summary, assets / "band_peak_parameters.png"),
        "narrowband_abs": _plot_narrowbands(summary, cleaned, assets / "narrowband_absolute_topomaps.png"),
        "narrowband_rel": _plot_narrowbands(summary, cleaned, assets / "narrowband_relative_topomaps.png", relative=True),
        "ratios": _plot_ratios(summary, cleaned, assets / "power_ratio_topomaps.png"),
        "regional_bandpower": _plot_regional_bandpower(summary, assets / "regional_bandpower.png"),
        "hemispheric_asymmetry": _plot_hemispheric_asymmetry(summary, assets / "hemispheric_asymmetry.png"),
        "gfp": _plot_gfp_gmd(summary, assets / "gfp_gmd_summary.png"),
        "micro_templates": _plot_microstate_templates(summary, cleaned, assets / "microstate_topomaps.png"),
        "micro_parameters": _plot_microstate_parameters(summary, assets / "microstate_parameters.png"),
        "micro_transition": _plot_microstate_transitions(summary, assets / "microstate_transition_matrix.png"),
        "micro_sequence": _plot_microstate_sequence(summary, assets / "microstate_sequence.png"),
        "micro_coverage": _plot_microstate_coverage(summary, assets / "microstate_per_second.png"),
        "micro_duration_distribution": _plot_microstate_duration_distribution(summary, assets / "microstate_duration_distribution.png"),
        "micro_outgoing": _plot_microstate_outgoing(summary, assets / "microstate_outgoing_transitions.png"),
        "micro_total_contribution": _plot_microstate_total_contribution(summary, assets / "microstate_total_contribution.png"),
        "micro_transition_polar": _plot_microstate_transition_polar(summary, assets / "microstate_transition_polar.png"),
        "micro_distribution_histograms": _plot_microstate_distribution_histograms(summary, assets / "microstate_distribution_histograms.png"),
        "micro_sequence_raster": _plot_microstate_sequence_raster(summary, assets / "microstate_sequence_raster.png"),
        "micro_information_dynamics": _plot_microstate_information_dynamics(summary, assets / "microstate_information_dynamics.png"),
        "complexity": base._plot_complexity(summary, assets / "complexity_overview.png"),
        "multiscale_entropy": _plot_multiscale_entropy(summary, assets / "multiscale_entropy.png"),
        "omega": _plot_omega(summary, assets / "spatial_complexity.png"),
        "connectivity": base._plot_connectivity(summary, assets / "connectivity_overview.png"),
        "connectivity_nodes": _plot_connectivity_nodes(summary, cleaned, assets / "connectivity_node_strength.png"),
        "connectivity_regional": _plot_connectivity_regional(summary, assets / "connectivity_regional.png"),
        "coupling": base._plot_coupling(summary, assets / "cross_frequency_coupling.png"),
        "pac_maps": _plot_coupling_topomaps(summary, cleaned, assets / "cross_frequency_topomaps.png"),
        "pac_curve": _plot_pac_curves(summary, assets / "pac_phase_amplitude_curves.png"),
        "coupling_regional": _plot_coupling_regional(summary, assets / "cross_frequency_regional_summary.png"),
        "aperiodic": _plot_aperiodic(summary, assets / "spectral_parameterization.png"),
    }
    files.update(_plot_channel_psd_atlas_with_parameters(summary, assets))
    files.update(_plot_connectivity_atlas(summary, assets))
    report = destination / "report.html"
    technical = destination / "technical-details.html"
    report.write_text(_clinical_html(summary, files), encoding="utf-8")
    technical.write_text(_technical_html(summary, files, destination=destination), encoding="utf-8")
    manifest = _write_manifest(destination, files, base.DESIGN_SPEC)
    validation = validate_full_report(destination, files)
    if validation["status"] != "passed":
        raise RuntimeError("Expanded report validation failed: " + "; ".join(validation["errors"]))
    return {"report_path": report, "technical_path": technical, "assets": files, "tables_dir": tables, "visual_manifest_path": manifest, "validation": validation}


def _save(fig, path):
    fig.savefig(path, dpi=160, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    return Path(path).name


def _scalp_info(raw):
    return raw.copy().pick("eeg").info


def _topomap(axis, values, raw, title, unit, cmap="viridis"):
    image, _ = mne.viz.plot_topomap(np.asarray(values, float), _scalp_info(raw), axes=axis, show=False, contours=5, cmap=cmap)
    axis.set_title(title, fontsize=10)
    colorbar = plt.colorbar(image, ax=axis, shrink=0.76, pad=0.03)
    colorbar.set_label(unit, fontsize=8)


def _plot_clinical_scalp_waveform(raw, path):
    """Display every scalp channel across the complete retained recording."""
    eeg = raw.copy().pick("eeg")
    data_uv = eeg.get_data() * 1e6
    max_points = 8000
    step = max(1, data_uv.shape[1] // max_points)
    data_uv = data_uv[:, ::step]
    times = eeg.times[::step]
    channel_groups = np.array_split(np.arange(len(eeg.ch_names)), 4)
    scale_uv = max(float(np.nanpercentile(np.abs(data_uv), 90)) * 2.5, 20.0)
    fig, axes = plt.subplots(4, 1, figsize=(18, 16), sharex=True, constrained_layout=True)
    for axis, indices in zip(axes, channel_groups):
        offsets = np.arange(len(indices))[::-1] * scale_uv
        for index, offset in zip(indices, offsets):
            axis.plot(times, data_uv[index] + offset, color="#145a78", linewidth=0.35)
        axis.set_yticks(offsets, [eeg.ch_names[index] for index in indices], fontsize=7)
        axis.set_ylabel("Channel")
        axis.grid(axis="x", alpha=.18)
    axes[0].set_title("Complete recording: all scalp-channel waveforms")
    axes[-1].set_xlabel("Time (s)")
    axes[-1].set_xlim(float(times[0]), float(times[-1]))
    return _save(fig, path)


def _plot_cleaned_psd_detail(summary, path):
    """Plot complete-recording mean PSD and channel SEM with a fixed frequency range."""
    spectral = summary["spectral"]
    frequencies = np.asarray(spectral["frequencies_hz"], dtype=float)
    psd = np.asarray(list(spectral["psd_uv2_per_hz"].values()), dtype=float)
    mask = (frequencies >= .5) & (frequencies <= 45.)
    mean = np.nanmean(psd[:, mask], axis=0)
    sem = np.nanstd(psd[:, mask], axis=0, ddof=1) / np.sqrt(max(1, psd.shape[0]))
    fig, axis = plt.subplots(figsize=(14, 5.5), constrained_layout=True)
    axis.plot(frequencies[mask], mean, color="#0f766e", linewidth=1.5, label="Mean across scalp channels")
    axis.fill_between(frequencies[mask], np.maximum(0, mean - sem), mean + sem, color="#0f766e", alpha=.22, label="SEM")
    axis.set(title="Cleaned complete-recording power spectral density", xlabel="Frequency (Hz)", ylabel="PSD (uV^2/Hz)", xlim=(.5, 45))
    axis.grid(alpha=.22)
    axis.legend(frameon=False)
    return _save(fig, path)


def _alpha_dispersion_rows(summary, channels=None):
    """Return the canonical 7--13 Hz dispersion rows saved by ``spectral``.

    Report rendering must not silently substitute the earlier 8--13 Hz and
    +/-1 Hz display approximation for the recovered historical algorithm.
    """
    rows = summary["spectral"]["alpha_spectral_dispersion"]["channels"]
    if channels is None:
        return rows
    requested = set(channels)
    return [row for row in rows if row["channel"] in requested]


def _plot_bandpower_topomaps(summary, raw, path, relative=False):
    rows = summary["spectral"]["absolute_band_power"]
    channels = raw.copy().pick("eeg").ch_names
    fig, axes = plt.subplots(1, len(rows), figsize=(18, 4.4), constrained_layout=True)
    for axis, row in zip(np.ravel(axes), rows):
        values = [row["relative_power" if relative else "absolute_power_uv2"][name] for name in channels]
        _topomap(axis, values, raw, f"{row['band'].title()} {row['low_hz']:.0f}-{row['high_hz']:.0f} Hz", "ratio" if relative else "uV²")
    fig.suptitle("全头皮频带" + ("相对功率" if relative else "绝对功率") + "分布（完整记录）", fontsize=15)
    return _save(fig, path)


def _plot_global_bandpower(summary, path):
    rows = summary["spectral"]["absolute_band_power"]
    labels = [row["band"].title() for row in rows]
    absolute = [np.mean(list(row["absolute_power_uv2"].values())) for row in rows]
    relative = [100 * np.mean(list(row["relative_power"].values())) for row in rows]
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8), constrained_layout=True)
    axes[0].bar(labels, absolute, color="#0f766e")
    axes[0].set(title="全头皮平均绝对频带功率", ylabel="功率 (uV²)")
    axes[1].bar(labels, relative, color="#1d4ed8")
    axes[1].set(title="全头皮平均相对频带功率", ylabel="占总功率 (%)")
    for axis in axes:
        axis.grid(axis="y", alpha=.22)
    return _save(fig, path)


def _plot_posterior_alpha(summary, raw, path):
    alpha = summary["spectral"]["posterior_alpha"]
    rows = alpha["channels"]
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.8), constrained_layout=True)
    names = [row["channel"] for row in rows]
    colors = ["#0f766e" if row["hemisphere"] == "left" else "#1d4ed8" for row in rows]
    axes[0].bar(names, [row["alpha_modal_frequency_hz"] for row in rows], color=colors)
    axes[0].set(title="后部 Alpha 峰频率", ylabel="频率 (Hz)")
    axes[1].bar(names, [row["alpha_integrated_power_uv2"] for row in rows], color=colors)
    axes[1].set(title="后部 Alpha 积分功率", ylabel="功率 (uV²)")
    by_channel = {row["channel"]: row for row in rows}
    values = [by_channel.get(name, {}).get("alpha_modal_frequency_hz", np.nan) for name in raw.copy().pick("eeg").ch_names]
    _topomap(axes[2], values, raw, "后部 Alpha 峰频率头皮分布", "Hz", "cividis")
    for axis in axes[:2]:
        axis.tick_params(axis="x", rotation=45)
        axis.grid(axis="y", alpha=.22)
    return _save(fig, path)


def _plot_alpha_dispersion(summary, raw, path):
    """Show how concentrated the posterior alpha spectrum is around its peak."""
    posterior = summary["spectral"]["posterior_alpha"]["channels"]
    rows = _alpha_dispersion_rows(summary, [item["channel"] for item in posterior])
    hemisphere = {item["channel"]: item["hemisphere"] for item in posterior}
    for row in rows:
        row["hemisphere"] = hemisphere[row["channel"]]
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), constrained_layout=True)
    colors = ["#0f766e" if row["hemisphere"] == "left" else "#1d4ed8" for row in rows]
    axes[0].bar([row["channel"] for row in rows], [row["cd_alpha1"] for row in rows], color=colors)
    axes[0].set(title="Alpha 主峰相对高度", ylabel="主峰占 Alpha 谱的比例")
    axes[1].bar([row["channel"] for row in rows], [row["cd_alpha2"] for row in rows], color=colors)
    axes[1].set(title="主峰附近能量集中度", ylabel="峰值 ±1 Hz 内功率比例")
    by_channel = {row["channel"]: row for row in rows}
    values = [by_channel.get(name, {}).get("cd_alpha2", np.nan) for name in raw.copy().pick("eeg").ch_names]
    _topomap(axes[2], values, raw, "后部 Alpha 集中度头皮分布", "ratio", "cividis")
    for axis in axes[:2]:
        axis.tick_params(axis="x", rotation=45); axis.grid(axis="y", alpha=.22)
    return _save(fig, path)


def _plot_alpha_dispersion_topomaps(summary, raw, path):
    """Restore the historical scalp view of alpha peak and concentration measures."""
    channels = raw.copy().pick("eeg").ch_names
    rows = _alpha_dispersion_rows(summary, channels)
    by_channel = {row["channel"]: row for row in rows}
    specifications = (
        ("modal_frequency_hz", "Alpha modal frequency", "Hz", "cividis"),
        ("cd_alpha1", "CD-alpha1: modal-bin power fraction", "ratio", "viridis"),
        ("cd_alpha2", "CD-alpha2: modal +/-0.5 Hz power fraction", "ratio", "viridis"),
    )
    fig, axes = plt.subplots(1, 3, figsize=(16, 5), constrained_layout=True)
    for axis, (key, title, unit, cmap) in zip(axes, specifications):
        _topomap(axis, [by_channel[name][key] for name in channels], raw, title, unit, cmap)
    return _save(fig, path)


def _plot_alpha_hemisphere_views(summary, path):
    """Restore the hemisphere-specific alpha spectra and channel-frequency heatmaps."""
    spectral = summary["spectral"]
    frequencies = np.asarray(spectral["frequencies_hz"], dtype=float)
    alpha_mask = (frequencies >= 8.) & (frequencies <= 13.)
    alpha_frequencies = frequencies[alpha_mask]
    posterior = spectral["posterior_alpha"]["channels"]
    grouped = {
        side: [row["channel"] for row in posterior if row["hemisphere"] == side]
        for side in ("left", "right")
    }
    fig, axes = plt.subplots(2, 2, figsize=(15, 10), constrained_layout=True)
    for column, side in enumerate(("left", "right")):
        names = grouped[side]
        psd = np.asarray([spectral["psd_uv2_per_hz"][name] for name in names], dtype=float)[:, alpha_mask]
        color = "#0f766e" if side == "left" else "#1d4ed8"
        axes[0, column].plot(alpha_frequencies, psd.T, color=color, alpha=.35, linewidth=.9)
        axes[0, column].plot(alpha_frequencies, np.mean(psd, axis=0), color="#17212b", linewidth=2, label="Channel mean")
        axes[0, column].set(title=f"{side.title()} posterior alpha spectra", xlabel="Frequency (Hz)", ylabel="PSD (uV^2/Hz)")
        axes[0, column].grid(alpha=.22)
        axes[0, column].legend(frameon=False)
        image = axes[1, column].imshow(psd, aspect="auto", origin="lower", cmap="magma", extent=(alpha_frequencies[0], alpha_frequencies[-1], -.5, len(names) - .5))
        axes[1, column].set(title=f"{side.title()} posterior channels", xlabel="Frequency (Hz)", ylabel="Channel", yticks=range(len(names)), yticklabels=names)
        fig.colorbar(image, ax=axes[1, column], shrink=.82, label="PSD (uV^2/Hz)")
    return _save(fig, path)


def _plot_beta_envelopes(summary, path):
    beta = summary["spectral"]["beta_envelopes"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), constrained_layout=True)
    for axis, (name, result) in zip(axes, beta.items()):
        values = [result["hemisphere_summary"][side]["mean_p95_uv"] for side in ("left", "right")]
        axis.bar(["左半球", "右半球"], values, color=["#0f766e", "#1d4ed8"])
        axis.set(title=f"{name.title()} {result['range_hz'][0]:.0f}-{result['range_hz'][1]:.0f} Hz 包络", ylabel="P95 幅度 (uV)")
        axis.grid(axis="y", alpha=.22)
    return _save(fig, path)


def _region(channel):
    label = channel.upper()
    if label.startswith(("FP", "AF", "F")):
        return "额区"
    if label.startswith(("FT", "T", "TP")):
        return "颞区"
    if label.startswith(("CP", "P")):
        return "顶区"
    if label.startswith(("FC", "C")):
        return "中央区"
    return "枕区"


def _hemisphere(channel):
    digits = "".join(character for character in channel if character.isdigit())
    return "左" if digits and int(digits) % 2 else "右" if digits else "中线"


def _plot_regional_bandpower(summary, path):
    rows = summary["spectral"]["absolute_band_power"]
    regions = ["额区", "中央区", "颞区", "顶区", "枕区"]
    fig, axes = plt.subplots(1, 2, figsize=(15, 5.2), constrained_layout=True)
    for axis, relative, title, unit in ((axes[0], False, "各脑区绝对频带功率", "功率 (uV2)"), (axes[1], True, "各脑区相对频带功率", "占总功率 (%)")):
        for band in rows:
            values = []
            for region in regions:
                selected = [value for channel, value in band["relative_power" if relative else "absolute_power_uv2"].items() if _region(channel) == region]
                values.append(np.mean(selected) * (100 if relative else 1))
            axis.plot(regions, values, marker="o", label=band["band"].title())
        axis.set(title=title, ylabel=unit); axis.grid(alpha=.22); axis.legend(ncol=2, fontsize=8)
    return _save(fig, path)


def _plot_hemispheric_asymmetry(summary, path):
    rows = summary["spectral"]["absolute_band_power"]
    labels, values = [], []
    for row in rows:
        powers = row["absolute_power_uv2"]
        left = [value for channel, value in powers.items() if _hemisphere(channel) == "左"]
        right = [value for channel, value in powers.items() if _hemisphere(channel) == "右"]
        labels.append(row["band"].title())
        values.append(100 * (np.mean(right) - np.mean(left)) / max((np.mean(right) + np.mean(left)) / 2, np.finfo(float).eps))
    fig, axis = plt.subplots(figsize=(9, 4.5), constrained_layout=True)
    axis.bar(labels, values, color=["#1d4ed8" if value >= 0 else "#0f766e" for value in values])
    axis.axhline(0, color="#17212b", linewidth=.9)
    axis.set(title="左右半球绝对频带功率差异", ylabel="(右 - 左) / 双侧均值 (%)")
    axis.grid(axis="y", alpha=.22)
    return _save(fig, path)


def _plot_spectral_statistics(summary, path):
    rows = summary["spectral"]["channel_spectral_statistics"]
    statistics = [("spectral_entropy", "频谱熵", "ratio"), ("spectral_centroid_hz", "频谱质心", "Hz"), ("spectral_bandwidth_hz", "频谱带宽", "Hz"), ("spectral_edge_50_hz", "SEF50", "Hz"), ("spectral_edge_90_hz", "SEF90", "Hz"), ("spectral_edge_95_hz", "SEF95", "Hz"), ("alpha_centroid_hz", "Alpha 重心", "Hz")]
    fig, axes = plt.subplots(2, 4, figsize=(16, 8), constrained_layout=True)
    for axis, (key, label, unit) in zip(axes.flat, statistics):
        values = [item[key] for item in rows.values()]
        axis.boxplot(values, patch_artist=True, boxprops={"facecolor": "#dbeafe"})
        axis.scatter(np.ones(len(values)), values, s=10, alpha=.55, color="#1d4ed8")
        axis.set(title=label, ylabel=unit, xticks=[])
        axis.grid(axis="y", alpha=.2)
    axes.flat[-1].axis("off")
    return _save(fig, path)


def _plot_band_peaks(summary, path):
    rows = summary["spectral"]["band_peak_parameters"]["global"]
    labels = [item["band"] for item in rows]
    freqs = [item["peak_frequency_hz"] or 0 for item in rows]
    widths = [item["peak_bandwidth_hz"] or 0 for item in rows]
    prominence = [item["peak_prominence_log10"] or 0 for item in rows]
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), constrained_layout=True)
    for axis, values, title, ylabel, color in zip(axes, (freqs, widths, prominence), ("各频带峰频率", "各频带峰宽", "各频带峰突出度"), ("Hz", "Hz", "log10 PSD"), ("#0f766e", "#1d4ed8", "#b45309")):
        axis.bar(labels, values, color=color)
        axis.set(title=title, ylabel=ylabel)
        axis.tick_params(axis="x", rotation=35)
        axis.grid(axis="y", alpha=.2)
    return _save(fig, path)


def _plot_narrowbands(summary, raw, path, relative=False):
    rows = summary["spectral"]["narrowband_power"]["bands"]
    channels = raw.copy().pick("eeg").ch_names
    fig, axes = plt.subplots(4, 4, figsize=(17, 15), constrained_layout=True)
    for axis, row in zip(axes.flat, rows):
        values = [row["relative_power" if relative else "absolute_power_uv2"][name] for name in channels]
        _topomap(axis, values, raw, row["band"], "ratio" if relative else "uV²")
    fig.suptitle("2-34 Hz 连续窄频带" + ("相对功率" if relative else "绝对功率") + "头皮图", fontsize=15)
    return _save(fig, path)


def _plot_ratios(summary, raw, path):
    rows = summary["spectral"]["power_ratios"]
    channels = raw.copy().pick("eeg").ch_names
    fig, axes = plt.subplots(3, 4, figsize=(17, 12), constrained_layout=True)
    for axis, row in zip(axes.flat, rows):
        _topomap(axis, [row["value"][name] for name in channels], raw, row["ratio"], "ratio", "magma")
    fig.suptitle("12 种频带功率比头皮分布", fontsize=15)
    return _save(fig, path)


def _gfp_fields(summary):
    return summary["gfp_gmd"]


def _plot_gfp_gmd(summary, path):
    result = _gfp_fields(summary)
    full = result.get("gfp_display_series")
    gmd = result.get("successive_peak_gmd_series")
    fig, axes = plt.subplots(2, 1, figsize=(16, 7.5), constrained_layout=True)
    if full:
        axes[0].plot(full["time_sec"], full["values_uv"], color="#7c3aed", linewidth=.45)
        axes[0].set(title="全程全局场功率 (GFP)", xlabel="时间 (s)", ylabel="GFP (uV)")
    else:
        axes[0].plot(result["gfp_peak_times_sec"], result["gfp_peak_uv"], ".", ms=1.5, color="#7c3aed")
        axes[0].set(title="GFP 峰值", xlabel="时间 (s)", ylabel="GFP (uV)")
    if gmd:
        axes[1].plot(gmd["to_time_sec"], gmd["values"], color="#b45309", linewidth=.45)
    else:
        axes[1].plot(np.arange(len(result["successive_peak_gmd"])), result["successive_peak_gmd"], color="#b45309", linewidth=.45)
    axes[1].set(title="相邻 GFP 峰全局地形差异 (GMD)", xlabel="时间 / 峰序列", ylabel="GMD (0-1)")
    for axis in axes:
        axis.grid(alpha=.2)
    return _save(fig, path)


def _plot_microstate_templates(summary, raw, path):
    result = summary["microstates"]
    fig, axes = plt.subplots(2, 3, figsize=(13, 8), constrained_layout=True)
    for axis, (name, values) in zip(axes.flat, result["templates_uv_normalized"].items()):
        _topomap(axis, values, raw, f"微状态 {name}", "normalized uV", "RdBu_r")
    return _save(fig, path)


def _plot_microstate_parameters(summary, path):
    rows = summary["microstates"]["parameters"]
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
    names = [row["state"] for row in rows]
    keys = [("mean_duration_ms", "平均持续时间", "ms"), ("occurrences_per_sec", "出现率", "次/s"), ("time_coverage_percent", "时间覆盖", "%"), ("gev_percent", "全局解释方差", "%")]
    for axis, (key, title, unit) in zip(axes.flat, keys):
        axis.bar(names, [row[key] for row in rows], color="#0f766e")
        axis.set(title=title, ylabel=unit)
        axis.grid(axis="y", alpha=.2)
    return _save(fig, path)


def _plot_microstate_transitions(summary, path):
    result = summary["microstates"]
    transition = result["transition_matrix"]
    matrix = np.asarray(transition["row_normalized_percent"], float)
    names = transition["states"]
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5), constrained_layout=True)
    image = axes[0].imshow(matrix, cmap="magma", vmin=0, vmax=max(.01, matrix.max()))
    axes[0].set(title="微状态转换概率", xlabel="下一个状态", ylabel="当前状态", xticks=range(len(names)), xticklabels=names, yticks=range(len(names)), yticklabels=names)
    plt.colorbar(image, ax=axes[0], label="出向转换比例 (%)")
    outgoing = result.get("outgoing_transitions", [])
    axes[1].bar([row["from_state"] for row in outgoing], [row["outgoing_transition_count"] for row in outgoing], color="#b45309")
    axes[1].set(title="各状态出向转换次数", xlabel="状态", ylabel="次数")
    axes[1].grid(axis="y", alpha=.2)
    return _save(fig, path)


def _plot_microstate_sequence(summary, path):
    result = summary["microstates"]
    names = result["state_names"]
    labels = np.asarray([names.index(item) for item in result["sample_labels"]], dtype=int)
    length = labels.size
    if length > 8000:
        labels = labels[:: max(1, length // 8000)]
    fig, axis = plt.subplots(figsize=(16, 2.8), constrained_layout=True)
    image = axis.imshow([labels], aspect="auto", interpolation="nearest", cmap="tab10", vmin=0, vmax=max(5, max(labels)))
    axis.set(title="微状态全程连续序列（为显示而等间隔抽样）", xlabel="完整记录时间位置", yticks=[])
    colorbar = plt.colorbar(image, ax=axis, ticks=range(6))
    colorbar.set_label("A-F 标签")
    return _save(fig, path)


def _plot_microstate_coverage(summary, path):
    rows = summary["microstates"].get("per_second_coverage", [])
    fig, axis = plt.subplots(figsize=(16, 4.4), constrained_layout=True)
    if rows:
        states = summary["microstates"]["state_names"]
        values = np.asarray([[row["state_coverage_fraction"].get(state, 0) for row in rows] for state in states])
        axis.stackplot(np.arange(len(rows)), values, labels=states, alpha=.86)
        axis.legend(ncol=6, loc="upper right", frameon=False)
    axis.set(title="微状态逐秒时间覆盖", xlabel="时间 (s)", ylabel="覆盖比例")
    axis.set_ylim(0, 1)
    return _save(fig, path)


def _plot_microstate_duration_distribution(summary, path):
    segments = summary["microstates"].get("segments", [])
    names = summary["microstates"]["state_names"]
    fig, axis = plt.subplots(figsize=(10, 4.8), constrained_layout=True)
    duration_sets = [[segment["duration_ms"] for segment in segments if segment["state"] == name] for name in names]
    axis.boxplot(duration_sets, tick_labels=names, showfliers=False, patch_artist=True, boxprops={"facecolor": "#dbeafe", "edgecolor": "#1d4ed8"})
    axis.set(title="微状态持续时间分布", xlabel="微状态类别", ylabel="持续时间 (ms)")
    axis.grid(axis="y", alpha=.22)
    return _save(fig, path)


def _plot_microstate_outgoing(summary, path):
    rows = summary["microstates"].get("outgoing_transitions", [])
    fig, axis = plt.subplots(figsize=(9, 4.5), constrained_layout=True)
    axis.bar([row["from_state"] for row in rows], [row["outgoing_transition_count"] for row in rows], color=["#0f766e", "#1d4ed8", "#b45309", "#7c3aed", "#be123c", "#0369a1"][:len(rows)])
    axis.set(title="各微状态的出向转换次数", xlabel="起始微状态", ylabel="转换次数")
    axis.grid(axis="y", alpha=.22)
    return _save(fig, path)


def _plot_microstate_total_contribution(summary, path):
    """Show time contribution and GFP-peak explanatory variance side by side."""
    rows = summary["microstates"]["parameters"]
    names = [row["state"] for row in rows]
    coverage = [row["time_coverage_percent"] for row in rows]
    gev = [row["gev_percent"] for row in rows]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), constrained_layout=True)
    for axis, values, title in zip(axes, (coverage, gev), ("Microstate time contribution", "GFP-peak explained variance")):
        bars = axis.bar(names, values, color=[plt.get_cmap("tab10")(index) for index in range(len(names))])
        for bar, value in zip(bars, values):
            axis.text(bar.get_x() + bar.get_width() / 2, value, f"{value:.1f}%", ha="center", va="bottom", fontsize=8)
        axis.set(title=title, ylabel="Percent (%)")
        axis.grid(axis="y", alpha=.22)
    return _save(fig, path)


def _plot_microstate_transition_polar(summary, path):
    """Restore a directed polar view of the strongest non-self transitions."""
    transition = summary["microstates"]["transition_matrix"]
    states = transition["states"]
    matrix = np.asarray(transition["row_normalized_percent"], dtype=float)
    angles = np.linspace(0, 2 * np.pi, len(states), endpoint=False)
    coordinates = {state: (angle, 1.0) for state, angle in zip(states, angles)}
    edges = [(matrix[source, target], source, target) for source in range(len(states)) for target in range(len(states)) if source != target and matrix[source, target] > 0]
    strongest = sorted(edges, reverse=True)[:12]
    fig, axis = plt.subplots(figsize=(8, 8), subplot_kw={"projection": "polar"}, constrained_layout=True)
    axis.set_theta_offset(np.pi / 2)
    axis.set_theta_direction(-1)
    axis.set_ylim(0, 1.25)
    axis.set_yticks([])
    axis.set_xticks([])
    axis.grid(False)
    for state, angle in zip(states, angles):
        axis.scatter(angle, 1.0, s=650, color=plt.get_cmap("tab10")(states.index(state)), zorder=3)
        axis.text(angle, 1.0, state, ha="center", va="center", color="white", weight="bold")
    maximum = max(value for value, _, _ in strongest) if strongest else 1.0
    for value, source, target in strongest:
        source_angle, _ = coordinates[states[source]]
        target_angle, _ = coordinates[states[target]]
        midpoint = (source_angle + target_angle) / 2
        if abs(source_angle - target_angle) > np.pi:
            midpoint += np.pi
        radius = .45 + .35 * (1 - value / maximum)
        axis.annotate(
            "", xy=(target_angle, .92), xytext=(source_angle, .92),
            arrowprops={"arrowstyle": "->", "color": "#b45309", "lw": .55 + 3 * value / maximum, "alpha": .72,
                       "connectionstyle": f"arc3,rad={.18 if np.sin(midpoint) >= 0 else -.18}"},
        )
    axis.set_title("Strongest directed microstate transitions (top 12)", pad=22)
    fig.text(.5, .03, "Arrow width is proportional to the row-normalized transition percentage.", ha="center", fontsize=9)
    return _save(fig, path)


def _plot_microstate_distribution_histograms(summary, path):
    """Show distributions of duration, per-second occurrence, and per-second coverage."""
    result = summary["microstates"]
    states = result["state_names"]
    colors = [plt.get_cmap("tab10")(index) for index in range(len(states))]
    segments = result.get("segments", [])
    duration_sets = [[segment["duration_ms"] for segment in segments if segment["state"] == state] for state in states]
    coverage_rows = result.get("per_second_coverage", [])
    coverage_sets = [[row["state_coverage_fraction"].get(state, 0) for row in coverage_rows] for state in states]
    duration_sec = max(float(summary["analysis_data"].get("duration_sec", 0)), 1.0)
    start_sets = []
    for state in states:
        starts = np.zeros(int(np.ceil(duration_sec)), dtype=float)
        for segment in segments:
            if segment["state"] == state:
                index = min(len(starts) - 1, int(segment["start_sec"]))
                starts[index] += 1
        start_sets.append(starts)
    fig, axes = plt.subplots(1, 3, figsize=(18, 5.2), constrained_layout=True)
    for values, color, state in zip(duration_sets, colors, states):
        axes[0].hist(values, bins=25, histtype="step", linewidth=1.2, color=color, alpha=.9, label=state)
    axes[0].set(title="Segment duration distribution", xlabel="Duration (ms)", ylabel="Segment count")
    for values, color, state in zip(start_sets, colors, states):
        axes[1].hist(values, bins=np.arange(-.5, max(2, int(max(values)) + 2)) - .5, histtype="step", linewidth=1.2, color=color, alpha=.9, label=state)
    axes[1].set(title="Occurrence count per second", xlabel="Segments starting in one second", ylabel="Second count")
    for values, color, state in zip(coverage_sets, colors, states):
        axes[2].hist(values, bins=np.linspace(0, 1, 26), histtype="step", linewidth=1.2, color=color, alpha=.9, label=state)
    axes[2].set(title="Time coverage per second", xlabel="Coverage fraction", ylabel="Second count")
    for axis in axes:
        axis.grid(alpha=.18)
    axes[0].legend(ncol=3, fontsize=8, frameon=False)
    return _save(fig, path)


def _plot_microstate_sequence_raster(summary, path):
    """Render labels on their verified source-time axis, leaving rejected gaps blank."""
    result = summary["microstates"]
    states = result["state_names"]
    lookup = {state: index for index, state in enumerate(states)}
    mapping = result.get("timeline_mapping", {})
    source_duration = float(mapping.get("source_duration_sec") or summary["analysis_data"].get("duration_sec", 0))
    if source_duration <= 0:
        raise ValueError("microstate source duration must be positive")
    columns = min(2400, max(400, int(np.ceil(source_duration * 4))))
    raster = np.full(columns, -1, dtype=int)
    source_segments = result.get("source_timeline_segments", [])
    if source_segments:
        for segment in source_segments:
            start, end = segment.get("source_start_sec"), segment.get("source_end_sec")
            state = lookup.get(segment.get("state"), -1)
            if start is None or end is None or state < 0:
                continue
            left = max(0, min(columns, int(np.floor(float(start) / source_duration * columns))))
            right = max(left + 1, min(columns, int(np.ceil(float(end) / source_duration * columns))))
            raster[left:right] = state
    else:
        labels = np.asarray([lookup.get(label, -1) for label in result["sample_labels"]], dtype=int)
        samples_per_column = int(np.ceil(labels.size / columns))
        for column in range(columns):
            values = labels[column * samples_per_column:(column + 1) * samples_per_column]
            values = values[values >= 0]
            if values.size:
                raster[column] = int(np.bincount(values, minlength=len(states)).argmax())
    cmap = plt.get_cmap("tab10", len(states))
    cmap.set_bad("#f0f3f4")
    masked = np.ma.masked_less(raster, 0)
    fig, axis = plt.subplots(figsize=(18, 2.8), constrained_layout=True)
    image = axis.imshow(masked[np.newaxis, :], interpolation="nearest", aspect="auto", cmap=cmap, vmin=0, vmax=max(1, len(states) - 1), extent=(0, source_duration, 0, 1))
    axis.set(title="Complete-recording microstate sequence on source time", xlabel="Original recording time (s)", ylabel="State sequence")
    axis.set_yticks([])
    colorbar = fig.colorbar(image, ax=axis, ticks=range(len(states)), shrink=.84, pad=.015)
    colorbar.ax.set_yticklabels(states)
    colorbar.set_label("Microstate label")
    return _save(fig, path)


def _plot_microstate_information_dynamics(summary, path):
    """Plot full-recording windowed microstate information measures."""
    information = summary["microstates"]["information_dynamics"]
    rows = information["rows"]
    if not rows:
        raise ValueError("microstate information dynamics contains no windows")

    center_time = np.asarray(
        [(row["start_sec"] + row["end_sec"]) / 2 for row in rows], dtype=float
    )
    self_information = np.asarray(
        [row["mean_self_information_bits"] for row in rows], dtype=float
    )
    state_entropy = np.asarray(
        [row["state_entropy_bits"] for row in rows], dtype=float
    )
    lagged_mi = np.asarray(
        [np.nan if row["lagged_mutual_information_bits"] is None else row["lagged_mutual_information_bits"] for row in rows],
        dtype=float,
    )
    normalized_mi = np.asarray(
        [np.nan if row["lagged_normalized_mutual_information"] is None else row["lagged_normalized_mutual_information"] for row in rows],
        dtype=float,
    )

    fig, axes = plt.subplots(3, 1, figsize=(16, 9), sharex=True, constrained_layout=True)
    window_seconds = information["window_seconds"]
    lag_ms = information["mutual_information_lag_ms"]
    axes[0].plot(center_time, self_information, color="#0f766e", linewidth=1.0)
    axes[0].set(
        title="Microstate self-information across the complete recording",
        ylabel="Mean self-information (bits)",
    )
    axes[1].plot(center_time, state_entropy, color="#1d4ed8", linewidth=1.0)
    axes[1].set(ylabel="State entropy (bits)")
    axes[2].plot(center_time, lagged_mi, color="#b45309", linewidth=1.0, label="Lagged mutual information")
    axes[2].plot(center_time, normalized_mi, color="#7c3aed", linewidth=1.0, label="Normalized mutual information")
    axes[2].set(
        xlabel="Time in retained complete recording (s)",
        ylabel="Information (bits / normalized)",
    )
    axes[2].legend(frameon=False, ncol=2)
    for axis in axes:
        axis.grid(alpha=.22)
        axis.set_xlim(float(center_time[0] - window_seconds / 2), float(center_time[-1] + window_seconds / 2))
    fig.suptitle(
        f"Consecutive {window_seconds:g}-s microstate windows; within-window lag = {lag_ms:g} ms",
        fontsize=13,
    )
    return _save(fig, path)


def _plot_multiscale_entropy(summary, path):
    curve = summary["complexity"].get("multiscale_entropy", {})
    fig, axis = plt.subplots(figsize=(10, 4.5), constrained_layout=True)
    axis.plot(curve.get("scales", []), curve.get("mean_sample_entropy", []), marker="o", color="#0f766e")
    axis.set(title="多尺度样本熵曲线", xlabel="粗粒化尺度", ylabel="平均样本熵")
    axis.grid(alpha=.22)
    return _save(fig, path)


def _plot_omega(summary, path):
    values = summary["spatial_complexity"]
    labels = ["有效维数", "标准化 Omega", "相关矩阵熵"]
    numbers = [values["omega_effective_dimension"], values["omega_normalized"], values["eigenvalue_entropy_nats"]]
    fig, axis = plt.subplots(figsize=(8, 4.6), constrained_layout=True)
    bars = axis.bar(labels, numbers, color=["#0f766e", "#1d4ed8", "#b45309"])
    for bar, value in zip(bars, numbers):
        axis.text(bar.get_x() + bar.get_width()/2, bar.get_height(), f"{value:.3f}", ha="center", va="bottom")
    axis.set(title="空间复杂度（Omega）", ylabel="指标值")
    axis.grid(axis="y", alpha=.2)
    return _save(fig, path)


def _plot_channel_psd_atlas(summary, assets):
    psd = summary["spectral"]["psd_uv2_per_hz"]
    freqs = np.asarray(summary["spectral"]["frequencies_hz"])
    names = list(psd)
    result = {}
    for page, start in enumerate(range(0, len(names), 8), 1):
        selected = names[start:start + 8]
        fig, axes = plt.subplots(2, 4, figsize=(17, 8), constrained_layout=True)
        for axis, name in zip(axes.flat, selected):
            axis.plot(freqs, psd[name], color="#0f766e", linewidth=1)
            axis.set(title=name, xlabel="频率 (Hz)", ylabel="PSD (uV²/Hz)", xlim=(.5, 45))
            axis.grid(alpha=.2)
        for axis in axes.flat[len(selected):]:
            axis.axis("off")
        filename = f"channel_psd_atlas_{page:02d}.png"
        result[f"psd_atlas_{page:02d}"] = _save(fig, assets / filename)
    return result


def _plot_channel_psd_atlas_with_parameters(summary, assets):
    """Build the eight-channel PSD atlas with its source values directly below it."""
    psd = summary["spectral"]["psd_uv2_per_hz"]
    frequencies = np.asarray(summary["spectral"]["frequencies_hz"], dtype=float)
    names = list(psd)
    band_rows = summary["spectral"]["absolute_band_power"]
    alpha_rows = {row["channel"]: row for row in _alpha_dispersion_rows(summary)}
    result = {}
    for page, start in enumerate(range(0, len(names), 8), 1):
        selected = names[start:start + 8]
        fig = plt.figure(figsize=(18, 10.8), constrained_layout=True)
        grid = fig.add_gridspec(3, 4, height_ratios=(1, 1, .76))
        axes = [fig.add_subplot(grid[row, column]) for row in range(2) for column in range(4)]
        for axis, name in zip(axes, selected):
            axis.plot(frequencies, psd[name], color="#0f766e", linewidth=1)
            axis.set(title=name, xlabel="Frequency (Hz)", ylabel="PSD (uV^2/Hz)", xlim=(.5, 45))
            axis.grid(alpha=.2)
        for axis in axes[len(selected):]:
            axis.axis("off")
        table_axis = fig.add_subplot(grid[2, :])
        table_axis.axis("off")
        rows = []
        for name in selected:
            powers = [band["absolute_power_uv2"][name] for band in band_rows]
            modal_frequency = alpha_rows[name]["modal_frequency_hz"]
            rows.append([name, *[f"{value:.2f}" for value in powers], "" if modal_frequency is None else f"{modal_frequency:.2f}"])
        table = table_axis.table(
            cellText=rows,
            colLabels=["Channel", *[f"{band['band'].title()} power\n(uV^2)" for band in band_rows], "Alpha peak\n(Hz)"],
            cellLoc="center",
            loc="center",
        )
        table.auto_set_font_size(False)
        table.set_fontsize(7)
        table.scale(1, 1.25)
        table_axis.set_title("Band-power and alpha-peak parameters for channels shown above", fontsize=10, pad=8)
        result[f"psd_atlas_{page:02d}"] = _save(fig, assets / f"channel_psd_atlas_{page:02d}.png")
    return result


def _plot_connectivity_atlas(summary, assets):
    bands = summary["connectivity"]["bands"]
    result = {}
    methods = list(next(iter(bands.values())).keys())
    for method in methods:
        fig, axes = plt.subplots(1, 3, figsize=(15, 4.6), constrained_layout=True)
        vmax = max(np.asarray(bands[band][method]["matrix"]).max() for band in bands)
        for axis, band in zip(axes, bands):
            matrix = np.asarray(bands[band][method]["matrix"])
            image = axis.imshow(matrix, cmap="magma", vmin=0, vmax=max(vmax, .01))
            axis.set(title=f"{band.title()} {METHOD_LABELS.get(method, method)}", xlabel="通道", ylabel="通道")
        fig.colorbar(image, ax=axes, shrink=.8, label="连接值")
        key = f"connectivity_{method}"
        result[key] = _save(fig, assets / f"{key}.png")
    return result


def _plot_connectivity_nodes(summary, raw, path):
    methods = (("imcoh", "虚部相干"), ("plv", "相位锁定值"))
    bands = ("theta", "alpha", "beta")
    fig, axes = plt.subplots(2, 3, figsize=(14, 8), constrained_layout=True)
    for index, axis in enumerate(axes.flat):
        method, label = methods[index // 3]
        band = bands[index % 3]
        values = summary["connectivity"]["bands"][band][method]["node_strength"]
        _topomap(axis, [values[name] for name in raw.copy().pick("eeg").ch_names], raw, f"{label} {band.title()} 节点强度", "平均连接", "magma")
    return _save(fig, path)


def _plot_connectivity_regional(summary, path):
    bands = summary["connectivity"]["bands"]
    keys = list(bands["alpha"]["plv"]["regional_mean"])
    matrix = np.asarray([[bands[band]["plv"]["regional_mean"].get(key, np.nan) for key in keys] for band in ("theta", "alpha", "beta")])
    fig, axis = plt.subplots(figsize=(14, 4.5), constrained_layout=True)
    image = axis.imshow(matrix, aspect="auto", cmap="magma")
    axis.set(title="区域间相位锁定值（PLV）", yticks=range(3), yticklabels=["Theta", "Alpha", "Beta"], xticks=range(len(keys)), xticklabels=keys)
    axis.tick_params(axis="x", rotation=45)
    plt.colorbar(image, ax=axis, label="区域间平均 PLV")
    return _save(fig, path)


def _plot_coupling_topomaps(summary, raw, path):
    pac = {row["channel"]: row for row in summary["coupling"]["pac"]}
    cpc = {row["channel"]: row for row in summary["coupling"]["cross_phase_coupling"]}
    channels = raw.copy().pick("eeg").ch_names
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.8), constrained_layout=True)
    _topomap(axes[0], [pac[name]["modulation_index"] for name in channels], raw, "Theta 相位 - Beta 振幅耦合 (PAC)", "Tort MI", "magma")
    _topomap(axes[1], [cpc[name]["n_m_phase_locking_value"] for name in channels], raw, "Theta - Alpha 跨频相位耦合 (CPC)", "n:m PLV", "viridis")
    return _save(fig, path)


def _plot_pac_curves(summary, path):
    rows = sorted(summary["coupling"]["pac"], key=lambda item: item["modulation_index"], reverse=True)[:6]
    fig, axes = plt.subplots(2, 3, figsize=(15, 7), constrained_layout=True)
    for axis, row in zip(axes.flat, rows):
        curve = row.get("phase_amplitude_binned_curve")
        if curve:
            axis.plot(curve["phase_bin_centers_degrees"], curve["normalized_amplitude_distribution"], color="#7c3aed")
        axis.set(title=f"{row['channel']}：Theta-Beta PAC", xlabel="Theta 相位 (度)", ylabel="归一化 Beta 振幅")
        axis.grid(alpha=.2)
    return _save(fig, path)


def _plot_coupling_regional(summary, path):
    pac = summary["coupling"]["pac"]
    cpc = summary["coupling"]["cross_phase_coupling"]
    regions = ["额区", "中央区", "颞区", "顶区", "枕区"]
    pac_values = [np.mean([row["modulation_index"] for row in pac if _region(row["channel"]) == region]) for region in regions]
    cpc_values = [np.mean([row["n_m_phase_locking_value"] for row in cpc if _region(row["channel"]) == region]) for region in regions]
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5), constrained_layout=True)
    axes[0].bar(regions, pac_values, color="#0f766e"); axes[0].set(title="各脑区 Theta-Beta PAC", ylabel="调制指数")
    axes[1].bar(regions, cpc_values, color="#1d4ed8"); axes[1].set(title="各脑区 Theta-Alpha CPC", ylabel="n:m 相位锁定值")
    for axis in axes:
        axis.grid(axis="y", alpha=.22)
    return _save(fig, path)


def _plot_aperiodic(summary, path):
    result = summary.get("aperiodic_spectrum")
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), constrained_layout=True)
    if result:
        labels = ["非周期偏移", "非周期斜率", "拟合 R²", "拟合 MAE"]
        values = [result["aperiodic_offset_log10_uv2_per_hz"], result["aperiodic_exponent"], result["fit_r_squared"], result["fit_mae_log10_power"]]
        axes[0].bar(labels, values, color=["#0f766e", "#1d4ed8", "#b45309", "#7c3aed"])
        axes[0].tick_params(axis="x", rotation=25)
        axes[0].set(title="周期/非周期频谱分解参数", ylabel="参数值")
        peaks = result.get("peaks", [])
        axes[1].scatter([row["center_frequency_hz"] for row in peaks], [row["power_above_aperiodic"] for row in peaks], s=[max(20, row["bandwidth_hz"] * 20) for row in peaks], color="#b45309")
        axes[1].set(title="周期性谱峰", xlabel="中心频率 (Hz)", ylabel="超越非周期背景的功率")
    else:
        axes[0].text(.5, .5, "本次运行未启用 Specparam", ha="center", va="center")
        axes[0].axis("off"); axes[1].axis("off")
    return _save(fig, path)


def _write_csv(path, rows):
    if not rows:
        return
    with Path(path).open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def _write_all_tables(summary, tables, cleaned):
    spectral = summary["spectral"]
    _write_csv(tables / "qc_epochs.csv", summary["quality_control"].get("epochs", []))
    band_rows = []
    for row in spectral["absolute_band_power"]:
        for channel, absolute in row["absolute_power_uv2"].items():
            band_rows.append({"channel": channel, "band": row["band"], "low_hz": row["low_hz"], "high_hz": row["high_hz"], "absolute_power_uv2": absolute, "relative_power": row["relative_power"][channel]})
    _write_csv(tables / "bandpower_by_channel.csv", band_rows)
    _write_csv(tables / "narrowband_power.csv", [{"channel": channel, "band": row["band"], "absolute_power_uv2": value, "relative_power": row["relative_power"][channel]} for row in spectral["narrowband_power"]["bands"] for channel, value in row["absolute_power_uv2"].items()])
    _write_csv(tables / "power_ratios.csv", [{"channel": channel, "ratio": row["ratio"], "value": value} for row in spectral["power_ratios"] for channel, value in row["value"].items()])
    _write_csv(tables / "posterior_alpha.csv", spectral["posterior_alpha"]["channels"])
    alpha_result = compute_alpha_spectral_dispersion(
        cleaned,
        full_recording_psd_uv2=np.asarray(list(spectral["psd_uv2_per_hz"].values()), dtype=float),
        full_recording_freqs_hz=np.asarray(spectral["frequencies_hz"], dtype=float),
        include_windowed_spectra=True,
    )
    write_alpha_spectral_dispersion_csv(alpha_result, tables)
    _write_csv(tables / "spectral_statistics.csv", [{"channel": channel, **values} for channel, values in spectral["channel_spectral_statistics"].items()])
    _write_csv(tables / "band_peak_parameters.csv", spectral["band_peak_parameters"]["global"])
    _write_csv(tables / "beta_envelope_by_channel.csv", [{"band": band, **row} for band, result in spectral["beta_envelopes"].items() for row in result["channels"]])
    regional_bandpower = []
    hemispheric = []
    for band in spectral["absolute_band_power"]:
        for region in ("额区", "中央区", "颞区", "顶区", "枕区"):
            selected = [channel for channel in band["absolute_power_uv2"] if _region(channel) == region]
            regional_bandpower.append({"band": band["band"], "region": region, "absolute_power_uv2": float(np.mean([band["absolute_power_uv2"][channel] for channel in selected])), "relative_power": float(np.mean([band["relative_power"][channel] for channel in selected]))})
        for hemisphere in ("左", "右", "中线"):
            selected = [channel for channel in band["absolute_power_uv2"] if _hemisphere(channel) == hemisphere]
            if selected:
                hemispheric.append({"band": band["band"], "hemisphere": hemisphere, "absolute_power_uv2": float(np.mean([band["absolute_power_uv2"][channel] for channel in selected])), "relative_power": float(np.mean([band["relative_power"][channel] for channel in selected]))})
    _write_csv(tables / "regional_bandpower.csv", regional_bandpower)
    _write_csv(tables / "hemispheric_bandpower.csv", hemispheric)
    _write_csv(tables / "complexity_by_channel.csv", summary["complexity"]["channel_metrics"])
    mse = summary["complexity"].get("multiscale_entropy", {})
    _write_csv(tables / "multiscale_entropy.csv", [{"scale": scale, "mean_sample_entropy": value} for scale, value in zip(mse.get("scales", []), mse.get("mean_sample_entropy", []))])
    _write_csv(tables / "microstate_parameters.csv", summary["microstates"]["parameters"])
    _write_csv(tables / "microstate_segments.csv", summary["microstates"].get("segments", []))
    _write_csv(tables / "microstate_per_second.csv", summary["microstates"].get("per_second_coverage", []))
    _write_microstate_information_table(summary["microstates"], tables)
    _write_microstate_legacy_tables(summary["microstates"], tables)
    _write_csv(tables / "gfp_full_recording.csv", _series_rows(summary["gfp_gmd"].get("gfp_display_series"), "gfp_uv"))
    _write_csv(tables / "gmd_successive_peaks.csv", _series_rows(summary["gfp_gmd"].get("successive_peak_gmd_series"), "gmd"))
    write_gfp_peak_topography_gmd_csv(
        summary["gfp_gmd"], tables / "gfp_peak_topography_gmd.csv"
    )
    _write_csv(tables / "pac_by_channel.csv", summary["coupling"]["pac"])
    _write_csv(tables / "cpc_by_channel.csv", summary["coupling"]["cross_phase_coupling"])
    regions = ("额区", "中央区", "颞区", "顶区", "枕区")
    _write_csv(tables / "cross_frequency_regional.csv", [{"region": region, "theta_beta_pac_modulation_index": float(np.mean([row["modulation_index"] for row in summary["coupling"]["pac"] if _region(row["channel"]) == region])), "theta_alpha_cpc_n_m_plv": float(np.mean([row["n_m_phase_locking_value"] for row in summary["coupling"]["cross_phase_coupling"] if _region(row["channel"]) == region]))} for region in regions])
    connectivity = []
    node_rows = []
    edge_rows = []
    regional_rows = []
    for band, methods in summary["connectivity"]["bands"].items():
        for method, value in methods.items():
            connectivity.append({"band": band, "method": method, "global_mean": value["global_mean"], "global_median": value["global_median"]})
            node_rows.extend({"band": band, "method": method, "channel": channel, "node_strength": strength} for channel, strength in value["node_strength"].items())
            edge_rows.extend({"band": band, "method": method, **edge} for edge in value["edges"])
            regional_rows.extend({"band": band, "method": method, "region_pair": key, "mean_connectivity": mean} for key, mean in value["regional_mean"].items())
    _write_csv(tables / "connectivity_global.csv", connectivity)
    _write_csv(tables / "connectivity_node_strength.csv", node_rows)
    _write_csv(tables / "connectivity_edges.csv", edge_rows)
    _write_csv(tables / "connectivity_regional.csv", regional_rows)


def _write_microstate_information_table(microstates, tables):
    """Export the optional full-recording microstate information time series."""
    information = microstates.get("information_dynamics")
    if information is None:
        return None
    return write_microstate_information_csv(
        information,
        Path(tables) / "microstate_information_dynamics.csv",
    )


def _write_microstate_legacy_tables(microstates, tables):
    """Export full-record transition and lag tables from the saved contract."""
    if microstates.get("direct_transition_counts"):
        write_microstate_transition_counts_csv(
            microstates["direct_transition_counts"],
            Path(tables) / "microstate_transition_counts.csv",
        )
    if microstates.get("lagged_information"):
        write_microstate_lagged_information_csv(
            microstates["lagged_information"],
            Path(tables) / "microstate_auto_information.csv",
        )
        write_microstate_state_self_information_csv(
            microstates["lagged_information"],
            Path(tables) / "microstate_state_self_information.csv",
        )
    if microstates.get("timeline_mapping"):
        write_microstate_timeline_mapping_csv(
            microstates["timeline_mapping"],
            Path(tables) / "microstate_source_time_mapping.csv",
        )
    if microstates.get("source_timeline_segments"):
        write_microstate_source_segments_csv(
            microstates["source_timeline_segments"],
            Path(tables) / "microstate_source_time_segments.csv",
        )


def _series_rows(series, name):
    if not series:
        return []
    values = series.get("values", series.get("values_uv", []))
    return [{"time_sec": time, name: value} for time, value in zip(series.get("time_sec", []), values)]


def _figure(file, caption):
    return f'<figure><a href="assets/{html.escape(file)}" target="_blank"><img src="assets/{html.escape(file)}" alt="{html.escape(caption)}"></a><figcaption>{html.escape(caption)}</figcaption></figure>'


def _atlas(files, prefix, caption):
    matches = [files[key] for key in sorted(files) if key.startswith(prefix)]
    return '<details><summary>' + html.escape(caption) + '</summary>' + ''.join(_figure(item, caption) for item in matches) + '</details>'


def _clinical_html(summary, files):
    qc, spectral = summary["quality_control"], summary["spectral"]
    gate = summary["safety_gate"]
    markers = spectral["markers"]
    metric = [("记录范围", f"完整记录；保留 {qc['epoch_summary']['retained']} / {qc['epoch_summary']['total']} 秒"), ("头皮通道", f"{len(summary['analysis_data']['eeg_channels'])} 个"), ("后部 Alpha 峰频率", _value(markers['paf_hz']['mean'], 'Hz')), ("Theta/Beta 功率比", _value(markers['tbr']['mean'])), ("额叶 Alpha 不对称", _value(markers['faa_ln_f4_minus_ln_f3']))]
    body = f'''<header><div><h1>64导脑电定量分析报告</h1><p>完整记录的节律、空间组织、时间动态、复杂度、功能连接与跨频耦合</p></div><div class="status {'blocked' if gate['conclusion'] != 'AUTO_PASS' else 'pass'}">{html.escape(gate['conclusion'])}</div></header>
<nav><a href="#qc">预处理</a><a href="#rhythm">节律与频谱</a><a href="#spatial">空间分布</a><a href="#dynamic">GFP与微状态</a><a href="#complexity">复杂度</a><a href="#connectivity">功能连接</a><a href="#coupling">跨频耦合</a><a href="technical-details.html">技术细节</a></nav><main>
<section class="overview"><h2>分析概览</h2><div class="metric-grid">{''.join(f'<div><span>{html.escape(k)}</span><strong>{html.escape(v)}</strong></div>' for k,v in metric)}</div></section>
<section id="qc"><h2>预处理与质控结果</h2><p>全程记录依次接受 50 Hz 陷波、0.5–45 Hz 带通、坏导联筛查与插值、全头皮平均参考、250 Hz 重采样、逐秒筛查、ICA 伪迹识别及残余伪迹复检。{qc['epoch_summary']['rejected']} 秒未进入后续定量分析。自动 ICA 状态：<b>{html.escape(qc['ica']['status'])}</b>。</p><p class="warning">{html.escape('；'.join(gate['reasons']) or '自动处理完成，仍应结合原始波形进行专业复核。')}</p>{_figure(files['qc'], '同一完整记录的处理前后对照：波形、全通道平均功率谱和时频图。上下图分别按各自色标及纵轴读取。')}</section>
<section id="rhythm"><h2>节律与频谱</h2><p>功率谱展示每个频率成分在完整记录中的强度；绝对功率表示实际能量（uV²），相对功率表示它在总体频谱中所占比例。</p>{_figure(files['spectral'], '全头皮功率谱及五个常用频带的平均绝对功率和相对功率。')}{_figure(files['bandpower_bars'], '五个频带的全头皮平均绝对功率与相对功率柱状图。')}{_figure(files['alpha'], '后部 Alpha 指标。左图为各后部电极峰频率，中图为积分功率，右图为峰频率的头皮位置。')}{_figure(files['spectral_statistics'], '频谱熵、边缘频率、质心和带宽等指标的全头皮通道分布。箱体表示通道间分布，散点表示单个通道。')}{_figure(files['band_peaks'], '各频带主峰的频率、宽度及相对突出度；未检出稳定峰时以 0 表示。')}{_figure(files['aperiodic'], '周期/非周期频谱参数。非周期斜率描述频谱背景随频率升高的衰减；散点是拟合出的周期性峰。')}{_atlas(files, 'psd_atlas_', '展开查看全部头皮通道功率谱图册')}</section>
<section id="spatial"><h2>头皮空间分布</h2><p>头皮图的上方为额部、下方为枕部；颜色与各图自身色标共同表示该频带或指标在电极位置的数值。各图色标独立时，应读取色标而不是直接比较颜色深浅。</p>{_figure(files['bandpower'], '五个频带的绝对功率头皮图。')}{_figure(files['bandpower_relative'], '五个频带的相对功率头皮图。')}{_figure(files['narrowband_abs'], '2–34 Hz 的连续窄频带绝对功率头皮图。')}{_figure(files['narrowband_rel'], '2–34 Hz 的连续窄频带相对功率头皮图。')}{_figure(files['ratios'], '12 种频带功率比。颜色高表示标题中分子频带相对分母频带更强。')}</section>
<section id="dynamic"><h2>全局场功率与微状态</h2><p>GFP 概括每一时刻全头皮电位分布的总体强度；GMD 描述相邻稳定头皮分布之间的差异。微状态将连续头皮分布归纳为本次记录内反复出现的 A–F 六类模式，用于描述其持续、出现与转换。</p>{_figure(files['gfp'], '全程 GFP 与相邻 GFP 峰之间的 GMD。')}{_figure(files['micro_templates'], '本次记录的六个微状态头皮模板。')}{_figure(files['micro_parameters'], '六类微状态的平均持续时间、出现率、时间覆盖和 GEV。')}{_figure(files['micro_transition'], '微状态转换概率及各状态的出向转换次数。')}{_figure(files['micro_sequence'], '完整记录的连续微状态标签序列。')}{_figure(files['micro_coverage'], '逐秒的六类微状态时间覆盖。')}{_figure(files['micro_information_dynamics'], '全程连续 1 秒窗的微状态自信息、状态熵和 40 ms 滞后互信息。自信息越高表示该状态在本次记录中越少见；状态熵越高表示该时间窗内状态构成越均衡；滞后互信息描述短时状态序列的可预测性。')}</section>
<section id="complexity"><h2>信号复杂度</h2><p>复杂度指标从信号波动幅度、变化速度、规则性、分形结构和长期相关性等角度概括完整记录的时间组织。不同指标的量纲不同，应在同一指标的不同记录之间进行比较。</p>{_figure(files['complexity'], '13 项复杂度指标的 61 个头皮通道分布；每个小图使用自身纵轴。')}{_figure(files['omega'], '空间复杂度（Omega）概括多通道活动可区分的有效维数。')}</section>
<section id="connectivity"><h2>功能连接</h2><p>功能连接描述不同头皮通道在同一频带中相位或振幅的协同变化。不同连接指标的数学定义不同，因此应在同一指标内比较频带和空间分布。</p>{_figure(files['connectivity'], '各连接方法在 Theta、Alpha 和 Beta 频带中的全局平均值，以及 Alpha 频带的示例矩阵。')}{_atlas(files, 'connectivity_', '展开查看 8 种连接方法的 Theta、Alpha、Beta 矩阵图册')}</section>
<section id="coupling"><h2>跨频耦合</h2><p>PAC 观察慢频相位与快频振幅是否存在稳定关系；CPC 观察两个频带相位间的 n:m 同步。结果用于描述传感器层的节律协同，不单独作为疾病诊断依据。</p>{_figure(files['coupling'], '逐通道 Theta–Beta PAC 与 Theta–Alpha CPC 概览。')}{_figure(files['pac_maps'], 'PAC 与 CPC 的头皮空间分布。')}{_figure(files['pac_curve'], 'PAC 数值较高的六个通道的相位–振幅曲线；横轴为慢波相位，纵轴为归一化快波振幅。')}</section></main>'''
    body += f'''<section id="extended"><h2>补充分析图册</h2><p>以下图表补充展示区域频带功率、左右半球差异、Beta 包络、微状态时间分布、连接性节点与区域结果，以及跨频耦合的脑区汇总。各项均基于同一份质控后完整记录。</p>{_figure(files['clinical_scalp_waveform'], '全程 61 通道脑电波形。每条波形均覆盖完整保留记录。')}{_figure(files['cleaned_psd_detail'], '全头皮通道平均功率谱及标准误，范围为 0.5 至 45 Hz。')}{_figure(files['alpha_dispersion'], '后部 Alpha 主峰在频谱中的相对高度与主峰附近能量集中度。')}{_figure(files['alpha_dispersion_topomaps'], '全头皮 Alpha 峰频率及峰周能量集中度地形图。')}{_figure(files['alpha_hemisphere_views'], '左右后部 Alpha 频谱曲线与频率-电极分布。')}{_figure(files['beta_envelopes'], 'Beta1 与 Beta2 包络幅度的左右半球 P95 汇总。')}{_figure(files['regional_bandpower'], '额、中央、颞、顶、枕区的频带功率汇总。')}{_figure(files['hemispheric_asymmetry'], '各频带左右半球绝对功率的相对差异。')}{_figure(files['micro_duration_distribution'], '六类微状态的持续时间分布。')}{_figure(files['micro_total_contribution'], '微状态时间贡献率及 GFP 峰解释方差。')}{_figure(files['micro_transition_polar'], '最强的定向微状态转换。箭头宽度表示转换比例。')}{_figure(files['micro_distribution_histograms'], '微状态分段时长、每秒出现次数和每秒覆盖率分布。')}{_figure(files['micro_sequence_raster'], '完整记录的彩色微状态栅格图。')}{_figure(files['micro_outgoing'], '六类微状态的出向转换次数。')}{_figure(files['multiscale_entropy'], '全头皮平均多尺度样本熵随粗粒化尺度的变化。')}{_figure(files['connectivity_nodes'], '虚部相干与相位锁定值在三个频带的节点平均连接强度头皮分布。')}{_figure(files['connectivity_regional'], 'Theta、Alpha、Beta 频带的区域间 PLV 汇总。')}{_figure(files['coupling_regional'], 'PAC 与 CPC 的脑区平均值。')}</section>'''
    return _page('64导脑电定量分析报告', body)


_TRACEABILITY_GROUPS = (
    (
        "预处理与质量控制",
        ("qc_epochs.csv",),
        ("qc", "clinical_scalp_waveform"),
    ),
    (
        "频谱与节律",
        (
            "bandpower_by_channel.csv", "narrowband_power.csv", "power_ratios.csv",
            "posterior_alpha.csv", "spectral_statistics.csv", "band_peak_parameters.csv",
            "beta_envelope_by_channel.csv", "regional_bandpower.csv",
            "hemispheric_bandpower.csv", "alpha_spectral_dispersion.csv",
            "alpha_spectral_dispersion_windows.csv", "alpha_spectral_dispersion_spectra.csv",
        ),
        (
            "spectral", "cleaned_psd_detail", "bandpower", "bandpower_relative",
            "bandpower_bars", "alpha", "alpha_dispersion", "alpha_dispersion_topomaps",
            "alpha_hemisphere_views", "beta_envelopes", "spectral_statistics", "band_peaks",
            "narrowband_abs", "narrowband_rel", "ratios", "regional_bandpower",
            "hemispheric_asymmetry", "aperiodic",
        ),
    ),
    (
        "空间分布与动态",
        (
            "gfp_full_recording.csv", "gmd_successive_peaks.csv", "microstate_parameters.csv",
            "microstate_segments.csv", "microstate_per_second.csv",
            "microstate_information_dynamics.csv", "gfp_peak_topography_gmd.csv",
            "microstate_transition_counts.csv", "microstate_auto_information.csv",
            "microstate_state_self_information.csv", "microstate_source_time_mapping.csv",
            "microstate_source_time_segments.csv",
        ),
        (
            "gfp", "micro_templates", "micro_parameters", "micro_transition", "micro_sequence",
            "micro_coverage", "micro_duration_distribution", "micro_outgoing",
            "micro_total_contribution", "micro_transition_polar",
            "micro_distribution_histograms", "micro_sequence_raster", "micro_information_dynamics",
        ),
    ),
    (
        "复杂度",
        ("complexity_by_channel.csv", "multiscale_entropy.csv"),
        ("complexity", "multiscale_entropy", "omega"),
    ),
    (
        "功能连接",
        (
            "connectivity_global.csv", "connectivity_node_strength.csv",
            "connectivity_edges.csv", "connectivity_regional.csv",
        ),
        ("connectivity", "connectivity_nodes", "connectivity_regional"),
    ),
    (
        "跨频耦合",
        ("pac_by_channel.csv", "cpc_by_channel.csv", "cross_frequency_regional.csv"),
        ("coupling", "pac_maps", "pac_curve", "coupling_regional"),
    ),
)


def _traceability_link(relative_path, label):
    escaped_path = html.escape(relative_path.as_posix(), quote=True)
    return f'<a class="artifact-link" href="{escaped_path}" target="_blank" rel="noopener">{html.escape(label)}</a>'


def _existing_traceability_groups(destination, files):
    """Return only non-empty artifacts that were produced for this report run."""
    destination = Path(destination)
    tables = destination / "tables"
    assets = destination / "assets"
    seen = set()
    groups = []

    def add_if_present(entries, relative_path, label):
        path = destination / relative_path
        if path.is_file() and path.stat().st_size > 0:
            relative = Path(relative_path)
            entries.append((relative, label))
            seen.add(relative.as_posix())

    for title, table_names, file_keys in _TRACEABILITY_GROUPS:
        entries = []
        for name in table_names:
            add_if_present(entries, Path("tables") / name, f"CSV：{name}")
        for key in file_keys:
            filename = files.get(key)
            if filename:
                add_if_present(entries, Path("assets") / filename, f"图像：{filename}")
        if entries:
            groups.append((title, entries))

    summary_entries = []
    add_if_present(summary_entries, Path("analysis_summary.json"), "JSON：analysis_summary.json")
    add_if_present(summary_entries, Path("visual_manifest.json"), "JSON：visual_manifest.json")
    if summary_entries:
        groups.insert(0, ("结构化分析摘要", summary_entries))

    remaining = []
    for directory, prefix, suffix in ((tables, "tables", ".csv"), (assets, "assets", ".png")):
        if directory.is_dir():
            for path in sorted(directory.glob(f"*{suffix}")):
                relative = Path(prefix) / path.name
                if relative.as_posix() not in seen and path.stat().st_size > 0:
                    remaining.append((relative, f"{'CSV' if suffix == '.csv' else '图像'}：{path.name}"))
    if remaining:
        groups.append(("其他已生成文件", remaining))
    return groups


def _traceability_html(destination, files):
    groups = _existing_traceability_groups(destination, files)
    if not groups:
        return ""
    sections = []
    for title, entries in groups:
        links = "".join(_traceability_link(path, label) for path, label in entries)
        sections.append(f'<article class="artifact-group"><h3>{html.escape(title)}</h3><div class="artifact-list">{links}</div></article>')
    return '<section id="traceability"><h2>结果文件与图像追溯</h2><p>下列入口仅列出本次实际生成且非空的文件；可在离线报告目录中直接打开。</p>' + "".join(sections) + "</section>"


def _technical_html(summary, files, destination=None):
    qc = summary['quality_control']
    methods = [('频谱与节律', 'Welch PSD、绝对/相对频带功率、后部 Alpha、PAF、TBR、FAA、窄频带、功率比、频谱熵、SEF、频谱质心/带宽、频带峰参数、Specparam'), ('空间与动态', '全头皮地形图、GFP、GMD、六类微状态、持续时间、覆盖率、GEV、转换矩阵与连续序列'), ('复杂度', 'Hjorth、样本熵、Higuchi/Petrosian/Katz 分形维数、Hurst、排列熵、DFA、Lempel-Ziv、SVD 熵、多尺度熵及 Omega'), ('功能连接', 'ImCoh、wPLI²、ciPLV、PPC、Coherence、PLV、PLI、AEC；Theta、Alpha、Beta 频带'), ('跨频耦合', 'Theta 相位–Beta 振幅 PAC（Tort MI）与 Theta–Alpha n:m 跨频相位耦合')]
    body = f'''<header><div><h1>64导脑电定量分析技术细节</h1><p>输入范围、预处理、方法定义与结构化结果</p></div><a class="back" href="report.html">返回报告正文</a></header><main>
<section><h2>数据与分析范围</h2><table><tr><th>输入文件</th><td>{html.escape(summary['source']['filename'])}</td></tr><tr><th>原始记录</th><td>{summary['source']['duration_sec']:.1f} 秒，{summary['source']['sampling_rate_hz']:.0f} Hz</td></tr><tr><th>分析范围</th><td>质控后保留的完整记录，{summary['analysis_data']['duration_sec']:.1f} 秒，{len(summary['analysis_data']['eeg_channels'])} 个头皮通道</td></tr><tr><th>安全门禁</th><td>{html.escape(summary['safety_gate']['conclusion'])}：{html.escape('；'.join(summary['safety_gate']['reasons']))}</td></tr></table></section>
<section><h2>预处理顺序</h2><ol>{''.join(f'<li>{html.escape(str(step))}</li>' for step in qc['preprocessing']['steps'])}</ol><table><tr><th>总 epoch</th><td>{qc['epoch_summary']['total']}</td></tr><tr><th>保留 epoch</th><td>{qc['epoch_summary']['retained']}</td></tr><tr><th>剔除 epoch</th><td>{qc['epoch_summary']['rejected']}</td></tr><tr><th>保留率</th><td>{qc['epoch_summary']['retention_percent']:.1f}%</td></tr><tr><th>ICA</th><td>{html.escape(qc['ica']['status'])}</td></tr></table></section>
<section><h2>完整方法集合</h2><table><tr><th>模块</th><th>方法</th></tr>{''.join(f'<tr><td>{html.escape(a)}</td><td>{html.escape(b)}</td></tr>' for a,b in methods)}</table></section>
<section><h2>微状态短时信息动力学</h2><p>以全程状态占比计算每个状态的自信息，并在连续 1 秒窗内汇总；同一窗口内以 40 ms 固定滞后计算离散互信息及其归一化值。该图用于描述本次记录内微状态序列的时间变化，不作为功能连接指标。</p>{_figure(files['micro_information_dynamics'], '全程连续 1 秒窗的微状态自信息、状态熵以及 40 ms 滞后互信息。横轴覆盖全部质控保留记录。')}</section>
<section><h2>结构化结果</h2><p>同目录 <code>tables</code> 包含逐通道和逐频带 CSV；<code>analysis_summary.json</code> 保存完整机器可读结果；每张报告图均来自这些结构化结果或同一份质控后全程数据。</p></section></main>'''
    if destination is not None:
        body = body.replace("</main>", _traceability_html(destination, files) + "</main>")
    return _page('64导脑电定量分析技术细节', body)


def _value(value, unit=''):
    return '未计算' if value is None else f'{value:.3f}{(" " + unit) if unit else ""}'


def _page(title, body):
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title><style>
*{{box-sizing:border-box}} body{{margin:0;background:#f5f7f8;color:#17212b;font:16px/1.7 Arial,'Microsoft YaHei',sans-serif}} header{{background:#0c3448;color:#fff;padding:30px max(5vw,24px);display:flex;justify-content:space-between;gap:20px;align-items:flex-start}}h1{{margin:0;font-size:29px;font-weight:700}}h2{{margin:0 0 11px;font-size:23px;color:#0c3448}}h3{{margin:0 0 10px;font-size:17px;color:#164a60}}header p{{margin:5px 0 0;color:#dbe9ed}}nav{{position:sticky;top:0;z-index:4;padding:11px 5vw;background:#fff;border-bottom:1px solid #dbe4e9;display:flex;gap:18px;overflow:auto;white-space:nowrap}}nav a,.back{{color:#0f5f82;text-decoration:none;font-weight:700}}main{{max-width:1380px;margin:auto;padding:24px}}section{{background:#fff;border:1px solid #dce5e9;border-radius:6px;padding:24px;margin:0 0 20px}}.overview{{background:#edf6f7}}.metric-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:1px;background:#cbdde4;border:1px solid #cbdde4}}.metric-grid div{{background:#fff;padding:14px}}.metric-grid span{{display:block;color:#527080;font-size:13px}}.metric-grid strong{{display:block;color:#153e52;margin-top:3px;font-size:17px}}.status{{padding:7px 11px;border:1px solid #7bc3da;border-radius:4px;font-weight:700;font-size:13px;white-space:nowrap}}.blocked{{background:#fff3e5;color:#8a3d00;border-color:#e7ad68}}.pass{{background:#e8f7ef;color:#17663b}}.warning{{color:#873c04;background:#fff7ed;border-left:3px solid #d97706;padding:11px 13px}}.artifact-group{{border-top:1px solid #dce5e9;padding-top:16px;margin-top:16px}}.artifact-list{{display:flex;flex-wrap:wrap;gap:8px}}.artifact-link{{display:inline-block;border:1px solid #bad2dc;background:#f7fbfc;color:#0f5f82;text-decoration:none;padding:5px 8px;border-radius:4px;font-size:13px;line-height:1.35;overflow-wrap:anywhere}}.artifact-link:hover{{background:#e6f2f5}}figure{{margin:20px 0 0;border-top:1px solid #e4ecef;padding-top:16px}}figure img{{width:100%;display:block;background:white;cursor:zoom-in}}figcaption{{color:#526772;font-size:14px;margin-top:9px}}details{{border-top:1px solid #dce5e9;margin-top:18px;padding-top:14px}}summary{{cursor:pointer;color:#0f5f82;font-weight:700}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #d9e4e8;padding:9px 11px;text-align:left;vertical-align:top}}th{{background:#edf5f7;color:#164a60}}ol{{padding-left:24px}}code{{background:#edf3f5;padding:2px 5px}}@media(max-width:700px){{header{{padding:22px 18px;display:block}}h1{{font-size:24px}}main{{padding:14px}}section{{padding:17px}}.metric-grid{{grid-template-columns:1fr 1fr}}figure{{overflow:auto}}figure img{{min-width:700px}}}}</style></head><body>{body}</body></html>'''


def _write_manifest(destination, files, design_spec):
    assets = Path(destination) / 'assets'
    artifacts = []
    for name, filename in files.items():
        path = assets / filename
        if path.exists():
            artifacts.append({'name': name, 'path': f'assets/{filename}', 'size_bytes': path.stat().st_size})
    manifest = {'status': 'passed', 'artifact_type': 'full_recording_qeeg_complete_method_atlas', 'design_spec': design_spec, 'artifacts': artifacts, 'warnings': []}
    path = Path(destination) / 'visual_manifest.json'
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    return path


class _HrefCollector(HTMLParser):
    """Collect hyperlink targets without using a brittle regular expression."""

    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self.hrefs.append(href)


def _local_link_errors(page, destination):
    parser = _HrefCollector()
    parser.feed(page.read_text(encoding="utf-8"))
    errors = []
    output_root = Path(destination).resolve()
    for href in parser.hrefs:
        parsed = urlsplit(href)
        if parsed.scheme or parsed.netloc or href.startswith("#"):
            continue
        relative = unquote(parsed.path)
        if not relative:
            continue
        target = (page.parent / relative).resolve()
        if not target.is_relative_to(output_root):
            errors.append(f"Link escapes report output: {page} -> {href}")
        elif not target.is_file() or target.stat().st_size == 0:
            errors.append(f"Missing or empty link target: {page} -> {href}")
    return errors


def validate_full_report(destination, files):
    destination = Path(destination)
    required = [destination / 'report.html', destination / 'technical-details.html', destination / 'analysis_summary.json', destination / 'visual_manifest.json']
    required.extend(destination / 'assets' / file for file in files.values())
    errors = [f'Missing or empty: {path}' for path in required if not path.is_file() or path.stat().st_size == 0]
    for page in (destination / 'report.html', destination / 'technical-details.html'):
        if page.exists():
            if '\ufffd' in page.read_text(encoding='utf-8'):
                errors.append(f'Encoding corruption marker found: {page}')
            errors.extend(_local_link_errors(page, destination))
    return {'status': 'passed' if not errors else 'failed', 'checked_files': [str(item) for item in required], 'errors': errors}
