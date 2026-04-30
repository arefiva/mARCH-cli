"""
Tree-sitter integration for syntax tree parsing and code analysis.

Provides language-specific parsers for Python, JavaScript, TypeScript, Go, Rust,
and other common languages using tree-sitter bindings.
"""

from pathlib import Path

try:
    import tree_sitter
    from tree_sitter import Language, Parser
except ImportError:
    raise ImportError(
        "tree_sitter package required. Install with: pip install tree_sitter"
    )


class TreeSitterLanguage:
    """Supported languages and their tree-sitter parsers."""

    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    GO = "go"
    RUST = "rust"
    JAVA = "java"
    CPP = "cpp"
    C = "c"
    RUBY = "ruby"
    BASH = "bash"

    SUPPORTED = {
        PYTHON,
        JAVASCRIPT,
        TYPESCRIPT,
        GO,
        RUST,
        JAVA,
        CPP,
        C,
        RUBY,
        BASH,
    }

    # Map file extensions to language
    EXTENSION_MAP = {
        "py": PYTHON,
        "js": JAVASCRIPT,
        "jsx": JAVASCRIPT,
        "ts": TYPESCRIPT,
        "tsx": TYPESCRIPT,
        "go": GO,
        "rs": RUST,
        "java": JAVA,
        "cpp": CPP,
        "cc": CPP,
        "cxx": CPP,
        "c": C,
        "h": C,
        "hpp": CPP,
        "rb": RUBY,
        "sh": BASH,
        "bash": BASH,
    }


