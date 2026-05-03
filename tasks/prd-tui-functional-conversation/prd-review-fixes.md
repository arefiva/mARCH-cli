# PRD: TUI Functional Conversation — Code Review Fixes

## 1. Introduction / Overview

The `feature/tui-functional-conversation` branch wired ConversationView and InputBar
into MarchApp and added AI streaming responses. A code review identified **8 issues**
spanning a critical functionality gap (slash commands, exit handling, and plan mode all
removed), two high-severity streaming bugs, a markup injection vulnerability, dead
code accumulation, and missing test coverage. This PRD captures each fix so the issues
can be resolved incrementally on the same branch.

## 2. Goals

- Fix streaming error handling so `finish_streaming()` is always called and errors are
  logged and visually distinguished from normal assistant text.
- Close the Rich markup injection path in user-facing widgets.
- Restore slash command dispatch, exit handling, and mode cycling in the TUI so
  functionality removed during the migration is available again.
- Remove dead code and unused widgets that create maintenance burden.

---

## 3. User Stories

### US-001: Harden Streaming Error Handling and Add Streaming Tests

**Description:** As a user, I want AI streaming errors to be handled gracefully — with
cleanup, logging, and a visually distinct error indicator — so that the conversation
state is never corrupted and I can tell when something went wrong.

**Implementation Notes:**

- In `src/mARCH/ui/tui_app.py`, restructure `_stream_ai_response` so that the
  `call_from_thread(conv.start_streaming)` call on line 81 is inside the `try` block,
  not before it.
- Use `try / except Exception / finally` so that `conv.finish_streaming()` is called
  in the `finally` block regardless of where the error occurs.
- In the `except` branch, log the exception with `logger.error(...)`. Add
  `import logging` and `logger = logging.getLogger(__name__)` at module level.
- Display errors with a `MessageRole.SYSTEM` role (or a distinct `[bold red]ERROR[/]`
  prefix) instead of appending raw text to the assistant bubble. Do NOT leak raw
  exception `repr` — use `str(e)` and truncate if longer than 200 chars.
- Add async Textual pilot tests in `tests/test_tui_rewrite.py`:
  (a) mock `ai_client.stream_chat` to yield chunks and verify assistant message
  appears and `_streaming_widget` is reset to `None`;
  (b) mock `ai_client.stream_chat` to raise `RuntimeError` and verify error message
  appears with SYSTEM role and `finish_streaming()` was called;
  (c) verify `agent.add_assistant_message` is called with the full concatenated
  response on success.

**Preservation Constraints:**

- `src/mARCH/ui/tui_app.py::MarchApp`
- `src/mARCH/ui/tui_widgets/conversation.py::ConversationView`
- `src/mARCH/ui/tui_widgets/conversation.py::ConversationView.start_streaming`
- `src/mARCH/ui/tui_widgets/conversation.py::ConversationView.finish_streaming`

**Acceptance Criteria:**

- [ ] `start_streaming()` call is inside the `try` block in `_stream_ai_response`.
- [ ] `finish_streaming()` is called in a `finally` block so it executes on success,
      error, and cancellation.
- [ ] Streaming errors are logged via `logger.error(...)`.
- [ ] Error messages displayed in ConversationView use a visually distinct role or
      style (not plain assistant text).
- [ ] Unit test: mock `stream_chat` raises `RuntimeError` — error message widget
      appears in ConversationView and `_streaming_widget` is `None` after.
- [ ] Unit test: mock `stream_chat` yields `["Hel", "lo"]` — assistant message
      content equals `"Hello"` and `agent.add_assistant_message("Hello")` was called.
- [ ] Unit test: when `start_streaming` raises (e.g., app shutting down),
      `finish_streaming` is still called and no `NameError` occurs.
- [ ] `ruff check` passes with no errors.
- [ ] `pytest` passes with no failures.

---

### US-002: Escape Rich Markup in User-Supplied Content

**Description:** As a user, I want my messages and tool call details to be displayed
literally so that Rich markup codes in my input cannot spoof the UI or break
rendering.

**Implementation Notes:**

- Add `from rich.markup import escape` to `src/mARCH/ui/tui_widgets/message.py`.
- In `MessageWidget.__init__`, escape the `content` parameter before interpolation:
  `super().__init__(f"{label}  {escape(content)}", markup=True)`.
