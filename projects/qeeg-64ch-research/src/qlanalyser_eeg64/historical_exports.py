"""Compatibility exports for the retired 64-channel report contract.

This module deliberately does not read BDF data or run an EEG algorithm.  It
turns values already persisted in ``analysis_summary.json`` into the CSV
schemas used by the historical HTML report.  Missing provenance is reported
explicitly through :class:`HistoricalExportBundle` rather than reconstructed.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median, pstdev
from types import MappingProxyType
from typing import Any, Final, Mapping, Sequence
from uuid import uuid4

from .gfp import GFPConfig


BANDS = ("delta", "theta", "alpha", "beta", "gamma")
PEAK_BANDS = (("delta", 1.0, 4.0), ("theta", 4.0, 8.0), ("alpha", 8.0, 13.0),
              ("beta1", 13.0, 20.0), ("beta2", 20.0, 30.0), ("gamma", 30.0, 45.0))
REGIONS = ("frontal", "central", "temporal", "parietal", "occipital")
DEFAULT_MICROSTATE_STATES = ("A", "B", "C", "D", "E", "F")
GFP_REPORT_LIMITATION_CODE: Final[str] = "historical_gfp_short_continuous_interval"
METHOD_LABELS = {
    "imcoh": "绝对虚部相干强度 |ImCoh|", "wpli2_debiased": "去偏 wPLI²",
    "ciplv": "校正相位锁定值 ciPLV", "ppc": "成对相位一致性 PPC",
    "coherence": "相干 Coherence", "plv": "相位锁定值 PLV",
    "pli": "相位滞后指数 PLI", "aec": "振幅包络相关 AEC",
}

REQUIRED_HISTORICAL_TABLES: Final[frozenset[str]] = frozenset({
    "alpha_hemisphere_summary.csv", "alpha_posterior_channels.csv", "band_peak_parameters.csv",
    "beta_hemisphere_channels.csv", "beta_hemisphere_summary.csv", "channel_bandpower.csv",
    "connectivity_edges.csv", "connectivity_global_summary.csv", "connectivity_node_strength.csv",
    "connectivity_regional_summary.csv", "cross_phase_coupling_channel_metrics.csv",
    "cross_phase_coupling_regional_summary.csv", "gfp_gmd_summary.csv", "gfp_timeseries.csv",
    "hemispheric_asymmetry.csv", "microstate_auto_information.csv", "microstate_direct_transitions.csv",
    "microstate_distribution_statistics.csv", "microstate_per_second.csv", "microstate_segments.csv",
    "microstate_transition_counts.csv", "microstate_transition_matrix.csv", "multiscale_entropy.csv",
    "pac_channel_metrics.csv", "pac_phase_amplitude_distribution.csv", "pac_regional_summary.csv",
    "qlanalyser_core_metrics.csv", "qlanalyser_narrowband_power.csv", "qlanalyser_power_ratios.csv",
    "regional_bandpower.csv", "report_compatibility_channel_spectral.csv", "spatial_complexity.csv",
    "spectral_parameterization.csv", "spectral_peaks.csv",
})

_TABLE_HEADERS: Final[Mapping[str, tuple[str, ...]]] = MappingProxyType({
    "alpha_hemisphere_summary.csv": (
        "hemisphere", "channels", "dominant_peak_psd_channel", "dominant_alpha_frequency_hz",
        "dominant_alpha_peak_psd_uv2_per_hz", "maximum_envelope_channel", "maximum_alpha_envelope_uv",
        "p95_envelope_channel", "p95_alpha_envelope_uv", "mean_alpha_integrated_power_uv2",
        "power_weighted_modal_frequency_hz", "power_weighted_frequency_dispersion_hz",
        "posterior_alpha_asymmetry_percent",
    ),
    "alpha_posterior_channels.csv": (
        "hemisphere", "channel", "alpha_modal_frequency_hz", "alpha_peak_psd_uv2_per_hz",
        "alpha_integrated_power_uv2", "alpha_envelope_max_uv", "alpha_envelope_p95_uv",
    ),
    "band_peak_parameters.csv": (
        "scope", "band", "requested_low_hz", "requested_high_hz", "fitted_low_hz", "fitted_high_hz",
        "detected_peak_count", "peak_detected", "peak_frequency_hz", "peak_bandwidth_hz",
        "peak_prominence_log10",
    ),
    "beta_hemisphere_channels.csv": (
        "band", "band_low_hz", "band_high_hz", "hemisphere", "channel", "envelope_max_uv",
        "envelope_p95_uv",
    ),
    "beta_hemisphere_summary.csv": (
        "band", "band_low_hz", "band_high_hz", "hemisphere", "channels", "maximum_envelope_channel",
        "maximum_envelope_uv", "p95_envelope_channel", "p95_envelope_uv",
    ),
    "channel_bandpower.csv": (
        "channel",
        *(field for band in BANDS for field in (
            f"{band}_absolute_uv2", f"{band}_relative", f"{band}_log10_uv2",
        )),
        "higuchi_fractal_dimension", "detrended_fluctuation_alpha", "petrosian_fractal_dimension",
        "katz_fractal_dimension", "hjorth_activity_uv2", "hjorth_mobility", "hjorth_complexity",
        "sample_entropy", "hurst_exponent", "permutation_entropy", "lempel_ziv_complexity", "svd_entropy",
        "multiscale_entropy_complexity_index", "spectral_entropy", "alpha_center_of_gravity_hz",
        "spectral_centroid_hz", "spectral_bandwidth_hz", "spectral_edge_50_hz", "spectral_edge_90_hz",
        "spectral_edge_95_hz", "theta_beta_ratio", "delta_alpha_ratio", "theta_alpha_ratio",
    ),
    "connectivity_edges.csv": (
        "branch", "method", "band", "channel_1", "channel_2", "estimate", "strength", "value_definition",
    ),
    "connectivity_global_summary.csv": (
        "branch", "method", "band", "edge_count", "mean_strength", "median_strength", "value_definition",
    ),
    "connectivity_node_strength.csv": (
        "branch", "method", "band", "channel", "edge_count", "mean_strength", "median_strength", "region",
        "value_definition",
    ),
    "connectivity_regional_summary.csv": (
        "branch", "method", "band", "region_1", "region_2", "edge_count", "mean_strength",
        "median_strength", "value_definition",
    ),
    "cross_phase_coupling_channel_metrics.csv": (
        "channel", "coupling", "low_phase_band_low_hz", "low_phase_band_high_hz",
        "high_phase_band_low_hz", "high_phase_band_high_hz", "low_phase_multiplier", "high_phase_multiplier",
        "n_m_phase_locking_value", "analyzed_samples", "analyzed_duration_sec",
    ),
    "cross_phase_coupling_regional_summary.csv": (
        "region", "coupling", "channel_count", "n_m_phase_locking_value_mean",
        "n_m_phase_locking_value_median",
    ),
    "gfp_gmd_summary.csv": (
        "filter_low_hz", "filter_high_hz", "gfp_definition", "gmd_definition", "gmd_polarity",
        *(field for prefix in ("continuous_gfp_uv", "peak_gfp_uv", "successive_peak_gmd") for field in (
            f"{prefix}_count", f"{prefix}_mean", f"{prefix}_median", f"{prefix}_standard_deviation",
            f"{prefix}_p95", f"{prefix}_maximum",
        )),
    ),
    "gfp_timeseries.csv": ("time_sec", "gfp_uv"),
    "hemispheric_asymmetry.csv": (
        "left_channel", "right_channel", *(f"{band}_asymmetry_percent" for band in BANDS),
    ),
    "microstate_auto_information.csv": ("lag_samples", "lag_ms", "auto_information_bits"),
    "microstate_direct_transitions.csv": (
        "from_state", "to_state", "transition_count", "conditional_probability_percent",
    ),
    "microstate_distribution_statistics.csv": (
        "state", "total_duration_sec", "segment_count", "duration_mean_ms", "duration_sd_ms",
        "longest_duration_samples", "longest_duration_sec", "longest_duration_ms",
        "per_second_occurrence_mean_hz", "per_second_occurrence_sd_hz",
        "per_second_contribution_mean_percent", "per_second_contribution_sd_percent",
    ),
    "microstate_segments.csv": (
        "segment_index", "state_index", "state", "start_sample", "stop_sample_exclusive", "start_sec",
        "stop_sec", "duration_samples", "duration_sec", "duration_ms",
    ),
    "multiscale_entropy.csv": (
        "channel", "scale", "coarse_grained_sample_count", "sample_entropy", "tolerance_uv",
        "embedding_dimension", "distance_metric", "complexity_index",
    ),
    "pac_channel_metrics.csv": (
        "channel", "coupling", "phase_band_low_hz", "phase_band_high_hz", "amplitude_band_low_hz",
        "amplitude_band_high_hz", "modulation_index", "mean_vector_length", "analyzed_samples",
        "analyzed_duration_sec",
    ),
    "pac_phase_amplitude_distribution.csv": (
        "channel", "coupling", "phase_bin_index", "phase_center_deg", "mean_amplitude_uv",
        "relative_amplitude", "analyzed_samples",
    ),
    "pac_regional_summary.csv": (
        "region", "coupling", "channel_count", "modulation_index_mean", "modulation_index_median",
        "mean_vector_length_mean", "mean_vector_length_median",
    ),
    "qlanalyser_core_metrics.csv": (
        "metric", "status", "value", "unit", "channels", "definition", "evidence", "peak_psd_uv2_per_hz",
    ),
    "qlanalyser_narrowband_power.csv": (
        "channel", "band", "low_hz", "high_hz", "absolute_power_uv2", "relative_power",
    ),
    "qlanalyser_power_ratios.csv": (
        "channel", "ratio", "numerator_band", "denominator_band", "numerator_power_uv2",
        "denominator_power_uv2", "value",
    ),
    "regional_bandpower.csv": (
        "region", "channel_count", "channels",
        *(field for band in BANDS for field in (f"{band}_absolute_uv2", f"{band}_relative")),
    ),
    "report_compatibility_channel_spectral.csv": (
        "channel",
        *(field for band, _, _ in PEAK_BANDS for field in (
            f"{band}_peak_psd_uv2_per_hz", f"{band}_integrated_power_uv2", f"{band}_modal_frequency_hz",
        )),
    ),
    "spatial_complexity.csv": (
        "method", "channel_count", "reference_rank_loss", "maximum_effective_dimension",
        "omega_effective_dimension", "omega_normalized", "eigenvalue_entropy_nats", "matrix", "unit",
        "frequency_range_hz",
    ),
    "spectral_parameterization.csv": (
        "scope", "aperiodic_offset_log10_uv2_per_hz", "aperiodic_exponent", "fit_mae_log10_power",
        "fit_r_squared", "peak_count",
    ),
    "spectral_peaks.csv": (
        "scope", "peak_index", "band", "center_frequency_hz", "peak_power_above_aperiodic_log10",
        "bandwidth_hz",
    ),
})


@dataclass(frozen=True)
class HistoricalExportBundle:
    """CSV rows and provenance caveats, all built from a persisted summary."""

    tables: dict[str, list[dict[str, Any]]]
    partial: dict[str, str]
    unavailable: dict[str, str]


def _region(channel: str) -> str:
    name = channel.upper()
    if name.startswith(("FP", "AF", "F")):
        return "frontal"
    if name.startswith(("FT", "TP", "T")):
        return "temporal"
    if name.startswith(("CP", "P")):
        return "parietal"
    if name.startswith(("FC", "C")):
        return "central"
    return "occipital"


def _side(channel: str) -> str | None:
    """Return scalp hemisphere using the conventional odd/even label rule."""
    digits = "".join(c for c in channel if c.isdigit())
    if not digits:
        return None
    number = int(digits)
    if number == 0 or number % 10 == 0:
        return None
    return "left" if number % 2 else "right"


def _safe_float(value: Any) -> float | None:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def _mean(values: Sequence[Any]) -> float | None:
    clean = [x for value in values if (x := _safe_float(value)) is not None]
    return mean(clean) if clean else None


def _median(values: Sequence[Any]) -> float | None:
    clean = [x for value in values if (x := _safe_float(value)) is not None]
    return median(clean) if clean else None


def _std(values: Sequence[Any]) -> float | None:
    clean = [x for value in values if (x := _safe_float(value)) is not None]
    return pstdev(clean) if clean else None


def _table_headers(summary: Mapping[str, Any]) -> dict[str, tuple[str, ...]]:
    states = tuple(str(state) for state in summary.get("microstates", {}).get("state_names", []))
    states = states or DEFAULT_MICROSTATE_STATES
    headers = dict(_TABLE_HEADERS)
    headers["microstate_transition_matrix.csv"] = (
        "from_state", *(f"to_{state}" for state in states),
    )
    headers["microstate_transition_counts.csv"] = (
        "from_state", *(f"to_{state}" for state in states),
    )
    headers["microstate_per_second.csv"] = (
        "second",
        *(field for state in states for field in (f"{state}_occurrences", f"{state}_contribution_percent")),
        "unlabeled_percent",
    )
    if frozenset(headers) != REQUIRED_HISTORICAL_TABLES:
        raise RuntimeError("historical table headers do not match the required table contract")
    return headers


def _retained_source_times(source_time_mapping: Mapping[str, Any], sample_count: int) -> list[float]:
    rate = _safe_float(source_time_mapping.get("analysis_sampling_rate_hz"))
    if rate is None or rate <= 0:
        raise ValueError("source_time_mapping requires a positive analysis_sampling_rate_hz")
    expected_count = source_time_mapping.get("analysis_sample_count")
    if not isinstance(expected_count, int) or expected_count != sample_count:
        raise ValueError("source_time_mapping does not match the GFP sample count")

    times: list[float] = []
    expected_start = 0
    intervals = source_time_mapping.get("retained_intervals", [])
    if not isinstance(intervals, Sequence) or isinstance(intervals, (str, bytes)):
        raise ValueError("source_time_mapping retained_intervals must be a sequence")
    for interval in intervals:
        if not isinstance(interval, Mapping):
            raise ValueError("source_time_mapping retained_intervals must contain mappings")
        start = interval.get("analysis_sample_start")
        stop = interval.get("analysis_sample_stop")
        source_start = _safe_float(interval.get("source_start_sec"))
        if not isinstance(start, int) or not isinstance(stop, int) or start != expected_start or stop < start:
            raise ValueError("source_time_mapping retained intervals must be contiguous and ordered")
        if source_start is None:
            raise ValueError("source_time_mapping retained interval requires source_start_sec")
        times.extend(source_start + offset / rate for offset in range(stop - start))
        expected_start = stop
    if expected_start != sample_count or len(times) != sample_count:
        raise ValueError("source_time_mapping retained intervals do not match the GFP sample count")
    return times


def _legacy_epoch_source_time_mapping(
    epoch_rows: Any, analysis_sampling_rate_hz: Any, sample_count: int
) -> dict[str, Any]:
    """Recover source coordinates from persisted pre-mapping QC epoch rows."""
    rate = _safe_float(analysis_sampling_rate_hz)
    if rate is None or rate <= 0:
        raise ValueError("legacy GFP export requires a positive sampling_rate_hz")
    if not isinstance(epoch_rows, Sequence) or isinstance(epoch_rows, (str, bytes)):
        raise ValueError(
            "GFP timeseries export requires quality_control.source_time_mapping "
            "or persisted quality_control.epochs"
        )

    intervals = []
    analysis_cursor = 0
    previous_end = 0.0
    for index, row in enumerate(epoch_rows):
        if not isinstance(row, Mapping):
            raise ValueError(f"quality_control.epochs[{index}] must be a mapping")
        start = _safe_float(row.get("start_sec"))
        stop = _safe_float(row.get("end_sec"))
        if start is None or stop is None or stop <= start or start < previous_end:
            raise ValueError("quality_control.epochs must contain ordered positive time intervals")
        interval_samples_float = (stop - start) * rate
        interval_samples = int(round(interval_samples_float))
        if interval_samples <= 0 or not math.isclose(
            interval_samples_float, interval_samples, rel_tol=0.0, abs_tol=1e-6
        ):
            raise ValueError("quality_control.epochs intervals do not align to GFP sampling_rate_hz")
        if row.get("retained") is True:
            intervals.append({
                "analysis_sample_start": analysis_cursor,
                "analysis_sample_stop": analysis_cursor + interval_samples,
                "source_start_sec": start,
            })
            analysis_cursor += interval_samples
        previous_end = stop

    if analysis_cursor != sample_count:
        raise ValueError("quality_control.epochs do not match the GFP sample count")
    return {
        "analysis_sampling_rate_hz": rate,
        "analysis_sample_count": sample_count,
        "retained_intervals": intervals,
    }


def _continuous_retained_interval_lengths(
    source_time_mapping: Mapping[str, Any], sample_count: int, sampling_rate_hz: float
) -> list[int]:
    """Return source-continuous retained lengths without reading EEG values."""
    mapped_rate = _safe_float(source_time_mapping.get("analysis_sampling_rate_hz"))
    if mapped_rate is not None and not math.isclose(
        mapped_rate, sampling_rate_hz, rel_tol=0.0, abs_tol=1e-9
    ):
        raise ValueError("source_time_mapping sampling rate does not match saved GFP")
    mapped_count = source_time_mapping.get("analysis_sample_count")
    if mapped_count != sample_count:
        raise ValueError("source_time_mapping does not match the GFP sample count")

    intervals = source_time_mapping.get("retained_intervals", [])
    if not isinstance(intervals, Sequence) or isinstance(intervals, (str, bytes)):
        raise ValueError("source_time_mapping retained_intervals must be a sequence")

    continuous_lengths: list[int] = []
    analysis_cursor = 0
    previous_source_stop = None
    for index, interval in enumerate(intervals):
        if not isinstance(interval, Mapping):
            raise ValueError(f"source_time_mapping retained_intervals[{index}] must be a mapping")
        analysis_start = interval.get("analysis_sample_start")
        analysis_stop = interval.get("analysis_sample_stop")
        if (
            not isinstance(analysis_start, int)
            or not isinstance(analysis_stop, int)
            or analysis_start != analysis_cursor
            or analysis_stop <= analysis_start
        ):
            raise ValueError("source_time_mapping retained analysis intervals must be contiguous and ordered")
        interval_length = analysis_stop - analysis_start

        source_start = interval.get("screened_sample_start")
        source_stop = interval.get("screened_sample_stop")
        if not isinstance(source_start, int) or not isinstance(source_stop, int):
            source_start_sec = _safe_float(interval.get("source_start_sec"))
            if source_start_sec is None:
                raise ValueError("source_time_mapping retained interval requires source coordinates")
            source_start_float = source_start_sec * sampling_rate_hz
            source_start = int(round(source_start_float))
            if not math.isclose(source_start_float, source_start, rel_tol=0.0, abs_tol=1e-6):
                raise ValueError("source_time_mapping source coordinates do not align to saved GFP")
            source_stop = source_start + interval_length
        if source_stop - source_start != interval_length:
            raise ValueError("source_time_mapping retained interval sample counts do not match")
        if previous_source_stop is not None and source_start < previous_source_stop:
            raise ValueError("source_time_mapping retained source intervals must be ordered")

        if continuous_lengths and source_start == previous_source_stop:
            continuous_lengths[-1] += interval_length
        else:
            continuous_lengths.append(interval_length)
        analysis_cursor = analysis_stop
        previous_source_stop = source_stop

    if analysis_cursor != sample_count or sum(continuous_lengths) != sample_count:
        raise ValueError("source_time_mapping does not match the GFP sample count")
    return continuous_lengths


def saved_gfp_filter_interval_audit(summary: Mapping[str, Any]) -> dict[str, Any] | None:
    """Audit a saved GFP result against the current continuous-interval policy."""
    gfp = summary.get("gfp_gmd")
    if not isinstance(gfp, Mapping):
        return None
    series = gfp.get("gfp_full_series")
    if not isinstance(series, Mapping):
        return None
    values = series.get("values_uv")
    if values is None:
        return None
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        raise ValueError("saved GFP full series must be a sequence")
    sample_count = len(values)
    if sample_count == 0:
        return None

    sampling_rate_hz = _safe_float(series.get("sampling_rate_hz"))
    filter_hz = gfp.get("filter_hz")
    if sampling_rate_hz is None or sampling_rate_hz <= 0:
        raise ValueError("saved GFP requires a positive sampling_rate_hz")
    if not isinstance(filter_hz, Sequence) or isinstance(filter_hz, (str, bytes)):
        raise ValueError("saved GFP requires filter_hz")
    low_hz = _safe_float(filter_hz[0] if filter_hz else None)
    if low_hz is None or low_hz <= 0:
        raise ValueError("saved GFP requires a positive low filter cutoff")

    quality_control = summary.get("quality_control", {})
    if not isinstance(quality_control, Mapping):
        raise ValueError("saved GFP requires quality_control metadata")
    source_time_mapping = quality_control.get("source_time_mapping")
    mapping_source = "quality_control.source_time_mapping"
    if source_time_mapping is None:
        source_time_mapping = _legacy_epoch_source_time_mapping(
            quality_control.get("epochs"), sampling_rate_hz, sample_count
        )
        mapping_source = "quality_control.epochs"
    if not isinstance(source_time_mapping, Mapping):
        raise ValueError("quality_control.source_time_mapping must be a mapping")

    lengths = _continuous_retained_interval_lengths(
        source_time_mapping, sample_count, sampling_rate_hz
    )
    minimum_cycles = GFPConfig().minimum_filter_cycles
    minimum_samples = int(math.ceil(minimum_cycles * sampling_rate_hz / low_hz))
    short_lengths = [length for length in lengths if length < minimum_samples]
    return {
        "mapping_source": mapping_source,
        "sampling_rate_hz": sampling_rate_hz,
        "low_cutoff_hz": low_hz,
        "minimum_cycles": minimum_cycles,
        "minimum_interval_samples": minimum_samples,
        "minimum_interval_duration_sec": minimum_samples / sampling_rate_hz,
        "continuous_interval_count": len(lengths),
        "short_interval_count": len(short_lengths),
        "shortest_interval_samples": min(lengths),
        "shortest_interval_duration_sec": min(lengths) / sampling_rate_hz,
        "analysis_sample_count": sample_count,
    }


def saved_gfp_report_limitations(summary: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Build deterministic, aggregate-only report limitations for saved GFP."""
    audit = saved_gfp_filter_interval_audit(summary)
    if audit is None or audit["short_interval_count"] == 0:
        return []
    message = (
        "历史 GFP 结果限制：本冻结报告生成于连续源时段三周期校验策略加入之前。"
        f"按当前 {audit['low_cutoff_hz']:.1f} Hz 低截止、{audit['minimum_cycles']:g} 个周期"
        f"（至少 {audit['minimum_interval_samples']} 个样本 / "
        f"{audit['minimum_interval_duration_sec']:.2f} 秒）要求复核，"
        f"{audit['continuous_interval_count']} 个连续保留时段中有 "
        f"{audit['short_interval_count']} 个未达标，最短 "
        f"{audit['shortest_interval_samples']} 个样本（"
        f"{audit['shortest_interval_duration_sec']:.2f} 秒）。"
        "因此保留既有 GFP 数值用于历史追溯，不将该 GFP 结果视为满足当前滤波策略；"
        "需从原始记录重新运行后方可完成科学验收。"
    )
    return [{
        "code": GFP_REPORT_LIMITATION_CODE,
        "severity": "scientific_limitation",
        "scope": "gfp_gmd",
        "message": message,
        "audit": audit,
    }]


