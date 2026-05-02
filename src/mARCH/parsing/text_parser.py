"""
Multi-format text parsing.

Provides TextParser for parsing markdown, code blocks, JSON, and other text formats
with format detection and structure extraction.
"""

import re
import json
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum


class TextFormat(Enum):
    """Supported text formats."""

    MARKDOWN = "markdown"
    CODE_BLOCK = "code_block"
    JSON = "json"
    PLAIN_TEXT = "plain_text"
    YAML = "yaml"


@dataclass
class CodeBlock:
    """Represents a code block."""

    language: str
    code: str
    line_start: int = 0
    line_end: int = 0


@dataclass
class TextSection:
    """Represents a section of text."""

    heading: str
    level: int
    content: str
    start_line: int = 0
    end_line: int = 0


@dataclass
class MarkdownTree:
    """Represents markdown structure."""

    sections: list[TextSection] = field(default_factory=list)
    code_blocks: list[CodeBlock] = field(default_factory=list)


@dataclass
class ParsedText:
    """Result of text parsing."""

    format: TextFormat
    content: str
    sections: list[TextSection] = field(default_factory=list)
    code_blocks: list[CodeBlock] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    language: Optional[str] = None

    def get_sections(self) -> list[TextSection]:
        """Get all sections."""
        return self.sections

    def get_code_blocks(self) -> list[CodeBlock]:
        """Get all code blocks."""
        return self.code_blocks

    def to_plain_text(self) -> str:
        """Convert to plain text."""
        lines = []
        
        for section in self.sections:
            if section.heading:
                lines.append(f"{'#' * section.level} {section.heading}")
            lines.append(section.content)
        
        return "\n".join(lines)

    def to_markdown(self) -> str:
        """Convert to markdown."""
        if self.format == TextFormat.MARKDOWN:
            return self.content
        
        lines = []
        for section in self.sections:
            if section.heading:
                lines.append(f"{'#' * section.level} {section.heading}")
            lines.append(section.content)
        
        for code_block in self.code_blocks:
            lines.append(f"```{code_block.language}")
            lines.append(code_block.code)
            lines.append("```")
        
        return "\n".join(lines)


