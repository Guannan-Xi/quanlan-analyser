"""
Teaching Data Service for QLanalyser

Manages multiple teaching demo EEG scenarios for educational purposes.
Provides 6 different 10-minute teaching scenarios demonstrating various
sleep stages, epilepsy events, and artifact patterns.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional

from backend.models.eeg_file import EEGFileRead
from backend.models.project import ProjectRead
from backend.services import storage_service


ROOT = Path(__file__).resolve().parents[2]
TEACHING_DATA_ROOT = ROOT / "data" / "teaching"

# Teaching demo file configurations
TEACHING_DEMOS = {
    "demo_10min_full": {
        "file_id": "eeg_teaching_demo_10min_full",
        "filename": "teaching_demo_10min.edf",
        "name": "10分钟完整教学演示",
        "description": "包含Wake/NREM/REM/Seizure的完整10分钟演示数据",
        "duration": 600,
        "features": ["睡眠分期", "癫痫检测", "Sleep Spindles", "K-complexes", "眼动伪迹"],
        "scenarios": ["Wake (0-120s)", "NREM 1-2 (120-240s)", "NREM 3 (240-360s)", 
                     "REM (360-480s)", "Seizure (500-520s)"],
    },
    "demo_normal_sleep": {
        "file_id": "eeg_teaching_demo_normal_sleep",
        "filename": "teaching_demo_normal_sleep.edf",
        "name": "正常睡眠周期",
        "description": "展示完整正常睡眠周期的平滑过渡",
        "duration": 600,
        "features": ["睡眠分期", "睡眠结构", "阶段转换"],
        "scenarios": ["Wake -> NREM1-2 -> NREM3 -> NREM2 -> REM"],
    },
    "demo_epilepsy_multiple": {
        "file_id": "eeg_teaching_demo_epilepsy_multiple",
        "filename": "teaching_demo_epilepsy_multiple.edf",
        "name": "多次癫痫发作",
        "description": "包含3次独立癫痫发作事件及发作后抑制",
        "duration": 600,
        "features": ["癫痫检测", "高频尖波", "发作后抑制", "基线对比"],
        "scenarios": ["Seizure 1 (100-115s)", "Seizure 2 (300-320s)", "Seizure 3 (500-525s)"],
    },
    "demo_insomnia": {
        "file_id": "eeg_teaching_demo_insomnia",
        "filename": "teaching_demo_insomnia.edf",
        "name": "失眠模式",
        "description": "频繁觉醒的失眠模式演示",
        "duration": 600,
        "features": ["睡眠碎片化", "频繁觉醒", "入睡困难", "睡眠维持障碍"],
        "scenarios": ["多次觉醒", "浅睡眠为主", "体动增多"],
    },
    "demo_rem_behavior": {
        "file_id": "eeg_teaching_demo_rem_behavior",
        "filename": "teaching_demo_rem_behavior.edf",
        "name": "REM行为障碍",
        "description": "REM期异常高肌张力演示",
        "duration": 600,
        "features": ["REM睡眠", "异常高EMG", "REM行为障碍", "肌张力异常"],
        "scenarios": ["REM期高EMG", "运动伪迹", "肌肉麻痹缺失"],
    },
    "demo_mixed_artifacts": {
        "file_id": "eeg_teaching_demo_mixed_artifacts",
        "filename": "teaching_demo_mixed_artifacts.edf",
        "name": "各种伪迹",
        "description": "展示多种常见伪迹类型用于识别训练",
        "duration": 600,
        "features": ["眼电伪迹", "工频干扰", "电极脱落", "运动伪迹", "肌电干扰"],
        "scenarios": ["眨眼 (60-80s)", "50/60Hz噪声 (150-200s)", 
                     "电极脱落 (280s)", "运动伪迹 (400-420s)", "肌电 (500-550s)"],
    },
}

TEACHING_PROJECT_ID = "proj_teaching_demo_collection"


def list_teaching_demos() -> List[Dict]:
    """
    List all available teaching demo scenarios
    
    Returns
    -------
    demos : List[Dict]
        List of teaching demo metadata
    """
    demos = []
    for demo_id, config in TEACHING_DEMOS.items():
        demo_path = TEACHING_DATA_ROOT / config["filename"]
        status = "available" if demo_path.exists() else "not_generated"
        
        demo_info = {
            "id": demo_id,
            "file_id": config["file_id"],
            "name": config["name"],
            "description": config["description"],
            "duration": config["duration"],
            "features": config["features"],
            "scenarios": config["scenarios"],
            "status": status,
            "file_path": str(demo_path) if demo_path.exists() else None,
        }
        
        if demo_path.exists():
            demo_info["file_size_mb"] = demo_path.stat().st_size / (1024 * 1024)
            demo_info["sha256"] = _sha256(demo_path)
        
        demos.append(demo_info)
    
    return demos


def get_teaching_demo(demo_id: str) -> Optional[Dict]:
    """
    Get specific teaching demo information
    
    Parameters
    ----------
    demo_id : str
        Demo identifier (e.g., 'demo_10min_full')
        
    Returns
    -------
    demo : Dict or None
        Demo metadata or None if not found
    """
    if demo_id not in TEACHING_DEMOS:
        return None
    
    config = TEACHING_DEMOS[demo_id]
    demo_path = TEACHING_DATA_ROOT / config["filename"]
    
    if not demo_path.exists():
        return {
            "id": demo_id,
            "status": "not_generated",
            "message": f"Demo file not found: {config['filename']}",
        }
    
    return {
        "id": demo_id,
        "file_id": config["file_id"],
        "name": config["name"],
        "description": config["description"],
        "duration": config["duration"],
        "features": config["features"],
        "scenarios": config["scenarios"],
        "status": "available",
        "file_path": str(demo_path),
        "file_size_mb": demo_path.stat().st_size / (1024 * 1024),
        "sha256": _sha256(demo_path),
    }


def ensure_teaching_project() -> ProjectRead:
    """
    Ensure teaching demo project exists in storage
    
    Returns
    -------
    project : ProjectRead
        Teaching demo project
    """
    try:
        return storage_service.get_project(TEACHING_PROJECT_ID)
    except Exception:
        pass
    
    project = ProjectRead(
        id=TEACHING_PROJECT_ID,
        name="教学演示数据集合",
        description="包含6个不同场景的10分钟EEG教学演示数据，用于睡眠分期、癫痫检测和伪迹识别训练",
        research_type="teaching_demo_collection",
        owner_id="public-teaching",
        permission_policy={
            "teaching_mode": True,
            "protected_teaching_dataset": True,
            "archive_policy": "not_allowed",
            "delete_policy": "not_allowed",
            "rename_policy": "not_allowed",
        },
    )
    storage_service.upsert_project(project)
    return project


def register_teaching_demo(demo_id: str) -> Dict:
    """
    Register a teaching demo file in the storage system
    
    Parameters
    ----------
    demo_id : str
        Demo identifier
        
    Returns
    -------
    result : Dict
        Registration result with project and file info
    """
    if demo_id not in TEACHING_DEMOS:
        raise ValueError(f"Unknown teaching demo: {demo_id}")
    
    config = TEACHING_DEMOS[demo_id]
    demo_path = TEACHING_DATA_ROOT / config["filename"]
    
    if not demo_path.exists():
        raise FileNotFoundError(f"Demo file not found: {demo_path}")
    
    # Ensure project exists
    project = ensure_teaching_project()
    
    # Try to get existing file
    try:
        existing_file = storage_service.get_eeg_file(config["file_id"])
        return {
            "status": "already_registered",
            "project": project.model_dump(mode="json"),
            "file": existing_file.model_dump(mode="json"),
        }
    except Exception:
        pass
    
    # Register new file
    eeg_file = EEGFileRead(
        id=config["file_id"],
        project_id=TEACHING_PROJECT_ID,
        subject_id="teaching_demo_subject",
        original_filename=config["filename"],
        stored_path=demo_path,
        detected_format="edf",
        sampling_rate=250.0,
        channel_count=5,  # EEG3, EEG1, ACC_X, ACC_Y, ACC_Z
        duration_sec=float(config["duration"]),
        size_bytes=demo_path.stat().st_size,
        sha256=_sha256(demo_path),
        metadata_json={
            "demo": True,
            "teaching_mode": True,
            "protected_teaching_dataset": True,
            "demo_id": demo_id,
            "name": config["name"],
            "description": config["description"],
            "features": config["features"],
            "scenarios": config["scenarios"],
            "channels": ["EEG3", "EEG1", "ACC_X", "ACC_Y", "ACC_Z"],
            "delete_policy": "not_allowed",
            "rename_policy": "not_allowed",
        },
        permission_policy={
            "teaching_mode": True,
            "protected_teaching_dataset": True,
            "delete_policy": "not_allowed",
            "rename_policy": "not_allowed",
        },
        retention_policy="protected_teaching_demo",
        status="metadata_ready",
        upload_status="teaching_demo_fixture",
    )
    
    storage_service.register_eeg_file(eeg_file)
    
    return {
        "status": "registered",
        "project": project.model_dump(mode="json"),
        "file": eeg_file.model_dump(mode="json"),
    }


def register_all_teaching_demos() -> Dict:
    """
    Register all available teaching demos
    
    Returns
    -------
    result : Dict
        Registration results for all demos
    """
    project = ensure_teaching_project()
    
    results = {
        "project": project.model_dump(mode="json"),
        "demos": [],
        "summary": {
            "total": len(TEACHING_DEMOS),
            "registered": 0,
            "already_registered": 0,
            "missing": 0,
            "errors": 0,
        }
    }
    
    for demo_id in TEACHING_DEMOS.keys():
        try:
            result = register_teaching_demo(demo_id)
            results["demos"].append({
                "demo_id": demo_id,
                "status": result["status"],
                "file_id": result["file"]["id"],
            })
            
            if result["status"] == "registered":
                results["summary"]["registered"] += 1
            elif result["status"] == "already_registered":
                results["summary"]["already_registered"] += 1
                
        except FileNotFoundError as e:
            results["demos"].append({
                "demo_id": demo_id,
                "status": "missing",
                "error": str(e),
            })
            results["summary"]["missing"] += 1
            
        except Exception as e:
            results["demos"].append({
                "demo_id": demo_id,
                "status": "error",
                "error": str(e),
            })
            results["summary"]["errors"] += 1
    
    return results


def get_teaching_demo_path(demo_id: str) -> Path:
    """
    Get file path for a teaching demo
    
    Parameters
    ----------
    demo_id : str
        Demo identifier
        
    Returns
    -------
    path : Path
        Path to demo file
        
    Raises
    ------
    ValueError
        If demo_id is unknown
    FileNotFoundError
        If demo file doesn't exist
    """
    if demo_id not in TEACHING_DEMOS:
        raise ValueError(f"Unknown teaching demo: {demo_id}")
    
    demo_path = TEACHING_DATA_ROOT / TEACHING_DEMOS[demo_id]["filename"]
    
    if not demo_path.exists():
        raise FileNotFoundError(f"Demo file not found: {demo_path}")
    
    return demo_path


def _sha256(path: Path) -> str:
    """Calculate SHA256 hash of a file"""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def generate_teaching_demos() -> Dict:
    """
    Generate all teaching demo files if not already present
    
    Returns
    -------
    result : Dict
        Generation result
    """
    import subprocess
    import sys
    
    TEACHING_DATA_ROOT.mkdir(parents=True, exist_ok=True)
    
    # Check which demos need generation
    missing_demos = []
    for demo_id, config in TEACHING_DEMOS.items():
        demo_path = TEACHING_DATA_ROOT / config["filename"]
        if not demo_path.exists():
            missing_demos.append(demo_id)
    
    if not missing_demos:
        return {
            "status": "all_present",
            "message": "All teaching demos already exist",
            "demos": list(TEACHING_DEMOS.keys()),
        }
    
    # Run generation scripts
    script_dir = ROOT / "scripts"
    
    try:
        # Generate main demo
        if any(TEACHING_DEMOS[d]["filename"] == "teaching_demo_10min.edf" for d in missing_demos):
            result = subprocess.run(
                [sys.executable, str(script_dir / "generate_teaching_demo_10min.py")],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode != 0:
                raise RuntimeError(f"Failed to generate main demo: {result.stderr}")
        
        # Generate additional variants
        if len(missing_demos) > 1:
            result = subprocess.run(
                [sys.executable, str(script_dir / "generate_multiple_teaching_demos.py")],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode != 0:
                raise RuntimeError(f"Failed to generate demo variants: {result.stderr}")
        
        return {
            "status": "generated",
            "message": f"Generated {len(missing_demos)} teaching demos",
            "generated": missing_demos,
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error generating teaching demos: {str(e)}",
            "missing": missing_demos,
        }
