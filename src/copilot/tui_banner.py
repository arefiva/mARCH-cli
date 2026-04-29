"""
TUI banner and splash screen components.

Provides animated and static ASCII art banners for terminal display.
"""


from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.text import Text


class Banner:
    """ASCII art banner display."""

    # Copilot CLI banner (simplified, not overly complex)
    COPILOT_BANNER = r"""
    ___________     .__.__        __     
    \_   _____/     |__|  | _____|  |__  
     |    __)  ____  __|  |/  ___/  |  \ 
     |     \ / __ \/ __ |  \___ \|   Y  \
     \___  / (__)  (__ |__/____  >___|  /
         \/                    \/     \/ 
    """

    COPILOT_BANNER_SIMPLE = r"""
    ╔════════════════════════════════════════════════════════╗
    ║                                                        ║
    ║       GitHub Copilot CLI - Python Edition            ║
    ║                                                        ║
    ║    AI-powered coding assistant in your terminal      ║
    ║                                                        ║
    ╚════════════════════════════════════════════════════════╝
    """

    def __init__(self, console: Console | None = None):
        """
        Initialize banner.

        Args:
            console: Rich Console instance
        """
        self.console = console or Console()

    def show_simple_banner(self, version: str = "0.1.0") -> None:
        """
        Show simple ASCII banner.

        Args:
            version: Version string to display
        """
        self.console.print(self.COPILOT_BANNER_SIMPLE)
        version_text = Text(
            f"Version {version}",
            style="bold cyan",
        )
        version_centered = Align.center(version_text)
        self.console.print(version_centered)
        self.console.print()

    def show_welcome_screen(
        self,
        version: str = "0.1.0",
        model: str = "claude-sonnet-4.5",
    ) -> None:
        """
        Show welcome screen with startup information.

        Args:
            version: CLI version
            model: Default AI model name
        """
        self.show_simple_banner(version)

        # Welcome info panel
        info_text = f"""[bold]Welcome to GitHub Copilot CLI![/bold]

[cyan]Version:[/cyan] {version}
[cyan]Model:[/cyan] {model}

Type [bold]/help[/bold] for available commands or start typing to chat."""

        panel = Panel(
            info_text,
            border_style="cyan",
            padding=(1, 2),
        )
        self.console.print(panel)
        self.console.print()

    def show_help_banner(self) -> None:
        """Show help/commands banner."""
        help_text = """[bold cyan]Available Commands[/bold cyan]

[bold]/help[/bold]          Show this help message
[bold]/login[/bold]         Log in with GitHub PAT
[bold]/logout[/bold]        Log out
[bold]/model[/bold] <name>  Switch AI model
[bold]/status[/bold]        Show current status
[bold]/lsp[/bold] <cmd>     Configure language server
[bold]/feedback[/bold] <msg> Send feedback
[bold]/experimental[/bold]  Toggle experimental mode
[bold]exit[/bold]           Exit the CLI

Type any question or code snippet to chat with Copilot!"""

        panel = Panel(
            help_text,
            title="[cyan]Commands[/cyan]",
            border_style="cyan",
            padding=(1, 2),
        )
        self.console.print(panel)

    def show_goodbye(self) -> None:
        """Show goodbye message."""
        goodbye_text = Text("Goodbye! Happy coding! 👋", style="green bold")
        goodbye_centered = Align.center(goodbye_text)
        self.console.print()
        self.console.print(goodbye_centered)

    def show_spinner_start(self, text: str = "Processing") -> None:
        """
        Start spinner animation (requires rich spinners).

        Args:
            text: Text to display with spinner
        """
        from rich.spinner import Spinner

        spinner = Spinner("dots", text=text)
        self.console.print(spinner)

    def show_status_line(self, text: str, style: str = "blue") -> None:
        """
        Show status line (e.g., "→ Searching for files...").

        Args:
            text: Status text
            style: Rich style
        """
        status_text = Text(f"→ {text}", style=style)
        self.console.print(status_text)


class ProgressBar:
    """Progress bar display for long operations."""

    def __init__(self, console: Console | None = None):
        """
        Initialize progress bar.

        Args:
            console: Rich Console instance
        """
        self.console = console or Console()

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

        percentage = (current / total * 100) if total > 0 else 0
        bar_text = self._build_progress_bar(current, total)

        progress_text = (
            f"{description}: {current}/{total} ({percentage:.0f}%)"
        )
        self.console.print(f"[cyan]{progress_text}[/cyan]")
        self.console.print(bar_text)

    @staticmethod
    def _build_progress_bar(current: int, total: int, width: int = 30) -> str:
        """
        Build ASCII progress bar.

        Args:
            current: Current progress
            total: Total items
            width: Bar width in characters

        Returns:
            Progress bar string
        """
        if total == 0:
            filled = 0
        else:
            filled = int((current / total) * width)

        bar = "█" * filled + "░" * (width - filled)
        return f"[cyan][{bar}][/cyan]"


def get_banner() -> Banner:
    """Get or create banner instance."""
    if not hasattr(get_banner, "_instance"):
        get_banner._instance = Banner()
    return get_banner._instance


def get_progress_bar() -> ProgressBar:
    """Get or create progress bar instance."""
    if not hasattr(get_progress_bar, "_instance"):
        get_progress_bar._instance = ProgressBar()
    return get_progress_bar._instance