class TextParser:
    """
    Parser for multiple text formats.

    Detects format, extracts structure, and provides unified interface for parsing.
    """

    def __init__(self) -> None:
        """Initialize TextParser."""
        self._markdown_header_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
        self._code_block_pattern = re.compile(
            r'```(\w+)?\n(.*?)\n```',
            re.DOTALL
        )
        self._code_inline_pattern = re.compile(r'`([^`]+)`')

    def detect_format(self, text: str) -> TextFormat:
        """
        Detect text format automatically.

        Args:
            text: Text to analyze

        Returns:
            Detected TextFormat
        """
        if not text:
            return TextFormat.PLAIN_TEXT

        # Try JSON
        try:
            json.loads(text)
            return TextFormat.JSON
        except (json.JSONDecodeError, ValueError):
            pass

        # Check for markdown patterns
        if re.search(self._markdown_header_pattern, text):
            return TextFormat.MARKDOWN

        # Check for code blocks
        if re.search(self._code_block_pattern, text):
            return TextFormat.CODE_BLOCK

        # Check for YAML patterns
        if text.strip().startswith("---") or re.search(r'^[\w-]+:', text, re.MULTILINE):
            return TextFormat.YAML

        return TextFormat.PLAIN_TEXT

    def parse(
        self,
        text: str,
        format: Optional[TextFormat] = None,
    ) -> ParsedText:
        """
        Parse text with automatic or specified format.

        Args:
            text: Text to parse
            format: Optional format to force (auto-detect if None)

        Returns:
            ParsedText with extracted structure
        """
        if format is None:
            format = self.detect_format(text)

        if format == TextFormat.MARKDOWN:
            return self._parse_markdown(text)
        elif format == TextFormat.CODE_BLOCK:
            return self._parse_code_blocks(text)
        elif format == TextFormat.JSON:
            return self._parse_json(text)
        elif format == TextFormat.YAML:
            return self._parse_yaml(text)
        else:
            return ParsedText(
                format=TextFormat.PLAIN_TEXT,
                content=text,
            )

    def _parse_markdown(self, text: str) -> ParsedText:
        """Parse markdown format."""
        sections = []
        code_blocks = self.extract_code_blocks(text)
        
        # Extract headers and content
        lines = text.split("\n")
        current_section = None
        content_lines = []

        for line in lines:
            header_match = re.match(r'^(#{1,6})\s+(.+)$', line)
            
            if header_match:
                # Save previous section
                if current_section or content_lines:
                    if current_section is None:
                        current_section = TextSection(
                            heading="",
                            level=0,
                            content="\n".join(content_lines),
                        )
                    else:
                        current_section.content = "\n".join(content_lines)
                    sections.append(current_section)
                
                # Start new section
                level = len(header_match.group(1))
                heading = header_match.group(2)
                current_section = TextSection(
                    heading=heading,
                    level=level,
                    content="",
                )
                content_lines = []
            else:
                content_lines.append(line)

        # Save last section
        if current_section or content_lines:
            if current_section is None:
                current_section = TextSection(
                    heading="",
                    level=0,
                    content="\n".join(content_lines),
                )
            else:
                current_section.content = "\n".join(content_lines)
            sections.append(current_section)

        return ParsedText(
            format=TextFormat.MARKDOWN,
            content=text,
            sections=sections,
            code_blocks=code_blocks,
        )

    def _parse_code_blocks(self, text: str) -> ParsedText:
        """Parse code block format."""
        code_blocks = self.extract_code_blocks(text)
        
        return ParsedText(
            format=TextFormat.CODE_BLOCK,
            content=text,
            code_blocks=code_blocks,
        )

    def _parse_json(self, text: str) -> ParsedText:
        """Parse JSON format."""
        try:
            data = json.loads(text)
            return ParsedText(
                format=TextFormat.JSON,
                content=text,
                metadata={"parsed": data},
            )
        except json.JSONDecodeError as e:
            return ParsedText(
                format=TextFormat.JSON,
                content=text,
                metadata={"error": str(e)},
            )

    def _parse_yaml(self, text: str) -> ParsedText:
        """Parse YAML format (basic)."""
        # Basic YAML parsing without external library
        metadata = {}
        
        lines = text.split("\n")
        for line in lines:
            if ":" in line:
                key, value = line.split(":", 1)
                metadata[key.strip()] = value.strip()

        return ParsedText(
            format=TextFormat.YAML,
            content=text,
            metadata=metadata,
        )

    def extract_code_blocks(self, text: str) -> list[CodeBlock]:
        """
        Extract all code blocks from text.

        Args:
            text: Text containing code blocks

        Returns:
            List of CodeBlock instances
        """
        code_blocks = []
        matches = re.finditer(self._code_block_pattern, text)

        for match in matches:
            language = match.group(1) or "text"
            code = match.group(2)
            
            # Calculate line numbers
            line_start = text[:match.start()].count("\n")
            line_end = text[:match.end()].count("\n")

            code_blocks.append(
                CodeBlock(
                    language=language,
                    code=code,
                    line_start=line_start,
                    line_end=line_end,
                )
            )

        return code_blocks

    def extract_markdown_structure(self, text: str) -> MarkdownTree:
        """
        Extract markdown structure.

        Args:
            text: Markdown text

        Returns:
            MarkdownTree with structure information
        """
        parsed = self._parse_markdown(text)
        return MarkdownTree(
            sections=parsed.sections,
            code_blocks=parsed.code_blocks,
        )

    def extract_metadata(self, text: str) -> dict[str, Any]:
        """
        Extract metadata from text (frontmatter, comments).

        Args:
            text: Text to extract metadata from

        Returns:
            Dictionary of metadata
        """
        metadata = {}

        # Look for frontmatter (YAML between ---)
        frontmatter_match = re.match(r'^---\n(.*?)\n---', text, re.DOTALL)
        if frontmatter_match:
            lines = frontmatter_match.group(1).split("\n")
            for line in lines:
                if ":" in line:
                    key, value = line.split(":", 1)
                    metadata[key.strip()] = value.strip()

        # Count code blocks
        code_blocks = self.extract_code_blocks(text)
        metadata["code_block_count"] = len(code_blocks)

        # Count headers
        headers = re.findall(self._markdown_header_pattern, text)
        metadata["header_count"] = len(headers)

        return metadata

    def extract_sections_by_level(self, text: str, level: int) -> list[TextSection]:
        """
        Extract sections at specific heading level.

        Args:
            text: Markdown text
            level: Heading level (1-6)

        Returns:
            List of TextSection at specified level
        """
        parsed = self._parse_markdown(text)
        return [s for s in parsed.sections if s.level == level]
