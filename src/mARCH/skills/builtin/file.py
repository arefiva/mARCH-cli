"""File read and write skills."""

import logging
from pathlib import Path
from typing import Any, Dict

from ..registry import Skill

logger = logging.getLogger(__name__)


class FileReadSkill(Skill):
    """Reads file contents."""

    name = "file_read"
    version = "1.0.0"
    description = "Read file contents with optional encoding detection"

    async def execute(
        self, params: Dict[str, Any], context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Read a file.

        Args:
            params: Parameters including 'path' and optional 'encoding'
            context: Optional execution context

        Returns:
            Result with file contents
        """
        file_path = params.get("path")
        if not file_path:
            raise ValueError("Missing required parameter: path")

        encoding = params.get("encoding", "utf-8")

        try:
            filepath = Path(file_path)

            if not filepath.exists():
                raise FileNotFoundError(f"File not found: {file_path}")

            if not filepath.is_file():
                raise ValueError(f"Path is not a file: {file_path}")

            content = filepath.read_text(encoding=encoding)

            return {
                "path": str(filepath),
                "size": filepath.stat().st_size,
                "content": content,
                "encoding": encoding,
            }
        except Exception as e:
            logger.error(f"Failed to read file: {e}")
            raise

    def validate_params(self, params: Dict[str, Any]) -> bool:
        """Validate parameters."""
        return "path" in params

    def get_schema(self) -> Dict[str, Any]:
        """Get JSON schema."""
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to file to read",
                },
                "encoding": {
                    "type": "string",
                    "description": "File encoding",
                    "default": "utf-8",
                },
            },
            "required": ["path"],
        }


class FileWriteSkill(Skill):
    """Writes file contents."""

    name = "file_write"
    version = "1.0.0"
    description = "Write contents to a file safely"

    async def execute(
        self, params: Dict[str, Any], context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Write to a file.

        Args:
            params: Parameters including 'path', 'content', and optional settings
            context: Optional execution context

        Returns:
            Result with write status
        """
        file_path = params.get("path")
        content = params.get("content")

        if not file_path:
            raise ValueError("Missing required parameter: path")
        if content is None:
            raise ValueError("Missing required parameter: content")

        encoding = params.get("encoding", "utf-8")
        create_dirs = params.get("create_dirs", True)

        try:
            filepath = Path(file_path)

            # Create parent directories if needed
            if create_dirs:
                filepath.parent.mkdir(parents=True, exist_ok=True)

            # Write content
            filepath.write_text(content, encoding=encoding)

            return {
                "path": str(filepath),
                "size": len(content),
                "encoding": encoding,
                "success": True,
            }
        except Exception as e:
            logger.error(f"Failed to write file: {e}")
            raise

    def validate_params(self, params: Dict[str, Any]) -> bool:
        """Validate parameters."""
        return "path" in params and "content" in params

    def get_schema(self) -> Dict[str, Any]:
        """Get JSON schema."""
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to file to write",
                },
                "content": {
                    "type": "string",
                    "description": "Content to write",
                },
                "encoding": {
                    "type": "string",
                    "description": "File encoding",
                    "default": "utf-8",
                },
                "create_dirs": {
                    "type": "boolean",
                    "description": "Create parent directories if needed",
                    "default": True,
                },
            },
            "required": ["path", "content"],
        }
