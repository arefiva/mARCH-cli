# PRD: Textual-Based TUI Rewrite

## 1. Introduction/Overview

The current mARCH TUI is built on Rich panels and prompt_toolkit for input. While functional, this architecture has limitations: no true reactive widget tree, no built-in modal support, manual layout management, and no async-first event loop. Textual (already a dependency) provides all of these out of the box.

This PRD defines a full rewrite of the TUI layer from Rich/prompt_toolkit to Textual, delivering a modern reactive terminal UI with proper widget composition, modal dialogs, streaming support, and a theme system.

## 2. Goals

- Replace the Rich-panel + prompt_toolkit TUI with a Textual `App`-based architecture
- Provide a composable widget tree: Header, ConversationView, InputBar, StatusBar
- Support modal dialogs for tool approval and plan display
- Enable real-time streaming of AI responses without flicker
- Introduce a centralized theme/color system for consistent styling
- Maintain backward compatibility during transition (old TUI remains available)

## 3. User Stories

### TUI-001: Textual App Scaffold + Core Layout
**Description:** As a developer using mARCH, I want the TUI to run as a Textual App with a structured layout so that I have a stable foundation for all UI widgets.

**Implementation Notes:**
- Create `src/mARCH/ui/tui_app.py` with a `MarchApp(App)` class
- Layout uses Textual CSS: vertical arrangement of Header | ConversationArea | InputBar | Footer
- Create `src/mARCH/ui/tui_widgets/__init__.py` as the widget package
- Mount placeholder `Static` widgets for each layout zone
- Handle `on_key` for Ctrl+C / Ctrl+D graceful exit
- Update `src/mARCH/cli/cli.py` to call `MarchApp().run()` instead of the old TUI entry point
- Keep old TUI code intact; wire new app behind default path

**Acceptance Criteria:**
- [ ] `MarchApp` class exists and subclasses `textual.app.App`
- [ ] App launches with 4 visible layout zones (header, conversation, input, footer)
- [ ] Ctrl+C and Ctrl+D exit the app cleanly without traceback
- [ ] `tui_widgets/__init__.py` exists and is importable
- [ ] `ruff check` passes with no errors
- [ ] `pytest` passes with no failures

### TUI-002: Header & Banner Widget
**Description:** As a user, I want to see the project name, version, and mode indicator in a header bar so that I always know what mode I'm in.

**Implementation Notes:**
- Create `src/mARCH/ui/tui_widgets/header.py` with a `HeaderWidget(Static)` class
- Display project name "mARCH", version from package metadata, current mode
- Include a simple ASCII mascot (static text, no animation)
- Responsive: narrow layout (<80 cols) hides mascot, wide layout shows it
- Wire into `tui_app.py` by replacing the header placeholder

**Acceptance Criteria:**
- [ ] `HeaderWidget` renders project name and version string
- [ ] Mode indicator displays current mode (e.g., INTERACTIVE)
- [ ] Widget degrades gracefully when terminal width < 80 columns
- [ ] Unit test verifies header content includes "mARCH"
- [ ] `ruff check` passes with no errors
- [ ] `pytest` passes with no failures

### TUI-003: Message Display Widget
**Description:** As a user, I want to see conversation messages rendered with role labels, markdown, and syntax-highlighted code blocks so that the conversation is readable.

**Implementation Notes:**
- Create `src/mARCH/ui/tui_widgets/conversation.py` with `ConversationView(VerticalScroll)` container
- Create `src/mARCH/ui/tui_widgets/message.py` with `MessageWidget(Static)` for individual messages
- Support roles: USER, ASSISTANT, SYSTEM, TOOL — each with a distinct label/color
- Use Textual's `Markdown` widget or Rich markup for markdown rendering and code blocks
- Auto-scroll to bottom when new messages are appended
- Handle empty conversation state with a placeholder message

**Acceptance Criteria:**
- [ ] `ConversationView` renders a list of `MessageWidget` instances
- [ ] Each message displays role label (USER/ASSISTANT/SYSTEM/TOOL)
- [ ] Code blocks render with syntax highlighting
- [ ] View auto-scrolls to the newest message on append
- [ ] Empty conversation shows a placeholder (not blank)
- [ ] `ruff check` passes with no errors
- [ ] `pytest` passes with no failures

