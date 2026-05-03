# PRD: TUI Functional Conversation Loop

## 1. Introduction/Overview

The Textual TUI rewrite (TUI-001 through TUI-009) created all the individual widgets — `InputBar`,
`ConversationView`, `MessageWidget`, `HeaderWidget`, etc. — but the main application shell
(`tui_app.py`) was never updated to use them. It still mounts two `Static` placeholder widgets for
the conversation area and input bar, which means the user cannot type anything or receive AI
responses.

This PRD fixes the missing wire-up: replace the placeholders with the real widgets, focus the
input field on startup, then implement the full message dispatch loop (user types → Enter → AI
streams response → conversation view updates).

## 2. Goals

- Replace Static placeholders in `MarchApp.compose()` with the real `InputBar` and `ConversationView` widgets
- Auto-focus the input field so users can type immediately after launch
- Handle `Input.Submitted` events to add user messages to the conversation view
- Call the AI client from a thread worker and stream the response token-by-token into `ConversationView`
- Gracefully handle the case where the AI client is not configured (show a helpful message)
- Keep all existing tests green

## 3. User Stories

### US-001: Wire Real TUI Widgets into MarchApp

**Description:** As a user, I want the TUI input field to be interactive so that I can type
messages and see the conversation view update.

**Implementation Notes:**
- In `src/mARCH/ui/tui_app.py`, replace `Static("Conversation area…", id="conversation-area")` in
  `compose()` with `ConversationView(id="conversation-area")`; replace
  `Static("Input bar…", id="input-bar")` with `InputBar(id="input-bar")`
- Add `on_mount(self)` to `MarchApp` that calls
  `self.query_one("#march-input", Input).focus()` so the input is focused immediately
- Update `src/mARCH/ui/tui_widgets/input_bar.py`: change `__init__(self)` to
  `__init__(self, **kwargs)` and pass `**kwargs` to `super().__init__(**kwargs)` so callers can
  pass `id=` and other Textual widget kwargs
- Update `src/mARCH/ui/tui_widgets/conversation.py`: same `**kwargs` change in `__init__`
- Add imports to `tui_app.py`: `from textual.widgets import Footer, Header, Input` and
  `from mARCH.ui.tui_widgets import ConversationView, InputBar`

**Preservation Constraints:**
- `src/mARCH/ui/tui_widgets/input_bar.py` — must not be deleted
- `src/mARCH/ui/tui_widgets/input_bar.py::InputBar` — must remain importable
- `src/mARCH/ui/tui_widgets/conversation.py` — must not be deleted
- `src/mARCH/ui/tui_widgets/conversation.py::ConversationView` — must remain importable
- `src/mARCH/ui/tui_app.py::MarchApp` — must remain importable

**Acceptance Criteria:**
- [ ] `MarchApp.compose()` yields a `ConversationView` (not a `Static` placeholder) for the
  conversation area
- [ ] `MarchApp.compose()` yields an `InputBar` (not a `Static` placeholder) for the input area
- [ ] App mounts with the input field focused (`query_one("#march-input")` is focused on startup)
- [ ] Existing test `test_march_app_mounts_four_zones` passes: `#conversation-area` and
  `#input-bar` selectors still resolve
- [ ] `InputBar` and `ConversationView` `__init__` accept and forward `**kwargs` to
  `super().__init__()`
- [ ] `ruff check` passes with no errors
- [ ] `pytest` passes with no failures

---

### US-002: AI Conversation Dispatch Loop in MarchApp

**Description:** As a user, I want to type a message, press Enter, and see my message displayed
and then receive a streaming AI response in the TUI so I can have a real conversation with the
agent.

**Implementation Notes:**
- Add `__init__(self, ai_client=None, agent=None, **kwargs)` to `MarchApp`; store as
  `self._ai_client` and `self._agent`; call `super().__init__(**kwargs)`. **Do NOT import
  `AppContext` from `cli.py`** — that would create a circular import (`cli.py` already imports
  `tui_app.py`)
