"""Tests for context compaction (PS-004)."""

import pytest

from mARCH.core.context_compaction import (
    _CHARS_PER_TOKEN,
    _COMPACT_THRESHOLD,
    _DEFAULT_MAX_TOKENS,
    ContextCompactor,
)


@pytest.fixture
def compactor():
    return ContextCompactor()


# ---------------------------------------------------------------------------
# should_compact
# ---------------------------------------------------------------------------


def test_should_compact_false_for_short_conversation(compactor):
    """Short conversations should not trigger compaction."""
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
    ]
    assert compactor.should_compact(messages) is False


def test_should_compact_true_when_over_threshold(compactor):
    """Compaction is triggered when total chars exceed 75 % of max_tokens * 4."""
    # threshold = _DEFAULT_MAX_TOKENS * _COMPACT_THRESHOLD * _CHARS_PER_TOKEN chars
    threshold_chars = int(_DEFAULT_MAX_TOKENS * _COMPACT_THRESHOLD * _CHARS_PER_TOKEN)
    large_content = "x" * (threshold_chars + 1)
    messages = [{"role": "user", "content": large_content}]
    assert compactor.should_compact(messages) is True


def test_should_compact_false_just_below_threshold(compactor):
    """Just below threshold should not trigger compaction."""
    threshold_chars = int(_DEFAULT_MAX_TOKENS * _COMPACT_THRESHOLD * _CHARS_PER_TOKEN)
    content = "x" * (threshold_chars - 1)
    messages = [{"role": "user", "content": content}]
    assert compactor.should_compact(messages) is False


def test_should_compact_respects_custom_max_tokens(compactor):
    """Custom max_tokens parameter is honoured."""
    messages = [{"role": "user", "content": "x" * 1000}]
    # With max_tokens=100 the threshold is 75 * 4 = 300 chars; 1000 > 300 → True
    assert compactor.should_compact(messages, max_tokens=100) is True
    # With max_tokens=10000 the threshold is 7500 * 4 = 30000 chars; 1000 < 30000 → False
    assert compactor.should_compact(messages, max_tokens=10_000) is False


# ---------------------------------------------------------------------------
# build_summarization_prompt
# ---------------------------------------------------------------------------


def test_build_summarization_prompt_returns_non_empty(compactor):
    """Summarisation prompt is a non-empty string."""
    prompt = compactor.build_summarization_prompt()
    assert isinstance(prompt, str)
    assert len(prompt) > 0


def test_build_summarization_prompt_includes_five_sections(compactor):
    """Summarisation prompt includes all five required sections."""
    prompt = compactor.build_summarization_prompt()
    required = [
        "Task Overview",
        "Current State",
        "Important Discoveries",
        "Next Steps",
        "Context to Preserve",
    ]
    for section in required:
        assert section in prompt, f"Missing section: {section}"


def test_build_summarization_prompt_includes_summary_tags(compactor):
    """Summarisation prompt references <summary> tags."""
    prompt = compactor.build_summarization_prompt()
    assert "<summary>" in prompt


# ---------------------------------------------------------------------------
# build_compacted_messages
# ---------------------------------------------------------------------------


def test_build_compacted_messages_contains_summary_tags(compactor):
    """Compacted messages contain <summary> tags wrapping the summary."""
    messages = compactor.build_compacted_messages("My summary")
    combined = " ".join(m["content"] for m in messages)
    assert "<summary>" in combined
    assert "My summary" in combined


def test_build_compacted_messages_first_message_explains_compaction(compactor):
    """First compacted message explains that history was summarised."""
    messages = compactor.build_compacted_messages("Summary text")
    assert "summarised" in messages[0]["content"].lower() or "summarized" in messages[0]["content"].lower()


def test_build_compacted_messages_preserves_user_messages(compactor):
    """User messages passed to build_compacted_messages appear in the result."""
    user_msgs = ["Please continue.", "What is the status?"]
    messages = compactor.build_compacted_messages("Summary", user_msgs)
    contents = [m["content"] for m in messages]
    assert "Please continue." in contents
    assert "What is the status?" in contents


# ---------------------------------------------------------------------------
# compact (async)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compact_extracts_summary_from_mock_response(compactor):
    """compact() calls ai_complete_fn and extracts <summary> block."""
    mock_response = (
        "Here is the summary:\n"
        "<summary>\nTask was to write tests.\nStatus: done.\n</summary>"
    )

    async def mock_ai(msgs):
        return mock_response

    messages = [
        {"role": "user", "content": "Write tests"},
        {"role": "assistant", "content": "Done!"},
    ]
    result = await compactor.compact(messages, mock_ai)
    combined = " ".join(m["content"] for m in result)
    assert "Task was to write tests" in combined
    assert "<summary>" in combined


@pytest.mark.asyncio
async def test_compact_falls_back_when_no_summary_tags(compactor):
    """compact() uses raw response when <summary> tags are absent."""

    async def mock_ai(msgs):
        return "Plain summary without tags."

    messages = [{"role": "user", "content": "Hello"}]
    result = await compactor.compact(messages, mock_ai)
    combined = " ".join(m["content"] for m in result)
    assert "Plain summary without tags." in combined


# ---------------------------------------------------------------------------
# ConversationHistory.compact_if_needed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_conversation_history_compact_if_needed_method_exists():
    """ConversationHistory has compact_if_needed method."""
    from mARCH.core.agent_state import ConversationHistory

    hist = ConversationHistory()
    assert hasattr(hist, "compact_if_needed")
    assert callable(hist.compact_if_needed)


@pytest.mark.asyncio
async def test_conversation_history_compact_if_needed_returns_false_for_short():
    """compact_if_needed returns False when below threshold."""
    from mARCH.core.agent_state import ConversationHistory

    hist = ConversationHistory()
    hist.add_message("user", "Hello")
    hist.add_message("assistant", "Hi")

    async def mock_ai(msgs):
        return "<summary>Short summary</summary>"

    result = await hist.compact_if_needed(mock_ai)
    assert result is False


@pytest.mark.asyncio
async def test_conversation_history_compact_if_needed_compacts_large_history():
    """compact_if_needed returns True and replaces messages when above threshold."""
    from mARCH.core.agent_state import ConversationHistory

    hist = ConversationHistory()
    # Fill with enough content to exceed threshold at max_tokens=10
    for i in range(5):
        hist.add_message("user", "x" * 200)

    async def mock_ai(msgs):
        return "<summary>Compacted context.</summary>"

    result = await hist.compact_if_needed(mock_ai, max_tokens=10)
    assert result is True
    # After compaction messages should be fewer / different
    contents = [m.content for m in hist.messages]
    assert any("Compacted context" in c for c in contents)
