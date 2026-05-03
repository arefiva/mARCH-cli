# PRD: Plan Mode Feature - Fix and Implementation

## 1. Introduction/Overview

The plan mode feature in copilot-cli-python is currently broken. When users press Shift+Tab to cycle through execution modes (interactive → plan → autopilot), an unhandled exception occurs in the prompt_toolkit event loop, crashing the REPL.

The root cause: `ModeChangeSignal` exception is raised from within a prompt_toolkit key binding handler. Prompt_toolkit's event loop expects handlers to complete normally or use async/await patterns—raising exceptions from handlers causes the event loop to fail.

This PRD describes the fix needed to make Shift+Tab mode switching work correctly, matching the feature parity of the original Copilot CLI (TypeScript version).

## 2. Goals

- ✅ Fix Shift+Tab key binding without crashing the prompt_toolkit event loop
- ✅ Enable users to cycle through execution modes: interactive → plan → autopilot → interactive
- ✅ Display mode change confirmation message
- ✅ Ensure no exception errors are printed to console
- ✅ Maintain feature parity with original tool

## 3. User Stories

### US-001: Fix Shift+Tab Mode Switching

**Description:** As a CLI user, I want to press Shift+Tab to cycle through execution modes so that I can switch between interactive, plan, and autopilot modes without restarting the CLI.

**Implementation Notes:**
- Modify `MARCH_REPL._create_key_bindings()` in `src/mARCH/cli/repl.py` (lines 71-87)
- Instead of raising `ModeChangeSignal`, set a flag on the PromptSession or store it in instance variable
- Return from key binding handler normally (don't raise exception)
- Make `get_input()` detect when mode change flag is set and return special marker string `__MODE_CHANGE__<mode>`
- The marker is already handled by `cli.py` (lines 687-694), so no changes needed there
- Test that prompt_toolkit event loop continues running without errors
- Ensure mode indicator in prompt updates after mode change
- Pattern: Use instance attribute `self._pending_mode_change` to signal mode change without exceptions

**Acceptance Criteria:**
- [ ] Pressing Shift+Tab triggers mode change without raising exception
- [ ] Exception no longer printed to console: "Unhandled exception in event loop"
- [ ] Mode cycles: interactive → plan → autopilot → interactive (repeats)
- [ ] Console prints confirmation: "[green]✓[/green] Mode changed to: [bold]{mode_name}[/bold]"
- [ ] REPL prompt is still responsive after mode change (user can type next command)
- [ ] No changes needed to cli.py main loop (already handles __MODE_CHANGE__ marker)
- [ ] Unit test verifies ModeChangeSignal exception is NOT raised from key binding
- [ ] Unit test verifies mode change marker is returned to main loop
- [ ] Build with `ruff check` passes with no errors
- [ ] `pytest` passes with no failures

### US-002: Verify Plan Mode Workflow Integration

**Description:** As a CLI user, I want plan mode to work end-to-end so that I can create, review, and approve plans using the `[[PLAN]]` prefix.

**Implementation Notes:**
- Verify that `handle_plan_mode()` in `cli.py` is called when user types `[[PLAN]]` followed by a request
- Check that `PlanModeDetector.is_plan_request()` correctly identifies `[[PLAN]]` prefix
- Verify `PlanGenerator.generate_plan()` creates structured plans
- Verify `PlanApprovalUI.display_plan()` displays plan correctly
- Verify `PlanApprovalUI.get_approval()` collects user choice (e, i, a, f)
- Verify plan execution flow works (or document what's missing)
- No code changes required—this is validation that existing components work together
- Pattern: Follow existing event-based architecture (exit_plan_mode tool in original)

**Acceptance Criteria:**
- [ ] User can type `[[PLAN]] my request` to start plan mode
- [ ] Plan is generated and displayed in terminal
- [ ] User is prompted to approve plan with choices: e, i, a, f
- [ ] Plan execution or exit works based on user choice
- [ ] No errors or exceptions occur during plan display and approval
- [ ] Plan content is correctly extracted and processed
- [ ] Manual end-to-end test passes without errors
- [ ] Build with `ruff check` passes with no errors
- [ ] `pytest` passes with no failures

## 4. Non-Goals (Out of Scope)

- Rewriting REPL with Textual (decision deferred—implement fix first)
- Adding new plan mode features beyond fixing the broken Shift+Tab
- Implementing background plan execution or async plan generation
- Supporting plan templates or plan history

## 5. Technical Considerations

### Why the Original Code Fails

The key binding handler in `repl.py` line 85 raises `ModeChangeSignal`:
```python
@bindings.add("s-tab")  # Shift+Tab
def _(event):
    if self.mode_manager:
        new_mode = self.mode_manager.cycle_mode()
        raise ModeChangeSignal(new_mode)  # ← PROBLEM: Exception escapes event loop
```

Prompt_toolkit's event loop processes key bindings and expects handlers to:
1. Return normally (no exception)
2. Modify state and return (e.g., update buffer)
3. Use async/await if needed

When an exception escapes, it propagates to the asyncio event loop, causing the "Unhandled exception in event loop" error.

### Solution: Flag-Based Mode Change

Instead of raising an exception, set a flag and return normally:
```python
@bindings.add("s-tab")  # Shift+Tab
def _(event):
    if self.mode_manager:
        new_mode = self.mode_manager.cycle_mode()
        self._pending_mode_change = new_mode  # ← Set flag instead
        # Signal the session to exit by breaking the input loop
        # or return a marker that get_input() will detect
```

Then in `get_input()`, detect the flag and return the marker:
```python
def get_input(self, mode: ExecutionMode = ExecutionMode.INTERACTIVE) -> str:
    try:
        user_input = self.session.prompt(prompt_text)
        if self._pending_mode_change:
            mode = self._pending_mode_change
            self._pending_mode_change = None
            return f"__MODE_CHANGE__{mode.value}"
        return user_input.strip()
    except ModeChangeSignal as e:  # Keep for backward compat (but won't be raised)
        return f"__MODE_CHANGE__{e.new_mode.value}"
```

### Prompt_toolkit Architecture

- `PromptSession` runs an event loop internally
- Key bindings are called from within that event loop
- Exceptions in handlers bubble up to asyncio event loop
- Solution: Use in-process signaling (flags, queues, or session state)

## 6. Open Questions

- Should we keep the `ModeChangeSignal` exception class for backward compatibility, or remove it?
  - **Answer:** Keep it but don't use it; mark as deprecated
- Should Shift+Tab only work in INTERACTIVE mode, or in all modes?
  - **Answer:** Work in all modes (user should always be able to change modes)
- Should we add keyboard shortcut help message when entering plan mode?
  - **Answer:** Not in this story (out of scope); can add in future

## 7. Success Criteria

✅ Feature complete when:
1. Shift+Tab cycles through modes without crashing
2. No exception errors printed to console
3. Mode indicator in prompt updates correctly
4. User can immediately type next command after mode change
5. All acceptance criteria from both user stories pass
6. Ruff and pytest pass
7. Manual end-to-end test succeeds
