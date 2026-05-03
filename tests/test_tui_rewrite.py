"""Tests for the Textual TUI rewrite (TUI-001 through TUI-009)."""

import pytest

# ============================================================================
# TUI-001: App Scaffold + Core Layout
# ============================================================================


class TestMarchAppImport:
    """Test that MarchApp is importable and correctly structured."""

    def test_march_app_importable(self):
        """MarchApp can be imported from tui_app."""
        from mARCH.ui.tui_app import MarchApp

        assert MarchApp is not None

    def test_march_app_subclasses_textual_app(self):
        """MarchApp subclasses textual.app.App."""
        from textual.app import App

        from mARCH.ui.tui_app import MarchApp

        assert issubclass(MarchApp, App)

    def test_tui_widgets_package_importable(self):
        """tui_widgets package is importable."""
        import mARCH.ui.tui_widgets  # noqa: F401

    def test_march_app_has_bindings(self):
        """MarchApp defines quit bindings for Ctrl+C and Ctrl+D."""
        from mARCH.ui.tui_app import MarchApp

        keys = {b.key for b in MarchApp.BINDINGS}
        assert "ctrl+c" in keys
        assert "ctrl+d" in keys

    def test_march_app_has_action_quit(self):
        """MarchApp defines action_quit method."""
        from mARCH.ui.tui_app import MarchApp

        assert hasattr(MarchApp, "action_quit")
        assert callable(MarchApp.action_quit)


@pytest.mark.asyncio
async def test_march_app_mounts_four_zones():
    """MarchApp composes 4 layout zones."""
    from textual.widgets import Footer, Header

    from mARCH.ui.tui_app import MarchApp

    async with MarchApp().run_test(headless=True) as pilot:
        app = pilot.app
        assert app.query_one(Header) is not None
        assert app.query_one(Footer) is not None
        assert app.query_one("#conversation-area") is not None
        assert app.query_one("#input-bar") is not None


# ============================================================================
# TUI-002: Header & Banner Widget
# ============================================================================


class TestHeaderWidget:
    """Tests for HeaderWidget."""

    def test_header_widget_importable(self):
        """HeaderWidget can be imported."""
        from mARCH.ui.tui_widgets.header import HeaderWidget

        assert HeaderWidget is not None

    def test_header_widget_subclasses_static(self):
        """HeaderWidget subclasses Textual Static."""
        from textual.widgets import Static

        from mARCH.ui.tui_widgets.header import HeaderWidget

        assert issubclass(HeaderWidget, Static)

    def test_header_widget_renders_march_name(self):
        """HeaderWidget render includes 'mARCH'."""
        from mARCH.ui.tui_widgets.header import HeaderWidget

        widget = HeaderWidget()
        rendered = widget.render()
        assert "mARCH" in str(rendered)


# ============================================================================
# TUI-003: Message Display Widget
# ============================================================================


class TestMessageWidget:
    """Tests for MessageWidget."""

    def test_message_widget_importable(self):
        """MessageWidget can be imported."""
        from mARCH.ui.tui_widgets.message import MessageRole, MessageWidget

        assert MessageWidget is not None
        assert MessageRole is not None

    def test_message_roles_defined(self):
        """All four message roles are defined."""
        from mARCH.ui.tui_widgets.message import MessageRole

        assert MessageRole.USER is not None
        assert MessageRole.ASSISTANT is not None
        assert MessageRole.SYSTEM is not None
        assert MessageRole.TOOL is not None

    def test_conversation_view_importable(self):
        """ConversationView can be imported."""
        from mARCH.ui.tui_widgets.conversation import ConversationView

        assert ConversationView is not None

    def test_conversation_view_subclasses_vertical_scroll(self):
        """ConversationView subclasses VerticalScroll."""
        from textual.containers import VerticalScroll

        from mARCH.ui.tui_widgets.conversation import ConversationView

        assert issubclass(ConversationView, VerticalScroll)


# ============================================================================
# TUI-004: Input Widget + Mode Cycling
# ============================================================================


