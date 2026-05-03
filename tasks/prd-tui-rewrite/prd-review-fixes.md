# PRD: TUI Rewrite — Code Review Fixes

## 1. Introduction / Overview

The `feature/tui-rewrite` branch introduces a Textual-based TUI for the mARCH CLI.
A code review identified **8 issues** ranging from critical runtime crashes and a
security vulnerability to dead code and missing behavioral tests. This PRD captures
each fix as a user story so the issues can be resolved incrementally without
regressing the existing work on the branch.

## 2. Goals

- Eliminate all runtime crashes in TUI widgets (SpinnerWidget, StatusBar, InputBar).
- Close the Rich markup injection vulnerability in user-facing widgets.
- Restore functional CLI by wiring `MarchApp` to the real TUI widgets.
- Remove dead code or integrate the unused theme system into widgets.
- Tighten linting configuration (N999 scoping).
- Add behavioral tests that exercise actual widget interactions.

---

## 3. User Stories

### US-001: Fix Widget Initialization and Runtime Crashes

**Description:** As a developer, I want SpinnerWidget, StatusBar, and InputBar to
be robust against lifecycle timing and edge-case inputs so that the TUI never crashes
from predictable conditions.

**Implementation Notes:**

- **SpinnerWidget** (`src/mARCH/ui/tui_widgets/spinners.py`):
  - Add `self._timer: Timer | None = None` in `__init__` (after line 20).
  - In `start()`, guard with `if self._timer is not None:` before calling
    `self._timer.resume()`.
  - In `stop()`, guard with `if self._timer is not None:` before calling
    `self._timer.pause()`.
- **StatusBar** (`src/mARCH/ui/tui_widgets/status_bar.py`):
  - Change the `__init__` call to `super().__init__("", markup=True)` so the
    widget accepts markup from the start.
  - Remove `markup=True` from the `self.update(...)` call on line 43; `update()`
    does not accept that keyword argument.
- **InputBar** (`src/mARCH/ui/tui_widgets/input_bar.py`):
  - At the top of `action_cycle_mode()`, add `if not CYCLE_ORDER: return` to
    prevent `ValueError` / `ZeroDivisionError`.

**Acceptance Criteria:**

- [ ] Unit test: calling `SpinnerWidget().start()` before mount does **not** raise
      `AttributeError` (returns silently).
- [ ] Unit test: calling `SpinnerWidget().stop()` before mount does **not** raise
      `AttributeError`.
- [ ] Unit test: `StatusBar().set_status("ok", "success")` does **not** raise
      `TypeError`.
- [ ] Unit test: after `set_status("msg", "error")`, the widget's internal
      `_message` equals `"msg"`.
- [ ] Unit test: `InputBar.action_cycle_mode()` with an empty `CYCLE_ORDER` does
      **not** raise.
- [ ] `ruff check` passes with no errors.
- [ ] `pytest` passes with no failures.

---

### US-002: Fix Rich Markup Injection in User-Facing Widgets

**Description:** As a user, I want my messages and tool call details to be displayed
literally so that Rich markup codes in content cannot spoof the UI or break
rendering.

**Implementation Notes:**

- Add `from rich.markup import escape` to both `message.py` and `tool_modal.py`.
- **MessageWidget** (`src/mARCH/ui/tui_widgets/message.py`):
  - In `__init__`, escape the `content` parameter before interpolation:
    `super().__init__(f"{label}  {escape(content)}", markup=True)`.
  - In `append_chunk`, escape the accumulated `_content`:
    `self.update(f"{label}  {escape(self._content)}")`.
- **ToolModal** (`src/mARCH/ui/tui_widgets/tool_modal.py`):
  - In `compose()`, escape `self._tool_name`, `self._description`, and
    `self._arguments` before interpolation into the `Label` constructors.
- Do **not** escape static label prefixes (`[bold]Tool:[/bold]`) — only
  user-controlled values.

**Acceptance Criteria:**

- [ ] Unit test: `MessageWidget(role, "[red]evil[/red]")` renders the literal
      text `[red]evil[/red]`, not red-styled text.
