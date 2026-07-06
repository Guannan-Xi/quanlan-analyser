"""
癫痫分析阶段验证器 - 集成示例与测试

展示如何在现有 epilepsy_workbench.py 中集成阶段验证
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock
from fastapi import HTTPException

from backend.api.epilepsy_phase_validator import (
    validate_epilepsy_file_constraints,
    validate_by_file_id,
    get_phase_roadmap,
    check_file_phase_compatibility,
    get_validation_metrics,
    reset_validation_metrics,
    PHASE_CONFIGS,
    CURRENT_PHASE,
)


# ============================================================================
# 集成示例：如何在 epilepsy_workbench.py 中使用
# ============================================================================

"""
在 backend/api/epilepsy_workbench.py 中的集成方式：

1. 在文件顶部导入验证器：

    from backend.api.epilepsy_phase_validator import validate_by_file_id

2. 在 create_review_session 函数中添加验证（第300行附近）：

    @router.post("/tasks/{task_id}/epilepsy-review-sessions", response_model=EpilepsyReviewSession)
    def create_review_session(task_id: str, payload: CreateReviewSessionRequest) -> EpilepsyReviewSession:
        task = task_service.get_task(task_id)
        task_params = _task_parameters(task)
        inherited_context = _validate_inherited_context(payload, task_params)
        input_file_id = payload.input_file_id or _task_input_file_id(task)
        
        # ===== 新增：阶段1发布限制验证 =====
        from eeg_core.io.readers import read_raw
        validation_result = validate_by_file_id(
            input_file_id,
            storage_service,
            read_raw,
            enforce=True  # 不满足时抛出HTTPException
        )
        logger.info(f"Phase validation passed for {input_file_id}: {validation_result}")
        # ======================================
        
        workflow_id = payload.workflow_id or getattr(task, "workflow_id", "") or "epilepsy_workbench"
        # ... 其余代码保持不变

3. （可选）添加路线图查询端点：

    @router.get("/epilepsy-workbench/phase-roadmap")
    def get_epilepsy_phase_roadmap() -> dict[str, Any]:
        '''返回阶段发布路线图'''
        return get_phase_roadmap()

4. （可选）添加文件预检端点（前端上传前调用）：

    @router.post("/epilepsy-workbench/check-file-compatibility")
    def check_epilepsy_file_compatibility(
        duration_h: float,
        size_mb: float,
        channel_count: int
    ) -> dict[str, Any]:
        '''检查文件是否兼容当前阶段'''
        return check_file_phase_compatibility(duration_h, size_mb, channel_count)
