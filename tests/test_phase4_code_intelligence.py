"""
Tests for Phase 4: Code Intelligence components.

Tests tree-sitter parsing, ripgrep search, LSP client, and syntax highlighting.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

from mARCH.tree_sitter import (
    TreeSitterParser,
    TreeSitterLanguage,
    get_tree_sitter_parser,
)
from mARCH.ripgrep_search import (
    RipgrepSearcher,
    SearchMatch,
    get_ripgrep_searcher,
)
from mARCH.lsp_client import (
    Position,
    Range,
    Location,
    Diagnostic,
    CompletionItem,
    LSPClient,
    LSPManager,
    get_lsp_manager,
)
from mARCH.syntax_highlight import (
    CodeHighlighter,
    SyntaxHighlightRenderer,
    get_code_highlighter,
    get_syntax_renderer,
)
from mARCH.code_intelligence import (
    CodeIntelligence,
    get_code_intelligence,
)


# ============================================================================
# Tree-Sitter Tests
# ============================================================================


class TestTreeSitterLanguage:
    """Tests for TreeSitterLanguage constants."""

    def test_supported_languages(self):
        """Test that supported languages are defined."""
        assert TreeSitterLanguage.PYTHON in TreeSitterLanguage.SUPPORTED
        assert TreeSitterLanguage.JAVASCRIPT in TreeSitterLanguage.SUPPORTED
        assert TreeSitterLanguage.TYPESCRIPT in TreeSitterLanguage.SUPPORTED

    def test_extension_map(self):
        """Test extension to language mapping."""
        assert TreeSitterLanguage.EXTENSION_MAP["py"] == "python"
        assert TreeSitterLanguage.EXTENSION_MAP["js"] == "javascript"
        assert TreeSitterLanguage.EXTENSION_MAP["ts"] == "typescript"
        assert TreeSitterLanguage.EXTENSION_MAP["go"] == "go"


class TestTreeSitterParser:
    """Tests for TreeSitterParser."""

    def test_parser_initialization(self):
        """Test parser can be initialized."""
        parser = TreeSitterParser()
        assert parser is not None

    def test_get_language(self):
        """Test getting language parser."""
        parser = TreeSitterParser()
        # Python should be available if tree-sitter-python is installed
        lang = parser.get_language("python")
        # May be None if tree-sitter doesn't have parsers, but that's okay for testing

    def test_unsupported_language(self):
        """Test that unsupported languages return None."""
        parser = TreeSitterParser()
        lang = parser.get_language("nonexistent")
        assert lang is None

    def test_parse_python_code(self):
        """Test parsing Python code."""
        parser = TreeSitterParser()
        code = "def hello():\n    pass\n"
        # May return None if tree-sitter-python not installed, but shouldn't error
        root = parser.parse(code, "python")
        # Just verify it doesn't crash

    def test_parser_singleton(self):
        """Test parser singleton."""
        parser1 = get_tree_sitter_parser()
        parser2 = get_tree_sitter_parser()
        assert parser1 is parser2


# ============================================================================
# Ripgrep Search Tests
# ============================================================================


class TestSearchMatch:
    """Tests for SearchMatch dataclass."""

    def test_search_match_creation(self):
        """Test creating a search match."""
        match = SearchMatch(
            file_path="test.py",
            line_number=10,
            column=5,
            line_text="def hello():",
            match_text="hello",
        )
        assert match.file_path == "test.py"
        assert match.line_number == 10


class TestRipgrepSearcher:
    """Tests for RipgrepSearcher."""

    def test_searcher_initialization(self):
        """Test searcher can be initialized if rg available."""
        try:
            searcher = RipgrepSearcher()
            assert searcher is not None
        except RuntimeError:
            # rg not installed, that's okay for test
            pytest.skip("ripgrep not installed")

    def test_searcher_rg_not_available(self):
        """Test error when rg not available."""
        with patch("subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(RuntimeError):
                RipgrepSearcher(rg_path="/nonexistent/rg")

    def test_search_symbol(self):
        """Test searching for symbol with word boundaries."""
        try:
            searcher = RipgrepSearcher()
            # Use a pattern we know won't match in non-existent dir
            matches = searcher.search_symbol(
                "nonexistent_symbol_xyz", directory="/tmp"
            )
            # May return empty list
            assert isinstance(matches, list)
        except RuntimeError:
            pytest.skip("ripgrep not installed")

    def test_get_ripgrep_searcher_singleton(self):
        """Test ripgrep searcher singleton."""
        try:
            searcher1 = get_ripgrep_searcher()
            # May be None if rg not available
            if searcher1:
                searcher2 = get_ripgrep_searcher()
                assert searcher1 is searcher2
        except RuntimeError:
            pytest.skip("ripgrep not installed")


# ============================================================================
# LSP Client Tests
# ============================================================================


class TestPosition:
    """Tests for Position dataclass."""

    def test_position_creation(self):
        """Test creating a position."""
        pos = Position(line=10, character=5)
        assert pos.line == 10
        assert pos.character == 5


class TestRange:
    """Tests for Range dataclass."""

    def test_range_creation(self):
        """Test creating a range."""
        start = Position(0, 0)
        end = Position(10, 5)
        range_obj = Range(start=start, end=end)
        assert range_obj.start.line == 0
        assert range_obj.end.line == 10


class TestLocation:
    """Tests for Location dataclass."""

    def test_location_creation(self):
        """Test creating a location."""
        start = Position(0, 0)
        end = Position(10, 5)
        range_obj = Range(start=start, end=end)
        loc = Location(uri="file:///test.py", range=range_obj)
        assert loc.uri == "file:///test.py"
        assert loc.range.start.line == 0


class TestDiagnostic:
    """Tests for Diagnostic dataclass."""

    def test_diagnostic_creation(self):
        """Test creating a diagnostic."""
        range_obj = Range(
            start=Position(0, 0), end=Position(0, 5)
        )
        diag = Diagnostic(
            range=range_obj,
            message="Syntax error",
            severity=1,  # error
            code="E001",
        )
        assert diag.message == "Syntax error"
        assert diag.severity == 1


class TestCompletionItem:
    """Tests for CompletionItem dataclass."""

    def test_completion_item_creation(self):
        """Test creating a completion item."""
        item = CompletionItem(
            label="print",
            kind=3,  # Function
            detail="Built-in function",
            documentation="Print to stdout",
        )
        assert item.label == "print"
        assert item.kind == 3


class TestLSPClient:
    """Tests for LSPClient."""

    @patch("subprocess.Popen")
    def test_lsp_client_initialization(self, mock_popen):
        """Test LSP client can be initialized."""
        mock_process = MagicMock()
        mock_popen.return_value = mock_process

        try:
            client = LSPClient(["pylsp"], root_path="/test")
            assert client is not None
        except RuntimeError:
            pytest.skip("pylsp not installed")

    def test_lsp_client_init_fails_without_server(self):
        """Test LSP client fails gracefully without server."""
        with pytest.raises(RuntimeError):
            LSPClient(["/nonexistent/server"], root_path="/test")


class TestLSPManager:
    """Tests for LSPManager."""

    def test_manager_initialization(self):
        """Test manager can be initialized."""
        manager = LSPManager()
        assert manager is not None

    def test_get_lsp_manager_singleton(self):
        """Test LSP manager singleton."""
        mgr1 = get_lsp_manager()
        mgr2 = get_lsp_manager()
        assert mgr1 is mgr2

    def test_manager_get_nonexistent_client(self):
        """Test getting client for non-supported language."""
        manager = LSPManager()
        client = manager.get_client("unsupported_lang")
        assert client is None


# ============================================================================
# Syntax Highlighting Tests
# ============================================================================


class TestCodeHighlighter:
    """Tests for CodeHighlighter."""

    def test_highlighter_initialization(self):
        """Test highlighter can be initialized."""
        highlighter = CodeHighlighter(theme="dark")
        assert highlighter is not None
        assert highlighter.theme == "dark"

    def test_language_aliases(self):
        """Test language aliases mapping."""
        assert CodeHighlighter.LANGUAGE_ALIASES["py"] == "python"
        assert CodeHighlighter.LANGUAGE_ALIASES["js"] == "javascript"

    def test_highlight_code(self):
        """Test highlighting code."""
        highlighter = CodeHighlighter()
        code = "print('hello')"
        # Just verify it doesn't crash
        result = highlighter.highlight_code(code, "python")
        assert isinstance(result, str)

    def test_inline_highlight(self):
        """Test inline highlighting."""
        highlighter = CodeHighlighter()
        code = "let x = 42;"
        result = highlighter.get_inline_highlight(code, "javascript")
        assert isinstance(result, str)

    def test_get_code_highlighter_singleton(self):
        """Test code highlighter singleton."""
        h1 = get_code_highlighter()
        h2 = get_code_highlighter()
        assert h1 is h2


class TestSyntaxHighlightRenderer:
    """Tests for SyntaxHighlightRenderer."""

    def test_renderer_initialization(self):
        """Test renderer can be initialized."""
        renderer = SyntaxHighlightRenderer(theme="monokai")
        assert renderer is not None

    def test_get_syntax_renderer_singleton(self):
        """Test syntax renderer singleton."""
        r1 = get_syntax_renderer()
        r2 = get_syntax_renderer()
        assert r1 is r2


# ============================================================================
# Code Intelligence Tests
# ============================================================================


class TestCodeIntelligence:
    """Tests for CodeIntelligence unified interface."""

    def test_code_intelligence_initialization(self):
        """Test CodeIntelligence can be initialized."""
        ci = CodeIntelligence()
        assert ci is not None

    def test_code_intelligence_components(self):
        """Test that all components are initialized."""
        ci = CodeIntelligence()
        assert ci.parser is not None
        # searcher may be None if ripgrep not installed
        assert ci.lsp_manager is not None
        assert ci.highlighter is not None
        assert ci.renderer is not None

    def test_search_code(self):
        """Test code search."""
        ci = CodeIntelligence()
        if ci.searcher:
            # Use a pattern that won't match in non-existent dir
            matches = ci.search_code("xyz_nonexistent", directory="/tmp")
            assert isinstance(matches, list)

    def test_search_symbol(self):
        """Test symbol search."""
        ci = CodeIntelligence()
        if ci.searcher:
            matches = ci.search_symbol("xyz_nonexistent", directory="/tmp")
            assert isinstance(matches, list)

    def test_highlight_code(self):
        """Test code highlighting."""
        ci = CodeIntelligence()
        code = "def hello():\n    pass"
        result = ci.highlight_code(code, "python")
        assert isinstance(result, str)

    def test_get_code_outline(self):
        """Test getting code outline."""
        ci = CodeIntelligence()
        # This may return empty if tree-sitter not set up, but shouldn't crash
        outline = ci.get_code_outline("test.py")
        assert isinstance(outline, dict)
        assert "file" in outline

    def test_get_code_intelligence_singleton(self):
        """Test CodeIntelligence singleton."""
        ci1 = get_code_intelligence()
        ci2 = get_code_intelligence()
        assert ci1 is ci2


# ============================================================================
# Integration Tests
# ============================================================================


class TestPhase4Integration:
    """Integration tests for Phase 4 components."""

    def test_all_components_available(self):
        """Test that all Phase 4 components are available."""
        # Tree-sitter
        parser = get_tree_sitter_parser()
        assert parser is not None

        # Ripgrep (optional)
        searcher = get_ripgrep_searcher()
        # May be None if not installed

        # LSP
        lsp_mgr = get_lsp_manager()
        assert lsp_mgr is not None

        # Syntax highlighting
        highlighter = get_code_highlighter()
        assert highlighter is not None
        renderer = get_syntax_renderer()
        assert renderer is not None

        # Code Intelligence
        ci = get_code_intelligence()
        assert ci is not None

    def test_code_intelligence_no_crashes(self):
        """Test that CodeIntelligence methods don't crash."""
        ci = CodeIntelligence()

        # These should not raise exceptions even if components unavailable
        ci.search_code("test", directory="/tmp")
        ci.search_symbol("test", directory="/tmp")
        ci.find_functions(directory="/tmp")
        ci.find_classes(directory="/tmp")
        ci.find_todos(directory="/tmp")
        ci.highlight_code("x = 1", "python")
        ci.get_code_outline("test.py")
        ci.get_completions("test.py", 0, 0)
