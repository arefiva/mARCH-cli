"""
Tests for Phase 5: TUI & User Interaction components.

Tests conversation rendering, input handling, banners, layouts, and unified TUI.
"""


from mARCH.ui.tui import get_march_tui, mARCHTUI
from mARCH.ui.tui_conversation import (
    ConversationRenderer,
    Message,
    MessageRole,
    get_conversation_renderer,
)

# ============================================================================
# Message Tests
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

class TestmARCHTUI:
    """Tests for unified mARCHTUI."""

    def test_tui_initialization(self):
        """Test TUI initialization."""
        tui = mARCHTUI()
        assert tui is not None

    def test_tui_startup(self):
        """Test TUI startup."""
        tui = mARCHTUI()
        # Should not crash
        tui.startup(version="0.1.0", show_welcome=True)

    def test_add_messages(self):
        """Test adding different message types."""
        tui = mARCHTUI()
        tui.add_user_message("Hello")
        tui.add_assistant_message("Hi there")
        tui.add_system_message("System info")
        assert len(tui.get_conversation_history()) == 3

    def test_show_help(self):
        """Test showing help."""
        tui = mARCHTUI()
        # Should not crash
        tui.show_help()

    def test_show_messages(self):
        """Test showing different message types."""
        tui = mARCHTUI()
        # Should not crash
        tui.show_status("Status")
        tui.show_error("Error")
        tui.show_success("Success")
        tui.show_info("Info")

    def test_theme_management(self):
        """Test theme management."""
        tui = mARCHTUI()
        tui.set_theme("light")
        assert tui.get_theme() == "light"
        themes = tui.list_themes()
        assert "dark" in themes

    def test_window_management(self):
        """Test window management."""
        tui = mARCHTUI()
        window = tui.create_window("test", "Test")
        assert window is not None
        assert tui.set_active_window("test")

    def test_status_bar_management(self):
        """Test status bar management."""
        tui = mARCHTUI()
        tui.set_status("key", "Message")
        # Should not crash
        tui.render_status_bar()

    def test_clear_conversation(self):
        """Test clearing conversation."""
        tui = mARCHTUI()
        tui.add_user_message("Test")
        tui.clear_conversation()
        assert len(tui.get_conversation_history()) == 0

    def test_march_tui_singleton(self):
        """Test mARCHTUI singleton."""
        t1 = get_march_tui()
        t2 = get_march_tui()
        assert t1 is t2

# ============================================================================
# Integration Tests
# ============================================================================

