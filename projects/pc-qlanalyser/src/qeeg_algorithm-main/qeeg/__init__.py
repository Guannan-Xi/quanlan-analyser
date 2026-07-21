"""QEEG Analysis Package"""

__version__ = "1.1.0"
__author__ = "QEEG Analysis Team"

from .analyzer import QEEGAnalyzer
from .models import (
    PAFResult,
    TBRResult,
    PSDResult,
    BandMappingResult,
    RatioMappingResult,
    QEEGAnalysisResult,
    PreprocessingParams,
)

from .zscore import (
    ZScoreCalculator,
    ZScoreResult,
    BroadBandZScore,
    NarrowBandZScore,
    NarrowBandZScoreBands,
    BA_ELECTRODES,
    BA_REGIONS,
)

__all__ = [
    "QEEGAnalyzer",
    "PAFResult",
    "TBRResult", 
    "PSDResult",
    "BandMappingResult",
    "RatioMappingResult",
    "QEEGAnalysisResult",
    "PreprocessingParams",
    "ZScoreCalculator",
    "ZScoreResult",
    "BroadBandZScore",
    "NarrowBandZScore",
    "NarrowBandZScoreBands",
    "BA_ELECTRODES",
    "BA_REGIONS",
]
