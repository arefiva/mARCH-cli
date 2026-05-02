"""Test analysis extension integration."""

import asyncio
import pytest
from pathlib import Path
from mARCH.extension.builtin.analysis_extension import AnalysisExtension
from mARCH.extension.lifecycle import ExtensionContext


@pytest.fixture
def analysis_extension():
    """Create an analysis extension instance."""
    async def _create():
        context = ExtensionContext(
            name="analysis",
            version="0.1.0",
            path=Path("src/mARCH/extension/builtin/analysis_extension"),
            config={},
        )
        ext = AnalysisExtension(context)
        await ext.on_load()
        return ext
    
    return asyncio.run(_create())


@pytest.mark.asyncio
async def test_analysis_extension_loads(analysis_extension):
    """Test that extension loads and registers tools."""
    tools = analysis_extension.get_tools()
    assert len(tools) == 4
    assert "aggregate_files" in tools
    assert "extract_themes" in tools
    assert "detect_gaps" in tools
    assert "analyze_content" in tools


@pytest.mark.asyncio
async def test_analyze_blog_with_extension(analysis_extension, tmp_path):
    """Test complete blog analysis using extension tools."""
    # Create sample blog posts
    posts = [
        ("post1.md", "# Introduction to Agents\nSpecification and agents"),
        ("post2.md", "# Error Handling\nFail gracefully, recover properly"),
        ("post3.md", "# Performance\nOptimization and scaling"),
    ]
    
    for filename, content in posts:
        (tmp_path / filename).write_text(content)
    
    # Test aggregate_files
    agg_result = await analysis_extension.invoke_tool(
        "aggregate_files", directory=str(tmp_path)
    )
    assert agg_result["success"] is True
    assert agg_result["file_count"] == 3
    
    # Test extract_themes
    theme_result = await analysis_extension.invoke_tool(
        "extract_themes", directory=str(tmp_path)
    )
    assert theme_result["success"] is True
    assert theme_result["theme_count"] > 0
    
    # Test detect_gaps
    gap_result = await analysis_extension.invoke_tool(
        "detect_gaps", directory=str(tmp_path)
    )
    assert gap_result["success"] is True
    assert "gap_count" in gap_result
    
    # Test complete analysis
    analysis_result = await analysis_extension.invoke_tool(
        "analyze_content", directory=str(tmp_path)
    )
    assert analysis_result["success"] is True
    assert "analysis" in analysis_result
    analysis = analysis_result["analysis"]
    assert analysis["files_analyzed"] == 3
    assert analysis["themes_found"] > 0


@pytest.mark.asyncio
async def test_analysis_on_real_blog(analysis_extension):
    """Test analysis on real blog directory."""
    blog_path = Path("/home/fbl/repos/communication/arefiva.github.io/_posts")
    
    if not blog_path.exists():
        pytest.skip("Blog directory not found")
    
    # Run complete analysis
    result = await analysis_extension.invoke_tool(
        "analyze_content", directory=str(blog_path)
    )
    
    # Should succeed
    assert result["success"] is True
    analysis = result["analysis"]
    
    # Should find multiple posts and themes
    assert analysis["files_analyzed"] > 5
    assert analysis["themes_found"] >= 5
    
    # Should detect gaps
    assert analysis["gap_count"] > 0
    
    # Themes should be identifiable
    themes = analysis["themes"]
    theme_names = {t["name"] for t in themes}
    assert len(theme_names) > 0
