"""Analysis extension for multi-file content analysis.

Provides tools for analyzing multiple files, extracting patterns,
and detecting gaps in content.
"""

import logging
from pathlib import Path
from typing import Any, Optional

from mARCH.analysis.correlation_analyzer import CorrelationAnalyzer
from mARCH.analysis.file_aggregator import aggregate_files_sync
from mARCH.analysis.pattern_extractor import PatternExtractor
from mARCH.extension.lifecycle import ExtensionContext
from mARCH.extension.tool import ToolExtension

logger = logging.getLogger(__name__)


class AnalysisExtension(ToolExtension):
    """Extension providing content analysis capabilities."""

    async def on_load(self) -> None:
        """Register analysis tools."""
        self.register_tool(
            "aggregate_files",
            self._aggregate_files,
            description="Aggregate and summarize multiple files from a directory",
            parameters={
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "Path to directory containing files to analyze",
                    },
                    "pattern": {
                        "type": "string",
                        "description": "File pattern to match (default: *.md)",
                        "default": "*.md",
                    },
                    "max_files": {
                        "type": "integer",
                        "description": "Maximum number of files to aggregate",
                        "default": 100,
                    },
                },
                "required": ["directory"],
            },
        )

        self.register_tool(
            "extract_themes",
            self._extract_themes,
            description="Extract recurring themes and patterns from aggregated content",
            parameters={
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "Directory to analyze",
                    },
                    "pattern": {
                        "type": "string",
                        "description": "File pattern (default: *.md)",
                        "default": "*.md",
                    },
                    "min_frequency": {
                        "type": "integer",
                        "description": "Minimum theme frequency threshold",
                        "default": 2,
                    },
                },
                "required": ["directory"],
            },
        )

        self.register_tool(
            "detect_gaps",
            self._detect_gaps,
            description="Detect content gaps and opportunities in analyzed content",
            parameters={
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "Directory to analyze",
                    },
                    "pattern": {
                        "type": "string",
                        "description": "File pattern (default: *.md)",
                        "default": "*.md",
                    },
                },
                "required": ["directory"],
            },
        )

        self.register_tool(
            "analyze_content",
            self._analyze_content,
            description="Perform complete content analysis (aggregate -> extract -> detect)",
            parameters={
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "Directory to analyze",
                    },
                    "pattern": {
                        "type": "string",
                        "description": "File pattern (default: *.md)",
                        "default": "*.md",
                    },
                },
                "required": ["directory"],
            },
        )

    async def _aggregate_files(
        self,
        directory: str,
        pattern: str = "*.md",
        max_files: int = 100,
    ) -> dict[str, Any]:
        """Aggregate files from a directory.

        Args:
            directory: Directory path
            pattern: File glob pattern
            max_files: Maximum files to read

        Returns:
            Aggregation results with file count and summaries
        """
        try:
            path = Path(directory)
            if not path.exists():
                return {
                    "success": False,
                    "error": f"Directory not found: {directory}",
                    "file_count": 0,
                }

            summaries = aggregate_files_sync(
                path, pattern=pattern, max_files=max_files
            )

            return {
                "success": True,
                "directory": str(path),
                "pattern": pattern,
                "file_count": len(summaries),
                "files": [
                    {
                        "name": s.filename,
                        "path": s.path,
                        "title": s.metadata.get("title", ""),
                        "key_phrases": s.key_phrases[:5],
                    }
                    for s in summaries
                ],
            }
        except Exception as e:
            logger.error(f"Error aggregating files: {e}")
            return {
                "success": False,
                "error": str(e),
                "file_count": 0,
            }

    async def _extract_themes(
        self,
        directory: str,
        pattern: str = "*.md",
        min_frequency: int = 2,
    ) -> dict[str, Any]:
        """Extract themes from content.

        Args:
            directory: Directory path
            pattern: File glob pattern
            min_frequency: Minimum theme frequency

        Returns:
            Extracted themes with statistics
        """
        try:
            path = Path(directory)
            if not path.exists():
                return {
                    "success": False,
                    "error": f"Directory not found: {directory}",
                    "theme_count": 0,
                }

            # Aggregate files
            summaries = aggregate_files_sync(path, pattern=pattern)

            if not summaries:
                return {
                    "success": False,
                    "error": "No files found to analyze",
                    "theme_count": 0,
                }

            # Extract themes
            extractor = PatternExtractor(
                min_frequency=min_frequency, min_confidence=0.1
            )
            themes = extractor.extract_themes(summaries)

            return {
                "success": True,
                "file_count": len(summaries),
                "theme_count": len(themes),
                "themes": [
                    {
                        "name": t.name,
                        "frequency": t.frequency,
                        "confidence": round(t.confidence, 2),
                    }
                    for t in sorted(
                        themes, key=lambda t: t.frequency, reverse=True
                    )
                ],
            }
        except Exception as e:
            logger.error(f"Error extracting themes: {e}")
            return {
                "success": False,
                "error": str(e),
                "theme_count": 0,
            }

    async def _detect_gaps(
        self,
        directory: str,
        pattern: str = "*.md",
    ) -> dict[str, Any]:
        """Detect content gaps.

        Args:
            directory: Directory path
            pattern: File glob pattern

        Returns:
            Detected gaps and opportunities
        """
        try:
            path = Path(directory)
            if not path.exists():
                return {
                    "success": False,
                    "error": f"Directory not found: {directory}",
                    "gap_count": 0,
                }

            # Aggregate files
            summaries = aggregate_files_sync(path, pattern=pattern)

            if not summaries:
                return {
                    "success": False,
                    "error": "No files found to analyze",
                    "gap_count": 0,
                }

            # Extract themes
            extractor = PatternExtractor(
                min_frequency=1, min_confidence=0.1
            )
            themes = extractor.extract_themes(summaries)

            # Analyze correlations and detect gaps
            analyzer = CorrelationAnalyzer()
            gaps = analyzer.detect_content_gaps(themes, summaries)

            return {
                "success": True,
                "file_count": len(summaries),
                "theme_count": len(themes),
                "gap_count": len(gaps),
                "gaps": gaps[:10],  # Top 10 gaps
            }
        except Exception as e:
            logger.error(f"Error detecting gaps: {e}")
            return {
                "success": False,
                "error": str(e),
                "gap_count": 0,
            }

    async def _analyze_content(
        self,
        directory: str,
        pattern: str = "*.md",
    ) -> dict[str, Any]:
        """Perform complete content analysis.

        Args:
            directory: Directory path
            pattern: File glob pattern

        Returns:
            Complete analysis results
        """
        try:
            path = Path(directory)
            if not path.exists():
                return {
                    "success": False,
                    "error": f"Directory not found: {directory}",
                }

            # Aggregate files
            summaries = aggregate_files_sync(path, pattern=pattern)

            if not summaries:
                return {
                    "success": False,
                    "error": "No files found to analyze",
                }

            # Extract themes
            extractor = PatternExtractor(
                min_frequency=2, min_confidence=0.1
            )
            themes = extractor.extract_themes(summaries)

            # Analyze correlations
            analyzer = CorrelationAnalyzer()
            gaps = analyzer.detect_content_gaps(themes, summaries)
            coverage = analyzer.analyze_coverage(themes, summaries)

            # Build comprehensive result
            return {
                "success": True,
                "analysis": {
                    "files_analyzed": len(summaries),
                    "themes_found": len(themes),
                    "gaps_identified": len(gaps),
                    "themes": [
                        {
                            "name": t.name,
                            "frequency": t.frequency,
                            "confidence": round(t.confidence, 2),
                            "coverage": round(
                                coverage.get(t.name.lower(), {}).get(
                                    "percentage", 0
                                ),
                                1,
                            ),
                        }
                        for t in sorted(
                            themes, key=lambda t: t.frequency, reverse=True
                        )
                    ],
                    "top_gaps": gaps[:5],
                },
            }
        except Exception as e:
            logger.error(f"Error in complete analysis: {e}")
            return {
                "success": False,
                "error": str(e),
            }
