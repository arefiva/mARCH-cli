"""
Syntax highlighting for code display using Pygments and Rich.

Provides language-aware code highlighting with theme support for terminal display.
"""

from pathlib import Path

try:
    from pygments import highlight
    from pygments.formatters import TerminalFormatter, TerminalTrueColorFormatter
    from pygments.lexers import get_lexer_by_name, guess_lexer_for_filename
except ImportError:
    raise ImportError(
        "pygments package required. Install with: pip install pygments"
    )

try:
    from rich.console import Console
    from rich.syntax import Syntax
except ImportError:
    raise ImportError(
        "rich package required. Install with: pip install rich"
    )


class CodeHighlighter:
    """Syntax highlighter for code display."""

    # Language aliases
    LANGUAGE_ALIASES = {
        "py": "python",
        "js": "javascript",
        "ts": "typescript",
        "jsx": "jsx",
        "tsx": "tsx",
        "go": "go",
        "rs": "rust",
        "rb": "ruby",
        "java": "java",
        "cpp": "cpp",
        "c": "c",
        "h": "c",
        "hpp": "cpp",
        "bash": "bash",
        "sh": "bash",
        "yaml": "yaml",
        "yml": "yaml",
        "json": "json",
        "toml": "toml",
        "md": "markdown",
        "sql": "sql",
    }

    # Theme options
    THEME_LIGHT = "light"
    THEME_DARK = "dark"
    THEME_MONOKAI = "monokai"

    def __init__(
        self, theme: str = THEME_DARK, use_truecolor: bool = True
    ):
        """
        Initialize code highlighter.

        Args:
            theme: Color theme (light, dark, monokai)
            use_truecolor: Use 24-bit truecolor if available
        """
        self.theme = theme
        self.use_truecolor = use_truecolor
        self.console = Console()

    def highlight_code(
        self,
        code: str,
        language: str,
        line_numbers: bool = False,
        start_line: int = 1,
    ) -> str:
        """
        Highlight code string and return formatted output.

        Args:
            code: Source code to highlight
            language: Language identifier (py, js, etc.)
            line_numbers: Show line numbers
            start_line: Starting line number

        Returns:
            ANSI-colored code string
        """
        # Normalize language name
        lang = self.LANGUAGE_ALIASES.get(language, language)

        try:
            syntax = Syntax(
                code,
                lang,
                theme=self.theme,
                line_numbers=line_numbers,
                start_line=start_line,
            )
            # Get rendered text
            console_output = Console(
                force_terminal=True, legacy_windows=False
            )
            with console_output.capture() as capture:
                console_output.print(syntax)
            return str(capture.get())
        except Exception:
            # If highlighting fails, return plain code
            return code

    def highlight_file(
        self,
        file_path: str,
        language: str | None = None,
        line_numbers: bool = True,
        max_lines: int | None = None,
    ) -> str:
        """
        Highlight a source file.

        Args:
            file_path: Path to source file
            language: Language identifier (auto-detected if not provided)
            line_numbers: Show line numbers
            max_lines: Maximum lines to highlight

        Returns:
            ANSI-colored code string
        """
        path = Path(file_path)
        if not path.exists():
            return f"File not found: {file_path}"

        try:
            code = path.read_text(encoding="utf-8")
        except Exception as e:
            return f"Error reading file: {e}"

        # Auto-detect language from extension
        if language is None:
            ext = path.suffix.lstrip(".")
            language = self.LANGUAGE_ALIASES.get(
                ext, ext
            )

        # Limit lines if specified
        if max_lines:
            lines = code.split("\n")
            code = "\n".join(lines[:max_lines])
            if len(lines) > max_lines:
                code += f"\n... ({len(lines) - max_lines} more lines)"

        return self.highlight_code(code, language, line_numbers)

    def highlight_snippet(
        self,
        code: str,
        language: str,
        line_start: int = 1,
        line_end: int | None = None,
    ) -> str:
        """
        Highlight a snippet of code with context.

        Args:
            code: Source code
            language: Language identifier
            line_start: Starting line number for display
            line_end: Ending line number (for limiting display)

        Returns:
            ANSI-colored code string
        """
        lines = code.split("\n")

        # Handle line range
        if line_end and line_end < len(lines):
            lines = lines[: line_end - line_start + 1]

        snippet = "\n".join(lines)
        return self.highlight_code(
            snippet, language, line_numbers=True, start_line=line_start
        )

    def get_inline_highlight(self, code: str, language: str) -> str:
        """
        Get single-line highlighted code (no line numbers).

        Args:
            code: Source code (typically one line)
            language: Language identifier

        Returns:
            ANSI-colored code string
        """
        return self.highlight_code(code, language, line_numbers=False)


