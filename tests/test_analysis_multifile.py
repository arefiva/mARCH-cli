"""
Tests for multi-file analysis capabilities.

Tests FileAggregator, PatternExtractor, and CorrelationAnalyzer.
"""

import asyncio
import tempfile
from pathlib import Path
import pytest

from mARCH.analysis.file_aggregator import FileAggregator, aggregate_files_sync
from mARCH.analysis.pattern_extractor import PatternExtractor, Theme
from mARCH.analysis.correlation_analyzer import CorrelationAnalyzer


class TestFileAggregator:
    """Test FileAggregator functionality."""

    @pytest.fixture
    def temp_files(self):
        """Create temporary test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create test markdown files
            (tmpdir / "post1.md").write_text("""---
title: First Post
date: 2026-04-15
---

# Welcome to Analysis

This is the first post about specification-first development.
Key concepts include acceptance criteria and specification.
""")

            (tmpdir / "post2.md").write_text("""---
title: Second Post
date: 2026-04-16
---

# Context and Memory

Context persistence is critical for agentic systems.
We need to maintain state across multiple interactions.
""")

            (tmpdir / "post3.md").write_text("""---
title: Third Post
date: 2026-04-17
---

# Human Judgment

Even with automation, human judgment remains essential.
Architects must make decisions that agents cannot.
""")

            yield tmpdir

    @pytest.mark.asyncio
    async def test_aggregate_files(self, temp_files):
        """Test basic file aggregation."""
        aggregator = FileAggregator(max_files=10)
        summaries = await aggregator.aggregate_files(temp_files, pattern="*.md")

        assert len(summaries) == 3
        assert all(s.is_valid for s in summaries)
        assert summaries[0].filename == "post1.md"

    def test_aggregate_files_sync(self, temp_files):
        """Test synchronous file aggregation."""
        summaries = aggregate_files_sync(temp_files, pattern="*.md")

        assert len(summaries) == 3
        assert summaries[0].filename == "post1.md"

    @pytest.mark.asyncio
    async def test_file_summary_extraction(self, temp_files):
        """Test that file summaries are correctly extracted."""
        aggregator = FileAggregator()
        summaries = await aggregator.aggregate_files(temp_files, pattern="*.md")

        # Check metadata extraction
        assert summaries[0].metadata.get("title") == "First Post"
        assert "2026-04" in summaries[0].metadata.get("date", "")

        # Check summary generation
        assert "First Post" in summaries[0].summary or "specification" in summaries[0].summary

        # Check key phrases
        assert len(summaries[0].key_phrases) > 0

    @pytest.mark.asyncio
    async def test_empty_directory(self):
        """Test aggregation on empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            aggregator = FileAggregator()
            summaries = await aggregator.aggregate_files(tmpdir, pattern="*.md")

            assert len(summaries) == 0

    @pytest.mark.asyncio
    async def test_max_files_limit(self, temp_files):
        """Test that max_files limit is respected."""
        # Create 5 files
        for i in range(2):
            (temp_files / f"extra_{i}.md").write_text("# Extra\nContent")

        aggregator = FileAggregator(max_files=3)
        summaries = await aggregator.aggregate_files(temp_files, pattern="*.md")

        assert len(summaries) <= 3

    @pytest.mark.asyncio
    async def test_large_file_handling(self, temp_files):
        """Test handling of large files."""
        # Create a "large" file (exceeding limit)
        large_file = temp_files / "large.md"
        large_file.write_text("x" * (11 * 1024 * 1024))  # 11MB

        aggregator = FileAggregator(max_file_size_mb=10)
        summaries = await aggregator.aggregate_files(temp_files, pattern="*.md")

        # Should include valid files and mark large file as invalid
        assert any(not s.is_valid for s in summaries)