- In `MessageWidget.append_chunk`, escape accumulated `_content`:
  `self.update(f"{label}  {escape(self._content)}")`.
- Only escape the message body, not the role label (which uses trusted markup).
- Add `from rich.markup import escape` to `src/mARCH/ui/tui_widgets/tool_modal.py`.
- In `ToolModal.compose()`, escape `self._tool_name`, `self._description`, and
  `self._arguments` before interpolation into the `Label` constructors.
- Add tests in `tests/test_tui_rewrite.py` that construct a `MessageWidget` with
  content `"[bold red]injected[/]"` and verify the `_content` stored internally is
  the unescaped original but the rendered output contains literal brackets.

**Preservation Constraints:**

- `src/mARCH/ui/tui_widgets/message.py::MessageWidget`
- `src/mARCH/ui/tui_widgets/message.py::MessageWidget.append_chunk`
- `src/mARCH/ui/tui_widgets/tool_modal.py::ToolModal`

**Acceptance Criteria:**

- [ ] Unit test: `MessageWidget(USER, "[bold]hi[/]")` renders with literal `[bold]`
      visible (not bold text).
- [ ] Unit test: after `append_chunk("[red]x[/]")`, rendered output contains literal
      `[red]` brackets.
- [ ] Unit test: `ToolModal(tool_name="[bold]rm[/]")` renders with literal `[bold]`
      in the tool name label.
- [ ] Role labels (USER, ASSISTANT, etc.) still render with color styling.
- [ ] `ruff check` passes with no errors.
- [ ] `pytest` passes with no failures.

---

### US-003: Restore Slash Command Dispatch and Exit Handling in TUI

**Description:** As a user, I want to type `/help`, `/status`, `/model`, `exit`, and
other slash and exit commands in the TUI input bar and have them work, so that the TUI
provides the same command surface as the old REPL.

**Implementation Notes:**

- Create `src/mARCH/ui/tui_session.py` with a `TuiSession` dataclass (or plain class)
  that holds references to: `ai_client`, `agent`, `slash_parser`, `mode_manager`,
  `config_manager`, `github_integration`, `experimental_mode: bool`,
  `current_model: str`. This avoids importing `cli.AppContext` into the UI layer
  (circular import risk). Keep it lightweight — no methods that call `console.print`.
- In `src/mARCH/cli/cli.py`, update the `main()` function to construct a `TuiSession`
  from `AppContext` fields and pass it to `MarchApp(session=session)` instead of the
  current `ai_client=` and `agent=` kwargs.
- In `src/mARCH/ui/tui_app.py`, update `MarchApp.__init__` to accept
  `session: TuiSession | None = None` and fall back to extracting `ai_client` /
  `agent` from it. Keep the old `ai_client=` / `agent=` kwargs working for backward
  compatibility with existing tests.
- In `on_input_submitted`, implement dispatch precedence:
  1. Empty / whitespace → return early (already done).
  2. Exit commands (`exit`, `quit`, `:q`, `q!`) → call `self.exit()`.
  3. Slash commands (starts with `/`) → parse with `slash_parser`, execute, display
     output as a SYSTEM message in ConversationView. For commands that produce text
     output (`/help`, `/status`, `/model`, `/lsp`, `/feedback`), capture the output
     and display it. For state-mutating commands (`/model <name>`, `/experimental`),
     execute the mutation and show a confirmation SYSTEM message. For interactive
     commands (`/login`, `/setup`) that require `console.input`, show a SYSTEM message
     saying "Use the CLI directly for interactive commands like /login".
  4. Plan mode (`[[PLAN]]` prefix) → show a SYSTEM message indicating plan mode is
     not yet supported in the TUI (defer full implementation).
  5. Normal text → existing streaming path.
- Do NOT add the user message to conversation history for exit or slash commands —
  only for normal AI messages.
- Add tests: (a) typing `exit` calls `app.exit()`; (b) typing `/help` shows a SYSTEM
  message; (c) typing `/model` shows current model info as SYSTEM message.

**Preservation Constraints:**

