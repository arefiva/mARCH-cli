"""
String manipulation and transformation utilities.

Provides StringTransform for case conversion, normalization, and TextFormatter
for template-based formatting.
"""

import re
import textwrap
from enum import Enum
from typing import Optional


class CaseStyle(Enum):
    """String case styles."""

    CAMEL_CASE = "camelCase"
    SNAKE_CASE = "snake_case"
    KEBAB_CASE = "kebab-case"
    PASCAL_CASE = "PascalCase"
    CONSTANT_CASE = "CONSTANT_CASE"
    SENTENCE_CASE = "Sentence case"


class StringTransform:
    """
    String manipulation utilities for case conversion and normalization.
    """

    @staticmethod
    def to_camel_case(text: str) -> str:
        """
        Convert string to camelCase.

        Args:
            text: String to convert

        Returns:
            camelCase string
        """
        # Split on various delimiters
        parts = re.split(r'[-_\s]+', text.strip())
        if not parts:
            return text

        # First part is lowercase, rest are capitalized
        result = parts[0].lower()
        for part in parts[1:]:
            if part:
                result += part[0].upper() + part[1:].lower()

        return result

    @staticmethod
    def to_snake_case(text: str) -> str:
        """
        Convert string to snake_case.

        Args:
            text: String to convert

        Returns:
            snake_case string
        """
        # Insert underscore before uppercase letters
        text = re.sub(r'(?<!^)(?=[A-Z])', '_', text)
        # Replace hyphens and spaces with underscores
        text = re.sub(r'[-\s]+', '_', text)
        return text.lower()

    @staticmethod
    def to_kebab_case(text: str) -> str:
        """
        Convert string to kebab-case.

        Args:
            text: String to convert

        Returns:
            kebab-case string
        """
        # Convert to snake_case first, then replace underscores with hyphens
        snake = StringTransform.to_snake_case(text)
        return snake.replace("_", "-")

    @staticmethod
    def to_pascal_case(text: str) -> str:
        """
        Convert string to PascalCase.

        Args:
            text: String to convert

        Returns:
            PascalCase string
        """
        # Split on delimiters
        parts = re.split(r'[-_\s]+', text.strip())
        return "".join(part[0].upper() + part[1:].lower() for part in parts if part)

    @staticmethod
    def to_constant_case(text: str) -> str:
        """
        Convert string to CONSTANT_CASE.

        Args:
            text: String to convert

        Returns:
            CONSTANT_CASE string
        """
        return StringTransform.to_snake_case(text).upper()

    @staticmethod
    def to_sentence_case(text: str) -> str:
        """
        Convert string to Sentence case.

        Args:
            text: String to convert

        Returns:
            Sentence case string
        """
        # Remove extra whitespace and convert to lowercase
        text = " ".join(text.split()).lower()
        # Capitalize first letter
        if text:
            text = text[0].upper() + text[1:]
        return text

    @staticmethod
    def convert_case(text: str, from_style: CaseStyle, to_style: CaseStyle) -> str:
        """
        Convert between case styles.

        Args:
            text: String to convert
            from_style: Source case style
            to_style: Target case style

        Returns:
            Converted string
        """
        if from_style == to_style:
            return text

        case_map = {
            CaseStyle.CAMEL_CASE: StringTransform.to_camel_case,
            CaseStyle.SNAKE_CASE: StringTransform.to_snake_case,
            CaseStyle.KEBAB_CASE: StringTransform.to_kebab_case,
            CaseStyle.PASCAL_CASE: StringTransform.to_pascal_case,
            CaseStyle.CONSTANT_CASE: StringTransform.to_constant_case,
            CaseStyle.SENTENCE_CASE: StringTransform.to_sentence_case,
        }

        converter = case_map.get(to_style)
        if converter:
            return converter(text)
        return text

    @staticmethod
    def normalize(text: str, remove_special: bool = False) -> str:
        """
        Normalize text.

        Args:
            text: Text to normalize
            remove_special: Remove special characters if True

        Returns:
            Normalized text
        """
        # Collapse whitespace
        text = " ".join(text.split())

        if remove_special:
            # Remove non-alphanumeric characters (except spaces)
            text = re.sub(r'[^a-zA-Z0-9\s]', '', text)

        return text

    @staticmethod
    def pluralize(word: str, count: int) -> str:
        """
        Pluralize a word based on count.

        Args:
            word: Word to pluralize
            count: Count for pluralization

        Returns:
            Pluralized word (or singular if count == 1)
        """
        if count == 1:
            return word

        # Simple pluralization rules
        if word.endswith("y"):
            return word[:-1] + "ies"
        elif word.endswith("s") or word.endswith("x") or word.endswith("z"):
            return word + "es"
        elif word.endswith("o"):
            return word + "es"
        else:
            return word + "s"

    @staticmethod
    def truncate(text: str, length: int, suffix: str = "...") -> str:
        """
        Truncate text to specified length.

        Args:
            text: Text to truncate
            length: Maximum length
            suffix: Suffix to add if truncated

        Returns:
            Truncated text
        """
        if len(text) <= length:
            return text

        return text[:length - len(suffix)] + suffix

    @staticmethod
    def indent(text: str, spaces: int = 4) -> str:
        """
        Indent text.

        Args:
            text: Text to indent
            spaces: Number of spaces to indent

        Returns:
            Indented text
        """
        indent_str = " " * spaces
        lines = text.split("\n")
        return "\n".join(indent_str + line for line in lines)

    @staticmethod
    def reverse(text: str) -> str:
        """Reverse text."""
        return text[::-1]

    @staticmethod
    def repeat(text: str, times: int) -> str:
        """Repeat text multiple times."""
        return text * times

    @staticmethod
    def strip_ansi(text: str) -> str:
        """Remove ANSI escape codes from text."""
        ansi_pattern = re.compile(r'\x1b\[[0-9;]*m')
        return ansi_pattern.sub('', text)