### TUI-004: Input Widget + Mode Cycling
**Description:** As a user, I want an input bar with mode cycling so that I can switch between INTERACTIVE, PLAN, AUTOPILOT, and SHELL modes without leaving the keyboard.

**Implementation Notes:**
- Create `src/mARCH/ui/tui_widgets/input_bar.py` with `InputBar(Widget)` containing a Textual `Input`
- Mode indicator shows current mode with color: INTERACTIVE(cyan), PLAN(yellow), AUTOPILOT(green), SHELL(red)
- Shift+Tab cycles through modes (matching existing `repl.py` behavior)
- Enter submits input; Ctrl+C interrupts current operation
- Ctrl+N toggles multiline mode
- Wire into `tui_app.py` replacing the input placeholder
- Mark `repl.py` REPL input as deprecated but don't delete it

**Acceptance Criteria:**
- [ ] `InputBar` widget renders with mode label and text input field
- [ ] Shift+Tab cycles modes in order: INTERACTIVE → PLAN → AUTOPILOT → SHELL → INTERACTIVE
- [ ] Enter key submits the input text and clears the field
- [ ] Mode indicator color changes per mode
- [ ] Unit test verifies mode cycling logic
- [ ] `ruff check` passes with no errors
- [ ] `pytest` passes with no failures

### TUI-005: Streaming Response Display
**Description:** As a user, I want AI responses to stream token-by-token into the conversation view so that I see output in real time without flicker.

**Implementation Notes:**
- Update `src/mARCH/ui/tui_widgets/conversation.py` to support `append_chunk(text: str)` reactive method on the active message
- When streaming starts, create a new `MessageWidget` with role ASSISTANT and empty content
- Each delta token calls `append_chunk` which updates the widget content reactively
- Use Textual `Worker` pattern for the async AI call + streaming loop
- Update `src/mARCH/core/agent_state.py` to integrate with the new streaming callback
- Ensure no cursor artifacts or visible flicker during rapid updates

**Acceptance Criteria:**
- [ ] `append_chunk` method exists on `MessageWidget` and updates content reactively
- [ ] Streaming tokens appear incrementally in the conversation view
- [ ] Worker pattern properly handles async streaming lifecycle
- [ ] No visible flicker or cursor artifacts during streaming
- [ ] Unit test verifies `append_chunk` accumulates text correctly
- [ ] `ruff check` passes with no errors
- [ ] `pytest` passes with no failures

### TUI-006: Tool Call Approval Modal
**Description:** As a user, I want a modal dialog for tool call approvals so that I can review and approve/deny tool executions with keyboard shortcuts.

**Implementation Notes:**
- Create `src/mARCH/ui/tui_widgets/tool_modal.py` with `ToolModal(ModalScreen)`
- Display: tool name, description, formatted arguments
- Keyboard shortcuts: y=yes once, a=always approve, n=no/deny, Esc=cancel
- Also support arrow up/down navigation and number shortcuts 1/2/3/4
- Return choice via Textual `dismiss()` mechanism
- Integration in `tui_app.py`: `self.push_screen(ToolModal(tool_info), callback)`

**Acceptance Criteria:**
- [ ] `ToolModal` subclasses `textual.screen.ModalScreen`
- [ ] Modal displays tool name, description, and arguments
- [ ] Keyboard shortcut 'y' dismisses with "yes_once" result
- [ ] Keyboard shortcut 'a' dismisses with "always" result
- [ ] Keyboard shortcut 'n' or Esc dismisses with "deny" result
- [ ] Unit test verifies dismiss values for each shortcut
- [ ] `ruff check` passes with no errors
- [ ] `pytest` passes with no failures

### TUI-007: Status Indicators + Animated Spinners
**Description:** As a user, I want animated spinners and status indicators so that I know when the system is processing, and can see success/error/warning states.

**Implementation Notes:**
- Create `src/mARCH/ui/tui_widgets/spinners.py` with `SpinnerWidget(Static)` using Textual timer for animation
- Spinner frames: braille pattern ⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏ cycling at ~100ms
- Create `src/mARCH/ui/tui_widgets/status_bar.py` with `StatusBar(Static)` showing current operation
- Status icons: ✓ (success/green), ✗ (error/red), ⚠ (warning/yellow), ● (info/blue)
- Wire status bar into `tui_app.py` footer zone

