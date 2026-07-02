from fastapi import APIRouter, Depends, HTTPException, UploadFile

from backend.models.eeg_file import EEGFileRead
from backend.models.governance import AccountRead
from backend.services import account_service, metadata_service, storage_service, waveform_chunk_service

router = APIRouter()

# Teaching-demo EEG recordings are public read-only.
_TEACHING_FILE_IDS = {"eeg_demo_teaching_oddball", "eeg_demo_epilepsy_high_amplitude"}


def _assert_file_visible(file_id: str, current: AccountRead) -> EEGFileRead:
    """Read endpoints remain open in V01 sandbox (owner checks on mutations only).
    Teaching files are exempt from all authz gates."""
    return storage_service.get_eeg_file(file_id)


@router.get("/eeg/files", response_model=list[EEGFileRead])
def list_eeg_files(current: AccountRead = Depends(account_service.require_current_account)) -> list[EEGFileRead]:
    return storage_service.list_eeg_files()


@router.post("/eeg/upload", response_model=EEGFileRead)
async def upload_eeg(
    project_id: str,
    subject_id: str | None = None,
    upload_authorization_confirmed: bool = False,
    upload_authorization_text: str | None = None,
    file: UploadFile | None = None,
    current: AccountRead = Depends(account_service.require_current_account),
) -> EEGFileRead:
    if not upload_authorization_confirmed:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "UPLOAD_AUTHORIZATION_REQUIRED",
                "message": "Please confirm that you have the right to upload this EEG file for research trial analysis.",
                "suggested_action": "Tick the upload authorization confirmation before uploading.",
            },
        )
    text = upload_authorization_text or "Uploader confirms authorization to upload this EEG file for research trial analysis."
    return await storage_service.create_eeg_file(
        project_id=project_id,
        subject_id=subject_id,
        upload=file,
        upload_authorization_confirmed=True,
        upload_authorization_text=text,
    )


@router.get("/eeg/files/{file_id}", response_model=EEGFileRead)
def get_eeg_file(file_id: str, current: AccountRead = Depends(account_service.require_current_account)) -> EEGFileRead:
    return _assert_file_visible(file_id, current)


@router.get("/eeg/files/{file_id}/metadata")
def get_eeg_metadata(file_id: str, current: AccountRead = Depends(account_service.require_current_account)) -> dict:
    eeg_file = _assert_file_visible(file_id, current)
    return metadata_service.extract_metadata(eeg_file)


@router.get("/eeg/files/{file_id}/waveform/chunk")
def get_eeg_waveform_chunk(
    file_id: str,
    start_sec: float = 0.0,
    duration_sec: float = 24.0,
    channels: str | None = None,
    channel_limit: int = 8,
    display_sfreq: float = 200.0,
    mode: str = "minmax",
    width_px: int = 1440,
    current: AccountRead = Depends(account_service.require_current_account),
) -> dict:
    eeg_file = _assert_file_visible(file_id, current)
    return waveform_chunk_service.get_waveform_chunk(
        eeg_file,
        start_sec=start_sec,
        duration_sec=duration_sec,
        channels=channels,
        channel_limit=channel_limit,
        display_sfreq=display_sfreq,
        mode=mode,
        width_px=width_px,
    )
