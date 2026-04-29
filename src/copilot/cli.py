"""
Main CLI entry point using Typer framework.

Provides command-line interface with argument parsing, modes, and slash commands.
"""

import logging
import sys

import typer
from rich.console import Console

from copilot import __version__
from config import get_config_manager
from exceptions import CopilotError
from github_integration import GitHubIntegration
import logging_config
from slash_commands import SlashCommandParser, SlashCommandType

logger = logging_config.get_logger(__name__)
console = Console()

app = typer.Typer(
    name="copilot",
    help="GitHub Copilot CLI - AI-powered coding assistant in your terminal",
    no_args_is_help=False,
)


class AppContext:
    """Application context for maintaining state across commands."""

    def __init__(self) -> None:
        """Initialize application context."""
        self.config_manager = get_config_manager()
        self.slash_parser = SlashCommandParser()
        self.github_integration = GitHubIntegration()
        self.experimental_mode = self.config_manager.is_experimental_enabled()
        self.current_model = self.config_manager.get_model()
        self.show_banner = self.config_manager.settings.show_banner


# Global context
_app_context: AppContext | None = None


def get_app_context() -> AppContext:
    """Get or create the application context."""
    global _app_context
    if _app_context is None:
        _app_context = AppContext()
    return _app_context


def print_banner() -> None:
    """Print the Copilot CLI banner."""
    banner = """
    ╔══════════════════════════════════════════════════════════╗
    ║                                                          ║
    ║          GitHub Copilot CLI - Python Edition            ║
    ║                                                          ║
    ║   AI-powered coding assistant in your terminal          ║
    ║                                                          ║
    ╚══════════════════════════════════════════════════════════╝
    """
    console.print(banner, style="cyan")
    console.print(f"Version {__version__}", justify="center")
    console.print()


def print_help_text() -> None:
    """Print help text with available commands."""
    console.print("[bold cyan]GitHub Copilot CLI[/bold cyan]", justify="center")
    console.print()
    console.print("[bold]Available Slash Commands:[/bold]")
    console.print()

    commands_info = [
        ("/login", "Authenticate with GitHub"),
        ("/logout", "Log out from GitHub"),
        ("/model", "View or change the AI model"),
        ("/lsp", "View Language Server Protocol configuration"),
        ("/feedback", "Send feedback to GitHub"),
        ("/experimental", "Toggle experimental mode"),
        ("/status", "Show current status and settings"),
        ("/help", "Show this help message"),
    ]

    for command, description in commands_info:
        console.print(f"  [bold green]{command:<15}[/bold green] {description}")

    console.print()
    console.print("[bold]Flags:[/bold]")
    console.print("  [bold green]--experimental[/bold green]  Enable experimental features")
    console.print("  [bold green]--banner[/bold green]        Show ASCII art banner")
    console.print("  [bold green]--model[/bold green] MODEL   Specify AI model")
    console.print("  [bold green]--version[/bold green]       Show version and exit")
    console.print()


def handle_slash_command(ctx: AppContext, command_input: str) -> bool:
    """
    Handle a slash command.

    Args:
        ctx: Application context
        command_input: The slash command input

    Returns:
        True if command was handled, False otherwise
    """
    parsed = ctx.slash_parser.parse(command_input)
    if not parsed:
        return False

    try:
        if parsed.command_type == SlashCommandType.LOGIN:
            handle_login_command(ctx, parsed.args)
        elif parsed.command_type == SlashCommandType.LOGOUT:
            handle_logout_command(ctx, parsed.args)
        elif parsed.command_type == SlashCommandType.MODEL:
            handle_model_command(ctx, parsed.args)
        elif parsed.command_type == SlashCommandType.LSP:
            handle_lsp_command(ctx, parsed.args)
        elif parsed.command_type == SlashCommandType.FEEDBACK:
            handle_feedback_command(ctx, parsed.args)
        elif parsed.command_type == SlashCommandType.EXPERIMENTAL:
            handle_experimental_command(ctx, parsed.args)
        elif parsed.command_type == SlashCommandType.STATUS:
            handle_status_command(ctx, parsed.args)
        elif parsed.command_type == SlashCommandType.HELP:
            print_help_text()
        else:
            console.print(f"[red]Unknown command: {parsed.command_type}[/red]")
            return False

        return True
    except Exception as e:
        logger.error(f"Error handling slash command: {e}")
        console.print(f"[red]Error: {e}[/red]")
        return False


def handle_login_command(ctx: AppContext, args: list[str]) -> None:
    """Handle /login command."""
    console.print("[yellow]/login[/yellow] - GitHub Authentication")
    console.print()

    if ctx.github_integration.is_authenticated():
        user = ctx.github_integration.get_user_info()
        if user:
            console.print("[green]✓[/green] Already authenticated!")
            console.print(f"  User: [bold]{user['login']}[/bold]")
            console.print(f"  Name: {user['name']}")
            if user.get("bio"):
                console.print(f"  Bio: {user['bio']}")
            console.print()
            return

    console.print("Enter your GitHub Personal Access Token:")
    console.print("[dim]Generate a new token at: https://github.com/settings/personal-access-tokens/new[/dim]")
    console.print("[dim]Required permissions: 'Copilot Requests'[/dim]")
    console.print()

    try:
        token = console.input("[cyan]Token (hidden):[/cyan] ", password=True)
        if not token:
            console.print("[yellow]Cancelled[/yellow]")
            return

        console.print("[dim]Authenticating...[/dim]")
        if ctx.github_integration.authenticate_with_pat(token):
            user = ctx.github_integration.get_user_info()
            if user:
                console.print(f"[green]✓[/green] Authenticated as [bold]{user['login']}[/bold]")
        else:
            console.print("[red]✗ Authentication failed[/red]")
    except Exception as e:
        logger.error(f"Error during login: {e}")
        console.print(f"[red]Error: {e}[/red]")


