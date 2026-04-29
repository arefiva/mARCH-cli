"""
Tests for Phase 5: TUI & User Interaction components.

Tests conversation rendering, input handling, banners, layouts, and unified TUI.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from io import StringIO

from copilot.tui_conversation import (
    MessageRole,
    Message,
    ConversationRenderer,
    InputPrompt,
    ThemeManager,
    get_conversation_renderer,
    get_input_prompt,
    get_theme_manager,
)
from copilot.tui_banner import (
    Banner,
    ProgressBar,
    get_banner,
    get_progress_bar,
)
from copilot.tui_layout import (
    PanelLocation,
    TUILayout,
    Window,
    WindowManager,
    StatusBar,
    get_tui_layout,
    get_window_manager,
    get_status_bar,
)
from copilot.tui import CopilotTUI, get_copilot_tui


# ============================================================================
# Message Tests
# ============================================================================


class TestMessage:
    """Tests for Message dataclass."""

    def test_message_creation_with_timestamp(self):
        """Test creating message with timestamp."""
        msg = Message(
            role=MessageRole.USER,
            content="Hello",
        )
        assert msg.role == MessageRole.USER
        assert msg.content == "Hello"
        assert msg.timestamp is not None

    def test_message_creation_explicit_timestamp(self):
        """Test creating message with explicit timestamp."""
        now = datetime.now()
        msg = Message(
            role=MessageRole.ASSISTANT,
            content="Response",
            timestamp=now,
        )
        assert msg.timestamp == now

    def test_message_with_metadata(self):
        """Test message with metadata."""
        msg = Message(
            role=MessageRole.USER,
            content="code",
            metadata={"language": "python"},
        )
        assert msg.metadata["language"] == "python"


class TestMessageRole:
    """Tests for MessageRole enum."""

    def test_message_roles(self):
        """Test all message roles exist."""
        assert MessageRole.USER in MessageRole
        assert MessageRole.ASSISTANT in MessageRole
        assert MessageRole.SYSTEM in MessageRole


# ============================================================================
# Conversation Renderer Tests
# ============================================================================


class TestConversationRenderer:
    """Tests for ConversationRenderer."""

    def test_renderer_initialization(self):
        """Test renderer initialization."""
        renderer = ConversationRenderer()
        assert renderer is not None

    def test_add_message(self):
        """Test adding message to conversation."""
        renderer = ConversationRenderer()
        renderer.add_message(MessageRole.USER, "Hello")
        assert len(renderer.messages) == 1
        assert renderer.messages[0].role == MessageRole.USER

    def test_add_multiple_messages(self):
        """Test adding multiple messages."""
        renderer = ConversationRenderer()
        renderer.add_message(MessageRole.USER, "Hello")
        renderer.add_message(MessageRole.ASSISTANT, "Hi there")
        renderer.add_message(MessageRole.USER, "How are you?")
        assert len(renderer.messages) == 3

    def test_clear_messages(self):
        """Test clearing conversation."""
        renderer = ConversationRenderer()
        renderer.add_message(MessageRole.USER, "Hello")
        renderer.clear_messages()
        assert len(renderer.messages) == 0

    def test_render_message_user(self):
        """Test rendering user message."""
        renderer = ConversationRenderer()
        msg = Message(role=MessageRole.USER, content="Test")
        # Should not crash
        renderer.render_message(msg)

    def test_render_conversation(self):
        """Test rendering full conversation."""
        renderer = ConversationRenderer()
        renderer.add_message(MessageRole.USER, "Hi")
        renderer.add_message(MessageRole.ASSISTANT, "Hello")
        # Should not crash
        renderer.render_conversation()

    def test_render_status_messages(self):
        """Test rendering status messages."""
        renderer = ConversationRenderer()
        # Should not crash
        renderer.render_status("Testing", style="blue")
        renderer.render_error("Error test")
        renderer.render_success("Success test")
        renderer.render_info("Info test")

    def test_render_divider(self):
        """Test rendering divider."""
        renderer = ConversationRenderer()
        # Should not crash
        renderer.render_divider()
        renderer.render_divider("Section")

    def test_conversation_renderer_singleton(self):
        """Test conversation renderer singleton."""
        r1 = get_conversation_renderer()
        r2 = get_conversation_renderer()
        assert r1 is r2


# ============================================================================
# Input Prompt Tests
# ============================================================================


class TestInputPrompt:
    """Tests for InputPrompt."""

    def test_prompt_initialization(self):
        """Test input prompt initialization."""
        prompt = InputPrompt()
        assert prompt is not None

    def test_history_management(self):
        """Test input history management."""
        prompt = InputPrompt()
        # Manually add to history (instead of using prompt which reads stdin)
        prompt.history.append("first input")
        prompt.history.append("second input")
        history = prompt.get_history()
        assert len(history) == 2
        assert "first input" in history

    def test_history_limit(self):
        """Test history limit."""
        prompt = InputPrompt()
        prompt.history.extend(["input1", "input2", "input3", "input4"])
        history = prompt.get_history(limit=2)
        assert len(history) == 2
        assert history[-1] == "input4"

    def test_clear_history(self):
        """Test clearing history."""
        prompt = InputPrompt()
        prompt.history.append("test")
        prompt.clear_history()
        assert len(prompt.history) == 0

    def test_input_prompt_singleton(self):
        """Test input prompt singleton."""
        p1 = get_input_prompt()
        p2 = get_input_prompt()
        assert p1 is p2


# ============================================================================
# Theme Manager Tests
# ============================================================================


class TestThemeManager:
    """Tests for ThemeManager."""

    def test_theme_initialization(self):
        """Test theme manager initialization."""
        theme_mgr = ThemeManager(theme="dark")
        assert theme_mgr.current_theme == "dark"

    def test_available_themes(self):
        """Test available themes."""
        theme_mgr = ThemeManager()
        themes = theme_mgr.list_themes()
        assert "dark" in themes
        assert "light" in themes

    def test_set_theme(self):
        """Test setting theme."""
        theme_mgr = ThemeManager()
        theme_mgr.set_theme("light")
        assert theme_mgr.current_theme == "light"

    def test_get_color(self):
        """Test getting color for type."""
        theme_mgr = ThemeManager()
        color = theme_mgr.get_color("primary")
        assert isinstance(color, str)

    def test_theme_manager_singleton(self):
        """Test theme manager singleton."""
        t1 = get_theme_manager()
        t2 = get_theme_manager()
        assert t1 is t2


# ============================================================================
# Banner Tests
# ============================================================================


class TestBanner:
    """Tests for Banner."""

    def test_banner_initialization(self):
        """Test banner initialization."""
        banner = Banner()
        assert banner is not None

    def test_show_simple_banner(self):
        """Test showing simple banner."""
        banner = Banner()
        # Should not crash
        banner.show_simple_banner(version="0.1.0")

    def test_show_welcome_screen(self):
        """Test showing welcome screen."""
        banner = Banner()
        # Should not crash
        banner.show_welcome_screen(version="0.1.0", model="test-model")

    def test_show_help_banner(self):
        """Test showing help banner."""
        banner = Banner()
        # Should not crash
        banner.show_help_banner()

    def test_show_goodbye(self):
        """Test showing goodbye message."""
        banner = Banner()
        # Should not crash
        banner.show_goodbye()

    def test_show_status_line(self):
        """Test showing status line."""
        banner = Banner()
        # Should not crash
        banner.show_status_line("Processing")

    def test_banner_singleton(self):
        """Test banner singleton."""
        b1 = get_banner()
        b2 = get_banner()
        assert b1 is b2


# ============================================================================
# Progress Bar Tests
# ============================================================================


class TestProgressBar:
    """Tests for ProgressBar."""

    def test_progress_bar_initialization(self):
        """Test progress bar initialization."""
        pbar = ProgressBar()
        assert pbar is not None

    def test_show_progress(self):
        """Test showing progress."""
        pbar = ProgressBar()
        # Should not crash
        pbar.show_progress("Processing", total=10, current=5)

    def test_build_progress_bar(self):
        """Test building progress bar string."""
        pbar = ProgressBar()
        bar = ProgressBar._build_progress_bar(5, 10, width=10)
        assert "█" in bar
        assert "░" in bar

    def test_progress_bar_singleton(self):
        """Test progress bar singleton."""
        p1 = get_progress_bar()
        p2 = get_progress_bar()
        assert p1 is p2


# ============================================================================
# Layout Tests
# ============================================================================


class TestPanelLocation:
    """Tests for PanelLocation enum."""

    def test_locations(self):
        """Test panel locations."""
        assert PanelLocation.TOP in PanelLocation
        assert PanelLocation.BOTTOM in PanelLocation
        assert PanelLocation.CENTER in PanelLocation


class TestTUILayout:
    """Tests for TUILayout."""

    def test_layout_initialization(self):
        """Test layout initialization."""
        layout = TUILayout()
        assert layout is not None

    def test_set_header(self):
        """Test setting header."""
        layout = TUILayout()
        # Should not crash
        layout.set_header("Test Header")

    def test_set_footer(self):
        """Test setting footer."""
        layout = TUILayout()
        # Should not crash
        layout.set_footer("Test Footer")

    def test_two_column_layout(self):
        """Test creating two-column layout."""
        layout = TUILayout()
        # Should not crash
        layout.create_two_column_layout()

    def test_three_column_layout(self):
        """Test creating three-column layout."""
        layout = TUILayout()
        # Should not crash
        layout.create_three_column_layout()

    def test_layout_singleton(self):
        """Test layout singleton."""
        l1 = get_tui_layout()
        l2 = get_tui_layout()
        assert l1 is l2


class TestWindow:
    """Tests for Window."""

    def test_window_creation(self):
        """Test window creation."""
        window = Window(name="test", title="Test Window")
        assert window.name == "test"
        assert window.title == "Test Window"

    def test_window_content(self):
        """Test setting window content."""
        window = Window(name="test")
        window.set_content("Test content")
        assert window.content == "Test content"

    def test_window_active_state(self):
        """Test window active state."""
        window = Window(name="test")
        assert not window.is_active
        window.activate()
        assert window.is_active
        window.deactivate()
        assert not window.is_active


class TestWindowManager:
    """Tests for WindowManager."""

    def test_manager_initialization(self):
        """Test window manager initialization."""
        mgr = WindowManager()
        assert mgr is not None

    def test_create_window(self):
        """Test creating window."""
        mgr = WindowManager()
        window = mgr.create_window("test", "Test")
        assert window is not None
        assert mgr.get_window("test") is window

    def test_list_windows(self):
        """Test listing windows."""
        mgr = WindowManager()
        mgr.create_window("w1")
        mgr.create_window("w2")
        windows = mgr.list_windows()
        assert "w1" in windows
        assert "w2" in windows

    def test_set_active_window(self):
        """Test setting active window."""
        mgr = WindowManager()
        mgr.create_window("w1")
        mgr.create_window("w2")
        assert mgr.set_active_window("w2")
        assert mgr.active_window == "w2"

    def test_update_window_content(self):
        """Test updating window content."""
        mgr = WindowManager()
        mgr.create_window("test")
        assert mgr.update_window_content("test", "Content")
        assert mgr.get_window("test").content == "Content"

    def test_window_manager_singleton(self):
        """Test window manager singleton."""
        m1 = get_window_manager()
        m2 = get_window_manager()
        assert m1 is m2


class TestStatusBar:
    """Tests for StatusBar."""

    def test_status_bar_initialization(self):
        """Test status bar initialization."""
        sbar = StatusBar()
        assert sbar is not None

    def test_set_status(self):
        """Test setting status."""
        sbar = StatusBar()
        sbar.set_status("key1", "Message 1")
        assert sbar.get_status("key1") == "Message 1"

    def test_clear_status(self):
        """Test clearing status."""
        sbar = StatusBar()
        sbar.set_status("key", "Message")
        sbar.clear_status("key")
        assert sbar.get_status("key") is None

    def test_status_bar_singleton(self):
        """Test status bar singleton."""
        s1 = get_status_bar()
        s2 = get_status_bar()
        assert s1 is s2


# ============================================================================
# Copilot TUI Tests
# ============================================================================


class TestCopilotTUI:
    """Tests for unified CopilotTUI."""

    def test_tui_initialization(self):
        """Test TUI initialization."""
        tui = CopilotTUI()
        assert tui is not None

    def test_tui_startup(self):
        """Test TUI startup."""
        tui = CopilotTUI()
        # Should not crash
        tui.startup(version="0.1.0", show_welcome=True)

    def test_add_messages(self):
        """Test adding different message types."""
        tui = CopilotTUI()
        tui.add_user_message("Hello")
        tui.add_assistant_message("Hi there")
        tui.add_system_message("System info")
        assert len(tui.get_conversation_history()) == 3

    def test_show_help(self):
        """Test showing help."""
        tui = CopilotTUI()
        # Should not crash
        tui.show_help()

    def test_show_messages(self):
        """Test showing different message types."""
        tui = CopilotTUI()
        # Should not crash
        tui.show_status("Status")
        tui.show_error("Error")
        tui.show_success("Success")
        tui.show_info("Info")

    def test_theme_management(self):
        """Test theme management."""
        tui = CopilotTUI()
        tui.set_theme("light")
        assert tui.get_theme() == "light"
        themes = tui.list_themes()
        assert "dark" in themes

    def test_window_management(self):
        """Test window management."""
        tui = CopilotTUI()
        window = tui.create_window("test", "Test")
        assert window is not None
        assert tui.set_active_window("test")

    def test_status_bar_management(self):
        """Test status bar management."""
        tui = CopilotTUI()
        tui.set_status("key", "Message")
        # Should not crash
        tui.render_status_bar()

    def test_clear_conversation(self):
        """Test clearing conversation."""
        tui = CopilotTUI()
        tui.add_user_message("Test")
        tui.clear_conversation()
        assert len(tui.get_conversation_history()) == 0

    def test_copilot_tui_singleton(self):
        """Test CopilotTUI singleton."""
        t1 = get_copilot_tui()
        t2 = get_copilot_tui()
        assert t1 is t2


# ============================================================================
# Integration Tests
# ============================================================================


class TestPhase5Integration:
    """Integration tests for Phase 5 components."""

    def test_all_components_available(self):
        """Test that all Phase 5 components are available."""
        assert get_conversation_renderer() is not None
        assert get_input_prompt() is not None
        assert get_theme_manager() is not None
        assert get_banner() is not None
        assert get_progress_bar() is not None
        assert get_tui_layout() is not None
        assert get_window_manager() is not None
        assert get_status_bar() is not None
        assert get_copilot_tui() is not None

    def test_tui_full_workflow(self):
        """Test complete TUI workflow."""
        tui = CopilotTUI()
        
        # Startup
        tui.startup(version="0.1.0")
        
        # Interaction
        tui.show_help()
        tui.add_user_message("Test question")
        tui.add_assistant_message("Test response")
        tui.show_status("Operation complete")
        
        # Verify state
        history = tui.get_conversation_history()
        assert len(history) >= 2
        
        # Cleanup
        tui.shutdown()
