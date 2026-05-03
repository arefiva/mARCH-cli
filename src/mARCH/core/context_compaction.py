"""Context compaction for mARCH CLI conversation history.

When a conversation exceeds the context-window token budget, this module
summarises older messages with an AI-generated summary so the session can
continue without losing important context.
"""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable

# Rough characters-per-token estimate used throughout this module.
_CHARS_PER_TOKEN: int = 4

# Default context window (tokens).
_DEFAULT_MAX_TOKENS: int = 100_000

# Compact when the estimated token count exceeds this fraction of max_tokens.
_COMPACT_THRESHOLD: float = 0.75

# ---------------------------------------------------------------------------
# Summarisation prompt
# ---------------------------------------------------------------------------

_SUMMARIZATION_PROMPT = """\
Please produce a concise summary of the conversation so far.
Structure your response inside <summary> tags with the following sections:

<summary>
## Task Overview
Describe the main task or goal of this conversation.

## Current State
What has been accomplished so far and the current status.

## Important Discoveries
Key findings, decisions, errors encountered, and how they were resolved.

## Next Steps
Remaining work or what the user/agent should do next.

## Context to Preserve
Any specific values, file paths, variable names, or other details that must
be remembered verbatim to continue the task correctly.
</summary>

Be concise — this summary will replace earlier messages to free up context space."""


class ContextCompactor:
    """Handles context compaction for long conversations."""

    def should_compact(
        self,
        messages: list[dict],
        max_tokens: int = _DEFAULT_MAX_TOKENS,
    ) -> bool:
        """Return True when the message list exceeds the compaction threshold.

        Token count is estimated as total characters divided by
        ``_CHARS_PER_TOKEN``.

        Args:
            messages: List of message dicts with at least a ``content`` key.
            max_tokens: Maximum context window size in tokens.

        Returns:
            True if compaction is recommended.
        """
        total_chars = sum(len(str(m.get("content", ""))) for m in messages)
        estimated_tokens = total_chars / _CHARS_PER_TOKEN
        return estimated_tokens >= max_tokens * _COMPACT_THRESHOLD

    def build_summarization_prompt(self) -> str:
        """Return the structured summarisation instruction.

        The instruction asks the AI to produce a ``<summary>`` block with
        five required sections: Task Overview, Current State, Important
        Discoveries, Next Steps, and Context to Preserve.

        Returns:
            Summarisation prompt string.
        """
        return _SUMMARIZATION_PROMPT

    def build_compacted_messages(
        self,
        summary: str,
        original_user_messages: list[str] | None = None,
    ) -> list[dict]:
        """Build a compacted message list from an AI-generated summary.

        The resulting list begins with a system-injected message that
        explains the compaction, followed by the summary wrapped in
        ``<summary>`` tags, and then any preserved user messages.

        Args:
            summary: The AI-generated summary text (without outer tags).
            original_user_messages: Optional list of user message strings to
                preserve after the summary (e.g., the most recent user turn).

        Returns:
            New list of message dicts suitable for the conversation API.
        """
        compacted_content = (
            "The conversation history has been summarised to free up context space. "
            "The summary below captures all essential context:\n\n"
            f"<summary>\n{summary}\n</summary>"
        )
        messages: list[dict] = [{"role": "user", "content": compacted_content}]

        for user_msg in original_user_messages or []:
            messages.append({"role": "user", "content": user_msg})

        return messages

    async def compact(
        self,
        messages: list[dict],
        ai_complete_fn: Callable[[list[dict]], Awaitable[str]],
    ) -> list[dict]:
        """Summarise the conversation and return compacted messages.

        Calls the AI with the current messages plus the summarisation prompt
        appended, extracts the ``<summary>`` block, then builds and returns
        the compacted message list.

        Args:
            messages: Current conversation message list.
            ai_complete_fn: Async callable that accepts a message list and
                returns the AI response string.

        Returns:
            Compacted message list.
        """
        summarization_request = [
            *messages,
            {"role": "user", "content": self.build_summarization_prompt()},
        ]
        response = await ai_complete_fn(summarization_request)
        summary = self._extract_summary(response)
        return self.build_compacted_messages(summary)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_summary(self, response: str) -> str:
        """Extract the content inside ``<summary>…</summary>`` tags.

        Falls back to the raw response if tags are not found.
        """
        match = re.search(r"<summary>(.*?)</summary>", response, re.DOTALL)
        if match:
            return match.group(1).strip()
        return response.strip()
