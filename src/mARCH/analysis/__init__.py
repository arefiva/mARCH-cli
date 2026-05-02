"""
Analysis module for mARCH.

Provides multi-file analysis capabilities including aggregation, pattern extraction,
and correlation analysis for content understanding and gap identification.
"""

from mARCH.analysis.file_aggregator import FileAggregator, FileSummary
from mARCH.analysis.pattern_extractor import PatternExtractor, Theme
from mARCH.analysis.correlation_analyzer import CorrelationAnalyzer

__all__ = [
    "FileAggregator",
    "FileSummary",
    "PatternExtractor",
    "Theme",
    "CorrelationAnalyzer",
]