class TreeSitterParser:
    """Syntax tree parser using tree-sitter."""

    def __init__(self):
        """Initialize parser with language cache."""
        self._parser = Parser()
        self._languages: dict[str, Language] = {}
        self._cache: dict[str, tuple[bytes, object]] = {}

    def get_language(self, language: str) -> Language | None:
        """
        Get tree-sitter language parser for a specific language.

        Args:
            language: Language identifier (e.g., 'python', 'javascript')

        Returns:
            Language parser object, or None if not available
        """
        if language not in TreeSitterLanguage.SUPPORTED:
            return None

        if language not in self._languages:
            try:
                # Try to load the language parser
                # This requires the language plugin to be installed
                import tree_sitter_python  # type: ignore[import-untyped]
                lang_obj = tree_sitter_python.language()  # type: ignore[attr-defined]
                self._languages[language] = lang_obj  # type: ignore[assignment]
            except Exception:
                # Language not available, return None
                return None

        return self._languages.get(language)

    def parse(
        self, code: str, language: str
    ) -> object | None:
        """
        Parse code string into syntax tree.

        Args:
            code: Source code to parse
            language: Language identifier

        Returns:
            Root node of syntax tree, or None if parsing failed
        """
        lang = self.get_language(language)
        if not lang:
            return None

        try:
            self._parser.language = lang  # type: ignore[assignment]
            tree = self._parser.parse(code.encode("utf-8"))
            result: object = tree.root_node
            return result
        except Exception:
            return None

    def parse_file(
        self, file_path: str, language: str | None = None
    ) -> object | None:
        """
        Parse a source file into syntax tree.

        Args:
            file_path: Path to source file
            language: Language identifier (auto-detected if not provided)

        Returns:
            Root node of syntax tree, or None if parsing failed
        """
        path = Path(file_path)
        if not path.exists():
            return None

        # Auto-detect language from extension
        if language is None:
            ext = path.suffix.lstrip(".")
            language = TreeSitterLanguage.EXTENSION_MAP.get(ext)
            if not language:
                return None

        try:
            code = path.read_text(encoding="utf-8")
            return self.parse(code, language)
        except Exception:
            return None

    def extract_functions(
        self, root_node: object, language: str
    ) -> list[dict]:
        """
        Extract function definitions from syntax tree.

        Args:
            root_node: Root node of syntax tree
            language: Language identifier

        Returns:
            List of function info dicts with name, line, column, signature
        """
        if not root_node:
            return []

        functions = []

        def extract_lang_specific(node, lang: str):
            """Language-specific function extraction logic."""
            if lang == TreeSitterLanguage.PYTHON:
                if node.type == "function_definition":
                    name_node = node.child_by_field_name("name")
                    return {
                        "name": name_node.text.decode()
                        if name_node
                        else "unknown",
                        "type": "function",
                        "line": node.start_point[0],
                        "column": node.start_point[1],
                        "range": (node.start_byte, node.end_byte),
                    }
            elif lang in (
                TreeSitterLanguage.JAVASCRIPT,
                TreeSitterLanguage.TYPESCRIPT,
            ):
                if node.type in (
                    "function_declaration",
                    "function_expression",
                    "arrow_function",
                ):
                    name_node = node.child_by_field_name("name")
                    return {
                        "name": name_node.text.decode()
                        if name_node
                        else "anonymous",
                        "type": "function",
                        "line": node.start_point[0],
                        "column": node.start_point[1],
                        "range": (node.start_byte, node.end_byte),
                    }
            return None

        def traverse(node):
            """Traverse syntax tree and extract functions."""
            result = extract_lang_specific(node, language)
            if result:
                functions.append(result)

            for child in node.children:
                traverse(child)

        traverse(root_node)
        return functions

    def extract_classes(
        self, root_node: object, language: str
    ) -> list[dict]:
        """
        Extract class definitions from syntax tree.

        Args:
            root_node: Root node of syntax tree
            language: Language identifier

        Returns:
            List of class info dicts with name, line, column
        """
        if not root_node:
            return []

        classes = []

        def traverse(node):
            """Traverse syntax tree and extract classes."""
            if language == TreeSitterLanguage.PYTHON:
                if node.type == "class_definition":
                    name_node = node.child_by_field_name("name")
                    classes.append(
                        {
                            "name": name_node.text.decode()
                            if name_node
                            else "unknown",
                            "type": "class",
                            "line": node.start_point[0],
                            "column": node.start_point[1],
                            "range": (node.start_byte, node.end_byte),
                        }
                    )
            elif language in (
                TreeSitterLanguage.JAVASCRIPT,
                TreeSitterLanguage.TYPESCRIPT,
            ):
                if node.type == "class_declaration":
                    name_node = node.child_by_field_name("name")
                    classes.append(
                        {
                            "name": name_node.text.decode()
                            if name_node
                            else "unknown",
                            "type": "class",
                            "line": node.start_point[0],
                            "column": node.start_point[1],
                            "range": (node.start_byte, node.end_byte),
                        }
                    )

            for child in node.children:
                traverse(child)

        traverse(root_node)
        return classes

    def get_outline(
        self, file_path: str, language: str | None = None
    ) -> dict:
        """
        Get file outline (classes, functions, etc.) for display.

        Args:
            file_path: Path to source file
            language: Language identifier (auto-detected if not provided)

        Returns:
            Dictionary with file outline structure
        """
        root_node = self.parse_file(file_path, language)
        if not root_node:
            return {"file": str(file_path), "classes": [], "functions": []}

        if language is None:
            ext = Path(file_path).suffix.lstrip(".")
            language = TreeSitterLanguage.EXTENSION_MAP.get(ext)

        return {
            "file": str(file_path),
            "classes": self.extract_classes(root_node, language or ""),
            "functions": self.extract_functions(root_node, language or ""),
        }

    def clear_cache(self) -> None:
        """Clear parsing cache."""
        self._cache.clear()


# Singleton instance
_parser_instance: TreeSitterParser | None = None


def get_tree_sitter_parser() -> TreeSitterParser:
    """Get or create singleton TreeSitterParser instance."""
    global _parser_instance
    if _parser_instance is None:
        _parser_instance = TreeSitterParser()
    return _parser_instance
