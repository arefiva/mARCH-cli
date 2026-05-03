"""
Main CLI entry point using Typer framework.

Provides command-line interface with argument parsing, modes, and slash commands.
"""

import logging
import sys

import typer
from rich.console import Console

from mARCH import __version__, logging_config
from mARCH.config.config import get_config_manager
from mARCH.core.agent_state import Agent, ConversationMode
from mARCH.core.ai_client import ConversationClient
from mARCH.core.execution_mode import ExecutionMode, ModeManager
from mARCH.core.slash_commands import SlashCommandParser
from mARCH.exceptions import mARCHError
from mARCH.github.github_integration import GitHubIntegration
from mARCH.logging_config import setup_logging

logger = logging_config.get_logger(__name__)
console = Console()

app = typer.Typer(
    name="march",
    help="GitHub mARCH CLI - AI-powered coding assistant in your terminal",
    no_args_is_help=False,
)


class AppContext:
    """Application context for maintaining state across commands."""

    def __init__(self) -> None:
        """Initialize application context."""
        from pathlib import Path

        self.config_manager = get_config_manager()
        self.slash_parser = SlashCommandParser()
        self.github_integration = GitHubIntegration()
        self.experimental_mode = self.config_manager.is_experimental_enabled()
        self.current_model = self.config_manager.get_model()
        self.show_banner = self.config_manager.settings.show_banner
        self.agent = Agent(name="mARCH", mode=ConversationMode.INTERACTIVE)

        # Set up agent context with current working directory
        # This gives the agent default read access to files in CWD
        self.agent.context.current_directory = str(Path.cwd())

        self.ai_client: ConversationClient | None = None
        self.mode_manager = ModeManager(initial_mode=ExecutionMode.INTERACTIVE)
        self._initialize_ai_client()

        logger.debug(f"CLI initialized with CWD: {self.agent.context.current_directory}")

    def _initialize_ai_client(self) -> None:
        """Initialize the AI client."""
        try:
            # Get API key from config (environment variable or config file)
            api_key = self.config_manager.settings.anthropic_api_key
            self.ai_client = ConversationClient(self.current_model, api_key=api_key)
        except Exception as e:
            logger.debug(f"Failed to initialize AI client: {e}")
            # AI client is optional - slash commands will work without it


# Global context
_app_context: AppContext | None = None


def get_app_context() -> AppContext:
    """Get or create the application context."""
    global _app_context
    if _app_context is None:
        _app_context = AppContext()
    return _app_context


def print_banner() -> None:
    """Print the mARCH CLI banner."""
    banner = """
    ╔══════════════════════════════════════════════════════════╗
    ║                                                          ║
    ║          GitHub mARCH CLI - Python Edition            ║
    ║                                                          ║
    ║   AI-powered coding assistant in your terminal          ║
    ║                                                          ║
    ╚══════════════════════════════════════════════════════════╝
    """
    console.print(banner, style="cyan")
    console.print(f"Version {__version__}", justify="center")
    console.print()


@app.command()
def main(
    experimental: bool = typer.Option(
        False, "--experimental", help="Enable experimental features"
    ),
    banner: bool = typer.Option(False, "--banner", help="Show ASCII art banner"),
    model: str | None = typer.Option(
        None, "--model", help="Specify AI model to use"
    ),
    version: bool = typer.Option(False, "--version", help="Show version and exit"),
    log_level: str = typer.Option("INFO", "--log-level", help="Set logging level"),
) -> None:
    """
    GitHub mARCH CLI - Terminal-native AI coding assistant.

    Start an interactive session with your AI coding assistant.
    """
    # Setup logging
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    setup_logging(level=level_map.get(log_level.upper(), logging.INFO))

    # Handle version flag
    if version:
        console.print(f"GitHub mARCH CLI v{__version__}")
        sys.exit(0)

    # Get app context
    ctx = get_app_context()

    # Apply command-line overrides
    if experimental:
        ctx.config_manager.set_experimental(True)
        ctx.experimental_mode = True

    if model:
        ctx.config_manager.set_model(model)
        ctx.current_model = model

    # Print banner if requested or configured
    if banner or ctx.show_banner:
        print_banner()
        ctx.show_banner = False  # Don't show again in this session

    console.print("[bold cyan]GitHub mARCH CLI[/bold cyan]")
    console.print(f"Version {__version__}")
    console.print(f"Model: [bold]{ctx.current_model}[/bold]")
    if ctx.experimental_mode:
        console.print("[yellow]⚡ Experimental mode enabled[/yellow]")
    console.print()
    console.print("[dim]Type /help for available commands[/dim]")
    console.print()

    # Launch Textual TUI
    from mARCH.ui.tui_app import MarchApp
    from mARCH.ui.tui_session import TuiSession

    tui_session = TuiSession(
        ai_client=ctx.ai_client,
        agent=ctx.agent,
        slash_parser=ctx.slash_parser,
        mode_manager=ctx.mode_manager,
        config_manager=ctx.config_manager,
        github_integration=ctx.github_integration,
    )
    MarchApp(session=tui_session).run()


def cli_main() -> None:
    """Main entry point for the CLI."""
    try:
        app()
    except mARCHError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        console.print(f"[red]Unexpected error: {e}[/red]")
        sys.exit(1)


def cli() -> None:
    """Entry point for the CLI."""
    cli_main()
