"""
File aggregation and summarization for multi-file analysis.

Provides capabilities to read multiple files from a directory, extract summaries,
detect metadata, and prepare structured data for pattern extraction and analysis.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class FileSummary:
    """Summary of an analyzed file."""

    path: str
    filename: str
    content: str
    summary: str  # 100-200 char condensed summary
    key_phrases: list[str] = field(default_factory=list)  # Top 5-10 keywords
    metadata: dict = field(default_factory=dict)  # title, date, tags, etc.
    size_bytes: int = 0
    is_valid: bool = True
    error_message: Optional[str] = None

    @property
    def relative_path(self) -> str:
        """Get path relative to base directory."""
        return self.path


class FileAggregator:
    """Aggregates and summarizes multiple files from a directory.

    Handles:
    - Directory scanning with glob patterns
    - File reading and encoding handling
    - Content summarization
    - Metadata extraction
    - Error recovery and partial failures
    """

    def __init__(self, max_files: int = 100, max_file_size_mb: int = 10):
        """Initialize FileAggregator.

        Args:
            max_files: Maximum number of files to read (default: 100)
            max_file_size_mb: Maximum file size in MB (default: 10MB)
        """
        self.max_files = max_files
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024
        self.encoding_fallback_chain = ["utf-8", "utf-8-sig", "latin-1", "ascii"]

    async def aggregate_files(
        self,
        directory: str | Path,
        pattern: str = "*.md",
        base_dir: Optional[str | Path] = None,
    ) -> list[FileSummary]:
        """Aggregate files from a directory.

        Args:
            directory: Directory to scan
            pattern: File glob pattern (e.g., "*.md", "**/*.txt")
            base_dir: Base directory for relative paths (defaults to directory)

        Returns:
            List of FileSummary objects
        """
        directory = Path(directory)
        base_dir = Path(base_dir or directory)

        if not directory.exists():
            logger.warning(f"Directory does not exist: {directory}")
            return []

        # Find matching files
        files = sorted(directory.glob(pattern))[: self.max_files]
        if not files:
            logger.info(f"No files matching pattern '{pattern}' in {directory}")
            return []

        logger.info(f"Found {len(files)} files matching pattern '{pattern}'")

        # Read files concurrently
        tasks = [self._read_and_summarize_file(f, base_dir) for f in files]
        summaries = await asyncio.gather(*tasks, return_exceptions=False)

        # Filter out None values
        return [s for s in summaries if s is not None]

    async def _read_and_summarize_file(
        self, file_path: Path, base_dir: Path
    ) -> Optional[FileSummary]:
        """Read and summarize a single file.

        Args:
            file_path: Path to file
            base_dir: Base directory for relative paths

        Returns:
            FileSummary or None if error
        """
        try:
            # Check file size
            size = file_path.stat().st_size
            if size > self.max_file_size_bytes:
                return FileSummary(
                    path=str(file_path.relative_to(base_dir)),
                    filename=file_path.name,
                    content="",
                    summary="[File too large]",
                    is_valid=False,
                    error_message=f"File exceeds max size: {size} bytes",
                    size_bytes=size,
                )

            # Read file with encoding fallback
            content = None
            for encoding in self.encoding_fallback_chain:
                try:
                    content = file_path.read_text(encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue

            if content is None:
                return FileSummary(
                    path=str(file_path.relative_to(base_dir)),
                    filename=file_path.name,
                    content="",
                    summary="[Unable to decode]",
                    is_valid=False,
                    error_message="Could not decode file with any supported encoding",
                    size_bytes=size,
                )

            # Extract metadata and create summary
            summary = self._create_summary(content)
            metadata = self._extract_metadata(file_path, content)
            key_phrases = self._extract_key_phrases(content)

            return FileSummary(
                path=str(file_path.relative_to(base_dir)),
                filename=file_path.name,
                content=content,
                summary=summary,
                key_phrases=key_phrases,
                metadata=metadata,
                size_bytes=size,
                is_valid=True,
            )

        except Exception as e:
            logger.warning(f"Error reading {file_path}: {e}")
            return FileSummary(
                path=str(file_path.relative_to(base_dir)),
                filename=file_path.name,
                content="",
                summary="[Error reading file]",
                is_valid=False,
                error_message=str(e),
            )

    def _create_summary(self, content: str, max_length: int = 200) -> str:
        """Create a brief summary of file content.

        Args:
            content: File content
            max_length: Maximum summary length

        Returns:
            Summary string
        """
        # For markdown, try to extract title and first paragraph
        lines = content.split("\n")

        # Look for title (# heading or YAML front matter title)
        title = ""
        start_idx = 0

        if lines and lines[0].strip().startswith("---"):
            # YAML front matter
            for i, line in enumerate(lines[1:], 1):
                if line.strip().startswith("title:"):
                    title = line.split("title:", 1)[1].strip().strip('"\'')
                    break
                if line.strip().startswith("---"):
                    start_idx = i + 1
                    break

        # Look for first heading
        if not title:
            for line in lines[start_idx:]:
                if line.startswith("#"):
                    title = line.lstrip("#").strip()
                    break

        # Extract first non-empty paragraph
        paragraph = ""
        for line in lines[start_idx:]:
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and not stripped.startswith(">"):
                paragraph = stripped
                break

        # Combine
        summary = " | ".join(filter(None, [title, paragraph]))
        if len(summary) > max_length:
            summary = summary[: max_length - 3] + "..."

        return summary or content[:max_length]

    def _extract_metadata(self, file_path: Path, content: str) -> dict:
        """Extract metadata from file.

        Args:
            file_path: Path to file
            content: File content

        Returns:
            Metadata dictionary
        """
        metadata = {
            "filename": file_path.name,
            "extension": file_path.suffix,
            "size_kb": file_path.stat().st_size / 1024,
            "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
        }

        # Try to extract YAML front matter
        if content.startswith("---"):
            lines = content.split("\n")
            for i, line in enumerate(lines[1:], 1):
                if line.strip().startswith("---"):
                    break
                if ":" in line:
                    key, value = line.split(":", 1)
                    metadata[key.strip().lower()] = value.strip().strip('"\'')

        return metadata

    def _extract_key_phrases(self, content: str, count: int = 10) -> list[str]:
        """Extract key phrases from content.

        Simple approach: split by whitespace, filter stop words, count frequency.

        Args:
            content: File content
            count: Number of key phrases to extract

        Returns:
            List of key phrases
        """
        # Common stop words
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "is", "are", "be", "been", "being", "have", "has", "had",
            "do", "does", "did", "will", "would", "could", "should", "may", "might",
            "can", "this", "that", "these", "those", "i", "you", "he", "she", "it",
            "we", "they", "what", "which", "who", "when", "where", "why", "how",
        }

        # Extract words
        import re

        words = re.findall(r"\b[a-z]+\b", content.lower())
        word_freq = {}

        for word in words:
            if len(word) > 3 and word not in stop_words:
                word_freq[word] = word_freq.get(word, 0) + 1

        # Sort by frequency
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_words[:count]]


def aggregate_files_sync(
    directory: str | Path,
    pattern: str = "*.md",
    base_dir: Optional[str | Path] = None,
    max_files: int = 100,
) -> list[FileSummary]:
    """Synchronous wrapper for aggregating files.

    Convenience function for synchronous code.

    Args:
        directory: Directory to scan
        pattern: File glob pattern
        base_dir: Base directory for relative paths
        max_files: Maximum files to process

    Returns:
        List of FileSummary objects
    """
    aggregator = FileAggregator(max_files=max_files)
    return asyncio.run(aggregator.aggregate_files(directory, pattern, base_dir))