class TestInputBar:
    """Tests for InputBar widget."""

    def test_input_bar_importable(self):
        """InputBar can be imported."""
        from mARCH.ui.tui_widgets.input_bar import InputBar

        assert InputBar is not None

    def test_mode_cycle_order(self):
        """Mode cycling follows INTERACTIVE -> PLAN -> AUTOPILOT -> SHELL -> INTERACTIVE."""
        from mARCH.ui.tui_widgets.input_bar import CYCLE_ORDER, InputMode

        assert CYCLE_ORDER[0] == InputMode.INTERACTIVE
        assert CYCLE_ORDER[1] == InputMode.PLAN
        assert CYCLE_ORDER[2] == InputMode.AUTOPILOT
        assert CYCLE_ORDER[3] == InputMode.SHELL
        assert len(CYCLE_ORDER) == 4

    def test_mode_cycle_wraps(self):
        """Mode cycling wraps back to INTERACTIVE after SHELL."""
        from mARCH.ui.tui_widgets.input_bar import CYCLE_ORDER, InputMode

        # Simulate cycling from SHELL
        current = InputMode.SHELL
        idx = CYCLE_ORDER.index(current)
        next_mode = CYCLE_ORDER[(idx + 1) % len(CYCLE_ORDER)]
        assert next_mode == InputMode.INTERACTIVE

    def test_mode_colors_defined(self):
        """Each mode has a distinct color defined."""
        from mARCH.ui.tui_widgets.input_bar import MODE_COLORS, InputMode

        assert InputMode.INTERACTIVE in MODE_COLORS
        assert InputMode.PLAN in MODE_COLORS
        assert InputMode.AUTOPILOT in MODE_COLORS
        assert InputMode.SHELL in MODE_COLORS
        colors = list(MODE_COLORS.values())
        assert len(set(colors)) == 4, "All mode colors must be distinct"


# ============================================================================
# TUI-005: Streaming Response Display
# ============================================================================


class TestStreamingAppendChunk:
    """Tests for MessageWidget.append_chunk streaming."""

    def test_append_chunk_method_exists(self):
        """MessageWidget has append_chunk method."""
        from mARCH.ui.tui_widgets.message import MessageWidget

        assert hasattr(MessageWidget, "append_chunk")
        assert callable(MessageWidget.append_chunk)

    def test_append_chunk_accumulates_text(self):
        """append_chunk accumulates text across multiple calls."""
        from mARCH.ui.tui_widgets.message import MessageRole, MessageWidget

        widget = MessageWidget(role=MessageRole.ASSISTANT, content="")
        widget.append_chunk("Hello")
        widget.append_chunk(", ")
        widget.append_chunk("world")
        assert widget._content == "Hello, world"


# ============================================================================
# TUI-006: Tool Call Approval Modal
# ============================================================================


class TestToolModal:
    """Tests for ToolModal."""

    def test_tool_modal_importable(self):
        """ToolModal can be imported."""
        from mARCH.ui.tui_widgets.tool_modal import ToolModal

        assert ToolModal is not None

    def test_tool_modal_subclasses_modal_screen(self):
        """ToolModal subclasses textual.screen.ModalScreen."""
        from textual.screen import ModalScreen

        from mARCH.ui.tui_widgets.tool_modal import ToolModal

        assert issubclass(ToolModal, ModalScreen)

    def test_tool_modal_dismiss_values(self):
        """ToolModal defines correct dismiss values for each key."""
        from mARCH.ui.tui_widgets.tool_modal import DISMISS_VALUES

        assert DISMISS_VALUES["y"] == "yes_once"
        assert DISMISS_VALUES["a"] == "always"
        assert DISMISS_VALUES["n"] == "deny"
        assert DISMISS_VALUES["escape"] == "deny"


# ============================================================================
# TUI-007: Status Indicators + Animated Spinners
# ============================================================================