def handle_logout_command(ctx: AppContext, args: list[str]) -> None:
    """Handle /logout command."""
    console.print("[yellow]/logout[/yellow] - Sign out from GitHub")
    console.print()

    if not ctx.github_integration.is_authenticated():
        console.print("[yellow]Not currently authenticated[/yellow]")
        return

    ctx.github_integration.logout()
    console.print("[green]✓[/green] Signed out successfully")


def handle_model_command(ctx: AppContext, args: list[str]) -> None:
    """Handle /model command."""
    if args:
        new_model = " ".join(args)
        ctx.config_manager.set_model(new_model)
        ctx.current_model = new_model
        console.print(f"[green]✓[/green] Model changed to: [bold]{new_model}[/bold]")
    else:
        console.print(f"[bold]Current Model:[/bold] {ctx.current_model}")
        console.print()
        console.print("[bold]Available Models:[/bold]")
        console.print("  - claude-sonnet-4.5 (default)")
        console.print("  - claude-sonnet-4")
        console.print("  - gpt-5.4")
        console.print()
        console.print("[dim]Tip: Use '/model <model-name>' to change[/dim]")


def handle_lsp_command(ctx: AppContext, args: list[str]) -> None:
    """Handle /lsp command."""
    console.print("[yellow]/lsp[/yellow] - Language Server Protocol")
    console.print("[bold]Status:[/bold] Phase 4 implementation")
    console.print()
    console.print("Configure LSP servers at:")
    console.print("  - User level: ~/.copilot/lsp-config.json")
    console.print("  - Repo level: .github/lsp.json")


def handle_feedback_command(ctx: AppContext, args: list[str]) -> None:
    """Handle /feedback command."""
    console.print("[yellow]/feedback[/yellow] - Send Feedback")
    console.print("[bold]Status:[/bold] Future implementation")
    console.print()
    console.print("Your feedback helps improve GitHub Copilot CLI!")


def handle_experimental_command(ctx: AppContext, args: list[str]) -> None:
    """Handle /experimental command."""
    new_state = not ctx.experimental_mode
    ctx.config_manager.set_experimental(new_state)
    ctx.experimental_mode = new_state
    status = "enabled" if new_state else "disabled"
    console.print(f"[green]✓[/green] Experimental mode {status}")
    console.print()
    console.print("[bold]Experimental Features:[/bold]")
    console.print("  - Autopilot mode: Press Shift+Tab to cycle modes")
    console.print("  - Auto-planning and execution")


def handle_status_command(ctx: AppContext, args: list[str]) -> None:
    """Handle /status command."""
    console.print("[bold cyan]Copilot CLI Status[/bold cyan]")
    console.print()
    console.print(f"[bold]Version:[/bold] {__version__}")
    console.print(f"[bold]Model:[/bold] {ctx.current_model}")
    console.print(f"[bold]Experimental Mode:[/bold] {'enabled' if ctx.experimental_mode else 'disabled'}")

    # GitHub status
    if ctx.github_integration.is_authenticated():
        user = ctx.github_integration.get_user_info()
        if user:
            console.print(f"[bold]GitHub Authentication:[/bold] [green]✓[/green] {user['login']}")
    else:
        console.print("[bold]GitHub Authentication:[/bold] [yellow]not configured[/yellow]")

    # Repository context
    repo_ctx = ctx.github_integration.get_current_repo_context()
    if repo_ctx:
        status = "[red]dirty" if repo_ctx.is_dirty else "[green]clean"
        console.print(
            f"[bold]Current Repository:[/bold] {repo_ctx.owner}/{repo_ctx.name} "
            f"({status}[/bold], branch: {repo_ctx.branch})"
        )
    else:
        console.print("[bold]Current Repository:[/bold] not in a Git repository")

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
    GitHub Copilot CLI - Terminal-native AI coding assistant.

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
        console.print(f"GitHub Copilot CLI v{__version__}")
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

    console.print("[bold cyan]GitHub Copilot CLI[/bold cyan]")
    console.print(f"Version {__version__}")
    console.print(f"Model: [bold]{ctx.current_model}[/bold]")
    if ctx.experimental_mode:
        console.print("[yellow]⚡ Experimental mode enabled[/yellow]")
    console.print()
    console.print("[dim]Type /help for available commands[/dim]")
    console.print()

    # Interactive loop
    try:
        while True:
            try:
                user_input = console.input("[cyan]copilot> [/cyan]").strip()

                if not user_input:
                    continue

                # Check for exit commands
                if user_input.lower() in ("exit", "quit", ":q", "q!"):
                    console.print("[yellow]Goodbye![/yellow]")
                    break

                # Handle slash commands
                if ctx.slash_parser.is_slash_command(user_input):
                    handle_slash_command(ctx, user_input)
                    continue

                # Regular input (placeholder for Phase 6 - AI agent)
                console.print("[dim]Phase 6 placeholder - AI agent will process regular input[/dim]")

            except KeyboardInterrupt:
                console.print()
                console.print("[yellow]Interrupted (use 'exit' to quit)[/yellow]")
                continue

    except EOFError:
        console.print()
        console.print("[yellow]Goodbye![/yellow]")
    except Exception as e:
        logger.error(f"Error in main loop: {e}")
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


def cli_main() -> None:
    """Main entry point for the CLI."""
    try:
        app()
    except CopilotError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        console.print(f"[red]Unexpected error: {e}[/red]")
        sys.exit(1)


def cli() -> None:
    """Entry point for the CLI."""
    cli_main()