- [ ] Unit test: `append_chunk("[bold]x[/bold]")` accumulates the literal markup
      string, not formatted text.
- [ ] Unit test: `ToolModal(tool_name="[red]bad[/red]")` renders the literal
      string in the tool label.
- [ ] Existing tests continue to pass.
- [ ] `ruff check` passes with no errors.
- [ ] `pytest` passes with no failures.

---

### US-003: Wire Up MarchApp With Actual TUI Widgets

**Description:** As a user, I want `MarchApp` to compose the real TUI widgets
(HeaderWidget, ConversationView, InputBar, StatusBar) so that the CLI is functional
when launched.

**Implementation Notes:**

- **`src/mARCH/ui/tui_app.py`:**
  - Import `HeaderWidget`, `ConversationView`, `InputBar`, `StatusBar`, and
    `SpinnerWidget` from `mARCH.ui.tui_widgets`.
  - Replace the two `Static` placeholders in `compose()` with:
    `HeaderWidget`, `ConversationView` (id=`"conversation-area"`),
    `InputBar` (id=`"input-bar"`), `StatusBar`.
  - Remove the Textual built-in `Header`/`Footer` imports if no longer used.
  - Ensure CSS selectors `#conversation-area` and `#input-bar` still match
    (set `id` on the new widgets).
- Wire an `on_input_submitted` handler (or the equivalent Textual message) that
  reads text from the `InputBar`'s `Input` child, adds a user message via
  `ConversationView.add_message()`, and clears the input field.
- This story is **not** responsible for AI integration or slash-command handling —
  only for composing the widgets and handling basic message submission so the TUI
  is visually complete and interactive.

**Acceptance Criteria:**

- [ ] Async test: `MarchApp` mounts `HeaderWidget`, `ConversationView`, `InputBar`,
      and `StatusBar` (query selectors find them).
- [ ] Async test: submitting text in the input adds a `MessageWidget` to the
      `ConversationView`.
- [ ] Update existing `test_march_app_mounts_four_zones` to assert on the real
      widget types instead of generic `Static` placeholders.
- [ ] The app starts and exits cleanly with Ctrl+C / Ctrl+D.
- [ ] `ruff check` passes with no errors.
- [ ] `pytest` passes with no failures.

---

### US-004: Integrate Theme System Into Widgets

**Description:** As a developer, I want the TUI widgets to use the centralized
theme system defined in `colors.py` / `theme.py` so that color definitions are
not duplicated and dark/light mode support is possible.

**Implementation Notes:**

- **`src/mARCH/ui/tui_widgets/input_bar.py`:**
  - Import `get_theme` from `mARCH.ui.theme`.
  - Replace the hardcoded `MODE_COLORS` dict values with theme lookups
    (e.g., `theme.mode_interactive`).
- **`src/mARCH/ui/tui_widgets/status_bar.py`:**
  - Replace hardcoded `"bold green"`, `"bold red"`, etc. in `_STATUS_STYLES` with
    values from the theme's `status_*` fields.
- **`src/mARCH/ui/tui_widgets/message.py`:**
  - Replace hardcoded `"bold cyan"`, `"bold green"`, etc. in `_ROLE_STYLES` with
    theme-derived values.
- Keep `colors.py` and `theme.py` as-is — they already define the correct constants.
- Ensure `get_theme()` is called once at module level (or lazily) so that all
  widgets share one theme instance.

**Acceptance Criteria:**

- [ ] Unit test: `MODE_COLORS` values match the corresponding `get_theme()` fields.
- [ ] Unit test: `_STATUS_STYLES` values include the theme's status colors.
- [ ] Unit test: `_ROLE_STYLES` values include the theme's mode/role colors.
- [ ] `grep -r '"cyan"\|"green"\|"red"\|"yellow"\|"magenta"\|"blue"'` in widget
      files returns no hardcoded color strings (only theme references).
- [ ] `ruff check` passes with no errors.
- [ ] `pytest` passes with no failures.

---

### US-005: Scope N999 Ruff Suppression to Per-File Overrides