- `src/mARCH/cli/cli.py::main`
- `src/mARCH/cli/cli.py::AppContext`
- `src/mARCH/cli/cli.py::handle_slash_command`
- `src/mARCH/ui/tui_app.py::MarchApp`
- `src/mARCH/core/slash_commands.py::SlashCommandParser`

**Acceptance Criteria:**

- [ ] `TuiSession` class exists in `src/mARCH/ui/tui_session.py` and holds all
      required fields (ai_client, agent, slash_parser, mode_manager, config_manager,
      github_integration).
- [ ] `cli.py::main()` constructs a `TuiSession` and passes it to `MarchApp`.
- [ ] `MarchApp(session=None)` and `MarchApp()` still work (backward compat with
      existing tests).
- [ ] Typing `exit` or `quit` in the TUI exits the app.
- [ ] Typing `/help` displays a SYSTEM message with command help text.
- [ ] Typing `/status` displays a SYSTEM message with current status.
- [ ] Typing `/model` displays a SYSTEM message with the current model name.
- [ ] Slash and exit commands do NOT add a USER message to ConversationView.
- [ ] Normal text input still streams an AI response (existing behavior preserved).
- [ ] Unit test: exit command triggers `app.exit()`.
- [ ] Unit test: `/help` input produces a SYSTEM MessageWidget.
- [ ] `ruff check` passes with no errors.
- [ ] `pytest` passes with no failures.

---

### US-004: Connect Mode Cycling to Real ModeManager

**Description:** As a user, I want Shift+Tab mode cycling in the TUI to change the
actual execution mode (via ModeManager) so that the mode indicator reflects real
state and mode-dependent behavior works.

**Implementation Notes:**

- In `src/mARCH/ui/tui_widgets/input_bar.py`, add an optional `mode_manager`
  parameter to `InputBar.__init__`. Store as `self._mode_manager`.
- In `action_cycle_mode()`, if `self._mode_manager` is not None, call
  `self._mode_manager.cycle_mode()` and sync `self._mode` from the result. Otherwise
  keep the current local-only cycling as fallback.