def _band_values(spectral: Mapping[str, Any], band: str) -> dict[str, float]:
    all_bands = spectral.get("absolute_band_power", {})
    if isinstance(all_bands, list):
        item = next((row for row in all_bands if row.get("band") == band), {})
    else:
        item = all_bands.get(band, {})
    return item.get("absolute_power_uv2", item.get("value", item)) if isinstance(item, Mapping) else {}


def _relative_values(spectral: Mapping[str, Any], band: str) -> dict[str, float]:
    all_bands = spectral.get("absolute_band_power", {})
    if isinstance(all_bands, list):
        item = next((row for row in all_bands if row.get("band") == band), {})
    else:
        item = all_bands.get(band, {})
    return item.get("relative_power", {}) if isinstance(item, Mapping) else {}


def _channels(spectral: Mapping[str, Any]) -> list[str]:
    values = _band_values(spectral, "alpha")
    return list(values) if values else list(spectral.get("psd_uv2_per_hz", {}))


def _integrate(values: Sequence[float], frequencies: Sequence[float], low: float, high: float) -> tuple[float | None, float | None, float | None]:
    pairs = [(float(f), _safe_float(v)) for f, v in zip(frequencies, values) if low <= float(f) <= high]
    pairs = [(f, v) for f, v in pairs if v is not None]
    if not pairs:
        return None, None, None
    peak_frequency, peak_value = max(pairs, key=lambda item: item[1])
    if len(pairs) == 1:
        return peak_value, pairs[0][1], peak_frequency
    integral = sum((pairs[i + 1][0] - pairs[i][0]) * (pairs[i][1] + pairs[i + 1][1]) / 2 for i in range(len(pairs) - 1))
    return peak_value, integral, peak_frequency


