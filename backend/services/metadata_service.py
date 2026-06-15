from backend.models.eeg_file import EEGFileRead
from eeg_core.io.metadata import read_metadata


def extract_metadata(eeg_file: EEGFileRead) -> dict:
    metadata = read_metadata(eeg_file.stored_path)
    eeg_file.metadata_json.update(metadata)
    eeg_file.detected_format = metadata["format"]
    eeg_file.sampling_rate = metadata.get("sampling_rate")
    eeg_file.channel_count = metadata.get("channel_count")
    eeg_file.duration_sec = metadata.get("duration_sec")
    return eeg_file.metadata_json

