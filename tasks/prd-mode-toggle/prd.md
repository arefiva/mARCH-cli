# PRD: Fix Mode Toggle (Plan / Autopilot / Normal)

## 1. Introduction / Overview

The mARCH CLI has three modes — **interactive** (default), **plan**, and **autopilot** — that
should be cycled by pressing **Shift+Tab** in the input bar, exactly mirroring the original
Copilot CLI (JS edition).

The building blocks already exist:

- `InputBar` (Textual widget) binds `backtab` → `action_cycle_mode()`, which cycles
  `_mode` between `INTERACTIVE / PLAN / AUTOPILOT` and updates the on-screen label.
- `ModeManager.cycle_mode()` cycles `ExecutionMode` in the same order.
- `PlanModeDetector` knows the `[[PLAN]]` prefix.

**What is broken**: the mode change is entirely cosmetic. `MarchApp` does not:
1. Post a visible notification when the mode changes.
2. Prefix messages with `[[PLAN]]` when in plan mode.
3. Inject the plan-mode or autopilot system-prompt section before sending to the AI.

---

## 2. Goals

- Shift+Tab cycles INTERACTIVE → PLAN → AUTOPILOT → INTERACTIVE and shows a system
  message in the conversation view announcing the new mode.
- When InputBar is in PLAN mode, every submitted message is sent to the AI prefixed
  with `[[PLAN]]` (the conversation view shows the original text, without the prefix).
- When InputBar is in PLAN mode, the system prompt includes the canonical
  `<plan_mode>` block copied verbatim from the original Copilot CLI.
- When InputBar is in AUTOPILOT mode, the system prompt includes the canonical
  non-interactive-mode paragraph copied verbatim from the original Copilot CLI.
- All existing tests continue to pass.

---

## 3. User Stories

### US-001: Mode Change Notification

**Description:** As a user, I want to see a notification in the conversation view when
I press Shift+Tab so that I can confirm which mode is now active.

**Implementation Notes:**
- Add `class ModeChanged(Message)` as a nested class inside `InputBar`
  (`src/mARCH/ui/tui_widgets/input_bar.py`). The message must carry `mode: InputMode`.
- In `InputBar.action_cycle_mode()`, after updating `self._mode`, call
  `self.post_message(InputBar.ModeChanged(self._mode))`.  Do NOT raise any
  exception or call `app.exit()` from this method.
- In `MarchApp` (`src/mARCH/ui/tui_app.py`), add event handler
  `on_input_bar_mode_changed(self, event: InputBar.ModeChanged)`.
  The handler must: (a) query `ConversationView` and (b) call
  `conv.add_message(MessageRole.SYSTEM, f"⚡ Mode changed to: {event.mode.value}")`.
- Import `InputBar` in `tui_app.py` where needed; it is already imported via
  `from mARCH.ui.tui_widgets import ConversationView, InputBar`.
- Do NOT change `CYCLE_ORDER`, `MODE_COLORS`, or `InputMode` enum values.

**Preservation Constraints:**
- `src/mARCH/ui/tui_widgets/input_bar.py` — must not be deleted
- `src/mARCH/ui/tui_widgets/input_bar.py::InputBar` — must remain importable
- `src/mARCH/ui/tui_widgets/input_bar.py::InputMode` — must remain importable
- `src/mARCH/ui/tui_widgets/input_bar.py::CYCLE_ORDER` — must remain importable
- `src/mARCH/ui/tui_app.py::MarchApp` — must remain importable

**Acceptance Criteria:**
- [ ] `InputBar.ModeChanged` is a Textual `Message` subclass importable from
      `mARCH.ui.tui_widgets.input_bar`
- [ ] `InputBar.ModeChanged` carries a `mode` attribute of type `InputMode`
- [ ] Unit test: `InputBar.action_cycle_mode()` calls `post_message` with an
      `InputBar.ModeChanged` instance whose `.mode` equals the next mode
- [ ] Unit test: `MarchApp.on_input_bar_mode_changed` calls
      `ConversationView.add_message` with `MessageRole.SYSTEM` and a string that
      contains the new mode name
- [ ] All pre-existing tests in `tests/test_tui_rewrite.py` continue to pass
- [ ] `ruff check` passes with no errors
- [ ] `pytest` passes with no failures

---

### US-002: Message Prefix Injection Based on Mode

**Description:** As a user in PLAN mode, I want my messages sent to the AI with
`[[PLAN]]` prepended so the AI enters plan-mode behaviour, while the conversation
view shows my original text without that prefix.

