"""
Logging configuration for mARCH CLI.

Sets up structured logging with optional Rich formatting.
"""

import logging
import logging.config
from pathlib import Path

from rich.logging import RichHandler


def setup_logging(
    level: int = logging.INFO,
    log_file: Path | None = None,
    use_rich: bool = True,
) -> None:
    """
    Configure logging for the application.

    Args:
        level: Logging level (default: logging.INFO)
        log_file: Optional path to log file for file-based logging
        use_rich: Whether to use Rich handler for colored output (default: True)
    """
    # Create logger
    logger = logging.getLogger("march")
    logger.setLevel(level)

    # Remove existing handlers
    logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler (with Rich if available)
    console_handler: RichHandler | logging.StreamHandler
    if use_rich:
        console_handler = RichHandler(
            level=level,
            show_time=True,
            show_level=True,
            show_path=False,
        )
        console_handler.setFormatter(formatter)
    else:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)

    # File handler (if log_file provided)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Suppress overly verbose third-party loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("github").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(f"march.{name}")
