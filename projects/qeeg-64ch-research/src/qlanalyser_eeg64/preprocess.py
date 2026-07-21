"""Deterministic full-recording preprocessing used by every analysis module."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class PreprocessConfig:
    notch_freq_hz: float | None = 50.0
    l_freq_hz: float | None = 0.5
    h_freq_hz: float | None = 45.0
    resample_hz: float | None = 250.0
    average_reference: bool = True
    bad_channels: tuple[str, ...] = field(default_factory=tuple)


def preprocess_full_recording(raw, config: PreprocessConfig | None = None):
    """Apply the historical preprocessing baseline to the complete recording."""
    config = config or PreprocessConfig()
    processed = raw.copy().load_data().pick("eeg")
    nyquist = float(processed.info["sfreq"]) / 2
    trace = []
    known_bads = sorted(set(config.bad_channels) & set(processed.ch_names))
    if known_bads:
        processed.info["bads"] = known_bads
    trace.append({"step": "mark_bad_channels", "channels": known_bads})
    if config.notch_freq_hz is not None:
        if not 0 < config.notch_freq_hz < nyquist:
            raise ValueError("notch frequency must fall below Nyquist")
        processed.notch_filter(config.notch_freq_hz, verbose="ERROR")
        trace.append({"step": "notch_filter", "frequency_hz": config.notch_freq_hz})
    if config.l_freq_hz is not None or config.h_freq_hz is not None:
        processed.filter(config.l_freq_hz, config.h_freq_hz, verbose="ERROR")
        trace.append({"step": "bandpass_filter", "l_freq_hz": config.l_freq_hz, "h_freq_hz": config.h_freq_hz})
    if config.average_reference:
        processed.set_eeg_reference("average", projection=False, verbose="ERROR")
        trace.append({"step": "average_reference"})
    if config.resample_hz is not None and config.resample_hz != processed.info["sfreq"]:
        if not 0 < config.resample_hz <= processed.info["sfreq"]:
            raise ValueError("resample frequency must be positive and no greater than source rate")
        before = float(processed.info["sfreq"])
        processed.resample(config.resample_hz, verbose="ERROR")
        trace.append({"step": "resample", "from_hz": before, "to_hz": config.resample_hz})
    return processed, {"parameters": asdict(config), "steps": trace}
