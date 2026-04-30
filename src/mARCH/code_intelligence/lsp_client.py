"""
Language Server Protocol (LSP) client for IDE-like code intelligence.

Provides communication with LSP servers (e.g., pylsp, typescript-language-server)
for features like goto-definition, find-references, hover documentation, completions.
"""

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class Position:
    """LSP position (line, character)."""

    line: int
    character: int


@dataclass
class Range:
    """LSP range (start and end positions)."""

    start: Position
    end: Position


@dataclass
class Location:
    """LSP location (file URI and range)."""

    uri: str
    range: Range


@dataclass
class Diagnostic:
    """LSP diagnostic (error/warning in code)."""

    range: Range
    message: str
    severity: int  # 1=error, 2=warning, 3=info, 4=hint
    code: str | None = None
    source: str | None = None


@dataclass
class CompletionItem:
    """LSP completion item."""

    label: str
    kind: int  # CompletionItemKind
    detail: str | None = None
    documentation: str | None = None
    insert_text: str | None = None


@dataclass
class HoverInfo:
    """Hover documentation information."""

    language: str
    value: str


class LSPClient:
    """Language Server Protocol client."""

    def __init__(self, server_cmd: list[str], root_path: str = "."):
        """
        Initialize LSP client connected to a language server.

        Args:
            server_cmd: Command to start LSP server (e.g., ['pylsp'])
            root_path: Root directory for workspace
        """
        self.server_cmd = server_cmd
        self.root_path = str(Path(root_path).resolve())
        self.process: subprocess.Popen | None = None
        self.message_id = 0
        self._connect()

    def _connect(self) -> None:
        """Start LSP server subprocess."""
        try:
            self.process = subprocess.Popen(
                self.server_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
        except FileNotFoundError:
            raise RuntimeError(
                f"LSP server not found: {self.server_cmd[0]}. "
                "Install the language server and ensure it's in PATH."
            )

    def _send_message(
        self, method: str, params: dict | None = None
    ) -> dict:
        """
        Send LSP message to server and receive response.

        Args:
            method: LSP method name (e.g., 'initialize', 'textDocument/definition')
            params: Method parameters

        Returns:
            LSP response object
        """
        if not self.process or not self.process.stdin:
            return {}

        self.message_id += 1
        message: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": self.message_id,
            "method": method,
        }
        if params:
            message["params"] = params

        content = json.dumps(message)
        request = (
            f"Content-Length: {len(content)}\r\n"
            f"Content-Type: application/vnd-json;charset=utf8\r\n"
            f"\r\n{content}"
        )

        try:
            if self.process and self.process.stdin and self.process.stdout:
                self.process.stdin.write(request)
                self.process.stdin.flush()

                # Read response (simplified - just read first response)
                response_text = ""
                while True:
                    line = self.process.stdout.readline()
                    if not line:
                        break
                    response_text += line
                    if "\r\n\r\n" in response_text:
                        # Got complete header, try to parse
                        break

                if response_text:
                    try:
                        result: dict[Any, Any] = json.loads(response_text.split("\r\n\r\n", 1)[-1])
                        return result
                    except json.JSONDecodeError:
                        return {}

        except Exception:
            pass

        return {}

    def initialize(self, client_info: str | None = None) -> bool:
        """
        Initialize LSP connection with server.

        Args:
            client_info: Client name for server

        Returns:
            True if initialization succeeded
        """
        response = self._send_message(
            "initialize",
            {
                "processId": None,
                "rootPath": self.root_path,
                "rootUri": f"file://{self.root_path}",
                "capabilities": {},
                "clientInfo": {"name": client_info or "march-cli"},
            },
        )
        return "result" in response

    def shutdown(self) -> None:
        """Shutdown LSP connection."""
        if self.process:
            try:
                self._send_message("shutdown")
                self.process.terminate()
                self.process.wait(timeout=5)
            except Exception:
                if self.process:
                    self.process.kill()

    def goto_definition(
        self, file_path: str, line: int, character: int
    ) -> Location | None:
        """
        Go to definition of symbol at position.

        Args:
            file_path: File URI or path
            line: Line number (0-indexed)
            character: Character offset (0-indexed)

        Returns:
            Location of definition, or None if not found
        """
        if not file_path.startswith("file://"):
            file_path = f"file://{Path(file_path).resolve()}"

        response = self._send_message(
            "textDocument/definition",
            {
                "textDocument": {"uri": file_path},
                "position": {"line": line, "character": character},
            },
        )

        if result := response.get("result"):
            if isinstance(result, list) and result:
                loc = result[0]
                return Location(
                    uri=loc.get("uri", ""),
                    range=Range(
                        start=Position(
                            loc["range"]["start"]["line"],
                            loc["range"]["start"]["character"],
                        ),
                        end=Position(
                            loc["range"]["end"]["line"],
                            loc["range"]["end"]["character"],
                        ),
                    ),
                )
            elif isinstance(result, dict):
                return Location(
                    uri=result.get("uri", ""),
                    range=Range(
                        start=Position(
                            result["range"]["start"]["line"],
                            result["range"]["start"]["character"],
                        ),
                        end=Position(
                            result["range"]["end"]["line"],
                            result["range"]["end"]["character"],
                        ),
                    ),
                )

        return None

    def find_references(
        self, file_path: str, line: int, character: int
    ) -> list[Location]:
        """
        Find all references to symbol at position.

        Args:
            file_path: File URI or path
            line: Line number (0-indexed)
            character: Character offset (0-indexed)

        Returns:
            List of locations where symbol is referenced
        """
        if not file_path.startswith("file://"):
            file_path = f"file://{Path(file_path).resolve()}"

        response = self._send_message(
            "textDocument/references",
            {
                "textDocument": {"uri": file_path},
                "position": {"line": line, "character": character},
                "context": {"includeDeclaration": True},
            },
        )

        locations = []
        if result := response.get("result"):
            for loc in result:
                locations.append(
                    Location(
                        uri=loc.get("uri", ""),
                        range=Range(
                            start=Position(
                                loc["range"]["start"]["line"],
                                loc["range"]["start"]["character"],
                            ),
                            end=Position(
                                loc["range"]["end"]["line"],
                                loc["range"]["end"]["character"],
                            ),
                        ),
                    )
                )

        return locations

    def hover(
        self, file_path: str, line: int, character: int
    ) -> HoverInfo | None:
        """
        Get hover documentation for symbol at position.

        Args:
            file_path: File URI or path
            line: Line number (0-indexed)
            character: Character offset (0-indexed)

        Returns:
            Hover information, or None if not available
        """
        if not file_path.startswith("file://"):
            file_path = f"file://{Path(file_path).resolve()}"

        response = self._send_message(
            "textDocument/hover",
            {
                "textDocument": {"uri": file_path},
                "position": {"line": line, "character": character},
            },
        )

        if result := response.get("result"):
            contents = result.get("contents", {})
            if isinstance(contents, str):
                return HoverInfo(language="plaintext", value=contents)
            elif isinstance(contents, dict):
                return HoverInfo(
                    language=contents.get("language", "plaintext"),
                    value=contents.get("value", ""),
                )

        return None

    def get_diagnostics(self, file_path: str) -> list[Diagnostic]:
        """
        Get diagnostics (errors/warnings) for a file.

        Args:
            file_path: File path or URI

        Returns:
            List of diagnostics for the file
        """
        # Note: LSP publishes diagnostics asynchronously
        # This is a placeholder for a more complete implementation
        return []

    def complete(
        self, file_path: str, line: int, character: int
    ) -> list[CompletionItem]:
        """
        Get completions at position.

        Args:
            file_path: File URI or path
            line: Line number (0-indexed)
            character: Character offset (0-indexed)

        Returns:
            List of completion items
        """
        if not file_path.startswith("file://"):
            file_path = f"file://{Path(file_path).resolve()}"

        response = self._send_message(
            "textDocument/completion",
            {
                "textDocument": {"uri": file_path},
                "position": {"line": line, "character": character},
            },
        )

        items = []
        if result := response.get("result"):
            completions = (
                result.get("items", [])
                if isinstance(result, dict)
                else result
            )
            for item in completions:
                items.append(
                    CompletionItem(
                        label=item.get("label", ""),
                        kind=item.get("kind", 1),
                        detail=item.get("detail"),
                        documentation=item.get("documentation"),
                        insert_text=item.get("insertText"),
                    )
                )

        return items


