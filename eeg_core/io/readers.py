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
    return "unsupported"

