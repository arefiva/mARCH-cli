"""
Terminal User Interface (TUI) components for conversation rendering and display.

Provides Rich-based UI for displaying multi-turn conversations with syntax
highlighting, message formatting, and interactive elements.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.syntax import Syntax
from rich.text import Text


class MessageRole(str, Enum):
    """Message sender role in conversation."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class Message:
    """Single message in conversation."""

    role: MessageRole
    content: str
    timestamp: datetime | None = None
    metadata: dict | None = None

    def __post_init__(self):
        """Set default timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.now()


class ConversationRenderer:
    """Renders multi-turn conversations in terminal."""

    # Color scheme
    COLORS = {
        MessageRole.USER: "cyan",
        MessageRole.ASSISTANT: "green",
        MessageRole.SYSTEM: "yellow",
    }

    ROLE_ICONS = {
        MessageRole.USER: "👤",
        MessageRole.ASSISTANT: "🤖",
        MessageRole.SYSTEM: "⚙️",
    }

    def __init__(self, console: Console | None = None):
        """
        Initialize conversation renderer.

        Args:
            console: Rich Console instance (creates default if not provided)
        """
        self.console = console or Console()
        self.messages: list[Message] = []

    def add_message(
        self,
        role: MessageRole,
        content: str,
        metadata: dict | None = None,
    ) -> None:
        """
        Add message to conversation history.

        Args:
            role: Message sender role
            content: Message content
            metadata: Optional metadata (code language, etc.)
        """
        msg = Message(role=role, content=content, metadata=metadata)
        self.messages.append(msg)

    def render_message(self, message: Message) -> None:
        """
        Render single message to console.

        Args:
            message: Message to render
        """
        color = self.COLORS.get(message.role, "white")
        icon = self.ROLE_ICONS.get(message.role, "•")

        # Create header with role and timestamp
        timestamp_str = (
            message.timestamp.strftime("%H:%M:%S")
            if message.timestamp
            else ""
        )
        header = Text(
            f"{icon} {message.role.value.upper()}",
            style=f"bold {color}",
        )
        if timestamp_str:
            header.append(f" ({timestamp_str})", style="dim")

        # Check if content has code blocks
        if "```" in message.content:
            self._render_message_with_code(header, message.content)
        else:
            # Render as markdown or plain text
            try:
                md = Markdown(message.content)
                panel = Panel(md, title=header, border_style=color)
                self.console.print(panel)
            except Exception:
                panel = Panel(message.content, title=header, border_style=color)
                self.console.print(panel)

    def _render_message_with_code(
        self, header: Text, content: str
    ) -> None:
        """
        Render message with code blocks.

        Args:
            header: Message header text
            content: Message content with code blocks
        """
        parts = content.split("```")
        panel_content = []

        for i, part in enumerate(parts):
            if i % 2 == 0:
                # Text part
                if part.strip():
                    try:
                        md = Markdown(part)
                        panel_content.append(md)
                    except Exception:
                        panel_content.append(part)
            else:
                # Code part
                lines = part.strip().split("\n")
                if lines:
                    language = lines[0] if lines[0] else "text"
                    code = "\n".join(lines[1:]) if len(lines) > 1 else ""

                    # Syntax highlight the code
                    try:
                        syntax = Syntax(
                            code,
                            language,
                            theme="monokai",
                            line_numbers=True,
                        )
                        panel_content.append(syntax)
                    except Exception:
                        panel_content.append(code)

        # Render panel with combined content
        from rich.group import Group

        group = Group(*panel_content)
        panel = Panel(
            group,
            title=header,
            border_style=self.COLORS.get(
                MessageRole(parts[0].split()[0] if parts else "user"), "white"
            ),
        )
        self.console.print(panel)

    def render_conversation(self, limit: int | None = None) -> None:
        """
        Render entire conversation history.

        Args:
            limit: Limit to last N messages (None for all)
        """
        messages = self.messages
        if limit:
            messages = messages[-limit:]

        for i, message in enumerate(messages):
            self.render_message(message)
            if i < len(messages) - 1:
                self.console.print()  # Blank line between messages

    def clear_messages(self) -> None:
        """Clear conversation history."""
        self.messages.clear()

    def render_status(self, text: str, style: str = "blue") -> None:
        """
        Render status message.

        Args:
            text: Status text
            style: Rich style string
        """
        self.console.print(Text(f"→ {text}", style=style))

    def render_error(self, text: str) -> None:
        """
        Render error message.

        Args:
            text: Error text
        """
        panel = Panel(text, title="[red]ERROR[/red]", border_style="red")
        self.console.print(panel)

    def render_success(self, text: str) -> None:
        """
        Render success message.

        Args:
            text: Success text
        """
        panel = Panel(
            text, title="[green]SUCCESS[/green]", border_style="green"
        )
        self.console.print(panel)

    def render_info(self, text: str) -> None:
        """
        Render info message.

        Args:
            text: Info text
        """
        panel = Panel(text, title="[blue]INFO[/blue]", border_style="blue")
        self.console.print(panel)

    def render_divider(self, title: str | None = None) -> None:
        """
        Render horizontal divider.

        Args:
            title: Optional divider title
        """
        if title:
            self.console.print(Rule(title))
        else:
            self.console.print(Rule())


class InputPrompt:
    """Interactive input prompt with history and completion."""

    def __init__(self, console: Console | None = None):
        """
        Initialize input prompt.

        Args:
            console: Rich Console instance
        """
        self.console = console or Console()
        self.history: list[str] = []
        self.history_index = -1

    def prompt(
        self,
        prompt_text: str = "> ",
        multiline: bool = False,
        password: bool = False,
    ) -> str:
        """
        Get user input with optional features.

        Args:
            prompt_text: Prompt text to display
            multiline: Allow multiple lines
            password: Mask input (for passwords)

        Returns:
            User input string
        """
        if password:
            import getpass

            return getpass.getpass(prompt_text)

        if multiline:
            self.console.print(
                prompt_text + " (Press Ctrl+D or Ctrl+Z then Enter to finish)"
            )
            lines = []
            while True:
                try:
                    line = input()
                    lines.append(line)
                except EOFError:
                    break
            result = "\n".join(lines)
        else:
            result = input(prompt_text)

        if result.strip():
            self.history.append(result)
            self.history_index = len(self.history) - 1

        return result

    def get_history(self, limit: int | None = None) -> list[str]:
        """
        Get input history.

        Args:
            limit: Limit to last N items

        Returns:
            List of historical inputs
        """
        if limit:
            return self.history[-limit:]
        return self.history.copy()

    def clear_history(self) -> None:
        """Clear input history."""
        self.history.clear()
        self.history_index = -1


class ThemeManager:
    """Manage TUI color themes."""

    THEMES = {
        "dark": {
            "primary": "cyan",
            "secondary": "green",
            "error": "red",
            "warning": "yellow",
            "success": "green",
            "info": "blue",
        },
        "light": {
            "primary": "blue",
            "secondary": "green",
            "error": "red",
            "warning": "yellow",
            "success": "green",
            "info": "blue",
        },
        "monokai": {
            "primary": "color(75)",
            "secondary": "color(148)",
            "error": "color(197)",
            "warning": "color(220)",
            "success": "color(148)",
            "info": "color(75)",
        },
    }

    def __init__(self, theme: str = "dark"):
        """
        Initialize theme manager.

        Args:
            theme: Theme name (dark, light, monokai)
        """
        self.current_theme = theme
        self.colors = self.THEMES.get(theme, self.THEMES["dark"])

    def set_theme(self, theme: str) -> None:
        """
        Set current theme.

        Args:
            theme: Theme name
        """
        if theme in self.THEMES:
            self.current_theme = theme
            self.colors = self.THEMES[theme]

    def get_color(self, color_type: str) -> str:
        """
        Get color for type.

        Args:
            color_type: Color type (primary, error, warning, etc.)

        Returns:
            Rich style string
        """
        return self.colors.get(color_type, "white")

    def list_themes(self) -> list[str]:
        """Get list of available themes."""
        return list(self.THEMES.keys())


def get_conversation_renderer() -> ConversationRenderer:
    """Get or create conversation renderer instance."""
    if not hasattr(get_conversation_renderer, "_instance"):
        get_conversation_renderer._instance = ConversationRenderer()
    return get_conversation_renderer._instance


def get_input_prompt() -> InputPrompt:
    """Get or create input prompt instance."""
    if not hasattr(get_input_prompt, "_instance"):
        get_input_prompt._instance = InputPrompt()
    return get_input_prompt._instance


def get_theme_manager() -> ThemeManager:
    """Get or create theme manager instance."""
    if not hasattr(get_theme_manager, "_instance"):
        get_theme_manager._instance = ThemeManager()
    return get_theme_manager._instance