class TestPatternExtractor:
    """Test PatternExtractor functionality."""

    @pytest.fixture
    def sample_summaries(self, tmp_path):
        """Create sample file summaries."""
        from mARCH.analysis.file_aggregator import FileSummary

        summaries = [
            FileSummary(
                path="post1.md",
                filename="post1.md",
                content="Specification and acceptance criteria",
                summary="Specification-first development approach",
                key_phrases=["specification", "criteria", "development"],
                metadata={"title": "Spec First"},
                is_valid=True,
            ),
            FileSummary(
                path="post2.md",
                filename="post2.md",
                content="Context and persistent memory",
                summary="Context persistence in agents",
                key_phrases=["context", "memory", "persistent"],
                metadata={"title": "Context Memory"},
                is_valid=True,
            ),
            FileSummary(
                path="post3.md",
                filename="post3.md",
                content="Human judgment in architecture",
                summary="Why humans must make architecture decisions",
                key_phrases=["human", "judgment", "architecture"],
                metadata={"title": "Human Judgment"},
                is_valid=True,
            ),
        ]
        return summaries

    def test_theme_extraction(self, sample_summaries):
        """Test that themes are correctly extracted."""
        extractor = PatternExtractor(min_frequency=1, min_confidence=0.3)
        themes = extractor.extract_themes(sample_summaries)

        assert len(themes) > 0
        # Should find specification theme
        theme_names = [t.name.lower() for t in themes]
        assert any("specification" in name for name in theme_names)

    def test_theme_frequency(self, sample_summaries):
        """Test that theme frequency is correctly counted."""
        extractor = PatternExtractor()
        themes = extractor.extract_themes(sample_summaries)

        # Most themes should appear in 1-2 files
        for theme in themes:
            assert theme.frequency >= 1

    def test_theme_confidence(self, sample_summaries):
        """Test that theme confidence scores are calculated."""
        extractor = PatternExtractor()
        themes = extractor.extract_themes(sample_summaries)

        # All themes should have confidence scores
        assert all(0 <= t.confidence <= 1 for t in themes)

    def test_gap_identification(self, sample_summaries):
        """Test that content gaps are identified."""
        extractor = PatternExtractor()
        themes = extractor.extract_themes(sample_summaries)
        gaps = extractor.identify_gaps(themes, len(sample_summaries))

        assert len(gaps) > 0
        # Gaps should have names and descriptions
        assert all("name" in g and "description" in g for g in gaps)

    def test_empty_input(self):
        """Test behavior with empty input."""
        extractor = PatternExtractor()
        themes = extractor.extract_themes([])

        assert len(themes) == 0


class TestCorrelationAnalyzer:
    """Test CorrelationAnalyzer functionality."""

    @pytest.fixture
    def sample_themes(self):
        """Create sample themes."""
        return [
            Theme(
                name="Specification Foundation",
                description="Quality specs drive execution",
                confidence=0.9,
                related_files=["post1.md", "post2.md", "post3.md"],
                supporting_phrases=["specification", "acceptance criteria"],
                frequency=3,
            ),
            Theme(
                name="Context and Memory",
                description="Persistent context is critical",
                confidence=0.8,
                related_files=["post2.md", "post3.md"],
                supporting_phrases=["context", "persistent"],
                frequency=2,
            ),
            Theme(
                name="Human Judgment",
                description="Humans make key decisions",
                confidence=0.7,
                related_files=["post3.md"],
                supporting_phrases=["human", "judgment"],
                frequency=1,
            ),
        ]

    @pytest.fixture
    def sample_summaries(self):
        """Create sample file summaries."""
        from mARCH.analysis.file_aggregator import FileSummary

        return [
            FileSummary(
                path="post1.md",
                filename="post1.md",
                content="First",
                summary="First post",
                key_phrases=[],
                is_valid=True,
            ),
            FileSummary(
                path="post2.md",
                filename="post2.md",
                content="Second",
                summary="Second post",
                key_phrases=[],
                is_valid=True,
            ),
            FileSummary(
                path="post3.md",
                filename="post3.md",
                content="Third",
                summary="Third post",
                key_phrases=[],
                is_valid=True,
            ),
        ]

    def test_temporal_progression(self, sample_themes, sample_summaries):
        """Test temporal progression analysis."""
        analyzer = CorrelationAnalyzer()
        progression = analyzer.analyze_temporal_progression(sample_summaries, sample_themes)

        assert "early_themes" in progression
        assert "mid_themes" in progression
        assert "late_themes" in progression

    def test_conceptual_linkage(self, sample_themes, sample_summaries):
        """Test conceptual linkage analysis."""
        analyzer = CorrelationAnalyzer()
        correlations = analyzer.analyze_conceptual_linkage(sample_themes, sample_summaries)

        assert isinstance(correlations, list)
        # Should find relationships between themes
        if correlations:
            assert all(hasattr(c, "source") and hasattr(c, "target") for c in correlations)

    def test_coverage_analysis(self, sample_themes, sample_summaries):
        """Test coverage analysis."""
        analyzer = CorrelationAnalyzer()
        coverage = analyzer.analyze_coverage(sample_themes, sample_summaries)

        assert coverage["total_files"] == 3
        assert coverage["total_themes"] == 3
        assert "coverage_map" in coverage
        # Each theme should have coverage info
        assert len(coverage["coverage_map"]) == 3

    def test_gap_detection(self, sample_themes, sample_summaries):
        """Test gap detection."""
        analyzer = CorrelationAnalyzer()
        gaps = analyzer.detect_content_gaps(sample_themes, sample_summaries)

        assert isinstance(gaps, list)
        # Should potentially find gaps
        if gaps:
            assert all("name" in g and "description" in g for g in gaps)


