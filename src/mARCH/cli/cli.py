"""
Main CLI entry point using Typer framework.

Provides command-line interface with argument parsing, modes, and slash commands.
"""

import asyncio
import logging
import sys
from typing import Generator

import typer
from rich.console import Console

from mARCH import __version__
from mARCH import logging_config
from mARCH.logging_config import setup_logging
from mARCH.config.config import get_config_manager
from mARCH.exceptions import mARCHError
from mARCH.github.github_integration import GitHubIntegration
from mARCH.core.slash_commands import SlashCommandParser, SlashCommandType
from mARCH.core.ai_client import ConversationClient
from mARCH.core.agent_state import Agent, ConversationMode
from mARCH.cli.repl import get_repl
from mARCH.core.execution_mode import ExecutionMode, ModeManager
from mARCH.core.plan_mode import PlanModeDetector
from mARCH.core.plan_generator import PlanGenerator
from mARCH.cli.plan_display import PlanApprovalUI, PlanResultDisplay
from mARCH.core.autopilot_executor import AutopilotExecutor

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
        import os
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


def print_help_text() -> None:
    """Print help text with available commands."""
    console.print("[bold cyan]GitHub mARCH CLI[/bold cyan]", justify="center")
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
        elif parsed.command_type == SlashCommandType.SETUP:
            handle_setup_command(ctx, parsed.args)
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
    console.print("[dim]Required permissions: 'mARCH Requests'[/dim]")
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
    console.print("  - User level: ~/.march/lsp-config.json")
    console.print("  - Repo level: .github/lsp.json")


def handle_feedback_command(ctx: AppContext, args: list[str]) -> None:
    """Handle /feedback command."""
    console.print("[yellow]/feedback[/yellow] - Send Feedback")
    console.print("[bold]Status:[/bold] Future implementation")
    console.print()
    console.print("Your feedback helps improve GitHub mARCH CLI!")


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
    console.print("[bold cyan]mARCH CLI Status[/bold cyan]")
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
        status = "[red]dirty[/red]" if repo_ctx.is_dirty else "[green]clean[/green]"
        console.print(
            f"[bold]Current Repository:[/bold] {repo_ctx.owner}/{repo_ctx.name} "
            f"({status}, branch: {repo_ctx.branch})"
        )
    else:
        console.print("[bold]Current Repository:[/bold] not in a Git repository")

    console.print()


def handle_setup_command(ctx: AppContext, args: list[str]) -> None:
    """Handle /setup command for configuring Anthropic API key."""
    console.print("[bold cyan]/setup[/bold cyan] - Configure mARCH CLI")
    console.print()

    if not args or args[0].lower() == "anthropic":
        console.print("[bold]Anthropic API Key Configuration[/bold]")
        console.print()

        # Check current status
        if ctx.config_manager.settings.anthropic_api_key:
            console.print("[green]✓[/green] Anthropic API key already configured!")
            console.print()

        console.print("To use the mARCH CLI with Claude AI, you need an Anthropic API key.")
        console.print("Get one at: [cyan]https://console.anthropic.com/account/keys[/cyan]")
        console.print()

        try:
            api_key = console.input("[cyan]Enter your Anthropic API key (hidden):[/cyan] ", password=True)
            if not api_key:
                console.print("[yellow]Cancelled[/yellow]")
                return

            # Save to config file
            config = ctx.config_manager.user_config
            config.anthropic_api_key = api_key
            ctx.config_manager.save_user_config(config)

            # Update current settings
            ctx.config_manager._settings = None  # Reset settings to reload

            console.print("[green]✓[/green] Anthropic API key configured successfully!")
            console.print()
            console.print("You can now use /chat or just type prompts directly.")
        except Exception as e:
            logger.error(f"Error configuring API key: {e}")
            console.print(f"[red]Error: {e}[/red]")
    else:
        console.print("Usage: /setup [anthropic]")
        console.print()
        console.print("Examples:")
        console.print("  /setup anthropic   - Configure Anthropic API key")


