"""Tests for TUI, plan mode, and autopilot mode."""

import pytest

from mARCH.cli.repl import MARCH_REPL, get_repl
from mARCH.core.plan_mode import PlanModeDetector
from mARCH.core.execution_mode import ExecutionMode, ModeManager
from mARCH.cli.plan_display import PlanApprovalUI, PlanResultDisplay
from mARCH.core.plan_generator import PlanGenerator
from mARCH.cli.cli import AppContext


class TestREPL:
    """Test REPL functionality."""

    def test_repl_initialization(self):
        """Test REPL initializes without errors."""
        repl = MARCH_REPL()
        assert repl is not None
        assert repl.session is not None

    def test_repl_singleton(self):
        """Test get_repl returns singleton."""
        repl1 = get_repl()
        repl2 = get_repl()
        assert repl1 is repl2

    def test_repl_get_input_with_mode_interactive(self):
        """Test REPL prompt includes mode when provided."""
        repl = MARCH_REPL()
        # Note: Can't easily test interactive input, but can verify method exists
        assert hasattr(repl, "get_input")
        assert callable(repl.get_input)

    def test_repl_get_input_accepts_mode_parameter(self):
        """Test get_input accepts ExecutionMode parameter."""
        repl = MARCH_REPL()
        # Just verify the method signature accepts mode
        # (can't test actual input without mocking stdin)
        import inspect

        sig = inspect.signature(repl.get_input)
        assert "mode" in sig.parameters


class TestPlanModeDetection:
    """Test plan mode detection."""

    def test_plan_prefix_detection_true(self):
        """Test detection of [[PLAN]] prefix."""
        assert PlanModeDetector.is_plan_request("[[PLAN]] create a file")
        assert PlanModeDetector.is_plan_request("  [[PLAN]] add feature")

    def test_plan_prefix_detection_false(self):
        """Test detection when [[PLAN]] not present."""
        assert not PlanModeDetector.is_plan_request("create a file")
        assert not PlanModeDetector.is_plan_request("/create")

    def test_plan_content_extraction(self):
        """Test extraction of content after prefix."""
        content = PlanModeDetector.extract_content("[[PLAN]] add feature X")
        assert content == "add feature X"

    def test_plan_content_extraction_no_prefix(self):
        """Test extraction when no prefix."""
        content = PlanModeDetector.extract_content("add feature X")
        assert content == "add feature X"


class TestExecutionMode:
    """Test execution mode management."""

    def test_mode_initialization(self):
        """Test ModeManager initializes with correct mode."""
        mgr = ModeManager(ExecutionMode.INTERACTIVE)
        assert mgr.current_mode == ExecutionMode.INTERACTIVE

    def test_set_mode(self):
        """Test setting execution mode."""
        mgr = ModeManager()
        mgr.set_mode(ExecutionMode.PLAN)
        assert mgr.current_mode == ExecutionMode.PLAN

    def test_is_autopilot_true(self):
        """Test is_autopilot returns true for autopilot modes."""
        mgr = ModeManager(ExecutionMode.AUTOPILOT)
        assert mgr.is_autopilot()

    def test_is_autopilot_false(self):
        """Test is_autopilot returns false for interactive mode."""
        mgr = ModeManager(ExecutionMode.INTERACTIVE)
        assert not mgr.is_autopilot()

    def test_cycle_mode(self):
        """Test cycling through modes."""
        mgr = ModeManager(ExecutionMode.INTERACTIVE)
        assert mgr.cycle_mode() == ExecutionMode.PLAN
        assert mgr.cycle_mode() == ExecutionMode.AUTOPILOT
        assert mgr.cycle_mode() == ExecutionMode.INTERACTIVE

    def test_mode_prompt_indicator(self):
        """Test mode display in prompt."""
        mgr = ModeManager(ExecutionMode.INTERACTIVE)
        indicator = mgr.get_prompt_indicator()
        assert "interactive" in indicator
        assert "[cyan]" in indicator


class TestPlanDisplay:
    """Test plan display functionality."""

    def test_plan_display_creation(self):
        """Test PlanApprovalUI exists and is callable."""
        ui = PlanApprovalUI()
        assert ui is not None

    def test_plan_structure(self):
        """Test valid plan structure."""
        plan = {
            "summary": "Test plan",
            "approach": "Test approach",
            "tasks": ["Task 1", "Task 2"],
            "estimated_effort": "2 hours",
            "success_criteria": ["Criterion 1"],
        }
        # Should not raise
        PlanApprovalUI.display_plan(plan)

    def test_result_display_creation(self):
        """Test PlanResultDisplay exists and is callable."""
        display = PlanResultDisplay()
        assert display is not None

    def test_result_display_with_results(self):
        """Test displaying execution results."""
        results = {
            "status": "complete",
            "mode": "interactive",
            "tasks": [
                {
                    "id": "task1",
                    "description": "Test task",
                    "status": "completed",
                },
            ],
        }
        # Should not raise
        PlanResultDisplay.display_results(results)


@pytest.mark.asyncio
async def test_plan_generator_initialization():
    """Test PlanGenerator initializes with agent."""
    from mARCH.core.agent_state import Agent, ConversationMode

    agent = Agent(name="test", mode=ConversationMode.INTERACTIVE)
    gen = PlanGenerator(agent)
    assert gen is not None
    assert gen.agent == agent


@pytest.mark.asyncio
async def test_plan_generator_generates_plan():
    """Test plan generation creates valid structure."""
    from mARCH.core.agent_state import Agent, ConversationMode

    agent = Agent(name="test", mode=ConversationMode.INTERACTIVE)
    gen = PlanGenerator(agent)

    plan = await gen.generate_plan("add a new feature")
    assert "summary" in plan
    assert "approach" in plan
    assert "tasks" in plan
    assert "estimated_effort" in plan
    assert "success_criteria" in plan


class TestAppContextModes:
    """Test AppContext integration with modes."""

    def test_app_context_has_mode_manager(self):
        """Test AppContext initializes with mode manager."""
        ctx = AppContext()
        assert hasattr(ctx, "mode_manager")
        assert ctx.mode_manager is not None

    def test_app_context_mode_manager_is_correct_type(self):
        """Test AppContext mode manager is correct type."""
        ctx = AppContext()
        assert isinstance(ctx.mode_manager, ModeManager)

    def test_app_context_mode_manager_starts_interactive(self):
        """Test AppContext mode manager starts in interactive mode."""
        ctx = AppContext()
        assert ctx.mode_manager.current_mode == ExecutionMode.INTERACTIVE