class TextFormatter:
    """
    Formats text using templates and keyword substitution.
    """

    @staticmethod
    def format(template: str, **kwargs) -> str:
        """
        Format template with keyword arguments.

        Args:
            template: Template string with {placeholders}
            **kwargs: Keyword arguments for substitution

        Returns:
            Formatted string

        Raises:
            KeyError: If required placeholder is missing
        """
        return template.format(**kwargs)

    @staticmethod
    def format_safe(template: str, **kwargs) -> Optional[str]:
        """
        Format template with error handling.

        Args:
            template: Template string
            **kwargs: Keyword arguments

        Returns:
            Formatted string or None if formatting fails
        """
        try:
            return TextFormatter.format(template, **kwargs)
        except (KeyError, ValueError, AttributeError):
            return None

    @staticmethod
    def format_with_defaults(
        template: str,
        defaults: dict,
        **kwargs
    ) -> str:
        """
        Format template with default values.

        Args:
            template: Template string
            defaults: Default values for placeholders
            **kwargs: Override values

        Returns:
            Formatted string
        """
        merged = {**defaults, **kwargs}
        return template.format(**merged)

    @staticmethod
    def wrap(text: str, width: int = 80) -> str:
        """
        Wrap text to specified width.

        Args:
            text: Text to wrap
            width: Line width

        Returns:
            Wrapped text
        """
        return textwrap.fill(text, width=width)

    @staticmethod
    def wrap_paragraphs(text: str, width: int = 80) -> str:
        """
        Wrap text preserving paragraphs.

        Args:
            text: Text to wrap (paragraphs separated by blank lines)
            width: Line width

        Returns:
            Wrapped text
        """
        paragraphs = text.split("\n\n")
        wrapped = [textwrap.fill(p, width=width) for p in paragraphs]
        return "\n\n".join(wrapped)

    @staticmethod
    def center(text: str, width: int = 80, fillchar: str = " ") -> str:
        """
        Center text.

        Args:
            text: Text to center
            width: Total width
            fillchar: Character to fill with

        Returns:
            Centered text
        """
        return text.center(width, fillchar)

    @staticmethod
    def pad(text: str, width: int, side: str = "both", fillchar: str = " ") -> str:
        """
        Pad text.

        Args:
            text: Text to pad
            width: Total width
            side: "left", "right", or "both"
            fillchar: Character to fill with

        Returns:
            Padded text
        """
        if side == "left":
            return text.ljust(width, fillchar)
        elif side == "right":
            return text.rjust(width, fillchar)
        else:  # both
            return text.center(width, fillchar)
