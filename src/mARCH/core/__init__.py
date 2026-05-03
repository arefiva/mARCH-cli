"""Core module - Stream buffer, Shell execution, Process management, Async utilities."""

from mARCH.core.prompts import (
    AgentRole,
    PromptBuilder,
)
from mARCH.core.stream_buffer import (
    StreamBuffer,
    StreamManager,
    StreamMode,
)
from mARCH.core.shell_executor import (
    ShellExecutor,
    CommandResult,
    CommandOptions,
    ShellType,
    CaptureMode,
)
from mARCH.core.process_manager import (
    ProcessManager,
    ProcessInfo,
    ProcessStatus,
    ResourceUsage,
)
from mARCH.core.async_executor import (
    TaskPool,
    CancelToken,
    TaskPriority,
    AsyncIterator,
)
from mARCH.core.payload_handler import (
    PayloadCodec,
    PayloadValidator,
    PayloadFormat,
)

__all__ = [
    # Prompt builder
    "AgentRole",
    "PromptBuilder",
    # Stream buffer
    "StreamBuffer",
    "StreamManager",
    "StreamMode",
    # Shell executor
    "ShellExecutor",
    "CommandResult",
    "CommandOptions",
    "ShellType",
    "CaptureMode",
    # Process manager
    "ProcessManager",
    "ProcessInfo",
    "ProcessStatus",
    "ResourceUsage",
    # Async executor
    "TaskPool",
    "CancelToken",
    "TaskPriority",
    "AsyncIterator",
    # Payload handler
    "PayloadCodec",
    "PayloadValidator",
    "PayloadFormat",
]