**Implementation Notes:**
- In `MarchApp.on_input_submitted` (`tui_app.py`), after validating `text` is
  non-empty, read the current mode:
  ```python
  from mARCH.ui.tui_widgets.input_bar import InputBar, InputMode
  input_bar = self.query_one("#input-bar", InputBar)
  current_mode = input_bar.current_mode
  ```
- Show the *original* `text` (no prefix) in `ConversationView` and call
  `self._agent.add_user_message(text)` with the original text.
- Call `self._stream_ai_response(text, current_mode)` — add `current_mode` as
  the second argument.
- In `_stream_ai_response(self, user_text: str, mode: InputMode = InputMode.INTERACTIVE)`:
  - After obtaining `messages` from `agent.get_conversation_context(...)`, find
    the last message with `role == "user"` in the list.
  - If `mode == InputMode.PLAN`: replace its `"content"` value with
    `f"[[PLAN]] {user_text}"` (use the original `user_text`, not the already-stored
    agent history value, to avoid double-modification on retry).
  - If `mode == InputMode.AUTOPILOT`: no prefix change is needed; the system
    prompt (handled in US-003) already carries the autopilot instruction.
- Do NOT store the prefixed text in the agent's history; only modify the
  transient `messages` list used for the current API call.

**Preservation Constraints:**
- `src/mARCH/ui/tui_app.py::MarchApp` — must not be deleted
- `src/mARCH/ui/tui_app.py::MarchApp.on_input_submitted` — must remain callable
- `src/mARCH/ui/tui_app.py::MarchApp._stream_ai_response` — must remain callable
- `src/mARCH/ui/tui_widgets/input_bar.py::InputBar.current_mode` — must remain accessible

**Acceptance Criteria:**
- [ ] Unit test: submitting text when InputBar is in PLAN mode results in the
      ConversationView showing the original text (without `[[PLAN]]`) as the USER message
- [ ] Unit test: `_stream_ai_response` sends `[[PLAN]] {text}` as the last user
      message content when mode is `InputMode.PLAN`
- [ ] Unit test: `_stream_ai_response` sends plain `{text}` (no prefix) when mode
      is `InputMode.INTERACTIVE`
- [ ] Unit test: edge case — submitting empty/whitespace text does NOT add any
      message to ConversationView regardless of mode
- [ ] Unit test: `Agent.get_conversation_context()` stores the original text
      (without `[[PLAN]]`) even when in PLAN mode
- [ ] All pre-existing tests in `tests/test_tui_rewrite.py` continue to pass
- [ ] `ruff check` passes with no errors
- [ ] `pytest` passes with no failures

---

### US-003: System Prompt Injection for Plan and Autopilot Modes

**Description:** As a user, I want the AI to receive the correct mode-specific system
prompt so that it behaves in full plan mode or full autopilot mode, exactly as in the
original Copilot CLI.

**Implementation Notes:**
- Extend `src/mARCH/core/plan_mode.py` with two constants and one helper function.
  Do NOT modify `PlanModeDetector`.

  ```python
  PLAN_MODE_SYSTEM_PROMPT = """
  <plan_mode>
  When user messages are prefixed with [[PLAN]], you handle them in "plan mode". In this mode:
  1. If this is a new request or requirements are unclear, use the ask_user tool to confirm understanding and resolve ambiguity
  2. Analyze the codebase to understand the current state
  3. Create a structured implementation plan (or update the existing one if present)
  4. Save the plan to: plan.md in the session workspace

  The plan should include:
  - A brief statement of the problem and proposed approach
  - A list of todos (tracking is handled via SQL, not markdown checkboxes)
  - Any notes or considerations

  Guidelines:
  - Use the **create** or **edit** tools to write plan.md in the session workspace.
  - Do NOT ask for permission to create or update plan.md in the session workspace—it's designed for this purpose.
  - After writing plan.md, provide a brief summary of the plan in your response. Include the key points so the user doesn't need to open the file separately.
  - Do NOT include time or date estimates of any kind when generating a plan or timeline.
  - Do NOT start implementing unless the user explicitly asks (e.g., "start", "get to work", "implement it").
    When they do, read plan.md first to check for any edits the user may have made.

  Before finalizing a plan, use ask_user to confirm any assumptions about:
  - Feature scope and boundaries (what's in/out)
  - Behavioral choices (defaults, limits, error handling)
  - Implementation approach when multiple valid options exist

  After saving plan.md, reflect todos into the SQL database for tracking:
  - INSERT todos into the `todos` table (id, title, description)
  - INSERT dependencies into `todo_deps` (todo_id, depends_on)
  - Use status values: 'pending', 'in_progress', 'done', 'blocked'
  - Update todo status as work progresses

  plan.md is the human-readable source of truth. SQL provides queryable structure for execution.
  </plan_mode>
  """

  AUTOPILOT_SYSTEM_PROMPT = (
      "You are running in non-interactive mode and have no way to communicate with "
      "the user. You must work on the task until it is completed. Do not stop to ask "
      "questions or request confirmation - make reasonable assumptions and proceed "
      "autonomously. Complete the entire task before finishing.\n"
  )
  ```

