"""
Code Intelligence module - unified interface for syntax parsing, code search, and LSP.

Combines tree-sitter parsing, ripgrep search, LSP language servers, and syntax
highlighting to provide comprehensive code intelligence features.
"""


from .lsp_client import CompletionItem, Location, get_lsp_manager
from .ripgrep_search import SearchMatch, get_ripgrep_searcher
from .syntax_highlight import (
    get_code_highlighter,
    get_syntax_renderer,
)
from .tree_sitter import TreeSitterLanguage, get_tree_sitter_parser


class CodeIntelligence:
    """Unified code intelligence interface."""

    def __init__(self):
        """Initialize code intelligence components."""
        self.parser = get_tree_sitter_parser()
        self.searcher = get_ripgrep_searcher()
        self.lsp_manager = get_lsp_manager()
        self.highlighter = get_code_highlighter()
        self.renderer = get_syntax_renderer()

    def find_symbol_definition(
        self, file_path: str, line: int, character: int
    ) -> Location | None:
        """
        Find definition of symbol at given position.

        Args:
            file_path: Path to source file
            line: Line number (0-indexed)
            character: Character offset (0-indexed)

        Returns:
            Location of symbol definition, or None if not found
        """
        # Try LSP first (most accurate)
        from pathlib import Path

        ext = Path(file_path).suffix.lstrip(".")
        language = TreeSitterLanguage.EXTENSION_MAP.get(ext)

        if language:
            client = self.lsp_manager.get_client(language)
            if client:
                return client.goto_definition(file_path, line, character)

        return None

    def find_references(
        self, file_path: str, line: int, character: int
    ) -> list[Location]:
        """
        Find all references to symbol at given position.

        Args:
            file_path: Path to source file
            line: Line number (0-indexed)
            character: Character offset (0-indexed)

        Returns:
            List of locations where symbol is referenced
        """
        from pathlib import Path

        ext = Path(file_path).suffix.lstrip(".")
        language = TreeSitterLanguage.EXTENSION_MAP.get(ext)

        if language:
            client = self.lsp_manager.get_client(language)
            if client:
                return client.find_references(file_path, line, character)

        return []

    def search_code(
        self,
        pattern: str,
        directory: str = ".",
        file_types: list[str] | None = None,
    ) -> list[SearchMatch]:
        """
        Search for pattern in code files.

        Args:
            pattern: Search pattern (regex)
            directory: Root directory to search
            file_types: File types to search (e.g., ['py', 'js'])

        Returns:
            List of matches
        """
        if not self.searcher:
            return []

        return self.searcher.search(
            pattern, directory=directory, file_types=file_types
        )

    def search_symbol(
        self, symbol: str, directory: str = "."
    ) -> list[SearchMatch]:
        """
        Search for symbol references (word boundaries).

        Args:
            symbol: Symbol name to search for
            directory: Root directory to search

        Returns:
            List of matches
        """
        if not self.searcher:
            return []

        return self.searcher.search_symbol(symbol, directory=directory)

    def find_functions(
        self, directory: str = ".", language: str = "py"
    ) -> list[SearchMatch]:
        """
        Find function definitions.

        Args:
            directory: Root directory to search
            language: Language to search

        Returns:
            List of function definitions
        """
        if not self.searcher:
            return []

        return self.searcher.find_functions(
            directory=directory, language=language
        )

    def find_classes(
        self, directory: str = ".", language: str = "py"
    ) -> list[SearchMatch]:
        """
        Find class definitions.

        Args:
            directory: Root directory to search
            language: Language to search

        Returns:
            List of class definitions
        """
        if not self.searcher:
            return []

        return self.searcher.find_classes(
            directory=directory, language=language
        )

    def find_todos(self, directory: str = ".") -> list[SearchMatch]:
        """
        Find TODO/FIXME comments.

        Args:
            directory: Root directory to search

        Returns:
            List of TODO matches
        """
        if not self.searcher:
            return []

        return self.searcher.find_todos(directory=directory)

    def get_code_outline(
        self, file_path: str
    ) -> dict:
        """
        Get file outline (classes and functions).

        Args:
            file_path: Path to source file

        Returns:
            Dictionary with file outline
        """
        return self.parser.get_outline(file_path)

    def highlight_code(
        self, code: str, language: str, line_numbers: bool = False
    ) -> str:
        """
        Highlight code with syntax colors.

        Args:
            code: Source code
            language: Language identifier
            line_numbers: Show line numbers

        Returns:
            ANSI-colored code string
        """
        if line_numbers:
            return self.highlighter.highlight_code(
                code, language, line_numbers=True
            )
        else:
            return self.highlighter.get_inline_highlight(code, language)

    def get_completions(
        self, file_path: str, line: int, character: int
    ) -> list[CompletionItem]:
        """
        Get code completions at given position.

        Args:
            file_path: Path to source file
            line: Line number (0-indexed)
            character: Character offset (0-indexed)

        Returns:
            List of completion items
        """
        from pathlib import Path

        ext = Path(file_path).suffix.lstrip(".")
        language = TreeSitterLanguage.EXTENSION_MAP.get(ext)

        if language:
            client = self.lsp_manager.get_client(language)
            if client:
                return client.complete(file_path, line, character)

        return []

    def render_file(
        self, file_path: str, max_lines: int | None = None
    ) -> None:
        """
        Display highlighted file in terminal.

        Args:
            file_path: Path to source file
            max_lines: Maximum lines to display
        """
        self.renderer.render_file(file_path, max_lines=max_lines)

    def render_snippet(
        self, code: str, language: str, title: str | None = None
    ) -> None:
        """
        Display highlighted code snippet in terminal.

        Args:
            code: Source code
            language: Language identifier
            title: Optional title
        """
        self.renderer.render_snippet(code, language, title=title)

    def shutdown(self) -> None:
        """Shutdown all code intelligence components."""
        self.lsp_manager.shutdown_all()


# Singleton instance
_code_intelligence_instance: CodeIntelligence | None = None


def get_code_intelligence() -> CodeIntelligence:
    """Get or create singleton CodeIntelligence instance."""
    global _code_intelligence_instance
    if _code_intelligence_instance is None:
        _code_intelligence_instance = CodeIntelligence()
    return _code_intelligence_instance
