"""
Correlation analysis for multi-file content understanding.

Analyzes relationships between themes, temporal progressions, and conceptual linkages.
"""

from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class Correlation:
    """Represents a relationship between items."""

    source: str
    target: str
    relationship_type: str  # "mentions", "builds_on", "contrasts", "relates_to"
    strength: float  # 0.0-1.0
    description: str = ""


class CorrelationAnalyzer:
    """Analyzes correlations and relationships across analyzed content.

    Handles:
    - Temporal progression (how themes evolve)
    - Conceptual linkage (how ideas connect)
    - Content dependencies (what builds on what)
    - Coverage mapping (which areas are covered)
    """

    def analyze_temporal_progression(
        self, file_summaries: list, themes: list
    ) -> dict:
        """Analyze how themes progress over time.

        Args:
            file_summaries: Ordered list of FileSummary objects
            themes: List of identified Theme objects

        Returns:
            Dictionary describing temporal progression
        """
        if not file_summaries or not themes:
            return {}

        progression = {
            "early_themes": [],  # First 1/3 of files
            "mid_themes": [],  # Middle 1/3
            "late_themes": [],  # Last 1/3
            "evolution": [],  # How themes change
        }

        third = len(file_summaries) // 3

        # Categorize themes by where they appear
        for theme in themes:
            if not theme.related_files:
                continue

            # Find file indices
            indices = []
            for file_name in theme.related_files:
                for i, summary in enumerate(file_summaries):
                    if summary.filename == file_name:
                        indices.append(i)
                        break

            if indices:
                avg_idx = sum(indices) / len(indices)

                if avg_idx < third:
                    progression["early_themes"].append(theme.name)
                elif avg_idx < 2 * third:
                    progression["mid_themes"].append(theme.name)
                else:
                    progression["late_themes"].append(theme.name)

        # Describe evolution
        if progression["early_themes"] and progression["late_themes"]:
            progression["evolution"] = {
                "foundation": progression["early_themes"],
                "development": progression["mid_themes"],
                "specialization": progression["late_themes"],
            }

        return progression

    def analyze_conceptual_linkage(self, themes: list, file_summaries: list) -> list[Correlation]:
        """Analyze how concepts relate to each other.

        Args:
            themes: List of identified Theme objects
            file_summaries: List of FileSummary objects

        Returns:
            List of Correlation objects
        """
        correlations = []

        # Define theme relationships
        theme_relationships = {
            "specification_foundation": ["discipline_structure", "human_judgment"],
            "context_memory": ["learning_improvement", "automation_tools"],
            "discipline_structure": ["specification_foundation", "error_handling"],
            "human_judgment": ["cognitive_debt", "specification_foundation"],
            "error_handling": ["discipline_structure", "learning_improvement"],
            "scaling_coordination": ["context_memory", "human_judgment"],
        }

        # Find correlations
        theme_dict = {t.name.lower().replace(" ", "_"): t for t in themes}

        for theme_key, related_keys in theme_relationships.items():
            if theme_key in theme_dict:
                source_theme = theme_dict[theme_key]

                for related_key in related_keys:
                    if related_key in theme_dict:
                        target_theme = theme_dict[related_key]

                        # Count co-occurrences
                        source_files = set(source_theme.related_files)
                        target_files = set(target_theme.related_files)
                        overlap = len(source_files & target_files)
                        strength = overlap / max(len(source_files), len(target_files))

                        if strength > 0:
                            correlations.append(
                                Correlation(
                                    source=source_theme.name,
                                    target=target_theme.name,
                                    relationship_type="relates_to",
                                    strength=strength,
                                    description=f"{source_theme.name} and "
                                    f"{target_theme.name} appear in {overlap} "
                                    f"files together",
                                )
                            )

        return correlations

    def analyze_coverage(self, themes: list, file_summaries: list) -> dict:
        """Analyze coverage of topics across files.

        Args:
            themes: List of identified Theme objects
            file_summaries: List of FileSummary objects

        Returns:
            Coverage analysis dictionary
        """
        coverage = {
            "total_files": len(file_summaries),
            "total_themes": len(themes),
            "coverage_map": {},
            "uncovered_areas": [],
        }

        # Map theme coverage
        for theme in themes:
            coverage_percent = (len(theme.related_files) / max(1, len(file_summaries))) * 100
            coverage["coverage_map"][theme.name] = {
                "files_mentioned": len(theme.related_files),
                "coverage_percent": round(coverage_percent, 1),
                "files": theme.related_files[:3],  # First 3 files
            }

        # Identify potentially uncovered areas
        low_coverage_threshold = 30
        for theme, stats in coverage["coverage_map"].items():
            if stats["coverage_percent"] < low_coverage_threshold:
                coverage["uncovered_areas"].append({
                    "theme": theme,
                    "coverage": stats["coverage_percent"],
                    "depth": "shallow",
                })

        return coverage

    def detect_content_gaps(
        self, themes: list, file_summaries: list, context: Optional[dict] = None
    ) -> list[dict]:
        """Detect gaps in content coverage.

        Args:
            themes: List of identified Theme objects
            file_summaries: List of FileSummary objects
            context: Optional context about author/audience

        Returns:
            List of gap descriptions with reasoning
        """
        gaps = []
        theme_names = {t.name.lower() for t in themes}

        # Gap 1: Mentioned but unexplored
        common_topics = {
            "error handling": ["error", "failure", "recover"],
            "real-world examples": ["example", "case", "practice"],
            "implementation details": ["how-to", "setup", "implement"],
            "cost analysis": ["cost", "roi", "economics"],
            "security": ["security", "compliance", "audit"],
        }

        for gap_name, keywords in common_topics.items():
            mentioned = any(
                any(kw in phrase.lower() for phrase in t.supporting_phrases)
                for t in themes
                for kw in keywords
            )
            dedicated_coverage = gap_name.lower() in theme_names

            if mentioned and not dedicated_coverage:
                gaps.append({
                    "name": f"Expand: {gap_name}",
                    "type": "mentioned_but_unexplored",
                    "priority": "high",
                    "description": f"{gap_name} is mentioned across posts but lacks dedicated coverage",
                    "recommendation": f"Write a focused post on {gap_name}",
                })

        # Gap 2: Low-coverage themes
        for theme in themes:
            coverage = len(theme.related_files) / max(1, len(file_summaries))
            if coverage < 0.4:  # Appears in <40% of files
                gaps.append({
                    "name": f"Deepen: {theme.name}",
                    "type": "shallow_coverage",
                    "priority": "medium",
                    "description": f"{theme.name} appears in only {int(coverage*100)}% of content",
                    "recommendation": f"Provide more depth on {theme.name}",
                })

        return gaps
