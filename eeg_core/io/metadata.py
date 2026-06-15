from pathlib import Path


SUPPORTED_FORMATS = {"edf", "bdf", "set", "vhdr", "cnt", "fif"}


def read_metadata(path: str | Path) -> dict:
    file_path = Path(path)
    suffix = file_path.suffix.lower().lstrip(".") or "unknown"
    stat = file_path.stat() if file_path.exists() else None
    if suffix in {"edf", "bdf"} and file_path.exists():
        mne_metadata = _read_with_mne(file_path, suffix, stat.st_size if stat else 0)
        if mne_metadata:
            return mne_metadata

    if suffix in {"edf", "bdf"} and file_path.exists():
        return _read_edf_bdf_header(file_path, suffix, stat.st_size if stat else 0)

    return {
        "filename": file_path.name,
        "format": suffix,
        "supported": suffix in SUPPORTED_FORMATS,
        "size_bytes": stat.st_size if stat else 0,
        "sampling_rate": None,
        "channel_count": None,
        "duration_sec": None,
        "reader": "placeholder",
        "note": "MNE-based metadata extraction will replace this placeholder.",
    }


def _read_with_mne(file_path: Path, suffix: str, size_bytes: int) -> dict | None:
    try:
        import mne

        if suffix == "bdf":
            raw = mne.io.read_raw_bdf(file_path, preload=False, verbose="ERROR")
        elif suffix == "edf":
            raw = mne.io.read_raw_edf(file_path, preload=False, verbose="ERROR")
        else:
            return None
    except Exception:
        return None

    return {
        "filename": file_path.name,
        "format": suffix,
        "supported": suffix in SUPPORTED_FORMATS,
        "size_bytes": size_bytes,
        "sampling_rate": float(raw.info["sfreq"]),
        "channel_count": int(len(raw.ch_names)),
        "duration_sec": float(raw.n_times / raw.info["sfreq"]) if raw.info["sfreq"] else None,
        "n_times": int(raw.n_times),
        "annotations_count": int(len(raw.annotations)),
        "channel_labels_preview": raw.ch_names[:12],
        "reader": "mne",
        "mne_version": mne.__version__,
        "note": "MNE metadata read with preload=False; signal data was not loaded.",
    }


def _read_edf_bdf_header(file_path: Path, suffix: str, size_bytes: int) -> dict:
    with file_path.open("rb") as handle:
        fixed_header = handle.read(256)
        header_bytes = _parse_int(fixed_header[184:192])
        record_count = _parse_int(fixed_header[236:244])
        record_duration = _parse_float(fixed_header[244:252])
        signal_count = _parse_int(fixed_header[252:256])
        signal_header = handle.read(max(0, header_bytes - 256))

    labels = [
        signal_header[index * 16 : (index + 1) * 16].decode("latin1", "ignore").strip()
        for index in range(signal_count)
    ]
    samples_offset = signal_count * (16 + 80 + 8 + 8 + 8 + 8 + 8 + 80)
    samples_per_record = []
    for index in range(signal_count):
        raw = signal_header[samples_offset + index * 8 : samples_offset + (index + 1) * 8]
        samples_per_record.append(_parse_int(raw))

    sampling_rates = [
        sample_count / record_duration if record_duration else None
        for sample_count in samples_per_record
    ]
    primary_sampling_rate = next((rate for rate in sampling_rates if rate), None)
    duration_sec = record_count * record_duration if record_count > 0 and record_duration else None

    return {
        "filename": file_path.name,
        "format": suffix,
        "supported": suffix in SUPPORTED_FORMATS,
        "size_bytes": size_bytes,
        "sampling_rate": primary_sampling_rate,
        "channel_count": signal_count,
        "duration_sec": duration_sec,
        "header_bytes": header_bytes,
        "record_count": record_count,
        "record_duration_sec": record_duration,
        "channel_labels_preview": labels[:12],
        "samples_per_record_preview": samples_per_record[:12],
        "sampling_rates_preview": sampling_rates[:12],
        "reader": "edf_bdf_header",
        "note": "Header-only metadata read; signal data was not loaded.",
    }


def _parse_int(raw: bytes) -> int:
    value = raw.decode("ascii", "ignore").strip()
    return int(value or 0)


def _parse_float(raw: bytes) -> float:
    value = raw.decode("ascii", "ignore").strip()
    return float(value or 0)
