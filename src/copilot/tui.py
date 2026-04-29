"""
Unified Terminal User Interface (TUI) for Copilot CLI.

Integrates conversation rendering, input handling, banners, and layouts
into a cohesive terminal interface.
"""


from rich.console import Console

from .tui_banner import Banner, ProgressBar
from .tui_conversation import (
    ConversationRenderer,
    InputPrompt,
    MessageRole,
    ThemeManager,
)
from .tui_layout import (
    StatusBar,
    TUILayout,
    Window,
    WindowManager,
)


class CopilotTUI:
    """Main TUI interface for Copilot CLI."""

    def __init__(self, console: Console | None = None):
        """
        Initialize Copilot TUI.

        Args:
            console: Rich Console instance
        """
        self.console = console or Console()

        # Initialize all TUI components
        self.conversation = ConversationRenderer(self.console)
        self.input_prompt = InputPrompt(self.console)
        self.theme_manager = ThemeManager(theme="dark")
        self.banner = Banner(self.console)
        self.progress_bar = ProgressBar(self.console)
        self.layout = TUILayout(self.console)
        self.window_manager = WindowManager(self.console)
        self.status_bar = StatusBar(self.console)

        self.is_running = False

    def startup(
        self,
        version: str = "0.1.0",
        model: str = "claude-sonnet-4.5",
        show_welcome: bool = True,
    ) -> None:
        """
        Show startup screen and initialize TUI.

        Args:
            version: CLI version
            model: Default AI model
            show_welcome: Show welcome screen
        """
        if show_welcome:
            self.banner.show_welcome_screen(version, model)
        else:
            self.banner.show_simple_banner(version)

    def shutdown(self) -> None:
        """Show shutdown screen and cleanup."""
        self.banner.show_goodbye()
        self.is_running = False

    def add_user_message(self, content: str) -> None:
        """
        Add and display user message.

        Args:
            content: User message text
        """
        self.conversation.add_message(MessageRole.USER, content)
        self.conversation.render_message(
            self.conversation.messages[-1]
        )

    def add_assistant_message(self, content: str) -> None:
        """
        Add and display assistant message.

        Args:
            content: Assistant response text
        """
        self.conversation.add_message(MessageRole.ASSISTANT, content)
        self.conversation.render_message(
            self.conversation.messages[-1]
        )

    def add_system_message(self, content: str) -> None:
        """
        Add and display system message.

        Args:
            content: System message text
        """
        self.conversation.add_message(MessageRole.SYSTEM, content)
        self.conversation.render_message(
            self.conversation.messages[-1]
        )

    def show_help(self) -> None:
        """Display help information."""
        self.banner.show_help_banner()

    def show_status(self, text: str, style: str = "blue") -> None:
        """
        Show status message.

        Args:
            text: Status text
            style: Rich style
        """
        self.conversation.render_status(text, style)

    def show_error(self, text: str) -> None:
        """
        Show error message.

        Args:
            text: Error text
        """
        self.conversation.render_error(text)

    def show_success(self, text: str) -> None:
        """
        Show success message.

        Args:
            text: Success text
        """
        self.conversation.render_success(text)

    def show_info(self, text: str) -> None:
        """
        Show info message.

        Args:
            text: Info text
        """
        self.conversation.render_info(text)

    def get_user_input(
        self,
        prompt: str = "copilot> ",
        multiline: bool = False,
        password: bool = False,
    ) -> str:
        """
        Get user input.

        Args:
            prompt: Prompt text
            multiline: Allow multiline input
            password: Mask input

        Returns:
            User input string
        """
        return self.input_prompt.prompt(
            prompt_text=prompt,
            multiline=multiline,
            password=password,
        )

    def show_divider(self, title: str | None = None) -> None:
        """
        Show divider line.

        Args:
            title: Optional divider title
        """
        self.conversation.render_divider(title)

    def set_theme(self, theme: str) -> None:
        """
        Set UI theme.

        Args:
            theme: Theme name (dark, light, monokai)
        """
        self.theme_manager.set_theme(theme)

    def get_theme(self) -> str:
        """Get current theme name."""
        return self.theme_manager.current_theme

    def list_themes(self) -> list[str]:
        """Get available themes."""
        return self.theme_manager.list_themes()

    def show_progress(
        self,
        description: str,
        total: int,
        current: int,
    ) -> None:
        """
        Show progress bar.

        Args:
            description: Operation description
            total: Total items
            current: Current progress
        """
        self.progress_bar.show_progress(description, total, current)

    def create_window(
        self,
        name: str,
        title: str | None = None,
        border_style: str = "blue",
    ) -> Window:
        """
        Create TUI window.

        Args:
            name: Window identifier
            title: Window title
            border_style: Border style

        Returns:
            Created Window object
        """
        return self.window_manager.create_window(name, title, border_style)

    def get_window(self, name: str) -> Window | None:
        """Get window by name."""
        return self.window_manager.get_window(name)

    def set_active_window(self, name: str) -> bool:
        """
        Activate window.

        Args:
            name: Window name

        Returns:
            True if successful
        """
        return self.window_manager.set_active_window(name)

    def render_windows(self) -> None:
        """Render all windows."""
        self.window_manager.render_all_windows()

    def set_status(self, key: str, message: str) -> None:
        """
        Set status bar message.

        Args:
            key: Status key
            message: Status message
        """
        self.status_bar.set_status(key, message)

    def render_status_bar(self) -> None:
        """Render status bar."""
        self.status_bar.render_status_bar()

    def clear_status(self, key: str) -> None:
        """Clear status message."""
        self.status_bar.clear_status(key)

    def get_conversation_history(
        self, limit: int | None = None
    ) -> list:
        """
        Get conversation history.

        Args:
            limit: Limit to last N messages

        Returns:
            List of Message objects
        """
        messages = self.conversation.messages
        if limit:
            return messages[-limit:]
        return messages

    def clear_conversation(self) -> None:
        """Clear conversation history."""
        self.conversation.clear_messages()

    def clear_input_history(self) -> None:
        """Clear input history."""
        self.input_prompt.clear_history()


def get_copilot_tui() -> CopilotTUI:
    """Get or create singleton CopilotTUI instance."""
    if not hasattr(get_copilot_tui, "_instance"):
        get_copilot_tui._instance = CopilotTUI()
    return get_copilot_tui._instance
