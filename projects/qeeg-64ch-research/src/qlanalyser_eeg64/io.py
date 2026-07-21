"""Input and provenance helpers for supported EEG recordings."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import mne


REFERENCE_CHANNELS = frozenset({"M1", "M2"})


def read_raw(path: str | Path, *, preload: bool = True):
    path = Path(path)
    readers = {".bdf": mne.io.read_raw_bdf, ".edf": mne.io.read_raw_edf, ".set": mne.io.read_raw_eeglab, ".vhdr": mne.io.read_raw_brainvision, ".fif": mne.io.read_raw_fif, ".cnt": mne.io.read_raw_cnt}
    try:
        return readers[path.suffix.lower()](path, preload=preload, verbose="ERROR")
    except KeyError as exc:
        raise ValueError(f"Unsupported EEG input format: {path.suffix}") from exc


def prepare_analysis_raw(raw):
    """Select scalp EEG and assign standard 10-10 locations when available.

    The recovered report contract treats M1/M2 as mastoid references rather
    than scalp analysis channels. Location assignment is name based and its
    result is returned for provenance instead of being implicit in plotting.
    """
    source_channels = list(raw.ch_names)
    excluded = [name for name in source_channels if name.upper() in REFERENCE_CHANNELS]
    analysis = raw.copy().pick("eeg").drop_channels(excluded)
    montage = mne.channels.make_standard_montage("standard_1005")
    analysis.set_montage(montage, match_case=False, on_missing="ignore", verbose="ERROR")
    positions = analysis._get_channel_positions()
    positioned = [name for name, position in zip(analysis.ch_names, positions) if bool(position.any())]
    return analysis, {
        "source_eeg_channels": source_channels,
        "excluded_reference_channels": excluded,
        "analysis_eeg_channels": list(analysis.ch_names),
        "montage": "standard_1005_name_matched",
        "channels_with_positions": positioned,
        "channels_without_positions": [name for name in analysis.ch_names if name not in positioned],
    }


def file_sha256(path: str | Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