class LSPManager:
    """Manages LSP connections for different languages."""

    def __init__(self):
        """Initialize LSP manager."""
        self._clients: dict[str, LSPClient] = {}

    def get_client(
        self, language: str, root_path: str = "."
    ) -> LSPClient | None:
        """
        Get or create LSP client for language.

        Args:
            language: Language identifier (python, javascript, etc.)
            root_path: Root directory for workspace

        Returns:
            LSPClient instance, or None if server not available
        """
        if language in self._clients:
            return self._clients[language]

        # Map languages to their LSP servers
        server_map = {
            "python": ["pylsp"],
            "javascript": ["node", "--max-old-space-size=4096"],
            "typescript": ["typescript-language-server", "--stdio"],
            "go": ["gopls"],
            "rust": ["rust-analyzer"],
        }

        server_cmd = server_map.get(language)
        if not server_cmd:
            return None

        try:
            client = LSPClient(server_cmd, root_path)
            if client.initialize(f"march-cli-{language}"):
                self._clients[language] = client
                return client
        except RuntimeError:
            pass

        return None

    def shutdown_all(self) -> None:
        """Shutdown all LSP connections."""
        for client in self._clients.values():
            try:
                client.shutdown()
            except Exception:
                pass
        self._clients.clear()


# Singleton instance
_manager_instance: LSPManager | None = None


def get_lsp_manager() -> LSPManager:
    """Get or create singleton LSPManager instance."""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = LSPManager()
    return _manager_instance
