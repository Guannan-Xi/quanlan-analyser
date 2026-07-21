"""
癫痫分析阶段发布限制验证模块

用途：在任务创建时验证文件是否满足当前阶段的限制
作者：ZCode Agent
日期：2026-07-03
版本：v1.0-phase1
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from fastapi import HTTPException

logger = logging.getLogger(__name__)


# ============================================================================
# 阶段发布配置
# ============================================================================

@dataclass
class PhaseConfig:
    """阶段配置数据类"""
    phase: int
    name: str
    max_duration_h: float
    max_size_mb: float
    max_channels: int
    release_date: str
    enabled: bool


# 阶段配置表（集中管理，便于后续移除）
PHASE_CONFIGS = {
    1: PhaseConfig(
        phase=1,
        name="phase_1_regular_data",
        max_duration_h=10.0,
        max_size_mb=500,
        max_channels=64,
        release_date="2026-07-03",
        enabled=True
    ),
    2: PhaseConfig(
        phase=2,
        name="phase_2_medium_data",
        max_duration_h=24.0,
        max_size_mb=1000,
        max_channels=64,
        release_date="2026-07-17",
        enabled=False
    ),
    3: PhaseConfig(
        phase=3,
        name="phase_3_extended_data",
        max_duration_h=48.0,
        max_size_mb=2000,
        max_channels=128,
        release_date="2026-08-03",
        enabled=False
    ),
}

# 当前活跃阶段（Feature Flag，便于A/B测试）
CURRENT_PHASE = 1

# 全局开关（紧急情况下可快速禁用所有限制）
PHASE_VALIDATION_ENABLED = True


# ============================================================================
# 验证逻辑
# ============================================================================

@dataclass
class ValidationResult:
    """验证结果数据类"""
    allowed: bool
    phase: int
    file_size_mb: float
    duration_h: float
    channel_count: int
    rejection_reason: str | None = None
    rejection_code: str | None = None
    expected_support_phase: int | None = None
    expected_support_date: str | None = None
    workaround: str | None = None


def get_current_phase_config() -> PhaseConfig:
    """获取当前活跃阶段配置"""
    return PHASE_CONFIGS[CURRENT_PHASE]


def find_support_phase(duration_h: float, size_mb: float, channel_count: int) -> PhaseConfig | None:
    """查找能够支持给定数据特征的最早阶段"""
    for phase_num in sorted(PHASE_CONFIGS.keys()):
        config = PHASE_CONFIGS[phase_num]
        if (duration_h <= config.max_duration_h and 
            size_mb <= config.max_size_mb and 
            channel_count <= config.max_channels):
            return config
    return None


def validate_epilepsy_file_constraints(
    file_path: Path,
    raw_reader_func: Any,
    *,
    enforce: bool = True
) -> ValidationResult:
    """
    验证EEG文件是否满足当前阶段限制
    
    Args:
        file_path: EEG文件路径
        raw_reader_func: MNE读取函数（通常是 read_raw）
        enforce: 是否在不满足时抛出异常（False时仅返回结果）
    
    Returns:
        ValidationResult: 验证结果对象
    
    Raises:
        HTTPException: 当enforce=True且验证失败时
    
    Example:
        >>> from eeg_core.io.readers import read_raw
        >>> result = validate_epilepsy_file_constraints(
        ...     Path("data.edf"),
        ...     read_raw,
        ...     enforce=True
        ... )
    """
    # 全局开关检查
    if not PHASE_VALIDATION_ENABLED:
        logger.warning("Phase validation is globally disabled")
        return ValidationResult(
            allowed=True,
            phase=CURRENT_PHASE,
            file_size_mb=0.0,
            duration_h=0.0,
            channel_count=0
        )
    
    current_config = get_current_phase_config()
    
    # 1. 文件大小检查
    if not file_path.exists():
        if enforce:
            raise HTTPException(
                status_code=410,
                detail="EEG file not found on disk"
            )
        return ValidationResult(
            allowed=False,
            phase=CURRENT_PHASE,
            file_size_mb=0.0,
            duration_h=0.0,
            channel_count=0,
            rejection_code="FileNotFound"
        )
    
    size_bytes = file_path.stat().st_size
    size_mb = size_bytes / (1024 * 1024)
    
    # 2. 读取文件元数据（不加载数据到内存）
    try:
        raw = raw_reader_func(file_path, preload=False)
    except Exception as e:
        logger.error(f"Failed to read EEG file {file_path}: {e}")
        if enforce:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "EEGFileReadError",
                    "message": f"Unable to read EEG file: {str(e)}"
                }
            )
        return ValidationResult(
            allowed=False,
            phase=CURRENT_PHASE,
            file_size_mb=size_mb,
            duration_h=0.0,
            channel_count=0,
            rejection_code="EEGFileReadError"
        )
    
    # 3. 计算时长和通道数
    sfreq = float(raw.info.get("sfreq", 0))
    duration_sec = float(raw.n_times / sfreq) if sfreq > 0 else 0.0
    duration_h = duration_sec / 3600.0
    channel_count = len(raw.ch_names)
    
    # 4. 验证文件大小
    if size_mb > current_config.max_size_mb:
        support_phase = find_support_phase(duration_h, size_mb, channel_count)
        
        detail = {
            "code": "EpilepsyFileTooLarge",
            "message": f"文件大小 {size_mb:.1f}MB 超过当前版本限制 {current_config.max_size_mb}MB",
            "file_size_mb": round(size_mb, 1),
            "current_phase": {
                "phase": current_config.phase,
                "name": current_config.name,
                "max_size_mb": current_config.max_size_mb,
                "release_date": current_config.release_date
            }
        }
        
        if support_phase:
            detail["expected_support"] = {
                "phase": support_phase.phase,
                "name": support_phase.name,
                "expected_date": support_phase.release_date,
                "max_size_mb": support_phase.max_size_mb
            }
            detail["workaround"] = "建议等待后续版本发布，或将数据分割为多个片段进行分析"
        else:
            detail["workaround"] = "此文件超过所有规划阶段的限制，请联系技术支持"
        
        if enforce:
            raise HTTPException(status_code=422, detail=detail)
        
        return ValidationResult(
            allowed=False,
            phase=CURRENT_PHASE,
            file_size_mb=size_mb,
            duration_h=duration_h,
            channel_count=channel_count,
            rejection_reason=detail["message"],
            rejection_code="EpilepsyFileTooLarge",
            expected_support_phase=support_phase.phase if support_phase else None,
            expected_support_date=support_phase.release_date if support_phase else None,
            workaround=detail["workaround"]
        )
    
    # 5. 验证数据时长
    if duration_h > current_config.max_duration_h:
        support_phase = find_support_phase(duration_h, size_mb, channel_count)
        
        detail = {
            "code": "EpilepsyDurationTooLong",
            "message": f"数据时长 {duration_h:.1f}h 超过当前版本限制 {current_config.max_duration_h}h",
            "file_duration_h": round(duration_h, 1),
            "current_phase": {
                "phase": current_config.phase,
                "name": current_config.name,
                "max_duration_h": current_config.max_duration_h,
                "release_date": current_config.release_date
            }
        }
        
        if support_phase:
            detail["expected_support"] = {
                "phase": support_phase.phase,
                "name": support_phase.name,
                "expected_date": support_phase.release_date,
                "max_duration_h": support_phase.max_duration_h
            }
            detail["workaround"] = "建议等待后续版本发布，或按时段分析数据"
        else:
            detail["workaround"] = "此数据时长超过所有规划阶段的限制，请联系技术支持"
        
        if enforce:
            raise HTTPException(status_code=422, detail=detail)
        
        return ValidationResult(
            allowed=False,
            phase=CURRENT_PHASE,
            file_size_mb=size_mb,
            duration_h=duration_h,
            channel_count=channel_count,
            rejection_reason=detail["message"],
            rejection_code="EpilepsyDurationTooLong",
            expected_support_phase=support_phase.phase if support_phase else None,
            expected_support_date=support_phase.release_date if support_phase else None,
            workaround=detail["workaround"]
        )
    
    # 6. 验证通道数
    if channel_count > current_config.max_channels:
        detail = {
            "code": "EpilepsyTooManyChannels",
            "message": f"通道数 {channel_count} 超过当前版本限制 {current_config.max_channels}",
            "channel_count": channel_count,
            "current_phase": {
                "phase": current_config.phase,
                "name": current_config.name,
                "max_channels": current_config.max_channels,
                "release_date": current_config.release_date
            },
            "workaround": "建议选择部分通道进行分析，或等待后续版本支持"
        }
        
        if enforce:
            raise HTTPException(status_code=422, detail=detail)
        
        return ValidationResult(
            allowed=False,
            phase=CURRENT_PHASE,
            file_size_mb=size_mb,
            duration_h=duration_h,
            channel_count=channel_count,
            rejection_reason=detail["message"],
            rejection_code="EpilepsyTooManyChannels",
            workaround=detail["workaround"]
        )
    
    # 7. 验证通过
    logger.info(
        f"Epilepsy file validation passed: "
        f"size={size_mb:.1f}MB, duration={duration_h:.1f}h, channels={channel_count}, "
        f"phase={current_config.phase}"
    )
    
    return ValidationResult(
        allowed=True,
        phase=CURRENT_PHASE,
        file_size_mb=size_mb,
        duration_h=duration_h,
        channel_count=channel_count
    )


# ============================================================================
# 集成辅助函数
# ============================================================================

def validate_by_file_id(
    file_id: str,
    storage_service: Any,
    raw_reader_func: Any,
    *,
    enforce: bool = True
) -> ValidationResult:
    """
    通过文件ID验证（适配现有API）
    
    Args:
        file_id: 文件ID
        storage_service: 存储服务实例
        raw_reader_func: MNE读取函数
        enforce: 是否在不满足时抛出异常
    
    Returns:
        ValidationResult: 验证结果
    
    Example:
        >>> from backend.services import storage_service
        >>> from eeg_core.io.readers import read_raw
        >>> result = validate_by_file_id(
        ...     "file_abc123",
        ...     storage_service,
        ...     read_raw,
        ...     enforce=True
        ... )
    """
    eeg_file = storage_service.get_eeg_file(file_id)
    file_path = Path(eeg_file.stored_path)
    return validate_epilepsy_file_constraints(file_path, raw_reader_func, enforce=enforce)


def get_phase_roadmap() -> dict[str, Any]:
    """
    获取阶段发布路线图（用于前端展示）
    
    Returns:
        包含所有阶段信息的字典
    
    Example:
        >>> roadmap = get_phase_roadmap()
        >>> print(roadmap["current_phase"])
        1
        >>> print(roadmap["phases"][1]["max_duration_h"])
        10.0
    """
    return {
        "current_phase": CURRENT_PHASE,
        "validation_enabled": PHASE_VALIDATION_ENABLED,
        "phases": {
            phase_num: {
                "phase": config.phase,
                "name": config.name,
                "max_duration_h": config.max_duration_h,
                "max_size_mb": config.max_size_mb,
                "max_channels": config.max_channels,
                "release_date": config.release_date,
                "enabled": config.enabled,
                "is_current": phase_num == CURRENT_PHASE
            }
            for phase_num, config in PHASE_CONFIGS.items()
        }
    }


def check_file_phase_compatibility(
    duration_h: float,
    size_mb: float,
    channel_count: int
) -> dict[str, Any]:
    """
    检查文件与各阶段的兼容性（用于前端预检）
    
    Args:
        duration_h: 数据时长（小时）
        size_mb: 文件大小（MB）
        channel_count: 通道数
    
    Returns:
        兼容性报告字典
    
    Example:
        >>> report = check_file_phase_compatibility(12.0, 600, 32)
        >>> print(report["compatible_phases"])
        [2, 3]
        >>> print(report["current_phase_compatible"])
        False
    """
    compatible_phases = []
    current_compatible = False
    
    for phase_num, config in sorted(PHASE_CONFIGS.items()):
        is_compatible = (
            duration_h <= config.max_duration_h and
            size_mb <= config.max_size_mb and
            channel_count <= config.max_channels
        )
        
        if is_compatible:
            compatible_phases.append(phase_num)
            if phase_num == CURRENT_PHASE:
                current_compatible = True
    
    earliest_support = compatible_phases[0] if compatible_phases else None
    earliest_config = PHASE_CONFIGS.get(earliest_support) if earliest_support else None
    
    return {
        "duration_h": duration_h,
        "size_mb": size_mb,
        "channel_count": channel_count,
        "current_phase": CURRENT_PHASE,
        "current_phase_compatible": current_compatible,
        "compatible_phases": compatible_phases,
        "earliest_support_phase": earliest_support,
        "earliest_support_date": earliest_config.release_date if earliest_config else None,
        "requires_wait": earliest_support is not None and earliest_support > CURRENT_PHASE,
        "never_supported": earliest_support is None
    }


# ============================================================================
# 监控和统计
# ============================================================================

class PhaseValidationMetrics:
    """阶段验证指标收集器（用于监控）"""
    
    def __init__(self):
        self.total_validations = 0
        self.passed_validations = 0
        self.failed_validations = 0
        self.rejection_reasons: dict[str, int] = {}
        self.file_sizes_mb: list[float] = []
        self.durations_h: list[float] = []
    
    def record_validation(self, result: ValidationResult):
        """记录一次验证结果"""
        self.total_validations += 1
        
        if result.allowed:
            self.passed_validations += 1
        else:
            self.failed_validations += 1
            if result.rejection_code:
                self.rejection_reasons[result.rejection_code] = \
                    self.rejection_reasons.get(result.rejection_code, 0) + 1
        
        self.file_sizes_mb.append(result.file_size_mb)
        self.durations_h.append(result.duration_h)
    
    def get_summary(self) -> dict[str, Any]:
        """获取统计摘要"""
        return {
            "total_validations": self.total_validations,
            "passed_validations": self.passed_validations,
            "failed_validations": self.failed_validations,
            "pass_rate": self.passed_validations / max(1, self.total_validations),
            "rejection_rate": self.failed_validations / max(1, self.total_validations),
            "rejection_reasons": self.rejection_reasons,
            "avg_file_size_mb": sum(self.file_sizes_mb) / max(1, len(self.file_sizes_mb)),
            "avg_duration_h": sum(self.durations_h) / max(1, len(self.durations_h))
        }


# 全局指标收集器实例（可选，用于监控）
_global_metrics = PhaseValidationMetrics()


def get_validation_metrics() -> dict[str, Any]:
    """获取全局验证指标"""
    return _global_metrics.get_summary()


def reset_validation_metrics():
    """重置全局验证指标（用于测试）"""
    global _global_metrics
    _global_metrics = PhaseValidationMetrics()
