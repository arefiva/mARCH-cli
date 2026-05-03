"""Tests for the prompt builder and agent role system (PS-001 through PS-005)."""

import platform

import pytest

from mARCH.core.prompts import (
    _CODE_CHANGE_INSTRUCTIONS,
    _ECOSYSTEM_TOOLS,
    _LINTING_TESTING,
    _PROHIBITED_ACTIONS,
    _STYLE_RULES,
    _TASK_GUIDELINES,
    _TIPS,
    AgentRole,
    PromptBuilder,
)


@pytest.fixture
def builder():
    return PromptBuilder()


# ---------------------------------------------------------------------------
# PS-001: Core static sections
# ---------------------------------------------------------------------------


def test_build_system_prompt_returns_non_empty_string(builder):
    """build_system_prompt returns a non-empty string."""
    result = builder.build_system_prompt("mARCH", AgentRole.TASK_AGENT)
    assert isinstance(result, str)
    assert len(result) > 0


def test_identity_task_agent_includes_name_and_role(builder):
    """Identity section contains agent name and task-agent-specific skills."""
    section = builder._identity_section("mARCH", AgentRole.TASK_AGENT)
    assert "mARCH" in section
    assert "Task Agent" in section
    assert "researching" in section.lower() or "planning" in section.lower()


def test_identity_coding_agent_includes_name_and_role(builder):
    """Identity section contains agent name and coding-agent-specific skills."""
    section = builder._identity_section("mARCH", AgentRole.CODING_AGENT)
    assert "mARCH" in section
    assert "Coding Agent" in section
    assert "code" in section.lower()


def test_task_agent_and_coding_agent_produce_different_identity(builder):
    """TASK_AGENT and CODING_AGENT produce different identity text."""
    task = builder._identity_section("mARCH", AgentRole.TASK_AGENT)
    coding = builder._identity_section("mARCH", AgentRole.CODING_AGENT)
    assert task != coding


def test_section_constants_are_non_empty():
    """Every static section constant is a non-empty string."""
    for const in (
        _TASK_GUIDELINES,
        _CODE_CHANGE_INSTRUCTIONS,
        _LINTING_TESTING,
        _STYLE_RULES,
        _ECOSYSTEM_TOOLS,
        _TIPS,
        _PROHIBITED_ACTIONS,
    ):
        assert isinstance(const, str)
        assert len(const) > 0


def test_build_system_prompt_includes_all_eight_sections(builder):
    """Full prompt includes all 8 static sections."""
    result = builder.build_system_prompt("mARCH", AgentRole.TASK_AGENT)
    # Spot-check representative phrases from each section
    assert "Task Agent" in result or "Coding Agent" in result  # identity
    assert "<plan>" in result  # task guidelines
    assert "surgical" in result.lower() or "precise" in result.lower()  # code change
    assert "linter" in result.lower() or "lint" in result.lower()  # linting/testing
    assert "comment" in result.lower()  # style
    assert "ecosystem" in result.lower() or "package manager" in result.lower()  # ecosystem
    assert "temporary files" in result.lower() or "temp" in result.lower()  # tips
    assert "prohibited" in result.lower() or "must not" in result.lower()  # prohibited


def test_task_guidelines_mentions_plan_tags(builder):
    """Task guidelines section mentions <plan> tags."""
    section = builder._task_guidelines_section()
    assert "<plan>" in section


def test_prohibited_actions_section_contains_security_rules(builder):
    """Prohibited actions section includes security-related rules."""
    section = builder._prohibited_actions_section()
    assert "secret" in section.lower() or "credential" in section.lower()
    assert "copyright" in section.lower() or "harmful" in section.lower()


def test_agent_role_enum_values():
    """AgentRole enum has TASK_AGENT and CODING_AGENT."""
    assert AgentRole.TASK_AGENT.value == "task_agent"
    assert AgentRole.CODING_AGENT.value == "coding_agent"


# ---------------------------------------------------------------------------
# PS-002: Environment context and custom instructions
# ---------------------------------------------------------------------------


class _MockContext:
    current_directory = "/tmp/test-project"
    git_branch = "main"


def test_environment_section_includes_os_and_directory(builder):
    """Environment context section includes OS name and directory."""
    ctx = _MockContext()
    section = builder._environment_context_section(ctx)
    assert platform.system() in section
    assert "/tmp/test-project" in section


def test_environment_section_includes_branch(builder):
    """Environment context section includes git branch when provided."""
    ctx = _MockContext()
    section = builder._environment_context_section(ctx)
    assert "main" in section


def test_custom_instructions_returns_none_when_file_missing(builder, tmp_path):
    """custom_instructions_section returns None when file does not exist."""
    result = builder._custom_instructions_section(str(tmp_path))
    assert result is None


def test_custom_instructions_returns_content_when_file_exists(builder, tmp_path):
    """custom_instructions_section returns file content when file exists."""
    github_dir = tmp_path / ".github"
    github_dir.mkdir()
    instructions = github_dir / "copilot-instructions.md"
    instructions.write_text("Always use type hints.")
    result = builder._custom_instructions_section(str(tmp_path))
    assert result is not None
    assert "Always use type hints." in result


def test_full_prompt_includes_environment_section(builder):
    """Full prompt includes environment context section."""
    ctx = _MockContext()
    result = builder.build_system_prompt("mARCH", AgentRole.TASK_AGENT, context=ctx)
    assert platform.system() in result
    assert "/tmp/test-project" in result