- Note: `ModeManager.cycle_mode()` cycles through 3 modes (interactive → plan →
  autopilot) while InputBar's `CYCLE_ORDER` has 4 (adds SHELL). Align by either
  removing SHELL from `CYCLE_ORDER` (it's a future placeholder) or adding SHELL to
  `ModeManager`. Prefer removing SHELL from `CYCLE_ORDER` since `ExecutionMode.SHELL`
  is marked "future" in execution_mode.py.
- In `src/mARCH/ui/tui_app.py`, when composing InputBar, pass the `mode_manager`
  from `self._session` if available.
- In `on_input_submitted`, read `InputBar.current_mode` and use it to decide behavior:
  if mode is PLAN, prepend `[[PLAN]]` to the user text before dispatching to the AI
  (or handle as plan mode).
- Add tests: cycle mode with a mock ModeManager and verify the mode_manager's
  `cycle_mode()` was called.

**Preservation Constraints:**

- `src/mARCH/ui/tui_widgets/input_bar.py::InputBar`
- `src/mARCH/ui/tui_widgets/input_bar.py::InputMode`
- `src/mARCH/ui/tui_widgets/input_bar.py::CYCLE_ORDER`
- `src/mARCH/core/execution_mode.py::ModeManager`

**Acceptance Criteria:**

- [ ] `InputBar.__init__` accepts an optional `mode_manager` keyword argument.
- [ ] When `mode_manager` is provided, `action_cycle_mode()` calls
      `mode_manager.cycle_mode()`.
- [ ] When `mode_manager` is `None`, cycling still works locally (backward compat).
- [ ] SHELL mode is removed from `CYCLE_ORDER` or ModeManager is extended to include
      it — the two are consistent.
- [ ] Unit test: cycling with a mock ModeManager calls `cycle_mode()` and updates
      the label.
- [ ] `ruff check` passes with no errors.
- [ ] `pytest` passes with no failures.

---

### US-005: Remove Dead Code and Unused Widgets

**Description:** As a developer, I want dead handler functions and unused widget
modules cleaned up so that the codebase is easier to navigate and maintain.

**Implementation Notes:**

- In `src/mARCH/cli/cli.py`, remove the following functions that are no longer called
  after slash command handling moved to the TUI (US-003): `handle_slash_command`,
  `handle_login_command`, `handle_logout_command`, `handle_model_command`,
  `handle_lsp_command`, `handle_feedback_command`, `handle_experimental_command`,
  `handle_status_command`, `handle_setup_command`, `handle_plan_mode`,
  `handle_regular_input`. Keep `print_help_text` and `print_banner` — they may still
  be useful.
- **Before removing**, check `tests/test_phase2_cli.py` which imports
  `handle_model_command`, `handle_experimental_command`, `handle_status_command`.
  Update those tests to either: (a) test the equivalent TUI behavior instead, or
  (b) move the reusable logic to a shared module and test it there.
- Evaluate `HeaderWidget`, `StatusBar`, and `SpinnerWidget` in
  `src/mARCH/ui/tui_widgets/`. These are defined but never mounted by `MarchApp`.
  Keep them in the package (they are part of the widget library for future use) but
  fix the `StatusBar.set_status` bug: change `__init__` to
  `super().__init__("", markup=True)` and remove `markup=True` from the
  `self.update(...)` call.
- Evaluate `src/mARCH/ui/theme.py` and `src/mARCH/ui/colors.py`. If no widget
  imports them, add a `# TODO: integrate theme system` comment but keep them — they
  represent intentional design work.
- Remove unused imports from `cli.py` that were only needed by the removed functions
  (e.g., `PlanModeDetector`, `PlanGenerator`, `AutopilotExecutor`, `PlanApprovalUI`,
  `PlanResultDisplay` if no other code uses them).

**Preservation Constraints:**

- `src/mARCH/cli/cli.py::main`
- `src/mARCH/cli/cli.py::AppContext`
- `src/mARCH/cli/cli.py::print_help_text`
- `src/mARCH/ui/tui_widgets/__init__.py`
- `tests/test_phase2_cli.py` — must still pass (update imports/tests as needed)

**Acceptance Criteria:**

- [ ] `handle_slash_command`, `handle_plan_mode`, `handle_regular_input`, and all
      individual slash handler functions are removed from `cli.py`.
- [ ] `tests/test_phase2_cli.py` is updated to reflect the removal and still passes.
- [ ] `StatusBar.__init__` passes `markup=True` to `super().__init__` and
      `set_status` no longer passes `markup=True` to `self.update()`.
- [ ] No unused imports remain in `cli.py` after function removal.
- [ ] `src/mARCH/ui/tui_widgets/__init__.py` still exports `HeaderWidget`,
      `SpinnerWidget`, `StatusBar` (kept for future use).
- [ ] `ruff check` passes with no errors.
- [ ] `pytest` passes with no failures.

---

## 4. Non-Goals (Out of Scope)

- Full TUI-native implementation of interactive commands (`/login`, `/setup`) that
  require password input. These will show a "use CLI directly" message for now.
- Full plan mode execution in the TUI (`[[PLAN]]` prefix). The dispatch detects it
  and shows a "not yet supported" message.
- Redesigning the theme system or integrating it into all widgets.
- Adding new slash commands or changing existing command behavior.

## 5. Technical Considerations

- **Circular import risk:** `tui_app.py` must NOT import `cli.py::AppContext`. A
  neutral `TuiSession` dataclass in `src/mARCH/ui/tui_session.py` bridges the gap.
- **Mode inconsistency:** `ModeManager.cycle_mode()` cycles 3 modes (interactive →
  plan → autopilot) while `InputBar.CYCLE_ORDER` has 4 (adds SHELL). US-004 resolves
  this by aligning the two.
- **Console vs TUI output:** The existing slash command handlers use `console.print()`
  which doesn't render inside Textual. US-003 reimplements output display via
  ConversationView SYSTEM messages rather than calling the old handlers directly.
- **Test imports:** `tests/test_phase2_cli.py` imports handler functions that US-005
  removes. Those tests must be updated in the same story.

## 6. Open Questions

- Should `/login` and `/setup` (interactive commands requiring password input) be
  implemented as TUI modals in a future story, or remain CLI-only?
- Should SHELL mode be fully removed from the UI or kept as a disabled placeholder?
