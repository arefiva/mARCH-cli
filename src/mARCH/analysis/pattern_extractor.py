"""
Pattern extraction for multi-file content analysis.

Identifies recurring themes, concepts, and patterns across aggregated file summaries.
"""

from dataclasses import dataclass, field
from typing import Optional
import logging
import re

logger = logging.getLogger(__name__)


@dataclass
class Theme:
    """Represents an identified theme or pattern."""

    name: str
    description: str
    confidence: float  # 0.0-1.0
    related_files: list[str] = field(default_factory=list)
    supporting_phrases: list[str] = field(default_factory=list)
    frequency: int = 0  # How many files mention this theme

    def __lt__(self, other):
        """Sort themes by confidence (descending)."""
        return self.confidence > other.confidence


class PatternExtractor:
    """Extracts patterns and themes from multiple file summaries.

    Handles:
    - Theme identification from key phrases
    - Concept clustering
    - Theme confidence scoring
    - Cross-file pattern detection
    """

    def __init__(self, min_frequency: int = 2, min_confidence: float = 0.5):
        """Initialize PatternExtractor.

        Args:
            min_frequency: Minimum files that must mention a pattern
            min_confidence: Minimum confidence score (0-1) for a theme
        """
        self.min_frequency = min_frequency
        self.min_confidence = min_confidence

        # Theme keywords - map of theme name to keywords that suggest it
        self.theme_keywords = {
            "specification_foundation": [
                "specification", "spec", "requirement", "requirement", "acceptance criteria",
                "acceptance", "criteria", "definition", "clear", "precise", "exact"
            ],
            "context_memory": [
                "context", "memory", "persistent", "maintain", "history", "state",
                "session", "window", "degradation", "information", "tracking"
            ],
            "human_judgment": [
                "human", "human", "judgment", "think", "understand", "decision",
                "architect", "review", "expert", "oversight", "thought"
            ],
            "cognitive_debt": [
                "cognitive", "debt", "understand", "understanding", "knowledge",
                "team", "shared", "confusion", "invisible", "erosion"
            ],
            "discipline_structure": [
                "discipline", "structure", "rigor", "organize", "framework",
                "process", "procedure", "methodology", "systematic", "formal"
            ],
            "learning_improvement": [
                "learn", "improve", "improvement", "cycle", "iteration",
                "feedback", "refine", "evolve", "progress", "growth"
            ],
            "automation_tools": [
                "tool", "automation", "agent", "ai", "model", "capability",
                "implement", "execute", "automate", "infrastructure"
            ],
            "error_handling": [
                "error", "failure", "fail", "recover", "recovery", "backtrack",
                "debug", "debug", "issue", "problem", "went wrong"
            ],
            "scaling_coordination": [
                "scale", "scaling", "team", "coordinate", "coordination",
                "concurrent", "parallel", "multiple", "many", "large"
            ],
        }

    def extract_themes(self, file_summaries: list) -> list[Theme]:
        """Extract themes from multiple file summaries.

        Args:
            file_summaries: List of FileSummary objects

        Returns:
            List of Theme objects sorted by confidence
        """
        if not file_summaries:
            return []

        themes_found = {}  # theme_name -> Theme object
        file_theme_map = {}  # theme_name -> list of files

        # Process each file's key phrases
        for summary in file_summaries:
            file_themes = self._extract_themes_from_file(summary)

            for theme_name, confidence in file_themes.items():
                if theme_name not in themes_found:
                    themes_found[theme_name] = Theme(
                        name=theme_name.replace("_", " ").title(),
                        description=self._get_theme_description(theme_name),
                        confidence=confidence,
                    )
                    file_theme_map[theme_name] = []

                file_theme_map[theme_name].append(summary.filename)
                # Increase frequency
                themes_found[theme_name].frequency += 1

        # Update theme details and filter
        themes = []
        for theme_name, theme in themes_found.items():
            if theme.frequency >= self.min_frequency and theme.confidence >= self.min_confidence:
                theme.related_files = file_theme_map[theme_name]
                theme.supporting_phrases = self._get_supporting_phrases(
                    theme_name, file_summaries
                )
                themes.append(theme)

        # Sort by confidence
        themes.sort()
        return themes

    def _extract_themes_from_file(self, summary) -> dict[str, float]:
        """Extract theme matches from a file summary.

        Args:
            summary: FileSummary object

        Returns:
            Dict of theme_name -> confidence score
        """
        themes = {}

        # Combine summary text, metadata, content, and key phrases
        text_parts = [
            summary.summary,
            " ".join(summary.key_phrases),
            summary.metadata.get("title", ""),
        ]
        if hasattr(summary, 'content') and summary.content:
            text_parts.append(summary.content[:500])  # First 500 chars
        
        text = " ".join(text_parts).lower()

        # Check each theme against the text
        for theme_name, keywords in self.theme_keywords.items():
            keyword_matches = 0
            for keyword in keywords:
                # Check for exact word boundaries or simple substring
                if re.search(rf"\b{re.escape(keyword)}\b", text) or keyword in text:
                    keyword_matches += 1

            if keyword_matches > 0:
                # Confidence = proportion of keywords that match
                confidence = min(1.0, keyword_matches / len(keywords))
                themes[theme_name] = confidence

        return themes

    def _get_theme_description(self, theme_name: str) -> str:
        """Get description for a theme.

        Args:
            theme_name: Theme identifier

        Returns:
            Theme description
        """
        descriptions = {
            "specification_foundation": "Quality specifications drive execution quality",
            "context_memory": "Persistent context and memory are critical",
            "human_judgment": "Human judgment remains irreplaceable",
            "cognitive_debt": "Understanding and shared knowledge matter",
            "discipline_structure": "Structure and discipline enable reliability",
            "learning_improvement": "Systems learn and improve over time",
            "automation_tools": "Tools and automation enhance capability",
            "error_handling": "Errors and failures are recoverable events",
            "scaling_coordination": "Coordination matters at scale",
        }
        return descriptions.get(theme_name, theme_name.replace("_", " "))

    def _get_supporting_phrases(self, theme_name: str, file_summaries: list) -> list[str]:
        """Get supporting phrases for a theme from file summaries.

        Args:
            theme_name: Theme identifier
            file_summaries: List of FileSummary objects

        Returns:
            List of phrases supporting the theme
        """
        keywords = self.theme_keywords.get(theme_name, [])
        phrases = []

        for summary in file_summaries:
            # Check key phrases
            for phrase in summary.key_phrases:
                if any(kw in phrase.lower() for kw in keywords):
                    if phrase not in phrases:
                        phrases.append(phrase)

        return phrases[:5]  # Return top 5

    def identify_gaps(self, themes: list[Theme], file_count: int) -> list[dict]:
        """Identify content gaps based on theme distribution.

        Args:
            themes: List of identified themes
            file_count: Total number of files analyzed

        Returns:
            List of gap descriptions
        """
        gaps = []
        theme_names = {t.name.lower() for t in themes}

        # Predefined gaps that might exist
        potential_gaps = [
            {
                "name": "Error Handling and Recovery",
                "keywords": ["error", "recovery", "failure"],
                "description": "How to handle failures and recover gracefully"
            },
            {
                "name": "Practical Implementation Details",
                "keywords": ["practical", "how-to", "setup", "tutorial"],
                "description": "Step-by-step guidance for implementing concepts"
            },
            {
                "name": "Real-World Examples",
                "keywords": ["example", "case study", "real", "practice"],
                "description": "Concrete examples from actual usage"
            },
            {
                "name": "Cost and Economics",
                "keywords": ["cost", "economics", "roi", "investment", "price"],
                "description": "Cost analysis and ROI calculations"
            },
            {
                "name": "Security and Compliance",
                "keywords": ["security", "compliance", "audit", "regulation"],
                "description": "Security, compliance, and audit considerations"
            },
            {
                "name": "Performance and Optimization",
                "keywords": ["performance", "optimize", "fast", "efficient"],
                "description": "Performance tuning and optimization"
            },
        ]

        # Check which gaps might exist
        for gap_spec in potential_gaps:
            gap_keywords = set(kw.lower() for kw in gap_spec["keywords"])
            has_coverage = False

            for theme in themes:
                for phrase in theme.supporting_phrases:
                    if any(kw in phrase.lower() for kw in gap_keywords):
                        has_coverage = True
                        break

            if not has_coverage:
                gaps.append({
                    "name": gap_spec["name"],
                    "description": gap_spec["description"],
                    "priority": "high" if gap_spec["keywords"][0] in theme_names else "medium",
                })

        return gaps