"""


# ============================================================================
# 单元测试
# ============================================================================

class TestPhaseValidator:
    """阶段验证器单元测试"""
    
    def setup_method(self):
        """每个测试前重置指标"""
        reset_validation_metrics()
    
    def test_phase_1_regular_data_passes(self):
        """测试：阶段1常规数据通过验证"""
        # 创建模拟的MNE Raw对象
        mock_raw = Mock()
        mock_raw.info = {"sfreq": 256.0}
        mock_raw.n_times = 256 * 3600 * 5  # 5小时数据
        mock_raw.ch_names = ["EEG1", "EEG2", "EEG3"]
        
        # 创建模拟的读取函数
        def mock_reader(path, preload=False):
            return mock_raw
        
        # 创建临时文件（300MB）
        test_file = Path("/tmp/test_5h_300mb.edf")
        test_file.parent.mkdir(exist_ok=True)
        test_file.write_bytes(b"x" * (300 * 1024 * 1024))
        
        try:
            result = validate_epilepsy_file_constraints(
                test_file,
                mock_reader,
                enforce=False
            )
            
            assert result.allowed is True
            assert result.phase == CURRENT_PHASE
            assert result.duration_h == 5.0
            assert result.file_size_mb == 300.0
            assert result.channel_count == 3
        finally:
            if test_file.exists():
                test_file.unlink()
    
    def test_phase_1_file_too_large_rejected(self):
        """测试：阶段1超大文件被拒绝"""
        mock_raw = Mock()
        mock_raw.info = {"sfreq": 256.0}
        mock_raw.n_times = 256 * 3600 * 5  # 5小时
        mock_raw.ch_names = ["EEG1"]
        
        def mock_reader(path, preload=False):
            return mock_raw
        
        # 创建超大文件（600MB，超过500MB限制）
        test_file = Path("/tmp/test_5h_600mb.edf")
        test_file.parent.mkdir(exist_ok=True)
        test_file.write_bytes(b"x" * (600 * 1024 * 1024))
        
        try:
            with pytest.raises(HTTPException) as exc_info:
                validate_epilepsy_file_constraints(
                    test_file,
                    mock_reader,
                    enforce=True
                )
            
            assert exc_info.value.status_code == 422
            assert exc_info.value.detail["code"] == "EpilepsyFileTooLarge"
            assert "600" in str(exc_info.value.detail["message"])
            assert "expected_support" in exc_info.value.detail
        finally:
            if test_file.exists():
                test_file.unlink()
    
    def test_phase_1_duration_too_long_rejected(self):
        """测试：阶段1超长数据被拒绝"""
        mock_raw = Mock()
        mock_raw.info = {"sfreq": 256.0}
        mock_raw.n_times = 256 * 3600 * 12  # 12小时（超过10h限制）
        mock_raw.ch_names = ["EEG1"]
        
        def mock_reader(path, preload=False):
            return mock_raw
        
        test_file = Path("/tmp/test_12h_300mb.edf")
        test_file.parent.mkdir(exist_ok=True)
        test_file.write_bytes(b"x" * (300 * 1024 * 1024))
        
        try:
            result = validate_epilepsy_file_constraints(
                test_file,
                mock_reader,
                enforce=False
            )
            
            assert result.allowed is False
            assert result.rejection_code == "EpilepsyDurationTooLong"
            assert result.expected_support_phase == 2  # 阶段2支持24h
            assert result.expected_support_date == "2026-07-17"
            assert "分析" in result.workaround
        finally:
            if test_file.exists():
                test_file.unlink()
    
    def test_phase_1_extreme_data_rejected(self):
        """测试：HE-105极端场景（44h, 1.9GB）被拒绝"""
        mock_raw = Mock()
        mock_raw.info = {"sfreq": 256.0}
        mock_raw.n_times = 256 * 3600 * 44  # 44小时
        mock_raw.ch_names = ["EEG1"]
        
        def mock_reader(path, preload=False):
            return mock_raw
        
        test_file = Path("/tmp/test_he105_44h_1900mb.edf")
        test_file.parent.mkdir(exist_ok=True)
        test_file.write_bytes(b"x" * (1900 * 1024 * 1024))
        
        try:
            result = validate_epilepsy_file_constraints(
                test_file,
                mock_reader,
                enforce=False
            )
            
            assert result.allowed is False
            # 可能因为文件大小或时长被拒绝，检查其中一个
            assert result.rejection_code in ["EpilepsyFileTooLarge", "EpilepsyDurationTooLong"]
            assert result.expected_support_phase == 3  # 阶段3才支持
            assert result.expected_support_date == "2026-08-03"
        finally:
            if test_file.exists():
                test_file.unlink()
    
    def test_get_phase_roadmap(self):
        """测试：获取阶段路线图"""
        roadmap = get_phase_roadmap()
        
        assert roadmap["current_phase"] == CURRENT_PHASE
        assert roadmap["validation_enabled"] is True
        assert len(roadmap["phases"]) == 3
        assert roadmap["phases"][1]["max_duration_h"] == 10.0
        assert roadmap["phases"][2]["max_duration_h"] == 24.0
        assert roadmap["phases"][3]["max_duration_h"] == 48.0
        assert roadmap["phases"][1]["is_current"] is True
        assert roadmap["phases"][2]["is_current"] is False
    
    def test_check_file_phase_compatibility(self):
        """测试：检查文件兼容性"""
        # 测试常规数据（5h, 300MB）
        report = check_file_phase_compatibility(5.0, 300, 32)
        assert report["current_phase_compatible"] is True
        assert report["compatible_phases"] == [1, 2, 3]
        assert report["requires_wait"] is False
        
        # 测试中等数据（12h, 600MB）
        report = check_file_phase_compatibility(12.0, 600, 32)
        assert report["current_phase_compatible"] is False
        assert report["compatible_phases"] == [2, 3]
        assert report["earliest_support_phase"] == 2
        assert report["earliest_support_date"] == "2026-07-17"
        assert report["requires_wait"] is True
        
        # 测试超长数据（30h, 1500MB）
        report = check_file_phase_compatibility(30.0, 1500, 32)
        assert report["current_phase_compatible"] is False
        assert report["compatible_phases"] == [3]
        assert report["earliest_support_phase"] == 3
        assert report["requires_wait"] is True
        
        # 测试超出所有阶段的数据（60h, 3000MB）
        report = check_file_phase_compatibility(60.0, 3000, 32)
        assert report["current_phase_compatible"] is False
        assert report["compatible_phases"] == []
        assert report["never_supported"] is True


# ============================================================================
# 集成测试（需要实际文件系统和依赖）
# ============================================================================

class TestPhaseValidatorIntegration:
    """阶段验证器集成测试（需要完整环境）"""
    
    @pytest.mark.skip(reason="Requires full environment setup")
    def test_validate_by_file_id_integration(self):
        """测试：通过file_id验证（完整集成）"""
        # 这需要真实的storage_service和数据库
        from backend.services import storage_service
        from eeg_core.io.readers import read_raw
        
        # 使用真实文件ID
        test_file_id = "file_test_5h_300mb"
        
        result = validate_by_file_id(
            test_file_id,
            storage_service,
            read_raw,
            enforce=False
        )
        
        assert result is not None
        assert result.file_size_mb > 0
        assert result.duration_h > 0


# ============================================================================
# 性能测试
# ============================================================================

class TestPhaseValidatorPerformance:
    """验证器性能测试"""
    
    def test_validation_performance(self, benchmark):
        """测试：验证操作的性能"""
        mock_raw = Mock()
        mock_raw.info = {"sfreq": 256.0}
        mock_raw.n_times = 256 * 3600 * 5
        mock_raw.ch_names = ["EEG1", "EEG2"]
        
        def mock_reader(path, preload=False):
            return mock_raw
        
        test_file = Path("/tmp/test_perf.edf")
        test_file.parent.mkdir(exist_ok=True)
        test_file.write_bytes(b"x" * (300 * 1024 * 1024))
        
        try:
            # 基准测试：验证操作应该在10ms内完成
            result = benchmark(
                validate_epilepsy_file_constraints,
                test_file,
                mock_reader,
                enforce=False
            )
            assert result.allowed is True
        finally:
            if test_file.exists():
                test_file.unlink()


# ============================================================================
# 监控指标测试
# ============================================================================

class TestValidationMetrics:
    """验证指标收集测试"""
    
    def setup_method(self):
        reset_validation_metrics()
    
    def test_metrics_collection(self):
        """测试：指标收集功能"""
        from backend.api.epilepsy_phase_validator import _global_metrics, ValidationResult
        
        # 记录几次验证
        _global_metrics.record_validation(ValidationResult(
            allowed=True, phase=1, file_size_mb=300, duration_h=5, channel_count=32
        ))
        _global_metrics.record_validation(ValidationResult(
            allowed=False, phase=1, file_size_mb=600, duration_h=12, channel_count=32,
            rejection_code="EpilepsyDurationTooLong"
        ))
        _global_metrics.record_validation(ValidationResult(
            allowed=True, phase=1, file_size_mb=200, duration_h=3, channel_count=16
        ))
        
        summary = get_validation_metrics()
        
        assert summary["total_validations"] == 3
        assert summary["passed_validations"] == 2
        assert summary["failed_validations"] == 1
        assert summary["pass_rate"] == 2/3
        assert summary["rejection_rate"] == 1/3
        assert summary["rejection_reasons"]["EpilepsyDurationTooLong"] == 1
        assert summary["avg_file_size_mb"] == (300 + 600 + 200) / 3
        assert summary["avg_duration_h"] == (5 + 12 + 3) / 3


# ============================================================================
# 边界值测试
# ============================================================================

class TestBoundaryConditions:
    """边界值测试"""
    
    def test_exactly_at_limit(self):
        """测试：恰好在限制边界的数据"""
        mock_raw = Mock()
        mock_raw.info = {"sfreq": 256.0}
        mock_raw.n_times = 256 * 3600 * 10  # 恰好10小时
        mock_raw.ch_names = ["EEG1"]
        
        def mock_reader(path, preload=False):
            return mock_raw
        
        test_file = Path("/tmp/test_exactly_10h.edf")
        test_file.parent.mkdir(exist_ok=True)
        test_file.write_bytes(b"x" * (500 * 1024 * 1024))  # 恰好500MB
        
        try:
            result = validate_epilepsy_file_constraints(
                test_file,
                mock_reader,
                enforce=False
            )
            # 边界值应该通过（≤ 10h）
            assert result.allowed is True
        finally:
            if test_file.exists():
                test_file.unlink()
    
    def test_just_over_limit(self):
        """测试：刚刚超过限制的数据"""
        mock_raw = Mock()
        mock_raw.info = {"sfreq": 256.0}
        mock_raw.n_times = int(256 * 3600 * 10.1)  # 10.1小时
        mock_raw.ch_names = ["EEG1"]
        
        def mock_reader(path, preload=False):
            return mock_raw
        
        test_file = Path("/tmp/test_just_over_10h.edf")
        test_file.parent.mkdir(exist_ok=True)
        test_file.write_bytes(b"x" * (300 * 1024 * 1024))
        
        try:
            result = validate_epilepsy_file_constraints(
                test_file,
                mock_reader,
                enforce=False
            )
            # 应该被拒绝
            assert result.allowed is False
            assert result.rejection_code == "EpilepsyDurationTooLong"
        finally:
            if test_file.exists():
                test_file.unlink()


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