class TestIntegration:
    """Integration tests for full analysis pipeline."""

    def test_full_analysis_pipeline(self):
        """Test complete analysis pipeline from files to gaps."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create test posts
            posts = [
                (
                    "post1.md",
                    """---
title: Specification Foundation
---
# Spec First

Acceptance criteria and specification are foundational.
Clear requirements drive successful implementation.""",
                ),
                (
                    "post2.md",
                    """---
title: Context and Memory
---
# Persistent Context

Maintaining context and state across interactions.
Memory systems enable better decision-making.""",
                ),
                (
                    "post3.md",
                    """---
title: Error Handling
---
# When Things Fail

Error recovery and failure handling strategies.
Resilience through proper error management.""",
                ),
            ]

            for filename, content in posts:
                (tmpdir / filename).write_text(content)

            # Step 1: Aggregate files
            summaries = aggregate_files_sync(tmpdir, pattern="*.md")
            assert len(summaries) == 3

            # Step 2: Extract themes (allow lower frequency for pipeline test)
            extractor = PatternExtractor(min_frequency=1, min_confidence=0.2)
            themes = extractor.extract_themes(summaries)
            assert len(themes) > 0

            # Step 3: Analyze correlations
            analyzer = CorrelationAnalyzer()
            coverage = analyzer.analyze_coverage(themes, summaries)
            assert coverage["total_files"] == 3

            # Step 4: Detect gaps
            gaps = analyzer.detect_content_gaps(themes, summaries)
            # Should find some gaps
            assert isinstance(gaps, list)

    def test_end_to_end_blog_analysis(self):
        """Test end-to-end blog analysis like the original task."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create realistic blog posts
            blog_posts = {
                "post1.md": "# Welcome\nIntroduction to agentic development",
                "post2.md": "# Spec First\nSpecification-driven approach",
                "post3.md": "# Context Memory\nPersistent context in agents",
                "post4.md": "# Human Judgment\nWhy humans matter",
                "post5.md": "# Error Recovery\nHandling failures gracefully",
            }

            for name, content in blog_posts.items():
                (tmpdir / name).write_text(content)

            # Full analysis (allow lower frequency for 5-file test)
            summaries = aggregate_files_sync(tmpdir)
            assert len(summaries) == 5

            extractor = PatternExtractor(min_frequency=1, min_confidence=0.15)
            themes = extractor.extract_themes(summaries)
            assert len(themes) > 0

            analyzer = CorrelationAnalyzer()
            gaps = analyzer.detect_content_gaps(themes, summaries)
            assert isinstance(gaps, list)
