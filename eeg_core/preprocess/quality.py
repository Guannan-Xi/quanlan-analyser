from pathlib import Path


def summarize_quality(path, parameters: dict) -> dict:
    file_path = Path(path)
    return {
        "filename": file_path.name,
        "checks": ["file_present", "format_supported", "metadata_readable"],
        "status": "pending_mne_qc",
        "parameters": parameters,
    }