async def handle_plan_mode(
    ctx: AppContext, user_input: str, mode_manager: ModeManager
) -> None:
    """Handle [[PLAN]] prefix - generate and execute plan.

    Flow:
    1. Extract content after [[PLAN]]
    2. Generate plan
    3. Display plan
    4. Get user action choice
    5. Execute based on choice

    Args:
        ctx: Application context
        user_input: User input with [[PLAN]] prefix
        mode_manager: Mode manager for mode tracking
    """
    # Extract request content after [[PLAN]]
    request = PlanModeDetector.extract_content(user_input)

    if not request:
        console.print("[yellow]⚠️  No request provided after [[PLAN]][/yellow]")
        return

    try:
        # Generate plan
        console.print("[dim]Generating plan...[/dim]")
        plan_gen = PlanGenerator(ctx.agent)
        plan = await plan_gen.generate_plan(request)

        # Display plan
        PlanApprovalUI.display_plan(plan)

        # Get user action selection
        action = PlanApprovalUI.get_approval()

        if action == "exit_only":
            console.print("[yellow]Plan not implemented[/yellow]")
            return

        # Convert action to ExecutionMode
        action_to_mode = {
            "interactive": ExecutionMode.INTERACTIVE,
            "autopilot": ExecutionMode.AUTOPILOT,
            "autopilot_fleet": ExecutionMode.AUTOPILOT_FLEET,
        }
        execution_mode = action_to_mode.get(action, ExecutionMode.INTERACTIVE)

        # Execute plan
        console.print()
        console.print("[bold cyan]Executing plan...[/bold cyan]")
        executor = AutopilotExecutor()
        results = await executor.execute_plan(plan, execution_mode)

        # Display results
        PlanResultDisplay.display_results(results)

    except Exception as e:
        logger.error(f"Error in plan mode: {e}")
        console.print(f"[red]Error generating plan: {e}[/red]")


def handle_regular_input(ctx: AppContext, user_input: str) -> None:
    """
    Handle regular (non-slash command) user input.

    Args:
        ctx: Application context
        user_input: User's input text
    """
    if not ctx.ai_client:
        console.print(
            "[yellow]⚠️  AI client not available.[/yellow] "
            "[dim]Please set your API key using /login or set ANTHROPIC_API_KEY[/dim]"
        )
        return

    # Add user message to agent history
    ctx.agent.add_user_message(user_input)

    # Get conversation context with system prompt
    messages = ctx.agent.get_conversation_context(include_system_prompt=True)

    console.print()
    console.print("[bold cyan]mARCH:[/bold cyan]", end=" ")

    # Stream response from AI
    full_response = ""
    try:
        for chunk in ctx.ai_client.stream_chat(messages):
            console.print(chunk, end="", soft_wrap=True)
            full_response += chunk
        console.print()  # Newline after response
    except Exception as e:
        console.print()
        console.print(f"[red]Error: {e}[/red]")
        logger.error(f"AI client error: {e}")
        return

    # Add assistant response to history
    if full_response:
        ctx.agent.add_assistant_message(full_response)

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

    # Interactive loop
    repl = get_repl(mode_manager=ctx.mode_manager)
    try:
        while True:
            try:
                # Get current mode for prompt display
                current_mode = ctx.mode_manager.current_mode

                # Get user input with mode indicator in prompt
                user_input = repl.get_input(mode=current_mode)

                if not user_input:
                    continue

                # Check for mode change signal (Shift+Tab)
                if user_input.startswith("__MODE_CHANGE__"):
                    mode_value = user_input.split("__MODE_CHANGE__")[1]
                    new_mode = ExecutionMode(mode_value)
                    ctx.mode_manager.set_mode(new_mode)
                    console.print(
                        f"[green]✓[/green] Mode changed to: [bold]{mode_value}[/bold]"
                    )
                    continue

                # Check for exit commands
                if user_input.lower() in ("exit", "quit", ":q", "q!"):
                    console.print("[yellow]Goodbye![/yellow]")
                    break

                # Check for [[PLAN]] prefix FIRST (before slash commands)
                if PlanModeDetector.is_plan_request(user_input):
                    asyncio.run(handle_plan_mode(ctx, user_input, ctx.mode_manager))
                    continue

                # Handle slash commands
                if ctx.slash_parser.is_slash_command(user_input):
                    handle_slash_command(ctx, user_input)
                    continue

                # Handle regular input - send to AI agent
                handle_regular_input(ctx, user_input)

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