class SyntaxHighlightRenderer:
    """Rich-based syntax highlighting renderer."""

    def __init__(self, theme: str = "monokai"):
        """
        Initialize renderer.

        Args:
            theme: Rich theme name (monokai, dracula, fruity, etc.)
        """
        self.theme = theme
        self.console = Console()

    def render_file(
        self,
        file_path: str,
        language: str | None = None,
        line_numbers: bool = True,
        max_lines: int | None = None,
    ) -> None:
        """
        Render a file with syntax highlighting to console.

        Args:
            file_path: Path to source file
            language: Language identifier
            line_numbers: Show line numbers
            max_lines: Maximum lines to display
        """
        path = Path(file_path)
        if not path.exists():
            self.console.print(f"[red]File not found: {file_path}[/red]")
            return

        try:
            code = path.read_text(encoding="utf-8")
        except Exception as e:
            self.console.print(f"[red]Error reading file: {e}[/red]")
            return

        # Auto-detect language
        if language is None:
            ext = path.suffix.lstrip(".")
            language = CodeHighlighter.LANGUAGE_ALIASES.get(
                ext, ext
            )

        # Limit lines
        if max_lines:
            lines = code.split("\n")
            code = "\n".join(lines[:max_lines])

        try:
            syntax = Syntax(
                code,
                language,
                theme=self.theme,
                line_numbers=line_numbers,
                word_wrap=True,
            )
            self.console.print(syntax)
        except Exception:
            self.console.print(code)

    def render_snippet(
        self,
        code: str,
        language: str,
        line_start: int = 1,
        title: str | None = None,
    ) -> None:
        """
        Render a code snippet to console.

        Args:
            code: Source code
            language: Language identifier
            line_start: Starting line number for display
            title: Optional title to display above code
        """
        if title:
            self.console.print(f"[bold]{title}[/bold]")

        try:
            syntax = Syntax(
                code,
                language,
                theme=self.theme,
                line_numbers=True,
                start_line=line_start,
                word_wrap=True,
            )
            self.console.print(syntax)
        except Exception:
            self.console.print(code)

    def render_diff(
        self,
        old_code: str,
        new_code: str,
        language: str,
        context_lines: int = 3,
    ) -> None:
        """
        Render a code diff to console.

        Args:
            old_code: Original code
            new_code: New code
            language: Language identifier
            context_lines: Context lines around changes
        """
        import difflib

        old_lines = old_code.splitlines(keepends=True)
        new_lines = new_code.splitlines(keepends=True)

        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            lineterm="",
            n=context_lines,
        )

        for line in diff:
            line = line.rstrip("\n")
            if line.startswith("+++") or line.startswith("---"):
                self.console.print(f"[bold blue]{line}[/bold blue]")
            elif line.startswith("+"):
                self.console.print(f"[green]{line}[/green]")
            elif line.startswith("-"):
                self.console.print(f"[red]{line}[/red]")
            elif line.startswith("@@"):
                self.console.print(f"[yellow]{line}[/yellow]")
            else:
                self.console.print(line)


# Singleton instances
_highlighter_instance: CodeHighlighter | None = None
_renderer_instance: SyntaxHighlightRenderer | None = None


def get_code_highlighter() -> CodeHighlighter:
    """Get or create singleton CodeHighlighter instance."""
    global _highlighter_instance
    if _highlighter_instance is None:
        _highlighter_instance = CodeHighlighter()
    return _highlighter_instance


def get_syntax_renderer() -> SyntaxHighlightRenderer:
    """Get or create singleton SyntaxHighlightRenderer instance."""
    global _renderer_instance
    if _renderer_instance is None:
        _renderer_instance = SyntaxHighlightRenderer()
    return _renderer_instance
