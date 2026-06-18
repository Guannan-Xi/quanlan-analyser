from pathlib import Path

from eeg_core.io.readers import read_raw, resolve_reader


SUPPORTED_FORMATS = {"edf", "bdf", "set", "vhdr", "cnt", "fif"}


def read_metadata(path: str | Path) -> dict:
    file_path = Path(path)
    suffix = file_path.suffix.lower().lstrip(".") or "unknown"
    stat = file_path.stat() if file_path.exists() else None
    base = {
        "filename": file_path.name,
        "format": suffix,
        "supported": suffix in SUPPORTED_FORMATS,
        "size_bytes": stat.st_size if stat else 0,
        "reader": resolve_reader(file_path),
    }
    if not file_path.exists() or not stat or stat.st_size <= 0:
        return {**base, "status": "failed", "error": "file_missing_or_empty"}
    if suffix not in SUPPORTED_FORMATS:
        return {**base, "status": "failed", "error": "unsupported_format"}

    try:
        raw = read_raw(file_path, preload=False)
        sfreq = float(raw.info["sfreq"])
        n_times = int(raw.n_times)
        annotations = [
            {
                "onset": float(item["onset"]),
                "duration": float(item["duration"]),
                "description": str(item["description"]),
            }
            for item in raw.annotations
        ]
        channel_types = raw.get_channel_types()
        return {
            **base,
            "status": "readable",
            "sampling_rate": sfreq,
            "channel_count": int(len(raw.ch_names)),
            "duration_sec": float(n_times / sfreq) if sfreq else None,
            "n_times": n_times,
            "channel_names": list(raw.ch_names),
            "channel_types": channel_types,
            "eeg_channel_count": int(sum(1 for ch in channel_types if ch == "eeg")),
            "annotation_count": int(len(raw.annotations)),
            "annotations_preview": annotations[:20],
            "highpass": float(raw.info.get("highpass") or 0),
            "lowpass": float(raw.info.get("lowpass") or 0),
            "meas_date": str(raw.info.get("meas_date")) if raw.info.get("meas_date") else None,
        }
    except Exception as exc:
        return {**base, "status": "failed", "error": str(exc)}