- Add `on_input_submitted(self, event: Input.Submitted)` to `MarchApp`: strip the text; return if
  empty; call `event.input.clear()`; query `ConversationView` and call
  `conv.add_message(MessageRole.USER, text)`; call
  `self._agent.add_user_message(text)` if agent is set; start `self._stream_ai_response(text)` if
  `ai_client` is set, otherwise call `conv.add_message(MessageRole.ASSISTANT, "AI client not
  configured — set ANTHROPIC_API_KEY")`
- Add `@work(thread=True, exclusive=True)` def `_stream_ai_response(self, user_text: str)`:
  query `ConversationView`; call `self.call_from_thread(conv.start_streaming)` to get
  `streaming_widget`; build messages from
  `self._agent.get_conversation_context(include_system_prompt=True)` if agent is available, else
  use `[{"role": "user", "content": user_text}]`; iterate
  `self._ai_client.stream_chat(messages)` sync generator and call
  `self.call_from_thread(streaming_widget.append_chunk, chunk)` per chunk; call
  `self.call_from_thread(conv.finish_streaming)` on completion; wrap in `try/except Exception` —
  on error, call `self.call_from_thread(conv.add_message, MessageRole.ASSISTANT, f"Error: {e}")`
  then `self.call_from_thread(conv.finish_streaming)`
- Add imports to `tui_app.py`: `from textual import work` and
  `from mARCH.ui.tui_widgets.message import MessageRole`
- Update `src/mARCH/cli/cli.py`: change `MarchApp().run()` to
  `MarchApp(ai_client=ctx.ai_client, agent=ctx.agent).run()` — `ctx` is already obtained from
  `get_app_context()` earlier in the same `main()` function
- Add a unit test in `tests/test_tui_rewrite.py` that uses `await app.run_test()` pilot to submit
  text and assert a `MessageWidget` with `MessageRole.USER` appears in `ConversationView` and the
  input is cleared; add a second test verifying that when `ai_client=None`, an ASSISTANT error
  message is added

**Preservation Constraints:**
- `src/mARCH/cli/cli.py` — must not be deleted
- `src/mARCH/cli/cli.py::main` — must remain callable; only the `MarchApp().run()` line changes
- `src/mARCH/cli/cli.py::handle_regular_input` — must remain importable
- `src/mARCH/core/agent_state.py::Agent` — must remain importable
- `src/mARCH/core/ai_client.py::ConversationClient` — must remain importable

**Acceptance Criteria:**
- [ ] `MarchApp.__init__` accepts optional `ai_client` and `agent` keyword arguments
- [ ] `on_input_submitted` handler exists on `MarchApp` and handles `Input.Submitted` events
- [ ] Submitting non-empty text adds a `USER` `MessageWidget` to `ConversationView`
- [ ] Submitting non-empty text clears the input field
- [ ] `_stream_ai_response` is decorated with `@work(thread=True)` and accepts a `str` argument
- [ ] When `ai_client` is `None`, submitting text shows an ASSISTANT "AI client not configured"
  message in `ConversationView`
- [ ] `cli.py::main` passes `ai_client` and `agent` to `MarchApp` constructor
- [ ] Unit test verifies: submitting text displays a `USER` message in `ConversationView`
- [ ] Unit test verifies: when `ai_client=None`, an ASSISTANT error message appears in
  `ConversationView`
- [ ] `ruff check` passes with no errors
- [ ] `pytest` passes with no failures

## 4. Non-Goals (Out of Scope)

- Slash command handling inside the TUI (handled separately in CLI layer)
- Plan mode (`[[PLAN]]`) integration in the TUI
- Tool call approval modal wiring (existing modal widgets are kept but not wired to live tool calls)
- Multiline input support (Ctrl+N is a stub for now)

## 5. Technical Considerations

- `ConversationClient.stream_chat()` returns a **sync** generator — use `@work(thread=True)` not
  `@work()` (async worker)
- `call_from_thread` in Textual blocks the calling thread until the callback returns on the main
  thread and returns its value — this is the correct pattern for getting `start_streaming()`'s
  return value from a thread worker
- The `InputBar` input has id `"march-input"` — use this selector for focus and in tests
- The `id="conversation-area"` and `id="input-bar"` selectors must be preserved to keep
  `test_march_app_mounts_four_zones` passing

## 6. Open Questions

None — the implementation path is clear from the existing codebase.