def _alpha_tables(spectral: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
    posterior = spectral.get("posterior_alpha", {})
    channels = posterior.get("channels", [])
    rows = [{"hemisphere": row.get("hemisphere"), "channel": row.get("channel"),
             "alpha_modal_frequency_hz": row.get("alpha_modal_frequency_hz"),
             "alpha_peak_psd_uv2_per_hz": row.get("alpha_peak_psd_uv2_per_hz"),
             "alpha_integrated_power_uv2": row.get("alpha_integrated_power_uv2"),
             "alpha_envelope_max_uv": row.get("alpha_envelope_max_uv"),
             "alpha_envelope_p95_uv": row.get("alpha_envelope_p95_uv")} for row in channels]
    summaries: list[dict[str, Any]] = []
    asymmetry = posterior.get("posterior_alpha_asymmetry_percent")
    for hemisphere in ("left", "right"):
        selected = [row for row in rows if row["hemisphere"] == hemisphere]
        if not selected:
            continue
        peak = max(selected, key=lambda row: _safe_float(row["alpha_peak_psd_uv2_per_hz"]) or float("-inf"))
        maximum = max(selected, key=lambda row: _safe_float(row["alpha_envelope_max_uv"]) or float("-inf"))
        p95 = max(selected, key=lambda row: _safe_float(row["alpha_envelope_p95_uv"]) or float("-inf"))
        weights = [(_safe_float(row["alpha_integrated_power_uv2"]) or 0.0, _safe_float(row["alpha_modal_frequency_hz"])) for row in selected]
        valid = [(power, frequency) for power, frequency in weights if frequency is not None and power > 0]
        weighted = sum(power * frequency for power, frequency in valid) / sum(power for power, _ in valid) if valid else None
        dispersion = (math.sqrt(sum(power * (frequency - weighted) ** 2 for power, frequency in valid) / sum(power for power, _ in valid)) if weighted is not None else None)
        summaries.append({"hemisphere": hemisphere, "channels": ";".join(str(row["channel"]) for row in selected),
                          "dominant_peak_psd_channel": peak["channel"], "dominant_alpha_frequency_hz": peak["alpha_modal_frequency_hz"],
                          "dominant_alpha_peak_psd_uv2_per_hz": peak["alpha_peak_psd_uv2_per_hz"],
                          "maximum_envelope_channel": maximum["channel"], "maximum_alpha_envelope_uv": maximum["alpha_envelope_max_uv"],
                          "p95_envelope_channel": p95["channel"], "p95_alpha_envelope_uv": p95["alpha_envelope_p95_uv"],
                          "mean_alpha_integrated_power_uv2": _mean([row["alpha_integrated_power_uv2"] for row in selected]),
                          "power_weighted_modal_frequency_hz": weighted,
                          "power_weighted_frequency_dispersion_hz": dispersion,
                          "posterior_alpha_asymmetry_percent": asymmetry})
    return {"alpha_posterior_channels.csv": rows, "alpha_hemisphere_summary.csv": summaries}


def _beta_tables(spectral: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
    output: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    for band, payload in spectral.get("beta_envelopes", {}).items():
        low, high = (payload.get("range_hz") or (None, None))
        channels = []
        for row in payload.get("channels", []):
            hemisphere = _side(str(row.get("channel", "")))
            if hemisphere:
                item = {"band": band, "band_low_hz": low, "band_high_hz": high, "hemisphere": hemisphere,
                        "channel": row.get("channel"), "envelope_max_uv": row.get("max_uv"), "envelope_p95_uv": row.get("p95_uv")}
                output.append(item); channels.append(item)
        for hemisphere in ("left", "right"):
            selected = [row for row in channels if row["hemisphere"] == hemisphere]
            if selected:
                maximum = max(selected, key=lambda row: _safe_float(row["envelope_max_uv"]) or float("-inf"))
                p95 = max(selected, key=lambda row: _safe_float(row["envelope_p95_uv"]) or float("-inf"))
                summaries.append({"band": band, "band_low_hz": low, "band_high_hz": high, "hemisphere": hemisphere,
                                  "channels": ";".join(str(row["channel"]) for row in selected), "maximum_envelope_channel": maximum["channel"],
                                  "maximum_envelope_uv": maximum["envelope_max_uv"], "p95_envelope_channel": p95["channel"], "p95_envelope_uv": p95["envelope_p95_uv"]})
    return {"beta_hemisphere_channels.csv": output, "beta_hemisphere_summary.csv": summaries}


def _spectral_tables(summary: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
    spectral = summary.get("spectral", {})
    channels = _channels(spectral)
    complexity = {row.get("channel"): row for row in summary.get("complexity", {}).get("channel_metrics", [])}
    stats = spectral.get("channel_spectral_statistics", {})
    ratios = spectral.get("power_ratios", [])
    ratio_by_name = {row.get("ratio"): row.get("value", {}) for row in ratios}
    rows = []
    for channel in channels:
        row: dict[str, Any] = {"channel": channel}
        for band in BANDS:
            power = _band_values(spectral, band).get(channel)
            row[f"{band}_absolute_uv2"] = power; row[f"{band}_relative"] = _relative_values(spectral, band).get(channel)
            row[f"{band}_log10_uv2"] = math.log10(max(float(power), 1e-30)) if _safe_float(power) is not None else None
        metric = complexity.get(channel, {})
        mapping = {"higuchi_fd": "higuchi_fractal_dimension", "dfa_exponent": "detrended_fluctuation_alpha", "petrosian_fd": "petrosian_fractal_dimension", "katz_fd": "katz_fractal_dimension"}
        for source, target in mapping.items(): row[target] = metric.get(source)
        for key in ("hjorth_activity_uv2", "hjorth_mobility", "hjorth_complexity", "sample_entropy", "hurst_exponent", "permutation_entropy", "lempel_ziv_complexity", "svd_entropy", "multiscale_entropy_complexity_index"):
            row[key] = metric.get(key)
        statistic = stats.get(channel, {})
        for source, target in {"spectral_entropy": "spectral_entropy", "alpha_centroid_hz": "alpha_center_of_gravity_hz", "spectral_centroid_hz": "spectral_centroid_hz", "spectral_bandwidth_hz": "spectral_bandwidth_hz", "spectral_edge_50_hz": "spectral_edge_50_hz", "spectral_edge_90_hz": "spectral_edge_90_hz", "spectral_edge_95_hz": "spectral_edge_95_hz"}.items(): row[target] = statistic.get(source)
        for name, target in (("theta/beta", "theta_beta_ratio"), ("delta/alpha", "delta_alpha_ratio"), ("theta/alpha", "theta_alpha_ratio")):
            row[target] = ratio_by_name.get(name, {}).get(channel)
        rows.append(row)
    ratio_rows = []
    for item in ratios:
        for channel, value in item.get("value", {}).items():
            ratio_rows.append({"channel": channel, "ratio": item.get("ratio"), "numerator_band": item.get("numerator_band"), "denominator_band": item.get("denominator_band"), "numerator_power_uv2": item.get("numerator_power_uv2", {}).get(channel), "denominator_power_uv2": item.get("denominator_power_uv2", {}).get(channel), "value": value})
    narrow = []
    for item in spectral.get("narrowband_power", {}).get("bands", []):
        for channel, value in item.get("absolute_power_uv2", {}).items(): narrow.append({"channel": channel, "band": item.get("band"), "low_hz": item.get("low_hz"), "high_hz": item.get("high_hz"), "absolute_power_uv2": value, "relative_power": item.get("relative_power", {}).get(channel)})
    regional = []
    for region in REGIONS:
        selected = [channel for channel in channels if _region(channel) == region]
        item: dict[str, Any] = {"region": region, "channel_count": len(selected), "channels": ";".join(selected)}
        for band in BANDS:
            item[f"{band}_absolute_uv2"] = _mean([_band_values(spectral, band).get(ch) for ch in selected]); item[f"{band}_relative"] = _mean([_relative_values(spectral, band).get(ch) for ch in selected])
        regional.append(item)
    compat = []
    freqs = spectral.get("frequencies_hz", [])
    psds = spectral.get("psd_uv2_per_hz", {})
    for channel in channels:
        item = {"channel": channel}
        for band, low, high in PEAK_BANDS:
            peak, integral, modal = _integrate(psds.get(channel, []), freqs, low, high)
            item[f"{band}_peak_psd_uv2_per_hz"] = peak; item[f"{band}_integrated_power_uv2"] = integral; item[f"{band}_modal_frequency_hz"] = modal
        compat.append(item)
    return {"channel_bandpower.csv": rows, "qlanalyser_power_ratios.csv": ratio_rows, "qlanalyser_narrowband_power.csv": narrow, "regional_bandpower.csv": regional, "report_compatibility_channel_spectral.csv": compat}


def _asymmetry(spectral: Mapping[str, Any]) -> list[dict[str, Any]]:
    channels = _channels(spectral); lookup = set(channels); rows = []
    for left in channels:
        if _side(left) != "left": continue
        digits = "".join(c for c in left if c.isdigit())
        right = left[:-len(digits)] + str(int(digits) + 1) if digits else ""
        if right not in lookup: continue
        row = {"left_channel": left, "right_channel": right}
        for band in BANDS:
            lv, rv = _band_values(spectral, band).get(left), _band_values(spectral, band).get(right)
            denominator = ((_safe_float(lv) or 0) + (_safe_float(rv) or 0)) / 2
            row[f"{band}_asymmetry_percent"] = ((_safe_float(rv) - _safe_float(lv)) / denominator * 100) if denominator else None
        rows.append(row)
    return rows


def _connectivity_tables(connectivity: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
    global_rows=[]; node_rows=[]; regional_rows=[]; edge_rows=[]
    channels=connectivity.get("channels", [])
    for band, methods in connectivity.get("bands", {}).items():
        for method, payload in methods.items():
            definition=METHOD_LABELS.get(method, method); edges=payload.get("edges", []); matrix=payload.get("matrix", [])
            values=[edge.get("value") for edge in edges]
            global_rows.append({"branch":"average_primary","method":method,"band":band,"edge_count":len(edges),"mean_strength":_mean(values),"median_strength":_median(values),"value_definition":definition})
            for index, channel in enumerate(channels):
                vals=[matrix[index][j] for j in range(len(channels)) if j != index and index < len(matrix) and j < len(matrix[index])]
                node_rows.append({"branch":"average_primary","method":method,"band":band,"channel":channel,"edge_count":len(vals),"mean_strength":_mean(vals),"median_strength":_median(vals),"region":_region(channel),"value_definition":definition})
            for edge in edges:
                first, second=_region(edge.get("source","")),_region(edge.get("target","")); r1,r2=sorted((first,second))
                edge_rows.append({"branch":"average_primary","method":method,"band":band,"channel_1":edge.get("source"),"channel_2":edge.get("target"),"estimate":edge.get("value"),"strength":edge.get("value"),"value_definition":definition})
                # Group after all edge rows using a temporary key in a local list.
            for r1 in REGIONS:
                for r2 in REGIONS:
                    if r2 < r1: continue
                    vals=[edge.get("value") for edge in edges if tuple(sorted((_region(edge.get("source","")),_region(edge.get("target",""))))) == tuple(sorted((r1,r2)))]
                    if vals: regional_rows.append({"branch":"average_primary","method":method,"band":band,"region_1":r1,"region_2":r2,"edge_count":len(vals),"mean_strength":_mean(vals),"median_strength":_median(vals),"value_definition":definition})
    return {"connectivity_global_summary.csv":global_rows,"connectivity_node_strength.csv":node_rows,"connectivity_regional_summary.csv":regional_rows,"connectivity_edges.csv":edge_rows}


def _coupling_tables(coupling: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
    pac_rows=[]; distributions=[]; pac_by_region={}; cpc_rows=[]; cpc_by_region={}
    for item in coupling.get("pac", []):
        low,high=item.get("phase_band_hz",(None,None)); amplitude_low,amplitude_high=item.get("amplitude_band_hz",(None,None))
        row={"channel":item.get("channel"),"coupling":item.get("coupling"),"phase_band_low_hz":low,"phase_band_high_hz":high,"amplitude_band_low_hz":amplitude_low,"amplitude_band_high_hz":amplitude_high,"modulation_index":item.get("modulation_index"),"mean_vector_length":item.get("mean_vector_length"),"analyzed_samples":item.get("analyzed_samples"),"analyzed_duration_sec":item.get("analyzed_duration_sec")}; pac_rows.append(row)
        pac_by_region.setdefault((_region(str(item.get("channel",""))), item.get("coupling")),[]).append(row)
        curve=item.get("phase_amplitude_binned_curve",{})
        for index,(degree,amplitude,relative) in enumerate(zip(curve.get("phase_bin_centers_degrees",[]),curve.get("mean_amplitude_uv",[]),curve.get("normalized_amplitude_distribution",[]))): distributions.append({"channel":item.get("channel"),"coupling":item.get("coupling"),"phase_bin_index":index,"phase_center_deg":degree,"mean_amplitude_uv":amplitude,"relative_amplitude":relative,"analyzed_samples":item.get("analyzed_samples")})
    for item in coupling.get("cross_phase_coupling",[]):
        low=item.get("low_phase_band_hz",(None,None)); high=item.get("high_phase_band_hz",(None,None)); row={"channel":item.get("channel"),"coupling":item.get("coupling"),"low_phase_band_low_hz":low[0],"low_phase_band_high_hz":low[1],"high_phase_band_low_hz":high[0],"high_phase_band_high_hz":high[1],"low_phase_multiplier":item.get("low_phase_multiplier"),"high_phase_multiplier":item.get("high_phase_multiplier"),"n_m_phase_locking_value":item.get("n_m_phase_locking_value"),"analyzed_samples":item.get("analyzed_samples"),"analyzed_duration_sec":item.get("analyzed_duration_sec")}; cpc_rows.append(row); cpc_by_region.setdefault((_region(str(item.get("channel",""))),item.get("coupling")),[]).append(row)
    pac_regional=[{"region":region,"coupling":coupling_name,"channel_count":len(values),"modulation_index_mean":_mean([x["modulation_index"] for x in values]),"modulation_index_median":_median([x["modulation_index"] for x in values]),"mean_vector_length_mean":_mean([x["mean_vector_length"] for x in values]),"mean_vector_length_median":_median([x["mean_vector_length"] for x in values])} for (region,coupling_name),values in pac_by_region.items()]
    cpc_regional=[{"region":region,"coupling":coupling_name,"channel_count":len(values),"n_m_phase_locking_value_mean":_mean([x["n_m_phase_locking_value"] for x in values]),"n_m_phase_locking_value_median":_median([x["n_m_phase_locking_value"] for x in values])} for (region,coupling_name),values in cpc_by_region.items()]
    return {"pac_channel_metrics.csv":pac_rows,"pac_phase_amplitude_distribution.csv":distributions,"pac_regional_summary.csv":pac_regional,"cross_phase_coupling_channel_metrics.csv":cpc_rows,"cross_phase_coupling_regional_summary.csv":cpc_regional}


def _microstate_tables(
    micro: Mapping[str, Any], analysis_sampling_rate_hz: Any = None
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, str]]:
    states=micro.get("state_names",[]); transition=micro.get("transition_matrix",{}); counts=transition.get("counts",[]); normalized=transition.get("row_normalized_percent",[])
    matrix=[]; count_rows=[]
    for i,state in enumerate(states):
        matrix.append({"from_state":state, **{f"to_{target}": ((normalized[i][j]/100) if i < len(normalized) and j < len(normalized[i]) else None) for j,target in enumerate(states)}})
        count_rows.append({"from_state":state, **{f"to_{target}": (counts[i][j] if i < len(counts) and j < len(counts[i]) else None) for j,target in enumerate(states)}})
    direct=[{"from_state":row.get("from_state"),"to_state":row.get("to_state"),"transition_count":row.get("count",row.get("transition_count")),"conditional_probability_percent":row.get("conditional_probability_percent",row.get("percent_of_outgoing"))} for row in micro.get("direct_transition_counts",{}).get("rows",micro.get("direct_transition_counts",[]))]
    segments=micro.get("segments",[]); coverage=list(micro.get("per_second_coverage",[])); duration=[]; partial={}
    sfreq=_safe_float(analysis_sampling_rate_hz)
    if segments and not coverage:
        coverage=_reconstruct_microstate_coverage(segments, states, sfreq)
    segment_starts=[]
    for segment in segments:
        start_sec=_safe_float(segment.get("start_sec"))
        start_sample=segment.get("start_sample")
        if start_sec is None and sfreq and isinstance(start_sample,(int,float)):
            start_sec=float(start_sample)/sfreq
        segment_starts.append((segment.get("state"),start_sec))
    occurrence_rows=[]
    occurrence_complete=bool(coverage) and bool(segments) and all(start is not None for _state,start in segment_starts)
    for sec,item in enumerate(coverage):
        start_sec=_safe_float(item.get("start_sec")); end_sec=_safe_float(item.get("end_sec"))
        window_start=float(sec) if start_sec is None else start_sec
        window_end=float(sec+1) if end_sec is None else end_sec
        row={"second":sec}
        for state in states:
            row[f"{state}_occurrences"]=(sum(1 for segment_state,segment_start in segment_starts if segment_state==state and segment_start is not None and window_start<=segment_start<window_end) if occurrence_complete else None)
            row[f"{state}_contribution_percent"]=(item.get("state_coverage_fraction",{}).get(state,0)*100)
        row["unlabeled_percent"]=0
        occurrence_rows.append((row,max(0.0,window_end-window_start)))
    if (coverage or segments) and not occurrence_complete:
        limitation="Occurrence counts cannot be reconstructed because persisted microstate segments lack usable timing or coverage windows."
        partial["microstate_per_second.csv"]=limitation
        partial["microstate_distribution_statistics.csv"]=limitation
    for state in states:
        selected=[x for x in segments if x.get("state")==state]; durations=[value for x in selected if (value:=_safe_float(x.get("duration_ms"))) is not None]; samples=[(x.get("end_sample_exclusive",0)-x.get("start_sample",0)) for x in selected if isinstance(x.get("start_sample"),int) and isinstance(x.get("end_sample_exclusive"),int)]
        cover=[x.get("state_coverage_fraction",{}).get(state,0)*100 for x in coverage]
        occurrence_rates=[row[f"{state}_occurrences"]/window_duration for row,window_duration in occurrence_rows if row[f"{state}_occurrences"] is not None and window_duration>0]
        longest_ms=max(durations) if durations else None
        longest_sec=(longest_ms/1000 if longest_ms is not None else (max(samples)/sfreq if samples and sfreq else None))
        duration.append({"state":state,"total_duration_sec":sum(durations)/1000,"segment_count":len(selected),"duration_mean_ms":_mean(durations),"duration_sd_ms":_std(durations),"longest_duration_samples":max(samples) if samples else None,"longest_duration_sec":longest_sec,"longest_duration_ms":longest_ms,"per_second_occurrence_mean_hz":_mean(occurrence_rates),"per_second_occurrence_sd_hz":_std(occurrence_rates),"per_second_contribution_mean_percent":_mean(cover),"per_second_contribution_sd_percent":_std(cover)})
    seg_rows=[]
    for index,item in enumerate(segments,1):
        start=item.get("start_sample"); end=item.get("end_sample_exclusive")
        seg_rows.append({"segment_index":index,"state_index":states.index(item.get("state")) if item.get("state") in states else None,"state":item.get("state"),"start_sample":start,"stop_sample_exclusive":end,"start_sec":item.get("start_sec"),"stop_sec":item.get("end_sec"),"duration_samples":(end-start) if isinstance(start,int) and isinstance(end,int) else None,"duration_sec":(_safe_float(item.get("duration_ms")) or 0)/1000,"duration_ms":item.get("duration_ms")})
    lagged=micro.get("lagged_information",{}).get("rows",[])
    tables={"microstate_transition_matrix.csv":matrix,"microstate_transition_counts.csv":count_rows,"microstate_direct_transitions.csv":direct,"microstate_distribution_statistics.csv":duration,"microstate_segments.csv":seg_rows,"microstate_per_second.csv":[row for row,_duration in occurrence_rows],"microstate_auto_information.csv":[{"lag_samples":x.get("lag_samples"),"lag_ms":x.get("actual_lag_ms",x.get("requested_lag_ms")),"auto_information_bits":x.get("mutual_information_bits")} for x in lagged]}
    return tables,partial


def _reconstruct_microstate_coverage(
    segments: Sequence[Mapping[str, Any]],
    states: Sequence[str],
    sfreq: float | None,
) -> list[dict[str, Any]]:
    timed_segments=[]
    for segment in segments:
        start=_safe_float(segment.get("start_sec"))
        stop=_safe_float(segment.get("end_sec"))
        if start is None and sfreq and isinstance(segment.get("start_sample"),(int,float)):
            start=float(segment["start_sample"])/sfreq
        if stop is None and sfreq and isinstance(segment.get("end_sample_exclusive"),(int,float)):
            stop=float(segment["end_sample_exclusive"])/sfreq
        if stop is None and start is not None:
            duration_ms=_safe_float(segment.get("duration_ms"))
            if duration_ms is not None:
                stop=start+duration_ms/1000
        if start is None or stop is None or stop <= start:
            return []
        timed_segments.append((segment.get("state"),start,stop))
    if not timed_segments:
        return []
    recording_stop=max(stop for _state,_start,stop in timed_segments)
    coverage=[]
    window_start=0.0
    while window_start < recording_stop:
        window_end=min(window_start+1.0,recording_stop)
        window_duration=window_end-window_start
        fractions={
            state: sum(
                max(0.0,min(stop,window_end)-max(start,window_start))
                for segment_state,start,stop in timed_segments
                if segment_state == state
            )/window_duration
            for state in states
        }
        coverage.append({"start_sec":window_start,"end_sec":window_end,"state_coverage_fraction":fractions})
        window_start=window_end
    return coverage


def _gfp_tables(
    gfp: Mapping[str, Any], quality_control: Mapping[str, Any]
) -> dict[str, list[dict[str, Any]]]:
    low,high=gfp.get("filter_hz",(None,None)); row={"filter_low_hz":low,"filter_high_hz":high,"gfp_definition":gfp.get("definition",{}).get("gfp"),"gmd_definition":gfp.get("definition",{}).get("gmd"),"gmd_polarity":"polarity-invariant"}
    for prefix, payload in (("continuous_gfp_uv",gfp.get("gfp_uv",{})),("peak_gfp_uv",gfp.get("gfp_peak_uv",{})),("successive_peak_gmd",gfp.get("successive_peak_gmd",{}))):
        for source,target in (("count","count"),("mean","mean"),("median","median"),("standard_deviation","standard_deviation"),("p95","p95"),("maximum","maximum")): row[f"{prefix}_{target}"]=payload.get(source)
    series=gfp.get("gfp_full_series",{}); values=series.get("values_uv",[])
    if values:
        source_time_mapping = quality_control.get("source_time_mapping")
        if source_time_mapping is None:
            source_time_mapping = _legacy_epoch_source_time_mapping(
                quality_control.get("epochs"), series.get("sampling_rate_hz"), len(values)
            )
        times=_retained_source_times(source_time_mapping, len(values))
    else:
        times=[]
    rows=[{"time_sec":time,"gfp_uv":value} for time,value in zip(times,values)]
    return {"gfp_gmd_summary.csv":[row],"gfp_timeseries.csv":rows}


def _other_tables(summary: Mapping[str, Any]) -> tuple[dict[str, list[dict[str, Any]]], dict[str, str]]:
    complexity=summary.get("complexity",{}); mse=[]
    for channel,curve in complexity.get("multiscale_entropy",{}).get("channel_curves",{}).items():
        for scale,value in zip(complexity.get("multiscale_entropy",{}).get("scales",[]),curve): mse.append({"channel":channel,"scale":scale,"coarse_grained_sample_count":(complexity.get("sample_count_per_channel",0)//scale if scale else None),"sample_entropy":value,"tolerance_uv":None,"embedding_dimension":None,"distance_metric":None,"complexity_index":None})
    spatial=summary.get("spatial_complexity",{}); spatial_rows=[{key:spatial.get(key) for key in ("method","channel_count","reference_rank_loss","maximum_effective_dimension","omega_effective_dimension","omega_normalized","eigenvalue_entropy_nats","matrix")} | {"unit":"dimensionless","frequency_range_hz":""}] if spatial else []
    aper=summary.get("aperiodic_spectrum",{}); parameter=[{"scope":"global","aperiodic_offset_log10_uv2_per_hz":aper.get("aperiodic_offset_log10_uv2_per_hz"),"aperiodic_exponent":aper.get("aperiodic_exponent"),"fit_mae_log10_power":aper.get("fit_mae_log10_power"),"fit_r_squared":aper.get("fit_r_squared"),"peak_count":len(aper.get("peaks",[]))}] if aper else []
    peaks=[]
    for index,item in enumerate(aper.get("peaks",[]),1):
        frequency=item.get("center_frequency_hz",item.get("center_frequency")); band=next((name for name,low,high in PEAK_BANDS if low<=(_safe_float(frequency) or -1)<high),"gamma")
        peaks.append({"scope":"global","peak_index":index,"band":band,"center_frequency_hz":frequency,"peak_power_above_aperiodic_log10":item.get("peak_power_above_aperiodic_log10",item.get("power")),"bandwidth_hz":item.get("bandwidth_hz",item.get("bandwidth"))})
    core=[]
    for key,value in summary.get("spectral",{}).get("markers",{}).items(): core.append({"metric":key,"status":"computed","value":value,"unit":"","channels":"","definition":"Persisted spectral marker","evidence":"analysis_summary.json","peak_psd_uv2_per_hz":""})
    return ({"multiscale_entropy.csv":mse,"spatial_complexity.csv":spatial_rows,"spectral_parameterization.csv":parameter,"spectral_peaks.csv":peaks,"qlanalyser_core_metrics.csv":core}, {"multiscale_entropy.csv":"Per-scale entropy is persisted, but historical tolerance, embedding dimension and distance metric were not retained.","spectral_parameterization.csv":"Only the global aperiodic fit is persisted; regional fits cannot be reconstructed.","spectral_peaks.csv":"Only global aperiodic peaks are persisted; regional peaks cannot be reconstructed.","band_peak_parameters.csv":"Persisted result provides global and per-channel rows; historical regional aggregation was not retained."})


def build_historical_compatibility_tables(summary: Mapping[str, Any]) -> HistoricalExportBundle:
    """Build historical CSV rows from persisted result data without EEG recalculation."""
    spectral=summary.get("spectral",{}); tables={}
    tables.update(_alpha_tables(spectral)); tables.update(_beta_tables(spectral)); tables.update(_spectral_tables(summary)); tables["hemispheric_asymmetry.csv"]=_asymmetry(spectral)
    tables.update(_connectivity_tables(summary.get("connectivity",{}))); tables.update(_coupling_tables(summary.get("coupling",{})))
    microstate_tables,microstate_partial=_microstate_tables(summary.get("microstates",{}),summary.get("analysis_data",{}).get("sampling_rate_hz")); tables.update(microstate_tables)
    tables.update(_gfp_tables(summary.get("gfp_gmd",{}),summary.get("quality_control",{})))
    other, partial=_other_tables(summary); tables.update(other); partial={**microstate_partial,**partial}
    peak=spectral.get("band_peak_parameters",{}); tables["band_peak_parameters.csv"]=[{"scope":"global",**row} for row in peak.get("global",[])]
    if frozenset(tables) != REQUIRED_HISTORICAL_TABLES:
        missing=sorted(REQUIRED_HISTORICAL_TABLES.difference(tables)); unexpected=sorted(set(tables).difference(REQUIRED_HISTORICAL_TABLES))
        raise RuntimeError(f"historical table contract mismatch: missing={missing}, unexpected={unexpected}")
    return HistoricalExportBundle(tables=tables, partial=partial, unavailable={"pac_public_backend_validation.csv":"Historical public-backend comparison statistics were not persisted in the analysis summary."})


def _temporary_sibling(path: Path) -> Path:
    return path.with_name(f".{path.name}.{uuid4().hex}.tmp")


def _write_csv_atomic(path: Path, header: Sequence[str], rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    temporary = _temporary_sibling(path)
    try:
        with temporary.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=header, extrasaction="raise")
            writer.writeheader()
            for row in rows:
                writer.writerow({
                    key: ("" if _safe_float(value) is None and isinstance(value, float) else value)
                    for key, value in row.items()
                })
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)

    payload = path.read_bytes()
    return {
        "header": list(header),
        "data_row_count": len(rows),
        "size_bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def _write_manifest_atomic(path: Path, manifest: Mapping[str, Any]) -> None:
    temporary = _temporary_sibling(path)
    try:
        temporary.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def write_historical_compatibility_tables(summary: Mapping[str, Any], destination: str | Path) -> HistoricalExportBundle:
    """Write the complete compatibility set and publish its manifest last."""
    bundle=build_historical_compatibility_tables(summary); headers=_table_headers(summary); metadata={}
    path=Path(destination); path.mkdir(parents=True,exist_ok=True)
    manifest_path=path/"export_manifest.json"; manifest_path.unlink(missing_ok=True)
    for filename in sorted(REQUIRED_HISTORICAL_TABLES):
        metadata[filename]=_write_csv_atomic(path/filename,headers[filename],bundle.tables[filename])
    for stale_path in sorted(path.glob("*.csv")):
        if stale_path.name not in REQUIRED_HISTORICAL_TABLES:
            stale_path.unlink()
    table_names=sorted(REQUIRED_HISTORICAL_TABLES)
    manifest={
        "status":"complete_with_declared_limitations" if bundle.partial or bundle.unavailable else "complete",
        "table_count":len(table_names),
        "required_tables":table_names,
        "tables":table_names,
        "table_metadata":metadata,
        "partial":bundle.partial,
        "unavailable":bundle.unavailable,
    }
    _write_manifest_atomic(manifest_path,manifest)
    return bundle