# ---------------------------------------------------------------------------
# PS-003: Memory injection
# ---------------------------------------------------------------------------


def test_memory_section_returns_none_when_memories_empty(builder):
    """Memory section returns None for empty/None memories."""
    assert builder._memory_section(None) is None
    assert builder._memory_section([]) is None


def test_memory_section_includes_preamble_when_memories_provided(builder):
    """Memory section includes verification preamble when memories are given."""
    memories = [{"fact": "Use ruff for linting.", "subject": "linting", "citations": "pyproject.toml:190"}]
    section = builder._memory_section(memories)
    assert section is not None
    assert "obsolete" in section.lower() or "verify" in section.lower()


def test_memory_section_includes_each_fact_and_citation(builder):
    """Memory section lists each fact and its citation."""
    memories = [
        {"fact": "Use ruff for linting.", "subject": "linting", "citations": "pyproject.toml:190"},
        {"fact": "Tests live in src/mARCH/tests/.", "subject": "testing", "citations": "Makefile:10"},
    ]
    section = builder._memory_section(memories)
    assert section is not None
    assert "Use ruff for linting." in section
    assert "pyproject.toml:190" in section
    assert "Tests live in src/mARCH/tests/." in section
    assert "Makefile:10" in section


def test_full_prompt_omits_memory_section_when_no_memories(builder):
    """Full prompt has no memory section when memories not provided."""
    result = builder.build_system_prompt("mARCH", AgentRole.TASK_AGENT)
    assert "Memories from previous sessions" not in result


def test_full_prompt_includes_memory_section_when_memories_provided(builder):
    """Full prompt includes memory section when memories are provided."""
    memories = [{"fact": "Prefer pathlib.", "subject": "style", "citations": "CONTRIBUTING.md:5"}]
    result = builder.build_system_prompt("mARCH", AgentRole.TASK_AGENT, memories=memories)
    assert "Memories from previous sessions" in result
    assert "Prefer pathlib." in result


# ---------------------------------------------------------------------------
# PS-005: Mode transition messages (imported from prompts module)
# ---------------------------------------------------------------------------


def test_mode_transition_message_imports():
    """Mode transition constants and helper are importable."""
    from mARCH.core.prompts import (  # noqa: F401
        AUTOPILOT_FLEET_MODE_MESSAGE,
        AUTOPILOT_MODE_MESSAGE,
        INTERACTIVE_MODE_MESSAGE,
        INTERACTIVE_NO_EXEC_MESSAGE,
        QUOTA_INSUFFICIENT_MESSAGE,
        TASK_NOT_COMPLETE_MESSAGE,
        get_mode_transition_message,
        get_quota_message,
        get_task_not_complete_message,
    )


def test_each_mode_returns_distinct_non_empty_message():
    """Each execution mode returns a unique, non-empty message."""
    from mARCH.core.execution_mode import ExecutionMode
    from mARCH.core.prompts import get_mode_transition_message

    messages = {mode: get_mode_transition_message(mode) for mode in ExecutionMode}
    for mode, msg in messages.items():
        assert isinstance(msg, str), f"Mode {mode} returned non-string"
        assert len(msg) > 0, f"Mode {mode} returned empty message"

    non_empty = [m for m in messages.values() if m]
    assert len(set(non_empty)) > 1, "Modes should produce distinct messages"


def test_autopilot_message_mentions_auto_approved():
    """AUTOPILOT mode message mentions auto-approved or autopilot."""
    from mARCH.core.prompts import AUTOPILOT_MODE_MESSAGE

    assert "auto" in AUTOPILOT_MODE_MESSAGE.lower()


def test_interactive_message_mentions_manual_approval():
    """INTERACTIVE mode message mentions manual confirmation or approval."""
    from mARCH.core.prompts import INTERACTIVE_MODE_MESSAGE

    assert "confirm" in INTERACTIVE_MODE_MESSAGE.lower() or "manual" in INTERACTIVE_MODE_MESSAGE.lower() or "interactive" in INTERACTIVE_MODE_MESSAGE.lower()


def test_quota_message_mentions_insufficient():
    """Quota message mentions insufficient."""
    from mARCH.core.prompts import QUOTA_INSUFFICIENT_MESSAGE

    assert "insufficient" in QUOTA_INSUFFICIENT_MESSAGE.lower() or "quota" in QUOTA_INSUFFICIENT_MESSAGE.lower()


def test_task_not_complete_message():
    """Task-not-complete message contains appropriate text."""
    from mARCH.core.prompts import TASK_NOT_COMPLETE_MESSAGE

    assert "complete" in TASK_NOT_COMPLETE_MESSAGE.lower() or "not yet" in TASK_NOT_COMPLETE_MESSAGE.lower()


def test_mode_manager_get_transition_context():
    """ModeManager.get_transition_context returns the mode message."""
    from mARCH.core.execution_mode import ExecutionMode, ModeManager
    from mARCH.core.prompts import get_mode_transition_message

    mgr = ModeManager(ExecutionMode.AUTOPILOT)
    msg = mgr.get_transition_context(ExecutionMode.AUTOPILOT)
    expected = get_mode_transition_message(ExecutionMode.AUTOPILOT)
    assert msg == expected