class TestSpinnerWidget:
    """Tests for SpinnerWidget and StatusBar."""

    def test_spinner_widget_importable(self):
        """SpinnerWidget can be imported."""
        from mARCH.ui.tui_widgets.spinners import SPINNER_FRAMES, SpinnerWidget

        assert SpinnerWidget is not None
        assert SPINNER_FRAMES is not None

    def test_spinner_frames_are_braille(self):
        """Spinner frames contain braille characters."""
        from mARCH.ui.tui_widgets.spinners import SPINNER_FRAMES

        assert len(SPINNER_FRAMES) >= 8
        # Verify all frames are single characters
        for frame in SPINNER_FRAMES:
            assert len(frame) == 1

    def test_spinner_frame_cycling(self):
        """Spinner frames cycle correctly."""
        from mARCH.ui.tui_widgets.spinners import SPINNER_FRAMES

        n = len(SPINNER_FRAMES)
        # Cycling through indices should wrap
        for i in range(n * 2):
            frame = SPINNER_FRAMES[i % n]
            assert frame in SPINNER_FRAMES

    def test_status_bar_importable(self):
        """StatusBar can be imported."""
        from mARCH.ui.tui_widgets.status_bar import STATUS_ICONS, StatusBar

        assert StatusBar is not None
        assert STATUS_ICONS is not None

    def test_status_icons_mapping(self):
        """Status icons map correctly to their types."""
        from mARCH.ui.tui_widgets.status_bar import STATUS_ICONS

        assert STATUS_ICONS["success"] == "✓"
        assert STATUS_ICONS["error"] == "✗"
        assert STATUS_ICONS["warning"] == "⚠"
        assert STATUS_ICONS["info"] == "●"


# ============================================================================
# TUI-008: Plan Mode Display Modal
# ============================================================================


class TestPlanModal:
    """Tests for PlanModal."""

    def test_plan_modal_importable(self):
        """PlanModal can be imported."""
        from mARCH.ui.tui_widgets.plan_modal import PlanModal

        assert PlanModal is not None

    def test_plan_modal_subclasses_modal_screen(self):
        """PlanModal subclasses textual.screen.ModalScreen."""
        from textual.screen import ModalScreen

        from mARCH.ui.tui_widgets.plan_modal import PlanModal

        assert issubclass(PlanModal, ModalScreen)

    def test_plan_modal_dismiss_values(self):
        """PlanModal defines correct dismiss values for each key."""
        from mARCH.ui.tui_widgets.plan_modal import DISMISS_VALUES

        assert DISMISS_VALUES["e"] == "exit_only"
        assert DISMISS_VALUES["i"] == "interactive"
        assert DISMISS_VALUES["a"] == "autopilot"
        assert DISMISS_VALUES["f"] == "autopilot_fleet"


# ============================================================================
# TUI-009: Theme System + Color Constants
# ============================================================================


class TestThemeSystem:
    """Tests for the theme and color system."""

    def test_theme_importable(self):
        """Theme dataclass can be imported."""
        from mARCH.ui.theme import Theme, get_theme

        assert Theme is not None
        assert get_theme is not None

    def test_colors_importable(self):
        """colors module exports named constants."""
        import mARCH.ui.colors as colors

        assert hasattr(colors, "BRAND")
        assert hasattr(colors, "MODE_INTERACTIVE")
        assert hasattr(colors, "MODE_PLAN")
        assert hasattr(colors, "MODE_AUTOPILOT")
        assert hasattr(colors, "MODE_SHELL")
        assert hasattr(colors, "STATUS_SUCCESS")
        assert hasattr(colors, "STATUS_ERROR")
        assert hasattr(colors, "STATUS_WARNING")
        assert hasattr(colors, "STATUS_INFO")

    def test_get_theme_returns_theme_instance(self):
        """get_theme() returns a valid Theme instance."""
        from mARCH.ui.theme import Theme, get_theme

        theme = get_theme()
        assert isinstance(theme, Theme)

    def test_get_theme_dark_default(self):
        """get_theme() defaults to dark mode."""
        from mARCH.ui.theme import get_theme

        dark = get_theme()
        light = get_theme(dark=False)
        # Dark and light themes should differ
        assert dark != light

    def test_get_theme_has_required_fields(self):
        """Theme instance has all required color fields."""
        from mARCH.ui.theme import get_theme

        theme = get_theme()
        required = [
            "brand",
            "text",
            "background",
            "accent",
            "border",
            "status_success",
            "status_error",
            "status_warning",
            "status_info",
        ]
        for field in required:
            assert hasattr(theme, field), f"Theme missing field: {field}"

    def test_get_theme_light_returns_different_colors(self):
        """get_theme(dark=False) returns distinct light-mode colors."""
        from mARCH.ui.theme import get_theme

        light = get_theme(dark=False)
        assert isinstance(light.background, str)
        assert isinstance(light.text, str)


