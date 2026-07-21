from pathlib import Path


def resolve_reader(path: str | Path) -> str:
    suffix = Path(path).suffix.lower().lstrip(".")
    if suffix in {"edf", "bdf"}:
        return "mne.io.read_raw_edf"
    if suffix == "set":
        return "mne.io.read_raw_eeglab"
    if suffix == "vhdr":
        return "mne.io.read_raw_brainvision"
    if suffix == "fif":
        return "mne.io.read_raw_fif"
    if suffix == "cnt":
        return "mne.io.read_raw_cnt"
    return "unsupported"


def read_raw(path: str | Path, *, preload: bool = False):
    """Read an EEG file with MNE using a format-specific reader.

    Production rule: unsupported or unreadable files raise a clear exception.
    Callers should surface the error instead of manufacturing placeholder outputs.
    """
    file_path = Path(path)
    if not file_path.exists() or file_path.stat().st_size <= 0:
        raise FileNotFoundError(f"EEG file is missing or empty: {file_path}")

    reader = resolve_reader(file_path)
    if reader == "unsupported":
        raise ValueError(f"Unsupported EEG format: {file_path.suffix or 'unknown'}")

    try:
        import mne
    except Exception as exc:  # pragma: no cover - environment dependent
        raise RuntimeError("MNE-Python is required for EEG analysis") from exc

    suffix = file_path.suffix.lower().lstrip(".")
    common = {"preload": preload, "verbose": "ERROR"}
    if suffix in {"edf", "bdf"}:
        return mne.io.read_raw_edf(file_path, **common)
    if suffix == "set":
        return mne.io.read_raw_eeglab(file_path, **common)
    if suffix == "vhdr":
        return mne.io.read_raw_brainvision(file_path, **common)
    if suffix == "fif":
        return mne.io.read_raw_fif(file_path, **common)
    if suffix == "cnt":
        return mne.io.read_raw_cnt(file_path, **common)
    raise ValueError(f"Unsupported EEG format: {suffix}")