**Acceptance Criteria:**
- [ ] `SpinnerWidget` animates through braille frames on a timer
- [ ] `StatusBar` displays current operation text with appropriate icon
- [ ] Status icons map correctly: success=✓, error=✗, warning=⚠, info=●
- [ ] Spinner stops and clears when operation completes
- [ ] Unit test verifies spinner frame cycling
- [ ] `ruff check` passes with no errors
- [ ] `pytest` passes with no failures

### TUI-008: Plan Mode Display Modal
**Description:** As a user, I want a modal for viewing and acting on plans so that I can review plan summaries and choose an execution action.

**Implementation Notes:**
- Create `src/mARCH/ui/tui_widgets/plan_modal.py` with `PlanModal(ModalScreen)`
- Display plan summary as rendered markdown and task list
- Action buttons with keyboard shortcuts: (e)xit_only, (i)nteractive, (a)utopilot, (f)leet
- Return selected action string via `dismiss()`
- Replace current `plan_display.py` approval flow with this modal in `tui_app.py`

**Acceptance Criteria:**
- [ ] `PlanModal` subclasses `textual.screen.ModalScreen`
- [ ] Modal renders plan summary as markdown
- [ ] Keyboard shortcut 'e' dismisses with "exit_only"
- [ ] Keyboard shortcut 'i' dismisses with "interactive"
- [ ] Keyboard shortcut 'a' dismisses with "autopilot"
- [ ] Keyboard shortcut 'f' dismisses with "autopilot_fleet"
- [ ] Unit test verifies dismiss values for each action
- [ ] `ruff check` passes with no errors
- [ ] `pytest` passes with no failures

### TUI-009: Theme System + Color Constants
**Description:** As a developer, I want a centralized theme and color system so that all widgets use consistent brand colors and support future light/dark mode toggling.

**Implementation Notes:**
- Create `src/mARCH/ui/theme.py` with a `Theme` dataclass containing color fields (brand, text, background, accent, etc.)
- Create `src/mARCH/ui/colors.py` with color constants: brand, selected, statusSuccess, statusError, statusWarning, statusInfo, mode colors
- Provide `get_theme()` function returning the active theme (dark mode default)
- Support optional light mode toggle (store preference in theme)
- Wire brand color into header borders, mode indicator, and status bar across all widgets

**Acceptance Criteria:**
- [ ] `Theme` dataclass exists with documented color fields
- [ ] `colors.py` exports named color constants
- [ ] `get_theme()` returns a valid `Theme` instance
- [ ] Dark mode is the default; light mode is available via toggle
- [ ] Unit test verifies `get_theme()` returns expected color values
- [ ] `ruff check` passes with no errors
- [ ] `pytest` passes with no failures

## 4. Non-Goals (Out of Scope)

- **Mouse support** — Keyboard-only for this iteration
- **Plugin/extension system** — No third-party widget API
- **Configuration file for themes** — Themes are code-defined, not user-configurable YAML/TOML
- **Deleting old TUI code** — Old Rich/prompt_toolkit code stays until all new widgets are proven
- **Mobile/web terminal support** — Standard terminal emulators only

## 5. Technical Considerations

- **Textual is already a dependency** (`textual>=0.25.0` in pyproject.toml) but unused — no install needed
- **Async compatibility** — Textual is async-first; `agent_state.py` already uses asyncio, so integration is natural
- **Backward compatibility** — Wire new Textual app as the default entry, but keep old TUI importable
- **Testing** — Use `textual.testing` for widget/app tests where possible; fall back to unit tests for pure logic
- **File structure** — All new widgets live under `src/mARCH/ui/tui_widgets/`; core files `tui_app.py`, `theme.py`, `colors.py` live in `src/mARCH/ui/`

## 6. Open Questions

- Should we expose a `--legacy-tui` CLI flag for users who prefer the old Rich-based TUI?
- What is the minimum terminal size we should support (e.g., 80×24)?
- Should the theme system integrate with Textual's built-in CSS theming or remain independent?