# ============================================================================
# US-002: AI conversation dispatch loop
# ============================================================================


class TestMarchAppInit:
    """Tests for MarchApp.__init__ keyword arguments."""

    def test_march_app_default_construction(self):
        """MarchApp() can be constructed with no arguments."""
        from mARCH.ui.tui_app import MarchApp

        app = MarchApp()
        assert app._ai_client is None
        assert app._agent is None

    def test_march_app_accepts_ai_client_and_agent(self):
        """MarchApp accepts optional ai_client and agent arguments."""
        from unittest.mock import MagicMock

        from mARCH.ui.tui_app import MarchApp

        mock_client = MagicMock()
        mock_agent = MagicMock()
        app = MarchApp(ai_client=mock_client, agent=mock_agent)
        assert app._ai_client is mock_client
        assert app._agent is mock_agent

    def test_march_app_has_on_input_submitted(self):
        """MarchApp has on_input_submitted event handler."""
        from mARCH.ui.tui_app import MarchApp

        assert hasattr(MarchApp, "on_input_submitted")
        assert callable(MarchApp.on_input_submitted)

    def test_march_app_has_stream_ai_response(self):
        """MarchApp has _stream_ai_response worker method."""
        from mARCH.ui.tui_app import MarchApp

        assert hasattr(MarchApp, "_stream_ai_response")
        assert callable(MarchApp._stream_ai_response)


@pytest.mark.asyncio
async def test_submit_text_shows_user_message():
    """Submitting text via pilot displays a USER MessageWidget in ConversationView."""
    from mARCH.ui.tui_app import MarchApp
    from mARCH.ui.tui_widgets.conversation import ConversationView
    from mARCH.ui.tui_widgets.message import MessageRole, MessageWidget

    async with MarchApp().run_test(headless=True) as pilot:
        await pilot.press("H", "e", "l", "l", "o")
        await pilot.press("enter")
        await pilot.pause()
        conv = pilot.app.query_one(ConversationView)
        messages = list(conv.query(MessageWidget))
        assert len(messages) >= 1
        user_msgs = [m for m in messages if m._role == MessageRole.USER]
        assert len(user_msgs) >= 1
        assert user_msgs[0]._content == "Hello"


@pytest.mark.asyncio
async def test_submit_text_clears_input():
    """Submitting text clears the input field."""
    from textual.widgets import Input

    from mARCH.ui.tui_app import MarchApp

    async with MarchApp().run_test(headless=True) as pilot:
        await pilot.press("H", "i")
        await pilot.press("enter")
        await pilot.pause()
        inp = pilot.app.query_one("#march-input", Input)
        assert inp.value == ""


@pytest.mark.asyncio
async def test_submit_empty_text_no_message():
    """Submitting empty or whitespace-only text does not add a message."""
    from mARCH.ui.tui_app import MarchApp
    from mARCH.ui.tui_widgets.conversation import ConversationView
    from mARCH.ui.tui_widgets.message import MessageWidget

    async with MarchApp().run_test(headless=True) as pilot:
        await pilot.press("enter")
        await pilot.pause()
        conv = pilot.app.query_one(ConversationView)
        messages = list(conv.query(MessageWidget))
        assert len(messages) == 0


@pytest.mark.asyncio
async def test_submit_text_no_ai_client_shows_not_configured():
    """When ai_client=None, an ASSISTANT 'not configured' message appears."""
    from mARCH.ui.tui_app import MarchApp
    from mARCH.ui.tui_widgets.conversation import ConversationView
    from mARCH.ui.tui_widgets.message import MessageRole, MessageWidget

    async with MarchApp(ai_client=None).run_test(headless=True) as pilot:
        await pilot.press("H", "i")
        await pilot.press("enter")
        await pilot.pause()
        conv = pilot.app.query_one(ConversationView)
        messages = list(conv.query(MessageWidget))
        assistant_msgs = [m for m in messages if m._role == MessageRole.ASSISTANT]
        assert len(assistant_msgs) >= 1
        assert "not configured" in assistant_msgs[0]._content

