"""
Teaching Data API Router

Provides endpoints for accessing teaching demonstration EEG data.
Supports listing, retrieving, and registering teaching demos.
"""

from typing import List, Dict, Optional
from fastapi import APIRouter, HTTPException, Path as PathParam
from pydantic import BaseModel, Field

from backend.services import teaching_data_service


router = APIRouter()


class TeachingDemoInfo(BaseModel):
    """Teaching demo metadata response"""
    id: str
    file_id: str
    name: str
    description: str
    duration: int
    features: List[str]
    scenarios: List[str]
    status: str
    file_path: Optional[str] = None
    file_size_mb: Optional[float] = None
    sha256: Optional[str] = None


class TeachingDemoListResponse(BaseModel):
    """Response for listing teaching demos"""
    demos: List[Dict]
    summary: Dict[str, int]


@router.get("/teaching/demos", summary="List all teaching demos")
def list_teaching_demos() -> TeachingDemoListResponse:
    """
    List all available teaching demonstration scenarios
    
    Returns information about 6 different 10-minute teaching demos:
    - demo_10min_full: Complete demonstration with all features
    - demo_normal_sleep: Normal sleep cycle progression
    - demo_epilepsy_multiple: Multiple seizure events
    - demo_insomnia: Insomnia pattern with frequent awakenings
    - demo_rem_behavior: REM behavior disorder
    - demo_mixed_artifacts: Various artifact types
    """
    demos = teaching_data_service.list_teaching_demos()
    
    summary = {
        "total": len(demos),
        "available": sum(1 for d in demos if d["status"] == "available"),
        "not_generated": sum(1 for d in demos if d["status"] == "not_generated"),
    }
    
    return TeachingDemoListResponse(demos=demos, summary=summary)


@router.get("/teaching/demos/{demo_id}", summary="Get specific teaching demo")
def get_teaching_demo(
    demo_id: str = PathParam(..., description="Demo identifier (e.g., 'demo_10min_full')")
) -> Dict:
    """
    Get detailed information about a specific teaching demo
    
    Parameters
    ----------
    demo_id : str
        Demo identifier:
        - demo_10min_full
        - demo_normal_sleep
        - demo_epilepsy_multiple
        - demo_insomnia
        - demo_rem_behavior
        - demo_mixed_artifacts
    """
    demo = teaching_data_service.get_teaching_demo(demo_id)
    
    if demo is None:
        raise HTTPException(
            status_code=404,
            detail=f"Teaching demo not found: {demo_id}"
        )
    
    if demo.get("status") == "not_generated":
        raise HTTPException(
            status_code=404,
            detail=demo.get("message", "Demo file not found")
        )
    
    return demo


@router.post("/teaching/register/{demo_id}", summary="Register teaching demo in storage")
def register_teaching_demo(
    demo_id: str = PathParam(..., description="Demo identifier to register")
) -> Dict:
    """
    Register a teaching demo file in the storage system
    
    This creates project and file records so the demo can be used
    for analysis tasks.
    """
    try:
        result = teaching_data_service.register_teaching_demo(demo_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


@router.post("/teaching/register-all", summary="Register all teaching demos")
def register_all_teaching_demos() -> Dict:
    """
    Register all available teaching demos in the storage system
    
    This is useful for initial setup or after generating new demos.
    """
    try:
        result = teaching_data_service.register_all_teaching_demos()
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to register teaching demos: {str(e)}"
        )


@router.post("/teaching/generate", summary="Generate teaching demo files")
def generate_teaching_demos() -> Dict:
    """
    Generate teaching demo EEG files if they don't exist
    
    This runs the generation scripts to create all 6 teaching demo files.
    Takes approximately 1-2 minutes to complete.
    
    Note: Requires MNE-Python to be installed in the environment.
    """
    try:
        result = teaching_data_service.generate_teaching_demos()
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate teaching demos: {str(e)}"
        )


@router.get("/teaching/project", summary="Get or create teaching project")
def ensure_teaching_project() -> Dict:
    """
    Ensure the teaching demo project exists in storage
    
    Returns the teaching demo project metadata.
    """
    try:
        project = teaching_data_service.ensure_teaching_project()
        return {
            "status": "ready",
            "project": project.model_dump(mode="json"),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to ensure teaching project: {str(e)}"
        )


@router.get("/teaching/demos/{demo_id}/path", summary="Get demo file path")
def get_teaching_demo_path(
    demo_id: str = PathParam(..., description="Demo identifier")
) -> Dict:
    """
    Get the file system path for a teaching demo
    
    Used internally for loading demo files.
    """
    try:
        path = teaching_data_service.get_teaching_demo_path(demo_id)
        return {
            "demo_id": demo_id,
            "path": str(path),
            "exists": path.exists(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/teaching/status", summary="Get teaching data system status")
def get_teaching_status() -> Dict:
    """
    Get overall status of the teaching data system
    
    Returns summary of available demos, registered demos, and project status.
    """
    demos = teaching_data_service.list_teaching_demos()
    
    try:
        project = teaching_data_service.ensure_teaching_project()
        project_status = "ready"
    except Exception as e:
        project_status = f"error: {str(e)}"
    
    return {
        "status": "operational",
        "project_status": project_status,
        "demos": {
            "total": len(demos),
            "available": sum(1 for d in demos if d["status"] == "available"),
            "not_generated": sum(1 for d in demos if d["status"] == "not_generated"),
        },
        "data_directory": str(teaching_data_service.TEACHING_DATA_ROOT),
    }