**Description:** As a developer, I want the N999 linting rule to be suppressed only
for files that actually need it (the `mARCH` package with its mixed-case name) so
that invalid module names elsewhere are caught by the linter.

**Implementation Notes:**

- **`pyproject.toml`:**
  - Remove `"N999"` from the global `ignore = [...]` list under `[tool.ruff]`.
  - Add a `[tool.ruff.per-file-ignores]` section (or extend the existing one):
    ```toml
    [tool.ruff.per-file-ignores]
    "src/mARCH/**" = ["N999"]
    ```
- Verify by running `ruff check` on the full project to confirm no new violations
  are introduced.

**Acceptance Criteria:**

- [ ] `"N999"` is not in the global `ignore` list in `pyproject.toml`.
- [ ] `pyproject.toml` contains a per-file-ignores entry suppressing N999 for
      `src/mARCH/**`.
- [ ] `ruff check` passes with no errors.
- [ ] `pytest` passes with no failures.

---

### US-006: Add Behavioral Tests for TUI Widget Interactions

**Description:** As a developer, I want behavioral tests that exercise real widget
interactions (mode cycling, status updates, streaming, modal dismiss flows) so that
regressions in widget logic are caught.

**Implementation Notes:**

- Add tests to `tests/test_tui_rewrite.py` (or a new `tests/test_tui_behavior.py`).
- **Mode cycling:**
  - Mount an `InputBar`, invoke `action_cycle_mode()` repeatedly, assert mode
    transitions through INTERACTIVE → PLAN → AUTOPILOT → SHELL → INTERACTIVE.
- **StatusBar updates:**
  - Mount a `StatusBar`, call `set_status("msg", "success")`, verify internal state.
  - Call `clear()`, verify state is reset.
- **Streaming:**
  - Create a `ConversationView`, call `start_streaming()`, then
    `append_chunk("a")`, `append_chunk("b")`, then `finish_streaming()`.
    Assert the accumulated content is `"ab"` and `_streaming_widget` is `None`.
- **SpinnerWidget lifecycle:**
  - Mount a `SpinnerWidget` inside a Textual app, call `start()`, verify `_running`
    is `True`, call `stop()`, verify `_running` is `False`.
- **ToolModal dismiss:**
  - Push a `ToolModal`, simulate pressing `y`, assert dismiss value is
    `"yes_once"`.
- Use `pytest-asyncio` and Textual's `run_test(headless=True)` / `Pilot` API for
  async widget tests.

**Acceptance Criteria:**

- [ ] Test: `InputBar.action_cycle_mode()` cycles through all 4 modes and wraps.
- [ ] Test: `StatusBar.set_status()` and `clear()` update internal state correctly.
- [ ] Test: `ConversationView.start_streaming()` + `append_chunk()` +
      `finish_streaming()` accumulates content and resets streaming widget.
- [ ] Test: `SpinnerWidget.start()` / `stop()` toggle `_running` flag when mounted.
- [ ] Test: `ToolModal` dismiss with `y` key returns `"yes_once"`.
- [ ] At least 5 new behavioral tests beyond import/existence checks.
- [ ] `ruff check` passes with no errors.
- [ ] `pytest` passes with no failures.

---

## 4. Non-Goals (Out of Scope)

- **AI client integration:** Wiring the TUI to the actual AI agent and streaming
  API responses is not part of these fixes.
- **Slash command handling in TUI:** Restoring `/help`, `/login`, etc. inside the
  Textual app is deferred to a separate story.
- **Dark/light mode toggle UI:** While US-004 integrates the theme system, adding
  a user-facing toggle for dark/light mode is out of scope.
- **Performance optimization:** No profiling or performance work is included.

## 5. Technical Considerations

- All widget fixes (US-001, US-002) must land before US-003 (wiring up MarchApp)
  since `MarchApp.compose()` will instantiate these widgets.
- The theme integration (US-004) should land after US-003 so that widget
  composition is stable before changing color references.
- Behavioral tests (US-006) should be written last to cover the fixed behavior.

## 6. Open Questions

- None — all issues are well-defined from the code review findings.