- Add `build_mode_system_prompt(base_prompt: str, mode: "InputMode") -> str` that
  returns:
  - `base_prompt + "\n" + PLAN_MODE_SYSTEM_PROMPT.strip()` for PLAN
  - `AUTOPILOT_SYSTEM_PROMPT.strip() + "\n\n" + base_prompt` for AUTOPILOT
  - `base_prompt` for INTERACTIVE (unchanged)
  - Import `InputMode` inside the function with `from mARCH.ui.tui_widgets.input_bar import InputMode`
    to avoid a circular-import (plan_mode → ui → plan_mode). Use a `TYPE_CHECKING` guard
    for the type hint.

- In `MarchApp._stream_ai_response` (`tui_app.py`): after building `messages`,
  locate the system message (role `"system"`) in the list.  If found, replace its
  `"content"` with `build_mode_system_prompt(original_content, mode)`.  If no
  system message exists, prepend one:
  `{"role": "system", "content": build_mode_system_prompt("", mode)}`.

**Preservation Constraints:**
- `src/mARCH/core/plan_mode.py` — must not be deleted
- `src/mARCH/core/plan_mode.py::PlanModeDetector` — must remain importable and unchanged
- `src/mARCH/core/plan_mode.py::PlanModeDetector.PLAN_PREFIX` — value must remain `"[[PLAN]]"`

**Acceptance Criteria:**
- [ ] `PLAN_MODE_SYSTEM_PROMPT` is importable from `mARCH.core.plan_mode` and contains
      the substring `"[[PLAN]]"` and `"plan mode"` and `"plan.md"`
- [ ] `AUTOPILOT_SYSTEM_PROMPT` is importable from `mARCH.core.plan_mode` and contains
      `"non-interactive mode"` and `"autonomously"`
- [ ] `build_mode_system_prompt(base, InputMode.PLAN)` returns a string that ends
      with the plan mode XML block and contains `"[[PLAN]]"`
- [ ] `build_mode_system_prompt(base, InputMode.AUTOPILOT)` returns a string that
      starts with the autopilot paragraph and contains `"autonomously"`
- [ ] `build_mode_system_prompt(base, InputMode.INTERACTIVE)` returns `base` unchanged
- [ ] Unit test: `_stream_ai_response` in PLAN mode sends a system message that
      contains `"[[PLAN]]"` and `"plan mode"`
- [ ] Unit test: `_stream_ai_response` in AUTOPILOT mode sends a system message that
      contains `"non-interactive mode"` and `"autonomously"`
- [ ] `PlanModeDetector.is_plan_request` and `.extract_content` still work as before
- [ ] `ruff check` passes with no errors
- [ ] `pytest` passes with no failures

---

## 4. Non-Goals (Out of Scope)

- Autopilot fleet mode (`AUTOPILOT_FLEET`) — not toggled via Shift+Tab, not in scope.
- Shell mode (`SHELL`) — not in scope.
- Persisting the selected mode across sessions.
- Auto-approval of tool calls in autopilot mode (separate feature).
- The legacy `MARCH_REPL` / prompt-toolkit path — mode toggle there already works.

---

## 5. Technical Considerations

- **Circular import risk**: `plan_mode.py` must not import from `tui_widgets` at
  module level. Use `TYPE_CHECKING` guard + inline import inside the function.
- **Textual message routing**: `post_message` requires the widget to be mounted.
  The existing test suite tests `InputBar` without mounting; therefore the unit
  tests for US-001 should mock `post_message` rather than rely on actual Textual
  routing.
- **Backtab binding scope**: `backtab` is bound at `InputBar` widget level.
  Textual bubbles key events from the focused widget (`#march-input` / Input) up
  through parent widgets.  `Input` does not bind `backtab` itself, so the event
  reaches `InputBar`.  If integration tests reveal the binding does not fire,
  escalate it to `MarchApp.BINDINGS` and call
  `self.query_one("#input-bar", InputBar).action_cycle_mode()`.
- **Message display text**: The conversation view should always show the user's
  *original* text; the `[[PLAN]]` prefix belongs only in the transient messages
  list passed to the AI client.

---

## 6. Open Questions

None — all design decisions resolved by cross-referencing the original JS source.
