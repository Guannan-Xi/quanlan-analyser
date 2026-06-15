from fastapi import APIRouter

router = APIRouter()


@router.get("/data/files")
def list_customer_files() -> list[dict]:
    return [
        {
            "id": "demo_bdf",
            "filename": "C64RS_390026040074_260531103644.bdf",
            "format": "bdf",
            "status": "metadata_ready",
        }
    ]


@router.patch("/data/files/{file_id}")
def update_customer_file(file_id: str, label: str | None = None) -> dict:
    return {"id": file_id, "label": label, "status": "updated"}


@router.delete("/data/files/{file_id}")
def delete_customer_file(file_id: str) -> dict:
    return {"id": file_id, "status": "delete_requested", "audit_required": True}

